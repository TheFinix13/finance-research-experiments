#!/usr/bin/env python3
"""Run E019 Phase 2 validation.

Evaluates the frozen §4/§5 candidate grid on the pre-registered PRIMARY
metric (CDaR-adjusted return ``RaC_beta``) with bootstrap-95% CIs, the
capital / operational guardrails, gauge convergence, the 2026-07-08 incident
replay, and the §7 multiplicity accounting (BH-FDR, PBO, deflated statistic),
then classifies the verdict per PROTOCOL §6 and writes ``results.json``.

Single-process, numpy-vectorised over paths (no ProcessPoolExecutor — it
fails under the Cursor sandbox, the E017 lesson).

CLI::

    python3 programs/E019/run_e019_validation.py                 # full N=10k
    python3 programs/E019/run_e019_validation.py --quick         # smoke
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "programs" / "E019"))

from confidence_sim import (  # noqa: E402
    Arm,
    DGP,
    CandidateConfig,
    FrozenParams,
    benjamini_hochberg,
    bootstrap_ci,
    bootstrap_superiority_pvalue,
    deflated_statistic,
    frozen_candidate_grid,
    gauge_convergence_check,
    load_bootstrap_r,
    probability_backtest_overfitting,
    replay_incident,
    simulate_cell,
    simulate_job,
)


# DGP cells: bootstrap (p_win ignored) + synthetic at each frozen p_win.
def _dgp_cells() -> list[tuple[DGP, float]]:
    return [
        (DGP.BOOTSTRAP, float("nan")),
        (DGP.SYNTHETIC, 0.40),
        (DGP.SYNTHETIC, 0.55),
    ]


def _cell_key(dgp: DGP, p_win: float, rho: float) -> str:
    tag = dgp.value if dgp == DGP.BOOTSTRAP else f"{dgp.value}(p={p_win})"
    return f"{tag}|rho={rho}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-paths", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=8,
                        help="process-pool workers (1 = serial). Pools work "
                             "outside the Cursor sandbox.")
    parser.add_argument("--quick", action="store_true", help="fast smoke run")
    parser.add_argument(
        "--ledger",
        default=str(_REPO / "programs/E017/data/trade_ledger_EURUSD_H4.json"),
    )
    parser.add_argument(
        "--output",
        default=str(_REPO / "experiments/E019_confidence_recovery_riskadjusted/results.json"),
    )
    args = parser.parse_args()

    if args.quick:
        n_paths = 400
        params = FrozenParams(horizon_days=1_500, bootstrap_resamples=800)
        rhos = [0.0]
        dgp_cells = [(DGP.BOOTSTRAP, float("nan")), (DGP.SYNTHETIC, 0.40)]
    else:
        n_paths = args.n_paths
        params = FrozenParams()
        rhos = [0.0, 0.5]
        dgp_cells = _dgp_cells()

    sorted_rs = None
    ledger = Path(args.ledger)
    if ledger.is_file():
        sorted_rs = np.sort(np.asarray(load_bootstrap_r(ledger), dtype=float))

    grid = frozen_candidate_grid()
    t0 = time.time()
    seed = args.seed

    # ---- Build the flat job list over every (arm, config, dgp, rho) cell ----
    jobs: list[tuple] = []
    job_meta: list[tuple] = []   # (arm, label, cell_key)
    for dgp, p_win in dgp_cells:
        pw = 0.5 if dgp == DGP.BOOTSTRAP else p_win
        for rho in rhos:
            ck = _cell_key(dgp, p_win, rho)
            jobs.append((Arm.AK, grid[0], params, dgp, rho, pw, n_paths, seed, sorted_rs))
            job_meta.append((Arm.AK, grid[0].label, ck))
            for cfg in grid:
                jobs.append((Arm.GR_S, cfg, params, dgp, rho, pw, n_paths, seed + 1, sorted_rs))
                job_meta.append((Arm.GR_S, cfg.label, ck))
                jobs.append((Arm.GR_T, cfg, params, dgp, rho, pw, n_paths, seed + 2, sorted_rs))
                job_meta.append((Arm.GR_T, cfg.label, ck))

    n_cells = len(jobs)
    results: list = [None] * n_cells

    def _store(i, res):
        results[i] = res

    if args.workers > 1:
        from concurrent.futures import ProcessPoolExecutor, as_completed
        done = 0
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            fut_to_i = {pool.submit(simulate_job, jobs[i]): i for i in range(n_cells)}
            for fut in as_completed(fut_to_i):
                i = fut_to_i[fut]
                _store(i, fut.result())
                done += 1
                arm, lbl, ck = job_meta[i]
                print(f"[{done}/{n_cells}] {arm.value} {lbl} {ck} "
                      f"({time.time()-t0:.0f}s)", flush=True)
    else:
        for i in range(n_cells):
            _store(i, simulate_job(jobs[i]))
            arm, lbl, ck = job_meta[i]
            print(f"[{i+1}/{n_cells}] {arm.value} {lbl} {ck} "
                  f"({time.time()-t0:.0f}s)", flush=True)

    # ---- Reassemble results by cell / arm / config ----
    ak_summ: dict[str, dict] = {}
    ak_arrays: dict[str, np.ndarray] = {}
    gr_s: list[dict] = []
    gr_t: list[dict] = []
    grs_rac: dict[str, dict[str, np.ndarray]] = {}
    grs_res: dict[str, dict[str, object]] = {}
    for (arm, lbl, ck) in job_meta:
        grs_rac.setdefault(ck, {})
        grs_res.setdefault(ck, {})
    for i, (arm, lbl, ck) in enumerate(job_meta):
        res = results[i]
        summ = res.summary()
        summ["cell"] = ck
        if arm == Arm.AK:
            ak_summ[ck] = summ
            ak_arrays[ck] = res.rac
        elif arm == Arm.GR_S:
            gr_s.append(summ)
            grs_rac[ck][lbl] = res.rac
            grs_res[ck][lbl] = summ
        else:
            gr_t.append(summ)

    # ---- Gauge convergence (§4a) ----
    gauge_checks = {cfg.label: gauge_convergence_check(params, cfg) for cfg in grid}
    gauge_pass = all(v["passed"] for v in gauge_checks.values())

    # ---- Incident replay (descriptive, n=1) ----
    replay = replay_incident(params)

    # ---- Primary-metric gate evaluation, per config across all cells ----
    all_cells = list(ak_arrays.keys())
    config_labels = [cfg.label for cfg in grid]
    gate_rows: list[dict] = []
    per_config_pvals: dict[str, float] = {}

    for cfg in grid:
        lbl = cfg.label
        cell_details = []
        wins_all = True
        dd_ok_all = True
        ruin_ok_all = True
        ttr_ok_all = True
        worst_pval = 0.0
        for ck in all_cells:
            gr_vals = grs_rac[ck][lbl]
            ci = bootstrap_ci(gr_vals, n_resamples=params.bootstrap_resamples,
                              seed=seed + 7, statistic=np.median)
            ak_point = ak_summ[ck]["median_rac_beta"]
            pval = bootstrap_superiority_pvalue(
                gr_vals, ak_point, n_resamples=params.bootstrap_resamples,
                seed=seed + 9, statistic=np.median,
            )
            worst_pval = max(worst_pval, pval)
            primary_win = ci["ci_low"] > ak_point
            grs = grs_res[ck][lbl]
            aks = ak_summ[ck]
            dd_ok = grs["worst_max_drawdown"] <= aks["worst_max_drawdown"] * 1.02
            ruin_ok = grs["risk_of_ruin"] <= aks["risk_of_ruin"] + 0.005
            ttr_ok = grs["median_time_to_resume_hours"] <= max(
                aks["median_time_to_resume_hours"], 1e-9) * 1.0 + 1e-9
            wins_all &= primary_win
            dd_ok_all &= dd_ok
            ruin_ok_all &= ruin_ok
            ttr_ok_all &= ttr_ok
            cell_details.append({
                "cell": ck,
                "gr_s_median_rac": grs["median_rac_beta"],
                "gr_s_rac_ci_low": ci["ci_low"],
                "gr_s_rac_ci_high": ci["ci_high"],
                "ak_median_rac": ak_point,
                "primary_win": bool(primary_win),
                "dd_guardrail_ok": bool(dd_ok),
                "ruin_guardrail_ok": bool(ruin_ok),
                "time_to_resume_guardrail_ok": bool(ttr_ok),
                "bootstrap_pvalue": pval,
            })
        per_config_pvals[lbl] = worst_pval
        gate_rows.append({
            "config": lbl,
            "primary_win_all_cells": bool(wins_all),
            "dd_guardrail_all_cells": bool(dd_ok_all),
            "ruin_guardrail_all_cells": bool(ruin_ok_all),
            "time_to_resume_guardrail_all_cells": bool(ttr_ok_all),
            "alive_candidate": bool(wins_all and dd_ok_all and ruin_ok_all
                                    and ttr_ok_all and gauge_pass
                                    and replay["protective_close_preserved"]),
            "cells": cell_details,
        })

    # ---- H2: GR-S vs GR-T on the primary metric (headline cell) ----
    head = all_cells[0]
    h2_rows = []
    shadow_adds_any = False
    for cfg in grid:
        lbl = cfg.label
        gs = grs_res[head][lbl]["median_rac_beta"]
        gt = next(r for r in gr_t if r["cell"] == head and r["config"] == lbl)["median_rac_beta"]
        rel = abs(gs - gt) / max(abs(gs), abs(gt), 1e-9)
        adds = rel > 0.10
        shadow_adds_any |= adds
        h2_rows.append({"config": lbl, "gr_s_rac": gs, "gr_t_rac": gt,
                        "rel_diff": rel, "shadow_adds_value": bool(adds)})

    # ---- §7 multiplicity: BH-FDR, PBO, deflated statistic ----
    pvals = [per_config_pvals[l] for l in config_labels]
    bh = benjamini_hochberg(pvals, q=0.05)
    fdr_rows = [{"config": l, "worst_cell_pvalue": per_config_pvals[l],
                 "bh_reject_null": bool(rej)} for l, rej in zip(config_labels, bh)]
    pbo = probability_backtest_overfitting(
        grs_rac[head], n_splits=200, seed=seed + 11)
    best_lbl = max(config_labels, key=lambda l: float(np.median(grs_rac[head][l])))
    deflated = deflated_statistic(grs_rac[head][best_lbl], grs_rac[head], seed=seed + 13)

    # ---- Verdict classification (PROTOCOL §6) ----
    alive_configs = [r["config"] for r in gate_rows if r["alive_candidate"]]
    verdict, winning = _classify(
        gate_rows, ak_summ, grs_res, gr_t, all_cells, config_labels,
        gauge_pass=gauge_pass, replay=replay, shadow_adds_any=shadow_adds_any,
    )

    out = {
        "meta": {
            "id": "E019",
            "status": "completed",
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "phase": 2,
            "n_paths": n_paths,
            "horizon_days": params.horizon_days,
            "seed": args.seed,
            "beta": params.beta,
            "primary_metric": "RaC_beta = AnnRet / CDaR_beta (beta=0.95)",
            "baseline": "AK (auto-clearing daily-DD kill, shipped 2026-07-14)",
            "dgp_cells": [_cell_key(d, pw, rho) for (d, pw) in dgp_cells for rho in rhos],
            "n_configs": len(grid),
            "n_arm_configs_vs_ak": 2 * len(grid),
            "quick": bool(args.quick),
            "verdict": verdict,
            "winning_config": winning if verdict == "alive" else None,
            "verdict_diagnostic": winning,
            "runtime_seconds": round(time.time() - t0, 1),
        },
        "monte_carlo": {
            "AK": ak_summ,
            "GR-S": gr_s,
            "GR-T": gr_t,
        },
        "primary_gate": gate_rows,
        "alive_candidates": alive_configs,
        "h2_shadow_vs_timedecay": {
            "headline_cell": head,
            "rows": h2_rows,
            "shadow_adds_value_any": bool(shadow_adds_any),
        },
        "multiplicity": {
            "family_size": len(config_labels),
            "bh_fdr": fdr_rows,
            "pbo": pbo,
            "deflated_statistic": deflated,
        },
        "gauge_convergence_check": gauge_checks,
        "gauge_convergence_passed": gauge_pass,
        "incident_replay_2026_07_08": replay,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nVerdict: {verdict}")
    print(f"Alive candidates: {alive_configs or 'none'}")
    print(f"Wrote {out_path} ({time.time()-t0:.0f}s total)")
    return 0 if verdict == "alive" else 1


def _classify(gate_rows, ak_summ, grs_res, gr_t, all_cells, config_labels,
              *, gauge_pass, replay, shadow_adds_any) -> tuple[str, dict | None]:
    """Map results to the PROTOCOL §6 four-tier registry."""
    if not gauge_pass or not replay["protective_close_preserved"]:
        return "dead", None

    alive = [r for r in gate_rows if r["alive_candidate"]]
    if alive:
        winner = alive[0]
        # H2 parsimony check on the winning config (headline cell)
        head = all_cells[0]
        lbl = winner["config"]
        gs = grs_res[head][lbl]["median_rac_beta"]
        gt = next(r for r in gr_t if r["cell"] == head and r["config"] == lbl)["median_rac_beta"]
        rel = abs(gs - gt) / max(abs(gs), abs(gt), 1e-9)
        if rel <= 0.10:
            return "parked_shadow_adds_nothing", {"config": lbl,
                                                  "gr_s_rac": gs, "gr_t_rac": gt}
        return "alive", {"config": lbl, "cells": winner["cells"]}

    # No alive config. Distinguish the parked_* / dead reasons.
    # Did any config win the PRIMARY in all cells but breach a guardrail?
    primary_only = [r for r in gate_rows if r["primary_win_all_cells"]]
    if primary_only:
        return "parked_capital_cost", {"config": primary_only[0]["config"]}

    # Headline (production-matching bootstrap) cell for the AK vs GR-S contrast.
    head = all_cells[0]
    ak_point = ak_summ[head]["median_rac_beta"]
    best_gr = max(grs_res[head].values(), key=lambda s: s["median_rac_beta"])
    best_gr_rac = best_gr["median_rac_beta"]
    rel = (best_gr_rac - ak_point) / max(abs(ak_point), 1e-9)

    # H3 (parked_baseline_sufficient): AK ~ GR-S, i.e. the graduated overlay
    # neither materially beats nor is materially beaten by the cheap fix
    # (|rel| <= 10%). A genuine statistical tie -> the shipped AK is enough.
    if abs(rel) <= 0.10:
        return "parked_baseline_sufficient", {
            "ak_median_rac": ak_point, "best_gr_s_median_rac": best_gr_rac,
            "rel_diff": rel}

    # Otherwise GR-S materially FAILS to beat AK on the primary -> dead/STOP
    # (PROTOCOL §6 last bullet: "GR-S does not beat AK on RaC_beta").
    return "dead", {
        "ak_median_rac": ak_point, "best_gr_s_median_rac": best_gr_rac,
        "rel_diff": rel}


if __name__ == "__main__":
    raise SystemExit(main())
