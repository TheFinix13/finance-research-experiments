# 02 — Literature Survey Plan

**Status:** `DRAFT v0.3` — 2026-06-24. v0.3 adds the carry and FinRL
references behind the Sae composite (F16) and adds F15 + F16 to the
formula table. v0.2 added §1.6 (PBT / self-play / diversity-driven
MARL) and F11–F14 to support the doctrine in
`06-blue-lock-doctrine.md`.

Goal: a defensible, source-cited foundation for every architectural
decision in `03-architecture-v0-sketch.md` and every formula in
`04-quant-foundations.md`. We are *not* inventing fusion mechanisms;
we are picking from validated prior art and adapting to FX.

This is the **plan**, not the survey itself. Survey output will land
in `02b-literature-survey.md` after Φ1 completes.

## 1. The five intellectual lineages to draw from

### 1.1 Forecast combination (classical statistics)

The oldest body of work. Asks: "given K forecasts of the same target,
what is the optimal combination?"

- **Bates & Granger (1969)** — *The Combination of Forecasts.*
  Foundational; minimum-variance combination formula. Even one paragraph
  is enough.
  Formula to extract: optimal combination weights given forecast
  covariance matrix.
- **Granger & Ramanathan (1984)** — regression-based forecast
  combination. Adds bias-correction.
- **Timmermann (2006)** — *Forecast Combinations* (Handbook of Economic
  Forecasting). Survey-of-surveys; covers simple average vs optimal
  weights vs shrinkage.
- **Stock & Watson (2004)** — empirical: simple average often beats
  optimal weights estimated on noisy in-sample data. *Robustness
  argument for equal-weight defaults.*

What we extract:
- The formula `w* = (1ᵀ Σ⁻¹ 1)⁻¹ Σ⁻¹ 1` for variance-minimising
  weights given covariance Σ between agents.
- The "forecast-combination puzzle" — why simple average is often
  uncrushable.

### 1.2 Ensemble methods (machine learning)

How ML combines weak learners into strong predictors.

- **Breiman (1996)** — *Bagging Predictors.* Variance reduction by
  bootstrap aggregation.
- **Freund & Schapire (1997)** — *AdaBoost.* Sequential reweighting of
  the same hypothesis class.
- **Wolpert (1992)** — *Stacked Generalization.* A meta-learner over
  base learners. **Directly applicable** to our late-fusion design.
- **Dietterich (2000)** — *Ensemble Methods in Machine Learning* (survey).
- **Caruana et al. (2004)** — *Ensemble Selection from Libraries of
  Models.* How to greedily build an ensemble from a pool.

What we extract:
- The mental model: roster of agents = ensemble of weak learners; the
  fusion mechanism = stacking / voting / weighted-average.
- Practical: greedy forward selection for roster composition.

### 1.3 Mixture of Experts (gating networks)

How to route inputs to specialists depending on context.

- **Jacobs, Jordan, Nowlan, Hinton (1991)** — *Adaptive Mixtures of
  Local Experts.* Original gating-network paper.
- **Shazeer et al. (2017)** — *Outrageously Large Neural Networks: The
  Sparsely-Gated Mixture-of-Experts Layer.* Modern revival;
  load-balancing tricks. Lessons even if we don't use neural gates.
- **Fedus, Zoph & Shazeer (2022)** — *Switch Transformers.* MoE
  scaling; routing collapse failure mode is important to understand.

What we extract:
- The gating-network pattern: a small model takes context (regime
  features) and outputs weights over agents.
- The "routing-collapse" failure mode: one expert wins every input,
  others starve. Must include a load-balance / minimum-weight floor.

### 1.4 Portfolio theory & risk parity (quant finance)

How to combine *capital* (not just signals) across a set of return
streams.

- **Markowitz (1952)** — mean-variance optimisation. The original.
- **Black & Litterman (1992)** — adds views to MV; shrinks toward
  market equilibrium. Useful if we want to combine model views with a
  prior.
- **Maillard, Roncalli, Teïletche (2010)** — *The Properties of
  Equally Weighted Risk Contribution Portfolios.* Risk parity formal.
- **Roncalli (2013)** — *Introduction to Risk Parity and Budgeting*
  (book). Definitive practical treatment.
- **Lopez de Prado (2016)** — *Building Diversified Portfolios that
  Outperform Out of Sample.* Hierarchical Risk Parity (HRP); avoids
  matrix inversion which is the achilles heel of MV.
- **Menkhoff, Sarno, Schmeling, Schrimpf (2012)** — *Carry Trades and
  Global Foreign Exchange Volatility.* The canonical reference for
  the long-high-yield / short-low-yield carry component of the Sae
  composite baseline (F16 in `04-quant-foundations.md`). Also cited
  in §2 for the macro / vol-regime agent; F16 use is the primary
  reason it appears in §1.4 here.

What we extract:
- Risk-parity weights for the capital allocator: each agent
  contributes equal *risk*, not equal *capital*.
- HRP clustering approach for handling correlated agents (e.g. two
  trend agents) without exploding the covariance estimate.
- Roncalli (2013) ERC additionally underwrites F15's Ledoit-Wolf
  shrinkage choice for the TQS-autocorrelation devour bonus.

### 1.5 RL & multi-agent systems for trading

How recent work uses learned policies, sometimes plural, for trading.

- **Yang et al. (2020)** — *Deep Reinforcement Learning for Automated
  Stock Trading: An Ensemble Strategy.* Explicit ensemble of PPO, A2C,
  DDPG with Sharpe-weighted selection. **Closest published prior art
  to what we want to build.**
- **Liu et al. (2021, 2022)** — *FinRL / FinRL-Meta.* Open-source
  multi-strategy RL framework. Worth surveying for engineering
  patterns even if we don't adopt the framework wholesale. **Primary
  reference for the PPO component of the Sae composite (F16):** the
  FinRL_PPO column of F16 uses an open-source FinRL PPO agent
  trained on 2015–2025 H1 data with frozen weights as the off-the-
  shelf RL competitor inside the synthetic baseline.
- **Théate & Ernst (2021)** — *An Application of Deep Reinforcement
  Learning to Algorithmic Trading.* Honest about the overfit risk.
- **Wang et al. (2021)** — *AlphaPortfolio.* RL for portfolio
  weighting, with sparse attention over assets.
- **Vinyals et al. (2019)** — *AlphaStar.* Population-based training
  (PBT) and exploiter agents — not finance, but the *PBT pattern* maps
  cleanly to "many strategies, periodic culling, periodic introduction."
- **Foerster et al. (2018+)** — multi-agent learning surveys; CTDE
  (centralised training, decentralised execution).

What we extract:
- Ensemble-of-RL-policies as one fusion mechanism candidate.
- PBT-style roster management as a long-horizon evolution mechanism.
- Honest reading: most published trading-RL has weak out-of-sample
  validation. We will not adopt their hyperparameters; we will adopt
  their architecture *patterns* and re-validate on our own data with
  our own evidence bar.

### 1.6 Population-Based Training, Self-Play, and Diversity-Driven MARL

This is the lineage that makes the Blue Lock doctrine
(`06-blue-lock-doctrine.md`) operational rather than aesthetic. The
"ego, weapon, chemical reaction, devour" framing maps directly to
formal patterns in this body of work.

- **Jaderberg et al. (2017)** — *Population Based Training of Neural
  Networks.* The PBT pattern: maintain a population, periodically
  *exploit* (copy weights from a better agent) and *explore*
  (perturb hyperparameters). Directly underwrites the **Awakening**
  mechanism (doctrine §1.1). Φ5+.
  *We borrow:* the exploit-and-explore loop and the asynchronous
  population update schedule.
  *Failure mode:* bad exploit triggers (e.g. naive Sharpe ranking) cause
  population collapse to a single ancestor. Mitigation = TQS (F12)
  with cluster-aware ranking.

- **Vinyals et al. (2019)** — *Grandmaster level in StarCraft II
  using multi-agent reinforcement learning* (AlphaStar). The
  league-training architecture: **main agents** + **main exploiters**
  (whose only job is to beat main agents) + **league exploiters**
  (whose job is to find population-wide weaknesses). **The single
  closest published precedent for our cast + opponents framing.**
  *We borrow:* the three-tier league structure (strikers / Sae
  baseline / Kaiser-and-Loki human exploiters) and prioritised
  fictitious self-play.
  *Failure mode:* exploiter agents game cosmetic weaknesses. Mitigation
  = require Coverage ≥ 0.6 AND PnL_HH ≥ 0 in F14, not either-or.

- **OpenAI (Baker et al. 2019)** — *Emergent Tool Use From
  Multi-Agent Autocurricula* ("Hide and Seek"). Six emergent
  strategies arose from competitive self-play that none of the agents
  was explicitly designed for. Justifies the "let the squad evolve"
  philosophy of devour and chemical reaction.
  *We borrow:* the autocurriculum framing — opponents *should* push
  the squad into novel strategies the engineers didn't anticipate.
  *Failure mode:* emergent strategies can be reward-hack-shaped. Mitigation
  = Risk Conductor's hard SL invariant constrains the action space.

- **Berner et al. (2019)** — *Dota 2 with Large Scale Deep
  Reinforcement Learning* (OpenAI Five). Cooperative MARL at scale;
  team-of-five with shared objective. Less directly applicable than
  AlphaStar but useful for the *coordination patterns* in chemical
  reactions.
  *We borrow:* the "team-spirit" parameter that interpolates between
  individual and team reward — same idea as our ego coefficient but
  inverted (Blue Lock prefers *individual* tilt).
  *Failure mode:* OpenAI Five's coordination collapsed when one
  agent's policy diverged. Mitigation = HRP cluster-aware allocation.

- **Pathak et al. (2017)** — *Curiosity-driven Exploration by
  Self-Supervised Prediction.* Intrinsic motivation as a separate
  reward channel; the agent rewards *itself* for novelty.
  *We borrow:* the intrinsic-reward formulation. Each agent's
  training objective in Φ5+ is `TQS_i + ego_i × (TQS_i −
  mean(TQS_others))` — the second term is an explicit "I want to be
  different from the team mean" intrinsic reward.
  *Failure mode:* curiosity rewards can dominate task rewards. Mitigation
  = ego cap at 1.0 and the *primary* reward is still TQS.

- **Burda et al. (2018)** — *Exploration by Random Network
  Distillation.* Practical, scalable intrinsic-reward formulation.
  More tractable than Pathak's ICM in our setting.
  *We borrow:* the network-distillation trick if Φ5+ uses neural
  policies; otherwise we synthesise the same effect with the ego
  coefficient.

- **Eysenbach et al. (2018)** — *Diversity is All You Need (DIAYN).*
  Trains a population of skills with explicit *diversity reward* (do
  something distinguishable from your peers). Maps cleanly to the
  weapon framing — each agent has a different weapon by *design*,
  but DIAYN gives us the formal objective to *enforce* it under
  PBT.
  *We borrow:* the diversity-reward formulation as a regulariser on
  PBT-driven hyperparameter drift. Stops every agent from converging
  to the same strategy when one agent is winning.
  *Failure mode:* diversity for its own sake produces noisy weak
  agents. Mitigation = diversity reward gated on minimum TQS floor.

- **Lowe et al. (2017)** — *Multi-Agent Actor-Critic for Mixed
  Cooperative-Competitive Environments* (MADDPG). Formal MARL
  setting with continuous action spaces; centralised training,
  decentralised execution.
  *We borrow:* CTDE pattern — agents act on local market state at
  inference time; the allocator/aggregator (centralised) trains on
  joint outcomes.
  *Failure mode:* MADDPG is sample-inefficient. Mitigation = the v0
  agents are rule-based; learning is Φ5+ only.

- **Foerster et al. (2018)** — *Counterfactual Multi-Agent Policy
  Gradients* (COMA). Solves the MARL credit-assignment problem: who
  in the team caused the win? Critical for our **devour** mechanism
  — we cannot reweight toward winners if we cannot identify them.
  *We borrow:* the counterfactual baseline — for each closed trade,
  we compute "what would TQS have been if agent *i* had abstained?"
  and credit *i* the difference. Implementable since our aggregator
  is deterministic.
  *Failure mode:* counterfactual estimates have high variance with
  small N. Mitigation = devour cycle is weekly, ≥ 30 trades minimum.

- **Sukhbaatar et al. (2017)** — *Intrinsic Motivation and Automatic
  Curricula via Asymmetric Self-Play.* A learner-vs-adversary setup
  where the adversary proposes tasks of growing difficulty.
  *We borrow:* the asymmetric framing. The human (Kaiser/Loki) is
  the learner-vs-adversary asymmetry — the human is the
  *opponent*, not a peer; the squad must *catch up*.
  *Failure mode:* if the adversary's tasks become too easy, the
  learner stops growing. Mitigation = three-tier opponent
  (Kaiser/Loki/Sae); when the squad beats one, the next tier
  remains.

What we extract from §1.6 collectively:
- **The squad architecture is AlphaStar's league**, with strikers
  as main agents, Sae as the synthetic baseline exploiter, Kaiser
  and Loki as human league exploiters.
- **Awakening = PBT** (Jaderberg) with TQS-driven exploit and
  hyperparameter-perturbation explore. Diversity-regularised
  (Eysenbach) so the squad doesn't collapse to one ancestor.
- **Ego = intrinsic motivation** with population-relative reward
  (Pathak / Burda / Eysenbach combined).
- **Devour = COMA-style counterfactual credit assignment** (Foerster).
- **Adversarial = asymmetric self-play** (Sukhbaatar) with the human
  as the privileged opponent.

This is the *honest* answer to "is this design unprecedented?": every
component is borrowed; the *combination* applied to FX trading
ensembles with explicit Coordinate emission and TQS fitness is
novel here.

## 2. Domain-specific FX / microstructure references

The above is method. Below is domain.

- **Hasbrouck (2007)** — *Empirical Market Microstructure.* For
  understanding what "1h pattern break" really means in the order book.
- **Avellaneda & Stoikov (2008)** — market-making. Useful for any
  agent that thinks about spread / liquidity.
- **Easley, López de Prado, O'Hara (2012)** — *Flow Toxicity and
  Liquidity in a High-Frequency World.* VPIN. Order-flow toxicity is
  one regime signal.
- **Menkhoff, Sarno, Schmeling, Schrimpf (2012)** — *Carry Trades and
  Global Foreign Exchange Volatility.* For the macro / vol-regime
  agent.
- **Lyons (2001)** — *The Microstructure Approach to Exchange Rates.*
  For order-flow framing in FX specifically.

## 3. The Smart-Money / Order-Flow tradition (what the trader's
analysis actually uses)

The trader's analyses (D1 liquidity zones, demand zones, H&S, "unfilled
liquidity") map to a body of practitioner work that is mostly outside
peer review. We treat it the same as we treat technical analysis: take
the operational definitions, codify them, and validate empirically.

- **ICT / Inner Circle Trader** material (Michael Huddleston) —
  operational definitions for fair-value gaps, order blocks, liquidity
  pools, market-structure-shifts. We will codify these as feature
  detectors and validate.
- **Steve Mauro / MMM (Market Maker Method)** — multi-timeframe accumu-
  lation / distribution framing.
- **Tom Williams — *Master the Markets*** — Volume Spread Analysis.
  Classical and well documented.

Practitioner methods that survive empirical validation will become
agents; those that don't will be archived.

## 4. Cross-cutting: avoiding backtest overfit

Anything we build will be over-fit to the sealed window unless we
explicitly control for it.

- **López de Prado (2014)** — *The Probability of Backtest Overfitting.*
  The PBO formula. Will be applied to roster-selection at gate C5.
- **Harvey, Liu, Zhu (2016)** — *… and the Cross-Section of Expected
  Returns.* Multiple-testing in finance. Reinforces conservative
  significance bars.
- **Bailey & López de Prado (2014)** — *The Deflated Sharpe Ratio.*
  Sharpe-adjusted for selection bias.

These are non-optional and will be referenced in the foundations doc.

## 5. Formulas to extract into `04-quant-foundations.md`

Numbered for later cross-reference:

| F# | Formula | Source | Role |
|---|---|---|---|
| F1 | Minimum-variance combination weights `w* = Σ⁻¹ 1 / (1ᵀ Σ⁻¹ 1)` | Bates-Granger 1969 | Allocator |
| F2 | Risk-parity weights (Maillard 2010) — `wᵢ × (Σw)ᵢ = wⱼ × (Σw)ⱼ` ∀ i,j | Maillard 2010 / Roncalli 2013 | Allocator |
| F3 | Hierarchical Risk Parity recursion | López de Prado 2016 | Allocator (correlated agents) |
| F4 | Kelly fraction `f* = μ / σ²` (continuous) / per-trade Kelly | Kelly 1956 / Thorp 1969 | Sizing cap (with safety fraction) |
| F5 | PBO probability formula | López de Prado 2014 | Roster-selection gate |
| F6 | Deflated Sharpe ratio | Bailey & LdP 2014 | Agent-eligibility gate |
| F7 | VPIN (flow toxicity) | Easley, LdP, O'Hara 2012 | Regime feature (vol agent) |
| F8 | Softmax gating with load-balance penalty | Shazeer 2017 | Gating-network design |
| F9 | Stacking meta-learner (per Wolpert 1992) | Wolpert 1992 | Optional advanced fusion |
| F10 | Sharpe-weighted ensemble (Yang 2020) | Yang 2020 | Simple baseline fusion |
| F11 | Independent-OR confluence conviction `1 − ∏(1 − cᵢ × eᵢ)` | Naïve Bayes / product-of-evidence (classical), ego-weighting novel | Aggregator chemical-reaction branch |
| F12 | Trade Quality Score `R^0.7 × eff × t × clean × beauty` | Composite, novel; component design draws on Bailey-LdP DSR philosophy | Per-trade fitness; allocator + PBT |
| F13 | Coordinate overlap (geometric mean of three fractions) | Novel; geometric-mean choice from Roncalli (2013) risk-budget asymmetry handling | Aggregator confluence detector |
| F14 | Adversarial validation (PnL_HH, Coverage, Counter) over rolling 12-week window | League-exploiter pattern (Vinyals 2019) + asymmetric self-play (Sukhbaatar 2017) | Charter gate C6 |
| F15 | Devour bonus δ from TQS autocorrelation, clipped to [0, 0.5], Ledoit-Wolf shrunk | Roncalli 2013 (ERC) + Ledoit-Wolf 2004 (shrinkage estimator) | Closes the previously-arbitrary δ = 0.25 in doctrine §3.4 |
| F16 | Sae composite = 0.35 CTA_trend + 0.25 Carry + 0.25 FinRL_PPO + 0.15 Frozen_zone_d1_against, ERC-rebalanced weekly | Roncalli 2013 (ERC), Menkhoff et al. 2012 (carry), Liu 2021 (FinRL PPO), in-house frozen seed | Charter gate C6 — the synthetic competitive baseline |

## 6. Reading order (intended)

Phase Φ1 is sized at ≈ 2 weeks of reading. Order matters because some
references presume others.

1. Stock & Watson (2004) — primes the "simple average is hard to beat"
   intuition.
2. Bates & Granger (1969) + Timmermann (2006) — combination formula.
3. Maillard, Roncalli, Teïletche (2010) + first three chapters of
   Roncalli (2013) — risk parity formal foundation.
4. López de Prado (2016) HRP — handles correlation between agents.
5. Lopez de Prado (2014) PBO + Bailey & LdP (2014) Deflated Sharpe —
   the overfit toolkit.
6. Wolpert (1992) Stacking + Caruana (2004) Ensemble Selection — the
   ML side of fusion.
7. Yang et al. (2020) ensemble RL trading — closest published
   precedent.
8. Jacobs et al. (1991) + Shazeer (2017) Sparse MoE — the gating
   network design and its failure modes.
9. Easley, LdP, O'Hara (2012) VPIN — one concrete regime feature.
10. Hasbrouck (2007) selected chapters — microstructure foundation for
    the intraday agents.
11. **Vinyals et al. (2019) AlphaStar** — league-exploiter
    architecture; the doctrine's structural backbone.
12. **Jaderberg et al. (2017) PBT** + **Eysenbach (2018) DIAYN** —
    Awakening + diversity regularisation.
13. **Pathak (2017)** + **Burda (2018)** — intrinsic-motivation /
    ego-as-reward.
14. **Foerster (2018) COMA** — counterfactual credit for the devour
    mechanism.
15. **Sukhbaatar (2017)** — asymmetric self-play for the human-as-
    opponent benchmark.
16. **Menkhoff, Sarno, Schmeling, Schrimpf (2012)** — the carry-trade
    reference for the Carry component of the Sae composite (F16).
    Read alongside Roncalli (2013) for the ERC rebalancing rule.
17. **Liu et al. (2021) FinRL** — engineering reference for the
    FinRL_PPO component of F16; we use the upstream PPO agent with
    frozen weights, not a re-trained variant.

Then a focused pass through the trader / smart-money practitioner
material to codify the level-detection logic (separate doc).

## 7. Output of Φ1

`02b-literature-survey.md` will contain, for each numbered reference:
- 2–4 sentence summary in our own words.
- The one formula / pattern we are borrowing.
- The one critique / failure mode flagged in subsequent literature.
- A pointer (page / section) so the trader can audit any claim.

We do not cite from memory. Every formula in `04-quant-foundations.md`
will be traceable back to a specific reference in `02b`.
