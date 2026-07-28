"""E028 stage runner — Power-of-Three session sequence.

Usage (from repo root, agent venv):

    PYTHONPATH=../multi-pair-trading-agent:. \
        ../multi-pair-trading-agent/.venv/bin/python \
        programs/E028/run_e028_validation.py --stage 1

All parameters frozen in PROTOCOL §3.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from conflab.stats import benjamini_hochberg
from programs.E028.po3_days import analyze_days, wilson_ci

REPO = Path(__file__).resolve().parents[2]
PARQUET = REPO.parent / "multi-pair-trading-agent" / "data" / "parquet"
OUT = REPO / "output" / "E028_power_of_three_sessions"

COST_BASE = 0.3      # pips per side
COST_STRESS = 1.0
N_GATE = 100
ALPHA = 0.05
BOOT_B = 10_000
MARGIN_PP = 0.05     # +5 percentage points (PROTOCOL §1)

STAGES = {
    1: {"seed": 28, "pair": "EURUSD", "window": ("2015-01-01", "2021-12-31"),
        "label": "EURUSD_screen"},
    2: {"seed": 128, "pair": "EURUSD", "window": ("2022-01-01", "2024-12-31"),
        "label": "EURUSD_confirm"},
    3: {"seed": 228, "pair": "GBPUSD", "window": ("2015-01-01", "2021-12-31"),
        "label": "GBPUSD_crosspair"},
}


def load_window(pair: str, start: str, end: str) -> pd.DataFrame:
    df = pd.read_parquet(PARQUET / f"{pair}_M15.parquet")
    lo = pd.Timestamp(start, tz="UTC")
    hi = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    return df[(df.index >= lo) & (df.index < hi)]


def descriptives(days: list) -> dict:
    n = len(days)
    classes = {k: sum(1 for d in days if d.klass == k)
               for k in ("HIGH_ONLY", "LOW_ONLY", "BOTH", "NEITHER")}
    one_side = [d for d in days if d.klass in ("HIGH_ONLY", "LOW_ONLY")]

    # D2 completion (pooled one-side)
    comp_k = sum(1 for d in one_side if d.completed)
    d2 = wilson_ci(comp_k, len(one_side))

    # D3 baselines: unconditional touch rates + matched baseline for D2.
    touch_high = wilson_ci(sum(1 for d in days if d.ny_touch_high), n)
    touch_low = wilson_ci(sum(1 for d in days if d.ny_touch_low), n)
    # matched baseline: weight unconditional touch prob of each one-side
    # day's own target level by the class mix.
    n_low_only = classes["LOW_ONLY"]
    n_high_only = classes["HIGH_ONLY"]
    if one_side:
        matched_baseline = (n_low_only * touch_high[0]
                            + n_high_only * touch_low[0]) / len(one_side)
    else:
        matched_baseline = float("nan")
    both = [d for d in days if d.klass == "BOTH"]
    neither = [d for d in days if d.klass == "NEITHER"]
    both_high = wilson_ci(sum(1 for d in both if d.ny_touch_high), len(both))
    both_low = wilson_ci(sum(1 for d in both if d.ny_touch_low), len(both))
    neither_high = wilson_ci(sum(1 for d in neither if d.ny_touch_high),
                             len(neither))
    neither_low = wilson_ci(sum(1 for d in neither if d.ny_touch_low),
                            len(neither))

    # D4 fake rate
    fake_k = sum(1 for d in one_side if d.fake)
    d4 = wilson_ci(fake_k, len(one_side))

    # D5 completion timing
    bars = [d.completion_bar for d in one_side
            if d.completed and d.completion_bar is not None]
    d5 = float(np.median(bars)) if bars else None

    # D6 per-year D2 vs matched baseline
    d6 = {}
    years = sorted({d.date[:4] for d in days})
    for y in years:
        yd = [d for d in days if d.date.startswith(y)]
        yo = [d for d in yd if d.klass in ("HIGH_ONLY", "LOW_ONLY")]
        yk = sum(1 for d in yo if d.completed)
        th = sum(1 for d in yd if d.ny_touch_high) / len(yd) if yd else np.nan
        tl = sum(1 for d in yd if d.ny_touch_low) / len(yd) if yd else np.nan
        nlo = sum(1 for d in yo if d.klass == "LOW_ONLY")
        nho = sum(1 for d in yo if d.klass == "HIGH_ONLY")
        mb = (nlo * th + nho * tl) / len(yo) if yo else np.nan
        d6[y] = {"n_one_side": len(yo),
                 "completion": round(yk / len(yo), 4) if yo else None,
                 "matched_baseline": None if np.isnan(mb) else round(mb, 4)}

    return {
        "n_days": n,
        "D1_class_counts": classes,
        "D2_completion": {"k": comp_k, "n": len(one_side),
                          "p": d2[0], "ci95": [d2[1], d2[2]]},
        "D3_baselines": {
            "uncond_touch_asia_high": {"p": touch_high[0],
                                       "ci95": [touch_high[1], touch_high[2]]},
            "uncond_touch_asia_low": {"p": touch_low[0],
                                      "ci95": [touch_low[1], touch_low[2]]},
            "matched_baseline_for_D2": round(matched_baseline, 4),
            "both_days_touch_high": {"p": both_high[0], "n": len(both)},
            "both_days_touch_low": {"p": both_low[0]},
            "neither_days_touch_high": {"p": neither_high[0],
                                        "n": len(neither)},
            "neither_days_touch_low": {"p": neither_low[0]},
        },
        "D4_fake_rate": {"k": fake_k, "n": len(one_side),
                         "p": d4[0], "ci95": [d4[1], d4[2]]},
        "D5_median_completion_bar": d5,
        "D6_by_year": d6,
        "margin_pass": bool(len(one_side) and
                            d2[0] >= matched_baseline + MARGIN_PP),
    }


def score_arm(trades: list[dict], rng: np.random.Generator) -> dict:
    net = np.array([t["net_pips"] for t in trades])
    gross = np.array([t["gross_pips"] for t in trades])
    n = len(net)
    row = {"n_trades": n}
    if n == 0:
        row["verdict"] = "parked_insufficient_n"
        return row
    stress = gross - 2.0 * COST_STRESS
    boots = np.empty(BOOT_B)
    for b in range(BOOT_B):
        boots[b] = net[rng.integers(0, n, size=n)].mean()
    p = float((1 + np.sum(boots <= 0)) / (1 + BOOT_B))
    ci = np.percentile(boots, [2.5, 97.5])
    wins = int(np.sum(np.array([t["exit_reason"] for t in trades]) == "tp"))
    row.update({
        "mean_net_pips_base": round(float(net.mean()), 3),
        "mean_net_pips_stress": round(float(stress.mean()), 3),
        "boot_ci95_base": [round(float(ci[0]), 3), round(float(ci[1]), 3)],
        "boot_p_le0": round(p, 5),
        "tp_rate": round(wins / n, 4),
        "sl_rate": round(float(np.mean(
            np.array([t["exit_reason"] for t in trades]) == "sl")), 4),
    })
    return row


def assign_verdicts(cells: dict, use_bh: bool) -> None:
    powered = [c for c in cells.values() if c.get("n_trades", 0) >= N_GATE]
    if use_bh:
        flags = benjamini_hochberg([c["boot_p_le0"] for c in powered], ALPHA)
        sig = {id(c) for c, f in zip(powered, flags) if f}
    else:
        sig = {id(c) for c in powered if c["boot_p_le0"] < ALPHA}
    for c in cells.values():
        if c.get("n_trades", 0) < N_GATE:
            c["verdict"] = "parked_insufficient_n"
        elif (c["boot_ci95_base"][0] > 0 and c["mean_net_pips_stress"] > 0
              and id(c) in sig):
            c["verdict"] = "alive"
        elif c["mean_net_pips_base"] > 0:
            c["verdict"] = "parked_weak_effect"
        else:
            c["verdict"] = "dead"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, required=True, choices=(1, 2, 3))
    ap.add_argument("--arms", type=str, default="long,short",
                    help="surviving arms for stage 2/3")
    args = ap.parse_args()
    spec = STAGES[args.stage]
    rng = np.random.default_rng(spec["seed"])

    df = load_window(spec["pair"], *spec["window"])
    days = analyze_days(df, COST_BASE)
    desc = descriptives(days)

    arms = args.arms.split(",")
    cells = {}
    trades_by_arm = {
        "long": [d.trade for d in days
                 if d.klass == "LOW_ONLY" and d.trade is not None],
        "short": [d.trade for d in days
                  if d.klass == "HIGH_ONLY" and d.trade is not None],
    }
    skip_counts = {}
    for d in days:
        if d.skip_reason:
            skip_counts[d.skip_reason] = skip_counts.get(d.skip_reason, 0) + 1
    for arm in arms:
        cells[arm] = score_arm(trades_by_arm[arm], rng)
    assign_verdicts(cells, use_bh=(args.stage == 1))

    result = {"experiment": "E028", "stage": args.stage, "pair": spec["pair"],
              "window": list(spec["window"]), "seed": spec["seed"],
              "descriptives": desc, "mechanical_cells": cells,
              "skip_counts": skip_counts}

    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    path = OUT / f"stage{args.stage}_{spec['label']}_{stamp}.json"
    with open(path, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps({"D1": desc["D1_class_counts"],
                      "D2": desc["D2_completion"],
                      "matched_baseline": desc["D3_baselines"]["matched_baseline_for_D2"],
                      "D4": desc["D4_fake_rate"],
                      "margin_pass": desc["margin_pass"]}, indent=2))
    for arm, c in cells.items():
        print(f"  arm {arm}: {c}")
    print(f"results -> {path}")

    if args.stage == 1:
        mech_dead = all(c.get("mean_net_pips_base", -1) <= 0
                        for c in cells.values())
        if not desc["margin_pass"] and mech_dead:
            stop = {"experiment": "E028", "stage": 1,
                    "trigger": "descriptive margin failed AND both mechanical "
                               "cells non-positive at base costs (PROTOCOL §6)",
                    "results": str(path), "stamp": stamp,
                    "downstream_not_run": ["stage2", "stage3"]}
            for n_ in (2, 3):
                with open(OUT / f"stage{n_}_E028_stop.json", "w") as f:
                    json.dump(stop, f, indent=2)
            print("STOP RULE FIRED (full stop): stage2/3 stop files emitted.")
        elif desc["margin_pass"] and mech_dead:
            print("PARTIAL: descriptive margin passed; mechanical rule dead — "
                  "descriptive finding publishes, no stage2/3 for mechanics.")


if __name__ == "__main__":
    main()
