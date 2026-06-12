"""Session-range liquidity sweeps (intraday only).

Asia range = 00:00–06:59 UTC of the current day. During the London window
(07:00–12:59 UTC), a wick beyond the Asia high that closes back inside is a
sweep → reversal hypothesis (−1 for the high, +1 for the low). One sweep per
side per day. Only emitted when median bar spacing ≤ 1 hour.
"""
from __future__ import annotations

import pandas as pd

from conflab.events import Event


def detect_session_sweeps(df: pd.DataFrame) -> list[Event]:
    if len(df) < 48:
        return []
    spacing = df.index.to_series().diff().median()
    if pd.isna(spacing) or spacing > pd.Timedelta(hours=1):
        return []
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    idx = df.index
    events: list[Event] = []
    cur_day = None
    asia_high = asia_low = None
    swept_high = swept_low = False
    for t in range(len(df)):
        ts = idx[t]
        if ts.date() != cur_day:
            cur_day = ts.date()
            asia_high = asia_low = None
            swept_high = swept_low = False
        hour = ts.hour
        if hour < 7:
            asia_high = highs[t] if asia_high is None else max(asia_high,
                                                               highs[t])
            asia_low = lows[t] if asia_low is None else min(asia_low, lows[t])
        elif 7 <= hour < 13 and asia_high is not None:
            if (not swept_high and highs[t] > asia_high
                    and closes[t] < asia_high):
                events.append(Event(t, str(ts), "asia_high_sweep", -1,
                                    float(asia_high)))
                swept_high = True
            if (not swept_low and lows[t] < asia_low
                    and closes[t] > asia_low):
                events.append(Event(t, str(ts), "asia_low_sweep", +1,
                                    float(asia_low)))
                swept_low = True
    return events
