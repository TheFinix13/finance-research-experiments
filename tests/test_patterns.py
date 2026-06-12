"""Pattern detection on hand-crafted series."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conflab.patterns import (
    candle_events,
    detect_double_bottoms,
    detect_double_tops,
    detect_sr_flips,
    swing_points,
)


def _frame(closes: list[float], wick: float = 0.0005) -> pd.DataFrame:
    closes_arr = np.asarray(closes, dtype=float)
    opens = np.concatenate([[closes_arr[0]], closes_arr[:-1]])
    highs = np.maximum(opens, closes_arr) + wick
    lows = np.minimum(opens, closes_arr) - wick
    idx = pd.date_range("2024-01-01", periods=len(closes_arr), freq="4h",
                        tz="UTC")
    return pd.DataFrame({"open": opens, "high": highs, "low": lows,
                         "close": closes_arr,
                         "volume": np.full(len(closes_arr), 100.0)}, index=idx)


def _vee(base: float, depth: float, width: int) -> list[float]:
    down = list(np.linspace(base, base - depth, width))
    up = list(np.linspace(base - depth, base, width))
    return down + up[1:]


def test_double_bottom_detected():
    # Two equal lows separated by a clear neckline peak.
    closes = ([1.10] * 10 + _vee(1.10, 0.01, 8) + [1.10] * 6
              + _vee(1.10, 0.0102, 8) + [1.10] * 10)
    df = _frame(closes)
    hits = detect_double_bottoms(df)
    assert hits, "constructed double bottom not detected"
    hit = hits[0]
    assert hit.kind == "double_bottom"
    assert hit.level == pytest.approx(1.10 - 0.0102, abs=0.002)
    assert hit.neckline is not None and hit.neckline > hit.level


def test_double_top_detected():
    closes = ([1.10] * 10 + [c + 2 * (1.10 - c) for c in _vee(1.10, 0.01, 8)]
              + [1.10] * 6
              + [c + 2 * (1.10 - c) for c in _vee(1.10, 0.0101, 8)]
              + [1.10] * 10)
    df = _frame(closes)
    hits = detect_double_tops(df)
    assert hits and hits[0].kind == "double_top"
    assert hits[0].neckline is not None and hits[0].neckline < hits[0].level


def test_sr_flip_support_becomes_resistance():
    # Hold above 1.10 (support), break hard below, rally back to retest
    # 1.10 from underneath, get rejected.
    closes = ([1.105, 1.102, 1.1005, 1.103, 1.1003, 1.104, 1.1002, 1.105]
              + list(np.linspace(1.104, 1.085, 12))     # the break
              + [1.086, 1.088, 1.092, 1.096, 1.0992, 1.0975, 1.094, 1.090])
    df = _frame(closes, wick=0.0012)
    hits = detect_sr_flips(df, lookback=3)
    kinds = {h.kind for h in hits}
    assert "sr_flip_resistance" in kinds


def test_swing_points_alternating_extremes():
    closes = [1.10, 1.12, 1.10, 1.08, 1.10, 1.12, 1.10, 1.08, 1.10]
    df = _frame([c for c in closes for _ in range(3)])
    pts = swing_points(df, lookback=3)
    assert any(p.is_high for p in pts)
    assert any(not p.is_high for p in pts)


def test_candle_events_doji_and_engulfing():
    idx = pd.date_range("2024-01-01", periods=3, freq="4h", tz="UTC")
    df = pd.DataFrame({
        "open":  [1.1000, 1.1010, 1.0995],
        "high":  [1.1030, 1.1015, 1.1030],
        "low":   [1.0970, 1.0990, 1.0990],
        "close": [1.1001, 1.0995, 1.1020],
        "volume": [100.0, 100.0, 100.0],
    }, index=idx)
    ev = candle_events(df)
    assert bool(ev["doji"].iloc[0])            # tiny body, big range
    assert bool(ev["bull_engulfing"].iloc[2])  # body engulfs prior red body
    assert not bool(ev["bear_engulfing"].iloc[2])
