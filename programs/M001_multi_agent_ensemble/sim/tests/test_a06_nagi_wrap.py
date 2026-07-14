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


def _coord(
    symbol: str, *, lo: float, hi: float, direction: str, conv: float,
    atr_pips: float | None = None, h1_swing_pips: float | None = None,
) -> Coordinate:
    rationale: dict = {
        "entry": (lo + hi) / 2,
        "stop": lo - 0.0005 if direction == "long" else hi + 0.0005,
        "take_profit": hi + 0.0050 if direction == "long" else lo - 0.0050,
    }
    if atr_pips is not None:
        rationale["atr_pips"] = float(atr_pips)
    if h1_swing_pips is not None:
        rationale["h1_swing_pips"] = float(h1_swing_pips)
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
        rationale=rationale,
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


# ---------------------------------------------------------------------------
# Dispersion-primitives round 2 (2026-07-14): Nagi borrows the leader's
# volatility provenance so his F19/F20 inputs are real and varying.
# ---------------------------------------------------------------------------


def _fire_confluence(
    *, leader_coord: Coordinate, other_coord: Coordinate,
    leader_conv: float = 0.80, other_conv: float = 0.85,
) -> tuple[A6NagiV1, Thought, MarketState]:
    """Build a two-peer confluence firing configuration and run
    ``observe`` -> return (nagi, firing_thought, market)."""
    nagi = A6NagiV1()
    ledger = FullLedger()
    common_tags = ["zone_d1_against", "htf_against", "shared_seed"]
    ledger.append(_peer_thought(
        agent_id="isagi_yoichi", tick=0, conviction=leader_conv,
        tags=common_tags, coord=leader_coord,
    ))
    ledger.append(_peer_thought(
        agent_id="barou_shoei", tick=0, conviction=other_conv,
        tags=common_tags, coord=other_coord,
    ))
    market = _market(tick=1)
    return nagi, nagi.observe(market, ledger), market


def test_nagi_borrows_leader_atr_and_swing_when_stamped():
    """Dispersion-r2 §2.3: Nagi's proposal rationale must carry the
    leader's stamped ``atr_pips`` and ``h1_swing_pips`` (verbatim).
    """
    leader_coord = _coord(
        "EURUSD", lo=1.0995, hi=1.1015, direction="long", conv=0.85,
        atr_pips=42.0, h1_swing_pips=118.0,
    )
    other_coord = _coord(
        "EURUSD", lo=1.1000, hi=1.1020, direction="long", conv=0.80,
    )
    nagi, firing, market = _fire_confluence(
        leader_coord=leader_coord, other_coord=other_coord,
        leader_conv=0.85, other_conv=0.80,   # isagi wins as leader
    )
    p = nagi.intend(market, firing)
    assert p is not None
    assert p.rationale["atr_pips"] == pytest.approx(42.0)
    assert p.rationale["h1_swing_pips"] == pytest.approx(118.0)
    assert p.rationale["regime_fit_source"] == "leader_atr_pips_phase_s_map"


def test_nagi_regime_fit_reflects_borrowed_atr():
    """Regime fit must be computed from the borrowed ATR, not the
    NAGI_V1_REGIME_FIT (0.5) placeholder that G7 §11.13 pinned CV
    to 0.000.
    """
    # Active tape (ATR 100 pips) -> phase-S map clips to 0.8.
    active_leader = _coord(
        "EURUSD", lo=1.0995, hi=1.1015, direction="long", conv=0.85,
        atr_pips=100.0, h1_swing_pips=200.0,
    )
    other = _coord("EURUSD", lo=1.1000, hi=1.1020, direction="long", conv=0.80)
    nagi, firing, market = _fire_confluence(
        leader_coord=active_leader, other_coord=other,
        leader_conv=0.85, other_conv=0.80,
    )
    p = nagi.intend(market, firing)
    assert p is not None
    assert p.regime_fit == pytest.approx(0.8)

    # Quiet tape (ATR 5 pips) -> clips low to 0.2.
    quiet_leader = _coord(
        "EURUSD", lo=1.0995, hi=1.1015, direction="long", conv=0.85,
        atr_pips=5.0, h1_swing_pips=30.0,
    )
    nagi, firing, market = _fire_confluence(
        leader_coord=quiet_leader, other_coord=other,
        leader_conv=0.85, other_conv=0.80,
    )
    p = nagi.intend(market, firing)
    assert p is not None
    assert p.regime_fit == pytest.approx(0.2)


def test_nagi_regime_fit_defaults_to_neutral_when_leader_unstamped():
    """Bar-less legacy case: leader coord has no atr_pips stamp.
    Borrowed value is None; regime_fit falls back to 0.5. Proposal
    still fires (safe degrade), and rationale keys are present but
    None so downstream cache readers can distinguish "not-yet-wired"
    from "wired but null".
    """
    leader_coord = _coord(
        "EURUSD", lo=1.0995, hi=1.1015, direction="long", conv=0.85,
    )
    other_coord = _coord(
        "EURUSD", lo=1.1000, hi=1.1020, direction="long", conv=0.80,
    )
    nagi, firing, market = _fire_confluence(
        leader_coord=leader_coord, other_coord=other_coord,
        leader_conv=0.85, other_conv=0.80,
    )
    p = nagi.intend(market, firing)
    assert p is not None
    assert p.rationale["atr_pips"] is None
    assert p.rationale["h1_swing_pips"] is None
    assert p.regime_fit == pytest.approx(0.5)


def test_nagi_borrow_dispersion_over_a_range_of_leaders():
    """Across a range of leader ATR/swing stamps, Nagi's borrowed
    ``atr_pips`` and ``h1_swing_pips`` on his proposal rationale
    span the same range -- i.e. once leaders vary, Nagi's F20 inputs
    vary too. This is the dispersion-r2 core promise: Nagi's C5/C6
    CV = 0.000 root cause (constant inputs) is removed.
    """
    stamps = [
        (12.0, 55.0), (22.0, 80.0), (30.0, 120.0),
        (42.0, 160.0), (65.0, 240.0),
    ]
    borrowed_atr: list[float] = []
    borrowed_swing: list[float] = []
    for atr, swing in stamps:
        leader = _coord(
            "EURUSD", lo=1.0995, hi=1.1015, direction="long", conv=0.85,
            atr_pips=atr, h1_swing_pips=swing,
        )
        other = _coord(
            "EURUSD", lo=1.1000, hi=1.1020, direction="long", conv=0.80,
        )
        nagi, firing, market = _fire_confluence(
            leader_coord=leader, other_coord=other,
            leader_conv=0.85, other_conv=0.80,
        )
        p = nagi.intend(market, firing)
        assert p is not None
        borrowed_atr.append(float(p.rationale["atr_pips"]))
        borrowed_swing.append(float(p.rationale["h1_swing_pips"]))
    # Inputs are truthfully varying (necessary condition for downstream
    # C5/C6 CV to move off 0.000).
    assert min(borrowed_atr) < max(borrowed_atr)
    assert min(borrowed_swing) < max(borrowed_swing)
