"""E032 — with-trend H4 breakout-continuation cell.

12 pre-registered cells: 3 symbols x N in {10, 20} x k in {1.0, 1.5}.

Entry (evaluated at H4 bar close, causal):
  * D1 bias from the PRODUCTION `htf_bias_at` helper (read-only import;
    lookback 10, min-move 60p — the deployed cell's exact parameters),
    required to MATCH the breakout direction ("with" mode).
  * Long: bar close > max(high of prior N bars); short mirrored on min(low).
  * Impulse filter: bar range (high - low) >= k * ATR14 (SMA of true range).
  * cap=1 per cell: signals while a trade is open are dropped.

Exit: SL = signal-bar low (long) / high (short), floored at 10p from
entry; TP = entry +/- 1.5R. Intrabar touch fills, SL-first tie-break.
Entry at the signal bar's CLOSE (breakout close is the trigger; no
next-bar-open delay — declared in PROTOCOL §3).

Costs: round-trip spread per trade (1.0/1.5/2.0p); stress arm doubles it.

Usage (from repo root):
    PYTHONPATH=../multi-pair-trading-agent:. \
        ../multi-pair-trading-agent/.venv/bin/python \
        programs/E032/run_e032.py --stage screen \
        --output programs/E032/results_screen.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent.alphas.concepts._htf import HTFBias, htf_bias_at  # noqa: E402
from agent.config import load_config  # noqa: E402
from agent.data.loader import BarLoader, df_to_bars  # noqa: E402
from agent.types import Timeframe  # noqa: E402

SYMBOLS = ("EURUSD", "GBPUSD", "USDCAD")
N_GRID = (10, 20)
K_GRID = (1.0, 1.5)
SPREAD_RT_PIPS = {"EURUSD": 1.0, "GBPUSD": 1.5, "USDCAD": 2.0}
PIP = 0.0001
ATR_PERIOD = 14
TARGET_RR = 1.5
MIN_STOP_PIPS = 10.0
HTF_LOOKBACK = 10
HTF_MIN_MOVE_PIPS = 60.0
WARMUP_DAYS = 90
MIN_TRADES_GATE = 100

STAGES = {
    "screen": (datetime(2015, 1, 1, tzinfo=timezone.utc),
               datetime(2021, 12, 31, tzinfo=timezone.utc)),
    "confirm": (datetime(2022, 1, 1, tzinfo=timezone.utc),
                datetime(2024, 12, 31, tzinfo=timezone.utc)),
    "sealed": (datetime(2025, 1, 1, tzinfo=timezone.utc),
               datetime(2026, 7, 25, tzinfo=timezone.utc)),
}


@dataclass
class CellTrade:
    entry_time: datetime
    direction: str
    entry: float
    stop: float
    tp: float
    exit_time: datetime | None = None
    exit_price: float | None = None
    reason: str = ""

    def pnl_pips_net(self, spread_rt: float) -> float:
        raw = ((self.exit_price - self.entry) if self.direction == "long"
               else (self.entry - self.exit_price)) / PIP
        return raw - spread_rt


def atr_series(bars) -> np.ndarray:
    """SMA of true range over ATR_PERIOD; index i = ATR known at close i."""
    n = len(bars)
    tr = np.empty(n)
    tr[0] = bars[0].high - bars[0].low
    for i in range(1, n):
        h, l, pc = bars[i].high, bars[i].low, bars[i - 1].close
        tr[i] = max(h - l, abs(h - pc), abs(l - pc))
    atr = np.full(n, np.nan)
    if n >= ATR_PERIOD:
        c = np.cumsum(tr)
        atr[ATR_PERIOD - 1:] = (c[ATR_PERIOD - 1:] -
                                np.concatenate(([0.0], c[:-ATR_PERIOD]))) / ATR_PERIOD
    return atr


def run_cell(bars, start_index: int, n_lookback: int, k_atr: float,
             spread_rt: float) -> list[CellTrade]:
    atr = atr_series(bars)
    highs = np.array([b.high for b in bars])
    lows = np.array([b.low for b in bars])
    trades: list[CellTrade] = []
    open_trade: CellTrade | None = None

    for i in range(max(start_index, n_lookback + 1, ATR_PERIOD), len(bars)):
        bar = bars[i]

        if open_trade is not None:
            long = open_trade.direction == "long"
            hit_sl = (bar.low <= open_trade.stop) if long else (bar.high >= open_trade.stop)
            hit_tp = (bar.high >= open_trade.tp) if long else (bar.low <= open_trade.tp)
            if hit_sl:  # SL-first conservative tie-break
                open_trade.exit_time, open_trade.exit_price, open_trade.reason = \
                    bar.time, open_trade.stop, "sl"
                trades.append(open_trade)
                open_trade = None
            elif hit_tp:
                open_trade.exit_time, open_trade.exit_price, open_trade.reason = \
                    bar.time, open_trade.tp, "tp"
                trades.append(open_trade)
                open_trade = None
            if open_trade is not None:
                continue  # cap=1: no new entry while open

        if np.isnan(atr[i]) or atr[i] <= 0:
            continue
        if (bar.high - bar.low) < k_atr * atr[i]:
            continue

        prior_high = highs[i - n_lookback:i].max()
        prior_low = lows[i - n_lookback:i].min()
        direction = None
        if bar.close > prior_high:
            direction = "long"
        elif bar.close < prior_low:
            direction = "short"
        if direction is None:
            continue

        bias = htf_bias_at(bars, i, htf="D1", htf_lookback=HTF_LOOKBACK,
                           min_move_pips=HTF_MIN_MOVE_PIPS)
        if direction == "long" and bias is not HTFBias.UP:
            continue
        if direction == "short" and bias is not HTFBias.DOWN:
            continue

        entry = bar.close
        if direction == "long":
            stop = min(bar.low, entry - MIN_STOP_PIPS * PIP)
            tp = entry + TARGET_RR * (entry - stop)
        else:
            stop = max(bar.high, entry + MIN_STOP_PIPS * PIP)
            tp = entry - TARGET_RR * (stop - entry)
        open_trade = CellTrade(entry_time=bar.time, direction=direction,
                               entry=entry, stop=stop, tp=tp)

    # open trade at end-of-data: discard (unresolved, excluded per protocol)
    return trades


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def bootstrap_p_mean_pos(pips: np.ndarray, n_boot: int = 10000,
                         seed: int = 32) -> float:
    """One-sided bootstrap p-value for H1: mean > 0."""
    rng = np.random.default_rng(seed)
    n = len(pips)
    means = pips[rng.integers(0, n, size=(n_boot, n))].mean(axis=1)
    return float((means <= 0).mean())


def fold_means(pips_by_time: list[tuple[datetime, float]],
               n_folds: int = 5) -> list[float]:
    n = len(pips_by_time)
    edges = np.linspace(0, n, n_folds + 1, dtype=int)
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        seg = [p for _, p in pips_by_time[a:b]]
        out.append(float(np.mean(seg)) if seg else float("nan"))
    return out


def bh_fdr(pvals: list[float], alpha: float = 0.05) -> list[bool]:
    m = len(pvals)
    order = sorted(range(m), key=lambda k: pvals[k])
    max_k = -1
    for rank, k in enumerate(order, start=1):
        if pvals[k] <= alpha * rank / m:
            max_k = rank
    passed = [False] * m
    for rank, k in enumerate(order, start=1):
        if rank <= max_k:
            passed[k] = True
    return passed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=list(STAGES), required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    start, end = STAGES[args.stage]

    cfg = load_config()
    loader = BarLoader(cache_root=cfg.data_dir)

    cells = []
    for sym in SYMBOLS:
        df = loader.get(sym, Timeframe.H4, start - timedelta(days=WARMUP_DAYS),
                        end, refresh=False)
        bars = df_to_bars(df, Timeframe.H4)
        start_index = next((i for i, b in enumerate(bars) if b.time >= start),
                           len(bars))
        for n_lb in N_GRID:
            for k in K_GRID:
                trades = run_cell(bars, start_index, n_lb, k,
                                  SPREAD_RT_PIPS[sym])
                cells.append((sym, n_lb, k, trades))
                print(f"{sym} N={n_lb} k={k}: {len(trades)} trades")

    out = {"stage": args.stage,
           "window": [start.isoformat(), end.isoformat()],
           "cells": {}}
    pvals, rows = [], []
    for sym, n_lb, k, trades in cells:
        name = f"{sym}_N{n_lb}_k{k}"
        spread = SPREAD_RT_PIPS[sym]
        pips = np.array([t.pnl_pips_net(spread) for t in trades])
        pips_stress = np.array([t.pnl_pips_net(2 * spread) for t in trades])
        row = {"symbol": sym, "n_lookback": n_lb, "k_atr": k,
               "n_trades": len(trades)}
        if len(trades) >= 2:
            seq = [(t.entry_time, float(p)) for t, p in zip(trades, pips)]
            folds = fold_means(seq)
            row.update({
                "hit_rate": float((pips > 0).mean()),
                "mean_pips": float(pips.mean()),
                "median_pips": float(np.median(pips)),
                "sum_pips": float(pips.sum()),
                "p_one_sided": bootstrap_p_mean_pos(pips),
                "mean_pips_stress2x": float(pips_stress.mean()),
                "folds_mean": folds,
                "folds_positive": sum(1 for f in folds if f > 0),
            })
        else:
            row.update({"hit_rate": None, "mean_pips": None,
                        "median_pips": None, "sum_pips": 0.0,
                        "p_one_sided": 1.0, "mean_pips_stress2x": None,
                        "folds_mean": [], "folds_positive": 0})
        out["cells"][name] = row
        pvals.append(row["p_one_sided"])
        rows.append((name, row))

    passed = bh_fdr(pvals)
    for (name, row), ok in zip(rows, passed):
        row["bh_fdr_pass"] = bool(ok)
        if row["n_trades"] < MIN_TRADES_GATE:
            verdict = "parked_insufficient_n"
        elif (ok and row["mean_pips"] is not None and row["mean_pips"] > 0
              and row["folds_positive"] >= 4
              and row["mean_pips_stress2x"] is not None
              and row["mean_pips_stress2x"] > 0):
            verdict = "alive"
        elif ok and row["mean_pips"] and row["mean_pips"] > 0:
            verdict = "parked_fragile"  # BH pass but folds/stress fail
        else:
            verdict = "dead"
        row["verdict"] = verdict
        print(f"{name}: n={row['n_trades']} mean={row['mean_pips']} "
              f"p={row['p_one_sided']:.4f} BH={'PASS' if ok else 'fail'} "
              f"folds+ {row['folds_positive']}/5 -> {verdict}")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(out, indent=2))
    print(f"\nwrote {args.output}")


if __name__ == "__main__":
    main()
