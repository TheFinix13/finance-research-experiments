"""F22b contract tests -- tick-barrier snapshot.

Pre-F22b, ``ReasoningWorkspace.snapshot(current_tick=T)`` filtered with
``t.tick_id < current_tick``, meaning peer Thoughts published on tick T
were invisible to agents running ``intend()`` on tick T. Rin's Phase
T-evolve peer-scan was therefore reading Isagi's tick T-1 metavision
read, not his tick T read -- a systematic 1-tick lag on her inference.

F22b adds ``snapshot_at_barrier`` with rule ``t.tick_id <= current_tick``
plus the same decision-horizon and as_of guards. Doctrine sec 3.8
forbids look-ahead, not same-tick reads at the barrier: at the barrier
every peer publish for tick T has been committed, so reading them in
Phase 2 is committed information, not look-ahead.

This test module verifies:

- Strict ``snapshot(...)`` still refuses same-tick Thoughts.
- ``snapshot_at_barrier(...)`` includes them.
- Both still refuse ``tick_id > current_tick`` (no look-ahead crossed).
- Both still apply ``timestamp <= as_of`` and ``decision_horizon <= as_of``
  guards (the writer's own look-ahead protection stays intact).
- Both return frozen ``WorkspaceSnapshot`` instances.
"""
from __future__ import annotations

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
    tick: int = 10,
    symbol: str = "EURUSD",
    ts_offset_minutes: int = 0,
    dh_offset_minutes: int = 0,
) -> Thought:
    ts = T0 + timedelta(minutes=ts_offset_minutes)
    return Thought(
        schema_version=SCHEMA_VERSION,
        agent_id=agent,
        tick_id=tick,
        timestamp=ts,
        symbol=symbol,
        narrative="",
        tags=["baseline"],
        confidence_in_thought=0.7,
        expected_action=None,
        coordinate=None,
        decision_horizon=ts + timedelta(minutes=dh_offset_minutes),
        ttl_ticks=6,
        references=[],
    )


class TestStrictSnapshotStillRefusesSameTick:
    def test_strict_snapshot_returns_nothing_from_current_tick(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="isagi_yoichi", tick=10, ts_offset_minutes=0))
        ws.publish(_thought(agent="bachira_meguru", tick=10, ts_offset_minutes=1))
        ws.publish(_thought(agent="itoshi_rin", tick=10, ts_offset_minutes=2))

        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10), current_tick=10,
        )
        assert len(snap.thoughts) == 0

    def test_strict_snapshot_returns_prior_tick_thoughts(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="isagi_yoichi", tick=9, ts_offset_minutes=-5))
        ws.publish(_thought(agent="isagi_yoichi", tick=10, ts_offset_minutes=0))

        snap = ws.snapshot(
            as_of=T0 + timedelta(minutes=10), current_tick=10,
        )
        assert len(snap.thoughts) == 1
        assert snap.thoughts[0].tick_id == 9


class TestBarrierSnapshotIncludesSameTick:
    def test_barrier_snapshot_includes_current_tick_publishes(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="isagi_yoichi", tick=10, ts_offset_minutes=0))
        ws.publish(_thought(agent="bachira_meguru", tick=10, ts_offset_minutes=1))
        ws.publish(_thought(agent="itoshi_rin", tick=10, ts_offset_minutes=2))

        snap = ws.snapshot_at_barrier(
            as_of=T0 + timedelta(minutes=10), current_tick=10,
        )
        assert len(snap.thoughts) == 3
        agent_ids = {t.agent_id for t in snap.thoughts}
        assert agent_ids == {"isagi_yoichi", "bachira_meguru", "itoshi_rin"}

    def test_barrier_snapshot_includes_prior_tick_thoughts_too(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="isagi_yoichi", tick=8, ts_offset_minutes=-10))
        ws.publish(_thought(agent="isagi_yoichi", tick=9, ts_offset_minutes=-5))
        ws.publish(_thought(agent="isagi_yoichi", tick=10, ts_offset_minutes=0))

        snap = ws.snapshot_at_barrier(
            as_of=T0 + timedelta(minutes=10), current_tick=10,
        )
        assert len(snap.thoughts) == 3
        ticks = {t.tick_id for t in snap.thoughts}
        assert ticks == {8, 9, 10}


class TestBarrierSnapshotStillRefusesLookAhead:
    def test_future_tick_never_visible_via_barrier(self):
        """The barrier admits ``tick_id <= current_tick`` -- future ticks
        (tick_id > current_tick) are still refused. This is the honest
        look-ahead guard.
        """
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="isagi_yoichi", tick=11, ts_offset_minutes=0))

        snap = ws.snapshot_at_barrier(
            as_of=T0 + timedelta(minutes=10), current_tick=10,
        )
        assert len(snap.thoughts) == 0

    def test_future_timestamp_still_refused(self):
        """Even a tick-10 Thought whose timestamp is 3 minutes AFTER
        ``as_of`` must not appear; the ``timestamp <= as_of`` guard
        stays intact.
        """
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="isagi_yoichi", tick=10, ts_offset_minutes=15))

        snap = ws.snapshot_at_barrier(
            as_of=T0 + timedelta(minutes=10), current_tick=10,
        )
        assert len(snap.thoughts) == 0

    def test_decision_horizon_after_as_of_still_refused(self):
        """The writer's own look-ahead guard: if the Thought's
        ``decision_horizon`` is AFTER ``as_of``, the writer was reasoning
        with data past the current bar and the Thought must be filtered
        by both snapshot variants.
        """
        ws = ReasoningWorkspace()
        ws.publish(_thought(
            agent="isagi_yoichi",
            tick=10,
            ts_offset_minutes=0,
            dh_offset_minutes=60,   # decision_horizon 60min past its own timestamp
        ))

        snap = ws.snapshot_at_barrier(
            as_of=T0 + timedelta(minutes=10), current_tick=10,
        )
        assert len(snap.thoughts) == 0


class TestBarrierSnapshotIsFrozen:
    def test_barrier_snapshot_returns_workspacesnapshot(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="isagi_yoichi", tick=10, ts_offset_minutes=0))
        snap = ws.snapshot_at_barrier(
            as_of=T0 + timedelta(minutes=10), current_tick=10,
        )
        assert isinstance(snap, WorkspaceSnapshot)
        assert snap.current_tick == 10

    def test_barrier_snapshot_cannot_mutate_thoughts(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="isagi_yoichi", tick=10, ts_offset_minutes=0))
        snap = ws.snapshot_at_barrier(
            as_of=T0 + timedelta(minutes=10), current_tick=10,
        )
        # ``snap.thoughts`` is a tuple; assigning would be caught by
        # dataclass(frozen=True). But mutating the tuple itself is
        # impossible.
        with pytest.raises((AttributeError, TypeError)):
            snap.thoughts = ()   # type: ignore[misc]


class TestBarrierSnapshotFilters:
    """The barrier snapshot must not break existing ``read_for`` /
    ``peer_thoughts`` / ``latest_by_agent`` semantics -- only the
    same-tick admission changed.
    """

    def test_read_for_returns_barrier_visible_thoughts(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="isagi_yoichi", tick=10, ts_offset_minutes=0))
        ws.publish(_thought(agent="bachira_meguru", tick=10, ts_offset_minutes=1))
        snap = ws.snapshot_at_barrier(
            as_of=T0 + timedelta(minutes=10), current_tick=10,
        )
        got = snap.read_for(agent_id="itoshi_rin")
        assert len(got) == 2
        assert {t.agent_id for t in got} == {"isagi_yoichi", "bachira_meguru"}

    def test_peer_thoughts_excludes_own_agent(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(agent="itoshi_rin", tick=10, ts_offset_minutes=0))
        ws.publish(_thought(agent="isagi_yoichi", tick=10, ts_offset_minutes=1))
        snap = ws.snapshot_at_barrier(
            as_of=T0 + timedelta(minutes=10), current_tick=10,
        )
        peers = snap.peer_thoughts(agent_id="itoshi_rin")
        assert len(peers) == 1
        assert peers[0].agent_id == "isagi_yoichi"
