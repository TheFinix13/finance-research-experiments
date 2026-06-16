# E005 — Report: cross-pair frozen replication and sealed look

**Date executed:** 2026-06-10 (in `multi-pair-trading-agent`) ·
**Lab registration:** 2026-06-16 (retrospective) ·
**Status:** complete · two of three pairs cleared for deployment; sealed
2026 look inconclusive.

## Abstract

A rule that only works on the pair it was developed on is a curiosity,
not an edge. We took the `zone_d1_against / H4 / all sessions`
parameters from E004 and applied them with zero re-tuning to GBP/USD,
USD/CAD, AUD/USD, and NZD/USD. GBP/USD and USD/CAD replicated cleanly
(GBP/USD +10.24 pips per trade, $p=0.001$, positive in 11 of 11 years;
USD/CAD +4.63 pips per trade, $p=0.028$, positive in 10 of 11 years).
AUD/USD and NZD/USD did not clear the bar and were excluded. A
separate sealed 2026 EUR/USD look on 16 trades produced +7.75 pips per
trade with $p=0.29$: directionally consistent with the backtest but
under-powered.

## 1. Why this experiment exists

If the rule is structural FX behaviour, it should travel across major
pairs unchanged. If the rule is EUR/USD curve-fit, it should die on
other pairs. This experiment is the test that decides which it is.
A sealed-window look at 2026 EUR/USD trades is the second arm: an
out-of-sample window the rule has never been fitted on, used as a
last sanity check before deployment.

## 2. What we tested

- **H0:** the EUR/USD-trained rule has no edge on other major pairs.
- **H1:** the same frozen parameters produce positive expectancy on at
  least one additional pair.

For the sealed arm:

- **H0 (sealed):** the rule's expectancy on the 2025-12 onwards EUR/USD
  window is consistent with zero edge.
- **H1 (sealed):** the rule's expectancy on the sealed window is
  positive and consistent with the walk-forward expectation.

## 3. Method (short version)

- Frozen parameters: identical to E004's deployed cell
  (`htf_align = D1`, `htf_align_mode = against`, `htf_lookback = 10`,
  `htf_min_move_pips = 60`, `target_rr = 1.5`).
- Costs: realistic broker spreads scaled per pair (GBP/USD slightly
  wider, USD/CAD wider still, AUD/USD and NZD/USD widest).
- Outcome: per-trade expectancy, Sharpe ratio, $p$-value via bootstrap,
  count of positive calendar years.
- Pair-level deployment rule: clear for live trading if expectancy and
  Sharpe are positive, $p \leq 0.05$, and at least 10 of 11 years are
  positive.
- Sealed window: 2025-12-01 onwards EUR/USD, untouched by all earlier
  experiments.
- Runner: `scripts/run_cross_pair_frozen.py`.

## 4. Results

> **Headline:** GBP/USD and USD/CAD replicated; AUD/USD and NZD/USD were
> excluded. Two new pairs deployed at half risk. The sealed 2026 EUR/USD
> look returned +7.75 pips per trade on 16 trades ($p=0.29$),
> directionally right but under-powered.

### 4.1 Cross-pair frozen results

| Pair | Pips/trade | Sharpe | $p$ | Positive years | Deployment |
|---|---:|---:|---:|---:|---|
| GBP/USD | +10.24 | 2.42 | 0.001 | 11/11 | yes at 0.5x risk |
| USD/CAD | +4.63 | 1.16 | 0.028 | 10/11 | yes at 0.5x risk |
| AUD/USD | +3.45 | 1.15 | 0.032 | 8/11 | excluded |
| NZD/USD | +2.47 | 0.85 | 0.096 | 6/11 | excluded |

### 4.2 Sealed window (EUR/USD, 2025-12 onwards)

16 trades. +7.75 pips per trade. $p = 0.29$.

The point estimate is well inside the walk-forward range but the
standard error is large at this sample size. The next 30 to 60 live
trades will move the standard error from roughly $\pm 18$ pips per
trade to $\pm 9$, which is the resolution needed to call the sealed
look one way or the other.

## 5. What this tells us

1. **The rule is structural FX behaviour, not EUR/USD curve-fit.**
   Replicating on GBP/USD with $p = 0.001$ on 11 of 11 years, with
   zero re-tuning, is the cleanest possible evidence for that.
2. **Not every major pair carries the edge.** AUD/USD and NZD/USD
   failed at the same bar. The deployment policy is to require a
   pair-level pass, not to extrapolate.
3. **The sealed 2026 look is directionally right, statistically
   inconclusive.** That is the honest reading at $n = 16$. It does
   not change the deployment decision; it does change the monitoring
   plan.

## 6. Honest limitations

- All replications use the same fixed 1.5 take-profit. A pair-by-pair
  optimal multiple may exist; we have not tested it.
- The deployed cells trade at half risk (0.5x) until live results
  catch up to the backtest expectation. This is a deployment policy
  layered on top of the experiment, not a result.
- The sealed window covers a single calendar slice in a particular
  macro regime (early 2026). A regime change could move the sealed
  number meaningfully in either direction.

## 7. Conclusion

E005 is complete. GBP/USD and USD/CAD join EUR/USD on the live
deployment router. AUD/USD and NZD/USD are excluded. The sealed
2026 EUR/USD look is logged as monitoring evidence, not as a verdict.

## 8. References

- Runner: `multi-pair-trading-agent/scripts/run_cross_pair_frozen.py`.
- Evidence snapshots:
  `multi-pair-trading-agent/docs/reviews/2026-06-10_cross_pair_frozen.md`,
  `multi-pair-trading-agent/docs/reviews/2026-06-10_similar_pairs_frozen.md`.
- Lab copies: `results/2026-06-10_cross_pair_frozen.md`,
  `results/2026-06-10_similar_pairs_frozen.md` (this folder).
- Manifest: `MANIFEST.md`.
- Live router: `multi-pair-trading-agent/agent/alphas/zone_routing.py`.
