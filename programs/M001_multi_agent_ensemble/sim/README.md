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
  scoring/      F12 TQS · F17 ΔInfo · F18 regime-conditional KPIs
  roster/       mvp_phi4.yaml (4-agent Φ4 v1) + full_canon.yaml (10-agent target)
  agents/       Phi2.5 stubs: a01_isagi, a06_nagi, a07_barou, a10_kunigami, placeholder
  dashboard/    Streamlit v0 (six panels per `08-dashboard-spec.md`)
  tests/        determinism, ledger look-ahead, friction, sentinel, seed
```

## Quickstart

### 1. Run the test suite

```bash
PYTHONPATH=../multi-pair-trading-agent:. \
  ../multi-pair-trading-agent/.venv/bin/python \
  -m pytest programs/M001_multi_agent_ensemble/sim/tests/ -q
```

Expected: 55 tests pass + 1 skipped (the skipped one is the real-data
friction-calibration bounds test, which lights up automatically once
`sim/core/friction_calibration_2026-06.json` is present). The full
repo suite reports 125 passing + 1 skipped (70 pre-existing lab + 55
sim + the skip).

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
| Regime classifier: macro-regime labels achieve holdout F1 >= 0.75 vs hand-labelled validation set (>= 200 bars) | **research debt acknowledged**: synthetic F1=0.999 is circular (trains and scores against the same rule); real-data weak-label agreement F1=**0.496** on EURUSD H4 2024 (vs the heuristic rules; `vol_spike`/`news` drag the macro). 30 disagreements saved to `sim/regime/disagreements_for_review.csv` for human labelling — see `sim/regime/README.md` for the interpretation guide |
| Friction model calibrated against June 2026 VM broker fills (09 §1.8) | **machinery in place, data deferred**: text-log parser, JSONL vault reader, ATR-aware k estimator, and `load_calibration()` JSON loader all wired in `sim/core/friction.py`. No real fills on this Mac host (only `~/Documents/TradingAgentLogs/summaries/` weekly text); calibration runs on the VM in Phi3 and writes `sim/core/friction_calibration_2026-06.json`. Defaults remain conservative. |
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

## Phi3 build order (next phase)

Per architecture §10 and 09 §2:

1. [x] Wire the production `zone_d1_against` cell into `A1IsagiV1.intend`
   via cross-repo import (`PYTHONPATH=../multi-pair-trading-agent:.` or
   `M001_PRODUCTION_REPO=...`).
2. [x] Φ3 gate (A1 Isagi v1) — **PASS @ +11.04 median OOS pips/trade**
   (drift −2.7 % vs Sae +11.34; 7/7 OOS windows positive). Review:
   `reviews/phi3_gate_isagi_v1.md`.
3. [ ] Replace synthetic bars in the regime trainer with real parquet
   feeds from `multi-pair-trading-agent`'s data cache.
4. [ ] Hand-label the 30 disagreement bars seeded in
   `sim/regime/disagreements_for_review.csv` (Φ3-prep deliverable
   2026-06-24) and extend to ≥ 200 hand-labelled bars for the G4
   regime F1 gate.
5. [ ] Wire HRP allocator (F3 + F18) + chemical-reaction layer
   (F11 + F13) into the aggregator (currently a Φ2.5 stub).
6. [ ] On the VM, run `calibrate_against_fills(symbol, log_root=...)`
   for each of EURUSD/GBPUSD/USDCAD, persist via
   `write_calibration_file(...)`, and bump the friction defaults via a
   single calibration commit.

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
