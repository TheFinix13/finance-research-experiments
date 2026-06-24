"""Generic placeholder striker — observation-only.

Used by `sim/roster/full_canon.yaml` for the six benched agents
(Bachira, Rin, Chigiri, Reo, Yukimiya, Aoshi) whose real
implementations land in Phi3+.
"""
from __future__ import annotations

from programs.M001_multi_agent_ensemble.sim.core.ledger import ThoughtLedger
from programs.M001_multi_agent_ensemble.sim.core.striker import BaseStriker
from programs.M001_multi_agent_ensemble.sim.core.types import (
    SCHEMA_VERSION,
    AgentProposal,
    CanonRole,
    MarketState,
    Thought,
)


class PlaceholderAgent(BaseStriker):
    """Always emits an observation-only Thought; never intends.

    Tags carry the agent's canon-player identity for the dashboard so
    the league table renders all roster slots even before real logic
    lands.
    """

    def __init__(
        self,
        agent_id: str,
        canon_role: CanonRole,
        home_tf: str,
        symbols: list[str],
    ) -> None:
        super().__init__(agent_id, canon_role, home_tf, symbols)

    def observe(self, market: MarketState, ledger: ThoughtLedger) -> Thought:
        return Thought(
            schema_version=SCHEMA_VERSION,
            agent_id=self.agent_id,
            tick_id=market.tick_id,
            timestamp=market.as_of,
            symbol=market.symbol,
            narrative=(
                f"[{self.agent_id} placeholder] observation-only tick on "
                f"{market.symbol} {market.timeframe}; real strategy logic "
                "lands in Phi3"
            ),
            tags=[
                "phi2_placeholder",
                f"canon:{self.canon_role.canon_player.split()[0].lower()}",
            ],
            confidence_in_thought=0.0,
            expected_action="wait",
            coordinate=None,
            decision_horizon=market.as_of,
            ttl_ticks=1,
            references=[],
        )

    def intend(
        self,
        market: MarketState,
        my_recent_thought: Thought,
    ) -> AgentProposal | None:
        # Phi2.5: stubs never intend. Phi3+ overrides this.
        return None
