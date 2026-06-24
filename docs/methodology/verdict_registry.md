# Methodology: four-tier verdict registry

**Status:** binding · **Effective:** 2026-06-16 (`PROTOCOL_DISCIPLINE.md`)

## Registry

Every evaluated cell receives exactly one verdict. Verdicts are
**append-only** per cell — re-runs add rows, they do not overwrite.

| Verdict | Meaning | May advance? |
|---|---|---|
| `alive` | Positive effect, survived stage FDR | yes |
| `parked_weak_effect` | Positive raw signal, failed FDR or thin confirm | no — watch list |
| `parked_insufficient_n` | Below n gate; stats still recorded | no — power issue |
| `dead` | Adequately powered, no effect | no |

## Compute-vs-claim

Every cell in the stage's family is scored and recorded — including cells
we lose interest in. The n_gate governs **eligibility to be called
alive**, not whether statistics are computed.

## Multiplicity

BH-FDR α = 0.05 across the stage's declared family unless the protocol
specifies a per-cell confirm α for Stage 2+.

## Stop rules

Pre-declared stop conditions (e.g. "if 0 alive at Stage 1, STOP") are
valid outcomes. Document upstream stops in `stage*_stop.json` artefacts
(E007 template).

## M001 hybrid mapping

Internally M001 uses this four-tier registry as canonical KPI vocabulary
(`07-research-standards.md` §10.4). The Blue Lock dashboard labels
(`starter` / `sub` / `benched` / `cut`) are **view-layer only** —
see `08-dashboard-spec.md` §3.

## References

- [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md) §4
- E006 / E007 protocol examples
