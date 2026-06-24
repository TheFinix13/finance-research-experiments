"""A6 — Seishiro Nagi (`nagi_seishiro`) — Phi2.5 skeleton.

Nagi is confluence-only — the lowest-frequency, highest-conviction-floor
agent (doctrine §3.6 + roster §3.6). His proposal triggers AND-gate on
multiple peer Thoughts; Phi3 wires this to F11's thought-resonance
trigger (foundations §F11 v0.4 extension).

The Phi2.5 stub emits an observation-only Thought per tick, tags it
with `confluence_seeker` so the chemical-reaction panel can render his
slot, and returns None from `intend`.
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


class NagiSeishiro(BaseStriker):
    """Confluence-only multi-signal AND gate (Phi3 implementation pending)."""

    def __init__(
        self,
        agent_id: str,
        canon_role: CanonRole,
        home_tf: str,
        symbols: list[str],
    ) -> None:
        super().__init__(agent_id, canon_role, home_tf, symbols)

    def observe(self, market: MarketState, ledger: ThoughtLedger) -> Thought:
        # Nagi reads peers (Phi3 will gate his proposal on >= N tag-resonant peers).
        peers = ledger.read(
            as_of=market.as_of,
            current_tick=market.tick_id,
            symbol=market.symbol,
        )
        n_high_confidence_peers = sum(
            1 for t in peers if t.confidence_in_thought >= 0.7
        )
        return Thought(
            schema_version=SCHEMA_VERSION,
            agent_id=self.agent_id,
            tick_id=market.tick_id,
            timestamp=market.as_of,
            symbol=market.symbol,
            narrative=(
                f"[nagi] watching {market.symbol} {market.timeframe}; "
                f"{n_high_confidence_peers} high-confidence peer thoughts "
                "in window. Will fire only on multi-signal confluence."
            ),
            tags=[
                "phi2_placeholder",
                "confluence_seeker",
                "canon:nagi",
            ],
            confidence_in_thought=0.0,
            expected_action="wait",
            coordinate=None,
            decision_horizon=market.as_of,
            ttl_ticks=1,
            references=[t.thought_id for t in peers[:3]],
        )

    def intend(
        self,
        market: MarketState,
        my_recent_thought: Thought,
    ) -> AgentProposal | None:
        return None
