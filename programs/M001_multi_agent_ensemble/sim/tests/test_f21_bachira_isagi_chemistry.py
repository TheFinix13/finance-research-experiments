"""F21 chemistry test -- flagship "Isagi -> Bachira TF confluence".

Doctrine 06 v0.5 section 4.1a. Verifies:

- Bachira's ``intend`` reads the F21 ``WorkspaceSnapshot`` for peer
  Thoughts.
- When Isagi's latest same-symbol Thought is a fired LONG zone signal
  (coordinate != None, expected_action="long_on_H4_close"), Bachira's
  matching LONG proposal receives the +0.05 peer-confluence lift.
- No lift when Isagi is waiting (coordinate=None) or on a different
  symbol.
- No lift when directions disagree.
- No lift when the workspace is None (backwards compat).

The test doesn't need real market bars -- we construct Isagi Thoughts
directly and drive Bachira's peer detection helper.
"""
from __future__ import annotations

import datetime as dt

from programs.M001_multi_agent_ensemble.sim.agents.a02_bachira import (
    BACHIRA_PEER_CONFLUENCE_LIFT,
    BACHIRA_PEER_PARTNER_ID,
    A2BachiraV1,
)
from programs.M001_multi_agent_ensemble.sim.core.reasoning_workspace import (
    ReasoningWorkspace,
)
from programs.M001_multi_agent_ensemble.sim.core.types import (
    SCHEMA_VERSION,
    Coordinate,
    Thought,
)

UTC = dt.timezone.utc


def _isagi_fired_thought(
    *,
    symbol: str = "EURUSD",
    direction: str = "long",
    tick_id: int = 100,
    as_of: dt.datetime = dt.datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
) -> Thought:
    """Construct an Isagi Thought with a fired zone signal."""
    coord = Coordinate(
        agent_id=BACHIRA_PEER_PARTNER_ID,
        symbol=symbol,
        price_lo=1.0900,
        price_hi=1.0925,
        time_start=as_of,
        time_end=as_of + dt.timedelta(hours=24),
        vol_band=(0.5, 1.0),
        regime_predicate="trending",
        expected_strength=0.8,
        direction_bias=direction,
    )
    return Thought(
        schema_version=SCHEMA_VERSION,
        agent_id=BACHIRA_PEER_PARTNER_ID,
        tick_id=tick_id,
        timestamp=as_of,
        symbol=symbol,
        narrative=f"[isagi v1] {symbol} H4 fired {direction} zone",
        tags=["zone_d1_against", "htf_against", "canon:isagi"],
        confidence_in_thought=0.65,
        expected_action=f"{direction}_on_H4_close",
        coordinate=coord,
        decision_horizon=as_of,
        ttl_ticks=6,
        references=[],
    )


def _isagi_waiting_thought(
    *,
    symbol: str = "EURUSD",
    tick_id: int = 100,
    as_of: dt.datetime = dt.datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
) -> Thought:
    """Construct an Isagi Thought in observation-only (waiting) state."""
    return Thought(
        schema_version=SCHEMA_VERSION,
        agent_id=BACHIRA_PEER_PARTNER_ID,
        tick_id=tick_id,
        timestamp=as_of,
        symbol=symbol,
        narrative=f"[isagi v1] {symbol} H4 waiting",
        tags=["zone_d1_against", "htf_against", "canon:isagi"],
        confidence_in_thought=0.0,
        expected_action="wait",
        coordinate=None,
        decision_horizon=as_of,
        ttl_ticks=1,
        references=[],
    )


def _snapshot_with(thought: Thought, current_tick: int = 101) -> object:
    """Publish `thought` to a workspace and snapshot with backwards-only
    look-ahead."""
    ws = ReasoningWorkspace()
    ws.publish(thought)
    return ws.snapshot(
        as_of=thought.timestamp + dt.timedelta(hours=4),
        current_tick=current_tick,
    )


class TestBachiraIsagiChemistry:

    def test_peer_confluence_long_matches(self):
        bachira = A2BachiraV1()
        peer = _isagi_fired_thought(direction="long", tick_id=100)
        snap = _snapshot_with(peer, current_tick=101)
        assert bachira._detect_isagi_peer_confluence(
            workspace=snap, symbol="EURUSD", direction="long",
        ) is True

    def test_peer_confluence_short_matches(self):
        bachira = A2BachiraV1()
        peer = _isagi_fired_thought(direction="short", tick_id=100)
        snap = _snapshot_with(peer, current_tick=101)
        assert bachira._detect_isagi_peer_confluence(
            workspace=snap, symbol="EURUSD", direction="short",
        ) is True

    def test_direction_disagreement_no_confluence(self):
        bachira = A2BachiraV1()
        peer = _isagi_fired_thought(direction="long", tick_id=100)
        snap = _snapshot_with(peer, current_tick=101)
        assert bachira._detect_isagi_peer_confluence(
            workspace=snap, symbol="EURUSD", direction="short",
        ) is False

    def test_waiting_isagi_no_confluence(self):
        """Coordinate=None -> Isagi is waiting, no confluence."""
        bachira = A2BachiraV1()
        peer = _isagi_waiting_thought(tick_id=100)
        snap = _snapshot_with(peer, current_tick=101)
        assert bachira._detect_isagi_peer_confluence(
            workspace=snap, symbol="EURUSD", direction="long",
        ) is False

    def test_different_symbol_no_confluence(self):
        bachira = A2BachiraV1()
        peer = _isagi_fired_thought(symbol="GBPUSD", direction="long",
                                    tick_id=100)
        snap = _snapshot_with(peer, current_tick=101)
        assert bachira._detect_isagi_peer_confluence(
            workspace=snap, symbol="EURUSD", direction="long",
        ) is False

    def test_no_workspace_no_confluence(self):
        bachira = A2BachiraV1()
        assert bachira._detect_isagi_peer_confluence(
            workspace=None, symbol="EURUSD", direction="long",
        ) is False

    def test_empty_workspace_no_confluence(self):
        bachira = A2BachiraV1()
        ws = ReasoningWorkspace()
        snap = ws.snapshot(
            as_of=dt.datetime(2025, 1, 1, tzinfo=UTC),
            current_tick=101,
        )
        assert bachira._detect_isagi_peer_confluence(
            workspace=snap, symbol="EURUSD", direction="long",
        ) is False

    def test_same_tick_isagi_thought_excluded(self):
        """Look-ahead guard -- Bachira on tick T cannot see Isagi on tick T."""
        bachira = A2BachiraV1()
        peer = _isagi_fired_thought(direction="long", tick_id=100)
        ws = ReasoningWorkspace()
        ws.publish(peer)
        # snapshot at CURRENT tick = 100 -> peer at tick 100 excluded
        snap = ws.snapshot(
            as_of=peer.timestamp + dt.timedelta(hours=4),
            current_tick=100,
        )
        assert bachira._detect_isagi_peer_confluence(
            workspace=snap, symbol="EURUSD", direction="long",
        ) is False

    def test_confluence_lift_constant_value(self):
        """Doctrine 4.1a locks the +0.05 lift value."""
        assert BACHIRA_PEER_CONFLUENCE_LIFT == 0.05


class TestReoStyleWorkspaceContract:
    """Cross-agent contract: any agent using ``read_workspace`` on
    BaseStriker gets a tier-appropriate view without needing to override.
    """

    def test_bachira_read_workspace_default_returns_all_peer_thoughts(self):
        from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi import (
            A1IsagiV1,
        )

        bachira = A2BachiraV1()
        peer = _isagi_fired_thought(direction="long", tick_id=100)
        snap = _snapshot_with(peer, current_tick=101)
        result = bachira.read_workspace(snap, as_of=peer.timestamp
                                         + dt.timedelta(hours=4))
        # Bachira is tier-2 -> sees all peer + own thoughts.
        assert len(result) == 1
        assert result[0].agent_id == "isagi_yoichi"

        # Isagi is tier-1 -> also sees the peer thought.
        isagi = A1IsagiV1()
        result_isagi = isagi.read_workspace(snap, as_of=peer.timestamp
                                             + dt.timedelta(hours=4))
        assert len(result_isagi) == 1
