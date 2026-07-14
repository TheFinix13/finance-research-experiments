"""Supervisor script that launches all 14 LOO replays with proper
staggering to avoid parquet-cache write races.

Strategy: launch phi41 batch and arm4 batch, but stagger each individual
subprocess by ~4 seconds so the loader.get() cache-load / upsert path
never has two processes writing at the same instant.
Then wait for all subprocesses to complete.

Runs in the foreground of a persistent Cursor `Shell` background job,
so the parent shell is the Cursor terminal file (won't die on session
disconnect).
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO = Path("/Users/the1finix/Documents/GitHub/finance-research-experiments")
PY = "/Users/the1finix/Documents/GitHub/multi-pair-trading-agent/.venv/bin/python"
LOGDIR = REPO / "programs/M001_multi_agent_ensemble/reviews/loo_logs"
LOGDIR.mkdir(exist_ok=True)

AGENTS = [
    "isagi_yoichi", "bachira_meguru", "itoshi_rin", "chigiri_hyoma",
    "reo_mikage", "nagi_seishiro", "barou_shoei",
]

ENV = {**os.environ, "PYTHONPATH": str(REPO)}


def launch(tag: str, agent: str, aggregator: str) -> subprocess.Popen:
    logf = LOGDIR / f"{aggregator}_{agent}.log"
    baseline = REPO / f"programs/M001_multi_agent_ensemble/reviews/g7_replay_cache_g7retry1-{aggregator}"
    args = [
        PY, "-m",
        "programs.M001_multi_agent_ensemble.sim.scoring.run_g7_leave_one_out",
        "--tag", tag,
        "--baseline-cache-dir", str(baseline),
        "--exclude", agent,
        "--no-aggregate",
        "--aggregator-arm", aggregator,
        "--retire-kunigami",
        "-v",
    ]
    log = logf.open("w")
    p = subprocess.Popen(
        args, cwd=str(REPO), env=ENV,
        stdout=log, stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        preexec_fn=os.setsid,  # own process group; immune to caller SIGHUP
    )
    print(f"launch {aggregator} lo1={agent}  pid={p.pid}  -> {logf}", flush=True)
    return p


def main() -> int:
    procs: list[subprocess.Popen] = []
    for i, a in enumerate(AGENTS):
        procs.append(launch(f"g7retry1-phi41", a, "phi41"))
        time.sleep(4)
        procs.append(launch(f"g7retry1-arm4", a, "arm4"))
        time.sleep(4)

    (LOGDIR / "all.pids").write_text(
        "\n".join(str(p.pid) for p in procs) + "\n"
    )
    print(f"all pids: {[p.pid for p in procs]}", flush=True)

    exit_codes: dict[int, int] = {}
    while any(p.poll() is None for p in procs):
        time.sleep(30)
        alive = sum(1 for p in procs if p.poll() is None)
        done = sum(1 for p in procs if p.poll() is not None)
        print(f"[supervisor] alive={alive}  done={done}", flush=True)

    for p in procs:
        exit_codes[p.pid] = p.returncode
    print("[supervisor] all done", flush=True)
    for pid, rc in exit_codes.items():
        print(f"  pid={pid}  rc={rc}", flush=True)
    return 0 if all(rc == 0 for rc in exit_codes.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
