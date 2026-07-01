"""Unit tests for G7 criteria evaluators.

Doctrine 06 v0.5 sec 3.11.5. Verifies the criterion logic without
requiring a full replay -- we construct synthetic trade records and
inject them into the evaluators.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any

import pytest

from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi import A1IsagiV1
from programs.M001_multi_agent_ensemble.sim.agents.a02_bachira import A2BachiraV1
from programs.M001_multi_agent_ensemble.sim.agents.a04_chigiri import A4ChigiriV1
from programs.M001_multi_agent_ensemble.sim.scoring.run_g7_v1_checkpoint_gate import (
    CRIT1_MEAN_TQS_THRESHOLD,
    CRIT5_LOT_CV_THRESHOLD,
    CRIT6_RISK_CV_THRESHOLD,
    STRUCTURAL_FALSIFIERS,
    AgentVerdict,
    CriterionResult,
    G7GateReport,
    _cv,
    _evaluate_criterion_1,
    _evaluate_criterion_2_stub,
    _evaluate_criterion_3_stub,
    _evaluate_criterion_4_stub,
    _evaluate_criterion_5,
    _evaluate_criterion_6,
    render_g7_report,
)


@dataclass
class SyntheticTrade:
    """Minimal trade shape for criterion evaluators."""

    agent_id: str = "test"
    trade_id: str = "t0"
    conviction: float = 0.7
    sl_pips: float = 40.0
    regime_fit: float = 0.5
    atr_pips: float = 30.0
    h1_swing_pips: float = 60.0
    tqs_components: dict = field(default_factory=lambda: {"tqs": 0.5})


class TestCriterion1:
    def test_no_trades_fails(self):
        r = _evaluate_criterion_1("isagi_yoichi", [], is_falsifier=False)
        assert r.passed is False
        assert r.status == "computed"
        assert "no trades" in r.evidence["reason"]

    def test_high_tqs_passes(self):
        trades = [
            SyntheticTrade(tqs_components={"tqs": 0.45}),
            SyntheticTrade(tqs_components={"tqs": 0.35}),
            SyntheticTrade(tqs_components={"tqs": 0.32}),
        ]
        r = _evaluate_criterion_1("isagi_yoichi", trades, is_falsifier=False)
        assert r.passed is True
        assert r.statistic >= CRIT1_MEAN_TQS_THRESHOLD

    def test_low_tqs_fails(self):
        trades = [
            SyntheticTrade(tqs_components={"tqs": 0.15}),
            SyntheticTrade(tqs_components={"tqs": 0.20}),
        ]
        r = _evaluate_criterion_1("bachira_meguru", trades, is_falsifier=False)
        assert r.passed is False

    def test_falsifier_waived(self):
        r = _evaluate_criterion_1("reo_mikage", [], is_falsifier=True)
        assert r.status == "waived"
        assert "structural falsifier" in r.evidence["reason"]

    def test_reo_in_structural_falsifiers(self):
        assert "reo_mikage" in STRUCTURAL_FALSIFIERS


class TestCriterionStubs:
    def test_c2_stub_pending(self):
        r = _evaluate_criterion_2_stub()
        assert r.status == "pending"
        assert "leave-one-out" in r.evidence["reason"]

    def test_c3_stub_pending(self):
        r = _evaluate_criterion_3_stub()
        assert r.status == "pending"

    def test_c4_stub_pending(self):
        r = _evaluate_criterion_4_stub()
        assert r.status == "pending"
        assert "workspace" in r.evidence["reason"]


class TestCriterion5:
    def test_conviction_scaled_agent_passes(self):
        """Bachira's rebel_tight varies with conviction -- CV > 0.10."""
        bachira = A2BachiraV1()
        trades = [
            SyntheticTrade(conviction=0.30, sl_pips=20.0, regime_fit=0.5),
            SyntheticTrade(conviction=0.60, sl_pips=20.0, regime_fit=0.5),
            SyntheticTrade(conviction=0.85, sl_pips=20.0, regime_fit=0.5),
            SyntheticTrade(conviction=0.90, sl_pips=20.0, regime_fit=0.5),
        ]
        r = _evaluate_criterion_5(bachira, trades)
        assert r.statistic > 0.0

    def test_no_trades_fails(self):
        chigiri = A4ChigiriV1()
        r = _evaluate_criterion_5(chigiri, [])
        assert r.passed is False


class TestCriterion6:
    def test_atr_scaled_agent_varies(self):
        """Chigiri's speed_momentum SL varies with ATR -- CV > 0.10."""
        chigiri = A4ChigiriV1()
        trades = [
            SyntheticTrade(conviction=0.7, atr_pips=10.0, h1_swing_pips=40.0),
            SyntheticTrade(conviction=0.7, atr_pips=25.0, h1_swing_pips=40.0),
            SyntheticTrade(conviction=0.7, atr_pips=40.0, h1_swing_pips=40.0),
            SyntheticTrade(conviction=0.7, atr_pips=55.0, h1_swing_pips=40.0),
        ]
        r = _evaluate_criterion_6(chigiri, trades)
        assert r.statistic >= CRIT6_RISK_CV_THRESHOLD
        assert r.passed is True

    def test_no_trades_fails(self):
        isagi = A1IsagiV1()
        r = _evaluate_criterion_6(isagi, [])
        assert r.passed is False


class TestBitVector:
    def test_all_pass_gives_111111(self):
        v = AgentVerdict(agent_id="isagi_yoichi", playstyle="conservative_metavision", tier=1)
        for i in range(1, 7):
            v.criteria[i] = CriterionResult(
                passed=True, statistic=1.0, threshold=0.0, status="computed",
            )
        assert v.bit_vector == "111111"
        assert v.is_v1_pass is True

    def test_mixed_pass_gives_correct_string(self):
        v = AgentVerdict(agent_id="nagi_seishiro", playstyle="confluence_only", tier=2)
        v.criteria[1] = CriterionResult(passed=True, statistic=0.35, threshold=0.30, status="computed")
        v.criteria[2] = CriterionResult(passed=False, statistic=0.0, threshold=0.0, status="pending")
        v.criteria[3] = CriterionResult(passed=False, statistic=0.0, threshold=0.0, status="pending")
        v.criteria[4] = CriterionResult(passed=False, statistic=0.0, threshold=0.0, status="pending")
        v.criteria[5] = CriterionResult(passed=True, statistic=0.15, threshold=0.10, status="computed")
        v.criteria[6] = CriterionResult(passed=True, statistic=0.15, threshold=0.10, status="computed")
        assert v.bit_vector == "1???11"
        assert v.is_v1_pass is False

    def test_falsifier_waived_bit_is_W(self):
        v = AgentVerdict(agent_id="reo_mikage", playstyle="copier_hrp", tier=2)
        v.criteria[1] = CriterionResult(passed=False, statistic=0.0, threshold=0.0, status="waived")
        v.criteria[2] = CriterionResult(passed=False, statistic=0.0, threshold=0.0, status="pending")
        v.criteria[3] = CriterionResult(passed=False, statistic=0.0, threshold=0.0, status="pending")
        v.criteria[4] = CriterionResult(passed=False, statistic=0.0, threshold=0.0, status="pending")
        v.criteria[5] = CriterionResult(passed=True, statistic=0.11, threshold=0.10, status="computed")
        v.criteria[6] = CriterionResult(passed=True, statistic=0.12, threshold=0.10, status="computed")
        assert v.bit_vector == "W???11"
        assert v.is_v1_pass is False  # waived != pass under strict rules


class TestCVUtility:
    def test_empty_returns_zero(self):
        assert _cv([]) == 0.0

    def test_single_value_returns_zero(self):
        assert _cv([5.0]) == 0.0

    def test_zero_mean_returns_zero(self):
        assert _cv([0.0, 0.0, 0.0]) == 0.0

    def test_typical_cv_computed(self):
        cv = _cv([0.1, 0.15, 0.2])
        expected = statistics.stdev([0.1, 0.15, 0.2]) / statistics.mean([0.1, 0.15, 0.2])
        assert cv == pytest.approx(expected)


class TestReportRenderer:
    def test_empty_report_renders_pending(self):
        from datetime import datetime, timezone
        r = G7GateReport(
            tag="test",
            panel_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            panel_end=datetime(2024, 12, 31, tzinfo=timezone.utc),
            oos_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            oos_end=datetime(2024, 12, 31, tzinfo=timezone.utc),
        )
        md = render_g7_report(r)
        assert "G7 v1 Checkpoint Gate" in md
        assert "pending" in md.lower()
        assert "FAIL / PARTIAL / PENDING" in md

    def test_report_with_agent_verdict(self):
        from datetime import datetime, timezone
        r = G7GateReport(
            tag="test",
            panel_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            panel_end=datetime(2024, 12, 31, tzinfo=timezone.utc),
            oos_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            oos_end=datetime(2024, 12, 31, tzinfo=timezone.utc),
        )
        v = AgentVerdict(agent_id="isagi_yoichi", playstyle="conservative_metavision", tier=1)
        for i in range(1, 7):
            v.criteria[i] = CriterionResult(
                passed=(i in (1, 5, 6)), statistic=0.35 if i == 1 else 0.15,
                threshold=0.30, status="computed" if i in (1, 5, 6) else "pending",
            )
        r.per_agent["isagi_yoichi"] = v
        md = render_g7_report(r)
        assert "isagi_yoichi" in md
        assert "conservative_metavision" in md
        assert "`1???11`" in md
