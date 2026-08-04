"""E031 — slot-blocking: position-cap relaxation / queue-replacement.

Portfolio-level replay of the FROZEN production cell (`zone_d1_against`,
H4, EURUSD/GBPUSD/USDCAD) under five slot policies:

  A0  cap=1 per symbol (reconstructed production baseline)
  A1  cap=2 per symbol
  A2  cap=3 per symbol
  B1  cap=1 + replace incumbent when a new signal arrives while the slot
      is full AND the incumbent's unrealized R <= -0.25 (close incumbent
      at next bar open, open the new ticket)
  B2  as B1, replacement only when the new signal is same-direction

Everything EXCEPT the slot policy is identical across arms (signal
stream, sizing, costs, exits, portfolio ceiling), so arm-vs-baseline
deltas isolate the slot mechanics. Baseline is the reconstructed A0
replay, never the production ledger (E026 Amendment-1 convention).

Signal stream: `SupplyDemandAlpha` (production code, read-only import)
driven at EVERY bar — exactly what production's SignalLoop does; the
slot decision is applied by the simulator, not the detector.

Exits: zone-edge SL / fixed 1.5R TP from the signal, re-anchored to the
next-bar-open fill; intrabar touch fills; SL-first tie-break when both
levels lie inside one bar (conservative house convention). No wick-proof
/ BE / PLG layers — identical across arms, so their absence cancels.

Costs: round-trip spread subtracted per closed trade (1.0p EURUSD,
1.5p GBPUSD, 2.0p USDCAD per PROTOCOL §3).

Usage (from repo root):
    PYTHONPATH=../multi-pair-trading-agent:. \
        ../multi-pair-trading-agent/.venv/bin/python \
        programs/E031/run_e031.py --stage screen \
        --output programs/E031/results_screen.json
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent.alphas.base import AlphaContext  # noqa: E402  (agent repo, read-only)
from agent.alphas.concepts import SupplyDemandAlpha  # noqa: E402
from agent.config import load_config  # noqa: E402
from agent.data.loader import BarLoader, df_to_bars  # noqa: E402
from agent.rules.engine import precompute  # noqa: E402
from agent.types import Direction, Timeframe  # noqa: E402

SYMBOLS = ("EURUSD", "GBPUSD", "USDCAD")
RISK_SCALE = {"EURUSD": 1.0, "GBPUSD": 0.5, "USDCAD": 0.5}
SPREAD_RT_PIPS = {"EURUSD": 1.0, "GBPUSD": 1.5, "USDCAD": 2.0}
RISK_FRAC = 0.01
PORTFOLIO_CEILING = 0.05
PIP = 0.0001
PIP_VALUE_PER_LOT = 10.0
INITIAL_BALANCE = 1000.0
REPLACE_R_THRESHOLD = -0.25
WARMUP_DAYS = 365

STAGES = {
    "screen": (datetime(2015, 1, 1, tzinfo=timezone.utc),
               datetime(2021, 12, 31, tzinfo=timezone.utc)),
    "confirm": (datetime(2022, 1, 1, tzinfo=timezone.utc),
                datetime(2024, 12, 31, tzinfo=timezone.utc)),
    "sealed": (datetime(2025, 1, 1, tzinfo=timezone.utc),
               datetime(2026, 7, 25, tzinfo=timezone.utc)),
}

ARM_NAMES = ("A1_cap2", "A2_cap3", "B1_replace_losing", "B2_replace_same_dir")


# ---------------------------------------------------------------------------
# Signal extraction (production detector, read-only)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Sig:
    bar_index: int          # index of the SIGNAL bar (fill at bar_index+1 open)
    time: datetime
    direction: str          # "long" | "short"
    entry: float
    stop: float
    take_profit: float


def extract_signals(symbol: str, start: datetime, end: datetime,
                    ) -> tuple[list, list[Sig]]:
    """Return (bars, signals) for ``symbol`` with warmup prefix.

    Signals are recorded only for bars >= ``start``; the warmup year exists
    so zones / HTF bias have history at the stage boundary.
    """
    cfg = load_config()
    loader = BarLoader(cache_root=cfg.data_dir)
    df = loader.get(symbol, Timeframe.H4,
                    start - timedelta(days=WARMUP_DAYS), end, refresh=False)
    bars = df_to_bars(df, Timeframe.H4)
    alpha = SupplyDemandAlpha(
        cfg, htf_align="D1", htf_align_mode="against",
        htf_lookback=10, htf_min_move_pips=60.0,
    )
    ctx = precompute(bars, cfg)
    actx = AlphaContext(bars=bars, ctx=ctx, cfg=cfg)
    start_index = next((i for i, b in enumerate(bars) if b.time >= start),
                       len(bars))
    signals: list[Sig] = []
    for i in range(start_index, len(bars) - 1):
        sig = alpha.signal(actx, i)
        if sig is None or sig.stop_pips <= 0:
            continue
        signals.append(Sig(
            bar_index=i, time=bars[i].time,
            direction=sig.direction.value,
            entry=sig.entry, stop=sig.stop, take_profit=sig.take_profit,
        ))
    return bars, signals


# ---------------------------------------------------------------------------
# Portfolio simulator
# ---------------------------------------------------------------------------

@dataclass
class Ticket:
    symbol: str
    direction: str
    fill: float
    stop: float
    tp: float
    lots: float
    risk_cur: float
    open_time: datetime

    def unrealized_r(self, price: float) -> float:
        move = (price - self.fill) if self.direction == "long" else (self.fill - price)
        stop_dist = abs(self.fill - self.stop)
        return move / stop_dist if stop_dist > 0 else 0.0

    def open_risk_cur(self) -> float:
        return abs(self.fill - self.stop) / PIP * self.lots * PIP_VALUE_PER_LOT


@dataclass
class SimResult:
    arm: str
    equity: dict          # date -> end-of-day equity
    trades: list          # dicts
    slot_conflicts: dict  # symbol -> count of signals arriving while cap-full
    ceiling_blocks: int
    replacements: int


def _fill_price(sig: Sig, next_bar) -> tuple[float, float, float]:
    """Production _open_at_next_bar recipe minus cost (costs applied at close):
    market fill at next bar open, stop/TP re-anchored to preserve distances."""
    fill = next_bar.open
    stop_dist = abs(sig.entry - sig.stop)
    tp_dist = abs(sig.take_profit - sig.entry)
    if sig.direction == "long":
        return fill, fill - stop_dist, fill + tp_dist
    return fill, fill + stop_dist, fill - tp_dist


def simulate(arm: str, bars_by_sym: dict, sigs_by_sym: dict,
             start: datetime) -> SimResult:
    """Run one arm over the merged 3-symbol timeline."""
    cap = {"A0_cap1": 1, "A1_cap2": 2, "A2_cap3": 3,
           "B1_replace_losing": 1, "B2_replace_same_dir": 1}[arm]
    replace_mode = arm.startswith("B")
    same_dir_only = arm == "B2_replace_same_dir"

    # Merged timeline: (time, symbol, bar_index), chronological.
    timeline: list[tuple[datetime, str, int]] = []
    sig_at: dict[tuple[str, int], Sig] = {}
    for sym, bars in bars_by_sym.items():
        for i, b in enumerate(bars):
            if b.time >= start:
                timeline.append((b.time, sym, i))
        for s in sigs_by_sym[sym]:
            sig_at[(sym, s.bar_index)] = s
    timeline.sort(key=lambda t: (t[0], t[1]))

    balance = INITIAL_BALANCE
    latest_close: dict[str, float] = {}
    open_tickets: dict[str, list[Ticket]] = {s: [] for s in SYMBOLS}
    # entries pend one bar: signal at bar i fills at bar i+1 open
    pending: dict[str, list[Sig]] = {s: [] for s in SYMBOLS}
    pending_replacements: dict[str, list[tuple[Ticket, Sig]]] = {s: [] for s in SYMBOLS}
    trades: list[dict] = []
    equity_by_day: dict = {}
    slot_conflicts = {s: 0 for s in SYMBOLS}
    ceiling_blocks = 0
    replacements = 0

    def total_open_risk() -> float:
        return sum(t.open_risk_cur()
                   for tickets in open_tickets.values() for t in tickets)

    def close_ticket(t: Ticket, price: float, when: datetime, reason: str) -> None:
        nonlocal balance
        raw_pips = ((price - t.fill) if t.direction == "long" else (t.fill - price)) / PIP
        net_pips = raw_pips - SPREAD_RT_PIPS[t.symbol]
        pnl = net_pips * t.lots * PIP_VALUE_PER_LOT
        balance += pnl
        trades.append({
            "symbol": t.symbol, "direction": t.direction,
            "open_time": t.open_time.isoformat(), "close_time": when.isoformat(),
            "fill": t.fill, "exit": price, "reason": reason,
            "pnl_pips_net": net_pips, "pnl_cur": pnl,
            "r": net_pips * PIP / abs(t.fill - t.stop) if t.fill != t.stop else 0.0,
        })

    for when, sym, i in timeline:
        bar = bars_by_sym[sym][i]
        latest_close[sym] = bar.close

        # 1) queued replacements fill at this bar's open
        for incumbent, sig in pending_replacements[sym]:
            if incumbent in open_tickets[sym]:
                open_tickets[sym].remove(incumbent)
                close_ticket(incumbent, bar.open, when, "replaced")
                replacements += 1
                pending[sym].append(sig)
        pending_replacements[sym] = []

        # 2) pending entries fill at this bar's open
        for sig in pending[sym]:
            fill, stop, tp = _fill_price(sig, bar)
            risk_cur = balance * RISK_FRAC * RISK_SCALE[sym]
            stop_pips = abs(fill - stop) / PIP
            if stop_pips <= 0:
                continue
            lots = risk_cur / (stop_pips * PIP_VALUE_PER_LOT)
            ticket = Ticket(sym, sig.direction, fill, stop, tp, lots,
                            risk_cur, when)
            if total_open_risk() + ticket.open_risk_cur() > PORTFOLIO_CEILING * balance:
                ceiling_blocks += 1
                continue
            open_tickets[sym].append(ticket)
        pending[sym] = []

        # 3) exits on this bar (SL-first conservative tie-break)
        surviving: list[Ticket] = []
        for t in open_tickets[sym]:
            long = t.direction == "long"
            hit_sl = (bar.low <= t.stop) if long else (bar.high >= t.stop)
            hit_tp = (bar.high >= t.tp) if long else (bar.low <= t.tp)
            if hit_sl:
                close_ticket(t, t.stop, when, "sl")
            elif hit_tp:
                close_ticket(t, t.tp, when, "tp")
            else:
                surviving.append(t)
        open_tickets[sym] = surviving

        # 4) new signal on this bar close
        key = (sym, i)
        if key in sig_at:
            sig = sig_at[key]
            if len(open_tickets[sym]) < cap:
                pending[sym].append(sig)
            else:
                slot_conflicts[sym] += 1
                if replace_mode and open_tickets[sym]:
                    incumbent = open_tickets[sym][0]  # cap=1 in B arms
                    if same_dir_only and incumbent.direction != sig.direction:
                        pass
                    elif incumbent.unrealized_r(bar.close) <= REPLACE_R_THRESHOLD:
                        pending_replacements[sym].append((incumbent, sig))

        # 5) end-of-day mark-to-market equity (last write per date wins)
        unrealized = 0.0
        for ts in open_tickets.values():
            for t in ts:
                px = latest_close.get(t.symbol, t.fill)
                move = (px - t.fill) if t.direction == "long" else (t.fill - px)
                unrealized += (move / PIP) * t.lots * PIP_VALUE_PER_LOT
        equity_by_day[when.date().isoformat()] = balance + unrealized

    return SimResult(arm=arm, equity=equity_by_day, trades=trades,
                     slot_conflicts=slot_conflicts,
                     ceiling_blocks=ceiling_blocks, replacements=replacements)


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def daily_returns(equity: dict) -> tuple[list[str], np.ndarray]:
    days = sorted(equity)
    vals = np.array([equity[d] for d in days], dtype=float)
    rets = np.diff(vals) / vals[:-1]
    return days[1:], rets


def ann_sharpe(rets: np.ndarray) -> float:
    if len(rets) < 2 or rets.std(ddof=0) == 0:
        return 0.0
    return float(rets.mean() / rets.std(ddof=0) * math.sqrt(252.0))


def max_drawdown(equity: dict) -> float:
    days = sorted(equity)
    vals = np.array([equity[d] for d in days], dtype=float)
    peak = np.maximum.accumulate(vals)
    dd = (vals - peak) / peak
    return float(dd.min())


def block_bootstrap_delta_sharpe(r_arm: np.ndarray, r_base: np.ndarray,
                                 n_boot: int = 5000, block: int = 20,
                                 seed: int = 31) -> tuple[float, float, float, float]:
    """Paired moving-block bootstrap of ΔSharpe. Returns
    (delta, ci_lo, ci_hi, one_sided_p_of_delta_le_0)."""
    n = min(len(r_arm), len(r_base))
    r_arm, r_base = r_arm[:n], r_base[:n]
    delta = ann_sharpe(r_arm) - ann_sharpe(r_base)
    rng = np.random.default_rng(seed)
    n_blocks = max(1, math.ceil(n / block))
    deltas = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, max(1, n - block), size=n_blocks)
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
        deltas[b] = ann_sharpe(r_arm[idx]) - ann_sharpe(r_base[idx])
    ci_lo, ci_hi = np.percentile(deltas, [2.5, 97.5])
    p = float((deltas <= 0).mean())
    return delta, float(ci_lo), float(ci_hi), p


def fold_consistency(days: list[str], r_arm: np.ndarray, r_base: np.ndarray,
                     n_folds: int = 5) -> list[float]:
    n = min(len(r_arm), len(r_base))
    edges = np.linspace(0, n, n_folds + 1, dtype=int)
    return [ann_sharpe(r_arm[a:b]) - ann_sharpe(r_base[a:b])
            for a, b in zip(edges[:-1], edges[1:])]


def bh_fdr(pvals: list[float], alpha: float = 0.05) -> list[bool]:
    m = len(pvals)
    order = sorted(range(m), key=lambda k: pvals[k])
    passed = [False] * m
    max_k = -1
    for rank, k in enumerate(order, start=1):
        if pvals[k] <= alpha * rank / m:
            max_k = rank
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

    bars_by_sym, sigs_by_sym = {}, {}
    for sym in SYMBOLS:
        bars, sigs = extract_signals(sym, start, end)
        bars_by_sym[sym], sigs_by_sym[sym] = bars, sigs
        print(f"{sym}: {len(bars)} bars (incl. warmup), {len(sigs)} signals")

    base = simulate("A0_cap1", bars_by_sym, sigs_by_sym, start)
    days_b, r_base = daily_returns(base.equity)
    print(f"\nA0_cap1 baseline: {len(base.trades)} trades, "
          f"Sharpe {ann_sharpe(r_base):+.3f}, MaxDD {max_drawdown(base.equity):+.2%}, "
          f"slot conflicts {base.slot_conflicts}")

    out = {
        "stage": args.stage,
        "window": [start.isoformat(), end.isoformat()],
        "baseline": {
            "n_trades": len(base.trades),
            "sharpe": ann_sharpe(r_base),
            "max_dd": max_drawdown(base.equity),
            "slot_conflicts": base.slot_conflicts,
            "ceiling_blocks": base.ceiling_blocks,
            "final_equity": base.equity[sorted(base.equity)[-1]],
        },
        "stage0_feasibility": {
            sym: {"slot_conflicts": base.slot_conflicts[sym],
                  "passes_floor_100": base.slot_conflicts[sym] >= 100}
            for sym in SYMBOLS
        },
        "arms": {},
    }

    pvals, arm_rows = [], []
    for arm in ARM_NAMES:
        res = simulate(arm, bars_by_sym, sigs_by_sym, start)
        days_a, r_arm = daily_returns(res.equity)
        # align on common days
        common = sorted(set(days_a) & set(days_b))
        ia = {d: k for k, d in enumerate(days_a)}
        ib = {d: k for k, d in enumerate(days_b)}
        ra = np.array([r_arm[ia[d]] for d in common])
        rb = np.array([r_base[ib[d]] for d in common])
        delta, lo, hi, p = block_bootstrap_delta_sharpe(ra, rb)
        folds = fold_consistency(common, ra, rb)
        mdd_a, mdd_b = max_drawdown(res.equity), max_drawdown(base.equity)
        rel_dd_worsening = (mdd_a - mdd_b) / abs(mdd_b) if mdd_b != 0 else 0.0
        big_down_a = int((ra <= -0.03).sum())
        big_down_b = int((rb <= -0.03).sum())
        row = {
            "n_trades": len(res.trades),
            "replacements": res.replacements,
            "ceiling_blocks": res.ceiling_blocks,
            "sharpe": ann_sharpe(ra),
            "delta_sharpe": delta, "ci95": [lo, hi], "p_one_sided": p,
            "folds_delta": folds,
            "folds_positive": sum(1 for f in folds if f > 0),
            "max_dd": mdd_a,
            "rel_dd_worsening_vs_base": rel_dd_worsening,
            "big_down_days": [big_down_a, big_down_b],
            "final_equity": res.equity[sorted(res.equity)[-1]],
        }
        out["arms"][arm] = row
        pvals.append(p)
        arm_rows.append((arm, row))
        print(f"{arm}: n={row['n_trades']} ΔSharpe {delta:+.4f} "
              f"CI [{lo:+.4f},{hi:+.4f}] p={p:.4f} folds+ {row['folds_positive']}/5 "
              f"relDD {rel_dd_worsening:+.2%} repl={res.replacements}")

    passed = bh_fdr(pvals)
    for (arm, row), ok in zip(arm_rows, passed):
        row["bh_fdr_pass"] = ok
        # verdict per PROTOCOL §4/§5
        if row["n_trades"] == 0:
            verdict = "parked_insufficient_n"
        elif ok and row["delta_sharpe"] > 0 and row["folds_positive"] >= 4:
            if (row["rel_dd_worsening_vs_base"] < -0.20
                    or (row["big_down_days"][1] > 0
                        and row["big_down_days"][0] > 1.5 * row["big_down_days"][1])):
                verdict = "parked_risk_degraded"
            else:
                verdict = "alive"
        elif row["delta_sharpe"] > 0:
            verdict = "parked_weak_effect"
        else:
            verdict = "dead"
        row["verdict"] = verdict
        print(f"{arm}: BH={'PASS' if ok else 'fail'} -> {verdict}")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(out, indent=2))
    print(f"\nwrote {args.output}")


if __name__ == "__main__":
    main()
