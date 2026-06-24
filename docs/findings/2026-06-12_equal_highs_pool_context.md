# Finding (exploratory): H1 `equal_highs_pool` as context amplifier

**Date:** 2026-06-12 · **Experiment:** E006 Stage 2 exploratory ·
**Status:** exploratory — candidate for E010 pre-registered confirmation

## Headline

In E006's **exploratory** Stage 2 (65 H1-context × M15-setup pairs),
H1 **`equal_highs_pool`** as context improved **every** M15 setup placed
under it. Selection term (joint MFE minus setup marginal): **+0.10 to
+0.46 ATR** across setups. Liquidity resting above equal highs appears
to amplify M15 setups below it.

## What this is not

- Not a standalone strategy — effects are gate-sized (+0.05 to +0.35 ATR
  on survivors elsewhere in E006).
- Not a confirmed claim — strict pre-registered Stage 2 was empty by
  construction (all Stage-1 survivors are M15; no higher-TF context cell).
- Not deployed to production — parked for **E010** Stage-2b validation.

## M001 relevance

- **A6 Nagi** confluence layer — canonical chemical-reaction context
  primitive pending E010.
- **A1 Isagi v2** — `conflab/detectors_liquidity.py:equal_highs_pool`.
- Doctrine chemical-reaction detector (`06-blue-lock-doctrine.md` §3.3).

## Canonical sources

- E006 report §4.4: [`experiments/E006_test_a_price_action/REPORT.md`](../../experiments/E006_test_a_price_action/REPORT.md)
- Detector: `conflab/detectors_liquidity.py`
- Planned confirmation: [`experiments/E010_equal_highs_pool_stage2b/PROTOCOL.md`](../../experiments/E010_equal_highs_pool_stage2b/PROTOCOL.md)
