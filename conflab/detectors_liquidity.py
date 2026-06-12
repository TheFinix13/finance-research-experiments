"""Liquidity events: equal-extreme pools (magnets) and their sweeps
(rejections)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from conflab.events import Event
from conflab.indicators import atr
from conflab.patterns import swing_points


def detect_liquidity_events(df: pd.DataFrame, lookback: int = 5,
                            tol_atr: float = 0.25,
                            max_scan: int = 200) -> list[Event]:
    """Two consecutive confirmed swing highs within tol → an equal-highs
    pool (resting buy-side liquidity). Pool FORMATION is a magnet
    hypothesis: price is drawn toward it (+1 for pools above, -1 below).
    A SWEEP — wick through the pool with a close back inside — is a
    rejection hypothesis in the opposite direction. Mirror logic for lows.
    """
    n = len(df)
    a = atr(df).to_numpy()
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    sw = swing_points(df, lookback)
    events: list[Event] = []

    for is_high in (True, False):
        group = [s for s in sw if s.is_high == is_high]
        for i in range(1, len(group)):
            s1, s2 = group[i - 1], group[i]
            conf = s2.index + lookback
            if conf >= n:
                continue
            tol = tol_atr * a[conf]
            if not np.isfinite(tol) or tol <= 0:
                continue
            if abs(s1.price - s2.price) > tol:
                continue
            level = max(s1.price, s2.price) if is_high else min(s1.price, s2.price)
            events.append(Event(
                conf, str(df.index[conf]),
                "equal_highs_pool" if is_high else "equal_lows_pool",
                +1 if is_high else -1, float(level),
                detail=f"swings {s1.index},{s2.index}"))

            # First pierce-and-reject after formation = sweep; a clean close
            # through the pool ends the pool without a sweep.
            for t in range(conf + 1, min(conf + 1 + max_scan, n)):
                if is_high:
                    if highs[t] > level and closes[t] < level:
                        events.append(Event(t, str(df.index[t]),
                                            "liquidity_sweep_high", -1,
                                            float(level)))
                        break
                    if closes[t] > level:
                        break
                else:
                    if lows[t] < level and closes[t] > level:
                        events.append(Event(t, str(df.index[t]),
                                            "liquidity_sweep_low", +1,
                                            float(level)))
                        break
                    if closes[t] < level:
                        break
    return events
