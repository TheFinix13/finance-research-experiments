# E021 — STOP NOTICE

**Date:** 2026-07-20 · **Verdict:** `dead` · **Registry status:** LOCKED

Per PROTOCOL §6 and `PROTOCOL_DISCIPLINE.md` §5, this notice records
that E021 (Partial exit at fixed-R milestone) failed its pre-registered
`alive` criteria — and also failed the H2 special-case
`parked_lower_variance_lower_return` gate — and is stopped without
Phase 3 (production wiring). `LiveConfig.partial_exits` remains `False`
in production.

## What was found

Zero of the nine pre-registered arms
(`partial_R × partial_fraction = {0.7, 1.0, 1.3} × {0.25, 0.4, 0.5}`)
achieved pooled bootstrap 95 % CI lower > 0 on ΔSharpe of the per-trade
R sequence versus the deployed `all_on` cell. All nine arms produced
negative pooled ΔSharpe (range **−0.1314 to −0.1076**), all with
BH-adjusted p = 0.0000 and 0/5 folds positive. BH-FDR at α = 0.10
rejected H0 in the direction of **degradation** for every arm.

The H2 special-case rule (`parked_lower_variance_lower_return`) did not
rescue any arm either: while Δ variance of R is statistically negative
for all 9 arms (CI-UB in [−0.85, −0.43]), PROTOCOL §5.3 requires the
ΔSharpe CI to *include* 0 for H2 to fire, and every arm's ΔSharpe CI
lies entirely below 0 (upper bound in [−0.079, −0.099]). The
sign-of-variance-shift observation is preserved for E025's information
but does NOT elevate this study to `parked_*`.

Numeric detail:
[`../../programs/E021/results.json`](../../programs/E021/results.json).
Narrative + mechanism diagnostics:
[`REPORT.md`](./REPORT.md).

## Why

The partial-exit mechanic *is* doing what PROTOCOL §3 specified — the
guardrails and mechanism diagnostics all fire in the predicted
directions:

- Δ tail-mean R (worst 10 %) = **+1.0R** across all 9 arms — the
  partial caps the loss decile from −2R to −1R exactly.
- Δ variance of R = **−0.49 to −0.90 R²** across all 9 arms
  (CI-UB < 0 on all) — a first-order variance reduction.
- Δ P(alt_r > 0 &#124; partial fired) = **+7 to +18 percentage points** —
  the partial genuinely converts would-be losers into net winners on
  the fired subset.

These gains are dominated by the **mean-R give-up on the
50–63 % fired cohort**:

- Fire-rate: 63 % at `partial_R = 0.7`, 57 % at `partial_R = 1.0`,
  47 % at `partial_R = 1.3`.
- Δ mean R on the fired cohort: **−0.03 to −0.17 R** depending on the
  `(partial_R, partial_fraction)` arm.
- Δ mean R on the whole population: **−0.18 to −0.23 R** across all 9
  arms.
- Net Sharpe cost: **−0.108 to −0.131** — the mean drop is larger than
  the variance reduction supports on the ΔSharpe scale.

The deployed cell's existing BE-at-1R + wick-proof close SL + PLG
stack already provides most of the tail cap the partial could add; a
mechanical partial-close on top of that stack pays for a real tail-cap
gain by capping the residual runner on the ~50–63 % of trades whose
paths cross the trigger, and the residual-cap cost outweighs the
tail-cap benefit on the ΔSharpe primary.

The finding is robust across `partial_R` (fire later → same loss
magnitude within 0.024 ΔSharpe) and `partial_fraction` (bank more →
same loss magnitude within 0.017 ΔSharpe). The grid is not the problem —
the mechanism is a bad fit for this cell's TP = 1.5R geometry and
existing BE-driven tail protection.

## What we DO NOT do

Per PROTOCOL §6 and `PROTOCOL_DISCIPLINE.md` §5:

1. **NOT** extending the arm grid to search for a positive arm.
2. **NOT** promoting Δ tail-mean R = +1.0R (a large positive secondary
   guardrail) or Δ variance R (large statistically-negative secondary)
   to primary post hoc.
3. **NOT** shipping any partial-exit variant to the deployed cell.
   `LiveConfig.partial_exits` stays `False`.
4. **NOT** re-running Phase 2 with a modified rule spec (that would be
   a NEW study, requiring fresh pre-registration).
5. **NOT** claiming a partial win from any single arm or any single
   symbol.
6. **NOT** re-classifying under H2 — the ΔSharpe CI is entirely below
   0 on all 9 arms, so the "lower-variance / straddles-0-Sharpe"
   special case is not triggered.

## What we DO

1. Keep the shipped `all_on` cell (EURUSD/GBPUSD/USDCAD, H4,
   `zone_d1_against`, wick-proof SL + BE-at-1R + PLG,
   `LiveConfig.partial_exits = False`) as-is.
2. Register this study as `stopped_dead` in the campaign registry
   (`EXPERIMENTS.md` row updated by the coordinator in the same commit
   as this notice).
3. Preserve `results.json`, `REPORT.md`, and this `STOP_NOTICE.md` on
   `main` for future meta-analysis.
4. Record the **variance-generator observation** (Δ variance of R
   statistically negative on all 9 arms, monotone in both grid
   dimensions) in `REPORT.md` §7 and in the E025 planning discussion,
   as descriptive engine-behaviour context — not as a re-scoring of
   E021 or as authorisation for E025 to consume E021 as a stack
   component.

## Family-multiplicity impact on E025

E021's `dead` verdict removes 9 arms from the campaign's search-width
argument. E025 (joint exit-stack Pareto) can no longer include E021 as
an *alpha-additive* stack component. The remaining live search width
depends on E022, E023, E024 outcomes; effective family size for the
deflated Sharpe (`bailey2014deflated`) argument in E025 will need to be
recomputed once each sibling study lands its verdict.

E021's variance-reduction property is preserved as **descriptive
context** for a future risk-budget-oriented E025 framing, per
REPORT.md §7. That framing would be a new pre-registered study, not a
re-entry of E021.
