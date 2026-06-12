"""Contracts for the second wave of Stage-0 detector families: zones/OB/
breaker/FVG, trendlines/channels, chart patterns, fib, multi-bar candles,
premium/discount, PWH/PWL and session sweeps."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conflab.data import synthetic_frame
from conflab.detectors_chartpatterns import (
    detect_chart_pattern_events,
    detect_flag_events,
    detect_rectangle_events,
)
from conflab.detectors_fib import detect_fib_events
from conflab.detectors_levels import detect_pwh_pwl_touches
from conflab.detectors_patterns import detect_multibar_candle_events
from conflab.detectors_sessions import detect_session_sweeps
from conflab.detectors_structure import detect_premium_discount_events
from conflab.detectors_trendlines import detect_trendline_events
from conflab.detectors_zones import detect_fvg_events, detect_zone_events
from conflab.events import all_detectors


def _frame(closes, wick: float = 0.0004, freq: str = "4h") -> pd.DataFrame:
    closes_arr = np.asarray(closes, dtype=float)
    opens = np.concatenate([[closes_arr[0]], closes_arr[:-1]])
    idx = pd.date_range("2024-01-01", periods=len(closes_arr), freq=freq,
                        tz="UTC")
    return pd.DataFrame({
        "open": opens,
        "high": np.maximum(opens, closes_arr) + wick,
        "low": np.minimum(opens, closes_arr) - wick,
        "close": closes_arr,
        "volume": np.full(len(closes_arr), 100.0)}, index=idx)


def test_demand_zone_touch_after_impulse():
    # Quiet base, one big up-impulse bar, drift up, then return to the base.
    closes = ([1.10, 1.1005, 1.10, 1.0995, 1.10] * 4      # ATR settles small
              + [1.10, 1.108]                              # impulse bar
              + list(np.linspace(1.108, 1.112, 5))
              + list(np.linspace(1.112, 1.1, 8)))          # return to zone
    events = detect_zone_events(_frame(closes, wick=0.0002))
    types = {e.type for e in events}
    assert "demand_zone_touch" in types
    touch = next(e for e in events if e.type == "demand_zone_touch")
    assert touch.direction == +1


def test_broken_demand_zone_becomes_breaker_resistance():
    closes = ([1.10, 1.1005, 1.10, 1.0995, 1.10] * 4
              + [1.10, 1.108]                              # impulse → zone
              + list(np.linspace(1.108, 1.094, 8))         # close through it
              + list(np.linspace(1.094, 1.101, 8)))        # retest from below
    events = detect_zone_events(_frame(closes, wick=0.0002))
    breakers = [e for e in events if e.type == "breaker_resistance_retest"]
    assert breakers and breakers[0].direction == -1


def test_bullish_fvg_touch():
    # Gap up leaving low[t] > high[t-2], then return into the gap.
    closes = ([1.10, 1.1005, 1.10, 1.0995, 1.10] * 4
              + [1.10, 1.1015, 1.106]                      # creates the gap
              + [1.107, 1.108]
              + list(np.linspace(1.108, 1.1008, 6)))       # back into gap
    events = detect_fvg_events(_frame(closes, wick=0.0001))
    types = {e.type for e in events}
    assert "bullish_fvg_touch" in types


def test_trendline_support_touch_on_rising_lows():
    # Rising swing lows with pullbacks: a support line forms; later pullback
    # to the line should fire a touch.
    seg = []
    base = 1.10
    for k in range(5):
        seg += list(np.linspace(base, base + 0.006, 6))
        seg += list(np.linspace(base + 0.006, base + 0.002, 5))[1:]
        base += 0.002
    events = detect_trendline_events(_frame(seg, wick=0.0002), lookback=3)
    types = {e.type for e in events}
    assert "trendline_support_touch" in types
    touch = next(e for e in events if e.type == "trendline_support_touch")
    assert touch.direction == +1


def test_rectangle_breakout_up():
    closes = [1.10 + 0.0004 * ((-1) ** k) for k in range(40)]
    closes += list(np.linspace(1.1004, 1.106, 6))
    events = detect_rectangle_events(_frame(closes, wick=0.0001))
    assert any(e.type == "rectangle_breakout_up" and e.direction == +1
               for e in events)


def test_triangle_or_pattern_events_well_formed():
    df = synthetic_frame(1200, seed=21)
    events = detect_chart_pattern_events(df)
    for e in events:
        assert e.direction in (-1, +1)
        assert 0 <= e.index < len(df)


def test_bull_flag_breakout():
    closes = ([1.10, 1.1004, 1.10, 1.0996, 1.10] * 4          # quiet ATR
              + list(np.linspace(1.10, 1.112, 6))             # impulse
              + [1.1115, 1.1112, 1.1110, 1.1112, 1.1110]      # tight drift
              + [1.1135])                                     # breakout
    events = detect_flag_events(_frame(closes, wick=0.0001))
    assert any(e.type == "bull_flag_breakout" and e.direction == +1
               for e in events)


def test_fib_retrace_tag_on_pullback():
    closes = ([1.10, 1.1003, 1.10, 1.0997, 1.10] * 4
              + list(np.linspace(1.10, 1.094, 8))             # swing low leg
              + list(np.linspace(1.094, 1.112, 14))           # impulse up
              + [1.1118, 1.1110, 1.1105, 1.1118, 1.1125, 1.1118, 1.1110]
              + list(np.linspace(1.111, 1.1015, 14)))         # deep pullback
    events = detect_fib_events(_frame(closes, wick=0.0002), lookback=3,
                               min_leg_atr=2.0)
    types = {e.type for e in events}
    assert types & {"fib_382_tag", "fib_50_tag", "fib_618_tag", "fib_786_tag",
                    "ote_tag"}, f"no retrace tag fired: {types}"


def test_morning_star():
    closes = ([1.10, 1.1004, 1.10, 1.0996, 1.10] * 4
              + [1.10, 1.094, 1.0938, 1.0995])  # thrust dn, pause, reversal
    events = detect_multibar_candle_events(_frame(closes, wick=0.0001))
    assert any(e.type == "morning_star" and e.direction == +1
               for e in events)


def test_premium_discount_cross_events():
    n = 130
    closes = list(np.linspace(1.10, 1.12, n))   # establishes range
    closes += list(np.linspace(1.12, 1.1, 30))  # crosses below equilibrium
    events = detect_premium_discount_events(_frame(closes), window=100)
    assert any(e.type == "entered_discount" and e.direction == +1
               for e in events)


def test_pwh_touch_intraday():
    # Week 1 sets a high; week 2 rallies into it from below.
    week1 = list(np.linspace(1.10, 1.11, 21)) + list(
        np.linspace(1.11, 1.103, 21))
    week2 = list(np.linspace(1.103, 1.1102, 42))
    df = _frame(week1 + week2, wick=0.0002, freq="4h")
    events = detect_pwh_pwl_touches(df)
    assert any(e.type == "pwh_touch" and e.direction == -1 for e in events)


def test_session_sweep_h1_only():
    # H4 frame: detector must decline.
    assert detect_session_sweeps(synthetic_frame(300, seed=5)) == []
    # Build 3 days of H1 with an Asia range and a London wick through it.
    idx = pd.date_range("2024-01-02", periods=72, freq="1h", tz="UTC")
    closes = np.full(72, 1.10)
    df = pd.DataFrame({"open": closes, "high": closes + 0.0005,
                       "low": closes - 0.0005, "close": closes,
                       "volume": np.full(72, 100.0)}, index=idx)
    # Day 2: Asia high 1.1010; 09:00 wick above it, close back below.
    day2 = (idx.date == idx[30].date())
    asia_mask = day2 & (idx.hour < 7)
    df.loc[asia_mask, "high"] = 1.1010
    nine = day2 & (idx.hour == 9)
    df.loc[nine, "high"] = 1.1020
    df.loc[nine, "close"] = 1.0998
    events = detect_session_sweeps(df)
    assert any(e.type == "asia_high_sweep" and e.direction == -1
               for e in events)


def test_ntouch_support_touch():
    from conflab.detectors_levels import detect_ntouch_level_events

    # Two confirmed swing lows at ~1.094, then a third clean approach.
    def vee(depth, width=5):
        down = list(np.linspace(1.10, 1.10 - depth, width))
        return down + list(np.linspace(1.10 - depth, 1.10, width))[1:]

    closes = ([1.10, 1.1005, 1.10, 1.0995] * 3
              + vee(0.006) + [1.10, 1.1010, 1.1005] + vee(0.0061)
              + [1.10, 1.1010, 1.1015, 1.1010]
              + list(np.linspace(1.1010, 1.0939, 8)))
    events = detect_ntouch_level_events(_frame(closes, wick=0.0002),
                                        lookback=3)
    assert any(e.type == "ntouch_support_touch" and e.direction == +1
               for e in events)


def test_full_registry_runs_clean_on_synthetic():
    detectors = all_detectors()
    assert len(detectors) >= 17
    df = synthetic_frame(800, seed=33)
    for name, det in detectors.items():
        for e in det(df):
            assert 0 <= e.index < len(df), f"{name}: out-of-range index"
            assert e.direction in (-1, +1), f"{name}: bad direction"
