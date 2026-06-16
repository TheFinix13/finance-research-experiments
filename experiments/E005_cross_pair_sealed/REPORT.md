# E005 — Report: cross-pair frozen + sealed look

## Headline (cross-pair)

> **H4 zone-fade edge replicated on unseen pairs with zero re-tuning — strongest
> evidence the effect is structural FX behaviour, not EURUSD overfitting.**

## H4 frozen results (zone_d1_against)

| Pair | Exp/trade | Sharpe | p | Positive years | Deployment |
|---|---:|---:|---:|---:|---|
| GBPUSD | +10.24 | 2.42 | 0.001 | 11/11 | yes @ 0.5× risk |
| USDCAD | +4.63 | 1.16 | 0.028 | 10/11 | yes @ 0.5× risk |
| AUDUSD | +3.45 | 1.15 | 0.032 | 8/11 | **excluded** |
| NZDUSD | +2.47 | 0.85 | 0.096 | 6/11 | **excluded** |

## Sealed 2026 (EURUSD)

16 trades, +7.75/trade, p=0.29 — directionally consistent, statistically
inconclusive at this n (monitoring continues in agent live logs).

## Lab copies

- `results/2026-06-10_cross_pair_frozen.md`
- `results/2026-06-10_similar_pairs_frozen.md`

## Verdict

**Complete** for research registration. Agent router deploys EURUSD + GBPUSD +
USDCAD per this evidence.
