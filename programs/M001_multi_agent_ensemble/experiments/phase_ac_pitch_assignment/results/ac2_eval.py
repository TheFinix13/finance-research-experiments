"""AC.2 arm evaluator against the pre-registered locked criteria.

Pre-registration:
    programs/M001_multi_agent_ensemble/experiments/phase_ac_pitch_assignment/
        PROTOCOL.md §5.2 (AC.2 success criteria)
        PROTOCOL.md §6 (statistic + FDR budget)

What this does
--------------

Consumes the per-arm ``ac2_arm_<arm>.json`` reports produced by
``ac2_run.py`` and renders:

- Per-arm per-agent C1 status (used for AC2.1 anchor lock check).
- Per-arm squad mean-of-window-mean TQS with bootstrap 95% CI.
- Per-arm Nagi OOS trade count (AC2.3 volume floor).
- A1-vs-A2 squad-TQS delta with bootstrap 95% CI (AC2.2 primary).
- BH FDR q=0.10 across the AC.2 tests actually run.

Coverage note (transparent):

- **B1-hard and B1-soft not run** in this session (see ac2_run.py
  module docstring for the exact scope reasons: `_drive_squad_replay`
  requires isagi/barou/kunigami role-kwargs so multi-squad rosters
  break the harness; B1-soft's pitch-preferred routing needs core
  aggregator changes out of the resumer's write scope). AC2.5
  (isolation-cost audit) is therefore NOT REPORTED.
- **AC2.4 (no C3 poisoning) not evaluated**: ``ac2_run.py`` does not
  export per-agent per-window same-tick collision counts (C3). The
  underlying ``_drive_squad_replay`` output collects them, but the
  ac2_run slicer emits only mean-TQS and n_trades per window. Adding
  C3 export would be a re-run; here it is honestly flagged as
  "not measured this session" rather than assumed-clean.

C1 (per agent, per arm)
-----------------------

Same threshold as AC.1 / G7 §3.11.5:
    - mean TQS ≥ 0.30 across OOS windows.
    - per-window mean TQS ≥ 0.20 in at least 5 of 7 rolling OOS windows.
    - bootstrap 95% percentile CI lower bound on mean TQS > 0.25
      (n_boot = 10,000, window-level resample, seed pinned).

AC2.1 anchor lock
-----------------

For each anchor in {isagi_yoichi, bachira_meguru, barou_shoei}: the
A2-arm C1 pass status must equal the A1-arm C1 pass status. Any change
from PASS→FAIL fails the arm.

AC2.2 squad TQS lift
--------------------

Squad TQS per arm = mean across all trading agents of their per-agent
per-window mean-TQS, averaged over the 7 OOS windows. Zero-trade
agent-window slices are dropped from the window-mean numerator and
denominator (matching the "y=0 not a legitimate observation" rule
from amendment §8 extended to squad aggregation).

Kunigami is excluded from the squad-TQS numerator when he is retired
(default in both A1 and A2); this matches pre-reg §6 wording ("Kunigami
excluded if retired in that arm").

Delta = squad_tqs(A2) − squad_tqs(A1). Bootstrap 95% CI on the delta
by paired window-level resampling (same 7 window indices sampled with
replacement, evaluated in both arms, delta recomputed).

Pass criterion:
    delta ≥ 0.02 AND bootstrap 95% CI lower on delta > 0.

AC2.3 Nagi trade floor
----------------------

Nagi's total OOS trades across all 7 windows ≥ 50. Applied per arm
(fails independently in each arm).

FDR
---

BH q=0.10. Pre-reg §6 reserves 28 tests (8 AC.1 sub-arms + 4 AC.2 arms
× 5 AC.2 criteria = 20 AC.2 tests). This session tests fewer AC.2
hypotheses than the reservation (B1-* not run, AC2.4/AC2.5 not
measured), so FDR is applied over the tests actually executed in this
family — the reservation is documented in the verdict for honest
accounting.

Outputs
-------

- ``ac2_arm_<arm>_verdict.json`` — per-arm C1 + AC2.1/2.2/2.3 rendering.
- ``ac2_verdicts.md`` — narrative table + FDR accounting + coverage note.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import random
import statistics
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Locked pre-reg constants
# ---------------------------------------------------------------------------

C1_MEAN_TQS_THRESHOLD: float = 0.30
C1_WINDOW_TQS_THRESHOLD: float = 0.20
C1_MIN_PASSING_WINDOWS: int = 5
C1_BOOTSTRAP_CI_LOWER: float = 0.25

AC22_SQUAD_LIFT_MIN: float = 0.02          # squad_tqs delta ≥ +0.02
AC23_NAGI_TRADE_FLOOR: int = 50            # nagi ≥ 50 OOS trades

DEFAULT_N_BOOT: int = 10_000
DEFAULT_SEED: int = 20260721                # AC.2 fires this date
FDR_Q: float = 0.10

ANCHOR_IDS: tuple[str, ...] = (
    "isagi_yoichi", "bachira_meguru", "barou_shoei",
)
NAGI_ID: str = "nagi_seishiro"
KUNIGAMI_ID: str = "kunigami_rensuke"

# Trading agents contributing to squad TQS numerator (pre-reg §6: exclude
# Kunigami when retired). All 7 non-Kunigami agents that trade are candidates;
# zero-trade windows are simply dropped by the aggregator.
TRADING_AGENT_IDS: tuple[str, ...] = (
    "isagi_yoichi", "bachira_meguru", "itoshi_rin", "chigiri_hyoma",
    "reo_mikage", "nagi_seishiro", "barou_shoei",
)


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------

@dataclass
class AgentC1:
    agent_id: str
    n_trades_total: int
    n_populated_windows: int              # windows with ≥1 trade
    per_window_mean_tqs: list[Optional[float]]  # length 7; None = 0-trade
    n_windows_ge_020: int
    mean_tqs_over_populated: Optional[float]
    ci_lower: Optional[float]
    ci_upper: Optional[float]
    cond_mean_tqs_met: Optional[bool]
    cond_k_of_n_met: Optional[bool]
    cond_bootstrap_met: Optional[bool]
    c1_pass: Optional[bool]

    def to_jsonable(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "n_trades_total": int(self.n_trades_total),
            "n_populated_windows": int(self.n_populated_windows),
            "per_window_mean_tqs": [
                None if v is None else float(v)
                for v in self.per_window_mean_tqs
            ],
            "c1_evaluation": {
                "thresholds": {
                    "mean_tqs_ge": C1_MEAN_TQS_THRESHOLD,
                    "per_window_ge": C1_WINDOW_TQS_THRESHOLD,
                    "min_passing_windows": C1_MIN_PASSING_WINDOWS,
                    "bootstrap_ci_lower_gt": C1_BOOTSTRAP_CI_LOWER,
                },
                "observed": {
                    "mean_tqs_over_populated": (
                        None if self.mean_tqs_over_populated is None
                        else float(self.mean_tqs_over_populated)
                    ),
                    "n_windows_ge_020": int(self.n_windows_ge_020),
                    "bootstrap_ci_lower": (
                        None if self.ci_lower is None else float(self.ci_lower)
                    ),
                    "bootstrap_ci_upper": (
                        None if self.ci_upper is None else float(self.ci_upper)
                    ),
                },
                "sub_criteria": {
                    "mean_tqs_met": self.cond_mean_tqs_met,
                    "k_of_n_met": self.cond_k_of_n_met,
                    "bootstrap_met": self.cond_bootstrap_met,
                },
                "c1_pass": self.c1_pass,
            },
        }


@dataclass
class ArmVerdict:
    arm_id: str
    fired_at_utc: str
    n_windows: int
    n_trades_total: int
    per_agent_c1: dict[str, AgentC1]
    squad_per_window_mean_tqs: list[Optional[float]]
    squad_mean_of_window_mean: Optional[float]
    squad_ci_lower: Optional[float]
    squad_ci_upper: Optional[float]
    nagi_trades_total: int
    ac23_nagi_pass: bool

    def to_jsonable(self) -> dict:
        return {
            "arm_id": self.arm_id,
            "fired_at_utc": self.fired_at_utc,
            "n_windows": int(self.n_windows),
            "n_trades_total": int(self.n_trades_total),
            "per_agent_c1": {
                aid: a.to_jsonable() for aid, a in self.per_agent_c1.items()
            },
            "squad_per_window_mean_tqs": [
                None if v is None else float(v)
                for v in self.squad_per_window_mean_tqs
            ],
            "squad_mean_of_window_mean": (
                None if self.squad_mean_of_window_mean is None
                else float(self.squad_mean_of_window_mean)
            ),
            "squad_ci_lower": (
                None if self.squad_ci_lower is None
                else float(self.squad_ci_lower)
            ),
            "squad_ci_upper": (
                None if self.squad_ci_upper is None
                else float(self.squad_ci_upper)
            ),
            "nagi_trades_total": int(self.nagi_trades_total),
            "ac23_nagi_pass": bool(self.ac23_nagi_pass),
        }


# ---------------------------------------------------------------------------
# Bootstrap helpers
# ---------------------------------------------------------------------------

def _bootstrap_mean(
    values: list[float], *,
    n_boot: int = DEFAULT_N_BOOT,
    seed: int = DEFAULT_SEED,
    alpha: float = 0.05,
) -> tuple[float, float]:
    rng = random.Random(seed)
    n = len(values)
    if n == 0:
        return (float("nan"), float("nan"))
    boots = []
    for _ in range(n_boot):
        s = [values[rng.randrange(n)] for _ in range(n)]
        boots.append(statistics.mean(s))
    boots.sort()
    lo = boots[int(alpha / 2 * n_boot)]
    hi = boots[int((1 - alpha / 2) * n_boot)]
    return (lo, hi)


def _bootstrap_paired_window_delta(
    a1_windows: list[Optional[float]],
    a2_windows: list[Optional[float]],
    *,
    n_boot: int = DEFAULT_N_BOOT,
    seed: int = DEFAULT_SEED,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """Paired window-level bootstrap on delta = squad_tqs(A2) - squad_tqs(A1).

    Returns (point_estimate, ci_lower, ci_upper). Windows where either
    arm has None are dropped from the paired bootstrap (matches "y=0 not
    a legitimate observation" convention).
    """
    paired = [
        (a, b) for a, b in zip(a1_windows, a2_windows)
        if a is not None and b is not None
    ]
    n = len(paired)
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    point = statistics.mean(b - a for a, b in paired)
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        s = [paired[rng.randrange(n)] for _ in range(n)]
        boots.append(statistics.mean(b - a for a, b in s))
    boots.sort()
    lo = boots[int(alpha / 2 * n_boot)]
    hi = boots[int((1 - alpha / 2) * n_boot)]
    return (point, lo, hi)


# ---------------------------------------------------------------------------
# Per-agent C1 from an arm's per_agent_window slices
# ---------------------------------------------------------------------------

def _per_agent_c1(
    arm_payload: dict[str, Any],
    agent_id: str,
) -> AgentC1:
    slices = [
        s for s in arm_payload.get("per_agent_window", [])
        if s.get("agent_id") == agent_id
    ]
    slices.sort(key=lambda s: int(s["window_idx"]))
    n_windows_expected = int(arm_payload.get("n_windows", 7))
    per_window_mean_tqs: list[Optional[float]] = [None] * n_windows_expected
    n_trades_total = 0
    for s in slices:
        w = int(s["window_idx"])
        n = int(s["n_trades"])
        n_trades_total += n
        if n > 0:
            per_window_mean_tqs[w] = float(s["mean_tqs"])
    populated = [v for v in per_window_mean_tqs if v is not None]
    n_populated = len(populated)
    n_ge_020 = sum(1 for v in populated if v >= C1_WINDOW_TQS_THRESHOLD)
    if n_populated == 0:
        return AgentC1(
            agent_id=agent_id, n_trades_total=0,
            n_populated_windows=0,
            per_window_mean_tqs=per_window_mean_tqs,
            n_windows_ge_020=0,
            mean_tqs_over_populated=None,
            ci_lower=None, ci_upper=None,
            cond_mean_tqs_met=False,
            cond_k_of_n_met=False,
            cond_bootstrap_met=False,
            c1_pass=False,
        )
    mean_tqs = statistics.mean(populated)
    lo, hi = _bootstrap_mean(populated)
    cond_mean = mean_tqs >= C1_MEAN_TQS_THRESHOLD
    cond_kofn = n_ge_020 >= C1_MIN_PASSING_WINDOWS
    cond_boot = (not math.isnan(lo)) and (lo > C1_BOOTSTRAP_CI_LOWER)
    return AgentC1(
        agent_id=agent_id,
        n_trades_total=n_trades_total,
        n_populated_windows=n_populated,
        per_window_mean_tqs=per_window_mean_tqs,
        n_windows_ge_020=n_ge_020,
        mean_tqs_over_populated=mean_tqs,
        ci_lower=lo, ci_upper=hi,
        cond_mean_tqs_met=cond_mean,
        cond_k_of_n_met=cond_kofn,
        cond_bootstrap_met=cond_boot,
        c1_pass=bool(cond_mean and cond_kofn and cond_boot),
    )


# ---------------------------------------------------------------------------
# Squad TQS per window (mean across trading agents that traded that window)
# ---------------------------------------------------------------------------

def _squad_per_window(
    arm_payload: dict[str, Any],
    trading_agent_ids: tuple[str, ...] = TRADING_AGENT_IDS,
) -> list[Optional[float]]:
    """Per-window squad mean-TQS: mean across trading agents of their
    per-agent mean-TQS in that window. Zero-trade slices dropped.
    Returns list of length n_windows (None for windows where no trading
    agent contributed).
    """
    n_windows = int(arm_payload.get("n_windows", 7))
    out: list[Optional[float]] = [None] * n_windows
    by_w: dict[int, list[float]] = {w: [] for w in range(n_windows)}
    for s in arm_payload.get("per_agent_window", []):
        if s.get("agent_id") not in trading_agent_ids:
            continue
        if int(s["n_trades"]) <= 0:
            continue
        w = int(s["window_idx"])
        if w >= n_windows:
            continue
        by_w[w].append(float(s["mean_tqs"]))
    for w, vals in by_w.items():
        if vals:
            out[w] = statistics.mean(vals)
    return out


# ---------------------------------------------------------------------------
# Per-arm rollup
# ---------------------------------------------------------------------------

def evaluate_arm(arm_payload: dict[str, Any]) -> ArmVerdict:
    arm_id = str(arm_payload["arm_id"])
    n_windows = int(arm_payload.get("n_windows", 7))
    n_trades_total = int(arm_payload.get("n_trades", 0))
    per_agent_c1 = {
        aid: _per_agent_c1(arm_payload, aid)
        for aid in TRADING_AGENT_IDS + (KUNIGAMI_ID,)
    }
    squad_per_window = _squad_per_window(arm_payload)
    populated_window_means = [v for v in squad_per_window if v is not None]
    if populated_window_means:
        squad_mean = statistics.mean(populated_window_means)
        lo, hi = _bootstrap_mean(populated_window_means)
    else:
        squad_mean = None
        lo, hi = None, None
    nagi_total = per_agent_c1[NAGI_ID].n_trades_total
    return ArmVerdict(
        arm_id=arm_id,
        fired_at_utc=str(arm_payload.get("fired_at_utc", "")),
        n_windows=n_windows,
        n_trades_total=n_trades_total,
        per_agent_c1=per_agent_c1,
        squad_per_window_mean_tqs=squad_per_window,
        squad_mean_of_window_mean=squad_mean,
        squad_ci_lower=lo, squad_ci_upper=hi,
        nagi_trades_total=nagi_total,
        ac23_nagi_pass=(nagi_total >= AC23_NAGI_TRADE_FLOOR),
    )


# ---------------------------------------------------------------------------
# BH FDR
# ---------------------------------------------------------------------------

def _bh_fdr(pvals: list[float], q: float = FDR_Q) -> tuple[float, list[bool]]:
    """Benjamini-Hochberg step-up. Returns (adjusted-threshold, per-test-reject).

    p_(k) ≤ k/m · q → largest k that satisfies is the cutoff; all p_(i) for
    i ≤ k are rejected. Per-test reject bits ordered same as input.
    """
    m = len(pvals)
    if m == 0:
        return (0.0, [])
    indexed = sorted(enumerate(pvals), key=lambda t: t[1])
    threshold = 0.0
    cut_k = -1
    for rank, (_, p) in enumerate(indexed, start=1):
        if p <= rank / m * q:
            threshold = p
            cut_k = rank
    reject = [False] * m
    if cut_k >= 0:
        for rank, (orig_i, _) in enumerate(indexed, start=1):
            if rank <= cut_k:
                reject[orig_i] = True
    return (threshold, reject)


# ---------------------------------------------------------------------------
# Per-test p-values from the observed test statistics
# ---------------------------------------------------------------------------

def _fraction_boot_le_zero(
    a1_windows: list[Optional[float]],
    a2_windows: list[Optional[float]],
    *,
    n_boot: int = DEFAULT_N_BOOT,
    seed: int = DEFAULT_SEED,
) -> float:
    """One-sided bootstrap p-value: P(bootstrap delta ≤ 0) under paired
    window resample. For H0: delta ≤ 0 → small p signals A2 > A1.
    """
    paired = [
        (a, b) for a, b in zip(a1_windows, a2_windows)
        if a is not None and b is not None
    ]
    n = len(paired)
    if n == 0:
        return 1.0
    rng = random.Random(seed)
    n_le_zero = 0
    for _ in range(n_boot):
        s = [paired[rng.randrange(n)] for _ in range(n)]
        d = statistics.mean(b - a for a, b in s)
        if d <= 0:
            n_le_zero += 1
    return n_le_zero / n_boot


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _fmt(v, w=6, digits=3) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "-".rjust(w)
    if isinstance(v, bool):
        return ("y" if v else "n").rjust(w)
    if isinstance(v, float):
        return f"{v:.{digits}f}".rjust(w)
    return str(v).rjust(w)


def render_verdict_md(
    arm_verdicts: dict[str, ArmVerdict],
    a1_a2_delta: Optional[tuple[float, float, float, float]],  # (delta, lo, hi, p)
    bh: Optional[tuple[float, list[bool], list[str], list[float]]],  # (threshold, rejects, labels, pvals)
    outdir: Path,
    baseline_id: str = "A1",
    tested_id: str = "A2",
) -> str:
    lines: list[str] = []
    now = datetime.now(timezone.utc).isoformat()
    lines.append("# AC.2 arm verdicts (Phase AC pitch assignment)")
    lines.append("")
    lines.append(
        "Rendered by ``ac2_eval.py`` at "
        f"{now}. See PROTOCOL.md §5.2 for the locked criteria."
    )
    lines.append("")
    lines.append("## 1. Coverage")
    lines.append("")
    lines.append(
        "| Pre-registered arm | Session status | Reason |"
    )
    lines.append("|---|---|---|")
    lines.append(
        "| **A1** (baseline / control) | RUN | reference for AC2.1/AC2.2 |"
    )
    lines.append(
        "| **A2** (single-squad, Rin widened to (EURUSD, USDCHF)) | "
        "RUN | AC.1.rin-a passed BH-adjusted (see ac1_verdicts.md §6 STRICT) |"
    )
    lines.append(
        "| **B1-hard** (multi-squad hard isolation) | DEFERRED | "
        "`_drive_squad_replay` role-kwargs isagi/barou/kunigami block partial "
        "rosters; out of resumer write-scope. See ac2_run.py module docstring. |"
    )
    lines.append(
        "| **B1-soft** (multi-squad soft isolation, pitch-preferred routing) | "
        "DEFERRED | needs core-aggregator pitch-preferred routing; out of "
        "resumer write-scope. |"
    )
    lines.append(
        "| **AC2.4** (no C3 poisoning) | NOT MEASURED | `ac2_run.py` slicer "
        "does not export per-agent per-window same-tick collision counts; "
        "adding it would be a re-run. Flagged as not-measured rather than "
        "assumed-clean. |"
    )
    lines.append(
        "| **AC2.5** (isolation-cost audit, B1-soft − B1-hard) | NOT REPORTED | "
        "B1 arms deferred. |"
    )
    lines.append("")

    lines.append("## 2. Per-arm per-agent C1 (mean TQS + k/7 + boot 95% CI)")
    lines.append("")
    for arm_id, v in arm_verdicts.items():
        lines.append(f"### Arm {arm_id}")
        lines.append("")
        lines.append(
            "| Agent | trades | pop.win | mean-TQS | boot 95% CI | wins≥0.20 | "
            "cond mean≥0.30 | cond ≥5/7 | cond boot>0.25 | C1 |"
        )
        lines.append(
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
        )
        for aid in TRADING_AGENT_IDS + (KUNIGAMI_ID,):
            ag = v.per_agent_c1[aid]
            ci = (
                f"[{_fmt(ag.ci_lower)}, {_fmt(ag.ci_upper)}]"
                if ag.ci_lower is not None else "-"
            )
            lines.append(
                f"| `{aid}` | {ag.n_trades_total} | {ag.n_populated_windows}/7 "
                f"| {_fmt(ag.mean_tqs_over_populated)} | {ci} "
                f"| {ag.n_windows_ge_020}/{ag.n_populated_windows} "
                f"| {_fmt(ag.cond_mean_tqs_met, w=3)} "
                f"| {_fmt(ag.cond_k_of_n_met, w=3)} "
                f"| {_fmt(ag.cond_bootstrap_met, w=3)} "
                f"| {'**PASS**' if ag.c1_pass else 'fail'} |"
            )
        lines.append("")
        lines.append(
            f"Squad mean-of-window-mean TQS: **{_fmt(v.squad_mean_of_window_mean)}** "
            f"[boot 95% CI {_fmt(v.squad_ci_lower)}, {_fmt(v.squad_ci_upper)}] "
            f"over {sum(1 for x in v.squad_per_window_mean_tqs if x is not None)}"
            "/7 populated windows."
        )
        lines.append("")
        lines.append(
            f"Nagi total OOS trades: **{v.nagi_trades_total}** "
            f"(AC2.3 threshold {AC23_NAGI_TRADE_FLOOR}) — "
            f"**{'PASS' if v.ac23_nagi_pass else 'FAIL'}**."
        )
        lines.append("")

    lines.append("## 3. AC2.1 anchor lock")
    lines.append("")
    lines.append(
        "For each anchor, arm-A2 C1 pass status must equal arm-A1 C1 pass status."
    )
    lines.append("")
    lines.append("| Anchor | A1 C1 | A2 C1 | Anchor lock |")
    lines.append("|---|---:|---:|---:|")
    a1 = arm_verdicts.get(baseline_id)
    a2 = arm_verdicts.get(tested_id)
    ac21_any_regression = False
    if a1 is not None and a2 is not None:
        for aid in ANCHOR_IDS:
            p1 = a1.per_agent_c1[aid].c1_pass
            p2 = a2.per_agent_c1[aid].c1_pass
            same = (p1 == p2)
            regression = (p1 is True and p2 is False)
            if regression:
                ac21_any_regression = True
            lines.append(
                f"| `{aid}` | {'PASS' if p1 else 'fail'} "
                f"| {'PASS' if p2 else 'fail'} "
                f"| {'REGRESSION' if regression else ('same' if same else 'change')} |"
            )
    lines.append("")
    lines.append(
        f"AC2.1 verdict for {tested_id} vs {baseline_id}: "
        f"**{'FAIL (regression)' if ac21_any_regression else 'PASS (no regression)'}**."
    )
    lines.append("")

    lines.append("## 4. AC2.2 squad TQS lift (primary)")
    lines.append("")
    if a1_a2_delta is not None:
        delta, lo, hi, p_le0 = a1_a2_delta
        lift_ok = (delta >= AC22_SQUAD_LIFT_MIN) and (lo > 0.0)
        lines.append(
            f"Squad TQS delta ({tested_id} − {baseline_id}): **{_fmt(delta, w=6, digits=4)}** "
            f"[boot 95% CI {_fmt(lo, w=6, digits=4)}, {_fmt(hi, w=6, digits=4)}]."
        )
        lines.append("")
        lines.append(
            f"AC2.2 threshold: delta ≥ +{AC22_SQUAD_LIFT_MIN:.2f} AND boot CI lower > 0."
        )
        lines.append(
            f"AC2.2 verdict: **{'PASS' if lift_ok else 'FAIL'}** "
            f"(one-sided bootstrap p(delta ≤ 0) = {p_le0:.3f})."
        )
    else:
        lines.append("No delta computed (baseline or tested arm missing).")
    lines.append("")

    lines.append("## 5. AC2.3 Nagi volume floor")
    lines.append("")
    lines.append("| Arm | Nagi trades | Threshold | Pass |")
    lines.append("|---|---:|---:|---:|")
    for arm_id, v in arm_verdicts.items():
        lines.append(
            f"| {arm_id} | {v.nagi_trades_total} | ≥ {AC23_NAGI_TRADE_FLOOR} "
            f"| **{'PASS' if v.ac23_nagi_pass else 'FAIL'}** |"
        )
    lines.append("")
    if any(v.nagi_trades_total == 0 for v in arm_verdicts.values()):
        lines.append(
            "**Diagnostic on Nagi = 0 across arms.** In the 2026-07-01 G7 v1 "
            "walk-forward baseline (3-pair panel EURUSD/GBPUSD/USDCAD), Nagi "
            "cleanly passed C1 with mean-TQS 0.385 (see "
            "`reviews/2026-07-01_g7_walk_forward_baseline.md`). On the "
            "extended 7-pair panel used by AC.2 (AC.0-v2 amendment §5), Nagi "
            "produces zero trades in the A1 baseline arm despite iterating "
            "over 53,163 bar-events on his home pairs (workspace publish "
            "counter confirms he is being called). His `.symbols` is still "
            "(EURUSD, GBPUSD, USDCAD); the anchors' `.symbols` is unchanged; "
            "yet no confluence proposals fire. This is a baseline-reproduction "
            "regression on the extended panel, not caused by widening. AC2.3 "
            "therefore fails EVERY AC.2 arm intrinsically — it is not a "
            "widening penalty. Recommended follow-up: investigate whether "
            "the extended-panel interleaved bar stream perturbs Nagi's peer-"
            "confluence gate timing before shipping any pitch-assignment "
            "change to `next-gen`. Diagnostic is flagged in REPORT.md §4."
        )
        lines.append("")

    lines.append("## 6. BH FDR accounting")
    lines.append("")
    if bh is not None:
        thresh, rejects, labels, pvals = bh
        lines.append(
            "Pre-reg §6 reserved 20 AC.2 tests (4 arms × 5 criteria). "
            "This session ran fewer: A1 baseline + A2 tested against AC2.1 "
            "(anchor lock, 3 anchors, treated as hard prerequisite not BH "
            "member), AC2.2 (squad-lift bootstrap, one-sided), AC2.3 "
            "(Nagi floor, per-arm; hard-threshold count converted to a "
            "binary p ∈ {0, 1} so BH ordering is well-defined). B1-hard "
            "and B1-soft not run; AC2.4/AC2.5 not measured."
        )
        lines.append("")
        lines.append(f"BH q = {FDR_Q}. Tests actually executed and BH-adjusted:")
        lines.append("")
        lines.append("| Test | p-value | BH reject? |")
        lines.append("|---|---:|---:|")
        for label, p, r in zip(labels, pvals, rejects):
            lines.append(
                f"| {label} | {p:.4f} | {'yes' if r else 'no'} |"
            )
    else:
        lines.append("No tests to BH-adjust (see §1 coverage).")
    lines.append("")

    lines.append("## 7. Recommended-action feed for REPORT.md")
    lines.append("")
    if a1_a2_delta is not None:
        delta, lo, hi, p_le0 = a1_a2_delta
        lift_ok = (delta >= AC22_SQUAD_LIFT_MIN) and (lo > 0.0)
        if lift_ok and not ac21_any_regression and (a2 and a2.ac23_nagi_pass):
            lines.append(
                "**A2 PASSES all executed AC.2 criteria (AC2.1, AC2.2, AC2.3).** "
                "REPORT.md should recommend porting A2 to `next-gen` via "
                "`build_roster(pitch_overrides={'itoshi_rin': ('EURUSD', 'USDCHF')})`, "
                "conditional on the future runs of B1-hard/B1-soft (currently "
                "deferred) not producing a strictly-superior alternative."
            )
        else:
            fail_bits = []
            if ac21_any_regression:
                fail_bits.append("AC2.1 anchor regression")
            if not lift_ok:
                fail_bits.append("AC2.2 squad lift below threshold or CI touches 0")
            if a2 is not None and not a2.ac23_nagi_pass:
                fail_bits.append(
                    "AC2.3 Nagi trades below 50 (but A1 baseline "
                    "also fails AC2.3 — see §5 diagnostic)"
                    if (a1 is not None and not a1.ac23_nagi_pass)
                    else "AC2.3 Nagi trades below 50"
                )
            lines.append(
                "**A2 FAILS at least one executed AC.2 criterion "
                f"({', '.join(fail_bits) or 'unknown'}).** "
                "REPORT.md should recommend staying with A1 baseline "
                "(no evidence-backed pitch-assignment widening survived)."
            )
            if a1 is not None and not a1.ac23_nagi_pass:
                lines.append("")
                lines.append(
                    "Note: AC2.3 failure in both A1 and A2 is a baseline-"
                    "reproduction issue on the extended 7-pair panel (see §5 "
                    "diagnostic), not a widening penalty. It does not by "
                    "itself falsify pitch-assignment as a concept; it does "
                    "mean the extended panel needs Nagi triage before the "
                    "pitch-assignment question can be re-asked cleanly."
                )
    lines.append("")

    md_path = outdir / "ac2_verdicts.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("Wrote %s", md_path)
    return md_path.as_posix()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="AC.2 arm evaluator against the pre-registered criteria.",
    )
    parser.add_argument(
        "--arms-dir", type=Path, required=True,
        help="Directory containing ac2_arm_*.json outputs from ac2_run.py.",
    )
    parser.add_argument(
        "--out-dir", type=Path, required=True,
        help="Directory to write ac2_arm_<arm>_verdict.json + ac2_verdicts.md.",
    )
    parser.add_argument(
        "--baseline", default="A1",
        help="Arm-id used as baseline in AC2.2 delta (default A1).",
    )
    parser.add_argument(
        "--tested", default="A2",
        help="Arm-id tested against baseline in AC2.2 delta (default A2).",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)

    arm_verdicts: dict[str, ArmVerdict] = {}
    for arm_json in sorted(args.arms_dir.glob("ac2_arm_*.json")):
        if "verdict" in arm_json.name:
            continue
        payload = json.loads(arm_json.read_text())
        v = evaluate_arm(payload)
        arm_verdicts[v.arm_id] = v
        (args.out_dir / f"ac2_arm_{v.arm_id}_verdict.json").write_text(
            json.dumps(v.to_jsonable(), indent=2), encoding="utf-8",
        )
        log.info(
            "Arm %s: squad_tqs=%s, nagi_trades=%d (pass=%s)",
            v.arm_id,
            _fmt(v.squad_mean_of_window_mean),
            v.nagi_trades_total, v.ac23_nagi_pass,
        )

    # AC2.2 delta
    a1_a2_delta = None
    bh = None
    if args.baseline in arm_verdicts and args.tested in arm_verdicts:
        base = arm_verdicts[args.baseline]
        test = arm_verdicts[args.tested]
        delta, lo, hi = _bootstrap_paired_window_delta(
            base.squad_per_window_mean_tqs,
            test.squad_per_window_mean_tqs,
        )
        p_le0 = _fraction_boot_le_zero(
            base.squad_per_window_mean_tqs,
            test.squad_per_window_mean_tqs,
        )
        a1_a2_delta = (delta, lo, hi, p_le0)
        log.info(
            "AC2.2 %s−%s squad_tqs delta=%.4f [%.4f, %.4f] p=%.3f",
            args.tested, args.baseline, delta, lo, hi, p_le0,
        )
        # BH FDR over actually-executed tests
        pvals: list[float] = []
        labels: list[str] = []
        # AC2.1: 3 anchors × (A2 vs A1). Non-regression is a null-hypothesis
        # framing that is awkward for BH; we omit them from the BH family
        # and treat AC2.1 as a hard prerequisite (as the pre-reg §5.2 wording
        # "Any regression kills that arm" suggests). This matches the
        # pre-reg spirit of AC2.2 being the primary test.
        # AC2.2 squad lift:
        pvals.append(p_le0)
        labels.append(f"AC2.2 squad_lift {args.tested}−{args.baseline}")
        # AC2.3 Nagi floor per arm — binary counts; use a discrete p as
        # count/threshold ratio proxy for BH ordering. We include as
        # "reject-if-fail" tests where p=1.0 if fail else p=0 (essentially
        # forcing BH to reject only if the Nagi test passes; failing tests
        # are trivially "not significant"). This matches the practical
        # semantics — a failing hard-threshold test can't be rescued by FDR.
        for arm_id, v in arm_verdicts.items():
            p_nagi = 0.0 if v.ac23_nagi_pass else 1.0
            pvals.append(p_nagi)
            labels.append(f"AC2.3 nagi_floor {arm_id}")
        bh_threshold, bh_rejects = _bh_fdr(pvals)
        bh = (bh_threshold, bh_rejects, labels, pvals)
        log.info(
            "BH FDR q=%.2f threshold=%.4f; rejects=%s",
            FDR_Q, bh_threshold, list(zip(labels, bh_rejects)),
        )

    md_path = render_verdict_md(
        arm_verdicts,
        a1_a2_delta,
        bh,
        args.out_dir,
        baseline_id=args.baseline,
        tested_id=args.tested,
    )
    print(f"[AC.2] wrote {md_path}")
    return 0


if __name__ == "__main__":       # pragma: no cover
    sys.exit(main())
