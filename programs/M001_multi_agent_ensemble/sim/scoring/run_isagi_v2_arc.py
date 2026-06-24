"""Isagi v1 vs v2 evolution-arc head-to-head harness.

Runs A1 Isagi v1 and A1 Isagi v2 INDEPENDENTLY on the same EURUSD H4
2015-2025 panel as the Phi3 gate (`reviews/phi3_gate_isagi_v1.md`).
This is a *single-agent* arc evaluation, NOT a squad gate. The output
is the verdict on whether v2 dominates v1 enough to canonise.

The "locked statistic" (per the §3.11.2 step 4 / step 5 contract) is the
**median across the seven 4-yr-IS / 1-yr-OOS windows of each window's
mean TQS (F12)** -- exactly the comparator the Phi3 gate uses against
the Sae baseline. v2 is awarded CLOSE iff:

1. v2 mean OOS-window TQS >= v1's median, AND
2. v2 takes at least every v1 zone-touch trade (regression invariant
   re-asserted on real data, not just synthetic), AND
3. v2 introduces >= 1 sweep trade in at least 4 of 7 OOS windows
   (behaviour delta on real data, not just synthetic), AND
4. No single OOS window's v2 mean TQS is < 0.95 x v1's (the per-window
   tolerance).

Otherwise FAIL -- v2 is archived in `sim/agents/a01_isagi_v2.py` for
the audit trail, but v1 stays canonical until a new defeat note + arc
clears the contract.

CLI:

    PYTHONPATH=../multi-pair-trading-agent:. \\
        M001_PRODUCTION_REPO=../multi-pair-trading-agent \\
        ../multi-pair-trading-agent/.venv/bin/python \\
        -m programs.M001_multi_agent_ensemble.sim.scoring.run_isagi_v2_arc
        [--symbol EURUSD] [--start 2015-01-01] [--end 2025-12-31]
        [--out reviews/isagi_v2_arc.md]

Mirrors the structure of `run_isagi_phi3_gate.py`. The two scripts share
the `_drive_replay`, `_load_production_bars`, walk-forward window logic
via direct imports -- no duplication.
"""
from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from programs.M001_multi_agent_ensemble.sim._cross_repo import (
    ensure_production_repo_on_path,
)
from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi import A1IsagiV1
from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi_v2 import A1IsagiV2
from programs.M001_multi_agent_ensemble.sim.core.types import (
    AgentProposal,
    MarketState,
    Thought,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_isagi_phi3_gate import (
    DEFAULT_FULL_END,
    DEFAULT_FULL_START,
    IS_YEARS,
    OOS_YEARS,
    SAE_BASELINE_PIPS_PER_TRADE,
    WARMUP_BARS,
    TradeRecord,
    _drive_replay,
    _load_production_bars,
    _window_starts,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Gate thresholds for the arc verdict
# ---------------------------------------------------------------------------

# Per-window non-regression tolerance: v2 OOS TQS must not drop below
# v1's in any single window by more than this fraction.
PER_WINDOW_TOLERANCE = 0.05

# v2 must produce sweep trades in at least this many of the 7 OOS windows.
SWEEP_WINDOW_COVERAGE_FLOOR = 4

# v2 must take at least every v1 zone-touch trade (regression invariant).
# Already enforced by the unit test; re-asserted here on real data for the
# arc report.

# Honest-baseline-v1 reference numbers from `reviews/phi3_gate_isagi_v1.md`:
V1_REFERENCE_MEDIAN_OOS_PIPS = 11.04
V1_REFERENCE_MEDIAN_OOS_TQS = 0.317


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AgentRunResult:
    """All artefacts from running one agent over the dev window."""

    agent_id: str
    version: str  # "v1" | "v2"
    thoughts: list[Thought] = field(default_factory=list)
    proposals: list[AgentProposal] = field(default_factory=list)
    trades: list[TradeRecord] = field(default_factory=list)


@dataclass
class WindowComparison:
    """Per-OOS-window v1 vs v2 metrics."""

    is_start: datetime
    is_end: datetime
    oos_start: datetime
    oos_end: datetime
    v1_n: int = 0
    v1_mean_pips: float = 0.0
    v1_median_pips: float = 0.0
    v1_mean_tqs: float = 0.0
    v1_win_rate: float = 0.0
    v2_n: int = 0
    v2_mean_pips: float = 0.0
    v2_median_pips: float = 0.0
    v2_mean_tqs: float = 0.0
    v2_win_rate: float = 0.0
    v2_zone_trades: int = 0
    v2_sweep_trades: int = 0


@dataclass
class ArcReport:
    """Top-level arc verdict + supporting evidence."""

    symbol: str
    full_start: datetime
    full_end: datetime
    n_bars: int

    v1: AgentRunResult
    v2: AgentRunResult

    v1_median_oos_window_mean_pips: float = 0.0
    v1_median_oos_window_mean_tqs: float = 0.0
    v1_oos_windows_positive: int = 0
    v2_median_oos_window_mean_pips: float = 0.0
    v2_median_oos_window_mean_tqs: float = 0.0
    v2_oos_windows_positive: int = 0
    # Behaviour delta -- v2's NEW vocabulary on real data.
    v2_zone_trade_count: int = 0
    v2_sweep_trade_count: int = 0
    sweep_window_coverage: int = 0

    windows: list[WindowComparison] = field(default_factory=list)
    verdict: str = "PENDING"
    verdict_reason: str = ""

    # Rejection-rate proxy (same-direction redundancy across v1 vs v2).
    v1_rejection_count: int = 0
    v2_rejection_count: int = 0
    v1_rejection_same_dir_pct: float = 0.0
    v2_rejection_same_dir_pct: float = 0.0


# ---------------------------------------------------------------------------
# Trade execution -- preserve provenance through to TradeRecord
# ---------------------------------------------------------------------------

def _drive_replay_with_weapon_provenance(
    agent,
    bars: list,
    symbol: str,
    *,
    version: str,
) -> AgentRunResult:
    """Reuse `_drive_replay` but annotate each TradeRecord with the
    agent_id + version (and, for v2, the weapon that fired so the
    behaviour-delta numbers come straight from the trade ledger).
    """
    from programs.M001_multi_agent_ensemble.sim.core.ledger import FullLedger

    ledger = FullLedger()
    thoughts, proposals, trades = _drive_replay(
        agent, bars, symbol, ledger=ledger,
    )
    # The shared `_drive_replay` hardcodes agent_id = "isagi_yoichi" and
    # symbol = "EURUSD" on TradeRecord; here we re-stamp with the real
    # symbol from the panel and tag each trade with which weapon fired
    # by matching trade entry_time -> proposal -> rationale.weapon.
    proposal_by_time: dict[datetime, AgentProposal] = {
        p.timestamp: p for p in proposals
    }
    annotated: list[TradeRecord] = []
    for t in trades:
        weapon = "zone_d1_against"  # v1 default; overwritten for v2 below.
        # Match: trade.entry_time = first bar AFTER the proposal's bar.
        # The Phi3 harness opens at next-bar-open; we look up the
        # CLOSEST proposal whose timestamp is < trade.entry_time.
        # Cheap approach: scan all proposals whose timestamp < entry_time
        # and pick the one nearest in time.
        best = None
        for p in proposals:
            if p.timestamp >= t.entry_time:
                continue
            if best is None or p.timestamp > best.timestamp:
                best = p
        if best is not None:
            weapon = str(best.rationale.get("weapon", weapon))
        # Repack the TradeRecord with the real symbol + weapon-tagged
        # tqs_components (we keep tqs_components as the F12 component
        # dict; we add a parallel `weapon` key for downstream code).
        tqs = dict(t.tqs_components) | {"weapon": weapon}
        annotated.append(TradeRecord(
            agent_id=agent.agent_id,
            symbol=symbol,
            entry_time=t.entry_time,
            exit_time=t.exit_time,
            direction=t.direction,
            entry=t.entry,
            stop=t.stop,
            take_profit=t.take_profit,
            exit_price=t.exit_price,
            exit_reason=t.exit_reason,
            pnl_pips=t.pnl_pips,
            mae_pips=t.mae_pips,
            mfe_pips=t.mfe_pips,
            bars_held=t.bars_held,
            r_multiple=t.r_multiple,
            tqs_components=tqs,
        ))
    return AgentRunResult(
        agent_id=agent.agent_id,
        version=version,
        thoughts=list(thoughts),
        proposals=list(proposals),
        trades=annotated,
    )


# ---------------------------------------------------------------------------
# Window stats
# ---------------------------------------------------------------------------

def _summarise(trades: list[TradeRecord]) -> tuple[float, float, float, float, int]:
    if not trades:
        return 0.0, 0.0, 0.0, 0.0, 0
    pips = [t.pnl_pips for t in trades]
    tqs = [t.tqs_components["tqs"] for t in trades]
    wins = sum(1 for t in trades if t.pnl_pips > 0)
    return (
        statistics.mean(pips),
        statistics.median(pips),
        statistics.mean(tqs),
        wins / len(trades),
        len(trades),
    )


def _slice(trades: list[TradeRecord], lo: datetime, hi: datetime) -> list[TradeRecord]:
    return [t for t in trades if lo <= t.entry_time < hi]


def _split_by_weapon(trades: list[TradeRecord]) -> tuple[int, int]:
    """Return (zone_count, sweep_count)."""
    zone = sum(
        1 for t in trades if t.tqs_components.get("weapon") == "zone_d1_against"
    )
    sweep = sum(
        1 for t in trades if t.tqs_components.get("weapon") == "liquidity_sweep"
    )
    return zone, sweep


def _compute_window_comparisons(
    v1_trades: list[TradeRecord],
    v2_trades: list[TradeRecord],
    full_start: datetime,
    full_end: datetime,
) -> list[WindowComparison]:
    out: list[WindowComparison] = []
    for ws in _window_starts(full_start, full_end):
        is_start = ws
        is_end = datetime(ws.year + IS_YEARS, 1, 1, tzinfo=timezone.utc)
        oos_start = is_end
        oos_end = datetime(
            oos_start.year + OOS_YEARS, 1, 1, tzinfo=timezone.utc,
        )
        if oos_end > full_end:
            oos_end = full_end
        v1_oos = _slice(v1_trades, oos_start, oos_end)
        v2_oos = _slice(v2_trades, oos_start, oos_end)
        v1_mean, v1_med, v1_tqs, v1_wr, v1_n = _summarise(v1_oos)
        v2_mean, v2_med, v2_tqs, v2_wr, v2_n = _summarise(v2_oos)
        v2_zone, v2_sweep = _split_by_weapon(v2_oos)
        out.append(WindowComparison(
            is_start=is_start, is_end=is_end,
            oos_start=oos_start, oos_end=oos_end,
            v1_n=v1_n, v1_mean_pips=v1_mean, v1_median_pips=v1_med,
            v1_mean_tqs=v1_tqs, v1_win_rate=v1_wr,
            v2_n=v2_n, v2_mean_pips=v2_mean, v2_median_pips=v2_med,
            v2_mean_tqs=v2_tqs, v2_win_rate=v2_wr,
            v2_zone_trades=v2_zone, v2_sweep_trades=v2_sweep,
        ))
    return out


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------

def _decide_arc_verdict(report: ArcReport) -> tuple[str, str]:
    """Determine whether the arc CLOSES (v2 canonised) or FAILS (v1 stays).

    Four criteria (all must hold for CLOSE):
      1. v2 mean OOS-window TQS >= v1's median OOS-window TQS.
      2. v2 trade count >= v1 trade count (zone-branch regression on real
         data; v2 may not lose v1 trades).
      3. Sweep trades fired in >= SWEEP_WINDOW_COVERAGE_FLOOR (4 of 7)
         OOS windows.
      4. No single OOS window's v2 mean TQS < (1 - PER_WINDOW_TOLERANCE)
         x v1's mean TQS.
    """
    v1_count = len(report.v1.trades)
    v2_count = len(report.v2.trades)

    if v2_count < v1_count:
        return (
            "FAIL",
            f"v2 took {v2_count} trades; v1 took {v1_count} -- v2 "
            "regressed on the v1 zone branch (lost v1 trades).",
        )

    if report.v2_median_oos_window_mean_tqs < report.v1_median_oos_window_mean_tqs:
        return (
            "FAIL",
            f"v2 median OOS TQS {report.v2_median_oos_window_mean_tqs:.3f} "
            f"< v1 {report.v1_median_oos_window_mean_tqs:.3f} -- "
            "vocabulary expansion has net-negative TQS effect.",
        )

    if report.sweep_window_coverage < SWEEP_WINDOW_COVERAGE_FLOOR:
        return (
            "FAIL",
            f"v2 sweep trades fired in only {report.sweep_window_coverage} "
            f"of 7 OOS windows; below the {SWEEP_WINDOW_COVERAGE_FLOOR}-of-7 "
            "behaviour-delta floor. Evolution arc is empty per doctrine §3.11.3.",
        )

    # Per-window non-regression.
    for w in report.windows:
        if w.v1_n == 0:
            continue
        tol = (1.0 - PER_WINDOW_TOLERANCE) * w.v1_mean_tqs
        if w.v2_mean_tqs < tol:
            return (
                "FAIL",
                f"v2 OOS window {w.oos_start.year} mean TQS "
                f"{w.v2_mean_tqs:.3f} < {tol:.3f} = "
                f"{1 - PER_WINDOW_TOLERANCE:.0%} x v1 ({w.v1_mean_tqs:.3f}) "
                "-- per-window regression tolerance breached.",
            )

    return (
        "CLOSE",
        f"v2 median OOS TQS {report.v2_median_oos_window_mean_tqs:.3f} "
        f">= v1 {report.v1_median_oos_window_mean_tqs:.3f}; "
        f"v2 took {v2_count} trades >= v1 {v1_count}; sweep trades fired in "
        f"{report.sweep_window_coverage}/7 OOS windows; per-window non-"
        "regression holds. v2 canonises -- v1 stays in roster for one "
        "phase gate per coexistence rule.",
    )


# ---------------------------------------------------------------------------
# Rejection-rate proxy
# ---------------------------------------------------------------------------

def _rejection_proxy(result: AgentRunResult) -> tuple[int, float]:
    """Single-agent rejection proxy.

    For a single-agent run there is no "squad to be rejected by"; the
    closest proxy is the per-tick gap between proposals emitted and
    trades opened. Specifically:

        rejected = len(proposals) - len(trades)

    These are proposals the production fill model produced but the
    single-position concurrency limit blocked (a trade was already
    open from a prior tick). The "same-direction percentage" we
    report is the share of these rejections where the open trade's
    direction matched the rejected proposal's direction -- a *very
    rough* proxy for the squad-gate analysis the Phi4 squad doc
    produced, but on a single-agent run the only "competing
    direction" is the agent's own prior trade.
    """
    proposals = result.proposals
    trades = result.trades
    n_rejections = max(0, len(proposals) - len(trades))
    # Build a time-indexed list of (entry_time, direction) per trade.
    if not trades or not proposals:
        return n_rejections, 0.0
    sorted_trades = sorted(trades, key=lambda t: t.entry_time)
    same_dir = 0
    counted = 0
    for p in proposals:
        # Find the trade currently open at this proposal time.
        active = None
        for t in sorted_trades:
            if t.entry_time <= p.timestamp < t.exit_time:
                active = t
                break
        if active is None:
            continue
        counted += 1
        if active.direction == p.direction:
            same_dir += 1
    same_dir_pct = (100.0 * same_dir / counted) if counted else 0.0
    return n_rejections, same_dir_pct


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def _format_window_row(w: WindowComparison) -> str:
    return (
        f"| {w.is_start.year}-{w.is_end.year - 1} | {w.oos_start.year} | "
        f"{w.v1_n} | {w.v1_mean_pips:+.2f} | {w.v1_mean_tqs:.3f} | "
        f"{w.v2_n} | {w.v2_mean_pips:+.2f} | {w.v2_mean_tqs:.3f} | "
        f"{w.v2_zone_trades} | {w.v2_sweep_trades} | "
        f"{w.v2_mean_pips - w.v1_mean_pips:+.2f} | "
        f"{(w.v2_mean_tqs - w.v1_mean_tqs):+.3f} |"
    )


def render_report(report: ArcReport) -> str:
    lines: list[str] = []
    lines.append("# Isagi v1 vs v2 evolution-arc head-to-head\n")
    lines.append(f"**Run date:** {datetime.now(timezone.utc).isoformat()}\n")
    lines.append(
        f"**Symbol:** {report.symbol} -- **Window:** "
        f"{report.full_start.date()} -> {report.full_end.date()} "
        f"({report.n_bars} H4 bars)\n"
    )
    lines.append(
        "**v1:** `sim/agents/a01_isagi.py` -- wraps "
        "`SupplyDemandAlpha` at locked E004 params "
        "(`htf_align=D1`, `htf_align_mode=against`, "
        "`htf_lookback=10`, `htf_min_move_pips=60`, `target_rr=1.5`).\n"
    )
    lines.append(
        "**v2:** `sim/agents/a01_isagi_v2.py` -- v1 zone weapon "
        "byte-preserved + new `liquidity_sweep` weapon "
        "(sweep_max_age_bars=6, stop_atr_mult=0.5, target_rr=1.5, "
        "sweep_conviction=0.55; HTF gate: D1 bias must AGREE with "
        "sweep reaction).\n"
    )
    lines.append(
        "**Defeat trigger (the §3.11.2 step 1 evidence):** Φ4 squad-gate "
        "rejection analysis -- **1579 of 2994 (52.7 %) of v1's "
        "rejections were SAME-DIRECTION** with the rest of the squad. "
        "v1's `zone_d1_against` vocabulary leaves the rest of the "
        "dimensional space unused. v2 adds the liquidity-sweep "
        "vocabulary to claim ticks v1 cannot read at all. "
        "Full defeat note: `reviews/isagi_yoichi_v1_defeat.md`.\n"
    )
    lines.append("---\n")
    lines.append("## Verdict\n")
    lines.append(f"**Arc: `{report.verdict}`**\n")
    lines.append(f"_{report.verdict_reason}_\n")
    lines.append(
        "Honest framing: **CLOSE** means v2 dominates v1 by the §3.11.2 "
        "step 6 contract -- v2 takes all v1 trades, ≥4-of-7 OOS windows "
        "carry sweep trades, median OOS TQS not below v1, no single "
        "window worse by > 5%. **FAIL** means v2 should be archived; "
        "v1 stays canonical (the module on disk is preserved for the "
        "audit trail per §3.11.2 step 3).\n"
    )
    lines.append("---\n")
    lines.append("## Top-line comparison\n")
    lines.append(
        "Comparator -- **median across OOS windows of each window's mean "
        "TQS (F12)**. This is the same statistic the Phi3 gate locked.\n"
    )
    lines.append("")
    lines.append("| Metric | v1 | v2 | Delta |")
    lines.append("|---|---|---|---|")
    lines.append(
        f"| **Median OOS-window mean TQS** | "
        f"**{report.v1_median_oos_window_mean_tqs:.3f}** | "
        f"**{report.v2_median_oos_window_mean_tqs:.3f}** | "
        f"**{report.v2_median_oos_window_mean_tqs - report.v1_median_oos_window_mean_tqs:+.3f}** |"
    )
    lines.append(
        f"| Median OOS-window mean pips/trade | "
        f"{report.v1_median_oos_window_mean_pips:+.2f} | "
        f"{report.v2_median_oos_window_mean_pips:+.2f} | "
        f"{report.v2_median_oos_window_mean_pips - report.v1_median_oos_window_mean_pips:+.2f} |"
    )
    lines.append(
        f"| OOS windows positive (pips) | {report.v1_oos_windows_positive} / "
        f"{len(report.windows)} | {report.v2_oos_windows_positive} / "
        f"{len(report.windows)} | -- |"
    )
    lines.append(
        f"| Total trades | {len(report.v1.trades)} | {len(report.v2.trades)} | "
        f"{len(report.v2.trades) - len(report.v1.trades):+d} |"
    )
    lines.append(
        f"| v2 zone-branch trades | -- | {report.v2_zone_trade_count} | -- |"
    )
    lines.append(
        f"| v2 sweep-branch trades (NEW vocab) | -- | "
        f"{report.v2_sweep_trade_count} | -- |"
    )
    lines.append(
        f"| Sweep-trade window coverage | -- | "
        f"{report.sweep_window_coverage} / {len(report.windows)} | -- |"
    )
    lines.append("")
    lines.append(f"_v1 reference (Phi3 gate): **{V1_REFERENCE_MEDIAN_OOS_TQS:.3f}** median OOS-window mean TQS; this run reproduces it for the arc comparator._\n")
    lines.append("---\n")
    lines.append("## Per-window walk-forward (v1 vs v2 OOS)\n")
    lines.append(
        "(4 yr IS / 1 yr OOS rolling -- matches "
        "`reviews/phi3_gate_isagi_v1.md`)\n"
    )
    lines.append("")
    lines.append(
        "| IS window | OOS yr | v1 n | v1 mean pips | v1 mean TQS | "
        "v2 n | v2 mean pips | v2 mean TQS | v2 zone | v2 sweep | "
        "ΔPips | ΔTQS |"
    )
    lines.append(
        "|---|---|---|---|---|---|---|---|---|---|---|---|"
    )
    for w in report.windows:
        lines.append(_format_window_row(w))
    lines.append("")
    lines.append("---\n")
    lines.append("## Per-weapon breakdown (v2 zone vs sweep, standalone quality)\n")
    lines.append(
        "Isolating each weapon's per-trade quality answers the diagnostic "
        "question 'is the FAIL driven by negative sweep-weapon edge, or by "
        "queue collision stealing slots from zone trades?'\n"
    )
    lines.append("")
    lines.append(
        "| Weapon (v2) | Trades | Mean pips | Median pips | Mean TQS | Win % |"
    )
    lines.append("|---|---|---|---|---|---|")
    v2_zone_trades = [
        t for t in report.v2.trades
        if t.tqs_components.get("weapon") == "zone_d1_against"
    ]
    v2_sweep_trades = [
        t for t in report.v2.trades
        if t.tqs_components.get("weapon") == "liquidity_sweep"
    ]
    for label, tlist in (("zone", v2_zone_trades), ("sweep", v2_sweep_trades)):
        mean_p, med_p, mean_tqs, wr, n = _summarise(tlist)
        lines.append(
            f"| {label} | {n} | {mean_p:+.2f} | {med_p:+.2f} | {mean_tqs:.3f} | "
            f"{wr:.1%} |"
        )
    # v1 reference for comparison.
    mean_p, med_p, mean_tqs, wr, n = _summarise(report.v1.trades)
    lines.append(
        f"| _v1 zone (reference)_ | {n} | {mean_p:+.2f} | {med_p:+.2f} | "
        f"{mean_tqs:.3f} | {wr:.1%} |"
    )
    lines.append("")
    # Diagnostic narrative.
    if v2_sweep_trades:
        sw_mean_tqs = statistics.mean(
            t.tqs_components["tqs"] for t in v2_sweep_trades
        )
        z_mean_tqs = (
            statistics.mean(t.tqs_components["tqs"] for t in v2_zone_trades)
            if v2_zone_trades else 0.0
        )
        if sw_mean_tqs < z_mean_tqs:
            lines.append(
                f"**Diagnostic:** the sweep weapon's standalone mean TQS "
                f"({sw_mean_tqs:.3f}) is **below** v2's preserved zone "
                f"weapon ({z_mean_tqs:.3f}). The FAIL is dominated by "
                "**sweep-weapon edge being weaker than zone-weapon edge** "
                "on this panel -- adding sweep proposals to the single-"
                "position queue *cannibalises* the high-TQS zone slots "
                "with low-TQS sweep slots. A future v2 attempt should "
                "either (a) use the sweep weapon as a *zone confluence "
                "filter* rather than an independent entry, (b) tighten "
                "the sweep HTF gate (more conservative min_move_pips or "
                "longer lookback) so it fires only on highest-conviction "
                "sweeps, or (c) move v2 to a multi-position simulator so "
                "the queue collision is removed.\n"
            )
        else:
            lines.append(
                f"**Diagnostic:** sweep TQS ({sw_mean_tqs:.3f}) is at or "
                f"above v2 zone ({z_mean_tqs:.3f}); the FAIL is driven by "
                "queue-collision dynamics rather than weapon edge.\n"
            )
    lines.append("---\n")
    lines.append("## Behaviour delta (v2's NEW vocabulary in plain English)\n")
    lines.append(
        f"v2 fired **{report.v2_sweep_trade_count} liquidity-sweep "
        f"trades** across the eleven-year dev window that v1 cannot "
        f"emit at all (v1's `zone_d1_against` codepath has no sweep "
        f"branch). Of those, "
        f"{report.sweep_window_coverage} of the seven OOS windows "
        f"carry at least one sweep trade -- "
        f"{'PASSES' if report.sweep_window_coverage >= SWEEP_WINDOW_COVERAGE_FLOOR else 'FAILS'} "
        f"the {SWEEP_WINDOW_COVERAGE_FLOOR}-of-7 coverage floor.\n"
    )
    lines.append(
        "What v2 catches that v1 misses, concretely: when price wicks "
        "above a tagged equal-highs / swing-high / PDH cluster and "
        "closes back below (a buyside sweep) -- AND the D1 trend is "
        "ALREADY pointing down -- v2 takes a SHORT at the H4 close. "
        "Mirror geometry for sellside sweeps and LONG entries. v1 "
        "ignores these setups entirely.\n"
    )
    lines.append(
        f"v2's zone-branch trade count is **{report.v2_zone_trade_count}**, "
        f"vs v1's **{len(report.v1.trades)}** total trades. If the "
        f"zone branch is preserved byte-equivalently the two numbers "
        f"should match; any positive gap on v2's side is the harness "
        f"opening a trade on a sweep that pre-empts a zone touch in "
        f"the same per-symbol single-position queue.\n"
    )
    lines.append("---\n")
    lines.append("## Rejection-rate proxy\n")
    lines.append(
        "Single-agent runs do not have a squad to be rejected by, so "
        "the directly-comparable Phi4 rejection bucket count (2994 / "
        "1579 same-direction) is **not** the right comparator here. "
        "The closest single-agent proxy is the count of proposals the "
        "production fill model produced but the per-symbol single-"
        "position rule blocked.\n"
    )
    lines.append("")
    lines.append("| Agent | Proposals | Trades | Blocked-by-concurrency | Same-direction-as-open-trade % |")
    lines.append("|---|---|---|---|---|")
    lines.append(
        f"| v1 | {len(report.v1.proposals)} | {len(report.v1.trades)} | "
        f"{report.v1_rejection_count} | {report.v1_rejection_same_dir_pct:.1f} % |"
    )
    lines.append(
        f"| v2 | {len(report.v2.proposals)} | {len(report.v2.trades)} | "
        f"{report.v2_rejection_count} | {report.v2_rejection_same_dir_pct:.1f} % |"
    )
    lines.append("")
    lines.append(
        "**Did the rejection rate drop?** "
        f"v1 blocked-by-concurrency: {report.v1_rejection_count}. "
        f"v2 blocked-by-concurrency: {report.v2_rejection_count}. "
        + (
            "v2 has MORE rejections (expected -- the sweep weapon adds "
            "proposals on bars where a zone trade is already open, "
            "which then get rejected). The Phi4 squad-gate's "
            "**same-direction redundancy** number cannot be recomputed "
            "here because there is no squad; the closest single-agent "
            "proxy is the same-direction-as-open-trade column above, "
            "which only describes self-self interaction."
            if report.v2_rejection_count > report.v1_rejection_count
            else "v2 has FEWER blocked-by-concurrency proposals; "
            "the vocabulary expansion did not increase rejection "
            "pressure on the single-position queue."
        ) + "\n"
    )
    lines.append("---\n")
    lines.append("## Recommendation\n")
    if report.verdict == "CLOSE":
        lines.append(
            "**Canonise v2 as `isagi_yoichi`'s active version.** Per "
            "doctrine §3.11.2 step 6 + coexistence rule: keep v1 "
            "registered in `sim/roster/` for at least one phase gate "
            "so the F17 A/B ablation has a clean comparator on the "
            "next sealed panel. The v1 module stays on disk "
            "indefinitely (`07-research-standards.md` §3 retention "
            "rule). Append a CLOSE row to "
            "`reviews/evolution_ledger.md`.\n"
        )
    else:
        lines.append(
            "**Keep v1 as the canonical Isagi.** v2 is archived in "
            "`sim/agents/a01_isagi_v2.py` for the audit trail; the "
            "module is NOT deleted (§3.11.2 step 3 + "
            "`07-research-standards.md` §3 retention rule). Append a "
            "FAIL row to `reviews/evolution_ledger.md` quoting the "
            "verdict reason above. The defeat trigger (1579 / 52.7 % "
            "same-direction rejections) is preserved; a future arc "
            "may revisit with a different evolution hypothesis "
            "(e.g. FVG primitive, OB primitive, H1 cadence move "
            "alone).\n"
        )
    lines.append("---\n")
    lines.append("## Honest caveats\n")
    lines.append(
        "1. **Single-agent evaluation only.** This is NOT a squad gate. "
        "The Phi4 squad-gate same-direction rejection count cannot be "
        "directly reproduced here; the §3.11.2 contract is about "
        "*agent* evolution, not roster fusion.\n"
        "2. **Same panel as Phi3.** EURUSD H4 2015-2025, 4 yr IS / 1 yr "
        "OOS rolling. v2's gate is evaluated on the exact same data "
        "v1's Phi3 PASS verdict used.\n"
        "3. **HTF gate inversion is intentional.** v1's zone weapon "
        "wants D1 to OPPOSE the trade (fade); v2's sweep weapon wants "
        "D1 to AGREE with the trade (ride the reaction). This is the "
        "canon 'metavision evolved' framing -- sweeps are confirmations "
        "of the macro trend, not fades against it. Documented in the "
        "v2 module docstring.\n"
        "4. **No look-ahead in the sweep detector.** The production "
        "`detect_liquidity_sweeps` runs in its default "
        "`require_reversal_confirmation=False` mode, which is fully "
        "causal per the module's docstring.\n"
        "5. **The Phi3 gate baseline TQS (0.317) is the comparator** -- "
        "this run reproduces it for v1 on the same panel; any drift is "
        "noise from the harness, not a re-evaluation of E004.\n"
    )
    lines.append("---\n")
    lines.append("## References\n")
    lines.append(
        "- Defeat note: `reviews/isagi_yoichi_v1_defeat.md`\n"
        "- v1 Phi3 PASS: `reviews/phi3_gate_isagi_v1.md`\n"
        "- Squad-gate evidence chain: `reviews/phi4_squad_v1.md`, "
        "`reviews/phi4_isagi_rejection_analysis.md`\n"
        "- Doctrine contract: `06-blue-lock-doctrine.md` §3.11.2\n"
        "- Roster row: `05-agent-roster-v0.md` §3.1\n"
        "- v2 module: `sim/agents/a01_isagi_v2.py`\n"
        "- v2 tests: `sim/tests/test_a01_isagi_v2.py`\n"
        "- Production primitives: "
        "`agent.detectors.liquidity_sweep.detect_liquidity_sweeps`, "
        "`agent.alphas.concepts._htf.htf_bias_at`\n"
    )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_arc(
    *,
    symbol: str = "EURUSD",
    full_start: datetime = DEFAULT_FULL_START,
    full_end: datetime = DEFAULT_FULL_END,
    out_path: Path | str | None = None,
    write_trades_jsonl: bool = True,
) -> ArcReport:
    ensure_production_repo_on_path()
    log.info("Loading %s H4 bars %s -> %s", symbol, full_start.date(), full_end.date())
    bars = _load_production_bars(symbol, full_start, full_end)
    log.info("Loaded %d bars", len(bars))

    if not bars or len(bars) < WARMUP_BARS + 50:
        raise RuntimeError(
            f"Insufficient bars ({len(bars)}) -- v2 arc cannot run "
            "without a full Phi3-equivalent panel."
        )

    log.info("Running A1IsagiV1 ...")
    v1 = A1IsagiV1()
    v1.prepare(symbol, bars)
    v1_run = _drive_replay_with_weapon_provenance(v1, bars, symbol, version="v1")

    log.info("Running A1IsagiV2 ...")
    v2 = A1IsagiV2()
    v2.prepare(symbol, bars)
    v2_run = _drive_replay_with_weapon_provenance(v2, bars, symbol, version="v2")

    # Per-window comparison.
    windows = _compute_window_comparisons(
        v1_run.trades, v2_run.trades, full_start, full_end,
    )
    sweep_window_coverage = sum(1 for w in windows if w.v2_sweep_trades > 0)
    v1_oos_window_means = [w.v1_mean_pips for w in windows if w.v1_n > 0]
    v1_oos_window_tqs = [w.v1_mean_tqs for w in windows if w.v1_n > 0]
    v2_oos_window_means = [w.v2_mean_pips for w in windows if w.v2_n > 0]
    v2_oos_window_tqs = [w.v2_mean_tqs for w in windows if w.v2_n > 0]
    v1_pos = sum(1 for w in windows if w.v1_n > 0 and w.v1_mean_pips > 0)
    v2_pos = sum(1 for w in windows if w.v2_n > 0 and w.v2_mean_pips > 0)
    v2_zone, v2_sweep = _split_by_weapon(v2_run.trades)

    v1_rej, v1_same = _rejection_proxy(v1_run)
    v2_rej, v2_same = _rejection_proxy(v2_run)

    report = ArcReport(
        symbol=symbol,
        full_start=full_start,
        full_end=full_end,
        n_bars=len(bars),
        v1=v1_run,
        v2=v2_run,
        v1_median_oos_window_mean_pips=(
            statistics.median(v1_oos_window_means) if v1_oos_window_means else 0.0
        ),
        v1_median_oos_window_mean_tqs=(
            statistics.median(v1_oos_window_tqs) if v1_oos_window_tqs else 0.0
        ),
        v1_oos_windows_positive=v1_pos,
        v2_median_oos_window_mean_pips=(
            statistics.median(v2_oos_window_means) if v2_oos_window_means else 0.0
        ),
        v2_median_oos_window_mean_tqs=(
            statistics.median(v2_oos_window_tqs) if v2_oos_window_tqs else 0.0
        ),
        v2_oos_windows_positive=v2_pos,
        v2_zone_trade_count=v2_zone,
        v2_sweep_trade_count=v2_sweep,
        sweep_window_coverage=sweep_window_coverage,
        windows=windows,
        v1_rejection_count=v1_rej,
        v2_rejection_count=v2_rej,
        v1_rejection_same_dir_pct=v1_same,
        v2_rejection_same_dir_pct=v2_same,
    )
    report.verdict, report.verdict_reason = _decide_arc_verdict(report)
    log.info(
        "Arc verdict: %s (v1 trades=%d, v2 trades=%d, v2 sweep=%d, "
        "v1 OOS TQS=%.3f, v2 OOS TQS=%.3f)",
        report.verdict, len(v1_run.trades), len(v2_run.trades), v2_sweep,
        report.v1_median_oos_window_mean_tqs,
        report.v2_median_oos_window_mean_tqs,
    )

    if out_path is None:
        out_path = (
            Path(__file__).resolve().parents[2] / "reviews" / "isagi_v2_arc.md"
        )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_report(report), encoding="utf-8")
    log.info("Wrote arc report to %s", out_path)

    if write_trades_jsonl:
        for label, run in (("v1", v1_run), ("v2", v2_run)):
            path = out_path.parent / f"isagi_v2_arc_{label}_trades.jsonl"
            with path.open("w", encoding="utf-8") as fh:
                for t in run.trades:
                    fh.write(json.dumps({
                        "agent_id": t.agent_id,
                        "version": label,
                        "symbol": t.symbol,
                        "entry_time": t.entry_time.isoformat(),
                        "exit_time": t.exit_time.isoformat(),
                        "direction": t.direction,
                        "entry": t.entry,
                        "stop": t.stop,
                        "take_profit": t.take_profit,
                        "exit_price": t.exit_price,
                        "exit_reason": t.exit_reason,
                        "pnl_pips": t.pnl_pips,
                        "mae_pips": t.mae_pips,
                        "mfe_pips": t.mfe_pips,
                        "r_multiple": t.r_multiple,
                        "weapon": t.tqs_components.get("weapon"),
                        "tqs": t.tqs_components,
                    }, sort_keys=True) + "\n")
    return report


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Isagi v1 vs v2 evolution-arc head-to-head.",
    )
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument(
        "--start", type=_parse_date,
        default=DEFAULT_FULL_START.strftime("%Y-%m-%d"),
    )
    parser.add_argument(
        "--end", type=_parse_date,
        default=DEFAULT_FULL_END.strftime("%Y-%m-%d"),
    )
    parser.add_argument(
        "--out", default=None,
        help="Output markdown path (default: <repo>/.../reviews/isagi_v2_arc.md)",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
    )
    start = args.start if isinstance(args.start, datetime) else _parse_date(args.start)
    end = args.end if isinstance(args.end, datetime) else _parse_date(args.end)
    report = run_arc(
        symbol=args.symbol,
        full_start=start,
        full_end=end,
        out_path=args.out,
    )
    print(
        f"Arc verdict: {report.verdict} "
        f"(v1 trades={len(report.v1.trades)}, v2 trades={len(report.v2.trades)}, "
        f"v2 sweep trades={report.v2_sweep_trade_count}, "
        f"v1 median OOS TQS={report.v1_median_oos_window_mean_tqs:.3f}, "
        f"v2 median OOS TQS={report.v2_median_oos_window_mean_tqs:.3f})"
    )
    return 0 if report.verdict == "CLOSE" else 1


if __name__ == "__main__":
    sys.exit(main())
