# C3 v2 — distinctness-aware non-cannibalisation criterion (pre-registration)

- **Registered:** 2026-07-14 (this file committed BEFORE any C3 v2 number is computed).
- **Program:** M001 multi-agent ensemble.
- **Parent gate:** `experiments/G7_v1_checkpoint_gate/PROTOCOL.md` §3 Criterion 3; formal amendment logged as G7 §11.14.
- **Status of verdicts under this definition:** **ADVISORY ONLY** until the user ratifies the §11.14 amendment. C3 v1 remains the verdict-bearing definition for any G7 gate attempt until ratification.

---

## 1. Motivation (from banked evidence only)

Phase W-barou v1.2 (POSTMORTEM_v1.2.md, 2026-07-06) established that
`A2BachiraV1` and `A7BarouV1` wrap the SAME production
`SupplyDemandAlpha(htf_align=None, target_rr=1.5)`: on all 4,576 shared
USDCAD ticks, entry, stop and TP are identical to full float precision.
Bachira's C3 v1 FAIL (0/7 clean windows, §11.13) is therefore a
measurement artifact: the "suppressed" Barou trades recovered when
Bachira is removed are the SAME trades relabelled, not suppressed
independent alpha. C3 was designed to detect suppression of a peer's
*distinct* alpha (doctrine §3.11.5 criterion 3: "slot cannibalisation");
literal duplication is an agent-identity problem, not slot behaviour.

## 2. Definition (locked BEFORE evaluation)

### 2.1 Trade-plan identity key

Two trades are **duplicates** iff ALL of the following match:

- `symbol`
- `direction`
- `source_tick_id`
- `entry` rounded to 7 decimal places
- `stop` rounded to 7 decimal places
- `take_profit` rounded to 7 decimal places

Rationale: a trade *plan* is (entry, stop, take-profit) at a tick. Phase
W measured full-float identity on all contested ticks, so a 1e-7
rounding tolerance (0.001 pip) is conservative and immune to JSON
round-trip noise. The key deliberately includes TP: two agents entering
at the same tick/price with different invalidation or target structure
are expressing DIFFERENT alpha (different exit distribution) and must
not be netted out.

### 2.2 C3 v2 statistic

For excluded agent `a` (the agent under C3 evaluation), peer `p`,
window `w`:

1. Let `D(a)` = the set of trade-plan keys (§2.1) of **`a`'s trades in
   the BASELINE run** (full squad).
2. A trade of peer `p` is **distinct** iff its key ∉ `D(a)`.
3. `base_distinct(p, w)` = count of `p`'s distinct trades in window `w`
   of the baseline run; `lo1_distinct(p, w)` = same in the
   leave-one-out-`a` run.
4. Reduction ratio (same guard as the v1 final evaluator):

   `r_v2(p, w) = (lo1_distinct − base_distinct) / lo1_distinct`, with
   `lo1_distinct <= 0 → 0.0`.

5. Window `w` is **clean** iff `max_p r_v2(p, w) <= 0.50`.
6. **Pass iff clean windows >= 4 of 7** (identical thresholds to v1 —
   only the trade universe changes; no threshold is being retuned).

Interpretation: trades peer `p` only takes when `a` is absent AND which
are literal copies of `a`'s own baseline trade plans are re-attribution,
not suppressed peer alpha; they are removed from both sides of the
ratio. Everything else is unchanged from C3 v1
(`run_g7_final_verdict.evaluate_c3_final`).

### 2.3 Reported alongside (audit-only, not decisive)

- Per (agent, peer): duplicate share of the peer's lo1 trades
  (`|{lo1 trades of p with key ∈ D(a)}| / |lo1 trades of p|`).
- C3 v1 and v2 side by side for every agent, both aggregator arms.

## 3. Evaluation plan (single computation, banked caches)

- **Inputs:** the §11.13 banked caches only — phi41:
  `reviews/g7_replay_cache_walk-forward-post-kunigami-retirement` +
  `reviews/g7_leave_one_out_post-V/lo1_*`; arm4:
  `reviews/g7_replay_cache_phi5-arm4-post-kunigami` +
  `reviews/g7_leave_one_out_phi5-arm4/lo1_*`. No new replay compute; no
  new OOS touch (these caches are already-banked §11.13 evidence).
- **Evaluator:** new pure function(s) in
  `sim/scoring/run_g7_final_verdict.py` (or a sibling module) +
  unit tests, committed BEFORE the evaluation is run.
- **Output:** `reviews/c3_v2_side_by_side_<arm>.md` (+ `.json`), one row
  per agent: v1 clean windows, v2 clean windows, v1 pass, v2 pass,
  worst-peer duplicate share.
- The same evaluator runs again on the re-gate caches (G7 §11.15) as the
  advisory companion.

## 4. Predictions (falsifiable, stated before evaluation)

- Bachira (phi41): v1 = 0/7; v2 expected >= 4/7 (the Barou reductions
  are ~100 % duplicates per Phase W). If v2 stays < 4/7, the
  duplication story is INCOMPLETE and Bachira's C3 failure has a real
  cannibalisation component — report as such.
- All agents whose C3 v1 already passes: v2 expected identical or
  better (v2 removes only duplicate trades from the universe; an agent
  with no duplicate-alpha peer is untouched). Any v2 DEGRADATION is an
  implementation bug — stop and diagnose.

## 5. Stop rules

1. If v2 degrades any v1-passing agent (see §4), halt and diagnose
   before reporting.
2. No threshold iteration: 0.50 / 4-of-7 / the §2.1 key are locked. Any
   change is a fresh amendment with multiplicity noted.

## 6. What requires user ratification

Adopting C3 v2 as the verdict-bearing definition for G7 (replacing or
complementing v1) is a gate-definition change; per repo norms the
verdicts computed here are advisory until the user ratifies G7 §11.14.
