"""Summarize Barou v1.4 tapes with AN-identical burn-in + cost floors."""
from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BURN_DAYS = 92
HONEST_SPREAD = 1.0  # USDJPY
COST_MULT = 1.0


def _kpis(trades: list[dict], cost: float) -> dict:
    if not trades:
        return {"n": 0, "win_rate": 0.0, "pf": 0.0, "mean_r": 0.0, "total_pips": 0.0}
    rs, wins, gp, gl = [], 0, 0.0, 0.0
    for t in trades:
        pnl = float(t["pnl_pips"]) - cost
        sl = float(t.get("source_sl_pips") or 0.0)
        r = (pnl / sl) if sl > 0 else 0.0
        rs.append(r)
        if pnl > 0:
            wins += 1
            gp += pnl
        elif pnl < 0:
            gl += -pnl
    return {
        "n": len(trades),
        "win_rate": round(wins / len(trades), 4),
        "pf": round(gp / gl, 3) if gl > 0 else (999.0 if gp > 0 else 0.0),
        "mean_r": round(statistics.mean(rs), 4),
        "total_pips": round(sum(float(t["pnl_pips"]) - cost for t in trades), 1),
    }


def _load(path: Path, start_iso: str) -> list[dict]:
    cutoff = datetime.fromisoformat(start_iso).replace(tzinfo=timezone.utc) + timedelta(days=BURN_DAYS)
    rows = []
    with path.open() as fh:
        for line in fh:
            t = json.loads(line)
            if t.get("agent_id") != "barou_shoei":
                continue
            et = datetime.fromisoformat(t["entry_time"].replace("Z", "+00:00"))
            if et >= cutoff:
                rows.append(t)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("design", "sealed"), required=True)
    args = ap.parse_args()
    root = HERE / "results" / args.phase
    meta = json.loads((root / "meta.json").read_text())
    per_start = []
    for k, m in enumerate(meta):
        trades = _load(root / f"start_{k}" / "trades.jsonl", m["start"])
        per_start.append({"start": m["start"], **_kpis(trades, HONEST_SPREAD * COST_MULT)})

    def med(key):
        vals = [s[key] for s in per_start]
        return {
            "median": round(statistics.median(vals), 4 if key == "mean_r" else 3),
            "min": round(min(vals), 4 if key == "mean_r" else 3),
            "max": round(max(vals), 4 if key == "mean_r" else 3),
        }

    n_med = statistics.median([s["n"] for s in per_start])
    pf_med = statistics.median([s["pf"] for s in per_start])
    r_med = statistics.median([s["mean_r"] for s in per_start])
    pos = sum(1 for s in per_start if s["pf"] > 1.0)
    if args.phase == "design":
        floors = (n_med >= 60, pf_med >= 1.15, r_med >= 0.05, pos >= 4)
    else:
        floors = (n_med >= 25, pf_med >= 1.10, r_med > 0, pos >= 4)
    verdict = "PASS" if all(floors) else "FAIL"
    reasons = []
    if args.phase == "design":
        if n_med < 60: reasons.append("n_floor")
        if pf_med < 1.15: reasons.append("pf_floor")
        if r_med < 0.05: reasons.append("mean_r_floor")
        if pos < 4: reasons.append(f"pf_positive_starts={pos}/5")
    else:
        if n_med < 25: reasons.append("n_floor")
        if pf_med < 1.10: reasons.append("pf_floor")
        if r_med <= 0: reasons.append("mean_r_floor")
        if pos < 4: reasons.append(f"pf_positive_starts={pos}/5")

    out = {
        "verdict_at_1x_cost": verdict,
        "fail_reasons": reasons,
        "n": med("n"),
        "pf": med("pf"),
        "mean_r": med("mean_r"),
        "pf_positive_starts": pos,
        "honest_spread": HONEST_SPREAD,
        "per_start": per_start,
        "note": ("design KPIs are contaminated upper-bound; sealed is judgment"
                 if args.phase == "design" else "sealed judgment"),
    }
    path = HERE / "results" / f"{args.phase}_summary.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"barou_v14:{args.phase}  {verdict:4}  n={n_med:.0f} PF={pf_med:.3f} "
          f"meanR={r_med:.4f} stab={pos}/5  reasons={reasons}")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
