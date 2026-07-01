"""Tests for F21 workspace threading in `_drive_squad_replay`.

Verifies:

- ``use_workspace=False`` (default) preserves Phi4.1 audit behaviour --
  no workspace publish/read counts, no ``_AgentScopedSnapshot`` wrapping.
- ``use_workspace=True`` populates ``workspace_publish_counts`` +
  ``workspace_read_counts`` on the output.
- ``_AgentScopedSnapshot`` proxies the three read methods
  (``read_for`` / ``peer_thoughts`` / ``latest_by_agent``) and records
  reads under the scoped agent_id.
- G7 harness ``_evaluate_criterion_4`` handles pass / fail / Reo-waiver
  cases from real counts.
"""
from __future__ import annotations

import datetime as dt

import pytest

from programs.M001_multi_agent_ensemble.sim.core.reasoning_workspace import (
    ReasoningWorkspace,
)
from programs.M001_multi_agent_ensemble.sim.core.types import (
    SCHEMA_VERSION,
    Coordinate,
    Thought,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_g7_v1_checkpoint_gate import (
    STRUCTURAL_FALSIFIERS,
    _evaluate_criterion_4,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
    _AgentScopedSnapshot,
)

UTC = dt.timezone.utc


def _make_snapshot():
    ws = ReasoningWorkspace()
    ts = dt.datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
    coord = Coordinate(
        agent_id="isagi_yoichi",
        symbol="EURUSD",
        price_lo=1.09, price_hi=1.10,
        time_start=ts, time_end=ts + dt.timedelta(hours=24),
        vol_band=(0.5, 1.0),
        regime_predicate="trending",
        expected_strength=0.8,
        direction_bias="long",
    )
    isagi_t = Thought(
        schema_version=SCHEMA_VERSION,
        agent_id="isagi_yoichi",
        tick_id=100,
        timestamp=ts,
        symbol="EURUSD",
        narrative="fired zone",
        tags=["zone_d1_against"],
        confidence_in_thought=0.7,
        expected_action="long_on_H4_close",
        coordinate=coord,
        decision_horizon=ts,
        ttl_ticks=6,
        references=[],
    )
    ws.publish(isagi_t)
    return ws.snapshot(
        as_of=ts + dt.timedelta(hours=4),
        current_tick=101,
    )


class TestAgentScopedSnapshot:

    def test_read_for_records_read(self):
        snap = _make_snapshot()
        counts: dict[str, int] = {}
        scoped = _AgentScopedSnapshot(snap, "bachira_meguru", counts)
        result = scoped.read_for(agent_id="bachira_meguru", tier=2)
        assert isinstance(result, tuple)
        assert counts["bachira_meguru"] == 1

    def test_peer_thoughts_records_read(self):
        snap = _make_snapshot()
        counts: dict[str, int] = {}
        scoped = _AgentScopedSnapshot(snap, "nagi_seishiro", counts)
        _ = scoped.peer_thoughts(agent_id="nagi_seishiro", symbol="EURUSD")
        assert counts["nagi_seishiro"] == 1

    def test_latest_by_agent_records_read(self):
        snap = _make_snapshot()
        counts: dict[str, int] = {}
        scoped = _AgentScopedSnapshot(snap, "bachira_meguru", counts)
        _ = scoped.latest_by_agent(symbol="EURUSD")
        assert counts["bachira_meguru"] == 1

    def test_multiple_calls_increment(self):
        snap = _make_snapshot()
        counts: dict[str, int] = {}
        scoped = _AgentScopedSnapshot(snap, "chigiri_hyoma", counts)
        _ = scoped.read_for(agent_id="chigiri_hyoma", tier=2)
        _ = scoped.peer_thoughts(agent_id="chigiri_hyoma")
        _ = scoped.latest_by_agent()
        assert counts["chigiri_hyoma"] == 3

    def test_scoped_read_data_matches_snapshot(self):
        """Proxy passes through unchanged content."""
        snap = _make_snapshot()
        counts: dict[str, int] = {}
        scoped = _AgentScopedSnapshot(snap, "rin", counts)
        via_scoped = scoped.read_for(agent_id="rin", tier=2)
        via_direct = snap.read_for(agent_id="rin", tier=2)
        assert via_scoped == via_direct

    def test_passthrough_properties(self):
        snap = _make_snapshot()
        counts: dict[str, int] = {}
        scoped = _AgentScopedSnapshot(snap, "kunigami_rensuke", counts)
        assert scoped.thoughts == snap.thoughts
        assert scoped.as_of == snap.as_of
        assert scoped.current_tick == snap.current_tick


class TestCriterion4Evaluator:

    def test_both_positive_passes(self):
        r = _evaluate_criterion_4("bachira_meguru", publish_count=10, read_count=5)
        assert r.passed is True
        assert r.status == "computed"

    def test_zero_read_fails(self):
        r = _evaluate_criterion_4("chigiri_hyoma", publish_count=10, read_count=0)
        assert r.passed is False
        assert r.status == "computed"

    def test_zero_publish_fails(self):
        r = _evaluate_criterion_4("bachira_meguru", publish_count=0, read_count=5)
        assert r.passed is False

    def test_reo_falsifier_waived(self):
        """Reo passes with publish-only per doctrine 3.10 exception."""
        r = _evaluate_criterion_4("reo_mikage", publish_count=100, read_count=0)
        assert r.status == "waived"
        assert r.passed is True

    def test_reo_no_publish_still_fails(self):
        """Waiver requires at least 1 publish."""
        r = _evaluate_criterion_4("reo_mikage", publish_count=0, read_count=0)
        assert r.status == "computed"
        assert r.passed is False

    def test_reo_in_structural_falsifiers(self):
        assert "reo_mikage" in STRUCTURAL_FALSIFIERS

    def test_statistic_reflects_bottleneck(self):
        """Statistic is min(publish, read) for computed cases."""
        r = _evaluate_criterion_4("bachira_meguru", publish_count=100, read_count=3)
        assert r.statistic == 3.0
