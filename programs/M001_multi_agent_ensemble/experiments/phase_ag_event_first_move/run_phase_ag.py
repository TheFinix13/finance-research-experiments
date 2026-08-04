"""Phase AG (Sae v2 S2): follow-the-first-move event continuation study.

All mechanics/constants are pre-registered in PROTOCOL.md. Run IS first;
validation only after IS verdicts are fixed:

    python run_phase_ag.py --window is
    python run_phase_ag.py --window validation --arms-from results/arms_is.json
    python run_phase_ag.py --window is --symbol GBPUSD   # robustness readout
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
CAL = HERE / "data" / "news_calendar_frozen_2026-07-24.json"
PARQUET = "/Users/the1finix/Documents/GitHub/multi-pair-trading-agent/data/parquet/{sym}_M15.parquet"

ATR_N = 96
KS = (1, 2)
MS = (3.0, 5.0, 8.0)
TPS = (1.5, 2.5)
HORIZON = 48          # M15 bars after the impulse window
COST_PIPS = 1.2
PIP = 1e4             # EURUSD/GBPUSD pip factor

WINDOWS = {
    "is": ("2015-01-01", "2021-12-31"),
    "validation": ("2022-01-01", "2025-12-31"),
}
IS_HALVES = (("2015-01-01", "2017-12-31"), ("2018-01-01", "2021-12-31"))


def _load_events(start: str, end: str) -> list[datetime]:
    d = json.loads(CAL.read_text())
    evs = d["events"] if isinstance(d, dict) else d
    lo = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    hi = datetime.fromisoformat(end + "T23:59:59").replace(tzinfo=timezone.utc)
    out = []
    for e in evs:
        t = datetime.fromisoformat(e["time_utc"])
        if lo <= t <= hi:
            out.append((t, e["title"]))
    return sorted(out)


def _simulate(df: pd.DataFrame, events, k: int):
    """Per-event impulse measurement + trade outcome per (m, tp) arm."""
    idx = df.index
    o, h, l, c = (df[x].to_numpy() for x in ("open", "high", "low", "close"))
    pc = np.roll(c, 1)
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    tr[0] = h[0] - l[0]
    rows = []
    for t_ev, title in events:
        i0 = idx.searchsorted(t_ev)          # first bar with open >= event
        if i0 <= ATR_N or i0 + k + HORIZON >= len(df):
            continue
        atr = float(np.mean(tr[i0 - ATR_N:i0]))  # strictly pre-event bars
        if atr <= 0:
            continue
        ref = c[i0 - 1]
        conf = i0 + k - 1                     # impulse-confirmation bar
        impulse = c[conf] - ref
        direction = 1 if impulse > 0 else -1
        atr_mult = abs(impulse) / atr
        entry = c[conf]
        stop = l[i0:conf + 1].min() if direction > 0 else h[i0:conf + 1].max()
        risk = abs(entry - stop)
        row = {
            "event_time": t_ev.isoformat(), "title": title, "k": k,
            "atr_pips": atr * PIP, "impulse_pips": impulse * PIP,
            "atr_mult": atr_mult, "direction": direction,
            "risk_pips": risk * PIP,
        }
        for tp_r in TPS:
            if risk <= 0:
                row[f"pnl_{tp_r}"] = None
                continue
            tp = entry + direction * tp_r * risk
            exit_px = None
            for j in range(conf + 1, conf + 1 + HORIZON):
                if direction > 0:
                    if l[j] <= stop:          # SL first when both touch
                        exit_px = stop
                        break
                    if h[j] >= tp:
                        exit_px = tp
                        break
                else:
                    if h[j] >= stop:
                        exit_px = stop
                        break
                    if l[j] <= tp:
                        exit_px = tp
                        break
            if exit_px is None:
                exit_px = c[conf + HORIZON]
            row[f"pnl_{tp_r}"] = (exit_px - entry) * direction * PIP - COST_PIPS
        rows.append(row)
    return pd.DataFrame(rows)


def _arm_stats(per_event: pd.DataFrame, m: float, tp_r: float) -> dict:
    sel = per_event[per_event["atr_mult"] >= m]
    pnl = sel[f"pnl_{tp_r}"].dropna()
    n = len(pnl)
    return {
        "n": int(n),
        "net_mean_pips": round(float(pnl.mean()), 2) if n else None,
        "net_total_pips": round(float(pnl.sum()), 1) if n else None,
        "win_rate": round(float((pnl > 0).mean()), 3) if n else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", choices=("is", "validation"), required=True)
    ap.add_argument("--symbol", default="EURUSD")
    ap.add_argument("--arms-from", type=Path, default=None,
                    help="validation: only run arms marked alive here")
    args = ap.parse_args()

    start, end = WINDOWS[args.window]
    events = _load_events(start, end)
    df = pd.read_parquet(PARQUET.format(sym=args.symbol))
    print(f"{args.symbol} {args.window}: {len(events)} events")

    frames = [(_simulate(df, events, k)) for k in KS]
    per_event = pd.concat(frames, ignore_index=True)
    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    tag = "" if args.symbol == "EURUSD" else f"_{args.symbol}"
    per_event.to_csv(out_dir / f"per_event_{args.window}{tag}.csv", index=False)

    allowed = None
    if args.arms_from:
        prior = json.loads(args.arms_from.read_text())
        allowed = {a["arm"] for a in prior["arms"] if a.get("is_alive")}

    arms = []
    for k in KS:
        pe_k = per_event[per_event["k"] == k]
        for m in MS:
            for tp_r in TPS:
                arm_id = f"K{k}_m{m:g}_tp{tp_r:g}"
                if allowed is not None and arm_id not in allowed:
                    continue
                stats = _arm_stats(pe_k, m, tp_r)
                rec = {"arm": arm_id, "k": k, "m": m, "tp_r": tp_r, **stats}
                if args.window == "is":
                    halves_pos = []
                    for h_lo, h_hi in IS_HALVES:
                        mask = (pe_k["event_time"] >= h_lo) & (pe_k["event_time"] <= h_hi + "T23:59:59")
                        hs = _arm_stats(pe_k[mask], m, tp_r)
                        halves_pos.append((hs["net_total_pips"] or 0) > 0)
                        rec[f"half_{h_lo[:4]}_total"] = hs["net_total_pips"]
                    rec["is_alive"] = bool(
                        stats["n"] >= 30
                        and (stats["net_mean_pips"] or -1) >= 2.0
                        and all(halves_pos)
                    )
                else:
                    rec["validation_pass"] = bool(
                        stats["n"] >= 15
                        and (stats["net_mean_pips"] or -1) >= 1.5
                    )
                arms.append(rec)

    dest = out_dir / f"arms_{args.window}{tag}.json"
    dest.write_text(json.dumps(
        {"symbol": args.symbol, "window": [start, end], "arms": arms},
        indent=2))
    print(json.dumps(arms, indent=1))
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
