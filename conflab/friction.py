"""Friction-score components for Test B (impulse-origin return → bounce).

The four components measure how "messy" the path between impulse-end and
the return-touch is. Each is a pure function of an OHLCV frame and a
[start_idx, end_idx] index pair. The aggregator z-scores each component
against a frozen reference distribution (from the EURUSD screen split,
per `protocols/TEST_B_PROTOCOL.md` §4) and sums.

Conventions:
* index ranges are INCLUSIVE on both ends.
* If start_idx == end_idx (touch on the impulse-end bar itself), the path
  is one bar; oscillation_count = 0, time_in_chop_band uses that one bar,
  wick_density is computed for that bar only.
* All functions return Python floats (or ints) for trivial JSON
  serialisation.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from conflab.indicators import atr


@dataclass(frozen=True)
class FrictionComponents:
    wick_density: float
    oscillation_count: int
    path_drawdown_ratio: float
    time_in_chop_band: float

    def as_dict(self) -> dict:
        return {
            "wick_density": float(self.wick_density),
            "oscillation_count": int(self.oscillation_count),
            "path_drawdown_ratio": float(self.path_drawdown_ratio),
            "time_in_chop_band": float(self.time_in_chop_band),
        }


def wick_density(df: pd.DataFrame, start_idx: int, end_idx: int) -> float:
    """Mean over path bars of (upper_wick + lower_wick) / range.

    range == 0 contributes 0 (a perfect doji-like flat bar has no wicks).
    """
    if end_idx < start_idx:
        return 0.0
    o = df["open"].to_numpy()
    h = df["high"].to_numpy()
    l = df["low"].to_numpy()
    c = df["close"].to_numpy()
    n = len(df)
    end_idx = min(end_idx, n - 1)
    body_top = np.maximum(o[start_idx:end_idx + 1], c[start_idx:end_idx + 1])
    body_bot = np.minimum(o[start_idx:end_idx + 1], c[start_idx:end_idx + 1])
    upper = h[start_idx:end_idx + 1] - body_top
    lower = body_bot - l[start_idx:end_idx + 1]
    rng = h[start_idx:end_idx + 1] - l[start_idx:end_idx + 1]
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(rng > 0, (upper + lower) / rng, 0.0)
    return float(np.mean(ratio)) if ratio.size else 0.0


def oscillation_count(df: pd.DataFrame, start_idx: int, end_idx: int,
                      *, atr_at_idx: int | None = None,
                      threshold_mult: float = 0.5) -> int:
    """ZigZag swing count on closes over [start_idx, end_idx] with a
    threshold of ``threshold_mult × ATR(20)`` evaluated at ``atr_at_idx``
    (defaults to ``end_idx``).

    A swing is each time the running extreme reverses by ≥ threshold from
    the last anchor in the OPPOSITE direction. The first leg (initial
    direction set) does not count; only confirmed reversals do.
    """
    if end_idx <= start_idx:
        return 0
    if atr_at_idx is None:
        atr_at_idx = end_idx
    a = atr(df, period=20).to_numpy()
    n = len(df)
    if not (np.isfinite(a[atr_at_idx]) and a[atr_at_idx] > 0):
        return 0
    threshold = threshold_mult * float(a[atr_at_idx])
    closes = df["close"].to_numpy()[start_idx:end_idx + 1]
    if len(closes) < 2:
        return 0
    last_anchor = float(closes[0])
    extreme = float(closes[0])
    direction: int = 0  # +1 going up, -1 going down, 0 unset
    swings = 0
    for x in closes[1:]:
        x = float(x)
        if direction == 0:
            if x - last_anchor >= threshold:
                direction = +1
                extreme = x
            elif last_anchor - x >= threshold:
                direction = -1
                extreme = x
            continue
        if direction > 0:
            if x > extreme:
                extreme = x
            elif extreme - x >= threshold:
                swings += 1
                direction = -1
                last_anchor = extreme
                extreme = x
        else:
            if x < extreme:
                extreme = x
            elif x - extreme >= threshold:
                swings += 1
                direction = +1
                last_anchor = extreme
                extreme = x
    return swings


def path_drawdown_ratio(df: pd.DataFrame, start_idx: int, end_idx: int,
                        *, impulse_top: float, impulse_bottom: float,
                        direction: int) -> float:
    """Up: (impulse_top − path_low) / impulse_height. Down mirrors.

    Higher = path penetrated further from the leg's "winning" end.
    A ratio of 1.0 means the path retraced the entire impulse exactly.
    """
    impulse_height = impulse_top - impulse_bottom
    if impulse_height <= 0:
        return 0.0
    n = len(df)
    end_idx = min(end_idx, n - 1)
    if end_idx < start_idx:
        return 0.0
    if direction > 0:
        path_low = float(df["low"].to_numpy()[start_idx:end_idx + 1].min())
        return (impulse_top - path_low) / impulse_height
    else:
        path_high = float(df["high"].to_numpy()[start_idx:end_idx + 1].max())
        return (path_high - impulse_bottom) / impulse_height


def time_in_chop_band(df: pd.DataFrame, start_idx: int, end_idx: int,
                      *, origin_zone_mid: float,
                      atr_at_idx: int | None = None,
                      band_mult: float = 0.5) -> float:
    """Share of path bars whose close is within ``band_mult × ATR(20)``
    of the origin-zone midline (ATR evaluated at ``atr_at_idx``)."""
    if end_idx < start_idx:
        return 0.0
    if atr_at_idx is None:
        atr_at_idx = end_idx
    a = atr(df, period=20).to_numpy()
    if not (np.isfinite(a[atr_at_idx]) and a[atr_at_idx] > 0):
        return 0.0
    band = band_mult * float(a[atr_at_idx])
    closes = df["close"].to_numpy()[start_idx:end_idx + 1]
    inside = np.abs(closes - origin_zone_mid) < band
    return float(inside.mean()) if inside.size else 0.0


def components(df: pd.DataFrame, *, impulse_end_idx: int,
               touch_idx: int, impulse_top: float, impulse_bottom: float,
               direction: int, origin_zone_mid: float) -> FrictionComponents:
    """Compute all four components for one event."""
    return FrictionComponents(
        wick_density=wick_density(df, impulse_end_idx, touch_idx),
        oscillation_count=oscillation_count(df, impulse_end_idx, touch_idx,
                                            atr_at_idx=touch_idx),
        path_drawdown_ratio=path_drawdown_ratio(
            df, impulse_end_idx, touch_idx,
            impulse_top=impulse_top, impulse_bottom=impulse_bottom,
            direction=direction),
        time_in_chop_band=time_in_chop_band(
            df, impulse_end_idx, touch_idx,
            origin_zone_mid=origin_zone_mid, atr_at_idx=touch_idx),
    )


def aggregate(comp: FrictionComponents,
              ref: dict[str, tuple[float, float]]) -> float:
    """Aggregate to the friction score: simple sum of z-scored components.

    ``ref`` maps each component name to its (mean, std) on the frozen
    reference distribution (EURUSD screen split). std == 0 contributes 0
    for that component (component is degenerate on the reference).
    """
    keys = ("wick_density", "oscillation_count", "path_drawdown_ratio",
            "time_in_chop_band")
    score = 0.0
    d = comp.as_dict()
    for k in keys:
        mu, sigma = ref[k]
        if sigma > 0:
            score += (float(d[k]) - mu) / sigma
    return score


def fit_reference(component_records: list[dict]) -> dict[str, tuple[float, float]]:
    """Compute per-component (mean, std) from a list of friction-component
    dicts (the EURUSD screen-split events). Frozen by Stage 1 and reused
    for every subsequent stage and pair (per protocol §4)."""
    keys = ("wick_density", "oscillation_count", "path_drawdown_ratio",
            "time_in_chop_band")
    out: dict[str, tuple[float, float]] = {}
    for k in keys:
        arr = np.array([float(r[k]) for r in component_records], dtype=float)
        if arr.size == 0:
            out[k] = (0.0, 0.0)
            continue
        out[k] = (float(arr.mean()), float(arr.std(ddof=0)))
    return out


def quartile_cutoffs(scores: list[float]) -> tuple[float, float, float]:
    """Return (Q1, Q2, Q3) cutoffs of the friction-score array. Frozen
    after Stage 1 and used as Q1/Q2/Q3 boundaries for every subsequent
    stage and pair (protocol §4)."""
    arr = np.asarray(scores, dtype=float)
    if arr.size == 0:
        return (0.0, 0.0, 0.0)
    q1, q2, q3 = np.quantile(arr, [0.25, 0.5, 0.75])
    return (float(q1), float(q2), float(q3))


def assign_quartile(score: float,
                    cutoffs: tuple[float, float, float]) -> int:
    """Return 1, 2, 3, or 4 (Q1 = lowest friction, Q4 = highest).
    Ties at a boundary go to the lower quartile."""
    q1, q2, q3 = cutoffs
    if score <= q1:
        return 1
    if score <= q2:
        return 2
    if score <= q3:
        return 3
    return 4
