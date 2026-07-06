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

---

## Amendment §11.2 — arm package path (`aggregator/` → `aggregator_arms/`, 2026-06-30)

**Filed:** 2026-06-30 (same session as §11.1).
**Procedure:** `07-research-standards.md` §11 — file-footprint plan change. Locked parameters, decision rule, statistic, arm mechanics all unchanged.

**What changes.** §7 file footprint plan originally listed the arm-specific code at `sim/core/aggregator/*.py` inside a NEW package `sim/core/aggregator/`. Python's module system prevents `sim/core/aggregator.py` (the preserved Phi2.5 stub — "DO NOT MODIFY" per §7) and a sibling `sim/core/aggregator/` package from coexisting in the same directory.

**New path.** `sim/core/aggregator_arms/` (package). Mapping:

| §7 planned path | Actual path (post-amendment) |
|---|---|
| `sim/core/aggregator/__init__.py` | `sim/core/aggregator_arms/__init__.py` |
| `sim/core/aggregator/hrp.py` | `sim/core/aggregator_arms/hrp.py` |
| `sim/core/aggregator/tqs_floor.py` | `sim/core/aggregator_arms/tqs_floor.py` |
| `sim/core/aggregator/same_direction_merge.py` | `sim/core/aggregator_arms/same_direction_merge.py` |
| `sim/core/aggregator/multi_position.py` | `sim/core/aggregator_arms/multi_position.py` |
| `sim/core/aggregator/combined.py` | `sim/core/aggregator_arms/combined.py` |

**What did NOT change.** Test filenames (`sim/tests/test_aggregator_arms_*.py`) also renamed to match. `sim/core/aggregator.py` (Phi2.5 stub) preserved unchanged. All locked parameters, all arm mechanics, all sentinel semantics unchanged.

**Empirical justification.** Structural constraint of Python's import system; no scientific implication. The alternative — renaming `sim/core/aggregator.py` — would have counted as a modification to preserved code, which the "DO NOT MODIFY" §7 directive forbids.

**Follow-up.** None. If a future amendment adds a factory (`make_aggregator(arm: str)`), it will live at `sim/core/aggregator_arms/__init__.py::make_aggregator` rather than the originally-planned `sim/core/aggregator/__init__.py::make_aggregator`.

---

## Amendment §11.3 — fixed-lot retired to unknown-playstyle default (2026-07-01, v1/v2 reframe)

**Filed:** 2026-07-01 (v1/v2 reframe session, same-day as doctrine v0.4 → v0.5 and roster v0.7 → v0.8).
**Procedure:** `07-research-standards.md` §11 — parameter-status change (not a threshold change).

**What changes.** The Φ5 PROTOCOL originally treated `FIXED_LOT = 0.10` as a global sizing rule set by the harness. Post-2026-07-01, `FIXED_LOT` is the **`"unknown"`-playstyle default** on `sim/core/lot_intent.py::default_lot_intent`; live v1 agents obtain their lot from `agent.lot_intent(conviction, sl_pips, equity, regime_fit)` which dispatches on `self.playstyle` (doctrine 06 v0.5 §4.1a). The five arms retain their arm-specific mechanics; the only change is that the *input* lot to the aggregator now varies with agent conviction, SL, and regime_fit rather than being a constant.

**What did NOT change.**

- Arm 1 HRP: still weighted-lot mixture over top-K conviction-ranked proposals.
- Arm 2 TQS floor: still conviction-quantile-conditional post-observation filter.
- Arms 3 / 4 / 5: mechanics unchanged; only the per-proposal `lot` input now varies.
- Locked statistic (median-of-window-mean squad TQS) unchanged.
- Decision rule (Δ ≥ 0.020 vs Arm 0 with bootstrap CI lower bound > 0) unchanged.
- Sentinel R1 (min-lot floor 0.01) still applies at intent-evaluation time; any playstyle-dispatched lot < 0.01 gets clamped by Sentinel R1, and any lot > R6's per-symbol cap gets blocked by Sentinel R6 before order placement.

**Empirical justification.** User directive during Phase-6 completion: sizing IS part of the "beautiful goal" (quality of setup + TP + SL + smoothness + speed). A constant lot means agents have no size cognition. Retaining `FIXED_LOT` as a global default would have made criterion #5 of the newly-registered G7 v1-checkpoint gate structurally unpassable — any properly-implemented v1 agent MUST have per-trade lot variation (CV ≥ 0.10 across the OOS panel).

**Downstream effect on Φ5 arm re-sim.** Arm 1 HRP's post-hoc verdict (+0.0019 Δ, essentially null in the fixed-lot harness) was flagged in the partial verdict as requiring variable-lot re-sim. With F19 wired, Arm 1's mechanism has actual dispersion to work with and the re-sim (Phase 6e) will produce a non-null Δ if HRP has any real effect. This is an **honest re-evaluation** under §11 discipline, not a retune: the arm mechanic is unchanged; only the input distribution changed.

**Follow-up.** Phase 6e Φ5 re-sim now depends on G7 v1-checkpoint gate landing first (so the 8 agents have proven v1 status). Ordering: G7 batch → Φ5 arm re-sim.

---

## Amendment §11.4 — Arm 3/4 re-sim wiring, order-of-run, same-environment control, Arm 4 cap scale (2026-07-06)

**Filed:** 2026-07-06, BEFORE any Arm 3/4 re-sim compute ran. All numbers referenced below are from already-sealed verdicts (post-V / post-W); no Arm 3/4 outcome is known at filing time.

### A. What changed since §11.3 that this amendment must absorb

1. **Roster.** Kunigami retired per G7 §11.12 (Role Registry v1 C8 = 0.0). The Φ5 §5 "Agent roster" row (8 agents) is superseded: **7 rostered agents** (isagi, bachira, rin, chigiri, reo, nagi, barou). Kunigami's Sentinel R5 side channel is retained (matches the measured lo1 configuration).
2. **Environment.** The G7-era harness runs with `use_workspace=True` + `sentinel_blocks=True` + F19 variable lots + Barou v1.1 H1 (diagnostic) — a materially different environment from the Φ4.1 fixed-lot, workspace-off control (0.2922). Comparing an Arm 3 re-sim against 0.2922 would conflate the aggregator treatment with environment changes.
3. **Motivating evidence sharpened.** G7 C2/C3 (post-V): Bachira cannibalises Barou by **84.1%** (worst peer reduction). Two agent-level fixes (Phase V-b §11.9, Phase W-barou v1.1 §11.11) produced NULL results with root cause "aggregator single-slot mutex". The binding constraint diagnosis of §2 stands, now with leave-one-out-grade evidence.

### B. Locked control (supersedes Arm 0 for the re-sim family)

**Control = `walk-forward-post-kunigami-retirement`**: the G7 walk-forward harness (`run_g7_v1_checkpoint_gate --mode walk-forward --retire-kunigami`) with the sealed `phi41` aggregator, 7-agent roster, full 2015-2025 panel, 7 OOS windows. Every treatment arm runs the IDENTICAL harness with ONLY `--aggregator-arm` changed. Locked statistic unchanged: **median across OOS windows of per-window mean squad TQS**.

The legacy Φ4.1 control (0.2922) and Isagi-alone (0.3175) are reported as secondary references only.

**Expected control values (declared, not yet run):** near-identical to the lo1_kunigami_rensuke leave-one-out cache (kunigami removal measured as a no-op on every peer). Any material deviation halts the experiment for investigation before arms run.

### C. Locked order-of-run and decision rule

1. **Arm 3 (same-direction merge) FIRST** — it directly targets the same-direction slot collision (52.7% of Isagi rejections were same-direction; Bachira-Barou 84.1% cannibalisation is a same-direction collision).
2. **Arm 4 (multi-position K=2) SECOND** — runs regardless of Arm 3's verdict (both arms' evidence is needed for the Arm 5 stacking decision and for Phase W-barou v1.2 H2).
3. **Arms 1/2 (HRP, TQS-floor)** — post-hoc gates re-run on the control run's `proposals_all.jsonl` (now persisted by the harness cache writer; the post-V cache lacked it). No re-sim needed.
4. **Arm 5 (combined)** — deferred until Arm 3/4 verdicts land; will be its own §11.5 amendment.

**Per-arm acceptance (unchanged from §4, restated against the new control):** arm passes if bootstrap 95% CI lower bound (n=7 window means, 10,000 resamples, Bonferroni α=0.01 across the arms run) exceeds the control's median-of-window-means AND Δ median ≥ 0.020.

**Arm-specific mandatory diagnostics (from §8 pre-mortems):**
- Arm 3: per-agent attributed trade counts + Bachira→Barou cannibalisation ratio recomputed; merged-trade fraction; tightest-SL early-clip effect on mean pips.
- Arm 4: fraction of admissions blocked by R6; concurrent-positions-same-bar-stop event rate (>30% ⇒ structurally redundant with Arm 3).

### D. Arm 4 sandbox risk-cap scale fix (locked pre-run)

§3 Arm 4 locked `total_risk_cap_per_symbol = 1.0%` of equity assuming percent-risk sizing. The sandbox is fixed-lot 0.1 on $100 equity: measured post-V stop distribution (n=5604) is min 6.6 / median 27.5 / max 50.0 pips ⇒ per-position risk $6.6–$50. A 1% ($1) cap blocks EVERY admission including the first — Arm 4 would be null by construction, not by evidence. This is exactly the situation §11.1's registered follow-up anticipated ("if R6 blocks a material fraction of Arm 4 proposals, file an amendment — do NOT retune silently").

**New locked value:** `ARM4_SANDBOX_RISK_CAP_FRAC = 0.50` of equity — the combined risk across a symbol's K positions may not exceed what ONE max-size single position can risk under Sentinel R1 at fixed lot (5% × 10 min-lot units = 50%). This is the faithful sandbox translation of "matches single-position cap; budget is SPLIT across positions, not doubled". Filed BEFORE the Arm 4 re-sim ran; the constant lives at `run_phi4_squad_gate.ARM4_SANDBOX_RISK_CAP_FRAC` with the derivation in-line.

### E. Known semantic notes (declared pre-run)

1. **Arm 3 trade attribution.** Merged trades carry `agent_id = "arm3_merged_<a>+<b>"`, with contributors + per-contributor conviction in rationale and `arm3_winner_agent_id` journalled. TQS hold-hours scoring uses the winner's canon target-hold. Per-agent G7-style slicing will therefore show merged trades under synthetic ids; the squad-level locked statistic is unaffected. Per-agent attribution analysis is post-hoc from rationale.
2. **Arm 3 + Sentinel R3.** The per-agent proposals-today counter counts ORIGINAL proposals at proposal time; a merged proposal's synthetic id has no R3 history, so merged proposals are never R3-blocked. Contributors were each counted individually pre-merge. Declared as harness semantics, not tuned.
3. **Arm 4 same-direction stacks.** Per §3, same-direction concurrent positions are admitted (flagged) in Arm 4 standalone; the correlation-block "count as one" rule applies to the cap check only via combined-risk dollars.

### F. File footprint delta

| Path | Action |
|---|---|
| `sim/scoring/run_phi4_squad_gate.py` | `_drive_squad_replay(aggregator_arm=...)` + Arm 3 merge call + Arm 4 admission/exit bookkeeping + `ARM4_SANDBOX_RISK_CAP_FRAC` |
| `sim/scoring/run_g7_v1_checkpoint_gate.py` | `--retire-kunigami`, `--aggregator-arm`, proposals_all/rejected cache writer |
| `sim/core/aggregator_arms/same_direction_merge.py` | winner tier propagation + `arm3_winner_agent_id` journal |
| `sim/tests/test_aggregator_arm_wiring.py` | NEW (14 tests) |
| `reviews/g7_replay_cache_walk-forward-post-kunigami-retirement/` | control cache (trades + proposals + workspace counts) |
| `reviews/g7_replay_cache_phi5-arm3-*` / `phi5-arm4-*` | treatment caches |
| `scripts/analyze_phi5_resim.py` | NEW — locked-statistic + bootstrap CI + diagnostics from the caches |

---

## Amendment §11.5 — Arm 3/4 re-sim VERDICT (2026-07-06)

**Filed:** 2026-07-06, same session as §11.4, AFTER the pre-registered runs completed. Full numbers: `reviews/phi5_resim_verdict.{md,json}`; commits `7d27ce8` (pre-reg) → `666d87a` (results).

### Locked-statistic verdict: NULL for both arms

Control (`walk-forward-post-kunigami-retirement`, 7 agents, phi41 aggregator): **0.3618** median-of-window-mean squad TQS, 5,604 trades — per-agent byte-identical to post-V and to lo1_kunigami (retirement halt-condition CLEAR; Kunigami's removal is a confirmed no-op on trade outcomes).

| Arm | n trades | median TQS | Δ vs control | CI99 lower | verdict |
|---|---:|---:|---:|---:|---|
| 3 same-direction merge | 5,653 | 0.3617 | −0.0001 | 0.3362 | NULL |
| 4 multi-position K=2 | 7,273 | 0.3643 | +0.0025 | 0.3442 | NULL (positive, ns) |
| 1 HRP (post-hoc) | — | 0.3549 | −0.0069 | — | REGRESS |
| 2 TQS-floor (post-hoc) | — | 0.3643 | +0.0025 | — | NULL (positive, ns) |

Per §4: **no arm is canonised on the locked statistic.** The squad-level TQS is aggregator-invariant on this panel — proposal quality, not slot routing, binds the median-of-window-means.

§6 stop rule #1 (25% DD): the fixed-lot $100 sandbox equity curve breaches 25% DD in EVERY window INCLUDING control (worst window 1.82× control vs 1.45×/1.70× arms) — the rule targets arm-CAUSED risk inflation, which did not occur. Journalled, arms not blamed.

### Mandatory diagnostics: Arm 4 resolves the §11.4 A.3 pathology

The escalation that motivated this re-sim (G7 §11.11) was per-agent slot starvation, not squad TQS. There, Arm 4 is decisive:

| measure | phi41 control | Arm 4 |
|---|---:|---:|
| Barou trades (Bachira present) | 153 @ 0.3469 TQS | **567 @ 0.3944 TQS** (×3.7, quality UP) |
| Barou lo1-Bachira cannibalisation | 961 vs 153 = **+528%** (7-agent measure) | 1,280 vs 567 = **+126%** |
| squad trades | 5,604 | 7,273 (+30%) |
| same-bar-stop rate (§8 pre-mortem, >30% ⇒ redundant with Arm 3) | — | **18.8%** — clears |

Arm 3 diagnostics: 56.5% of trades merged; Barou co-contributes to 1,568 merged trades but his SOLO attribution drops to zero — the merge erases exactly the per-agent identity the Role Registry needs. Arm 3 is the wrong lever for roster health.

### Decision (recommendation, user sign-off required for canonisation)

1. **Do NOT canonise any arm on G6-inherited TQS grounds** — the locked-statistic experiment is honestly NULL and the verdict ladder stays untouched.
2. **Adopt Arm 4 as the default aggregator for the G7-era squad on ROSTER-HEALTH grounds** — a separate, explicitly non-TQS rationale: it collapses the Bachira→Barou starvation from 528% to 126% at zero squad-TQS cost (+0.0025, ns), lifts Barou's own TQS, and gives Rin/Chigiri/Nagi wider live streams. This unblocks Phase W-barou v1.2 H2 (continuation-entry) and future per-agent evolution work that the single-slot mutex was silently nullifying.
3. Arm 5 (stacking) remains deferred: with Arm 3 null-and-attribution-destroying and Arm 1 regressing, the §3 Arm 5 order-of-operations has no evidence-backed components beyond Arm 4 alone.
4. Kunigami Wild Card gate (G7 §11.12) will be designed against the Arm 4 aggregator if adopted.

---

## Amendment §11.6 — Arm 4 ADOPTED + chemistry re-baseline pre-registration (2026-07-06)

**Filed:** 2026-07-06, BEFORE the compute described in part B ran.

### A. Adoption record

User sign-off received 2026-07-06 ("phase 5 is highly needed … proceed in getting it done however is most efficient and effective"). Per §11.5 decision item 2:

1. **Arm 4 (multi-position, K=2, `ARM4_SANDBOX_RISK_CAP_FRAC = 0.50`) is the default aggregator for all G7-era squad work from this date.** Rationale is roster-health (starvation collapse 528%→126% at zero squad-TQS cost), NOT a locked-statistic win — the §11.5 NULL verdicts stand unamended.
2. All sealed artefacts (G6 verdict ladder, phi41-era caches, post-V/post-W walk-forwards, the §11.5 verdict files) are untouched. `_drive_squad_replay` keeps `aggregator_arm="phi41"` as its code default for byte-compatibility with sealed replays; G7-era harness invocations must pass `--aggregator-arm arm4` explicitly.
3. Downstream unblocks: Phase W-barou v1.2 H2 (continuation-entry) and the Kunigami Wild Card drawdown gate (G7 §11.12) are designed against Arm 4.

### B. Pre-registration: leave-one-out chemistry re-baseline under Arm 4

The Phase-3 C2/C3 + Role Registry verdicts (G7 §11.11) were measured under the phi41 single-slot aggregator — the same mutex the adoption removes. The chemistry numbers driving roster decisions (Bachira→Barou −84%, Nagi's incoming lift, etc.) are therefore stale under the adopted aggregator and must be re-measured before any further roster/evolution decision cites them.

**Locked before compute:**

- **Runs:** 7 leave-one-out replays, one per active-roster agent (isagi, bachira, rin, chigiri, reo, nagi, barou). Kunigami retired per Role Registry v1 §12.1 — roster excludes him as proposer; instance stays wired for Sentinel R5.
- **Config:** `run_g7_leave_one_out --aggregator-arm arm4 --retire-kunigami --tag phi5-arm4`, panel/env identical to §11.4 (same bars, sentinel_blocks, workspace, shadow ledger). Baseline = `g7_replay_cache_phi5-arm4-post-kunigami` (the §11.5 Arm 4 walk-forward, 7,273 trades @ 0.3643).
- **Execution:** 7 independent single-`--exclude` processes in parallel with `--no-aggregate` (replay is deterministic per process; parallelism cannot change results), then one `--aggregate-only` pass. Heartbeat monitor on all PIDs.
- **This is a MEASUREMENT, not a gate.** C2/C3/C7/C8/C9 definitions and thresholds inherited verbatim from G7 v1 §11.1 + Role Registry v1 §3. No roster change auto-triggers from these numbers; any retention/evolution decision citing them requires its own amendment. Expected (not required) outcome: Barou's lo1-Bachira cannibalisation ≈ +126% (matches the §11.5 diagnostic, which this batch supersedes for verdict purposes — the earlier one-off `run_arm4_lo1_bachira.py` cache used a non-canonical path).
- **Outputs:** `reviews/g7_leave_one_out_verdict_phi5-arm4.{md,json}`, `reviews/g7_role_registry_verdict_phi5-arm4.{md,json}`, caches under `reviews/g7_leave_one_out_phi5-arm4/lo1_<agent>/`.

---

## Amendment §11.7 — Arm 4 chemistry re-baseline RESULTS (2026-07-06)

**Filed:** 2026-07-06, after the §11.6 B pre-registered batch completed (7 parallel lo1 replays, 37–42 min each, heartbeat monitor clean exit, zero stalls). Verdict files: `reviews/g7_leave_one_out_verdict_phi5-arm4.{md,json}`, `reviews/g7_role_registry_verdict_phi5-arm4.{md,json}`.

### Headline vs the phi41-era Phase-3 verdict (G7 §11.11)

1. **Bachira→Barou cannibalisation: 84% → 55.7%** (Barou 567 with Bachira present vs 1,280 absent — matches the §11.5 one-off diagnostic exactly, confirming determinism). Still a **C3 FAIL** (threshold 50%), but the margin collapsed from 34 points over threshold to 5.7. The residual overlap is now an agent-level problem — exactly what Phase W-barou v1.2 H2 (continuation-entry) is scoped to attack, and Arm 4 has removed the aggregator confound that was silently nullifying agent-level fixes.
2. **Nagi's finisher role is CONFIRMED under Arm 4**: C7 passes with 3 lifting peers (Bachira +0.1806, Rin +0.0624, Reo +0.0504 TQS) — the §11.11 role-aware retention transfers intact to the adopted aggregator. Retained via C7+C8.
3. **All six other active agents retained**; Rin/Chigiri regain healthy volume (436/437 trades, 6.0% share each vs starvation under phi41). Barou passes C9 at 7.8% share (was starved to ~2.7% under phi41).
4. **Kunigami rows are measurement artefacts**: he is retired (Role Registry v1 §12.1), has no lo1 cache by design, and the emitter's "retirement_candidate / squad FAIL" line simply re-confirms the already-executed retirement. No new action.

### Consequences (per §11.6 B: measurement, not gate — no auto roster change)

- Bachira is NOT removed: he holds 48.8% of squad trades, is Nagi's primary lifter (+0.1806), and passes C2/C8/C9. The C3 residual is routed to **Phase W-barou v1.2** (Barou continuation-entry under Arm 4) as the next pre-registered experiment; its success criterion should target the 55.7% reduction dropping below the 50% C3 threshold.
- The `phi5-arm4` verdict files are now the CANONICAL chemistry baseline for all G7-era roster/evolution decisions; the `post-V` (phi41) verdicts remain sealed as the Phase-3 record.

