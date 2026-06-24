"""A10 — Rensuke Kunigami (`kunigami_rensuke`) — Phi2.5 skeleton.

Kunigami is the anti-tilt risk auxiliary (doctrine §4.2 distinction:
in-cast agent that dampens *the squad's own* enthusiasm after a loss
streak — distinct from the Sentinel's R5 outer multiplier).

He never emits a Coordinate; never trades long/short. His Thoughts
carry the current drawdown context and a recommended risk-scale that
the allocator may consume in Phi3+.
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


class KunigamiRensuke(BaseStriker):
    """Anti-tilt risk auxiliary (Phi3+ wires the dampening signal)."""

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
                f"[kunigami] monitoring equity / loss-streak state on "
                f"{market.symbol}; Phi3 will publish a risk-scale "
                "recommendation here based on rolling DD."
            ),
            tags=[
                "phi2_placeholder",
                "anti_tilt",
                "risk_auxiliary",
                "canon:kunigami",
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
        # Kunigami never produces a trade proposal — he only dampens.
        return None
