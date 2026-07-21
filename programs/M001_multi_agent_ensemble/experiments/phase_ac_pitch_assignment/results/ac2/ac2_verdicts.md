# AC.2 arm verdicts (Phase AC pitch assignment)

Rendered by ``ac2_eval.py`` at 2026-07-21T00:12:27.330426+00:00. See PROTOCOL.md §5.2 for the locked criteria.

## 1. Coverage

| Pre-registered arm | Session status | Reason |
|---|---|---|
| **A1** (baseline / control) | RUN | reference for AC2.1/AC2.2 |
| **A2** (single-squad, Rin widened to (EURUSD, USDCHF)) | RUN | AC.1.rin-a passed BH-adjusted (see ac1_verdicts.md §6 STRICT) |
| **B1-hard** (multi-squad hard isolation) | DEFERRED | `_drive_squad_replay` role-kwargs isagi/barou/kunigami block partial rosters; out of resumer write-scope. See ac2_run.py module docstring. |
| **B1-soft** (multi-squad soft isolation, pitch-preferred routing) | DEFERRED | needs core-aggregator pitch-preferred routing; out of resumer write-scope. |
| **AC2.4** (no C3 poisoning) | NOT MEASURED | `ac2_run.py` slicer does not export per-agent per-window same-tick collision counts; adding it would be a re-run. Flagged as not-measured rather than assumed-clean. |
| **AC2.5** (isolation-cost audit, B1-soft − B1-hard) | NOT REPORTED | B1 arms deferred. |

## 2. Per-arm per-agent C1 (mean TQS + k/7 + boot 95% CI)

### Arm A1

| Agent | trades | pop.win | mean-TQS | boot 95% CI | wins≥0.20 | cond mean≥0.30 | cond ≥5/7 | cond boot>0.25 | C1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `isagi_yoichi` | 955 | 7/7 |  0.358 | [ 0.347,  0.369] | 7/7 |   y |   y |   y | **PASS** |
| `bachira_meguru` | 736 | 7/7 |  0.392 | [ 0.359,  0.422] | 7/7 |   y |   y |   y | **PASS** |
| `itoshi_rin` | 203 | 7/7 |  0.370 | [ 0.330,  0.419] | 7/7 |   y |   y |   y | **PASS** |
| `chigiri_hyoma` | 503 | 7/7 |  0.239 | [ 0.212,  0.264] | 6/7 |   n |   y |   n | fail |
| `reo_mikage` | 0 | 0/7 |      - | - | 0/0 |   n |   n |   n | fail |
| `nagi_seishiro` | 0 | 0/7 |      - | - | 0/0 |   n |   n |   n | fail |
| `barou_shoei` | 438 | 7/7 |  0.401 | [ 0.336,  0.469] | 7/7 |   y |   y |   y | **PASS** |
| `kunigami_rensuke` | 0 | 0/7 |      - | - | 0/0 |   n |   n |   n | fail |

Squad mean-of-window-mean TQS: ** 0.352** [boot 95% CI  0.337,  0.370] over 7/7 populated windows.

Nagi total OOS trades: **0** (AC2.3 threshold 50) — **FAIL**.

### Arm A2

| Agent | trades | pop.win | mean-TQS | boot 95% CI | wins≥0.20 | cond mean≥0.30 | cond ≥5/7 | cond boot>0.25 | C1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `isagi_yoichi` | 955 | 7/7 |  0.358 | [ 0.347,  0.369] | 7/7 |   y |   y |   y | **PASS** |
| `bachira_meguru` | 736 | 7/7 |  0.392 | [ 0.359,  0.422] | 7/7 |   y |   y |   y | **PASS** |
| `itoshi_rin` | 391 | 7/7 |  0.341 | [ 0.272,  0.396] | 6/7 |   y |   y |   y | **PASS** |
| `chigiri_hyoma` | 503 | 7/7 |  0.239 | [ 0.212,  0.264] | 6/7 |   n |   y |   n | fail |
| `reo_mikage` | 0 | 0/7 |      - | - | 0/0 |   n |   n |   n | fail |
| `nagi_seishiro` | 0 | 0/7 |      - | - | 0/0 |   n |   n |   n | fail |
| `barou_shoei` | 438 | 7/7 |  0.401 | [ 0.336,  0.469] | 7/7 |   y |   y |   y | **PASS** |
| `kunigami_rensuke` | 0 | 0/7 |      - | - | 0/0 |   n |   n |   n | fail |

Squad mean-of-window-mean TQS: ** 0.346** [boot 95% CI  0.325,  0.368] over 7/7 populated windows.

Nagi total OOS trades: **0** (AC2.3 threshold 50) — **FAIL**.

## 3. AC2.1 anchor lock

For each anchor, arm-A2 C1 pass status must equal arm-A1 C1 pass status.

| Anchor | A1 C1 | A2 C1 | Anchor lock |
|---|---:|---:|---:|
| `isagi_yoichi` | PASS | PASS | same |
| `bachira_meguru` | PASS | PASS | same |
| `barou_shoei` | PASS | PASS | same |

AC2.1 verdict for A2 vs A1: **PASS (no regression)**.

## 4. AC2.2 squad TQS lift (primary)

Squad TQS delta (A2 − A1): **-0.0059** [boot 95% CI -0.0172, 0.0048].

AC2.2 threshold: delta ≥ +0.02 AND boot CI lower > 0.
AC2.2 verdict: **FAIL** (one-sided bootstrap p(delta ≤ 0) = 0.861).

## 5. AC2.3 Nagi volume floor

| Arm | Nagi trades | Threshold | Pass |
|---|---:|---:|---:|
| A1 | 0 | ≥ 50 | **FAIL** |
| A2 | 0 | ≥ 50 | **FAIL** |

**Diagnostic on Nagi = 0 across arms.** In the 2026-07-01 G7 v1 walk-forward baseline (3-pair panel EURUSD/GBPUSD/USDCAD), Nagi cleanly passed C1 with mean-TQS 0.385 (see `reviews/2026-07-01_g7_walk_forward_baseline.md`). On the extended 7-pair panel used by AC.2 (AC.0-v2 amendment §5), Nagi produces zero trades in the A1 baseline arm despite iterating over 53,163 bar-events on his home pairs (workspace publish counter confirms he is being called). His `.symbols` is still (EURUSD, GBPUSD, USDCAD); the anchors' `.symbols` is unchanged; yet no confluence proposals fire. This is a baseline-reproduction regression on the extended panel, not caused by widening. AC2.3 therefore fails EVERY AC.2 arm intrinsically — it is not a widening penalty. Recommended follow-up: investigate whether the extended-panel interleaved bar stream perturbs Nagi's peer-confluence gate timing before shipping any pitch-assignment change to `next-gen`. Diagnostic is flagged in REPORT.md §4.

## 6. BH FDR accounting

Pre-reg §6 reserved 20 AC.2 tests (4 arms × 5 criteria). This session ran fewer: A1 baseline + A2 tested against AC2.1 (anchor lock, 3 anchors, treated as hard prerequisite not BH member), AC2.2 (squad-lift bootstrap, one-sided), AC2.3 (Nagi floor, per-arm; hard-threshold count converted to a binary p ∈ {0, 1} so BH ordering is well-defined). B1-hard and B1-soft not run; AC2.4/AC2.5 not measured.

BH q = 0.1. Tests actually executed and BH-adjusted:

| Test | p-value | BH reject? |
|---|---:|---:|
| AC2.2 squad_lift A2−A1 | 0.8613 | no |
| AC2.3 nagi_floor A1 | 1.0000 | no |
| AC2.3 nagi_floor A2 | 1.0000 | no |

## 7. Recommended-action feed for REPORT.md

**A2 FAILS at least one executed AC.2 criterion (AC2.2 squad lift below threshold or CI touches 0, AC2.3 Nagi trades below 50 (but A1 baseline also fails AC2.3 — see §5 diagnostic)).** REPORT.md should recommend staying with A1 baseline (no evidence-backed pitch-assignment widening survived).

Note: AC2.3 failure in both A1 and A2 is a baseline-reproduction issue on the extended 7-pair panel (see §5 diagnostic), not a widening penalty. It does not by itself falsify pitch-assignment as a concept; it does mean the extended panel needs Nagi triage before the pitch-assignment question can be re-asked cleanly.

