"""E029 stage runner — pool-window timing, lift-only (PROTOCOL frozen).

    PYTHONPATH=../multi-pair-trading-agent:. \
        ../multi-pair-trading-agent/.venv/bin/python \
        programs/E029/run_e029_validation.py --stage 1

Stage 2 (sealed, run once) takes Stage-1 survivors:

    ... --stage 2 --cells fib_50_tag,ote_tag

Reuses E010's frozen helpers (`scripts/E010/run_e010.py` @ a159ec1):
loader, context/setup event collection, `screen_pair` displacement
null. No selection term / marginal pass — not part of this claim
(E029 PROTOCOL §3).
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from conflab.stage2 import Stage2Config, _mfe_table, screen_pair
from conflab.stats import benjamini_hochberg
from scripts.E010.run_e010 import (
    CELLS, CONTEXT_TYPE, HORIZON_M15, N_GATE, N_PERM, WARMUP,
    collect_setup_events, context_events, load_window,
)

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "output" / "E029_pool_window_timing"

EFFECT_FLOOR = 0.10
ALPHA = 0.05

STAGES = {
    1: {"seed": 29, "pair": "GBPUSD", "window": ("2015-01-01", "2021-12-31"),
        "label": "GBPUSD_screen", "fdr": "bh"},
    2: {"seed": 129, "pair": "EURUSD", "window": ("2025-01-01", "2026-05-27"),
        "label": "EURUSD_sealed", "fdr": "percell"},
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, required=True, choices=(1, 2))
    ap.add_argument("--cells", type=str, default=None,
                    help="Stage-1 survivors (required for stage 2)")
    args = ap.parse_args()
    spec = STAGES[args.stage]
    cells = CELLS if args.stage == 1 else None
    if cells is None:
        if not args.cells:
            raise SystemExit("stage 2 requires --cells (Stage-1 survivors)")
        cells = args.cells.split(",")
        unknown = set(cells) - set(CELLS)
        if unknown:
            raise SystemExit(f"unknown cells: {unknown}")

    rng = np.random.default_rng(spec["seed"])
    cfg = Stage2Config(n_draws=N_PERM, seed=spec["seed"], warmup=WARMUP)

    h1 = load_window(spec["pair"], "H1", *spec["window"])
    m15 = load_window(spec["pair"], "M15", *spec["window"])
    print(f"[E029 s{args.stage}] {spec['pair']} H1={len(h1)} M15={len(m15)} bars")
    ctx = context_events(h1)
    print(f"[E029 s{args.stage}] {len(ctx)} H1 {CONTEXT_TYPE} events")
    setups = collect_setup_events(m15)
    table = _mfe_table(m15, HORIZON_M15, WARMUP)

    rows = []
    for cell in cells:
        row = screen_pair(ctx, h1, "H1", setups.get(cell, []), m15, "M15",
                          cfg, rng, mfe_table=table)
        if row is None:
            row = {"n_joint": 0, "degenerate": True}
        row.update({"cell": cell, "stage": args.stage, "pair": spec["pair"],
                    "window": list(spec["window"]), "seed": spec["seed"]})
        rows.append(row)
        print(f"[E029 s{args.stage}] {cell}: n_joint={row.get('n_joint')} "
              f"joint={row.get('joint_mfe_atr')} displaced={row.get('displaced_mfe_atr')} "
              f"lift={row.get('lift')} p={row.get('p_value')}", flush=True)

    powered = [r for r in rows if r.get("n_joint", 0) >= N_GATE]
    if spec["fdr"] == "bh":
        flags = benjamini_hochberg([r["p_value"] for r in powered], ALPHA)
        sig = {id(r) for r, f in zip(powered, flags) if f}
    else:
        sig = {id(r) for r in powered if r["p_value"] < ALPHA}
    for r in rows:
        if r.get("n_joint", 0) < N_GATE:
            r["verdict"] = "parked_insufficient_n"
        elif r["lift"] >= EFFECT_FLOOR and id(r) in sig:
            r["verdict"] = "alive"
        elif r["lift"] > 0 and (id(r) in sig or r["p_value"] < ALPHA):
            r["verdict"] = "parked_weak_effect"
        else:
            r["verdict"] = "dead"

    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    path = OUT / f"stage{args.stage}_{spec['label']}_{stamp}.jsonl"
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"registry -> {path}")
    for r in rows:
        print(f"  {r['cell']}: {r['verdict']}")

    if args.stage == 1 and not any(r["verdict"] == "alive" for r in rows):
        stop = {"experiment": "E029", "stage": 1,
                "trigger": "0 of 10 cells alive on GBPUSD (PROTOCOL §6) — "
                           "timing edge declared EURUSD-local; sealed "
                           "reservation released",
                "registry": str(path), "stamp": stamp,
                "downstream_not_run": ["stage2_sealed"]}
        with open(OUT / "stage2_E029_stop.json", "w") as f:
            json.dump(stop, f, indent=2)
        print("STOP RULE FIRED: stage2 stop file emitted; "
              "sealed reservation to be released in DATA_LEDGER.")


if __name__ == "__main__":
    main()
