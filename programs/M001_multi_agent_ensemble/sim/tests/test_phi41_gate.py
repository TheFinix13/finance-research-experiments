"""Φ4.1 expanded-squad gate harness -- smoke + verdict logic tests.

Three layers:

1. Verdict-logic unit tests (no production-repo dependency). Reuses
   the Φ4 thresholds (PASS >= 1.10x, PARTIAL 1.00..1.10x, FAIL < 1.00x,
   PROVISIONAL if n_trades < 30).
2. Pure tests for the Φ4.1 report renderer's new diagnostic block: the
   Nagi confluence delta vs Φ4, the predicate-starvation falsifier
   headline.
3. Import smoke -- the harness module loads cleanly, the agent ordering
   registry is consistent with the new roster, and the F17 candidate
   tuple is intact.

The full end-to-end smoke (loading 11 years of EURUSD/GBPUSD/USDCAD
bars from the production cache) is exercised by the CLI manually --
same opt-in pattern as `test_phi4_gate.py::test_squad_gate_smoke_run`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from programs.M001_multi_agent_ensemble.sim._cross_repo import (
    production_repo_available,
)
from programs.M001_multi_agent_ensemble.sim.core.types import (
    AgentProposal,
    LadderRung,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_phi41_report(*, squad_tqs: float = 0.350, n_trades: int = 100,
                       nagi_count: int = 0):
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi41_gate import (
        SYMBOLS_PHI41,
    )
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        ISAGI_ALONE_MEDIAN_OOS_PIPS,
        ISAGI_ALONE_MEDIAN_OOS_TQS,
        SquadGateReport,
    )
    ratio = squad_tqs / ISAGI_ALONE_MEDIAN_OOS_TQS
    return SquadGateReport(
        full_start=datetime(2015, 1, 1, tzinfo=timezone.utc),
        full_end=datetime(2025, 12, 31, tzinfo=timezone.utc),
        symbols=SYMBOLS_PHI41,
        n_thoughts=42000, n_proposals_all=1200,
        n_proposals_accepted=900, n_proposals_rejected=300,
        n_trades=n_trades,
        per_agent_trade_counts={
            "isagi_yoichi": 60, "bachira_meguru": 25,
            "itoshi_rin": 8, "chigiri_hyoma": 12,
            "nagi_seishiro": 0, "barou_shoei": 25,
            "reo_mikage": 0, "kunigami_rensuke": 0,
        },
        per_agent_overall_kpis={
            "isagi_yoichi": {"n": 60, "mean_pips": 11.0, "median_pips": 8.0,
                             "mean_tqs": 0.32, "win_rate": 0.55},
            "bachira_meguru": {"n": 25, "mean_pips": 9.0, "median_pips": 7.0,
                                "mean_tqs": 0.28, "win_rate": 0.50},
        },
        squad_median_oos_window_mean_pips=12.0,
        squad_mean_oos_window_mean_pips=12.0,
        squad_median_oos_window_mean_tqs=squad_tqs,
        squad_oos_windows_positive=7,
        squad_oos_windows_total=7,
        isagi_alone_median_oos_pips=ISAGI_ALONE_MEDIAN_OOS_PIPS,
        isagi_alone_median_oos_tqs=ISAGI_ALONE_MEDIAN_OOS_TQS,
        squad_vs_isagi_tqs_ratio=ratio,
        verdict="PENDING", verdict_reason="",
        nagi_fired_count=nagi_count,
    )


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------

def test_phi41_verdict_pass_at_or_above_1_10x():
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi41_gate import (
        _decide_phi41_verdict,
    )
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        ISAGI_ALONE_MEDIAN_OOS_TQS,
    )
    r = _build_phi41_report(
        squad_tqs=ISAGI_ALONE_MEDIAN_OOS_TQS * 1.10,
        n_trades=100, nagi_count=5,
    )
    v, reason = _decide_phi41_verdict(r)
    assert v == "PASS", reason


def test_phi41_verdict_partial_between_1_00_and_1_10x():
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi41_gate import (
        _decide_phi41_verdict,
    )
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        ISAGI_ALONE_MEDIAN_OOS_TQS,
    )
    r = _build_phi41_report(
        squad_tqs=ISAGI_ALONE_MEDIAN_OOS_TQS * 1.05,
        n_trades=100, nagi_count=3,
    )
    v, reason = _decide_phi41_verdict(r)
    assert v == "PARTIAL", reason


def test_phi41_verdict_fail_below_1_00x():
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi41_gate import (
        _decide_phi41_verdict,
    )
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        ISAGI_ALONE_MEDIAN_OOS_TQS,
    )
    r = _build_phi41_report(
        squad_tqs=ISAGI_ALONE_MEDIAN_OOS_TQS * 0.90,
        n_trades=100, nagi_count=0,
    )
    v, reason = _decide_phi41_verdict(r)
    assert v == "FAIL", reason
    assert "did not close the gap" in reason


def test_phi41_verdict_provisional_when_too_few_trades():
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi41_gate import (
        _decide_phi41_verdict,
    )
    r = _build_phi41_report(squad_tqs=0.5, n_trades=20, nagi_count=0)
    v, reason = _decide_phi41_verdict(r)
    assert v == "PROVISIONAL", reason


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def test_render_phi41_report_diag_says_yes_when_nagi_fires():
    """When Nagi count moves from 0 (Φ4) to > 0 (Φ4.1), the diagnosis
    block reports 'YES' on predicate starvation."""
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi41_gate import (
        render_phi41_report, _decide_phi41_verdict,
    )
    r = _build_phi41_report(squad_tqs=0.35, n_trades=100, nagi_count=7)
    r.verdict, r.verdict_reason = _decide_phi41_verdict(r)
    md = render_phi41_report(
        r,
        nagi_confluence_count_phi4=0,
        reo_mirror_count=120,
        rin_precision_lift_count=5,
        bachira_rebel_lift_count=18,
        chigiri_breakout_count=15,
    )
    assert "**Nagi confluence-firing thoughts**" in md
    assert "**YES.**" in md
    assert "**7**" in md
    # Φ4.1 telemetry counts must surface in the engine telemetry block.
    assert "Reo mirror Thoughts emitted: 120" in md
    assert "Bachira rebel lifts applied: 18" in md
    assert "Rin precision lifts applied: 5" in md
    assert "Chigiri breakout-firing thoughts: 15" in md


def test_render_phi41_report_diag_says_no_when_nagi_silent():
    """When Nagi count stays at 0 with Reo lifting peer convictions,
    the diagnosis block reports 'NO' and proposes the Φ4.2 diagnostic."""
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi41_gate import (
        render_phi41_report, _decide_phi41_verdict,
    )
    r = _build_phi41_report(squad_tqs=0.31, n_trades=100, nagi_count=0)
    r.verdict, r.verdict_reason = _decide_phi41_verdict(r)
    md = render_phi41_report(
        r,
        nagi_confluence_count_phi4=0,
        reo_mirror_count=120,    # Reo lifted lots of peers
        rin_precision_lift_count=5,
        bachira_rebel_lift_count=18,
        chigiri_breakout_count=15,
    )
    assert "**NO.**" in md
    assert "coordinate band non-overlap" in md
    assert "nagi_predicate_audit" in md


def test_render_phi41_report_falsifier_headline_includes_delta():
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi41_gate import (
        render_phi41_report, _decide_phi41_verdict,
    )
    r = _build_phi41_report(squad_tqs=0.35, n_trades=100, nagi_count=5)
    r.verdict, r.verdict_reason = _decide_phi41_verdict(r)
    md = render_phi41_report(
        r, nagi_confluence_count_phi4=0,
        reo_mirror_count=0, rin_precision_lift_count=0,
        bachira_rebel_lift_count=0, chigiri_breakout_count=0,
    )
    # delta should be "+5"
    assert "| **Nagi confluence-firing thoughts** | 0 | **5** | +5 |" in md


# ---------------------------------------------------------------------------
# Roster + F17 wiring smoke
# ---------------------------------------------------------------------------

def test_phi41_agent_order_matches_roster_yaml_count():
    """The ordering registry must list 8 agents matching the roster."""
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi41_gate import (
        PHI41_AGENT_ORDER,
    )
    assert len(PHI41_AGENT_ORDER) == 8
    expected = {
        "isagi_yoichi", "bachira_meguru", "itoshi_rin",
        "chigiri_hyoma", "reo_mikage", "nagi_seishiro",
        "barou_shoei", "kunigami_rensuke",
    }
    assert set(PHI41_AGENT_ORDER) == expected


def test_phi41_f17_candidates_cover_all_tier2_candidates():
    """F17 ΔInfo measurement covers Nagi, Barou, and the 4 new agents."""
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi41_gate import (
        F17_CANDIDATES,
    )
    candidate_ids = {cid for cid, _ in F17_CANDIDATES}
    assert candidate_ids == {
        "nagi_seishiro", "barou_shoei",
        "bachira_meguru", "itoshi_rin",
        "chigiri_hyoma", "reo_mikage",
    }


def test_phi41_symbols_include_gbpusd():
    """Φ4.1 must drive EURUSD + GBPUSD + USDCAD (Φ4 only had EURUSD+USDCAD)."""
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi41_gate import (
        SYMBOLS_PHI41,
    )
    assert "EURUSD" in SYMBOLS_PHI41
    assert "GBPUSD" in SYMBOLS_PHI41
    assert "USDCAD" in SYMBOLS_PHI41


def test_phi41_imports_clean():
    """The harness module imports without raising and inherits the
    Φ4 thresholds verbatim."""
    import programs.M001_multi_agent_ensemble.sim.scoring.run_phi41_gate as m
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
        SQUAD_PASS_RATIO,
        SQUAD_PARTIAL_RATIO,
        DEFAULT_DELTA_INFO_WINDOWS,
    )
    assert SQUAD_PASS_RATIO == 1.10
    assert SQUAD_PARTIAL_RATIO == 1.00
    assert DEFAULT_DELTA_INFO_WINDOWS >= 1
    assert m.SYMBOLS_PHI41 == ("EURUSD", "GBPUSD", "USDCAD")


# ---------------------------------------------------------------------------
# Slow end-to-end smoke (opt-in)
# ---------------------------------------------------------------------------

@pytest.mark.slow
@pytest.mark.skipif(
    not production_repo_available(),
    reason="Φ4.1 squad gate smoke needs production repo (Isagi+Barou inits)",
)
@pytest.mark.skipif(
    not bool(__import__("os").environ.get("M001_RUN_SLOW")),
    reason="set M001_RUN_SLOW=1 to enable the real-data Φ4.1 gate smoke",
)
def test_phi41_gate_smoke_run(tmp_path):
    """Run the Φ4.1 squad gate end-to-end on the production cache.

    Marked slow + opt-in. Use `M001_RUN_SLOW=1 pytest -m slow
    programs/.../test_phi41_gate.py` to enable.
    """
    from programs.M001_multi_agent_ensemble.sim.scoring.run_phi41_gate import (
        run_phi41_gate,
    )
    report = run_phi41_gate(out_dir=tmp_path, delta_info_windows=1)
    assert report.verdict in ("PASS", "PARTIAL", "FAIL", "PROVISIONAL")
    assert (tmp_path / "phi41_squad_v1.md").exists()
    assert (tmp_path / "phi41_isagi_rejection_analysis.md").exists()
