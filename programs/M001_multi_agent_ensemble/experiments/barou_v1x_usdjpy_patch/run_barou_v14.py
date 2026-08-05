"""Barou v1.4 design/sealed isolation driver (see PROTOCOL.md).

    python run_barou_v14.py --phase design
    python run_barou_v14.py --phase sealed
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PRODUCT_REPO = Path("/Users/the1finix/Documents/GitHub/multi-pair-trading-agent-product")
TIER1_CACHE = Path("/Users/the1finix/Documents/GitHub/multi-pair-trading-agent/data/parquet")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(PRODUCT_REPO))

import pandas as pd  # noqa: E402
from agent.data.loader import df_to_bars, filter_bars_by_date  # noqa: E402
from agent.types import Timeframe  # noqa: E402

EQUITY = 500.0
SYMBOL = "USDJPY"
AGENT = "barou_shoei"
DESIGN_STARTS = ("2015-01-01", "2015-04-01", "2015-07-01",
                 "2015-10-01", "2016-01-01")
DESIGN_END = "2022-12-31"
SEALED_STARTS = ("2023-01-01", "2023-04-01", "2023-07-01",
                 "2023-10-01", "2024-01-01")
SEALED_END = "2026-05-31"


def _load(start: datetime, end: datetime):
    df = pd.read_parquet(TIER1_CACHE / f"{SYMBOL}_H4.parquet")
    return filter_bars_by_date(df_to_bars(df, Timeframe.H4), start=start, end=end)


def _run_one(start_iso: str, end_iso: str, out_dir: Path) -> dict:
    import agent.squad.agents.a07_barou as a07
    import agent.squad.roster as roster_mod
    from agent.squad.engine import SquadEngine
    from agent.squad.roster import build_roster

    a07.BAROU_V1_SYMBOLS = (SYMBOL,)
    roster_mod.DEFAULT_SYMBOLS = (SYMBOL,)

    start = datetime.fromisoformat(start_iso).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(end_iso).replace(tzinfo=timezone.utc)
    bars = _load(start, end)

    roster = build_roster(barou_v13=True, barou_v14=True)
    roster.proposers = [a for a in roster.proposers if a.agent_id == AGENT]
    assert len(roster.proposers) == 1
    assert roster.proposers[0]._weapon_v14 is True
    assert roster.proposers[0]._stop_atr_max == 2.25

    out_dir.mkdir(parents=True, exist_ok=True)
    engine = SquadEngine(
        roster, out_dir, aggregator_arm="phi41",
        source_label=f"barou_v14:{SYMBOL}:{start_iso}", equity=EQUITY,
    )
    t0 = time.time()
    stats = engine.run_batch({SYMBOL: bars})
    print(f"  {AGENT}:{SYMBOL} start={start_iso} bars={len(bars)} "
          f"trades={stats.get('n_trades', 0)} ({time.time()-t0:.0f}s)",
          flush=True)
    return {"start": start_iso, "end": end_iso, "bars": len(bars),
            "n_trades": stats.get("n_trades", 0)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("design", "sealed"), required=True)
    args = ap.parse_args()
    starts = DESIGN_STARTS if args.phase == "design" else SEALED_STARTS
    end = DESIGN_END if args.phase == "design" else SEALED_END
    root = HERE / "results" / args.phase
    meta = []
    for k, start in enumerate(starts):
        out = root / f"start_{k}"
        meta.append(_run_one(start, end, out))
    (root / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"barou_v14 {args.phase} complete", flush=True)


if __name__ == "__main__":
    main()
