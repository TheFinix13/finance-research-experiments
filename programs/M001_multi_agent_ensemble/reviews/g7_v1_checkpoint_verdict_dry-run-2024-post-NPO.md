# G7 v1 Checkpoint Gate -- Verdict (dry-run-2024-post-NPO)

**Panel:** 2023-01-01 -> 2024-12-31 | OOS: 2024-01-01 -> 2024-12-31
**Symbols:** EURUSD, GBPUSD, USDCAD
**Squad verdict:** FAIL / PARTIAL / PENDING
**Partial reason:** dry-run: criteria 2/3 are stubs pending 8 leave-one-out squads (PROTOCOL sec 8 stop rule #2 -- ~ 32h batch)

## Per-agent 6-bit vectors

| Agent | Playstyle | Tier | Bit vector | v1 pass? |
|---|---|---|---|---|
| isagi_yoichi | conservative_metavision | 1 | `0??100` | no |
| bachira_meguru | rebel_tight | 2 | `1??101` | no |
| itoshi_rin | analytical_precision | 2 | `1??100` | no |
| chigiri_hyoma | speed_momentum | 2 | `1??101` | no |
| reo_mikage | copier_hrp | 2 | `W??W00` | no |
| nagi_seishiro | confluence_only | 2 | `0??100` | no |
| barou_shoei | solo_king | 2 | `0??101` | no |
| kunigami_rensuke | defensive | 2 | `0??000` | no |

Legend: `1` = pass, `0` = fail, `?` = pending (deferred to full-panel batch run), `W` = waived (falsifier exception).

## Per-criterion detail

### isagi_yoichi (conservative_metavision, tier 1)
- C1 (fail): stat=0.2265 threshold=0.3000
    - n_trades: 25
    - mean_tqs: 0.2265
    - median_tqs: 0.0000
    - note_dry_run: single-window dry-run; PROTOCOL sec 3 requires mean_tqs >= 0.30 AND per-window mean >= 0.20 in >= 5/7 windows; full-panel run pending
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (pass): stat=1177.0000 threshold=1.0000
    - publish_count: 9660
    - read_count: 1177
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- C5 (fail): stat=0.0000 threshold=0.1000
    - n_trades: 25
    - mean_lot: 0.1000
    - min_lot: 0.1000
    - max_lot: 0.1000
    - cv: 0.0000
- C6 (fail): stat=0.0534 threshold=0.1000
    - n_trades: 25
    - sl_cv: 0.0534
    - tp1_cv: 0.0534
    - mean_sl: 37.8027
    - mean_tp1: 56.7041

### bachira_meguru (rebel_tight, tier 2)
- C1 (pass): stat=0.3390 threshold=0.3000
    - n_trades: 399
    - mean_tqs: 0.3390
    - median_tqs: 0.0000
    - note_dry_run: single-window dry-run; PROTOCOL sec 3 requires mean_tqs >= 0.30 AND per-window mean >= 0.20 in >= 5/7 windows; full-panel run pending
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (pass): stat=2772.0000 threshold=1.0000
    - publish_count: 9660
    - read_count: 2772
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- C5 (fail): stat=0.0473 threshold=0.1000
    - n_trades: 399
    - mean_lot: 0.0591
    - min_lot: 0.0500
    - max_lot: 0.0600
    - cv: 0.0473
- C6 (pass): stat=0.1788 threshold=0.1000
    - n_trades: 399
    - sl_cv: 0.1788
    - tp1_cv: 0.1788
    - mean_sl: 20.1183
    - mean_tp1: 60.3549

### itoshi_rin (analytical_precision, tier 2)
- C1 (pass): stat=0.5308 threshold=0.3000
    - n_trades: 12
    - mean_tqs: 0.5308
    - median_tqs: 0.0310
    - note_dry_run: single-window dry-run; PROTOCOL sec 3 requires mean_tqs >= 0.30 AND per-window mean >= 0.20 in >= 5/7 windows; full-panel run pending
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (pass): stat=211.0000 threshold=1.0000
    - publish_count: 3221
    - read_count: 211
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- C5 (fail): stat=0.0000 threshold=0.1000
    - n_trades: 12
    - mean_lot: 0.0100
    - min_lot: 0.0100
    - max_lot: 0.0100
    - cv: 0.0000
- C6 (fail): stat=0.0884 threshold=0.1000
    - n_trades: 12
    - sl_cv: 0.0884
    - tp1_cv: 0.0884
    - mean_sl: 29.2200
    - mean_tp1: 58.4400

### chigiri_hyoma (speed_momentum, tier 2)
- C1 (pass): stat=0.3107 threshold=0.3000
    - n_trades: 48
    - mean_tqs: 0.3107
    - median_tqs: 0.0000
    - note_dry_run: single-window dry-run; PROTOCOL sec 3 requires mean_tqs >= 0.30 AND per-window mean >= 0.20 in >= 5/7 windows; full-panel run pending
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (pass): stat=154.0000 threshold=1.0000
    - publish_count: 6440
    - read_count: 154
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- C5 (fail): stat=0.0461 threshold=0.1000
    - n_trades: 48
    - mean_lot: 0.1548
    - min_lot: 0.1500
    - max_lot: 0.1800
    - cv: 0.0461
- C6 (pass): stat=0.1915 threshold=0.1000
    - n_trades: 48
    - sl_cv: 0.1915
    - tp1_cv: 0.1915
    - mean_sl: 32.1481
    - mean_tp1: 96.4442

### reo_mikage (copier_hrp, tier 2)
- C1 (waived): stat=0.0000 threshold=0.0000
    - reason: structural falsifier exception (doctrine sec 3.10); dry-run does not yet count mirror Thoughts -- rerun with workspace-threaded replay for a real verdict
    - agent_id: reo_mikage
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (waived): stat=9660.0000 threshold=1.0000
    - reason: structural falsifier -- publish alone suffices (doctrine sec 3.10 exception)
    - publish_count: 9660
    - read_count: 0
- C5 (fail): stat=0.0000 threshold=0.1000
    - reason: no trades in OOS panel
- C6 (fail): stat=0.0000 threshold=0.1000
    - reason: no trades in OOS panel

### nagi_seishiro (confluence_only, tier 2)
- C1 (fail): stat=0.1056 threshold=0.3000
    - n_trades: 14
    - mean_tqs: 0.1056
    - median_tqs: 0.0000
    - note_dry_run: single-window dry-run; PROTOCOL sec 3 requires mean_tqs >= 0.30 AND per-window mean >= 0.20 in >= 5/7 windows; full-panel run pending
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (pass): stat=135.0000 threshold=1.0000
    - publish_count: 9660
    - read_count: 135
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- C5 (fail): stat=0.0000 threshold=0.1000
    - n_trades: 14
    - mean_lot: 0.0100
    - min_lot: 0.0100
    - max_lot: 0.0100
    - cv: 0.0000
- C6 (fail): stat=0.0000 threshold=0.1000
    - n_trades: 14
    - sl_cv: 0.0000
    - tp1_cv: 0.0000
    - mean_sl: 39.0000
    - mean_tp1: 58.5000

### barou_shoei (solo_king, tier 2)
- C1 (fail): stat=0.2322 threshold=0.3000
    - n_trades: 8
    - mean_tqs: 0.2322
    - median_tqs: 0.0000
    - note_dry_run: single-window dry-run; PROTOCOL sec 3 requires mean_tqs >= 0.30 AND per-window mean >= 0.20 in >= 5/7 windows; full-panel run pending
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (pass): stat=905.0000 threshold=1.0000
    - publish_count: 3220
    - read_count: 905
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- C5 (fail): stat=0.0000 threshold=0.1000
    - n_trades: 8
    - mean_lot: 0.1300
    - min_lot: 0.1300
    - max_lot: 0.1300
    - cv: 0.0000
- C6 (pass): stat=0.1601 threshold=0.1000
    - n_trades: 8
    - sl_cv: 0.1601
    - tp1_cv: 0.1601
    - mean_sl: 33.1250
    - mean_tp1: 49.6875

### kunigami_rensuke (defensive, tier 2)
- C1 (fail): stat=0.0000 threshold=0.3000
    - reason: no trades in OOS panel
    - n_trades: 0
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (fail): stat=0.0000 threshold=1.0000
    - publish_count: 9660
    - read_count: 0
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- C5 (fail): stat=0.0000 threshold=0.1000
    - reason: no trades in OOS panel
- C6 (fail): stat=0.0000 threshold=0.1000
    - reason: no trades in OOS panel

## Amendment log

Any change to the criteria in PROTOCOL sec 3, the pass thresholds, the panel, the statistic, or the file footprint requires a sec 11 amendment. This dry-run output is a scaffold; the formal G7 verdict awaits the full 7-window batch run (see stop rule #2).
