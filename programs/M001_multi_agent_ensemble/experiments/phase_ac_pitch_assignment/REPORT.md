# Phase AC — pitch assignment for sub-passing v1 agents (campaign REPORT)

**Written:** 2026-07-21 (UTC).
**Program:** M001 multi-agent ensemble.
**Branch:** `multi-agent-ensemble` (research repo). No port to `next-gen` recommended by this campaign (see §3).
**Pre-registration:** `PROTOCOL.md` (13 §, locked 2026-07-20 morning) + `AMENDMENT_2026-07-20_ac0_methodology_switch.md` (fresh-compute AC.0-v2).
**Stages fired:** AC.0-v2 → AC.1 → AC.2 (partial — B1-hard / B1-soft deferred; AC2.4 / AC2.5 not measured; see §2.3 & §4).

---

## 1. Topline

**A2 (single-squad, Rin widened to (EURUSD, USDCHF)) FAILS the pre-registered AC.2 primary criterion.** The squad mean-of-window-mean TQS delta A2 − A1 is **−0.006 [boot 95% CI −0.017, +0.005], p(delta ≤ 0) = 0.861** — well below the pre-registered +0.02 lift and consistent with zero at 95%. Anchor lock (AC2.1) holds — Isagi, Bachira, Barou pass C1 identically in both arms. The Nagi ≥ 50-trade floor (AC2.3) fails in **both** A1 and A2 with 0 trades each; that is a baseline-reproduction issue on the extended 7-pair panel, not a widening penalty, and is flagged as a follow-up (§4).

**Recommended action for `next-gen`: stay with A1 baseline.** No evidence-backed pitch-assignment widening survived. The Rin USDCHF authorisation from AC.1 does not translate into a measurable squad-level improvement, and the campaign therefore does not authorise any change to `build_roster` overrides. See §3.

---

## 2. Stage-by-stage summary

### 2.1 AC.0-v2 — pair-character predicts agent success? PASS (thin)

**Verdict file:** `results/ac0_verdict_v2.md` · **Regression JSON:** `results/ac0_regression_v2.json` · **Compute artefacts:** `results/ac0_compute/*.json`

Methodology (per amendment): one fresh walk-forward per movable proposer with the movable's `.symbols` widened to the extended 7-pair panel; each per-movable-per-pair per-window mean-TQS regressed against the frozen `pair_character.json` feature vector; OLS + 10,000-resample window-level bootstrap.

| Movable | Passing features (95% CI on \|β\| > 0) | Direction-respected pair |
|---|---|---|
| `chigiri_hyoma` | `d1_ac1`, `h4_atr_percentile`, `max_session_impulse`, `d1_chop_fraction` | ✓ `max_session_impulse` (β = +1.10, CI lower = +0.27) — pre-locked "positive" sign |
| `itoshi_rin` | `d1_ac1`, `h4_atr_percentile`, `max_session_impulse`, `d1_chop_fraction` | ✗ (all four have CI-lower > 0 by lax semantic, but none match the pre-locked sign) |
| `kunigami_rensuke` | — (no telemetry: 0 trades on all 7 pairs after un-retirement) | n/a |

**Cond 1** (≥2 of 3 movables with passing feature): MET (2/3 = Chigiri, Rin).
**Cond 2** (≥1 direction-respected pair): MET (1/1 = Chigiri × `max_session_impulse`).
**Cond 3** (Kunigami un-retirement wiring): failed silently — amendment §8 zero-trades sentinel triggers; Kunigami sub-arms are non-testable downstream.

AC.0-v2 PASSES per §5, but on thin evidence: only Chigiri × `max_session_impulse` earned a direction-respected pass, and Kunigami's un-retirement is broken. Commit: `b31a36f`.

### 2.2 AC.1 — per-agent per-pair sub-arms

**Verdict file:** `results/ac1_verdicts.md` · **Per-sub-arm JSON:** `results/ac1_<sub-arm>.json`

Methodology (transparent): AC.1 sub-arms evaluated by extracting per-pair per-window mean-TQS from the AC.0-v2 fresh-compute telemetry rather than firing fresh per-sub-arm walk-forwards. Justification (recorded verbatim in `ac1_verdicts.md` §1): (a) `run_g7_v1_checkpoint_gate.py --symbols` restricts the whole PANEL — silences non-widened agents whose doctrine `.symbols` fall outside the panel — not the AC.1 semantic; (b) `run_ac0_compute.py --symbols` widens the movable to the full panel and cannot express "widen movable to a subset of the panel"; (c) a per-movable-symbol-override harness is outside the resumer session's write scope; (d) per-pair per-window mean-TQS is pair-local under phi41 aggregator (per-pair TQS scoring), so the AC.0-v2 wide-panel telemetry is a scientifically valid proxy modulo a bounded 2nd-order effect via Reo's HRP copier universe. BH FDR q = 0.10 applied over testable sub-arms only; NOT_TESTABLE sub-arms (amendment §8 sentinels) explicitly excluded from the BH family with no p-value.

| Sub-arm | Agent | Nominal `.symbols` | Evaluated | §8 dropped | C1 sub-criteria (mean/K-of-N/CI) | Verdict | BH reject |
|---|---|---|---|---|---|---|---|
| AC.1.chi-a | Chigiri | AUDUSD, NZDUSD | AUDUSD, NZDUSD | — | 0.207 / 3/7 / 0.183 | no | no |
| AC.1.chi-b | Chigiri | USDJPY | — | USDJPY | — | **NOT_TESTABLE** | — |
| AC.1.chi-c | Chigiri | GBPUSD | GBPUSD | — | 0.219 / 6/7 / 0.190 | no | no |
| AC.1.rin-a | Rin | EURUSD, USDCHF | EURUSD, USDCHF | — | 0.357 / 6/7 / 0.295 | **YES** | **yes** |
| AC.1.rin-b | Rin | EURUSD, USDJPY | EURUSD | USDJPY | 0.370 / 7/7 / 0.329 | YES* | yes |
| AC.1.rin-c | Rin | USDCHF | USDCHF | — | 0.349 / 6/7 / 0.244 | no | yes |
| AC.1.kun-a | Kunigami | AUDUSD, NZDUSD | — | AUDUSD, NZDUSD | — | **NOT_TESTABLE** | — |
| AC.1.kun-b | Kunigami | AUDUSD, NZDUSD, USDJPY | — | AUDUSD, NZDUSD, USDJPY | — | **NOT_TESTABLE** | — |

*AC.1.rin-b passes C1 arithmetically but is uninformative for widening — USDJPY dropped by the amendment §8 zero-trades sentinel, reducing the sub-arm to EURUSD-only which is already Rin's canonical home. Crediting rin-b for USDJPY widening would credit a pair that never produced a trade. The verdict applies the STRICT reading (§6 of `ac1_verdicts.md`) and credits only `evaluated_pairs` toward the passing pitch set.

**STRICT passing pitch set — the ONLY authorisation flowing into AC.2:**
- `itoshi_rin`: newly authorised widening = **`['USDCHF']`**; AC.2 A2 UNION `.symbols` = `('EURUSD', 'USDCHF')`.

No Chigiri or Kunigami sub-arm authorises a new widening. Kunigami un-retirement remains broken (§8) — a hard blocker for any AC.1 kunigami-widening question. Commit: `fd5d55d`.

### 2.3 AC.2 — squad-composition arms

**Verdict file:** `results/ac2/ac2_verdicts.md` · **Per-arm compute:** `results/ac2/ac2_arm_A{1,2}.json` · **Per-arm rendered verdict:** `results/ac2/ac2_arm_A{1,2}_verdict.json`

| Pre-registered arm | Session status | Reason |
|---|---|---|
| **A1** (baseline / control) | RUN | reference for AC2.1/AC2.2 |
| **A2** (single-squad, Rin widened) | RUN | AC.1.rin-a passed BH-adjusted (STRICT reading) |
| **B1-hard** (multi-squad hard isolation) | **DEFERRED** | `_drive_squad_replay` requires `isagi/barou/kunigami` role-kwargs; multi-squad rosters that drop those anchors break the harness (Manshine City = Bachira + Chigiri + Nagi + Reo has no Isagi/Barou). Out of resumer session's `results/**` + `REPORT.md` write scope; needs a proper `SquadEngineMulti` in `sim/`. |
| **B1-soft** (multi-squad soft isolation, pitch-preferred routing) | **DEFERRED** | needs core-aggregator pitch-preferred routing; out of resumer session's write scope. |
| **AC2.4** (no C3 poisoning) | **NOT MEASURED** | `ac2_run.py` slicer does not export per-agent per-window same-tick collision counts; adding it would be a re-run. Flagged as not-measured rather than assumed-clean. |
| **AC2.5** (isolation-cost audit, B1-soft − B1-hard) | NOT REPORTED | B1 arms deferred. |

**A1 baseline (5,117 trades / 7 OOS windows, phi41 aggregator, `sentinel_blocks=True`, `use_workspace=True`).** Per-agent C1 status (mean-TQS over populated windows / k-of-7 windows ≥ 0.20 / boot 95% CI lower):

| Agent | trades | mean-TQS | 95% CI | wins≥0.20 | C1 |
|---|---:|---:|---|---|---|
| `isagi_yoichi` | 955 | 0.358 | [0.347, 0.369] | 7/7 | **PASS** |
| `bachira_meguru` | 736 | 0.392 | [0.359, 0.422] | 7/7 | **PASS** |
| `itoshi_rin` | 203 | 0.370 | [0.330, 0.419] | 7/7 | **PASS** |
| `chigiri_hyoma` | 503 | 0.239 | [0.212, 0.264] | 6/7 | fail (mean+CI) |
| `reo_mikage` | 0 | — | — | — | fail (0 trades) |
| `nagi_seishiro` | 0 | — | — | — | fail (0 trades) |
| `barou_shoei` | 438 | 0.401 | [0.336, 0.469] | 7/7 | **PASS** |
| `kunigami_rensuke` | 0 | — | — | — | fail (retired proposer) |

Squad mean-of-window-mean TQS: **0.352 [boot 95% CI 0.337, 0.370]** over 7/7 populated windows.

**A2 (Rin widened to EURUSD, USDCHF; 5,496 trades).** Same aggregator/sentinel/workspace. Per-agent diffs vs A1:

| Agent | A1 mean-TQS | A2 mean-TQS | A1 trades | A2 trades | Delta |
|---|---:|---:|---:|---:|---:|
| `isagi_yoichi` | 0.358 | 0.358 | 955 | 955 | 0 / 0 |
| `bachira_meguru` | 0.392 | 0.392 | 736 | 736 | 0 / 0 |
| `itoshi_rin` | 0.370 | **0.341** | 203 | **391** | −0.029 / +188 |
| `chigiri_hyoma` | 0.239 | 0.239 | 503 | 503 | 0 / 0 |
| `barou_shoei` | 0.401 | 0.401 | 438 | 438 | 0 / 0 |
| `reo_mikage` / `nagi_seishiro` / `kunigami_rensuke` | 0 | 0 | 0 | 0 | — |

Squad mean-of-window-mean TQS: **0.346 [boot 95% CI 0.325, 0.368]**.

**Pre-registered criteria (§5.2), applied on the executed subset:**

| Criterion | Result | Notes |
|---|---|---|
| **AC2.1 anchor lock** — Isagi/Bachira/Barou C1 identical A1 vs A2 | **PASS** | all three pass in both arms; no regression |
| **AC2.2 squad TQS lift** — delta ≥ +0.02, boot 95% CI lower > 0 | **FAIL** | delta = −0.006 [−0.017, +0.005], p(delta ≤ 0) = 0.861 |
| **AC2.3 Nagi ≥ 50 OOS trades** (every arm) | **FAIL in BOTH A1 AND A2** | Nagi = 0 in both; see §4 diagnostic |
| **AC2.4 no C3 poisoning** | **NOT MEASURED** | see coverage table above |
| **AC2.5 isolation-cost audit** | NOT REPORTED | B1 arms deferred |

**BH FDR (q = 0.10) over tests actually executed:**

| Test | p-value | BH reject? |
|---|---:|---|
| AC2.2 squad lift A2−A1 | 0.8613 | no |
| AC2.3 Nagi floor A1 | 1.0000 | no |
| AC2.3 Nagi floor A2 | 1.0000 | no |

None reject. Pre-reg §6 reserved 20 AC.2 tests (4 arms × 5 criteria); this session ran 3, documented for honest accounting (§5 below).

Commit: `2c8e363`.

---

## 3. Recommended action

**Stay with A1 baseline — no evidence-backed pitch-assignment widening survived AC.2.**

Concretely for `next-gen`:

- **Do NOT ship** `build_roster(pitch_overrides={'itoshi_rin': ('EURUSD', 'USDCHF')})` at this time. The AC.1.rin-a authorisation (BH-adjusted C1 pass on USDCHF) does hold as an **individual-agent** finding — Rin passes C1 individually in A2 (0.341, CI [0.272, 0.396], 6/7 windows ≥ 0.20). But the pre-registered squad-level criterion (AC2.2) is the gate for shipping, and it does not clear.
- **Do NOT enable** any additional widening. Chigiri had no AC.1 sub-arm pass; Kunigami un-retirement is broken and un-testable.

**Sequenced follow-up work** (not a commit here, just recommended next steps):

1. **Nagi extended-panel diagnostic** (blocking prerequisite for any repeat of AC.2). On the 3-pair panel EURUSD/GBPUSD/USDCAD, Nagi passed C1 with mean-TQS 0.385 in the 2026-07-01 baseline. On the extended 7-pair panel used by AC.0-v2 + AC.2, Nagi produces **zero** trades in the baseline arm despite iterating over 53,163 bar-events on his home pairs. Something about the extended interleaved bar stream perturbs Nagi's peer-confluence gate timing. Fix the diagnostic before re-running any AC.2 arm.
2. **Kunigami un-retirement wiring fix** in `run_ac0_compute._build_movable_roster` (documented in amendment §8 sentinel). Blocks AC.1.kun-a and AC.1.kun-b, which are otherwise the only defensive-playstyle probes on the AUD/NZD candidates predicted by §3 priors.
3. **B1-hard / B1-soft harness build.** Implement `SquadEngineMulti` in `sim/` (not `experiments/**`), then re-run AC.2 with all four arms and AC2.4 (C3 poisoning) exported. Follow-up branch — out of scope for this resumer session.
4. **AC2.4 C3 export** in `ac2_run.py`. Extend the per-agent per-window slicer to include same-tick collision clean-window counts; a one-line add against `_drive_squad_replay.out.workspace_read_counts` alongside a per-tick collision tally.

---

## 4. Honest negatives and surprise findings

- **AC.0-v2 PASS is thin.** Only Chigiri × `max_session_impulse` gave a direction-respected feature pass. Rin passed §5 Cond 1 but no feature respected her pre-locked directional prior (§3). Kunigami got zero telemetry. If one strengthened §5 to require Cond 2 for the same agent whose Cond 1 fires, only Chigiri would carry AC.0 forward.
- **AC.1 rin-c narrowly fails on C1 bootstrap** — CI lower 0.244 vs threshold 0.250. If the pre-reg used percentile CI-lower-inclusive (> vs ≥), rin-c passes; the STRICT reading with `>` is applied per pre-reg wording. USDCHF-only Rin would be a *replacement* rather than an addition — but §5.1 is locked to UNION, so this is moot.
- **AC.1.rin-b passes on paper but the pre-reg intent (widen to USDJPY) collapses under §8 sentinel.** USDJPY had zero Rin trades in the AC.0-v2 telemetry — amendment §8 dropped the pair from the eval, leaving EURUSD-only. The STRICT reading credits only `evaluated_pairs`, so rin-b authorises no new pitch. This is a fair application of the pre-reg intent (a pass on a pair that produced zero trades cannot authorise widening TO that pair), but it also means the USDJPY hypothesis for Rin was never actually tested.
- **A2 Rin quality dropped on aggregation.** Individually Rin still passes C1 (0.341 vs threshold 0.30), but her mean-TQS fell 0.370 → 0.341 (−0.029) when USDCHF was added. Her total trade count rose 203 → 391 (+188). USDCHF trades are lower-quality than EURUSD trades in her hands at the squad level — a signal that per-agent solo C1 pass ≠ per-agent quality in the ensemble. This is exactly the kind of interaction the AC.2 layer was designed to catch, and it is caught cleanly.
- **Nagi = 0 trades in A1 baseline on extended panel.** Most consequential surprise. Reproduces cleanly (same behavior in both A1 and A2), workspace publish counts confirm Nagi is being iterated (53,163 bar-events on his home pairs), yet his confluence gate never fires. On the 2026-07-01 3-pair baseline he passed C1 comfortably. The extended-panel interleaved bar stream (7 pairs vs 3) is the only material difference. This is a **baseline-reproduction regression**, not a widening penalty — the AC.2 pipeline surfaced it as a side effect but did not cause it.
- **Reo = 0 trades in both arms.** Same likely mechanism — Reo is `copier_hrp`, driven by peer signals. Zero Reo trades in A1 baseline is consistent with the Nagi observation: some component of the peer-signal / confluence pipeline is quiescent on the extended panel.
- **`_drive_squad_replay` role-kwargs blocked B1 arms.** The pre-reg §5 speaks of "three independent processes" for B1-hard, but the sealed sim harness requires an Isagi, Barou, and Kunigami instance per squad call. Manshine City's pre-registered composition (Bachira + Chigiri + Nagi + Reo) has none of the three anchor kwargs. A resumer-scope faithful implementation would require monkey-patching or a new `SquadEngineMulti`; the honest choice was to defer.

---

## 5. FDR accounting (pre-reg §6)

Pre-reg budgeted **28 tests total**:

- **8 AC.1 sub-arms.** 5 tested (chi-a, chi-c, rin-a, rin-b, rin-c). 3 NOT_TESTABLE (chi-b, kun-a, kun-b — amendment §8 sentinels; no p-value; excluded from the BH family). BH q = 0.10 applied over the 5 testable p-values in `ac1_verdicts.md` §5: 3 rejects (rin-a, rin-b, rin-c; STRICT reading credits only rin-a for a new widening).
- **20 AC.2 tests** (4 arms × 5 criteria). 3 tested this session (AC2.2 A2 vs A1; AC2.3 A1; AC2.3 A2). AC2.1 treated as a hard prerequisite ("Any regression kills that arm") rather than a BH family member, per pre-reg §5.2 wording. B1-hard, B1-soft, AC2.4 (all arms), AC2.5 not measured this session. BH q = 0.10 applied over the 3 executed tests: 0 rejects.

Net rejects across the campaign: **3 out of 28 pre-registered tests**, all in AC.1. All AC.2 tests fail to reject.

The 17-test shortfall (20 AC.2 reservations − 3 executed) is not a discipline breach — the reserved budget is a maximum, not a lower bound. It is documented here so that a follow-up session running B1-hard / B1-soft / AC2.4 uses the correct BH-family size for its own execution log rather than double-counting this session's tests.

---

## 6. Follow-ups

Numbered by priority for a follow-up worker (not this session):

1. **Nagi extended-panel diagnostic** — see §3. Highest priority; blocks any faithful AC.2 re-run.
2. **Kunigami un-retirement wiring fix** in `run_ac0_compute._build_movable_roster`. Blocks AC.1.kun-a / kun-b (the only defensive-playstyle probes).
3. **`SquadEngineMulti` build** in `sim/` for B1-hard / B1-soft. This is the unfinished half of the AC.2 quartet.
4. **AC2.4 C3 export** in `ac2_run.py`. One-line add against `_drive_squad_replay.out.workspace_read_counts` alongside a per-tick collision tally.
5. **Panel-size sensitivity study.** The Nagi = 0 finding suggests the pre-reg's "5 pairs → 7 pairs" harness extension has second-order dynamics that the pre-reg did not anticipate. A short study of Nagi's confluence-fire count as a function of panel size (3, 4, 5, 6, 7 pairs) would isolate the mechanism.
6. **AC.1.rin-c revisit under REPLACE additivity.** §5.1 is locked to UNION, so this is moot for the current campaign, but rin-c narrowly failed on C1 CI-lower 0.244 vs threshold 0.250. Under REPLACE (Rin → USDCHF-only), the squad question changes — no volume dilution on EURUSD. Would need a §5.1 amendment.
7. **Pair-character panel expansion.** AC.0-v2's PASS-on-thin-evidence would gain power with more USD-quoted pairs. Amendment §7 forbids a third methodology switch if AC.0-v2 fails; it does not forbid extending the pair panel. A 10-pair panel would let §3 direction-respected tests move from "1 pair" to a meaningful family.

---

## 7. Session hygiene

- Session claim file: `.sessions/2026-07-20_phase-ac-pipeline-run.md` — marked done at end of this session.
- Heartbeat monitor artefacts: `programs/M001_multi_agent_ensemble/reviews/compute_heartbeat.{jsonl,log}` — appended, not rotated.
- Crash-fingerprint tail captures (normal-exit): `programs/M001_multi_agent_ensemble/reviews/crash_fingerprints/20260720T2*_AC2-*.txt`, `20260721T0*_AC2-A2-widened_pid43979.txt` — kept for audit trail, not committed.
- Compute wall-clock actual vs estimated:
  - **Stage 2 AC.0-v2 regression:** ~3 s (est. 5–15 min); trivially under budget.
  - **Stage 3 AC.1 evaluation:** ~2 s (est. 5–10 h); the amendment §8 methodology (extract from AC.0-v2 telemetry) was far faster than a per-sub-arm walk-forward would have been.
  - **Stage 4 AC.2 A1 + A2 (parallel):** ~57 min total wall-clock (A1 finished at ~48 min, A2 at ~57 min; ran in overlapping detached screen sessions). Estimate was 8–20 h assuming all four arms; the deferred B1-* arms account for the difference.
- No push. The follow-up cleanup worker owns pushes.
- Every stage commit and rationale is enumerated in §8 below.

---

## 8. Commit SHAs (chronological, this campaign only)

| SHA | Stage | One-line |
|---|---|---|
| `16246a7` | Pre-Stage-0 | Extend `pair_character.json` with USDJPY, USDCHF (post cache pull). |
| (pre-existing prior to resumer) | AC.0-v2 harness + regression + tests landed in a prior session; sim suite 863→882 passed. See `ai_context.md` 2026-07-20 evening section. |
| `b31a36f` | AC.0-v2 | PASS — Chigiri × `max_session_impulse` direction-respected; Kunigami zero-trades sentinel (2/3 movables, Cond 1+2 met). |
| `fd5d55d` | AC.1 | 1 of 8 sub-arms authorises a new widening (Rin USDCHF; BH-adjusted q = 0.10, STRICT reading applied). |
| `2c8e363` | AC.2 | A1 = baseline, A2 = FAIL (squad-lift −0.006, Nagi = 0 in both arms; B1-hard/B1-soft deferred; AC2.4/AC2.5 not measured). |
| _(this file)_ | Report | Campaign REPORT.md written — stay with A1 baseline, no port to `next-gen`. |
