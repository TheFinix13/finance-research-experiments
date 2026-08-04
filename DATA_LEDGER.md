# Data usage ledger

Tracks which `(pair, timeframe, date slice)` combinations each experiment
has consumed. Update this file **in the same commit** as the first Stage-1
run (or retrospective registration) for that experiment.

**Status key:** `pristine` (never used) · `screen` · `confirm` · `sealed` ·
`excluded` (tested, rejected for deployment) · `live` (production monitor)

Parquet cache: `../multi-pair-trading-agent/data/parquet/` (single canonical copy).
Live broker fills cache (Φ3): `~/Documents/TradingAgentLogs/{SYMBOL}/`
(VM-only; absent on the Mac research host as of 2026-06-24).

Last updated: **2026-08-04** (E031/E032 screens consumed, both stopped
at Stage-1 go/no-go — confirm + sealed reservations RELEASED
un-consumed)

---

## EURUSD

| TF | Slice | Status | Experiments |
|---|---|---|---|
| H4 | 2015-01-01 → 2021-12-31 (9th use) | screen | E001, E002, E003, E004, E006, E007, E027 (consumed 2026-07-28; overuse acknowledged in E027 §8), E031 + E032 (consumed 2026-08-04; overuse acknowledged in both protocols §4 — orthogonal hypotheses: portfolio slot mechanics / breakout entry class) |
| H4 | 2022-01-01 → 2024-12-31 | confirm | E003, E004, E006, E007; E027 stopped at Stage 1 — not consumed; E031/E032 stopped at Stage 1 2026-08-04 — not consumed |
| H4 | 2024-01-01 → 2024-12-31 | **observation** | M001 Φ3-prep regime weak-label validation (`sim/regime/validate_real.py`; 1617 bars; not an experiment, no claim, see `sim/regime/README.md`) |
| H4 | 2015-01-01 → 2025-12-31 | screen+confirm | E001, E002, E004 |
| H4 | 2025-01-01 → 2026-06-09 | sealed | E005 |
| H4 | 2026-01-01 → present | live | (agent demo — not a lab split) |
| H1 | 2015-01-01 → 2021-12-31 | screen | E001, E006, E007, E010 (consumed 2026-07-28), E027 (consumed 2026-07-28) |
| H1 | 2022-01-01 → 2024-12-31 | confirm | E006, E007, E010 (consumed 2026-07-28); E027 stopped at Stage 1 — not consumed |
| H1 | 2025-01-01 → 2026-05-27 | sealed — **CONSUMED** | E029 Stage 2 (sealed run executed once 2026-07-28; verdict ALIVE ×2 cells). No longer pristine for any future experiment |
| M15 | 2015-01-01 → 2021-12-31 | screen | E001, E006, E010 (consumed 2026-07-28), E028 (consumed 2026-07-28; day-sequence outcome), E030 (Stage-1 lock consumed 2026-07-28 — go/no-go stop fired here) |
| M15 | 2022-01-01 → 2024-12-31 | confirm | E006, E010 (consumed 2026-07-28); E030 Stage-2 reservation RELEASED un-consumed 2026-07-28 (stopped at Stage 1) |
| M15 | 2025-01-01 → 2026-05-27 | sealed — **CONSUMED** | E029 Stage 2 (executed once 2026-07-28); E030 co-reservation released un-consumed. No longer pristine for any future experiment |
| D1 | 2015-01-01 → 2025-12-31 | screen | E001, E002, E004 |
| M5 | 2015-01-01 → 2021-12-31 | screen | E001 |

**Fresh slices (good candidates for new hypotheses):** EURUSD M5 confirm/OOS,
EURUSD M30 (if cached), any TF on pairs below with `pristine` H1/M15.

---

## GBPUSD

| TF | Slice | Status | Experiments |
|---|---|---|---|
| H4 | 2015-01-01 → 2021-12-31 | screen | E031 + E032 (consumed 2026-08-04; both stopped at Stage 1; prior E005/E006 sealed history on the wider slice documented in both protocols) |
| H4 | 2015-01-01 → 2024-12-31 | sealed | E005, E006 (replication) |
| H4 | 2015-01-01 → 2025-12-31 | screen+confirm | E001, E004, E005 |
| H1 | 2015-01-01 → 2021-12-31 | screen | E001, E006, E029 (Stage 1 consumed 2026-07-28 — first computation of the lift statistic on this pair; 8/10 alive) |
| H1 | 2022+ | pristine | — (cache audit per E007 §3.8: GBPUSD H1 not available past 2021) |
| M15 | 2015-01-01 → 2021-12-31 | screen | E006 (screen-style replication), E029 (Stage 1 consumed 2026-07-28); E030 Stage-3 reservation RELEASED un-consumed 2026-07-28 |
| M15 | 2022+ | pristine | — (subject to cache audit) |

Agent **live deployment** started 2026-06; lab should prefer USDCAD H1/M15
or new pairs before re-mining GBPUSD H4 2015-2024 for unrelated hypotheses.

---

## USDCAD

| TF | Slice | Status | Experiments |
|---|---|---|---|
| H4 | 2015-01-01 → 2021-12-31 | screen | E031 + E032 (consumed 2026-08-04; both stopped at Stage 1; prior E005 sealed history on the wider slice documented in both protocols) |
| H4 | 2015-01-01 → 2024-12-31 | sealed | E005 |
| H4 | 2015-01-01 → 2025-12-31 | screen+confirm | E001, E004, E005 (E027 Stage-3 reservation released 2026-07-28 — stopped at Stage 1) |
| H1 | all | pristine — **not cached** (E007 §3.8 audit; E010 §0 Stage-0 check confirms) | — |
| M15 | all | pristine — **not cached** (E007 §3.8; E010 §0 Stage-0 check confirms) | — |

**Best fresh real estate:** USDCAD H1, M15, M5 (once cached); USDCAD H4
post-2025 sealed look when enough bars accumulate. Caching USDCAD H1/M15
is a prerequisite for any cross-pair extension of E010 (currently
flagged as out-of-scope for the active pre-registration).

---

## AUDUSD / NZDUSD

| Pair | TF | Slice | Status | Experiments |
|---|---|---|---|---|
| AUDUSD | H4 | 2015 → 2025 | excluded | E005 (failed replication) |
| NZDUSD | H4 | 2015 → 2025 | excluded | E005 (failed replication) |

Use only with explicit acknowledgment of prior failed replication in the
new protocol's Related Work section.

---

## Planned (pre-registered, Stage 1 not yet run)

(none — E031/E032 screens consumed 2026-08-04 and moved into the
per-pair tables above; both stopped at Stage 1, so their confirm
(2022–2024) and sealed (2025-01-01 → 2026-07-25) H4 reservations were
RELEASED un-consumed.)

## Overuse warning

EURUSD H4 **2015-2021** has been screened by **nine** registered experiments.
Treat further claims on that exact slice as **low independent power** unless
the hypothesis is orthogonal (different outcome, different event definition)
and the protocol documents the prior uses above.

When in doubt, pick a **pristine** row from this table.

---

## M001 friction calibration manifest

The friction model (`programs/M001_multi_agent_ensemble/sim/core/friction.py`)
is calibrated against **June 2026 VM broker fills** on Exness demo
(1:1000, $100 equity profile) per `09-experiment-architecture.md` §1.8.

| Field | Value |
|---|---|
| Source path | `~/Documents/TradingAgentLogs/{EURUSD,GBPUSD,USDCAD}/` |
| Source schema | `{SYMBOL}_YYYY-MM-DD.log` (text, bracketed events) + `near_misses/events.jsonl` + `losses/events.jsonl` + `ladders/events.jsonl` |
| Expected window | 2026-06-17 → ongoing (live deployment) |
| Artefact path (when calibrated) | `programs/M001_multi_agent_ensemble/sim/core/friction_calibration_2026-06.json` |
| Status (2026-06-24, Mac host) | **deferred** — only `~/Documents/TradingAgentLogs/summaries/summary_2026-06-17_to_2026-06-23.txt` exists locally (no symbol dirs, no fills yet). Machinery in place; calibration runs on the VM in Φ3. |
| n_fills calibrated | 0 (deferred) |
| Friction defaults in force | `k=0.05`, `latency_ms=250`, `partial_fill_prob=0.20`, `reject_prob=0.01` (see `friction.py` `DEFAULT_*`) |

Calibration commit policy: bump only via a commit that re-runs
`calibrate_against_fills(symbol, ...)` and `write_calibration_file(...)`
on the VM; prior values stay in git history (`09` §6).

