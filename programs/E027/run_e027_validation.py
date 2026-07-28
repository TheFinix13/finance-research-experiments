"""E027 stage runner — valid-liquidity sweep reversal.

Usage (from repo root, agent venv):

    PYTHONPATH=../multi-pair-trading-agent:. \
        ../multi-pair-trading-agent/.venv/bin/python \
        programs/E027/run_e027_validation.py --stage 1

Stage 2/3 run only on survivors, passed explicitly and recorded:

    ... --stage 2 --cells EURUSD:H1:sellside,EURUSD:H4:buyside

All parameters are frozen in PROTOCOL §3; nothing here is tunable from
the command line except the stage and the survivor list.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from conflab.indicators import atr
from conflab.screening import directional_outcome
from conflab.stats import benjamini_hochberg
from programs.E027.sweep_validity import detect_validity_sweeps

REPO = Path(__file__).resolve().parents[2]
PARQUET = REPO.parent / "multi-pair-trading-agent" / "data" / "parquet"
OUT = REPO / "output" / "E027_valid_liquidity_sweep"

# --- frozen (PROTOCOL §3) ---------------------------------------------------
LOOKBACK = 5
MAX_SCAN = 200
HORIZON = 20
WARMUP = 60
N_PERM = 5000
N_GATE = 100
EFFECT_FLOOR = 0.10
ALPHA = 0.05
CONTROL_MULT = 5

STAGES = {
    1: {"seed": 27, "window": ("2015-01-01", "2021-12-31"), "label": "EURUSD_screen",
        "cells": [("EURUSD", "H1", "sellside"), ("EURUSD", "H1", "buyside"),
                  ("EURUSD", "H4", "sellside"), ("EURUSD", "H4", "buyside")],
        "fdr": "bh"},
    2: {"seed": 127, "window": ("2022-01-01", "2024-12-31"), "label": "EURUSD_confirm",
        "cells": None, "fdr": "percell"},   # survivors via --cells
    3: {"seed": 227, "window": ("2015-01-01", "2021-12-31"), "label": "crosspair",
        "cells": None, "fdr": "percell"},   # survivors mapped to GBPUSD/USDCAD via --cells
}


def load_window(pair: str, tf: str, start: str, end: str) -> pd.DataFrame:
    """Direct read-only parquet read (PROTOCOL §7 A1 — network-free)."""
    df = pd.read_parquet(PARQUET / f"{pair}_{tf}.parquet")
    lo = pd.Timestamp(start, tz="UTC")
    hi = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    return df[(df.index >= lo) & (df.index < hi)]


def score_cell(df: pd.DataFrame, side: str,
               rng: np.random.Generator) -> dict | None:
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    a = atr(df).to_numpy()
    n = len(df)
    hours = df.index.hour.to_numpy()

    events = [e for e in detect_validity_sweeps(df, LOOKBACK, MAX_SCAN)
              if e.side == side and WARMUP <= e.index < n - 1]
    mfe, labels, ev_hours = [], [], []
    for e in events:
        out = directional_outcome(highs, lows, closes, a, e.index,
                                  e.direction, HORIZON)
        if out is None:
            continue
        mfe.append(out[0])
        labels.append(e.valid)
        ev_hours.append(int(hours[e.index]))
    if not mfe:
        return None
    mfe = np.asarray(mfe)
    labels = np.asarray(labels, dtype=bool)
    ev_hours = np.asarray(ev_hours)
    n_valid = int(labels.sum())
    n_invalid = int((~labels).sum())
    if n_valid == 0 or n_invalid == 0:
        return {"n_events": len(mfe), "n_valid": n_valid,
                "n_invalid": n_invalid, "degenerate": True}

    mean_v = float(mfe[labels].mean())
    mean_i = float(mfe[~labels].mean())
    obs = mean_v - mean_i

    # Hour-stratified label-shuffle permutation (PROTOCOL §1/§5).
    strata = [np.where(ev_hours == h)[0] for h in np.unique(ev_hours)]
    count = 0
    perm_labels = labels.copy()
    for _ in range(N_PERM):
        for idxs in strata:
            perm_labels[idxs] = labels[idxs][rng.permutation(len(idxs))]
        pv = perm_labels
        d = mfe[pv].mean() - mfe[~pv].mean() if pv.any() and (~pv).any() else -np.inf
        if d >= obs:
            count += 1
    p = (count + 1) / (N_PERM + 1)

    # Secondary (reported, not gating): each class vs hour+direction-matched
    # random-time controls, house 5x recipe.
    direction = +1 if side == "sellside" else -1
    lo_i, hi_i = WARMUP, n - 1 - HORIZON
    valid_pool = np.arange(lo_i, hi_i)
    pool_by_hour = {int(h): valid_pool[hours[valid_pool] == h]
                    for h in np.unique(hours[valid_pool])}
    ctrl = {True: [], False: []}
    for lab in (True, False):
        cls_hours = ev_hours[labels == lab]
        for _ in range(CONTROL_MULT):
            for eh in cls_hours:
                pool = pool_by_hour.get(int(eh))
                i = int(pool[rng.integers(0, len(pool))]) if pool is not None \
                    and len(pool) else int(rng.integers(lo_i, hi_i))
                out = directional_outcome(highs, lows, closes, a, i,
                                          direction, HORIZON)
                if out is not None:
                    ctrl[lab].append(out[0])
    eff_v = mean_v - float(np.mean(ctrl[True])) if ctrl[True] else None
    eff_i = mean_i - float(np.mean(ctrl[False])) if ctrl[False] else None

    return {
        "n_events": len(mfe), "n_valid": n_valid, "n_invalid": n_invalid,
        "valid_share": round(n_valid / len(mfe), 4),
        "mean_mfe_valid_atr": round(mean_v, 4),
        "mean_mfe_invalid_atr": round(mean_i, 4),
        "diff_atr": round(obs, 4),
        "p_value": round(p, 5),
        "effect_valid_vs_ctrl_atr": None if eff_v is None else round(eff_v, 4),
        "effect_invalid_vs_ctrl_atr": None if eff_i is None else round(eff_i, 4),
    }


def assign_verdicts(rows: list[dict], fdr: str) -> None:
    powered = [r for r in rows if not r.get("degenerate")
               and r["n_valid"] >= N_GATE and r["n_invalid"] >= N_GATE]
    if fdr == "bh":
        flags = benjamini_hochberg([r["p_value"] for r in powered], ALPHA)
        sig = {id(r) for r, f in zip(powered, flags) if f}
    else:
        sig = {id(r) for r in powered if r["p_value"] < ALPHA}
    for r in rows:
        if r.get("degenerate") or r["n_valid"] < N_GATE or r["n_invalid"] < N_GATE:
            r["verdict"] = "parked_insufficient_n"
        elif r["diff_atr"] >= EFFECT_FLOOR and id(r) in sig:
            r["verdict"] = "alive"
        elif r["diff_atr"] > 0 and (id(r) in sig or r["p_value"] < ALPHA):
            r["verdict"] = "parked_weak_effect"
        else:
            r["verdict"] = "dead"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, required=True, choices=(1, 2, 3))
    ap.add_argument("--cells", type=str, default=None,
                    help="PAIR:TF:side,... (required for stage 2/3)")
    args = ap.parse_args()
    spec = STAGES[args.stage]
    cells = spec["cells"]
    if cells is None:
        if not args.cells:
            raise SystemExit("stage 2/3 require --cells (Stage-1 survivors)")
        cells = [tuple(c.split(":")) for c in args.cells.split(",")]

    rng = np.random.default_rng(spec["seed"])
    rows = []
    for pair, tf, side in cells:
        df = load_window(pair, tf, *spec["window"])
        row = score_cell(df, side, rng) or {"degenerate": True, "n_events": 0,
                                            "n_valid": 0, "n_invalid": 0}
        row.update({"pair": pair, "tf": tf, "side": side,
                    "window": list(spec["window"]), "stage": args.stage,
                    "seed": spec["seed"]})
        rows.append(row)
        print(f"[E027 s{args.stage}] {pair} {tf} {side}: "
              f"n={row.get('n_events')} v={row.get('n_valid')} "
              f"i={row.get('n_invalid')} diff={row.get('diff_atr')} "
              f"p={row.get('p_value')}")

    assign_verdicts(rows, spec["fdr"])

    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    path = OUT / f"stage{args.stage}_{spec['label']}_{stamp}.jsonl"
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"registry -> {path}")
    for r in rows:
        print(f"  {r['pair']} {r['tf']} {r['side']}: {r['verdict']}")

    if args.stage == 1 and not any(r["verdict"] == "alive" for r in rows):
        stop = {"experiment": "E027", "stage": 1,
                "trigger": "0 of 4 Stage-1 cells alive (PROTOCOL §6)",
                "registry": str(path), "stamp": stamp,
                "downstream_not_run": ["stage2_confirm", "stage3_crosspair"]}
        for n_ in (2, 3):
            with open(OUT / f"stage{n_}_E027_stop.json", "w") as f:
                json.dump(stop, f, indent=2)
        print("STOP RULE FIRED: 0 alive at Stage 1 — stage2/3 stop files emitted.")


if __name__ == "__main__":
    main()
