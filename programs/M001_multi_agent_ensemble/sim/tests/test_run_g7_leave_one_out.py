"""Tests for the G7 leave-one-out aggregation logic (Phase 3, 2026-07-03).

The compute side of the runner (``run_all_leave_one_outs``) is exercised
by the actual compute job -- it loads real bars, drives the squad
replay, and takes ~42 min per run, so it isn't unit-testable in the
same session. What IS unit-testable is the aggregation math + the
markdown/JSON emitters that consume on-disk trades caches. Those are
what these tests cover.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from programs.M001_multi_agent_ensemble.sim.scoring import (
    run_g7_leave_one_out as lo1,
)


UTC = timezone.utc


def _write_trades_jsonl(path: Path, trades: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for t in trades:
            fh.write(json.dumps(t) + "\n")


def _trade(agent_id: str, tqs: float) -> dict:
    """Trade dict matching the on-disk TradeRecord schema (composite
    TQS nested under ``tqs_components.tqs``). Kept minimal -- only
    the fields the aggregator reads are populated."""
    return {
        "agent_id": agent_id,
        "tqs_components": {"tqs": tqs},
    }


def _legacy_trade_top_level_tqs(agent_id: str, tqs: float) -> dict:
    """Legacy fixture shape from pre-2026-07-03 Phase R scratch caches
    (composite TQS at top level). The schema-tolerant reader accepts
    both; a dedicated test locks this behaviour so we don't
    accidentally break backward compatibility with older on-disk
    caches."""
    return {"agent_id": agent_id, "tqs": tqs}


# ---------------------------------------------------------------------------
# _per_agent_stats
# ---------------------------------------------------------------------------

class TestPerAgentStats:
    def test_empty_input_returns_empty_dict(self):
        assert lo1._per_agent_stats([]) == {}

    def test_single_agent_mean_and_count(self):
        trades = [_trade("isagi_yoichi", 0.3), _trade("isagi_yoichi", 0.5)]
        stats = lo1._per_agent_stats(trades)
        assert stats == {
            "isagi_yoichi": {"n_trades": 2.0, "mean_tqs": 0.4},
        }

    def test_multiple_agents(self):
        trades = [
            _trade("isagi_yoichi", 0.3),
            _trade("bachira_meguru", 0.5),
            _trade("bachira_meguru", 0.7),
        ]
        stats = lo1._per_agent_stats(trades)
        assert stats["isagi_yoichi"] == {"n_trades": 1.0, "mean_tqs": 0.3}
        assert stats["bachira_meguru"] == {"n_trades": 2.0, "mean_tqs": 0.6}

    def test_missing_agent_id_skipped(self):
        trades = [{"tqs": 0.3}, _trade("isagi_yoichi", 0.5)]
        stats = lo1._per_agent_stats(trades)
        assert list(stats.keys()) == ["isagi_yoichi"]

    def test_missing_tqs_counted_but_not_mean(self):
        trades = [
            {"agent_id": "isagi_yoichi", "tqs_components": {"tqs": None}},
            _trade("isagi_yoichi", 0.4),
        ]
        stats = lo1._per_agent_stats(trades)
        assert stats["isagi_yoichi"]["n_trades"] == 2.0
        # Only the numeric one contributes: mean = 0.4 / 1 = 0.4
        assert stats["isagi_yoichi"]["mean_tqs"] == pytest.approx(0.4)

    def test_extract_tqs_from_tqs_components(self):
        # Production schema: composite TQS lives at
        # tqs_components["tqs"]. This is what run_isagi_phi3_gate.py
        # emits when it serialises a TradeRecord to jsonl.
        t = {
            "agent_id": "isagi_yoichi",
            "tqs_components": {
                "r": 1.5, "efficiency": 0.7, "time_score": 0.7,
                "cleanliness": 1.0, "beauty_bonus": 1.0,
                "tqs": 0.679,
            },
        }
        assert lo1._extract_tqs(t) == pytest.approx(0.679)

    def test_extract_tqs_from_top_level_fallback(self):
        # Legacy schema (pre-2026-07-03 Phase R scratch caches). The
        # reader accepts it so older on-disk artefacts still
        # aggregate correctly.
        t = _legacy_trade_top_level_tqs("isagi_yoichi", 0.42)
        assert lo1._extract_tqs(t) == pytest.approx(0.42)

    def test_extract_tqs_missing_both_sources_returns_none(self):
        assert lo1._extract_tqs({"agent_id": "x"}) is None
        assert lo1._extract_tqs({"agent_id": "x", "tqs_components": {}}) is None
        assert lo1._extract_tqs(
            {"agent_id": "x", "tqs_components": None},
        ) is None

    def test_extract_tqs_non_numeric_returns_none(self):
        assert lo1._extract_tqs(
            {"agent_id": "x", "tqs_components": {"tqs": "0.5"}},
        ) == pytest.approx(0.5)  # str-of-float is coercible
        assert lo1._extract_tqs(
            {"agent_id": "x", "tqs_components": {"tqs": "high"}},
        ) is None
        assert lo1._extract_tqs(
            {"agent_id": "x", "tqs_components": {"tqs": None}, "tqs": "n/a"},
        ) is None

    def test_per_agent_stats_production_schema_end_to_end(self):
        # Mixes production schema + legacy schema in one input list
        # so a partially-migrated cache would still aggregate cleanly.
        trades = [
            _trade("isagi_yoichi", 0.3),
            _legacy_trade_top_level_tqs("isagi_yoichi", 0.5),
            _trade("bachira_meguru", 0.4),
        ]
        stats = lo1._per_agent_stats(trades)
        assert stats == {
            "isagi_yoichi": {"n_trades": 2.0, "mean_tqs": pytest.approx(0.4)},
            "bachira_meguru": {"n_trades": 1.0, "mean_tqs": pytest.approx(0.4)},
        }


# ---------------------------------------------------------------------------
# _load_trades_from_jsonl
# ---------------------------------------------------------------------------

class TestLoadTrades:
    def test_missing_file_returns_empty(self, tmp_path: Path):
        assert lo1._load_trades_from_jsonl(tmp_path / "nope.jsonl") == []

    def test_empty_file_returns_empty(self, tmp_path: Path):
        f = tmp_path / "a.jsonl"
        f.write_text("")
        assert lo1._load_trades_from_jsonl(f) == []

    def test_reads_one_trade_per_line(self, tmp_path: Path):
        f = tmp_path / "a.jsonl"
        _write_trades_jsonl(f, [
            _trade("isagi_yoichi", 0.3),
            _trade("bachira_meguru", 0.5),
        ])
        got = lo1._load_trades_from_jsonl(f)
        assert len(got) == 2
        assert got[0]["agent_id"] == "isagi_yoichi"

    def test_skips_blank_lines(self, tmp_path: Path):
        f = tmp_path / "a.jsonl"
        f.write_text(
            json.dumps(_trade("isagi_yoichi", 0.3)) + "\n\n"
            + json.dumps(_trade("bachira_meguru", 0.5)) + "\n",
        )
        got = lo1._load_trades_from_jsonl(f)
        assert len(got) == 2


# ---------------------------------------------------------------------------
# _compute_reduction_ratio
# ---------------------------------------------------------------------------

class TestReductionRatio:
    def test_zero_baseline(self):
        assert lo1._compute_reduction_ratio(baseline_n=0, lo1_n=10) == 0.0

    def test_positive_reduction(self):
        # peer had 5 trades in baseline; 10 without excluded -> 50% more.
        r = lo1._compute_reduction_ratio(baseline_n=5, lo1_n=10)
        assert r == pytest.approx(0.5)

    def test_zero_effect(self):
        r = lo1._compute_reduction_ratio(baseline_n=5, lo1_n=5)
        assert r == 0.0

    def test_lo1_zero(self):
        r = lo1._compute_reduction_ratio(baseline_n=5, lo1_n=0)
        assert r == 1.0

    def test_negative_when_excluded_agent_helped_peer(self):
        r = lo1._compute_reduction_ratio(baseline_n=10, lo1_n=5)
        # peer traded LESS without excluded agent -> excluded lifted peer.
        assert r == pytest.approx(-1.0)


# ---------------------------------------------------------------------------
# compute_c2_c3
# ---------------------------------------------------------------------------

class TestComputeC2C3:
    def _baseline_stats(self):
        return {
            "isagi_yoichi": {"n_trades": 100, "mean_tqs": 0.30},
            "bachira_meguru": {"n_trades": 200, "mean_tqs": 0.32},
            "chigiri_hyoma": {"n_trades": 50, "mean_tqs": 0.24},
        }

    def test_c2_pass_via_tqs_lift(self):
        # Excluded=chigiri. When chigiri absent, bachira's TQS drops
        # from 0.32 to 0.30 => chigiri's presence lifts bachira by
        # +0.02 (>0.005 epsilon), so C2 PASSES for chigiri.
        per_excluded_stats = {
            "chigiri_hyoma": {
                "isagi_yoichi": {"n_trades": 100, "mean_tqs": 0.30},
                "bachira_meguru": {"n_trades": 200, "mean_tqs": 0.30},
            },
        }
        c2c3 = lo1.compute_c2_c3(
            baseline_stats=self._baseline_stats(),
            per_excluded_stats=per_excluded_stats,
        )
        r = c2c3["chigiri_hyoma"]
        assert r.c2_pass is True
        assert "bachira_meguru" in r.c2_reason

    def test_c2_pass_via_trade_count_lift(self):
        # Excluded=chigiri. When chigiri absent, isagi's trades DROP
        # from 100 to 80 => chigiri's presence lifts isagi by +20 trades.
        per_excluded_stats = {
            "chigiri_hyoma": {
                "isagi_yoichi": {"n_trades": 80, "mean_tqs": 0.30},
                "bachira_meguru": {"n_trades": 200, "mean_tqs": 0.32},
            },
        }
        c2c3 = lo1.compute_c2_c3(
            baseline_stats=self._baseline_stats(),
            per_excluded_stats=per_excluded_stats,
        )
        r = c2c3["chigiri_hyoma"]
        assert r.c2_pass is True
        assert "isagi_yoichi" in r.c2_reason

    def test_c2_reason_reports_strongest_lift_not_first_hit(self):
        # Regression guard for the 2026-07-03 05:36 UTC finding: two
        # peers pass C2 threshold, one by a marginal trade-count nudge
        # (bachira +1 trade = 1x epsilon) and one by a massive TQS lift
        # (isagi +0.10 TQS = 20x epsilon). The reason string MUST
        # attribute to isagi, not bachira. Pre-fix (first-hit) would
        # have attributed to bachira because dict order is bachira
        # first. This is the bug that would have made Reo's Nagi
        # signal (+0.0719 TQS) invisible under Bachira's +0.0009 TQS.
        baseline = {
            "isagi_yoichi": {"n_trades": 100, "mean_tqs": 0.30},
            "bachira_meguru": {"n_trades": 100, "mean_tqs": 0.30},
        }
        per_excluded_stats = {
            "chigiri_hyoma": {
                "bachira_meguru": {  # marginal: +1 trade
                    "n_trades": 99, "mean_tqs": 0.30,
                },
                "isagi_yoichi": {  # strong: +0.10 TQS
                    "n_trades": 100, "mean_tqs": 0.20,
                },
            },
        }
        c2c3 = lo1.compute_c2_c3(
            baseline_stats=baseline,
            per_excluded_stats=per_excluded_stats,
        )
        r = c2c3["chigiri_hyoma"]
        assert r.c2_pass is True
        # STRONGEST peer wins the reason string.
        assert "isagi_yoichi" in r.c2_reason
        assert "bachira_meguru" not in r.c2_reason
        # Metric attribution surfaced.
        assert "strongest on tqs" in r.c2_reason

    def test_c2_reason_prefers_trade_count_when_larger(self):
        # Inverse: a peer with a huge trade-count delta should beat
        # a peer with a marginal TQS delta.
        baseline = {
            "isagi_yoichi": {"n_trades": 100, "mean_tqs": 0.30},
            "bachira_meguru": {"n_trades": 100, "mean_tqs": 0.30},
        }
        per_excluded_stats = {
            "chigiri_hyoma": {
                "isagi_yoichi": {  # marginal: +0.006 TQS = 1.2x eps
                    "n_trades": 100, "mean_tqs": 0.294,
                },
                "bachira_meguru": {  # strong: +50 trades = 50x eps
                    "n_trades": 50, "mean_tqs": 0.30,
                },
            },
        }
        c2c3 = lo1.compute_c2_c3(
            baseline_stats=baseline,
            per_excluded_stats=per_excluded_stats,
        )
        r = c2c3["chigiri_hyoma"]
        assert r.c2_pass is True
        assert "bachira_meguru" in r.c2_reason
        assert "strongest on trades" in r.c2_reason

    def test_c2_fail_no_peer_helped(self):
        # Excluded=chigiri. Removing chigiri leaves every peer BETTER
        # or same => chigiri is a leech, no positive-sum chemistry.
        per_excluded_stats = {
            "chigiri_hyoma": {
                "isagi_yoichi": {"n_trades": 120, "mean_tqs": 0.32},
                "bachira_meguru": {"n_trades": 220, "mean_tqs": 0.33},
            },
        }
        c2c3 = lo1.compute_c2_c3(
            baseline_stats=self._baseline_stats(),
            per_excluded_stats=per_excluded_stats,
        )
        r = c2c3["chigiri_hyoma"]
        assert r.c2_pass is False
        assert "no peer lifted" in r.c2_reason

    def test_c3_fail_on_cannibalisation(self):
        # Excluded=bachira. When bachira absent, isagi trades rise from
        # 100 to 300 (200% more) => bachira was cannibalising isagi.
        per_excluded_stats = {
            "bachira_meguru": {
                "isagi_yoichi": {"n_trades": 300, "mean_tqs": 0.30},
                "chigiri_hyoma": {"n_trades": 50, "mean_tqs": 0.24},
            },
        }
        c2c3 = lo1.compute_c2_c3(
            baseline_stats=self._baseline_stats(),
            per_excluded_stats=per_excluded_stats,
        )
        r = c2c3["bachira_meguru"]
        assert r.c3_pass is False
        assert r.c3_worst_peer == "isagi_yoichi"
        assert "CANNIBALISATION" in r.c3_reason

    def test_c3_pass_when_reductions_small(self):
        # 20% peer increase without excluded agent -> below 50% threshold.
        per_excluded_stats = {
            "chigiri_hyoma": {
                "isagi_yoichi": {"n_trades": 120, "mean_tqs": 0.30},
                "bachira_meguru": {"n_trades": 230, "mean_tqs": 0.32},
            },
        }
        c2c3 = lo1.compute_c2_c3(
            baseline_stats=self._baseline_stats(),
            per_excluded_stats=per_excluded_stats,
        )
        r = c2c3["chigiri_hyoma"]
        assert r.c3_pass is True

    def test_delta_populated_for_every_peer(self):
        per_excluded_stats = {
            "chigiri_hyoma": {
                "isagi_yoichi": {"n_trades": 100, "mean_tqs": 0.30},
                "bachira_meguru": {"n_trades": 200, "mean_tqs": 0.32},
            },
        }
        c2c3 = lo1.compute_c2_c3(
            baseline_stats=self._baseline_stats(),
            per_excluded_stats=per_excluded_stats,
        )
        r = c2c3["chigiri_hyoma"]
        assert "isagi_yoichi" in r.per_peer_delta_trades
        assert "bachira_meguru" in r.per_peer_delta_trades
        # Excluded agent itself is skipped from the peer deltas.
        assert "chigiri_hyoma" not in r.per_peer_delta_trades


# ---------------------------------------------------------------------------
# aggregate_from_disk
# ---------------------------------------------------------------------------

class TestAggregateFromDisk:
    def test_missing_lo1_caches_leave_verdict_pending(
        self, tmp_path: Path, caplog,
    ):
        # Seed only a baseline; no lo1 caches at all.
        baseline_dir = tmp_path / "baseline"
        _write_trades_jsonl(
            baseline_dir / "trades.jsonl",
            [_trade("isagi_yoichi", 0.3)],
        )
        baseline_stats, per_excluded, c2c3, role_registry = (
            lo1.aggregate_from_disk(
                baseline_cache_dir=baseline_dir,
                lo1_root_dir=tmp_path,
                tag="unit",
            )
        )
        assert "isagi_yoichi" in baseline_stats
        assert per_excluded == {}
        assert c2c3 == {}
        # Role registry always emits results for every agent in
        # G7_AGENT_ORDER (with 0/waived values when data is missing).
        assert set(role_registry.keys()) == set(lo1.G7_AGENT_ORDER)

    def test_end_to_end_two_lo1(self, tmp_path: Path):
        baseline_dir = tmp_path / "baseline"
        _write_trades_jsonl(baseline_dir / "trades.jsonl", [
            _trade("isagi_yoichi", 0.30),
            _trade("isagi_yoichi", 0.32),
            _trade("bachira_meguru", 0.34),
            _trade("chigiri_hyoma", 0.24),
        ])
        # lo1 excluded=chigiri: isagi TQS drops
        # (chigiri presence lifted isagi) -> C2 PASS for chigiri.
        _write_trades_jsonl(
            tmp_path / "g7_leave_one_out_unit"
            / "lo1_chigiri_hyoma" / "trades.jsonl",
            [
                _trade("isagi_yoichi", 0.20),
                _trade("bachira_meguru", 0.34),
            ],
        )
        # lo1 excluded=bachira: isagi trade count balloons from 2 to
        # 8 -> (8-2)/8 = 75% > 50% threshold -> bachira cannibalised
        # isagi -> C3 FAIL.
        _write_trades_jsonl(
            tmp_path / "g7_leave_one_out_unit"
            / "lo1_bachira_meguru" / "trades.jsonl",
            [
                _trade("isagi_yoichi", 0.30),
                _trade("isagi_yoichi", 0.30),
                _trade("isagi_yoichi", 0.30),
                _trade("isagi_yoichi", 0.30),
                _trade("isagi_yoichi", 0.30),
                _trade("isagi_yoichi", 0.30),
                _trade("isagi_yoichi", 0.30),
                _trade("isagi_yoichi", 0.30),
                _trade("chigiri_hyoma", 0.24),
            ],
        )
        baseline_stats, per_excluded, c2c3, role_registry = (
            lo1.aggregate_from_disk(
                baseline_cache_dir=baseline_dir,
                lo1_root_dir=tmp_path,
                tag="unit",
            )
        )
        assert set(c2c3.keys()) == {"chigiri_hyoma", "bachira_meguru"}
        assert c2c3["chigiri_hyoma"].c2_pass is True
        assert c2c3["bachira_meguru"].c3_pass is False
        # Role Registry always covers every agent in G7_AGENT_ORDER.
        assert set(role_registry.keys()) == set(lo1.G7_AGENT_ORDER)


# ---------------------------------------------------------------------------
# Role Registry v1 (C7 / C8 proxy / C9 / role labels / retention)
# ---------------------------------------------------------------------------

class TestRoleRegistry:
    def _baseline_and_lo1(self):
        # 4-agent toy panel: X = "star_finisher" is what C7 should
        # detect. Two peers (catalyst_a, catalyst_b) lift X's TQS when
        # they are present; a third peer (solo) does not.
        baseline_stats = {
            "isagi_yoichi": {"n_trades": 100, "mean_tqs": 0.35},
            "bachira_meguru": {"n_trades": 200, "mean_tqs": 0.40},
            "nagi_seishiro": {"n_trades": 50, "mean_tqs": 0.50},
            "chigiri_hyoma": {"n_trades": 30, "mean_tqs": 0.30},
        }
        # nagi is the "star_finisher"; isagi + bachira both lift nagi's
        # mean_tqs by 0.03 when they are present.
        per_excluded_stats = {
            "isagi_yoichi": {  # remove isagi -> nagi's TQS drops
                "bachira_meguru": {"n_trades": 200, "mean_tqs": 0.40},
                "nagi_seishiro": {"n_trades": 50, "mean_tqs": 0.47},
                "chigiri_hyoma": {"n_trades": 30, "mean_tqs": 0.30},
            },
            "bachira_meguru": {  # remove bachira -> nagi's TQS drops
                "isagi_yoichi": {"n_trades": 100, "mean_tqs": 0.35},
                "nagi_seishiro": {"n_trades": 50, "mean_tqs": 0.47},
                "chigiri_hyoma": {"n_trades": 30, "mean_tqs": 0.30},
            },
            "nagi_seishiro": {  # remove nagi -> no peer changes
                "isagi_yoichi": {"n_trades": 100, "mean_tqs": 0.35},
                "bachira_meguru": {"n_trades": 200, "mean_tqs": 0.40},
                "chigiri_hyoma": {"n_trades": 30, "mean_tqs": 0.30},
            },
            "chigiri_hyoma": {  # remove chigiri -> no peer changes
                "isagi_yoichi": {"n_trades": 100, "mean_tqs": 0.35},
                "bachira_meguru": {"n_trades": 200, "mean_tqs": 0.40},
                "nagi_seishiro": {"n_trades": 50, "mean_tqs": 0.50},
            },
        }
        return baseline_stats, per_excluded_stats

    def test_c7_pass_for_star_finisher(self):
        baseline, lo1_stats = self._baseline_and_lo1()
        rr = lo1.compute_c7(
            baseline_stats=baseline,
            per_excluded_stats=lo1_stats,
        )
        nagi = rr["nagi_seishiro"]
        assert nagi.c7_pass is True
        assert len(nagi.c7_lifting_peers) == 2
        assert set(nagi.c7_lifting_peers.keys()) == {
            "isagi_yoichi", "bachira_meguru",
        }
        assert "isagi_yoichi" in nagi.c7_reason
        assert "bachira_meguru" in nagi.c7_reason

    def test_c7_fail_for_solo_scorer(self):
        baseline, lo1_stats = self._baseline_and_lo1()
        rr = lo1.compute_c7(
            baseline_stats=baseline,
            per_excluded_stats=lo1_stats,
        )
        # chigiri gets no lift from any peer
        chigiri = rr["chigiri_hyoma"]
        assert chigiri.c7_pass is False
        assert len(chigiri.c7_lifting_peers) == 0

    def test_c7_waived_for_zero_trade_agents(self):
        # Simulate reo_mikage (0 trades) -- C7 has no TQS to measure.
        baseline = {"reo_mikage": {"n_trades": 0, "mean_tqs": 0.0}}
        rr = lo1.compute_c7(
            baseline_stats=baseline,
            per_excluded_stats={},
        )
        assert rr["reo_mikage"].c7_status == "waived"
        assert rr["reo_mikage"].c7_pass is False

    def test_c8_proxy_pass_when_workspace_activity_high(self):
        baseline, lo1_stats = self._baseline_and_lo1()
        # bachira excluded produces peer delta: nagi -0.03 tqs =
        # 6 eps, ~0 trades. Only ~6 eps -- doesn't cross 50.
        # Fabricate an "isagi" scenario where removing isagi produces
        # LARGE trade delta for bachira to exercise the pass path.
        lo1_stats["isagi_yoichi"]["bachira_meguru"] = {
            "n_trades": 100, "mean_tqs": 0.40,
        }
        rr = lo1.compute_c7(
            baseline_stats=baseline,
            per_excluded_stats=lo1_stats,
        )
        lo1.compute_c8_proxy(
            per_excluded_stats=lo1_stats,
            baseline_stats=baseline,
            results=rr,
        )
        # Removing isagi drops bachira from 200 -> 100 trades =
        # 100 epsilon-units. Plus nagi 3 tqs = 6 eps. Total >= 50.
        isagi = rr["isagi_yoichi"]
        assert isagi.c8_pass is True
        # Top-impacted peer should be bachira (largest single-peer impact).
        assert isagi.c8_top_impacted_peer == "bachira_meguru"

    def test_c8_proxy_fail_for_workspace_ghost(self):
        # Kunigami-like: removing X produces ZERO delta on any peer.
        baseline = {
            "isagi_yoichi": {"n_trades": 100, "mean_tqs": 0.35},
            "kunigami_rensuke": {"n_trades": 0, "mean_tqs": 0.0},
        }
        per_excluded = {
            "kunigami_rensuke": {
                "isagi_yoichi": {"n_trades": 100, "mean_tqs": 0.35},
            },
        }
        rr = lo1.compute_c7(
            baseline_stats=baseline, per_excluded_stats=per_excluded,
        )
        lo1.compute_c8_proxy(
            per_excluded_stats=per_excluded,
            baseline_stats=baseline,
            results=rr,
        )
        kunigami = rr["kunigami_rensuke"]
        assert kunigami.c8_pass is False
        assert kunigami.c8_workspace_impact_epsilons == 0.0

    def test_c9_pass_when_volume_share_above_floor(self):
        # bachira has 200/380 trades = 52.6% share -- passes 5% floor.
        baseline, _ = self._baseline_and_lo1()
        rr = {aid: lo1.RoleRegistryResult(agent_id=aid) for aid in baseline}
        lo1.compute_c9(baseline_stats=baseline, results=rr)
        # nagi 50/380 = 13% > 5%
        assert rr["nagi_seishiro"].c9_pass is True
        # bachira 200/380 = 52%
        assert rr["bachira_meguru"].c9_pass is True

    def test_c9_waived_for_structural_falsifier(self):
        # reo has 0 trades and is a structural falsifier.
        baseline = {"reo_mikage": {"n_trades": 0, "mean_tqs": 0.0}}
        rr = {"reo_mikage": lo1.RoleRegistryResult(agent_id="reo_mikage")}
        lo1.compute_c9(baseline_stats=baseline, results=rr)
        assert rr["reo_mikage"].c9_status == "waived"
        assert rr["reo_mikage"].c9_pass is False

    def test_role_label_chemistry_catalyst_when_c2_passes(self):
        baseline, lo1_stats = self._baseline_and_lo1()
        c2c3 = lo1.compute_c2_c3(
            baseline_stats=baseline, per_excluded_stats=lo1_stats,
        )
        rr = lo1.compute_role_registry(
            baseline_stats=baseline,
            per_excluded_stats=lo1_stats,
            c2c3=c2c3,
        )
        # isagi + bachira both lift nagi -- they are chemistry catalysts.
        assert "chemistry_catalyst" in rr["isagi_yoichi"].role_labels
        assert "chemistry_catalyst" in rr["bachira_meguru"].role_labels

    def test_role_label_finisher_when_c7_passes(self):
        baseline, lo1_stats = self._baseline_and_lo1()
        c2c3 = lo1.compute_c2_c3(
            baseline_stats=baseline, per_excluded_stats=lo1_stats,
        )
        rr = lo1.compute_role_registry(
            baseline_stats=baseline,
            per_excluded_stats=lo1_stats,
            c2c3=c2c3,
        )
        # nagi is lifted by 2 peers -> C7 pass -> finisher label.
        assert "finisher" in rr["nagi_seishiro"].role_labels

    def test_role_label_retirement_candidate_when_all_fail(self):
        # Fabricate an agent that fails C2 + C7 + C8 + C9.
        baseline = {
            "isagi_yoichi": {"n_trades": 100, "mean_tqs": 0.35},
            "dead_weight_agent": {"n_trades": 1, "mean_tqs": 0.30},
        }
        per_excluded = {
            "dead_weight_agent": {
                "isagi_yoichi": {"n_trades": 100, "mean_tqs": 0.35},
            },
            "isagi_yoichi": {
                "dead_weight_agent": {"n_trades": 1, "mean_tqs": 0.30},
            },
        }
        c2c3 = lo1.compute_c2_c3(
            baseline_stats=baseline, per_excluded_stats=per_excluded,
        )
        rr = lo1.compute_role_registry(
            baseline_stats=baseline,
            per_excluded_stats=per_excluded,
            c2c3=c2c3,
        )
        # dead_weight_agent isn't in G7_AGENT_ORDER, so it won't be
        # scored -- verify the mechanism works for real agents by
        # asserting kunigami hits retirement.
        # (kunigami will be in G7_AGENT_ORDER; with no data it fails
        # all criteria.)
        kunigami = rr.get("kunigami_rensuke")
        assert kunigami is not None
        assert "retirement_candidate" in kunigami.role_labels

    def test_retention_requires_c3_and_one_role_axis(self):
        # kunigami with only C3 pass but no role axis -> NOT retained.
        baseline, lo1_stats = self._baseline_and_lo1()
        c2c3 = lo1.compute_c2_c3(
            baseline_stats=baseline, per_excluded_stats=lo1_stats,
        )
        rr = lo1.compute_role_registry(
            baseline_stats=baseline,
            per_excluded_stats=lo1_stats,
            c2c3=c2c3,
        )
        # kunigami: no data in fixture -> C3 defaults to True, but
        # no C2/C7/C8/C9 pass -> should NOT be retained.
        # nagi: C7 pass -> IS retained.
        assert rr["nagi_seishiro"].retained is True
        # kunigami is in G7_AGENT_ORDER but not in the toy fixture,
        # so its C2 defaults to fail; C3 defaults to True; C7/C8/C9
        # all fail. Not retained.
        assert rr["kunigami_rensuke"].retained is False


# ---------------------------------------------------------------------------
# Markdown/JSON emitters
# ---------------------------------------------------------------------------

class TestEmitters:
    def _fake_verdict(self):
        baseline_stats = {
            "isagi_yoichi": {"n_trades": 100, "mean_tqs": 0.30},
            "bachira_meguru": {"n_trades": 200, "mean_tqs": 0.32},
        }
        per_excluded = {
            "isagi_yoichi": {
                "bachira_meguru": {"n_trades": 210, "mean_tqs": 0.31},
            },
        }
        c2c3 = lo1.compute_c2_c3(
            baseline_stats=baseline_stats,
            per_excluded_stats=per_excluded,
        )
        return baseline_stats, per_excluded, c2c3

    def test_markdown_emits_expected_sections(self, tmp_path: Path):
        baseline_stats, per_excluded, c2c3 = self._fake_verdict()
        md_path = tmp_path / "verdict.md"
        lo1.emit_c2_c3_verdict_md(
            baseline_stats=baseline_stats,
            per_excluded_stats=per_excluded,
            c2c3=c2c3,
            out_path=md_path,
            tag="unit",
        )
        content = md_path.read_text()
        assert "G7 leave-one-out C2/C3 verdict (unit)" in content
        assert "## Baseline per-agent stats" in content
        assert "## Criterion 2" in content
        assert "## Criterion 3" in content
        assert "isagi_yoichi" in content

    def test_json_roundtrip(self, tmp_path: Path):
        baseline_stats, per_excluded, c2c3 = self._fake_verdict()
        json_path = tmp_path / "verdict.json"
        lo1.emit_c2_c3_verdict_json(
            baseline_stats=baseline_stats,
            per_excluded_stats=per_excluded,
            c2c3=c2c3,
            out_path=json_path,
            tag="unit",
        )
        payload = json.loads(json_path.read_text())
        assert payload["tag"] == "unit"
        assert "baseline_stats" in payload
        assert "c2_c3" in payload
        assert "isagi_yoichi" in payload["c2_c3"]

    def test_role_registry_md_emits_all_sections(self, tmp_path: Path):
        baseline_stats, per_excluded, c2c3 = self._fake_verdict()
        role_registry = lo1.compute_role_registry(
            baseline_stats=baseline_stats,
            per_excluded_stats=per_excluded,
            c2c3=c2c3,
        )
        md_path = tmp_path / "role_verdict.md"
        lo1.emit_role_registry_verdict_md(
            baseline_stats=baseline_stats,
            c2c3=c2c3,
            role_registry=role_registry,
            out_path=md_path,
            tag="unit",
        )
        content = md_path.read_text()
        assert "G7 Role Registry v1 verdict (unit)" in content
        assert "## Role Registry summary" in content
        assert "## Criterion 7" in content
        assert "## Criterion 8" in content
        assert "## Criterion 9" in content
        assert "## Retention verdict" in content
        assert "## Squad-level verdict" in content

    def test_role_registry_json_roundtrip(self, tmp_path: Path):
        baseline_stats, per_excluded, c2c3 = self._fake_verdict()
        role_registry = lo1.compute_role_registry(
            baseline_stats=baseline_stats,
            per_excluded_stats=per_excluded,
            c2c3=c2c3,
        )
        json_path = tmp_path / "role_verdict.json"
        lo1.emit_role_registry_verdict_json(
            baseline_stats=baseline_stats,
            c2c3=c2c3,
            role_registry=role_registry,
            out_path=json_path,
            tag="unit",
        )
        payload = json.loads(json_path.read_text())
        assert payload["tag"] == "unit"
        assert "role_registry" in payload
        # Every G7 agent must have a role_registry entry (waived or not).
        for aid in lo1.G7_AGENT_ORDER:
            assert aid in payload["role_registry"]
            entry = payload["role_registry"][aid]
            assert "c7_pass" in entry
            assert "c8_pass" in entry
            assert "c9_pass" in entry
            assert "role_labels" in entry
            assert "retained" in entry


# ---------------------------------------------------------------------------
# CLI parser sanity
# ---------------------------------------------------------------------------

class TestCliParser:
    def test_defaults(self):
        args = lo1.build_arg_parser().parse_args([])
        assert args.tag == "post-V"
        assert args.aggregate_only is False
        assert args.exclude is None

    def test_exclude_repeatable(self):
        args = lo1.build_arg_parser().parse_args([
            "--exclude", "isagi_yoichi",
            "--exclude", "bachira_meguru",
        ])
        assert args.exclude == ["isagi_yoichi", "bachira_meguru"]
