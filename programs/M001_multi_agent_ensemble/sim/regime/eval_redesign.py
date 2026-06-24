"""Evaluation harness for the regime redesign v2 detectors.

Runs the detectors from `redesign_v2.py` against the existing weak
labels from `validate_real.py:weak_label_dataframe` on the
pre-registered evaluation set (PROTOCOL §3): EURUSD H4 2024 primary
+ GBPUSD H4 2024 + USDCAD H4 2024 + EURUSD H4 2023 cross-symbol /
cross-period robustness.

Emits a JSON results bundle to stdout (and optionally to a file)
containing per-class precision / recall / F1 for every symbol-window
combination, plus the comparison vs the legacy detector
(`atr20_percentile > 0.90`).

Usage::

    PYTHONPATH=../multi-pair-trading-agent:. \\
      ../multi-pair-trading-agent/.venv/bin/python \\
      -m programs.M001_multi_agent_ensemble.sim.regime.eval_redesign \\
      --out programs/M001_multi_agent_ensemble/reviews/regime_redesign_2026-06-24_eval.json

This script is the verdict-report data source — its output JSON is
embedded in `reviews/regime_redesign_2026-06-24.md` once committed.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from programs.M001_multi_agent_ensemble.sim.regime.redesign_v2 import (  # noqa: E402
    DetectorConfig,
    binary_f1,
    detect_news_ohlcv,
    detect_vol_spike,
    detect_vol_spike_v2b,
)
from programs.M001_multi_agent_ensemble.sim.regime.validate_real import (  # noqa: E402
    UNKNOWN_LABEL,
    load_news_calendar,
    weak_label_dataframe,
)
from programs.M001_multi_agent_ensemble.sim.regime.classifier import (  # noqa: E402
    extract_features,
    label_rule_based,
)

PARQUET_ROOT = (
    REPO_ROOT.parent / "multi-pair-trading-agent" / "data" / "parquet"
)

# Pre-registered evaluation slices per PROTOCOL §3.
EVAL_SLICES: tuple[dict, ...] = (
    {
        "name": "EURUSD_H4_2024",
        "parquet": PARQUET_ROOT / "EURUSD_H4.parquet",
        "window_start": "2024-01-01",
        "window_end": "2025-01-01",
        "role": "primary",
    },
    {
        "name": "EURUSD_H4_2023",
        "parquet": PARQUET_ROOT / "EURUSD_H4.parquet",
        "window_start": "2023-01-01",
        "window_end": "2024-01-01",
        "role": "cross_period",
    },
    {
        "name": "GBPUSD_H4_2024",
        "parquet": PARQUET_ROOT / "GBPUSD_H4.parquet",
        "window_start": "2024-01-01",
        "window_end": "2025-01-01",
        "role": "cross_symbol",
    },
    {
        "name": "USDCAD_H4_2024",
        "parquet": PARQUET_ROOT / "USDCAD_H4.parquet",
        "window_start": "2024-01-01",
        "window_end": "2025-01-01",
        "role": "cross_symbol",
    },
)


def legacy_vol_spike_predict(window: pd.DataFrame) -> pd.Series:
    """Reproduce the existing `classifier.label_rule_based` decision.

    For the `vol_spike` class only — the legacy rule is
    `atr20_percentile > 0.90` per `classifier.py:label_rule_based`.
    Returns a bool series aligned to ``window.index``.

    (This is the "before" arm for the verdict report's per-class
    precision/recall/F1 comparison.)
    """
    feats = extract_features(window).fillna(0.0)
    labels = feats.apply(label_rule_based, axis=1)
    return (labels == "vol_spike").rename("vol_spike_legacy")


def evaluate_slice(slice_spec: dict) -> dict:
    """Run both detectors against weak labels on one slice."""
    parquet_path = Path(slice_spec["parquet"])
    if not parquet_path.exists():
        return {
            "name": slice_spec["name"],
            "role": slice_spec["role"],
            "error": f"parquet missing: {parquet_path}",
        }
    bars = pd.read_parquet(parquet_path)
    if bars.index.tz is None:
        bars.index = bars.index.tz_localize("UTC")
    window = bars[
        (bars.index >= slice_spec["window_start"])
        & (bars.index < slice_spec["window_end"])
    ]
    if len(window) < 200:
        return {
            "name": slice_spec["name"],
            "role": slice_spec["role"],
            "error": f"insufficient bars: {len(window)}",
        }
    # Calendar adapter — `news` retirement means we don't depend on it
    # for the verdict, but if it happens to load (cross-symbol GBPUSD
    # uses USD/EUR proxy in the existing validator; here we keep it
    # symmetric so the weak-label `news` support is comparable).
    news_flag = load_news_calendar(window.index)
    news_available = news_flag is not None and (news_flag > 0).any()

    weak = weak_label_dataframe(window, news_calendar=news_flag)
    scope = weak != UNKNOWN_LABEL

    # New detectors.
    vol_spike_v2 = detect_vol_spike(window)
    vol_spike_v2b = detect_vol_spike_v2b(window)
    news_new = detect_news_ohlcv(window)
    # Build the predicted-label series for binary_f1's classification
    # API (same labels the weak series uses). Priority: news > vol_spike
    # > "other" (we don't compare the trending/chop classes here — they
    # weren't broken in the original validation).
    predicted_v2 = pd.Series("other", index=window.index, dtype="object")
    predicted_v2[vol_spike_v2] = "vol_spike"
    predicted_v2[news_new] = "news"  # always False, no-op by construction

    predicted_v2b = pd.Series("other", index=window.index, dtype="object")
    predicted_v2b[vol_spike_v2b] = "vol_spike"
    predicted_v2b[news_new] = "news"

    # Legacy detector (the current `classifier.label_rule_based`
    # vol_spike rule: `atr20_percentile > 0.90` — the function we are
    # about to retire).
    vol_spike_legacy = legacy_vol_spike_predict(window)
    predicted_legacy = pd.Series("other", index=window.index, dtype="object")
    predicted_legacy[vol_spike_legacy] = "vol_spike"

    # Per-class metrics — scoped to scope==True per the existing
    # validate_real.py contract.
    metrics_v2: dict = {}
    metrics_v2b: dict = {}
    metrics_legacy: dict = {}
    for label in ("vol_spike", "news"):
        metrics_v2[label] = binary_f1(
            weak=weak[scope], predicted=predicted_v2[scope],
            positive_label=label,
        )
        metrics_v2b[label] = binary_f1(
            weak=weak[scope], predicted=predicted_v2b[scope],
            positive_label=label,
        )
        metrics_legacy[label] = binary_f1(
            weak=weak[scope], predicted=predicted_legacy[scope],
            positive_label=label,
        )

    return {
        "name": slice_spec["name"],
        "role": slice_spec["role"],
        "parquet": str(parquet_path),
        "window": [slice_spec["window_start"], slice_spec["window_end"]],
        "counts": {
            "n_total_bars": int(len(window)),
            "n_scored_bars": int(scope.sum()),
            "n_weak_vol_spike": int((weak == "vol_spike").sum()),
            "n_weak_news": int((weak == "news").sum()),
            "n_pred_vol_spike_v2": int(vol_spike_v2.sum()),
            "n_pred_vol_spike_v2b": int(vol_spike_v2b.sum()),
            "n_pred_vol_spike_legacy": int(vol_spike_legacy.sum()),
            "n_pred_news_new": int(news_new.sum()),
        },
        "news_calendar_available": bool(news_available),
        "per_class_v2": {k: v.to_jsonable() for k, v in metrics_v2.items()},
        "per_class_v2b": {k: v.to_jsonable() for k, v in metrics_v2b.items()},
        "per_class_legacy": {
            k: v.to_jsonable() for k, v in metrics_legacy.items()
        },
    }


def run_all(*, config: DetectorConfig | None = None) -> dict:
    """Run every evaluation slice; produce the full results bundle."""
    cfg = config or DetectorConfig()
    return {
        "manifest": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "protocol": (
                "programs/M001_multi_agent_ensemble/reviews/"
                "regime_redesign_2026-06-24_PROTOCOL.md"
            ),
            "detector_config": asdict(cfg),
            "weak_label_source": (
                "programs/M001_multi_agent_ensemble/sim/regime/"
                "validate_real.py::weak_label_dataframe"
            ),
            "_note": (
                "Per-class precision / recall / F1 are scoped to bars "
                "where the weak labeller did NOT abstain (UNKNOWN_LABEL "
                "scope). Weak-label F1 is NOT ground-truth F1 — see "
                "PROTOCOL §5 weak-label-ceiling acknowledgement."
            ),
        },
        "thresholds": {
            "PASS": 0.50,
            "PARTIAL_LOWER": 0.30,
            "PARTIAL_UPPER": 0.50,
            "FAIL_UPPER": 0.30,
        },
        "slices": [evaluate_slice(s) for s in EVAL_SLICES],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", type=Path, default=None,
        help="optional path to write the JSON bundle; stdout otherwise",
    )
    args = parser.parse_args(argv)
    bundle = run_all()
    text = json.dumps(bundle, indent=2, sort_keys=True)
    print(text)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"\n[eval_redesign] wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
