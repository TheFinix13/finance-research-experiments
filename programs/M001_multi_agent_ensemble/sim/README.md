# `sim/` — M001 multi-agent ensemble simulator

**Status:** `Phi2.5 scaffold` — 2026-06-24. Binding spec:
[`../09-experiment-architecture.md`](../09-experiment-architecture.md).
Doctrine: [`../06-blue-lock-doctrine.md`](../06-blue-lock-doctrine.md).
Standards: [`../07-research-standards.md`](../07-research-standards.md).

This folder is the deterministic replay simulator for M001. **The
simulator is the experiment.** Phase gates Phi2 -> Phi6 are evaluated
inside `sim/`; the live demo (Phi5+) is out-of-sample validation only.

```
sim/
  core/         types, ledger, striker, engine, seed, friction, sentinel, aggregator
  regime/       four-class classifier (trending / chop / vol_spike / news) + train/eval
                + Streamlit `label_disagreements.py` (Φ3-prep human-data-loop)
  scoring/      F12 TQS · F17 ΔInfo · F18 regime-conditional KPIs
  roster/       mvp_phi4.yaml (4-agent Φ4 v1) + mvp_phi41.yaml (8-agent
                Φ4.1 expansion) + full_canon.yaml (10-agent target)
  agents/       Φ4 v1: a01_isagi, a06_nagi, a07_barou, a10_kunigami;
                Φ4.1 v1 expansion: a02_bachira, a03_rin, a04_chigiri, a05_reo
  dashboard/    Streamlit v0 (six panels per `08-dashboard-spec.md`)
  tests/        determinism, ledger look-ahead, friction, sentinel, seed
../scripts/     VM-side CLIs run on the Windows deployment box
                (e.g. `vm_calibrate_friction.py`)
```

## Quickstart

The repo-root `Makefile` carries shortcuts for the most common
operations (`make test-sim`, `make label-regime`, `make vm-calibrate`,
`make vm-calibrate-dry`). The raw invocations below stay as the
canonical reference; the Makefile is a thin alias layer over them.

### 1. Run the test suite

```bash
PYTHONPATH=../multi-pair-trading-agent:. \
  ../multi-pair-trading-agent/.venv/bin/python \
  -m pytest programs/M001_multi_agent_ensemble/sim/tests/ -q
```

Expected: **210 tests pass + 4 skipped** (the skipped ones are the
real-data friction-calibration bounds test, the slow Phi3 gate
real-data integration, the slow Phi4 squad gate real-data
integration, and the slow Phi4.1 expanded-squad real-data
integration).

### 2. Train the regime classifier (synthetic data smoke test)

```bash
PYTHONPATH=../multi-pair-trading-agent:. \
  ../multi-pair-trading-agent/.venv/bin/python \
  -m programs.M001_multi_agent_ensemble.sim.regime.train --seed 42
```

The synthetic generator injects all four regime classes (trending / chop
/ vol_spike / news) so the rule-based labels exercise the full classifier
surface. Real training requires hand-labelled validation data (see
[`#training-data-contract`](#training-data-contract)).

### 3. Evaluate the regime classifier against the G4 gate

```bash
PYTHONPATH=../multi-pair-trading-agent:. \
  ../multi-pair-trading-agent/.venv/bin/python \
  -m programs.M001_multi_agent_ensemble.sim.regime.eval --gate 0.75
```

Gate threshold: holdout macro F1 >= 0.75. The eval script returns a
non-zero exit code on failure.

### 4. Launch the Streamlit dashboard

```bash
PYTHONPATH=../multi-pair-trading-agent:. \
  ../multi-pair-trading-agent/.venv/bin/streamlit run \
  programs/M001_multi_agent_ensemble/sim/dashboard/app.py \
  --server.address 127.0.0.1 --server.port 8501
```

Default port: 8501. The server binds to `127.0.0.1` only
(research-standards §6). Open `http://127.0.0.1:8501` in a browser.

All **six panels** render with placeholder data when no replay run is on
disk so the surface is exercisable before the first sim run lands.

## Phi2 -> Phi3 gate (G4) — checklist

Per `09-experiment-architecture.md` §1.5 the G4 exit criteria are:

| Criterion | Status (Phi2.5 scaffold + Phi3-prep 2026-06-24) |
|---|---|
| Replay fidelity: simulator median pips/trade per rolling OOS window reproduces E004 `zone_d1_against / H4 / all` baseline **±5 %** per window (reference +11.34 pips/trade) | **deferred** — requires Phi3 cross-repo import of the production `zone_d1_against` cell + parquet bar feed |
| Regime classifier: macro-regime labels achieve holdout F1 >= 0.75 vs hand-labelled validation set (>= 200 bars) | **research debt acknowledged + human-data-loop tool shipped**: synthetic F1=0.999 is circular (trains and scores against the same rule); real-data weak-label agreement F1=**0.496** on EURUSD H4 2024 (vs the heuristic rules; `vol_spike`/`news` drag the macro). 30 disagreements saved to `sim/regime/disagreements_for_review.csv`. Streamlit labelling tool at [`sim/regime/label_disagreements.py`](regime/label_disagreements.py) — run with `streamlit run …/label_disagreements.py` to convert the 30 anchors into a ground-truth label slice. See `sim/regime/README.md` for the interpretation guide. |
| Friction model calibrated against June 2026 VM broker fills (09 §1.8) | **machinery in place, data deferred, VM script shipped**: text-log parser, JSONL vault reader, ATR-aware k estimator, and `load_calibration()` JSON loader all wired in `sim/core/friction.py`. No real fills on this Mac host (only `~/Documents/TradingAgentLogs/summaries/` weekly text); the VM-side CLI at [`scripts/vm_calibrate_friction.py`](../scripts/vm_calibrate_friction.py) auto-detects `C:\Users\Fiyin\Documents\TradingAgentLogs\` (with `~/Documents/TradingAgentLogs` and `D:\TradingAgentLogs` fallbacks), pulls ATR(14) at signal time from the production parquet cache, prints a paste-friendly per-symbol summary, and writes `sim/core/friction_calibration_2026-06.json`. Defaults remain conservative until a real run lands the JSON. |
| Dashboard: Streamlit v0 renders all six panels in `08-dashboard-spec.md` §2 against synthetic + one real replay run without exception | **scaffold renders all six with placeholder data**; first-run-against-real-replay validates in Phi3 |

Phi2.5 deliverables that land in this folder:

- [x] Deterministic kernel (`sim/core/types.py`, `seed.py`, `engine.py`,
      `ledger.py`, `striker.py`)
- [x] Four-impl ledger: `FullLedger`, `RedactedLedger(agent_id)`,
      `FrozenLedger(snapshot_path)`, `SyntheticLedger(null_hypothesis)`
- [x] Friction model with calibration placeholders (`sim/core/friction.py`)
- [x] Sentinel R1–R5 + external-shock evaluator (`sim/core/sentinel.py`)
- [x] Minimal aggregator stub (`sim/core/aggregator.py`)
- [x] Regime classifier trained + saved to `sim/regime/model_v1.pkl`
- [x] TQS + ΔInfo + regime-KPI implementations (`sim/scoring/`)
- [x] 4-agent MVP roster YAML + 10-agent canon target YAML
- [x] Agent stubs for A1 / A6 / A7 / A10
- [x] Streamlit v0 dashboard with all six panels
- [x] Tests pass: determinism, ledger look-ahead, friction, sentinel, seed

## Running Φ3 gate (A1 Isagi v1 vs Sae)

The Φ3 → Φ4 gate (`09-experiment-architecture.md` §1.5 G4) wraps the
production `zone_d1_against / H4 / all` cell as A1 Isagi v1 and
validates that the `BlueLockStriker.observe`/`intend` protocol preserves
E004's `+11.34 median OOS pips/trade` baseline (`docs/findings/2026-06-09_walk_forward_validation.md`).

### Cross-repo import contract

The wrapper imports
`agent.alphas.concepts.zone_alpha.SupplyDemandAlpha` from the
production repo. Resolution order (`sim/_cross_repo.py`):

1. `M001_PRODUCTION_REPO` environment variable (preferred).
2. Default dev path `~/Documents/GitHub/multi-pair-trading-agent`.

A clear `ProductionRepoMissing` error fires if neither location
contains `agent/alphas/concepts/zone_alpha.py`. **Lab code never
recreates or copies the production cell** — that is a doctrine §7
commitment (`06-blue-lock-doctrine.md`).

### Run the gate

```bash
PYTHONPATH=../multi-pair-trading-agent:. \
  M001_PRODUCTION_REPO=../multi-pair-trading-agent \
  ../multi-pair-trading-agent/.venv/bin/python \
  -m programs.M001_multi_agent_ensemble.sim.scoring.run_isagi_phi3_gate \
  --verbose
```

Default window: EURUSD H4 2015-01-01 → 2025-12-31 (matches E004's
7-window walk-forward: 4 yr IS / 1 yr OOS rolling). Output:
`programs/M001_multi_agent_ensemble/reviews/phi3_gate_isagi_v1.md`.

Verdict thresholds (per spec):

| Outcome | Rule |
|---|---|
| `PASS` | median OOS-window mean pips/trade within ± 5 % of +11.34, AND ≥ 5/7 OOS windows positive |
| `PARTIAL` | OOS windows pass but median pip drift outside ± 5 % |
| `FAIL` | median OOS mean < +9.0 pips OR < 5/7 OOS windows positive |
| `PROVISIONAL` | data window incomplete / wrapper missing — numbers reported, gate not graded |

Slow integration tests are skipped by default. Enable with
`M001_RUN_SLOW=1 pytest -m slow`.

## Running Φ4 gate (4-agent MVP squad vs Isagi-alone)

The Φ4 → Φ5 gate (`09-experiment-architecture.md` §1.5 G5) drives the
four MVP strikers concurrently and asks whether the squad TQS beats
Isagi-alone:

| Outcome | Rule |
|---|---|
| `PASS` | squad median OOS-window mean TQS ≥ **1.10 ×** Isagi-alone |
| `PARTIAL` | 1.00 × ≤ ratio < 1.10 × — positive lift below the gate floor |
| `FAIL` | ratio < 1.00 × — adding agents LOST edge (reported honestly per user constraint) |
| `PROVISIONAL` | < 30 squad trades; below the statistical-claim floor |

```bash
PYTHONPATH=../multi-pair-trading-agent:. \
  M001_PRODUCTION_REPO=../multi-pair-trading-agent \
  ../multi-pair-trading-agent/.venv/bin/python \
  -m programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate \
  --verbose
```

Default window: EURUSD + USDCAD H4 2015-01-01 → 2025-12-31 (GBPUSD
skipped — Barou is USDCAD-only and EURUSD is the apples-to-apples
comparator vs Phi3). Walk-forward 4 yr IS / 1 yr OOS (7 windows).

Outputs written to `programs/M001_multi_agent_ensemble/reviews/`:

* `phi4_squad_v1.md` — verdict, per-agent KPIs, walk-forward table,
  F17 ΔInfo for Nagi + Barou, engine telemetry, **Diagnosis section
  on FAIL/PARTIAL**, honest caveats.
* `phi4_isagi_rejection_analysis.md` — cross-striker rejection
  bucket distribution (same/opposite/silent/elsewhere).
* `phi4_squad_v1_trades.jsonl` — every closed trade with TQS components.
* `phi4_squad_v1_proposals_all.jsonl` — every proposal (accepted +
  rejected) for replay debugging.
* `phi4_squad_v1_rejected_proposals.jsonl` — only the rejected
  proposals, structured for the rejection-analysis harness.

CLI flags:

* `--start YYYY-MM-DD`, `--end YYYY-MM-DD` — narrow the window.
* `--out-dir PATH` — override the default reviews directory.
* `--delta-info-windows N` — how many of the 7 OOS windows to use for
  F17 ΔInfo (default 3; max 7). The isolated arm re-runs the full
  4-agent squad per window with a `RedactedLedger(self_only)` for
  the candidate Tier-2 agent (Nagi or Barou) — compute scales linearly.

The harness implements the Phi4 contract from `09 §1.5` + doctrine §3.8:

1. **Two-phase tick order** — every striker `observe()` runs before
   ANY striker `intend()` in the same bar; the ledger guard
   (`tick_id < current_tick`) blocks same-tick reads. This means
   Nagi's chemical-reaction predicate fires against tick T-1 peer
   thoughts at the earliest. The one-bar lag is **intentional**.
2. **Deterministic agent ordering** — lexicographic on `agent_id`,
   independent of roster YAML order.
3. **Per-symbol single-position rule** — preserves the E004 execution
   contract; concurrent positions allowed across symbols.
4. **Phi4 aggregator** — per `(symbol, tick)`, highest-conviction
   proposal wins; all losers logged to `rejected_proposals.jsonl`
   with full provenance.
5. **F17 ΔInfo for Tier-2 candidates** — each candidate (Nagi, Barou)
   runs both informed (FullLedger) and isolated
   (`RedactedLedger(self_only)`) arms; bootstrap CI per
   `sim/scoring/delta_info.py`.

## Running Φ4.1 gate (8-agent expanded squad)

Φ4.1 is the predicate-starvation-fix expansion of Φ4. The Φ4 squad
gate **FAILed at 0.98x** with Nagi firing **0** confluence thoughts
because the F11/F13 chemical-reaction predicate needs ≥ 2 distinct
peers with conviction ≥ 0.70 + shared tags + overlapping coordinate
bands — structurally unreachable with only Isagi (base conviction
0.65) and Barou trading. Φ4.1 expands the roster to 8 strikers and
re-asks the gate question.

The verdict thresholds (PASS/PARTIAL/FAIL/PROVISIONAL) and locked
statistic (median OOS-window mean TQS) are **identical to Φ4** —
this is an apples-to-apples comparison with one variable changed
(the roster).

Roster: `sim/roster/mvp_phi41.yaml` (8 agents = 4 Φ4 carryovers +
4 new strikers). `mvp_phi4.yaml` is preserved verbatim for
backwards-compatible reruns.

```bash
PYTHONPATH=../multi-pair-trading-agent:. \
  M001_PRODUCTION_REPO=../multi-pair-trading-agent \
  ../multi-pair-trading-agent/.venv/bin/python \
  -m programs.M001_multi_agent_ensemble.sim.scoring.run_phi41_gate \
  --verbose
```

Default window: EURUSD + GBPUSD + USDCAD H4 2015-01-01 → 2025-12-31
(GBPUSD added vs Φ4 because Bachira + Chigiri trade it; without it
they're silenced). Walk-forward 4 yr IS / 1 yr OOS (7 windows).

Outputs written to `programs/M001_multi_agent_ensemble/reviews/`:

* `phi41_squad_v1.md` — verdict, per-agent KPIs, walk-forward
  table, F17 ΔInfo for 6 candidates, **predicate-starvation
  falsifier headline** with Φ4 → Φ4.1 Nagi confluence count delta,
  auto-diagnosis (YES/NO answer to "did predicate starvation get
  fixed?"), honest caveats.
* `phi41_squad_v1_addendum.md` — hand-written interpretation. Φ5
  recommendations (aggregator + risk allocator, NOT more strikers).
* `phi41_isagi_rejection_analysis.md` — cross-striker rejection
  buckets. The 87.5% same-direction share in the 2026-06-24 run is
  the fingerprint of crowd-out.
* `phi41_squad_v1_trades.jsonl` — every closed trade with TQS components.
* `phi41_squad_v1_proposals_all.jsonl` — every proposal (accepted +
  rejected) for replay debugging.
* `phi41_squad_v1_rejected_proposals.jsonl` — rejected proposals only,
  structured for the rejection-analysis harness.

CLI flags:

* `--start YYYY-MM-DD`, `--end YYYY-MM-DD` — narrow the window.
* `--out-dir PATH` — override the default reviews directory.
* `--delta-info-windows N` — how many of the 7 OOS windows to use for
  F17 (default 3). F17 isolated arms now run for 6 candidates (Nagi,
  Barou, Bachira, Rin, Chigiri, Reo), so each window adds ~6 × per-
  window cost.

The Φ4.1 harness reuses Φ4's `_drive_squad_replay`, aggregator, and
isolated-arm driver verbatim — only squad construction, symbol set,
F17 candidate registry, telemetry counters, and the diagnosis block
differ.

**2026-06-24 verdict: FAIL @ 0.92x. Nagi confluence count 0 → 34302
— predicate starvation confirmed fixed; new failure mode is
structural crowd-out at the aggregator.** See `phi41_squad_v1.md`
+ `phi41_squad_v1_addendum.md` for the full diagnosis.

### Why Φ4.1 hardened the FullLedger

Φ4.1 has 8 agents × 3 symbols × 53k bars where ~5 active agents call
`ledger.read(symbol=...)` per tick. The legacy O(N) per-call read +
O(N) per-append dedup compounded to O(N²) aggregate cost, which
prevented the squad gate from completing within the interactive
compute budget. The Φ4.1 ledger optimisation adds:

* `_JsonlBackend._seen_ids` — O(1) dedup set keyed by thought_id.
* `_JsonlBackend._by_symbol` — per-symbol bucket index.
* `FullLedger.read(..., symbol=X)` fast path using `iter_by_symbol(X)`.

**Semantics preserved verbatim** — guards, insertion order,
look-ahead filtering, on-disk JSONL files all byte-identical to
the pre-optimisation backend. Tested via the existing 186-test
sim suite (including `test_ledger_lookahead`, `test_a05_reo_wrap`,
`test_a06_nagi_wrap` which all exercise the ledger heavily).

## Phi3 build order (next phase)

Per architecture §10 and 09 §2:

1. [x] Wire the production `zone_d1_against` cell into `A1IsagiV1.intend`
   via cross-repo import (`PYTHONPATH=../multi-pair-trading-agent:.` or
   `M001_PRODUCTION_REPO=...`).
2. [x] Φ3 gate (A1 Isagi v1) — **PASS @ +11.04 median OOS pips/trade**
   (drift −2.7 % vs Sae +11.34; 7/7 OOS windows positive). Review:
   `reviews/phi3_gate_isagi_v1.md`.
3. [x] Φ4 gate (4-agent MVP squad) — **FAIL @ 0.98× Isagi-alone TQS**
   on EURUSD + USDCAD H4 2015–2025 (squad mean TQS 0.311 vs Isagi-
   alone 0.317; 2006 squad trades; Nagi fired 0 confluence thoughts,
   Barou's median is negative -7.28 pips, dilutes Isagi's median).
   Honest diagnostic in `reviews/phi4_squad_v1.md`. Rejection
   analysis in `reviews/phi4_isagi_rejection_analysis.md`.
4. [x] Φ4.1 gate (8-agent expanded squad) — **FAIL @ 0.92× Isagi-alone
   TQS** on EURUSD + GBPUSD + USDCAD H4 2015–2025. New agents A2
   Bachira / A3 Rin / A4 Chigiri / A5 Reo shipped. **Nagi confluence
   count moved from 0 (Φ4) to 34302 (Φ4.1) — predicate-starvation
   hypothesis decisively confirmed**, but the squad still loses
   because of a new failure mode: Bachira/Rin's +0.10/+0.15
   conviction lifts crowd Isagi and Barou out of the aggregator
   entirely (both made 0 trades; the squad ledger is 76% Bachira).
   Diagnostic in `reviews/phi41_squad_v1.md`; hand-written Φ5
   roadmap (aggregator + risk allocator, NOT more strikers) in
   `reviews/phi41_squad_v1_addendum.md`.
5. [ ] Replace synthetic bars in the regime trainer with real parquet
   feeds from `multi-pair-trading-agent`'s data cache.
6. [ ] Hand-label the 30 disagreement bars seeded in
   `sim/regime/disagreements_for_review.csv` via the Streamlit tool
   at [`sim/regime/label_disagreements.py`](regime/label_disagreements.py)
   (Φ3-prep deliverable 2026-06-24) and extend to ≥ 200 hand-labelled
   bars for the G4 regime F1 gate.
7. [ ] Wire HRP allocator (F3 + F18) + chemical-reaction layer
   (F11 + F13) into the aggregator (currently a Φ2.5 stub). **HRP
   is the empirical remedy for BOTH Φ4 FAIL diagnosis #2 (Barou's
   right-tail-skewed contribution dilutes Isagi's median) AND Φ4.1's
   structural-crowd-out failure mode (per-agent risk budgeting +
   TQS-conditional conviction floor + same-direction merge instead
   of highest-conviction-wins).**
8. [ ] On the VM, run [`scripts/vm_calibrate_friction.py`](../scripts/vm_calibrate_friction.py)
   to calibrate friction against the live broker fills for
   EURUSD/GBPUSD/USDCAD, then commit the resulting
   `sim/core/friction_calibration_2026-06.json` via a single
   calibration commit.

## Determinism contract

09 §1.2 — given the same manifest `(seed, roster hash, data slice)`,
the engine emits byte-identical JSONL. Every stochastic operation
consumes a seed via `sim.core.seed.seed(agent_id, tick_id)` or
`seed_for(agent_id, tick_id, channel)`. Hard rules:

* No `random.random()` without a seeded generator.
* No `time.time()` in the decision path — bar timestamps only.
* No async I/O in the decision path — dashboard runs as a sidecar.

`tests/test_determinism.py` runs 5 replay cases and asserts byte
identity across re-runs.

## Calibration data

The friction model (`sim/core/friction.py`) targets the **June 2026
VM broker fills** on the Exness demo account (1:1000, $100 equity
profile) per 09 §1.8. The fills are not in this repo — they live in
the production repo's per-symbol log tree on the deployment VM:

```
~/Documents/TradingAgentLogs/{EURUSD,GBPUSD,USDCAD}/
  {SYMBOL}_YYYY-MM-DD.log          # text log, bracketed events
  near_misses/events.jsonl         # one JSON event per line
  losses/events.jsonl              # one JSON event per line
  ladders/events.jsonl             # one JSON event per line
```

`sim/core/friction.py` now ships the **calibration machinery**:

| Function | Role |
|---|---|
| `parse_text_log(path)` | regex-pair `[SIGNAL]` → `[TRADE OPENED]` on `(symbol, timeframe, alpha, direction)`; count `[ORDER REJECTED]` lines |
| `iter_vault_jsonl(path)` | tolerant JSONL reader for `near_misses` / `losses` / `ladders` |
| `calibrate_against_fills(symbol, log_root=None, atr_by_record=None)` | empirical distributions: median/p95 spread, median/p95 latency, partial-fill rate, rejection rate, ATR-aware slippage coefficient `k`. Returns a `CalibrationResult` with `n_orders == 0` when the log tree is absent on this host (the current Mac case) so callers fall back to defaults without raising. |
| `write_calibration_file(results, path=None)` | serialise per-symbol calibrations to `sim/core/friction_calibration_2026-06.json` (the canonical artefact) |
| `load_calibration(path=None)` | read the JSON and return `{symbol: FrictionConfig}` |
| `config_for_symbol(symbol, calibration_path=None)` | convenience wrapper used by the engine on a per-symbol basis; returns conservative defaults when no calibration is present |

**Current state on this Mac host (2026-06-24):**
`~/Documents/TradingAgentLogs/` only contains
`summaries/summary_2026-06-17_to_2026-06-23.txt`. There are no
per-symbol log directories yet (no live deployment trades in the
window). `friction_calibration_2026-06.json` is therefore **not yet
written**; the simulator falls back to the conservative
`FrictionConfig()` defaults documented in `09` §1.8. Calibration
runs on the VM in Φ3 and writes the JSON.

Calibration commit policy (research-standards §5):

1. Replay >= 20 demo orders through the simulator + production fills.
2. Estimate empirical distributions per symbol via
   `calibrate_against_fills(symbol, log_root=...)`; pass
   `atr_by_record` once the parquet-join utility is wired so the
   `k` regression has ATR-at-signal data.
3. Persist the result with `write_calibration_file(...)` →
   `sim/core/friction_calibration_2026-06.json`.
4. Bump only via a calibration commit; the prior value stays in
   git history.

## Training data contract

The regime classifier trains on 2015–2023, validates on 2024 per
09 §1.5. Inputs:

* `--train-parquet PATH` — OHLCV bar parquet with `open, high, low,
  close, volume` columns and a UTC `DatetimeIndex`.
* `--val-parquet PATH` — same schema, 2024 window.

If no parquet is supplied, the trainer generates a synthetic walk
that exercises all four classes (the rule-based labeller picks all
four). Synthetic mode is a smoke test, **not a substitute for real
data** — the G4 gate is only met by hand-labelled validation.

Real data lives in the production repo's parquet cache; M001's
data plane trajectory pins the path to `07-research-standards.md` §8.

## Cross-references

| What | Where |
|---|---|
| Replay-first kernel + numeric phase gates | `../09-experiment-architecture.md` |
| Thought Ledger + tier model | `../06-blue-lock-doctrine.md` §3.8, §3.9 |
| Schema (Thought / Coordinate / Proposal) | `../03-architecture-v0-sketch.md` §3 |
| F12 TQS, F17 ΔInfo, F18 regime KPIs | `../04-quant-foundations.md` |
| Dashboard panel inventory | `../08-dashboard-spec.md` §2 |
| Roster (10-agent canon) | `../05-agent-roster-v0.md` |
| E004 baseline (+11.34 pips/trade) | `docs/findings/2026-06-09_walk_forward_validation.md` |
| E001-E007 audit + conflab inheritance | `audits/2026-06-24_E001-E007_audit.md` §4 |
