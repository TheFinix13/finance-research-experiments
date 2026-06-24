# 03 — Architecture v0 Sketch

**Status:** `DRAFT v0.1` — 2026-06-23. Pre-literature-pass.

> This is the *strawman* architecture. Every box on the diagram is
> open for revision after Φ1 (literature pass) and Φ4 (fusion sweep).
> Nothing here is committed.

## 1. Mental model

> **Blue Lock metaphor, formalised.** A football pitch has N players;
> each has a distinct style, ego, and field-of-view. A goal (= a
> profitable trade) emerges from their *interactions* — passing,
> deferring, overriding — within a coach's (= risk conductor's) system.
> No single player is the team. No coach plays the ball.

In ML terms this is **late fusion**: each specialist consumes the raw
market and emits a structured proposal; the fusion layer combines
proposals (not features) into final orders.

In ensemble-methods terms it is a **stacking architecture** — base
learners (the specialists) + a meta-learner / aggregator (the fusion
layer) — with the additional constraint that the meta-learner produces
*executable orders* rather than predictions.

## 2. Layered architecture (ASCII)

```
                       ┌──────────────────────────────────┐
                       │   MARKET FEED  (broker, candles, │
                       │   tick, calendar, news, regime)  │
                       └─────────────────┬────────────────┘
                                         │
              ┌──────────────────────────┴───────────────────────────┐
              │                  FEATURE FAN-OUT                     │
              │  (regime features, microstructure, structural lvls,  │
              │   pattern detectors, calendar tags, vol metrics)     │
              └──────────────────────────┬───────────────────────────┘
                                         │
   ┌───────────┬───────────┬─────────────┴─────────────┬─────────────┬───────────┐
   ▼           ▼           ▼                           ▼             ▼           ▼
┌──────┐  ┌──────┐  ┌──────────┐                 ┌──────────┐  ┌──────────┐  ┌──────────┐
│ A1   │  │ A2   │  │   A3     │       …         │   A8     │  │   A9     │  │  A10     │
│ zone │  │ break│  │ pattern  │                 │ liquidity│  │ vol-     │  │ carry /  │
│ fade │  │ -out │  │ trader   │                 │ sweep    │  │ event    │  │ macro    │
│ (MR) │  │ (MOM)│  │ (H&S/DT) │                 │ trader   │  │ trader   │  │ trader   │
└───┬──┘  └──┬───┘  └────┬─────┘                 └────┬─────┘  └────┬─────┘  └────┬─────┘
    │        │           │                            │             │             │
    └────────┴───────────┴─────────────┬──────────────┴─────────────┴─────────────┘
                                       ▼
                       ┌──────────────────────────────────┐
                       │       PROPOSAL BUS               │
                       │  (typed AgentProposal objects;   │
                       │   no agent reads another's prop) │
                       └─────────────────┬────────────────┘
                                         │
              ┌──────────────────────────┴───────────────────────────┐
              │              CAPITAL ALLOCATOR                       │
              │  inputs: account state, agent track record,          │
              │          regime fit, correlation matrix              │
              │  outputs: per-agent risk budget (in $-of-equity)     │
              │  default: risk-parity (HRP), gated to floor + cap    │
              └──────────────────────────┬───────────────────────────┘
                                         │
              ┌──────────────────────────┴───────────────────────────┐
              │              TRADE AGGREGATOR                        │
              │  inputs: per-agent budget + per-agent proposal       │
              │  rules:                                              │
              │    • Same direction same pair → conviction-          │
              │      weighted single ticket with summed sizing       │
              │      (capped by basket risk)                         │
              │    • Opposing direction same pair → highest-         │
              │      conviction wins; loser is journalled as veto    │
              │    • Disagreement across pairs → independent         │
              │      tickets, basket-correlation-aware sizing        │
              │  outputs: list[OrderIntent]                          │
              └──────────────────────────┬───────────────────────────┘
                                         │
              ┌──────────────────────────┴───────────────────────────┐
              │              RISK CONDUCTOR                          │
              │  hard caps:                                          │
              │    • Per-trade risk ≤ 1 % equity                     │
              │    • Per-basket risk ≤ 2 % equity (USD-long,         │
              │      USD-short, JPY-long, ...)                       │
              │    • Daily DD ≤ 4 % → flatten + cooldown             │
              │    • Margin level floor ≥ 200 % (4× broker stop-out) │
              │  invariant: every OrderIntent has a hard SL          │
              └──────────────────────────┬───────────────────────────┘
                                         │
                                         ▼
                       ┌──────────────────────────────────┐
                       │       EXECUTION LAYER            │
                       │  (existing broker / monitor /    │
                       │   state-store / vaults, untouched)│
                       └──────────────────────────────────┘
```

## 3. The contract every agent honours

```python
# pseudocode — not the final type
@dataclass(frozen=True)
class AgentProposal:
    agent_id: str                 # e.g. "zone_fade_v1"
    timestamp: datetime
    symbol: str
    direction: Literal["long", "short", "flat"]
    entry: float                  # market or limit; the price the
                                  # agent wants the trade taken at
    stop: float                   # hard SL price; mandatory
    ladder: list[LadderRung]      # [(price, fraction_to_close), ...]
                                  # must sum to 1.0
    conviction: float             # [0, 1] — agent's own confidence
    regime_fit: float             # [0, 1] — how well the current
                                  # regime matches this agent's edge
    valid_until: datetime         # proposal expires; agents do not
                                  # carry stale conviction
    rationale: dict[str, Any]     # explainability payload
    feature_vector: np.ndarray    # for the meta-learner, not the
                                  # aggregator
```

Key constraints:

- **Every proposal carries a hard SL.** Aggregator refuses
  proposals without one. This kills the L6 failure mode (no-SL
  blowup) at the type level.
- **Every proposal carries a ladder.** This unblocks per-rung
  partial-exit execution and ends the demo/live "exited too early"
  problem at the architecture level.
- **`regime_fit` is computed by the agent**, not the allocator.
  Each agent owns the answer to "does the current regime suit me?"
  because the agent has the most context to answer.
- **No agent reads another's proposal.** Information isolation is
  the whole point of late fusion. Cross-talk happens only at the
  aggregator.

## 4. The capital allocator (v0 plan)

Default mechanism (no learning): **Hierarchical Risk Parity** (López
de Prado 2016) over the agent return covariance matrix.

- **Why HRP not classical Markowitz / risk-parity:** classical methods
  require inverting Σ, which explodes when two agents are highly
  correlated (e.g. two trend agents). HRP clusters correlated agents
  first, then allocates within clusters.
- **Floor:** every active agent gets ≥ 2 % of risk budget so a starving
  agent can still learn and recover.
- **Cap:** no agent exceeds 35 % of risk budget. Forces diversification.
- **Update cadence:** weekly. Faster updates would over-fit to noise.

Advanced mechanism (Φ4 candidate): **Gated softmax meta-learner**
(Shazeer 2017 with load-balance penalty) — a small model that takes
regime features and emits weights. Optional. Equal-weight is the kill
condition K3 baseline.

## 5. The aggregator (v0 plan)

Three rules, in priority order:

1. **Same direction, same pair** → one ticket. Size = `min(Σ agent_size,
   per_pair_cap)`. Stop = tightest agent stop (so any agent's
   invalidation invalidates the trade). Ladder = union of rungs,
   conviction-weighted.
2. **Opposing direction, same pair** → highest-conviction × regime_fit
   wins. Other agents' proposals journalled as "vetoed near-miss" to
   `vetoes/events.jsonl` for ex-post analysis. Veto rate per agent is a
   live KPI.
3. **Independent pairs** → each pair handled independently *but*
   passed to risk conductor as a basket.

Aggregator is **pure logic** (no state). Trivially testable.

## 6. The risk conductor (v0 plan)

Sits between aggregator and execution. The "no veto, no order"
invariant lives here.

| Cap | Default | Adjustable? |
|---|---|---|
| Per-trade risk | 1 % equity | per-account config |
| Per-basket risk (correlated pairs) | 2 % equity | per-account config |
| Daily drawdown | 4 % equity → flatten + 24h cooldown | per-account config |
| Margin level floor | 200 % (4× broker stop-out) | per-broker config |
| Concurrent positions | 4 | per-account config |
| No-add to winners | enforced | non-configurable |
| Stop loss present | enforced | non-configurable |

Basket detection: when two pending OrderIntents touch correlated
instruments (|ρ| > 0.7 on rolling 30-d H1 returns), they are sized
*jointly* by basket risk, not independently. This closes the L3 / C4
gap.

## 7. Where this differs from the current architecture

| Current architecture (`agent/`) | Multi-agent v0 |
|---|---|
| One alpha (`SupplyDemandAlpha`) selects (signal, size, ladder) | N alphas each emit `AgentProposal`; aggregator selects |
| Strategy gates (HTF align, vol gate, news gate) are *eliminative* — fail → no trade | Gates are *informational* — fed to allocator as features; loser proposals are journalled |
| `PostLossGuard` halves size after a loss | Allocator down-weights any agent whose recent realised PnL is in left tail; PLG remains as a risk-conductor backstop |
| Risk scale is per-symbol in router | Risk scale is per-agent-and-symbol, learned from rolling realised performance |
| Soft SL = hard SL / catastrophe_mult | Soft SL is per-agent (agents differ in invalidation logic); catastrophe SL is risk-conductor-enforced floor |
| One process per symbol | One process per symbol still, *but* multiple agents inside it producing proposals |

## 8. What does *not* change

- Live runner orchestrator (`scripts/run_live.py`) — gets an option
  flag to switch between `single_alpha` and `ensemble` mode.
- Broker layer, MT5 wiring, monitor, state store, vaults — untouched.
- Observability (daily logs, near-miss vaults, ladder reach scoring,
  daily-summary report) — gains agent-id columns but format
  unchanged.
- Validation harness (walk-forward, holdout, frozen cross-pair, BH-FDR,
  PBO) — gains an "ensemble selection" tier on top of the per-agent
  tier.

## 9. Open questions for Φ1 / Φ2 to close

1. **Q1.** What is the right time horizon over which to estimate the
   agent-return covariance Σ for the allocator? Weekly? Monthly?
   Shrinkage-Ledoit-Wolf?
2. **Q2.** Should agents share features or compute their own from raw?
   (Shared = cheaper, late-fusion-purity-violation.)
3. **Q3.** Does the aggregator need a "abstain" outcome — i.e. all
   proposals are weak → no trade — distinct from "no proposal"?
4. **Q4.** Do we add an exploiter / adversary agent (AlphaStar-style PBT)
   in Φ5+, whose job is to find configurations the current roster gets
   wrong?
5. **Q5.** Veto journalling: do veto'd proposals get resolved (forward
   PnL) in the same near-miss resolver, or in a separate `vetoes/`
   resolver?
6. **Q6.** Capital-allocator update cadence — weekly is the default;
   does that survive a regime shift mid-week, or should regime shift
   trigger a forced re-allocate?

These questions remain `OPEN` in this doc until specifically resolved.

## 10. Build order (Φ3 prototype)

In order of dependency, smallest first:

1. `AgentProposal` dataclass + serialisation.
2. `BaseSpecialistAgent` interface + an adapter that wraps the existing
   `SupplyDemandAlpha` as `agent_id="zone_fade_v1"` (so the current
   strategy is the first roster member, not a competitor).
3. Trivial aggregator (rule 1 only — same direction same pair). Test.
4. Equal-weight allocator. Test.
5. Risk conductor with hard SL invariant + per-trade cap. Test.
6. End-to-end backtest path: feed sealed 2026 H1 data through one
   agent + trivial allocator + conductor; verify result is
   byte-identical to current single-alpha backtest.
7. Add agent #2 (most divergent thesis from zone-fade — likely
   momentum / break-out). Test pairwise.
8. Add HRP allocator. Compare against equal-weight on same data.
9. Add aggregator rule 2 (opposing proposals).
10. Add basket-correlation sizing. Validate against L3.

Each step lands in `experiments/multi_agent/`, has a one-paragraph
note in `docs/reviews/`, and is byte-deterministic.
