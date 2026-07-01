# Compute-speedup notes -- 2026-07-01

Investigated speed levers for the two long-running experiments (G7
walk-forward + Phi4.1 physical rerun) as part of the "keep tabs +
speed up" ask. Actual code changes landed in this session are marked
with **[SHIPPED]**; the rest are documented for next-session pickup.

## What's shipped

### [SHIPPED] Progress logging inside `_drive_squad_replay` + `_drive_squad_replay_with_isolated_candidate`

**File:** `sim/scoring/run_phi4_squad_gate.py`

Both driver functions now emit an `INFO` line every 5-10 pct of bars
processed (or every 10 min of wall-clock, whichever comes sooner)
with `bars processed / total / pct / elapsed / eta / trades /
proposals_all` fields. Also a starting line and a completion line
with `bars/sec` throughput.

Rationale: replays go silent for 30-60 min without any stdout signal,
making it impossible from outside the process to distinguish
"progressing normally" from "actually frozen". This resolves that.
Zero runtime overhead (one integer modulo + wall-clock read per bar,
one log line every ~5 pct of bars).

### [SHIPPED] `--parallel-arms N` flag on `run_phi41_gate`

**File:** `sim/scoring/run_phi41_gate.py`

F17 isolated arms are pairwise-independent (each rebuilds its own
squad + ledger + `out` object). Wired
`concurrent.futures.ProcessPoolExecutor` behind a `--parallel-arms N`
CLI flag (default 1 = serial, deterministic, matches sealed audit
reruns). Recommended value on an 8-core Mac: **4-6**.

Expected speedup for the F17 phase (dominant time sink for the
physical rerun): near-linear up to core count. Physical rerun's F17
phase currently takes ~1.5 hr; with `--parallel-arms 6` it should
drop to ~15-20 min.

### [SHIPPED] `scripts/monitor_compute_jobs.py`

Zero-dep stdlib health-monitor for long-running experiments. Samples
CPU + RSS + elapsed time + output-artefact mtime every N seconds and
writes to `reviews/compute_heartbeat.{log,jsonl}`. Flags STALLED /
MEMORY_DROP / NO_OUTPUT_PROGRESS. Usage:

```bash
python scripts/monitor_compute_jobs.py \
    --pid 12345:g7_walk_forward \
    --pid 67890:phi41_physical_rerun \
    --output-artefact 12345:programs/M001_multi_agent_ensemble/reviews/g7_v1_checkpoint_walk-forward-baseline_report.md \
    --interval 60 --cpu-floor 30 --stall-samples 5
```

Runs until every tracked PID exits. `tail -f
programs/M001_multi_agent_ensemble/reviews/compute_heartbeat.log`
gives a live view.

## Deferred to next session

### [DEFERRED] Hoist `precompute()` out of per-agent `prepare()`

5 agents (Isagi, Bachira, Rin, Barou + Isagi v2) each call the same
`agent.rules.engine.precompute(bars, cfg)` inside their own
`prepare(symbol, bars)`. That's 5x redundant work per symbol per
replay. Precompute cost is ~30 sec per symbol on our panel (log
says "prepared USDCAD: 17722 bars, 1704 zones, 2386 swings").

**Estimated saving:** 5 agents x 3 symbols x 30 sec = 7.5 min per
replay, dropping to 1.5 min if the ctx is shared.

**Refactor sketch:**

1. Add `harness.precompute_context(bars, cfg) -> PrecomputeCtx` in
   `sim/core/shared_precompute.py`.
2. Add optional `precomputed_ctx=` kwarg to each of the 5 agents'
   `prepare()`. When present, agents skip their internal
   `precompute()` call and use the shared ctx.
3. Harness calls `precompute_context` once per symbol, then passes
   it to each agent.

**Blocker:** any non-determinism in `agent.rules.engine.precompute`
would lose reproducibility of sealed verdicts. Need to verify the
function is pure (given `(bars, cfg)` -> deterministic output) before
landing.

### [DEFERRED] On-disk cache for zones/swings/ATR

Same target as the above, but with a parquet cache under
`data/precompute_cache/<symbol>_<data_hash>_<cfg_hash>.parquet`.
Slower than in-memory hoisting on the first run but ideal for
running many experiments back-to-back.

**Estimated saving:** ~15 min per re-run of the same panel with the
same cfg. Not useful for the G7 walk-forward (single run) but very
useful for Phi5 arm re-sim (Arms 1-5 = 5 runs of the same panel).

### [DEFERRED] Vectorised bar-to-MarketState creation

Currently done per-bar inside the interleaved loop
(`_bar_to_market_state(bar, tick_id=...)` + a second
`MarketState(...)` constructor to reset the symbol). Could be
batched with a pandas-based bar table + integer indexing.

**Estimated saving:** ~5-10 pct on the main loop (small but easy).

### [DEFERRED] Parallelise G7 leave-one-out squads

Same pattern as F17 arms -- once C2/C3 leave-one-out squads are
implemented in `run_g7_v1_checkpoint_gate.py`, they'll be 8
independent replays. Wire the same `ProcessPoolExecutor` pattern.

**Estimated saving:** 8 leave-one-out squads x ~30 min each = 4 hr
serial -> ~30 min with `--parallel-loo 8`. This is what tips the G7
full-batch run from PROTOCOL sec 8 stop rule #2's 32h estimate down
to something like 4-6h.

## Health-monitor coverage today

Both currently-running background jobs are being monitored (as of
16:37 UTC 2026-07-01):

- **G7 walk-forward** (pid 73654): 36+ min elapsed, single-pass
  replay across 2015-2025 panel, 99-100% CPU, RSS climbing (trades
  accumulating in memory).
- **Phi4.1 physical rerun** (pid 68336): 1:52 hr elapsed, cycling
  through F17 isolated arms, 100% CPU, RSS cycling 87MB -> 630MB
  (arm transitions).

Neither is stalled. Both will fire a completion notification when
they exit.
