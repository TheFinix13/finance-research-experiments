# E004 — Report: walk-forward validation

**Date executed:** 2026-06-09 (in `multi-pair-trading-agent`) ·
**Lab registration:** 2026-06-16 (retrospective) ·
**Status:** complete · primary evidence for the EUR/USD deployment cell.

## Abstract

A single in-sample / out-of-sample split (E003) is one draw and can
mislead. The walk-forward test runs the same rule across seven
independent rolling windows, each with four years in-sample and one
year out-of-sample. On the `zone_d1_against / H4` family, all seven
out-of-sample windows posted positive expectancy with a median of
+11.34 pips per trade. The "Asia-session only" survivor from E003
turned out to be selection bias from one window: the H4 all-sessions
cell produced the same per-trade edge with roughly four times the
trade count, and was chosen as the deployment cell.

## 1. Why this experiment exists

Walk-forward is the standard antidote to single-split selection bias.
The rule's parameters are locked in advance, then the data is sliced
into rolling four-year-in / one-year-out windows. If the rule survives
multiple independent out-of-sample windows, the edge is more likely
structural and less likely an artefact of any one fitting window. The
experiment was run on the strongest E002 candidates after the lesson
of E003.

## 2. What we tested

- **H0:** the H4 zone-fade rule's positive expectancy is concentrated
  in a single in-sample window and does not repeat across rolling
  out-of-sample slices.
- **H1:** the rule produces positive expectancy in at least four of
  seven rolling out-of-sample windows.

## 3. Method (short version)

- Data: EUR/USD 2015-01-01 to 2025-11-30.
- Windows: seven rolling windows, each four years in-sample followed
  by one year out-of-sample, stepped one year at a time.
- Cells compared: `zone_d1_against / H4 / asia` (the E003 survivor)
  and `zone_d1_against / H4 / all sessions`.
- Outcome: median out-of-sample per-trade expectancy across windows;
  fraction of windows positive.
- Runner: `scripts/run_walk_forward.py`; analysis:
  `scripts/analyze_walk_forward.py`.

## 4. Results

> **Headline:** `zone_d1_against / H4 / all sessions` posted positive
> out-of-sample expectancy in 7 of 7 rolling windows, median +11.34
> pips per trade. The Asia-session cell achieved the same per-trade
> edge on roughly one-quarter of the sample; the all-sessions cell
> was chosen for deployment on sample-size grounds.

### 4.1 Cell comparison

| Cell | OOS windows positive | Median OOS pips/trade | Approx. trades/window |
|---|---:|---:|---:|
| `zone_d1_against / H4 / all` | **7/7** | **+11.34** | ~66 |
| `zone_d1_against / H4 / asia` | 7/7 | +11.36 | ~15 |

### 4.2 Raw results

Per-window numbers are preserved in `results/2026-06-09_walk_forward.md`
and `results/walk_forward_raw.json` in this experiment folder.

## 5. What this tells us

1. **Seven of seven positive out-of-sample windows is the strongest
   single piece of evidence in the agent's validation chain.** A
   coin-flip null would put this at probability $2^{-7} \approx 0.008$.
2. **The Asia-only survivor from E003 was a smaller-sample echo of the
   same edge.** Per-trade expectancy is statistically indistinguishable
   between the Asia and all-sessions variants. The all-sessions variant
   has more trades, so its standard error around the per-trade mean is
   smaller and its live risk profile is steadier.
3. **The deployment cell exists.** This is the test that produced the
   answer the live agent runs in production.

## 6. Honest limitations

- All seven windows are EUR/USD. Cross-pair replication is a separate
  arm (E005) and is required before any new pair is deployed.
- The 1.5 take-profit multiple is locked across all windows. It was
  never grid-searched. A future experiment will sweep it after the
  live agent passes 50 trades.
- Walk-forward is robust to single-window bias but not to regime
  changes that exceed the window length. The 2025 to 2026 sealed look
  (E005) is the first sanity check on that.

## 7. Conclusion

E004 is complete and is the deployment evidence of record. The
agent's live router uses `zone_d1_against / H4 / all sessions` for
EUR/USD with full risk; the same parameters were taken to the
cross-pair replication arm in E005.

## 8. References

- Runner: `multi-pair-trading-agent/scripts/run_walk_forward.py`.
- Analyser: `multi-pair-trading-agent/scripts/analyze_walk_forward.py`.
- Narrative: `multi-pair-trading-agent/docs/00-journey.md` section 7;
  evidence snapshot: `multi-pair-trading-agent/docs/reviews/2026-06-09_walk_forward.md`.
- Lab copies: `results/2026-06-09_walk_forward.md`,
  `results/walk_forward_raw.json` (this folder).
- Downstream: `experiments/E005_cross_pair_sealed/` (cross-pair arm and
  sealed look).
- Manifest: `MANIFEST.md`.
