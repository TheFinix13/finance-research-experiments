"""Phase AE — one-shot AE1-AE4 evaluator (PROTOCOL §4, locked).

Reads the two arm result JSONs produced by
``sim/scoring/run_phase_ae_compute.py`` and scores:

- AE1: Sae >= 30 OOS trades on the panel.
- AE2: Sae OOS mean TQS >= 0.30 AND bootstrap 95% CI lower bound
  > 0.20 (n=10000, seed=42, percentile — same spec as g7retry2).
- AE3: fade/ride mechanic split; a mechanic contributing < 20% of
  Sae's OOS trades is PARKED (does not fail the phase).
- AE4: no incumbent agent's union-OOS mean TQS regresses by more
  than 0.02 in the treatment arm vs baseline.

Phase verdict: PASS iff AE1 AND AE2 AND AE4. Evaluated ONCE —
committed BEFORE the arms ran (statistical-honesty requirement).

Usage::

    python evaluate_phase_ae.py \\
        --baseline results/results_ae-baseline.json \\
        --treatment results/results_ae-treatment.json \\
        --out-json results/phase_ae_evaluation.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import numpy as np

AE1_MIN_OOS_TRADES = 30
AE2_MEAN_TQS_FLOOR = 0.30
AE2_CI_LOWER_FLOOR = 0.20
AE3_PARK_FRACTION = 0.20
AE4_MAX_REGRESSION = 0.02
BOOTSTRAP_N = 10_000
BOOTSTRAP_SEED = 42
SAE_ID = "sae_itoshi"


def bootstrap_ci(values: list[float], n: int = BOOTSTRAP_N,
                 seed: int = BOOTSTRAP_SEED,
                 alpha: float = 0.05) -> tuple[float, float]:
    """Percentile bootstrap CI of the mean (g7retry2 spec)."""
    rng = np.random.default_rng(seed)
    arr = np.asarray(values, dtype=float)
    idx = rng.integers(0, len(arr), size=(n, len(arr)))
    means = arr[idx].mean(axis=1)
    lo, hi = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def evaluate(baseline: dict, treatment: dict) -> dict:
    sae_stats = treatment["union_oos"].get(SAE_ID, {})
    n_sae = int(sae_stats.get("n_trades") or 0)
    tqs_values = list(sae_stats.get("tqs_values") or [])

    # --- AE1 ---------------------------------------------------------
    ae1_pass = n_sae >= AE1_MIN_OOS_TRADES
    ae1 = {"pass": ae1_pass, "n_oos_trades": n_sae,
           "threshold": AE1_MIN_OOS_TRADES}

    # --- AE2 ---------------------------------------------------------
    if tqs_values:
        mean_tqs = statistics.mean(tqs_values)
        ci_lo, ci_hi = bootstrap_ci(tqs_values)
        ae2_pass = (mean_tqs >= AE2_MEAN_TQS_FLOOR
                    and ci_lo > AE2_CI_LOWER_FLOOR)
    else:
        mean_tqs, ci_lo, ci_hi, ae2_pass = None, None, None, False
    ae2 = {
        "pass": bool(ae2_pass),
        "mean_tqs": mean_tqs,
        "bootstrap_ci95": [ci_lo, ci_hi],
        "mean_floor": AE2_MEAN_TQS_FLOOR,
        "ci_lower_floor": AE2_CI_LOWER_FLOOR,
        "bootstrap": {"n": BOOTSTRAP_N, "seed": BOOTSTRAP_SEED,
                      "method": "percentile"},
    }

    # --- AE3 (mechanic split; OOS trades only) -------------------------
    # sae_trade_meta rows are matched to OOS membership through the
    # union_oos count: the arm runner counts OOS trades by entry_time,
    # and every meta row carries entry_time. Recompute OOS membership
    # from the per_window bounds for exactness.
    oos_bounds = [
        (row["oos_start"], row["oos_end"]) for row in treatment["per_window"]
    ]

    def _in_oos(entry_iso: str) -> bool:
        return any(lo <= entry_iso < hi for lo, hi in oos_bounds)

    meta_oos = [
        m for m in treatment.get("sae_trade_meta", [])
        if _in_oos(m["entry_time"])
    ]
    split: dict[str, dict] = {}
    for mech in ("sae_fade", "sae_ride"):
        rows = [m for m in meta_oos if m.get("mechanic") == mech]
        split[mech] = {
            "n_trades": len(rows),
            "fraction": (len(rows) / len(meta_oos)) if meta_oos else 0.0,
            "mean_tqs": (
                statistics.mean(float(m["tqs"]) for m in rows)
                if rows else None
            ),
            "mean_pnl_pips": (
                statistics.mean(float(m["pnl_pips"]) for m in rows)
                if rows else None
            ),
        }
    parked = [
        mech for mech, s in split.items()
        if s["fraction"] < AE3_PARK_FRACTION
    ]
    ae3 = {
        "split": split,
        "n_oos_meta": len(meta_oos),
        "park_threshold_fraction": AE3_PARK_FRACTION,
        "parked_mechanics": parked,
    }

    # --- AE4 ---------------------------------------------------------
    deltas: dict[str, dict] = {}
    regressions: list[str] = []
    for aid, base_row in baseline["union_oos"].items():
        if aid == SAE_ID:
            continue
        treat_row = treatment["union_oos"].get(aid, {})
        b_mean = base_row.get("mean_tqs")
        t_mean = treat_row.get("mean_tqs")
        if b_mean is None or t_mean is None:
            delta = None
        else:
            delta = float(t_mean) - float(b_mean)
            if delta < -AE4_MAX_REGRESSION:
                regressions.append(aid)
        deltas[aid] = {
            "baseline_mean_tqs": b_mean,
            "treatment_mean_tqs": t_mean,
            "delta": delta,
            "baseline_n": base_row.get("n_trades"),
            "treatment_n": treat_row.get("n_trades"),
        }
    ae4_pass = not regressions
    ae4 = {
        "pass": ae4_pass,
        "max_regression_allowed": AE4_MAX_REGRESSION,
        "regressed_agents": regressions,
        "per_agent": deltas,
    }

    verdict = "PASS" if (ae1_pass and ae2_pass and ae4_pass) else "FAIL"
    return {
        "verdict": verdict,
        "verdict_rule": "PASS iff AE1 AND AE2 AND AE4 (AE3 parks only)",
        "ae1": ae1,
        "ae2": ae2,
        "ae3": ae3,
        "ae4": ae4,
        "arms": {
            "baseline_tag": baseline["tag"],
            "treatment_tag": treatment["tag"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--treatment", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    args = parser.parse_args(argv)
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    treatment = json.loads(args.treatment.read_text(encoding="utf-8"))
    result = evaluate(baseline, treatment)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(result, indent=2), encoding="utf-8",
    )
    print(json.dumps({
        "verdict": result["verdict"],
        "ae1": result["ae1"]["pass"],
        "ae2": result["ae2"]["pass"],
        "ae3_parked": result["ae3"]["parked_mechanics"],
        "ae4": result["ae4"]["pass"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
