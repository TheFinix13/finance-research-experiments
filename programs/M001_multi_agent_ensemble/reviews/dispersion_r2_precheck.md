# Dispersion-primitives round 2 — pre-check on banked §11.13 caches

**Tag:** `g7retry1_precheck` (both aggregators).
**Ran:** 2026-07-14, immediately after committing the r2 primitives + tests.
**Panel:** OOS union 2019-01 → 2025-12 (7 rolling windows, `--retire-kunigami` roster).
**Inputs:** §11.13 banked caches (byte-equivalent to their originals — no new OOS touch).
- phi41: `g7_replay_cache_walk-forward-post-kunigami-retirement` + `g7_leave_one_out_post-V/lo1_*`.
- arm4:  `g7_replay_cache_phi5-arm4-post-kunigami`             + `g7_leave_one_out_phi5-arm4/lo1_*`.
**Verdict-bearing:** the numbers below are C5/C6 only. C1–C4 are reported for
completeness but they inherit §11.13's trade streams unchanged and are not
what dispersion-r2 predicts on (see §4 of
`experiments/dispersion_primitives_r2/PROTOCOL.md`).

## Purpose

Pre-registration §4.1: recompute C5/C6 for the five bar-having agents
(Isagi/Bachira/Rin/Chigiri/Barou) through the NEW primitives on the §11.13
cached `source_*` fields. Nagi is explicitly N/A here — his fix requires
freshly stamped leader provenance which only the re-gate replay produces.
The pre-check is BINDING per stop rule §5.1: any predicted-pass that fails
at this step is REPORTED, and the constants stay frozen (no
iterate-and-recheck).

## Result summary

| Agent            | phi41 C5→C5' | phi41 C6→C6' | arm4 C5→C5' | arm4 C6→C6' | Meets §3 prediction |
|---|---|---|---|---|---|
| isagi_yoichi    | 0.086 → **0.205** ✓ | 0.083 → **0.178** ✓ | 0.087 → **0.196** ✓ | 0.082 → **0.185** ✓ | YES (Isagi C5/C6 both predicted ≥ 0.10) |
| bachira_meguru  | 0.089 → **0.476** ✓ | 0.154 → **0.154** ✓ | 0.101 → **0.448** ✓ | 0.154 → **0.156** ✓ | YES (C5 predicted ≥ 0.10; C6 predicted no regression) |
| itoshi_rin      | 0.112 → **0.112** ✓ | 0.086 → **0.222** ✓ | 0.112 → **0.112** ✓ | 0.084 → **0.219** ✓ | YES (C5 untouched; C6 predicted ≥ 0.10) |
| chigiri_hyoma   | untouched → **0.105** ✓ | untouched → **0.176** ✓ | untouched → **0.106** ✓ | untouched → **0.177** ✓ | YES (untouched; must stay ≥ 0.10) |
| barou_shoei     | 0.068 → **0.254** ✓ | 0.154 → **0.154** ✓ | 0.118 → **0.151** ✓ | 0.154 → **0.183** ✓ | YES (C5 predicted ≥ 0.10 arm4; phi41 depended on Phase Y — clears anyway via SL channel) |
| nagi_seishiro   | 0.000 → **0.259** ✓ | 0.000 → **0.000** ✗ | 0.000 → **0.246** ✓ | 0.000 → **0.000** ✗ | Pre-reg N/A — Nagi C6 requires re-gate (fresh borrowed provenance) |
| reo_mikage      | waived | waived | waived | waived | untouched |

All predictions in `dispersion_primitives_r2/PROTOCOL.md` §3 are met on the
pre-check. No regressions observed on any previously-passing dispersion
criterion. Nagi's C6 remains at 0.000 exactly as pre-registered (his fix
requires freshly stamped leader `atr_pips` / `h1_swing_pips`, which only
lands on the §11.15 re-gate walk-forward).

## Mechanism-level attribution

- **Isagi C5 (0.086 → 0.205):** `conservative_metavision` switched from
  `conviction_scaled` to `risk_normalised` at doctrine anchor SL ≈ 40.
  Sizing now responds to `sl_pips` variation via the inverse-SL factor.
- **Isagi C6 (0.083 → 0.178):** F20 replaced the damped 0.25× ATR
  sensitivity with full ATR proportionality (`atr_scaled_risk_intent`,
  `atr_multiplier=1.3`, `payoff_ratio=1.5`, sl_min/max 30/50).
- **Bachira C5 (0.089 → 0.476):** `rebel_tight` switched to
  `risk_normalised` at doctrine anchor SL ≈ 20. The single-agent effect
  is very large because Bachira's `source_sl_pips` panel spans 15–25 (band
  matches the 0.5–2.0 ratio-clip perfectly).
- **Rin C6 (0.086 → 0.222):** structural stop de-saturated
  (`sl_swing_fraction 0.30 → 0.20`, `sl_pips_max 30 → 35`). Panel mean SL
  moves off the 30-pip ceiling into the band.
- **Barou C5 (0.068 → 0.254 phi41; 0.118 → 0.151 arm4):** `solo_king`
  switched to `risk_normalised` at doctrine anchor SL ≈ 30. Sizing now
  responds to Barou's real SL variation (banked panel spans 15–45 pips).
- **Nagi C5 (0.000 → 0.259):** even without leader-borrowed provenance,
  the amended `risk_normalised` primitive gives Nagi's F19 output a real
  SL channel because his cached `source_sl_pips` vary trade-to-trade with
  the borrowed leader geometry. The banked cache's `source_regime_fit =
  0.5` (placeholder) and `source_conviction` (F11-combined) still feed the
  primitive, but the inverse-SL factor is enough on its own to clear 0.10.
- **Nagi C6 (0.000 → 0.000):** unchanged on the banked cache because
  `source_atr_pips` on Nagi's trades is `None` (leader stamp on
  `coord.rationale` did not exist in the OLD code), so the evaluator falls
  back to the constant 30.0. Fixed on the re-gate replay by the new
  `stamp_provenance_pips(coord.rationale, ...)` calls on all 5 bar-having
  leaders + Nagi's `intend()` borrow, together landing in commit `2bf5194`.

## Not affected by dispersion-r2 (documented negatives)

- Bachira C3 (0/7 windows clean on phi41; 1/7 on arm4). The dispersion-r2
  lever does NOT touch C3, which is the pre-registered known duplication
  artifact (§11.13 discussion item 1). C3 v2 (§11.14, advisory) is a
  separate ratification path.
- Chigiri C1 (0.267 mean TQS) and C2 (no peer clears the CI gate). C1/C2
  are pre-registered as Phase Y / role-registry territory; dispersion-r2
  makes no prediction here.
- Barou C1 (CI lower 0.247 ≤ 0.25 at n=62 phi41; passes at n=322 arm4).
  Barou's C1 is Phase Y's territory (weapon v1.3 changes his trade
  stream); dispersion-r2 makes no prediction here.

## Conclusion

Dispersion-r2 primitives PASS the pre-check against every pre-registered
prediction on both aggregators. No re-tuning; constants stay frozen at
commit `0a97835` (protocol) / `2bf5194` (implementation + tests). The
verdict-bearing numbers for the second gate attempt are the §11.15 re-gate
replays which run next.
