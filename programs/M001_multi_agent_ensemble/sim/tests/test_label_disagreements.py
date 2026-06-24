"""Smoke + pure-logic tests for the regime disagreement labelling tool.

The Streamlit page itself is exercised by the user (the tool is a v0
human-data-loop surface, not a CI gate). These tests cover:

* The module imports cleanly without launching Streamlit.
* The CSV read path resolves the existing
  `disagreements_for_review.csv` artefact and yields exactly 30 anchor
  records with the 51-bar context shape the validator wrote.
* `append_label` writes append-only rows; re-saving the same anchor
  produces two rows whose `labeled_at` orders correctly and where
  `latest_labels` resolves "most recent wins".
* `compute_aggregate` returns the same schema as the
  machine-validation JSON when given a full set of labels.
* `build_validation_json` carries the inherited manifest fields and
  the new `labeled_by` / `labeled_at` fields, and is valid JSON.
"""
from __future__ import annotations

import importlib
import json
import time
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture(scope="module")
def labeller():
    """Import the module once per test module."""
    return importlib.import_module(
        "programs.M001_multi_agent_ensemble.sim.regime.label_disagreements"
    )


def test_module_imports(labeller):
    """Smoke test: module imports without launching Streamlit."""
    assert hasattr(labeller, "main")
    assert hasattr(labeller, "load_disagreements")
    assert hasattr(labeller, "iter_anchors")
    assert hasattr(labeller, "append_label")
    assert hasattr(labeller, "compute_aggregate")
    assert hasattr(labeller, "build_validation_json")
    # Regime taxonomy stays consistent with classifier.py
    assert labeller.REGIMES == ("trending", "chop", "vol_spike", "news")
    # Human-only exits are tacked on after the canonical regimes.
    assert labeller.HUMAN_CHOICES[-2:] == ("unknown", "skip")


def test_load_disagreements_on_real_csv(labeller):
    """The existing CSV must be readable and shaped as `validate_real.py` writes."""
    df = labeller.load_disagreements()
    assert not df.empty
    # 30 anchors × 51 bars = 1530 rows when the validator ran on
    # 2024 EURUSD H4 — the test allows for re-samples (anchor count
    # may vary, but the per-anchor context window is fixed).
    expected_cols = {
        "sample_idx", "anchor_ts", "weak_label", "predicted_label",
        "offset", "ts", "open", "high", "low", "close", "volume",
    }
    assert expected_cols.issubset(set(df.columns))
    # Each anchor has the same number of context bars (51 = 50 lookback + the
    # anchor at offset 0).
    counts_per_anchor = df.groupby("sample_idx").size()
    assert counts_per_anchor.nunique() == 1
    assert counts_per_anchor.iloc[0] == 51


def test_iter_anchors_yields_records(labeller):
    df = labeller.load_disagreements()
    anchors = labeller.iter_anchors(df)
    assert anchors, "expected at least one disagreement anchor"
    for rec in anchors:
        assert set(rec) == {
            "sample_idx", "anchor_ts", "rule_label",
            "classifier_label", "ohlc",
        }
        assert rec["rule_label"] in labeller.REGIMES
        assert rec["classifier_label"] in labeller.REGIMES
        # The anchor must be at the end of the 51-bar window and the
        # frame must have a DatetimeIndex named 'Date' (mplfinance contract).
        assert rec["ohlc"].index.name == "Date"
        assert isinstance(rec["ohlc"].index, pd.DatetimeIndex)
        assert len(rec["ohlc"]) == 51


def test_append_label_round_trip(labeller, tmp_path: Path):
    """Append-only writer + `latest_labels` resolver behave as specced."""
    csv_path = tmp_path / "labeled.csv"
    anchor_ts = pd.Timestamp("2024-02-05T08:00:00", tz="UTC")
    labeller.append_label(
        sample_idx=0,
        anchor_ts=anchor_ts,
        rule_label="vol_spike",
        classifier_label="chop",
        human_label="trending",
        note="strong impulse leg",
        path=csv_path,
    )
    time.sleep(0.01)  # guarantee labeled_at ordering
    labeller.append_label(
        sample_idx=0,
        anchor_ts=anchor_ts,
        rule_label="vol_spike",
        classifier_label="chop",
        human_label="vol_spike",
        note="changed my mind — gap candle",
        path=csv_path,
    )
    df = labeller.read_existing_labels(csv_path)
    assert len(df) == 2  # append-only, both rows persisted
    resolved = labeller.latest_labels(df)
    assert resolved == {0: "vol_spike"}, "most recent label must win"


def test_compute_aggregate_with_synthetic_labels(labeller):
    """A synthetic 4-anchor set hits every code path in the aggregator."""
    anchors = [
        {"sample_idx": 0, "anchor_ts": pd.Timestamp("2024-01-01", tz="UTC"),
         "rule_label": "trending", "classifier_label": "chop", "ohlc": None},
        {"sample_idx": 1, "anchor_ts": pd.Timestamp("2024-01-02", tz="UTC"),
         "rule_label": "vol_spike", "classifier_label": "vol_spike",
         "ohlc": None},
        {"sample_idx": 2, "anchor_ts": pd.Timestamp("2024-01-03", tz="UTC"),
         "rule_label": "chop", "classifier_label": "trending", "ohlc": None},
        {"sample_idx": 3, "anchor_ts": pd.Timestamp("2024-01-04", tz="UTC"),
         "rule_label": "trending", "classifier_label": "trending",
         "ohlc": None},
    ]
    labels_by_idx = {
        0: "trending",   # rule got it right, classifier wrong
        1: "vol_spike",  # both right
        2: "skip",       # excluded from F1
        3: "trending",   # both right
    }
    agg = labeller.compute_aggregate(anchors=anchors, labels_by_idx=labels_by_idx)
    assert agg["n_anchors_total"] == 4
    assert agg["n_labeled"] == 3  # skip excluded from `n_labeled`
    assert agg["n_skipped"] == 1
    assert agg["n_scored"] == 3
    # The classifier disagrees with the human on anchor 0 (chop vs trending).
    f1 = agg["vs_classifier"]["agreement_f1_macro"]
    assert 0.0 <= f1 <= 1.0
    # Per-class shape is stable across both sides.
    assert set(agg["vs_classifier"]["per_class"]) == set(labeller.REGIMES)
    assert set(agg["vs_rule"]["per_class"]) == set(labeller.REGIMES)


def test_build_validation_json_schema(labeller, tmp_path: Path):
    """JSON payload carries the human-only fields + inherits manifest."""
    anchors = [
        {"sample_idx": 0, "anchor_ts": pd.Timestamp("2024-01-01", tz="UTC"),
         "rule_label": "trending", "classifier_label": "chop", "ohlc": None},
    ]
    labels_by_idx = {0: "trending"}
    aggregate = labeller.compute_aggregate(
        anchors=anchors, labels_by_idx=labels_by_idx,
    )
    fake_source = tmp_path / "source.json"
    fake_source.write_text(json.dumps({
        "manifest": {
            "parquet_path": "/some/EURUSD_H4.parquet",
            "window_start": "2024-01-01 00:00:00+00:00",
            "window_end": "2024-12-31 20:00:00+00:00",
            "seed": 42,
        },
    }))
    payload = labeller.build_validation_json(
        aggregate=aggregate,
        anchors=anchors,
        labels_by_idx=labels_by_idx,
        source_json_path=fake_source,
    )
    assert payload["labeled_by"] == "user"
    assert payload["labeled_at"]  # ISO timestamp string
    assert payload["manifest"]["seed"] == 42  # inherited
    assert payload["manifest"]["parquet_path"].endswith("EURUSD_H4.parquet")
    assert payload["manifest"]["labeling_tool"].endswith("label_disagreements.py")
    assert "agreement_f1_macro_vs_classifier" in payload["metrics"]
    assert "agreement_f1_macro_vs_rule" in payload["metrics"]
    assert payload["gate"]["threshold_agreement_f1"] == 0.5

    out = tmp_path / "out.json"
    written = labeller.write_validation_json(payload, path=out)
    assert written == out
    reread = json.loads(out.read_text(encoding="utf-8"))
    assert reread["labeled_by"] == "user"
