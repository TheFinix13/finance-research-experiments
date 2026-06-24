"""Holdout evaluation for the regime classifier.

Emits F1/precision/recall per class plus a confusion matrix. The gate
G4 threshold (holdout F1 >= 0.75) is checked and printed in the
script's exit message; non-zero exit code if it fails.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from programs.M001_multi_agent_ensemble.sim.regime.classifier import (  # noqa: E402
    REGIMES,
    RegimeClassifier,
    extract_features,
    label_rule_based,
)
from programs.M001_multi_agent_ensemble.sim.regime.train import (  # noqa: E402
    synthetic_bars,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the regime model.")
    parser.add_argument(
        "--model", type=str, default=str(THIS_DIR / "model_v1.pkl"),
    )
    parser.add_argument("--holdout-parquet", type=str, default=None)
    parser.add_argument("--seed", type=int, default=43)
    parser.add_argument("--n-synthetic", type=int, default=1000)
    parser.add_argument("--gate", type=float, default=0.75)
    args = parser.parse_args(argv)

    clf = RegimeClassifier.load(args.model)

    if args.holdout_parquet:
        df = pd.read_parquet(args.holdout_parquet)
        cal = None
    else:
        df, cal = synthetic_bars(args.n_synthetic, args.seed)

    feats = extract_features(df, calendar_proximity=cal).dropna()
    y_true = feats.apply(label_rule_based, axis=1).astype("string").to_list()
    y_pred = clf.predict(feats).tolist()

    from sklearn.metrics import classification_report, f1_score
    macro_f1 = float(
        f1_score(y_true, y_pred, average="macro", zero_division=0,
                 labels=list(REGIMES))
    )
    report = classification_report(
        y_true, y_pred,
        labels=list(REGIMES),
        output_dict=True,
        zero_division=0,
    )
    out = {
        "n_holdout": int(len(y_true)),
        "macro_f1": macro_f1,
        "per_class": {r: report[r] for r in REGIMES},
        "gate_threshold": float(args.gate),
        "gate_pass": bool(macro_f1 >= args.gate),
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if macro_f1 >= args.gate else 1


if __name__ == "__main__":
    raise SystemExit(main())
