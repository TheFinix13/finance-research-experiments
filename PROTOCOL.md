# Protocol v2 — role-structured cross-timeframe study (pre-registered)

Status: PRE-REGISTERED 2026-06-12, before any v2 code or results exist.
Supersedes a pooled band-density pilot (v1, code removed after the
study), whose result stands as recorded: H0 not rejected on EURUSD H4
(p = 0.23, no source survived FDR). v1 tested an omnibus, role-free
question; v2 tests the structured hypothesis it could not address.

## Hypothesis

Price interaction outcomes are conditional on a HIERARCHY of timeframe
roles, not on undifferentiated level stacking:

- **Context (D1):** where the move starts and its direction bias
  (demand/supply zone touch, S/R polarity flip retest, channel edge).
- **Setup (H4):** the structure that times participation (trendline bounce,
  ascending/descending channel, double bottom/top completion, fib
  retracement tag).
- **Target (H1/M15):** the destination (liquidity pool, prior swing,
  fib extension, daily level).

Claim under test: specific (context, setup, target) combinations yield
directional moves from context to target at rates unexplainable by the
marginal behaviour of their parts.

## Program structure (amended 2026-06-12 after design review)

Three independent test families, each with its own dictionary and FDR
family, run in order:

- **Test A — price action / classical methods** (this protocol's Stages
  0–3): the full dictionary below.
- **Test B — technical indicators only** (EMA/Bollinger/RSI/MACD/etc.
  derived events): separate pre-registration before it runs.
- **Test C — cross-family interactions** (A survivors+parked × B
  survivors+parked): separate pre-registration; the largest study, last.

**Compute-vs-claim principle:** effect size, CI and p are COMPUTED AND
RECORDED for every cell at every stage regardless of sample size — nothing
is invisible. The staged funnel governs CLAIMS (what advances), not what
is measured. Compute plan: local CPU (numpy/pandas permutation work is not
GPU-shaped; v1 ran in 20s; full Stage 1 is minutes, Test C overnight at
worst, parallelised across cells). No Colab/GPU.

**Verdict registry (permanent, append-only):** every cell carries one of:
- `alive` — positive effect, survived stage FDR → advances;
- `parked_weak_effect` — positive effect, raw p<0.05, failed FDR → held;
- `parked_insufficient_n` — below the n gate → held;
- `dead` — adequately powered, no effect → cut.
Parked cells are re-tested ONLY at pre-registered re-look milestones:
screen-split n doubled, or a new pair's data added. Each re-look is a
counted test in that round's FDR family (no silent peeking).

## Stages

### Stage 0 — event dictionary (no statistics)
Each detector emits directional EVENTS per timeframe:
`(index, time, type, direction, level)`; direction is the event's
pre-registered directional hypothesis (+1 up / −1 down; touch-type events
hypothesise the bounce, break-type events the continuation, magnet-type
the draw). Causality rule: an event at bar t uses bars ≤ t only (swings
count as confirmed `lookback` bars after their extreme).

**Test A dictionary** (FROZEN 2026-06-12 — build queue empty; ✅ = built):
1. Market structure: BOS bullish/bearish ✅, CHoCH bullish/bearish ✅,
   premium/discount equilibrium crossings ✅; range/consolidation expressed
   as rectangle-breakout events (family 7), the raw STATE tag is a Stage-2
   conditioner, not a Stage-1 cell.
2. Zones & blocks: supply/demand zone touch ✅ (lab-native impulse+base
   definition — deviation from the planned main-repo adapter, recorded so
   the lab stays self-contained and the definition auditable),
   order block touch ✅, breaker block retest ✅
3. Imbalance: FVG touch ✅, inversion FVG retest ✅
4. Liquidity: equal highs/lows pool (magnet) ✅, liquidity sweep high/low ✅,
   PDH/PDL touch ✅, PWH/PWL touch ✅, Asia-session sweeps (H1) ✅,
   trendline liquidity sweep ✅
5. Trendlines & channels: trendline touch/bounce ✅, trendline
   break+retest ✅, parallel-channel boundary touches ✅
6. Horizontal S/R: S/R flip retest ✅, n-touch level touch ✅,
   round-number touch (x.x000/x.x500) ✅
7. Chart patterns: double bottom/top completion ✅, triple top/bottom ✅,
   head & shoulders ± inverse ✅, ascending/descending/symmetrical
   triangles ✅, rising/falling wedges ✅, flags/pennants ✅,
   rectangle range break ✅
8. Fib: retracement tags (38.2/50/61.8/78.6) ✅, OTE zone ✅,
   extensions (127.2/161.8, exhaustion hypothesis) ✅
9. Candlesticks: bull/bear engulfing ✅, hammer ✅, shooting star ✅,
   bull/bear pin ✅, outside bar ✅, tweezers ✅, morning/evening star ✅,
   three soldiers/crows ✅. Inside bar EXCLUDED from Stage 1: it carries no
   directional hypothesis (recorded design decision; candidate Stage-2
   conditioner).
10. Session/time: Asia-range sweep events ✅ (family 4); killzone/open
    TAGS are Stage-2 conditioners, not Stage-1 cells (as pre-registered).

Stage-1 statistics are run ONCE over the complete dictionary when the
build queue is empty — no partial-family analysis, no peeking. The build
queue emptied 2026-06-12; the canonical run follows this freeze.

### Stage 1 — marginal screening, per (timeframe × event type)
- Question: conditional on event E, is directional forward excursion
  (MFE in event direction within horizon, ATR-normalised) and the
  +1·ATR-before-−1·ATR hit rate better than at direction-matched random
  baseline times?
- Method: permutation test vs matched random-time controls (5× events,
  directions bootstrapped from the event distribution, same outcome code);
  BH-FDR 5% across the whole Stage-1 family.
- Qualification gate for `alive`: ≥ 100 events in the screen split; below
  → `parked_insufficient_n` (stats still computed and recorded).
- Horizons (bars of own TF): D1 30, H4 20, H1 20, M15 16. Same-bar
  +1/−1 ambiguity resolves adverse-first (conservative).

### Stage 2 — conditional pairs (context × setup)
- Only Stage-1 survivors enter. Family is therefore small by construction.
- Question: does setup S inside an active context window C improve outcomes
  over C alone AND over S alone (lift, not mere co-occurrence)?
- Control: displace S timings uniformly within C windows (breaks alignment,
  preserves both marginals). Permutation p + BH-FDR within stage.
- Gate: ≥ 50 joint events in the screen split.

### Stage 3 — triplets with a trade-shaped endpoint
- Add target T. Outcome: P(price reaches T before the context invalidation
  level), against distance-matched random targets on the same trades.
- Survivors are CANDIDATE STRATEGY CELLS only. Promotion path: the main
  repo's own pipeline (grid → holdout → walk-forward, with costs), same as
  zone_d1_against. Nothing in this lab ever trades.

## Split discipline (fixed now)

- Screen: 2015-01-01 → 2021-12-31 (EURUSD).
- Confirm: 2022-01-01 → 2024-12-31, survivors only, parameters frozen.
- Sealed: 2025-01-01 onward — untouched until a final pre-registered look.
- Cross-pair: any Stage-3 survivor must replicate on GBPUSD (frozen) before
  being called real.

## Amendment v2.1 — hour-matched controls (2026-06-12, pre-specified
## before any re-run)

The pre-registered Stage-1 analysis (uniform random-time controls) was run
as written on the EURUSD screen split and produced a pathological omnibus
pattern: 41/284 cells `alive`, all M15, nearly all at the permutation
floor p, including mutually contradictory hypotheses (both channel edges,
both Asia sweep directions, every fib level). A pre-analysis diagnostic
(`scripts/diagnose_m15_controls.py`) confirmed the cause: ATR(14) lags the
intraday session-volatility cycle, so ATR-normalised forward MFE at RANDOM
times varies by hour-of-day from 1.09 ATR (19:00 UTC) to 4.03 ATR
(05:00 UTC). Event families cluster in specific hours; uniform controls do
not. The null was therefore not exchangeable with events.

Amendment (analysis layer only — no detector parameter changes):
controls are drawn DIRECTION-MATCHED AND HOUR-OF-DAY-MATCHED per event
(control i shares event i's directional hypothesis and its bar's hour).
The Stage-2 displacement null likewise redraws within-window positions
restricted to the event's hour where available. The uniform-control run is
retained and reported as the cautionary primary record; the hour-matched
re-run is the definitive Stage-1 screen. No result from the invalid run
carries any claim.

## Multiplicity & honesty rules

1. Every hypothesis evaluated at any stage counts toward that stage's FDR
   family — including ones we lose interest in.
2. "Insufficient data" is a recorded verdict distinct from pass/fail;
   parked combinations may be revisited only when new data accrues, not by
   loosening gates.
3. No parameter retuning after Stage 0. A "wouldn't it work better if…"
   idea is a NEW pre-registered protocol, not an edit to this one.
4. Negative results are reported with the same prominence as positive ones.

## Execution record (Test A)

Executed 2026-06-12. Full report: `REPORT.md`. Registries under
`output/`. Summary: 284 cells screened (EURUSD 2015-21, hour-matched
controls per amendment v2.1) → 5 alive (all M15) / 16 parked_weak / 77
parked_insufficient_n / 186 dead. Confirm split (2022-24, frozen):
`trendline_liquidity_sweep_low` confirmed. GBPUSD (frozen):
`channel_top_touch` replicated. Strict Stage 2: empty family (no
higher-TF survivor). Exploratory Stage 2: lift mostly explained by setup
marginals; H1 `equal_highs_pool` context flagged for a pre-registered
Stage-2b. Tests B and C: not yet pre-registered.
