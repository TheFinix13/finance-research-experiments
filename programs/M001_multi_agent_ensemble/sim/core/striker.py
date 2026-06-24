"""BlueLockStriker Protocol + BaseStriker abstract base class.

Doctrine `06-blue-lock-doctrine.md` section 4.1 — every agent observes
every tick (always emits a Thought) and intends only at home-TF close
(may emit an AgentProposal).

The Phi2.5 scaffold ships:

* The `BlueLockStriker` Protocol — the typed contract every roster
  agent satisfies.
* A `BaseStriker` ABC with a seed-derivation helper and a default
  KPI-reporter stub. Concrete agents live in `sim/agents/*.py`.

Agents stay pure: they never touch wall-clock time, never spawn
threads, never read globals.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

import numpy as np

from .ledger import ThoughtLedger
from .seed import seed, seed_for
from .types import AgentProposal, CanonRole, MarketState, Symbol, Thought


class BlueLockStriker(Protocol):
    """The contract every roster agent implements.

    Required attributes:

    * ``agent_id`` — globally unique string id (matches roster YAML).
    * ``canon_role`` — fixed identity layer (doctrine 3.10).
    * ``home_tf`` — primary cadence for ``intend``.
    * ``symbols`` — whitelist of tradable symbols for this agent.
    """

    agent_id: str
    canon_role: CanonRole
    home_tf: str
    symbols: list[Symbol]

    def observe(self, market: MarketState, ledger: ThoughtLedger) -> Thought:
        """Called every tick. Always returns a Thought; never returns None."""
        ...

    def intend(
        self,
        market: MarketState,
        my_recent_thought: Thought,
    ) -> AgentProposal | None:
        """Called only at ``home_tf`` close. May return a Proposal or None."""
        ...

    def report_kpis(self, week_id: str) -> dict:
        """Default-implementable in `BaseStriker`."""
        ...


class BaseStriker(ABC):
    """Abstract base class with deterministic helpers.

    Subclasses must implement ``observe`` and ``intend``. Default
    ``report_kpis`` reads from the per-agent journal (Phi2.5 returns
    a placeholder dict; full implementation lands in Phi3+).
    """

    agent_id: str
    canon_role: CanonRole
    home_tf: str
    symbols: list[Symbol]

    def __init__(
        self,
        agent_id: str,
        canon_role: CanonRole,
        home_tf: str,
        symbols: list[Symbol],
    ) -> None:
        self.agent_id = agent_id
        self.canon_role = canon_role
        self.home_tf = home_tf
        self.symbols = list(symbols)

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
