# Phase W-barou v1.2 — pre-registered protocol (H2 continuation-entry under Φ5 Arm 4)

**Status:** HALTED same day per §5 stop rule — the anchor premise is false (Bachira and Barou share identical stop geometry; 0/4,576 anchor fires). See `POSTMORTEM_v1.2.md` for the structural finding (strategy duplication, not slot competition). Pre-registration below preserved verbatim.
**Original status:** PRE-REGISTERED (2026-07-06 evening, BEFORE any v1.2 compute)
**Parent:** `PROTOCOL.md` (v1.1, H2 deferred per §1) + `POSTMORTEM.md` (v1.1 NULL, escalation to Φ5)
**Unblocking event:** Φ5 Arm 4 (multi-position K=2) ADOPTED as default G7-era aggregator, `../phi5_aggregator/PROTOCOL.md` §11.6 (2026-07-06). The single-slot mutex that nullified Phase V-b and W-barou v1.1 is gone; the agent-side complement is now measurable.
**Chemistry baseline (canonical):** `../../reviews/g7_leave_one_out_verdict_phi5-arm4.md` — Bachira→Barou cannibalisation **55.7%** (Barou 567 trades with Bachira present vs 1,280 absent), still a C3 FAIL against the 50% threshold.

---

## 1. Hypothesis (H2, v1.2 restatement)

**H2 (continuation-entry, Bachira-anchored stop):** when Bachira has published a same-direction thought on Barou's symbol at the tick barrier (the exact branch v1.1 H1 skips), Barou's proposal is a *continuation* of a peer-confirmed move. His invalidation can therefore anchor to **Bachira's structural stop** instead of his own wider baseline-zone stop. The tighter stop reduces Barou's risk dollars, which directly attacks the two blockers measured under Arm 4 (see §2), admitting Barou alongside Bachira instead of instead-of-nothing. Prediction: Barou's with-Bachira trade count rises and the lo1-bachira cannibalisation ratio drops below the 50% C3 threshold.

### Why the v1.1 "entry offset" wording is translated to a stop anchor (locked pre-run)

v1.1 §3-H2 sketched "a delayed entry 2–3 pips beyond Bachira's trigger". The sandbox fill model (`agent.alphas.backtest._open`, mirrored by `_open_trade_from_proposal`) fills every proposal at next-bar open and **re-anchors stop/TP to the fill using only the proposal's stop-distance and TP-distance geometry**. Consequences, verified against the code before this pre-registration:

1. An entry offset with risk-neutral geometry (stop distance preserved) produces a **byte-identical Trade** — a guaranteed null by construction, exactly the §11.4-D class of sandbox-translation error we are required to fix pre-run, not discover post-run.
2. An entry offset with the stop *price* held fixed **widens** the stop distance for a continuation entry, *increasing* risk dollars — and the measured Arm 4 rejection ledger (§2) shows risk dollars are precisely what blocks Barou.

The faithful sandbox translation of "continuation entry on peer-confirmed momentum" is therefore the component of the idea that survives the fill model: **structure-anchored tighter invalidation**. Entry stays Barou's own read; the stop anchors to Bachira's published invalidation when that is tighter. This is a pre-run design translation in the spirit of Φ5 §11.4 D, not a post-hoc retune.

---

## 2. Empirical motivation (locked numbers from the Arm 4 caches)

From `g7_replay_cache_phi5-arm4-post-kunigami/proposals_rejected.jsonl` (the §11.5 pre-registered walk-forward):

| Barou rejection reason | count |
|---|---:|
| `lower_conviction_same_symbol` (aggregator rank, non-physical under Arm 4 iteration) | 4,789 |
| `sentinel_R1_block` (his OWN per-trade risk over cap at fixed lot) | 1,713 |
| `arm4_sentinel_R6_block` (combined risk with existing position over 50% cap) | 1,608 |
| `arm4_slot_full` | 284 |
| `arm4_same_agent_already_on_symbol` | 78 |

All 8,472 on USDCAD. The two *physical* blockers (R1 + R6 = 3,321) are both monotone in Barou's stop-distance dollars. Bachira (`rebel_tight` playstyle) publishes structurally tighter stops on the same zone events; his coordinate rationale carries `entry`/`stop`/`take_profit` (F21 plumbing already in place — same fields Nagi borrows).

---

## 3. The mechanic (locked)

Lives in `sim/agents/a07_barou.py::A7BarouV1.intend()`, inside the existing `bachira_same_direction=True` branch (the branch H1 explicitly skips — so H1 and H2 partition the workspace-available decision table and v1.1 behaviour is unchanged on H1's branches).

**Gating (byte-compat guard):** the mechanic is OFF by default. `A7BarouV1(continuation_entry_enabled=True)` must be passed explicitly; the harnesses expose `--barou-v12`. Sealed phi41-era replays and every existing cache remain byte-identical because the default constructor never activates the branch.

Decision, when `continuation_entry_enabled` AND `bachira_same_direction` AND Bachira's coordinate rationale carries a numeric `stop`:

```
sign            = +1 if direction == "long" else -1
own_stop_dist   = |barou_entry - barou_stop|
candidate_dist  = sign * (barou_entry - bachira_stop)      # >0 iff Bachira's stop is on the adverse side
if candidate_dist <= 0:  fall through (stop_source="own", invalid anchor)
new_stop_dist   = max(CONTINUATION_MIN_STOP_PIPS * pip, min(own_stop_dist, candidate_dist))
if new_stop_dist < own_stop_dist:
    stop  = barou_entry - sign * new_stop_dist
    tp    = barou_entry + sign * BAROU_V1_PARAMS["target_rr"] * new_stop_dist   # RR 1.5 preserved
    stop_source = "bachira_anchor"
else:
    unchanged (stop_source="own")
```

**Locked constants:**

- `BAROU_V1_2_CONTINUATION_MIN_STOP_PIPS = 6.6` — the measured post-V panel minimum stop (Φ5 §11.4 D distribution, n=5,604). The mechanic can never create a stop tighter than anything the squad has ever traded.
- `BAROU_V1_PARAMS["target_rr"] = 1.5` — unchanged; TP re-derived from the new stop distance so RR is preserved, not gamed.
- **No conviction change.** Phase V-b and W-barou v1.1 both proved conviction-level lifts are dead ends (POSTMORTEM §3); v1.2 touches risk geometry only.

**Rationale stamps (audit-grade, extends the v1.1 trail):**

- `barou_continuation_entry: bool` (True iff the anchored-tighter stop was applied)
- `barou_v1_2_enabled: bool`
- `barou_v1_2_stop_source: "own" | "bachira_anchor" | "invalid_anchor"`
- `barou_v1_2_stop_pips_own: float`, `barou_v1_2_stop_pips_final: float`

---

## 4. Runs (locked, both under `--aggregator-arm arm4 --retire-kunigami --barou-v12`)

Panel/env identical to Φ5 §11.4 (3 symbols, H4, 2015–2025, sentinel physical, workspace + shadow ledger on). Heartbeat monitor mandatory on every PID.

1. **Full-squad walk-forward**, tag `wbarou12-arm4` (7-agent roster). Comparator: `g7_replay_cache_phi5-arm4-post-kunigami` (7,273 trades, squad median-of-window-mean TQS 0.3643, Barou 567 @ 0.3944).
2. **lo1-bachira replay**, tag `wbarou12-arm4` via `run_g7_leave_one_out --exclude bachira_meguru --no-aggregate`. Comparator: §11.7 lo1 cache (Barou 1,280 absent-Bachira trades).

**Comparison arithmetic (locked):** cannibalisation ratio = 1 − (Barou n_trades in run 1) / (Barou n_trades in run 2), the same reduction-ratio arithmetic as C3 in `run_g7_leave_one_out.compute_c2_c3`. Current value 1 − 567/1280 = 55.7%.

---

## 5. Verdict rules (locked pre-run)

- **LAND v1.2** iff ALL of:
  - cannibalisation ratio **< 50%** (C3 threshold — the entire point of the phase);
  - squad median-of-window-mean TQS ≥ **0.3593** (control 0.3643 − 0.005 noise band);
  - Barou mean TQS ≥ **0.34** (v1.1 §5 quality floor, unchanged);
  - Barou same-bar-stop rate on `barou_continuation_entry=True` trades < **30%** (Φ5 §8 pre-mortem redundancy bound — a tighter stop must not just convert admissions into instant stop-outs);
  - Rin guardrail: mean TQS ≥ 0.36 AND n_trades ≥ 350 (v1.1 §6, unchanged).
- **REVERT** if Barou n_trades (run 1) < **400** (below the 567 status quo — mechanic made things worse) OR Barou mean TQS < **0.30**.
- **AMBIGUOUS zone** → postmortem, no auto-land, no retuning of the locked constants (no offset/floor/RR search). Any iteration is a new pre-registration.

Stop rules: halt if run 1 squad trades < 3,000 (structural break vs 7,273); halt on heartbeat stall (>10 min gap); halt if `barou_v1_2_stop_source="bachira_anchor"` fires on 0 proposals (plumbing bug, not a result).

---

## 6. Cross-references

- Φ5 `PROTOCOL.md` §11.4 D (sandbox-scale translation precedent), §11.6 (Arm 4 adoption + measurement-not-gate rule), §11.7 (canonical chemistry baseline this phase must beat).
- v1.1 `POSTMORTEM.md` §3 (root cause), §5 ("do not iterate at the conviction level" — honoured: v1.2 is geometry-level).
- Role Registry v1 §3 (C3 reduction-ratio arithmetic).
