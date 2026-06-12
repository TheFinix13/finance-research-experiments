"""Market-structure events: break of structure (BOS), change of character
(CHoCH) and premium/discount equilibrium crossings, built causally."""
from __future__ import annotations

import pandas as pd

from conflab.events import Event
from conflab.patterns import swing_points


def detect_bos_choch(df: pd.DataFrame, lookback: int = 5) -> list[Event]:
    """BOS = close beyond the most recent CONFIRMED opposite swing in the
    prevailing direction; CHoCH = the first such break AGAINST the prevailing
    structure. Both are continuation hypotheses: direction = break direction.

    A swing at bar i is only usable from bar i+lookback (confirmation lag),
    so no event ever sees the future.
    """
    n = len(df)
    closes = df["close"].to_numpy()
    confirmed = sorted(
        ((s.index + lookback, s) for s in swing_points(df, lookback)
         if s.index + lookback < n),
        key=lambda t: t[0],
    )
    events: list[Event] = []
    last_high: float | None = None
    last_low: float | None = None
    state = 0  # +1 bullish structure, -1 bearish, 0 unknown
    ci = 0
    for t in range(lookback * 2, n):
        while ci < len(confirmed) and confirmed[ci][0] <= t:
            s = confirmed[ci][1]
            if s.is_high:
                last_high = s.price
            else:
                last_low = s.price
            ci += 1
        if last_high is not None and closes[t] > last_high:
            kind = "choch_bullish" if state == -1 else "bos_bullish"
            events.append(Event(t, str(df.index[t]), kind, +1,
                                float(last_high)))
            state = +1
            last_high = None  # consumed; wait for the next confirmed high
        elif last_low is not None and closes[t] < last_low:
            kind = "choch_bearish" if state == +1 else "bos_bearish"
            events.append(Event(t, str(df.index[t]), kind, -1,
                                float(last_low)))
            state = -1
            last_low = None
    return events


def detect_premium_discount_events(df: pd.DataFrame,
                                   window: int = 100) -> list[Event]:
    """Equilibrium crossings of the trailing ``window``-bar range: a close
    crossing below the midpoint enters DISCOUNT (value-buy hypothesis, +1);
    crossing above enters PREMIUM (value-sell, −1). Trailing extremes only —
    strictly causal."""
    if len(df) < window + 2:
        return []
    closes = df["close"]
    hi = df["high"].rolling(window).max().shift(1)
    lo = df["low"].rolling(window).min().shift(1)
    mid = ((hi + lo) / 2).to_numpy()
    c = closes.to_numpy()
    events: list[Event] = []
    for t in range(window + 1, len(df)):
        m = mid[t]
        if not pd.notna(m):
            continue
        if c[t - 1] >= m > c[t]:
            events.append(Event(t, str(df.index[t]), "entered_discount", +1,
                                float(m)))
        elif c[t - 1] <= m < c[t]:
            events.append(Event(t, str(df.index[t]), "entered_premium", -1,
                                float(m)))
    return events
