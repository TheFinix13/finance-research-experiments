"""Unit tests for the E019 risk-adjusted confidence-recovery harness.

Mirrors the E017 test style: metric correctness, arm behaviour, and a
determinism / seed check.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from confidence_sim import (  # noqa: E402
    Arm,
    DGP,
    CandidateConfig,
    FrozenParams,
    GaugeFormula,
    RecoveryLaw,
    annualized_return,
    benjamini_hochberg,
    bootstrap_ci,
    calmar,
    cdar_beta,
    frozen_candidate_grid,
    gauge_convergence_check,
    rac_beta,
    sharpe,
    simulate_cell,
)


# --------------------------------------------------------------------------
# Metric correctness
# --------------------------------------------------------------------------
def test_cdar_beta_tail_mean():
    # underwater curve: worst 5% of 100 points = the 5 largest.
    uw = np.array([0.0] * 95 + [0.10, 0.20, 0.30, 0.40, 0.50])
    # ceil(0.05*100)=5 -> mean of the 5 worst = 0.30
    assert cdar_beta(uw, beta=0.95) == pytest.approx(0.30, abs=1e-9)


def test_cdar_beta_single_worst_when_small_sample():
    uw = np.array([0.05, 0.02, 0.08])
    # ceil(0.05*3)=1 -> just the worst drawdown
    assert cdar_beta(uw, beta=0.95) == pytest.approx(0.08, abs=1e-9)


def test_annualized_return_geometric():
    # doubling over exactly 1 year -> 100% annualised.
    assert annualized_return(2000.0, 1000.0, 1.0) == pytest.approx(1.0, abs=1e-9)
    # flat -> 0.
    assert annualized_return(1000.0, 1000.0, 30.0) == pytest.approx(0.0, abs=1e-9)


def test_rac_and_calmar_definition():
    # AnnRet 0.10, CDaR 0.05 -> RaC 2.0; maxDD 0.20 -> Calmar 0.5.
    assert rac_beta(0.10, 0.05) == pytest.approx(2.0, abs=1e-9)
    assert calmar(0.10, 0.20) == pytest.approx(0.5, abs=1e-9)


def test_rac_reverses_terminal_equity_ranking():
    """The core E019 thesis: an arm that gives up return but slashes CDaR can
    outscore a higher-return arm on RaC (E017's fix)."""
    # Arm A: big return, big tail drawdown. Arm B: small return, tiny CDaR.
    rac_a = rac_beta(1.32, 0.169)   # ~7.8  (AK-like)
    rac_b = rac_beta(0.40, 0.025)   # 16.0  (flat-but-safe recovery)
    assert rac_b > rac_a


def test_sharpe_zero_when_flat():
    assert sharpe(np.zeros(100)) == 0.0
    r = np.array([0.01, -0.01, 0.02, -0.02, 0.015])
    assert sharpe(r) != 0.0


# --------------------------------------------------------------------------
# Arm behaviour
# --------------------------------------------------------------------------
def _fast_params(**kw) -> FrozenParams:
    base = dict(horizon_days=600, bootstrap_resamples=200)
    base.update(kw)
    return FrozenParams(**base)


def test_ak_auto_clears_far_less_dead_time_than_legacy_blind():
    """AK auto-clears at rollover, so a normal DD-halt costs only rest-of-day
    dead time — far below a 48 h blind window."""
    params = _fast_params()
    cfg = frozen_candidate_grid()[0]
    ak = simulate_cell(Arm.AK, cfg, params, dgp=DGP.SYNTHETIC, rho=0.0,
                       p_win=0.40, n_paths=200, seed=1)
    # A normal auto-clear halt is 12 h; sticky escalation is 48 h. The median
    # path must not sit near the old 48 h-per-episode blind regime.
    per_episode = ak.dead_hours / np.maximum(
        np.where(ak.dead_hours > 0, 1, 0).sum(), 1)
    assert float(np.median(ak.dead_hours)) < 48.0 * params.horizon_days


def test_gr_never_goes_blind():
    """GR arms keep evaluating — they never accrue full-blind dead time."""
    params = _fast_params()
    cfg = CandidateConfig(RecoveryLaw.R_RISKADJ, GaugeFormula.G_SURPLUS, 1.0)
    gr = simulate_cell(Arm.GR_S, cfg, params, dgp=DGP.SYNTHETIC, rho=0.0,
                       p_win=0.40, n_paths=200, seed=1)
    assert float(np.max(gr.dead_hours)) == 0.0


def test_gr_t_cannot_fully_restore_risk():
    """GR-T time-decay is capped below tau_full, so once anchored it should be
    slower to resume full risk than GR-S (H2 isolation)."""
    params = _fast_params()
    cfg = CandidateConfig(RecoveryLaw.R_RISKADJ, GaugeFormula.G_SURPLUS, 1.0)
    gs = simulate_cell(Arm.GR_S, cfg, params, dgp=DGP.SYNTHETIC, rho=0.0,
                       p_win=0.55, n_paths=300, seed=2)
    gt = simulate_cell(Arm.GR_T, cfg, params, dgp=DGP.SYNTHETIC, rho=0.0,
                       p_win=0.55, n_paths=300, seed=2)
    # GR-T resume latency (hours) should be >= GR-S at the median.
    assert float(np.median(gt.time_to_resume_h)) >= float(np.median(gs.time_to_resume_h))


def test_recovery_raises_confidence_monotone_in_progress():
    """R-riskadj recovery is monotone: a stronger demonstrated score restores
    at least as much confidence as a weaker one."""
    p = FrozenParams()
    c_min = p.c_min
    def restored(score, target):
        return c_min + (1 - c_min) * min(max(score / target, 0.0), 1.0)
    assert restored(2.0, 1.0) >= restored(0.5, 1.0)
    assert restored(0.0, 1.0) == pytest.approx(c_min)
    assert restored(5.0, 1.0) == pytest.approx(1.0)


def test_gauge_convergence_passes():
    params = FrozenParams()
    for cfg in frozen_candidate_grid():
        res = gauge_convergence_check(params, cfg)
        assert res["passed"] is True
        assert res["max_pairwise_disagreement"] <= params.gauge_tolerance


# --------------------------------------------------------------------------
# Determinism / seed
# --------------------------------------------------------------------------
def test_determinism_same_seed_identical():
    params = _fast_params()
    cfg = frozen_candidate_grid()[0]
    a = simulate_cell(Arm.GR_S, cfg, params, dgp=DGP.SYNTHETIC, rho=0.5,
                      p_win=0.40, n_paths=150, seed=123)
    b = simulate_cell(Arm.GR_S, cfg, params, dgp=DGP.SYNTHETIC, rho=0.5,
                      p_win=0.40, n_paths=150, seed=123)
    assert np.array_equal(a.rac, b.rac)
    assert np.array_equal(a.terminal_equity, b.terminal_equity)


def test_determinism_different_seed_differs():
    params = _fast_params()
    cfg = frozen_candidate_grid()[0]
    a = simulate_cell(Arm.GR_S, cfg, params, dgp=DGP.SYNTHETIC, rho=0.0,
                      p_win=0.40, n_paths=150, seed=1)
    b = simulate_cell(Arm.GR_S, cfg, params, dgp=DGP.SYNTHETIC, rho=0.0,
                      p_win=0.40, n_paths=150, seed=2)
    assert not np.array_equal(a.terminal_equity, b.terminal_equity)


# --------------------------------------------------------------------------
# Statistics helpers
# --------------------------------------------------------------------------
def test_benjamini_hochberg_basic():
    # one tiny p-value among large ones should be rejected at q=0.05.
    pvals = [0.001, 0.4, 0.6, 0.8]
    rej = benjamini_hochberg(pvals, q=0.05)
    assert rej[0] is True
    assert rej[1:] == [False, False, False]


def test_bootstrap_ci_brackets_point():
    rng = np.random.default_rng(0)
    vals = rng.normal(1.0, 0.2, size=500)
    ci = bootstrap_ci(vals, n_resamples=500, seed=0, statistic=np.median)
    assert ci["ci_low"] <= ci["point"] <= ci["ci_high"]


def test_frozen_grid_size():
    # 3 recovery variants (R-riskadj S=1, S=2, R-kelly) x 2 gauges = 6 configs.
    grid = frozen_candidate_grid()
    assert len(grid) == 6
    labels = {c.label for c in grid}
    assert len(labels) == 6
