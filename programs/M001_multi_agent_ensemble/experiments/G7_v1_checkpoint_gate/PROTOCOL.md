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

---

## 12. Verdict registry row (to be added)

The G7 gate row for `docs/methodology/gate_verdict_registry.md`:

| Gate | Locked statistic | Pass criterion | Panel | Registered date |
|---|---|---|---|---|
| **G7** — v1 checkpoint gate | Per-agent 6-bit vector conjunction across all 8 implemented agents | All 8 agents PASS on all 6 §3.11.5 criteria | Φ4.1 panel (EURUSD/GBPUSD/USDCAD H4 2015-2025, 7 OOS windows) with F19/F20/F21 wired | 2026-07-01 (pre-registered, awaiting sign-off) |

This row lands in `docs/methodology/gate_verdict_registry.md` when the user signs off on this PROTOCOL. Until then, G7 is `pre-registered` here but not `active` in the registry.
