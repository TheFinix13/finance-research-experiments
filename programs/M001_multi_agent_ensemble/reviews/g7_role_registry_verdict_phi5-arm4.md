# G7 Role Registry v1 verdict (phi5-arm4)

Generated 2026-07-06T18:38:19.642442+00:00 from post-phi5-arm4 baseline + leave-one-out caches. Pre-registered protocol: `experiments/G7_role_registry_v1/PROTOCOL.md`.

**Companion to G7 v1** — adds three role-differentiating criteria (C7 incoming chemistry / C8 workspace-signal impact / C9 trade-volume floor) and role labels. Retention rule (per §5): C3 pass AND at least one of {C2, C7, C8, C9} pass.

## Role Registry summary

| Agent | C2 | C3 | C7 | C8 | C9 | Role labels | Retained |
|---|:---:|:---:|:---:|:---:|:---:|---|:---:|
| `isagi_yoichi` | ✅ | ✅ | ❌ | ✅ | ✅ | chemistry_catalyst, workspace_catalyst | ✅ |
| `bachira_meguru` | ✅ | ❌ | ❌ | ✅ | ✅ | chemistry_catalyst, workspace_catalyst | ❌ |
| `itoshi_rin` | ✅ | ✅ | ❌ | ✅ | ✅ | chemistry_catalyst, workspace_catalyst | ✅ |
| `chigiri_hyoma` | ✅ | ✅ | ❌ | ✅ | ✅ | chemistry_catalyst, workspace_catalyst | ✅ |
| `reo_mikage` | ✅ | ✅ | W | ✅ | W | chemistry_catalyst, workspace_catalyst | ✅ |
| `nagi_seishiro` | ❌ | ✅ | ✅ | ✅ | ❌ | finisher, workspace_catalyst | ✅ |
| `barou_shoei` | ❌ | ✅ | ❌ | ✅ | ✅ | workspace_catalyst | ✅ |
| `kunigami_rensuke` | ⏸ | ⏸ | ⏸ | ⏸ | ⏸ | pending | ⏸ |

## Criterion 7 — Incoming chemistry (finisher role)

For each agent X, count peers p that lift X's mean TQS by ≥ 0.02 (4× C2's epsilon) when p is present vs absent. **C7 PASS** if ≥ 2 peers independently lift X.

| Agent | Lifting peers | Reason |
|---|:---:|---|
| `isagi_yoichi` | 0 (❌) | no peer lifts 'isagi_yoichi' by >= 0.02 TQS |
| `bachira_meguru` | 0 (❌) | no peer lifts 'bachira_meguru' by >= 0.02 TQS |
| `itoshi_rin` | 0 (❌) | no peer lifts 'itoshi_rin' by >= 0.02 TQS |
| `chigiri_hyoma` | 0 (❌) | no peer lifts 'chigiri_hyoma' by >= 0.02 TQS |
| `reo_mikage` | W | waived: 0 baseline trades (structural falsifier) |
| `nagi_seishiro` | 3 (✅) | 3 peers lift 'nagi_seishiro' by >= 0.02 TQS. Top: bachira_meguru +0.1806, itoshi_rin +0.0624, reo_mikage +0.0504 |
| `barou_shoei` | 0 (❌) | no peer lifts 'barou_shoei' by >= 0.02 TQS |
| `kunigami_rensuke` | W | waived: 0 baseline trades (structural falsifier) |

## Criterion 8 — Workspace-signal impact (v1 proxy)

Peer-delta magnitude proxy for workspace-signal consumption (the true `IntentDecision.interpreted_signal_family` citation count is not persisted in post-V artifacts; see PROTOCOL §12 amendment note). **C8 PASS** if workspace_impact ≥ 50 epsilon-units summed across all peers.

| Agent | Workspace impact | C8 | Top-impacted peer |
|---|---:|:---:|---|
| `isagi_yoichi` | 1340.9 | ✅ | `bachira_meguru` |
| `bachira_meguru` | 1084.8 | ✅ | `barou_shoei` |
| `itoshi_rin` | 713.3 | ✅ | `isagi_yoichi` |
| `chigiri_hyoma` | 198.4 | ✅ | `bachira_meguru` |
| `reo_mikage` | 236.2 | ✅ | `nagi_seishiro` |
| `nagi_seishiro` | 57.5 | ✅ | `bachira_meguru` |
| `barou_shoei` | 109.3 | ✅ | `bachira_meguru` |
| `kunigami_rensuke` | 0.0 | ❌ | `--` |

## Criterion 9 — Trade-volume floor (anti-dilution)

**C9 PASS** if the agent holds ≥ 5% of squad baseline trades. Structural falsifiers (Reo, Kunigami) are waived on C9 per PROTOCOL §3.

| Agent | Volume share | C9 | Reason |
|---|---:|:---:|---|
| `isagi_yoichi` | 29.4% | ✅ | volume_share=29.4% >= 5% floor (2139/7273 trades) |
| `bachira_meguru` | 48.8% | ✅ | volume_share=48.8% >= 5% floor (3546/7273 trades) |
| `itoshi_rin` | 6.0% | ✅ | volume_share=6.0% >= 5% floor (436/7273 trades) |
| `chigiri_hyoma` | 6.0% | ✅ | volume_share=6.0% >= 5% floor (437/7273 trades) |
| `reo_mikage` | 0.0% | W | waived: structural falsifier (intend() -> None by design) |
| `nagi_seishiro` | 2.0% | ❌ | volume_share=2.0% < 5% floor (148/7273 trades) |
| `barou_shoei` | 7.8% | ✅ | volume_share=7.8% >= 5% floor (567/7273 trades) |
| `kunigami_rensuke` | 0.0% | W | waived: structural falsifier (intend() -> None by design) |

## Retention verdict

Rule (§5): agent retained iff C3 pass AND at least one of {C2, C7, C8, C9} passes. Waived counts as "not a pass" for the OR-gate; the agent must have real evidence on at least one axis.

| Agent | Retained | Role labels | Reason |
|---|:---:|---|---|
| `isagi_yoichi` | ✅ | chemistry_catalyst, workspace_catalyst | RETAINED: C3 pass AND role axis ['C2', 'C8', 'C9'] (labels: ['chemistry_catalyst', 'workspace_catalyst']) |
| `bachira_meguru` | ❌ | chemistry_catalyst, workspace_catalyst | NOT RETAINED: C3 fail (cannibalises peer) |
| `itoshi_rin` | ✅ | chemistry_catalyst, workspace_catalyst | RETAINED: C3 pass AND role axis ['C2', 'C8', 'C9'] (labels: ['chemistry_catalyst', 'workspace_catalyst']) |
| `chigiri_hyoma` | ✅ | chemistry_catalyst, workspace_catalyst | RETAINED: C3 pass AND role axis ['C2', 'C8', 'C9'] (labels: ['chemistry_catalyst', 'workspace_catalyst']) |
| `reo_mikage` | ✅ | chemistry_catalyst, workspace_catalyst | RETAINED: C3 pass AND role axis ['C2', 'C8'] (labels: ['chemistry_catalyst', 'workspace_catalyst']) |
| `nagi_seishiro` | ✅ | finisher, workspace_catalyst | RETAINED: C3 pass AND role axis ['C7', 'C8'] (labels: ['finisher', 'workspace_catalyst']) |
| `barou_shoei` | ✅ | workspace_catalyst | RETAINED: C3 pass AND role axis ['C8', 'C9'] (labels: ['workspace_catalyst']) |
| `kunigami_rensuke` | ❌ | retirement_candidate | NOT RETAINED: C3 fail (cannibalises peer) |

## Squad-level verdict

- Retirement candidates: 1 (`kunigami_rensuke`)
- Agents failing retention: 2 (`bachira_meguru`, `kunigami_rensuke`)
- Squad Role Registry verdict: **FAIL** (threshold: 0 retirement candidates)
