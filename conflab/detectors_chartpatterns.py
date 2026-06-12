"""Multi-swing chart patterns: triple tops/bottoms, head & shoulders,
triangles, wedges, flags and rectangles. All emit events at COMPLETION
(the breakout/neckline close) — the first bar at which the pattern is
tradeable knowledge.

Implementations are deliberately simple, auditable operational definitions
built on the alternating confirmed-swing sequence (see REPORT.md §3.2 for
the full definitions and their limitations).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from conflab.events import Event
from conflab.indicators import atr
from conflab.patterns import swing_points


def _alternating(swings: list) -> list:
    """Collapse consecutive same-side swings to the more extreme one."""
    out: list = []
    for s in sorted(swings, key=lambda s: s.index):
        if out and out[-1].is_high == s.is_high:
            keep_new = (s.price > out[-1].price) == s.is_high
            if keep_new:
                out[-1] = s
        else:
            out.append(s)
    return out


def _completion(closes: np.ndarray, start: int, level: float,
                direction: int, max_scan: int) -> int | None:
    """First bar after ``start`` closing through ``level`` in ``direction``."""
    for t in range(start, min(start + max_scan, len(closes))):
        if direction > 0 and closes[t] > level:
            return t
        if direction < 0 and closes[t] < level:
            return t
    return None


def detect_chart_pattern_events(df: pd.DataFrame, lookback: int = 5,
                                tol_atr: float = 0.5,
                                max_scan: int = 40) -> list[Event]:
    n = len(df)
    a = atr(df).to_numpy()
    c = df["close"].to_numpy()
    seq = _alternating(swing_points(df, lookback))
    events: list[Event] = []
    seen: set[tuple] = set()

    def emit(kind: str, t: int, direction: int, level: float, key: tuple):
        if key in seen or t >= n:
            return
        seen.add(key)
        events.append(Event(t, str(df.index[t]), kind, direction,
                            float(level), detail=str(key[1])))

    for i in range(4, len(seq)):
        s = seq[i]
        conf = s.index + lookback          # sequence known from here
        if conf >= n:
            continue
        tol = tol_atr * a[conf] if np.isfinite(a[conf]) else 0.0
        if tol <= 0:
            continue
        w5 = seq[i - 4:i + 1]              # five alternating swings
        prices = [x.price for x in w5]

        if s.is_high:                       # H-L-H-L-H window
            h1, l1, h2, l2, h3 = prices
            neck = min(l1, l2)
            # triple top: three highs level
            if abs(h1 - h2) <= tol and abs(h2 - h3) <= tol:
                t = _completion(c, conf, neck - tol * 0.0, -1, max_scan)
                if t:
                    emit("triple_top_completion", t, -1, neck,
                         ("tt", s.index))
            # head & shoulders: middle high dominant, shoulders level
            elif (h2 > h1 + tol and h2 > h3 + tol and abs(h1 - h3) <= 2 * tol):
                t = _completion(c, conf, neck, -1, max_scan)
                if t:
                    emit("hs_completion", t, -1, neck, ("hs", s.index))
            # ascending triangle: flat highs + rising lows
            if abs(h1 - h2) <= tol and abs(h2 - h3) <= tol and l2 > l1 + tol:
                t = _completion(c, conf, max(h1, h2, h3), +1, max_scan)
                if t:
                    emit("ascending_triangle_breakout", t, +1,
                         max(h1, h2, h3), ("at", s.index))
            # rising wedge: rising highs + rising lows, contracting
            if (h2 > h1 + tol and h3 > h2 + tol and l2 > l1 + tol
                    and (h3 - l2) < (h2 - l1)):
                t = _completion(c, conf, l2, -1, max_scan)
                if t:
                    emit("rising_wedge_breakdown", t, -1, l2,
                         ("rw", s.index))
            # symmetrical triangle: falling highs + rising lows
            if h2 < h1 - tol and h3 < h2 - tol and l2 > l1 + tol:
                t_up = _completion(c, conf, h3, +1, max_scan)
                t_dn = _completion(c, conf, l2, -1, max_scan)
                if t_up and (not t_dn or t_up <= t_dn):
                    emit("symmetrical_triangle_breakout_up", t_up, +1, h3,
                         ("sy", s.index))
                elif t_dn:
                    emit("symmetrical_triangle_breakout_down", t_dn, -1, l2,
                         ("sy", s.index))
        else:                                # L-H-L-H-L window
            l1, h1, l2, h2, l3 = prices
            neck = max(h1, h2)
            if abs(l1 - l2) <= tol and abs(l2 - l3) <= tol:
                t = _completion(c, conf, neck, +1, max_scan)
                if t:
                    emit("triple_bottom_completion", t, +1, neck,
                         ("tb", s.index))
            elif (l2 < l1 - tol and l2 < l3 - tol and abs(l1 - l3) <= 2 * tol):
                t = _completion(c, conf, neck, +1, max_scan)
                if t:
                    emit("inverse_hs_completion", t, +1, neck,
                         ("ihs", s.index))
            if abs(l1 - l2) <= tol and abs(l2 - l3) <= tol and h2 < h1 - tol:
                t = _completion(c, conf, min(l1, l2, l3), -1, max_scan)
                if t:
                    emit("descending_triangle_breakout", t, -1,
                         min(l1, l2, l3), ("dt", s.index))
            if (l2 < l1 - tol and l3 < l2 - tol and h2 < h1 - tol
                    and (h2 - l3) < (h1 - l2)):
                t = _completion(c, conf, h2, +1, max_scan)
                if t:
                    emit("falling_wedge_breakout", t, +1, h2,
                         ("fw", s.index))
    return events


def detect_flag_events(df: pd.DataFrame, impulse_atr: float = 2.5,
                       impulse_bars: int = 6, max_flag_bars: int = 15,
                       flag_width_atr: float = 1.5) -> list[Event]:
    """Flag/pennant: a sharp impulse, then a tight counter-drift; breakout
    beyond the impulse extreme = continuation."""
    n = len(df)
    a = atr(df).to_numpy()
    c = df["close"].to_numpy()
    h = df["high"].to_numpy()
    lo = df["low"].to_numpy()
    events: list[Event] = []
    t = impulse_bars
    while t < n - 2:
        if not (np.isfinite(a[t]) and a[t] > 0):
            t += 1
            continue
        move = c[t] - c[t - impulse_bars]
        if abs(move) < impulse_atr * a[t]:
            t += 1
            continue
        direction = 1 if move > 0 else -1
        extreme = h[t] if direction > 0 else lo[t]
        fired = False
        for k in range(t + 2, min(t + 2 + max_flag_bars, n)):
            # flag bars exclude the candidate breakout bar k itself
            width = h[t + 1:k].max() - lo[t + 1:k].min()
            if width > flag_width_atr * a[t]:
                break  # consolidation too loose — not a flag
            if direction > 0 and c[k] > extreme:
                events.append(Event(k, str(df.index[k]),
                                    "bull_flag_breakout", +1,
                                    float(extreme)))
                fired = True
                break
            if direction < 0 and c[k] < extreme:
                events.append(Event(k, str(df.index[k]),
                                    "bear_flag_breakout", -1,
                                    float(extreme)))
                fired = True
                break
        t = (k if fired else t) + 1
    return events


def detect_rectangle_events(df: pd.DataFrame, window: int = 20,
                            width_atr: float = 1.5,
                            cooldown: int = 20) -> list[Event]:
    """Tight consolidation range break: over the trailing ``window`` bars the
    high-low envelope is < width_atr×ATR; a close beyond it is a breakout
    (continuation hypothesis in the break direction)."""
    n = len(df)
    a = atr(df).to_numpy()
    c = df["close"].to_numpy()
    h = df["high"].to_numpy()
    lo = df["low"].to_numpy()
    events: list[Event] = []
    last_fire = -10**9
    for t in range(window + 1, n):
        if t - last_fire < cooldown:
            continue
        if not (np.isfinite(a[t]) and a[t] > 0):
            continue
        hi_band = h[t - window:t].max()
        lo_band = lo[t - window:t].min()
        if hi_band - lo_band > width_atr * a[t]:
            continue
        if c[t] > hi_band:
            events.append(Event(t, str(df.index[t]), "rectangle_breakout_up",
                                +1, float(hi_band)))
            last_fire = t
        elif c[t] < lo_band:
            events.append(Event(t, str(df.index[t]),
                                "rectangle_breakout_down", -1,
                                float(lo_band)))
            last_fire = t
    return events
