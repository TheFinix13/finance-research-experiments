# E015 — Stop Notice: dependency gate not cleared

**Date:** 2026-07-01 · **Status:** `cancelled_dependency_failed` · **Protocol:** [`PROTOCOL.md`](PROTOCOL.md)

## Gate condition (as pre-registered)

> **Gate:** conditional on E014 verdict `alive_positive` OR `alive_equivalent_higher_hit_rate`.
> — `PROTOCOL.md`, header block.

## What actually happened upstream

E014 ([`../E014_quality_score_entry_gate/REPORT.md`](../E014_quality_score_entry_gate/REPORT.md)) tested three quality-score entry thresholds ($\theta \in \{30, 50, 70\}$) on the same `zone_d1_against` H4 alpha that E015 would have sized. The locked-per-window threshold procedure landed on $\theta = 70$ in six of seven windows, producing a pooled out-of-sample result of:

| Statistic | Value |
|---|---:|
| Pooled OOS trades | 102 |
| Trade-count ratio vs baseline | 11.9% |
| Median pips/trade | +26.09 |
| Bootstrap 95% CI | [+16.17, +33.99] |
| Baseline (E004) | +11.34 |

The confidence interval sits strictly above the frozen baseline — a real effect by E014's own locked statistic — but the study's verdict is `parked_low_yield`, not `alive_positive` or `alive_equivalent_higher_hit_rate`, because the pooled trade count (102, 11.9% of the 855-trade baseline) falls below the pre-declared 25% trade-count floor. Neither of the two conditions E015's gate accepts was met.

## Decision

**E015 does not run.** The gate was written into `PROTOCOL.md` before E014 executed, and E014's actual verdict — `parked_low_yield` — is neither of the two values the gate accepts. No sizing-aware driver (`programs/E015/run_sizing_walk_forward.py`) was created, and the frozen conviction-mapping function specified in Section 0 of the protocol (`conviction_from_quality(quality_score)`) was never wired into any simulation.

## Why this matters

E015's premise is that `quality_score` correlates with expectancy strongly enough to size positions on it. E014's result is consistent with that premise being *directionally* true (higher quality, higher median pips) but not yet validated at a trade volume that would make a sizing rule trustworthy — a sizing function trained on 102 trades, most of them concentrated in a handful of the seven windows (see E014 REPORT.md Table 3, where six windows contribute between 6 and 33 trades each), risks fitting to a small, non-representative sample rather than a real relationship. Running E015 on top of an unvalidated-at-volume gate would compound that risk by propagating a thin-sample effect directly into live position sizing math.

## Re-opening conditions

Two paths re-open E015, both already logged in `ai_context.md` Section 3 as backlog items:

1. **E014 wider-grid amendment.** Re-run E014 with a lower threshold grid ($\theta \in \{20, 30, 40, 50\}$) to search for a value that preserves more of the pip uplift while clearing the 25% trade-count floor. If that amendment lands `alive_positive` or `alive_equivalent_higher_hit_rate`, E015's gate opens automatically under its existing pre-registered form.
2. **E015 protocol amendment to a soft-weighting design.** E014 only tested a *hard gate* (trade or don't trade based on a threshold). E015's underlying question — should conviction scale with quality score — could instead be tested as continuous soft-weighting across *all* trades (no gate, `conviction = a + b * quality_score` fit on training folds), which does not inherit E014's volume problem because it does not discard any trades. This would require a new pre-registered amendment to E015's Section 1 hypothesis before running, since the current protocol locks the E014-gated alpha as its base rather than the ungated one.

## References

- Gate condition: [`PROTOCOL.md`](PROTOCOL.md) header + Section 5 (stop rules).
- Upstream result: [`../E014_quality_score_entry_gate/REPORT.md`](../E014_quality_score_entry_gate/REPORT.md).
- Registry entry: [`../../EXPERIMENTS.md`](../../EXPERIMENTS.md).
- Backlog: `ai_context.md` Section 3 ("E014 wider-grid amendment").
