# E020 — STOP NOTICE

**Date:** 2026-07-20 · **Verdict:** `dead` · **Registry status:** LOCKED

Per PROTOCOL §6 and `PROTOCOL_DISCIPLINE.md` §5, this notice records
that E020 (MFE-ratcheted trailing stop) failed its pre-registered
`alive` criteria and is stopped without Phase 3 (production wiring).

## What was found

Zero of the twelve pre-registered arms (`activation_R × lock_fraction`
= `{1.0, 1.2, 1.3} × {0.4, 0.5, 0.6, 0.7}`) achieved pooled bootstrap
95 % CI lower > 0 on ΔSharpe of the per-trade R sequence versus the
deployed `all_on` cell. All twelve arms produced negative pooled
ΔSharpe (range −0.103 to −0.114), all with p = 0.0000 and 0/5 folds
positive. BH-FDR at α = 0.10 rejected H0 in the direction of
**degradation** for every arm.

Numeric detail:
[`../../programs/E020/results.json`](../../programs/E020/results.json).
Narrative + mechanism diagnostics:
[`REPORT.md`](./REPORT.md).

## Why

The MFE-ratchet did reduce the worst-decile tail from −2.00 R to −1.00
R (a real +1 R tail cap on ≈ 239 aggregate R). That gain was dominated
by the runner-choke cost: P(winner reaches ≥ 1 R) fell from 0.553
(baseline) to as low as 0.333 under the tightest arm — roughly 22 pp
of would-be 1R+ winners were chopped to 0.4–0.9 R exits by the ratchet.

The deployed cell's existing BE-at-1R + wick-proof close SL + panic
already provides most of the tail cap the ratchet could add; a
continuous MFE-tightening on top of that stack is net-negative on the
same trade distribution.

The finding is robust across `activation_R` (fire later → same loss
magnitude within 0.005 ΔSharpe) and `lock_fraction` (lock more → same
loss magnitude within 0.005 ΔSharpe). The grid is not the problem —
the mechanism is a bad fit for this cell.

## What we DO NOT do

Per PROTOCOL §6 and `PROTOCOL_DISCIPLINE.md` §5:

1. **NOT** extending the arm grid to search for a positive arm.
2. **NOT** promoting Δ tail-mean R (a large positive secondary
   guardrail) to primary post hoc.
3. **NOT** shipping any ratchet variant to the deployed cell.
4. **NOT** re-running Phase 2 with a modified rule spec (that would
   be a NEW study, requiring fresh pre-registration).
5. **NOT** claiming a partial win from any single arm or any single
   symbol.

## What we DO

1. Keep the shipped `all_on` cell (EURUSD/GBPUSD/USDCAD, H4,
   `zone_d1_against`, wick-proof SL + BE-at-1R + PLG) as-is.
2. Register this study as `stopped_dead` in the campaign registry
   (EXPERIMENTS.md row updated in the same commit as this notice).
3. Preserve the results.json, REPORT.md, and this STOP_NOTICE.md on
   `main` for future meta-analysis.
4. Unblock E023 (post-BE structure trail) which was gated on this
   verdict per the campaign group note in EXPERIMENTS.md. E023 will be
   pre-registered separately following the same discipline (fresh
   PROTOCOL, no post-hoc grid revision from E020).

## Family-multiplicity impact on E025

E020's dead verdict removes 12 arms from the campaign's search-width
argument. E025 (joint exit-stack Pareto) can no longer include E020 as
a stack component. Effective family size for the deflated Sharpe
argument in E025 is now `57 − 12 = 45` — E025 protocol should be
re-checked when it comes up.
