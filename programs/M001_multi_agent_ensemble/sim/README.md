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

Expected: 43 tests pass. The full repo suite (including `tests/`) reports
113 passing (70 pre-existing lab + 43 sim).

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

| Criterion | Status (Phi2.5 scaffold) |
|---|---|
| Replay fidelity: simulator median pips/trade per rolling OOS window reproduces E004 `zone_d1_against / H4 / all` baseline **±5 %** per window (reference +11.34 pips/trade) | **deferred** — requires Phi3 cross-repo import of the production `zone_d1_against` cell + parquet bar feed |
| Regime classifier: macro-regime labels achieve holdout F1 >= 0.75 vs hand-labelled validation set (>= 200 bars) | **scaffold passes on synthetic** (F1 ~ 0.999); real hand-labelled validation set is a Phi3 deliverable |
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

## Phi3 build order (next phase)

Per architecture §10 and 09 §2:

1. Wire the production `zone_d1_against` cell into `IsagiYoichi.intend`
   via cross-repo import (PYTHONPATH=../multi-pair-trading-agent:.).
2. Replace synthetic bars in the regime trainer with real parquet
   feeds from `multi-pair-trading-agent`'s data cache.
3. Add a hand-labelled validation set (>= 200 bars) for the G4
   regime F1 gate.
4. Wire HRP allocator (F3 + F18) + chemical-reaction layer (F11 + F13)
   into the aggregator (currently a Phi2.5 stub).
5. Run the first replay fidelity check vs E004's +11.34 pips/trade
   baseline; tune friction calibration constants against the June 2026
   VM broker fills (production repo log path; see Calibration below).

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
profile) per 09 §1.8. The fills CSV is **not in this repo** — it
lives in the production repo at:

```
~/Documents/TradingAgentLogs/<june_2026>/*.csv
```

`sim/core/friction.py` carries a `TODO: calibrate against {fills_path}`
marker on the calibration block. The `calibrate_against_fills` stub
raises `NotImplementedError` with the expected import path. Calibration
is **deferred to Phi3** when the cross-repo data pipe is wired.

Calibration commit policy (research-standards §5):

1. Replay >= 20 demo orders through the simulator + production fills.
2. Sweep `k ∈ {0.02, 0.03, ..., 0.10}` and
   `reject_prob ∈ {0.005, 0.01, 0.02}` to minimise median |Δprice|.
3. Freeze calibrated values in a new `sim/friction.yaml`.
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
