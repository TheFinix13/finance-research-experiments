"""Test B detector contracts (impulse-origin return events).

Synthetic OHLC fixtures with known answers. The hardest constraint is the
30%-retrace ceiling: every bar in the leg must have intrabar drawdown
from the running max ≤ 30% of leg height. The helpers in this module
chain bars at 20% range each + 20% gap each, so 3 bars × 20% range +
2 gaps × 20% = 100% of the leg covered with comfortable margin under
the 30%-per-bar ceiling.

Warmup bars use a TWO-SIDED tiny range so neither up- nor down-direction
detector accidentally anchors a "leg_top = warmup high" or
"leg_bottom = warmup low" that exceeds the M_pips floor at unintended
indices. To make it possible at all, warmup bars sit at the same price
as the impulse start (so the warmup-side wick contributes far less than
40 pips), and we use a tiny range so ATR is positive but bar-resolution
noise stays << M_pips.

Tests cover:
- clean up-impulse + valid return → exactly 1 up event
- clean down-impulse + valid return → exactly 1 down event
- impulse below the M_pips floor → rejected
- impulse with intrabar retrace > 30% → rejected
- late return outside the N-bar validity window → rejected
- first-touch-only (a later re-touch from the same impulse does not double-emit)
- inter-event K-bar spacing (overlapping rolling impulses do not double-emit)
- direction must be ±1
- detect_both_directions returns up + down on a mixed frame
- tiny frame returns no events (length guard)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conflab.detectors_impulse_return import (
    ImpulseReturnConfig,
    detect_both_directions,
    detect_impulse_origin_return_events,
)


# Tiny per-bar wick used in warmup so ATR > 0 yet leg pip thresholds
# can never be tripped purely by the warmup wick.
WICK_TICK = 1e-5  # 0.1 pip


# ---------------------------------------------------------------------------
# Bar-frame helpers
# ---------------------------------------------------------------------------


def _frame(rows: list[tuple[float, float, float, float]],
           freq: str = "4h") -> pd.DataFrame:
    n = len(rows)
    idx = pd.date_range("2024-01-01", periods=n, freq=freq, tz="UTC")
    arr = np.asarray(rows, dtype=float)
    return pd.DataFrame({
        "open": arr[:, 0], "high": arr[:, 1],
        "low": arr[:, 2], "close": arr[:, 3],
        "volume": np.full(n, 100.0)}, index=idx)


def _flat_bar_two_sided(price: float = 1.1000, half: float = WICK_TICK / 2):
    """Doji bar with tiny upper AND lower wicks; OK for warmup before tests
    that don't need to control which side of `price` a leg can anchor on."""
    return (price, price + half, price - half, price)


def _flat_bar_below_only(price: float = 1.1000, wick: float = WICK_TICK):
    """Doji bar with NO upper wick — high = price, low = price - wick.

    Used as warmup ahead of UP impulses: prevents a false leg top (which
    would push leg_top above the impulse-start price and dilute pip checks).
    """
    return (price, price, price - wick, price)


def _flat_bar_above_only(price: float = 1.1000, wick: float = WICK_TICK):
    """Doji bar with NO lower wick — high = price + wick, low = price.

    Used as warmup ahead of DOWN impulses.
    """
    return (price, price + wick, price, price)


def _up_impulse_3bars(start: float, top: float):
    """3 chained up-bars: each bar's range = 20% of leg height, gaps = 20%
    each → 3×20% + 2×20% = 100% of leg covered. Every bar's intrabar dd from
    the running max is 20% of leg, comfortably under the 30% ceiling.
    """
    h = top - start
    bar_range = 0.20 * h
    gap = 0.20 * h
    p0_low = start
    p0_high = start + bar_range
    p1_low = p0_high + gap
    p1_high = p1_low + bar_range
    p2_low = p1_high + gap
    p2_high = p2_low + bar_range
    eps = 1e-7
    return [
        (p0_low, p0_high, p0_low, p0_high - eps),
        (p1_low, p1_high, p1_low, p1_high - eps),
        (p2_low, p2_high, p2_low, p2_high - eps),
    ]


def _down_impulse_3bars(start: float, bottom: float):
    h = start - bottom
    bar_range = 0.20 * h
    gap = 0.20 * h
    p0_high = start
    p0_low = start - bar_range
    p1_high = p0_low - gap
    p1_low = p1_high - bar_range
    p2_high = p1_low - gap
    p2_low = p2_high - bar_range
    eps = 1e-7
    return [
        (p0_high, p0_high, p0_low, p0_low + eps),
        (p1_high, p1_high, p1_low, p1_low + eps),
        (p2_high, p2_high, p2_low, p2_low + eps),
    ]


# ---------------------------------------------------------------------------
# Clean up-impulse + return → 1 event
# ---------------------------------------------------------------------------


def test_up_impulse_with_valid_return_emits_one_event():
    rows = [_flat_bar_below_only(1.1000) for _ in range(25)]   # bars 0..24
    rows += _up_impulse_3bars(1.1000, 1.1050)                  # bars 25..27
    rows += [
        (1.1050, 1.1052, 1.1045, 1.1048),
        (1.1048, 1.1050, 1.1042, 1.1044),
        (1.1044, 1.1046, 1.1035, 1.1038),
        (1.1038, 1.1040, 1.1025, 1.1028),
        (1.1028, 1.1030, 1.1015, 1.1018),
        (1.1018, 1.1020, 1.1005, 1.1008),    # touch (low ≤ origin zone top)
    ]
    rows += [_flat_bar_below_only(1.1000) for _ in range(20)]
    df = _frame(rows)

    events = detect_impulse_origin_return_events(
        df, direction=+1,
        cfg=ImpulseReturnConfig(M_atr=1.0, M_pips=40.0, K=3, N=40))
    assert len(events) == 1
    e = events[0]
    assert e["event_type"] == "impulse_origin_return_up"
    assert e["direction"] == +1
    assert e["impulse_height_pips"] >= 40.0
    assert e["origin_zone_top"] >= e["origin_zone_bottom"]
    assert e["touch_bar_idx"] > e["impulse_end_idx"]
    assert e["validity_window_bars"] >= 1
    fc = e["friction_components"]
    assert set(fc) == {"wick_density", "oscillation_count",
                       "path_drawdown_ratio", "time_in_chop_band"}
    for v in fc.values():
        assert np.isfinite(v)


# ---------------------------------------------------------------------------
# Clean down-impulse + return → 1 event
# ---------------------------------------------------------------------------


def test_down_impulse_with_valid_return_emits_one_event():
    rows = [_flat_bar_above_only(1.1000) for _ in range(25)]    # bars 0..24
    rows += _down_impulse_3bars(1.1000, 1.0950)                 # bars 25..27
    rows += [
        (1.0950, 1.0955, 1.0948, 1.0953),
        (1.0953, 1.0962, 1.0951, 1.0960),
        (1.0960, 1.0975, 1.0958, 1.0972),
        (1.0972, 1.0985, 1.0970, 1.0982),
        (1.0982, 1.0995, 1.0980, 1.0993),    # touch (high ≥ origin zone bot)
    ]
    rows += [_flat_bar_above_only(1.1000) for _ in range(20)]
    df = _frame(rows)

    events = detect_impulse_origin_return_events(
        df, direction=-1,
        cfg=ImpulseReturnConfig(M_atr=1.0, M_pips=40.0, K=3, N=40))
    assert len(events) == 1
    e = events[0]
    assert e["event_type"] == "impulse_origin_return_down"
    assert e["direction"] == -1
    assert e["impulse_height_pips"] >= 40.0


# ---------------------------------------------------------------------------
# Below the M_pips floor → no events
# ---------------------------------------------------------------------------


def test_impulse_below_pip_threshold_is_rejected():
    rows = [_flat_bar_below_only(1.1000) for _ in range(25)]
    rows += _up_impulse_3bars(1.1000, 1.1020)        # 20-pip leg
    rows += [(1.1020, 1.1022, 1.1005, 1.1010)]
    rows += [_flat_bar_below_only(1.1000) for _ in range(20)]
    df = _frame(rows)

    events = detect_impulse_origin_return_events(
        df, direction=+1,
        cfg=ImpulseReturnConfig(M_atr=0.1, M_pips=40.0, K=3, N=40))
    assert events == []


# ---------------------------------------------------------------------------
# Intrabar retrace > 30% during the leg → rejected
# ---------------------------------------------------------------------------


def test_impulse_with_oversized_retrace_is_rejected():
    """A 50-pip nominal leg whose middle bar plunges 40 pips intrabar from
    the running max — 80% drawdown, well over the 30% ceiling."""
    rows = [_flat_bar_below_only(1.1000) for _ in range(25)]
    rows += [
        (1.1000, 1.1010, 1.1000, 1.1010),
        (1.1010, 1.1025, 1.0985, 1.1025),    # offending: dd 40/50 = 80%
        (1.1025, 1.1050, 1.1025, 1.1050),
    ]
    rows += [(1.1050, 1.1052, 1.1005, 1.1010)]
    rows += [_flat_bar_below_only(1.1000) for _ in range(20)]
    df = _frame(rows)

    events = detect_impulse_origin_return_events(
        df, direction=+1,
        cfg=ImpulseReturnConfig(M_atr=0.1, M_pips=40.0, K=3, N=40))
    assert events == []


# ---------------------------------------------------------------------------
# Late return outside validity window → rejected
# ---------------------------------------------------------------------------


def test_late_return_outside_validity_is_rejected():
    rows = [_flat_bar_below_only(1.1000) for _ in range(25)]
    rows += _up_impulse_3bars(1.1000, 1.1050)
    # 30 flat bars at 1.1050 — never touches origin zone within N=10
    rows += [(1.1050, 1.1050, 1.1050 - WICK_TICK, 1.1050)
             for _ in range(30)]
    # eventual late return well outside the validity window
    rows += [(1.1050, 1.1052, 1.1005, 1.1010)]
    rows += [_flat_bar_below_only(1.1000) for _ in range(60)]
    df = _frame(rows)

    events = detect_impulse_origin_return_events(
        df, direction=+1,
        cfg=ImpulseReturnConfig(M_atr=0.1, M_pips=40.0, K=3, N=10))
    assert events == []


# ---------------------------------------------------------------------------
# First-touch-only: subsequent re-touches do not double-emit
# ---------------------------------------------------------------------------


def test_first_touch_only_no_double_emission():
    rows = [_flat_bar_below_only(1.1000) for _ in range(25)]
    rows += _up_impulse_3bars(1.1000, 1.1050)
    rows += [
        (1.1050, 1.1052, 1.1045, 1.1048),
        (1.1048, 1.1050, 1.1008, 1.1015),    # first touch (low ≤ zone top)
        (1.1015, 1.1030, 1.1015, 1.1028),
        (1.1028, 1.1035, 1.1025, 1.1032),
        (1.1032, 1.1035, 1.1008, 1.1015),    # second touch — must NOT fire
    ]
    rows += [_flat_bar_below_only(1.1000) for _ in range(40)]
    df = _frame(rows)

    events = detect_impulse_origin_return_events(
        df, direction=+1,
        cfg=ImpulseReturnConfig(M_atr=0.1, M_pips=40.0, K=3, N=40))
    assert len(events) == 1


# ---------------------------------------------------------------------------
# Inter-event K-bar spacing
# ---------------------------------------------------------------------------


def test_inter_event_spacing_blocks_overlapping_legs():
    """Bar 28 and bar 29 are both VALID impulse-end candidates (their K-bar
    windows pass pip + 30% checks). With K=3 spacing, only one event fires
    (the earliest)."""
    rows = [_flat_bar_below_only(1.1000) for _ in range(25)]
    rows += _up_impulse_3bars(1.1000, 1.1050)              # bars 25..27
    rows += [(1.1057, 1.1062, 1.1057, 1.1061)]             # bar 28
    rows += [(1.1075, 1.1080, 1.1075, 1.1079)]             # bar 29
    rows += [_flat_bar_below_only(1.1000) for _ in range(40)]
    df = _frame(rows)

    events = detect_impulse_origin_return_events(
        df, direction=+1,
        cfg=ImpulseReturnConfig(M_atr=0.1, M_pips=40.0, K=3, N=40))
    assert len(events) == 1
    # First-fired impulse-end is at bar 27 (spacing then blocks 28 and 29).
    assert events[0]["impulse_end_idx"] == 27


# ---------------------------------------------------------------------------
# Direction validation
# ---------------------------------------------------------------------------


def test_direction_must_be_pm_one():
    df = _frame([_flat_bar_two_sided() for _ in range(60)])
    with pytest.raises(ValueError):
        detect_impulse_origin_return_events(df, direction=0)


# ---------------------------------------------------------------------------
# detect_both_directions returns up + down
# ---------------------------------------------------------------------------


def test_detect_both_directions_smoke():
    rows = [_flat_bar_two_sided(1.1000) for _ in range(25)]
    rows += _up_impulse_3bars(1.1000, 1.1050)
    rows += [(1.1050, 1.1052, 1.1005, 1.1010)]            # up touch
    rows += [_flat_bar_two_sided(1.1000) for _ in range(10)]
    rows += _down_impulse_3bars(1.1000, 1.0950)
    rows += [(1.0950, 1.0995, 1.0950, 1.0993)]            # down touch
    rows += [_flat_bar_two_sided(1.1000) for _ in range(20)]
    df = _frame(rows)

    events = detect_both_directions(
        df, cfg=ImpulseReturnConfig(M_atr=0.1, M_pips=40.0, K=3, N=40),
        timeframe="H4")
    types = {e["event_type"] for e in events}
    assert "impulse_origin_return_up" in types
    assert "impulse_origin_return_down" in types
    assert all(e["tf"] == "H4" for e in events)


# ---------------------------------------------------------------------------
# Tiny frame → no events (no crash on length-guard)
# ---------------------------------------------------------------------------


def test_tiny_frame_returns_no_events():
    df = _frame([_flat_bar_two_sided() for _ in range(8)])
    assert detect_impulse_origin_return_events(df, direction=+1) == []
    assert detect_impulse_origin_return_events(df, direction=-1) == []
