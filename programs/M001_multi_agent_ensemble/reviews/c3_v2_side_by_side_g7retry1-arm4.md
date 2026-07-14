# C3 v1 vs v2 side-by-side (g7retry1-arm4) -- ADVISORY

Definition: `experiments/c3_v2_distinctness/PROTOCOL.md` (G7 sec 11.14). C3 v1 remains verdict-bearing until the user ratifies the amendment.

- Aggregator arm: `arm4`
- Baseline cache: `programs/M001_multi_agent_ensemble/reviews/g7_replay_cache_g7retry1-arm4`
- lo1 caches: `programs/M001_multi_agent_ensemble/reviews/g7_leave_one_out_g7retry1-arm4/lo1_*`

| Agent | C3 v1 clean | v1 pass | C3 v2 clean | v2 pass | worst-peer lo1 duplicate share |
|---|---|---|---|---|---|
| `isagi_yoichi` | 7/7 | ✅ | 7/7 | ✅ | 36.7% |
| `bachira_meguru` | 3/7 | ❌ | 3/7 | ❌ | 40.1% |
| `itoshi_rin` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |
| `chigiri_hyoma` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |
| `reo_mikage` | 6/7 | ✅ | 6/7 | ✅ | 0.0% |
| `nagi_seishiro` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |
| `barou_shoei` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |

## Per-agent v2 windows + duplicate shares

### isagi_yoichi
- v1 worst reductions: w0:0.18, w1:0.19, w2:0.18, w3:0.26, w4:0.18, w5:0.15, w6:0.17
- v2 worst reductions: w0:0.11, w1:0.10, w2:0.13, w3:0.09, w4:0.07, w5:0.08, w6:0.08
- bachira_meguru: lo1 922/2515 duplicates (36.7%); baseline 491/2035

### bachira_meguru
- v1 worst reductions: w0:0.54!, w1:0.65!, w2:0.61!, w3:0.50, w4:0.41, w5:0.45, w6:0.54!
- v2 worst reductions: w0:0.54!, w1:0.65!, w2:0.61!, w3:0.50, w4:0.41, w5:0.45, w6:0.54!
- isagi_yoichi: lo1 485/1209 duplicates (40.1%); baseline 491/1122

### itoshi_rin
- v1 worst reductions: w0:0.05, w1:0.15, w2:0.08, w3:0.25, w4:0.12, w5:0.11, w6:0.14
- v2 worst reductions: w0:0.05, w1:0.15, w2:0.08, w3:0.25, w4:0.12, w5:0.11, w6:0.14

### chigiri_hyoma
- v1 worst reductions: w0:0.20, w1:0.07, w2:0.03, w3:0.03, w4:0.06, w5:0.03, w6:0.09
- v2 worst reductions: w0:0.20, w1:0.07, w2:0.03, w3:0.03, w4:0.06, w5:0.03, w6:0.09

### reo_mikage
- v1 worst reductions: w0:0.01, w1:0.19, w2:0.20, w3:0.67!, w4:0.31, w5:0.25, w6:0.40
- v2 worst reductions: w0:0.01, w1:0.19, w2:0.20, w3:0.67!, w4:0.31, w5:0.25, w6:0.40

### nagi_seishiro
- v1 worst reductions: w0:0.01, w1:0.06, w2:0.03, w3:0.03, w4:0.04, w5:0.06, w6:0.00
- v2 worst reductions: w0:0.01, w1:0.06, w2:0.03, w3:0.03, w4:0.04, w5:0.06, w6:0.00

### barou_shoei
- v1 worst reductions: w0:0.03, w1:0.01, w2:0.01, w3:0.02, w4:0.05, w5:0.14, w6:0.08
- v2 worst reductions: w0:0.03, w1:0.01, w2:0.01, w3:0.02, w4:0.05, w5:0.14, w6:0.08

