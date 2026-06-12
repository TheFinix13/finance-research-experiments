"""Supply/demand zones, order blocks, breaker blocks and fair value gaps.

Operational definitions (fixed; see PROTOCOL.md anti-fooling rules):

* **Impulse bar**: |body| > 1.5×ATR.
* **Demand zone**: the full range of the bar preceding an up-impulse
  (drop-base-rally simplified to base-rally). Supply mirror.
* **Order block**: the most recent opposite-body bar within 5 bars before
  the impulse.
* **Touch**: first re-entry into a FRESH zone from outside → bounce
  hypothesis in the zone's direction.
* **Breaker**: a zone whose far edge is closed through; the first retest
  from the other side → continuation of the break (polarity flip),
  emitted as breaker_support_retest (+1) / breaker_resistance_retest (−1).
* **FVG**: 3-bar gap (bullish: low[t] > high[t-2]) larger than 0.1×ATR.
  First touch → bounce hypothesis. A fully closed-through FVG becomes an
  inversion FVG; its first retest → flipped-direction hypothesis.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from conflab.events import Event
from conflab.indicators import atr


def detect_zone_events(df: pd.DataFrame, impulse_atr: float = 1.5,
                       max_age: int = 300) -> list[Event]:
    a = atr(df).to_numpy()
    o = df["open"].to_numpy()
    c = df["close"].to_numpy()
    h = df["high"].to_numpy()
    lo = df["low"].to_numpy()
    n = len(df)
    events: list[Event] = []
    zones: list[dict] = []

    for t in range(2, n):
        # 1) update existing zones (created strictly before t)
        for z in zones:
            if z["state"] == "done" or t <= z["created"] + 1:
                continue
            if t - z["created"] > max_age:
                z["state"] = "done"
                continue
            prev_close = c[t - 1]
            if z["dir"] > 0:
                if z["state"] in ("fresh", "touched") and c[t] < z["bottom"]:
                    z["state"] = "broken"
                    continue
                if (z["state"] == "fresh" and prev_close > z["top"]
                        and lo[t] <= z["top"]):
                    events.append(Event(t, str(df.index[t]), z["touch_type"],
                                        +1, z["top"]))
                    z["state"] = "touched"
                elif (z["state"] == "broken" and prev_close < z["bottom"]
                        and h[t] >= z["bottom"]):
                    events.append(Event(t, str(df.index[t]),
                                        "breaker_resistance_retest", -1,
                                        z["bottom"]))
                    z["state"] = "done"
            else:
                if z["state"] in ("fresh", "touched") and c[t] > z["top"]:
                    z["state"] = "broken"
                    continue
                if (z["state"] == "fresh" and prev_close < z["bottom"]
                        and h[t] >= z["bottom"]):
                    events.append(Event(t, str(df.index[t]), z["touch_type"],
                                        -1, z["bottom"]))
                    z["state"] = "touched"
                elif (z["state"] == "broken" and prev_close > z["top"]
                        and lo[t] <= z["top"]):
                    events.append(Event(t, str(df.index[t]),
                                        "breaker_support_retest", +1,
                                        z["top"]))
                    z["state"] = "done"

        # 2) create zones off a fresh impulse bar
        if not (np.isfinite(a[t]) and a[t] > 0):
            continue
        body = c[t] - o[t]
        if abs(body) <= impulse_atr * a[t]:
            continue
        direction = 1 if body > 0 else -1
        touch = "demand_zone_touch" if direction > 0 else "supply_zone_touch"
        zones.append({"top": float(h[t - 1]), "bottom": float(lo[t - 1]),
                      "dir": direction, "created": t, "state": "fresh",
                      "touch_type": touch})
        # order block: last opposite-body bar within 5 bars before impulse
        for k in range(t - 1, max(t - 6, 0), -1):
            if (c[k] - o[k]) * direction < 0:
                ob_touch = ("bullish_ob_touch" if direction > 0
                            else "bearish_ob_touch")
                zones.append({"top": float(h[k]), "bottom": float(lo[k]),
                              "dir": direction, "created": t,
                              "state": "fresh", "touch_type": ob_touch})
                break
        zones = [z for z in zones if z["state"] != "done"]
    return events


def detect_fvg_events(df: pd.DataFrame, min_gap_atr: float = 0.1,
                      max_age: int = 300) -> list[Event]:
    a = atr(df).to_numpy()
    c = df["close"].to_numpy()
    h = df["high"].to_numpy()
    lo = df["low"].to_numpy()
    n = len(df)
    events: list[Event] = []
    gaps: list[dict] = []

    for t in range(2, n):
        for g in gaps:
            if g["state"] == "done" or t <= g["created"]:
                continue
            if t - g["created"] > max_age:
                g["state"] = "done"
                continue
            prev_close = c[t - 1]
            if g["dir"] > 0:  # bullish FVG below price: support
                if g["state"] in ("fresh", "touched") and c[t] < g["bottom"]:
                    g["state"] = "inverted"
                    continue
                if (g["state"] == "fresh" and prev_close > g["top"]
                        and lo[t] <= g["top"]):
                    events.append(Event(t, str(df.index[t]),
                                        "bullish_fvg_touch", +1, g["top"]))
                    g["state"] = "touched"
                elif (g["state"] == "inverted" and prev_close < g["bottom"]
                        and h[t] >= g["bottom"]):
                    events.append(Event(t, str(df.index[t]),
                                        "inversion_fvg_bearish", -1,
                                        g["bottom"]))
                    g["state"] = "done"
            else:  # bearish FVG above price: resistance
                if g["state"] in ("fresh", "touched") and c[t] > g["top"]:
                    g["state"] = "inverted"
                    continue
                if (g["state"] == "fresh" and prev_close < g["bottom"]
                        and h[t] >= g["bottom"]):
                    events.append(Event(t, str(df.index[t]),
                                        "bearish_fvg_touch", -1, g["bottom"]))
                    g["state"] = "touched"
                elif (g["state"] == "inverted" and prev_close > g["top"]
                        and lo[t] <= g["top"]):
                    events.append(Event(t, str(df.index[t]),
                                        "inversion_fvg_bullish", +1,
                                        g["top"]))
                    g["state"] = "done"

        if not (np.isfinite(a[t]) and a[t] > 0):
            continue
        if lo[t] > h[t - 2] and lo[t] - h[t - 2] > min_gap_atr * a[t]:
            gaps.append({"top": float(lo[t]), "bottom": float(h[t - 2]),
                         "dir": +1, "created": t, "state": "fresh"})
        elif h[t] < lo[t - 2] and lo[t - 2] - h[t] > min_gap_atr * a[t]:
            gaps.append({"top": float(lo[t - 2]), "bottom": float(h[t]),
                         "dir": -1, "created": t, "state": "fresh"})
        gaps = [g for g in gaps if g["state"] != "done"]
    return events
