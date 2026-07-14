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

    Phase Y (2026-07-14): this is the LEGACY v1 weapon, retained behind
    ``weapon_v13=False``. The v1.3 weapon is covered by
    ``test_a07_barou_v13_weapon.py``.
    """
    from agent.alphas.base import AlphaContext
    from agent.alphas.concepts.zone_alpha import SupplyDemandAlpha
    from agent.config import load_config
    from agent.rules.engine import precompute
    from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import (
        A7BarouV1,
    )

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

    barou = A7BarouV1(weapon_v13=False)
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


# ---------------------------------------------------------------------------
# Phase W-barou v1.1 (2026-07-03): H1 lone-conviction claim
# ---------------------------------------------------------------------------

class TestPhaseW_BarouLoneConvictionClaim:
    """H1: Barou's ``intend()`` adds `BAROU_V1_1_LONE_CONVICTION_LIFT`
    to conviction when Bachira did NOT publish a same-symbol
    same-direction Thought at the tick barrier. When Bachira DID publish
    same-direction, H1 skips and the existing devour path decides
    conviction unchanged.

    See ``experiments/phase_w_barou/PROTOCOL.md`` sec 3 for the
    decision table.
    """

    def _fire_index_and_signal(self, barou, bars):
        for i in range(200, len(bars) - 1):
            sig = barou.inner_signal_at("USDCAD", i)
            if sig is not None:
                return i, sig
        return None, None

    def _make_workspace_snapshot(
        self, *, tick_id, as_of, peer_thoughts,
    ):
        from programs.M001_multi_agent_ensemble.sim.core.reasoning_workspace import (
            WorkspaceSnapshot,
        )
        return WorkspaceSnapshot(
            thoughts=tuple(peer_thoughts),
            as_of=as_of,
            current_tick=tick_id,
        )

    def _make_bachira_thought(
        self, *, tick_id, as_of, direction, symbol="USDCAD",
    ):
        coord = Coordinate(
            agent_id="bachira_meguru", symbol=symbol,
            price_lo=1.29, price_hi=1.31,
            time_start=as_of - timedelta(hours=4),
            time_end=as_of + timedelta(hours=20),
            vol_band=(0.5, 2.0),
            regime_predicate="test_regime",
            expected_strength=0.70, direction_bias=direction,
            rationale={"entry": 1.30, "stop": 1.29, "take_profit": 1.32},
        )
        return Thought(
            schema_version=SCHEMA_VERSION,
            agent_id="bachira_meguru",
            tick_id=tick_id, timestamp=as_of, symbol=symbol,
            narrative=f"[bachira test] {direction}",
            tags=["bachira_test"], confidence_in_thought=0.70,
            expected_action=f"{direction}_on_H4_close_USDCAD",
            coordinate=coord,
            decision_horizon=as_of,
            ttl_ticks=6, references=[],
        )

    def test_h1_fires_when_no_bachira_read(self):
        """workspace snapshot has NO Bachira thought at all -> H1 fires
        (genuine solo read). Conviction bumped by LONE_CONVICTION_LIFT.
        """
        from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import (
            BAROU_V1_1_LONE_CONVICTION_LIFT,
        )
        bars = _build_synthetic_usdcad_bars(600)
        barou = _make_barou()
        barou.prepare("USDCAD", bars)
        fire_idx, sig = self._fire_index_and_signal(barou, bars)
        if fire_idx is None:
            pytest.skip("synthetic series produced no Barou signal")
        fire_bar = bars[fire_idx]
        market = _bar_to_market(fire_bar, fire_idx)
        # Ledger empty, no devour. Workspace snapshot has NO bachira.
        t = barou.observe(market, FullLedger())
        base_conv = float(t.confidence_in_thought)
        ws = self._make_workspace_snapshot(
            tick_id=fire_idx, as_of=fire_bar.time, peer_thoughts=[],
        )
        p = barou.intend(market, t, workspace=ws)
        assert p is not None
        r = p.rationale
        assert r["barou_lone_conviction_claim"] is True
        assert r["barou_lone_conviction_lift_applied"] == pytest.approx(
            BAROU_V1_1_LONE_CONVICTION_LIFT, abs=1e-9,
        )
        assert r["barou_v1_1_bachira_read_present"] is False
        assert r["_yield_reason"] == "peer_did_not_read_this_setup"
        # Final conviction must be raised by the lift (capped at CAP).
        expected_conv = min(1.0, base_conv + BAROU_V1_1_LONE_CONVICTION_LIFT)
        assert p.conviction == pytest.approx(expected_conv, abs=1e-9)

    def test_h1_fires_when_bachira_read_is_opposite_direction(self):
        """Bachira reads OPPOSITE direction -> Barou's read is a
        counter-conviction opportunity, treated as lone-conviction.
        """
        from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import (
            BAROU_V1_1_LONE_CONVICTION_LIFT,
        )
        bars = _build_synthetic_usdcad_bars(600)
        barou = _make_barou()
        barou.prepare("USDCAD", bars)
        fire_idx, sig = self._fire_index_and_signal(barou, bars)
        if fire_idx is None:
            pytest.skip("synthetic series produced no Barou signal")
        fire_bar = bars[fire_idx]
        market = _bar_to_market(fire_bar, fire_idx)
        t = barou.observe(market, FullLedger())
        base_conv = float(t.confidence_in_thought)
        barou_dir = sig.direction.value
        bachira_dir = "short" if barou_dir == "long" else "long"
        ws = self._make_workspace_snapshot(
            tick_id=fire_idx, as_of=fire_bar.time,
            peer_thoughts=[self._make_bachira_thought(
                tick_id=fire_idx, as_of=fire_bar.time,
                direction=bachira_dir,
            )],
        )
        p = barou.intend(market, t, workspace=ws)
        assert p is not None
        r = p.rationale
        assert r["barou_lone_conviction_claim"] is True
        assert r["barou_lone_conviction_lift_applied"] == pytest.approx(
            BAROU_V1_1_LONE_CONVICTION_LIFT, abs=1e-9,
        )
        assert r["barou_v1_1_bachira_read_present"] is True
        assert r["barou_v1_1_bachira_same_direction"] is False
        assert r["_yield_reason"] == "peer_did_not_read_this_setup"
        expected_conv = min(1.0, base_conv + BAROU_V1_1_LONE_CONVICTION_LIFT)
        assert p.conviction == pytest.approx(expected_conv, abs=1e-9)

    def test_h1_skips_when_bachira_read_is_same_direction(self):
        """Bachira reads SAME direction -> H1 skips (existing devour
        path handles it). Conviction unchanged from observe()'s output.
        """
        bars = _build_synthetic_usdcad_bars(600)
        barou = _make_barou()
        barou.prepare("USDCAD", bars)
        fire_idx, sig = self._fire_index_and_signal(barou, bars)
        if fire_idx is None:
            pytest.skip("synthetic series produced no Barou signal")
        fire_bar = bars[fire_idx]
        market = _bar_to_market(fire_bar, fire_idx)
        t = barou.observe(market, FullLedger())
        base_conv = float(t.confidence_in_thought)
        barou_dir = sig.direction.value
        # Bachira matches Barou's direction -- H1 must skip.
        ws = self._make_workspace_snapshot(
            tick_id=fire_idx, as_of=fire_bar.time,
            peer_thoughts=[self._make_bachira_thought(
                tick_id=fire_idx, as_of=fire_bar.time,
                direction=barou_dir,
            )],
        )
        p = barou.intend(market, t, workspace=ws)
        assert p is not None
        r = p.rationale
        assert r["barou_lone_conviction_claim"] is False
        assert r["barou_lone_conviction_lift_applied"] == 0.0
        assert r["barou_v1_1_bachira_read_present"] is True
        assert r["barou_v1_1_bachira_same_direction"] is True
        assert r["_yield_reason"] == "peer_claimed_slot_no_lift"
        assert p.conviction == pytest.approx(base_conv, abs=1e-9)

    def test_h1_default_when_workspace_unavailable(self):
        """No workspace snapshot passed -> yield_reason=workspace_unavailable
        and no lift applied. Preserves backward-compat with contexts
        that don't wire F21.
        """
        bars = _build_synthetic_usdcad_bars(600)
        barou = _make_barou()
        barou.prepare("USDCAD", bars)
        fire_idx, _ = self._fire_index_and_signal(barou, bars)
        if fire_idx is None:
            pytest.skip("synthetic series produced no Barou signal")
        fire_bar = bars[fire_idx]
        market = _bar_to_market(fire_bar, fire_idx)
        t = barou.observe(market, FullLedger())
        p = barou.intend(market, t, workspace=None)
        assert p is not None
        r = p.rationale
        assert r["barou_lone_conviction_claim"] is False
        assert r["barou_lone_conviction_lift_applied"] == 0.0
        assert r["barou_workspace_snapshot_ok"] is False
        assert r["_yield_reason"] == "workspace_unavailable"

    def test_h1_stacks_on_devour_when_both_fire(self):
        """H1 and existing devour mechanic are ORTHOGONAL -- when both
        fire, the conviction lift stacks (capped at 1.0). Interaction
        is explicitly documented in PROTOCOL sec 3.
        """
        from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import (
            BAROU_V1_1_LONE_CONVICTION_LIFT, BAROU_V1_DEVOUR_LIFT,
        )
        bars = _build_synthetic_usdcad_bars(600)
        barou = _make_barou()
        barou.prepare("USDCAD", bars)
        fire_idx, sig = self._fire_index_and_signal(barou, bars)
        if fire_idx is None:
            pytest.skip("synthetic series produced no Barou signal")
        fire_bar = bars[fire_idx]
        fire_direction = sig.direction.value
        # Isagi disagrees at high conviction (devour will fire).
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
        # Workspace has NO bachira -> H1 fires. Ledger has isagi
        # disagreeing -> devour fires (in observe()).
        t = barou.observe(market, ledger)
        assert "barou_devour_applied" in t.tags
        base_conv_after_devour = float(t.confidence_in_thought)
        ws = self._make_workspace_snapshot(
            tick_id=fire_idx, as_of=fire_bar.time, peer_thoughts=[],
        )
        p = barou.intend(market, t, workspace=ws)
        assert p is not None
        r = p.rationale
        assert r["devour_applied"] is True
        assert r["barou_lone_conviction_claim"] is True
        # Final conviction = base_after_devour + H1 lift, capped at 1.0.
        expected_conv = min(
            1.0,
            base_conv_after_devour + BAROU_V1_1_LONE_CONVICTION_LIFT,
        )
        assert p.conviction == pytest.approx(expected_conv, abs=1e-9)


# ---------------------------------------------------------------------------
# Phase W-barou v1.2 (2026-07-06): H2 continuation-entry
# (experiments/phase_w_barou/PROTOCOL_v1.2.md sec 3)
# ---------------------------------------------------------------------------

class TestPhaseW12_AnchorGeometryPure:
    """Deterministic coverage of the locked H2 arithmetic
    (PROTOCOL_v1.2.md sec 3) independent of the synthetic bar series."""

    def _geom(self, **kw):
        from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import (
            continuation_anchor_geometry,
        )
        defaults = dict(
            entry=1.3000, own_stop=1.2970, own_tp=1.3045,
            direction="long", target_rr=1.5,
        )
        defaults.update(kw)
        return continuation_anchor_geometry(**defaults)

    def test_tighter_anchor_fires_and_rederives_tp(self):
        stop, tp, source, fired = self._geom(bachira_stop=1.2988)  # 12 pips
        assert fired and source == "bachira_anchor"
        assert stop == pytest.approx(1.2988, abs=1e-12)
        assert tp == pytest.approx(1.3000 + 1.5 * 0.0012, abs=1e-12)

    def test_floor_clamps_ultra_tight_anchor(self):
        from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import (
            BAROU_V1_2_CONTINUATION_MIN_STOP_PIPS,
        )
        stop, tp, source, fired = self._geom(bachira_stop=1.2999)  # 1 pip
        assert fired and source == "bachira_anchor"
        floor = BAROU_V1_2_CONTINUATION_MIN_STOP_PIPS * 0.0001
        assert stop == pytest.approx(1.3000 - floor, abs=1e-12)
        assert tp == pytest.approx(1.3000 + 1.5 * floor, abs=1e-12)

    def test_wider_anchor_falls_through_to_own(self):
        stop, tp, source, fired = self._geom(bachira_stop=1.2950)  # 50 pips
        assert not fired and source == "own"
        assert stop == pytest.approx(1.2970, abs=1e-12)
        assert tp == pytest.approx(1.3045, abs=1e-12)

    def test_wrong_side_anchor_is_invalid(self):
        stop, tp, source, fired = self._geom(bachira_stop=1.3010)
        assert not fired and source == "invalid_anchor"
        assert stop == pytest.approx(1.2970, abs=1e-12)

    def test_short_direction_mirror(self):
        stop, tp, source, fired = self._geom(
            entry=1.3000, own_stop=1.3030, own_tp=1.2955,
            direction="short", bachira_stop=1.3012,
        )
        assert fired and source == "bachira_anchor"
        assert stop == pytest.approx(1.3012, abs=1e-12)
        assert tp == pytest.approx(1.3000 - 1.5 * 0.0012, abs=1e-12)


class TestPhaseW12_ContinuationEntry:
    """H2: when Bachira published a SAME-direction thought and the
    mechanic is explicitly enabled, Barou anchors his stop to Bachira's
    published structural stop when tighter (floor 6.6 pips), re-derives
    TP at RR 1.5, and stamps the audit trail. Disabled (default) must
    be byte-identical to v1.1 behaviour.
    """

    def _fire(self, barou, bars):
        for i in range(200, len(bars) - 1):
            sig = barou.inner_signal_at("USDCAD", i)
            if sig is not None:
                return i, sig
        pytest.skip("synthetic series produced no Barou signal")

    def _make_bachira_thought_with_stop(
        self, *, tick_id, as_of, direction, stop, symbol="USDCAD",
    ):
        coord = Coordinate(
            agent_id="bachira_meguru", symbol=symbol,
            price_lo=1.29, price_hi=1.31,
            time_start=as_of - timedelta(hours=4),
            time_end=as_of + timedelta(hours=20),
            vol_band=(0.5, 2.0),
            regime_predicate="test_regime",
            expected_strength=0.70, direction_bias=direction,
            rationale={"entry": 1.30, "stop": stop, "take_profit": 1.32},
        )
        return Thought(
            schema_version=SCHEMA_VERSION,
            agent_id="bachira_meguru",
            tick_id=tick_id, timestamp=as_of, symbol=symbol,
            narrative=f"[bachira test] {direction}",
            tags=["bachira_test"], confidence_in_thought=0.70,
            expected_action=f"{direction}_on_H4_close_USDCAD",
            coordinate=coord,
            decision_horizon=as_of,
            ttl_ticks=6, references=[],
        )

    def _snapshot(self, *, tick_id, as_of, peer_thoughts):
        from programs.M001_multi_agent_ensemble.sim.core.reasoning_workspace import (
            WorkspaceSnapshot,
        )
        return WorkspaceSnapshot(
            thoughts=tuple(peer_thoughts),
            as_of=as_of,
            current_tick=tick_id,
        )

    def _run_same_dir_intend(self, *, enabled: bool, bachira_stop_fn):
        """Drive one same-direction intend(); bachira_stop_fn(sig, sign)
        returns the stop price to publish for Bachira."""
        from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import (
            A7BarouV1,
        )
        bars = _build_synthetic_usdcad_bars(600)
        barou = A7BarouV1(continuation_entry_enabled=enabled)
        barou.prepare("USDCAD", bars)
        fire_idx, sig = self._fire(barou, bars)
        fire_bar = bars[fire_idx]
        market = _bar_to_market(fire_bar, fire_idx)
        t = barou.observe(market, FullLedger())
        direction = sig.direction.value
        sign = 1.0 if direction == "long" else -1.0
        ws = self._snapshot(
            tick_id=fire_idx, as_of=fire_bar.time,
            peer_thoughts=[self._make_bachira_thought_with_stop(
                tick_id=fire_idx, as_of=fire_bar.time,
                direction=direction,
                stop=bachira_stop_fn(sig, sign),
            )],
        )
        p = barou.intend(market, t, workspace=ws)
        assert p is not None
        return p, sig, sign

    def test_disabled_by_default_is_v11_byte_identical(self):
        """Default constructor -> mechanic off; same-direction branch
        keeps Barou's own stop/TP exactly (sealed-cache byte-compat)."""
        p, sig, _ = self._run_same_dir_intend(
            enabled=False,
            bachira_stop_fn=lambda sig, sign: (
                float(sig.entry) - sign * 0.0010   # much tighter anchor
            ),
        )
        r = p.rationale
        assert r["barou_v1_2_enabled"] is False
        assert r["barou_continuation_entry"] is False
        assert r["barou_v1_2_stop_source"] == "own"
        assert p.stop == pytest.approx(float(sig.stop), abs=1e-12)
        assert p.ladder[0].price == pytest.approx(
            float(sig.take_profit), abs=1e-12,
        )

    def test_anchors_to_tighter_bachira_stop_and_rederives_tp(self):
        """Enabled + same-direction + Bachira stop tighter than own ->
        stop anchored at Bachira's distance, TP re-derived at RR 1.5."""
        from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import (
            BAROU_V1_PARAMS,
        )
        anchor_dist = 0.0012   # 12 pips, above the 6.6-pip floor
        p, sig, sign = self._run_same_dir_intend(
            enabled=True,
            bachira_stop_fn=lambda sig, sign: (
                float(sig.entry) - sign * anchor_dist
            ),
        )
        own_dist = abs(float(sig.entry) - float(sig.stop))
        if own_dist <= anchor_dist:
            pytest.skip("synthetic signal stop tighter than test anchor")
        r = p.rationale
        assert r["barou_v1_2_enabled"] is True
        assert r["barou_continuation_entry"] is True
        assert r["barou_v1_2_stop_source"] == "bachira_anchor"
        assert r["barou_v1_2_stop_pips_final"] == pytest.approx(
            anchor_dist / 0.0001, abs=1e-6,
        )
        assert p.stop == pytest.approx(
            float(sig.entry) - sign * anchor_dist, abs=1e-12,
        )
        rr = float(BAROU_V1_PARAMS["target_rr"])
        assert p.ladder[0].price == pytest.approx(
            float(sig.entry) + sign * rr * anchor_dist, abs=1e-12,
        )

    def test_floor_clamps_ultra_tight_anchor(self):
        """Bachira stop tighter than the 6.6-pip floor -> final stop
        distance clamps to the floor, never below."""
        from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import (
            BAROU_V1_2_CONTINUATION_MIN_STOP_PIPS,
        )
        p, sig, sign = self._run_same_dir_intend(
            enabled=True,
            bachira_stop_fn=lambda sig, sign: (
                float(sig.entry) - sign * 0.0001   # 1 pip: below floor
            ),
        )
        own_dist = abs(float(sig.entry) - float(sig.stop))
        floor_dist = BAROU_V1_2_CONTINUATION_MIN_STOP_PIPS * 0.0001
        if own_dist <= floor_dist:
            pytest.skip("synthetic signal stop tighter than the floor")
        r = p.rationale
        assert r["barou_continuation_entry"] is True
        assert r["barou_v1_2_stop_pips_final"] == pytest.approx(
            BAROU_V1_2_CONTINUATION_MIN_STOP_PIPS, abs=1e-6,
        )

    def test_invalid_anchor_on_wrong_side_falls_through(self):
        """Bachira stop on the PROFIT side of Barou's entry (invalid
        invalidation anchor) -> own geometry kept, journalled as
        invalid_anchor."""
        p, sig, _ = self._run_same_dir_intend(
            enabled=True,
            bachira_stop_fn=lambda sig, sign: (
                float(sig.entry) + sign * 0.0010   # wrong side
            ),
        )
        r = p.rationale
        assert r["barou_continuation_entry"] is False
        assert r["barou_v1_2_stop_source"] == "invalid_anchor"
        assert p.stop == pytest.approx(float(sig.stop), abs=1e-12)

    def test_h1_branches_untouched_when_enabled(self):
        """Enabled mechanic must not alter the H1 (no-Bachira) branch:
        no continuation entry, own geometry, H1 lift still applied."""
        from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import (
            A7BarouV1,
        )
        bars = _build_synthetic_usdcad_bars(600)
        barou = A7BarouV1(continuation_entry_enabled=True)
        barou.prepare("USDCAD", bars)
        fire_idx, sig = self._fire(barou, bars)
        fire_bar = bars[fire_idx]
        market = _bar_to_market(fire_bar, fire_idx)
        t = barou.observe(market, FullLedger())
        ws = self._snapshot(
            tick_id=fire_idx, as_of=fire_bar.time, peer_thoughts=[],
        )
        p = barou.intend(market, t, workspace=ws)
        assert p is not None
        r = p.rationale
        assert r["barou_lone_conviction_claim"] is True
        assert r["barou_continuation_entry"] is False
        assert r["barou_v1_2_stop_source"] == "own"
        assert p.stop == pytest.approx(float(sig.stop), abs=1e-12)
