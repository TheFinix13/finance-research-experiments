"""E022 Phase 2 — structure-aware TP snap, walk-forward validation.

PROTOCOL: ``experiments/E022_structure_aware_tp_snap/PROTOCOL.md``.

Consumes the PRE-0 path-augmented ledgers for EURUSD/GBPUSD/USDCAD
(``programs/_shared/counterfactual_replay/data/{SYMBOL}_H4_paths.jsonl``),
reconstructs the four level sources (``daily_only``, ``ladder_top``,
``round_number``, ``all``) per PROTOCOL §3.3 using
``programs/E022/level_detector.py``, sweeps the 12-arm frozen grid
``snap_distance ∈ {5, 10, 15} × snap_source ∈ {daily_only, ladder_top,
round_number, all}`` (PROTOCOL §4.1), applies :func:`snap_tp` +
:func:`rescore_trade` from ``rescorer.py``, and emits per-fold + pooled
ΔSharpe with paired bootstrap 95 % CIs and BH-FDR correction across the
12-arm family (PROTOCOL §5).

This file mirrors ``programs/E020/run_e020_validation.py`` structurally
(argparse skeleton, fold assignment, sweep loop, bootstrap helpers,
BH-FDR helper, verdict classifier plumbing). The mechanism-specific
differences vs E020 are:

- No lifetime replay — E022 modifies the target price at order placement.
  ``rescorer.rescore_trade`` scans the intra-trade path directly (bar 0
  counts, per the design note in the rescorer's module docstring).
- Level reconstruction runs UP-FRONT once per (trade, snap_source),
  cached in memory across the 3 snap_distance arms that share it.
- ``snap_fire_rate`` is tracked per arm and feeds the PROTOCOL §6.5
  ``parked_snap_never_fires`` (H3) verdict.

CLI::

    PYTHONPATH=../multi-pair-trading-agent:.:scripts \\
        ../multi-pair-trading-agent/.venv/bin/python \\
        programs/E022/run_e022_validation.py \\
        --output programs/E022/results.json
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT.parent / "multi-pair-trading-agent"))

from programs._shared.counterfactual_replay.replay import (  # noqa: E402
    PIP,
    TradeRecord,
    load_paths_ledger,
)
from programs.E022.level_detector import (  # noqa: E402
    LOOKBACK,
    SUPPORTED_SNAP_SOURCES,
    TradeLevels,
    compute_trade_levels,
    load_symbol_cache,
)
from programs.E022.rescorer import (  # noqa: E402
    AltOutcome,
    rescore_trade,
    snap_tp,
)

log = logging.getLogger("E022")


# ---------------------------------------------------------------------------
# Frozen §4 grid — PROTOCOL §4.1 (12 arms, 2-D, do NOT expand).
# ---------------------------------------------------------------------------

SYMBOLS: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDCAD")
SNAP_DISTANCE_GRID: tuple[float, ...] = (5.0, 10.0, 15.0)
SNAP_SOURCE_GRID: tuple[str, ...] = ("daily_only", "ladder_top", "round_number", "all")
BOOTSTRAP_SEED: int = 42
BOOTSTRAP_RESAMPLES: int = 5000
FDR_ALPHA: float = 0.10
FIRE_RATE_FLOOR: float = 0.05  # PROTOCOL §6.4 / §H3

FOLDS: tuple[tuple[str, datetime, datetime], ...] = (
    ("fold1", datetime(2017, 1, 1, tzinfo=timezone.utc), datetime(2019, 1, 1, tzinfo=timezone.utc)),
    ("fold2", datetime(2019, 1, 1, tzinfo=timezone.utc), datetime(2021, 1, 1, tzinfo=timezone.utc)),
    ("fold3", datetime(2021, 1, 1, tzinfo=timezone.utc), datetime(2023, 1, 1, tzinfo=timezone.utc)),
    ("fold4", datetime(2023, 1, 1, tzinfo=timezone.utc), datetime(2024, 7, 1, tzinfo=timezone.utc)),
    ("fold5", datetime(2024, 7, 1, tzinfo=timezone.utc), datetime(2026, 1, 1, tzinfo=timezone.utc)),
)


def _snap_offset(snap_distance: float) -> float:
    """PROTOCOL §4.2: snap_offset_pips = min(3, snap_distance/2)."""
    return min(3.0, snap_distance / 2.0)


# ---------------------------------------------------------------------------
# Metrics.
# ---------------------------------------------------------------------------

def _sharpe(returns: Sequence[float]) -> float:
    """Sharpe on a per-trade R-sequence (unannualised; same convention as
    E020 — both sides use the same n_trades, so annualisation factors
    cancel in the paired delta)."""
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
    """(delta_sharpe_point, ci_low, ci_high, p_value_two_sided). Mirrors
    E020's helper — paired, seed-42, 5000 resamples per PROTOCOL §4.2."""
    arm = np.asarray(r_arm, dtype=float)
    base = np.asarray(r_base, dtype=float)
    assert arm.shape == base.shape, "paired arrays must have equal length"
    n = arm.size
    if n < 2:
        return float("nan"), float("nan"), float("nan"), float("nan")

    point = _paired_delta_sharpe(arm, base)
    if not np.isfinite(point):
        # Both sides share the same population and produce NaN Sharpe
        # (zero variance). The snap did not move any trade — treat as
        # zero delta with a large p-value so no arm claims significance.
        return 0.0, 0.0, 0.0, 1.0

    rng = np.random.default_rng(seed)
    deltas = np.empty(resamples, dtype=float)
    for k in range(resamples):
        idx = rng.integers(0, n, size=n)
        deltas[k] = _paired_delta_sharpe(arm[idx], base[idx])

    finite = deltas[np.isfinite(deltas)]
    if finite.size < 2:
        return float(point), 0.0, 0.0, 1.0

    lo = float(np.quantile(finite, alpha / 2))
    hi = float(np.quantile(finite, 1 - alpha / 2))
    if point >= 0:
        p_two = 2.0 * float(np.mean(finite <= 0))
    else:
        p_two = 2.0 * float(np.mean(finite >= 0))
    p_two = min(p_two, 1.0)
    return float(point), lo, hi, p_two


def _bh_fdr(p_values: Sequence[float], alpha: float = FDR_ALPHA) -> list[bool]:
    """Benjamini–Hochberg FDR. Mirrors E020's helper — see comment there."""
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


# ---------------------------------------------------------------------------
# Fold assignment.
# ---------------------------------------------------------------------------

def _fold_of(entry_time: datetime, folds: Sequence[tuple[str, datetime, datetime]]) -> Optional[str]:
    for name, s, e in folds:
        if s <= entry_time < e:
            return name
    return None


# ---------------------------------------------------------------------------
# Level pre-computation.
#
# 12 arms share the 4 snap_source level sets — reconstruct each set ONCE
# per trade up front, then reuse across the 3 snap_distance values.
# ---------------------------------------------------------------------------

def _build_levels(trades: list[TradeRecord]) -> dict[str, TradeLevels]:
    from agent.config import load_config
    cfg = load_config()
    # Materialise per-symbol H4 caches up front (so log lines report the
    # counts once, not once per trade).
    for sym in sorted({t.symbol for t in trades}):
        cfg.symbol = sym
        load_symbol_cache(sym, cfg=cfg)

    out: dict[str, TradeLevels] = {}
    log_every = max(1, len(trades) // 20)
    t0 = time.time()
    for i, t in enumerate(trades):
        cache = load_symbol_cache(t.symbol, cfg=cfg)
        out[t.trade_id] = compute_trade_levels(
            symbol_cache=cache,
            cfg=cfg,
            trade_id=t.trade_id,
            entry_time=t.entry_time,
            entry=t.entry,
            tp=t.take_profit,
            direction=t.direction,
        )
        if (i + 1) % log_every == 0 or i + 1 == len(trades):
            log.info(
                "level reconstruction %d/%d (%.1fs elapsed)",
                i + 1, len(trades), time.time() - t0,
            )
    log.info("level reconstruction complete in %.1fs", time.time() - t0)
    return out


# ---------------------------------------------------------------------------
# Sweep engine.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ArmResult:
    """One (snap_distance, snap_source) arm's rescored per-trade R sequence
    plus mechanism diagnostics."""

    arm_id: str
    snap_distance: float
    snap_source: str
    arm_r: list[float]
    base_r: list[float]
    fired_flags: list[bool]     # snap moved the TP
    filled_at_snap: list[bool]  # alt fill was the new_tp (vs original exit)


def _run_arm(
    trades: list[TradeRecord],
    levels_by_trade: dict[str, TradeLevels],
    snap_distance: float,
    snap_source: str,
) -> ArmResult:
    offset = _snap_offset(snap_distance)
    arm_id = f"{snap_source}_d{int(snap_distance)}"
    arm_r: list[float] = []
    base_r: list[float] = []
    fired_flags: list[bool] = []
    filled_at_snap: list[bool] = []
    for t in trades:
        L = levels_by_trade[t.trade_id].prices(snap_source)
        new_tp = snap_tp(
            entry=t.entry,
            tp=t.take_profit,
            direction=t.direction,
            L=L,
            snap_distance_pips=snap_distance,
            snap_offset_pips=offset,
        )
        alt: AltOutcome = rescore_trade(t, new_tp)
        arm_r.append(alt.r)
        base_r.append(t.r)
        fired_flags.append(new_tp != t.take_profit)
        filled_at_snap.append(alt.filled_at_snap)
    return ArmResult(
        arm_id=arm_id,
        snap_distance=snap_distance,
        snap_source=snap_source,
        arm_r=arm_r,
        base_r=base_r,
        fired_flags=fired_flags,
        filled_at_snap=filled_at_snap,
    )


def _tp_fill_flag(trade: TradeRecord) -> bool:
    """True if the ORIGINAL trade filled at TP."""
    return trade.exit_reason == "tp"


def _mean_r_when_win_delta(
    arm_r: Sequence[float], base_r: Sequence[float],
) -> tuple[float, int]:
    """Δ mean R conditional on winner. A "winner" is a trade with r > 0 in
    EITHER arm or baseline (union) — we mean-diff over that population."""
    arm = np.asarray(arm_r, dtype=float)
    base = np.asarray(base_r, dtype=float)
    winners_mask = (arm > 0) | (base > 0)
    if not winners_mask.any():
        return float("nan"), 0
    delta = float(np.mean(arm[winners_mask] - base[winners_mask]))
    return delta, int(winners_mask.sum())


def _mean_bars_in_trade_delta(
    trades: list[TradeRecord],
    arm_result: ArmResult,
) -> tuple[float, int]:
    """Δ mean time-in-trade for winners, in H4 bars. Uses ``trade.exit_time
    − entry_time`` (bar count = seconds / 14_400) for the baseline;
    for the arm we use ``alt.exit_time`` where the snap filled at
    new_tp (else baseline exit)."""
    deltas: list[float] = []
    for t, alt_r, filled in zip(trades, arm_result.arm_r, arm_result.filled_at_snap):
        # A "winner" here mirrors E020: original trade closed with r > 0
        # OR the arm's alt r > 0. Restrict to that population.
        if t.r <= 0 and alt_r <= 0:
            continue
        base_seconds = (t.exit_time - t.entry_time).total_seconds()
        if filled:
            # We don't carry the exact alt exit_time in ArmResult, but we
            # can recover it: it's the FIRST bar in trade.path that hit
            # new_tp — for time-in-trade we approximate by re-scoring.
            # For efficiency we skip this here; the aggregate uses
            # per-arm results below.
            deltas.append(0.0)  # placeholder — see main sweep for exact
            continue
        deltas.append(0.0)
    return float(np.mean(deltas)) if deltas else float("nan"), len(deltas)


def sweep(
    trades: list[TradeRecord],
    levels_by_trade: dict[str, TradeLevels],
    *,
    snap_distance_grid: Sequence[float] = SNAP_DISTANCE_GRID,
    snap_source_grid: Sequence[str] = SNAP_SOURCE_GRID,
    folds: Sequence[tuple[str, datetime, datetime]] = FOLDS,
    seed: int = BOOTSTRAP_SEED,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> dict:
    """Full 12-arm × 5-fold sweep, pooled across symbols.

    Returns a JSON-ready dict — schema mirrors ``programs/E020/results.json``
    but with E022-specific fields (``snap_fire_rate``, ``delta_p_tp_fills``).
    """
    fold_ids = [_fold_of(t.entry_time, folds) for t in trades]
    base_tp_fill = [_tp_fill_flag(t) for t in trades]

    arms_out: list[dict] = []
    pooled_p_values: list[float] = []

    for snap_source in snap_source_grid:
        for snap_distance in snap_distance_grid:
            arm_id = f"{snap_source}_d{int(snap_distance)}"
            log.info(
                "arm %s: running on %d trades (offset=%.1fp) ...",
                arm_id, len(trades), _snap_offset(snap_distance),
            )
            armr = _run_arm(trades, levels_by_trade, snap_distance, snap_source)

            # Per-fold pass.
            per_fold: list[dict] = []
            fold_positive_flags: list[bool] = []
            for fname, _fs, _fe in folds:
                arm_fold = [r for r, fid in zip(armr.arm_r, fold_ids) if fid == fname]
                base_fold = [r for r, fid in zip(armr.base_r, fold_ids) if fid == fname]
                fired_fold = [f for f, fid in zip(armr.fired_flags, fold_ids) if fid == fname]
                filled_snap_fold = [f for f, fid in zip(armr.filled_at_snap, fold_ids) if fid == fname]
                base_tp_fold = [bf for bf, fid in zip(base_tp_fill, fold_ids) if fid == fname]
                n_trades = len(arm_fold)
                if n_trades == 0:
                    per_fold.append({
                        "fold": fname, "n_trades": 0,
                        "delta_sharpe": None, "ci_low": None, "ci_high": None,
                        "p_two_sided": None,
                        "snap_fire_rate": None,
                        "delta_p_tp_fills": None,
                    })
                    fold_positive_flags.append(False)
                    continue
                point, lo, hi, p = _paired_bootstrap_ci(
                    arm_fold, base_fold, seed=seed, resamples=resamples,
                )
                # Δ P(TP fills) — on the arm side, a "TP fill" is either
                # the original trade's TP fill (if the snap did not
                # displace the outcome) or the new_tp fill.
                arm_tp = [
                    (btp if not fld else True)  # alt fill at new_tp counts as TP
                    for btp, fld in zip(base_tp_fold, filled_snap_fold)
                ]
                delta_p_tp = (
                    float(np.mean(arm_tp)) - float(np.mean(base_tp_fold))
                    if base_tp_fold else float("nan")
                )
                per_fold.append({
                    "fold": fname,
                    "n_trades": n_trades,
                    "delta_sharpe": round(point, 4),
                    "ci_low": round(lo, 4),
                    "ci_high": round(hi, 4),
                    "p_two_sided": round(p, 4),
                    "sharpe_arm": round(_sharpe(arm_fold), 4),
                    "sharpe_base": round(_sharpe(base_fold), 4),
                    "mean_delta_r": round(
                        float(np.mean(np.array(arm_fold) - np.array(base_fold))), 4
                    ),
                    "snap_fire_rate": round(float(np.mean(fired_fold)), 4),
                    "delta_p_tp_fills": round(delta_p_tp, 4),
                })
                fold_positive_flags.append(point > 0)

            # Pooled pass.
            arm_R = np.asarray(armr.arm_r, dtype=float)
            base_R = np.asarray(armr.base_r, dtype=float)
            pooled_delta_r = arm_R - base_R
            point, lo, hi, p = _paired_bootstrap_ci(
                arm_R, base_R, seed=seed, resamples=resamples,
            )
            snap_fire_rate = float(np.mean(armr.fired_flags))
            filled_at_snap_rate = float(np.mean(armr.filled_at_snap))
            arm_tp_fills = [
                (btp if not fld else True)
                for btp, fld in zip(base_tp_fill, armr.filled_at_snap)
            ]
            delta_p_tp = float(np.mean(arm_tp_fills)) - float(np.mean(base_tp_fill))
            delta_meanR_win, n_winners = _mean_r_when_win_delta(armr.arm_r, armr.base_r)

            # Time-in-trade for the trades whose fill was moved by the snap.
            # For efficiency, we compute it here on the pooled level, not
            # per fold: the population is small (only filled_at_snap trades).
            time_deltas_hours: list[float] = []
            time_deltas_bars: list[float] = []
            for t, filled, alt_r in zip(trades, armr.filled_at_snap, armr.arm_r):
                if not filled:
                    continue
                # Re-derive alt exit_time by scanning the path once more.
                # Cheap because this branch fires only on filled_at_snap trades.
                dsign = +1 if t.direction == "long" else -1
                # We must recompute new_tp — but we know it fired, so pull
                # it from the pooled level set.
                L = levels_by_trade[t.trade_id].prices(armr.snap_source)
                new_tp = snap_tp(
                    entry=t.entry, tp=t.take_profit, direction=t.direction,
                    L=L,
                    snap_distance_pips=armr.snap_distance,
                    snap_offset_pips=_snap_offset(armr.snap_distance),
                )
                for bar in t.path:
                    hits = (bar.high >= new_tp) if dsign == +1 else (bar.low <= new_tp)
                    if hits:
                        alt_exit_time = bar.time
                        base_dur_hours = (t.exit_time - t.entry_time).total_seconds() / 3600.0
                        alt_dur_hours = (alt_exit_time - t.entry_time).total_seconds() / 3600.0
                        time_deltas_hours.append(alt_dur_hours - base_dur_hours)
                        time_deltas_bars.append((alt_dur_hours - base_dur_hours) / 4.0)
                        break
            time_delta_hours_mean = (
                float(np.mean(time_deltas_hours)) if time_deltas_hours else float("nan")
            )
            time_delta_bars_mean = (
                float(np.mean(time_deltas_bars)) if time_deltas_bars else float("nan")
            )

            arm_out = {
                "arm_id": arm_id,
                "snap_source": snap_source,
                "snap_distance": snap_distance,
                "snap_offset": _snap_offset(snap_distance),
                "n_trades": int(len(arm_R)),
                "per_fold": per_fold,
                "fold_positive_flags": fold_positive_flags,
                "n_folds_positive": int(sum(fold_positive_flags)),
                "pooled": {
                    "delta_sharpe": round(point, 4),
                    "ci_low": round(lo, 4),
                    "ci_high": round(hi, 4),
                    "p_two_sided": round(p, 4),
                    "sharpe_arm": round(_sharpe(arm_R), 4),
                    "sharpe_base": round(_sharpe(base_R), 4),
                    "mean_delta_r": round(float(pooled_delta_r.mean()), 4),
                    "median_delta_r": round(float(np.median(pooled_delta_r)), 4),
                },
                "mechanism": {
                    "snap_fire_rate": round(snap_fire_rate, 4),
                    "filled_at_snap_rate": round(filled_at_snap_rate, 4),
                    "delta_p_tp_fills": round(delta_p_tp, 4),
                    "delta_mean_r_on_winners": (
                        round(delta_meanR_win, 4)
                        if delta_meanR_win == delta_meanR_win
                        else None
                    ),
                    "n_winners_pooled": int(n_winners),
                    "delta_mean_time_in_trade_winners_hours": (
                        round(time_delta_hours_mean, 3)
                        if time_delta_hours_mean == time_delta_hours_mean
                        else None
                    ),
                    "delta_mean_time_in_trade_winners_bars_h4": (
                        round(time_delta_bars_mean, 3)
                        if time_delta_bars_mean == time_delta_bars_mean
                        else None
                    ),
                },
            }
            arms_out.append(arm_out)
            pooled_p_values.append(p)

    # BH-FDR across the 12-arm family.
    fdr_rejected = _bh_fdr(pooled_p_values, alpha=FDR_ALPHA)
    for arm, rejected in zip(arms_out, fdr_rejected):
        arm["bh_fdr_rejected"] = bool(rejected)

    # PROTOCOL §6 per-arm verdict.
    for arm in arms_out:
        arm["verdict"] = _classify_arm(arm)

    return {
        "arms": arms_out,
        "grid": {
            "snap_distance": list(snap_distance_grid),
            "snap_source": list(snap_source_grid),
            "n_arms": len(arms_out),
        },
        "folds": [
            {"name": n, "start": s.isoformat(), "end": e.isoformat()}
            for n, s, e in folds
        ],
        "bootstrap": {"seed": seed, "resamples": resamples},
        "fdr": {"method": "BH", "alpha": FDR_ALPHA, "family_size": len(arms_out)},
        "fire_rate_floor": FIRE_RATE_FLOOR,
    }


def _classify_arm(arm: dict) -> str:
    """PROTOCOL §6 per-arm verdict.

    ``alive`` iff ALL:
      - pooled CI-LB > 0
      - positive in ≥ 4 of 5 folds
      - BH-FDR rejects H0 for this arm
      - snap_fire_rate ≥ FIRE_RATE_FLOOR
      - Δ P(TP fills) > 0

    Otherwise:
      - ``inactive_snap_never_fires`` if snap_fire_rate < FIRE_RATE_FLOOR
        (feeds study-level `parked_snap_never_fires` if EVERY arm is inactive)
      - ``parked_weak_effect`` if the point estimate is > 0 but any of the
        other alive criteria fail
      - ``dead`` otherwise
    """
    p = arm["pooled"]
    mech = arm["mechanism"]

    fires_enough = mech["snap_fire_rate"] >= FIRE_RATE_FLOOR
    if not fires_enough:
        return "inactive_snap_never_fires"

    primary_ok = p["ci_low"] > 0
    robust = arm["n_folds_positive"] >= 4
    fdr_ok = arm["bh_fdr_rejected"]
    tp_fill_ok = (mech["delta_p_tp_fills"] or 0.0) > 0.0

    if primary_ok and robust and fdr_ok and tp_fill_ok:
        return "alive"
    if p["delta_sharpe"] > 0:
        return "parked_weak_effect"
    return "dead"


def _study_verdict(arms: list[dict]) -> str:
    """PROTOCOL §6 study-level roll-up.

    - ``alive`` if any arm is alive.
    - ``parked_snap_never_fires`` if EVERY arm is ``inactive_snap_never_fires``
      (i.e. no arm meets the 5 % fire-rate floor).
    - ``parked_daily_only_suffices`` if the ``all`` winner ΔSharpe CI overlaps
      the ``daily_only`` winner's (H2 parsimony). Only computed if the
      study has at least one alive arm.
    - ``parked_weak_effect`` if any arm is ``parked_weak_effect``.
    - ``dead`` otherwise.
    """
    if all(a["verdict"] == "inactive_snap_never_fires" for a in arms):
        return "parked_snap_never_fires"

    alives = [a for a in arms if a["verdict"] == "alive"]
    if alives:
        # H2 parsimony check: if the best `all` arm CI overlaps the best
        # `daily_only` arm CI, prefer `daily_only` — mark as parked.
        best_all = _best_alive_by_source(arms, "all")
        best_daily = _best_alive_by_source(arms, "daily_only")
        if best_all is not None and best_daily is not None:
            ci_all = (best_all["pooled"]["ci_low"], best_all["pooled"]["ci_high"])
            ci_daily = (best_daily["pooled"]["ci_low"], best_daily["pooled"]["ci_high"])
            # Overlap check: intervals [a_lo, a_hi] and [b_lo, b_hi] overlap
            # iff a_lo <= b_hi AND b_lo <= a_hi.
            if ci_all[0] <= ci_daily[1] and ci_daily[0] <= ci_all[1]:
                return "parked_daily_only_suffices"
        return "alive"

    if any(a["verdict"] == "parked_weak_effect" for a in arms):
        return "parked_weak_effect"
    return "dead"


def _best_alive_by_source(arms: list[dict], source: str) -> Optional[dict]:
    winners = [a for a in arms if a["verdict"] == "alive" and a["snap_source"] == source]
    if not winners:
        return None
    return max(winners, key=lambda a: a["pooled"]["delta_sharpe"])


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

def _generator_commit() -> str:
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(_REPO_ROOT), stderr=subprocess.DEVNULL,
        ).decode().strip()
        return sha
    except Exception:
        return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="programs/E022/results.json")
    parser.add_argument("--data-dir", default=None,
                        help="Override PRE-0 data dir (defaults to package location)")
    parser.add_argument("--symbols", default=",".join(SYMBOLS))
    parser.add_argument("--smoke-only-first-arm", action="store_true",
                        help="Only evaluate the first (source, distance) arm — for interface smoke tests")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    log.info("E022 Phase 2 — structure-aware TP snap validation")
    log.info(
        "Grid: snap_distance=%s × snap_source=%s (%d arms)",
        SNAP_DISTANCE_GRID, SNAP_SOURCE_GRID,
        len(SNAP_DISTANCE_GRID) * len(SNAP_SOURCE_GRID),
    )

    all_trades: list[TradeRecord] = []
    per_symbol_meta: dict[str, dict] = {}
    symbols = tuple(s.strip() for s in args.symbols.split(","))
    kwargs = {"data_dir": args.data_dir} if args.data_dir else {}
    for sym in symbols:
        meta, trades = load_paths_ledger(sym, **kwargs)
        per_symbol_meta[sym] = meta
        all_trades.extend(trades)
        log.info(
            "  loaded %s: %d trades, hit_rate=%.4f, mean_r=%.4f",
            sym, len(trades), meta.get("hit_rate", -1), meta.get("mean_r", -1),
        )
    log.info("Total pooled trades: %d", len(all_trades))

    # ------------------------------------------------------------------
    # Pre-compute the four level sets per trade (once, reused across the
    # 3 snap_distance values that share each snap_source).
    # ------------------------------------------------------------------
    log.info("Reconstructing level sets over [entry-%d·H4, entry) ...", LOOKBACK)
    levels_by_trade = _build_levels(all_trades)

    if args.smoke_only_first_arm:
        distance = (SNAP_DISTANCE_GRID[0],)
        source = (SNAP_SOURCE_GRID[0],)
    else:
        distance = SNAP_DISTANCE_GRID
        source = SNAP_SOURCE_GRID

    results = sweep(
        all_trades,
        levels_by_trade,
        snap_distance_grid=distance,
        snap_source_grid=source,
    )

    # -- motivating trade lookup (PROTOCOL §5.3) ------------------------
    motivator = _motivating_trade_summary(all_trades, levels_by_trade)

    payload = {
        "study": "E022",
        "title": "Structure-aware TP snap (order-placement)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator_commit": _generator_commit(),
        "pre_registration": "experiments/E022_structure_aware_tp_snap/PROTOCOL.md",
        "harness": (
            "programs/E022/level_detector.py + programs/E022/rescorer.py "
            "(bypasses programs/_shared/counterfactual_replay/replay.py "
            "adjust_tp semantics — see rescorer.py module docstring)"
        ),
        "symbols": list(symbols),
        "per_symbol_meta": per_symbol_meta,
        "total_trades": len(all_trades),
        "results": results,
        "motivating_trade": motivator,
    }

    payload["study_verdict"] = _study_verdict(results["arms"])
    # Winners / parked lists for reporting convenience.
    payload["winning_arms"] = [
        a["arm_id"] for a in results["arms"] if a["verdict"] == "alive"
    ]
    payload["parked_arms"] = [
        (a["arm_id"], a["verdict"]) for a in results["arms"]
        if a["verdict"].startswith("parked") or a["verdict"] == "inactive_snap_never_fires"
    ]

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    log.info("Wrote %s", out)
    log.info("Study verdict: %s", payload["study_verdict"])
    if payload["winning_arms"]:
        log.info("Winning arms: %s", payload["winning_arms"])


def _motivating_trade_summary(
    trades: list[TradeRecord], levels_by_trade: dict[str, TradeLevels],
) -> dict:
    """PROTOCOL §5.3 case walkthrough. The referenced live ticket
    (GBPUSD 2969136564, 2026-07-16 short 1.35060 → 1.34264) predates the
    PRE-0 ledger window (2015-01 → 2025-12), so it is NOT in the
    ``all_trades`` population; the pre-registration itself notes n = 1
    descriptive-only. We synthesise the arm walk-through against the
    PROTOCOL's declared level values (Path A) so the REPORT can reconcile
    the "no fire" prediction with the empirical rule."""

    entry = 1.35060
    tp = 1.34264
    direction = "short"

    predicted_ladder_top = 1.34111  # PROTOCOL §5.3 — beyond TP
    predicted_round_numbers = [1.34500, 1.35000]

    outcomes: list[dict] = []
    for snap_distance in SNAP_DISTANCE_GRID:
        offset = _snap_offset(snap_distance)
        for snap_source, L_candidates in [
            ("ladder_top", [predicted_ladder_top]),
            ("round_number", predicted_round_numbers),
            ("daily_only", []),  # not known ex-post; the case walkthrough leaves this empty
            ("all", [predicted_ladder_top] + predicted_round_numbers),
        ]:
            new_tp = snap_tp(entry, tp, direction, L_candidates, snap_distance, offset)
            outcomes.append({
                "arm_id": f"{snap_source}_d{int(snap_distance)}",
                "snap_source": snap_source,
                "snap_distance": snap_distance,
                "snap_offset": offset,
                "L_used": L_candidates,
                "new_tp": round(new_tp, 5),
                "fired": bool(new_tp != tp),
            })
    return {
        "ticket": "2969136564",
        "symbol": "GBPUSD",
        "date": "2026-07-16",
        "direction": direction,
        "entry": entry,
        "tp": tp,
        "note": (
            "n=1 descriptive case (PROTOCOL §5.3); this ticket predates "
            "the PRE-0 ledger window (2015-01 → 2025-12), so it is NOT in "
            "the sweep population. Level values are the ones declared in "
            "PROTOCOL §5.3 (ladder_top swing @ 1.34111, round-number set "
            "{1.34500, 1.35000}). Under every arm, the pre-registration "
            "predicts snap does NOT fire."
        ),
        "arm_outcomes": outcomes,
    }


if __name__ == "__main__":
    main()
