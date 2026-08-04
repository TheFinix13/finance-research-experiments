"""Invariant tests for the E031 portfolio slot simulator (synthetic bars).

Run:
    PYTHONPATH=../multi-pair-trading-agent:. \
        ../multi-pair-trading-agent/.venv/bin/python -m pytest \
        programs/E031/tests/ -q
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.types import Bar, Timeframe  # noqa: E402

from run_e031 import Sig, simulate  # noqa: E402

T0 = datetime(2020, 1, 6, 0, 0, tzinfo=timezone.utc)


def _bar(i: int, o: float, h: float, l: float, c: float) -> Bar:
    return Bar(time=T0 + timedelta(hours=4 * i), open=o, high=h, low=l,
               close=c, volume=0.0, timeframe=Timeframe.H4)


def _flat_bars(n: int, px: float = 1.1000) -> list[Bar]:
    return [_bar(i, px, px + 0.0001, px - 0.0001, px) for i in range(n)]


def _sig(i: int, bars: list[Bar], direction: str = "long",
         stop_pips: float = 20.0, rr: float = 1.5) -> Sig:
    e = bars[i].close
    sd = stop_pips * 0.0001
    if direction == "long":
        return Sig(i, bars[i].time, "long", e, e - sd, e + rr * sd)
    return Sig(i, bars[i].time, "short", e, e + sd, e - rr * sd)


def test_cap1_blocks_second_signal_and_counts_conflict():
    bars = _flat_bars(30)
    sigs = [_sig(2, bars), _sig(5, bars)]  # second arrives while first open
    res = simulate("A0_cap1", {"EURUSD": bars}, {"EURUSD": sigs}, T0)
    assert res.slot_conflicts["EURUSD"] == 1
    # nothing exits on flat bars -> only 1 ticket ever opened, 0 closed trades
    assert len(res.trades) == 0


def test_cap2_admits_second_signal():
    bars = _flat_bars(30)
    sigs = [_sig(2, bars), _sig(5, bars)]
    res = simulate("A1_cap2", {"EURUSD": bars}, {"EURUSD": sigs}, T0)
    assert res.slot_conflicts["EURUSD"] == 0


def test_b1_replaces_losing_incumbent():
    bars = _flat_bars(30)
    # after entry at bar 3 open (1.1000), price drops 10p (=0.5R of a 20p
    # stop, beyond the -0.25R threshold) and sits there
    for i in range(4, 30):
        px = 1.0990
        bars[i] = _bar(i, px, px + 0.0001, px - 0.0001, px)
    sigs = [_sig(2, bars), _sig(6, bars, direction="short")]
    res = simulate("B1_replace_losing", {"EURUSD": bars}, {"EURUSD": sigs}, T0)
    assert res.replacements == 1
    assert any(t["reason"] == "replaced" for t in res.trades)


def test_b2_blocks_opposite_direction_replacement():
    bars = _flat_bars(30)
    for i in range(4, 30):
        px = 1.0990
        bars[i] = _bar(i, px, px + 0.0001, px - 0.0001, px)
    sigs = [_sig(2, bars), _sig(6, bars, direction="short")]
    res = simulate("B2_replace_same_dir", {"EURUSD": bars}, {"EURUSD": sigs}, T0)
    assert res.replacements == 0


def test_b1_keeps_winning_incumbent():
    bars = _flat_bars(30)
    # price rises 10p after entry: incumbent is winning, must NOT be replaced
    for i in range(4, 30):
        px = 1.1010
        bars[i] = _bar(i, px, px + 0.0001, px - 0.0001, px)
    sigs = [_sig(2, bars), _sig(6, bars)]
    res = simulate("B1_replace_losing", {"EURUSD": bars}, {"EURUSD": sigs}, T0)
    assert res.replacements == 0
    assert res.slot_conflicts["EURUSD"] == 1


def test_sl_first_tie_break_and_costs():
    bars = _flat_bars(30)
    # bar 5 straddles both SL (1.0980) and TP (1.1030) -> must close as SL
    bars[5] = _bar(5, 1.1000, 1.1040, 1.0970, 1.1000)
    sigs = [_sig(2, bars)]
    res = simulate("A0_cap1", {"EURUSD": bars}, {"EURUSD": sigs}, T0)
    assert len(res.trades) == 1
    t = res.trades[0]
    assert t["reason"] == "sl"
    # net pips = -20 raw - 1.0 spread
    assert abs(t["pnl_pips_net"] - (-21.0)) < 1e-6
