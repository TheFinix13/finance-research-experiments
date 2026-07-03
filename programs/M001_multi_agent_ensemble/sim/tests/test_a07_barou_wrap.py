"""A7 Barou v1 wrap tests.

Asserts:
  * Barou wraps the production `SupplyDemandAlpha` with `htf_align=None`
    (baseline zone, no D1 gate) on USDCAD.
  * Off-symbol abstention (EURUSD / GBPUSD ticks emit observation-only).
  * Devour mechanic fires when Isagi's prior-tick thought disagrees
    directionally with Barou's at high conviction.
  * Devour DOES NOT fire when Isagi agrees or is silent.
  * Tier-3 RedactedLedger emits NO devour lift (Barou cannot read peer
    thoughts under isolation).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from programs.M001_multi_agent_ensemble.sim._cross_repo import (
    production_repo_available,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import (
    FullLedger, RedactedLedger,
)
from programs.M001_multi_agent_ensemble.sim.core.types import (
    SCHEMA_VERSION,
    Coordinate, MarketState, Thought,
)


pytestmark = pytest.mark.skipif(
    not production_repo_available(),
    reason="A7 Barou wraps production zone_alpha; requires prod repo on path",
)


def _build_synthetic_usdcad_bars(n: int = 600):
    """USDCAD synthetic series with a clean DOWN impulse + pullback into
    the resulting supply zone -- the baseline `zone` cell fires on the
    pullback close.
    """
    from agent.types import Bar, Timeframe
    base = datetime(2020, 1, 1, tzinfo=timezone.utc)
    bars: list[Bar] = []
    price = 1.3000
    # Slow uptrend
    for i in range(250):
        new_price = price + 0.00012
        bars.append(Bar(
            time=base + timedelta(hours=4 * i),
            open=price,
            high=max(price, new_price) + 0.00020,
            low=min(price, new_price) - 0.00015,
            close=new_price,
            volume=100.0,
            timeframe=Timeframe.H4,
        ))
        price = new_price
    impulse_top = price
    # Sharp DOWN impulse
    for i in range(10):
        new_price = price - 0.00250
        bars.append(Bar(
            time=base + timedelta(hours=4 * (250 + i)),
            open=price,
            high=price + 0.00020,
            low=new_price - 0.00020,
            close=new_price,
            volume=300.0,
            timeframe=Timeframe.H4,
        ))
        price = new_price
    # Pullback into supply zone
    pullback_target = impulse_top - 0.00010
    n_pullback = 60
    for i in range(n_pullback):
        delta = (pullback_target - price) / max(n_pullback - i, 1)
        new_price = price + delta
        bars.append(Bar(
            time=base + timedelta(hours=4 * (250 + 10 + i)),
            open=price,
            high=new_price + 0.00010,
            low=price - 0.00005,
            close=new_price,
            volume=120.0,
            timeframe=Timeframe.H4,
        ))
        price = new_price
    # Chop runway
    chop = max(60, n - len(bars))
    for i in range(chop):
        new_price = price + (-0.00020 if i % 3 == 0 else 0.00010)
        bars.append(Bar(
            time=base + timedelta(hours=4 * len(bars)),
            open=price,
            high=max(price, new_price) + 0.00020,
            low=min(price, new_price) - 0.00020,
            close=new_price,
            volume=100.0,
            timeframe=Timeframe.H4,
        ))
        price = new_price
    return bars


def _bar_to_market(bar, tick_id: int, symbol: str = "USDCAD") -> MarketState:
    return MarketState(
        tick_id=tick_id,
        symbol=symbol,
        timeframe=bar.timeframe.value,
        as_of=bar.time,
        open=float(bar.open), high=float(bar.high),
        low=float(bar.low), close=float(bar.close),
        volume=float(bar.volume),
    )


def _make_barou():
    from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import (
        A7BarouV1,
    )
    return A7BarouV1()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_barou_abstains_on_eurusd_observe_and_intend():
    barou = _make_barou()
    market = MarketState(
        tick_id=0, symbol="EURUSD", timeframe="H4",
        as_of=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=1.1, high=1.11, low=1.09, close=1.105, volume=100.0,
    )
    ledger = FullLedger()
    t = barou.observe(market, ledger)
    assert t.coordinate is None
    assert "barou_abstain" in t.tags
    assert "barou_abstain_symbol" in t.tags
    assert barou.intend(market, t) is None


def test_barou_abstains_on_gbpusd():
    barou = _make_barou()
    market = MarketState(
        tick_id=0, symbol="GBPUSD", timeframe="H4",
        as_of=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=1.3, high=1.31, low=1.29, close=1.305, volume=100.0,
    )
    ledger = FullLedger()
    t = barou.observe(market, ledger)
    assert "barou_abstain" in t.tags
    assert barou.intend(market, t) is None


def test_barou_wraps_baseline_zone_no_d1_gate():
    """The production SupplyDemandAlpha with `htf_align=None` is the
    baseline cell (no D1 trend gate). Confirm Barou's inner alpha emits
    the same signal as a raw baseline-zone SupplyDemandAlpha.
    """
    from agent.alphas.base import AlphaContext
    from agent.alphas.concepts.zone_alpha import SupplyDemandAlpha
    from agent.config import load_config
    from agent.rules.engine import precompute

    bars = _build_synthetic_usdcad_bars(600)
    cfg = load_config()
    raw = SupplyDemandAlpha(cfg=cfg, htf_align=None, target_rr=1.5)
    ctx = precompute(bars, cfg)
    actx = AlphaContext(bars=bars, ctx=ctx, cfg=cfg)

    raw_signals: dict[int, object] = {}
    for i in range(200, len(bars) - 1):
        s = raw.signal(actx, i)
        if s is not None:
            raw_signals[i] = s

    if not raw_signals:
        pytest.skip("synthetic USDCAD series produced no baseline zone signals")

    barou = _make_barou()
    barou.prepare("USDCAD", bars)

    for i in list(raw_signals.keys())[:5]:
        sig = barou.inner_signal_at("USDCAD", i)
        raw_sig = raw_signals[i]
        assert sig is not None
        assert sig.direction.value == raw_sig.direction.value
        assert sig.entry == pytest.approx(float(raw_sig.entry))
        assert sig.stop == pytest.approx(float(raw_sig.stop))
        assert sig.take_profit == pytest.approx(float(raw_sig.take_profit))


def test_barou_devour_fires_on_isagi_opposite_high_conviction():
    """Set up a USDCAD signal tick where Barou fires LONG and Isagi has
    a prior-tick SHORT thought at conviction >= 0.7. Devour lift should
    add +0.10 to Barou's conviction.
    """
    bars = _build_synthetic_usdcad_bars(600)
    barou = _make_barou()
    barou.prepare("USDCAD", bars)

    # Find the first bar index where Barou's inner alpha fires.
    fire_idx = None
    fire_direction = None
    for i in range(200, len(bars) - 1):
        sig = barou.inner_signal_at("USDCAD", i)
        if sig is not None:
            fire_idx = i
            fire_direction = sig.direction.value
            break
    if fire_idx is None:
        pytest.skip("synthetic series produced no Barou signal")

    # Build an Isagi thought at tick fire_idx - 1 with OPPOSITE direction.
    fire_bar = bars[fire_idx]
    isagi_direction = "short" if fire_direction == "long" else "long"
    isagi_coord = Coordinate(
        agent_id="isagi_yoichi", symbol="USDCAD",
        price_lo=float(fire_bar.close) - 0.0010,
        price_hi=float(fire_bar.close) + 0.0010,
        time_start=fire_bar.time - timedelta(hours=4),
        time_end=fire_bar.time + timedelta(hours=20),
        vol_band=(0.5, 2.0),
        regime_predicate="D1_trend_against",
        expected_strength=0.85, direction_bias=isagi_direction,
        rationale={
            "entry": float(fire_bar.close),
            "stop": float(fire_bar.close) - 0.0010,
            "take_profit": float(fire_bar.close) + 0.0015,
        },
    )
    isagi_thought = Thought(
        schema_version=SCHEMA_VERSION,
        agent_id="isagi_yoichi", tick_id=fire_idx - 1,
        timestamp=bars[fire_idx - 1].time, symbol="USDCAD",
        narrative="prior isagi",
        tags=["zone_d1_against", "htf_against"],
        confidence_in_thought=0.85,
        expected_action=f"{isagi_direction}_on_H4_close",
        coordinate=isagi_coord,
        decision_horizon=bars[fire_idx - 1].time,
        ttl_ticks=6, references=[],
    )
    ledger = FullLedger()
    ledger.append(isagi_thought)

    market = _bar_to_market(fire_bar, fire_idx)
    t = barou.observe(market, ledger)
    assert t.coordinate is not None
    assert "barou_devour_applied" in t.tags
    assert "barou_devour_candidate" in t.tags  # final conv >= 0.7


def test_barou_devour_skipped_on_isagi_agreement():
    bars = _build_synthetic_usdcad_bars(600)
    barou = _make_barou()
    barou.prepare("USDCAD", bars)

    fire_idx = None
    fire_direction = None
    for i in range(200, len(bars) - 1):
        sig = barou.inner_signal_at("USDCAD", i)
        if sig is not None:
            fire_idx = i
            fire_direction = sig.direction.value
            break
    if fire_idx is None:
        pytest.skip("synthetic series produced no Barou signal")

    fire_bar = bars[fire_idx]
    isagi_coord = Coordinate(
        agent_id="isagi_yoichi", symbol="USDCAD",
        price_lo=float(fire_bar.close) - 0.0010,
        price_hi=float(fire_bar.close) + 0.0010,
        time_start=fire_bar.time - timedelta(hours=4),
        time_end=fire_bar.time + timedelta(hours=20),
        vol_band=(0.5, 2.0),
        regime_predicate="D1_trend_against",
        expected_strength=0.85, direction_bias=fire_direction,
        rationale={
            "entry": float(fire_bar.close),
            "stop": float(fire_bar.close) - 0.0010,
            "take_profit": float(fire_bar.close) + 0.0015,
        },
    )
    isagi_thought = Thought(
        schema_version=SCHEMA_VERSION,
        agent_id="isagi_yoichi", tick_id=fire_idx - 1,
        timestamp=bars[fire_idx - 1].time, symbol="USDCAD",
        narrative="prior isagi",
        tags=["zone_d1_against", "htf_against"],
        confidence_in_thought=0.85,
        expected_action=f"{fire_direction}_on_H4_close",
        coordinate=isagi_coord,
        decision_horizon=bars[fire_idx - 1].time,
        ttl_ticks=6, references=[],
    )
    ledger = FullLedger()
    ledger.append(isagi_thought)

    market = _bar_to_market(fire_bar, fire_idx)
    t = barou.observe(market, ledger)
    assert t.coordinate is not None
    assert "barou_devour_applied" not in t.tags


def test_barou_redacted_ledger_blocks_devour():
    """Tier-3 isolation -- RedactedLedger filters reads to Barou's own
    agent_id, so Isagi's prior thought is invisible. Devour must NOT
    fire under isolation.
    """
    bars = _build_synthetic_usdcad_bars(600)
    barou = _make_barou()
    barou.prepare("USDCAD", bars)

    fire_idx = None
    fire_direction = None
    for i in range(200, len(bars) - 1):
        sig = barou.inner_signal_at("USDCAD", i)
        if sig is not None:
            fire_idx = i
            fire_direction = sig.direction.value
            break
    if fire_idx is None:
        pytest.skip("synthetic series produced no Barou signal")

    fire_bar = bars[fire_idx]
    opposite = "short" if fire_direction == "long" else "long"
    isagi_coord = Coordinate(
        agent_id="isagi_yoichi", symbol="USDCAD",
        price_lo=float(fire_bar.close) - 0.0010,
        price_hi=float(fire_bar.close) + 0.0010,
        time_start=fire_bar.time - timedelta(hours=4),
        time_end=fire_bar.time + timedelta(hours=20),
        vol_band=(0.5, 2.0),
        regime_predicate="D1_trend_against",
        expected_strength=0.85, direction_bias=opposite,
        rationale={
            "entry": float(fire_bar.close),
            "stop": float(fire_bar.close) - 0.0010,
            "take_profit": float(fire_bar.close) + 0.0015,
        },
    )
    isagi_thought = Thought(
        schema_version=SCHEMA_VERSION,
        agent_id="isagi_yoichi", tick_id=fire_idx - 1,
        timestamp=bars[fire_idx - 1].time, symbol="USDCAD",
        narrative="prior isagi",
        tags=["zone_d1_against", "htf_against"],
        confidence_in_thought=0.85,
        expected_action=f"{opposite}_on_H4_close",
        coordinate=isagi_coord,
        decision_horizon=bars[fire_idx - 1].time,
        ttl_ticks=6, references=[],
    )
    inner = FullLedger()
    inner.append(isagi_thought)
    redacted = RedactedLedger(agent_id=barou.agent_id, source=inner)

    market = _bar_to_market(fire_bar, fire_idx)
    t = barou.observe(market, redacted)
    assert "barou_devour_applied" not in t.tags


# ---------------------------------------------------------------------------
# Phase V-b: solo-king clarification (2026-07-02)
# ---------------------------------------------------------------------------

class TestPhaseVB_BarouSoloKingSpecialist:
    """Barou stamps ``rationale["_effective_tier"] = 1`` when his
    devour-lift fired in observe() (his direction opposes Isagi's
    active USDCAD position at conviction >= 0.7). Non-devour proposals
    stay tier-2 and continue to lose to Bachira on raw conviction.
    """

    def test_specialist_bit_fires_when_devour_active(self):
        """Reuses the devour-fires fixture: builds a USDCAD signal +
        opposite-direction Isagi thought at 0.85 conviction on tick-1.
        Barou's observe() stamps devour_applied; intend() must stamp
        the specialist bit + effective_tier=1.
        """
        bars = _build_synthetic_usdcad_bars(600)
        barou = _make_barou()
        barou.prepare("USDCAD", bars)
        fire_idx = None
        fire_direction = None
        for i in range(200, len(bars) - 1):
            sig = barou.inner_signal_at("USDCAD", i)
            if sig is not None:
                fire_idx = i
                fire_direction = sig.direction.value
                break
        if fire_idx is None:
            pytest.skip("synthetic series produced no Barou signal")
        fire_bar = bars[fire_idx]
        isagi_direction = "short" if fire_direction == "long" else "long"
        isagi_coord = Coordinate(
            agent_id="isagi_yoichi", symbol="USDCAD",
            price_lo=float(fire_bar.close) - 0.0010,
            price_hi=float(fire_bar.close) + 0.0010,
            time_start=fire_bar.time - timedelta(hours=4),
            time_end=fire_bar.time + timedelta(hours=20),
            vol_band=(0.5, 2.0),
            regime_predicate="D1_trend_against",
            expected_strength=0.85, direction_bias=isagi_direction,
            rationale={
                "entry": float(fire_bar.close),
                "stop": float(fire_bar.close) - 0.0010,
                "take_profit": float(fire_bar.close) + 0.0015,
            },
        )
        isagi_thought = Thought(
            schema_version=SCHEMA_VERSION,
            agent_id="isagi_yoichi", tick_id=fire_idx - 1,
            timestamp=bars[fire_idx - 1].time, symbol="USDCAD",
            narrative="prior isagi",
            tags=["zone_d1_against", "htf_against"],
            confidence_in_thought=0.85,
            expected_action=f"{isagi_direction}_on_H4_close",
            coordinate=isagi_coord,
            decision_horizon=bars[fire_idx - 1].time,
            ttl_ticks=6, references=[],
        )
        ledger = FullLedger()
        ledger.append(isagi_thought)
        market = _bar_to_market(fire_bar, fire_idx)
        t = barou.observe(market, ledger)
        assert "barou_devour_applied" in t.tags   # sanity
        p = barou.intend(market, t)
        assert p is not None
        r = p.rationale
        assert r["devour_applied"] is True
        assert r["barou_solo_king_specialist"] is True
        # Phase V-b null result: specialist bit is stamped for audit
        # but NO tier override is applied (see PROTOCOL sec 11.9-
        # postmortem). Regression guard: the override must be absent.
        assert "_effective_tier" not in r, (
            "Phase V-b null result: specialist bit is diagnostic; "
            "tier promotion is reverted"
        )

    def test_specialist_bit_absent_when_no_devour(self):
        """Signal fires but devour is skipped -- either because Isagi
        agrees (test_barou_devour_skipped_on_isagi_agreement) or
        because there's no Isagi thought. Barou stays tier-2.
        """
        bars = _build_synthetic_usdcad_bars(600)
        barou = _make_barou()
        barou.prepare("USDCAD", bars)
        fire_idx = None
        for i in range(200, len(bars) - 1):
            sig = barou.inner_signal_at("USDCAD", i)
            if sig is not None:
                fire_idx = i
                break
        if fire_idx is None:
            pytest.skip("synthetic series produced no Barou signal")
        fire_bar = bars[fire_idx]
        # Empty ledger: no Isagi thought -> no devour.
        market = _bar_to_market(fire_bar, fire_idx)
        t = barou.observe(market, FullLedger())
        assert "barou_devour_applied" not in t.tags   # sanity
        p = barou.intend(market, t)
        assert p is not None
        r = p.rationale
        assert r["devour_applied"] is False
        assert r["barou_solo_king_specialist"] is False
        assert "_effective_tier" not in r, (
            "Non-devour Barou proposal must stay at agent_tier (no override)"
        )

    def test_specialist_bit_is_diagnostic_not_routing(self):
        """Regression guard for the Phase V-b null-result configuration
        (see PROTOCOL sec 11.9-postmortem 2026-07-02): even when the
        devour lift fires, the rationale must NOT contain any tier
        override, so the aggregator's routing decision is unchanged.
        """
        bars = _build_synthetic_usdcad_bars(600)
        barou = _make_barou()
        barou.prepare("USDCAD", bars)
        fire_idx = None
        fire_direction = None
        for i in range(200, len(bars) - 1):
            sig = barou.inner_signal_at("USDCAD", i)
            if sig is not None:
                fire_idx = i
                fire_direction = sig.direction.value
                break
        if fire_idx is None:
            pytest.skip("synthetic series produced no Barou signal")
        fire_bar = bars[fire_idx]
        isagi_direction = "short" if fire_direction == "long" else "long"
        isagi_coord = Coordinate(
            agent_id="isagi_yoichi", symbol="USDCAD",
            price_lo=float(fire_bar.close) - 0.0010,
            price_hi=float(fire_bar.close) + 0.0010,
            time_start=fire_bar.time - timedelta(hours=4),
            time_end=fire_bar.time + timedelta(hours=20),
            vol_band=(0.5, 2.0),
            regime_predicate="D1_trend_against",
            expected_strength=0.85, direction_bias=isagi_direction,
            rationale={
                "entry": float(fire_bar.close),
                "stop": float(fire_bar.close) - 0.0010,
                "take_profit": float(fire_bar.close) + 0.0015,
            },
        )
        isagi_thought = Thought(
            schema_version=SCHEMA_VERSION,
            agent_id="isagi_yoichi", tick_id=fire_idx - 1,
            timestamp=bars[fire_idx - 1].time, symbol="USDCAD",
            narrative="prior isagi", tags=["zone_d1_against"],
            confidence_in_thought=0.85,
            expected_action=f"{isagi_direction}_on_H4_close",
            coordinate=isagi_coord,
            decision_horizon=bars[fire_idx - 1].time,
            ttl_ticks=6, references=[],
        )
        ledger = FullLedger()
        ledger.append(isagi_thought)
        market = _bar_to_market(fire_bar, fire_idx)
        t = barou.observe(market, ledger)
        p = barou.intend(market, t)
        assert p is not None
        keys_that_would_promote_tier = [
            k for k in p.rationale
            if k == "_effective_tier"
        ]
        assert keys_that_would_promote_tier == [], (
            "Phase V-b null result: rationale must NOT contain tier "
            "override keys under the reverted mechanic"
        )
