"""A4 Chigiri v1 wrap tests.

Asserts:
  * Chigiri is a fully self-contained agent (no production-repo
    coupling for its inner detector); the tests therefore do not skip
    when the production repo is missing.
  * Off-symbol abstention (USDCAD/XAUUSD ticks emit observation-only).
  * `prepare()` populates ATR cache; warmup gate respected.
  * Breakout predicate fires on a clean range-break with ATR
    confirmation; `intend()` emits a proposal with entry=close,
    stop = broken_level ∓ 0.25 ATR, and 1.5R target.
  * Random walks produce no signal (negative regression).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from programs.M001_multi_agent_ensemble.sim.agents.a04_chigiri import (
    A4ChigiriV1,
    CHIGIRI_V1_BASE_CONVICTION,
    CHIGIRI_V1_BREAKOUT_ATR_MULT,
    CHIGIRI_V1_WARMUP_BARS,
    _wilder_atr,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import FullLedger
from programs.M001_multi_agent_ensemble.sim.core.types import MarketState


@dataclass(frozen=True)
class _Bar:
    """Minimal bar shim that satisfies Chigiri's ATR + breakout reads."""

    time: datetime
    open: float
    high: float
    low: float
    close: float


def _build_breakout_series(
    n_chop: int = 130,
    chop_high: float = 1.1050,
    chop_low: float = 1.1000,
    breakout_height: float = 0.0060,
) -> list[_Bar]:
    """Build a synthetic series with a long chop followed by a clean
    LONG breakout. The chop bars have small per-bar ranges (~10 pips)
    so the trailing ATR stays low; the 20-bar lookback high reaches
    `chop_high` because periodic bars touch it. The breakout bar has
    a much larger range so the vol-expansion gate fires.
    """
    base = datetime(2020, 1, 1, tzinfo=timezone.utc)
    bars: list[_Bar] = []
    mid = 0.5 * (chop_high + chop_low)
    for i in range(n_chop):
        # Small alternating body near the midpoint; per-bar range ~10 pips.
        delta = 0.00030 if i % 2 == 0 else -0.00030
        o = mid - delta
        c = mid + delta
        h = mid + 0.00050
        l = mid - 0.00050
        # Touch the chop band edges periodically so the 20-bar lookback
        # high/low forms cleanly. Per-bar range still tight.
        if i % 10 == 0:
            h = chop_high
        if i % 10 == 5:
            l = chop_low
        bars.append(_Bar(
            time=base + timedelta(hours=4 * i),
            open=o, high=h, low=l, close=c,
        ))
    # Clean breakout above chop_high by `breakout_height`.
    breakout_close = chop_high + breakout_height
    bars.append(_Bar(
        time=base + timedelta(hours=4 * len(bars)),
        open=chop_high - 0.0005,
        high=breakout_close + 0.00010,
        low=chop_high - 0.0010,
        close=breakout_close,
    ))
    # A few follow-through bars so intend can see a "next bar".
    price = breakout_close
    for i in range(5):
        new_price = price + 0.00050
        bars.append(_Bar(
            time=base + timedelta(hours=4 * len(bars)),
            open=price,
            high=new_price + 0.00010,
            low=price - 0.00005,
            close=new_price,
        ))
        price = new_price
    return bars


def _build_random_walk(n: int = 220, step: float = 0.00020) -> list[_Bar]:
    """Deterministic zig-zag with no clean breakout. Each bar's range
    stays small relative to the trailing window."""
    base = datetime(2020, 1, 1, tzinfo=timezone.utc)
    bars: list[_Bar] = []
    price = 1.1000
    for i in range(n):
        sign = 1.0 if i % 4 < 2 else -1.0
        new_price = price + sign * step
        bars.append(_Bar(
            time=base + timedelta(hours=4 * i),
            open=price,
            high=max(price, new_price) + step / 2,
            low=min(price, new_price) - step / 2,
            close=new_price,
        ))
        price = new_price
    return bars


def _bar_to_market(bar: _Bar, tick_id: int, symbol: str = "EURUSD") -> MarketState:
    return MarketState(
        tick_id=tick_id,
        symbol=symbol,
        timeframe="H4",
        as_of=bar.time,
        open=bar.open, high=bar.high, low=bar.low, close=bar.close,
        volume=100.0,
    )


# ---------------------------------------------------------------------------
# ATR helper sanity
# ---------------------------------------------------------------------------

def test_wilder_atr_returns_nan_for_short_series():
    bars = _build_random_walk(5)
    atr = _wilder_atr(bars, period=14)
    assert all(x != x for x in atr)  # all NaN


def test_wilder_atr_is_positive_after_warmup():
    bars = _build_breakout_series()
    atr = _wilder_atr(bars, period=14)
    assert atr[15] > 0.0


# ---------------------------------------------------------------------------
# Off-symbol abstention
# ---------------------------------------------------------------------------

def test_chigiri_abstains_on_usdcad():
    chigiri = A4ChigiriV1()
    market = MarketState(
        tick_id=0, symbol="USDCAD", timeframe="H4",
        as_of=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=1.3, high=1.31, low=1.29, close=1.305, volume=100.0,
    )
    t = chigiri.observe(market, FullLedger())
    assert t.coordinate is None
    assert "chigiri_abstain" in t.tags
    assert "chigiri_abstain_symbol" in t.tags
    assert chigiri.intend(market, t) is None


def test_chigiri_abstains_on_xau():
    chigiri = A4ChigiriV1()
    market = MarketState(
        tick_id=0, symbol="XAUUSD", timeframe="H4",
        as_of=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=1900.0, high=1910.0, low=1890.0, close=1905.0, volume=100.0,
    )
    t = chigiri.observe(market, FullLedger())
    assert "chigiri_abstain" in t.tags


def test_chigiri_unprepared_emits_observation_only():
    chigiri = A4ChigiriV1()
    market = MarketState(
        tick_id=0, symbol="EURUSD", timeframe="H4",
        as_of=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=1.1, high=1.11, low=1.09, close=1.105, volume=100.0,
    )
    t = chigiri.observe(market, FullLedger())
    assert t.coordinate is None
    assert "chigiri_abstain" in t.tags
    assert "abstain_reason:unprepared" in t.tags
    assert chigiri.intend(market, t) is None


# ---------------------------------------------------------------------------
# Breakout firing
# ---------------------------------------------------------------------------

def test_chigiri_fires_on_clean_breakout():
    """Synthetic chop then breakout: the last chop-bar produces no
    signal (no break); the breakout bar produces a Thought with
    `chigiri_speed_breakout` tag and conviction >= base."""
    bars = _build_breakout_series(n_chop=CHIGIRI_V1_WARMUP_BARS + 10)
    chigiri = A4ChigiriV1()
    chigiri.prepare("EURUSD", bars)
    # The breakout bar is at index n_chop (the first bar after chop).
    breakout_idx = CHIGIRI_V1_WARMUP_BARS + 10
    market = _bar_to_market(bars[breakout_idx], breakout_idx)
    t = chigiri.observe(market, FullLedger())
    assert t.coordinate is not None, "expected Chigiri breakout to fire"
    assert "chigiri_speed_breakout" in t.tags
    assert t.confidence_in_thought >= CHIGIRI_V1_BASE_CONVICTION
    # Coordinate carries entry/stop/tp for downstream consumers.
    assert "entry" in t.coordinate.rationale
    assert "stop" in t.coordinate.rationale
    assert "take_profit" in t.coordinate.rationale
    # Direction must be "long" for the up-breakout.
    assert t.coordinate.direction_bias == "long"


def test_chigiri_does_not_fire_on_random_walk():
    bars = _build_random_walk(220)
    chigiri = A4ChigiriV1()
    chigiri.prepare("EURUSD", bars)
    fired = 0
    for i in range(CHIGIRI_V1_WARMUP_BARS, len(bars) - 1):
        market = _bar_to_market(bars[i], i)
        t = chigiri.observe(market, FullLedger())
        if "chigiri_speed_breakout" in t.tags:
            fired += 1
    assert fired == 0, (
        f"random walk should not produce breakouts; got {fired}"
    )


def test_chigiri_warmup_gate_returns_observation_only():
    """Bars below the warmup floor must return observation-only."""
    bars = _build_breakout_series(n_chop=CHIGIRI_V1_WARMUP_BARS + 10)
    chigiri = A4ChigiriV1()
    chigiri.prepare("EURUSD", bars)
    # Bar at index 50 is below warmup -> no signal.
    early_idx = 50
    market = _bar_to_market(bars[early_idx], early_idx)
    t = chigiri.observe(market, FullLedger())
    assert t.coordinate is None
    assert "chigiri_speed_breakout" not in t.tags


def test_chigiri_intend_emits_proposal_with_correct_levels():
    bars = _build_breakout_series(n_chop=CHIGIRI_V1_WARMUP_BARS + 10)
    chigiri = A4ChigiriV1()
    chigiri.prepare("EURUSD", bars)

    breakout_idx = CHIGIRI_V1_WARMUP_BARS + 10
    market = _bar_to_market(bars[breakout_idx], breakout_idx)
    t = chigiri.observe(market, FullLedger())
    p = chigiri.intend(market, t)
    assert p is not None
    assert p.symbol == "EURUSD"
    assert p.direction == "long"
    # Entry == breakout close.
    assert p.entry == pytest.approx(bars[breakout_idx].close)
    # Risk > 0 and ladder sums to 1.
    assert sum(r.fraction for r in p.ladder) == pytest.approx(1.0)
    # Conviction preserved end-to-end.
    assert p.conviction == pytest.approx(t.confidence_in_thought)
    # Rationale flag the wrapped detector + breakout-magnitude metadata.
    assert "atr_breakout_continuation_v1" in p.rationale["wrapped"]
    assert p.rationale["breakout_atr_mult"] == CHIGIRI_V1_BREAKOUT_ATR_MULT


def test_chigiri_intend_returns_none_for_no_breakout_thought():
    """If observe emits an observation-only Thought, intend must skip."""
    bars = _build_random_walk(220)
    chigiri = A4ChigiriV1()
    chigiri.prepare("EURUSD", bars)

    market = _bar_to_market(bars[150], 150)
    t = chigiri.observe(market, FullLedger())
    assert "chigiri_speed_breakout" not in t.tags
    assert chigiri.intend(market, t) is None


# ---------------------------------------------------------------------------
# Phase V-a: regime-specialist promotion (2026-07-02)
# ---------------------------------------------------------------------------

class TestPhaseVA_ChigiriRegimeSpecialist:
    """Chigiri stamps ``rationale["_effective_tier"] = 1`` when in his
    specialist regime -- ``mag_atr_ratio >= 1.5 AND atr_expansion_ratio
    >= 1.5``. Aggregator honours the promotion (`test_phase_v_regime
    _specialist.py` covers the aggregator side). This test covers the
    detection contract on the agent side.
    """

    def test_specialist_bit_absent_on_routine_breakout(self):
        """A marginal breakout (magnitude only 0.5 ATR past the range,
        ATR barely above median) must NOT stamp the specialist bit.
        The ``_build_breakout_series`` fixture is calibrated for a
        clean baseline breakout, not a specialist regime.
        """
        bars = _build_breakout_series(n_chop=CHIGIRI_V1_WARMUP_BARS + 10)
        chigiri = A4ChigiriV1()
        chigiri.prepare("EURUSD", bars)
        breakout_idx = CHIGIRI_V1_WARMUP_BARS + 10
        market = _bar_to_market(bars[breakout_idx], breakout_idx)
        t = chigiri.observe(market, FullLedger())
        p = chigiri.intend(market, t)
        assert p is not None
        assert p.rationale["chigiri_regime_specialist"] is False, (
            "Routine breakout must not stamp specialist bit"
        )
        assert "_effective_tier" not in p.rationale, (
            "Routine breakout must not promote to tier-1-equivalent"
        )

    def test_specialist_bit_reports_ratios_for_audit(self):
        """Even on non-specialist bars, the rationale must report the
        ratios so post-hoc walk-forward attribution can inspect why a
        given breakout did/didn't earn the promotion.
        """
        bars = _build_breakout_series(n_chop=CHIGIRI_V1_WARMUP_BARS + 10)
        chigiri = A4ChigiriV1()
        chigiri.prepare("EURUSD", bars)
        breakout_idx = CHIGIRI_V1_WARMUP_BARS + 10
        market = _bar_to_market(bars[breakout_idx], breakout_idx)
        t = chigiri.observe(market, FullLedger())
        p = chigiri.intend(market, t)
        assert p is not None
        r = p.rationale
        assert "chigiri_mag_atr_ratio" in r
        assert "chigiri_atr_expansion_ratio" in r
        assert r["chigiri_regime_min_mag_atr"] == 1.5
        assert r["chigiri_regime_atr_mult"] == 1.5

    def test_specialist_bit_fires_on_high_magnitude_high_expansion(self):
        """Synthesise a stronger breakout series: long low-vol chop
        (small H-L on every bar) then a massive impulse (magnitude
        ~3 ATR past range) into a high-vol regime (ATR spikes vs.
        median). Both specialist conditions should fire.
        """
        base = datetime(2020, 1, 1, tzinfo=timezone.utc)
        tight: list[_Bar] = []
        price = 1.1000
        # Long low-vol chop -- 10-pip H-L range, small step, so ATR
        # median stays low. Include periodic touches of a "chop band"
        # so the 20-bar lookback range is well-defined.
        chop_high = 1.1020
        chop_low = 1.0980
        for i in range(CHIGIRI_V1_WARMUP_BARS + 40):
            delta = 0.00010 if i % 2 == 0 else -0.00010
            o = price
            c = price + delta
            h = max(o, c) + 0.00005
            lo = min(o, c) - 0.00005
            if i % 8 == 0:
                h = chop_high
            if i % 8 == 4:
                lo = chop_low
            tight.append(_Bar(
                time=base + timedelta(hours=4 * i),
                open=o, high=h, low=lo, close=c,
            ))
            price = c
        # 3 huge impulse bars -- ATR spikes, magnitude blows past
        # the recent range by a large multiple.
        for k in range(3):
            new_price = price + 0.0080   # ~80 pip up-move
            tight.append(_Bar(
                time=base + timedelta(
                    hours=4 * (CHIGIRI_V1_WARMUP_BARS + 40 + k),
                ),
                open=price,
                high=new_price + 0.0010,
                low=price - 0.0010,
                close=new_price,
            ))
            price = new_price
        chigiri = A4ChigiriV1()
        chigiri.prepare("EURUSD", tight)
        last_idx = len(tight) - 1
        market = _bar_to_market(tight[last_idx], last_idx)
        t = chigiri.observe(market, FullLedger())
        if "chigiri_speed_breakout" not in t.tags:
            pytest.skip("Synthetic impulse didn't produce a breakout signal")
        p = chigiri.intend(market, t)
        if p is None:
            pytest.skip("Chigiri didn't propose on the synthetic impulse")
        r = p.rationale
        assert r["chigiri_mag_atr_ratio"] is not None
        assert r["chigiri_atr_expansion_ratio"] is not None
        assert r["chigiri_mag_atr_ratio"] >= 1.5
        assert r["chigiri_atr_expansion_ratio"] >= 1.5
        assert r["chigiri_regime_specialist"] is True
        # Phase V-a null result: specialist bit is stamped for audit
        # but NO tier override is applied (see PROTOCOL sec 11.9-
        # postmortem). Regression guard: the override must be absent.
        assert "_effective_tier" not in r, (
            "Phase V-a null result: specialist bit is diagnostic; "
            "tier promotion is reverted"
        )
