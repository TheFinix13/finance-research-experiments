# 00 — Charter, Scope & Success Criteria

**Status:** `DRAFT v0.4` — 2026-06-24. v0.4 makes the §7 account
profile *operational*: §7.1 fixes the C1 promotion gate to a numeric
TQS bar against the **E004 deployed cell** (median +11.34 pips/trade,
7/7 OOS sign test, p ≈ 0.008, per `audits/2026-06-24_E001-E007_
audit.md` §2.4); §7.2 makes position sizing **discrete** (0.01,
0.02, … min-lot multiples, rounded down) instead of continuous; §7.3
points at the Sentinel hard rules R1–R5 in `06-blue-lock-doctrine.md`
§4.3 as pre-trade gates that override every agent's conviction. v0.3
landed the repo split into a research repo + production repo (G9),
inserted a Φ2.5 infrastructure + standards phase (G10,
`07-research-standards.md`), scoped the Φ3 MVP down to 5 components
(A1 Isagi, A4 Chigiri, A10 Kunigami, Sentinel, Sae), and added C7
(no retro-fit in adversarial benchmark). v0.2 added the Blue Lock
doctrine (`06-blue-lock-doctrine.md`) as the project's philosophical
spine, the 10-character roster (`05-agent-roster-v0.md`), TQS-driven
fitness (G7), the human-as-opponent benchmark (G8 / C6), and the new
$100 / 1:1000 demo account profile (§7).

## Mandate

Design, prototype, and quant-validate a multi-agent ensemble trading
system that replaces the current single-strategy gate-and-funnel
architecture with a **roster of specialist agents whose proposals are
combined via late fusion** at the decision layer.

The system targets the same instruments and timeframes as the current
production agent (EURUSD / GBPUSD / USDCAD on H4, with optional D1 and
intraday sub-agents) and is benchmarked against the current
`zone_d1_against` deployment on identical data.

## Problem statement

The single-strategy architecture has three structural weaknesses
exposed by the week of 2026-06-15:

1. **Regime dependency.** `zone_d1_against` is a counter-trend mean
   reverter. In a momentum / vol-breakout week (FOMC, June 17) it
   silently degrades. The system has no second voice that says "this
   week is a trend week, fade is wrong."
2. **Single-funnel elimination.** Successive validation tightening (BH-FDR,
   walk-forward, frozen cross-pair) discards strategies that work *in
   their regime* because they don't work everywhere. We lose conditional
   edge in pursuit of unconditional edge.
3. **No diversity of method.** Liquidity-zone reading, pattern triggers
   (H&S), volatility-event positioning, and zone fade are all legitimate
   alpha streams. The current code carries one. Real trading desks carry
   many and weight them.
4. **Single fitness function (P&L) hides ugly wins and clean losses.** A
   30-pip win that took 4 days, drew down 80 pips, and required two
   re-entries is not equivalent to a 30-pip win that took 6 hours,
   drew down 10 pips, and was clean. Quality of execution is alpha
   that raw P&L cannot see.

## Goals (in priority order)

1. **G1 — Specialist isolation.** Each agent in the roster encapsulates
   one strategy / mindset, with its own signal logic, sizing rule, stop
   rule, target ladder, and confidence score. No agent depends on any
   other's internals.
2. **G2 — Late fusion at the decision layer.** Combine agent proposals
   into final orders through an explicit fusion mechanism (allocator +
   aggregator + risk conductor). Fusion choices are configurable and
   testable in isolation.
3. **G3 — Regime-aware capital allocation.** Capital allocator can shift
   weight toward agents whose recent regime fit is high, without
   eliminating agents whose fit is currently low.
4. **G4 — Correlation-aware risk.** The system treats EUR/USD and GBP/USD
   shorts as one USD-long exposure, not two trades, and sizes the basket
   not the lines.
5. **G5 — Quant-validated.** Every fusion mechanism and every agent that
   joins the roster passes the same evidence bar as `zone_d1_against`
   (walk-forward + frozen holdout + sealed period), with PBO control on
   roster-selection.
6. **G6 — Same evidence ledger.** All experiments produce JSONL +
   summary docs in `docs/reviews/` so the audit trail matches the rest
   of the repo.
7. **G7 — TQS-driven evolution.** Agent ranking, capital reallocation,
   and Population-Based Training (Φ5+) are driven by the **Trade
   Quality Score** (F12 in `04-quant-foundations.md`), not raw P&L.
   Quality components — efficiency, time, cleanliness, beauty — are
   journalled per trade so we can audit which axis any agent is winning
   on.
8. **G8 — Adversarial benchmark.** The ensemble is benchmarked weekly
   against the user's own discretionary trades (mapped to the named
   opponents Kaiser / Loki / Sae per
   `06-blue-lock-doctrine.md` §5) using the head-to-head metrics in F14.
   Promotion requires beating the human on TQS over a rolling 12-week
   window with ≥ 60 % coordinate coverage.
9. **G9 — Repo split.** Research lives in
   `finance-research-experiments/programs/M001_multi_agent_ensemble`;
   only validated agents land in `multi-pair-trading-agent`.
10. **G10 — Standards.** Φ2.5 establishes data infrastructure, simulator
    scaffold, validation standards, and reproducibility manifests (see
    `07-research-standards.md`) before any Φ3 backtest runs.

## Non-goals

- **Not a rewrite of the live runner.** Live runner, broker layer, state
  store, monitor, vaults — all stay as-is until a separate promotion
  pass.
- **Not a discretionary copilot.** The system makes decisions
  autonomously. Human notes feed back via the journal, not via
  per-trade overrides.
- **Not multi-asset.** Stays on the same FX majors the current router
  ships with. Cross-asset is parked.
- **Not RL-first.** RL is *one* fusion mechanism we will study; we do
  not start there. Simple aggregation (vote, conviction-weighted, risk
  parity) ships first.

## Success criteria — gate to "promotion to a parallel live run"

The ensemble system enters a parallel live run on a *separate* demo
account (i.e. shadow trading, no capital decision) when **all** of the
following hold on the existing sealed 2026 H1 data:

- **C1 — Beat single-agent baseline (TQS-driven).** Ensemble median
  TQS ≥ zone-only baseline TQS × 1.10 (10 % uplift), *and* hit rate ≥
  baseline − 2 pp, *and* max drawdown ≤ baseline + 25 %. C1 is now
  driven by F12 (TQS) per G7, not raw pip count.
- **C2 — Roster contribution.** At least 3 of the agents in the final
  roster contribute non-trivially: each is the marginal-deciding agent
  on ≥ 5 % of taken trades, *and* no single agent is the marginal-decider
  on > 60 %.
- **C3 — Regime conditioning is real.** Capital weights shift
  measurably across at least two distinct regime windows (e.g. June
  pre-FOMC vs June post-FOMC), and the shift improves PnL vs frozen
  equal-weight on the held-out portion.
- **C4 — Correlation gate works.** When two agents propose same-direction
  trades on correlated pairs (|ρ| > 0.7 on the rolling 30 d H1 window),
  total deployed risk is capped by the basket-risk rule and the
  resulting drawdown distribution has a thinner left tail than the
  un-capped variant.
- **C5 — No backtest-overfit signature.** Probability of Backtest
  Overfitting (PBO, López de Prado 2014) on roster-selection ≤ 0.5.
- **C6 — Adversarial gate (human + synthetic).** Per F14 over a
  rolling 12-week window: PnL_HH ≥ 0 (mean ensemble TQS ≥ mean human
  TQS); Coverage ≥ 0.6 (≥ 60 % of human-claimed coordinates have at
  least one agent coordinate overlapping per F13); the synthetic Sae
  baseline is also beaten on TQS. Counter rate is reported but not
  gated. Per G8.
- **C7 — No retro-fit in adversarial benchmark.** Human proposals
  submitted after the H4 close of the relevant entry bar are discarded
  (per locked protocol in `07-research-standards.md` §6). Anything
  graded in C6 must satisfy C7 first.

Then — and only then — it joins live as a **shadow** runner with no
capital. Real-capital promotion requires a further 3 months of shadow
performance review.

## Kill conditions

This work is paused or terminated if any apply:

- **K1.** After the literature pass, no proposed fusion mechanism has
  been empirically validated by an independent published source in FX or
  futures live trading. (We are inventing, not building on prior art.)
- **K2.** A 4-agent ensemble cannot meet **all three** of C1's components
  on sealed 2026 H1.
- **K3.** Fusion code crosses ~ 500 LoC without producing a
  configuration that beats equal-weight voting.
- **K4.** Live `zone_d1_against` performance on demo improves to the
  point where the rationale for this overhaul no longer holds.

## Account profile (the pitch)

The R&D environment is intentionally constrained — see
`06-blue-lock-doctrine.md` §6 for the philosophy. In numbers:

| Field | Value |
|---|---|
| Starting equity | **$100 USD** (replaces the prior $1000 demo profile) |
| Leverage | **1:1000** (Exness demo) |
| Min lot | 0.01 (broker minimum) |
| Per-trade risk cap (sandbox-relaxed) | **5 % of equity** ($5 max stop loss per trade) |
| Per-correlated-basket risk cap | **7 % of equity** ($7 across same-direction USD pairs) |
| Margin level floor | **200 %** (4× safer than Exness 50 % stop-out) |
| Daily DD soft-flatten | 4 % of equity → flatten + 24 h cool-down |

Implications for agent design (full discussion in doctrine §6):
- Wide-stop H4 zone fades (Isagi v1) often refused by F4 Kelly cap on
  this small account; need confluence (F11 + F13) to size up.
- Tight-stop strategies (Bachira / Rin / Chigiri) mechanically fit
  better.
- Confluence-only agent (Nagi) becomes the highest-survival member.

The pitch is *intentionally* hostile to indiscriminate trading — it is
the stress test that proves which agents can play.

### §7.1 — C1 promotion gate is numeric

C1 ("Beat single-agent baseline") in the success-criteria table above
collapses to a **single numeric bar** against the E004 deployed cell:

> **Beat Sae by ≥ 10 % on TQS over the sealed 2026 H1 panel.**

Where "Sae" here means the E004-validated configuration —
`zone_d1_against / H4 / all sessions`, with `htf_align = D1`,
`htf_align_mode = against`, `htf_lookback = 10`,
`htf_min_move_pips = 60`, `target_rr = 1.5`. The reference numbers
that constitute the bar:

| Metric | E004 Sae baseline | Squad must clear |
|---|---|---|
| Median pips/trade | **+11.34** | n/a (TQS-based; pips reported for reference) |
| Trades per OOS window | ~66 | n/a |
| Sign-test (7 rolling 4-yr-IS / 1-yr-OOS windows) | **7/7 positive**, p ≈ 0.008 | n/a |
| Median **TQS** over sealed 2026 H1 panel | computed at C1 evaluation time | **≥ baseline × 1.10** |

Source for the baseline numbers: `audits/2026-06-24_E001-E007_
audit.md` §2.4 (E004 walk-forward, the cleanest single piece of
evidence in the pre-M001 lab). The TQS conversion uses F12 in
`04-quant-foundations.md`. C1 is **only** evaluated against this
baseline; the v0.1 placeholder language "baseline" without a
quantitative referent is superseded.

### §7.2 — Discrete position sizing under $100 / 1:1000

The pitch's mechanics:

- Minimum broker lot: **0.01**.
- EURUSD pip value at 0.01 lot: **≈ $0.10**.
- A 50-pip stop on 0.01 lot is therefore **≈ $5.00 ≈ 5 % of $100
  equity** — exactly at the R1 floor (`06-blue-lock-doctrine.md`
  §4.3).

Implications:

1. **Position sizes are discrete**, not continuous. The Capital
   Allocator (`03-architecture-v0-sketch.md` §4) emits HRP weights
   that imply *desired* fractional lots; the Sentinel rounds those
   fractions to the nearest min-lot multiple.
2. **Rounding direction is always "down"** (toward smaller risk).
   0.017 lot → 0.01, not 0.02. This is intentionally pessimistic
   on the small account.
3. **Position-sizing math is integer optimisation, not continuous
   optimisation.** The HRP weights become an *upper bound*; the
   actual size is the largest min-lot multiple that fits under
   every Sentinel rule simultaneously.
4. **Some agents will mechanically refuse trades** at this pitch
   because their realised SL distance × 0.01 lot exceeds 5 %
   equity (Sentinel R1). This is the doctrine §6 prediction made
   binding: wide-stop H4 zone fades (Isagi v1 standalone) are the
   primary refusal candidates; confluence (F11 + F13) is how they
   get sized back in.

The full mapping from HRP-weight → discrete-lot → Sentinel-block
decision lives in `sim/sentinel.py` (Φ3).

### §7.3 — Sentinel hard rules

The Sentinel sits between the Aggregator output and the Risk
Conductor's order ladder (architecture diagram, `03-architecture-
v0-sketch.md` §2). It is **not** an agent — it has no Coordinate,
no Proposal, no TQS — it is a deterministic pre-trade gate.

The five hard rules are defined in `06-blue-lock-doctrine.md` §4.3:

- **R1 — Min-lot risk floor.** Block trade if SL distance × 0.01
  lot > 5 % equity.
- **R2 — Discrete position sizing.** Round HRP weights down to
  nearest min-lot multiple.
- **R3 — Pass bias.** Most ticks, most agents emit observation-only
  Thoughts. Daily proposal-rate > 3 per agent triggers roster
  review.
- **R4 — Concentration cap.** No agent gets > 40 % of risk budget
  on any tick (hard backstop above HRP's 35 %).
- **R5 — Loss-streak dampener.** 3 consecutive losses → 50 % risk-
  scale × 24 h, applied to all agents.

R1–R5 are non-configurable and cannot be overridden by any agent's
conviction or by the Allocator. They are the floor below which "the
squad is allowed to play" stops being true.

## Phases (intended cadence)

| # | Phase | Deliverables | Gate before next phase |
|---|---|---|---|
| Φ0 | Charter + archive + literature plan | `00`–`02` docs in this folder | User review |
| Φ1 | Literature pass + foundations | `04-quant-foundations.md` filled, ≥ 10 papers / chapters consumed, formulas extracted | Foundations doc reviewed |
| Φ2 | Architecture v0 + roster v0 | `03`, `05`. End state: 5 specialist agent specs written, fusion API drafted | Architecture review |
| Φ2.5 | Infrastructure + standards | `07-research-standards.md`, multi-agent simulator scaffold (`sim/`), data manifest for M1/M5/M15/H1/H4/D1 on EUR/GBP/USDCAD, MLflow experiment tracker stood up, null-baseline suite scaffolded | Standards doc reviewed; tracker live; data manifest verifiable |
| Φ3 | Offline prototype | `sim/` runs each agent in isolation against sealed data; allocator + aggregator combine; metrics emit. **MVP scope: 5 components only — A1 Isagi, A4 Chigiri, A10 Kunigami, Sentinel, Sae.** A2/A3/A5/A6/A7/A8/A9 deferred to Φ4+. | Prototype produces a backtest |
| Φ4 | Roster selection + fusion sweep | Multiple ensembles tested. PBO control. Φ4 sweep compares **TQS-weighted (F12) vs Sharpe-weighted (F10) vs equal-weight** allocators. Selected ensemble passes C1–C6 | Promotion gate |
| Φ5 | Shadow live | Parallel-run shadow tickets. No capital. Daily eval. | 3-month shadow review |
| Φ6 | Capital promotion | Real demo capital allocated. Production router updated. | n/a |

We are at start of Φ0.
