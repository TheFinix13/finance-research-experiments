# E006 — Report: do classical price-action events carry directional information? (Test A)

**Date:** 2026-06-12 ·
**Protocol:** `PROTOCOL.md` v2 (pre-registered 2026-06-12) plus amendment v2.1 ·
**Code:** `conflab/` at this repo state ·
**Status:** complete through Stage 2. Tests B (indicators, E008) and C
(cross-family interactions, E009) are scheduled, not yet pre-registered.

## Abstract

Discretionary traders say price-action confluence (zones, trendlines,
liquidity sweeps, fibonacci tags, and so on) produces stronger reactions
than random levels. We pre-registered a screen of seventy-six classical
price-action events on EUR/USD across four timeframes (284 cells) on
2015 to 2021 data, with frozen-parameter replication on 2022 to 2024
EUR/USD and on GBP/USD. The first run with uniform-time controls
returned forty-one survivors, including pairs of events that
contradicted each other; a diagnostic traced this to a session-volatility
confound on M15 (random forward movement varies by a factor of 3.7 across
the hour-of-day cycle). After a documented amendment to hour-matched
controls, five cells survived screening, all on M15. One confirmed on
the frozen EUR/USD window (`trendline_liquidity_sweep_low`,
$+0.30$ ATR); one replicated on GBP/USD (`channel_top_touch`). All five
survivors stayed positive on both out-of-sample tests. The effects are
small (+0.05 to +0.35 ATR of maximum favourable excursion, hit-rate
deltas under two percentage points). They are real enough to inform a
gate input in a separately validated trading agent, far too small to
trade on alone. The repository never trades.

## 1. Why this experiment exists

Online education sells "confluence" as the magic ingredient: when three
patterns align, the level matters. The empirical content of that claim
is a comparative one. A trendline touch that also lands at a 50\,\%
fibonacci on a higher-timeframe channel boundary should *behave
differently* from a random level sampled at the same time of day. If
the claim is true, the difference should survive multiple-hypothesis
correction and reproduce out of sample. Test A asks whether each
classical event, alone, carries directional information against a
matched random baseline. Tests B (indicators) and C (cross-family
interactions) build on whatever Test A leaves alive.

## 2. What we tested

- **H0**: conditional on a classical price-action event, ATR-normalised
  directional forward excursion is indistinguishable from
  direction-and-time-matched random baselines.
- **H1**: specific (timeframe by event-type) cells beat the matched
  baseline; specific cross-timeframe combinations beat their parts.

This is Test A of a three-family program (Test B: indicators; Test C:
cross-family interactions). Test A tests each method individually by
timeframe (the "one by one" design) before any combination claim is
made.

## 3. Method (short version)

This section locks the recipe. The full pre-registered protocol is in
`PROTOCOL.md`.

- Data: EUR/USD and GBP/USD, Dukascopy minute data resampled to D1, H4,
  H1, and M15. EUR/USD screen-window bar counts: D1 2,190, H4 11,272,
  H1 43,635, M15 174,461.
- Splits: screen 2015-01-01 to 2021-12-31 for all selection. Confirm
  2022-01-01 to 2024-12-31, frozen, for tests of survivors only.
  Sealed 2025-01-01 onwards, untouched. GBP/USD same protocol as
  frozen cross-pair arm.
- Event dictionary (Stage 0): 18 detector modules emit 76 event types.
  Each event carries a pre-registered directional hypothesis (touch
  bounces, break continues, sweep reverses, magnet draws). All
  detectors are causal. The dictionary was frozen before any Stage-1
  statistic was computed; 51 unit tests pin the detector contracts.
- Outcome metric: maximum favourable excursion (MFE) in the event's
  hypothesised direction over the next $H$ bars (D1 30, H4 20, H1 20,
  M15 16), divided by the average true range (ATR) of the last 14
  bars at the event bar. Also recorded: a binary hit (reaches +1 ATR
  before $-$1 ATR).
- Controls: a number of randomly placed bars per event, with direction
  resampled from the event cell's direction mix. After amendment v2.1
  (see Section 4 below), controls are also matched to the event's
  hour of day.
- Statistics: 2,000-shuffle permutation test on the difference in mean
  MFE; one-sided in the hypothesised direction. Benjamini-Hochberg
  false-discovery-rate correction at 5\,\% across cells with $n \geq
  100$. Four-tier verdicts: `alive`, `parked_weak_effect`,
  `parked_insufficient_n`, `dead`.

No costs are modelled. MFE measures information about future price,
not net profit.

### 3.1 Worked example: one trendline-liquidity-sweep-low event

On a fifteen-minute M15 bar at 14:45 UTC on a 2019 EUR/USD chart, the
detector observed three things in sequence: an ascending swing-low
trendline drawn from the last three confirmed swing lows; price wicked
below that trendline on the current bar; the bar then closed *above*
the trendline. The detector tagged the event with direction $+1$
(upward) and recorded the ATR(14) at that bar (about 4 pips on M15).
Over the next 16 M15 bars (four hours), the maximum favourable
excursion in the up direction was 6.2 pips, or 1.55 ATR. The matched
control (a randomly chosen bar with the same hour-of-day and the same
direction) over its own next 16 bars reached 1.18 ATR. This event's
contribution to the cell's mean difference is therefore
$1.55 - 1.18 = +0.37$ ATR. The cell aggregates 1,133 such events; the
mean difference is $+0.303$ ATR with permutation $p = 0.0005$.

## 4. Results

This section reports the numbers stage by stage.

### 4.1 Stage 1 on EUR/USD screen with hour-matched controls

> **Headline:** five of 284 cells survived Benjamini-Hochberg at 5\,\%.
> All five are M15 cells: one trendline-liquidity sweep, one channel
> touch, three fibonacci tags.

| cell | $n$ | event MFE | control MFE | effect | $p$ |
|---|---:|---:|---:|---:|---:|
| M15 `channel_top_touch` | 19,793 | 2.503 | 2.428 | +0.075 | 0.0005 |
| M15 `fib_50_tag` | 5,134 | 2.588 | 2.436 | +0.152 | 0.0005 |
| M15 `trendline_liquidity_sweep_low` | 1,133 | 2.821 | 2.518 | +0.303 | 0.0005 |
| M15 `fib_618_tag` | 4,676 | 2.604 | 2.480 | +0.124 | 0.0010 |
| M15 `fib_ext_1272_tag` | 2,482 | 2.759 | 2.570 | +0.189 | 0.0010 |

![Stage-1 summary](output/stage1_summary.png)

Two patterns are worth naming. First, D1 contributes nothing testable
at the $n \geq 100$ gate within seven years; most D1 cells are parked
for insufficient sample size, several with large point effects (D1
`entered_premium` was $+0.60$ on $n=55$, for instance). Second, H4 and
H1 are adequately powered and almost uniformly dead. Candlestick
families are dead everywhere they are powered. The 16 parked-weak
cells concentrate in M15 and H1 trendline-and-level geometry: the same
neighbourhood as the survivors.

### 4.2 Confirm split (EUR/USD 2022 to 2024, frozen, FDR within the 5)

| cell | $n$ | effect | $p$ | verdict |
|---|---:|---:|---:|---|
| `trendline_liquidity_sweep_low` | 508 | **+0.308** | 0.0065 | **CONFIRMED** |
| `channel_top_touch` | 8,288 | +0.063 | 0.0295 | not confirmed (borderline) |
| `fib_ext_1272_tag` | 1,042 | +0.096 | 0.149 | not confirmed |
| `fib_618_tag` | 1,939 | +0.068 | 0.145 | not confirmed |
| `fib_50_tag` | 2,108 | +0.051 | 0.213 | not confirmed |

The `trendline_liquidity_sweep_low` effect is essentially unchanged
between splits (+0.303 in, +0.308 out). That is the signature of a
stable effect rather than a lucky screen. The fibonacci-tag effects
shrink by roughly half out of sample: classic winner's-curse
attenuation.

### 4.3 Cross-pair replication (GBP/USD 2015 to 2021, frozen, FDR within the 5)

| cell | $n$ | effect | $p$ | verdict |
|---|---:|---:|---:|---|
| `channel_top_touch` | 19,161 | **+0.099** | 0.0005 | **REPLICATED** |
| `fib_50_tag` | 4,934 | +0.076 | 0.036 | not replicated |
| `fib_618_tag` | 4,527 | +0.080 | 0.037 | not replicated |
| `trendline_liquidity_sweep_low` | 1,152 | +0.150 | 0.055 | not replicated |
| `fib_ext_1272_tag` | 2,414 | +0.102 | 0.062 | not replicated |

All five effects are positive again. Five out of five sign-consistency
on two independent out-of-sample tests has probability roughly 3\,\%
each under a random-sign null. Three of the four "failures" sit just
above the corrected threshold. The honest summary is a weak but
directionally consistent family-level effect, with two members
individually validated on one axis each:
`trendline_liquidity_sweep_low` in time, `channel_top_touch` across
pairs.

### 4.4 Stage 2 conditional pairs

The strict pre-registered Stage 2 was empty by construction. All five
alive cells are M15, so there is no surviving higher-timeframe cell
to use as context.

The exploratory Stage 2 (including parked-weak cells, labelled as such)
ran 65 H1-context-by-M15-setup pairs. 51 of them were nominally alive
on the displacement null with lifts of +0.03 to +0.49 ATR. Decomposing
the joint MFE into the setup's marginal MFE plus a selection term
showed that most of the lift was the setup's own within-window timing
skill, not a context interaction: the selection term (joint minus
marginal) was negative or near zero for most pairs. One consistent
positive emerged: H1 `equal_highs_pool` as context improved every
setup placed under it (selection +0.10 to +0.46 ATR). Liquidity
resting above equal highs appears to genuinely amplify M15 setups
below it. This is a hypothesis for a future pre-registered Stage-2b,
not a claim.

### 4.5 The cautionary record (uniform-control run)

The uniform-control run is preserved at
`output/stage1_EURUSD_screen_2026-06-12_1334.jsonl`. It would have
reported 41 discoveries: channel tops and channel bottoms, both Asia
sweep directions, every fibonacci level, three-soldiers and
three-crows. Each would have been false. The cost of catching this
was one diagnostic script; the cost of missing it would have been a
trading agent gated on session-time artefacts.

## 5. What this tells us

1. **The discretionary "confluence works" claim is partially
   supported on M15 trendline, channel, and fibonacci geometry, not
   broadly across the full price-action vocabulary.** Five out of 284
   cells survive at 5\,\% false discovery rate. That is consistent
   with a small handful of real signals living inside a much larger
   pool of folklore.
2. **The two validated cells point at the same neighbourhood.** Both
   `trendline_liquidity_sweep_low` and `channel_top_touch` are
   reaction-to-geometry events. The other three survivors are also
   geometric (fibonacci tags). Candlestick survivors: zero.
3. **The session-volatility confound is a general lesson, not a
   local one.** Intraday ATR-normalised metrics on M15 need
   hour-matched controls. Uniform-time controls quietly impose a
   false null and can return forty-plus survivors out of nothing.
4. **Effect sizes are small.** +0.05 to +0.35 ATR of average
   favourable excursion, hit-rate deltas under two percentage points.
   These are gate inputs, not strategies. EUR/USD M15 spread in
   active hours is roughly 0.1 to 0.2 ATR(M15); the smallest
   surviving effect sits inside the cost band.

## 6. Honest limitations

- Each detector is one auditable operational definition. A dead
  verdict closes that definition, not the underlying folk concept.
- Daily-timeframe cells are structurally underpowered at $n \geq 100$
  on seven years. Several parked D1 cells have large point effects
  and wait for a pre-registered re-look as data accumulates. A
  cross-pair panel design is probably the right route to D1 claims.
- Hour-matching removes the session cycle but not all conditional
  heteroskedasticity (news days, central-bank meetings). A regime-
  matched control is a candidate v2.2 amendment.
- MFE is one-sided. It measures opportunity, not net outcome. The
  hit-rate metric partially compensates; a full maximum-adverse and
  maximum-favourable joint analysis belongs to a Stage 3.
- The screen-split data was used twice in a soft sense (once with
  uniform controls, once with hour-matched controls). The amendment
  was specified from the diagnostic, not from confirm-window data,
  and the confirm and sealed windows were never used in the
  diagnostic. The amended screen $p$-values are conditional on one
  analysis revision and we say so.

## 7. Conclusion

E006 closes with two validated cells
(`trendline_liquidity_sweep_low` confirmed on the EUR/USD frozen
window; `channel_top_touch` replicated on GBP/USD), three
attenuated-but-positive cells, an exploratory hypothesis
(`equal_highs_pool` as H1 context), and one important methodological
discovery (intraday hour-matched controls). Effects are too small to
trade on standalone. Any use in the live trading agent must pass that
agent's separate grid, holdout, and walk-forward pipeline with
realistic costs. Next pre-registrations, in order of value: a
Stage-2b with a setup-alone contrast for the `equal_highs_pool`
context; Test B (E008, indicators); a D1-power redesign using
cross-pair panels.

## 8. References and reproducibility

Pre-registration and protocol: `PROTOCOL.md` (this folder).

Run pipeline:

```bash
export PYTHONPATH=/path/to/multi-pair-trading-agent:.

python -m pytest tests/
python scripts/run_stage1.py --symbol EURUSD --final --tag screen_hourmatched
python scripts/run_stage1.py --symbol EURUSD --final \
    --start 2022-01-01 --end 2024-12-31 --tag confirm
python scripts/run_stage1.py --symbol GBPUSD --final --tag screen_replication
python scripts/run_stage2.py --registry output/stage1_EURUSD_screen_hourmatched_*.jsonl
python scripts/diagnose_m15_controls.py
python scripts/render_registry_figure.py --registry ... --out output/stage1_summary.png
```

All randomness is seeded (Stage 1 seed 42, Stage 2 seed 42,
diagnostic seed 7). Registries are append-only JSONL in `output/`.
The permutation floor is $p \geq 1/2001$ on Stage 1.

| Artefact | File |
|---|---|
| Stage 1 screen, hour-matched (canonical) | `output/stage1_EURUSD_screen_hourmatched_2026-06-12_1340.jsonl` |
| Stage 1 screen, uniform (cautionary) | `output/stage1_EURUSD_screen_2026-06-12_1334.jsonl` |
| Confirm split | `output/stage1_EURUSD_confirm_2026-06-12_1342.jsonl` |
| GBP/USD replication | `output/stage1_GBPUSD_screen_replication_2026-06-12_1345.jsonl` |
| Stage 2 strict | empty family by construction (no higher-TF survivor) |
| Stage 2 exploratory | `output/stage2_EURUSD_2026-06-12_1348.jsonl` |
| Summary figure | `output/stage1_summary.png` |

Related experiments: E007 (impulse-origin bounce). Planned: E008
(indicators), E009 (cross-family interactions), E010 (Stage-2b
`equal_highs_pool` context). Manifest: `MANIFEST.md`.
