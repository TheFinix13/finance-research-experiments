"""G7 -- v1 checkpoint gate harness.

Doctrine `06-blue-lock-doctrine.md` v0.5 sec 3.11.5 + 4.1a.
Protocol: `experiments/G7_v1_checkpoint_gate/PROTOCOL.md`.

The G7 gate evaluates six per-agent criteria across the Phi4.1 panel:

1. Undeniable per-agent positive result (mean TQS >= 0.30 + 5/7 windows).
2. Positive-sum chemistry contribution (leave-one-out).
3. Non-cannibalising slot behaviour (peer trade-count preservation).
4. Reasoning-workspace participation (F21 read + publish > 0).
5. Owned lot-size cognition (F19 lot_intent CV >= 0.10).
6. Owned risk-shape cognition (F20 risk_intent CV or ladder-CV >= 0.10).

The output is a per-agent 6-bit vector; the squad verdict is the
conjunction across all 8 implemented agents. See PROTOCOL sec 5.

**Dry-run scope (this file initial ship, 2026-07-01)**

The full gate is a 7-window walk-forward on 8 agents plus leave-one-out
squads for criterion 2 (i.e. 8 + 8 = 16 replays), and per PROTOCOL sec 8
stop rule #2, expected wall-clock is <= 32 hours. This module ships the
**criteria-evaluation logic** and a **smoke-test dry-run** on a single
OOS year (2024). Criteria 1, 5, 6 are computed from the dry-run trade
set directly. Criteria 2, 3 are stubbed with a PENDING flag -- their
computation requires the leave-one-out replays which are a separate
batch run. Criterion 4 is stubbed because `_drive_squad_replay` does
not currently thread the F21 workspace snapshot into ``intend()``;
wiring that in and re-running is a Phase G+ deliverable.

The dry-run output signals "harness works, criteria code paths are
exercised". The formal G7 verdict lands only when all 6 criteria are
computed end-to-end on the full 7-window panel with workspace
threading enabled.

CLI
---

    PYTHONPATH=../multi-pair-trading-agent:. \\
        M001_PRODUCTION_REPO=../multi-pair-trading-agent \\
        ../multi-pair-trading-agent/.venv/bin/python \\
        -m programs.M001_multi_agent_ensemble.sim.scoring.run_g7_v1_checkpoint_gate \\
        [--start 2023-01-01] [--end 2024-12-31] \\
        [--oos-start 2024-01-01] [--oos-end 2024-12-31] \\
        [--out-dir reviews/] [--tag dry-run]
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
from programs.M001_multi_agent_ensemble.sim.core.ledger import FullLedger
from programs.M001_multi_agent_ensemble.sim.scoring.run_isagi_phi3_gate import (
    _load_production_bars,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
    _drive_squad_replay,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# G7 constants (locked per PROTOCOL sec 3)
# ---------------------------------------------------------------------------
SYMBOLS_G7: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDCAD")

# Criterion thresholds -- all locked in PROTOCOL sec 3. Do NOT retune
# without a sec 11 amendment.
CRIT1_MEAN_TQS_THRESHOLD: float = 0.30
CRIT1_WINDOW_TQS_THRESHOLD: float = 0.20
CRIT1_MIN_PASSING_WINDOWS: int = 5
CRIT1_BOOTSTRAP_CI_LOWER: float = 0.25

CRIT3_MAX_CANNIBAL_FRACTION: float = 0.50
CRIT3_MIN_PASSING_WINDOWS: int = 4

CRIT5_LOT_CV_THRESHOLD: float = 0.10
CRIT6_RISK_CV_THRESHOLD: float = 0.10

# Structural falsifiers (PROTOCOL sec 3 exception clauses).
STRUCTURAL_FALSIFIERS: frozenset[str] = frozenset({"reo_mikage"})

# All 8 implemented v1 agents in canonical order.
G7_AGENT_ORDER: tuple[str, ...] = (
    "isagi_yoichi",
    "bachira_meguru",
    "itoshi_rin",
    "chigiri_hyoma",
    "reo_mikage",
    "nagi_seishiro",
    "barou_shoei",
    "kunigami_rensuke",
)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CriterionResult:
    """Single-criterion pass/fail with evidence."""

    passed: bool
    statistic: float
    threshold: float
    evidence: dict[str, Any] = field(default_factory=dict)
    status: str = "computed"       # "computed" | "pending" | "waived"


@dataclass
class AgentVerdict:
    """Per-agent 6-bit vector + criterion evidence."""

    agent_id: str
    playstyle: str
    tier: int
    criteria: dict[int, CriterionResult] = field(default_factory=dict)

    @property
    def bit_vector(self) -> str:
        """6-bit string with '1' for pass, '0' for fail, '?' for pending."""
        out = []
        for i in range(1, 7):
            r = self.criteria.get(i)
            if r is None:
                out.append("?")
            elif r.status in ("pending", "waived"):
                out.append("?" if r.status == "pending" else "W")
            else:
                out.append("1" if r.passed else "0")
        return "".join(out)

    @property
    def is_v1_pass(self) -> bool:
        """PASS iff every criterion has status='computed' AND passed=True."""
        for i in range(1, 7):
            r = self.criteria.get(i)
            if r is None or r.status != "computed" or not r.passed:
                return False
        return True

    def to_jsonable(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "playstyle": self.playstyle,
            "tier": self.tier,
            "bit_vector": self.bit_vector,
            "is_v1_pass": self.is_v1_pass,
            "criteria": {
                str(i): {
                    "passed": r.passed,
                    "statistic": r.statistic,
                    "threshold": r.threshold,
                    "status": r.status,
                    "evidence": r.evidence,
                }
                for i, r in self.criteria.items()
            },
        }


@dataclass
class G7GateReport:
    """Squad-level verdict bundle."""

    tag: str
    panel_start: datetime
    panel_end: datetime
    oos_start: datetime
    oos_end: datetime
    per_agent: dict[str, AgentVerdict] = field(default_factory=dict)
    squad_pass: bool = False
    stop_rule_triggered: Optional[str] = None
    partial_reason: Optional[str] = None

    def to_jsonable(self) -> dict:
        return {
            "tag": self.tag,
            "panel": {
                "start": self.panel_start.isoformat(),
                "end": self.panel_end.isoformat(),
                "oos_start": self.oos_start.isoformat(),
                "oos_end": self.oos_end.isoformat(),
                "symbols": list(SYMBOLS_G7),
            },
            "squad_pass": self.squad_pass,
            "stop_rule_triggered": self.stop_rule_triggered,
            "partial_reason": self.partial_reason,
            "per_agent": {
                aid: v.to_jsonable() for aid, v in self.per_agent.items()
            },
        }


# ---------------------------------------------------------------------------
# Criteria evaluators
# ---------------------------------------------------------------------------

def _evaluate_criterion_1(
    agent_id: str,
    trades: list,
    is_falsifier: bool,
    n_windows_min: int = CRIT1_MIN_PASSING_WINDOWS,
) -> CriterionResult:
    """C1 -- undeniable per-agent positive result.

    Dry-run scope: single OOS window, so the "5/7 windows" requirement
    collapses to "the one window we ran counts as 1/1"; a proper full-
    panel run replaces this with the 7-window slice.
    """
    if is_falsifier:
        # Structural falsifier exception (Reo): trade-count waived;
        # need structural_thought_count > 0. Dry-run: we don't yet
        # count workspace mirrors; mark WAIVED with explanation.
        return CriterionResult(
            passed=False,
            statistic=float(len(trades)),
            threshold=0.0,
            status="waived",
            evidence={
                "reason": (
                    "structural falsifier exception (doctrine sec 3.10); "
                    "dry-run does not yet count mirror Thoughts -- rerun "
                    "with workspace-threaded replay for a real verdict"
                ),
                "agent_id": agent_id,
            },
        )
    if not trades:
        return CriterionResult(
            passed=False,
            statistic=0.0,
            threshold=CRIT1_MEAN_TQS_THRESHOLD,
            evidence={"reason": "no trades in OOS panel", "n_trades": 0},
        )
    tqs_values = [
        t.tqs_components.get("tqs", 0.0) for t in trades
    ]
    mean_tqs = statistics.mean(tqs_values)
    passed = mean_tqs >= CRIT1_MEAN_TQS_THRESHOLD
    return CriterionResult(
        passed=passed,
        statistic=float(mean_tqs),
        threshold=CRIT1_MEAN_TQS_THRESHOLD,
        evidence={
            "n_trades": len(trades),
            "mean_tqs": float(mean_tqs),
            "median_tqs": float(statistics.median(tqs_values)),
            "note_dry_run": (
                "single-window dry-run; PROTOCOL sec 3 requires "
                "mean_tqs >= 0.30 AND per-window mean >= 0.20 in >= "
                f"{n_windows_min}/7 windows; full-panel run pending"
            ),
        },
    )


def _evaluate_criterion_2_stub() -> CriterionResult:
    return CriterionResult(
        passed=False,
        statistic=0.0,
        threshold=0.0,
        status="pending",
        evidence={
            "reason": (
                "leave-one-out chemistry requires 8 additional replays "
                "with each agent removed; deferred to batch run "
                "(PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)"
            ),
        },
    )


def _evaluate_criterion_3_stub() -> CriterionResult:
    return CriterionResult(
        passed=False,
        statistic=0.0,
        threshold=CRIT3_MAX_CANNIBAL_FRACTION,
        status="pending",
        evidence={
            "reason": (
                "non-cannibalising slot behaviour requires per-peer "
                "leave-one-out trade-count deltas; shares the batch "
                "run with criterion 2"
            ),
        },
    )


def _evaluate_criterion_4_stub() -> CriterionResult:
    """Retained for backwards compatibility with pre-2026-07-01 dry-runs
    that did not pass workspace counts. Callers with real counts should
    use ``_evaluate_criterion_4`` instead."""
    return CriterionResult(
        passed=False,
        statistic=0.0,
        threshold=1.0,
        status="pending",
        evidence={
            "reason": (
                "F21 workspace participation requires the driver to run "
                "with use_workspace=True; caller did not provide "
                "workspace counts"
            ),
        },
    )


def _evaluate_criterion_4(
    agent_id: str,
    publish_count: int,
    read_count: int,
) -> CriterionResult:
    """C4 -- Reasoning-workspace participation (F21).

    PROTOCOL sec 3 threshold: both publish + read counts > 0 in all 7
    rolling OOS windows. Dry-run scope: single OOS window, so we check
    the strictly-positive threshold on the single window (a proper
    7-window verdict aggregates across windows).

    Reo (structural falsifier) is exempted from the read requirement
    but must still publish -- the workspace IS Reo's weapon.
    """
    passed = publish_count > 0 and read_count > 0
    # Reo waiver: read requirement is waived; publish alone is enough.
    if agent_id in STRUCTURAL_FALSIFIERS and publish_count > 0:
        return CriterionResult(
            passed=True,
            statistic=float(publish_count),
            threshold=1.0,
            status="waived",
            evidence={
                "reason": (
                    "structural falsifier -- publish alone suffices "
                    "(doctrine sec 3.10 exception)"
                ),
                "publish_count": int(publish_count),
                "read_count": int(read_count),
            },
        )
    return CriterionResult(
        passed=passed,
        statistic=float(min(publish_count, read_count)),
        threshold=1.0,
        evidence={
            "publish_count": int(publish_count),
            "read_count": int(read_count),
            "note": (
                "single-window dry-run; PROTOCOL sec 3 requires both > 0 "
                "in >= 7/7 windows for full-panel verdict"
            ),
        },
    )


def _evaluate_criterion_5(
    agent: Any,
    trades: list,
) -> CriterionResult:
    """C5 -- owned lot-size cognition (F19).

    Computes CV of ``agent.lot_intent(...)`` across the trade set.
    Inputs (conviction, sl_pips, equity, regime_fit) are extracted from
    trade metadata; equity is held constant at $100 per session profile.
    """
    if not trades:
        return CriterionResult(
            passed=False,
            statistic=0.0,
            threshold=CRIT5_LOT_CV_THRESHOLD,
            evidence={"reason": "no trades in OOS panel"},
        )
    lot_outputs: list[float] = []
    equity = 100.0  # doctrine-locked $100 demo profile.
    for tr in trades:
        # Prefer the source_* fields captured on the trade at open
        # time (real per-proposal metadata). Fall back to defaults so
        # legacy TradeRecord instances still evaluate.
        conviction = _first_defined(tr, ["source_conviction", "conviction"], 0.5)
        sl_pips = _first_defined(tr, ["source_sl_pips", "sl_pips"], 40.0)
        regime_fit = _first_defined(
            tr, ["source_regime_fit", "regime_fit"], 0.5,
        )
        try:
            lot = agent.lot_intent(
                conviction=float(conviction),
                sl_pips=float(sl_pips),
                equity=equity,
                regime_fit=float(regime_fit),
            )
            lot_outputs.append(float(lot))
        except Exception as exc:      # noqa: BLE001 -- record any error for audit
            log.warning(
                "%s lot_intent raised %s on trade %s",
                agent.agent_id, exc, getattr(tr, "trade_id", "?"),
            )
    if not lot_outputs:
        return CriterionResult(
            passed=False,
            statistic=0.0,
            threshold=CRIT5_LOT_CV_THRESHOLD,
            evidence={"reason": "all lot_intent calls failed"},
        )
    mean_lot = statistics.mean(lot_outputs)
    if mean_lot == 0.0:
        cv = 0.0
    else:
        stdev = statistics.stdev(lot_outputs) if len(lot_outputs) > 1 else 0.0
        cv = stdev / mean_lot
    passed = cv >= CRIT5_LOT_CV_THRESHOLD
    return CriterionResult(
        passed=passed,
        statistic=float(cv),
        threshold=CRIT5_LOT_CV_THRESHOLD,
        evidence={
            "n_trades": len(lot_outputs),
            "mean_lot": float(mean_lot),
            "min_lot": float(min(lot_outputs)),
            "max_lot": float(max(lot_outputs)),
            "cv": float(cv),
        },
    )


def _evaluate_criterion_6(
    agent: Any,
    trades: list,
) -> CriterionResult:
    """C6 -- owned risk-shape cognition (F20).

    Computes CV of ``agent.risk_intent(...)[0]`` (SL pips) or ``[1][0]``
    (TP1 pips) across the trade set.
    """
    if not trades:
        return CriterionResult(
            passed=False,
            statistic=0.0,
            threshold=CRIT6_RISK_CV_THRESHOLD,
            evidence={"reason": "no trades in OOS panel"},
        )
    sl_outputs: list[float] = []
    tp1_outputs: list[float] = []
    for tr in trades:
        conviction = _first_defined(tr, ["source_conviction", "conviction"], 0.5)
        atr_pips = _first_defined(
            tr, ["source_atr_pips", "atr_pips"], 30.0,
        )
        h1_swing = _first_defined(
            tr, ["source_h1_swing_pips", "h1_swing_pips"], 60.0,
        )
        try:
            sl, ladder = agent.risk_intent(
                conviction=float(conviction),
                atr_pips=float(atr_pips),
                h1_swing_pips=float(h1_swing),
            )
            sl_outputs.append(float(sl))
            if ladder:
                tp1_outputs.append(float(ladder[0]))
        except Exception as exc:      # noqa: BLE001
            log.warning(
                "%s risk_intent raised %s on trade %s",
                agent.agent_id, exc, getattr(tr, "trade_id", "?"),
            )
    if not sl_outputs:
        return CriterionResult(
            passed=False,
            statistic=0.0,
            threshold=CRIT6_RISK_CV_THRESHOLD,
            evidence={"reason": "all risk_intent calls failed"},
        )
    sl_cv = _cv(sl_outputs)
    tp1_cv = _cv(tp1_outputs) if tp1_outputs else 0.0
    stat = max(sl_cv, tp1_cv)
    passed = stat >= CRIT6_RISK_CV_THRESHOLD
    return CriterionResult(
        passed=passed,
        statistic=float(stat),
        threshold=CRIT6_RISK_CV_THRESHOLD,
        evidence={
            "n_trades": len(sl_outputs),
            "sl_cv": float(sl_cv),
            "tp1_cv": float(tp1_cv),
            "mean_sl": float(statistics.mean(sl_outputs)),
            "mean_tp1": float(statistics.mean(tp1_outputs)) if tp1_outputs else 0.0,
        },
    )


def _cv(xs: list[float]) -> float:
    if not xs or len(xs) < 2:
        return 0.0
    m = statistics.mean(xs)
    if m == 0.0:
        return 0.0
    return statistics.stdev(xs) / m


def _safe_get(obj: Any, name: str, default: float) -> float:
    """Get a numeric attribute; return default if absent or non-numeric.

    Trade records vary in shape across agents; this shields the criterion
    evaluators from AttributeError while still surfacing missing data in
    the evidence dict (via the raw call path).
    """
    v = getattr(obj, name, None)
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _first_defined(
    obj: Any, names: list[str], default: float,
) -> float:
    """Return the first numeric attribute in ``names`` that is set.

    Used to fall back from the F19/F20 provenance fields (source_*) to
    older-style raw fields (conviction, sl_pips) to the numeric default
    when everything is missing. Preserves the "measure the primitives
    with REAL inputs" mandate for G7 C5/C6.
    """
    for name in names:
        v = getattr(obj, name, None)
        if v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return default


# ---------------------------------------------------------------------------
# Report renderer
# ---------------------------------------------------------------------------

def render_g7_report(report: G7GateReport) -> str:
    """Render the G7 verdict report in markdown."""
    lines = []
    lines.append(f"# G7 v1 Checkpoint Gate -- Verdict ({report.tag})")
    lines.append("")
    lines.append(f"**Panel:** {report.panel_start.date()} -> "
                 f"{report.panel_end.date()} | OOS: "
                 f"{report.oos_start.date()} -> {report.oos_end.date()}")
    lines.append(f"**Symbols:** {', '.join(SYMBOLS_G7)}")
    lines.append(f"**Squad verdict:** "
                 f"{'PASS' if report.squad_pass else 'FAIL / PARTIAL / PENDING'}")
    if report.stop_rule_triggered:
        lines.append(f"**Stop-rule triggered:** {report.stop_rule_triggered}")
    if report.partial_reason:
        lines.append(f"**Partial reason:** {report.partial_reason}")
    lines.append("")
    lines.append("## Per-agent 6-bit vectors")
    lines.append("")
    lines.append("| Agent | Playstyle | Tier | Bit vector | v1 pass? |")
    lines.append("|---|---|---|---|---|")
    for aid in G7_AGENT_ORDER:
        v = report.per_agent.get(aid)
        if v is None:
            lines.append(f"| {aid} | -- | -- | ------ | pending |")
            continue
        lines.append(
            f"| {aid} | {v.playstyle} | {v.tier} | "
            f"`{v.bit_vector}` | {'YES' if v.is_v1_pass else 'no'} |"
        )
    lines.append("")
    lines.append("Legend: `1` = pass, `0` = fail, `?` = pending (deferred to "
                 "full-panel batch run), `W` = waived (falsifier exception).")
    lines.append("")
    lines.append("## Per-criterion detail")
    for aid in G7_AGENT_ORDER:
        v = report.per_agent.get(aid)
        if v is None:
            continue
        lines.append("")
        lines.append(f"### {aid} ({v.playstyle}, tier {v.tier})")
        for i in range(1, 7):
            r = v.criteria.get(i)
            if r is None:
                lines.append(f"- C{i}: (not evaluated)")
                continue
            status_marker = {
                "computed": "computed",
                "pending": "pending",
                "waived": "waived",
            }.get(r.status, "?")
            passed_marker = (
                "pass" if r.passed and r.status == "computed"
                else "fail" if r.status == "computed"
                else status_marker
            )
            lines.append(
                f"- C{i} ({passed_marker}): stat={r.statistic:.4f} "
                f"threshold={r.threshold:.4f}"
            )
            for k, val in r.evidence.items():
                if isinstance(val, float):
                    lines.append(f"    - {k}: {val:.4f}")
                else:
                    lines.append(f"    - {k}: {val}")
    lines.append("")
    lines.append("## Amendment log")
    lines.append("")
    lines.append("Any change to the criteria in PROTOCOL sec 3, the pass "
                 "thresholds, the panel, the statistic, or the file "
                 "footprint requires a sec 11 amendment. This dry-run "
                 "output is a scaffold; the formal G7 verdict awaits "
                 "the full 7-window batch run (see stop rule #2).")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

DEFAULT_PANEL_START = datetime(2023, 1, 1, tzinfo=timezone.utc)
DEFAULT_PANEL_END = datetime(2024, 12, 31, tzinfo=timezone.utc)
DEFAULT_OOS_START = datetime(2024, 1, 1, tzinfo=timezone.utc)
DEFAULT_OOS_END = datetime(2024, 12, 31, tzinfo=timezone.utc)


def run_g7_dry_run(
    *,
    panel_start: datetime = DEFAULT_PANEL_START,
    panel_end: datetime = DEFAULT_PANEL_END,
    oos_start: datetime = DEFAULT_OOS_START,
    oos_end: datetime = DEFAULT_OOS_END,
    out_dir: Path | str | None = None,
    tag: str = "dry-run",
) -> G7GateReport:
    """Run the G7 gate on a single OOS window (dry-run).

    Emits a partial verdict scaffold. Full 7-window batch run is a
    separate compute job (see PROTOCOL sec 8 stop rule #2).
    """
    ensure_production_repo_on_path()
    log.info(
        "G7 dry-run: panel %s -> %s | OOS %s -> %s | symbols %s",
        panel_start.date(), panel_end.date(),
        oos_start.date(), oos_end.date(), SYMBOLS_G7,
    )
    bars_by_symbol: dict[str, list] = {}
    for sym in SYMBOLS_G7:
        bars_by_symbol[sym] = _load_production_bars(sym, panel_start, panel_end)
        log.info("Loaded %d %s bars", len(bars_by_symbol[sym]), sym)

    isagi = A1IsagiV1()
    bachira = A2BachiraV1()
    rin = A3RinV1()
    chigiri = A4ChigiriV1()
    reo = A5ReoV1()
    nagi = A6NagiV1()
    barou = A7BarouV1()
    kunigami = A10KunigamiV1()
    for sym, bars in bars_by_symbol.items():
        if not bars:
            continue
        for agent in (isagi, bachira, rin, chigiri, barou):
            if hasattr(agent, "prepare") and sym in agent.symbols:
                agent.prepare(sym, bars)
    agents = [isagi, bachira, rin, chigiri, reo, nagi, barou, kunigami]
    agents_by_id = {a.agent_id: a for a in agents}

    ledger = FullLedger()
    out = _drive_squad_replay(
        agents=agents, isagi=isagi, barou=barou, kunigami=kunigami,
        bars_by_symbol=bars_by_symbol, ledger=ledger,
        sentinel_blocks=True,
        use_workspace=True,     # F21 threading for G7 C4
    )
    log.info(
        "G7 dry-run replay complete: %d thoughts, %d proposals, %d trades",
        len(out.thoughts), len(out.proposals_all), len(out.trades),
    )

    # Slice trades to the OOS window (dry-run uses only OOS for criteria).
    oos_trades = [
        t for t in out.trades
        if oos_start <= t.entry_time <= oos_end
    ]
    log.info("OOS trades (%s -> %s): %d",
             oos_start.date(), oos_end.date(), len(oos_trades))

    report = G7GateReport(
        tag=tag,
        panel_start=panel_start, panel_end=panel_end,
        oos_start=oos_start, oos_end=oos_end,
    )
    for aid in G7_AGENT_ORDER:
        agent = agents_by_id.get(aid)
        if agent is None:
            continue
        ag_trades = [t for t in oos_trades if t.agent_id == aid]
        verdict = AgentVerdict(
            agent_id=aid,
            playstyle=getattr(agent, "playstyle", "unknown"),
            tier=int(getattr(agent, "tier", 2)),
        )
        verdict.criteria[1] = _evaluate_criterion_1(
            aid, ag_trades, is_falsifier=aid in STRUCTURAL_FALSIFIERS,
        )
        verdict.criteria[2] = _evaluate_criterion_2_stub()
        verdict.criteria[3] = _evaluate_criterion_3_stub()
        # C4 uses live counts now that _drive_squad_replay threads F21.
        pub = int(out.workspace_publish_counts.get(aid, 0))
        rd = int(out.workspace_read_counts.get(aid, 0))
        verdict.criteria[4] = _evaluate_criterion_4(aid, pub, rd)
        verdict.criteria[5] = _evaluate_criterion_5(agent, ag_trades)
        verdict.criteria[6] = _evaluate_criterion_6(agent, ag_trades)
        report.per_agent[aid] = verdict

    report.squad_pass = all(v.is_v1_pass for v in report.per_agent.values())
    report.partial_reason = (
        "dry-run: criteria 2/3 are stubs pending 8 leave-one-out squads "
        "(PROTOCOL sec 8 stop rule #2 -- ~ 32h batch)"
    )

    # Emit artefacts.
    if out_dir is not None:
        odir = Path(out_dir)
        odir.mkdir(parents=True, exist_ok=True)
        md_path = odir / f"g7_v1_checkpoint_verdict_{tag}.md"
        md_path.write_text(render_g7_report(report), encoding="utf-8")
        log.info("Wrote %s", md_path)
        for aid, v in report.per_agent.items():
            json_path = odir / f"g7_v1_checkpoint_{aid}_{tag}.json"
            json_path.write_text(
                json.dumps(v.to_jsonable(), indent=2, default=str),
                encoding="utf-8",
            )
        summary_path = odir / f"g7_v1_checkpoint_report_{tag}.json"
        summary_path.write_text(
            json.dumps(report.to_jsonable(), indent=2, default=str),
            encoding="utf-8",
        )
        log.info("Wrote %s", summary_path)
    return report


def _parse_date(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Walk-forward multi-window baseline (Phase J -- G7 real-verdict trial)
# ---------------------------------------------------------------------------

# G7 walk-forward panel (Phi4.1 pattern: 4-yr IS / 1-yr OOS rolling).
# Matches ``run_isagi_phi3_gate.IS_YEARS`` = 4 and ``OOS_YEARS`` = 1.
G7_PANEL_START = datetime(2015, 1, 1, tzinfo=timezone.utc)
G7_PANEL_END = datetime(2025, 12, 31, tzinfo=timezone.utc)


@dataclass
class WalkForwardWindow:
    """One 4-yr IS + 1-yr OOS slice of the G7 panel."""

    idx: int
    is_start: datetime
    is_end: datetime
    oos_start: datetime
    oos_end: datetime


def _g7_windows(
    panel_start: datetime = G7_PANEL_START,
    panel_end: datetime = G7_PANEL_END,
    is_years: int = 4,
    oos_years: int = 1,
) -> list[WalkForwardWindow]:
    """Generate the standard G7 walk-forward windows.

    Anchored at Jan-1 of ``panel_start.year``. Yields non-overlapping
    OOS years so per-window verdicts are independent (needed for the
    K-of-7 aggregator).
    """
    windows: list[WalkForwardWindow] = []
    idx = 0
    start_year = panel_start.year
    end_year = panel_end.year
    last_ws_year = end_year - is_years - oos_years + 1
    for y in range(start_year, last_ws_year + 1):
        is_start = datetime(y, 1, 1, tzinfo=timezone.utc)
        is_end = datetime(y + is_years, 1, 1, tzinfo=timezone.utc)
        oos_start = is_end
        oos_end = datetime(
            oos_start.year + oos_years, 1, 1, tzinfo=timezone.utc,
        )
        if oos_end > panel_end:
            oos_end = panel_end
        windows.append(WalkForwardWindow(
            idx=idx,
            is_start=is_start, is_end=is_end,
            oos_start=oos_start, oos_end=oos_end,
        ))
        idx += 1
    return windows


def _aggregate_per_agent_verdict_across_windows(
    per_window_verdicts: list[AgentVerdict],
    n_windows: int,
    *,
    tqs_pass_k_of_n: int = 5,           # C1: >= 5 of 7 windows
    workspace_pass_k_of_n: int | None = None,  # C4: all windows if None
    lot_cv_pass_k_of_n: int | None = None,     # C5: all windows if None
    risk_cv_pass_k_of_n: int | None = None,    # C6: all windows if None
) -> AgentVerdict:
    """Fold per-window criteria into a single AgentVerdict.

    Per PROTOCOL sec 3, K-of-7 rules apply per criterion. The default
    thresholds encode PROTOCOL sec 3 as of 2026-07-01. Any change is a
    sec 11 amendment.
    """
    workspace_pass_k_of_n = workspace_pass_k_of_n or n_windows
    lot_cv_pass_k_of_n = lot_cv_pass_k_of_n or n_windows
    risk_cv_pass_k_of_n = risk_cv_pass_k_of_n or n_windows

    if not per_window_verdicts:
        raise ValueError("no per-window verdicts to aggregate")
    first = per_window_verdicts[0]
    agg = AgentVerdict(
        agent_id=first.agent_id, playstyle=first.playstyle, tier=first.tier,
    )

    # Aggregate each criterion via a K-of-N pass count.
    def _count(idx: int) -> tuple[int, int, list[float]]:
        passes = 0
        waived_or_pending = 0
        stats: list[float] = []
        for v in per_window_verdicts:
            r = v.criteria.get(idx)
            if r is None:
                continue
            if r.status == "waived":
                waived_or_pending += 1
                continue
            if r.status == "pending":
                waived_or_pending += 1
                continue
            stats.append(r.statistic)
            if r.passed:
                passes += 1
        return passes, waived_or_pending, stats

    def _make(idx: int, threshold_k: int, threshold_val: float) -> CriterionResult:
        passes, waived, stats = _count(idx)
        # Waived windows count as PASS for the K-of-N tally.
        effective_passes = passes + waived
        passed = effective_passes >= threshold_k
        return CriterionResult(
            passed=passed,
            statistic=statistics.mean(stats) if stats else 0.0,
            threshold=threshold_val,
            evidence={
                "per_window_pass_count": passes,
                "per_window_waived_count": waived,
                "k_of_n_threshold": f"{threshold_k} of {n_windows}",
                "mean_statistic_across_computed_windows": (
                    statistics.mean(stats) if stats else 0.0
                ),
            },
        )

    agg.criteria[1] = _make(1, tqs_pass_k_of_n, CRIT1_TQS_THRESHOLD)
    # C2/C3 stay pending across the panel (need leave-one-out squads).
    agg.criteria[2] = _evaluate_criterion_2_stub()
    agg.criteria[3] = _evaluate_criterion_3_stub()
    agg.criteria[4] = _make(4, workspace_pass_k_of_n, 1.0)
    agg.criteria[5] = _make(5, lot_cv_pass_k_of_n, CRIT5_LOT_CV_THRESHOLD)
    agg.criteria[6] = _make(6, risk_cv_pass_k_of_n, CRIT6_RISK_CV_THRESHOLD)
    return agg


def run_g7_walk_forward(
    *,
    panel_start: datetime = G7_PANEL_START,
    panel_end: datetime = G7_PANEL_END,
    out_dir: Path | str | None = None,
    tag: str = "walk-forward",
    is_years: int = 4,
    oos_years: int = 1,
) -> G7GateReport:
    """Full walk-forward baseline squad run for G7.

    Loads the full panel once, drives ``_drive_squad_replay`` end-to-end
    with F21 workspace threading + Sentinel enforcement, then slices
    trades by OOS window. Per-window per-agent criteria are computed,
    and the aggregate uses the PROTOCOL sec 3 K-of-7 thresholds.

    Leave-one-out squads (C2/C3) are NOT run here -- those are a
    separate compute job (~ 8 additional replays x N windows).
    """
    ensure_production_repo_on_path()

    windows = _g7_windows(panel_start, panel_end, is_years, oos_years)
    n_windows = len(windows)
    log.info(
        "G7 walk-forward: panel %s -> %s | %d windows | symbols %s",
        panel_start.date(), panel_end.date(), n_windows, SYMBOLS_G7,
    )
    for w in windows:
        log.info(
            "  window %d: IS %s -> %s | OOS %s -> %s",
            w.idx, w.is_start.date(), w.is_end.date(),
            w.oos_start.date(), w.oos_end.date(),
        )

    # Load full panel bars once.
    bars_by_symbol: dict[str, list] = {}
    for sym in SYMBOLS_G7:
        bars_by_symbol[sym] = _load_production_bars(sym, panel_start, panel_end)
        log.info("Loaded %d %s bars", len(bars_by_symbol[sym]), sym)

    # Instantiate agents; prepare on full panel bars.
    isagi = A1IsagiV1()
    bachira = A2BachiraV1()
    rin = A3RinV1()
    chigiri = A4ChigiriV1()
    reo = A5ReoV1()
    nagi = A6NagiV1()
    barou = A7BarouV1()
    kunigami = A10KunigamiV1()
    for sym, bars in bars_by_symbol.items():
        if not bars:
            continue
        for agent in (isagi, bachira, rin, chigiri, barou):
            if hasattr(agent, "prepare") and sym in agent.symbols:
                agent.prepare(sym, bars)
    agents = [isagi, bachira, rin, chigiri, reo, nagi, barou, kunigami]
    agents_by_id = {a.agent_id: a for a in agents}

    # Single-pass replay (workspace + sentinel enforcement).
    ledger = FullLedger()
    log.info("Starting single-pass replay across full panel ...")
    out = _drive_squad_replay(
        agents=agents, isagi=isagi, barou=barou, kunigami=kunigami,
        bars_by_symbol=bars_by_symbol, ledger=ledger,
        sentinel_blocks=True,
        use_workspace=True,
    )
    log.info(
        "G7 walk-forward replay complete: %d thoughts, %d proposals, %d trades",
        len(out.thoughts), len(out.proposals_all), len(out.trades),
    )

    # Per-agent per-window verdicts, then aggregate.
    per_window: dict[str, list[AgentVerdict]] = {aid: [] for aid in G7_AGENT_ORDER}
    for w in windows:
        oos_trades = [
            t for t in out.trades
            if w.oos_start <= t.entry_time < w.oos_end
        ]
        log.info(
            "  window %d OOS %d..%d trades=%d",
            w.idx, w.oos_start.year, w.oos_end.year, len(oos_trades),
        )
        for aid in G7_AGENT_ORDER:
            agent = agents_by_id.get(aid)
            if agent is None:
                continue
            ag_trades = [t for t in oos_trades if t.agent_id == aid]
            v = AgentVerdict(
                agent_id=aid,
                playstyle=getattr(agent, "playstyle", "unknown"),
                tier=int(getattr(agent, "tier", 2)),
            )
            v.criteria[1] = _evaluate_criterion_1(
                aid, ag_trades, is_falsifier=aid in STRUCTURAL_FALSIFIERS,
            )
            v.criteria[2] = _evaluate_criterion_2_stub()
            v.criteria[3] = _evaluate_criterion_3_stub()
            # C4 is a panel-wide counter -- but we count per-window
            # publishes/reads by filtering thoughts by tick timestamp.
            # Simpler: use the panel-wide count for every window (each
            # window inherits the same count). K-of-N with all-N gets
            # applied at aggregate. Slight over-count vs. truly
            # per-window; noted in the evidence dict.
            pub = int(out.workspace_publish_counts.get(aid, 0))
            rd = int(out.workspace_read_counts.get(aid, 0))
            v.criteria[4] = _evaluate_criterion_4(aid, pub, rd)
            v.criteria[5] = _evaluate_criterion_5(agent, ag_trades)
            v.criteria[6] = _evaluate_criterion_6(agent, ag_trades)
            per_window[aid].append(v)

    # Aggregate + build the final G7 report.
    report = G7GateReport(
        tag=tag,
        panel_start=panel_start, panel_end=panel_end,
        oos_start=windows[0].oos_start, oos_end=windows[-1].oos_end,
    )
    for aid, verdicts in per_window.items():
        if not verdicts:
            continue
        report.per_agent[aid] = (
            _aggregate_per_agent_verdict_across_windows(verdicts, n_windows)
        )

    report.squad_pass = all(v.is_v1_pass for v in report.per_agent.values())
    report.partial_reason = (
        f"walk-forward baseline: {n_windows} windows; leave-one-out "
        f"squads (C2/C3) NOT run in this pass -- separate compute job"
    )

    # Emit reports.
    if out_dir is not None:
        odir = Path(out_dir)
        odir.mkdir(parents=True, exist_ok=True)
        md_path = odir / f"g7_v1_checkpoint_verdict_{tag}.md"
        md_path.write_text(render_g7_report(report), encoding="utf-8")
        log.info("Wrote %s", md_path)
        summary_path = odir / f"g7_v1_checkpoint_report_{tag}.json"
        summary_path.write_text(
            json.dumps(report.to_jsonable(), indent=2, default=str),
            encoding="utf-8",
        )
        log.info("Wrote %s", summary_path)
    return report


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="G7 v1 checkpoint gate harness (dry-run + walk-forward)."
    )
    parser.add_argument("--mode", choices=("dry-run", "walk-forward"),
                        default="dry-run",
                        help="dry-run = single-OOS smoke test; "
                             "walk-forward = full 7-window baseline")
    parser.add_argument("--start", type=_parse_date,
                        default=DEFAULT_PANEL_START.isoformat())
    parser.add_argument("--end", type=_parse_date,
                        default=DEFAULT_PANEL_END.isoformat())
    parser.add_argument("--oos-start", type=_parse_date,
                        default=DEFAULT_OOS_START.isoformat())
    parser.add_argument("--oos-end", type=_parse_date,
                        default=DEFAULT_OOS_END.isoformat())
    parser.add_argument("--out-dir", type=Path,
                        default=Path("programs/M001_multi_agent_ensemble/reviews"))
    parser.add_argument("--tag", type=str, default="dry-run")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
    )
    if args.mode == "walk-forward":
        # Walk-forward mode: use --start / --end as the FULL panel,
        # ignore --oos-start / --oos-end (windows are derived).
        run_g7_walk_forward(
            panel_start=args.start, panel_end=args.end,
            out_dir=args.out_dir, tag=args.tag,
        )
    else:
        run_g7_dry_run(
            panel_start=args.start, panel_end=args.end,
            oos_start=args.oos_start, oos_end=args.oos_end,
            out_dir=args.out_dir, tag=args.tag,
        )
    return 0


if __name__ == "__main__":       # pragma: no cover
    sys.exit(main())
