"""Phase X-kunigami Wild Card gate verdict analysis.

Implements experiments/phase_x_kunigami_wildcard/PROTOCOL.md sec 5
(locked verdict rules) against the gated walk-forward cache vs the
canonical Arm 4 baseline:

- LAND iff worst-window max DD reduced by >= 20% relative vs baseline
  AND squad median-of-window-mean TQS >= baseline - 0.005
  AND squad trade count >= 60% of baseline.
- REVERT if trade count < 40% of baseline OR TQS drops > 0.010.
- Stop rule: NOT-MEASURABLE if the gate never tripped (zero
  ``kunigami_wildcard_dd_gate`` rejections journalled).
- Anything else -> AMBIGUOUS (postmortem, no retuning).

Window/DD machinery is identical to scripts/analyze_phi5_resim.py
(same panel, same $1/pip sandbox convention).

Usage:
    python scripts/analyze_kunigate.py \
        --baseline phi5-arm4-post-kunigami \
        --gated kunigate-arm4 \
        --reviews-dir programs/M001_multi_agent_ensemble/reviews \
        --out-prefix kunigate_arm4
"""
from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyze_phi5_resim import (  # noqa: E402
    _cross_stats,
    _load_trades,
    _per_agent_counts,
    _window_means,
)

# PROTOCOL.md sec 5, locked.
LAND_DD_RELATIVE_REDUCTION = 0.20
LAND_TQS_TOLERANCE = 0.005
LAND_TRADE_FLOOR_FRAC = 0.60
REVERT_TRADE_FLOOR_FRAC = 0.40
REVERT_TQS_DROP = 0.010
GATE_REJECTION_REASON = "kunigami_wildcard_dd_gate"


def _count_gate_vetoes(cache_dir: Path) -> int:
    path = cache_dir / "proposals_rejected.jsonl"
    if not path.exists():
        return 0
    n = 0
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and GATE_REJECTION_REASON in line:
                r = json.loads(line)
                if r.get("rejection_reason") == GATE_REJECTION_REASON:
                    n += 1
    return n


def analyze(reviews_dir: Path, baseline_tag: str, gated_tag: str) -> dict:
    base_dir = reviews_dir / f"g7_replay_cache_{baseline_tag}"
    gate_dir = reviews_dir / f"g7_replay_cache_{gated_tag}"

    base_trades = _load_trades(base_dir)
    gate_trades = _load_trades(gate_dir)
    base_windows = _window_means(base_trades)
    gate_windows = _window_means(gate_trades)
    base_stats = _cross_stats(base_trades, base_windows)
    gate_stats = _cross_stats(gate_trades, gate_windows)

    base_worst_dd = max(
        (r["max_drawdown_frac"] for r in base_windows), default=0.0,
    )
    gate_worst_dd = max(
        (r["max_drawdown_frac"] for r in gate_windows), default=0.0,
    )
    dd_relative_reduction = (
        (base_worst_dd - gate_worst_dd) / base_worst_dd
        if base_worst_dd > 0 else 0.0
    )

    base_tqs = base_stats["median_window_mean_tqs"]
    gate_tqs = gate_stats["median_window_mean_tqs"]
    tqs_delta = (
        gate_tqs - base_tqs
        if gate_tqs is not None and base_tqs is not None else None
    )
    trade_frac = (
        gate_stats["n_trades"] / base_stats["n_trades"]
        if base_stats["n_trades"] else 0.0
    )
    n_vetoes = _count_gate_vetoes(gate_dir)

    # Locked verdict order: stop rule first (untestable mechanic beats
    # any pass/fail), then REVERT (starvation/damage), then LAND.
    checks = {
        "gate_ever_tripped": n_vetoes > 0,
        "dd_reduced_ge_20pct": dd_relative_reduction >= LAND_DD_RELATIVE_REDUCTION,
        "tqs_within_tolerance": (
            tqs_delta is not None and tqs_delta >= -LAND_TQS_TOLERANCE
        ),
        "trades_ge_60pct": trade_frac >= LAND_TRADE_FLOOR_FRAC,
        "revert_trades_lt_40pct": trade_frac < REVERT_TRADE_FLOOR_FRAC,
        "revert_tqs_drop_gt_0.010": (
            tqs_delta is not None and tqs_delta < -REVERT_TQS_DROP
        ),
    }
    if not checks["gate_ever_tripped"]:
        verdict = "NOT_MEASURABLE_GATE_NEVER_TRIPPED"
    elif checks["revert_trades_lt_40pct"] or checks["revert_tqs_drop_gt_0.010"]:
        verdict = "REVERT"
    elif (
        checks["dd_reduced_ge_20pct"]
        and checks["tqs_within_tolerance"]
        and checks["trades_ge_60pct"]
    ):
        verdict = "LAND"
    else:
        verdict = "AMBIGUOUS"

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": "experiments/phase_x_kunigami_wildcard/PROTOCOL.md sec 5",
        "baseline": {
            "tag": baseline_tag,
            "windows": base_windows,
            "cross_statistics": base_stats,
            "worst_window_dd_frac": base_worst_dd,
            "per_agent": _per_agent_counts(base_trades),
        },
        "gated": {
            "tag": gated_tag,
            "windows": gate_windows,
            "cross_statistics": gate_stats,
            "worst_window_dd_frac": gate_worst_dd,
            "n_gate_vetoes": n_vetoes,
            "per_agent": _per_agent_counts(gate_trades),
        },
        "dd_relative_reduction": dd_relative_reduction,
        "tqs_delta_vs_baseline": tqs_delta,
        "trade_count_fraction_of_baseline": trade_frac,
        "checks": checks,
        "verdict": verdict,
    }


def render_md(result: dict) -> str:
    b = result["baseline"]
    g = result["gated"]
    lines = [
        "# Phase X-kunigami Wild Card gate verdict (PROTOCOL sec 5)",
        "",
        f"Generated: {result['generated_at_utc']}",
        "",
        f"Baseline `{b['tag']}` vs gated `{g['tag']}`.",
        "",
        "| metric | baseline | gated |",
        "|---|---:|---:|",
        f"| worst-window max DD | {b['worst_window_dd_frac']:.1%} | "
        f"{g['worst_window_dd_frac']:.1%} |",
        f"| median-of-window-mean TQS | "
        f"{b['cross_statistics']['median_window_mean_tqs']:.4f} | "
        f"{g['cross_statistics']['median_window_mean_tqs']:.4f} |",
        f"| trades | {b['cross_statistics']['n_trades']} | "
        f"{g['cross_statistics']['n_trades']} |",
        f"| gate vetoes journalled | -- | {g['n_gate_vetoes']} |",
        "",
        f"- DD relative reduction: **{result['dd_relative_reduction']:+.1%}** "
        f"(LAND needs >= +20%)",
        f"- TQS delta: **{result['tqs_delta_vs_baseline']:+.4f}** "
        f"(LAND tolerance -0.005; REVERT below -0.010)",
        f"- Trade retention: **{result['trade_count_fraction_of_baseline']:.1%}** "
        f"(LAND floor 60%; REVERT below 40%)",
        "",
        "Checks: "
        + ", ".join(f"{k}={'Y' if v else 'n'}" for k, v in result["checks"].items()),
        "",
        f"## VERDICT: **{result['verdict']}**",
        "",
        "## Per-window drawdown",
        "",
        "| OOS window | baseline DD | gated DD | baseline n | gated n |",
        "|---|---:|---:|---:|---:|",
    ]
    for rb, rg in zip(b["windows"], g["windows"]):
        lines.append(
            f"| {rb['oos_start'][:10]} | {rb['max_drawdown_frac']:.1%} | "
            f"{rg['max_drawdown_frac']:.1%} | {rb['n_trades']} | "
            f"{rg['n_trades']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--gated", required=True)
    ap.add_argument("--reviews-dir", type=Path,
                    default=Path("programs/M001_multi_agent_ensemble/reviews"))
    ap.add_argument("--out-prefix", default="kunigate_arm4")
    args = ap.parse_args()

    result = analyze(args.reviews_dir, args.baseline, args.gated)
    json_path = args.reviews_dir / f"{args.out_prefix}_verdict.json"
    json_path.write_text(
        json.dumps(result, indent=2, default=str), encoding="utf-8",
    )
    md_path = args.reviews_dir / f"{args.out_prefix}_verdict.md"
    md_path.write_text(render_md(result), encoding="utf-8")
    print(f"wrote {json_path}\nwrote {md_path}")
    print(f"VERDICT: {result['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
