"""Reaction metric + experiment harness contracts."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conflab.data import synthetic_frame
from conflab.experiment import (
    ExperimentConfig,
    analyze,
    benjamini_hochberg,
    format_report,
    run_experiment,
)
from conflab.reaction import find_touches


def _frame(closes: list[float], wick: float = 0.0003) -> pd.DataFrame:
    closes_arr = np.asarray(closes, dtype=float)
    opens = np.concatenate([[closes_arr[0]], closes_arr[:-1]])
    idx = pd.date_range("2024-01-01", periods=len(closes_arr), freq="4h",
                        tz="UTC")
    return pd.DataFrame({
        "open": opens,
        "high": np.maximum(opens, closes_arr) + wick,
        "low": np.minimum(opens, closes_arr) - wick,
        "close": closes_arr,
        "volume": np.full(len(closes_arr), 100.0)}, index=idx)


def test_touch_with_bounce_scores_positive_and_held():
    # Drift down into 1.0950, bounce hard away from it.
    closes = (list(np.linspace(1.1050, 1.0952, 30))
              + list(np.linspace(1.0955, 1.1040, 15)))
    df = _frame(closes)
    touches = find_touches(df, 1.0948, 1.0956, start=20, end=35, horizon=12)
    assert touches, "touch not detected"
    t = touches[0]
    assert t.from_above is True
    assert t.reaction_atr > 1.0
    assert t.held is True


def test_touch_blown_through_is_not_held():
    closes = list(np.linspace(1.1050, 1.0900, 40))  # straight through
    df = _frame(closes)
    touches = find_touches(df, 1.0948, 1.0956, start=10, end=40, horizon=10)
    assert touches
    assert touches[0].held is False
    assert touches[0].reaction_atr < 1.0


def test_no_touch_when_price_never_reaches():
    df = _frame([1.10] * 40)
    assert find_touches(df, 1.2000, 1.2010, start=1, end=40) == []


def test_benjamini_hochberg_basic():
    flags = benjamini_hochberg([0.001, 0.04, 0.9], alpha=0.05)
    assert flags[0] is True
    assert flags[2] is False
    assert benjamini_hochberg([]) == []


def test_experiment_smoke_produces_bands_and_controls():
    frames = {"H4": synthetic_frame(700, seed=5),
              "D1": synthetic_frame(150, seed=6, tf_hours=24)}
    cfg = ExperimentConfig(eval_tf="H4", warmup=260, stride=30,
                           n_controls=8, use_mainrepo=False, seed=1)
    records = run_experiment(frames, cfg)
    assert records, "experiment produced no touch records"
    kinds = {r["is_control"] for r in records}
    assert kinds == {True, False}, "need both band and control touches"
    for r in records:
        assert r["reaction_atr"] >= 0.0

    report = analyze(records)
    assert report["n_records"] == len(records)
    assert "mean_reaction_control" in report
    p = report.get("permutation_p_high_vs_control")
    if p is not None:
        assert 0.0 < p <= 1.0
    text = format_report(report)
    assert "confluence-lab experiment report" in text
    assert "CAVEAT" in text


def test_experiment_is_deterministic_for_fixed_seed():
    frames = {"H4": synthetic_frame(500, seed=9)}
    cfg = ExperimentConfig(eval_tf="H4", warmup=260, stride=40,
                           n_controls=5, use_mainrepo=False, seed=2)
    r1 = run_experiment(frames, cfg)
    r2 = run_experiment(frames, cfg)
    assert r1 == r2
