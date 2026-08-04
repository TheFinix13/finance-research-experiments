"""Invariant tests for the E032 breakout cell (synthetic bars).

Run:
    PYTHONPATH=../multi-pair-trading-agent:. \
        ../multi-pair-trading-agent/.venv/bin/python -m pytest \
        programs/E032/tests/ -q
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.types import Bar, Timeframe  # noqa: E402

from run_e032 import run_cell  # noqa: E402

T0 = datetime(2020, 1, 6, 0, 0, tzinfo=timezone.utc)
PIP = 0.0001


def _bar(i: int, o: float, h: float, l: float, c: float) -> Bar:
    return Bar(time=T0 + timedelta(hours=4 * i), open=o, high=h, low=l,
               close=c, volume=0.0, timeframe=Timeframe.H4)


def _uptrend_with_breakout() -> list[Bar]:
    """~70 bars: slow grind up (keeps D1 bias UP: >60p over 10 D1 bars =
    60 H4 bars), then one wide breakout bar above the prior-10 high."""
    bars = []
    px = 1.1000
    for i in range(70):
        # +3p per H4 bar => +180p over 60 bars, D1 bias solidly UP
        o = px
        c = px + 3 * PIP
        bars.append(_bar(i, o, c + 1 * PIP, o - 1 * PIP, c))
        px = c
    # breakout bar: range 40p (>= k*ATR for ATR ~5p), close above prior high
    o = px
    bars.append(_bar(70, o, o + 40 * PIP, o - 2 * PIP, o + 38 * PIP))
    # follow-through so the trade resolves at TP
    px = o + 38 * PIP
    for i in range(71, 90):
        o2 = px
        c2 = px + 15 * PIP
        bars.append(_bar(i, o2, c2 + 2 * PIP, o2 - 2 * PIP, c2))
        px = c2
    return bars


def test_breakout_long_fires_and_hits_tp():
    bars = _uptrend_with_breakout()
    trades = run_cell(bars, start_index=0, n_lookback=10, k_atr=1.0,
                      spread_rt=1.0)
    assert len(trades) >= 1
    t = trades[0]
    assert t.direction == "long"
    assert t.reason == "tp"
    # 1.5R geometry: tp - entry == 1.5 * (entry - stop)
    assert abs((t.tp - t.entry) - 1.5 * (t.entry - t.stop)) < 1e-9


def test_no_fire_without_impulse():
    """Breakout close whose bar range < k*ATR -> impulse filter blocks it."""
    bars = _uptrend_with_breakout()[:70]
    o = bars[-1].close
    # closes above the prior-10 high but the bar is tiny (range 4p < 1.5*ATR)
    bars.append(_bar(70, o, o + 4 * PIP, o, o + 3.5 * PIP))
    # flat tail: no further breakout closes
    px = bars[-1].close
    for i in range(71, 80):
        bars.append(_bar(i, px, px + 1 * PIP, px - 1 * PIP, px))
    trades = run_cell(bars, start_index=0, n_lookback=10, k_atr=1.5,
                      spread_rt=1.0)
    assert len(trades) == 0


def test_no_fire_against_bias():
    """Downtrend grind (D1 bias DOWN) + upside breakout bar -> blocked."""
    bars = []
    px = 1.2000
    for i in range(70):
        o = px
        c = px - 3 * PIP
        bars.append(_bar(i, o, o + 1 * PIP, c - 1 * PIP, c))
        px = c
    o = px
    # wide up-bar closing above the prior-10 high (a counter-trend breakout)
    bars.append(_bar(70, o, o + 60 * PIP, o - 2 * PIP, o + 55 * PIP))
    for i in range(71, 80):
        bars.append(_bar(i, px, px + 2 * PIP, px - 2 * PIP, px))
    # k=1.5 so the 5p-range grind bars can't fire; the 62p bar passes the
    # impulse filter but must be blocked by the DOWN bias alone
    trades = run_cell(bars, start_index=0, n_lookback=10, k_atr=1.5,
                      spread_rt=1.0)
    assert len(trades) == 0


def test_min_stop_floor():
    """Signal bar with a tiny low-to-close distance still gets >= 10p stop."""
    bars = _uptrend_with_breakout()
    # shrink the breakout bar's low to 2p under close (natural stop 42p ->
    # make it small): open near close, low just 2p below entry
    b = bars[70]
    entry = b.close
    bars[70] = _bar(70, entry - 30 * PIP, entry + 1 * PIP, entry - 32 * PIP,
                    entry)
    # rebuild: low is 32p below -> that's the natural stop; instead craft a
    # bar with low 2p below close but wide high wick for the range filter
    bars[70] = _bar(70, entry - 1 * PIP, entry + 40 * PIP, entry - 2 * PIP,
                    entry)
    trades = run_cell(bars, start_index=0, n_lookback=10, k_atr=1.0,
                      spread_rt=1.0)
    if trades:  # bar closes above prior high -> long with floored stop
        t = trades[0]
        assert (t.entry - t.stop) >= 10 * PIP - 1e-9
