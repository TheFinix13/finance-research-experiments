"""I030 parity harness: prove the pip-semantics fix is a no-op on majors.

Runs the deployed squad (full roster, phi41 arm) over 2019 on the three
deployed majors, once per invocation. Called twice by the driver -- with
the pre-fix engine (git stash) and the post-fix engine -- and the two
trades.jsonl tapes must be byte-identical.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

PRODUCT_REPO = Path("/Users/the1finix/Documents/GitHub/multi-pair-trading-agent-product")
CACHE_ROOT = Path("/Users/the1finix/Documents/GitHub/multi-pair-trading-agent/data/parquet")
SYMBOLS = ("EURUSD", "GBPUSD", "USDCAD")

sys.path.insert(0, str(PRODUCT_REPO))

from agent.data.source import ParquetCache  # noqa: E402
from agent.data.loader import df_to_bars, filter_bars_by_date  # noqa: E402
from agent.types import Timeframe  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()

    from agent.squad.engine import SquadEngine
    from agent.squad.roster import build_roster

    start = datetime(2019, 1, 1, tzinfo=timezone.utc)
    end = datetime(2019, 12, 31, tzinfo=timezone.utc)
    cache = ParquetCache(CACHE_ROOT)
    bars_by_symbol = {}
    for sym in SYMBOLS:
        bars = df_to_bars(cache.load(sym, Timeframe.H4), Timeframe.H4)
        bars_by_symbol[sym] = filter_bars_by_date(bars, start=start, end=end)

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = SquadEngine(
        build_roster(), out_dir,
        aggregator_arm="phi41", source_label="i030_parity",
    )
    stats = engine.run_batch(bars_by_symbol)
    print("run_batch stats:", stats, flush=True)


if __name__ == "__main__":
    main()
