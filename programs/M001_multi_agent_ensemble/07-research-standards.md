# 07 — Research Standards

**Status:** `DRAFT v0.1` — 2026-06-24.

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
