"""AC.1 sub-arm evaluation over the AC.0-v2 fresh-compute telemetry.

Pre-registration:
    programs/M001_multi_agent_ensemble/experiments/phase_ac_pitch_assignment/
        PROTOCOL.md §5 (AC.1 sub-arm table + C1 threshold)
        AMENDMENT_2026-07-20_ac0_methodology_switch.md §7 (AC.0-v2 outputs)

What this does
--------------

Reads the per-movable AC.0-v2 walk-forward telemetry produced by
``sim/scoring/run_ac0_compute.py`` (each movable widened to all 7 pairs;
Kunigami un-retired only inside his own run) and, for each of the eight
pre-registered AC.1 sub-arms, evaluates the movable agent's G7 §3.11.5
C1 threshold on the sub-arm's ``.symbols`` subset.

C1 threshold (pre-reg §5, unchanged):
    - mean TQS ≥ 0.30 across the sub-arm's OOS windows.
    - per-window mean TQS ≥ 0.20 in at least 5 of 7 rolling OOS windows.
    - bootstrap 95% percentile CI lower bound on mean TQS > 0.25
      (n_boot = 10,000, window-level resample, seed pinned).

FDR budget (pre-reg §6): BH q = 0.10 across the 8 AC.1 sub-arms.
Sub-arms whose telemetry is data-invalid (per amendment §8: zero-trades
on a widened pair for Rin/Kunigami-un-retired, or Kunigami's un-
retirement produced 0 trades across all pairs) are flagged as
"NOT_TESTABLE" and excluded from the BH family — an empty p-value
cannot participate in a Benjamini-Hochberg correction. Excluded sub-
arms are enumerated explicitly in the verdict so the reader can see
which pre-registered hypotheses could not be evaluated.

Methodology note (transparent)
------------------------------

The pre-reg §5 AC.1 language ("Each movable agent runs solo (rest of
squad still present as peer readers, but only the movable agent's
``.symbols`` is changed)") ideally calls for a *per-sub-arm* fresh
walk-forward with the movable's ``.symbols`` widened to the sub-arm's
target pairs and other agents at doctrine defaults. The in-repo
harness (``run_g7_v1_checkpoint_gate.py --symbols``) restricts the
whole PANEL to those symbols and thereby silences every non-widened
agent (their doctrine ``.symbols`` no longer intersect the panel);
``run_ac0_compute.py`` widens the movable to the panel ``--symbols``
and cannot express "widen movable to a subset of the panel". Building
a per-movable-symbol-override harness is out of the resumer session's
write-scope. Instead: the AC.0-v2 fresh compute already widened each
movable to all 7 pairs with other agents at doctrine defaults (exact
AC.1 semantic for the fully-widened case). Per-pair per-window mean-
TQS is pair-local in the aggregator (phi41 scores TQS per-pair from
that pair's trade set), so the sub-arm's per-pair per-window mean-TQS
extracted from AC.0-v2 is a scientifically valid proxy for the sub-
arm's dedicated walk-forward. The one 2nd-order risk is Reo's HRP
copier universe (7 pairs in AC.0-v2 vs sub-arm's narrower set) leaking
into per-pair aggregator dynamics; Reo does not self-propose so the
leakage is bounded to peer-copier mirroring, which is small on non-
overlapping pairs. This methodology decision is recorded in the
verdict verbatim.

Aggregation per sub-arm
-----------------------

For each sub-arm's list of pairs S:
    per_window_mean_tqs[w] =
        sum(pair_mean_tqs[p, w] * n_trades[p, w] for p in S)
        / sum(n_trades[p, w] for p in S)
    n_trades_window[w] = sum(n_trades[p, w] for p in S)

Trade-weighted averaging within a window matches the aggregator's
per-pair scoring: each per-pair per-window mean-TQS is itself an
average over that pair's trades in that window, so the trade-weighted
combination reproduces the mean of the pooled trade set.

Windows with n_trades_window[w] == 0 are dropped from the OOS window
count for the K-of-N check (i.e. counted as neither pass nor fail);
this matches the amendment §8 "zero trades = not a legitimate y = 0
observation" rule extended to the K-of-N evaluation. The pre-reg's
"5 of 7 windows ≥ 0.20" is then applied against the number of
POPULATED windows: if fewer than 5 of 7 windows have any trades on
the sub-arm's pairs, C1 fails the coverage sub-criterion automatically.

Outputs
-------

- ``ac1_<sub-arm>.json`` — machine-readable per-sub-arm verdict.
- ``ac1_verdicts.md`` — narrative table + FDR accounting + methodology note.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import random
import statistics
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pre-registered AC.1 sub-arm table (§5, locked)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SubArm:
    sub_arm_id: str
    agent_id: str
    symbols: tuple[str, ...]
    prereq: str


AC1_SUB_ARMS: tuple[SubArm, ...] = (
    SubArm("AC.1.chi-a", "chigiri_hyoma", ("AUDUSD", "NZDUSD"), "none"),
    SubArm("AC.1.chi-b", "chigiri_hyoma", ("USDJPY",), "cache pull"),
    SubArm("AC.1.chi-c", "chigiri_hyoma", ("GBPUSD",), "none"),
    SubArm("AC.1.rin-a", "itoshi_rin", ("EURUSD", "USDCHF"), "cache pull"),
    SubArm("AC.1.rin-b", "itoshi_rin", ("EURUSD", "USDJPY"), "cache pull"),
    SubArm("AC.1.rin-c", "itoshi_rin", ("USDCHF",), "cache pull"),
    SubArm("AC.1.kun-a", "kunigami_rensuke", ("AUDUSD", "NZDUSD"), "none"),
    SubArm("AC.1.kun-b", "kunigami_rensuke", ("AUDUSD", "NZDUSD", "USDJPY"),
           "cache pull"),
)

# Pre-reg §5 AC.1 C1 thresholds (locked).
C1_MEAN_TQS_THRESHOLD: float = 0.30
C1_WINDOW_TQS_THRESHOLD: float = 0.20
C1_MIN_PASSING_WINDOWS: int = 5
C1_BOOTSTRAP_CI_LOWER: float = 0.25

DEFAULT_N_BOOT: int = 10_000
DEFAULT_SEED: int = 20260720
FDR_Q: float = 0.10          # pre-reg §6


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PerWindowStat:
    window_idx: int
    per_window_mean_tqs: float
    n_trades_window: int
    per_pair_breakdown: list[dict]     # [{symbol, mean_tqs, n_trades}, ...]


@dataclass
class SubArmVerdict:
    sub_arm_id: str
    agent_id: str
    symbols: tuple[str, ...]
    evaluated_pairs: tuple[str, ...]      # subset of `symbols` post §8 filtering
    dropped_pairs: tuple[str, ...]        # widened+zero pairs dropped
    prereq: str
    testable: bool
    not_testable_reason: Optional[str]
    n_populated_windows: int
    total_trades_across_sub_arm: int
    per_window: list[PerWindowStat]
    mean_tqs: Optional[float]
    n_windows_ge_threshold: Optional[int]
    ci_lower: Optional[float]
    ci_upper: Optional[float]
    bootstrap_p_gt_025: Optional[float]
    cond_mean_tqs_met: Optional[bool]
    cond_k_of_n_met: Optional[bool]
    cond_bootstrap_met: Optional[bool]
    c1_pass: Optional[bool]
    telemetry_source: str

    def to_jsonable(self) -> dict:
        return {
            "sub_arm_id": self.sub_arm_id,
            "agent_id": self.agent_id,
            "symbols": list(self.symbols),
            "evaluated_pairs": list(self.evaluated_pairs),
            "dropped_pairs": list(self.dropped_pairs),
            "prereq": self.prereq,
            "testable": bool(self.testable),
            "not_testable_reason": self.not_testable_reason,
            "n_populated_windows": int(self.n_populated_windows),
            "total_trades_across_sub_arm": int(self.total_trades_across_sub_arm),
            "per_window": [
                {
                    "window_idx": int(pw.window_idx),
                    "per_window_mean_tqs": (
                        None if math.isnan(pw.per_window_mean_tqs)
                        else float(pw.per_window_mean_tqs)
                    ),
                    "n_trades_window": int(pw.n_trades_window),
                    "per_pair_breakdown": pw.per_pair_breakdown,
                }
                for pw in self.per_window
            ],
            "c1_evaluation": {
                "thresholds": {
                    "mean_tqs_ge": C1_MEAN_TQS_THRESHOLD,
                    "per_window_ge": C1_WINDOW_TQS_THRESHOLD,
                    "min_passing_windows": C1_MIN_PASSING_WINDOWS,
                    "bootstrap_ci_lower_gt": C1_BOOTSTRAP_CI_LOWER,
                },
                "observed": {
                    "mean_tqs": (
                        None if self.mean_tqs is None else float(self.mean_tqs)
                    ),
                    "n_windows_ge_020": (
                        None if self.n_windows_ge_threshold is None
                        else int(self.n_windows_ge_threshold)
                    ),
                    "bootstrap_ci_lower": (
                        None if self.ci_lower is None else float(self.ci_lower)
                    ),
                    "bootstrap_ci_upper": (
                        None if self.ci_upper is None else float(self.ci_upper)
                    ),
                    "bootstrap_p_mean_tqs_gt_025": (
                        None if self.bootstrap_p_gt_025 is None
                        else float(self.bootstrap_p_gt_025)
                    ),
                },
                "sub_criteria": {
                    "mean_tqs_met": self.cond_mean_tqs_met,
                    "k_of_n_met": self.cond_k_of_n_met,
                    "bootstrap_met": self.cond_bootstrap_met,
                },
                "c1_pass": self.c1_pass,
            },
            "telemetry_source": self.telemetry_source,
        }


# ---------------------------------------------------------------------------
# Telemetry loading
# ---------------------------------------------------------------------------

def load_movable_telemetry(
    telemetry_dir: Path,
    agent_ids: tuple[str, ...],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for aid in agent_ids:
        p = telemetry_dir / f"{aid}_walkforward.json"
        if not p.exists():
            log.warning("AC.1: missing telemetry for %s at %s", aid, p)
            continue
        out[aid] = json.loads(p.read_text())
    return out


def _detect_kunigami_wiring_broken(payload: dict[str, Any]) -> bool:
    """Amendment §8: Kunigami un-retired that emits 0 trades on ANY of the
    newly-widened pairs (AUDUSD, NZDUSD, USDJPY, USDCHF) → data problem.
    In the AC.0-v2 fresh compute we observed 0 trades on ALL pairs including
    his home pairs; that's a broken un-retirement wiring, not a signal.
    """
    if payload.get("agent_id") != "kunigami_rensuke":
        return False
    return int(payload.get("n_trades_movable", 0)) == 0


# ---------------------------------------------------------------------------
# Bootstrap on window-level means
# ---------------------------------------------------------------------------

def _bootstrap_window_mean(
    per_window_means: list[float],
    *,
    n_boot: int = DEFAULT_N_BOOT,
    seed: int = DEFAULT_SEED,
    alpha: float = 0.05,
) -> tuple[float, float, list[float]]:
    """Percentile bootstrap on the mean of a set of per-window means.

    Returns (ci_lower, ci_upper, all_bootstrap_means).
    Window-level resample (pre-reg §6: bootstrap unit = OOS window, K=7
    rolling, not individual trades). Seed pinned per §6 for
    reproducibility.
    """
    rng = random.Random(seed)
    n = len(per_window_means)
    if n == 0:
        return (float("nan"), float("nan"), [])
    boots: list[float] = []
    for _ in range(n_boot):
        sample = [
            per_window_means[rng.randrange(n)] for _ in range(n)
        ]
        boots.append(statistics.mean(sample))
    boots.sort()
    lo = boots[int(alpha / 2 * len(boots))]
    hi = boots[int((1 - alpha / 2) * len(boots))]
    return (lo, hi, boots)


# ---------------------------------------------------------------------------
# Sub-arm evaluation
# ---------------------------------------------------------------------------

def _extract_per_pair_window_map(
    payload: dict[str, Any],
) -> dict[tuple[str, int], tuple[float, int]]:
    """{(symbol, window_idx): (mean_tqs, n_trades)}"""
    out: dict[tuple[str, int], tuple[float, int]] = {}
    for s in payload.get("per_pair_window_stats") or []:
        key = (str(s["symbol"]), int(s["window_idx"]))
        out[key] = (float(s.get("mean_tqs", 0.0) or 0.0),
                    int(s.get("n_trades", 0) or 0))
    return out


def _evaluate_sub_arm(
    sub_arm: SubArm,
    telemetry: dict[str, dict[str, Any]],
    *,
    n_boot: int = DEFAULT_N_BOOT,
    seed: int = DEFAULT_SEED,
) -> SubArmVerdict:
    payload = telemetry.get(sub_arm.agent_id)
    telemetry_source = (
        f"{sub_arm.agent_id}_walkforward.json"
        if payload is not None else "MISSING"
    )

    # NOT_TESTABLE gates (data problems per amendment §8).
    if payload is None:
        return SubArmVerdict(
            sub_arm_id=sub_arm.sub_arm_id, agent_id=sub_arm.agent_id,
            symbols=sub_arm.symbols,
            evaluated_pairs=(), dropped_pairs=sub_arm.symbols,
            prereq=sub_arm.prereq,
            testable=False,
            not_testable_reason=(
                f"AC.0-v2 telemetry for {sub_arm.agent_id} missing at "
                f"{sub_arm.agent_id}_walkforward.json"
            ),
            n_populated_windows=0, total_trades_across_sub_arm=0,
            per_window=[],
            mean_tqs=None, n_windows_ge_threshold=None,
            ci_lower=None, ci_upper=None, bootstrap_p_gt_025=None,
            cond_mean_tqs_met=None, cond_k_of_n_met=None,
            cond_bootstrap_met=None, c1_pass=None,
            telemetry_source=telemetry_source,
        )

    kun_broken = _detect_kunigami_wiring_broken(payload)
    if sub_arm.agent_id == "kunigami_rensuke" and kun_broken:
        return SubArmVerdict(
            sub_arm_id=sub_arm.sub_arm_id, agent_id=sub_arm.agent_id,
            symbols=sub_arm.symbols,
            evaluated_pairs=(), dropped_pairs=sub_arm.symbols,
            prereq=sub_arm.prereq,
            testable=False,
            not_testable_reason=(
                "amendment §8 sentinel: Kunigami un-retired produced 0 "
                "trades across ALL 7 pairs (49 pair-windows) in the "
                "AC.0-v2 fresh compute — un-retirement wiring failed "
                "silently. Cannot legitimately be counted as y = 0 "
                "observations for AC.1. Fix required: investigate "
                "Kunigami proposer-wiring in run_ac0_compute._build_movable_roster"
            ),
            n_populated_windows=0, total_trades_across_sub_arm=0,
            per_window=[],
            mean_tqs=None, n_windows_ge_threshold=None,
            ci_lower=None, ci_upper=None, bootstrap_p_gt_025=None,
            cond_mean_tqs_met=None, cond_k_of_n_met=None,
            cond_bootstrap_met=None, c1_pass=None,
            telemetry_source=telemetry_source,
        )

    # Amendment §8: check whether any of the sub-arm's WIDENED pairs
    # (i.e. pairs NOT in the movable's v1 doctrine defaults) produced
    # zero trades across all windows. That is a data problem, not a
    # signal → the sub-arm becomes NOT_TESTABLE.
    # v1 doctrine defaults (from Phase AC PROTOCOL §3):
    v1_defaults = {
        "chigiri_hyoma": ("EURUSD", "GBPUSD"),
        "itoshi_rin": ("EURUSD",),
        "kunigami_rensuke": ("EURUSD", "GBPUSD", "USDCAD"),
    }
    defaults = set(v1_defaults.get(sub_arm.agent_id, ()))
    per_pair_window = _extract_per_pair_window_map(payload)
    windows_meta = payload.get("windows") or []
    n_windows = len(windows_meta) or 7  # G7 default

    # Per-widened-pair zero-trades sentinel (only fires for non-Chigiri
    # per amendment §8 wording; Chigiri exempt on GBPUSD but not on
    # other newly-widened pairs like USDJPY). We apply the sentinel to
    # all three movables here (stricter reading per resumer prompt
    # rule 4) — a widened pair with zero trades in every window is a
    # data problem for the movable, not a legitimate zero signal.
    widened_pairs_in_arm = [p for p in sub_arm.symbols if p not in defaults]
    zero_widened_pairs: list[str] = []
    for p in widened_pairs_in_arm:
        total_p_trades = sum(
            per_pair_window.get((p, w), (0.0, 0))[1]
            for w in range(n_windows)
        )
        if total_p_trades == 0:
            zero_widened_pairs.append(p)

    if zero_widened_pairs and len(zero_widened_pairs) == len(sub_arm.symbols):
        # Every symbol in the sub-arm is a widened-and-zero pair →
        # the sub-arm cannot even be reduced to a legitimate v1-default
        # slice.
        return SubArmVerdict(
            sub_arm_id=sub_arm.sub_arm_id, agent_id=sub_arm.agent_id,
            symbols=sub_arm.symbols,
            evaluated_pairs=(), dropped_pairs=tuple(zero_widened_pairs),
            prereq=sub_arm.prereq,
            testable=False,
            not_testable_reason=(
                f"amendment §8 sentinel: all symbols in this sub-arm "
                f"({', '.join(sub_arm.symbols)}) are newly-widened for "
                f"{sub_arm.agent_id} (v1 defaults = "
                f"{sorted(defaults) or '(none)'}) and produced 0 trades "
                f"in every OOS window in the AC.0-v2 fresh compute. "
                "This is a data/logic problem for the movable on those "
                "pairs, not a legitimate y = 0 signal — cannot enter "
                "the C1 test."
            ),
            n_populated_windows=0, total_trades_across_sub_arm=0,
            per_window=[],
            mean_tqs=None, n_windows_ge_threshold=None,
            ci_lower=None, ci_upper=None, bootstrap_p_gt_025=None,
            cond_mean_tqs_met=None, cond_k_of_n_met=None,
            cond_bootstrap_met=None, c1_pass=None,
            telemetry_source=telemetry_source,
        )

    # Effective evaluation pairs = sub-arm pairs minus any zero-trades
    # widened pairs (they get dropped as per amendment §8; the sub-arm
    # runs on the remaining pairs and any effective reduction is
    # recorded).
    eval_pairs = [p for p in sub_arm.symbols if p not in zero_widened_pairs]
    if not eval_pairs:
        # Should already be caught above, but keep the defensive branch.
        return SubArmVerdict(
            sub_arm_id=sub_arm.sub_arm_id, agent_id=sub_arm.agent_id,
            symbols=sub_arm.symbols,
            evaluated_pairs=(), dropped_pairs=tuple(zero_widened_pairs),
            prereq=sub_arm.prereq,
            testable=False,
            not_testable_reason=(
                "sub-arm collapsed to empty pair set after amendment §8 "
                "zero-trades sentinel — no usable data"
            ),
            n_populated_windows=0, total_trades_across_sub_arm=0,
            per_window=[],
            mean_tqs=None, n_windows_ge_threshold=None,
            ci_lower=None, ci_upper=None, bootstrap_p_gt_025=None,
            cond_mean_tqs_met=None, cond_k_of_n_met=None,
            cond_bootstrap_met=None, c1_pass=None,
            telemetry_source=telemetry_source,
        )

    # Trade-weighted per-window mean-TQS.
    per_window_stats: list[PerWindowStat] = []
    per_window_means_for_bootstrap: list[float] = []
    total_trades = 0
    for w in range(n_windows):
        pair_rows = []
        weighted_sum = 0.0
        n_win = 0
        for p in eval_pairs:
            mean_tqs, n_tr = per_pair_window.get((p, w), (0.0, 0))
            pair_rows.append({
                "symbol": p,
                "mean_tqs": float(mean_tqs),
                "n_trades": int(n_tr),
            })
            weighted_sum += mean_tqs * n_tr
            n_win += n_tr
        if n_win > 0:
            pw_mean = weighted_sum / n_win
            per_window_means_for_bootstrap.append(pw_mean)
        else:
            pw_mean = float("nan")
        total_trades += n_win
        per_window_stats.append(PerWindowStat(
            window_idx=w,
            per_window_mean_tqs=pw_mean,
            n_trades_window=n_win,
            per_pair_breakdown=pair_rows,
        ))

    n_populated = len(per_window_means_for_bootstrap)
    if n_populated == 0:
        return SubArmVerdict(
            sub_arm_id=sub_arm.sub_arm_id, agent_id=sub_arm.agent_id,
            symbols=sub_arm.symbols,
            evaluated_pairs=tuple(eval_pairs),
            dropped_pairs=tuple(zero_widened_pairs),
            prereq=sub_arm.prereq,
            testable=False,
            not_testable_reason=(
                "no OOS windows had any trades on the sub-arm's pairs "
                "after amendment §8 filtering — cannot compute C1"
            ),
            n_populated_windows=0, total_trades_across_sub_arm=total_trades,
            per_window=per_window_stats,
            mean_tqs=None, n_windows_ge_threshold=None,
            ci_lower=None, ci_upper=None, bootstrap_p_gt_025=None,
            cond_mean_tqs_met=None, cond_k_of_n_met=None,
            cond_bootstrap_met=None, c1_pass=None,
            telemetry_source=telemetry_source,
        )

    mean_tqs = statistics.mean(per_window_means_for_bootstrap)
    n_windows_ge = sum(
        1 for m in per_window_means_for_bootstrap
        if m >= C1_WINDOW_TQS_THRESHOLD
    )
    ci_lo, ci_hi, boots = _bootstrap_window_mean(
        per_window_means_for_bootstrap,
        n_boot=n_boot, seed=seed,
    )
    # One-sided bootstrap p-value for H0: mean TQS ≤ 0.25.
    n_boot_actual = len(boots) or 1
    boots_le_025 = sum(1 for b in boots if b <= C1_BOOTSTRAP_CI_LOWER)
    p_gt_025 = boots_le_025 / n_boot_actual

    cond_mean_tqs = mean_tqs >= C1_MEAN_TQS_THRESHOLD
    # K-of-N: at least 5 of the ORIGINAL 7 windows must clear ≥ 0.20.
    # An unpopulated window cannot pass the threshold → counts as fail.
    cond_k_of_n = n_windows_ge >= C1_MIN_PASSING_WINDOWS
    cond_bootstrap = ci_lo > C1_BOOTSTRAP_CI_LOWER
    c1_pass = cond_mean_tqs and cond_k_of_n and cond_bootstrap

    return SubArmVerdict(
        sub_arm_id=sub_arm.sub_arm_id, agent_id=sub_arm.agent_id,
        symbols=sub_arm.symbols,
        evaluated_pairs=tuple(eval_pairs),
        dropped_pairs=tuple(zero_widened_pairs),
        prereq=sub_arm.prereq,
        testable=True,
        not_testable_reason=None,
        n_populated_windows=n_populated,
        total_trades_across_sub_arm=total_trades,
        per_window=per_window_stats,
        mean_tqs=float(mean_tqs),
        n_windows_ge_threshold=int(n_windows_ge),
        ci_lower=float(ci_lo),
        ci_upper=float(ci_hi),
        bootstrap_p_gt_025=float(p_gt_025),
        cond_mean_tqs_met=bool(cond_mean_tqs),
        cond_k_of_n_met=bool(cond_k_of_n),
        cond_bootstrap_met=bool(cond_bootstrap),
        c1_pass=bool(c1_pass),
        telemetry_source=telemetry_source,
    )


# ---------------------------------------------------------------------------
# BH FDR adjustment
# ---------------------------------------------------------------------------

def _bh_fdr(
    p_values: list[tuple[str, float]], q: float,
) -> dict[str, dict[str, Any]]:
    """Benjamini-Hochberg FDR control at level q.

    Input: [(sub_arm_id, p_value), ...] for TESTABLE sub-arms only.
    Returns {sub_arm_id: {rank, threshold, reject}}. Not-testable
    sub-arms are excluded upstream (no p-value to combine).
    """
    if not p_values:
        return {}
    ordered = sorted(p_values, key=lambda x: x[1])
    m = len(ordered)
    out: dict[str, dict[str, Any]] = {}
    max_reject_rank = -1
    for i, (sid, p) in enumerate(ordered, start=1):
        thresh = (i / m) * q
        if p <= thresh:
            max_reject_rank = i
    for i, (sid, p) in enumerate(ordered, start=1):
        thresh = (i / m) * q
        reject = i <= max_reject_rank
        out[sid] = {
            "rank": int(i),
            "family_size": int(m),
            "raw_p": float(p),
            "bh_threshold": float(thresh),
            "reject_at_q": bool(reject),
        }
    return out


# ---------------------------------------------------------------------------
# Verdict rendering
# ---------------------------------------------------------------------------

def _render_verdict_md(
    verdicts: list[SubArmVerdict],
    fdr: dict[str, dict[str, Any]],
    telemetry_dir: str,
    n_boot: int,
    seed: int,
    fired_at: str,
    fdr_q: float,
) -> str:
    lines: list[str] = []
    lines.append("# Phase AC — AC.1 sub-arm verdicts (C1 on AC.0-v2 telemetry)")
    lines.append("")
    lines.append(f"- **Fired:** {fired_at}")
    lines.append(f"- **Telemetry source:** `{telemetry_dir}`")
    lines.append(
        f"- **Bootstrap:** n = {n_boot}, seed = {seed}, "
        "window-level resample (§6)"
    )
    lines.append(
        f"- **FDR budget:** BH q = {fdr_q} across TESTABLE sub-arms only. "
        "NOT_TESTABLE sub-arms (amendment §8 sentinels) are enumerated "
        "below and excluded from the BH family (no p-value)."
    )
    lines.append("")
    lines.append("## 1. Methodology note (transparent)")
    lines.append("")
    lines.append(
        "The AC.0-v2 fresh compute widened each movable agent to all 7 "
        "pairs with other agents at doctrine defaults — the exact per-"
        "reg §5 AC.1 semantic for the fully-widened case. Sub-arm "
        "evaluation extracts the sub-arm's pair subset from that "
        "per-pair per-window mean-TQS grid rather than firing a fresh "
        "walk-forward per sub-arm, because (a) `run_g7_v1_checkpoint_gate.py "
        "--symbols` restricts the whole PANEL and silences non-widened "
        "agents whose doctrine `.symbols` fall outside the panel — "
        "not the AC.1 semantic; (b) `run_ac0_compute.py` widens the "
        "movable to the panel `--symbols` and cannot express \"widen "
        "movable to a subset of the panel\" — also not the AC.1 "
        "semantic; (c) building a per-movable-symbol-override harness "
        "is outside this resumer session's write-scope; (d) per-pair "
        "per-window mean-TQS is pair-local under phi41's per-pair TQS "
        "scoring, so extracting the sub-arm's pair subset from the "
        "widest-panel telemetry is a scientifically valid proxy for a "
        "narrower-panel run modulo a bounded 2nd-order effect via "
        "Reo's HRP copier universe."
    )
    lines.append("")
    lines.append("## 2. Sub-arm summary table")
    lines.append("")
    lines.append(
        "| Sub-arm | Agent | Nominal `.symbols` | Evaluated | §8-dropped | "
        "Populated wins | Trades | Mean TQS | K/7 ≥ 0.20 | 95% CI lower | "
        "C1 pass? | BH reject? |"
    )
    lines.append(
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---|---|"
    )
    for v in verdicts:
        if not v.testable:
            lines.append(
                f"| **{v.sub_arm_id}** | `{v.agent_id}` | "
                f"{', '.join(v.symbols)} | "
                f"{', '.join(v.evaluated_pairs) or '—'} | "
                f"{', '.join(v.dropped_pairs) or '—'} | "
                "— | — | — | — | — | **NOT_TESTABLE** | — |"
            )
            continue
        fdr_entry = fdr.get(v.sub_arm_id, {})
        bh_marker = (
            "yes" if fdr_entry.get("reject_at_q") else
            ("no" if "reject_at_q" in fdr_entry else "—")
        )
        c1_marker = (
            "**YES**" if v.c1_pass else "no"
        )
        lines.append(
            f"| {v.sub_arm_id} | `{v.agent_id}` | "
            f"{', '.join(v.symbols)} | "
            f"{', '.join(v.evaluated_pairs) or '—'} | "
            f"{', '.join(v.dropped_pairs) or '—'} | "
            f"{v.n_populated_windows}/7 | "
            f"{v.total_trades_across_sub_arm} | "
            f"{'—' if v.mean_tqs is None else f'{v.mean_tqs:.3f}'} | "
            f"{'—' if v.n_windows_ge_threshold is None else f'{v.n_windows_ge_threshold}/7'} | "
            f"{'—' if v.ci_lower is None else f'{v.ci_lower:.3f}'} | "
            f"{c1_marker} | {bh_marker} |"
        )
    lines.append("")

    # NOT_TESTABLE details
    not_testable = [v for v in verdicts if not v.testable]
    if not_testable:
        lines.append("## 3. NOT_TESTABLE sub-arms (amendment §8 sentinels)")
        lines.append("")
        for v in not_testable:
            lines.append(f"### {v.sub_arm_id} — `{v.agent_id}` on {', '.join(v.symbols)}")
            lines.append("")
            lines.append(f"- **Reason:** {v.not_testable_reason}")
            lines.append("")

    # TESTABLE per-sub-arm detail
    testable = [v for v in verdicts if v.testable]
    if testable:
        lines.append("## 4. Testable sub-arm detail")
        lines.append("")
        for v in testable:
            lines.append(f"### {v.sub_arm_id} — `{v.agent_id}` on {', '.join(v.symbols)}")
            lines.append("")
            lines.append(f"- **Populated windows:** {v.n_populated_windows}/7")
            lines.append(f"- **Total trades in sub-arm:** {v.total_trades_across_sub_arm}")
            lines.append(f"- **Mean TQS (across populated windows):** "
                         f"{v.mean_tqs:.4f}  (≥ 0.30? {'YES' if v.cond_mean_tqs_met else 'no'})")
            lines.append(f"- **K-of-7 windows ≥ 0.20:** "
                         f"{v.n_windows_ge_threshold}/7  (≥ 5? "
                         f"{'YES' if v.cond_k_of_n_met else 'no'})")
            lines.append(f"- **Bootstrap 95% CI on mean TQS:** "
                         f"[{v.ci_lower:.4f}, {v.ci_upper:.4f}]  "
                         f"(lower > 0.25? "
                         f"{'YES' if v.cond_bootstrap_met else 'no'})")
            lines.append(f"- **Bootstrap one-sided p(mean_TQS ≤ 0.25):** "
                         f"{v.bootstrap_p_gt_025:.6f}")
            lines.append(f"- **C1 pass?** "
                         f"{'**YES**' if v.c1_pass else 'no (need all 3 sub-criteria met)'}")
            fdr_entry = fdr.get(v.sub_arm_id, {})
            if fdr_entry:
                lines.append(
                    f"- **BH FDR (q = {fdr_q}):** rank "
                    f"{fdr_entry['rank']}/{fdr_entry['family_size']}, "
                    f"threshold = {fdr_entry['bh_threshold']:.4f}, "
                    f"raw p = {fdr_entry['raw_p']:.6f}, "
                    f"reject H0 at q = {fdr_q}: "
                    f"{'YES' if fdr_entry['reject_at_q'] else 'no'}"
                )
            lines.append("")
            lines.append("Per-window (trade-weighted across sub-arm pairs):")
            lines.append("")
            lines.append(
                "| Window | mean TQS | n trades | breakdown |"
            )
            lines.append(
                "|---:|---:|---:|---|"
            )
            for pw in v.per_window:
                bd = ", ".join(
                    f"{r['symbol']} ({r['mean_tqs']:.3f}, n={r['n_trades']})"
                    for r in pw.per_pair_breakdown
                )
                mean_s = (
                    "— (0 trades)" if pw.n_trades_window == 0
                    else f"{pw.per_window_mean_tqs:.3f}"
                )
                lines.append(
                    f"| {pw.window_idx} | {mean_s} | "
                    f"{pw.n_trades_window} | {bd} |"
                )
            lines.append("")

    # Aggregate PASS count
    n_pass = sum(1 for v in verdicts if v.c1_pass)
    n_testable = sum(1 for v in verdicts if v.testable)
    n_bh_reject = sum(
        1 for sid, ent in fdr.items() if ent.get("reject_at_q")
    )
    lines.append("## 5. Aggregate")
    lines.append("")
    lines.append(f"- **Sub-arms testable:** {n_testable} of {len(verdicts)}")
    lines.append(f"- **Sub-arms passing C1 (all 3 sub-criteria):** {n_pass}")
    lines.append(
        f"- **Sub-arms BH-rejected at q = {fdr_q} (i.e. C1 pass survives "
        f"multi-test correction):** {n_bh_reject}"
    )
    lines.append("")

    # Passing pitch sets per agent — STRICT reading: use evaluated_pairs
    # (post amendment §8 filtering), not nominal sub_arm.symbols. A
    # sub-arm whose §8-dropped pair means the eval reduced to a v1-
    # default subset produces NO widening authorization even if the
    # reduced eval passes C1.
    lines.append("## 6. Passing pitch sets per movable (STRICT: evaluated pairs only)")
    lines.append("")
    lines.append(
        "The pre-reg §5 says the 'passing pitch set' is the union of "
        "`.symbols` across passing sub-arms. Applying that literally to "
        "sub-arms where amendment §8 dropped a widened pair from the "
        "eval would credit the drop-victim pair for a pass it never "
        "demonstrated. STRICT reading: only credit `evaluated_pairs` "
        "(i.e. the pairs that actually contributed trades to the "
        "eval) toward the passing pitch set. Widenings that never "
        "produced a trade cannot be authorised by a pass that didn't "
        "measure them."
    )
    lines.append("")
    per_agent_evaluated: dict[str, set[str]] = {}
    reduced_notes: list[str] = []
    for v in verdicts:
        if v.c1_pass and fdr.get(v.sub_arm_id, {}).get("reject_at_q"):
            per_agent_evaluated.setdefault(v.agent_id, set()).update(
                v.evaluated_pairs
            )
            if v.dropped_pairs:
                reduced_notes.append(
                    f"- {v.sub_arm_id}: nominal `.symbols` = "
                    f"{list(v.symbols)}; §8 dropped "
                    f"{list(v.dropped_pairs)}; evaluated on "
                    f"{list(v.evaluated_pairs)}. Pass CREDITS ONLY "
                    f"{list(v.evaluated_pairs)}."
                )
    if per_agent_evaluated:
        for aid, pitches in per_agent_evaluated.items():
            v1_defaults = {
                "chigiri_hyoma": ("EURUSD", "GBPUSD"),
                "itoshi_rin": ("EURUSD",),
                "kunigami_rensuke": ("EURUSD", "GBPUSD", "USDCAD"),
            }.get(aid, ())
            defaults_set = set(v1_defaults)
            union = defaults_set | pitches
            new_pitches = pitches - defaults_set
            lines.append(
                f"- **`{aid}`** v1 defaults: `{sorted(defaults_set)}`; "
                f"AC.1 evaluated-pairs union: `{sorted(pitches)}`; "
                f"**newly authorised widening pitches: "
                f"`{sorted(new_pitches) if new_pitches else '(none)'}`**; "
                f"UNION `.symbols` for AC.2: `{sorted(union)}`."
            )
    else:
        lines.append(
            "(no sub-arm passed BH-adjusted C1 → no widening authorised)"
        )
    if reduced_notes:
        lines.append("")
        lines.append("§8-reduced sub-arm crediting:")
        lines.append("")
        for n in reduced_notes:
            lines.append(n)
    lines.append("")

    # Verdict — STRICT: does any movable earn a NEW pitch (beyond v1
    # defaults) via a sub-arm that both raw-C1-passes and BH-rejects?
    v1_defaults_map = {
        "chigiri_hyoma": {"EURUSD", "GBPUSD"},
        "itoshi_rin": {"EURUSD"},
        "kunigami_rensuke": {"EURUSD", "GBPUSD", "USDCAD"},
    }
    any_new_widening = False
    for aid, pitches in per_agent_evaluated.items():
        if pitches - v1_defaults_map.get(aid, set()):
            any_new_widening = True
            break

    lines.append("## 7. Verdict")
    lines.append("")
    if not any_new_widening:
        if n_bh_reject == 0:
            lines.append(
                "**AC.1 FAILS.** No sub-arm passed the pre-registered "
                "C1 threshold after BH FDR correction at q = 0.10. Per "
                "PROTOCOL §5 AC.1, this means no movable agent earned "
                "a passing pitch set beyond its v1 defaults. AC.2 "
                "squad-composition arms are NOT authorised to fire "
                "(per §12 sequencing, AC.2 requires ≥1 AC.1 sub-arm "
                "pass per movable, or the movable stays at canon "
                "home — with all movables staying at canon home, "
                "A2/B1 arms collapse to A1 baseline)."
            )
        else:
            lines.append(
                f"**AC.1 FAILS on the widening question.** "
                f"{n_bh_reject} sub-arm(s) BH-rejected H0 raw, and "
                f"{sum(1 for v in verdicts if v.c1_pass)} sub-arm(s) "
                "passed all three C1 sub-criteria, but under the STRICT "
                "reading of amendment §8 (drop widened-and-zero pairs "
                "from the eval; credit only evaluated pairs), every "
                "post-drop passing sub-arm reduced to a v1-default "
                "pair set — i.e. re-confirming home pitches, not "
                "authorising new widenings. AC.2 A2/B1 arms are NOT "
                "authorised to fire because the only widenings "
                "expressible in AC.2's roster construction are the "
                "'newly authorised widening pitches' listed in §6, "
                "and that list is empty for every movable."
            )
    else:
        lines.append(
            f"**AC.1 PASSES on the widening question** — at least one "
            "movable earned a new authorised pitch beyond its v1 "
            f"defaults ({n_bh_reject} sub-arm(s) survived BH FDR at "
            f"q = 0.10). Passing pitch sets recorded above (§6) "
            "authorise the corresponding movable-agent widenings for "
            "AC.2 A2 / B1 arm construction per PROTOCOL §5.1 UNION "
            "semantic."
        )
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_ac1(
    *,
    telemetry_dir: Path | str,
    out_dir: Path | str,
    n_boot: int = DEFAULT_N_BOOT,
    seed: int = DEFAULT_SEED,
    fdr_q: float = FDR_Q,
) -> list[SubArmVerdict]:
    telemetry_dir = Path(telemetry_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    agent_ids = tuple(sorted({sa.agent_id for sa in AC1_SUB_ARMS}))
    telemetry = load_movable_telemetry(telemetry_dir, agent_ids)

    verdicts: list[SubArmVerdict] = []
    for sa in AC1_SUB_ARMS:
        v = _evaluate_sub_arm(sa, telemetry, n_boot=n_boot, seed=seed)
        verdicts.append(v)
        jpath = out_dir / f"ac1_{sa.sub_arm_id.replace('.', '_')}.json"
        jpath.write_text(
            json.dumps(v.to_jsonable(), indent=2, default=str),
            encoding="utf-8",
        )
        log.info(
            "AC.1 %s: testable=%s c1_pass=%s mean_tqs=%s",
            sa.sub_arm_id, v.testable, v.c1_pass,
            "N/A" if v.mean_tqs is None else f"{v.mean_tqs:.4f}",
        )

    # BH FDR on TESTABLE sub-arms only.
    testable_p = [
        (v.sub_arm_id, v.bootstrap_p_gt_025)
        for v in verdicts
        if v.testable and v.bootstrap_p_gt_025 is not None
    ]
    fdr = _bh_fdr(testable_p, fdr_q)

    md = _render_verdict_md(
        verdicts, fdr,
        telemetry_dir=str(telemetry_dir),
        n_boot=n_boot, seed=seed,
        fired_at=datetime.now(timezone.utc).isoformat(),
        fdr_q=fdr_q,
    )
    verdict_md = out_dir / "ac1_verdicts.md"
    verdict_md.write_text(md, encoding="utf-8")
    log.info("AC.1: wrote %s", verdict_md)

    # Summary JSON alongside.
    summary_path = out_dir / "ac1_verdicts_summary.json"
    summary_path.write_text(
        json.dumps({
            "fired_at_utc": datetime.now(timezone.utc).isoformat(),
            "telemetry_dir": str(telemetry_dir),
            "n_boot": int(n_boot),
            "rng_seed": int(seed),
            "fdr_q": float(fdr_q),
            "sub_arms": [v.to_jsonable() for v in verdicts],
            "bh_fdr": fdr,
            "n_pass_c1": sum(1 for v in verdicts if v.c1_pass),
            "n_bh_reject": sum(
                1 for sid, ent in fdr.items() if ent.get("reject_at_q")
            ),
            "n_testable": sum(1 for v in verdicts if v.testable),
        }, indent=2, default=str),
        encoding="utf-8",
    )
    log.info("AC.1: wrote %s", summary_path)
    return verdicts


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="AC.1 sub-arm evaluation over AC.0-v2 fresh-compute telemetry.",
    )
    parser.add_argument("--telemetry-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--n-boot", type=int, default=DEFAULT_N_BOOT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--fdr-q", type=float, default=FDR_Q)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
    )
    verdicts = evaluate_ac1(
        telemetry_dir=args.telemetry_dir,
        out_dir=args.out_dir,
        n_boot=args.n_boot, seed=args.seed, fdr_q=args.fdr_q,
    )
    n_pass = sum(1 for v in verdicts if v.c1_pass)
    n_testable = sum(1 for v in verdicts if v.testable)
    print(
        f"[AC.1] === {n_pass} of {n_testable} testable sub-arms PASS "
        f"C1 (raw); BH FDR applied in ac1_verdicts.md ==="
    )
    return 0


if __name__ == "__main__":       # pragma: no cover
    sys.exit(main())
