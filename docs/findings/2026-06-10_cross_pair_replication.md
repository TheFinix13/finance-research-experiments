# Finding: E005 cross-pair frozen replication

**Date:** 2026-06-10 (executed in `multi-pair-trading-agent`) ·
**Registered:** 2026-06-16 (retrospective) ·
**Status:** load-bearing — multi-pair deployment evidence

## Headline

The E004 frozen cell replicated on **GBP/USD** and **USD/CAD** with zero
re-tuning. **AUD/USD** and **NZD/USD** failed the pre-declared deployment
bar and were excluded.

| Pair | Pips/trade | Sharpe | p | Positive years | Live |
|---|---:|---:|---:|---:|---|
| GBP/USD | +10.24 | 2.42 | 0.001 | 11/11 | yes @ 0.5× risk |
| USD/CAD | +4.63 | 1.16 | 0.028 | 10/11 | yes @ 0.5× risk |
| AUD/USD | +3.45 | 1.15 | 0.032 | 8/11 | excluded |
| NZD/USD | +2.47 | 0.85 | 0.096 | 6/11 | excluded |

## Sealed 2026 EUR/USD (monitoring only)

16 trades, **+7.75 pips/trade**, p = 0.29. Directionally consistent
with walk-forward; **statistically inconclusive** at this n. Frame as
monitoring evidence, not confirmation.

## Why this matters

1. **Structural FX argument:** edge travels across majors when parameters
   are frozen — not EUR/USD curve-fit alone.
2. **A7 Barou rationale:** USDCAD shows weaker `zone_d1_against` edge
   (+4.63 vs +11.34 EUR); side-note that baseline `zone` (no D1 gate) is
   *stronger* on USDCAD — the asymmetry Barou exploits.
3. **Production pairs:** live router ships EURUSD, GBPUSD, USDCAD at
   locked params from this experiment.

## Caveat

Cross-pair arm is true OOS (no fit on non-EUR pairs). Retrospective
registration on the experiment doc. Sealed window is under-powered.

## Canonical sources

- Experiment folder: [`experiments/E005_cross_pair_sealed/`](../../experiments/E005_cross_pair_sealed/)
- Full report: [`experiments/E005_cross_pair_sealed/REPORT.md`](../../experiments/E005_cross_pair_sealed/REPORT.md)
