"""Unit tests for E017 confidence-gated cooldown simulation."""
from __future__ import annotations

import random

from programs.E017.confidence_sim import (
    Arm,
    CandidateConfig,
    FrozenParams,
    GaugeFormula,
    PerSymbolFormula,
    gauge_convergence_check,
    pareto_dominates,
    run_path,
)


def test_hk_blinds_longer_than_gc_s_on_loss_streak():
    params = FrozenParams(horizon_days=800, kill_blind_hours=48.0)
    cfg = CandidateConfig(PerSymbolFormula.P_EXP, GaugeFormula.G_SURPLUS, lam=0.25)
    rng_hk = random.Random(7)
    rng_gc = random.Random(7)
    hk = run_path(Arm.HK, cfg, params, rng_hk, bootstrap_rs=None, p_win=0.35)
    gc = run_path(Arm.GC_S, cfg, params, rng_gc, bootstrap_rs=None, p_win=0.35)
    assert gc.total_dead_hours <= hk.total_dead_hours


def test_gauge_convergence_passes_for_surplus():
    params = FrozenParams()
    cfg = CandidateConfig(PerSymbolFormula.P_EXP, GaugeFormula.G_SURPLUS, lam=0.25)
    result = gauge_convergence_check(params, cfg)
    assert result["passed"] is True
    assert result["max_pairwise_disagreement"] <= params.gauge_tolerance


def test_pareto_helper_detects_dead_time_win():
    hk = {"median_dead_hours": 100.0, "median_terminal_equity": 1000,
          "worst_max_drawdown": 0.2, "risk_of_ruin": 0.01}
    gc = {"median_dead_hours": 40.0, "median_terminal_equity": 1010,
          "worst_max_drawdown": 0.19, "risk_of_ruin": 0.01}
    assert pareto_dominates(hk, gc)
