# Phase AJ-2 — Barou n-growth on the extended window (pre-registration)

Registered: 2026-08-04, AFTER Phase AJ's IS readout (Barou:EURUSD
registered_near_miss, PF 2.03 / meanR +0.45 / n=25) and BEFORE any
AJ-2 replay executed. This is the pre-declared, floors-first way to
act on a near-miss: grow the sample honestly, don't lower the bar.

## Hypothesis

H-AJ2: Barou's deployed weapon (v1.3, impulse 30, target_rr 1.5)
carries positive causal expectancy on EURUSD and USDCAD when the
in-sample window is extended to 2015-01-01 → 2023-12-31 (9 years —
the full banked history before the sealed window), lifting n above
the floor that Phase AF and AJ could not reach on 5-year windows.

## Cells (declared exhaustively — 3, all Barou)

Barou × {EURUSD, USDCAD, GBPUSD} on the extended IS window. GBPUSD is
included for completeness but carries the AJ prior AGAINST it
(PF 1.027); a GBPUSD pass would be surprising and gets an extra
robustness look (split-half sign check) before any promotion claim.

## Method

ONE replay, 2015-01-01 → 2023-12-31, same expanded-roster harness as
Phase AJ (`run_phase_aj.py`, own process), same causal semantics,
deployed configs, no knob sweeps. Only Barou's cells are being
JUDGED; every other agent×symbol readout from this replay is
context, not a claim, and cannot be promoted from this study.

**Known-data note:** 2019–2023 (the AJ IS window, n=25 of Barou's
EURUSD trades) is a subset of the extended window and has been SEEN.
The genuinely new evidence is 2015–2018. The REPORT must therefore
show the 2015–2018 sub-window separately: if the new years are flat
or negative and the pooled pass rides entirely on the already-seen
2019–2023 trades, the cell is `not_promoted (subset_carried)`
regardless of pooled numbers.

## Promotion rule (declared before execution)

1. Pooled IS floors per cell: PF ≥ 1.15 AND mean R ≥ +0.05 AND
   n ≥ 40, AND the unseen 2015–2018 sub-window is direction-positive
   (total R > 0) on its own.
2. Validation: ONE sealed replay 2024-01-01 → 2026-07-31 (the same
   sealed window Phase AJ never opened), run only if ≥ 1 cell passes
   rule 1. Cell PASSES if validation PF ≥ 1.10 AND mean R ≥ +0.03
   AND n ≥ 10 (floor lowered from AF's 15 with reason: Barou's
   documented fire rate is ~5–6 trades/year/symbol; 15 was calibrated
   for busier agents; 10 in 31 months is the honest equivalent).
   Floor declared HERE, before any validation data is seen.
3. A PASS ⇒ recommendation: shadow-paper pitch time for Barou on the
   passing away symbol (user-approved roster change, shadow-only).
   No live-order implications; F018 stays off.

## Multiplicity

3 cells, one selection family, single-shot validation. Same binomial
sketch convention as AF/AJ in the REPORT.

## Abort conditions

Replay crash / squad-wide zero trades → STOP_NOTICE. Home-cell
(USDCAD) interaction shift vs AJ > 0.15 PF → flag, since the same
expanded roster should reproduce AJ's interactions on the shared
sub-window.
