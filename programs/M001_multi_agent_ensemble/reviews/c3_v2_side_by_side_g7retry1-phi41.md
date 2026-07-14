# C3 v1 vs v2 side-by-side (g7retry1-phi41) -- ADVISORY

Definition: `experiments/c3_v2_distinctness/PROTOCOL.md` (G7 sec 11.14). C3 v1 remains verdict-bearing until the user ratifies the amendment.

- Aggregator arm: `phi41`
- Baseline cache: `programs/M001_multi_agent_ensemble/reviews/g7_replay_cache_g7retry1-phi41`
- lo1 caches: `programs/M001_multi_agent_ensemble/reviews/g7_leave_one_out_g7retry1-phi41/lo1_*`

| Agent | C3 v1 clean | v1 pass | C3 v2 clean | v2 pass | worst-peer lo1 duplicate share |
|---|---|---|---|---|---|
| `isagi_yoichi` | 7/7 | ✅ | 7/7 | ✅ | 34.6% |
| `bachira_meguru` | 0/7 | ❌ | 0/7 | ❌ | 0.0% |
| `itoshi_rin` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |
| `chigiri_hyoma` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |
| `reo_mikage` | 6/7 | ✅ | 6/7 | ✅ | 0.0% |
| `nagi_seishiro` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |
| `barou_shoei` | 7/7 | ✅ | 7/7 | ✅ | 0.0% |

## Per-agent v2 windows + duplicate shares

### isagi_yoichi
- v1 worst reductions: w0:0.41, w1:0.39, w2:0.34, w3:0.38, w4:0.42, w5:0.38, w6:0.39
- v2 worst reductions: w0:0.10, w1:0.10, w2:0.11, w3:0.08, w4:0.09, w5:0.08, w6:0.04
- bachira_meguru: lo1 828/2392 duplicates (34.6%); baseline 0/1468

### bachira_meguru
- v1 worst reductions: w0:0.69!, w1:0.71!, w2:0.91!, w3:0.72!, w4:0.65!, w5:0.77!, w6:0.81!
- v2 worst reductions: w0:0.69!, w1:0.71!, w2:0.91!, w3:0.72!, w4:0.65!, w5:0.77!, w6:0.81!

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
- v1 worst reductions: w0:0.04, w1:0.01, w2:0.00, w3:0.02, w4:0.05, w5:0.29, w6:0.02
- v2 worst reductions: w0:0.04, w1:0.01, w2:0.00, w3:0.02, w4:0.05, w5:0.29, w6:0.02

