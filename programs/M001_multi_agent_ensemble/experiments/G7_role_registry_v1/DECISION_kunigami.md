# Kunigami retention decision (post-V, Role Registry v1)

**Status:** DECISION-PENDING-USER-SIGN-OFF
**Date:** 2026-07-03 07:40 UTC
**Governing protocol:** `PROTOCOL.md` §5 (Retention rule).
**Verdict source:** `../../reviews/g7_role_registry_verdict_post-V.md`.

---

## 1. Post-V Role Registry v1 findings for `kunigami_rensuke`

| Criterion | Result | Numeric evidence |
|---|:---:|---|
| **G7 v1 C1** (per-agent TQS) | Waived (§11.1 defensive-observer) | 0 baseline trades |
| **G7 v1 C2** (outgoing chemistry) | ❌ FAIL | best_lift on `None` at 0.000 epsilon-units. No peer TQS or trade-count moves when Kunigami is EXCLUDED. |
| **G7 v1 C3** (non-cannibalising) | ✅ PASS | 0.0% worst-peer reduction (trivial pass — he takes no slots). |
| **G7 v1 C4** (workspace read + publish) | Waived read-side; publishes 53164 (§11.1) | The waiver was ratified when Kunigami's role was still hypothesised. |
| **G7 v1 C5** (F19 lot cognition) | Waived (§11.1) | intend() → None by design. |
| **G7 v1 C6** (F20 risk cognition) | Waived (§11.1) | intend() → None by design. |
| **Role Registry C7** (incoming chemistry) | Waived | 0 baseline trades — no TQS to be lifted. |
| **Role Registry C8** (workspace-signal impact, v1 proxy) | ❌ FAIL | workspace_impact = **0.0** epsilon-units. Every single peer's mean TQS and trade count is unchanged when Kunigami is removed. |
| **Role Registry C9** (volume floor) | Waived | Structural falsifier. |
| **Retention rule** (C3 ∧ any of {C2,C7,C8,C9}) | ❌ NOT RETAINED | C3 passes trivially, but ZERO role axes pass (all four of C2/C7/C8/C9 either fail or are waived). Waived is not a pass. |
| **Role label** | `retirement_candidate` | The only agent in the post-V squad to receive this label. |

---

## 2. Why the §11.1 waiver falls short

The Kunigami defensive-observer waiver (G7 v1 §11.1) was pre-registered on the hypothesis that Kunigami earns his slot through workspace publishes — Thoughts describing anti-tilt / warning states peers would consume in their intent decisions. The Role Registry v1 C8 proxy directly tests that hypothesis in the ONLY way the current on-disk data allows: does Kunigami's workspace activity actually MOVE any peer decision?

Empirically: **no**. Not by TQS, not by trade count, not on any of the 7 peers, not on any measurement axis in the post-V walk-forward. Kunigami publishes 53164 thoughts (one per bar on every symbol) and every single one of them is workspace noise from the perspective of peer decisions. He is architecturally a dead-weight publisher.

Compare against the OTHER §11.1-waived agent (Reo Mikage):

| Agent | C8 workspace_impact | Interpretation |
|---|---:|---|
| `reo_mikage` | **245.4 epsilon-units** | Signals ARE consumed. Removing Reo drops Nagi's trade count −135 and lifts Nagi's TQS quality +0.0719 -- Reo is a functioning gatekeeper. §11.1 waiver holds. |
| `kunigami_rensuke` | **0.0 epsilon-units** | Signals are NOT consumed. §11.1 waiver is a rubber stamp. |

The Role Registry v1 C8 was designed precisely to disambiguate these two cases without a new walk-forward run. It succeeded. Kunigami's waiver is empirically groundless.

---

## 3. The three viable options

### Option A -- RETIRE (recommended)

Remove Kunigami from the `G7_AGENT_ORDER` roster and drop `A10KunigamiV1` from the eight-agent instantiation in `run_g7_leave_one_out.py` and `run_g7_v1_checkpoint_gate.py`.

- **Pros:** honest verdict on the C8 evidence. Reduces roster to 7 agents (isagi, bachira, rin, chigiri, reo, nagi, barou), all of whom pass Role Registry v1 retention (albeit some with C3 caveats). Removes 53164 publish operations per walk-forward -- cheap runtime win. No canonical Blue Lock rule violated (Kunigami is not on the field in the anime's main squad plotline either -- he is a "second-string finisher").
- **Cons:** breaks the "8-agent squad" symmetry of the G7 v1 panel. Requires a G7 v1 §11 amendment to record the retirement.
- **Amendment path:** G7 v1 PROTOCOL.md §11.10 "Kunigami retirement" + Role Registry v1 PROTOCOL.md §12.1 "First retirement candidate confirmed by C8 v1 proxy".

### Option B -- RE-EVOLVE Kunigami on a new mechanic

Ship a Kunigami v1.1 that actually contributes to peer decisions in a measurable way. Candidate mechanics:
- **B1 (anti-tilt broadcaster):** Kunigami's warning Thoughts get amplified during high-loss-streak windows so peers' reads on `KUNIGAMI_WARNING` actually feed a cool-off conviction penalty. Peers would need to be instrumented to react to KUNIGAMI_WARNING in `intend()`.
- **B2 (defensive proposal):** Kunigami starts proposing conservative single-position trades (small size, wide SL) in extreme regimes only. Loses the "defensive observer" invariant but earns a real trade slot.
- **B3 (drawdown gate):** Kunigami is promoted from workspace publisher to an aggregator-side gate that vetoes new positions when squad drawdown exceeds a threshold. Aggregator-level, not agent-level.

Each of B1/B2/B3 is a Phase X-kunigami-style mechanic and requires its own pre-registration.

- **Pros:** preserves the 8-agent panel. Turns a null result into a design lesson.
- **Cons:** ~1–2 weeks of code + walk-forward + verdict for each candidate mechanic. Meanwhile Kunigami continues to burn 53164 publishes per replay.

### Option C -- WAIT for C8 v2 (true citation counts)

Extend `run_phi4_squad_gate.py` to persist per-tick `IntentDecision` records to `intents.jsonl`, re-run the walk-forward-post-V, then recompute C8 with true `interpreted_signal_family` citation counts. If Kunigami has ≥ 100 real citations, keep him; if he still has ≤ 5, retire him.

- **Pros:** ratifies the v1-proxy verdict on the pure statistic. Fully rigorous.
- **Cons:** ~40 min compute + a driver code change. The v1 proxy already scores Kunigami at 0.0 (not "small" -- exactly zero), which is a strong prior that C8 v2 will also score him at zero.

---

## 4. Recommendation

**Option A -- RETIRE.**

The empirical case is unambiguous: workspace_impact of exactly 0.0 across every peer, every metric, every direction, in the full 53164-bar walk-forward. No borderline zone. No "we might be missing signal" caveat. The 0.0 result is the SAME shape a random-noise publisher would produce.

Option C is defensible if the user wants to see the pure citation count before retiring, but the probability of a v2 verdict differing from the v1 verdict on this specific agent is extremely low. Option B is defensible if the user finds Kunigami's canon role worth preserving despite the null evidence; each B-variant is at least 1 week of pre-reg + code + compute.

---

## 5. Amendments if Option A is chosen

1. **`experiments/G7_v1_checkpoint_gate/PROTOCOL.md`** — add `§11.10 (2026-07-03) — Kunigami retirement, Role Registry v1 C8 fail`. Document:
   - Trigger: C8 workspace_impact = 0.0.
   - Effect on G7 v1: the 6-bit vector conjunction is no longer computed for Kunigami; he is removed from `STRUCTURAL_FALSIFIERS`.
   - Roster becomes 7 agents.
2. **`experiments/G7_role_registry_v1/PROTOCOL.md`** — add `§12.1 (2026-07-03) — First retirement confirmed by v1 proxy`.
3. **`sim/scoring/run_g7_leave_one_out.py`** — drop kunigami from `G7_AGENT_ORDER`.
4. **`sim/scoring/run_g7_v1_checkpoint_gate.py`** — drop `A10KunigamiV1` from `_instantiate_all_agents()` and any panels.
5. **`sim/agents/a10_kunigami.py`** — retain the code (audit trail) but mark the module docstring as RETIRED and remove imports from active runners.
6. **`ai_context.md`** — log the retirement under a new section, note the new 7-agent roster.
7. **Regenerate** `walk-forward-post-V-post-kunigami-retirement` to lock in the new roster's numbers. This becomes the baseline for Phase 5 Φ5 re-sim.

---

## 6. Amendments if Option B is chosen

Draft `experiments/phase_x_kunigami_v1_1/PROTOCOL.md` for the chosen B-variant. Follow the same statistical-honesty rules as Phase V (pre-register hypothesis, lock success threshold BEFORE running compute, document null-result path).

---

## 7. Amendments if Option C is chosen

1. **Extend `run_phi4_squad_gate.py`** to persist `IntentDecision` records to `<cache_dir>/intents.jsonl`, mirroring the existing `trades.jsonl` write.
2. **Add** `_extract_citation_counts` helper in `run_g7_leave_one_out.py` that reads `intents.jsonl` and computes per-source citations from `interpreted_signal_family`.
3. **Re-run** the walk-forward-post-V baseline + a single lo1 (Kunigami excluded) to get the citation counts. ~1h compute.
4. **Regenerate** the Role Registry verdict with C8 v2 numbers.

---

## 8. User sign-off

**Awaiting user decision on A / B / C above.**

If Option A: I will execute the §5 amendments in one atomic commit + regenerate the post-kunigami-retirement walk-forward.
If Option B: I will draft the Phase X-kunigami pre-registration for the user-chosen variant.
If Option C: I will implement the intents.jsonl persistence + re-run compute.
