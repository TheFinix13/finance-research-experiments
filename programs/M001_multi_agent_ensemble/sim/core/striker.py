"""BlueLockStriker Protocol + BaseStriker abstract base class.

Doctrine `06-blue-lock-doctrine.md` section 4.1 + section 4.1a. Every
agent observes every tick (always emits a Thought), intends only at
home-TF close (may emit an AgentProposal), owns its own lot-size
cognition (F19), owns its own SL/TP-shape cognition (F20), and
participates in the shared reasoning workspace (F21).

The Phi2.5 scaffold ships:

* The `BlueLockStriker` Protocol — the typed contract every roster
  agent satisfies, extended 2026-07-01 with F19 / F20 / F21.
* A `BaseStriker` ABC with a seed-derivation helper, a default
  KPI-reporter stub, and default `lot_intent` / `risk_intent` /
  `read_workspace` implementations that dispatch on the agent's
  ``playstyle`` attribute. Concrete agents live in `sim/agents/*.py`
  and typically override only `observe` + `intend` + set their
  `playstyle` in `__init__`.

Agents stay pure: they never touch wall-clock time, never spawn
threads, never read globals.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Literal, Protocol

import numpy as np

from .ledger import ThoughtLedger
from .lot_intent import (
    Playstyle,
    default_lot_intent,
    playstyle_lot_intent,
)
from .reasoning_workspace import Tier, WorkspaceSnapshot
from .risk_intent import (
    default_risk_intent,
    playstyle_risk_intent,
)
from .seed import seed, seed_for
from .types import AgentProposal, CanonRole, MarketState, Symbol, Thought


class BlueLockStriker(Protocol):
    """The contract every roster agent implements.

    Required attributes:

    * ``agent_id`` — globally unique string id (matches roster YAML).
    * ``canon_role`` — fixed identity layer (doctrine 3.10).
    * ``home_tf`` — primary cadence for ``intend``.
    * ``symbols`` — whitelist of tradable symbols for this agent.
    * ``playstyle`` — F19/F20 dispatch key (doctrine 4.1a); "unknown"
      means the agent has not yet reached v1 checkpoint and falls back
      to the fixed-lot / 40-pip default.
    * ``tier`` — information tier (1, 2, or 3) per doctrine 3.9. Set
      empirically by F17 ΔInfo measurement; defaults to Tier-2 for v0.
    """

    agent_id: str
    canon_role: CanonRole
    home_tf: str
    symbols: list[Symbol]
    playstyle: Playstyle | str
    tier: Tier

    def observe(self, market: MarketState, ledger: ThoughtLedger) -> Thought:
        """Called every tick. Always returns a Thought; never returns None."""
        ...

    def intend(
        self,
        market: MarketState,
        my_recent_thought: Thought,
        *,
        workspace: WorkspaceSnapshot | None = None,
    ) -> AgentProposal | None:
        """Called only at ``home_tf`` close. May return a Proposal or None.

        ``workspace`` is the F21 reasoning-workspace snapshot at the tick
        barrier -- carries every peer Thought visible under the doctrine
        3.8 look-ahead guards (tick_id < current_tick, timestamp <=
        bar.as_of). Optional for backwards compatibility with agents
        that don't consume peer thoughts yet; the harness always
        supplies it when calling ``intend`` from Phase 2 of
        ``run_replay``.
        """
        ...

    def lot_intent(
        self,
        conviction: float,
        sl_pips: float,
        equity: float,
        regime_fit: float,
    ) -> float:
        """F19 -- agent-owned position sizing. Default in ``BaseStriker``
        dispatches on ``playstyle``. Override for weapon-specific logic
        (e.g. Reo's HRP-mixture computation before dispatch)."""
        ...

    def risk_intent(
        self,
        conviction: float,
        atr_pips: float,
        h1_swing_pips: float,
    ) -> tuple[float, list[float]]:
        """F20 -- agent-owned SL/TP-shape cognition. Default in
        ``BaseStriker`` dispatches on ``playstyle``. Override for
        weapon-specific logic (e.g. Bachira's peer-silence-gated
        SL tightening)."""
        ...

    def read_workspace(
        self,
        workspace: WorkspaceSnapshot,
        as_of: datetime,
    ) -> tuple[Thought, ...]:
        """F21 -- read peer Thoughts from the reasoning workspace.
        Default in ``BaseStriker`` returns the tier-appropriate view of
        the whole snapshot. Override for agent-specific filters
        (Isagi reads confluence tags; Bachira reads TF-adaptation
        signals; Reo reads all for HRP mixture)."""
        ...

    def report_kpis(self, week_id: str) -> dict:
        """Default-implementable in `BaseStriker`."""
        ...


class BaseStriker(ABC):
    """Abstract base class with deterministic helpers.

    Subclasses must implement ``observe`` and ``intend``. Default
    ``report_kpis`` reads from the per-agent journal (Phi2.5 returns
    a placeholder dict; full implementation lands in Phi3+).

    F19 / F20 / F21 (doctrine 4.1a, added 2026-07-01) have default
    playstyle-dispatched implementations here; subclasses need only
    set ``self.playstyle = "conservative_metavision"`` (or similar
    from the doctrine's playstyle mapping) in ``__init__``.
    """

    agent_id: str
    canon_role: CanonRole
    home_tf: str
    symbols: list[Symbol]
    playstyle: Playstyle | str
    tier: Tier

    def __init__(
        self,
        agent_id: str,
        canon_role: CanonRole,
        home_tf: str,
        symbols: list[Symbol],
        *,
        playstyle: Playstyle | str = "unknown",
        tier: Tier = 2,
    ) -> None:
        self.agent_id = agent_id
        self.canon_role = canon_role
        self.home_tf = home_tf
        self.symbols = list(symbols)
        self.playstyle = playstyle
        self.tier = tier

    # ------------------------------------------------------------------
    # Determinism helpers
    # ------------------------------------------------------------------

    def rng(self, tick_id: int, channel: str = "default") -> np.random.Generator:
        """Return a numpy Generator seeded by `(agent_id, tick_id, channel)`.

        Use this for any randomness in the decision path. Hard rule
        (09 section 1.2): no `random.random()`, no `time.time()`.
        """
        return np.random.default_rng(seed_for(self.agent_id, tick_id, channel))

    def base_seed(self, tick_id: int) -> int:
        return seed(self.agent_id, tick_id)

    # ------------------------------------------------------------------
    # Required overrides
    # ------------------------------------------------------------------

    @abstractmethod
    def observe(self, market: MarketState, ledger: ThoughtLedger) -> Thought:
        raise NotImplementedError

    @abstractmethod
    def intend(
        self,
        market: MarketState,
        my_recent_thought: Thought,
    ) -> AgentProposal | None:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # F19 / F20 / F21 (doctrine 4.1a) -- default playstyle dispatch
    # ------------------------------------------------------------------

    def lot_intent(
        self,
        conviction: float,
        sl_pips: float,
        equity: float,
        regime_fit: float,
    ) -> float:
        """F19 default -- dispatches on ``self.playstyle``.

        Agents that need weapon-specific logic (e.g. Reo's HRP mixture
        before dispatch, Kunigami's 0.5x on warning-active, Bachira's
        rebel-lift-gate-blocking) override this method entirely.
        """
        if self.playstyle == "unknown":
            return default_lot_intent(conviction, sl_pips, equity, regime_fit)
        return playstyle_lot_intent(
            conviction, sl_pips, equity, regime_fit,
            playstyle=self.playstyle,   # type: ignore[arg-type]
        )

    def risk_intent(
        self,
        conviction: float,
        atr_pips: float,
        h1_swing_pips: float,
    ) -> tuple[float, list[float]]:
        """F20 default -- dispatches on ``self.playstyle``.

        Agents that need weapon-specific SL/TP shapes override entirely.
        """
        if self.playstyle == "unknown":
            return default_risk_intent(conviction, atr_pips, h1_swing_pips)
        return playstyle_risk_intent(
            conviction, atr_pips, h1_swing_pips,
            playstyle=self.playstyle,   # type: ignore[arg-type]
        )

    def read_workspace(
        self,
        workspace: WorkspaceSnapshot,
        as_of: datetime,      # noqa: ARG002 -- interface signature; snapshot already scoped
    ) -> tuple[Thought, ...]:
        """F21 default -- returns the tier-appropriate peer view.

        Tier-1 / Tier-2 agents get the full backwards-only slice (own
        + peers); Tier-3 agents get only their own past Thoughts.

        Agents override this to add symbol / tag filters (Isagi reads
        confluence-tagged Thoughts; Bachira reads TF-adaptation
        signals; Reo reads all for HRP-mixture computation).
        """
        return workspace.read_for(
            agent_id=self.agent_id,
            tier=self.tier,
        )

    # ------------------------------------------------------------------
    # Default implementations
    # ------------------------------------------------------------------

    def report_kpis(self, week_id: str) -> dict:
        return {
            "agent_id": self.agent_id,
            "week_id": week_id,
            "assertion_rate": None,
            "coexistence_rate": None,
            "devour_rate": None,
            "goal_rate": None,
            "beauty_rate": None,
            "_status": "phi2.5_placeholder",
        }
