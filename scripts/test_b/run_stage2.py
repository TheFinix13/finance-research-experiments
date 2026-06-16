"""Test B Stage 2 — Confirm survivors on EURUSD 2022-01-01 → 2024-12-31.

Per protocols/TEST_B_PROTOCOL.md §3.6: only cells with verdict `alive`
in the Stage-1 registry advance. Same hour-matched displacement null,
per-cell α=0.05 (small family, no BH-FDR), seed = 142.

If the Stage-1 registry contains zero `alive` cells, the §3.7 stop rule
fires: this script writes a stop-rule record and exits cleanly. That is
the case for the canonical 2026-06-16 run.

Usage:
    PYTHONPATH=/path/to/multi-pair-trading-agent:. \
        python scripts/test_b/run_stage2.py \
        --stage1-registry output/test_b/stage1_EURUSD_screen_<stamp>.jsonl
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

from conflab.data import load_frames
from scripts.test_b._lib import (
    apply_fdr_and_verdicts,
    evaluate_cell,
    format_registry_table,
    read_jsonl,
    write_events_jsonl,
    write_registry_jsonl,
)

CONFIRM_START = "2022-01-01"
CONFIRM_END = "2024-12-31"
SEED = 142

log = logging.getLogger("test_b.stage2")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--stage1-registry", required=True,
                   help="Path to the Stage-1 canonical registry JSONL.")
    p.add_argument("--symbol", default="EURUSD")
    p.add_argument("--start", default=CONFIRM_START)
    p.add_argument("--end", default=CONFIRM_END)
    p.add_argument("--out", default="output/test_b")
    p.add_argument("--tag", default="confirm")
    return p.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    out_dir = Path(args.out)
    stamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_%H%M")

    rows = read_jsonl(Path(args.stage1_registry))
    survivors = [r for r in rows if r.get("verdict") == "alive"]

    if not survivors:
        record = {
            "stage": 2,
            "timestamp": stamp,
            "stage1_registry": str(args.stage1_registry),
            "n_alive_in_stage1": 0,
            "stop_rule_fired": "TEST_B_PROTOCOL §3.7 — H1 (main) dies at "
                               "Stage 1; H2 and H3 do not run.",
            "verdict": "stopped_no_survivors",
        }
        path = out_dir / f"stage2_{args.symbol}_{args.tag}_{stamp}.stop.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2))
        print("[Test B Stage 2] STOP — no Stage-1 survivors. "
              f"Record written to {path}")
        return

    print(f"[Test B Stage 2] {args.symbol}, {args.start}..{args.end}")
    print(f"  survivors from Stage 1: {len(survivors)}")
    tfs_needed = sorted({r["tf"] for r in survivors})
    frames = load_frames(args.symbol, tfs_needed,
                         start=args.start, end=args.end)
    if not frames:
        sys.exit("No data loaded — check parquet cache + PYTHONPATH.")
    rng = np.random.default_rng(SEED)

    confirm_rows: list[dict] = []
    all_events: list[dict] = []
    for s in survivors:
        if s["tf"] not in frames:
            log.warning("survivor %s skipped: no %s data in confirm window",
                        s["cell_id"], s["tf"])
            continue
        outcome = evaluate_cell(
            frames[s["tf"]], tf=s["tf"], direction=s["direction"],
            M_atr=s["M_atr"], rng=rng)
        confirm_rows.append(outcome.to_registry_row())
        all_events.extend(outcome.events)
        print(f"  {outcome.cell_id}: n={outcome.n_events} "
              f"effect={outcome.effect_pips:+.2f}p p={outcome.p_value:.4f}")

    confirm_rows = apply_fdr_and_verdicts(confirm_rows, use_fdr=False)
    print()
    print(format_registry_table(confirm_rows))

    registry_path = out_dir / f"stage2_{args.symbol}_{args.tag}_{stamp}.jsonl"
    write_registry_jsonl(confirm_rows, registry_path)
    write_events_jsonl(
        all_events,
        out_dir / f"stage2_{args.symbol}_{args.tag}_{stamp}_events.jsonl")
    print(f"\nregistry: {registry_path}")


if __name__ == "__main__":
    main()
