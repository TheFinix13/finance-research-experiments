# E010 — Stage-2b: H1 `equal_highs_pool` context validation

**Status:** PRE-REGISTRATION SKELETON · **Date:** 2026-06-24 ·
**Parallel with:** M001 program (`programs/M001_multi_agent_ensemble/`)

Follow [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md). Register
in [`EXPERIMENTS.md`](../../EXPERIMENTS.md).

---

## 1. Hypothesis (operational)

**Prior (exploratory only):** E006 exploratory Stage 2 found H1
`equal_highs_pool` as context lifted every tested M15 setup by +0.10 to
+0.46 ATR on the selection term. See
[`docs/findings/2026-06-12_equal_highs_pool_context.md`](../../docs/findings/2026-06-12_equal_highs_pool_context.md).

**H0:** Conditional on M15 setup events, H1 `equal_highs_pool` active
within the pre-registered lookback does **not** increase directional MFE
vs the setup's marginal MFE alone (selection term ≤ 0).

**H1:** Selection term (joint MFE − setup marginal MFE) is **positive**
and survives BH-FDR 5 % across the pre-declared family of M15 setups
tested under `equal_highs_pool` context.

**Outcome metric:** mean MFE difference in ATR(14) units; hour-matched
random controls per [`docs/methodology/hour_matched_controls.md`](../../docs/methodology/hour_matched_controls.md).

## 2. Separation

- **Trading agent:** no execution changes. Candidate primitive for M001
  A6 Nagi / A1 Isagi v2 only after `alive` verdict here.
- **M001 coupling:** runs in parallel; Nagi deployment-grade confluence
  waits for E010 `alive` on H1 `equal_highs_pool` (per
  `07-research-standards.md` §10.1).
- **Data slices:** check [`DATA_LEDGER.md`](../../DATA_LEDGER.md) before
  Stage 1. Screen split must not overlap E006 confirm/sealed claims.

## 3. Locked parameters (to finalise before first run)

| Knob | Proposed value | Rationale |
|---|---|---|
| Context TF | H1 | Matches exploratory finding |
| Setup TF | M15 | Survivor TF from E006 Stage 1 |
| Context detector | `equal_highs_pool` (`conflab/detectors_liquidity.py`) | Frozen definition from E006 |
| Setup family | E006 Stage-1 `alive` + `parked_weak_effect` M15 cells | Pre-declared list committed before peek |
| Lookback for pool | TBD (match E006 detector default) | Lock in amendment 0 if changed |
| Control | Hour-matched random, 5× draws | E006 v2.1 recipe |
| n_perm | 2,000 | Match E006 Stage 1 |
| n_gate (alive eligibility) | 100 | Match E006 screen |
| FDR | BH α = 0.05 across setup family | Standard |

## 4. Statistical pipeline

| Stage | Pairs | Period | Family | FDR |
|---|---|---|---|---|
| 1 screen | EURUSD | 2015 → 2021 | \|setup family\| cells | BH α=0.05 |
| 2 confirm | EURUSD | 2022 → 2024 | Stage-1 survivors only | per-cell α=0.05 |
| 3 cross-pair | GBPUSD | 2015 → 2021 | survivors only | per-cell α=0.05 |

Displacement null and hour-restricted re-draws per `conflab/stage2.py`.

## 5. Stop rules

- If **0 setups** survive Stage 1 with `alive` → STOP; report negative
  on the exploratory prior; M001 uses primitive as parked only.
- If confirm fails for all survivors → STOP at Stage 2; no sealed run.
- Exploratory sub-runs (if any) labelled per
  [`docs/methodology/exploratory_stage2.md`](../../docs/methodology/exploratory_stage2.md).

## 6. Verdict registry

Four-tier per [`docs/methodology/verdict_registry.md`](../../docs/methodology/verdict_registry.md).

## 7. Amendments

_(None — append here before any locked-parameter change.)_

---

**Pre-registration commit:** _(pending first commit of this file)_
