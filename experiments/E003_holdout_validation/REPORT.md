# E003 — Report: holdout validation

**Date executed:** 2026-06-10 (in `multi-pair-trading-agent`) ·
**Lab registration:** 2026-06-16 (retrospective) ·
**Status:** complete · superseded for deployment by E004.

## Abstract

E002 left us with thirteen candidate cells from one window, the
textbook setup for selection bias. We ran a single in-sample /
out-of-sample split (2015 to 2022 in-sample, 2023 to 2025
out-of-sample) on the eight strongest candidates. One cell survived
out-of-sample (`zone_d1_against / H4 / asia`); the rest collapsed.
The deeper lesson was that one out-of-sample window is itself a single
draw and can be misleading, which motivated the walk-forward test in
E004. The deployment cell ultimately chosen by E004 differs from the
single survivor here.

## 1. Why this experiment exists

A candidate list from one window is a portfolio of guesses. The
standard guard against selection bias is to hold out a slice of data,
fit on the rest, and check whether the chosen rule still works on the
slice that was never seen. We did that here. The experiment is both a
validation step and a lesson in how easily the standard guard can lie
to you when only one out-of-sample window is available.

## 2. What we tested

- **H0:** an in-sample-significant cell's edge does not survive out of
  sample.
- **H1:** at least one of the eight strongest E002 candidates retains
  positive expectancy on the 2023 to 2025 out-of-sample window.

## 3. Method (short version)

- Data: EUR/USD 2015-01-01 to 2025-11-30, Dukascopy minute data.
- Split: in-sample 2015-01-01 to 2022-12-31; out-of-sample 2023-01-01
  to 2025-11-30.
- Candidates: the eight strongest cells from E002 by in-sample
  expectancy.
- Outcome: per-trade expectancy after a fixed 0.3-pip spread per side.
- Verdict per cell: "validated" if the out-of-sample mean is positive
  and significant under bootstrap at 5\,\%; "collapsed" otherwise.
- Harness: `scripts/run_holdout_validation.py`.

## 4. Results

> **Headline:** one of eight cells validated out-of-sample
> (`zone_d1_against / H4 / asia`). The others either collapsed or
> shrank to near zero. A spectacular D1 collapse from +25 pips in-sample
> to +1 pip out-of-sample is the cleanest illustration of why we did
> not stop here.

### 4.1 Summary

| Metric | Value |
|---|---|
| Candidates tested in-sample | 8 |
| Out-of-sample survivor | 1 (`zone_d1_against / H4 / asia`) |
| Largest in-sample-to-out-of-sample collapse | D1 cell: +25 to +1 pips/trade |

## 5. What this tells us

1. **One in-sample-to-out-of-sample window catches some overfitting,
   but not all.** The 7 of 8 collapse rate is consistent with
   significant selection bias in the candidate list.
2. **The one survivor was the H4 Asia-session cell.** This looked like
   a clear answer at the time. E004's walk-forward later showed that
   the per-trade edge of the H4 Asia cell and the H4 all-sessions cell
   are within a pip of each other; the all-sessions variant has roughly
   four times the sample and is the safer deployment.
3. **D1 looks dangerous from this experiment alone.** The +25 to +1
   pip collapse is large but is also a small-sample artefact. A
   cross-pair panel design (parked as future work) is the right next
   step for D1 claims.

## 6. Honest limitations

- A single in-sample / out-of-sample split is one draw. With only one
  window, an unlucky out-of-sample slice or a regime change can throw
  the verdict either way. The protocol's answer was to graduate to
  walk-forward (E004), not to trust this single split.
- The out-of-sample window happens to span 2023 to 2025, a directional
  trend regime for EUR/USD. Different out-of-sample windows could
  produce different survivors.
- Costs are modelled identically to E001 and E002, so any cost-shift
  bias propagates.

## 7. Conclusion

E003 is complete. The validated cell of record is
`zone_d1_against / H4 / asia` as a single-split survivor; the
*deployed* cell is `zone_d1_against / H4 / all sessions`, chosen by
the walk-forward in E004. The discrepancy between this report's
survivor and the deployment choice is itself part of the validation
story: the single split was not the final word.

## 8. References

- Runner: `multi-pair-trading-agent/scripts/run_holdout_validation.py`.
- Narrative: `multi-pair-trading-agent/docs/00-journey.md` section 6.2.
- Downstream: `experiments/E004_walk_forward/` (replaces this verdict
  for deployment), `experiments/E005_cross_pair_sealed/` (independent
  out-of-sample arm).
- Manifest: `MANIFEST.md`.
