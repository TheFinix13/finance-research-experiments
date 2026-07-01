"""Compute-job heartbeat monitor -- keeps tabs on long-running experiments.

Purpose
-------

Multi-hour experiments (G7 walk-forward, Phi4.1 physical rerun, etc.)
can go silent for 30-60 min mid-run because their per-bar replay loop
doesn't emit stdout. Distinguishing "silently progressing" from
"actually frozen" requires sampling process state (CPU, RSS, elapsed
time, output-file mtime) from outside the process. This script does
exactly that -- it samples a set of PIDs every N seconds and appends
one JSONL heartbeat per sample to ``reviews/compute_heartbeat.jsonl``,
plus a human-readable line to ``reviews/compute_heartbeat.log``.

Also flags anomalies:

- CPU% below the healthy floor for K consecutive samples -> ``STALLED``.
- RSS drop > 20% between samples -> ``MEMORY_DROP`` (usually the
  process just released a big allocation, so INFO level only).
- No mtime change on the expected output artefact for M samples ->
  ``NO_OUTPUT_PROGRESS``.

Usage
-----

    ../multi-pair-trading-agent/.venv/bin/python \
        scripts/monitor_compute_jobs.py \
        --pid 73654:g7_walk_forward \
        --pid 68336:phi41_physical_rerun \
        --interval 30 --cpu-floor 20 --stall-samples 4

Add ``--output-artefact PID:path`` to also monitor an output file's
mtime for that process. Runs until every tracked PID is gone.

Design notes
------------

- Zero external dependencies (stdlib only). Uses ``ps`` under the hood.
- Safe to run alongside the target processes -- it makes no
  modifications to disk beyond appending to the heartbeat files.
- The script is intentionally minimal: 200-ish LoC, no fancy
  Rich/curses UI. If the user wants a live TUI, run
  ``tail -f reviews/compute_heartbeat.log`` in a separate terminal.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


HEARTBEAT_JSONL = "programs/M001_multi_agent_ensemble/reviews/compute_heartbeat.jsonl"
HEARTBEAT_LOG = "programs/M001_multi_agent_ensemble/reviews/compute_heartbeat.log"


@dataclass
class TrackedJob:
    pid: int
    label: str
    output_artefact: Optional[Path] = None
    cpu_history: list[float] = field(default_factory=list)
    rss_history: list[int] = field(default_factory=list)
    mtime_history: list[float] = field(default_factory=list)
    last_seen_alive: float = field(default_factory=time.time)
    started_at: Optional[str] = None
    exit_code: Optional[int] = None
    warnings: list[str] = field(default_factory=list)


def _ps_sample(pid: int) -> Optional[dict]:
    """One ps sample for ``pid``. Returns None if the process is gone."""
    try:
        out = subprocess.check_output(
            ["ps", "-p", str(pid), "-o", "pid=,pcpu=,rss=,etime=,command="],
            stderr=subprocess.DEVNULL, text=True,
        )
    except subprocess.CalledProcessError:
        return None
    line = out.strip()
    if not line:
        return None
    parts = line.split(maxsplit=4)
    if len(parts) < 5:
        return None
    return {
        "pid": int(parts[0]),
        "cpu_pct": float(parts[1]),
        "rss_kb": int(parts[2]),
        "etime": parts[3],
        "command_head": parts[4][:120],
    }


def _artefact_mtime(path: Optional[Path]) -> Optional[float]:
    """mtime of ``path`` in seconds, or None when it doesn't exist yet."""
    if path is None:
        return None
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return None


def _classify_health(
    job: TrackedJob, *, cpu_floor: float, stall_samples: int,
    no_output_samples: int,
) -> list[str]:
    """Return a list of health flags for the current sample."""
    flags: list[str] = []
    # CPU floor over last K samples.
    if len(job.cpu_history) >= stall_samples:
        recent = job.cpu_history[-stall_samples:]
        if all(c < cpu_floor for c in recent):
            flags.append(
                f"STALLED (cpu<{cpu_floor} for {stall_samples} samples)"
            )
    # RSS drop.
    if len(job.rss_history) >= 2:
        prev, curr = job.rss_history[-2], job.rss_history[-1]
        if prev > 0 and (prev - curr) / prev > 0.20:
            flags.append(
                f"MEMORY_DROP (rss {prev/1024:.0f}MB -> {curr/1024:.0f}MB)"
            )
    # No output progress.
    if (
        job.output_artefact is not None
        and len(job.mtime_history) >= no_output_samples
    ):
        recent_mtimes = job.mtime_history[-no_output_samples:]
        if all(m is None for m in recent_mtimes):
            flags.append("NO_OUTPUT_PROGRESS (artefact missing)")
        elif all(m == recent_mtimes[0] for m in recent_mtimes):
            flags.append(
                f"NO_OUTPUT_PROGRESS (mtime unchanged for "
                f"{no_output_samples} samples)"
            )
    return flags


def _emit_heartbeat(
    jsonl_path: Path,
    log_path: Path,
    sample_ts: str,
    job: TrackedJob,
    stats: Optional[dict],
    flags: list[str],
) -> None:
    """Append one JSONL + one human-readable log line for this sample."""
    payload = {
        "sample_ts": sample_ts,
        "label": job.label,
        "pid": job.pid,
        "alive": stats is not None,
        "flags": flags,
    }
    if stats is not None:
        payload.update({
            "cpu_pct": stats["cpu_pct"],
            "rss_mb": round(stats["rss_kb"] / 1024, 1),
            "etime": stats["etime"],
        })
    if job.output_artefact is not None:
        payload["output_artefact"] = str(job.output_artefact)
        m = _artefact_mtime(job.output_artefact)
        if m is not None:
            payload["artefact_mtime_iso"] = datetime.fromtimestamp(
                m, tz=timezone.utc,
            ).isoformat()
    if job.exit_code is not None:
        payload["exit_code"] = job.exit_code

    with open(jsonl_path, "a") as fh:
        fh.write(json.dumps(payload) + "\n")

    if stats is not None:
        line = (
            f"{sample_ts}  {job.label:<28} pid={job.pid:<6} "
            f"cpu={stats['cpu_pct']:>5.1f}%  "
            f"rss={payload.get('rss_mb', 0):>6.1f}MB  "
            f"etime={stats['etime']}"
        )
        if flags:
            line += "   [" + ", ".join(flags) + "]"
    else:
        line = (
            f"{sample_ts}  {job.label:<28} pid={job.pid:<6}  "
            f"EXITED (no ps entry)"
        )
    line += "\n"
    with open(log_path, "a") as fh:
        fh.write(line)


def _parse_pid_arg(raw: str) -> tuple[int, str]:
    if ":" in raw:
        pid_str, label = raw.split(":", 1)
        return int(pid_str), label
    return int(raw), f"pid_{raw}"


def _parse_artefact_arg(raw: str) -> tuple[int, Path]:
    pid_str, path = raw.split(":", 1)
    return int(pid_str), Path(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
    )
    parser.add_argument(
        "--pid", action="append", required=True,
        help="PID:label pair, repeatable (e.g. --pid 73654:g7_walk_forward)",
    )
    parser.add_argument(
        "--output-artefact", action="append", default=[],
        help="PID:PATH pair, repeatable. Track mtime of PATH for PID",
    )
    parser.add_argument("--interval", type=float, default=30.0,
                        help="Seconds between samples (default 30)")
    parser.add_argument("--cpu-floor", type=float, default=20.0,
                        help="CPU%% below this counts as stalled (default 20)")
    parser.add_argument("--stall-samples", type=int, default=4,
                        help="Consecutive stalled samples before flagging (default 4)")
    parser.add_argument("--no-output-samples", type=int, default=20,
                        help="Consecutive samples without output progress before flagging (default 20)")
    parser.add_argument("--jsonl", default=HEARTBEAT_JSONL)
    parser.add_argument("--log", default=HEARTBEAT_LOG)
    parser.add_argument("--max-samples", type=int, default=0,
                        help="Stop after N samples; 0 = run until all PIDs exit")
    args = parser.parse_args(argv)

    jsonl_path = Path(args.jsonl)
    log_path = Path(args.log)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    artefact_map: dict[int, Path] = {}
    for raw in args.output_artefact:
        pid, path = _parse_artefact_arg(raw)
        artefact_map[pid] = path

    jobs: dict[int, TrackedJob] = {}
    for raw in args.pid:
        pid, label = _parse_pid_arg(raw)
        jobs[pid] = TrackedJob(
            pid=pid, label=label,
            output_artefact=artefact_map.get(pid),
            started_at=datetime.now(tz=timezone.utc).isoformat(),
        )

    # Session header.
    header = (
        f"# monitor_compute_jobs.py started at "
        f"{datetime.now(tz=timezone.utc).isoformat()}\n"
        f"# tracking {len(jobs)} PIDs: "
        f"{', '.join(f'{j.pid}={j.label}' for j in jobs.values())}\n"
        f"# interval={args.interval}s  cpu_floor={args.cpu_floor}%  "
        f"stall_samples={args.stall_samples}\n"
    )
    with open(log_path, "a") as fh:
        fh.write(header)
    with open(jsonl_path, "a") as fh:
        fh.write(json.dumps({
            "event": "session_start",
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            "tracked": {j.pid: j.label for j in jobs.values()},
            "interval_s": args.interval,
        }) + "\n")

    sample_count = 0
    while True:
        sample_count += 1
        ts_iso = datetime.now(tz=timezone.utc).isoformat()
        alive_count = 0
        for job in jobs.values():
            stats = _ps_sample(job.pid)
            if stats is None:
                if job.exit_code is None:
                    job.exit_code = 0     # ps gone = process exited (or was killed)
                _emit_heartbeat(
                    jsonl_path, log_path, ts_iso, job,
                    stats=None, flags=["EXITED"],
                )
                continue
            alive_count += 1
            job.cpu_history.append(stats["cpu_pct"])
            job.rss_history.append(stats["rss_kb"])
            job.mtime_history.append(_artefact_mtime(job.output_artefact))
            job.last_seen_alive = time.time()

            flags = _classify_health(
                job,
                cpu_floor=args.cpu_floor,
                stall_samples=args.stall_samples,
                no_output_samples=args.no_output_samples,
            )
            _emit_heartbeat(
                jsonl_path, log_path, ts_iso, job, stats=stats, flags=flags,
            )

        if alive_count == 0:
            footer = (
                f"# All tracked PIDs exited at "
                f"{datetime.now(tz=timezone.utc).isoformat()} "
                f"after {sample_count} samples\n"
            )
            with open(log_path, "a") as fh:
                fh.write(footer)
            with open(jsonl_path, "a") as fh:
                fh.write(json.dumps({
                    "event": "session_end",
                    "ts": datetime.now(tz=timezone.utc).isoformat(),
                    "samples": sample_count,
                }) + "\n")
            return 0

        if args.max_samples and sample_count >= args.max_samples:
            return 0

        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
