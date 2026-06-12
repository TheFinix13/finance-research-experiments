"""Run the pre-registered confluence experiment on historical data.

Tests README's H0/H1: do high-confluence bands out-react matched random
levels? Walk-forward, identical scoring code for bands and controls,
BH-FDR-corrected per-source ablation.

Usage:
    PYTHONPATH=/path/to/eurusd-ai-agent:. python scripts/run_experiment.py \
        --symbol EURUSD --eval-tf H4 --days 1500
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conflab.data import load_frames
from conflab.experiment import (
    ExperimentConfig,
    analyze,
    format_report,
    run_experiment,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Confluence H0/H1 experiment.")
    p.add_argument("--symbol", "-s", default="EURUSD")
    p.add_argument("--tfs", default="D1,H4",
                   help="timeframes for level extraction (default D1,H4)")
    p.add_argument("--eval-tf", default="H4",
                   help="timeframe whose bars are scored (default H4)")
    p.add_argument("--days", type=int, default=1500)
    p.add_argument("--stride", type=int, default=24)
    p.add_argument("--horizon", type=int, default=12)
    p.add_argument("--mainrepo-levels", action="store_true",
                   help="include zone/trendline/fib levels (slower)")
    p.add_argument("--out", default="output")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    tfs = [t.strip().upper() for t in args.tfs.split(",") if t.strip()]
    if args.eval_tf not in tfs:
        tfs.append(args.eval_tf)
    frames = load_frames(args.symbol, tfs, days=args.days)
    if args.eval_tf not in frames:
        print(f"No data for eval TF {args.eval_tf}")
        return

    cfg = ExperimentConfig(eval_tf=args.eval_tf, stride=args.stride,
                           horizon=args.horizon,
                           use_mainrepo=args.mainrepo_levels)
    print(f"Running walk-forward experiment on {args.symbol} "
          f"({', '.join(frames)} | eval {args.eval_tf}, "
          f"{len(frames[args.eval_tf])} bars)…")
    records = run_experiment(frames, cfg)
    report = analyze(records, min_band_members=cfg.min_band_members)
    print()
    print(format_report(report))

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_%H%M")
    rec_path = out_dir / f"{args.symbol}_{args.eval_tf}_records_{stamp}.jsonl"
    with rec_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    (out_dir / f"{args.symbol}_{args.eval_tf}_report_{stamp}.json").write_text(
        json.dumps(report, indent=2, default=str))
    print(f"\nrecords: {rec_path}")


if __name__ == "__main__":
    main()
