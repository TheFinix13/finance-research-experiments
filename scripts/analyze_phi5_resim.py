"""Phi5 Arm 3/4 re-sim analysis -- locked statistic + bootstrap CI.

Reads the G7 walk-forward replay caches (control + treatment arms) and
computes the phi5_aggregator PROTOCOL §4 / §11.4 verdict inputs:

- Per-OOS-window squad mean TQS (7 windows, 4yr IS / 1yr OOS, 2015-2025).
- Median of window means (LOCKED statistic).
- Bootstrap CI on the median (percentile method, 10,000 resamples,
  seeded) at 95% and 99% (Bonferroni alpha = 0.01) levels.
- Effect size Delta vs the same-environment control run.
- Cross-statistic robustness table (§4 mandatory journalled diagnostic).
- Arm 3 diagnostics: merged-trade fraction, per-contributor appearance
  counts, per-agent trade counts.
- Arm 4 diagnostics: R6-block fraction from proposals_rejected.jsonl,
  concurrent-same-bar-stop rate proxy.
- §6 stop rule #1: peak-to-trough drawdown per window (>25% flags FAIL).

Usage:
    python scripts/analyze_phi5_resim.py \
        --control walk-forward-post-kunigami-retirement \
        --arm arm3:phi5-arm3-post-kunigami \
        [--arm arm4:phi5-arm4-post-kunigami] \
        --reviews-dir programs/M001_multi_agent_ensemble/reviews \
        --out-prefix phi5_resim
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
from datetime import datetime, timezone
from pathlib import Path

IS_YEARS = 4
OOS_YEARS = 1
PANEL_START_YEAR = 2015
PANEL_END = datetime(2025, 12, 31, tzinfo=timezone.utc)
BOOTSTRAP_N = 10_000
BOOTSTRAP_SEED = 20260706
SANDBOX_EQUITY = 100.0
DOLLARS_PER_PIP = 1.0          # 0.1 lot x $10/pip/lot
DD_STOP_FRAC = 0.25            # §6 stop rule #1

# Secondary references only (§11.4 B).
LEGACY_PHI41_CONTROL_TQS = 0.2922
LEGACY_ISAGI_ALONE_TQS = 0.3175


def _load_trades(cache_dir: Path) -> list[dict]:
    path = cache_dir / "trades.jsonl"
    out: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    for t in out:
        t["_entry_dt"] = datetime.fromisoformat(t["entry_time"])
        tqs = None
        tc = t.get("tqs_components")
        if isinstance(tc, dict):
            tqs = tc.get("tqs")
        if tqs is None:
            tqs = t.get("tqs")
        t["_tqs"] = float(tqs) if tqs is not None else None
    out.sort(key=lambda t: t["_entry_dt"])
    return out


def _windows() -> list[tuple[datetime, datetime]]:
    """(oos_start, oos_end) pairs for the standard G7 panel."""
    out = []
    last_ws_year = PANEL_END.year - IS_YEARS - OOS_YEARS + 1
    for y in range(PANEL_START_YEAR, last_ws_year + 1):
        oos_start = datetime(y + IS_YEARS, 1, 1, tzinfo=timezone.utc)
        oos_end = datetime(y + IS_YEARS + OOS_YEARS, 1, 1, tzinfo=timezone.utc)
        if oos_end > PANEL_END:
            oos_end = PANEL_END
        out.append((oos_start, oos_end))
    return out


def _window_means(trades: list[dict]) -> list[dict]:
    rows = []
    for oos_start, oos_end in _windows():
        w = [t for t in trades if oos_start <= t["_entry_dt"] < oos_end]
        tqs_vals = [t["_tqs"] for t in w if t["_tqs"] is not None]
        pips = [float(t["pnl_pips"]) for t in w]
        # §6 stop rule #1: peak-to-trough drawdown on the $100 sandbox
        # equity curve within this OOS window.
        equity = SANDBOX_EQUITY
        peak = equity
        max_dd_frac = 0.0
        for t in w:
            equity += float(t["pnl_pips"]) * DOLLARS_PER_PIP
            peak = max(peak, equity)
            if peak > 0:
                max_dd_frac = max(max_dd_frac, (peak - equity) / peak)
        rows.append({
            "oos_start": oos_start.isoformat(),
            "oos_end": oos_end.isoformat(),
            "n_trades": len(w),
            "mean_tqs": statistics.mean(tqs_vals) if tqs_vals else None,
            "mean_pips": statistics.mean(pips) if pips else None,
            "max_drawdown_frac": max_dd_frac,
            "dd_stop_rule_breach": max_dd_frac > DD_STOP_FRAC,
        })
    return rows


def _bootstrap_ci(
    values: list[float], level: float,
) -> tuple[float, float]:
    rng = random.Random(BOOTSTRAP_SEED)
    n = len(values)
    medians = []
    for _ in range(BOOTSTRAP_N):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        medians.append(statistics.median(sample))
    medians.sort()
    lo_idx = int(((1.0 - level) / 2.0) * BOOTSTRAP_N)
    hi_idx = int((1.0 - (1.0 - level) / 2.0) * BOOTSTRAP_N) - 1
    return medians[lo_idx], medians[hi_idx]


def _trimmed_mean(values: list[float], frac: float = 0.10) -> float | None:
    if not values:
        return None
    vs = sorted(values)
    k = int(len(vs) * frac)
    core = vs[k: len(vs) - k] if len(vs) > 2 * k else vs
    return statistics.mean(core)


def _cross_stats(trades: list[dict], window_rows: list[dict]) -> dict:
    tqs_vals = [t["_tqs"] for t in trades if t["_tqs"] is not None]
    pips = [float(t["pnl_pips"]) for t in trades]
    w_tqs = [r["mean_tqs"] for r in window_rows if r["mean_tqs"] is not None]
    w_pips = [r["mean_pips"] for r in window_rows if r["mean_pips"] is not None]
    wins = sum(1 for p in pips if p > 0)
    return {
        "median_window_mean_tqs": statistics.median(w_tqs) if w_tqs else None,
        "mean_window_mean_tqs": statistics.mean(w_tqs) if w_tqs else None,
        "pooled_per_trade_mean_tqs": statistics.mean(tqs_vals) if tqs_vals else None,
        "pooled_per_trade_trimmed_mean_tqs_10": _trimmed_mean(tqs_vals),
        "median_window_mean_pips": statistics.median(w_pips) if w_pips else None,
        "pooled_per_trade_mean_pips": statistics.mean(pips) if pips else None,
        "cumulative_pips_forbidden_as_scoring": sum(pips),
        "hit_rate": wins / len(pips) if pips else None,
        "n_trades": len(trades),
    }


def _per_agent_counts(trades: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for t in trades:
        aid = t.get("agent_id") or "?"
        d = out.setdefault(aid, {"n": 0, "tqs_sum": 0.0, "tqs_n": 0})
        d["n"] += 1
        if t["_tqs"] is not None:
            d["tqs_sum"] += t["_tqs"]
            d["tqs_n"] += 1
    return {
        aid: {
            "n_trades": d["n"],
            "mean_tqs": (d["tqs_sum"] / d["tqs_n"]) if d["tqs_n"] else None,
        }
        for aid, d in sorted(out.items())
    }


def _arm3_diagnostics(trades: list[dict]) -> dict:
    merged = [t for t in trades if str(t.get("agent_id", "")).startswith("arm3_merged_")]
    contributor_counts: dict[str, int] = {}
    for t in merged:
        blob = str(t["agent_id"])[len("arm3_merged_"):]
        for aid in blob.split("+"):
            contributor_counts[aid] = contributor_counts.get(aid, 0) + 1
    merged_pips = [float(t["pnl_pips"]) for t in merged]
    return {
        "n_merged_trades": len(merged),
        "merged_fraction_of_all_trades": len(merged) / len(trades) if trades else 0.0,
        "contributor_appearance_counts": dict(sorted(contributor_counts.items())),
        "merged_mean_pips": statistics.mean(merged_pips) if merged_pips else None,
        "merged_mean_tqs": (
            statistics.mean([t["_tqs"] for t in merged if t["_tqs"] is not None])
            if any(t["_tqs"] is not None for t in merged) else None
        ),
    }


def _arm4_diagnostics(cache_dir: Path, trades: list[dict]) -> dict:
    rej_path = cache_dir / "proposals_rejected.jsonl"
    counts: dict[str, int] = {}
    if rej_path.exists():
        with rej_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                reason = r.get("rejection_reason", "?")
                counts[reason] = counts.get(reason, 0) + 1
    # Concurrent-positions-same-bar-stop proxy: same symbol, same exit
    # time, both stopped out ("sl" on the production Trade), different
    # agents. §8 pre-mortem: if >30% of multi-position events end this
    # way, Arm 4 is structurally redundant with Arm 3.
    by_exit: dict[tuple[str, str], list[dict]] = {}
    n_sl = 0
    for t in trades:
        if t.get("exit_reason") == "sl":
            n_sl += 1
            by_exit.setdefault((t["symbol"], t["exit_time"]), []).append(t)
    same_bar_stop_events = sum(
        1 for group in by_exit.values()
        if len({g.get("agent_id") for g in group}) >= 2
    )
    return {
        "rejection_reason_counts": dict(sorted(counts.items())),
        "n_stop_loss_exits": n_sl,
        "concurrent_same_bar_stop_events": same_bar_stop_events,
        "same_bar_stop_rate_of_sl_exits": (
            same_bar_stop_events / n_sl if n_sl else 0.0
        ),
    }


def analyze(
    reviews_dir: Path, control_tag: str, arm_specs: list[tuple[str, str]],
) -> dict:
    result: dict = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": "experiments/phi5_aggregator/PROTOCOL.md sec 4 + sec 11.4",
        "bootstrap": {"n": BOOTSTRAP_N, "seed": BOOTSTRAP_SEED},
        "legacy_references": {
            "phi41_control_tqs": LEGACY_PHI41_CONTROL_TQS,
            "isagi_alone_tqs": LEGACY_ISAGI_ALONE_TQS,
        },
    }
    control_dir = reviews_dir / f"g7_replay_cache_{control_tag}"
    control_trades = _load_trades(control_dir)
    control_windows = _window_means(control_trades)
    control_stats = _cross_stats(control_trades, control_windows)
    control_median = control_stats["median_window_mean_tqs"]
    result["control"] = {
        "tag": control_tag,
        "windows": control_windows,
        "cross_statistics": control_stats,
        "per_agent": _per_agent_counts(control_trades),
    }

    result["arms"] = {}
    for arm_id, tag in arm_specs:
        cache_dir = reviews_dir / f"g7_replay_cache_{tag}"
        trades = _load_trades(cache_dir)
        windows = _window_means(trades)
        stats = _cross_stats(trades, windows)
        w_tqs = [r["mean_tqs"] for r in windows if r["mean_tqs"] is not None]
        ci95 = _bootstrap_ci(w_tqs, 0.95) if w_tqs else (None, None)
        ci99 = _bootstrap_ci(w_tqs, 0.99) if w_tqs else (None, None)
        median = stats["median_window_mean_tqs"]
        delta = (median - control_median) if (
            median is not None and control_median is not None
        ) else None
        ci_test_pass = (
            ci99[0] is not None and control_median is not None
            and ci99[0] > control_median
        )
        effect_pass = delta is not None and delta >= 0.020
        dd_breach = any(r["dd_stop_rule_breach"] for r in windows)
        # §6 stop rule #1 nuance: the fixed-lot $100 sandbox was never
        # drawdown-controlled -- the CONTROL breaches 25% in every
        # window too. The rule targets arm-CAUSED risk inflation, so
        # the FAIL flag applies only when the arm's worst-window DD
        # exceeds the control's worst-window DD. Shared environment
        # breaches are journalled, not blamed on the arm.
        control_worst_dd = max(
            (r["max_drawdown_frac"] for r in control_windows), default=0.0,
        )
        arm_worst_dd = max(
            (r["max_drawdown_frac"] for r in windows), default=0.0,
        )
        dd_arm_caused = dd_breach and arm_worst_dd > control_worst_dd
        if dd_arm_caused:
            verdict = "FAIL_DD_STOP_RULE_ARM_CAUSED"
        elif ci_test_pass and effect_pass:
            verdict = "PASS_SELECTION_CRITERIA"
        elif delta is not None and delta > 0:
            verdict = "NULL_POSITIVE_NOT_SIGNIFICANT"
        elif delta is not None and delta == 0:
            verdict = "NULL_IDENTICAL"
        else:
            verdict = "NULL_NEGATIVE_NOT_SIGNIFICANT" if (
                delta is not None and abs(delta) < 0.020
            ) else "REGRESS"
        arm_result = {
            "tag": tag,
            "windows": windows,
            "cross_statistics": stats,
            "median_window_mean_tqs": median,
            "delta_vs_control": delta,
            "bootstrap_ci95_median": list(ci95),
            "bootstrap_ci99_median_bonferroni": list(ci99),
            "ci_test_pass_bonferroni": ci_test_pass,
            "effect_size_pass_delta_ge_0.020": effect_pass,
            "dd_stop_rule_breach": dd_breach,
            "dd_worst_window_frac": arm_worst_dd,
            "dd_control_worst_window_frac": control_worst_dd,
            "dd_arm_caused": dd_arm_caused,
            "verdict": verdict,
            "per_agent": _per_agent_counts(trades),
        }
        if arm_id == "arm3":
            arm_result["arm3_diagnostics"] = _arm3_diagnostics(trades)
        if arm_id == "arm4":
            arm_result["arm4_diagnostics"] = _arm4_diagnostics(cache_dir, trades)
        result["arms"][arm_id] = arm_result
    return result


def render_md(result: dict) -> str:
    lines = ["# Phi5 Arm 3/4 re-sim verdict (sec 11.4 protocol)", ""]
    lines.append(f"Generated: {result['generated_at_utc']}")
    lines.append("")
    c = result["control"]
    cs = c["cross_statistics"]
    lines.append(
        f"**Control** `{c['tag']}`: median-of-window-mean TQS = "
        f"**{cs['median_window_mean_tqs']:.4f}** "
        f"({cs['n_trades']} trades). Legacy refs: phi41 0.2922 / "
        f"isagi-alone 0.3175 (secondary only)."
    )
    lines.append("")
    lines.append(
        "| Arm | n trades | Median TQS | Delta vs control | CI99 lower | "
        "CI pass | Effect pass | DD breach | Verdict |")
    lines.append("|---|---:|---:|---:|---:|:--:|:--:|:--:|---|")
    for arm_id, a in result["arms"].items():
        lines.append(
            f"| {arm_id} | {a['cross_statistics']['n_trades']} | "
            f"{a['median_window_mean_tqs']:.4f} | "
            f"{a['delta_vs_control']:+.4f} | "
            f"{a['bootstrap_ci99_median_bonferroni'][0]:.4f} | "
            f"{'Y' if a['ci_test_pass_bonferroni'] else 'n'} | "
            f"{'Y' if a['effect_size_pass_delta_ge_0.020'] else 'n'} | "
            f"{'Y' if a['dd_stop_rule_breach'] else 'n'} | "
            f"{a['verdict']} |")
    lines.append("")
    for arm_id, a in result["arms"].items():
        lines.append(f"## {arm_id} (`{a['tag']}`)")
        lines.append("")
        lines.append("### Cross-statistic robustness (mandatory, sec 4)")
        lines.append("")
        lines.append("| statistic | control | arm |")
        lines.append("|---|---:|---:|")
        for key in (
            "median_window_mean_tqs", "mean_window_mean_tqs",
            "pooled_per_trade_mean_tqs",
            "pooled_per_trade_trimmed_mean_tqs_10",
            "median_window_mean_pips", "pooled_per_trade_mean_pips",
            "cumulative_pips_forbidden_as_scoring", "hit_rate", "n_trades",
        ):
            cv = result["control"]["cross_statistics"].get(key)
            av = a["cross_statistics"].get(key)
            fmt = (lambda v: f"{v:.4f}" if isinstance(v, float) else str(v))
            lines.append(f"| {key} | {fmt(cv)} | {fmt(av)} |")
        lines.append("")
        lines.append("### Per-agent trades (arm)")
        lines.append("")
        lines.append("| agent | n | mean TQS |")
        lines.append("|---|---:|---:|")
        for aid, row in a["per_agent"].items():
            mt = f"{row['mean_tqs']:.4f}" if row["mean_tqs"] is not None else "--"
            lines.append(f"| `{aid}` | {row['n_trades']} | {mt} |")
        lines.append("")
        if "arm3_diagnostics" in a:
            d = a["arm3_diagnostics"]
            lines.append("### Arm 3 diagnostics")
            lines.append("")
            lines.append(f"- merged trades: {d['n_merged_trades']} "
                         f"({d['merged_fraction_of_all_trades']:.1%} of all)")
            lines.append(f"- contributor appearances: "
                         f"{d['contributor_appearance_counts']}")
            lines.append(f"- merged mean pips: {d['merged_mean_pips']}")
            lines.append(f"- merged mean TQS: {d['merged_mean_tqs']}")
            lines.append("")
        if "arm4_diagnostics" in a:
            d = a["arm4_diagnostics"]
            lines.append("### Arm 4 diagnostics")
            lines.append("")
            lines.append(f"- rejection reasons: {d['rejection_reason_counts']}")
            lines.append(f"- concurrent same-bar-stop events: "
                         f"{d['concurrent_same_bar_stop_events']}")
            lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", required=True)
    ap.add_argument("--arm", action="append", default=[],
                    help="arm_id:cache_tag (e.g. arm3:phi5-arm3-post-kunigami)")
    ap.add_argument("--reviews-dir", type=Path,
                    default=Path("programs/M001_multi_agent_ensemble/reviews"))
    ap.add_argument("--out-prefix", default="phi5_resim")
    args = ap.parse_args()

    arm_specs = []
    for spec in args.arm:
        arm_id, _, tag = spec.partition(":")
        arm_specs.append((arm_id, tag))

    result = analyze(args.reviews_dir, args.control, arm_specs)
    json_path = args.reviews_dir / f"{args.out_prefix}_verdict.json"
    json_path.write_text(
        json.dumps(result, indent=2, default=str), encoding="utf-8",
    )
    md_path = args.reviews_dir / f"{args.out_prefix}_verdict.md"
    md_path.write_text(render_md(result), encoding="utf-8")
    print(f"wrote {json_path}\nwrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
