"""Friction model unit tests."""
from __future__ import annotations

from programs.M001_multi_agent_ensemble.sim.core.friction import (
    FrictionConfig,
    simulate_fill,
    slippage_from_atr,
    spread_from_bar,
)
from programs.M001_multi_agent_ensemble.sim.tests.conftest import make_bar


def test_spread_from_bar_uses_bid_ask_extremes():
    bar = make_bar(tick_id=0, bid_low=1.0890, ask_high=1.0915)
    s = spread_from_bar(bar)
    # ask_high - bid_low
    assert abs(s - 0.0025) < 1e-9


def test_spread_from_bar_zero_when_unknown():
    bar = make_bar(tick_id=0, bid_low=None, ask_high=None)
    assert spread_from_bar(bar) == 0.0


def test_slippage_proportional_to_atr():
    s = slippage_from_atr(atr=0.0010, k=0.05)
    assert abs(s - 0.00005) < 1e-12
    # Sign convention is "magnitude" — caller applies the sign.
    s2 = slippage_from_atr(atr=0.0020, k=0.05)
    assert s2 == 2 * s


def test_slippage_zero_for_bad_atr():
    assert slippage_from_atr(atr=0.0) == 0.0
    assert slippage_from_atr(atr=float("nan")) == 0.0
    assert slippage_from_atr(atr=-1.0) == 0.0


def test_simulate_fill_is_deterministic():
    """Same inputs -> same FillResult."""
    fr1 = simulate_fill(
        agent_id="isagi_yoichi", tick_id=42, intended_size=0.5,
        intended_price=1.0900, atr=0.0010, direction=+1,
    )
    fr2 = simulate_fill(
        agent_id="isagi_yoichi", tick_id=42, intended_size=0.5,
        intended_price=1.0900, atr=0.0010, direction=+1,
    )
    assert fr1 == fr2


def test_simulate_fill_applies_adverse_slippage_long():
    """Long order pays the slippage on the way up."""
    fr = simulate_fill(
        agent_id="isagi_yoichi", tick_id=42, intended_size=0.1,
        intended_price=1.0900, atr=0.0010, direction=+1,
        config=FrictionConfig(reject_prob=0.0),  # guarantee no reject
    )
    assert fr.status == "filled"
    # Long pays +k*ATR = +0.05 * 0.0010 = +0.00005 vs intended.
    assert abs(fr.fill_price - 1.0900 - 0.00005) < 1e-9


def test_simulate_fill_applies_adverse_slippage_short():
    fr = simulate_fill(
        agent_id="isagi_yoichi", tick_id=42, intended_size=0.1,
        intended_price=1.0900, atr=0.0010, direction=-1,
        config=FrictionConfig(reject_prob=0.0),
    )
    assert fr.status == "filled"
    assert abs(fr.fill_price - 1.0900 + 0.00005) < 1e-9


def test_partial_fill_only_above_threshold():
    """Below the 1.0-lot threshold, partials never fire."""
    fr = simulate_fill(
        agent_id="agent", tick_id=0, intended_size=0.5,
        intended_price=1.0900, atr=0.0010, direction=+1,
        config=FrictionConfig(
            reject_prob=0.0, partial_fill_prob=1.0,
            partial_lot_threshold=1.0,
        ),
    )
    # Even with partial_prob=1.0, size 0.5 is below threshold -> full.
    assert fr.status == "filled"
    assert fr.filled_size == 0.5


def test_partial_fill_haircut_above_threshold():
    fr = simulate_fill(
        agent_id="agent", tick_id=0, intended_size=2.0,
        intended_price=1.0900, atr=0.0010, direction=+1,
        config=FrictionConfig(
            reject_prob=0.0, partial_fill_prob=1.0,
            partial_fill_haircut=0.5, partial_lot_threshold=1.0,
        ),
    )
    assert fr.status == "partial"
    assert fr.filled_size == 1.0


def test_reject_with_certain_probability():
    fr = simulate_fill(
        agent_id="agent", tick_id=0, intended_size=0.1,
        intended_price=1.0900, atr=0.0010, direction=+1,
        config=FrictionConfig(reject_prob=1.0),
    )
    assert fr.status == "rejected"
    assert fr.filled_size == 0.0


def test_default_latency_is_250ms():
    fr = simulate_fill(
        agent_id="agent", tick_id=0, intended_size=0.1,
        intended_price=1.0900, atr=0.0010, direction=+1,
    )
    # Architecture section 1.8 default: 250 ms latency.
    assert fr.latency_ms == 250
