# E012 - Pending-limit-inside-zone entry variant for `zone_d1_against` H4 (pre-registered)

**Status:** PRE-REGISTERED 2026-07-01 · **Date frozen:** 2026-07-01 ·
**Gate:** conditional on E011 Stage-1 verdict `alive_positive` on at least
one stop bucket ≤ 20 pips.

E012 asks a strategy-modification question: **does entering
`zone_d1_against` via a pending buy/sell limit placed INSIDE the zone
(one ATR/4 beyond the zone edge into the zone body) preserve the alpha's
edge while producing a 7-15 pip effective stop distance?**

Motivation: the deployed cell enters at zone-edge touch, which under
production sizing produces 20-65 pip stops and forces the position sizer
to reject the trade at $100 balance. A pending limit deeper into the zone
would reduce stop distance if filled, but only if:

1. The fill-rate is not decimated (a limit inside a zone can be missed
   if price wicks in without a full retest).
2. The trades that DO get filled retain the alpha's OOS median edge
   (touched-zone trades might carry more edge than limit-filled trades).

This is a genuine strategy change. E012 does NOT ship to production
without a positive verdict here PLUS a Wave-6 validation on the
production repo's own pipeline.

Follow [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md). Registered
in [`EXPERIMENTS.md`](../../EXPERIMENTS.md). Data accounting in
[`DATA_LEDGER.md`](../../DATA_LEDGER.md).

---

## §0 Reuse declaration (no re-derived code except entry mechanic)

E012 reuses the following artefacts exactly as committed. The only
NEW code is the `entry_mode = pending_limit_inside` fork inside a
research-side alpha subclass. Production `SupplyDemandAlpha` is not
modified.

| Purpose | Module / artefact |
|---|---|
| Base alpha | `multi-pair-trading-agent/agent/alphas/concepts/zone_alpha.py::SupplyDemandAlpha` (frozen at pre-reg commit) |
| Backtest fill model | `multi-pair-trading-agent/agent/alphas/backtest.py::run_alpha` (frozen) |
| Bar loader | `multi-pair-trading-agent/agent/data/loader.py::BarLoader` |
| Walk-forward driver | `finance-research-experiments/scripts/run_walk_forward_ab.py` (extended with `entry_mode` kwarg for E012) |
| Bootstrap CI | `multi-pair-trading-agent/agent/backtest/metrics.py::bootstrap_p_value` |
| Baseline trade log | `docs/reviews/walk_forward_raw.json` (E004 baseline) |

**Research-side entry fork.** A subclass
`SupplyDemandAlpha_PendingLimit` in
`finance-research-experiments/programs/E012/alpha_pending_limit.py`
overrides ONLY the entry price computation: `entry` becomes
`zone.top - depth_fraction * (zone.top - zone.bottom)` for supply
zones (mirror for demand). Stop stays at the original zone level +
buffer. TP stays at fixed 1.5R. All HTF filters, all other detector
parameters, all session filtering are inherited unchanged.

**Fill accounting.** A limit entry only counts as filled if, in the
2 bars following signal-detection (H4: 8 hours), price wicks to at
least `entry_price` OR closes past it. Unfilled limits are recorded as
`unfilled_expired` and excluded from the outcome sample. The fill-rate
itself is a locked stat.

---

## §1 Hypothesis (operational)

**H0.** Under `entry_mode = pending_limit_inside`, the OOS median
pips/trade on filled trades is **not** materially different from the
baseline touch-entry OOS median (E004: +11.34 pips/trade on the
deployed cell) after adjusting for the reduced stop distance
(pips-per-R basis).

**H1.** The pending-limit entry variant produces an OOS median
pips/trade whose bootstrap 95 % CI is **strictly above** the baseline
OOS median on the 7-window walk-forward test folds, at a fill-rate
≥ 60 % of the baseline touch-entry signal count.

**Fill-rate H2.** Fill-rate < 40 % → variant is
`parked_low_fill` regardless of expectancy (too few trades to matter
in production).

**Outcome metric.** OOS median pips/trade over the 7 E004 test folds,
filled trades only. Bootstrap 95 % CI, 5,000 resamples, seed 42.

---

## §2 Separation

- **Does this touch the trading agent?** No. All entry-fork code lives
  in this repo under `programs/E012/`. Production `SupplyDemandAlpha`
  is read-only.
- **Prior uses of the same data slice.** EURUSD H4 2015-2025 has been
  screened by E001-E005 and re-analysed by E011. E012 is a **new
  simulation** (different entry price → different exit-price sample
  path) so it consumes the confirm window as a full statistical draw.
  DATA_LEDGER row added at Stage 1.

---

## §3 Locked parameters

| Knob | Value | Rationale |
|---|---|---|
| Alpha family | `SupplyDemandAlpha_PendingLimit` (subclass) | Only override = entry price |
| HTF filter | `htf_align="D1", htf_align_mode="against", htf_lookback=10, htf_min_move_pips=60.0` | E004 locked |
| Timeframe | H4 | Deployed |
| Session | `all` | Deployed |
| `depth_fraction` (limit depth into zone) | **0.5** | Zone midpoint; the E006 exploratory finding shows mid-zone fills carry the strongest displacement-null signal on `bullish_fvg_touch`; frozen here without grid search to avoid selection bias |
| Fill window | 2 H4 bars after signal-detection | H4 supply/demand zones typically retest within one bar; 2 bars is a permissive fill window |
| Stop placement | Original zone edge + `sl_buffer_pips` (unchanged from `SupplyDemandAlpha`) | Preserves the alpha's OOS invalidation criterion |
| TP placement | 1.5R from **fill** price (not zone edge) | Matches E004 deployed cell reward:risk |
| Backtest cost | Same as `run_alpha` per-TF `cost_for("H4")` | No cost changes for the variant |
| Bootstrap resamples | 5,000 | E004 / E011 convention |
| Random seed | 42 | Convention |
| n-gate | 40 filled trades OOS per stage | Below this, verdict is `parked_insufficient_n` |

**Verdict (locked):**

- `alive_positive` iff n ≥ 40 AND bootstrap-95 % CI lower bound >
  baseline OOS median AND fill-rate ≥ 0.60.
- `alive_equivalent_smaller_stop` iff n ≥ 40 AND bootstrap-95 % CI
  contains the baseline median AND fill-rate ≥ 0.60 AND per-R
  expectancy > 1.05 × baseline per-R expectancy (equivalent P&L on a
  tighter stop → improves sizing viability without harming edge).
- `parked_low_fill` iff fill-rate < 0.60.
- `parked_insufficient_n` iff n < 40.
- `dead` iff n ≥ 40 AND CI upper bound < baseline median.

---

## §4 Statistical pipeline

| Stage | Pair | Period | Family | Test | FDR |
|---|---|---|---|---|---|
| 1 - Screen (EURUSD IS) | EURUSD | 2015-2018 IS folds pooled | 1 cell | Bootstrap-95 % CI vs baseline | per-cell α = 0.05 |
| 2 - Walk-forward OOS | EURUSD | 7 × 1-yr OOS folds 2019-2025 | 1 cell | Bootstrap-95 % CI on pooled OOS trades | per-cell α = 0.05 |
| 3 - Cross-pair replicate | GBPUSD, USDCAD | 2015-2024 (E005 sealed) | Stage-2 survivors | Bootstrap-95 % CI, frozen params | per-cell α = 0.05 |

**Stage 1 IS-only sanity check** validates that the variant is not
catastrophically worse in-sample (a fast fail). It is NOT used to
select `depth_fraction` or any other knob - all knobs are frozen at
this pre-reg commit.

---

## §5 Stop rules

- **Stage 1.** If fill-rate < 0.40 OR IS bootstrap median < 0 pips →
  **STOP at Stage 1.** Report the variant as `dead`. E016 (re-entry
  rule) is unaffected; it does not depend on E012.
- **Stage 2.** If OOS variance verdict is `dead` or `parked_low_fill` →
  **STOP at Stage 2.** Do not consume the cross-pair slice.
- **Stage 3.** If any Stage-2 survivor fails cross-pair → downgrade to
  `parked_weak_effect` (EURUSD-only).

Stopping at any stage is a valid outcome. E012 not shipping to
production is an acceptable answer; the whole point of the study is to
find out whether the intuition holds.

---

## §6 Amendments

_(No amendments yet - appended after pre-registration commits only.)_

---

## §7 Cross-references

- **E004 walk-forward** ([`../E004_walk_forward/PROTOCOL.md`](../E004_walk_forward/PROTOCOL.md))
  - baseline touch-entry expectancy.
- **E005 cross-pair sealed** ([`../E005_cross_pair_sealed/`](../E005_cross_pair_sealed/))
  - Stage-3 replicate.
- **E011 small-stop subset** ([`../E011_small_stop_subset_expectancy/PROTOCOL.md`](../E011_small_stop_subset_expectancy/PROTOCOL.md))
  - upstream dependency; E012 only runs if E011 Stage-1 has an
  `alive_positive` bucket ≤ 20 pips.
- **E006 exploratory** ([`../E006_test_a_price_action/REPORT.md`](../E006_test_a_price_action/REPORT.md))
  - source of the mid-zone displacement-null finding that motivates
  the frozen `depth_fraction = 0.5` choice.

---

## §8 Data-ledger declaration

| Stage | Pair | TF | Slice | Status this experiment | Prior uses |
|---|---|---|---|---|---|
| 1 | EURUSD | H4 | 2015-2018 | new sim (entry-mode fork) | E001, E002, E003, E004 |
| 2 | EURUSD | H4 | 2019-2025 | new sim | E004 (baseline sim) |
| 3 | GBPUSD | H4 | 2015-2024 | new sim on E005 sealed slice | E001, E004, E005 |
| 3 | USDCAD | H4 | 2015-2024 | new sim on E005 sealed slice | E001, E004, E005 |

Stage 3 consumes cross-pair slices that are already E005-sealed for
the deployed cell verdict. E012's re-fill on those bars is a new
sample path (different entry prices), and is disclosed here as the
second consumption of those slices for a `zone_d1_against` variant.

---

**Pre-registration commit:** _(hash after push)_
