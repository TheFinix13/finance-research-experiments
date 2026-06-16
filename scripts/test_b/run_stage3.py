"""Test B Stage 3 — Cross-pair sealed look on GBPUSD + USDCAD H4.

Per protocols/TEST_B_PROTOCOL.md §3.6 + §3.8: H4 ONLY (USDCAD has no H1
parquet; GBPUSD H1 only goes to 2021), 2015-01-01 → 2024-12-31, run
ONCE on Stage-2 confirmed survivors. Per-cell α=0.05, seed = 242.

If the Stage-2 registry contains zero `alive` cells (or the file is the
stop-rule record), the protocol stops. This script writes a stop-rule
record and exits cleanly.

Usage:
    PYTHONPATH=/path/to/multi-pair-trading-agent:. \
        python scripts/test_b/run_stage3.py \
        --stage2-registry output/test_b/stage2_EURUSD_confirm_<stamp>.jsonl
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

CROSS_START = "2015-01-01"
CROSS_END = "2024-12-31"
SEED = 242
PAIRS = ("GBPUSD", "USDCAD")
H4_ONLY = ("H4",)

log = logging.getLogger("test_b.stage3")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--stage2-registry", required=True)
    p.add_argument("--out", default="output/test_b")
    p.add_argument("--tag", default="cross_pair")
    return p.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    out_dir = Path(args.out)
    stamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_%H%M")

    s2_path = Path(args.stage2_registry)
    if s2_path.suffix == ".json" and ".stop." in s2_path.name:
        upstream_stop = json.loads(s2_path.read_text())
    else:
        upstream_stop = None
    survivors = []
    if upstream_stop is None:
        rows = read_jsonl(s2_path)
        survivors = [r for r in rows
                     if r.get("verdict") == "alive" and r.get("tf") == "H4"]

    if upstream_stop or not survivors:
        record = {
            "stage": 3,
            "timestamp": stamp,
            "stage2_path": str(args.stage2_registry),
            "upstream_stop": upstream_stop,
            "n_h4_alive_in_stage2": len(survivors),
            "stop_rule_fired": "TEST_B_PROTOCOL §3.7 — H1 dies upstream;"
                               " Stage 3 cross-pair does not run.",
            "verdict": "stopped_no_survivors",
        }
        path = out_dir / f"stage3_{args.tag}_{stamp}.stop.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2))
        print("[Test B Stage 3] STOP — no H4 Stage-2 survivors. "
              f"Record written to {path}")
        return

    print(f"[Test B Stage 3] cross-pair {','.join(PAIRS)} H4 "
          f"{CROSS_START}..{CROSS_END}")
    rng = np.random.default_rng(SEED)
    cross_rows: list[dict] = []
    all_events: list[dict] = []
    for symbol in PAIRS:
        frames = load_frames(symbol, list(H4_ONLY),
                             start=CROSS_START, end=CROSS_END)
        if not frames:
            log.warning("no data for %s — skipping", symbol)
            continue
        for s in survivors:
            tf = s["tf"]
            if tf not in frames:
                continue
            outcome = evaluate_cell(
                frames[tf], tf=tf, direction=s["direction"],
                M_atr=s["M_atr"], rng=rng)
            row = outcome.to_registry_row()
            row["symbol"] = symbol
            cross_rows.append(row)
            all_events.extend(
                {**e, "symbol": symbol} for e in outcome.events)
            print(f"  [{symbol}] {outcome.cell_id}: n={outcome.n_events} "
                  f"effect={outcome.effect_pips:+.2f}p p={outcome.p_value:.4f}")

    cross_rows = apply_fdr_and_verdicts(cross_rows, use_fdr=False)
    print()
    print(format_registry_table(cross_rows))
    registry_path = out_dir / f"stage3_{args.tag}_{stamp}.jsonl"
    write_registry_jsonl(cross_rows, registry_path)
    write_events_jsonl(
        all_events, out_dir / f"stage3_{args.tag}_{stamp}_events.jsonl")
    print(f"\nregistry: {registry_path}")


if __name__ == "__main__":
    main()
