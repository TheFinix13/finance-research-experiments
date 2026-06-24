"""A6 Nagi v1 wrap tests.

Covers the F11/F13 confluence trigger predicate, the one-bar lag (a
doctrine sec 3.8 invariant), and the safe-degrade observation-only
path when the ledger has no qualifying peer thoughts.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from programs.M001_multi_agent_ensemble.sim.agents.a06_nagi import (
    A6NagiV1,
    NAGI_V1_CONFIDENCE_FLOOR,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import (
    FullLedger, RedactedLedger, SyntheticLedger,
)
from programs.M001_multi_agent_ensemble.sim.core.types import (
    SCHEMA_VERSION,
    Coordinate, MarketState, Thought,
)


def _market(tick: int, symbol: str = "EURUSD", tf: str = "H4") -> MarketState:
    return MarketState(
        tick_id=tick,
        symbol=symbol,
        timeframe=tf,
        as_of=datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(hours=4 * tick),
        open=1.1000, high=1.1010, low=1.0990, close=1.1005,
        volume=100.0,
    )


def _coord(symbol: str, *, lo: float, hi: float, direction: str, conv: float) -> Coordinate:
    return Coordinate(
        agent_id="seed",
        symbol=symbol,
        price_lo=lo, price_hi=hi,
        time_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        time_end=datetime(2024, 1, 2, tzinfo=timezone.utc),
        vol_band=(0.5, 2.0),
        regime_predicate="seed",
        expected_strength=conv,
        direction_bias=direction,
        rationale={
            "entry": (lo + hi) / 2,
            "stop": lo - 0.0005 if direction == "long" else hi + 0.0005,
            "take_profit": hi + 0.0050 if direction == "long" else lo - 0.0050,
        },
    )


def _peer_thought(
    *,
    agent_id: str,
    tick: int,
    symbol: str = "EURUSD",
    conviction: float = 0.75,
    direction: str = "long",
    tags: list[str] | None = None,
    coord: Coordinate | None = None,
) -> Thought:
    return Thought(
        schema_version=SCHEMA_VERSION,
        agent_id=agent_id,
        tick_id=tick,
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc)
        + timedelta(hours=4 * tick),
        symbol=symbol,
        narrative="seed",
        tags=tags or ["zone_d1_against", "htf_against"],
        confidence_in_thought=conviction,
        expected_action=f"{direction}_on_H4_close",
        coordinate=coord
        or _coord(symbol, lo=1.0950, hi=1.1050, direction=direction, conv=conviction),
        decision_horizon=datetime(2024, 1, 1, tzinfo=timezone.utc)
        + timedelta(hours=4 * tick),
        ttl_ticks=6,
        references=[],
    )


# ---------------------------------------------------------------------------
# Predicate tests
# ---------------------------------------------------------------------------

def test_observation_only_when_zero_peers():
    nagi = A6NagiV1()
    ledger = FullLedger()
    t = nagi.observe(_market(tick=1), ledger)
    assert t.coordinate is None
    assert t.confidence_in_thought == 0.0
    assert "kunigami_loss_streak_warning" not in t.tags
    assert nagi.intend(_market(tick=1), t) is None


def test_observation_only_when_only_low_conviction_peers():
    nagi = A6NagiV1()
    ledger = FullLedger()
    ledger.append(_peer_thought(
        agent_id="isagi_yoichi", tick=0,
        conviction=NAGI_V1_CONFIDENCE_FLOOR - 0.05,
    ))
    ledger.append(_peer_thought(
        agent_id="barou_shoei", tick=0,
        conviction=NAGI_V1_CONFIDENCE_FLOOR - 0.05,
    ))
    t = nagi.observe(_market(tick=1), ledger)
    assert t.coordinate is None
    assert "nagi_confluence" not in t.tags


def test_observation_only_when_single_peer():
    nagi = A6NagiV1()
    ledger = FullLedger()
    ledger.append(_peer_thought(
        agent_id="isagi_yoichi", tick=0, conviction=0.85,
    ))
    t = nagi.observe(_market(tick=1), ledger)
    # Only 1 peer thought -- no confluence.
    assert t.coordinate is None
    assert "nagi_confluence" not in t.tags


def test_confluence_fires_with_two_distinct_high_conviction_peers():
    nagi = A6NagiV1()
    ledger = FullLedger()
    common_tags = ["zone_d1_against", "htf_against", "shared_seed"]
    ledger.append(_peer_thought(
        agent_id="isagi_yoichi", tick=0, conviction=0.80,
        tags=common_tags,
        coord=_coord("EURUSD", lo=1.0995, hi=1.1015, direction="long", conv=0.80),
    ))
    ledger.append(_peer_thought(
        agent_id="barou_shoei", tick=0, conviction=0.85,
        tags=common_tags + ["barou_devour_candidate"],
        coord=_coord("EURUSD", lo=1.1000, hi=1.1020, direction="long", conv=0.85),
    ))
    t = nagi.observe(_market(tick=1), ledger)
    assert t.coordinate is not None, "expected confluence to fire"
    assert "nagi_confluence" in t.tags
    assert "f11_chemical_reaction" in t.tags
    # F11 lift: 1 - (1-0.80)*(1-0.85) = 1 - 0.03 = 0.97
    assert t.confidence_in_thought == pytest.approx(0.97, abs=1e-9)
    # references must point backwards (tick 0 < current tick 1).
    assert len(t.references) == 2


def test_one_bar_lag_same_tick_reads_forbidden():
    """Doctrine sec 3.8 -- same-tick reads forbidden. The ledger guard
    filters out `tick_id >= current_tick` so Nagi at tick T sees only
    T-1 thoughts. Confirm by appending peer thoughts at the SAME tick
    Nagi observes -- confluence must NOT fire."""
    nagi = A6NagiV1()
    ledger = FullLedger()
    common_tags = ["zone_d1_against", "htf_against", "shared_seed"]
    # Peer thoughts at tick=1 (SAME tick Nagi observes).
    ledger.append(_peer_thought(
        agent_id="isagi_yoichi", tick=1, conviction=0.80, tags=common_tags,
    ))
    ledger.append(_peer_thought(
        agent_id="barou_shoei", tick=1, conviction=0.85, tags=common_tags,
    ))
    t = nagi.observe(_market(tick=1), ledger)
    # Same-tick reads forbidden -- no confluence.
    assert t.coordinate is None
    assert "nagi_confluence" not in t.tags


def test_intend_returns_none_without_confluence_tag():
    nagi = A6NagiV1()
    market = _market(tick=2)
    bare_thought = Thought(
        schema_version=SCHEMA_VERSION,
        agent_id="nagi_seishiro", tick_id=2,
        timestamp=market.as_of, symbol="EURUSD",
        narrative="observation-only",
        tags=["confluence_seeker"],
        confidence_in_thought=0.0,
        expected_action="wait",
        coordinate=None,
        decision_horizon=market.as_of,
        ttl_ticks=1, references=[],
    )
    assert nagi.intend(market, bare_thought) is None


def test_intend_emits_proposal_on_confluence_thought():
    """End-to-end: confluence fires, then `intend()` emits a Proposal
    that mirrors the leader's entry/stop/tp."""
    nagi = A6NagiV1()
    ledger = FullLedger()
    common_tags = ["zone_d1_against", "htf_against", "shared_seed"]
    leader_coord = _coord(
        "EURUSD", lo=1.0995, hi=1.1015, direction="long", conv=0.80,
    )
    ledger.append(_peer_thought(
        agent_id="isagi_yoichi", tick=0, conviction=0.80,
        tags=common_tags, coord=leader_coord,
    ))
    ledger.append(_peer_thought(
        agent_id="barou_shoei", tick=0, conviction=0.85, tags=common_tags,
        coord=_coord(
            "EURUSD", lo=1.1000, hi=1.1020, direction="long", conv=0.85,
        ),
    ))
    market = _market(tick=1)
    t = nagi.observe(market, ledger)
    p = nagi.intend(market, t)
    assert p is not None
    assert p.direction == "long"
    # Entry/stop/tp mirror the LEADER (higher conviction = barou here).
    assert p.entry == pytest.approx(1.1010)  # (1.1000 + 1.1020) / 2
    # Conviction equals the F11 lift.
    assert p.conviction == pytest.approx(0.97, abs=1e-9)


def test_observation_only_when_direction_disagreement():
    nagi = A6NagiV1()
    ledger = FullLedger()
    common_tags = ["zone_d1_against", "htf_against", "shared_seed"]
    ledger.append(_peer_thought(
        agent_id="isagi_yoichi", tick=0, conviction=0.80, direction="long",
        tags=common_tags,
        coord=_coord("EURUSD", lo=1.0995, hi=1.1015, direction="long", conv=0.80),
    ))
    ledger.append(_peer_thought(
        agent_id="barou_shoei", tick=0, conviction=0.85, direction="short",
        tags=common_tags,
        coord=_coord("EURUSD", lo=1.1000, hi=1.1020, direction="short", conv=0.85),
    ))
    t = nagi.observe(_market(tick=1), ledger)
    # Direction disagreement -> no confluence.
    assert t.coordinate is None
