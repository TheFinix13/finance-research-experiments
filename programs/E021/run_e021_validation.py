"""E021 Phase 2 — Partial exit at fixed-R milestone, walk-forward validation.

Consumes the PRE-0 path-augmented ledgers for EURUSD/GBPUSD/USDCAD
(``programs/_shared/counterfactual_replay/data/{SYMBOL}_H4_paths.jsonl``)
via the shared replay engine. Sweeps the 9-arm frozen grid
``partial_R ∈ {0.7, 1.0, 1.3} × partial_fraction ∈ {0.25, 0.4, 0.5}``
and produces per-fold + pooled ΔSharpe statistics with paired bootstrap
95 % CIs and BH-FDR correction.

Everything is pre-registered in
[`experiments/E021_partial_exit_at_r_milestone/PROTOCOL.md`](../../experiments/E021_partial_exit_at_r_milestone/PROTOCOL.md).
This file is the mechanical implementation — no post-hoc tuning.

The verdict registry (PROTOCOL §6) has four labels:

    - ``alive``: CI-LB > 0 AND positive-in-≥4/5 folds AND BH-FDR-adjusted
      p < 0.05 AND secondary guardrails not materially degraded.
    - ``parked_low_yield``: point ΔSharpe > 0 but CI includes 0 or
      positive-in-only-3-folds.
    - ``parked_lower_variance_lower_return`` (H2 SPECIAL): Δ variance of R
      statistically negative (CI-UB < 0) AND ΔSharpe CI includes 0 —
      retained for the E025 joint-stack candidate set.
    - ``dead``: none of the above.

CLI::

    PYTHONPATH=../multi-pair-trading-agent:.:scripts \\
        ../multi-pair-trading-agent/.venv/bin/python \\
        programs/E021/run_e021_validation.py \\
        --output programs/E021/results.json
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
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
    PRIORITY_E021_PARTIAL,
    TradeRecord,
    TradeState,
    load_paths_ledger,
    replay,
)

log = logging.getLogger("E021")


# ---------------------------------------------------------------------------
# Frozen §4 grid.
# ---------------------------------------------------------------------------

SYMBOLS: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDCAD")
PARTIAL_R_GRID: tuple[float, ...] = (0.7, 1.0, 1.3)
PARTIAL_FRACTION_GRID: tuple[float, ...] = (0.25, 0.4, 0.5)
BOOTSTRAP_SEED: int = 42
BOOTSTRAP_RESAMPLES: int = 5000
FDR_ALPHA: float = 0.10

# Guardrail loose-bands (PROTOCOL §5.3 — matches E020's loose sanity bands).
GUARDRAIL_MIN_DELTA_MEAN_R: float = -0.05
GUARDRAIL_MIN_DELTA_P_RESCUE: float = -0.05
GUARDRAIL_MIN_DELTA_TAIL_WORST10: float = -0.10

# Walk-forward folds (SPEC §3, mirrors E004 / E020).
FOLDS: tuple[tuple[str, datetime, datetime], ...] = (
    ("fold1", datetime(2017, 1, 1, tzinfo=timezone.utc), datetime(2019, 1, 1, tzinfo=timezone.utc)),
    ("fold2", datetime(2019, 1, 1, tzinfo=timezone.utc), datetime(2021, 1, 1, tzinfo=timezone.utc)),
    ("fold3", datetime(2021, 1, 1, tzinfo=timezone.utc), datetime(2023, 1, 1, tzinfo=timezone.utc)),
    ("fold4", datetime(2023, 1, 1, tzinfo=timezone.utc), datetime(2024, 7, 1, tzinfo=timezone.utc)),
    ("fold5", datetime(2024, 7, 1, tzinfo=timezone.utc), datetime(2026, 1, 1, tzinfo=timezone.utc)),
)


# ---------------------------------------------------------------------------
# Rule factory (PROTOCOL §3).
# ---------------------------------------------------------------------------

def make_e021_rule(partial_R: float, partial_fraction: float) -> Callable[[TradeState, Bar], Optional[ExitAction]]:
    """Return the E021 partial-exit rule for a given ``(partial_R, partial_fraction)`` arm.

    PROTOCOL §3.1 trigger: on any bar where the favorable excursion in R
    (``state.mfe_r_so_far`` — equals ``mfe_pips_so_far / stop_pips``) is at
    or above ``partial_R``, AND the partial has not yet fired on this
    trade (``state.remaining_fraction`` is still ~1.0), emit a
    ``partial_close`` action.

    PROTOCOL §3.2 fill: fill at the trigger price
    ``entry + d · partial_R · stop_pips · PIP``. This is the touch-fill
    convention — a wick that reaches through the trigger fills AT the
    trigger, regardless of the bar's high/low.

    Reversal-guard (PROTOCOL §3.4) is enforced by the engine's exit-priority
    ordering (SPEC §4.3): ``hard_sl → e024_stall → e021_partial → tp → …``.
    A hard SL that fires on the same bar as the partial trigger pre-empts
    the partial. This rule does NOT re-implement the guard.

    Null-rule invariant (PROTOCOL §3.5 §5.1): if ``partial_R`` is very large
    (e.g. 100.0), no trade's ``mfe_r_so_far`` ever crosses it, no partial
    fires, and the engine's fall-back path (bars exhausted with no
    rule-driven exit) returns the ORIGINAL exit byte-for-byte — so
    ``alt.r == trade.r`` for all trades. Unit-tested in
    ``tests/test_e021_rule.py::test_null_partial_is_identity``.
    """
    def rule(state: TradeState, bar: Bar) -> Optional[ExitAction]:
        if state.remaining_fraction < 1.0 - 1e-9:
            return None
        if state.mfe_r_so_far < partial_R:
            return None
        trigger_price = state.entry + state.direction * partial_R * state.stop_pips * PIP
        return ExitAction(
            kind="partial_close",
            fraction=partial_fraction,
            price=trigger_price,
            reason=PRIORITY_E021_PARTIAL,
        )
    return rule


# ---------------------------------------------------------------------------
# Metric helpers.
# ---------------------------------------------------------------------------

def _sharpe(returns: Sequence[float]) -> float:
    """Sharpe on a per-trade R-sequence (no annualisation — same convention
    as the paired ΔSharpe: both sides use the same n_trades, so
    annualisation factors cancel in the delta)."""
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

    if point >= 0:
        p_two = 2.0 * float(np.mean(deltas <= 0))
    else:
        p_two = 2.0 * float(np.mean(deltas >= 0))
    p_two = min(p_two, 1.0)
    return point, lo, hi, p_two


def _paired_bootstrap_variance_delta(
    r_arm: Sequence[float],
    r_base: Sequence[float],
    seed: int = BOOTSTRAP_SEED,
    resamples: int = BOOTSTRAP_RESAMPLES,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """Return (delta_variance_point, ci_low, ci_high) — the H2 special-case
    observable. Δ variance is ``var(arm) − var(base)``; ``CI-UB < 0`` is
    the H2 trigger.

    Paired bootstrap over the same seed as ΔSharpe, so the two CIs are
    directly comparable (SPEC §4.5 determinism)."""
    arm = np.asarray(r_arm, dtype=float)
    base = np.asarray(r_base, dtype=float)
    assert arm.shape == base.shape
    n = arm.size
    if n < 2:
        return float("nan"), float("nan"), float("nan")
    point = float(arm.var(ddof=1) - base.var(ddof=1))
    rng = np.random.default_rng(seed)
    dv = np.empty(resamples, dtype=float)
    for k in range(resamples):
        idx = rng.integers(0, n, size=n)
        dv[k] = arm[idx].var(ddof=1) - base[idx].var(ddof=1)
    lo = float(np.quantile(dv, alpha / 2))
    hi = float(np.quantile(dv, 1 - alpha / 2))
    return point, lo, hi


def _bh_fdr(p_values: Sequence[float], alpha: float = FDR_ALPHA) -> list[bool]:
    """Benjamini–Hochberg FDR. Returns list of booleans (True = reject H0).

    Also returns per-p adjusted p-values via ``_bh_adjusted_p`` below for
    the alive-classifier's ``BH-adjusted p < 0.05`` gate (PROTOCOL §5.3)."""
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


def _bh_adjusted_p(p_values: Sequence[float]) -> list[float]:
    """Return the BH-adjusted p-values (one per input, aligned).

    Standard BH monotone step-up: ``p_adj_(i) = min_{k ≥ i} (m/k) · p_(k)``,
    clipped to [0, 1]. Used for the alive-classifier's per-arm
    ``BH-adjusted p < 0.05`` gate (PROTOCOL §5.3)."""
    p = np.asarray(p_values, dtype=float)
    m = p.size
    order = np.argsort(p)
    p_sorted = p[order]
    adj_sorted = np.empty(m, dtype=float)
    running_min = 1.0
    for k in range(m - 1, -1, -1):
        rank = k + 1
        val = (m / rank) * p_sorted[k]
        running_min = min(running_min, val)
        adj_sorted[k] = min(1.0, running_min)
    adj = np.empty(m, dtype=float)
    adj[order] = adj_sorted
    return adj.tolist()


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
# Per-trade replay collector.
# ---------------------------------------------------------------------------

def _run_arm_all_trades(
    trades: list[TradeRecord],
    rule: Callable[[TradeState, Bar], Optional[ExitAction]],
) -> tuple[list[float], list[float], list[bool]]:
    """Return (arm_R, base_R, partial_fired_mask) triples across all trades.

    ``partial_fired_mask[i]`` is True iff at least one ``partial_close``
    fill was booked for trade i under this arm — used by the fire-rate
    diagnostic and by the "P(alt_r > 0 | partial fired)" guardrail
    (PROTOCOL §5.2 secondary #2)."""
    arm_R: list[float] = []
    base_R: list[float] = []
    fired: list[bool] = []
    for t in trades:
        alt = replay(t, rule=rule)
        arm_R.append(alt.r)
        base_R.append(t.r)
        fired.append(any(f.reason == PRIORITY_E021_PARTIAL for f in alt.fills))
    return arm_R, base_R, fired


# ---------------------------------------------------------------------------
# Sweep engine.
# ---------------------------------------------------------------------------

def sweep(
    trades: list[TradeRecord],
    partial_r_grid: Sequence[float] = PARTIAL_R_GRID,
    partial_fraction_grid: Sequence[float] = PARTIAL_FRACTION_GRID,
    folds: Sequence[tuple[str, datetime, datetime]] = FOLDS,
    seed: int = BOOTSTRAP_SEED,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> dict:
    """Full 9-arm × 5-fold sweep over the pooled trade population.

    Returns a JSON-ready dict with per-arm per-fold + pooled metrics,
    guardrails, mechanism diagnostics (fire-rate, mean R of fired cohort,
    Δ P(alt_r > 0 | fired)), and BH-FDR verdicts."""
    fold_ids = [_fold_of(t.entry_time, folds) for t in trades]
    symbol_ids = [t.symbol for t in trades]

    arms_out: list[dict] = []
    pooled_p_values: list[float] = []

    for pr in partial_r_grid:
        for pf in partial_fraction_grid:
            rule = make_e021_rule(pr, pf)
            log.info(
                "arm (partial_R=%.2f, partial_fraction=%.2f): replaying %d trades ...",
                pr, pf, len(trades),
            )
            arm_R_all, base_R_all, fired_all = _run_arm_all_trades(trades, rule)
            arm_arr = np.asarray(arm_R_all, dtype=float)
            base_arr = np.asarray(base_R_all, dtype=float)
            fired_arr = np.asarray(fired_all, dtype=bool)

            # Per-fold pass.
            per_fold: list[dict] = []
            fold_positive_flags: list[bool] = []
            for fname, _fs, _fe in folds:
                mask = np.asarray([fid == fname for fid in fold_ids], dtype=bool)
                arm_fold = arm_arr[mask]
                base_fold = base_arr[mask]
                if arm_fold.size == 0:
                    per_fold.append({
                        "fold": fname, "n_trades": 0,
                        "delta_sharpe": None, "ci_low": None, "ci_high": None,
                        "p_two_sided": None,
                        "sharpe_arm": None, "sharpe_base": None,
                        "mean_delta_r": None,
                        "n_partial_fired": 0,
                    })
                    fold_positive_flags.append(False)
                    continue
                point, lo, hi, p = _paired_bootstrap_ci(
                    arm_fold, base_fold, seed=seed, resamples=resamples,
                )
                per_fold.append({
                    "fold": fname,
                    "n_trades": int(arm_fold.size),
                    "delta_sharpe": round(point, 4),
                    "ci_low": round(lo, 4),
                    "ci_high": round(hi, 4),
                    "p_two_sided": round(p, 4),
                    "sharpe_arm": round(_sharpe(arm_fold), 4),
                    "sharpe_base": round(_sharpe(base_fold), 4),
                    "mean_delta_r": round(float((arm_fold - base_fold).mean()), 4),
                    "n_partial_fired": int(fired_arr[mask].sum()),
                })
                fold_positive_flags.append(point > 0)

            # Pooled pass (primary).
            pooled_delta_r = arm_arr - base_arr
            pooled_point, pooled_lo, pooled_hi, pooled_p = _paired_bootstrap_ci(
                arm_arr, base_arr, seed=seed, resamples=resamples,
            )

            # Δ variance of R (H2 special-case observable, PROTOCOL §5.2 #4).
            dv_point, dv_lo, dv_hi = _paired_bootstrap_variance_delta(
                arm_arr, base_arr, seed=seed, resamples=resamples,
            )

            # Guardrail: Δ tail-mean R worst 10 %.
            tail_arm = _tail_mean(arm_arr, q=0.10)
            tail_base = _tail_mean(base_arr, q=0.10)
            delta_tail = tail_arm - tail_base

            # Fire-rate diagnostic (PROTOCOL §5.5 trigger-rate).
            n_fired = int(fired_arr.sum())
            fire_rate = float(n_fired / arm_arr.size) if arm_arr.size else 0.0

            # Fired-cohort mechanism: Δ mean R of the fired subset, and the
            # "rescue" delta P(alt_r > 0 | partial fired) − P(baseline_r > 0
            # | partial fired). Positive rescue delta = partial converted
            # more losers into winners than it turned would-be winners into
            # break-evens.
            if n_fired > 0:
                arm_fired = arm_arr[fired_arr]
                base_fired = base_arr[fired_arr]
                mean_arm_fired = float(arm_fired.mean())
                mean_base_fired = float(base_fired.mean())
                delta_mean_fired = mean_arm_fired - mean_base_fired
                p_arm_pos_on_fired = float((arm_fired > 0).mean())
                p_base_pos_on_fired = float((base_fired > 0).mean())
                delta_p_rescue = p_arm_pos_on_fired - p_base_pos_on_fired
            else:
                mean_arm_fired = float("nan")
                mean_base_fired = float("nan")
                delta_mean_fired = float("nan")
                p_arm_pos_on_fired = float("nan")
                p_base_pos_on_fired = float("nan")
                delta_p_rescue = float("nan")

            # Per-symbol stratified ΔSharpe (PROTOCOL §5.5 diagnostic).
            per_symbol_diag: dict[str, dict] = {}
            for sym in sorted(set(symbol_ids)):
                sym_mask = np.asarray([s == sym for s in symbol_ids], dtype=bool)
                arm_sym = arm_arr[sym_mask]
                base_sym = base_arr[sym_mask]
                if arm_sym.size < 2:
                    per_symbol_diag[sym] = {"n_trades": int(arm_sym.size)}
                    continue
                per_symbol_diag[sym] = {
                    "n_trades": int(arm_sym.size),
                    "sharpe_arm": round(_sharpe(arm_sym), 4),
                    "sharpe_base": round(_sharpe(base_sym), 4),
                    "delta_sharpe": round(_sharpe(arm_sym) - _sharpe(base_sym), 4),
                    "mean_delta_r": round(float((arm_sym - base_sym).mean()), 4),
                    "n_partial_fired": int(fired_arr[sym_mask].sum()),
                    "fire_rate": round(float(fired_arr[sym_mask].mean()), 4),
                }

            arm_out = {
                "arm_id": f"pR{pr}_pf{pf}",
                "partial_R": pr,
                "partial_fraction": pf,
                "n_trades": int(arm_arr.size),
                "per_fold": per_fold,
                "fold_positive_flags": fold_positive_flags,
                "n_folds_positive": int(sum(fold_positive_flags)),
                "pooled": {
                    "delta_sharpe": round(pooled_point, 4),
                    "ci_low": round(pooled_lo, 4),
                    "ci_high": round(pooled_hi, 4),
                    "p_two_sided": round(pooled_p, 4),
                    "sharpe_arm": round(_sharpe(arm_arr), 4),
                    "sharpe_base": round(_sharpe(base_arr), 4),
                    "mean_delta_r": round(float(pooled_delta_r.mean()), 4),
                    "median_delta_r": round(float(np.median(pooled_delta_r)), 4),
                    "delta_variance_r": round(dv_point, 6),
                    "delta_variance_r_ci_low": round(dv_lo, 6),
                    "delta_variance_r_ci_high": round(dv_hi, 6),
                },
                "guardrails": {
                    "tail_arm_worst10": round(tail_arm, 4),
                    "tail_base_worst10": round(tail_base, 4),
                    "delta_tail_worst10": round(delta_tail, 4),
                    "delta_mean_r": round(float(pooled_delta_r.mean()), 4),
                    "delta_p_rescue_on_fired": (
                        round(delta_p_rescue, 4)
                        if not np.isnan(delta_p_rescue) else None
                    ),
                },
                "mechanism": {
                    "n_partial_fired": n_fired,
                    "fire_rate": round(fire_rate, 4),
                    "mean_r_arm_on_fired": (
                        round(mean_arm_fired, 4) if not np.isnan(mean_arm_fired) else None
                    ),
                    "mean_r_base_on_fired": (
                        round(mean_base_fired, 4) if not np.isnan(mean_base_fired) else None
                    ),
                    "delta_mean_r_on_fired": (
                        round(delta_mean_fired, 4) if not np.isnan(delta_mean_fired) else None
                    ),
                    "p_arm_positive_on_fired": (
                        round(p_arm_pos_on_fired, 4) if not np.isnan(p_arm_pos_on_fired) else None
                    ),
                    "p_base_positive_on_fired": (
                        round(p_base_pos_on_fired, 4) if not np.isnan(p_base_pos_on_fired) else None
                    ),
                    "delta_p_rescue_on_fired": (
                        round(delta_p_rescue, 4) if not np.isnan(delta_p_rescue) else None
                    ),
                },
                "per_symbol": per_symbol_diag,
            }
            arms_out.append(arm_out)
            pooled_p_values.append(pooled_p)

    # BH-FDR across the 9-arm family on pooled two-sided p-values.
    fdr_rejected = _bh_fdr(pooled_p_values, alpha=FDR_ALPHA)
    bh_adj_ps = _bh_adjusted_p(pooled_p_values)
    for arm, rejected, adj_p in zip(arms_out, fdr_rejected, bh_adj_ps):
        arm["bh_fdr_rejected"] = bool(rejected)
        arm["bh_adjusted_p"] = round(float(adj_p), 4)

    # Per-arm verdict per PROTOCOL §5.3 / §6.
    def _classify(arm: dict) -> str:
        p = arm["pooled"]
        primary = p["ci_low"] > 0
        robust = arm["n_folds_positive"] >= 4
        bh_adj_significant = arm["bh_adjusted_p"] < 0.05
        tail_ok = (
            arm["guardrails"]["delta_tail_worst10"]
            >= GUARDRAIL_MIN_DELTA_TAIL_WORST10
        )
        mean_r_ok = (
            arm["guardrails"]["delta_mean_r"]
            >= GUARDRAIL_MIN_DELTA_MEAN_R
        )
        rescue_ok = (
            arm["guardrails"]["delta_p_rescue_on_fired"] is None
            or arm["guardrails"]["delta_p_rescue_on_fired"]
            >= GUARDRAIL_MIN_DELTA_P_RESCUE
        )
        secondaries_ok = tail_ok and mean_r_ok and rescue_ok

        # ALIVE — the strict per-PROTOCOL §5.3 gate.
        if primary and robust and bh_adj_significant and secondaries_ok:
            return "alive"

        # PARKED_LOWER_VARIANCE_LOWER_RETURN — H2 SPECIAL CASE (§6).
        # ΔSharpe CI contains 0 AND Δ variance CI-UB < 0 (statistically
        # negative variance shift).
        ci_contains_zero = p["ci_low"] <= 0 <= p["ci_high"]
        variance_negative = p["delta_variance_r_ci_high"] < 0
        if ci_contains_zero and variance_negative:
            return "parked_lower_variance_lower_return"

        # PARKED_LOW_YIELD — point positive but weak evidence.
        if p["delta_sharpe"] > 0 and (
            not primary or not robust or not bh_adj_significant
        ):
            return "parked_low_yield"

        # DEAD — nothing above triggered.
        return "dead"

    for arm in arms_out:
        arm["verdict"] = _classify(arm)

    return {
        "arms": arms_out,
        "grid": {
            "partial_R": list(partial_r_grid),
            "partial_fraction": list(partial_fraction_grid),
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
        "guardrail_bands": {
            "min_delta_mean_r": GUARDRAIL_MIN_DELTA_MEAN_R,
            "min_delta_p_rescue_on_fired": GUARDRAIL_MIN_DELTA_P_RESCUE,
            "min_delta_tail_worst10": GUARDRAIL_MIN_DELTA_TAIL_WORST10,
        },
    }


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="programs/E021/results.json")
    parser.add_argument("--data-dir", default=None,
                        help="Override PRE-0 data dir (defaults to package location)")
    parser.add_argument("--symbols", default=",".join(SYMBOLS))
    parser.add_argument("--smoke-only-first-arm", action="store_true",
                        help="Only evaluate the first (partial_R, partial_fraction) arm — "
                             "for interface smoke tests")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    log.info("E021 Phase 2 — Partial exit at fixed-R milestone validation")
    log.info(
        "Grid: partial_R=%s × partial_fraction=%s (%d arms)",
        PARTIAL_R_GRID, PARTIAL_FRACTION_GRID,
        len(PARTIAL_R_GRID) * len(PARTIAL_FRACTION_GRID),
    )

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

    pr_grid = (PARTIAL_R_GRID[0],) if args.smoke_only_first_arm else PARTIAL_R_GRID
    pf_grid = (PARTIAL_FRACTION_GRID[0],) if args.smoke_only_first_arm else PARTIAL_FRACTION_GRID

    results = sweep(
        all_trades,
        partial_r_grid=pr_grid,
        partial_fraction_grid=pf_grid,
    )

    payload = {
        "study": "E021",
        "title": "Partial exit at fixed-R milestone",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator_commit": _generator_commit(),
        "pre_registration": "experiments/E021_partial_exit_at_r_milestone/PROTOCOL.md",
        "harness": "programs/_shared/counterfactual_replay/replay.py",
        "symbols": list(symbols),
        "per_symbol_meta": per_symbol_meta,
        "total_trades": len(all_trades),
        "results": results,
    }

    # Overall verdict roll-up (PROTOCOL §6): any arm alive → alive;
    # else any arm parked_* → parked; else dead.
    alives = [a for a in results["arms"] if a["verdict"] == "alive"]
    parked = [
        (a["arm_id"], a["verdict"])
        for a in results["arms"]
        if a["verdict"].startswith("parked")
    ]
    if alives:
        payload["study_verdict"] = "alive"
        payload["winning_arms"] = [a["arm_id"] for a in alives]
        if parked:
            payload["parked_arms"] = parked
    elif parked:
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
    if "parked_arms" in payload:
        log.info("Parked arms: %s", payload["parked_arms"])


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
