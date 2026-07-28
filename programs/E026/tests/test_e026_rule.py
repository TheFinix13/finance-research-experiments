"""E026 rule unit tests — PROTOCOL §3 semantics against the shared engine.

Synthetic long trade: entry 1.1000, soft stop 1.0950 (50 pips),
TP 1.1075 (75 pips = 1.5R). Paths are hand-built H4 bars.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT))

from programs._shared.counterfactual_replay.replay import (  # noqa: E402
    Bar,
    TradeRecord,
    replay,
)
from programs.E026.time_stop_rule import (  # noqa: E402
    REASON_E026_TIME_STOP,
    E026TimeStopRule,
    make_arm_grid,
)

T0 = datetime(2024, 1, 2, 0, 0, tzinfo=timezone.utc)
ENTRY = 1.1000
SOFT_STOP = 1.0950   # 50 pips
TP = 1.1075          # 75 pips = 1.5R
STOP_PIPS = 50.0


def _bar(i: int, o: float, h: float, l: float, c: float) -> Bar:
    return Bar(time=T0 + timedelta(hours=4 * i), open=o, high=h, low=l, close=c)


def _flat_bars(n: int, lo: float = 1.0990, hi: float = 1.1010) -> list[Bar]:
    """Bars that meander ±10 pips around entry — MFE stays at 0.2R."""
    return [_bar(i, 1.1000, hi, lo, 1.1000) for i in range(n)]


def _trade(path: list[Bar], exit_reason: str = "sl",
           exit_price: float = SOFT_STOP, r: float = -1.0) -> TradeRecord:
    exit_time = path[-1].time
    pnl_pips = (exit_price - ENTRY) / 0.0001
    return TradeRecord(
        trade_id="t1", symbol="EURUSD", tf="H4", direction="long",
        entry_time=T0, entry=ENTRY, stop=SOFT_STOP, soft_stop=SOFT_STOP,
        take_profit=TP, stop_pips=STOP_PIPS, tp_pips=75.0,
        r=r, pnl_pips=pnl_pips, exit_time=exit_time, exit_price=exit_price,
        exit_reason=exit_reason,
        mfe_pips=10.0, mae_pips=10.0, mfe_ts=T0, mae_ts=T0,
        mfe_r=0.2, mae_r=0.2,
        path=path, path_resolution="H4",
    )


class TestFiring:
    def test_fires_at_first_bar_past_age_when_mfe_low(self):
        # 20 flat bars (MFE 0.2R); B=12, P=0.5 → fires exactly on bar index 11.
        t = _trade(_flat_bars(20))
        rule = E026TimeStopRule(progress_r=0.50, age_bars=12)
        alt = replay(t, rule=rule)
        assert alt.exit_reason == REASON_E026_TIME_STOP
        assert rule.fired_details is not None
        assert rule.fired_details.bar_index == 11
        assert rule.fired_details.bars_held == 12
        # Closed at bar close = entry → r ≈ 0.
        assert abs(alt.r) < 1e-9

    def test_exempt_once_progress_touched_even_if_later_stagnant(self):
        # Bar 3 spikes to +0.6R (1.1030), then flat forever. P=0.5 → the
        # trade earned its exemption; rule must never fire.
        bars = _flat_bars(30)
        bars[3] = _bar(3, 1.1000, 1.1030, 1.0995, 1.1005)
        t = _trade(bars)
        rule = E026TimeStopRule(progress_r=0.50, age_bars=12)
        alt = replay(t, rule=rule)
        assert rule.fired_details is None
        # Falls back to the original exit (SPEC §4 fall-through).
        assert alt.exit_reason == "sl"
        assert alt.r == t.r

    def test_no_fire_before_age_threshold(self):
        # Only 10 flat bars, B=12 → never fires, falls back to original exit.
        t = _trade(_flat_bars(10))
        rule = E026TimeStopRule(progress_r=0.50, age_bars=12)
        alt = replay(t, rule=rule)
        assert rule.fired_details is None
        assert alt.exit_reason == "sl"

    def test_cannot_fire_on_tp_bar(self):
        # Bar 12 (the first bar past B=12) reaches TP intra-bar. The engine
        # updates MFE BEFORE calling the rule, so mfe_r jumps to 1.5 ≥ P and
        # the fire condition is false — TP must win (PROTOCOL §0).
        bars = _flat_bars(12)
        bars.append(_bar(12, 1.1000, 1.1080, 1.0995, 1.1070))
        t = _trade(bars, exit_reason="tp", exit_price=TP, r=1.5)
        rule = E026TimeStopRule(progress_r=0.75, age_bars=13)
        alt = replay(t, rule=rule)
        assert rule.fired_details is None
        assert alt.exit_reason == "tp"
        assert alt.r == 1.5

    def test_hard_sl_beats_fire_on_same_bar(self):
        # Bar 11 (bars_held=12=B) also crosses the soft stop → hard SL has
        # priority slot 0 and must win the same-bar tie.
        bars = _flat_bars(11)
        bars.append(_bar(11, 1.1000, 1.1005, 1.0940, 1.0960))
        t = _trade(bars)
        rule = E026TimeStopRule(progress_r=0.50, age_bars=12)
        alt = replay(t, rule=rule)
        assert alt.exit_reason == "sl"
        assert alt.exit_price == SOFT_STOP
        assert alt.r == -1.0

    def test_fire_price_and_r_math(self):
        # Flat bars closing at 1.0990 (−10 pips): fire on bar 11 at close
        # → r = −10/50 = −0.2.
        bars = [_bar(i, 1.1000, 1.1010, 1.0985, 1.0990) for i in range(15)]
        t = _trade(bars)
        rule = E026TimeStopRule(progress_r=0.50, age_bars=12)
        alt = replay(t, rule=rule)
        assert alt.exit_reason == REASON_E026_TIME_STOP
        assert abs(alt.exit_price - 1.0990) < 1e-9
        assert abs(alt.r - (-0.2)) < 1e-6


class TestGridAndNull:
    def test_grid_is_15_arms_frozen(self):
        grid = make_arm_grid()
        assert len(grid) == 15
        assert grid[0] == {"arm_id": "P0.25_B12", "progress_r": 0.25, "age_bars": 12}
        assert grid[-1] == {"arm_id": "P0.75_B42", "progress_r": 0.75, "age_bars": 42}

    def test_huge_age_threshold_reproduces_baseline(self):
        # B larger than any path → the rule is inert; alt must equal the
        # original trade on all decision fields (null-arm identity).
        t = _trade(_flat_bars(20))
        rule = E026TimeStopRule(progress_r=0.75, age_bars=10_000)
        alt = replay(t, rule=rule)
        assert rule.fired_details is None
        assert alt.exit_reason == t.exit_reason
        assert alt.exit_price == t.exit_price
        assert alt.r == t.r

    def test_reset_clears_fired_details(self):
        t = _trade(_flat_bars(20))
        rule = E026TimeStopRule(progress_r=0.50, age_bars=12)
        replay(t, rule=rule)
        assert rule.fired_details is not None
        rule.reset()
        assert rule.fired_details is None
