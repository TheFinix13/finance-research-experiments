"""Stage-1 marginal screening: every (timeframe × event type) cell, scored
against direction-matched random-time controls.

Implements the compute-vs-claim principle from PROTOCOL.md: statistics are
computed and recorded for EVERY cell regardless of sample size; the verdict
field tiers the claim:

    alive                  positive effect, survived BH-FDR, n >= min_n
    parked_weak_effect     positive effect, raw p < alpha, failed FDR
    parked_insufficient_n  n < min_n (stats still recorded)
    dead                   adequately powered, no effect
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from conflab.events import Event, all_detectors
from conflab.indicators import atr
from conflab.stats import _permutation_pvalue, benjamini_hochberg

log = logging.getLogger(__name__)


@dataclass
class Stage1Config:
    horizons: dict = field(default_factory=lambda: {
        "D1": 30, "H4": 20, "H1": 20, "M15": 16})
    warmup: int = 60            # bars excluded at the start (indicator warmup)
    min_n: int = 100            # alive-qualification gate
    control_mult: int = 5       # controls per event
    n_perm: int = 2000
    alpha: float = 0.05
    seed: int = 42
    # Amendment v2.1: controls share each event's hour-of-day, neutralising
    # the session-volatility/ATR-lag confound found in the uniform-control
    # run (see PROTOCOL.md). Set False to reproduce the original analysis.
    hour_matched: bool = True


def directional_outcome(highs: np.ndarray, lows: np.ndarray,
                        closes: np.ndarray, a: np.ndarray, idx: int,
                        direction: int, horizon: int) -> tuple[float, bool] | None:
    """(MFE in event direction within horizon, ATR units; hit +1·ATR before
    −1·ATR). Same-bar ambiguity counts as adverse-first (conservative).
    None when ATR is unusable or no room remains."""
    n = len(closes)
    if idx + 1 >= n:
        return None
    entry = closes[idx]
    unit = a[idx]
    if not np.isfinite(unit) or unit <= 0:
        return None
    end = min(idx + 1 + horizon, n)
    mfe = 0.0
    hit: bool | None = None
    for t in range(idx + 1, end):
        if direction > 0:
            fav = (highs[t] - entry) / unit
            adv = (entry - lows[t]) / unit
        else:
            fav = (entry - lows[t]) / unit
            adv = (highs[t] - entry) / unit
        mfe = max(mfe, fav)
        if hit is None:
            if adv >= 1.0:
                hit = False        # adverse-first tie-break
            elif fav >= 1.0:
                hit = True
    return round(float(mfe), 4), bool(hit)


def screen_cell(df: pd.DataFrame, events: list[Event], horizon: int,
                cfg: Stage1Config, rng: np.random.Generator) -> dict | None:
    """Score one (timeframe × event type) cell. Returns the registry row
    (verdict assigned later, after the family-wide FDR pass)."""
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    a = atr(df).to_numpy()
    n = len(df)

    usable = [e for e in events
              if cfg.warmup <= e.index < n - 1 and e.direction in (-1, +1)]
    outcomes = []
    for e in usable:
        out = directional_outcome(highs, lows, closes, a, e.index,
                                  e.direction, horizon)
        if out is not None:
            outcomes.append(out)
    if not outcomes:
        return None

    # Direction-matched (and, per amendment v2.1, hour-of-day-matched)
    # random-time controls through the identical outcome code path.
    directions = np.array([e.direction for e in usable])
    ctrl_outcomes = []
    lo, hi = cfg.warmup, n - 1 - horizon
    if hi > lo:
        hours = df.index.hour.to_numpy()
        pool_by_hour: dict[int, np.ndarray] = {}
        if cfg.hour_matched:
            valid = np.arange(lo, hi)
            for h in np.unique(hours[valid]):
                pool_by_hour[int(h)] = valid[hours[valid] == h]
        ev_hours = [int(hours[e.index]) for e in usable]
        for _ in range(cfg.control_mult):
            dirs = rng.choice(directions, size=len(usable))
            for e, eh, d in zip(usable, ev_hours, dirs):
                pool = pool_by_hour.get(eh) if cfg.hour_matched else None
                if pool is not None and len(pool):
                    i = int(pool[rng.integers(0, len(pool))])
                else:
                    i = int(rng.integers(lo, hi))
                out = directional_outcome(highs, lows, closes, a, i,
                                          int(d), horizon)
                if out is not None:
                    ctrl_outcomes.append(out)
    if len(ctrl_outcomes) < 10:
        return None

    ev_mfe = np.array([o[0] for o in outcomes])
    ct_mfe = np.array([o[0] for o in ctrl_outcomes])
    p = float(_permutation_pvalue(ev_mfe.copy(), ct_mfe.copy(),
                                  cfg.n_perm, rng))
    return {
        "n": len(outcomes),
        "mean_mfe_atr": round(float(ev_mfe.mean()), 4),
        "control_mfe_atr": round(float(ct_mfe.mean()), 4),
        "effect": round(float(ev_mfe.mean() - ct_mfe.mean()), 4),
        "hit_rate": round(float(np.mean([o[1] for o in outcomes])), 4),
        "control_hit_rate": round(
            float(np.mean([o[1] for o in ctrl_outcomes])), 4),
        "p_value": p,
    }


def run_stage1(frames: dict[str, pd.DataFrame],
               cfg: Stage1Config | None = None,
               screen_end: str | None = None) -> list[dict]:
    """Run the full Stage-1 screen and return the verdict registry.

    ``screen_end``: ISO date; bars after it are excluded (split discipline).
    """
    cfg = cfg or Stage1Config()
    rng = np.random.default_rng(cfg.seed)
    detectors = all_detectors()
    rows: list[dict] = []

    for tf, df in frames.items():
        if screen_end is not None:
            df = df[df.index <= pd.Timestamp(screen_end, tz="UTC")]
        horizon = cfg.horizons.get(tf, 20)
        if len(df) < cfg.warmup + horizon + 50:
            continue
        by_type: dict[str, list[Event]] = {}
        for det_name, detector in detectors.items():
            try:
                for e in detector(df):
                    by_type.setdefault(e.type, []).append(e)
            except Exception as ex:
                log.warning("detector %s failed on %s: %s", det_name, tf, ex)
        for event_type, events in sorted(by_type.items()):
            row = screen_cell(df, events, horizon, cfg, rng)
            if row is None:
                continue
            row.update({"tf": tf, "event_type": event_type})
            rows.append(row)

    # Family-wide FDR over adequately-powered cells; verdicts per protocol.
    powered = [r for r in rows if r["n"] >= cfg.min_n]
    flags = benjamini_hochberg([r["p_value"] for r in powered], cfg.alpha)
    fdr_by_id = {(r["tf"], r["event_type"]): sig
                 for r, sig in zip(powered, flags)}
    for r in rows:
        sig = fdr_by_id.get((r["tf"], r["event_type"]), False)
        positive = r["effect"] > 0
        if r["n"] < cfg.min_n:
            r["verdict"] = "parked_insufficient_n"
        elif positive and sig:
            r["verdict"] = "alive"
        elif positive and r["p_value"] < cfg.alpha:
            r["verdict"] = "parked_weak_effect"
        else:
            r["verdict"] = "dead"
        r["fdr_significant"] = bool(sig)
    return rows


def format_registry(rows: list[dict]) -> str:
    order = {"alive": 0, "parked_weak_effect": 1,
             "parked_insufficient_n": 2, "dead": 3}
    rows = sorted(rows, key=lambda r: (order[r["verdict"]], r["p_value"]))
    lines = ["Stage-1 verdict registry", "=" * 96,
             f"{'tf':<5} {'event_type':<30} {'n':>6} {'evMFE':>7} "
             f"{'ctMFE':>7} {'effect':>7} {'hit%':>6} {'ctHit%':>7} "
             f"{'p':>8}  verdict",
             "-" * 96]
    for r in rows:
        lines.append(
            f"{r['tf']:<5} {r['event_type']:<30} {r['n']:>6} "
            f"{r['mean_mfe_atr']:>7.3f} {r['control_mfe_atr']:>7.3f} "
            f"{r['effect']:>+7.3f} {r['hit_rate']*100:>5.1f}% "
            f"{r['control_hit_rate']*100:>6.1f}% {r['p_value']:>8.4f}  "
            f"{r['verdict']}")
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    lines.append("-" * 96)
    lines.append("  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return "\n".join(lines)
