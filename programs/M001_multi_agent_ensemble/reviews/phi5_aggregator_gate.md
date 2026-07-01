# Phi5 aggregator selection experiment -- verdict

**Run date:** 2026-07-01T01:31:51.029327+00:00

**Protocol:** `experiments/phi5_aggregator/PROTOCOL.md` (pre-registered 2026-06-25; amended 2026-06-30 §11.1 + §11.2)

**Statistic (locked, inherited from G6):** median across OOS windows of per-window mean TQS (F12)

**Control (Arm 0, Phi4.1):** 0.2922 TQS; Isagi-alone reference: 0.3175 TQS.

---

## Partial-verdict framing

Per PROTOCOL §6 stop rule #2 (retained after §11.1 amendment), when the compute time-box precludes running every arm, ship the arms that DID complete and mark the others REQUIRES_RESIM. This run computes Arms 0, 1, 2 post-hoc from the Phi4.1 artefacts. Arms 3, 4, 5 require a full re-simulation (`_drive_squad_replay` plumbed to arm-specific aggregators) which is a follow-up phase.

---

## Locked-statistic verdict table


| Arm | n trades | Median window mean TQS | Δ vs control | Ratio vs Isagi | Verdict |
|---|---|---|---|---|---|
| **arm0** (Control (Phi4.1 aggregator)) | 3714 | 0.2922 | +0.0000 | 0.92x | `baseline` |
| **arm1** (HRP (Ledoit-Wolf tangency, TQS covariance)) | 3714 | 0.2941 | +0.0019 | 0.93x | `PARTIAL` |
| **arm2** (TQS-conditional conviction floor (P=0.40, min_n=200)) | 3372 | 0.3109 | +0.0187 | 0.98x | `PARTIAL` |
| **arm3** (Same-direction merge (tightest SL, median TP)) | 0 | — | — | — | `REQUIRES_RESIM` |
| **arm4** (Multi-position per symbol (K=2 + R6 cap)) | 0 | — | — | — | `REQUIRES_RESIM` |
| **arm5** (Combined (floor -> merge -> multi-position -> HRP)) | 0 | — | — | — | `REQUIRES_RESIM` |

---

## Cross-statistic robustness table


Locked statistic (median-of-window-mean TQS) is bolded. Reported alongside per PROTOCOL §4 cross-statistic discipline.


| Arm | **Median WM TQS** | Mean WM TQS | Pooled TQS | Pooled pips |
|---|---|---|---|---|
| arm0 | **0.2922** | 0.2956 | 0.2955 | +9.49 |
| arm1 | **0.2941** | 0.2514 | 0.2941 | +9.49 |
| arm2 | **0.3109** | 0.3082 | 0.3030 | +10.47 |
| arm3 | **—** | — | — | — |
| arm4 | **—** | — | — | — |
| arm5 | **—** | — | — | — |

---

## Per-arm details


### arm0 -- Control (Phi4.1 aggregator)

- **Verdict:** `baseline`
- **Median window mean TQS:** 0.2922
- **n trades:** 3714
- **n OOS windows with trades:** 7
- _Caveat:_ Locked control value from Phi4.1: median = 0.2922. This harness's re-computation should agree within a few basis points (any difference is arithmetic noise, not a re-derivation).

### arm1 -- HRP (Ledoit-Wolf tangency, TQS covariance)

- **Verdict:** `PARTIAL`
- **Median window mean TQS:** 0.2941
- **n trades:** 3714
- **n OOS windows with trades:** 7
- _Caveat:_ Post-hoc re-weighting only -- production HRP scales lot size, which alters pnl_pips. In the fixed-lot sim harness this effect is folded into the WEIGHTED-mean TQS statistic, which is the closest post-hoc analogue.
- _Caveat:_ First window has empty prior history -> HRP falls back to equal-weight-on-positive-mean (documented in HRP fallback).

### arm2 -- TQS-conditional conviction floor (P=0.40, min_n=200)

- **Verdict:** `PARTIAL`
- **Median window mean TQS:** 0.3109
- **n trades:** 3372
- **n OOS windows with trades:** 7
- _Caveat:_ Dropped 342 trades below per-agent P40 conviction (walk-forward, no lookahead).
- _Caveat:_ 5 trades had no matched proposal (conviction=None) -- retained as free-pass to avoid biasing against the arm.

### arm3 -- Same-direction merge (tightest SL, median TP)

- **Verdict:** `REQUIRES_RESIM`
- _Caveat:_ Merging changes SL (tightest) and TP (median-of-ladder-target). Trade outcomes with the modified SL/TP cannot be recomputed post-hoc without the H4 price paths and the production fill model. Requires a full re-simulation via `_drive_squad_replay` with the aggregator plumbed to `apply_same_direction_merge`.

### arm4 -- Multi-position per symbol (K=2 + R6 cap)

- **Verdict:** `REQUIRES_RESIM`
- _Caveat:_ Admitting a second concurrent position per symbol requires trade outcomes for previously-rejected proposals; those outcomes depend on H4 price paths not preserved in the artefacts. Requires a full re-simulation with the aggregator plumbed to `admit_proposals`. Sentinel R6 wiring is already in place (`sim/core/sentinel.py::check_r6_per_symbol_risk_cap`).

### arm5 -- Combined (floor -> merge -> multi-position -> HRP)

- **Verdict:** `REQUIRES_RESIM`
- _Caveat:_ The stack includes Arms 3 and 4 which require re-simulation. A partial stack (Arms 1 + 2 alone) is computable but does not match the pre-registered order-of-operations; reporting it would blur the verdict. Full stack requires the same re-sim path as Arms 3 and 4.

---

## Follow-up (Phase 6e)


Ship the full-sim harness path for Arms 3, 4, 5 by plumbing the aggregator arms into `sim/scoring/run_phi4_squad_gate.py::_drive_squad_replay` as an injectable strategy. Then run the 5-arm x 7-window grid.

## Cross-references


- Protocol: `experiments/phi5_aggregator/PROTOCOL.md`
- HRP notes: `experiments/phi5_aggregator/HRP_NOTES.md`
- Locked statistic: `docs/methodology/gate_verdict_registry.md` (G6 row)
- Phi4.1 artefacts: `reviews/phi41_squad_v1_trades.jsonl`, `reviews/phi41_squad_v1_proposals_all.jsonl`
- Verdict-comparator discipline: `programs/M001_multi_agent_ensemble/07-research-standards.md` §11

