# E001 — ICT concept ablation (retrospective protocol)

Status: **executed-then-registered 2026-06-16** (work ran in `eurusd-ai-agent`
2026-06-09 → 2026-06-10 before this repo existed).

Pre-registration: **not available at execution time.** This document records
what was actually done so the agent validation chain is auditable from the lab.

---

## Hypothesis

Each ICT-style alpha concept, tested **alone** on a grid of timeframes and
sessions, produces positive expectancy after bootstrap p-values and
Benjamini-Hochberg FDR correction at 5%.

## Method (as executed)

- **Harness:** `agent/alphas/grid.py` (`AblationCell`), one alpha per run.
- **Grid:** TF ∈ {D1, H4, H1, M15, M5} × session ∈ {all, london, ny,
  london_ny_overlap, asia}.
- **Statistics:** bootstrap p-value per cell; BH-FDR 5% across full grid.
- **Costs:** per-timeframe realistic spreads in backtest harness.
- **Window:** primarily 2015 → 2025 (full research window at reset).

## Concepts tested

| Concept | Verdict |
|---|---|
| FVG retest | eliminated — no BH-significant cell |
| BOS continuation | eliminated |
| Order blocks | eliminated |
| Fibonacci OTE | eliminated |
| Momentum | eliminated (fair-shot second wave) |
| Liquidity sweep | eliminated (fair-shot second wave) |
| **Supply/demand zone** | **sole survivor** |

## HTF discovery (post-ablation)

Zone edge behaves as **mean-reversion**. Gating **against** D1 trend
(`zone_d1_against`: htf_align=D1, mode=against, lookback=10,
min_move_pips=60) strengthened the edge; with-trend gating destroyed it.

## Agent code references

- `agent/alphas/concepts/zone_alpha.py`, `agent/alphas/concepts/_htf.py`
- `agent/alphas/grid.py`, `scripts/run_zone_all_tfs.py` (follow-on E002)

## Epistemic caveat

This funnel selected the zone concept on the same broad window later used
for holdout and walk-forward. Subsequent experiments (E003, E004) explicitly
address selection bias.
