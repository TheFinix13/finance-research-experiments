# E018 — STOP NOTICE

**Verdict: `dead`. Study stopped at Stage-1. No live code changed.**
**Date:** 2026-07-14 · **Registry:** `PROTOCOL_DISCIPLINE.md` §4 → `dead`.

## What was tested

Whether standing aside on the **R2 (trend-extension/breakout)** regime improves
the out-of-sample performance of the deployed `zone_d1_against` fade, using a
**causal, frozen, prior-derived** regime labeller (Chigiri Φ4.1 breakout
constants + deployed D1-bias params + F18 ADX convention). Pre-registered in
`PROTOCOL.md` (frozen 2026-07-14, before any labelling).

## Why it stopped (gate not met)

The pre-registered gate (§5) requires R2-labelled fades to show **significantly
negative** OOS expectancy (BH-FDR q ≤ 0.05, n ≥ 30, robust across pairs). Over
walk-forward pooled OOS 2019–2025 (EURUSD/GBPUSD/USDCAD H4):

| Pair | R2 n | R2 OOS exp (pips) | q (BH, one-sided "less") | significantly negative? |
|---|---|---|---|---|
| EURUSD | 35 | **+0.19** | 0.70 | No |
| GBPUSD | 37 | **+16.20** | 0.98 | No (positive) |
| USDCAD | 28† | **+2.53** | 0.70 | No |

† underpowered (< 30). **R2 is negative-significant on 0 of 3 pairs.**

R2 is not the fade's losing mirror of R1. The R1 (pullback) cells are all
strongly positive and BH-significant (EURUSD +17.13, GBPUSD +19.56,
USDCAD +18.18; all q = 0.001), but R2 is break-even to positive — not a
regime worth refusing to trade. The marginal pooled "improvement" from dropping
R2 (+0.88 pips, +0.11 Sharpe) sits inside overlapping bootstrap CIs and is a
noise-level artefact of removing ~break-even trades, explicitly ruled out by the
gate's significance requirement.

The 2026-07 incident that motivated the study is a **descriptive n=1 case**; the
frozen definition shows its pattern does **not** generalise. Reverse-engineering
a threshold to flip those specific losers would invalidate the study (§6
discipline guards), so it was not done.

## Consequences (explicit)

- **NO change to `multi-pair-trading-agent`.** `agent/alphas/concepts/zone_alpha.py`,
  `_htf.py`, and `zone_routing.py` are **untouched**. The fade continues to trade
  all D1-biased zone touches (R1 and R2 alike), as before.
- The E018 harness + frozen labeller remain in `programs/E018/` for reuse; the
  per-trade ledger records the strict-breakout ratios for any **future,
  separately pre-registered** re-examination (e.g. a hit-rate/median-based filter
  or a different breakout definition — which must open a fresh FDR family, not
  reuse this one).

## Artefacts

`PROTOCOL.md`, `REPORT.md`, `results.json`, `MANIFEST.md`;
`programs/E018/regime_labeller.py`, `programs/E018/run_e018_validation.py`,
`programs/E018/tests/test_regime_labeller.py` (10/10 pass),
`programs/E018/data/labelled_ledger.json`.
