# 03 — Architecture v0 Sketch

**Status:** `DRAFT v0.2` — 2026-06-24. v0.2 lands the **Thought
Ledger** as a first-class data-plane object alongside the Proposal
Bus (see §2 diagram and §3.b); replaces the v0.1 "no agent reads
another's proposal" rule with the **tier-conditional read model** of
`06-blue-lock-doctrine.md` §3.9 (§3.a); reframes `Coordinate` as an
optional field on `Thought` rather than a parallel artefact (§3.b);
and pins the data-plane trajectory (JSONL → SQLite shadow →
WebSocket/Grafana) to `07-research-standards.md` §8 (§11).

> The boxes are still subject to revision after Φ4 (fusion sweep),
> but the typed objects are now committed enough that Φ3 can build
> against them without expecting structural change.

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
└──┬───┘  └──┬───┘  └────┬─────┘                 └────┬─────┘  └────┬─────┘  └────┬─────┘
   │ obs+intend            (every tick: observe → Thought; home_tf close: maybe intend → Proposal)
   │
   │  ╔══════════════════════════════════════════════════════════════════════╗
   ├─►║   THOUGHT LEDGER  (append-only JSONL; doctrine §3.8)                 ║◄─┐
   │  ║   • Tier-1 readers: dashboard, Aggregator (journal), F14/F17 harness ║  │
   │  ║   • Tier-2 readers: agents with ΔInfo > 0 (full ledger, §3.9)        ║  │
   │  ║   • Tier-3 readers: agents with ΔInfo ≤ 0 (own thoughts only)        ║  │
   │  ║   guards: `decision_horizon` (look-ahead), `references` (backwards)  ║  │
   │  ╚══════════════════════════════════════════════════════════════════════╝  │
   │                                                                            │
   │  Tier-2 agents read prior-tick ledger snapshot before `intend`────────────┘
   │
   │       │           │                            │             │             │
   └───────┴───────────┴─────────────┬──────────────┴─────────────┴─────────────┘
                                     ▼
                       ┌──────────────────────────────────┐
                       │       PROPOSAL BUS               │
                       │  (typed AgentProposal objects;   │
                       │   one per agent per home_tf      │
                       │   close, when intend fires)      │
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
              │  also: writes the fused decision (and its            │
              │  contributing Thought IDs) back to the Thought       │
              │  Ledger as a Tier-1 journal entry                    │
              │  outputs: list[OrderIntent]                          │
              └──────────────────────────┬───────────────────────────┘
                                         │
              ┌──────────────────────────┴───────────────────────────┐
              │              SENTINEL  (doctrine §4.2 + §4.3)        │
              │  triggers: ρ-jump, spread-spike, calendar event,     │
              │            DXY shock; hard rules R1-R5 (min-lot      │
              │            floor, discrete sizing, pass bias,        │
              │            concentration cap, loss-streak dampener)  │
              │  effect: veto + 24h halt, or per-trade block         │
              └──────────────────────────┬───────────────────────────┘
                                         │
              ┌──────────────────────────┴───────────────────────────┐
              │              RISK CONDUCTOR                          │
              │  hard caps:                                          │
              │    • Per-trade risk ≤ 5 % equity ($100 / 1:1000)     │
              │    • Per-basket risk ≤ 7 % equity (USD-long,         │
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

The Thought Ledger and the Proposal Bus are two distinct streams.
Every agent writes to the ledger every tick; only some agents, on
their home-TF close, write to the Proposal Bus. The Aggregator
consumes the Proposal Bus and writes back to the ledger as a Tier-1
journal entry (so the dashboard and the F17/F14 harness can replay
the fused decision against the contributing Thoughts).

## 3. The contracts every agent honours

The agent contract is now **two typed objects**: a per-tick `Thought`
and a per-home-TF-close `AgentProposal`. `Coordinate` (doctrine §3.2)
is no longer a parallel artefact — it lives as an optional field on
`Thought`, so its lifecycle is the lifecycle of the thought that
emitted it.

### 3.a `Thought` — the per-tick contract

```python
# pseudocode — see 06-blue-lock-doctrine.md §3.8 for the canonical schema
@dataclass(frozen=True)
class Thought:
    schema_version: int               # = 1 for v0
    agent_id: str
    tick_id: int                      # global squad tick (monotonic)
    timestamp: datetime
    symbol: str
    narrative: str                    # 1-3 sentence prose
    tags: list[str]                   # semantic labels
    confidence_in_thought: float      # [0, 1]
    expected_action: str | None       # e.g. "long_on_break", None
    coordinate: Coordinate | None     # optional; doctrine §3.2
    decision_horizon: datetime        # look-ahead guard
    ttl_ticks: int                    # read bound
    references: list[str]             # IDs of prior-tick thoughts;
                                      # MUST be backwards in time
```

### 3.b `Coordinate` — the embedded forward claim

```python
@dataclass(frozen=True)
class Coordinate:
    agent_id: str
    symbol: str
    price_lo: float
    price_hi: float
    time_start: datetime
    time_end: datetime
    vol_band: tuple[float, float]
    regime_predicate: str
    expected_strength: float          # [0, 1]
    direction_bias: Literal["long", "short", "either"]
    rationale: dict
```

(v0.1 fields, unchanged from doctrine §3.2. The change in v0.2 is
*where* it lives: as `Thought.coordinate`, not as a standalone
emission.)

### 3.c `AgentProposal` — the per-home-TF-close contract

```python
@dataclass(frozen=True)
class AgentProposal:
    agent_id: str                     # e.g. "zone_fade_v1"
    tick_id: int                      # the squad tick this proposal
                                      # was emitted on
    source_thought_id: str            # the Thought that crystallised
                                      # into this proposal
    timestamp: datetime
    symbol: str
    direction: Literal["long", "short", "flat"]
    entry: float                      # market or limit
    stop: float                       # hard SL price; mandatory
    ladder: list[LadderRung]          # [(price, fraction_to_close), ...]
                                      # must sum to 1.0
    conviction: float                 # [0, 1]
    regime_fit: float                 # [0, 1]
    valid_until: datetime             # proposal expires
    rationale: dict[str, Any]         # explainability payload
    feature_vector: np.ndarray        # for the meta-learner, not the
                                      # aggregator
```

### 3.d Key constraints

- **Every proposal carries a hard SL.** Aggregator refuses
  proposals without one. This kills the L6 failure mode (no-SL
  blowup) at the type level.
- **Every proposal carries a ladder.** This unblocks per-rung
  partial-exit execution and ends the demo/live "exited too early"
  problem at the architecture level.
- **Every proposal references the Thought that produced it**
  (`source_thought_id`). The journal is bidirectional: a closed
  trade can be replayed against the Thought that crystallised it
  AND every Thought (own and peers') that informed that Thought via
  `references`.
- **`regime_fit` is computed by the agent**, not the allocator.
  Each agent owns the answer to "does the current regime suit me?"
  because the agent has the most context to answer.
- **Tier-3 agents are information-isolated; Tier-2 agents read the
  Thought Ledger with the schema-enforced look-ahead guard**
  (`decision_horizon`, `references` backwards-only). This replaces
  the v0.1 rule "no agent reads another's proposal". Information
  isolation is *still* the default in v0.2 — but now it is decided
  empirically per agent (via ΔInfo, F17) rather than by blanket
  prohibition. See `06-blue-lock-doctrine.md` §3.9 for the tier
  model and §3.8 for the read guards.

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

| Cap | Default ($100 / 1:1000) | Adjustable? |
|---|---|---|
| Per-trade risk | 5 % equity (sandbox-relaxed; original spec was 1 %) | per-account config |
| Per-basket risk (correlated pairs) | 7 % equity (sandbox-relaxed; original spec was 2 %) | per-account config |
| Daily drawdown | 4 % equity → flatten + 24h cooldown | per-account config |
| Margin level floor | 200 % (4× broker stop-out) | per-broker config |
| Concurrent positions | 4 | per-account config |
| No-add to winners | enforced | non-configurable |
| Stop loss present | enforced | non-configurable |
| Discrete position sizes (Sentinel R2) | round to min-lot 0.01, direction "down" | non-configurable |
| Min-lot risk floor (Sentinel R1) | block trade if SL distance × 0.01 lot > 5 % equity | non-configurable |
| Loss-streak dampener (Sentinel R5) | 50 % risk-scale × 24h after 3 consecutive losses | non-configurable |

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

## 11. Data plane (Φ2.5 → Φ4 → Φ6+)

The architecture above is the **logical** flow. The data-plane
trajectory — what actually stores and serves the Thought Ledger,
Proposal Bus, and trade journals — is pinned to
`07-research-standards.md` §8 and summarised here so the diagram
does not paint Φ2.5 storage choices into a corner.

| Phase | Storage | Index | Dashboard | Trigger to upgrade |
|---|---|---|---|---|
| Φ2.5 (now) | JSONL append-only; one file per agent per UTC day for the Thought Ledger; one parquet per backtest result; per-trade journal as a single growing JSONL keyed by `trade_id` | None beyond filesystem layout | Streamlit running locally, no autorefresh | First PBT run or sweep > 100 configurations |
| Φ4 (fusion sweep) | JSONL remains source of truth; **SQLite shadow** rebuilt from JSONLs on demand (one table per stream: thoughts, coordinates, proposals, trades, KPIs) | SQLite + materialised view per dashboard panel | Streamlit + autorefresh | First live shadow run for capital-promotion eval |
| Φ6+ (live shadow + capital) | JSONL append-only remains long-term truth; SQLite shadow upgraded to small Postgres OR kept as SQLite (decision deferred) | SQL + thin **WebSocket sidecar** publishing new ledger entries + **FastAPI** in front of read paths | Either small React/Svelte frontend on WebSocket+FastAPI, **or** Grafana on the SQL store — choose one when we get there | n/a |

JSONL append-only is the through-line; everything else is indices,
views, and transports built on top of that immutable spine. The
dashboard spec in `08-dashboard-spec.md` describes the Φ2.5
Streamlit panel inventory that consumes this data plane.
