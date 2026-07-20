# E025 — STOP notice (`cancelled_dependency_failed`)

**Date:** 2026-07-20 · **Verdict:** `cancelled_dependency_failed`
· **Phase 2:** not run · **Phase 3:** not authorised

---

## Trigger

PROTOCOL §4a §"Handling of upstream verdicts", case **"Zero `alive`"**:

> "E025 is `cancelled_dependency_failed`. No stack ships."

At the time of this stop notice, all four upstream studies have landed
`dead`:

| Study | Verdict | Commit | ΔSharpe summary (pooled or per-symbol worst) |
|---|---|---|---|
| E020 (MFE ratchet) | `dead` | `7e1a3e7` | [−0.114, −0.103] across 12 arms |
| E021 (partial exit at R) | `dead` | `343b512` | [−0.131, −0.108] across 9 arms |
| E022 (structure TP snap) | `dead` | `dbe398c` | [−0.028, −0.001] across 11 dead arms (+ 1 inactive) |
| E024 (near-TP stall exit stage-1) | `dead` | `93f4887` | EURUSD [−0.094, −0.085], GBPUSD [−0.095, −0.084], USDCAD [−0.145, −0.133] across 24 arms |

The gate is deterministic: with zero upstream arms crossing the `alive`
bar, there is no `(activation_R, lock_fraction)` for E020, no
`(partial_R, partial_fraction)` for E021, no `(snap_source,
snap_distance)` for E022, and no `(activation_R, stall_signal,
stall_secs)` for E024 to plug into the composition ordering. E025's
compositions `π1 = A`, `π2 = A+B`, `π3 = A+B+C`, `π4 = A+B+C+D` are
therefore undefined. Nothing to test. Nothing to compose. Study
terminates cleanly.

## What is NOT done as a result

Per `PROTOCOL_DISCIPLINE.md` §5 and PROTOCOL §6 stop rule:

- Phase 2 sweep is **not** launched.
- The family-size-57 deflated-Sharpe budget (12 + 9 + 12 + 24 upstream
  arms) is **not** spent — no arm passes upstream, so there is no
  selection to deflate.
- The bar-granularity sensitivity (PROTOCOL §5.2) is **not** run.
- The OOS-only sensitivity on 2024-07 → 2025-12 (PROTOCOL §5.3) is
  **not** run.
- The 2026-07-16 GBPUSD live-ticket case study (PROTOCOL §5.4) is
  **not** produced (tickets 2969136564 and 2966547972 are already
  descriptively covered in the E024 REPORT.md §"Worked-example
  outcomes" section; no additional coverage is needed under E025).
- The grid is **not** extended, and no arm hyperparameters are
  retuned. Any retuning would violate `PROTOCOL_DISCIPLINE.md` §5.
- **No production code touched.** `LiveConfig.partial_exits = False`,
  `LiveConfig.exit_manager_enabled = False`, and the deployed
  1.5R fixed TP on the `zone_d1_against` H4 all_on cell all stay
  as they are.
- **No follow-on family opened** on the same trade population.

## What IS done

- This STOP_NOTICE.md is committed to the record.
- `experiments/E025_joint_exit_stack/MANIFEST.md` has its `Status:`
  field flipped and its `## Verdict` block appended.
- `EXPERIMENTS.md` row for E025 is updated to
  `CANCELLED-DEPENDENCY-FAILED`.
- The `programs/E025/` directory is **not** created (no code to ship
  under E025).
- The `DATA_LEDGER.md` row for E025 is **not** opened (no bar-slice
  consumption; the four upstream studies each already own their
  ledger consumption row).

## Family-multiplicity accounting (for the historical record)

The four upstream studies opened four independent FDR families:

| Family | Size | BH-α | Rejected in DEGRADATION direction | Rejected in FAVOR direction |
|---|---:|---:|---:|---:|
| E020 (pooled, 12) | 12 | 0.10 | 12 / 12 | 0 / 12 |
| E021 (pooled, 9) | 9 | 0.10 | 9 / 9 | 0 / 9 |
| E022 (pooled, 12) | 12 | 0.10 | 7 / 12 | 0 / 12 |
| E024 (per-symbol × 3, 24 each) | 72 total | 0.10 | 22+24+24 = 70 / 72 | 0 / 72 |
| **Total** | **105** | 0.10 | **98 / 105** | **0 / 105** |

Every non-null BH-FDR rejection across the entire exit-side campaign
went in the direction opposite to H1 — i.e. the exit-side rule
degraded ΔSharpe rather than improved it. E022 is the closest to
"harmless" (5 arms not rejected either way; effect sizes small), but
even its ΔP(TP fills)-based sanity gate does not compensate for the
per-winner R give-up.

The E025 verdict is **`cancelled_dependency_failed`**, which is
functionally equivalent to "`dead` upstream" but retains the
distinction for future readers: E025's own machinery never ran, so
no E025-specific p-value exists to interpret.

## What DOES this campaign say about the near-miss pathology?

The motivating case (GBPUSD 2969136564 missing TP by 0.5 p and giving
back 36.5 p) is real, but the population evidence across 2,388
counterfactual trades and 105 pre-registered arms shows there is **no
mechanical exit-side fix on the deployed cell's 1.5R TP geometry**
that improves Sharpe:

1. **Runner-choke path (E020 continuous MFE trail):** any early
   tightening chops the ≈ 30–40 % of trades that would have run to
   TP faster than it saves the ≈ 5–8 % near-misses that give back.
2. **Rebank path (E021 partial at 1R milestone):** banking early
   caps the winners in exactly the population where they matter
   most (the deployed cell's 1.5R TP means realising 25–50 % of
   position at 1.0R sacrifices the 0.5R differential on a majority
   of winners).
3. **TP-snap path (E022 order-placement pull-in):** raising fill
   probability by up to +3.48 pp gives up more mean-R than it gains
   (winners realised at less R).
4. **Near-TP stall detection path (E024 failure-to-extend close-at-
   market):** the population in the `mfe_r ∈ [1.45, 1.50]` band is
   ≈ 44:1 clean-TP:give-back on GBPUSD — any detector armed in that
   zone eats a majority of clean TPs.

The deployed 1.5R TP has been priced correctly by E004 walk-forward
and E005 cross-pair sealed. This campaign's collective negative is
strong evidence that the exit-side rule set on the current cell is
already close to optimal, given the entry model.

**Where next?** The next legitimate exit-side campaign would either
(a) redesign the underlying cell (different `target_rr` from a fresh
walk-forward), or (b) test a genuinely new mechanism outside the
E020–E024 family (E023 post-BE structure trail, still pre-registered
but Phase-2 unstarted, is the obvious candidate). Neither would be an
amendment to E025 — both would need a fresh pre-registration.

---

**References for this notice.** All numeric values quoted above are
from the four upstream studies' `results.json` files (commits
`7e1a3e7`, `343b512`, `dbe398c`, `93f4887`) and their REPORT.md
files. `PROTOCOL_DISCIPLINE.md` §5 (no post-freeze parameter change,
no post-hoc grid extension) and PROTOCOL §4a §6 (stop-rule label
map) govern the decision.
