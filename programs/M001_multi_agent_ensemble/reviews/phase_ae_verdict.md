# Phase AE verdict — Sae Itoshi event specialist

**Evaluated:** 2026-07-24 (UTC), ONCE, per the locked pre-registration
(`experiments/phase_ae_sae_event_specialist/PROTOCOL.md`, LOCKED
2026-07-24 commit `dfe5ce1` BEFORE any arm ran).
**Evaluator:** `experiments/phase_ae_sae_event_specialist/evaluate_phase_ae.py`
(committed `8fbc2ba`, also before any arm ran).
**Machine-readable:** `experiments/phase_ae_sae_event_specialist/results/phase_ae_evaluation.json`.

## VERDICT: **FAIL**

Rule: PASS iff AE1 AND AE2 AND AE4 (AE3 can only park a mechanic).
AE2 fails decisively. **Sae v1 is NOT armed for the Aug 7 NFP.** The
lever stops here; no threshold softening, no rerun.

| Criterion | Locked threshold | Observed | Status |
|---|---|---|---|
| AE1 volume | ≥ 30 OOS trades | **54** OOS trades (87 full-panel) | **PASS** |
| AE2 quality | mean TQS ≥ 0.30 AND boot 95% CI lower > 0.20 | mean TQS **0.097**, CI95 **[0.042, 0.162]** (n=10000, seed=42) | **FAIL** |
| AE3 mechanic split | park any mechanic < 20% of OOS trades | fade 12/54 = 22.2%, ride 42/54 = 77.8% | no park |
| AE4 chemistry | no incumbent regresses > 0.02 mean TQS | max delta −0.000 (Chigiri +0.001; all others 0.000) | **PASS** |

## Numbers that matter

- Sae fired on the frozen NFP/CPI/FOMC calendar exactly as designed:
  87 trades on the 2015-2025 panel (61 ride / 26 fade), 54 inside the
  seven §11.17 OOS windows. The volume prior held.
- The trades are bad: 25 TP vs 62 SL exits = **28.7% win rate at a
  1.5R target** (breakeven needs 40%), mean **−4.16 pips/trade**.
  Fade: mean TQS 0.122, −4.18 pips. Ride: mean TQS 0.089, −8.52 pips.
  Neither mechanic clears the quality bar; ride is the worse of the two.
- Per-window OOS mean TQS never exceeded 0.266 (best window) and hit
  0.000 in window 5 — the failure is uniform across the panel, not one
  bad regime.
- Chemistry is clean: the M15 side-book displaced exactly 2 incumbent
  trades over 11 years (Chigiri 503 → 501) and every incumbent's mean
  TQS is unchanged to 3 decimals. Sae the *mechanism* integrates
  safely; Sae the *edge* does not exist as specified.

## Interpretation (one paragraph, honest)

The hour-13 bleed hypothesis said some event-window pips are tradable
impulses. On NFP+CPI+FOMC 2015-2025, the v1 fade/ride rules capture
none of it: post-event M15 direction at T+15/T+30 is not predictable
enough for a 1.5R bracket, and the wick/retention filters do not
select better-than-random continuation or reversal. This is a real
negative result on 87 pre-registered trades, not a harness artifact —
the baseline arm reproduces the sealed g7retry2 driver byte-for-byte
(equivalence test, 1 passed) and Sae's mechanics are a verbatim port
of production `a09_sae.py` (next-gen `a26eba8`).

## Consequences

1. `sae_enabled` stays **False** in production. Nothing to arm on Aug 7.
2. Phase AD (Karasu news *defender*) remains the live claim on the
   hour-13 bleed — avoidance, not capture. This verdict strengthens
   the "avoidable, not tradable" reading of that bleed.
3. Any Sae v2 (different brackets, different windows, asymmetric
   mechanics) requires a NEW pre-registration; the v1 thresholds and
   mechanics are spent.
