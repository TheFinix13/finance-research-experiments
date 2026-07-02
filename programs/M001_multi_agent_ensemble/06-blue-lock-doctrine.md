# 06 — Blue Lock Doctrine

**Status:** `DRAFT v0.5` — 2026-07-01 (v1/v2 versioning discipline
clarified per user 2026-07-01 decision on Phase 6 completion; §3.11.5
lands the operational definition of a v1 checkpoint; G7 v1-checkpoint
gate introduced at `experiments/G7_v1_checkpoint_gate/PROTOCOL.md`;
three new v1 primitives — F19 `lot_intent`, F20 `risk_intent`, F21
reasoning workspace — added in §4.1a. These are per-agent capabilities
that belong in v1, not v2 capability additions).

**The 2026-07-01 v1/v2 reframe (§3.11.5).** User's operational definition:
- **v1** = a checkpoint state where the agent has demonstrated
  undeniable positive results in its own testing AND functions
  productively alongside its teammates in the squad. It is not "the
  code the agent was born with" — it is "the code that cleared the
  v1 checkpoint gate (G7)".
- **v2** = a named architectural addition that empirically trumps a
  proven v1 by pre-declared margins (per §3.11.2 contract).

Under this reframe, six of the previously-labeled "v1 → v2"
resolutions from 2026-06-25 / 2026-06-30 (Barou hybrid A+B, Bachira
REFINE-to-peer-silence, Rin REFINE-regime+peer-disagreement, Chigiri
REFINE-multi-TF-ADX+ATR-percentile, Reo ADVANCE-coupled-to-Φ5-multi-
position, Kunigami R5-wired) are — under the reframe — **v1 mechanic
iterations pending G7**, not v2 evolutions. The v2 label is reserved
for post-G7 capability additions that empirically trump a proven v1.
Only Isagi (A1) has passed a v1-analog gate to date (Φ3 PASS,
`reviews/phi3_gate_isagi_v1.md`); Isagi's v1→v2 arc (2026-06-24) is
the *only* true v2 attempt to date, and it FAILED.

**The chemical-reaction mandate.** The reframe elevates the doctrine's
chemical-reaction concept from a §3.3 confluence-detection feature to
a first-class architectural primitive (F21 — reasoning workspace) that
every agent's v1 must demonstrate: agents must be able to *read* each
other's forward-looking Thoughts before deciding their own trade, and
the v1-checkpoint gate G7 tests the squad's collective chemistry, not
just per-agent solo TQS.

v0.4.1 (below) stands as the pre-reframe record.

**Status:** `DRAFT v0.4.1` — 2026-06-25 (Barou row amended 2026-06-30;
A10 Kunigami row un-deferred 2026-06-30 post Sentinel R1–R6 wiring).
v0.4 records the **first three §3.11 sketch resolutions** post-Φ4.1: A6
Nagi v2 sketch DROPPED (v1 floor empirically correct — confluence-firing
thoughts 0 → 34,302 between Φ4 and Φ4.1, mean TQS 0.349 highest in the
8-agent squad); A7 Barou v2 sketch REDESIGNED to a hybrid mechanic A
(closed-loss replay) + mechanic B (symbol-whitelist expansion to
EURUSD/GBPUSD/USDCAD), per `reviews/v2_arc_backlog_resolution_2026-06-25.md`
§2 + 2026-06-30 amendment (user resolved C-Q1 = both A and B); A10
Kunigami v2 sketch WIRED 2026-06-30 via Sentinel R1–R6 mini-sprint
(Kunigami's 25,877 warning Thoughts at Φ4.1 previously had 0 R5
consumers; the Φ4.2 wiring adds `SentinelContext.kunigami_loss_streak_
active` + `evaluate_proposal` helper + `R6` per-symbol total-risk cap
for Φ5 Arm 4; audit-only in Φ4 / Φ4.1 replays, physically blocking
via `sentinel_blocks=True` in the Φ5 harness). Resolution detail:
`reviews/v2_arc_backlog_resolution_2026-06-25.md` + `experiments/
phi5_aggregator/PROTOCOL.md` §11.1 amendment. v0.3 stands below.

v0.3 (2026-06-24) adds **§3.11 — Agent Evolution Arcs**, the
canon-inspired contract that every striker is a *versioned identity*
(vN, vN+1, …) whose evolution is *earned* by a documented defeat
trigger or phase gate, never asserted. §3.11.2 is the regression /
forward-test contract for any vN → vN+1; §3.11.3 seeds per-agent
evolution sketches (initial, refined as defeats accumulate); §3.11.4
points at the new `reviews/evolution_ledger.md` audit trail. The v0.2
revisions stand below.
v0.2 (second pass) formalises the **Thought Ledger** as a first-class
object (§3.8), the **three-tier access model** decided empirically by
ΔInfo (§3.9), and the **canon-role vs information-tier** orthogonality
(§3.10); splits the striker base class into an **`observe` / `intend`
pair** (§4.1); appends **Sentinel hard rules R1–R5** for the $100 /
1:1000 account (§4.3); and cites E006 Stage-2 exploratory evidence
(`audits/2026-06-24_E001-E007_audit.md` §2.6, §4.3) inside the
chemical-reaction discussion (§3.3). The first-pass v0.2 resolved
Q-doc-1 through Q-doc-5 (see §8), added §3.1.b on the principled-form
of ego (information ratio across peers), formalised the A+ setup
score (§3.7) and replaced the universal H4 emission cadence with
per-agent home-TF cadence gated by A+ threshold, expanded metavision
in §1.1 to its evolved order-flow form (with Isagi v1's primitive
seed being the existing `zone_d1_against` detector), and introduced
the **Sentinel** as a non-character architectural role for external-
shock containment (§4.2). Q-doc-6 is added and resolved together with
the others.

> "Soccer is a sport where you devour each other to score." — Ego Jinpachi
>
> "The world doesn't reward kindness. It rewards results." — Ego Jinpachi

This doc is the philosophical spine of the multi-agent ensemble.
Every metaphor below is translated into either a **typed object** (a
class the code will instantiate), a **measurable KPI** (a number we
compute and journal), or a **structural rule** (an architectural
invariant the conductor enforces). If a metaphor doesn't translate to
one of those three, it doesn't earn a place in the codebase.

The previous docs (`00-charter`, `03-architecture`, `04-foundations`,
`05-roster`) are the *what* and the *how*. This doc is the *why*.

---

## 1. Source canon and what we borrow

### 1.1 Blue Lock — Ego Jinpachi's doctrine

Five concepts from the manga / anime are operationally load-bearing:

1. **Ego.** The selfish hunger to be the one who scores. Not
   teamwork-first; me-first. Producers of value are individuals who
   refuse to defer.
2. **Weapon.** Each striker has *one* signature ability that nobody
   else has. Bachira's monstrous dribble is not Rin's cold technique
   is not Chigiri's speed is not Isagi's metavision. Generality is
   weakness; *specialised dominance* is strength.
3. **Metavision.** Isagi's *evolved* order-flow awareness. He starts
   with raw spatial perception of zone touches (Isagi v1 = the
   existing `zone_d1_against` detector) and *evolves* through training
   into full order-flow reading — H1 volume-bucket imbalance, FVG
   detection, IRL/ERL liquidity mapping, market-structure shifts. The
   training arc is the canon justification for why the seed strategy
   is the *primitive* form of the weapon, not its final form.
4. **Chemical reaction.** When two strikers' weapons collide
   *productively*, neither defers — but the trajectory of one
   creates an opening the other exploits. Rare, non-deterministic,
   high-output. Not co-operation; it's overlapping ego producing
   emergent value.
5. **Devour.** Eat the strengths of your opponents. Take what beat
   you and make it yours. Evolutionary; competitive; you grow only
   by losing first.

Optional sixth concept (used here, not central in canon):
**Awakening** — the moment a player's weapon levels up by
recombination with a borrowed strength. We use this to describe
agent parameter evolution / population-based training.

### 1.2 Attack on Titan — the Coordinate

In AoT, the "Coordinate" is the locus through which the Founding
Titan can command all titans simultaneously. It is the *single
spatial-temporal point at which all paths intersect*.

We borrow this for trading: each agent claims a **Coordinate** —
a 4-dimensional bounding box in (price × time × volatility ×
regime-condition) where its A+ setup is most likely to materialise.
Two agents whose coordinates overlap are entering the same field
of play; that overlap is the *trigger* for chemical reaction.

This is the most operational concept in the doctrine — it gets a
typed dataclass in `agent/multi/coordinate.py` (Φ3).

---

## 2. Operational translation table

The full metaphor → math map. Every entry has a section in this doc
or in `04-quant-foundations.md`.

| Canon concept | Operational object | Type | Where defined |
|---|---|---|---|
| Ego | Per-agent reward greediness; conviction floor | scalar (≥ 0) per agent | §3.1 |
| Weapon | The agent's strategy primitive | code module | `05-agent-roster-v0.md` |
| Metavision | Liquidity / structure mapping | feature detector | Isagi agent spec |
| Coordinate | (price, time, σ, regime) bounding box | `Coordinate` dataclass | §3.2, F13 |
| Chemical reaction | Confluence of overlapping coordinates | event + conviction lift | §3.3, F11 |
| Devour | Capital allocation reweighting toward winners | allocator update rule | §3.4, F2/F3 |
| Awakening | Per-agent parameter evolution | PBT mechanism | Φ5+, lit §1.5 |
| Trade quality | "Beautiful goal" score | TQS metric | §3.5, F12 |
| Assertion | Agent's order survival rate | KPI | §3.6 |
| Coexistence | Confluence participation rate | KPI | §3.6 |
| Devour rate | Agent's collision-win rate | KPI | §3.6 |
| Coach (Ego Jinpachi) | Risk Conductor + Allocator | architectural layer | `03-architecture` |
| Sentinel | External-shock auxiliary | architectural role | §4.2 |
| Striker | Specialist agent | base class | §4 |
| Thought Ledger | Append-only journal of every agent's reasoning | JSONL stream + `ThoughtLedger` reader | §3.8 |
| Thought | One agent's per-tick narrative + tags + optional coordinate | `Thought` dataclass | §3.8 |
| Canon role | Fixed identity layer (weapon, ego, narrative voice) | `CanonRole` dataclass | §3.10 |
| Information tier | Empirical read-permission layer (ΔInfo-decided) | Tier ∈ {1, 2, 3} | §3.9, F17 |
| Agent lot-size intent | Per-agent conviction-driven position sizing | `lot_intent()` method | §4.1a, F19 |
| Agent risk-shape intent | Per-agent playstyle-driven SL/TP cognition | `risk_intent()` method | §4.1a, F20 |
| Reasoning workspace | Per-tick shared blackboard for peer Thought reads | `ReasoningWorkspace` dataclass | §4.1a, F21 |
| v1 checkpoint | Squad-level chemistry + per-agent adequacy gate | G7 gate | §3.11.5 |
| Opponent (Kaiser/Loki) | Human discretionary trades | adversarial benchmark | §5, F14 |
| Pitch | Demo account ($100, 1:1000) | environment | §6 |
| Goal | Closed profitable trade scored by TQS | event | §3.5 |
| Match | One trading week | evaluation window | §3.6 |
| Tournament | Sealed evaluation period | promotion gate | `00-charter` |

---

## 3. The five operational primitives

### 3.1 Ego (per-agent reward greediness)

Ego in Blue Lock is the refusal to defer. Operationally an agent's
ego is a scalar `ego ∈ [0, 1]` that sets:

- **Conviction floor.** Below this, the agent emits no proposal.
  High-ego agents fire often (Bachira, Chigiri); low-ego agents fire
  rarely (Nagi). Hyperparameter; agent-specific.
- **Defer threshold.** When two agents' coordinates overlap, the
  lower-ego agent yields conviction credit to the higher-ego agent
  in the confluence sum. (We will *not* let an agent veto itself out
  of a chemical reaction; ego controls *credit assignment*, not
  participation.)
- **Reward function tilt.** Per-agent learning (Φ5+) optimises a
  tilted objective:
  `objective_i = TQS_i + ego_i × (TQS_i − mean(TQS_others))`.
  High ego = "I want to outperform the others, not just score."

Ego is *not* a free parameter we tune to the data. Each agent's ego
is set by its character and stays stable. Otherwise the metaphor
collapses into "a learnable weight."

### 3.1.b Ego, principled form

Ego in v0 is set by character feel (Barou 1.00, Bachira 0.85,
Kunigami 0.00). This is a *placeholder*. From Φ4+, ego is re-derived
as the **information ratio of the agent's edge versus its peers**:
if your weapon produces an edge that no other agent shares, you carry
high ego; if your weapon is similar to two other agents', ego is
dampened. Concretely:

> `ego_i = clip( IR(agent_i edge | other agents' edges), 0, 1 )`

where IR is the residual Sharpe of agent `i` after regressing its TQS
time-series against the other agents' TQS time-series. High residual
= unique weapon = high ego. The character ego values become Bayesian
priors; the data updates them.

This is the league dynamic — every agent's ego depends on what the
others are doing well, so improvement by anyone raises the bar for
everyone. It is also the formal reason why Reo (the chameleon) has
low ego: by construction his TQS is highly correlated with the
trailing leader's, so his residual is small, so his ego is small.

### 3.2 Coordinate (the AoT locus, formalised)

A `Coordinate` is the agent's claim: *here is the box in which my A+
setup is most likely to land*. It is emitted *before* a trade
trigger fires — it is a forward-looking promise, not a retrospective
description.

```python
@dataclass(frozen=True)
class Coordinate:
    """An agent's forward-looking claim of where + when its A+ setup
    will materialise. Emitted on every H4 close; expires at
    time_end."""

    agent_id: str
    symbol: str

    # Spatial: horizontal price band (the "shoot zone")
    price_lo: float
    price_hi: float

    # Temporal: how long this claim is valid
    time_start: datetime  # usually "now" (the emitting H4 close)
    time_end: datetime    # forward window; coordinate dies at time_end

    # Conditional: only fires if these context predicates hold
    vol_band: tuple[float, float]   # (sigma_lo, sigma_hi) on H1 returns
    regime_predicate: str           # rule key, e.g. "D1_trend=down"

    # Strength: agent's own probability the box is correct
    expected_strength: float        # [0, 1]
    direction_bias: Literal["long", "short", "either"]

    rationale: dict                 # explainability payload
```

**Lifecycle.**
1. On each agent's own home-TF close (per the roster's `Home TF`
   column in `05-agent-roster-v0.md`), agents emit coordinates iff
   their A+ score (§3.7) crosses their personal threshold. Universal
   H4 cadence is retired — Chigiri ticks on M15, Aoshi on M5
   event-windows, Isagi on H1, Rin and Barou on H4, Kunigami off
   internal equity state. The aggregator polls heterogeneously.
2. Coordinates are written to `coordinates/events.jsonl` (new vault).
3. Aggregator computes pairwise overlaps (F13) and flags chemical
   reactions.
4. When price enters a coordinate's box and the agent's *trigger*
   fires inside it, the agent emits a full `AgentProposal`.
5. Coordinates expire at `time_end`, become resolved post-hoc:
   "did price actually visit the box? did the agent's trigger fire?"

**Why this design.** Separating coordinates (the prediction) from
proposals (the order) lets us measure two distinct skills:
- **Targeting** (does the agent know *where*?) — coordinate hit-rate.
- **Execution** (does the agent know *when*?) — proposal-to-fill rate.

Isagi's metavision is about the first. Yukimiya / Otoya's smooth
execution is about the second. They are different weapons.

### 3.3 Chemical reaction (confluence)

Two agents' coordinates *react* when **all** hold:

1. Same `symbol`.
2. Price bands overlap by ≥ 50 % of the smaller band.
3. Time windows overlap by ≥ one H4 bar (4h).
4. Vol bands intersect.
5. `direction_bias` is compatible (same direction, or one is
   `either`).
6. Regime predicates do not conflict (one says "trend=up", the other
   does not say "trend=down").

Conviction lift is **independent-OR** (F11) — multiplicative, not
additive:

> `c_combined = 1 − ∏_i (1 − c_i × ego_i)`

This honours the canon: a reaction is *not* the sum of two ordinary
shots; it is qualitatively different — neither agent could have
produced this conviction alone. With two 0.5-conviction agents,
combined conviction is 0.75, not 1.0. With three 0.5-conviction
agents, 0.875.

Trade size is lifted by the `confluence_multiplier`:

> `size_multiplier = 1 + 0.5 × log₂(num_agents_in_reaction)`,
> capped at 2.5×.

Two agents = 1.5×. Three = 1.79×. Four = 2.0×. Six = 2.29×. Cap at
2.5× prevents runaway leverage.

Hard rule: a chemical reaction *does not* lower stops. The trade's
SL is the **tightest** SL among participants — any agent's
invalidation pulls the whole trade out. This bakes ego back in:
"if any of you was wrong, we're all out."

**Empirical prior for the chemical-reaction layer.** E006 Stage-2
exploratory (the pre-M001 lab) found that H1 `equal_highs_pool`
lifts every M15 setup placed under it by +0.10 to +0.46 ATR
(selection term, displacement null), across 65 H1-context × M15-setup
pairs. See `audits/2026-06-24_E001-E007_audit.md` §2.6 and §4.3 for
the per-cell numbers and the protocol notes. This is the first piece
of *evidence* (rather than analogy) that the late-fusion frame —
context primitive amplifies setup primitive — produces non-trivial
lift in FX intraday data. E010 will validate this independently in
parallel with M001 development (pre-registered Stage-2b); A6 Nagi's
deployment-grade confluence layer waits for E010 to confirm before
graduating, but the doctrine treats this as a directional prior now.

### 3.4 Devour (competitive capital reallocation)

Standard ensemble methods reweight by Sharpe or PnL. We reweight by
**TQS** (§3.5) and we make it explicitly competitive:

> Weekly: each agent's allocator weight is updated via HRP (F3) over
> the agent's *TQS-vector* (not raw return) covariance, with an
> additional **devour bonus**:
>
> `w_i' = w_i × (1 + δ × (TQS_i − median(TQS_all)) / IQR(TQS_all))`
>
> followed by renormalisation to sum to 1, floor 0.02, cap 0.35.

`δ = 0.25` (tunable). Agents above the median *eat into* the
allocations of agents below. Agents below survive at the 2 % floor
so they can recover.

Population-Based Training (Jaderberg et al. 2017, AlphaStar) is the
academic precedent. Φ5+ extends devour to parameter perturbation —
losers don't just get smaller allocations; their hyperparameters
get pushed toward winners' (the *Awakening* mechanism).

### 3.5 Trade Quality Score (TQS) — the "beautiful goal" metric

Raw P&L is the wrong objective. A 30-pip win that took 6 hours, ran
−10 pips of drawdown, and was clean is more valuable than a 30-pip
win that took 4 days, ran −80 pips, and required two re-entries.
Blue Lock celebrates *shocking, beautiful goals* — speed × magnitude
× efficiency × cleanliness.

We compute (F12):

> `TQS = R^0.7 × efficiency × time_score × cleanliness × beauty_bonus`
>
> where:
> - `R = max(0, realised R-multiple)` — losing trades score 0
> - `efficiency = max(0, 1 − MAE_pips / max(MFE_pips, 1))` — how
>   little drawdown vs max favourable
> - `time_score = exp(−(actual_hold − target_hold)² / (2 × target_hold²))`
>   — gaussian around the agent's target hold time
> - `cleanliness = 1.0` if no adds, no panic-exits, broker-stop never
>   threatened; else `0.7`
> - `beauty_bonus = 1.2` if entry was inside a chemical-reaction
>   coordinate; else `1.0`

TQS is computed at trade close and journalled per agent. It is the
**fitness function** for the allocator and (Φ5+) for PBT.

Important property: a losing trade scores **0**, not negative. The
allocator down-weights via low-TQS, not via punitive negatives. This
matches Blue Lock's framing — you don't get points for ugly losses;
you also don't get crucified for clean ones. (Negative reward is
reserved for the Risk Conductor, which is a separate layer.)

### 3.6 Assertion / Coexistence / Devour-rate (the soccer analytics)

Per-agent KPIs, computed weekly, journalled to
`agents/<agent_id>/kpis_<week>.json`.

| KPI | Definition | Canon analog |
|---|---|---|
| **Assertion rate** | orders_taken / proposals_emitted | "shots taken / shots attempted" |
| **Coexistence rate** | confluence_participations / proposals_emitted | "key passes / shots" |
| **Devour rate** | wins_in_collision / collisions | "1v1 wins" — when two agents propose opposite-direction same-pair |
| **Goal rate** | profitable_trades / orders_taken | hit rate |
| **Beauty rate** | mean(TQS) over orders taken | quality of finishing |
| **Awakening delta** (Φ5+) | Δ(parameter mean) since last cycle | parameter evolution |

These five (six with awakening) make the per-agent dashboard. After
each week we get a five-row scorecard per agent. Patterns flag
issues:

- High assertion + low goal-rate = trigger-happy; tighten conviction floor.
- Low assertion + high goal-rate = too cautious; consider lowering ego threshold or moving to Nagi-class.
- High coexistence + low solo goal-rate = "support player," should not be sized as a primary.
- High devour rate = this agent wins arguments; it's earning its weight in the roster.
- Low beauty rate, high goal-rate = wins ugly; risk-conductor scrutiny.

### 3.7 A+ setup score (Q-doc-2 resolution)

The doctrine no longer asks "did the H4 close just happen?" — it asks
"is this an A+ setup *now*?" Each agent computes a scalar A_score per
its home-TF close (and any sub-TF refresh its weapon allows), and
emits a coordinate only when the score crosses its personal
threshold. Sparsity is a feature, not a quota.

> ```
> A_score = 0.25 × regime_fit
>         + 0.25 × conviction
>         + 0.20 × confluence_proximity
>         + 0.20 × structural_cleanliness
>         + 0.10 × novelty
> ```

Components:

- **regime_fit** — agent's self-assessment that the current regime
  matches its diversity-matrix row in `05-agent-roster-v0.md` §2.
  `[0, 1]`. Computed off the agent's own regime detector (ADX bucket,
  realised σ percentile, ranging-vs-trending classifier).
- **conviction** — the agent's per-setup confidence, produced by its
  detector logic exactly as today's `zone_d1_against` already does.
  Same scale `[0, 1]`.
- **confluence_proximity** — `exp(−d / 0.3)` where `d` is the F13
  overlap-score distance to the nearest *other* agent's active
  coordinate. `d = 0` means the boxes coincide (max bonus); `d > 1`
  means no overlap. Encodes the canon: chemical reactions are
  high-value. No other agents active yet? `confluence_proximity = 0`
  (the bonus is opt-in; it does not penalise being first).
- **structural_cleanliness** — the source signal's quality. For Isagi
  / Rin this is "single-thrust swing, no overlapping pivots"; for
  Chigiri this is "clear range pre-break, ATR rising not falling";
  for Bachira this is "pattern symmetry / shoulder ratio in canonical
  bounds". Agent-defined, agent-journalled. `[0, 1]`.
- **novelty** — `1 / (1 + recent_fires_in_box)` where the recency
  window is 5× the agent's target_hold. Prevents the same coordinate
  being re-emitted on every bar; rewards finding a *new* shot, not
  re-shouting an old one.

**Emission rule.** Default emit if `A_score ≥ 0.60`. Personal
threshold is per-agent and ego-modulated:

> `A_threshold_i = 0.85 − 0.40 × ego_i`

So Barou (ego 1.00) emits whenever `A_score ≥ 0.45` (King fires
often); Kunigami (ego 0.00) emits only at `≥ 0.85` (and per his spec,
emits *negative* coordinates only). The character egos drive the
firing personality; the principled-form ego (§3.1.b) eventually
replaces the placeholder values once the data tells us who is unique.

### 3.8 The Thought Ledger

A first-class append-only journal of agent reasoning. Every agent
emits `Thought` objects at every observation tick; some Thoughts
crystallise into `AgentProposal` objects at decision ticks. The
ledger is the canonical evidence stream the dashboard renders, the
post-hoc evaluation harness consumes (F14, F17), and the Tier-2
agents (per §3.9) read during decision.

```python
@dataclass(frozen=True)
class Thought:
    schema_version: int           # = 1 for v0; bumped on schema change
    agent_id: str
    tick_id: int                  # global squad tick (monotonic)
    timestamp: datetime
    symbol: str
    narrative: str                # 1-3 sentence prose reasoning
    tags: list[str]               # semantic labels:
                                  #   ["supply_zone", "d1_against",
                                  #    "h1_pattern", ...]
    confidence_in_thought: float  # [0, 1]
    expected_action: str | None   # e.g. "long_on_break", "wait", None
    coordinate: Coordinate | None # optional; None for observation-only
    decision_horizon: datetime    # latest bar timestamp this thought
                                  # could legitimately have used
    ttl_ticks: int                # writer's TF ticks; bounds reads
    references: list[str]         # IDs of other thoughts this builds
                                  # on (empty in v0 for Tier-3 agents)
```

Two architectural guarantees the schema gives us:

- **`decision_horizon` is a look-ahead guard.** Reading agents at
  tick T may only consume thoughts where `decision_horizon ≤ T's
  bar_time`. This is the architectural translation of the E006 hour-
  matched-controls episode (where uniform-time controls leaked 3.7×
  hour-of-day variance into the null — fixed pre-MFE by amendment
  v2.1). See `audits/2026-06-24_E001-E007_audit.md` §2.6 and §3.2.
  The same discipline applies to inter-agent reads: a thought whose
  validity extends past `decision_horizon` is dropped by the reader,
  not the writer.
- **`references` only points BACKWARDS in time** (`tick_id <
  current_tick`). Same-tick reads are forbidden. This breaks
  reflexive loops between writer and reader agents — Reo cannot read
  Isagi's current-tick thought before forming his own, only Isagi's
  prior-tick thoughts.

Forward-declared in `07-research-standards.md` §6 as `Thought` with
the same `schema_version` / `decision_horizon` / `ttl_ticks` fields;
the v0.2 schema above is the formalisation that satisfies that
forward declaration. v0.1 consumers may assume schema 1.

Implementation lives at `sim/thought_ledger/` (Φ2.5+), with one JSONL
file per agent per UTC day. Consumer API is a thin reader that
returns the slice satisfying both guards.

### 3.9 Three-tier access model

Who reads the Thought Ledger:

| Tier | Who | Read access |
|---|---|---|
| **Tier 1** (always read) | Human dashboard, the Aggregator (for journalling fused decisions), the post-hoc evaluation harness (for F14 adversarial comparison and F17 ΔInfo) | Full ledger, no restriction |
| **Tier 2** (conditional read, decided empirically) | Agents whose ΔInfo > 0 and bootstrap-significant at α = 0.05 | Full ledger (subject to `decision_horizon`/`ttl_ticks`/`references` guards from §3.8) |
| **Tier 3** (information-isolated) | Agents whose ΔInfo ≤ 0 (or not yet measured at C1 promotion); their edge is independently measurable and acts as the **control** for Tier-2 agents | Own agent's past thoughts only (`agent_id == self`) |

**Critical: tier assignment is empirical, NOT a priori.** Every agent
is trained and evaluated **twice** on identical windows — once with
full Thought Ledger access (informed), once with ledger access
restricted to the agent's own thoughts (isolated). The ΔInfo metric
(F17 in `04-quant-foundations.md`) decides which deployment ships.

This supersedes the placeholder tier definitions in
`07-research-standards.md` v0.1 §7.2 / §7.3 (which described Tier 2
as "own + one cluster of peers" and Tier 3 as "audit-only"). Those
definitions were forward-declared research debt before F17 existed;
v0.2 lands the data-driven model above.

### 3.10 Canon role vs information tier

Two orthogonal layers:

| Layer | Set how | Mutable? |
|---|---|---|
| **Canon role** (weapon, ego, preferred coordinate type, narrative voice, target hold) | A priori, from Blue Lock canon | Fixed at Φ0 |
| **Information tier** (reads ledger? Y/N, scope of reads) | Empirically, from ΔInfo measurement | Reviewed each phase gate |

### 3.10a Structural-falsifier waiver class (2026-07-01 amendment)

Some canon roles are *observers* rather than *proposers*. Their
`intend()` returns None by design; their contribution is the
publish-side of the workspace (mirror Thoughts, warning Thoughts, HRP
weight-vectors) rather than an executed trade. Evaluating them on
trade-driven criteria (C1 TQS, C5 lot dispersion, C6 risk-shape
dispersion) is a category error: there are no trades to score.

Two agents currently qualify:

- **A5 Reo (copier_hrp).** Publishes a mirror Thought every tick
  carrying an HRP-weighted mixture of top-K peer intents. His weapon
  is the *reasoning-workspace signal*, not the trade.
- **A10 Kunigami (defensive observer).** Publishes a warning Thought
  every tick with the current anti-tilt state (loss-streak count,
  overconfidence flag). His weapon is the *risk-state broadcast*, not
  the trade.

Both are waived on C1/C5/C6 (never proposes → nothing to measure) and
on C4's read requirement (workspace *is* their weapon; they don't need
to read it). They must still satisfy C4's publish requirement
(`publish_count > 0` in ≥ 5 of 7 OOS windows) — publishing IS their
v1 evidence.

Waived criteria count as passes for the squad-level v1 tally in
`is_v1_pass`. Any *new* agent claiming a structural-falsifier waiver
must be added to this list explicitly, with a canon-role justification
recorded in `05-agent-roster-v0.md` and a matching row in the
evolution ledger.

A Tier-3 Bachira still has Bachira's improvisational identity in
narrative + tags + weapon — he just doesn't read peers' thoughts
during decision. Both Bachira-isolated and Bachira-informed are
evaluated; the data picks the deployment. If informed Bachira beats
isolated Bachira by enough to clear the α = 0.05 bootstrap on F17,
he ships with ledger access; otherwise he ships information-isolated
and his isolated performance becomes part of the Tier-2 control
comparison for the next phase.

This is the formal answer to a confusion that ran through v0.1: the
character-feel egos in `05-agent-roster-v0.md` (A1 0.60, A7 1.00,
A10 0.00, etc.) are *canon* — they belong to the agent's identity
and stay fixed. The information tier is *empirical* and lives on a
different axis. A high-canon-ego agent (A7 Barou) can be Tier-3 if
F17 says his contribution is redundant with A4 Chigiri's; a low-
canon-ego agent (A10 Kunigami) can be Tier-2 if his anti-tilt
signal contains marginal information no one else carries.

The doctrine governs *what an agent is*; the tier governs *what the
agent is allowed to read* in the ensemble's collective deliberation.

### 3.11 Agent evolution arcs

The third orthogonal layer. §3.10 separated *identity* (canon role,
fixed at Φ0) from *permission* (information tier, ΔInfo-decided).
§3.11 separates both of those from **version** — the implementation
generation `vN` of the agent's weapon. Identity is fixed; permission
is empirical; **version is earned**.

This is the operational translation of the Blue Lock "evolution"
mechanic. Characters in the manga do not grow by accumulating tweaks
between matches. They evolve by facing a *specific limit*, naming the
defeat, and returning with a *specific new capability* that resolves
it. Barou faces defeat to evolve. Chigiri learns to run again only
after losing his first race. Bachira releases the monster only when
teaming fails him. Isagi's metavision sharpens only when his current
read misses the goal. The arc is the unit of growth; tweaks are not.

#### 3.11.1 The principle

Each striker is a versioned identity, not a static implementation. A
transition `vN → vN+1` of any agent is **triggered by one of**:

- **Defeat trigger.** A measurable failure mode in vN's evaluation:
  a loss streak, a ΔInfo collapse, a regime mis-prediction, persistent
  rejection by other strikers in the Ledger, a TQS regression in a
  specific regime bucket. The defeat is identifiable in the per-trade
  journal, not in the modeller's intuition.
- **Phase trigger.** Reaching a phase gate that mandates expansion
  (e.g., crossing Φ4 → Φ5 may require Isagi v1 → v2 because the new
  fusion sweep needs primitives v1 cannot express). Phase triggers
  are pre-declared; they are not "I felt like evolving now."
- **Inspiration trigger.** Another striker's reasoning in the Thought
  Ledger reveals a possibility that the agent's vN architecture
  *cannot express*. The inspiration is a structural absence, not a
  parameter tweak. (If vN could express the new behaviour by changing
  a hyperparameter, the answer is to retune vN, not to ship vN+1.)

vN+1 is not "vN with more parameters." It is a *named architectural
generation* with a documented defeat behind it. The retention rule in
`07-research-standards.md` §3 applies: vN is not deleted when vN+1
ships — both are preserved so the ablation has a clean A/B.

#### 3.11.2 The contract for any vN → vN+1

Six binding deliverables before vN+1 is allowed to enter a phase-gate
evaluation. Missing any one of them means the evolution has not
happened — vN is still the canonical agent.

1. **Defeat documented.** A note in `reviews/<agent_id>_vN_defeat.md`
   citing the failure mode by trade IDs, ΔInfo windows, or
   regime-bucket TQS rows. "vN underperformed" is not documentation;
   "vN's `zone_d1_against` detector missed 73 % of 2024 vol-expansion
   setups, audit §2.4 row 4" is.
2. **Evolution hypothesis stated explicitly.** A one-paragraph
   declaration: *what new capability vN+1 adds*; *what failure it
   should resolve*; *what it must NOT regress*. Stated **before**
   vN+1 is implemented (no post-hoc retconning).
3. **New code surface, cleanly named.** `sim/agents/aXX_<name>_v2.py`
   sits next to `sim/agents/aXX_<name>_v1.py` (or wherever vN lives).
   No in-place mutation of vN's module. The diff is *additive* at the
   file-system level.
4. **Regression test that vN+1 reproduces vN behaviour** on the inputs
   vN handled correctly. The regression suite lives at
   `sim/tests/test_<agent_id>_v2_regression.py` and asserts byte
   identity (or documented permitted divergence) on a frozen panel of
   trades vN took. No silent regressions are allowed to slip through
   as "v2 improvements."
5. **Forward test that vN+1 resolves the defeat trigger** on the same
   evaluation window where vN failed. The forward test lives at
   `sim/tests/test_<agent_id>_v2_resolves_<defeat_id>.py` and asserts
   the named failure no longer fires (or fires with measurably reduced
   frequency, with the threshold pre-declared in step 2).
6. **Both versions co-exist** in `sim/roster/`. The ablation can swap
   `aXX_<name>_v1` and `aXX_<name>_v2` via config (per
   `09-experiment-architecture.md` §1.10). **This is how F17 ΔInfo
   gets a clean A/B for the evolution itself** — the same agent
   identity at two versions, on the same sealed panel, with all
   other roster members fixed.

**Coexistence period.** vN and vN+1 run side-by-side for **at least
one full phase gate** before vN is retired. Retirement requires a
written decision in the evolution ledger (§3.11.4), not a silent
deletion. Per `07-research-standards.md` §3, nothing is deleted from
git history anyway — but the *roster* keeps vN as an option until
the gate's worth of evidence says vN+1 dominates across all regime
buckets vN owned.

#### 3.11.3 Per-agent evolution sketches (initial, refined as defeats accumulate)

These sketches are **starters**, not contracts. Each entry below
records the *expected* first defeat trigger and the *initial*
hypothesis for vN+1 — informed by canon and by the E001–E007
empirical priors in `audits/2026-06-24_E001-E007_audit.md` §4.3.
Real defeats land in `reviews/evolution_ledger.md` as they happen;
that file, not this section, is the binding record. The sketches
exist to make the principle concrete and to give each agent's spec
a starting point.

- **A1 Isagi v1 → v2 — metavision sharpens.** *Defeat (expected):*
  Isagi v1 misses setups outside the `zone_d1_against` vocabulary —
  specifically the IRL/ERL liquidity sweeps and FVG fills that the
  canon "metavision evolved form" can read. *v2 hypothesis:* expand
  the primitive vocabulary via `conflab/detectors_liquidity.py`
  (`equal_highs_pool`, `equal_lows_pool`, `liquidity_sweep_high`,
  `liquidity_sweep_low`) and FVG/OB detectors; coordinate-emission
  cadence moves from H4 to H1. *Inspiration:* Isagi's metavision
  evolving through the Wild Card and U-20 arcs from raw spatial
  perception into full order-flow reading.
- **A2 Bachira v1 → v2 — narrowed rebel-lift (peer-silence /
  peer-disagreement-conditional).** *Defeat (Φ4.1):* v1 rebel-lift
  fired 46,584 times unconditionally, slot-cannibalising Isagi
  (0 trades) and Barou (0 trades) across all three Φ4.1 symbols
  and producing 76 % of squad trades (2,840 / 3,714). The v0.3
  sketch's spirit ("peer-silence") was correct but v1 implements
  the opposite (peer-saturation). *v2 hypothesis:* the rebel-lift
  from 0.65 to 0.75 fires only when (a) no Isagi/Barou prior-tick
  Thought at conviction ≥ 0.70 exists on the same symbol OR (b)
  at least one peer (Isagi/Barou/Rin) has a prior-tick Thought
  at conviction ≥ 0.65 going the OPPOSITE direction on the same
  symbol. Otherwise Bachira's base baseline-zone Thought stays at
  0.65. *Defeat trigger:* Bachira v2 per-OOS-window trade count
  drops below 200 OR Bachira's mean TQS regresses below 0.25
  (Φ4.1 was 0.308) across ≥ 4 of 7 rolling OOS windows. Resolution
  detail: `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md`
  §1.
- **A3 Rin v1 → v2 — regime-gated and peer-disagreement-gated
  precision lift.** *Defeat (Φ4.1):* v1 precision-lift fired
  3,094 times; Rin opened 244 trades at mean +9.95 / median
  −28.26 pips (fat-right-tail; 35.7 % win rate). The v0.3 sketch
  proposed regime-gating to `{trending, vol_spike}` but the
  2026-06-24 regime redesign RETIRED `vol_spike` + `news` on
  structural grounds — live-classes are `{trending, chop}` only.
  *v2 hypothesis:* the precision-lift fires only when (a)
  classifier label = `trending` AND (b) v1's R:R ≥ 2.5 + stop-
  distance ≥ 20 pips filter passes (retained) AND (c) at least
  one peer (Chigiri or Bachira) has a prior-tick Thought at
  conviction ≥ 0.65 going the OPPOSITE direction on the same
  bar. Otherwise Rin's base zone_d1_against Thought stays at
  0.65 (no lift). *Defeat trigger:* Rin v2 mean TQS regresses
  below 0.25 OR win rate falls below 30 % across ≥ 4 of 7
  rolling OOS windows. Resolution detail:
  `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §2.
- **A4 Chigiri v1 → v2 — multi-TF ADX alignment + top-decile σ
  floor.** *Defeat (Φ4.1):* v1 breakout-firing produced 3,615
  Thoughts → 536 trades at +6.62 mean / −26.67 median pips, win
  39.9 %, TQS 0.229 (lowest among trading agents). The v0.3
  sketch ("continuation-only, never retest") is already in v1
  — the active defeat is whipsaw losses on early-stage σ
  expansions. *v2 hypothesis:* continuation requires (a) M15
  close beyond 20-bar high/low (v1, retained) AND (b) M15-ADX
  × H1-ADX × H4-ADX all rising on the same bar (replaces v1's
  H1-ADX-only) AND (c) realised σ_M15 over trailing 10 bars in
  the top-decile of trailing 80-bar distribution (replaces v1's
  > 1.2× median ≈ top-quartile). Three conjunctive guards
  filter out false starts that drove the Φ4.1 median-negative
  profile. *Defeat trigger:* win rate stays below 40 % AND mean
  TQS regresses below 0.20 across ≥ 4 of 7 rolling OOS windows.
  Resolution detail: `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md`
  §3.
- **A5 Reo v1 → v2 — chemistry, not mimicry (HRP mixture) +
  second-position proposer (Φ5-coupled).** *Defeat (Φ4.1):* v1
  ships the mirror-Thought emitter without `intend()` — the
  structural Tier-2 falsifier; 28,469 mirror Thoughts emitted,
  0 trades. Falsifier worked but Reo never participates in
  capital allocation. *v2 hypothesis — stacked mechanics:*
  **(1)** HRP-weighted mixture of top-K (≥ 2) trailing-TQS
  agents — Reo computes HRP weights over the trailing-K-week
  TQS series for OTHER strikers; the mixture defines whose
  coordinate(s) Reo mirrors. **(2)** Second-position proposer
  under Φ5 multi-position policy (Arm 4 / K = 2) — Reo's mirror
  Thought becomes a Proposal for the second-best leader's
  coordinate at HRP-derived size when the first-best leader's
  slot is contested. Both slots respect Φ5 PROTOCOL §3 Arm 4's
  `total_risk_cap_per_symbol = 1.0%`. *Φ5 dependency:* mechanic
  2 is gated on Φ5 Arm 4 landing (multi-position policy); if Arm
  4 is deferred, mechanic 2 defers with it and Reo remains
  mirror-only. Mechanic 1 stands independently of Φ5. *Defeat
  trigger:* mechanic 1 retires if F17 ΔInfo ≤ 0 with 95 % CI
  lower bound ≤ 0 (Reo cut from roster); mechanic 2 retires if
  second-position trades' per-window mean TQS is ≥ 0.05 below
  first-position leader's mean TQS across ≥ 4 of 7 rolling OOS
  windows. Resolution detail:
  `reviews/v2_arc_backlog_resolution_round2_2026-06-30.md` §4.
- **A6 Nagi v1 — canonical (Φ4.1-validated); v2 sketch retired.**
  Empirical: Φ4.1 telemetry shows the v1 confluence floor (2-distinct
  peers × shared tags × overlapping coordinate × matching direction)
  is **correct as-shipped**. With peer fuel (Bachira rebel-lift,
  Rin precision-lift, Reo mirror Thoughts) Nagi fired 34,302
  confluence-firing Thoughts → 645 proposals → 94 trades at mean
  **TQS 0.349 (highest per-agent TQS in the 8-agent squad)**.
  Relaxing the floor would make Nagi less canonical, not more.
  *Defeat trigger (replaces "fires too rarely"):* Nagi's per-OOS-
  window mean TQS regresses below the median of all other proposing
  strikers in ≥ 2 of 3 regime buckets (trend / range / vol-expansion
  event) across ≥ 4 of 7 rolling OOS windows on the locked walk-
  forward panel. *v2 status:* deferred indefinitely until that
  regression appears in the squad-gate harness. The sketch is
  retired in `reviews/v2_arc_backlog_resolution_2026-06-25.md`
  §1; the v1 module is canonical.
- **A7 Barou v1 → v2 — devour replays Isagi's losses (Tier-1
  asynchronous, mechanic A) + symbol-whitelist expansion to
  EURUSD/GBPUSD/USDCAD baseline-zone (mechanic B). HYBRID A+B per
  user decision 2026-06-30.** *Defeat:* the v1 live-ledger devour
  mechanic fired 0 times in 11 years across Φ4 + Φ4.1 (2 of 2 runs).
  Root cause #1 (Φ4): live disagreement between Isagi (USDCAD
  zone × D1-against) and Barou (USDCAD baseline zone, no D1 gate) is
  architecturally rare — they target different setups on the only
  shared symbol. Root cause #2 (Φ4.1): Barou opened **0 trades** on
  the expanded roster — fully slot-cannibalised by Bachira's `+0.10`
  rebel-lift on every USDCAD signal tick (`phi41_squad_v1.md` engine
  telemetry + addendum §1). *v2 hypothesis — stacked A + B:*
  **(A)** devour reads Isagi's **closed losing trades** (Tier-1
  post-fact data) from the public ledger; when a closed Isagi loss
  lands in Barou's coordinate space (USDCAD, last 24 H4 bars, inside
  or within 1 ATR of a baseline-zone touch Barou would have
  proposed), Barou's NEXT-bar proposal conviction gets a `+0.10`
  lift (cap 1.0). Closed trades are Tier-1 public per §3.9 row 1;
  the thought-reading layer stays asynchronous and Tier-3-compatible.
  **(B)** Barou's symbol whitelist expands from `("USDCAD",)` to
  `("USDCAD", "EURUSD", "GBPUSD")` running baseline-zone (no D1
  gate). USDCAD remains canonical specialty per E005 audit §2.5
  (inverse asymmetry on baseline vs D1-against); EURUSD + GBPUSD are
  added explicitly to contest Bachira's slot dominance and surface
  live-disagreement opportunities where mechanic A can also fire.
  The devour lift remains USDCAD-only — EURUSD/GBPUSD slice runs raw
  baseline-zone without the lift. *Lookback:* 24 H4 bars (locked for
  v2; tunable in Φ5). *Defeat trigger replacement (conjunction):*
  live-ledger devour 0-fires retired; v2 defeat trigger is "Barou v2
  produces (i) ≥ 100 devour-fire events on the 11-yr USDCAD H4 panel
  AND (ii) ≥ 50 trades opened on EURUSD or GBPUSD combined". Either
  half of the conjunction failing retires that half (mechanic A or
  mechanic B) while the surviving half continues as a narrower v2.
  Resolution detail: `reviews/v2_arc_backlog_resolution_2026-06-25.md`
  §2 + 2026-06-30 amendment.
- **A8 Yukimiya v1 → v2 — sharper hands.** *Defeat (expected):*
  execution-timing improvements are small without friction context —
  v1 refines fills in isolation and the gains do not survive the
  simulator's calibrated friction (§1.8 in `09-experiment-architecture.md`).
  *v2 hypothesis:* Yukimiya uses the E007 friction-quartile cutoffs
  (`conflab/friction.py`, Q1/Q2 = −1.1916, Q2/Q3 = −0.2472,
  Q3/Q4 = +0.9864 per audit §4.1) to **filter low-quality entries
  before commit** — refusing fills below the bottom-friction-quartile
  threshold. *Inspiration:* Yukimiya's growth from supporting forward
  to clinical finisher.
- **A9 Aoshi v1 → v2 — calendar-aware vol.** *Defeat (expected):*
  vol-event detection without news context produces false positives
  at non-news vol spikes (random liquidity holes mis-classified as
  FOMC-style events). *v2 hypothesis:* Aoshi reads the production
  forex calendar (`agent/news/calendar.py` in `multi-pair-trading-agent`)
  via PYTHONPATH-only consumption per `sim/README.md`; vol-events
  without news context become **observation-only** thoughts, never
  proposals. *Inspiration:* Aoshi as captain — situational awareness
  over raw signal.
- **A10 Kunigami v1 → v2 — gentle giant (`status: v2-wired 2026-06-
  30, Sentinel R5 consumer online`).** *Defeat (expected, retained):*
  loss-streak dampener fires post-fact — three losses before the
  half-size kicks in. *v2 mechanic (WIRED 2026-06-30 as part of
  Φ4.2 mini-sprint):* Sentinel R5 now polls
  `A10KunigamiV1.warning_active_at(as_of)` on every accepted
  proposal via `SentinelContext.kunigami_loss_streak_active`. When
  Kunigami's rolling 5-trade loss-streak window fires (`3+ losses
  out of last 5 at conviction ≥ 0.70`), R5 activates for the next
  24 h and journals to `sentinel_log` (audit-only in Φ4 / Φ4.1
  replays; physically blocking in the Φ5 harness via
  `sentinel_blocks=True`). Kunigami v1's 25,877 warning Thoughts
  at Φ4.1 (previously 0 consumed) are now the Sentinel's authoritative
  R5 input. *v2 hypothesis (retained for future v3):* read forward-
  looking ledger confidence aggregates (low aggregate conviction ×
  high pairwise correlation) and dampen **pre-emptively**, before
  the third loss lands. *Pre-condition for v3 revisit:* (1) ≥ 100
  OOS-window Sentinel-fire observations across `{trending, chop}`
  regime buckets (post-`vol_spike`+`news` retirement 2026-06-24);
  (2) v1-wired baseline frequency-of-fire established in the Φ5
  aggregator gate report. Wiring detail: `sim/core/sentinel.py`
  (R6 + `evaluate_proposal` helper + extended `SentinelContext`),
  `sim/scoring/run_phi4_squad_gate.py::_drive_squad_replay`,
  `sim/tests/test_sentinel_wired.py`, and
  `experiments/phi5_aggregator/PROTOCOL.md` §11.1 amendment.
  Resolution detail: `reviews/v2_arc_backlog_resolution_2026-06-25.md`
  §3.

Each sketch above is provisional. The actual defeat triggers will be
the ones the ledger records — perhaps a different failure surfaces
first for some agent, perhaps an inspiration trigger fires before a
defeat trigger does, perhaps a phase gate forces an evolution the
sketch did not anticipate. Future-you should treat this section as
*priors*, not *commitments*, and update the evolution ledger from
evidence rather than from this list.

#### 3.11.5 Versioning discipline (2026-07-01 clarification)

The §3.11.1–§3.11.4 framework describes *what a vN → vN+1 transition
costs*. This subsection defines *what qualifies as v1 in the first
place* — a piece of scaffolding that was implicit in v0.1–v0.4 and
made ambiguous by the 2026-06-25 and 2026-06-30 backlog resolutions.

**v1 checkpoint definition.** An agent is at v1 when **all of** these
hold on the locked walk-forward panel (checked by G7 gate):

1. **Undeniable per-agent positive result.** Mean TQS ≥ 0.30 and
   per-window mean TQS ≥ 0.20 in at least 5 of 7 rolling OOS windows
   *or* an explicit "structural falsifier" role that the doctrine
   has declared valid (e.g. Reo as Tier-2 falsifier per §3.10, whose
   0-trade design was intentional).
2. **Positive-sum chemistry contribution.** With the agent in the
   squad, at least one *other* agent's mean TQS or trade count
   strictly improves vs the same squad minus this agent (bootstrap
   CI lower bound > 0 at α = 0.05).
3. **Non-cannibalising slot behaviour.** The agent does not reduce
   any single peer's trade count by more than 50 % in ≥ 4 of 7
   rolling OOS windows via slot cannibalisation on shared symbols.
   (Bachira v1's rebel-lift firing 46,584 times and pushing Isagi +
   Barou to 0 trades in Φ4.1 is the falsifier for this criterion —
   it is why Bachira is *not* at v1 despite positive solo TQS.)
4. **Reasoning-workspace participation (F21).** The agent both
   *publishes* to and *reads from* the shared reasoning workspace
   (§4.1a). An agent that only publishes is a specialist-in-silo;
   the doctrine requires chemistry-capable v1s.
5. **Owned lot-size cognition (F19).** The agent implements a
   non-trivial `lot_intent(conviction, sl_pips, equity, regime_fit)
   → lot_size` — not the fixed-lot default. Sizing is part of the
   "beautiful goal" equation (TP + SL + smoothness + speed + size),
   not a global constant.
6. **Owned risk-shape cognition (F20).** The agent implements a
   non-trivial `risk_intent(conviction, atr_pips, h1_swing_pips) →
   (sl_pips, tp_ladder)` — not the default 40-pip stop. Different
   playstyles produce different SL/TP shapes.

**v2 definition (unchanged from §3.11.1).** A named architectural
addition that empirically trumps a proven v1 on the same panel by
pre-declared margins.

**Squad chemistry mandate.** The v1 checkpoint is a squad-level gate
(G7), not a per-agent gate. All 8 implemented v1s (A1 Isagi, A2
Bachira, A3 Rin, A4 Chigiri, A5 Reo, A6 Nagi, A7 Barou, A10 Kunigami)
must clear G7 as a group before any agent is authorised for a v2 arc.
This operationalises the "cogs in a wheel" framing — no single agent
gets to evolve past v1 while the squad is broken. See
`experiments/G7_v1_checkpoint_gate/PROTOCOL.md` for the formal
statistic, panel, and pass criterion.

**Reclassification of the 2026-06-25 / 2026-06-30 backlog resolutions.**
The six resolutions listed in §3.11.3 that were labelled "v1 → v2"
are — under §3.11.5 — reclassified as **v1 mechanic iterations
pending G7**:

| Agent | Previously labelled | Reclassified as |
|---|---|---|
| A2 Bachira | v2 REFINE-to-peer-silence | v1 mechanic-iteration-1 (peer-silence gate on rebel-lift) |
| A3 Rin | v2 REFINE-regime+peer-disagreement | v1 mechanic-iteration-1 (regime-gate to `trending` + peer-disagreement) |
| A4 Chigiri | v2 REFINE-multi-TF-ADX+ATR-percentile | v1 mechanic-iteration-1 (three conjunctive guards) |
| A5 Reo | v2 ADVANCE-coupled-to-Φ5-multi-position | v1 mechanic-iteration-1 (HRP mixture); mechanic 2 (second-position) deferred to post-G7 |
| A7 Barou | v2 REDESIGN-hybrid-A+B | v1 mechanic-iteration-1 (hybrid A + B) |
| A10 Kunigami | v2 WIRED (Sentinel R5 consumer) | v1 primitive (`warning_active_at` is a v1 feature; Sentinel R5 consumption is Sentinel-side plumbing, not agent evolution) |

The v2 label survives on:

- A1 Isagi v2 (archived) — the only true v2 attempt to date, FAILED
  per `reviews/isagi_v2_arc.md`. Retained on disk per §3.11.2 step 3.

**Retroactive ledger discipline.** The evolution ledger rows for the
six reclassifications above receive companion **RELABEL-2026-07-01**
rows citing this subsection as the authoritative source of the
reclassification. The original v2-labelled rows are *not deleted* per
`07-research-standards.md` §3 — they remain in the ledger as
historical prior-art with an "amended by RELABEL-2026-07-01"
annotation.

**Why this reframe now.** Session 2026-07-01 Phase 6d partial verdict
showed Arm 2 (TQS-conditional conviction floor) lifting squad TQS by
+0.0187 without any v2 arc — the aggregator lever works. The user's
2026-07-01 decision was: *don't stack v2 evolutions on top of a broken
v1 squad; make the squad's v1s work like cogs in a wheel first*. F19,
F20, F21 are the primitives the doctrine was missing to make that
possible.

#### 3.11.4 The evolution ledger

The audit trail for the doctrine. Every actual `vN → vN+1` event
lands in `programs/M001_multi_agent_ensemble/reviews/evolution_ledger.md`
as a dated row, with:

- Date and program phase at the time of evolution
- Agent ID and version transition (`isagi_yoichi v1 → v2`)
- Defeat trigger (one line) + evidence link (`reviews/<file>.md` or
  trade-ID range)
- Evolution hypothesis (one line, copied from `reviews/<agent_id>_vN_defeat.md`)
- Co-existence window declared (which phase gate retires vN, if any)
- Eventual outcome (filled in after the co-existence window closes:
  v2 supersedes v1, v2 abandoned and v1 retained, or both kept as
  regime-conditional siblings)

The ledger is the *proof that evolutions are earned, not asserted*.
A vN+1 module on disk without a matching ledger row is treated as
research debt — vN remains canonical until the row lands.

The ledger file is also Tier-1 read-only (per §3.9): it is part of
the human dashboard and the post-hoc evaluation harness, never read
by an agent at decision time. The architectural separation between
*how an agent decides today* and *how the agent's identity is allowed
to change tomorrow* is intentional: agents do not get to vote on
their own evolution.

---

## 4. The striker base class (Φ3 stub)

### 4.1 `BlueLockStriker` — the observe / intend split

Every roster agent inherits from `BlueLockStriker`. The class
captures the canonical contract — Thought emission on every tick,
Proposal emission only at home-TF close, KPI reporting weekly —
without prescribing strategy logic. v0.2 splits the v0.1 single
`emit_proposal` entry point into a **two-method protocol**: every
agent always *observes*, only sometimes *intends*.

```python
class BlueLockStriker(Protocol):
    """Base contract for every roster agent.

    Two-method protocol:
      1. `observe` is called every squad tick. Always emits a Thought.
         Tier-3 agents (per §3.9) receive a redacted ledger view
         containing only their own past thoughts; Tier-2 agents receive
         the full ledger subject to the §3.8 guards.
      2. `intend` is called only at the agent's `home_tf` close. May
         return a Proposal or None.

    Weekly KPI reporting (assertion / coexistence / devour / goal /
    beauty, doctrine §3.6) has a default implementation that reads
    from the per-agent journal; weapon-specific overrides allowed.
    """

    agent_id: str
    canon_role: CanonRole           # fixed at Phi0; carries weapon,
                                    # ego, target_hold, canon_player,
                                    # narrative_voice
    home_tf: Timeframe              # primary cadence for `intend`
    symbols: list[Symbol]           # whitelist of tradable symbols

    def observe(
        self,
        market: MarketState,
        ledger: ThoughtLedger,      # full or redacted, per tier
    ) -> Thought:
        """Called every tick. Always emits a Thought. The thought
        may be observation-only (coordinate is None, expected_action
        is None or 'wait'); it is appended to the ledger regardless."""

    def intend(
        self,
        market: MarketState,
        my_recent_thought: Thought,  # this tick's own observation
    ) -> AgentProposal | None:
        """Called only at home_tf close. May return a full Proposal
        if the agent's A+ score (§3.7) clears its threshold and a
        trigger fires inside an active coordinate; else None."""

    def report_kpis(self, week_id: str) -> dict:
        """Default implementation reads from the journal and computes
        assertion / coexistence / devour / goal / beauty. Subclasses
        only override for weapon-specific metrics."""
```

Decoupling observation from intention means the ledger captures the
*evolution* of each agent's view, not just its final decisions.
Canonical Blue Lock: players constantly observe the pitch; they only
*intend* when an opportunity crystallises. v0.1's `emit_proposal`
collapsed these two beats into one and lost everything in between.

The base class lives at `sim/striker.py` (Φ3). Existing
`SupplyDemandAlpha` is wrapped into `IsagiYoichi(BlueLockStriker)`
as the seeded first agent — its v0.1 `emit_proposal` becomes
`intend`, and a new `observe` is written that emits a `Thought` per
H1 close with tags `["zone_d1_against", "h4_close", ...]` and
`coordinate = None` on most ticks. See `05-agent-roster-v0.md` for
full character roster.

### 4.1a v1 chemistry primitives (F19 / F20 / F21) — added 2026-07-01

The §3.11.5 v1 checkpoint definition requires per-agent lot cognition
(F19), per-agent risk-shape cognition (F20), and squad-shared
reasoning-workspace participation (F21). These extend the
`BlueLockStriker` protocol above with three new methods; they are v1
primitives, not v2 capability additions. Prior to the 2026-07-01
reframe, `FIXED_LOT = 0.1` and a global `40-pip default stop` were
implicit in the sim harness, and cross-agent chemistry lived only in
the §3.3 Aggregator confluence-detection layer. §4.1a moves all three
into the agent's own decision surface.

```python
class BlueLockStriker(Protocol):  # extends §4.1 above
    ...

    def lot_intent(
        self,
        conviction: float,
        sl_pips: float,
        equity: float,
        regime_fit: float,
    ) -> float:
        """F19 -- agent-owned position sizing. Returns lot size (lots).
        Sentinel R1 (min-lot floor) and R6 (per-symbol total-risk cap)
        apply as backstops after the agent's decision. Default returns
        FIXED_LOT (0.1); agents override with playstyle logic."""

    def risk_intent(
        self,
        conviction: float,
        atr_pips: float,
        h1_swing_pips: float,
    ) -> tuple[float, list[float]]:
        """F20 -- agent-owned SL/TP shape. Returns (sl_pips, tp_ladder).
        Default: (40.0, [80.0]) -- 1:2 R:R with single TP. Agents
        override with playstyle logic (Isagi wide-stop zone-fade shape,
        Bachira tight-stop pattern shape, etc.)."""

    def read_workspace(
        self,
        workspace: ReasoningWorkspace,
        as_of: datetime,
    ) -> list[Thought]:
        """F21 -- read peers' Thoughts published at prior ticks.
        Backwards-only reads (§3.8 references guard). Default returns
        all peer Thoughts published before `as_of` in the same tick
        group. Agents override with agent-specific filters (Isagi
        reads confluence hints, Bachira reads timeframe-adaptation
        signals, Reo reads all-of-them for HRP mixture)."""
```

The `ReasoningWorkspace` dataclass is a per-tick immutable snapshot
of the Thought Ledger that every agent gets read access to before
its `intend()` runs. It closes the "chemical reaction" loop from
§3.3 — reactions no longer require the Aggregator to detect
confluence *after* proposals are submitted; agents can *anticipate*
confluence during their own decisioning by reading peers' prior-tick
Thoughts.

**Playstyle mapping for the 8 v1 agents.** Each agent's F19 / F20
defaults are set by playstyle (extended from §1 canon-feel egos):

| Agent | Playstyle | Lot-intent shape | Risk-intent shape |
|---|---|---|---|
| A1 Isagi | Conservative-metavision | Lot ∝ confluence-adjusted conviction; downshift when isolated | Wide-stop-tight-TP zone-fade shape (SL ≈ 40 pips, TP1 ≈ 60 pips) |
| A2 Bachira | Rebel-tight | Small lot when peer-silence gate active; standard otherwise | Tight-stop-wide-TP pattern shape (SL ≈ 20 pips, TP1 ≈ 60 pips) |
| A3 Rin | Analytical-precision | Larger lot on peer-disagreement, else standard | Structural-SL + Fibonacci-ratio TP ladder (SL ≈ 25 pips, TP ladder [50, 100, 150] pips) |
| A4 Chigiri | Speed-momentum | Larger lot on multi-TF ADX confluence, else standard | Tight-trailing-stop shape (SL ≈ 30 pips, TP1 ≈ 90 pips, trailed) |
| A5 Reo | Copier-HRP | HRP-weighted mixture of top-K peer lot intents | HRP-weighted mixture of top-K peer risk intents |
| A6 Nagi | Confluence-only | Larger lot on 2+ peer overlap, else refuses | Structural-cleanliness-driven SL/TP (SL ≈ 30 pips, TP1 ≈ 90 pips) |
| A7 Barou | Solo-king | Standard lot on all trades; single-symbol devour lift | Tight-stop-wide-TP baseline-zone shape (SL ≈ 30 pips, TP ladder [50, 100]) |
| A10 Kunigami | Defensive | 0.5× lot when own `warning_active_at` fires, else standard | Standard 40-pip SL; warning fires → refuse the trade |

Defaults live in `sim/agents/aXX_<name>.py::lot_intent` and
`::risk_intent` implementations. Playstyle values are v1 features and
must not be tuned to the panel post-hoc (per `07-research-standards.md`
§3). Agents A8 Yukimiya and A9 Aoshi remain not-yet-implemented; when
they land, they receive their own F19/F20/F21 defaults per their
canon playstyles.

**Interaction with §4.3 Sentinel rules.** F19 produces a *desired* lot
size, and F20 produces a *desired* SL/TP shape. The Sentinel R-rules
still apply *after* the agent's cognition:

- R1 blocks the trade if the F20-produced SL implies risk > 5 % of
  equity at F19's lot size.
- R2 rounds F19's fractional lot down to the min-lot multiple.
- R4 caps any single agent's *actual* risk share at 40 % of the tick's
  budget (F19 producing an unusually large lot on high conviction is
  fine; four agents each producing a large lot on the same symbol is
  what R4 catches).
- R6 caps the *combined* per-symbol risk across all admitted positions
  at 1 % of equity (built for Φ5 Arm 4 multi-position).

The agent's cognition is *not* a Sentinel override; it is the *first
line* of risk decision. The Sentinel is the last line.

### 4.1b Phase U — Shadow ledger (diagnostic-only, 2026-07-01 amendment)

The `TradeRecord` stream captures who WON the aggregator on each
tick — a striker-record view. But that stream cannot distinguish an
agent whose alpha is bad (retire) from an agent whose alpha is fine
but whose slot is crowded by a peer with a stronger signal
(evolve). The shadow ledger closes that gap without touching the
v1 checkpoint criteria.

**Blue-Lock canon frame.** In the 2nd and 3rd selection matches,
scouts credit players who *read* plays that ended in goals, even
when they weren't the striker who scored. Bachira's misdirection
setting up Isagi at the 3rd selection, Nikki's read of Sae's
backspin at U20 — the read is a measurable skill separate from the
finish. Rin and Isagi in the U-20 vs Blue-Lock arc explicitly
devour each other: Rin's precision forced Isagi to sharpen
metavision, Isagi's Neo-Egoist reads pushed Rin toward one-touch
play. They *need* each other's presence to evolve. The shadow
ledger is the scouting record that lets us see that evolution
happening even when only one of them holds the striker slot on a
given tick.

**Primitive.** For every proposal produced by any agent on any
tick — accepted or rejected — the sim optionally emits one
`ShadowTradeRecord` (`sim/scoring/shadow_ledger.py`). The record is
produced by re-running the proposal through the same
`_open_trade_from_proposal` + `_check_exit` engine as executed
trades, on the same symbol's bar stream, in isolation from the
per-symbol single-position rule and the R6 total-risk cap. Each
record carries an attribution provenance triple:

- `is_shadow: True` — always, for records in the shadow stream.
- `proposal_tick_id` — the tick the proposal fired on; used to join
  back to `TradeRecord.source_tick_id` for the executed twin.
- `rejection_reason` — the aggregator's routing verdict:
  `"accepted_by_aggregator"` when the proposal also became a real
  trade, `"aggregator_lower_conviction"` when it lost the
  tie-break, or a Sentinel `sentinel_*_block` string when the R-rule
  vetoed it.

**Alpha-attribution signal.** Per-agent, split shadow-TQS into two
subsets:

- **shadow-TQS-when-accepted** — score for proposals that also
  executed. Equals executed-TQS by construction (same fill/exit
  simulation), so this subset is the *calibration proof* of the
  shadow simulator, not a new signal. If the two disagree, the
  shadow simulator has a bug and every downstream inference on
  rejected proposals is untrustworthy.
- **shadow-TQS-when-rejected** — score for proposals the
  aggregator sidelined. THIS is the alpha attribution signal.

The delta `mean(rejected) − mean(accepted)` for the same agent
tells us whether their crowding-out is a design feature or a
routing bug:

| Delta sign | Interpretation | Implication for the agent |
|---|---|---|
| Strongly negative (≤ −0.10) | Aggregator picks winners; rejected proposals are genuinely worse than accepted. | Crowding-out is a design feature. The mechanic is fine; the routing is correct. |
| ~ 0 | Aggregator's tie-break is random with respect to trade quality. | Alpha is real but routed away. Evolve the mechanic toward a peer-disagreement or regime-specialist role that fires *when the peer's signal is absent*, not on the same signal. |
| Strongly positive (≥ +0.10) | Aggregator picks the wrong winners; rejected proposals were the better trades. | Routing bug. Fix the tier bias / conviction lift / regime_fit weighting in the aggregator itself before touching the agent. |

**Diagnostic-only for v1.** Shadow-TQS never moves an agent's
§3.11.5 6-bit `bachira/isagi/rin/…` vector. All six criteria remain
scored on **executed** trades. Shadow-TQS is emitted as an
appendix on every G7 verdict (`shadow_by_agent` JSON block +
"Phase U — Shadow ledger" markdown section). Any use of shadow-TQS
for a promotion decision (Φ5 Arm 4 K=2 multi-position lift,
Reo's HRP mixture inputs when peers have zero executed trades)
must be declared as its own doctrine amendment.

**Systematic bias.** Shadow trades face no inter-symbol R6 cap, no
R4 concentration cap, no per-symbol single-position rule. Raw
shadow-TQS is therefore biased upward relative to executed-TQS by
a constant (both the accepted and rejected subsets suffer the same
upward bias, so the DELTA is unbiased). The raw mean shadow-TQS
column in the verdict markdown is context, not the signal — the
signal is always the accepted-vs-rejected delta for the same agent.

**Research-grade per-trade quality metrics.** In addition to the
TQS composition inherited from `sim/scoring/tqs.py`
(`R^0.7 × efficiency × time_score × cleanliness × beauty_bonus`),
each `ShadowTradeRecord` carries three explicit metrics drawn from
the quant literature:

- `entry_efficiency = 1 - MAE / (MAE + initial_risk)` — Kaufman
  and Sweeney entry-quality proxy. In [0, 1]. 1.0 = never went
  against the position; 0.0 = trade immediately underwater by more
  than the initial risk.
- `exit_efficiency = pnl / max(MFE, 1)` — Kaufman exit-quality
  proxy. In (−∞, 1]. 1.0 = captured the peak; 0.0 = closed at
  breakeven despite favourable excursion; negative = closed at loss
  despite favourable excursion (nursed a bad exit).
- `friction_ratio = |commission| / max(|pnl|, 1)` — Almgren-Chriss
  implementation-shortfall proxy (retail forex has no material
  market impact, so we approximate as commission-over-pnl). Small
  (< 0.05) means costs are negligible; large (> 0.20) means the
  trade barely covered its own costs.

These three complement the existing TQS composition; they are
per-trade values, aggregated to per-agent means on the shadow
aggregate. Reproducibility is captured via the per-window CV of
shadow-TQS across the walk-forward panel.

### 4.1c Phase T-evolve — Rin peer-yield-and-lift (2026-07-01 amendment)

**Trigger.** Phase S walk-forward rerun showed Rin regressing to 0
trades across all 7 OOS windows: her `analytical_precision`
playstyle is a *strict subset filter* on the same
`SupplyDemandAlpha` source Isagi wraps, and Isagi's Phase-S
metavision lift plus tier-1 aggregator bias consistently wins the
tie-break on every shared tick. Phase U's dry-run seed confirmed:
Rin fires 211 shadow proposals with mean shadow-TQS 0.254, zero of
which execute (`n_shadow_accepted=0`, `n_shadow_rejected=211`).

**Canonical framing.** In the Blue-Lock canon, Rin and Isagi
devour each other by evolving into *different* modes on the same
pitch. Isagi's Neo-Egoist metavision is a *confluence-driven*
weapon — it fires HARDER when peers align. Rin's precision
geometry is a *solitude-driven* weapon — it should fire HARDER
when peers are absent or contradictory. The retire-and-replace
reading of Phase S was rejected by the user: Rin doesn't retire;
she finds *something new in herself* to score more goals than
Isagi. Peer-yield-and-lift is that "something new".

**Mechanic (Rin v1.1).** In `intend()`:

1. Read peer thoughts on the same symbol from the F21 workspace
   snapshot. Compute `peer_agree_count` (peers whose
   `direction_bias` matches Rin's proposed direction) and
   `peer_disagree_count` (peers whose direction opposes hers),
   restricted to peers with a non-None `Coordinate`.
2. Compute `isagi_would_lift_metavision = (peer_agree_count >= 1
   and peer_disagree_count == 0)`. This mirrors the exact
   trigger condition of `isagi_metavision_lift` (§4.1 F19).
3. **Yield rule.** If `isagi_would_lift_metavision` is True, Rin
   returns `None` from `intend()`. She cedes the shot to Isagi
   because his metavision lift + tier-1 bias will win the
   aggregator on any tick where peers are aligned.
4. **Lone-read lift rule.** Otherwise (peers disagree, or all
   quiet), Rin adds `RIN_V1_LONE_READ_LIFT = +0.10` to her
   precision-lifted conviction (capped at 1.0). Her total
   conviction reaches 0.65 base + 0.15 precision + 0.10
   lone-read = 0.90, decisively winning against Isagi's base
   0.65 on ticks where his metavision doesn't fire.

**Rationale trail.** The proposal's `rationale` gains six new
fields for post-hoc attribution:

- `peer_agree_count` / `peer_disagree_count` / `peer_seen_count`
- `isagi_would_lift_metavision` (bool)
- `lone_read_lift_applied` (bool)
- `lone_read_lift` (float, always `RIN_V1_LONE_READ_LIFT`)

Plus the pre-existing `isagi_frame_direction` and
`isagi_frame_aligned` are retained for backward compatibility
with G7 C4 audit logs.

**Statistical honesty.** This is a mechanic change after the
Phase S regression was observed — exactly the kind of post-hoc
tuning §07-research-standards forbids on the panel. Two guards
apply:

1. The change is **dated 2026-07-01 evening** and lands in a
   separate commit from the observation that motivated it.
2. Both the **pre-Phase-T** (Rin v1.0, precision filter only) and
   **post-Phase-T** (Rin v1.1, peer-yield-and-lift) walk-forward
   verdicts are archived side-by-side in
   `reviews/g7_v1_checkpoint_verdict_walk-forward-post-U.md` and
   `reviews/g7_v1_checkpoint_verdict_walk-forward-post-TU.md`.
   The narrative report at
   `reviews/2026-07-01_g7_walk_forward_baseline.md` must show
   both numbers with the delta highlighted.

If Phase T-evolve doesn't produce a positive delta (Rin still 0
trades, or worse: crowds Isagi's low-metavision setups without
improving own shadow-TQS), the mechanic reverts and Rin's v1 status
is reported as `PENDING_MECHANIC_ITER_3`. No promotion to Rin v2
is authorised until she scores under this mechanic.

**Interaction with §4.1b Phase U shadow ledger.** Rin's Phase U
scouting report will now contain **both** paired and unpaired
shadow trades (previously all unpaired). The
`mean_shadow_tqs_when_accepted` vs `mean_shadow_tqs_when_rejected`
delta becomes the acceptance test for Phase T-evolve:

- Delta < −0.10 on Rin → Phase T-evolve is a routing win (Rin's
  accepted trades are meaningfully better than her rejected ones,
  proving the peer-yield decision is discriminating).
- Delta ~ 0 → Phase T-evolve gave her routing but not alpha; her
  underlying signal is still just Isagi's subset. Consider a
  further v1.2 evolution (regime-specialist or symbol expansion).
- Delta > 0 → the yield rule is dropping her best trades. Revert.

### 4.1d F22 — workspace richness upgrade (2026-07-02 amendment)

Three cracks in the F21 workspace were named and closed together as
F22 (a/b/c). Every fix ships with a unit test AND a walk-forward
acceptance run.

**Gap 1 — Thought richness.** Pre-F22a, an agent's read was smuggled
through `narrative: str` + `tags: list[str]`. Peers could only string-
match the tag bag to guess signal family; Rin's Phase T-evolve had to
yield on direction alone.

Fix (F22a): new `ThoughtRead` frozen dataclass on
`Thought.read: ThoughtRead | None`. Fields: `signal_family`,
`direction_bias`, `regime_read`, `expected_stop_pips`, `expected_r`,
`driving_evidence`. Canon `SignalFamily` literal covers every roster
agent (metavision / pattern_rebel / precision / breakout /
adaptive_copy / confluence / solo_king / risk_watch / unknown).
`WorkspaceSnapshot.read_for(signal_family=...)` and
`peer_thoughts(signal_family=...)` add a first-class filter, skipping
`read=None` Thoughts. All 8 agents' `observe()` main-signal path
populates `read`; abstention paths keep `read=None` so the filter
correctly excludes them.

**Gap 2 — Same-tick intent visibility (tick-barrier clarification).**
Doctrine sec 3.8 forbids **look-ahead** reads, not same-tick reads
**at the tick barrier**. Pre-F22b the workspace snapshot rule was
strict `tick_id < current_tick`, so every peer Thought published in
Phase 1 (observe) was invisible in Phase 2 (intend). Rin's Phase
T-evolve was reading Isagi's tick T-1 metavision, a systematic
1-tick lag.

Fix (F22b): new `ReasoningWorkspace.snapshot_at_barrier()` method
with rule `tick_id <= current_tick`. Same `timestamp <= as_of`,
`decision_horizon <= as_of`, and future-tick refusal (`tick_id >
current_tick`) guards. Between Phase 1 and Phase 2, every peer
publish for tick T has been committed; reading them in Phase 2 is
committed information, not look-ahead. `_drive_squad_replay` swaps
from `snapshot()` to `snapshot_at_barrier()`. Legacy `snapshot()`
stays for callers that need strict backwards-only (mid-tick ledger
replay, etc.).

**Gap 3 — Interpretation record.** Pre-F22c, `intend()` returned
`AgentProposal | None`. `None` conflated (a) silent no-signal,
(b) inferred yield deferring to a peer, and (c) hard-filter
rejection. Rin's Phase T-evolve yields carried real inferences that
had no audit trail.

Fix (F22c): new `YieldReason` frozen dataclass +
`IntentDecision = AgentProposal | YieldReason | None`. Widened
`BlueLockStriker.intend` protocol return type. Rin's Phase T-evolve
yield now emits `YieldReason(reason="isagi_would_lift_metavision",
peer_ids_read=(...), evidence={...})`. Driver appends every
`YieldReason` to `SquadRunOutput.yields`. Legacy `None` returns are
unchanged and remain "silent".

**Empirical acceptance test.** F22 end-to-end validation lives in
`test_workspace_richness_e2e.py` -- runs a 100-bar synthetic panel
and asserts inference accuracy ≥ 90% (of Rin's metavision-yield
events on tick T, on how many did Isagi's proposal actually carry
`metavision_lift_applied=True`?).

Then walk-forward-post-F22 (7-window OOS) confirms at scale. Rin's
walk-forward-post-TU delta was -0.146 with the STALE-workspace read;
walk-forward-post-F22 measures how much of that was mechanic vs.
workspace-tick-lag.

### 4.2 The Sentinel (Q-doc-5 resolution)

A non-character architectural role. Blue Lock has no canonical
goalkeeper because the league is anti-defensive by design, so this
role stays *outside* the cast — it is not a striker, it is not Ego,
it is not Anri. It is the **Sentinel**.

It is distinct from A10 Kunigami and from the Risk Conductor:

- **Kunigami** triggers on *internal* state (drawdown, loss streak,
  PostLossGuard). He dampens *the squad's own* behaviour after the
  squad has misfired.
- **The Risk Conductor** (Ego's executive arm) enforces hard
  per-trade and per-basket invariants on every order before it
  ships. Always-on, deterministic, narrow.
- **The Sentinel** triggers on *external* shocks the squad cannot
  see from its own journals. It is the circuit breaker for events
  the agents have no weapon against.

**Triggers** (any one fires the Sentinel):

1. Cross-pair realised correlation jumps to `|ρ| > 0.95` on the
   trailing 30-day H1 window — the pairs have merged into one bet.
2. Broker quoted spread on any active pair exceeds 3× the trailing
   week's median spread — liquidity has just left the room.
3. A high-impact calendar event lands within the next 2 hours and
   the prior comparable event produced a regime shift (calendar-
   gated, history-checked).
4. DXY realised σ on the last H1 bar > 2σ above the weekly mean —
   USD shock that contaminates every USD pair simultaneously.

**Effect.** On any trigger:

1. Flatten all open positions immediately (risk-conductor-mediated,
   journalled with the trigger reason).
2. 24h new-entry halt across all symbols.
3. Trigger reason and resolution time persisted via the existing
   state store (same vault as `PostLossGuard`, different key).

**Implementation.** Lives in `sim/sentinel.py` under M001. It is *not*
a `BlueLockStriker` subclass — it has no Coordinate, no proposal, no
TQS. It is an architectural auxiliary that sits between the
Aggregator output and the Risk Conductor's order ladder, with veto
power and an audit log. Operational-translation row added in §2.

### 4.3 Sentinel hard rules for the $100 / 1:1000 account

The Sentinel is not a Blue Lock character; it is the systemic risk
role. The §4.2 triggers handle external shocks (correlation jumps,
spread spikes, calendar events, DXY shocks). The rules below handle
the *account-shape* shocks that are unique to a 0.01-min-lot,
$100-equity, 1:1000-leverage pitch. **Any single violation = trade
blocked.** No agent's conviction overrides a hard rule.

- **R1 — Min-lot risk floor.** If `realised_SL_distance_pips × 0.01
  lot pip_value` exceeds **5 % of current equity**, the trade is
  blocked regardless of conviction. On a $100 account with EURUSD
  pip value ≈ $0.10 at 0.01 lot, the implied max stop distance is
  ~50 pips. Wider stops are not "size down" cases — they are
  *refusals*. The doctrine accepts that some setups become untradable
  at this pitch by design (§6).
- **R2 — Discrete position sizing.** Position sizes are discrete
  (0.01, 0.02, 0.03, …) not continuous. The Capital Allocator's HRP
  weights produce a *desired* fractional lot; the Sentinel rounds to
  the nearest min-lot multiple. **Rounding direction is always "down"**
  (toward smaller risk). 0.017 lot becomes 0.01, not 0.02.
- **R3 — Pass bias.** Most ticks, most agents emit observation-only
  Thoughts (`coordinate = None`, `expected_action = None | "wait"`).
  The expected proposal-rate per agent per day is typically `< 1`.
  The Sentinel's audit log flags any agent whose daily proposal rate
  exceeds 3 — that is over-firing, not edge, and triggers a roster
  review.
- **R4 — Concentration cap.** No single agent receives `> 40 %` of
  risk budget on any tick. This sits *above* the v0.1 HRP allocator's
  35 % cap (architecture §4) as a hard backstop — if an HRP edge
  case produces a 38 % weight, the allocator passes; if a bug
  produces a 60 % weight, the Sentinel blocks.
- **R5 — Loss-streak dampener.** Three consecutive losses → **50 %
  risk-scale** for the next 24 hours, applied to all agents. This is
  distinct from A10 Kunigami's anti-tilt logic (which is an in-cast
  agent and can be overridden by the allocator's confluence boosts);
  R5 is a hard multiplier the Sentinel applies *after* the allocator
  and after Kunigami. Restated: Kunigami dampens his own roster's
  enthusiasm; R5 dampens the *Sentinel's view of* the roster's
  output. The two compound multiplicatively if both fire.

All five rules are deterministic, journalled with the trigger reason
in the same vault as the §4.2 triggers (different key namespace),
and cannot be disabled by any agent. They are the floor below which
"the squad is allowed to play" stops being true.

---

## 5. The opponent — adversarial validation

> "The world doesn't reward kindness." — Ego Jinpachi

The roster is not benchmarked only against itself. It is
benchmarked against **the human discretionary trader** (you).
Every week:

1. **You submit your chart analysis + trades.** Same template as the
   week of 2026-06-15 archive: timeframes, levels, target ladders,
   actual demo / live tickets if any.
2. **The system records these as `human_proposals.jsonl`.** A
   `Coordinate` is reverse-engineered from each submission for
   apples-to-apples comparison with agent coordinates.
3. **Three head-to-head metrics computed (F14):**
   - **PnL head-to-head** — agent ensemble PnL vs human PnL on the
     same chart, normalised to identical capital.
   - **Coverage** — what fraction of human-claimed coordinates did
     *any* agent also claim? (Tests Isagi.)
   - **Counter** — what fraction of human proposals had at least one
     agent take the opposite side that resolved more profitably?
     (Tests adversarial diversity.)

The opponents have names:

- **Michael Kaiser** = your **high-conviction discretionary trades**
  with known target ladders. The ones you'd take if you saw them
  again. Calculated, engineered single-decisive shot.
- **Loki Yuya** = your **adaptive trade selection** — your tendency
  to revise plans mid-week as new information arrives. The
  observation-and-counter style.
- **Nagi (yes, also a striker name; here as the foil)** = your
  **passive setups** — the ones you saw but didn't take. We
  compute their counterfactual P&L too.

The roster wins the season when, over a rolling 12-week window:
- Mean ensemble TQS ≥ mean human TQS, **and**
- Ensemble drawdown ≤ human drawdown × 1.25, **and**
- Coverage of human coordinates ≥ 60 %.

Anything less than that and the system has not yet earned the
right to operate without the human's read.

This is the gate that keeps the work honest. We are not building a
toy that beats a synthetic baseline. We are building something that
has to beat *you*.

---

## 6. The pitch — $100 / 1:1000 demo

The new account profile is a deliberate constraint. Smaller pitch,
sharper play.

- **Equity:** $100 starting balance.
- **Leverage:** 1:1000.
- **Pip values:** 0.01 lot (broker minimum) = $0.10 / pip. 0.10 lot
  = $1.00 / pip.
- **Max margin used (50% safety floor):** ~$50 → ~0.40 lot total
  exposure capacity. (The blow-up margin level on Exness Standard is
  50 %. We hold ourselves to 200 % i.e. 4× safer. So real cap is
  ~0.10 lot total exposure, $1 / pip basket.)

Implications for agent design:

| Constraint | Bites which agents |
|---|---|
| Per-trade risk ≤ 5 % equity = $5.00 → 50 pips max stop on 0.01 lot | Wide-stop H4 zone fades (Isagi v1) lose half their trades to size-floor refusals |
| Per-basket risk ≤ 7 % = $7.00 (sandbox-relaxed; real spec was 2 %) | Cross-pair confluence trades get sized down hard |
| Min lot 0.01 | Any agent whose Kelly cap recommends < 0.01 lot must skip the trade entirely |
| Margin level floor 200 % | Total exposure cannot exceed ~0.10 lot equivalent at any time |

The $100 / 1:1000 pitch will mechanically favour:
- **Tight-stop strategies** (Bachira's pattern triggers, Rin's Fib
  ratios with structural invalidation, Chigiri's breakouts).
- **Sub-H4 timeframes** (15m, 30m, H1).
- **Confluence-only entries** (Nagi's "perfect setup or nothing"
  becomes the highest-survival agent).

It will mechanically punish:
- Wide-stop H4 zone fades without confluence (Isagi v1 alone).
- Multi-pair correlated baskets without explicit hedging (the L3
  failure mode that blew the live $72 account).
- Slow trend-continuation plays that need 3-day holds (Asahi /
  Naruhaya-class agents).

This is exactly what we want from a research environment. The pitch
**enforces the diversity requirement** — agents that can't survive
small-account constraints don't make the squad.

---

## 7. What this doctrine commits us to

Six commitments, each measurable:

1. **Every agent has a Coordinate API.** No agent is allowed to
   trade without first publishing a forward-looking coordinate.
   Validates targeting separately from execution.
2. **TQS, not raw P&L, is the fitness function.** Allocator,
   PBT (Φ5+), and roster culling all consume TQS.
3. **Chemical reactions are detected and rewarded.** Agents earn
   credit not just for solo goals but for participating in
   confluence events that the team scores.
4. **Devour is competitive.** Every week, weights shift toward
   winners; losers survive at a floor. No agent is permanently safe.
5. **The human is the opponent.** Weekly head-to-head benchmark
   against your trades is the canonical evaluation. The system has
   not earned promotion until it beats you over a rolling season.
6. **The pitch shapes the squad.** $100 / 1:1000 is not a budget
   constraint to apologise for; it is the *adversarial environment*
   that proves which agents can play.

If any of these six fail, the doctrine has been violated and we go
back to the drawing board. They are the architectural invariants
this folder defends.

---

## 8. Open questions / canon disputes

The v0.1 open list, resolved.

1. **Q-doc-1 — RESOLVED 2026-06-24:** metavision = *evolved* order-
   flow awareness; Isagi v1 = the existing `zone_d1_against`
   detector as the primitive seed. Training (Φ4+) layers in H1
   volume imbalance, FVG/IRL/ERL detection, market-structure shifts.
   The canon "training arc" is the mechanism by which the seed
   weapon becomes the full metavision. See §1.1.
2. **Q-doc-2 — RESOLVED 2026-06-24:** sparser. Agents emit on their
   own home-TF close (per `05-agent-roster-v0.md`) and only when
   their A+ score (§3.7) crosses their personal threshold. Universal
   H4 cadence is retired.
3. **Q-doc-3 — RESOLVED 2026-06-24:** ego is no longer plucked from
   character feel as a permanent parameter; v0 keeps the character
   values as priors, Φ4+ derives ego as the information ratio of
   each agent's edge versus its peers (§3.1.b). Similarly the devour
   bonus `δ` is no longer a single guess — F15 in
   `04-quant-foundations.md` derives it from TQS autocorrelation, with
   a Φ4 CV sweep as cross-check.
4. **Q-doc-4 — RESOLVED 2026-06-24:** human is evaluated on a
   *demo* account that mirrors the squad's $100 / 1:1000 pitch.
   Apples-to-apples capital. Live-account commentary is welcome in
   the journal but does not enter the C6 calculation.
5. **Q-doc-5 — RESOLVED 2026-06-24:** no goalkeeper character. The
   role is an architectural auxiliary — **the Sentinel** — defined
   in §4.2. Lives outside the cast because Blue Lock canon has no
   goalkeeper worth promoting; defensive containment is a system
   property, not a player.
6. **Q-doc-6 — RESOLVED 2026-06-24:** the A+ score must be
   audit-traceable. Components (regime_fit, conviction,
   confluence_proximity, structural_cleanliness, novelty) are
   journalled with every emitted coordinate, alongside the personal
   threshold and the ego value used. This becomes part of the
   reproducibility manifest required by `07-research-standards.md`
   §2.

Resolved questions stay in the doc as a paper trail. New questions
can be added below the line.

---

## 9. References (forward-pointing)

- Roster instantiating this doctrine: `05-agent-roster-v0.md`
- Architecture (Conductor, Aggregator, Allocator, Thought Ledger, Sentinel placement): `03-architecture-v0-sketch.md`
- Math (TQS, confluence, coordinate overlap, ΔInfo, regime-conditional KPIs): `04-quant-foundations.md` §F11–F18
- Standards (forward-declared schema, evaluation hygiene, data-plane trajectory): `07-research-standards.md` §6, §4, §8
- Dashboard surface (panel inventory, verdict translation, Φ2.5 Streamlit): `08-dashboard-spec.md`
- Charter (C1 numeric gate, discrete sizing, Sentinel rules): `00-charter.md` §7.1–§7.3
- Literature (PBT, MARL, intrinsic motivation, COMA): `02-literature-survey-plan.md` §1.6
- Empirical priors (E001–E007 evidence inheritance): `audits/2026-06-24_E001-E007_audit.md`
- The week that triggered this: `01-week-2026-06-15-archive.md`