"""Phase AB -- Barou v1.3 multi-pair scope reversal tests (2026-07-14).

Pre-registration: `experiments/phase_ab_barou_multipair/PROTOCOL.md`
sec 3. Asserts:

  (a) the whitelist is ("USDCAD", "EURUSD", "GBPUSD") and the v1.3
      weapon runs on a prepared EURUSD fixture;
  (b) the devour lift does NOT apply on EURUSD even when Isagi
      disagrees at high conviction;
  (c) the lone-conviction (H1) lift does NOT apply off-USDCAD;
  (d) both lifts still apply on USDCAD (regression);
  (e) legacy single-symbol construction (``symbols=["USDCAD"]``) still
      abstains off-USDCAD.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from programs.M001_multi_agent_ensemble.sim._cross_repo import (
    production_repo_available,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import FullLedger
from programs.M001_multi_agent_ensemble.sim.core.types import (
    SCHEMA_VERSION,
    Coordinate,
    Thought,
)
from programs.M001_multi_agent_ensemble.sim.tests.test_a07_barou_wrap import (
    _bar_to_market,
    _build_synthetic_usdcad_bars,
)

pytestmark = pytest.mark.skipif(
    not production_repo_available(),
    reason="Barou wraps production zone_alpha; requires prod repo on path",
)


def _make_barou(**kwargs):
    from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import (
        A7BarouV1,
    )
    return A7BarouV1(**kwargs)


class _FakeDirection:
    def __init__(self, value: str) -> None:
        self.value = value


def _fake_signal(direction: str = "short"):
    """Minimal AlphaSignal stand-in accepted by observe()/intend()."""
    return SimpleNamespace(
        direction=_FakeDirection(direction),
        conviction=0.65,
        entry=1.1000,
        stop=1.1050,
        take_profit=1.0925,
        reason="zone_touch_supply",
        meta={"htf_align": "D1"},
    )


def _isagi_thought(symbol: str, direction: str, ts, tick_id: int) -> Thought:
    coord = Coordinate(
        agent_id="isagi_yoichi", symbol=symbol,
        price_lo=1.09, price_hi=1.11,
        time_start=ts, time_end=ts,
        vol_band=(0.5, 2.0), regime_predicate="test",
        expected_strength=0.9, direction_bias=direction,
        rationale={"entry": 1.1, "stop": 1.095, "take_profit": 1.11},
    )
    return Thought(
        schema_version=SCHEMA_VERSION,
        agent_id="isagi_yoichi", tick_id=tick_id, timestamp=ts,
        symbol=symbol, narrative="isagi disagrees", tags=["zone_setup_h4"],
        confidence_in_thought=0.9,
        expected_action=f"{direction}_on_H4_close",
        coordinate=coord, decision_horizon=ts, ttl_ticks=6, references=[],
    )


class _FakeWorkspace:
    """WorkspaceSnapshot stand-in: latest_by_agent only."""

    def __init__(self, thoughts_by_agent: dict) -> None:
        self._t = thoughts_by_agent

    def latest_by_agent(self, symbol: str):
        return {
            aid: t for aid, t in self._t.items() if t.symbol == symbol
        }


def _prepared_barou(symbol: str, direction: str = "short", **kwargs):
    """Barou prepared on a synthetic series with the inner signal
    monkey-patched to a deterministic fire (isolates the home-ground
    gating from zone-detector luck)."""
    bars = _build_synthetic_usdcad_bars(600)
    barou = _make_barou(**kwargs)
    barou.prepare(symbol, bars)
    barou.inner_signal_at = (            # type: ignore[method-assign]
        lambda sym, i, _d=direction: _fake_signal(_d)
    )
    return barou, bars


# ---------------------------------------------------------------------------
# (a) whitelist + weapon on EURUSD
# ---------------------------------------------------------------------------

def test_default_whitelist_is_three_pairs():
    from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import (
        BAROU_HOME_SYMBOL,
        BAROU_V1_SYMBOLS,
        BAROU_V13_PARAMS,
    )
    assert BAROU_V1_SYMBOLS == ("USDCAD", "EURUSD", "GBPUSD")
    assert BAROU_HOME_SYMBOL == "USDCAD"
    # v1.3 weapon params byte-unchanged by Phase AB.
    assert BAROU_V13_PARAMS["htf_align_mode"] == "with"
    assert BAROU_V13_PARAMS["stop_atr_mult"] == 1.0
    barou = _make_barou()
    assert list(barou.symbols) == ["USDCAD", "EURUSD", "GBPUSD"]


def test_v13_weapon_runs_on_prepared_eurusd_fixture():
    barou, bars = _prepared_barou("EURUSD")
    assert "EURUSD" in barou.prepared_symbols
    i = 400
    market = _bar_to_market(bars[i], i, "EURUSD")
    t = barou.observe(market, FullLedger())
    assert t.coordinate is not None, "whitelisted EURUSD tick must fire"
    assert "barou_abstain" not in t.tags
    p = barou.intend(market, t)
    assert p is not None
    assert p.symbol == "EURUSD"
    assert p.rationale["weapon"] == "barou_v13"
    assert p.rationale["barou_home_ground"] is False


# ---------------------------------------------------------------------------
# (b) devour lift is home-ground-only
# ---------------------------------------------------------------------------

def test_devour_does_not_apply_on_eurusd_even_when_isagi_disagrees():
    barou, bars = _prepared_barou("EURUSD", direction="short")
    i = 400
    ledger = FullLedger()
    ledger.append(_isagi_thought(
        "EURUSD", "long", bars[i - 1].time, tick_id=i - 1,
    ))
    market = _bar_to_market(bars[i], i, "EURUSD")
    t = barou.observe(market, ledger)
    assert t.coordinate is not None
    assert "barou_devour_applied" not in t.tags
    assert t.confidence_in_thought == pytest.approx(0.65)


def test_devour_still_applies_on_usdcad_regression():
    barou, bars = _prepared_barou("USDCAD", direction="short")
    i = 400
    ledger = FullLedger()
    ledger.append(_isagi_thought(
        "USDCAD", "long", bars[i - 1].time, tick_id=i - 1,
    ))
    market = _bar_to_market(bars[i], i, "USDCAD")
    t = barou.observe(market, ledger)
    assert t.coordinate is not None
    assert "barou_devour_applied" in t.tags
    assert t.confidence_in_thought == pytest.approx(0.65 + 0.20)


# ---------------------------------------------------------------------------
# (c)/(d) lone-conviction (H1) lift is home-ground-only
# ---------------------------------------------------------------------------

def _observe_and_intend(barou, bars, symbol: str, i: int):
    market = _bar_to_market(bars[i], i, symbol)
    t = barou.observe(market, FullLedger())
    assert t.coordinate is not None
    workspace = _FakeWorkspace({})   # Bachira silent -> H1 branch live
    return barou.intend(market, t, workspace=workspace)


def test_lone_conviction_lift_not_applied_off_usdcad():
    barou, bars = _prepared_barou("EURUSD")
    p = _observe_and_intend(barou, bars, "EURUSD", 400)
    assert p is not None
    assert p.rationale["barou_lone_conviction_claim"] is False
    assert p.rationale["barou_lone_conviction_lift_applied"] == 0.0
    assert p.rationale["_yield_reason"] == "off_home_ground"
    assert p.conviction == pytest.approx(0.65)


def test_lone_conviction_lift_still_applies_on_usdcad_regression():
    barou, bars = _prepared_barou("USDCAD")
    p = _observe_and_intend(barou, bars, "USDCAD", 400)
    assert p is not None
    assert p.rationale["barou_lone_conviction_claim"] is True
    assert p.rationale["barou_lone_conviction_lift_applied"] == pytest.approx(0.10)
    assert p.rationale["barou_home_ground"] is True
    assert p.conviction == pytest.approx(0.65 + 0.10)


# ---------------------------------------------------------------------------
# (e) legacy single-symbol construction
# ---------------------------------------------------------------------------

def test_legacy_single_symbol_construction_abstains_off_usdcad():
    bars = _build_synthetic_usdcad_bars(600)
    barou = _make_barou(symbols=["USDCAD"])
    barou.prepare("USDCAD", bars)
    market = _bar_to_market(bars[400], 400, "EURUSD")
    t = barou.observe(market, FullLedger())
    assert t.coordinate is None
    assert "barou_abstain_symbol" in t.tags
    assert barou.intend(market, t) is None
