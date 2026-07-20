# Phase AC — AC.2 DEFERRED

- **Status:** DEFERRED (all 4 arms — A1, A2, B1-hard, B1-soft)
- **Primary blocker:** AC.0 FAILED per PROTOCOL §5 fail-branch and
  §10 kill condition. AC.2 pass-gates on AC.1 producing ≥1 passing
  sub-arm per movable agent (§5 AC.2 opening line: *"Runs only if
  AC.1 produces ≥ 1 passing sub-arm per agent"*). AC.1 did not fire.
- **Secondary blocker:** USDJPY / USDCHF are not in the production
  parquet cache; a full extended-panel run per §7 would be missing
  those two symbols even if AC.0 / AC.1 had cleared.

## What was pre-locked (from PROTOCOL §5 AC.2)

| Arm | Shape | Would require |
|---|---|---|
| A1 | baseline (control) | current 3-pair panel + banked-config reproduction |
| A2 | single-squad, movable agents' `.symbols` = AC.1 passing set (UNION) | full AC.1 passing set + extended panel |
| B1-hard | multi-squad, HARD isolation (3 processes) | full AC.1 passing set + extended panel + squad-isolation harness |
| B1-soft | multi-squad, SOFT isolation (shared workspace) | full AC.1 passing set + extended panel |

- **Additivity flag (§5.1) is pre-locked to UNION.** No amendment
  needed; this decision remains binding if Phase AC is ever revived
  and reaches AC.2.

## Path forward

- Same as `results/ac1_NOT_FIRED.md` §"Path forward" — a materially
  amended pre-reg statistic OR a wider banked panel is required
  before AC.0 → AC.1 → AC.2 can meaningfully fire.
- USDJPY / USDCHF cache pull is orthogonal; do whenever convenient
  on the VM: `foreach ($s in @("USDJPY","USDCHF")) { .venv\Scripts\python.exe scripts\download_data.py --symbol $s --years 11 --timeframes H4 D1 --source mt5 --refresh }`

No AC.2 outputs (`ac2_<arm>.json`, `ac2_verdict.md`) are produced by
this run. The pre-reg §11 file-footprint plan reserves those slots
for a future amendment.
