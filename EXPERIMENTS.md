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

| ID | Short name | Repo folder | Pre-reg | Notes |
|---|---|---|---|---|
| E010 | Stage-2b equal_highs_pool | [E010_equal_highs_pool_stage2b](experiments/E010_equal_highs_pool_stage2b/) | yes (`fd8eb3d`, 2026-06-24) | H1 `equal_highs_pool` × 10 M15 setups; selection-term + displacement-null lift ≥ +0.10 ATR; BH-FDR α=0.05; Stage 1 EURUSD 2015–2021, Stage 2 EURUSD 2022–2024, Stage 3 GBPUSD 2015–2021 (cache-constrained), Stage 4 EURUSD H1+M15 2025–2026-06-09 (sealed, reserved). Runs parallel with M001; A6 Nagi confluence-only deployment-grade waits on E010 alive verdict. |
| E017 | Confidence-gated cooldown | [E017_confidence_gated_cooldown](experiments/E017_confidence_gated_cooldown/) | yes (2026-07-13) | **Verdict `parked_capital_cost` (2026-07-13).** MC N=10k: GC-S eliminates dead time (0 h vs HK 6,500 h) and cuts median max DD (2.5% vs 16.9%) but **fails Pareto** on terminal equity vs compounding HK baseline. Gauge convergence PASS; Jul-08 replay descriptive PASS. **Phase 3 blocked** — [`STOP_NOTICE.md`](experiments/E017_confidence_gated_cooldown/STOP_NOTICE.md), [`REPORT.md`](experiments/E017_confidence_gated_cooldown/REPORT.md). Binary `kill.txt` halt stays in production. Harness: `programs/E017/`. |
| E018 | Regime-aware fade gating (R2 stand-aside) | [E018_regime_aware_fade_gating](experiments/E018_regime_aware_fade_gating/) | yes (2026-07-14) | **Verdict `dead` (2026-07-14).** Frozen causal R2 (trend-extension/breakout, Chigiri Φ4.1 priors) is NOT a negative-expectancy regime OOS 2019–2025: R2 exp +0.19/+16.20/+2.53 pips (EUR/GBP/USD-CAD), BH q=0.70/0.98/0.70, 0/3 pairs sig-negative; fade edge concentrated in R1 pullback (BH q=0.001). 2026-07 incident = descriptive streak, not generalizable. No live change; `zone_d1_against` unchanged. Harness: `programs/E018/`. |
| E019 | Risk-adjusted confidence recovery (redesign of parked E017) | [E019_confidence_recovery_riskadjusted](experiments/E019_confidence_recovery_riskadjusted/) | yes (2026-07-14) | **Verdict `dead` / STOP (2026-07-14).** Re-scored the graduated-confidence mechanism on the risk-adjusted primary `RaC_β=AnnRet/CDaR_β` (β=0.95) vs the shipped AK auto-clear baseline. GR-S is genuinely SAFER (CDaR 0.027 vs 0.097, worst-DD 0.089 vs 0.355, ruin 0 vs 0.38) but its annualised return collapses to ≈0.2%/yr (gauge suppresses exposure off-peak) → `RaC_β`≈0.03–0.10 vs AK ≈11.6–15.5; loses all 6 DGP×ρ cells, bootstrap p=1.000, PBO=0.0, deflated z=−0.39. E017's terminal-equity failure reappears one level up. **Phase 3 blocked** — keep shipped AK auto-clear; reframe needs new id (E020+). N=10k, 16 tests. `STOP_NOTICE.md`. |

Register in this table **before** writing `experiments/E00X_*/PROTOCOL.md`.

## M001 program gates (cross-registry visibility)

M001 gate protocols live under `programs/M001_multi_agent_ensemble/experiments/`;
verdicts are recorded as dated §11.N amendments in each protocol. Rows here
are pointers, not the canonical record.

| Gate | Pre-reg | Verdict | Record |
|---|---|---|---|
| G7 v1 checkpoint gate | 2026-07-01 | **FAIL 1/7 (2026-07-14, first attempt)** — verdict-bearing phi41 run per protocol §4; Arm 4 companion also FAIL 1/7 (Barou 5/6 under Arm 4). Only Reo passes 6/6. Blockers: C5/C6 dispersion (five agents, mostly marginal; Nagi CV exactly 0), Bachira C3 (known Bachira↔Barou strategy-duplication artifact, applied as pre-registered), C2 bootstrap-CI gate (Chigiri/Nagi/Barou). No v2 arc authorised per doctrine §3.11.5. | `programs/M001_multi_agent_ensemble/experiments/G7_v1_checkpoint_gate/PROTOCOL.md` §11.13; `reviews/g7_v1_checkpoint_final_g7final-{phi41,arm4}.{md,json}` |
| G7 v1 checkpoint gate (second attempt, `g7retry1`) | 2026-07-14 (§11.15) | **FAIL 3/7 phi41; 2/7 arm4 (2026-07-14)** — post three-lever campaign (Phase Y Barou v1.3 weapon USDCAD-only + dispersion-r2 F19/F20 primitives + Nagi provenance borrow; C3 v2 advisory). Under phi41 (verdict-bearing): isagi + rin flip to full pass on C5/C6; reo waivers hold — squad 1/7 → 3/7. C3 v2 side-by-side falsifies the §11.13 "Bachira C3 = duplication artifact" hypothesis: Phase Y drops the Bachira→Barou worst-peer duplicate share from 89 %→0 % (phi41) / 94 %→40 % (arm4), and Bachira **still** fails C3 v2 in both arms. Remaining blockers: Bachira C3 (now agent-level cannibalisation of Barou's *distinct* trades), C2 bootstrap-CI gate for low-volume agents (Chigiri/Nagi/Barou unchanged), Chigiri C1 unchanged, Barou C1 REGRESSED under phi41 (n=43, panel mean 0.283 — Phase Y USDCAD-only reduced volume). No v2 arc authorised. Levers remain committed as first-class code. | `programs/M001_multi_agent_ensemble/experiments/G7_v1_checkpoint_gate/PROTOCOL.md` §11.14–§11.16; `reviews/g7_v1_checkpoint_final_g7retry1-{phi41,arm4}.{md,json}`; `reviews/c3_v2_side_by_side_g7retry1-{phi41,arm4}.{md,json}` |

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
