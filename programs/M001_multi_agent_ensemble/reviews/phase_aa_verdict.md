# Phase AA verdict — Chigiri v1.4 panther-ignition weapon (Lever C, §11.17 campaign)

- **Protocol:** `experiments/phase_aa_chigiri_ignition/PROTOCOL.md`
  (registered 2026-07-14, committed before implementation results).
- **Evaluated:** 2026-07-15 on the §11.17 `g7retry2` replays (single
  pre-registered OOS touch). Baselines are the §11.16 `g7retry1` numbers.
- **Evidence:** `reviews/g7_v1_checkpoint_final_g7retry2-{phi41,arm4}.{md,json}`,
  `reviews/g7retry2_lever_audits.json`.

## Verdict: **FAIL (AA1, AA2, AA-M)**

Per the locked letter (§4): PASS iff AA1 AND AA2 AND AA3 AND AA4.
Both primaries fail, and the mechanism check fails with them.

| Criterion | Locked threshold | Result | Pass |
|---|---|---|---|
| AA1 — C1 pass (primary) | mean TQS ≥ 0.30, ≥ 5/7 windows ≥ 0.20, CI low > 0.25, n ≥ 200 | mean **0.2386** (was 0.267), 6/7 windows ≥ 0.20, CI low **0.2066**, n = 503 | ❌ |
| AA2 — C2 pass (primary) | ≥ 1 qualifying peer under phi41 | **none** (all six peer deltas non-qualifying; trade-count deltas mostly negative) | ❌ |
| AA-M — mechanism check | mean entry-efficiency component strictly > §11.16 value | **0.2775 vs 0.2904** — decreased (arm4: 0.2788 vs 0.2916) | ❌ |
| AA3 — no self-regression | keeps C3/C4/C5/C6 | C3 7/7, C4 1231, C5 0.1163, C6 0.1591 — all pass | ✅ |
| AA4 — no squad regression | within −0.02 of §11.16 per arm | phi41 Δ −0.0112; arm4 Δ −0.0141 (shared campaign movement) | ✅ |

## What the numbers say about the mechanism (honest read)

The ignition-thrust gate did exactly what it mechanically promised —
earlier, more frequent entries (n 296 → 503; volume was the one
dimension that improved) — and the market paid less for them:

- Mean TQS **fell** 0.267 → 0.2386. The removed 0.5-ATR magnitude
  hurdle was doing real quality-selection work that the thrust gate
  does not replicate.
- Entry efficiency (the exact component the canon story predicted
  would improve) **fell** 0.2904 → 0.2775. The "first to the move"
  entries are, on average, slightly *worse*-placed than the
  confirmation-taxed v1 entries. The '44-panther speed premium did not
  survive contact with H4 data.
- No C2 lift emerged: peers do not measurably join the moves Chigiri
  enters early (his removal helps nobody and hurts nobody at the
  CI-gated letter).

## Consequences per stop rules

- Phase AA **STOPS** (protocol §5 rule 1): no thrust-ratio or window
  iteration against the same OOS windows. The pre-registered prior
  AGAINST (doctrine §3.11.3 A4 said Chigiri needed *stricter*, not
  looser, entry filtering) is the better-supported hypothesis after
  this result.
- Chigiri C1 is now 0/7-window-passing at the 0.30 panel bar in the
  raw stat and his bit vector is unchanged (`001111`). Any future
  Chigiri lever should start from the A4 strict-filter direction, in
  a fresh protocol flagged as attempt #2 with this failure cited.

## Status of the code

`weapon_ignition=True` is the committed default that produced these
replays. Given the clean FAIL, the recommended adoption call at the
§11.18 review is to **revert the default to the v1 magnitude hurdle**
(one-parameter change; both behaviours are pinned by unit tests).
Awaiting the user's call; no code has been changed post-evaluation.
