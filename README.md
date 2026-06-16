# Finance Research Experiments

Central **research workshop** for hypothesis tests across the finance/trading
AI stack (forex agent today; portfolio agent and dividend agent next).
Observation-only — nothing here trades or changes any live agent without
that agent's own validation pipeline.

**Production agent:** [`multi-pair-trading-agent`](../multi-pair-trading-agent) (separate repo).

---

## Start here

| Doc | Purpose |
|---|---|
| [`EXPERIMENTS.md`](EXPERIMENTS.md) | Master index — every test E001+ |
| [`PROTOCOL_DISCIPLINE.md`](PROTOCOL_DISCIPLINE.md) | Binding rules (pre-reg, FDR, splits) |
| [`DATA_LEDGER.md`](DATA_LEDGER.md) | Which pair/TF/slice each experiment used |
| [`ai_context.md`](ai_context.md) | Compact state for fresh chats |

---

## Experiment timeline

| ID | What | Where |
|---|---|---|
| E001 | ICT concept ablation → zone survivor | Agent (documented here) |
| E002 | Zone definitive grid (13 BH cells) | Agent |
| E003 | Holdout IS/OOS | Agent |
| E004 | Walk-forward → H4/all deployed | Agent |
| E005 | Cross-pair frozen + sealed 2026 | Agent |
| E006 | Price-action confluence screening | Lab (`conflab/`, `output/`) |
| E007 | Impulse-origin bounce | Lab (`output/test_b/`) |

Each folder under [`experiments/`](experiments/) has `PROTOCOL.md`,
`REPORT.md`, and `MANIFEST.md`.

---

## Running lab code

```bash
# From finance-research-experiments root; uses agent venv + parquet cache
export PYTHONPATH=../multi-pair-trading-agent:.

../multi-pair-trading-agent/.venv/bin/python -m pytest -q

# E006 Stage 1 example
../multi-pair-trading-agent/.venv/bin/python scripts/run_stage1.py --symbol EURUSD

# E007 Stage 1 example
../multi-pair-trading-agent/.venv/bin/python scripts/test_b/run_stage1.py
```

---

## Adding a new experiment

1. Register **E0XX** in `EXPERIMENTS.md`.
2. Copy `experiments/_TEMPLATE/` → `experiments/E0XX_name/`.
3. Write and commit `PROTOCOL.md` **before** screening data.
4. Update `DATA_LEDGER.md` when Stage 1 starts.
5. Commit results + `REPORT.md` + `MANIFEST.md`.

---

## Legacy paths

Root `PROTOCOL.md`, `REPORT.md`, and `protocols/TEST_B_PROTOCOL.md` redirect
to **E006** / **E007** canonical folders. Scripts still write to `output/`
and `output/test_b/`; manifests link both paths.

Formal PDF: [`docs/reports/confluence_experiment_research_report.pdf`](docs/reports/confluence_experiment_research_report.pdf) (E006-era write-up).
