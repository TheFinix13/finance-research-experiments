"""E024 Phase 2 stage-1 — near-TP stall exit, walk-forward validation.

Consumes the PRE-0 path-augmented ledgers for EURUSD/GBPUSD/USDCAD
(``programs/_shared/counterfactual_replay/data/{SYMBOL}_H4_paths.jsonl``)
via the shared replay engine. Sweeps the frozen 24-arm stage-1 grid
per PROTOCOL §4.1:

    activation_R ∈ {1.30, 1.40, 1.45}
    × { S1_wallclock × stall_secs ∈ {900, 1800, 3600, 14400}   (12 arms)
      , S2_h1_range                                            (3 arms)
      , S3_h1_reversal                                         (3 arms)
      , S4_bar_stall_h1                                        (3 arms)
      , S5_any_of_1-4 (stall_secs=3600 locked)                 (3 arms) }
    = 24 arms.

Scored per-symbol (PROTOCOL §5.4 — NOT pooled across symbols). BH-FDR
at α = 0.10 is applied within each symbol's 24 joint p-values. Stouffer's
Z (weights = √n_fold_trades) combines the 5 per-fold two-sided bootstrap
p-values into an arm-level joint p; Fisher's combined p is reported as
sensitivity.

Everything is pre-registered in
[`experiments/E024_near_tp_stall_exit/PROTOCOL.md`](../../experiments/E024_near_tp_stall_exit/PROTOCOL.md).
This file is the mechanical implementation — no post-hoc tuning.

CLI::

    PYTHONPATH=../multi-pair-trading-agent:.:scripts \\
        ../multi-pair-trading-agent/.venv/bin/python \\
        programs/E024/run_e024_validation.py \\
        --output programs/E024/results.json
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
from scipy.stats import chi2, norm

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from programs._shared.counterfactual_replay.replay import (  # noqa: E402
    PRIORITY_E024_STALL,
    TradeRecord,
    load_paths_ledger,
    replay,
)
from programs.E024.stall_signals import (  # noqa: E402
    SIGNAL_S1,
    SIGNAL_S5,
    E024StallRule,
    make_arm_grid,
)

log = logging.getLogger("E024")


# ---------------------------------------------------------------------------
# Frozen §4 grid (PROTOCOL §4.1).
# ---------------------------------------------------------------------------

SYMBOLS: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDCAD")
ACTIVATION_R_GRID: tuple[float, ...] = (1.30, 1.40, 1.45)
S1_STALL_SECS_GRID: tuple[float, ...] = (900.0, 1800.0, 3600.0, 14400.0)

BOOTSTRAP_SEED: int = 42
BOOTSTRAP_RESAMPLES: int = 5000
FDR_ALPHA: float = 0.10
JOINT_P_ALPHA: float = 0.05     # per PROTOCOL §6 leg 3 ("joint fold p < 0.05")
FALSE_POS_HEAVY_THRESHOLD: float = 0.50  # PROTOCOL §6 (H3) parked threshold

# Walk-forward folds mirror PRE-0 §3 / E004 exactly (identical to E020).
FOLDS: tuple[tuple[str, datetime, datetime], ...] = (
    ("fold1", datetime(2017, 1, 1, tzinfo=timezone.utc), datetime(2019, 1, 1, tzinfo=timezone.utc)),
    ("fold2", datetime(2019, 1, 1, tzinfo=timezone.utc), datetime(2021, 1, 1, tzinfo=timezone.utc)),
    ("fold3", datetime(2021, 1, 1, tzinfo=timezone.utc), datetime(2023, 1, 1, tzinfo=timezone.utc)),
    ("fold4", datetime(2023, 1, 1, tzinfo=timezone.utc), datetime(2024, 7, 1, tzinfo=timezone.utc)),
    ("fold5", datetime(2024, 7, 1, tzinfo=timezone.utc), datetime(2026, 1, 1, tzinfo=timezone.utc)),
)


# ---------------------------------------------------------------------------
# Metric helpers (Sharpe, paired bootstrap, tail-mean, Stouffer, BH-FDR).
# ---------------------------------------------------------------------------

def _sharpe(returns: Sequence[float]) -> float:
    """Sharpe on a per-trade R-sequence (no annualisation — the paired
    ΔSharpe uses the same n_trades on both sides, so annualisation cancels)."""
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

    Paired: resample indices once, apply to arm and baseline. Two-sided
    p-value uses the fraction of bootstrap deltas on the opposite side of
    zero from the point estimate (bootstrap-standard, matches E020)."""
    arm = np.asarray(r_arm, dtype=float)
    base = np.asarray(r_base, dtype=float)
    assert arm.shape == base.shape, "paired arrays must have equal length"
    n = arm.size
    if n < 2:
        return float("nan"), float("nan"), float("nan"), float("nan")

    point = _paired_delta_sharpe(arm, base)
    if not np.isfinite(point):
        return point, float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    deltas = np.empty(resamples, dtype=float)
    for k in range(resamples):
        idx = rng.integers(0, n, size=n)
        deltas[k] = _paired_delta_sharpe(arm[idx], base[idx])

    lo = float(np.quantile(deltas, alpha / 2))
    hi = float(np.quantile(deltas, 1 - alpha / 2))

    if point >= 0:
        p_two = 2.0 * float(np.mean(deltas <= 0))
    else:
        p_two = 2.0 * float(np.mean(deltas >= 0))
    p_two = min(p_two, 1.0)
    return point, lo, hi, p_two


def _bh_fdr(p_values: Sequence[float], alpha: float = FDR_ALPHA) -> list[bool]:
    """Benjamini–Hochberg. Returns list of booleans (True = reject H0)."""
    p = np.asarray(p_values, dtype=float)
    m = p.size
    order = np.argsort(p)
    thresholds = (np.arange(1, m + 1) / m) * alpha
    p_sorted = p[order]
    passed_sorted = p_sorted <= thresholds
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


def _stouffer_combine(
    p_values: Sequence[Optional[float]],
    deltas: Sequence[Optional[float]],
    weights: Sequence[float],
) -> tuple[Optional[float], Optional[float]]:
    """Signed Stouffer's Z with per-fold weights.

    Convention (documented in the return message):
        z_i = sign(Δ_i) · Φ⁻¹(1 − p_i / 2)
        Z   = Σ w_i · z_i / √Σ w_i²
        joint_p = 2 · (1 − Φ(|Z|))

    Folds with p None (empty or too-thin) are skipped."""
    zs: list[float] = []
    ws: list[float] = []
    for p, d, w in zip(p_values, deltas, weights):
        if p is None or d is None or not np.isfinite(p) or not np.isfinite(d) or w <= 0:
            continue
        p_clipped = float(min(max(p, 1e-16), 1.0 - 1e-16))
        z_mag = float(norm.isf(p_clipped / 2))
        sign = 1.0 if d > 0 else (-1.0 if d < 0 else 0.0)
        zs.append(sign * z_mag)
        ws.append(float(w))
    if not zs:
        return None, None
    zs_arr = np.asarray(zs)
    ws_arr = np.asarray(ws)
    z_combined = float(np.sum(ws_arr * zs_arr) / np.sqrt(np.sum(ws_arr ** 2)))
    p_joint = float(2.0 * (1.0 - norm.cdf(abs(z_combined))))
    return z_combined, p_joint


def _fisher_combine(p_values: Sequence[Optional[float]]) -> Optional[float]:
    """Fisher's combined χ² test on per-fold two-sided p-values (sensitivity
    against Stouffer; unsigned)."""
    ps = [float(p) for p in p_values if p is not None and np.isfinite(p)]
    if not ps:
        return None
    stat = -2.0 * float(np.sum(np.log(np.clip(ps, 1e-16, 1.0))))
    df = 2 * len(ps)
    return float(1.0 - chi2.cdf(stat, df))


def _tail_mean(rs: Sequence[float], q: float = 0.10) -> float:
    """Mean of the worst-q fraction of the R-sequence (matches E020)."""
    arr = np.sort(np.asarray(rs, dtype=float))
    if arr.size == 0:
        return float("nan")
    k = max(1, int(arr.size * q))
    return float(arr[:k].mean())


# ---------------------------------------------------------------------------
# Fold assignment.
# ---------------------------------------------------------------------------

def _fold_of(entry_time: datetime, folds=FOLDS) -> Optional[str]:
    for name, s, e in folds:
        if s <= entry_time < e:
            return name
    return None


# ---------------------------------------------------------------------------
# Path-resolution audit.
# ---------------------------------------------------------------------------

def _path_resolution_audit(trades: Sequence[TradeRecord]) -> dict:
    """Per-fold, per-resolution counts. Used for the low-fidelity flag."""
    by_fold: dict[str, Counter] = {name: Counter() for name, _, _ in FOLDS}
    by_fold["unassigned"] = Counter()
    for t in trades:
        f = _fold_of(t.entry_time) or "unassigned"
        by_fold[f][t.path_resolution] += 1
    return {fname: dict(counter) for fname, counter in by_fold.items() if counter}


# ---------------------------------------------------------------------------
# Sweep for one symbol.
# ---------------------------------------------------------------------------

def _run_arm_single_trade(
    trade: TradeRecord,
    rule: E024StallRule,
) -> tuple[float, Optional[dict], str]:
    """Replay one trade under one arm. Returns (arm_r, fire_details, alt_exit_reason)."""
    rule.reset()
    alt = replay(trade, rule=rule)
    fd = rule.fired_details
    if fd is not None:
        fire_details = {
            "sub_signal": fd.sub_signal,
            "bar_index": fd.bar_index,
            "bar_time": fd.bar_time.isoformat(),
            "fire_price": fd.fire_price,
            "mfe_r_at_fire": fd.mfe_r_at_fire,
            "mfe_pips_at_fire": fd.mfe_pips_at_fire,
            "elapsed_since_mfe_ts_s": fd.elapsed_since_mfe_ts,
            "h1_no_extend_count": fd.h1_no_extend_count,
        }
    else:
        fire_details = None
    return alt.r, fire_details, alt.exit_reason


def _run_arm(
    trades: list[TradeRecord],
    activation_r: float,
    signal: str,
    stall_secs: Optional[float],
) -> tuple[list[float], list[Optional[dict]], list[str]]:
    """Run one arm across all input trades. Returns paired arm_R, per-trade
    fire_details (None if didn't fire), and per-trade alt-exit-reason."""
    rule = E024StallRule(activation_r=activation_r, signal=signal, stall_secs=stall_secs)
    arm_R: list[float] = []
    fires: list[Optional[dict]] = []
    alt_reasons: list[str] = []
    for t in trades:
        r, fd, alt_reason = _run_arm_single_trade(t, rule)
        arm_R.append(r)
        fires.append(fd)
        alt_reasons.append(alt_reason)
    return arm_R, fires, alt_reasons


def _classify_arm(
    per_fold_positive_flags: list[bool],
    pooled_ci_low: float,
    joint_p_stouffer: Optional[float],
    bh_rejected: bool,
    delta_p_false_positive: float,
    pooled_delta_sharpe: float,
) -> str:
    """PROTOCOL §6 verdict rules, applied per (arm, symbol)."""
    n_pos = sum(per_fold_positive_flags)
    # Primary criteria for 'alive'.
    alive_primary = pooled_ci_low > 0
    alive_robust = n_pos >= 4
    alive_joint_sig = joint_p_stouffer is not None and joint_p_stouffer < JOINT_P_ALPHA
    alive_all = alive_primary and alive_robust and alive_joint_sig and bh_rejected

    if alive_all and delta_p_false_positive > FALSE_POS_HEAVY_THRESHOLD:
        return "parked_false_positive_heavy"
    if alive_all:
        return "alive"

    # Parked low-yield: point positive with CI including 0, OR fold-positive-in-3.
    ci_includes_zero = pooled_ci_low <= 0
    point_positive = pooled_delta_sharpe > 0
    if point_positive and (ci_includes_zero or n_pos == 3):
        return "parked_low_yield"

    return "dead"


def _sweep_symbol(
    symbol: str,
    trades: list[TradeRecord],
    grid: list[dict],
    folds=FOLDS,
    seed: int = BOOTSTRAP_SEED,
    resamples: int = BOOTSTRAP_RESAMPLES,
    fdr_alpha: float = FDR_ALPHA,
    log_progress_every: int = 3,
) -> dict:
    """Sweep one symbol across the 24-arm grid. Returns a JSON-ready dict.

    Per-symbol BH-FDR (PROTOCOL §5.4) — 24 joint p-values corrected within
    this symbol's family, not pooled across symbols.
    """
    fold_ids = [_fold_of(t.entry_time, folds) for t in trades]

    # Baseline R sequence is trade.r (invariant §4.1: null rule reproduces).
    base_R_all = [t.r for t in trades]

    arms_out: list[dict] = []
    per_arm_joint_p: list[float] = []

    for i_arm, arm in enumerate(grid):
        a = arm["activation_r"]
        sig = arm["signal"]
        secs = arm["stall_secs"]
        arm_R_all, fires, alt_reasons = _run_arm(trades, a, sig, secs)

        per_fold: list[dict] = []
        per_fold_flags: list[bool] = []
        per_fold_p: list[Optional[float]] = []
        per_fold_delta: list[Optional[float]] = []
        per_fold_weights: list[float] = []

        for fname, fs, fe in folds:
            arm_fold = [r for r, fid in zip(arm_R_all, fold_ids) if fid == fname]
            base_fold = [r for r, fid in zip(base_R_all, fold_ids) if fid == fname]
            if len(arm_fold) < 2:
                per_fold.append({
                    "fold": fname,
                    "n_trades": len(arm_fold),
                    "delta_sharpe": None,
                    "ci_low": None,
                    "ci_high": None,
                    "p_two_sided": None,
                    "sharpe_arm": None,
                    "sharpe_base": None,
                    "mean_delta_r": None,
                })
                per_fold_flags.append(False)
                per_fold_p.append(None)
                per_fold_delta.append(None)
                per_fold_weights.append(0.0)
                continue

            point, lo, hi, p_two = _paired_bootstrap_ci(
                arm_fold, base_fold, seed=seed, resamples=resamples,
            )
            per_fold.append({
                "fold": fname,
                "n_trades": len(arm_fold),
                "delta_sharpe": round(point, 4),
                "ci_low": round(lo, 4),
                "ci_high": round(hi, 4),
                "p_two_sided": round(p_two, 4),
                "sharpe_arm": round(_sharpe(arm_fold), 4),
                "sharpe_base": round(_sharpe(base_fold), 4),
                "mean_delta_r": round(
                    float(np.mean(np.array(arm_fold) - np.array(base_fold))), 4
                ),
            })
            per_fold_flags.append(point > 0)
            per_fold_p.append(p_two)
            per_fold_delta.append(point)
            per_fold_weights.append(float(np.sqrt(len(arm_fold))))

        # Stouffer + Fisher combined joint p over the 5 folds.
        z_stouffer, p_stouffer = _stouffer_combine(per_fold_p, per_fold_delta, per_fold_weights)
        p_fisher = _fisher_combine(per_fold_p)

        # Pooled per-symbol Δ Sharpe on all-fold trades within this symbol.
        arm_R_arr = np.array(arm_R_all, dtype=float)
        base_R_arr = np.array(base_R_all, dtype=float)
        pooled_delta_r = arm_R_arr - base_R_arr
        pooled_point, pooled_lo, pooled_hi, pooled_p = _paired_bootstrap_ci(
            arm_R_arr, base_R_arr, seed=seed, resamples=resamples,
        )

        # Fire diagnostics.
        n_trades = len(trades)
        n_fires = sum(1 for r in alt_reasons if r == PRIORITY_E024_STALL)
        n_fires_on_tp = sum(
            1 for r, t in zip(alt_reasons, trades)
            if r == PRIORITY_E024_STALL and t.exit_reason == "tp"
        )
        n_worse_than_stall = sum(
            1 for r, alt_r, t in zip(alt_reasons, arm_R_all, trades)
            if r == PRIORITY_E024_STALL and t.r < alt_r
        )
        # Δ P(fire) — baseline never fires so this is just the arm rate.
        delta_p_fire = n_fires / n_trades if n_trades else 0.0
        delta_p_false_pos = n_fires_on_tp / n_fires if n_fires > 0 else 0.0
        delta_p_worse_than_stall = n_worse_than_stall / n_fires if n_fires > 0 else 0.0

        # Sub-signal firing breakdown (S5 fires via S1/S2/S3/S4 legs).
        sub_signal_hist = Counter(
            fd["sub_signal"] for fd in fires if fd is not None
        )

        # Near-miss cohort (trades whose original mfe_r ≥ activation_R).
        cohort_mask = [t.mfe_r >= a for t in trades]
        cohort_arm = [r for r, m in zip(arm_R_all, cohort_mask) if m]
        cohort_base = [r for r, m in zip(base_R_all, cohort_mask) if m]
        cohort_n = sum(cohort_mask)
        delta_mean_r_cohort = (
            float(np.mean(np.array(cohort_arm) - np.array(cohort_base)))
            if cohort_n > 0 else 0.0
        )

        # Tail-mean R (worst 10 %).
        tail_arm = _tail_mean(arm_R_arr, q=0.10)
        tail_base = _tail_mean(base_R_arr, q=0.10)

        # Path-resolution histogram over trades this arm was applied to
        # (all trades; some are low-fidelity for H1-based signals).
        low_fidelity = sig != SIGNAL_S1 and any(
            t.path_resolution == "H4" for t in trades
        )
        path_res_hist = dict(Counter(t.path_resolution for t in trades))

        bh_rejected_placeholder = None  # populated after per-symbol BH loop.

        arm_out = {
            "arm_id": arm["arm_id"],
            "activation_R": a,
            "signal": sig,
            "stall_secs": secs,
            "n_trades": n_trades,
            "per_fold": per_fold,
            "fold_positive_flags": per_fold_flags,
            "n_folds_positive": sum(per_fold_flags),
            "joint_p_stouffer": (round(p_stouffer, 6) if p_stouffer is not None else None),
            "joint_z_stouffer": (round(z_stouffer, 4) if z_stouffer is not None else None),
            "joint_p_fisher": (round(p_fisher, 6) if p_fisher is not None else None),
            "pooled": {
                "delta_sharpe": round(pooled_point, 4),
                "ci_low": round(pooled_lo, 4),
                "ci_high": round(pooled_hi, 4),
                "p_two_sided": round(pooled_p, 4),
                "sharpe_arm": round(_sharpe(arm_R_arr), 4),
                "sharpe_base": round(_sharpe(base_R_arr), 4),
                "mean_delta_r": round(float(pooled_delta_r.mean()), 4),
                "median_delta_r": round(float(np.median(pooled_delta_r)), 4),
                "tail_arm_worst10": round(tail_arm, 4),
                "tail_base_worst10": round(tail_base, 4),
                "delta_tail_worst10": round(tail_arm - tail_base, 4),
            },
            "fire_diagnostics": {
                "n_fires": n_fires,
                "n_fires_on_tp": n_fires_on_tp,
                "n_worse_than_stall": n_worse_than_stall,
                "delta_p_fire": round(delta_p_fire, 4),
                "delta_p_false_positive": round(delta_p_false_pos, 4),
                "delta_p_worse_than_stall": round(delta_p_worse_than_stall, 4),
                "sub_signal_fire_histogram": dict(sub_signal_hist),
            },
            "near_miss_cohort": {
                "n": cohort_n,
                "delta_mean_r": round(delta_mean_r_cohort, 4),
                "mean_r_arm": round(float(np.mean(cohort_arm)), 4) if cohort_n else None,
                "mean_r_base": round(float(np.mean(cohort_base)), 4) if cohort_n else None,
            },
            "low_fidelity_flag": bool(low_fidelity),
            "path_resolution_histogram_this_symbol": path_res_hist,
            "bh_fdr_rejected": bh_rejected_placeholder,
            "verdict": None,
        }
        arms_out.append(arm_out)
        per_arm_joint_p.append(
            p_stouffer if p_stouffer is not None else 1.0
        )

        if log_progress_every > 0 and (i_arm + 1) % log_progress_every == 0:
            log.info(
                "  [%s] arm %d/%d %s ΔSharpe=%.4f CI=[%.4f, %.4f] p=%.4f fires=%d",
                symbol, i_arm + 1, len(grid), arm["arm_id"],
                pooled_point, pooled_lo, pooled_hi,
                p_stouffer if p_stouffer is not None else float("nan"),
                n_fires,
            )

    # BH-FDR at α = 0.10 across this symbol's 24 arms.
    fdr_rejected = _bh_fdr(per_arm_joint_p, alpha=fdr_alpha)
    for arm, rej in zip(arms_out, fdr_rejected):
        arm["bh_fdr_rejected"] = bool(rej)

    # Per-arm verdict.
    for arm in arms_out:
        arm["verdict"] = _classify_arm(
            per_fold_positive_flags=arm["fold_positive_flags"],
            pooled_ci_low=arm["pooled"]["ci_low"],
            joint_p_stouffer=arm["joint_p_stouffer"],
            bh_rejected=arm["bh_fdr_rejected"],
            delta_p_false_positive=arm["fire_diagnostics"]["delta_p_false_positive"],
            pooled_delta_sharpe=arm["pooled"]["delta_sharpe"],
        )

    verdict_counts = Counter(arm["verdict"] for arm in arms_out)
    return {
        "symbol": symbol,
        "n_trades": len(trades),
        "path_resolution_by_fold": _path_resolution_audit(trades),
        "arms": arms_out,
        "verdict_counts": dict(verdict_counts),
        "fdr": {
            "method": "BH",
            "alpha": fdr_alpha,
            "family_size": len(arms_out),
        },
    }


# ---------------------------------------------------------------------------
# Study-level roll-up (PROTOCOL §6).
# ---------------------------------------------------------------------------

def _study_verdict(per_symbol_results: list[dict]) -> str:
    """`alive` if any (arm, symbol) is alive; else `parked_false_positive_heavy`
    if any exists; else `parked_low_yield` if any exists; else `dead`."""
    verdicts = [
        a["verdict"] for sym in per_symbol_results for a in sym["arms"]
    ]
    if "alive" in verdicts:
        return "alive"
    if "parked_false_positive_heavy" in verdicts:
        return "parked_false_positive_heavy"
    if "parked_low_yield" in verdicts:
        return "parked_low_yield"
    return "dead"


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="programs/E024/results.json")
    parser.add_argument("--data-dir", default=None,
                        help="Override PRE-0 data dir (defaults to package location)")
    parser.add_argument("--symbols", default=",".join(SYMBOLS))
    parser.add_argument("--smoke-only-first-arm", action="store_true",
                        help="Only evaluate the first arm — for interface smoke tests")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    log.info("E024 Phase 2 stage-1 — near-TP stall exit validation")
    grid = make_arm_grid(ACTIVATION_R_GRID, S1_STALL_SECS_GRID)
    if args.smoke_only_first_arm:
        grid = grid[:1]
    log.info("Grid: %d arms (activation_R=%s × {S1×%d, S2, S3, S4, S5})",
             len(grid), ACTIVATION_R_GRID, len(S1_STALL_SECS_GRID))

    symbols = tuple(s.strip() for s in args.symbols.split(","))
    kwargs = {"data_dir": args.data_dir} if args.data_dir else {}

    per_symbol_meta: dict[str, dict] = {}
    per_symbol_trades: dict[str, list[TradeRecord]] = {}
    for sym in symbols:
        meta, trades = load_paths_ledger(sym, **kwargs)
        per_symbol_meta[sym] = meta
        per_symbol_trades[sym] = trades
        log.info("  loaded %s: %d trades, hit_rate=%.4f, mean_r=%.4f",
                 sym, len(trades), meta.get("hit_rate", -1), meta.get("mean_r", -1))

    per_symbol_results: list[dict] = []
    for sym in symbols:
        log.info("Sweeping %s (%d trades × %d arms) ...",
                 sym, len(per_symbol_trades[sym]), len(grid))
        sym_result = _sweep_symbol(
            sym, per_symbol_trades[sym], grid,
        )
        per_symbol_results.append(sym_result)
        log.info(
            "  %s verdict counts: %s",
            sym, sym_result["verdict_counts"],
        )

    payload = {
        "study": "E024",
        "title": "Near-TP stall exit (stage 1)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator_commit": _generator_commit(),
        "pre_registration": "experiments/E024_near_tp_stall_exit/PROTOCOL.md",
        "harness": "programs/_shared/counterfactual_replay/replay.py",
        "symbols": list(symbols),
        "per_symbol_meta": per_symbol_meta,
        "grid": {
            "activation_R": list(ACTIVATION_R_GRID),
            "S1_stall_secs": list(S1_STALL_SECS_GRID),
            "S5_locked_stall_secs": 3600.0,
            "n_arms": len(grid),
            "signals": [
                "S1_wallclock", "S2_h1_range", "S3_h1_reversal",
                "S4_bar_stall_h1", "S5_any_of_1-4",
            ],
        },
        "folds": [
            {"name": n, "start": s.isoformat(), "end": e.isoformat()}
            for n, s, e in FOLDS
        ],
        "bootstrap": {
            "seed": BOOTSTRAP_SEED,
            "resamples": BOOTSTRAP_RESAMPLES,
        },
        "fdr": {
            "method": "BH",
            "alpha": FDR_ALPHA,
            "family_size_per_symbol": len(grid),
            "note": "Applied per-symbol (PROTOCOL §5.4), not pooled across symbols.",
        },
        "stouffer_convention": (
            "z_i = sign(delta_i) * norm.isf(p_i / 2); "
            "Z = sum(w_i * z_i) / sqrt(sum(w_i^2)); "
            "w_i = sqrt(n_fold_trades); joint_p = 2 * (1 - Phi(|Z|)). "
            "Fisher's combined p reported as sensitivity."
        ),
        "per_symbol": per_symbol_results,
    }
    payload["study_verdict"] = _study_verdict(per_symbol_results)

    # Stage-2 authorisation status.
    alive_arms = [
        {"symbol": sym["symbol"], "arm_id": a["arm_id"], "verdict": a["verdict"]}
        for sym in per_symbol_results for a in sym["arms"]
        if a["verdict"] == "alive"
    ]
    parked_fp_heavy = [
        {"symbol": sym["symbol"], "arm_id": a["arm_id"],
         "delta_p_false_positive": a["fire_diagnostics"]["delta_p_false_positive"]}
        for sym in per_symbol_results for a in sym["arms"]
        if a["verdict"] == "parked_false_positive_heavy"
    ]
    payload["alive_arms"] = alive_arms
    payload["parked_false_positive_heavy_arms"] = parked_fp_heavy
    payload["stage_2_authorised"] = bool(alive_arms)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    log.info("Wrote %s", out)
    log.info("Study verdict: %s", payload["study_verdict"])
    if alive_arms:
        log.info("Alive arms: %s", alive_arms)
    if parked_fp_heavy:
        log.info("Parked FP-heavy arms: %s", parked_fp_heavy)


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
