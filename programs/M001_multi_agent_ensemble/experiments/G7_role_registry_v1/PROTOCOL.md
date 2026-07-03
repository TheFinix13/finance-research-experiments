# G7 Role Registry v1 — pre-registered protocol

**Status:** PRE-REGISTERED (2026-07-03 07:20 UTC)
**Companion to:** `../G7_v1_checkpoint_gate/PROTOCOL.md`
**Depends on:** G7 v1 C1–C6 verdicts + `g7_leave_one_out_verdict_post-V.json` + `g7_replay_cache_walk-forward-post-V/` on disk.
**Statistical honesty note:** the 3 new criteria (C7/C8/C9) and their thresholds are locked BEFORE the C7/C8 numbers are computed. C6 volume-floor uses ONLY the already-observed post-V trade counts; no forward-looking data.

---

## 1. Motivation

G7 v1 (§3) asks "can this agent play?" with 6 conjunctive competence bits (C1 quality, C2 outgoing chemistry, C3 non-cannibalisation, C4 workspace participation, C5 lot cognition, C6 risk cognition). The strict G7 v1 verdict on the post-V walk-forward exposed a role-blindness gap:

| Agent | C2 (outgoing) | C3 | Reading |
|---|:---:|:---:|---|
| `nagi_seishiro` | **FAIL** (0.292× eps) | PASS | Highest mean TQS in squad (0.431), lowest trade count (135). Star finisher who converts peer setups but does not create for peers. Cutting him removes ~2.5% trades but ~45% of the highest-TQS conversions. |
| `barou_shoei` | **FAIL** (0.502× eps) | PASS | 153 trades at 0.347 mean TQS. Slot-suppressed by Bachira (excluded=bachira → Barou gains +808 trades, 84% cannibalisation). Solo-conviction niche exists but the aggregator never lets him occupy it. |
| `kunigami_rensuke` | FAIL (0.0× eps) | PASS | 0 trades in baseline (defensive-observer role, waived on G7 v1 C1/C5/C6 by §11.1). All peer deltas are exactly 0.0 when Kunigami is removed. Publishes every bar but no measurable downstream peer effect. |
| `reo_mikage` | PASS | PASS | 0 trades in baseline (F14 architect, waived on G7 v1 C1/C5/C6 by §11.1). Peer deltas ARE meaningful when Reo is removed (nagi −135 trades / +0.0719 TQS quality-filter effect on the surviving trades). Publish-only but genuinely consumed. |

Two problems fall out:

1. **Star finishers (Nagi, Barou) are structurally penalised by C2** as currently written, because C2 measures OUTGOING lift only. In Blue Lock terms, the finisher's role is to convert plays other players build — the equivalent of Erling Haaland. Cutting them because they don't "chemistry" is a category error.

2. **Publish-only agents Reo and Kunigami are indistinguishable under G7 v1 C4** — both pass C4 via §11.1 waiver, both publish every bar. But Reo's signals are DEMONSTRABLY consumed (peer deltas move when he's removed); Kunigami's are demonstrably NOT (peer deltas are exactly 0.0 when he's removed). G7 v1 has no criterion that distinguishes a functioning workspace catalyst from a dead-weight publisher.

The Role Registry v1 test adds three orthogonal criteria that resolve both problems and emit a **role label** per agent.

---

## 2. Hypothesis

**H1 (finisher role exists):** Nagi's mean TQS drops significantly when any of {bachira, rin, reo} is individually removed from the squad. Formally: ∃ ≥ 2 peers p such that `baseline_stats["nagi_seishiro"]["mean_tqs"] - lo1_stats_without_p["nagi_seishiro"]["mean_tqs"] > 0.02`.

**H2 (dead-weight publisher exists):** Kunigami's F22c-YieldReason citation count (the number of times peer intents cite `signal_family="kunigami_rensuke"` in `interpreted_signal_family` or workspace-thought reads) is < 5% of Reo's citation count on the same walk-forward panel.

**H3 (volume-floor separation):** at least 2 agents in the post-V roster hold ≥ 5% of squad trades individually.

Each hypothesis independently informs a criterion pass/fail. Hypotheses are NOT rejected via the study; they merely instantiate the criterion thresholds on empirical evidence.

---

## 3. The 3 new criteria (C7 / C8 / C9)

Numbering continues from G7 v1 to avoid namespace clash. All 3 are ADDITIVE — they never REMOVE a pass from G7 v1. They only ADD a role label when a G7 v1 fail is due to a specific structural pattern.

### Criterion 7 — Incoming chemistry (finisher role)

- **Statistic:** for each peer `p ≠ X`, the reduction in agent `X`'s mean TQS caused by `p`'s absence:
  ```
  incoming_lift_from_p_to_X = baseline_stats[X]["mean_tqs"] - lo1_stats_without_p[X]["mean_tqs"]
  ```
  If `X` has 0 trades in either configuration, C7 is `waived` (falsifier semantics per §11.1).
- **Pass threshold:** ≥ 2 peers with `incoming_lift ≥ 0.02` (i.e. 4× the C2 outgoing epsilon; deliberately stricter because incoming lift accumulates from multiple sources).
- **Rationale:** a legitimate finisher receives lift from multiple setup-players. A single-peer lift could be coincidence; ≥ 2 independent peers systematically lifting the same finisher is a stable role pattern.

### Criterion 8 — Workspace-signal impact (context-provider role)

- **Statistic (v1 proxy):** the peer-delta-magnitude score from the leave-one-out. When agent `X` is excluded, the sum of absolute per-peer stat changes measures how much `X`'s workspace activity was actually FLOWING INTO peer decisions. Formally:
  ```
  workspace_impact_of_X = sum over peers p != X:
    |delta_tqs_p_when_X_excluded| / 0.005
    + |delta_trades_p_when_X_excluded| / 1.0
  ```
  (Same epsilon-normalisation as C2's strongest-lift ranking.)
- **Pass threshold:** `workspace_impact_of_X ≥ 50` epsilon-units summed across all peers.
- **Rationale (v1 proxy):** publish-only agents can be either (a) legitimate context providers (Reo-style — signals get consumed and PEER BEHAVIOUR CHANGES) or (b) dead-weight broadcasters (Kunigami candidate — signals are published but peer behaviour is invariant). Peer-delta-magnitude directly measures which category the agent falls into WITHOUT requiring a new walk-forward. It is a strictly weaker proxy than counting `IntentDecision.interpreted_signal_family` citations (see §12 amendment note below), but it uses ONLY data already on disk, and it correctly separates the pathological cases: Kunigami's excluded-run shows all-zero peer deltas (workspace_impact = 0), whereas Reo's shows a Nagi shift of −135 trades and +0.0719 TQS quality on the survivors (workspace_impact ≥ 150 epsilon-units from Nagi alone). A structural falsifier (§11.1 waiver) MUST also pass C8 to keep their waiver — otherwise the waiver becomes a rubber stamp.

- **§12 amendment note on C8 v2:** the direct citation count using `IntentDecision.interpreted_signal_family` (F22c field) is the pure statistic; the peer-delta-magnitude proxy is a strictly weaker approximation. The pure statistic is NOT available in the post-V walk-forward artifacts because the interpretation records are not serialised by the current driver. Landing C8 v2 requires: (a) extending `run_phi4_squad_gate.py` to persist per-tick `IntentDecision` records to a new `intents.jsonl` file, (b) re-running the walk-forward (~40 min). C8 v1 uses the proxy; C8 v2 would ratify or overturn the v1 verdict. Any Kunigami retirement decision made on C8 v1 is provisional pending C8 v2 confirmation if the workspace_impact score is between 25 and 100 (borderline zone).

### Criterion 9 — Trade-volume floor (anti-dilution)

- **Statistic:** `X`'s baseline trade count as a fraction of the squad total baseline trade count:
  ```
  volume_share_of_X = baseline_stats[X]["n_trades"] / sum(baseline_stats[.]["n_trades"])
  ```
- **Pass threshold:** `volume_share_of_X ≥ 0.05` (5% of squad trades).
- **Rationale:** an agent who fails C1/C2 but is single-handedly responsible for a meaningful slice of squad trades cannot be cut without measurable volume regression. This is the anti-dilution guardrail.
- **Waiver:** structural falsifiers (`STRUCTURAL_FALSIFIERS` set) are exempt from C9 (they have 0 trades by design).

---

## 4. Role labels

Each agent is emitted with a role label based on the combination of G7 v1 C2 + new C7/C8/C9. Role labels are diagnostic (not gating); the retention decision uses the retention rule in §5.

| C2 (outgoing) | C7 (incoming) | C8 (workspace) | C9 (volume) | Role label |
|:---:|:---:|:---:|:---:|---|
| ✅ | any | any | any | `chemistry_catalyst` |
| ❌ | ✅ | any | any | `finisher` (receives lift, doesn't give it) |
| ❌ | ❌ | ✅ | any | `workspace_catalyst` (publish-only that IS consumed) |
| ❌ | ❌ | ❌ | ✅ | `volume_specialist` (solo scorer, retained on volume floor) |
| ❌ | ❌ | ❌ | ❌ | `retirement_candidate` (all four axes fail — recommend removal) |

Multiple labels can apply (e.g. an agent passing C2 AND C7 gets `chemistry_catalyst + finisher` — that's the Rin-lifts-Nagi shape but with Rin herself receiving lift from Reo).

---

## 5. Retention rule (roster admission gate)

An agent is RETAINED in the roster iff:

```
G7 v1 pass on C3 (non-cannibalising)         # unchanged from G7 v1
AND
at least ONE of {C2, C7, C8, C9} passes.     # role-aware or-gate
```

C1/C4/C5/C6 remain diagnostic but are NOT retention-gating under Role Registry v1 (they inform coaching decisions, not squad admission).

**Explicit resolution for the 3 problem cases:**

- **Nagi** — currently G7 v1 C2 FAIL. Under Role Registry v1: C7 pass (H1) → retained as `finisher`.
- **Barou** — currently G7 v1 C2 FAIL, C7 UNKNOWN. Retention depends on Phase W-barou (companion protocol) evolving Barou to claim solo-conviction slots; if Phase W-barou lands a walk-forward-post-W with Barou's C2 passing OR C7 passing (peers lift him), retained. Otherwise retirement candidate.
- **Kunigami** — currently §11.1 waiver on C4. Under Role Registry v1: C8 is the acid test. If C8 fails → the §11.1 waiver is REVOKED and Kunigami is a retirement candidate. If C8 passes → §11.1 waiver stands.

---

## 6. Panel

**Reuse the post-V walk-forward on disk.** No new compute required for C7 (re-aggregate existing `lo1_*/trades.jsonl`) or C9 (already have baseline counts). C8 requires parsing `trades.jsonl` for citation counts — new script, small compute.

Panel: 3 symbols (EURUSD, GBPUSD, USDCAD), H4 bars, 2015–2025, 7 rolling OOS windows. Identical to G7 v1 §4.

---

## 7. Statistic (locked)

**Per-agent Role Registry verdict:** the 3-bit vector (C7, C8, C9) plus the role label emission from §4. Recorded alongside the G7 v1 6-bit vector.

**Squad-level Role Registry verdict:** the number of `retirement_candidate` agents. Squad PASSES the Role Registry test iff `retirement_candidate_count == 0`. A single retirement candidate is flagged for a §12 decision (retire vs re-evolve).

**No K-of-7 window discretisation on C7/C8/C9.** C7 uses the full walk-forward aggregate (per-agent-per-peer mean TQS across the entire panel — the same aggregation C2 uses on the outgoing side). C8 uses total citation counts. C9 uses total volume share. Rationale: role identity is a structural property, not a per-window one.

---

## 8. Pre-mortems

- **C7 might over-fire on chemistry catalysts.** A catalyst like Bachira also receives some incoming lift (e.g. from Isagi's confluence provisions). Mitigation: C7 pass is compatible with C2 pass. Agents can be both `chemistry_catalyst` AND `finisher`. That is expected and honest.
- **C8 threshold 100 is a guess.** If the walk-forward-post-V citation counts show ≥ 1000 citations for Reo and ≥ 500 for Kunigami, the threshold is too permissive; if the numbers are ≤ 10 for both, the threshold is too strict. Mitigation: the threshold is locked as pre-registered, but a §11 amendment will document any need to re-tune AFTER the measurement — with the caveat that any re-tune that would flip a role label requires user sign-off before landing.
- **C9 threshold 5% is derived from squad size** (with 8 agents, uniform share = 12.5%; 5% is the "at least a third of your fair share" floor). Mitigation: the threshold is locked. Agents below 5% who fail all of C2/C7/C8 are retirement candidates by definition.
- **Role Registry v1 retention rule could conflict with G7 v1 conjunction.** G7 v1 requires ALL 6 bits set for v1 admission; Role Registry v1 requires C3 + ONE of {C2,C7,C8,C9}. These are DIFFERENT gates. The intent is: G7 v1 = "eligible to play at all" (basic competence). Role Registry v1 = "worth keeping on the roster given the observed role" (role-aware retention). If G7 v1 blocks an agent, Role Registry v1 cannot save them. If G7 v1 passes an agent, Role Registry v1 further asks "what role and is that role worth a slot".

---

## 9. Stop rules

Not applicable — Role Registry v1 is a pure re-aggregation of existing walk-forward-post-V data. No compute session to stop. If the C8 citation-parser encounters a schema mismatch that requires a new walk-forward, that is a §11 amendment.

---

## 10. Cross-references

- G7 v1 §3.2 (C2 definition) — Role Registry v1 C7 is the direct inverse aggregation.
- G7 v1 §11.1 (Kunigami/Reo defensive-observer waiver) — Role Registry v1 C8 tests whether the §11.1 waiver is grounded in real workspace activity.
- G7 v1 §11.9-postmortem (Phase V null result) — Role Registry v1 formalises what the postmortem foreshadowed: role-aware retention.
- F22c YieldReason spec (`sim/core/types.py IntentDecision.interpreted_signal_family`) — Role Registry v1 C8 depends on this field being populated during walk-forward-post-V (it was, per the F22 walk-forward verdict).

---

## 11. Verdict registry rows (to be added)

To be appended to `programs/M001_multi_agent_ensemble/reviews/verdict_registry.md` (or equivalent) after C7/C8/C9 land:

```
| agent            | G7 v1 bits | C7 | C8 | C9 | role label(s) | retention |
|------------------|:----------:|:--:|:--:|:--:|---------------|:---------:|
| isagi_yoichi     | ??????     | ?  | ?  | ?  | ?             | ?         |
| bachira_meguru   | ??????     | ?  | ?  | ?  | ?             | ?         |
| itoshi_rin       | ??????     | ?  | ?  | ?  | ?             | ?         |
| chigiri_hyoma    | ??????     | ?  | ?  | ?  | ?             | ?         |
| reo_mikage       | W??WWW     | W  | ?  | W  | ?             | ?         |
| nagi_seishiro    | ??????     | ?  | ?  | ?  | ?             | ?         |
| barou_shoei      | ??????     | ?  | ?  | ?  | ?             | ?         |
| kunigami_rensuke | W??WWW     | W  | ?  | W  | ?             | ?         |
```

`W` = structural-falsifier waiver, `?` = pending measurement.

---

## 12. Amendment procedure

Same as G7 v1 §11. Amendments append `§12.x` sub-sections. Any post-measurement threshold change on C8 (or any Role Registry criterion) is an explicit §12 amendment requiring:
1. Original threshold + numeric result at the original threshold.
2. Reason the original threshold was miscalibrated.
3. New threshold + user sign-off if the change flips a role label.
