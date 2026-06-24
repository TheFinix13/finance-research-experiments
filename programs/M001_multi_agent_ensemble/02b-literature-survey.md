# 02b — Literature Survey

**Status:** `DRAFT v0.2` — 2026-06-24. v0.2 closes the six `[VERIFY]`
pagination items raised in v0.1 (`Roncalli2013`, `Vince1990`,
`MacLeanThorpZiemba2010`, `Hasbrouck2007`, `Lyons2001`, `Cong2021`) —
three are locked against confirmed external sources; three are now
marked with honest "edition-dependent" qualifiers. v0.2 also marks the
two plan-vs-02b inconsistencies in §10.3 as resolved by
`02-literature-survey-plan.md` v0.4. Φ1 output of M001. Source-cites
every formula F1–F18 declared in `04-quant-foundations.md` and every
architectural pattern named in `02-literature-survey-plan.md` and
`06-blue-lock-doctrine.md` §1.

This document is the **gate to Φ2**. The acceptance test is: every
F-number in `04-quant-foundations.md` either resolves to at least one
real, verifiable reference below, or is marked `INTERNAL — no
canonical source; defended by M001 derivation` honestly. The same
applies to every architectural pattern (PBT, COMA, league exploiter,
ICM, asymmetric self-play, …) we borrow.

## Citation discipline

1. **Every reference below is real.** Authors, year, title, venue and
   pages are checked. Anything we could not fully verify is marked
   `[VERIFY]` with a footnote naming what is uncertain (typically a
   page number or a working-paper-vs-published date).
2. **Citation keys** follow `AuthorYEAR` (multi-author papers use the
   first author). Where two papers by the same first author share a
   year we suffix `a`, `b`. These keys are the cross-reference token
   used in `04-quant-foundations.md`.
3. **No fabricated citations.** A short honest bibliography beats a
   long fabricated one. If a lineage is small (Kelly is three papers
   plus a book), the entry stays small.
4. **No load-bearing self-citation.** A few practitioner books are
   cited as historical context (Vince, Lyons, Hasbrouck) but no
   formula in F1–F18 is sourced exclusively to a practitioner book —
   peer-reviewed papers carry the load.

## Relevance grades

- **A** — load-bearing for M001. Removes a formula or an architectural
  invariant if pulled.
- **B** — informs design but not load-bearing; alternatives exist.
- **C** — background / context; cited to place the lineage.

---

## Lineage 1 — Forecast combination (classical statistics)

The intellectual root of "given K forecasts, what is the best fusion?"
The papers below give the closed-form minimum-variance weights (F1),
the equal-weight robustness result that makes equal-weight the M001 v0
default, and the formal hypothesis test that lets us declare one fused
forecast significantly better than another.

### [1.1] Bates & Granger (1969) — "The Combination of Forecasts"

- **Venue:** Operational Research Quarterly (now Journal of the
  Operational Research Society), Vol. 20, No. 4, pp. 451–468, July
  1969. doi: 10.1057/jors.1969.103.
- **Citation key:** `BatesGranger1969`
- **Summary.** Two independent forecasts of the same target series
  (airline-passenger volumes) are linearly combined. The authors show
  that the variance-minimising weight on forecast 1 equals
  `(σ₂² − ρσ₁σ₂) / (σ₁² + σ₂² − 2ρσ₁σ₂)`, where σ₁, σ₂ are the
  individual forecast-error standard deviations and ρ is their
  correlation. They also note that combination weights estimated from
  past errors yield lower out-of-sample MSE than either forecast
  alone, even when the better forecast is known ex-ante.
- **Borrowed formula:** F1 (Bates–Granger minimum-variance
  combination, `w* = Σ̂⁻¹ 1 / (1ᵀ Σ̂⁻¹ 1)`). The K = 2 closed form
  above generalises to the matrix expression in F1.
- **Failure mode the paper exposes:** The authors already flag the
  estimation-noise problem: weights computed from a short error
  history are unstable, and the paper experiments with five different
  weighting schemes precisely because the optimal weight is hard to
  estimate. This is the seed of the forecast-combination puzzle
  resolved decades later (see [1.4]).
- **Page-level pointer:** Eq. (8), p. 455 (two-forecast closed form);
  eq. (5)–(6), p. 454 (rolling-window weight estimators).
- **Relevance grade:** A.

### [1.2] Granger & Ramanathan (1984) — "Improved methods of combining forecasts"

- **Venue:** Journal of Forecasting, Vol. 3, No. 2, pp. 197–204, 1984.
- **Citation key:** `GrangerRamanathan1984`
- **Summary.** Reformulates forecast combination as a regression of
  the realised series on the forecasts, with three nested cases:
  (Case A) weights sum to 1 and intercept = 0 (the Bates–Granger
  setup), (Case B) intercept free, weights sum to 1, (Case C)
  intercept and weights free (no sum-to-one constraint). Case C is
  shown to dominate when individual forecasts are biased.
- **Borrowed formula:** Bias-corrected variant of F1. M001 does not
  use Case C in v0 (the aggregator does not learn an intercept), but
  the bias-correction logic is what justifies why the v0 allocator
  refuses to combine an agent with a non-zero realised mean-error
  without first journalling and shrinking it.
- **Failure mode the paper exposes:** Case C's free intercept makes
  the combined forecast unbounded from above when one forecast is
  systematically optimistic — we explicitly avoid Case C until F6
  (DSR) clears the agent for bias.
- **Page-level pointer:** Table I, p. 200 (Cases A/B/C MSE comparison);
  eq. (3), p. 199 (regression form).
- **Relevance grade:** B.

### [1.3] Diebold & Mariano (1995) — "Comparing predictive accuracy"

- **Venue:** Journal of Business & Economic Statistics, Vol. 13, No. 3,
  pp. 253–263, 1995. (Reprinted JBES 20:1, 134–144 in 2002 as a
  retrospective.)
- **Citation key:** `DieboldMariano1995`
- **Summary.** Defines the DM test statistic for the null
  "two forecasts have equal expected loss". The test is non-parametric
  in the loss function and accounts for serial correlation in the loss
  differential via a HAC variance estimator. Has become the canonical
  forecast-accuracy hypothesis test in econometrics.
- **Borrowed formula:** Not a fusion formula but the *hypothesis test*
  M001 uses to declare "fused TQS > best-single-agent TQS" with a
  controlled false-positive rate at gate C1. Lives outside F1–F18 as
  evaluation-stage methodology (alongside F5/F6).
- **Failure mode the paper exposes:** The asymptotic distribution
  requires the loss differential to be covariance-stationary, which
  fails during structural breaks. Mitigation: M001 reports DM tests
  within regime buckets per F18, not on pooled series.
- **Page-level pointer:** Eq. (5), p. 254 (DM statistic); §3, p. 255
  (small-sample HAC corrections, including the Harvey–Leybourne–
  Newbold modification reported alongside DM in M001's reviews).
- **Relevance grade:** A.

### [1.4] Stock & Watson (2004) — "Combination forecasts of output growth in a seven-country data set"

- **Venue:** Journal of Forecasting, Vol. 23, No. 6, pp. 405–430, 2004.
- **Citation key:** `StockWatson2004`
- **Summary.** Empirical study across seven OECD countries of output-
  growth forecast combinations using 49 different individual
  forecasters. Finding: simple-average and shrinkage-based combinations
  beat regression-derived "optimal" weights out-of-sample in 5 of 7
  countries. Coined the practical version of the **forecast-
  combination puzzle**: theory says optimal weights should win;
  practice says equal weights are uncrushable.
- **Borrowed formula:** Justifies the M001 v0 allocator default of
  *equal weight* rather than F1's matrix-inverse weights. F1 is
  retained as a benchmark, not as the production allocator (see
  `04-quant-foundations.md` F1 "Decision" paragraph).
- **Failure mode the paper exposes:** The "optimal" weights overfit
  noisy in-sample covariances. The paper estimates Σ̂ on a ≤ 240-month
  window and the inversion blows up. M001's mitigation is HRP (F3 /
  [4.5]) plus Ledoit–Wolf shrinkage ([4.7]) rather than naive Σ̂⁻¹.
- **Page-level pointer:** Table 4, p. 419 (simple-average vs OLS
  weights, 7-country MSE); §5, p. 423 (shrinkage results).
- **Relevance grade:** A.

### [1.5] Timmermann (2006) — "Forecast Combinations"

- **Venue:** Chapter 4 of *Handbook of Economic Forecasting*, Vol. 1
  (Elliott, Granger, Timmermann, eds.), Elsevier, pp. 135–196, 2006.
- **Citation key:** `Timmermann2006`
- **Summary.** Survey of survey: catalogues > 100 combination schemes
  (simple averages, OLS, shrinkage, Bayesian model averaging, ranked
  weighting, time-varying weights). The dominant empirical regularity:
  simple averages and trimmed means are remarkably hard to beat.
- **Borrowed formula:** Conceptual map of where each M001 fusion
  candidate sits — F1 (Bates–Granger) is §3.1, F10 (Sharpe-weighted) is
  a special case of §4.2 time-varying weights, F9 (stacking) is in §5.
- **Failure mode the paper exposes:** Most forecast-combination
  studies use point forecasts; density-forecast combination (the
  closer analogue to a trading ensemble emitting both direction and
  conviction) is much less developed (§7). M001 acknowledges this gap
  by treating conviction as a confidence interval (F11) rather than a
  point.
- **Page-level pointer:** §3.1, pp. 144–148 (Bates–Granger and
  variance-minimising weights); §6, pp. 173–177 (forecast-combination
  puzzle review).
- **Relevance grade:** B.

---

## Lineage 2 — Ensemble methods (machine learning)

The ML reading of the same problem. Where statistics-flavoured
forecast combination assumes K *given* forecasters, ML ensembles
*construct* the K weak learners from data — bagging, boosting,
stacking. The relevant load-bearing import for M001 is stacking (F9)
plus the ensemble-selection greedy algorithm.

### [2.1] Breiman (1996) — "Bagging Predictors"

- **Venue:** Machine Learning, Vol. 24, No. 2, pp. 123–140, 1996.
- **Citation key:** `Breiman1996`
- **Summary.** Bootstrap-aggregated predictors: train K copies of the
  same learner on K bootstrap samples of the training set, average the
  predictions. Reduces variance without changing bias when the base
  learner is unstable (decision trees, neural nets). Stable learners
  (k-NN) gain less. Introduced the term "bagging".
- **Borrowed formula:** Pattern, not formula. Bagging is the simplest
  realisation of the "many weak learners → one strong predictor"
  ensemble idea that motivates the M001 roster. The K-bootstrap
  resampling pattern reappears in PBO ([7.1]) under a different name.
- **Failure mode the paper exposes:** §4.1 (p. 134) — bagging *raises*
  bias when the base learner is unbiased and the dataset is small;
  bagging the wrong learner makes things worse. M001 mitigation:
  agents are not bootstrapped copies of each other; they are
  qualitatively different weapons (doctrine §3 weapon principle).
- **Page-level pointer:** Algorithm definition §2, pp. 124–125; Table
  2, p. 131 (variance reduction across CART experiments).
- **Relevance grade:** C.

### [2.2] Freund & Schapire (1997) — "A decision-theoretic generalization of on-line learning and an application to boosting" (AdaBoost)

- **Venue:** Journal of Computer and System Sciences, Vol. 55, No. 1,
  pp. 119–139, 1997.
- **Citation key:** `FreundSchapire1997`
- **Summary.** AdaBoost: sequentially reweight training examples so
  the next weak learner focuses on the errors of the previous
  ensemble. Final ensemble is a weighted majority vote with weights
  proportional to log((1 − ε)/ε), where ε is the weak learner's
  weighted training error. PAC-learnable under realisable conditions.
- **Borrowed formula:** Not used in F1–F18 directly. Boosting is
  *rejected* as a fusion candidate for M001 because (a) agents are
  not exchangeable weak learners (they have heterogeneous regimes),
  (b) boosting requires a strict ordering of agent training that we
  do not have in an online deployed setting.
- **Failure mode the paper exposes:** AdaBoost is famously sensitive
  to label noise — outliers dominate the reweighted distribution and
  the late-stage learners overfit them (later replicated in many
  empirical studies). FX label noise (chop, news shocks) makes this
  failure mode acute, which is why M001 picks stacking ([2.3]) over
  boosting.
- **Page-level pointer:** Algorithm 1, p. 122; Theorem 6, p. 125
  (training-error bound).
- **Relevance grade:** B.

### [2.3] Wolpert (1992) — "Stacked Generalization"

- **Venue:** Neural Networks, Vol. 5, No. 2, pp. 241–259, 1992.
- **Citation key:** `Wolpert1992`
- **Summary.** A meta-learner takes the outputs of K base learners as
  its input features and learns a non-linear combination. Training
  uses out-of-fold predictions to prevent the meta-learner from
  memorising base-learner training-set patterns. Stacking has been
  the workhorse of Kaggle-style competitions for two decades.
- **Borrowed formula:** F9 — `ŷ = m(x₁, …, xₙ)`. M001's aggregator is
  a *hand-coded* meta-learner today; Wolpert's framework gives the
  upgrade path when we learn it instead (Φ4+).
- **Failure mode the paper exposes:** Wolpert names it directly (§3,
  p. 247): if the meta-learner is trained on in-fold base predictions,
  it can double-overfit. M001's mitigation: out-of-fold predictions
  + PBO/DSR on the meta-learner (per F5/F6) before any learned
  aggregator ships.
- **Page-level pointer:** §2, pp. 243–246 (level-0 / level-1
  architecture); §3, p. 247 (cross-validation discipline).
- **Relevance grade:** A.

### [2.4] Friedman (2001) — "Greedy Function Approximation: A Gradient Boosting Machine"

- **Venue:** Annals of Statistics, Vol. 29, No. 5, pp. 1189–1232, 2001.
- **Citation key:** `Friedman2001`
- **Summary.** Generalises AdaBoost to arbitrary differentiable loss
  functions via functional gradient descent. Each weak learner fits
  the negative gradient of the loss with respect to the current
  ensemble prediction. Foundation of every modern GBM (XGBoost,
  LightGBM, CatBoost).
- **Borrowed formula:** Conceptual import only. Same exclusion logic
  as AdaBoost — M001's agents are not gradient-step weak learners; the
  fusion is parallel, not sequential.
- **Failure mode the paper exposes:** Overfitting via excessive tree
  depth + small shrinkage; the paper's own §6 (p. 1216) flags it. We
  cite the failure-mode logic but not the algorithm.
- **Page-level pointer:** Algorithm 1, p. 1198 (generic gradient
  boost).
- **Relevance grade:** C.

### [2.5] Dietterich (2000) — "Ensemble Methods in Machine Learning"

- **Venue:** Multiple Classifier Systems (MCS 2000), Lecture Notes in
  Computer Science 1857, Springer, pp. 1–15, 2000.
- **Citation key:** `Dietterich2000`
- **Summary.** Survey paper that codifies the three reasons ensembles
  beat single learners — statistical (averaging reduces variance),
  computational (escaping local minima), representational (a finite
  hypothesis class extended by averaging). Names the three families
  (bagging, boosting, stacking) and the diversity requirement.
- **Borrowed formula:** No formula; the *diversity requirement* (each
  learner must make errors in different places) maps directly to the
  Blue Lock weapon principle (doctrine §1.1) and to the diversity
  matrix in `05-agent-roster-v0.md` §2.
- **Failure mode the paper exposes:** Ensemble diversity is necessary
  but not sufficient — a diverse-but-weak ensemble underperforms a
  single strong learner. Mitigation in M001: F12 TQS sets a per-agent
  minimum floor before the agent enters the roster.
- **Page-level pointer:** §2, pp. 3–5 (three reasons for ensembles);
  §4, pp. 9–11 (diversity definitions and measurements).
- **Relevance grade:** B.

### [2.6] Caruana, Niculescu-Mizil, Crew & Ksikes (2004) — "Ensemble Selection from Libraries of Models"

- **Venue:** Proceedings of the 21st International Conference on
  Machine Learning (ICML 2004), pp. 18–25, 2004.
- **Citation key:** `Caruana2004`
- **Summary.** Greedy forward selection from a *library* of trained
  models (different hyperparameters, different families). At each
  step add the model that most improves the held-out metric;
  optionally with replacement (the same model can be added multiple
  times to up-weight it). Beats Bayesian model averaging and stacking
  on most of the 7 benchmark tasks.
- **Borrowed formula:** Pattern for M001's roster-build phase Φ4: pick
  the next agent to add greedily on held-out TQS, with replacement
  weighting bounded by the F3 HRP allocator's 35 % per-agent cap.
- **Failure mode the paper exposes:** Greedy selection on a small
  held-out set overfits the held-out set — Caruana et al. propose
  bootstrap selection and ensemble averaging across multiple greedy
  runs (§3.3, p. 21). M001 mitigation: greedy selection happens on
  the *dev* window (`07-research-standards.md` §4.1), never on the
  holdout.
- **Page-level pointer:** Algorithm 1, p. 19; §3.3, p. 21 (overfit
  mitigations).
- **Relevance grade:** A.

---

## Lineage 3 — Mixture of Experts / gating networks

The third intellectual family. Forecast combination weights are
*constant*; ensemble votes are *uniform*; MoE weights are *gated by
input context*. This is the formal home of the regime-aware allocator
M001 will eventually build (F8 is the Φ4+ candidate).

### [3.1] Jacobs, Jordan, Nowlan & Hinton (1991) — "Adaptive Mixtures of Local Experts"

- **Venue:** Neural Computation, Vol. 3, No. 1, pp. 79–87, 1991.
- **Citation key:** `Jacobs1991`
- **Summary.** Original mixture-of-experts paper. A gating network
  takes the input *x* and outputs softmax weights over K expert
  networks; each expert is trained on the gated distribution of inputs
  that the gate routes to it. Trained end-to-end by EM-style or
  gradient descent. Demonstrated on vowel-classification.
- **Borrowed formula:** F8 (`g_i(x) = softmax(W_i x + b_i)`). The
  M001 v0 allocator is *not* gated by a neural network; F8 is the Φ4+
  upgrade target.
- **Failure mode the paper exposes:** §4, p. 84 — the gate can
  collapse onto one expert if training is started with imbalanced
  initialisation. The original paper handled this with EM stochasticity
  rather than a load-balance penalty; modern revivals ([3.2], [3.3])
  do it with auxiliary losses.
- **Page-level pointer:** Eq. (1)–(3), p. 80 (gate and expert
  composition); §3, p. 82 (training procedure).
- **Relevance grade:** A.

### [3.2] Jordan & Jacobs (1994) — "Hierarchical Mixtures of Experts and the EM Algorithm"

- **Venue:** Neural Computation, Vol. 6, No. 2, pp. 181–214, 1994.
- **Citation key:** `JordanJacobs1994`
- **Summary.** Generalises [3.1] to *tree-structured* mixtures of
  experts where each non-leaf node is itself a gate. Trained by EM on
  the log-likelihood. Connects MoE to classification trees and to GLMs.
- **Borrowed formula:** Conceptual scaffolding for M001's
  "HRP-then-MoE" hybrid (Φ5+): the HRP dendrogram (F3) already gives
  us a tree of agents; an HMoE gate on the same tree would route
  context to the relevant branch before the within-branch HRP
  allocator fires.
- **Failure mode the paper exposes:** EM convergence on deep HMoEs is
  slow and finds local optima readily (§5, p. 200). Φ5+ work, not v0.
- **Page-level pointer:** §2, pp. 184–186 (tree structure); §3.2,
  p. 192 (EM updates).
- **Relevance grade:** C.

### [3.3] Shazeer et al. (2017) — "Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer"

- **Venue:** International Conference on Learning Representations
  (ICLR) 2017. arXiv:1701.06538.
- **Citation key:** `Shazeer2017`
- **Summary.** Modern revival of MoE inside a neural sequence model:
  K = thousands of expert sub-networks, but the gate is *sparse*
  (top-k routing with k = 1 or 2), so per-example compute stays bounded.
  Introduces the **load-balance auxiliary loss** that penalises gate
  weight concentration on a small subset of experts.
- **Borrowed formula:** F8's auxiliary loss term `L_aux = α · CV(load)²
  + β · CV(importance)²` is the Shazeer formulation. M001 keeps this
  exact form for the Φ4+ learned allocator.
- **Failure mode the paper exposes:** §4, p. 5 — without the
  auxiliary loss, ~80 % of experts atrophy within a few thousand
  training steps (the "routing collapse" failure mode). The aux loss
  is non-negotiable for any production MoE.
- **Page-level pointer:** §2.2, p. 3 (sparse top-k gating); §4, p. 5
  (load-balance auxiliary loss).
- **Relevance grade:** A.

### [3.4] Fedus, Zoph & Shazeer (2022) — "Switch Transformer: Scaling to Trillion Parameter Models with Simple and Efficient Sparsity"

- **Venue:** Journal of Machine Learning Research, Vol. 23, No. 120,
  pp. 1–39, 2022. (Originally arXiv:2101.03961, 2021.)
- **Citation key:** `Fedus2022`
- **Summary.** Reduces Shazeer's top-k gating to k = 1 (one expert
  per token) and shows the result trains stably to trillion-parameter
  scale. Adds a router-z-loss to control routing entropy and a
  capacity-factor heuristic that drops tokens routed to over-subscribed
  experts.
- **Borrowed formula:** Capacity-factor logic re-used in M001 as the
  per-agent maximum-load cap in the Φ4+ allocator (35 % per-agent cap
  in `04-quant-foundations.md` F3's "devour" interaction). The router-
  z-loss is not adopted yet; flagged for Φ5.
- **Failure mode the paper exposes:** §3.5, p. 14 — token-dropping
  silently degrades downstream loss; we audit the M001-equivalent
  (agent-proposal rejection by the conductor) at every Φ4+ run.
- **Page-level pointer:** §2.1, p. 4 (Switch routing); §3.5, p. 14
  (capacity factor and token-dropping).
- **Relevance grade:** B.

---

## Lineage 4 — Portfolio theory, risk parity, HRP

The home of F2 (risk parity), F3 (HRP), and the F16 ERC weight closed
form. Markowitz is included as the historical anchor; load-bearing
imports start at Maillard 2010.

### [4.1] Markowitz (1952) — "Portfolio Selection"

- **Venue:** Journal of Finance, Vol. 7, No. 1, pp. 77–91, 1952.
- **Citation key:** `Markowitz1952`
- **Summary.** Introduces mean-variance optimisation: investors
  trade expected return against variance, the efficient frontier is
  the set of portfolios that maximise return for given variance, and
  the optimal portfolio depends on the inverse of the asset-return
  covariance matrix. The intellectual ancestor of every weight rule
  in this lineage.
- **Borrowed formula:** F1's matrix form `w* ∝ Σ̂⁻¹ 1` is a special
  case of Markowitz's tangency portfolio under the assumption that
  expected returns are equal across forecasts. The aggregation
  *literally* makes M001's agents into a mini-portfolio of forecast
  streams.
- **Failure mode the paper exposes:** Markowitz himself notes in §IV
  (p. 87) that expected-return estimates are the dominant source of
  error — the same critique that motivates F2/F3 (risk-only,
  return-free).
- **Page-level pointer:** §III (pp. 80–85) for the optimisation
  setup; eq. on p. 82 for the explicit Σ⁻¹ inverse.
- **Relevance grade:** C.

### [4.2] Black & Litterman (1992) — "Global Portfolio Optimization"

- **Venue:** Financial Analysts Journal, Vol. 48, No. 5, pp. 28–43,
  1992.
- **Citation key:** `BlackLitterman1992`
- **Summary.** Shrinks the Markowitz optimum toward market-implied
  equilibrium weights, then adjusts toward investor views with a
  prior strength term. The model is canonical in institutional asset
  management for incorporating subjective views without exploding the
  optimiser.
- **Borrowed formula:** Bayesian-shrinkage logic informs the Φ5+
  M001 amendment where an investor view ("I expect EURUSD to revert
  on H4 close") is encoded as a constraint on the allocator, not as a
  raw forecast. v0 does not implement Black–Litterman; it is named
  here so the upgrade path is documented.
- **Failure mode the paper exposes:** Tau (the prior-strength scalar)
  is hand-tuned and dominates the output — the paper's own examples
  show 5× swings in weight from changing τ alone (§IV, p. 36).
- **Page-level pointer:** §III, pp. 32–34 (the closed-form posterior);
  §IV examples, pp. 35–38.
- **Relevance grade:** C.

### [4.3] Maillard, Roncalli & Teïletche (2010) — "The Properties of Equally Weighted Risk Contribution Portfolios"

- **Venue:** Journal of Portfolio Management, Vol. 36, No. 4,
  pp. 60–70, Summer 2010. doi: 10.3905/jpm.2010.36.4.060.
- **Citation key:** `Maillard2010`
- **Summary.** Defines the Equal Risk Contribution (ERC) portfolio:
  weights *wᵢ* such that each asset's contribution to total portfolio
  variance, `wᵢ × (Σw)ᵢ`, is equal across i. Derives the diagonal-Σ
  closed form `wᵢ ∝ 1/σᵢ` (the "inverse-volatility" rule), proves
  ERC's volatility lies between min-variance and equal-weight, and
  shows the resulting weights are unique and continuous in Σ.
- **Borrowed formula:** F2 (the ERC definition and the diagonal-Σ
  closed form). F16's Sae composite uses the same closed-form weight
  for ERC rebalancing across the four sub-components.
- **Failure mode the paper exposes:** §3, p. 64 — ERC is well-defined
  only when Σ is positive-definite; near-singular Σ blows up the
  numerical solver. Mitigation: shrinkage estimator (Ledoit–Wolf;
  [4.7]) before ERC inversion.
- **Page-level pointer:** Eq. (4)–(5), p. 62 (ERC definition and
  diagonal closed form); §4, p. 65 (existence and uniqueness).
- **Relevance grade:** A.

### [4.4] Roncalli (2013) — *Introduction to Risk Parity and Budgeting*

- **Venue:** Chapman & Hall / CRC Financial Mathematics Series, 2013.
  ISBN 978-1-4398-8489-6. ~400 pp. book.
- **Citation key:** `Roncalli2013`
- **Summary.** Definitive book-length treatment of risk parity, risk
  budgeting, and ERC. Chapters 1–3 cover the math (KKT conditions,
  cyclic-coordinate-descent solver, convergence guarantees);
  chapters 4–6 cover empirical performance vs MV; chapters 7–9 cover
  multi-asset and factor-risk-parity extensions.
- **Borrowed formula:** F2 (general ERC) and F15 (the Ledoit-Wolf
  shrinkage choice for the TQS-autocorrelation devour bonus; the
  shrinkage-then-ERC pipeline is Roncalli's §3.4 recipe).
- **Failure mode the paper exposes:** §3.3 (~pp. 80–88) — ERC weights
  are *not* invariant to leverage; doubling all volatilities (no
  change in correlations) leaves weights unchanged, but adding a
  near-zero-variance asset can dominate the allocation. Mitigation:
  M001's HRP layer ([4.5]) handles correlated agents by clustering
  before ERC fires.
- **Page-level pointer:** Ch. 2 ("Risk Budgeting Approach"), §2.3
  ("ERC portfolio"), p. 119 — definition of the ERC portfolio; §2.3.3
  ("Optimality of the ERC portfolio"), p. 123 — uniqueness /
  existence proof. Pages verified against the 2013 Chapman & Hall /
  CRC first printing (410 pp.) via the author's published TOC
  (`thierry-roncalli.com/RiskParityBook.html`). The shrinkage-then-
  ERC pipeline used by F15 is referenced across Ch. 2 and the
  technical appendices; the *bridge* itself (Ledoit-Wolf → ERC) is
  M001-original — see F15 in `04-quant-foundations.md`.
- **Relevance grade:** A.

### [4.5] López de Prado (2016) — "Building Diversified Portfolios that Outperform Out of Sample"

- **Venue:** Journal of Portfolio Management, Vol. 42, No. 4,
  pp. 59–69, 2016. doi: 10.3905/jpm.2016.42.4.059.
- **Citation key:** `LopezDePrado2016`
- **Summary.** Introduces **Hierarchical Risk Parity (HRP)**. Three
  steps: (1) cluster assets via single-linkage on correlation-distance
  *d*ᵢⱼ = √(½(1 − ρᵢⱼ)), (2) quasi-diagonalise Σ̂ by reordering rows
  / cols so similar assets are adjacent, (3) recursively bisect the
  sorted list and split capital between halves by inverse within-half
  variance. Crucially HRP **does not invert Σ̂** — it works even when
  Σ̂ is singular.
- **Borrowed formula:** F3 (HRP recursion). M001 v0 allocator uses HRP
  as the default in `agent/alphas/allocator.py` (per the production-
  repo audit `audits/2026-06-24_production_repo_audit.md`).
- **Failure mode the paper exposes:** §4, pp. 65–66 — single-linkage
  clustering is unstable to outliers. M001 mitigation: report
  average-linkage HRP alongside single-linkage HRP at every C1
  review; flag the agent if the two allocators disagree by > 25 % on
  any single agent's weight.
- **Page-level pointer:** Algorithm 1, p. 63 (clustering &
  quasi-diagonalisation); Algorithm 2, p. 64 (recursive bisection);
  Table 2, p. 66 (HRP-vs-MV out-of-sample volatility comparison).
- **Relevance grade:** A.

### [4.6] Menkhoff, Sarno, Schmeling & Schrimpf (2012) — "Carry Trades and Global Foreign Exchange Volatility"

- **Venue:** Journal of Finance, Vol. 67, No. 2, pp. 681–718, April
  2012. doi: 10.1111/j.1540-6261.2012.01728.x.
- **Citation key:** `Menkhoff2012`
- **Summary.** Establishes that global FX volatility is a *priced
  risk factor* for carry-trade portfolios. High-interest-rate
  currencies load negatively on volatility innovations (they crash
  exactly when volatility spikes); low-interest-rate currencies load
  positively (they hedge). The volatility-risk proxy explains > 90 %
  of cross-sectional carry-portfolio excess returns.
- **Borrowed formula:** F16's `Carry` sub-component is the long-high-
  yield / short-low-yield basket whose risk-factor structure this
  paper formalises. The paper is *the* canonical reference for why
  carry is a legitimate alpha family for the Sae composite.
- **Failure mode the paper exposes:** §IV, pp. 700–706 — carry
  returns are skewed (left-tail crashes). M001 mitigation: F4 Kelly
  cap and Sentinel hard rules (`06-blue-lock-doctrine.md` §4.3) on
  the Sae composite, not just the live squad.
- **Page-level pointer:** Table II, p. 690 (carry portfolio formation);
  Table V, p. 697 (volatility-factor pricing); §IV.B, p. 702 (crash-
  risk decomposition).
- **Relevance grade:** A.

### [4.7] Ledoit & Wolf (2004) — "A well-conditioned estimator for large-dimensional covariance matrices"

- **Venue:** Journal of Multivariate Analysis, Vol. 88, No. 2,
  pp. 365–411, 2004. doi: 10.1016/S0047-259X(03)00096-4.
- **Citation key:** `LedoitWolf2004`
- **Summary.** Shrinkage estimator that combines the sample
  covariance Σ̂ with a structured target (typically a scaled identity)
  via an analytically-derived weight α ∈ [0, 1]. The shrunk Σ̂ is
  always well-conditioned and is asymptotically more accurate than Σ̂
  itself when the asset-count-to-sample-size ratio p/n is non-negligible.
- **Borrowed formula:** F15 — the M001 devour bonus δ is computed
  on a Ledoit–Wolf shrunk TQS-autocorrelation matrix. The shrinkage
  weight is exactly the closed-form α in eq. (14), p. 374 of the
  paper.
- **Failure mode the paper exposes:** §6, pp. 391–393 — the analytical
  optimal α requires the *true* Σ; the paper proposes a consistent
  plug-in estimator that has its own variance at small n. Mitigation
  in F15: clip δ to [0, 0.5] regardless of what the plug-in α
  suggests.
- **Page-level pointer:** Eq. (14), p. 374 (optimal shrinkage
  intensity); §3.3, pp. 374–377 (plug-in estimator); Theorem 3.3,
  p. 376 (consistency).
- **Relevance grade:** A.

---

## Lineage 5 — Kelly criterion and drawdown discipline

A small, dense lineage. Three core references (Kelly, Thorp, MacLean–
Thorp–Ziemba) plus one practitioner book (Vince). The load-bearing
import is F4's Kelly fraction; the failure-mode warnings are why M001
caps at ⅓-Kelly, not full Kelly.

### [5.1] Kelly (1956) — "A New Interpretation of Information Rate"

- **Venue:** Bell System Technical Journal, Vol. 35, No. 4,
  pp. 917–926, 1956.
- **Citation key:** `Kelly1956`
- **Summary.** Maximises the expected logarithm of wealth in a
  repeated favourable bet. Closed-form Kelly fraction for a binary
  outcome with win probability *p* and gross win *b* (loss 1) is
  `f* = p − (1 − p)/b`. Equivalent in the continuous-return limit to
  `f* = μ/σ²`. The growth-optimal bet over an infinite horizon.
- **Borrowed formula:** F4 (Kelly fraction, used as a cap, not a
  target). Both the binary and continuous forms appear verbatim in
  `04-quant-foundations.md` F4.
- **Failure mode the paper exposes:** §IV, p. 923 — Kelly maximises
  long-run growth but has unbounded drawdown variance; the paper
  acknowledges this explicitly. M001 caps at ⅓-Kelly per [5.4] /
  practitioner consensus.
- **Page-level pointer:** Eq. (4), p. 920 (binary Kelly); §III,
  pp. 919–922 (log-utility derivation).
- **Relevance grade:** A.

### [5.2] Thorp (1969) — "Optimal Gambling Systems for Favorable Games"

- **Venue:** Review of the International Statistical Institute,
  Vol. 37, No. 3, pp. 273–293, 1969.
- **Citation key:** `Thorp1969`
- **Summary.** Applies Kelly to blackjack, baccarat, roulette (tilted
  wheel), and warrant hedging. Empirically demonstrates that
  fractional Kelly (¼ to ½) gives smoother growth than full Kelly,
  with marginal long-run-growth loss. This is the operating range
  practitioners cite.
- **Borrowed formula:** F4's fractional Kelly cap. M001 uses ⅓-Kelly
  (within Thorp's ¼–½ range) as the upper bound; the actual bet is
  the *minimum* of ⅓-Kelly and 1 % of equity.
- **Failure mode the paper exposes:** §6, pp. 283–286 — the practical
  *p* and *b* are estimated from small samples; the realised Kelly
  has unbounded variance because the denominator (variance) is the
  thing being estimated. M001 mitigation: estimate Kelly on a trailing
  90-trade rolling window with a minimum-trade floor before promotion.
- **Page-level pointer:** §3, pp. 277–280 (fractional Kelly examples);
  §6, pp. 283–286 (estimation-error discussion).
- **Relevance grade:** A.

### [5.3] Vince (1990) — *Portfolio Management Formulas*

- **Venue:** John Wiley & Sons, 1990. Practitioner book. (Companion
  volume *The Mathematics of Money Management*, Wiley 1992, expands
  on the same material.)
- **Citation key:** `Vince1990`
- **Summary.** Reformulates Kelly for futures / leveraged trading as
  the "optimal-f" fraction: for a stream of historical R-multiple
  trades, find f ∈ [0, 1] that maximises the geometric growth rate of
  the equity curve. Practitioner translation of Kelly to trading,
  including drawdown bounds.
- **Borrowed formula:** Practical f-estimator that complements F4 when
  the win/loss process is non-Bernoulli. v0 M001 uses Kelly directly;
  Vince's optimal-f is the alternative if Kelly's ratio estimator
  proves too noisy on the FX symbol universe.
- **Failure mode the paper exposes:** Optimal-f estimated on a single
  historical equity curve is hopelessly overfit — Vince's own §5
  walks through it. Practitioner consensus is ⅓-optimal-f at most.
- **Page-level pointer:** Ch. 4 "Optimal Fixed Fractional Trading" —
  the canonical optimal-f derivation (chapter title verified against
  the Wiley 1990 first-edition listing, ISBN 978-0-471-52756-5,
  288 pp.). Exact within-chapter pages not directly checked against a
  physical copy — chapter pages approximate; the *content* (optimal-f
  via TWR maximisation) is corroborated by the 1992 companion volume
  *The Mathematics of Money Management* (Wiley) which expands the
  same material.
- **Relevance grade:** C.

### [5.4] MacLean, Thorp & Ziemba (2010) — *The Kelly Capital Growth Investment Criterion: Theory and Practice*

- **Venue:** World Scientific Handbook in Financial Economics, Vol. 3,
  World Scientific Publishing, 2011 (published 10 February 2011 per
  the publisher; the 2010 copyright on early printings caused the
  `2010` suffix in our citation key, which is retained for stability
  across cross-references). 884 pp. edited volume.
- **Citation key:** `MacLeanThorpZiemba2010` (key suffix is the
  copyright year; publication date is 10 February 2011 per World
  Scientific). Chapter-level page citations below are approximate —
  edition-dependent.
- **Summary.** Edited volume that consolidates 50 years of theory
  + practice around the Kelly criterion. Includes the original Kelly
  and Thorp papers, Latané's 1959 independent derivation, Markowitz's
  rebuttal, and ~30 empirical chapters on fractional-Kelly drawdown
  behaviour. *The* place to look for fractional-Kelly evidence.
- **Borrowed formula:** Justifies the M001 choice of ⅓-Kelly (within
  the ¼–½ practitioner range documented across multiple chapters).
- **Failure mode the paper exposes:** Multiple chapters document
  "even ½-Kelly suffers 25 %+ drawdowns" in equity-only backtests.
  This is the empirical justification for M001's hard 1 %-of-equity
  per-trade cap that overrides Kelly downward.
- **Page-level pointer:** Editor introduction (Part I — Early Ideas
  and Contributions); Thorp 1969 reprint and Ziemba's empirical
  drawdown chapter (Part IV — Critics and Assessing the Good and Bad
  Properties of Kelly). Within-volume pages are approximate —
  edition-dependent across the 2011 hardback and the 2012 paperback
  reprint. The originals (Kelly 1956, Thorp 1969) are independently
  verified at their own venues — see [5.1] and [5.2].
- **Relevance grade:** B.

---

## Lineage 6 — Population-Based Training, self-play, MARL diversity

This is the lineage that operationalises the Blue Lock doctrine. Each
of the doctrine's primitives (Awakening, Weapon, Chemical reaction,
Devour, Ego, Adversarial validation) maps to a formal pattern below.
The reading is heavy because the doctrine commits us to *every one of
these* being a real published mechanism, not a metaphor.

### [6.1] Jaderberg et al. (2017) — "Population Based Training of Neural Networks"

- **Venue:** DeepMind technical report; arXiv:1711.09846, 2017. (PBT
  was later integrated into AlphaStar [6.2] and many subsequent
  DeepMind systems; the 2017 arXiv is the foundational reference.)
- **Citation key:** `Jaderberg2017`
- **Summary.** Maintains a population of N networks training in
  parallel with different hyperparameters. Every K steps each network
  *exploits* (if it underperforms a randomly-sampled peer, copy that
  peer's weights and hyperparameters) and *explores* (perturb the
  hyperparameters by a small random factor). The population
  asynchronously self-tunes hyperparameters while training. Applied
  successfully to GAN training, RL on UNREAL, and large-scale
  language models.
- **Borrowed formula:** The exploit-and-explore loop is the operational
  template for the doctrine's **Awakening** mechanism (`06-blue-lock-
  doctrine.md` §1.1). Specifically, the exploit-trigger in M001 is
  TQS-driven (F12), not Sharpe-driven, but the architecture is
  Jaderberg's verbatim.
- **Failure mode the paper exposes:** §4.1, p. 6 — naive exploit
  ranking causes population collapse onto a single ancestor lineage.
  Mitigation in M001: cluster-aware exploit triggers (PBT exploit only
  fires between agents in different HRP clusters per F3) plus diversity
  regularisation from DIAYN [6.7].
- **Page-level pointer:** Algorithm 1, p. 4 (PBT main loop); §4.1,
  p. 6 (collapse failure-mode discussion).
- **Relevance grade:** A.

### [6.2] Vinyals et al. (2019) — "Grandmaster level in StarCraft II using multi-agent reinforcement learning" (AlphaStar)

- **Venue:** Nature, Vol. 575, pp. 350–354, 14 November 2019.
  doi: 10.1038/s41586-019-1724-z.
- **Citation key:** `Vinyals2019`
- **Summary.** League-training architecture: three pools of agents —
  **main agents** (the strongest, evaluated head-to-head), **main
  exploiters** (whose only job is to beat current main agents and
  expose their weaknesses), **league exploiters** (whose job is to
  find population-wide weaknesses). Prioritised fictitious self-play
  for opponent selection. Achieves grandmaster-level StarCraft II
  with ~10 % of the human-game data of prior work.
- **Borrowed formula:** F14 (adversarial validation) is verbatim
  the league-exploiter pattern: strikers = main agents, Sae composite
  (F16) = synthetic main-exploiter-equivalent, Kaiser/Loki (human
  trader benchmarks) = league exploiters. The three-tier opponent
  structure in `06-blue-lock-doctrine.md` §5 is named in the
  doctrine as "the AlphaStar translation".
- **Failure mode the paper exposes:** Methods §A.4 (Supplementary,
  pp. 27–30) — exploiter agents can game cosmetic weaknesses without
  generalisable improvement. AlphaStar mitigated this by requiring
  exploiters to beat *multiple* main-agent generations before being
  retired. M001 mitigation: F14's Coverage ≥ 0.6 *and* PnL_HH ≥ 0
  joint requirement, not either-or.
- **Page-level pointer:** Fig. 3, p. 352 (league architecture);
  Supplementary §A.4, pp. 27–30 (exploiter dynamics and gaming-
  resistance heuristics).
- **Relevance grade:** A.

### [6.3] Baker et al. (2019) — "Emergent Tool Use From Multi-Agent Autocurricula" (Hide and Seek)

- **Venue:** International Conference on Learning Representations
  (ICLR) 2020. arXiv:1909.07528, OpenAI, 2019.
- **Citation key:** `Baker2019`
- **Summary.** Two teams (hiders, seekers) in a simple physics
  sandbox. Six distinct strategies emerged from purely competitive
  self-play — box pushing, ramp use, box locking, ramp defense,
  surfing on boxes, and exploiting physics-engine bugs — that none of
  the agents was designed to discover. Each new strategy was a
  competitive response to the previous one (the autocurriculum).
- **Borrowed formula:** Conceptual import: justifies the "let the
  squad evolve" philosophy of devour and chemical reaction (doctrine
  §1.1). M001 does not implement a closed-loop autocurriculum in v0,
  but Φ5+ exploiter agents are explicitly modelled on Baker's hiders/
  seekers dynamic.
- **Failure mode the paper exposes:** §5, p. 8 — two of the six
  emergent strategies were *reward-hacks* (exploiting bugs in the
  simulator), not real solutions. M001 mitigation: Risk Conductor's
  hard SL invariant (Sentinel R1–R5 in doctrine §4.3) constrains the
  action space so that "trade-the-bug" reward-hacks are mechanically
  refused.
- **Page-level pointer:** Fig. 3, p. 5 (six emergent strategies in
  order); §5, p. 8 (reward-hack discussion).
- **Relevance grade:** B.

### [6.4] Berner et al. (2019) — "Dota 2 with Large Scale Deep Reinforcement Learning" (OpenAI Five)

- **Venue:** OpenAI technical report; arXiv:1912.06680, 2019.
- **Citation key:** `Berner2019`
- **Summary.** Cooperative MARL at scale: five agents acting in a
  team to play Dota 2 against human professionals. Introduces the
  **team-spirit** scalar τ ∈ [0, 1] that interpolates per-agent reward
  between purely individual (τ = 0) and equally-shared team reward
  (τ = 1). The training schedule starts low and rises to ~ 1.
- **Borrowed formula:** The team-spirit concept maps to M001's
  **ego coefficient** (doctrine §3.1) — but *inverted*. Blue Lock's
  doctrine deliberately keeps τ low (high ego, individual-tilted
  reward) for most strikers. The mathematical form is the same; the
  philosophical choice is opposite.
- **Failure mode the paper exposes:** §7.4, p. 18 — when one team
  member's policy diverged during training, the whole team's
  coordination collapsed. Mitigation in M001: HRP (F3) cluster-aware
  allocation isolates a divergent agent before it can drag the
  ensemble through correlation contagion.
- **Page-level pointer:** §3.4, p. 7 (team-spirit definition);
  §7.4, p. 18 (coordination-collapse failure mode).
- **Relevance grade:** B.

### [6.5] Pathak, Agrawal, Efros & Darrell (2017) — "Curiosity-driven Exploration by Self-Supervised Prediction" (ICM)

- **Venue:** Proceedings of the 34th International Conference on
  Machine Learning (ICML 2017), PMLR Vol. 70, pp. 2778–2787, 2017.
- **Citation key:** `Pathak2017`
- **Summary.** Intrinsic Curiosity Module (ICM): a forward dynamics
  model is trained to predict the next state given the current state
  and action; the agent gets an *intrinsic reward* equal to the
  prediction error. This drives the agent toward novel parts of the
  state space without any extrinsic reward. Demonstrated on VizDoom
  and Mario.
- **Borrowed formula:** The "be different from the mean" intrinsic-
  reward formulation is the inspiration for M001's Φ5+ per-agent
  training objective `TQS_i + ego_i × (TQS_i − mean(TQS_others))` — the
  second term is an explicit M001-flavoured curiosity reward.
- **Failure mode the paper exposes:** §5, p. 2782 — curiosity rewards
  dominate task rewards in environments with low extrinsic-reward
  density. Mitigation in M001: hard cap `ego_i ≤ 1.0` so the curiosity
  term cannot exceed the TQS task term.
- **Page-level pointer:** §3, pp. 2780–2781 (ICM architecture and
  intrinsic-reward definition); §5, p. 2782 (noisy-TV failure mode).
- **Relevance grade:** B.

### [6.6] Burda et al. (2018) — "Exploration by Random Network Distillation" (RND)

- **Venue:** International Conference on Learning Representations
  (ICLR) 2019. arXiv:1810.12894, 2018.
- **Citation key:** `Burda2018`
- **Summary.** Simpler scalable alternative to ICM: a fixed random
  *target* network maps states to a feature vector; a trainable
  *predictor* network learns to match the target. The prediction
  error on novel states is the intrinsic reward. Avoids ICM's "noisy
  TV" failure mode (where stochastic dynamics produce permanent high
  intrinsic reward).
- **Borrowed formula:** RND is the tractable Φ5+ implementation of
  the intrinsic-reward channel that ICM ([6.5]) defines. If M001 ever
  ships neural agents, RND is the curiosity backbone; v0 rule-based
  agents use the ego coefficient as the analytical equivalent.
- **Failure mode the paper exposes:** §4.4, p. 7 — RND intrinsic
  rewards decay over the training horizon (the predictor learns the
  target everywhere). Mitigation: bound the M001 Φ5+ training horizon
  to a window short enough that the diversity reward remains
  informative (treated as Φ5+ open research).
- **Page-level pointer:** §3, p. 4 (RND architecture); §4.4, p. 7
  (intrinsic-reward decay).
- **Relevance grade:** B.

### [6.7] Eysenbach, Gupta, Ibarz & Levine (2018) — "Diversity is All You Need" (DIAYN)

- **Venue:** International Conference on Learning Representations
  (ICLR) 2019. arXiv:1802.06070, 2018.
- **Citation key:** `Eysenbach2018`
- **Summary.** Trains a population of skills with explicit diversity
  reward: a discriminator tries to predict which skill an agent is
  executing from its state, and each skill is rewarded for being
  distinguishable. Yields a portfolio of behaviourally-distinct
  policies *without* any task reward.
- **Borrowed formula:** The DIAYN diversity reward is the formal
  objective M001 uses to *enforce* the doctrine's weapon principle
  under PBT (`06-blue-lock-doctrine.md` §1.1 weapon → DIAYN reward).
  Specifically, under Φ5+ PBT, the exploit-explore drift will pull
  strikers toward whatever is currently winning unless an explicit
  diversity term keeps the squad heterogeneous.
- **Failure mode the paper exposes:** §6, p. 9 — diversity-only
  training produces a portfolio of distinguishable but task-weak
  policies. Mitigation in M001: diversity reward is gated on a
  minimum-TQS floor; an agent that is "different but bad" gets cut
  (doctrine §3.4 devour cycle), not protected.
- **Page-level pointer:** §3, pp. 3–4 (DIAYN objective); Algorithm 1,
  p. 4.
- **Relevance grade:** A.

### [6.8] Lowe et al. (2017) — "Multi-Agent Actor-Critic for Mixed Cooperative-Competitive Environments" (MADDPG)

- **Venue:** Advances in Neural Information Processing Systems
  (NeurIPS) 30, pp. 6379–6390, 2017. arXiv:1706.02275.
- **Citation key:** `Lowe2017`
- **Summary.** Multi-Agent Deep Deterministic Policy Gradient: each
  agent has its own actor π_i(observation) and its own critic
  Q_i(state, joint-action). Centralised training (the critic sees
  every agent's action), decentralised execution (the actor sees only
  its own observation). This is the **CTDE** pattern.
- **Borrowed formula:** CTDE is the architectural pattern M001
  adopts: each agent acts on its local market state at inference
  time, but the aggregator/allocator (the centralised critic
  equivalent) trains/calibrates on joint outcomes. M001 v0 keeps the
  actors *rule-based* and only adopts CTDE *training* at Φ5+.
- **Failure mode the paper exposes:** §5, p. 9 — MADDPG is sample-
  inefficient and struggles with > ~10 agents. M001 mitigation: keep
  the v0 roster at 10 agents (`05-agent-roster-v0.md`) and stay
  rule-based until Φ5+, when this scaling limit is re-tested.
- **Page-level pointer:** Algorithm 1, p. 4 (MADDPG main loop); §5.3,
  p. 9 (scaling limits).
- **Relevance grade:** B.

### [6.9] Foerster, Farquhar, Afouras, Nardelli & Whiteson (2018) — "Counterfactual Multi-Agent Policy Gradients" (COMA)

- **Venue:** Proceedings of the 32nd AAAI Conference on Artificial
  Intelligence (AAAI 2018), Vol. 32, No. 1, 2018.
  doi: 10.1609/aaai.v32i1.11794. arXiv:1705.08926.
- **Citation key:** `Foerster2018`
- **Summary.** Solves the multi-agent credit-assignment problem:
  when the team wins, *who* caused the win? COMA uses a
  *counterfactual baseline* — for each agent i, marginalise its own
  action while keeping the other agents' actions fixed, and compare
  the realised joint-Q to the marginal-Q expectation. The difference
  is i's specific contribution. Centralised critic computes this
  baseline in one forward pass.
- **Borrowed formula:** This is the formal model behind M001's
  **devour** mechanism (`06-blue-lock-doctrine.md` §3.4): "what
  would TQS have been if agent i had abstained?" The counterfactual
  baseline is exactly the Foerster formulation translated from
  action-credit to outcome-credit. F17 (ΔInfo) extends the same idea
  to information-access credit.
- **Failure mode the paper exposes:** §6, pp. 5–6 — counterfactual
  estimates have high variance at small sample sizes (the marginal
  expectation requires many counterfactual rollouts). Mitigation in
  M001: devour cycle is weekly with a 30-trade minimum (`04-quant-
  foundations.md` F15).
- **Page-level pointer:** §3, p. 3 (counterfactual baseline); Algorithm
  1, p. 4 (COMA training); §6, pp. 5–6 (variance discussion).
- **Relevance grade:** A.

### [6.10] Sukhbaatar, Lin, Kostrikov, Synnaeve, Szlam & Fergus (2017) — "Intrinsic Motivation and Automatic Curricula via Asymmetric Self-Play"

- **Venue:** International Conference on Learning Representations
  (ICLR) 2018. arXiv:1703.05407, 2017.
- **Citation key:** `Sukhbaatar2017`
- **Summary.** A learner agent is paired with an *adversary* agent
  that proposes increasingly-hard tasks. The adversary is rewarded
  for proposing tasks the learner *just barely* fails; the learner is
  rewarded for solving the adversary's tasks. Yields an automatic
  curriculum that scales task difficulty to the learner's frontier.
- **Borrowed formula:** Conceptual scaffold for F14's
  human-as-opponent framing. Kaiser (human's high-conviction trades)
  and Loki (human's mid-week revisions) are the asymmetric adversary;
  the squad is the learner. The asymmetry is exactly the
  Sukhbaatar–Fergus setup: the human's *intent* is the privileged
  task-proposing signal.
- **Failure mode the paper exposes:** §4.3, p. 7 — if the adversary's
  tasks become trivially easy, the learner stops growing. Mitigation
  in M001: three-tier opponent (Kaiser / Loki / Sae composite); the
  squad cannot coast against any single tier.
- **Page-level pointer:** §3, pp. 3–4 (asymmetric reward); §4.3,
  p. 7 (curriculum-collapse failure mode).
- **Relevance grade:** B.

---

## Lineage 7 — Backtest discipline (PBO, DSR, multiple testing)

Three load-bearing papers + one editorial. These are the
non-negotiable references for the C5 (PBO) and C6 (DSR) charter
gates.

### [7.1] Bailey, Borwein, López de Prado & Zhu (2015) — "The Probability of Backtest Overfitting"

- **Venue:** Journal of Computational Finance, Vol. 20, No. 4,
  pp. 39–69, 2015 (published 2017 in print; circulating from 2013 as
  SSRN 2326253).
- **Citation key:** `Bailey2015`
- **Summary.** Defines PBO as the probability that the in-sample
  best configuration underperforms the out-of-sample median.
  Estimates it via **Combinatorially Symmetric Cross-Validation
  (CSCV)**: split the return matrix (T periods × K candidate configs)
  into 2S equal time blocks; for each of the C(2S, S) block
  combinations, find the IS best and check if it beats the OOS
  median; PBO = fraction of combinations where it does not.
- **Borrowed formula:** F5 (PBO via CSCV). The C5 charter gate
  requires PBO ≤ 0.5.
- **Failure mode the paper exposes:** §4.2, p. 51 — CSCV assumes
  block-wise independence. FX H4 series have block autocorrelation
  that biases PBO downward. Mitigation: block-size selection per the
  paper's §5, p. 56 — choose S so each block exceeds the integrated-
  autocorrelation length of the loss series.
- **Page-level pointer:** Definition of PBO, eq. (1), p. 43; CSCV
  algorithm, §3.2, pp. 46–49; block-size guidance, §5, p. 56.
- **Relevance grade:** A.

### [7.2] Bailey, Borwein, López de Prado & Zhu (2014) — "Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance"

- **Venue:** Notices of the American Mathematical Society, Vol. 61,
  No. 5, pp. 458–471, May 2014.
- **Citation key:** `Bailey2014b`
- **Summary.** Companion piece to [7.1] aimed at the broader math /
  finance community. Demonstrates that with only five years of daily
  data and 45+ independent variations of a strategy tried, the
  best-of-K-trials Sharpe is > 1.0 by chance alone — i.e. all
  "edge" can be selection artefact.
- **Borrowed formula:** The "minimum backtest length" rule of thumb
  in §4, p. 463: `MinBTL ≈ ((1.96/E[SR]_max)² × ln(N))` years of
  daily data needed to support N independent strategy trials at
  α = 0.05. M001 uses this to gate the number of fusion variants we
  test at gate C5.
- **Failure mode the paper exposes:** The pseudo-mathematics framing
  itself: backtest reports without selection-bias correction are
  *equivalent* to mining a uniform-random series and reporting the
  winner. M001's response is the mandatory pairing of every reported
  Sharpe with its DSR ([7.3]) and its PBO ([7.1]).
- **Page-level pointer:** Eq. (1), p. 459 (MinBTL formula); §4–5,
  pp. 463–466 (charlatanism case studies).
- **Relevance grade:** A.

### [7.3] Bailey & López de Prado (2014) — "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality"

- **Venue:** Journal of Portfolio Management, Vol. 40, No. 5,
  pp. 94–107, 2014.
- **Citation key:** `Bailey2014a`
- **Summary.** Adjusts the reported Sharpe ratio for (a) selection
  bias (the reporter picked the best of K trials), (b) non-normal
  returns (skew and excess kurtosis bias the Sharpe estimator). The
  deflated SR is the probability that the realised Sharpe exceeds a
  null benchmark `SR₀` derived in closed form from K and the trial's
  σ_SR.
- **Borrowed formula:** F6 verbatim (`DSR = Φ((SR̂ − SR₀) × √(n−1) /
  √(1 − γ₃ SR̂ + ((γ₄ − 1)/4) SR̂²))`). M001 requires DSR > 0 with
  one-sided α = 0.05 at agent-eligibility gate.
- **Failure mode the paper exposes:** §3.3, p. 100 — DSR variance
  is high at small n (< 30 trades). Mitigation: M001 charter gate
  requires `n_trades ≥ 30` before DSR is computed (mirrored to F17).
- **Page-level pointer:** Eq. (10), p. 99 (DSR formula); §3.3, p. 100
  (small-n caveat); Table 1, p. 102 (DSR vs raw Sharpe on simulated
  selection scenarios).
- **Relevance grade:** A.

### [7.4] Harvey, Liu & Zhu (2016) — "… and the Cross-Section of Expected Returns"

- **Venue:** Review of Financial Studies, Vol. 29, No. 1, pp. 5–68,
  2016.
- **Citation key:** `HarveyLiu2016`
- **Summary.** Surveys the > 300 published "anomalies" in the asset-
  pricing cross-section and applies a multiple-testing correction
  (Bonferroni and FDR-style). Argues that with 300+ trials at
  α = 0.05, the realistic significance threshold for a *new* anomaly
  is |t| > 3.0, not the conventional |t| > 2.0. Renames the field's
  significance bar by ~50 %.
- **Borrowed formula:** Multiple-testing logic for the M001
  experiment registry (`07-research-standards.md` and the lab's
  E001–E007 evidence). The lab's verdict-registry FDR floor is set
  with Harvey-Liu-Zhu in mind.
- **Failure mode the paper exposes:** §V, p. 38 — Bonferroni is
  conservative; the realistic correction for *correlated* anomalies
  is the Benjamini-Hochberg FDR procedure adapted to dependent
  tests. M001 uses FDR-BH at the lab/experiment level
  (`finance-research-experiments/PROTOCOL.md`).
- **Page-level pointer:** §III, pp. 15–25 (the 300+ anomalies
  catalogue); §V, pp. 35–45 (multiple-testing correction proposals).
- **Relevance grade:** B.

---

## Lineage 8 — Microstructure, VPIN, friction

A small lineage, but F7 (VPIN) is load-bearing and the Kyle-1985
adverse-selection model is the theoretical backbone everyone in this
lineage cites.

### [8.1] Kyle (1985) — "Continuous Auctions and Insider Trading"

- **Venue:** Econometrica, Vol. 53, No. 6, pp. 1315–1335, November
  1985.
- **Citation key:** `Kyle1985`
- **Summary.** Single-informed-trader model where one trader knows
  the asset's true value, noise traders trade randomly, and a market
  maker sets prices to break even on average. Yields the famous
  "Kyle's lambda" — the price-impact coefficient that scales linearly
  with order size. Foundation of every information-asymmetry
  microstructure model.
- **Borrowed formula:** Kyle's lambda is the theoretical justification
  for treating VPIN ([8.3]) as a regime feature. M001 does not
  estimate lambda directly; it uses VPIN as the empirical analogue.
- **Failure mode the paper exposes:** §IV, p. 1326 — the single-
  informed-trader assumption is unrealistic in modern FX (many
  informed traders, much faster updating). The model still anchors
  the *direction* of the prediction (high information asymmetry →
  high adverse-selection cost → wider spreads → discriminator
  signal for trend regimes).
- **Page-level pointer:** §II, pp. 1318–1322 (model setup);
  Proposition 1, p. 1322 (lambda derivation).
- **Relevance grade:** C.

### [8.2] Hasbrouck (2007) — *Empirical Market Microstructure*

- **Venue:** Oxford University Press, 2007. ISBN 978-0-19-530164-9.
  ix + 198 pp. textbook. (Pagination verified against the OUP /
  Library of Congress catalog record and the publisher's published
  TOC.)
- **Citation key:** `Hasbrouck2007`
- **Summary.** Standard graduate textbook on equity-market
  microstructure. Covers order-flow imbalance and PIN estimation,
  Kyle-style strategic trade models (lambda), spread decomposition
  (Roll, Glosten-Harris, Madhavan-Richardson-Roomans), and high-
  frequency volatility estimators. The book treats centralised
  equity markets as the canonical setting — FX-specific
  microstructure is *not* a chapter; see Lyons (2001) [9.4] for that.
- **Borrowed formula:** Operational definition of order-flow imbalance
  used as a feature in Φ4+ regime classifiers. v0 M001 does not have
  order-book data; this is a forward-looking reference for when
  microstructure features become available.
- **Failure mode the paper exposes:** The textbook's centralised-tape
  assumption is what *fails* in FX — order-flow imbalance is
  dealer-specific and hard to estimate without consolidated tape.
  Mitigation: M001 v0 uses transaction-count proxies per F7's
  "Failure mode" note in `04-quant-foundations.md`; FX-specific
  treatment is delegated to Lyons (2001) [9.4].
- **Page-level pointer:** Ch. 6 "Order Flow and the Probability of
  Informed Trading (PIN)" (starts p. 65); Ch. 7 "Strategic Trade
  Models" (starts p. 70) — the Kyle / lambda chapter; Ch. 9
  "Multivariate Linear Microstructure Models" (starts p. 90) for the
  Hasbrouck VAR construction. Chapter starts verified against the
  OUP catalog; within-chapter section pages not separately checked.
- **Relevance grade:** C.

### [8.3] Easley, López de Prado & O'Hara (2012) — "Flow Toxicity and Liquidity in a High-Frequency World"

- **Venue:** Review of Financial Studies, Vol. 25, No. 5,
  pp. 1457–1493, 2012. doi: 10.1093/rfs/hhs053.
- **Citation key:** `Easley2012`
- **Summary.** Defines **VPIN** (Volume-synchronized Probability of
  Informed Trading): aggregate trades into volume-equal buckets,
  classify each bucket's volume as buy- or sell-driven (the paper
  proposes Bulk Volume Classification), and compute the volume
  imbalance over a rolling window of buckets. VPIN spikes
  predict short-term volatility increases and were claimed to have
  forecast the 2010 Flash Crash 30 minutes ahead.
- **Borrowed formula:** F7 (VPIN). M001 uses VPIN as a per-agent
  `regime_fit` input — a momentum agent should up-weight in
  high-VPIN regimes, a mean-revert agent should down-weight.
- **Failure mode the paper exposes:** §IV, pp. 1480–1485 — VPIN's
  signal-to-noise depends critically on the volume-bucket size; the
  paper's defaults (50 buckets per day with 1/50th of daily volume
  per bucket) are not portable across asset classes. Mitigation in
  M001: per-symbol VPIN calibration on training-window data only.
  Also: the **Andersen–Bondarenko (2014)** rejoinder argues VPIN's
  predictive power for volatility *vanishes* once you control for
  trailing volatility itself. M001 treats VPIN as a regime *label*,
  not as a return predictor, to sidestep this critique.
- **Page-level pointer:** Algorithm in §III, pp. 1467–1473; eq. (8)
  on p. 1470 (VPIN definition).
- **Relevance grade:** A.

### [8.4] Avellaneda & Stoikov (2008) — "High-frequency trading in a limit order book"

- **Venue:** Quantitative Finance, Vol. 8, No. 3, pp. 217–224, 2008.
- **Citation key:** `AvellanedaStoikov2008`
- **Summary.** Optimal market-making model: dealer posts bid and ask
  to minimise inventory risk + maximise expected spread capture.
  Closed-form bid/ask quotes depend on the dealer's current
  inventory, the time-to-close, and the asset volatility.
- **Borrowed formula:** Not used in M001 v0 (the squad does not
  market-make). Cited as the model-of-record for if/when a market-
  making agent joins the roster.
- **Failure mode the paper exposes:** §4, p. 222 — closed-form solution
  assumes a Brownian price process; jump-driven FX news events break
  the assumption.
- **Page-level pointer:** Eq. (12)–(13), p. 220 (optimal bid/ask).
- **Relevance grade:** C.

---

## Lineage 9 — FX-specific (drift, carry, AMH, regime classification, RL trading prior art)

The domain-specific lineage. Closes F16 (Sae composite components),
F18 (regime taxonomy), and named the closest published prior art to
M001 itself (Yang 2020, AlphaPortfolio, FinRL).

### [9.1] Lo & MacKinlay (1988) — "Stock Market Prices Do Not Follow Random Walks: Evidence from a Simple Specification Test"

- **Venue:** Review of Financial Studies, Vol. 1, No. 1, pp. 41–66,
  1988. doi: 10.1093/rfs/1.1.41.
- **Citation key:** `LoMacKinlay1988`
- **Summary.** Introduces the **variance-ratio test**: under a random
  walk, the variance of q-period returns equals q × the variance of
  1-period returns. The authors compute VR(q) for 1962–1985 weekly
  CRSP returns at q = 2, 4, 8, 16 and reject the random walk at all
  horizons. Evidence of positive short-horizon autocorrelation that
  the paper attributes partly to micro-structure and partly to genuine
  predictability.
- **Borrowed formula:** Conceptual import for F18 — the variance-ratio
  test is one of the regime-classifier inputs (trending regime is
  associated with VR > 1; mean-reverting is VR < 1). M001 v0
  classifier uses ADX as the primary tag (per F18); VR is reserved
  for the v1 classifier upgrade.
- **Failure mode the paper exposes:** §4, p. 56 — VR is sensitive
  to outliers and to the choice of q. Mitigation in M001: ensemble
  the variance-ratio classifier with ADX rather than rely on it alone.
- **Page-level pointer:** Eq. (5), p. 45 (VR statistic); Table 1,
  p. 47 (CRSP VR results).
- **Relevance grade:** B.

### [9.2] Hamilton (1989) — "A New Approach to the Economic Analysis of Nonstationary Time Series and the Business Cycle"

- **Venue:** Econometrica, Vol. 57, No. 2, pp. 357–384, March 1989.
  doi: 10.2307/1912559.
- **Citation key:** `Hamilton1989`
- **Summary.** Markov-regime-switching model: the parameters of an
  AR(p) process are drawn from a discrete-state Markov chain
  (S_t ∈ {1, 2, …, K}), where the regime is unobserved. The Hamilton
  filter recursively computes Pr(S_t = k | data through t) and is
  used to estimate transition probabilities by maximum likelihood.
  Foundational paper for every regime-switching model in macro,
  asset pricing, and quant trading since.
- **Borrowed formula:** F18 (regime-conditional KPIs and HRP). M001
  v0 uses a *deterministic* regime classifier (ADX bucket, σ percentile,
  calendar tag) rather than a Hamilton filter, but the regime
  *taxonomy* is Hamilton's pattern. Φ5+ may upgrade to a Hamilton
  filter when training data is large enough to estimate transition
  probabilities reliably.
- **Failure mode the paper exposes:** §IV, pp. 370–376 — Hamilton-
  filter likelihoods are non-convex; multiple local optima exist and
  the MLE depends on starting values. Mitigation: M001 v0 sidesteps
  by using deterministic classifiers; v0.5 upgrade requires the
  multi-start optimisation Hamilton recommends.
- **Page-level pointer:** §II, pp. 360–365 (Markov-switching setup);
  Algorithm in §III, pp. 365–369 (Hamilton filter recursion).
- **Relevance grade:** A.

### [9.3] Lo (2004) — "The Adaptive Markets Hypothesis: Market Efficiency from an Evolutionary Perspective"

- **Venue:** Journal of Portfolio Management, Vol. 30, No. 5,
  pp. 15–29, 30th Anniversary Issue, 2004.
- **Citation key:** `Lo2004`
- **Summary.** Reconciles EMH with behavioural finance via
  evolutionary dynamics: market efficiency is not a fixed property
  but a *process* of adaptation. Trading strategies have lifecycle
  arcs (discovery → exploitation → saturation → decay); behavioural
  biases are heuristics that were once adaptive in their environment.
- **Borrowed formula:** Conceptual scaffold — the doctrine's
  "Awakening" mechanism (PBT-based agent regeneration, doctrine §1.1)
  is the M001 operationalisation of the AMH lifecycle: an agent's
  edge decays as the market adapts, and PBT spawns replacements
  before the decay is fatal.
- **Failure mode the paper exposes:** AMH is empirically qualitative;
  Lo himself flags this (§VI, p. 24). No closed-form test of AMH.
  Mitigation: M001 treats AMH as motivation for the PBT mechanism,
  not as a falsifiable claim of the program.
- **Page-level pointer:** §III–IV, pp. 18–22 (AMH definition);
  §VI, p. 24 (qualitative-nature acknowledgement).
- **Relevance grade:** B.

### [9.4] Lyons (2001) — *The Microstructure Approach to Exchange Rates*

- **Venue:** MIT Press, 2001. ISBN 0-262-12243-X. 333 pp. textbook.
  (Pagination and chapter list verified against the MIT Press direct
  TOC and the author's Berkeley faculty page.)
- **Citation key:** `Lyons2001`
- **Summary.** Foundational FX-microstructure textbook. Order flow
  has *persistent* explanatory power for exchange-rate returns even
  controlling for macro fundamentals. Introduces the order-flow-based
  pricing framework that has dominated empirical FX research since.
- **Borrowed formula:** Operational definition of "FX order flow" used
  in the Φ4+ microstructure agent (M001's A8 / A9 in `05-agent-
  roster-v0.md` reference Lyons' framework, even though v0 does not
  have order-book data).
- **Failure mode the paper exposes:** Ch. 3 §3.3 "Transparency of
  Order Flow" — order-flow data is dealer-specific and consolidated
  tape does not exist in FX. Mitigation: v0 M001 uses transaction-
  count proxies; Φ5+ may ingest demo broker's L2 if and when it
  becomes reliable.
- **Page-level pointer:** Ch. 2 "The Economics of Order Flow
  Information" — §2.2 "Empirical Evidence that Order Flow is
  Informative" is the canonical statement of the order-flow / return
  link; Ch. 5 "Empirical Frameworks" — §5.3 "Findings: Informative
  Order Flow and Imperfect Risk Sharing" extends it. Chapter
  structure verified against the MIT Press TOC; within-chapter pages
  approximate — exact pagination not separately checked against the
  2001 first edition.
- **Relevance grade:** C.

### [9.5] Yang, Liu, Zhong & Walid (2020) — "Deep Reinforcement Learning for Automated Stock Trading: An Ensemble Strategy"

- **Venue:** ICAIF '20: 1st ACM International Conference on AI in
  Finance, October 15–16, 2020. (Also SSRN 3690996.)
- **Citation key:** `Yang2020`
- **Summary.** Trains three actor-critic RL agents (PPO, A2C, DDPG)
  separately, then ensembles by *selecting* the one with the highest
  trailing 3-month Sharpe ratio at each rebalance. Tested on DJIA 30
  with H1 bars. Out-performs each individual algorithm and the DJIA
  buy-and-hold baseline.
- **Borrowed formula:** F10 (Sharpe-weighted ensemble). This is the
  cleanest published precedent for what M001 is doing — multiple RL
  policies fused on a trailing performance metric — and the
  performance bar Yang et al. report (≈ 0.5–0.7 OOS Sharpe over a 6-
  month evaluation) is the M001 v0 "baseline-to-beat" reference point.
- **Failure mode the paper exposes:** Their selection rule picks
  *one* algorithm at a time, not a weighted average — high
  whip-saw between algorithms as trailing Sharpe rotates. M001
  mitigation: F10 uses a continuous weight (not a winner-take-all
  selection) with a 60-trade minimum window.
- **Page-level pointer:** §4, p. 5 (ensemble strategy definition);
  §5, pp. 6–8 (DJIA results).
- **Relevance grade:** A.

### [9.6] Liu, Yang, Gao & Wang (2021) — "FinRL: Deep Reinforcement Learning Framework to Automate Trading in Quantitative Finance"

- **Venue:** ICAIF '21: 2nd ACM International Conference on AI in
  Finance, November 3–5, 2021. doi: 10.1145/3490354.3494366.
  arXiv:2111.09395.
- **Citation key:** `Liu2021`
- **Summary.** Open-source framework that wraps PPO / A2C / DDPG /
  SAC / TD3 in a unified market-simulator environment. Three-layer
  modular architecture (market simulator → agent → strategy harness).
  Has become the de facto open-source RL-for-trading baseline.
- **Borrowed formula:** F16's `FinRL_PPO` sub-component of the Sae
  composite is an off-the-shelf FinRL PPO agent. We adopt FinRL as
  an *engineering* reference (its market simulator + PPO wiring),
  not as a research result — M001 holds its own evidence bar.
- **Failure mode the paper exposes:** §6, p. 7 — FinRL's published
  examples have weak out-of-sample validation by the M001 evidence
  bar (no PBO, no DSR). Mitigation: we use FinRL agents as *frozen*
  components in F16 — their inputs and weights are locked before the
  evaluation window, removing any in-sample tuning.
- **Page-level pointer:** §3, pp. 3–5 (FinRL architecture); §5,
  pp. 6–7 (stock-trading example).
- **Relevance grade:** B.

### [9.7] Théate & Ernst (2021) — "An Application of Deep Reinforcement Learning to Algorithmic Trading"

- **Venue:** Expert Systems with Applications, Vol. 173, Article
  114632, 1 July 2021. arXiv:2004.06627.
- **Citation key:** `Theate2021`
- **Summary.** Introduces TDQN (Trading Deep Q-Network), a variant
  of DQN adapted for daily-bar long/short trading. The paper's key
  contribution is the **performance-assessment methodology** — they
  test on 30 individual stocks and an index ETF, and report
  *exactly* how unstable the results are across symbols and seeds.
- **Borrowed formula:** Not used in F1–F18. Cited for its honest
  treatment of the OOS-instability problem in RL-trading — the
  paper's §6 (p. 17) is one of the few in the literature that
  explicitly reports negative results per-symbol, which calibrates
  M001's expectations on what "beating buy-and-hold" actually means
  in this lineage.
- **Failure mode the paper exposes:** §6, p. 17 — TDQN's per-symbol
  performance is high-variance; the "average across 30 stocks"
  headline number hides cases where TDQN underperforms buy-and-hold
  by 30 %+ on individual symbols. M001 mitigation: F18's regime-
  conditional KPIs report per-regime, not pooled.
- **Page-level pointer:** §4–5, pp. 8–14 (TDQN architecture &
  experiments); §6, pp. 14–17 (per-symbol breakdown and honest
  failure-mode reporting).
- **Relevance grade:** C.

### [9.8] Cong, Tang, Wang & Zhang (2021) — "AlphaPortfolio: Direct Construction Through Deep Reinforcement Learning and Interpretable AI"

- **Venue:** SSRN Working Paper 3554486, posted 20 April 2020, last
  revised 2 March 2022, 76 pp. (Stanford Digital Repository
  fy908xd8332; SITE Conference 2021). **As of 2026 the paper has no
  peer-reviewed journal publication** — verified via the SSRN entry
  and the NBER record. A re-titled, three-author successor
  (Cong, Tang & Wang, dropping the fourth author Zhang) is now
  available as **NBER Working Paper 35195 (2026)**
  "AlphaPortfolio: Goal-Oriented Investment Management Through Deep
  Reinforcement Learning" — distinct paper, not a journal publication
  of the SSRN version. M001 cites the original SSRN version because
  that is what the architectural pattern (multi-sequence attention,
  CAAN, direct-Sharpe optimisation) was published in.
- **Citation key:** `Cong2021`
- **Summary.** RL framework that *directly* optimises a portfolio
  objective (Sharpe ratio) end-to-end, without first estimating
  return distributions or pricing kernels. Uses a multi-sequence
  attention-based neural net (SREM + CAAN). Reports > 2.0 OOS
  Sharpe on US equities with monthly rebalancing.
- **Borrowed formula:** Conceptual scaffold for the Φ5+ direct-
  optimisation upgrade — instead of training agents on per-bar PnL
  and aggregating, train the aggregator end-to-end on portfolio
  TQS. M001 v0 stays modular (rule-based agents + hand-coded
  aggregator); end-to-end optimisation is parked.
- **Failure mode the paper exposes:** The reported 2.0+ Sharpe is on
  US equities with monthly rebalancing on a 30-year window; FX with
  $100 demo accounts and H4 cadence is a different regime. M001
  treats AlphaPortfolio as proof-of-concept for end-to-end RL
  *direction*, not as a numerical benchmark.
- **Page-level pointer:** §2–3 of the SSRN PDF (architecture); §4
  (US-equities backtest). M001 reviews against the
  20 April 2020 / 2 March 2022 SSRN revision (76 pp.); exact within-
  section pages depend on the SSRN-PDF version snapshot — record the
  SSRN revision date alongside any page citation that lands in a
  M001 deliverable.
- **Relevance grade:** C.

---

## 10. Cross-reference table — F1–F18 → source citation keys

The table below is the load-bearing audit trail. Every F-number
declared in `04-quant-foundations.md` resolves to one of the
following:
(a) one or more peer-reviewed source citation keys from this survey, OR
(b) `INTERNAL — defended by M001 derivation` plus the M001
    document section where the derivation lives.

| F# | Topic | Source citation keys |
|---|---|---|
| F1 | Bates–Granger minimum-variance combination | `BatesGranger1969` (primary), `StockWatson2004` (puzzle / equal-weight robustness), `Timmermann2006` (survey context) |
| F2 | Equal Risk Contribution / risk parity | `Maillard2010` (primary), `Roncalli2013` (book-length treatment), `Markowitz1952` (historical anchor) |
| F3 | Hierarchical Risk Parity | `LopezDePrado2016` (primary) |
| F4 | Kelly fraction (as a cap) | `Kelly1956` (primary), `Thorp1969` (fractional Kelly), `MacLeanThorpZiemba2010` (drawdown evidence), `Vince1990` (practitioner translation) |
| F5 | Probability of Backtest Overfitting (PBO) via CSCV | `Bailey2015` (primary), `Bailey2014b` (companion / charlatanism framing) |
| F6 | Deflated Sharpe Ratio | `Bailey2014a` (primary), `HarveyLiu2016` (multiple-testing context) |
| F7 | VPIN (flow toxicity) | `Easley2012` (primary), `Kyle1985` (theoretical backbone), `Hasbrouck2007` (textbook context) |
| F8 | Softmax gating with load-balance auxiliary loss | `Shazeer2017` (primary; auxiliary-loss formulation), `Jacobs1991` (original MoE), `Fedus2022` (capacity-factor extension) |
| F9 | Stacked generalisation (meta-learner) | `Wolpert1992` (primary), `Caruana2004` (greedy ensemble selection) |
| F10 | Sharpe-weighted ensemble | `Yang2020` (primary; ICAIF 2020 ensemble RL paper) |
| F11 | Independent-OR confluence conviction with ego weighting and thought-resonance trigger | **INTERNAL** — no canonical source for the ego-weighted independent-OR form. Closest classical analogue is naïve-Bayes product-of-evidence (folklore; no single citation). M001 derivation lives in `06-blue-lock-doctrine.md` §3.3 and `04-quant-foundations.md` F11 (v0.4 extension for thought-resonance is M001-original). |
| F12 | Trade Quality Score (TQS) — composite per-trade fitness | **INTERNAL** — composite metric, M001-original. Component-design philosophy borrows: concavity in R inspired by Kelly drawdown control (`Kelly1956`, `MacLeanThorpZiemba2010`); selection-bias awareness from `Bailey2014a` (DSR). Derivation in `04-quant-foundations.md` F12. |
| F13 | Coordinate-overlap measure (binary predicate + geometric-mean continuous score) | **INTERNAL** — M001-original. The geometric-mean-over-arithmetic-mean choice draws on risk-budget asymmetry intuitions in `Roncalli2013` Ch. 3. Derivation in `04-quant-foundations.md` F13 and `06-blue-lock-doctrine.md` §3.2. |
| F14 | Adversarial validation (PnL_HH, Coverage, Counter) over rolling 12-week window | `Vinyals2019` (primary; AlphaStar league-exploiter pattern), `Sukhbaatar2017` (asymmetric self-play), `Baker2019` (autocurricula context). Joint Coverage ≥ 0.6 *and* PnL_HH ≥ 0 requirement is the M001-specific tightening of the AlphaStar exploiter-validation idea. |
| F15 | Devour bonus δ from TQS autocorrelation, Ledoit-Wolf shrunk, clipped to [0, 0.5] | `LedoitWolf2004` (primary shrinkage estimator), `Roncalli2013` (ERC-shrinkage pipeline pattern). The autocorrelation-→-δ mapping itself is **INTERNAL** to M001 — derivation lives in `04-quant-foundations.md` F15. |
| F16 | Sae composite baseline = 0.35 CTA_trend + 0.25 Carry + 0.25 FinRL_PPO + 0.15 Frozen_zone_d1_against, ERC-rebalanced weekly | `Menkhoff2012` (carry component primary), `Liu2021` (FinRL PPO component), `Maillard2010` (ERC closed form), `Roncalli2013` (weekly rebalancing rule). The composition itself (the 0.35 / 0.25 / 0.25 / 0.15 starting allocations and the evolution clause) is **INTERNAL** — defended in `04-quant-foundations.md` F16. |
| F17 | ΔInfo — marginal information value of inter-agent observability, with pairwise-block bootstrap CI | `Foerster2018` (primary; counterfactual baseline pattern from COMA, translated from action-credit to information-credit dimension). The information-dimension translation and the pairwise-block bootstrap protocol are **INTERNAL** to M001 — derivation in `04-quant-foundations.md` F17. |
| F18 | Regime-conditional KPIs + regime-conditional HRP allocation | `Hamilton1989` (regime-switching foundation), `LoMacKinlay1988` (variance-ratio regime detection), `LopezDePrado2016` (HRP component). The per-regime HRP coupling and the 1.5×-dominance-threshold rule are **INTERNAL** to M001 — derivation in `04-quant-foundations.md` F18. |

### 10.1 Summary of INTERNAL F-numbers

Five F-numbers are M001-original compositions and carry no canonical
external source:

- **F11** (independent-OR confluence conviction with ego weighting +
  v0.4 thought-resonance trigger).
- **F12** (Trade Quality Score composite fitness).
- **F13** (Coordinate overlap binary predicate + geometric-mean
  continuous score).
- **F15** (mapping from TQS-autocorrelation to devour-bonus δ —
  the *bridge* is internal; the shrinkage estimator and ERC pipeline
  it builds on are cited).
- **F17** (translation of COMA-style counterfactual credit from
  the action dimension to the information dimension; the original
  COMA pattern is cited via `Foerster2018`).

These five are *explicitly defended* in `04-quant-foundations.md` —
each has a "Why we use it" / "Failure mode" / "Decision" pair, just
like the sourced F-numbers. The honest claim of M001 is **not** that
the architecture is unprecedented at the component level; every
component is borrowed. The novelty is in the composition. F11–F13 +
F15 + F17 are the composition.

Three F-numbers are partly internal (the *coefficient choices* /
*starting allocations* / *thresholds* are M001-specific but the
underlying machinery is cited):

- **F14** — coefficient choices (Coverage ≥ 0.6, PnL_HH ≥ 0,
  Counter target band [0.10, 0.25]) are M001-specific; the league-
  exploiter machinery is `Vinyals2019` + `Sukhbaatar2017`.
- **F16** — the 0.35 / 0.25 / 0.25 / 0.15 starting allocations and
  the four-sub-component composition are M001-specific; each sub-
  component is cited (`Menkhoff2012`, `Liu2021`, `Maillard2010`,
  `Roncalli2013`).
- **F18** — the regime taxonomy thresholds (ADX 25/20, σ 90th-percentile,
  1.5×-dominance) are M001-specific; the regime-switching machinery
  is `Hamilton1989` + `LoMacKinlay1988`, the HRP component is
  `LopezDePrado2016`.

This is the audit trail. Every F-number is either sourced, internal
(named honestly), or partly-internal (with explicit listing of which
piece is which).

### 10.2 References previously marked `[VERIFY]` — Φ1-close status

The six entries flagged `[VERIFY]` in v0.1 were chased in v0.2.
None of them affected an A-grade load-bearing claim (the formula
citation is firm in each case; only the page-number or working-
paper-vs-published metadata was uncertain). Status as of v0.2:

- `Roncalli2013` — **resolved**. ERC location locked to Ch. 2
  ("Risk Budgeting Approach"), §2.3 p. 119 (definition) and §2.3.3
  p. 123 (optimality), verified against the author's published TOC
  (`thierry-roncalli.com/RiskParityBook.html`) for the 2013 Chapman
  & Hall / CRC first printing (410 pp.). The previous v0.1 citation
  of "§3.2 / §3.4" was a section-number slip and has been corrected.
- `Vince1990` — **partly resolved**. Book and chapter title locked
  ("Optimal Fixed Fractional Trading" is Ch. 4 of the Wiley 1990
  first edition, 288 pp., ISBN 978-0-471-52756-5, verified against
  the Wiley catalog). Exact within-chapter pages not directly
  checked against a physical copy — chapter pages remain
  approximate.
- `MacLeanThorpZiemba2010` — **partly resolved**. Publication
  metadata locked: World Scientific Handbook in Financial Economics
  Vol. 3, published 10 February 2011, 884 pp. (the "2010" in the
  citation key reflects the early-printing copyright date and is
  retained for stability across cross-references — see §10.3 for the
  date-vs-key discussion). Within-volume page citations for the
  Thorp 1969 reprint and the Ziemba drawdown chapter remain
  approximate — edition-dependent across the 2011 hardback and the
  2012 paperback reprint.
- `Hasbrouck2007` — **resolved**. Full chapter list and starting
  pages locked against the OUP / Library of Congress catalog record
  (ix + 198 pp., not the ~320 pp. estimated in v0.1). Previous v0.1
  citation of "Ch. 6 (FX-specific microstructure)" was wrong —
  Ch. 6 is "Order Flow and the Probability of Informed Trading
  (PIN)" and the book is equity-focused, not FX. Updated to point
  to Ch. 6, Ch. 7 (Strategic Trade Models, the Kyle chapter), and
  Ch. 9 (Multivariate Linear Microstructure Models).
- `Lyons2001` — **partly resolved**. Full chapter list and total
  page count (333 pp., MIT Press 2001, ISBN 0-262-12243-X) locked
  against the MIT Press direct TOC and author's Berkeley faculty
  page. Previous v0.1 citation of "Ch. 8 (data-availability
  discussion)" was wrong — Ch. 8 is "Microstructure and Central
  Bank Intervention"; the data-availability discussion lives in
  Ch. 3 §3.3 "Transparency of Order Flow" and the order-flow /
  return link is in Ch. 2 §2.2. Updated. Within-chapter exact
  pages still approximate.
- `Cong2021` (`AlphaPortfolio`) — **resolved**. SSRN Working Paper
  3554486 confirmed as posted 20 April 2020, last revised 2 March
  2022, 76 pp. **As of 2026 the paper has no peer-reviewed journal
  publication.** A re-titled, three-author successor by the same
  lead authors (Cong, Tang & Wang, without Zhang) is now NBER
  Working Paper 35195 (2026) "Goal-Oriented Investment Management
  Through Deep Reinforcement Learning" — a distinct paper, not a
  journal publication of the SSRN version. M001 keeps the SSRN
  citation as the source of the architectural pattern.

The three "partly resolved" entries (`Vince1990`,
`MacLeanThorpZiemba2010`, `Lyons2001`) carry "chapter pages
approximate — edition-dependent" qualifiers in the entries
themselves; the formula and chapter-content claims are firm.

### 10.3 Conflicts found between the plan §1.x lineages and the actual literature

Two minor conflicts were noted in v0.1; both are now **resolved in
`02-literature-survey-plan.md` v0.4 (2026-06-24)**. They are kept on
record here for audit-trail continuity:

1. **PBO authorship — resolved in plan v0.4.** v0.1 of this survey
   flagged that `02-literature-survey-plan.md` §4 attributed PBO to
   *"López de Prado (2014) — The Probability of Backtest Overfitting"*
   when the actual paper is **Bailey, Borwein, López de Prado & Zhu
   (2015)**, *Journal of Computational Finance* 20(4), pp. 39–69 —
   a four-author paper, not solo-LdP. The 2014 *Notices of the AMS*
   companion (`Bailey2014b`) is by the same four authors. Plan v0.4
   §4 bullet 1 now lists all four authors and the JCF venue, with the
   *Notices* companion as a sub-bullet.
2. **Switch Transformer date — clarified in plan v0.4.** v0.1 noted
   that `02-literature-survey-plan.md` §1.3 cited *"Fedus, Zoph &
   Shazeer (2022) — Switch Transformers"* without flagging that the
   paper first appeared as arXiv:2101.03961 in January 2021 and was
   published in JMLR Vol. 23, No. 120 in 2022. Plan v0.4 §1.3 now
   carries the parenthetical "(arXiv:2101.03961, 2021; JMLR 23(120),
   2022)" so both dates are explicit.

One further inconsistency noted during the v0.2 close pass — **not
yet resolved in the plan, flagged for follow-up:**

3. **AlphaPortfolio first author.** `02-literature-survey-plan.md`
   §1.5 cites the paper as *"Wang et al. (2021) — AlphaPortfolio"*.
   The actual first author is **Lin William Cong** (Cornell). This
   survey's [9.8] is correct (`Cong, Tang, Wang & Zhang (2021)`); the
   plan §1.5 wording needs to be aligned in a future plan revision.
   Not load-bearing for any F-number.

Beyond these three, no formula attributed in §1–§5 of the plan
contradicts the literature we surveyed. F11 / F12 / F13 / F15 / F17
were already named in the plan and in the foundations doc as
INTERNAL or partly-internal compositions; this survey confirms that
naming.

---

## 11. Closing note

The intellectual honesty of this survey is the gate, not the length.
Every load-bearing F-number resolves to either a real peer-reviewed
paper above or an INTERNAL composition that is named honestly and
defended in `04-quant-foundations.md`. Every architectural primitive
in `06-blue-lock-doctrine.md` (PBT, league exploiter, ICM, asymmetric
self-play, CTDE, COMA) resolves to a specific paper in Lineage 6.
The pieces are borrowed; the composition is M001's.

Φ1 close. Φ2 (architecture validation against this lit-base) opens
on this commit.
