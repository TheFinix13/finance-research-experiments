# G7 leave-one-out C2/C3 verdict (post-V)

Generated 2026-07-03T07:14:38.564349+00:00 from baseline + 8 leave-one-out replays.

## Baseline per-agent stats (all 8 agents present)

| Agent | N trades | Mean TQS |
|---|---:|---:|
| `isagi_yoichi` | 1923 | 0.3568 |
| `bachira_meguru` | 2542 | 0.4026 |
| `itoshi_rin` | 421 | 0.3940 |
| `chigiri_hyoma` | 430 | 0.2585 |
| `reo_mikage` | 0 | 0.0000 |
| `nagi_seishiro` | 135 | 0.4313 |
| `barou_shoei` | 153 | 0.3469 |
| `kunigami_rensuke` | 0 | 0.0000 |

## Criterion 2 (positive-sum chemistry) per agent

For each excluded agent X, we ask: does removing X hurt at least one peer? An epsilon-strict positive delta on peer mean-TQS OR trade count when X is present vs absent = **C2 PASS**.

| Excluded | C2 pass? | Reason |
|---|:---:|---|
| `isagi_yoichi` | ✅ | peer 'bachira_meguru' lifted by presence: delta_tqs=+0.0133 delta_trades=-1823.0 (strongest on tqs, 2.7x epsilon) |
| `bachira_meguru` | ✅ | peer 'nagi_seishiro' lifted by presence: delta_tqs=+0.1979 delta_trades=+94.0 (strongest on trades, 94.0x epsilon) |
| `itoshi_rin` | ✅ | peer 'nagi_seishiro' lifted by presence: delta_tqs=+0.0886 delta_trades=+83.0 (strongest on trades, 83.0x epsilon) |
| `chigiri_hyoma` | ✅ | peer 'nagi_seishiro' lifted by presence: delta_tqs=-0.0110 delta_trades=+5.0 (strongest on trades, 5.0x epsilon) |
| `reo_mikage` | ✅ | peer 'itoshi_rin' lifted by presence: delta_tqs=+0.0142 delta_trades=+45.0 (strongest on trades, 45.0x epsilon) |
| `nagi_seishiro` | ❌ | no peer lifted by more than epsilon (tqs>0.005, trades>1.0); best lift on 'barou_shoei' at 0.292 epsilon-units |
| `barou_shoei` | ❌ | no peer lifted by more than epsilon (tqs>0.005, trades>1.0); best lift on 'isagi_yoichi' at 0.502 epsilon-units |
| `kunigami_rensuke` | ❌ | no peer lifted by more than epsilon (tqs>0.005, trades>1.0); best lift on None at 0.000 epsilon-units |

## Criterion 3 (non-cannibalising slot behaviour)

Worst per-peer trade-count reduction ratio caused by the excluded agent's presence. Threshold = 50% (peer trading more than 50% more when excluded agent is absent = **C3 FAIL** for that agent -- structural cannibalisation).

| Excluded | Worst peer | Reduction | C3 pass? |
|---|---|---:|:---:|
| `isagi_yoichi` | `bachira_meguru` | 41.8% | ✅ |
| `bachira_meguru` | `barou_shoei` | 84.1% | ❌ |
| `itoshi_rin` | `isagi_yoichi` | 21.0% | ✅ |
| `chigiri_hyoma` | `itoshi_rin` | 4.3% | ✅ |
| `reo_mikage` | `nagi_seishiro` | 50.0% | ✅ |
| `nagi_seishiro` | `itoshi_rin` | 3.7% | ✅ |
| `barou_shoei` | `bachira_meguru` | 4.1% | ✅ |
| `kunigami_rensuke` | `--` | 0.0% | ✅ |

## Per-peer delta tables (audit-grade)

For each excluded agent X, delta[p] = baseline[p].{tqs, n_trades} - lo1_without_X[p].{tqs, n_trades}. Positive delta means "X's presence lifts peer p".

### Excluded: `isagi_yoichi`

| Peer | Δ n_trades | Δ mean_tqs |
|---|---:|---:|
| `bachira_meguru` | -1823.0 | +0.0133 |
| `itoshi_rin` | +1.0 | +0.0025 |
| `chigiri_hyoma` | -43.0 | +0.0076 |
| `reo_mikage` | +0.0 | +0.0000 |
| `nagi_seishiro` | -1.0 | +0.0017 |
| `barou_shoei` | +0.0 | +0.0000 |
| `kunigami_rensuke` | +0.0 | +0.0000 |

### Excluded: `bachira_meguru`

| Peer | Δ n_trades | Δ mean_tqs |
|---|---:|---:|
| `isagi_yoichi` | -117.0 | +0.0033 |
| `itoshi_rin` | -57.0 | -0.0242 |
| `chigiri_hyoma` | -32.0 | +0.0008 |
| `reo_mikage` | +0.0 | +0.0000 |
| `nagi_seishiro` | +94.0 | +0.1979 |
| `barou_shoei` | -808.0 | -0.0581 |
| `kunigami_rensuke` | +0.0 | +0.0000 |

### Excluded: `itoshi_rin`

| Peer | Δ n_trades | Δ mean_tqs |
|---|---:|---:|
| `isagi_yoichi` | -511.0 | +0.0000 |
| `bachira_meguru` | -87.0 | +0.0024 |
| `chigiri_hyoma` | -18.0 | -0.0069 |
| `reo_mikage` | +0.0 | +0.0000 |
| `nagi_seishiro` | +83.0 | +0.0886 |
| `barou_shoei` | +0.0 | +0.0000 |
| `kunigami_rensuke` | +0.0 | +0.0000 |

### Excluded: `chigiri_hyoma`

| Peer | Δ n_trades | Δ mean_tqs |
|---|---:|---:|
| `isagi_yoichi` | -53.0 | -0.0013 |
| `bachira_meguru` | -105.0 | +0.0014 |
| `itoshi_rin` | -19.0 | -0.0087 |
| `reo_mikage` | +0.0 | +0.0000 |
| `nagi_seishiro` | +5.0 | -0.0110 |
| `barou_shoei` | +0.0 | +0.0000 |
| `kunigami_rensuke` | +0.0 | +0.0000 |

### Excluded: `reo_mikage`

| Peer | Δ n_trades | Δ mean_tqs |
|---|---:|---:|
| `isagi_yoichi` | +17.0 | +0.0003 |
| `bachira_meguru` | +14.0 | +0.0009 |
| `itoshi_rin` | +45.0 | +0.0142 |
| `chigiri_hyoma` | +15.0 | -0.0034 |
| `nagi_seishiro` | -135.0 | +0.0719 |
| `barou_shoei` | -1.0 | +0.0015 |
| `kunigami_rensuke` | +0.0 | +0.0000 |

### Excluded: `nagi_seishiro`

| Peer | Δ n_trades | Δ mean_tqs |
|---|---:|---:|
| `isagi_yoichi` | -12.0 | +0.0003 |
| `bachira_meguru` | -27.0 | +0.0009 |
| `itoshi_rin` | -16.0 | -0.0080 |
| `chigiri_hyoma` | -7.0 | -0.0033 |
| `reo_mikage` | +0.0 | +0.0000 |
| `barou_shoei` | -1.0 | +0.0015 |
| `kunigami_rensuke` | +0.0 | +0.0000 |

### Excluded: `barou_shoei`

| Peer | Δ n_trades | Δ mean_tqs |
|---|---:|---:|
| `isagi_yoichi` | -37.0 | +0.0025 |
| `bachira_meguru` | -110.0 | +0.0024 |
| `itoshi_rin` | +0.0 | +0.0000 |
| `chigiri_hyoma` | +0.0 | +0.0000 |
| `reo_mikage` | +0.0 | +0.0000 |
| `nagi_seishiro` | -2.0 | -0.0065 |
| `kunigami_rensuke` | +0.0 | +0.0000 |

### Excluded: `kunigami_rensuke`

| Peer | Δ n_trades | Δ mean_tqs |
|---|---:|---:|
| `isagi_yoichi` | +0.0 | +0.0000 |
| `bachira_meguru` | +0.0 | +0.0000 |
| `itoshi_rin` | +0.0 | +0.0000 |
| `chigiri_hyoma` | +0.0 | +0.0000 |
| `reo_mikage` | +0.0 | +0.0000 |
| `nagi_seishiro` | +0.0 | +0.0000 |
| `barou_shoei` | +0.0 | +0.0000 |
