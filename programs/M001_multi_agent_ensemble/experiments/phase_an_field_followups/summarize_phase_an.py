"""Phase AN analysis layer: burn-in discard, cost deduction, median
[min-max] across starts, floor verdicts. Pure read of the raw tapes.

    python summarize_phase_an.py --phase design
"""
from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

HONEST_SPREAD = {"AUDUSD": 1.2, "NZDUSD": 1.6, "USDJPY": 1.0,
                 "USDCAD": 1.4, "XAGUSD": 2.5, "USTEC": 2.0}
COST_GRID = (0.0, 0.5, 1.0, 2.0)
BURN_IN_DAYS = 92  # ~3 months per methodology standard

STUDIES = {
    "AN-1": ("itoshi_rin", ("USDJPY",)),
    "AN-2": ("chigiri_hyoma", ("AUDUSD",)),
    "AN-3": ("chigiri_hyoma", ("XAGUSD",)),
    "AN-4": ("bachira_meguru", ("NZDUSD",)),
    "AN-5": ("barou_shoei", ("USDCAD", "USDJPY", "USTEC")),
}

DESIGN_STARTS = ("2015-01-01", "2015-04-01", "2015-07-01",
                 "2015-10-01", "2016-01-01")
SEALED_STARTS = ("2023-01-01", "2023-04-01", "2023-07-01",
                 "2023-10-01", "2024-01-01")

FLOORS = {
    "design": {"n": 60, "pf": 1.15, "mean_r": 0.05},
    "sealed": {"n": 25, "pf": 1.10, "mean_r": 0.0},
}


def _kpis(trades: list[dict], cost: float) -> dict:
    adj = []
    for t in trades:
        pnl = (t.get("pnl_pips") or 0.0) - cost
        sl = t.get("source_sl_pips") or 0.0
        adj.append((pnl, (pnl / sl) if sl > 0 else 0.0))
    n = len(adj)
    wins = [p for p, _ in adj if p > 0]
    gl = -sum(p for p, _ in adj if p <= 0)
    gw = sum(wins)
    rs = [r for _, r in adj]
    return {
        "n": n,
        "win_rate": round(len(wins) / n, 4) if n else None,
        "pf": round(gw / gl, 3) if gl > 0 else (None if not n else 99.0),
        "mean_r": round(sum(rs) / n, 4) if n else None,
        "total_pips": round(sum(p for p, _ in adj), 1),
    }


def _median_range(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return {"median": round(statistics.median(vals), 4),
            "min": round(min(vals), 4), "max": round(max(vals), 4)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("design", "sealed"), required=True)
    args = ap.parse_args()
    starts = DESIGN_STARTS if args.phase == "design" else SEALED_STARTS
    floors = FLOORS[args.phase]

    family = {}
    for study, (agent, fields) in STUDIES.items():
        for field in fields:
            spread = HONEST_SPREAD[field]
            per_start = []
            for k, start_iso in enumerate(starts):
                tpath = (HERE / "results" / study / field / args.phase
                         / f"start_{k}" / "trades.jsonl")
                if not tpath.exists():
                    continue
                start = datetime.fromisoformat(start_iso).replace(
                    tzinfo=timezone.utc)
                cutoff = start + timedelta(days=BURN_IN_DAYS)
                trades = []
                for line in tpath.read_text().splitlines():
                    if not line.strip():
                        continue
                    t = json.loads(line)
                    if t.get("agent_id") != agent:
                        continue
                    et = datetime.fromisoformat(t["entry_time"])
                    if et >= cutoff:
                        trades.append(t)
                row = {"start": start_iso}
                for c in COST_GRID:
                    row[f"cost_{c}x"] = _kpis(trades, c * spread)
                per_start.append(row)
            if not per_start:
                continue

            at1 = [r["cost_1.0x"] for r in per_start]
            n_stat = _median_range([r["n"] for r in at1])
            pf_stat = _median_range([r["pf"] for r in at1])
            mr_stat = _median_range([r["mean_r"] for r in at1])
            pf_pos = sum(1 for r in at1 if (r["pf"] or 0) > 1.0)
            verdict = "PASS"
            reasons = []
            if n_stat is None or n_stat["median"] < floors["n"]:
                verdict = "FAIL"; reasons.append("n_floor")
            if pf_stat is None or pf_stat["median"] < floors["pf"]:
                verdict = "FAIL"; reasons.append("pf_floor")
            if mr_stat is None or mr_stat["median"] < floors["mean_r"] or (
                    args.phase == "sealed" and mr_stat["median"] <= 0):
                verdict = "FAIL"; reasons.append("mean_r_floor")
            if pf_pos < 4:
                verdict = ("path_unstable"
                           if verdict == "PASS" else verdict)
                reasons.append(f"pf_positive_starts={pf_pos}/5")

            family[f"{study}:{agent}:{field}"] = {
                "verdict_at_1x_cost": verdict,
                "fail_reasons": reasons,
                "n": n_stat, "pf": pf_stat, "mean_r": mr_stat,
                "pf_positive_starts": pf_pos,
                "honest_spread": spread,
                "per_start": per_start,
            }

    out = HERE / "results" / f"{args.phase}_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(family, indent=2))
    for k, v in family.items():
        print(f"{k:42} {v['verdict_at_1x_cost']:14} "
              f"n={v['n']['median'] if v['n'] else '-':>6} "
              f"PF={v['pf']['median'] if v['pf'] else '-':>7} "
              f"[{v['pf']['min'] if v['pf'] else '-'}-"
              f"{v['pf']['max'] if v['pf'] else '-'}] "
              f"meanR={v['mean_r']['median'] if v['mean_r'] else '-':>8} "
              f"stab={v['pf_positive_starts']}/5")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
