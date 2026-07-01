# G7 v1 Checkpoint Gate -- Verdict (walk-forward-baseline)

**Panel:** 2015-01-01 -> 2025-12-31 | OOS: 2019-01-01 -> 2025-12-31
**Symbols:** EURUSD, GBPUSD, USDCAD
**Squad verdict:** FAIL / PARTIAL / PENDING
**Partial reason:** walk-forward baseline: 7 windows; leave-one-out squads (C2/C3) NOT run in this pass -- separate compute job

## Per-agent 6-bit vectors

| Agent | Playstyle | Tier | Bit vector | v1 pass? |
|---|---|---|---|---|
| isagi_yoichi | conservative_metavision | 1 | `0??000` | no |
| bachira_meguru | rebel_tight | 2 | `1??100` | no |
| itoshi_rin | analytical_precision | 2 | `1??000` | no |
| chigiri_hyoma | speed_momentum | 2 | `0??000` | no |
| reo_mikage | copier_hrp | 2 | `1??100` | no |
| nagi_seishiro | confluence_only | 2 | `1??000` | no |
| barou_shoei | solo_king | 2 | `0??000` | no |
| kunigami_rensuke | defensive | 2 | `0??000` | no |

Legend: `1` = pass, `0` = fail, `?` = pending (deferred to full-panel batch run), `W` = waived (falsifier exception).

## Per-criterion detail

### isagi_yoichi (conservative_metavision, tier 1)
- C1 (fail): stat=0.0000 threshold=0.3000
    - per_window_pass_count: 0
    - per_window_waived_count: 0
    - k_of_n_threshold: 5 of 7
    - mean_statistic_across_computed_windows: 0.0000
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (fail): stat=0.0000 threshold=1.0000
    - per_window_pass_count: 0
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0000
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

### bachira_meguru (rebel_tight, tier 2)
- C1 (pass): stat=0.3750 threshold=0.3000
    - per_window_pass_count: 7
    - per_window_waived_count: 0
    - k_of_n_threshold: 5 of 7
    - mean_statistic_across_computed_windows: 0.3750
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (pass): stat=14551.0000 threshold=1.0000
    - per_window_pass_count: 7
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 14551.0000
- C5 (fail): stat=0.0438 threshold=0.1000
    - per_window_pass_count: 0
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0438
- C6 (fail): stat=0.0000 threshold=0.1000
    - per_window_pass_count: 0
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0000

### itoshi_rin (analytical_precision, tier 2)
- C1 (pass): stat=0.3933 threshold=0.3000
    - per_window_pass_count: 5
    - per_window_waived_count: 0
    - k_of_n_threshold: 5 of 7
    - mean_statistic_across_computed_windows: 0.3933
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (fail): stat=0.0000 threshold=1.0000
    - per_window_pass_count: 0
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0000
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

### chigiri_hyoma (speed_momentum, tier 2)
- C1 (fail): stat=0.2676 threshold=0.3000
    - per_window_pass_count: 3
    - per_window_waived_count: 0
    - k_of_n_threshold: 5 of 7
    - mean_statistic_across_computed_windows: 0.2676
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (fail): stat=0.0000 threshold=1.0000
    - per_window_pass_count: 0
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0000
- C5 (fail): stat=0.0446 threshold=0.1000
    - per_window_pass_count: 0
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0446
- C6 (fail): stat=0.0000 threshold=0.1000
    - per_window_pass_count: 0
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0000

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

### nagi_seishiro (confluence_only, tier 2)
- C1 (pass): stat=0.3848 threshold=0.3000
    - per_window_pass_count: 5
    - per_window_waived_count: 0
    - k_of_n_threshold: 5 of 7
    - mean_statistic_across_computed_windows: 0.3848
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (fail): stat=0.0000 threshold=1.0000
    - per_window_pass_count: 0
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0000
- C5 (fail): stat=0.0500 threshold=0.1000
    - per_window_pass_count: 1
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0500
- C6 (fail): stat=0.0000 threshold=0.1000
    - per_window_pass_count: 0
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0000

### barou_shoei (solo_king, tier 2)
- C1 (fail): stat=0.0000 threshold=0.3000
    - per_window_pass_count: 0
    - per_window_waived_count: 0
    - k_of_n_threshold: 5 of 7
    - mean_statistic_across_computed_windows: 0.0000
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (fail): stat=0.0000 threshold=1.0000
    - per_window_pass_count: 0
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0000
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

### kunigami_rensuke (defensive, tier 2)
- C1 (fail): stat=0.0000 threshold=0.3000
    - per_window_pass_count: 0
    - per_window_waived_count: 0
    - k_of_n_threshold: 5 of 7
    - mean_statistic_across_computed_windows: 0.0000
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (fail): stat=0.0000 threshold=1.0000
    - per_window_pass_count: 0
    - per_window_waived_count: 0
    - k_of_n_threshold: 7 of 7
    - mean_statistic_across_computed_windows: 0.0000
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

## Amendment log

Any change to the criteria in PROTOCOL sec 3, the pass thresholds, the panel, the statistic, or the file footprint requires a sec 11 amendment. This dry-run output is a scaffold; the formal G7 verdict awaits the full 7-window batch run (see stop rule #2).
