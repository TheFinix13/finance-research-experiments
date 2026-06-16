# AI Context — confluence lab (updated 2026-06-16)

Read this first in a fresh chat. This repo is the **central research workshop**
for all hypothesis tests. The trading agent (`eurusd-ai-agent`) executes only
what survived the agent validation chain (E001–E005); lab experiments (E006+)
never auto-change live params.

**Index:** `EXPERIMENTS.md` · **Rules:** `PROTOCOL_DISCIPLINE.md` ·
**Data accounting:** `DATA_LEDGER.md`

Parquet cache: borrow via `PYTHONPATH=../eurusd-ai-agent:.` (no duplicate data).

## 1) What is built and working

### Agent validation chain (documented retrospectively as E001–E005)

- **E001** concept ablation: 6 ICT concepts eliminated; zone sole survivor;
  `zone_d1_against` (fade H4 zone against D1) discovered.
- **E002** zone grid: 13 BH cells on full window (candidate list only).
- **E003** holdout: 1/8 IS-survivors OOS — selection-bias lesson.
- **E004** walk-forward: `H4/all` 7/7 positive OOS windows, median +11.34
  pips/trade → deployed cell.
- **E005** cross-pair frozen: GBPUSD +10.24/trade p=0.001; USDCAD +4.63
  p=0.028; AUD/NZD excluded. Sealed 2026: 16 trades +7.75/trade p=0.29.

Agent code stays in `eurusd-ai-agent`; reports copied under `experiments/E00X/`.

### Lab experiments (pre-registered in this repo)

- **E006** price-action confluence (legacy Test A): 18 detectors, 76 event
  types; hour-matched controls (v2.1); 5/284 alive on EURUSD screen; gate-
  sized effects only. Canonical: `experiments/E006_test_a_price_action/`.
- **E007** impulse-origin bounce: 0/12 alive; bounce ≈ random hour-matched
  levels; stop at Stage 1. Canonical: `experiments/E007_impulse_origin_bounce/`.

### Planned

- **E008** technical indicators only (v2-PROTOCOL "Test B" family).
- **E009** cross-family A×B (v2-PROTOCOL "Test C").
- **E010** Stage-2b `equal_highs_pool` context (from E006 exploratory).

## 2) Key file paths

| Area | Files |
|---|---|
| Registry | `EXPERIMENTS.md`, `DATA_LEDGER.md`, `PROTOCOL_DISCIPLINE.md` |
| Experiments | `experiments/E001_…` through `E007_…`, `experiments/_TEMPLATE/` |
| E006 code | `conflab/detectors_*.py`, `conflab/screening.py`, `scripts/run_stage1.py` |
| E007 code | `conflab/detectors_impulse_return.py`, `conflab/friction.py`, `scripts/test_b/` |
| Shared stats | `conflab/stats.py` |
| Outputs | `output/` (E006), `output/test_b/` (E007) |

Tests: **70** passing. Run:
`PYTHONPATH=../eurusd-ai-agent:. ../eurusd-ai-agent/.venv/bin/python -m pytest -q`

## 3) Next immediate goal

**Use the registry for every new hypothesis.** Before screening:

1. Assign E0XX in `EXPERIMENTS.md`.
2. Pre-register in `experiments/E0XX_*/PROTOCOL.md`.
3. Check `DATA_LEDGER.md` — prefer pristine slices (USDCAD H1/M15, etc.).
4. Never import lab findings into agent execution without agent validation.

Parked: E010 Stage-2b; E008 indicators; E009 cross-family; D1 power redesign.

Honesty rules binding: see `PROTOCOL_DISCIPLINE.md`.
