# Phase W-barou v1.1 — postmortem (NULL RESULT)

**Status:** NULL RESULT (2026-07-03 09:47 UTC)
**Verdict:** AMBIGUOUS zone per PROTOCOL §5 → no auto-land, escalate.
**Recommendation:** leave H1 code in place as diagnostic (Phase V-b precedent), amend PROTOCOL to reflect the null, escalate the underlying problem to Phi5 Arm 3/4.

---

## 1. Locked pre-run acceptance thresholds (from PROTOCOL §5)

| Statistic | LAND threshold | REVERT threshold | Post-V baseline | Post-W measured |
|---|---:|---:|---:|---:|
| `Barou_n_trades` | ≥ 250 | < 100 | 153 | **153** |
| `Barou_mean_tqs` | ≥ 0.34 | < 0.30 | 0.347 | **0.347** |
| `Bachira→Barou C3 cannibalisation` | ≤ 0.60 | -- | 0.841 | **0.841** |

`n_trades` is at 153 — above REVERT, below LAND. `mean_tqs` at 0.347 — same distance from LAND (0.34) as post-V, just barely above threshold, but the LAND rule requires trades ≥ 250 too, which fails. Cannibalisation unchanged.

**Verdict:** AMBIGUOUS. No auto-land, no auto-revert. §5 mandates a postmortem — this document.

---

## 2. Byte-level per-agent comparison

Recomputed from `reviews/g7_replay_cache_walk-forward-post-V/trades.jsonl` and `reviews/g7_replay_cache_walk-forward-post-W/trades.jsonl`:

| Agent | n_trades V | n_trades W | ΔN | mean_tqs V | mean_tqs W | Δtqs |
|---|---:|---:|---:|---:|---:|---:|
| `isagi_yoichi` | 1923 | 1923 | +0 | 0.3568 | 0.3568 | +0.0000 |
| `bachira_meguru` | 2542 | 2542 | +0 | 0.4026 | 0.4026 | +0.0000 |
| `itoshi_rin` | 421 | 421 | +0 | 0.3940 | 0.3940 | +0.0000 |
| `chigiri_hyoma` | 430 | 430 | +0 | 0.2585 | 0.2585 | +0.0000 |
| `nagi_seishiro` | 135 | 135 | +0 | 0.4313 | 0.4313 | +0.0000 |
| `barou_shoei` | 153 | 153 | +0 | 0.3469 | 0.3469 | +0.0000 |

**Every single per-agent stat is identical to four decimal places.** Squad totals: 5604 trades in both runs, 28842 proposals in both, 336707 thoughts in both, byte-identical `workspace_counts.json`.

This is the same shape of null result as Phase V-b (2026-07-02): the H1 lift is applied on ticks that were NOT the deciding ticks. No R6 tournament outcome flipped.

---

## 3. Root cause diagnosis

Phase W-barou H1 fires the +0.10 conviction lift when Bachira did NOT publish a same-direction thought on Barou's symbol at the tick barrier. The mechanic is behaviourally correct — it applies to the exact ticks it was designed for. But those ticks are structurally NOT the ticks where Barou is losing.

Reasoning trace, made concrete via C3 evidence:

1. C3 post-V verdict shows Bachira excluded → Barou gains **+808 trades** (84.1% cannibalisation ratio).
2. Those 808 trades are ticks where **Bachira DID publish same-direction on Barou's symbol** and won the R6 tournament by higher TQS-adjusted conviction.
3. H1 EXPLICITLY SKIPS those ticks (branch `bachira_same_direction=True` → `yield_reason=peer_claimed_slot_no_lift`). The existing devour mechanic handles them, and Phase V-b already proved the devour lift doesn't flip those tournaments either.
4. Therefore H1 only fires on the ticks where **Bachira was NOT competing** (silent or opposite direction). On those ticks, Barou was already winning — his proposal was the only one on the (symbol, direction) slot, so R6 was uncontested.
5. Adding +0.10 conviction to an already-winning proposal changes NOTHING at the aggregator level. Trade outcome is identical.

**Formal statement:** H1 targets the wrong set of ticks. The set of ticks where Bachira does NOT compete is disjoint from the set where Barou needs help.

This is the SAME structural failure as Phase V-b's tier promotion. Both mechanics attempted to give Barou an edge at the agent-conviction level. Both faced the same reality: Barou's problem is **aggregator single-slot mutex**, not conviction inadequacy. When Bachira and Barou compete on the same (symbol, direction) slot, the aggregator picks the higher-TQS proposal (Bachira's), and no agent-side lift can change that as long as the aggregator remains single-position-per-slot.

---

## 4. What Phase W-barou v1.1 DID accomplish (auditable diagnostic value)

Not a wasted phase. The mechanic emits new rationale fields (`barou_lone_conviction_claim`, `barou_lone_conviction_lift_applied`, `barou_v1_1_bachira_read_present`, `barou_v1_1_bachira_same_direction`, `barou_v1_1_bachira_direction`, `barou_workspace_snapshot_ok`, `_yield_reason`) that let post-hoc audits distinguish:

- How often Bachira publishes same-direction on USDCAD (the ticks where Barou is blocked).
- How often Bachira publishes opposite-direction (Barou's counter-conviction opportunities).
- How often Bachira is silent (Barou's lone-conviction opportunities).
- Which of those buckets produces trades under the current aggregator.

Those diagnostics are useful for the Phi5 Arm 3/4 pre-registration — the multi-position aggregator design needs to know which slot-competition patterns are common and which are rare.

The rationale trail is kept for that reason. See §5 recommendation.

---

## 5. Recommendation (blue-lock alignment)

**Leave the H1 code in place as diagnostic** (Phase V-b precedent, PROTOCOL §11.9-postmortem 2026-07-02). Do NOT revert.

Rationale:
- The mechanic is behaviourally correct and adds audit-grade rationale fields.
- Removing it deletes the diagnostic value described in §4.
- Adding a `_effective_tier`-style routing flip is EXPLICITLY forbidden by the acceptance rule (Phase V-b null result is the direct precedent).
- The three-branch decision table (`peer_did_not_read_this_setup` / `peer_claimed_slot_no_lift` / `workspace_unavailable`) is exactly the kind of signal Phi5 Arm 3/4 will want to consume.

**Amend `experiments/G7_v1_checkpoint_gate/PROTOCOL.md`** with a `§11.11 (2026-07-03)` sub-section that records:
- Phase W-barou v1.1 landed as pre-registered.
- Null result on the trade-count / mean-TQS axes.
- Root cause: aggregator single-slot mutex, not agent conviction.
- H1 remains as diagnostic; no tier override applied.
- Escalation to Phi5 Arm 3/4 (see §6 below).

**Update `experiments/phase_w_barou/PROTOCOL.md` §11 verdict registry** with the AMBIGUOUS-null row.

**Do NOT** propose a Phase W-barou-v1.2 iteration at the agent conviction level. The direct-competition path is closed. Any successful Barou rescue requires an aggregator-level intervention.

---

## 6. Escalation — Phi5 Arm 3 / Arm 4

The Bachira-Barou cannibalisation is fundamentally an **aggregator routing** problem. The two viable interventions per the Phi5 arms design draft:

**Arm 3 — Same-direction merge:** When Bachira and Barou both propose long-USDCAD at the same tick, the aggregator MERGES the two proposals into a single "consensus" position with blended sizing / entry, rather than picking one and dropping the other. Both agents get credit for the trade (dual-authorship in the trade ledger). This preserves the "one position per symbol" invariant while eliminating the winner-take-all penalty on the losing agent.

**Arm 4 — Multi-position:** When multiple agents propose on the same (symbol, direction) slot AND their entries differ by ≥ N pips, the aggregator publishes BOTH as separate positions. Position management costs go up (2x SL/TP tracking, 2x margin) but slot-competition disappears. Barou's H2 (continuation-entry offset) was designed for this path.

Both arms are in the Phi5 pre-registration (`phase_v_iterate/PROTOCOL.md`). Both explicitly cite C3 evidence as the empirical motivation.

Recommend running **Arm 3 first** (smaller code change, more conservative). If Arm 3 lands positive → Arm 4 becomes optional. If Arm 3 lands null → Arm 4 becomes mandatory. Either way, the Bachira-Barou cannibalisation gets a real fix at the aggregator level rather than agent-level bandage.

The Phi5 re-sim compute (~4-6h) is next in the pipeline after this postmortem.

---

## 7. What this means for the Role Registry v1 verdict

Post-W does NOT change any Role Registry v1 numbers — all agents' baseline stats are byte-identical to post-V. The Barou retention verdict stays as `workspace_catalyst` (single axis, C8 pass at 151.3 epsilon-units). The Bachira retention verdict stays as NOT RETAINED (C3 fail).

The Role Registry v1 verdict already flagged this correctly: Barou's problem is not that he's an unproductive agent, but that his single retained axis is thin. Phase 5 Arm 3/4 is the intervention path that would widen his retention (by resolving the Bachira cannibalisation → Barou passes C3 for Bachira → Bachira retains, AND Barou gains trade volume → C9 might pass → Barou has two axes).

Full status blocked on Phase 5.

---

## 8. Reproducibility

- Panel: identical to G7 v1 (§4 of G7 v1 PROTOCOL) and post-V walk-forward.
- Random seeds: none used by the simulator (per doctrine §3.11).
- Compute wall-clock: 3166 seconds (~53 min on M001 panel).
- Baseline cache: `reviews/g7_replay_cache_walk-forward-post-W/`.
- Verdict artifact: `reviews/g7_v1_checkpoint_verdict_walk-forward-post-W.md`.
- Compute log: `reviews/logs/g7_walk_forward_post_W.stdout.log`.
- Heartbeat log entries: from `2026-07-03T08:55:23` to completion.
