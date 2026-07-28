"""E010 Stage-0 count-only diagnostic (PROTOCOL §7).

Verifies every §2 cell crosses n_joint >= 100 on the EURUSD 2015-2021
screen window WITHOUT invoking the MFE outcome path. Emits
output/E010_equal_highs_pool_stage2b/stage0_counts_<stamp>.json.

    PYTHONPATH=../multi-pair-trading-agent:. \
        ../multi-pair-trading-agent/.venv/bin/python \
        scripts/E010/diagnose_counts.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from scripts.E010.run_e010 import (
    CELLS, CONTEXT_TYPE, N_GATE, OUT, collect_setup_events,
    context_events, joint_events, load_window,
)


def main() -> None:
    h1 = load_window("EURUSD", "H1", "2015-01-01", "2021-12-31")
    m15 = load_window("EURUSD", "M15", "2015-01-01", "2021-12-31")
    ctx = context_events(h1)
    setups = collect_setup_events(m15)
    counts = {}
    for cell in CELLS:
        joint = joint_events(ctx, h1, setups.get(cell, []), m15)
        counts[cell] = {"n_joint_pre_mfe": len(joint),
                        "n_marginal": len(setups.get(cell, [])),
                        "crosses_gate": len(joint) >= N_GATE}
    result = {"experiment": "E010", "stage": 0,
              "context": f"H1:{CONTEXT_TYPE}", "n_context_events": len(ctx),
              "note": "count-only; MFE outcome path not invoked",
              "cells": counts}
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    path = OUT / f"stage0_counts_{stamp}.json"
    with open(path, "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))
    print(f"-> {path}")


if __name__ == "__main__":
    main()
