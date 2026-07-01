# Research-Pipeline Sweep E011-E016: Small-Stop Expectancy, Zone-Quality Gating, and Safety-Layer Attribution for a Live Counter-Trend Forex Alpha — Progress Report

**Author:** Fiyinfoluwa Akano
**Date:** 2026-07-01 · Version 1.0
**Repos:** `github.com/TheFinix13/Trading_AI_model` (production) · research lab (this repo)
**Type:** Pre-registered research sweep, personal R&D portfolio entry
**Status:** Closed. Three studies executed (E011, E013, E014); three cancelled by pre-declared dependency gates (E012, E015, E016).

## Abstract

A live counter-trend forex strategy (`zone_d1_against`, deployed on a $1,000 demo account) raised six open questions after a week of manual chart review: whether small-stop trades carry distinct expectancy, whether entering on a pending limit inside the zone would tighten stops without losing edge, whether the deployed safety layers (wick-proof stop-loss, break-even migration, a post-loss guard) are earning their keep, whether gating entries on a zone-quality score improves risk-adjusted return, and whether re-entering on a tighter-stop signal during an open drawdown would help. We answer these questions with six pre-registered protocols evaluated on a 7-window walk-forward split of EUR/USD H4 bars (2019-2025, 855 baseline trades), using bootstrap confidence intervals and Benjamini-Hochberg false-discovery-rate correction throughout. Three studies executed to a locked verdict: the alpha's edge is bucket-agnostic across stop distances (E011, `stopped_at_stage_1`); the combined safety-layer stack contributes +0.80 Sharpe over the raw alpha with wick-proof stops alone contributing +0.75 (E013, `combined_alive`), but the post-loss guard blocks 64% of would-be winners against only 33% of would-be losers (`plg_earns_keep`, the protocol's own label for "PLG is expensive"); and a zone-quality entry gate finds a real effect (+26 pips/trade at the strictest threshold, more than double the +11.34 pips/trade baseline) that is too data-hungry for production (12% of baseline trade volume, `parked_low_yield`). Three follow-on studies were formally cancelled because their pre-declared dependency gates did not clear. No production code path for the live agent's entry, exit, or sizing logic changed as a result of this sweep; two non-strategy safety features (a weekly rejection-review report and a portfolio-wide 5% risk ceiling) shipped independently of the research verdicts. The sweep's main practical contribution is a reusable safety-layer attribution harness and a documented, falsified hypothesis about small-stop expectancy that closes a specific investigation thread rather than leaving it open indefinitely.

## 1. Introduction

### 1.1 Motivation

A retail trader running an automated EUR/USD system on a small account faces a recurring temptation: eyeball a week of live trades, notice a pattern, and change the code. The multi-pair-trading-agent project deliberately resists this. Its one governing rule is that an idea only touches the live strategy after it survives a pre-registered study, not after a good week or a bad week (see the project's `docs/00-journey.md` philosophy and `PROTOCOL_DISCIPLINE.md` in this lab).

The immediate trigger for this sweep was a manual review of two weeks of `zone_d1_against` H4 charts on the live $1,000 demo account. That review surfaced six concrete, falsifiable questions rather than six vague impressions: (1) do trades with small stop-losses make more money per trade than trades with wide stops, because a wide stop implies a worse entry; (2) would entering with a pending limit order placed inside the demand or supply zone — rather than waiting for price to touch the zone edge — achieve the same signal with a much tighter stop; (3) are the three safety layers riding on top of the raw alpha (a wick-proof synthetic stop, break-even stop migration, and a post-loss guard that pauses trading after a losing streak) actually adding return, or are they costing more in blocked opportunity than they save in avoided losses; (4) does the zone-quality score that the detector already computes but never uses at signal time predict better trades; (5) should trade conviction (currently a hardcoded constant) scale with that same quality score; and (6) when a tighter-stop signal fires on a symbol that already has an open, losing position, would closing and re-entering (or flipping) outperform holding through.

### 1.2 Research questions and hypotheses

Each question above maps to one pre-registered protocol (Table 1). All six were registered in `EXPERIMENTS.md` before any of the underlying trade data was touched for that study, per the lab's `PROTOCOL_DISCIPLINE.md`.

**Table 1. The six studies, their questions, and their pre-declared dependency gates.**

| ID | Short name | Question | Depends on |
|---|---|---|---|
| E011 | `small_stop_subset_expectancy` | Does `zone_d1_against` H4 have a distinct, higher expectancy on the small-stop subset of trades? | none (uses existing walk-forward output) |
| E012 | `pending_limit_inside_zone` | Does entering via a pending limit inside the zone preserve the alpha's edge with a 7-15 pip effective stop? | E011 shows small-stop bucket expectancy $\geq 0$ |
| E013 | `safety_layer_contribution` | What is the Sharpe-ratio contribution of each of wick-proof stop-loss, break-even migration, and the post-loss guard? | A/B toggle harness built (this sweep, Wave 1) |
| E014 | `quality_score_entry_gate` | Does gating entries on the zone's quality score improve out-of-sample Sharpe? | none (detector already computes the score) |
| E015 | `conviction_from_quality` | Should position-sizing conviction scale with the same quality score instead of a fixed constant? | E014 positive |
| E016 | `reentry_flip_on_tighter_stop` | Does closing-and-re-entering on a tighter-stop signal outperform holding through an open drawdown? | E011 and E014 both positive |

### 1.3 Contributions

This report documents four falsifiable contributions:

1. A reusable four-arm leave-one-out walk-forward harness (`scripts/run_walk_forward_ab.py`) that isolates the marginal Sharpe contribution of each of three independent risk-management layers on the same trade stream, with a fixed random seed for arm parity.
2. The first quantified false-negative / false-positive rate for a live post-loss guard, computed by walking every guard-triggered block forward to its counterfactual outcome (n = 123 blocks).
3. A negative result for the small-stop-expectancy hypothesis, closing an open investigation thread that would otherwise have kept recurring in weekly reviews.
4. A positive-but-underpowered result for zone-quality gating that is precise enough to specify exactly what a follow-up study needs to change (a lower threshold grid) rather than leaving the question open-ended.

### 1.4 Report outline

Section 2 places the six questions in the context of prior work on stop-loss placement, risk-management overlays, and the multiple-testing problem in trading research. Section 3 specifies the shared methodology: the strategy under test, the walk-forward protocol, and the statistical pipeline used by every study. Section 4 describes what was implemented, including the A/B harness and the three study-specific scripts. Section 5 reports results per study. Section 6 discusses what the combined evidence means for the live agent, the threats to validity, and why no production trading logic changed. Section 7 concludes and lists the two backlog items the sweep opened for a future session.

## 2. Background and Related Work

### 2.1 Retail technical trading and the zone-fade strategy

The strategy under test enters a fade against price when it returns to a four-hour supply or demand zone that sits against the prevailing daily trend. Academic opinion on whether technical trading rules like this carry genuine expectancy is split. Menkhoff and Taylor's survey of the foreign-exchange professional community finds that technical analysis remains a first-order input to real trading desks despite decades of efficient-markets scepticism [@menkhoff2007technical]. Earlier genetic-programming studies found tradeable, if shrinking, expectancy in FX technical rules once realistic transaction costs were applied [@neely1997technical]. The methodological risk in this literature is well known: naive backtests of technical rules are prone to data-snooping bias, where hundreds of parameter variants are tried and only the best-looking one is reported [@sullivan1999datasnooping; @white2000reality]. The `zone_d1_against` strategy's own validation history (E001-E007 in this lab, and the walk-forward study E004 in the production repo) was designed with this risk in mind: parameters were frozen before the out-of-sample walk-forward windows were evaluated, and the +11.34 pips/trade baseline used throughout this sweep is the frozen E004 headline, not a number re-optimised for this sweep.

### 2.2 Stop-loss placement and exit-side risk overlays

The question of whether a wider or a tighter stop-loss changes a strategy's risk-adjusted return is a capital-allocation problem before it is a signal-quality problem. Kelly's original criterion frames position sizing (and by extension, the fraction of capital exposed to a given stop distance) as an optimisation over the geometric growth rate of capital, not the arithmetic expectancy of a single bet [@kelly1956]. Chan's practitioner-oriented treatment of quantitative trading strategy design discusses stop-loss and take-profit placement as a joint problem with position sizing, warning against the common retail mistake of tuning stop distance in isolation from bet size [@chan2009quantitative]. E011's question — whether the *subset* of trades with naturally small stops has different expectancy from the pooled sample — is distinct from the sizing question and is answerable directly from historical trade data without touching the sizing model, which is why it was pre-registered as a descriptive re-analysis rather than a re-simulation.

Wick-proof and break-even stop mechanics are common practitioner risk-management overlays that are rarely isolated and measured on their own in published academic work; most treatments bundle exit-side risk controls into the backtest without reporting their marginal contribution. This sweep's E013 study borrows the leave-one-out ablation design standard in machine-learning evaluation — remove one component at a time, holding all others fixed, and attribute the performance delta to the removed component — and applies it to a trading system's risk-management stack rather than a model architecture.

### 2.3 Post-loss controls and the false-negative problem

A post-loss guard (also called a "cooldown" or "circuit breaker" in some retail trading literature) pauses a strategy after a losing streak on the premise that losses cluster during adverse regimes. Lo's adaptive-markets framing supports the premise that a strategy's edge is regime-dependent rather than constant [@lo2004adaptive], which is the theoretical justification most retail systems cite for having a guard at all. What is rarely measured, in either the practitioner or the academic literature, is the guard's false-negative rate: how often it blocks a signal that would have won. López de Prado's critique of common failure modes in quantitative fund design specifically flags "not measuring the true cost of a risk overlay" as one of the ten reasons machine-learning-driven funds under-perform their backtest [@lopezdeprado2018tactical]. E013's walk-forward-the-block methodology, where every guard-triggered block is resolved to its counterfactual outcome using the same signal-generation logic that would have fired had the guard not intervened, is a direct answer to that critique, applied to this system's specific guard rather than treated as a settled question.

### 2.4 Pre-registration and multiple-testing discipline

The single biggest methodological risk running through this entire sweep is testing many hypotheses against the same underlying trade data and reporting only the ones that look good. Harvey, Liu and Zhu's survey of asset-pricing factor discovery estimates that most published anomalies would fail a proper multiple-testing correction, precisely because researchers test dozens of variants before publishing the one significant result [@harvey2016cross]. The remedy used throughout this sweep is threefold and is inherited from the lab's standing `PROTOCOL_DISCIPLINE.md`: every study's hypothesis, sample, and stop rule is written down and committed to version control *before* the relevant trade data is touched (following the pre-registration norm formalised for behavioural science by Nosek et al. [@nosek2018preregistration] and adapted here for a systematic-trading context); every family of related statistical tests within a study is corrected using the Benjamini-Hochberg false-discovery-rate procedure [@benjamini1995controlling]; and every confidence interval on a small-sample statistic (as low as 7 paired walk-forward windows in E013) is computed by bootstrap resampling rather than a normal-theory approximation that would understate uncertainty at this sample size [@efron1993bootstrap]. Bailey and López de Prado's deflated Sharpe ratio and their broader warning about backtest overfitting [@bailey2014deflated; @bailey2014pseudo] motivate treating every Sharpe number in this report as provisional on the number of configurations tried to reach it — a discipline this sweep enforces structurally by locking each study's arm count and threshold grid before execution.

### 2.5 Gap this sweep addresses

No source found in this literature review reports a pre-registered, false-discovery-corrected attribution of a *specific deployed* retail trading system's exit-side risk overlays, including a walked-forward false-negative rate for its post-loss guard, alongside a companion study on entry-side quality gating evaluated on the same trade stream. This sweep is narrow in scope by design: it is not a claim of a novel general method, but a documented, falsifiable application of established statistical discipline (pre-registration, FDR correction, bootstrap CIs, leave-one-out ablation) to one specific live system's six open questions.

## 3. Methodology

### 3.1 Strategy under test

All six studies evaluate the same underlying alpha, `SupplyDemandAlpha` running in `zone_d1_against` mode: on the four-hour (H4) chart, price touching a supply or demand zone is faded (traded against the touch) only when that touch is *against* the daily-chart (D1) trend, with the D1 bias computed over a 10-bar lookback and a minimum 60-pip move threshold. This parameterisation is frozen from the production repo's E001-E007 validation chain and was not re-tuned for this sweep; every study either re-uses the existing E004 walk-forward trade log directly (E011) or re-runs the same frozen alpha under an additional toggle (E013, E014) rather than re-optimising its entry rule.

### 3.2 Data and walk-forward protocol

The underlying instrument is EUR/USD H4 bars, 2015-2025, cached as Parquet in the production repo and read read-only by this lab via a `PYTHONPATH` pointer (no data is duplicated between repos). The walk-forward split follows the frozen E004 design: seven non-overlapping out-of-sample (OOS) windows spanning 2019-2025, each preceded by an in-sample (IS) fitting window used only for threshold selection in E014 (Section 3.5.3), never for parameter re-fitting of the alpha itself. The pooled OOS baseline across all seven windows is 855 raw trades at a median +11.34 pips/trade — this is the fixed comparator every study measures itself against.

### 3.3 Pre-registration and stop rules

Every study's protocol (`experiments/E0XX_*/PROTOCOL.md`) was committed to version control before its trade data was touched, specifying: the exact hypothesis in falsifiable form; the locked statistic that decides the verdict (median OOS pips/trade, Sharpe delta, or trade-count ratio depending on the study — see `docs/methodology/gate_verdict_registry.md` for the house rule against choosing a comparator statistic after seeing the data); the sample-size gate below which a result is `parked_insufficient_n` rather than claimed; and a pre-declared stop rule that, if triggered, formally cancels any dependent downstream study without requiring a new decision at the time. This last point matters for interpreting Section 5: E012, E015, and E016 were not abandoned by a judgement call made after seeing disappointing results — they were cancelled automatically by conditions written into E011's and E014's protocols before those studies ran.

### 3.4 Statistical pipeline

Three tools recur across all three executed studies:

1. **Bootstrap confidence intervals.** Every headline effect size (a per-bucket median in E011, a per-arm Sharpe delta in E013, a pooled OOS median in E014) is accompanied by a 95% confidence interval from 5,000-10,000 resamples with a fixed seed, following the nonparametric bootstrap of Efron and Tibshirani [@efron1993bootstrap]. This avoids the normal-theory approximation that would be unreliable at the small per-window and per-bucket sample sizes involved (as few as 7 paired windows in E013, as few as 19 trades in E011's thinnest bucket).
2. **Benjamini-Hochberg false-discovery-rate correction.** Every study tests a *family* of related hypotheses at once (5 stop-buckets in E011, 3 Sharpe deltas in E013, 3 thresholds in E014). Benjamini-Hochberg correction at $\alpha = 0.05$ is applied across each family before any individual result is called significant [@benjamini1995controlling], per the lab's standing `docs/methodology/verdict_registry.md`.
3. **Locked-statistic discipline.** Following the house `gate_verdict_registry.md` rule (itself a direct response to the post-hoc-statistic risk documented by Harvey, Liu and Zhu [@harvey2016cross] and by Bailey and López de Prado's overfitting critique [@bailey2014pseudo]), each protocol names its one deciding statistic before execution. Alternative statistics are reported as diagnostic cross-checks in this report but never substituted for the locked one after the fact.

### 3.5 Per-study designs

#### 3.5.1 E011 — small-stop subset expectancy

A purely descriptive re-analysis: the 855-trade E004 walk-forward log is stratified into five stop-distance buckets (0-10, 10-20, 20-40, 40-80, and 80+ pips, measured at signal time), and the bootstrap 95% CI of each bucket's median pips/trade is compared against the pooled cross-bucket median. No new simulation is run; no code path changes. The pre-declared n-gate is 30 trades per bucket for an `alive_*` verdict to be claimed (buckets below this threshold still have their statistics reported, per the lab's compute-vs-claim rule, but cannot be called alive).

#### 3.5.2 E013 — safety-layer contribution

A new four-arm leave-one-out walk-forward harness (Section 4.1) re-simulates the alpha under four configurations: all three safety layers on (`all_on`), wick-proof stop-loss disabled (`wick_off`), break-even migration disabled (`be_off`), and all three layers disabled (`all_off`, the raw alpha). Each arm is run across the same seven OOS windows with a fixed random seed for parity. Three paired Sharpe deltas are computed (`all_on` minus each of the other three arms) and bootstrap-tested against zero. Separately, every signal that the post-loss guard blocked in the `all_on` arm is walked forward using the same alpha logic to its counterfactual close, producing a false-negative rate (blocks that would have won) and a false-positive rate (blocks that would have lost).

#### 3.5.3 E014 — quality-score entry gate

The zone detector already computes a 0-100 quality score for every zone (`QualifiedZone.quality.quality_score`) that the live alpha currently ignores at signal time. E014 tests three candidate thresholds ($\theta \in \{30, 50, 70\}$) as a hard entry gate: only take a signal if the touched zone's quality score is at or above $\theta$. For each of the seven walk-forward windows, the threshold with the highest in-sample Sharpe is locked before that window's out-of-sample fold is evaluated — this prevents the threshold from being chosen using OOS information. The locked-per-window thresholds are then pooled and evaluated against the trade-count ratio and median-pips criteria declared in the protocol.

## 4. Implementation

### 4.1 A/B walk-forward driver

The core new artefact from this sweep is `scripts/run_walk_forward_ab.py`, which extends the lab's existing walk-forward primitives (originally built for E004) with three independent boolean toggles — `wick_proof_enabled`, `be_migration_enabled`, `plg_enabled` — plus a `plg_walk_forward_blocked` ledger that records every signal the guard blocks together with enough context (entry price, stop, target, bar index) to resolve its counterfactual outcome later. The wick-proof and break-even logic in the harness mirrors the production repo's `agent/live/soft_stop.py` and breakeven-migration behaviour closely enough to preserve directional fidelity, though the harness's post-loss guard (`BarPlg`) is a simplified bar-driven approximation of the production `agent/risk/post_loss_guard.py` (a 2-bar cooldown standing in for the live 60-minute wall-clock cooldown) — a limitation discussed further in Section 6.3.

### 4.2 Study execution scripts

Three thin driver scripts sit on top of the shared harness and the E004 trade cache: `scripts/run_e011.py` stratifies the existing trade log by stop bucket and renders the bootstrap table; the E013 arms are produced directly by `run_walk_forward_ab.py` with `scripts/analyze_e013.py` computing the paired deltas, bootstrap CIs, BH-FDR correction, and the PLG false-negative/positive resolution; `scripts/run_e014.py` runs the per-window IS/OOS threshold-locking loop described in Section 3.5.3.

### 4.3 Reproducibility

Every study's raw output is committed alongside its report: `experiments/E011_small_stop_subset_expectancy/{PROTOCOL,REPORT,MANIFEST}.md`, `experiments/E013_safety_layer_contribution/{PROTOCOL,REPORT}.md` with raw results at `output/E013_safety_layer_contribution/results.json`, and `experiments/E014_quality_score_entry_gate/{PROTOCOL,REPORT}.md`. All three studies are re-runnable from a clean checkout with `PYTHONPATH=../multi-pair-trading-agent:.` set and the production repo's Parquet cache present; no external data download is required for exact reproduction.

## 5. Results

### 5.1 E011 — the alpha's edge is bucket-agnostic

**Headline: the pooled OOS median across all 463 stop-classified trades is +9.99 pips/trade, and no individual stop-distance bucket's confidence interval sits above or below that pooled figure.** Table 2 gives the full per-bucket breakdown.

**Table 2. E011 per-bucket walk-forward results (5,000-resample bootstrap, BH-FDR $\alpha=0.05$ across the 5-bucket family).**

| Stop bucket | n | Hit rate | Median pips/trade | 95% CI | BH-reject | Verdict |
|---|---:|---:|---:|---|---|---|
| 0-10 pips | 19 | 58% | +11.42 | [+0.00, +0.00] | no | `parked_insufficient_n` |
| 10-20 pips | 141 | 51% | +15.18 | [-12.14, +18.05] | no | `dead` |
| 20-40 pips | 162 | 48% | -20.31 | [-23.13, +33.91] | no | `dead` |
| 40-80 pips | 113 | 50% | -40.50 | [-45.40, +63.45] | no | `dead` |
| 80+ pips | 28 | 57% | +125.85 | [+0.00, +0.00] | no | `parked_insufficient_n` |

**Worked example.** Consider a specific 10-20 pip bucket trade at the median: a EUR/USD H4 zone touch with a 15-pip stop closes with a +15.18 pip median outcome across 141 such trades in the sample, a hit rate of 51%. Compare this to an 80+ pip bucket trade: a wider-stop signal closes with a much larger +125.85 pip median across only 28 trades — but the wide interval (collapsing to a degenerate [+0.00, +0.00] CI because the bucket sits below the 30-trade n-gate) means this number cannot be trusted as a stable estimate of what a future 80-pip-stop trade will do. Both buckets are consistent with the same underlying +9.99 pip pooled expectancy once sampling noise is accounted for; neither is a distinct, exploitable regime.

The two motivating questions this answers directly: (1) small-stop trades do not have materially higher expectancy than the pooled alpha, so there is no efficiency gain from filtering for them; and (2) the premise behind E012 (that tightening the effective stop via pending-limit entry would capture a distinct small-stop edge) is falsified before E012 needed to run a single simulation.

### 5.2 E014 — a real but data-starved effect

**Headline: at the strictest quality threshold ($\theta = 70$), the pooled out-of-sample median is +26.09 pips/trade — more than double the +11.34 pip frozen baseline — but only 102 trades survive the gate, 12% of the 855-trade ungated baseline.** Table 3 shows the per-window threshold-locking process; Table 4 shows the pooled result.

**Table 3. E014 per-window in-sample Sharpe by threshold, locked threshold, and its out-of-sample outcome.**

| Window | IS Sharpe $\theta{=}30$ | IS Sharpe $\theta{=}50$ | IS Sharpe $\theta{=}70$ | Locked $\theta$ | OOS n | OOS median (pips) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | +1.565 | +1.522 | +2.191 | 70 | 7 | +24.82 |
| 2 | +1.968 | +1.989 | +2.467 | 70 | 9 | +33.99 |
| 3 | +2.288 | +2.389 | +2.158 | 50 | 33 | +19.17 |
| 4 | +2.431 | +2.410 | +3.036 | 70 | 23 | +53.91 |
| 5 | +1.645 | +1.842 | +4.247 | 70 | 10 | -22.47 |
| 6 | +0.805 | +0.926 | +2.557 | 70 | 6 | +6.32 |
| 7 | +0.728 | +0.764 | +2.611 | 70 | 14 | +48.67 |

**Table 4. E014 pooled out-of-sample outcome vs baseline.**

| Statistic | Value |
|---|---:|
| Pooled OOS trades | 102 |
| Trade-count ratio vs 855-trade baseline | 11.9% |
| Hit rate | 62.7% |
| Median pips/trade | +26.09 |
| Bootstrap 95% CI | [+16.17, +33.99] |
| Frozen E004 baseline | +11.34 |

**Worked example.** Window 4 locked $\theta = 70$ from an in-sample Sharpe of +3.036 (the highest of the three candidates in that fold) and produced 23 out-of-sample trades at a +53.91 pip median — almost five times the pooled baseline. Window 5 also locked $\theta = 70$, from an in-sample Sharpe of +4.247, the single highest IS Sharpe recorded in the study, yet its out-of-sample fold returned a *negative* -22.47 pip median across 10 trades. The same threshold, chosen by the same in-sample criterion, produced the study's best and one of its worst out-of-sample windows. This is the concrete anatomy of what "too data-hungry" means in Table 4's headline: with only 6-33 trades surviving the gate per window, a single adverse window can swing the pooled statistic substantially, which is exactly why the protocol's pre-declared 25% trade-count floor exists as a guardrail independent of the median-pips result.

The confidence interval [+16.17, +33.99] sits entirely above the +11.34 baseline — this is a real, not spurious, effect by the study's own locked statistic. But the pre-declared trade-count floor (25% of baseline volume) was not met at 11.9%, which is why the verdict is `parked_low_yield` rather than `alive_positive`: the gate is too aggressive to generate a survivable trade frequency on a live account, even though the trades it does approve are demonstrably better than the pool.

### 5.3 E013 — the safety stack earns its keep, but the guard is expensive

**Headline: disabling all three safety layers costs -0.80 Sharpe relative to running them together (95% CI [+0.38, +1.22], Benjamini-Hochberg reject); of that, wick-proof stop-loss alone accounts for +0.75 Sharpe (CI [+0.29, +1.38]), while break-even migration's contribution (+0.18, CI [-0.02, +0.36]) cannot be distinguished from zero at this sample size.** Table 5 gives the per-arm summary; Table 6 the per-window Sharpe; Table 7 the three deltas.

**Table 5. E013 per-arm full-series results (737-855 trades depending on arm, 7 OOS windows).**

| Arm | Trades | Median pips | Sharpe | PLG blocks |
|---|---:|---:|---:|---:|
| `all_on` (production posture) | 737 | +19.10 | +1.705 | 123 |
| `wick_off` | 781 | +0.00 | +1.058 | 198 |
| `be_off` | 660 | +22.13 | +1.526 | 124 |
| `all_off` (raw alpha) | 855 | +15.63 | +1.106 | 0 |

**Table 6. E013 per-window annualised Sharpe, all four arms.**

| Window | `all_on` | `wick_off` | `be_off` | `all_off` |
|---:|---:|---:|---:|---:|
| 1 | +6.253 | +3.812 | +5.869 | +4.357 |
| 2 | +1.888 | +1.716 | +1.660 | +1.964 |
| 3 | +2.102 | +1.186 | +1.889 | +1.233 |
| 4 | +2.120 | +1.383 | +1.637 | +1.055 |
| 5 | +2.173 | +1.512 | +1.788 | +1.298 |
| 6 | +3.223 | +3.168 | +3.414 | +2.720 |
| 7 | +1.755 | +1.464 | +1.979 | +1.314 |

**Table 7. E013 paired Sharpe deltas (`all_on` minus each arm), 10,000-resample bootstrap, BH-FDR $\alpha = 0.05$ across the 3-delta family.**

| Delta | Isolates | Mean | 95% CI | $p$ (> 0) | BH-reject |
|---|---|---:|---|---:|---|
| $\Delta_{\text{wick}}$ | wick-proof stop-loss | +0.753 | [+0.293, +1.376] | 0.000 | yes |
| $\Delta_{\text{be}}$ | break-even migration | +0.183 | [-0.019, +0.364] | 0.036 | yes |
| $\Delta_{\text{combined}}$ | all three layers jointly | +0.796 | [+0.382, +1.224] | 0.000 | yes |

**Worked example — window 1.** With all three safety layers on, window 1 produces a Sharpe of +6.253, the highest of any window in the study. Turning wick-proof stops off (holding break-even and the guard fixed) drops that same window to +3.812 — a loss of nearly 2.5 Sharpe from one layer, on one window, and the single largest per-window gap in the table. This is the mechanism behind $\Delta_{\text{wick}}$'s headline: window 1 evidently contained at least one large adverse wick that a hard broker-side stop would have realised as a loss, but the wick-proof synthetic stop rode through and let the position recover.

**PLG false-negative and false-positive analysis.** Every one of the 123 signals the post-loss guard blocked in the `all_on` arm was walked forward using the same alpha logic to its counterfactual close. Table 8 reports the result.

**Table 8. E013 post-loss guard counterfactual resolution (n = 123 blocked signals, `all_on` arm).**

| Statistic | Value |
|---|---:|
| Blocks that would have won (false-negative rate) | 64.2% |
| Blocks that would have lost (false-positive rate) | 33.3% |
| Median would-be pips per block | +23.50 |
| Mean would-be pips per block | +10.43 |

**Worked example.** Of the 123 signals the guard suppressed, 79 (64.2%) would have closed as winners had they been allowed to fire, with a median would-be outcome of +23.50 pips — roughly double the alpha's overall +11.34 pip baseline. Only 41 (33.3%) would have lost. This is the arithmetic behind the study's `plg_earns_keep` finding (the PROTOCOL.md's own, deliberately counter-intuitive label for "PLG is expensive" — see the note below): on this specific cell, the guard is blocking money more often than it is preventing losses, even though the joint safety stack (Table 7's $\Delta_{\text{combined}}$) is still net-positive because wick-proof stops are carrying the combined result.

*A note on the verdict name.* `E013_safety_layer_contribution/PROTOCOL.md` Section 4 locks two PLG verdict labels before the data was touched: `plg_earns_keep`, defined as "the uncomfortable answer that says PLG is expensive", and `plg_dead`, defined as "the comforting answer that PLG is doing its job". Both names are deliberately named from an adversarial framing (does the guard block money we would have made?) rather than from an intuitive reading, and a first-time reader should expect the opposite of what the label suggests. This report uses the locked label as the formal verdict and glosses it in plain English at each use to avoid ambiguity.

The study's three-part verdict, consistent with the locked statistic in each case: wick-proof stop-loss `alive` (keep it); break-even migration not distinguishable from zero on this sample (its 1.5R-target design means most winners close within 1-2 bars on H4 before break-even has a chance to matter — see Section 6.3); and the joint safety stack `combined_alive`, meaning the *current production configuration* (all three layers on) is validated against the raw alpha, even though one of its three components (the guard) has a documented and non-trivial cost that a future study should address directly rather than by simply disabling it.

### 5.4 E012, E015, E016 — cancelled by pre-declared dependency gates

None of the three downstream studies executed. Each was formally cancelled, not abandoned, by a condition written into an upstream protocol before that upstream study ran:

- **E012** (`pending_limit_inside_zone`) required E011 to show small-stop bucket expectancy $\geq 0$ relative to the pooled baseline. Section 5.1 shows every bucket's CI overlapping the pool; the premise that a distinct small-stop edge exists to preserve was falsified, so E012's question has no object to test.
- **E015** (`conviction_from_quality`) required E014 to reach an `alive_*` verdict. Section 5.2's `parked_low_yield` result means the quality-score signal, while real, is not validated at production-usable volume; wiring conviction to it would propagate an unvalidated, low-n effect into live position sizing.
- **E016** (`reentry_flip_on_tighter_stop`) required *both* E011 and E014 to be positive, because its premise depends on being able to identify a "better" tighter-stop or higher-quality signal during an open drawdown. With neither discriminator validated, a re-entry rule built on top of them would be re-entering on noise.

Formal stop notices for all three are filed at `experiments/E012_pending_limit_inside_zone/STOP_NOTICE.md`, `experiments/E015_conviction_from_quality/STOP_NOTICE.md`, and `experiments/E016_reentry_flip_on_tighter_stop/STOP_NOTICE.md`.

## 6. Discussion

### 6.1 What the alpha's edge actually looks like

Before this sweep, it was an open question whether `zone_d1_against`'s edge was concentrated in some identifiable subset of trades — small stops, high-quality zones, or some interaction of the two. E011 and E014 together sharpen that picture considerably. The edge is *not* concentrated by stop distance (Section 5.1): a 15-pip-stop trade and an 80-pip-stop trade draw from the same underlying expectancy once sampling noise is accounted for. The edge *is* concentrated by zone quality (Section 5.2), but only detectably so at a threshold strict enough to cut trade frequency to roughly one in eight of the ungated rate. Put plainly: the strategy does not have a "free" subset of better trades hiding in the stop-distance dimension, but it may have one hiding in the quality-score dimension — the problem is that isolating it costs so much trade frequency that a live $1,000 account would see a signal only a handful of times per walk-forward window, which is not a usable trading cadence on its own.

### 6.2 The safety stack and the post-loss guard paradox

E013's headline is reassuring for the live agent's current configuration: turning off all three risk-management layers would cost -0.80 Sharpe, a large and FDR-corrected effect. That is the honest answer to "should we simplify the safety stack because it rarely fires" — no, the layer's job is asymmetric, it is supposed to be quiet in calm weeks and valuable in the tail events that a single week of manual review will never happen to sample (this is precisely the reasoning that motivated running this study in the first place rather than reacting to one week of live data).

But the guard's own attribution is not comfortable, and that discomfort is the point of measuring it properly. A guard that blocks 64% future-winners against 33% future-losers, with the blocked winners averaging more than double the alpha's baseline expectancy, is not obviously well-calibrated *on this cell* — the locked verdict for this pattern is `plg_earns_keep` (Section 5.3's note explains the label). It is tempting to read that finding as "turn the guard off" — that would repeat exactly the error this sweep was designed to prevent (see Section 6.4). The correct reading is narrower: the guard's current cooldown length and consecutive-loss threshold were not tuned against this specific strategy's post-loss return distribution, and a dedicated retuning study (flagged as E017 in Section 7.2) is now well-motivated by a specific, quantified number rather than a vague feeling that "it blocked something last week".

### 6.3 Threats to validity

Four limitations bound how far these results should be trusted, listed honestly rather than buried:

1. **Small window count for the E013 bootstrap.** The paired Sharpe deltas rest on only 7 walk-forward windows. The bootstrap CIs are correspondingly wide (the $\Delta_{\text{be}}$ interval spans from -0.019 to +0.364, a factor-of-nineteen range around its midpoint), and a longer out-of-sample history, or a per-trade rather than per-window delta framing, would sharpen the estimate considerably.
2. **Harness-vs-production fidelity gap for the post-loss guard.** The A/B harness's guard (`BarPlg`) uses a 2-bar cooldown as a bar-driven approximation of the production guard's 60-minute wall-clock cooldown. The direction of the false-negative finding is very unlikely to flip under the exact production cooldown logic, but the *magnitude* (64.2% / 33.3%) should be treated as an estimate, not an exact live figure, until a fidelity-matched re-simulation is run.
3. **Break-even migration is structurally under-tested on H4.** Break-even fires at +1R intrabar; on the four-hour chart with a 1.5R take-profit, most winning trades close within one or two bars of triggering break-even, leaving the mechanism little room to matter. A finer-grained (H1) re-run of E013 would give break-even a fairer test before any conclusion is drawn about whether it is truly Sharpe-neutral in general or merely Sharpe-neutral on this specific timeframe.
4. **E014's threshold-locking procedure is IS-Sharpe-greedy per window.** Locking the highest in-sample Sharpe threshold independently in each of the seven windows (Table 3) is a defensible walk-forward design, but it means the pooled OOS result is not a single fixed-threshold backtest — it is an ensemble of seven independently-chosen thresholds. Window 5's outcome (best IS Sharpe, worst OOS median) is the clearest illustration that this procedure, while methodologically standard, is not immune to the small-sample instability documented throughout Section 5.2.

### 6.4 Why no production trading logic changed

The project's standing rule is that any change to entry, exit, sizing, or quality-gating logic requires a pre-registered study with an `alive_*` verdict before it reaches the live account (`docs/00-journey.md`; `PROTOCOL_DISCIPLINE.md`). None of the three executed studies produced a verdict that clears that bar for a *new* piece of strategy logic: E011 found no small-stop edge to exploit; E014 found a real but production-unusable effect; and E013's `combined_alive` verdict validates the alpha's *existing* deployed configuration rather than proposing a change to it. Applying the rule mechanically and honestly here means the correct action, in a session where the research came back mostly negative or inconclusive, is to change nothing rather than to salvage something — E014's result in particular would have been an easy candidate to over-interpret ("+26 pips is real, ship it") had the pre-declared 25% trade-count floor not been fixed in the protocol before the pooled result was computed.

Two features did ship this session, and it is worth being precise about why they were exempt from the pre-registration requirement rather than treating that as an inconsistency: a weekly rejection-review report (a pure observability addition that resolves already-rejected signals to their counterfactual outcome for human review, changing no live decision) and a portfolio-wide 5% total-open-risk ceiling (a pure ceiling that can only ever block a trade that would otherwise have been taken, never approve one that would not have been). Both changes are monotonically risk-reducing or purely observational; neither can introduce a new false-positive trading decision, which is the property that the pre-registration requirement exists to guard against.

## 7. Conclusion and Future Work

### 7.1 Summary

Six pre-registered questions were asked about a live, deployed forex strategy. Three were answered directly: the alpha's edge does not concentrate by stop distance (E011, `stopped_at_stage_1`); the deployed safety-layer stack is validated as a whole and wick-proof stops specifically earn their keep, but the post-loss guard has a documented, non-trivial false-negative cost (E013, `combined_alive` with a `plg_earns_keep` sub-finding — the protocol's own label for "PLG is expensive"); and zone-quality gating finds a real effect that is currently too data-hungry to deploy (E014, `parked_low_yield`). Three were formally cancelled by pre-declared dependency gates rather than left open indefinitely (E012, E015, E016). No production trading logic changed as a result; two independent, risk-reducing-only observability and safety features shipped alongside the research.

### 7.2 Future work

Two concrete follow-on studies are now well-motivated by this sweep's specific numbers rather than by general intuition, and both are recorded in the lab's backlog (`ai_context.md` Section 3) pending a future session:

1. **E017, post-loss guard cooldown and consecutive-loss threshold tuning.** Directly motivated by Section 5.3's Table 8: retune the guard's cooldown length and streak threshold against this strategy's specific post-loss return distribution, using the same A/B harness with a `plg_config` sweep in place of the current boolean toggle, before any change to the deployed guard parameters is considered.
2. **E014 wider-threshold-grid amendment.** Directly motivated by Section 5.2: repeat the study with $\theta \in \{20, 30, 40, 50\}$ to search for a threshold that preserves more of the +26 pip effect while clearing the 25% trade-count floor. A positive result here would re-open the currently-cancelled E015 (conviction-from-quality sizing) as a direct consequence.

Both items require a fresh or amended pre-registered protocol before touching any production parameter, per the discipline this report has tried to model throughout.

## References

Full BibTeX entries are maintained at `reviews/refs.bib` for LaTeX/pandoc conversion. Harvard-style list below.

1. Bailey, D.H. and López de Prado, M., 2014. The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality. *Journal of Portfolio Management*, 40(5), pp.94-107.
2. Bailey, D.H., Borwein, J.M., López de Prado, M. and Zhu, Q.J., 2014. Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance. *Notices of the American Mathematical Society*, 61(5), pp.458-471.
3. Benjamini, Y. and Hochberg, Y., 1995. Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing. *Journal of the Royal Statistical Society, Series B*, 57(1), pp.289-300.
4. Chan, E.P., 2009. *Quantitative Trading: How to Build Your Own Algorithmic Trading Business*. Hoboken, NJ: Wiley.
5. Efron, B. and Tibshirani, R.J., 1993. *An Introduction to the Bootstrap*. New York: Chapman & Hall/CRC.
6. Harvey, C.R., Liu, Y. and Zhu, H., 2016. ...and the Cross-Section of Expected Returns. *Review of Financial Studies*, 29(1), pp.5-68.
7. Kelly, J.L., 1956. A New Interpretation of Information Rate. *Bell System Technical Journal*, 35(4), pp.917-926.
8. Lo, A.W., 2004. The Adaptive Markets Hypothesis: Market Efficiency from an Evolutionary Perspective. *Journal of Portfolio Management*, 30(5), pp.15-29.
9. López de Prado, M., 2018a. *Advances in Financial Machine Learning*. Hoboken, NJ: Wiley.
10. López de Prado, M., 2018b. The 10 Reasons Most Machine Learning Funds Fail. *Journal of Portfolio Management*, 44(6), pp.120-133.
11. Menkhoff, L. and Taylor, M.P., 2007. The Obstinate Passion of Foreign Exchange Professionals: Technical Analysis. *Journal of Economic Literature*, 45(4), pp.936-972.
12. Neely, C.J., Weller, P.A. and Dittmar, R., 1997. Is Technical Analysis in the Foreign Exchange Market Profitable? A Genetic Programming Approach. *Journal of Financial and Quantitative Analysis*, 32(4), pp.405-426.
13. Nosek, B.A., Ebersole, C.R., DeHaven, A.C. and Mellor, D.T., 2018. The Preregistration Revolution. *Proceedings of the National Academy of Sciences*, 115(11), pp.2600-2606.
14. Sullivan, R., Timmermann, A. and White, H., 1999. Data-Snooping, Technical Trading Rule Performance, and the Bootstrap. *Journal of Finance*, 54(5), pp.1647-1691.
15. White, H., 2000. A Reality Check for Data Snooping. *Econometrica*, 68(5), pp.1097-1126.

## Appendix A — Study registry cross-reference

| ID | Protocol | Report / Notice | Raw data |
|---|---|---|---|
| E011 | `experiments/E011_small_stop_subset_expectancy/PROTOCOL.md` | `experiments/E011_small_stop_subset_expectancy/REPORT.md` | `experiments/E011_small_stop_subset_expectancy/MANIFEST.md` |
| E012 | `experiments/E012_pending_limit_inside_zone/PROTOCOL.md` | `experiments/E012_pending_limit_inside_zone/STOP_NOTICE.md` | not executed |
| E013 | `experiments/E013_safety_layer_contribution/PROTOCOL.md` | `experiments/E013_safety_layer_contribution/REPORT.md` | `output/E013_safety_layer_contribution/results.json` |
| E014 | `experiments/E014_quality_score_entry_gate/PROTOCOL.md` | `experiments/E014_quality_score_entry_gate/REPORT.md` | inline in `REPORT.md` |
| E015 | `experiments/E015_conviction_from_quality/PROTOCOL.md` | `experiments/E015_conviction_from_quality/STOP_NOTICE.md` | not executed |
| E016 | `experiments/E016_reentry_flip_on_tighter_stop/PROTOCOL.md` | `experiments/E016_reentry_flip_on_tighter_stop/STOP_NOTICE.md` | not executed |

## Appendix B — Statistical honesty self-check

Per the lab's `PROTOCOL_DISCIPLINE.md` and `07-research-standards.md` Section 11:

- [x] All six protocols pre-registered and committed before their data was touched.
- [x] Locked decision statistic named per study before execution (median pips, Sharpe delta, trade-count ratio).
- [x] BH-FDR $\alpha = 0.05$ applied within each study's hypothesis family.
- [x] Bootstrap CIs (not normal-theory approximations) used at every small-sample decision point.
- [x] Pre-declared stop rules honoured mechanically (E011 and E014 stop rules cancelled E012/E015/E016 without a discretionary decision).
- [x] Negative and inconclusive results reported in `EXPERIMENTS.md` alongside positive ones, append-only.
- [x] No post-freeze retuning of any threshold, window, or comparator after seeing results.
- [x] No production trading-logic parameter changed without a passing verdict.
