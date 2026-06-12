"""Pattern-completion and candlestick events.

Double tops/bottoms become events at COMPLETION (first close through the
neckline after the second touch) — that is the moment the pattern is
tradeable knowledge, not at the second touch where hindsight would leak in.
Candlestick events fire on the bar where the pattern closes.
"""
from __future__ import annotations

import pandas as pd

from conflab.events import Event
from conflab.patterns import (
    candle_events,
    detect_double_bottoms,
    detect_double_tops,
)

_CANDLE_DIRECTIONS = {
    "bull_engulfing": +1,
    "bear_engulfing": -1,
    "hammer": +1,
    "shooting_star": -1,
    "bull_pin": +1,
    "bear_pin": -1,
    # doji is directionless — excluded from Stage 1 (no directional
    # hypothesis to score); it returns in Stage 2 as a conditioner.
}


def detect_double_pattern_completions(df: pd.DataFrame,
                                      max_completion_scan: int = 40) -> list[Event]:
    closes = df["close"].to_numpy()
    n = len(df)
    events: list[Event] = []
    for hit, direction in ([(h, +1) for h in detect_double_bottoms(df)]
                           + [(h, -1) for h in detect_double_tops(df)]):
        if hit.neckline is None:
            continue
        second_touch = max(hit.indices)
        for t in range(second_touch + 1,
                       min(second_touch + 1 + max_completion_scan, n)):
            broke = (closes[t] > hit.neckline if direction > 0
                     else closes[t] < hit.neckline)
            if broke:
                events.append(Event(
                    t, str(df.index[t]), f"{hit.kind}_completion",
                    direction, float(hit.neckline),
                    detail=f"touches {hit.indices}"))
                break
    return events


def detect_candle_pattern_events(df: pd.DataFrame) -> list[Event]:
    flags = candle_events(df)
    events: list[Event] = []
    closes = df["close"].to_numpy()
    for name, direction in _CANDLE_DIRECTIONS.items():
        if name not in flags.columns:
            continue
        for t in flags.index[flags[name]]:
            pos = flags.index.get_loc(t)
            events.append(Event(pos, str(t), name, direction,
                                float(closes[pos])))
    return events


def detect_multibar_candle_events(df: pd.DataFrame,
                                  tol_atr: float = 0.1) -> list[Event]:
    """Multi-bar candlestick events: outside bars, tweezers, morning/evening
    stars, three white soldiers / black crows."""
    import numpy as np

    from conflab.indicators import atr

    o = df["open"].to_numpy()
    c = df["close"].to_numpy()
    h = df["high"].to_numpy()
    lo = df["low"].to_numpy()
    a = atr(df).to_numpy()
    n = len(df)
    body = c - o
    events: list[Event] = []
    for t in range(2, n):
        ts = str(df.index[t])
        unit = a[t] if np.isfinite(a[t]) and a[t] > 0 else None
        if unit is None:
            continue
        # outside bar: engulfs prior bar's full range; continuation of its close
        if h[t] > h[t - 1] and lo[t] < lo[t - 1] and abs(body[t]) > 0.25 * unit:
            kind = "outside_bar_bull" if body[t] > 0 else "outside_bar_bear"
            events.append(Event(t, ts, kind, 1 if body[t] > 0 else -1,
                                float(c[t])))
        # tweezers: two near-equal extremes, second bar reversing
        if abs(h[t] - h[t - 1]) <= tol_atr * unit and body[t] < 0 < body[t - 1]:
            events.append(Event(t, ts, "tweezer_top", -1, float(h[t])))
        if abs(lo[t] - lo[t - 1]) <= tol_atr * unit and body[t] > 0 > body[t - 1]:
            events.append(Event(t, ts, "tweezer_bottom", +1, float(lo[t])))
        # morning/evening star (3 bars: thrust, pause, reversal past midpoint)
        if (body[t - 2] < -0.5 * unit and abs(body[t - 1]) < 0.3 * abs(body[t - 2])
                and body[t] > 0 and c[t] > (o[t - 2] + c[t - 2]) / 2):
            events.append(Event(t, ts, "morning_star", +1, float(c[t])))
        if (body[t - 2] > 0.5 * unit and abs(body[t - 1]) < 0.3 * abs(body[t - 2])
                and body[t] < 0 and c[t] < (o[t - 2] + c[t - 2]) / 2):
            events.append(Event(t, ts, "evening_star", -1, float(c[t])))
        # three soldiers / crows
        if all(body[t - k] > 0.5 * unit for k in (0, 1, 2)) and \
                c[t] > c[t - 1] > c[t - 2]:
            events.append(Event(t, ts, "three_white_soldiers", +1,
                                float(c[t])))
        if all(body[t - k] < -0.5 * unit for k in (0, 1, 2)) and \
                c[t] < c[t - 1] < c[t - 2]:
            events.append(Event(t, ts, "three_black_crows", -1, float(c[t])))
    return events
