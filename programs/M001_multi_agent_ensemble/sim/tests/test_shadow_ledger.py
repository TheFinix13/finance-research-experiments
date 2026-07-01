"""Tests for Phase U shadow ledger.

Focus:

- Quality-metric helpers behave sensibly on edge cases (MAE=MFE=0,
  losing trades, no-friction).
- ``aggregate_shadow_by_agent`` produces per-agent scouting bit
  vectors, including the reproducibility CV across walk-forward
  windows and the shadow-vs-executed Pearson correlation.
- Shadow trade objects are structurally compatible with
  ``TradeRecord`` (same field surface) so downstream reporting can
  iterate uniformly.
"""
from __future__ import annotations

import datetime as dt

import pytest

from programs.M001_multi_agent_ensemble.sim.scoring.shadow_ledger import (
    ShadowAggregate,
    ShadowTradeRecord,
    _coeff_of_variation,
    _entry_efficiency,
    _exit_efficiency,
    _friction_ratio,
    _pearson,
    aggregate_shadow_by_agent,
)

UTC = dt.timezone.utc


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------

def _make_shadow(
    agent_id: str,
    *,
    tick_id: int,
    tqs: float,
    pnl: float = 10.0,
    r_multiple: float = 1.0,
    symbol: str = "EURUSD",
    mae: float = 5.0,
    mfe: float = 15.0,
    entry_eff: float | None = None,
    exit_eff: float | None = None,
    friction: float | None = None,
) -> ShadowTradeRecord:
    t = dt.datetime(2025, 1, 1, tzinfo=UTC) + dt.timedelta(hours=tick_id)
    return ShadowTradeRecord(
        agent_id=agent_id,
        symbol=symbol,
        entry_time=t,
        exit_time=t + dt.timedelta(hours=4),
        direction="long",
        entry=1.10,
        stop=1.095,
        take_profit=1.115,
        exit_price=1.101,
        exit_reason="tp",
        pnl_pips=pnl,
        mae_pips=mae,
        mfe_pips=mfe,
        bars_held=3,
        r_multiple=r_multiple,
        tqs_components={
            "r": max(0.0, r_multiple),
            "efficiency": 0.6,
            "time_score": 1.0,
            "cleanliness": 1.0,
            "beauty_bonus": 1.0,
            "tqs": tqs,
        },
        is_shadow=True,
        proposal_tick_id=tick_id,
        rejection_reason="crowded_out_by_higher_conviction",
        entry_efficiency=entry_eff,
        exit_efficiency=exit_eff,
        friction_ratio=friction,
    )


# ---------------------------------------------------------------------------
# Quality-metric helpers
# ---------------------------------------------------------------------------

class TestEntryEfficiency:

    def test_never_underwater_gives_one(self):
        assert _entry_efficiency(mae_pips=0.0, initial_risk_pips=50.0) == 1.0

    def test_hits_risk_exactly_gives_half(self):
        assert _entry_efficiency(mae_pips=50.0, initial_risk_pips=50.0) == 0.5

    def test_worse_than_risk_clips_low(self):
        assert _entry_efficiency(mae_pips=200.0, initial_risk_pips=50.0) < 0.3

    def test_both_zero_returns_neutral(self):
        assert _entry_efficiency(mae_pips=0.0, initial_risk_pips=0.0) == 0.5


class TestExitEfficiency:

    def test_captured_full_mfe_gives_one(self):
        assert _exit_efficiency(pnl_pips=20.0, mfe_pips=20.0) == 1.0

    def test_left_half_on_table_gives_half(self):
        assert _exit_efficiency(pnl_pips=10.0, mfe_pips=20.0) == 0.5

    def test_negative_pnl_gives_negative(self):
        assert _exit_efficiency(pnl_pips=-10.0, mfe_pips=20.0) == -0.5

    def test_zero_mfe_denominator_guarded(self):
        assert _exit_efficiency(pnl_pips=5.0, mfe_pips=0.0) == 5.0


class TestFrictionRatio:

    def test_typical_low_friction(self):
        assert _friction_ratio(commission=0.5, pnl=50.0) == pytest.approx(0.01)

    def test_high_friction_flagged(self):
        assert _friction_ratio(commission=5.0, pnl=15.0) == pytest.approx(0.333, abs=0.01)

    def test_zero_pnl_guarded(self):
        # abs(pnl) < 1 -> denom clipped to 1, ratio = commission
        assert _friction_ratio(commission=2.0, pnl=0.0) == 2.0


class TestPearson:

    def test_perfect_positive_correlation(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [2.0, 4.0, 6.0, 8.0, 10.0]
        assert _pearson(xs, ys) == pytest.approx(1.0)

    def test_perfect_negative_correlation(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [5.0, 4.0, 3.0, 2.0, 1.0]
        assert _pearson(xs, ys) == pytest.approx(-1.0)

    def test_zero_variance_series_returns_zero(self):
        xs = [1.0] * 5
        ys = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert _pearson(xs, ys) == 0.0

    def test_below_threshold_returns_zero(self):
        assert _pearson([1.0, 2.0], [1.0, 2.0]) == 0.0


class TestCoeffOfVariation:

    def test_zero_variance_gives_zero(self):
        assert _coeff_of_variation([1.0, 1.0, 1.0]) == 0.0

    def test_moderate_dispersion(self):
        cv = _coeff_of_variation([0.1, 0.2, 0.3, 0.4])
        assert 0.4 < cv < 0.7  # ~0.516

    def test_zero_mean_guarded(self):
        assert _coeff_of_variation([-1.0, 1.0, -1.0, 1.0]) == 0.0


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

class TestAggregateShadowByAgent:

    def test_empty_input_yields_empty_dict(self):
        assert aggregate_shadow_by_agent([]) == {}

    def test_two_agents_grouped_separately(self):
        recs = [
            _make_shadow("isagi_yoichi", tick_id=1, tqs=0.30, pnl=15.0),
            _make_shadow("isagi_yoichi", tick_id=2, tqs=0.40, pnl=20.0),
            _make_shadow("rin_itoshi", tick_id=3, tqs=0.55, pnl=25.0),
        ]
        out = aggregate_shadow_by_agent(recs)
        assert set(out.keys()) == {"isagi_yoichi", "rin_itoshi"}
        assert out["isagi_yoichi"].n_shadow_trades == 2
        assert out["rin_itoshi"].n_shadow_trades == 1

    def test_win_rate_and_mean_tqs(self):
        recs = [
            _make_shadow("isagi_yoichi", tick_id=1, tqs=0.5, pnl=10.0),
            _make_shadow("isagi_yoichi", tick_id=2, tqs=0.3, pnl=-5.0),
            _make_shadow("isagi_yoichi", tick_id=3, tqs=0.0, pnl=-10.0),
        ]
        out = aggregate_shadow_by_agent(recs)
        agg = out["isagi_yoichi"]
        assert agg.win_rate == pytest.approx(1.0 / 3.0)
        assert agg.mean_shadow_tqs == pytest.approx((0.5 + 0.3 + 0.0) / 3.0)

    def test_per_window_cv_populated(self):
        # Two windows, three trades each. Window 0 mean TQS ~0.3,
        # window 1 mean TQS ~0.5 -- CV = stdev(0.3, 0.5) / mean(0.3, 0.5).
        recs = [
            _make_shadow("bachira_meguru", tick_id=10, tqs=0.28),
            _make_shadow("bachira_meguru", tick_id=11, tqs=0.30),
            _make_shadow("bachira_meguru", tick_id=12, tqs=0.32),
            _make_shadow("bachira_meguru", tick_id=20, tqs=0.48),
            _make_shadow("bachira_meguru", tick_id=21, tqs=0.50),
            _make_shadow("bachira_meguru", tick_id=22, tqs=0.52),
        ]
        window_of_tick = {10: 0, 11: 0, 12: 0, 20: 1, 21: 1, 22: 1}
        out = aggregate_shadow_by_agent(recs, window_of_tick=window_of_tick)
        agg = out["bachira_meguru"]
        assert set(agg.per_window_mean_tqs.keys()) == {0, 1}
        assert agg.per_window_mean_tqs[0] == pytest.approx(0.30)
        assert agg.per_window_mean_tqs[1] == pytest.approx(0.50)
        # CV of (0.30, 0.50) should be nonzero.
        assert agg.per_window_cv_tqs > 0.3

    def test_shadow_executed_pearson_populated_with_enough_pairs(self):
        # 6 paired ticks. Shadow-TQS moves lockstep with executed-TQS
        # -- should get Pearson near 1.0.
        recs = [
            _make_shadow("chigiri_hyoma", tick_id=t, tqs=0.10 * t)
            for t in range(1, 7)
        ]
        executed = {
            ("chigiri_hyoma", t): 0.10 * t + 0.05 for t in range(1, 7)
        }
        out = aggregate_shadow_by_agent(
            recs, executed_by_agent_tick=executed,
        )
        agg = out["chigiri_hyoma"]
        assert agg.n_paired_ticks == 6
        assert agg.shadow_executed_pearson == pytest.approx(1.0, abs=1e-6)

    def test_shadow_executed_pearson_none_below_threshold(self):
        # Only 3 paired ticks -- below the min-sample threshold (5).
        recs = [
            _make_shadow("nagi_seishiro", tick_id=t, tqs=0.10 * t)
            for t in range(1, 4)
        ]
        executed = {
            ("nagi_seishiro", t): 0.10 * t for t in range(1, 4)
        }
        out = aggregate_shadow_by_agent(
            recs, executed_by_agent_tick=executed,
        )
        assert out["nagi_seishiro"].shadow_executed_pearson is None

    def test_quality_metrics_aggregated_when_present(self):
        recs = [
            _make_shadow(
                "barou_shoei", tick_id=1, tqs=0.4,
                entry_eff=0.80, exit_eff=0.6, friction=0.02,
            ),
            _make_shadow(
                "barou_shoei", tick_id=2, tqs=0.5,
                entry_eff=0.90, exit_eff=0.7, friction=0.03,
            ),
        ]
        out = aggregate_shadow_by_agent(recs)
        agg = out["barou_shoei"]
        assert agg.mean_entry_efficiency == pytest.approx(0.85)
        assert agg.mean_exit_efficiency == pytest.approx(0.65)
        assert agg.mean_friction_ratio == pytest.approx(0.025)

    def test_quality_metrics_none_when_all_missing(self):
        recs = [
            _make_shadow("kunigami_rensuke", tick_id=1, tqs=0.3),
        ]
        out = aggregate_shadow_by_agent(recs)
        agg = out["kunigami_rensuke"]
        assert agg.mean_entry_efficiency is None
        assert agg.mean_exit_efficiency is None
        assert agg.mean_friction_ratio is None

    def test_accepted_vs_rejected_split(self):
        # Two accepted proposals with high shadow-TQS, three rejected
        # with low. Aggregator picked winners -> delta (rej-acc) < 0.
        recs = [
            _make_shadow("isagi_yoichi", tick_id=1, tqs=0.60),
            _make_shadow("isagi_yoichi", tick_id=2, tqs=0.65),
            _make_shadow("isagi_yoichi", tick_id=3, tqs=0.20),
            _make_shadow("isagi_yoichi", tick_id=4, tqs=0.15),
            _make_shadow("isagi_yoichi", tick_id=5, tqs=0.25),
        ]
        # Tag first two as accepted, rest as rejected.
        recs[0].rejection_reason = "accepted_by_aggregator"
        recs[1].rejection_reason = "accepted_by_aggregator"
        for r in recs[2:]:
            r.rejection_reason = "aggregator_lower_conviction"

        out = aggregate_shadow_by_agent(recs)
        agg = out["isagi_yoichi"]
        assert agg.n_shadow_accepted == 2
        assert agg.n_shadow_rejected == 3
        assert agg.mean_shadow_tqs_when_accepted == pytest.approx(0.625)
        assert agg.mean_shadow_tqs_when_rejected == pytest.approx(0.20)
        # Delta strongly negative -> aggregator picked winners.
        delta = (
            agg.mean_shadow_tqs_when_rejected
            - agg.mean_shadow_tqs_when_accepted
        )
        assert delta < -0.3

    def test_split_when_no_accepted(self):
        # Rin post-Phase-S: proposes but never executes.
        recs = [
            _make_shadow("itoshi_rin", tick_id=t, tqs=0.30 + 0.01 * t)
            for t in range(1, 6)
        ]
        for r in recs:
            r.rejection_reason = "aggregator_lower_conviction"
        out = aggregate_shadow_by_agent(recs)
        agg = out["itoshi_rin"]
        assert agg.n_shadow_accepted == 0
        assert agg.n_shadow_rejected == 5
        assert agg.mean_shadow_tqs_when_accepted is None
        assert agg.mean_shadow_tqs_when_rejected is not None


class TestShadowAggregateJsonable:

    def test_to_jsonable_roundtrip_shape(self):
        agg = ShadowAggregate(
            agent_id="isagi_yoichi",
            n_shadow_trades=10,
            n_shadow_wins=6,
            mean_shadow_tqs=0.35,
            mean_shadow_r_multiple=0.9,
            win_rate=0.6,
            per_window_mean_tqs={0: 0.3, 1: 0.4},
            per_window_cv_tqs=0.2,
            per_symbol_mean_tqs={"EURUSD": 0.35},
            shadow_executed_pearson=0.72,
            n_paired_ticks=8,
            mean_entry_efficiency=0.85,
            mean_exit_efficiency=0.60,
            mean_friction_ratio=0.03,
        )
        out = agg.to_jsonable()
        assert out["agent_id"] == "isagi_yoichi"
        assert out["per_window_mean_tqs"] == {0: 0.3, 1: 0.4}
        assert out["shadow_executed_pearson"] == pytest.approx(0.72)
        assert out["mean_entry_efficiency"] == pytest.approx(0.85)

    def test_to_jsonable_handles_none_correlation(self):
        agg = ShadowAggregate(
            agent_id="reo_mikage",
            n_shadow_trades=0,
            n_shadow_wins=0,
            mean_shadow_tqs=0.0,
            mean_shadow_r_multiple=0.0,
            win_rate=0.0,
        )
        out = agg.to_jsonable()
        assert out["shadow_executed_pearson"] is None
        assert out["mean_entry_efficiency"] is None
