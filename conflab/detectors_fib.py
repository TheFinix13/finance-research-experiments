"""Fibonacci events on the most recent significant impulse leg.

Leg = the last two alternating confirmed swings, qualified by size
(≥ 3×ATR). Retracement tags (38.2 / 50 / 61.8 / 78.6 and the 61.8–78.6 OTE
zone) hypothesise continuation in the leg direction; extension touches
(127.2 / 161.8 beyond the leg) hypothesise exhaustion AGAINST the leg.
A leg dies when price closes beyond its origin (full retrace) or a newer
qualified leg replaces it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from conflab.events import Event
from conflab.indicators import atr
from conflab.patterns import swing_points

RETRACE_LEVELS = {"fib_382_tag": 0.382, "fib_50_tag": 0.5,
                  "fib_618_tag": 0.618, "fib_786_tag": 0.786}
EXT_LEVELS = {"fib_ext_1272_tag": 1.272, "fib_ext_1618_tag": 1.618}


def detect_fib_events(df: pd.DataFrame, lookback: int = 5,
                      min_leg_atr: float = 3.0,
                      max_age: int = 150) -> list[Event]:
    n = len(df)
    a = atr(df).to_numpy()
    c = df["close"].to_numpy()
    h = df["high"].to_numpy()
    lo = df["low"].to_numpy()
    sw = sorted(swing_points(df, lookback), key=lambda s: s.index)
    confirmed = [(s.index + lookback, s) for s in sw if s.index + lookback < n]

    events: list[Event] = []
    leg = None  # {start_price, end_price, dir, born, tagged:set}
    ci = 0
    for t in range(lookback * 2, n):
        while ci < len(confirmed) and confirmed[ci][0] <= t:
            conf_idx, s = confirmed[ci]
            ci += 1
            prev = confirmed[ci - 2][1] if ci >= 2 else None
            if prev is None or prev.is_high == s.is_high:
                continue
            size = abs(s.price - prev.price)
            if np.isfinite(a[conf_idx]) and size >= min_leg_atr * a[conf_idx]:
                leg = {"start": prev.price, "end": s.price,
                       "dir": 1 if s.price > prev.price else -1,
                       "born": conf_idx, "tagged": set()}
        if leg is None or t <= leg["born"]:
            continue
        if t - leg["born"] > max_age:
            leg = None
            continue
        rng = leg["end"] - leg["start"]
        # leg invalidated on close beyond its origin
        if (leg["dir"] > 0 and c[t] < leg["start"]) or \
           (leg["dir"] < 0 and c[t] > leg["start"]):
            leg = None
            continue
        prev_close = c[t - 1]
        ts = str(df.index[t])
        for name, frac in RETRACE_LEVELS.items():
            if name in leg["tagged"]:
                continue
            level = leg["end"] - rng * frac
            if leg["dir"] > 0:
                if prev_close > level and lo[t] <= level:
                    events.append(Event(t, ts, name, +1, float(level)))
                    leg["tagged"].add(name)
            else:
                if prev_close < level and h[t] >= level:
                    events.append(Event(t, ts, name, -1, float(level)))
                    leg["tagged"].add(name)
        # OTE zone entry (61.8–78.6)
        if "ote_tag" not in leg["tagged"]:
            z_hi = leg["end"] - rng * 0.618
            z_lo = leg["end"] - rng * 0.786
            lo_z, hi_z = min(z_lo, z_hi), max(z_lo, z_hi)
            inside = lo[t] <= hi_z and h[t] >= lo_z
            was_out = prev_close > hi_z if leg["dir"] > 0 else prev_close < lo_z
            if inside and was_out:
                events.append(Event(t, ts, "ote_tag", leg["dir"],
                                    float((lo_z + hi_z) / 2)))
                leg["tagged"].add("ote_tag")
        for name, frac in EXT_LEVELS.items():
            if name in leg["tagged"]:
                continue
            level = leg["start"] + rng * frac
            if leg["dir"] > 0:
                if prev_close < level and h[t] >= level:
                    events.append(Event(t, ts, name, -1, float(level)))
                    leg["tagged"].add(name)
            else:
                if prev_close > level and lo[t] <= level:
                    events.append(Event(t, ts, name, +1, float(level)))
                    leg["tagged"].add(name)
    return events
