"""Test A, Stage 2: conditional (context × setup) pairs among Stage-1
survivors, on the screen split only.

Usage:
    PYTHONPATH=/path/to/multi-pair-trading-agent:. python scripts/run_stage2.py \
        --registry output/stage1_EURUSD_screen_<stamp>.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conflab.data import load_frames
from conflab.events import all_detectors
from conflab.stage2 import Stage2Config, run_stage2

SCREEN_START = "2015-01-01"
SCREEN_END = "2021-12-31"


def main() -> None:
    p = argparse.ArgumentParser(description="Test A Stage-2 pairs.")
    p.add_argument("--registry", required=True)
    p.add_argument("--symbol", default="EURUSD")
    p.add_argument("--out", default="output")
    p.add_argument("--include-parked-weak", action="store_true",
                   help="EXPLORATORY ONLY: also pair parked_weak_effect "
                        "cells (results labelled exploratory)")
    args = p.parse_args()

    rows = [json.loads(line) for line in
            Path(args.registry).read_text().splitlines() if line.strip()]
    wanted = {"alive"}
    if args.include_parked_weak:
        wanted.add("parked_weak_effect")
    survivors = [r for r in rows if r["verdict"] in wanted]
    print(f"Stage-1 cells entering Stage 2 ({'+parked_weak' if args.include_parked_weak else 'alive only'}): {len(survivors)}")
    for r in survivors:
        print(f"  {r['tf']:>4} {r['event_type']:<30} n={r['n']:>6} "
              f"effect={r['effect']:+.3f} p={r['p_value']:.4f} [{r['verdict']}]")
    if len(survivors) < 2:
        print("\nFewer than two survivors — Stage-2 pair family is EMPTY "
              "by protocol. Recording the outcome and stopping.")
        return

    tfs = sorted({r["tf"] for r in survivors})
    frames = load_frames(args.symbol, tfs, start=SCREEN_START, end=SCREEN_END)
    detectors = all_detectors()
    events_by_cell: dict[tuple, list] = {}
    for tf, df in frames.items():
        for det in detectors.values():
            for e in det(df):
                events_by_cell.setdefault((tf, e.type), []).append(e)

    out_rows = run_stage2(survivors, frames, events_by_cell, Stage2Config())
    print(f"\nStage-2 pair registry ({len(out_rows)} pairs):")
    for r in sorted(out_rows, key=lambda r: r["p_value"]):
        print(f"  {r['context']:<34} x {r['setup']:<34} "
              f"n={r['n_joint']:>5} lift={r['lift']:+.3f} "
              f"p={r['p_value']:.4f} [{r['verdict']}]")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_%H%M")
    path = out_dir / f"stage2_{args.symbol}_{stamp}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r) + "\n")
    print(f"\nregistry: {path}")


if __name__ == "__main__":
    main()
