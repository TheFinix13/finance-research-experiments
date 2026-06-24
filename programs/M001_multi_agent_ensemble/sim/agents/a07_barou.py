"""A7 — Shoei Barou (`barou_shoei`) — Phi2.5 skeleton.

Barou is the single-pair-locked control agent (USDCAD per roster §3.7).
By design he does NOT participate in chemical reactions — his role is
the apples-to-apples "lone wolf vs squad" baseline (doctrine §1.10 +
roster §3.7).

Phi3 wires Barou's H4 trend-continuation logic on USDCAD; Phi2.5 ships
the observation-only stub.
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


class BarouShoei(BaseStriker):
    """Single-pair specialist (USDCAD only by design).

    The roster YAML restricts `symbols` to `["USDCAD"]` — this stub
    enforces that contract by emitting only when the bar's symbol is
    in `self.symbols`.
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
                f"[barou] {market.symbol} {market.timeframe} — lone-wolf "
                "control; will NOT participate in chemical reactions. Apples-"
                "to-apples baseline for the fusion mechanism."
            ),
            tags=[
                "phi2_placeholder",
                "lone_wolf",
                "no_fusion",
                "canon:barou",
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
        return None
