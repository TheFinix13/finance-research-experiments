"""G7 v1 checkpoint gate -- FINAL verdict evaluator (all six criteria).

Protocol: `experiments/G7_v1_checkpoint_gate/PROTOCOL.md` (pre-registered
2026-07-01; amendments sec 11.1-11.12). This module closes the C2/C3
"pending" stubs that every prior G7 report carried and produces the
squad-level gate verdict per the protocol's LOCKED sec 3/sec 5 letter.

Why a separate module
---------------------
`run_g7_v1_checkpoint_gate.py` computes C1/C4/C5/C6 live during a
walk-forward replay and stubs C2/C3 (they need the 8 leave-one-out
replays). `run_g7_leave_one_out.py` runs those replays and computes a
panel-wide DIAGNOSTIC C2/C3 (epsilon thresholds, IS+OOS pooled). The
gate verdict itself, however, must follow the protocol's letter:

* C1 -- mean TQS >= 0.30 over the OOS panel AND per-window mean >= 0.20
  in >= 5/7 windows AND bootstrap 95% CI lower bound > 0.25.
* C2 -- at least one peer's mean TQS or trade count strictly improves
  with the agent present, bootstrap CI lower bound on the delta > 0 at
  alpha = 0.05.
* C3 -- the agent does not reduce any single peer's trade count by more
  than 50% in >= 4 of 7 rolling OOS windows.
* C4 -- workspace publish + read counts > 0 (falsifier read waiver per
  sec 11.1). Caches persist panel-wide counts only; per-window counts
  are not recoverable from disk -- documented limitation carried over
  from the walk-forward harness ("C4 is a panel-wide counter").
* C5 -- lot_intent CV >= 0.10 over the OOS panel (panel-wide CV per the
  protocol letter, NOT the harness's stricter all-7-windows fold).
* C6 -- sl_pips CV >= 0.10 OR tp1 CV >= 0.10 over the OOS panel.

Everything is computed from the on-disk replay caches (baseline
`trades.jsonl` + `workspace_counts.json`, per-agent leave-one-out
`trades.jsonl`), so no new multi-hour replay is required when the
caches already cover the panel.

All statistics are computed on OOS trades only (entry_time inside the
union of the 7 rolling OOS windows), matching the protocol's panel
definition. Note this differs from the DIAGNOSTIC lo1 verdicts
(`g7_leave_one_out_verdict_*.{md,json}`), which pooled IS+OOS.

Roster: 7 agents per sec 11.12 (Kunigami retired 2026-07-06).
Structural falsifier waivers per sec 11.1 (Reo).

CLI
---

    PYTHONPATH=../multi-pair-trading-agent:. \
        M001_PRODUCTION_REPO=../multi-pair-trading-agent \
        ../multi-pair-trading-agent/.venv/bin/python \
        -m programs.M001_multi_agent_ensemble.sim.scoring.run_g7_final_verdict \
        --baseline-cache-dir programs/M001_multi_agent_ensemble/reviews/g7_replay_cache_walk-forward-post-kunigami-retirement \
        --lo1-root programs/M001_multi_agent_ensemble/reviews \
        --lo1-tag post-V \
        --arm phi41 \
        --tag g7final-phi41 \
        --out-dir programs/M001_multi_agent_ensemble/reviews -v
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
from types import SimpleNamespace
from typing import Any, Optional

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from programs.M001_multi_agent_ensemble.sim.scoring.run_g7_leave_one_out import (
    _extract_tqs,
    _load_trades_from_jsonl,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_g7_v1_checkpoint_gate import (
    CRIT1_BOOTSTRAP_CI_LOWER,
    CRIT1_MEAN_TQS_THRESHOLD,
    CRIT1_MIN_PASSING_WINDOWS,
    CRIT1_WINDOW_TQS_THRESHOLD,
    CRIT3_MAX_CANNIBAL_FRACTION,
    CRIT3_MIN_PASSING_WINDOWS,
    STRUCTURAL_FALSIFIERS,
    AgentVerdict,
    CriterionResult,
    WalkForwardWindow,
    _evaluate_criterion_4,
    _evaluate_criterion_5,
    _evaluate_criterion_6,
    _g7_windows,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Locked constants for this evaluator (per PROTOCOL sec 3 / sec 5; the
# bootstrap mechanics are implementation details fixed BEFORE results
# were seen -- seed + iteration count recorded in the verdict JSON).
# ---------------------------------------------------------------------------

# 7-agent roster per PROTOCOL sec 11.12 (Kunigami retired).
G7_FINAL_ROSTER: tuple[str, ...] = (
    "isagi_yoichi",
    "bachira_meguru",
    "itoshi_rin",
    "chigiri_hyoma",
    "reo_mikage",
    "nagi_seishiro",
    "barou_shoei",
)

# PARTIAL PASS floor per PROTOCOL sec 1 (>= 5 agents pass; conjunction
# adjusted to the 7-agent roster by sec 11.12).
PARTIAL_PASS_MIN_AGENTS: int = 5

DEFAULT_N_BOOT: int = 10_000
DEFAULT_SEED: int = 42


# ---------------------------------------------------------------------------
# Cache readers
# ---------------------------------------------------------------------------

def _parse_entry_time(t: dict) -> Optional[datetime]:
    raw = t.get("entry_time")
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        dt = datetime.fromisoformat(str(raw))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def load_oos_trades(
    path: Path, windows: list[WalkForwardWindow],
) -> list[dict]:
    """Load a trades.jsonl cache and keep only OOS-window trades.

    Each kept trade dict gains two synthetic keys: ``_entry_dt`` (parsed
    datetime) and ``_window_idx`` (which OOS window it falls in).
    Trades outside every OOS window (i.e. in-sample years) are dropped.
    """
    trades = _load_trades_from_jsonl(path)
    out: list[dict] = []
    for t in trades:
        dt = _parse_entry_time(t)
        if dt is None:
            continue
        for w in windows:
            if w.oos_start <= dt < w.oos_end:
                t["_entry_dt"] = dt
                t["_window_idx"] = w.idx
                out.append(t)
                break
    return out


def _trades_of(trades: list[dict], agent_id: str) -> list[dict]:
    return [t for t in trades if t.get("agent_id") == agent_id]


def _tqs_values(trades: list[dict]) -> list[float]:
    out = []
    for t in trades:
        v = _extract_tqs(t)
        if v is not None:
            out.append(v)
    return out


def _window_counts(
    trades: list[dict], n_windows: int,
) -> list[int]:
    counts = [0] * n_windows
    for t in trades:
        idx = t.get("_window_idx")
        if idx is not None and 0 <= int(idx) < n_windows:
            counts[int(idx)] += 1
    return counts


# ---------------------------------------------------------------------------
# Bootstrap helpers (deterministic, seeded)
# ---------------------------------------------------------------------------

def bootstrap_mean_ci(
    values: list[float],
    *,
    n_boot: int = DEFAULT_N_BOOT,
    seed: int = DEFAULT_SEED,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Percentile bootstrap CI on the mean of ``values``.

    Returns (lower, upper). With < 2 values the CI degenerates to the
    point estimate (or (nan, nan) when empty).
    """
    if not values:
        return (float("nan"), float("nan"))
    arr = np.asarray(values, dtype=float)
    if arr.size < 2:
        return (float(arr[0]), float(arr[0]))
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot, dtype=float)
    chunk = 2_000
    done = 0
    while done < n_boot:
        k = min(chunk, n_boot - done)
        idx = rng.integers(0, arr.size, size=(k, arr.size))
        means[done:done + k] = arr[idx].mean(axis=1)
        done += k
    lo = float(np.quantile(means, alpha / 2.0))
    hi = float(np.quantile(means, 1.0 - alpha / 2.0))
    return (lo, hi)


def bootstrap_mean_diff_ci(
    a: list[float],
    b: list[float],
    *,
    n_boot: int = DEFAULT_N_BOOT,
    seed: int = DEFAULT_SEED,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Percentile bootstrap CI on ``mean(a) - mean(b)``.

    Independent resampling of the two samples (the two configurations
    are separate replays, not paired observations). Degenerate inputs
    (either side empty) return (nan, nan).
    """
    if not a or not b:
        return (float("nan"), float("nan"))
    arr_a = np.asarray(a, dtype=float)
    arr_b = np.asarray(b, dtype=float)
    rng = np.random.default_rng(seed)
    diffs = np.empty(n_boot, dtype=float)
    chunk = 2_000
    done = 0
    while done < n_boot:
        k = min(chunk, n_boot - done)
        ia = rng.integers(0, arr_a.size, size=(k, arr_a.size))
        ib = rng.integers(0, arr_b.size, size=(k, arr_b.size))
        diffs[done:done + k] = (
            arr_a[ia].mean(axis=1) - arr_b[ib].mean(axis=1)
        )
        done += k
    lo = float(np.quantile(diffs, alpha / 2.0))
    hi = float(np.quantile(diffs, 1.0 - alpha / 2.0))
    return (lo, hi)


# ---------------------------------------------------------------------------
# Criterion 1 -- final (protocol letter)
# ---------------------------------------------------------------------------

def evaluate_c1_final(
    agent_id: str,
    trades: list[dict],
    *,
    n_windows: int,
    is_falsifier: bool,
    publish_count: int = 0,
    n_boot: int = DEFAULT_N_BOOT,
    seed: int = DEFAULT_SEED,
) -> CriterionResult:
    """C1 per PROTOCOL sec 3: mean TQS >= 0.30 AND per-window mean
    >= 0.20 in >= 5/7 windows AND bootstrap 95% CI lower bound > 0.25.

    Structural falsifiers are waived per sec 11.1 (publish evidence
    recorded).
    """
    if is_falsifier:
        return CriterionResult(
            passed=True, statistic=float(publish_count), threshold=0.0,
            status="waived",
            evidence={
                "reason": (
                    "structural falsifier waiver (sec 11.1) -- intend() "
                    "returns None by design; earns v1 through publishing"
                ),
                "publish_count": int(publish_count),
            },
        )
    tqs_all = _tqs_values(trades)
    if not tqs_all:
        return CriterionResult(
            passed=False, statistic=0.0,
            threshold=CRIT1_MEAN_TQS_THRESHOLD,
            evidence={"reason": "no OOS trades", "n_trades": 0},
        )
    mean_tqs = statistics.mean(tqs_all)
    # Per-window means; empty windows count as failing windows.
    windows_passing = 0
    per_window_means: dict[int, float | None] = {}
    for w_idx in range(n_windows):
        w_vals = _tqs_values(
            [t for t in trades if t.get("_window_idx") == w_idx]
        )
        if not w_vals:
            per_window_means[w_idx] = None
            continue
        w_mean = statistics.mean(w_vals)
        per_window_means[w_idx] = w_mean
        if w_mean >= CRIT1_WINDOW_TQS_THRESHOLD:
            windows_passing += 1
    ci_lo, ci_hi = bootstrap_mean_ci(tqs_all, n_boot=n_boot, seed=seed)
    passed = (
        mean_tqs >= CRIT1_MEAN_TQS_THRESHOLD
        and windows_passing >= CRIT1_MIN_PASSING_WINDOWS
        and ci_lo > CRIT1_BOOTSTRAP_CI_LOWER
    )
    return CriterionResult(
        passed=passed,
        statistic=float(mean_tqs),
        threshold=CRIT1_MEAN_TQS_THRESHOLD,
        evidence={
            "n_trades": len(trades),
            "mean_tqs": float(mean_tqs),
            "windows_passing_0.20": windows_passing,
            "windows_required": CRIT1_MIN_PASSING_WINDOWS,
            "per_window_means": {
                str(k): (None if v is None else round(v, 4))
                for k, v in per_window_means.items()
            },
            "bootstrap_ci95": [round(ci_lo, 4), round(ci_hi, 4)],
            "ci_lower_floor": CRIT1_BOOTSTRAP_CI_LOWER,
        },
    )


# ---------------------------------------------------------------------------
# Criterion 2 -- final (protocol letter, bootstrap CI on the delta)
# ---------------------------------------------------------------------------

def evaluate_c2_final(
    excluded_id: str,
    *,
    baseline_trades: list[dict],
    lo1_trades: list[dict],
    roster: tuple[str, ...],
    n_windows: int,
    n_boot: int = DEFAULT_N_BOOT,
    seed: int = DEFAULT_SEED,
) -> CriterionResult:
    """C2 per PROTOCOL sec 3: at least one peer's mean TQS or trade
    count strictly improves with the agent present (baseline) vs
    removed (lo1), with bootstrap CI lower bound on that delta > 0.

    Two qualification routes per peer:

    * TQS route -- trade-level bootstrap on
      ``mean_tqs(baseline) - mean_tqs(lo1)``; CI lower bound > 0.
    * Trade-count route -- per-window count deltas
      ``d_w = n_baseline_w - n_lo1_w``; total delta strictly > 0 AND a
      window-level bootstrap (resampling the 7 windows) CI lower
      bound > 0. Window bootstrap because the replay is deterministic
      at trade level -- count variability lives across windows.
    """
    per_peer: dict[str, dict[str, Any]] = {}
    qualifying: list[str] = []
    for peer in roster:
        if peer == excluded_id:
            continue
        b_tr = _trades_of(baseline_trades, peer)
        l_tr = _trades_of(lo1_trades, peer)
        b_tqs = _tqs_values(b_tr)
        l_tqs = _tqs_values(l_tr)
        delta_tqs = (
            statistics.mean(b_tqs) - statistics.mean(l_tqs)
            if b_tqs and l_tqs else None
        )
        tqs_lo, tqs_hi = bootstrap_mean_diff_ci(
            b_tqs, l_tqs, n_boot=n_boot, seed=seed,
        )
        tqs_qualifies = (
            delta_tqs is not None and delta_tqs > 0.0 and tqs_lo > 0.0
        )
        b_counts = _window_counts(b_tr, n_windows)
        l_counts = _window_counts(l_tr, n_windows)
        window_deltas = [
            float(b - l) for b, l in zip(b_counts, l_counts)
        ]
        delta_trades = sum(window_deltas)
        cnt_lo, cnt_hi = bootstrap_mean_ci(
            window_deltas, n_boot=n_boot, seed=seed,
        )
        trades_qualifies = delta_trades > 0.0 and cnt_lo > 0.0
        per_peer[peer] = {
            "delta_tqs": None if delta_tqs is None else round(delta_tqs, 5),
            "tqs_ci95": [round(tqs_lo, 5), round(tqs_hi, 5)],
            "tqs_qualifies": tqs_qualifies,
            "delta_trades": delta_trades,
            "window_deltas": window_deltas,
            "trades_ci95": [round(cnt_lo, 3), round(cnt_hi, 3)],
            "trades_qualifies": trades_qualifies,
        }
        if tqs_qualifies or trades_qualifies:
            qualifying.append(peer)
    passed = bool(qualifying)
    # Statistic: strongest qualifying peer's delta (TQS units when the
    # TQS route qualifies, else the trade-count delta).
    stat = 0.0
    if qualifying:
        best = max(
            qualifying,
            key=lambda p: (
                per_peer[p]["delta_tqs"] or 0.0
                if per_peer[p]["tqs_qualifies"]
                else per_peer[p]["delta_trades"] / 1000.0
            ),
        )
        stat = float(
            per_peer[best]["delta_tqs"] or per_peer[best]["delta_trades"]
        )
    return CriterionResult(
        passed=passed,
        statistic=stat,
        threshold=0.0,
        evidence={
            "qualifying_peers": qualifying,
            "per_peer": per_peer,
            "rule": (
                "exists peer with (delta_tqs > 0 AND bootstrap CI lower "
                "> 0) OR (delta_trades > 0 AND window-bootstrap CI "
                "lower > 0); alpha=0.05"
            ),
        },
    )


# ---------------------------------------------------------------------------
# Criterion 3 -- final (protocol letter, per-window 4-of-7)
# ---------------------------------------------------------------------------

def _window_reduction_ratio(baseline_n: int, lo1_n: int) -> float:
    """Fraction of a peer's without-agent trades lost to the agent's
    presence: ``(lo1_n - baseline_n) / lo1_n``.

    ``lo1_n == 0`` -> 0.0: the peer would not have traded even without
    the agent, so no reduction is attributable (the agent's presence
    can only have ADDED trades in that window). Note the diagnostic
    aggregator in ``run_g7_leave_one_out`` returns 1.0 for the
    lo1_n == 0 / baseline_n > 0 branch -- that is wrong-signed for a
    cannibalisation measure (the peer trades MORE with the agent
    present) and is corrected here for the gate verdict.
    """
    if lo1_n <= 0:
        return 0.0
    return (lo1_n - baseline_n) / lo1_n


def evaluate_c3_final(
    excluded_id: str,
    *,
    baseline_trades: list[dict],
    lo1_trades: list[dict],
    roster: tuple[str, ...],
    n_windows: int,
) -> CriterionResult:
    """C3 per PROTOCOL sec 3: the agent must not reduce any single
    peer's trade count by more than 50% in >= 4 of 7 OOS windows.

    A window is CLEAN iff every peer's reduction ratio <= 0.50.
    Pass iff clean windows >= CRIT3_MIN_PASSING_WINDOWS (4).
    """
    peer_counts_b: dict[str, list[int]] = {}
    peer_counts_l: dict[str, list[int]] = {}
    for peer in roster:
        if peer == excluded_id:
            continue
        peer_counts_b[peer] = _window_counts(
            _trades_of(baseline_trades, peer), n_windows,
        )
        peer_counts_l[peer] = _window_counts(
            _trades_of(lo1_trades, peer), n_windows,
        )
    clean_windows = 0
    per_window: list[dict[str, Any]] = []
    for w in range(n_windows):
        worst_peer: str | None = None
        worst_ratio = 0.0
        for peer in peer_counts_b:
            ratio = _window_reduction_ratio(
                peer_counts_b[peer][w], peer_counts_l[peer][w],
            )
            if ratio > worst_ratio:
                worst_ratio = ratio
                worst_peer = peer
        clean = worst_ratio <= CRIT3_MAX_CANNIBAL_FRACTION
        if clean:
            clean_windows += 1
        per_window.append({
            "window": w,
            "worst_peer": worst_peer,
            "worst_reduction": round(worst_ratio, 4),
            "clean": clean,
        })
    passed = clean_windows >= CRIT3_MIN_PASSING_WINDOWS
    return CriterionResult(
        passed=passed,
        statistic=float(clean_windows),
        threshold=float(CRIT3_MIN_PASSING_WINDOWS),
        evidence={
            "clean_windows": clean_windows,
            "windows_required": CRIT3_MIN_PASSING_WINDOWS,
            "max_reduction_threshold": CRIT3_MAX_CANNIBAL_FRACTION,
            "per_window": per_window,
        },
    )


# ---------------------------------------------------------------------------
# Final report assembly
# ---------------------------------------------------------------------------

@dataclass
class G7FinalReport:
    tag: str
    arm: str
    baseline_cache: str
    lo1_root: str
    lo1_tag: str
    n_windows: int
    seed: int
    n_boot: int
    per_agent: dict[str, AgentVerdict] = field(default_factory=dict)
    verdict: str = "FAIL"          # "PASS" | "PARTIAL PASS" | "FAIL"
    n_agents_passing: int = 0
    notes: list[str] = field(default_factory=list)

    def to_jsonable(self) -> dict:
        return {
            "tag": self.tag,
            "arm": self.arm,
            "protocol": "experiments/G7_v1_checkpoint_gate/PROTOCOL.md",
            "roster": list(G7_FINAL_ROSTER),
            "baseline_cache": self.baseline_cache,
            "lo1_root": self.lo1_root,
            "lo1_tag": self.lo1_tag,
            "n_windows": self.n_windows,
            "bootstrap": {"seed": self.seed, "n_boot": self.n_boot},
            "verdict": self.verdict,
            "n_agents_passing": self.n_agents_passing,
            "notes": self.notes,
            "per_agent": {
                aid: v.to_jsonable() for aid, v in self.per_agent.items()
            },
        }


def squad_verdict(per_agent: dict[str, AgentVerdict]) -> tuple[str, int]:
    """PROTOCOL sec 1 semantics on the sec 11.12 roster: PASS iff all
    rostered agents pass 6/6; PARTIAL PASS iff >= 5 pass; else FAIL."""
    n_pass = sum(
        1 for aid in G7_FINAL_ROSTER
        if aid in per_agent and per_agent[aid].is_v1_pass
    )
    if n_pass == len(G7_FINAL_ROSTER):
        return "PASS", n_pass
    if n_pass >= PARTIAL_PASS_MIN_AGENTS:
        return "PARTIAL PASS", n_pass
    return "FAIL", n_pass


def _dict_trades_as_attr(trades: list[dict]) -> list[Any]:
    """Wrap trade dicts so the C5/C6 evaluators (which use getattr on
    TradeRecord instances) can consume cache rows unchanged."""
    return [SimpleNamespace(**t) for t in trades]


def _instantiate_roster_agents() -> dict[str, Any]:
    """Instantiate the 7 rostered agent classes for C5/C6 (playstyle
    dispatch only -- no bars / no prepare needed, F19/F20 are pure
    functions of their arguments)."""
    from programs.M001_multi_agent_ensemble.sim._cross_repo import (
        ensure_production_repo_on_path,
    )
    ensure_production_repo_on_path()
    from programs.M001_multi_agent_ensemble.sim.agents.a01_isagi import A1IsagiV1
    from programs.M001_multi_agent_ensemble.sim.agents.a02_bachira import A2BachiraV1
    from programs.M001_multi_agent_ensemble.sim.agents.a03_rin import A3RinV1
    from programs.M001_multi_agent_ensemble.sim.agents.a04_chigiri import A4ChigiriV1
    from programs.M001_multi_agent_ensemble.sim.agents.a05_reo import A5ReoV1
    from programs.M001_multi_agent_ensemble.sim.agents.a06_nagi import A6NagiV1
    from programs.M001_multi_agent_ensemble.sim.agents.a07_barou import A7BarouV1
    agents = [
        A1IsagiV1(), A2BachiraV1(), A3RinV1(), A4ChigiriV1(),
        A5ReoV1(), A6NagiV1(), A7BarouV1(),
    ]
    return {a.agent_id: a for a in agents}


def run_final_verdict(
    *,
    baseline_cache_dir: Path,
    lo1_root: Path,
    lo1_tag: str,
    arm: str,
    tag: str,
    out_dir: Path | None = None,
    n_boot: int = DEFAULT_N_BOOT,
    seed: int = DEFAULT_SEED,
    agents_by_id: dict[str, Any] | None = None,
) -> G7FinalReport:
    """Compose the on-disk caches into the final six-criterion verdict.

    ``agents_by_id`` is injectable for tests; the default instantiates
    the real roster classes (requires the production repo on path).
    """
    windows = _g7_windows()
    n_windows = len(windows)

    baseline_trades = load_oos_trades(
        baseline_cache_dir / "trades.jsonl", windows,
    )
    if not baseline_trades:
        raise FileNotFoundError(
            f"baseline cache has no OOS trades: {baseline_cache_dir}"
        )
    ws_path = baseline_cache_dir / "workspace_counts.json"
    ws = json.loads(ws_path.read_text()) if ws_path.exists() else {}
    publish = {k: int(v) for k, v in (ws.get("publish") or {}).items()}
    read = {k: int(v) for k, v in (ws.get("read") or {}).items()}

    lo1_dir = lo1_root / f"g7_leave_one_out_{lo1_tag}"
    lo1_trades_by_excluded: dict[str, list[dict]] = {}
    for aid in G7_FINAL_ROSTER:
        p = lo1_dir / f"lo1_{aid}" / "trades.jsonl"
        if not p.exists():
            log.warning("lo1 cache missing for excluded=%s at %s", aid, p)
            continue
        lo1_trades_by_excluded[aid] = load_oos_trades(p, windows)

    if agents_by_id is None:
        agents_by_id = _instantiate_roster_agents()

    report = G7FinalReport(
        tag=tag, arm=arm,
        baseline_cache=str(baseline_cache_dir),
        lo1_root=str(lo1_root), lo1_tag=lo1_tag,
        n_windows=n_windows, seed=seed, n_boot=n_boot,
    )
    for aid in G7_FINAL_ROSTER:
        agent = agents_by_id.get(aid)
        ag_trades = _trades_of(baseline_trades, aid)
        is_falsifier = aid in STRUCTURAL_FALSIFIERS
        v = AgentVerdict(
            agent_id=aid,
            playstyle=getattr(agent, "playstyle", "unknown"),
            tier=int(getattr(agent, "tier", 2)),
        )
        v.criteria[1] = evaluate_c1_final(
            aid, ag_trades,
            n_windows=n_windows, is_falsifier=is_falsifier,
            publish_count=publish.get(aid, 0),
            n_boot=n_boot, seed=seed,
        )
        lo1 = lo1_trades_by_excluded.get(aid)
        if lo1 is None:
            v.criteria[2] = CriterionResult(
                passed=False, statistic=0.0, threshold=0.0,
                status="pending",
                evidence={"reason": f"lo1 cache missing for {aid}"},
            )
            v.criteria[3] = CriterionResult(
                passed=False, statistic=0.0,
                threshold=float(CRIT3_MIN_PASSING_WINDOWS),
                status="pending",
                evidence={"reason": f"lo1 cache missing for {aid}"},
            )
        else:
            v.criteria[2] = evaluate_c2_final(
                aid,
                baseline_trades=baseline_trades, lo1_trades=lo1,
                roster=G7_FINAL_ROSTER, n_windows=n_windows,
                n_boot=n_boot, seed=seed,
            )
            v.criteria[3] = evaluate_c3_final(
                aid,
                baseline_trades=baseline_trades, lo1_trades=lo1,
                roster=G7_FINAL_ROSTER, n_windows=n_windows,
            )
        v.criteria[4] = _evaluate_criterion_4(
            aid, publish.get(aid, 0), read.get(aid, 0),
        )
        shim = _dict_trades_as_attr(ag_trades)
        if agent is not None:
            v.criteria[5] = _evaluate_criterion_5(agent, shim)
            v.criteria[6] = _evaluate_criterion_6(agent, shim)
        else:
            for i in (5, 6):
                v.criteria[i] = CriterionResult(
                    passed=False, statistic=0.0, threshold=0.10,
                    status="pending",
                    evidence={"reason": f"agent instance missing for {aid}"},
                )
        report.per_agent[aid] = v

    report.verdict, report.n_agents_passing = squad_verdict(
        report.per_agent,
    )
    report.notes = [
        "All statistics OOS-only (union of the 7 rolling OOS windows); "
        "differs from the diagnostic lo1 verdicts which pooled IS+OOS.",
        "C4 evaluated on panel-wide publish/read counters (per-window "
        "counts not persisted in caches; documented harness limitation).",
        "C5/C6 recomputed from cached source_* trade fields via the "
        "pure playstyle-dispatched F19/F20 primitives (no agent "
        "overrides exist).",
    ]

    if out_dir is not None:
        odir = Path(out_dir)
        odir.mkdir(parents=True, exist_ok=True)
        json_path = odir / f"g7_v1_checkpoint_final_{tag}.json"
        json_path.write_text(
            json.dumps(report.to_jsonable(), indent=2, default=str),
            encoding="utf-8",
        )
        log.info("wrote %s", json_path)
        md_path = odir / f"g7_v1_checkpoint_final_{tag}.md"
        md_path.write_text(render_final_report(report), encoding="utf-8")
        log.info("wrote %s", md_path)
    return report


def render_final_report(report: G7FinalReport) -> str:
    lines: list[str] = []
    lines.append(
        f"# G7 v1 Checkpoint Gate -- FINAL verdict ({report.tag})"
    )
    lines.append("")
    lines.append(
        f"**Squad verdict: {report.verdict}** "
        f"({report.n_agents_passing}/{len(G7_FINAL_ROSTER)} agents pass "
        f"all six criteria)"
    )
    lines.append("")
    lines.append(f"- Aggregator arm: `{report.arm}`")
    lines.append(f"- Baseline cache: `{report.baseline_cache}`")
    lines.append(
        f"- Leave-one-out caches: `{report.lo1_root}/"
        f"g7_leave_one_out_{report.lo1_tag}/lo1_*`"
    )
    lines.append(
        f"- Bootstrap: n={report.n_boot}, seed={report.seed}, "
        f"percentile CI, alpha=0.05"
    )
    lines.append(
        f"- Windows: {report.n_windows} rolling OOS (2019..2025)"
    )
    lines.append("")
    lines.append("## Per-agent 6-bit vectors")
    lines.append("")
    lines.append("| Agent | Playstyle | Bit vector | C1 | C2 | C3 | C4 | C5 | C6 | v1 pass? |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for aid in G7_FINAL_ROSTER:
        v = report.per_agent.get(aid)
        if v is None:
            continue

        def _cell(i: int) -> str:
            r = v.criteria.get(i)
            if r is None:
                return "?"
            if r.status == "waived":
                return "W"
            if r.status == "pending":
                return "?"
            return f"{'✅' if r.passed else '❌'} {r.statistic:.3f}"

        lines.append(
            f"| `{aid}` | {v.playstyle} | `{v.bit_vector}` | "
            + " | ".join(_cell(i) for i in range(1, 7))
            + f" | {'YES' if v.is_v1_pass else 'no'} |"
        )
    lines.append("")
    lines.append(
        "Legend: `1` pass / `0` fail / `W` waived (structural "
        "falsifier, sec 11.1) / `?` pending. Cell numbers are the "
        "criterion statistic (C1 mean TQS; C2 strongest qualifying "
        "delta; C3 clean windows; C4 min(publish, read); C5/C6 CV)."
    )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for n in report.notes:
        lines.append(f"- {n}")
    lines.append("")
    lines.append("## Per-criterion evidence")
    for aid in G7_FINAL_ROSTER:
        v = report.per_agent.get(aid)
        if v is None:
            continue
        lines.append("")
        lines.append(f"### {aid}")
        for i in range(1, 7):
            r = v.criteria.get(i)
            if r is None:
                continue
            state = (
                r.status if r.status != "computed"
                else ("pass" if r.passed else "fail")
            )
            lines.append(
                f"- **C{i}** ({state}): stat={r.statistic:.4f} "
                f"threshold={r.threshold:.4f}"
            )
            for k, val in r.evidence.items():
                if k == "per_peer":
                    for peer, pe in val.items():
                        lines.append(
                            f"    - {peer}: dTQS={pe['delta_tqs']} "
                            f"CI={pe['tqs_ci95']} "
                            f"(qual={pe['tqs_qualifies']}) | "
                            f"dTrades={pe['delta_trades']:+.0f} "
                            f"CI={pe['trades_ci95']} "
                            f"(qual={pe['trades_qualifies']})"
                        )
                elif k == "per_window":
                    row = ", ".join(
                        f"w{p['window']}:{p['worst_reduction']:.2f}"
                        f"{'' if p['clean'] else '!'}"
                        for p in val
                    )
                    lines.append(
                        f"    - per_window worst reductions: {row} "
                        f"('!' = dirty window)"
                    )
                elif isinstance(val, float):
                    lines.append(f"    - {k}: {val:.4f}")
                else:
                    lines.append(f"    - {k}: {val}")
    lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_g7_final_verdict",
        description=(
            "G7 v1 checkpoint gate FINAL verdict -- computes all six "
            "criteria from on-disk replay caches per the protocol's "
            "locked letter."
        ),
    )
    p.add_argument("--baseline-cache-dir", type=Path, required=True)
    p.add_argument("--lo1-root", type=Path, required=True,
                   help="Directory containing g7_leave_one_out_<tag>/")
    p.add_argument("--lo1-tag", required=True,
                   help="e.g. post-V (phi41) or phi5-arm4")
    p.add_argument("--arm", required=True, choices=("phi41", "arm4"),
                   help="Label recorded in the report (provenance only).")
    p.add_argument("--tag", required=True)
    p.add_argument("--out-dir", type=Path,
                   default=Path("programs/M001_multi_agent_ensemble/reviews"))
    p.add_argument("--n-boot", type=int, default=DEFAULT_N_BOOT)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("-v", "--verbose", action="count", default=0)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
    )
    report = run_final_verdict(
        baseline_cache_dir=args.baseline_cache_dir,
        lo1_root=args.lo1_root,
        lo1_tag=args.lo1_tag,
        arm=args.arm,
        tag=args.tag,
        out_dir=args.out_dir,
        n_boot=args.n_boot,
        seed=args.seed,
    )
    print(
        f"G7 FINAL verdict [{args.tag}] ({args.arm}): {report.verdict} "
        f"({report.n_agents_passing}/{len(G7_FINAL_ROSTER)})"
    )
    for aid in G7_FINAL_ROSTER:
        v = report.per_agent.get(aid)
        if v is not None:
            print(f"  {aid:<18} {v.bit_vector}  "
                  f"{'v1 PASS' if v.is_v1_pass else 'no'}")
    return 0


if __name__ == "__main__":                                 # pragma: no cover
    sys.exit(main())
