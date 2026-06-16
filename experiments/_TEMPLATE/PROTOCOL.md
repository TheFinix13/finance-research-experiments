# Experiment protocol template

Status: **TEMPLATE** — copy to `experiments/E0XX_short_name/PROTOCOL.md` and
fill before any data run. Follow `PROTOCOL_DISCIPLINE.md`.

Register ID in `EXPERIMENTS.md` first.

---

## 1. Hypothesis (operational)

> State H0 and H1 in testable form. Include the exact outcome metric.

## 2. Separation

- Does this touch the trading agent? (must be **no** for execution changes)
- Which prior experiments used the same data slice? (cite `DATA_LEDGER.md`)

## 3. Locked parameters

| Knob | Value | Rationale |
|---|---|---|
| … | … | … |

## 4. Statistical pipeline

| Stage | Pairs | Period | Family size | FDR |
|---|---|---|---|---|
| 1 screen | | | | BH α=0.05 |
| 2 confirm | | | | per-cell α=0.05 |

## 5. Stop rules

- If … → STOP; report honestly.

## 6. Amendments

(Appended after pre-registration commits only.)

---

**Pre-registration commit:** _(hash after push)_
