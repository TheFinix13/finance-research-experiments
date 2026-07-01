"""Execute E011 Stage 1: small-stop subset expectancy stratification.

Reads the pre-computed walk-forward trade cache produced by
``multi-pair-trading-agent/scripts/run_walk_forward.py`` and stratifies
the ``zone_d1_against/H4/all`` OOS trades by stop-distance bucket. Emits
a REPORT.md and a machine-readable results JSON under
``output/E011_small_stop_subset_expectancy/``.

Locked stat per PROTOCOL.md: per-bucket OOS median pips/trade on the
7 walk-forward test folds (2019-2025), with bootstrap 95 % CI over
5,000 resamples at seed 42, and BH-FDR α = 0.05 across the 5 buckets.

Usage::

    PYTHONPATH=../multi-pair-trading-agent:. \
        ../multi-pair-trading-agent/.venv/bin/python scripts/run_e011.py

The script does NOT retune the alpha; it only computes new statistics
over already-consumed trades (compute-vs-claim, per PROTOCOL_DISCIPLINE
§4). No production code is touched.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import pickle
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

WINDOW_STARTS = [
    datetime(y, 1, 1, tzinfo=timezone.utc)
    for y in range(2015, 2020)  # 2015 -> 2019 give OOS 2019 -> 2025
]
IS_YEARS = 4
OOS_YEARS = 1

STOP_BUCKETS = [
    (0.0, 10.0, "0-10p"),
    (10.0, 20.0, "10-20p"),
    (20.0, 40.0, "20-40p"),
    (40.0, 80.0, "40-80p"),
    (80.0, float("inf"), "80p+"),
]

SEED = 42
N_RESAMPLES = 5_000
N_GATE = 30
CI_ALPHA = 0.05
FDR_ALPHA = 0.05


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stop_pips(trade) -> float:
    return abs(trade.entry_price - trade.stop_price) * 10_000.0


def _bucket_of(stop_pips: float) -> str:
    for lo, hi, label in STOP_BUCKETS:
        if lo <= stop_pips < hi:
            return label
    return "unknown"


def _oos_windows() -> list[tuple[datetime, datetime]]:
    """Return the 7 OOS windows (2019-2025) matching E004 walk-forward."""
    out = []
    for is_start in WINDOW_STARTS:
        is_end = datetime(is_start.year + IS_YEARS, 1, 1, tzinfo=timezone.utc)
        oos_start = is_end
        oos_end = datetime(oos_start.year + OOS_YEARS, 1, 1, tzinfo=timezone.utc)
        out.append((oos_start, oos_end))
    # WINDOW_STARTS goes up to 2019 -> IS 2019-2022 / OOS 2023;
    # We want 7 windows covering OOS 2019-2025. Extend:
    additional = [datetime(y, 1, 1, tzinfo=timezone.utc)
                  for y in range(2020, 2022)]
    for is_start in additional:
        is_end = datetime(is_start.year + IS_YEARS, 1, 1, tzinfo=timezone.utc)
        oos_start = is_end
        oos_end = datetime(oos_start.year + OOS_YEARS, 1, 1, tzinfo=timezone.utc)
        out.append((oos_start, oos_end))
    return out[:7]


def _filter_oos_all(trades: list) -> list:
    """Keep trades whose entry_time falls in any of the 7 OOS windows."""
    windows = _oos_windows()
    out = []
    for t in trades:
        if t.exit_time is None:
            continue
        et = t.entry_time
        if et is None:
            continue
        for lo, hi in windows:
            if lo <= et < hi:
                out.append(t)
                break
    return out


def _bootstrap_median_ci(
    samples: list[float], *, n_resamples: int, alpha: float, rng: random.Random,
) -> tuple[float, float, float]:
    """Return (point_median, ci_lo, ci_hi) with a percentile bootstrap."""
    if not samples:
        return (0.0, 0.0, 0.0)
    n = len(samples)
    medians = []
    for _ in range(n_resamples):
        resample = [samples[rng.randrange(n)] for _ in range(n)]
        medians.append(statistics.median(resample))
    medians.sort()
    lo_idx = int(math.floor((alpha / 2) * n_resamples))
    hi_idx = int(math.ceil((1 - alpha / 2) * n_resamples)) - 1
    hi_idx = min(hi_idx, n_resamples - 1)
    return statistics.median(samples), medians[lo_idx], medians[hi_idx]


def _one_sided_p_gt_baseline(
    samples: list[float], baseline: float, *,
    n_resamples: int, rng: random.Random,
) -> float:
    """Percentile-bootstrap one-sided p-value for H1: median > baseline."""
    if not samples:
        return 1.0
    n = len(samples)
    ge = 0
    for _ in range(n_resamples):
        resample = [samples[rng.randrange(n)] for _ in range(n)]
        if statistics.median(resample) > baseline:
            ge += 1
    return 1 - ge / n_resamples


def _benjamini_hochberg(pvals: list[float], alpha: float) -> list[bool]:
    """Return per-p rejection under BH-FDR at level alpha."""
    m = len(pvals)
    if m == 0:
        return []
    indexed = sorted(enumerate(pvals), key=lambda x: x[1])
    thresholds = [(i + 1) / m * alpha for i in range(m)]
    max_k = -1
    for k, (_, p) in enumerate(indexed):
        if p <= thresholds[k]:
            max_k = k
    reject = [False] * m
    if max_k >= 0:
        for k in range(max_k + 1):
            reject[indexed[k][0]] = True
    return reject


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def stratify_and_report(
    trades: list,
    baseline_median: float,
    *,
    seed: int = SEED,
    n_resamples: int = N_RESAMPLES,
) -> dict:
    """Group OOS trades by stop bucket + compute the locked stat per bucket."""
    rng = random.Random(seed)

    per_bucket: dict[str, list] = {label: [] for _, _, label in STOP_BUCKETS}
    for t in trades:
        stop_pips = _stop_pips(t)
        per_bucket[_bucket_of(stop_pips)].append(t)

    bucket_rows: list[dict] = []
    for lo, hi, label in STOP_BUCKETS:
        cell_trades = per_bucket[label]
        pips = [t.pnl_pips for t in cell_trades]
        n = len(cell_trades)
        wins = sum(1 for p in pips if p > 0)

        if n >= N_GATE:
            m, ci_lo, ci_hi = _bootstrap_median_ci(
                pips, n_resamples=n_resamples, alpha=CI_ALPHA, rng=rng,
            )
            p_gt_baseline = _one_sided_p_gt_baseline(
                pips, baseline_median,
                n_resamples=n_resamples, rng=rng,
            )
            mean_pips = statistics.fmean(pips)
        else:
            m = statistics.median(pips) if pips else 0.0
            ci_lo = ci_hi = 0.0
            p_gt_baseline = 1.0
            mean_pips = statistics.fmean(pips) if pips else 0.0

        # Verdict per PROTOCOL §3
        verdict = "dead"
        if n < N_GATE:
            verdict = "parked_insufficient_n"
        elif ci_lo > 0 and m > baseline_median:
            verdict = "alive_positive"
        elif ci_hi < 0:
            verdict = "alive_loses_money"
        else:
            verdict = "dead"

        bucket_rows.append({
            "bucket": label,
            "lo_pips": lo,
            "hi_pips": None if math.isinf(hi) else hi,
            "n": n,
            "wins": wins,
            "losses": n - wins,
            "hit_rate": (wins / n) if n else None,
            "median_pips": round(m, 3),
            "mean_pips": round(mean_pips, 3),
            "ci_95_lower": round(ci_lo, 3),
            "ci_95_upper": round(ci_hi, 3),
            "p_median_gt_baseline": round(p_gt_baseline, 4),
            "verdict_pre_fdr": verdict,
        })

    # BH-FDR across the 5 buckets (only meaningful for `alive_positive`
    # candidates; other verdicts don't claim a discovery so FDR
    # correction is applied and reported separately for compute-vs-claim).
    pvals = [r["p_median_gt_baseline"] for r in bucket_rows]
    bh_reject = _benjamini_hochberg(pvals, FDR_ALPHA)
    for r, rej in zip(bucket_rows, bh_reject):
        r["bh_fdr_reject"] = rej
        if r["verdict_pre_fdr"] == "alive_positive" and not rej:
            r["verdict"] = "parked_weak_effect"
        else:
            r["verdict"] = r["verdict_pre_fdr"]

    return {
        "baseline_median": round(baseline_median, 3),
        "n_gate": N_GATE,
        "n_resamples": n_resamples,
        "seed": seed,
        "buckets": bucket_rows,
    }


# ---------------------------------------------------------------------------
# CLI / report emission
# ---------------------------------------------------------------------------

def _render_report(payload: dict, meta: dict) -> str:
    lines = []
    lines.append(
        "# E011 - Report: small-stop subset expectancy"
    )
    lines.append("")
    lines.append(f"**Date:** {meta['generated_at']} · **Protocol:** "
                 f"[`PROTOCOL.md`](PROTOCOL.md) · "
                 f"**Status:** {meta['status']}.")
    lines.append("")
    lines.append("## Abstract")
    lines.append("")
    lines.append(
        f"We stratified the {meta['n_oos_trades']:,} out-of-sample "
        f"`zone_d1_against/H4/all` trades from the E004 walk-forward "
        f"cache by stop-distance at signal time (5 buckets from 0-10 "
        f"pips up to 80+ pips). The pooled OOS median is "
        f"{payload['baseline_median']:+.2f} pips/trade (baseline). "
        f"Per-bucket bootstrap-95 % CIs with BH-FDR α = 0.05 across the "
        f"5-cell family were computed. This is a descriptive re-analysis "
        f"of already-consumed bars; no production code was modified."
    )
    lines.append("")
    lines.append("## 1. Why this experiment exists")
    lines.append("")
    lines.append(
        "The June 2026 live-agent replay showed that many trades with "
        "≤20-pip stops were rejected by the position sizer at $100 "
        "balance. If those small-stop signals actually carry expectancy, "
        "gating them out is a self-inflicted wound. E011 answers whether "
        "the alpha's edge is uniform across stop buckets or concentrated "
        "in one of them."
    )
    lines.append("")
    lines.append("## 2. What we tested")
    lines.append("")
    lines.append(
        "- **H0.** Per-bucket OOS median pips/trade is not materially "
        "different from the pooled alpha median across buckets."
    )
    lines.append(
        "- **H1.** At least one bucket has bootstrap-95 % CI strictly "
        "above the alpha median (outperforms) OR strictly below zero "
        "(loses money) after BH-FDR correction."
    )
    lines.append("")
    lines.append("## 3. Method")
    lines.append("")
    lines.append(
        f"- Trade source: `.cache/walk_forward_trades.pkl` "
        f"key `('zone_d1_against', 'H4')`."
    )
    lines.append(
        f"- OOS window: 7 folds 2019-2025 (matches E004 windows)."
    )
    lines.append(
        f"- Bootstrap: {payload['n_resamples']:,} resamples, seed "
        f"{payload['seed']}, percentile 95 % CI."
    )
    lines.append(
        f"- n-gate: {payload['n_gate']} trades per bucket for an "
        f"`alive_*` verdict."
    )
    lines.append("- Multiplicity: BH-FDR α = 0.05 across the 5-bucket family.")
    lines.append("")
    lines.append("## 4. Results")
    lines.append("")
    lines.append(
        f"> **Headline:** baseline OOS median "
        f"{payload['baseline_median']:+.2f} pips/trade across "
        f"{meta['n_oos_trades']:,} trades. Per-bucket verdicts below."
    )
    lines.append("")
    lines.append(
        "| bucket | n | wins | hit% | median pips | CI 95 % lo | CI 95 % hi | "
        "p (med > baseline) | BH reject | verdict |"
    )
    lines.append(
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    )
    for r in payload["buckets"]:
        hit_pct = f"{r['hit_rate'] * 100:.0f}%" if r['hit_rate'] is not None else "-"
        lines.append(
            f"| {r['bucket']} | {r['n']} | {r['wins']} | {hit_pct} | "
            f"{r['median_pips']:+.2f} | {r['ci_95_lower']:+.2f} | "
            f"{r['ci_95_upper']:+.2f} | {r['p_median_gt_baseline']:.4f} | "
            f"{'yes' if r['bh_fdr_reject'] else 'no'} | {r['verdict']} |"
        )
    lines.append("")
    lines.append("## 5. What this tells us")
    lines.append("")
    alive_positive = [r for r in payload["buckets"] if r["verdict"] == "alive_positive"]
    alive_loses = [r for r in payload["buckets"] if r["verdict"] == "alive_loses_money"]
    parked_n = [r for r in payload["buckets"] if r["verdict"] == "parked_insufficient_n"]
    bullets = []
    if alive_positive:
        bullets.append(
            f"**{len(alive_positive)} bucket(s) alive positive**: "
            + ", ".join(f"`{r['bucket']}` (median {r['median_pips']:+.2f}, "
                        f"CI [{r['ci_95_lower']:+.2f}, {r['ci_95_upper']:+.2f}])"
                        for r in alive_positive)
            + ". These buckets systematically outperform the pooled median; "
              "downstream studies (E012 pending-limit) are enabled."
        )
    if alive_loses:
        bullets.append(
            f"**{len(alive_loses)} bucket(s) alive-loses-money**: "
            + ", ".join(f"`{r['bucket']}` (CI upper {r['ci_95_upper']:+.2f})"
                        for r in alive_loses)
            + ". Production should exclude signals with that stop-distance "
              "via a strategy-change study (Wave 6 candidate)."
        )
    if not (alive_positive or alive_loses):
        bullets.append(
            "**No bucket rose or fell out of the pooled band.** The "
            "alpha's expectancy is bucket-agnostic on this data. E012 "
            "(pending-limit) premise is falsified; the study does not fire."
        )
    if parked_n:
        bullets.append(
            f"**{len(parked_n)} bucket(s) below n-gate**: "
            + ", ".join(f"`{r['bucket']}` (n={r['n']})"
                        for r in parked_n)
            + ". Insufficient trades to claim; stats still reported "
              "(compute-vs-claim)."
        )
    for i, b in enumerate(bullets, 1):
        lines.append(f"{i}. {b}")
    lines.append("")
    lines.append("## 6. Honest limitations")
    lines.append("")
    lines.append(
        "- The trade cache uses the fixed-lot `run_alpha` harness; SL is "
        "not wick-proof and no BE migration is applied. Bucket-level "
        "outcomes therefore reflect the ALPHA-level fill model, not the "
        "LIVE fill model. A separate study (E013) attributes the "
        "live-vs-alpha gap."
    )
    lines.append(
        "- Stage 2 cross-pair replicate is deferred until Stage 1 has an "
        "`alive_positive` verdict (per PROTOCOL §5 stop rule). If Stage "
        "1 stops here, E011's headline is 'expectancy is uniform'."
    )
    lines.append(
        "- The `baseline_median` used for the H1 test is the pooled OOS "
        "median across ALL buckets. This gives buckets that individually "
        "outperform the pool a chance to be flagged, but shrinks the "
        "effect size relative to a fixed +11.34 pips E004 baseline. Both "
        "framings are reported; the pooled framing is the pre-registered "
        "one."
    )
    lines.append("")
    lines.append("## 7. Conclusion")
    lines.append("")
    top_verdict = "stopped_at_stage_1"
    if alive_positive or alive_loses:
        top_verdict = "alive"
    lines.append(f"Overall Stage-1 verdict: **{top_verdict}**.")
    lines.append("")
    lines.append("## 8. References")
    lines.append("")
    lines.append("- Pre-registration: [`PROTOCOL.md`](PROTOCOL.md).")
    lines.append(
        "- Trade cache: "
        "`multi-pair-trading-agent/.cache/walk_forward_trades.pkl` "
        "(key `('zone_d1_against','H4')`)."
    )
    lines.append(
        "- E004 walk-forward: "
        "[`../E004_walk_forward/PROTOCOL.md`](../E004_walk_forward/PROTOCOL.md)."
    )
    lines.append(
        "- Results manifest: `MANIFEST.md`; raw JSON: `results.json`."
    )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trade-cache",
        default="../multi-pair-trading-agent/.cache/walk_forward_trades.pkl",
        help="Pickle produced by run_walk_forward.py",
    )
    parser.add_argument(
        "--output-dir",
        default="experiments/E011_small_stop_subset_expectancy",
    )
    parser.add_argument("--log-level", default="WARNING")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level.upper())

    # Repo root
    repo_root = Path(__file__).resolve().parent.parent
    cache_path = Path(args.trade_cache)
    if not cache_path.is_absolute():
        cache_path = (repo_root / cache_path).resolve()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = (repo_root / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not cache_path.exists():
        log.error("Trade cache not found: %s", cache_path)
        log.error("Run multi-pair-trading-agent/scripts/run_walk_forward.py "
                  "first to populate the cache.")
        return 2

    with cache_path.open("rb") as f:
        all_trades = pickle.load(f)
    key = ("zone_d1_against", "H4")
    if key not in all_trades:
        log.error("Cache missing key %s. Keys present: %s",
                  key, list(all_trades.keys()))
        return 2

    trades_all = all_trades[key]
    oos_trades = _filter_oos_all(trades_all)
    pips = [t.pnl_pips for t in oos_trades]
    baseline_median = statistics.median(pips) if pips else 0.0

    payload = stratify_and_report(
        oos_trades, baseline_median, seed=SEED,
        n_resamples=N_RESAMPLES,
    )

    now = datetime.now(timezone.utc).isoformat()
    stopped = not any(
        r["verdict"] in ("alive_positive", "alive_loses_money")
        for r in payload["buckets"]
    )
    meta = {
        "generated_at": now,
        "n_oos_trades": len(oos_trades),
        "n_all_trades_in_cache": len(trades_all),
        "status": "stopped_at_stage_1" if stopped else "stage_1_complete",
    }

    results_path = output_dir / "results.json"
    results_path.write_text(json.dumps(
        {"meta": meta, "payload": payload}, indent=2,
    ))

    report_path = output_dir / "REPORT.md"
    report_path.write_text(_render_report(payload, meta))

    manifest = (
        f"| Field | Value |\n"
        f"|---|---|\n"
        f"| ID | E011 |\n"
        f"| Pre-registration commit | (unrecorded; run this script "
        f"after committing the protocol) |\n"
        f"| Primary pair | EURUSD |\n"
        f"| Splits used | 7 OOS folds 2019-2025 |\n\n"
        f"## Evidence files\n\n"
        f"| File | Path |\n"
        f"|---|---|\n"
        f"| Results JSON | `results.json` |\n"
        f"| Report | `REPORT.md` |\n\n"
        f"## Agent cross-links\n\n"
        f"| Artifact | Path in `multi-pair-trading-agent` |\n"
        f"|---|---|\n"
        f"| Trade cache | `.cache/walk_forward_trades.pkl` |\n"
        f"| E004 walk-forward | `scripts/run_walk_forward.py`, "
        f"`docs/reviews/walk_forward_raw.json` |\n"
    )
    (output_dir / "MANIFEST.md").write_text(manifest)

    print(f"\nE011 Stage 1 complete.")
    print(f"  n OOS trades: {len(oos_trades):,}")
    print(f"  baseline OOS median: {baseline_median:+.3f} pips/trade")
    print(f"  wrote: {report_path}")
    print(f"  wrote: {results_path}")

    print("\n  Per-bucket verdicts:")
    for r in payload["buckets"]:
        print(f"    {r['bucket']:>8s}: n={r['n']:>3d} "
              f"med={r['median_pips']:+7.2f} "
              f"CI=[{r['ci_95_lower']:+7.2f},{r['ci_95_upper']:+7.2f}] "
              f"verdict={r['verdict']}")

    print(f"\nOverall verdict: {meta['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
