# AI Context — finance research experiments (updated 2026-06-24, late evening)

Read this first in a fresh chat. This repo is the **central research workshop**.
Production execution lives in `multi-pair-trading-agent`; lab experiments never
auto-change live params.

**Index:** `EXPERIMENTS.md` · **Rules:** `PROTOCOL_DISCIPLINE.md` ·
**M001 program:** `programs/M001_multi_agent_ensemble/` (branch `multi-agent-ensemble`)

Parquet cache: `PYTHONPATH=../multi-pair-trading-agent:.` (no duplicate data).

## 1) What is built and working

### Lab Phase 1 (E001–E007) — closed

- Tag **`lab-phase-1-closed`** marks pre-M001 lab state (do not recreate).
- **E004** walk-forward: 7/7 OOS, median +11.34 pips/trade → deployed cell.
  Promoted: `docs/findings/2026-06-09_walk_forward_validation.md`.
- **E005** cross-pair: GBPUSD/USDCAD replicate; AUD/NZD excluded.
  Promoted: `docs/findings/2026-06-10_cross_pair_replication.md`.
- **E006** price-action: 5/284 alive; hour-matched controls (v2.1).
  Exploratory `equal_highs_pool` → `docs/findings/2026-06-12_equal_highs_pool_context.md`.
- **E007** impulse bounce: 0/12 alive; clean negative at Stage 1.
- Methodology promoted: `docs/methodology/` (hour_matched_controls,
  verdict_registry, exploratory_stage2, amendments).
- Audit: `audits/2026-06-24_E001-E007_audit.md`.

### M001 multi-agent ensemble (doctrine + Φ2.5 scaffold)

- **v0.2 complete** (commits after `11cdde4`): Thought Ledger, F17/F18,
  `08-dashboard-spec.md`, charter §7, standards §10.
- **v0.3 landed:** `09-experiment-architecture.md` — replay-first kernel,
  numeric gates G1–G7, TQS-only optimisation, 4-agent Φ4 MVP roster.
- **Φ2.5 scaffold landed:** `programs/M001_multi_agent_ensemble/sim/` —
  deterministic kernel (types/ledger/striker/engine/seed/friction/sentinel/
  aggregator), four-impl ledger, regime classifier (F1≈0.999 on synthetic,
  hand-labelled real-data validation deferred), TQS+ΔInfo+regime-KPI
  scoring, 4-agent MVP roster YAML + 10-agent canon YAML, agent stubs for
  A1/A6/A7/A10, Streamlit v0 dashboard (six panels render with placeholder
  data on `127.0.0.1:8501`).
- **Φ3-prep (2026-06-24 late):** two Φ3 entry blockers closed.
  *Friction:* full calibration machinery wired in `sim/core/friction.py`
  (text-log parser, JSONL vault reader, ATR-aware k estimator,
  `load_calibration()` JSON loader) plus `test_friction_calibration.py`
  (12 unit tests + 1 skip for absent real data). No fills on this Mac
  host — only `~/Documents/TradingAgentLogs/summaries/` weekly text —
  so `friction_calibration_2026-06.json` runs on the VM in Φ3; defaults
  stay conservative. *Regime:* `sim/regime/validate_real.py` runs the
  trained classifier on real EURUSD H4 2024 vs heuristic weak labels
  (priority `news>vol_spike>trending>chop`); first run macro
  agreement F1 = **0.496** (per-class trending 0.92, chop 0.96,
  vol_spike 0.10, news 0.00 / support=0 because FF feed is current-week
  only). 30 disagreements saved to `sim/regime/disagreements_for_review.csv`
  for hand-labelling.
- **Φ3 v1 (2026-06-24 late) — A1 Isagi v1 wrapper PASS:**
  `sim/agents/a01_isagi.py` wraps production
  `agent.alphas.concepts.zone_alpha.SupplyDemandAlpha` at locked E004
  params (`htf_align=D1`, `htf_align_mode=against`, `htf_lookback=10`,
  `htf_min_move_pips=60`, `target_rr=1.5`) via the cross-repo import
  contract (`sim/_cross_repo.py` — `M001_PRODUCTION_REPO` env var).
  Φ3→Φ4 gate harness in `sim/scoring/run_isagi_phi3_gate.py` ran
  EURUSD H4 2015-2025 (17 723 bars, 856 trades, 7 windows): **verdict
  `PASS`** — median OOS-window mean **+11.04 pips/trade** vs Sae
  **+11.34** (drift **−2.7 %**, within ±5 %); **7/7 OOS windows
  positive**; mean TQS 0.317. Report:
  `programs/M001_multi_agent_ensemble/reviews/phi3_gate_isagi_v1.md`
  + per-trade JSONL ledger. Tier-3 `RedactedLedger` produces
  byte-identical proposals to `FullLedger` (proven in
  `tests/test_a01_isagi_wrap.py`). **137 tests passing + 3 skipped**
  (70 lab + 67 sim; +12 new Φ3 tests).
- Branch: **`multi-agent-ensemble`** only for M001; structure docs on same branch.

### Planned

- **E010** Stage-2b `equal_highs_pool` — skeleton pre-reg at
  `experiments/E010_equal_highs_pool_stage2b/PROTOCOL.md`; parallel with M001.
- E008 skipped per M001 standards §10.3; E009 cross-family parked.

## 2) Key file paths

| Area | Files |
|---|---|
| Registry | `EXPERIMENTS.md`, `DATA_LEDGER.md`, `PROTOCOL_DISCIPLINE.md` |
| Findings | `docs/findings/2026-06-09_*.md`, `2026-06-10_*.md`, `2026-06-12_*.md` |
| Methodology | `docs/methodology/*.md` |
| Audits | `audits/README.md`, `audits/2026-06-24_E001-E007_audit.md` |
| M001 doctrine | `programs/M001_multi_agent_ensemble/00`–`09` + `README.md` |
| M001 Φ2.5 sim | `programs/M001_multi_agent_ensemble/sim/{core,regime,scoring,roster,agents,dashboard,tests}/` + `sim/README.md` + `sim/regime/README.md` (Φ3-prep) |
| M001 Φ3-prep artefacts | `sim/regime/validate_real.py`, `sim/regime/validation_2024_eurusd_h4.json`, `sim/regime/disagreements_for_review.csv`, `sim/tests/test_friction_calibration.py` |
| M001 Φ3 v1 artefacts | `sim/_cross_repo.py`, `sim/agents/a01_isagi.py` (A1IsagiV1 wrapper), `sim/scoring/run_isagi_phi3_gate.py`, `sim/tests/test_a01_isagi_wrap.py`, `sim/tests/test_phi3_gate.py`, `programs/M001_multi_agent_ensemble/reviews/phi3_gate_isagi_v1.md` (+ `*_trades.jsonl`) |
| E006/E007 code | `conflab/`, `scripts/run_stage1.py`, `scripts/test_b/` |
| Outputs | `output/` (legacy paths; reorganise deferred — needs git mv + MANIFEST sync) |

Tests: **137** passing + **3 skipped** (70 pre-existing lab + 67 sim).
`PYTHONPATH=../multi-pair-trading-agent:. M001_PRODUCTION_REPO=../multi-pair-trading-agent ../multi-pair-trading-agent/.venv/bin/python -m pytest -q`

## 3) Next immediate goal

**M001 Φ3 (remaining):** wrapper is done (A1 Isagi v1 PASS, see above).
Remaining Φ3 → Φ4 work: replace synthetic regime-trainer bars with real
parquet feeds; **hand-label the 30 disagreement bars in
`sim/regime/disagreements_for_review.csv`** and extend to ≥ 200 bars for
the G4 F1 ≥ 0.75 gate; wire HRP allocator + chemical-reaction layer
(F11/F13) into the aggregator; **on the VM, run
`calibrate_against_fills(symbol, ...)` for each of EURUSD/GBPUSD/USDCAD
and bump friction defaults via a single calibration commit**.
**E010:** finalise locked params in PROTOCOL before Stage 1.

Parked: `output/` reorganisation; E009 cross-family; agent-side path
re-check after repo rename (audit follow-up).

Honesty rules: `PROTOCOL_DISCIPLINE.md`. M001 gates: `09` §1.5.
