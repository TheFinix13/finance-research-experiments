"""Phase AK-2: capture Reo's mirror thoughts in a standard replay,
then counterfactually execute the mirrored leader plans.

    python run_phase_ak2.py --start 2019-01-01 --end 2023-12-31 \
        --out-dir results/raw/ak2 --results-dir results
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
FILL_TTL_BARS = 6
TIMEOUT_BARS = 60

sys.path.insert(0, str(PRODUCT_REPO))

from agent.data.source import ParquetCache  # noqa: E402
from agent.data.loader import df_to_bars, filter_bars_by_date  # noqa: E402
from agent.types import Timeframe  # noqa: E402


def _pip(symbol: str) -> float:
    return 0.01 if symbol.endswith("JPY") else 0.0001


def _capture_mirrors(sink: list[dict]) -> None:
    """Wrap A5ReoV1.observe so every mirror Thought is teed to sink."""
    from agent.squad.agents import a05_reo

    original = a05_reo.A5ReoV1.observe

    def observed(self, market, ledger):
        thought = original(self, market, ledger)
        if thought.coordinate is not None:
            lr = thought.coordinate.rationale.get("leader_rationale", {})
            sink.append({
                "tick_id": thought.tick_id,
                "timestamp": thought.timestamp.isoformat(),
                "symbol": thought.symbol,
                "direction": thought.coordinate.direction_bias,
                "leader": thought.coordinate.rationale.get("mirrored_agent_id"),
                "conviction": thought.confidence_in_thought,
                "entry": lr.get("entry"),
                "stop": lr.get("stop"),
                "take_profit": lr.get("take_profit"),
            })
        return thought

    a05_reo.A5ReoV1.observe = observed


def _simulate(mirror: dict, bars: list) -> dict | None:
    """Deterministic counterfactual per PROTOCOL: fill within 6 bars,
    stop-first tie-break, 60-bar timeout."""
    entry, stop, tp = mirror["entry"], mirror["stop"], mirror["take_profit"]
    if entry is None or stop is None or tp is None or entry == stop:
        return None
    t0 = datetime.fromisoformat(mirror["timestamp"])
    start_idx = next((i for i, b in enumerate(bars) if b.time > t0), None)
    if start_idx is None:
        return None
    is_long = mirror["direction"] == "long"

    fill_idx = None
    for i in range(start_idx, min(start_idx + FILL_TTL_BARS, len(bars))):
        if bars[i].low <= entry <= bars[i].high:
            fill_idx = i
            break
    if fill_idx is None:
        return {"filled": False}

    exit_price = None
    for i in range(fill_idx, min(fill_idx + TIMEOUT_BARS, len(bars))):
        b = bars[i]
        hit_stop = (b.low <= stop) if is_long else (b.high >= stop)
        hit_tp = (b.high >= tp) if is_long else (b.low <= tp)
        if hit_stop:            # stop wins ties (conservative, declared)
            exit_price = stop
            break
        if hit_tp:
            exit_price = tp
            break
    if exit_price is None:
        last = bars[min(fill_idx + TIMEOUT_BARS, len(bars)) - 1]
        exit_price = last.close

    sign = 1.0 if is_long else -1.0
    risk = abs(entry - stop)
    pnl = sign * (exit_price - entry)
    return {
        "filled": True,
        "pnl_pips": pnl / _pip(mirror["symbol"]),
        "r_multiple": pnl / risk,
    }


def _kpis(trades: list[dict]) -> dict:
    n = len(trades)
    wins = [t for t in trades if t["pnl_pips"] > 0]
    gw = sum(t["pnl_pips"] for t in wins)
    gl = -sum(t["pnl_pips"] for t in trades if t["pnl_pips"] <= 0)
    return {
        "n": n,
        "win_rate": round(len(wins) / n, 4) if n else None,
        "profit_factor": round(gw / gl, 3) if gl > 0 else None,
        "mean_r": round(sum(t["r_multiple"] for t in trades) / n, 4) if n else None,
        "total_r": round(sum(t["r_multiple"] for t in trades), 2) if n else None,
        "total_pips": round(sum(t["pnl_pips"] for t in trades), 1) if n else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--results-dir", type=Path, required=True)
    args = ap.parse_args()

    mirrors: list[dict] = []
    _capture_mirrors(mirrors)

    from agent.squad.engine import SquadEngine
    from agent.squad.roster import build_roster

    start = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)
    cache = ParquetCache(CACHE_ROOT)
    bars_by_symbol = {}
    for sym in SYMBOLS:
        bars = df_to_bars(cache.load(sym, Timeframe.H4), Timeframe.H4)
        bars_by_symbol[sym] = filter_bars_by_date(bars, start=start, end=end)
        print(f"{sym}: {len(bars_by_symbol[sym])} bars", flush=True)

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = SquadEngine(build_roster(), out_dir,
                         aggregator_arm="phi41", source_label="phase_ak2")
    stats = engine.run_batch(bars_by_symbol)
    print(f"replay done: {stats.get('n_trades')} squad trades, "
          f"{len(mirrors)} Reo mirrors captured", flush=True)

    results_dir = args.results_dir.resolve()
    results_dir.mkdir(parents=True, exist_ok=True)
    with open(results_dir / "mirrors.jsonl", "w", encoding="utf-8") as fh:
        for m in mirrors:
            fh.write(json.dumps(m) + "\n")

    executed, unfilled, skipped = [], 0, 0
    for m in mirrors:
        res = _simulate(m, bars_by_symbol[m["symbol"]])
        if res is None:
            skipped += 1
        elif not res["filled"]:
            unfilled += 1
        else:
            executed.append({**m, **res})

    by_leader = defaultdict(list)
    by_symbol = defaultdict(list)
    for t in executed:
        by_leader[t["leader"] or "unknown"].append(t)
        by_symbol[t["symbol"]].append(t)

    out = {
        "window": [args.start, args.end],
        "n_mirrors": len(mirrors),
        "n_skipped_no_plan": skipped,
        "n_unfilled": unfilled,
        "n_executed": len(executed),
        "overall": _kpis(executed),
        "per_leader": {k: _kpis(v) for k, v in sorted(by_leader.items())},
        "per_symbol": {k: _kpis(v) for k, v in sorted(by_symbol.items())},
    }
    (results_dir / "striker_kpis.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out["overall"], indent=2), flush=True)


if __name__ == "__main__":
    main()
