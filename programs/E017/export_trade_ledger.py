"""E017 Phase 2 — export the deployed cell's per-trade R ledger.

Re-runs the E013 A/B harness (`scripts/run_walk_forward_ab.py`) with the
production-matching ``all_on`` toggles (wick-proof + BE migration + PLG) on
the deployed EURUSD/H4 ``zone_d1_against`` cell, and writes a per-trade
ledger with R multiples (pnl_pips / original stop_pips) to JSON.

This is the bootstrap source pre-registered in
``experiments/E017_confidence_gated_cooldown/PROTOCOL.md`` §4
("bootstrapped from the deployed cell's own trade R-distribution
(E004/E013 trade ledger)"). E013's ``results.json`` stores only window
aggregates, so the ledger is regenerated here from the same harness and
the same production parquet cache — read-only reuse, no production code
touched.

CLI::

    PYTHONPATH=../multi-pair-trading-agent:.:scripts \
        ../multi-pair-trading-agent/.venv/bin/python \
        programs/E017/export_trade_ledger.py \
        --symbol EURUSD \
        --output programs/E017/data/trade_ledger_EURUSD_H4.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
sys.path.insert(0, str(_REPO_ROOT))

from run_walk_forward_ab import (  # noqa: E402
    FULL_END,
    FULL_START,
    ArmToggles,
    PlgConfig,
    _make_alpha,
    _run_alpha_ab,
)

from agent.config import load_config  # noqa: E402
from agent.data.loader import BarLoader, df_to_bars  # noqa: E402
from agent.rules.engine import precompute  # noqa: E402
from agent.types import Timeframe  # noqa: E402
from agent.utils import to_pips  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--timeframe", default="H4")
    parser.add_argument("--alpha", default="zone_d1_against")
    parser.add_argument(
        "--output",
        default="programs/E017/data/trade_ledger_EURUSD_H4.json",
    )
    args = parser.parse_args()

    cfg = load_config()
    cfg.symbol = args.symbol
    tf = Timeframe(args.timeframe)

    loader = BarLoader(cache_root=cfg.data_dir)
    print(f"Loading {args.symbol} {tf.value} bars {FULL_START.year}-{FULL_END.year} ...")
    df = loader.get(args.symbol, tf, FULL_START, FULL_END, refresh=False)
    bars = df_to_bars(df, tf)
    print(f"  {len(bars):,} bars")

    print("Precomputing detector context ...")
    ctx = precompute(bars, cfg)

    # Production-matching toggles (E013 "all_on" arm).
    toggles = ArmToggles(
        wick_proof_enabled=True,
        be_migration_enabled=True,
        plg_enabled=True,
        plg_cfg=PlgConfig(),
        record_plg_blocks=False,
    )
    alpha = _make_alpha(cfg, args.alpha)
    print("Running all_on backtest ...")
    run = _run_alpha_ab(alpha, bars, cfg, ctx=ctx, start_index=200, toggles=toggles)
    print(f"  {len(run.trades):,} trades")

    ledger = []
    for t in run.trades:
        stop_pips = to_pips(abs(t.setup.entry - t.setup.stop))
        if stop_pips <= 0:
            continue
        pnl_pips = float(t.pnl_pips or 0.0)
        ledger.append(
            {
                "entry_time": t.entry_time.isoformat(),
                "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                "direction": t.direction.value,
                "stop_pips": round(stop_pips, 2),
                "pnl_pips": round(pnl_pips, 2),
                "r": round(pnl_pips / stop_pips, 4),
                "exit_reason": t.exit_reason,
            }
        )

    rs = [row["r"] for row in ledger]
    wins = sum(1 for r in rs if r > 0)
    payload = {
        "meta": {
            "symbol": args.symbol,
            "timeframe": tf.value,
            "alpha": args.alpha,
            "toggles": "all_on (wick_proof + be_migration + plg) — production-matching",
            "harness": "scripts/run_walk_forward_ab.py::_run_alpha_ab (E013, read-only reuse)",
            "full_start": FULL_START.isoformat(),
            "full_end": FULL_END.isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "n_trades": len(ledger),
            "hit_rate": round(wins / len(ledger), 4) if ledger else None,
            "mean_r": round(statistics.fmean(rs), 4) if rs else None,
            "median_r": round(statistics.median(rs), 4) if rs else None,
            "min_r": round(min(rs), 4) if rs else None,
            "max_r": round(max(rs), 4) if rs else None,
        },
        "trades": ledger,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1))
    print(f"Wrote {out} ({len(ledger)} trades)")
    print(json.dumps(payload["meta"], indent=1))


if __name__ == "__main__":
    main()
