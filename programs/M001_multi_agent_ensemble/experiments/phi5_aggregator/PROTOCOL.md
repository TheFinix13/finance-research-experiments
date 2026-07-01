# Φ5 Aggregator Selection Experiment — pre-registered protocol

**Status:** `pre-registered` — 2026-06-25
**Author:** orchestrator (foreground; the parallel worker `[Φ5 aggregator pre-registered protocol]` resource-exhausted before producing output)
**Gate context:** This is the internal selection experiment for Φ5. Its output (the winning aggregator arm) feeds the **G6** gate (Φ5 → Φ6 full-squad-vs-Sae) which is already registered in `docs/methodology/gate_verdict_registry.md`. The selection experiment uses G6's locked statistic by inheritance; no new gate is registered.

> **Why this exists.** Both Φ4 (squad FAIL @ 0.98×) and Φ4.1 (expanded squad FAIL @ 0.92×) and Isagi v1→v2 (arc FAIL with sweep weapon cannibalising zone slots) converged on the same diagnosis: the **single-position-per-symbol queue with conviction-only ranking** is the binding constraint. Roster expansion confirmed that Nagi's F11 confluence predicate works once given peer fuel (0 → 34,302 confluence-firing thoughts), but the squad still loses to Isagi-alone because slot allocation is wrong. The Φ5 lever is the **aggregator**, not more strikers.

---

## 1. Hypothesis

**H0:** No aggregator change improves squad TQS over the Φ4.1 baseline (median OOS-window mean-TQS = 0.2922) by more than the multiple-comparison-corrected critical value across the 5 treatment arms tested.

**H1:** At least one aggregator arm reaches squad TQS ratio ≥ 1.00× Isagi-alone (≥ 0.3175) AND beats the Φ4.1 control by Δ ≥ 0.020 in median-of-window-means TQS, with a 95% bootstrap CI lower bound > 0.

**Rejection criterion:** PASS = H1 satisfied with Bonferroni-corrected α = 0.05/5 = 0.01 across the 5 arms (any one arm meeting CI lower bound > 0 at α=0.01).

---

## 2. Empirical motivation (numbers locked)

| Source | Number | What it shows |
|---|---|---|
| Φ4 squad FAIL | 0.2918 squad TQS / 0.98× Isagi-alone | 4-agent MVP loses edge |
| Φ4.1 squad FAIL | **0.2922 squad TQS / 0.92× Isagi-alone** (control baseline for this experiment) | 8-agent expansion does not close the gap |
| Φ4.1 telemetry | Isagi 0 trades, Barou 0 trades — both slot-cannibalised by Bachira's +0.10 rebel-lift | conviction-only ranking on a single slot starves canonical agents |
| Isagi v1→v2 arc FAIL | zone trades 856 → 311 with byte-equivalent zone signal | sweep weapon held the slot the zone needed |
| Φ4 rejection analysis | 1,579 / 2,994 = **52.7%** of Isagi rejections were SAME-DIRECTION as another agent's accepted proposal | the squad agreed but only one slot existed |
| Nagi v1 effective | 645 proposals, 94 trades, mean TQS **0.349 (highest in 8-agent squad)** | the canonical agents are the high-TQS source; conviction ranking does not preserve them |

These five empirical facts point at the same root cause and motivate the 5 treatment arms below.

---

## 3. Treatment arms

Arm 0 is the locked control. Arms 1–4 are independent isolated treatments. Arm 5 is the stacked combination. All arms run on the same OOS panel with the same Φ4.1 roster (8 agents) and the same regime classifier (live-classes only).

### Arm 0 — Control (Φ4.1 aggregator as-is)

- **Source:** existing `sim/core/aggregator.py`, single-position-per-symbol queue, conviction-only ranking, equal per-agent risk budget.
- **Already evaluated:** squad median OOS-window mean-TQS = **0.2922**, ratio 0.92× Isagi-alone.
- **Implementation cost:** 0 (already shipped).
- **Re-run requirement:** no re-run; numbers come from `phi41_squad_v1_trades.jsonl`.

### Arm 1 — HRP (Hierarchical Risk Parity weighting)

- **Mechanic:** Replace flat per-agent risk with HRP-style weights derived from agent OOS TQS covariance. Down-weights correlated, low-edge agents.
- **Source:** port from production `agent/alphas/allocator.py` (mean-variance tangency with Ledoit-Wolf shrinkage, long-only clipping, fallback to equal-weight on positive-edge agents). The production code uses pip-P&L; the port replaces with TQS series.
- **Locked parameters:**
  - `lookback_windows = 3` OOS windows (≈ 3 yrs of trades) for covariance estimation
  - `shrinkage = 0.2` (Ledoit-Wolf-toward-diagonal, matches production)
  - `min_trades_per_agent = 30` (else excluded — F6 minimum-n rule)
  - `weight_floor = 0.0`, `weight_cap = 0.5` (no agent gets > 50% of risk budget)
  - Fallback when < 2 eligible agents: equal-weight on positive-TQS agents (matches production fallback)
- **Pre-mortem:** Covariance unstable with 8 agents × small trade count. If `min_trades_per_agent` excludes Rin (94 trades) or Nagi (94 trades), Arm 1 effectively becomes 6-agent allocation. Track this in the report.

### Arm 2 — TQS-conditional conviction floor

- **Mechanic:** Filter proposals below per-agent historical OOS TQS percentile P before they reach the conviction queue. Keeps single-position-per-symbol but raises the bar on what gets queued.
- **Locked parameter:** `P = 0.40` (filter bottom-40th-percentile per-agent TQS proposals). Justification: Φ4.1 worst-quartile of Bachira (mean TQS 0.299, median 0.247) and Chigiri (mean TQS 0.210, median 0.180) trades drag squad mean — filtering bottom 40% of each agent's own historical TQS distribution preserves selectivity.
- **Pre-mortem:** Likely filters Nagi (n=94, all his trades are by definition his "historical distribution"). Mitigation: P-floor only applies to agents with ≥ `min_n_for_floor = 200` historical OOS trades. Below 200, agent gets a free pass (paired with Arm 1's `min_trades_per_agent = 30` — agents in the "free-pass-but-allocated" band are flagged).

### Arm 3 — Same-direction merge

- **Mechanic:** When N ≥ 2 agents propose the same direction (long/short) on the same symbol within window W, aggregate into a single position with merged SL/TP. Does NOT lift single-position-per-symbol.
- **Locked parameters:**
  - `W = 1 H4 bar` (concurrent on the same close)
  - SL: tightest of all merged proposals
  - TP: median of all merged proposals
  - Conviction: max across merged proposals (winner-takes-all) — but with the merged SL/TP
  - Source-attribution: trade tagged with all contributing agent IDs; per-agent KPIs split P&L by F12 attribution share
- **Pre-mortem:** Tightest-SL choice may invalidate proposals before they would naturally trigger SL on their own basis. This is intentional (better risk control) but could clip Barou-style fat-right-tail trades early. Track per-agent attributed mean pips before vs after.

### Arm 4 — Multi-position-per-symbol

- **Mechanic:** Allow up to K concurrent positions per symbol if proposals come from distinct agents. Constrained by total-risk-per-symbol cap.
- **Locked parameters:**
  - `K = 2` positions per symbol (start small)
  - `total_risk_cap_per_symbol = 1.0%` of equity (matches single-position cap; budget split across concurrent positions)
  - `correlation_block`: if two open positions on the same symbol are same-direction, treat as one position for the cap (no doubling on same direction; that's Arm 3's job)
  - `concurrent_distinct_agents = 2` minimum (no single agent occupies both slots)
- **Pre-mortem:** May inflate drawdown if positions correlate at the trade-outcome level (e.g. both stop out on the same news bar). Track concurrent-positions-stop-on-same-bar event count; if > 30% of multi-position events end this way, Arm 4 is structurally redundant with Arm 3.

### Arm 5 — Combined (1 + 2 + 3 + 4 stacked)

- **Mechanic:** All four treatments active simultaneously.
- **Order of operations:** TQS-floor (Arm 2) filters the proposal pool first → same-direction merge (Arm 3) collapses surviving same-direction proposals into one merged proposal per symbol-direction → multi-position policy (Arm 4) admits up to K=2 distinct merged proposals per symbol → HRP (Arm 1) sets the risk weight for each admitted proposal.
- **This is the headline arm.** The selection criterion is structured to favour Arm 5 if it dominates the isolated arms, which is the architecturally interesting case.
- **Pre-mortem:** Interaction effects may dominate. If Arm 5 underperforms its component arms in isolation, the combination has a destructive interaction — a real finding, not a failure.

---

## 4. Locked decision rule

### Locked statistic (inherited from G6 / G5-squad)

**Median across OOS windows of per-window mean TQS (F12) for the squad's fused trade stream.**

This is the same statistic used at G5-squad (Φ4 / Φ4.1), G6 (Φ5 → Φ6 vs Sae), and C1. Inheriting this statistic keeps the verdict ladder coherent: Φ4.1 control = 0.2922, every arm in this experiment is comparable to Φ4.1 directly and to Isagi-alone (0.3175) directly.

### Selection criterion (within experiment)

Each arm produces a median-of-window-means TQS. The **winner** is selected by:

1. **Multi-arm correction:** Bonferroni at α = 0.05 / 5 = 0.01 across Arms 1-5 (Arm 0 is control).
2. **CI test:** for each arm, bootstrap 95% CI on the per-window-mean-TQS sample (n=7 OOS windows). Arm passes the CI test if CI lower bound > Φ4.1 control TQS (0.2922).
3. **Effect-size threshold:** Δ ≥ 0.020 in median-of-window-means TQS over Arm 0.
4. **Winner = highest median TQS among arms that pass both CI test AND effect-size threshold.**
5. If no arm passes: experiment FAILS, no aggregator change is canonised, Φ5 must explore a different lever (e.g. agent-level changes, regime gating).

### Verdict mapping

| Best-arm median TQS | Ratio vs Isagi-alone (0.3175) | Verdict |
|---|---|---|
| < 0.2922 (control) | < 0.92× | **REGRESS** — H0 holds, control wins |
| ≥ 0.2922 but Bonferroni-corrected CI lower bound ≤ 0.2922 | up to ~0.95× | **NULL** — H0 not rejected, no significant lift |
| Bonferroni-corrected CI lower bound > 0.2922 AND best < 0.3175 | 0.92 ≤ r < 1.00× | **PARTIAL** — significant lift over control but still loses to Isagi-alone |
| Best ≥ 0.3175 AND < 0.349 | 1.00 ≤ r < 1.10× | **PASS-PARTIAL** — beats Isagi-alone; G6 G5-squad-equivalent PARTIAL band |
| Best ≥ 0.349 | r ≥ 1.10× | **PASS** — G6-equivalent PASS band |

### Cross-statistic robustness (mandatory journalled diagnostic)

Per the G5-squad / Φ4.1 addendum precedent, every arm's verdict must be reported alongside a cross-statistic table showing:
- Median OOS-window mean TQS *(locked)*
- Mean OOS-window mean TQS
- Pooled per-trade mean TQS
- Pooled per-trade trimmed mean TQS (10%)
- Median OOS-window mean pips
- Pooled per-trade mean pips
- Cumulative pips (forbidden as scoring; reported for sanity)
- Hit rate

This prevents post-hoc statistic swap and surfaces fat-tail / window-skew anomalies (the same precedent that found Φ4.1 was a stronger FAIL than Φ4 on every TQS-family aggregator but a 6.56× WIN on cumulative pips).

---

## 5. Experimental design

| Field | Locked value |
|---|---|
| Symbols | EURUSD, GBPUSD, USDCAD H4 |
| Time range | 2015-01-01 to 2025-12-31 (matches Φ4.1) |
| OOS windows | 4 yr IS / 1 yr OOS rolling, n=7 windows (matches G5-squad) |
| Agent roster | Φ4.1 8-agent squad (Isagi v1, Bachira v1, Rin v1, Chigiri v1, Reo v1, Nagi v1, Barou v1, Kunigami v1) |
| Regime classifier | Live-classes-only (`trending` + `chop`) — vol_spike + news retired per `regime_redesign_2026-06-24.md` |
| Random seed | inherits `sim/core/seed.py` deterministic policy |
| Friction model | inherits Φ4.1 calibration (or VM-calibration if available) |
| F17 ΔInfo windows | 5 (up from Φ4.1's 1; required for the underpowered flag to clear) |

---

## 6. Stop rules

1. **Hard stop on drawdown sentinel:** any arm causing > 25% peak-to-trough drawdown in a single OOS window → arm flagged as FAIL regardless of TQS, escalate before continuing other arms.
2. **Compute time-box:** total wall-clock budget for the experiment is 12 hours on a single host. If the budget is exceeded, ship a partial verdict (only arms that completed) — never silently truncate to ship a clean number.
3. **Sentinel R1-R5 wiring blocker:** if Arm 4 (multi-position) requires Sentinel R1-R5 to be wired (it does — total-risk cap is a Sentinel R-rule), Arm 4 is GATED on Φ4.2 Sentinel implementation. If Sentinel is not wired by the time this experiment runs, Arm 4 is skipped and the report records "Arm 4 deferred pending Sentinel".

---

## 7. File footprint plan

| Path | Action | Owner |
|---|---|---|
| `sim/core/aggregator.py` | DO NOT MODIFY (Arm 0 control preserves current behaviour) | — |
| `sim/core/aggregator/` | NEW package, contains arm-specific strategies | tomorrow's worker |
| `sim/core/aggregator/__init__.py` | NEW, exports `make_aggregator(arm: str)` factory | tomorrow's worker |
| `sim/core/aggregator/hrp.py` | NEW, ports production `agent/alphas/allocator.py` | tomorrow's worker |
| `sim/core/aggregator/tqs_floor.py` | NEW, P=0.40 percentile filter | tomorrow's worker |
| `sim/core/aggregator/same_direction_merge.py` | NEW, merge logic | tomorrow's worker |
| `sim/core/aggregator/multi_position.py` | NEW, K=2 admission + total-risk cap | tomorrow's worker |
| `sim/core/aggregator/combined.py` | NEW, Arm 5 stacking with locked order-of-operations | tomorrow's worker |
| `sim/scoring/run_phi5_aggregator_gate.py` | NEW, runs all 5 arms + control on the same panel | tomorrow's worker |
| `sim/tests/test_aggregator_arms.py` | NEW, contract tests for each arm | tomorrow's worker |
| `programs/M001_multi_agent_ensemble/reviews/phi5_aggregator_gate.md` | NEW, verdict report | tomorrow's worker |
| `programs/M001_multi_agent_ensemble/reviews/phi5_aggregator_<arm>_trades.jsonl` | NEW per arm | tomorrow's worker |

**Constraint:** Arm 0's results come from `phi41_squad_v1_trades.jsonl` directly — no re-run of control needed.

---

## 8. Pre-mortem (per arm, summarised)

| Arm | Most-likely failure mode | Diagnostic to confirm |
|---|---|---|
| 1 (HRP) | Covariance unstable with 8 agents × few trades | Track number of agents excluded by `min_trades_per_agent`; report covariance condition number |
| 2 (TQS-floor) | Filters Nagi (low-n high-TQS) | Track Nagi trade count under floor vs no-floor; if drops by > 50%, free-pass logic is misconfigured |
| 3 (merge) | Tightest-SL clips fat-right-tail trades early | Compare per-agent attributed mean pips before vs after merge |
| 4 (multi-position) | Concurrent positions correlate at outcome level (both SL on same news bar) | Track concurrent-positions-same-bar-stop event rate |
| 5 (combined) | Destructive interaction across arms | If Arm 5 < max(Arms 1-4), report as architectural finding |

---

## 9. Tomorrow's first-15-minutes execution sequence

1. Read this protocol + `HRP_NOTES.md` (5 min)
2. Pull latest `multi-agent-ensemble` (it's in sync as of session-end 2026-06-25)
3. Confirm any user decisions on aggregator parameter values (the locked values above are the orchestrator's choices; user may override)
4. Implement Arm 1 (HRP) first — port from production allocator. Estimated 60-90 min including tests.
5. Run Arm 1 on a single dev OOS window (2024) before scaling to all 7 windows. Smoke-test.
6. If Arm 1 produces a sensible-looking trade JSONL, proceed to scale up. Else debug.
7. Implement Arms 2 / 3 / 4 in parallel (3 worker subagents — they don't conflict on files since each owns its own aggregator/*.py)
8. Implement Arm 5 last (depends on 1-4)
9. Run all arms via `run_phi5_aggregator_gate.py`
10. Produce verdict report with cross-statistic robustness table

**Estimated total wall-clock:** 6-10 hours for code + tests + run + report. Leaves headroom in the 12-hour stop rule.

---

## 10. Approval

This protocol requires user sign-off on the locked parameters before tomorrow's worker implements:

- **Arm 1 HRP:** lookback=3 windows, shrinkage=0.2, min_trades=30, weight cap=0.5
- **Arm 2 TQS-floor:** P=0.40, min_n_for_floor=200
- **Arm 3 merge:** W=1 H4 bar, SL=tightest, TP=median, conviction=max
- **Arm 4 multi-position:** K=2, total_risk_cap_per_symbol=1.0%, distinct_agents required
- **Arm 5 order-of-operations:** floor → merge → multi-position → HRP

If the user wants different values, amend this protocol BEFORE tomorrow's run (per `07-research-standards.md` §11 amendment procedure). Silent post-hoc parameter retuning is forbidden.

---

## Cross-references

- `docs/methodology/gate_verdict_registry.md` G6 — the locked-statistic source for this experiment
- `programs/M001_multi_agent_ensemble/06-blue-lock-doctrine.md` §3.1 (Capital Allocator), §3.3 (Aggregator), §3.5 (Sentinel)
- `programs/M001_multi_agent_ensemble/04-quant-foundations.md` F12 (TQS), F17 (ΔInfo), F18 (regime KPIs)
- `programs/M001_multi_agent_ensemble/07-research-standards.md` §11 (verdict-comparator discipline)
- `programs/M001_multi_agent_ensemble/reviews/phi41_squad_v1.md` + addendum — Φ4.1 control baseline
- `programs/M001_multi_agent_ensemble/reviews/isagi_v2_arc.md` — queue-collision diagnostic
- `programs/M001_multi_agent_ensemble/experiments/phi5_aggregator/HRP_NOTES.md` — port notes for Arm 1

---

## Amendment §11.1 — retire §6 stop rule #3 (Sentinel R1-R6 wired, 2026-06-30)

**Filed:** 2026-06-30 (this session).
**Procedure:** `07-research-standards.md` §11 verdict-comparator discipline — this is a stop-rule change, not a locked-statistic change, but the same amendment discipline applies (dated subsection at the bottom of the frozen protocol, dedicated commit, no silent edit of §6).

**What changes.** §6 stop rule #3 originally read:

> "**Sentinel R1-R5 wiring blocker:** if Arm 4 (multi-position) requires Sentinel R1-R5 to be wired (it does — total-risk cap is a Sentinel R-rule), Arm 4 is GATED on Φ4.2 Sentinel implementation. If Sentinel is not wired by the time this experiment runs, Arm 4 is skipped and the report records 'Arm 4 deferred pending Sentinel'."

**Retired.** Sentinel R1-R5 (agent-level) + a new **R6 per-symbol total-risk cap** (Φ5 Arm 4-specific) are wired into the squad-gate harness as of commit `<phase-4-commit-sha>` (2026-06-30). Wiring surface: `sim/scoring/run_phi4_squad_gate.py::_drive_squad_replay(..., sentinel_blocks=False)` — audit-only in the Φ4 / Φ4.1 replay path so the sealed verdicts are unchanged, and physical enforcement in the Φ5 harness via `sentinel_blocks=True`.

**New §6 stop rule #3 (in effect):**

> "**Sentinel enforcement mode.** All Φ5 aggregator arms run with `sentinel_blocks=True`. R1 (min-lot risk floor) and R6 (per-symbol total-risk cap) physically block violating proposals. R3 (over-firing) and R5 (loss-streak dampener) journal to `sentinel_log` but do not block in this experiment — R5's 0.5× risk-scale semantic is out of scope until aggregator-side sizing lands. R2 (discrete sizing) is a no-op in the fixed-lot sim. R4 (agent-level concentration cap) is active only when Arm 1 or Arm 5 supplies `intended_weights_by_agent` (i.e. HRP is on)."

**What did NOT change.** §6 stop rules #1 (25% drawdown → arm FAIL) and #2 (12-hour compute time-box) are unchanged. §4 locked decision rule, §5 experimental design, §3 treatment arm mechanics — all unchanged. §7 file footprint plan gains one new addition (`sim/core/sentinel.py` extended with R6 and `evaluate_proposal` helper; not creating a new aggregator file).

**Empirical justification for retirement.** User decision 2026-06-30 (Q-AGG-1): "no deferrals. implement everything you need to one by one and proceed with writing them accordingly once completed with fully functional works." Interpretation: wire Sentinel R1-R5 as a Φ4.2 mini-sprint before Φ5 starts, per this amendment. This also un-blocks Kunigami v2 (his `warning_active_at` accessor is now consumed by Sentinel's R5 path).

**Registered follow-up.** Once Φ5 verdict lands, if any arm shows Sentinel R6 blocking a material fraction of Arm 4 proposals (>10 %), file a §11.2 amendment to reconsider the 1 % per-symbol cap. Do NOT retune silently — that is exactly the post-hoc discipline `07-research-standards.md` §11 forbids.

**Cross-reference.** Sentinel wiring + integration tests in `sim/core/sentinel.py`, `sim/tests/test_sentinel_wired.py`, `sim/scoring/run_phi4_squad_gate.py::_drive_squad_replay`. Kunigami v2 status transition (DEFERRED → v2-wired) in `reviews/evolution_ledger.md` + `05-agent-roster-v0.md` §3.10 + `06-blue-lock-doctrine.md` §3.11 A10.
