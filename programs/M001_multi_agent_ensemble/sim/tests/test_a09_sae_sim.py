"""Phase AE — sim-port Sae mechanics tests.

Mirrors the trading repo's ``tests/test_squad_sae.py`` coverage for
the mechanics the Phase AE harness exercises: fade fire, ride fire,
threshold rejections, one-proposal-per-event, disabled flag, and the
frozen-calendar loader.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from programs.M001_multi_agent_ensemble.sim.agents.a09_sae import (
    A9SaeV1,
    SaeConfig,
    SimNewsEvent,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import FullLedger
from programs.M001_multi_agent_ensemble.sim.core.types import (
    AgentProposal,
    MarketState,
)

UTC = timezone.utc
EVENT_T = datetime(2024, 3, 8, 13, 30, tzinfo=UTC)
PIP = 0.0001


@dataclass
class FakeBar:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 100.0


def _market(as_of: datetime, tick_id: int = 1) -> MarketState:
    return MarketState(
        tick_id=tick_id, symbol="EURUSD", timeframe="M15", as_of=as_of,
        open=1.10, high=1.11, low=1.09, close=1.105, volume=100.0,
    )


def _sae(bars: list[FakeBar], events: list[SimNewsEvent] | None = None) -> A9SaeV1:
    sae = A9SaeV1(config=SaeConfig(sae_enabled=True))
    sae.load_calendar(events=events if events is not None else [
        SimNewsEvent(time_utc=EVENT_T, currency="USD", impact="High",
                     title="Employment Situation (NFP)"),
    ])
    sae.set_bars_provider(lambda sym, start, end: [
        b for b in bars
        if start <= b.time and b.time + timedelta(minutes=15) <= end
    ])
    return sae


def _fade_bars() -> list[FakeBar]:
    """Bullish 50-pip event bar with a 55% upper wick."""
    o = 1.1000
    c = o + 50 * PIP                    # +50 pips body
    h = o + 120 * PIP                   # upper wick (h-c)/range = 70/... below
    lo = o - 5 * PIP
    # range = 125 pips; upper wick = 70 pips -> 0.56 >= 0.5 ✓
    return [
        FakeBar(time=EVENT_T, open=o, high=h, low=lo, close=c),
        FakeBar(time=EVENT_T + timedelta(minutes=15),
                open=c, high=c + 10 * PIP, low=c - 10 * PIP, close=c),
    ]


def _ride_bars() -> list[FakeBar]:
    """Bullish 50-pip event bar, tiny wick; next bar closes bullish
    (open o+40p -> close o+45p) with 90% retention of the impulse."""
    o = 1.1000
    c = o + 50 * PIP
    nxt_o = o + 40 * PIP
    nxt_c = o + 45 * PIP                # retention 0.9 >= 0.7 ✓, same dir ✓
    return [
        FakeBar(time=EVENT_T, open=o, high=c + 2 * PIP, low=o - 2 * PIP, close=c),
        FakeBar(time=EVENT_T + timedelta(minutes=15),
                open=nxt_o, high=nxt_c + 2 * PIP, low=nxt_o - 2 * PIP,
                close=nxt_c),
    ]


def _observe_and_intend(sae: A9SaeV1, as_of: datetime):
    market = _market(as_of)
    thought = sae.observe(market, FullLedger())
    return sae.intend(market, thought)


class TestFade:
    def test_fade_fires_short_on_bullish_rejection(self):
        sae = _sae(_fade_bars())
        p = _observe_and_intend(sae, EVENT_T + timedelta(minutes=15))
        assert isinstance(p, AgentProposal)
        assert p.direction == "short"
        assert p.rationale["mechanic"] == "sae_fade"
        assert p.conviction == pytest.approx(0.85)
        # Stop = event bar high + 5 pip padding.
        assert p.stop == pytest.approx(1.1000 + 120 * PIP + 5 * PIP)

    def test_fade_blocked_below_move_floor(self):
        bars = _fade_bars()
        small = FakeBar(time=EVENT_T, open=1.1000, high=1.1010,
                        low=1.0995, close=1.1003)     # 3-pip move
        sae = _sae([small, bars[1]])
        assert _observe_and_intend(sae, EVENT_T + timedelta(minutes=15)) is None

    def test_fade_blocked_below_wick_floor(self):
        o = 1.1000
        c = o + 50 * PIP
        bar = FakeBar(time=EVENT_T, open=o, high=c + 5 * PIP,
                      low=o - 2 * PIP, close=c)       # wick frac ~0.09
        sae = _sae([bar])
        assert _observe_and_intend(sae, EVENT_T + timedelta(minutes=15)) is None

    def test_no_fire_before_t_plus_15(self):
        sae = _sae(_fade_bars())
        assert _observe_and_intend(sae, EVENT_T + timedelta(minutes=10)) is None


class TestRide:
    def test_ride_fires_long_on_retained_impulse(self):
        sae = _sae(_ride_bars())
        p = _observe_and_intend(sae, EVENT_T + timedelta(minutes=30))
        assert isinstance(p, AgentProposal)
        assert p.direction == "long"
        assert p.rationale["mechanic"] == "sae_ride"
        assert p.stop == pytest.approx(1.1000)        # event bar open
        assert p.entry == pytest.approx(1.1000 + 45 * PIP)

    def test_ride_blocked_below_retention(self):
        bars = _ride_bars()
        weak = FakeBar(time=EVENT_T + timedelta(minutes=15),
                       open=bars[0].close,
                       high=bars[0].close + 2 * PIP,
                       low=1.1000 + 10 * PIP,
                       close=1.1000 + 20 * PIP)       # retention 0.4
        sae = _sae([bars[0], weak])
        assert _observe_and_intend(sae, EVENT_T + timedelta(minutes=30)) is None

    def test_ride_not_evaluated_at_t_plus_15(self):
        sae = _sae(_ride_bars())
        assert _observe_and_intend(sae, EVENT_T + timedelta(minutes=15)) is None


class TestGuards:
    def test_one_proposal_per_event(self):
        sae = _sae(_fade_bars())
        first = _observe_and_intend(sae, EVENT_T + timedelta(minutes=15))
        assert first is not None
        again = _observe_and_intend(sae, EVENT_T + timedelta(minutes=30))
        assert again is None

    def test_disabled_flag_blocks_everything(self):
        sae = A9SaeV1(config=SaeConfig(sae_enabled=False))
        sae.load_calendar(events=[SimNewsEvent(
            time_utc=EVENT_T, currency="USD", impact="High", title="NFP",
        )])
        bars = _fade_bars()
        sae.set_bars_provider(lambda sym, s, e: bars)
        assert _observe_and_intend(sae, EVENT_T + timedelta(minutes=15)) is None

    def test_non_usd_or_low_impact_ignored(self):
        events = [
            SimNewsEvent(time_utc=EVENT_T, currency="EUR", impact="High",
                         title="ECB"),
            SimNewsEvent(time_utc=EVENT_T, currency="USD", impact="Medium",
                         title="minor"),
        ]
        sae = _sae(_fade_bars(), events=events)
        assert _observe_and_intend(sae, EVENT_T + timedelta(minutes=15)) is None

    def test_no_bars_provider_fails_open(self):
        sae = A9SaeV1(config=SaeConfig(sae_enabled=True))
        sae.load_calendar(events=[SimNewsEvent(
            time_utc=EVENT_T, currency="USD", impact="High", title="NFP",
        )])
        assert _observe_and_intend(sae, EVENT_T + timedelta(minutes=15)) is None


class TestFrozenCalendarFixture:
    def test_fixture_loads_and_is_all_high_usd(self):
        from pathlib import Path

        from programs.M001_multi_agent_ensemble.sim.agents.a09_sae import (
            load_frozen_calendar,
        )
        fixture = (
            Path(__file__).resolve().parents[2]
            / "data" / "news_calendar_frozen_2026-07-24.json"
        )
        events = load_frozen_calendar(fixture)
        assert len(events) == 349
        assert all(e.currency == "USD" for e in events)
        assert all(e.impact == "High" for e in events)
        assert events[0].time_utc.year == 2015
        assert events[-1].time_utc.year == 2025
        # Sorted ascending.
        assert all(
            events[i].time_utc <= events[i + 1].time_utc
            for i in range(len(events) - 1)
        )
