# E012 — Stop Notice: dependency gate not cleared

**Date:** 2026-07-01 · **Status:** `cancelled_dependency_failed` · **Protocol:** [`PROTOCOL.md`](PROTOCOL.md)

## Gate condition (as pre-registered)

> **Gate:** conditional on E011 Stage-1 verdict `alive_positive` on at least one stop bucket ≤ 20 pips.
> — `PROTOCOL.md`, header block.

## What actually happened upstream

E011 ([`../E011_small_stop_subset_expectancy/REPORT.md`](../E011_small_stop_subset_expectancy/REPORT.md)) evaluated five stop-distance buckets, including both buckets ≤ 20 pips (`0-10p` and `10-20p`). Neither reached `alive_positive`:

| Bucket | n | Median pips | 95% CI | Verdict |
|---|---:|---:|---|---|
| 0-10 pips | 19 | +11.42 | [+0.00, +0.00] | `parked_insufficient_n` |
| 10-20 pips | 141 | +15.18 | [-12.14, +18.05] | `dead` |

E011's overall Stage-1 verdict was `stopped_at_stage_1`: the alpha's expectancy is bucket-agnostic, with no bucket's confidence interval sitting strictly above the pooled cross-bucket median. The `10-20p` bucket, despite having sufficient trades (n = 141, above the 30-trade n-gate), landed `dead` — its CI straddles zero and does not clear the bar. The `0-10p` bucket has a positive median but is `parked_insufficient_n` (n = 19, below the 30-trade gate) — it cannot be called `alive_positive` regardless of its point estimate, per the compute-vs-claim rule in `docs/methodology/verdict_registry.md`.

## Decision

**E012 does not run.** This is not a judgement call — the gate condition was written into `PROTOCOL.md` before E011 executed, and E011's outcome mechanically fails it. No simulation, no code (`programs/E012/alpha_pending_limit.py` was never created), and no data slice beyond what E011 already consumed was touched.

## Why this matters

E012's entire premise — that entering via a pending limit inside the zone would let the strategy capture a distinct, higher-expectancy small-stop subset — depends on that subset existing in the first place. E011 falsified the premise. Building and running the pending-limit entry fork would have been effort spent testing a mechanism to preserve an edge that the data shows is not there to preserve.

## Re-opening conditions

E012 can be re-registered (as an amendment or a fresh protocol) if a future, differently-designed study establishes that some identifiable subset of `zone_d1_against` signals has small-stop-distance edge that a tighter effective stop would meaningfully capture. Simply re-running E011 on more data without a design change is unlikely to change the underlying finding, since the bucket-agnostic result held at reasonable sample sizes (n = 113-162) across the three well-powered middle buckets.

## References

- Gate condition: [`PROTOCOL.md`](PROTOCOL.md) header + Section 5 (stop rules).
- Upstream result: [`../E011_small_stop_subset_expectancy/REPORT.md`](../E011_small_stop_subset_expectancy/REPORT.md).
- Registry entry: [`../../EXPERIMENTS.md`](../../EXPERIMENTS.md).
