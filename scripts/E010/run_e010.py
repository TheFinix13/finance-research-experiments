"""E010 stage runner — H1 equal_highs_pool × 10 M15 setups (PROTOCOL frozen).

    PYTHONPATH=../multi-pair-trading-agent:. \
        ../multi-pair-trading-agent/.venv/bin/python \
        scripts/E010/run_e010.py --stage 1

Stages 2-4 run on survivors only:

    ... --stage 2 --cells bullish_fvg_touch,fib_50_tag

Loader per PROTOCOL §7 A1 (direct parquet, network-free); marginal per
§7 A2 (event/outcome code path of screen_cell, no marginal p-value).
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from conflab.detectors_fib import detect_fib_events
from conflab.detectors_liquidity import detect_liquidity_events
from conflab.detectors_trendlines import detect_trendline_events
from conflab.detectors_zones import detect_fvg_events
from conflab.events import Event
from conflab.stage2 import Stage2Config, _context_windows, _mfe_table, screen_pair
from conflab.stats import benjamini_hochberg

REPO = Path(__file__).resolve().parents[2]
PARQUET = REPO.parent / "multi-pair-trading-agent" / "data" / "parquet"
OUT = REPO / "output" / "E010_equal_highs_pool_stage2b"

# --- frozen (PROTOCOL §2/§3) ------------------------------------------------
CONTEXT_TYPE = "equal_highs_pool"
CELLS = [
    "bullish_fvg_touch", "channel_bottom_touch", "fib_382_tag", "fib_50_tag",
    "fib_618_tag", "fib_ext_1272_tag", "ote_tag",
    "trendline_break_retest_bullish", "trendline_liquidity_sweep_low",
    "trendline_support_touch",
]
N_PERM = 5000
N_GATE = 100
EFFECT_FLOOR = 0.10
ALPHA = 0.05
WARMUP = 60
HORIZON_M15 = 16
CONTROL_MULT = 5

STAGES = {
    1: {"seed": 42, "pair": "EURUSD", "window": ("2015-01-01", "2021-12-31"),
        "label": "EURUSD_screen", "fdr": "bh"},
    2: {"seed": 142, "pair": "EURUSD", "window": ("2022-01-01", "2024-12-31"),
        "label": "EURUSD_confirm", "fdr": "percell"},
    3: {"seed": 242, "pair": "GBPUSD", "window": ("2015-01-01", "2021-12-31"),
        "label": "GBPUSD", "fdr": "percell"},
    4: {"seed": 342, "pair": "EURUSD", "window": ("2025-01-01", "2026-06-09"),
        "label": "EURUSD_sealed", "fdr": "percell"},
}


def load_window(pair: str, tf: str, start: str, end: str) -> pd.DataFrame:
    df = pd.read_parquet(PARQUET / f"{pair}_{tf}.parquet")
    lo = pd.Timestamp(start, tz="UTC")
    hi = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    return df[(df.index >= lo) & (df.index < hi)]


def context_events(h1: pd.DataFrame) -> list[Event]:
    return [e for e in detect_liquidity_events(h1)
            if e.type == CONTEXT_TYPE]


def collect_setup_events(m15: pd.DataFrame) -> dict[str, list[Event]]:
    by_type: dict[str, list[Event]] = {}
    for det in (detect_fvg_events, detect_trendline_events, detect_fib_events):
        for e in det(m15):
            if e.type in CELLS and e.direction == +1:
                by_type.setdefault(e.type, []).append(e)
    return by_type


def joint_events(ctx: list[Event], h1: pd.DataFrame,
                 setups: list[Event], m15: pd.DataFrame) -> list[Event]:
    """Same window/direction-agreement rule as screen_pair, count only."""
    cfg = Stage2Config()
    windows = _context_windows(ctx, h1, cfg.context_horizons["H1"])
    idx = m15.index
    win_ranges = []
    for start, end, direction in windows:
        i0 = idx.searchsorted(start, side="left")
        i1 = idx.searchsorted(end, side="right") - 1
        if i1 > i0 >= 0:
            win_ranges.append((int(i0), int(i1), direction))
    out = []
    for e in setups:
        if e.index < WARMUP:
            continue
        for i0, i1, d in win_ranges:
            if i0 <= e.index <= i1 and e.direction == d:
                out.append(e)
                break
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, required=True, choices=(1, 2, 3, 4))
    ap.add_argument("--cells", type=str, default=None,
                    help="survivor cells for stages 2-4")
    args = ap.parse_args()
    spec = STAGES[args.stage]
    cells = CELLS if args.stage == 1 else None
    if cells is None:
        if not args.cells:
            raise SystemExit("stages 2-4 require --cells (survivors)")
        cells = args.cells.split(",")
        unknown = set(cells) - set(CELLS)
        if unknown:
            raise SystemExit(f"unknown cells: {unknown}")

    rng = np.random.default_rng(spec["seed"])
    cfg = Stage2Config(n_draws=N_PERM, seed=spec["seed"], warmup=WARMUP)

    h1 = load_window(spec["pair"], "H1", *spec["window"])
    m15 = load_window(spec["pair"], "M15", *spec["window"])
    print(f"[E010 s{args.stage}] {spec['pair']} H1={len(h1)} M15={len(m15)} bars")
    ctx = context_events(h1)
    print(f"[E010 s{args.stage}] {len(ctx)} H1 {CONTEXT_TYPE} events")
    setups = collect_setup_events(m15)

    # Shared MFE lookup table (also serves the marginal + its controls, §7 A2).
    table = _mfe_table(m15, HORIZON_M15, WARMUP)
    hours = m15.index.hour.to_numpy()
    n = len(m15)
    lo_i, hi_i = WARMUP, n - 1 - HORIZON_M15
    valid_pool = np.arange(lo_i, hi_i)
    pool_by_hour = {int(h): valid_pool[hours[valid_pool] == h]
                    for h in np.unique(hours[valid_pool])}

    rows = []
    for cell in cells:
        evs = setups.get(cell, [])
        row = screen_pair(ctx, h1, "H1", evs, m15, "M15", cfg, rng,
                          mfe_table=table)
        if row is None:
            row = {"n_joint": 0, "degenerate": True}
        # Setup-marginal MFE + hour-matched controls via table lookups (§7 A2).
        marg_vals, ctrl_vals = [], []
        for e in evs:
            if not (WARMUP <= e.index < n - 1):
                continue
            v = table[e.direction][e.index]
            if np.isfinite(v):
                marg_vals.append(v)
                pool = pool_by_hour.get(int(hours[e.index]))
                for _ in range(CONTROL_MULT):
                    i = int(pool[rng.integers(0, len(pool))]) if pool is not None \
                        and len(pool) else int(rng.integers(lo_i, hi_i))
                    cv = table[e.direction][i]
                    if np.isfinite(cv):
                        ctrl_vals.append(cv)
        marginal = float(np.mean(marg_vals)) if marg_vals else None
        ctrl = float(np.mean(ctrl_vals)) if ctrl_vals else None
        if not row.get("degenerate") and marginal is not None:
            row["setup_marginal_mfe_atr"] = round(marginal, 4)
            row["marginal_ctrl_mfe_atr"] = None if ctrl is None else round(ctrl, 4)
            row["n_marginal"] = len(marg_vals)
            row["selection_term"] = round(row["joint_mfe_atr"] - marginal, 4)
        row.update({"cell": cell, "stage": args.stage, "pair": spec["pair"],
                    "window": list(spec["window"]), "seed": spec["seed"]})
        rows.append(row)
        print(f"[E010 s{args.stage}] {cell}: n_joint={row.get('n_joint')} "
              f"joint={row.get('joint_mfe_atr')} marg={row.get('setup_marginal_mfe_atr')} "
              f"sel={row.get('selection_term')} lift={row.get('lift')} "
              f"p={row.get('p_value')}", flush=True)

    # Verdicts per PROTOCOL §3.
    powered = [r for r in rows if r.get("n_joint", 0) >= N_GATE
               and "selection_term" in r]
    if spec["fdr"] == "bh":
        flags = benjamini_hochberg([r["p_value"] for r in powered], ALPHA)
        sig = {id(r) for r, f in zip(powered, flags) if f}
    else:
        sig = {id(r) for r in powered if r["p_value"] < ALPHA}
    for r in rows:
        if r.get("n_joint", 0) < N_GATE or "selection_term" not in r:
            r["verdict"] = "parked_insufficient_n"
        elif (r["selection_term"] >= EFFECT_FLOOR
              and r["lift"] >= EFFECT_FLOOR and id(r) in sig):
            r["verdict"] = "alive"
        elif (r["selection_term"] > 0 and r["lift"] > 0
              and (id(r) in sig or r["p_value"] < ALPHA)):
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

    alive = [r for r in rows if r["verdict"] == "alive"]
    if not alive:
        downstream = {1: [2, 3, 4], 2: [3, 4], 3: [4], 4: []}[args.stage]
        stop = {"experiment": "E010", "stage": args.stage,
                "trigger": f"0 alive at stage {args.stage} (PROTOCOL §6)",
                "registry": str(path), "stamp": stamp,
                "downstream_not_run": [f"stage{d}" for d in downstream]}
        for d in downstream:
            with open(OUT / f"stage{d}_E010_stop.json", "w") as f:
                json.dump(stop, f, indent=2)
        if downstream:
            print(f"STOP RULE FIRED at stage {args.stage}: "
                  f"stop files emitted for {downstream}.")


if __name__ == "__main__":
    main()
