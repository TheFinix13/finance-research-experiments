# C3 v1 vs v2 side-by-side (c3v2-arm4) -- ADVISORY

Definition: `experiments/c3_v2_distinctness/PROTOCOL.md` (G7 sec 11.14). C3 v1 remains verdict-bearing until the user ratifies the amendment.

- Aggregator arm: `arm4`
- Baseline cache: `programs/M001_multi_agent_ensemble/reviews/g7_replay_cache_phi5-arm4-post-kunigami`
- lo1 caches: `programs/M001_multi_agent_ensemble/reviews/g7_leave_one_out_phi5-arm4/lo1_*`

| Agent | C3 v1 clean | v1 pass | C3 v2 clean | v2 pass | worst-peer lo1 duplicate share |
|---|---|---|---|---|---|
| `isagi_yoichi` | 7/7 | ✅ | 7/7 | ✅ | 36.5% |
| `bachira_meguru` | 1/7 | ❌ | 7/7 | ✅ | 93.8% |
| `itoshi_rin` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |
| `chigiri_hyoma` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |
| `reo_mikage` | 6/7 | ✅ | 6/7 | ✅ | 0.0% |
| `nagi_seishiro` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |
| `barou_shoei` | 7/7 | ✅ | 7/7 | ✅ | 13.9% |

## Per-agent v2 windows + duplicate shares

### isagi_yoichi
- v1 worst reductions: w0:0.44, w1:0.33, w2:0.22, w3:0.27, w4:0.35, w5:0.21, w6:0.34
- v2 worst reductions: w0:0.12, w1:0.10, w2:0.13, w3:0.09, w4:0.07, w5:0.08, w6:0.05
- bachira_meguru: lo1 925/2536 duplicates (36.5%); baseline 495/2040
- barou_shoei: lo1 167/468 duplicates (35.7%); baseline 0/322

### bachira_meguru
- v1 worst reductions: w0:0.61!, w1:0.62!, w2:0.54!, w3:0.62!, w4:0.56!, w5:0.43, w6:0.53!
- v2 worst reductions: w0:0.12, w1:0.17, w2:0.14, w3:0.12, w4:0.10, w5:0.20, w6:0.12
- isagi_yoichi: lo1 493/1176 duplicates (41.9%); baseline 495/1120
- barou_shoei: lo1 683/728 duplicates (93.8%); baseline 256/322

### itoshi_rin
- v1 worst reductions: w0:0.05, w1:0.15, w2:0.08, w3:0.25, w4:0.12, w5:0.11, w6:0.14
- v2 worst reductions: w0:0.05, w1:0.15, w2:0.08, w3:0.25, w4:0.12, w5:0.11, w6:0.14

### chigiri_hyoma
- v1 worst reductions: w0:0.22, w1:0.07, w2:0.03, w3:0.03, w4:0.06, w5:0.03, w6:0.09
- v2 worst reductions: w0:0.22, w1:0.07, w2:0.03, w3:0.03, w4:0.06, w5:0.03, w6:0.09

### reo_mikage
- v1 worst reductions: w0:0.02, w1:0.19, w2:0.20, w3:0.67!, w4:0.38, w5:0.38, w6:0.40
- v2 worst reductions: w0:0.02, w1:0.19, w2:0.20, w3:0.67!, w4:0.38, w5:0.38, w6:0.40

### nagi_seishiro
- v1 worst reductions: w0:0.02, w1:0.06, w2:0.03, w3:0.03, w4:0.04, w5:0.06, w6:0.00
- v2 worst reductions: w0:0.02, w1:0.06, w2:0.03, w3:0.03, w4:0.04, w5:0.06, w6:0.00

### barou_shoei
- v1 worst reductions: w0:0.12, w1:0.04, w2:0.01, w3:0.02, w4:0.09, w5:0.29, w6:0.08
- v2 worst reductions: w0:0.12, w1:0.01, w2:0.00, w3:0.01, w4:0.09, w5:0.29, w6:0.08
- isagi_yoichi: lo1 1/1139 duplicates (0.1%); baseline 0/1120
- bachira_meguru: lo1 288/2074 duplicates (13.9%); baseline 256/2040

