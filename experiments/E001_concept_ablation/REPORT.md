# E001 — Report: concept ablation funnel

## Headline

> **Six of seven ICT-style concepts died under BH-FDR grid testing. Supply/demand
> zone touch was the sole survivor; fading against D1 trend (`zone_d1_against`)
> was the configuration that survived subsequent validation (E003–E005).**

## Elimination summary

| Concept | Outcome |
|---|---|
| FVG, BOS, order blocks, fib OTE | No BH-significant cells (first wave) |
| Momentum, liquidity sweep | No BH-significant cells (fair-shot second wave) |
| Supply/demand zone | Survivor → HTF against-D1 gate |

## Downstream

E002 ran the definitive zone-only grid (13 BH cells). E003–E004 corrected
deployment cell via holdout and walk-forward. E005 replicated on unseen pairs.

## Source material (agent repo)

- Narrative: `eurusd-ai-agent/docs/00-journey.md` §2–4
- Harness: `agent/alphas/grid.py`

## Verdict

**Complete.** Informed agent strategy lock; not re-run from lab unless a
new concept is proposed under fresh pre-registration on a pristine slice
(see `DATA_LEDGER.md`).
