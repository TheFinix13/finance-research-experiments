# G7 leave-one-out C2/C3 verdict (phi5-arm4)

Generated 2026-07-06T18:38:19.641130+00:00 from baseline + 7 leave-one-out replays.

## Baseline per-agent stats (all 8 agents present)

| Agent | N trades | Mean TQS |
|---|---:|---:|
| `isagi_yoichi` | 2139 | 0.3539 |
| `bachira_meguru` | 3546 | 0.3953 |
| `itoshi_rin` | 436 | 0.3952 |
| `chigiri_hyoma` | 437 | 0.2617 |
| `reo_mikage` | 0 | 0.0000 |
| `nagi_seishiro` | 148 | 0.4162 |
| `barou_shoei` | 567 | 0.3944 |
| `kunigami_rensuke` | 0 | 0.0000 |

## Criterion 2 (positive-sum chemistry) per agent

For each excluded agent X, we ask: does removing X hurt at least one peer? An epsilon-strict positive delta on peer mean-TQS OR trade count when X is present vs absent = **C2 PASS**.

| Excluded | C2 pass? | Reason |
|---|:---:|---|
| `isagi_yoichi` | ✅ | peer 'chigiri_hyoma' lifted by presence: delta_tqs=+0.0109 delta_trades=-40.0 (strongest on tqs, 2.2x epsilon) |
| `bachira_meguru` | ✅ | peer 'nagi_seishiro' lifted by presence: delta_tqs=+0.1806 delta_trades=+104.0 (strongest on trades, 104.0x epsilon) |
| `itoshi_rin` | ✅ | peer 'nagi_seishiro' lifted by presence: delta_tqs=+0.0624 delta_trades=+90.0 (strongest on trades, 90.0x epsilon) |
| `chigiri_hyoma` | ✅ | peer 'nagi_seishiro' lifted by presence: delta_tqs=-0.0036 delta_trades=+3.0 (strongest on trades, 3.0x epsilon) |
| `reo_mikage` | ✅ | peer 'itoshi_rin' lifted by presence: delta_tqs=+0.0182 delta_trades=+33.0 (strongest on trades, 33.0x epsilon) |
| `nagi_seishiro` | ❌ | no peer lifted by more than epsilon (tqs>0.005, trades>1.0); best lift on 'bachira_meguru' at 0.097 epsilon-units |
| `barou_shoei` | ❌ | no peer lifted by more than epsilon (tqs>0.005, trades>1.0); best lift on 'nagi_seishiro' at 0.881 epsilon-units |
| `kunigami_rensuke` | ⏸ | leave-one-out cache missing |

## Criterion 3 (non-cannibalising slot behaviour)

Worst per-peer trade-count reduction ratio caused by the excluded agent's presence. Threshold = 50% (peer trading more than 50% more when excluded agent is absent = **C3 FAIL** for that agent -- structural cannibalisation).

| Excluded | Worst peer | Reduction | C3 pass? |
|---|---|---:|:---:|
| `isagi_yoichi` | `barou_shoei` | 29.7% | ✅ |
| `bachira_meguru` | `barou_shoei` | 55.7% | ❌ |
| `itoshi_rin` | `isagi_yoichi` | 15.0% | ✅ |
| `chigiri_hyoma` | `itoshi_rin` | 3.5% | ✅ |
| `reo_mikage` | `nagi_seishiro` | 47.9% | ✅ |
| `nagi_seishiro` | `itoshi_rin` | 1.8% | ✅ |
| `barou_shoei` | `nagi_seishiro` | 2.6% | ✅ |
| `kunigami_rensuke` | -- | -- | ⏸ |

## Per-peer delta tables (audit-grade)

For each excluded agent X, delta[p] = baseline[p].{tqs, n_trades} - lo1_without_X[p].{tqs, n_trades}. Positive delta means "X's presence lifts peer p".

### Excluded: `isagi_yoichi`

| Peer | Δ n_trades | Δ mean_tqs |
|---|---:|---:|
| `bachira_meguru` | -1042.0 | +0.0069 |
| `itoshi_rin` | -8.0 | -0.0046 |
| `chigiri_hyoma` | -40.0 | +0.0109 |
| `reo_mikage` | +0.0 | +0.0000 |
| `nagi_seishiro` | -4.0 | +0.0097 |
| `barou_shoei` | -240.0 | +0.0026 |
| `kunigami_rensuke` | +0.0 | +0.0000 |

### Excluded: `bachira_meguru`

| Peer | Δ n_trades | Δ mean_tqs |
|---|---:|---:|
| `isagi_yoichi` | -129.0 | +0.0001 |
| `itoshi_rin` | -59.0 | -0.0298 |
| `chigiri_hyoma` | -36.0 | +0.0051 |
| `reo_mikage` | +0.0 | +0.0000 |
| `nagi_seishiro` | +104.0 | +0.1806 |
| `barou_shoei` | -713.0 | -0.0034 |
| `kunigami_rensuke` | +0.0 | +0.0000 |

### Excluded: `itoshi_rin`

| Peer | Δ n_trades | Δ mean_tqs |
|---|---:|---:|
| `isagi_yoichi` | -378.0 | -0.0010 |
| `bachira_meguru` | -214.0 | +0.0028 |
| `chigiri_hyoma` | -17.0 | -0.0053 |
| `reo_mikage` | +0.0 | +0.0000 |
| `nagi_seishiro` | +90.0 | +0.0624 |
| `barou_shoei` | +0.0 | +0.0000 |
| `kunigami_rensuke` | +0.0 | +0.0000 |

### Excluded: `chigiri_hyoma`

| Peer | Δ n_trades | Δ mean_tqs |
|---|---:|---:|
| `isagi_yoichi` | -49.0 | -0.0010 |
| `bachira_meguru` | -128.0 | +0.0000 |
| `itoshi_rin` | -16.0 | -0.0072 |
| `reo_mikage` | +0.0 | +0.0000 |
| `nagi_seishiro` | +3.0 | -0.0036 |
| `barou_shoei` | +0.0 | +0.0000 |
| `kunigami_rensuke` | +0.0 | +0.0000 |

### Excluded: `reo_mikage`

| Peer | Δ n_trades | Δ mean_tqs |
|---|---:|---:|
| `isagi_yoichi` | +9.0 | -0.0002 |
| `bachira_meguru` | +24.0 | +0.0001 |
| `itoshi_rin` | +33.0 | +0.0182 |
| `chigiri_hyoma` | +16.0 | -0.0020 |
| `nagi_seishiro` | -136.0 | +0.0504 |
| `barou_shoei` | -4.0 | -0.0003 |
| `kunigami_rensuke` | +0.0 | +0.0000 |

### Excluded: `nagi_seishiro`

| Peer | Δ n_trades | Δ mean_tqs |
|---|---:|---:|
| `isagi_yoichi` | -9.0 | -0.0004 |
| `bachira_meguru` | -29.0 | +0.0005 |
| `itoshi_rin` | -8.0 | -0.0023 |
| `chigiri_hyoma` | -6.0 | -0.0038 |
| `reo_mikage` | +0.0 | +0.0000 |
| `barou_shoei` | -4.0 | -0.0003 |
| `kunigami_rensuke` | +0.0 | +0.0000 |

### Excluded: `barou_shoei`

| Peer | Δ n_trades | Δ mean_tqs |
|---|---:|---:|
| `isagi_yoichi` | -40.0 | +0.0012 |
| `bachira_meguru` | -64.0 | +0.0011 |
| `itoshi_rin` | +0.0 | +0.0000 |
| `chigiri_hyoma` | +0.0 | +0.0000 |
| `reo_mikage` | +0.0 | +0.0000 |
| `nagi_seishiro` | -4.0 | +0.0044 |
| `kunigami_rensuke` | +0.0 | +0.0000 |
