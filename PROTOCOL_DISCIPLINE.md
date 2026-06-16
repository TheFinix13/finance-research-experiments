# Protocol discipline — binding rules for every experiment

Status: **effective 2026-06-16**. Every experiment in this repository must
follow these rules. Individual experiment protocols (`experiments/EXXX_*/PROTOCOL.md`)
extend this document; they may not weaken it without an explicit amendment
commit **before** the affected analysis runs.

This repo is the **central research workshop**. The trading agent
(`eurusd-ai-agent`) is the **production execution system**. Nothing here
trades, routes orders, or changes live parameters without the agent's own
validation pipeline (grid → holdout → walk-forward → cross-pair → sealed).

---

## 1. Registration before data

1. **Assign an ID** in `EXPERIMENTS.md` (`E001`, `E002`, … incrementing).
2. **Create** `experiments/EXXX_short_name/PROTOCOL.md` using
   `experiments/_TEMPLATE/PROTOCOL.md` as a skeleton.
3. **Commit and push** the protocol with message containing `PRE-REGISTRATION`
   or `E00X: pre-register` **before** any Stage-1 screen or peek at outcomes.
4. Record the **commit hash** in the experiment's `REPORT.md` when results land.

Retrospective experiments (agent work predating this repo) are documented
with status `executed-then-registered` and carry an epistemic caveat: they
informed production but did not benefit from pre-registration at execution
time.

---

## 2. Data splits and the ledger

| Split | Typical window | Use |
|---|---|---|
| **screen** | e.g. 2015 → 2021 | First look; BH-FDR family defined here |
| **confirm** | e.g. 2022 → 2024 | Survivors only; per-cell α, no re-tuning |
| **sealed** | e.g. 2025+ | Run once; no peeking; no parameter edits |
| **live** | deployment period | Production monitoring only; not a research split |

**`DATA_LEDGER.md` is updated atomically** with every experiment that
touches a `(pair, TF, split)` slice. A slice used in `sealed` status cannot
honestly be claimed as unseen in a later experiment without documenting
the prior use.

Parquet bars live in **`eurusd-ai-agent/data/parquet/`** (canonical). This
repo reads them via `PYTHONPATH=../eurusd-ai-agent:.` — never duplicate
the cache.

---

## 3. Controls and confounds

- **Hour-of-day-matched controls** are the default for intraday TFs (M15,
  H1, H4). Uniform random-time controls are invalid when session volatility
  varies by hour (Test A amendment v2.1; see `E006`).
- Permutation nulls use a fixed `n_perm` declared in the protocol.
- Control draws must match the event's direction and hour-of-day unless
  the protocol explicitly states otherwise.

---

## 4. Multiplicity and verdicts

Every evaluated cell counts toward that stage's FDR family — including
cells we lose interest in (**compute-vs-claim**).

Four-tier verdict registry (append-only per cell):

| Verdict | Meaning |
|---|---|
| `alive` | Positive effect, survived stage FDR → may advance |
| `parked_weak_effect` | Positive raw signal, failed FDR or thin confirm |
| `parked_insufficient_n` | Below n gate; stats still recorded |
| `dead` | Adequately powered, no effect |

**Stop rules** must be pre-declared (e.g. "if 0 alive at Stage 1, stop").
Stopping is a valid outcome.

---

## 5. Amendments

Any change to a locked parameter after pre-registration requires:

1. A new subsection in the experiment's `PROTOCOL.md` under **Amendments**
   with date, rationale, and guarantee that outcomes were not yet scored
   (or that the amendment is explicitly post-hoc and non-claiming).
2. A dedicated commit before the amended analysis runs.
3. Preservation of the pre-amendment registry as a cautionary record.

No silent edits to frozen protocols.

---

## 6. Outputs and naming

| Artifact | Location |
|---|---|
| Protocol | `experiments/EXXX_*/PROTOCOL.md` |
| Report | `experiments/EXXX_*/REPORT.md` |
| Evidence manifest | `experiments/EXXX_*/MANIFEST.md` |
| Stage registries | `output/EXXX_*/` or legacy `output/` paths documented in MANIFEST |
| Figures | `output/EXXX_*/figures/` or experiment `results/figures/` |

Commit prefix: `E00X:` for experiment-scoped work.

---

## 7. Separation from the trading agent

| Allowed | Forbidden |
|---|---|
| Observation, screening, hypothesis tests | Importing this repo into the agent's live path |
| Copying result summaries into reports | Changing agent locked params from lab tables |
| Proposing candidates for agent validation | Auto-deploying lab survivors without agent pipeline |
| Reading agent parquet via PYTHONPATH | Duplicating or mutating agent strategy code here |

Validated agent parameters live in `eurusd-ai-agent` only. Lab findings
that might affect deployment are **candidates** until the agent's full
validation chain re-locks them.

---

## 8. Starting a new experiment (checklist)

```
[ ] ID assigned in EXPERIMENTS.md
[ ] DATA_LEDGER.md row drafted (status: planned)
[ ] experiments/EXXX_*/PROTOCOL.md written (parameters frozen)
[ ] PRE-REGISTRATION commit pushed
[ ] Run stages per protocol
[ ] Update DATA_LEDGER.md (status: screen / confirm / sealed)
[ ] REPORT.md + MANIFEST.md committed
[ ] EXPERIMENTS.md status → complete | stopped | parked
```

Use `experiments/_TEMPLATE/` for copy-paste scaffolding.
