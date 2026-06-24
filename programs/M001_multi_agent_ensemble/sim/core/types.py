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


@dataclass(frozen=True)
class Thought:
    """One agent's per-tick narrative + optional coordinate.

    Doctrine section 3.8. Look-ahead guarded by `decision_horizon`;
    `references` must point strictly backwards in time.
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

    def __post_init__(self) -> None:
        if self.direction not in ("long", "short", "flat"):
            raise ValueError(f"invalid direction: {self.direction}")
        if not (0.0 <= self.conviction <= 1.0):
            raise ValueError(f"conviction out of bounds: {self.conviction}")
        if not (0.0 <= self.regime_fit <= 1.0):
            raise ValueError(f"regime_fit out of bounds: {self.regime_fit}")
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
