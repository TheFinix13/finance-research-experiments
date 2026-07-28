"""E026 Phase 2 stage-1 — low-MFE time-stop, walk-forward validation.

Consumes the PRE-0 path-augmented ledgers for EURUSD/GBPUSD/USDCAD via
the shared replay engine and sweeps the frozen 15-arm stage-1 grid per
PROTOCOL §4.1:

    P (progress threshold, R) ∈ {0.25, 0.50, 0.75}
    × B (age threshold, H4 bars) ∈ {12, 18, 24, 30, 42}
    = 15 arms, exit_action = close_at_market fixed.

Scored per-symbol (PROTOCOL §5 — NOT pooled across symbols). BH-FDR at
α = 0.10 within each symbol's 15 joint p-values; Stouffer's Z (weights
√n_fold_trades) combines fold-level bootstrap p-values; Fisher's
combined p reported as sensitivity. Statistical machinery is identical
to E024's runner (`programs/E024/run_e024_validation.py`) — deliberate,
for cross-study comparability.

Everything is pre-registered in
[`experiments/E026_low_mfe_time_stop/PROTOCOL.md`](../../experiments/E026_low_mfe_time_stop/PROTOCOL.md).
This file is the mechanical implementation — no post-hoc tuning.

CLI::

    ../multi-pair-trading-agent/.venv/bin/python \\
        programs/E026/run_e026_validation.py \\
        --output programs/E026/results.json
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
    TradeRecord,
    load_paths_ledger,
    replay,
)
from programs.E026.time_stop_rule import (  # noqa: E402
    B_GRID,
    P_GRID,
    REASON_E026_TIME_STOP,
    RESOLUTION_TO_H4_FRACTION,
    E026TimeStopRule,
    make_arm_grid,
)

log = logging.getLogger("E026")

SYMBOLS: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDCAD")

BOOTSTRAP_SEED: int = 42
BOOTSTRAP_RESAMPLES: int = 5000
FDR_ALPHA: float = 0.10
JOINT_P_ALPHA: float = 0.05
FALSE_POS_HEAVY_THRESHOLD: float = 0.50   # PROTOCOL §6 park threshold

# Walk-forward folds mirror PRE-0 §3 / E004 exactly (identical to E020/E024).
FOLDS: tuple[tuple[str, datetime, datetime], ...] = (
    ("fold1", datetime(2017, 1, 1, tzinfo=timezone.utc), datetime(2019, 1, 1, tzinfo=timezone.utc)),
    ("fold2", datetime(2019, 1, 1, tzinfo=timezone.utc), datetime(2021, 1, 1, tzinfo=timezone.utc)),
    ("fold3", datetime(2021, 1, 1, tzinfo=timezone.utc), datetime(2023, 1, 1, tzinfo=timezone.utc)),
    ("fold4", datetime(2023, 1, 1, tzinfo=timezone.utc), datetime(2024, 7, 1, tzinfo=timezone.utc)),
    ("fold5", datetime(2024, 7, 1, tzinfo=timezone.utc), datetime(2026, 1, 1, tzinfo=timezone.utc)),
)


# ---------------------------------------------------------------------------
# Metric helpers (identical to E024's runner).
# ---------------------------------------------------------------------------

def _sharpe(returns: Sequence[float]) -> float:
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
    return point, lo, hi, min(p_two, 1.0)


def _bh_fdr(p_values: Sequence[float], alpha: float = FDR_ALPHA) -> list[bool]:
    p = np.asarray(p_values, dtype=float)
    m = p.size
    order = np.argsort(p)
    thresholds = (np.arange(1, m + 1) / m) * alpha
    p_sorted = p[order]
    passed_sorted = p_sorted <= thresholds
    cutoff = int(np.max(np.where(passed_sorted))) if passed_sorted.any() else -1
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
    ps = [float(p) for p in p_values if p is not None and np.isfinite(p)]
    if not ps:
        return None
    stat = -2.0 * float(np.sum(np.log(np.clip(ps, 1e-16, 1.0))))
    return float(1.0 - chi2.cdf(stat, 2 * len(ps)))


def _tail_mean(rs: Sequence[float], q: float = 0.10) -> float:
    arr = np.sort(np.asarray(rs, dtype=float))
    if arr.size == 0:
        return float("nan")
    k = max(1, int(arr.size * q))
    return float(arr[:k].mean())


def _fold_of(entry_time: datetime, folds=FOLDS) -> Optional[str]:
    for name, s, e in folds:
        if s <= entry_time < e:
            return name
    return None


# ---------------------------------------------------------------------------
# Sweep for one symbol.
# ---------------------------------------------------------------------------

def _run_arm(
    trades: list[TradeRecord],
    progress_r: float,
    age_bars: int,
) -> tuple[list[float], list[Optional[dict]], list[str], list[int]]:
    """Run one arm across all trades. Returns paired arm_R, per-trade fire
    details (None if didn't fire), per-trade alt-exit-reason, and per-trade
    arm bars-held (fire bar for fired trades, full path length otherwise)."""
    rule = E026TimeStopRule(progress_r=progress_r, age_bars=age_bars)
    arm_R: list[float] = []
    fires: list[Optional[dict]] = []
    alt_reasons: list[str] = []
    bars_held_arm: list[float] = []           # H4-equivalents (Amendment 2)
    for t in trades:
        rule.reset(path_resolution=t.path_resolution)
        alt = replay(t, rule=rule)
        arm_R.append(alt.r)
        alt_reasons.append(alt.exit_reason)
        fd = rule.fired_details
        # fired_details is set the first time the condition holds, but the
        # engine may have closed the trade earlier on the SAME bar via hard
        # SL priority — only count a fire when the alt exit really is ours.
        if fd is not None and alt.exit_reason == REASON_E026_TIME_STOP:
            fires.append({
                "bar_index": fd.bar_index,
                "bar_time": fd.bar_time.isoformat(),
                "fire_price": fd.fire_price,
                "bars_held_h4": fd.bars_held_h4,
                "mfe_r_at_fire": fd.mfe_r_at_fire,
                "mfe_pips_at_fire": fd.mfe_pips_at_fire,
            })
            bars_held_arm.append(fd.bars_held_h4)
        else:
            fires.append(None)
            bars_held_arm.append(_path_bars_h4(t))
    return arm_R, fires, alt_reasons, bars_held_arm


def _path_bars_h4(t: TradeRecord) -> float:
    """Full-path holding time in H4-equivalents."""
    return len(t.path) * RESOLUTION_TO_H4_FRACTION[t.path_resolution]


def _classify_arm(
    per_fold_positive_flags: list[bool],
    pooled_ci_low: float,
    joint_p_stouffer: Optional[float],
    bh_rejected: bool,
    delta_p_false_positive: float,
    pooled_delta_sharpe: float,
) -> str:
    """PROTOCOL §6 verdict rules (identical to E024)."""
    n_pos = sum(per_fold_positive_flags)
    alive_primary = pooled_ci_low > 0
    alive_robust = n_pos >= 4
    alive_joint_sig = joint_p_stouffer is not None and joint_p_stouffer < JOINT_P_ALPHA
    alive_all = alive_primary and alive_robust and alive_joint_sig and bh_rejected

    if alive_all and delta_p_false_positive > FALSE_POS_HEAVY_THRESHOLD:
        return "parked_false_positive_heavy"
    if alive_all:
        return "alive"
    ci_includes_zero = pooled_ci_low <= 0
    point_positive = pooled_delta_sharpe > 0
    if point_positive and (ci_includes_zero or n_pos == 3):
        return "parked_low_yield"
    return "dead"


#: Amendment 1 — inert-rule age threshold (never fires on any real path).
INERT_AGE_BARS: int = 10**9


def _null_arm_baseline(trades: list[TradeRecord]) -> tuple[list[float], list[str]]:
    """Replayed inert-rule baseline (PROTOCOL §7 Amendment 1).

    Same rule class, ``age_bars`` so large it can never fire, so every
    trade takes the engine's fall-through reconstruction — identical
    semantics to a real arm's non-fired trades. The paired delta against
    this baseline isolates the rule effect from reconstruction drift."""
    rule = E026TimeStopRule(progress_r=0.50, age_bars=INERT_AGE_BARS)
    base_R: list[float] = []
    base_reasons: list[str] = []
    for t in trades:
        rule.reset(path_resolution=t.path_resolution)
        alt = replay(t, rule=rule)
        assert alt.exit_reason != REASON_E026_TIME_STOP
        base_R.append(alt.r)
        base_reasons.append(alt.exit_reason)
    return base_R, base_reasons


def _sweep_symbol(
    symbol: str,
    trades: list[TradeRecord],
    grid: list[dict],
    folds=FOLDS,
    seed: int = BOOTSTRAP_SEED,
    resamples: int = BOOTSTRAP_RESAMPLES,
    fdr_alpha: float = FDR_ALPHA,
) -> dict:
    fold_ids = [_fold_of(t.entry_time, folds) for t in trades]
    base_R_all, base_reasons = _null_arm_baseline(trades)
    bars_held_base = [_path_bars_h4(t) for t in trades]

    # Reconstruction audit (Amendment 1): quantify null-arm vs ledger drift.
    ledger_R = [t.r for t in trades]
    n_mismatch = sum(
        1 for a, b in zip(base_R_all, ledger_R) if abs(a - b) > 1e-6)
    drift_sharpe = _sharpe(base_R_all) - _sharpe(ledger_R)
    reconstruction_audit = {
        "n_trades": len(trades),
        "n_null_vs_ledger_mismatch": n_mismatch,
        "sharpe_null_arm": round(_sharpe(base_R_all), 4),
        "sharpe_ledger": round(_sharpe(ledger_R), 4),
        "delta_sharpe_null_vs_ledger": round(drift_sharpe, 4),
    }

    arms_out: list[dict] = []
    per_arm_joint_p: list[float] = []

    for i_arm, arm in enumerate(grid):
        p_thr = arm["progress_r"]
        b_thr = arm["age_bars"]
        arm_R_all, fires, alt_reasons, bars_held_arm = _run_arm(trades, p_thr, b_thr)

        per_fold: list[dict] = []
        per_fold_flags: list[bool] = []
        per_fold_p: list[Optional[float]] = []
        per_fold_delta: list[Optional[float]] = []
        per_fold_weights: list[float] = []

        for fname, _fs, _fe in folds:
            arm_fold = [r for r, fid in zip(arm_R_all, fold_ids) if fid == fname]
            base_fold = [r for r, fid in zip(base_R_all, fold_ids) if fid == fname]
            if len(arm_fold) < 2:
                per_fold.append({"fold": fname, "n_trades": len(arm_fold),
                                 "delta_sharpe": None, "ci_low": None,
                                 "ci_high": None, "p_two_sided": None})
                per_fold_flags.append(False)
                per_fold_p.append(None)
                per_fold_delta.append(None)
                per_fold_weights.append(0.0)
                continue
            point, lo, hi, p_two = _paired_bootstrap_ci(
                arm_fold, base_fold, seed=seed, resamples=resamples)
            per_fold.append({
                "fold": fname,
                "n_trades": len(arm_fold),
                "delta_sharpe": round(point, 4),
                "ci_low": round(lo, 4),
                "ci_high": round(hi, 4),
                "p_two_sided": round(p_two, 4),
                "mean_delta_r": round(
                    float(np.mean(np.array(arm_fold) - np.array(base_fold))), 4),
            })
            per_fold_flags.append(point > 0)
            per_fold_p.append(p_two)
            per_fold_delta.append(point)
            per_fold_weights.append(float(np.sqrt(len(arm_fold))))

        z_stouffer, p_stouffer = _stouffer_combine(per_fold_p, per_fold_delta, per_fold_weights)
        p_fisher = _fisher_combine(per_fold_p)

        arm_R_arr = np.array(arm_R_all, dtype=float)
        base_R_arr = np.array(base_R_all, dtype=float)
        pooled_point, pooled_lo, pooled_hi, pooled_p = _paired_bootstrap_ci(
            arm_R_arr, base_R_arr, seed=seed, resamples=resamples)

        # Fire diagnostics (PROTOCOL §5 guardrails).
        n_trades = len(trades)
        fired_mask = [f is not None for f in fires]
        n_fires = sum(fired_mask)
        # FP/rescued keyed off the NULL-ARM baseline exit (Amendment 1 —
        # the counterfactual for a fired trade is the null-arm outcome).
        n_fires_on_tp = sum(
            1 for fd, br in zip(fires, base_reasons)
            if fd is not None and br == "tp")
        n_fires_on_sl = sum(
            1 for fd, br in zip(fires, base_reasons)
            if fd is not None and br.startswith("sl"))
        delta_p_fire = n_fires / n_trades if n_trades else 0.0
        delta_p_false_pos = n_fires_on_tp / n_fires if n_fires else 0.0
        delta_p_rescued = n_fires_on_sl / n_fires if n_fires else 0.0

        fired_arm_R = [r for r, m in zip(arm_R_all, fired_mask) if m]
        fired_base_R = [r for r, m in zip(base_R_all, fired_mask) if m]
        delta_mean_r_fired = (
            float(np.mean(np.array(fired_arm_R) - np.array(fired_base_R)))
            if n_fires else 0.0)

        # Bars-held (H3 capital-efficiency read, descriptive only).
        mean_bars_arm = float(np.mean(bars_held_arm)) if n_trades else 0.0
        mean_bars_base = float(np.mean(bars_held_base)) if n_trades else 0.0
        fired_bars_arm = [b for b, m in zip(bars_held_arm, fired_mask) if m]
        fired_bars_base = [b for b, m in zip(bars_held_base, fired_mask) if m]

        tail_arm = _tail_mean(arm_R_arr)
        tail_base = _tail_mean(base_R_arr)

        arm_out = {
            "arm_id": arm["arm_id"],
            "progress_r": p_thr,
            "age_bars": b_thr,
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
                "mean_delta_r": round(float((arm_R_arr - base_R_arr).mean()), 4),
                "tail_arm_worst10": round(tail_arm, 4),
                "tail_base_worst10": round(tail_base, 4),
                "delta_tail_worst10": round(tail_arm - tail_base, 4),
            },
            "fire_diagnostics": {
                "n_fires": n_fires,
                "n_fires_on_tp": n_fires_on_tp,
                "n_fires_on_sl": n_fires_on_sl,
                "delta_p_fire": round(delta_p_fire, 4),
                "delta_p_false_positive": round(delta_p_false_pos, 4),
                "delta_p_rescued": round(delta_p_rescued, 4),
                "delta_mean_r_fired_cohort": round(delta_mean_r_fired, 4),
                "mean_mfe_r_at_fire": (
                    round(float(np.mean([f["mfe_r_at_fire"] for f in fires if f])), 4)
                    if n_fires else None),
            },
            "bars_held": {
                "mean_arm_all": round(mean_bars_arm, 2),
                "mean_base_all": round(mean_bars_base, 2),
                "mean_arm_fired": (round(float(np.mean(fired_bars_arm)), 2)
                                   if n_fires else None),
                "mean_base_fired": (round(float(np.mean(fired_bars_base)), 2)
                                    if n_fires else None),
            },
            "bh_fdr_rejected": None,
            "verdict": None,
        }
        arms_out.append(arm_out)
        per_arm_joint_p.append(p_stouffer if p_stouffer is not None else 1.0)

        log.info(
            "  [%s] arm %2d/%d %s ΔSharpe=%+.4f CI=[%+.4f, %+.4f] fires=%d "
            "FP=%.3f rescued=%.3f",
            symbol, i_arm + 1, len(grid), arm["arm_id"],
            pooled_point, pooled_lo, pooled_hi, n_fires,
            delta_p_false_pos, delta_p_rescued,
        )

    fdr_rejected = _bh_fdr(per_arm_joint_p, alpha=fdr_alpha)
    for arm_out, rej in zip(arms_out, fdr_rejected):
        arm_out["bh_fdr_rejected"] = bool(rej)
    for arm_out in arms_out:
        arm_out["verdict"] = _classify_arm(
            per_fold_positive_flags=arm_out["fold_positive_flags"],
            pooled_ci_low=arm_out["pooled"]["ci_low"],
            joint_p_stouffer=arm_out["joint_p_stouffer"],
            bh_rejected=arm_out["bh_fdr_rejected"],
            delta_p_false_positive=arm_out["fire_diagnostics"]["delta_p_false_positive"],
            pooled_delta_sharpe=arm_out["pooled"]["delta_sharpe"],
        )

    return {
        "symbol": symbol,
        "n_trades": len(trades),
        "reconstruction_audit": reconstruction_audit,
        "arms": arms_out,
        "verdict_counts": dict(Counter(a["verdict"] for a in arms_out)),
        "fdr": {"method": "BH", "alpha": fdr_alpha, "family_size": len(arms_out)},
    }


def _study_verdict(per_symbol_results: list[dict]) -> str:
    verdicts = [a["verdict"] for sym in per_symbol_results for a in sym["arms"]]
    if "alive" in verdicts:
        return "alive"
    if "parked_false_positive_heavy" in verdicts:
        return "parked_false_positive_heavy"
    if "parked_low_yield" in verdicts:
        return "parked_low_yield"
    return "dead"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="programs/E026/results.json")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--symbols", default=",".join(SYMBOLS))
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level),
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")

    log.info("E026 Phase 2 stage-1 — low-MFE time-stop validation")
    grid = make_arm_grid()
    log.info("Grid: %d arms (P=%s × B=%s)", len(grid), P_GRID, B_GRID)

    symbols = tuple(s.strip() for s in args.symbols.split(","))
    kwargs = {"data_dir": args.data_dir} if args.data_dir else {}

    per_symbol_meta: dict[str, dict] = {}
    per_symbol_trades: dict[str, list[TradeRecord]] = {}
    for sym in symbols:
        meta, trades = load_paths_ledger(sym, **kwargs)
        per_symbol_meta[sym] = meta
        per_symbol_trades[sym] = trades
        log.info("  loaded %s: %d trades", sym, len(trades))

    per_symbol_results: list[dict] = []
    for sym in symbols:
        log.info("Sweeping %s (%d trades × %d arms) ...",
                 sym, len(per_symbol_trades[sym]), len(grid))
        res = _sweep_symbol(sym, per_symbol_trades[sym], grid)
        per_symbol_results.append(res)
        log.info("  %s verdict counts: %s", sym, res["verdict_counts"])

    payload = {
        "study": "E026",
        "title": "Low-MFE time-stop (stage 1)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator_commit": _generator_commit(),
        "pre_registration": "experiments/E026_low_mfe_time_stop/PROTOCOL.md",
        "harness": "programs/_shared/counterfactual_replay/replay.py",
        "symbols": list(symbols),
        "per_symbol_meta": per_symbol_meta,
        "grid": {"progress_r": list(P_GRID), "age_bars": list(B_GRID),
                 "n_arms": len(grid)},
        "folds": [{"name": n, "start": s.isoformat(), "end": e.isoformat()}
                  for n, s, e in FOLDS],
        "bootstrap": {"seed": BOOTSTRAP_SEED, "resamples": BOOTSTRAP_RESAMPLES},
        "fdr": {"method": "BH", "alpha": FDR_ALPHA,
                "family_size_per_symbol": len(grid),
                "note": "Applied per-symbol, not pooled across symbols."},
        "per_symbol": per_symbol_results,
    }
    payload["study_verdict"] = _study_verdict(per_symbol_results)
    alive_arms = [
        {"symbol": sym["symbol"], "arm_id": a["arm_id"], "verdict": a["verdict"]}
        for sym in per_symbol_results for a in sym["arms"] if a["verdict"] == "alive"]
    payload["alive_arms"] = alive_arms
    payload["stage_2_authorised"] = bool(alive_arms)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    log.info("Wrote %s", out)
    log.info("Study verdict: %s", payload["study_verdict"])


def _generator_commit() -> str:
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(_REPO_ROOT), stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "unknown"


if __name__ == "__main__":
    main()
