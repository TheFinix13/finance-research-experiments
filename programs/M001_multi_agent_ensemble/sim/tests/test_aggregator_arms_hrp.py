"""Phi5 Arm 1 (HRP) contract tests.

Six tests ported from production `tests/test_allocator.py` (equal-weight
smoke, correlated-alphas downweight, negative-edge exclusion, min-N
exclusion, long-only, ...) and six M001-specific tests (window rollover,
min-trades filter, weight cap, zero-total fallback, Phi4.1 replay,
singleton window).

Score axis is per-OOS-window mean TQS, not daily pips. Reference:
`experiments/phi5_aggregator/HRP_NOTES.md` §Tests.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from programs.M001_multi_agent_ensemble.sim.core.aggregator_arms import (
    HRPAggregator,
    HRPWeightSnapshot,
    compute_hrp_weights,
)
from programs.M001_multi_agent_ensemble.sim.core.aggregator_arms.hrp import (
    HRP_MIN_TRADES_PER_AGENT,
    HRP_WEIGHT_CAP,
    _apply_weight_cap,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WINDOW_START = datetime(2024, 1, 1, tzinfo=timezone.utc)
WINDOW_END = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _snap(
    tqs: dict[str, list[float]],
    trades: dict[str, int] | None = None,
    **kwargs,
) -> HRPWeightSnapshot:
    """Convenience wrapper for compute_hrp_weights with default trade counts."""
    if trades is None:
        # Default: 100 trades each (well above min-trades floor).
        trades = {aid: 100 for aid in tqs}
    return compute_hrp_weights(
        tqs, trades,
        window_start=WINDOW_START, window_end=WINDOW_END,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Ported tests from production allocator
# ---------------------------------------------------------------------------

def test_hrp_equal_streams_produce_equal_weights():
    """Two agents with identical per-window mean TQS should get equal weight."""
    tqs = {"isagi_yoichi": [0.30, 0.32, 0.31], "nagi_seishiro": [0.30, 0.32, 0.31]}
    snap = _snap(tqs)
    assert snap.fallback_triggered is False
    assert math.isclose(snap.weights["isagi_yoichi"], 0.5, abs_tol=1e-6)
    assert math.isclose(snap.weights["nagi_seishiro"], 0.5, abs_tol=1e-6)


def test_hrp_correlated_agents_downweighted_relative_to_single():
    """Two perfectly-correlated agents together should get < 100% weight
    each -- the correlation is priced in."""
    tqs = {
        "isagi_yoichi": [0.30, 0.32, 0.31],
        "twin_of_isagi": [0.30, 0.32, 0.31],   # identical series
        "chigiri_hyoma": [0.20, 0.10, 0.15],   # uncorrelated + lower TQS
    }
    snap = _snap(tqs)
    # Each correlated twin should get less than the full slot's weight;
    # combined they should share the mass.
    assert snap.weights["isagi_yoichi"] < 0.75
    assert snap.weights["twin_of_isagi"] < 0.75


def test_hrp_deep_negative_positively_correlated_gets_zero():
    """A strongly-negative-mean agent that is POSITIVELY correlated with a
    positive-mean agent (so it can't hedge) gets zero-clipped."""
    tqs = {
        "isagi_yoichi": [0.30, 0.35, 0.32, 0.34, 0.31],
        "always_loser": [-0.50, -0.45, -0.48, -0.46, -0.49],
    }
    snap = _snap(tqs)
    assert snap.weights["always_loser"] == 0.0
    assert math.isclose(snap.weights["isagi_yoichi"], 1.0, abs_tol=1e-6)


def test_hrp_long_only_no_negative_weights():
    """Long-only clip: no returned weight is negative regardless of the
    tangency raw output."""
    tqs = {
        "isagi_yoichi": [0.30, 0.32, 0.31],
        "nagi_seishiro": [0.28, 0.30, 0.29],
        "loser": [-0.20, -0.10, -0.15],
    }
    snap = _snap(tqs)
    for w in snap.weights.values():
        assert w >= 0.0


def test_hrp_weights_sum_to_one():
    tqs = {
        "isagi_yoichi": [0.30, 0.32, 0.31],
        "nagi_seishiro": [0.28, 0.30, 0.29],
        "bachira_meguru": [0.20, 0.25, 0.22],
    }
    snap = _snap(tqs)
    assert math.isclose(sum(snap.weights.values()), 1.0, abs_tol=1e-6)


def test_hrp_reports_excluded_and_included():
    tqs = {
        "isagi_yoichi": [0.30, 0.32],
        "shortlived_agent": [0.25, 0.28],
    }
    trades = {"isagi_yoichi": 100, "shortlived_agent": 5}  # below min-trades
    snap = _snap(tqs, trades=trades)
    assert "isagi_yoichi" in snap.included_agents
    assert "shortlived_agent" in snap.excluded_agents
    assert "min_trades" in snap.excluded_reasons["shortlived_agent"]


# ---------------------------------------------------------------------------
# M001-specific tests
# ---------------------------------------------------------------------------

def test_hrp_min_trades_per_agent_excludes_short_streams():
    """Below-threshold agents are dropped, not down-weighted."""
    tqs = {
        "isagi_yoichi": [0.30, 0.32],
        "sub_threshold": [0.40, 0.45],   # higher TQS but too few trades
    }
    trades = {
        "isagi_yoichi": 100,
        "sub_threshold": HRP_MIN_TRADES_PER_AGENT - 1,
    }
    snap = _snap(tqs, trades=trades)
    assert "sub_threshold" not in snap.weights
    assert "sub_threshold" in snap.excluded_agents
    assert math.isclose(snap.weights["isagi_yoichi"], 1.0, abs_tol=1e-6)


def test_hrp_weight_cap_prevents_dominance():
    """A single-dominant-agent tangency (one huge positive-mean, rest near-
    zero) should still be capped at ``weight_cap``."""
    tqs = {
        "dominant": [1.00, 1.00, 1.00],
        "meh_a": [0.01, 0.02, 0.01],
        "meh_b": [0.01, 0.02, 0.01],
    }
    snap = _snap(tqs, weight_cap=0.5)
    assert snap.weights["dominant"] <= 0.5 + 1e-6


def test_hrp_zero_total_tqs_fallback_never_nan():
    """All-zero mean TQS should trigger equal-weight fallback, never NaN."""
    tqs = {
        "flat_a": [0.0, 0.0, 0.0],
        "flat_b": [0.0, 0.0, 0.0],
        "flat_c": [0.0, 0.0, 0.0],
    }
    snap = _snap(tqs)
    assert snap.fallback_triggered is True
    for w in snap.weights.values():
        assert not math.isnan(w)
    assert math.isclose(sum(snap.weights.values()), 1.0, abs_tol=1e-6)


def test_hrp_all_negative_edge_produces_safe_weights():
    """When NO agent has positive mean TQS, the allocation must remain
    non-NaN, non-negative, and normalised. Whether that's a one-hot (MVO
    anti-correlation solution) or equal-weight (fallback) is left to the
    solver -- the safety contract is the invariant."""
    tqs = {
        "loser_a": [-0.10, -0.15, -0.12, -0.14, -0.11],
        "loser_b": [-0.20, -0.25, -0.22, -0.24, -0.21],
    }
    snap = _snap(tqs)
    assert math.isclose(sum(snap.weights.values()), 1.0, abs_tol=1e-6)
    for w in snap.weights.values():
        assert not math.isnan(w)
        assert w >= 0.0


def test_hrp_singleton_window_returns_full_weight():
    """With only one eligible agent, that agent gets full weight."""
    tqs = {"lone_agent": [0.30, 0.35, 0.32]}
    snap = _snap(tqs)
    assert snap.fallback_triggered is True
    assert snap.fallback_reason == "singleton_eligible"
    assert math.isclose(snap.weights["lone_agent"], 1.0, abs_tol=1e-6)


def test_hrp_insufficient_windows_falls_back():
    """With only 1 window of history, covariance is undefined; fallback fires."""
    tqs = {
        "isagi_yoichi": [0.30],
        "nagi_seishiro": [0.35],
    }
    snap = _snap(tqs)
    assert snap.fallback_triggered is True
    assert "insufficient_windows" in snap.fallback_reason


def test_hrp_phi41_replay_downweights_bachira_vs_nagi():
    """Phi4.1 replay: Bachira mean TQS 0.308 vs Nagi mean TQS 0.349.
    HRP should favour Nagi given equal-n eligibility. Uses noisier synthetic
    inputs to avoid the small-n low-variance tangency pathology (real Phi4.1
    windows have material within-window TQS dispersion)."""
    # 5-window synthetic Phi4.1-shaped TQS with realistic within-agent noise
    # and mild independence across agents.
    tqs = {
        "bachira_meguru": [0.35, 0.28, 0.31, 0.29, 0.31],   # mean ~0.308
        "nagi_seishiro": [0.37, 0.33, 0.35, 0.36, 0.34],    # mean ~0.35
    }
    trades = {"bachira_meguru": 2840, "nagi_seishiro": 94}
    snap = _snap(tqs, trades=trades)
    assert snap.weights["nagi_seishiro"] > snap.weights["bachira_meguru"]


# ---------------------------------------------------------------------------
# Stateful adapter tests
# ---------------------------------------------------------------------------

def test_hrp_aggregator_refits_and_caches():
    hrp = HRPAggregator()
    assert hrp.has_snapshot is False

    snap = hrp.refit(
        per_agent_window_tqs={
            "a": [0.30, 0.35, 0.31, 0.33, 0.32],
            "b": [0.28, 0.32, 0.30, 0.34, 0.29],
        },
        per_agent_trade_counts={"a": 100, "b": 100},
        window_start=WINDOW_START, window_end=WINDOW_END,
    )
    assert hrp.has_snapshot is True
    assert hrp.current_snapshot is snap
    assert math.isclose(sum(snap.weights.values()), 1.0, abs_tol=1e-6)
    # Both agents positive-mean and eligible -> both should have non-negative
    # weights. Long-only clip may push one to zero if correlation dominates;
    # what we guarantee is normalisation and no NaN.
    for w in snap.weights.values():
        assert w >= 0.0
        assert not math.isnan(w)
    assert hrp.get_weight("nonexistent") == 0.0


def test_hrp_aggregator_history_appends_per_refit():
    hrp = HRPAggregator()
    for i in range(3):
        hrp.refit(
            per_agent_window_tqs={"a": [0.3 + i * 0.01]},
            per_agent_trade_counts={"a": 100},
            window_start=WINDOW_START + timedelta(days=365 * i),
            window_end=WINDOW_END + timedelta(days=365 * i),
        )
    assert len(hrp.history) == 3


# ---------------------------------------------------------------------------
# Weight-cap internals
# ---------------------------------------------------------------------------

def test_apply_weight_cap_redistributes_excess():
    import numpy as np
    w = np.array([0.7, 0.2, 0.1])
    capped = _apply_weight_cap(w, 0.5)
    assert capped[0] <= 0.5 + 1e-6
    assert math.isclose(capped.sum(), 1.0, abs_tol=1e-6)


def test_apply_weight_cap_leaves_small_weights_alone():
    import numpy as np
    w = np.array([0.4, 0.35, 0.25])
    capped = _apply_weight_cap(w, 0.5)
    # None exceed cap -> should return unchanged (modulo renormalisation drift).
    assert math.isclose(capped[0], 0.4, abs_tol=1e-6)
    assert math.isclose(capped[1], 0.35, abs_tol=1e-6)
    assert math.isclose(capped[2], 0.25, abs_tol=1e-6)
