"""Touch detection and reaction measurement.

The reaction metric answers one question, identically for confluence bands
and random control levels: when price first enters a band from outside, how
far does it bounce *against* the approach direction within a fixed horizon,
in ATR units?

reaction_r > 0  → price bounced off the band (the level "worked")
reaction_r ~ 0  → nothing happened
held            → price never closed beyond the far edge by > 0.5 ATR
                  within the horizon (the band capped the move)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from conflab.indicators import atr


@dataclass(frozen=True)
class Touch:
    index: int            # bar that first entered the band
    from_above: bool      # approach direction (True = price fell into band)
    reaction_atr: float   # max counter-move within horizon, ATR units
    held: bool
    band_low: float
    band_high: float

    def to_dict(self) -> dict:
        return {"index": self.index, "from_above": self.from_above,
                "reaction_atr": self.reaction_atr, "held": self.held,
                "band_low": self.band_low, "band_high": self.band_high}


def find_touches(df: pd.DataFrame, band_low: float, band_high: float,
                 start: int, end: int, horizon: int = 12,
                 max_touches: int = 5) -> list[Touch]:
    """Score touches of [band_low, band_high] occurring in bar range
    [start, end). The horizon may extend past ``end`` (reactions need room)
    but never past the data. After a touch, scanning resumes only once price
    has fully left the band, so one consolidation inside the band is one
    touch, not twenty."""
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    a = atr(df).to_numpy()
    n = len(df)
    end = min(end, n)

    touches: list[Touch] = []
    i = max(start, 1)
    while i < end and len(touches) < max_touches:
        prev_close = closes[i - 1]
        inside = lows[i] <= band_high and highs[i] >= band_low
        was_outside = prev_close > band_high or prev_close < band_low
        if not (inside and was_outside):
            i += 1
            continue
        from_above = prev_close > band_high
        touch_atr = a[i] if np.isfinite(a[i]) and a[i] > 0 else None
        if touch_atr is None:
            i += 1
            continue

        h_end = min(i + 1 + horizon, n)
        ref = band_high if from_above else band_low  # entry edge
        if from_above:
            extreme = highs[i + 1:h_end].max() if h_end > i + 1 else ref
            reaction = (extreme - ref) / touch_atr
            breached = (closes[i:h_end] < band_low - 0.5 * touch_atr).any()
        else:
            extreme = lows[i + 1:h_end].min() if h_end > i + 1 else ref
            reaction = (ref - extreme) / touch_atr
            breached = (closes[i:h_end] > band_high + 0.5 * touch_atr).any()

        touches.append(Touch(
            index=i, from_above=bool(from_above),
            reaction_atr=round(float(max(reaction, 0.0)), 4),
            held=not bool(breached),
            band_low=band_low, band_high=band_high,
        ))
        # Resume after price has fully exited the band.
        j = i + 1
        while j < end and lows[j] <= band_high and highs[j] >= band_low:
            j += 1
        i = j
    return touches
