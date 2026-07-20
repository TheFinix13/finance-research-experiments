"""Execute E014 Stage 1: quality-score entry gate on zone_d1_against H4.

Runs the deployed alpha (`SupplyDemandAlpha` with the E004-locked
`zone_d1_against` HTF filter) against a QUALIFIED-zone universe, where
zones with `quality_score < theta` are filtered out. Three thresholds
{30, 50, 70} are scored per walk-forward window; the winning theta per
IS window is locked, and the pooled OOS trades under the locked
per-window theta produce the E014 verdict.

Per PROTOCOL.md §3, the alpha is unchanged; only the zone source is
replaced (`ctx.zones = [qz.zone for qz in detect_qualified_zones(bars) if
qz.quality.quality_score >= theta]`).

Usage::

    PYTHONPATH=../multi-pair-trading-agent:. \
        ../multi-pair-trading-agent/.venv/bin/python scripts/run_e014.py
"""
from __future__ import annotations

import argparse
import copy
import json
import logging
import math
import random
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from agent.alphas.backtest import run_alpha
from agent.alphas.concepts import SupplyDemandAlpha
from agent.config import load_config
from agent.data.loader import BarLoader, df_to_bars
from agent.detectors.zones import detect_qualified_zones
from agent.rules.engine import PrecomputedContext, precompute
from agent.types import Bar, Timeframe

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Locked parameters (PROTOCOL §3)
# ---------------------------------------------------------------------------

SYMBOL = "EURUSD"
TIMEFRAME = Timeframe.H4
FULL_START = datetime(2015, 1, 1, tzinfo=timezone.utc)
FULL_END = datetime(2025, 12, 1, tzinfo=timezone.utc)
IS_YEARS = 4
OOS_YEARS = 1
WINDOW_STARTS = [
    datetime(y, 1, 1, tzinfo=timezone.utc)
    for y in range(2015, 2015 + 7)  # 7 windows -> OOS 2019..2025
]
QUALITY_THRESHOLDS = (30.0, 50.0, 70.0)
BASELINE_MEDIAN = 11.34  # E004 locked OOS median pips/trade
SEED = 42
N_RESAMPLES = 5_000
N_GATE = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_alpha(cfg):
    return SupplyDemandAlpha(
        cfg,
        htf_align="D1", htf_align_mode="against",
        htf_lookback=10, htf_min_move_pips=60.0,
    )


def _shim_ctx_with_zones(base_ctx: PrecomputedContext, zones) -> PrecomputedContext:
    """Return a shallow copy of ``base_ctx`` with ``zones`` replaced."""
    shim = copy.copy(base_ctx)
    shim.zones = zones
    return shim


def _in_window(t, lo, hi) -> bool:
    return lo <= t.entry_time < hi and t.exit_time is not None


def _pips(t) -> float:
    return float(t.pnl_pips or 0.0)


def _sharpe(pips_list: list[float]) -> float | None:
    if len(pips_list) < 2:
        return None
    mean = statistics.fmean(pips_list)
    sd = statistics.pstdev(pips_list)
    if sd == 0:
        return None
    return (mean / sd) * math.sqrt(66.0)  # annualise via ~66 H4 trades/yr


def _bootstrap_median_ci(
    samples: list[float], *, n_resamples: int, rng: random.Random,
) -> tuple[float, float, float]:
    if not samples:
        return 0.0, 0.0, 0.0
    n = len(samples)
    medians = sorted(
        statistics.median(samples[rng.randrange(n)] for _ in range(n))
        for _ in range(n_resamples)
    )
    lo = medians[int(math.floor(0.025 * n_resamples))]
    hi = medians[int(math.ceil(0.975 * n_resamples)) - 1]
    return statistics.median(samples), lo, hi


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default="experiments/E014_quality_score_entry_gate",
    )
    parser.add_argument("--log-level", default="WARNING")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level.upper())

    repo_root = Path(__file__).resolve().parent.parent
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = (repo_root / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    loader = BarLoader(cache_root=cfg.data_dir)
    print(f"Loading {SYMBOL} {TIMEFRAME.value} bars {FULL_START.year}-{FULL_END.year} ...")
    df = loader.get(SYMBOL, TIMEFRAME, FULL_START, FULL_END, refresh=False)
    bars = df_to_bars(df, TIMEFRAME)
    print(f"  {len(bars):,} bars")

    print("\nPrecomputing base context (raw zones)...")
    base_ctx = precompute(bars, cfg)
    print(f"  raw zones: {len(base_ctx.zones):,}")

    print("\nComputing qualified zones ...")
    qualified = detect_qualified_zones(bars, min_impulse_pips=30.0)
    print(f"  qualified zones: {len(qualified):,}")

    per_theta_trades: dict[float, list] = {}
    for theta in QUALITY_THRESHOLDS:
        kept = [qz.zone for qz in qualified if qz.quality.quality_score >= theta]
        print(f"\nRunning alpha with theta = {theta:.0f} "
              f"({len(kept):,} zones passing) ...")
        shim = _shim_ctx_with_zones(base_ctx, kept)
        alpha = _make_alpha(cfg)
        trades = run_alpha(alpha, bars, cfg, ctx=shim, start_index=200)
        per_theta_trades[theta] = trades
        print(f"  {len(trades):,} trades")

    rng = random.Random(SEED)
    per_window_locked_theta = []
    per_window_details = []
    pooled_oos_trades: list = []

    for w_idx, is_start in enumerate(WINDOW_STARTS):
        is_end = datetime(is_start.year + IS_YEARS, 1, 1, tzinfo=timezone.utc)
        oos_start = is_end
        oos_end = datetime(oos_start.year + OOS_YEARS, 1, 1, tzinfo=timezone.utc)
        if oos_end > FULL_END:
            oos_end = FULL_END

        theta_scores = {}
        for theta in QUALITY_THRESHOLDS:
            is_trades = [t for t in per_theta_trades[theta]
                         if _in_window(t, is_start, is_end)]
            pips = [_pips(t) for t in is_trades]
            sharpe = _sharpe(pips)
            theta_scores[theta] = {
                "n_is": len(is_trades),
                "sharpe_is": sharpe,
                "median_is": statistics.median(pips) if pips else 0.0,
            }
        winner = max(
            QUALITY_THRESHOLDS,
            key=lambda th: theta_scores[th]["sharpe_is"] or float("-inf"),
        )
        per_window_locked_theta.append(winner)

        oos_trades = [t for t in per_theta_trades[winner]
                      if _in_window(t, oos_start, oos_end)]
        pooled_oos_trades.extend(oos_trades)
        oos_pips = [_pips(t) for t in oos_trades]

        per_window_details.append({
            "window": w_idx + 1,
            "is_start": is_start.isoformat(),
            "is_end": is_end.isoformat(),
            "oos_start": oos_start.isoformat(),
            "oos_end": oos_end.isoformat(),
            "theta_scores_is": {str(k): v for k, v in theta_scores.items()},
            "locked_theta": winner,
            "oos_n": len(oos_trades),
            "oos_median_pips": statistics.median(oos_pips) if oos_pips else 0.0,
            "oos_hit_rate": (
                sum(1 for p in oos_pips if p > 0) / len(oos_pips)
                if oos_pips else None
            ),
        })

    pooled_pips = [_pips(t) for t in pooled_oos_trades]
    baseline_count_est = 855  # from E011 raw-zone alpha run
    trade_count_ratio = (
        len(pooled_oos_trades) / baseline_count_est
        if baseline_count_est else 0.0
    )
    median, ci_lo, ci_hi = _bootstrap_median_ci(
        pooled_pips, n_resamples=N_RESAMPLES, rng=rng,
    )
    hit_rate = (
        sum(1 for p in pooled_pips if p > 0) / len(pooled_pips)
        if pooled_pips else None
    )

    # Verdict per PROTOCOL §3
    if len(pooled_oos_trades) < N_GATE:
        verdict = "parked_insufficient_n"
    elif trade_count_ratio < 0.25:
        verdict = "parked_low_yield"
    elif ci_lo > BASELINE_MEDIAN and trade_count_ratio >= 0.40:
        verdict = "alive_positive"
    elif ci_hi < BASELINE_MEDIAN:
        verdict = "dead"
    else:
        verdict = "parked_weak_effect"

    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "meta": {
            "generated_at": now,
            "symbol": SYMBOL,
            "timeframe": TIMEFRAME.value,
            "thresholds": list(QUALITY_THRESHOLDS),
            "baseline_median_pips": BASELINE_MEDIAN,
            "baseline_trade_count_estimate": baseline_count_est,
            "n_gate": N_GATE,
            "n_resamples": N_RESAMPLES,
            "seed": SEED,
        },
        "per_theta_trade_counts": {
            str(th): len(per_theta_trades[th]) for th in QUALITY_THRESHOLDS
        },
        "per_window": per_window_details,
        "locked_theta_sequence": per_window_locked_theta,
        "pooled_oos": {
            "n": len(pooled_oos_trades),
            "trade_count_ratio_vs_baseline": round(trade_count_ratio, 3),
            "hit_rate": hit_rate,
            "median_pips": round(median, 3),
            "ci_95_lower": round(ci_lo, 3),
            "ci_95_upper": round(ci_hi, 3),
        },
        "verdict": verdict,
    }
    (output_dir / "results.json").write_text(json.dumps(payload, indent=2))

    # Report
    lines = []
    lines.append("# E014 - Report: quality-score entry gate")
    lines.append("")
    lines.append(f"**Date:** {now} · **Protocol:** [`PROTOCOL.md`](PROTOCOL.md) · **Status:** stage_1_complete.")
    lines.append("")
    lines.append("## Abstract")
    lines.append("")
    lines.append(
        f"We tested three quality-score thresholds ({', '.join(str(int(t)) for t in QUALITY_THRESHOLDS)}) "
        f"as an entry gate on `zone_d1_against/H4/all`. On the 7 walk-forward windows, "
        f"per-window IS Sharpe picks a locked theta; pooled OOS trades under those "
        f"locked thetas yielded {len(pooled_oos_trades):,} trades with median "
        f"{median:+.2f} pips/trade and bootstrap 95% CI [{ci_lo:+.2f}, {ci_hi:+.2f}]. "
        f"E004 baseline median is {BASELINE_MEDIAN:+.2f}. Trade-count vs baseline: "
        f"{trade_count_ratio:.0%}. Verdict: **{verdict}**."
    )
    lines.append("")
    lines.append("## 4. Results")
    lines.append("")
    lines.append("### 4.1 Per-window locked-theta table")
    lines.append("")
    lines.append("| window | IS Sharpe θ=30 | IS Sharpe θ=50 | IS Sharpe θ=70 | locked θ | OOS n | OOS median |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|")
    for w in per_window_details:
        s = w["theta_scores_is"]
        s30 = s["30.0"]["sharpe_is"]
        s50 = s["50.0"]["sharpe_is"]
        s70 = s["70.0"]["sharpe_is"]
        def _fmt(x):
            return f"{x:+.3f}" if x is not None else "n/a"
        lines.append(
            f"| {w['window']} | {_fmt(s30)} | {_fmt(s50)} | {_fmt(s70)} | "
            f"{w['locked_theta']:.0f} | {w['oos_n']} | {w['oos_median_pips']:+.2f} |"
        )
    lines.append("")
    lines.append("### 4.2 Pooled OOS")
    lines.append("")
    lines.append(f"- n trades: {len(pooled_oos_trades):,}")
    lines.append(f"- Trade-count ratio vs raw baseline (~{baseline_count_est}): {trade_count_ratio:.1%}")
    lines.append(f"- Hit rate: {(hit_rate*100 if hit_rate is not None else 0):.1f}%")
    lines.append(f"- Median pips/trade: {median:+.2f}")
    lines.append(f"- Bootstrap-95 % CI: [{ci_lo:+.2f}, {ci_hi:+.2f}]")
    lines.append(f"- Baseline (E004): {BASELINE_MEDIAN:+.2f}")
    lines.append("")
    lines.append(f"## 7. Conclusion: **{verdict}**")
    lines.append("")
    if verdict == "alive_positive":
        lines.append(
            "The quality gate strictly outperforms the baseline. E015 "
            "(conviction-from-quality sizing) is enabled per PROTOCOL §5."
        )
    elif verdict == "dead":
        lines.append(
            "The quality gate destroys the alpha's edge. E015 is NOT "
            "launched; the deployed cell's raw-zone universe is preserved."
        )
    elif verdict == "parked_low_yield":
        lines.append(
            "Trade-count fell below 25% of baseline; the gate is too "
            "aggressive to matter in production. Consider lower "
            "thresholds in an amendment or a separate future study."
        )
    else:
        lines.append(
            "The verdict is weak: the CI overlaps the baseline median; the "
            "gate does not clearly help or hurt. Downstream E015 does not "
            "fire; a re-design or larger data slice is required."
        )
    lines.append("")
    lines.append("## 8. References")
    lines.append("")
    lines.append("- Pre-registration: [`PROTOCOL.md`](PROTOCOL.md).")
    lines.append(f"- Trade cache: computed inline; per-theta counts stored in `results.json`.")
    lines.append(
        "- Related: `agent/detectors/zones.py::compute_zone_quality` "
        "(quality-score formula, frozen)."
    )

    report_path = output_dir / "REPORT.md"
    report_path.write_text("\n".join(lines) + "\n")

    manifest = (
        f"| Field | Value |\n"
        f"|---|---|\n"
        f"| ID | E014 |\n"
        f"| Pre-registration commit | (see git log) |\n"
        f"| Primary pair | {SYMBOL} |\n"
        f"| Splits used | 7 IS/OOS walk-forward folds 2015-2025 |\n"
    )
    (output_dir / "MANIFEST.md").write_text(manifest)

    print(f"\nE014 Stage 1 complete.")
    print(f"  Pooled OOS n: {len(pooled_oos_trades):,}")
    print(f"  Trade-count ratio vs baseline: {trade_count_ratio:.1%}")
    print(f"  Pooled OOS median: {median:+.2f} pips  CI [{ci_lo:+.2f}, {ci_hi:+.2f}]")
    print(f"  Baseline (E004): {BASELINE_MEDIAN:+.2f}")
    print(f"  Locked-theta sequence: {per_window_locked_theta}")
    print(f"  Verdict: {verdict}")
    print(f"  wrote: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
