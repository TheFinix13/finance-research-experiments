# Data usage ledger

Tracks which `(pair, timeframe, date slice)` combinations each experiment
has consumed. Update this file **in the same commit** as the first Stage-1
run (or retrospective registration) for that experiment.

**Status key:** `pristine` (never used) · `screen` · `confirm` · `sealed` ·
`excluded` (tested, rejected for deployment) · `live` (production monitor)

Parquet cache: `../eurusd-ai-agent/data/parquet/` (single canonical copy).

Last updated: **2026-06-16**

---

## EURUSD

| TF | Slice | Status | Experiments |
|---|---|---|---|
| H4 | 2015-01-01 → 2021-12-31 | screen | E001, E002, E003, E004, E006, E007 |
| H4 | 2022-01-01 → 2024-12-31 | confirm | E003, E004, E006, E007 |
| H4 | 2015-01-01 → 2025-12-31 | screen+confirm | E001, E002, E004 |
| H4 | 2025-01-01 → 2026-06-09 | sealed | E005 |
| H4 | 2026-01-01 → present | live | (agent demo — not a lab split) |
| H1 | 2015-01-01 → 2021-12-31 | screen | E001, E006, E007 |
| H1 | 2022-01-01 → 2024-12-31 | confirm | E006, E007 |
| M15 | 2015-01-01 → 2021-12-31 | screen | E001, E006 |
| M15 | 2022-01-01 → 2024-12-31 | confirm | E006 |
| D1 | 2015-01-01 → 2025-12-31 | screen | E001, E002, E004 |
| M5 | 2015-01-01 → 2021-12-31 | screen | E001 |

**Fresh slices (good candidates for new hypotheses):** EURUSD M5 confirm/OOS,
EURUSD M30 (if cached), any TF on pairs below with `pristine` H1/M15.

---

## GBPUSD

| TF | Slice | Status | Experiments |
|---|---|---|---|
| H4 | 2015-01-01 → 2024-12-31 | sealed | E005, E006 (replication) |
| H4 | 2015-01-01 → 2025-12-31 | screen+confirm | E001, E004, E005 |
| H1 | 2015-01-01 → 2021-12-31 | screen | E001, E006 |
| H1 | 2022+ | pristine | — |
| M15 | most | pristine | E006 only on screen-style replication |

Agent **live deployment** started 2026-06; lab should prefer USDCAD H1/M15
or new pairs before re-mining GBPUSD H4 2015-2024 for unrelated hypotheses.

---

## USDCAD

| TF | Slice | Status | Experiments |
|---|---|---|---|
| H4 | 2015-01-01 → 2024-12-31 | sealed | E005 |
| H4 | 2015-01-01 → 2025-12-31 | screen+confirm | E001, E004, E005 |
| H1 | all | pristine | — |
| M15 | all | pristine | — |

**Best fresh real estate:** USDCAD H1, M15, M5; USDCAD H4 post-2025 sealed
look when enough bars accumulate.

---

## AUDUSD / NZDUSD

| Pair | TF | Slice | Status | Experiments |
|---|---|---|---|---|
| AUDUSD | H4 | 2015 → 2025 | excluded | E005 (failed replication) |
| NZDUSD | H4 | 2015 → 2025 | excluded | E005 (failed replication) |

Use only with explicit acknowledgment of prior failed replication in the
new protocol's Related Work section.

---

## Overuse warning

EURUSD H4 **2015-2021** has been screened by **six** registered experiments.
Treat further claims on that exact slice as **low independent power** unless
the hypothesis is orthogonal (different outcome, different event definition)
and the protocol documents the prior uses above.

When in doubt, pick a **pristine** row from this table.
