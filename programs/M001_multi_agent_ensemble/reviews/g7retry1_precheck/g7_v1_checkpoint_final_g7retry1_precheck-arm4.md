# G7 v1 Checkpoint Gate -- FINAL verdict (g7retry1_precheck-arm4)

**Squad verdict: FAIL** (2/7 agents pass all six criteria)

- Aggregator arm: `arm4`
- Baseline cache: `/Users/the1finix/Documents/GitHub/finance-research-experiments/programs/M001_multi_agent_ensemble/reviews/g7_replay_cache_phi5-arm4-post-kunigami`
- Leave-one-out caches: `/Users/the1finix/Documents/GitHub/finance-research-experiments/programs/M001_multi_agent_ensemble/reviews/g7_leave_one_out_phi5-arm4/lo1_*`
- Bootstrap: n=10000, seed=42, percentile CI, alpha=0.05
- Windows: 7 rolling OOS (2019..2025)

## Per-agent 6-bit vectors

| Agent | Playstyle | Bit vector | C1 | C2 | C3 | C4 | C5 | C6 | v1 pass? |
|---|---|---|---|---|---|---|---|---|---|
| `isagi_yoichi` | conservative_metavision | `101111` | ✅ 0.351 | ❌ 0.000 | ✅ 7.000 | ✅ 6571.000 | ✅ 0.196 | ✅ 0.185 | no |
| `bachira_meguru` | rebel_tight | `110111` | ✅ 0.384 | ✅ 0.136 | ❌ 1.000 | ✅ 14551.000 | ✅ 0.448 | ✅ 0.156 | no |
| `itoshi_rin` | analytical_precision | `111111` | ✅ 0.374 | ✅ 0.132 | ✅ 7.000 | ✅ 2988.000 | ✅ 0.112 | ✅ 0.219 | YES |
| `chigiri_hyoma` | speed_momentum | `001111` | ❌ 0.269 | ❌ 0.000 | ✅ 7.000 | ✅ 992.000 | ✅ 0.106 | ✅ 0.177 | no |
| `reo_mikage` | copier_hrp | `W11WWW` | W | ✅ 0.011 | ✅ 6.000 | W | W | W | YES |
| `nagi_seishiro` | confluence_only | `101110` | ✅ 0.427 | ❌ 0.000 | ✅ 7.000 | ✅ 658.000 | ✅ 0.246 | ❌ 0.000 | no |
| `barou_shoei` | solo_king | `101111` | ✅ 0.388 | ❌ 0.000 | ✅ 7.000 | ✅ 4576.000 | ✅ 0.151 | ✅ 0.183 | no |

Legend: `1` pass / `0` fail / `W` waived (structural falsifier, sec 11.1) / `?` pending. Cell numbers are the criterion statistic (C1 mean TQS; C2 strongest qualifying delta; C3 clean windows; C4 min(publish, read); C5/C6 CV).

## Notes

- All statistics OOS-only (union of the 7 rolling OOS windows); differs from the diagnostic lo1 verdicts which pooled IS+OOS.
- C4 evaluated on panel-wide publish/read counters (per-window counts not persisted in caches; documented harness limitation).
- C5/C6 recomputed from cached source_* trade fields via the pure playstyle-dispatched F19/F20 primitives (no agent overrides exist).

## Per-criterion evidence

### isagi_yoichi
- **C1** (pass): stat=0.3512 threshold=0.3000
    - n_trades: 1120
    - mean_tqs: 0.3512
    - windows_passing_0.20: 7
    - windows_required: 5
    - per_window_means: {'0': 0.3784, '1': 0.3444, '2': 0.3311, '3': 0.3454, '4': 0.3576, '5': 0.3552, '6': 0.3469}
    - bootstrap_ci95: [0.3287, 0.3738]
    - ci_lower_floor: 0.2500
- **C2** (fail): stat=0.0000 threshold=0.0000
    - qualifying_peers: []
    - bachira_meguru: dTQS=0.00505 CI=[-0.01811, 0.0283] (qual=False) | dTrades=-496 CI=[-86.429, -57.0] (qual=False)
    - itoshi_rin: dTQS=0.00291 CI=[-0.10564, 0.1103] (qual=False) | dTrades=-3 CI=[-1.143, 0.286] (qual=False)
    - chigiri_hyoma: dTQS=0.00923 CI=[-0.05204, 0.07009] (qual=False) | dTrades=-26 CI=[-4.714, -2.714] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=0.01889 CI=[-0.14918, 0.19153] (qual=False) | dTrades=-4 CI=[-1.143, -0.143] (qual=False)
    - barou_shoei: dTQS=0.002 CI=[-0.04964, 0.05467] (qual=False) | dTrades=-146 CI=[-26.429, -16.429] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.44, w1:0.33, w2:0.22, w3:0.27, w4:0.35, w5:0.21, w6:0.34 ('!' = dirty window)
- **C4** (pass): stat=6571.0000 threshold=1.0000
    - publish_count: 53164
    - read_count: 6571
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.1959 threshold=0.1000
    - n_trades: 1120
    - mean_lot: 0.1764
    - min_lot: 0.0900
    - max_lot: 0.2000
    - cv: 0.1959
- **C6** (pass): stat=0.1851 threshold=0.1000
    - n_trades: 1120
    - sl_cv: 0.1851
    - tp1_cv: 0.1851
    - mean_sl: 41.8297
    - mean_tp1: 62.7445

### bachira_meguru
- **C1** (pass): stat=0.3836 threshold=0.3000
    - n_trades: 2040
    - mean_tqs: 0.3836
    - windows_passing_0.20: 7
    - windows_required: 5
    - per_window_means: {'0': 0.3615, '1': 0.3633, '2': 0.3736, '3': 0.4228, '4': 0.3947, '5': 0.3844, '6': 0.3833}
    - bootstrap_ci95: [0.3662, 0.4004]
    - ci_lower_floor: 0.2500
- **C2** (pass): stat=0.1357 threshold=0.0000
    - qualifying_peers: ['nagi_seishiro']
    - isagi_yoichi: dTQS=-0.00386 CI=[-0.03587, 0.02768] (qual=False) | dTrades=-56 CI=[-11.714, -4.571] (qual=False)
    - itoshi_rin: dTQS=-0.02974 CI=[-0.13892, 0.07822] (qual=False) | dTrades=-31 CI=[-6.571, -2.714] (qual=False)
    - chigiri_hyoma: dTQS=0.00664 CI=[-0.05623, 0.0683] (qual=False) | dTrades=-23 CI=[-4.286, -2.286] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=0.13566 CI=[-0.10203, 0.35185] (qual=False) | dTrades=+53 CI=[5.286, 10.429] (qual=True)
    - barou_shoei: dTQS=0.00343 CI=[-0.04686, 0.05461] (qual=False) | dTrades=-406 CI=[-63.571, -51.857] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (fail): stat=1.0000 threshold=4.0000
    - clean_windows: 1
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.61!, w1:0.62!, w2:0.54!, w3:0.62!, w4:0.56!, w5:0.43, w6:0.53! ('!' = dirty window)
- **C4** (pass): stat=14551.0000 threshold=1.0000
    - publish_count: 53164
    - read_count: 14551
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.4479 threshold=0.1000
    - n_trades: 2040
    - mean_lot: 0.0584
    - min_lot: 0.0200
    - max_lot: 0.1300
    - cv: 0.4479
- **C6** (pass): stat=0.1562 threshold=0.1000
    - n_trades: 2040
    - sl_cv: 0.1562
    - tp1_cv: 0.1562
    - mean_sl: 22.2374
    - mean_tp1: 66.7121

### itoshi_rin
- **C1** (pass): stat=0.3738 threshold=0.3000
    - n_trades: 212
    - mean_tqs: 0.3738
    - windows_passing_0.20: 7
    - windows_required: 5
    - per_window_means: {'0': 0.3668, '1': 0.3855, '2': 0.2383, '3': 0.435, '4': 0.3243, '5': 0.3955, '6': 0.3818}
    - bootstrap_ci95: [0.2977, 0.454]
    - ci_lower_floor: 0.2500
- **C2** (pass): stat=0.1316 threshold=0.0000
    - qualifying_peers: ['nagi_seishiro']
    - isagi_yoichi: dTQS=-0.00146 CI=[-0.0327, 0.02854] (qual=False) | dTrades=-178 CI=[-40.0, -15.429] (qual=False)
    - bachira_meguru: dTQS=0.00137 CI=[-0.02247, 0.0253] (qual=False) | dTrades=-112 CI=[-20.571, -11.714] (qual=False)
    - chigiri_hyoma: dTQS=-0.00044 CI=[-0.06196, 0.06291] (qual=False) | dTrades=-12 CI=[-2.286, -1.286] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=0.13157 CI=[-0.05395, 0.3122] (qual=False) | dTrades=+45 CI=[2.714, 10.714] (qual=True)
    - barou_shoei: dTQS=0.0 CI=[-0.05802, 0.05735] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
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
    - isagi_yoichi: dTQS=-0.00206 CI=[-0.03393, 0.02946] (qual=False) | dTrades=-30 CI=[-5.429, -3.286] (qual=False)
    - bachira_meguru: dTQS=0.00077 CI=[-0.02296, 0.02422] (qual=False) | dTrades=-84 CI=[-17.714, -6.714] (qual=False)
    - itoshi_rin: dTQS=-0.01156 CI=[-0.12473, 0.10047] (qual=False) | dTrades=-3 CI=[-1.143, 0.286] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=-0.00466 CI=[-0.17785, 0.17209] (qual=False) | dTrades=+1 CI=[-0.857, 1.0] (qual=False)
    - barou_shoei: dTQS=0.0 CI=[-0.05802, 0.05735] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.22, w1:0.07, w2:0.03, w3:0.03, w4:0.06, w5:0.03, w6:0.09 ('!' = dirty window)
- **C4** (pass): stat=992.0000 threshold=1.0000
    - publish_count: 35442
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
- **C1** (waived): stat=53164.0000 threshold=0.0000
    - reason: structural falsifier waiver (sec 11.1) -- intend() returns None by design; earns v1 through publishing
    - publish_count: 53164
- **C2** (pass): stat=0.0106 threshold=0.0000
    - qualifying_peers: ['itoshi_rin']
    - isagi_yoichi: dTQS=0.00047 CI=[-0.0314, 0.03226] (qual=False) | dTrades=+3 CI=[-0.714, 1.429] (qual=False)
    - bachira_meguru: dTQS=0.00146 CI=[-0.0224, 0.02537] (qual=False) | dTrades=+0 CI=[-3.571, 3.143] (qual=False)
    - itoshi_rin: dTQS=0.01055 CI=[-0.10429, 0.12422] (qual=False) | dTrades=+19 CI=[0.714, 5.429] (qual=True)
    - chigiri_hyoma: dTQS=0.00101 CI=[-0.06319, 0.06446] (qual=False) | dTrades=+8 CI=[0.0, 2.429] (qual=False)
    - nagi_seishiro: dTQS=0.03876 CI=[-0.11178, 0.19549] (qual=False) | dTrades=-60 CI=[-20.429, -0.857] (qual=False)
    - barou_shoei: dTQS=-0.0007 CI=[-0.0582, 0.05706] (qual=False) | dTrades=-2 CI=[-0.571, 0.0] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=6.0000 threshold=4.0000
    - clean_windows: 6
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.02, w1:0.19, w2:0.20, w3:0.67!, w4:0.38, w5:0.38, w6:0.40 ('!' = dirty window)
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
- **C1** (pass): stat=0.4274 threshold=0.3000
    - n_trades: 76
    - mean_tqs: 0.4274
    - windows_passing_0.20: 5
    - windows_required: 5
    - per_window_means: {'0': 0.1636, '1': 0.3839, '2': 0.3251, '3': 0.5549, '4': 0.6031, '5': 0.1624, '6': 0.4376}
    - bootstrap_ci95: [0.3097, 0.5535]
    - ci_lower_floor: 0.2500
- **C2** (fail): stat=0.0000 threshold=0.0000
    - qualifying_peers: []
    - isagi_yoichi: dTQS=-0.00205 CI=[-0.03372, 0.02991] (qual=False) | dTrades=-5 CI=[-1.571, -0.143] (qual=False)
    - bachira_meguru: dTQS=0.00069 CI=[-0.02301, 0.02458] (qual=False) | dTrades=-13 CI=[-2.714, -1.0] (qual=False)
    - itoshi_rin: dTQS=-0.00624 CI=[-0.11622, 0.10269] (qual=False) | dTrades=-6 CI=[-1.429, -0.286] (qual=False)
    - chigiri_hyoma: dTQS=0.00065 CI=[-0.06216, 0.06545] (qual=False) | dTrades=-4 CI=[-1.143, -0.143] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - barou_shoei: dTQS=-0.0007 CI=[-0.0582, 0.05706] (qual=False) | dTrades=-2 CI=[-0.571, 0.0] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.02, w1:0.06, w2:0.03, w3:0.03, w4:0.04, w5:0.06, w6:0.00 ('!' = dirty window)
- **C4** (pass): stat=658.0000 threshold=1.0000
    - publish_count: 53164
    - read_count: 658
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.2461 threshold=0.1000
    - n_trades: 76
    - mean_lot: 0.1647
    - min_lot: 0.0800
    - max_lot: 0.2000
    - cv: 0.2461
- **C6** (fail): stat=0.0000 threshold=0.1000
    - n_trades: 76
    - sl_cv: 0.0000
    - tp1_cv: 0.0000
    - mean_sl: 39.0000
    - mean_tp1: 58.5000

### barou_shoei
- **C1** (pass): stat=0.3878 threshold=0.3000
    - n_trades: 322
    - mean_tqs: 0.3878
    - windows_passing_0.20: 7
    - windows_required: 5
    - per_window_means: {'0': 0.3499, '1': 0.457, '2': 0.3228, '3': 0.46, '4': 0.3951, '5': 0.3491, '6': 0.4356}
    - bootstrap_ci95: [0.3464, 0.429]
    - ci_lower_floor: 0.2500
- **C2** (fail): stat=0.0000 threshold=0.0000
    - qualifying_peers: []
    - isagi_yoichi: dTQS=-0.00067 CI=[-0.03274, 0.03101] (qual=False) | dTrades=-19 CI=[-4.143, -1.429] (qual=False)
    - bachira_meguru: dTQS=0.00099 CI=[-0.02287, 0.02432] (qual=False) | dTrades=-34 CI=[-6.714, -3.714] (qual=False)
    - itoshi_rin: dTQS=0.0 CI=[-0.11065, 0.10904] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - chigiri_hyoma: dTQS=0.0 CI=[-0.06232, 0.06208] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=0.0047 CI=[-0.15977, 0.17038] (qual=False) | dTrades=-5 CI=[-1.286, -0.286] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.12, w1:0.04, w2:0.01, w3:0.02, w4:0.09, w5:0.29, w6:0.08 ('!' = dirty window)
- **C4** (pass): stat=4576.0000 threshold=1.0000
    - publish_count: 17722
    - read_count: 4576
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.1508 threshold=0.1000
    - n_trades: 322
    - mean_lot: 0.1643
    - min_lot: 0.0800
    - max_lot: 0.1800
    - cv: 0.1508
- **C6** (pass): stat=0.1834 threshold=0.1000
    - n_trades: 322
    - sl_cv: 0.1834
    - tp1_cv: 0.1834
    - mean_sl: 30.2283
    - mean_tp1: 45.3425

