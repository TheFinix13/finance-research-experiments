"""Horizontal-level events: round numbers, S/R polarity-flip retests and
previous-day high/low touches. All are bounce hypotheses (direction against
the approach)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from conflab.events import Event
from conflab.patterns import detect_sr_flips


def detect_round_number_touches(df: pd.DataFrame, grid: float = 0.0050,
                                clearance_frac: float = 0.3) -> list[Event]:
    """Touch of a psychological grid level (default every 50 pips:
    x.x000 / x.x500). Event when a bar's range reaches a grid level the
    previous close was clearly away from (≥ ``clearance_frac``×grid).
    Approach from above → support test (+1); from below → resistance (−1).
    Nearest grid level only, one event per bar."""
    closes = df["close"].to_numpy()
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    events: list[Event] = []
    for t in range(1, len(df)):
        prev = closes[t - 1]
        level = round(prev / grid) * grid
        if abs(prev - level) < clearance_frac * grid:
            continue  # already sitting on it — no fresh approach
        if not (lows[t] <= level <= highs[t]):
            continue
        direction = +1 if prev > level else -1
        events.append(Event(t, str(df.index[t]), "round_number_touch",
                            direction, float(level)))
    return events


def detect_sr_flip_events(df: pd.DataFrame, lookback: int = 5) -> list[Event]:
    """Polarity-flip retests as events at the RETEST bar: old support
    retested from below rejects price down (−1); old resistance retested
    from above supports it (+1)."""
    events: list[Event] = []
    for hit in detect_sr_flips(df, lookback=lookback):
        retest_idx = hit.indices[-1]
        direction = +1 if hit.kind == "sr_flip_support" else -1
        events.append(Event(retest_idx, str(df.index[retest_idx]), hit.kind,
                            direction, hit.level))
    return events


def detect_pdh_pdl_touches(df: pd.DataFrame,
                           clearance_atr: float = 0.25) -> list[Event]:
    """Touches of the previous UTC day's high/low. PDH touched from below
    → rejection hypothesis (−1); PDL from above → bounce (+1). Skipped on
    timeframes ≥ D1 (the level is the bar itself)."""
    if len(df) < 20:
        return []
    # Median bar spacing >= 1 day means PDH/PDL is degenerate here.
    spacing = df.index.to_series().diff().median()
    if pd.isna(spacing) or spacing >= pd.Timedelta(days=1):
        return []
    from conflab.indicators import atr as _atr
    a = _atr(df).to_numpy()
    daily = df.resample("1D").agg({"high": "max", "low": "min"}).dropna()
    pdh = daily["high"].shift(1)
    pdl = daily["low"].shift(1)
    dates = df.index.floor("D")
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    events: list[Event] = []
    for t in range(1, len(df)):
        day = dates[t]
        if day not in pdh.index:
            continue
        h_level, l_level = pdh.get(day), pdl.get(day)
        clr = clearance_atr * a[t] if np.isfinite(a[t]) else 0.0
        if clr <= 0:
            continue
        prev = closes[t - 1]
        if (h_level is not None and not math.isnan(h_level)
                and prev < h_level - clr and highs[t] >= h_level):
            events.append(Event(t, str(df.index[t]), "pdh_touch", -1,
                                float(h_level)))
        if (l_level is not None and not math.isnan(l_level)
                and prev > l_level + clr and lows[t] <= l_level):
            events.append(Event(t, str(df.index[t]), "pdl_touch", +1,
                                float(l_level)))
    return events


def detect_ntouch_level_events(df: pd.DataFrame, lookback: int = 5,
                               tol_atr: float = 0.5,
                               min_touches: int = 2,
                               max_age: int = 300) -> list[Event]:
    """Horizontal S/R defined by ≥ ``min_touches`` confirmed swing extremes
    within tol of each other; the NEXT clean approach is the event (bounce
    hypothesis against the approach). One event per level."""
    from conflab.indicators import atr as _atr
    from conflab.patterns import swing_points

    n = len(df)
    a = _atr(df).to_numpy()
    c = df["close"].to_numpy()
    h = df["high"].to_numpy()
    lo = df["low"].to_numpy()
    sw = sorted(swing_points(df, lookback), key=lambda s: s.index)
    confirmed = [(s.index + lookback, s) for s in sw if s.index + lookback < n]

    events: list[Event] = []
    levels: list[dict] = []  # {price, is_high, touches, born, state}
    ci = 0
    for t in range(lookback * 2, n):
        tol = tol_atr * a[t] if np.isfinite(a[t]) else 0.0
        while ci < len(confirmed) and confirmed[ci][0] <= t:
            conf_idx, s = confirmed[ci]
            ci += 1
            tol_c = tol_atr * a[conf_idx] if np.isfinite(a[conf_idx]) else 0.0
            if tol_c <= 0:
                continue
            for lv in levels:
                if (lv["is_high"] == s.is_high and lv["state"] == "armed"
                        and abs(lv["price"] - s.price) <= tol_c):
                    lv["touches"] += 1
                    lv["price"] = (lv["price"] + s.price) / 2
                    lv["born"] = conf_idx
                    break
            else:
                levels.append({"price": s.price, "is_high": s.is_high,
                               "touches": 1, "born": conf_idx,
                               "state": "armed"})
        if tol <= 0:
            continue
        prev = c[t - 1]
        for lv in levels:
            if lv["state"] != "armed" or lv["touches"] < min_touches:
                continue
            if t <= lv["born"] or t - lv["born"] > max_age:
                if t - lv["born"] > max_age:
                    lv["state"] = "done"
                continue
            p = lv["price"]
            if lv["is_high"]:
                if prev < p - tol and h[t] >= p:
                    events.append(Event(t, str(df.index[t]),
                                        "ntouch_resistance_touch", -1,
                                        float(p)))
                    lv["state"] = "done"
                elif c[t] > p + tol:
                    lv["state"] = "done"  # broken — no longer the same level
            else:
                if prev > p + tol and lo[t] <= p:
                    events.append(Event(t, str(df.index[t]),
                                        "ntouch_support_touch", +1,
                                        float(p)))
                    lv["state"] = "done"
                elif c[t] < p - tol:
                    lv["state"] = "done"
        levels = [lv for lv in levels if lv["state"] != "done"]
    return events


def detect_pwh_pwl_touches(df: pd.DataFrame,
                           clearance_atr: float = 0.25) -> list[Event]:
    """Previous-week high/low touches (PWH from below → −1, PWL from above
    → +1). Valid for any timeframe with bar spacing < 5 days."""
    if len(df) < 20:
        return []
    spacing = df.index.to_series().diff().median()
    if pd.isna(spacing) or spacing >= pd.Timedelta(days=5):
        return []
    from conflab.indicators import atr as _atr
    a = _atr(df).to_numpy()
    weekly = df.resample("W").agg({"high": "max", "low": "min"}).dropna()
    pwh = weekly["high"].shift(1)
    pwl = weekly["low"].shift(1)
    # Map each bar to its ISO week; the W-resample label (week-end Sunday)
    # shares the ISO week of the days it covers.
    def _week_key(ts) -> tuple:
        iso = ts.isocalendar()
        return (iso.year, iso.week)

    week_keys = df.index.to_series().apply(_week_key)
    pwh_idx = {_week_key(k): v for k, v in pwh.items()}
    pwl_idx = {_week_key(k): v for k, v in pwl.items()}
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    events: list[Event] = []
    keys = week_keys.to_numpy()
    for t in range(1, len(df)):
        h_level = pwh_idx.get(keys[t])
        l_level = pwl_idx.get(keys[t])
        clr = clearance_atr * a[t] if np.isfinite(a[t]) else 0.0
        if clr <= 0:
            continue
        prev = closes[t - 1]
        if (h_level is not None and not math.isnan(h_level)
                and prev < h_level - clr and highs[t] >= h_level):
            events.append(Event(t, str(df.index[t]), "pwh_touch", -1,
                                float(h_level)))
        if (l_level is not None and not math.isnan(l_level)
                and prev > l_level + clr and lows[t] <= l_level):
            events.append(Event(t, str(df.index[t]), "pwl_touch", +1,
                                float(l_level)))
    return events
