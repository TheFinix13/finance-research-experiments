"""F22a contract tests -- structured ``ThoughtRead`` on Thought.

Doctrine 06 sec 4.1a + F22a amendment. Verifies:

- ``ThoughtRead`` dataclass is frozen, JSON-serialises cleanly, and
  survives round-tripping.
- ``Thought.read`` defaults to ``None`` (backwards compatibility).
- ``Thought.to_jsonable`` includes ``read`` when present.
- ``WorkspaceSnapshot.read_for(signal_family=...)`` narrows to matching
  Thoughts and skips ``read=None`` Thoughts.
- ``WorkspaceSnapshot.peer_thoughts(signal_family=...)`` same, minus own.
- **Semantic test:** given two peer Thoughts on the same direction --
  one with ``signal_family="metavision"`` and one with
  ``signal_family="pattern_rebel"`` -- Rin's Phase T-evolve peer scan
  narrowed by ``signal_family="metavision"`` returns only Isagi's
  Thought. Pre-F22a, Rin could not distinguish these.

The F22a helpers (``stop_pips_from_prices``, ``expected_r_from_prices``)
are also tested here since they land alongside ``ThoughtRead``.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from programs.M001_multi_agent_ensemble.sim.core.provenance_pips import (
    expected_r_from_prices,
    pip_size_for,
    stop_pips_from_prices,
)
from programs.M001_multi_agent_ensemble.sim.core.reasoning_workspace import (
    ReasoningWorkspace,
)
from programs.M001_multi_agent_ensemble.sim.core.types import (
    SCHEMA_VERSION,
    Thought,
    ThoughtRead,
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
    read: ThoughtRead | None = None,
) -> Thought:
    ts = T0 + timedelta(minutes=ts_offset_minutes)
    return Thought(
        schema_version=SCHEMA_VERSION,
        agent_id=agent,
        tick_id=tick,
        timestamp=ts,
        symbol=symbol,
        narrative=narrative,
        tags=list(tags or ["baseline"]),
        confidence_in_thought=conviction,
        expected_action=None,
        coordinate=None,
        decision_horizon=ts,
        ttl_ticks=6,
        references=[],
        read=read,
    )


class TestThoughtReadDataclass:
    def test_defaults(self):
        r = ThoughtRead(signal_family="metavision", direction_bias="long")
        assert r.regime_read == "unknown"
        assert r.expected_stop_pips is None
        assert r.expected_r is None
        assert r.driving_evidence == ()

    def test_to_jsonable_shape(self):
        r = ThoughtRead(
            signal_family="metavision",
            direction_bias="long",
            regime_read="trending",
            expected_stop_pips=25.4,
            expected_r=1.5,
            driving_evidence=("zone_d1_against", "htf_against"),
        )
        j = r.to_jsonable()
        assert j == {
            "signal_family": "metavision",
            "direction_bias": "long",
            "regime_read": "trending",
            "expected_stop_pips": 25.4,
            "expected_r": 1.5,
            "driving_evidence": ["zone_d1_against", "htf_against"],
        }
        # Round-trip through JSON.
        parsed = json.loads(json.dumps(j, sort_keys=True))
        assert parsed == j


class TestThoughtBackwardsCompat:
    def test_read_defaults_to_none(self):
        t = _thought()
        assert t.read is None

    def test_to_jsonable_includes_read_none_for_legacy_thought(self):
        t = _thought()
        j = t.to_jsonable()
        assert "read" in j
        assert j["read"] is None

    def test_to_jsonable_includes_read_when_present(self):
        r = ThoughtRead(signal_family="metavision", direction_bias="long")
        t = _thought(read=r)
        j = t.to_jsonable()
        assert j["read"] == r.to_jsonable()


class TestWorkspaceSignalFamilyFilter:
    def test_read_for_narrows_by_signal_family(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(
            agent="isagi_yoichi", tick=1,
            read=ThoughtRead(signal_family="metavision", direction_bias="long"),
        ))
        ws.publish(_thought(
            agent="bachira_meguru", tick=1,
            read=ThoughtRead(signal_family="pattern_rebel", direction_bias="long"),
        ))
        ws.publish(_thought(
            agent="chigiri_hyoma", tick=1,
            read=ThoughtRead(signal_family="breakout", direction_bias="long"),
        ))
        snap = ws.snapshot(as_of=T0 + timedelta(minutes=1), current_tick=2)
        # Filter down to just metavision.
        just_meta = snap.read_for(
            agent_id="itoshi_rin", signal_family="metavision",
        )
        assert len(just_meta) == 1
        assert just_meta[0].agent_id == "isagi_yoichi"

    def test_read_for_skips_read_none_thoughts_when_filtering(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(
            agent="isagi_yoichi", tick=1,
            read=ThoughtRead(signal_family="metavision", direction_bias="long"),
        ))
        # Bachira's thought has read=None (legacy path); should NOT be
        # returned by a signal_family-filtered read even though it
        # would be returned by an unfiltered read.
        ws.publish(_thought(agent="bachira_meguru", tick=1, read=None))
        snap = ws.snapshot(as_of=T0 + timedelta(minutes=1), current_tick=2)

        unfiltered = snap.read_for(agent_id="itoshi_rin")
        assert len(unfiltered) == 2

        filtered = snap.read_for(agent_id="itoshi_rin", signal_family="metavision")
        assert len(filtered) == 1
        assert filtered[0].agent_id == "isagi_yoichi"

    def test_peer_thoughts_signal_family_filter(self):
        ws = ReasoningWorkspace()
        # Rin's own past metavision-flavoured thought should NOT come
        # back from peer_thoughts even with the family filter.
        ws.publish(_thought(
            agent="itoshi_rin", tick=1,
            read=ThoughtRead(signal_family="precision", direction_bias="long"),
        ))
        ws.publish(_thought(
            agent="isagi_yoichi", tick=1,
            read=ThoughtRead(signal_family="metavision", direction_bias="long"),
        ))
        snap = ws.snapshot(as_of=T0 + timedelta(minutes=1), current_tick=2)
        peers = snap.peer_thoughts(agent_id="itoshi_rin", signal_family="metavision")
        assert len(peers) == 1
        assert peers[0].agent_id == "isagi_yoichi"


class TestF22aSemantic_RinCanNowDistinguishSignalFamilies:
    """Semantic guarantee: pre-F22a, Rin's Phase T-evolve peer scan
    could only see peer *direction*. If Bachira's pattern-rebel and
    Isagi's metavision both said "long", Rin couldn't tell them apart.
    Post-F22a, ``signal_family="metavision"`` on ``peer_thoughts()``
    narrows to Isagi cleanly.
    """

    def test_metavision_and_rebel_same_direction_are_now_distinguishable(self):
        ws = ReasoningWorkspace()
        ws.publish(_thought(
            agent="isagi_yoichi", tick=1, symbol="EURUSD",
            read=ThoughtRead(
                signal_family="metavision",
                direction_bias="long",
                regime_read="trending",
                driving_evidence=("zone_d1_against",),
            ),
        ))
        ws.publish(_thought(
            agent="bachira_meguru", tick=1, symbol="EURUSD",
            read=ThoughtRead(
                signal_family="pattern_rebel",
                direction_bias="long",  # same direction
                regime_read="rebel_lift",
                driving_evidence=("bachira_rebel_baseline_zone",),
            ),
        ))
        snap = ws.snapshot(as_of=T0 + timedelta(minutes=1), current_tick=2)

        all_long_peers = [
            t for t in snap.peer_thoughts(agent_id="itoshi_rin", symbol="EURUSD")
            if t.read is not None and t.read.direction_bias == "long"
        ]
        assert len(all_long_peers) == 2  # direction-only view: indistinguishable

        metavision_peers = snap.peer_thoughts(
            agent_id="itoshi_rin", symbol="EURUSD", signal_family="metavision",
        )
        assert len(metavision_peers) == 1
        assert metavision_peers[0].agent_id == "isagi_yoichi"

        rebel_peers = snap.peer_thoughts(
            agent_id="itoshi_rin", symbol="EURUSD", signal_family="pattern_rebel",
        )
        assert len(rebel_peers) == 1
        assert rebel_peers[0].agent_id == "bachira_meguru"


class TestPipHelpers:
    def test_pip_size_for_major(self):
        assert pip_size_for("EURUSD") == 1e-4
        assert pip_size_for("GBPUSD") == 1e-4
        assert pip_size_for("USDCAD") == 1e-4

    def test_pip_size_for_jpy(self):
        assert pip_size_for("USDJPY") == 1e-2
        assert pip_size_for("EURJPY") == 1e-2

    def test_stop_pips_from_prices_major(self):
        # 20-pip stop on EURUSD at 1.0800 -> 1.0780
        assert abs(stop_pips_from_prices("EURUSD", 1.0800, 1.0780) - 20.0) < 1e-6
        assert abs(stop_pips_from_prices("EURUSD", 1.0800, 1.0820) - 20.0) < 1e-6

    def test_stop_pips_from_prices_jpy(self):
        # 20-pip stop on USDJPY at 150.00 -> 149.80
        assert abs(stop_pips_from_prices("USDJPY", 150.00, 149.80) - 20.0) < 1e-6

    def test_stop_pips_none_on_missing_inputs(self):
        assert stop_pips_from_prices("EURUSD", None, 1.0) is None  # type: ignore[arg-type]
        assert stop_pips_from_prices("EURUSD", 1.0, None) is None  # type: ignore[arg-type]

    def test_expected_r_r15(self):
        # entry 1.0800, stop 1.0780 (20 pips risk), tp 1.0830 (30 pips reward) -> 1.5R
        assert abs(expected_r_from_prices(1.0800, 1.0780, 1.0830) - 1.5) < 1e-9

    def test_expected_r_none_on_zero_risk(self):
        assert expected_r_from_prices(1.0800, 1.0800, 1.0830) is None
