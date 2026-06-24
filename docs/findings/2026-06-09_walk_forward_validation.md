# Finding: E004 walk-forward validation (deployed cell)

**Date:** 2026-06-09 (executed in `multi-pair-trading-agent`) ·
**Registered:** 2026-06-16 (retrospective) ·
**Status:** load-bearing — production deployment evidence

## Headline

`zone_d1_against / H4 / all sessions` on EUR/USD posted **positive
out-of-sample expectancy in 7 of 7 rolling windows**, median **+11.34
pips/trade**, ~66 trades per window. A coin-flip null puts 7/7 at
$p \approx 0.008$.

## Deployed configuration

| Parameter | Value |
|---|---|
| Concept | `zone_d1_against` |
| Timeframe | H4 |
| Session | all |
| HTF align | D1 |
| HTF mode | against |
| HTF lookback | 10 |
| HTF min move | 60 pips |
| Target R:R | 1.5 |

## Why this matters

1. **Strongest single evidence** in the E001→E005 agent validation chain.
2. **Corrected E003 selection bias:** the `H4/asia` survivor had the same
   per-trade edge on ~¼ the sample; deployment switched to `H4/all`.
3. **M001 baseline:** A1 Isagi v1 wraps this cell; C1 requires beating
   Sae (this configuration) by ≥ 10 % on TQS over sealed 2026 H1.

## Method (one paragraph)

Seven rolling 4-year in-sample / 1-year out-of-sample windows on
EUR/USD 2015–2025. Parameters locked before the sweep. Compared
`zone_d1_against / H4 / asia` vs `zone_d1_against / H4 / all`.
Runner: `multi-pair-trading-agent/scripts/run_walk_forward.py`.

## Caveat

Retrospective registration (`executed-then-registered`). Walk-forward
design is harder to overfit than single-split holdout, but the epistemic
weight is lower than a pre-registered lab experiment (E006/E007 standard).

## Canonical sources

- Experiment folder: [`experiments/E004_walk_forward/`](../../experiments/E004_walk_forward/)
- Full report: [`experiments/E004_walk_forward/REPORT.md`](../../experiments/E004_walk_forward/REPORT.md)
- Raw numbers: `experiments/E004_walk_forward/results/2026-06-09_walk_forward.md`
