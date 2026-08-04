"""Phase AL field survey: full squad on the four never-played Tier-1
pairs, design region only (2015-01-01 -> 2022-12-31).

    python run_phase_al.py --out-dir results/raw/survey \
        --kpi-out results/survey.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PRODUCT_REPO = Path("/Users/the1finix/Documents/GitHub/multi-pair-trading-agent-product")
CACHE_ROOT = Path("/Users/the1finix/Documents/GitHub/multi-pair-trading-agent/data/parquet")
SURVEY_SYMBOLS = ("AUDUSD", "NZDUSD", "USDJPY", "USDCHF")
DESIGN_START = "2015-01-01"
DESIGN_END = "2022-12-31"  # 2023+ sealed per DATA_LEDGER rule 4

sys.path.insert(0, str(PRODUCT_REPO))

from agent.data.source import ParquetCache  # noqa: E402
from agent.data.loader import df_to_bars, filter_bars_by_date  # noqa: E402
from agent.types import Timeframe  # noqa: E402


def _expand_all_agents() -> None:
    """Point every proposer's symbol universe at the survey pairs
    BEFORE build_roster()."""
    import agent.squad.agents.a01_isagi as a01
    import agent.squad.agents.a02_bachira as a02
    import agent.squad.agents.a03_rin as a03
    import agent.squad.agents.a04_chigiri as a04
    import agent.squad.agents.a05_reo as a05
    import agent.squad.agents.a06_nagi as a06
    import agent.squad.agents.a07_barou as a07
    import agent.squad.agents.a10_kunigami as a10
    import agent.squad.roster as roster_mod

    a01.ISAGI_V1_SYMBOLS = SURVEY_SYMBOLS
    a02.BACHIRA_V1_SYMBOLS = SURVEY_SYMBOLS
    a03.RIN_V1_SYMBOLS = SURVEY_SYMBOLS
    a04.CHIGIRI_V1_SYMBOLS = SURVEY_SYMBOLS
    a05.REO_V1_SYMBOLS = SURVEY_SYMBOLS
    a06.NAGI_V1_SYMBOLS = SURVEY_SYMBOLS
    a07.BAROU_V1_SYMBOLS = SURVEY_SYMBOLS
    a10.KUNIGAMI_V1_SYMBOLS = SURVEY_SYMBOLS
    roster_mod.DEFAULT_SYMBOLS = SURVEY_SYMBOLS


def _pip(symbol: str) -> float:
    return 0.01 if symbol.endswith("JPY") else 0.0001


def _kpis(trades: list[dict]) -> dict:
    n = len(trades)
    wins = [t for t in trades if (t.get("pnl_pips") or 0) > 0]
    gw = sum(t.get("pnl_pips") or 0 for t in wins)
    gl = -sum(t.get("pnl_pips") or 0 for t in trades if (t.get("pnl_pips") or 0) <= 0)
    rs = [t.get("r_multiple") for t in trades if t.get("r_multiple") is not None]
    return {
        "n_trades": n,
        "win_rate": round(len(wins) / n, 4) if n else None,
        "total_pips": round(sum(t.get("pnl_pips") or 0 for t in trades), 1),
        "profit_factor": round(gw / gl, 3) if gl > 0 else None,
        "mean_r": round(sum(rs) / len(rs), 4) if rs else None,
        "total_r": round(sum(rs), 2) if rs else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--kpi-out", type=Path, required=True)
    args = ap.parse_args()

    _expand_all_agents()

    from agent.squad.engine import SquadEngine
    from agent.squad.roster import build_roster

    start = datetime.fromisoformat(DESIGN_START).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(DESIGN_END).replace(tzinfo=timezone.utc)
    cache = ParquetCache(CACHE_ROOT)
    bars_by_symbol = {}
    for sym in SURVEY_SYMBOLS:
        bars = df_to_bars(cache.load(sym, Timeframe.H4), Timeframe.H4)
        bars = filter_bars_by_date(bars, start=start, end=end)
        bars_by_symbol[sym] = bars
        print(f"{sym}: {len(bars)} bars "
              f"({bars[0].time.date()} -> {bars[-1].time.date()})", flush=True)

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = SquadEngine(build_roster(), out_dir,
                         aggregator_arm="phi41", source_label="phase_al_survey")
    stats = engine.run_batch(bars_by_symbol)
    print("run_batch stats:", {k: stats[k] for k in
          ("bars_processed", "n_proposals", "n_rejected", "n_trades")}, flush=True)

    trades = []
    tpath = out_dir / "trades.jsonl"
    if tpath.exists():
        trades = [json.loads(l) for l in
                  tpath.read_text(encoding="utf-8").splitlines() if l.strip()]
    cell = defaultdict(list)
    for t in trades:
        cell[(t.get("agent_id") or "?", t.get("symbol") or "?")].append(t)

    out = {
        "window": [DESIGN_START, DESIGN_END],
        "symbols": list(SURVEY_SYMBOLS),
        "run_batch": {k: stats[k] for k in
                      ("bars_processed", "n_proposals", "n_rejected", "n_trades")},
        "squad": _kpis(trades),
        "per_agent_symbol": {
            f"{a}:{s}": _kpis(v) for (a, s), v in sorted(cell.items())},
    }
    args.kpi_out.parent.mkdir(parents=True, exist_ok=True)
    args.kpi_out.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {args.kpi_out}", flush=True)


if __name__ == "__main__":
    main()
