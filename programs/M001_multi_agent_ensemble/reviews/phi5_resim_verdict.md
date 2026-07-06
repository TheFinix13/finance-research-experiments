# Phi5 Arm 3/4 re-sim verdict (sec 11.4 protocol)

Generated: 2026-07-06T17:41:36.027482+00:00

**Control** `walk-forward-post-kunigami-retirement`: median-of-window-mean TQS = **0.3618** (5604 trades). Legacy refs: phi41 0.2922 / isagi-alone 0.3175 (secondary only).

| Arm | n trades | Median TQS | Delta vs control | CI99 lower | CI pass | Effect pass | DD breach | Verdict |
|---|---:|---:|---:|---:|:--:|:--:|:--:|---|
| arm3 | 5653 | 0.3617 | -0.0001 | 0.3362 | n | n | Y | NULL_NEGATIVE_NOT_SIGNIFICANT |
| arm4 | 7273 | 0.3643 | +0.0025 | 0.3442 | n | n | Y | NULL_POSITIVE_NOT_SIGNIFICANT |

## arm3 (`phi5-arm3-post-kunigami`)

### Cross-statistic robustness (mandatory, sec 4)

| statistic | control | arm |
|---|---:|---:|
| median_window_mean_tqs | 0.3618 | 0.3617 |
| mean_window_mean_tqs | 0.3632 | 0.3598 |
| pooled_per_trade_mean_tqs | 0.3743 | 0.3698 |
| pooled_per_trade_trimmed_mean_tqs_10 | 0.3290 | 0.3279 |
| median_window_mean_pips | 7.3072 | 7.2004 |
| pooled_per_trade_mean_pips | 8.0069 | 7.6633 |
| cumulative_pips_forbidden_as_scoring | 44870.5577 | 43320.5659 |
| hit_rate | 0.5080 | 0.5084 |
| n_trades | 5604 | 5653 |

### Per-agent trades (arm)

| agent | n | mean TQS |
|---|---:|---:|
| `arm3_merged_bachira_meguru+barou_shoei` | 966 | 0.3978 |
| `arm3_merged_bachira_meguru+barou_shoei+isagi_yoichi` | 588 | 0.3619 |
| `arm3_merged_bachira_meguru+barou_shoei+isagi_yoichi+nagi_seishiro` | 2 | 0.0000 |
| `arm3_merged_bachira_meguru+barou_shoei+nagi_seishiro` | 12 | 0.0787 |
| `arm3_merged_bachira_meguru+chigiri_hyoma` | 87 | 0.3681 |
| `arm3_merged_bachira_meguru+chigiri_hyoma+isagi_yoichi` | 2 | 1.1065 |
| `arm3_merged_bachira_meguru+chigiri_hyoma+isagi_yoichi+itoshi_rin` | 3 | 0.0000 |
| `arm3_merged_bachira_meguru+chigiri_hyoma+isagi_yoichi+itoshi_rin+nagi_seishiro` | 5 | 1.1164 |
| `arm3_merged_bachira_meguru+chigiri_hyoma+nagi_seishiro` | 5 | 0.0000 |
| `arm3_merged_bachira_meguru+isagi_yoichi` | 992 | 0.3868 |
| `arm3_merged_bachira_meguru+isagi_yoichi+itoshi_rin` | 357 | 0.4130 |
| `arm3_merged_bachira_meguru+isagi_yoichi+itoshi_rin+nagi_seishiro` | 48 | 0.2974 |
| `arm3_merged_bachira_meguru+isagi_yoichi+nagi_seishiro` | 13 | 0.5451 |
| `arm3_merged_bachira_meguru+nagi_seishiro` | 24 | 0.2877 |
| `arm3_merged_chigiri_hyoma+isagi_yoichi+itoshi_rin` | 1 | 0.0000 |
| `arm3_merged_chigiri_hyoma+nagi_seishiro` | 3 | 0.8968 |
| `arm3_merged_isagi_yoichi+itoshi_rin` | 85 | 0.2097 |
| `arm3_merged_isagi_yoichi+itoshi_rin+nagi_seishiro` | 2 | 0.4495 |
| `bachira_meguru` | 1737 | 0.3954 |
| `chigiri_hyoma` | 327 | 0.2276 |
| `isagi_yoichi` | 346 | 0.2576 |
| `nagi_seishiro` | 48 | 0.4488 |

### Arm 3 diagnostics

- merged trades: 3195 (56.5% of all)
- contributor appearances: {'bachira_meguru': 3104, 'barou_shoei': 1568, 'chigiri_hyoma': 106, 'isagi_yoichi': 2098, 'itoshi_rin': 501, 'nagi_seishiro': 114}
- merged mean pips: 8.754577779496787
- merged mean TQS: 0.38141558068417847

## arm4 (`phi5-arm4-post-kunigami`)

### Cross-statistic robustness (mandatory, sec 4)

| statistic | control | arm |
|---|---:|---:|
| median_window_mean_tqs | 0.3618 | 0.3643 |
| mean_window_mean_tqs | 0.3632 | 0.3666 |
| pooled_per_trade_mean_tqs | 0.3743 | 0.3754 |
| pooled_per_trade_trimmed_mean_tqs_10 | 0.3290 | 0.3353 |
| median_window_mean_pips | 7.3072 | 7.4533 |
| pooled_per_trade_mean_pips | 8.0069 | 7.5654 |
| cumulative_pips_forbidden_as_scoring | 44870.5577 | 55022.8238 |
| hit_rate | 0.5080 | 0.5146 |
| n_trades | 5604 | 7273 |

### Per-agent trades (arm)

| agent | n | mean TQS |
|---|---:|---:|
| `bachira_meguru` | 3546 | 0.3953 |
| `barou_shoei` | 567 | 0.3944 |
| `chigiri_hyoma` | 437 | 0.2617 |
| `isagi_yoichi` | 2139 | 0.3539 |
| `itoshi_rin` | 436 | 0.3952 |
| `nagi_seishiro` | 148 | 0.4162 |

### Arm 4 diagnostics

- rejection reasons: {'arm4_same_agent_already_on_symbol': 2621, 'arm4_sentinel_R6_block': 6039, 'arm4_slot_full': 1116, 'lower_conviction_same_symbol': 13488, 'sentinel_R1_block': 11128}
- concurrent same-bar-stop events: 665
