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

## Pre-registered (Stage 0 ready to run)

### Six-study line (v1 alpha / risk research)

Individual pre-registrations across the alpha, risk-gating, and
kill-switch design surface. Each study stands alone.

| ID | Short name | Repo folder | Pre-reg | Notes |
|---|---|---|---|---|
| E010 | Stage-2b equal_highs_pool | [E010_equal_highs_pool_stage2b](experiments/E010_equal_highs_pool_stage2b/) | yes (`fd8eb3d`, 2026-06-24) | **STOPPED at Stage 2 (2026-07-28); survivors `parked_weak_effect`.** Stage 0 reproduced E006 exploratory joint counts exactly; Stage 1 screen 7/10 alive (selection +0.12…+0.47, lift +0.12…+0.33, p ≤ 0.0004); Stage 2 confirm (EURUSD 2022–2024) 0/7 — **selection term flipped negative on every cell** (−0.05…−0.66; best +0.013) while the displacement-null **lift stayed positive and significant everywhere** (+0.11…+0.28, p ≤ 0.0036). The pool window's in-window *timing* edge is real OOS; its setup-*selection* edge was regime-local to 2015–2021. Stages 3–4 not run; sealed reservation released. **A6 Nagi confluence deployment-grade stays blocked.** A lift-only hypothesis is a legitimate new ID. See [REPORT.md](experiments/E010_equal_highs_pool_stage2b/REPORT.md). |
| E017 | Confidence-gated cooldown | [E017_confidence_gated_cooldown](experiments/E017_confidence_gated_cooldown/) | yes (2026-07-13) | **Verdict `parked_capital_cost` (2026-07-13).** MC N=10k: GC-S eliminates dead time (0 h vs HK 6,500 h) and cuts median max DD (2.5% vs 16.9%) but **fails Pareto** on terminal equity vs compounding HK baseline. Gauge convergence PASS; Jul-08 replay descriptive PASS. **Phase 3 blocked** — [`STOP_NOTICE.md`](experiments/E017_confidence_gated_cooldown/STOP_NOTICE.md), [`REPORT.md`](experiments/E017_confidence_gated_cooldown/REPORT.md). Binary `kill.txt` halt stays in production. Harness: `programs/E017/`. |
| E018 | Regime-aware fade gating (R2 stand-aside) | [E018_regime_aware_fade_gating](experiments/E018_regime_aware_fade_gating/) | yes (2026-07-14) | **Verdict `dead` (2026-07-14).** Frozen causal R2 (trend-extension/breakout, Chigiri Φ4.1 priors) is NOT a negative-expectancy regime OOS 2019–2025: R2 exp +0.19/+16.20/+2.53 pips (EUR/GBP/USD-CAD), BH q=0.70/0.98/0.70, 0/3 pairs sig-negative; fade edge concentrated in R1 pullback (BH q=0.001). 2026-07 incident = descriptive streak, not generalizable. No live change; `zone_d1_against` unchanged. Harness: `programs/E018/`. |
| E019 | Risk-adjusted confidence recovery (redesign of parked E017) | [E019_confidence_recovery_riskadjusted](experiments/E019_confidence_recovery_riskadjusted/) | yes (2026-07-14) | **Verdict `dead` / STOP (2026-07-14).** Re-scored the graduated-confidence mechanism on the risk-adjusted primary `RaC_β=AnnRet/CDaR_β` (β=0.95) vs the shipped AK auto-clear baseline. GR-S is genuinely SAFER (CDaR 0.027 vs 0.097, worst-DD 0.089 vs 0.355, ruin 0 vs 0.38) but its annualised return collapses to ≈0.2%/yr (gauge suppresses exposure off-peak) → `RaC_β`≈0.03–0.10 vs AK ≈11.6–15.5; loses all 6 DGP×ρ cells, bootstrap p=1.000, PBO=0.0, deflated z=−0.39. E017's terminal-equity failure reappears one level up. **Phase 3 blocked** — keep shipped AK auto-clear; reframe needs new id (E020+). N=10k, 16 tests. `STOP_NOTICE.md`. |

### Exit-management campaign (E020–E025)

A coordinated family of five pre-registered studies evaluating
exit-side improvements for the v1 live agent. All share the
counterfactual replay harness `programs/_shared/counterfactual_replay/SPEC.md`
(PRE-0). Motivating incident: GBPUSD ticket `2969136564` (2026-07-16
short) reached MFE 79.1 pips (1.49R, 0.5p shy of the 1.5R TP), retraced
36.5 pips with no give-back protection between BE-at-1R and TP.

Study roles in the stack:

- **E020** — MFE-ratcheted trailing stop (locks in favorable excursion)
- **E021** — Partial exit at fixed-R milestone (banks a fraction early)
- **E022** — Structure-aware TP snap (pulls TP inward at order placement)
- **E024** — Near-TP stall exit (closes when MFE plateaus close to TP)
- **E025** — Joint exit-stack Pareto validation (composability safety net)

E025 gates what actually ships — even if E020/E021/E022/E024 land
individual `alive` verdicts, E025's Pareto verdict on the layered stack
decides the production surface. See each study's `PROTOCOL.md` for full
statistical design.

| ID | Short name | Repo folder | Pre-reg | Notes |
|---|---|---|---|---|
| E020 | MFE-ratcheted trailing stop | [E020_mfe_ratcheted_trail](experiments/E020_mfe_ratcheted_trail/) | yes (2026-07-20) | **STOPPED-DEAD (2026-07-20).** All 12 pre-registered arms produced negative pooled ΔSharpe (−0.103 to −0.114, all p ≈ 0, all 0/5 folds positive, all BH-FDR rejected in the degradation direction). Mechanism confirmed: tail-cap gain (+1R on worst decile) dominated by runner-choke cost (P(reach 1R) drops 22 pp under tightest arm). Deployed cell stays as-is; STOP_NOTICE.md filed. See [REPORT.md](experiments/E020_mfe_ratcheted_trail/REPORT.md), [STOP_NOTICE.md](experiments/E020_mfe_ratcheted_trail/STOP_NOTICE.md), [results.json](programs/E020/results.json). |
| E021 | Partial exit at fixed-R milestone | [E021_partial_exit_at_r_milestone](experiments/E021_partial_exit_at_r_milestone/) | yes (2026-07-20) | **STOPPED-DEAD (2026-07-20).** All 9 pre-registered arms produced negative pooled ΔSharpe (−0.1076 to −0.1314, BH-adj p ≈ 0, 0/5 folds positive on every arm); every CI lies entirely below 0. H2 special case `parked_lower_variance_lower_return` did NOT authorise: Δ variance of R is statistically negative on all arms (CI-UB [−0.85, −0.43]) but ΔSharpe CI does not straddle 0 (PROTOCOL §5.3 gate not met). Mechanism confirmed: tail-cap (+1R worst-decile) + variance drop + give-back rescue (+7 to +18 pp) are real, but mean-R give-up on the 47–63 % of trades that cross the trigger dominates. `LiveConfig.partial_exits` stays `False`; STOP_NOTICE.md filed; no E025 candidates promoted via H2. See [REPORT.md](experiments/E021_partial_exit_at_r_milestone/REPORT.md), [STOP_NOTICE.md](experiments/E021_partial_exit_at_r_milestone/STOP_NOTICE.md), [results.json](programs/E021/results.json). |
| E022 | Structure-aware TP snap | [E022_structure_aware_tp_snap](experiments/E022_structure_aware_tp_snap/) | yes (2026-07-20) | **STOPPED-DEAD (2026-07-20).** 0/12 arms alive, 11/12 dead, 1/12 `inactive_snap_never_fires` (`ladder_top_d5`, 3.02 % fire — below the 5 % feasibility floor). Family-level `parked_snap_never_fires` NOT triggered (only 1/12 arms fires < 5 %). Mechanism sanity PASSES: Δ P(TP fills) is positive on every arm (up to +3.48 pp on `all_d15`) — the snap DOES raise fill probability as designed. But Δ mean R \| winner is −0.106 R on the largest-firing arm (winner exits for less R deterministically), and this per-winner cost dominates the fill-rate gain: pooled ΔSharpe ∈ [−0.028, −0.001], 7/12 arms BH-FDR significant in the degradation direction. Motivating GBPUSD 2969136564 vindicates PROTOCOL §5.3's predicted "no fire" (candidate levels lie outside the entry→TP band). Kept shipped placement; STOP_NOTICE.md filed. See [REPORT.md](experiments/E022_structure_aware_tp_snap/REPORT.md), [STOP_NOTICE.md](experiments/E022_structure_aware_tp_snap/STOP_NOTICE.md), [results.json](programs/E022/results.json). |
| E024 | Near-TP stall exit | [E024_near_tp_stall_exit](experiments/E024_near_tp_stall_exit/) | yes (2026-07-20) | **STOPPED-DEAD (2026-07-20).** Stage-1 dead in all 72 (arm, symbol) cells; stage-2 cancelled per PROTOCOL §6. Per-symbol ΔSharpe ranges: EURUSD [−0.0852, −0.0936], GBPUSD [−0.0839, −0.0948], USDCAD [−0.1327, −0.1448]. BH-FDR at α=0.10 rejected H0 in the DEGRADATION direction on 22/24 EURUSD, 24/24 GBPUSD, 24/24 USDCAD arms. Every arm's Δ P(false positive) is above the 0.5 `parked_false_positive_heavy` threshold (range [0.630, 0.909]); on the anchor arm (a=1.45, S1_wallclock, s=3600) 78.6 % of GBPUSD fires land on trades whose baseline exit_reason == "tp". Mechanism: tail cap +1R real, but clean-TP-vs-give-back ratio in the `mfe_r ∈ [1.45, 1.50]` band is ~44:1 on PRE-0 GBPUSD — any near-TP detector is structurally forced to eat clean winners. Mirror image of E020's runner-choke; both die on the deployed 1.5R TP geometry. Deployed cell stays as-is; STOP_NOTICE.md filed. See [REPORT.md](experiments/E024_near_tp_stall_exit/REPORT.md), [STOP_NOTICE.md](experiments/E024_near_tp_stall_exit/STOP_NOTICE.md), [results.json](programs/E024/results.json). |
| E025 | Joint exit-stack Pareto validation | [E025_joint_exit_stack](experiments/E025_joint_exit_stack/) | yes (2026-07-20) | **CANCELLED-DEPENDENCY-FAILED (2026-07-20).** All four upstream studies (E020, E021, E022, E024) landed `dead` — zero-alive-upstream is a deterministic cancellation per PROTOCOL §4a. Phase 2 sweep not launched; family-size-57 deflated-Sharpe budget not spent; bar-granularity + OOS-only sensitivities not run. Deployed `all_on` cell (wick_proof + be_migration + plg + fixed 1.5R TP) stays as-is; `LiveConfig.partial_exits = False` and `LiveConfig.exit_manager_enabled = False` defaults preserved. Collective campaign finding: the exit-side rule set on the current cell is already close to optimal given the entry model (see [STOP_NOTICE.md](experiments/E025_joint_exit_stack/STOP_NOTICE.md) §"Family-multiplicity accounting" — 98/105 arms rejected in the DEGRADATION direction, 0/105 in the FAVOR direction). Next legitimate exit-side campaign requires a genuinely new mechanism (E023 pre-registered but Phase-2 unstarted) or a redesigned cell — not an amendment. |

Note: E023 (post-BE structure trail) was intentionally omitted from
the initial campaign — deferred until E020 verdict lands so the
combined behaviour of MFE-ratchet + structural anchor can be
scoped precisely.

Note: **E026** is reserved by the in-flight `e026-low-mfe-time-stop`
branch (I021 time-boxed-trades candidate); not part of this registry
table until that lane lands.

### Liquidity-structure line (2026-07-28)

Two pre-registered studies reducing externally-sourced discretionary
"liquidity" folklore to falsifiable tests, sequenced per
component-before-composite discipline. Both are prerequisites for any
M001 Po3 / valid-liquidity striker and for any v1-side liquidity
candidate; neither touches production.

| ID | Short name | Repo folder | Pre-reg | Notes |
|---|---|---|---|---|
| E027 | Valid-liquidity sweep reversal (BOS-qualified) | [E027_valid_liquidity_sweep](experiments/E027_valid_liquidity_sweep/) | yes (`cdb7a01`, 2026-07-28) | **STOPPED-DEAD at Stage 1 (2026-07-28).** 0/4 EURUSD H1/H4 cells alive; the BOS-qualified "valid" class reacted **worse** than the invalid class on every cell (diff −0.29…−0.57 ATR, one-sided p ≥ 0.55, both classes ≥ 100 events). The folk rule ("a low is valid liquidity only if it broke the high it came from") selects the *weaker* half of the sweep universe under this operationalisation. Closes this definition, not the folk concept (E001 §6 clause). Standing block on any valid-liquidity striker/candidate. See [REPORT.md](experiments/E027_valid_liquidity_sweep/REPORT.md). |
| E029 | Pool-window timing (lift-only, E010 successor) | [E029_pool_window_timing](experiments/E029_pool_window_timing/) | yes (2026-07-28) | The E010 decomposition's surviving half as a standalone claim: inside H1 `equal_highs_pool` windows, real setup timing beats hour-matched displaced timing (lift ≥ +0.10 ATR). EURUSD screen+confirm are burnt for this statistic (observed under E010, priors only); Stage 1 = GBPUSD 2015–2021 full 10-cell family BH α=0.05, Stage 2 = EURUSD H1+M15 2025→2026-05-27 sealed (re-reserved; shared with E030's M15 stage, declared same commit). Timing-primitive claim, not tradable expectancy. Harness: `programs/E029/`. |
| E030 | London-continuation session drift (E028 successor) | [E030_london_continuation](experiments/E030_london_continuation/) | yes (2026-07-28) | Mirror of E028's inversion: on one-side London days, go WITH London's direction 13:30→21:00 UTC, time exit only (zero geometry knobs), costs 0.3/1.0 pip/side. Taint declared: hypothesis generated on EURUSD M15 2015–21 → Stage 1 there is a non-claiming effect-size lock + placebo contrast (BOTH/NEITHER days); verdict begins Stage 2 (EURUSD 2022–24, BH across 2 cells), Stage 3 GBPUSD, Stage 4 sealed (shared reservation with E029). Harness: `programs/E030/`. |
| E028 | "Power of Three" session sequence | [E028_power_of_three_sessions](experiments/E028_power_of_three_sessions/) | yes (`cdb7a01`, 2026-07-28) | **STOPPED-DEAD at Stage 1 (2026-07-28), full stop.** The narrative is empirically **inverted** on EURUSD M15 2015–2021: one-side London takes are common (65 % of 1,816 days) but NY completes to the untapped opposite Asia extreme on only **26.2 %** [23.8, 28.8] vs a 61.2 % matched baseline (pre-registered margin +5 pp; observed −35 pp); "NY fake" = plain continuation 60 % of the time; both mechanical arms negative at base costs (−0.74/−0.66 pips, SL hit ~2.5× as often as TP); stable across all 7 years. Standing block on any Po3-reversal striker; a London-continuation hypothesis would be a new ID. See [REPORT.md](experiments/E028_power_of_three_sessions/REPORT.md). |

Register in this table **before** writing `experiments/E00X_*/PROTOCOL.md`.

## M001 program gates (cross-registry visibility)

M001 gate protocols live under `programs/M001_multi_agent_ensemble/experiments/`;
verdicts are recorded as dated §11.N amendments in each protocol. Rows here
are pointers, not the canonical record.

| Gate | Pre-reg | Verdict | Record |
|---|---|---|---|
| G7 v1 checkpoint gate | 2026-07-01 | **FAIL 1/7 (2026-07-14, first attempt)** — verdict-bearing phi41 run per protocol §4; Arm 4 companion also FAIL 1/7 (Barou 5/6 under Arm 4). Only Reo passes 6/6. Blockers: C5/C6 dispersion (five agents, mostly marginal; Nagi CV exactly 0), Bachira C3 (known Bachira↔Barou strategy-duplication artifact, applied as pre-registered), C2 bootstrap-CI gate (Chigiri/Nagi/Barou). No v2 arc authorised per doctrine §3.11.5. | `programs/M001_multi_agent_ensemble/experiments/G7_v1_checkpoint_gate/PROTOCOL.md` §11.13; `reviews/g7_v1_checkpoint_final_g7final-{phi41,arm4}.{md,json}` |
| G7 v1 checkpoint gate (second attempt, `g7retry1`) | 2026-07-14 (§11.15) | **FAIL 3/7 phi41; 2/7 arm4 (2026-07-14)** — post three-lever campaign (Phase Y Barou v1.3 weapon USDCAD-only + dispersion-r2 F19/F20 primitives + Nagi provenance borrow; C3 v2 advisory). Under phi41 (verdict-bearing): isagi + rin flip to full pass on C5/C6; reo waivers hold — squad 1/7 → 3/7. C3 v2 side-by-side falsifies the §11.13 "Bachira C3 = duplication artifact" hypothesis: Phase Y drops the Bachira→Barou worst-peer duplicate share from 89 %→0 % (phi41) / 94 %→40 % (arm4), and Bachira **still** fails C3 v2 in both arms. Remaining blockers: Bachira C3 (now agent-level cannibalisation of Barou's *distinct* trades), C2 bootstrap-CI gate for low-volume agents (Chigiri/Nagi/Barou unchanged), Chigiri C1 unchanged, Barou C1 REGRESSED under phi41 (n=43, panel mean 0.283 — Phase Y USDCAD-only reduced volume). No v2 arc authorised. Levers remain committed as first-class code. | `programs/M001_multi_agent_ensemble/experiments/G7_v1_checkpoint_gate/PROTOCOL.md` §11.14–§11.16; `reviews/g7_v1_checkpoint_final_g7retry1-{phi41,arm4}.{md,json}`; `reviews/c3_v2_side_by_side_g7retry1-{phi41,arm4}.{md,json}` |
| G7 v1 checkpoint gate (third attempt, `g7retry2`) | 2026-07-14 (§11.17, four levers each with own protocol) | **FAIL 3/7 phi41; 4/7 arm4 (2026-07-15)** — post four-lever campaign. Lever outcomes vs their own pre-registered criteria: **Phase AB (Barou multi-pair) PASS** — C1 0.283 (n=43) → 0.406 (n=444), all AB1–AB5; **Phase Z (Bachira weave) FAIL on Z5** — C3 0/7 → 7/7 with zero Bachira×Barou same-tick overlap (Z1/Z2), but the weave halved Bachira's volume and broke Nagi's confluence fuel (n 67→21, C1 0.436→0.197) — the pre-registered interaction risk; **Phase AA (Chigiri ignition) FAIL on AA1+AA2+AA-M** — volume up (296→503) but mean TQS 0.267→0.239 and entry-efficiency down, stricter-filter prior stands; **Lever D (C2 finisher clause, advisory)** behaves as designed (Nagi `W`, 3–4 qualified incoming lifts) but moot while his C1 fails. Bachira full pass for the first time; squad composition changed (Bachira/Barou fixed, Nagi newly broken, Chigiri unchanged). No v2 arc authorised. Standing user calls: weave default keep/revert, ignition revert, Barou whitelist adoption, finisher-clause + C3 v2 ratification. | `programs/M001_multi_agent_ensemble/experiments/G7_v1_checkpoint_gate/PROTOCOL.md` §11.17–§11.18; `reviews/g7_v1_checkpoint_final_g7retry2-{phi41,arm4}.{md,json}`; `reviews/phase_{z,aa,ab}_verdict.md`; `reviews/g7retry2_lever_audits.json` |

## Completed 2026-07-01 research-pipeline sweep (E011–E016)

Six pre-registered studies fired in the 2026-07-01 research pipeline
(session log: `brain-box/life/finance-research/multi-pair-trading-agent.md`).
Only studies with `alive` verdicts advance to production; verdicts are
append-only per `docs/methodology/verdict_registry.md`.

| ID | Short name | Repo folder | Verdict | One-line finding |
|---|---|---|---|---|
| E011 | Small-stop subset expectancy | [E011_small_stop_subset_expectancy](experiments/E011_small_stop_subset_expectancy/) | **stopped_at_stage_1** | Per-bucket OOS median CI overlaps pooled baseline (+9.99 pips/trade) on 463 trades. The alpha's edge is bucket-agnostic; small-stop subset does not carry a distinct edge. E012 does not launch. |
| E012 | Pending-limit-inside-zone entry | [E012_pending_limit_inside_zone](experiments/E012_pending_limit_inside_zone/) | **cancelled_dependency_failed** | E011 stop rule triggered → E012's premise falsified. Study not executed. |
| E013 | Safety-layer contribution | [E013_safety_layer_contribution](experiments/E013_safety_layer_contribution/) | **combined_alive; wick_alive; be_dead; plg_earns_keep** | Δ_wick +0.75 Sharpe (CI [+0.29, +1.38], BH-reject); Δ_be +0.18 (CI [-0.02, +0.36], CI touches 0); Δ_combined +0.80 (CI [+0.38, +1.22], BH-reject). PLG blocks 64 % winners vs 33 % losers, median would-be pips +23.5 — PLG is **blocking money more often than averting losses**. `plg_earns_keep` is `PROTOCOL.md`'s own (deliberately counter-intuitive) locked label for this pattern: "the uncomfortable answer that says PLG is expensive". Production posture: keep wick-proof + BE stack; open follow-up study to retune PLG thresholds. |
| E014 | Zone quality-score entry gate | [E014_quality_score_entry_gate](experiments/E014_quality_score_entry_gate/) | **parked_low_yield** | Pooled OOS 102 trades (12 % of baseline) at locked θ per-window. Median +26.09 pips (CI [+16.17, +33.99] strictly above E004 baseline +11.34), but trade-count ratio < 25 % production floor. Real edge concentration; too aggressive at θ ≥ 50. Candidate for a wider-grid amendment. E015 not launched. |
| E015 | Conviction-from-quality sizing | [E015_conviction_from_quality](experiments/E015_conviction_from_quality/) | **cancelled_dependency_failed** | E014 verdict not `alive_*` → E015 gate not opened. Study not executed. |
| E016 | Re-entry / flip on tighter-stop | [E016_reentry_flip_on_tighter_stop](experiments/E016_reentry_flip_on_tighter_stop/) | **cancelled_dependency_failed** | E011 stopped AND E014 not `alive_*` → both preconditions failed. Study not executed. |

**Production-side outcomes of the sweep:**

- Two non-strategy production adds shipped in the same session (Wave 2 of
  the plan): weekly rejection-review report (`agent/reports/rejection_review.py`)
  and portfolio-wide 5 % open-risk cap (`RiskConfig.portfolio_max_open_risk_pct`).
  Both are observation / ceiling changes, do not alter entry logic, and
  ship without a pre-registered study per `PROTOCOL_DISCIPLINE.md` §7
  ("proposing candidates for agent validation" is allowed; the two adds
  are not entry candidates).
- **No strategy-changing port** because no strategy-change study achieved
  an `alive_positive` verdict. The E013 `combined_alive` result validates
  the EXISTING production posture (wick-proof + BE + PLG all on); no
  change is required.
- The E013 PLG finding (`plg_earns_keep`, the protocol's locked label
  for "PLG is expensive") will feed a future pre-registered study on
  PLG cooldown tuning; do NOT change PLG
  parameters ad-hoc.

---

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
