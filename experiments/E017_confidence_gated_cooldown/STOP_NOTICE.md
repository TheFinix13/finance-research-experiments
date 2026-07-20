# E017 — Stop Notice: graduated confidence fails Pareto gate (`parked_capital_cost`)

**Date:** 2026-07-13 · **Status:** `parked_capital_cost` · **Protocol:** [`PROTOCOL.md`](PROTOCOL.md)

## Gate condition (as pre-registered)

> **`alive` → Phase 3 implementation** iff GC-S **Pareto-dominates** HK — median dead-time
> reduction ≥ 50% **and** capital preservation no worse on all three sub-metrics
> (median terminal equity, worst-path max drawdown, risk-of-ruin), robust across both
> data-generating processes, **and** the no-IPC gauge-convergence check passes, **and**
> the 2026-07-08 incident replay preserves the protective close while removing the blind
> window.
> — `PROTOCOL.md` §6

## What the Phase 2 harness found (N = 10,000 paths, seed 42, horizon 11,000 days)

| Arm | Median dead hours | Median max DD | Median terminal equity (p_win grid) | Risk of ruin |
|---|---:|---:|---:|---:|
| **HK** (binary kill-switch) | **6,500** | 16.9% | compounding path (bootstrap ledger) | 0.0 |
| **GC-S** (best config: P-exp+G-surplus λ=0.25) | **0** | **2.5%** | ~$1,020 (flat) | 0.0 |

GC-S **does** slash dead time (100% reduction vs HK — far above the 50% bar) and
**dramatically** improves drawdown (median 2.5% vs 16.9%). It **fails** the capital-
preservation leg: median terminal equity stays near starting capital (~$1,020) while
HK paths compound under the bootstrapped positive-R ledger. No frozen §3 configuration
achieved Pareto dominance.

Supporting checks **passed**:

- **Gauge convergence** (§4a): max pairwise disagreement = 0.0 across all four
  candidate configs (deterministic shared-equity feed).
- **Incident replay** (descriptive): HK blind window = 50.9 h; GC-S = 0 h with
  protective close preserved; ~12.4 R shadow opportunity during suspension.

**H2 (shadow vs time-decay):** GC-S ≈ GC-T on dead-time — shadow machinery does not
earn its keep (`h2_shadow_adds_value: false`).

## Decision

**Phase 3 production wiring does not proceed.** The binary per-symbol `kill.txt`
halt in `multi-pair-trading-agent` stays as-is. No `ConfidenceGuard`, shadow tracker,
or kill-switch rewire lands in the live agent on this evidence.

Verdict label: **`parked_capital_cost`** — the graduated mechanism cuts dead time and
drawdown but fails the pre-registered Pareto gate because de-risked / shadow-heavy
operation forgoes the compounding upside HK captures when the ledger edge is positive.
Redesign (different recovery thresholds, explicit opportunity-cost accounting, or a
revised capital metric that penalises blind downtime without requiring matched terminal
wealth) would need a **fresh pre-registration** before another attempt.

## Re-opening conditions

1. A new protocol amends the success criterion **or** proposes a redesigned confidence
   recovery function that pre-registers why terminal-equity parity is the wrong metric
   for a risk-overlay study (with literature grounding).
2. Historical replay on the full Jul 8–12 log bundle (not just descriptive constants)
   shows GC-S would have resumed live trading with net-positive account outcome — the
   MC panel alone is insufficient if live incident economics differ.
3. Any re-run uses a **new** study id (E018+) — no post-freeze retuning of §3/§4
   constants in this protocol.

## References

- Full report: [`REPORT.md`](REPORT.md)
- Results artefact: [`results.json`](results.json)
- Harness: [`../../programs/E017/`](../../programs/E017/)
- Registry: [`../../EXPERIMENTS.md`](../../EXPERIMENTS.md)
