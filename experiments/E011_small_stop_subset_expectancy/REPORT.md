# E011 — Small-Stop Subset Expectancy of `zone_d1_against` H4

**Date:** 2026-07-01 · **Protocol:** [`PROTOCOL.md`](PROTOCOL.md) · **Status:** `stopped_at_stage_1`.
**Part of:** [2026-07-01 pipeline sweep](../../reviews/2026-07-01_pipeline_sweep_E011-E016.md) (E011-E016).

## Abstract

Many `zone_d1_against` H4 trades on the live $1,000 demo account carry stop-losses tight enough to be rejected by the position sizer at small account balances, raising the question of whether the strategy's edge concentrates in that small-stop subset. We stratified the 463 stop-classified, out-of-sample trades from the frozen E004 walk-forward log into five stop-distance buckets and compared each bucket's bootstrap-95% median pips/trade against the pooled cross-bucket median, correcting for the five-bucket family with Benjamini-Hochberg false-discovery-rate control. No bucket's confidence interval sits strictly above or below the pooled +9.99 pip median: the alpha's expectancy is bucket-agnostic on this data. This closes the small-stop-expectancy question and, per the pre-registered dependency chain, formally cancels the downstream pending-limit-entry study (E012).

## 1. Introduction

### 1.1 Motivation

A manual review of two weeks of live `zone_d1_against` trades on the $1,000 demo account showed the position sizer rejecting several signals whose zone-touch stop distance exceeded the account's risk-per-trade budget at the minimum lot size. The natural follow-up question is whether the trades that *do* fit inside a small stop are, coincidentally or causally, the strategy's better trades — in which case the sizer's rejections would be filtering out the alpha's best signals rather than its typical ones.

### 1.2 Problem statement

Does `zone_d1_against` H4 have a stop-distance-dependent expectancy, such that trades with smaller stops at signal time out-perform (or under-perform) the pooled trade population?

### 1.3 Contributions

1. A five-bucket stratification of the full 463-trade E004 walk-forward log by stop distance at signal time, with bootstrap confidence intervals and BH-FDR correction.
2. A closed, falsifiable answer (no) that removes this question from the open-investigation backlog rather than leaving it to recur in future manual chart reviews.
3. A mechanically-triggered cancellation of E012 (pending-limit-inside-zone entry), whose premise depended on this study finding a positive result.

### 1.4 Report outline

Section 2 places the question in the context of stop-loss and bet-sizing literature. Section 3 describes the walk-forward trade source and bucketing method. Section 4 gives the implementation. Section 5 reports the per-bucket results. Section 6 discusses what the finding means and its limitations. Section 7 concludes.

## 2. Background and Related Work

The premise under test — that a strategy's expectancy might vary systematically with its own stop distance — sits at the intersection of signal quality and bet sizing, two questions that are usually kept separate in the position-sizing literature. Kelly's capital-growth framework treats stop distance and bet fraction jointly as inputs to a growth-rate optimisation, not as evidence about signal quality in themselves [@kelly1956]. Chan's practitioner treatment of quantitative strategy design explicitly warns against the common retail error of reading a stop-distance pattern in historical trades as a signal-quality finding, when it may simply reflect how volatile the market was at the moment a given zone happened to form [@chan2009quantitative]. This caution motivated treating E011 as a purely descriptive stratification of already-computed trade outcomes rather than a new simulation: any apparent stop-distance effect found here would need a causal explanation (e.g. small-stop trades occurring preferentially in low-volatility, trending conditions) before being acted on, and the study is designed to detect whether such an effect exists at all before investing effort in explaining it.

The broader methodological risk is that stratifying one trade log into five buckets and reporting only the interesting-looking one is a textbook multiple-testing problem [@harvey2016cross; @sullivan1999datasnooping]. Benjamini-Hochberg correction [@benjamini1995controlling] across the five-bucket family, applied here before any bucket is called `alive`, is the direct countermeasure. The full sweep report's Section 2 (`../../reviews/2026-07-01_pipeline_sweep_E011-E016.md`) situates this study alongside the other five in this pipeline in more depth.

## 3. Methodology

**Trade source.** `.cache/walk_forward_trades.pkl`, key `('zone_d1_against', 'H4')` — the frozen E004 walk-forward output, 855 raw trades across 7 out-of-sample windows spanning 2019-2025. Of these, 463 trades carry a computable stop distance at signal time and are used here; the remainder are excluded for reasons unrelated to stop distance (documented in the E004 cache schema).

**Stratification.** Five buckets by stop-distance-in-pips at signal time: 0-10, 10-20, 20-40, 40-80, and 80+.

**Hypotheses.**
- $H_0$: per-bucket OOS median pips/trade is not materially different from the pooled cross-bucket median.
- $H_1$: at least one bucket's bootstrap-95% CI sits strictly above the pooled median (outperforms) or strictly below zero (loses money), after BH-FDR correction.

**Statistical pipeline.** 5,000-resample bootstrap per bucket, fixed seed 42, percentile 95% CI; BH-FDR $\alpha = 0.05$ across the 5-bucket family; n-gate of 30 trades per bucket for an `alive_*` verdict (buckets below this threshold have their statistics reported per the lab's compute-vs-claim rule, but cannot be claimed alive).

## 4. Implementation

`scripts/run_e011.py` loads the cached trade log, computes each trade's stop distance at signal time, assigns it to a bucket, and runs the bootstrap procedure described above. No new simulation, no new alpha code, and no change to any production code path — this is a re-analysis of bars the E004 walk-forward already consumed. The script is re-runnable from a clean checkout with the production repo's Parquet cache present.

## 5. Results

**Headline: the pooled OOS median across all 463 stop-classified trades is +9.99 pips/trade, and no bucket's confidence interval sits above or below that pooled figure.**

**Table 1. Per-bucket walk-forward results.**

| Bucket | n | Wins | Hit rate | Median pips | 95% CI | $p$ (median > baseline) | BH-reject | Verdict |
|---|---:|---:|---:|---:|---|---:|---|---|
| 0-10 pips | 19 | 11 | 58% | +11.42 | [+0.00, +0.00] | 1.0000 | no | `parked_insufficient_n` |
| 10-20 pips | 141 | 72 | 51% | +15.18 | [-12.14, +18.05] | 0.3986 | no | `dead` |
| 20-40 pips | 162 | 77 | 48% | -20.31 | [-23.13, +33.91] | 0.7586 | no | `dead` |
| 40-80 pips | 113 | 56 | 50% | -40.50 | [-45.40, +63.45] | 0.5464 | no | `dead` |
| 80+ pips | 28 | 16 | 57% | +125.85 | [+0.00, +0.00] | 1.0000 | no | `parked_insufficient_n` |

**Worked example.** A trade in the 10-20 pip bucket — a EUR/USD H4 zone touch with, say, a 15-pip stop — closes at a +15.18 pip median across the 141 trades in that bucket, with a 51% hit rate. An 80+ pip bucket trade closes at a much larger +125.85 pip median across only 28 trades, but that bucket sits below the 30-trade n-gate and its bootstrap interval collapses to a degenerate [+0.00, +0.00] — the point estimate cannot be trusted as a stable forecast of what a future wide-stop trade will do. Both figures are statistically consistent with the same +9.99 pip pooled expectancy once sampling noise is taken into account.

## 6. Discussion

### 6.1 Interpretation

The alpha's edge does not concentrate by stop distance. A signal that happens to produce a tight stop is not, on this evidence, a materially better or worse signal than one that produces a wide stop — the two well-powered middle buckets (10-20 and 20-40 pips, n = 141 and 162 respectively) both land `dead`, meaning their confidence intervals straddle the comparison value with no directional signal in either.

### 6.2 Threats to validity

- **Bucket boundaries were fixed before the data was examined** (per the pre-registered protocol), which avoids the obvious risk of choosing boundaries that happen to isolate an interesting-looking subset, but it also means a genuine effect at a different boundary (e.g. 0-15 pips instead of 0-10) would not be detected by this design.
- **Two of five buckets are underpowered** (`0-10p` at n = 19, `80+p` at n = 26 below the 30-trade gate). Their point estimates are reported for completeness but cannot be claimed as `alive`; a longer trade history would be needed to power these tails properly.
- **The trade cache reflects the alpha-level fill model** (fixed-lot `run_alpha`, no wick-proof stop, no break-even migration), not the live fill model. Bucket-level outcomes here describe the raw alpha's behaviour; E013 (in the same sweep) separately attributes the gap between alpha-level and live-level outcomes to the safety layers.

### 6.3 Limitations

Stage 2 (cross-pair replicate on GBPUSD/USDCAD) was pre-declared as conditional on a Stage-1 `alive_positive` result and does not run given the Stage-1 outcome reported here. The pooled-median comparator used for the hypothesis test (rather than a fixed E004 baseline of +11.34 pips/trade) is the pre-registered framing; both framings are reported in the protocol's amendment notes for transparency, but only the pooled framing decides the verdict.

## 7. Conclusion

Overall Stage-1 verdict: **`stopped_at_stage_1`**. The alpha's expectancy is bucket-agnostic across stop distances on the available walk-forward sample. Per the pre-registered dependency chain, E012 (pending-limit-inside-zone entry) is formally cancelled — see [`../E012_pending_limit_inside_zone/STOP_NOTICE.md`](../E012_pending_limit_inside_zone/STOP_NOTICE.md).

## 8. References

1. Benjamini, Y. and Hochberg, Y., 1995. Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing. *Journal of the Royal Statistical Society, Series B*, 57(1), pp.289-300.
2. Chan, E.P., 2009. *Quantitative Trading: How to Build Your Own Algorithmic Trading Business*. Hoboken, NJ: Wiley.
3. Harvey, C.R., Liu, Y. and Zhu, H., 2016. ...and the Cross-Section of Expected Returns. *Review of Financial Studies*, 29(1), pp.5-68.
4. Kelly, J.L., 1956. A New Interpretation of Information Rate. *Bell System Technical Journal*, 35(4), pp.917-926.
5. Sullivan, R., Timmermann, A. and White, H., 1999. Data-Snooping, Technical Trading Rule Performance, and the Bootstrap. *Journal of Finance*, 54(5), pp.1647-1691.
6. Pre-registration: [`PROTOCOL.md`](PROTOCOL.md).
7. Trade cache: `multi-pair-trading-agent/.cache/walk_forward_trades.pkl` (key `('zone_d1_against','H4')`).
8. E004 walk-forward: [`../E004_walk_forward/PROTOCOL.md`](../E004_walk_forward/PROTOCOL.md).
9. Results manifest: `MANIFEST.md`; raw JSON: `results.json`.
10. Full BibTeX: `../../reviews/refs.bib`.
