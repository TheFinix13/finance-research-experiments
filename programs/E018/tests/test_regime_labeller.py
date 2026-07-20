"""Unit tests for the E018 frozen causal regime labeller.

Run:
    PYTHONPATH=../multi-pair-trading-agent:.:programs/E018 \
        ../multi-pair-trading-agent/.venv/bin/python -m pytest \
        programs/E018/tests/test_regime_labeller.py -q
"""
from __future__ import annotations

import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_LAB_ROOT = Path(__file__).resolve().parents[3]
_AGENT_ROOT = _LAB_ROOT.parent / "multi-pair-trading-agent"
for _p in (str(_AGENT_ROOT), str(_LAB_ROOT / "programs" / "E018")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest

from agent.alphas.concepts._htf import HTFBias
from agent.types import Bar, Direction, Timeframe

from regime_labeller import (
    Regime,
    breakout_at,
    regime_at,
    wilder_atr,
)

_T0 = datetime(2020, 1, 1, tzinfo=timezone.utc)


def _mkbars(closes: list[float], ranges: list[float]) -> list[Bar]:
    """Build an H4 bar series from close prices and per-bar high-low ranges."""
    bars = []
    prev = closes[0]
    for k, (c, rng) in enumerate(zip(closes, ranges)):
        hi = max(c, prev) + rng / 2
        lo = min(c, prev) - rng / 2
        bars.append(Bar(
            time=_T0 + timedelta(hours=4 * k),
            open=prev, high=hi, low=lo, close=c, volume=100.0,
            timeframe=Timeframe.H4,
        ))
        prev = c
    return bars


def _uptrend(n: int, *, drift: float, base_range: float,
             jump_at: int | None = None, jump: float = 0.0,
             jump_range: float = 0.0) -> list[Bar]:
    closes, ranges = [], []
    c = 1.1000
    for k in range(n):
        c = 1.1000 + drift * k
        rng = base_range
        if jump_at is not None and k == jump_at:
            c = c + jump
            rng = jump_range
        elif jump_at is not None and jump_at - 4 <= k < jump_at:
            rng = jump_range  # expand vol just before the breakout bar
        closes.append(c)
        ranges.append(rng)
    return _mkbars(closes, ranges)


# ---------------------------------------------------------------------------
# Wilder ATR
# ---------------------------------------------------------------------------

def test_wilder_atr_constant_range():
    # Constant true range => ATR converges to that range.
    closes = [1.1000] * 40
    ranges = [0.0010] * 40
    bars = _mkbars(closes, ranges)
    atr = wilder_atr(bars, period=14)
    assert math.isnan(atr[13])
    assert atr[14] == pytest.approx(0.0010, abs=1e-9)
    assert atr[39] == pytest.approx(0.0010, abs=1e-9)


def test_wilder_atr_warmup_nan():
    bars = _mkbars([1.1] * 10, [0.001] * 10)
    atr = wilder_atr(bars, period=14)
    assert all(math.isnan(x) for x in atr)


# ---------------------------------------------------------------------------
# Breakout predicate
# ---------------------------------------------------------------------------

def test_breakout_none_in_quiet_drift():
    bars = _uptrend(130, drift=0.0002, base_range=0.0004)
    atr = wilder_atr(bars)
    # Gentle drift: no bar closes beyond the prior 20-bar high by 0.5*ATR.
    assert breakout_at(bars, 125, atr) is None


def test_breakout_up_detected_on_vol_expansion():
    bars = _uptrend(130, drift=0.0002, base_range=0.0004,
                    jump_at=125, jump=0.0060, jump_range=0.0015)
    atr = wilder_atr(bars)
    bo = breakout_at(bars, 125, atr)
    assert bo is not None
    assert bo.direction == Direction.LONG
    assert bo.mag_atr_ratio > 0
    assert bo.atr_expansion_ratio > 1.0


def test_breakout_warmup_returns_none():
    bars = _uptrend(130, drift=0.0002, base_range=0.0004)
    atr = wilder_atr(bars)
    assert breakout_at(bars, 50, atr) is None  # < WARMUP_BARS (105)


# ---------------------------------------------------------------------------
# Regime decision
# ---------------------------------------------------------------------------

def test_r3_neutral_bias_flat_market():
    bars = _mkbars([1.1000] * 130, [0.0004] * 130)
    res = regime_at(bars, 125)
    assert res.bias is HTFBias.NEUTRAL
    assert res.regime is Regime.R3_NO_BIAS


def test_r2_up_bias_with_aligned_up_breakout():
    bars = _uptrend(130, drift=0.0002, base_range=0.0004,
                    jump_at=125, jump=0.0060, jump_range=0.0015)
    res = regime_at(bars, 125)
    assert res.bias is HTFBias.UP
    assert res.regime is Regime.R2_TREND_EXTENSION
    assert res.breakout_aligned is True
    assert res.breakout_dir is Direction.LONG


def test_r1_up_bias_no_breakout_is_pullback():
    bars = _uptrend(130, drift=0.0002, base_range=0.0004)
    res = regime_at(bars, 125)
    assert res.bias is HTFBias.UP
    assert res.regime is Regime.R1_TREND_PULLBACK
    assert res.breakout_aligned is False


def test_causality_future_bars_do_not_change_label():
    bars = _uptrend(130, drift=0.0002, base_range=0.0004,
                    jump_at=125, jump=0.0060, jump_range=0.0015)
    res_before = regime_at(bars, 120)
    # Mutate everything AFTER bar 120 to nonsense; label at 120 must not move.
    for k in range(121, len(bars)):
        bars[k].close += 0.05
        bars[k].high += 0.05
        bars[k].low += 0.05
    res_after = regime_at(bars, 120)
    assert res_before.regime == res_after.regime
    assert res_before.bias == res_after.bias


def test_down_breakout_against_up_bias_is_r1():
    # Up D1 bias, but the breakout at i is DOWN (not aligned) => R1, not R2.
    n = 130
    closes, ranges = [], []
    for k in range(n):
        c = 1.1000 + 0.0002 * k
        rng = 0.0004
        if k == 125:
            c = c - 0.0060  # sharp down spike
            rng = 0.0015
        elif 121 <= k < 125:
            rng = 0.0015
        closes.append(c)
        ranges.append(rng)
    bars = _mkbars(closes, ranges)
    res = regime_at(bars, 125)
    # bias is measured close[125] vs close[65]; the single down spike keeps
    # the 60-bar move well positive => still UP bias.
    assert res.bias is HTFBias.UP
    assert res.regime is Regime.R1_TREND_PULLBACK
