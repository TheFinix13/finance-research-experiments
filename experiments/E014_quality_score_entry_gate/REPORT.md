# E014 — Zone Quality-Score Entry Gate for `zone_d1_against` H4

**Date:** 2026-07-01 · **Protocol:** [`PROTOCOL.md`](PROTOCOL.md) · **Status:** `stage_1_complete`.
**Part of:** [2026-07-01 pipeline sweep](../../reviews/2026-07-01_pipeline_sweep_E011-E016.md) (E011-E016).

## Abstract

The zone detector already computes a 0-100 quality score for every supply and demand zone, but the live `zone_d1_against` alpha ignores it at signal time. We tested three candidate thresholds ($\theta \in \{30, 50, 70\}$) as a hard entry gate, locking the highest in-sample-Sharpe threshold per walk-forward window before evaluating its out-of-sample fold, to avoid choosing the threshold with knowledge of the test data. The locked-per-window procedure selected $\theta = 70$ in six of seven windows, producing a pooled out-of-sample median of +26.09 pips/trade (95% bootstrap CI [+16.17, +33.99]) against a frozen +11.34 pip baseline — more than double the baseline, and the interval sits strictly above it. However, only 102 trades (11.9% of the 855-trade ungated baseline) survive the gate, below the pre-declared 25% trade-count floor. The verdict is `parked_low_yield`: a real effect, not yet validated at a production-usable trade frequency.

## 1. Introduction

### 1.1 Motivation

Zone quality is not a new concept invented for this study — the production zone detector (`agent/detectors/zones.py::compute_zone_quality`) already scores every detected zone on a 0-100 scale using structural features of the zone (approach displacement, base tightness, and related criteria). That score has never been wired into the live alpha's entry decision. If it predicts trade quality, gating entries on it is one of the cleanest, lowest-risk improvements available: it requires no new indicator, no new data source, and no change to the alpha's core signal logic, only a filter on signals already being generated.

### 1.2 Problem statement

Does gating `zone_d1_against` H4 entries on the zone's quality score at a fixed threshold $\theta$ improve out-of-sample risk-adjusted return relative to the ungated baseline, at a trade frequency usable in production?

### 1.3 Contributions

1. A locked, leak-free threshold-selection procedure (per-window in-sample Sharpe selects $\theta$, evaluated only on that window's held-out out-of-sample fold) applied to an entry-side signal filter for the first time on this alpha.
2. A precise, quantified answer to why the effect is not yet deployable — not "no effect", but "real effect, insufficient trade volume" — which specifies exactly what a follow-up study needs to change (Section 6.3).
3. The formal, mechanically-triggered cancellation of two downstream studies (E015, E016) whose premises depended on this study clearing a higher bar than it did.

### 1.4 Report outline

Section 2 reviews why hard-gating a technical signal on a secondary quality score is a well-motivated but data-hungry design choice. Section 3 specifies the threshold grid, locking procedure, and statistical pipeline. Section 4 describes the implementation. Section 5 reports the per-window locking results and the pooled outcome. Section 6 discusses the finding's interpretation, the mechanism behind the trade-count shortfall, and limitations. Section 7 concludes.

## 2. Background and Related Work

Filtering a base trading signal on a secondary quality or confidence score is a standard technique for improving a strategy's per-trade expectancy at the cost of trade frequency — the trade-off this study quantifies directly. Harvey, Liu and Zhu's survey of factor discovery is a useful cautionary reference here [@harvey2016cross]: their central finding is that most published return-predicting signals fail to survive proper multiple-testing correction, and a three-point threshold grid tested without correction would be exactly the kind of under-powered, over-flexible search their critique targets. This study's response is the locked-per-window design in Section 3.2, which fixes the threshold-selection rule (highest in-sample Sharpe) before any out-of-sample fold is touched, rather than choosing a threshold by looking at pooled out-of-sample performance across all three candidates. Sullivan, Timmermann and White's bootstrap-based reality-check methodology for technical trading rules [@sullivan1999datasnooping] is the broader statistical ancestor of the bootstrap confidence interval used here to test whether the pooled effect is distinguishable from the baseline once sampling noise is accounted for.

The specific trade-off this study surfaces — a real effect that is too data-hungry to deploy — is a common outcome in quality-filtering studies generally and is exactly the outcome the pre-declared trade-count floor (Section 3.3) exists to catch, rather than letting an attractive point estimate on a small sample pass as a production-ready result.

## 3. Methodology

### 3.1 Strategy and data

`zone_d1_against` H4, the same frozen alpha parameterisation used throughout this sweep. Base signal source: `QualifiedZone.quality.quality_score`, computed by the existing production zone detector and read but not modified for this study.

### 3.2 Threshold grid and locking procedure

Three candidate thresholds: $\theta \in \{30, 50, 70\}$. For each of the seven walk-forward windows, the threshold with the highest in-sample (IS) Sharpe ratio is locked before that window's out-of-sample (OOS) fold is evaluated. This prevents the threshold choice from using any information from the test fold it will subsequently be scored on.

### 3.3 Verdict criteria (locked before execution)

- `alive_positive` requires the pooled OOS bootstrap-95% CI lower bound to sit above the frozen baseline **and** the pooled trade count to be at least 25% of the ungated baseline (855 trades).
- `alive_equivalent_higher_hit_rate` requires equivalent median pips with a materially higher hit rate at the same 25% volume floor.
- `parked_low_yield` applies when the effect is real (CI above baseline) but the trade-count floor is not met.
- `dead` applies when the CI does not clear the baseline regardless of volume.

### 3.4 Statistical pipeline

5,000-resample bootstrap on the pooled OOS trade set, fixed seed 42, percentile 95% CI against the frozen E004 baseline of +11.34 pips/trade.

## 4. Implementation

`scripts/run_e014.py` runs the per-window IS/OOS threshold-locking loop described in Section 3.2 against the frozen `zone_d1_against` alpha and the existing `detect_qualified_zones` detector output (no detector code changes), pools the OOS trades across all seven windows under their respective locked thresholds, and computes the bootstrap comparison against the frozen baseline.

## 5. Results

### 5.1 Per-window locked-threshold table

**Table 1. In-sample Sharpe by candidate threshold, the locked threshold, and its out-of-sample outcome.**

| Window | IS Sharpe $\theta{=}30$ | IS Sharpe $\theta{=}50$ | IS Sharpe $\theta{=}70$ | Locked $\theta$ | OOS n | OOS median (pips) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | +1.565 | +1.522 | +2.191 | 70 | 7 | +24.82 |
| 2 | +1.968 | +1.989 | +2.467 | 70 | 9 | +33.99 |
| 3 | +2.288 | +2.389 | +2.158 | 50 | 33 | +19.17 |
| 4 | +2.431 | +2.410 | +3.036 | 70 | 23 | +53.91 |
| 5 | +1.645 | +1.842 | +4.247 | 70 | 10 | -22.47 |
| 6 | +0.805 | +0.926 | +2.557 | 70 | 6 | +6.32 |
| 7 | +0.728 | +0.764 | +2.611 | 70 | 14 | +48.67 |

### 5.2 Pooled out-of-sample outcome

**Table 2. Pooled OOS result vs baseline.**

| Statistic | Value |
|---|---:|
| Pooled OOS trades | 102 |
| Trade-count ratio vs 855-trade baseline | 11.9% |
| Hit rate | 62.7% |
| Median pips/trade | +26.09 |
| Bootstrap 95% CI | [+16.17, +33.99] |
| Frozen E004 baseline | +11.34 |

**Worked example.** Window 4 locks $\theta = 70$ from an in-sample Sharpe of +3.036 (the highest of the three candidates that window) and returns 23 out-of-sample trades at a +53.91 pip median — nearly five times the pooled baseline. Window 5 also locks $\theta = 70$, from the single highest in-sample Sharpe recorded anywhere in the study (+4.247), yet its out-of-sample fold returns a *negative* -22.47 pip median across 10 trades. The same threshold, selected by the same rule, produced the study's best and one of its worst out-of-sample outcomes — the direct anatomy of why the trade-count floor exists as a guardrail independent of the pooled median result.

## 6. Discussion

### 6.1 Interpretation

By its own locked statistic, the quality-score gate finds a real effect: the confidence interval [+16.17, +33.99] sits entirely above the +11.34 baseline. This is not a marginal or noisy result — the effect size is large (more than double the baseline median) and the interval is reasonably tight given the sample. The problem is not the effect's existence but its cost in trade frequency: at $\theta = 70$, roughly seven-eighths of the ungated signal population is discarded.

### 6.2 Why the trade-count floor, not the point estimate, decides the verdict

Table 1's window-5 example (highest in-sample Sharpe, worst out-of-sample median) demonstrates concretely why a real point estimate on a thin sample is not sufficient grounds to call this `alive_positive`. With as few as 6 trades surviving the gate in some windows, a single adverse or favourable window can swing the pooled statistic substantially. The pre-declared 25% trade-count floor exists precisely to prevent an attractive but under-powered result from being read as production-ready, independent of how statistically clean the confidence interval looks.

### 6.3 Threats to validity

1. **The threshold-locking procedure is IS-Sharpe-greedy per window**, which is a defensible walk-forward design but means the pooled result is an ensemble of seven independently-chosen thresholds rather than a single fixed-threshold backtest. This is disclosed rather than hidden, since it materially affects how the pooled statistic should be interpreted.
2. **The three-value grid ($\{30, 50, 70\}$) may not contain the volume-preserving threshold.** Section 6.4 below proposes exactly this as the next study.
3. **No cross-pair replication was run** — Stage 2 was pre-declared as conditional on a Stage-1 `alive_*` result, which was not reached.

### 6.4 What a follow-up study should change

The natural next step, motivated directly by this result rather than by general intuition, is a wider and lower threshold grid ($\theta \in \{20, 30, 40, 50\}$) to search for a value that preserves more of the pip uplift documented in Table 2 while clearing the 25% trade-count floor. This amendment is proposed in the sweep report's Section 7.2 (`../../reviews/2026-07-01_pipeline_sweep_E011-E016.md`).

## 7. Conclusion

**Verdict: `parked_low_yield`.** The trade-count ratio (11.9%) falls below the pre-declared 25% floor; the gate is too aggressive to generate a survivable trade frequency on a live account, even though the trades it does approve are demonstrably and significantly better than the pool. Per the pre-registered dependency chain, E015 (conviction-from-quality sizing) and E016 (re-entry/flip) are both formally cancelled — see their respective `STOP_NOTICE.md` files ([`../E015_conviction_from_quality/STOP_NOTICE.md`](../E015_conviction_from_quality/STOP_NOTICE.md), [`../E016_reentry_flip_on_tighter_stop/STOP_NOTICE.md`](../E016_reentry_flip_on_tighter_stop/STOP_NOTICE.md)).

## 8. References

1. Harvey, C.R., Liu, Y. and Zhu, H., 2016. ...and the Cross-Section of Expected Returns. *Review of Financial Studies*, 29(1), pp.5-68.
2. Sullivan, R., Timmermann, A. and White, H., 1999. Data-Snooping, Technical Trading Rule Performance, and the Bootstrap. *Journal of Finance*, 54(5), pp.1647-1691.
3. Pre-registration: [`PROTOCOL.md`](PROTOCOL.md).
4. Trade cache: computed inline; per-theta counts stored in `results.json`.
5. Related: `multi-pair-trading-agent/agent/detectors/zones.py::compute_zone_quality` (quality-score formula, frozen).
6. Full BibTeX: `../../reviews/refs.bib`.
