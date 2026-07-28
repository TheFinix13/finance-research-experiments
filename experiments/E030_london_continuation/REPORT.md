# E030 — London-continuation session drift: REPORT

**Verdict: STOPPED at Stage 1 go/no-go (2026-07-28).**
No out-of-sample data was touched. Pre-registration commit `36328ab`;
harness commit `3e90cf4`; Stage 1 run 2026-07-28, seed 30.

---

## 1. Claim tested

Mirror of E028's inversion: on days when London takes exactly one side
of the Asia range, enter WITH London's direction at the close of the
first M15 bar ≥ 13:30 UTC and hold to the last M15 close before 21:00
UTC. Time exit only, zero geometry knobs, costs 0.3 pip/side base.

Stage 1 was pre-declared **non-claiming** (the hypothesis was
generated on this very slice via E028) — an effect-size lock with a
go/no-go: stop if either arm's mean ≤ 0 at base costs, or if either
arm fails to beat the same-direction drift on BOTH/NEITHER placebo
days.

## 2. Stage 1 — EURUSD M15 2015–2021

| Arm | n | Mean net (base) | Mean net (stress) | 95 % CI (base) | p(≤0) | Win rate | Placebo mean |
|---|---|---|---|---|---|---|---|
| LONG (HIGH_ONLY days) | 580 | **+0.34 pips** | −1.06 | [−2.35, +3.11] | 0.410 | 46.0 % | −2.02 |
| SHORT (LOW_ONLY days) | 600 | **−1.38 pips** | −2.78 | [−4.44, +1.59] | 0.815 | 49.3 % | +0.82 |

**Stop trigger:** SHORT mean ≤ 0 at base costs. (The LONG arm passed
the letter of the go/no-go but is itself noise: p = 0.41, CI spanning
zero, negative at stress costs.)

## 3. Interpretation

E028's inversion was a statement about **path**, not **endpoint**:
60 % of one-side days *touch* territory beyond London's extreme at
some point in NY, but the close-to-close 13:30 → 21:00 drift in
London's direction is ~zero — a fraction of a pip against a ±40-pip
trade distribution. Touch probability does not convert into holdable
directional drift; whatever continuation exists is intrabar/transient
and is consumed by costs. Both readings of the Po3 day structure —
reversal (E028) and continuation (E030) — are now dead as mechanical
rules on this data.

## 4. Discipline notes

- The taint design worked exactly as intended: because the
  hypothesis-generating slice was demoted to a non-claiming go/no-go,
  the idea died **in-sample, at zero out-of-sample cost**. EURUSD
  2022–2024, GBPUSD 2015–2021 (Stage 3) and the sealed slice were
  never scored under this protocol.
- Sealed reservation (EURUSD M15 2025-01-01 → 2026-05-27) released
  for E030; the E029 co-reservation was unaffected and was consumed
  by E029's own sealed run.
- Day classification delegated to E028's frozen classifier
  (byte-identical rule; equivalence unit-tested).
- Stop files: `output/E030_london_continuation/stage{2,3,4}_E030_stop.json`.

## 5. Artefacts

- Stage 1: `output/E030_london_continuation/stage1_EURUSD_lock_2026-07-28_1813.json`
- Tests: `programs/E030/tests/test_continuation_days.py` (4 pass)
