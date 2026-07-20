#!/usr/bin/env python3
"""Run E017 Phase 2 validation (Monte Carlo + incident replay + verdict)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "programs" / "E017"))

from confidence_sim import (  # noqa: E402
    Arm,
    CandidateConfig,
    FrozenParams,
    frozen_candidate_grid,
    gauge_convergence_check,
    load_bootstrap_r,
    pareto_dominates,
    replay_incident,
    run_monte_carlo,
)


def _pick_winner(hk_results: list[dict], gc_results: list[dict]) -> dict | None:
    for gc in gc_results:
        for hk in hk_results:
            if hk["p_win"] == gc["p_win"] and pareto_dominates(hk, gc):
                return gc
    return None


def _classify_verdict(
    hk_rows: list[dict],
    gc_s_rows: list[dict],
    gc_t_rows: list[dict],
    *,
    gauge_pass: bool,
    replay: dict,
) -> tuple[str, dict | None, bool]:
    winner = _pick_winner(hk_rows, gc_s_rows)
    if not gauge_pass:
        return "dead", winner, False
    if not replay.get("protective_close_preserved"):
        return "dead", winner, False
    if winner is None:
        # Distinguish capital-cost vs outright failure.
        best_gc = min(gc_s_rows, key=lambda r: r["median_dead_hours"])
        best_hk = min(hk_rows, key=lambda r: r["median_dead_hours"])
        if best_gc["median_dead_hours"] < best_hk["median_dead_hours"] * 0.5:
            return "parked_capital_cost", None, False
        return "dead", None, False
    w_cfg = winner["config"]
    w_pw = winner["p_win"]
    gc_s_match = next(r for r in gc_s_rows if r["config"] == w_cfg and r["p_win"] == w_pw)
    gc_t_match = next(r for r in gc_t_rows if r["config"] == w_cfg and r["p_win"] == w_pw)
    shadow_adds = abs(gc_s_match["median_dead_hours"] - gc_t_match["median_dead_hours"]) >= 24
    verdict = "alive"
    if not shadow_adds:
        verdict = "parked_shadow_adds_nothing"
    return verdict, winner, shadow_adds


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-paths", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--quick", action="store_true", help="500 paths for smoke")
    parser.add_argument(
        "--ledger",
        default=str(_REPO / "programs/E017/data/trade_ledger_EURUSD_H4.json"),
    )
    parser.add_argument(
        "--output",
        default=str(_REPO / "experiments/E017_confidence_gated_cooldown/results.json"),
    )
    args = parser.parse_args()

    n_paths = 500 if args.quick else args.n_paths
    params = FrozenParams()
    if args.quick:
        params = FrozenParams(horizon_days=2_000)
    ledger = Path(args.ledger)
    bootstrap = load_bootstrap_r(ledger) if ledger.is_file() else None

    hk_rows: list[dict] = []
    gc_s_rows: list[dict] = []
    gc_t_rows: list[dict] = []

    for p_win in (0.40, 0.55):
        print(f"MC p_win={p_win} HK baseline ({n_paths} paths)...", flush=True)
        hk_base_cfg = CandidateConfig(
            per_symbol=frozen_candidate_grid()[0].per_symbol,
            gauge=frozen_candidate_grid()[0].gauge,
        )
        hk = run_monte_carlo(
            Arm.HK, hk_base_cfg, params,
            n_paths=n_paths, seed=args.seed, bootstrap_rs=bootstrap, p_win=p_win,
            workers=args.workers,
        )
        hk_rows.append(hk)

        for cfg in frozen_candidate_grid():
            print(f"  GC-S {cfg.label} ...", flush=True)
            gc_s = run_monte_carlo(
                Arm.GC_S, cfg, params,
                n_paths=n_paths, seed=args.seed + 1, bootstrap_rs=bootstrap, p_win=p_win,
                workers=args.workers,
            )
            gc_s_rows.append(gc_s)
            print(f"  GC-T {cfg.label} ...", flush=True)
            gc_t = run_monte_carlo(
                Arm.GC_T, cfg, params,
                n_paths=n_paths, seed=args.seed + 2, bootstrap_rs=bootstrap, p_win=p_win,
                workers=args.workers,
            )
            gc_t_rows.append(gc_t)

    gauge_checks = {
        cfg.label: gauge_convergence_check(params, cfg)
        for cfg in frozen_candidate_grid()
    }
    gauge_pass = all(v["passed"] for v in gauge_checks.values())

    winner = _pick_winner(hk_rows, gc_s_rows)
    replay = replay_incident()

    verdict, winner, shadow_adds = _classify_verdict(
        hk_rows, gc_s_rows, gc_t_rows,
        gauge_pass=gauge_pass, replay=replay,
    )

    out = {
        "meta": {
            "id": "E017",
            "status": "completed",
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "phase": 2,
            "n_paths": n_paths,
            "seed": args.seed,
            "verdict": verdict,
            "winning_config": winner,
        },
        "monte_carlo": {
            "HK": hk_rows,
            "GC-S": gc_s_rows,
            "GC-T": gc_t_rows,
        },
        "gauge_convergence_check": gauge_checks,
        "gauge_convergence_passed": gauge_pass,
        "incident_replay_2026_07_08": replay,
        "h2_shadow_adds_value": shadow_adds,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Verdict: {verdict}")
    print(f"Wrote {out_path}")
    return 0 if verdict == "alive" else 1


if __name__ == "__main__":
    raise SystemExit(main())
