"""A10 Kunigami v1 wrap tests.

Asserts:
  * `intend()` ALWAYS returns None (the canonical contract).
  * Loss-streak warning fires when 3 of the last 5 high-conviction
    trades were losses; clears when the streak ends.
  * Overconfidence warning fires when squad-wide mean confidence
    crosses the 0.85 threshold over 10+ samples.
  * `warning_active_at` honours the 24h dampener window for the
    Sentinel R5 wiring.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from programs.M001_multi_agent_ensemble.sim.agents.a10_kunigami import (
    A10KunigamiV1,
    ClosedTradeRecord,
    KUNIGAMI_V1_DURATION_HOURS,
    KUNIGAMI_V1_OVERCONF_THRESHOLD,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import FullLedger
from programs.M001_multi_agent_ensemble.sim.core.types import (
    SCHEMA_VERSION,
    Coordinate, MarketState, Thought,
)


def _market(tick: int) -> MarketState:
    return MarketState(
        tick_id=tick, symbol="EURUSD", timeframe="H4",
        as_of=datetime(2024, 1, 1, tzinfo=timezone.utc)
        + timedelta(hours=4 * tick),
        open=1.10, high=1.11, low=1.09, close=1.105, volume=100.0,
    )


def _peer_thought(
    *, agent_id: str, tick: int, conf: float, ttl_ticks: int = 10,
) -> Thought:
    return Thought(
        schema_version=SCHEMA_VERSION,
        agent_id=agent_id, tick_id=tick,
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc)
        + timedelta(hours=4 * tick),
        symbol="EURUSD", narrative="seed",
        tags=["seed"], confidence_in_thought=conf,
        expected_action="long_on_H4_close",
        coordinate=None,
        decision_horizon=datetime(2024, 1, 1, tzinfo=timezone.utc)
        + timedelta(hours=4 * tick),
        ttl_ticks=int(ttl_ticks), references=[],
    )


def _closed_trade(*, pnl: float, conv: float = 0.85) -> ClosedTradeRecord:
    return ClosedTradeRecord(
        agent_id="isagi_yoichi",
        exit_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        pnl_pips=pnl, source_conviction=conv,
    )


def test_intend_always_returns_none():
    k = A10KunigamiV1()
    market = _market(tick=0)
    ledger = FullLedger()
    t = k.observe(market, ledger)
    assert k.intend(market, t) is None
    # And after warnings fire.
    for _ in range(5):
        k.record_closed_trade(_closed_trade(pnl=-15.0))
    t = k.observe(market, ledger)
    assert k.intend(market, t) is None


def test_observation_clean_when_no_trades_no_peers():
    k = A10KunigamiV1()
    t = k.observe(_market(tick=0), FullLedger())
    assert "kunigami_observation_clean" in t.tags
    assert "kunigami_loss_streak_warning" not in t.tags
    assert "kunigami_overconfidence_warning" not in t.tags


def test_loss_streak_warning_fires_on_three_of_five():
    k = A10KunigamiV1()
    # 3 high-conv losses + 2 wins of the last 5 -> warning fires.
    k.record_closed_trade(_closed_trade(pnl=+12.0))
    k.record_closed_trade(_closed_trade(pnl=-15.0))
    k.record_closed_trade(_closed_trade(pnl=-15.0))
    k.record_closed_trade(_closed_trade(pnl=+12.0))
    k.record_closed_trade(_closed_trade(pnl=-15.0))
    t = k.observe(_market(tick=0), FullLedger())
    assert "kunigami_loss_streak_warning" in t.tags


def test_loss_streak_does_not_fire_below_window_fill():
    k = A10KunigamiV1()
    # Only 4 trades in the rolling window -- streak needs full window.
    k.record_closed_trade(_closed_trade(pnl=-15.0))
    k.record_closed_trade(_closed_trade(pnl=-15.0))
    k.record_closed_trade(_closed_trade(pnl=-15.0))
    k.record_closed_trade(_closed_trade(pnl=-15.0))
    t = k.observe(_market(tick=0), FullLedger())
    assert "kunigami_loss_streak_warning" not in t.tags


def test_loss_streak_only_counts_high_conviction_losses():
    k = A10KunigamiV1()
    # 5 LOW-conviction losses -> NO warning.
    for _ in range(5):
        k.record_closed_trade(_closed_trade(pnl=-15.0, conv=0.4))
    t = k.observe(_market(tick=0), FullLedger())
    assert "kunigami_loss_streak_warning" not in t.tags


def test_warning_active_at_24h_window():
    k = A10KunigamiV1()
    # Fill the deque with high-conv losses to fire a warning at the
    # observe() call below.
    for _ in range(5):
        k.record_closed_trade(_closed_trade(pnl=-15.0))
    market = _market(tick=0)
    t = k.observe(market, FullLedger())
    assert "kunigami_loss_streak_warning" in t.tags
    assert k.warning_active_at(market.as_of) is True
    # Just before 24h -- still active.
    near_end = market.as_of + timedelta(
        hours=KUNIGAMI_V1_DURATION_HOURS - 1
    )
    assert k.warning_active_at(near_end) is True
    # Past 24h -- inactive.
    past = market.as_of + timedelta(
        hours=KUNIGAMI_V1_DURATION_HOURS + 1
    )
    assert k.warning_active_at(past) is False


def test_overconfidence_warning_fires_above_threshold():
    k = A10KunigamiV1()
    ledger = FullLedger()
    # 12 prior peer thoughts all at confidence 0.90 -- above 0.85
    # threshold and above the 10-sample floor. Use a high ttl_ticks so
    # all 12 stay visible at tick 13 (the ledger filters stale rows
    # by `current_tick - tick_id > ttl_ticks`).
    for tick in range(12):
        ledger.append(_peer_thought(
            agent_id="isagi_yoichi", tick=tick, conf=0.90,
            ttl_ticks=50,
        ))
    t = k.observe(_market(tick=13), ledger)
    assert "kunigami_overconfidence_warning" in t.tags


def test_overconfidence_does_not_fire_below_threshold():
    k = A10KunigamiV1()
    ledger = FullLedger()
    for tick in range(12):
        ledger.append(_peer_thought(
            agent_id="isagi_yoichi", tick=tick,
            conf=KUNIGAMI_V1_OVERCONF_THRESHOLD - 0.10,
            ttl_ticks=50,
        ))
    t = k.observe(_market(tick=13), ledger)
    assert "kunigami_overconfidence_warning" not in t.tags


def test_overconfidence_requires_min_sample():
    k = A10KunigamiV1()
    ledger = FullLedger()
    # Only 5 peer thoughts -> below the n=10 floor; warning skipped.
    for tick in range(5):
        ledger.append(_peer_thought(
            agent_id="isagi_yoichi", tick=tick, conf=0.95,
            ttl_ticks=50,
        ))
    t = k.observe(_market(tick=6), ledger)
    assert "kunigami_overconfidence_warning" not in t.tags
