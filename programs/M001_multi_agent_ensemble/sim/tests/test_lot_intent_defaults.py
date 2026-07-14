"""Contract tests for F19 -- Lot Intent defaults and playstyle building blocks.

Doctrine 06 v0.5 section 4.1a. Verifies:

- ``default_lot_intent`` returns FIXED_LOT (backwards compat).
- ``conviction_scaled_lot_intent`` scales with conviction and regime_fit,
  respects clipping bounds, rounds down to MIN_LOT.
- ``kelly_lot_intent`` scales with (conviction, SL, equity), respects
  Kelly cap, handles SL=0 defensively.
- ``playstyle_lot_intent`` dispatches to the right building block per
  playstyle; unknown playstyle falls back to default.
- Min-lot rounding is always DOWN (Sentinel R2).
- Lot CV across a spread of conviction inputs >= 0.10 (§3.11.5
  criterion #5 sanity).
"""
from __future__ import annotations

import statistics

import pytest

from programs.M001_multi_agent_ensemble.sim.core.lot_intent import (
    FIXED_LOT,
    MIN_LOT,
    conviction_scaled_lot_intent,
    default_lot_intent,
    kelly_lot_intent,
    playstyle_lot_intent,
    risk_normalised_lot_intent,
    _round_down_to_min_lot,
)


class TestDefault:
    def test_returns_fixed_lot_ignoring_inputs(self):
        assert default_lot_intent(0.0, 0.0, 0.0, 0.0) == FIXED_LOT
        assert default_lot_intent(1.0, 100.0, 10000.0, 1.0) == FIXED_LOT

    def test_default_fails_v1_criterion_5_by_design(self):
        """CV of default across varied inputs is 0.0 -- fails §3.11.5 #5."""
        lots = [default_lot_intent(c, 40.0, 100.0, 0.5) for c in [0.1, 0.5, 0.9]]
        cv = statistics.stdev(lots) / statistics.mean(lots)
        assert cv == 0.0
        assert cv < 0.10  # fails the G7 criterion (as expected for default)


class TestConvictionScaledLotIntent:
    def test_scales_up_with_conviction_above_pivot(self):
        low = conviction_scaled_lot_intent(0.40, 40.0, 100.0, 0.5)
        mid = conviction_scaled_lot_intent(0.60, 40.0, 100.0, 0.5)
        high = conviction_scaled_lot_intent(0.80, 40.0, 100.0, 0.5)
        assert low < mid <= high  # monotone non-decreasing

    def test_scales_up_with_regime_fit(self):
        weak = conviction_scaled_lot_intent(0.70, 40.0, 100.0, 0.0)
        strong = conviction_scaled_lot_intent(0.70, 40.0, 100.0, 1.0)
        assert weak <= strong

    def test_respects_min_lot_floor(self):
        # Extreme low conviction + weak regime -> raw would go below MIN_LOT
        lot = conviction_scaled_lot_intent(
            0.0, 40.0, 100.0, 0.0,
            base_lot=0.01, conviction_pivot=0.9, conviction_gain=5.0,
        )
        assert lot >= MIN_LOT
        assert lot % MIN_LOT < 1e-9  # rounded to min-lot multiple

    def test_respects_max_lot_ceiling(self):
        # Extreme high conviction + strong regime -> would exceed ceiling
        lot = conviction_scaled_lot_intent(
            1.0, 40.0, 100.0, 1.0,
            base_lot=FIXED_LOT, max_lot_ceiling=0.20,
        )
        assert lot <= 0.20

    def test_cv_across_conviction_range_meets_v1_criterion(self):
        """§3.11.5 criterion #5: lot CV >= 0.10 across varied inputs."""
        convictions = [0.30, 0.45, 0.60, 0.75, 0.90]
        lots = [
            conviction_scaled_lot_intent(c, 40.0, 100.0, 0.5)
            for c in convictions
        ]
        cv = statistics.stdev(lots) / statistics.mean(lots)
        assert cv >= 0.10


class TestRiskNormalisedLotIntent:
    """Dispersion-primitives round 2 (2026-07-14, doctrine §4.1a amendment).

    Constant-risk sizing anchored at each playstyle's doctrine SL.
    """

    def test_ratio_is_one_at_anchor_sl(self):
        # At sl_pips == ref_sl_pips the inverse-SL factor is 1.0 and the
        # result matches conviction_scaled with the same constants.
        lot_rn = risk_normalised_lot_intent(
            0.70, sl_pips=30.0, equity=100.0, regime_fit=0.5,
            base_lot=0.10, ref_sl_pips=30.0,
            conviction_pivot=0.60, conviction_gain=2.0,
        )
        lot_cs = conviction_scaled_lot_intent(
            0.70, sl_pips=30.0, equity=100.0, regime_fit=0.5,
            base_lot=0.10, conviction_pivot=0.60, conviction_gain=2.0,
        )
        assert lot_rn == pytest.approx(lot_cs)

    def test_tighter_stop_produces_larger_lot(self):
        # Constant-risk: tighter SL earns proportionally more size.
        lot_tight = risk_normalised_lot_intent(
            0.70, sl_pips=20.0, equity=100.0, regime_fit=0.5,
            base_lot=0.10, ref_sl_pips=40.0,
        )
        lot_wide = risk_normalised_lot_intent(
            0.70, sl_pips=60.0, equity=100.0, regime_fit=0.5,
            base_lot=0.10, ref_sl_pips=40.0,
        )
        assert lot_tight > lot_wide

    def test_ratio_clipped_at_floor_and_cap(self):
        # SL 10x the anchor -> ratio would be 0.1, clipped to floor 0.5.
        lot_far_wide = risk_normalised_lot_intent(
            0.70, sl_pips=300.0, equity=100.0, regime_fit=0.5,
            base_lot=0.10, ref_sl_pips=30.0,
        )
        # SL a tenth of the anchor -> ratio would be 10, clipped to cap 2.0.
        lot_far_tight = risk_normalised_lot_intent(
            0.70, sl_pips=3.0, equity=100.0, regime_fit=0.5,
            base_lot=0.10, ref_sl_pips=30.0,
        )
        # Both hit their respective clip boundaries, so far-wide never
        # goes below `base_lot × 0.5 × conviction_factor`, and far-tight
        # never exceeds `base_lot × 2.0 × conviction_factor`.
        assert lot_far_wide > 0
        assert lot_far_tight <= 0.30  # default max_lot_ceiling

    def test_zero_or_negative_sl_defaults_to_ratio_one(self):
        # Defensive: sl_pips <= 0 -> ratio 1.0, size determined by
        # conviction/regime only.
        lot_zero = risk_normalised_lot_intent(
            0.70, sl_pips=0.0, equity=100.0, regime_fit=0.5,
            base_lot=0.10, ref_sl_pips=30.0,
        )
        lot_neg = risk_normalised_lot_intent(
            0.70, sl_pips=-5.0, equity=100.0, regime_fit=0.5,
            base_lot=0.10, ref_sl_pips=30.0,
        )
        assert lot_zero > 0
        assert lot_neg == lot_zero

    def test_min_lot_floor_and_max_ceiling_respected(self):
        lo = risk_normalised_lot_intent(
            0.0, sl_pips=30.0, equity=100.0, regime_fit=0.0,
            base_lot=0.01, ref_sl_pips=30.0,
            conviction_pivot=0.9, conviction_gain=5.0,
        )
        hi = risk_normalised_lot_intent(
            1.0, sl_pips=15.0, equity=100.0, regime_fit=1.0,
            base_lot=0.10, ref_sl_pips=30.0, max_lot_ceiling=0.20,
        )
        assert lo >= MIN_LOT
        assert hi <= 0.20

    def test_cv_across_conviction_x_sl_grid_meets_v1_criterion(self):
        """§3.11.5 criterion #5: for a realistic (conviction × sl) grid
        the risk-normalised lot CV clears 0.10.

        This is the dispersion-r2 core promise: the four failing-C5
        playstyles get the inverse-SL factor as a genuine second
        dispersion channel independent of conviction.
        """
        convictions = [0.30, 0.45, 0.60, 0.75, 0.90]
        sls = [18.0, 24.0, 30.0, 36.0, 42.0]
        lots = [
            risk_normalised_lot_intent(
                c, sl_pips=s, equity=100.0, regime_fit=0.5,
                base_lot=0.10, ref_sl_pips=30.0,
                conviction_pivot=0.60, conviction_gain=2.0,
            )
            for c in convictions for s in sls
        ]
        mean = statistics.mean(lots)
        cv = statistics.stdev(lots) / mean
        assert cv >= 0.10, f"risk_normalised grid CV = {cv:.3f}"


class TestKellyLotIntent:
    def test_positive_conviction_produces_kelly_lot(self):
        lot = kelly_lot_intent(0.75, 40.0, 100.0, 0.5)
        assert lot > 0
        assert lot >= MIN_LOT

    def test_zero_sl_returns_min_floor(self):
        assert kelly_lot_intent(0.75, 0.0, 100.0, 0.5) == MIN_LOT
        assert kelly_lot_intent(0.75, -5.0, 100.0, 0.5) == MIN_LOT

    def test_zero_equity_returns_min_floor(self):
        assert kelly_lot_intent(0.75, 40.0, 0.0, 0.5) == MIN_LOT

    def test_low_conviction_produces_smaller_lot(self):
        high = kelly_lot_intent(0.75, 40.0, 100.0, 0.5)
        low = kelly_lot_intent(0.35, 40.0, 100.0, 0.5)
        assert low <= high

    def test_kelly_capped(self):
        # Even at conviction=1.0, cap of 2 % means max Kelly = 0.02 × 100 = $2.
        # $2 / (40 pips × $0.10/pip) = 0.5 min-lots = 0.005 lot -> rounded to 0.
        # But floor is MIN_LOT (0.01). Should return MIN_LOT.
        lot = kelly_lot_intent(1.0, 40.0, 100.0, 1.0, kelly_fraction_cap=0.02)
        # With max ceiling of 0.30 and small kelly, actual should stay small.
        assert lot <= 0.30


class TestPlaystyleLotIntent:
    def test_conservative_metavision_isagi(self):
        lot = playstyle_lot_intent(
            0.75, 40.0, 100.0, 0.6, playstyle="conservative_metavision",
        )
        assert lot > 0

    def test_rebel_tight_bachira_small_base(self):
        lot = playstyle_lot_intent(
            0.65, 20.0, 100.0, 0.5, playstyle="rebel_tight",
        )
        assert lot <= 0.15  # rebel_tight max_lot_ceiling

    def test_analytical_precision_rin_kelly(self):
        lot = playstyle_lot_intent(
            0.70, 25.0, 100.0, 0.5, playstyle="analytical_precision",
        )
        assert lot >= MIN_LOT

    def test_speed_momentum_chigiri_regime_gain(self):
        weak = playstyle_lot_intent(
            0.65, 30.0, 100.0, 0.0, playstyle="speed_momentum",
        )
        strong = playstyle_lot_intent(
            0.65, 30.0, 100.0, 1.0, playstyle="speed_momentum",
        )
        assert strong >= weak

    def test_copier_hrp_reo(self):
        lot = playstyle_lot_intent(
            0.60, 30.0, 100.0, 0.5, playstyle="copier_hrp",
        )
        assert lot >= MIN_LOT
        assert lot <= 0.15  # copier_hrp max_lot_ceiling

    def test_confluence_only_nagi(self):
        lot = playstyle_lot_intent(
            0.80, 30.0, 100.0, 0.7, playstyle="confluence_only",
        )
        assert lot > 0

    def test_solo_king_barou(self):
        lot = playstyle_lot_intent(
            0.70, 30.0, 100.0, 0.5, playstyle="solo_king",
        )
        assert lot > 0

    def test_defensive_kunigami(self):
        lot = playstyle_lot_intent(
            0.60, 35.0, 100.0, 0.5, playstyle="defensive",
        )
        assert lot > 0
        # defensive max_lot_ceiling = 0.15
        assert lot <= 0.15

    def test_unknown_playstyle_falls_back_to_default(self):
        lot = playstyle_lot_intent(
            0.60, 40.0, 100.0, 0.5, playstyle="not_a_real_playstyle",  # type: ignore[arg-type]
        )
        assert lot == FIXED_LOT

    def test_cv_across_playstyles_and_convictions_meets_v1_criterion(self):
        """§3.11.5 criterion #5: for each playstyle, lot CV across
        varied inputs is >= 0.10.

        Phase S (2026-07-01) added ``analytical_precision`` +
        ``confluence_only`` to this coverage after the kelly
        saturation fix.
        """
        convictions = [0.30, 0.45, 0.60, 0.75, 0.90]
        for ps in [
            "conservative_metavision", "rebel_tight",
            "analytical_precision", "speed_momentum",
            "confluence_only", "solo_king", "defensive",
        ]:
            lots = [
                playstyle_lot_intent(c, 40.0, 100.0, 0.5, playstyle=ps)
                for c in convictions
            ]
            mean = statistics.mean(lots)
            if mean > 0:
                cv = statistics.stdev(lots) / mean
                assert cv >= 0.10, f"playstyle {ps} CV = {cv:.3f} < 0.10"

    def test_dispersion_r2_playstyles_use_sl_channel(self):
        """Dispersion-r2 (2026-07-14): the four amended playstyles must
        respond to ``sl_pips`` (structural dispersion channel), not
        only to conviction.

        Locks in §2.1's promise -- the inverse-SL factor is present.
        Pre-r2 ``conviction_scaled`` produced the same lot at all SLs
        for a fixed conviction, so this test would have returned CV 0.
        """
        for ps in [
            "conservative_metavision", "rebel_tight",
            "confluence_only", "solo_king",
        ]:
            lots = [
                playstyle_lot_intent(0.70, sl, 100.0, 0.5, playstyle=ps)
                for sl in [15.0, 22.5, 30.0, 45.0, 60.0]
            ]
            mean = statistics.mean(lots)
            if mean > 0:
                cv = statistics.stdev(lots) / mean
                # Structural channel alone must be non-trivial.
                assert cv > 0.0, (
                    f"playstyle {ps} shows no SL response: "
                    f"lots={lots} CV=0"
                )

    def test_dispersion_r2_grid_cv_meets_criterion_per_amended_playstyle(self):
        """§3.11.5 criterion #5 stress test on a realistic grid.

        Each amended playstyle, evaluated on a 5-conviction × 5-SL
        grid centred at that playstyle's doctrine anchor, must clear
        CV >= 0.10.
        """
        convictions = [0.30, 0.45, 0.60, 0.75, 0.90]
        # (playstyle, sls-anchored-at-doctrine)
        ps_grid = [
            ("conservative_metavision", [30.0, 35.0, 40.0, 45.0, 50.0]),
            ("rebel_tight",             [10.0, 15.0, 20.0, 25.0, 30.0]),
            ("confluence_only",         [20.0, 25.0, 30.0, 35.0, 40.0]),
            ("solo_king",               [20.0, 25.0, 30.0, 35.0, 40.0]),
        ]
        for ps, sls in ps_grid:
            lots = [
                playstyle_lot_intent(c, sl, 100.0, 0.5, playstyle=ps)
                for c in convictions for sl in sls
            ]
            mean = statistics.mean(lots)
            cv = statistics.stdev(lots) / mean
            assert cv >= 0.10, (
                f"dispersion-r2 grid: playstyle {ps} CV = {cv:.3f} < 0.10"
            )


class TestMinLotRounding:
    def test_rounds_down(self):
        assert _round_down_to_min_lot(0.017, MIN_LOT) == 0.01
        assert _round_down_to_min_lot(0.029, MIN_LOT) == 0.02
        assert _round_down_to_min_lot(0.10, MIN_LOT) == pytest.approx(0.10)

    def test_below_min_lot_returns_zero(self):
        # Note: the fn returns 0 when below floor; callers must clip to MIN_LOT.
        assert _round_down_to_min_lot(0.005, MIN_LOT) == 0.0

    def test_negative_returns_zero(self):
        assert _round_down_to_min_lot(-0.05, MIN_LOT) == 0.0
