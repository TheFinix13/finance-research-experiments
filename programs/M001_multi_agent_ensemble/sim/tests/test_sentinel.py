"""Sentinel hard-rule unit tests (R1-R5 + external)."""
from __future__ import annotations

from programs.M001_multi_agent_ensemble.sim.core.sentinel import (
    ExternalShockState,
    check_external_shocks,
    check_r1_min_lot_risk_floor,
    check_r2_discrete_size,
    check_r3_pass_bias,
    check_r4_concentration,
    check_r5_loss_streak,
)


# ---------------------------------------------------------------------------
# R1 — min-lot risk floor
# ---------------------------------------------------------------------------

def test_r1_blocks_when_min_lot_risk_exceeds_cap():
    # $100 equity, 0.01 lot pip value = $0.10. 51 pip stop -> $5.10 risk
    # > $5.00 (5% of $100). Must block.
    d = check_r1_min_lot_risk_floor(
        sl_distance_pips=51, pip_value_per_min_lot=0.10, equity=100.0,
    )
    assert d.allowed is False
    assert d.rule == "R1"


def test_r1_allows_when_within_cap():
    # 50-pip stop -> exactly $5.00 = cap. Not above; allowed.
    d = check_r1_min_lot_risk_floor(
        sl_distance_pips=50, pip_value_per_min_lot=0.10, equity=100.0,
    )
    assert d.allowed is True


# ---------------------------------------------------------------------------
# R2 — discrete sizing rounds DOWN
# ---------------------------------------------------------------------------

def test_r2_rounds_down_to_nearest_min_lot():
    rounded, d = check_r2_discrete_size(0.017)
    assert rounded == 0.01
    assert d.rule == "R2"


def test_r2_rejects_below_min_lot():
    rounded, d = check_r2_discrete_size(0.005)
    assert rounded == 0.0
    assert d.allowed is False
    assert d.rule == "R2"


def test_r2_clean_multiple_unchanged():
    rounded, d = check_r2_discrete_size(0.02)
    assert rounded == 0.02


# ---------------------------------------------------------------------------
# R3 — over-firing flag (audit-only)
# ---------------------------------------------------------------------------

def test_r3_flags_over_firing_but_does_not_block():
    d = check_r3_pass_bias("isagi_yoichi", proposals_today=5)
    assert d.rule == "R3"
    assert d.allowed is True  # R3 is audit-only


def test_r3_silent_at_or_below_threshold():
    d = check_r3_pass_bias("isagi_yoichi", proposals_today=3)
    assert d.rule == "OK"


# ---------------------------------------------------------------------------
# R4 — concentration cap
# ---------------------------------------------------------------------------

def test_r4_blocks_above_concentration_cap():
    d = check_r4_concentration("isagi_yoichi", intended_weight=0.45)
    assert d.allowed is False
    assert d.rule == "R4"


def test_r4_allows_at_cap():
    d = check_r4_concentration("isagi_yoichi", intended_weight=0.40)
    assert d.allowed is True


# ---------------------------------------------------------------------------
# R5 — loss-streak dampener
# ---------------------------------------------------------------------------

def test_r5_applies_dampener_at_3_losses():
    scale, d = check_r5_loss_streak(3)
    assert scale == 0.5
    assert d.rule == "R5"


def test_r5_no_dampener_below_trigger():
    scale, d = check_r5_loss_streak(2)
    assert scale == 1.0
    assert d.rule == "OK"


# ---------------------------------------------------------------------------
# External shocks
# ---------------------------------------------------------------------------

def test_external_rho_jump_fires():
    d = check_external_shocks(ExternalShockState(cross_pair_rho_30d=0.96))
    assert d.allowed is False
    assert "rho_jump" in d.payload.get("trigger", "")


def test_external_spread_spike_fires():
    d = check_external_shocks(
        ExternalShockState(spread_x_trailing_median=3.5)
    )
    assert d.allowed is False
    assert "spread_spike" in d.payload.get("trigger", "")


def test_external_calendar_fires_only_with_prior_regime_shift():
    d_no_shift = check_external_shocks(ExternalShockState(
        high_impact_event_within_2h=True,
        high_impact_prior_regime_shift=False,
    ))
    assert d_no_shift.allowed is True

    d_shift = check_external_shocks(ExternalShockState(
        high_impact_event_within_2h=True,
        high_impact_prior_regime_shift=True,
    ))
    assert d_shift.allowed is False


def test_external_dxy_shock_fires():
    d = check_external_shocks(ExternalShockState(dxy_h1_sigma_z=2.5))
    assert d.allowed is False
    assert "dxy_shock" in d.payload.get("trigger", "")


def test_external_quiet_state_is_ok():
    d = check_external_shocks(ExternalShockState())
    assert d.allowed is True
    assert d.rule == "OK"
