"""AN-3 recency-fade diagnostic (read-only, mechanism question).

Declared: re-reads the already-consumed AN-3 design + sealed tapes.
No selection, no retuning -- asks ONE question: is the weak 2024+
sealed performance outside the distribution of normal single-year
variation observed in the design region (2015-2022)?

Method: per-calendar-year KPIs at 1x honest cost (2.5 field-pips RT),
computed on the LONGEST path each side (design start_0 = 2015-01,
sealed start_0 = 2023-01) so every year is seen by one continuous
squad state. Sealed years are additionally cross-checked across all
five sealed paths to separate calendar effect from path noise.

    python diagnose_an3_recency.py
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
AGENT = "chigiri_hyoma"
FIELD = "XAGUSD"
COST = 2.5  # 1x honest RT spread, per PROTOCOL.md
BURN_IN_DAYS = 92
SEALED_STARTS = ("2023-01-01", "2023-04-01", "2023-07-01",
                 "2023-10-01", "2024-01-01")


def load(phase: str, k: int, start_iso: str) -> list[dict]:
    path = (HERE / "results" / "AN-3" / FIELD / phase
            / f"start_{k}" / "trades.jsonl")
    start = datetime.fromisoformat(start_iso).replace(tzinfo=timezone.utc)
    cutoff = start + timedelta(days=BURN_IN_DAYS)
    out = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        t = json.loads(line)
        if t.get("agent_id") != AGENT:
            continue
        if datetime.fromisoformat(t["entry_time"]) >= cutoff:
            out.append(t)
    return out


def kpis(trades: list[dict]) -> dict:
    n = len(trades)
    if not n:
        return {"n": 0}
    pnls = [(t["pnl_pips"] or 0.0) - COST for t in trades]
    wins = [p for p in pnls if p > 0]
    gl = -sum(p for p in pnls if p <= 0)
    rs = [((t["pnl_pips"] or 0.0) - COST) / t["source_sl_pips"]
          for t in trades if (t.get("source_sl_pips") or 0) > 0]
    atrs = [t["source_atr_pips"] for t in trades
            if t.get("source_atr_pips")]
    return {
        "n": n,
        "win_rate": round(len(wins) / n, 3),
        "pf": round(sum(wins) / gl, 3) if gl > 0 else 99.0,
        "mean_r": round(sum(rs) / len(rs), 4) if rs else None,
        "total_pips": round(sum(pnls), 1),
        "median_atr_pips": round(statistics.median(atrs), 1) if atrs else None,
    }


def by_year(trades: list[dict]) -> dict[int, list[dict]]:
    years: dict[int, list[dict]] = {}
    for t in trades:
        y = datetime.fromisoformat(t["entry_time"]).year
        years.setdefault(y, []).append(t)
    return years


def main() -> None:
    report: dict = {"question": "is 2024+ sealed weakness outside "
                    "normal single-year variation from design?"}

    # Design side: one continuous path, 2015-04 (post burn-in) -> 2022.
    design = by_year(load("design", 0, "2015-01-01"))
    report["design_years_start0"] = {
        str(y): kpis(ts) for y, ts in sorted(design.items())}

    # Sealed side: continuous 2023-01 path, then per-year across paths.
    sealed0 = by_year(load("sealed", 0, "2023-01-01"))
    report["sealed_years_start0"] = {
        str(y): kpis(ts) for y, ts in sorted(sealed0.items())}

    cross: dict[str, dict] = {}
    for k, start_iso in enumerate(SEALED_STARTS):
        for y, ts in sorted(by_year(load("sealed", k, start_iso)).items()):
            cross.setdefault(str(y), {})[f"path_{k} ({start_iso})"] = kpis(ts)
    report["sealed_years_all_paths"] = cross

    design_pfs = [v["pf"] for v in report["design_years_start0"].values()
                  if v.get("pf") is not None and v["n"] >= 10]
    report["design_single_year_pf_range"] = {
        "min": min(design_pfs), "max": max(design_pfs),
        "median": round(statistics.median(design_pfs), 3),
        "years_below_1": sum(1 for p in design_pfs if p < 1.0),
        "n_years": len(design_pfs),
    }

    out = HERE / "results" / "an3_recency_diagnostic.json"
    out.write_text(json.dumps(report, indent=2))

    print("design years (start_0, 1x cost):")
    for y, v in report["design_years_start0"].items():
        print(f"  {y}: n={v.get('n'):>3} pf={v.get('pf')} "
              f"wr={v.get('win_rate')} atr={v.get('median_atr_pips')}")
    print("sealed years (start_0, 1x cost):")
    for y, v in report["sealed_years_start0"].items():
        print(f"  {y}: n={v.get('n'):>3} pf={v.get('pf')} "
              f"wr={v.get('win_rate')} atr={v.get('median_atr_pips')}")
    print("design single-year PF range:",
          report["design_single_year_pf_range"])
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
