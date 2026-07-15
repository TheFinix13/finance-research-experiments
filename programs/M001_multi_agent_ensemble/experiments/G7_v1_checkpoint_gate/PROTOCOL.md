# G7 — v1 Checkpoint Gate — pre-registered protocol

**Status:** `pre-registered` — 2026-07-01
**Author:** orchestrator (foreground, per user 2026-07-01 Phase-6-completion decision).
**Parent doctrine:** `06-blue-lock-doctrine.md` v0.5 §3.11.5.
**Gate context:** G7 is the **v1 checkpoint gate** — the squad-level test that decides whether any agent is authorised to attempt a v2 arc. It is *not* a phase-transition gate (like G4 → G5 → G6 → G6-continuation → G7 → G8 in `docs/methodology/gate_verdict_registry.md`); it is a pre-condition on the *v2 authorisation event* itself. If any agent proposes a v2 arc and the squad has not cleared G7, the v2 authorisation is denied and the agent's v2 work stays parked.

> **Why this exists.** Session 2026-07-01 Phase-6d Φ5 aggregator partial verdict showed Arm 2 (TQS-conditional conviction floor) lifting squad TQS by +0.0187 without any v2 arc. The user's response: *the aggregator lever works — the binding constraint is not agent capability, it is squad chemistry. Stop stacking v2 evolutions on top of a broken v1 squad; make the squad's v1s work like cogs in a wheel first.* G7 is the operationalisation of that constraint. See `06-blue-lock-doctrine.md` v0.5 preamble + §3.11.5 for the doctrinal source.

---

## 1. Hypothesis

**H0:** The Φ4.1 8-agent squad, augmented with the three v1 chemistry primitives (F19 `lot_intent`, F20 `risk_intent`, F21 `read_workspace` — doctrine §4.1a), cannot simultaneously satisfy §3.11.5's six v1 checkpoint criteria for all 8 implemented agents on the locked walk-forward panel.

**H1:** The augmented Φ4.1 squad *does* satisfy §3.11.5's six criteria for all 8 implemented agents, with per-criterion bootstrap 95 % CI lower bound > the threshold specified in §5 below.

**Rejection criterion:** PASS = H1 satisfied for **all 8 implemented agents** (A1 Isagi, A2 Bachira, A3 Rin, A4 Chigiri, A5 Reo, A6 Nagi, A7 Barou, A10 Kunigami). PARTIAL PASS = H1 satisfied for ≥ 5 of 8 agents; the remaining agents are named as `pre-v1 (mechanic-iter-N in flight)` with specific criterion failures cited. FAIL = fewer than 5 agents pass. Per doctrine §3.11.5, **no v2 authorisation is granted unless PASS** (full 8/8); PARTIAL PASS keeps the squad at "chemistry-improving-but-not-yet-cogs-in-a-wheel" and blocks v2 work.

A single-agent PASS is not a v1 checkpoint — the checkpoint is squad-level by design (see doctrine §3.11.5 "Squad chemistry mandate").

---

## 2. Empirical motivation (numbers locked)

| Source | Number | What it shows |
|---|---|---|
| Φ4.1 squad FAIL | 0.2922 squad TQS / 0.92× Isagi-alone | 8-agent expansion does not close the gap; the squad's chemistry is broken |
| Φ4.1 telemetry | Isagi 0 trades, Barou 0 trades — both slot-cannibalised by Bachira | criterion #3 (non-cannibalising slot behaviour) fails empirically for Bachira |
| Φ4.1 Kunigami | 25,877 warning Thoughts, 0 consumed by R5 (pre-Φ4.2-wiring) | criterion #4 (workspace participation) fails empirically pre-F21 |
| Φ4.1 Reo | 28,469 mirror Thoughts, 0 trades | intentional Tier-2 falsifier per §3.10 — criterion #1 exception clause applies |
| Φ4.1 Nagi | 645 proposals, 94 trades, mean TQS 0.349 (HIGHEST) | criterion #1 passes; criterion #4 (F21 read) unproven pre-Φ5 |
| Φ5 Arm 2 partial verdict | +0.0187 TQS lift from filtering low-conviction proposals | aggregator lever alone lifts squad TQS; agent-side chemistry primitives may compound this |

These six facts jointly motivate the six §3.11.5 criteria; each criterion has at least one Φ4.1 falsifier attesting to its necessity.

---

## 3. The 6 v1 checkpoint criteria (per doctrine §3.11.5)

Each criterion has a locked pass threshold. Criteria are conjunctive — an agent must pass all 6 to be classified v1.

### Criterion 1 — Undeniable per-agent positive result

- **Statistic:** per-agent mean TQS across all trades in the OOS windows; per-agent per-window mean TQS.
- **Pass threshold:** mean TQS ≥ 0.30 AND per-window mean TQS ≥ 0.20 in at least 5 of 7 rolling OOS windows.
- **Exception (structural falsifier):** if the agent has an explicit falsifier role documented in the doctrine (§3.10 currently names only A5 Reo), the trade-count requirement is waived and the falsifier's `structural_thought_count` (mirror Thoughts, in Reo's case) must be > 0 in ≥ 5 of 7 OOS windows instead.
- **Bootstrap CI:** 95 % CI lower bound on mean TQS must exceed 0.25 (a slightly looser bound than the point-estimate threshold to avoid tight-panel false negatives).

### Criterion 2 — Positive-sum chemistry contribution

- **Statistic:** leave-one-out squad TQS delta. Run two replays per agent: (a) with the agent in the squad; (b) with the agent removed. Compute the mean TQS of *each remaining agent* in each configuration.
- **Pass threshold:** at least one *other* agent's mean TQS or trade count strictly improves in configuration (a) vs configuration (b), with bootstrap CI lower bound on that delta > 0 at α = 0.05.
- **Rationale:** the agent adds to the squad, not just to itself. A specialist that trades productively alone but does not lift any peer is a solo player, not a cog in a wheel.

### Criterion 3 — Non-cannibalising slot behaviour

- **Statistic:** for each other agent `p`, the reduction in `p`'s OOS trade count caused by this agent's presence, per rolling window.
- **Pass threshold:** the agent does not reduce any single peer's trade count by more than 50 % in ≥ 4 of 7 rolling OOS windows via slot cannibalisation on shared symbols.
- **Explicit falsifier:** Bachira v1's Φ4.1 behaviour (46,584 rebel-lift fires forcing Isagi + Barou to 0 trades) is the archetype this criterion catches.

### Criterion 4 — Reasoning-workspace participation (F21)

- **Statistic:** per-agent workspace-read count (how many peer Thoughts the agent's `read_workspace()` method returned as inputs to `intend()` decisions) AND workspace-publish count (how many Thoughts the agent published to the workspace) per OOS window.
- **Pass threshold:** both counts > 0 in all 7 rolling OOS windows. An agent that only publishes is a specialist-in-silo; the doctrine requires reads too.
- **Rationale:** chemical reactions require agents to *read* each other's Thoughts before deciding. Publish-only participation is § 3.3 Aggregator-side confluence (post-proposal); § 3.11.5 wants agent-side anticipation (pre-proposal).

### Criterion 5 — Owned lot-size cognition (F19)

- **Statistic:** per-agent `lot_intent()` output variance across trades. If the method returns a constant (i.e. `FIXED_LOT = 0.1` for every trade), variance = 0 and the criterion fails.
- **Pass threshold:** coefficient of variation (CV = std / mean) of the agent's `lot_intent()` output ≥ 0.10 over the OOS panel — the agent's sizing varies meaningfully with conviction, SL, equity, and regime_fit.
- **Rationale:** sizing is part of the "beautiful goal" equation. A fixed-lot agent has no size cognition.

### Criterion 6 — Owned risk-shape cognition (F20)

- **Statistic:** per-agent `risk_intent()` output variance across trades. If both `sl_pips` and `tp_ladder` return their defaults (40.0, [80.0]) for every trade, variance = 0 and the criterion fails.
- **Pass threshold:** either `sl_pips` CV ≥ 0.10 OR `tp_ladder[0]` CV ≥ 0.10 over the OOS panel.
- **Rationale:** playstyle produces different SL/TP shapes. A default-only agent has no risk cognition.

---

## 4. Panel

Same panel as Φ4.1 + Φ5 aggregator experiment (locked):

- **Symbols:** EURUSD, GBPUSD, USDCAD (H4 bars).
- **Full period:** 2015-01-01 → 2025-12-31.
- **Walk-forward:** IS = 4 years, OOS = 1 year, stepped annually → 7 rolling OOS windows (2019 through 2025).
- **Roster:** the 8 implemented agents (A1 Isagi v1, A2 Bachira v1, A3 Rin v1, A4 Chigiri v1, A5 Reo v1, A6 Nagi v1, A7 Barou v1, A10 Kunigami v1) — each augmented with F19/F20/F21 implementations per doctrine §4.1a playstyle mapping.
- **Regime classifier:** live-classes only (`trending`, `chop`) per 2026-06-24 regime redesign.
- **Sentinel:** physically blocking (`sentinel_blocks=True`) per Φ5 PROTOCOL §11.1. R6 active for multi-position candidates.
- **Aggregator:** Φ4.1 baseline (single-position-per-symbol queue, conviction-only ranking) — the G7 gate is about *agent-side* chemistry, not aggregator selection.

---

## 5. Statistic (locked)

**Per-agent verdict:** a boolean pass on each of the 6 criteria above (§3). Reported as a 6-bit vector per agent.

**Squad-level verdict:** the conjunction of all 8 per-agent verdicts. PASS iff every agent has all 6 bits set.

**Cross-statistic robustness (reported alongside, not decisive):**

- Median-of-window-mean squad TQS (matches G6's locked statistic).
- Mean-of-window-mean squad TQS.
- Squad win rate across all OOS windows.
- Per-agent contribution table (mean TQS, trade count, leave-one-out delta, workspace read/publish counts, `lot_intent` CV, `risk_intent` CV).

Per `07-research-standards.md` §11, the primary decision is made on the locked statistic (per-agent 6-bit vector conjunction). Cross-statistics are audit-only.

---

## 6. Pre-mortems

- **F19/F20 implementations may over-fit playstyle to panel.** Playstyle values in doctrine §4.1a were derived from Φ4.1 telemetry — they are informed by the same panel G7 evaluates on. Mitigation: playstyle values are *not* free parameters; they are derived from canon character traits + per-agent Φ4.1 telemetry summary statistics (mean TQS, median pip P&L, win rate), and locked in doctrine §4.1a *before* G7 runs. Any post-hoc re-tuning of playstyle constants after seeing G7 results is a §11 amendment.
- **F21 workspace could add false chemistry.** If agents can read each other's Thoughts, one dominant agent (e.g. Nagi at 0.349 mean TQS) could pull the whole squad's decisions toward its own preferences, creating apparent chemistry without genuine diversity. Mitigation: the workspace is read-only from the reader's perspective and does not include lot sizes or risk parameters — only Thought narratives + coordinates. Agents can *see* peers' claims but must translate them through their own F19/F20 cognition.
- **Reo's HRP mixture couples to squad size.** Reo's `lot_intent` returns an HRP-weighted mixture of top-K peer intents. If K > roster size, the mixture degenerates. Mitigation: K = min(K, roster_size − 1) per implementation.
- **Kunigami's `warning_active_at` may fire too often under variable lots.** Larger lot sizes from F19 could increase loss magnitudes and trigger Kunigami's warning threshold more frequently. Mitigation: Kunigami's warning threshold is expressed in *R-multiples*, not dollars — invariant under lot changes.
- **Isagi's confluence-adjusted conviction may absorb Nagi's advantage.** If Isagi reads Nagi's Thoughts via F21 and gets a lift on every Nagi-confluent decision, the leave-one-out Nagi criterion (§3.2) may fail — removing Nagi hurts Isagi. This is the desired outcome (positive-sum chemistry, criterion #2) but must be documented per agent.

---

## 7. File footprint plan

New files to be created (all in `programs/M001_multi_agent_ensemble/`):

| Path | Purpose |
|---|---|
| `sim/core/reasoning_workspace.py` | F21 primitive — per-tick shared blackboard for peer Thought reads (Phase C). |
| `sim/core/lot_intent.py` | F19 default + shared utilities for playstyle-specific overrides (Phase D). |
| `sim/core/risk_intent.py` | F20 default + shared utilities for playstyle-specific overrides (Phase D). |
| `sim/tests/test_reasoning_workspace.py` | F21 contract tests (Phase C). |
| `sim/tests/test_lot_intent_defaults.py` | F19 default tests (Phase D). |
| `sim/tests/test_risk_intent_defaults.py` | F20 default tests (Phase D). |
| `sim/agents/aXX_<name>.py` | Wire F19/F20/F21 into all 8 implemented agents with playstyle mapping (Phase E). |
| `sim/scoring/run_g7_v1_checkpoint_gate.py` | G7 harness — evaluates all 6 criteria for all 8 agents on the panel (Phase G). |
| `reviews/g7_v1_checkpoint_verdict.md` | Human-readable verdict report (Phase G output). |
| `reviews/g7_v1_checkpoint_<agent_id>.json` | Machine-readable per-agent 6-bit vector + criterion evidence (Phase G output). |

Preserved (do not modify):

- `sim/core/aggregator.py` — Φ2.5 stub, still under the DO-NOT-MODIFY §7 directive from Φ5 PROTOCOL.
- `sim/core/aggregator_arms/*.py` — Φ5 arm implementations (partial verdict shipped 2026-07-01).
- `sim/core/sentinel.py` — Φ4.2 R1-R6 wiring, tests pass; F19/F20 outputs feed into Sentinel context.

---

## 8. Stop rules

Per Φ5 PROTOCOL §6 stop-rule conventions (retained):

1. **Panel drift check.** If the Φ4.1 baseline (Arm 0 control at 0.2922) does not reproduce within ±0.005 TQS on this harness with F19/F20/F21 wired but all agents using default (fixed-lot, 40-pip stop, no workspace read) implementations, halt and diagnose. The wiring is not supposed to move Arm 0.
2. **Compute time-box.** If the 7-window full-panel replay takes > 4 hours per agent (i.e. > 32 hours total for the 8 agents), ship a partial verdict on the completed subset and mark the rest `REQUIRES_RESIM` per §11.2 discipline. Never silently truncate.
3. **F19/F20 lot-size explosion.** If any agent's `lot_intent()` returns a lot > 1.0 (10× the fixed-lot default) on any trade, halt and inspect — this is a runaway sizing bug, not a chemistry signal. Sentinel R1 should catch this before it hits execution but the harness logs it as a hard stop-rule trigger.

---

## 9. Cross-references

- Doctrine: `06-blue-lock-doctrine.md` v0.5 §3.11.5 (v1 checkpoint definition) + §4.1a (F19/F20/F21 primitives).
- Roster: `05-agent-roster-v0.md` v0.8 §1.0 (v1 checkpoint status table).
- Evolution ledger: `reviews/evolution_ledger.md` (six RELABEL-2026-07-01 rows citing this protocol).
- Verdict registry: `docs/methodology/gate_verdict_registry.md` — G7 row to be added after this protocol is signed off (see §11).
- Research standards: `07-research-standards.md` §11 (verdict-comparator discipline, pre-registration amendments).
- Prior Φ5 protocol: `experiments/phi5_aggregator/PROTOCOL.md` (partial verdict shipped 2026-07-01; G7 is downstream of Φ5, i.e. G7 evaluates the *squad* on which Φ5 selects an aggregator).

---

## 10. Sequencing (relative to session 2026-07-01)

G7 pre-registration lands as Phase A of the 2026-07-01 v1/v2 reframe session. The actual G7 gate fire (Phase G in the session plan) requires:

- Phase C: F21 `ReasoningWorkspace` scaffold + contract tests.
- Phase D: F19/F20 default implementations on `BlueLockStriker` + contract tests.
- Phase E: playstyle wiring on all 8 implemented agents.
- Phase F: agent-side workspace read/write hooks.
- Phase G: `run_g7_v1_checkpoint_gate.py` + report generation.

The full plan is documented in `ai_context.md` (2026-07-01 update).

---

## 11. Amendment procedure

Per `07-research-standards.md` §11. Any change to the criteria in §3, the pass thresholds in §3 or §5, the panel in §4, the statistic in §5, or the file footprint in §7 requires a dated §11.N amendment appended to this file. Locked parameters are locked; deviations are documented, not silent.

### §11.1 (2026-07-01) — Kunigami defensive-observer waiver

**Trigger:** the walk-forward baseline (pre-Phase-N/O/P wiring fixes) recorded Kunigami with C1/C4/C5/C6 all failing at `0` because Kunigami's `intend()` returns None by design (roster §3.10 / doctrine §3.11 "defensive observer, no shooting drive"). The bit vector `0??000` is truthful but not doctrinally meaningful — Kunigami's role is anti-tilt warning, not trade-taking.

**Amendment:** Kunigami is added to `STRUCTURAL_FALSIFIERS` in `run_g7_v1_checkpoint_gate.py` alongside Reo. Both agents are now waived on:

- **C1** (mean TQS ≥ 0.30): trade-count waived because `intend() → None` by design; passes with `status=waived`.
- **C5** (F19 lot dispersion): waived — no trades to measure dispersion on.
- **C6** (F20 risk-shape dispersion): waived — same reason as C5.
- **C4** (workspace participation): read-side is waived; publish alone is enough. Both agents publish thoughts every tick (Reo's copier-mirrors, Kunigami's warning-status thoughts).

**Doctrine linkage:** §3.10 (Reo copier-falsifier waiver) is extended to §3.11 (Kunigami defensive-observer waiver) with identical semantics. Both agents earn v1 through publishing alone.

**Effect on the G7 verdict:** Reo already reached `W??W..` in the pre-fix baseline (C1/C4 waived; C5/C6 fail because they were `no trades in OOS panel`). Post-amendment Reo reaches `W??WWW` (all waivers explicit). Kunigami moves from `0??000` to `W??WWW`. Both agents contribute to squad pass count via waiver + publish evidence.

**No panel/statistic change** — the walk-forward panel, the K-of-7 thresholds, and the per-criterion pass floors are unchanged. This amendment only adjusts which agents the evaluator considers a structural falsifier.

### §11.2 (2026-07-01) — Aggregator tier-anchor (Phase N)

**Trigger:** the walk-forward baseline recorded Isagi and Barou at 0 trades across all 7 OOS windows. Diagnosis: the `_phi4_aggregate` sort key `(-conviction, agent_id)` gives no weight to the tier axis; Bachira wraps the same production alpha as Isagi/Barou at wider filters, so her fire set is a strict superset at the same base conviction. `bachira_meguru` < `isagi_yoichi` alphabetically → Bachira always wins the tie.

**Amendment:** `AgentProposal` gains an `agent_tier: int = 2` field. `_phi4_aggregate` sort key becomes `(-adjusted_conviction, agent_tier, agent_id)` where `adjusted_conviction = conviction - TIER_BIAS * (agent_tier - 1)` and `TIER_BIAS = 0.05`. Isagi (tier 1) wins same-base-conviction tiebreaks; a peer needs `conviction >= anchor.conviction + 0.05` to override.

Additionally: the aggregator now exposes `ranked_by_symbol: dict[str, list[AgentProposal]]`. In physical-sentinel mode (`sentinel_blocks=True`), the sentinel loop iterates the full ranked list per symbol so a blocked winner cedes the slot to the next-ranked proposal — the slot no longer dies on a single-agent R1-R6 block.

**Empirical effect (2024 OOS single-window smoke, `dry-run-2024-post-NPO`):** Isagi 0 → 25 trades; Barou 0 → 8 trades; Chigiri C1 0.268 fail → 0.311 pass; Rin C1 0.393 → 0.531.

### §11.3 (2026-07-01) — F21 workspace reads for five agents (Phase O)

Isagi, Rin, Chigiri, Nagi, and Barou now carry an explicit `workspace: WorkspaceSnapshot | None = None` kwarg on `intend()` and each calls a snapshot read method (`peer_thoughts` or `latest_by_agent`). Chemistry evidence is stamped on `proposal.rationale`. Diagnostic-only for v1 — the local playstyle gates still dominate the decision.

**Empirical effect:** C4 chemistry lit for every non-Bachira/non-Reo/non-Kunigami proposer — 1177 (Isagi), 211 (Rin), 154 (Chigiri), 135 (Nagi), 905 (Barou) reads in the smoke window.

### §11.4 (2026-07-01) — Provenance-pips helper (Phase P)

New module `sim/core/provenance_pips.py` with `atr_pips_at` (Wilder ATR) and `swing_pips_from_bars` (lookback high-low range). Every proposer with bar access now stamps `atr_pips` + `h1_swing_pips` on `proposal.rationale` via `stamp_provenance_pips(...)`. Rin's `PRECISION_LIFT` becomes a stop-tightness function 0.05..0.15 so per-trade conviction has real variance.

**Empirical effect:** three C6 passes in the smoke (Bachira 0.179, Chigiri 0.192, Barou 0.160); Rin C6 = 0.088 (one hair short of 0.10); Isagi C6 = 0.053.

### §11.5 (2026-07-01) — Barou devour bump (Phase N companion)

Barou's `BAROU_V1_DEVOUR_LIFT` raised 0.10 → 0.20 and `BAROU_V1_DEVOUR_OBS_FLOOR` lowered 0.7 → 0.5 so the devour condition fires more often and produces a decisive override when it does (final conviction 0.85 > Bachira max 0.75 on USDCAD). Matches the roster's "solo king finishes what Isagi couldn't" narrative frame.

### §11.6 (2026-07-01) — Phase S: F19 variance amplification

**Trigger:** the Phase R walk-forward rerun (Phase N+O+P wiring live)
recorded C5 = 0 for four of six trade-taking agents (Isagi, Rin,
Barou; Nagi at 0.05; Bachira at 0.035; Chigiri at 0.044). Every root
cause moved in the intended direction but no agent cleared the C5
threshold. Diagnosis on the raw verdict + a targeted lot_intent trace
identified three structural gaps:

1. `SupplyDemandAlpha` (Isagi/Bachira/Rin/Barou base source) hardcodes
   `conviction = 0.65`. Every proposal Isagi ever generates has the
   same base conviction — his metavision playstyle never expresses
   itself in the lot output.
2. `regime_fit = 0.5` is a placeholder set on every proposal in the
   panel. `playstyle_lot_intent` sees zero variance on that dimension.
3. `kelly_lot_intent` at `kelly_fraction_cap = 0.025` on a $100 demo
   sandbox produces `dollar_risk = $2.50`. Divided by a typical
   20-40 pip SL and $0.10/pip pip value → 0.6–1.2 min-lot multiples →
   every trade rounds to `MIN_LOT = 0.01`. Rin and Nagi were
   Kelly-saturated at the FLOOR (not the cap) — every trade lot was
   identical.

**Amendment (Phase S wiring):**

- **`regime_fit_from_atr(bars, i)`** helper added to
  `sim/core/provenance_pips.py`. Maps current-bar ATR14 to
  `clip(0.5 * atr / mean_atr, 0.2, 0.8)`. Every proposer with bar
  access now sets `proposal.regime_fit = regime_fit_from_atr(prep.bars, i)`
  instead of the `0.5` placeholder — Isagi, Bachira, Rin, Chigiri,
  Barou all wired in this pass. Nagi keeps `NAGI_V1_REGIME_FIT`
  because his proposal borrows the leader's `entry/stop`; a leader-
  regime-fit borrow is a Phase T follow-up.

- **`isagi_metavision_lift(peers_agree, peers_disagree)`** helper
  added. Returns +0.10 for 2+ peer agree, +0.05 for 1 peer agree with
  no disagreement, -0.05 for majority disagreement, else 0.0. Isagi's
  `intend()` computes `final_conviction = clip(sig.conviction +
  metavision_lift, 0.0, 1.0)` — his metavision reads DO shift his
  proposal conviction now, not just log a diagnostic bit.

- **Playstyle `analytical_precision` (Rin)** switched from
  `kelly_lot_intent(kelly_fraction_cap=0.025, payoff_ratio=2.0)` to
  `conviction_scaled_lot_intent(base_lot=0.05, conviction_pivot=0.60,
  conviction_gain=3.0, max_lot_ceiling=0.15, regime_fit_gain=0.6)`.
  Same precision-floor semantic (small base, aggressive lift on
  above-pivot conviction), but the map is expressed in
  conviction-scaled lots that don't saturate against MIN_LOT on the
  $100 sandbox.

- **Playstyle `confluence_only` (Nagi)** switched from kelly to
  `conviction_scaled_lot_intent(base_lot=0.08, conviction_pivot=0.70,
  conviction_gain=3.5, max_lot_ceiling=0.20, regime_fit_gain=0.5)`.
  Higher pivot because Nagi's `combined_conviction = 1 - Π(1 - c_i)`
  already ranges 0.70..0.95; the steep gain of 3.5 makes that range
  produce lot spreads of 0.06..0.13 — real F19 dispersion.

**Empirical baseline (from Phase R verdict, before this amendment):**

| Agent | C5 | mean_lot |
|---|---|---|
| Isagi | 0.000 | 0.10 constant |
| Rin | 0.000 | 0.01 constant (kelly-saturated at MIN_LOT floor) |
| Nagi | 0.050 | 0.01 constant (same) |
| Barou | 0.000 | 0.11 near-constant |
| Bachira | 0.035 | 0.10 modal |
| Chigiri | 0.044 | 0.11 modal |

**Empirical effect (Phase S walk-forward rerun, tag
`walk-forward-post-NPOS`):** to be recorded once the compute job
lands.

**Doctrine linkage:** §4.1a amended in parallel — the F19 primitive
now includes the `regime_fit_from_atr` mapping as its
"per-bar-regime input" and the "no kelly on the sandbox scale"
rationale for the two playstyle changes.

### §11.7 (2026-07-01 evening) — Phase U: Shadow ledger (diagnostic only)

**Trigger:** the Phase S walk-forward rerun revealed that
`itoshi_rin` regressed to **0 trades / 7 windows** because Isagi's
new metavision peer-alignment lift consistently wins the aggregator
tie-break on the shared `SupplyDemandAlpha` signal. That C1 = 0
would ordinarily fail Rin on the v1 bit vector, but the executed
ledger alone can't tell us whether Rin's alpha is bad (retire) or
her routing is bad (evolve). The user's directive: measure the
hypotheticals — every proposal, accepted or rejected, run through
the fill/exit engine in isolation, so we score the *scouting* skill
independently of the *striker* slot. Blue-Lock canon: agents who
READ plays that end in goals get credit even when someone else
scored, exactly like the 2nd/3rd selection scouting reports.

**Amendment (Phase U wiring):**
- **`sim/scoring/shadow_ledger.py`** — new module.
  `shadow_evaluate_proposal(...)` re-runs any proposal through
  `_open_trade_from_proposal` + `_check_exit` on
  `symbol_bars[i_open+1..i_open+30]`, producing a
  `ShadowTradeRecord` that mirrors `TradeRecord` field-for-field
  plus attribution provenance (`is_shadow`, `rejection_reason`,
  `proposal_tick_id`) and three research-grade quality metrics
  from the quant literature: `entry_efficiency` (Kaufman/Sweeney,
  `1 - MAE / (MAE + initial_risk)`), `exit_efficiency`
  (`pnl / max(MFE, 1)`), `friction_ratio`
  (Almgren-Chriss proxy, `|commission| / max(|pnl|, 1)`).
- **`_drive_squad_replay`** gains an opt-in `use_shadow_ledger=True`
  flag. When on, every accepted **and** rejected proposal produces
  one `ShadowTradeRecord` in `out.shadow_trades`. Default is OFF
  to preserve Φ4/Φ4.1 sealed-verdict replay fidelity.
- **`aggregate_shadow_by_agent(...)`** produces per-agent scouting
  aggregates split into two subsets: shadow-TQS **when accepted**
  (calibration baseline; equals executed-TQS by construction) and
  shadow-TQS **when rejected** (the actual alpha attribution
  signal). The **delta (rejected − accepted)** is the routing-
  quality signal:
    - **strongly negative** (≤ −0.10) → aggregator picked winners;
      crowding-out is a design feature.
    - **~ 0** → aggregator's tie-break is random with respect to
      trade quality; agent's alpha is real but routed away; a
      Phase T-style peer-disagreement or regime-specialist role
      is warranted.
    - **strongly positive** (≥ +0.10) → aggregator picked wrong
      winners; rejected proposals were better; a routing bug.
- **`ShadowAggregate`** also reports per-window CV (reproducibility)
  and per-symbol shadow-TQS spread (symbol-robustness). Full JSON
  schema in `shadow_ledger.py`.

**Diagnostic-only guarantee.** For v1, the shadow ledger CANNOT move
any agent's 6-bit `bachira/isagi/rin/…` vector. Every criterion
C1..C6 remains scored on **executed** trades. Shadow-TQS is emitted
as an appendix (`shadow_by_agent` block in the JSON verdict +
"Phase U — Shadow ledger" markdown section). Any use of shadow-TQS
for promotion (e.g. Φ5 Arm 4 K=2 multi-position lifting) must be
declared as a follow-up amendment (§11.X).

**Systematic bias note.** Shadow trades never face inter-symbol R6
total-risk cap, R4 concentration cap, or per-symbol single-position
rule; they're isolated. This is a known upward bias in raw
shadow-TQS. The bias is corrected implicitly by comparing
**accepted vs rejected** for the same agent (both subsets suffer
the same upward bias), which is why the delta is the actual signal
and the raw mean shadow-TQS is context only.

**Doctrine linkage:** §4.1a amended in parallel to declare
Phase U diagnostic-only and to reference the Blue-Lock canon frame
for "scouting record vs striker record".

**Empirical seed (from 2024 OOS dry-run,
tag `phase-u-smoke2`):**

| Agent | N shadow | TQS acc | TQS rej | Δ (rej-acc) | Reading |
|---|---:|---:|---:|---:|---|
| Isagi | 1177 | 0.324 | 0.249 | −0.075 | aggregator picks winners |
| Bachira | 2772 | 0.330 | 0.327 | −0.003 | tie-break random for her |
| Rin | 211 | n/a | 0.254 | n/a | 0 accepted -- crowded out |
| Chigiri | 154 | 0.188 | 0.253 | +0.065 | rejected > accepted (routing bug) |
| Nagi | 135 | 0.282 | n/a | n/a | 0 rejected (all his fire) |
| Barou | 905 | 0.288 | 0.315 | +0.027 | mild routing bug |

The Rin `n/a` and Chigiri positive delta are the two Phase-T-relevant
signals; the full 7-window walk-forward rerun will register the
locked numbers.

### §11.8 (2026-07-01 evening) — Phase T-evolve: Rin v1.1 peer-yield-and-lift

**Trigger:** Phase S walk-forward showed Rin regressing to 0 trades
across all 7 OOS windows. Phase U shadow-ledger 2024 dry-run
confirmed she fires 211 shadow proposals with mean shadow-TQS
0.254 but 0 accepted (crowded out by Isagi's metavision lift).
Retirement was rejected by the user: Rin and Isagi evolve off each
other in canon; the fix is to give Rin a mechanic that scores where
Isagi can't, not to replace her.

**Amendment (Phase T-evolve wiring):**
- **`sim/agents/a03_rin.py`** — Rin v1.1 `intend()` now reads peer
  thoughts from the F21 workspace snapshot. Computes
  `peer_agree_count` and `peer_disagree_count` relative to her
  proposed direction (mirroring the exact math Isagi's
  `isagi_metavision_lift` uses). If Isagi's metavision would fire
  (`peer_agree>=1 & peer_disagree==0`), Rin **yields** (returns
  None from `intend()`). Otherwise Rin applies an additional
  `RIN_V1_LONE_READ_LIFT = +0.10` on top of the precision lift,
  reaching final conviction 0.90 (0.65 base + 0.15 precision +
  0.10 lone-read) — enough to decisively beat Isagi's base 0.65
  on ticks where his metavision doesn't fire.
- **Rationale trail** gains 6 new fields (`peer_agree_count`,
  `peer_disagree_count`, `peer_seen_count`,
  `isagi_would_lift_metavision`, `lone_read_lift_applied`,
  `lone_read_lift`) for post-hoc attribution.
- **Doctrine §4.1c** written in parallel with the mechanic spec +
  the delta-sign acceptance test.

**Empirical acceptance test (measured on walk-forward-post-TU):**
Rin's Phase-U shadow ledger delta = `mean_shadow_tqs_when_rejected
- mean_shadow_tqs_when_accepted` must be:
- **≤ −0.05** → routing improvement is real; Phase T-evolve
  clears; commit and update roster to `v1.1 confirmed`.
- **~ 0** → routing improved but shadow alpha didn't; Rin's v1
  status remains `PENDING_MECHANIC_ITER_3`; consider v1.2
  regime-specialist or symbol-expansion iteration.
- **> +0.05** → yield rule dropped her best trades; **REVERT** to
  v1.0 (precision-only). Amendment rolled back with a
  §11.X postmortem.

**Pre-Phase-T-evolve baseline (locked, from walk-forward-post-U):**
to be recorded once that job lands. Phase T-evolve numbers
(walk-forward-post-TU) will be scored against this baseline.

### §11.9 (2026-07-02) — Phase V design draft: Chigiri regime-specialist + Barou solo-king

**Status:** DESIGN DRAFT ONLY. Pre-registered pending
walk-forward-post-F22 verdict which will re-measure the deltas
below. If post-F22 keeps Chigiri delta ≥ +0.03 and/or Barou delta
≥ +0.01, Phase V lands as follows; otherwise the design is amended
or dropped.

**Trigger (measured on walk-forward-post-TU):** Two agents show
positive `Delta (rej-acc)` in the Phase U shadow ledger, meaning
the aggregator is dropping their better trades and accepting their
weaker ones -- the opposite of Rin's negative delta which signaled
correct routing:

| Agent    | tqs_acc | tqs_rej | Δ (rej-acc) | Reading |
|----------|---------|---------|-------------|---------|
| Chigiri  | 0.242   | 0.285   | +0.044      | Small routing sub-optimality |
| Barou    | 0.302   | 0.317   | +0.015      | Persistent 90% rejection rate; the rejected 10% is fractionally better than the accepted 10% |

Post-TU F22 impact expected to be MODEST -- F22b (barrier snapshot)
lets Chigiri and Barou see Isagi's same-tick metavision Thought,
which may cause them to yield differently, but they don't have a
Phase T-evolve-style yield rule (yet). Their deltas should stay
positive but may shift by ~0.01.

**Phase V-a — Chigiri regime-specialist (proposed).**

*Canon frame.* Chigiri is a speed-and-momentum striker; his edge
is highest when the market is ALREADY in vol-expansion. On chop or
mean-reversion regimes, his breakout signals stall out -- exactly
the ticks where the aggregator rejects him in favour of Isagi's
zone-fade.

*Mechanic.* Introduce a regime-conditional tier-1-equivalent bias
for Chigiri when the F22a-populated `ThoughtRead.regime_read ==
"vol_expansion"` AND ATR on the entry bar exceeds a threshold
`CHIGIRI_V1_REGIME_ATR_PCT` (e.g. > 75th percentile of trailing
14-bar ATR). Concretely, in `run_phi4_squad_gate` aggregator,
before the tier-1 anchor bias applies, check:

    if proposal.agent_id == "chigiri_hyoma" and _chigiri_regime_bonus(...):
        # tier-1-equivalent conviction lift
        effective_conviction += CHIGIRI_V1_REGIME_LIFT   # e.g. +0.05

This is a NARROW carve-out: only Chigiri, only on vol-expansion
regime bars, only when his F22a read confirms `vol_expansion`.
Analogous to Phase T-evolve's peer-yield-and-lift for Rin.

*Acceptance test (walk-forward-post-VA):* Chigiri's Phase-U delta
moves from `+0.044` to `≤ +0.02`, meaning the routing improves.
Aggregate squad TQS must not regress by more than 0.005.

**Phase V-b — Barou solo-king clarification (proposed).**

*Canon frame.* Barou is the "counter-liquidity" solo-king: he's
sharp when he devours (his F22a `regime_read == "devour_active"`
tag fires when his direction opposes Isagi's active position).
Non-devour proposals are baseline-zone at his standard tier-2
conviction and rightly compete with Bachira; the aggregator's
current 90% rejection is CORRECT for those. The 10% that IS
accepted is roughly random within the tier-2 tie-break, hence the
+0.015 delta.

*Mechanic.* When Barou's `regime_read == "devour_active"`, apply
the same tier-1-equivalent conviction lift as Chigiri's Phase V-a
(`BAROU_V1_DEVOUR_LIFT_ROUTING`, e.g. +0.05). Non-devour proposals
stay at baseline conviction and continue to be rightly filtered.

*Acceptance test (walk-forward-post-VB):* Barou's Phase-U delta
on the `devour_active` subset moves from ~+0.015 to `≤ 0.0`.
Non-devour subset delta unchanged. Aggregate squad TQS must not
regress by more than 0.005.

**Order:** Phase V-a first (Chigiri; higher delta = higher signal).
Phase V-b only if V-a lands cleanly, otherwise the interaction
between two simultaneous tier-1-equivalent lifts confounds the
attribution.

**Statistical honesty guards.** Same as Phase T-evolve: revert if
delta moves the wrong way, log postmortem in §11.X. No hyper-
parameter tuning after the walk-forward is scored. Any parameter
change (`CHIGIRI_V1_REGIME_ATR_PCT`, `..._LIFT`) requires a fresh
walk-forward + full amendment.

---

### §11.9-implementation (2026-07-02) — Phase V-a + V-b landed

**Status:** IMPLEMENTED, unit-tested, awaiting walk-forward-post-V.

The design in §11.9 was refined during implementation from a hard
conviction lift to a **rationale-flagged effective-tier promotion**,
because tier-based mixing (TIER_BIAS on Tier-2 agents in
`_tier_adjusted_conviction`) is where the routing loss actually
happens -- lifting raw conviction would double-count the tier bias
in some paths. The final mechanic is thinner and more auditable:

**Aggregator carve-out (`sim/scoring/run_phi4_squad_gate.py`).**
Added `_EFFECTIVE_TIER_RATIONALE_KEY = "_effective_tier"` constant
and `_effective_tier(proposal, roster)` helper. The helper reads
`proposal.rationale["_effective_tier"]` (if present and valid) and
uses it in `_tier_adjusted_conviction` + the ordering key of
`_phi4_aggregate`'s sort. The override cannot demote a tier-1 agent
(Isagi/Bachira stay tier-1 regardless), so the only observable
behaviour is a tier-2 agent being ranked at tier-1 parity on the
specific ticks where the specialist bit fires.

**Phase V-a (Chigiri) — implemented in `agents/a04_chigiri.py`.**
Constants `CHIGIRI_V1_REGIME_MIN_MAG_ATR = 1.5` and
`CHIGIRI_V1_REGIME_ATR_MULT = 1.5`. `intend()` now computes:

    mag_atr_ratio       = abs(entry - stop) / atr(entry_bar)
    atr_expansion_ratio = atr(entry_bar) / median(atr, prior 20 bars)

Both are always stamped into `rationale` for audit
(`chigiri_mag_atr_ratio`, `chigiri_atr_expansion_ratio`). If BOTH
are `>= 1.5`, `rationale["chigiri_regime_specialist"] = True` and
`rationale["_effective_tier"] = 1`. Analogous to Phase T-evolve's
peer-yield-and-lift, this is a narrow carve-out that only fires on
Chigiri's canon regime (high-magnitude breakout into vol-expansion).

**Phase V-b (Barou) — implemented in `agents/a07_barou.py`.**
When `"barou_devour_applied" in my_recent_thought.tags` (i.e. the
F19-aware ledger read confirmed Barou's devour lift already fired
in `observe()`), `intend()` stamps
`rationale["barou_solo_king_specialist"] = True` and
`rationale["_effective_tier"] = 1`. Non-devour proposals stay
tier-2 with no rationale override -- they continue to compete
rightly with Bachira on raw conviction, and the aggregator's ~90%
rejection stays correct for that subset.

**Unit tests.** `test_phase_v_regime_specialist.py` (7 tests) plus
`TestPhaseVA_ChigiriRegimeSpecialist` in `test_a04_chigiri_wrap.py`
(3 tests) and `TestPhaseVB_BarouSoloKingSpecialist` in
`test_a07_barou_wrap.py` (2 tests) cover:
- default `_effective_tier` matches agent tier
- rationale override promotes tier-2 → effective tier-1
- override never demotes tier-1
- malformed override falls back to agent tier
- `_tier_adjusted_conviction` removes the TIER_BIAS penalty for
  promoted proposals
- specialist Chigiri beats an equal-conviction Isagi
- non-specialist Chigiri still loses to Isagi
- specialist Chigiri still loses to a stronger Isagi
- specialist bit absent on routine breakout / absent when devour
  didn't fire

**Acceptance test (walk-forward-post-V, kicked off 2026-07-02).**
Combined test since V-a and V-b touch the same rationale mechanism:
- Chigiri Phase-U delta `+0.049` (post-F22) → target `≤ +0.02`
- Barou Phase-U delta `+0.015` (post-F22) → target `≤ 0.0`
- Aggregate squad TQS regression `≤ 0.005` vs walk-forward-post-F22

If either delta moves the wrong way, revert the corresponding
rationale-stamp (mechanic revert, tests kept as regression guards)
and log postmortem in §11.X.

---

### §11.9-postmortem (2026-07-02) — Phase V-a + V-b NULL RESULT

**Verdict:** REVERT. Both Phase V-a and Phase V-b failed their pre-
registered acceptance criteria on `walk-forward-post-V`. The active
mechanic (rationale stamps `_effective_tier=1`) was surgically
reverted; the aggregator plumbing (`_effective_tier` helper) and
diagnostic ratios are retained as regression scaffolding and audit
surface for a future Phase V-iterate.

**Observed vs target (post-F22 → post-V, exact from JSONs):**

| Agent   | N_shadow | N_flips | Δ_post-F22 | Δ_post-V | Change    | Target      | Verdict |
|---------|---------:|--------:|-----------:|---------:|----------:|:------------|---------|
| Chigiri | 992      | +1      | +0.04887   | +0.05085 | +0.00198  | ≤ +0.02     | FAIL (moved WRONG way) |
| Barou   | 4576     | 0       | +0.01488   | +0.01488 | 0.00000   | ≤ 0.0       | FAIL (no movement)      |

Side-effect check on other agents (must not regress):

| Agent   | Δ_post-F22 | Δ_post-V | Change    | Verdict |
|---------|-----------:|---------:|----------:|---------|
| Rin     | −0.14622   | −0.14693 | −0.00071  | ✓ robust (regression guard held) |
| Isagi   | +0.00507   | +0.00507 | 0         | ✓ no side-effect on tier-1 |
| Bachira | −0.01275   | −0.01275 | 0         | ✓ no side-effect |
| Nagi    | n/a        | n/a      | n/a       | ✓ no side-effect (0 rejected) |

Aggregate squad totals unchanged: 5604 trades, 28842 shadow trades on
both runs. No squad TQS regression.

**Root cause -- why the mechanic fired but the routing didn't move.**

The final implementation (see §11.9-implementation) used a rationale-
flagged effective-tier promotion instead of the raw conviction lift
originally proposed. The theory was: neutralise the `-TIER_BIAS`
penalty on specialist ticks, and Chigiri/Barou can now win same-
conviction tiebreaks against Isagi.

**Empirically, the theory is wrong for this squad.** The raw
conviction distributions are:

- Isagi metavision: base 0.85, boosted to 0.90-1.00 on his D1
  alignment path.
- Chigiri breakout: base 0.70, boosted to 0.85-0.95 on his
  magnitude-boost path.
- Barou solo-king: base 0.65, boosted to ~0.85 on `devour_applied`.

`TIER_BIAS` is a fixed 0.05 penalty (see `run_phi4_squad_gate.py`).
Promoting Chigiri/Barou removes 0.05 from their adjusted-conviction
penalty -- but the raw gap on their winning ticks averages 0.08-0.12
in Isagi's favour. Removing 0.05 does NOT close the gap; Isagi still
wins.

Additionally, the `mag/atr >= 1.5 AND atr/median_atr >= 1.5` double
hurdle restricts Chigiri's specialist bit to genuinely unusual bars
(~5% of his fires), and on those bars Isagi's metavision typically
ALSO scores highly because vol-expansion regimes are exactly what
Isagi's D1-alignment path is designed for. The two agents peak
together, and Isagi's raw margin dominates the tier bias adjustment.

For Barou: the `barou_devour_applied` tag fires by definition when
his direction OPPOSES Isagi's active position. So Isagi has already
executed on that tick with high conviction. Barou's devour lift plus
tier promotion still doesn't beat Isagi's raw conviction on the same
tick. Result: zero flips.

**What survives (regression scaffold + audit surface).**

Retained:

1. `_effective_tier` helper + `_EFFECTIVE_TIER_RATIONALE_KEY` in
   `sim/scoring/run_phi4_squad_gate.py`. Regime-neutral: no side-
   effect unless a proposal actively stamps the key.
2. Chigiri's specialist-bit ratio computation (`mag_atr_ratio`,
   `atr_expansion_ratio`, `chigiri_regime_specialist` boolean) in
   `sim/agents/a04_chigiri.py`. Written to rationale for audit.
3. Barou's `barou_solo_king_specialist` boolean in rationale.
4. Aggregator-side tests in `test_phase_v_regime_specialist.py`
   (docstring updated to reflect they test plumbing, not an active
   mechanic).

Reverted:

1. `proposal_rationale["_effective_tier"] = 1` stamp in
   `sim/agents/a04_chigiri.py::intend`.
2. `rationale["_effective_tier"] = 1` stamp in
   `sim/agents/a07_barou.py::intend`.
3. `TestPhaseVA_ChigiriRegimeSpecialist` +
   `TestPhaseVB_BarouSoloKingSpecialist` updated to assert the tier
   override is ABSENT; a new
   `test_specialist_bit_is_diagnostic_not_routing` in Barou's suite
   makes the null-result explicit as a regression guard.

**Next-mechanic hypotheses (parked for a future Phase V-iterate).**

Do NOT implement without a fresh pre-registration + fresh walk-
forward. Statistical honesty guard: no in-place tuning of Phase V
thresholds.

- **Option A -- per-tick conviction LIFT** (the original §11.9 draft).
  On specialist ticks, add e.g. +0.10 to base conviction (not just
  neutralise the tier bias). Would raise Chigiri from 0.85 to 0.95
  on specialist ticks, potentially clearing Isagi's 0.90-1.00 range
  on boundary cases. Risk: over-firing where Isagi is also correct.

- **Option B -- symbol-conditional slot reservation.** When both
  Isagi and Chigiri fire on the same tick with Chigiri in specialist
  regime, PROMOTE Chigiri's proposal to a dedicated slot instead of
  forcing them through R6. Requires aggregator changes beyond a
  per-proposal flag.

- **Option C -- Phase T-evolve-style peer-YIELD** (analogous to Rin).
  When Chigiri detects Isagi is on the same-direction metavision
  path, Chigiri YIELDS (returns a `YieldReason`) instead of
  proposing. When Isagi disagrees or is quiet, Chigiri proposes
  normally with a lone-read lift. This is a mechanic evolution, not
  a routing hack. Direct analogue to the proven Rin v1.1 mechanic.

- **Option D -- concede.** The +0.049 / +0.015 deltas are small in
  absolute terms and may reflect canon role: complementary readers
  that occasionally get out-competed on tiebreaks. C2/C3 leave-one-
  out results (still pending, ~32h compute) will show whether
  removing them hurts squad TQS. If not, their crowding is a feature
  not a bug.

**Recommended sequencing:** Option D (concede) first -- measure C2/C3
before designing another mechanic. If C2/C3 shows Chigiri/Barou
contribute counterfactual alpha, Option C (peer-YIELD) is the natural
analogue to Rin's proven Phase T-evolve. Option A is tempting but
risks over-firing without more analysis of the ratio distribution.

### §11.10 (2026-07-03) — G7 Role Registry v1 companion test lands

Post-V C2/C3 verdict (`reviews/g7_leave_one_out_verdict_post-V.md`)
identified 3 agents failing strict C2 (Nagi, Barou, Kunigami). Rather
than remove them, we pre-registered `experiments/G7_role_registry_v1/PROTOCOL.md`
adding three ADDITIVE role-differentiating criteria to G7 v1's 6-bit
vector:

- **C7** — Incoming chemistry (finisher role). Agent X passes if ≥ 2
  peers lift X's mean TQS by ≥ 0.02 when they are present. Nagi passes
  strongly (Bachira +0.1979, Rin +0.0886, Reo +0.0719 TQS).
- **C8** — Workspace-signal impact (v1 proxy). Peer-delta magnitude
  score in epsilon-units. Reo: 245.4 (real gatekeeper). Kunigami:
  **0.0 exactly** (dead-weight publisher — his §11.1 waiver becomes
  a rubber stamp).
- **C9** — Trade-volume floor. Agent holds ≥ 5% of squad trades. Waived
  for structural falsifiers (Reo, Kunigami).

Retention rule: pass C3 AND at least one of {C2, C7, C8, C9}. Emit role
labels: `chemistry_catalyst`, `finisher`, `workspace_catalyst`,
`volume_specialist`, `retirement_candidate`.

**Post-V retention outcomes:**

| Agent | Role label(s) | Retained |
|---|---|:---:|
| `isagi_yoichi` | chemistry_catalyst, workspace_catalyst | ✅ |
| `bachira_meguru` | chemistry_catalyst, workspace_catalyst | ❌ (C3 fail on Barou 84.1%) |
| `itoshi_rin` | chemistry_catalyst, workspace_catalyst | ✅ |
| `chigiri_hyoma` | chemistry_catalyst, workspace_catalyst | ✅ |
| `reo_mikage` | chemistry_catalyst, workspace_catalyst | ✅ |
| `nagi_seishiro` | **finisher**, workspace_catalyst | ✅ |
| `barou_shoei` | workspace_catalyst (thin single axis) | ✅ (pending Phase W-barou / Phi5 Arm 3/4) |
| `kunigami_rensuke` | **retirement_candidate** | ❌ |

Kunigami retirement decision doc drafted at
`experiments/G7_role_registry_v1/DECISION_kunigami.md` (Options A retire
[recommended] / B re-evolve / C wait for C8 v2). Awaits user sign-off
before landing amendments §11.12 (roster reduction).

C8 v1 uses peer-delta magnitude proxy; true `IntentDecision.interpreted_signal_family`
citation count deferred to C8 v2 pending intents.jsonl persistence
(see Role Registry PROTOCOL §12).

Commits: `3c1ce7d` (spec + C7/C8/C9 aggregator + regenerated verdict).

### §11.11 (2026-07-03) — Phase W-barou v1.1 landed as NULL RESULT

Pre-registered at `experiments/phase_w_barou/PROTOCOL.md` (H1 lone-
conviction claim; H2 continuation-entry offset deferred to v1.2 pending
Phi5 Arm 4). H1 mechanic: when Bachira did NOT publish same-direction
on Barou's symbol at the tick barrier, apply
`BAROU_V1_1_LONE_CONVICTION_LIFT = 0.10`. Locked acceptance thresholds
(LAND if n_trades ≥ 250 AND mean_tqs ≥ 0.34 AND Bachira→Barou
cannibalisation ≤ 0.60; REVERT if n_trades < 100 or mean_tqs < 0.30).

walk-forward-post-W measured (2026-07-03 UTC): **byte-identical to
post-V.** Every per-agent trade count and mean_TQS matches to four
decimal places (Barou 153/0.3469 both runs; Bachira 2542/0.4026 both
runs; all others 0/0.0 delta). Same 5604 total trades, 28842 proposals,
336707 thoughts, identical workspace_counts.json.

Verdict: **AMBIGUOUS zone per PROTOCOL §5** — no auto-land, no
auto-revert. Postmortem written at
`experiments/phase_w_barou/POSTMORTEM.md`.

Root cause: H1 only fires when Bachira did NOT compete on Barou's
slot. On those ticks, Barou was already the sole proposer -- his
proposal was going to win the R6 tournament with or without the +0.10
lift. The ticks where Barou is BLOCKED (Bachira same-direction same-
slot) explicitly fall through H1's skip branch. Same structural
failure mode as Phase V-b (§11.9-postmortem 2026-07-02): agent-side
conviction lift cannot flip aggregator single-slot mutex.

**Resolution:**
- Leave H1 code in place as DIAGNOSTIC-ONLY (Phase V-b precedent).
  The new rationale fields (`barou_lone_conviction_claim`,
  `barou_v1_1_bachira_read_present`, `barou_v1_1_bachira_same_direction`,
  `_yield_reason`) are useful for post-hoc audits and for Phi5 Arm 3/4
  pre-registration analysis.
- Do NOT ship a Phase W-barou-v1.2 at the agent-conviction level.
  Direct competition path is closed.
- Escalate to Phi5 Arm 3 (same-direction merge) as the primary
  intervention, Arm 4 (multi-position) as fallback.

Commits: `d81bd46` (v1.1 landing) + postmortem (this amendment).

---

### §11.12 (2026-07-06) — Kunigami retirement (Role Registry v1 C8 fail) + Wild Card return path

**User decision (2026-07-06):** Option A from
`experiments/G7_role_registry_v1/DECISION_kunigami.md` — RETIRE — with
the canon-faithful return path pre-registered below.

**Empirical trigger.** Role Registry v1 C8 (workspace-signal impact,
v1 peer-delta-magnitude proxy) measured `kunigami_rensuke` at exactly
**0.0 epsilon-units**: across the full post-V leave-one-out panel, no
peer's trade count or mean TQS moves by any amount when Kunigami is
removed. His 53,164 workspace publishes are consumed by no peer
decision. The §11.1 defensive-observer waiver was ratified on the
hypothesis that his warnings influence peers; C8 tested exactly that
hypothesis and it failed. Retention rule (C3 ∧ any of {C2,C7,C8,C9})
→ NOT RETAINED; only agent in the squad labelled
`retirement_candidate`.

**Why not wait for C8 v2 (true citation counts)?** C8 v2 can only
produce (a) zero citations — confirming retirement — or (b) nonzero
citations whose downstream effect is provably zero (the v1 proxy
already measured the effect side), which still fails retention. The
decision cannot flip; waiting is compute without information.

**Implementation (roster-construction flag, NOT constant deletion):**
- `run_g7_v1_checkpoint_gate.run_g7_walk_forward(include_kunigami=False)`
  + CLI `--retire-kunigami` remove him from the PROPOSER/PUBLISHER
  roster.
- His instance KEEPS feeding the Sentinel R5 anti-tilt side channel
  (`record_closed_trade` / `warning_active_at`) — this is exactly the
  configuration the C2/C3 lo1_kunigami_rensuke replay measured, so the
  retirement baseline inherits the lo1 evidence without a new
  unmeasured behaviour change. Deprecating the R5 channel would be a
  SEPARATE experiment; it was not measured and is not part of this
  amendment.
- `G7_AGENT_ORDER` / `STRUCTURAL_FALSIFIERS` constants are retained so
  old post-V artifacts stay readable; verdict loops skip agents absent
  from the roster.
- `sim/agents/a10_kunigami.py` retained (audit trail + R5 channel).

**Baseline regeneration.** A fresh
`walk-forward-post-kunigami-retirement` runs with the current code
(NOT reusing the lo1 cache: Barou v1.1 H1 landed after the LOO batch,
and the lo1 cache lacks the proposals stream). Expected near-identical
to lo1_kunigami_rensuke trade outcomes; any deviation is investigated
before Φ5 arms run. This baseline is the Φ5 re-sim comparator (see
phi5_aggregator PROTOCOL §11.4).

**Wild Card return path (pre-registered design direction, not yet a
protocol).** Canon: Kunigami is eliminated, sent to the Wild Card
program, and returns as a physical enforcer — stealing goals and
defending, not talking. Mapped to our architecture this is DECISION
doc Option B3: an **aggregator-side drawdown gate** — veto power over
new position openings when squad drawdown breaches a threshold
(defending the goal), plus possible slot-steal semantics in extreme
regimes. That is Φ5-family work and will be pre-registered as its own
`phase_x_kunigami_wildcard` protocol AFTER the Φ5 Arm 3/4 verdicts
land. Kunigami does not return as a workspace publisher.

Roster is now **7 agents**: isagi, bachira, rin, chigiri, reo, nagi,
barou. The G7 §12 registry row's "all 8 agents" conjunction becomes
"all 7 rostered agents" from this amendment forward.

---

### §11.13 (2026-07-14) — G7 v1 checkpoint gate FINAL verdict: **FAIL (1/7)**

**Status:** gate FIRED. All six criteria computed end-to-end for the
§11.12 7-agent roster. Evaluator: `sim/scoring/run_g7_final_verdict.py`
(commit `5d5c1d1`, implementation + 36 tests committed BEFORE any gate
run), consuming on-disk replay caches — no new replay compute was
required because the banked caches already cover the full panel.

**Aggregator-arm decision.** §4 of this protocol pins the Φ4.1
aggregator ("the G7 gate is about *agent-side* chemistry, not
aggregator selection") and predates the Arm 4 adoption
(phi5_aggregator §11.6, 2026-07-06). No amendment changed §4, so the
**verdict-bearing run is phi41**. Because Arm 4 is the adopted G7-era
default for all other squad work, an **Arm 4 companion run** is
reported alongside (clearly labelled, non-verdict-bearing). The
tension is noted here rather than silently resolved.

**Inputs (cache reuse justification).**

| Run | Baseline cache | lo1 caches |
|---|---|---|
| phi41 (verdict) | `reviews/g7_replay_cache_walk-forward-post-kunigami-retirement` | `reviews/g7_leave_one_out_post-V/lo1_*` (8) |
| arm4 (companion) | `reviews/g7_replay_cache_phi5-arm4-post-kunigami` | `reviews/g7_leave_one_out_phi5-arm4/lo1_*` (7) |

Reuse is sound because (verified 2026-07-14, this session): the
kunigami-retirement baseline is byte-identical in per-agent
n_trades/mean_TQS to both the post-V baseline and the post-V
`lo1_kunigami_rensuke` cache — current code reproduces the post-V
phi41 trade stream exactly (Barou v1.1 H1 and Phase X gate are inert /
off by default), and Kunigami's presence in the post-V lo1 squads is a
no-op (Role Registry C8 = 0.0 exactly). The arm4 caches were produced
under the retired roster directly (§11.6 B).

**Evaluator specifics (locked before results were seen).**

- All statistics OOS-only (union of the 7 rolling OOS windows,
  2019–2025). NOTE: the earlier DIAGNOSTIC lo1 verdicts
  (`g7_leave_one_out_verdict_*.md`) pooled IS+OOS; numbers differ.
- C1 per §3 letter: panel mean ≥ 0.30 AND window mean ≥ 0.20 in ≥ 5/7
  AND bootstrap 95 % CI lower bound > 0.25 (percentile, n=10,000,
  seed 42).
- C2 per §3 letter: a peer qualifies via (TQS route) trade-level
  bootstrap CI lower bound > 0 on `mean_tqs(baseline) − mean_tqs(lo1)`,
  or (count route) strictly positive total trade-count delta with a
  window-level bootstrap CI lower bound > 0. Stricter than the
  diagnostic C2's fixed epsilons — several diagnostic C2 passes do not
  survive the CI gate.
- C3 per §3 letter: per-window reduction ratios, pass iff ≥ 4/7 clean
  windows. The `lo1_n = 0` branch is scored 0.0 (no attributable
  reduction); the diagnostic aggregator's 1.0 return for that branch
  is wrong-signed and was NOT used for the gate.
- C4: panel-wide publish/read counters (per-window counts are not
  persisted in caches — documented harness limitation).
- C5/C6: panel-wide CVs per §3 letter (not the harness's stricter
  all-7-windows fold), recomputed from cached `source_*` trade fields
  through the pure playstyle-dispatched F19/F20 primitives.

**Verdict-bearing result (phi41): FAIL — 1/7 agents pass (< 5).**

| Agent | Bit vector | Failing criteria (statistic vs threshold) |
|---|---|---|
| isagi_yoichi | `111100` | C5 CV 0.086 < 0.10; C6 CV 0.083 < 0.10 |
| bachira_meguru | `110101` | C3 0/7 clean windows (Barou reduced 76–97 % every window); C5 CV 0.089 |
| itoshi_rin | `111110` | C6 CV 0.086 |
| chigiri_hyoma | `001111` | C1 mean 0.267 < 0.30; C2 no peer clears CI gate |
| reo_mikage | `W11WWW` | **v1 PASS** (waivers §11.1 + C2 pass via Rin, C3 7/7 clean) |
| nagi_seishiro | `101100` | C2 fail; C5 CV 0.000; C6 CV 0.000 (constant lots/stops) |
| barou_shoei | `001101` | C1 CI lower 0.247 ≤ 0.25 (n=62); C2 fail; C5 CV 0.068 |

**Companion result (arm4): FAIL — 1/7** (isagi `101100`, bachira
`110111`, rin `111110`, chigiri `001111`, reo `W11WWW` PASS, nagi
`101100`, barou `101111`). Arm 4 moves real needles — Barou goes
5/6 (C1 passes at n=322, C5/C6 pass; only C2 fails) and Bachira's C3
worst-window reduction drops from 0.76–0.97 to 0.43–0.62 — but the
squad verdict is unchanged.

**Discussion.**

1. **Bachira C3 is the known duplication artifact.** Phase W-barou
   v1.2 (§11.11 lineage, POSTMORTEM_v1.2) established Bachira and
   Barou wrap the SAME `SupplyDemandAlpha` on shared symbols — the
   "cannibalisation" is literal strategy duplication, an agent-level
   identity problem no aggregator can fix. C3 is applied here AS
   PRE-REGISTERED; the parked distinctness-aware C3 v2 definition was
   NOT invented mid-gate. Under a C3 v2 that nets out duplicate-alpha
   pairs, Bachira would plausibly flip; that requires a fresh
   pre-registration.
2. **C5/C6 are the broadest blocker** — five of six trade-taking
   agents fail at least one dispersion criterion, mostly marginally
   (0.068–0.089 vs 0.10). Nagi is the extreme case: exactly zero
   dispersion (constant conviction × constant `NAGI_V1_REGIME_FIT`
   into the F19/F20 maps). Same Phase-S root cause family as §11.6.
3. **C2 under the CI letter is hard for low-volume agents.** Chigiri,
   Nagi, Barou fail C2 in both arms — their peer-lift deltas are real
   in sign in places but never clear the bootstrap CI gate. This is
   consistent with the Role Registry finding that their retention
   axes are C7/C8/C9, not C2.
4. **Per doctrine §3.11.5:** FAIL (< 5 agents) — **no v2 arc is
   authorised**; all v2 backlog items stay parked. The graduation
   decision toward live paper mode is the user's; this verdict is the
   pre-condition input to it, and the pre-condition is NOT met.

**Artifacts:** `reviews/g7_v1_checkpoint_final_g7final-phi41.{md,json}`
(verdict-bearing) and `reviews/g7_v1_checkpoint_final_g7final-arm4.{md,json}`
(companion). Full per-peer bootstrap CIs and per-window C3 tables are
in the JSONs.

---

### §11.14 (2026-07-14) — C3 v2 distinctness-aware definition (pre-registered, ADVISORY pending user ratification)

The user authorized formalizing the C3 v2 definition parked at Phase
W-barou v1.2 (§11.13 discussion item 1). The full pre-registration —
trade-plan identity key, statistic, predictions, stop rules — lives in
`experiments/c3_v2_distinctness/PROTOCOL.md`, committed BEFORE any C3
v2 number was computed.

Summary of the definition: per (excluded agent `a`, peer `p`, window),
the reduction ratio is computed on the peer's **distinct** trades only,
where a trade is non-distinct iff its (symbol, direction,
source_tick_id, entry, stop, take_profit) key — rounded to 1e-7 —
matches a baseline trade of `a`. Thresholds (0.50 reduction, 4-of-7
clean windows) are UNCHANGED from §3 Criterion 3.

**Ratification status: C3 v1 remains verdict-bearing.** All C3 v2
outputs (on the §11.13 banked caches and on any future gate attempt)
are reported side-by-side as ADVISORY until the user ratifies this
amendment. If ratified, the ratification note and effective gate
attempt will be recorded here.

---

### §11.15 (2026-07-14) — Second gate attempt pre-registration (post three-lever campaign)

The user authorized a three-lever campaign against the §11.13 blockers:

1. **Phase Y — Barou v1.3 weapon differentiation**
   (`experiments/phase_y_barou_weapon/PROTOCOL.md`): D1 with-trend
   gate (Isagi's locked gate params, mode flipped) + structural TP +
   `stop_atr_mult=1.0`, USDCAD only. Changes Barou's trade stream.
2. **C3 v2** (§11.14, advisory).
3. **Dispersion primitives round 2**
   (`experiments/dispersion_primitives_r2/PROTOCOL.md`):
   risk-normalised F19 sizing for the four failing-C5 playstyles,
   Isagi C6 full-ATR proportionality, Rin C6 de-saturation, Nagi
   provenance wiring (leader-borrowed atr/swing + Phase-S regime_fit
   map). Changes NO trade stream.

**Re-gate plan (single OOS touch, pre-registered):** fresh walk-forward
baseline + 7 leave-one-out replays per arm (phi41 verdict-bearing per
§4 pin; arm4 companion), 7-agent §11.12 roster, with Phase Y +
dispersion-r2 code active. `run_g7_final_verdict.py` then produces the
per-agent C1–C6 table and squad verdict recorded as **§11.16**. C3 v1
is verdict-bearing; C3 v2 reported alongside (advisory). Same
bootstrap spec as §11.13 (n=10,000, seed 42, percentile, α=0.05).
Success criteria for the individual levers are in their own protocols;
the squad graduation decision on the §11.16 result stays with the
user. Implementation + tests are committed before replays run; replay
caches follow the existing `g7_replay_cache_*` / `g7_leave_one_out_*`
naming with tag `g7retry1`.

---

### §11.16 (2026-07-14) — Second gate attempt FINAL verdict: **FAIL (3/7 phi41; 2/7 arm4)**

**Status:** the second gate attempt pre-registered in §11.15 has fired.
Evaluator: `sim/scoring/run_g7_final_verdict.py` (unchanged from §11.13),
consuming the freshly banked `g7retry1` replay caches — no post-freeze
retuning. Both aggregator arms remain FAIL under §3.11.5 (< 5/7 agents
pass all six criteria). The full three-lever campaign (Phase Y Barou
v1.3 weapon + dispersion-r2 primitives + C3 v2 advisory) moved real
numbers, but not enough of the C2/C3 blockers.

**Aggregator-arm decision.** §4 continues to pin the Φ4.1 aggregator
(the tension noted in §11.13 is unchanged), so the **verdict-bearing
run is phi41** with an **Arm 4 companion**.

**Inputs.**

| Run | Baseline cache | lo1 caches |
|---|---|---|
| phi41 (verdict) | `reviews/g7_replay_cache_g7retry1-phi41` | `reviews/g7_leave_one_out_g7retry1-phi41/lo1_*` (7) |
| arm4 (companion) | `reviews/g7_replay_cache_g7retry1-arm4` | `reviews/g7_leave_one_out_g7retry1-arm4/lo1_*` (7) |

Both caches were produced by fresh walk-forward + LOO replays under
Phase Y (Barou v1.3 weapon, USDCAD only, D1 with-trend gate + structural
TP + `stop_atr_mult=1.0`) and dispersion-r2 primitives (F19 risk-
normalised sizing for four playstyles, F20 Isagi full-ATR + Rin
de-saturation, Nagi provenance-borrow) live. `g7retry1_precheck`
(commit `2bf5194` pre-check on the banked §11.13 caches) met every
pre-registered dispersion prediction before the re-gate ran; the re-gate
numbers below inherit those improvements and add Nagi's fresh borrowed
provenance (which the banked-cache pre-check could not exercise).

**Verdict-bearing result (phi41): FAIL — 3/7 agents pass.**

| Agent | Playstyle | Bit vector | C1 | C2 | C3 v1 | C4 | C5 | C6 | v1 pass? |
|---|---|---|---|---|---|---|---|---|---|
| `isagi_yoichi` | conservative_metavision | `111111` | 0.359 ✅ | -0.034 ✅ | 7/7 ✅ | 6571 ✅ | 0.204 ✅ | 0.178 ✅ | **YES** |
| `bachira_meguru` | rebel_tight | `110111` | 0.386 ✅ | 0.206 ✅ | 0/7 ❌ | 14551 ✅ | 0.475 ✅ | 0.153 ✅ | no |
| `itoshi_rin` | analytical_precision | `111111` | 0.375 ✅ | 0.178 ✅ | 7/7 ✅ | 2988 ✅ | 0.112 ✅ | 0.221 ✅ | **YES** |
| `chigiri_hyoma` | speed_momentum | `001111` | 0.267 ❌ | 0.000 ❌ | 7/7 ✅ | 992 ✅ | 0.105 ✅ | 0.176 ✅ | no |
| `reo_mikage` | copier_hrp | `W11WWW` | W | 0.002 ✅ | 6/7 ✅ | W | W | W | **YES** (waiver) |
| `nagi_seishiro` | confluence_only | `101111` | 0.436 ✅ | 0.000 ❌ | 7/7 ✅ | 658 ✅ | 0.245 ✅ | 0.128 ✅ | no |
| `barou_shoei` | solo_king | `001111` | 0.283 ❌ | 0.000 ❌ | 7/7 ✅ | 2080 ✅ | 0.283 ✅ | 0.195 ✅ | no |

**Companion result (arm4): FAIL — 2/7 agents pass** (itoshi_rin
`111111`; reo_mikage `W11WWW` PASS; isagi_yoichi `101111`;
bachira_meguru `110111`; chigiri_hyoma `001111`; nagi_seishiro
`101111`; barou_shoei `101111`).

**C3 v1 vs C3 v2 side-by-side (advisory, per §11.14).** C3 v1 remains
verdict-bearing pending user ratification. On the g7retry1 caches:

| Agent | phi41 v1 clean | v1 pass | phi41 v2 clean | v2 pass | phi41 dup share | arm4 v1 clean | v1 pass | arm4 v2 clean | v2 pass | arm4 dup share |
|---|---|---|---|---|---|---|---|---|---|---|
| `isagi_yoichi` | 7/7 | ✅ | 7/7 | ✅ | 34.6% | 7/7 | ✅ | 7/7 | ✅ | 36.7% |
| `bachira_meguru` | 0/7 | ❌ | 0/7 | ❌ | 0.0% | 3/7 | ❌ | 3/7 | ❌ | 40.1% |
| `itoshi_rin` | 7/7 | ✅ | 7/7 | ✅ | 0% | 7/7 | ✅ | 7/7 | ✅ | 0% |
| `chigiri_hyoma` | 7/7 | ✅ | 7/7 | ✅ | 0% | 7/7 | ✅ | 7/7 | ✅ | 0% |
| `reo_mikage` | 6/7 | ✅ | 6/7 | ✅ | 0% | 6/7 | ✅ | 6/7 | ✅ | 0% |
| `nagi_seishiro` | 7/7 | ✅ | 7/7 | ✅ | 0% | 7/7 | ✅ | 7/7 | ✅ | 0% |
| `barou_shoei` | 7/7 | ✅ | 7/7 | ✅ | 0% | 7/7 | ✅ | 7/7 | ✅ | 0% |

**C3 v2 finding is material.** In §11.13 the Bachira→Barou worst-peer
duplicate share was 89 % (phi41) / 94 % (arm4) — a genuine duplication
artifact. Phase Y v1.3 differentiated Barou to the point that in
g7retry1 the worst-peer duplicate share for Bachira is **0.0 %
(phi41) / 40.1 % (arm4)**; and yet **Bachira still fails C3 v2** in
both arms (0/7 phi41, 3/7 arm4). This falsifies the §11.13 discussion
item 1 hypothesis that Bachira's C3 fail was a duplication artifact:
after de-duplicating Barou's trade stream, Bachira still cannibalises
Barou's distinct trades. C3 v2 no longer changes Bachira's squad
outcome; the amendment remains ADVISORY pending user ratification, but
its expected upside has been retired by the evidence.

**Comparison to §11.13 (honest delta table under phi41; ✅→❌ or vice versa flagged).**

| Agent | §11.13 bits | §11.16 bits | Flipped | Notes |
|---|---|---|---|---|
| isagi | `111100` | `111111` | C5 ❌→✅, C6 ❌→✅ | Dispersion-r2 (F19 risk-normalised + F20 full-ATR) landed as predicted; now v1 PASS. |
| bachira | `110101` | `110111` | C5 ❌→✅ | Dispersion-r2 F19 fixed C5 (0.089→0.475). C3 still fails; falsifies the duplication story (see above). |
| rin | `111110` | `111111` | C6 ❌→✅ | F20 de-saturation delivered C6 exactly as pre-registered. |
| chigiri | `001111` | `001111` | — | No flip. Pre-reg explicitly said dispersion-r2 made no C1/C2 prediction here; Phase Y did not touch Chigiri. Consistent with §11.13 discussion item 3 (Role Registry axes, not C2). |
| reo | `W11WWW` | `W11WWW` | — | Waivers held; C2 pass via Rin unchanged. |
| nagi | `101100` | `101111` | C5 ❌→✅, C6 ❌→✅ | Nagi's freshly-stamped borrowed provenance did what the banked pre-check could not: C5 0.000→0.245 AND C6 0.000→0.128 (both were exactly 0 in §11.13). C2 still fails (peer-lift CI gate remains hard at low volume). |
| barou | `001101` | `001111` | C5 ❌→✅ | Dispersion-r2 fixed C5 (0.068→0.283). C1 still fails — panel mean 0.283 < 0.30 at n=43. **C1 REGRESSED at the volume level** relative to §11.13's n=62 phi41: Phase Y's USDCAD-only weapon reduced Barou's phi41 trades further. Arm 4 companion holds him at n=86 with a passing C1 (0.380, CI [0.299, 0.462]) — Phase Y's mean is up under arm4, volume is down. |

**Arm 4 companion delta table.** §11.13 arm4 = 1/7 (rin only), §11.16
arm4 = 2/7 (rin + reo). isagi arm4 flipped C5/C6 to ✅ as predicted but
C2 (already ❌ in §11.13) stayed ❌, and Bachira arm4 flipped C3 from
❌ (3/7) to still ❌ (3/7 unchanged) — Phase Y de-duplicated the trade
stream (dup 94%→40%) but did not push Bachira above the 4-of-7 threshold
under arm4 either. Barou arm4 gave up C5 fix but lost C1 (was passing at
n=322 first-attempt arm4; now n=86 still passes, but the volume delta
is real).

**Where the squad still falls short.**

1. **Bachira C3 is agent-level, not duplication-level.** With the
   duplication story disproved on the second attempt, the remaining
   Bachira C3 fail is a genuine trade-stream cannibalisation of
   Barou's *distinct* trades. Neither dispersion nor Phase Y touches
   this. A new pre-registration (Phase Z? or a Bachira-side weapon
   differentiation analogue to Phase Y) would be required to attack it.
2. **C2 bootstrap-CI gate remains hard for low-volume agents.**
   Chigiri, Nagi, Barou fail C2 in both arms in §11.16 exactly as they
   did in §11.13. Their peer-lift deltas are directionally present but
   never clear the bootstrap CI gate at n = 43–300. This is a
   sample-size problem more than a chemistry problem, consistent with
   the Role Registry finding that their retention axes are C7/C8/C9.
3. **Barou C1 under phi41 is volume-limited by Phase Y (USDCAD only).**
   Panel mean 0.283 fails at n = 43. Under arm4 he passes C1 at n = 86;
   the aggregator tension noted in §11.13 has widened, not narrowed.
4. **Chigiri C1/C2** unchanged from §11.13 — Phase Y and dispersion-r2
   made no pre-registered prediction here and none was found.

**Per doctrine §3.11.5:** FAIL (< 5 agents PASS all six criteria in
the verdict-bearing arm). No v2 arc authorised. The squad graduation
decision toward live paper mode remains with the user; the
pre-condition is NOT met on the second attempt either.

**Artifacts.**

- `reviews/g7_v1_checkpoint_final_g7retry1-phi41.{md,json}` (verdict-bearing)
- `reviews/g7_v1_checkpoint_final_g7retry1-arm4.{md,json}` (companion)
- `reviews/c3_v2_side_by_side_g7retry1-{phi41,arm4}.{md,json}` (advisory C3 v2)
- `reviews/g7_v1_checkpoint_verdict_g7retry1-{phi41,arm4}.{md,json}` (partial C2/C3 diagnostic from LOO aggregator; kept for lineage)
- `reviews/g7_v1_checkpoint_report_g7retry1-{phi41,arm4}.json` (LOO aggregator raw report)
- `reviews/g7retry1_precheck/` (dispersion-r2 pre-check on banked §11.13 caches — binding stop rule §5.1, all predictions met)
- `reviews/g7_leave_one_out_g7retry1-{phi41,arm4}/lo1_*` (7 × 2 leave-one-out replay caches; 3379–6936 trades per LOO)
- `reviews/g7_replay_cache_g7retry1-{phi41,arm4}/` (fresh walk-forward baselines)

**Standing user decisions.**

1. **C3 v2 ratification (§11.14).** Still parked; the second-attempt
   evidence shows C3 v2 is no longer the lever that would flip Bachira
   (dup share collapsed under Phase Y but Bachira still fails v2 in
   both arms). Ratifying v2 as verdict-bearing would not change the
   §11.16 squad count. Recommended posture: leave v2 as an advisory
   companion in the protocol, do not promote to verdict-bearing.
2. **Third gate attempt: authorise / decline.** Two candidate directions
   surfaced by §11.16 evidence, neither should be started without a
   fresh pre-registration:
   - Bachira C3 cannibalisation of Barou's *distinct* trades — requires
     an agent-level Bachira analogue of Phase Y (weapon differentiation
     between Bachira and Barou beyond conviction mechanics; see §11.9
     postmortem lineage).
   - Chigiri / Nagi / Barou C2 under low volume — either widen their
     panels (e.g. multi-pair Barou reversal of the Phase Y USDCAD-only
     scope, with a real pre-registered acceptance test) or accept the
     Role Registry framing and re-scope G7 v1 checkpoint C2 for
     structurally-low-volume playstyles (needs a §11.N amendment with
     doctrine sign-off).
3. **Kept levers.** Phase Y Barou v1.3, dispersion-r2 F19/F20 primitives,
   and Nagi provenance borrow are already committed as first-class code
   (commits `6457e86`, `2bf5194`). Their code stays; the squad-level
   verdict on them under G7 v1 is captured by §11.16 above. Individual
   lever protocols (`phase_y_barou_weapon/`, `dispersion_primitives_r2/`,
   `c3_v2_distinctness/`) reference this section for the joint result.

---

### §11.17 (2026-07-14) — Third gate attempt pre-registration (four-lever campaign, tag `g7retry2`)

The user authorized a third gate attempt with explicit per-agent canon
guidance, targeting the four §11.16 blockers. Four levers, each with
its own pre-registered protocol committed BEFORE implementation results
exist:

1. **Lever A — Phase Z Bachira v1.4 weave weapon**
   (`experiments/phase_z_bachira_weave/PROTOCOL.md`): Bachira fires
   baseline-zone touches only when the D1 bias (Isagi's locked
   `htf_bias_at` params, verbatim) is NEUTRAL — the set-complement of
   Barou's with-gate and Isagi's against-gate. Canon: pure dribbling —
   weave through congestion where there is no open lane. Targets
   Bachira C3 (0/7, worst peer Barou in all 7 windows). Changes
   Bachira's trade stream.
2. **Lever B — Phase AB Barou multi-pair scope reversal**
   (`experiments/phase_ab_barou_multipair/PROTOCOL.md`): the locked
   Phase Y v1.3 weapon deploys on all three panel pairs (whitelist
   USDCAD → USDCAD/EURUSD/GBPUSD; devour + lone-conviction lifts stay
   USDCAD-only per doctrine §3.11.3 A7 mechanic B). Targets Barou C1
   volume starvation under phi41 (n=43). The canon "steal" mechanic is
   designed-but-untested in that protocol — NOT shipped. Changes
   Barou's trade stream.
3. **Lever C — Phase AA Chigiri v1.4 panther-ignition weapon**
   (`experiments/phase_aa_chigiri_ignition/PROTOCOL.md`): the 0.5-ATR
   breakout-magnitude confirmation tax is replaced by an ignition-bar
   thrust gate (TR ≥ 1.5 × mean of prior 5 TRs) — earliest entry on
   fresh momentum, per the '44 panther' canon. Targets Chigiri C1
   (0.267) and C2 (no qualifying peer). Changes Chigiri's trade stream.
4. **Lever D — C2 finisher clause**
   (`experiments/c2_finisher_clause/PROTOCOL.md`): gate-DEFINITION
   amendment — a confluence-gated agent with ≥ 2 statistically-
   qualified INCOMING lifts satisfies C2 via the finisher clause.
   Implemented behind `--c2-finisher-clause` in
   `run_g7_final_verdict.py`, evaluated **ADVISORY pending user
   ratification** (same pattern as C3 v2 §11.14). Changes NO trade
   stream and no verdict-bearing output.

**Multiplicity accounting (honest).** This is the THIRD firing of this
gate (§11.13 first, §11.16 second). What changed between attempts:
attempt 2 fixed the dispersion criteria (C5/C6, five agents) and
de-duplicated Barou from Bachira; attempt 3 attacks the four blockers
attempt 2 left standing, each with a doctrine-derived mechanism and no
touched threshold. No §3 criterion, threshold, panel, or statistic
changes in the verdict-bearing run — the multiplicity risk here is
mechanism-shopping, not threshold-shopping, and the mitigation is that
every lever's mechanism is derived from canon + banked evidence with
frozen parameters (each lever protocol names its parameter sources and
its priors AGAINST). The clause (Lever D) is the only definition
change and stays advisory. §11.16's improvements landed exactly where
attempt 2's levers pointed and nowhere else — evidence the process
measures mechanisms, not noise.

**Pre-registered predictions (phi41 verdict-bearing):**

- Bachira C3 ❌→✅ (Lever A primary); Bachira C1/C2/C4/C5/C6 retained
  (Z3 guardrails, activity floor 150).
- Barou C1 ❌→✅ at n ≥ 100 (Lever B primary); C3/C5/C6 retained.
- Chigiri C1 ❌→✅ and C2 ❌→✅ (Lever C primary); C3–C6 retained.
- Nagi C2: verdict-bearing stays ❌ (no lever changes his outgoing
  lift); advisory finisher clause expected `W` (≥ 2 incoming lifts).
- Isagi, Rin, Reo: unchanged passes (no lever points at them; Phase Z
  reduces Bachira volume, which §11.16 evidence says feeds Nagi and
  marginally feeds no one else — Nagi C1 is the named interaction
  risk, Z5).
- Squad: if all three trade-stream levers land → 6/7 phi41 = PARTIAL
  PASS (≥ 5); 7/7 PASS only if the user ratifies the finisher clause.
  If any lever fails its own protocol, it STOPS (no iteration against
  the same OOS).

**Re-gate plan (single OOS touch):** fresh walk-forward baseline + 7
leave-one-out replays per arm (phi41 verdict-bearing per §4 pin; arm4
companion), 7-agent §11.12 roster, with Phase Z + Phase AA + Phase AB
code active (dispersion-r2 + Phase Y v1.3 retained from attempt 2).
`run_g7_final_verdict.py` produces the per-agent C1–C6 table and squad
verdict recorded as **§11.18**, with `--c2-finisher-clause` advisory
blocks and the §11.14 C3 v2 side-by-side (still advisory). Same
bootstrap spec (n=10,000, seed 42, percentile, α=0.05). Implementation
+ tests committed before replays run; caches follow the existing
naming with tag `g7retry2`.

### §11.18 (2026-07-15) — Third gate attempt FINAL verdict: **FAIL (3/7 phi41; 4/7 arm4)**

**Status:** the third gate attempt pre-registered in §11.17 has fired.
Single OOS touch: fresh `g7retry2` walk-forward baseline + 7
leave-one-out replays per arm, evaluated by `run_g7_final_verdict.py`
(same bootstrap spec), with the C3 v2 side-by-side and the C2 finisher
clause both advisory. Artifacts:
`reviews/g7_v1_checkpoint_final_g7retry2-{phi41,arm4}.{md,json}`,
`reviews/c3_v2_side_by_side_g7retry2-{phi41,arm4}.{md,json}`,
`reviews/g7retry2_lever_audits.json`,
`reviews/phase_{z,aa,ab}_verdict.md`.

**Per-agent bit vectors (verdict-bearing phi41 / companion arm4):**

| Agent | §11.16 phi41 | §11.18 phi41 | §11.18 arm4 | Moved |
|---|---|---|---|---|
| isagi_yoichi | `111111` PASS | `111111` PASS | `111111` PASS | — |
| bachira_meguru | `110111` | **`111111` PASS** | `111111` PASS | C3 0/7→7/7 (Phase Z) |
| itoshi_rin | `111111` PASS | `111111` PASS | `111111` PASS | — |
| chigiri_hyoma | `001111` | `001111` | `001111` | C1 0.267→0.239 (Phase AA FAIL) |
| reo_mikage | `W11WWW` PASS | `W01WWW` | `W11WWW` PASS | C2 lost under phi41 (0.002→none) |
| nagi_seishiro | `101111` | `001111` | `001111` | **C1 0.436→0.197 LOST** (Z5 fired) |
| barou_shoei | `001111` | `101111` | `101111` | C1 0.283 (n=43)→0.406 (n=444) (Phase AB PASS) |

Squad: **FAIL 3/7 phi41** (isagi, bachira, rin) / **4/7 arm4** (+ reo).
Same phi41 count as §11.16 but different composition — one blocker
fixed (Bachira C3), one fixed (Barou C1), one unchanged-failed
(Chigiri), one **new** break (Nagi C1) caused by the fix to the first.
Advisory squad-with-finisher-clause: unchanged (3/7 and 4/7) — the
clause flips Nagi's C2 to `W` (3 qualified incoming lifts phi41:
bachira/isagi/rin; 4 under arm4) but cannot rescue his new C1 fail.

**Lever outcomes vs their own pre-registered criteria (honest):**

1. **Lever A / Phase Z (Bachira weave): FAIL on Z5.** Z1–Z4 all pass —
   C3 0/7→7/7 clean, zero Bachira×Barou same-tick fired proposals
   (Z2 audit), Bachira retains everything at n=733, squad TQS within
   tolerance (phi41 −0.011, arm4 −0.014). But the weave halved
   Bachira's volume (1468→733) and Nagi's confluence fuel collapsed
   with it (67→21 trades), breaking Nagi C1 — the exact interaction
   risk Z5 pre-registered as a phase failure. `reviews/phase_z_verdict.md`.
2. **Lever B / Phase AB (Barou multi-pair): PASS** — all of AB1–AB5.
   n 43→444, C1 0.406 with CI low 0.365, C3 7/7 kept, no peer C3
   poisoning, EURUSD slice 0.363 over 120 trades (audit vs E001 prior
   disclosed). `reviews/phase_ab_verdict.md`.
3. **Lever C / Phase AA (Chigiri ignition): FAIL on AA1+AA2+AA-M.**
   Volume rose (296→503) but mean TQS fell 0.267→0.239 and the
   entry-efficiency component — the component the mechanism predicted
   would rise — fell 0.290→0.278. No C2 peer emerged. The doctrine
   §3.11.3 A4 prior (Chigiri needs stricter, not looser, filtering)
   stands. `reviews/phase_aa_verdict.md`.
4. **Lever D / C2 finisher clause: behaved exactly as pre-registered**
   (advisory `W` for Nagi with 3–4 qualified incoming lifts; verdict-
   bearing outputs byte-identical with the flag on/off, enforced by
   unit test). Ratification remains with the user; note it is
   currently moot for the squad count until Nagi C1 is restored.

**C3 v2 side-by-side (§11.14, advisory):** v1 and v2 agree on every
agent in both arms (all 7/7 clean except reo 6/7 phi41), duplicate
share 0% everywhere. Post-Phase-Z there is no distinctness question
left for v2 to adjudicate — the ratification decision is now
essentially cosmetic.

**Standing decisions surfaced by §11.18 (user calls, not started):**

1. **Bachira weave default (`weapon_weave`):** keep (C3 fixed, Bachira
   full pass) and pursue a Nagi-fuel repair lever, or revert (restores
   Nagi C1, reopens C3). The obvious candidate direction — gate
   Bachira's *proposals* but keep his *thought stream* at v1 volume so
   Nagi's confluence fuel survives — requires a fresh pre-registered
   phase; Nagi reads fired thoughts, so this is a harness-semantics
   question to settle in design.
2. **Chigiri ignition default (`weapon_ignition`):** recommended
   revert to v1 magnitude hurdle (Phase AA clean FAIL).
3. **Barou multi-pair whitelist:** recommended adopt as standing v1.3
   configuration (Phase AB clean PASS).
4. **C2 finisher clause + C3 v2 ratification:** both advisory, both
   pending.
5. Reo's phi41 C2 flip (pass→fail) is low-n volatility of the
   CI-gated statistic (his §11.16 pass was +0.002 marginal), not a
   lever effect; no action proposed.

---

## 12. Verdict registry row (to be added)

The G7 gate row for `docs/methodology/gate_verdict_registry.md`:

| Gate | Locked statistic | Pass criterion | Panel | Registered date |
|---|---|---|---|---|
| **G7** — v1 checkpoint gate | Per-agent 6-bit vector conjunction across all 8 implemented agents | All 8 agents PASS on all 6 §3.11.5 criteria | Φ4.1 panel (EURUSD/GBPUSD/USDCAD H4 2015-2025, 7 OOS windows) with F19/F20/F21 wired | 2026-07-01 (pre-registered, awaiting sign-off) |

This row lands in `docs/methodology/gate_verdict_registry.md` when the user signs off on this PROTOCOL. Until then, G7 is `pre-registered` here but not `active` in the registry.
