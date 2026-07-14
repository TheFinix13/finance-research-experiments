# Phase AB — Barou v1.3 multi-pair scope reversal (pre-registration)

- **Registered:** 2026-07-14 (committed BEFORE any result is computed).
- **Program:** M001 multi-agent ensemble.
- **Authorization:** user authorized a four-lever third-attempt campaign
  2026-07-14. This lever is the §11.16 standing-decision candidate
  *"multi-pair Barou reversal of the Phase Y USDCAD-only scope, with a
  real pre-registered acceptance test"*, now with canon guidance:
  *"Barou steals and chop-dribbles, stealing the plays of Isagi or
  others who notice Isagi's plays like Rin."*
- **Lever slot:** Lever B of the G7 §11.17 third-attempt campaign.
  Target blocker: **Barou C1 fail under phi41** (§11.16: panel mean
  0.283 < 0.30 at n = 43; CI [0.177, 0.397] — volume-starved; arm4
  companion passes at n = 86, mean 0.380).
- **Evaluation vehicle:** the G7 re-gate replays pre-registered in G7
  PROTOCOL §11.17 (tag `g7retry2`) — OOS touched exactly once, jointly
  for all four campaign levers.

---

## 1. Problem (banked evidence)

Phase Y v1.3 gave Barou a genuinely distinct weapon (D1 with-trend
gate + structural TP + wide stop) but kept the USDCAD-only whitelist.
Under phi41 that weapon fires so rarely that his OOS volume FELL from
62 (§11.13) to 43 (§11.16); his mean TQS (0.283) and CI lower bound
never stabilise at that n. The §11.16 discussion names the fix
category explicitly: widen his panel. Doctrine §3.11.3 A7 mechanic B
(the 2026-06-30 user-decided hybrid) had already pre-registered the
same direction: *"Barou's symbol whitelist expands from ("USDCAD",) to
("USDCAD", "EURUSD", "GBPUSD") … explicitly to contest Bachira's slot
dominance"* — deferred at Phase Y for single-variable hygiene, now
activated.

## 2. Canon → mechanism mapping (doctrine + banked evidence ONLY)

Canon: the king claims the WHOLE pitch, not one wing. Barou's §3.7
USDCAD lock was an empirical concession (E005 asymmetry), not canon —
canon Barou plays anywhere and *steals* the play. The v1.3 weapon (D1
with-trend continuation, structural targets, wide invalidation) is the
king's own read; this lever deploys the SAME locked weapon on all
three panel pairs.

**Change (single variable):**
`BAROU_V1_SYMBOLS: ("USDCAD",) → ("USDCAD", "EURUSD", "GBPUSD")`.
`BAROU_V13_PARAMS` byte-unchanged. Roster/canon annotations updated.

**Home-ground privileges (locked):** the devour lift (+0.20 on Isagi
disagreement) and the v1.1 lone-conviction lift (+0.10) remain
**USDCAD-only**, per the doctrine §3.11.3 A7 mechanic-B letter ("the
devour lift remains USDCAD-only — EURUSD/GBPUSD slice runs raw").
On EURUSD/GBPUSD Barou proposes at the weapon's base conviction. This
keeps the expansion from importing new conviction-race pathologies
onto Isagi's home ground.

Empirical priors (banked, honestly stated):

- **Prior AGAINST, named up front:** E001 found with-trend D1 gating
  destroyed the zone edge **on EURUSD** — the exact subset Barou will
  now trade there. Phase Y §2 cited this as the reason to stay
  single-symbol. This lever knowingly trades against that prior on
  EURUSD/GBPUSD because (a) the §11.16 evidence shows the USDCAD-only
  weapon cannot reach C1 volume under phi41, and (b) the E001 negative
  was measured on the RR=1.5 fixed-TP cell, not the v1.3 structural-TP
  + wide-stop geometry — a real but unverified difference. The
  per-symbol TQS split is a mandatory audit output; if the
  EURUSD/GBPUSD slice is the E001 story replayed, criterion AB2 fails
  and the lever stops.
- **Prior FOR:** §11.16 arm4 shows the v1.3 weapon's mean TQS at
  0.380 (n=86) when volume doubles — the weapon's per-trade quality is
  not the problem; starvation is.
- Slot-contention prior: Barou enters EURUSD/GBPUSD against
  Isagi/Rin (D1-against — structurally disjoint from his with-gate on
  the signal tick), Bachira (D1-neutral under the campaign's Phase Z —
  also disjoint), and Chigiri (breakout family — can collide). His own
  C3 (currently 7/7 clean) and peers' C3 vs him are guarded below.

**Steal mechanic — designed but NOT shipped.** The user's canon
("steals the plays of Isagi, or of those who notice Isagi's plays,
like Rin") suggests an F21 read where an Isagi/Rin fired thought on
EURUSD/GBPUSD seeds a Barou "steal" entry variant (e.g. Barou takes
the with-trend continuation of the move Isagi faded, after Isagi's
stop side is taken out). There is **no banked expectancy evidence**
for that trigger subset, and designing its thresholds now would be
invention, not derivation. Per the campaign instruction it is recorded
here as a designed-but-untested follow-up (would need its own
pre-registration + fresh OOS discipline); Phase AB ships the plain
scope reversal only.

## 3. Implementation plan

- `sim/agents/a07_barou.py`: `BAROU_V1_SYMBOLS` extended; devour +
  lone-conviction lifts gated on `market.symbol == "USDCAD"`
  (`BAROU_HOME_SYMBOL`). Rationale stamps `barou_home_ground` bool.
  No constructor flag: symbol scope is roster state, and the sealed
  caches are never regenerated (the legacy scope remains reproducible
  by passing `symbols=["USDCAD"]`, already a constructor parameter).
- Harness: unchanged (agents are instantiated with default symbols).
- Unit tests BEFORE results: (a) v1.3 weapon fires on a prepared
  EURUSD fixture (whitelist honoured); (b) devour lift does NOT apply
  on EURUSD even when Isagi disagrees; (c) lone-conviction lift does
  NOT apply off-USDCAD; (d) both lifts still apply on USDCAD
  (regression); (e) legacy single-symbol construction still abstains
  off-USDCAD.

## 4. Success criteria (locked; evaluated ONCE on the §11.17 re-gate replays)

Baselines referenced below are the §11.16 `g7retry1` numbers.

- **AB1 — volume floor:** Barou ≥ 100 OOS trades under phi41 (was 43).
- **AB2 — C1 pass (primary):** Barou C1 passes under phi41: panel mean
  TQS ≥ 0.30 AND ≥ 5/7 windows ≥ 0.20 AND bootstrap CI lower > 0.25.
- **AB3 — no self-regression:** Barou keeps C3 (≥ 4/7 clean; was 7/7)
  and C5/C6 passes under phi41.
- **AB4 — no peer C3 poisoning:** no OTHER agent's C3 flips pass→fail
  in either arm with Barou's expansion as the worst-peer cause (i.e.
  `barou_shoei` appearing as the dirty-window worst peer).
- **AB5 — no squad regression:** squad mean-of-window-mean TQS within
  −0.02 of §11.16 in each arm (shared campaign tolerance).
- **Audit (non-decisive):** per-symbol n/mean-TQS split for Barou; the
  EURUSD slice explicitly compared against the E001 negative prior.

**Phase verdict:** PASS iff AB1 AND AB2 AND AB3 AND AB4 AND AB5.
Anything else is FAIL or PARTIAL with the failing criteria named.

## 5. Stop rules / anti-leakage

1. One evaluation. Failure STOPS the lever — no scope re-slicing
   (e.g. dropping GBPUSD post-hoc) against the same OOS windows.
2. No post-freeze retuning of `BAROU_V13_PARAMS`; the steal mechanic
   ships nothing in this phase.
3. Infra reruns are not analysis iterations.

## 6. Multiplicity note

Third Barou-directed lever (Phase W v1.1 NULL, Phase W v1.2 HALT,
Phase Y v1.3 partial — C5 fixed, C1 regressed on volume) inside the
THIRD G7 gate attempt. The direction was pre-surfaced by §11.16's
standing decisions and by doctrine §3.11.3 A7 mechanic B (2026-06-30)
— it is a scope reversal of a deferred pre-registered design, not a
post-hoc search. No G7 threshold is touched. See G7 §11.17.

## 7. Artifacts

- Verdict: `reviews/phase_ab_verdict.md` (+ numbers in the §11.17 gate
  report). EXPERIMENTS.md + ai_context.md rows on completion.
