"""Phi3 gate end-to-end smoke + verdict logic tests.

* Smoke test: drives the harness loop on 100 synthetic bars with no
  prepared bars (engine-only path, no real signals expected). Verifies
  the protocol runs without exceptions and emits >= 0 thoughts /
  proposals.
* Verdict logic test: feeds synthetic GateReport inputs into
  `_decide_verdict` to assert PASS / PARTIAL / FAIL / PROVISIONAL
  thresholds match the user spec.

Real-data slow runs are marked `@pytest.mark.slow` and skipped by
default. They take ~ 1-2 minutes on the production parquet cache.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from programs.M001_multi_agent_ensemble.sim._cross_repo import (
    production_repo_available,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_isagi_phi3_gate import (
    DEFAULT_FULL_END,
    DEFAULT_FULL_START,
    GateReport,
    SAE_BASELINE_PIPS_PER_TRADE,
    WARMUP_BARS,
    WindowStats,
    _decide_verdict,
    _drive_replay,
    _window_starts,
    run_gate,
)


# ---------------------------------------------------------------------------
# Smoke tests (no real data; production repo required for the wrapper init)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not production_repo_available(),
    reason="M001 Phi3 needs the production repo on sys.path",
)
def test_engine_smoke_100_synthetic_bars():
    """End-to-end: 100 bars synthetic -> engine produces >= 0 thoughts +
    no exceptions. Mirrors `test_a01_isagi_wrap.test_unprepared_symbol_*`
    but exercises the harness driver path used in the real gate.
    """
    from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi import (
        A1IsagiV1,
    )
    from programs.M001_multi_agent_ensemble.sim.tests.test_a01_isagi_wrap import (
        _make_synthetic_bars,
    )

    # `_make_synthetic_bars` synthesises the impulse + pullback skeleton
    # before any trailing chop -- the floor is ~470 bars. Use that floor
    # directly for the smoke contract.
    bars = _make_synthetic_bars(100)
    expected_n = len(bars)
    assert expected_n >= 100, "synthetic generator must produce >= 100 bars"
    agent = A1IsagiV1()
    agent.prepare("EURUSD", bars)
    thoughts, proposals, trades = _drive_replay(
        agent, bars, "EURUSD", warmup_bars=20,
    )
    assert len(thoughts) == expected_n, "every bar must produce a Thought"
    # Proposals + trades are allowed to be zero on 100-bar synthetic input.
    assert all(p.direction in ("long", "short", "flat") for p in proposals)
    assert all(t.pnl_pips == t.pnl_pips for t in trades)  # NaN-free


def test_window_starts_count_for_e004_match():
    """E004 walk-forward had 7 rolling windows (2015..2024 starts) when
    the full window ended 2025-12-31. We must reproduce that count.
    """
    starts = _window_starts(DEFAULT_FULL_START, DEFAULT_FULL_END)
    # Years 2015..2020 inclusive: IS [yyyy..yyyy+3] -> OOS [yyyy+4]
    # last start year = 2021 because OOS year 2025 is the cap.
    # E004 ran 2015..2021 = 7 windows. Confirm.
    assert len(starts) == 7, f"expected 7 windows, got {len(starts)}: {starts}"
    assert starts[0].year == 2015
    assert starts[-1].year == 2021


# ---------------------------------------------------------------------------
# Verdict logic (pure unit, no data)
# ---------------------------------------------------------------------------

def _build_report(
    *,
    median_pips: float,
    oos_pos: int,
    oos_total: int = 7,
    provisional: str | None = None,
) -> GateReport:
    """Build a GateReport where `median_pips` is the gate comparator
    (`median_oos_window_mean_pips`).
    """
    return GateReport(
        symbol="EURUSD",
        full_start=DEFAULT_FULL_START,
        full_end=DEFAULT_FULL_END,
        n_bars=18000,
        n_thoughts=18000,
        n_proposals=500,
        n_trades=450,
        overall_mean_pips=median_pips,
        overall_median_pips=median_pips,
        overall_mean_tqs=0.5,
        overall_win_rate=0.45,
        oos_windows_positive=oos_pos,
        oos_windows_total=oos_total,
        median_oos_window_mean_pips=median_pips,
        mean_oos_window_mean_pips=median_pips,
        median_oos_window_mean_tqs=0.5,
        windows=[],
        provisional_reason=provisional,
    )


def test_verdict_pass_at_baseline():
    r = _build_report(median_pips=SAE_BASELINE_PIPS_PER_TRADE, oos_pos=7)
    v, _ = _decide_verdict(r)
    assert v == "PASS"


def test_verdict_pass_within_5pct_above():
    r = _build_report(
        median_pips=SAE_BASELINE_PIPS_PER_TRADE * 1.04, oos_pos=7,
    )
    v, _ = _decide_verdict(r)
    assert v == "PASS"


def test_verdict_partial_above_5pct_drift():
    r = _build_report(
        median_pips=SAE_BASELINE_PIPS_PER_TRADE * 1.10, oos_pos=7,
    )
    v, reason = _decide_verdict(r)
    assert v == "PARTIAL", reason


def test_verdict_fail_below_9_pips():
    r = _build_report(median_pips=8.5, oos_pos=7)
    v, _ = _decide_verdict(r)
    assert v == "FAIL"


def test_verdict_fail_oos_windows_below_5():
    r = _build_report(median_pips=11.5, oos_pos=4)
    v, _ = _decide_verdict(r)
    assert v == "FAIL"


def test_verdict_provisional_passthrough():
    r = _build_report(
        median_pips=11.34, oos_pos=7,
        provisional="data slice missing 2024-2025",
    )
    v, reason = _decide_verdict(r)
    assert v == "PROVISIONAL"
    assert "data slice missing" in reason


# ---------------------------------------------------------------------------
# Slow integration (real production data) -- skipped by default.
# Opt-in via the env var M001_RUN_SLOW=1 (or invoke run_isagi_phi3_gate
# directly from the CLI). The pytest `slow` mark is still attached so
# callers using `-m slow` collect it explicitly.
# ---------------------------------------------------------------------------

@pytest.mark.slow
@pytest.mark.skipif(
    not production_repo_available(),
    reason="M001 Phi3 needs the production repo on sys.path",
)
@pytest.mark.skipif(
    not bool(__import__("os").environ.get("M001_RUN_SLOW")),
    reason="set M001_RUN_SLOW=1 to enable the real-data gate test",
)
def test_full_gate_eurusd_2015_2025(tmp_path):
    """Full real-data run.  Manual: enable with `M001_RUN_SLOW=1 pytest -m slow`."""
    out = tmp_path / "phi3_gate.md"
    report = run_gate(
        symbol="EURUSD",
        full_start=DEFAULT_FULL_START,
        full_end=DEFAULT_FULL_END,
        out_path=out,
        write_trades_jsonl=False,
    )
    assert report.n_bars > 10_000
    assert report.verdict in {"PASS", "PARTIAL", "FAIL", "PROVISIONAL"}
    assert out.exists()
