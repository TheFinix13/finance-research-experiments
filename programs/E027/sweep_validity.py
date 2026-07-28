"""E027 sweep + validity detector — frozen at the pre-registration commit.

Implements PROTOCOL §1 exactly:

* confirmed fractal swings (``conflab.patterns.swing_points``, lookback 5);
* origin swing = most recent confirmed opposite swing before the level's
  swing;
* level ends on a close through it, or after ``max_scan`` bars;
* sweep = wick through the level with a close back inside (first only);
* validity = some bar between the level swing and the sweep bar CLOSED
  beyond the origin swing's price (house BOS close convention).

All inputs to an event emitted at bar ``t`` come from bars ``<= t``.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from conflab.patterns import swing_points


@dataclass(frozen=True)
class ValiditySweep:
    index: int          # sweep bar (event is KNOWN here)
    time: str
    side: str           # "sellside" (swing low swept) | "buyside"
    direction: int      # +1 after sellside, -1 after buyside
    level: float        # the swept swing price
    origin_level: float  # the swing it "came from"
    valid: bool         # BOS-qualified per PROTOCOL §1.4
    swing_index: int
    origin_index: int

    def to_dict(self) -> dict:
        return {
            "index": self.index, "time": self.time, "side": self.side,
            "direction": self.direction, "level": self.level,
            "origin_level": self.origin_level, "valid": self.valid,
            "swing_index": self.swing_index, "origin_index": self.origin_index,
        }


def detect_validity_sweeps(df: pd.DataFrame, lookback: int = 5,
                           max_scan: int = 200) -> list[ValiditySweep]:
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    n = len(df)
    swings = sorted(swing_points(df, lookback), key=lambda s: s.index)
    events: list[ValiditySweep] = []

    for k, s in enumerate(swings):
        # Origin: the most recent opposite swing strictly before this one.
        origin = None
        for j in range(k - 1, -1, -1):
            if swings[j].is_high != s.is_high:
                origin = swings[j]
                break
        if origin is None:
            continue
        conf = s.index + lookback          # confirmation bar
        if conf >= n:
            continue
        level = s.price
        end = min(conf + max_scan, n)
        if s.is_high:
            # Buyside: sweep = high pierces, close back below.
            for t in range(conf, end):
                if highs[t] > level and closes[t] < level:
                    valid = bool(
                        (closes[s.index + 1:t + 1] < origin.price).any())
                    events.append(ValiditySweep(
                        t, str(df.index[t]), "buyside", -1, float(level),
                        float(origin.price), valid, s.index, origin.index))
                    break
                if closes[t] > level:      # clean break ends the level
                    break
        else:
            # Sellside: sweep = low pierces, close back above.
            for t in range(conf, end):
                if lows[t] < level and closes[t] > level:
                    valid = bool(
                        (closes[s.index + 1:t + 1] > origin.price).any())
                    events.append(ValiditySweep(
                        t, str(df.index[t]), "sellside", +1, float(level),
                        float(origin.price), valid, s.index, origin.index))
                    break
                if closes[t] < level:
                    break
    return events
