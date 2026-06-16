"""Shared evaluation helpers for Test B stage runners.

Per protocols/TEST_B_PROTOCOL.md: pip-units MFE in event direction over W
bars after the return-touch, plus reach probabilities at fixed R-multiples
(R = impulse_height / 4). Hour-matched + direction-matched random-level
controls (Test A amendment v2.1 carries forward). Permutation p on
difference of mean MFE pips. BH-FDR over the 12-cell Stage-1 family;
per-cell α=0.05 for Stages 2–3.

This module is private to scripts/test_b/. It does not touch
conflab.events.all_detectors or modify any Test A code.
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from conflab.detectors_impulse_return import (
    ImpulseReturnConfig,
    detect_impulse_origin_return_events,
)
from conflab.stats import _permutation_pvalue, benjamini_hochberg

log = logging.getLogger(__name__)

# Pre-registered reach thresholds (R-multiples). Frozen by protocol §3.4.
REACH_THRESHOLDS: tuple[float, ...] = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)
HEADLINE_THRESHOLD: float = 0.5     # the user's "X% of the time" number

# Per-TF locked detector knobs (protocol §3.1, §3.3, §3.4).
TF_KNOBS: dict[str, dict] = {
    "H4": {"M_pips": 40.0, "K": 3, "N": 40, "W": 20},
    "H1": {"M_pips": 20.0, "K": 3, "N": 80, "W": 40},
}

# Per Amendment 6.2 (committed before any MFE outcome inspected): the
# pre-registered 0.30 intrabar-retrace ceiling yielded <30 candidate
# impulses across the EURUSD H4/H1 screen split (0.30: 1-4 per cell).
# 0.50 is the smallest value that crosses the n_gate=30 in every cell.
# Runner uses 0.50 across all stages and pairs.
MAX_RETRACE_FRAC: float = 0.50

# The Stage-1 grid axis (only M_atr is gridded; rest of the knobs are TF-fixed).
M_ATR_GRID: tuple[float, ...] = (1.0, 1.5, 2.0)
DIRECTIONS: tuple[int, ...] = (+1, -1)
TIMEFRAMES: tuple[str, ...] = ("H4", "H1")

PIP_SIZE: float = 0.0001              # USD-quoted majors

# n-gates per protocol §3.6.
N_GATE_ALIVE: int = 30
N_PERM: int = 5000


# ---------------------------------------------------------------------------
# Per-event MFE (pips, event direction, W bars after the touch bar)
# ---------------------------------------------------------------------------


def _mfe_pips_after(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                    idx: int, direction: int, W: int,
                    pip_size: float = PIP_SIZE) -> float | None:
    """Max favourable excursion in pips, direction-matched, over W bars
    AFTER bar idx (idx+1 .. idx+W). The reference price is closes[idx]
    (the touch bar's close for events; the control bar's close for controls).
    Returns None when fewer than 1 forward bar exists.
    """
    n = len(closes)
    if idx + 1 >= n:
        return None
    ref = closes[idx]
    end = min(idx + 1 + W, n)
    mfe = 0.0
    for t in range(idx + 1, end):
        if direction > 0:
            fav = highs[t] - ref
        else:
            fav = ref - lows[t]
        if fav > mfe:
            mfe = fav
    return float(mfe / pip_size)


# ---------------------------------------------------------------------------
# Hour-matched + direction-matched control sampling
# ---------------------------------------------------------------------------


def _build_hour_pools(df: pd.DataFrame, *, warmup: int, W: int
                      ) -> dict[int, np.ndarray]:
    """Bar indices in [warmup, n - 1 - W] grouped by hour-of-day."""
    n = len(df)
    hi = n - 1 - W
    if hi <= warmup:
        return {}
    valid = np.arange(warmup, hi)
    hours = df.index.hour.to_numpy()
    pools: dict[int, np.ndarray] = {}
    for h in np.unique(hours[valid]):
        pools[int(h)] = valid[hours[valid] == int(h)]
    return pools


def _sample_controls_for_event(touch_idx: int, direction: int,
                               hours: np.ndarray, pools: dict[int, np.ndarray],
                               control_mult: int,
                               rng: np.random.Generator) -> list[int]:
    """Sample `control_mult` bar indices sharing the touch bar's hour-of-day.
    Falls back to any-hour pool if the hour pool is empty (defensive)."""
    h = int(hours[touch_idx])
    pool = pools.get(h)
    if pool is None or len(pool) == 0:
        all_pool = np.concatenate(list(pools.values())) if pools else None
        if all_pool is None or len(all_pool) == 0:
            return []
        pool = all_pool
    return [int(pool[rng.integers(0, len(pool))]) for _ in range(control_mult)]


# ---------------------------------------------------------------------------
# Cell evaluation
# ---------------------------------------------------------------------------


@dataclass
class CellOutcome:
    cell_id: str
    tf: str
    direction: int
    M_atr: float
    M_pips: float
    K: int
    N: int
    W: int
    n_events: int
    n_controls: int
    mean_mfe_pips_event: float
    mean_mfe_pips_control: float
    effect_pips: float
    cohens_d: float
    p_value: float
    reach_event: dict       # {threshold_key: probability}
    reach_control: dict
    headline_reach_event: float
    headline_reach_control: float
    headline_reach_lift: float
    events: list = field(default_factory=list)   # raw event records

    def to_registry_row(self) -> dict:
        return {
            "cell_id": self.cell_id,
            "tf": self.tf,
            "direction": self.direction,
            "M_atr": self.M_atr,
            "M_pips": self.M_pips,
            "K": self.K,
            "N": self.N,
            "W": self.W,
            "n_events": self.n_events,
            "n_controls": self.n_controls,
            "mean_mfe_pips_event": round(self.mean_mfe_pips_event, 4),
            "mean_mfe_pips_control": round(self.mean_mfe_pips_control, 4),
            "effect_pips": round(self.effect_pips, 4),
            "cohens_d": round(self.cohens_d, 4),
            "p_value": float(self.p_value),
            "reach_event": {f"{k}R": round(v, 4)
                            for k, v in self.reach_event.items()},
            "reach_control": {f"{k}R": round(v, 4)
                              for k, v in self.reach_control.items()},
            "headline_reach_event": round(self.headline_reach_event, 4),
            "headline_reach_control": round(self.headline_reach_control, 4),
            "headline_reach_lift": round(self.headline_reach_lift, 4),
        }


def _cohens_d(event_arr: np.ndarray, control_arr: np.ndarray) -> float:
    n_e = len(event_arr); n_c = len(control_arr)
    if n_e < 2 or n_c < 2:
        return 0.0
    var_e = float(event_arr.var(ddof=1))
    var_c = float(control_arr.var(ddof=1))
    pooled_sd = math.sqrt(((n_e - 1) * var_e + (n_c - 1) * var_c) /
                          (n_e + n_c - 2))
    if pooled_sd <= 0.0:
        return 0.0
    return float((event_arr.mean() - control_arr.mean()) / pooled_sd)


def evaluate_cell(df: pd.DataFrame, *, tf: str, direction: int, M_atr: float,
                  rng: np.random.Generator,
                  warmup: int = 60, control_mult: int = 5,
                  n_perm: int = N_PERM) -> CellOutcome:
    """Run one (tf, direction, M_atr) cell on a single OHLC frame."""
    knobs = TF_KNOBS[tf]
    cfg = ImpulseReturnConfig(
        M_atr=M_atr, M_pips=knobs["M_pips"], K=knobs["K"],
        max_retrace_frac=MAX_RETRACE_FRAC,
        N=knobs["N"], pip_size=PIP_SIZE)
    W = knobs["W"]
    cell_id = f"{tf}_dir{direction:+d}_Matr{M_atr}"

    events = detect_impulse_origin_return_events(
        df, direction=direction, cfg=cfg, timeframe=tf)

    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    n = len(df)
    hours = df.index.hour.to_numpy()
    pools = _build_hour_pools(df, warmup=warmup, W=W)

    ev_mfe: list[float] = []
    ev_reach: list[list[bool]] = []
    ct_mfe: list[float] = []
    ct_reach: list[list[bool]] = []
    enriched_events: list[dict] = []

    for e in events:
        touch_idx = int(e["touch_bar_idx"])
        if touch_idx + W >= n - 1:
            continue
        if touch_idx < warmup:
            continue
        mfe = _mfe_pips_after(highs, lows, closes, touch_idx, direction, W)
        if mfe is None:
            continue
        R_pips = float(e["R_pips"])
        if R_pips <= 0:
            continue
        reach_event_thresholds = [mfe >= k * R_pips for k in REACH_THRESHOLDS]
        ev_mfe.append(mfe)
        ev_reach.append(reach_event_thresholds)

        controls = _sample_controls_for_event(
            touch_idx, direction, hours, pools, control_mult, rng)
        per_event_ctrl_mfe: list[float] = []
        per_event_ctrl_reach: list[list[bool]] = []
        for ci in controls:
            cm = _mfe_pips_after(highs, lows, closes, ci, direction, W)
            if cm is None:
                continue
            ct_mfe.append(cm)
            ct_reach.append([cm >= k * R_pips for k in REACH_THRESHOLDS])
            per_event_ctrl_mfe.append(cm)
            per_event_ctrl_reach.append(
                [cm >= k * R_pips for k in REACH_THRESHOLDS])

        e_record = dict(e)
        e_record.update({
            "cell_id": cell_id,
            "mfe_pips": round(mfe, 4),
            "R_pips": round(R_pips, 4),
            "reach_event": {f"{k}R": bool(b) for k, b in
                            zip(REACH_THRESHOLDS, reach_event_thresholds)},
        })
        enriched_events.append(e_record)

    if not ev_mfe:
        return CellOutcome(
            cell_id=cell_id, tf=tf, direction=direction, M_atr=M_atr,
            M_pips=knobs["M_pips"], K=knobs["K"], N=knobs["N"], W=W,
            n_events=0, n_controls=0,
            mean_mfe_pips_event=0.0, mean_mfe_pips_control=0.0,
            effect_pips=0.0, cohens_d=0.0, p_value=1.0,
            reach_event={k: 0.0 for k in REACH_THRESHOLDS},
            reach_control={k: 0.0 for k in REACH_THRESHOLDS},
            headline_reach_event=0.0, headline_reach_control=0.0,
            headline_reach_lift=0.0)

    ev_mfe_arr = np.asarray(ev_mfe, dtype=float)
    if ct_mfe:
        ct_mfe_arr = np.asarray(ct_mfe, dtype=float)
    else:
        ct_mfe_arr = np.array([0.0])

    p = float(_permutation_pvalue(ev_mfe_arr.copy(), ct_mfe_arr.copy(),
                                  n_perm, rng))
    d = _cohens_d(ev_mfe_arr, ct_mfe_arr)

    ev_reach_arr = np.asarray(ev_reach, dtype=float)
    ct_reach_arr = (np.asarray(ct_reach, dtype=float)
                    if ct_reach else np.zeros((0, len(REACH_THRESHOLDS))))
    reach_event = {k: float(ev_reach_arr[:, i].mean())
                   for i, k in enumerate(REACH_THRESHOLDS)}
    reach_control = {k: (float(ct_reach_arr[:, i].mean())
                         if ct_reach_arr.size else 0.0)
                     for i, k in enumerate(REACH_THRESHOLDS)}

    return CellOutcome(
        cell_id=cell_id, tf=tf, direction=direction, M_atr=M_atr,
        M_pips=knobs["M_pips"], K=knobs["K"], N=knobs["N"], W=W,
        n_events=int(len(ev_mfe)), n_controls=int(len(ct_mfe)),
        mean_mfe_pips_event=float(ev_mfe_arr.mean()),
        mean_mfe_pips_control=(float(ct_mfe_arr.mean())
                               if ct_mfe else 0.0),
        effect_pips=float(ev_mfe_arr.mean() -
                          (ct_mfe_arr.mean() if ct_mfe else 0.0)),
        cohens_d=d,
        p_value=p,
        reach_event=reach_event,
        reach_control=reach_control,
        headline_reach_event=reach_event[HEADLINE_THRESHOLD],
        headline_reach_control=reach_control[HEADLINE_THRESHOLD],
        headline_reach_lift=(reach_event[HEADLINE_THRESHOLD] -
                             reach_control[HEADLINE_THRESHOLD]),
        events=enriched_events,
    )


# ---------------------------------------------------------------------------
# Verdict assignment
# ---------------------------------------------------------------------------


def assign_verdict(row: dict, fdr_significant: bool, *,
                   alpha: float = 0.05, n_gate: int = N_GATE_ALIVE) -> str:
    """Four-tier verdict per protocol §3.6 / Test A precedent."""
    n = int(row.get("n_events", 0))
    effect = float(row.get("effect_pips", 0.0))
    p = float(row.get("p_value", 1.0))
    d = float(row.get("cohens_d", 0.0))
    if n < n_gate:
        return "parked_insufficient_n"
    if effect > 0 and fdr_significant:
        return "alive"
    if effect > 0 and p < alpha:
        return "parked_weak_effect"
    if 0 < d < 0.2 and effect > 0:
        return "parked_weak_effect"
    return "dead"


def apply_fdr_and_verdicts(rows: list[dict], *, alpha: float = 0.05,
                           n_gate: int = N_GATE_ALIVE,
                           use_fdr: bool = True) -> list[dict]:
    """Annotate each row with `fdr_significant` (BH @ alpha across powered
    cells) and `verdict`. If `use_fdr=False` (Stage 2/3, small family),
    fall back to per-cell α only."""
    powered_idx = [i for i, r in enumerate(rows)
                   if int(r.get("n_events", 0)) >= n_gate]
    if use_fdr and powered_idx:
        flags = benjamini_hochberg(
            [float(rows[i]["p_value"]) for i in powered_idx], alpha)
        sig_set = {powered_idx[k] for k, f in enumerate(flags) if f}
    elif powered_idx:
        sig_set = {i for i in powered_idx
                   if float(rows[i]["p_value"]) < alpha
                   and float(rows[i]["effect_pips"]) > 0}
    else:
        sig_set = set()
    for i, r in enumerate(rows):
        r["fdr_significant"] = bool(i in sig_set)
        r["verdict"] = assign_verdict(r, r["fdr_significant"],
                                      alpha=alpha, n_gate=n_gate)
    return rows


# ---------------------------------------------------------------------------
# JSONL I/O
# ---------------------------------------------------------------------------


def write_registry_jsonl(rows: Iterable[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def write_events_jsonl(events: Iterable[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in
            Path(path).read_text().splitlines() if line.strip()]


def format_registry_table(rows: list[dict]) -> str:
    order = {"alive": 0, "parked_weak_effect": 1,
             "parked_insufficient_n": 2, "dead": 3}
    rows = sorted(rows, key=lambda r: (order.get(r["verdict"], 99),
                                       r["p_value"]))
    width = 100
    lines = [
        "Test B verdict registry",
        "=" * width,
        f"{'cell':<22} {'n':>5} {'evMFE':>8} {'ctMFE':>8} "
        f"{'effect':>7} {'reach.5R':>8} {'ctR.5R':>7} {'lift':>6} "
        f"{'d':>6} {'p':>8}  verdict",
        "-" * width,
    ]
    for r in rows:
        lines.append(
            f"{r['cell_id']:<22} {r['n_events']:>5} "
            f"{r['mean_mfe_pips_event']:>8.2f} "
            f"{r['mean_mfe_pips_control']:>8.2f} "
            f"{r['effect_pips']:>+7.2f} "
            f"{r['headline_reach_event']*100:>7.1f}% "
            f"{r['headline_reach_control']*100:>6.1f}% "
            f"{r['headline_reach_lift']*100:>+5.1f}% "
            f"{r['cohens_d']:>+6.3f} "
            f"{r['p_value']:>8.4f}  "
            f"{r['verdict']}")
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    lines.append("-" * width)
    lines.append("  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return "\n".join(lines)
