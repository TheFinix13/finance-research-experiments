"""Stage-0 detector + Stage-1 screening contracts."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conflab.data import synthetic_frame
from conflab.detectors_levels import (
    detect_pdh_pdl_touches,
    detect_round_number_touches,
)
from conflab.detectors_liquidity import detect_liquidity_events
from conflab.detectors_patterns import (
    detect_candle_pattern_events,
    detect_double_pattern_completions,
)
from conflab.detectors_structure import detect_bos_choch
from conflab.events import all_detectors
from conflab.indicators import atr
from conflab.screening import (
    Stage1Config,
    directional_outcome,
    format_registry,
    run_stage1,
)


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


# ----------------------------------------------------------------------
# Stage-0 detectors
# ----------------------------------------------------------------------

def test_bos_detected_on_breakout():
    # Range with a clear swing high, then a decisive close above it.
    closes = ([1.10, 1.103, 1.106, 1.103, 1.10, 1.097, 1.10, 1.103] * 3
              + list(np.linspace(1.103, 1.115, 8)))
    events = detect_bos_choch(_frame(closes), lookback=3)
    bullish = [e for e in events if e.type in ("bos_bullish", "choch_bullish")]
    assert bullish, "breakout above swing high produced no BOS event"
    assert all(e.direction == +1 for e in bullish)


def test_choch_fires_against_prevailing_structure():
    # Downtrend (bearish BOS events) then a reversal breaking a swing high.
    down = list(np.linspace(1.12, 1.10, 20))
    wiggle = [1.10, 1.103, 1.10, 1.097, 1.10, 1.103, 1.10]
    up = list(np.linspace(1.10, 1.115, 10))
    events = detect_bos_choch(_frame(down + wiggle * 2 + up), lookback=3)
    types = [e.type for e in events]
    assert "choch_bullish" in types


def test_equal_lows_pool_and_sweep():
    # Two equal lows form a pool; later a wick below with close back above.
    base = [1.10, 1.097, 1.094, 1.097, 1.10, 1.103, 1.10, 1.097, 1.0941,
            1.097, 1.10, 1.103, 1.106, 1.108, 1.106, 1.104]
    df = _frame(base + [1.10, 1.096, 1.098, 1.102, 1.105, 1.108])
    # Manually push one wick through the pool with a recovering close.
    df.iloc[18, df.columns.get_loc("low")] = 1.0930
    df.iloc[18, df.columns.get_loc("close")] = 1.0980
    events = detect_liquidity_events(df, lookback=2)
    types = {e.type for e in events}
    assert "equal_lows_pool" in types
    pool = next(e for e in events if e.type == "equal_lows_pool")
    assert pool.direction == -1  # magnet below
    if "liquidity_sweep_low" in types:
        sweep = next(e for e in events if e.type == "liquidity_sweep_low")
        assert sweep.direction == +1


def test_round_number_touch_direction():
    closes = [1.1080, 1.1075, 1.1070, 1.1052, 1.1048, 1.1060, 1.1070]
    events = detect_round_number_touches(_frame(closes, wick=0.0003))
    assert events, "approach into 1.1050 not detected"
    assert events[0].level == pytest.approx(1.1050)
    assert events[0].direction == +1  # approached from above -> support test


def test_pdh_pdl_skipped_on_daily():
    df = synthetic_frame(120, seed=2, tf_hours=24)
    assert detect_pdh_pdl_touches(df) == []


def test_pdh_touch_on_intraday():
    # Day 1 sets a high; day 2 rallies into it from below.
    day1 = list(np.linspace(1.10, 1.108, 6))   # high ~1.108
    day1 += list(np.linspace(1.108, 1.102, 6))
    day2 = list(np.linspace(1.102, 1.1083, 12))
    df = _frame(day1 + day2, wick=0.0002, freq="2h")
    events = detect_pdh_pdl_touches(df)
    assert any(e.type == "pdh_touch" and e.direction == -1 for e in events)


def test_double_bottom_completion_event():
    def vee(base, depth, width):
        down = list(np.linspace(base, base - depth, width))
        return down + list(np.linspace(base - depth, base, width))[1:]

    closes = ([1.10] * 10 + vee(1.10, 0.01, 8) + [1.10] * 6
              + vee(1.10, 0.0102, 8) + list(np.linspace(1.10, 1.108, 6)))
    events = detect_double_pattern_completions(_frame(closes))
    assert any(e.type == "double_bottom_completion" and e.direction == +1
               for e in events)


def test_candle_events_have_directions():
    df = synthetic_frame(300, seed=4)
    events = detect_candle_pattern_events(df)
    assert events
    assert all(e.direction in (-1, +1) for e in events)
    assert all(0 <= e.index < len(df) for e in events)


def test_registry_loads_all_detectors():
    detectors = all_detectors()
    assert len(detectors) >= 7
    df = synthetic_frame(400, seed=8)
    for name, det in detectors.items():
        events = det(df)  # must not raise
        for e in events:
            assert e.index < len(df), f"{name} emitted out-of-range index"


# ----------------------------------------------------------------------
# Stage-1 screening
# ----------------------------------------------------------------------

def test_directional_outcome_bounce():
    closes = list(np.linspace(1.10, 1.095, 10)) + list(
        np.linspace(1.095, 1.105, 10))
    df = _frame(closes)
    highs, lows, cl = (df[k].to_numpy() for k in ("high", "low", "close"))
    a = atr(df).to_numpy()
    out = directional_outcome(highs, lows, cl, a, 9, +1, horizon=10)
    assert out is not None
    mfe, hit = out
    assert mfe > 1.0
    assert hit is True


def test_directional_outcome_adverse_first_is_conservative():
    # Price collapses immediately after the event bar: hit must be False.
    closes = [1.10] * 5 + list(np.linspace(1.10, 1.085, 10))
    df = _frame(closes)
    highs, lows, cl = (df[k].to_numpy() for k in ("high", "low", "close"))
    a = atr(df).to_numpy()
    out = directional_outcome(highs, lows, cl, a, 4, +1, horizon=10)
    assert out is not None and out[1] is False


def test_stage1_smoke_verdicts_and_determinism():
    frames = {"H4": synthetic_frame(900, seed=13),
              "D1": synthetic_frame(250, seed=14, tf_hours=24)}
    cfg = Stage1Config(min_n=30, n_perm=200, seed=3)
    rows = run_stage1(frames, cfg)
    assert rows, "no registry rows produced"
    allowed = {"alive", "parked_weak_effect", "parked_insufficient_n", "dead"}
    assert {r["verdict"] for r in rows} <= allowed
    for r in rows:
        assert 0.0 < r["p_value"] <= 1.0
        assert r["n"] > 0
    # Determinism for a fixed seed.
    rows2 = run_stage1(frames, Stage1Config(min_n=30, n_perm=200, seed=3))
    assert rows == rows2
    text = format_registry(rows)
    assert "Stage-1 verdict registry" in text


def test_stage1_screen_end_respected():
    df = synthetic_frame(900, seed=13)
    cutoff = str(df.index[500].date())
    rows_full = run_stage1({"H4": df}, Stage1Config(min_n=30, n_perm=100))
    rows_cut = run_stage1({"H4": df}, Stage1Config(min_n=30, n_perm=100),
                          screen_end=cutoff)
    n_full = sum(r["n"] for r in rows_full)
    n_cut = sum(r["n"] for r in rows_cut)
    assert n_cut < n_full
