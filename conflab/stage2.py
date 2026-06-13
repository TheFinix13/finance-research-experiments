"""Stage 2: conditional (context × setup) pairs.

Question (PROTOCOL.md): does setup event S occurring inside an ACTIVE
context window C improve the directional outcome over S alone — lift, not
mere co-occurrence?

Design:
* Context window: from a context event (higher TF) until ``context_horizon``
  bars of the context TF elapse. Direction agreement is required: only setup
  events whose hypothesis matches the context direction count as joint.
* Outcome: the same `directional_outcome` used in Stage 1, measured on the
  SETUP timeframe in the setup direction.
* Control: the displacement null. Setup timings are re-drawn uniformly from
  the same context windows (direction kept), which preserves both marginals
  (context activity, setup direction mix) and breaks only the fine-grained
  alignment of the setup with its own trigger bar.
* Statistic: mean joint MFE − mean displaced MFE; permutation p via
  re-drawing displacements; BH-FDR across the Stage-2 family.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from conflab.events import Event
from conflab.indicators import atr
from conflab.screening import directional_outcome
from conflab.stats import benjamini_hochberg

log = logging.getLogger(__name__)


@dataclass
class Stage2Config:
    context_horizons: dict = field(default_factory=lambda: {
        "D1": 30, "H4": 20, "H1": 20})
    setup_horizons: dict = field(default_factory=lambda: {
        "D1": 30, "H4": 20, "H1": 20, "M15": 16})
    min_joint: int = 50
    n_draws: int = 1000     # displacement re-draws for the null
    alpha: float = 0.05
    seed: int = 42
    warmup: int = 60


def _mfe_table(df: pd.DataFrame, horizon: int,
               warmup: int) -> dict[int, np.ndarray]:
    """Precomputed directional MFE (ATR units) for every bar and both
    directions; NaN where undefined. Makes the displacement null a lookup."""
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    a = atr(df).to_numpy()
    n = len(df)
    out = {+1: np.full(n, np.nan), -1: np.full(n, np.nan)}
    for d in (+1, -1):
        for i in range(warmup, n - 1):
            res = directional_outcome(highs, lows, closes, a, i, d, horizon)
            if res is not None:
                out[d][i] = res[0]
    return out


def _context_windows(ctx_events: list[Event], ctx_df: pd.DataFrame,
                     horizon: int) -> list[tuple]:
    """(start_ts, end_ts, direction) per context event."""
    windows = []
    n = len(ctx_df)
    for e in ctx_events:
        if e.index + 1 >= n:
            continue
        start = ctx_df.index[e.index]
        end_idx = min(e.index + horizon, n - 1)
        windows.append((start, ctx_df.index[end_idx], e.direction))
    return windows


def screen_pair(ctx_events: list[Event], ctx_df: pd.DataFrame, ctx_tf: str,
                setup_events: list[Event], setup_df: pd.DataFrame,
                setup_tf: str, cfg: Stage2Config,
                rng: np.random.Generator,
                mfe_table: dict[int, np.ndarray] | None = None) -> dict | None:
    """Score one (context_cell × setup_cell) pair. Returns a registry row
    (verdict assigned by the caller after family FDR)."""
    windows = _context_windows(ctx_events, ctx_df,
                               cfg.context_horizons.get(ctx_tf, 20))
    if not windows:
        return None
    horizon = cfg.setup_horizons.get(setup_tf, 20)
    if mfe_table is None:
        mfe_table = _mfe_table(setup_df, horizon, cfg.warmup)
    idx = setup_df.index

    # positional bar ranges of each window on the setup TF
    win_ranges = []
    for start, end, direction in windows:
        i0 = idx.searchsorted(start, side="left")
        i1 = idx.searchsorted(end, side="right") - 1
        if i1 > i0 >= 0:
            win_ranges.append((int(i0), int(i1), direction))
    if not win_ranges:
        return None

    # joint events: setup inside a window, direction agreeing with context
    joint = []
    for e in setup_events:
        if e.index < cfg.warmup:
            continue
        for i0, i1, d in win_ranges:
            if i0 <= e.index <= i1 and e.direction == d:
                joint.append(e)
                break
    joint_vals = np.array([mfe_table[e.direction][e.index] for e in joint])
    joint_vals = joint_vals[np.isfinite(joint_vals)]
    if not len(joint_vals):
        return None
    joint_mean = float(joint_vals.mean())

    # displacement null: same number of draws per window-direction profile;
    # per amendment v2.1 the redraw is restricted to in-window bars sharing
    # the event's hour-of-day (fallback: any in-window bar).
    hours = idx.hour.to_numpy()
    profile = []
    for e in joint:
        for i0, i1, d in win_ranges:
            if i0 <= e.index <= i1 and e.direction == d:
                in_win = np.arange(i0, i1 + 1)
                same_hour = in_win[hours[in_win] == hours[e.index]]
                profile.append((same_hour if len(same_hour) else in_win, d))
                break
    draw_matrix = np.empty((len(profile), cfg.n_draws))
    for r, (pool, d) in enumerate(profile):
        js = pool[rng.integers(0, len(pool), size=cfg.n_draws)]
        draw_matrix[r] = mfe_table[d][js]
    with np.errstate(invalid="ignore"):
        null_means_arr = np.nanmean(draw_matrix, axis=0)
    null_means_arr = null_means_arr[np.isfinite(null_means_arr)]
    if len(null_means_arr) < 100:
        return None
    p = float((1 + np.sum(null_means_arr >= joint_mean))
              / (1 + len(null_means_arr)))
    return {
        "n_joint": int(len(joint_vals)),
        "n_context_windows": len(win_ranges),
        "joint_mfe_atr": round(joint_mean, 4),
        "displaced_mfe_atr": round(float(null_means_arr.mean()), 4),
        "lift": round(joint_mean - float(null_means_arr.mean()), 4),
        "p_value": round(p, 5),
    }


def run_stage2(survivor_cells: list[dict],
               frames: dict[str, pd.DataFrame],
               events_by_cell: dict[tuple, list[Event]],
               cfg: Stage2Config | None = None) -> list[dict]:
    """Evaluate all ordered (context, setup) pairs among Stage-1 survivors
    where the context TF is strictly higher than the setup TF.

    ``survivor_cells``: Stage-1 registry rows with verdict == 'alive'.
    ``events_by_cell``: {(tf, event_type): [Event, ...]} on the same frames.
    """
    cfg = cfg or Stage2Config()
    rng = np.random.default_rng(cfg.seed)
    tf_rank = {"D1": 3, "H4": 2, "H1": 1, "M15": 0}
    tables: dict[str, dict[int, np.ndarray]] = {}
    rows: list[dict] = []
    for ctx in survivor_cells:
        for setup in survivor_cells:
            ctf, stf = ctx["tf"], setup["tf"]
            if tf_rank.get(ctf, -1) <= tf_rank.get(stf, -1):
                continue
            if stf not in tables:
                tables[stf] = _mfe_table(frames[stf],
                                         cfg.setup_horizons.get(stf, 20),
                                         cfg.warmup)
            ctx_events = events_by_cell.get((ctf, ctx["event_type"]), [])
            setup_events = events_by_cell.get((stf, setup["event_type"]), [])
            row = screen_pair(ctx_events, frames[ctf], ctf, setup_events,
                              frames[stf], stf, cfg, rng,
                              mfe_table=tables[stf])
            if row is None:
                continue
            row.update({"context": f"{ctf}:{ctx['event_type']}",
                        "setup": f"{stf}:{setup['event_type']}"})
            rows.append(row)

    powered = [r for r in rows if r["n_joint"] >= cfg.min_joint]
    flags = benjamini_hochberg([r["p_value"] for r in powered], cfg.alpha)
    sig_ids = {(r["context"], r["setup"]) for r, s in zip(powered, flags)
               if s}
    for r in rows:
        positive = r["lift"] > 0
        if r["n_joint"] < cfg.min_joint:
            r["verdict"] = "parked_insufficient_n"
        elif positive and (r["context"], r["setup"]) in sig_ids:
            r["verdict"] = "alive"
        elif positive and r["p_value"] < cfg.alpha:
            r["verdict"] = "parked_weak_effect"
        else:
            r["verdict"] = "dead"
    return rows
