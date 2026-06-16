"""Test B Stage 1 — screen on EURUSD H4 + H1, 2015-01-01 → 2021-12-31.

Per protocols/TEST_B_PROTOCOL.md §3.5 / §3.6. Runs the 12-cell family:
TF ∈ {H4, H1} × direction ∈ {+1, −1} × M_atr ∈ {1.0, 1.5, 2.0}. Per-cell
permutation p (5000 shuffles, hour-matched random-level controls), BH-FDR
α=0.05 across the 12, four-tier verdicts.

After cells are scored, pools the unique events across the 12 cells
(deduplicated by (tf, direction, impulse_end_idx, touch_bar_idx)), fits
the FROZEN friction reference distribution and quartile cutoffs, and
writes them next to the registry.

Usage (PYTHONPATH=eurusd-ai-agent so `conflab.data.load_frames` can reach
the parquet cache; the venv is the parent's):

    PYTHONPATH=/path/to/eurusd-ai-agent:. \
        python scripts/test_b/run_stage1.py
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
from conflab.friction import (
    FrictionComponents,
    aggregate as friction_aggregate,
    fit_reference,
    quartile_cutoffs,
)
from scripts.test_b._lib import (
    DIRECTIONS,
    M_ATR_GRID,
    TIMEFRAMES,
    apply_fdr_and_verdicts,
    evaluate_cell,
    format_registry_table,
    write_events_jsonl,
    write_registry_jsonl,
)

SCREEN_START = "2015-01-01"
SCREEN_END = "2021-12-31"
SEED = 42

log = logging.getLogger("test_b.stage1")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="EURUSD")
    p.add_argument("--start", default=SCREEN_START)
    p.add_argument("--end", default=SCREEN_END)
    p.add_argument("--out", default="output/test_b")
    p.add_argument("--tag", default="screen")
    return p.parse_args()


def dedupe_events(events: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for e in events:
        key = (e["tf"], int(e["direction"]),
               int(e["impulse_end_idx"]), int(e["touch_bar_idx"]))
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    out_dir = Path(args.out)
    stamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_%H%M")

    print(f"[Test B Stage 1] {args.symbol}, {args.start}..{args.end}")
    frames = load_frames(args.symbol, list(TIMEFRAMES),
                         start=args.start, end=args.end)
    if not frames:
        sys.exit("No data loaded — check parquet cache + PYTHONPATH.")
    for tf in TIMEFRAMES:
        if tf in frames:
            print(f"  {tf}: {len(frames[tf])} bars")

    rng = np.random.default_rng(SEED)
    cell_outcomes = []
    all_events: list[dict] = []
    for tf in TIMEFRAMES:
        if tf not in frames:
            continue
        for direction in DIRECTIONS:
            for M_atr in M_ATR_GRID:
                outcome = evaluate_cell(
                    frames[tf], tf=tf, direction=direction, M_atr=M_atr,
                    rng=rng)
                cell_outcomes.append(outcome)
                all_events.extend(outcome.events)
                print(
                    f"  cell {outcome.cell_id}: n={outcome.n_events} "
                    f"evMFE={outcome.mean_mfe_pips_event:.2f}p "
                    f"ctMFE={outcome.mean_mfe_pips_control:.2f}p "
                    f"effect={outcome.effect_pips:+.2f}p "
                    f"reach0.5R={outcome.headline_reach_event*100:.1f}% "
                    f"(ctrl {outcome.headline_reach_control*100:.1f}%) "
                    f"d={outcome.cohens_d:+.3f} p={outcome.p_value:.4f}")

    rows = [o.to_registry_row() for o in cell_outcomes]
    rows = apply_fdr_and_verdicts(rows, use_fdr=True)
    print()
    print(format_registry_table(rows))

    registry_path = out_dir / f"stage1_{args.symbol}_{args.tag}_{stamp}.jsonl"
    write_registry_jsonl(rows, registry_path)
    print(f"\nregistry: {registry_path}")

    events_path = out_dir / f"stage1_{args.symbol}_{args.tag}_{stamp}_events.jsonl"
    write_events_jsonl(all_events, events_path)
    print(f"events:   {events_path}")

    deduped = dedupe_events(all_events)
    print(f"\nfriction reference: pooling {len(deduped)} unique screen-split events")
    if deduped:
        records = [e["friction_components"] for e in deduped]
        ref = fit_reference(records)
        scores = [
            friction_aggregate(FrictionComponents(**r), ref)
            for r in records
        ]
        cutoffs = quartile_cutoffs(scores)
        ref_path = out_dir / f"stage1_friction_reference_{stamp}.json"
        ref_payload = {
            "fit_at": stamp,
            "symbol": args.symbol,
            "split_start": args.start,
            "split_end": args.end,
            "n_unique_events": len(deduped),
            "reference_mean_std": {
                k: {"mean": float(mu), "std": float(sd)}
                for k, (mu, sd) in ref.items()
            },
            "quartile_cutoffs": {
                "Q1_Q2": float(cutoffs[0]),
                "Q2_Q3": float(cutoffs[1]),
                "Q3_Q4": float(cutoffs[2]),
            },
        }
        ref_path.write_text(json.dumps(ref_payload, indent=2))
        print(f"reference: {ref_path}")
        print(f"  cutoffs: Q1|Q2={cutoffs[0]:+.4f}, "
              f"Q2|Q3={cutoffs[1]:+.4f}, Q3|Q4={cutoffs[2]:+.4f}")


if __name__ == "__main__":
    main()
