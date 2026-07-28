"""E030 stage runner — London-continuation session drift.

    PYTHONPATH=../multi-pair-trading-agent:. \
        ../multi-pair-trading-agent/.venv/bin/python \
        programs/E030/run_e030_validation.py --stage 1

Stage 1 is a NON-CLAIMING effect-size lock on the hypothesis-generating
slice (PROTOCOL §0/§3); the inferential verdict begins at Stage 2.
Stages 3-4 take surviving arms via --arms.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from conflab.stats import benjamini_hochberg
from programs.E030.continuation_days import analyze_continuation_days

REPO = Path(__file__).resolve().parents[2]
PARQUET = REPO.parent / "multi-pair-trading-agent" / "data" / "parquet"
OUT = REPO / "output" / "E030_london_continuation"

COST_BASE = 0.3
COST_STRESS = 1.0
N_GATE = 100
ALPHA = 0.05
BOOT_B = 10_000

STAGES = {
    1: {"seed": 30, "pair": "EURUSD", "window": ("2015-01-01", "2021-12-31"),
        "label": "EURUSD_lock", "claiming": False, "fdr": None},
    2: {"seed": 130, "pair": "EURUSD", "window": ("2022-01-01", "2024-12-31"),
        "label": "EURUSD_confirm", "claiming": True, "fdr": "bh"},
    3: {"seed": 230, "pair": "GBPUSD", "window": ("2015-01-01", "2021-12-31"),
        "label": "GBPUSD_crosspair", "claiming": True, "fdr": "percell"},
    4: {"seed": 330, "pair": "EURUSD", "window": ("2025-01-01", "2026-05-27"),
        "label": "EURUSD_sealed", "claiming": True, "fdr": "percell"},
}


def load_window(pair: str, start: str, end: str) -> pd.DataFrame:
    df = pd.read_parquet(PARQUET / f"{pair}_M15.parquet")
    lo = pd.Timestamp(start, tz="UTC")
    hi = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    return df[(df.index >= lo) & (df.index < hi)]


def score_arm(net: np.ndarray, gross: np.ndarray,
              rng: np.random.Generator) -> dict:
    n = len(net)
    row = {"n_trades": n}
    if n == 0:
        return row
    stress = gross - 2.0 * COST_STRESS
    boots = np.empty(BOOT_B)
    for b in range(BOOT_B):
        boots[b] = net[rng.integers(0, n, size=n)].mean()
    ci = np.percentile(boots, [2.5, 97.5])
    row.update({
        "mean_net_pips_base": round(float(net.mean()), 3),
        "mean_net_pips_stress": round(float(stress.mean()), 3),
        "boot_ci95_base": [round(float(ci[0]), 3), round(float(ci[1]), 3)],
        "boot_p_le0": round(float((1 + np.sum(boots <= 0)) / (1 + BOOT_B)), 5),
        "median_net_pips_base": round(float(np.median(net)), 3),
        "win_rate_base": round(float(np.mean(net > 0)), 4),
    })
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, required=True, choices=(1, 2, 3, 4))
    ap.add_argument("--arms", type=str, default="long,short")
    args = ap.parse_args()
    spec = STAGES[args.stage]
    rng = np.random.default_rng(spec["seed"])

    df = load_window(spec["pair"], *spec["window"])
    days = analyze_continuation_days(df, COST_BASE)

    net_by_arm = {
        "long": np.array([d.net_pips_base for d in days
                          if d.klass == "HIGH_ONLY" and d.net_pips_base is not None]),
        "short": np.array([d.net_pips_base for d in days
                           if d.klass == "LOW_ONLY" and d.net_pips_base is not None]),
    }
    gross_by_arm = {
        "long": np.array([d.gross_pips for d in days
                          if d.klass == "HIGH_ONLY" and d.gross_pips is not None]),
        "short": np.array([d.gross_pips for d in days
                           if d.klass == "LOW_ONLY" and d.gross_pips is not None]),
    }
    placebo = {
        "long": np.array([d.placebo_long_gross for d in days
                          if d.placebo_long_gross is not None]) - 2.0 * COST_BASE,
        "short": np.array([d.placebo_short_gross for d in days
                           if d.placebo_short_gross is not None]) - 2.0 * COST_BASE,
    }

    cells = {}
    for arm in args.arms.split(","):
        c = score_arm(net_by_arm[arm], gross_by_arm[arm], rng)
        c["placebo_mean_net_pips"] = round(float(placebo[arm].mean()), 3) \
            if len(placebo[arm]) else None
        c["n_placebo_days"] = int(len(placebo[arm]))
        cells[arm] = c

    # Verdicts only at claiming stages (PROTOCOL §1/§3).
    if spec["claiming"]:
        powered = [c for c in cells.values() if c.get("n_trades", 0) >= N_GATE]
        if spec["fdr"] == "bh":
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

    result = {"experiment": "E030", "stage": args.stage, "pair": spec["pair"],
              "window": list(spec["window"]), "seed": spec["seed"],
              "claiming": spec["claiming"], "cells": cells}

    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    path = OUT / f"stage{args.stage}_{spec['label']}_{stamp}.json"
    with open(path, "w") as f:
        json.dump(result, f, indent=2)
    for arm, c in cells.items():
        print(f"  arm {arm}: {c}")
    print(f"results -> {path}")

    if args.stage == 1:
        # §4 go/no-go: both arms positive at base costs AND each arm's
        # one-side drift beats its placebo-day drift (point estimates).
        fails = []
        for arm, c in cells.items():
            if c.get("mean_net_pips_base", -1) <= 0:
                fails.append(f"{arm}: mean<=0 at base costs")
            elif c["placebo_mean_net_pips"] is not None and \
                    c["mean_net_pips_base"] <= c["placebo_mean_net_pips"]:
                fails.append(f"{arm}: does not beat placebo "
                             f"({c['mean_net_pips_base']} <= "
                             f"{c['placebo_mean_net_pips']})")
        if fails:
            stop = {"experiment": "E030", "stage": 1,
                    "trigger": "Stage-1 go/no-go failed (PROTOCOL §4): "
                               + "; ".join(fails),
                    "results": str(path), "stamp": stamp,
                    "downstream_not_run": ["stage2", "stage3", "stage4"],
                    "note": "sealed reservation released for E030 "
                            "(E029 co-reservation unaffected)"}
            for n_ in (2, 3, 4):
                with open(OUT / f"stage{n_}_E030_stop.json", "w") as f:
                    json.dump(stop, f, indent=2)
            print("STOP RULE FIRED (go/no-go): " + "; ".join(fails))
        else:
            print("Stage-1 go/no-go PASSED (non-claiming) — stage 2 may run.")

    if args.stage >= 2 and spec["claiming"]:
        alive = [a for a, c in cells.items() if c.get("verdict") == "alive"]
        if not alive:
            downstream = {2: [3, 4], 3: [4], 4: []}[args.stage]
            stop = {"experiment": "E030", "stage": args.stage,
                    "trigger": f"0 alive at stage {args.stage} (PROTOCOL §4)",
                    "results": str(path), "stamp": stamp,
                    "downstream_not_run": [f"stage{d}" for d in downstream]}
            for d in downstream:
                with open(OUT / f"stage{d}_E030_stop.json", "w") as f:
                    json.dump(stop, f, indent=2)
            if downstream:
                print(f"STOP RULE FIRED at stage {args.stage}.")


if __name__ == "__main__":
    main()
