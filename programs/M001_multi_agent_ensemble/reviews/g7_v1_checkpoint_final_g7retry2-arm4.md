# G7 v1 Checkpoint Gate -- FINAL verdict (g7retry2-arm4)

**Squad verdict: FAIL** (4/7 agents pass all six criteria)

- Aggregator arm: `arm4`
- Baseline cache: `programs/M001_multi_agent_ensemble/reviews/g7_replay_cache_g7retry2-arm4`
- Leave-one-out caches: `programs/M001_multi_agent_ensemble/reviews/g7_leave_one_out_g7retry2-arm4/lo1_*`
- Bootstrap: n=10000, seed=42, percentile CI, alpha=0.05
- Windows: 7 rolling OOS (2019..2025)

## Per-agent 6-bit vectors

| Agent | Playstyle | Bit vector | C1 | C2 | C3 | C4 | C5 | C6 | v1 pass? |
|---|---|---|---|---|---|---|---|---|---|
| `isagi_yoichi` | conservative_metavision | `111111` | ✅ 0.365 | ✅ -0.027 | ✅ 7.000 | ✅ 6571.000 | ✅ 0.196 | ✅ 0.188 | YES |
| `bachira_meguru` | rebel_tight | `111111` | ✅ 0.388 | ✅ 0.035 | ✅ 7.000 | ✅ 3620.000 | ✅ 0.474 | ✅ 0.156 | YES |
| `itoshi_rin` | analytical_precision | `111111` | ✅ 0.376 | ✅ 0.094 | ✅ 7.000 | ✅ 2988.000 | ✅ 0.113 | ✅ 0.219 | YES |
| `chigiri_hyoma` | speed_momentum | `001111` | ❌ 0.239 | ❌ 0.000 | ✅ 7.000 | ✅ 1231.000 | ✅ 0.119 | ✅ 0.164 | no |
| `reo_mikage` | copier_hrp | `W11WWW` | W | ✅ -0.104 | ✅ 7.000 | W | W | W | YES |
| `nagi_seishiro` | confluence_only | `001111` | ❌ 0.167 | ❌ 0.000 | ✅ 7.000 | ✅ 208.000 | ✅ 0.226 | ✅ 0.176 | no |
| `barou_shoei` | solo_king | `101111` | ✅ 0.402 | ❌ 0.000 | ✅ 7.000 | ✅ 6793.000 | ✅ 0.292 | ✅ 0.171 | no |

Legend: `1` pass / `0` fail / `W` waived (structural falsifier, sec 11.1) / `?` pending. Cell numbers are the criterion statistic (C1 mean TQS; C2 strongest qualifying delta; C3 clean windows; C4 min(publish, read); C5/C6 CV).

## ADVISORY -- C2 finisher clause (Lever D, pending ratification)

Advisory squad verdict WITH the clause: **FAIL** (4/7). The verdict-bearing numbers above are unaffected.

- `nagi_seishiro` (confluence_only): W (clause pass) -- 4 qualified incoming lift(s) ['bachira_meguru', 'isagi_yoichi', 'itoshi_rin', 'reo_mikage'] (need >= 2)

## Notes

- All statistics OOS-only (union of the 7 rolling OOS windows); differs from the diagnostic lo1 verdicts which pooled IS+OOS.
- C4 evaluated on panel-wide publish/read counters (per-window counts not persisted in caches; documented harness limitation).
- C5/C6 recomputed from cached source_* trade fields via the pure playstyle-dispatched F19/F20 primitives (no agent overrides exist).
- C2 finisher clause evaluated ADVISORY-ONLY (experiments/c2_finisher_clause/PROTOCOL.md, pending user ratification); verdict-bearing bit vectors and squad verdict are computed without it.

## Per-criterion evidence

### isagi_yoichi
- **C1** (pass): stat=0.3645 threshold=0.3000
    - n_trades: 1100
    - mean_tqs: 0.3645
    - windows_passing_0.20: 7
    - windows_required: 5
    - per_window_means: {'0': 0.3955, '1': 0.3553, '2': 0.3512, '3': 0.359, '4': 0.3652, '5': 0.3817, '6': 0.3458}
    - bootstrap_ci95: [0.3412, 0.3873]
    - ci_lower_floor: 0.2500
- **C2** (pass): stat=-0.0272 threshold=0.0000
    - qualifying_peers: ['nagi_seishiro']
    - bachira_meguru: dTQS=0.00457 CI=[-0.03533, 0.0434] (qual=False) | dTrades=-32 CI=[-7.857, -1.571] (qual=False)
    - itoshi_rin: dTQS=0.00114 CI=[-0.10576, 0.11276] (qual=False) | dTrades=-1 CI=[-0.429, 0.0] (qual=False)
    - chigiri_hyoma: dTQS=-0.00099 CI=[-0.04737, 0.04484] (qual=False) | dTrades=+0 CI=[-0.429, 0.429] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=-0.0272 CI=[-0.31429, 0.23312] (qual=False) | dTrades=+11 CI=[0.857, 2.286] (qual=True)
    - barou_shoei: dTQS=0.00064 CI=[-0.0544, 0.05648] (qual=False) | dTrades=-72 CI=[-14.143, -7.714] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.21, w1:0.11, w2:0.12, w3:0.11, w4:0.11, w5:0.12, w6:0.14 ('!' = dirty window)
- **C4** (pass): stat=6571.0000 threshold=1.0000
    - publish_count: 53163
    - read_count: 6571
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.1960 threshold=0.1000
    - n_trades: 1100
    - mean_lot: 0.1765
    - min_lot: 0.0900
    - max_lot: 0.2000
    - cv: 0.1960
- **C6** (pass): stat=0.1880 threshold=0.1000
    - n_trades: 1100
    - sl_cv: 0.1880
    - tp1_cv: 0.1880
    - mean_sl: 41.5970
    - mean_tp1: 62.3955

### bachira_meguru
- **C1** (pass): stat=0.3884 threshold=0.3000
    - n_trades: 764
    - mean_tqs: 0.3884
    - windows_passing_0.20: 7
    - windows_required: 5
    - per_window_means: {'0': 0.3925, '1': 0.3539, '2': 0.3229, '3': 0.4385, '4': 0.4321, '5': 0.3857, '6': 0.4223}
    - bootstrap_ci95: [0.3609, 0.4163]
    - ci_lower_floor: 0.2500
- **C2** (pass): stat=0.0346 threshold=0.0000
    - qualifying_peers: ['nagi_seishiro']
    - isagi_yoichi: dTQS=-0.00111 CI=[-0.03297, 0.03034] (qual=False) | dTrades=-44 CI=[-8.571, -3.714] (qual=False)
    - itoshi_rin: dTQS=-0.01388 CI=[-0.12132, 0.09712] (qual=False) | dTrades=-5 CI=[-1.429, 0.0] (qual=False)
    - chigiri_hyoma: dTQS=0.00221 CI=[-0.04373, 0.04776] (qual=False) | dTrades=-5 CI=[-1.714, 0.286] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=0.03462 CI=[-0.30083, 0.29669] (qual=False) | dTrades=+14 CI=[1.143, 2.714] (qual=True)
    - barou_shoei: dTQS=-0.00258 CI=[-0.05871, 0.05434] (qual=False) | dTrades=-24 CI=[-4.143, -2.857] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.06, w1:0.04, w2:0.05, w3:0.06, w4:0.06, w5:0.08, w6:0.08 ('!' = dirty window)
- **C4** (pass): stat=3620.0000 threshold=1.0000
    - publish_count: 53163
    - read_count: 3620
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.4741 threshold=0.1000
    - n_trades: 764
    - mean_lot: 0.0534
    - min_lot: 0.0200
    - max_lot: 0.1100
    - cv: 0.4741
- **C6** (pass): stat=0.1559 threshold=0.1000
    - n_trades: 764
    - sl_cv: 0.1559
    - tp1_cv: 0.1559
    - mean_sl: 22.0085
    - mean_tp1: 66.0254

### itoshi_rin
- **C1** (pass): stat=0.3763 threshold=0.3000
    - n_trades: 213
    - mean_tqs: 0.3763
    - windows_passing_0.20: 7
    - windows_required: 5
    - per_window_means: {'0': 0.2445, '1': 0.2908, '2': 0.3135, '3': 0.4536, '4': 0.3034, '5': 0.4366, '6': 0.4454}
    - bootstrap_ci95: [0.3003, 0.4548]
    - ci_lower_floor: 0.2500
- **C2** (pass): stat=0.0935 threshold=0.0000
    - qualifying_peers: ['nagi_seishiro']
    - isagi_yoichi: dTQS=0.00293 CI=[-0.0293, 0.03434] (qual=False) | dTrades=-164 CI=[-37.571, -13.286] (qual=False)
    - bachira_meguru: dTQS=0.00535 CI=[-0.03483, 0.04471] (qual=False) | dTrades=-22 CI=[-4.714, -1.571] (qual=False)
    - chigiri_hyoma: dTQS=0.00108 CI=[-0.04375, 0.04617] (qual=False) | dTrades=-7 CI=[-1.857, -0.286] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=0.09355 CI=[-0.08787, 0.29124] (qual=False) | dTrades=+8 CI=[0.571, 1.714] (qual=True)
    - barou_shoei: dTQS=-4e-05 CI=[-0.05598, 0.05762] (qual=False) | dTrades=-16 CI=[-4.0, -0.857] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.04, w1:0.15, w2:0.07, w3:0.24, w4:0.12, w5:0.11, w6:0.11 ('!' = dirty window)
- **C4** (pass): stat=2988.0000 threshold=1.0000
    - publish_count: 17723
    - read_count: 2988
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.1133 threshold=0.1000
    - n_trades: 213
    - mean_lot: 0.0886
    - min_lot: 0.0700
    - max_lot: 0.1100
    - cv: 0.1133
- **C6** (pass): stat=0.2191 threshold=0.1000
    - n_trades: 213
    - sl_cv: 0.2191
    - tp1_cv: 0.2191
    - mean_sl: 29.6191
    - mean_tp1: 59.2381

### chigiri_hyoma
- **C1** (fail): stat=0.2388 threshold=0.3000
    - n_trades: 514
    - mean_tqs: 0.2388
    - windows_passing_0.20: 6
    - windows_required: 5
    - per_window_means: {'0': 0.2445, '1': 0.256, '2': 0.2147, '3': 0.2967, '4': 0.1713, '5': 0.2632, '6': 0.2271}
    - bootstrap_ci95: [0.2074, 0.2716]
    - ci_lower_floor: 0.2500
- **C2** (fail): stat=0.0000 threshold=0.0000
    - qualifying_peers: []
    - isagi_yoichi: dTQS=0.00422 CI=[-0.02857, 0.03607] (qual=False) | dTrades=-47 CI=[-8.571, -4.714] (qual=False)
    - bachira_meguru: dTQS=0.00354 CI=[-0.03618, 0.04271] (qual=False) | dTrades=-26 CI=[-7.143, -0.857] (qual=False)
    - itoshi_rin: dTQS=-0.01905 CI=[-0.12946, 0.09129] (qual=False) | dTrades=-19 CI=[-4.286, -1.286] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=-0.09301 CI=[-0.34748, 0.16459] (qual=False) | dTrades=-2 CI=[-0.857, 0.0] (qual=False)
    - barou_shoei: dTQS=-0.00364 CI=[-0.06099, 0.0539] (qual=False) | dTrades=-7 CI=[-2.286, 0.286] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.08, w1:0.09, w2:0.19, w3:0.33, w4:0.09, w5:0.06, w6:0.06 ('!' = dirty window)
- **C4** (pass): stat=1231.0000 threshold=1.0000
    - publish_count: 35441
    - read_count: 1231
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.1187 threshold=0.1000
    - n_trades: 514
    - mean_lot: 0.1958
    - min_lot: 0.1500
    - max_lot: 0.2400
    - cv: 0.1187
- **C6** (pass): stat=0.1644 threshold=0.1000
    - n_trades: 514
    - sl_cv: 0.1644
    - tp1_cv: 0.1644
    - mean_sl: 35.5362
    - mean_tp1: 106.6087

### reo_mikage
- **C1** (waived): stat=53163.0000 threshold=0.0000
    - reason: structural falsifier waiver (sec 11.1) -- intend() returns None by design; earns v1 through publishing
    - publish_count: 53163
- **C2** (pass): stat=-0.1038 threshold=0.0000
    - qualifying_peers: ['nagi_seishiro']
    - isagi_yoichi: dTQS=-0.00059 CI=[-0.03305, 0.03106] (qual=False) | dTrades=-3 CI=[-1.0, 0.0] (qual=False)
    - bachira_meguru: dTQS=0.00263 CI=[-0.03782, 0.04212] (qual=False) | dTrades=+0 CI=[-0.571, 0.571] (qual=False)
    - itoshi_rin: dTQS=0.0 CI=[-0.1079, 0.11187] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - chigiri_hyoma: dTQS=0.0 CI=[-0.0452, 0.04537] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=-0.10377 CI=[-0.50823, 0.24314] (qual=False) | dTrades=+16 CI=[0.286, 4.143] (qual=True)
    - barou_shoei: dTQS=0.00144 CI=[-0.05489, 0.0579] (qual=False) | dTrades=-3 CI=[-1.0, 0.0] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.01, w1:0.00, w2:0.01, w3:0.33, w4:0.03, w5:0.00, w6:0.02 ('!' = dirty window)
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
- **C1** (fail): stat=0.1668 threshold=0.3000
    - n_trades: 25
    - mean_tqs: 0.1668
    - windows_passing_0.20: 2
    - windows_required: 5
    - per_window_means: {'0': 0.0, '1': 0.0, '2': 0.3207, '3': 0.5615, '4': 0.0, '5': 0.0, '6': 0.0}
    - bootstrap_ci95: [0.0188, 0.3465]
    - ci_lower_floor: 0.2500
- **C2** (fail): stat=0.0000 threshold=0.0000
    - qualifying_peers: []
    - isagi_yoichi: dTQS=-0.00059 CI=[-0.03305, 0.03106] (qual=False) | dTrades=-3 CI=[-1.0, 0.0] (qual=False)
    - bachira_meguru: dTQS=0.0029 CI=[-0.03745, 0.04214] (qual=False) | dTrades=-4 CI=[-0.857, -0.143] (qual=False)
    - itoshi_rin: dTQS=0.0 CI=[-0.1079, 0.11187] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - chigiri_hyoma: dTQS=0.0 CI=[-0.0452, 0.04537] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - barou_shoei: dTQS=-4e-05 CI=[-0.05741, 0.05664] (qual=False) | dTrades=-2 CI=[-0.571, 0.0] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.01, w1:0.00, w2:0.01, w3:0.02, w4:0.01, w5:0.00, w6:0.00 ('!' = dirty window)
- **C4** (pass): stat=208.0000 threshold=1.0000
    - publish_count: 53163
    - read_count: 208
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.2263 threshold=0.1000
    - n_trades: 25
    - mean_lot: 0.1608
    - min_lot: 0.1000
    - max_lot: 0.2000
    - cv: 0.2263
- **C6** (pass): stat=0.1763 threshold=0.1000
    - n_trades: 25
    - sl_cv: 0.1763
    - tp1_cv: 0.1763
    - mean_sl: 35.0645
    - mean_tp1: 52.5967

### barou_shoei
- **C1** (pass): stat=0.4016 threshold=0.3000
    - n_trades: 458
    - mean_tqs: 0.4016
    - windows_passing_0.20: 7
    - windows_required: 5
    - per_window_means: {'0': 0.3263, '1': 0.4094, '2': 0.4674, '3': 0.4572, '4': 0.5233, '5': 0.3277, '6': 0.2773}
    - bootstrap_ci95: [0.3617, 0.4418]
    - ci_lower_floor: 0.2500
- **C2** (fail): stat=0.0000 threshold=0.0000
    - qualifying_peers: []
    - isagi_yoichi: dTQS=0.00171 CI=[-0.03021, 0.03386] (qual=False) | dTrades=-87 CI=[-15.571, -9.0] (qual=False)
    - bachira_meguru: dTQS=-0.00051 CI=[-0.03924, 0.03872] (qual=False) | dTrades=-60 CI=[-12.143, -5.0] (qual=False)
    - itoshi_rin: dTQS=-0.00282 CI=[-0.11104, 0.1055] (qual=False) | dTrades=-8 CI=[-2.286, 0.0] (qual=False)
    - chigiri_hyoma: dTQS=-0.00187 CI=[-0.04782, 0.04299] (qual=False) | dTrades=-21 CI=[-4.286, -2.0] (qual=False)
    - reo_mikage: dTQS=None CI=[nan, nan] (qual=False) | dTrades=+0 CI=[0.0, 0.0] (qual=False)
    - nagi_seishiro: dTQS=-0.00827 CI=[-0.2491, 0.22705] (qual=False) | dTrades=+1 CI=[-0.714, 1.0] (qual=False)
    - rule: exists peer with (delta_tqs > 0 AND bootstrap CI lower > 0) OR (delta_trades > 0 AND window-bootstrap CI lower > 0); alpha=0.05
- **C3** (pass): stat=7.0000 threshold=4.0000
    - clean_windows: 7
    - windows_required: 4
    - max_reduction_threshold: 0.5000
    - per_window worst reductions: w0:0.18, w1:0.07, w2:0.08, w3:0.33, w4:0.14, w5:0.12, w6:0.07 ('!' = dirty window)
- **C4** (pass): stat=6793.0000 threshold=1.0000
    - publish_count: 53163
    - read_count: 6793
    - note: single-window dry-run; PROTOCOL sec 3 requires both > 0 in >= 7/7 windows for full-panel verdict
- **C5** (pass): stat=0.2916 threshold=0.1000
    - n_trades: 458
    - mean_lot: 0.0954
    - min_lot: 0.0600
    - max_lot: 0.1800
    - cv: 0.2916
- **C6** (pass): stat=0.1715 threshold=0.1000
    - n_trades: 458
    - sl_cv: 0.1715
    - tp1_cv: 0.1715
    - mean_sl: 31.0520
    - mean_tp1: 46.5780

