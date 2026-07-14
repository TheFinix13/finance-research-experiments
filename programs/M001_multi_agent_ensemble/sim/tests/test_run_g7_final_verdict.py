"""Tests for the G7 FINAL verdict evaluator (2026-07-14).

Covers the pure statistics (bootstrap helpers, per-criterion
evaluators, squad verdict semantics) and the end-to-end cache-driven
composition with synthetic caches + injected fake agents. The real
replay caches are only consumed by the actual gate run.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from programs.M001_multi_agent_ensemble.sim.scoring import (
    run_g7_final_verdict as fv,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_g7_v1_checkpoint_gate import (
    _g7_windows,
)


WINDOWS = _g7_windows()
N_WINDOWS = len(WINDOWS)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _trade(
    agent_id: str,
    tqs: float,
    window_idx: int = 0,
    *,
    conviction: float = 0.7,
    sl_pips: float = 30.0,
    atr_pips: float = 25.0,
) -> dict:
    """Trade dict matching the on-disk TradeRecord cache schema, with
    an entry_time placed inside the requested OOS window.

    Stamps ``_window_idx`` directly (as ``load_oos_trades`` would) so
    the dict is usable both for direct evaluator calls and for writing
    to a synthetic cache (the loader re-derives the stamp from
    ``entry_time`` on read, overwriting this value consistently)."""
    w = WINDOWS[window_idx]
    entry = w.oos_start.replace(month=6, day=15)
    return {
        "agent_id": agent_id,
        "entry_time": entry.isoformat(sep=" "),
        "_window_idx": window_idx,
        "tqs_components": {"tqs": tqs},
        "source_conviction": conviction,
        "source_sl_pips": sl_pips,
        "source_regime_fit": 0.5,
        "source_atr_pips": atr_pips,
        "source_h1_swing_pips": 60.0,
    }


def _spread(agent_id: str, tqs: float, per_window: int = 5) -> list[dict]:
    """``per_window`` identical trades in every OOS window."""
    out = []
    for w in range(N_WINDOWS):
        out.extend(_trade(agent_id, tqs, w) for _ in range(per_window))
    return out


class FakeAgent:
    """Minimal agent for C5/C6: pure F19/F20 with real variance."""

    def __init__(self, agent_id: str, *, flat: bool = False) -> None:
        self.agent_id = agent_id
        self.playstyle = "test_style"
        self.tier = 2
        self._flat = flat

    def lot_intent(self, conviction, sl_pips, equity, regime_fit):
        if self._flat:
            return 0.1
        return 0.05 + 0.2 * conviction

    def risk_intent(self, conviction, atr_pips, h1_swing_pips):
        if self._flat:
            return 40.0, [80.0]
        return 1.5 * atr_pips, [3.0 * atr_pips]


# ---------------------------------------------------------------------------
# Bootstrap helpers
# ---------------------------------------------------------------------------

class TestBootstrapHelpers:
    def test_mean_ci_deterministic_for_seed(self):
        vals = [0.1, 0.2, 0.3, 0.4, 0.5, 0.35, 0.25]
        a = fv.bootstrap_mean_ci(vals, n_boot=500, seed=7)
        b = fv.bootstrap_mean_ci(vals, n_boot=500, seed=7)
        assert a == b

    def test_mean_ci_brackets_mean(self):
        vals = [0.3] * 5 + [0.5] * 5
        lo, hi = fv.bootstrap_mean_ci(vals, n_boot=2000, seed=1)
        assert lo <= 0.4 <= hi
        assert lo < hi

    def test_mean_ci_constant_values_degenerate(self):
        lo, hi = fv.bootstrap_mean_ci([0.4] * 10, n_boot=200, seed=1)
        assert lo == pytest.approx(0.4)
        assert hi == pytest.approx(0.4)

    def test_mean_ci_empty_returns_nan(self):
        lo, hi = fv.bootstrap_mean_ci([], n_boot=100, seed=1)
        assert math.isnan(lo) and math.isnan(hi)

    def test_mean_ci_single_value_degenerates_to_point(self):
        lo, hi = fv.bootstrap_mean_ci([0.7], n_boot=100, seed=1)
        assert (lo, hi) == (0.7, 0.7)

    def test_diff_ci_positive_when_a_clearly_above_b(self):
        a = [0.6, 0.62, 0.58, 0.61, 0.6, 0.63, 0.59, 0.6]
        b = [0.2, 0.22, 0.18, 0.21, 0.2, 0.19, 0.23, 0.2]
        lo, hi = fv.bootstrap_mean_diff_ci(a, b, n_boot=2000, seed=3)
        assert lo > 0.0
        assert hi > lo

    def test_diff_ci_straddles_zero_when_equal(self):
        a = [0.3, 0.5, 0.4, 0.35, 0.45, 0.4, 0.3, 0.5]
        lo, hi = fv.bootstrap_mean_diff_ci(a, list(a), n_boot=2000, seed=3)
        assert lo < 0.0 < hi

    def test_diff_ci_empty_side_returns_nan(self):
        lo, hi = fv.bootstrap_mean_diff_ci([], [0.1], n_boot=100, seed=1)
        assert math.isnan(lo) and math.isnan(hi)


# ---------------------------------------------------------------------------
# Reduction-ratio edge cases (C3)
# ---------------------------------------------------------------------------

class TestWindowReductionRatio:
    def test_pure_reduction(self):
        # Peer traded 10 without X, only 4 with X -> 60% reduction.
        assert fv._window_reduction_ratio(4, 10) == pytest.approx(0.6)

    def test_no_reduction_when_counts_equal(self):
        assert fv._window_reduction_ratio(10, 10) == 0.0

    def test_negative_when_agent_helps_peer(self):
        # Peer trades MORE with X present -> negative, never flags.
        assert fv._window_reduction_ratio(12, 10) < 0.0

    def test_lo1_zero_yields_zero_not_one(self):
        # Peer would not have traded even without X: no reduction is
        # attributable. (The diagnostic aggregator's 1.0 return for
        # this branch is wrong-signed; the gate evaluator corrects it.)
        assert fv._window_reduction_ratio(5, 0) == 0.0
        assert fv._window_reduction_ratio(0, 0) == 0.0


# ---------------------------------------------------------------------------
# C1 final
# ---------------------------------------------------------------------------

class TestC1Final:
    def test_pass_when_all_three_clauses_hold(self):
        trades = _spread("a", 0.40)
        r = fv.evaluate_c1_final(
            "a", trades, n_windows=N_WINDOWS, is_falsifier=False,
            n_boot=200,
        )
        assert r.passed and r.status == "computed"
        assert r.statistic == pytest.approx(0.40)

    def test_fail_on_panel_mean(self):
        trades = _spread("a", 0.25)  # windows pass 0.20 but mean < 0.30
        r = fv.evaluate_c1_final(
            "a", trades, n_windows=N_WINDOWS, is_falsifier=False,
            n_boot=200,
        )
        assert not r.passed

    def test_fail_on_window_rule(self):
        # High TQS in only 4 windows, nothing elsewhere -> 4/7 < 5.
        trades = []
        for w in range(4):
            trades.extend(_trade("a", 0.60, w) for _ in range(5))
        r = fv.evaluate_c1_final(
            "a", trades, n_windows=N_WINDOWS, is_falsifier=False,
            n_boot=200,
        )
        assert not r.passed
        assert r.evidence["windows_passing_0.20"] == 4

    def test_fail_on_bootstrap_ci_floor(self):
        # Mean 0.305 >= 0.30 and every window >= 0.20, but the spread
        # is wide enough that the CI lower bound dips below 0.25.
        trades = []
        for w in range(N_WINDOWS):
            trades.append(_trade("a", 0.02, w))
            trades.append(_trade("a", 0.59, w))
        r = fv.evaluate_c1_final(
            "a", trades, n_windows=N_WINDOWS, is_falsifier=False,
            n_boot=2000,
        )
        assert r.statistic >= 0.30
        assert r.evidence["windows_passing_0.20"] == N_WINDOWS
        assert not r.passed
        assert r.evidence["bootstrap_ci95"][0] <= 0.25

    def test_falsifier_waived_with_publish_evidence(self):
        r = fv.evaluate_c1_final(
            "reo_mikage", [], n_windows=N_WINDOWS, is_falsifier=True,
            publish_count=123,
        )
        assert r.passed and r.status == "waived"
        assert r.evidence["publish_count"] == 123

    def test_no_trades_fails(self):
        r = fv.evaluate_c1_final(
            "a", [], n_windows=N_WINDOWS, is_falsifier=False,
        )
        assert not r.passed


# ---------------------------------------------------------------------------
# C2 final
# ---------------------------------------------------------------------------

ROSTER2 = ("x", "p", "q")


class TestC2Final:
    def test_tqs_route_qualifies(self):
        # Peer p: clearly better TQS with x present (0.5 vs 0.2).
        baseline = _spread("p", 0.50) + _spread("x", 0.4)
        lo1 = _spread("p", 0.20)
        r = fv.evaluate_c2_final(
            "x", baseline_trades=baseline, lo1_trades=lo1,
            roster=ROSTER2, n_windows=N_WINDOWS, n_boot=500,
        )
        assert r.passed
        assert "p" in r.evidence["qualifying_peers"]
        assert r.evidence["per_peer"]["p"]["tqs_qualifies"]

    def test_trade_count_route_qualifies(self):
        # Peer p: same TQS but 10/window with x present vs 5 without.
        baseline = _spread("p", 0.30, per_window=10)
        lo1 = _spread("p", 0.30, per_window=5)
        r = fv.evaluate_c2_final(
            "x", baseline_trades=baseline, lo1_trades=lo1,
            roster=ROSTER2, n_windows=N_WINDOWS, n_boot=500,
        )
        assert r.passed
        pe = r.evidence["per_peer"]["p"]
        assert pe["trades_qualifies"]
        assert pe["delta_trades"] == pytest.approx(35.0)

    def test_no_qualification_when_nothing_improves(self):
        baseline = _spread("p", 0.30)
        lo1 = _spread("p", 0.30)   # identical -> no strict improvement
        r = fv.evaluate_c2_final(
            "x", baseline_trades=baseline, lo1_trades=lo1,
            roster=ROSTER2, n_windows=N_WINDOWS, n_boot=500,
        )
        assert not r.passed

    def test_noisy_count_delta_fails_ci_gate(self):
        # Total delta +1 but window deltas alternate sign -> window
        # bootstrap CI straddles zero -> no qualification.
        baseline, lo1 = [], []
        per_b = [8, 2, 8, 2, 8, 2, 9]
        per_l = [2, 8, 2, 8, 2, 8, 8]
        for w in range(N_WINDOWS):
            baseline.extend(_trade("p", 0.3, w) for _ in range(per_b[w]))
            lo1.extend(_trade("p", 0.3, w) for _ in range(per_l[w]))
        r = fv.evaluate_c2_final(
            "x", baseline_trades=baseline, lo1_trades=lo1,
            roster=ROSTER2, n_windows=N_WINDOWS, n_boot=2000,
        )
        pe = r.evidence["per_peer"]["p"]
        assert pe["delta_trades"] > 0
        assert not pe["trades_qualifies"]

    def test_excluded_agent_not_scored_as_own_peer(self):
        baseline = _spread("x", 0.9)
        lo1: list[dict] = []
        r = fv.evaluate_c2_final(
            "x", baseline_trades=baseline, lo1_trades=lo1,
            roster=ROSTER2, n_windows=N_WINDOWS, n_boot=200,
        )
        assert "x" not in r.evidence["per_peer"]
        assert not r.passed


# ---------------------------------------------------------------------------
# C3 final
# ---------------------------------------------------------------------------

class TestC3Final:
    def test_clean_everywhere_passes(self):
        baseline = _spread("p", 0.3, per_window=10)
        lo1 = _spread("p", 0.3, per_window=10)
        r = fv.evaluate_c3_final(
            "x", baseline_trades=baseline, lo1_trades=lo1,
            roster=ROSTER2, n_windows=N_WINDOWS,
        )
        assert r.passed
        assert r.evidence["clean_windows"] == N_WINDOWS

    def test_heavy_cannibalisation_fails(self):
        # Peer p: 10/window without x, 2/window with x -> 80% reduction
        # in every window -> 0 clean windows < 4.
        baseline = _spread("p", 0.3, per_window=2)
        lo1 = _spread("p", 0.3, per_window=10)
        r = fv.evaluate_c3_final(
            "x", baseline_trades=baseline, lo1_trades=lo1,
            roster=ROSTER2, n_windows=N_WINDOWS,
        )
        assert not r.passed
        assert r.evidence["clean_windows"] == 0

    def test_exactly_four_clean_windows_passes(self):
        # 3 dirty windows (80% reduction), 4 clean ones.
        baseline, lo1 = [], []
        for w in range(N_WINDOWS):
            n_base = 2 if w < 3 else 10
            baseline.extend(_trade("p", 0.3, w) for _ in range(n_base))
            lo1.extend(_trade("p", 0.3, w) for _ in range(10))
        r = fv.evaluate_c3_final(
            "x", baseline_trades=baseline, lo1_trades=lo1,
            roster=ROSTER2, n_windows=N_WINDOWS,
        )
        assert r.passed
        assert r.evidence["clean_windows"] == 4

    def test_boundary_50_percent_is_clean(self):
        baseline = _spread("p", 0.3, per_window=5)
        lo1 = _spread("p", 0.3, per_window=10)   # exactly 50%
        r = fv.evaluate_c3_final(
            "x", baseline_trades=baseline, lo1_trades=lo1,
            roster=ROSTER2, n_windows=N_WINDOWS,
        )
        assert r.passed


# ---------------------------------------------------------------------------
# Squad verdict semantics
# ---------------------------------------------------------------------------

def _verdict_with(n_passing: int) -> dict:
    from programs.M001_multi_agent_ensemble.sim.scoring.run_g7_v1_checkpoint_gate import (  # noqa: E501
        AgentVerdict, CriterionResult,
    )
    out = {}
    for i, aid in enumerate(fv.G7_FINAL_ROSTER):
        v = AgentVerdict(agent_id=aid, playstyle="t", tier=2)
        ok = i < n_passing
        for c in range(1, 7):
            v.criteria[c] = CriterionResult(
                passed=ok, statistic=0.0, threshold=0.0,
            )
        out[aid] = v
    return out


class TestSquadVerdict:
    def test_all_seven_pass(self):
        verdict, n = fv.squad_verdict(_verdict_with(7))
        assert (verdict, n) == ("PASS", 7)

    def test_five_or_six_is_partial(self):
        assert fv.squad_verdict(_verdict_with(5))[0] == "PARTIAL PASS"
        assert fv.squad_verdict(_verdict_with(6))[0] == "PARTIAL PASS"

    def test_fewer_than_five_fails(self):
        assert fv.squad_verdict(_verdict_with(4))[0] == "FAIL"
        assert fv.squad_verdict(_verdict_with(0))[0] == "FAIL"


# ---------------------------------------------------------------------------
# End-to-end composition from synthetic caches
# ---------------------------------------------------------------------------

def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


@pytest.fixture()
def synthetic_caches(tmp_path: Path):
    """Baseline + lo1 caches for the 7-agent roster.

    Every trading agent gets healthy trades; each lo1 cache lifts one
    peer so C2 passes; no cannibalisation so C3 passes everywhere.
    """
    roster = fv.G7_FINAL_ROSTER
    traders = [a for a in roster if a != "reo_mikage"]
    base_rows: list[dict] = []
    for i, aid in enumerate(traders):
        # Varying conviction/atr per trade so C5/C6 CVs are non-zero.
        for w in range(N_WINDOWS):
            for j in range(6):
                base_rows.append(_trade(
                    aid, 0.42, w,
                    conviction=0.5 + 0.08 * j,
                    sl_pips=20.0 + 5.0 * j,
                    atr_pips=15.0 + 6.0 * j,
                ))
    baseline_dir = tmp_path / "baseline_cache"
    _write_jsonl(baseline_dir / "trades.jsonl", base_rows)
    (baseline_dir / "workspace_counts.json").write_text(json.dumps({
        "publish": {a: 100 for a in roster},
        "read": {a: 50 for a in traders},   # Reo: publish-only (waiver)
    }))
    lo1_root = tmp_path
    lo1_dir = tmp_path / "g7_leave_one_out_testtag"
    for excluded in roster:
        rows: list[dict] = []
        for aid in traders:
            if aid == excluded:
                continue
            # Peers trade the same count but at LOWER TQS without the
            # excluded agent -> C2 passes via the TQS route; identical
            # counts -> C3 clean everywhere.
            for w in range(N_WINDOWS):
                for j in range(6):
                    rows.append(_trade(aid, 0.30, w))
        _write_jsonl(lo1_dir / f"lo1_{excluded}" / "trades.jsonl", rows)
    agents = {a: FakeAgent(a) for a in roster}
    return baseline_dir, lo1_root, agents


class TestRunFinalVerdictE2E:
    def test_full_pass_squad(self, synthetic_caches, tmp_path):
        baseline_dir, lo1_root, agents = synthetic_caches
        report = fv.run_final_verdict(
            baseline_cache_dir=baseline_dir,
            lo1_root=lo1_root, lo1_tag="testtag",
            arm="phi41", tag="unit-e2e",
            out_dir=tmp_path / "out",
            n_boot=300, agents_by_id=agents,
        )
        assert report.verdict == "PASS"
        assert report.n_agents_passing == 7
        # Reo passes through waivers (C1/C5/C6 waived, C4 read-waived).
        reo = report.per_agent["reo_mikage"]
        assert reo.is_v1_pass
        assert reo.criteria[1].status == "waived"
        assert reo.criteria[5].status == "waived"
        # Artefacts written.
        assert (tmp_path / "out" / "g7_v1_checkpoint_final_unit-e2e.json").exists()
        assert (tmp_path / "out" / "g7_v1_checkpoint_final_unit-e2e.md").exists()

    def test_missing_lo1_cache_marks_c2_c3_pending(
        self, synthetic_caches, tmp_path,
    ):
        baseline_dir, lo1_root, agents = synthetic_caches
        # Remove one lo1 cache.
        victim = (
            lo1_root / "g7_leave_one_out_testtag" / "lo1_barou_shoei"
            / "trades.jsonl"
        )
        victim.unlink()
        report = fv.run_final_verdict(
            baseline_cache_dir=baseline_dir,
            lo1_root=lo1_root, lo1_tag="testtag",
            arm="phi41", tag="unit-e2e-missing",
            out_dir=None, n_boot=200, agents_by_id=agents,
        )
        barou = report.per_agent["barou_shoei"]
        assert barou.criteria[2].status == "pending"
        assert barou.criteria[3].status == "pending"
        assert not barou.is_v1_pass
        assert report.verdict == "PARTIAL PASS"   # 6/7 still pass

    def test_flat_agent_fails_c5_c6(self, synthetic_caches, tmp_path):
        baseline_dir, lo1_root, agents = synthetic_caches
        agents["barou_shoei"] = FakeAgent("barou_shoei", flat=True)
        report = fv.run_final_verdict(
            baseline_cache_dir=baseline_dir,
            lo1_root=lo1_root, lo1_tag="testtag",
            arm="phi41", tag="unit-e2e-flat",
            out_dir=None, n_boot=200, agents_by_id=agents,
        )
        barou = report.per_agent["barou_shoei"]
        assert not barou.criteria[5].passed
        assert not barou.criteria[6].passed
        assert not barou.is_v1_pass

    def test_report_json_carries_provenance(
        self, synthetic_caches, tmp_path,
    ):
        baseline_dir, lo1_root, agents = synthetic_caches
        report = fv.run_final_verdict(
            baseline_cache_dir=baseline_dir,
            lo1_root=lo1_root, lo1_tag="testtag",
            arm="arm4", tag="unit-prov",
            out_dir=None, n_boot=200, agents_by_id=agents,
        )
        payload = report.to_jsonable()
        assert payload["arm"] == "arm4"
        assert payload["bootstrap"] == {"seed": fv.DEFAULT_SEED,
                                        "n_boot": 200}
        assert payload["roster"] == list(fv.G7_FINAL_ROSTER)


# ---------------------------------------------------------------------------
# OOS slicing
# ---------------------------------------------------------------------------

class TestLoadOosTrades:
    def test_in_sample_trades_dropped(self, tmp_path):
        rows = [
            {"agent_id": "a", "entry_time": "2016-05-01 04:00:00+00:00",
             "tqs_components": {"tqs": 0.5}},          # IS-only year
            _trade("a", 0.5, 0),                        # 2019 OOS
        ]
        p = tmp_path / "trades.jsonl"
        _write_jsonl(p, rows)
        got = fv.load_oos_trades(p, WINDOWS)
        assert len(got) == 1
        assert got[0]["_window_idx"] == 0

    def test_malformed_entry_time_dropped(self, tmp_path):
        rows = [{"agent_id": "a", "entry_time": "not-a-date",
                 "tqs_components": {"tqs": 0.5}}]
        p = tmp_path / "trades.jsonl"
        _write_jsonl(p, rows)
        assert fv.load_oos_trades(p, WINDOWS) == []
