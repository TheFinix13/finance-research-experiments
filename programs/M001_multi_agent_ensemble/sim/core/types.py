"""Typed objects shared by every agent and every kernel stage.

Schema is frozen at v1 for Phi2.5. Any breaking change bumps
`SCHEMA_VERSION` and lands an amendment in `09-experiment-architecture.md`.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

SCHEMA_VERSION = 1

# Type aliases used across the kernel.
Symbol = str
Timeframe = Literal["M1", "M5", "M15", "H1", "H4", "D1"]
Direction = Literal["long", "short", "flat", "either"]


def _iso(ts: datetime | str) -> str:
    if isinstance(ts, str):
        return ts
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.isoformat()


@dataclass(frozen=True)
class Coordinate:
    """Forward-looking claim of where + when an A+ setup will materialise.

    Doctrine 06 section 3.2. Embedded in `Thought.coordinate` (doctrine
    section 3.8); never emitted as a standalone artefact in v0.2+.
    """

    agent_id: str
    symbol: Symbol
    price_lo: float
    price_hi: float
    time_start: datetime
    time_end: datetime
    vol_band: tuple[float, float]
    regime_predicate: str
    expected_strength: float
    direction_bias: Direction
    rationale: dict[str, Any] = field(default_factory=dict)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "symbol": self.symbol,
            "price_lo": float(self.price_lo),
            "price_hi": float(self.price_hi),
            "time_start": _iso(self.time_start),
            "time_end": _iso(self.time_end),
            "vol_band": [float(self.vol_band[0]), float(self.vol_band[1])],
            "regime_predicate": self.regime_predicate,
            "expected_strength": float(self.expected_strength),
            "direction_bias": self.direction_bias,
            "rationale": self.rationale,
        }


# F22a canonical signal families. Each agent claims exactly one; the
# workspace's signal_family filter uses this taxonomy to answer "which
# thoughts on this tick belong to reading X?" instead of string-matching
# tag bags. New agents that don't fit any of these should add a new
# literal with a doctrine amendment.
SignalFamily = Literal[
    "metavision",         # A1 Isagi -- liquidity + market-structure fusion
    "pattern_rebel",      # A2 Bachira -- pattern-geometry rebel-lift
    "precision",          # A3 Rin -- fib/harmonic precision + Neo-Egoist lone read
    "breakout",           # A4 Chigiri -- range-break + ATR vol-expansion
    "adaptive_copy",      # A5 Reo -- adaptive copier
    "confluence",         # A6 Nagi -- multi-signal AND gate
    "solo_king",          # A7 Barou -- counter-liquidity solo kingship
    "risk_watch",         # A10 Kunigami -- defensive tilt/streak/overconfidence watch
    "unknown",             # sentinel for observe() paths that fired without a read
]


@dataclass(frozen=True)
class ThoughtRead:
    """F22a -- structured semantic content of a Thought.

    Pre-F22a, agents smuggled their read through the free-text
    ``Thought.narrative`` + a bag of ``tags``. Peer inspection had to
    string-match tag prefixes to guess the signal family. That was
    brittle and blocked Rin's Phase T-evolve from distinguishing
    "Isagi's metavision" from "Isagi's supply_demand" on the same
    direction.

    ``ThoughtRead`` promotes the core semantic content to a typed
    record so ``WorkspaceSnapshot.read_for(signal_family=...)`` can
    answer richer questions cleanly.

    Doctrine ref: 06 section 4.1a (workspace primitive) + F22a
    amendment (this file).
    """

    signal_family: SignalFamily
    direction_bias: Direction
    regime_read: str = "unknown"
    expected_stop_pips: float | None = None
    expected_r: float | None = None
    driving_evidence: tuple[str, ...] = ()

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "signal_family": self.signal_family,
            "direction_bias": self.direction_bias,
            "regime_read": self.regime_read,
            "expected_stop_pips": (
                float(self.expected_stop_pips)
                if self.expected_stop_pips is not None
                else None
            ),
            "expected_r": (
                float(self.expected_r) if self.expected_r is not None else None
            ),
            "driving_evidence": list(self.driving_evidence),
        }


@dataclass(frozen=True)
class Thought:
    """One agent's per-tick narrative + optional coordinate.

    Doctrine section 3.8. Look-ahead guarded by `decision_horizon`;
    `references` must point strictly backwards in time.

    F22a (2026-07-02) adds an optional structured ``read`` field
    carrying the signal-family + direction + regime read + expected
    R/stop. Legacy consumers can ignore it; workspace snapshots use
    ``read.signal_family`` as a first-class filter.
    """

    schema_version: int
    agent_id: str
    tick_id: int
    timestamp: datetime
    symbol: Symbol
    narrative: str
    tags: list[str]
    confidence_in_thought: float
    expected_action: str | None
    coordinate: Coordinate | None
    decision_horizon: datetime
    ttl_ticks: int
    references: list[str]
    thought_id: str = ""
    # F22a: structured read. None on unprepared / no-signal Thought paths;
    # populated on the main signal path in every 8-agent observe().
    read: ThoughtRead | None = None

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence_in_thought <= 1.0):
            raise ValueError(
                f"confidence_in_thought out of bounds: {self.confidence_in_thought}"
            )
        if self.ttl_ticks < 0:
            raise ValueError(f"ttl_ticks negative: {self.ttl_ticks}")
        if not self.thought_id:
            # Stable id from immutable identity fields; never includes wall-clock.
            object.__setattr__(
                self,
                "thought_id",
                f"{self.agent_id}:{self.tick_id}:{self.symbol}",
            )

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "schema_version": int(self.schema_version),
            "thought_id": self.thought_id,
            "agent_id": self.agent_id,
            "tick_id": int(self.tick_id),
            "timestamp": _iso(self.timestamp),
            "symbol": self.symbol,
            "narrative": self.narrative,
            "tags": list(self.tags),
            "confidence_in_thought": float(self.confidence_in_thought),
            "expected_action": self.expected_action,
            "coordinate": (
                self.coordinate.to_jsonable() if self.coordinate else None
            ),
            "decision_horizon": _iso(self.decision_horizon),
            "ttl_ticks": int(self.ttl_ticks),
            "references": list(self.references),
            "read": self.read.to_jsonable() if self.read is not None else None,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_jsonable(), sort_keys=True)


@dataclass(frozen=True)
class LadderRung:
    """One partial-exit rung on a proposal's ladder."""

    price: float
    fraction: float


@dataclass(frozen=True)
class AgentProposal:
    """A per-home-TF-close intent to trade.

    Architecture section 3.c. Aggregator refuses proposals without a hard
    SL or a ladder summing to 1.0.
    """

    agent_id: str
    tick_id: int
    source_thought_id: str
    timestamp: datetime
    symbol: Symbol
    direction: Direction  # "long" | "short" | "flat"
    entry: float
    stop: float
    ladder: list[LadderRung]
    conviction: float
    regime_fit: float
    valid_until: datetime
    rationale: dict[str, Any] = field(default_factory=dict)
    # F19/F20 doctrine 3.9: information tier of the striker who
    # produced this proposal. 1 = anchor (Isagi), 2 = peer, 3 = aux.
    # The Phi4 aggregator applies a small tier-1 conviction bias so the
    # anchor wins same-conviction tiebreaks (doctrine 4.1a v1 checkpoint
    # -- see M001 amendment 2026-07-01 "aggregator tier-anchor").
    # Backwards-compatible default = 2 so pre-tier-aware proposal
    # constructors still validate.
    agent_tier: int = 2

    def __post_init__(self) -> None:
        if self.direction not in ("long", "short", "flat"):
            raise ValueError(f"invalid direction: {self.direction}")
        if not (0.0 <= self.conviction <= 1.0):
            raise ValueError(f"conviction out of bounds: {self.conviction}")
        if not (0.0 <= self.regime_fit <= 1.0):
            raise ValueError(f"regime_fit out of bounds: {self.regime_fit}")
        if self.agent_tier not in (1, 2, 3):
            raise ValueError(f"agent_tier must be 1/2/3, got {self.agent_tier}")
        if self.direction in ("long", "short"):
            total = sum(r.fraction for r in self.ladder)
            if abs(total - 1.0) > 1e-6:
                raise ValueError(
                    f"ladder fractions sum to {total:.6f}, must sum to 1.0"
                )
            if self.stop <= 0:
                raise ValueError(f"stop must be positive: {self.stop}")

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "tick_id": int(self.tick_id),
            "source_thought_id": self.source_thought_id,
            "timestamp": _iso(self.timestamp),
            "symbol": self.symbol,
            "direction": self.direction,
            "entry": float(self.entry),
            "stop": float(self.stop),
            "ladder": [
                {"price": float(r.price), "fraction": float(r.fraction)}
                for r in self.ladder
            ],
            "conviction": float(self.conviction),
            "regime_fit": float(self.regime_fit),
            "valid_until": _iso(self.valid_until),
            "rationale": self.rationale,
            "agent_tier": int(self.agent_tier),
        }


@dataclass(frozen=True)
class OrderIntent:
    """Aggregator output: a single concrete order to send downstream.

    Carries provenance back to the contributing Thoughts and Proposals so
    `08-dashboard-spec.md` section 2.6 can replay the decision.
    """

    intent_id: str
    tick_id: int
    timestamp: datetime
    symbol: Symbol
    direction: Direction
    entry: float
    stop: float
    size: float
    ladder: list[LadderRung]
    contributing_thought_ids: list[str]
    contributing_proposal_ids: list[str]
    rationale: dict[str, Any] = field(default_factory=dict)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "tick_id": int(self.tick_id),
            "timestamp": _iso(self.timestamp),
            "symbol": self.symbol,
            "direction": self.direction,
            "entry": float(self.entry),
            "stop": float(self.stop),
            "size": float(self.size),
            "ladder": [
                {"price": float(r.price), "fraction": float(r.fraction)}
                for r in self.ladder
            ],
            "contributing_thought_ids": list(self.contributing_thought_ids),
            "contributing_proposal_ids": list(self.contributing_proposal_ids),
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class MarketState:
    """A single bar slice fed to every agent on every tick.

    Pure (no I/O). The kernel constructs these from parquet/CSV inputs;
    agents must never reach past the `as_of` timestamp.
    """

    tick_id: int
    symbol: Symbol
    timeframe: Timeframe
    as_of: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    # Optional bid/ask for the bar; used by `friction.spread_from_bar`.
    bid_low: float | None = None
    ask_high: float | None = None
    # Wider context piped through by the engine — read-only.
    features: dict[str, float] = field(default_factory=dict)
    history: dict[str, list[float]] = field(default_factory=dict)

    def to_jsonable(self) -> dict[str, Any]:
        return asdict(self) | {"as_of": _iso(self.as_of)}


@dataclass(frozen=True)
class CanonRole:
    """Fixed identity layer per agent (doctrine section 3.10)."""

    canon_player: str
    weapon: str
    ego: float
    target_hold_hours: float
    narrative_voice: str
