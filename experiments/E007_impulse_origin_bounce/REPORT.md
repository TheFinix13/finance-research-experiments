# Test B — Impulse-Origin Return → Bounce Study (final report)

Pre-registered 2026-06-16 in `protocols/TEST_B_PROTOCOL.md` (commit
`b9715d9` on `origin/main`). All Stage-1 parameters, statistical
pipeline, and stop rules locked before any data was screened. This
report is the truthful read-out of the protocol's outcome.

## Headline

> **On EURUSD H4+H1 2015–2021, 93.4% of impulse-origin return events
> produced a bounce ≥ 0.5R within W bars — versus 91.6% at hour-matched
> random levels. The 1.8 pp lift is real but small, did not survive
> BH-FDR α=0.05 in any of the 12 pre-registered cells, and the protocol's
> stop rule (§3.7) fired at Stage 1. Stages 2/3/4 did not run. The user's
> "always bounces" intuition is *directionally* correct but the impulse-
> origin event does NOT carry meaningful conditional edge over random
> hour-matched price action.**

That sentence is what every figure in `output/test_b/figures/` is behind.

## Result by stage

| Stage | Status | Detail |
|---|---|---|
| **0 — Detector pre-registration** | done | `conflab/detectors_impulse_return.py` + `conflab/friction.py` committed (`5bc0145`). |
| **1 — Screen EURUSD 2015-2021** | **STOPPED — H1 dead** | 0 of 12 cells `alive`. 9 `parked_weak_effect`, 3 `dead`. Best raw p = 0.034 (H1 dir−1 M_atr=1.0); BH-FDR threshold at rank 1 of 12 is 0.05/12 ≈ 0.0042 — not even close. Registry: `output/test_b/stage1_EURUSD_screen_2026-06-16_1656.jsonl`. |
| **2 — Confirm** | **did not run** | Stop rule §3.7 fired. `stage2_…stop.json` documents the upstream stop. |
| **3 — Cross-pair sealed** | **did not run** | Same; recorded in `stage3_…stop.json`. |
| **4 — Friction conditioning** | **did not run** | Same; H2 is moot if H1 is dead. Friction-quartile cutoffs (§4) are still frozen for any future re-look under a fresh pre-registration. |

## Per-cell registry

All 12 cells (the full pre-registered Stage-1 family `TF × direction ×
M_atr`):

| cell | n | mean MFE (events) | mean MFE (controls) | effect (pips) | Cohen's d | raw p | P(≥0.5R) events | P(≥0.5R) controls | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| H4_dir+1_M1.0 | 49 | 91.8 | 87.9 | +4.0 | 0.05 | 0.357 | 93.9% | 94.7% | `parked_weak_effect` |
| H4_dir+1_M1.5 | 45 | 87.7 | 75.3 | +12.3 | 0.18 | 0.129 | 93.3% | 92.4% | `parked_weak_effect` |
| H4_dir+1_M2.0 | 36 | 92.5 | 78.4 | +14.1 | 0.18 | 0.164 | 91.7% | 87.8% | `parked_weak_effect` |
| H4_dir−1_M1.0 | 43 | 68.1 | 79.8 | −11.7 | −0.16 | 0.838 | 88.4% | 89.8% | **`dead`** |
| H4_dir−1_M1.5 | 38 | 65.1 | 81.3 | −16.2 | −0.28 | 0.935 | 86.8% | 91.1% | **`dead`** |
| H4_dir−1_M2.0 | 31 | 63.2 | 74.7 | −11.5 | −0.18 | 0.822 | 83.9% | 87.1% | **`dead`** |
| H1_dir+1_M1.0 | 213 | 60.7 | 54.2 | +6.5 | 0.13 | **0.040** | 93.9% | 92.1% | `parked_weak_effect` |
| H1_dir+1_M1.5 | 197 | 59.0 | 54.2 | +4.9 | 0.10 | 0.123 | 93.9% | 91.6% | `parked_weak_effect` |
| H1_dir+1_M2.0 | 160 | 57.2 | 53.5 | +3.7 | 0.07 | 0.189 | 91.9% | 92.1% | `parked_weak_effect` |
| H1_dir−1_M1.0 | 230 | 59.6 | 53.0 | +6.6 | 0.14 | **0.034** | 93.9% | 93.7% | `parked_weak_effect` |
| H1_dir−1_M1.5 | 214 | 56.6 | 52.1 | +4.5 | 0.09 | 0.110 | 93.5% | 91.8% | `parked_weak_effect` |
| H1_dir−1_M2.0 | 175 | 56.6 | 51.7 | +4.9 | 0.10 | 0.111 | 93.1% | 90.9% | `parked_weak_effect` |

BH-FDR at α=0.05 across the 12 cells requires p ≤ 0.05/12 ≈ 0.0042 at
the top rank. The lowest p (0.034, H1_dir−1_M1.0) misses the threshold
by an order of magnitude. **No cell is `alive`.**

## Figures

All figures live in `output/test_b/figures/` and are referenced
verbatim in the protocol's headline-statement requirement.

- `fig1_reach_curves_per_cell.png` — `P(MFE ≥ x·R)` at six R-multiples
  for every cell, events (solid blue) vs hour-matched controls (dashed
  grey), with verdict colour band behind each panel. The visual story
  is that event and control curves are essentially overlapping
  everywhere except H4 down-impulse where events sit *below* controls.
- `fig2_direction_split_headline.png` — the two best-raw-p cells
  (H1_dir+1_M1.0 and H1_dir−1_M1.0) overlaid against their respective
  hour-matched controls. Lifts of 1.8 pp / 0.3 pp at 0.5R; the gap
  widens at higher thresholds but never approaches significance under
  the locked test.
- `fig3_cross_pair_replication.png` — stop-state placeholder; Stage 3
  did not run.
- `fig4_friction_conditional.png` — stop-state placeholder; Stage 4
  did not run.
- `fig5_verdict_registry.png` — per-cell effect-pips (left) and
  headline reach probability (right) coloured by verdict tier. This is
  the single chart that summarises the entire experiment.

## What this tells us

1. **The user's discretionary intuition is directionally correct but
   uninformative.** Bounces ≥ 0.5R *do* happen ~93 % of the time after
   an impulse-origin return on EURUSD H4/H1 — but they also happen
   ~92 % of the time at *random* price points sampled at the same
   hour-of-day. The conditioning on "impulse origin" does not enrich
   the bounce rate enough to be detected as edge over BH-FDR.
2. **The asymmetry is real and informative.** Up-impulse events show
   a consistent (if not significant) positive lift (+4 to +14 pips).
   Down-impulse on H4 shows an actively *negative* lift (−11 to −16
   pips, events bounce LESS than random levels). EURUSD 2015-2021 had
   a net downward drift, so this is exactly what you'd expect if the
   "edge" is just baseline drift and the event picks up a sample
   biased the wrong way for shorts. **This is a strong implicit warning
   against asymmetric live deployment based on this signature.**
3. **Sample sizes are not the bottleneck.** Six of twelve cells have
   n ≥ 100 events. The effect is small in magnitude (Cohen's d ≤ 0.18
   across all cells), not undetected for lack of power. A larger N at
   the same effect size would shift the headline from "no edge" to
   "tiny edge", not to "tradable edge".
4. **"Friction in between is the noise — let's filter it out" stays
   untested.** That was H2, contingent on H1 surviving. The friction
   recipe is locked and the quartile cutoffs are computed; if anyone
   wants to test H2 in isolation later it must be a NEW pre-registered
   protocol with its own multiplicity accounting (a single-hypothesis
   test of friction conditioning, not a fishing trip downstream of a
   dead headline).
5. **No discoverable artefact was suppressed.** Statistics are
   computed and recorded for every cell, including the ones we lost
   interest in — that's the "compute-vs-claim" principle inherited
   from Test A's protocol.

## Methodology

Fully documented in `protocols/TEST_B_PROTOCOL.md` (commit `b9715d9`
on `origin/main`). Key choices:

- **Impulse leg** (§3.1): net move ≥ both `M_atr × ATR(20)` and
  `M_pips` (40 H4 / 20 H1) within `K=3` bars, with intrabar
  drawdown-from-running-max ≤ 50% of leg height (amendment 6.2 —
  the original 30% ceiling produced 1–4 candidate legs per cell, so
  the protocol was relaxed once, in a single non-data-peeking
  amendment, to the textbook fib 50% before any MFE was scored).
- **Origin zone** (§3.2): wider of the last opposite-direction bar
  or the prior 5-bar consolidation range. No padding.
- **Return event** (§3.3): first wick into the zone within `N` bars
  of impulse-end (40 H4 / 80 H1).
- **MFE** (§3.4): pip MFE in the impulse direction over `W` bars
  after the touch (20 H4 / 40 H1). `R = impulse_height ÷ 4`.
- **Controls** (§3.6): five hour-matched random levels per event,
  same direction, MFE measured the same way. Permutation null with
  `n_perm = 5000`.
- **FDR** (§3.5): BH-FDR α=0.05 across the 12-cell family.
- **n_gate** (§3.6): `n ≥ 30` to be eligible for `alive`.
- **Stop rules** (§3.7): if no `alive` cell at Stage 1, stop. Fired.

Direction conventions: `direction = +1` is up-impulse → bounce up;
`direction = −1` is down-impulse → bounce down. Both tested.

## Honest limitations

- **One screen window, one base pair.** This was the pre-registered
  screen (EURUSD 2015-2021). A future re-look — same protocol, new
  data window — is a counted re-test in its own multiplicity family.
- **Hour-matched controls only.** We did not also condition on the
  day-of-week or session-overlap. The Test A v2.1 amendment showed
  hour-of-day is the dominant nuisance variable; if the literature
  starts pointing at session-overlap as a separate nuisance, that's
  a NEW pre-registration.
- **R = impulse_height/4 is a fixed choice.** A larger denominator
  would shift reach probabilities upward at every threshold for both
  events and controls equivalently (it's a rescaling of x-axis), but
  the relative event-vs-control gap is invariant to this choice. The
  fixed denominator was set to make the reach grid `{0.5, 1, 1.5, 2,
  3, 4}R` cover the range from "first wiggle" to "full retrace".
- **`max_retrace_frac` was relaxed once** (amendment 6.2) before
  any MFE was scored — this was an infeasibility fix, not a tuning,
  and the original 0.30 record is preserved as
  `stage1_EURUSD_screen_cautionary_frac030_2026-06-16_1648.jsonl`
  alongside the canonical 0.50 result. No further parameter changes
  were made after seeing any event-level outcome.

## Conclusion

**The data does not support the romantic version of the claim.** Price
does come back to recent impulse origins and does usually bounce —
but it does so at almost the same rate as bouncing at any random
hour-of-day matched price point. The "always" framing is statistically
indistinguishable from the baseline behaviour of a trending FX market.

Practically, this means:

- The agent's existing `zone_d1_against` strategy — which trades the
  endpoint of a zone touch with HTF directional alignment — already
  captures whatever edge the impulse-origin signature has, and
  conditions it on the HTF gate that this test does NOT use. Adding a
  raw impulse-origin filter on top is not statistically motivated.
- The friction-conditioning idea (H2) is *interesting enough to be
  worth its own dedicated experiment* but only if registered against
  a SINGLE pre-specified setup, not as a downstream rescue of a dead
  headline. The cutoffs are saved; the protocol is not.
- Discretionary chart-reading that says "this looks like a textbook
  impulse-origin retest, I bet it bounces" will be right ~93 % of the
  time. So will "this is a random price point at the London open" be
  right ~92 % of the time. **The discretionary intuition is real;
  the conditional edge is not.**

Test B is closed.

---

References:

- Pre-registration: `protocols/TEST_B_PROTOCOL.md` (commit `b9715d9`).
- Detector & friction code: `conflab/detectors_impulse_return.py`,
  `conflab/friction.py` (commit `5bc0145`).
- Stage 1 canonical registry:
  `output/test_b/stage1_EURUSD_screen_2026-06-16_1656.jsonl`.
- Stage 1 cautionary record (frac=0.30):
  `output/test_b/stage1_EURUSD_screen_cautionary_frac030_2026-06-16_1648.jsonl`.
- Stop-state files: `stage{2,3,4}_…stop.json` in `output/test_b/`.
- Figures: `output/test_b/figures/fig{1..5}_*.png`.

70 unit tests pass (`python -m pytest -q` from repo root). Test A
artifacts unmodified. Trading agent (`eurusd-ai-agent`) not touched.
