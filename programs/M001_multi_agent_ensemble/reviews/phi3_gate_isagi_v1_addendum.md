# Phi3 gate -- A1 Isagi v1 -- addendum under locked verdict-comparator registry

**Addendum date:** 2026-06-24

**Addendum author:** verdict-comparator-discipline worker.

**Original report (preserved, not modified):** `reviews/phi3_gate_isagi_v1.md`.

**Binding rule applied:** `docs/methodology/gate_verdict_registry.md`
v0.1 + `07-research-standards.md` §11 (verdict-comparator discipline).

---

## Context — why an addendum

Two M001 phase-gate evaluations have landed (Φ3 PASS, Φ4 FAIL) and each
used a different aggregating statistic. The Φ3 worker initially flagged
a possible FAIL on this gate until the comparator was clarified by hand
against E004; the Φ4 worker correctly used median-of-OOS-window mean-TQS
but that statistic hides a property of one of the new agents. To remove
that degree of freedom for future gates, the verdict-comparator registry
locks the statistic per gate **before** the evaluation is run. This
addendum re-evaluates the Φ3 PASS verdict under the locked rule. The
original report is preserved in place per the registry's amendment
procedure (no in-place rewrites of sealed reviews).

## Statistic used in the original report

The Φ3 v1 report reported the comparator on this exact line:

> "Comparator: **median across 7 OOS windows of each window's mean
> per-trade pip expectancy**. This is the same statistic E004's
> headline reports."
> (`reviews/phi3_gate_isagi_v1.md`, "Apples-to-apples vs Sae (E004)").

The verdict line on the same page:

> "median OOS-window mean pips/trade +11.04 within ±5 % of Sae (+11.34);
> 7/7 OOS windows positive."

I.e. the Φ3 worker decided the PASS on **median across OOS windows of
per-window mean per-trade pips**, against the E004 baseline of
**+11.34 pips/trade**, with a ±5 % PASS band.

## Newly-locked statistic for this gate

Per `docs/methodology/gate_verdict_registry.md` v0.1, the registry row
for this gate is:

| Gate ID | Locked statistic | Comparator | PARTIAL band | PASS band |
|---|---|---|---|---|
| **G4** (Φ3 → Φ4 replay fidelity) | Median across OOS windows of per-window mean per-trade pips | E004 frozen baseline +11.34 pips/trade across 7 OOS windows | 5 % < \|Δ\| ≤ 10 % | \|Δ\| ≤ 5 % |

This is **identical** to the statistic the Φ3 worker used. The Φ3 v1
report decided the verdict under the very statistic that the registry
later locked, so the registry endorses the original choice; no swap is
required.

## Verdict under the locked rule

Recomputed from `reviews/phi3_gate_isagi_v1_trades.jsonl` for
transparency (numbers match the original report byte-for-byte; the
trade journal is the same one the original report rolled up):

| OOS year | n trades | Mean pips/trade |
|---|---|---|
| 2019 | 50 | +17.37 |
| 2020 | 77 | +12.25 |
| 2021 | 62 | +6.44 |
| 2022 | 119 | +3.61 |
| 2023 | 63 | +5.38 |
| 2024 | 43 | +12.99 |
| 2025 | 50 | +11.04 |

Sorted across windows: `[+3.61, +5.38, +6.44, +11.04, +12.25, +12.99,
+17.37]`. **Median = +11.04 pips/trade.**

Δ vs E004 baseline = (+11.04 − +11.34) / 11.34 = **−2.7 %**.

|Δ| = 2.7 % ≤ 5 % PASS band → **PASS**.

**Sub-gate status (informational; the original Φ3 report did not gate
on these and the addendum does not promote them to binding without a
separate amendment):**

- Regime macro-F1 ≥ 0.75 vs ≥ 200-bar hand-labelled set — current
  status is **F1 = 0.496** on 30 disagreement bars pending hand-label
  (`sim/regime/validation_2024_eurusd_h4.json`). This is below the 0.75
  G4 sub-gate floor. The original Φ3 report and `ai_context.md` already
  flag this as a Φ4 carryover ("hand-label 30 disagreement bars …
  extend to ≥ 200 for the G4 F1 ≥ 0.75 gate"). The locked-rule rewrite
  does **not** change that status — it just makes explicit that the G4
  sub-gate is not yet cleared. The pip-replay-fidelity PASS stands;
  the regime sub-gate remains an open carryover.
- Six dashboard panels render — confirmed in the Φ2.5 scaffold landing
  (`sim/dashboard/`). Sub-gate cleared.

## Cross-statistic diagnostic (journalled, not scored)

Reproduced for transparency. Numbers from
`reviews/phi3_gate_isagi_v1_trades.jsonl`:

| Statistic | Isagi v1 |
|---|---|
| **Median OOS-window mean-pips (locked statistic)** | **+11.04** |
| Mean OOS-window mean-pips | +9.87 |
| Pooled per-trade mean pips | +6.28 |
| Pooled per-trade median pips | −11.28 |
| Pooled per-trade mean TQS (F12) | 0.3150 |
| Pooled per-trade median TQS (F12) | 0.0000 *(structural zero, target_rr=1.5; see `04-quant-foundations.md` F12)* |
| Median OOS-window mean-TQS | 0.3175 |
| Mean OOS-window mean-TQS | 0.3320 |
| Cumulative pips (all OOS trades) | +5379.92 |
| Hit rate | 48.60 % |

The locked statistic landed at the same value the original report
reported; no other statistic was used as the comparator at this gate, so
no re-decision is necessary. The other rows are diagnostic only and do
not override the locked verdict.

## Final restated verdict under the locked rule

**Phi3 → Phi4 (G4) replay-fidelity gate: `PASS`.**

The original Φ3 PASS verdict holds verbatim under the registry's locked
rule. The locked statistic equals the statistic the original worker
used; the numbers do not change; the verdict does not change.

The G4 sub-gates that the original Φ3 report did not block on (regime
macro-F1 ≥ 0.75; six dashboard panels render) carry over unchanged: six
panels green, regime F1 still under-threshold pending the 30-bar
disagreement hand-labelling extension to ≥ 200 bars
(`ai_context.md` "Next steps" item 4).

## References

- Original Φ3 report: `reviews/phi3_gate_isagi_v1.md`
- Per-trade journal: `reviews/phi3_gate_isagi_v1_trades.jsonl`
- Verdict-comparator registry: `docs/methodology/gate_verdict_registry.md`
- Research-standards binding rule: `07-research-standards.md` §11
- Architecture spec G4: `09-experiment-architecture.md` §1.5
- E004 baseline: `docs/findings/2026-06-09_walk_forward_validation.md`
