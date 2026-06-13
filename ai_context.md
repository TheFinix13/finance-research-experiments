# AI Context — confluence experiment brain dump (updated 2026-06-13)

Read this first in a fresh chat in THIS workspace. Strictly technical.
This repo is fully separate from the trading agent (`eurusd-ai-agent`):
observation-only, no broker code, no imports INTO the agent, zero authority
over live trading. It borrows only the agent's parquet data cache at
runtime via PYTHONPATH (see PROTOCOL.md §Reproducibility / REPORT.md §7).

## 1) What is built and working

- **v1 (closed, code removed 2026-06-13):** pooled band-density pilot —
  H0 stood (EURUSD H4, p = 0.23, no source survived FDR). The numerical
  result is preserved in PROTOCOL.md/REPORT.md; the code itself was a
  dead end and was pruned.
- **Protocol v2 (PROTOCOL.md):** pre-registered role-structured study.
  Three test families: A price action, B indicators, C cross-family.
  Staged funnel: Stage 0 frozen event dictionary → Stage 1 marginal screen
  per (TF × event type) → Stage 2 conditional pairs → Stage 3 triplets.
  4-tier verdicts (alive / parked_weak_effect / parked_insufficient_n /
  dead), BH-FDR 5% per stage, n-gates (S1 ≥100, S2 ≥50). Splits: screen
  2015-21, confirm 2022-24, sealed 2025+, cross-pair GBPUSD frozen.
- **Test A COMPLETE (REPORT.md is the deliverable):**
  - Dictionary: 18 detectors, 76 event types, all causal, 42 tests green.
  - Pre-registered uniform controls were INVALID: session-volatility
    confound (random-time MFE 1.09→4.03 ATR by hour on M15; ATR(14) lags
    the session cycle). Amendment v2.1 = hour-of-day-matched controls;
    uniform run kept as cautionary record (41 false "alive").
  - Hour-matched screen: 5/284 alive, all M15 (channel_top_touch,
    fib_50_tag, fib_618_tag, fib_ext_1272_tag,
    trendline_liquidity_sweep_low).
  - Confirm 2022-24 (frozen, FDR within the 5): trendline_liquidity_
    sweep_low CONFIRMED (+0.303 → +0.308 ATR, p=0.0065).
  - GBPUSD (frozen): channel_top_touch REPLICATED (+0.099, p=0.0005).
    All 5 positive on both OOS tests (sign-consistency ≈3% under null).
  - Stage 2 strict: EMPTY family (no higher-TF survivor). Exploratory
    Stage 2 (65 pairs, parked-weak contexts): lift mostly = setup
    marginals; H1 equal_highs_pool context is the only consistent
    amplifier (selection +0.10…+0.46 ATR) → Stage-2b hypothesis.
  - Effects are gate/exit-input sized (≤0.35 ATR, hit-rate deltas <2pts),
    NOT tradeable standalone after spread.

## 2) Key file paths

| Area | Files |
|---|---|
| Protocol + report | `PROTOCOL.md` (v2 + amendment v2.1 + execution record), `REPORT.md` |
| Event framework | `conflab/events.py` (Event, all_detectors registry) |
| Detectors | `conflab/detectors_{structure,liquidity,levels,zones,trendlines,chartpatterns,fib,patterns,sessions}.py` |
| Stage 1 | `conflab/screening.py`, `scripts/run_stage1.py` |
| Stage 2 | `conflab/stage2.py`, `scripts/run_stage2.py` |
| Shared stats | `conflab/stats.py` (permutation p + BH-FDR) |
| Helpers | `conflab/indicators.py`, `conflab/patterns.py`, `conflab/data.py` |
| Diagnostics/figure | `scripts/diagnose_m15_controls.py`, `scripts/render_registry_figure.py` |
| Evidence | `output/*.jsonl` registries, `output/stage1_summary.png`, logs |

Tests: `tests/` (42). Run everything with the agent repo's venv:
`PYTHONPATH=../eurusd-ai-agent:. ../eurusd-ai-agent/.venv/bin/python ...`

## 3) Next immediate goal (roadmap, in value order)

1. **Stage-2b pre-registration:** H1 `equal_highs_pool` as context with a
   proper S-alone contrast (joint vs same-setup-outside-window), screen
   split only, FDR over the planned pair family. Write the protocol
   BEFORE running anything.
2. **Test B (indicators):** own pre-registration; reuse the Stage-1
   harness — hour-matched controls transfer directly.
3. **Test C (cross-family):** A-survivors+parked × B-survivors+parked;
   only after B.
4. **D1 power redesign:** cross-pair panel pooling for daily-TF cells
   (D1 is unpowerable per-pair at n≥100/7yr).
5. **Pre-registered re-looks:** parked cells re-test when screen n doubles
   or a new pair's data is added — each re-look counts in that round's FDR.

Honesty rules stay binding: no detector retuning post-freeze, every
evaluated hypothesis counts toward FDR, negative results reported with
equal prominence, nothing here ever trades.
