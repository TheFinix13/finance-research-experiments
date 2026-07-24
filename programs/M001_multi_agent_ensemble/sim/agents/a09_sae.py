"""A9 -- Sae Itoshi v1 (`sae_itoshi`) -- event specialist striker (SIM PORT).

Research-sim port of the trading repo's
``agent/squad/agents/a09_sae.py`` (branch ``next-gen``, commit
``a26eba8``) for the Phase AE pre-registration
(``experiments/phase_ae_sae_event_specialist/PROTOCOL.md``).

MECHANICS ARE VERBATIM from the production implementation (fade +
ride, thresholds per ``SaeConfig`` below == production
``agent/squad/sae_config.py`` defaults). Deliberate divergences,
all harness-plumbing only (flagged in the Phase AE report):

1. Types come from ``sim.core`` (``BaseStriker``, ``Thought``,
   ``AgentProposal``, ...) instead of ``agent.squad.*`` -- the same
   1:1 mirroring every other sim agent uses.
2. The calendar is the FROZEN fixture
   ``data/news_calendar_frozen_2026-07-24.json`` loaded via
   :func:`load_frozen_calendar` (the production ``NewsEvent`` /
   ``load_calendar`` machinery reads the live cache, which is
   off-limits to the research harness).
3. ``home_tf`` defaults to ``"M15"``: the Phase AE driver evaluates
   Sae at M15 event ticks (T+15 / T+30) injected alongside the H4
   replay (PROTOCOL §0 amendment 4). Production keeps ``"H4"`` for
   engine cadence reasons; the mechanics themselves are unchanged.
4. ``intend()`` accepts the sim driver's ``workspace=`` kwarg
   (ignored -- v1 Sae reads no peers, same as production).

Universe: EURUSD-only in v1. ``sae_enabled=False`` by default,
mirroring production.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from programs.M001_multi_agent_ensemble.sim.core.ledger import ThoughtLedger
from programs.M001_multi_agent_ensemble.sim.core.striker import BaseStriker
from programs.M001_multi_agent_ensemble.sim.core.types import (
    SCHEMA_VERSION,
    AgentProposal,
    CanonRole,
    LadderRung,
    MarketState,
    Thought,
    ThoughtRead,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Frozen-calendar event type + loader (Phase AE fixture)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SimNewsEvent:
    """One scheduled economic event from the frozen fixture.

    Field names mirror the production ``agent.news.calendar.NewsEvent``
    surface Sae actually touches (``time_utc`` / ``currency`` /
    ``impact`` / ``title``).
    """

    time_utc: datetime
    currency: str
    impact: str
    title: str


def load_frozen_calendar(path: str | Path) -> list[SimNewsEvent]:
    """Load the frozen Phase AD/AE calendar fixture (never refetched)."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    events: list[SimNewsEvent] = []
    for e in payload["events"]:
        events.append(SimNewsEvent(
            time_utc=datetime.fromisoformat(e["time_utc"]),
            currency=str(e["currency"]),
            impact=str(e["impact"]),
            title=str(e["title"]),
        ))
    events.sort(key=lambda e: e.time_utc)
    return events


# ---------------------------------------------------------------------------
# Config (verbatim values from agent/squad/sae_config.py, next-gen a26eba8)
# ---------------------------------------------------------------------------

DEFAULT_SAE_SYMBOLS: tuple[str, ...] = ("EURUSD",)


@dataclass(frozen=True)
class SaeConfig:
    """Locked knobs -- byte-identical values to production SaeConfig."""

    sae_enabled: bool = False
    symbols: tuple[str, ...] = DEFAULT_SAE_SYMBOLS
    fire_window_before_min: int = 30
    fire_window_after_min: int = 60
    fade_min_move_pips: float = 40.0
    fade_min_wick_frac: float = 0.5
    ride_min_retention: float = 0.7
    target_rr: float = 1.5
    fade_wait_min: int = 15
    ride_wait_min: int = 30
    fade_stop_padding_pips: float = 5.0
    pip_size: float = 0.0001


DEFAULT_SAE_CONFIG = SaeConfig()


SAE_V1_CANON_ROLE = CanonRole(
    canon_player="sae_itoshi",
    weapon="event_release_impulse",
    ego=0.75,
    target_hold_hours=6.0,
    narrative_voice="elite_striker_decisive",
)


BarsProvider = Callable[[str, datetime, datetime], list]
"""Injectable M15 bar fetcher: ``(symbol, start_utc, end_utc) -> list[Bar]``.

Bars must be CLOSED as of the requested end, sorted ascending, M15.
The Phase AE harness wires a closure over the production parquet
cache (read-only); tests pass synthetic in-memory lists.
"""


def _ensure_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class A9SaeV1(BaseStriker):
    """A9 Sae Itoshi v1 -- event specialist striker (sim port)."""

    def __init__(
        self,
        agent_id: str = "sae_itoshi",
        canon_role: Optional[CanonRole] = None,
        home_tf: str = "M15",
        symbols: Optional[Iterable[str]] = None,
        *,
        config: SaeConfig | None = None,
        bars_provider: BarsProvider | None = None,
    ) -> None:
        cfg = config or DEFAULT_SAE_CONFIG
        super().__init__(
            agent_id=agent_id,
            canon_role=canon_role or SAE_V1_CANON_ROLE,
            home_tf=home_tf,
            symbols=list(symbols) if symbols is not None else list(cfg.symbols),
            playstyle="event_specialist",
            tier=1,
        )
        self._config: SaeConfig = cfg
        self._events: list[SimNewsEvent] = []
        self._bars_provider: BarsProvider | None = bars_provider
        self._fired_events: set[tuple[str, str]] = set()

    # ------------------------------------------------------------------
    # Calendar hydration
    # ------------------------------------------------------------------

    def load_calendar(
        self,
        *,
        path: str | Path | None = None,
        events: Iterable[SimNewsEvent] | None = None,
    ) -> int:
        if events is not None:
            self._events = list(events)
            return len(self._events)
        if path is None:
            raise ValueError("load_calendar needs a fixture path or events=")
        self._events = load_frozen_calendar(path)
        return len(self._events)

    def set_bars_provider(self, provider: BarsProvider | None) -> None:
        self._bars_provider = provider

    @property
    def n_events(self) -> int:
        return len(self._events)

    @property
    def enabled(self) -> bool:
        return self._config.sae_enabled

    # ------------------------------------------------------------------
    # Event lookup (verbatim logic)
    # ------------------------------------------------------------------

    def _nearest_scheduled_event(self, as_of: datetime) -> SimNewsEvent | None:
        as_of = _ensure_utc(as_of)
        earliest = as_of - timedelta(minutes=self._config.fire_window_after_min)
        latest = as_of + timedelta(minutes=self._config.fire_window_before_min)
        candidates: list[SimNewsEvent] = []
        for e in self._events:
            if e.currency.upper() != "USD":
                continue
            if e.impact.lower() != "high":
                continue
            if earliest <= e.time_utc <= latest:
                candidates.append(e)
        if not candidates:
            return None
        candidates.sort(key=lambda e: e.time_utc)
        return candidates[0]

    def _event_key(self, event: SimNewsEvent, symbol: str) -> tuple[str, str]:
        return (event.time_utc.isoformat(), symbol)

    # ------------------------------------------------------------------
    # BlueLockStriker contract
    # ------------------------------------------------------------------

    def observe(self, market: MarketState, ledger: ThoughtLedger) -> Thought:  # noqa: ARG002
        tags = ["canon:sae", "weapon:event_release_impulse"]
        if market.symbol not in self.symbols:
            return self._abstain(market, tags + ["off_symbol"], "off_symbol")

        event = self._nearest_scheduled_event(market.as_of)
        if event is None:
            return self._abstain(market, tags + ["no_event_in_window"], "no_event")

        mins_to_event = int(
            (event.time_utc - _ensure_utc(market.as_of)).total_seconds() // 60
        )
        narrative = (
            f"[sae v1] {market.symbol} {market.timeframe} @ {market.as_of}: "
            f"awaiting release ('{event.title}' {event.currency} "
            f"{event.impact}, {mins_to_event:+d} min); "
            f"fade wait={self._config.fade_wait_min}min, "
            f"ride wait={self._config.ride_wait_min}min."
        )
        return Thought(
            schema_version=SCHEMA_VERSION,
            agent_id=self.agent_id,
            tick_id=market.tick_id,
            timestamp=market.as_of,
            symbol=market.symbol,
            narrative=narrative,
            tags=tags + ["awaiting_event", f"minutes_to_event:{mins_to_event}"],
            confidence_in_thought=0.0,
            expected_action="await_event",
            coordinate=None,
            decision_horizon=market.as_of,
            ttl_ticks=1,
            references=[],
            read=ThoughtRead(
                signal_family="solo_king",   # elite-striker family
                direction_bias="flat",
                regime_read="event_pending",
                driving_evidence=("sae_awaiting_event",),
            ),
        )

    def intend(
        self,
        market: MarketState,
        my_recent_thought: Thought,
        *,
        workspace: Any | None = None,   # noqa: ARG002 -- v1 reads no peers
        **_kwargs: object,
    ) -> AgentProposal | None:
        if not self._config.sae_enabled:
            return None
        if market.timeframe != self.home_tf:
            return None
        if market.symbol not in self.symbols:
            return None
        if self._bars_provider is None:
            return None

        event = self._nearest_scheduled_event(market.as_of)
        if event is None:
            return None

        key = self._event_key(event, market.symbol)
        if key in self._fired_events:
            return None

        as_of = _ensure_utc(market.as_of)
        event_time = _ensure_utc(event.time_utc)
        t_fade = event_time + timedelta(minutes=self._config.fade_wait_min)
        t_ride = event_time + timedelta(minutes=self._config.ride_wait_min)

        start = event_time - timedelta(minutes=30)
        end = as_of + timedelta(minutes=1)
        try:
            bars = self._bars_provider(market.symbol, start, end)
        except Exception as exc:   # noqa: BLE001
            log.warning(
                "A9SaeV1: bars_provider raised (%s) for %s -- skipping fire.",
                exc, market.symbol,
            )
            return None

        event_bar = _find_bar_covering(bars, event_time)
        if event_bar is None:
            return None

        proposal: AgentProposal | None = None

        if as_of >= t_fade:
            proposal = self._try_fade(
                market=market,
                event=event,
                event_bar=event_bar,
                my_recent_thought=my_recent_thought,
            )
            if proposal is not None:
                self._fired_events.add(key)
                return proposal

        if as_of >= t_ride:
            next_bar = _find_bar_covering(
                bars, event_time + timedelta(minutes=15),
            )
            if next_bar is None or next_bar.time == event_bar.time:
                return None
            proposal = self._try_ride(
                market=market,
                event=event,
                event_bar=event_bar,
                next_bar=next_bar,
                my_recent_thought=my_recent_thought,
            )
            if proposal is not None:
                self._fired_events.add(key)
                return proposal

        return None

    # ------------------------------------------------------------------
    # Mechanics (verbatim from production)
    # ------------------------------------------------------------------

    def _try_fade(
        self,
        *,
        market: MarketState,
        event: SimNewsEvent,
        event_bar: Any,
        my_recent_thought: Thought,
    ) -> AgentProposal | None:
        cfg = self._config
        pip = cfg.pip_size
        move_price = event_bar.close - event_bar.open
        move_pips = abs(move_price) / pip
        rng = event_bar.high - event_bar.low
        if rng <= 0.0:
            return None
        if move_pips < cfg.fade_min_move_pips:
            return None

        if move_price > 0:
            wick = (event_bar.high - event_bar.close) / rng
            if wick < cfg.fade_min_wick_frac:
                return None
            direction = "short"
            stop_price = event_bar.high + cfg.fade_stop_padding_pips * pip
            entry_price = event_bar.close
            risk = stop_price - entry_price
            tp_price = entry_price - cfg.target_rr * risk
        else:
            wick = (event_bar.open - event_bar.low) / rng
            if wick < cfg.fade_min_wick_frac:
                return None
            direction = "long"
            stop_price = event_bar.low - cfg.fade_stop_padding_pips * pip
            entry_price = event_bar.close
            risk = entry_price - stop_price
            tp_price = entry_price + cfg.target_rr * risk

        if risk <= 0:
            return None

        rationale = {
            "mechanic": "sae_fade",
            "event_title": event.title,
            "event_time": event.time_utc.isoformat(),
            "event_bar_open": float(event_bar.open),
            "event_bar_close": float(event_bar.close),
            "event_bar_high": float(event_bar.high),
            "event_bar_low": float(event_bar.low),
            "move_pips": float(move_pips),
            "wick_frac": float(wick),
            "target_rr": float(cfg.target_rr),
        }
        return _build_proposal(
            agent_id=self.agent_id,
            tick_id=int(market.tick_id),
            source_thought=my_recent_thought,
            symbol=market.symbol,
            direction=direction,
            entry=entry_price,
            stop=stop_price,
            tp=tp_price,
            timestamp=market.as_of,
            hold_hours=float(self.canon_role.target_hold_hours),
            rationale=rationale,
            tier=int(self.tier),
            tag="sae_fade",
        )

    def _try_ride(
        self,
        *,
        market: MarketState,
        event: SimNewsEvent,
        event_bar: Any,
        next_bar: Any,
        my_recent_thought: Thought,
    ) -> AgentProposal | None:
        cfg = self._config
        pip = cfg.pip_size
        move_price = event_bar.close - event_bar.open
        move_pips = abs(move_price) / pip
        if move_pips <= 0:
            return None
        impulse_direction = "long" if move_price > 0 else "short"

        next_bar_dir = "long" if next_bar.close >= next_bar.open else "short"
        if next_bar_dir != impulse_direction:
            return None

        retention = (next_bar.close - event_bar.open)
        if impulse_direction == "short":
            retention = -retention
        if abs(move_price) <= 0:
            return None
        retention_frac = retention / abs(move_price)
        if retention_frac < cfg.ride_min_retention:
            return None

        entry_price = float(next_bar.close)
        stop_price = float(event_bar.open)
        risk = abs(entry_price - stop_price)
        if risk <= 0:
            return None
        if impulse_direction == "long" and stop_price >= entry_price:
            return None
        if impulse_direction == "short" and stop_price <= entry_price:
            return None
        if impulse_direction == "long":
            tp_price = entry_price + cfg.target_rr * risk
        else:
            tp_price = entry_price - cfg.target_rr * risk

        rationale = {
            "mechanic": "sae_ride",
            "event_title": event.title,
            "event_time": event.time_utc.isoformat(),
            "event_bar_open": float(event_bar.open),
            "event_bar_close": float(event_bar.close),
            "next_bar_open": float(next_bar.open),
            "next_bar_close": float(next_bar.close),
            "move_pips": float(move_pips),
            "retention_frac": float(retention_frac),
            "target_rr": float(cfg.target_rr),
        }
        return _build_proposal(
            agent_id=self.agent_id,
            tick_id=int(market.tick_id),
            source_thought=my_recent_thought,
            symbol=market.symbol,
            direction=impulse_direction,
            entry=entry_price,
            stop=stop_price,
            tp=tp_price,
            timestamp=market.as_of,
            hold_hours=float(self.canon_role.target_hold_hours),
            rationale=rationale,
            tier=int(self.tier),
            tag="sae_ride",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _abstain(
        self, market: MarketState, tags: list[str], reason: str,
    ) -> Thought:
        return Thought(
            schema_version=SCHEMA_VERSION,
            agent_id=self.agent_id,
            tick_id=market.tick_id,
            timestamp=market.as_of,
            symbol=market.symbol,
            narrative=(
                f"[sae v1] {market.symbol} {market.timeframe} @ "
                f"{market.as_of}: abstain ({reason})."
            ),
            tags=tags,
            confidence_in_thought=0.0,
            expected_action="wait",
            coordinate=None,
            decision_horizon=market.as_of,
            ttl_ticks=1,
            references=[],
        )


def _find_bar_covering(bars: list, target: datetime) -> Any | None:
    """Return the M15 bar whose [time, time + 15 min) covers ``target``."""
    target = _ensure_utc(target)
    for b in bars:
        b_time = _ensure_utc(b.time)
        if b_time <= target < b_time + timedelta(minutes=15):
            return b
    return None


def _build_proposal(
    *,
    agent_id: str,
    tick_id: int,
    source_thought: Thought,
    symbol: str,
    direction: str,
    entry: float,
    stop: float,
    tp: float,
    timestamp: datetime,
    hold_hours: float,
    rationale: dict,
    tier: int,
    tag: str,
) -> AgentProposal:
    valid_until = timestamp + timedelta(hours=hold_hours)
    ladder = [LadderRung(price=float(tp), fraction=1.0)]
    rationale = dict(rationale) | {"tag": tag}
    return AgentProposal(
        agent_id=agent_id,
        tick_id=int(tick_id),
        source_thought_id=source_thought.thought_id,
        timestamp=timestamp,
        symbol=symbol,
        direction=direction,   # type: ignore[arg-type]
        entry=float(entry),
        stop=float(stop),
        ladder=ladder,
        conviction=0.85,
        regime_fit=0.6,
        valid_until=valid_until,
        rationale=rationale,
        agent_tier=int(tier),
    )


SaeItoshi = A9SaeV1


__all__ = [
    "A9SaeV1",
    "BarsProvider",
    "DEFAULT_SAE_CONFIG",
    "DEFAULT_SAE_SYMBOLS",
    "SAE_V1_CANON_ROLE",
    "SaeConfig",
    "SaeItoshi",
    "SimNewsEvent",
    "load_frozen_calendar",
]
