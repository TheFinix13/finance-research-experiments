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
