"""Phase AA -- Chigiri v1.4 panther-ignition weapon tests (2026-07-14).

Pre-registration: `experiments/phase_aa_chigiri_ignition/PROTOCOL.md`
sec 3. Asserts:

  (a) ignition params reach the detector and v1.4 is the default;
  (b) ``weapon_ignition=False`` reproduces the v1 fire set on a fixture;
  (c) on a synthetic accelerating breakout the v1.4 weapon fires on the
      FIRST breakout close where v1's magnitude hurdle would still be
      waiting;
  (d) a low-thrust poke past the level does NOT fire v1.4;
  (e) the conviction boost is driven by the observed thrust ratio
      (dispersion regression guard).

Chigiri is self-contained (no production-repo dependency).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from programs.M001_multi_agent_ensemble.sim.agents.a04_chigiri import (
    A4ChigiriV1,
    CHIGIRI_V1_BASE_CONVICTION,
    CHIGIRI_V1_MAGNITUDE_BOOST_PER_ATR,
    CHIGIRI_V1_MAX_MAGNITUDE_BOOST,
    CHIGIRI_V1_WARMUP_BARS,
    CHIGIRI_V14_IGNITION_PARAMS,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import FullLedger
from programs.M001_multi_agent_ensemble.sim.core.types import MarketState
from programs.M001_multi_agent_ensemble.sim.tests.test_a04_chigiri_wrap import (
    _build_breakout_series,
)


@dataclass(frozen=True)
class _Bar:
    time: datetime
    open: float
    high: float
    low: float
    close: float


def _bar_to_market(bar, tick_id: int, symbol: str = "EURUSD") -> MarketState:
    return MarketState(
        tick_id=tick_id,
        symbol=symbol,
        timeframe="H4",
        as_of=bar.time,
        open=bar.open, high=bar.high, low=bar.low, close=bar.close,
        volume=100.0,
    )


def _chop_bars(
    n: int,
    *,
    chop_high: float = 1.1050,
    chop_low: float = 1.1000,
    body: float = 0.00030,
    wick: float = 0.00050,
) -> list[_Bar]:
    """Tight chop with periodic touches of the band edges (mirrors the
    locked v1 fixture geometry: per-bar range ~10 pips)."""
    base = datetime(2020, 1, 1, tzinfo=timezone.utc)
    mid = 0.5 * (chop_high + chop_low)
    bars: list[_Bar] = []
    for i in range(n):
        delta = body if i % 2 == 0 else -body
        o = mid - delta
        c = mid + delta
        h = mid + wick
        lo = mid - wick
        if i % 10 == 0:
            h = chop_high
        if i % 10 == 5:
            lo = chop_low
        bars.append(_Bar(
            time=base + timedelta(hours=4 * i),
            open=o, high=h, low=lo, close=c,
        ))
    return bars


def _fire_indices(agent: A4ChigiriV1, bars, symbol: str = "EURUSD") -> list[int]:
    agent.prepare(symbol, bars)
    out = []
    for i in range(len(bars)):
        market = _bar_to_market(bars[i], i, symbol)
        t = agent.observe(market, FullLedger())
        if "chigiri_speed_breakout" in t.tags:
            out.append(i)
    return out


# ---------------------------------------------------------------------------
# (a) params reach the detector; v1.4 default
# ---------------------------------------------------------------------------

def test_ignition_params_locked_and_default():
    assert CHIGIRI_V14_IGNITION_PARAMS["thrust_ratio"] == 1.5
    assert CHIGIRI_V14_IGNITION_PARAMS["thrust_window"] == 5
    chigiri = A4ChigiriV1()
    assert chigiri._weapon_ignition is True
    legacy = A4ChigiriV1(weapon_ignition=False)
    assert legacy._weapon_ignition is False


def test_ignition_signal_carries_weapon_and_thrust():
    bars = _build_breakout_series(n_chop=CHIGIRI_V1_WARMUP_BARS + 10)
    chigiri = A4ChigiriV1()
    chigiri.prepare("EURUSD", bars)
    breakout_idx = CHIGIRI_V1_WARMUP_BARS + 10
    sig = chigiri._detect_breakout(chigiri._prepared["EURUSD"], breakout_idx)
    assert sig is not None
    assert sig["weapon"] == "chigiri_v14_ignition"
    assert sig["thrust_ratio_observed"] is not None
    assert sig["thrust_ratio_observed"] >= 1.5
    # Tag + rationale stamp end-to-end.
    market = _bar_to_market(bars[breakout_idx], breakout_idx)
    t = chigiri.observe(market, FullLedger())
    assert "chigiri_ignition_bar" in t.tags
    p = chigiri.intend(market, t)
    assert p is not None
    assert p.rationale["weapon"] == "chigiri_v14_ignition"
    assert p.rationale["thrust_ratio_observed"] == pytest.approx(
        sig["thrust_ratio_observed"]
    )
    assert p.rationale["ignition_params"] == CHIGIRI_V14_IGNITION_PARAMS


# ---------------------------------------------------------------------------
# (b) legacy flag reproduces the v1 fire set
# ---------------------------------------------------------------------------

def test_legacy_flag_reproduces_v1_fire_set_on_fixture():
    """On the locked v1 fixture, the v1 fire set is exactly the single
    breakout bar (magnitude 60 pips >= 0.5 ATR). ``weapon_ignition=
    False`` must reproduce it, geometry included."""
    n_chop = CHIGIRI_V1_WARMUP_BARS + 10
    bars = _build_breakout_series(n_chop=n_chop)
    legacy = A4ChigiriV1(weapon_ignition=False)
    fired = _fire_indices(legacy, bars)
    assert fired == [n_chop]
    sig = legacy._detect_breakout(legacy._prepared["EURUSD"], n_chop)
    assert sig is not None
    assert sig["weapon"] == "chigiri_v1"
    assert sig["thrust_ratio_observed"] is None
    assert sig["entry"] == pytest.approx(bars[n_chop].close)


# ---------------------------------------------------------------------------
# (c) v1.4 fires on the FIRST close past the range where v1 waits
# ---------------------------------------------------------------------------

def _accelerating_first_close_series(
    overshoot: float = 0.00020,
) -> tuple[list[_Bar], int]:
    """Chop then an ignition bar that closes only ``overshoot`` past the
    20-bar high but with a large true range (acceleration): v1's 0.5 ATR
    magnitude hurdle is NOT met, the 1.5x thrust gate IS."""
    n_chop = CHIGIRI_V1_WARMUP_BARS + 10
    bars = _chop_bars(n_chop)
    chop_high = 1.1050
    base = bars[0].time
    close = chop_high + overshoot
    bars.append(_Bar(
        time=base + timedelta(hours=4 * len(bars)),
        open=1.1005,
        high=close + 0.00005,
        low=1.1000 - 0.00040,      # big range -> TR ~ 5x prior mean
        close=close,
    ))
    return bars, n_chop


def test_v14_fires_on_first_close_where_v1_still_waits():
    bars, idx = _accelerating_first_close_series()
    v14 = A4ChigiriV1()
    v1 = A4ChigiriV1(weapon_ignition=False)
    assert idx in _fire_indices(v14, bars), (
        "v1.4 must fire on the first ignition close past the range"
    )
    assert idx not in _fire_indices(v1, bars), (
        "v1's magnitude hurdle must still be waiting on this bar "
        "(otherwise the fixture does not isolate the mechanism)"
    )


# ---------------------------------------------------------------------------
# (d) low-thrust poke past the level does NOT fire v1.4
# ---------------------------------------------------------------------------

def test_low_thrust_poke_does_not_fire_v14():
    """Poke past the 20-bar high in an already-expanded vol regime:
    predicates 1-4 hold (warmup, ATR valid, vol expansion, close past
    the range) but the bar's true range is < 1.5x the prior-5 mean, so
    the ignition thrust gate -- and ONLY that gate -- blocks the fire."""
    import statistics as _st

    base = datetime(2020, 1, 1, tzinfo=timezone.utc)
    bars: list[_Bar] = []
    mid = 1.1025
    n_lowvol = CHIGIRI_V1_WARMUP_BARS - 20
    # Regime 1: quiet chop (range ~6 pips) -- drags the 80-bar ATR
    # median down.
    for i in range(n_lowvol):
        delta = 0.00010 if i % 2 == 0 else -0.00010
        bars.append(_Bar(
            time=base + timedelta(hours=4 * len(bars)),
            open=mid - delta, high=mid + 0.00030,
            low=mid - 0.00030, close=mid + delta,
        ))
    # Regime 2: loud chop (range ~30 pips) under a hard ceiling at
    # 1.1050 -- ATR rises above the median; prior-5 TR is HIGH, so a
    # modest poke bar cannot reach 1.5x thrust.
    ceiling = 1.1050
    for i in range(30):
        delta = 0.00030 if i % 2 == 0 else -0.00030
        bars.append(_Bar(
            time=base + timedelta(hours=4 * len(bars)),
            open=mid - delta, high=ceiling,
            low=mid - 0.00150, close=mid + delta,
        ))
    # The poke: closes 2 pips past the ceiling; TR comparable to the
    # loud-chop bars (thrust ~1x, far below 1.5).
    close = ceiling + 0.00020
    bars.append(_Bar(
        time=base + timedelta(hours=4 * len(bars)),
        open=mid, high=close + 0.00005,
        low=mid - 0.00120, close=close,
    ))
    idx = len(bars) - 1
    v14 = A4ChigiriV1()
    v14.prepare("EURUSD", bars)
    prep = v14._prepared["EURUSD"]
    # Fixture sanity: predicates 1-4 hold...
    assert idx >= CHIGIRI_V1_WARMUP_BARS
    atr_at = prep.atr[idx]
    atr_median = _st.median(
        prep.atr[k] for k in range(idx - 80, idx)
    )
    assert atr_at > atr_median, "vol-expansion regime must be ON"
    assert close > max(b.high for b in bars[idx - 20:idx])
    # ...and the thrust is sub-threshold.
    window = int(CHIGIRI_V14_IGNITION_PARAMS["thrust_window"])
    mean_prior = sum(prep.tr[idx - window:idx]) / window
    observed = prep.tr[idx] / mean_prior
    assert observed < 1.5, (
        f"fixture must be sub-threshold, got thrust {observed:.2f}"
    )
    assert v14._detect_breakout(prep, idx) is None


# ---------------------------------------------------------------------------
# (e) boost driven by the thrust ratio
# ---------------------------------------------------------------------------

def test_conviction_boost_uses_thrust_ratio():
    bars, idx = _accelerating_first_close_series()
    v14 = A4ChigiriV1()
    v14.prepare("EURUSD", bars)
    sig = v14._detect_breakout(v14._prepared["EURUSD"], idx)
    assert sig is not None
    thrust = float(sig["thrust_ratio_observed"])
    expected_boost = min(
        CHIGIRI_V1_MAX_MAGNITUDE_BOOST,
        CHIGIRI_V1_MAGNITUDE_BOOST_PER_ATR * thrust,
    )
    market = _bar_to_market(bars[idx], idx)
    t = v14.observe(market, FullLedger())
    assert t.confidence_in_thought == pytest.approx(
        min(1.0, CHIGIRI_V1_BASE_CONVICTION + expected_boost)
    )
    # The old driver (magnitude/ATR) would give a DIFFERENT number on
    # this fixture (tiny magnitude, big thrust) -- guard the swap.
    magnitude_boost = min(
        CHIGIRI_V1_MAX_MAGNITUDE_BOOST,
        CHIGIRI_V1_MAGNITUDE_BOOST_PER_ATR
        * (float(sig["magnitude"]) / float(sig["atr"])),
    )
    assert expected_boost != pytest.approx(magnitude_boost)
