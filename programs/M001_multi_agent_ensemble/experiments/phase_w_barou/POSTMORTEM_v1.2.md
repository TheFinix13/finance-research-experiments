# Phase W-barou v1.2 — postmortem (HALT: premise failure, major structural finding)

**Status:** HALT per pre-registered stop rule (2026-07-06 evening)
**Stop rule hit:** PROTOCOL_v1.2.md §5 — `barou_v1_2_stop_source="bachira_anchor"` fired on **0 of 4,576** eligible proposals.
**Verdict artifact:** `../../reviews/wbarou12_verdict.json` (analysis: `scripts/analyze_wbarou12.py`).
**Runs:** walk-forward `wbarou12-arm4` (7,273 trades — byte-identical to the Arm 4 control) + lo1-bachira `wbarou12-arm4` (Barou 1,280 — byte-identical to §11.7). Heartbeat clean on both.

---

## 1. What happened

The H2 mechanic is implemented correctly (unit tests prove it fires on tighter anchors, clamps at the 6.6-pip floor, rejects wrong-side anchors) and was active in both runs (`barou_v1_2_enabled=True` on all 4,576 same-direction proposals). It never fired in the market data because the firing condition **cannot occur**:

| shared USDCAD ticks (Barou + Bachira same tick) | Bachira stop tighter | equal | wider |
|---:|---:|---:|---:|
| 4,576 | **0** | **4,576** | 0 |

Entry, stop, and TP are identical to full float precision on every contested tick.

## 2. Root cause — the premise was false

`A2BachiraV1` and `A7BarouV1` wrap the **same production `SupplyDemandAlpha` with the same parameters** (`htf_align=None`, `target_rr=1.5`). Bachira's `rebel_tight` playstyle label describes his conviction mechanics (rebel lift), NOT his stop geometry. On USDCAD the two agents are **the same strategy** — different conviction, different narrative, identical trade geometry.

The §2 motivation in PROTOCOL_v1.2.md inferred "Bachira publishes structurally tighter stops" from the playstyle label without checking the cell params. That inference was wrong, and the pre-registered stop rule caught it at zero cost to integrity: the treatment run is byte-identical to control (squad 0.3643, Barou 567 @ 0.3944, cannibalisation 55.7% — all unchanged), so nothing was contaminated.

## 3. The actual finding (bigger than the phase)

**The Bachira→Barou "cannibalisation" is not slot competition between two reads — it is literal strategy duplication.** When Bachira is removed, Barou's +713 "recovered" trades are the SAME trades relabelled from Bachira to Barou, not suppressed independent alpha. Consequences:

1. **The C3 FAIL on Bachira is a measurement artifact of duplication.** C3 was designed to detect an agent whose presence *suppresses a peer's distinct alpha*. Here the "suppressed" alpha is a duplicate of the suppressor's own trades. Removing Bachira gains the squad nothing (squad TQS invariant, §11.5) — it just reassigns attribution.
2. **The residual 55.7% under Arm 4 is mostly CORRECT risk behaviour**: R1/R6 blocking a second identical position on the same symbol at the same tick is the risk system refusing to double the same trade — the §11.6 rejection ledger (1,713 R1 + 1,608 R6 blocks) is the sandbox declining leverage-on-a-duplicate, not lost opportunity.
3. **No aggregator or stop-geometry mechanic can fix this**, because there is no second read to admit. The only honest fixes are agent-level differentiation: give Barou a genuinely different USDCAD weapon (different cell parameters, different signal family — a true v2 arc under doctrine §3.11.5), or accept the duplication and leave the roster as-is.

## 4. Disposition (pre-registered rules honoured)

- **HALT recorded; no retuning.** The locked constants stay; no anchor-offset search, no premise patch-and-rerun. Any Barou differentiation mechanic is a NEW pre-registration (candidate: "Phase Y-barou v2 weapon differentiation" — parked, do not start without discussion).
- **v1.2 code stays in place, default OFF** (same precedent as v1.1 H1 and Phase V-b): the mechanic is correct, adds the `barou_v1_2_*` audit rail, and costs nothing when disabled. Sealed caches unaffected (treatment run proved byte-identity even when enabled).
- **Role Registry consequence (recommendation, needs its own amendment before acting):** Bachira's C3 FAIL should be annotated as duplication-artifact pending a C3 v2 definition that tests whether the "recovered" lo1 trades are *distinct* from the removed agent's trades (e.g. tick-overlap of recovered trades with the excluded agent's baseline trades). Under such a definition Bachira likely passes and the squad Role Registry verdict flips to PASS.
- **Phase X-kunigami Wild Card gate is unblocked** (it was sequenced after this verdict) and remains the next compute-bearing experiment.

## 5. Reproducibility

- Caches: `reviews/g7_replay_cache_wbarou12-arm4/`, `reviews/g7_leave_one_out_wbarou12-arm4/lo1_bachira_meguru/`.
- Logs: `reviews/logs_wbarou12/{walk_forward,lo1_bachira}.stdout.log`.
- Compute: walk-forward ~27 min, lo1 ~25 min, parallel; heartbeat monitor exit 0.
- Determinism cross-checks: treatment squad per-agent table byte-identical to `phi5-arm4-post-kunigami`; lo1 Barou count byte-identical to §11.7 (1,280).
