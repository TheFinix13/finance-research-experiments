"""Phi4 squad gate harness -- smoke + verdict logic tests.

Two layers:

  1. Pure unit tests for `_phi4_aggregate` (no production-repo
     dependency): per-symbol highest-conviction-wins, rejected
     proposals journalled with provenance.
  2. Pure unit tests for `_decide_squad_verdict`: PASS / PARTIAL /
     FAIL / PROVISIONAL thresholds against the user-spec ratio gates.

Real-data slow runs are exercised by `run_phi4_squad_gate.run_squad_gate`
itself (manual CLI). Smoke testing the full driver would re-run the
production-repo loader -- already covered by `test_phi3_gate.py`.
"""
from __future__ import annotations

from dataclasses import field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from programs.M001_multi_agent_ensemble.sim._cross_repo import (
    production_repo_available,
)
from programs.M001_multi_agent_ensemble.sim.core.types import (
    AgentProposal,
    LadderRung,
)


# ---------------------------------------------------------------------------
# Helpers (no production-repo dependency)
# ---------------------------------------------------------------------------

def _proposal(
    *,
    agent_id: str,
    symbol: str = "EURUSD",
    direction: str = "long",
    conviction: float = 0.7,
    tick_id: int = 0,
    agent_tier: int = 2,
) -> AgentProposal:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return AgentProposal(
        agent_id=agent_id, tick_id=tick_id,
        source_thought_id=f"{agent_id}:{tick_id}:{symbol}",
        timestamp=base, symbol=symbol,
        direction=direction,
        entry=1.1000, stop=1.0950,
        ladder=[LadderRung(price=1.1100, fraction=1.0)],
        conviction=conviction, regime_fit=0.5,
        valid_until=base + timedelta(hours=24),
        rationale={"stub": True},
        agent_tier=agent_tier,
    )


# ---------------------------------------------------------------------------
# _phi4_aggregate
# ---------------------------------------------------------------------------

def test_aggregator_picks_highest_conviction_per_symbol():
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        _phi4_aggregate,
    )
    isagi = _proposal(agent_id="isagi_yoichi", conviction=0.65)
    nagi = _proposal(agent_id="nagi_seishiro", conviction=0.85)
    barou = _proposal(
        agent_id="barou_shoei", symbol="USDCAD", conviction=0.75,
    )
    out = _phi4_aggregate([isagi, nagi, barou], tick_id=42)
    # 2 winners (one per symbol), 1 rejected (the lower-conviction EURUSD).
    assert len(out.accepted) == 2
    accepted_ids = {p.agent_id for p in out.accepted}
    assert accepted_ids == {"nagi_seishiro", "barou_shoei"}
    assert len(out.rejected) == 1
    rej = out.rejected[0]
    assert rej["winner_agent_id"] == "nagi_seishiro"
    assert rej["loser_agent_id"] == "isagi_yoichi"
    assert rej["rejection_reason"] == "lower_conviction_same_symbol"
    assert rej["tick_id"] == 42


def test_aggregator_deterministic_tiebreak_on_conviction():
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        _phi4_aggregate,
    )
    # Two peer-tier proposals at IDENTICAL conviction -> tiebreaker is
    # (agent_tier asc, agent_id asc). Both tier 2 here, so falls back to
    # lex on agent_id.
    a = _proposal(agent_id="zz_late", conviction=0.80)
    b = _proposal(agent_id="aa_early", conviction=0.80)
    out = _phi4_aggregate([a, b], tick_id=0)
    assert len(out.accepted) == 1
    assert out.accepted[0].agent_id == "aa_early"  # lex tie-break


def test_aggregator_tier_anchor_wins_same_base_conviction():
    """Phase N (2026-07-01) -- Tier-1 anchor (Isagi) wins tiebreak over
    tier-2 peer at same base conviction, even when the peer sorts
    alphabetically before Isagi. The peer must exceed anchor conviction
    by TIER_BIAS to override.
    """
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        _phi4_aggregate, TIER_BIAS,
    )
    isagi = _proposal(agent_id="isagi_yoichi", conviction=0.65, agent_tier=1)
    bachira = _proposal(agent_id="bachira_meguru", conviction=0.65, agent_tier=2)
    out = _phi4_aggregate([bachira, isagi], tick_id=0)
    # Isagi wins tiebreak despite bachira_* sorting alphabetically first.
    assert out.accepted[0].agent_id == "isagi_yoichi"
    # Bachira at (anchor + TIER_BIAS - epsilon) still loses.
    bachira_just_below = _proposal(
        agent_id="bachira_meguru",
        conviction=0.65 + TIER_BIAS - 0.001, agent_tier=2,
    )
    out = _phi4_aggregate([bachira_just_below, isagi], tick_id=0)
    assert out.accepted[0].agent_id == "isagi_yoichi"
    # Bachira at (anchor + TIER_BIAS + epsilon) overrides.
    bachira_just_above = _proposal(
        agent_id="bachira_meguru",
        conviction=0.65 + TIER_BIAS + 0.001, agent_tier=2,
    )
    out = _phi4_aggregate([bachira_just_above, isagi], tick_id=0)
    assert out.accepted[0].agent_id == "bachira_meguru"


def test_aggregator_ranked_by_symbol_supports_slot_fallback():
    """Phase N -- aggregator exposes the full per-symbol ranked list so
    the sentinel loop in _drive_squad_replay can cede a blocked winner's
    slot to the next-ranked proposal.
    """
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        _phi4_aggregate,
    )
    isagi = _proposal(agent_id="isagi_yoichi", conviction=0.75, agent_tier=1)
    bachira = _proposal(agent_id="bachira_meguru", conviction=0.72, agent_tier=2)
    # Rin needs to exceed anchor + TIER_BIAS to override -> conviction 0.85.
    rin = _proposal(agent_id="itoshi_rin", conviction=0.85, agent_tier=2)
    out = _phi4_aggregate([bachira, isagi, rin], tick_id=0)
    ranked = out.ranked_by_symbol["EURUSD"]
    assert len(ranked) == 3
    # Rin adj=0.80 > isagi adj=0.75 > bachira adj=0.67 -> Rin overrides anchor.
    assert ranked[0].agent_id == "itoshi_rin"
    assert ranked[1].agent_id == "isagi_yoichi"
    assert ranked[2].agent_id == "bachira_meguru"


def test_aggregator_returns_empty_on_no_proposals():
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        _phi4_aggregate,
    )
    out = _phi4_aggregate([], tick_id=0)
    assert out.accepted == []
    assert out.rejected == []


def test_aggregator_no_collision_returns_all_winners():
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        _phi4_aggregate,
    )
    a = _proposal(agent_id="a", symbol="EURUSD", conviction=0.5)
    b = _proposal(agent_id="b", symbol="GBPUSD", conviction=0.5)
    c = _proposal(agent_id="c", symbol="USDCAD", conviction=0.5)
    out = _phi4_aggregate([a, b, c], tick_id=0)
    assert len(out.accepted) == 3
    assert out.rejected == []


# ---------------------------------------------------------------------------
# _decide_squad_verdict
# ---------------------------------------------------------------------------

def _build_squad_report(
    *,
    squad_tqs: float = 0.350,
    n_trades: int = 100,
):
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        ISAGI_ALONE_MEDIAN_OOS_PIPS, ISAGI_ALONE_MEDIAN_OOS_TQS,
        SquadGateReport,
    )
    ratio = squad_tqs / ISAGI_ALONE_MEDIAN_OOS_TQS
    return SquadGateReport(
        full_start=datetime(2015, 1, 1, tzinfo=timezone.utc),
        full_end=datetime(2025, 12, 31, tzinfo=timezone.utc),
        symbols=("EURUSD", "USDCAD"),
        n_thoughts=20000, n_proposals_all=500,
        n_proposals_accepted=400, n_proposals_rejected=100,
        n_trades=n_trades,
        per_agent_trade_counts={"isagi_yoichi": 80, "nagi_seishiro": 20},
        per_agent_overall_kpis={},
        squad_median_oos_window_mean_pips=12.0,
        squad_mean_oos_window_mean_pips=12.0,
        squad_median_oos_window_mean_tqs=squad_tqs,
        squad_oos_windows_positive=7,
        squad_oos_windows_total=7,
        isagi_alone_median_oos_pips=ISAGI_ALONE_MEDIAN_OOS_PIPS,
        isagi_alone_median_oos_tqs=ISAGI_ALONE_MEDIAN_OOS_TQS,
        squad_vs_isagi_tqs_ratio=ratio,
        verdict="PENDING", verdict_reason="",
    )


def test_verdict_pass_at_or_above_1_10x():
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        ISAGI_ALONE_MEDIAN_OOS_TQS,
        _decide_squad_verdict,
    )
    # 1.10x of Isagi-alone median OOS TQS.
    r = _build_squad_report(
        squad_tqs=ISAGI_ALONE_MEDIAN_OOS_TQS * 1.10, n_trades=100,
    )
    v, reason = _decide_squad_verdict(r)
    assert v == "PASS", reason


def test_verdict_partial_between_1_00_and_1_10x():
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        ISAGI_ALONE_MEDIAN_OOS_TQS,
        _decide_squad_verdict,
    )
    r = _build_squad_report(
        squad_tqs=ISAGI_ALONE_MEDIAN_OOS_TQS * 1.05, n_trades=100,
    )
    v, reason = _decide_squad_verdict(r)
    assert v == "PARTIAL", reason


def test_verdict_fail_below_1_00x():
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        ISAGI_ALONE_MEDIAN_OOS_TQS,
        _decide_squad_verdict,
    )
    r = _build_squad_report(
        squad_tqs=ISAGI_ALONE_MEDIAN_OOS_TQS * 0.90, n_trades=100,
    )
    v, reason = _decide_squad_verdict(r)
    assert v == "FAIL", reason
    assert "LOST edge" in reason


def test_verdict_provisional_when_too_few_trades():
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        _decide_squad_verdict,
    )
    r = _build_squad_report(squad_tqs=0.5, n_trades=20)  # below floor
    v, reason = _decide_squad_verdict(r)
    assert v == "PROVISIONAL", reason


# ---------------------------------------------------------------------------
# Rejection-analysis bucket logic
# ---------------------------------------------------------------------------

def test_rejection_bucket_same_direction_when_peer_proposed_same():
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        render_rejection_analysis,
    )
    rejections = [{
        "tick_id": 10, "symbol": "EURUSD",
        "loser_direction": "long", "winner_direction": "long",
        "loser_agent_id": "isagi_yoichi",
        "winner_agent_id": "nagi_seishiro",
        "loser_conviction": 0.7, "winner_conviction": 0.8,
        "rejection_reason": "lower_conviction_same_symbol",
        "timestamp": "2024-01-01T00:00:00+00:00",
    }]
    peer = _proposal(
        agent_id="nagi_seishiro", symbol="EURUSD",
        direction="long", conviction=0.8, tick_id=10,
    )
    md, b = render_rejection_analysis(
        isagi_rejections=rejections,
        thoughts_by_tick={},
        proposals_by_tick={10: [peer]},
        full_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        full_end=datetime(2024, 12, 31, tzinfo=timezone.utc),
    )
    assert b.same_direction == 1
    assert b.opposite_direction == 0


def test_rejection_bucket_opposite_direction():
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        render_rejection_analysis,
    )
    rejections = [{
        "tick_id": 10, "symbol": "EURUSD",
        "loser_direction": "long", "winner_direction": "short",
        "loser_agent_id": "isagi_yoichi",
        "winner_agent_id": "nagi_seishiro",
        "loser_conviction": 0.6, "winner_conviction": 0.9,
        "rejection_reason": "lower_conviction_same_symbol",
        "timestamp": "2024-01-01T00:00:00+00:00",
    }]
    peer = _proposal(
        agent_id="nagi_seishiro", symbol="EURUSD",
        direction="short", conviction=0.9, tick_id=10,
    )
    _, b = render_rejection_analysis(
        isagi_rejections=rejections,
        thoughts_by_tick={},
        proposals_by_tick={10: [peer]},
        full_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        full_end=datetime(2024, 12, 31, tzinfo=timezone.utc),
    )
    assert b.opposite_direction == 1
    assert b.same_direction == 0


def test_rejection_bucket_silent_when_no_peer_proposals():
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        render_rejection_analysis,
    )
    rejections = [{
        "tick_id": 5, "symbol": "EURUSD",
        "loser_direction": "long", "winner_direction": "long",
        "loser_agent_id": "isagi_yoichi",
        "winner_agent_id": "isagi_yoichi",
        "loser_conviction": 0.6, "winner_conviction": 0.6,
        "rejection_reason": "open_position_concurrency_limit",
        "timestamp": "2024-01-01T00:00:00+00:00",
    }]
    _, b = render_rejection_analysis(
        isagi_rejections=rejections,
        thoughts_by_tick={},
        proposals_by_tick={5: []},
        full_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        full_end=datetime(2024, 12, 31, tzinfo=timezone.utc),
    )
    assert b.silent == 1


def test_rejection_bucket_own_setup_elsewhere():
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        render_rejection_analysis,
    )
    rejections = [{
        "tick_id": 7, "symbol": "EURUSD",
        "loser_direction": "long", "winner_direction": "long",
        "loser_agent_id": "isagi_yoichi",
        "winner_agent_id": "isagi_yoichi",
        "loser_conviction": 0.6, "winner_conviction": 0.6,
        "rejection_reason": "open_position_concurrency_limit",
        "timestamp": "2024-01-01T00:00:00+00:00",
    }]
    elsewhere = _proposal(
        agent_id="barou_shoei", symbol="USDCAD",
        direction="long", conviction=0.8, tick_id=7,
    )
    _, b = render_rejection_analysis(
        isagi_rejections=rejections,
        thoughts_by_tick={},
        proposals_by_tick={7: [elsewhere]},
        full_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        full_end=datetime(2024, 12, 31, tzinfo=timezone.utc),
    )
    assert b.own_setup_elsewhere == 1


# ---------------------------------------------------------------------------
# Smoke -- the harness import path and constants are wired
# ---------------------------------------------------------------------------

def test_imports_clean():
    """The harness module can be imported without raising. Cheap
    regression guard against accidental top-level side effects (e.g.,
    a stray production import at module load time).
    """
    import programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate as m  # noqa: F401
    assert m.SQUAD_PASS_RATIO == 1.10
    assert m.SQUAD_PARTIAL_RATIO == 1.00
    assert m.DEFAULT_DELTA_INFO_WINDOWS >= 1


@pytest.mark.slow
@pytest.mark.skipif(
    not production_repo_available(),
    reason="Phi4 squad gate smoke needs production repo (Isagi+Barou inits)",
)
@pytest.mark.skipif(
    not bool(__import__("os").environ.get("M001_RUN_SLOW")),
    reason="set M001_RUN_SLOW=1 to enable the real-data squad gate smoke",
)
def test_squad_gate_smoke_run(tmp_path):
    """Run the squad gate end-to-end on the production cache.

    Marked slow + opt-in -- this drives the full 11-year window. Use
    `M001_RUN_SLOW=1 pytest -m slow programs/.../test_phi4_gate.py` to
    enable.
    """
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        run_squad_gate,
    )
    report = run_squad_gate(out_dir=tmp_path, delta_info_windows=1)
    assert report.verdict in (
        "PASS", "PARTIAL", "FAIL", "PROVISIONAL",
    )
    assert (tmp_path / "phi4_squad_v1.md").exists()
    assert (tmp_path / "phi4_isagi_rejection_analysis.md").exists()
