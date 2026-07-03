# G7 v1 Checkpoint Gate -- Verdict (walk-forward-post-V)

**Panel:** 2015-01-01 -> 2025-12-31 | OOS: 2019-01-01 -> 2025-12-31
**Symbols:** EURUSD, GBPUSD, USDCAD
**Squad verdict:** FAIL / PARTIAL / PENDING
**Partial reason:** walk-forward baseline: 7 windows; leave-one-out squads (C2/C3) NOT run in this pass -- separate compute job

## Per-agent 6-bit vectors

| Agent | Playstyle | Tier | Bit vector | v1 pass? |
|---|---|---|---|---|
| isagi_yoichi | conservative_metavision | 1 | `1??100` | no |
| bachira_meguru | rebel_tight | 2 | `1??100` | no |
| itoshi_rin | analytical_precision | 2 | `1??100` | no |
| chigiri_hyoma | speed_momentum | 2 | `0??100` | no |
| reo_mikage | copier_hrp | 2 | `1??111` | no |
| nagi_seishiro | confluence_only | 2 | `1??100` | no |
| barou_shoei | solo_king | 2 | `1??100` | no |
| kunigami_rensuke | defensive | 2 | `1??111` | no |

Legend: `1` = pass, `0` = fail, `?` = pending (deferred to full-panel batch run), `W` = waived (falsifier exception).

## Per-criterion detail

### isagi_yoichi (conservative_metavision, tier 1)
- C1 (pass): stat=0.3555 threshold=0.3000
    - per_window_pass_count: 7
    - per_window_waived_count: 0
    - k_of_n_threshold: 5 of 7
    - mean_statistic_across_computed_windows: 0.3555
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (pass): stat=6571.0000 threshold=1.0000
    - per_window_pass_count: 7
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 6571.0000
- C5 (fail): stat=0.0736 threshold=0.1000
    - per_window_pass_count: 0
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0736
- C6 (fail): stat=0.0685 threshold=0.1000
    - per_window_pass_count: 0
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0685

### bachira_meguru (rebel_tight, tier 2)
- C1 (pass): stat=0.3849 threshold=0.3000
    - per_window_pass_count: 7
    - per_window_waived_count: 0
    - k_of_n_threshold: 5 of 7
    - mean_statistic_across_computed_windows: 0.3849
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (pass): stat=14551.0000 threshold=1.0000
    - per_window_pass_count: 7
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 14551.0000
- C5 (fail): stat=0.0850 threshold=0.1000
    - per_window_pass_count: 2
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0850
- C6 (fail): stat=0.1348 threshold=0.1000
    - per_window_pass_count: 6
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.1348

### itoshi_rin (analytical_precision, tier 2)
- C1 (pass): stat=0.3708 threshold=0.3000
    - per_window_pass_count: 6
    - per_window_waived_count: 0
    - k_of_n_threshold: 5 of 7
    - mean_statistic_across_computed_windows: 0.3708
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (pass): stat=2988.0000 threshold=1.0000
    - per_window_pass_count: 7
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 2988.0000
- C5 (fail): stat=0.0931 threshold=0.1000
    - per_window_pass_count: 2
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0931
- C6 (fail): stat=0.0911 threshold=0.1000
    - per_window_pass_count: 2
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0911

### chigiri_hyoma (speed_momentum, tier 2)
- C1 (fail): stat=0.2706 threshold=0.3000
    - per_window_pass_count: 3
    - per_window_waived_count: 0
    - k_of_n_threshold: 5 of 7
    - mean_statistic_across_computed_windows: 0.2706
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (pass): stat=992.0000 threshold=1.0000
    - per_window_pass_count: 7
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 992.0000
- C5 (fail): stat=0.0959 threshold=0.1000
    - per_window_pass_count: 3
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0959
- C6 (fail): stat=0.1567 threshold=0.1000
    - per_window_pass_count: 6
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.1567

### reo_mikage (copier_hrp, tier 2)
- C1 (pass): stat=0.0000 threshold=0.3000
    - per_window_pass_count: 0
    - per_window_waived_count: 7
    - k_of_n_threshold: 5 of 7
    - mean_statistic_across_computed_windows: 0.0000
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (pass): stat=0.0000 threshold=1.0000
    - per_window_pass_count: 0
    - per_window_waived_count: 7
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0000
- C5 (pass): stat=0.0000 threshold=0.1000
    - per_window_pass_count: 0
    - per_window_waived_count: 7
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0000
- C6 (pass): stat=0.0000 threshold=0.1000
    - per_window_pass_count: 0
    - per_window_waived_count: 7
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0000

### nagi_seishiro (confluence_only, tier 2)
- C1 (pass): stat=0.3810 threshold=0.3000
    - per_window_pass_count: 5
    - per_window_waived_count: 0
    - k_of_n_threshold: 5 of 7
    - mean_statistic_across_computed_windows: 0.3810
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (pass): stat=658.0000 threshold=1.0000
    - per_window_pass_count: 7
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 658.0000
- C5 (fail): stat=0.0000 threshold=0.1000
    - per_window_pass_count: 0
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0000
- C6 (fail): stat=0.0000 threshold=0.1000
    - per_window_pass_count: 0
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0000

### barou_shoei (solo_king, tier 2)
- C1 (pass): stat=0.2990 threshold=0.3000
    - per_window_pass_count: 5
    - per_window_waived_count: 0
    - k_of_n_threshold: 5 of 7
    - mean_statistic_across_computed_windows: 0.2990
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (pass): stat=4576.0000 threshold=1.0000
    - per_window_pass_count: 7
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 4576.0000
- C5 (fail): stat=0.0491 threshold=0.1000
    - per_window_pass_count: 0
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0491
- C6 (fail): stat=0.1171 threshold=0.1000
    - per_window_pass_count: 4
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.1171

### kunigami_rensuke (defensive, tier 2)
- C1 (pass): stat=0.0000 threshold=0.3000
    - per_window_pass_count: 0
    - per_window_waived_count: 7
    - k_of_n_threshold: 5 of 7
    - mean_statistic_across_computed_windows: 0.0000
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (pass): stat=0.0000 threshold=1.0000
    - per_window_pass_count: 0
    - per_window_waived_count: 7
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0000
- C5 (pass): stat=0.0000 threshold=0.1000
    - per_window_pass_count: 0
    - per_window_waived_count: 7
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0000
- C6 (pass): stat=0.0000 threshold=0.1000
    - per_window_pass_count: 0
    - per_window_waived_count: 7
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0000

## Amendment log

Any change to the criteria in PROTOCOL sec 3, the pass thresholds, the panel, the statistic, or the file footprint requires a sec 11 amendment. This dry-run output is a scaffold; the formal G7 verdict awaits the full 7-window batch run (see stop rule #2).


## Phase U -- Shadow ledger (DIAGNOSTIC ONLY)

Per-agent counterfactual scouting record. Each row is what the agent's proposals would have produced if run in isolation on their symbol -- **not** what actually executed. Shadow-TQS is systematically over-optimistic (no inter-symbol R6 competition, no aggregator tie-break, no per-symbol single-position rule), so the alpha-attribution signal is the **accepted-vs-rejected TQS delta** for the same agent, not the raw shadow-TQS value. See G7 PROTOCOL §11.7 amendment.

| Agent | N shadow | Wins | Shadow-TQS | Shadow R | Win rate | Window CV | TQS accepted | TQS rejected | Delta (rej-acc) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `isagi_yoichi` | 6571 | 3056 | 0.301 | +0.152 | 0.465 | 0.076 | 0.300 | 0.305 | +0.005 |
| `bachira_meguru` | 14551 | 7233 | 0.314 | +0.224 | 0.497 | 0.047 | 0.320 | 0.307 | -0.013 |
| `itoshi_rin` | 1494 | 532 | 0.286 | +0.136 | 0.356 | 0.253 | 0.338 | 0.191 | -0.147 |
| `chigiri_hyoma` | 992 | 397 | 0.250 | -0.025 | 0.400 | 0.208 | 0.241 | 0.292 | +0.051 |
| `nagi_seishiro` | 658 | 301 | 0.300 | +0.237 | 0.457 | 0.253 | 0.300 | n/a | n/a |
| `barou_shoei` | 4576 | 2198 | 0.316 | +0.179 | 0.480 | 0.058 | 0.302 | 0.317 | +0.015 |

**Reading this table.** For each agent, the ``Delta (rej-acc)`` column is the routing-quality signal:

- **Delta strongly negative** (e.g. -0.10 or worse) -> the aggregator is picking real winners and rejecting real losers. The agent's crowding-out is a design feature, not a bug.
- **Delta ~ 0** -> the aggregator's tie-break is picking at random with respect to trade quality. The agent's alpha is real but routed away; consider Phase T-style peer-disagreement or regime-specialist role.
- **Delta strongly positive** -> the aggregator is picking the wrong winners. Rejected proposals were actually the better trades. This would be a routing bug, not a design decision.

**Reproducibility check.** Window CV > 0.30 flags an agent whose shadow alpha only shows up in specific windows -- regime-conditional, not stable.
