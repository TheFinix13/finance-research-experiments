"""Trendline and channel events, built causally from confirmed swing pairs.

Operational definitions:

* **Trendline**: the line through the TWO most recent confirmed swing highs
  (resistance) or lows (support), valid only if no close breached it between
  the anchors. Known from the second anchor's confirmation bar; projected
  at most ``max_proj`` bars forward.
* **Touch**: bar reaches the line from the inside while the previous close
  was clearly away → bounce hypothesis (resistance −1 / support +1).
* **Break + retest**: close through the line by > tol, then first return to
  the line from the other side → continuation of the break.
* **Channel**: a valid support (resistance) trendline plus a parallel line
  through the most extreme opposite swing between the anchors. Touch of the
  channel top → −1, bottom → +1 (the user's ascending-channel case).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from conflab.events import Event
from conflab.indicators import atr
from conflab.patterns import swing_points


def _line_valid(closes: np.ndarray, slope: float, intercept: float,
                i1: int, i2: int, tol: float, is_resistance: bool) -> bool:
    for t in range(i1, i2 + 1):
        val = slope * t + intercept
        if is_resistance and closes[t] > val + tol:
            return False
        if (not is_resistance) and closes[t] < val - tol:
            return False
    return True


def detect_trendline_events(df: pd.DataFrame, lookback: int = 5,
                            tol_atr: float = 0.25,
                            max_proj: int = 60) -> list[Event]:
    n = len(df)
    a = atr(df).to_numpy()
    c = df["close"].to_numpy()
    h = df["high"].to_numpy()
    lo = df["low"].to_numpy()
    sw = swing_points(df, lookback)
    events: list[Event] = []
    lines: list[dict] = []
    last_seen: dict[bool, list] = {True: [], False: []}  # is_high -> swings

    confirmed = sorted(((s.index + lookback, s) for s in sw
                        if s.index + lookback < n), key=lambda x: x[0])
    ci = 0
    for t in range(lookback * 2, n):
        # absorb newly confirmed swings; build lines on each new pair
        while ci < len(confirmed) and confirmed[ci][0] <= t:
            conf_idx, s = confirmed[ci]
            ci += 1
            group = last_seen[s.is_high]
            group.append(s)
            if len(group) >= 2:
                s1, s2 = group[-2], group[-1]
                if s2.index == s1.index:
                    continue
                slope = (s2.price - s1.price) / (s2.index - s1.index)
                intercept = s1.price - slope * s1.index
                tol = tol_atr * a[conf_idx] if np.isfinite(a[conf_idx]) else 0
                if tol <= 0 or not _line_valid(c, slope, intercept, s1.index,
                                               s2.index, tol, s.is_high):
                    continue
                line = {"slope": slope, "intercept": intercept,
                        "is_res": s.is_high, "start": conf_idx,
                        "anchor2": s2.index, "state": "active"}
                # parallel channel boundary: most extreme opposite excursion
                # between the anchors
                seg = range(s1.index, s2.index + 1)
                if s.is_high:
                    offs = min(lo[k] - (slope * k + intercept) for k in seg)
                else:
                    offs = max(h[k] - (slope * k + intercept) for k in seg)
                if abs(offs) > 2 * tol:  # a real channel, not a flat overlap
                    line["channel_offset"] = float(offs)
                lines.append(line)

        # evaluate active lines at bar t
        for ln in lines:
            if ln["state"] == "done" or t <= ln["start"]:
                continue
            if t - ln["anchor2"] > max_proj:
                ln["state"] = "done"
                continue
            val = ln["slope"] * t + ln["intercept"]
            tol = tol_atr * a[t] if np.isfinite(a[t]) else 0.0
            if tol <= 0:
                continue
            prev_close = c[t - 1]
            ts = str(df.index[t])
            if ln["is_res"]:
                if ln["state"] == "active":
                    if h[t] > val + tol and c[t] < val - tol:
                        # wick through the line, close back inside:
                        # trendline liquidity swept → reversal hypothesis
                        events.append(Event(t, ts,
                                            "trendline_liquidity_sweep_high",
                                            -1, float(val)))
                        ln["state"] = "cooling"
                    elif c[t] > val + tol:
                        ln["state"] = "broken"
                    elif prev_close < val - tol and h[t] >= val - tol:
                        events.append(Event(t, ts,
                                            "trendline_resistance_touch",
                                            -1, float(val)))
                        ln["state"] = "cooling"
                elif ln["state"] == "cooling" and c[t] < val - tol:
                    ln["state"] = "active"  # re-armed after moving away
                elif (ln["state"] == "broken" and prev_close > val + tol
                        and lo[t] <= val + tol):
                    events.append(Event(t, ts,
                                        "trendline_break_retest_bullish",
                                        +1, float(val)))
                    ln["state"] = "done"
            else:
                if ln["state"] == "active":
                    if lo[t] < val - tol and c[t] > val + tol:
                        events.append(Event(t, ts,
                                            "trendline_liquidity_sweep_low",
                                            +1, float(val)))
                        ln["state"] = "cooling"
                    elif c[t] < val - tol:
                        ln["state"] = "broken"
                    elif prev_close > val + tol and lo[t] <= val + tol:
                        events.append(Event(t, ts, "trendline_support_touch",
                                            +1, float(val)))
                        ln["state"] = "cooling"
                elif ln["state"] == "cooling" and c[t] > val + tol:
                    ln["state"] = "active"
                elif (ln["state"] == "broken" and prev_close < val - tol
                        and h[t] >= val - tol):
                    events.append(Event(t, ts,
                                        "trendline_break_retest_bearish",
                                        -1, float(val)))
                    ln["state"] = "done"

            # channel boundary (opposite side of the trendline)
            offset = ln.get("channel_offset")
            if offset is not None and ln["state"] in ("active", "cooling"):
                cval = val + offset
                if ln["is_res"]:  # channel bottom below a resistance line
                    if prev_close > cval + tol and lo[t] <= cval + tol:
                        events.append(Event(t, ts, "channel_bottom_touch",
                                            +1, float(cval)))
                else:             # channel top above a support line
                    if prev_close < cval - tol and h[t] >= cval - tol:
                        events.append(Event(t, ts, "channel_top_touch",
                                            -1, float(cval)))
        lines = [ln for ln in lines if ln["state"] != "done"]
    return events
