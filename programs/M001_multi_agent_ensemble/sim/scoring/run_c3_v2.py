"""C3 v2 -- distinctness-aware non-cannibalisation evaluator (ADVISORY).

Pre-registration: `experiments/c3_v2_distinctness/PROTOCOL.md`
(2026-07-14, committed before any C3 v2 number was computed). Formal
amendment: G7 PROTOCOL sec 11.14. Verdicts under this definition are
ADVISORY until the user ratifies the amendment; C3 v1
(`run_g7_final_verdict.evaluate_c3_final`) stays verdict-bearing.

Definition (PROTOCOL sec 2, locked):

* Two trades are DUPLICATES iff (symbol, direction, source_tick_id,
  entry, stop, take_profit) match, prices rounded to 7 dp (0.001 pip).
* For excluded agent `a`, a peer trade is DISTINCT iff its key is not
  in the set of `a`'s BASELINE trade keys.
* Reduction ratio per (peer, window) is computed on distinct trades
  only, with the same `lo1_distinct <= 0 -> 0.0` guard, 0.50 max
  reduction and 4-of-7 clean-window thresholds as v1.

CLI (side-by-side report on banked caches)
------------------------------------------

    PYTHONPATH=../multi-pair-trading-agent:. \
        M001_PRODUCTION_REPO=../multi-pair-trading-agent \
        ../multi-pair-trading-agent/.venv/bin/python \
        -m programs.M001_multi_agent_ensemble.sim.scoring.run_c3_v2 \
        --baseline-cache-dir <baseline>/ --lo1-root <reviews>/ \
        --lo1-tag post-V --arm phi41 --tag c3v2-phi41 \
        --out-dir programs/M001_multi_agent_ensemble/reviews
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from programs.M001_multi_agent_ensemble.sim.scoring.run_g7_final_verdict import (
    G7_FINAL_ROSTER,
    _trades_of,
    _window_counts,
    evaluate_c3_final,
    load_oos_trades,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_g7_v1_checkpoint_gate import (
    CRIT3_MAX_CANNIBAL_FRACTION,
    CRIT3_MIN_PASSING_WINDOWS,
    CriterionResult,
    _g7_windows,
)

log = logging.getLogger(__name__)

# Price rounding for the trade-plan identity key (PROTOCOL sec 2.1):
# 1e-7 = 0.001 pip on 4-decimal majors. Phase W measured full-float
# identity on all contested ticks, so this is conservative.
KEY_PRICE_DECIMALS: int = 7

TradePlanKey = tuple[str, str, Any, float, float, float]


def trade_plan_key(t: dict) -> TradePlanKey:
    """PROTOCOL sec 2.1 trade-plan identity key."""
    def _r(x: Any) -> float:
        try:
            return round(float(x), KEY_PRICE_DECIMALS)
        except (TypeError, ValueError):
            return float("nan")
    return (
        str(t.get("symbol")),
        str(t.get("direction")),
        t.get("source_tick_id"),
        _r(t.get("entry")),
        _r(t.get("stop")),
        _r(t.get("take_profit")),
    )


def _window_reduction_ratio_v2(baseline_n: int, lo1_n: int) -> float:
    """Same guard semantics as the v1 final evaluator."""
    if lo1_n <= 0:
        return 0.0
    return (lo1_n - baseline_n) / lo1_n


def evaluate_c3_v2(
    excluded_id: str,
    *,
    baseline_trades: list[dict],
    lo1_trades: list[dict],
    roster: tuple[str, ...],
    n_windows: int,
) -> CriterionResult:
    """C3 v2 per `experiments/c3_v2_distinctness/PROTOCOL.md` sec 2.2.

    Identical to ``evaluate_c3_final`` except each peer's trades are
    filtered to those DISTINCT from the excluded agent's baseline
    trade-plan keys, on both the baseline and lo1 sides.
    """
    excluded_keys = {
        trade_plan_key(t) for t in _trades_of(baseline_trades, excluded_id)
    }

    def _distinct(trades: list[dict]) -> list[dict]:
        return [t for t in trades if trade_plan_key(t) not in excluded_keys]

    peer_counts_b: dict[str, list[int]] = {}
    peer_counts_l: dict[str, list[int]] = {}
    duplicate_share: dict[str, dict[str, Any]] = {}
    for peer in roster:
        if peer == excluded_id:
            continue
        base_all = _trades_of(baseline_trades, peer)
        lo1_all = _trades_of(lo1_trades, peer)
        base_distinct = _distinct(base_all)
        lo1_distinct = _distinct(lo1_all)
        peer_counts_b[peer] = _window_counts(base_distinct, n_windows)
        peer_counts_l[peer] = _window_counts(lo1_distinct, n_windows)
        duplicate_share[peer] = {
            "lo1_n": len(lo1_all),
            "lo1_duplicates": len(lo1_all) - len(lo1_distinct),
            "lo1_duplicate_share": (
                round(1.0 - len(lo1_distinct) / len(lo1_all), 4)
                if lo1_all else 0.0
            ),
            "baseline_n": len(base_all),
            "baseline_duplicates": len(base_all) - len(base_distinct),
        }

    clean_windows = 0
    per_window: list[dict[str, Any]] = []
    for w in range(n_windows):
        worst_peer: str | None = None
        worst_ratio = 0.0
        for peer in peer_counts_b:
            ratio = _window_reduction_ratio_v2(
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
            "definition": "c3_v2_distinctness PROTOCOL sec 2.2 (ADVISORY)",
            "clean_windows": clean_windows,
            "windows_required": CRIT3_MIN_PASSING_WINDOWS,
            "max_reduction_threshold": CRIT3_MAX_CANNIBAL_FRACTION,
            "per_window": per_window,
            "duplicate_share": duplicate_share,
        },
    )


# ---------------------------------------------------------------------------
# Side-by-side report
# ---------------------------------------------------------------------------

def run_side_by_side(
    *,
    baseline_cache_dir: Path,
    lo1_root: Path,
    lo1_tag: str,
    arm: str,
    tag: str,
    out_dir: Path | None = None,
    roster: tuple[str, ...] = G7_FINAL_ROSTER,
) -> dict[str, Any]:
    windows = _g7_windows()
    n_windows = len(windows)
    baseline_trades = load_oos_trades(
        baseline_cache_dir / "trades.jsonl", windows,
    )
    if not baseline_trades:
        raise FileNotFoundError(
            f"baseline cache has no OOS trades: {baseline_cache_dir}"
        )
    lo1_dir = lo1_root / f"g7_leave_one_out_{lo1_tag}"

    per_agent: dict[str, Any] = {}
    for aid in roster:
        p = lo1_dir / f"lo1_{aid}" / "trades.jsonl"
        if not p.exists():
            log.warning("lo1 cache missing for excluded=%s at %s", aid, p)
            per_agent[aid] = {"status": "lo1_cache_missing"}
            continue
        lo1_trades = load_oos_trades(p, windows)
        v1 = evaluate_c3_final(
            aid, baseline_trades=baseline_trades, lo1_trades=lo1_trades,
            roster=roster, n_windows=n_windows,
        )
        v2 = evaluate_c3_v2(
            aid, baseline_trades=baseline_trades, lo1_trades=lo1_trades,
            roster=roster, n_windows=n_windows,
        )
        worst_dup = max(
            v2.evidence["duplicate_share"].values(),
            key=lambda d: d["lo1_duplicate_share"],
            default=None,
        )
        per_agent[aid] = {
            "status": "computed",
            "v1_clean_windows": int(v1.statistic),
            "v1_pass": v1.passed,
            "v2_clean_windows": int(v2.statistic),
            "v2_pass": v2.passed,
            "v1_per_window": v1.evidence["per_window"],
            "v2_per_window": v2.evidence["per_window"],
            "duplicate_share": v2.evidence["duplicate_share"],
            "worst_peer_lo1_duplicate_share": (
                worst_dup["lo1_duplicate_share"] if worst_dup else 0.0
            ),
        }

    result = {
        "tag": tag,
        "arm": arm,
        "protocol": "experiments/c3_v2_distinctness/PROTOCOL.md",
        "advisory": True,
        "baseline_cache": str(baseline_cache_dir),
        "lo1_root": str(lo1_root),
        "lo1_tag": lo1_tag,
        "n_windows": n_windows,
        "per_agent": per_agent,
    }
    if out_dir is not None:
        odir = Path(out_dir)
        odir.mkdir(parents=True, exist_ok=True)
        (odir / f"c3_v2_side_by_side_{tag}.json").write_text(
            json.dumps(result, indent=2, default=str), encoding="utf-8",
        )
        (odir / f"c3_v2_side_by_side_{tag}.md").write_text(
            render_side_by_side_md(result), encoding="utf-8",
        )
    return result


def render_side_by_side_md(result: dict[str, Any]) -> str:
    lines = [
        f"# C3 v1 vs v2 side-by-side ({result['tag']}) -- ADVISORY",
        "",
        "Definition: `experiments/c3_v2_distinctness/PROTOCOL.md` "
        "(G7 sec 11.14). C3 v1 remains verdict-bearing until the user "
        "ratifies the amendment.",
        "",
        f"- Aggregator arm: `{result['arm']}`",
        f"- Baseline cache: `{result['baseline_cache']}`",
        f"- lo1 caches: `{result['lo1_root']}/g7_leave_one_out_"
        f"{result['lo1_tag']}/lo1_*`",
        "",
        "| Agent | C3 v1 clean | v1 pass | C3 v2 clean | v2 pass | "
        "worst-peer lo1 duplicate share |",
        "|---|---|---|---|---|---|",
    ]
    for aid, row in result["per_agent"].items():
        if row.get("status") != "computed":
            lines.append(f"| `{aid}` | — | — | — | — | ({row.get('status')}) |")
            continue
        lines.append(
            f"| `{aid}` | {row['v1_clean_windows']}/7 | "
            f"{'✅' if row['v1_pass'] else '❌'} | "
            f"{row['v2_clean_windows']}/7 | "
            f"{'✅' if row['v2_pass'] else '❌'} | "
            f"{row['worst_peer_lo1_duplicate_share']:.1%} |"
        )
    lines.append("")
    lines.append("## Per-agent v2 windows + duplicate shares")
    for aid, row in result["per_agent"].items():
        if row.get("status") != "computed":
            continue
        lines.append("")
        lines.append(f"### {aid}")
        w1 = ", ".join(
            f"w{p['window']}:{p['worst_reduction']:.2f}"
            f"{'' if p['clean'] else '!'}"
            for p in row["v1_per_window"]
        )
        w2 = ", ".join(
            f"w{p['window']}:{p['worst_reduction']:.2f}"
            f"{'' if p['clean'] else '!'}"
            for p in row["v2_per_window"]
        )
        lines.append(f"- v1 worst reductions: {w1}")
        lines.append(f"- v2 worst reductions: {w2}")
        for peer, d in row["duplicate_share"].items():
            if d["lo1_duplicates"] or d["baseline_duplicates"]:
                lines.append(
                    f"- {peer}: lo1 {d['lo1_duplicates']}/{d['lo1_n']} "
                    f"duplicates ({d['lo1_duplicate_share']:.1%}); baseline "
                    f"{d['baseline_duplicates']}/{d['baseline_n']}"
                )
    lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_c3_v2",
        description="C3 v1 vs v2 side-by-side report (ADVISORY).",
    )
    p.add_argument("--baseline-cache-dir", type=Path, required=True)
    p.add_argument("--lo1-root", type=Path, required=True)
    p.add_argument("--lo1-tag", required=True)
    p.add_argument("--arm", required=True, choices=("phi41", "arm4"))
    p.add_argument("--tag", required=True)
    p.add_argument("--out-dir", type=Path,
                   default=Path("programs/M001_multi_agent_ensemble/reviews"))
    p.add_argument("-v", "--verbose", action="count", default=0)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
    )
    result = run_side_by_side(
        baseline_cache_dir=args.baseline_cache_dir,
        lo1_root=args.lo1_root,
        lo1_tag=args.lo1_tag,
        arm=args.arm,
        tag=args.tag,
        out_dir=args.out_dir,
    )
    print(f"C3 v1 vs v2 [{args.tag}] ({args.arm}) -- ADVISORY")
    for aid, row in result["per_agent"].items():
        if row.get("status") != "computed":
            print(f"  {aid:<18} ({row.get('status')})")
            continue
        print(
            f"  {aid:<18} v1 {row['v1_clean_windows']}/7 "
            f"{'PASS' if row['v1_pass'] else 'fail'}  ->  "
            f"v2 {row['v2_clean_windows']}/7 "
            f"{'PASS' if row['v2_pass'] else 'fail'}  "
            f"(dup {row['worst_peer_lo1_duplicate_share']:.0%})"
        )
    return 0


if __name__ == "__main__":                                 # pragma: no cover
    sys.exit(main())
