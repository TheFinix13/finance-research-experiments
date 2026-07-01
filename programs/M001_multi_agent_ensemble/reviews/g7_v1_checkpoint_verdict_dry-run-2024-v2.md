# G7 v1 Checkpoint Gate -- Verdict (dry-run-2024-v2)

**Panel:** 2023-01-01 -> 2024-12-31 | OOS: 2024-01-01 -> 2024-12-31
**Symbols:** EURUSD, GBPUSD, USDCAD
**Squad verdict:** FAIL / PARTIAL / PENDING
**Partial reason:** dry-run: criteria 2/3 are stubs pending 8 leave-one-out squads (PROTOCOL sec 8 stop rule #2 -- ~ 32h batch)

## Per-agent 6-bit vectors

| Agent | Playstyle | Tier | Bit vector | v1 pass? |
|---|---|---|---|---|
| isagi_yoichi | conservative_metavision | 1 | `0??000` | no |
| bachira_meguru | rebel_tight | 2 | `1??100` | no |
| itoshi_rin | analytical_precision | 2 | `1??000` | no |
| chigiri_hyoma | speed_momentum | 2 | `1??000` | no |
| reo_mikage | copier_hrp | 2 | `W??W00` | no |
| nagi_seishiro | confluence_only | 2 | `0??000` | no |
| barou_shoei | solo_king | 2 | `0??000` | no |
| kunigami_rensuke | defensive | 2 | `0??000` | no |

Legend: `1` = pass, `0` = fail, `?` = pending (deferred to full-panel batch run), `W` = waived (falsifier exception).

## Per-criterion detail

### isagi_yoichi (conservative_metavision, tier 1)
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

### bachira_meguru (rebel_tight, tier 2)
- C1 (pass): stat=0.3335 threshold=0.3000
    - n_trades: 398
    - mean_tqs: 0.3335
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
- C5 (fail): stat=0.0544 threshold=0.1000
    - n_trades: 398
    - mean_lot: 0.0588
    - min_lot: 0.0500
    - max_lot: 0.0600
    - cv: 0.0544
- C6 (fail): stat=0.0000 threshold=0.1000
    - n_trades: 398
    - sl_cv: 0.0000
    - tp1_cv: 0.0000
    - mean_sl: 24.0000
    - mean_tp1: 72.0000

### itoshi_rin (analytical_precision, tier 2)
- C1 (pass): stat=0.3538 threshold=0.3000
    - n_trades: 18
    - mean_tqs: 0.3538
    - median_tqs: 0.0000
    - note_dry_run: single-window dry-run; PROTOCOL sec 3 requires mean_tqs >= 0.30 AND per-window mean >= 0.20 in >= 5/7 windows; full-panel run pending
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (fail): stat=0.0000 threshold=1.0000
    - publish_count: 3221
    - read_count: 0
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- C5 (fail): stat=0.0000 threshold=0.1000
    - n_trades: 18
    - mean_lot: 0.0100
    - min_lot: 0.0100
    - max_lot: 0.0100
    - cv: 0.0000
- C6 (fail): stat=0.0000 threshold=0.1000
    - n_trades: 18
    - sl_cv: 0.0000
    - tp1_cv: 0.0000
    - mean_sl: 18.0000
    - mean_tp1: 36.0000

### chigiri_hyoma (speed_momentum, tier 2)
- C1 (pass): stat=0.3099 threshold=0.3000
    - n_trades: 44
    - mean_tqs: 0.3099
    - median_tqs: 0.0000
    - note_dry_run: single-window dry-run; PROTOCOL sec 3 requires mean_tqs >= 0.30 AND per-window mean >= 0.20 in >= 5/7 windows; full-panel run pending
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (fail): stat=0.0000 threshold=1.0000
    - publish_count: 6440
    - read_count: 0
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- C5 (fail): stat=0.0472 threshold=0.1000
    - n_trades: 44
    - mean_lot: 0.1550
    - min_lot: 0.1500
    - max_lot: 0.1800
    - cv: 0.0472
- C6 (fail): stat=0.0000 threshold=0.1000
    - n_trades: 44
    - sl_cv: 0.0000
    - tp1_cv: 0.0000
    - mean_sl: 36.0000
    - mean_tp1: 108.0000

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
- C4 (fail): stat=0.0000 threshold=1.0000
    - publish_count: 9660
    - read_count: 0
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
- C1 (fail): stat=0.0000 threshold=0.3000
    - reason: no trades in OOS panel
    - n_trades: 0
- C2 (pending): stat=0.0000 threshold=0.0000
    - reason: leave-one-out chemistry requires 8 additional replays with each agent removed; deferred to batch run (PROTOCOL sec 8 stop rule #2 wall-clock ~ 32 hours)
- C3 (pending): stat=0.0000 threshold=0.5000
    - reason: non-cannibalising slot behaviour requires per-peer leave-one-out trade-count deltas; shares the batch run with criterion 2
- C4 (fail): stat=0.0000 threshold=1.0000
    - publish_count: 3220
    - read_count: 0
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- C5 (fail): stat=0.0000 threshold=0.1000
    - reason: no trades in OOS panel
- C6 (fail): stat=0.0000 threshold=0.1000
    - reason: no trades in OOS panel

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
