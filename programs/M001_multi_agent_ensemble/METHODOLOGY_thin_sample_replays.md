# Methodology standard — testing thin-sample (rare-fire) agents

Adopted 2026-08-04 in response to the Phase AJ-2 structural
discovery: per-agent replay KPIs are PATH-DEPENDENT for low-n agents.
Barou's identical calendar years produced n=25 vs n=10 depending only
on where the replay started, because accumulated squad state (risk
caps, cooldowns, open-position slots, Kunigami warnings, aggregator
history) differs by path. A single replay is therefore ONE DRAW from
a distribution, and for agents with few trades that draw is noisy
enough to flip verdicts.

## The standard (binding on all future M001 protocols)

Applies whenever a cell's expected per-agent n is below **100 trades**
in the tested window (check against the nearest prior replay; if
unknown, assume it applies).

1. **Multi-start ensemble, K = 5.** Run the identical configuration
   five times with start dates staggered by 0 / +3 / +6 / +9 / +12
   months (same end date). Each start is a different squad-state
   path over the same market history.
2. **Burn-in discard.** Trades in the first 3 months after each
   start are excluded from KPIs (the warm-up where state is filling
   from empty and no path is representative).
3. **Judge the MEDIAN, require stability.** Promotion floors apply
   to the median across the 5 starts, AND the verdict-relevant sign
   (mean R > 0, PF > 1) must hold in at least 4 of 5 starts. A cell
   that passes on the median but flips sign across starts is
   `path_unstable` — reported, never promoted.
4. **Report the range.** Every REPORT table for a thin-n cell shows
   median [min–max] for n, PF, and mean R. A point estimate without
   the range is non-compliant.
5. **Cost accounting.** 5× replay cost is the price of an honest
   answer for rare-fire agents; protocols must budget for it or
   narrow their cell count. Mechanism/ablation studies (AK-style)
   comparing two arms should use the SAME start set for both arms so
   path noise cancels in the comparison.
6. **Effect-size floor.** Differences smaller than the observed
   cross-start range are noise by construction and may not be cited
   as findings.

## Why not fix the path-dependence itself

The path-dependence is REAL behaviour, not a bug: the live squad also
carries state, and a rare-fire agent's live results will likewise
depend on the squad's history. Averaging over starts estimates the
distribution the live agent actually samples from; "fixing" the
engine to be stateless would test a system we don't ship.

## Retroactive note

Phase AF/AJ/AJ-2 single-replay results for Barou, Nagi, and any
agent below ~40 trades per cell carry an unquantified path-noise
band and should be read as provisional. Rin (n≈470+) and squad-level
KPIs (n≈1800) are effectively immune.
