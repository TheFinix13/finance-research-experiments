# Experiment registry

Master index of every hypothesis test in this repository. Numeric IDs
(`E001`, …) are collision-proof; legacy names (Test A, Test B) map to
`E006` / `E007` only.

**Discipline:** `PROTOCOL_DISCIPLINE.md` · **Data accounting:** `DATA_LEDGER.md`

| ID | Short name | Repo folder | Status | Pre-reg | Verdict (one line) |
|---|---|---|---|---|---|
| E001 | ICT concept ablation | [E001_concept_ablation](experiments/E001_concept_ablation/) | complete | executed-then-registered | Zone sole survivor; 6 concepts eliminated (BH-FDR grid) |
| E002 | Zone definitive grid | [E002_zone_definitive_grid](experiments/E002_zone_definitive_grid/) | complete | executed-then-registered | 13 BH-significant cells; candidate list only (in-sample) |
| E003 | Holdout IS/OOS | [E003_holdout_validation](experiments/E003_holdout_validation/) | complete | executed-then-registered | 1/8 IS-survivors validated OOS (H4/asia); selection-bias lesson |
| E004 | Walk-forward | [E004_walk_forward](experiments/E004_walk_forward/) | complete | executed-then-registered | H4/all 7/7 positive OOS windows; deployed cell chosen |
| E005 | Cross-pair + sealed | [E005_cross_pair_sealed](experiments/E005_cross_pair_sealed/) | complete | executed-then-registered | GBPUSD/USDCAD replicate; AUD/NZD excluded; 2026 sealed inconclusive |
| E006 | Price-action confluence (Test A) | [E006_test_a_price_action](experiments/E006_test_a_price_action/) | complete | yes (`2026-06-12`) | 5/284 alive hour-matched; gate-sized effects only |
| E007 | Impulse-origin bounce | [E007_impulse_origin_bounce](experiments/E007_impulse_origin_bounce/) | complete | yes (`b9715d9`) | 0/12 alive; bounce ≈ random hour-matched levels |

---

## Planned (not started)

| ID | Short name | Notes |
|---|---|---|
| E008 | Technical indicators only | v2-PROTOCOL "Test B" family — EMA/RSI/MACD/etc.; own pre-registration |
| E009 | Cross-family confluence | v2-PROTOCOL "Test C"; A×B survivors; last |

## M001 program gates (cross-registry visibility)

M001 gate protocols live under `programs/M001_multi_agent_ensemble/experiments/`;
verdicts are recorded as dated §11.N amendments in each protocol. Rows here
are pointers, not the canonical record.

| Gate | Pre-reg | Verdict | Record |
|---|---|---|---|
| G7 v1 checkpoint gate | 2026-07-01 | **FAIL 1/7 (2026-07-14, first attempt)** — verdict-bearing phi41 run per protocol §4; Arm 4 companion also FAIL 1/7 (Barou 5/6 under Arm 4). Only Reo passes 6/6. Blockers: C5/C6 dispersion (five agents, mostly marginal; Nagi CV exactly 0), Bachira C3 (known Bachira↔Barou strategy-duplication artifact, applied as pre-registered), C2 bootstrap-CI gate (Chigiri/Nagi/Barou). No v2 arc authorised per doctrine §3.11.5. | `programs/M001_multi_agent_ensemble/experiments/G7_v1_checkpoint_gate/PROTOCOL.md` §11.13; `reviews/g7_v1_checkpoint_final_g7final-{phi41,arm4}.{md,json}` |
| G7 v1 checkpoint gate (second attempt, `g7retry1`) | 2026-07-14 (§11.15) | **FAIL 3/7 phi41; 2/7 arm4 (2026-07-14)** — post three-lever campaign (Phase Y Barou v1.3 weapon USDCAD-only + dispersion-r2 F19/F20 primitives + Nagi provenance borrow; C3 v2 advisory). Under phi41 (verdict-bearing): isagi + rin flip to full pass on C5/C6; reo waivers hold — squad 1/7 → 3/7. C3 v2 side-by-side falsifies the §11.13 "Bachira C3 = duplication artifact" hypothesis: Phase Y drops the Bachira→Barou worst-peer duplicate share from 89 %→0 % (phi41) / 94 %→40 % (arm4), and Bachira **still** fails C3 v2 in both arms. Remaining blockers: Bachira C3 (now agent-level cannibalisation of Barou's *distinct* trades), C2 bootstrap-CI gate for low-volume agents (Chigiri/Nagi/Barou unchanged), Chigiri C1 unchanged, Barou C1 REGRESSED under phi41 (n=43, panel mean 0.283 — Phase Y USDCAD-only reduced volume). No v2 arc authorised. Levers remain committed as first-class code. | `programs/M001_multi_agent_ensemble/experiments/G7_v1_checkpoint_gate/PROTOCOL.md` §11.14–§11.16; `reviews/g7_v1_checkpoint_final_g7retry1-{phi41,arm4}.{md,json}`; `reviews/c3_v2_side_by_side_g7retry1-{phi41,arm4}.{md,json}` |
| G7 v1 checkpoint gate (third attempt, `g7retry2`) | 2026-07-14 (§11.17, four levers each with own protocol) | **FAIL 3/7 phi41; 4/7 arm4 (2026-07-15)** — post four-lever campaign. Lever outcomes vs their own pre-registered criteria: **Phase AB (Barou multi-pair) PASS** — C1 0.283 (n=43) → 0.406 (n=444), all AB1–AB5; **Phase Z (Bachira weave) FAIL on Z5** — C3 0/7 → 7/7 with zero Bachira×Barou same-tick overlap (Z1/Z2), but the weave halved Bachira's volume and broke Nagi's confluence fuel (n 67→21, C1 0.436→0.197) — the pre-registered interaction risk; **Phase AA (Chigiri ignition) FAIL on AA1+AA2+AA-M** — volume up (296→503) but mean TQS 0.267→0.239 and entry-efficiency down, stricter-filter prior stands; **Lever D (C2 finisher clause, advisory)** behaves as designed (Nagi `W`, 3–4 qualified incoming lifts) but moot while his C1 fails. Bachira full pass for the first time; squad composition changed (Bachira/Barou fixed, Nagi newly broken, Chigiri unchanged). No v2 arc authorised. Standing user calls: weave default keep/revert, ignition revert, Barou whitelist adoption, finisher-clause + C3 v2 ratification. | `programs/M001_multi_agent_ensemble/experiments/G7_v1_checkpoint_gate/PROTOCOL.md` §11.17–§11.18; `reviews/g7_v1_checkpoint_final_g7retry2-{phi41,arm4}.{md,json}`; `reviews/phase_{z,aa,ab}_verdict.md`; `reviews/g7retry2_lever_audits.json` |
| Phase AC pitch assignment (AC.0-v2 → AC.1 → AC.2-partial) | 2026-07-20 (PROTOCOL §13 sections + `AMENDMENT_2026-07-20_ac0_methodology_switch.md`) | **AC.2 A2 FAIL — recommended action: stay with A1 baseline (2026-07-21)**. Stage-by-stage: **AC.0-v2 PASS (thin)** — 2/3 movables (Chigiri, Rin) had a passing feature; only Chigiri × `max_session_impulse` direction-respected; Kunigami un-retirement wiring silently failed (0 trades all 7 pairs → amendment §8 zero-trades sentinel). **AC.1** — 5/8 sub-arms testable; BH q=0.10 rejects rin-a/b/c; STRICT reading (credit only `evaluated_pairs`) authorises exactly ONE new widening: **Rin USDCHF** (rin-a). **AC.2** — A1 (baseline) + A2 (Rin widened) ran; B1-hard / B1-soft DEFERRED (`_drive_squad_replay` role-kwargs block partial rosters, needs `SquadEngineMulti`); AC2.4 NOT MEASURED (C3 counts not exported); AC2.5 NOT REPORTED (B1 deferred). AC2.1 anchor lock PASS; **AC2.2 squad-lift FAIL** — delta A2−A1 = −0.006 [boot 95% CI −0.017, +0.005], p(delta≤0) = 0.861; **AC2.3 Nagi ≥ 50 trades FAIL in BOTH arms** (0 trades — extended 7-pair panel baseline-reproduction regression, not a widening penalty; Nagi passed C1 at 0.385 on the 2026-07-01 3-pair baseline). FDR: 3 rejects / 28 pre-registered tests (all AC.1). Follow-ups sequenced: Nagi extended-panel diagnostic (blocker), Kunigami un-retirement wiring fix, `SquadEngineMulti` build, AC2.4 C3 export, panel-size sensitivity. | `programs/M001_multi_agent_ensemble/experiments/phase_ac_pitch_assignment/PROTOCOL.md`; `AMENDMENT_2026-07-20_ac0_methodology_switch.md`; `REPORT.md`; `results/ac0_verdict_v2.md`; `results/ac1_verdicts.md`; `results/ac2/ac2_verdicts.md` |
| Phase AE Sae Itoshi event specialist | 2026-07-20 draft, LOCKED 2026-07-24 pre-run (§0 factual amendments: frozen NFP/CPI/FOMC calendar replaces the never-frozen Phase AD Dukascopy fixture; H4 driver + M15 event-tick injection; R7 absent by construction) | **FAIL (2026-07-24, evaluated once)** — **AE1 PASS** 54 OOS Sae trades (≥30 floor; 87 full-panel, all calendar-gated); **AE2 FAIL** OOS mean TQS **0.097** vs 0.30 floor, boot 95% CI **[0.042, 0.162]** vs 0.20 lower-bound floor (n=10k, seed 42); **AE3** fade 22.2%/ride 77.8%, no mechanic parked, both negative (fade −4.18 pips, ride −8.52 pips mean); **AE4 PASS** — incumbents untouched (max delta +0.001 Chigiri, 2 H4 trades displaced in 11 yr). 25 TP / 62 SL = 28.7% wins at 1.5R (breakeven 40%). Baseline arm reproduces sealed g7retry2 driver byte-for-byte (equivalence test). Consequence: `sae_enabled` stays False, **no Aug 7 NFP arming**; hour-13 bleed reads "avoidable, not tradable" — Phase AD Karasu remains the only live event-window lever; Sae v2 needs fresh pre-registration. Read-only-coupling incident (BarLoader head-gap backfill hit Dukascopy) caught, killed, cache verified undamaged, loader made network-free — REPORT §3. | `programs/M001_multi_agent_ensemble/experiments/phase_ae_sae_event_specialist/PROTOCOL.md`; `REPORT.md`; `results/phase_ae_evaluation.json`; `reviews/phase_ae_verdict.md`; fixture `data/news_calendar_frozen_2026-07-24.json` (sha256 `cfd18602…`) |

## Agent-side vs lab-side

| E001–E005 | Ran in `multi-pair-trading-agent` (validation harness). Documented here retrospectively; code stays in agent. |
| E006–E007 | Ran in this repo (`finance-research-experiments`). Code and outputs live here. |

Production strategy locked in agent: **`zone_d1_against` / H4 / all** on
EURUSD, GBPUSD, USDCAD. See E004 + E005 reports.

---

## How to add E017+

1. Copy `experiments/_TEMPLATE/` → `experiments/E0XX_your_hypothesis/`.
2. Add a row to the table above (`planned`).
3. Follow `PROTOCOL_DISCIPLINE.md` checklist.
4. Update `DATA_LEDGER.md` when Stage 1 starts.
