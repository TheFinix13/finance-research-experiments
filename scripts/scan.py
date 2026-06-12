"""Visual confluence scanner: where do levels stack right now?

Loads D1/H4/H1 from the main repo's parquet cache, extracts every level
source per timeframe, clusters them into scored bands, prints the table and
renders one annotated chart per timeframe into output/.

Observation only — there is no order code anywhere in this repository.

Usage:
    PYTHONPATH=/path/to/eurusd-ai-agent:. python scripts/scan.py --symbol EURUSD
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conflab.confluence import cluster_levels, top_bands
from conflab.data import load_frames
from conflab.indicators import atr
from conflab.levels import extract_all_levels
from conflab.render import render_confluence_chart


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cross-TF confluence scan.")
    p.add_argument("--symbol", "-s", default="EURUSD")
    p.add_argument("--tfs", default="D1,H4,H1",
                   help="comma-separated timeframes (default D1,H4,H1)")
    p.add_argument("--days", type=int, default=400)
    p.add_argument("--tol-atr", type=float, default=0.5,
                   help="cluster tolerance in ATR of the highest TF")
    p.add_argument("--no-mainrepo-levels", action="store_true",
                   help="skip zone/trendline/fib levels from the main repo")
    p.add_argument("--out", default="output")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    tfs = [t.strip().upper() for t in args.tfs.split(",") if t.strip()]
    frames = load_frames(args.symbol, tfs, days=args.days)
    if not frames:
        print("No data loaded — is the parquet cache populated?")
        return

    levels = []
    for tf, df in frames.items():
        tf_levels = extract_all_levels(df, tf,
                                       use_mainrepo=not args.no_mainrepo_levels)
        levels.extend(tf_levels)
        print(f"{tf}: {len(df)} bars, {len(tf_levels)} levels")

    anchor_tf = tfs[0]
    tol = args.tol_atr * float(atr(frames[anchor_tf]).iloc[-1])
    bands = top_bands(cluster_levels(levels, tolerance=tol))

    print(f"\n{args.symbol} confluence bands "
          f"(tolerance {tol:.5f}, {len(levels)} levels)\n")
    print(f"{'center':>9} {'score':>7} {'lvls':>5} {'srcs':>5} {'TFs':>4}  members")
    print("-" * 100)
    for b in bands:
        print(f"{b.center:>9.5f} {b.score:>7.2f} {b.n_members:>5} "
              f"{b.n_sources:>5} {b.n_timeframes:>4}  {b.sources_summary()}")

    out_dir = Path(args.out)
    stamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_%H%M")
    for tf, df in frames.items():
        png = out_dir / f"{args.symbol}_{tf}_{stamp}.png"
        if render_confluence_chart(df, bands, png,
                                   title=f"{args.symbol} {tf} — confluence "
                                         f"bands @ {stamp}"):
            print(f"chart: {png}")

    jsonl = out_dir / f"{args.symbol}_bands.jsonl"
    out_dir.mkdir(parents=True, exist_ok=True)
    with jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": stamp, "symbol": args.symbol, "tolerance": tol,
            "bands": [b.to_dict() for b in bands],
        }) + "\n")
    print(f"journal: {jsonl}")
    print("\nObservation only — these bands carry no trade authority.")


if __name__ == "__main__":
    main()
