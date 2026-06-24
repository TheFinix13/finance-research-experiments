"""A1 — Yoichi Isagi (`isagi_yoichi`) — Phi2.5 skeleton.

The production `zone_d1_against` detector lives in the **production
repo** at
`~/Documents/GitHub/multi-pair-trading-agent/agent/alphas/concepts/zone_alpha.py`
and is NOT modified by this scaffold. Phi3 wraps the production cell
into Isagi v1 via a cross-repo import (PYTHONPATH=../multi-pair-trading-agent).

This file is intentionally a stub: it inherits `BaseStriker`, emits an
observation-only Thought every tick, and returns None from `intend`.
Once the cross-repo import lands, the v1 `intend` implementation
becomes a thin adapter around `SupplyDemandAlpha.emit_proposal` from
the production repo.

Documented expected PYTHONPATH for Phi3 import (sim/README.md):

    PYTHONPATH=../multi-pair-trading-agent:.

If the production repo is not on PYTHONPATH, this stub falls back to
observation-only Thoughts so the protocol end-to-end test still
passes.
"""
from __future__ import annotations

import importlib

from programs.M001_multi_agent_ensemble.sim.core.ledger import ThoughtLedger
from programs.M001_multi_agent_ensemble.sim.core.striker import BaseStriker
from programs.M001_multi_agent_ensemble.sim.core.types import (
    SCHEMA_VERSION,
    AgentProposal,
    CanonRole,
    MarketState,
    Thought,
)


# Phi2.5 keeps this as a function-level lazy import so the scaffold
# doesn't crash if the production repo isn't on PYTHONPATH. Phi3 makes
# this a hard requirement and lands the proposal-adapter.
def _try_production_zone_alpha():
    try:
        return importlib.import_module("agent.alphas.concepts.zone_alpha")
    except Exception:
        return None


class IsagiYoichi(BaseStriker):
    """Isagi v1 — wraps the production `zone_d1_against` cell.

    Phi2.5 scope: observation-only stub. Phi3 implements `intend` as
    a thin adapter over the production cell's proposal output.
    """

    def __init__(
        self,
        agent_id: str,
        canon_role: CanonRole,
        home_tf: str,
        symbols: list[str],
    ) -> None:
        super().__init__(agent_id, canon_role, home_tf, symbols)
        self._production_module = _try_production_zone_alpha()

    @property
    def has_production_link(self) -> bool:
        return self._production_module is not None

    def observe(self, market: MarketState, ledger: ThoughtLedger) -> Thought:
        # Tier-3 read by default (Phi2.5 — own thoughts only).
        peers = ledger.read(
            as_of=market.as_of,
            current_tick=market.tick_id,
            symbol=market.symbol,
        )
        peer_count = len(peers)
        link_note = "production zone_alpha import OK" if self.has_production_link \
            else "production zone_alpha not on PYTHONPATH (Phi3 wires this)"
        return Thought(
            schema_version=SCHEMA_VERSION,
            agent_id=self.agent_id,
            tick_id=market.tick_id,
            timestamp=market.as_of,
            symbol=market.symbol,
            narrative=(
                f"[isagi v1] H1 close on {market.symbol}; metavision seed "
                f"= zone_d1_against detector. {link_note}. "
                f"{peer_count} prior-tick peer thoughts in window."
            ),
            tags=[
                "phi2_placeholder",
                "zone_d1_against",
                "metavision_v1",
                f"canon:isagi",
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
        # Phi3 lands the proposal-adapter; Phi2.5 never intends.
        # See sim/README.md `Phi3 build order` for the wiring contract.
        return None
