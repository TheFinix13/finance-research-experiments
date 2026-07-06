"""Phase W-barou v1.2 verdict analysis (PROTOCOL_v1.2.md sec 4/5).

Computes the pre-registered statistics from the two v1.2 replay caches
against the locked Arm 4 comparators:

- cannibalisation ratio = 1 - (Barou n, full squad) / (Barou n, lo1-bachira)
  -- LAND requires < 0.50 (baseline 0.557).
- squad median-of-window-mean TQS  -- LAND requires >= 0.3593.
- Barou mean TQS >= 0.34; REVERT if Barou n < 400 or mean TQS < 0.30.
- Rin guardrail: mean TQS >= 0.36 AND n >= 350.
- continuation same-bar-stop rate < 30% using the Phi5 sec 8 arithmetic
  (sl exits sharing symbol+exit_time with another agent's sl exit),
  restricted to barou_continuation_entry=True trades. The instant-stop
  variant (bars_held == 0) is journalled alongside as a diagnostic.

Usage:
    python scripts/analyze_wbarou12.py \
        --reviews-dir programs/M001_multi_agent_ensemble/reviews \
        --out-prefix wbarou12_verdict
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import analyze_phi5_resim as base  # noqa: E402  (shared locked arithmetic)

CONTROL_TAG = "phi5-arm4-post-kunigami"
TREATMENT_TAG = "wbarou12-arm4"
BAROU = "barou_shoei"
RIN = "itoshi_rin"

# PROTOCOL_v1.2.md sec 5 locked thresholds.
CANNIBALISATION_LAND = 0.50
SQUAD_TQS_FLOOR = 0.3593
BAROU_TQS_LAND = 0.34
BAROU_TQS_REVERT = 0.30
BAROU_N_REVERT = 400
SAME_BAR_STOP_BOUND = 0.30
RIN_TQS_FLOOR = 0.36
RIN_N_FLOOR = 350
SQUAD_TRADES_HALT = 3000


def _load_proposal_continuation_index(cache_dir: Path) -> set[tuple[str, int]]:
    """(agent_id, tick_id) pairs whose rationale has
    barou_continuation_entry=True."""
    out: set[tuple[str, int]] = set()
    path = cache_dir / "proposals_all.jsonl"
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            p = json.loads(line)
            rat = p.get("rationale") or {}
            if rat.get("barou_continuation_entry") is True:
                out.add((p.get("agent_id"), int(p.get("tick_id"))))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviews-dir", type=Path,
                    default=Path("programs/M001_multi_agent_ensemble/reviews"))
    ap.add_argument("--out-prefix", default="wbarou12_verdict")
    args = ap.parse_args()
    rd = args.reviews_dir

    control = base._load_trades(rd / f"g7_replay_cache_{CONTROL_TAG}")
    treat = base._load_trades(rd / f"g7_replay_cache_{TREATMENT_TAG}")
    lo1 = base._load_trades(
        rd / f"g7_leave_one_out_{TREATMENT_TAG}" / "lo1_bachira_meguru",
    )

    ctrl_windows = base._window_means(control)
    treat_windows = base._window_means(treat)
    ctrl_median = base._cross_stats(control, ctrl_windows)[
        "median_window_mean_tqs"]
    treat_median = base._cross_stats(treat, treat_windows)[
        "median_window_mean_tqs"]

    ctrl_agents = base._per_agent_counts(control)
    treat_agents = base._per_agent_counts(treat)
    lo1_agents = base._per_agent_counts(lo1)

    barou_present = treat_agents.get(BAROU, {"n_trades": 0, "mean_tqs": None})
    barou_absent = lo1_agents.get(BAROU, {"n_trades": 0, "mean_tqs": None})
    cannibalisation = (
        1.0 - barou_present["n_trades"] / barou_absent["n_trades"]
        if barou_absent["n_trades"] else None
    )

    # Continuation attribution: join trades -> proposals on
    # (agent_id, source_tick_id).
    cont_idx = _load_proposal_continuation_index(
        rd / f"g7_replay_cache_{TREATMENT_TAG}",
    )
    barou_trades = [t for t in treat if t.get("agent_id") == BAROU]
    cont_trades = [
        t for t in barou_trades
        if (BAROU, int(t.get("source_tick_id", -1))) in cont_idx
    ]
    # Phi5 sec 8 same-bar-stop arithmetic restricted to continuation
    # trades: sl exits sharing (symbol, exit_time) with another AGENT's
    # sl exit.
    sl_by_exit: dict[tuple[str, str], set[str]] = {}
    for t in treat:
        if t.get("exit_reason") == "sl":
            sl_by_exit.setdefault(
                (t["symbol"], t["exit_time"]), set(),
            ).add(t.get("agent_id"))
    cont_sl = [t for t in cont_trades if t.get("exit_reason") == "sl"]
    cont_same_bar = sum(
        1 for t in cont_sl
        if len(sl_by_exit.get((t["symbol"], t["exit_time"]), set())) >= 2
    )
    same_bar_rate = cont_same_bar / len(cont_sl) if cont_sl else 0.0
    instant_stop = sum(1 for t in cont_sl if int(t.get("bars_held", 99)) == 0)
    instant_rate = instant_stop / len(cont_trades) if cont_trades else 0.0

    rin = treat_agents.get(RIN, {"n_trades": 0, "mean_tqs": None})

    # ---- verdict per PROTOCOL_v1.2.md sec 5 -------------------------
    checks = {
        "cannibalisation_below_50pct": (
            cannibalisation is not None
            and cannibalisation < CANNIBALISATION_LAND
        ),
        "squad_tqs_floor": (
            treat_median is not None and treat_median >= SQUAD_TQS_FLOOR
        ),
        "barou_tqs_land": (
            barou_present["mean_tqs"] is not None
            and barou_present["mean_tqs"] >= BAROU_TQS_LAND
        ),
        "same_bar_stop_below_30pct": same_bar_rate < SAME_BAR_STOP_BOUND,
        "rin_guardrail": (
            rin["mean_tqs"] is not None
            and rin["mean_tqs"] >= RIN_TQS_FLOOR
            and rin["n_trades"] >= RIN_N_FLOOR
        ),
    }
    revert = (
        barou_present["n_trades"] < BAROU_N_REVERT
        or (barou_present["mean_tqs"] or 0.0) < BAROU_TQS_REVERT
    )
    halt = len(treat) < SQUAD_TRADES_HALT
    cont_fired = any(True for _ in cont_idx)
    if halt:
        verdict = "HALT_STRUCTURAL_BREAK"
    elif not cont_fired:
        # Pre-registered stop rule: 0 continuation proposals halts the
        # experiment. Whether that is a plumbing bug or a structural
        # premise failure is determined by the postmortem, not here.
        verdict = "HALT_NO_CONTINUATION_PROPOSALS"
    elif revert:
        verdict = "REVERT"
    elif all(checks.values()):
        verdict = "LAND"
    else:
        verdict = "AMBIGUOUS_NULL"

    result = {
        "protocol": "experiments/phase_w_barou/PROTOCOL_v1.2.md sec 4/5",
        "control_tag": CONTROL_TAG,
        "treatment_tag": TREATMENT_TAG,
        "squad": {
            "control_median_window_mean_tqs": ctrl_median,
            "treatment_median_window_mean_tqs": treat_median,
            "delta": (
                treat_median - ctrl_median
                if None not in (treat_median, ctrl_median) else None
            ),
            "control_n_trades": len(control),
            "treatment_n_trades": len(treat),
        },
        "barou": {
            "present_bachira": barou_present,
            "absent_bachira_lo1": barou_absent,
            "cannibalisation_ratio": cannibalisation,
            "baseline_cannibalisation_11_7": 0.557,
        },
        "continuation": {
            "n_continuation_proposals": len(cont_idx),
            "n_continuation_trades": len(cont_trades),
            "n_continuation_sl_exits": len(cont_sl),
            "same_bar_stop_rate_sec8_arithmetic": same_bar_rate,
            "instant_stop_rate_bars_held_0_diagnostic": instant_rate,
            "continuation_mean_tqs": (
                statistics.mean(
                    [t["_tqs"] for t in cont_trades if t["_tqs"] is not None],
                )
                if any(t["_tqs"] is not None for t in cont_trades) else None
            ),
        },
        "rin_guardrail": rin,
        "per_agent_treatment": treat_agents,
        "per_agent_control": ctrl_agents,
        "checks": checks,
        "revert_triggered": revert,
        "verdict": verdict,
    }
    out_path = args.reviews_dir / f"{args.out_prefix}.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
