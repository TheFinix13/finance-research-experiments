# E019 — Stop Notice: risk-adjusted recovery fails the primary gate (`dead`)

**Date:** 2026-07-14 · **Status:** `dead` / STOP (Phase 3 blocked) · **Protocol:** [`PROTOCOL.md`](PROTOCOL.md)

## Gate condition (as pre-registered)

> **`alive` → advance to Phase 3** iff, for at least one frozen §4 config, GR-S
> beats AK on `RaC_β` (GR-S bootstrap-95 % CI lower bound **>** AK point
> estimate) **robust across both DGPs and both correlation settings**, with the
> capital-preservation, operational, gauge-convergence and replay guardrails all
> satisfied.
> **`dead` / STOP (keep AK, write `STOP_NOTICE.md`)** — GR-S does **not** beat AK
> on `RaC_β`, or degrades a guardrail, or the gauge check fails.
> — `PROTOCOL.md` §6

## What Phase 2 found (N = 10,000 paths, seed 42, 11,000-day horizon, 6 cells)

**Primary metric `RaC_β = AnnRet / CDaR_β` (β = 0.95): GR-S loses to AK in every
cell, for every config.** 36/36 per-cell `primary_win = False`; bootstrap
one-sided superiority p-value = 1.000 throughout.

| Cell | AK median `RaC_β` | best GR-S median `RaC_β` |
|---|---:|---:|
| bootstrap, ρ=0.0 | **12.93** | 0.063 |
| bootstrap, ρ=0.5 | **11.59** | 0.055 |
| synthetic p=0.40, ρ=0.0 | 0.012 | −0.012 |
| synthetic p=0.40, ρ=0.5 | 0.005 | −0.012 |
| synthetic p=0.55, ρ=0.0 | **15.46** | 0.099 |
| synthetic p=0.55, ρ=0.5 | **14.17** | 0.082 |

**Root cause.** GR-S cuts CDaR (~0.027 vs AK ~0.097) and worst-path drawdown
(0.089 vs 0.355) and, in the zero-edge regime, risk-of-ruin (0.00 vs 0.38–0.41),
but its **annualised return collapses to ≈ 0.2 %/yr** (AK ≈ 125 %/yr) because the
equity gauge suppresses real exposure whenever equity is off its peak. A
return-per-drawdown ratio with a ≈ 0 numerator cannot beat a compounding
baseline — E017's terminal-equity failure re-appears one level up, now under the
risk-adjusted metric that was supposed to fix it.

Supporting checks:

- **Guardrails** (DD / ruin / time-to-resume): GR-S **passes** all — it is the
  *safer* arm — but guardrails are floors, not the pre-registered decision
  variable, and cannot be promoted to primary to manufacture a win (§7).
- **H2** (shadow vs time-decay): GR-S ≈ GR-T on `RaC_β` (rel diff ≤ 1.2 %) —
  `shadow_adds_value_any = false`.
- **Gauge convergence** (§4a): max pairwise disagreement = 0.0 — **PASS**.
- **Multiplicity** (§7): BH-FDR rejects no null (all p = 1.000); PBO = 0.0;
  deflated z = −0.39.
- **Incident replay** (descriptive): AK auto-clears (~12 h vs old HK 50.9 h),
  GR-S 0 h, protective close preserved, no premature reopen.

## Decision

**Phase 3 production wiring does not proceed.** The shipped 2026-07-14 daily-DD
auto-clear (AK) remains the production risk overlay in `multi-pair-trading-agent`.
No `ConfidenceGuard`, shadow tracker, or graduated recovery law lands in the live
agent on this evidence. Verdict label: **`dead`**.

Operationally this coincides with the spirit of H3 (`parked_baseline_sufficient`)
— the cheap shipped fix is enough — but the frozen gate returns `dead` because
GR-S is materially **worse** (not tied) on the primary, which is the §6
`dead`/STOP condition verbatim.

## Re-opening conditions

1. A **new study id (E020+)** with a fresh pre-registration. No post-freeze
   retune of E019's §4/§5 constants, primary metric, arms, or gate.
2. A defensible reframe must pre-register **either** a loss-regime-conditioned
   objective under which capital preservation dominates (AK's 38–41 % ruin in the
   zero-edge regime becomes the headline), **or** a gauge/threshold redesign that
   lets the overlay resume real exposure near the peak so it can compound — with
   literature grounding and the same anti-overfit discipline (single primary,
   frozen grid, both DGPs must agree, negatives reported).

## References

- Full report: [`REPORT.md`](REPORT.md)
- Results artefact: [`results.json`](results.json)
- Harness: [`../../programs/E019/`](../../programs/E019/)
- Predecessor: [`../E017_confidence_gated_cooldown/`](../E017_confidence_gated_cooldown/)
- Registry: [`../../EXPERIMENTS.md`](../../EXPERIMENTS.md)
