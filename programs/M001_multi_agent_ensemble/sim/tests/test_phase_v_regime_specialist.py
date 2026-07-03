"""Phase V-a/V-b -- aggregator plumbing regression tests.

Pre-Phase-V, a tier-2 agent's proposal always ran through
``_tier_adjusted_conviction`` with a -TIER_BIAS penalty. Isagi (tier-1)
therefore won every same-base-conviction tiebreak.

**Phase V null result (2026-07-02) -- see G7 PROTOCOL sec 11.9-postmortem.**
The rationale-driven tier promotion was implemented and empirically
tested via ``walk-forward-post-V``:

- Chigiri delta moved from +0.049 -> +0.051 (WORSE by +0.002).
  Only 1 of 992 shadow trades flipped, and it flipped to a worse
  trade.
- Barou delta unchanged at +0.015. Zero ticks flipped.

Root cause: the raw conviction gap between Chigiri/Barou (~0.70-0.85)
and Isagi (~0.85-1.00) exceeds the TIER_BIAS penalty that the tier
promotion neutralises. Promoting Chigiri/Barou to effective tier-1
does not tip the aggregator sort because they're still below Isagi
on raw conviction. The mechanic was reverted (agents no longer stamp
``_effective_tier=1``) but the aggregator plumbing is retained
because:

1. It is regime-neutral: no side-effects unless a proposal actively
   stamps the rationale key.
2. A future Phase V-iterate (e.g. per-tick conviction lift, or a
   symbol-conditional slot reservation) may need this plumbing.
3. The tests here document the intended semantics of the helper.

This module therefore covers only the AGGREGATOR-side behaviour of
``_effective_tier`` (what happens IF a proposal stamps the key).
It does NOT assert that any agent currently stamps the key -- that
concern lives in ``test_a04_chigiri_wrap.py::TestPhaseVA`` and
``test_a07_barou_wrap.py::TestPhaseVB``, which now verify the
diagnostic-only (no-stamp) configuration.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from programs.M001_multi_agent_ensemble.sim.core.types import (
    AgentProposal,
    LadderRung,
)


def _proposal(
    *,
    agent_id: str,
    symbol: str = "EURUSD",
    direction: str = "long",
    conviction: float = 0.70,
    tick_id: int = 0,
    agent_tier: int = 2,
    effective_tier: int | None = None,
) -> AgentProposal:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rationale: dict[str, object] = {"stub": True}
    if effective_tier is not None:
        rationale["_effective_tier"] = effective_tier
    return AgentProposal(
        agent_id=agent_id, tick_id=tick_id,
        source_thought_id=f"{agent_id}:{tick_id}:{symbol}",
        timestamp=base, symbol=symbol, direction=direction,
        entry=1.1000, stop=1.0950,
        ladder=[LadderRung(price=1.1100, fraction=1.0)],
        conviction=conviction, regime_fit=0.5,
        valid_until=base + timedelta(hours=24),
        rationale=rationale,
        agent_tier=agent_tier,
    )


class TestEffectiveTierHelper:
    def test_default_matches_agent_tier(self):
        from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
            _effective_tier,
        )
        assert _effective_tier(_proposal(agent_id="a", agent_tier=1)) == 1
        assert _effective_tier(_proposal(agent_id="a", agent_tier=2)) == 2
        assert _effective_tier(_proposal(agent_id="a", agent_tier=3)) == 3

    def test_rationale_override_promotes_tier_2_to_tier_1(self):
        from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
            _effective_tier,
        )
        p = _proposal(agent_id="chigiri_hyoma", agent_tier=2, effective_tier=1)
        assert _effective_tier(p) == 1

    def test_rationale_override_never_demotes_tier_1(self):
        """A tier-1 agent (Isagi) cannot be demoted to tier-2 via a
        buggy rationale stamp -- the aggregator uses ``min(agent_tier,
        override)`` so anchors stay anchors.
        """
        from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
            _effective_tier,
        )
        p = _proposal(agent_id="isagi_yoichi", agent_tier=1, effective_tier=2)
        assert _effective_tier(p) == 1

    def test_malformed_override_falls_back_to_agent_tier(self):
        from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
            _effective_tier,
        )
        p = _proposal(agent_id="chigiri_hyoma", agent_tier=2)
        p.rationale["_effective_tier"] = "not_an_int"   # type: ignore[assignment]
        assert _effective_tier(p) == 2


class TestTierAdjustedConvictionWithSpecialistBit:
    def test_specialist_promotion_removes_tier_bias_penalty(self):
        from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
            TIER_BIAS,
            _tier_adjusted_conviction,
        )
        raw = 0.70
        # Non-specialist tier-2: conviction - TIER_BIAS.
        p_normal = _proposal(agent_id="chigiri_hyoma", agent_tier=2, conviction=raw)
        assert abs(_tier_adjusted_conviction(p_normal) - (raw - TIER_BIAS)) < 1e-9
        # Specialist tier-2: promoted to tier-1-equivalent; no penalty.
        p_specialist = _proposal(
            agent_id="chigiri_hyoma", agent_tier=2, conviction=raw,
            effective_tier=1,
        )
        assert abs(_tier_adjusted_conviction(p_specialist) - raw) < 1e-9


class TestSpecialistBeatsAnchorAtEqualConviction:
    """The core Phase V-a acceptance property: Chigiri's specialist
    proposal beats Isagi's proposal at IDENTICAL base conviction.
    Without the specialist bit, Chigiri would lose (Isagi's tier-1
    anchor bias wins). With the bit, they tie on adjusted conviction
    and the ``_effective_tier`` sort key breaks the tie in Chigiri's
    favour (lex tie-break on agent_id: "chigiri_hyoma" < "isagi_yoichi").
    """

    def test_chigiri_wins_when_specialist_bit_set(self):
        from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
            _phi4_aggregate,
        )
        isagi = _proposal(agent_id="isagi_yoichi", agent_tier=1, conviction=0.70)
        chigiri_spec = _proposal(
            agent_id="chigiri_hyoma", agent_tier=2, conviction=0.70,
            effective_tier=1,
        )
        out = _phi4_aggregate([isagi, chigiri_spec], tick_id=0)
        assert len(out.accepted) == 1
        assert out.accepted[0].agent_id == "chigiri_hyoma", (
            "Phase V-a: Chigiri's regime-specialist bit should let him win "
            "at equal base conviction on lex tie-break vs. Isagi"
        )

    def test_chigiri_loses_without_specialist_bit(self):
        from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
            _phi4_aggregate,
        )
        isagi = _proposal(agent_id="isagi_yoichi", agent_tier=1, conviction=0.70)
        chigiri_norm = _proposal(
            agent_id="chigiri_hyoma", agent_tier=2, conviction=0.70,
        )
        out = _phi4_aggregate([isagi, chigiri_norm], tick_id=0)
        assert out.accepted[0].agent_id == "isagi_yoichi", (
            "Pre-Phase-V baseline: Isagi wins the tie-break as tier-1 anchor"
        )

    def test_chigiri_specialist_still_loses_to_a_stronger_isagi(self):
        """Phase V-a is a tie-break helper, not a supercharger. If Isagi
        has meaningfully higher raw conviction, he still wins.
        """
        from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
            TIER_BIAS,
            _phi4_aggregate,
        )
        isagi_strong = _proposal(
            agent_id="isagi_yoichi", agent_tier=1,
            conviction=0.70 + TIER_BIAS + 0.01,  # comfortably above bias margin
        )
        chigiri_spec = _proposal(
            agent_id="chigiri_hyoma", agent_tier=2, conviction=0.70,
            effective_tier=1,
        )
        out = _phi4_aggregate([isagi_strong, chigiri_spec], tick_id=0)
        assert out.accepted[0].agent_id == "isagi_yoichi"
