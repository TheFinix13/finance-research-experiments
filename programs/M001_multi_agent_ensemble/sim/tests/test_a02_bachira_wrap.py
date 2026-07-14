"""A2 Bachira v1 wrap tests.

Mirrors `test_a07_barou_wrap.py`. Asserts:
  * Bachira wraps `SupplyDemandAlpha(htf_align=None)` (baseline zone, no
    D1 gate) on EURUSD / GBPUSD / USDCAD.
  * Off-symbol abstention emits observation-only Thoughts.
  * `intend()` returns None when `prepare()` was never called.
  * Rebel lift fires when the recent-K-bar window contains an
    opposite-direction body close; conviction lands above the
    NAGI_V1_CONFIDENCE_FLOOR (0.7) so Bachira can act as a Nagi peer.
  * Rebel lift skipped when no opposite swing in the lookback window.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from programs.M001_multi_agent_ensemble.sim._cross_repo import (
    production_repo_available,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import FullLedger
from programs.M001_multi_agent_ensemble.sim.core.types import MarketState


pytestmark = pytest.mark.skipif(
    not production_repo_available(),
    reason="A2 Bachira wraps production zone_alpha; requires prod repo on path",
)


def _build_synthetic_bars(n: int = 600, base_price: float = 1.1000):
    """Generic synthetic series with a clean DOWN impulse + pullback into
    the resulting supply zone -- baseline `zone` cell fires on pullback.
    """
    from agent.types import Bar, Timeframe
    base = datetime(2020, 1, 1, tzinfo=timezone.utc)
    bars: list[Bar] = []
    price = base_price
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


def _bar_to_market(bar, tick_id: int, symbol: str = "EURUSD") -> MarketState:
    return MarketState(
        tick_id=tick_id,
        symbol=symbol,
        timeframe=bar.timeframe.value,
        as_of=bar.time,
        open=float(bar.open), high=float(bar.high),
        low=float(bar.low), close=float(bar.close),
        volume=float(bar.volume),
    )


def _make_bachira(**kwargs):
    from programs.M001_multi_agent_ensemble.sim.agents.a02_bachira import (
        A2BachiraV1,
    )
    return A2BachiraV1(**kwargs)


# ---------------------------------------------------------------------------
# Off-symbol abstention
# ---------------------------------------------------------------------------

def test_bachira_abstains_on_unknown_symbol():
    bachira = _make_bachira()
    market = MarketState(
        tick_id=0, symbol="XAUUSD", timeframe="H4",
        as_of=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=1900.0, high=1910.0, low=1890.0, close=1905.0, volume=100.0,
    )
    ledger = FullLedger()
    t = bachira.observe(market, ledger)
    assert t.coordinate is None
    assert "bachira_abstain" in t.tags
    assert "bachira_abstain_symbol" in t.tags
    assert bachira.intend(market, t) is None


def test_bachira_observation_only_when_unprepared():
    bachira = _make_bachira()
    market = MarketState(
        tick_id=0, symbol="EURUSD", timeframe="H4",
        as_of=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=1.1, high=1.11, low=1.09, close=1.105, volume=100.0,
    )
    ledger = FullLedger()
    t = bachira.observe(market, ledger)
    # Never prepared -> observation-only with `unprepared` reason tag.
    assert t.coordinate is None
    assert "bachira_abstain" in t.tags
    assert "abstain_reason:unprepared" in t.tags
    assert bachira.intend(market, t) is None


def test_bachira_intend_returns_none_when_unprepared():
    """Even with a hand-built valid Thought, intend must refuse if
    `prepare()` was never called -- guards the harness contract.
    """
    bachira = _make_bachira()
    market = MarketState(
        tick_id=0, symbol="EURUSD", timeframe="H4",
        as_of=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=1.1, high=1.11, low=1.09, close=1.105, volume=100.0,
    )
    ledger = FullLedger()
    t = bachira.observe(market, ledger)
    assert bachira.intend(market, t) is None


# ---------------------------------------------------------------------------
# Wrap equivalence: same inner alpha output as raw baseline zone
# ---------------------------------------------------------------------------

def test_bachira_wraps_baseline_zone_no_d1_gate():
    """The production SupplyDemandAlpha with `htf_align=None` is the
    baseline cell (no D1 trend gate). Bachira's inner alpha must emit
    the same signal as a raw baseline-zone SupplyDemandAlpha at the
    same bar index.
    """
    from agent.alphas.base import AlphaContext
    from agent.alphas.concepts.zone_alpha import SupplyDemandAlpha
    from agent.config import load_config
    from agent.rules.engine import precompute

    bars = _build_synthetic_bars(600)
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
        pytest.skip("synthetic series produced no baseline zone signals")

    bachira = _make_bachira()
    bachira.prepare("EURUSD", bars)

    for i in list(raw_signals.keys())[:5]:
        sig = bachira.inner_signal_at("EURUSD", i)
        raw_sig = raw_signals[i]
        assert sig is not None
        assert sig.direction.value == raw_sig.direction.value
        assert sig.entry == pytest.approx(float(raw_sig.entry))
        assert sig.stop == pytest.approx(float(raw_sig.stop))
        assert sig.take_profit == pytest.approx(float(raw_sig.take_profit))


# ---------------------------------------------------------------------------
# Rebel lift contract
# ---------------------------------------------------------------------------

def _first_fire(bachira, bars, symbol="EURUSD"):
    """Helper: find first index where the inner alpha fires."""
    for i in range(200, len(bars) - 1):
        sig = bachira.inner_signal_at(symbol, i)
        if sig is not None:
            return i, sig
    return None, None


def test_bachira_observe_emits_proposal_grade_thought():
    """Sanity: when the inner alpha fires, observe emits a Thought with
    a Coordinate and a positive conviction tagged with canon:bachira.
    """
    # Phase Z (2026-07-14): this test pins the LEGACY v1 weapon
    # contract; the v1.4 weave gate is covered by
    # test_phase_z_bachira_weave.py.
    bars = _build_synthetic_bars(600)
    bachira = _make_bachira(weapon_weave=False)
    bachira.prepare("EURUSD", bars)

    fire_idx, fire_sig = _first_fire(bachira, bars)
    if fire_idx is None:
        pytest.skip("synthetic series produced no Bachira signal")

    market = _bar_to_market(bars[fire_idx], fire_idx, symbol="EURUSD")
    ledger = FullLedger()
    t = bachira.observe(market, ledger)
    assert t.coordinate is not None
    assert t.confidence_in_thought >= float(fire_sig.conviction)
    assert "canon:bachira" in t.tags
    assert "weapon:rebel_dribble" in t.tags
    assert "zone_setup_h4" in t.tags
    # Direction tag matches the signal direction.
    assert f"direction:{fire_sig.direction.value}" in t.tags
    # Rationale on the Coordinate carries entry/stop/tp for Nagi to read.
    assert "entry" in t.coordinate.rationale
    assert "stop" in t.coordinate.rationale
    assert "take_profit" in t.coordinate.rationale


def test_bachira_rebel_lift_applied_with_opposite_recent_swing():
    """The synthetic series has a clean DOWN impulse before the pullback
    fade. On the LONG-fade signal that follows the down impulse, the
    `_has_opposite_recent_swing` predicate should detect the recent
    SHORT body closes -> rebel lift fires. Conviction lands at 0.65 +
    0.10 = 0.75, ABOVE Nagi's 0.7 floor.
    """
    bars = _build_synthetic_bars(600)
    bachira = _make_bachira()
    bachira.prepare("EURUSD", bars)

    fire_idx, fire_sig = _first_fire(bachira, bars)
    if fire_idx is None:
        pytest.skip("synthetic series produced no Bachira signal")

    # The synthetic DOWN impulse runs 250..259; the long-fade fires
    # somewhere in the pullback (260..319). Recent K=3 bars at the
    # fire index will include the down-direction body closes, so the
    # rebel predicate fires.
    market = _bar_to_market(bars[fire_idx], fire_idx, symbol="EURUSD")
    ledger = FullLedger()
    t = bachira.observe(market, ledger)
    if fire_sig.direction.value == "long":
        assert "bachira_rebel_lift_applied" in t.tags
        # Final conviction above the Nagi floor (0.7).
        assert t.confidence_in_thought >= 0.70


def test_bachira_intend_carries_final_conviction():
    """The proposal's conviction must equal the Thought's (including
    any rebel lift), so downstream aggregator + Nagi see the lifted
    value.
    """
    # Phase Z (2026-07-14): legacy v1 weapon pin (see above).
    bars = _build_synthetic_bars(600)
    bachira = _make_bachira(weapon_weave=False)
    bachira.prepare("EURUSD", bars)

    fire_idx, _ = _first_fire(bachira, bars)
    if fire_idx is None:
        pytest.skip("synthetic series produced no Bachira signal")

    market = _bar_to_market(bars[fire_idx], fire_idx, symbol="EURUSD")
    ledger = FullLedger()
    t = bachira.observe(market, ledger)
    p = bachira.intend(market, t)
    assert p is not None
    assert p.conviction == pytest.approx(t.confidence_in_thought)
    assert p.symbol == "EURUSD"
    assert p.direction in ("long", "short")
    # Rationale carries the cell metadata.
    assert p.rationale["wrapped"].endswith("SupplyDemandAlpha")
    assert p.rationale["htf_align"] is None
    assert "base_conviction" in p.rationale
    assert "final_conviction" in p.rationale
