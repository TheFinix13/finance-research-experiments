# v2 Arc backlog resolution — Round 2: Bachira · Rin · Chigiri · Reo

| Field | Value |
|---|---|
| **Date** | 2026-06-30 |
| **Status** | applied — doctrine + roster + ledger updates land in the same commit |
| **Author** | orchestrator |
| **Phase context** | Post-Φ4.1 FAIL (squad TQS 0.292 = 0.92× Isagi-alone) + Φ5-aggregator + Sentinel-Φ4.2 in flight |
| **Branch** | `multi-agent-ensemble` |
| **Predecessor** | `reviews/v2_arc_backlog_resolution_2026-06-25.md` (Nagi DROP / Barou REDESIGN-hybrid-A+B / Kunigami DEFER) |
| **Trigger** | C-Q5 user decision 2026-06-30: revise v2 sketches for the four agents that gained Φ4.1 empirical state in the expanded squad |

This document is the round-2 resolution brief for the four §3.11.3
v2 sketches that pre-dated Φ4.1 empirical evidence and are now
covered by the Φ4.1 run telemetry. Each section ends with **exact
replacement text** for `06-blue-lock-doctrine.md` §3.11.3 and the
matching evolution-ledger row.

Round-1 (2026-06-25) closed Nagi/Barou/Kunigami. This round closes
**A2 Bachira / A3 Rin / A4 Chigiri / A5 Reo**. A8 Yukimiya and A9
Aoshi remain unimplemented (no Φ4.1 telemetry) — their pre-Φ4.1
sketches in §3.11.3 are not revised here. A1 Isagi is on its own
arc and was resolved in the 2026-06-24 Isagi-v2 FAIL.

---

## TL;DR

| Agent | Pre-Φ4.1 v0.3 sketch | Φ4.1 reality | Round-2 verdict | One-line revised hypothesis |
|---|---|---|---|---|
| **A2 Bachira** | "patterns fire only on peer-silence" | rebel-lift fired **46,584 times unconditionally**; Bachira fired **2,840 trades** (76 % of squad), slot-cannibalising Isagi + Barou everywhere | **REFINE-to-peer-silence** — the v0.3 spirit was correct but v1 implementation is the opposite (peer-saturation, not peer-silence) | Narrow rebel-lift to fire only when (a) no Isagi/Barou prior-tick Thought at conviction ≥ 0.70 on the same symbol OR (b) peer Thought is strongly contradictory (recent-opposite-swing × peer-disagreement) |
| **A3 Rin** | "regime-gate to {trending, vol_spike}, never chop" | 244 trades, mean +9.95 / **median −28.26** pips, TQS 0.277; precision-lift fired 3,094 times; right-tail concentrated | **REFINE-regime-and-peer-disagreement** — gate per the post-redesign live-classes (trending only; vol_spike + news retired) AND require peer-disagreement (fire when Chigiri/Bachira propose contrary direction) | Precision-lift fires only when (a) regime ∈ {trending} per live-classes-only classifier AND (b) at least one peer (Chigiri or Bachira) has a contrary-direction Thought at conviction ≥ 0.65 on the same bar |
| **A4 Chigiri** | "continuation-only of confirmed breakouts, never retest" | 536 trades, +6.62 mean / **−26.67 median** pips, TQS 0.229; breakout-firing thoughts 3,615; H1-ADX-rising filter already in v1 | **REFINE-multi-TF-ADX-and-ATR-percentile** — v0.3 already shipped (continuation-not-retest is v1 behaviour); v2 layers stricter regime-gate to escape whipsaws | Continuation-firing requires (a) M15-ADX × H1-ADX × H4-ADX all rising on the same bar AND (b) realised σ_M15 in the top-decile of trailing 80-bar distribution (was top-quartile in v1) |
| **A5 Reo** | "HRP-weighted mixture of top-K trailing-TQS agents, K ≥ 2 enforced" | 0 trades / **28,469 mirror Thoughts** emitted; structural Tier-2 falsifier validated | **ADVANCE-coupled-to-Φ5-multi-position** — original HRP-weighted mixture stands; Φ4.1 surfaces a new role tied to the Φ5 multi-position policy | HRP-weighted mixture of top-K (≥ 2) trailing-TQS agents AND second-position proposer when a first-leader's slot is contested under the Φ5 multi-position aggregator (Arm 4 / K = 2) — Reo becomes the agent that fills the second slot to break slot-cannibalisation |

---

## Section 1 — A2 Bachira v2 — verdict `REFINE-to-peer-silence`

### 1.1 Verdict

**REFINE.** The v0.3 sketch ("patterns trigger only on peer-silence")
captured the right spirit but the v1 implementation does the
**opposite** — Bachira's `+0.10` rebel-lift fires **unconditionally**
on the recent-opposite-swing trigger, regardless of peer activity.
v1 is peer-**saturation**. v2 inverts to peer-**silence-conditional**.

### 1.2 Empirical justification

| Metric | Φ4 (4-agent MVP — Bachira not in MVP) | Φ4.1 (8-agent expanded) | Implication |
|---|---|---|---|
| Bachira trades opened | n/a | **2,840** (76 % of squad's 3,714 trades) | dominant — far above any other striker |
| Mean pips / trade | n/a | **+9.97** | edge present at mean level |
| Median pips / trade | n/a | **+14.21** | uniquely median-positive in the Φ4.1 squad (only one of 4 trading agents with positive median) |
| Mean TQS | n/a | **0.308** | mid-pack |
| Win % | n/a | 50.9 % | barely-above-coin-flip — wins are concentrated, losses are frequent |
| Rebel-lift Thoughts emitted | n/a | **46,584** | unconditional fire on recent-opposite-swing trigger |
| Isagi trades (Φ4.1) | n/a | **0** (slot-cannibalised) | direct evidence of the v0.3 problem class — Bachira occupies every Isagi-eligible slot |
| Barou trades (Φ4.1) | n/a | **0** (slot-cannibalised) | same — Bachira occupies every USDCAD slot Barou would have proposed |

Source: `reviews/phi41_squad_v1.md` per-agent KPI table + engine
telemetry "Bachira rebel lifts applied: 46584"; `reviews/phi41_
squad_v1_addendum.md` §1 (structural crowding-out — Isagi 0,
Barou 0); `reviews/phi41_isagi_rejection_analysis.md` (87.5 % of
Isagi rejections were same-direction with another agent's accepted
proposal — the fingerprint of crowd-out).

**Root cause.** The v1 rebel-lift was specified pre-Φ4.1 with the
goal of "fuelling Nagi's confluence floor". It succeeded
(34,302 confluence thoughts) but at the cost of dominating the
aggregator queue. The mechanic is not "broken"; it is **mis-
specified for the post-Φ4.1 reality** where multiple strikers share
the baseline-zone primitive on the same symbols.

### 1.3 Revised v2 hypothesis

Bachira's `+0.10` rebel-lift fires only when **at least one** of:

1. **Peer-silence:** no Isagi or Barou prior-tick Thought at
   conviction ≥ 0.70 on the same symbol exists.
2. **Peer-disagreement:** at least one peer (Isagi, Barou, Rin)
   has a prior-tick Thought at conviction ≥ 0.65 going the
   **opposite direction** on the same symbol.

If neither condition holds, Bachira's base baseline-zone Thought
remains at conviction 0.65 (unchanged from v1). The rebel-lift to
0.75 is reserved for the empirically-rare cases the v0.3 sketch
envisioned.

### 1.4 Revised defeat trigger

Bachira v2's per-OOS-window trade count drops below 200 OR
Bachira's mean TQS regresses below 0.25 (Φ4.1 was 0.308) across
≥ 4 of 7 rolling OOS windows. The first threshold protects against
over-tightening; the second protects against an under-performing
v2. Either trips → v2 defeat → revert to v1 rebel-lift policy with
a documented decision in `reviews/bachira_meguru_v1_defeat.md`.

### 1.5 Exact replacement text — `06-blue-lock-doctrine.md` §3.11.3 (A2 Bachira bullet)

Replace the existing **A2 Bachira v1 → v2 — releasing the monster**
bullet with:

```
- **A2 Bachira v1 → v2 — narrowed rebel-lift (peer-silence /
  peer-disagreement-conditional).** *Defeat (Φ4.1):* v1 rebel-lift
  fired 46,584 times unconditionally, slot-cannibalising Isagi
  (0 trades) and Barou (0 trades) across all three Φ4.1 symbols
  and producing 76 % of squad trades (2,840 / 3,714). The v0.3
  sketch's spirit ("peer-silence") was correct but v1 implements
  the opposite (peer-saturation). *v2 hypothesis:* the rebel-lift
  from 0.65 to 0.75 fires only when (a) no Isagi/Barou prior-tick
  Thought at conviction ≥ 0.70 exists on the same symbol OR (b)
  at least one peer (Isagi/Barou/Rin) has a prior-tick Thought
  at conviction ≥ 0.65 going the OPPOSITE direction on the same
  symbol. Otherwise Bachira's base baseline-zone Thought stays at
  0.65. *Defeat trigger:* Bachira v2 per-OOS-window trade count
  drops below 200 OR Bachira's mean TQS regresses below 0.25
  (Φ4.1 was 0.308) across ≥ 4 of 7 rolling OOS windows. Resolution
  detail: `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md`
  §1.
```

### 1.6 Evolution-ledger row

```
| 2026-06-30 | Φ4.1 post-mortem (round-2; no co-existence; refinement-level update) | A2 Bachira (`bachira_meguru`) | v1 → v2 sketch refined | **Defeat (Φ4.1):** v1 rebel-lift fired 46,584 times unconditionally; slot-cannibalised Isagi + Barou (0 trades each); produced 76 % of squad's 3,714 trades. v0.3 sketch's peer-silence spirit was correct; v1 inverts to peer-saturation. | Narrow rebel-lift to peer-silence OR peer-disagreement gated trigger; base conviction 0.65 elsewhere. | Pending v2 implementation (Φ5 aggregator work may obviate via HRP downweighting; revisit ordering after Φ5 verdict). | **REFINE-to-peer-silence** — pending v2 implementation. See `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §1. |
```

### 1.7 Interaction with Φ5

If the Φ5 aggregator's HRP arm (Arm 1) materially down-weights
Bachira's risk allocation due to TQS-covariance with Isagi, the
slot-cannibalisation problem partially dissolves at the
aggregator layer rather than the agent layer. The v2 sketch above
remains the agent-side fix and stays valid; but the priority of
shipping it depends on Φ5's verdict. Decision tree:

- If Φ5 PASS via HRP alone → defer Bachira v2 (problem is solved
  at the aggregator).
- If Φ5 PARTIAL or FAIL → ship Bachira v2 as part of Φ5.5 or Φ6.

---

## Section 2 — A3 Rin v2 — verdict `REFINE-regime-and-peer-disagreement`

### 2.1 Verdict

**REFINE.** The v0.3 sketch ("regime-gate to {trending, vol_spike},
never chop") is partially superseded by the 2026-06-24 regime
classifier redesign (`reviews/regime_redesign_2026-06-24.md`):
`vol_spike` and `news` were RETIRED on structural grounds. Live-
classes are now only `{trending, chop}`. The v2 sketch updates to
that taxonomy AND adds a peer-disagreement requirement informed by
Φ4.1's right-tail-concentrated PnL.

### 2.2 Empirical justification

| Metric | Φ4 (4-agent MVP — Rin not in MVP) | Φ4.1 (8-agent expanded) | Implication |
|---|---|---|---|
| Rin trades opened | n/a | **244** | low frequency by design |
| Mean pips / trade | n/a | **+9.95** | edge present at mean |
| Median pips / trade | n/a | **−28.26** | fat right tail; losses are large but rarer than wins |
| Mean TQS | n/a | **0.277** | mid-pack |
| Win % | n/a | **35.7 %** | low win-rate, high R:R — consistent with the "cold technician" thesis |
| Precision-lift Thoughts | n/a | **3,094** | fires when v1's R:R ≥ 2.5 + stop ≥ 20 pips filter passes |

Source: `reviews/phi41_squad_v1.md` per-agent KPI table + engine
telemetry "Rin precision lifts applied: 3094"; `reviews/phi41_
squad_v1_addendum.md` §1.

**Root cause of the median-negative profile.** Rin's edge IS in the
right tail — a 35.7 % win rate at R:R ≥ 2.5 is mathematically
positive expectancy. The median is negative because the modal
trade loses; this is not a defect, it is the design. v2 should
**preserve** the right-tail behaviour while filtering out
chop-bar false starts.

### 2.3 Revised v2 hypothesis

Rin's `+0.15` precision-lift to 0.80 conviction fires only when
**all** of:

1. **Regime gate (updated):** classifier label = `trending` on the
   current bar (per the 2-class live-classes-only classifier).
   Chop bars are filtered out — they were the original v0.3
   target, and the redesign removes the `vol_spike` slot that v0.3
   had relied on.
2. **R:R + stop-distance filter (retained from v1):** R:R ≥ 2.5
   AND stop-distance ≥ 20 pips.
3. **Peer-disagreement (new):** at least one peer (Chigiri or
   Bachira) has a prior-tick Thought at conviction ≥ 0.65 going
   the **opposite direction** on the same bar. Rin's lethality is
   in contradicting momentum, so v2 requires explicit momentum
   contradiction.

If condition 1 or 3 fails, Rin's base zone_d1_against Thought
stays at 0.65 (no precision-lift). v1's filter (R:R + stop) is
retained as the *necessary* condition; regime + peer-disagreement
are the new *additional* conditions.

### 2.4 Revised defeat trigger

Rin v2's mean TQS regresses below 0.25 OR win rate falls below
30 % across ≥ 4 of 7 rolling OOS windows. The second guard
protects against over-tightening — if the regime + peer-
disagreement gate excludes too many setups, win rate collapses
along with sample size.

### 2.5 Exact replacement text — `06-blue-lock-doctrine.md` §3.11.3 (A3 Rin bullet)

Replace the existing **A3 Rin v1 → v2 — cold clinical reset**
bullet with:

```
- **A3 Rin v1 → v2 — regime-gated and peer-disagreement-gated
  precision lift.** *Defeat (Φ4.1):* v1 precision-lift fired
  3,094 times; Rin opened 244 trades at mean +9.95 / median
  −28.26 pips (fat-right-tail; 35.7 % win rate). The v0.3 sketch
  proposed regime-gating to `{trending, vol_spike}` but the
  2026-06-24 regime redesign RETIRED `vol_spike` + `news` on
  structural grounds — live-classes are `{trending, chop}` only.
  *v2 hypothesis:* the precision-lift fires only when (a)
  classifier label = `trending` AND (b) v1's R:R ≥ 2.5 + stop-
  distance ≥ 20 pips filter passes (retained) AND (c) at least
  one peer (Chigiri or Bachira) has a prior-tick Thought at
  conviction ≥ 0.65 going the OPPOSITE direction on the same
  bar. Otherwise Rin's base zone_d1_against Thought stays at
  0.65 (no lift). *Defeat trigger:* Rin v2 mean TQS regresses
  below 0.25 OR win rate falls below 30 % across ≥ 4 of 7
  rolling OOS windows. Resolution detail:
  `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §2.
```

### 2.6 Evolution-ledger row

```
| 2026-06-30 | Φ4.1 post-mortem (round-2; no co-existence; refinement-level update) | A3 Rin (`itoshi_rin`) | v1 → v2 sketch refined | **Defeat (Φ4.1):** v1 precision-lift fired 3,094 times; 244 trades at +9.95 mean / −28.26 median (right-tail-concentrated). v0.3 regime-gate targeted retired classes (vol_spike, news). | Regime-gate to live-classes `trending` only; retain v1 R:R + stop-distance filter; add peer-disagreement requirement (Chigiri/Bachira opposite-direction prior-tick Thought at conviction ≥ 0.65). | Pending v2 implementation. | **REFINE-regime+peer-disagreement** — pending v2 implementation. See `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §2. |
```

---

## Section 3 — A4 Chigiri v2 — verdict `REFINE-multi-TF-ADX-and-ATR-percentile`

### 3.1 Verdict

**REFINE.** The v0.3 sketch ("continuation-only, never retest") is
already shipped in v1 — Chigiri's primitive is range-break + ATR
vol-expansion momentum with no retest leg. The active defeat is
not "retest is dead" (already addressed) but "continuation
whipsaws when ADX rises but realised σ doesn't". v2 layers
stricter regime gates.

### 3.2 Empirical justification

| Metric | Φ4 (4-agent MVP — Chigiri not in MVP) | Φ4.1 (8-agent expanded) | Implication |
|---|---|---|---|
| Chigiri trades opened | n/a | **536** | medium-frequency |
| Mean pips / trade | n/a | **+6.62** | edge present at mean but smallest in squad |
| Median pips / trade | n/a | **−26.67** | mean-positive / median-negative — whipsaw losses concentrated |
| Mean TQS | n/a | **0.229** | lowest in the 4 trading agents |
| Win % | n/a | 39.9 % | well below coin-flip — losses dominate by count |
| Breakout-firing Thoughts | n/a | **3,615** | v1's range-break + ATR > 1.2× filter fires |

Source: `reviews/phi41_squad_v1.md` per-agent KPI table + engine
telemetry "Chigiri breakout-firing thoughts: 3615"; `reviews/phi41_
squad_v1_addendum.md` §1.

**Root cause.** Chigiri v1's ATR threshold (1.2× median) is too
permissive — it admits early-stage volatility expansions that fade
into whipsaws. The H1-ADX-rising filter catches direction but not
sustain. The Φ4.1 median (−26.67) confirms: most "breakouts" are
false starts.

### 3.3 Revised v2 hypothesis

Chigiri's continuation-firing requires **all** of (current v1
conditions in italics):

1. *M15 close beyond 20-bar high/low* (v1, retained)
2. **M15-ADX × H1-ADX × H4-ADX all rising on the same bar**
   (replaces v1's H1-ADX-only rising). Multi-TF ADX alignment is
   the empirical signature of a real breakout vs a false start.
3. **Realised σ_M15 over trailing 10 bars in the top-decile of
   trailing 80-bar distribution** (replaces v1's > 1.2× median —
   i.e. roughly top-quartile). Strictly higher σ floor.

If any of 1/2/3 fails, no Thought is emitted. v1's signature is
preserved on the "all conditions pass" path; v2 narrows the
admission criteria.

### 3.4 Revised defeat trigger

Chigiri v2's win rate stays below 40 % AND mean TQS regresses
below 0.20 across ≥ 4 of 7 rolling OOS windows — i.e. the
tightening doesn't pay off. The defeat is calibrated against the
Φ4.1 baseline (win 39.9 %, TQS 0.229).

### 3.5 Exact replacement text — `06-blue-lock-doctrine.md` §3.11.3 (A4 Chigiri bullet)

Replace the existing **A4 Chigiri v1 → v2 — learning to run
again** bullet with:

```
- **A4 Chigiri v1 → v2 — multi-TF ADX alignment + top-decile σ
  floor.** *Defeat (Φ4.1):* v1 breakout-firing produced 3,615
  Thoughts → 536 trades at +6.62 mean / −26.67 median pips, win
  39.9 %, TQS 0.229 (lowest among trading agents). The v0.3
  sketch ("continuation-only, never retest") is already in v1
  — the active defeat is whipsaw losses on early-stage σ
  expansions. *v2 hypothesis:* continuation requires (a) M15
  close beyond 20-bar high/low (v1, retained) AND (b) M15-ADX
  × H1-ADX × H4-ADX all rising on the same bar (replaces v1's
  H1-ADX-only) AND (c) realised σ_M15 over trailing 10 bars in
  the top-decile of trailing 80-bar distribution (replaces v1's
  > 1.2× median ≈ top-quartile). Three conjunctive guards
  filter out false starts that drove the Φ4.1 median-negative
  profile. *Defeat trigger:* win rate stays below 40 % AND mean
  TQS regresses below 0.20 across ≥ 4 of 7 rolling OOS windows.
  Resolution detail: `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md`
  §3.
```

### 3.6 Evolution-ledger row

```
| 2026-06-30 | Φ4.1 post-mortem (round-2; no co-existence; refinement-level update) | A4 Chigiri (`chigiri_hyoma`) | v1 → v2 sketch refined | **Defeat (Φ4.1):** v1 breakout-firing produced 3,615 Thoughts → 536 trades at +6.62 mean / −26.67 median, TQS 0.229, win 39.9 % (lowest among trading agents). v0.3 sketch already in v1; active defeat is whipsaw losses on early-stage σ expansions. | Multi-TF ADX alignment (M15 × H1 × H4 all rising) + top-decile σ floor (replaces v1's top-quartile). Three conjunctive guards. | Pending v2 implementation. | **REFINE-multi-TF-ADX+ATR-percentile** — pending v2 implementation. See `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §3. |
```

---

## Section 4 — A5 Reo v2 — verdict `ADVANCE-coupled-to-Φ5-multi-position`

### 4.1 Verdict

**ADVANCE.** The v0.3 sketch ("HRP-weighted mixture of top-K
trailing-TQS agents, K ≥ 2 enforced architecturally") stands as
the core v2 hypothesis. Φ4.1 surfaces an **additional** role for
Reo that couples his evolution to the Φ5 aggregator work:
**second-position proposer when the first leader's slot is
contested**. Reo becomes the agent that fills the second slot in
the Φ5 multi-position policy (Arm 4 / K = 2), breaking the
slot-cannibalisation kill-path that drove the Φ4.1 FAIL.

### 4.2 Empirical justification

| Metric | Φ4 (4-agent MVP — Reo not in MVP) | Φ4.1 (8-agent expanded) | Implication |
|---|---|---|---|
| Reo trades opened | n/a | **0** (by design) | structural Tier-2 falsifier validated |
| Mirror Thoughts emitted | n/a | **28,469** | lower bound on Nagi-qualifying peer lifts |
| Nagi confluence-firing thoughts | 0 (Φ4) | **34,302** (Φ4.1) | Reo's mediation contributed to clearing Nagi's 2-distinct-peer floor |

Source: `reviews/phi41_squad_v1.md` per-agent KPI table + engine
telemetry "Reo mirror Thoughts emitted: 28469"; `reviews/phi41_
squad_v1.md` Diagnosis ("Reo's mirror count is the lower bound on
Nagi-qualifying peer lifts").

**Root cause for the v2 advance.** The Φ4.1 FAIL diagnosis pinned
the binding constraint at the single-position-per-symbol queue,
not the predicate or roster. Φ5 Arm 4 (multi-position) targets
exactly that constraint with `K = 2 positions per symbol` admitted
from distinct agents. Reo — by design a chameleon mirror without
his own primitive — is the natural occupant of the second slot
when the first leader's coordinate is contested by a peer at lower
but still tradable conviction. Reo's v2 weapon becomes "admit the
second-best leader's coordinate at HRP-derived size when the
first-best leader's slot is contested".

### 4.3 Revised v2 hypothesis

Reo v2 stacks two mechanics:

1. **(retained from v0.3) HRP-weighted mixture of top-K (≥ 2)
   trailing-TQS agents** — Reo computes an HRP weight matrix over
   the trailing-K-week TQS series for all OTHER strikers; the
   mixture defines whose coordinate(s) Reo mirrors at each tick.
2. **(new from Φ4.1) Second-position proposer under Φ5 multi-
   position policy** — when the Φ5 aggregator admits two
   positions per symbol (Arm 4 / K = 2), Reo's mirror Thought
   becomes a Proposal (`intend()` non-trivial) for the
   second-best leader's coordinate, with HRP-derived risk size.
   First-best leader fills slot 1; Reo fills slot 2 with the
   second-best mirror. Both slots respect the `total_risk_cap_per_
   symbol = 1.0%` constraint per Φ5 PROTOCOL §3 Arm 4.

If the Φ5 aggregator does NOT include multi-position policy (Arm 4
gated out, e.g. if Sentinel R1–R5 not wired and stop rule #3
fires), mechanic 2 is deferred and Reo remains a mirror-only
falsifier per v1. Mechanic 1 stands independently of Φ5.

### 4.4 Revised defeat trigger

Reo v2 mechanic 1 (HRP mixture) defeat: F17 ΔInfo ≤ 0 with 95 %
CI lower bound ≤ 0 (i.e. informed Reo does not beat isolated Reo
on F17). v0.3 already specified this and it stands.

Reo v2 mechanic 2 (second-position) defeat: Reo's second-position
trades have a per-window mean TQS below the first-position
leader's mean TQS by ≥ 0.05 across ≥ 4 of 7 rolling OOS windows
— i.e. the second slot is consistently worse than the first slot
and is dragging the squad TQS down. If tripped, mechanic 2 retires
while mechanic 1 continues as v2.

### 4.5 Exact replacement text — `06-blue-lock-doctrine.md` §3.11.3 (A5 Reo bullet)

Replace the existing **A5 Reo v1 → v2 — chemistry, not mimicry**
bullet with:

```
- **A5 Reo v1 → v2 — chemistry, not mimicry (HRP mixture) +
  second-position proposer (Φ5-coupled).** *Defeat (Φ4.1):* v1
  ships the mirror-Thought emitter without `intend()` — the
  structural Tier-2 falsifier; 28,469 mirror Thoughts emitted,
  0 trades. Falsifier worked but Reo never participates in
  capital allocation. *v2 hypothesis — stacked mechanics:*
  **(1)** HRP-weighted mixture of top-K (≥ 2) trailing-TQS
  agents — Reo computes HRP weights over the trailing-K-week TQS
  series for OTHER strikers; the mixture defines whose coordinate(s)
  Reo mirrors. **(2)** Second-position proposer under Φ5 multi-
  position policy (Arm 4 / K = 2) — Reo's mirror Thought becomes
  a Proposal for the second-best leader's coordinate at HRP-
  derived size when the first-best leader's slot is contested.
  Both slots respect Φ5 PROTOCOL §3 Arm 4's `total_risk_cap_per_
  symbol = 1.0%`. *Φ5 dependency:* mechanic 2 is gated on Φ5
  Arm 4 landing (multi-position policy); if Arm 4 is deferred,
  mechanic 2 defers with it and Reo remains mirror-only.
  Mechanic 1 stands independently of Φ5. *Defeat trigger:*
  mechanic 1 retires if F17 ΔInfo ≤ 0 with 95 % CI lower bound
  ≤ 0 (Reo cut from roster); mechanic 2 retires if second-
  position trades' per-window mean TQS is ≥ 0.05 below first-
  position leader's mean TQS across ≥ 4 of 7 rolling OOS
  windows. Resolution detail:
  `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §4.
```

### 4.6 Evolution-ledger row

```
| 2026-06-30 | Φ4.1 post-mortem (round-2; no co-existence; advancement-level update) | A5 Reo (`reo_mikage`) | v1 → v2 sketch advanced (HRP + Φ5-second-position) | **Empirical (no defeat):** v1 ships structural Tier-2 falsifier; 28,469 mirror Thoughts emitted, 0 trades. Falsifier worked. Φ4.1 FAIL diagnosis pinned the binding constraint at the single-position queue — Reo is the natural occupant of the second slot under Φ5 multi-position policy. | Stacked mechanic 1 (HRP-weighted mixture of top-K ≥ 2 trailing-TQS agents, from v0.3) + mechanic 2 (second-position proposer when first leader's slot is contested under Φ5 Arm 4 / K = 2). Mechanic 2 gated on Φ5 Arm 4 landing. | Pending v2 implementation; mechanic 2 deferred until Φ5 Arm 4 ships. | **ADVANCE-coupled-to-Φ5-multi-position** — pending v2 implementation. See `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §4. |
```

---

## Section 5 — Open questions and out-of-scope items

### 5.1 A8 Yukimiya and A9 Aoshi

Both remain **not yet implemented**. No Φ4.1 telemetry exists for
either. Their v0.3 sketches stand unchanged. Once they are built
and run through a squad gate, a round-3 resolution doc will revise
their sketches with the empirical telemetry.

### 5.2 A1 Isagi

The 2026-06-24 Isagi v1 → v2 arc FAIL (`reviews/isagi_v2_arc.md`)
already closed the active v2 hypothesis. A future v3 may revisit
metavision via sweep-as-confluence-filter, multi-position simulator,
FVG/OB primitives, or H1 cadence. **No round-2 update** is needed
for Isagi.

### 5.3 Yukimiya / Aoshi need-build is not a precondition for Φ5

The Φ5 aggregator selection experiment (`experiments/phi5_
aggregator/PROTOCOL.md`) runs on the **8-agent Φ4.1 roster** as
locked. Yukimiya and Aoshi staying not-built does not block Φ5.
Their integration is post-Φ5 (Φ5.5 or Φ6).

### 5.4 Interaction with Phase 4 Sentinel work

The Sentinel R1–R5 wiring (today's Phase 4) is the precondition
for un-deferring Kunigami v2 (round-1, 2026-06-25 §3). The
Bachira / Rin / Chigiri / Reo v2 sketches above do not depend on
Sentinel — they ship independently. The Reo v2 mechanic 2
depends on Φ5 Arm 4, not on Sentinel directly.

---

## Section 6 — Today's orchestrator checklist

1. **Apply §1.5 / §2.5 / §3.5 / §4.5 doctrine bullets** to
   `06-blue-lock-doctrine.md` §3.11.3. Replace the four pre-Φ4.1
   sketch bullets with the revised text. The doctrine version
   header (already at v0.4 from round-1) does NOT bump again
   today; this is a v0.4 sub-update.
2. **Append §1.6 / §2.6 / §3.6 / §4.6 rows** to the Ledger table
   in `reviews/evolution_ledger.md`.
3. **Update Standing notes** in `reviews/evolution_ledger.md` to
   reflect the round-2 resolutions for Bachira / Rin / Chigiri / Reo.
4. **Update roster `v2 sketch revision pending` sub-text** for
   A2/A3/A4/A5 to point at this round-2 resolution doc (the
   pointer in `05-agent-roster-v0.md` §3.2 / §3.3 / §3.4 / §3.5
   Current-version field).
5. **Single commit** with subject
   `M001 doctrine: round-2 v2 backlog resolution (Bachira REFINE / Rin REFINE / Chigiri REFINE / Reo ADVANCE)`.
6. **No version bump** to doctrine or roster (this is sub-v0.4
   work; both files already carry the 2026-06-25 v0.4 / v0.7
   bump).

---

## References

- Round-1 sibling: `reviews/v2_arc_backlog_resolution_2026-06-25.md`
- Doctrine: `06-blue-lock-doctrine.md` §3.11.3 (bullets being
  replaced)
- Roster: `05-agent-roster-v0.md` §3.2 / §3.3 / §3.4 / §3.5 (rows
  pointing at this doc)
- Ledger: `reviews/evolution_ledger.md` (rows being appended)
- Φ4.1 diagnostic: `reviews/phi41_squad_v1.md` per-agent KPI
  table + engine telemetry
- Φ4.1 addendum: `reviews/phi41_squad_v1_addendum.md` §1
  (structural crowding-out)
- Regime redesign (why vol_spike + news retired): `reviews/regime_
  redesign_2026-06-24.md`
- Φ5 dependency for Reo mechanic 2: `experiments/phi5_aggregator/
  PROTOCOL.md` §3 Arm 4
- Standards: `07-research-standards.md` §11 (verdict-comparator
  discipline), §10.6 (evolution-arc regression / forward-test
  contract)
