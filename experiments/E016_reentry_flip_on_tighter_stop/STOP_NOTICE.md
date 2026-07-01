# E016 — Stop Notice: dependency gate not cleared

**Date:** 2026-07-01 · **Status:** `cancelled_dependency_failed` · **Protocol:** [`PROTOCOL.md`](PROTOCOL.md)

## Gate condition (as pre-registered)

> **Gate:** conditional on BOTH E011 Stage-1 verdict `alive_positive` AND E014 Stage-1 verdict `alive_positive` OR `alive_equivalent_higher_hit_rate` (i.e., we trust both that small-stop trades have edge AND that quality_score ranks that edge honestly).
> — `PROTOCOL.md`, header block.

## What actually happened upstream

Both halves of the conjunctive gate failed independently:

| Upstream study | Required | Actual verdict | Cleared? |
|---|---|---|---|
| E011 (small-stop expectancy) | `alive_positive` | `stopped_at_stage_1` — bucket-agnostic edge, no bucket cleared `alive_positive` | No |
| E014 (quality-score gate) | `alive_positive` or `alive_equivalent_higher_hit_rate` | `parked_low_yield` — real effect, below the 25% trade-count floor | No |

See [`../E011_small_stop_subset_expectancy/REPORT.md`](../E011_small_stop_subset_expectancy/REPORT.md) and [`../E014_quality_score_entry_gate/REPORT.md`](../E014_quality_score_entry_gate/REPORT.md) for the full per-bucket and per-threshold results.

## Decision

**E016 does not run — Stage 0 gate, per its own Section 5.** The protocol explicitly instructs: "If E011 verdict is not `alive_positive` OR E014 verdict is not `alive_positive` / `alive_equivalent_higher_hit_rate` -> DO NOT RUN E016. Publish the dependency chain as the honest reason; the study does not fire." Neither the multi-position walk-forward driver (`programs/E016/run_reentry_walk_forward.py`) nor any of the three sub-arm decision rules (hold / close-and-flip / add-on-same-side) were implemented or run.

## Why this matters

E016's premise requires two independent discriminators to both be trustworthy at once: that a tighter stop identifies a genuinely better signal (E011's question) and that a higher quality score identifies a genuinely better zone (E014's question). E016's own three sub-arms use E014's *locked-threshold gated alpha* as their signal source (see `PROTOCOL.md` Section 0, "Alpha family: `SupplyDemandAlpha_QualityGated` @ E014 locked θ") and its trigger condition is explicitly a *tighter-stop* signal (Section 0, "trigger-condition primitives"). With E011 showing stop distance carries no distinguishing information and E014 showing quality-score gating is directionally real but not yet production-validated, a re-entry or flip rule built on either discriminator would be re-entering positions on a signal the current evidence cannot distinguish from noise. Running the study anyway would not produce a wrong answer, but it would produce an answer that cannot yet be trusted, since the very inputs the sub-arms condition on have not cleared their own bars.

## Note on cross-pollination to M001

E016's protocol (Section 7) flags that its cell-level question — should a single-position-per-symbol constraint yield to a better signal arriving during drawdown — is the cell-level analogue of the M001 multi-agent-ensemble programme's Φ4.1/Φ5 finding that "the single-position-per-symbol queue with conviction-only ranking is the binding constraint" (`ai_context.md`, M001 section). That architectural insight stands independently of E016's cancellation: M001's Φ5 aggregator work (HRP + TQS-floor + same-direction merge + multi-position) continues on its own track and is not gated by E016.

## Re-opening conditions

E016 re-opens only if **both** upstream studies independently clear their bars in the future:

1. A future amendment or re-run of E011 (with a different design, since simply re-running on more data is unlikely to change a bucket-agnostic finding held at reasonable sample sizes) establishes a genuine small-stop edge.
2. The E014 wider-grid amendment (Section "Re-opening conditions" in [`../E015_conviction_from_quality/STOP_NOTICE.md`](../E015_conviction_from_quality/STOP_NOTICE.md)) lands `alive_positive` or `alive_equivalent_higher_hit_rate`.

Until both conditions are met, E016 stays cancelled and the live agent's one-position-per-symbol rule in `agent/live/signal_loop.py::_maybe_enter` remains unchanged.

## References

- Gate condition: [`PROTOCOL.md`](PROTOCOL.md) header + Section 5 (Stage 0 stop rule).
- Upstream results: [`../E011_small_stop_subset_expectancy/REPORT.md`](../E011_small_stop_subset_expectancy/REPORT.md), [`../E014_quality_score_entry_gate/REPORT.md`](../E014_quality_score_entry_gate/REPORT.md).
- Registry entry: [`../../EXPERIMENTS.md`](../../EXPERIMENTS.md).
