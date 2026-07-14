# Phase Y — Barou v1.3 weapon differentiation (pre-registration)

- **Registered:** 2026-07-14 (committed BEFORE any result is computed).
- **Program:** M001 multi-agent ensemble.
- **Authorization:** user authorized Phase Y 2026-07-14 (it was parked at Phase W-barou v1.2 HALT, POSTMORTEM_v1.2.md §4).
- **Evaluation vehicle:** the G7 re-gate replays pre-registered in G7 PROTOCOL §11.15 — the OOS windows are touched exactly once, jointly for Phase Y + dispersion-r2 + the new gate attempt.

---

## 1. Problem (banked evidence)

Phase W-barou v1.2 (HALT, 2026-07-06): Bachira and Barou wrap the SAME
`SupplyDemandAlpha(htf_align=None, target_rr=1.5)`; on USDCAD they are
the same strategy with different narratives. Consequences in §11.13:
Bachira C3 = 0/7 clean windows (phi41); Barou starved under phi41
(62 OOS trades, C1 CI lower 0.247 <= 0.25). The v1.2 postmortem's only
honest fix: "give Barou a genuinely different USDCAD weapon (different
cell parameters, different signal family)".

## 2. Design (doctrine + banked evidence ONLY — no OOS peeking)

Barou v1.3 weapon: **D1 with-trend continuation on baseline zones with
structural targets and wide invalidation**, USDCAD only.

Locked parameters (`BAROU_V13_PARAMS`):

| Param | Value | Source (no new tuning) |
|---|---|---|
| `htf_align` | `"D1"` | Roster §3.7 canon: Barou is "USDCAD-locked H4 **trend continuation**" |
| `htf_align_mode` | `"with"` | Same canon; mirrors Isagi's gate with the mode flipped |
| `htf_lookback` | `10` | Copied verbatim from Isagi's locked E001-derived cell (`ISAGI_V1_PARAMS`) |
| `htf_min_move_pips` | `60.0` | Same — copied verbatim, zero re-tuning |
| `target_via_structure` | `True` | Canon "solo king finishes the full move"; shipped production mode with shipped defaults |
| `structural_lookback` | `200` | Production default of `SupplyDemandAlpha` |
| `min_structural_rr` | `1.0` | Production default |
| `target_rr` | `1.5` | Unchanged fallback when no structural target exists |
| `stop_atr_mult` | `1.0` | Canon "wide invalidation — the king gives the strike room"; 2× the production default 0.5, a qualitative doubling, not a searched value |

Empirical basis (all banked):

- E005 side-note (audit 2026-06-24 §4.3): on USDCAD, baseline `zone`
  (no D1 gate) beats `zone_d1_against` — i.e. the with-trend complement
  subset (the trades the against-gate removes) contributed POSITIVELY
  on USDCAD. Barou v1.3 trades exactly that complement.
- E001: with-trend gating destroyed the edge **on EURUSD**. Barou is
  locked to USDCAD, where the E005 asymmetry is inverted. This tension
  is acknowledged: the EURUSD negative is a prior AGAINST this design
  generalising, which is why Barou stays single-symbol.
- Phase W v1.2: geometry-identity is the root cause; v1.3 changes all
  three geometry legs (fire set via the gate, stop via `stop_atr_mult`,
  TP via structural targets) so no Barou trade can be a §2.1
  (c3_v2_distinctness PROTOCOL) duplicate of a Bachira trade.

Kept unchanged: USDCAD-only whitelist, devour mechanic (§11.5 constants),
v1.1 lone-conviction lift, v1.2 continuation-entry (still default OFF),
playstyle `solo_king`, tier 2.

Expected side effect (stated up front): Isagi's against-gate and Barou's
with-gate are mutually exclusive on the same tick, so the devour lift
(triggered by Isagi disagreement) will fire on prior-tick Isagi thoughts
only and may become rarer. This is canon-consistent (the king strikes
where Isagi's read fails) and is NOT a failure criterion.

## 3. Implementation plan

- `sim/agents/a07_barou.py`: add `BAROU_V13_PARAMS`; constructor flag
  `weapon_v13: bool = True` (legacy v1 weapon retained behind
  `weapon_v13=False` for cache-reproduction tests). Rationale stamps
  `weapon: barou_v13` + the params dict.
- Harness: `run_g7_v1_checkpoint_gate.py` + `run_g7_leave_one_out.py`
  instantiate Barou with the v1.3 default (a `--barou-legacy-weapon`
  escape hatch is NOT added; sealed §11.13 caches are on disk and are
  never regenerated).
- Unit tests BEFORE results: (a) v1.3 params reach the inner alpha;
  (b) `weapon_v13=False` reproduces the v1 fire set on a fixture;
  (c) with-gate and against-gate are disjoint on a synthetic series;
  (d) structural-TP + wide-stop produce different stop and TP from
  Bachira's cell on the same synthetic signal tick.

## 4. Success criteria (locked; evaluated ONCE on the §11.15 re-gate replays)

Baselines referenced below are the §11.13 numbers (phi41 / arm4).

- **Y1 — geometric distinctness (manipulation check):** share of
  Barou's trades in the lo1-Bachira replay whose full trade-plan key
  (c3_v2 §2.1, incl. stop + TP) matches a Bachira baseline trade
  **< 20 %** (was ~100 % per Phase W). Report alongside the entry-only
  overlap share (same tick + entry + direction) as audit.
- **Y2 — Bachira C3 v2 (advisory):** >= 4/7 clean windows in at least
  one arm.
- **Y3 — Bachira C3 v1 improvement:** clean windows strictly greater
  than §11.13 (phi41: > 0/7; arm4: > 1/7) in the corresponding arm.
- **Y4 — no squad regression:** squad mean-of-window-mean TQS within
  **−0.02** of the §11.13 baseline in each arm.
- **Y5 — Barou activity floor:** >= 30 Barou OOS trades (phi41). Below
  30, C1's bootstrap CI is structurally starved — reported as a
  capacity failure of the weapon.

**Phase verdict:** PASS iff Y1 AND Y4 AND (Y2 OR Y3). Anything else is
reported as FAIL or PARTIAL with the failing criteria named. Barou's
own C1/C5/C6 movements are reported in the §11.15 gate table, not
duplicated here.

## 5. Stop rules / anti-leakage

1. One evaluation. If the pre-registered criteria fail, the lever STOPS
   — no parameter iteration against the same OOS windows. A second
   attempt requires a fresh protocol flagged as attempt #2 with
   multiplicity noted.
2. No post-freeze retuning of `BAROU_V13_PARAMS` after this commit.
3. If the walk-forward replays diverge (heartbeat stall / crash), fix
   infra and rerun — infra reruns are not analysis iterations.

## 6. Artifacts

- Verdict: `reviews/phase_y_verdict.md` (+ numbers in the §11.15 gate
  report). EXPERIMENTS.md + ai_context.md rows on completion.
