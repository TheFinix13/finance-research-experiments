# C3 v1 vs v2 side-by-side (c3v2-phi41) -- ADVISORY

Definition: `experiments/c3_v2_distinctness/PROTOCOL.md` (G7 sec 11.14). C3 v1 remains verdict-bearing until the user ratifies the amendment.

- Aggregator arm: `phi41`
- Baseline cache: `programs/M001_multi_agent_ensemble/reviews/g7_replay_cache_walk-forward-post-kunigami-retirement`
- lo1 caches: `programs/M001_multi_agent_ensemble/reviews/g7_leave_one_out_post-V/lo1_*`

| Agent | C3 v1 clean | v1 pass | C3 v2 clean | v2 pass | worst-peer lo1 duplicate share |
|---|---|---|---|---|---|
| `isagi_yoichi` | 7/7 | ✅ | 7/7 | ✅ | 34.9% |
| `bachira_meguru` | 0/7 | ❌ | 7/7 | ✅ | 89.1% |
| `itoshi_rin` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |
| `chigiri_hyoma` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |
| `reo_mikage` | 6/7 | ✅ | 6/7 | ✅ | 0.0% |
| `nagi_seishiro` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |
| `barou_shoei` | 7/7 | ✅ | 7/7 | ✅ | 3.1% |

## Per-agent v2 windows + duplicate shares

### isagi_yoichi
- v1 worst reductions: w0:0.41, w1:0.43, w2:0.35, w3:0.39, w4:0.43, w5:0.39, w6:0.41
- v2 worst reductions: w0:0.09, w1:0.10, w2:0.11, w3:0.09, w4:0.09, w5:0.08, w6:0.06
- bachira_meguru: lo1 837/2399 duplicates (34.9%); baseline 0/1444

### bachira_meguru
- v1 worst reductions: w0:0.92!, w1:0.76!, w2:0.97!, w3:0.89!, w4:0.81!, w5:0.90!, w6:0.89!
- v2 worst reductions: w0:0.07, w1:0.18, w2:0.13, w3:0.16, w4:0.11, w5:0.16, w6:0.09
- barou_shoei: lo1 489/549 duplicates (89.1%); baseline 0/62

### itoshi_rin
- v1 worst reductions: w0:0.10, w1:0.18, w2:0.16, w3:0.34, w4:0.16, w5:0.16, w6:0.19
- v2 worst reductions: w0:0.10, w1:0.18, w2:0.16, w3:0.34, w4:0.16, w5:0.16, w6:0.19

### chigiri_hyoma
- v1 worst reductions: w0:0.25, w1:0.07, w2:0.04, w3:0.03, w4:0.10, w5:0.04, w6:0.09
- v2 worst reductions: w0:0.25, w1:0.07, w2:0.04, w3:0.03, w4:0.10, w5:0.04, w6:0.09

### reo_mikage
- v1 worst reductions: w0:0.02, w1:0.19, w2:0.40, w3:0.72!, w4:0.33, w5:0.38, w6:0.41
- v2 worst reductions: w0:0.02, w1:0.19, w2:0.40, w3:0.72!, w4:0.33, w5:0.38, w6:0.41

### nagi_seishiro
- v1 worst reductions: w0:0.02, w1:0.07, w2:0.04, w3:0.08, w4:0.05, w5:0.06, w6:0.01
- v2 worst reductions: w0:0.02, w1:0.07, w2:0.04, w3:0.08, w4:0.05, w5:0.06, w6:0.01

### barou_shoei
- v1 worst reductions: w0:0.01, w1:0.07, w2:0.01, w3:0.03, w4:0.04, w5:0.29, w6:0.05
- v2 worst reductions: w0:0.01, w1:0.01, w2:0.00, w3:0.01, w4:0.04, w5:0.29, w6:0.00
- isagi_yoichi: lo1 1/1019 duplicates (0.1%); baseline 0/1004
- bachira_meguru: lo1 46/1490 duplicates (3.1%); baseline 0/1444

