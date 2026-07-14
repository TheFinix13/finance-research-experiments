"""Tests for the C3 v2 distinctness-aware evaluator (2026-07-14).

Pre-registration: `experiments/c3_v2_distinctness/PROTOCOL.md`. These
tests pin the trade-plan identity key, the duplicate-exclusion
semantics, and the invariance property (agents with no duplicate-alpha
peer score identically under v1 and v2).
"""
from __future__ import annotations

import math

from programs.M001_multi_agent_ensemble.sim.scoring import run_c3_v2 as c3
from programs.M001_multi_agent_ensemble.sim.scoring import (
    run_g7_final_verdict as fv,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_g7_v1_checkpoint_gate import (
    _g7_windows,
)

WINDOWS = _g7_windows()
N_WINDOWS = len(WINDOWS)

ROSTER = ("dupe_src", "dupe_peer", "clean_peer")


def _trade(
    agent_id: str,
    window_idx: int,
    *,
    tick: int = 100,
    symbol: str = "USDCAD",
    direction: str = "long",
    entry: float = 1.35000,
    stop: float = 1.34700,
    tp: float = 1.35450,
    tqs: float = 0.4,
) -> dict:
    w = WINDOWS[window_idx]
    e = w.oos_start.replace(month=6, day=15)
    return {
        "agent_id": agent_id,
        "entry_time": e.isoformat(sep=" "),
        "_window_idx": window_idx,
        "symbol": symbol,
        "direction": direction,
        "source_tick_id": tick,
        "entry": entry,
        "stop": stop,
        "take_profit": tp,
        "tqs_components": {"tqs": tqs},
    }


class TestTradePlanKey:
    def test_key_matches_on_float_noise_below_tolerance(self):
        a = _trade("x", 0, entry=1.3500000004)
        b = _trade("y", 0, entry=1.3500000001)
        assert c3.trade_plan_key(a) == c3.trade_plan_key(b)

    def test_key_differs_on_tp(self):
        a = _trade("x", 0, tp=1.35450)
        b = _trade("y", 0, tp=1.35500)
        assert c3.trade_plan_key(a) != c3.trade_plan_key(b)

    def test_key_differs_on_stop(self):
        a = _trade("x", 0, stop=1.34700)
        b = _trade("y", 0, stop=1.34600)
        assert c3.trade_plan_key(a) != c3.trade_plan_key(b)

    def test_key_differs_on_tick_symbol_direction(self):
        base = _trade("x", 0)
        assert c3.trade_plan_key(base) != c3.trade_plan_key(
            _trade("x", 0, tick=101)
        )
        assert c3.trade_plan_key(base) != c3.trade_plan_key(
            _trade("x", 0, symbol="EURUSD")
        )
        assert c3.trade_plan_key(base) != c3.trade_plan_key(
            _trade("x", 0, direction="short")
        )

    def test_key_handles_missing_prices(self):
        t = _trade("x", 0)
        del t["take_profit"]
        k = c3.trade_plan_key(t)
        assert math.isnan(k[5])
        # NaN != NaN -> a keyless trade can never be a duplicate.
        assert k not in {c3.trade_plan_key(_trade("y", 0))}


def _duplication_fixture() -> tuple[list[dict], list[dict]]:
    """Bachira/Barou-style literal duplication.

    Baseline: `dupe_src` takes 10 trades per window; `dupe_peer` takes
    1 distinct trade per window; `clean_peer` 5 per window.
    lo1 (dupe_src removed): `dupe_peer` picks up the SAME 10 trade
    plans plus its own 1 distinct trade; `clean_peer` unchanged.

    Under v1: dupe_peer reduction = (11 - 1) / 11 = 0.909 -> dirty in
    all 7 windows. Under v2: the 10 recovered trades are duplicates of
    dupe_src's baseline plans -> reduction = (1 - 1) / 1 = 0 -> clean.
    """
    baseline: list[dict] = []
    lo1: list[dict] = []
    for w in range(N_WINDOWS):
        for k in range(10):
            plan = dict(tick=1000 + 10 * w + k, entry=1.30 + 0.001 * k,
                        stop=1.29 + 0.001 * k, tp=1.32 + 0.001 * k)
            baseline.append(_trade("dupe_src", w, **plan))
            lo1.append(_trade("dupe_peer", w, **plan))
        distinct = dict(tick=5000 + w, entry=1.40, stop=1.39, tp=1.42)
        baseline.append(_trade("dupe_peer", w, **distinct))
        lo1.append(_trade("dupe_peer", w, **distinct))
        for k in range(5):
            p = dict(tick=9000 + 10 * w + k, symbol="EURUSD",
                     entry=1.10 + 0.001 * k, stop=1.09, tp=1.12)
            baseline.append(_trade("clean_peer", w, **p))
            lo1.append(_trade("clean_peer", w, **p))
    return baseline, lo1


class TestEvaluateC3V2:
    def test_duplication_artifact_flips_v2_but_not_v1(self):
        baseline, lo1 = _duplication_fixture()
        v1 = fv.evaluate_c3_final(
            "dupe_src", baseline_trades=baseline, lo1_trades=lo1,
            roster=ROSTER, n_windows=N_WINDOWS,
        )
        v2 = c3.evaluate_c3_v2(
            "dupe_src", baseline_trades=baseline, lo1_trades=lo1,
            roster=ROSTER, n_windows=N_WINDOWS,
        )
        assert not v1.passed and v1.statistic == 0.0
        assert v2.passed and v2.statistic == float(N_WINDOWS)
        dup = v2.evidence["duplicate_share"]["dupe_peer"]
        assert dup["lo1_duplicates"] == 10 * N_WINDOWS
        assert dup["lo1_duplicate_share"] > 0.90

    def test_v2_equals_v1_when_no_duplicates(self):
        baseline, lo1 = _duplication_fixture()
        # clean_peer has no trades matching anyone else's plans.
        v1 = fv.evaluate_c3_final(
            "clean_peer", baseline_trades=baseline, lo1_trades=lo1,
            roster=ROSTER, n_windows=N_WINDOWS,
        )
        v2 = c3.evaluate_c3_v2(
            "clean_peer", baseline_trades=baseline, lo1_trades=lo1,
            roster=ROSTER, n_windows=N_WINDOWS,
        )
        assert v1.statistic == v2.statistic
        assert v1.passed == v2.passed

    def test_real_cannibalisation_still_fails_v2(self):
        """Distinct-plan suppression must NOT be excused by v2."""
        baseline: list[dict] = []
        lo1: list[dict] = []
        for w in range(N_WINDOWS):
            # cannibal takes trades with its OWN plans.
            baseline.append(_trade(
                "dupe_src", w, tick=100 + w, entry=1.31, stop=1.30, tp=1.33,
            ))
            # peer trades 10x when cannibal absent, 1x when present --
            # and the peer's plans are DISTINCT from the cannibal's.
            baseline.append(_trade(
                "dupe_peer", w, tick=7000 + w, entry=1.41, stop=1.40, tp=1.43,
            ))
            for k in range(10):
                lo1.append(_trade(
                    "dupe_peer", w, tick=7000 + 100 * w + k,
                    entry=1.41 + 0.001 * k, stop=1.40, tp=1.43,
                ))
        v2 = c3.evaluate_c3_v2(
            "dupe_src", baseline_trades=baseline, lo1_trades=lo1,
            roster=ROSTER, n_windows=N_WINDOWS,
        )
        assert not v2.passed
        assert v2.statistic == 0.0

    def test_lo1_zero_guard_matches_v1(self):
        baseline = [_trade("dupe_peer", w) for w in range(N_WINDOWS)]
        lo1: list[dict] = []      # peer never trades without the agent
        v2 = c3.evaluate_c3_v2(
            "dupe_src", baseline_trades=baseline, lo1_trades=lo1,
            roster=ROSTER, n_windows=N_WINDOWS,
        )
        assert v2.passed
        assert v2.statistic == float(N_WINDOWS)


class TestSideBySideRender:
    def test_render_includes_advisory_and_rows(self):
        result = {
            "tag": "t", "arm": "phi41",
            "baseline_cache": "b", "lo1_root": "r", "lo1_tag": "x",
            "per_agent": {
                "a1": {
                    "status": "computed",
                    "v1_clean_windows": 0, "v1_pass": False,
                    "v2_clean_windows": 7, "v2_pass": True,
                    "v1_per_window": [], "v2_per_window": [],
                    "duplicate_share": {},
                    "worst_peer_lo1_duplicate_share": 0.97,
                },
                "a2": {"status": "lo1_cache_missing"},
            },
        }
        md = c3.render_side_by_side_md(result)
        assert "ADVISORY" in md
        assert "| `a1` | 0/7 | ❌ | 7/7 | ✅ | 97.0% |" in md
        assert "lo1_cache_missing" in md
