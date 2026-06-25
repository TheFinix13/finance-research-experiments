# v2 Arc backlog resolution — Nagi · Barou · Kunigami

| Field | Value |
|---|---|
| **Date** | 2026-06-25 |
| **Status** | `prep` — orchestrator applies doctrine updates tomorrow |
| **Author** | prep-worker |
| **Phase context** | End of session, post-Φ4.1 FAIL (squad TQS 0.292 = 0.92× Isagi-alone) |
| **Branch** | `multi-agent-ensemble` (verified clean working tree at `add099d`) |
| **Constraint reminder** | No doctrine / roster / ledger / `ai_context` / `sim/` edits tonight |

This document is the binding diagnostic-and-resolution brief for the three
v2 evolution-arc sketches that pre-dated empirical Φ4 + Φ4.1 evidence.
Each section ends with **exact replacement text** the orchestrator can
copy-paste verbatim into `06-blue-lock-doctrine.md` §3.11.3 and
`05-agent-roster-v0.md` §3 rows. The §3.11.2 contract is unchanged;
this is a §3.11.3 (sketches) and per-row update.

---

## Section 1 — A6 Nagi v2 — verdict `DROP`

### 1.1 Verdict

**DROP** the existing v2 sketch ("boredom into mastery — relax confluence
floor"). The empirical evidence inverts the sketch's premise.

### 1.2 Empirical justification

| Metric | Φ4 (4-agent MVP) | Φ4.1 (8-agent expanded) | Verdict implication |
|---|---|---|---|
| Confluence-firing Thoughts | **0** | **34,302** | predicate is correct; needed peer fuel, not relaxation |
| Proposals emitted | 0 | **645** | structurally adequate when ≥ 2 Tier-2 source signals exist |
| Trades opened | 0 | **94** | concurrency rule throttles airtime, not predicate |
| Mean TQS per Nagi trade | n/a | **0.349** | **HIGHEST per-agent TQS in the 8-agent squad** |
| Per-agent rank (TQS) | n/a | **1 / 4 traded agents** | Nagi outperforms Bachira (0.308), Rin (0.277), Chigiri (0.229) |

Source: `reviews/phi4_squad_v1.md` (Φ4 telemetry, Nagi row);
`reviews/phi41_squad_v1.md` (Φ4.1 per-agent KPIs + engine telemetry);
`reviews/phi41_squad_v1_addendum.md` §"Nagi fired 34302 confluence
thoughts but only 94 trades".

The Φ4 → Φ4.1 delta confirms the Φ4 FAIL diagnosis verbatim: Nagi v1
was **predicate-starved**, not predicate-broken. Once Bachira's
rebel-lift, Rin's precision-lift, and Reo's mirror Thoughts supplied
the 2-distinct-peer × shared-tag × overlapping-coordinate × matching-
direction fuel, the predicate fired 34,302 times in 11 years and
produced the **best per-trade quality in the squad**.

The original v2 sketch — "tolerate 2-striker overlap, lower aggregate
conviction floor when regime is favourable per F18" — would make Nagi
**less canonical**, not more. It would:

1. Push Nagi toward Bachira-class firing frequency, collapsing the
   "perfect trap" weapon identity (doctrine §1.1 item 1 → ego ≠ floor).
2. Move TQS downward (the 0.349 score is achieved precisely because
   the floor is tight; relaxing it would admit lower-quality trades).
3. Undo the canon contract in §3.11.1 — "vN+1 is not vN with more
   parameters" — by making v2 a hyperparameter tweak of v1.

### 1.3 Replacement defeat trigger

The v1 defeat trigger ("confluence-only firing rate too low") is now
empirically wrong. The replacement defeat trigger is forward-looking:

> **Nagi defeat trigger (post-Φ4.1):** Nagi's per-OOS-window mean
> TQS regresses below the median of all other proposing strikers in
> **≥ 2 of 3 regime buckets** (trend / range / vol-expansion event)
> across **≥ 4 of 7 rolling OOS windows** on the locked walk-forward
> panel. Detected via the Φ4.1 squad-gate harness; the threshold is
> a per-regime row in the squad TQS table.

This trigger is consistent with the data: Nagi's first defeat (when
it lands) will be a *regression*, not a *starvation*. The single
regime-bucket threshold is preserved from `06-blue-lock-doctrine.md`
§3.11.1 ("a TQS regression in a specific regime bucket").

### 1.4 Exact replacement text — `06-blue-lock-doctrine.md` §3.11.3

Replace the existing **A6 Nagi v1 → v2 — boredom into mastery** bullet
(currently at §3.11.3 in the doctrine file, between A5 Reo and A7
Barou) with:

```
- **A6 Nagi v1 — canonical (Φ4.1-validated); v2 sketch retired.**
  Empirical: Φ4.1 telemetry shows the v1 confluence floor (2-distinct
  peers × shared tags × overlapping coordinate × matching direction)
  is **correct as-shipped**. With peer fuel (Bachira rebel-lift,
  Rin precision-lift, Reo mirror Thoughts) Nagi fired 34,302
  confluence-firing Thoughts → 645 proposals → 94 trades at mean
  **TQS 0.349 (highest per-agent TQS in the 8-agent squad)**.
  Relaxing the floor would make Nagi less canonical, not more.
  *Defeat trigger (replaces "fires too rarely"):* Nagi's per-OOS-
  window mean TQS regresses below the median of all other proposing
  strikers in ≥ 2 of 3 regime buckets (trend / range / vol-expansion
  event) across ≥ 4 of 7 rolling OOS windows on the locked walk-
  forward panel. *v2 status:* deferred indefinitely until that
  regression appears in the squad-gate harness. The sketch is
  retired in `reviews/v2_arc_backlog_resolution_2026-06-25.md`
  §1; the v1 module is canonical.
```

### 1.5 Exact replacement text — `05-agent-roster-v0.md` §3.6 (A6 Nagi row)

Replace the **Evolution arc** field (currently:
`v1 → v2 boredom into mastery (...). *Trigger:* confluence-only firing
rate too low — sample size never clears C1 under the v1 ≥ 3-striker
overlap rule. *v2 hypothesis:* tolerate 2-striker overlaps with lower
aggregate conviction floor when regime is favourable per F18`) with:

```
| **Evolution arc** | **v1 canonical (Φ4.1-validated); v2 sketch retired** per `reviews/v2_arc_backlog_resolution_2026-06-25.md` §1. Φ4.1 telemetry showed v1's 2-distinct-peer floor is correct as-shipped: with peer fuel Nagi fired 34,302 confluence-firing Thoughts at mean TQS 0.349 (highest per-agent TQS in the 8-agent squad). Relaxing the floor would make Nagi less canonical, not more. Future v2 reserved for a regression-class defeat (see Defeat trigger). |
```

Replace the **Defeat trigger** field (currently: `Expected: v1 trade
count too low for statistical power on the rolling 12-week window (< 5
trades per pair); insufficient-n verdict on the C1 gate`) with:

```
| **Defeat trigger** | Nagi's per-OOS-window mean TQS regresses below the median of all other proposing strikers in ≥ 2 of 3 regime buckets (trend / range / vol-expansion event) across ≥ 4 of 7 rolling OOS windows on the locked walk-forward panel. The trigger is forward-looking; not currently active (Nagi v1 leads the squad on TQS at Φ4.1). When tripped, cite trade-ID range in `reviews/nagi_seishiro_v1_defeat.md`. |
```

### 1.6 Status

**`v1 canonical, v2 sketch retired`.**

### 1.7 Followups (v3, optional)

If a Nagi v3 ever lands, the empirically-motivated direction is:
**confluence × concurrency-release**, i.e. solve the 365-confluence-
thoughts-per-trade attrition (`phi41_squad_v1_addendum.md` §2) by
letting Nagi *displace* a lower-TQS open trade rather than wait for it
to close. That is an aggregator-layer change, not a Nagi change, so
it is parked under the Φ5 aggregator deliverable
(`phi41_squad_v1_addendum.md` §"What this tells us about Φ5") rather
than under a Nagi v3 module. Tonight: no v3 sketch is recorded.

---

## Section 2 — A7 Barou v2 — verdict `REDESIGN`

### 2.1 Verdict

**REDESIGN.** The "live ledger read for devour" mechanic is empirically
dead. Replace it with **Mechanic A — Ex-post Isagi-miss replay**
(recommended; see §2.4) or **Mechanic B — Symbol expansion** (not
recommended; see §2.4).

### 2.2 Empirical justification

| Metric | Φ4 (4-agent MVP) | Φ4.1 (8-agent expanded) | Implication |
|---|---|---|---|
| Barou trades opened | 1,150 | **0** (slot-cannibalised by Bachira) | Barou crowded out at Φ4.1 aggregator |
| Mean pips / trade (Φ4) | +9.79 | n/a | E005 right-tail asymmetry holds at mean |
| Median pips / trade (Φ4) | **−7.28** | n/a | mean-positive / median-negative — drags TQS |
| **Devour lifts applied** (Φ4) | **0** | **0** | mechanic never fires in 11 years × 2 runs |
| Devour-lift Thoughts (Φ4.1) | n/a | **0** | confirmed dead at expanded roster |

Source: `reviews/phi4_squad_v1.md` Diagnosis #2 + per-agent KPI table;
`reviews/phi41_squad_v1.md` engine telemetry "Barou devour lifts
applied: 0"; `reviews/phi4_squad_v1_addendum.md` per-agent KPI row.

**Why devour fires 0 times — root cause (structural, not parameter).**

The Φ4 + Φ4.1 telemetry isolates two independent kill-paths for the
live-ledger devour mechanic:

1. **Doctrine §3.9 (three-tier access).** Barou is canonically Tier-3
   ("refuses to participate in chemical reactions"). The v1 spec
   added a Tier-2 hook (read Isagi's prior-tick Thought) as a *single
   exception*. This is architecturally fragile — every other Tier-3
   agent reads only its own past Thoughts; Barou's exception is the
   only inter-agent live read in the Tier-3 cohort.
2. **Structural rarity of simultaneous-disagreement.** On USDCAD H4,
   Isagi (zone × D1-against) and Barou (baseline zone, no D1 gate)
   target different setups — by audit §2.5, they have **inverse
   asymmetry** on USDCAD. The probability of Isagi having a
   ≥ 0.7-conviction Thought on the SAME bar Barou proposes, going in
   the OPPOSITE direction, is empirically ≤ 1 / 1,150 trades = **0 in
   2,006 squad-tick observations**. The mechanic is not "broken";
   it is **architecturally unreachable**.

The v2 sketch was authored before this telemetry existed. With
telemetry in hand, the sketch must be redesigned, not retuned.

### 2.3 Replacement mechanics

#### Mechanic A — Ex-post Isagi-miss replay (Tier-3 compatible)

**Concept.** Barou reads Isagi's **closed** trades from the public
ledger (closed trades are post-fact, not live ledger reads — they
are Tier-1 audit data per doctrine §3.9). When an Isagi closed trade
exited at a loss (`realised_pnl_pips < 0`), Barou checks if the loss
occurred in his coordinate space (USDCAD, within the last N H4 bars,
inside or within 1 ATR of a baseline-zone touch he would have
proposed). If yes, Barou's NEXT-bar proposal gets a `+0.10`
conviction devour lift (same cap, same accounting as v1, only the
trigger changes).

**Lookback window.** **24 H4 bars (≈ 4 trading days)**. Rationale:
matches Barou's `target_hold_hours = 32` × 0.75 dampening factor;
wider than 1 hold period (don't replay setups Barou already
captured) but tight enough to remain causally relevant. Tunable in
Φ5; locked for v2 implementation.

**Tier compliance.** Closed trades are Tier-1 read (doctrine §3.9
row 1). Barou stays Tier-3 at the *thought-reading* layer; the
closed-trade journal is a strictly post-fact data source on which
every agent in the squad has full read access. No doctrine §3.9
amendment is required.

**Failure mode addressed.** Live disagreement is rare → replay
disagreement is plentiful. The Φ4 telemetry shows Isagi opened 856
trades with median −11.28 pips/trade (i.e. > 50 % closed at a loss).
The Tier-1 ledger contains ≥ 400 Isagi-loss events to replay against
Barou's ~1,150 USDCAD signal-ticks. Expected devour-fire rate ≥ 1
per 5–10 Barou ticks (vs current 0 per 2,006).

**Implementation hint (DO NOT modify tonight).** The replacement
lives in `sim/agents/a07_barou.py` `_maybe_apply_devour()` — replace
the `ledger.read(as_of=, current_tick=, symbol=)` call (current
lines 352–356) with a call to a new `ClosedTradeLedger.read_losses(
agent_id="isagi_yoichi", symbol="USDCAD",
within=timedelta(hours=24*4))` method. The lift logic, the cap, the
tag emission, and the rationale dict are byte-preserved. The new
ledger interface is shipped under `sim/core/closed_trade_ledger.py`
and threaded through the harness via `run_phi4_squad_gate.py` (new
arg `closed_trade_ledger=`). All §3.11.2 deliverables follow:
v1 byte-preserved, v2 next to it, regression test on the v1 trade
panel (must reproduce 1,150 Φ4 trades exactly), forward test on the
11-year USDCAD panel (must show ≥ 100 devour-fire events).

#### Mechanic B — Symbol expansion (Tier-3 preserved but specialty diluted)

**Concept.** Barou expands beyond USDCAD baseline-zone to fire
baseline-zone (no D1 gate) on EURUSD + GBPUSD as well. This creates
direct same-symbol overlap with Isagi (zone × D1-against, on EURUSD
+ GBPUSD + USDCAD per roster §3.1) → live disagreement becomes
common → live devour fires.

**Symbol-coverage policy (if adopted).** Barou whitelist becomes
`("EURUSD", "GBPUSD", "USDCAD")` (was: `("USDCAD",)`). Setup
remains **baseline zone INSTEAD of zone × D1-against** on all three
symbols (the Isagi-Barou inverse asymmetry preserved by the
parameter, not by the symbol restriction).

**Why this is the inferior choice.**

1. **Direct collision with Bachira at Φ4.1.** Bachira v1 is
   `bachira_meguru` running **the same baseline-zone primitive
   (no D1 gate) on the same three symbols** (`mvp_phi41.yaml`
   roster + `phi41_squad_v1_addendum.md` §1). Barou expanded to
   EURUSD/GBPUSD would compete for the same per-symbol aggregator
   slot Bachira already dominates with the rebel-lift. Expected
   Barou Φ4.1 trade count under mechanic B: still ~0, for the
   same crowd-out reason that killed Φ4.1.
2. **Dilutes USDCAD canon specialty.** Barou's canon thesis
   (doctrine §1.1 item 2 + roster §3.7 thesis) is **single-pair
   specialist**. Symbol expansion makes Barou a generalist; the
   "King who locks one symbol" identity collapses.
3. **E005 asymmetry is USDCAD-specific.** The empirical prior that
   justifies the baseline-zone setup (audit §2.5: +4.63 pips/trade
   on USDCAD, Sharpe 1.16, p = 0.028) is *not* established on
   EURUSD or GBPUSD as a positive prior — quite the opposite, the
   audit shows zone × D1-against is the dominant edge on EURUSD.
   Symbol expansion contradicts the audit.

### 2.4 Recommendation — Mechanic A

**Pick Mechanic A.** Rationale:

| Criterion | Mechanic A | Mechanic B |
|---|---|---|
| Tier-3 compatibility | yes (closed trades = Tier-1 public) | yes (no ledger read change) |
| Preserves USDCAD canon specialty | **yes** | no |
| Devour-fire rate > 0 | yes (~100+ events on 11-yr panel) | uncertain (crowd-out persists) |
| Aligned with E005 empirical prior | yes (USDCAD-only) | no (contradicts audit §2.5) |
| Avoids Bachira collision at Φ4.1 | **yes** (different symbol) | no (same primitive × same symbol) |
| Doctrine §3.9 impact | none | none |
| Implementation surface | new `ClosedTradeLedger` interface | symbol whitelist + setup expansion |
| Regression risk on v1 USDCAD panel | low (byte-preserve `intend`) | medium (parameter sweep risk) |

Mechanic A also has the methodological advantage of converting devour
from a *synchronous* to an *asynchronous* mechanic — which is
architecturally cleaner under the Tier-3 contract and is robust to
the Φ4.1 crowd-out failure mode.

### 2.5 Exact replacement text — `06-blue-lock-doctrine.md` §3.11.3

Replace the existing **A7 Barou v1 → v2 — devour mechanic awakens**
bullet with:

```
- **A7 Barou v1 → v2 — devour replays Isagi's losses (Tier-3
  asynchronous).** *Defeat:* the v1 live-ledger devour mechanic
  fired 0 times in 11 years across Φ4 + Φ4.1 (2 of 2 runs). Root
  cause: live disagreement between Isagi (USDCAD zone × D1-against)
  and Barou (USDCAD baseline zone, no D1 gate) is architecturally
  rare — they target different setups on the only shared symbol.
  *v2 hypothesis:* devour reads Isagi's **closed losing trades**
  (Tier-1 post-fact data) from the public ledger; when a closed
  Isagi loss landed in Barou's coordinate space (USDCAD, within the
  last 24 H4 bars, inside or within 1 ATR of a baseline-zone touch
  Barou would have proposed), Barou's NEXT-bar proposal conviction
  gets a `+0.10` lift (cap 1.0). Closed trades are Tier-1 public
  per §3.9 row 1; Barou stays Tier-3 at the thought-reading layer.
  *Lookback:* 24 H4 bars (locked for v2; tunable in Φ5).
  *Defeat trigger replacement:* live-ledger devour 0-fires retired;
  the v2 defeat trigger is "Barou v2 conviction-lift slice TQS does
  not beat Barou v1 baseline TQS on the same USDCAD panel by ≥
  +0.02 absolute at the §3.11.2 step 5 forward test". Resolution
  detail: `reviews/v2_arc_backlog_resolution_2026-06-25.md` §2.
```

### 2.6 Exact replacement text — `05-agent-roster-v0.md` §3.7 (A7 Barou row)

Replace the **Evolution arc** field with:

```
| **Evolution arc** | **v1 → v2 devour replays Isagi's losses (Tier-3 asynchronous)** per `reviews/v2_arc_backlog_resolution_2026-06-25.md` §2. *Defeat (Φ4 + Φ4.1):* live-ledger devour fired 0 times in 11 yrs × 2 runs (mechanic dead). Live disagreement between Isagi (USDCAD zone × D1-against) and Barou (USDCAD baseline zone, no D1 gate) is architecturally rare — they target different setups. *v2 hypothesis:* devour reads Isagi's **closed losing trades** from the public ledger (Tier-1 post-fact); when an Isagi loss lands in Barou's coordinate space (USDCAD, last 24 H4 bars, within 1 ATR of a baseline-zone touch), Barou's NEXT-bar proposal conviction gets `+0.10`. Tier-3 thought-isolation preserved. Locked lookback 24 H4 bars (Φ5-tunable). |
```

### 2.7 Status

**`v1 canonical, v2 redesign pending implementation`.**

### 2.8 Implementation hint for tomorrow (DO NOT TOUCH TONIGHT)

The orchestrator does **not** implement v2 code tomorrow. Tomorrow is
the doctrine + roster + ledger update only. v2 implementation is a
later sprint. The pointers below are for that sprint:

- New module: `sim/agents/a07_barou_v2.py` sits next to
  `sim/agents/a07_barou.py` (additive at the filesystem level per
  §3.11.2 step 3).
- New interface: `sim/core/closed_trade_ledger.py` with
  `ClosedTradeLedger.read_losses(agent_id, symbol, within: timedelta)
  -> list[ClosedTrade]`.
- Harness wiring: `run_phi4_squad_gate.py` accepts
  `closed_trade_ledger=` and threads it to `A7BarouV2(__init__)`.
- Regression test: `sim/tests/test_a07_barou_v2_regression.py` —
  byte-equivalence on the Φ4 USDCAD trade panel (must reproduce
  1,150 trades when closed-ledger is empty / pre-Φ4 cold start).
- Forward test: `sim/tests/test_a07_barou_v2_resolves_devour_dead.py`
  — must show ≥ 100 devour-fire events on the 11-year USDCAD H4
  panel (the §3.11.2 step 5 contract; threshold pre-declared here).

---

## Section 3 — A10 Kunigami v2 — verdict `DEFER`

### 3.1 Verdict

**DEFER** until Sentinel R1–R5 are wired into the squad-gate harness
(Φ4.2 deliverable per `ai_context.md` "Next steps" #2). The "forward-
looking pre-emptive dampening" cannot be defined against a Sentinel
that does not consume Kunigami's warnings yet.

### 3.2 Empirical justification

| Metric | Φ4 (4-agent MVP) | Φ4.1 (8-agent expanded) | Implication |
|---|---|---|---|
| Kunigami **warning Thoughts emitted** | **0** | **25,877** | predicates emit at the expanded roster; Sentinel does not consume |
| Sentinel R1–R5 wired into harness | no | no | dampening cannot land without Sentinel |
| Trades blocked by Kunigami dampener | 0 | 0 | no observed effect on squad PnL either way |
| OOS-window observations of Sentinel-fire events | **0** | **0** | no baseline frequency to calibrate v2 against |

Source: `reviews/phi4_squad_v1.md` engine-telemetry "Kunigami warning
thoughts: 0" + "Sentinel R1-R5 not wired in v1"; `reviews/phi41_squad
_v1.md` engine-telemetry "Kunigami warning thoughts: 25877"; same
file caveat #2 ("Sentinel R5 still not wired to the squad-gate
harness"); roster §3.10 status row.

**Honest correction of the user-prompt headline.** The prep brief said
"Φ4.1: 0 warnings emitted (still)". The actual telemetry says
**25,877** Kunigami warning Thoughts in Φ4.1 — Kunigami's
overconfidence predicate fired repeatedly because Bachira's rebel-lift
and Rin's precision-lift pushed peer-mean confidence above 0.85 for
extended stretches. The DEFER verdict is unchanged because:

1. **Warnings are emitted but not consumed.** Sentinel R5 is not
   wired into the squad-gate harness (caveat #2 in both Φ4 and Φ4.1
   reports). The 25,877 warnings have zero downstream effect on
   sizing or proposal acceptance.
2. **Defining "pre-emptive" requires a baseline Sentinel-fire
   distribution.** We cannot say "Kunigami v2 fires *before* the
   third loss" until R5 is wired and v1's *post*-fact firing
   frequency is established as the baseline.

The verdict is therefore: **the v2 sketch is structurally undefined
until Sentinel R1–R5 lands**. DEFER is the correct status, but the
justification is "Sentinel not consuming", not "Kunigami not
emitting".

### 3.3 Pre-condition for un-deferring (binding)

All three of:

1. **Sentinel R1–R5 wired** into `run_phi4_squad_gate.py` (or its
   Φ5 successor harness) such that Kunigami warning Thoughts flow
   into R5's 50 %-risk-scale dampener. (Φ4.2 deliverable per
   `ai_context.md` "Next steps" #2.)
2. **Kunigami v1 has ≥ 100 OOS-window observations** of
   Sentinel-fire events (i.e. R5 actually dampening the squad after
   Kunigami warns) across the regime buckets `{trend, range,
   vol-expansion event}`.
3. **Baseline frequency-of-fire established** per regime bucket in a
   committed review doc (e.g. `reviews/kunigami_v1_sentinel_
   baseline.md`). The "pre-emptive dampening" v2 hypothesis is then
   defined relative to this baseline: "fire ≥ N H4 bars earlier than
   v1 on Y % of qualifying drawdown windows".

Until all three land, v2 stays deferred. The orchestrator marks the
v2 sketch `status: deferred` in the doctrine and roster — see §3.4
and §3.5 below.

### 3.4 Exact replacement text — `06-blue-lock-doctrine.md` §3.11.3

Replace the existing **A10 Kunigami v1 → v2 — gentle giant** bullet
with:

```
- **A10 Kunigami v1 → v2 — gentle giant (`status: deferred-pending-
  Sentinel-Φ4.2`).** *Defeat (expected, retained):* loss-streak
  dampener fires post-fact — three losses before the half-size
  kicks in. *v2 hypothesis (retained):* read forward-looking ledger
  confidence aggregates (low aggregate conviction × high pairwise
  correlation) and dampen **pre-emptively**, before the third loss
  lands. *Deferred pending:* Sentinel R1–R5 are not yet wired into
  the squad-gate harness; Kunigami v1 emitted 25,877 warning
  Thoughts at Φ4.1 but none reached R5's 50 %-risk-scale dampener.
  "Pre-emptive" cannot be defined against a Sentinel that does not
  consume warnings. *Pre-condition for un-deferring:* (1) R1–R5
  wired (Φ4.2 deliverable per `ai_context.md`); (2) ≥ 100 OOS-
  window Sentinel-fire observations across `{trend, range,
  vol-expansion event}` regime buckets; (3) v1 baseline frequency-
  of-fire established in `reviews/kunigami_v1_sentinel_baseline.md`.
  Resolution detail: `reviews/v2_arc_backlog_resolution_2026-06-25.md`
  §3.
```

### 3.5 Exact replacement text — `05-agent-roster-v0.md` §3.10 (A10 Kunigami row)

Replace the **Evolution arc** field with:

```
| **Evolution arc** | **v1 → v2 deferred-pending-Sentinel-Φ4.2** per `reviews/v2_arc_backlog_resolution_2026-06-25.md` §3. v2 hypothesis retained (pre-emptive dampening via forward-looking ledger confidence aggregates) but un-deferring requires (1) Sentinel R1–R5 wired into the squad-gate harness, (2) ≥ 100 OOS-window Sentinel-fire observations across `{trend, range, vol-expansion event}` regime buckets, (3) v1 baseline frequency-of-fire established in `reviews/kunigami_v1_sentinel_baseline.md`. Φ4.1: 25,877 Kunigami warning Thoughts emitted but unconsumed; Sentinel not yet wired. |
```

### 3.6 Sentinel differentiation note (R1–R5 vs Kunigami v2)

For tomorrow's orchestrator: Kunigami v2 (when un-deferred) is the
**character agent** — anticipatory anti-tilt within the cast,
ego-modulated, reads ledger aggregates as part of its weapon
identity. Sentinel R1–R5 is the **architectural auxiliary** (doctrine
§4.2 — explicitly *not* a `BlueLockStriker`), deterministic, narrow,
external-shock-driven (correlation jumps, spread spikes, calendar
events, DXY shocks for §4.2; min-lot floor, discrete sizing, pass
bias, concentration cap, loss-streak for §4.3). The differentiation
is preserved verbatim in doctrine §4.2 / §4.3 — no edit required
to those sections. Kunigami v2's "forward-looking aggregates" weapon
is upstream of Sentinel's deterministic floor; the two stack
multiplicatively per doctrine §4.3 R5.

### 3.7 Status

**`v1 canonical, v2 deferred`.**

---

## Section 4 — `evolution_ledger.md` row appends

Three exact rows for tomorrow's orchestrator to **append** verbatim to
the Ledger table in `programs/M001_multi_agent_ensemble/reviews/
evolution_ledger.md` (currently has one row: the 2026-06-24 Isagi
v1 → v2 FAIL). Append in the order shown; preserve the existing
2026-06-24 row.

Note: the existing ledger schema is
`| Date | Phase | Agent | vN → vN+1 | Trigger | Hypothesis |
Co-existence window | Outcome |` — eight columns, not the
six-column abbreviation used in the prep brief. The rows below
match the real schema.

```
| 2026-06-25 | Φ4.1 post-mortem (no co-existence; sketch-level update) | A6 Nagi (`nagi_seishiro`) | v1 → v2 sketch retired | **Empirical (no defeat):** Φ4.1 telemetry shows v1 confluence floor is correct. With peer fuel Nagi fired 34,302 confluence-firing Thoughts → 94 trades at mean **TQS 0.349** (HIGHEST per-agent TQS in 8-agent squad). Relaxing floor would make Nagi less canonical, not more. | v2 sketch retired; new defeat trigger forward-looking (TQS regression across regime buckets, see `reviews/v2_arc_backlog_resolution_2026-06-25.md` §1.3). | n/a (no v2 module ever shipped) | **DROP** — v1 canonical, v2 sketch retired. See `reviews/v2_arc_backlog_resolution_2026-06-25.md` §1. |
| 2026-06-25 | Φ4.1 post-mortem (no co-existence; redesign-level update) | A7 Barou (`barou_shoei`) | v1 → v2 sketch redesigned | **Defeat:** live-ledger devour fired 0 times in 11 yrs × 2 runs (Φ4 + Φ4.1). Root cause: live disagreement between Isagi (USDCAD zone × D1-against) and Barou (USDCAD baseline zone, no D1 gate) is architecturally rare — different setups on the only shared symbol. | New v2 reads Isagi's **closed losing trades** (Tier-1 post-fact); when a loss lands in Barou's coordinate space (USDCAD, last 24 H4 bars, within 1 ATR of a baseline-zone touch), Barou's NEXT-bar proposal conviction gets +0.10. Tier-3 thought-isolation preserved. Mechanic A chosen over symbol expansion (B); see `reviews/v2_arc_backlog_resolution_2026-06-25.md` §2.4. | Pending v2 implementation (Φ5 or later sprint). Co-existence window declared at implementation time. | **REDESIGN** — pending v2 implementation. See `reviews/v2_arc_backlog_resolution_2026-06-25.md` §2. |
| 2026-06-25 | Φ4.1 post-mortem (no co-existence; deferral) | A10 Kunigami (`kunigami_rensuke`) | v1 → v2 deferred | **Pre-condition not met:** Sentinel R1–R5 not yet wired into squad-gate harness. Φ4.1 emitted 25,877 Kunigami warning Thoughts but R5 dampener never consumed them. "Pre-emptive dampening" undefined against a Sentinel that does not consume warnings. | Retain v2 hypothesis (forward-looking ledger confidence aggregates). Un-deferring requires (1) R1–R5 wired (Φ4.2), (2) ≥ 100 OOS-window Sentinel-fire observations across `{trend, range, vol-expansion event}` regime buckets, (3) v1 baseline frequency-of-fire established in `reviews/kunigami_v1_sentinel_baseline.md`. | n/a until pre-conditions land. | **DEFER** — v2 deferred-pending-Sentinel-Φ4.2. See `reviews/v2_arc_backlog_resolution_2026-06-25.md` §3. |
```

---

## Section 5 — Tomorrow's orchestrator checklist (target < 15 min)

Sequential. Each step has the file path and the exact edit to apply.

### Step 1 — `06-blue-lock-doctrine.md` §3.11.3 (Nagi bullet)

Open `programs/M001_multi_agent_ensemble/06-blue-lock-doctrine.md`.
Find the **A6 Nagi v1 → v2 — boredom into mastery** bullet in
§3.11.3 (between A5 Reo and A7 Barou — currently 5-line bullet
starting "**A6 Nagi v1 → v2 — boredom into mastery.**"). Replace
verbatim with the block in §1.4 of this document.

### Step 2 — `06-blue-lock-doctrine.md` §3.11.3 (Barou bullet)

Same file. Find the **A7 Barou v1 → v2 — devour mechanic awakens**
bullet in §3.11.3 (between A6 Nagi and A8 Yukimiya). Replace verbatim
with the block in §2.5 of this document.

### Step 3 — `06-blue-lock-doctrine.md` §3.11.3 (Kunigami bullet)

Same file. Find the **A10 Kunigami v1 → v2 — gentle giant** bullet
in §3.11.3 (last bullet in §3.11.3). Replace verbatim with the block
in §3.4 of this document.

### Step 4 — `05-agent-roster-v0.md` (3 row updates)

Open `programs/M001_multi_agent_ensemble/05-agent-roster-v0.md`.

- §3.6 (A6 Nagi) — replace `**Evolution arc**` and `**Defeat
  trigger**` fields per §1.5 of this document (both fields, two
  consecutive table rows).
- §3.7 (A7 Barou) — replace `**Evolution arc**` field per §2.6 of
  this document (one row).
- §3.10 (A10 Kunigami) — replace `**Evolution arc**` field per §3.5
  of this document (one row).

### Step 5 — `evolution_ledger.md` (3 rows appended)

Open `programs/M001_multi_agent_ensemble/reviews/evolution_ledger.md`.
Append the three rows from §4 of this document to the **Ledger**
table (the existing 2026-06-24 Isagi row stays at the top; the three
new rows go below it in the order shown — Nagi, then Barou, then
Kunigami).

### Step 6 — Bump doctrine version header

Same `06-blue-lock-doctrine.md`. Top of file currently reads:

> **Status:** `DRAFT v0.3` — 2026-06-24. v0.3 adds **§3.11 — Agent
> Evolution Arcs**, …

Change to:

> **Status:** `DRAFT v0.4` — 2026-06-25. v0.4 records the **first
> three §3.11 sketch resolutions** post-Φ4.1: A6 Nagi v2 sketch
> DROPPED (v1 floor empirically correct); A7 Barou v2 sketch
> REDESIGNED (live-ledger devour replaced by Tier-3 closed-loss
> replay); A10 Kunigami v2 sketch DEFERRED pending Sentinel R1–R5
> wiring (Φ4.2). Resolution detail:
> `reviews/v2_arc_backlog_resolution_2026-06-25.md`. v0.3 stands
> below.

Then add a short header sentence under the existing intro paragraph
that links to this resolution file.

### Step 7 — Commit

```
M001 doctrine: v2 arc backlog resolution (Nagi DROP, Barou REDESIGN, Kunigami DEFER)
```

No `Co-authored-by` trailers. No `--author` overrides. Plain commit
per the workspace rule `.cursor/rules/git-no-cursor-attribution.mdc`.

Files in this commit:
- `programs/M001_multi_agent_ensemble/06-blue-lock-doctrine.md` (3
  bullet replacements + version-header bump)
- `programs/M001_multi_agent_ensemble/05-agent-roster-v0.md` (3 row
  updates across 4 cells)
- `programs/M001_multi_agent_ensemble/reviews/evolution_ledger.md`
  (3 row appends)

`ai_context.md` is **not** in this commit — its update happens at the
session-end ritual per the workspace rule `.cursor/rules/ai-context-
routine.mdc`, after the doctrine commit lands and the orchestrator
confirms all three changes apply cleanly.

### Step 8 — Verify

`git diff HEAD~1 --stat` to confirm only those three files changed
and the line counts match the expected deltas (≈ +15 / −10 in
doctrine, ≈ +6 / −4 in roster, +3 in ledger).

---

## Section 6 — Open questions for the user

These are the ambiguities the prep analysis surfaced. The
orchestrator should pause on Step 1 of §5 until the user resolves
them. If the user is asleep / unavailable, the orchestrator may
proceed with the default in parentheses; flag the choice in the
commit message footer if a non-default is taken.

### Q1 — Barou v2 mechanic A vs B

The recommendation in §2.4 is Mechanic A (ex-post Isagi-miss replay).
The user-prompt asked for a choice with justification. Confirm A is
the right choice, or instruct the orchestrator to pick B / a hybrid.

**Default if unanswered:** Mechanic A (per §2.4 rationale).

### Q2 — Kunigami pre-condition phase — Φ4.2 or Φ5?

The DEFER pre-condition (§3.3) names Φ4.2 as the Sentinel-wiring
phase per `ai_context.md` "Next steps" #2. If the user has since
decided to defer Sentinel wiring to Φ5 (because Φ4.2 is now scoped
narrower — only HRP allocator + same-direction merge in the
aggregator), the pre-condition phase name should be Φ5 instead.

**Default if unanswered:** Φ4.2 (per `ai_context.md` as of
2026-06-24).

### Q3 — Honest-reporting note on Kunigami's 25,877 warnings

The user-prompt brief said "Φ4.1: 0 warnings emitted (still)"; the
actual telemetry says 25,877 warnings emitted but 0 consumed. §3.2
documents this correction. Confirm the orchestrator should keep the
honest correction in the committed doctrine + roster (not soften it
to "0 actionable warnings" or similar).

**Default if unanswered:** Keep the honest correction (cite 25,877
emitted, 0 consumed, explain why).

### Q4 — Nagi v3 placeholder in doctrine?

§1.7 records a directional idea for a hypothetical Nagi v3
(confluence × concurrency-release). Currently it is parked in this
resolution doc only — not added to doctrine §3.11.3 or the roster.
Confirm that's correct (the doctrine retires the v2 sketch without
introducing a v3 placeholder), or instruct the orchestrator to add
a v3 line to §3.11.3.

**Default if unanswered:** No v3 line added to doctrine; idea stays
parked in this resolution doc.

### Q5 — Pre-existing Φ4.1 Bachira / Chigiri / Rin / Reo v2 sketches

The current doctrine §3.11.3 has v2 sketches for A2 Bachira, A3 Rin,
A4 Chigiri, A5 Reo authored before Φ4.1 telemetry existed. Φ4.1 now
has empirical data on all four (Bachira 2840 trades / TQS 0.308,
Rin 244 / 0.277, Chigiri 536 / 0.229, Reo 0 trades by design,
Kunigami warnings 25,877). Should the orchestrator extend tomorrow's
edits to revise *those* sketches too, or stay strictly within the
Nagi / Barou / Kunigami scope of this prep doc?

**Default if unanswered:** Stay strictly within scope. The other
four sketches need their own resolution doc (e.g.
`v2_arc_backlog_resolution_round2_2026-06-26.md`).

---

## References

- Doctrine: `programs/M001_multi_agent_ensemble/06-blue-lock-doctrine.md`
  §3.11 (the contract being applied)
- Roster: `programs/M001_multi_agent_ensemble/05-agent-roster-v0.md`
  §3.6 / §3.7 / §3.10 (rows being edited)
- Evolution ledger: `programs/M001_multi_agent_ensemble/reviews/
  evolution_ledger.md` (rows being appended)
- Φ4 diagnostic: `programs/M001_multi_agent_ensemble/reviews/
  phi4_squad_v1.md` (Diagnosis #1, #2; per-agent KPI table)
- Φ4.1 diagnostic: `programs/M001_multi_agent_ensemble/reviews/
  phi41_squad_v1.md` (per-agent KPI table + predicate-starvation
  falsifier headline) + `phi41_squad_v1_addendum.md` (crowd-out
  analysis) + `phi41_squad_v1_crossstat_addendum.md` (cross-statistic
  robustness)
- Φ4 cross-statistic baseline: `programs/M001_multi_agent_ensemble/
  reviews/phi4_squad_v1_addendum.md` (locked-statistic registry
  context)
- Executed-arc precedent: `programs/M001_multi_agent_ensemble/
  reviews/isagi_v2_arc.md` (FAIL pattern; tomorrow's three updates
  follow the same retention rule)
- Cross-repo rules: `.cursor/rules/use-brain-box.mdc`,
  `.cursor/rules/git-no-cursor-attribution.mdc`,
  `.cursor/rules/ai-context-routine.mdc`
- AI context: `ai_context.md` ("Next steps" #1–#5 for Φ4.1 + Φ4.2
  ordering)
