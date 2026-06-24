# 04 — Quant Foundations

**Status:** `DRAFT v0.3` — 2026-06-24. v0.3 adds F15 (devour bonus δ
derived from TQS autocorrelation; closes the previously-arbitrary
`δ = 0.25` choice) and F16 (Sae composite baseline; closes the C6
adversarial gate). v0.2 (Pre-literature-pass) source-cited F1–F10 in
`02-literature-survey-plan.md` and added F11–F14 to instantiate the
doctrine in `06-blue-lock-doctrine.md`.

> Convention: bold-italic capitals (***W***, ***Σ***) are matrices /
> vectors. Lower-case greek (μ, σ, ρ) are scalars. *Hat* (μ̂) denotes
> a sample estimate.

This doc collects every formula the multi-agent ensemble depends on,
why we chose it, and the failure mode each formula has. Each entry
will get a verbatim source citation in Φ1.

---

## F1 — Minimum-variance combination of agent forecasts

**Setting.** Each agent *i* emits a forecast (or per-trade PnL)
*xᵢ* of the same unknown target. Sample covariance between agents is
estimated as ***Σ̂***.

**Bates–Granger (1969) minimum-variance weights:**

> ***w**** = (***1***ᵀ ***Σ̂***⁻¹ ***1***)⁻¹ × ***Σ̂***⁻¹ ***1***

Subject to **1**ᵀ ***w*** = 1.

**Why we use it.** It gives the *optimal* linear combination under
the assumption that ***Σ̂*** is well-estimated.

**Failure mode.** When ***Σ̂*** is noisy (typical with ≤ 5 years of
data and N ≥ 5 agents), the inversion blows up and weights become
extreme — including negative weights, which the aggregator would have
to interpret as "short this agent's signal." In practice **simple
average (equal weight)** often dominates (Stock-Watson 2004).

**Decision.** v0 allocator defaults to equal weight (or HRP, see F3).
F1 is a baseline benchmark, not the production allocator.

---

## F2 — Risk parity (equal risk contribution)

**Setting.** Each agent has volatility σᵢ and correlations ρᵢⱼ
forming ***Σ̂***. We want allocations such that every agent
contributes the same **risk**, not the same **capital**.

**Definition (Maillard, Roncalli, Teïletche 2010).** Find weights
***w*** ≥ 0, **1**ᵀ ***w*** = 1, such that:

> wᵢ × (***Σ̂*** ***w***)ᵢ = wⱼ × (***Σ̂*** ***w***)ⱼ ∀ i, j

**Closed form (diagonal Σ — uncorrelated agents):** wᵢ ∝ 1/σᵢ.

**General case:** no closed form; solve numerically (cyclic-coordinate
descent or convex solver). Many open implementations exist.

**Why we use it.** Risk parity has empirically outperformed both
equal-weight and mean-variance over multi-decade horizons in
diversified portfolios (Roncalli 2013). It is the default allocator
at AQR / Bridgewater / Lyxor "All Weather" style funds. It does
exactly what we want: prevent one agent from dominating risk merely
because its capital allocation looks balanced.

**Failure mode.** Assumes Σ is stable. Sudden regime shift breaks
the estimate. Mitigation: shrinkage estimator (Ledoit-Wolf 2004) plus
weekly re-estimation.

---

## F3 — Hierarchical Risk Parity (HRP)

**Setting.** Same as F2, but ***Σ̂*** has clusters of correlated
agents (e.g., two trend-following agents).

**López de Prado (2016) procedure.**

1. Cluster agents via single-linkage on the correlation-distance matrix
   *d*ᵢⱼ = √(½(1 − ρᵢⱼ)).
2. Quasi-diagonalise ***Σ̂***: reorder rows / cols so similar agents
   are adjacent.
3. **Recursive bisection:** split the sorted list in half; allocate
   between the two halves inversely to within-half variance; recurse.

**Why we use it as the v0 default.**
- No matrix inversion → no blow-up when two agents are nearly
  duplicated.
- Cluster-aware → if we ever add agent #11 = "zone fade v2" that is
  90 % correlated with agent #1, they share a slot in the allocator
  instead of doubling our zone-fade exposure.
- Outperforms classical risk parity out-of-sample in LdP's tests
  (and others have since replicated).

**Failure mode.** Single-linkage clustering can be unstable to outliers;
average-linkage is a robustness-tested alternative.

---

## F4 — Kelly fraction as a position-sizing cap

**Setting.** Agent *i* has a Bernoulli-ish outcome distribution with
win rate *p*, gross win *b*, gross loss 1 (units of R). The Kelly
fraction is the bet size that maximises expected log-wealth.

**Discrete Kelly (Kelly 1956, Thorp 1969):**

> *f**ᵢ* = *p* − (1 − *p*)/*b*

**Continuous Kelly (returns):**

> *f**ᵢ* = μᵢ / σᵢ²

**Why we use it.** As a **cap**, not a target. The full-Kelly bet
maximises growth but has wild drawdowns; even "half Kelly" has 25 %
drawdowns regularly. Risk conductor uses `fractional_kelly ×
edge_estimate` as an upper bound — never as the realised size.

**Failure mode.** Estimating *p* and *b* from small samples gives
hilariously over-confident Kellys; LdP / Thorp both warn that ¼ to ½
Kelly is the operating range. **Setting:** the conductor caps any
agent at ⅓ Kelly of its trailing 90-trade realised distribution, or
1 % equity, whichever is smaller.

This formula is what would have refused the trader's 0.6-lot basket
on a $72 account: trailing realised Kelly on a 1-trade demo sample is
arbitrarily small, → cap is the floor → 0.01 lot total → broker minimum
not met → "account too small for this strategy, refusing trade." That
is exactly the C/L6 behaviour we are designing for.

---

## F5 — Probability of Backtest Overfitting (PBO)

**Setting.** We will test K different ensemble configurations on the
same sealed window. With K ≥ 5 this is statistically dangerous
(López de Prado 2014).

**PBO procedure (informal).** Split sealed data into pairs of folds.
For each pair, find the *in-sample best* configuration; check its
*out-of-sample rank* on the other fold. PBO = the fraction of pairs
where the in-sample winner ranked in the bottom half OOS.

**Why we use it.** It is the cleanest published guard against "we
tried 50 ensembles and one happened to look good on sealed H1."
Charter gate C5 requires PBO ≤ 0.5.

**Failure mode.** PBO assumes IID-ish samples within folds; FX H4
has autocorrelation. Mitigation: use *block* fold splits, not
random shuffles.

---

## F6 — Deflated Sharpe Ratio (DSR)

**Setting.** Reported Sharpe on the winning ensemble across K trials.

**Bailey & López de Prado (2014):**

> DSR(SR̂) = Z⁻¹ [ Φ((SR̂ − SR₀) × √(n − 1) / √(1 − γ₃ SR̂ + ((γ₄ − 1)/4) SR̂²) ) ]

where SR₀ = expected max Sharpe under the null across K trials
(closed form in the paper), γ₃ and γ₄ are skew/kurtosis of returns,
n is the sample size.

**Why we use it.** Selection bias inflates Sharpe in proportion to
how many ensembles we tested. DSR adjusts for this. Required at
agent-eligibility gate (an agent enters the roster only if its
realised DSR > 0 on holdout).

**Failure mode.** Needs reasonable n; for low-trade-count agents
(daily timeframe), DSR has huge variance. Mitigation: also require a
minimum n_trades (≥ 30) before promotion.

---

## F7 — VPIN (Volume-synchronized Probability of Informed Trading)

**Setting.** A regime feature, *not* an allocator weight. Easley,
López de Prado, O'Hara (2012) define VPIN as the order-imbalance
toxicity over volume-equal time buckets.

**Use here.** As an input to per-agent `regime_fit`. A momentum
agent should see VPIN spikes as a regime that suits it (high
informed-flow imbalance → directional persistence); a mean-revert
agent should see it as a regime that hurts it.

**Failure mode.** FX volume is broker-specific and incomplete.
Mitigation: use *transaction count* per fixed time bucket on H1 as a
volume proxy.

---

## F8 — Softmax gating with load-balance penalty

**Setting.** If we later (Φ4+) want a *learned* allocator, this is the
form. Given regime feature vector ***x***, gate weights are:

> *g*ᵢ(***x***) = softmax(***W***ᵢ × ***x*** + bᵢ)

With a load-balance auxiliary loss (Shazeer 2017):

> L_aux = α × CV(load)² + β × CV(importance)²

where *load* is the gate's per-batch weight on each agent and
*importance* is the gradient flow.

**Why we use it (eventually).** It gives a differentiable, learnable
allocator. Without the auxiliary loss the gate **collapses** — one
agent wins every input and the rest atrophy. The aux loss prevents
that.

**Failure mode.** Over-fit to in-sample regimes. Will sit behind a
PBO gate before any use.

---

## F9 — Stacking (Wolpert 1992)

**Setting.** A meta-learner *m* takes base-learner outputs as its
input features:

> ŷ = *m*( *x*₁, *x*₂, ..., *xₙ* )

**Use here.** Optional Φ4+. The meta-learner consumes agent
proposals (feature_vector + conviction + direction one-hot) and
outputs a decision. The current aggregator + allocator is a
*hand-coded m*; stacking would learn *m* from data.

**Failure mode.** Doubles the overfit risk because we're now
training on agent outputs that were themselves trained.  Mitigation:
strict out-of-fold (OOF) training and PBO/DSR on the meta-learner
too.

---

## F10 — Sharpe-weighted ensemble (Yang et al. 2020)

**Setting.** A simple, *empirical-prior* fusion baseline. Each
agent's weight at time *t* is:

> *w*ᵢ(t) = max(0, Sharpeᵢ over trailing window) / Σⱼ max(0, Sharpeⱼ
> over trailing window)

(Negative-Sharpe agents get zeroed; renormalise.)

**Why we use it.** It is the cleanest published precedent for
multi-agent trading ensembles. Beats equal weight in Yang's experiments
on stocks. F2/F3 likely beat F10 but F10 is the *baseline* we must
beat.

**Failure mode.** Trailing Sharpe is noisy on small samples; agents
get whip-sawed between zero and full weight. Mitigation: shrinkage
toward equal weight + minimum window of 60 trades.

---

## F11 — Independent-OR confluence conviction (chemical reaction)

**Setting.** N agents' coordinates (`Coordinate` dataclass per
doctrine §3.2) overlap on the same symbol per F13. Each agent has
emitted its own conviction *cᵢ ∈ [0, 1]* and carries a fixed ego
*eᵢ ∈ [0, 1]*. We need a combined conviction for the chemical
reaction event.

**Formula (independent-OR with ego-weighted credit):**

> *c_combined* = 1 − ∏ᵢ (1 − *cᵢ* × *eᵢ*)

**Properties.**
- Two 0.5-conviction agents at full ego → 0.75. Three → 0.875.
- Multiplicative non-linearity matches the doctrine: a chemical
  reaction is *not* the additive sum of two ordinary shots; it is a
  qualitatively different event with a higher conviction floor than
  any single shot.
- Caps at 1 monotonically; cannot exceed any individual agent's
  ceiling without a peer also agreeing.

**Trade size lift.** Used in tandem (doctrine §3.3):

> *size_multiplier* = 1 + 0.5 × log₂(*N*), capped at 2.5×

| Agents | Combined conviction (eᵢ=1, cᵢ=0.5) | Size multiplier |
|---|---|---|
| 1 | 0.50 | 1.00× |
| 2 | 0.75 | 1.50× |
| 3 | 0.875 | 1.79× |
| 4 | 0.9375 | 2.00× |
| 6 | 0.984 | 2.29× |
| ≥ 8 | → 1 | 2.5× (capped) |

**Why we use it.** Late-fusion ensembles need a confidence rule for
disagreement-vs-agreement. Bayesian product-of-independent-evidence
(naïve Bayes for binary detection) is the closest classical
analogue and gives exactly this form. Ego-weighting is novel here
(maps to "not all peers' agreement counts equally — the egoist's
agreement counts more").

**Failure mode.** Assumes agents are *independent* — if A1 and A5
(Reo, the chameleon) co-vary because Reo *copies* A1, treating them
as independent double-counts the same evidence. **Mitigation:** the
HRP allocator (F3) already clusters correlated agents; the
chemical-reaction detector multiplies down by `(1 − ρᵢⱼ)` for
cluster-mates and aborts the reaction entirely if any pair has
ρ > 0.85.

**Decision.** F11 is the conviction rule for the aggregator's
chemical-reaction branch. Equal-weight conviction (mean of *cᵢ*) is
the simpler baseline kept for ablation in Φ4.

**Closes constraints.** L8 (fusion not elimination — disagreeing
voices can still produce a confluent trade with stronger combined
evidence than any single voice).

---

## F12 — Trade Quality Score (TQS)

**Setting.** Per-trade *fitness function*. Used by the allocator
(F3 / "devour" reweighting), by Population-Based Training (Φ5+),
and by the adversarial benchmark vs the human (F14). Replaces raw
P&L as the primary objective.

**Formula:**

> *TQS* = *R*^0.7 × *efficiency* × *time_score* × *cleanliness*
> × *beauty_bonus*

with components:

| Component | Definition | Range |
|---|---|---|
| *R* | max(0, realised R-multiple of the closed trade) | [0, ∞) |
| *efficiency* | max(0, 1 − MAE_pips / max(MFE_pips, 1)) | [0, 1] |
| *time_score* | exp(−(*Δt* − *Δt*\*)² / (2 × *Δt*\*²)) where *Δt* = actual hold, *Δt*\* = agent's target hold | [0, 1] |
| *cleanliness* | 1.0 if no adds + no panic exit + broker-stop never threatened, else 0.7 | {0.7, 1.0} |
| *beauty_bonus* | 1.2 if entry was inside a chemical-reaction coordinate, else 1.0 | {1.0, 1.2} |

**Interpretation of components.**
- *R*^0.7 is concave in R — diminishing returns to ever-larger wins.
  Discourages "lottery ticket" agents that hold dead-money positions
  hoping for a 10R outlier.
- *efficiency* penalises agents that need a lot of room to make
  their R. A trade that ran 30p MAE to make 30p is half the quality
  of one that ran 5p MAE to make 30p.
- *time_score* is a Gaussian centred at each agent's *target* hold
  (Bachira's target may be 4 hours; Barou's may be 4 days). Holding
  too long *or* too short hurts.
- *cleanliness* punishes the failure modes that wrecked the live
  account on 2026-06-19 (adds-into-winners, panic exits).
- *beauty_bonus* rewards confluence participation explicitly so
  agents have incentive to align with the chemical-reaction
  detector, not work around it.

**Properties.**
- Losing trades score **0**, not negative. Punishment for losses is
  the Risk Conductor's job (separate layer); TQS rewards quality.
  Aligns with the doctrine: in Blue Lock, ugly-loss is just no-goal,
  not a deduction.
- Bounded above by *R*^0.7 × 1 × 1 × 1.0 × 1.2; for typical R = 2 a
  perfect-quality trade scores ≈ 1.84. Multi-R + confluence can push
  TQS into the 5–10 range.

**Why we use it.** Sharpe (F6 deflated) measures portfolio-level
risk-adjusted return. TQS measures *per-trade quality*. Agents
within the ensemble are evaluated and reweighted on TQS distribution
(median + IQR); the portfolio is evaluated on Sharpe / max-DD. Both
scales coexist.

**Failure mode.** Composite scores can be gamed — an agent that
optimises one component (e.g., always closes at exactly *Δt*\* to
maximise *time_score*) may sacrifice the others. **Mitigation:**
report the *vector* of components per trade in the journal; flag
agents whose component-distribution skews to a single dominant
factor.

**Decision.** TQS is the per-trade fitness used by F3-with-devour
(doctrine §3.4). Validated against simple Sharpe-weighted (F10) in
the Φ4 fusion sweep.

**Closes constraints.** Doctrine commitment 2 (TQS not raw P&L is
the fitness function) + parts of L1 (executions of the same view
diverge in quality, not just P&L).

---

## F13 — Coordinate overlap measure

**Setting.** Two `Coordinate` instances *Cᵢ* and *Cⱼ* (per doctrine
§3.2) need a binary "do they react?" answer plus a continuous
overlap score for ranking confluences when many fire at once.

**Binary predicate.** Coordinates *Cᵢ*, *Cⱼ* react iff **all** hold:

1. *Cᵢ.symbol* = *Cⱼ.symbol*.
2. Price-band overlap fraction ≥ 0.5 of the smaller band:
   *price_overlap* = max(0, min(*hi*ᵢ, *hi*ⱼ) − max(*lo*ᵢ, *lo*ⱼ));
   width-min = min(*hi*ᵢ − *lo*ᵢ, *hi*ⱼ − *lo*ⱼ);
   require *price_overlap / width_min* ≥ 0.5.
3. Time-window overlap ≥ 1 H4 bar (4 h).
4. Vol-band intersection non-empty.
5. *direction_bias*ᵢ compatible with *direction_bias*ⱼ (same, or
   either is "either").
6. *regime_predicate* not contradictory.

**Continuous overlap score** (geometric mean — co-equal weighting
of the three numeric dimensions; fails to zero if any dimension
fails):

> *overlap_score* =
> (*price_overlap_frac* × *time_overlap_frac* × *vol_overlap_frac*)^(1/3)

with each fraction normalised to the smaller of the two bands.

**Why we use it.** Geometric mean (vs arithmetic) penalises
asymmetric overlap — two coordinates that share 90 % price-band but
only 5 % time-window are *not* a strong reaction. Arithmetic mean
would call that a 47 % match; geometric calls it a 14 % match. The
canon supports geometric: a chemical reaction needs all dimensions
aligned, not some.

**Failure mode.** Agents with deliberately wide coordinates (e.g.,
Reo's "leader-mirror with 20 % wider band") will score artificially
high overlap with everyone. **Mitigation:** the binary predicate's
"≥ 0.5 of smaller band" rule is a hard floor that defeats a single
overly-wide agent dominating reactions. Reo's coordinates are also
flagged in the journal so reactions involving him are tagged
`reo_passive` and excluded from devour-bonus calculation.

**Decision.** F13 is the overlap rule for the chemical-reaction
detector in the Aggregator. Activates F11.

**Closes constraints.** Doctrine commitments 1 + 3 (Coordinate API +
chemical reactions detected and rewarded).

---

## F14 — Adversarial validation (human-vs-ensemble)

**Setting.** The user (the human discretionary trader) submits chart
analysis + actual demo / live trades each week. These become the
synthetic opponents Kaiser / Loki / Sae per doctrine §5. The
ensemble is benchmarked head-to-head over a rolling 12-week window.

**Three composite metrics.** Each computed over the trailing 12-week
window; the gate requires all three.

**M1 — PnL head-to-head (TQS-normalised):**

> *PnL_HH* = mean(*TQS_ensemble*) − mean(*TQS_human*)
>
> Gate: *PnL_HH* ≥ 0.

Apples-to-apples on the same charts, same capital basis ($100 /
1:1000 demo); compared on TQS not raw $ to control for size choices.

**M2 — Coverage (does the squad see what the human sees?):**

> *Coverage* = | *human_coords* ∩ {*c* ∈ *agent_coords* :
> overlap_score(*c*, *human_c*) ≥ 0.5} | / | *human_coords* |
>
> Gate: *Coverage* ≥ 0.6.

Tests Isagi specifically — does any agent claim a coordinate that
overlaps the human's? 60 % is the threshold for "the squad has the
read."

**M3 — Counter (do we sometimes win the *opposite* side?):**

> *Counter* = | { *human_trade* : ∃ agent took opposite side,
> agent_TQS > human_TQS } | / | *human_trades* |
>
> Reported, not gated. Healthy values 0.10 – 0.25 indicate
> productive adversarial diversity. ≥ 0.40 suggests the human is
> systematically wrong; ≤ 0.05 suggests the squad has been calibrated
> to the human's blind spots.

**Why we use it.** Standard backtests overfit to historical
distributions. A live human adversary keeps the squad honest in
ways no synthetic baseline can. AlphaStar's *league-exploiter*
agents are the closest published precedent (Vinyals 2019); the
human-as-league-exploiter framing is a deliberate translation.

**Failure mode — important.** If the human adversary is the
*only* benchmark, the squad converges to "agree with the human" —
useless. **Mitigation 1:** Sae Itoshi (the synthetic baseline =
buy-and-hold + frozen `zone_d1_against`) is also benchmarked
weekly. The squad must beat *both* humans and synthetic. **Mitigation
2:** require *Counter* ≥ 0.10 on the rolling window — the squad must
sometimes disagree productively.

**Decision.** F14 promoted to charter gate C6 (see updated
`00-charter.md`). Mandatory for live promotion.

**Closes constraints.** Doctrine commitment 5 (the human is the
opponent) + Q-doc-4 ambiguity (we benchmark on the demo equivalent
of the human's trades to keep capital identical).

---

## F15 — Devour bonus δ from TQS autocorrelation

**Setting.** The devour bonus in the doctrine §3.4 was introduced
with `δ = 0.25` as a placeholder. F15 derives it from the data
instead — the more autocorrelated the per-agent TQS series is across
weeks, the more we can trust the ranking to extrapolate, so the
harder we devour. Noisy TQS series → fall back toward equal weight.

**Formula:**

> *δ*ₜ = clip( mean over agents of corr( *TQS*ᵢ,[t−12, t−1] ,
> *TQS*ᵢ,[t−11, t] ), 0, 0.5 )

i.e. lag-1 autocorrelation of each agent's weekly TQS over the
trailing 12 weeks, averaged across the roster, clipped to `[0, 0.5]`.

**Setting / estimator.** Weekly recomputation. The mean-of-pairwise-
correlations is stabilised with **Ledoit-Wolf shrinkage toward zero**
(Ledoit-Wolf 2004) to control variance at small N — typical Φ3/Φ4
rosters have N = 5–10 agents.

**Why we use it.** The data tells us how much to trust the TQS
ranking. If agents' TQS is heavily autocorrelated week-to-week (high
δ), the leader-board is informative and devouring aggressively is
correct. If TQS is noisy week-to-week (low δ), the leader-board is
random and devouring would be allocating to noise.

**Failure mode.** Short windows give unstable δ. Mitigation: require
a 12-week minimum trailing window before F15 is used; until then,
fall back to the placeholder `δ = 0.25`. Ledoit-Wolf shrinkage gives
a further variance floor.

**Decision.** Φ4 ships F15 live, with a 6-point cross-validation
sweep `δ ∈ {0.0, 0.1, 0.2, 0.3, 0.4, 0.5}` as a cross-check. If the
sweep optimum is within ±0.05 of F15's running value, keep F15 live;
otherwise treat the divergence as a research finding (the TQS
autocorrelation is either misleading or the sweep is overfitting).

**Closes constraints.** Doctrine commitment 4 (devour is
competitive) — closes the previously-arbitrary δ choice flagged in
Q-doc-3.

---

## F16 — Sae composite baseline

**Setting.** The charter's adversarial gate C6 requires beating a
synthetic baseline ("Sae Itoshi") on TQS. v0 placeholder Sae was
"buy-and-hold + frozen `zone_d1_against`" — a low bar. F16 replaces
that with a **competitive composite** that is true to the canon:
Sae's weapon is *complete soccer drawing from many disciplines*, so
the baseline draws from multiple validated alpha families.

**Formula:**

> *Sae*(t) =
> 0.35 × *CTA_trend*(t)
> + 0.25 × *Carry*(t)
> + 0.25 × *FinRL_PPO*(t)
> + 0.15 × *Frozen_zone_d1_against*(t)

**Setting / construction.** Equal-risk-contribution rebalanced
weekly on the same $100 / 1:1000 demo, running through the same Risk
Conductor + Sentinel as the squad. ERC weights are *targets*; the
0.35 / 0.25 / 0.25 / 0.15 numbers are starting allocations and are
re-derived weekly from the components' realised σ via F2 closed-form
(`wᵢ ∝ 1/σᵢ`).

**Sub-component details:**

- **CTA_trend.** Donchian channel breakout (20-bar entry, 10-bar
  exit) + ATR-vol-targeted sizing on D1. The trend-following
  industry baseline.
- **Carry.** Long the highest-yielder, short the lowest-yielder
  within the squad's symbol universe (EUR/GBP/USDCAD). Menkhoff,
  Sarno, Schmeling, Schrimpf (2012) is the canonical reference.
- **FinRL_PPO.** Open-source FinRL PPO agent (Liu 2021) trained on
  2015–2025 H1 data with frozen weights for the evaluation window.
  Represents "an off-the-shelf modern RL competitor".
- **Frozen_zone_d1_against.** The existing strategy run with no
  improvements as the sanity floor. If the squad cannot beat *its
  own seed strategy*, the architecture has not earned its weight.

**Why we use it.** Sae's role in the canon is "the elder Itoshi who
set the standard of cold excellence." A frozen relic is not that; a
composite of validated alpha families is. F16 makes the synthetic
baseline genuinely hard to beat — beating it constitutes evidence
that the squad has multi-discipline edge, not just a clever fade.

**Failure mode — important.** If the squad beats Sae too easily
(`PnL_HH > +0.5` TQS units for 8 consecutive weeks), Sae *evolves*:
add a 5th component (candidates: orderbook-flow detector, news-
sentiment classifier, options-implied-vol skew). The doctrine
forbids letting the squad coast against a fixed adversary — the
opponent has to stay competitive, in canon and in code.

**Decision.** F16 is the C6 baseline that the squad must beat
weekly. ERC rebalanced; sub-components frozen for the evaluation
window; evolution clause documented above.

**Closes constraints.** C6 (adversarial gate) — replaces the v0
placeholder with a competitive composite. The original Sae bullet in
`05-agent-roster-v0.md` §5.3 should be read in light of F16.

---

## A note on what is *not* in this doc

- Anything market-microstructure-specific (order-flow imbalance, queue
  position) — belongs in agent-specific docs once we have feature
  detectors.
- Anything reward-shaping or RL-specific — Φ4+, after baselines are
  beaten by simple fusion.
- Anything regime-classification specific — will live in a future
  `regime/` sub-folder; in v0 each agent owns its own `regime_fit`.

---

## Cross-reference to constraints

| Constraint (from `01-…archive.md` §5) | Formula(s) that close it |
|---|---|
| L1 — same view, spread of outcomes | F4 (Kelly cap), F2/F3 (allocator) |
| L2 — single-strategy mis-positions for regime | F8 (gated allocator), F10 (Sharpe weight), `regime_fit` on every proposal |
| L3 — "two trades = one bet" | Aggregator rule + correlation matrix in F2/F3 |
| L4 — intra-bar entry beat H4-close | Agent-internal logic; not a formula but a roster constraint |
| L5 — patterns carry alpha | Roster includes a Pattern Trader agent |
| L6 — feasibility ≠ edge | F4 with empirical-Kelly floor refuses sub-minimum-lot trades |
| L7 — ladder must execute, not just journal | Architecture: every proposal carries a ladder, conductor executes |
| L8 — fusion not elimination | Aggregator rule 2 (opposing → journal veto), allocator floor (≥ 2 %), F11 (confluence-OR conviction lift) |

Doctrine-driven additions:

| Doctrine commitment (06-…doctrine §7) | Formula(s) / mechanism that close it |
|---|---|
| 1 — Coordinate API on every agent | F13 (overlap measure) + Coordinate dataclass |
| 2 — TQS not P&L is fitness | F12 (TQS) + F3 reweighting on TQS-vector |
| 3 — Chemical reactions detected and rewarded | F11 (independent-OR conviction) + F13 (overlap detection) + size_multiplier rule |
| 4 — Devour is competitive | F3 HRP + devour bonus *δ* derived by F15 (TQS autocorrelation, Ledoit-Wolf shrunk) + 2 % floor / 35 % cap |
| 5 — Human is the opponent | F14 (adversarial validation) → charter gate C6, with F16 (Sae composite) as the synthetic adversary the squad must also beat |
| 6 — Pitch shapes the squad | F4 (Kelly cap) refusing sub-minimum-lot trades on $100 / 1:1000 |

F15 closes the previously-arbitrary `δ = 0.25` placeholder flagged
in Q-doc-3 of `06-blue-lock-doctrine.md`. F16 closes the C6
adversarial gate by replacing the v0 frozen-relic Sae with a
genuinely competitive composite.

Every formula has a constraint it closes. Every constraint has at
least one formula or architectural element that closes it.
