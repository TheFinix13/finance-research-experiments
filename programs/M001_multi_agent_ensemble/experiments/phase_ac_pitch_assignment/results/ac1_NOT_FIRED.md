# Phase AC — AC.1 NOT FIRED

- **Status:** NOT FIRED (all 8 sub-arms)
- **Reason:** AC.0 FAILED per PROTOCOL §5 fail-branch and §10 kill
  condition. AC.1 pass-gates on AC.0 PASS (§5 AC.1 opening line:
  *"Runs only if AC.0 PASSES"*).
- **AC.0 verdict:** see `results/ac0_verdict.md`.

## Sub-arm status matrix (pre-locked from PROTOCOL §5 AC.1)

| Sub-arm | Agent | `.symbols` | Status | Reason |
|---|---|---|---|---|
| AC.1.chi-a | Chigiri | AUDUSD, NZDUSD | NOT FIRED | AC.0 gate FAILED |
| AC.1.chi-b | Chigiri | USDJPY | NOT FIRED + BLOCKED | AC.0 gate FAILED, and USDJPY needs cache pull |
| AC.1.chi-c | Chigiri | GBPUSD | NOT FIRED | AC.0 gate FAILED |
| AC.1.rin-a | Rin | EURUSD, USDCHF | NOT FIRED + BLOCKED | AC.0 gate FAILED, and USDCHF needs cache pull |
| AC.1.rin-b | Rin | EURUSD, USDJPY | NOT FIRED + BLOCKED | AC.0 gate FAILED, and USDJPY needs cache pull |
| AC.1.rin-c | Rin | USDCHF | NOT FIRED + BLOCKED | AC.0 gate FAILED, and USDCHF needs cache pull |
| AC.1.kun-a | Kunigami (un-retire) | AUDUSD, NZDUSD | NOT FIRED | AC.0 gate FAILED |
| AC.1.kun-b | Kunigami (un-retire) | AUDUSD, NZDUSD, USDJPY | NOT FIRED + BLOCKED | AC.0 gate FAILED, and USDJPY needs cache pull |

## What would have run today (had AC.0 passed)

Only three sub-arms were compute-runnable without the USDJPY/USDCHF
cache pull:

- **AC.1.chi-a** (Chigiri × AUDUSD/NZDUSD) — AUDUSD/NZDUSD are in the
  production parquet cache.
- **AC.1.chi-c** (Chigiri × GBPUSD) — already in cache.
- **AC.1.kun-a** (Kunigami un-retired × AUDUSD/NZDUSD).

Estimated wall-clock: ~30-90 min per sub-arm on the extended G7
walk-forward panel (harness supports this via the newly-landed
`--symbols` flag, commit `3e0f611f`).

## What still needs a data step before it can ever run

USDJPY and USDCHF H4 + D1 (11 years) via the Windows/MT5 VM
`scripts/refresh_cache.py`. Commanded once from the VM (see final
report + PROTOCOL §12.1). Without it, `AC.1.chi-b`, `AC.1.rin-a`,
`AC.1.rin-b`, `AC.1.rin-c`, and `AC.1.kun-b` are unrunnable even
under a passing AC.0.

## Path forward (if the user chooses to revive Phase AC)

1. Amend the pre-reg per §13 with a new statistic that does not
   require per-agent per-pair OLS regression on a banked panel whose
   `.symbols` restrictions collapse per-movable-agent unique x-value
   count to 2/1/0 (see `results/ac0_verdict.md` §5a for the analysis).
2. Alternatively: re-run the g7retry1-phi41 walk-forward with movable
   agents' `.symbols` deliberately widened to the full 5-pair panel
   BEFORE the replay, then re-freeze the banked telemetry so the
   AC.0 regression has n=5 per agent (as the pre-reg §9 pre-mortem
   assumed).
3. Cache pull for USDJPY / USDCHF is orthogonal — do it whenever
   convenient on the VM.

No agent parameters, thresholds, or aggregator behaviour are altered
by this NOT-FIRED verdict.
