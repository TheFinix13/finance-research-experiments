"""E020 Phase 2 — MFE-ratcheted trailing stop, walk-forward validation.

Consumes the PRE-0 path-augmented ledgers for EURUSD/GBPUSD/USDCAD
(``programs/_shared/counterfactual_replay/data/{SYMBOL}_H4_paths.jsonl``)
via the shared replay engine. Sweeps the 12-arm frozen grid
``activation_R ∈ {1.0, 1.2, 1.3} × lock_fraction ∈ {0.4, 0.5, 0.6, 0.7}``
and produces per-fold + pooled ΔSharpe statistics with paired bootstrap
95 % CIs and BH-FDR correction.

Everything is pre-registered in
[`experiments/E020_mfe_ratcheted_trail/PROTOCOL.md`](../../experiments/E020_mfe_ratcheted_trail/PROTOCOL.md).
This file is the mechanical implementation — no post-hoc tuning.

CLI::

    PYTHONPATH=../multi-pair-trading-agent:.:scripts \\
        ../multi-pair-trading-agent/.venv/bin/python \\
        programs/E020/run_e020_validation.py \\
        --output programs/E020/results.json
"""
from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Sequence

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from programs._shared.counterfactual_replay.replay import (  # noqa: E402
    Bar,
    ExitAction,
    PIP,
    PRIORITY_E020_RATCHET,
    TradeRecord,
    TradeState,
    load_paths_ledger,
    replay,
)

log = logging.getLogger("E020")


# ---------------------------------------------------------------------------
# Frozen §4 grid.
# ---------------------------------------------------------------------------

SYMBOLS: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDCAD")
ACTIVATION_R_GRID: tuple[float, ...] = (1.0, 1.2, 1.3)
LOCK_FRACTION_GRID: tuple[float, ...] = (0.4, 0.5, 0.6, 0.7)
BOOTSTRAP_SEED: int = 42
BOOTSTRAP_RESAMPLES: int = 5000
FDR_ALPHA: float = 0.10

# Walk-forward folds (SPEC §3, mirrors E004).
FOLDS: tuple[tuple[str, datetime, datetime], ...] = (
    ("fold1", datetime(2017, 1, 1, tzinfo=timezone.utc), datetime(2019, 1, 1, tzinfo=timezone.utc)),
    ("fold2", datetime(2019, 1, 1, tzinfo=timezone.utc), datetime(2021, 1, 1, tzinfo=timezone.utc)),
    ("fold3", datetime(2021, 1, 1, tzinfo=timezone.utc), datetime(2023, 1, 1, tzinfo=timezone.utc)),
    ("fold4", datetime(2023, 1, 1, tzinfo=timezone.utc), datetime(2024, 7, 1, tzinfo=timezone.utc)),
    ("fold5", datetime(2024, 7, 1, tzinfo=timezone.utc), datetime(2026, 1, 1, tzinfo=timezone.utc)),
)


# ---------------------------------------------------------------------------
# Rule factory.
# ---------------------------------------------------------------------------

def make_e020_rule(activation_r: float, lock_fraction: float) -> Callable[[TradeState, Bar], Optional[ExitAction]]:
    """Return the E020 ratchet rule for a given (activation_R, lock_fraction) arm.

    PROTOCOL §3.4: on any bar where MFE ≥ activation_R multiples of the
    entry-time R-distance, propose an adjust_stop at entry + d·lock_fraction·MFE.
    The engine's stop-monotonicity invariant (SPEC §4.2) will drop the
    action if it would loosen the current effective stop.
    """
    def rule(state: TradeState, bar: Bar) -> Optional[ExitAction]:
        if state.mfe_r_so_far < activation_r:
            return None
        mfe_pips = state.mfe_pips_so_far
        ratchet_price = state.entry + state.direction * lock_fraction * mfe_pips * PIP
        return ExitAction(
            kind="adjust_stop",
            price=ratchet_price,
            reason=PRIORITY_E020_RATCHET,
        )
    return rule


# ---------------------------------------------------------------------------
# Metric helpers.
# ---------------------------------------------------------------------------

def _sharpe(returns: Sequence[float]) -> float:
    """Sharpe on a per-trade R-sequence (no annualisation — same convention as
    the paired ΔSharpe: both sides use the same n_trades, so annualisation
    factors cancel in the delta)."""
    arr = np.asarray(returns, dtype=float)
    if arr.size < 2:
        return float("nan")
    sd = arr.std(ddof=1)
    if sd == 0:
        return float("nan")
    return float(arr.mean() / sd)


def _paired_delta_sharpe(r_arm: Sequence[float], r_base: Sequence[float]) -> float:
    return _sharpe(r_arm) - _sharpe(r_base)


def _paired_bootstrap_ci(
    r_arm: Sequence[float],
    r_base: Sequence[float],
    seed: int = BOOTSTRAP_SEED,
    resamples: int = BOOTSTRAP_RESAMPLES,
    alpha: float = 0.05,
) -> tuple[float, float, float, float]:
    """Return (delta_sharpe_point, ci_low, ci_high, p_value_two_sided).

    Paired: resample indices, use same indices for arm and baseline. p-value
    is the two-sided fraction of bootstrap deltas whose sign disagrees with
    the point estimate (bootstrap-standard, ``benjamini1995controlling``
    friendly)."""
    arm = np.asarray(r_arm, dtype=float)
    base = np.asarray(r_base, dtype=float)
    assert arm.shape == base.shape, "paired arrays must have equal length"
    n = arm.size
    if n < 2:
        return float("nan"), float("nan"), float("nan"), float("nan")

    point = _paired_delta_sharpe(arm, base)
    rng = np.random.default_rng(seed)
    deltas = np.empty(resamples, dtype=float)
    for k in range(resamples):
        idx = rng.integers(0, n, size=n)
        deltas[k] = _paired_delta_sharpe(arm[idx], base[idx])

    lo = float(np.quantile(deltas, alpha / 2))
    hi = float(np.quantile(deltas, 1 - alpha / 2))

    # Two-sided p-value: fraction of resamples on the opposite side of 0
    # from the point estimate (asymptotically equivalent to the studentised
    # bootstrap under nice conditions).
    if point >= 0:
        p_two = 2.0 * float(np.mean(deltas <= 0))
    else:
        p_two = 2.0 * float(np.mean(deltas >= 0))
    p_two = min(p_two, 1.0)
    return point, lo, hi, p_two


def _bh_fdr(p_values: Sequence[float], alpha: float = FDR_ALPHA) -> list[bool]:
    """Benjamini–Hochberg FDR. Returns list of booleans (True = reject H0)."""
    p = np.asarray(p_values, dtype=float)
    m = p.size
    order = np.argsort(p)
    thresholds = (np.arange(1, m + 1) / m) * alpha
    p_sorted = p[order]
    passed_sorted = p_sorted <= thresholds
    # The BH procedure: find the largest k such that P_(k) ≤ (k/m)·α;
    # reject all P_(i) for i ≤ k.
    if not passed_sorted.any():
        cutoff = -1
    else:
        cutoff = int(np.max(np.where(passed_sorted)))
    rejected_sorted = np.zeros(m, dtype=bool)
    if cutoff >= 0:
        rejected_sorted[: cutoff + 1] = True
    rejected = np.empty(m, dtype=bool)
    rejected[order] = rejected_sorted
    return rejected.tolist()


def _p_max_consec_loss_streak(rs: Sequence[float]) -> int:
    """Length of the longest consecutive-loss run (r <= 0)."""
    longest = current = 0
    for r in rs:
        if r <= 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _tail_mean(rs: Sequence[float], q: float = 0.10) -> float:
    """Mean of the worst-q fraction of the R-sequence."""
    arr = np.sort(np.asarray(rs, dtype=float))
    k = max(1, int(arr.size * q))
    return float(arr[:k].mean())


# ---------------------------------------------------------------------------
# Fold assignment.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Fold:
    name: str
    start: datetime
    end: datetime  # exclusive


def _fold_of(entry_time: datetime, folds: Sequence[tuple[str, datetime, datetime]]) -> Optional[str]:
    for name, s, e in folds:
        if s <= entry_time < e:
            return name
    return None


# ---------------------------------------------------------------------------
# Sweep engine.
# ---------------------------------------------------------------------------

def _run_arm_all_trades(
    trades: list[TradeRecord],
    rule: Callable[[TradeState, Bar], Optional[ExitAction]],
) -> tuple[list[float], list[float]]:
    """Return (arm_R, base_R) paired lists across all input trades."""
    arm_R: list[float] = []
    base_R: list[float] = []
    for t in trades:
        alt = replay(t, rule=rule)
        arm_R.append(alt.r)
        base_R.append(t.r)
    return arm_R, base_R


def _diagnostic_n_fired_no_reach(
    trades: list[TradeRecord], activation_r: float,
) -> dict:
    """Trades where MFE ever crossed activation_R but the trade did not
    hit TP. Reports count + mean R impact vs baseline."""
    fired = [
        t for t in trades
        if t.mfe_r >= activation_r and t.exit_reason != "tp"
    ]
    return {
        "n": len(fired),
        "mean_baseline_r": float(np.mean([t.r for t in fired])) if fired else float("nan"),
    }


def sweep(
    trades: list[TradeRecord],
    activation_grid: Sequence[float] = ACTIVATION_R_GRID,
    lock_grid: Sequence[float] = LOCK_FRACTION_GRID,
    folds: Sequence[tuple[str, datetime, datetime]] = FOLDS,
    seed: int = BOOTSTRAP_SEED,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> dict:
    """Full 12-arm × 5-fold sweep over the pooled trade population.

    Returns a JSON-ready dict with per-arm per-fold + pooled metrics,
    guardrails, mechanism diagnostics, and BH-FDR verdicts."""
    # Assign each trade to a fold.
    fold_ids = [_fold_of(t.entry_time, folds) for t in trades]

    arms_out: list[dict] = []
    pooled_p_values: list[float] = []
    arm_summary_rows: list[dict] = []

    for a in activation_grid:
        for l in lock_grid:
            rule = make_e020_rule(a, l)
            log.info("arm (a=%.1f, l=%.1f): replaying %d trades ...", a, l, len(trades))
            arm_R_all, base_R_all = _run_arm_all_trades(trades, rule)

            # Per-fold pass.
            per_fold = []
            fold_positive_flags = []
            for fname, fs, fe in folds:
                arm_fold = [r for r, fid in zip(arm_R_all, fold_ids) if fid == fname]
                base_fold = [r for r, fid in zip(base_R_all, fold_ids) if fid == fname]
                if not arm_fold:
                    per_fold.append({
                        "fold": fname, "n_trades": 0,
                        "delta_sharpe": None, "ci_low": None, "ci_high": None,
                        "p_two_sided": None,
                    })
                    fold_positive_flags.append(False)
                    continue
                point, lo, hi, p = _paired_bootstrap_ci(
                    arm_fold, base_fold, seed=seed, resamples=resamples,
                )
                per_fold.append({
                    "fold": fname,
                    "n_trades": len(arm_fold),
                    "delta_sharpe": round(point, 4),
                    "ci_low": round(lo, 4),
                    "ci_high": round(hi, 4),
                    "p_two_sided": round(p, 4),
                    "sharpe_arm": round(_sharpe(arm_fold), 4),
                    "sharpe_base": round(_sharpe(base_fold), 4),
                    "mean_delta_r": round(float(np.mean(np.array(arm_fold) - np.array(base_fold))), 4),
                })
                fold_positive_flags.append(point > 0)

            # Pooled pass.
            arm_R_pooled = np.array(arm_R_all)
            base_R_pooled = np.array(base_R_all)
            pooled_delta_r = arm_R_pooled - base_R_pooled
            pooled_point, pooled_lo, pooled_hi, pooled_p = _paired_bootstrap_ci(
                arm_R_pooled, base_R_pooled, seed=seed, resamples=resamples,
            )

            # Guardrails.
            tail_arm = _tail_mean(arm_R_pooled, q=0.10)
            tail_base = _tail_mean(base_R_pooled, q=0.10)
            delta_tail = tail_arm - tail_base

            streak_arm = _p_max_consec_loss_streak(arm_R_pooled)
            streak_base = _p_max_consec_loss_streak(base_R_pooled)

            p_winner_reaches_arm = float(np.mean(arm_R_pooled >= 1.0))
            p_winner_reaches_base = float(np.mean(base_R_pooled >= 1.0))

            diagnostic = _diagnostic_n_fired_no_reach(trades, a)

            arm_out = {
                "arm_id": f"a{a}_l{l}",
                "activation_R": a,
                "lock_fraction": l,
                "n_trades": len(arm_R_all),
                "per_fold": per_fold,
                "fold_positive_flags": fold_positive_flags,
                "n_folds_positive": sum(fold_positive_flags),
                "pooled": {
                    "delta_sharpe": round(pooled_point, 4),
                    "ci_low": round(pooled_lo, 4),
                    "ci_high": round(pooled_hi, 4),
                    "p_two_sided": round(pooled_p, 4),
                    "sharpe_arm": round(_sharpe(arm_R_pooled), 4),
                    "sharpe_base": round(_sharpe(base_R_pooled), 4),
                    "mean_delta_r": round(float(pooled_delta_r.mean()), 4),
                    "median_delta_r": round(float(np.median(pooled_delta_r)), 4),
                },
                "guardrails": {
                    "tail_arm_worst10": round(tail_arm, 4),
                    "tail_base_worst10": round(tail_base, 4),
                    "delta_tail_worst10": round(delta_tail, 4),
                    "max_consec_loss_streak_arm": streak_arm,
                    "max_consec_loss_streak_base": streak_base,
                    "delta_max_consec_loss_streak": streak_arm - streak_base,
                    "p_winner_reaches_1r_arm": round(p_winner_reaches_arm, 4),
                    "p_winner_reaches_1r_base": round(p_winner_reaches_base, 4),
                    "delta_p_winner_reaches_1r": round(
                        p_winner_reaches_arm - p_winner_reaches_base, 4
                    ),
                },
                "mechanism": {
                    "n_fired_no_reach": diagnostic["n"],
                    "mean_baseline_r_of_fired_no_reach": (
                        round(diagnostic["mean_baseline_r"], 4)
                        if not (diagnostic["mean_baseline_r"] != diagnostic["mean_baseline_r"])
                        else None
                    ),
                },
            }
            arms_out.append(arm_out)
            pooled_p_values.append(pooled_p)

    # BH-FDR across 12 arms on pooled two-sided p-values.
    fdr_rejected = _bh_fdr(pooled_p_values, alpha=FDR_ALPHA)
    for arm, rejected in zip(arms_out, fdr_rejected):
        arm["bh_fdr_rejected"] = bool(rejected)

    # Per-arm verdict per PROTOCOL §6.
    def _classify(arm: dict) -> str:
        p = arm["pooled"]
        primary = p["ci_low"] > 0
        robust = arm["n_folds_positive"] >= 4
        joint_sig = p["p_two_sided"] < 0.05
        fdr = arm["bh_fdr_rejected"]
        # Tail guardrail: delta_tail ≥ 0 within bootstrap noise. We use a
        # loose "≥ -0.10 R" band as "within noise" (bootstrap CI on tail
        # is not computed here — a Phase 2b would add it; the PROTOCOL
        # says "within bootstrap noise").
        tail_ok = arm["guardrails"]["delta_tail_worst10"] >= -0.10
        streak_ok = arm["guardrails"]["delta_max_consec_loss_streak"] <= 0

        if primary and robust and joint_sig and fdr and tail_ok and streak_ok:
            return "alive"
        if p["delta_sharpe"] > 0 and (not primary or not robust or not fdr):
            return "parked_low_yield"
        if p["delta_sharpe"] > 0 and (not tail_ok or not streak_ok):
            return "parked_capital_cost"
        return "dead"

    for arm in arms_out:
        arm["verdict"] = _classify(arm)

    return {
        "arms": arms_out,
        "grid": {
            "activation_R": list(activation_grid),
            "lock_fraction": list(lock_grid),
            "n_arms": len(arms_out),
        },
        "folds": [
            {"name": n, "start": s.isoformat(), "end": e.isoformat()}
            for n, s, e in folds
        ],
        "bootstrap": {
            "seed": seed,
            "resamples": resamples,
        },
        "fdr": {
            "method": "BH",
            "alpha": FDR_ALPHA,
            "family_size": len(arms_out),
        },
    }


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="programs/E020/results.json")
    parser.add_argument("--data-dir", default=None,
                        help="Override PRE-0 data dir (defaults to package location)")
    parser.add_argument("--symbols", default=",".join(SYMBOLS))
    parser.add_argument("--smoke-only-first-arm", action="store_true",
                        help="Only evaluate the first (a,l) arm — for interface smoke tests")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    log.info("E020 Phase 2 — MFE-ratcheted trailing stop validation")
    log.info("Grid: activation_R=%s × lock_fraction=%s (%d arms)",
             ACTIVATION_R_GRID, LOCK_FRACTION_GRID,
             len(ACTIVATION_R_GRID) * len(LOCK_FRACTION_GRID))

    # Load all requested symbols.
    all_trades: list[TradeRecord] = []
    per_symbol_meta: dict[str, dict] = {}
    symbols = tuple(s.strip() for s in args.symbols.split(","))
    kwargs = {"data_dir": args.data_dir} if args.data_dir else {}
    for sym in symbols:
        meta, trades = load_paths_ledger(sym, **kwargs)
        per_symbol_meta[sym] = meta
        all_trades.extend(trades)
        log.info("  loaded %s: %d trades, hit_rate=%.4f, mean_r=%.4f",
                 sym, len(trades), meta.get("hit_rate", -1), meta.get("mean_r", -1))
    log.info("Total pooled trades: %d", len(all_trades))

    activation = (ACTIVATION_R_GRID[0],) if args.smoke_only_first_arm else ACTIVATION_R_GRID
    lock = (LOCK_FRACTION_GRID[0],) if args.smoke_only_first_arm else LOCK_FRACTION_GRID

    results = sweep(
        all_trades,
        activation_grid=activation,
        lock_grid=lock,
    )

    payload = {
        "study": "E020",
        "title": "MFE-ratcheted trailing stop",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator_commit": _generator_commit(),
        "pre_registration": "experiments/E020_mfe_ratcheted_trail/PROTOCOL.md",
        "harness": "programs/_shared/counterfactual_replay/replay.py",
        "symbols": list(symbols),
        "per_symbol_meta": per_symbol_meta,
        "total_trades": len(all_trades),
        "results": results,
    }

    # Overall verdict roll-up.
    alives = [a for a in results["arms"] if a["verdict"] == "alive"]
    if alives:
        payload["study_verdict"] = "alive"
        payload["winning_arms"] = [a["arm_id"] for a in alives]
    elif any(a["verdict"] in ("parked_low_yield", "parked_capital_cost") for a in results["arms"]):
        parked = [
            (a["arm_id"], a["verdict"])
            for a in results["arms"]
            if a["verdict"].startswith("parked")
        ]
        payload["study_verdict"] = "parked"
        payload["parked_arms"] = parked
    else:
        payload["study_verdict"] = "dead"

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    log.info("Wrote %s", out)
    log.info("Study verdict: %s", payload["study_verdict"])
    if "winning_arms" in payload:
        log.info("Winning arms: %s", payload["winning_arms"])


def _generator_commit() -> str:
    import subprocess
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(_REPO_ROOT), stderr=subprocess.DEVNULL,
        ).decode().strip()
        return sha
    except Exception:
        return "unknown"


if __name__ == "__main__":
    main()
