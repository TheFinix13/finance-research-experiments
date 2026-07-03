# Phase V-iterate — pre-registered protocol (TEMPLATE / DRAFT)

**Status:** `template-pending-c2c3` — 2026-07-03
**Author:** orchestrator (drafted during the Phase 3 C2/C3 compute-window fill; PID 27370 running at time of draft)
**Gate context:** Follows the null-result Phase V-a + V-b reversion documented in `experiments/G7_v1_checkpoint_gate/PROTOCOL.md` §11.9-postmortem. This experiment does NOT reopen the G7 gate; it registers a fresh V-iterate treatment whose verdict may or may not amend the G7 verdict registry rows for the affected agents.

> **Why this exists as a template first.** The postmortem's recommended sequencing is *"Option D (concede) first -- measure C2/C3 before designing another mechanic"*. C2/C3 is still running at draft time. Rather than cold-start a fresh protocol once the numbers land, this template locks the design frame, the pre-registration structure, and the four candidate mechanics NOW; the C2/C3-driven decision fields are explicit TBD cells. When the compute lands, this document is promoted from `template-pending-c2c3` to `pre-registered` by filling in the TBD cells and picking exactly ONE mechanic. No mid-flight retuning.

---

## 1. Hypothesis (candidate arms — one gets pre-registered)

**H0 (universal):** No Phase V-iterate mechanic improves squad TQS ratio over the post-V baseline (5604 executed trades, 28842 shadow trades, no per-agent regression on Isagi/Bachira/Rin) by Δ ≥ **0.010 median-of-OOS-window mean-TQS** at bootstrap CI lower bound > 0.

**H1 (one of the four arms, exact one chosen at pre-registration time):**

| Arm | Mechanic | Selection precondition (C2/C3-gated) |
|-----|----------|--------------------------------------|
| A | Per-tick conviction LIFT on specialist ticks (+0.10 additive, not tier-promotion) | C2 for Chigiri OR Barou = PASS at ≥ +0.020 delta *(⇒ they are contributing alpha but losing tiebreaks)* |
| B | Symbol-conditional slot reservation (dedicated slot when specialist bit fires) | C2 = PASS AND C3 has ≥ 2 peers with reduction ratio ≥ 0.40 *(⇒ they crowd out other agents when routed conventionally)* |
| C | Phase T-evolve-style peer-YIELD (Chigiri/Barou yield when Isagi's metavision is same-direction; lone-read lift otherwise) | C2 = PASS AND C3 = PASS with 0-1 peers ≥ 0.20 reduction *(⇒ they contribute alpha AND don't cannibalise -- the Rin analogue)* |
| D | Concede (accept post-V as final; no mechanic change) | C2 = FAIL *(⇒ removing them doesn't hurt squad TQS -- crowding is a feature)* |

**Rejection criterion (whichever arm is chosen):**

- PASS = H1 satisfied with bootstrap CI lower bound > 0 at α = 0.05 (single-arm test; no multiple-comparison correction because this experiment is a single-treatment amendment, not a sweep).
- FAIL = point estimate < +0.010 OR CI lower bound ≤ 0.
- REVERT = FAIL on the target agent's alpha metric AND any collateral regression on Isagi/Bachira/Rin ≥ 0.005 (matches §11.9-postmortem's revert threshold).

---

## 2. Empirical motivation (numbers locked)

| Source | Number | What it shows |
|---|---|---|
| Phase V-a null verdict | Chigiri Δ_post-V = +0.05085 vs target ≤ +0.020 | tier-promotion insufficient — raw conviction gap dominates |
| Phase V-b null verdict | Barou Δ_post-V = +0.01488, 0 flips | tier-promotion is a no-op when Barou fires against Isagi's active position |
| Isagi metavision boost | 0.85 → 0.90-1.00 on D1 alignment | Isagi's boosted raw conviction is 0.08-0.12 above Chigiri's boosted-breakout (0.85-0.95) |
| Rin Phase T-evolve | +0.032 delta with peer-yield mechanic ([verdict on disk](../../reviews/g7_v1_checkpoint_report_walk-forward-post-TU.json)) | peer-yield is the ONE Phase-T mechanic that produced non-null alpha for a canon "reader" agent |
| Post-V shadow ledger | 28842 records, dense per-agent per-tick counterfactuals | sufficient sample size for shadow-driven cov matrix (Phase 5 HRP input builder, `bafd01b`) |

**C2/C3 numbers (to be filled in when Phase 3 compute lands, ETA ~08:00 UTC 2026-07-03):**

| Agent | C2 verdict | C3 verdict | C3 worst-peer reduction | Selected arm |
|-------|-----------|-----------|------------------------|--------------|
| Chigiri | **TBD** | **TBD** | **TBD** | **TBD** |
| Barou | **TBD** | **TBD** | **TBD** | **TBD** |

---

## 3. Treatment arm — full spec (fill in ONE, delete others at pre-reg time)

### Arm A — Per-tick conviction LIFT

- **Mechanic:** On specialist ticks (Chigiri: `chigiri_regime_specialist == True`; Barou: `barou_solo_king_specialist == True`), add `PHASE_V_ITERATE_CONVICTION_LIFT = 0.10` to `proposal.conviction` BEFORE the aggregator tier-bias adjustment.
- **Rationale:** Neutralising the 0.05 tier bias failed because raw gaps are 0.08-0.12. A +0.10 additive lift raises Chigiri's typical 0.85 specialist to 0.95, clearing Isagi's 0.90-1.00 range on boundary cases.
- **Implementation surface:** `sim/agents/a04_chigiri.py::intend`, `sim/agents/a07_barou.py::intend`. Stamp `_phase_v_iterate_lift = 0.10` in rationale for audit.
- **Guard:** Reject if adjusted conviction > 1.0 (clip to 1.0 with rationale `_phase_v_iterate_lift_clipped = True`).
- **Rollout:** All symbols, both agents. Not symbol-conditional.
- **Risk:** Over-firing when Isagi is ALSO correct on the same tick. Mitigated by only lifting on the specialist bit's double-hurdle (mag/atr ≥ 1.5 AND atr/median_atr ≥ 1.5).

### Arm B — Symbol-conditional slot reservation

- **Mechanic:** When specialist bit fires AND at least one other proposal on the same symbol is same-direction, admit the specialist to a dedicated slot beyond R6's normal position count. Sentinel R6 total-risk cap still applies to the promoted slot; only the R6 concurrent-position cap is relaxed.
- **Rationale:** Chigiri/Barou lose tiebreaks against Isagi's high raw conviction. A per-proposal flag can't win a tiebreak; a slot reservation bypasses the tiebreak entirely.
- **Implementation surface:** `sim/scoring/run_phi4_squad_gate.py` aggregator — add `RESERVED_SPECIALIST_SLOT` handling in the admit loop. Sentinel R6 unchanged.
- **Guard:** Only ONE reserved slot per symbol per tick. If both Chigiri AND Barou fire specialist on the same symbol-tick, keep the higher-conviction one (Barou fires against Isagi's active direction so this collision is rare in practice).
- **Risk:** Increased position count → more capital used per symbol → tighter cross-symbol risk budget under Sentinel R7. Must verify walk-forward: R7 rejects don't spike.

### Arm C — Peer-YIELD (Rin analogue)

- **Mechanic:** In `intend()`, before returning `IntentDecision.propose`, both Chigiri and Barou inspect the workspace snapshot for Isagi's same-tick thought:
  - If Isagi has stamped `metavision_alignment` and its direction matches the agent's own proposal direction → return `IntentDecision.yield_(YieldReason.PEER_METAVISION_ALIGNED)` instead of proposing.
  - If Isagi is silent OR disagrees → propose normally with a "lone-read lift" (`_phase_v_iterate_lone_read_lift = 0.10`) added to conviction.
- **Rationale:** This is Rin's proven Phase T-evolve mechanic verbatim (see `sim/agents/a03_rin.py::intend` post-T-evolve). Rin's post-T-evolve verdict showed +0.032 alpha delta — the only positive-alpha Phase-T mechanic for a canon "reader" agent.
- **Implementation surface:** `sim/agents/a04_chigiri.py::intend`, `sim/agents/a07_barou.py::intend`. Uses the F22 same-tick workspace barrier (`snapshot_at_barrier`) which is production and tested.
- **Guard:** Yield only when Isagi's `ThoughtRead.signal_family == "metavision"`. Do NOT yield on other Isagi thoughts (zones, swings, D1) since Chigiri/Barou operate on orthogonal axes.
- **Risk:** Lower proposal count for Chigiri/Barou → fewer opportunities for their specialist alpha to show up. Mitigated by the lone-read lift on the surviving proposals.

### Arm D — Concede (no code change)

- **Mechanic:** None. Accept the post-V configuration as final for Chigiri and Barou.
- **Rationale:** If C2 = FAIL for both agents (removing them from the squad does NOT hurt squad TQS at α=0.05), their crowding-out behaviour is a canon-fidelity feature, not a bug. The +0.049 / +0.015 shadow deltas reflect complementary readers whose alpha is already priced in by the aggregator via cross-agent correlation.
- **Implementation surface:** None. Update `06-blue-lock-doctrine.md` §Roster with a "Chigiri/Barou routing accepted as canon" note. Update G7 verdict registry.
- **Guard:** N/A.
- **Risk:** None. This is the null hypothesis's default outcome.

---

## 4. Panel + statistical setup

- **Panel:** Same as G7 post-V walk-forward — 2015-01-01 through 2025-12-31, EURUSD + GBPUSD + USDCAD, 53164 global bars, 7 OOS windows per Phi4.1 layout.
- **Baseline:** `reviews/g7_v1_checkpoint_report_walk-forward-post-V.json` (already on disk, no re-run needed).
- **Treatment run tag:** `walk-forward-post-V-iterate-<arm>`.
- **Wall-clock estimate:** ~42 min single replay against the M001 panel; heartbeat monitor mandatory (see `.cursor/rules/heartbeat-monitor.mdc`, alwaysApply=true).
- **Statistical primitive:** Same as G7 — median-of-OOS-window mean-TQS + 10000-sample bootstrap CI.
- **Alpha:** α = 0.05, single-treatment arm, no multiple-comparison correction.

---

## 5. Verdict + registry writeback

On completion, emit:

1. `reviews/phase_v_iterate_<arm>_verdict.md` (audit-grade, same format as `walk-forward-post-V.md`).
2. Amended G7 verdict registry row for Chigiri (if Arm A/B/C touches Chigiri) OR Barou (if it touches Barou) OR both.
3. `06-blue-lock-doctrine.md` §Roster update ONLY on PASS + no collateral regression.

**On FAIL:** REVERT immediately (same discipline as Phase V-a null). Do NOT amend thresholds in place — that would be a §11 protocol-discipline violation. If the picked arm fails, this template stays open with the failed arm's cells filled in as historical record; a new arm requires a NEW pre-registration.

---

## 6. Amendment log

*(§11 amendment discipline — every retune goes here as a dated bullet.)*

- **§6.1 (2026-07-03):** Initial template drafted during Phase 3 compute-window fill. TBD cells: C2/C3 numbers (§2) and arm selection (§1 table). To be filled and promoted from `template-pending-c2c3` to `pre-registered` when Phase 3 compute lands.

---

## 7. References

- Null-result postmortem: [`../G7_v1_checkpoint_gate/PROTOCOL.md`](../G7_v1_checkpoint_gate/PROTOCOL.md) §11.9-postmortem
- Post-V verdict: [`../../reviews/g7_v1_checkpoint_report_walk-forward-post-V.json`](../../reviews/g7_v1_checkpoint_report_walk-forward-post-V.json)
- Rin Phase T-evolve verdict (Option C proof-of-concept): [`../../reviews/g7_v1_checkpoint_report_walk-forward-post-TU.json`](../../reviews/g7_v1_checkpoint_report_walk-forward-post-TU.json)
- Phase 3 C2/C3 runner: [`../../sim/scoring/run_g7_leave_one_out.py`](../../sim/scoring/run_g7_leave_one_out.py) (commit `589aae7`)
- F22 workspace barrier (used by Arm C): [`../../sim/core/reasoning_workspace.py`](../../sim/core/reasoning_workspace.py) `snapshot_at_barrier`
- Statistical-honesty rules: `07-research-standards.md` §11
