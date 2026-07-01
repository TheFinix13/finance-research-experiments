"""Contract tests for F21 -- Reasoning Workspace.

Doctrine 06 v0.5 section 4.1a. Verifies:

- Publish idempotency on `thought_id`.
- Snapshot look-ahead guards (as_of + current_tick + decision_horizon).
- Tier-2 read returns full peer view; Tier-3 read returns own only.
- Symbol / tag filters applied correctly.
- `peer_thoughts` excludes own agent.
- `latest_by_agent` returns most recent per agent.
- Snapshot is immutable (frozen dataclass; mutations raise).
- Empty workspace + edge cases don't explode.
"""
from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta, timezone

import pytest

from programs.M001_multi_agent_ensemble.sim.core.reasoning_workspace import (
    ReasoningWorkspace,
    WorkspaceSnapshot,
)
from programs.M001_multi_agent_ensemble.sim.core.types import (
    SCHEMA_VERSION,
    Thought,
)


T0 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)


def _thought(
    *,
    agent: str = "isagi_yoichi",
    tick: int = 100,
    symbol: str = "EURUSD",
    ts_offset_minutes: int = 0,
    tags: list[str] | None = None,
    conviction: float = 0.7,
    narrative: str = "test",
    dh_offset_minutes: int = 0,
) -> Thought:
    """Fixture for a Thought with sensible defaults.

    `dh_offset_minutes` is the offset FROM `timestamp`, not from T0 --
    so a decision_horizon 5 min in the past of the thought means the
    thought's writer only trusted context bars up to ts - 5 min.
    """
    ts = T0 + timedelta(minutes=ts_offset_minutes)
    return Thought(
        schema_version=SCHEMA_VERSION,
        agent_id=agent,
        tick_id=tick,
        timestamp=ts,
        symbol=symbol,
        narrative=narrative,
        tags=list(tags or ["baseline_zone"]),
        confidence_in_thought=conviction,
        expected_action=None,
        coordinate=None,
        decision_horizon=ts + timedelta(minutes=dh_offset_minutes),
        ttl_ticks=6,
        references=[],
    )


class TestPublishIdempotency:
    def test_first_publish_returns_true(self):
        ws = ReasoningWorkspace()
        assert ws.publish(_thought(agent="a", tick=1)) is True
        assert len(ws.thoughts) == 1

    def test_duplicate_id_returns_false_and_no_append(self):
        ws = ReasoningWorkspace()
        t = _thought(agent="a", tick=1, symbol="EURUSD")
        assert ws.publish(t) is True
        # Same identity fields -> same thought_id -> dedup.
        t2 = _thought(agent="a", tick=1, symbol="EURUSD", narrative="different")
        assert t2.thought_id == t.thought_id
        assert ws.publish(t2) is False
        assert len(ws.thoughts) == 1

    def test_distinct_tick_ids_both_publish(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="a", tick=1))
        ws.publish(_thought(agent="a", tick=2))
        assert len(ws.thoughts) == 2


class TestSnapshotLookAheadGuards:
    def test_excludes_same_tick_thoughts(self):
        """Doctrine section 3.8: t.tick_id >= current_tick is filtered."""
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="a", tick=100, symbol="EURUSD"))
        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10),
            current_tick=100,
        )
        assert snap.thoughts == ()  # same tick is invisible

    def test_excludes_future_tick_thoughts(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="a", tick=105, symbol="EURUSD"))
        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10),
            current_tick=100,
        )
        assert snap.thoughts == ()

    def test_includes_earlier_tick_thoughts(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="a", tick=99, symbol="EURUSD"))
        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10),
            current_tick=100,
        )
        assert len(snap.thoughts) == 1

    def test_excludes_thoughts_with_ts_after_as_of(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="a", tick=99, ts_offset_minutes=30))
        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10),
            current_tick=100,
        )
        assert snap.thoughts == ()

    def test_excludes_thoughts_with_decision_horizon_after_as_of(self):
        """Writer's own look-ahead guard is respected."""
        ws = ReasoningWorkspace()
        # Thought at t=T0+5, but writer trusts context only up to T0+15
        # (dh > ts, meaning the writer projected 10 min forward).
        ws.publish(_thought(
            agent="a", tick=99, ts_offset_minutes=5,
            dh_offset_minutes=10,  # decision_horizon = T0+15
        ))
        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10),  # reader as_of = T0+10
            current_tick=100,
        )
        # The writer's decision_horizon (T0+15) is AFTER the reader's
        # as_of (T0+10) -- the reader's context does not yet cover the
        # writer's claim. Reader must drop the Thought.
        assert snap.thoughts == ()


class TestTierFilters:
    def _multi_agent_ws(self) -> ReasoningWorkspace:
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="isagi_yoichi", tick=99, symbol="EURUSD"))
        ws.publish(_thought(agent="nagi_seishiro", tick=99, symbol="EURUSD"))
        ws.publish(_thought(agent="bachira_meguru", tick=98, symbol="EURUSD"))
        return ws

    def test_tier_2_sees_full_peer_view(self):
        ws = self._multi_agent_ws()
        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10),
            current_tick=100,
        )
        visible = snap.read_for(agent_id="isagi_yoichi", tier=2)
        agent_ids = {t.agent_id for t in visible}
        assert agent_ids == {"isagi_yoichi", "nagi_seishiro", "bachira_meguru"}

    def test_tier_3_sees_only_own(self):
        ws = self._multi_agent_ws()
        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10),
            current_tick=100,
        )
        visible = snap.read_for(agent_id="isagi_yoichi", tier=3)
        assert all(t.agent_id == "isagi_yoichi" for t in visible)
        assert len(visible) == 1

    def test_symbol_filter(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="a", tick=99, symbol="EURUSD"))
        ws.publish(_thought(agent="a", tick=98, symbol="GBPUSD"))
        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10),
            current_tick=100,
        )
        eur = snap.read_for(agent_id="a", tier=2, symbol="EURUSD")
        gbp = snap.read_for(agent_id="a", tier=2, symbol="GBPUSD")
        assert len(eur) == 1 and eur[0].symbol == "EURUSD"
        assert len(gbp) == 1 and gbp[0].symbol == "GBPUSD"

    def test_tag_filter(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="a", tick=99, tags=["baseline_zone"]))
        ws.publish(_thought(agent="a", tick=98, tags=["breakout"]))
        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10),
            current_tick=100,
        )
        zones = snap.read_for(agent_id="a", tier=2, tag="baseline_zone")
        assert len(zones) == 1
        assert "baseline_zone" in zones[0].tags


class TestPeerThoughts:
    def test_excludes_own_agent(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="isagi_yoichi", tick=99))
        ws.publish(_thought(agent="nagi_seishiro", tick=99))
        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10),
            current_tick=100,
        )
        peers = snap.peer_thoughts(agent_id="isagi_yoichi")
        assert all(t.agent_id != "isagi_yoichi" for t in peers)
        assert len(peers) == 1
        assert peers[0].agent_id == "nagi_seishiro"


class TestLatestByAgent:
    def test_returns_most_recent_per_agent(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="a", tick=95))
        ws.publish(_thought(agent="a", tick=98))  # newer
        ws.publish(_thought(agent="b", tick=97))
        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10),
            current_tick=100,
        )
        latest = snap.latest_by_agent()
        assert latest["a"].tick_id == 98
        assert latest["b"].tick_id == 97

    def test_symbol_filter(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="a", tick=95, symbol="EURUSD"))
        ws.publish(_thought(agent="a", tick=98, symbol="GBPUSD"))
        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10),
            current_tick=100,
        )
        eur = snap.latest_by_agent(symbol="EURUSD")
        assert eur["a"].tick_id == 95
        assert "b" not in eur


class TestImmutability:
    def test_snapshot_is_frozen(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="a", tick=99))
        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10),
            current_tick=100,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            snap.as_of = T0

    def test_snapshot_thoughts_is_tuple_not_list(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="a", tick=99))
        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10),
            current_tick=100,
        )
        assert isinstance(snap.thoughts, tuple)

    def test_snapshot_stable_across_subsequent_publishes(self):
        """Publishing after snapshot doesn't leak into the snapshot."""
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="a", tick=99))
        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10),
            current_tick=100,
        )
        ws.publish(_thought(agent="b", tick=99))
        assert len(snap.thoughts) == 1


class TestEdgeCases:
    def test_empty_workspace_produces_empty_snapshot(self):
        ws = ReasoningWorkspace()
        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10),
            current_tick=100,
        )
        assert snap.thoughts == ()
        assert snap.read_for(agent_id="a", tier=2) == ()
        assert snap.peer_thoughts(agent_id="a") == ()
        assert snap.latest_by_agent() == {}

    def test_tier_1_treated_as_full_view(self):
        """Tier-1 is 'human dashboard' -- gets the full peer view too."""
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="a", tick=99))
        ws.publish(_thought(agent="b", tick=99))
        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10),
            current_tick=100,
        )
        visible = snap.read_for(agent_id="a", tier=1)
        assert len(visible) == 2

    def test_sorted_by_tick_id_ascending(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="a", tick=99))
        ws.publish(_thought(agent="b", tick=97))
        ws.publish(_thought(agent="c", tick=98))
        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10),
            current_tick=100,
        )
        visible = snap.read_for(agent_id="a", tier=2)
        assert [t.tick_id for t in visible] == [97, 98, 99]
