# C3 v1 vs v2 side-by-side (g7retry2-phi41) -- ADVISORY

Definition: `experiments/c3_v2_distinctness/PROTOCOL.md` (G7 sec 11.14). C3 v1 remains verdict-bearing until the user ratifies the amendment.

- Aggregator arm: `phi41`
- Baseline cache: `programs/M001_multi_agent_ensemble/reviews/g7_replay_cache_g7retry2-phi41`
- lo1 caches: `programs/M001_multi_agent_ensemble/reviews/g7_leave_one_out_g7retry2-phi41/lo1_*`

| Agent | C3 v1 clean | v1 pass | C3 v2 clean | v2 pass | worst-peer lo1 duplicate share |
|---|---|---|---|---|---|
| `isagi_yoichi` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |
| `bachira_meguru` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |
| `itoshi_rin` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |
| `chigiri_hyoma` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |
| `reo_mikage` | 6/7 | ✅ | 6/7 | ✅ | 0.0% |
| `nagi_seishiro` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |
| `barou_shoei` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |

## Per-agent v2 windows + duplicate shares

### isagi_yoichi
- v1 worst reductions: w0:0.26, w1:0.11, w2:0.12, w3:0.11, w4:0.13, w5:0.12, w6:0.15
- v2 worst reductions: w0:0.26, w1:0.11, w2:0.12, w3:0.11, w4:0.13, w5:0.12, w6:0.15

### bachira_meguru
- v1 worst reductions: w0:0.08, w1:0.07, w2:0.06, w3:0.06, w4:0.06, w5:0.09, w6:0.09
- v2 worst reductions: w0:0.08, w1:0.07, w2:0.06, w3:0.06, w4:0.06, w5:0.09, w6:0.09

### itoshi_rin
- v1 worst reductions: w0:0.10, w1:0.18, w2:0.17, w3:0.35, w4:0.17, w5:0.17, w6:0.18
- v2 worst reductions: w0:0.10, w1:0.18, w2:0.17, w3:0.35, w4:0.17, w5:0.17, w6:0.18

### chigiri_hyoma
- v1 worst reductions: w0:0.17, w1:0.13, w2:0.17, w3:0.50, w4:0.33, w5:0.09, w6:0.07
- v2 worst reductions: w0:0.17, w1:0.13, w2:0.17, w3:0.50, w4:0.33, w5:0.09, w6:0.07

### reo_mikage
- v1 worst reductions: w0:0.09, w1:0.01, w2:0.01, w3:0.67!, w4:0.03, w5:0.00, w6:0.02
- v2 worst reductions: w0:0.09, w1:0.01, w2:0.01, w3:0.67!, w4:0.03, w5:0.00, w6:0.02

### nagi_seishiro
- v1 worst reductions: w0:0.09, w1:0.01, w2:0.01, w3:0.02, w4:0.01, w5:0.00, w6:0.00
- v2 worst reductions: w0:0.09, w1:0.01, w2:0.01, w3:0.02, w4:0.01, w5:0.00, w6:0.00

### barou_shoei
- v1 worst reductions: w0:0.23, w1:0.07, w2:0.11, w3:0.50, w4:0.13, w5:0.17, w6:0.09
- v2 worst reductions: w0:0.23, w1:0.07, w2:0.11, w3:0.50, w4:0.13, w5:0.17, w6:0.09

