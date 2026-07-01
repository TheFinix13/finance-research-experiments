"""Contract tests for F20 -- Risk Intent defaults and playstyle building blocks.

Doctrine 06 v0.5 section 4.1a. Verifies:

- ``default_risk_intent`` returns (40.0, [80.0]) (backwards compat).
- ``atr_scaled_risk_intent`` scales SL with ATR + TP with payoff ratio.
- ``structural_risk_intent`` scales SL with H1 swing pips.
- ``playstyle_risk_intent`` dispatches per playstyle.
- SL / TP CVs across varied inputs meet §3.11.5 criterion #6.
- Guards on zero / negative ATR / swing values.
"""
from __future__ import annotations

import statistics

import pytest

from programs.M001_multi_agent_ensemble.sim.core.risk_intent import (
    DEFAULT_SL_PIPS,
    atr_scaled_risk_intent,
    default_risk_intent,
    playstyle_risk_intent,
    structural_risk_intent,
)


class TestDefault:
    def test_returns_fixed_40_80(self):
        sl, ladder = default_risk_intent(0.5, 40.0, 100.0)
        assert sl == 40.0
        assert ladder == [80.0]

    def test_default_fails_v1_criterion_6_by_design(self):
        sls = [default_risk_intent(c, 40.0, 100.0)[0] for c in [0.3, 0.6, 0.9]]
        cv = statistics.stdev(sls) / statistics.mean(sls)
        assert cv == 0.0  # fails G7 by design


class TestAtrScaledRiskIntent:
    def test_sl_scales_with_atr(self):
        sl_low, _ = atr_scaled_risk_intent(0.7, atr_pips=15.0, h1_swing_pips=50.0)
        sl_high, _ = atr_scaled_risk_intent(0.7, atr_pips=30.0, h1_swing_pips=50.0)
        assert sl_low < sl_high

    def test_sl_respects_min_clip(self):
        sl, _ = atr_scaled_risk_intent(0.7, atr_pips=1.0, h1_swing_pips=50.0)
        assert sl >= 15.0  # sl_pips_min default

    def test_sl_respects_max_clip(self):
        sl, _ = atr_scaled_risk_intent(0.7, atr_pips=200.0, h1_swing_pips=50.0)
        assert sl <= 50.0  # sl_pips_max default

    def test_tp_scales_with_payoff_ratio(self):
        sl, ladder = atr_scaled_risk_intent(
            0.7, atr_pips=20.0, h1_swing_pips=50.0,
            atr_multiplier=1.5, payoff_ratio=2.0,
        )
        assert ladder[0] == pytest.approx(sl * 2.0)

    def test_zero_atr_returns_min_sl(self):
        sl, _ = atr_scaled_risk_intent(0.7, atr_pips=0.0, h1_swing_pips=50.0)
        assert sl == 15.0

    def test_partial_50_100_ladder(self):
        sl, ladder = atr_scaled_risk_intent(
            0.7, atr_pips=20.0, h1_swing_pips=50.0,
            tp_ladder_style="partial_50_100",
        )
        assert len(ladder) == 3
        # 0.5x, 1.0x, 1.5x TP1
        tp1 = ladder[1]
        assert ladder[0] == pytest.approx(tp1 * 0.5)
        assert ladder[2] == pytest.approx(tp1 * 1.5)


class TestStructuralRiskIntent:
    def test_sl_scales_with_swing(self):
        sl_low, _ = structural_risk_intent(0.7, 40.0, h1_swing_pips=50.0)
        sl_high, _ = structural_risk_intent(0.7, 40.0, h1_swing_pips=100.0)
        assert sl_low < sl_high

    def test_sl_min_max_clip(self):
        sl_small, _ = structural_risk_intent(0.7, 40.0, h1_swing_pips=1.0)
        assert sl_small >= 15.0
        sl_big, _ = structural_risk_intent(0.7, 40.0, h1_swing_pips=1000.0)
        assert sl_big <= 30.0

    def test_zero_swing_returns_min_sl(self):
        sl, _ = structural_risk_intent(0.7, 40.0, h1_swing_pips=0.0)
        assert sl == 15.0

    def test_fibonacci_ladder(self):
        sl, ladder = structural_risk_intent(
            0.7, 40.0, h1_swing_pips=80.0,
            tp_multipliers=(2.0, 4.0, 6.0),
        )
        assert len(ladder) == 3
        assert ladder[0] == pytest.approx(sl * 2.0)
        assert ladder[1] == pytest.approx(sl * 4.0)
        assert ladder[2] == pytest.approx(sl * 6.0)


class TestPlaystyleRiskIntent:
    def test_isagi_conservative_metavision(self):
        sl, ladder = playstyle_risk_intent(
            0.7, atr_pips=40.0, h1_swing_pips=60.0,
            playstyle="conservative_metavision",
        )
        # Isagi's fixed anchor near 40 pips.
        assert 30.0 <= sl <= 50.0
        assert len(ladder) == 1

    def test_bachira_rebel_tight(self):
        sl, ladder = playstyle_risk_intent(
            0.65, atr_pips=20.0, h1_swing_pips=40.0, playstyle="rebel_tight",
        )
        assert 15.0 <= sl <= 25.0

    def test_rin_analytical_precision_fib_ladder(self):
        sl, ladder = playstyle_risk_intent(
            0.7, atr_pips=25.0, h1_swing_pips=80.0,
            playstyle="analytical_precision",
        )
        assert len(ladder) == 3
        assert ladder[0] < ladder[1] < ladder[2]  # Fibonacci ascending

    def test_chigiri_speed_momentum(self):
        sl, ladder = playstyle_risk_intent(
            0.65, atr_pips=30.0, h1_swing_pips=60.0,
            playstyle="speed_momentum",
        )
        assert 20.0 <= sl <= 40.0
        # Payoff ratio 3 -> TP1 ≈ 3x SL
        assert ladder[0] >= sl * 2.5

    def test_reo_copier_hrp(self):
        sl, ladder = playstyle_risk_intent(
            0.65, atr_pips=30.0, h1_swing_pips=50.0, playstyle="copier_hrp",
        )
        assert sl > 0
        assert len(ladder) >= 1

    def test_nagi_confluence_only_partial_ladder(self):
        sl, ladder = playstyle_risk_intent(
            0.85, atr_pips=25.0, h1_swing_pips=50.0,
            playstyle="confluence_only",
        )
        assert len(ladder) == 3  # partial_50_100 ladder

    def test_barou_solo_king_structural(self):
        sl, ladder = playstyle_risk_intent(
            0.75, atr_pips=30.0, h1_swing_pips=80.0, playstyle="solo_king",
        )
        assert 20.0 <= sl <= 35.0
        assert len(ladder) == 2

    def test_kunigami_defensive(self):
        sl, ladder = playstyle_risk_intent(
            0.60, atr_pips=30.0, h1_swing_pips=50.0, playstyle="defensive",
        )
        assert 25.0 <= sl <= 45.0

    def test_unknown_playstyle_falls_back_to_default(self):
        sl, ladder = playstyle_risk_intent(
            0.5, 40.0, 100.0, playstyle="unknown",  # type: ignore[arg-type]
        )
        assert sl == DEFAULT_SL_PIPS

    def test_cv_across_atr_range_meets_v1_criterion(self):
        """§3.11.5 criterion #6: SL CV or TP[0] CV >= 0.10 across varied inputs."""
        atr_range = [10.0, 20.0, 30.0, 40.0, 50.0]
        for ps in ["rebel_tight", "speed_momentum", "confluence_only", "defensive"]:
            sls = [
                playstyle_risk_intent(0.7, atr, 50.0, playstyle=ps)[0]
                for atr in atr_range
            ]
            mean = statistics.mean(sls)
            if mean > 0:
                cv = statistics.stdev(sls) / mean
                assert cv >= 0.10, f"playstyle {ps} SL CV = {cv:.3f} < 0.10"

    def test_cv_across_swing_range_for_structural_playstyles(self):
        """Rin + Barou depend on swing pips, not ATR."""
        swings = [30.0, 50.0, 70.0, 90.0, 110.0]
        for ps in ["analytical_precision", "solo_king"]:
            sls = [
                playstyle_risk_intent(0.7, 25.0, s, playstyle=ps)[0]
                for s in swings
            ]
            mean = statistics.mean(sls)
            if mean > 0:
                cv = statistics.stdev(sls) / mean
                assert cv >= 0.10, f"playstyle {ps} SL CV = {cv:.3f} < 0.10"
