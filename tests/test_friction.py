"""Friction-component unit tests for Test B.

Each test uses a hand-built bar series with a known answer, plus a
monotonicity check on the aggregator (more chop → higher score).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conflab.friction import (
    FrictionComponents,
    aggregate,
    assign_quartile,
    components,
    fit_reference,
    oscillation_count,
    path_drawdown_ratio,
    quartile_cutoffs,
    time_in_chop_band,
    wick_density,
)


def _df(opens, highs, lows, closes, freq="4h") -> pd.DataFrame:
    n = len(opens)
    idx = pd.date_range("2024-01-01", periods=n, freq=freq, tz="UTC")
    return pd.DataFrame({
        "open": opens, "high": highs, "low": lows, "close": closes,
        "volume": np.full(n, 100.0)}, index=idx)


# ---------------------------------------------------------------------------
# wick_density
# ---------------------------------------------------------------------------

def test_wick_density_zero_for_marubozu():
    """All bars open=low, close=high (no wicks): density = 0."""
    o = [1.10, 1.101, 1.102, 1.103, 1.104]
    c = [1.101, 1.102, 1.103, 1.104, 1.105]
    h = c
    l = o
    df = _df(o, h, l, c)
    assert wick_density(df, 0, 4) == pytest.approx(0.0)


def test_wick_density_unity_for_pure_doji():
    """Open == close == midpoint, equal upper/lower wicks → ratio = 1.0
    on every bar."""
    bars = [(1.1005, 1.0995, 1.10, 1.10)] * 4  # high, low, open, close
    df = _df([b[2] for b in bars], [b[0] for b in bars],
             [b[1] for b in bars], [b[3] for b in bars])
    assert wick_density(df, 0, 3) == pytest.approx(1.0)


def test_wick_density_handles_zero_range_bar():
    """A bar with high == low (range=0) contributes 0, doesn't divide-by-zero."""
    o = [1.10, 1.101, 1.101]
    c = [1.101, 1.101, 1.102]
    h = [1.1015, 1.101, 1.1025]
    l = [1.0995, 1.101, 1.1005]
    df = _df(o, h, l, c)
    val = wick_density(df, 0, 2)
    assert np.isfinite(val)
    assert val < 1.0


# ---------------------------------------------------------------------------
# oscillation_count
# ---------------------------------------------------------------------------

def test_oscillation_count_monotonic_path():
    """A strictly rising path has zero oscillations."""
    closes = list(np.linspace(1.10, 1.15, 30))
    opens = closes
    highs = [c + 0.0001 for c in closes]
    lows = [c - 0.0001 for c in closes]
    df = _df(opens, highs, lows, closes)
    assert oscillation_count(df, 0, 29) == 0


def test_oscillation_count_zigzag():
    """A clean zig-zag with three turns of >0.5×ATR(20) → exactly 3 swings."""
    base = list(np.linspace(1.10, 1.10, 25))  # warmup so ATR(20) is defined
    legs = []
    p = 1.10
    for delta in (+0.005, -0.006, +0.007, -0.005):
        for _ in range(5):
            p += delta / 5
            legs.append(p)
    closes = base + legs
    opens = closes
    highs = [c + 0.0002 for c in closes]
    lows = [c - 0.0002 for c in closes]
    df = _df(opens, highs, lows, closes)
    swings = oscillation_count(df, 25, len(closes) - 1)
    assert swings == 3


def test_oscillation_count_zero_when_path_too_short():
    closes = [1.10, 1.101]
    df = _df(closes, [c + 0.0001 for c in closes],
             [c - 0.0001 for c in closes], closes)
    assert oscillation_count(df, 0, 1) == 0


# ---------------------------------------------------------------------------
# path_drawdown_ratio
# ---------------------------------------------------------------------------

def test_path_drawdown_ratio_up_full_retrace():
    """Path low equals impulse_bottom → ratio = 1.0."""
    closes = [1.115, 1.110, 1.105, 1.100]
    opens = closes
    highs = [c + 0.0001 for c in closes]
    lows = [1.115, 1.110, 1.105, 1.100]
    df = _df(opens, highs, lows, closes)
    val = path_drawdown_ratio(df, 0, 3, impulse_top=1.115,
                              impulse_bottom=1.100, direction=+1)
    assert val == pytest.approx(1.0)


def test_path_drawdown_ratio_up_partial_retrace():
    closes = [1.115, 1.112, 1.110, 1.108]
    opens = closes
    highs = [c + 0.0001 for c in closes]
    lows = [1.115, 1.112, 1.110, 1.108]
    df = _df(opens, highs, lows, closes)
    val = path_drawdown_ratio(df, 0, 3, impulse_top=1.115,
                              impulse_bottom=1.100, direction=+1)
    assert val == pytest.approx((1.115 - 1.108) / (1.115 - 1.100))


def test_path_drawdown_ratio_down_mirrors():
    closes = [1.100, 1.103, 1.106, 1.109]
    opens = closes
    highs = [1.100, 1.103, 1.106, 1.109]
    lows = [c - 0.0001 for c in closes]
    df = _df(opens, highs, lows, closes)
    val = path_drawdown_ratio(df, 0, 3, impulse_top=1.115,
                              impulse_bottom=1.100, direction=-1)
    assert val == pytest.approx((1.109 - 1.100) / (1.115 - 1.100))


def test_path_drawdown_ratio_zero_height_returns_zero():
    df = _df([1.10] * 3, [1.10] * 3, [1.10] * 3, [1.10] * 3)
    assert path_drawdown_ratio(df, 0, 2, impulse_top=1.10,
                               impulse_bottom=1.10, direction=+1) == 0.0


# ---------------------------------------------------------------------------
# time_in_chop_band
# ---------------------------------------------------------------------------

def test_time_in_chop_band_full_inside():
    closes = list(np.linspace(1.10, 1.10, 60))  # all at midline
    opens = closes
    highs = [c + 0.0002 for c in closes]
    lows = [c - 0.0002 for c in closes]
    df = _df(opens, highs, lows, closes)
    val = time_in_chop_band(df, 30, 59, origin_zone_mid=1.10)
    assert val == pytest.approx(1.0)


def test_time_in_chop_band_partial():
    """Half of the bars are inside the band, half outside."""
    base = list(np.linspace(1.10, 1.10, 50))
    closes = base + [1.10] * 5 + [1.20] * 5  # second 5 are way outside
    opens = closes
    highs = [c + 0.0002 for c in closes]
    lows = [c - 0.0002 for c in closes]
    df = _df(opens, highs, lows, closes)
    val = time_in_chop_band(df, 50, 59, origin_zone_mid=1.10)
    assert val == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# aggregator + reference + quartile cutoffs
# ---------------------------------------------------------------------------

def test_aggregate_z_scores_simple_sum():
    ref = {
        "wick_density": (0.5, 0.1),
        "oscillation_count": (2.0, 1.0),
        "path_drawdown_ratio": (0.8, 0.2),
        "time_in_chop_band": (0.4, 0.1),
    }
    comp = FrictionComponents(0.6, 3, 1.0, 0.5)
    score = aggregate(comp, ref)
    # +1, +1, +1, +1
    assert score == pytest.approx(4.0)


def test_aggregate_skips_degenerate_components():
    """std == 0 means component is degenerate; contributes nothing."""
    ref = {
        "wick_density": (0.5, 0.0),
        "oscillation_count": (2.0, 1.0),
        "path_drawdown_ratio": (0.8, 0.2),
        "time_in_chop_band": (0.4, 0.0),
    }
    comp = FrictionComponents(99.0, 3.0, 1.0, 99.0)
    # Only oscillation_count and path_drawdown_ratio contribute.
    score = aggregate(comp, ref)
    assert score == pytest.approx(1.0 + 1.0)


def test_aggregator_monotonicity_more_chop_higher_score():
    """Increasing every component should monotonically increase the score."""
    ref = {
        "wick_density": (0.5, 0.1),
        "oscillation_count": (2.0, 1.0),
        "path_drawdown_ratio": (0.8, 0.2),
        "time_in_chop_band": (0.4, 0.1),
    }
    low = FrictionComponents(0.4, 1, 0.6, 0.3)
    mid = FrictionComponents(0.5, 2, 0.8, 0.4)
    high = FrictionComponents(0.7, 4, 1.1, 0.6)
    s_low = aggregate(low, ref)
    s_mid = aggregate(mid, ref)
    s_high = aggregate(high, ref)
    assert s_low < s_mid < s_high


def test_fit_reference_records_means_and_stds():
    records = [
        {"wick_density": 0.4, "oscillation_count": 1,
         "path_drawdown_ratio": 0.6, "time_in_chop_band": 0.3},
        {"wick_density": 0.6, "oscillation_count": 3,
         "path_drawdown_ratio": 1.0, "time_in_chop_band": 0.5},
    ]
    ref = fit_reference(records)
    assert ref["wick_density"][0] == pytest.approx(0.5)
    assert ref["oscillation_count"][0] == pytest.approx(2.0)
    assert ref["path_drawdown_ratio"][0] == pytest.approx(0.8)
    assert ref["time_in_chop_band"][0] == pytest.approx(0.4)
    for k in ref:
        assert ref[k][1] >= 0.0


def test_quartile_cutoffs_and_assignment():
    scores = list(range(1, 101))
    cutoffs = quartile_cutoffs(scores)
    q1, q2, q3 = cutoffs
    # 25th, 50th, 75th percentile of 1..100
    assert q1 == pytest.approx(25.75, rel=1e-2)
    assert q2 == pytest.approx(50.5, rel=1e-2)
    assert q3 == pytest.approx(75.25, rel=1e-2)
    assert assign_quartile(0.0, cutoffs) == 1
    assert assign_quartile(q1, cutoffs) == 1
    assert assign_quartile(q1 + 0.01, cutoffs) == 2
    assert assign_quartile(q3 + 0.01, cutoffs) == 4


# ---------------------------------------------------------------------------
# components() integration smoke
# ---------------------------------------------------------------------------

def test_components_returns_all_four():
    base = list(np.linspace(1.10, 1.10, 30))
    closes = base + [1.115, 1.115, 1.110, 1.105, 1.102, 1.100]
    opens = closes
    highs = [c + 0.0002 for c in closes]
    lows = [c - 0.0002 for c in closes]
    df = _df(opens, highs, lows, closes)
    comp = components(df, impulse_end_idx=30, touch_idx=35,
                      impulse_top=1.116, impulse_bottom=1.100,
                      direction=+1, origin_zone_mid=1.100)
    d = comp.as_dict()
    assert set(d) == {"wick_density", "oscillation_count",
                      "path_drawdown_ratio", "time_in_chop_band"}
    for v in d.values():
        assert np.isfinite(v)
