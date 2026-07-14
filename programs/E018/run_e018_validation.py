#!/usr/bin/env python3
"""E018 — regime-aware fade gating: walk-forward validation + gate.

Pipeline (per pair in EURUSD/GBPUSD/USDCAD, H4):
  1. Load bars from the production parquet cache (read-only) and run the
     deployed ``zone_d1_against`` fade via the E013 ``_run_alpha_ab`` harness
     with production-matching ``all_on`` toggles.
  2. Label every trade at its causal SIGNAL bar (entry-bar-index − 1) with the
     FROZEN regime labeller (``programs/E018/regime_labeller.py``).
  3. Split trades into the 7 walk-forward windows (4yr-IS / 1yr-OOS) inherited
     from ``scripts/run_walk_forward.py``; pool OOS = 2019–2025.
  4. Compute regime-conditional OOS expectancy, bootstrap p-values
     (R2 one-sided ``less``; R1 one-sided ``greater``), BH-FDR across the 6
     {pair}×{R1,R2} cells, and the baseline-vs-R2-filtered arm comparison.
  5. Evaluate the pre-registered §5 gate and write ``results.json``.

Run (from the research repo root), single-process/foreground:

    PYTHONPATH=../multi-pair-trading-agent:.:scripts \
        ../multi-pair-trading-agent/.venv/bin/python \
        programs/E018/run_e018_validation.py
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

_LAB_ROOT = Path(__file__).resolve().parents[2]
_AGENT_ROOT = _LAB_ROOT.parent / "multi-pair-trading-agent"
for _p in (str(_AGENT_ROOT), str(_LAB_ROOT), str(_LAB_ROOT / "scripts"),
           str(Path(__file__).resolve().parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agent.backtest.metrics import (  # noqa: E402
    benjamini_hochberg,
    bootstrap_p_value,
    make_scorecard,
)
from agent.config import load_config  # noqa: E402
from agent.data.loader import BarLoader, df_to_bars  # noqa: E402
from agent.rules.engine import precompute  # noqa: E402
from agent.types import Timeframe  # noqa: E402

from run_walk_forward_ab import (  # noqa: E402
    FULL_END,
    FULL_START,
    IS_YEARS,
    OOS_YEARS,
    WINDOW_STARTS,
    ArmToggles,
    PlgConfig,
    _make_alpha,
    _run_alpha_ab,
)

from regime_labeller import (  # noqa: E402
    Regime,
    regime_at,
    wilder_adx,
    wilder_atr,
)

PAIRS = ("EURUSD", "GBPUSD", "USDCAD")
TF = Timeframe.H4
N_RESAMPLES = 2000
SEED = 42
MIN_CELL_N = 30


def _windows() -> list[tuple[datetime, datetime, datetime, datetime]]:
    out = []
    for is_start in WINDOW_STARTS:
        is_end = datetime(is_start.year + IS_YEARS, 1, 1, tzinfo=timezone.utc)
        oos_start = is_end
        oos_end = datetime(oos_start.year + OOS_YEARS, 1, 1, tzinfo=timezone.utc)
        if oos_end > FULL_END:
            oos_end = FULL_END
        out.append((is_start, is_end, oos_start, oos_end))
    return out


def _label_trades(symbol: str, cfg) -> list[dict]:
    """Run the fade and return a per-trade labelled ledger for one pair."""
    loader = BarLoader(cache_root=cfg.data_dir)
    df = loader.get(symbol, TF, FULL_START, FULL_END, refresh=False)
    bars = df_to_bars(df, TF)
    ctx = precompute(bars, cfg)

    toggles = ArmToggles(
        wick_proof_enabled=True, be_migration_enabled=True,
        plg_enabled=True, plg_cfg=PlgConfig(), record_plg_blocks=False,
    )
    alpha = _make_alpha(cfg, "zone_d1_against")
    run = _run_alpha_ab(alpha, bars, cfg, ctx=ctx, start_index=200, toggles=toggles)

    # Precompute causal indicator series once over the full bar list.
    atr = wilder_atr(bars)
    adx = wilder_adx(bars)
    idx_by_time = {b.time: k for k, b in enumerate(bars)}

    ledger: list[dict] = []
    for t in run.trades:
        if t.exit_time is None:
            continue
        entry_idx = idx_by_time.get(t.entry_time)
        if entry_idx is None:
            continue
        signal_idx = max(0, entry_idx - 1)  # decision bar = bar whose close fired
        rr = regime_at(bars, signal_idx, atr=atr, adx=adx)
        ledger.append({
            "symbol": symbol,
            "entry_time": t.entry_time.isoformat(),
            "signal_index": signal_idx,
            "direction": t.direction.value,
            "pnl_pips": float(t.pnl_pips or 0.0),
            "pnl": float(t.pnl or 0.0),
            "exit_reason": t.exit_reason,
            **rr.to_dict(),
        })
    return ledger


def _in_window(iso_time: str, lo: datetime, hi: datetime) -> bool:
    t = datetime.fromisoformat(iso_time)
    return lo <= t < hi


def _cell_stats(rows: list[dict], *, alternative: str) -> dict:
    pnl_pips = [r["pnl_pips"] for r in rows]
    pnl = [r["pnl"] for r in rows]
    n = len(rows)
    if n == 0:
        return {"n": 0, "exp_pips": None, "p": 1.0, "powered": False,
                "hit_rate": None}
    exp_pips = statistics.fmean(pnl_pips)
    p = bootstrap_p_value(pnl, alternative=alternative,
                          n_resamples=N_RESAMPLES, seed=SEED)
    wins = sum(1 for x in pnl_pips if x > 0)
    return {
        "n": n,
        "exp_pips": exp_pips,
        "median_pips": statistics.median(pnl_pips),
        "hit_rate": wins / n,
        "p": p,
        "alternative": alternative,
        "powered": n >= MIN_CELL_N,
    }


def _arm_scorecard(rows: list[dict], initial_balance: float, label: str) -> dict:
    """Scorecard from a list of labelled-trade rows (uses pnl currency)."""
    # Build lightweight trade stand-ins for make_scorecard via pnl only.
    from agent.types import Trade  # local import to avoid confusion

    class _T:  # minimal shim exposing the fields make_scorecard reads
        is_open = False

        def __init__(self, pnl, pnl_pips, exit_time):
            self.pnl = pnl
            self.pnl_pips = pnl_pips
            self.exit_price = 0.0 if exit_time else None
            self.exit_time = exit_time

    stand_ins = [
        _T(r["pnl"], r["pnl_pips"], datetime.fromisoformat(r["entry_time"]))
        for r in rows
    ]
    sc = make_scorecard(label, stand_ins, initial_balance, n_resamples=N_RESAMPLES)
    return {
        "label": label,
        "n": sc.n_trades,
        "expectancy": {"value": sc.expectancy.value, "lo": sc.expectancy.lo,
                       "hi": sc.expectancy.hi},
        "expectancy_pips": (statistics.fmean([r["pnl_pips"] for r in rows])
                            if rows else None),
        "profit_factor": sc.profit_factor.value,
        "win_rate": sc.win_rate.value,
        "sharpe": sc.base.sharpe,
        "max_drawdown_pct": sc.base.max_drawdown_pct,
        "verdict": sc.verdict,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=str(_LAB_ROOT
                    / "experiments/E018_regime_aware_fade_gating/results.json"),
    )
    parser.add_argument(
        "--ledger-out",
        default=str(Path(__file__).resolve().parent / "data" / "labelled_ledger.json"),
    )
    args = parser.parse_args()

    cfg = load_config()
    init_bal = cfg.backtest.initial_balance
    wins = _windows()
    oos_lo = wins[0][2]           # first OOS start (2019-01-01)
    oos_hi = wins[-1][3]          # last OOS end (2025-12-01)
    sealed_lo, sealed_hi = wins[-1][2], wins[-1][3]  # final-year OOS window

    all_ledger: dict[str, list[dict]] = {}
    for sym in PAIRS:
        print(f"[E018] {sym}: running fade + labelling ...", flush=True)
        cfg.symbol = sym
        all_ledger[sym] = _label_trades(sym, cfg)
        n = len(all_ledger[sym])
        r2 = sum(1 for r in all_ledger[sym] if r["regime"] == "R2")
        r1 = sum(1 for r in all_ledger[sym] if r["regime"] == "R1")
        r3 = sum(1 for r in all_ledger[sym] if r["regime"] == "R3")
        print(f"        {n} closed trades  (R1={r1} R2={r2} R3={r3})", flush=True)

    # --- Regime cells on pooled OOS + BH-FDR across the 6 cells --------------
    cells: dict[str, dict] = {}
    bh_labels: list[str] = []
    bh_pvals: list[float] = []
    for sym in PAIRS:
        oos = [r for r in all_ledger[sym] if _in_window(r["entry_time"], oos_lo, oos_hi)]
        for regime, alt in (("R1", "greater"), ("R2", "less")):
            rows = [r for r in oos if r["regime"] == regime]
            st = _cell_stats(rows, alternative=alt)
            key = f"{sym}/{regime}"
            cells[key] = st
            bh_labels.append(key)
            bh_pvals.append(st["p"])
    rejects, qvals = benjamini_hochberg(bh_pvals, fdr=0.05)
    for lbl, rej, q in zip(bh_labels, rejects, qvals):
        cells[lbl]["q"] = q
        cells[lbl]["bh_reject"] = bool(rej)

    # --- Per-window R2 robustness -------------------------------------------
    r2_by_window: dict[str, list[dict]] = {sym: [] for sym in PAIRS}
    for sym in PAIRS:
        for (_, _, os_lo, os_hi) in wins:
            rows = [r for r in all_ledger[sym]
                    if r["regime"] == "R2" and _in_window(r["entry_time"], os_lo, os_hi)]
            exp = statistics.fmean([r["pnl_pips"] for r in rows]) if rows else None
            r2_by_window[sym].append({
                "oos_year": os_lo.year, "n": len(rows), "exp_pips": exp,
                "neg": (exp is not None and exp <= 0),
            })

    # --- Baseline vs R2-filtered arms on pooled OOS (per pair + all) ---------
    arms: dict[str, dict] = {}
    for sym in list(PAIRS) + ["ALL"]:
        if sym == "ALL":
            oos = [r for s in PAIRS for r in all_ledger[s]
                   if _in_window(r["entry_time"], oos_lo, oos_hi)]
        else:
            oos = [r for r in all_ledger[sym] if _in_window(r["entry_time"], oos_lo, oos_hi)]
        baseline = oos
        filtered = [r for r in oos if r["regime"] != "R2"]
        arms[sym] = {
            "baseline": _arm_scorecard(baseline, init_bal, f"{sym}/baseline"),
            "r2_filtered": _arm_scorecard(filtered, init_bal, f"{sym}/r2_filtered"),
            "n_r2_dropped": len(baseline) - len(filtered),
        }

    # --- IS-band descriptive (2015-2018) + sealed 2025 read ------------------
    def _regime_exp(rows, regime):
        r = [x["pnl_pips"] for x in rows if x["regime"] == regime]
        return {"n": len(r), "exp_pips": (statistics.fmean(r) if r else None)}

    is_lo, is_hi = wins[0][0], wins[0][1]  # 2015-01-01 .. 2019-01-01 (first IS)
    descriptive = {}
    sealed = {}
    for sym in PAIRS:
        is_rows = [r for r in all_ledger[sym] if _in_window(r["entry_time"], is_lo, is_hi)]
        sealed_rows = [r for r in all_ledger[sym]
                       if _in_window(r["entry_time"], sealed_lo, sealed_hi)]
        descriptive[sym] = {"R1": _regime_exp(is_rows, "R1"),
                            "R2": _regime_exp(is_rows, "R2")}
        sealed[sym] = {"R1": _regime_exp(sealed_rows, "R1"),
                      "R2": _regime_exp(sealed_rows, "R2")}

    # --- Gate evaluation (PROTOCOL §5) --------------------------------------
    r2_sig_neg = {
        sym: (cells[f"{sym}/R2"]["bh_reject"]
              and cells[f"{sym}/R2"]["exp_pips"] is not None
              and cells[f"{sym}/R2"]["exp_pips"] < 0
              and cells[f"{sym}/R2"]["powered"])
        for sym in PAIRS
    }
    r2_sig_pos_contradiction = {
        sym: (cells[f"{sym}/R2"]["exp_pips"] is not None
              and cells[f"{sym}/R2"]["exp_pips"] > 0
              and cells[f"{sym}/R2"]["bh_reject"])
        for sym in PAIRS
    }
    n_pairs_sig_neg = sum(1 for v in r2_sig_neg.values() if v)
    any_contradiction = any(r2_sig_pos_contradiction.values())

    def _filter_helps(sym: str) -> bool:
        b = arms[sym]["baseline"]
        f = arms[sym]["r2_filtered"]
        if f["n"] < MIN_CELL_N:
            return False
        checks = [
            f["expectancy"]["value"] >= b["expectancy"]["value"],
            f["profit_factor"] >= b["profit_factor"],
            f["sharpe"] >= b["sharpe"],
            f["expectancy"]["lo"] >= b["expectancy"]["lo"],
        ]
        # sample size not destroyed: R1 keeps the majority of trades
        keep_ratio = f["n"] / b["n"] if b["n"] else 0.0
        return all(checks) and keep_ratio >= 0.5

    filter_helps = {sym: _filter_helps(sym) for sym in PAIRS}
    filter_helps_all = _filter_helps("ALL")

    powered_all = all(cells[f"{sym}/R2"]["powered"] for sym in PAIRS)
    condition_1 = n_pairs_sig_neg >= 1 and any(
        cells[f"{sym}/R2"]["powered"] for sym in PAIRS)
    condition_2 = n_pairs_sig_neg >= 2 and not any_contradiction
    condition_3 = filter_helps_all and sum(filter_helps.values()) >= 2

    if condition_1 and condition_2 and condition_3:
        verdict = "alive"
    elif (n_pairs_sig_neg >= 1) and not powered_all:
        verdict = "parked_underpowered"
    elif (n_pairs_sig_neg >= 1) and not condition_3:
        verdict = "dead"  # R2 negative but filtering doesn't help survivors
    else:
        verdict = "dead"

    payload = {
        "meta": {
            "id": "E018",
            "status": "completed",
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "verdict": verdict,
            "pairs": list(PAIRS),
            "timeframe": TF.value,
            "n_resamples": N_RESAMPLES,
            "seed": SEED,
            "min_cell_n": MIN_CELL_N,
            "oos_pooled": [oos_lo.isoformat(), oos_hi.isoformat()],
            "harness": "programs/E018/run_e018_validation.py",
        },
        "gate": {
            "r2_significantly_negative_by_pair": r2_sig_neg,
            "n_pairs_r2_sig_neg": n_pairs_sig_neg,
            "any_r2_sig_positive_contradiction": any_contradiction,
            "filter_helps_by_pair": filter_helps,
            "filter_helps_pooled": filter_helps_all,
            "condition_1_r2_real_neg_edge": condition_1,
            "condition_2_robust_across_pairs": condition_2,
            "condition_3_filter_improves_survivors": condition_3,
            "verdict": verdict,
        },
        "regime_cells_pooled_oos": cells,
        "r2_per_window": r2_by_window,
        "arms_pooled_oos": arms,
        "is_band_descriptive_2015_2018": descriptive,
        "sealed_final_oos_window": {"year": sealed_lo.year, "cells": sealed},
        "counts": {
            sym: {
                "total": len(all_ledger[sym]),
                "R1": sum(1 for r in all_ledger[sym] if r["regime"] == "R1"),
                "R2": sum(1 for r in all_ledger[sym] if r["regime"] == "R2"),
                "R3": sum(1 for r in all_ledger[sym] if r["regime"] == "R3"),
            }
            for sym in PAIRS
        },
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    ledger_out = Path(args.ledger_out)
    ledger_out.parent.mkdir(parents=True, exist_ok=True)
    ledger_out.write_text(json.dumps(all_ledger, indent=1), encoding="utf-8")

    print(f"\n[E018] verdict: {verdict}")
    print(f"[E018] wrote {out_path}")
    print(f"[E018] wrote {ledger_out}")
    for sym in PAIRS:
        c2 = cells[f"{sym}/R2"]
        c1 = cells[f"{sym}/R1"]
        print(f"  {sym}: R2 n={c2['n']} exp={c2['exp_pips']} q={c2.get('q'):.4f} "
              f"reject={c2.get('bh_reject')} | R1 n={c1['n']} exp={c1['exp_pips']}")
    return 0 if verdict == "alive" else 1


if __name__ == "__main__":
    raise SystemExit(main())
