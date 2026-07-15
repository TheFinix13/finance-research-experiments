# G7 v1 Checkpoint Gate -- FINAL verdict (g7retry2-phi41)

**Squad verdict: FAIL** (3/7 agents pass all six criteria)

- Aggregator arm: `phi41`
- Baseline cache: `programs/M001_multi_agent_ensemble/reviews/g7_replay_cache_g7retry2-phi41`
- Leave-one-out caches: `programs/M001_multi_agent_ensemble/reviews/g7_leave_one_out_g7retry2-phi41/lo1_*`
- Bootstrap: n=10000, seed=42, percentile CI, alpha=0.05
- Windows: 7 rolling OOS (2019..2025)

## Per-agent 6-bit vectors

| Agent | Playstyle | Bit vector | C1 | C2 | C3 | C4 | C5 | C6 | v1 pass? |
|---|---|---|---|---|---|---|---|---|---|
| `isagi_yoichi` | conservative_metavision | `111111` | ✅ 0.362 | ✅ 0.003 | ✅ 7.000 | ✅ 6571.000 | ✅ 0.209 | ✅ 0.178 | YES |
| `bachira_meguru` | rebel_tight | `111111` | ✅ 0.388 | ✅ -0.002 | ✅ 7.000 | ✅ 3620.000 | ✅ 0.473 | ✅ 0.152 | YES |
| `itoshi_rin` | analytical_precision | `111111` | ✅ 0.386 | ✅ 0.163 | ✅ 7.000 | ✅ 2988.000 | ✅ 0.114 | ✅ 0.213 | YES |
| `chigiri_hyoma` | speed_momentum | `001111` | ❌ 0.239 | ❌ 0.000 | ✅ 7.000 | ✅ 1231.000 | ✅ 0.116 | ✅ 0.159 | no |
| `reo_mikage` | copier_hrp | `W01WWW` | W | ❌ 0.000 | ✅ 6.000 | W | W | W | no |
| `nagi_seishiro` | confluence_only | `001111` | ❌ 0.197 | ❌ 0.000 | ✅ 7.000 | ✅ 208.000 | ✅ 0.232 | ✅ 0.179 | no |
| `barou_shoei` | solo_king | `101111` | ✅ 0.406 | ❌ 0.000 | ✅ 7.000 | ✅ 6793.000 | ✅ 0.285 | ✅ 0.166 | no |

Legend: `1` pass / `0` fail / `W` waived (structural falsifier, sec 11.1) / `?` pending. Cell numbers are the criterion statistic (C1 mean TQS; C2 strongest qualifying delta; C3 clean windows; C4 min(publish, read); C5/C6 CV).

## ADVISORY -- C2 finisher clause (Lever D, pending ratification)

Advisory squad verdict WITH the clause: **FAIL** (3/7). The verdict-bearing numbers above are unaffected.

- `nagi_seishiro` (confluence_only): W (clause pass) -- 3 qualified incoming lift(s) ['bachira_meguru', 'isagi_yoichi', 'itoshi_rin'] (need >= 2)

## Notes

- All statistics OOS-only (union of the 7 rolling OOS windows); differs from the diagnostic lo1 verdicts which pooled IS+OOS.
- C4 evaluated on panel-wide publish/read counters (per-window counts not persisted in caches; documented harness limitation).
- C5/C6 recomputed from cached source_* trade fields via the pure playstyle-dispatched F19/F20 primitives (no agent overrides exist).
- C2 finisher clause evaluated ADVISORY-ONLY (experiments/c2_finisher_clause/PROTOCOL.md, pending user ratification); verdict-bearing bit vectors and squad verdict are computed without it.

## Per-criterion evidence

### isagi_yoichi
- **C1** (pass): stat=0.3615 threshold=0.3000
    - n_trades: 935
    - mean_tqs: 0.3615
    - windows_passing_0.20: 7
    - windows_required: 5
    - per_window_means: {'0': 0.3906, '1': 0.3541, '2': 0.3336, '3': 0.3558, '4': 0.3823, '5': 0.3727, '6': 0.3449}
    - bootstrap_ci95: [0.3365, 0.3865]
    - ci_lower_floor: 0.2500
- **C2** (pass): stat=0.0025 threshold=0.0000
    - qualifying_peers: ['nagi_seishiro']
    - bachira_meguru: dTQS=0.0048 CI=[-0.03556, 0.04425] (qual=False) | dTrades=-32 CI=[-7.0, -2.143] (qual=False)
    - itoshi_rin: dTQS=0.00691 CI=[-0.10629, 0.11942] (qual=False) | dTrades=-8 CI=[-2.143, -0.286] (qual=False)
    - chigiri_hyoma: dTQS=-0.00197 CI=[-0.04869, 0.04376] (qual=False) | dTrades=+2 CI=[-0.286, 0.714] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=0.00251 CI=[-0.37118, 0.3232] (qual=False) | dTrades=+11 CI=[0.714, 2.429] (qual=True)
    - barou_shoei: dTQS=0.00436 CI=[-0.05085, 0.06121] (qual=False) | dTrades=-78 CI=[-16.143, -8.0] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.26, w1:0.11, w2:0.12, w3:0.11, w4:0.13, w5:0.12, w6:0.15 ('!' = dirty window)
- **C4** (pass): stat=6571.0000 threshold=1.0000
    - publish_count: 53163
    - read_count: 6571
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.2087 threshold=0.1000
    - n_trades: 935
    - mean_lot: 0.1727
    - min_lot: 0.0900
    - max_lot: 0.2000
    - cv: 0.2087
- **C6** (pass): stat=0.1779 threshold=0.1000
    - n_trades: 935
    - sl_cv: 0.1779
    - tp1_cv: 0.1779
    - mean_sl: 42.2605
    - mean_tp1: 63.3907

### bachira_meguru
- **C1** (pass): stat=0.3878 threshold=0.3000
    - n_trades: 733
    - mean_tqs: 0.3878
    - windows_passing_0.20: 7
    - windows_required: 5
    - per_window_means: {'0': 0.3857, '1': 0.3528, '2': 0.3105, '3': 0.4361, '4': 0.4249, '5': 0.4014, '6': 0.4407}
    - bootstrap_ci95: [0.359, 0.4166]
    - ci_lower_floor: 0.2500
- **C2** (pass): stat=-0.0023 threshold=0.0000
    - qualifying_peers: ['nagi_seishiro']
    - isagi_yoichi: dTQS=-0.00277 CI=[-0.03742, 0.03237] (qual=False) | dTrades=-53 CI=[-9.571, -5.143] (qual=False)
    - itoshi_rin: dTQS=-0.01296 CI=[-0.12559, 0.10091] (qual=False) | dTrades=-7 CI=[-1.714, -0.286] (qual=False)
    - chigiri_hyoma: dTQS=0.00152 CI=[-0.04491, 0.04666] (qual=False) | dTrades=-9 CI=[-2.429, 0.0] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=-0.00229 CI=[-0.35911, 0.30275] (qual=False) | dTrades=+10 CI=[0.714, 2.143] (qual=True)
    - barou_shoei: dTQS=-0.00313 CI=[-0.05976, 0.05329] (qual=False) | dTrades=-25 CI=[-4.571, -2.714] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.08, w1:0.07, w2:0.06, w3:0.06, w4:0.06, w5:0.09, w6:0.09 ('!' = dirty window)
- **C4** (pass): stat=3620.0000 threshold=1.0000
    - publish_count: 53163
    - read_count: 3620
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.4728 threshold=0.1000
    - n_trades: 733
    - mean_lot: 0.0520
    - min_lot: 0.0200
    - max_lot: 0.1100
    - cv: 0.4728
- **C6** (pass): stat=0.1523 threshold=0.1000
    - n_trades: 733
    - sl_cv: 0.1523
    - tp1_cv: 0.1523
    - mean_sl: 22.1116
    - mean_tp1: 66.3348

### itoshi_rin
- **C1** (pass): stat=0.3862 threshold=0.3000
    - n_trades: 202
    - mean_tqs: 0.3862
    - windows_passing_0.20: 7
    - windows_required: 5
    - per_window_means: {'0': 0.2435, '1': 0.3372, '2': 0.3135, '3': 0.4536, '4': 0.3243, '5': 0.3723, '6': 0.4666}
    - bootstrap_ci95: [0.3092, 0.4679]
    - ci_lower_floor: 0.2500
- **C2** (pass): stat=0.1630 threshold=0.0000
    - qualifying_peers: ['nagi_seishiro']
    - isagi_yoichi: dTQS=-0.00182 CI=[-0.03528, 0.03194] (qual=False) | dTrades=-238 CI=[-53.286, -21.143] (qual=False)
    - bachira_meguru: dTQS=0.00439 CI=[-0.03599, 0.0447] (qual=False) | dTrades=-22 CI=[-5.143, -1.286] (qual=False)
    - chigiri_hyoma: dTQS=0.00202 CI=[-0.04351, 0.04736] (qual=False) | dTrades=-9 CI=[-2.429, -0.286] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=0.16302 CI=[-0.01119, 0.38335] (qual=False) | dTrades=+7 CI=[0.429, 1.571] (qual=True)
    - barou_shoei: dTQS=-0.00171 CI=[-0.0589, 0.05573] (qual=False) | dTrades=-17 CI=[-4.286, -0.857] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.10, w1:0.18, w2:0.17, w3:0.35, w4:0.17, w5:0.17, w6:0.18 ('!' = dirty window)
- **C4** (pass): stat=2988.0000 threshold=1.0000
    - publish_count: 17723
    - read_count: 2988
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.1143 threshold=0.1000
    - n_trades: 202
    - mean_lot: 0.0889
    - min_lot: 0.0700
    - max_lot: 0.1100
    - cv: 0.1143
- **C6** (pass): stat=0.2134 threshold=0.1000
    - n_trades: 202
    - sl_cv: 0.2134
    - tp1_cv: 0.2134
    - mean_sl: 29.8416
    - mean_tp1: 59.6832

### chigiri_hyoma
- **C1** (fail): stat=0.2386 threshold=0.3000
    - n_trades: 503
    - mean_tqs: 0.2386
    - windows_passing_0.20: 6
    - windows_required: 5
    - per_window_means: {'0': 0.2482, '1': 0.256, '2': 0.2209, '3': 0.2967, '4': 0.1713, '5': 0.257, '6': 0.2226}
    - bootstrap_ci95: [0.2066, 0.2718]
    - ci_lower_floor: 0.2500
- **C2** (fail): stat=0.0000 threshold=0.0000
    - qualifying_peers: []
    - isagi_yoichi: dTQS=0.00124 CI=[-0.03318, 0.03545] (qual=False) | dTrades=-80 CI=[-13.714, -9.429] (qual=False)
    - bachira_meguru: dTQS=0.00346 CI=[-0.03666, 0.04316] (qual=False) | dTrades=-37 CI=[-9.429, -2.0] (qual=False)
    - itoshi_rin: dTQS=0.00421 CI=[-0.10626, 0.11461] (qual=False) | dTrades=-20 CI=[-4.143, -1.571] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=-0.09396 CI=[-0.3881, 0.19444] (qual=False) | dTrades=-3 CI=[-1.0, 0.0] (qual=False)
    - barou_shoei: dTQS=-0.0011 CI=[-0.05755, 0.05733] (qual=False) | dTrades=-11 CI=[-2.857, -0.143] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.17, w1:0.13, w2:0.17, w3:0.50, w4:0.33, w5:0.09, w6:0.07 ('!' = dirty window)
- **C4** (pass): stat=1231.0000 threshold=1.0000
    - publish_count: 35441
    - read_count: 1231
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.1163 threshold=0.1000
    - n_trades: 503
    - mean_lot: 0.1965
    - min_lot: 0.1500
    - max_lot: 0.2400
    - cv: 0.1163
- **C6** (pass): stat=0.1591 threshold=0.1000
    - n_trades: 503
    - sl_cv: 0.1591
    - tp1_cv: 0.1591
    - mean_sl: 35.7495
    - mean_tp1: 107.2485

### reo_mikage
- **C1** (waived): stat=53163.0000 threshold=0.0000
    - reason: structural falsifier waiver (sec 11.1) -- intend() returns None by design; earns v1 through publishing
    - publish_count: 53163
- **C2** (fail): stat=0.0000 threshold=0.0000
    - qualifying_peers: []
    - isagi_yoichi: dTQS=0.0002 CI=[-0.03456, 0.03619] (qual=False) | dTrades=-7 CI=[-2.143, -0.143] (qual=False)
    - bachira_meguru: dTQS=0.00166 CI=[-0.03827, 0.04151] (qual=False) | dTrades=+0 CI=[-0.714, 0.571] (qual=False)
    - itoshi_rin: dTQS=-0.0037 CI=[-0.11601, 0.10911] (qual=False) | dTrades=-1 CI=[-0.429, 0.0] (qual=False)
    - chigiri_hyoma: dTQS=0.0 CI=[-0.04583, 0.04555] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=-0.10782 CI=[-0.57391, 0.27917] (qual=False) | dTrades=+13 CI=[-0.571, 4.143] (qual=False)
    - barou_shoei: dTQS=0.00148 CI=[-0.05549, 0.05903] (qual=False) | dTrades=-4 CI=[-1.143, -0.143] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=6.0000 threshold=4.0000
    - clean_windows: 6
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.09, w1:0.01, w2:0.01, w3:0.67!, w4:0.03, w5:0.00, w6:0.02 ('!' = dirty window)
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
- **C1** (fail): stat=0.1966 threshold=0.3000
    - n_trades: 21
    - mean_tqs: 0.1966
    - windows_passing_0.20: 2
    - windows_required: 5
    - per_window_means: {'0': 0.1467, '1': 0.0, '2': 0.3207, '3': 0.7353, '4': 0.0, '5': 0.0, '6': 0.0}
    - bootstrap_ci95: [0.0349, 0.4067]
    - ci_lower_floor: 0.2500
- **C2** (fail): stat=0.0000 threshold=0.0000
    - qualifying_peers: []
    - isagi_yoichi: dTQS=0.00058 CI=[-0.03471, 0.03615] (qual=False) | dTrades=-8 CI=[-2.286, -0.286] (qual=False)
    - bachira_meguru: dTQS=0.00142 CI=[-0.03961, 0.04155] (qual=False) | dTrades=-3 CI=[-1.0, 0.0] (qual=False)
    - itoshi_rin: dTQS=-0.0037 CI=[-0.11601, 0.10911] (qual=False) | dTrades=-1 CI=[-0.429, 0.0] (qual=False)
    - chigiri_hyoma: dTQS=0.0 CI=[-0.04583, 0.04555] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - barou_shoei: dTQS=-5e-05 CI=[-0.0568, 0.05785] (qual=False) | dTrades=-3 CI=[-0.857, -0.143] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.09, w1:0.01, w2:0.01, w3:0.02, w4:0.01, w5:0.00, w6:0.00 ('!' = dirty window)
- **C4** (pass): stat=208.0000 threshold=1.0000
    - publish_count: 53163
    - read_count: 208
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.2324 threshold=0.1000
    - n_trades: 21
    - mean_lot: 0.1519
    - min_lot: 0.1000
    - max_lot: 0.2000
    - cv: 0.2324
- **C6** (pass): stat=0.1794 threshold=0.1000
    - n_trades: 21
    - sl_cv: 0.1794
    - tp1_cv: 0.1794
    - mean_sl: 34.7043
    - mean_tp1: 52.0564

### barou_shoei
- **C1** (pass): stat=0.4056 threshold=0.3000
    - n_trades: 444
    - mean_tqs: 0.4056
    - windows_passing_0.20: 7
    - windows_required: 5
    - per_window_means: {'0': 0.3328, '1': 0.4034, '2': 0.4737, '3': 0.4572, '4': 0.5363, '5': 0.3226, '6': 0.2823}
    - bootstrap_ci95: [0.3647, 0.4466]
    - ci_lower_floor: 0.2500
- **C2** (fail): stat=0.0000 threshold=0.0000
    - qualifying_peers: []
    - isagi_yoichi: dTQS=0.00357 CI=[-0.03029, 0.03832] (qual=False) | dTrades=-113 CI=[-20.571, -12.0] (qual=False)
    - bachira_meguru: dTQS=-0.00036 CI=[-0.04036, 0.03978] (qual=False) | dTrades=-60 CI=[-12.143, -4.857] (qual=False)
    - itoshi_rin: dTQS=-0.00514 CI=[-0.1183, 0.10817] (qual=False) | dTrades=-6 CI=[-2.0, 0.429] (qual=False)
    - chigiri_hyoma: dTQS=-0.0014 CI=[-0.04742, 0.04412] (qual=False) | dTrades=-22 CI=[-4.714, -1.714] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=-0.02236 CI=[-0.30687, 0.26561] (qual=False) | dTrades=+2 CI=[-0.571, 1.143] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.23, w1:0.07, w2:0.11, w3:0.50, w4:0.13, w5:0.17, w6:0.09 ('!' = dirty window)
- **C4** (pass): stat=6793.0000 threshold=1.0000
    - publish_count: 53163
    - read_count: 6793
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.2847 threshold=0.1000
    - n_trades: 444
    - mean_lot: 0.0944
    - min_lot: 0.0600
    - max_lot: 0.1800
    - cv: 0.2847
- **C6** (pass): stat=0.1659 threshold=0.1000
    - n_trades: 444
    - sl_cv: 0.1659
    - tp1_cv: 0.1659
    - mean_sl: 31.2795
    - mean_tp1: 46.9193

