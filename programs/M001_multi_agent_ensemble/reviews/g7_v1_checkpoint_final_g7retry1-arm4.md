# G7 v1 Checkpoint Gate -- FINAL verdict (g7retry1-arm4)

**Squad verdict: FAIL** (2/7 agents pass all six criteria)

- Aggregator arm: `arm4`
- Baseline cache: `programs/M001_multi_agent_ensemble/reviews/g7_replay_cache_g7retry1-arm4`
- Leave-one-out caches: `programs/M001_multi_agent_ensemble/reviews/g7_leave_one_out_g7retry1-arm4/lo1_*`
- Bootstrap: n=10000, seed=42, percentile CI, alpha=0.05
- Windows: 7 rolling OOS (2019..2025)

## Per-agent 6-bit vectors

| Agent | Playstyle | Bit vector | C1 | C2 | C3 | C4 | C5 | C6 | v1 pass? |
|---|---|---|---|---|---|---|---|---|---|
| `isagi_yoichi` | conservative_metavision | `101111` | ✅ 0.354 | ❌ 0.000 | ✅ 7.000 | ✅ 6571.000 | ✅ 0.195 | ✅ 0.185 | no |
| `bachira_meguru` | rebel_tight | `110111` | ✅ 0.386 | ✅ 0.236 | ❌ 3.000 | ✅ 14551.000 | ✅ 0.450 | ✅ 0.156 | no |
| `itoshi_rin` | analytical_precision | `111111` | ✅ 0.374 | ✅ 0.129 | ✅ 7.000 | ✅ 2988.000 | ✅ 0.112 | ✅ 0.219 | YES |
| `chigiri_hyoma` | speed_momentum | `001111` | ❌ 0.269 | ❌ 0.000 | ✅ 7.000 | ✅ 992.000 | ✅ 0.106 | ✅ 0.177 | no |
| `reo_mikage` | copier_hrp | `W11WWW` | W | ✅ 0.011 | ✅ 6.000 | W | W | W | YES |
| `nagi_seishiro` | confluence_only | `101111` | ✅ 0.421 | ❌ 0.000 | ✅ 7.000 | ✅ 658.000 | ✅ 0.231 | ✅ 0.130 | no |
| `barou_shoei` | solo_king | `101111` | ✅ 0.380 | ❌ 0.000 | ✅ 7.000 | ✅ 2080.000 | ✅ 0.243 | ✅ 0.182 | no |

Legend: `1` pass / `0` fail / `W` waived (structural falsifier, sec 11.1) / `?` pending. Cell numbers are the criterion statistic (C1 mean TQS; C2 strongest qualifying delta; C3 clean windows; C4 min(publish, read); C5/C6 CV).

## Notes

- All statistics OOS-only (union of the 7 rolling OOS windows); differs from the diagnostic lo1 verdicts which pooled IS+OOS.
- C4 evaluated on panel-wide publish/read counters (per-window counts not persisted in caches; documented harness limitation).
- C5/C6 recomputed from cached source_* trade fields via the pure playstyle-dispatched F19/F20 primitives (no agent overrides exist).

## Per-criterion evidence

### isagi_yoichi
- **C1** (pass): stat=0.3543 threshold=0.3000
    - n_trades: 1122
    - mean_tqs: 0.3543
    - windows_passing_0.20: 7
    - windows_required: 5
    - per_window_means: {'0': 0.3796, '1': 0.3514, '2': 0.3311, '3': 0.3438, '4': 0.3606, '5': 0.3655, '6': 0.3524}
    - bootstrap_ci95: [0.3315, 0.3766]
    - ci_lower_floor: 0.2500
- **C2** (fail): stat=0.0000 threshold=0.0000
    - qualifying_peers: []
    - bachira_meguru: dTQS=0.00664 CI=[-0.01644, 0.02967] (qual=False) | dTrades=-480 CI=[-84.857, -54.714] (qual=False)
    - itoshi_rin: dTQS=0.00291 CI=[-0.10564, 0.1103] (qual=False) | dTrades=-3 CI=[-1.143, 0.286] (qual=False)
    - chigiri_hyoma: dTQS=0.00923 CI=[-0.05204, 0.07009] (qual=False) | dTrades=-26 CI=[-4.714, -2.714] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=0.02684 CI=[-0.13955, 0.19346] (qual=False) | dTrades=-4 CI=[-1.143, 0.143] (qual=False)
    - barou_shoei: dTQS=-0.02719 CI=[-0.1461, 0.08991] (qual=False) | dTrades=+8 CI=[-0.143, 2.714] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.18, w1:0.19, w2:0.18, w3:0.26, w4:0.18, w5:0.15, w6:0.17 ('!' = dirty window)
- **C4** (pass): stat=6571.0000 threshold=1.0000
    - publish_count: 53163
    - read_count: 6571
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.1952 threshold=0.1000
    - n_trades: 1122
    - mean_lot: 0.1765
    - min_lot: 0.0900
    - max_lot: 0.2000
    - cv: 0.1952
- **C6** (pass): stat=0.1855 threshold=0.1000
    - n_trades: 1122
    - sl_cv: 0.1855
    - tp1_cv: 0.1855
    - mean_sl: 41.8100
    - mean_tp1: 62.7149

### bachira_meguru
- **C1** (pass): stat=0.3862 threshold=0.3000
    - n_trades: 2035
    - mean_tqs: 0.3862
    - windows_passing_0.20: 7
    - windows_required: 5
    - per_window_means: {'0': 0.3656, '1': 0.3692, '2': 0.3736, '3': 0.4234, '4': 0.4003, '5': 0.3882, '6': 0.3825}
    - bootstrap_ci95: [0.3693, 0.403]
    - ci_lower_floor: 0.2500
- **C2** (pass): stat=0.2357 threshold=0.0000
    - qualifying_peers: ['nagi_seishiro']
    - isagi_yoichi: dTQS=-0.00522 CI=[-0.03637, 0.02552] (qual=False) | dTrades=-87 CI=[-16.714, -8.714] (qual=False)
    - itoshi_rin: dTQS=-0.02974 CI=[-0.13892, 0.07822] (qual=False) | dTrades=-31 CI=[-6.571, -2.714] (qual=False)
    - chigiri_hyoma: dTQS=0.00664 CI=[-0.05623, 0.0683] (qual=False) | dTrades=-23 CI=[-4.286, -2.286] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=0.23574 CI=[-0.05378, 0.47373] (qual=False) | dTrades=+63 CI=[6.429, 12.0] (qual=True)
    - barou_shoei: dTQS=-0.00253 CI=[-0.10502, 0.09904] (qual=False) | dTrades=-91 CI=[-14.429, -11.286] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (fail): stat=3.0000 threshold=4.0000
    - clean_windows: 3
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.54!, w1:0.65!, w2:0.61!, w3:0.50, w4:0.41, w5:0.45, w6:0.54! ('!' = dirty window)
- **C4** (pass): stat=14551.0000 threshold=1.0000
    - publish_count: 53163
    - read_count: 14551
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.4497 threshold=0.1000
    - n_trades: 2035
    - mean_lot: 0.0582
    - min_lot: 0.0200
    - max_lot: 0.1300
    - cv: 0.4497
- **C6** (pass): stat=0.1556 threshold=0.1000
    - n_trades: 2035
    - sl_cv: 0.1556
    - tp1_cv: 0.1556
    - mean_sl: 22.2658
    - mean_tp1: 66.7975

### itoshi_rin
- **C1** (pass): stat=0.3738 threshold=0.3000
    - n_trades: 212
    - mean_tqs: 0.3738
    - windows_passing_0.20: 7
    - windows_required: 5
    - per_window_means: {'0': 0.3668, '1': 0.3855, '2': 0.2383, '3': 0.435, '4': 0.3243, '5': 0.3955, '6': 0.3818}
    - bootstrap_ci95: [0.2977, 0.454]
    - ci_lower_floor: 0.2500
- **C2** (pass): stat=0.1290 threshold=0.0000
    - qualifying_peers: ['nagi_seishiro']
    - isagi_yoichi: dTQS=-0.00104 CI=[-0.03196, 0.03012] (qual=False) | dTrades=-178 CI=[-40.0, -15.429] (qual=False)
    - bachira_meguru: dTQS=0.00152 CI=[-0.02196, 0.02527] (qual=False) | dTrades=-112 CI=[-20.571, -11.714] (qual=False)
    - chigiri_hyoma: dTQS=-0.00044 CI=[-0.06196, 0.06291] (qual=False) | dTrades=-12 CI=[-2.286, -1.286] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=0.12899 CI=[-0.04478, 0.30324] (qual=False) | dTrades=+45 CI=[2.714, 10.714] (qual=True)
    - barou_shoei: dTQS=0.0 CI=[-0.11336, 0.11266] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.05, w1:0.15, w2:0.08, w3:0.25, w4:0.12, w5:0.11, w6:0.14 ('!' = dirty window)
- **C4** (pass): stat=2988.0000 threshold=1.0000
    - publish_count: 17723
    - read_count: 2988
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.1119 threshold=0.1000
    - n_trades: 212
    - mean_lot: 0.0883
    - min_lot: 0.0700
    - max_lot: 0.1100
    - cv: 0.1119
- **C6** (pass): stat=0.2189 threshold=0.1000
    - n_trades: 212
    - sl_cv: 0.2189
    - tp1_cv: 0.2189
    - mean_sl: 29.7875
    - mean_tp1: 59.5751

### chigiri_hyoma
- **C1** (fail): stat=0.2690 threshold=0.3000
    - n_trades: 300
    - mean_tqs: 0.2690
    - windows_passing_0.20: 6
    - windows_required: 5
    - per_window_means: {'0': 0.1893, '1': 0.3351, '2': 0.2408, '3': 0.3391, '4': 0.2347, '5': 0.3101, '6': 0.2636}
    - bootstrap_ci95: [0.2243, 0.315]
    - ci_lower_floor: 0.2500
- **C2** (fail): stat=0.0000 threshold=0.0000
    - qualifying_peers: []
    - isagi_yoichi: dTQS=-0.00197 CI=[-0.03378, 0.02982] (qual=False) | dTrades=-30 CI=[-5.429, -3.286] (qual=False)
    - bachira_meguru: dTQS=0.00088 CI=[-0.02313, 0.02446] (qual=False) | dTrades=-84 CI=[-17.714, -6.714] (qual=False)
    - itoshi_rin: dTQS=-0.01156 CI=[-0.12473, 0.10047] (qual=False) | dTrades=-3 CI=[-1.143, 0.286] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=-0.00439 CI=[-0.1699, 0.16391] (qual=False) | dTrades=+1 CI=[-0.857, 1.0] (qual=False)
    - barou_shoei: dTQS=0.0 CI=[-0.11336, 0.11266] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.20, w1:0.07, w2:0.03, w3:0.03, w4:0.06, w5:0.03, w6:0.09 ('!' = dirty window)
- **C4** (pass): stat=992.0000 threshold=1.0000
    - publish_count: 35441
    - read_count: 992
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.1058 threshold=0.1000
    - n_trades: 300
    - mean_lot: 0.1568
    - min_lot: 0.1200
    - max_lot: 0.1900
    - cv: 0.1058
- **C6** (pass): stat=0.1772 threshold=0.1000
    - n_trades: 300
    - sl_cv: 0.1772
    - tp1_cv: 0.1772
    - mean_sl: 34.6471
    - mean_tp1: 103.9413

### reo_mikage
- **C1** (waived): stat=53163.0000 threshold=0.0000
    - reason: structural falsifier waiver (sec 11.1) -- intend() returns None by design; earns v1 through publishing
    - publish_count: 53163
- **C2** (pass): stat=0.0106 threshold=0.0000
    - qualifying_peers: ['itoshi_rin']
    - isagi_yoichi: dTQS=0.00046 CI=[-0.03117, 0.03098] (qual=False) | dTrades=+3 CI=[-0.714, 1.429] (qual=False)
    - bachira_meguru: dTQS=0.00147 CI=[-0.02254, 0.02487] (qual=False) | dTrades=+0 CI=[-3.571, 3.143] (qual=False)
    - itoshi_rin: dTQS=0.01055 CI=[-0.10429, 0.12422] (qual=False) | dTrades=+19 CI=[0.714, 5.429] (qual=True)
    - chigiri_hyoma: dTQS=0.00101 CI=[-0.06319, 0.06446] (qual=False) | dTrades=+8 CI=[0.0, 2.429] (qual=False)
    - nagi_seishiro: dTQS=0.03193 CI=[-0.11674, 0.18173] (qual=False) | dTrades=-57 CI=[-20.143, -0.286] (qual=False)
    - barou_shoei: dTQS=0.0 CI=[-0.11336, 0.11266] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=6.0000 threshold=4.0000
    - clean_windows: 6
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.01, w1:0.19, w2:0.20, w3:0.67!, w4:0.31, w5:0.25, w6:0.40 ('!' = dirty window)
- **C4** (waived): stat=53163.0000 threshold=1.0000
    - reason: structural falsifier -- publish alone suffices (doctrine sec 3.10 exception)
    - publish_count: 53163
    - read_count: 0
- **C5** (waived): stat=0.0000 threshold=0.1000
    - reason: structural falsifier waived on C5 -- agent's intend() returns None by design (doctrine sec 3.10 / 3.11); no trade-side lot dispersion measurable
    - agent_id: reo_mikage
- **C6** (waived): stat=0.0000 threshold=0.1000
    - reason: structural falsifier waived on C6 -- agent's intend() returns None by design (doctrine sec 3.10 / 3.11); no trade-side risk-shape dispersion measurable
    - agent_id: reo_mikage

### nagi_seishiro
- **C1** (pass): stat=0.4206 threshold=0.3000
    - n_trades: 79
    - mean_tqs: 0.4206
    - windows_passing_0.20: 6
    - windows_required: 5
    - per_window_means: {'0': 0.1431, '1': 0.3839, '2': 0.3251, '3': 0.5549, '4': 0.5483, '5': 0.2592, '6': 0.4376}
    - bootstrap_ci95: [0.3057, 0.5401]
    - ci_lower_floor: 0.2500
- **C2** (fail): stat=0.0000 threshold=0.0000
    - qualifying_peers: []
    - isagi_yoichi: dTQS=-0.00203 CI=[-0.03448, 0.0298] (qual=False) | dTrades=-5 CI=[-1.571, -0.143] (qual=False)
    - bachira_meguru: dTQS=0.0007 CI=[-0.02321, 0.02454] (qual=False) | dTrades=-13 CI=[-2.714, -1.0] (qual=False)
    - itoshi_rin: dTQS=-0.00624 CI=[-0.11622, 0.10269] (qual=False) | dTrades=-6 CI=[-1.429, -0.286] (qual=False)
    - chigiri_hyoma: dTQS=0.00065 CI=[-0.06216, 0.06545] (qual=False) | dTrades=-4 CI=[-1.143, -0.143] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - barou_shoei: dTQS=0.0 CI=[-0.11336, 0.11266] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.01, w1:0.06, w2:0.03, w3:0.03, w4:0.04, w5:0.06, w6:0.00 ('!' = dirty window)
- **C4** (pass): stat=658.0000 threshold=1.0000
    - publish_count: 53163
    - read_count: 658
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.2306 threshold=0.1000
    - n_trades: 79
    - mean_lot: 0.1701
    - min_lot: 0.0800
    - max_lot: 0.2000
    - cv: 0.2306
- **C6** (pass): stat=0.1303 threshold=0.1000
    - n_trades: 79
    - sl_cv: 0.1303
    - tp1_cv: 0.1303
    - mean_sl: 37.1489
    - mean_tp1: 55.7234

### barou_shoei
- **C1** (pass): stat=0.3802 threshold=0.3000
    - n_trades: 86
    - mean_tqs: 0.3802
    - windows_passing_0.20: 7
    - windows_required: 5
    - per_window_means: {'0': 0.4155, '1': 0.2432, '2': 0.452, '3': 0.3236, '4': 0.5516, '5': 0.2654, '6': 0.3}
    - bootstrap_ci95: [0.2993, 0.4624]
    - ci_lower_floor: 0.2500
- **C2** (fail): stat=0.0000 threshold=0.0000
    - qualifying_peers: []
    - isagi_yoichi: dTQS=0.00239 CI=[-0.02879, 0.0337] (qual=False) | dTrades=-17 CI=[-4.571, -0.714] (qual=False)
    - bachira_meguru: dTQS=0.00366 CI=[-0.02009, 0.02764] (qual=False) | dTrades=-39 CI=[-7.429, -3.714] (qual=False)
    - itoshi_rin: dTQS=0.0 CI=[-0.11065, 0.10904] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - chigiri_hyoma: dTQS=0.0 CI=[-0.06232, 0.06208] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=-0.00212 CI=[-0.16886, 0.16451] (qual=False) | dTrades=-2 CI=[-0.714, 0.0] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.03, w1:0.01, w2:0.01, w3:0.02, w4:0.05, w5:0.14, w6:0.08 ('!' = dirty window)
- **C4** (pass): stat=2080.0000 threshold=1.0000
    - publish_count: 17722
    - read_count: 2080
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.2428 threshold=0.1000
    - n_trades: 86
    - mean_lot: 0.1145
    - min_lot: 0.0700
    - max_lot: 0.1800
    - cv: 0.2428
- **C6** (pass): stat=0.1822 threshold=0.1000
    - n_trades: 86
    - sl_cv: 0.1822
    - tp1_cv: 0.1822
    - mean_sl: 30.0203
    - mean_tp1: 45.0305

