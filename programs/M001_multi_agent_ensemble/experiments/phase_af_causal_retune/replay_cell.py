"""Phase AF single sweep cell: one squad replay under a swept config.

Run in its OWN process per cell (module-constant patches and the
lru_cached Config must never leak between cells):

    python replay_cell.py --impulse 40 --rr-delta 0.5 \
        --start 2019-01-01 --end 2023-12-31 \
        --label is_cell_40_0.5 --out-dir results/raw/is_cell_40_0.5

Semantics come from the PRODUCT worktree (causal D138 detector). The
swept knobs are applied BEFORE build_roster() so every agent constructs
against them:
  * cfg.detectors.zone_min_impulse_pips -- mutated in place on the
    lru_cached Config instance (precompute reads it per prepare()).
  * rr_delta -- added to each zone-lineage agent's own locked
    target_rr via the module-level param dicts/constants.
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

from agent.config import load_config  # noqa: E402
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


def _apply_sweep(impulse: float, rr_delta: float) -> dict:
    """Mutate config + agent param dicts in this process. Returns the
    applied per-agent RR map for the manifest."""
    cfg = load_config()  # lru_cached singleton -- every agent sees this
    cfg.detectors.zone_min_impulse_pips = float(impulse)

    import agent.squad.agents.a01_isagi as a01
    import agent.squad.agents.a02_bachira as a02
    import agent.squad.agents.a03_rin as a03
    import agent.squad.agents.a04_chigiri as a04
    import agent.squad.agents.a07_barou as a07

    applied: dict[str, float] = {}
    for mod, dict_name, agent_name in (
        (a01, "ISAGI_V1_PARAMS", "isagi"),
        (a02, "BACHIRA_V1_PARAMS", "bachira"),
        (a03, "RIN_V1_PARAMS", "rin"),
        (a07, "BAROU_V13_PARAMS", "barou_v13"),
        (a07, "BAROU_V1_PARAMS", "barou_v1"),
    ):
        params = getattr(mod, dict_name, None)
        if params is not None and "target_rr" in params:
            params["target_rr"] = float(params["target_rr"]) + rr_delta
            applied[agent_name] = params["target_rr"]
    a04.CHIGIRI_V1_TARGET_RR = float(a04.CHIGIRI_V1_TARGET_RR) + rr_delta
    applied["chigiri"] = a04.CHIGIRI_V1_TARGET_RR
    return applied


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--impulse", type=float, required=True)
    ap.add_argument("--rr-delta", type=float, required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--kpi-out", type=Path, required=True)
    args = ap.parse_args()

    applied_rr = _apply_sweep(args.impulse, args.rr_delta)

    # Imported AFTER the sweep is applied: roster/engine construction
    # must observe the mutated config and param dicts.
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

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = SquadEngine(
        build_roster(),
        out_dir,
        aggregator_arm="phi41",
        source_label=f"phase_af:{args.label}",
    )
    stats = engine.run_batch(bars_by_symbol)
    print("run_batch stats:", stats, flush=True)

    trades: list[dict] = []
    tpath = out_dir / "trades.jsonl"
    if tpath.exists():
        for line in tpath.read_text(encoding="utf-8").splitlines():
            if line.strip():
                trades.append(json.loads(line))
    by_agent: dict[str, list[dict]] = defaultdict(list)
    for t in trades:
        by_agent[t.get("agent_id") or t.get("agent") or "unknown"].append(t)

    out = {
        "label": args.label,
        "impulse": args.impulse,
        "rr_delta": args.rr_delta,
        "applied_rr": applied_rr,
        "window": [args.start, args.end],
        "run_batch": stats,
        "squad": _kpis(trades),
        "per_agent": {k: _kpis(v) for k, v in sorted(by_agent.items())},
    }
    args.kpi_out.parent.mkdir(parents=True, exist_ok=True)
    args.kpi_out.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {args.kpi_out}", flush=True)


if __name__ == "__main__":
    main()
