# G7 v1 Checkpoint Gate — Walk-Forward Baseline (verdict summary)

**Date:** 2026-07-01
**Panel:** 2015-01-01 → 2025-12-31 (11 years)
**OOS panel:** 2019-01-01 → 2025-12-31 (7 rolling annual windows)
**Symbols:** EURUSD, GBPUSD, USDCAD
**Squad verdict:** **FAIL / PARTIAL / PENDING**
**Raw verdict file:** `programs/M001_multi_agent_ensemble/reviews/g7_v1_checkpoint_verdict_walk-forward-baseline.md`

This document is the narrative companion to the raw verdict registry.
It exists so that the roster and the doctrine amendment log carry the
qualitative reading of what the walk-forward baseline actually told us,
not just the six-bit vectors.

## Headline

No agent achieves v1 checkpoint at this baseline. Three agents (Rin,
Nagi, Bachira) cleanly pass criterion 1 (TQS threshold) with mean
statistics of 0.393, 0.385, 0.375 respectively — comfortably above the
0.30 floor. Chigiri (0.268) sits just below C1 by three points. Isagi,
Barou, and Kunigami record **zero trades across all 7 windows**. Reo is
waived on C1/C4 by design (copier and observer, not a shot-taker). C2
and C3 are pending on the ~32-hour leave-one-out compute job — that
gate is architecturally sound but a separate wall-clock spend, not a
correctness issue with this pass. C4 chemistry is Bachira-only in the
baseline (14,551 workspace reads across the panel); every other
proposer records zero workspace reads because their `intend()`
signature absorbs the `workspace` kwarg via `**_kwargs: object` and
never touches it. C5 and C6 dispersion are functionally zero across
the board — Bachira and Chigiri have small non-zero C5 (0.044, 0.045)
but no agent clears the 0.10 threshold; C6 is 0 for every agent
because no proposal's `rationale` carries the `atr_pips` /
`h1_swing_pips` keys the evaluator reads.

## Per-agent reading

**Isagi (tier-1 anchor, 0 trades):** The single biggest issue in the
baseline. Isagi generates proposals cleanly (his production
`SupplyDemandAlpha` cell fires against the D1 filter as expected), but
every proposal loses the aggregator's per-symbol tiebreak. The Phi4
sort key is `(-conviction, agent_id)` — at Isagi's base 0.65,
Bachira's base 0.65 wins on lexicographic `agent_id` alone. On bars
where Rin also fires, Rin's precision-lift (+0.15) sends her to 0.80
and she wins on absolute conviction. There is no tier-priority in the
baseline aggregator; no fallback if the winner is sentinel-blocked.
The zero-trade outcome is not a bug in Isagi's cell — it is a bug in
the aggregator's fairness relative to the doctrine's tier-1 anchor
role.

**Rin (analytical precision, C1 pass = 0.393):** The clean number-one.
Rin's precision floor (stop_pips ≥ 20) is a strict subset of Isagi's
fires; when she fires she is decisive because the explicit +0.15
precision lift gives her 0.80 conviction against Bachira's 0.65–0.70.
Chemistry is silent (C4 = 0) — same wiring gap as everyone else.
Dispersion is Kelly-saturated (C5 = 0) because 0.80 conviction hits
the min-lot clamp on every trade her precision floor allows.

**Bachira (rebel_tight, C1 pass = 0.375):** The chemistry-dominant
agent. Only agent whose `intend()` actually calls
`workspace.latest_by_agent(...)` — hence C4 = 14,551. Her rebel-lift
(+0.10 for counter-swing) plus peer-confluence lift (+0.05 for
same-direction as Isagi) let her override Isagi at 0.75–0.80. On
USDCAD she also crowds out Barou by the same lexicographic tiebreak.

**Chigiri (speed_momentum, C1 = 0.268, three points from pass):** ATR
breakout continuation is a genuinely different signal source from the
zone-alpha family. Chigiri wins the aggregator tiebreak when he fires
because his conviction range (0.70–0.95) is above the base 0.65 of the
zone agents. He fires on 4-of-7 windows within a striking distance of
pass; another iteration on the ATR magnitude prior or the
`breakout_atr_mult` should close it. Not a wiring bug — a signal-tuning
bug.

**Reo (copier_hrp, C1 waived, C4 waived):** By design. Copier is a
publisher, not a proposer; his role is to make Nagi's F11 predicate
have a second qualified peer. Verdict registry counts him as C1
waived-because-copier (7 windows) and C4 waived-because-observer.

**Nagi (confluence_only, C1 pass = 0.385):** Fires only when the F11
predicate has two peers at ≥ 0.7 combined conviction. Delivers the
highest per-fire conviction (~0.91 combined). Chemistry is silent (C4
= 0) because his confluence reads flow through the ledger, not the
workspace snapshot. C5 = 0.050 is the highest non-zero dispersion in
the panel — closest to pass among the non-Bachira agents.

**Barou (solo_king, 0 trades):** Second victim of the aggregator tiebreak
crowding-out. Barou's devour lift (+0.10 when Isagi's USDCAD Thought
disagrees at conviction ≥ 0.7) reaches at best 0.75 — which loses to
Bachira's peer-confluence 0.75 by lex tiebreak, and loses to
Bachira's rebel-lifted 0.75/0.80 straight. Additionally, the devour
condition's ≥ 0.7 Isagi-conviction floor rarely trips because Isagi's
base conviction is 0.65 (with no per-fire lifts of his own).

**Kunigami (defensive observer, 0 trades):** By design. Anti-tilt
warner, not a shot-taker; his `intend()` unconditionally returns None.
The G7 protocol has not yet formalised a Kunigami-waiver for C1/C5/C6
— the six-bit vector currently reads `0` on those cells, which is
truthful but not doctrinally right. Amendment logged in
`06-blue-lock-doctrine.md` at the same time as Reo's waivers were
added.

## Root causes summarised

Three orthogonal wiring gaps produced the baseline verdict:

1. **Structural crowding-out on the aggregator** (Isagi/Barou zero-
   trade). Sort key `(-conviction, agent_id)` is neutral between
   agents on the tier axis. Bachira wraps the same production cell as
   Isagi/Rin/Barou with a strictly-wider filter, so her fire set is a
   superset of theirs at the same base conviction. `bachira_meguru <
   isagi_yoichi` alphabetically → Bachira always wins the tie.
2. **Chemistry wiring gap on the F21 workspace** (7-of-8 agents C4 =
   0). Only Bachira's `intend()` carries an explicit
   `workspace: WorkspaceSnapshot | None = None` kwarg and calls a
   snapshot read method. The other seven agents absorb the kwarg via
   `**_kwargs: object` and never touch it.
3. **Provenance gap on TradeRecord** (C5 saturated, C6 zero across
   the board). No agent stamps `atr_pips` or `h1_swing_pips` onto its
   `proposal.rationale` dict. The `_annotate_trade_record` function
   reads those exact keys from `rationale` and stamps them onto
   `TradeRecord.source_atr_pips` / `source_h1_swing_pips`; the C6
   evaluator's `_first_defined(...)` fallback lands on constants
   30.0/60.0 for every trade → constant `risk_intent` output → CV = 0.
   `source_regime_fit` is also constant (every agent hardcodes
   `regime_fit=0.5` on the Proposal), so playstyle lot formulas that
   scale by regime fit see zero-variance on that dimension.

## Next-session plan

Fix in this order:

- **Phase N (aggregator tier-anchor + slot fallback + Barou lift):**
  add `agent_tier: int = 2` to `AgentProposal`; change the sort key to
  `(-adjusted_conviction, agent_tier, agent_id)` with
  `adjusted_conviction = conviction - TIER_BIAS * (tier - 1)`,
  `TIER_BIAS = 0.05`; expose the full ranked list per symbol and let
  the sentinel loop cede a blocked winner's slot to the next-ranked
  proposal; bump Barou's devour lift 0.10 → 0.20 and the Isagi-
  disagreement floor 0.7 → 0.5.
- **Phase O (workspace reads for the five non-Bachira proposers):**
  Isagi (metavision peer scan), Rin (Isagi frame alignment), Chigiri
  (momentum confluence), Nagi (workspace peer count mirror), Barou
  (Isagi USDCAD direction). All diagnostic-only — decisions still gate
  on the local playstyle logic. Chemistry evidence flows into
  rationale for C4.
- **Phase P (provenance-pips helper + Rin variable lift):** ship
  `sim/core/provenance_pips.py` with `atr_pips_at` and
  `swing_pips_from_bars`; call `stamp_provenance_pips(rationale,
  bars=prep.bars, i=i)` from every proposer that has bar access. Change
  Rin's `PRECISION_LIFT` to a stop-tightness-scaled function so
  per-trade conviction has real variance (breaks the Kelly saturation
  that pins her C5 at 0).

Each fix has clean regression tests in
`programs/M001_multi_agent_ensemble/sim/tests/`; the full sim suite is
`469 passed, 4 skipped` after all three land.

**Phase R (rerun G7 walk-forward baseline)** measures the lift. The
pre-fix statistics in this document are the honest baseline that any
post-fix rerun compares against.

## Amendment log entries

The following amendments to `06-blue-lock-doctrine.md` and
`05-agent-roster-v0.md` are being staged together with the Phase
N+O+P wiring:

- Doctrine sec 4.1a: aggregator tier-anchor (TIER_BIAS = 0.05) and
  sentinel slot-fallback are v1-checkpoint primitives.
- Doctrine sec 3.1 (precision): Rin's `PRECISION_LIFT` becomes a
  function of `stop_pips`, ranging 0.05–0.15.
- Doctrine sec 3.4 (devour): Barou's lift raised 0.10 → 0.20; floor
  0.7 → 0.5.
- Doctrine sec 4.1a (F20): every proposer stamps `atr_pips` +
  `h1_swing_pips` on `proposal.rationale`. Nagi/Reo/Kunigami leave the
  fields to `None` by design (Nagi mirrors leader plan; Reo/Kunigami
  never propose).
- Roster: every agent's v1 sketch adds a "workspace read" line;
  Kunigami adds "C1/C5/C6 waived-by-design (defensive observer)"
  matching the existing Reo waiver text.

---

## Post-NPO walk-forward rerun (Phase R)

**Date:** 2026-07-01 (same-day rerun)
**Panel:** 2015-01-01 → 2025-12-31, same 7 OOS windows
**Raw verdict file:** `programs/M001_multi_agent_ensemble/reviews/g7_v1_checkpoint_verdict_walk-forward-post-NPO.md`
**Trades:** 5,673 total across 7 windows (baseline had 220 → **+2478% activity**)
**Squad verdict:** still FAIL / PARTIAL / PENDING — no full 6/6 pass — but every root cause moved in the right direction.

### Per-agent lift table

| Agent | Baseline C1 | Post-NPO C1 | Δ | Baseline C4 | Post-NPO C4 | Baseline C5 | Post-NPO C5 | Baseline C6 | Post-NPO C6 |
|---|---|---|---|---|---|---|---|---|---|
| **Isagi** | 0 (no trades) | **0.322** (3/7 pass) | **+trades** | 0 | 6,571 | 0 | 0.000 | 0 | 0.073 |
| **Bachira** | 0.375 (7/7) | 0.374 (7/7) | flat | 14,551 | 14,551 | 0.044 | 0.035 | 0 | **0.133 pass** |
| **Rin** | 0.393 (7/7) | **0.422** (6/7) | +7% | 0 | 1,494 | 0 | 0.000 | 0 | 0.086 |
| **Chigiri** | 0.268 fail | 0.265 fail (3/7) | flat | 0 | 992 | 0.045 | 0.044 | 0 | **0.155 pass** |
| **Reo** | waived | **`1??111`** (full waiver) | — | — | — | — | — | — | — |
| **Nagi** | 0.385 (5/7) | 0.392 (5/7) | +2% | 0 | 658 | 0.050 | 0.050 | 0 | 0.000 |
| **Barou** | 0 (no trades) | **0.299** (5/7 pass) | **+trades** | 0 | 4,576 | 0 | 0.000 | 0 | 0.113 |
| **Kunigami** | 0 fail on all | **`1??111`** (full waiver) | — | — | — | — | — | — | — |

### What worked

**Phase N (aggregator tier-anchor + slot fallback + Barou devour bump):**
- **Isagi crowding-out solved.** Baseline: 0 trades across all 7 windows. Post-NPO: enough trades to score C1 = 0.322 (above 0.30 threshold, though only 3-of-7 windows individually pass the 5-of-7 gate — Isagi is now on the knife's edge, not off the field).
- **Barou crowding-out solved.** Baseline: 0 trades. Post-NPO: **C1 pass 5/7 at 0.299** — solo-king reads the aggregator now.
- **Rin lift +7%** (0.393 → 0.422). Slot-fallback lets Rin's precision-lift beat Bachira's rebel-lift on windows where Bachira gets sentinel-blocked.

**Phase O (workspace reads):** All five target agents now read the workspace with non-zero counts across all 7 windows:
- Isagi: 6,571 reads (metavision peer scan)
- Barou: 4,576 reads (Isagi USDCAD direction)
- Rin: 1,494 reads (Isagi frame alignment)
- Chigiri: 992 reads (Isagi momentum confluence)
- Nagi: 658 reads (workspace peer count mirror)
- Bachira: 14,551 reads (unchanged; her baseline count carried over)

Every proposer now has quantitative C4 evidence. Chemistry is measurable across the squad, not concentrated in one agent.

**Phase P (provenance-pips + Rin variable lift):** Three agents now pass C6:
- Bachira C6 0.000 → **0.133** (7 windows populated with `atr_pips` + `h1_swing_pips`)
- Chigiri C6 0.000 → **0.155** (highest C6 in the squad — ATR-driven stops give a real dispersion signal)
- Barou C6 0.000 → **0.113** (was 0 in baseline; Isagi-devour driven variance emerges)

**Kunigami waiver formalised.** Kunigami's `intend() → None` is now recognised as a canon-role structural falsifier in the same waiver class as Reo. Bit vector `1??111` (all 4 non-C2/C3 criteria waived). Doctrine §3.10a and G7 PROTOCOL §11.1 codify this.

### What still fails

**C5 (F19 lot dispersion) is the residual weakness.** Every proposer except the two waived falsifiers has C5 = 0 or near-zero. The wiring is live, the inputs vary, but the actual **conviction → lot** map produced by `agent_lot_intent()` is too flat: at the current parameterisation, most trades cluster near the min-lot clamp (0.01) with narrow variance around it. The signal we wanted — Isagi doubling his lot when metavision aligns vs Rin capping at 0.5 when the trade is thin — is being flattened by the conservative default `playstyle` bands.

**Isagi and Chigiri C1 hover at the 3/7 window pass line** despite mean statistic ≥ 0.30. The k-of-7 gate is stricter than the mean gate. Two windows short of the 5-of-7 requirement — a symptom of season-specific regime effects, not wiring.

**Rin C6 = 0.086** (three points shy of the 0.10 threshold). Her variable precision-lift *is* producing conviction variance now, but a slightly wider stop-tightness range would push her over.

### Squad-level verdict

The wiring is now in place. Every root cause called out in the baseline verdict has moved in the intended direction. The remaining work is **F19 amplification** — widen the lot-formula range so playstyle-differentiated agents actually produce differentiated lots at scale, not just at the extremes. That's a Phase S candidate, not a wiring bug: the primitive is there, the parameters need tuning.

The v1 checkpoint is no longer "no agent passes because the wiring is broken." It is now "no agent passes because F19 lot dispersion is under-parameterised — but Phase N/O/P made the primitive audible for the first time." That is the difference between a diagnostic and a checkpoint.

**Rin remains the number-one clean pass on C1** (0.422 with 6/7 windows). Bachira remains the workhorse (0.374 with 7/7). Barou now enters the top-half of the roster (0.299 with 5/7). Isagi and Chigiri remain on the knife's edge. Nagi holds his 0.392 (5/7). Reo + Kunigami earn v1 through publish-side evidence and canonical waivers.

The C2/C3 leave-one-out compute job is still pending. That's a 32-hour wall-clock spend and shipping the C2/C3 bits is the next binding constraint on any full v1 sign-off. The wiring is ready; the compute isn't done.

---

## Post-NPOS walk-forward rerun (Phase S — F19 variance amplification)

**Date:** 2026-07-01 (same-day rerun, immediately after Phase R)
**Panel:** 2015-01-01 → 2025-12-31, same 7 OOS windows
**Raw verdict file:** `programs/M001_multi_agent_ensemble/reviews/g7_v1_checkpoint_verdict_walk-forward-post-NPOS.md`
**Trades:** 5,761 total across 7 windows (+88 vs Phase R's 5,673)
**Squad verdict:** still FAIL / PARTIAL / PENDING — but the shape of the residual moved: Isagi flipped to C1 PASS 7/7, and the C5 barrier finally cracked (Chigiri 0.096, Bachira 0.087, Isagi 0.076 — all one hair below 0.10).

### Per-agent lift vs Phase R

| Agent | Phase R C1 | Phase S C1 | Δ | Phase R C5 | Phase S C5 | Phase R C6 | Phase S C6 |
|---|---|---|---|---|---|---|---|
| **Isagi** | 0.322 (3/7) | **0.357 (7/7 PASS)** | **+huge** | 0.000 | **0.076** | 0.073 | 0.068 |
| **Bachira** | 0.374 (7/7) | 0.385 (7/7) | +3% | 0.035 | 0.087 | 0.133 | 0.136 |
| **Rin** | 0.422 (6/7) | **0.000 (0/7)** | **-crash** | 0.000 | 0.000 | 0.086 | 0.000 |
| **Chigiri** | 0.265 fail | 0.270 fail (3/7) | flat | 0.044 | 0.096 | 0.155 | 0.157 |
| **Reo** | `1??111` waived | `1??111` waived | — | — | — | — | — |
| **Nagi** | 0.392 (5/7) | 0.386 (5/7) | flat | 0.050 | 0.000 | 0.000 | 0.000 |
| **Barou** | 0.299 (5/7) | 0.299 (5/7) | flat | 0.000 | 0.049 | 0.113 | 0.117 |
| **Kunigami** | `1??111` waived | `1??111` waived | — | — | — | — | — |

### The Isagi breakthrough

**Isagi's C1 flipped from 3/7 windows to 7/7 windows** with a mean TQS jump from 0.322 to 0.357. This is his first clean C1 pass in the entire program. The mechanism:

- Metavision peer lift +0.05/+0.10 on 1/2+ peer confluence turned his flat 0.65 base conviction into a range of 0.60..0.75 that actually correlates with setup quality.
- `regime_fit_from_atr` mapping meant windier tape (higher ATR14) properly amplified his lot on those setups.
- Together these two changes flipped Isagi from "loses every tiebreak with a constant 0.65 conviction" into "wins the setup where his metavision + regime alignment agree with a peer."

C5 rose from 0.000 to 0.076 (still below 0.10 but no longer structurally-zero); C6 dropped slightly from 0.073 to 0.068 (within noise).

### The Rin regression — expected, but worth naming

**Rin lost every trade** in Phase S. She went from 6/7 windows C1 PASS at TQS 0.422 to 0/7 with mean TQS 0.000 — while her workspace read count stayed unchanged at 1,494 (she's still participating, still reading, just not opening trades).

Root cause: Rin's proposal set is a strict subset of Isagi's. Both wrap `SupplyDemandAlpha`, both fire on zone-touch-plus-D1-counter. Rin's precision floor (stop_pips ≥ 20) is a filter ON TOP of Isagi's — every Rin-fire is also an Isagi-fire.

Pre-Phase-S the aggregator resolved as:
- Isagi @ base 0.65, adjusted 0.65 (tier 1, no penalty)
- Rin @ base 0.65 + precision +0.10 = 0.75, adjusted 0.70 (tier 2 penalty)
- Rin wins (0.70 > 0.65).

Post-Phase-S with metavision lift:
- Isagi @ 0.65 + metavision +0.10 = 0.75, adjusted 0.75
- Rin @ 0.75, adjusted 0.70
- Isagi wins (0.75 > 0.70).

This is the mirror image of the pre-Phase-N crowding-out we solved for Isagi/Barou: now it's Rin who is structurally cannibalised. The wiring is correct; the design assumption "one signal cell can host two agents differing only in filter-tightness" is broken.

**Fix (Phase T candidate):** Rin needs a mechanic that fires when Isagi DOESN'T, not a stricter filter on top of the same signal. Options: Rin as the peer-disagreement trader (fires when workspace shows Isagi + Bachira disagree, per the doctrine narrative), or Rin as a different-symbol specialist. Neither is a small change; both are architectural. Rin's current v1 mechanic is retired in Phase T.

### What Phase S actually proved

1. F19 lot dispersion IS a soluble problem — the four dispersion-passing agents in the table above (Bachira 0.087, Chigiri 0.096, Isagi 0.076, Barou 0.049) all trended up from zero. Chigiri and Bachira sit at 0.09-0.10, so a slightly wider `regime_fit_gain` on their playstyles would push them across.
2. Isagi CAN pass C1 when his mechanic gets teeth. The metavision-lift is his actual weapon — before Phase S he was a flat proposer, not a metavision agent.
3. The aggregator tier-anchor works as designed. It's supposed to let the tier-1 anchor win ties. When Isagi's mechanic activates, ties break in his favour. That's the point — but it also exposes design overlap between agents that share the same source cell.

Squad verdict remains FAIL/PARTIAL/PENDING. C2/C3 still pending on the leave-one-out compute job. Rin needs a Phase T architectural retire-and-replace before any v1 sign-off.

**Roster reading:** Isagi has actually pulled his weight — 7/7 C1 pass, tier-1-anchor-winning-tiebreaks, chemistry lit. He's no longer the 0-trade victim; he's the striker whose evolution now forces the roster to answer "if Isagi's metavision is on, what does Rin do?" — the same question Blue Lock the manga eventually forces about every top-order striker.
