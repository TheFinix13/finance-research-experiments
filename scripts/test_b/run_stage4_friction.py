"""Test B Stage 4 — Friction conditioning on Stage-3 survivors.

Per protocols/TEST_B_PROTOCOL.md §3.6 + §4: split Stage-3 survivor
events by friction quartile (cutoffs frozen from the EURUSD screen
split, never relearned per pair/stage), report per-quartile reach-curve
probabilities with bootstrap CIs (10000 resamples, seed = 342).

If Stage 3 produced a stop record (or no survivors), this script writes
its own stop record and exits cleanly.

Usage:
    PYTHONPATH=/path/to/eurusd-ai-agent:. \
        python scripts/test_b/run_stage4_friction.py \
        --stage3-registry output/test_b/stage3_cross_pair_<stamp>.jsonl \
        --friction-reference output/test_b/stage1_friction_reference_<stamp>.json \
        --stage3-events output/test_b/stage3_cross_pair_<stamp>_events.jsonl
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from conflab.friction import (
    FrictionComponents,
    aggregate as friction_aggregate,
    assign_quartile,
)
from scripts.test_b._lib import REACH_THRESHOLDS, read_jsonl

SEED = 342
N_BOOT = 10000

log = logging.getLogger("test_b.stage4")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--stage3-registry", required=True)
    p.add_argument("--stage3-events", required=False, default=None)
    p.add_argument("--friction-reference", required=True)
    p.add_argument("--out", default="output/test_b")
    p.add_argument("--tag", default="friction")
    return p.parse_args()


def reach_share(reaches: np.ndarray) -> float:
    return float(reaches.mean()) if reaches.size else 0.0


def bootstrap_ci(reaches: np.ndarray, n_boot: int,
                 rng: np.random.Generator,
                 alpha: float = 0.05) -> tuple[float, float]:
    if reaches.size == 0:
        return (0.0, 0.0)
    means = []
    n = len(reaches)
    for _ in range(n_boot):
        sample = reaches[rng.integers(0, n, size=n)]
        means.append(sample.mean())
    arr = np.asarray(means)
    return float(np.quantile(arr, alpha / 2)), float(np.quantile(arr, 1 - alpha / 2))


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    out_dir = Path(args.out)
    stamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_%H%M")

    s3_path = Path(args.stage3_registry)
    if s3_path.suffix == ".json" and ".stop." in s3_path.name:
        upstream_stop = json.loads(s3_path.read_text())
    else:
        upstream_stop = None
    survivors = []
    if upstream_stop is None:
        s3_rows = read_jsonl(s3_path)
        survivors = [r for r in s3_rows if r.get("verdict") == "alive"]

    if upstream_stop or not survivors:
        record = {
            "stage": 4,
            "timestamp": stamp,
            "stage3_path": str(args.stage3_registry),
            "upstream_stop": upstream_stop,
            "n_alive_in_stage3": len(survivors),
            "stop_rule_fired": "TEST_B_PROTOCOL §3.7 — H3 dies upstream;"
                               " Stage 4 friction conditioning does not run.",
            "verdict": "stopped_no_survivors",
        }
        path = out_dir / f"stage4_{args.tag}_{stamp}.stop.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2))
        print("[Test B Stage 4] STOP — no Stage-3 survivors. "
              f"Record written to {path}")
        return

    if args.stage3_events is None:
        sys.exit("Stage 3 had survivors but --stage3-events was not provided.")

    ref_payload = json.loads(Path(args.friction_reference).read_text())
    ref = {k: (v["mean"], v["std"])
           for k, v in ref_payload["reference_mean_std"].items()}
    cutoffs = (ref_payload["quartile_cutoffs"]["Q1_Q2"],
               ref_payload["quartile_cutoffs"]["Q2_Q3"],
               ref_payload["quartile_cutoffs"]["Q3_Q4"])

    events = read_jsonl(Path(args.stage3_events))
    rng = np.random.default_rng(SEED)
    rows = []
    for q in (1, 2, 3, 4):
        per_q = []
        for e in events:
            score = friction_aggregate(
                FrictionComponents(**e["friction_components"]), ref)
            if assign_quartile(score, cutoffs) == q:
                per_q.append(e)
        if not per_q:
            continue
        for k_threshold in REACH_THRESHOLDS:
            reaches = np.asarray(
                [bool(e.get("reach_event", {}).get(f"{k_threshold}R", False))
                 for e in per_q], dtype=float)
            mean = reach_share(reaches)
            lo, hi = bootstrap_ci(reaches, N_BOOT, rng)
            rows.append({
                "quartile": q,
                "n": len(per_q),
                "threshold_R": k_threshold,
                "reach_prob": round(mean, 4),
                "boot_ci_lo": round(lo, 4),
                "boot_ci_hi": round(hi, 4),
            })

    out_path = out_dir / f"stage4_{args.tag}_{stamp}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"\nfriction quartile reach curves: {out_path}")


if __name__ == "__main__":
    main()
