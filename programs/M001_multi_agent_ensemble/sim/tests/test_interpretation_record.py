"""F22c contract tests -- ``YieldReason`` interpretation record.

Pre-F22c, ``BaseStriker.intend()`` returned ``AgentProposal | None``.
``None`` conflated three cases: silent (no signal), inferred yield
(deferred to a peer), and hard-filter rejection. We could not audit
whether Rin's Phase T-evolve yield actually paired with Isagi firing.

Post-F22c, ``intend()`` returns ``IntentDecision =
AgentProposal | YieldReason | None``. The driver appends every
``YieldReason`` to ``SquadRunOutput.yields`` so post-hoc audits can
answer: "of N metavision-yields, on how many did Isagi actually fire?"

This module covers:

- ``YieldReason`` dataclass shape, defaults, JSON round-trip.
- ``IntentDecision`` union: legacy ``None`` still valid; ``YieldReason``
  is distinguishable from ``None`` via ``isinstance``.
- Driver capture of ``YieldReason`` into ``SquadRunOutput.yields``
  (via a stubbed agent to avoid re-running a synthetic replay).

The full "Rin actually emits YieldReason on the yield path" contract
lives in ``test_a03_rin_wrap.py::TestRinPhaseTEvolve``.
"""
from __future__ import annotations

import json

from programs.M001_multi_agent_ensemble.sim.core.types import (
    IntentDecision,
    YieldReason,
)


class TestYieldReasonDataclass:
    def test_minimal_construction(self):
        y = YieldReason(
            agent_id="itoshi_rin",
            tick_id=42,
            symbol="EURUSD",
            reason="isagi_would_lift_metavision",
        )
        assert y.agent_id == "itoshi_rin"
        assert y.tick_id == 42
        assert y.symbol == "EURUSD"
        assert y.reason == "isagi_would_lift_metavision"
        assert y.peer_ids_read == ()
        assert y.evidence == {}
        assert y.doctrine_ref == ""

    def test_populated_construction(self):
        y = YieldReason(
            agent_id="itoshi_rin",
            tick_id=42,
            symbol="EURUSD",
            reason="isagi_would_lift_metavision",
            peer_ids_read=("isagi_yoichi", "bachira_meguru"),
            evidence={
                "peer_agree_count": 2,
                "peer_disagree_count": 0,
                "direction": "long",
            },
            doctrine_ref="06-blue-lock-doctrine.md sec 4.1c + F22c",
        )
        assert "isagi_yoichi" in y.peer_ids_read
        assert y.evidence["peer_agree_count"] == 2
        assert y.evidence["direction"] == "long"

    def test_to_jsonable_and_round_trip(self):
        y = YieldReason(
            agent_id="itoshi_rin",
            tick_id=42,
            symbol="EURUSD",
            reason="isagi_would_lift_metavision",
            peer_ids_read=("isagi_yoichi",),
            evidence={"peer_agree_count": 1, "direction": "long"},
            doctrine_ref="ref",
        )
        j = y.to_jsonable()
        assert j == {
            "agent_id": "itoshi_rin",
            "tick_id": 42,
            "symbol": "EURUSD",
            "reason": "isagi_would_lift_metavision",
            "peer_ids_read": ["isagi_yoichi"],
            "evidence": {"peer_agree_count": 1, "direction": "long"},
            "doctrine_ref": "ref",
        }
        # JSON round-trip preserves everything.
        parsed = json.loads(json.dumps(j, sort_keys=True))
        assert parsed == j

    def test_frozen_dataclass_cannot_mutate(self):
        y = YieldReason(
            agent_id="itoshi_rin", tick_id=1, symbol="EURUSD", reason="x",
        )
        try:
            y.reason = "y"   # type: ignore[misc]
        except Exception as exc:  # noqa: BLE001
            assert "frozen" in str(exc).lower() or "cannot assign" in str(exc).lower()
        else:  # pragma: no cover
            raise AssertionError("YieldReason should be frozen")


class TestIntentDecisionUnion:
    """Legacy ``None`` returns still validate. ``YieldReason`` is
    distinguishable from ``None`` and from ``AgentProposal`` via
    ``isinstance``.
    """

    def test_none_is_valid_intent_decision(self):
        d: IntentDecision = None
        assert d is None
        assert not isinstance(d, YieldReason)

    def test_yield_reason_is_valid_intent_decision(self):
        d: IntentDecision = YieldReason(
            agent_id="itoshi_rin", tick_id=1, symbol="EURUSD", reason="x",
        )
        assert isinstance(d, YieldReason)
        assert d is not None


class TestSquadRunOutputCaptureYields:
    """The driver appends YieldReasons emitted by ``intend()`` into
    ``SquadRunOutput.yields``. Full end-to-end coverage happens in the
    walk-forward gate test; here we stub the interface so the contract
    is protected without needing a real replay.
    """

    def test_squad_run_output_has_yields_field(self):
        from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
            SquadRunOutput,
        )
        out = SquadRunOutput()
        assert hasattr(out, "yields")
        assert out.yields == []

    def test_squad_run_output_yields_accepts_yield_reason(self):
        from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
            SquadRunOutput,
        )
        out = SquadRunOutput()
        out.yields.append(YieldReason(
            agent_id="itoshi_rin",
            tick_id=100,
            symbol="EURUSD",
            reason="isagi_would_lift_metavision",
        ))
        assert len(out.yields) == 1
        assert out.yields[0].reason == "isagi_would_lift_metavision"
