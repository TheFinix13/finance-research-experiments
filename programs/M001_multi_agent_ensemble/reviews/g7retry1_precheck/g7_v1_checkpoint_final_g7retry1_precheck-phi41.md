# G7 v1 Checkpoint Gate -- FINAL verdict (g7retry1_precheck-phi41)

**Squad verdict: FAIL** (3/7 agents pass all six criteria)

- Aggregator arm: `phi41`
- Baseline cache: `/Users/the1finix/Documents/GitHub/finance-research-experiments/programs/M001_multi_agent_ensemble/reviews/g7_replay_cache_walk-forward-post-kunigami-retirement`
- Leave-one-out caches: `/Users/the1finix/Documents/GitHub/finance-research-experiments/programs/M001_multi_agent_ensemble/reviews/g7_leave_one_out_post-V/lo1_*`
- Bootstrap: n=10000, seed=42, percentile CI, alpha=0.05
- Windows: 7 rolling OOS (2019..2025)

## Per-agent 6-bit vectors

| Agent | Playstyle | Bit vector | C1 | C2 | C3 | C4 | C5 | C6 | v1 pass? |
|---|---|---|---|---|---|---|---|---|---|
| `isagi_yoichi` | conservative_metavision | `111111` | ✅ 0.356 | ✅ 62.000 | ✅ 7.000 | ✅ 6571.000 | ✅ 0.205 | ✅ 0.178 | YES |
| `bachira_meguru` | rebel_tight | `110111` | ✅ 0.385 | ✅ 0.098 | ❌ 0.000 | ✅ 14551.000 | ✅ 0.476 | ✅ 0.154 | no |
| `itoshi_rin` | analytical_precision | `111111` | ✅ 0.375 | ✅ 0.178 | ✅ 7.000 | ✅ 2988.000 | ✅ 0.112 | ✅ 0.221 | YES |
| `chigiri_hyoma` | speed_momentum | `001111` | ❌ 0.267 | ❌ 0.000 | ✅ 7.000 | ✅ 992.000 | ✅ 0.105 | ✅ 0.176 | no |
| `reo_mikage` | copier_hrp | `W11WWW` | W | ✅ 0.002 | ✅ 6.000 | W | W | W | YES |
| `nagi_seishiro` | confluence_only | `101110` | ✅ 0.436 | ❌ 0.000 | ✅ 7.000 | ✅ 658.000 | ✅ 0.259 | ❌ 0.000 | no |
| `barou_shoei` | solo_king | `001111` | ❌ 0.347 | ❌ 0.000 | ✅ 7.000 | ✅ 4576.000 | ✅ 0.254 | ✅ 0.154 | no |

Legend: `1` pass / `0` fail / `W` waived (structural falsifier, sec 11.1) / `?` pending. Cell numbers are the criterion statistic (C1 mean TQS; C2 strongest qualifying delta; C3 clean windows; C4 min(publish, read); C5/C6 CV).

## Notes

- All statistics OOS-only (union of the 7 rolling OOS windows); differs from the diagnostic lo1 verdicts which pooled IS+OOS.
- C4 evaluated on panel-wide publish/read counters (per-window counts not persisted in caches; documented harness limitation).
- C5/C6 recomputed from cached source_* trade fields via the pure playstyle-dispatched F19/F20 primitives (no agent overrides exist).

## Per-criterion evidence

### isagi_yoichi
- **C1** (pass): stat=0.3557 threshold=0.3000
    - n_trades: 1004
    - mean_tqs: 0.3557
    - windows_passing_0.20: 7
    - windows_required: 5
    - per_window_means: {'0': 0.372, '1': 0.3534, '2': 0.3234, '3': 0.3539, '4': 0.3806, '5': 0.3473, '6': 0.3582}
    - bootstrap_ci95: [0.3316, 0.3798]
    - ci_lower_floor: 0.2500
- **C2** (pass): stat=62.0000 threshold=0.0000
    - qualifying_peers: ['barou_shoei']
    - bachira_meguru: dTQS=0.00649 CI=[-0.01915, 0.03304] (qual=False) | dTrades=-955 CI=[-149.143, -122.143] (qual=False)
    - itoshi_rin: dTQS=0.0 CI=[-0.11425, 0.11638] (qual=False) | dTrades=+0 CI=[-0.429, 0.429] (qual=False)
    - chigiri_hyoma: dTQS=0.00786 CI=[-0.05407, 0.07081] (qual=False) | dTrades=-26 CI=[-4.571, -2.857] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=0.0035 CI=[-0.18481, 0.18692] (qual=False) | dTrades=-1 CI=[-0.429, 0.0] (qual=False)
    - barou_shoei: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+62 CI=[6.143, 11.714] (qual=True)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.41, w1:0.43, w2:0.35, w3:0.39, w4:0.43, w5:0.39, w6:0.41 ('!' = dirty window)
- **C4** (pass): stat=6571.0000 threshold=1.0000
    - publish_count: 53164
    - read_count: 6571
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.2045 threshold=0.1000
    - n_trades: 1004
    - mean_lot: 0.1740
    - min_lot: 0.0900
    - max_lot: 0.2000
    - cv: 0.2045
- **C6** (pass): stat=0.1781 threshold=0.1000
    - n_trades: 1004
    - sl_cv: 0.1781
    - tp1_cv: 0.1781
    - mean_sl: 42.2727
    - mean_tp1: 63.4091

### bachira_meguru
- **C1** (pass): stat=0.3853 threshold=0.3000
    - n_trades: 1444
    - mean_tqs: 0.3853
    - windows_passing_0.20: 7
    - windows_required: 5
    - per_window_means: {'0': 0.3562, '1': 0.3609, '2': 0.3634, '3': 0.4329, '4': 0.41, '5': 0.3733, '6': 0.3974}
    - bootstrap_ci95: [0.3647, 0.4058]
    - ci_lower_floor: 0.2500
- **C2** (pass): stat=0.0980 threshold=0.0000
    - qualifying_peers: ['nagi_seishiro']
    - isagi_yoichi: dTQS=0.00202 CI=[-0.03166, 0.03593] (qual=False) | dTrades=-46 CI=[-10.143, -3.571] (qual=False)
    - itoshi_rin: dTQS=-0.03408 CI=[-0.14569, 0.07709] (qual=False) | dTrades=-30 CI=[-7.571, -1.857] (qual=False)
    - chigiri_hyoma: dTQS=0.00328 CI=[-0.05885, 0.06578] (qual=False) | dTrades=-19 CI=[-3.571, -1.857] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=0.098 CI=[-0.14804, 0.32389] (qual=False) | dTrades=+45 CI=[4.429, 8.714] (qual=True)
    - barou_shoei: dTQS=-0.03788 CI=[-0.14127, 0.0678] (qual=False) | dTrades=-487 CI=[-81.429, -58.714] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (fail): stat=0.0000 threshold=4.0000
    - clean_windows: 0
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.92!, w1:0.76!, w2:0.97!, w3:0.89!, w4:0.81!, w5:0.90!, w6:0.89! ('!' = dirty window)
- **C4** (pass): stat=14551.0000 threshold=1.0000
    - publish_count: 53164
    - read_count: 14551
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.4757 threshold=0.1000
    - n_trades: 1444
    - mean_lot: 0.0500
    - min_lot: 0.0200
    - max_lot: 0.1100
    - cv: 0.4757
- **C6** (pass): stat=0.1545 threshold=0.1000
    - n_trades: 1444
    - sl_cv: 0.1545
    - tp1_cv: 0.1545
    - mean_sl: 22.3195
    - mean_tp1: 66.9586

### itoshi_rin
- **C1** (pass): stat=0.3750 threshold=0.3000
    - n_trades: 202
    - mean_tqs: 0.3750
    - windows_passing_0.20: 7
    - windows_required: 5
    - per_window_means: {'0': 0.4232, '1': 0.3952, '2': 0.2471, '3': 0.4168, '4': 0.3359, '5': 0.3955, '6': 0.3818}
    - bootstrap_ci95: [0.296, 0.4579]
    - ci_lower_floor: 0.2500
- **C2** (pass): stat=0.1776 threshold=0.0000
    - qualifying_peers: ['nagi_seishiro']
    - isagi_yoichi: dTQS=-0.00232 CI=[-0.03479, 0.02982] (qual=False) | dTrades=-243 CI=[-53.857, -22.429] (qual=False)
    - bachira_meguru: dTQS=0.00132 CI=[-0.02787, 0.03078] (qual=False) | dTrades=-50 CI=[-10.571, -4.143] (qual=False)
    - chigiri_hyoma: dTQS=-0.00051 CI=[-0.06416, 0.06379] (qual=False) | dTrades=-12 CI=[-2.286, -1.286] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=0.17762 CI=[-0.02237, 0.3729] (qual=False) | dTrades=+42 CI=[2.857, 9.714] (qual=True)
    - barou_shoei: dTQS=0.0 CI=[-0.14132, 0.13687] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.10, w1:0.18, w2:0.16, w3:0.34, w4:0.16, w5:0.16, w6:0.19 ('!' = dirty window)
- **C4** (pass): stat=2988.0000 threshold=1.0000
    - publish_count: 17723
    - read_count: 2988
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.1124 threshold=0.1000
    - n_trades: 202
    - mean_lot: 0.0882
    - min_lot: 0.0700
    - max_lot: 0.1100
    - cv: 0.1124
- **C6** (pass): stat=0.2215 threshold=0.1000
    - n_trades: 202
    - sl_cv: 0.2215
    - tp1_cv: 0.2215
    - mean_sl: 29.7576
    - mean_tp1: 59.5152

### chigiri_hyoma
- **C1** (fail): stat=0.2672 threshold=0.3000
    - n_trades: 296
    - mean_tqs: 0.2672
    - windows_passing_0.20: 6
    - windows_required: 5
    - per_window_means: {'0': 0.1866, '1': 0.3351, '2': 0.2408, '3': 0.3391, '4': 0.2189, '5': 0.3101, '6': 0.2636}
    - bootstrap_ci95: [0.2226, 0.3127]
    - ci_lower_floor: 0.2500
- **C2** (fail): stat=0.0000 threshold=0.0000
    - qualifying_peers: []
    - isagi_yoichi: dTQS=-0.00299 CI=[-0.03612, 0.03102] (qual=False) | dTrades=-36 CI=[-6.714, -3.571] (qual=False)
    - bachira_meguru: dTQS=0.00244 CI=[-0.02638, 0.03193] (qual=False) | dTrades=-72 CI=[-15.143, -6.429] (qual=False)
    - itoshi_rin: dTQS=-0.00652 CI=[-0.12243, 0.10858] (qual=False) | dTrades=-6 CI=[-1.857, 0.0] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=-0.00543 CI=[-0.19093, 0.17683] (qual=False) | dTrades=+1 CI=[-0.857, 1.143] (qual=False)
    - barou_shoei: dTQS=0.0 CI=[-0.14132, 0.13687] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.25, w1:0.07, w2:0.04, w3:0.03, w4:0.10, w5:0.04, w6:0.09 ('!' = dirty window)
- **C4** (pass): stat=992.0000 threshold=1.0000
    - publish_count: 35442
    - read_count: 992
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.1053 threshold=0.1000
    - n_trades: 296
    - mean_lot: 0.1570
    - min_lot: 0.1200
    - max_lot: 0.1900
    - cv: 0.1053
- **C6** (pass): stat=0.1761 threshold=0.1000
    - n_trades: 296
    - sl_cv: 0.1761
    - tp1_cv: 0.1761
    - mean_sl: 34.6889
    - mean_tp1: 104.0667

### reo_mikage
- **C1** (waived): stat=53164.0000 threshold=0.0000
    - reason: structural falsifier waiver (sec 11.1) -- intend() returns None by design; earns v1 through publishing
    - publish_count: 53164
- **C2** (pass): stat=0.0022 threshold=0.0000
    - qualifying_peers: ['itoshi_rin']
    - isagi_yoichi: dTQS=0.00108 CI=[-0.03267, 0.03478] (qual=False) | dTrades=+5 CI=[-0.714, 2.143] (qual=False)
    - bachira_meguru: dTQS=0.00093 CI=[-0.0278, 0.03004] (qual=False) | dTrades=-2 CI=[-3.571, 2.857] (qual=False)
    - itoshi_rin: dTQS=0.00217 CI=[-0.1161, 0.12134] (qual=False) | dTrades=+24 CI=[0.857, 7.143] (qual=True)
    - chigiri_hyoma: dTQS=0.00107 CI=[-0.06274, 0.06585] (qual=False) | dTrades=+8 CI=[-0.143, 2.429] (qual=False)
    - nagi_seishiro: dTQS=0.05911 CI=[-0.09899, 0.21945] (qual=False) | dTrades=-63 CI=[-21.286, -1.425] (qual=False)
    - barou_shoei: dTQS=0.00439 CI=[-0.13317, 0.14246] (qual=False) | dTrades=+1 CI=[0.0, 0.429] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=6.0000 threshold=4.0000
    - clean_windows: 6
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.02, w1:0.19, w2:0.40, w3:0.72!, w4:0.33, w5:0.38, w6:0.41 ('!' = dirty window)
- **C4** (waived): stat=53164.0000 threshold=1.0000
    - reason: structural falsifier -- publish alone suffices (doctrine sec 3.10 exception)
    - publish_count: 53164
    - read_count: 0
- **C5** (waived): stat=0.0000 threshold=0.1000
    - reason: structural falsifier waived on C5 -- agent's intend() returns None by design (doctrine sec 3.10 / 3.11); no trade-side lot dispersion measurable
    - agent_id: reo_mikage
- **C6** (waived): stat=0.0000 threshold=0.1000
    - reason: structural falsifier waived on C6 -- agent's intend() returns None by design (doctrine sec 3.10 / 3.11); no trade-side risk-shape dispersion measurable
    - agent_id: reo_mikage

### nagi_seishiro
- **C1** (pass): stat=0.4363 threshold=0.3000
    - n_trades: 67
    - mean_tqs: 0.4363
    - windows_passing_0.20: 5
    - windows_required: 5
    - per_window_means: {'0': 0.119, '1': 0.3839, '2': 0.3102, '3': 0.5632, '4': 0.6031, '5': 0.1624, '6': 0.5251}
    - bootstrap_ci95: [0.3076, 0.5714]
    - ci_lower_floor: 0.2500
- **C2** (fail): stat=0.0000 threshold=0.0000
    - qualifying_peers: []
    - isagi_yoichi: dTQS=9e-05 CI=[-0.03336, 0.03467] (qual=False) | dTrades=-5 CI=[-1.286, -0.286] (qual=False)
    - bachira_meguru: dTQS=0.0012 CI=[-0.02809, 0.03089] (qual=False) | dTrades=-12 CI=[-2.714, -0.857] (qual=False)
    - itoshi_rin: dTQS=-0.01346 CI=[-0.12562, 0.10228] (qual=False) | dTrades=-10 CI=[-3.143, -0.286] (qual=False)
    - chigiri_hyoma: dTQS=0.00152 CI=[-0.06258, 0.06371] (qual=False) | dTrades=-5 CI=[-1.286, -0.286] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - barou_shoei: dTQS=0.00439 CI=[-0.13317, 0.14246] (qual=False) | dTrades=+1 CI=[0.0, 0.429] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.02, w1:0.07, w2:0.04, w3:0.08, w4:0.05, w5:0.06, w6:0.01 ('!' = dirty window)
- **C4** (pass): stat=658.0000 threshold=1.0000
    - publish_count: 53164
    - read_count: 658
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.2587 threshold=0.1000
    - n_trades: 67
    - mean_lot: 0.1609
    - min_lot: 0.0800
    - max_lot: 0.2000
    - cv: 0.2587
- **C6** (fail): stat=0.0000 threshold=0.1000
    - n_trades: 67
    - sl_cv: 0.0000
    - tp1_cv: 0.0000
    - mean_sl: 39.0000
    - mean_tp1: 58.5000

### barou_shoei
- **C1** (fail): stat=0.3470 threshold=0.3000
    - n_trades: 62
    - mean_tqs: 0.3470
    - windows_passing_0.20: 6
    - windows_required: 5
    - per_window_means: {'0': 0.2208, '1': 0.4476, '2': 0.0, '3': 0.3743, '4': 0.3408, '5': 0.3006, '6': 0.4089}
    - bootstrap_ci95: [0.247, 0.4463]
    - ci_lower_floor: 0.2500
- **C2** (fail): stat=0.0000 threshold=0.0000
    - qualifying_peers: []
    - isagi_yoichi: dTQS=0.00011 CI=[-0.03354, 0.03293] (qual=False) | dTrades=-15 CI=[-4.0, -0.714] (qual=False)
    - bachira_meguru: dTQS=0.00097 CI=[-0.02829, 0.02974] (qual=False) | dTrades=-46 CI=[-9.143, -4.143] (qual=False)
    - itoshi_rin: dTQS=0.0 CI=[-0.11525, 0.11521] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - chigiri_hyoma: dTQS=0.0 CI=[-0.06266, 0.06555] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=-0.0128 CI=[-0.19585, 0.17041] (qual=False) | dTrades=-2 CI=[-0.857, 0.0] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.01, w1:0.07, w2:0.01, w3:0.03, w4:0.04, w5:0.29, w6:0.05 ('!' = dirty window)
- **C4** (pass): stat=4576.0000 threshold=1.0000
    - publish_count: 17722
    - read_count: 4576
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.2541 threshold=0.1000
    - n_trades: 62
    - mean_lot: 0.1400
    - min_lot: 0.0800
    - max_lot: 0.1800
    - cv: 0.2541
- **C6** (pass): stat=0.1541 threshold=0.1000
    - n_trades: 62
    - sl_cv: 0.1541
    - tp1_cv: 0.1541
    - mean_sl: 32.3419
    - mean_tp1: 48.5129

