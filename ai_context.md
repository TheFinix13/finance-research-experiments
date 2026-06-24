# AI Context — finance research experiments (updated 2026-06-24)

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

### M001 multi-agent ensemble (doctrine)

- **v0.2 complete** (commits after `11cdde4`): Thought Ledger, F17/F18,
  `08-dashboard-spec.md`, charter §7, standards §10.
- **v0.3 landed:** `09-experiment-architecture.md` — replay-first kernel,
  numeric gates G1–G7, TQS-only optimisation, 4-agent Φ4 MVP roster.
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
| E006/E007 code | `conflab/`, `scripts/run_stage1.py`, `scripts/test_b/` |
| Outputs | `output/` (legacy paths; reorganise deferred — needs git mv + MANIFEST sync) |

Tests: **70** passing.
`PYTHONPATH=../multi-pair-trading-agent:. ../multi-pair-trading-agent/.venv/bin/python -m pytest -q`

## 3) Next immediate goal

**M001 Φ2.5:** simulator scaffold + data manifest + Streamlit v0 six panels
(per `09-experiment-architecture.md` G4). **E010:** finalise locked params
in PROTOCOL before Stage 1.

Parked: `output/` reorganisation; E009 cross-family; agent-side path
re-check after repo rename (audit follow-up).

Honesty rules: `PROTOCOL_DISCIPLINE.md`. M001 gates: `09` §1.5.
