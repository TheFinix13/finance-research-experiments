# E017 — Confidence-gated cooldown vs. binary kill-switch

**Date:** 2026-07-13 · **Protocol:** [`PROTOCOL.md`](PROTOCOL.md) · **Status:** `parked_capital_cost` (Phase 3 blocked).
**Verdict artefact:** [`results.json`](results.json) · **Stop notice:** [`STOP_NOTICE.md`](STOP_NOTICE.md).

## Abstract

The live agent halts on a 3% daily-drawdown breach by writing a per-symbol `kill.txt`
that blinds the loop until manual deletion — costing **50.9+ hours** of dead time on
the real 2026-07-08→07-12 incident. E017 pre-registered four graduated-confidence
configurations (per-symbol P-exp / P-lin × account gauge G-surplus / G-cdar) against a
hard kill-switch baseline (HK), a shadow-recovery arm (GC-S), and a time-decay control
(GC-T). A Monte-Carlo panel (N = 10,000 paths, 11,000-day horizon, bootstrap R from
the E013 production-matching ledger) shows GC-S eliminates blind dead time (median
**0 h** vs HK **6,500 h**) and cuts median max drawdown (**2.5%** vs **16.9%**), but
fails Pareto dominance because median terminal equity stays near $1,020 while HK paths
compound under the positive-R ledger. Gauge convergence passes; the Jul-08 incident
replay preserves the protective close and removes the blind window descriptively. **Phase
3 production wiring does not proceed**; the binary kill-switch remains.

## 1. Introduction

### 1.1 Motivation

Operational forensics on 2026-07-08→07-12 showed ~50% H4-evaluation downtime driven by
`kill.txt` persistence, including a shared-account EURUSD loss that tripped GBPUSD's
halt with zero local open positions. A binary halt is simple but expensive: the agent
stops watching, stops shadow-evaluating, and requires human file deletion to resume.

### 1.2 Problem statement

Can a continuous, loss-magnitude-scaled confidence score (never hard-zero) that keeps
the agent evaluating and shadow-trading **Pareto-dominate** the binary kill-switch on
capital preservation **and** time-to-resume?

### 1.3 Contributions

1. Pre-registered protocol with literature-grounded candidate formulas (Grossman–Zhou,
   risk-constrained Kelly, CDaR) — [`PROTOCOL.md`](PROTOCOL.md).
2. Reproducible MC harness at `programs/E017/` (`confidence_sim.py`,
   `run_e017_validation.py`).
3. Honest **negative** verdict on Pareto gate: dead-time win, capital-cost loss.

## 2. Background

Drawdown-constrained exposure rules scale risk smoothly rather than switching off
[@grossman1993drawdowns]. Risk-constrained Kelly gambling trades growth for drawdown
probability with a single risk-aversion parameter [@busseti2016kelly]. CDaR penalises
sustained underwater periods rather than single-tick spikes [@chekhlov2005drawdown].
Circuit-breaker literature warns that halts can destabilise near triggers
[@chen2024darkside; @subrahmanyam1994]. E013 already showed post-loss guard blocks
more future winners than losers — blunt halting is expensive [@internal_e013].

## 3. Methodology

Frozen per §3–§4 of [`PROTOCOL.md`](PROTOCOL.md). Three arms on identical trade
streams:

| Arm | Behaviour |
|---|---|
| HK | 3% daily-DD / circuit-breaker → close real positions → **48 h blind** (`kill.txt` model) |
| GC-S | Same triggers close real positions; suspend live orders while κ < 0.30; shadow-bank wins; taper resume |
| GC-T | GC-S without shadow banking; +0.06/day time decay on confidence |

Effective confidence κ = c_s · g with floors C_min = 0.15, g_min = 0.25.

**Data:** bootstrap R-multiples from `programs/E017/data/trade_ledger_EURUSD_H4.json`
(737 trades, hit-rate 0.5577, mean R 0.382). Synthetic grid (p_win ∈ {0.40, 0.55}) also
pre-registered; bootstrap is the primary generator for the reported headline numbers.

## 4. Implementation

`programs/E017/confidence_sim.py` — single-path simulator + MC aggregator.
`programs/E017/run_e017_validation.py` — CLI writing `results.json`.
`programs/E017/tests/test_confidence_sim.py` — 3 regression tests.
Trade ledger export: `programs/E017/export_trade_ledger.py` (E013 harness reuse).

## 5. Results

### 5.1 Monte Carlo (N = 10,000, seed 42)

**Table 1. Headline comparison (bootstrap ledger, p_win = 0.40).**

| Metric | HK | GC-S (P-exp+G-surplus λ=0.25) |
|---|---:|---:|
| Median dead hours | 6,500 | **0** |
| Median max drawdown | 16.9% | **2.5%** |
| Median terminal equity | compounding | **$1,021** |
| Risk of ruin | 0.0 | 0.0 |
| Median shadow opportunity R | 0 | 9,083 |

Dead-time reduction **≥ 50%**: **PASS** (100%).
Capital preservation (terminal equity ≥ 98% of HK): **FAIL**.
Pareto dominance: **FAIL** → verdict `parked_capital_cost`.

All four frozen candidate configs show the same pattern: near-zero dead hours, ~2–3%
median max DD, flat terminal equity near $1,000.

### 5.2 Gauge convergence (§4a)

Max pairwise disagreement = **0.0** for every config (deterministic g from shared E, M).
**PASS.**

### 5.3 Incident replay 2026-07-08 (descriptive, n = 1)

| | HK (observed) | GC-S (replay model) |
|---|---:|---:|
| Dead time | 50.9 h | 0 h |
| Protective close on DD | yes | yes |
| Shadow R during suspension | n/a | ~12.4 R |

Illustrative only — not an FDR-family statistical claim.

### 5.4 H2 — shadow vs time-decay

GC-S and GC-T median dead hours are indistinguishable on the MC panel. Shadow recovery
machinery **does not** earn its keep on the pre-registered primary metrics.

## 6. Discussion

The graduated mechanism does what it was designed to do on **risk**: eliminate blind
dead time and crush drawdown relative to HK. It fails the pre-registered Pareto gate
because the MC compares against a compounding HK baseline under a positive-R ledger —
GC-S spends most of its life in shadow/reduced mode and does not compound.

This is not a deployment bug; it is a **metric trade-off** the protocol made explicit
up front. A redesign might:

- treat opportunity cost (shadow R banked during suspension) as part of the capital score;
- lower τ_live so live compounding resumes faster (requires new pre-reg);
- accept `parked_capital_cost` and keep the kill-switch for now (this study's decision).

**Limitation:** the MC uses a simplified day-driven trade arrival process and a single
shared ledger for all three symbols. Correlation grid (ρ ∈ {0, 0.5}) was pre-registered
but not exhaustively reported in this first pass — bootstrap headline drives the verdict.

## 7. Conclusion

E017 verdict: **`parked_capital_cost`**. Graduated confidence + shadow recovery
**materially reduces dead time and drawdown** but **does not** Pareto-dominate the
binary kill-switch on terminal equity under the frozen protocol. **Phase 3 is blocked.**
The production agent keeps `kill.txt` halts until a fresh study (E018+) passes the gate.
