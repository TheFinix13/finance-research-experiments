# 07 — Research Standards

**Status:** `DRAFT v0.3` — 2026-06-24. v0.3 adds **§10.6** — the
agent evolution arcs principle and its regression-test contract —
binding the v0.3 doctrine landing (`06-blue-lock-doctrine.md`
§3.11) to standards-grade evaluation: any `vN → vN+1` claim
requires both a regression test (vN+1 reproduces vN on inputs vN
handled) and a forward test (vN+1 resolves the named defeat),
plus a row in `reviews/evolution_ledger.md`. Missing either test
is a code-review failure. The §10 cross-reference table is
renumbered §10.7. v0.2 (below) appended §10.1–§10.5 consolidating
decisions taken after the E001–E007 audit: E010 stays as a
parallel pre-registered lab experiment, M001 agent promotion
stays internal to `programs/M001_*/` (not the E0XX registry),
E008 is skipped, and the verdict registry is hybrid (internal
four-tier vocabulary + Blue Lock dashboard translation).
Critically: the placeholder tier definitions in v0.1 §7.2 / §7.3
(which described Tier 2 as "own + one cluster of peers" and
Tier 3 as "audit-only") are **superseded** by the empirical
ΔInfo-decided model in `06-blue-lock-doctrine.md` §3.9 / F17 of
`04-quant-foundations.md`. §1–§9 are unchanged below to preserve
the v0.1 evidence record; §10 lands the v0.2 + v0.3 deltas.

This doc is the methodological floor that every experiment under
`programs/M001_multi_agent_ensemble/` stands on. Eight sections —
repo structure, naming, branching, evaluation hygiene,
reproducibility, the forward-declared Thought Ledger schema,
acknowledged research debt, and the data-plane trajectory we are
committing to.

It is short by design. Anything that can be a hard rule is a hard
rule; anything provisional is named as such; anything we cannot yet
honour cleanly is in §7 (research debt) so we do not pretend
otherwise.

---

## §1. Repo structure

This research repo (`finance-research-experiments`) is organised
around five top-level concepts:

| Folder | Purpose |
|---|---|
| `programs/` | Long-running research **programs** with their own branch and doctrine. Each program is a multi-month effort owning a question (e.g., "can a multi-agent ensemble beat zone_d1_against on TQS?"). |
| `experiments/` | Short-lived numbered **experiments** under the legacy `E001`–`E007` convention. Each experiment answers one falsifiable question and is sealed. |
| `audits/` | Point-in-time audits of sibling repos (e.g., production-repo state at migration). Read-only artefacts; never re-edited. |
| `output/` | Run artefacts: parquets, JSONLs, checkpoints. Out of git for size unless small. |
| `conflab/` | Ad-hoc scratch space for in-progress notes, hypotheses, dead-end write-ups. Not promoted into `programs/` or `experiments/` until they earn it. |

Cross-reference: `docs/` holds repo-level docs (the README, this
folder's `PROTOCOL_DISCIPLINE.md`, the data ledger). It is not for
program-specific work — that lives inside the program's folder.

**Program scaffold (M001 instance).** Every program folder contains:

```
programs/M001_multi_agent_ensemble/
  README.md            # one-page index; the user lands here first
  00-charter.md        # mandate, success criteria, kill conditions
  01-…archive.md       # historical context the program is reacting to
  02-…lit-survey.md    # references the program builds on
  03-…architecture.md  # how it is built
  04-…foundations.md   # the math the program depends on
  05-…roster.md        # the participants (agents, opponents, baselines)
  06-…doctrine.md      # the philosophical spine
  07-research-standards.md  # this doc
  sim/                 # simulator + agent code
  notebooks/           # exploratory analysis
  reviews/             # sealed evaluation outputs
  opponents/           # adversarial-cohort submissions (per §4)
```

The numbering is significant. `00`–`02` is *what the program is
reacting to*. `03`–`06` is *what the program builds*. `07` is *how
the program is allowed to evaluate itself*. New top-level docs land
as `08`, `09`, … in time order.

---

## §2. Naming conventions

**Programs:** `M001`, `M002`, … . `M` for "multi-agent / program-
scale work". Three digits. First program is `M001_multi_agent_ensemble`.

**Experiments:** `E001`, `E002`, …, three digits, snake_case suffix
(`E001_concept_ablation`, `E007_impulse_origin_bounce`). The
existing experiments at `experiments/E001–E007` define the
convention; new experiments continue at `E008+`.

**Audits:** `YYYY-MM-DD_<short_descriptor>.md` inside
`audits/`, e.g. `2026-06-24_production_repo_audit.md`. Dated so
order is unambiguous; descriptor is grep-friendly.

**Sub-experiment branches inside a program:** named
`programs/<M-id>/<topic>`, e.g. `programs/M001/chigiri-breakout-spec`.
Short-lived. Merge back into the program's long-lived branch (here,
`multi-agent-ensemble`) when the sub-question is answered, then
delete the branch (the work survives on the program branch as
commits; we do not need stale branch refs).

**Run artefacts in `output/`:** `output/<program-or-experiment>/<UTC-timestamp>/`.
Each run gets its own folder; the manifest sidecar (§5) lives next
to its results.

**Result files:** `<stem>.results.parquet` paired with
`<stem>.results.manifest.json`. The matching manifest is part of
the file's identity; a result without its manifest is treated as
undefined (§5).

---

## §3. Branching strategy

Three layers, in increasing volatility:

1. **`main`** — stable, *completed* work only. Every commit on main
   either (a) is a completed program/experiment, (b) is a doc-only
   update with no in-flight implications, or (c) is an audit. Main
   never carries half-finished doctrine or unreviewed code.

2. **Long-lived per-program branches** — one per program. For M001,
   the branch is `multi-agent-ensemble`. The program's whole life
   happens on this branch; it merges into `main` only when the
   program ends (graduated, killed, or paused). Lifespan: months.

3. **Short-lived sub-experiment branches** — branched **off the
   program branch**, not off `main`. Naming per §2. Lifespan: days
   to ~2 weeks. Merge back into the program branch; delete the
   branch ref after merge.

**Tags for snapshots.** Use lightweight tags to mark milestones
inside a program branch. Convention: `<M-id>-<artifact>-<version>`,
e.g. `M001-doctrine-v0.1` once `06-blue-lock-doctrine.md` settles,
`M001-charter-v0.3` for the current charter snapshot. Tags are
cheap; create them generously. They are the safest way to refer to
a doctrine state from another repo.

Production-side tags follow the same convention but live in
`multi-pair-trading-agent`, e.g. the existing
`v2-zone-d1-against-stable-2026-06-24`. Cross-repo references in
docs cite both tag names so the link is unambiguous.

**Retention rule.** Nothing is deleted from history. A dead
sub-experiment becomes a closed branch + a `conflab/` post-mortem,
not a `git push --force`. **Retention is a feature**: the audit
trail is what lets later programs use prior false-starts as
evidence instead of re-running them.

**Push policy.** Pushes to remote require explicit user consent
per session. Branch creation and local commits do not.

---

## §4. Evaluation hygiene

Three rules, all non-negotiable.

### 4.1 Named windows

Every experiment declares its time partition with these exact names:

| Window | Purpose |
|---|---|
| `training_window` | Where parameters / hyperparameters are fitted. |
| `dev_window` | Where decisions are made about which configuration to ship. Inner-CV folds live here. |
| `holdout_window` | Sealed. Touched once per program, at promotion. Outer-CV folds live here. |

Windows are dated start/end UTC and recorded in the manifest. A
window cannot be widened mid-program without bumping the program
charter's status banner and noting the change in the journey doc.

Φ3 of M001 maps to: training_window = 2024-01 → 2025-12;
dev_window = 2026-01 → 2026-05; holdout_window = 2026-06 → 2026-12
(the holdout is the live shadow run, not a backtest slice).

### 4.2 Five-baseline adversarial cohort

The doctrine in `06-blue-lock-doctrine.md` §5 names three
opponents (Kaiser, Loki, Sae). Standards adds two more so the
cohort spans every direction a baseline can come from:

| Opponent | Definition | Role |
|---|---|---|
| **Kaiser** | Human's high-conviction discretionary trades | Aspirational ceiling — what an engaged human peer can do. |
| **Loki** | Human's adaptive mid-week revisions | Anti-pattern ceiling — beats it if the squad refuses to revise reflexively. |
| **Median** | Median agent's solo performance across the roster | Internal floor — the squad must beat its own median agent acting alone. |
| **Random** | Random-direction-with-vol-targeted-size (per `04-quant-foundations.md` discussions) | No-edge null — the significance floor. |
| **Frozen-Sae** | Frozen `zone_d1_against` baseline (the v0 placeholder Sae) | Heritage floor — the squad must not regress from its seed. |

The Sae **composite** baseline (F16) is a separate, competitive
benchmark that the squad must also beat; Frozen-Sae above is the
v0 placeholder retained as the heritage floor and is *not* the
same object as F16. Both are computed weekly.

**Acceptance gates per the doctrine §5 + 00-charter §C1–C7:**

- **MUST beat** Random, Median, Frozen-Sae on TQS over the rolling
  12-week window. Failing any one of these means the squad has not
  earned its complexity.
- **SHOULD approach** Kaiser. Mean-ensemble TQS must converge
  toward mean-Kaiser TQS over the season; the gap is a research
  metric, not a hard gate.
- **MUST stay distant from** Loki. If the squad's TQS series
  becomes highly correlated with Loki's, we are reproducing the
  anti-pattern. Reported as `loki_distance = 1 −
  corr(TQS_squad, TQS_loki)` over the window; gate at `≥ 0.40`.

Loki's role here is not "an opponent to beat" — it is "a
behaviour to *not* converge to". This is the cleanest way to
encode "the squad is not allowed to learn the discretionary
trader's worst habit (reflexive mid-week revision) even if it
looks profitable in-sample".

### 4.3 Regime-conditional KPIs

Every per-agent KPI from `06-blue-lock-doctrine.md` §3.6
(assertion / coexistence / devour-rate / goal-rate / beauty)
is reported **per regime**, not pooled. Pooled numbers are
journalled but the dashboard renders regime-by-regime by default.

Regimes are the four cells of the diversity matrix in
`05-agent-roster-v0.md` §2: Trend, Range, Vol-Expansion Event,
Mean-Revert Range. A KPI without a regime label is not a KPI;
it is a placeholder.

The single concession: TQS itself is reported pooled *and*
per-regime. The pooled number is the headline; the per-regime
breakdown is the diagnosis.

---

## §5. Reproducibility

### 5.1 Seed pinning

Any stochastic component — RL training, baseline B2 (random-
direction baseline), bootstrap sampling, PBT (Φ5+) — must take a
seed as an explicit argument and write it to the manifest. There
is no implicit default seed; calling `np.random.rand()` without a
seeded generator is a code-review failure.

### 5.2 Reproducibility manifest

Every result file must be paired with `<stem>.results.manifest.json`
containing:

```json
{
  "git_sha": "<full sha of the head commit when the run started>",
  "data_sha": "<sha256 of the input parquet bundle>",
  "seed": "<seed passed to RNGs; integer or null if not stochastic>",
  "env_hash": "<sha256 of `pip freeze` output at run-start>",
  "datetime_utc": "<ISO 8601 timestamp of run-start>",
  "author": "<the1finix or the agent_id that emitted the run>",
  "charter_phase": "<one of Phi0..Phi6; Phi2.5 for setup work>",
  "training_window": "<ISO 8601 start>/<ISO 8601 end>",
  "dev_window": "<ISO 8601 start>/<ISO 8601 end>",
  "holdout_window": "<ISO 8601 start>/<ISO 8601 end>"
}
```

The manifest emitter lives at `sim/manifest.py`; no other code
path is allowed to construct the manifest. A result without a
manifest is excluded from any aggregation. A manifest whose
`git_sha` is not in the repo's history is a hard error.

Reference: Sculley et al. (2015), *Hidden Technical Debt in
Machine Learning Systems* (NIPS 2015), Configuration Debt +
Reproducibility Debt sections.

### 5.3 Environment lock files

Every experiment commits a `requirements.lock` (or `environment.yml`
for conda paths) alongside its code. The lock is the exact pinned
set of packages produced by `pip freeze` at run-start; it is what
the `env_hash` field in the manifest hashes. Rebuilding the
environment from the lock must reproduce the run bit-for-bit on
the same hardware class (we do not promise across architectures).

### 5.4 Data ledger entry

Any new dataset — a new symbol, a new timeframe, a new feed
vendor, a re-export of an existing feed with a different cleaning
rule — gets a row in `DATA_LEDGER.md` at the repo root with:
source, vendor, timeframe, symbol set, start/end UTC, cleaning
pipeline applied, sha256 of the resulting parquet bundle, date
ingested, ingester (the1finix or agent_id). The data_sha in the
manifest must match a ledger row, or the run is excluded.

---

## §6. Thought Ledger schema (forward declaration for v0.2)

The doctrine implies but does not formalise a stream of per-tick
thoughts shared between agents. v0.1 leaves this informal —
agents emit `Coordinate` objects and the aggregator reads them.
v0.2 will formalise the broader **Thought Ledger** that carries
per-agent rationale, intermediate features, and downstream-agent
reads. We forward-declare the schema here so v0.1 code does not
paint itself into a corner.

Minimum schema fields (subject to revision in v0.2):

```json
{
  "schema_version": 1,
  "decision_horizon": "<ISO 8601 timestamp; thoughts dated after this MUST NOT be read by downstream consumers — the look-ahead guard>",
  "ttl_ticks": "<int; how many ticks this thought is allowed to live before downstream consumers ignore it>"
}
```

Plus the agent's own payload (rationale text, intermediate
features, etc.) which is agent-specific.

**Non-negotiables for v0.2:**

- `schema_version` starts at 1 and is bumped on any breaking field
  change. v0.1 consumers may assume schema 1.
- `decision_horizon` is the **look-ahead guard**: a downstream
  agent reading a thought emitted at time *t* must not consume
  fields whose validity extends past `decision_horizon`. This is
  the program's defence against accidental look-ahead leakage
  between agents.
- `ttl_ticks` is the **read bound**: thoughts older than `ttl_ticks`
  ticks at consumption time are dropped. Prevents stale rationale
  from contaminating fresh decisions.

The Thought Ledger lives at `sim/thought_ledger/` in v0.2 with
JSONL files per agent per UTC day; the consumer API is a thin
reader that returns the slice satisfying both guards. None of
this is built yet — it is forward declaration only.

---

## §7. Acknowledged research debt

The doctrine is honest about its open questions; standards is
honest about its honest-evaluation debt.

### 7.1 Blood-test discipline DEFERRED

All of June 2026 is currently contaminated by post-hoc design.
`zone_d1_against` failed live on 2026-06-19; the doctrine in
`06-blue-lock-doctrine.md` was written between 2026-06-23 and
2026-06-24. We *cannot* turn around and use any June 2026 data
as a clean out-of-sample window for the squad — every design
choice in this program was shaped by what happened that week.

**Implication for numbers reported from June 2026 windows:** they
are "informed estimates", not honest OOS performance. They will
be journalled and they will inform Φ3 development, but the C1–C7
acceptance gates are NOT evaluated against them.

**Revisit:** in Φ4, once F12 (TQS), F14 (adversarial cohort), F17
(ΔInfo, see §7.2), and F18 (the as-yet-unspecified tier-allocation
metric) are wired up end-to-end, we re-open the question of which
windows can be treated as clean OOS. Until then, June 2026 is a
*development* window, not a *holdout* one. Honesty is the only
thing protecting us from quietly re-fitting on the failure that
motivated the program.

### 7.2 Tier 2/3 assignment is empirical (ΔInfo, F17)

The roster has informal tiers (e.g., Yukimiya is a sub-bar
refiner, not a primary; Reo is a follower). v0.1 doctrine treats
these as a-priori roles based on character feel.

That is provisional. Tier assignment will be re-derived
empirically once the F15 / F16 / F17 layer is wired up: an
agent's **tier** is decided by **ΔInfo (F17)** — the marginal
information that agent contributes to the ensemble's decision,
conditioned on the other agents. F17 is unspecified in
`04-quant-foundations.md` v0.3; it lands when the data-plane
trajectory in §8 produces enough run history to estimate it
non-trivially.

Until F17 ships, do not treat tier labels as load-bearing. Use
them as priors, the same way the principled-form ego in
`06-blue-lock-doctrine.md` §3.1.b uses character ego as a prior.

### 7.3 Canon role ≠ information tier

The Blue Lock cast maps to canonical roles — A1 Isagi is a
metavision protagonist, A7 Barou is the lone-wolf King, etc.
These are **a-priori** descriptions of *identity*: what the
agent's weapon is, what regime it likes, what its target hold is.

The **information tier** (Tier 1 / 2 / 3) is the **empirical**
permission to read the Thought Ledger (§6). Tier 1 reads its own
thoughts. Tier 2 reads its own + one cluster of peers. Tier 3
reads everything but writes nothing back to the shared ledger
(audit-only).

These two layers are **separate and must not be conflated.** A
high-canon-prestige agent (A7 Barou) can be a low-information-tier
agent if F17 says his contribution is redundant with A4 Chigiri's.
The doctrine governs *what* an agent is; the tier governs *what
the agent is allowed to read* in the ensemble's collective
deliberation. v0.1 does not yet assign tiers — it is research
debt parked for the v0.2 / Φ4 cycle.

---

## §8. Data-plane trajectory

How the program's data infrastructure evolves. Φ2.5 is the
infrastructure phase named in `00-charter.md`; this is the contract.

### Φ2.5 (now)

- **Storage:** JSONL append-only. One file per agent per UTC day
  for the Thought Ledger; one parquet per result for backtests;
  per-trade journal as a single growing JSONL keyed by trade_id.
- **Index:** none beyond filesystem layout. Reads scan files.
- **Dashboard:** Streamlit running locally, reading directly from
  the JSONLs and parquets. No autorefresh; reloads on user
  interaction.

**Why JSONL + Streamlit at Φ2.5:** the constant cost of every
piece of infrastructure exceeds the variable cost of grep at this
volume. We have ≤ 10² runs, ≤ 10⁴ trades total. Anything more
elaborate is premature.

### Φ4 (fusion sweep era)

- **Storage:** JSONL remains the source of truth (append-only,
  auditable). Add a **SQLite shadow index** that is rebuilt from
  the JSONLs on demand. Schema: one table per stream (coordinates,
  proposals, trades, KPIs). The SQLite is disposable; the JSONLs
  are not.
- **Index:** SQLite + a small materialised view per dashboard
  panel.
- **Dashboard:** Streamlit + autorefresh. PBT runs (Φ5+) push 10³+
  agent-weeks of state; clicking to reload doesn't scale.

**Trigger to graduate to Φ4 data plane:** the first PBT run, or
sweep > 100 configurations, whichever comes first.

### Φ6+ (live shadow + capital promotion)

- **Storage:** JSONL append-only remains the long-term truth. The
  SQLite shadow index is upgraded to a small Postgres or kept as
  SQLite (decision deferred to the relevant program review).
- **Streaming:** add a thin **WebSocket sidecar** that publishes
  new ledger entries as they land, plus a **lightweight FastAPI**
  in front of the read paths.
- **Visualisation:** either a small dedicated frontend (React /
  Svelte) consuming the WebSocket + FastAPI, *or* Grafana
  consuming the SQL store. Choose one when we get there; do not
  pre-emptively scaffold both.

**Trigger to graduate to Φ6+ data plane:** when the shadow run
goes live for capital-promotion evaluation. Until then the
overhead is not worth it.

The point of writing this trajectory down at Φ2.5 is so that
Φ4-era code does not paint Φ2.5 storage choices into a corner.
JSONL append-only is the through-line; everything else is
indices, views, and transports built on top of that immutable
spine.

---

## §9. Cross-reference

| Standard | Closes |
|---|---|
| §1 repo structure | Defines the home of every artefact this program ever produces. |
| §2 naming | Disambiguates programs vs experiments vs audits; makes grep work. |
| §3 branching | G9 (repo split) at the workflow level — separate research from production at the branch level too. |
| §4 evaluation hygiene | C1–C7 of `00-charter.md`; the five-baseline cohort is the input to F14 (adversarial gate). |
| §5 reproducibility | G6 (same evidence ledger) in machine-checkable form. |
| §6 Thought Ledger schema | Forward declaration for v0.2; closes a category of look-ahead leak before it can land. |
| §7 research debt | Honest accounting of what v0.1 *cannot* do — protects every later claim. |
| §8 data-plane trajectory | The Φ2.5/Φ4/Φ6+ infrastructure contract; closes the gap between charter phases and actual storage decisions. |

Every standard ties back to a charter goal, gate, or formula. A
standard that does not tie back does not belong here — file it in
`conflab/` instead.

---

## §10. v0.2 amendments (2026-06-24)

Decisions taken following the E001–E007 audit (`audits/2026-06-24_
E001-E007_audit.md`). Each amendment lists what changes, what stays,
and where the change is realised in the rest of the M001 doctrine.

### §10.1 E010 stays as a parallel pre-registered lab experiment

The E006 Stage-2 exploratory finding — H1 `equal_highs_pool` lifts
every M15 setup placed under it by +0.10 to +0.46 ATR (selection
term, displacement null; audit §2.6, §4.3) — is **cited as prior
evidence** in v0.2 doctrine (`06-blue-lock-doctrine.md` §3.3 and §3.8
of the same doc point at the same audit lines). M001's deployment-
grade confluence layer (A6 Nagi, `05-agent-roster-v0.md` §3.6)
**waits for E010** (the pre-registered Stage-2b that will replicate
the finding with full discipline) before live capital is allocated.

What this means operationally:

- E010 is *not* absorbed into M001. It runs as a separate
  pre-registered lab experiment, under the existing E0XX naming and
  registry per `EXPERIMENTS.md`.
- M001 may *develop* A6 Nagi against the exploratory finding in
  `sim/`, but A6 cannot pass the C1 promotion gate without E010
  having returned a confirmed `alive` verdict on H1 `equal_highs_pool`
  context primitive.
- Cross-program coupling: when E010 lands, M001 cites the E010 result
  in A6 Nagi's spec (a v0.5 amendment to `05-agent-roster-v0.md`)
  and the audit-trail link is bidirectional.

### §10.2 M001 agent promotion stays internal to `programs/M001_*/`

The audit raised the question (audit §6, Q5) of whether each M001
agent that graduates becomes a new E0XX experiment in
`EXPERIMENTS.md`. **Decision: no.** The lifecycle is:

1. Each M001 agent develops in `programs/M001_*/sim/<agent_id>.py`.
2. Each agent accumulates internal evidence in
   `programs/M001_*/reviews/<agent_id>/<date>.md` — per-agent
   walk-forward, regime-conditional KPIs (F18 in
   `04-quant-foundations.md`), F17 ΔInfo measurement, F12 TQS
   distribution.
3. Promotion gate is **C1** (TQS vs Sae per `00-charter.md` §7.1) +
   **C6** (vs Kaiser / Loki on the rolling 12-week window, with the
   Frozen-Sae + Median + Random + composite-Sae cohort from §4.2 of
   this doc).
4. **Only the *final* promoted strategy** — once it has cleared
   every gate and is ready to graduate to `multi-pair-trading-agent/
   agent/multi/` — gets a `docs/findings/` entry in the lab. The
   internal `reviews/` ledger is the evidence trail; the lab finding
   is the externally-visible summary.

Internal evidence is the M001 ledger, **not** the E0XX registry. This
keeps the agent's audit trail single-track (the program branch tells
its own story) and avoids the cross-track confusion of an agent that
is simultaneously a program component and a lab experiment.

### §10.3 E008 is SKIPPED

The audit raised (§6, Q6) whether E008 (technical-indicators-only
screening — RSI / MACD / ADX / Stochastic / Bollinger / SuperTrend
ablation in the E001/E006 style) should run before M001 Φ3 to give
indicator-using strikers (A4 Chigiri uses ADX; the doctrine
references RSI/MACD-style primitives) a pre-validated input set.

**Decision: E008 is skipped.** Rationale:

- The E001 + E006 evidence base already establishes the prior that
  the retail technical-indicator vocabulary is mostly noise when
  tested alone — extending the same screening to the indicator
  family is unlikely to change that prior.
- M001 agents that use indicators (A4 Chigiri's ADX gate; A9 Aoshi's
  ATR; any future indicator-using agent) validate their indicators
  *internally* as part of their weapon design — the indicator is one
  input to the agent's signal trigger, not a standalone signal.
- The C1 promotion gate (§7.1 of the charter) operates per-agent and
  is sample-based, not vocabulary-based; an agent that passes C1
  has demonstrated its indicator choice in context, not in
  isolation.

**Risk accepted:** the indicator vocabulary won't have lab-level
pre-validation. **Mitigation:** per-agent C1 gating absorbs the
risk; if an indicator-using agent fails C1, the failure mode is
already captured at the right level (this agent does not earn its
weight) without requiring a separate indicator-screening
experiment.

If a future M001 program needs indicator pre-validation as a hard
prerequisite (e.g. if an agent depends on an indicator that no
other agent uses, and the agent's edge cannot be reasonably
attributed to anything else), an E0XX experiment is filed at that
time rather than now.

### §10.4 Verdict registry: HYBRID

The audit raised (§6, Q7) whether the lab's four-tier verdict
registry (`alive` / `parked_weak_effect` / `parked_insufficient_n` /
`dead`) should be promoted to a shared dependency that M001 imports,
or whether M001 should invent its own vocabulary.

**Decision: hybrid.**

- **Internally** (per-agent evaluation, weekly reviews, internal
  ledgers): M001 uses the lab's four-tier registry as the
  canonical KPI vocabulary. Each agent's weekly review classifies
  the agent (or one of its variants) into one of the four tiers
  on the regime-conditional KPI vector (F18 in
  `04-quant-foundations.md`).
- **Externally** (human-facing dashboard, weekly digest, decision
  comms): the Blue Lock vocabulary `starter` / `sub` / `benched` /
  `cut` is the *translation layer* for human comprehension.

The mapping is explicit and one-to-one:

| Internal (four-tier registry) | Blue Lock (UI / human comms) |
|---|---|
| `alive` | `starter` (in the deployment XI) |
| `parked_weak_effect` | `sub` (bench, watching ΔInfo trend) |
| `parked_insufficient_n` | `benched` (no data yet to judge) |
| `dead` | `cut` (drop from roster) |

The mapping is also written in `08-dashboard-spec.md` §3 (the
dashboard's verdict-translation layer) so the rendering code has a
single source of truth. The internal vocabulary is the canonical
evidence vocabulary; the UI vocabulary is **decorative** — a UI bug
that mis-labels a `parked_weak_effect` agent as `cut` would be a
display bug, not a verdict change.

### §10.5 Tier definitions in §7.2 / §7.3 are superseded

The v0.1 §7.2 / §7.3 of this doc described:

- Tier 1: "reads its own thoughts"
- Tier 2: "reads its own + one cluster of peers"
- Tier 3: "reads everything but writes nothing back to the shared
  ledger (audit-only)"

These were placeholder definitions written before F17 (ΔInfo)
existed. The v0.2 doctrine in `06-blue-lock-doctrine.md` §3.9 lands
the **empirically-decided** three-tier model:

- **Tier 1** (always read): human dashboard, the Aggregator (for
  journalling fused decisions), the post-hoc evaluation harness
  (for F14 adversarial comparison and F17 ΔInfo).
- **Tier 2** (conditional read, decided empirically): agents whose
  ΔInfo > 0 and bootstrap-significant at α = 0.05.
- **Tier 3** (information-isolated): agents whose ΔInfo ≤ 0; their
  edge is independently measurable and acts as the *control* for
  Tier-2 agents.

The §7.2 / §7.3 v0.1 text is retained above as a paper trail of how
the program understood tiers before the metric existed; the v0.2
model is the binding one. F17 in `04-quant-foundations.md` is the
metric that decides the assignment.

### §10.6 Agent evolution arcs principle (v0.3 doctrine landing)

`06-blue-lock-doctrine.md` §3.11 lands the **Agent Evolution Arcs**
principle: each striker is a versioned identity (`vN`, `vN+1`, …)
whose transitions are *earned* by a defeat / phase / inspiration
trigger, never asserted. This subsection formalises how that
principle binds research-standards-grade evaluation.

**The regression-test contract is non-negotiable.** Any `vN → vN+1`
ships with both:

- A **regression test** (`sim/tests/test_<agent_id>_v2_regression.py`)
  that vN+1 reproduces vN's behaviour on the inputs vN handled
  correctly. Byte identity is the default; documented permitted
  divergences are allowed only when stated in the evolution
  hypothesis (`06-doctrine` §3.11.2 step 2).
- A **forward test** (`sim/tests/test_<agent_id>_v2_resolves_<defeat_id>.py`)
  that vN+1 resolves the defeat trigger on the same evaluation
  window where vN failed. The test asserts the named failure no
  longer fires (or fires with measurably reduced frequency, with
  the threshold pre-declared).

Missing either test is a code-review failure under §5.1 (same
status as calling `np.random.rand()` without a seeded generator).
The retention rule in §3 binds: vN's module and roster registration
remain on disk for at least one full phase gate after vN+1 lands;
the decision to retire vN is journalled in
`reviews/evolution_ledger.md` (Tier-1 per `06-doctrine` §3.9), not
applied silently.

**PBT (Φ5+) is not a substitute for §3.11.2.** A PBT sweep that
perturbs a hyperparameter and produces a TQS lift is a *retune*
of vN, not an evolution to vN+1. The version bump requires a new
code surface, the defeat documentation, and both tests above. PBT
is the *mechanism* that exposes defeat triggers; the doctrine is
the *contract* that turns them into evolutions.

**Acceptance flow for any `vN → vN+1` claim:**

1. Defeat note exists at `reviews/<agent_id>_vN_defeat.md` with a
   reproducible failure-mode citation (trade IDs / regime-bucket
   TQS row / F17 ΔInfo window).
2. Evolution hypothesis stated **before** vN+1 implementation
   begins; reviewer signs off on it inside the defeat note.
3. New module at `sim/agents/aXX_<name>_v2.py`; vN module
   untouched.
4. Both tests (regression + forward) green in CI on the sealed
   panel.
5. Row appended to `reviews/evolution_ledger.md` with the seven
   fields specified in `06-doctrine` §3.11.4.
6. Co-existence window declared (which phase gate retires vN, or
   "both kept as regime-conditional siblings").

A `vN+1` module on disk **without** the matching ledger row and
both tests is research debt — vN remains the canonical agent for
gate-evaluation purposes until the row lands.

### §10.7 Cross-reference (v0.2 + v0.3 deltas)

| Amendment | Closes | Realised in |
|---|---|---|
| §10.1 E010 stays parallel | audit §6, Q1 | `06-doctrine` §3.3 cite; `05-roster` §3.6 (A6 Nagi spec) |
| §10.2 promotion internal | audit §6, Q5 | This doc §10.2; agent reviews live in `programs/M001_*/reviews/` |
| §10.3 E008 skipped | audit §6, Q6 | This doc §10.3; per-agent C1 absorbs the risk |
| §10.4 verdict hybrid | audit §6, Q7 | This doc §10.4; mapping enforced in `08-dashboard-spec.md` §3 |
| §10.5 tier definitions superseded | research debt §7.2 / §7.3 (this doc, v0.1) | `06-doctrine` §3.9; F17 in `04-quant-foundations.md` |
| §10.6 agent evolution arcs | `06-doctrine` §3.11 (v0.3 landing) | This doc §10.6; `reviews/evolution_ledger.md`; per-agent fields in `05-agent-roster-v0.md` |
