"""Φ4.1 expanded-squad gate evaluation harness.

The Φ4 squad gate FAILED at 0.98x Isagi-alone TQS with Nagi firing 0
confluence thoughts (`reviews/phi4_squad_v1.md`). The Φ4 diagnosis:
predicate starvation -- only Isagi + Barou traded, and the 2-distinct-
peer floor was structurally unreachable. Φ4.1 expands the roster to
test that hypothesis directly.

What changes from Φ4
--------------------

* **Squad expansion** -- 4 -> 8 agents:
    A1 Isagi v1            (carryover, zone_d1_against)
    A6 Nagi v1             (carryover, confluence-only)
    A7 Barou v1            (carryover, USDCAD baseline-zone)
    A10 Kunigami v1        (carryover, anti-tilt)
    A2 Bachira v1          (NEW: rebel baseline-zone, all 3 symbols)
    A3 Rin v1              (NEW: precision zone_d1_against, EURUSD)
    A4 Chigiri v1          (NEW: ATR breakout continuation)
    A5 Reo v1              (NEW: chameleon mirror, no-trade)
* **All-symbol stream** -- the engine drives EURUSD + GBPUSD + USDCAD H4
  in lockstep (Φ4 ran EURUSD + USDCAD only). GBPUSD is added because
  Bachira + Chigiri trade it; without it those agents are essentially
  silenced.
* **F17 candidates expanded** -- Nagi + Barou (carryover) + Bachira,
  Rin, Chigiri, Reo measured for ΔInfo on the same sampled OOS windows.

What stays the same
-------------------

* Walk-forward windowing (4 yr IS / 1 yr OOS, 7 windows).
* Locked gate statistic: median OOS-window mean TQS.
* Production-grade fill model (`agent.alphas.backtest._open` +
  `_check_exit`) -- byte-comparable to Φ3.
* Per-symbol single-position rule.
* Two-phase tick order (observe-all then intend-all); same-tick reads
  forbidden by the doctrine sec 3.8 ledger guards.
* Aggregator semantics: per-symbol highest-conviction-wins.
* Verdict thresholds: PASS >= 1.10x, PARTIAL 1.00..1.10x, FAIL < 1.00x.

CLI
---

    PYTHONPATH=../multi-pair-trading-agent:. \\
        M001_PRODUCTION_REPO=../multi-pair-trading-agent \\
        ../multi-pair-trading-agent/.venv/bin/python \\
        -m programs.M001_multi_agent_ensemble.sim.scoring.run_phi41_gate
        [--start 2015-01-01] [--end 2025-12-31]
        [--out-dir reviews/]
        [--delta-info-windows 3]

Notes
-----

* If Nagi fires > 0 confluence thoughts in Φ4.1, the predicate-
  starvation diagnosis from Φ4 is CONFIRMED.
* If Nagi STILL fires 0 thoughts (with Reo specifically designed to
  give him a deterministic second peer), the problem is elsewhere
  (coordinate non-overlap, tag mismatch, one-bar lag mechanics, or
  a bug in the ledger plumbing).
* Reported verdicts are HONEST. No silent retuning.
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
from programs.M001_multi_agent_ensemble.sim.agents.a02_bachira import A2BachiraV1
from programs.M001_multi_agent_ensemble.sim.agents.a03_rin import A3RinV1
from programs.M001_multi_agent_ensemble.sim.agents.a04_chigiri import A4ChigiriV1
from programs.M001_multi_agent_ensemble.sim.agents.a05_reo import A5ReoV1
from programs.M001_multi_agent_ensemble.sim.agents.a06_nagi import A6NagiV1
from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import A7BarouV1
from programs.M001_multi_agent_ensemble.sim.agents.a10_kunigami import (
    A10KunigamiV1,
)
from programs.M001_multi_agent_ensemble.sim.core.ledger import (
    FullLedger,
    RedactedLedger,
)
from programs.M001_multi_agent_ensemble.sim.core.types import (
    AgentProposal,
    Thought,
)
from programs.M001_multi_agent_ensemble.sim.scoring.delta_info import (
    DeltaInfoResult,
    delta_info,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_isagi_phi3_gate import (
    DEFAULT_FULL_END,
    DEFAULT_FULL_START,
    IS_YEARS,
    OOS_YEARS,
    WARMUP_BARS,
    TradeRecord,
    _load_production_bars,
    _window_starts,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
    DEFAULT_DELTA_INFO_WINDOWS,
    ISAGI_ALONE_MEDIAN_OOS_PIPS,
    ISAGI_ALONE_MEDIAN_OOS_TQS,
    ISAGI_ALONE_OOS_WINDOWS_POSITIVE,
    SQUAD_PARTIAL_RATIO,
    SQUAD_PASS_RATIO,
    SquadGateReport,
    SquadRunOutput,
    SquadWindowStats,
    _drive_squad_replay,
    _drive_squad_replay_with_isolated_candidate,
    _sample_windows,
    _summarise,
    render_rejection_analysis,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SYMBOLS_PHI41: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDCAD")

# Locked Φ4.1 agent identity registry. The ordering controls (a) the
# squad construction order in run_phi41_gate, (b) the per-agent KPI
# table order in the rendered review, (c) the F17 sampling order.
# Reo is included even though he never trades -- his telemetry feeds
# the Nagi-confluence diagnostic. Kunigami never trades either.
PHI41_AGENT_ORDER: tuple[str, ...] = (
    "isagi_yoichi",
    "bachira_meguru",
    "itoshi_rin",
    "chigiri_hyoma",
    "reo_mikage",
    "nagi_seishiro",
    "barou_shoei",
    "kunigami_rensuke",
)

# F17 candidates for Φ4.1. Tier-2 strikers whose edge plausibly depends
# on ledger reads. Reo is structurally Tier-2 (his weapon IS reading
# the ledger); we still measure to make the audit trail explicit.
F17_CANDIDATES: tuple[tuple[str, Any], ...] = (
    ("nagi_seishiro", A6NagiV1),
    ("barou_shoei", A7BarouV1),
    ("bachira_meguru", A2BachiraV1),
    ("itoshi_rin", A3RinV1),
    ("chigiri_hyoma", A4ChigiriV1),
    ("reo_mikage", A5ReoV1),
)


# ---------------------------------------------------------------------------
# Window slicing (Φ4.1 = same as Φ4 but with the expanded agent ID set)
# ---------------------------------------------------------------------------

def _compute_phi41_windows(
    trades: list[TradeRecord],
    *,
    full_start: datetime,
    full_end: datetime,
    all_agent_ids: tuple[str, ...],
) -> list[SquadWindowStats]:
    out: list[SquadWindowStats] = []
    for ws in _window_starts(full_start, full_end):
        is_start = ws
        is_end = datetime(ws.year + IS_YEARS, 1, 1, tzinfo=timezone.utc)
        oos_start = is_end
        oos_end = datetime(
            oos_start.year + OOS_YEARS, 1, 1, tzinfo=timezone.utc,
        )
        if oos_end > full_end:
            oos_end = full_end
        oos_tr = [t for t in trades if oos_start <= t.entry_time < oos_end]
        per_agent: dict[str, tuple[int, float, float, float, float]] = {}
        for aid in all_agent_ids:
            slice_ = [t for t in oos_tr if t.agent_id == aid]
            mean_p, med_p, mean_tqs, wr, n = _summarise(slice_)
            per_agent[aid] = (n, mean_p, med_p, mean_tqs, wr)
        sq_mean, sq_med, sq_tqs, sq_wr, sq_n = _summarise(oos_tr)
        out.append(SquadWindowStats(
            is_start=is_start, is_end=is_end,
            oos_start=oos_start, oos_end=oos_end,
            per_agent_oos=per_agent,
            squad_oos_n=sq_n,
            squad_oos_mean_pips=sq_mean,
            squad_oos_median_pips=sq_med,
            squad_oos_mean_tqs=sq_tqs,
            squad_oos_win_rate=sq_wr,
        ))
    return out


# ---------------------------------------------------------------------------
# Verdict logic
# ---------------------------------------------------------------------------

def _decide_phi41_verdict(report: SquadGateReport) -> tuple[str, str]:
    if report.n_trades < 30:
        return (
            "PROVISIONAL",
            f"only {report.n_trades} squad trades; below the 30-trade "
            "floor for a statistical gate claim",
        )
    ratio = report.squad_vs_isagi_tqs_ratio
    if ratio >= SQUAD_PASS_RATIO:
        return (
            "PASS",
            f"squad median OOS-window mean TQS "
            f"{report.squad_median_oos_window_mean_tqs:.3f} is "
            f"{ratio:.2f}x Isagi-alone "
            f"({ISAGI_ALONE_MEDIAN_OOS_TQS:.3f}); G5 threshold 1.10x",
        )
    if ratio >= SQUAD_PARTIAL_RATIO:
        return (
            "PARTIAL",
            f"squad TQS {report.squad_median_oos_window_mean_tqs:.3f} "
            f"is {ratio:.2f}x Isagi-alone "
            f"({ISAGI_ALONE_MEDIAN_OOS_TQS:.3f}) -- positive lift "
            "but below 1.10x G5 floor",
        )
    return (
        "FAIL",
        f"squad TQS {report.squad_median_oos_window_mean_tqs:.3f} is "
        f"{ratio:.2f}x Isagi-alone ({ISAGI_ALONE_MEDIAN_OOS_TQS:.3f}) "
        "-- expanding the roster did not close the gap; reported "
        "honestly",
    )


# ---------------------------------------------------------------------------
# Report renderer
# ---------------------------------------------------------------------------

def render_phi41_report(
    report: SquadGateReport,
    *,
    nagi_confluence_count_phi4: int = 0,
    reo_mirror_count: int = 0,
    rin_precision_lift_count: int = 0,
    bachira_rebel_lift_count: int = 0,
    chigiri_breakout_count: int = 0,
) -> str:
    lines: list[str] = []
    lines.append("# Φ4.1 expanded-squad gate -- 8-agent vs A1 Isagi-alone\n")
    lines.append(f"**Run date:** {datetime.now(timezone.utc).isoformat()}\n")
    lines.append(
        f"**Window:** {report.full_start.date()} -> {report.full_end.date()} "
        f"on **{', '.join(report.symbols)}** (H4)\n"
    )
    lines.append(
        "**Agents:** A1 Isagi v1, A2 Bachira v1 (rebel baseline-zone), "
        "A3 Rin v1 (precision zone_d1_against), A4 Chigiri v1 (ATR "
        "breakout), A5 Reo v1 (chameleon mirror, no-trade), A6 Nagi v1 "
        "(confluence), A7 Barou v1 (USDCAD baseline-zone), A10 Kunigami "
        "v1 (anti-tilt).\n"
    )
    lines.append("---\n")
    lines.append("## Verdict\n")
    lines.append(f"**Φ4.1 gate (G5 statistic): `{report.verdict}`**\n")
    lines.append(f"_{report.verdict_reason}_\n")
    lines.append(
        "Honest framing: PASS = squad TQS >= 1.10x Isagi-alone. "
        "PARTIAL = positive lift below 1.10x. FAIL = adding agents "
        "did NOT close the gap. Reported verbatim; no silent "
        "retuning per user constraint.\n"
    )
    lines.append("---\n")
    # Predicate-starvation falsifier headline.
    lines.append("## Predicate-starvation falsifier headline\n")
    lines.append("")
    lines.append("| Metric | Φ4 | Φ4.1 | Delta |")
    lines.append("|---|---|---|---|")
    delta_str = (
        f"+{report.nagi_fired_count}"
        if report.nagi_fired_count > nagi_confluence_count_phi4
        else str(report.nagi_fired_count - nagi_confluence_count_phi4)
    )
    lines.append(
        f"| **Nagi confluence-firing thoughts** | "
        f"{nagi_confluence_count_phi4} | **{report.nagi_fired_count}** | {delta_str} |"
    )
    lines.append(
        f"| Reo mirror Thoughts emitted | n/a (Reo new in Φ4.1) | "
        f"{reo_mirror_count} | -- |"
    )
    lines.append(
        f"| Rin precision-lift Thoughts | n/a (Rin new in Φ4.1) | "
        f"{rin_precision_lift_count} | -- |"
    )
    lines.append(
        f"| Bachira rebel-lift Thoughts | n/a (Bachira new in Φ4.1) | "
        f"{bachira_rebel_lift_count} | -- |"
    )
    lines.append(
        f"| Chigiri breakout-firing Thoughts | n/a (Chigiri new in Φ4.1) | "
        f"{chigiri_breakout_count} | -- |"
    )
    lines.append(
        f"| Barou devour-lift Thoughts | 0 | "
        f"{report.devour_fired_count} | -- |"
    )
    lines.append("")
    lines.append(
        "**Interpretation:** The Φ4.1 hypothesis is that the Φ4 FAIL "
        "was driven by predicate starvation. If Nagi's confluence "
        "count moves from 0 to ANY positive number, the hypothesis "
        "is confirmed -- the predicate works, it just needed more "
        "peer fuel. If it stays at 0 with Reo specifically designed "
        "to deterministically lift any qualifying peer above Nagi's "
        "floor, the diagnosis was wrong and the problem is elsewhere "
        "(see the detailed diagnosis section at the bottom).\n"
    )
    lines.append("---\n")
    lines.append("## Squad TQS vs Isagi-alone\n")
    lines.append("")
    lines.append("| Metric | Squad (Φ4.1) | Isagi-alone (Φ3) | Ratio |")
    lines.append("|---|---|---|---|")
    if ISAGI_ALONE_MEDIAN_OOS_PIPS > 0:
        pip_ratio = (
            report.squad_median_oos_window_mean_pips
            / ISAGI_ALONE_MEDIAN_OOS_PIPS
        )
    else:
        pip_ratio = 0.0
    lines.append(
        f"| Median OOS-window mean pips/trade | "
        f"**{report.squad_median_oos_window_mean_pips:+.2f}** | "
        f"+{ISAGI_ALONE_MEDIAN_OOS_PIPS:.2f} | "
        f"{pip_ratio:.2f}x |"
    )
    lines.append(
        f"| Median OOS-window mean TQS (F12) | "
        f"**{report.squad_median_oos_window_mean_tqs:.3f}** | "
        f"{ISAGI_ALONE_MEDIAN_OOS_TQS:.3f} | "
        f"**{report.squad_vs_isagi_tqs_ratio:.2f}x** |"
    )
    lines.append(
        f"| OOS windows positive | "
        f"{report.squad_oos_windows_positive} / "
        f"{report.squad_oos_windows_total} | "
        f"{ISAGI_ALONE_OOS_WINDOWS_POSITIVE} / 7 | -- |"
    )
    lines.append("")
    lines.append("---\n")
    lines.append("## Per-agent KPIs (full dev window)\n")
    lines.append("")
    lines.append(
        "| Agent | Trades | Mean pips | Median pips | Mean TQS | Win % |"
    )
    lines.append("|---|---|---|---|---|---|")
    for aid in PHI41_AGENT_ORDER:
        kpi = report.per_agent_overall_kpis.get(aid)
        if kpi is None:
            lines.append(
                f"| `{aid}` | 0 | -- | -- | -- | -- |"
            )
            continue
        lines.append(
            f"| `{aid}` | {int(kpi['n'])} | "
            f"{kpi['mean_pips']:+.2f} | {kpi['median_pips']:+.2f} | "
            f"{kpi['mean_tqs']:.3f} | {kpi['win_rate']*100:.1f}% |"
        )
    lines.append("")
    lines.append(
        "_Note: Reo and Kunigami emit no Proposals (Reo by design, "
        "Kunigami is a risk auxiliary). Their rows show no trades._\n"
    )
    lines.append("---\n")
    lines.append("## Per-window walk-forward (squad-level)\n")
    lines.append("(4 yr IS / 1 yr OOS rolling -- matches E004 + Φ3)\n")
    lines.append("")
    header_cols = ["IS window", "OOS yr"] + [
        col
        for aid in PHI41_AGENT_ORDER
        if aid in report.per_agent_overall_kpis
        for col in [f"{aid} n", f"{aid} mean pips"]
    ] + ["Squad n", "Squad mean pips", "Squad mean TQS"]
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("|" + "|".join(["---"] * len(header_cols)) + "|")
    for w in report.windows:
        row = [
            f"{w.is_start.year}-{w.is_end.year - 1}",
            f"{w.oos_start.year}",
        ]
        for aid in PHI41_AGENT_ORDER:
            if aid not in report.per_agent_overall_kpis:
                continue
            n, mean_p, _, _, _ = w.per_agent_oos.get(
                aid, (0, 0.0, 0.0, 0.0, 0.0),
            )
            row.append(str(int(n)))
            row.append(f"{mean_p:+.2f}")
        row.extend([
            str(int(w.squad_oos_n)),
            f"{w.squad_oos_mean_pips:+.2f}",
            f"{w.squad_oos_mean_tqs:.3f}",
        ])
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append("---\n")
    lines.append("## F17 ΔInfo (Tier-2 candidates)\n")
    lines.append("")
    lines.append(
        "| Agent | n informed | n isolated | Median TQS informed | "
        "Median TQS isolated | ΔInfo | 95% CI | Tier | Notes |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for aid in PHI41_AGENT_ORDER:
        di = report.delta_info_results.get(aid)
        if di is None:
            continue
        underpowered_flags = []
        if di.n_informed < 100 or di.n_isolated < 100:
            underpowered_flags.append("[underpowered]")
        # Reo isolated arm produces 0 trades by design -- structural
        # Tier-2 marker.
        if aid == "reo_mikage":
            underpowered_flags.append("[structural Tier-2: isolated arm always trivial]")
        notes = " ".join(underpowered_flags)
        lines.append(
            f"| `{aid}` | {di.n_informed} | {di.n_isolated} | "
            f"{di.median_informed:.3f} | {di.median_isolated:.3f} | "
            f"{di.delta_info:+.3f} | "
            f"[{di.ci_low:+.3f}, {di.ci_high:+.3f}] | "
            f"{di.tier} | {notes} |"
        )
    lines.append("")
    lines.append(
        "_ΔInfo measures whether each Tier-2 candidate's edge depends "
        "on reading the ledger. Tier-2 = ΔInfo > 0 AND bootstrap CI "
        "lower bound > 0. The `[underpowered]` flag fires when "
        "informed or isolated trade count < 100, per the user spec._\n"
    )
    lines.append("---\n")
    lines.append("## Engine telemetry\n")
    lines.append("")
    lines.append(f"- Symbols: {', '.join(report.symbols)} (H4)")
    lines.append(f"- Thoughts emitted (squad-wide): {report.n_thoughts}")
    lines.append(f"- Proposals (all): {report.n_proposals_all}")
    lines.append(f"- Proposals accepted: {report.n_proposals_accepted}")
    lines.append(f"- Proposals rejected: {report.n_proposals_rejected}")
    lines.append(f"- Trades opened+closed: {report.n_trades}")
    lines.append(f"- Nagi confluence-firing thoughts: {report.nagi_fired_count}")
    lines.append(f"- Barou devour lifts applied: {report.devour_fired_count}")
    lines.append(f"- Bachira rebel lifts applied: {bachira_rebel_lift_count}")
    lines.append(f"- Rin precision lifts applied: {rin_precision_lift_count}")
    lines.append(f"- Chigiri breakout-firing thoughts: {chigiri_breakout_count}")
    lines.append(f"- Reo mirror Thoughts emitted: {reo_mirror_count}")
    lines.append(
        f"- Kunigami warning thoughts: {report.kunigami_warning_count}"
    )
    lines.append("")
    lines.append("---\n")
    lines.append("## Diagnosis -- did predicate starvation get fixed?\n")
    # Falsifier logic stated upfront.
    if report.nagi_fired_count > 0:
        diag_headline = (
            "**YES.** Nagi's confluence count moved from 0 (Φ4) to "
            f"**{report.nagi_fired_count}** (Φ4.1). The Φ4 predicate-"
            "starvation hypothesis is confirmed -- the F11/F13 "
            "predicate works, it just needed more peer fuel. The "
            "expanded roster (Bachira, Rin, Chigiri, Reo) delivered "
            "enough overlapping coordinate × tag × direction "
            "combinations to clear the 2-distinct-peer floor.\n"
        )
    else:
        diag_headline = (
            "**NO.** Nagi's confluence count is still 0 even with the "
            "expanded roster. Reo was specifically designed to lift "
            "ANY qualifying peer Thought above Nagi's floor; the fact "
            "that Nagi still didn't fire means the problem is NOT in "
            "the conviction floor. Most likely causes (in priority "
            "order): (1) **coordinate band non-overlap** -- peer "
            "coordinates are at materially different price levels, "
            "even though tags match; (2) **tag overlap insufficient** "
            "-- agents share fewer than 2 tags after the Reo merger "
            "due to different vocabularies; (3) **one-bar-lag "
            "mechanics** -- peer thoughts emitted at tick T are not "
            "visible to Nagi until tick T+1 AND must still be inside "
            "ttl_ticks; with H4 cadence the window is 24h "
            "(ttl_ticks=6) which should be enough -- worth checking "
            "the journal. Recommended Φ4.2 diagnostic: emit a "
            "per-tick `nagi_predicate_audit` log line counting "
            "(visible peers, peers passing conviction floor, peers "
            "matching direction, peers with overlapping band, "
            "peers with >= 2 shared tags) so we can see EXACTLY "
            "which gate is killing the predicate.\n"
        )
    lines.append(diag_headline)
    lines.append(
        f"- **Reo mirror Thoughts:** {reo_mirror_count}. Reo's "
        "mirror count is the lower bound on Nagi-qualifying peer "
        "lifts. If this is large but Nagi fires 0, the predicate is "
        "blocked by coordinate / tag / direction (not by conviction).\n"
    )
    lines.append(
        f"- **Bachira rebel lifts:** {bachira_rebel_lift_count}. These "
        "are the bars where Bachira jumped from 0.65 (base) to 0.75 "
        "(rebel) -- a Nagi-qualifying conviction with shared zone "
        "tags. A low count here means the recent-opposite-swing "
        "trigger fires rarely; a high count means Nagi had plenty "
        "of Bachira peer fuel on EURUSD + GBPUSD + USDCAD.\n"
    )
    lines.append(
        f"- **Rin precision lifts:** {rin_precision_lift_count}. These "
        "are the bars where Rin's strict R:R + stop-distance filter "
        "passed and conviction jumped to 0.80. Shares all "
        "zone_d1_against tags with Isagi by construction -- if this "
        "is > 0 on the same ticks Isagi fires, Nagi sees a 2-peer "
        "confluence on EURUSD.\n"
    )
    lines.append(
        f"- **Chigiri breakout thoughts:** {chigiri_breakout_count}. "
        "Chigiri is the diversity striker (NOT a zone wrap). His "
        "tags do NOT inherit `zone_d1_against`, so he tags-overlaps "
        "with Reo only by the Reo-merger trick (Reo inherits "
        "Chigiri's tags when Chigiri is the highest-conviction peer). "
        "Reads on Nagi's predicate are therefore Chigiri-driven only "
        "via Reo's mediation -- this is the cleanest test of the "
        "tag-overlap pathway.\n"
    )
    lines.append("---\n")
    lines.append("## Honest caveats\n")
    lines.append(
        "1. **One-bar chemical-reaction lag is intentional** -- "
        "doctrine sec 3.8 forbids same-tick reads.\n"
        "2. **Per-symbol single-position rule** preserves the E004 "
        "execution contract.\n"
        "3. **Risk Conductor: equal risk-budget per agent** for v1 "
        "(no HRP). Φ5 wires HRP.\n"
        "4. **`regime_fit = 0.5` placeholder** on every Proposal -- "
        "regime classifier (F1=0.496 weak-label) not yet wired.\n"
        "5. **F17 ΔInfo sampled** on a subset of OOS windows for "
        "compute economy; underpowered arms flagged in the table.\n"
        "6. **No Φ4.2 chemical-reaction beauty bonus** wired yet.\n"
        "7. **Squad-vs-baseline comparator caveat.** The Φ3 baseline "
        "ran on EURUSD ONLY. The Φ4.1 squad ran on EURUSD + GBPUSD + "
        "USDCAD (GBPUSD added so Bachira + Chigiri are not silenced). "
        "The TQS ratio is calculated against EURUSD-only Isagi-alone "
        "-- a structural conservatism.\n"
        "8. **Reo's isolated-arm trade count is always 0** by "
        "construction (he never trades). The F17 ΔInfo column for "
        "Reo therefore reports the structural Tier-2 marker rather "
        "than a meaningful CI.\n"
    )
    lines.append("")
    lines.append("## References\n")
    lines.append(
        "- Φ4 FAIL diagnostic: `reviews/phi4_squad_v1.md`\n"
        "- Doctrine: `06-blue-lock-doctrine.md` sec 3.1 / 3.3 / 3.5 / 3.8 / 3.11\n"
        "- Roster (Φ4.1): `sim/roster/mvp_phi41.yaml`\n"
        "- Experiment architecture: `09-experiment-architecture.md` sec 1.5 (G5)\n"
        "- Rejection analysis (companion): `reviews/phi41_isagi_rejection_analysis.md`\n"
    )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_phi41_gate(
    *,
    full_start: datetime = DEFAULT_FULL_START,
    full_end: datetime = DEFAULT_FULL_END,
    out_dir: Path | str | None = None,
    delta_info_windows: int = DEFAULT_DELTA_INFO_WINDOWS,
    write_jsonl: bool = True,
) -> SquadGateReport:
    """Run the Φ4.1 expanded-squad gate end-to-end."""
    ensure_production_repo_on_path()
    log.info(
        "Loading Φ4.1 bars %s -> %s on %s H4",
        full_start.date(), full_end.date(),
        ", ".join(SYMBOLS_PHI41),
    )
    bars_by_symbol: dict[str, list] = {}
    for sym in SYMBOLS_PHI41:
        bars_by_symbol[sym] = _load_production_bars(sym, full_start, full_end)
        log.info("Loaded %d %s bars", len(bars_by_symbol[sym]), sym)

    # Construct the 8-agent expanded squad.
    isagi = A1IsagiV1()
    bachira = A2BachiraV1()
    rin = A3RinV1()
    chigiri = A4ChigiriV1()
    reo = A5ReoV1()
    nagi = A6NagiV1()
    barou = A7BarouV1()
    kunigami = A10KunigamiV1()
    # `prepare` is called for every agent that has it.
    for sym, bars in bars_by_symbol.items():
        if not bars:
            continue
        for agent in (isagi, bachira, rin, chigiri, barou):
            if hasattr(agent, "prepare") and sym in agent.symbols:
                agent.prepare(sym, bars)
    agents = [isagi, bachira, rin, chigiri, reo, nagi, barou, kunigami]

    # Full squad run on the FullLedger. We pass `isagi` to satisfy the
    # _drive_squad_replay signature -- it uses `isagi._cfg` for the
    # production fill model (shared across all wrappers via the
    # cross-repo import).
    ledger = FullLedger()
    out = _drive_squad_replay(
        agents=agents,
        isagi=isagi,
        barou=barou,
        kunigami=kunigami,
        bars_by_symbol=bars_by_symbol,
        ledger=ledger,
    )
    log.info(
        "Φ4.1 squad run done -- %d thoughts, %d proposals, %d trades",
        len(out.thoughts), len(out.proposals_all), len(out.trades),
    )

    # Per-agent stats.
    all_agent_ids = tuple(a.agent_id for a in agents)
    per_agent_overall: dict[str, dict[str, float]] = {}
    per_agent_trade_counts: dict[str, int] = {}
    for aid in all_agent_ids:
        ag_trades = [t for t in out.trades if t.agent_id == aid]
        mean_p, med_p, mean_tqs, wr, n = _summarise(ag_trades)
        per_agent_overall[aid] = {
            "n": float(n),
            "mean_pips": float(mean_p),
            "median_pips": float(med_p),
            "mean_tqs": float(mean_tqs),
            "win_rate": float(wr),
        }
        per_agent_trade_counts[aid] = int(n)

    # Walk-forward windows.
    windows = _compute_phi41_windows(
        out.trades,
        full_start=full_start, full_end=full_end,
        all_agent_ids=all_agent_ids,
    )
    oos_mean_pips = [w.squad_oos_mean_pips for w in windows if w.squad_oos_n > 0]
    oos_mean_tqs = [w.squad_oos_mean_tqs for w in windows if w.squad_oos_n > 0]
    median_oos_pips = statistics.median(oos_mean_pips) if oos_mean_pips else 0.0
    mean_oos_pips = statistics.mean(oos_mean_pips) if oos_mean_pips else 0.0
    median_oos_tqs = statistics.median(oos_mean_tqs) if oos_mean_tqs else 0.0
    oos_positive = sum(
        1 for w in windows
        if w.squad_oos_n > 0 and w.squad_oos_mean_pips > 0
    )
    ratio = (
        median_oos_tqs / ISAGI_ALONE_MEDIAN_OOS_TQS
        if ISAGI_ALONE_MEDIAN_OOS_TQS > 0 else 0.0
    )

    # F17 ΔInfo on the F17_CANDIDATES roster. We reuse the Φ4
    # isolated-arm driver verbatim; it walks the 4-agent squad with
    # the candidate's reads redacted, and only counts the candidate's
    # trades. For agents that never trade (Reo), the isolated arm
    # produces 0 trades -- documented as a structural Tier-2 marker.
    delta_results: dict[str, DeltaInfoResult] = {}
    sampled_windows = _sample_windows(windows, n=delta_info_windows)
    for candidate_id, candidate_class in F17_CANDIDATES:
        informed = [
            t.tqs_components["tqs"]
            for t in out.trades if t.agent_id == candidate_id
        ]
        isolated_tqs: list[float] = []
        for w in sampled_windows:
            log.info(
                "F17 isolated arm: %s on %d-%d",
                candidate_id, w.is_start.year, w.oos_end.year,
            )
            iso_trades = _run_phi41_isolated_window(
                candidate_id=candidate_id,
                candidate_class=candidate_class,
                bars_by_symbol=bars_by_symbol,
                is_start=w.is_start, is_end=w.is_end,
                oos_start=w.oos_start, oos_end=w.oos_end,
            )
            isolated_tqs.extend(
                t.tqs_components["tqs"] for t in iso_trades
            )
        di = delta_info(
            candidate_id,
            informed,
            isolated_tqs,
            n_resamples=1000,
            block_size=5,
            seed=4242,
        )
        delta_results[candidate_id] = di

    # Telemetry counts.
    nagi_fired = sum(1 for t in out.thoughts if "nagi_confluence" in t.tags)
    devour_fired = sum(
        1 for t in out.thoughts if "barou_devour_applied" in t.tags
    )
    kuni_warned = sum(
        1 for t in out.thoughts
        if "kunigami_loss_streak_warning" in t.tags
        or "kunigami_overconfidence_warning" in t.tags
    )
    # Φ4.1-specific telemetry: new agents' signature tags.
    reo_mirror_count = sum(
        1 for t in out.thoughts if "reo_mirror" in t.tags
    )
    bachira_rebel_count = sum(
        1 for t in out.thoughts if "bachira_rebel_lift_applied" in t.tags
    )
    rin_precision_count = sum(
        1 for t in out.thoughts if "rin_precision_lift_applied" in t.tags
    )
    chigiri_breakout_count = sum(
        1 for t in out.thoughts if "chigiri_speed_breakout" in t.tags
    )

    verdict, reason = "PENDING", ""
    report = SquadGateReport(
        full_start=full_start, full_end=full_end,
        symbols=SYMBOLS_PHI41,
        n_thoughts=len(out.thoughts),
        n_proposals_all=len(out.proposals_all),
        n_proposals_accepted=len(out.proposals_accepted),
        n_proposals_rejected=len(out.proposals_rejected),
        n_trades=len(out.trades),
        per_agent_trade_counts=per_agent_trade_counts,
        per_agent_overall_kpis=per_agent_overall,
        squad_median_oos_window_mean_pips=median_oos_pips,
        squad_mean_oos_window_mean_pips=mean_oos_pips,
        squad_median_oos_window_mean_tqs=median_oos_tqs,
        squad_oos_windows_positive=oos_positive,
        squad_oos_windows_total=len(windows),
        isagi_alone_median_oos_pips=ISAGI_ALONE_MEDIAN_OOS_PIPS,
        isagi_alone_median_oos_tqs=ISAGI_ALONE_MEDIAN_OOS_TQS,
        squad_vs_isagi_tqs_ratio=float(ratio),
        verdict=verdict,
        verdict_reason=reason,
        windows=windows,
        delta_info_results=delta_results,
        sentinel_trigger_counts={},
        nagi_fired_count=int(nagi_fired),
        devour_fired_count=int(devour_fired),
        kunigami_warning_count=int(kuni_warned),
    )
    report.verdict, report.verdict_reason = _decide_phi41_verdict(report)
    log.info(
        "Φ4.1 squad gate verdict: %s (squad TQS %.3f, ratio %.2fx, "
        "Nagi confluence count %d)",
        report.verdict, report.squad_median_oos_window_mean_tqs, ratio,
        nagi_fired,
    )

    # Resolve out_dir.
    if out_dir is None:
        out_dir = Path(__file__).resolve().parents[2] / "reviews"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Persist artefacts.
    (out_dir / "phi41_squad_v1.md").write_text(
        render_phi41_report(
            report,
            nagi_confluence_count_phi4=0,
            reo_mirror_count=reo_mirror_count,
            rin_precision_lift_count=rin_precision_count,
            bachira_rebel_lift_count=bachira_rebel_count,
            chigiri_breakout_count=chigiri_breakout_count,
        ),
        encoding="utf-8",
    )
    log.info("Wrote Φ4.1 gate report to %s", out_dir / "phi41_squad_v1.md")

    if write_jsonl:
        with (out_dir / "phi41_squad_v1_trades.jsonl").open("w", encoding="utf-8") as fh:
            for t in out.trades:
                fh.write(json.dumps({
                    "agent_id": t.agent_id,
                    "symbol": t.symbol,
                    "entry_time": t.entry_time.isoformat(),
                    "exit_time": t.exit_time.isoformat(),
                    "direction": t.direction,
                    "entry": t.entry, "stop": t.stop,
                    "take_profit": t.take_profit, "exit_price": t.exit_price,
                    "exit_reason": t.exit_reason,
                    "pnl_pips": t.pnl_pips,
                    "mae_pips": t.mae_pips, "mfe_pips": t.mfe_pips,
                    "r_multiple": t.r_multiple,
                    "tqs": t.tqs_components,
                }, sort_keys=True) + "\n")
        with (out_dir / "phi41_squad_v1_rejected_proposals.jsonl").open("w", encoding="utf-8") as fh:
            for row in out.proposals_rejected:
                fh.write(json.dumps(row, sort_keys=True) + "\n")
        with (out_dir / "phi41_squad_v1_proposals_all.jsonl").open("w", encoding="utf-8") as fh:
            for p in out.proposals_all:
                fh.write(json.dumps(p.to_jsonable(), sort_keys=True) + "\n")
        log.info("Wrote Φ4.1 trades + proposals JSONL")

    # Rejection analysis -- companion report.
    proposals_by_tick: dict[int, list[AgentProposal]] = {}
    for p in out.proposals_all:
        proposals_by_tick.setdefault(int(p.tick_id), []).append(p)
    thoughts_by_tick: dict[int, list[Thought]] = {}
    for t in out.thoughts:
        thoughts_by_tick.setdefault(int(t.tick_id), []).append(t)
    isagi_rejections = [
        r for r in out.proposals_rejected
        if r.get("loser_agent_id") == "isagi_yoichi"
    ]
    rej_md, rej_buckets = render_rejection_analysis(
        isagi_rejections=isagi_rejections,
        thoughts_by_tick=thoughts_by_tick,
        proposals_by_tick=proposals_by_tick,
        full_start=full_start, full_end=full_end,
    )
    (out_dir / "phi41_isagi_rejection_analysis.md").write_text(
        rej_md, encoding="utf-8",
    )
    log.info(
        "Rejection analysis: same=%d, opposite=%d, silent=%d, elsewhere=%d",
        rej_buckets.same_direction, rej_buckets.opposite_direction,
        rej_buckets.silent, rej_buckets.own_setup_elsewhere,
    )

    return report


def _run_phi41_isolated_window(
    *,
    candidate_id: str,
    candidate_class: Any,
    bars_by_symbol: dict[str, list],
    is_start: datetime,
    is_end: datetime,
    oos_start: datetime,
    oos_end: datetime,
) -> list[TradeRecord]:
    """Φ4.1-flavored isolated arm.

    Walks the 8-agent squad on the given window with the candidate's
    reads redacted (RedactedLedger(self_only) wrapping a FullLedger
    that everyone else writes to). Only returns the candidate's
    trades, sliced to the OOS window.
    """
    sub_bars = {
        sym: [b for b in bars if is_start <= b.time < oos_end]
        for sym, bars in bars_by_symbol.items()
    }
    if not any(sub_bars.values()):
        return []

    # Rebuild squad with candidate substituted.
    isagi = A1IsagiV1()
    bachira = candidate_class(agent_id=candidate_id) if candidate_id == "bachira_meguru" else A2BachiraV1()
    rin = candidate_class(agent_id=candidate_id) if candidate_id == "itoshi_rin" else A3RinV1()
    chigiri = candidate_class(agent_id=candidate_id) if candidate_id == "chigiri_hyoma" else A4ChigiriV1()
    reo = candidate_class(agent_id=candidate_id) if candidate_id == "reo_mikage" else A5ReoV1()
    nagi = candidate_class(agent_id=candidate_id) if candidate_id == "nagi_seishiro" else A6NagiV1()
    barou = candidate_class(agent_id=candidate_id) if candidate_id == "barou_shoei" else A7BarouV1()
    kunigami = A10KunigamiV1()

    for sym, bars in sub_bars.items():
        if not bars:
            continue
        for agent in (isagi, bachira, rin, chigiri, barou):
            if hasattr(agent, "prepare") and sym in agent.symbols:
                agent.prepare(sym, bars)
    agents_list = [isagi, bachira, rin, chigiri, reo, nagi, barou, kunigami]

    full_ledger = FullLedger()
    isolated_view = RedactedLedger(agent_id=candidate_id, source=full_ledger)

    out = _drive_squad_replay_with_isolated_candidate(
        agents=agents_list,
        candidate_id=candidate_id,
        full_ledger=full_ledger,
        isolated_ledger=isolated_view,
        bars_by_symbol=sub_bars,
        isagi=isagi,
        barou=barou,
        kunigami=kunigami,
    )
    return [
        t for t in out.trades
        if t.agent_id == candidate_id
        and oos_start <= t.entry_time < oos_end
    ]


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the M001 Φ4.1 expanded-squad gate (8-agent vs Isagi-alone).",
    )
    parser.add_argument(
        "--start", type=_parse_date,
        default=DEFAULT_FULL_START.strftime("%Y-%m-%d"),
    )
    parser.add_argument(
        "--end", type=_parse_date,
        default=DEFAULT_FULL_END.strftime("%Y-%m-%d"),
    )
    parser.add_argument("--out-dir", default=None)
    parser.add_argument(
        "--delta-info-windows", type=int,
        default=DEFAULT_DELTA_INFO_WINDOWS,
        help="How many of the 7 OOS windows to use for F17 (default 3).",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
    )
    start = args.start if isinstance(args.start, datetime) else _parse_date(args.start)
    end = args.end if isinstance(args.end, datetime) else _parse_date(args.end)
    report = run_phi41_gate(
        full_start=start, full_end=end,
        out_dir=args.out_dir,
        delta_info_windows=int(args.delta_info_windows),
    )
    print(
        f"Φ4.1 squad gate verdict: {report.verdict} "
        f"({report.n_trades} trades; squad TQS "
        f"{report.squad_median_oos_window_mean_tqs:.3f} vs Isagi-alone "
        f"{ISAGI_ALONE_MEDIAN_OOS_TQS:.3f}; ratio "
        f"{report.squad_vs_isagi_tqs_ratio:.2f}x; "
        f"Nagi confluence count {report.nagi_fired_count})"
    )
    return 0 if report.verdict in ("PASS", "PARTIAL") else 1


if __name__ == "__main__":
    sys.exit(main())
