"""Phase AN driver: multi-start isolation replays for the chartered
field follow-ups (see PROTOCOL.md).

    python run_phase_an.py --phase design
    python run_phase_an.py --phase sealed --studies AN-3 AN-1 ...

Each (study, field, start) is one fresh replay: roster rebuilt,
proposers filtered to the study agent, engine state from empty.
Burn-in/cost handling happens in summarize_phase_an.py (analysis
layer), so raw tapes stay untouched.
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
TIER2_STORE = Path("/Users/the1finix/Documents/GitHub/finance-research-experiments/data/parquet_tier2")
HERE = Path(__file__).resolve().parent

sys.path.insert(0, str(PRODUCT_REPO))

import pandas as pd  # noqa: E402

from agent.data.loader import df_to_bars, filter_bars_by_date  # noqa: E402
from agent.types import Timeframe  # noqa: E402

EQUITY = 500.0
DESIGN_STARTS = ("2015-01-01", "2015-04-01", "2015-07-01",
                 "2015-10-01", "2016-01-01")
DESIGN_END = "2022-12-31"
SEALED_STARTS = ("2023-01-01", "2023-04-01", "2023-07-01",
                 "2023-10-01", "2024-01-01")
SEALED_END = "2026-05-31"

STUDIES: dict[str, dict] = {
    "AN-1": {"agent": "itoshi_rin", "fields": ("USDJPY",)},
    "AN-2": {"agent": "chigiri_hyoma", "fields": ("AUDUSD",)},
    "AN-3": {"agent": "chigiri_hyoma", "fields": ("XAGUSD",)},
    "AN-4": {"agent": "bachira_meguru", "fields": ("NZDUSD",)},
    "AN-5": {"agent": "barou_shoei", "fields": ("USDCAD", "USDJPY", "USTEC")},
}

TIER2_FIELDS = {"XAGUSD", "XAUUSD", "USOIL", "USTEC"}


def _load_bars(symbol: str, start: datetime, end: datetime):
    if symbol in TIER2_FIELDS:
        df = pd.read_parquet(TIER2_STORE / f"{symbol}_H4.parquet")
    else:
        df = pd.read_parquet(TIER1_CACHE / f"{symbol}_H4.parquet")
    bars = df_to_bars(df, Timeframe.H4)
    return filter_bars_by_date(bars, start=start, end=end)


def _set_symbols(symbol: str) -> None:
    """Point every proposer's universe at the study field (before
    build_roster). Only the study agent survives the proposer filter,
    but the shim keeps roster construction happy."""
    import agent.squad.agents.a01_isagi as a01
    import agent.squad.agents.a02_bachira as a02
    import agent.squad.agents.a03_rin as a03
    import agent.squad.agents.a04_chigiri as a04
    import agent.squad.agents.a05_reo as a05
    import agent.squad.agents.a06_nagi as a06
    import agent.squad.agents.a07_barou as a07
    import agent.squad.agents.a10_kunigami as a10
    import agent.squad.roster as roster_mod

    syms = (symbol,)
    a01.ISAGI_V1_SYMBOLS = syms
    a02.BACHIRA_V1_SYMBOLS = syms
    a03.RIN_V1_SYMBOLS = syms
    a04.CHIGIRI_V1_SYMBOLS = syms
    a05.REO_V1_SYMBOLS = syms
    a06.NAGI_V1_SYMBOLS = syms
    a07.BAROU_V1_SYMBOLS = syms
    a10.KUNIGAMI_V1_SYMBOLS = syms
    roster_mod.DEFAULT_SYMBOLS = syms


def _run_one(agent_id: str, symbol: str, start_iso: str, end_iso: str,
             out_dir: Path) -> dict:
    from agent.squad.engine import SquadEngine
    from agent.squad.roster import build_roster

    _set_symbols(symbol)
    start = datetime.fromisoformat(start_iso).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(end_iso).replace(tzinfo=timezone.utc)
    bars = _load_bars(symbol, start, end)

    roster = build_roster()
    roster.proposers = [a for a in roster.proposers
                        if a.agent_id == agent_id]
    assert len(roster.proposers) == 1, (
        f"isolation filter failed for {agent_id}: "
        f"{[a.agent_id for a in roster.proposers]}")

    out_dir.mkdir(parents=True, exist_ok=True)
    engine = SquadEngine(roster, out_dir, aggregator_arm="phi41",
                         source_label=f"phase_an:{agent_id}:{symbol}:{start_iso}",
                         equity=EQUITY)
    t0 = time.time()
    stats = engine.run_batch({symbol: bars})
    n_trades = stats.get("n_trades", 0)
    print(f"  {agent_id}:{symbol} start={start_iso} bars={len(bars)} "
          f"trades={n_trades} ({time.time()-t0:.0f}s)", flush=True)
    return {"start": start_iso, "end": end_iso, "bars": len(bars),
            "run_batch": {k: stats[k] for k in
                          ("bars_processed", "n_proposals",
                           "n_rejected", "n_trades")}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("design", "sealed"), required=True)
    ap.add_argument("--studies", nargs="*", default=list(STUDIES))
    args = ap.parse_args()

    starts, end = ((DESIGN_STARTS, DESIGN_END) if args.phase == "design"
                   else (SEALED_STARTS, SEALED_END))

    for study in args.studies:
        spec = STUDIES[study]
        for field in spec["fields"]:
            manifest = []
            for k, start_iso in enumerate(starts):
                out = (HERE / "results" / study / field / args.phase
                       / f"start_{k}")
                if (out / "trades.jsonl").exists() or (out / "state.json").exists():
                    print(f"  skip existing {out}", flush=True)
                    continue
                manifest.append(_run_one(spec["agent"], field, start_iso,
                                         end, out))
            mpath = (HERE / "results" / study / field
                     / f"{args.phase}_manifest.json")
            mpath.parent.mkdir(parents=True, exist_ok=True)
            mpath.write_text(json.dumps(manifest, indent=2))
        print(f"{study} {args.phase} complete", flush=True)
    print("ALL_DONE", flush=True)


if __name__ == "__main__":
    main()
