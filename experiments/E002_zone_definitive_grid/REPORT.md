# E002 — Report: zone definitive grid

**Date executed:** 2026-06-10 (in `multi-pair-trading-agent`) ·
**Lab registration:** 2026-06-16 (retrospective) ·
**Status:** complete (exploratory enumeration). Superseded for deployment
claims by E003 and E004.

## Abstract

Once the supply/demand zone concept survived E001, the next question
was where exactly it carried edge. We ran the definitive grid: every
timeframe and session combination for the `zone_d1_against` family on
EUR/USD across the full 2015 to 2025 window. Thirteen cells passed
Benjamini-Hochberg false-discovery-rate correction at 5\,\%. The
survivor list is a *candidate* list only; the cell finally deployed
was chosen by the walk-forward test (E004), not by this enumeration.

## 1. Why this experiment exists

E001 told us that zones work in principle. The retail follow-up
question is "what timeframe? what session?" Many traders use H1 or
M15 zones with London-session filters. Others use H4 or D1 with no
session filter. Before picking one for deployment, we wanted the full
map of where the rule was statistically significant on a single
window, so the walk-forward stage could choose from a *named* set of
candidates rather than an open universe of cells.

## 2. What we tested

- **H0:** the zone-fade rule has no edge on any specific
  (timeframe, session) cell.
- **H1:** at least one (timeframe, session) cell has positive
  expectancy that survives Benjamini-Hochberg at 5\,\% across the
  full grid.

## 3. Method (short version)

- Data window: EUR/USD 2015-01-01 to 2025-11-30, Dukascopy minute data.
- Grid: timeframe in {D1, H4, H1, M15, M5} crossed with session in
  {all, London, NY, London-NY overlap, Asia}.
- Rule: the frozen `zone_d1_against` configuration from E001
  (`htf_align = D1`, `htf_align_mode = against`, `htf_lookback = 10`,
  `htf_min_move_pips = 60`).
- Outcome: per-trade expectancy after a fixed 0.3-pip spread per side.
- Statistics: bootstrap $p$-value per cell, Benjamini-Hochberg at 5\,\%
  across the 25 cells.
- Runner: `scripts/run_zone_all_tfs.py` in the trading agent.

## 4. Results

> **Headline:** thirteen of twenty-five (timeframe, session) cells passed
> Benjamini-Hochberg at 5\,\%. The H4 family dominated, followed by D1.
> No cell was deployed off this enumeration alone.

### 4.1 Summary

| Family | Significant cells | Notes |
|---|---:|---|
| H4 zone-fade against D1 | several | strongest expectancy, largest sample |
| D1 zone-fade against D1 | several | larger per-trade expectancy, smaller sample |
| Lower timeframes (H1, M15, M5) | a few | small expectancy, large sample |

The full per-cell table lives in `multi-pair-trading-agent/docs/00-journey.md`
section 6.1; the lab does not duplicate it.

## 5. What this tells us

1. **The survivor list is plural, not unique.** Thirteen cells does not
   mean thirteen strategies; it means thirteen candidates for the
   selection-bias-aware tests that follow.
2. **The natural home of the edge looks like H4.** Both the per-trade
   number and the sample size are healthy on H4. D1 has larger per-trade
   expectancy but too few trades to lean on.
3. **An enumeration is not a deployment.** The deployment decision is
   the responsibility of E003 (holdout) and E004 (walk-forward), each
   of which is built explicitly to undo the selection bias baked into
   any "best-cell-on-one-window" claim.

## 6. Honest limitations

- All thirteen cells were significant on *the same* 2015 to 2025 window.
  Picking the "best" one from this list and shipping it would be classic
  selection bias.
- The grid is small (25 cells) and the multiplicity correction is
  modest. A finer grid would either need stronger correction or a fresh
  pre-registration.
- Spread, session, and broker-fill costs are modelled coarsely. Live
  costs may differ enough to shift small cells across the significance
  boundary.

## 7. Conclusion

E002 produced the candidate list. The list is on file; the decision is
not in this experiment. E003 took the eight strongest candidates into a
single in-sample / out-of-sample split (and showed why a single OOS
window is also unsafe); E004 then ran the walk-forward that produced
the deployed cell.

## 8. References

- Runner: `multi-pair-trading-agent/scripts/run_zone_all_tfs.py`.
- Narrative: `multi-pair-trading-agent/docs/00-journey.md` section 6.1.
- Downstream: `experiments/E003_holdout_validation/`,
  `experiments/E004_walk_forward/`.
- Manifest: `MANIFEST.md`.
