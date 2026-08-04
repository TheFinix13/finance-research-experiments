# Phase AH — S3 FOMC statement tone → post-release drift (pre-registration)

Registered: 2026-08-04, BEFORE any statement was fetched or scored.
Charter: multi-pair-trading-agent D141 (Sae v2 ladder, step S3).

## Hypothesis

H-AH1: the hawkish/dovish tone SHIFT of an FOMC statement relative to
the previous statement, measurable from the released text within
seconds of publication, predicts the direction of EURUSD drift over
the following 1–4 hours. (Hawkish shift → USD bid → EURUSD down.)

If this holds on historical text alone, live deployment is cheap: the
statement is plain text published at a known second (14:00 ET), and
dictionary scoring is instantaneous — no audio pipeline needed. The
18:30 press conference (S4) is only worth engineering if this
text-only signal exists.

## Data

- Events: the 87 scheduled FOMC statements in the frozen 349-event
  panel (sha `cfd18602…`, Phase AE lineage). Unscheduled/emergency
  meetings are excluded by construction.
- Text: `federalreserve.gov/newsevents/pressreleases/monetaryYYYYMMDDa.htm`
  per meeting date; raw HTML archived under `data/statements/` at
  fetch time; text extracted by stripping tags, keeping the statement
  body only. Any statement whose URL fails resolution is logged and
  dropped (count disclosed in REPORT).
- Prices: EURUSD M15 parquet (agent cache).

## Scoring (declared in full before execution)

Dictionary tone score, Apel–Grimaldi-style, adapted to FOMC statement
vocabulary. Case-insensitive, whole-word, counted over the statement
body:

- HAWKISH terms: inflation pressures, elevated inflation, upside
  risks, tighten, tightening, restrictive, raise the target range,
  increase the target range, strong labor market, robust, solid pace,
  above 2 percent, persistent inflation, further rate increases,
  reducing its holdings, balance sheet reduction.
- DOVISH terms: accommodative, accommodation, lower the target range,
  reduce the target range, cut, easing, downside risks, weak,
  weakness, slowed, softening, muted inflation, below 2 percent,
  patient, moderate pace, supporting the flow of credit, asset
  purchases, maintain the target range at 0.

Score(statement) = (n_hawkish − n_dovish) / (n_hawkish + n_dovish),
0 when no terms match. **Primary predictor: ΔTone = Score(t) −
Score(previous scheduled statement).** (First statement of the panel
has no ΔTone and is excluded from testing.)

No term may be added, removed, or reweighted after the first score is
computed. If the lists prove empty on real text (pathological match
failure), the study STOPS with a STOP_NOTICE rather than editing
terms in place.

## Outcome and test

- t0 = first M15 bar with open ≥ statement time (exact UTC from the
  frozen panel). Reference = close(t0 − 1).
- Outcomes: EURUSD pips from reference to close(t0+3) [~1h] and
  close(t0+15) [~4h].
- Directional prediction: ΔTone > 0 → short EURUSD; ΔTone < 0 →
  long; ΔTone = 0 → no trade (excluded, count disclosed).
- Splits: IS = statements 2015–2021; VALIDATION (sealed) = 2022–2025.
- IS-alive if, at the 1h horizon: n ≥ 35 usable statements, sign
  agreement ≥ 58%, and Spearman ρ(ΔTone, pips) ≤ −0.20.
- Validation PASS: sign agreement ≥ 55% at 1h AND ρ sign unchanged.
- The 4h horizon is a secondary readout (reported, not gating).

## Outputs

- `data/statements/*.htm` (raw), `results/statement_scores.csv`,
  `results/tone_test_is.json`, `results/tone_test_validation.json`
  (only if IS-alive), `REPORT.md`.
