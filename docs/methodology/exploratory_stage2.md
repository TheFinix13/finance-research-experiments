# Methodology: exploratory Stage 2

**Status:** guidance · **Worked example:** E006 §4.4

## Definition

An **exploratory Stage 2** runs when the strict pre-registered Stage 2
family is **empty by construction** (e.g. all Stage-1 survivors share
the same TF, so no higher-TF context cell exists).

Exploratory runs:

- Include parked-weak and non-survivor cells **explicitly labelled**.
- Use the same statistical machinery (displacement null, hour-restricted
  re-draws) where applicable.
- **Do not** produce deployment claims — they generate **hypotheses** for
  new pre-registered experiments.

## How to cite exploratory findings

| Allowed | Forbidden |
|---|---|
| "Candidate for E0XX pre-registration" | "Validated confluence layer" |
| Point to selection-term decomposition | Pool exploratory p-values with Stage-1 family |
| Link to findings doc | Auto-wire into live agent params |

## E006 worked case: `equal_highs_pool`

Strict Stage 2: empty (all survivors M15).

Exploratory Stage 2: 65 H1×M15 pairs. Most lift was setup-marginal, not
context interaction — **except** H1 `equal_highs_pool`, which showed
consistent positive selection terms (+0.10 to +0.46 ATR).

**Outcome:** finding promoted to
[`docs/findings/2026-06-12_equal_highs_pool_context.md`](../findings/2026-06-12_equal_highs_pool_context.md);
confirmation assigned to **E010**.

## Code template

`conflab/stage2.py` — context × setup pair-screening with displacement
null. Reused by M001 chemical-reaction validation.

## References

- E006 REPORT §4.3–§4.4
- [`audits/2026-06-24_E001-E007_audit.md`](../../audits/2026-06-24_E001-E007_audit.md) §2.6
