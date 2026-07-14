"""Phase Z -- Bachira v1.4 weave-weapon tests (2026-07-14).

Pre-registration: `experiments/phase_z_bachira_weave/PROTOCOL.md` sec 3.
Asserts:

  (a) gate params reach `htf_bias_at` verbatim (copied from Isagi's
      locked E001-derived cell) and v1.4 is the constructor default;
  (b) ``weapon_weave=False`` reproduces the v1 fire set on a fixture;
  (c) weave-gate/with-gate disjointness: for every tick where a
      v1.3-parametrised with-gate fires, Bachira v1.4 abstains;
  (d) a NEUTRAL tick fires with geometry unchanged vs the legacy v1
      weapon on that tick.
"""
from __future__ import annotations

import pytest

from programs.M001_multi_agent_ensemble.sim._cross_repo import (
    production_repo_available,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import FullLedger
from programs.M001_multi_agent_ensemble.sim.tests.test_a07_barou_wrap import (
    _bar_to_market,
    _build_synthetic_usdcad_bars,
)

pytestmark = pytest.mark.skipif(
    not production_repo_available(),
    reason="Bachira wraps production zone_alpha; requires prod repo on path",
)


def _make_bachira(**kwargs):
    from programs.M001_multi_agent_ensemble.sim.agents.a02_bachira import (
        A2BachiraV1,
    )
    return A2BachiraV1(**kwargs)


# ---------------------------------------------------------------------------
# (a) locked params, verbatim from Isagi's cell; v1.4 default
# ---------------------------------------------------------------------------

def test_weave_params_mirror_isagi_locked_cell_and_are_default():
    from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi import (
        ISAGI_V1_PARAMS,
    )
    from programs.M001_multi_agent_ensemble.sim.agents.a02_bachira import (
        BACHIRA_V14_WEAVE_PARAMS,
    )
    assert BACHIRA_V14_WEAVE_PARAMS["htf"] == ISAGI_V1_PARAMS["htf_align"]
    assert (
        BACHIRA_V14_WEAVE_PARAMS["htf_lookback"]
        == ISAGI_V1_PARAMS["htf_lookback"]
    )
    assert (
        BACHIRA_V14_WEAVE_PARAMS["htf_min_move_pips"]
        == ISAGI_V1_PARAMS["htf_min_move_pips"]
    )
    bachira = _make_bachira()
    assert bachira._weapon_weave is True
    legacy = _make_bachira(weapon_weave=False)
    assert legacy._weapon_weave is False


def test_weave_bias_matches_htf_bias_at_verbatim():
    from agent.alphas.concepts._htf import htf_bias_at
    from programs.M001_multi_agent_ensemble.sim.agents.a02_bachira import (
        BACHIRA_V14_WEAVE_PARAMS,
    )
    bars = _build_synthetic_usdcad_bars(600)
    bachira = _make_bachira(symbols=["USDCAD"])
    bachira.prepare("USDCAD", bars)
    prep = bachira._prepared["USDCAD"]
    for i in (100, 250, 300, 400, 550):
        expected = htf_bias_at(
            bars, i,
            htf=BACHIRA_V14_WEAVE_PARAMS["htf"],
            htf_lookback=BACHIRA_V14_WEAVE_PARAMS["htf_lookback"],
            min_move_pips=BACHIRA_V14_WEAVE_PARAMS["htf_min_move_pips"],
        )
        assert bachira._weave_bias_at(prep, i) == str(expected.value)


# ---------------------------------------------------------------------------
# (b) legacy flag reproduces the v1 fire set
# ---------------------------------------------------------------------------

def test_legacy_flag_reproduces_v1_fire_set():
    """``weapon_weave=False`` must fire a Thought with coordinate on
    exactly the ticks where the raw ungated cell signals."""
    bars = _build_synthetic_usdcad_bars(600)
    legacy = _make_bachira(weapon_weave=False)
    legacy.prepare("USDCAD", bars)
    fired = 0
    for i in range(200, len(bars) - 1):
        sig = legacy.inner_signal_at("USDCAD", i)
        market = _bar_to_market(bars[i], i, "USDCAD")
        t = legacy.observe(market, FullLedger())
        assert (sig is None) == (t.coordinate is None)
        if sig is not None:
            fired += 1
            assert "bachira_rebel_baseline_zone" in t.tags
            assert t.coordinate.rationale["entry"] == pytest.approx(
                float(sig.entry)
            )
    if fired == 0:
        pytest.skip("synthetic series produced no baseline zone signals")


# ---------------------------------------------------------------------------
# (c) disjointness from the with-gate on the signal tick
# ---------------------------------------------------------------------------

def test_weave_gate_disjoint_from_barou_with_gate():
    """Wherever a v1.3-parametrised with-gate alpha fires, the D1 bias
    necessarily MATCHES the direction (not neutral) -- Bachira v1.4
    must abstain on that tick."""
    from agent.alphas.base import AlphaContext
    from agent.alphas.concepts.zone_alpha import SupplyDemandAlpha
    from agent.config import load_config
    from agent.rules.engine import precompute
    from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import (
        BAROU_V13_PARAMS,
    )

    bars = _build_synthetic_usdcad_bars(600)
    cfg = load_config()
    ctx = precompute(bars, cfg)
    actx = AlphaContext(bars=bars, ctx=ctx, cfg=cfg)
    with_params = {k: v for k, v in BAROU_V13_PARAMS.items() if k != "name"}
    with_alpha = SupplyDemandAlpha(cfg=cfg, **with_params)

    bachira = _make_bachira(symbols=["USDCAD"])
    bachira.prepare("USDCAD", bars)

    with_fires = 0
    for i in range(200, len(bars) - 1):
        w = with_alpha.signal(actx, i)
        if w is None:
            continue
        with_fires += 1
        market = _bar_to_market(bars[i], i, "USDCAD")
        t = bachira.observe(market, FullLedger())
        assert t.coordinate is None, (
            f"Bachira v1.4 must abstain on with-gate tick {i}"
        )
        assert bachira.intend(market, t) is None
    if with_fires == 0:
        pytest.skip("synthetic series produced no with-gate signals")


# ---------------------------------------------------------------------------
# (d) NEUTRAL tick fires with unchanged geometry
# ---------------------------------------------------------------------------

def test_neutral_tick_fires_with_v1_geometry():
    bars = _build_synthetic_usdcad_bars(600)
    v14 = _make_bachira(symbols=["USDCAD"])
    v14.prepare("USDCAD", bars)
    legacy = _make_bachira(weapon_weave=False, symbols=["USDCAD"])
    legacy.prepare("USDCAD", bars)
    prep = v14._prepared["USDCAD"]

    neutral_fires = 0
    for i in range(200, len(bars) - 1):
        sig = v14.inner_signal_at("USDCAD", i)
        if sig is None or v14._weave_bias_at(prep, i) != "neutral":
            continue
        neutral_fires += 1
        market = _bar_to_market(bars[i], i, "USDCAD")
        t14 = v14.observe(market, FullLedger())
        t1 = legacy.observe(market, FullLedger())
        assert t14.coordinate is not None
        assert "bachira_weave_gate_neutral" in t14.tags
        # Geometry identical to the legacy weapon on the same tick.
        for key in ("entry", "stop", "take_profit"):
            assert t14.coordinate.rationale[key] == pytest.approx(
                t1.coordinate.rationale[key]
            )
        p14 = v14.intend(market, t14)
        assert p14 is not None
        assert p14.rationale["weapon"] == "bachira_v14_weave"
        assert p14.rationale["weave_gate_bias"] == "neutral"
    if neutral_fires == 0:
        pytest.skip("synthetic series produced no neutral-bias signals")
