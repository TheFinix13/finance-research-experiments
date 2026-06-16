# E001 — Report: ICT concept ablation

**Date executed:** 2026-06-09 to 2026-06-10 (in `multi-pair-trading-agent`) ·
**Lab registration:** 2026-06-16 (retrospective) ·
**Status:** complete · sole survivor handed to E002.

## Abstract

Discretionary forex traders use a vocabulary of price-structure concepts
(zones, order blocks, fair-value gaps, market-structure breaks,
liquidity sweeps, fibonacci retracements) almost interchangeably, as
though all of them carry edge. We ran each concept through the same
ablation grid on EUR/USD 2015 to 2025 and required Benjamini-Hochberg
false-discovery-rate correction at 5\,\%. Six of the seven concepts
failed and were dropped. One concept, fading supply or demand zone
touches, survived; gating it against the daily trend
(`zone_d1_against`) sharpened the edge further. The deployed live
strategy descends directly from this funnel.

## 1. Why this experiment exists

A retail trader on a Discord channel will tell you that "FVG + order
block + fib OTE" is a winning combo. The original work in
`multi-pair-trading-agent` started from that intuition and tested seven of the
most-marketed Inner Circle Trader (ICT) concepts individually. The
question was simple: can any of them carry positive expectancy on
EUR/USD on a multi-year window, alone, after costs, with no manual
overrides? If a concept failed here, it failed before any composite
strategy could be built on top of it.

## 2. What we tested

- **H0:** each concept's expectancy distribution is indistinguishable
  from a permutation null (no edge after costs).
- **H1:** at least one concept produces positive expectancy that
  survives Benjamini-Hochberg correction at 5\,\% across the full
  timeframe-by-session grid.

The seven concepts tested were: fair-value gap retest (FVG),
market-structure break continuation (BOS), order blocks, fibonacci OTE,
momentum continuation, liquidity sweep reversal, and supply or demand
zone touch.

## 3. Method (short version)

- Data window: EUR/USD 2015-01-01 to 2025-11-30, Dukascopy minute data.
- Grid: timeframe in {D1, H4, H1, M15, M5} crossed with session in {all,
  London, NY, London-NY overlap, Asia}.
- Outcome: per-trade expectancy after a fixed 0.3-pip spread per side.
- Statistics: bootstrap $p$-value per cell, Benjamini-Hochberg
  false-discovery-rate correction at 5\,\% across all 25 cells per
  concept and across all concepts.
- Harness: `agent/alphas/grid.py` in the trading agent.
- A "fair-shot" second wave was applied to momentum and liquidity sweep
  with relaxed entry rules so each concept got the benefit of the doubt.

Full grid output and timestamps live in `multi-pair-trading-agent/docs/00-journey.md`,
sections 2 to 4. The lab does not duplicate those raw results.

## 4. Results

> **Headline:** six of seven concepts failed Benjamini-Hochberg at 5\,\%
> on every cell. The supply/demand zone concept produced multiple
> significant cells; gating against the daily trend (`zone_d1_against`)
> emerged as the most robust configuration.

### 4.1 Elimination table

| Concept | Outcome | Notes |
|---|---|---|
| Fair-value gap retest | eliminated | no Benjamini-Hochberg-significant cell on any timeframe |
| Market-structure break continuation | eliminated | "" |
| Order blocks | eliminated | "" |
| Fibonacci OTE | eliminated | "" |
| Momentum (fair shot) | eliminated | relaxed entry, still nothing |
| Liquidity sweep (fair shot) | eliminated | "" |
| **Supply/demand zone touch** | **survivor** | multiple cells significant; H4 family strongest |

### 4.2 Configuration that won

The survivor was sharpened post-ablation. Fading the zone touch only
when it was against the higher-timeframe trend produced a stronger
edge than fading every zone touch. The frozen configuration is the
`zone_d1_against` cell: `htf_align = D1`, `htf_align_mode = against`,
`htf_lookback = 10` daily bars, `htf_min_move_pips = 60`.

## 5. What this tells us

1. **The retail vocabulary is over-applied.** Most of the
   most-marketed price-structure concepts did not carry edge on the
   data we tested.
2. **One concept survived the same bar that killed the others.** That
   is the entire research basis for the live agent.
3. **The edge is mean-reversion, not "zones in general".** With-trend
   zone trading was tested separately and lost; counter-trend was the
   only direction that worked.

## 6. Honest limitations

- The funnel selected the zone concept on the same broad window later
  used for in-sample / out-of-sample testing. This is the selection-
  bias risk that E003 and E004 were designed to address.
- Each concept is one operational definition. A "dead" verdict closes
  this definition, not the underlying folk concept. A new pre-
  registration on a pristine slice could revive any of the six.
- Costs were modelled at a fixed 0.3 pip per side. Tighter cost
  modelling (slippage, weekend gaps) could shift point estimates by
  small amounts but should not flip the survivor list.

## 7. Conclusion

E001 is complete. The zone concept passed; the others did not. The
`zone_d1_against` cell handed to E002 is the only thing carried forward
into the validation chain. The agent's current live deployment is a
descendant of this single survivor.

## 8. References

- Source code in the trading agent: `agent/alphas/grid.py`,
  `agent/alphas/concepts/zone_alpha.py`, `agent/alphas/concepts/_htf.py`,
  `scripts/run_zone_all_tfs.py`.
- Narrative record: `multi-pair-trading-agent/docs/00-journey.md` sections 2--4.
- Downstream: `experiments/E002_zone_definitive_grid/` (definitive
  enumeration), `experiments/E003_holdout_validation/` (selection-bias
  control), `experiments/E004_walk_forward/` (the test that picked
  the deployed cell).
- Manifest: `MANIFEST.md`.
