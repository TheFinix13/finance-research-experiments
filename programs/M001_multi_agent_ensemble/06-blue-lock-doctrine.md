# 06 — Blue Lock Doctrine

**Status:** `DRAFT v0.2` — 2026-06-24. v0.2 (this revision, second
pass) formalises the **Thought Ledger** as a first-class object
(§3.8), the **three-tier access model** decided empirically by ΔInfo
(§3.9), and the **canon-role vs information-tier** orthogonality
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