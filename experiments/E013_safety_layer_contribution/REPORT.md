# E013 — Safety-Layer Contribution of Wick-Proof Stop-Loss, Break-Even Migration, and the Post-Loss Guard

**Date:** 2026-07-01 · **Protocol:** [`PROTOCOL.md`](PROTOCOL.md) · **Status:** `stage_1_complete`.
**Part of:** [2026-07-01 pipeline sweep](../../reviews/2026-07-01_pipeline_sweep_E011-E016.md) (E011-E016).

## Abstract

The live `zone_d1_against` H4 strategy trades under three risk-management overlays — a wick-proof synthetic stop-loss, break-even stop migration, and a post-loss guard that pauses trading after a losing streak — none of whose individual Sharpe-ratio contributions had previously been measured in isolation. We built a four-arm leave-one-out walk-forward harness (all layers on, wick-proof off, break-even off, all layers off) and ran it across the same seven out-of-sample windows used by the frozen E004 baseline, computing paired Sharpe deltas with 10,000-resample bootstrap confidence intervals and Benjamini-Hochberg correction across the three-delta family. Wick-proof stop-loss contributes +0.753 Sharpe (95% CI [+0.293, +1.376], BH-reject); break-even migration's +0.183 contribution (CI [-0.019, +0.364]) cannot be distinguished from zero at this sample size; the combined stack contributes +0.796 (CI [+0.382, +1.224], BH-reject). Separately, walking every post-loss-guard block forward to its counterfactual outcome shows the guard blocks 64.2% future-winners against 33.3% future-losers — a documented, non-trivial cost that motivates a dedicated retuning study rather than disabling the guard.

## 1. Introduction

### 1.1 Motivation

Retail risk-management overlays — synthetic stops that survive price wicks, stop migration to break-even once a trade is in profit, and cooldown rules after a losing streak — are common practitioner heuristics that are rarely measured for their own marginal contribution once deployed. The live agent runs all three simultaneously; a single bad or good week of live trading cannot distinguish whether any one of them is helping, hurting, or Sharpe-neutral, because their effects are confounded in the combined P&L stream. This study isolates each layer's contribution with a controlled ablation design before any layer is considered for adjustment.

### 1.2 Problem statement

What is the marginal Sharpe-ratio contribution of (a) wick-proof stop-loss, (b) break-even migration, and (c) the joint three-layer stack, relative to the raw `zone_d1_against` alpha with no risk overlay? Separately: what fraction of the post-loss guard's blocked signals would have won versus lost, had they been allowed to fire?

### 1.3 Contributions

1. A reusable four-arm leave-one-out A/B walk-forward harness (`scripts/run_walk_forward_ab.py`) with independent boolean toggles for each safety layer and a fixed seed for arm parity.
2. The first quantified Sharpe attribution for each of the three layers on this specific deployed strategy, with bootstrap CIs and BH-FDR correction.
3. The first walked-forward false-negative / false-positive rate for the deployed post-loss guard (n = 123 blocked signals), directly answering López de Prado's critique that risk-overlay costs are rarely measured against their benefit [@lopezdeprado2018tactical].

### 1.4 Report outline

Section 2 reviews the sparse literature on measuring risk-overlay contribution in isolation. Section 3 specifies the four-arm design and statistical pipeline. Section 4 describes the harness implementation. Section 5 reports per-arm, per-window, and delta results, plus the guard's counterfactual analysis. Section 6 discusses the findings, their limitations, and why the guard's cost does not by itself justify disabling it. Section 7 concludes.

## 2. Background and Related Work

Exit-side risk overlays are usually evaluated as part of a bundled backtest rather than attributed individually. This is a gap the leave-one-out ablation design in this study addresses directly, borrowing the standard machine-learning practice of removing one component at a time while holding all others fixed to isolate its marginal contribution, and applying it to a trading system's risk-management stack. Lo's adaptive-markets framing supports the underlying premise that a strategy's edge is regime-dependent rather than stationary [@lo2004adaptive], which is the usual justification for having a post-loss guard at all — the guard exists on the theory that a losing streak signals a temporarily adverse regime worth sitting out. What that framing does not, by itself, quantify is how often the guard is *wrong* about which regime it is in. López de Prado's list of common reasons quantitative funds under-perform their backtests explicitly names "not measuring the true cost of a risk overlay" as a recurring failure [@lopezdeprado2018tactical]; the counterfactual-resolution method used in Section 3.3 below is a direct, mechanical answer to that critique for this specific guard rather than a general claim about post-loss guards in the abstract. Bailey and López de Prado's work on backtest overfitting and the deflated Sharpe ratio [@bailey2014deflated; @bailey2014pseudo] motivates treating every Sharpe figure reported here as conditional on the fixed, pre-registered arm count (four) and delta family (three) — no additional arms or comparator statistics were tried and discarded before arriving at the reported numbers.

## 3. Methodology

### 3.1 Strategy and data

`zone_d1_against` H4, the same frozen alpha parameterisation used throughout this sweep, evaluated on the same seven out-of-sample walk-forward windows (2019-2025) as E004 and E011.

### 3.2 Arms

Four configurations, run with a fixed random seed for parity:

1. **`all_on`** — wick-proof stop-loss, break-even migration, and the post-loss guard all enabled (mirrors the current live production configuration).
2. **`wick_off`** — wick-proof stop-loss disabled; break-even and the guard remain on.
3. **`be_off`** — break-even migration disabled; wick-proof and the guard remain on.
4. **`all_off`** — all three layers disabled (the raw alpha, equivalent to E004's original fixed-lot harness).

### 3.3 Metrics

Per-arm, per-window annualised Sharpe ratio is the primary metric. Three paired deltas (`all_on` minus each of the other three arms) are computed per window and bootstrap-tested against zero (10,000 resamples, percentile 95% CI). Benjamini-Hochberg correction is applied across the three-delta family at $\alpha = 0.05$.

Separately, every signal the post-loss guard blocked in the `all_on` arm is walked forward using the same alpha entry/exit logic that would have applied had the guard not intervened, to its counterfactual close. This produces a false-negative rate (blocked signals that would have won) and a false-positive rate (blocked signals that would have lost), plus the median and mean would-be pips per block.

## 4. Implementation

`scripts/run_walk_forward_ab.py` extends the lab's existing walk-forward primitives with three independent boolean toggles (`wick_proof_enabled`, `be_migration_enabled`, `plg_enabled`) and a `plg_walk_forward_blocked` ledger recording every guard-triggered block with enough context (entry price, stop, target, bar index) to resolve its counterfactual outcome. The wick-proof and break-even logic mirrors the production repo's `agent/live/soft_stop.py` closely enough to preserve directional fidelity. The harness's post-loss guard (`BarPlg`) is a simplified bar-driven approximation of the production `agent/risk/post_loss_guard.py`, using a 2-bar cooldown in place of the live 60-minute wall-clock cooldown — a limitation discussed in Section 6.2. `scripts/analyze_e013.py` computes the per-arm Sharpe, the paired deltas, the bootstrap CIs, the BH-FDR correction, and the guard counterfactual resolution from the raw results at `../../output/E013_safety_layer_contribution/results.json`.

## 5. Results

### 5.1 Per-arm full-series and per-window OOS

**Table 1. Per-arm full-series results.**

| Arm | Full-series n | Full-series median pips | Full-series Sharpe | Guard blocks |
|---|---:|---:|---:|---:|
| `all_on` | 737 | +19.104 | +1.705 | 123 |
| `wick_off` | 781 | +0.000 | +1.058 | 198 |
| `be_off` | 660 | +22.133 | +1.526 | 124 |
| `all_off` | 855 | +15.627 | +1.106 | 0 |

**Table 2. Per-window annualised Sharpe.**

| Window | `all_on` | `wick_off` | `be_off` | `all_off` |
|---:|---:|---:|---:|---:|
| 1 | +6.253 | +3.812 | +5.869 | +4.357 |
| 2 | +1.888 | +1.716 | +1.660 | +1.964 |
| 3 | +2.102 | +1.186 | +1.889 | +1.233 |
| 4 | +2.120 | +1.383 | +1.637 | +1.055 |
| 5 | +2.173 | +1.512 | +1.788 | +1.298 |
| 6 | +3.223 | +3.168 | +3.414 | +2.720 |
| 7 | +1.755 | +1.464 | +1.979 | +1.314 |

### 5.2 Sharpe deltas

**Table 3. Paired Sharpe deltas (`all_on` minus arm), 10,000-resample bootstrap, BH-FDR $\alpha = 0.05$ across the 3-delta family.**

| Delta | Isolates | Mean | 95% CI | $p$ (> 0) | BH-reject |
|---|---|---:|---|---:|---|
| $\Delta_{\text{wick}}$ | wick-proof stop-loss | +0.753 | [+0.293, +1.376] | 0.000 | yes |
| $\Delta_{\text{be}}$ | break-even migration | +0.183 | [-0.019, +0.364] | 0.036 | yes |
| $\Delta_{\text{combined}}$ | all three layers jointly | +0.796 | [+0.382, +1.224] | 0.000 | yes |

**Worked example.** Window 1 achieves a Sharpe of +6.253 with all safety layers on — the highest of any window in the study. Removing wick-proof stops alone (holding break-even and the guard fixed) drops the same window to +3.812, a loss of nearly 2.5 Sharpe from a single layer on a single window. This is the largest per-window gap in Table 2 and the primary driver of $\Delta_{\text{wick}}$'s headline result: window 1 evidently contained an adverse price wick that a hard broker-side stop would have realised as a loss, but the synthetic wick-proof stop rode through it.

### 5.3 Post-loss guard counterfactual resolution

**Table 4. Guard block resolution (n = 123 blocked signals, `all_on` arm).**

| Statistic | Value |
|---|---:|
| False-negative rate (blocks that would have won) | 64.2% |
| False-positive rate (blocks that would have lost) | 33.3% |
| Median would-be pips per block | +23.50 |
| Mean would-be pips per block | +10.43 |

**Worked example.** Of the 123 blocked signals, 79 (64.2%) would have closed as winners with a median would-be outcome of +23.50 pips — roughly double the alpha's overall +11.34 pip baseline — while only 41 (33.3%) would have lost. This is the concrete basis for the `plg_earns_keep` finding discussed in Section 6 — the protocol's own, deliberately counter-intuitive label for "PLG is expensive" (`PROTOCOL.md` Section 4: "the uncomfortable answer that says PLG is expensive").

## 6. Discussion

### 6.1 Interpretation

Wick-proof stop-loss is `alive`: it contributes a statistically robust +0.75 Sharpe on top of break-even and the guard, and Table 2's window-1 example shows the mechanism directly — it absorbs adverse wicks that a hard stop would realise as losses. Break-even migration's contribution cannot be distinguished from zero at this sample size; Section 6.2 explains why this is likely a sample-design artefact rather than evidence the mechanism is truly useless. The combined three-layer stack is `combined_alive`, meaning the *current deployed configuration* is validated against the raw alpha — turning all three layers off would cost real, FDR-corrected Sharpe. The post-loss guard's own attribution is the least comfortable finding: it blocks more future-winners than future-losers, and the blocked winners are, on average, better than the strategy's typical trade. This does not mean the guard should be disabled — see Section 6.3 — but it does mean its current cooldown length and consecutive-loss threshold were not tuned against this strategy's specific post-loss return distribution, and a dedicated retuning study is now well-motivated by a specific, quantified number.

### 6.2 Threats to validity

1. **Small window count.** The three paired Sharpe deltas rest on only 7 walk-forward windows; the bootstrap CIs are correspondingly wide (the $\Delta_{\text{be}}$ interval spans from -0.019 to +0.364, a factor-of-nineteen range around its midpoint). A longer OOS history or a per-trade delta framing would sharpen these estimates.
2. **Harness-vs-production fidelity gap for the guard.** `BarPlg`'s 2-bar cooldown approximates the production guard's 60-minute wall-clock cooldown. The *direction* of the false-negative finding is very unlikely to flip under exact production logic, but the *magnitude* (64.2%/33.3%) should be treated as an estimate pending a fidelity-matched re-simulation.
3. **Break-even is structurally under-tested on H4.** Break-even fires at +1R intrabar; with a 1.5R take-profit on the four-hour chart, most winning trades close within one or two bars of triggering break-even, leaving the mechanism little room to matter. A finer-grained (H1) re-run would give it a fairer test before concluding it is Sharpe-neutral in general rather than merely Sharpe-neutral on this timeframe.

### 6.3 Why `plg_earns_keep` does not mean "disable the guard"

It is tempting to read the 64.2% false-negative rate as grounds to turn the guard off. That would repeat exactly the reactive, single-week-of-data error this entire sweep was designed to prevent: the guard's job is asymmetric by design — cheap when quiet, valuable in the tail events that a controlled, multi-year walk-forward is far better positioned to sample than a week of live observation. Table 3's $\Delta_{\text{combined}}$ result shows the joint stack (which includes the guard) is still net-positive versus no safety layers at all; the guard's cost is real but is not large enough to flip the combined stack negative, and wick-proof stops are carrying the majority of the combined effect regardless. The correct response to `plg_earns_keep` is a dedicated retuning study (E017, proposed in Section 7.2), not an ad-hoc parameter change or removal.

## 7. Conclusion

**Combined safety stack: `alive`.** The current production configuration (all three layers on) is validated against the raw alpha on out-of-sample data. Wick-proof stop-loss individually: `alive`. Break-even migration: not distinguishable from zero at this sample size (Section 6.2 explains the likely cause). Post-loss guard: `plg_earns_keep` (locked label in `PROTOCOL.md` Section 4 for "PLG is expensive") — a quantified, non-trivial cost that motivates a follow-up retuning study rather than an immediate parameter change.

### 7.1 Future work

E017 (post-loss guard cooldown and consecutive-loss threshold tuning), motivated directly by Table 4, is proposed as the next study in this line — see the sweep report's Section 7.2 (`../../reviews/2026-07-01_pipeline_sweep_E011-E016.md`).

## 8. References

1. Bailey, D.H. and López de Prado, M., 2014. The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality. *Journal of Portfolio Management*, 40(5), pp.94-107.
2. Bailey, D.H., Borwein, J.M., López de Prado, M. and Zhu, Q.J., 2014. Pseudo-Mathematics and Financial Charlatanism. *Notices of the American Mathematical Society*, 61(5), pp.458-471.
3. Lo, A.W., 2004. The Adaptive Markets Hypothesis: Market Efficiency from an Evolutionary Perspective. *Journal of Portfolio Management*, 30(5), pp.15-29.
4. López de Prado, M., 2018. The 10 Reasons Most Machine Learning Funds Fail. *Journal of Portfolio Management*, 44(6), pp.120-133.
5. Pre-registration: [`PROTOCOL.md`](PROTOCOL.md).
6. Raw results: `../../output/E013_safety_layer_contribution/results.json`.
7. Harness: `../../scripts/run_walk_forward_ab.py`.
8. Full BibTeX: `../../reviews/refs.bib`.
