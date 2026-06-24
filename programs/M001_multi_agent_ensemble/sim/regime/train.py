"""Training script for the regime classifier.

Usage (Phi2.5):

    PYTHONPATH=../multi-pair-trading-agent:. python -m \
        programs.M001_multi_agent_ensemble.sim.regime.train \
        --train-parquet path/to/eurusd_h1_2015_2023.parquet \
        --val-parquet   path/to/eurusd_h1_2024.parquet \
        --output programs/M001_multi_agent_ensemble/sim/regime/model_v1.pkl \
        --seed 42

If parquet inputs are not available, the script generates a
synthetic OHLCV frame (deterministic via seed) so the scaffold is
exercisable end-to-end without external data.

Phi2 -> Phi3 gate (G4): holdout F1 >= 0.75. The script writes that
score, per-class metrics, and a reproducibility manifest next to the
model artefact (`*.manifest.json`).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Allow running as a script: `python sim/regime/train.py ...`.
THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from programs.M001_multi_agent_ensemble.sim.regime.classifier import (  # noqa: E402
    RegimeClassifier,
    extract_features,
    label_rule_based,
)


def synthetic_bars(n: int, seed: int) -> tuple[pd.DataFrame, pd.Series]:
    """Deterministic OHLCV walk for smoke tests.

    Returns ``(bars, calendar_proximity)``. The walk alternates between
    regimes so the rule-based labeller produces all four classes. NOT
    a substitute for real data — see `sim/README.md` for the real
    parquet contract.
    """
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="h", tz="UTC")
    base = 1.10 + np.cumsum(rng.normal(0, 0.0005, n))
    high = base + np.abs(rng.normal(0, 0.0003, n))
    low = base - np.abs(rng.normal(0, 0.0003, n))
    opens = base + rng.normal(0, 0.0001, n)
    vol = rng.uniform(80, 120, n)
    # Inject a vol-spike block so the model sees `vol_spike`.
    spike = (n // 4)
    high[spike:spike + 50] += np.abs(rng.normal(0, 0.003, 50))
    low[spike:spike + 50] -= np.abs(rng.normal(0, 0.003, 50))
    # Inject calendar events so the model sees `news`.
    cal = np.zeros(n, dtype=float)
    news_starts = rng.choice(np.arange(120, n - 10), size=max(4, n // 200),
                             replace=False)
    for ns in news_starts:
        cal[ns:ns + 6] = 1.0  # 6-bar window around the event
    return pd.DataFrame(
        {"open": opens, "high": high, "low": low, "close": base, "volume": vol},
        index=idx,
    ), pd.Series(cal, index=idx, name="calendar_event_proximity")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train the regime classifier.")
    parser.add_argument("--train-parquet", type=str, default=None)
    parser.add_argument("--val-parquet", type=str, default=None)
    parser.add_argument(
        "--output", type=str,
        default=str(THIS_DIR / "model_v1.pkl"),
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-synthetic-train", type=int, default=4000)
    parser.add_argument("--n-synthetic-val", type=int, default=1000)
    args = parser.parse_args(argv)

    if args.train_parquet and args.val_parquet:
        df_train = pd.read_parquet(args.train_parquet)
        df_val = pd.read_parquet(args.val_parquet)
        cal_train = None
        cal_val = None
        source = "parquet"
    else:
        df_train, cal_train = synthetic_bars(args.n_synthetic_train, args.seed)
        df_val, cal_val = synthetic_bars(args.n_synthetic_val, args.seed + 1)
        source = "synthetic"

    feats_train = extract_features(df_train, calendar_proximity=cal_train).dropna()
    feats_val = extract_features(df_val, calendar_proximity=cal_val).dropna()
    y_train = feats_train.apply(label_rule_based, axis=1).astype("string")
    y_val = feats_val.apply(label_rule_based, axis=1).astype("string")

    clf = RegimeClassifier(seed=args.seed)
    result = clf.fit(feats_train, y_train, feats_val, y_val)

    manifest = {
        "seed": args.seed,
        "source": source,
        "n_train": result.n_train,
        "n_holdout": result.n_holdout,
        "holdout_f1_macro": result.holdout_f1_macro,
        "per_class_f1": result.per_class_f1,
        "datetime_utc": datetime.now(timezone.utc).isoformat(),
        "labeller": "rule_based_F18",
        "_note": (
            "Phi2.5 training uses rule-based labels per F18; "
            "Phi3+ should add hand-labelled validation set per "
            "09 section 1.5 gate G4."
        ),
    }
    clf.save(args.output, manifest=manifest)
    print(json.dumps(result.to_jsonable(), indent=2, sort_keys=True))
    print(f"\n[regime.train] artefact: {args.output}")
    print(
        f"[regime.train] holdout macro F1 = {result.holdout_f1_macro:.3f} "
        f"({'PASS' if result.holdout_f1_macro >= 0.75 else 'FAIL'} G4)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
