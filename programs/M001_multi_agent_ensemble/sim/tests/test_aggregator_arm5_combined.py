"""Contract tests for Phi5 Arm 5 -- the combined stacking of Arms 1+2+3+4.

Verifies pipeline order (TQS floor -> merge -> multi-position -> HRP) and
audit-decision journaling.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from programs.M001_multi_agent_ensemble.sim.core.aggregator_arms import (
    CombinedAggregator,
    HRPAggregator,
    MultiPositionAggregator,
    TQSFloorAggregator,
)
from programs.M001_multi_agent_ensemble.sim.core.types import AgentProposal, LadderRung


T0 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)


def _prop(
    *,
    agent: str,
    symbol: str = "EURUSD",
    direction: str = "long",
    conviction: float = 0.7,
    entry: float = 1.1000,
    stop_pips: float = 0.5,
    tick_id: int = 1,
) -> AgentProposal:
    """Small-stop AgentProposal (fits R6 cap by default)."""
    stop = entry - stop_pips / 10000.0 if direction == "long" else entry + stop_pips / 10000.0
    target = entry + 0.0020 if direction == "long" else entry - 0.0020
    return AgentProposal(
        agent_id=agent, tick_id=tick_id,
        source_thought_id=f"{agent}:{tick_id}:{symbol}",
        timestamp=T0, symbol=symbol, direction=direction,
        entry=entry, stop=stop,
        ladder=[LadderRung(price=target, fraction=1.0)],
        conviction=conviction, regime_fit=0.6,
        valid_until=T0 + timedelta(hours=4),
    )


def _build_aggregator():
    """Fresh CombinedAggregator with sandbox defaults."""
    tqs_floor = TQSFloorAggregator()
    multi_pos = MultiPositionAggregator(
        equity_dollars=100.0, pip_value_per_min_lot=0.10,
    )
    hrp = HRPAggregator()
    return CombinedAggregator(
        tqs_floor=tqs_floor, multi_position=multi_pos, hrp=hrp,
    )


def test_arm5_passes_through_when_no_history_no_hrp_no_open():
    """Cold-start invariant: with empty state, Arm 5 admits any proposal
    that passes the R6 cap (falls back to conviction >= 0 and HRP weight
    = 1.0 pass-through)."""
    agg = _build_aggregator()
    p = _prop(agent="isagi_yoichi")
    admitted, decisions = agg.process([p], tick_id=1)
    assert len(admitted) == 1
    assert decisions[-1].admitted is True


def test_arm5_tqs_floor_rejects_low_conviction_after_min_n():
    """Once an agent has >= 200 historical convictions, the floor kicks in."""
    agg = _build_aggregator()
    for _ in range(210):
        agg.tqs_floor.update_history("above_min_n", [0.80])
    # P40 of [0.80] * 210 is 0.80.
    p_low = _prop(agent="above_min_n", conviction=0.30)
    admitted, decisions = agg.process([p_low], tick_id=1)
    assert len(admitted) == 0
    assert any(d.stage == "tqs_floor" and not d.admitted for d in decisions)


def test_arm5_same_direction_merge_produces_single_admission():
    """Two longs on the same symbol collapse to one merged intent before
    multi-position admission."""
    agg = _build_aggregator()
    p1 = _prop(agent="isagi", direction="long", conviction=0.6)
    p2 = _prop(agent="nagi", direction="long", conviction=0.8)
    admitted, decisions = agg.process([p1, p2], tick_id=1)
    assert len(admitted) == 1
    assert admitted[0].agent_id.startswith("arm3_merged_")


def test_arm5_multi_position_lets_opposing_directions_through():
    """One long + one short on the same symbol don't collide via Arm 3
    (opposite directions) and both fit Arm 4's K=2 slot on distinct
    agents."""
    agg = _build_aggregator()
    p_long = _prop(agent="isagi", direction="long")
    p_short = _prop(agent="nagi", direction="short")
    admitted, _ = agg.process([p_long, p_short], tick_id=1)
    assert len(admitted) == 2


def test_arm5_hrp_zero_weight_agent_gets_rejected():
    """When HRP assigns weight 0 to an agent (e.g. below min_trades in a
    refitted snapshot), Arm 5 rejects that agent's admitted-so-far
    proposal at the HRP stage."""
    agg = _build_aggregator()
    # Refit with only agent 'a' eligible -> agent 'b' gets zero weight.
    agg.hrp.refit(
        per_agent_window_tqs={
            "a": [0.30, 0.32, 0.31, 0.33, 0.32],
            "b": [0.25, 0.24, 0.26, 0.25, 0.24],
        },
        per_agent_trade_counts={"a": 100, "b": 5},   # b below min_trades
        window_start=T0, window_end=T0 + timedelta(days=365),
    )
    p_b = _prop(agent="b")
    admitted, decisions = agg.process([p_b], tick_id=1)
    assert len(admitted) == 0
    hrp_stage_decisions = [d for d in decisions if d.stage == "hrp"]
    assert hrp_stage_decisions, "expected HRP stage decision"
    assert hrp_stage_decisions[0].hrp_weight == 0.0


def test_arm5_records_decisions_history():
    agg = _build_aggregator()
    agg.process([_prop(agent="a")], tick_id=1)
    agg.process([_prop(agent="b")], tick_id=2)
    assert len(agg.decisions_history) == 2
