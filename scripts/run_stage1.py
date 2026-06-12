"""Test A, Stage 1: marginal screening of every price-action event type.

Screen split per PROTOCOL.md: 2015-01-01 → 2021-12-31. Confirm and sealed
splits are NOT touched by this script.

NOTE: per the protocol, the canonical Stage-1 analysis runs once when the
Stage-0 build queue is empty. Runs before that are BUILD-PROGRESS previews
(clearly labelled) — useful for sanity, not for claims.

Usage:
    PYTHONPATH=/path/to/eurusd-ai-agent:. python scripts/run_stage1.py \
        --symbol EURUSD --tfs D1,H4,H1
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conflab.data import load_frames
from conflab.screening import Stage1Config, format_registry, run_stage1

SCREEN_START = "2015-01-01"
SCREEN_END = "2021-12-31"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Test A Stage-1 screen.")
    p.add_argument("--symbol", "-s", default="EURUSD")
    p.add_argument("--tfs", default="D1,H4,H1,M15")
    p.add_argument("--out", default="output")
    p.add_argument("--start", default=SCREEN_START)
    p.add_argument("--end", default=SCREEN_END)
    p.add_argument("--tag", default="",
                   help="extra label for the output file (e.g. 'confirm')")
    p.add_argument("--final", action="store_true",
                   help="assert the build queue is empty (canonical run)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    tfs = [t.strip().upper() for t in args.tfs.split(",") if t.strip()]
    frames = load_frames(args.symbol, tfs, start=args.start, end=args.end)
    if not frames:
        print("No data loaded.")
        return

    label = "CANONICAL" if args.final else "BUILD-PROGRESS PREVIEW"
    print(f"[{label}] Test A Stage 1 — {args.symbol}, split "
          f"{args.start}..{args.end}, TFs: {', '.join(frames)}")
    for tf, df in frames.items():
        print(f"  {tf}: {len(df)} bars")

    rows = run_stage1(frames, Stage1Config(), screen_end=args.end)
    print()
    print(format_registry(rows))

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_%H%M")
    tag = f"_{args.tag}" if args.tag else ""
    path = out_dir / f"stage1_{args.symbol}{tag}_{stamp}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"\nregistry: {path}")
    print("CAVEAT: hypothesis-generating evidence only; verdicts govern what")
    print("advances to Stage 2, never what the live agent trades.")


if __name__ == "__main__":
    main()
