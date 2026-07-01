"""Arm 5 of the Phi5 aggregator experiment -- combined stacking (1+2+3+4).

Locked order of operations from ``experiments/phi5_aggregator/PROTOCOL.md``
§3.6:

    TQS-floor (Arm 2) filters the proposal pool first
        -> same-direction merge (Arm 3) collapses surviving same-direction
           proposals into one merged proposal per symbol-direction
            -> multi-position policy (Arm 4) admits up to K=2 distinct
               merged proposals per symbol subject to R6
                -> HRP (Arm 1) sets the risk weight for each admitted
                   proposal

This is the headline arm -- if it dominates the isolated arms, the
combination is validated as the Phi5 aggregator. If it underperforms
its components, that's an interaction finding (destructive stacking),
still a scientifically valid outcome.

Reference: `experiments/phi5_aggregator/PROTOCOL.md` §3.6.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from ..types import AgentProposal
from .hrp import HRPAggregator, HRPWeightSnapshot
from .multi_position import (
    Arm4Decision,
    MultiPositionAggregator,
    OpenPosition,
)
from .same_direction_merge import apply_same_direction_merge
from .tqs_floor import TQSFloorAggregator, TQSFloorDecision


@dataclass(frozen=True)
class CombinedDecision:
    """Per-proposal audit trail across all four stacked arms."""

    proposal: AgentProposal
    admitted: bool
    stage: str          # "tqs_floor" | "merge" | "multi_position" | "hrp" | "admitted"
    reason: str
    hrp_weight: float | None
    tqs_floor_decision: TQSFloorDecision | None = None
    multi_position_decision: Arm4Decision | None = None


@dataclass
class CombinedAggregator:
    """Stateful adapter for Arm 5 stacking.

    The harness (Phase 6c) constructs this once per OOS window with:
    - a pre-fitted `HRPAggregator` (refits at window boundaries)
    - a `TQSFloorAggregator` (accumulates conviction history across windows)
    - a `MultiPositionAggregator` (tracks open positions across ticks)

    Per tick, the harness calls ``process`` with the tick's proposal set;
    the return is the admitted set plus a decisions list for the audit
    log.
    """

    tqs_floor: TQSFloorAggregator
    multi_position: MultiPositionAggregator
    hrp: HRPAggregator
    decisions_history: list[list[CombinedDecision]] = field(default_factory=list)

    def process(
        self,
        proposals: Iterable[AgentProposal],
        *,
        tick_id: int,
    ) -> tuple[list[AgentProposal], list[CombinedDecision]]:
        proposals = list(proposals)
        decisions: list[CombinedDecision] = []

        # Stage 1: TQS floor (Arm 2).
        after_floor, floor_decisions = self.tqs_floor.filter(proposals)
        floor_by_proposal = {id(d.proposal): d for d in floor_decisions}
        for prop in proposals:
            d = floor_by_proposal.get(id(prop))
            if d is not None and not d.admitted:
                decisions.append(CombinedDecision(
                    proposal=prop, admitted=False,
                    stage="tqs_floor",
                    reason=d.reason,
                    hrp_weight=None,
                    tqs_floor_decision=d,
                ))

        # Stage 2: same-direction merge (Arm 3).
        # Merge collapses N-same-direction proposals into 1. The merged
        # proposal carries a synthetic agent_id ("arm3_merged_<agents>").
        merged = apply_same_direction_merge(after_floor, tick_id=tick_id)

        # Stage 3: multi-position admission (Arm 4).
        admitted_arm4, arm4_decisions = self.multi_position.admit(merged)
        arm4_by_id = {id(d.proposal): d for d in arm4_decisions}
        for m in merged:
            d = arm4_by_id.get(id(m))
            if d is not None and not d.admitted:
                decisions.append(CombinedDecision(
                    proposal=m, admitted=False,
                    stage="multi_position",
                    reason=d.reason,
                    hrp_weight=None,
                    multi_position_decision=d,
                ))

        # Stage 4: HRP weight assignment (Arm 1).
        # For merged proposals, the weight comes from the max-conviction
        # contributor's underlying agent. Since merged agent_id starts
        # with "arm3_merged_", we peel it back to the contributing agents
        # via rationale and take the AVERAGE HRP weight across contributors
        # (a defensible convention -- alternative would be the winner's
        # weight; the average preserves each contributor's marginal
        # influence).
        final_admitted: list[AgentProposal] = []
        for prop in admitted_arm4:
            weight = self._resolve_hrp_weight(prop)
            if weight <= 0:
                decisions.append(CombinedDecision(
                    proposal=prop, admitted=False,
                    stage="hrp",
                    reason="hrp_weight_zero",
                    hrp_weight=weight,
                ))
                continue
            final_admitted.append(prop)
            decisions.append(CombinedDecision(
                proposal=prop, admitted=True,
                stage="admitted",
                reason="admitted",
                hrp_weight=weight,
            ))

        self.decisions_history.append(decisions)
        return final_admitted, decisions

    def _resolve_hrp_weight(self, prop: AgentProposal) -> float:
        """Map a (possibly Arm-3-merged) proposal to an HRP weight.

        - Native (non-merged) proposals -> hrp.get_weight(agent_id).
        - Arm-3-merged proposals -> mean HRP weight of contributors from
          ``rationale["arm3_contributing_agents"]``.
        """
        if not self.hrp.has_snapshot:
            return 1.0    # pre-refit -> pass-through (fallback)
        if prop.agent_id.startswith("arm3_merged_"):
            contribs = prop.rationale.get("arm3_contributing_agents", [])
            if not contribs:
                return 0.0
            weights = [self.hrp.get_weight(a) for a in contribs]
            positive = [w for w in weights if w > 0]
            if not positive:
                return 0.0
            return sum(positive) / len(positive)
        return self.hrp.get_weight(prop.agent_id)
