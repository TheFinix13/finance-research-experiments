"""Phase AJ replay: symbol-restricted agents expanded to all pairs.

Run in its own process (module-constant patches must not leak):

    python run_phase_aj.py --start 2019-01-01 --end 2023-12-31 \
        --label is_expanded --out-dir results/raw/is_expanded \
        --kpi-out results/is_expanded.json

No knobs are swept: deployed configs only. The ONLY change vs the
live roster is that Rin/Barou/Chigiri's natural symbol lists are
expanded to all three pairs BEFORE build_roster() so construction and
prepare() observe the expansion.
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
SYMBOLS = ("EURUSD", "GBPUSD", "USDCAD")

sys.path.insert(0, str(PRODUCT_REPO))

from agent.data.source import ParquetCache  # noqa: E402
from agent.data.loader import df_to_bars, filter_bars_by_date  # noqa: E402
from agent.types import Timeframe  # noqa: E402


def _kpis(trades: list[dict]) -> dict:
    n = len(trades)
    wins = [t for t in trades if (t.get("pnl_pips") or 0) > 0]
    losses = [t for t in trades if (t.get("pnl_pips") or 0) <= 0]
    gross_win = sum(t.get("pnl_pips") or 0 for t in wins)
    gross_loss = -sum(t.get("pnl_pips") or 0 for t in losses)
    rs = [t.get("r_multiple") for t in trades if t.get("r_multiple") is not None]
    return {
        "n_trades": n,
        "win_rate": round(len(wins) / n, 4) if n else None,
        "total_pips": round(sum(t.get("pnl_pips") or 0 for t in trades), 1),
        "profit_factor": round(gross_win / gross_loss, 3) if gross_loss > 0 else None,
        "mean_r": round(sum(rs) / len(rs), 4) if rs else None,
        "total_r": round(sum(rs), 2) if rs else None,
    }


def _expand_symbols() -> dict:
    """Patch the module-level natural-symbol constants BEFORE
    build_roster() so agent construction observes the expansion."""
    import agent.squad.agents.a03_rin as a03
    import agent.squad.agents.a04_chigiri as a04
    import agent.squad.agents.a07_barou as a07

    before = {
        "rin": tuple(a03.RIN_V1_SYMBOLS),
        "chigiri": tuple(a04.CHIGIRI_V1_SYMBOLS),
        "barou": tuple(a07.BAROU_V1_SYMBOLS),
    }
    a03.RIN_V1_SYMBOLS = SYMBOLS
    a04.CHIGIRI_V1_SYMBOLS = SYMBOLS
    a07.BAROU_V1_SYMBOLS = SYMBOLS
    return before


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--kpi-out", type=Path, required=True)
    args = ap.parse_args()

    home_symbols = _expand_symbols()

    from agent.squad.engine import SquadEngine
    from agent.squad.roster import build_roster

    start = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)
    cache = ParquetCache(CACHE_ROOT)
    bars_by_symbol = {}
    for sym in SYMBOLS:
        bars = df_to_bars(cache.load(sym, Timeframe.H4), Timeframe.H4)
        bars = filter_bars_by_date(bars, start=start, end=end)
        bars_by_symbol[sym] = bars
        print(f"{sym}: {len(bars)} bars {bars[0].time:%Y-%m-%d}..{bars[-1].time:%Y-%m-%d}",
              flush=True)

    roster = build_roster()
    for a in roster.proposers:
        print(f"roster: {a.agent_id} symbols={getattr(a, 'symbols', None)}",
              flush=True)

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = SquadEngine(
        roster,
        out_dir,
        aggregator_arm="phi41",
        source_label=f"phase_aj:{args.label}",
    )
    stats = engine.run_batch(bars_by_symbol)
    print("run_batch stats:", stats, flush=True)

    trades: list[dict] = []
    tpath = out_dir / "trades.jsonl"
    if tpath.exists():
        for line in tpath.read_text(encoding="utf-8").splitlines():
            if line.strip():
                trades.append(json.loads(line))

    by_cell: dict[str, list[dict]] = defaultdict(list)
    by_agent: dict[str, list[dict]] = defaultdict(list)
    for t in trades:
        aid = t.get("agent_id") or "unknown"
        by_agent[aid].append(t)
        by_cell[f"{aid}:{t.get('symbol')}"].append(t)

    out = {
        "label": args.label,
        "window": [args.start, args.end],
        "home_symbols_before_expansion": home_symbols,
        "run_batch": stats,
        "squad": _kpis(trades),
        "per_agent": {k: _kpis(v) for k, v in sorted(by_agent.items())},
        "per_agent_symbol": {k: _kpis(v) for k, v in sorted(by_cell.items())},
    }
    args.kpi_out.parent.mkdir(parents=True, exist_ok=True)
    args.kpi_out.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {args.kpi_out}", flush=True)


if __name__ == "__main__":
    main()
