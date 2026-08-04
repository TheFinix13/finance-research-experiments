"""Phase AF in-sample sweep dispatcher: remaining 7 cells, sequential.

Each cell runs in its own subprocess (config/param patches must not
leak). Baseline (30, 0.0) was executed and timed separately.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = "/Users/the1finix/Documents/GitHub/multi-pair-trading-agent/.venv/bin/python"
CELLS = [
    (20, 0.0), (40, 0.0), (50, 0.0),
    (20, 0.5), (30, 0.5), (40, 0.5), (50, 0.5),
]

def main() -> None:
    for impulse, rr in CELLS:
        label = f"is_cell_{impulse}_{rr}"
        kpi = HERE / "results" / f"{label}.json"
        if kpi.exists():
            print(f"[skip] {label} already done", flush=True)
            continue
        t0 = time.time()
        print(f"[run ] {label}", flush=True)
        rc = subprocess.run([
            PY, str(HERE / "replay_cell.py"),
            "--impulse", str(impulse), "--rr-delta", str(rr),
            "--start", "2019-01-01", "--end", "2023-12-31",
            "--label", label,
            "--out-dir", str(HERE / "results" / "raw" / label),
            "--kpi-out", str(kpi),
        ]).returncode
        dt = time.time() - t0
        print(f"[done] {label} rc={rc} {dt:.0f}s", flush=True)
        if rc != 0:
            print("[ABORT] cell failed -- stopping per protocol", flush=True)
            sys.exit(1)
    print("[sweep complete]", flush=True)

if __name__ == "__main__":
    main()
