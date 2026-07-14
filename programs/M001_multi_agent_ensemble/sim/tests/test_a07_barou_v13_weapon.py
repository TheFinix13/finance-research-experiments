"""Phase Y -- Barou v1.3 weapon tests (2026-07-14).

Pre-registration: `experiments/phase_y_barou_weapon/PROTOCOL.md` sec 3.
Asserts:

  * BAROU_V13_PARAMS reach the inner production alpha verbatim, and
    the v1.3 weapon is the constructor default.
  * ``weapon_v13=False`` reproduces the legacy v1 fire set (parity
    with a raw baseline-zone ``SupplyDemandAlpha``).
  * The D1 with-gate and Isagi's against-gate are mutually exclusive:
    no bar index fires under both.
  * On any shared signal tick, Barou v1.3's stop AND take-profit
    differ from Bachira's cell (geometric distinctness -- the Phase W
    duplication root cause is structurally removed).
"""
from __future__ import annotations

import pytest

from programs.M001_multi_agent_ensemble.sim._cross_repo import (
    production_repo_available,
)
from programs.M001_multi_agent_ensemble.sim.tests.test_a07_barou_wrap import (
    _build_synthetic_usdcad_bars,
)

pytestmark = pytest.mark.skipif(
    not production_repo_available(),
    reason="Barou wraps production zone_alpha; requires prod repo on path",
)


def test_v13_params_reach_inner_alpha_and_are_default():
    from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import (
        BAROU_V13_PARAMS,
        A7BarouV1,
    )
    barou = A7BarouV1()
    inner = barou._inner
    assert barou._weapon_v13 is True
    assert inner.htf_align == "D1"
    assert inner.htf_align_mode == "with"
    assert inner.htf_lookback == 10
    assert inner.htf_min_move_pips == 60.0
    assert inner.target_via_structure is True
    assert inner.structural_lookback == 200
    assert inner.min_structural_rr == 1.0
    assert inner.stop_atr_mult == 1.0
    assert inner.target_rr == 1.5
    assert BAROU_V13_PARAMS["htf_align_mode"] == "with"


def test_v13_gate_params_mirror_isagi_locked_cell():
    """The gate params must be Isagi's E001-derived values verbatim
    (mode flipped) -- zero re-tuning per the pre-registration."""
    from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi import (
        ISAGI_V1_PARAMS,
    )
    from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import (
        BAROU_V13_PARAMS,
    )
    assert BAROU_V13_PARAMS["htf_align"] == ISAGI_V1_PARAMS["htf_align"]
    assert BAROU_V13_PARAMS["htf_lookback"] == ISAGI_V1_PARAMS["htf_lookback"]
    assert (
        BAROU_V13_PARAMS["htf_min_move_pips"]
        == ISAGI_V1_PARAMS["htf_min_move_pips"]
    )
    assert ISAGI_V1_PARAMS["htf_align_mode"] == "against"
    assert BAROU_V13_PARAMS["htf_align_mode"] == "with"


def test_legacy_flag_reproduces_v1_fire_set():
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

    legacy = A7BarouV1(weapon_v13=False)
    legacy.prepare("USDCAD", bars)
    assert legacy._weapon_v13 is False

    fired = 0
    for i in range(200, len(bars) - 1):
        raw_sig = raw.signal(actx, i)
        wrapped = legacy.inner_signal_at("USDCAD", i)
        assert (raw_sig is None) == (wrapped is None)
        if raw_sig is not None:
            fired += 1
            assert wrapped.entry == pytest.approx(float(raw_sig.entry))
            assert wrapped.stop == pytest.approx(float(raw_sig.stop))
            assert wrapped.take_profit == pytest.approx(
                float(raw_sig.take_profit)
            )
    if fired == 0:
        pytest.skip("synthetic series produced no baseline zone signals")


def test_with_gate_and_against_gate_are_disjoint():
    """Isagi (against) and Barou v1.3 (with) can never fire on the same
    bar: the D1 gate admits a signal to exactly one of them."""
    from agent.alphas.base import AlphaContext
    from agent.alphas.concepts.zone_alpha import SupplyDemandAlpha
    from agent.config import load_config
    from agent.rules.engine import precompute

    bars = _build_synthetic_usdcad_bars(600)
    cfg = load_config()
    ctx = precompute(bars, cfg)
    actx = AlphaContext(bars=bars, ctx=ctx, cfg=cfg)
    gate = dict(htf_align="D1", htf_lookback=10, htf_min_move_pips=60.0)
    with_alpha = SupplyDemandAlpha(
        cfg=cfg, htf_align_mode="with", target_rr=1.5, **gate,
    )
    against_alpha = SupplyDemandAlpha(
        cfg=cfg, htf_align_mode="against", target_rr=1.5, **gate,
    )
    both = 0
    either = 0
    for i in range(200, len(bars) - 1):
        w = with_alpha.signal(actx, i)
        a = against_alpha.signal(actx, i)
        if w is not None or a is not None:
            either += 1
        if w is not None and a is not None:
            both += 1
    assert both == 0
    if either == 0:
        pytest.skip("synthetic series produced no gated signals")


def test_v13_geometry_differs_from_bachira_cell_on_shared_ticks():
    """On any tick where BOTH Bachira's cell (ungated baseline) and
    Barou v1.3 fire, stop and TP must differ -- no full trade-plan
    duplication is possible."""
    from agent.alphas.base import AlphaContext
    from agent.alphas.concepts.zone_alpha import SupplyDemandAlpha
    from agent.config import load_config
    from agent.rules.engine import precompute
    from programs.M001_multi_agent_ensemble.sim.agents.a02_bachira import (
        BACHIRA_V1_PARAMS,
    )
    from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import (
        BAROU_V13_PARAMS,
    )

    bars = _build_synthetic_usdcad_bars(600)
    cfg = load_config()
    ctx = precompute(bars, cfg)
    actx = AlphaContext(bars=bars, ctx=ctx, cfg=cfg)
    bachira_params = {
        k: v for k, v in BACHIRA_V1_PARAMS.items() if k != "name"
    }
    barou_params = {
        k: v for k, v in BAROU_V13_PARAMS.items() if k != "name"
    }
    bachira_alpha = SupplyDemandAlpha(cfg=cfg, **bachira_params)
    barou_alpha = SupplyDemandAlpha(cfg=cfg, **barou_params)

    shared = 0
    for i in range(200, len(bars) - 1):
        b_sig = bachira_alpha.signal(actx, i)
        k_sig = barou_alpha.signal(actx, i)
        if b_sig is None or k_sig is None:
            continue
        shared += 1
        # stop_atr_mult 1.0 vs 0.5 -> stops MUST differ (ATR > 0).
        assert float(k_sig.stop) != pytest.approx(float(b_sig.stop))
        # Structural TP or rr-fallback on a wider stop -> TP differs.
        assert float(k_sig.take_profit) != pytest.approx(
            float(b_sig.take_profit)
        )
    if shared == 0:
        pytest.skip(
            "synthetic series produced no shared Bachira/Barou-v1.3 ticks"
        )
