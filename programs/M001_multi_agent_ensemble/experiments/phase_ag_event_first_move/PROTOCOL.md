# Phase AG — S2 "follow the first move" event-continuation study (pre-registration)

Registered: 2026-08-04, BEFORE any arm was executed.
Charter: multi-pair-trading-agent D141 (Sae v2 ladder, step S2).
Hypothesis owner: user directive 2026-08-04 — "we don't jump into
conclusions, we wait for the news to make a move on the market and
follow that trend fully."

## Hypothesis

H-AG1: after a scheduled high-impact USD release, when the FIRST
post-release move is large relative to recent volatility, price
CONTINUES in the direction of that first move often enough to clear
costs and a fixed-R target before returning to the pre-release stop.
This requires no knowledge of the release's content — only its
timestamp and the market's own reaction (fully causal, no NLP).

## Relationship to Phase AE (honesty)

Phase AE consumed this same 349-event panel testing DIFFERENT
mechanics (Sae's fade/ride TQS gate) and FAILED unconditionally.
Its outcomes are a prior, not a tuning signal, for this study. To
protect against panel-mining, arms are tuned ONLY on the 2015–2021
in-sample half; 2022–2025 is sealed for one-shot validation of
surviving arms.

## Fixed inputs

- Events: `news_calendar_frozen_2026-07-24.json` (349 USD events:
  131 NFP, 131 CPI, 87 scheduled FOMC statements; primary-source
  timestamps; sha-pinned by Phase AE). Extracted from the
  `multi-agent-ensemble` branch, byte-identical.
- Prices: EURUSD M15 parquet (agent cache, read-only). GBPUSD M15
  as a robustness readout only (no tuning on it).
- Costs: 1.2 pips per round trip deducted from every trade.

## Mechanics (all constants declared here)

- t0 = first M15 bar whose open time >= event time.
- Pre-event reference price = close of the last bar BEFORE t0.
- Volatility unit: ATR(96) on M15 computed strictly on bars < t0
  (~24h lookback).
- Impulse window: K bars starting at t0, K ∈ {1, 2} (15 or 30 min).
- Impulse = close(t0+K-1) − reference. Direction = its sign.
- Trigger: |impulse| ≥ m × ATR96, m ∈ {3, 5, 8}.
- Entry: at close(t0+K-1) (the moment the impulse is confirmed),
  in the impulse direction.
- Stop: the opposite extreme of the impulse window (min low / max
  high of bars t0..t0+K-1); R = |entry − stop|.
- Target: entry + direction × TP_R × R, TP_R ∈ {1.5, 2.5}.
- Exit: TP or SL, whichever an M15 bar touches first (both touched
  in one bar counts as SL — conservative); else market exit at the
  close of bar t0+48 (12 hours).
- Grid: K × m × TP_R = 2 × 3 × 2 = **12 arms**, exhaustive, no
  extensions without a dated amendment committed before running.

## Splits and verdict rule (declared before execution)

- IN-SAMPLE: events 2015-01-01 .. 2021-12-31.
- VALIDATION (sealed): events 2022-01-01 .. 2025-12-31.
- An arm is IS-alive if: n ≥ 30, net mean ≥ +2.0 pips/trade, and
  net total > 0 in BOTH the 2015–2017 and 2018–2021 sub-halves
  (sign-consistency guard).
- IS-alive arms (all of them, no cherry-pick) go to ONE validation
  pass. Validation PASS floors: n ≥ 15, net mean ≥ +1.5 pips/trade.
- If zero arms are IS-alive: verdict `dead_unconditional`, and the
  REPORT must state whether large-impulse events were simply too
  rare (n starvation) vs present-but-random (the informative
  distinction for S1, which adds the surprise dimension).

## Multiplicity

12 arms, per-arm binomial sketch reported against the null of
zero-mean returns; family-level honesty: with 12 arms and these
floors, ≥1 false IS-alive arm is expected under the null with
probability reported in the REPORT (bootstrap, 1,000 resamples of
event returns).

## Outputs

- `results/per_event.csv` — one row per (event, K): timestamps,
  impulse size in ATR units, direction, trade outcome per arm.
- `results/arms_is.json`, `results/arms_validation.json`.
- `REPORT.md` with verdicts and the S1 hand-off note.
