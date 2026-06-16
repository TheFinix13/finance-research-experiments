# E007 — Report: impulse-origin return then bounce study (Test B)

**Pre-registered:** 2026-06-16 in `protocols/TEST_B_PROTOCOL.md` (commit
`b9715d9` on `origin/main`). All Stage-1 parameters, statistical
pipeline, and stop rules were locked before any data was screened.
**Status:** stopped at Stage 1 by the protocol's own stop rule. This
report is the truthful read-out of the protocol's outcome.

## Abstract

A common discretionary intuition says that when price retraces back to
the start of a strong move, it almost always bounces. On EUR/USD H4
and H1 between 2015 and 2021, that intuition is *directionally*
correct: 93.4\,\% of impulse-origin return events produced a bounce of
at least half the move's risk-unit within the next window. The catch
is that 91.6\,\% of randomly chosen levels at the *same hour of day*
also produced a bounce of the same size. The 1.8 percentage-point lift
is real but small and did not survive Benjamini-Hochberg correction at
5\,\% in any of the 12 pre-registered cells. The protocol's stop rule
fired at Stage 1. Stages 2 (confirm), 3 (cross-pair sealed), and 4
(friction conditioning) did not run. The "always bounces" framing is
indistinguishable from the baseline behaviour of a trending FX market.

## 1. Why this experiment exists

This study was triggered by the user's chart-reading observation that
price reliably "comes back to" the origin of a sharp move and bounces
there. The literature variant is the ICT community's "imbalance
fills" / "order block returns" framing. The empirical content is a
conditional claim: bouncing at impulse origins should beat bouncing at
matched random levels. Test B is the test of that conditional claim,
on the pair the live agent already trades, using the same hour-matched
control machinery that E006 had to introduce after the M15
session-volatility confound.

## 2. What we tested

- **H1**: a return to the origin of a strong impulse leg produces a
  larger maximum favourable excursion in the impulse direction over
  the next window than a hour-matched random level of the same
  direction.
- **H2** (conditional on H1): the H1 effect is amplified after
  filtering out "high-friction" paths (lots of intra-move chop) and is
  strongest on clean impulse-to-retest paths.

H2 was not tested. The protocol's stop rule at Stage 1 made it moot.

## 3. Method (short version)

This section locks the recipe. The full pre-registered protocol is in
`protocols/TEST_B_PROTOCOL.md` and `PROTOCOL.md` in this folder.

- Pair and split: EUR/USD, screen window 2015-01-01 to 2021-12-31.
- Family: 12 cells = 2 timeframes (H4, H1) by 2 directions ($+1$ up,
  $-1$ down) by 3 impulse-size thresholds (1.0, 1.5, 2.0 ATR).
- Impulse leg definition: net move of at least $M_{\text{atr}} \times
  \text{ATR}(20)$ and at least $M_{\text{pips}}$ within $K=3$ bars,
  with intra-bar drawdown from the running maximum at most 50\,\% of
  leg height. ($M_{\text{pips}}$ is 40 for H4, 20 for H1. The 50\,\%
  drawdown ceiling is amendment 6.2 to the protocol; the original
  30\,\% gave too few candidate legs to test, and the amendment was
  applied once, before any MFE was scored, with the 30\,\% record
  preserved as a cautionary file.)
- Origin zone: the wider of the last opposite-direction bar before
  the impulse or the prior 5-bar consolidation range. No padding.
- Return event: the first wick into the origin zone within $N$ bars
  of impulse end (40 for H4, 80 for H1).
- Outcome metric: maximum favourable excursion in the impulse
  direction over $W$ bars after the touch (20 for H4, 40 for H1),
  measured in pips. Also recorded: probability of reaching
  $\{0.5, 1, 1.5, 2, 3, 4\}R$, where $R$ is the impulse height divided
  by four (so $0.5R$ is one-eighth of the impulse, $4R$ is a full
  retracement back to the impulse's far side).
- Controls: five hour-matched random levels per event, same direction,
  MFE measured identically.
- Statistics: 5,000-shuffle permutation test, one-sided in the
  hypothesised direction. Benjamini-Hochberg false-discovery-rate
  correction at 5\,\% across the 12 cells.
- Sample-size gate: $n \geq 30$ to be eligible for `alive`.
- Stop rule (Section 3.7 of the protocol): if no cell is `alive` at
  Stage 1, stop. (This is what fired.)

### 3.1 Worked example: one H4 impulse-origin return

In late 2018 on EUR/USD H4, price fell from 1.1820 to 1.1740 in two
bars (80 pips, $\approx 1.7 \times \text{ATR}(20)$). The detector
qualified this as a down-impulse leg at the 1.5-ATR threshold. The
origin zone was the previous up-bar's range, 1.1810 to 1.1822.
Twenty H4 bars later, price returned and wicked into 1.1815 from
below; the detector tagged this as a `direction = -1` return event.
The MFE in the down direction over the next 20 H4 bars was 41 pips.
The matched hour-matched random control (same hour-of-day, same
direction) over its own next 20 H4 bars reached 53 pips. This event's
contribution to the H4 down-impulse 1.5-ATR cell is therefore
$41 - 53 = -12$ pips: the event under-performed the random level.
The full cell aggregates 38 such events with a mean effect of $-16.2$
pips and a raw $p$-value of 0.935. The cell is `dead`.

## 4. Results

This section reports the per-stage outcome.

### 4.1 Stage results

> **Headline:** 0 of 12 cells alive at Stage 1. Lowest raw $p$ is 0.034
> on H1 down-direction at 1.0 ATR; the BH-FDR threshold at the top
> rank is 0.05 / 12 = 0.0042. The stop rule fired and Stages 2, 3, 4
> did not run.

| Stage | Status | Detail |
|---|---|---|
| 0 — Detector pre-registration | done | `conflab/detectors_impulse_return.py` and `conflab/friction.py` committed (`5bc0145`). |
| **1 — Screen EUR/USD 2015-2021** | **STOPPED — no cell alive** | 0 of 12 alive; 9 parked weak, 3 dead. Best raw $p$ = 0.034. Registry: `output/test_b/stage1_EURUSD_screen_2026-06-16_1656.jsonl`. |
| 2 — Confirm | did not run | Stop rule 3.7 fired. `stage2_..._stop.json` documents the upstream stop. |
| 3 — Cross-pair sealed | did not run | Same. Recorded in `stage3_..._stop.json`. |
| 4 — Friction conditioning | did not run | Same. H2 is moot if H1 is dead. Friction-quartile cutoffs are frozen for future re-look only. |

### 4.2 Per-cell registry

All 12 cells (the full pre-registered Stage-1 family):

| cell | $n$ | MFE events | MFE controls | effect (pips) | Cohen's $d$ | raw $p$ | $P(\geq 0.5R)$ events | $P(\geq 0.5R)$ controls | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| H4_dir+1_M1.0 | 49 | 91.8 | 87.9 | +4.0 | 0.05 | 0.357 | 93.9% | 94.7% | `parked_weak_effect` |
| H4_dir+1_M1.5 | 45 | 87.7 | 75.3 | +12.3 | 0.18 | 0.129 | 93.3% | 92.4% | `parked_weak_effect` |
| H4_dir+1_M2.0 | 36 | 92.5 | 78.4 | +14.1 | 0.18 | 0.164 | 91.7% | 87.8% | `parked_weak_effect` |
| H4_dir-1_M1.0 | 43 | 68.1 | 79.8 | -11.7 | -0.16 | 0.838 | 88.4% | 89.8% | **`dead`** |
| H4_dir-1_M1.5 | 38 | 65.1 | 81.3 | -16.2 | -0.28 | 0.935 | 86.8% | 91.1% | **`dead`** |
| H4_dir-1_M2.0 | 31 | 63.2 | 74.7 | -11.5 | -0.18 | 0.822 | 83.9% | 87.1% | **`dead`** |
| H1_dir+1_M1.0 | 213 | 60.7 | 54.2 | +6.5 | 0.13 | **0.040** | 93.9% | 92.1% | `parked_weak_effect` |
| H1_dir+1_M1.5 | 197 | 59.0 | 54.2 | +4.9 | 0.10 | 0.123 | 93.9% | 91.6% | `parked_weak_effect` |
| H1_dir+1_M2.0 | 160 | 57.2 | 53.5 | +3.7 | 0.07 | 0.189 | 91.9% | 92.1% | `parked_weak_effect` |
| H1_dir-1_M1.0 | 230 | 59.6 | 53.0 | +6.6 | 0.14 | **0.034** | 93.9% | 93.7% | `parked_weak_effect` |
| H1_dir-1_M1.5 | 214 | 56.6 | 52.1 | +4.5 | 0.09 | 0.110 | 93.5% | 91.8% | `parked_weak_effect` |
| H1_dir-1_M2.0 | 175 | 56.6 | 51.7 | +4.9 | 0.10 | 0.111 | 93.1% | 90.9% | `parked_weak_effect` |

The Benjamini-Hochberg threshold at the top rank in a family of 12 is
$0.05 / 12 \approx 0.0042$. The lowest raw $p$ in the table (0.034 on
H1 down-direction at 1.0 ATR) misses that threshold by roughly an
order of magnitude.

### 4.3 Figures

| File | What it shows |
|---|---|
| `output/test_b/figures/fig1_reach_curves_per_cell.png` | $P(\text{MFE} \geq xR)$ at six R-multiples for every cell. Events (solid blue) and hour-matched controls (dashed grey) sit on top of each other except on H4 down-impulse, where events sit *below* controls. |
| `output/test_b/figures/fig2_direction_split_headline.png` | The two best-raw-$p$ cells overlaid against their controls. Lifts of 1.8 pp and 0.3 pp at the $0.5R$ threshold; the gap widens slightly at higher thresholds but never approaches significance under the locked test. |
| `output/test_b/figures/fig3_cross_pair_replication.png` | Stop-state placeholder. Stage 3 did not run. |
| `output/test_b/figures/fig4_friction_conditional.png` | Stop-state placeholder. Stage 4 did not run. |
| `output/test_b/figures/fig5_verdict_registry.png` | Per-cell effect (pips, left) and headline reach probability (right) coloured by verdict tier. One chart summarises the whole experiment. |

## 5. What this tells us

1. **The discretionary intuition is directionally correct but
   uninformative.** Bounces of at least $0.5R$ happen roughly 93\,\%
   of the time after an impulse-origin return on EUR/USD H4 or H1,
   but they also happen roughly 92\,\% of the time at random price
   points sampled at the same hour of day. Conditioning on
   "impulse origin" does not enrich the bounce rate enough to be
   detected as edge under Benjamini-Hochberg.
2. **The asymmetry is real and informative.** Up-impulse cells show a
   consistent (if not significant) positive lift of +4 to +14 pips.
   Down-impulse cells on H4 show an actively negative lift, with
   events bouncing *less* than random levels. EUR/USD 2015 to 2021
   had a net downward drift, so a negative down-direction lift is
   what you would expect if the apparent "edge" is in fact the
   baseline drift and the event is picking up a sample biased the
   wrong way for shorts. This is a strong implicit warning against
   asymmetric live deployment based on this signature.
3. **Sample sizes are not the bottleneck.** Six of twelve cells have
   $n \geq 100$ events. The effect is small in magnitude (Cohen's $d
   \leq 0.18$ across all cells), not undetected for lack of power. A
   larger $n$ at the same effect size would shift the headline from
   "no edge" to "tiny edge", not to "tradable edge".
4. **The friction idea is not refuted.** Filtering out high-friction
   paths (H2) is a separately interesting question. If anyone wants
   to test it, the protocol's recipe is on file but the test must be
   a new pre-registration with its own multiplicity accounting, not a
   downstream rescue of a dead headline.
5. **No discoverable artefact was suppressed.** Statistics are
   computed and recorded for every cell, including the ones we lost
   interest in. That is the "compute-vs-claim" principle inherited
   from E006.

## 6. Honest limitations

- One screen window, one base pair. The pre-registered screen is
  EUR/USD 2015 to 2021. A future re-look on a different window is a
  counted re-test in its own multiplicity family.
- Hour-matched controls only. We did not also condition on day of
  week or session overlap. E006's amendment v2.1 showed hour of day
  is the dominant nuisance variable; any future addition of session
  overlap is a new pre-registration.
- $R$ = impulse height divided by 4 is a fixed choice. A larger
  denominator would shift all reach probabilities upward at every
  threshold for both events and controls equally; the relative gap
  is invariant. The denominator was set so the reach grid spans
  "first wiggle" to "full retracement".
- The 50\,\% drawdown ceiling for impulse legs is amendment 6.2 to
  the protocol. The amendment was applied once, before any MFE was
  scored, as an infeasibility fix (the original 30\,\% gave 1 to 4
  candidates per cell). The 30\,\% record is preserved at
  `output/test_b/stage1_EURUSD_screen_cautionary_frac030_2026-06-16_1648.jsonl`.

## 7. Conclusion

The data does not support the romantic version of the claim. Price
does come back to recent impulse origins and does usually bounce. It
does so at almost the same rate as bouncing at any hour-matched
random price point. The "always bounces" framing is statistically
indistinguishable from the baseline behaviour of a trending FX
market.

Practically:

- The agent's existing `zone_d1_against` strategy (E001 to E005)
  trades the endpoint of a zone touch with a higher-timeframe
  directional gate, which already captures whatever edge the
  impulse-origin signature has. Adding a raw impulse-origin filter on
  top is not statistically motivated.
- The friction-conditioning idea (H2) is interesting enough to be
  worth its own dedicated experiment, but only registered against a
  single pre-specified setup, not as a rescue of a dead headline. The
  friction cutoffs are saved; the protocol for that experiment is
  not yet written.
- Discretionary chart-reading that says "this looks like a textbook
  impulse-origin retest, I bet it bounces" will be right roughly
  93\,\% of the time. So will "this is a random price point at the
  London open" be right roughly 92\,\% of the time. The discretionary
  intuition is real; the conditional edge is not.

Test B is closed.

## 8. References

- Pre-registration: `protocols/TEST_B_PROTOCOL.md` and this folder's
  `PROTOCOL.md` (commit `b9715d9`).
- Detector and friction code: `conflab/detectors_impulse_return.py`,
  `conflab/friction.py` (commit `5bc0145`).
- Stage 1 canonical registry:
  `output/test_b/stage1_EURUSD_screen_2026-06-16_1656.jsonl`.
- Stage 1 cautionary record (drawdown ceiling 30\,\%):
  `output/test_b/stage1_EURUSD_screen_cautionary_frac030_2026-06-16_1648.jsonl`.
- Stop-state files: `stage{2,3,4}_..._stop.json` in `output/test_b/`.
- Figures: `output/test_b/figures/fig{1..5}_*.png`.
- Manifest: `MANIFEST.md`.

70 unit tests pass (`python -m pytest -q` from repo root). E006
artefacts unmodified. The trading agent (`multi-pair-trading-agent`) was not
touched.
