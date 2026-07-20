# E011 - Small-stop subset expectancy of `zone_d1_against` H4 (pre-registered)

**Status:** PRE-REGISTERED 2026-07-01 · **Date frozen:** 2026-07-01

E011 is a **descriptive re-analysis** of the trade log produced by the
already-locked deployed cell `zone_d1_against / H4 / all` in
[E004 walk-forward](../E004_walk_forward/PROTOCOL.md) and
[E005 cross-pair](../E005_cross_pair_sealed/). No new bars are consumed; no
production code is modified. The question is purely: **does the alpha's
expectancy depend on the stop-distance bucket at signal time?**

Motivation: the June 2026 live-agent replay showed a systematic pattern
where signals with ≤ 20-pip stops were rejected by the position sizer at
$100 balance (risk-at-min-lot > 2 %), while the same signals - if taken
- would have been profitable due to wick-proof SL preventing wick
sweeps. If the small-stop bucket has POSITIVE expectancy, it justifies
the E012 pending-limit entry variant (tighter effective stop, same
signal population).

Follow [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md). Registered
in [`EXPERIMENTS.md`](../../EXPERIMENTS.md). Data accounting in
[`DATA_LEDGER.md`](../../DATA_LEDGER.md).

---

## §0 Reuse declaration (no re-derived code, no new data)

E011 reuses the following artefacts **exactly as committed at the
pre-registration commit**. No detector parameter, no alpha parameter, no
statistical routine is re-derived.

| Purpose | Module / artefact |
|---|---|
| Trade log source | `multi-pair-trading-agent/docs/reviews/walk_forward_raw.json` (E004 output for `zone_d1_against/H4/all`) |
| Cross-pair replicate | `multi-pair-trading-agent/docs/reviews/2026-06-10_cross_pair_frozen.md` (E005 GBPUSD + USDCAD) |
| Alpha under test | `multi-pair-trading-agent/agent/alphas/concepts/zone_alpha.py::SupplyDemandAlpha(htf_align="D1", htf_align_mode="against", htf_lookback=10, htf_min_move_pips=60.0)` |
| Backtest fill model | `multi-pair-trading-agent/agent/alphas/backtest.py::run_alpha` |
| Bootstrap CI | `multi-pair-trading-agent/agent/backtest/metrics.py::bootstrap_p_value` |
| Bar loader | `multi-pair-trading-agent/agent/data/loader.py::BarLoader` |

**Stage-0 prerequisites:**

1. E004 walk-forward raw JSON exists on the production repo at
   `docs/reviews/walk_forward_raw.json` (verified 2026-06-24 audit).
2. Each trade record already carries entry price, stop price, and exit
   metadata. Stop distance in pips is derived (not re-simulated) as
   `abs(entry - stop) / 0.0001`.

---

## §1 Hypothesis (operational)

**Prior (from live-agent 2026-06 replay).** Over 22 signals fired by
`zone_d1_against/H4/all` on 2026-06-22 → 2026-06-30, 14 were rejected
by the position sizer for having `risk_at_min_lot > 2 %` on a $100
account (stop distance ≥ 20 pips). Of the 14 rejects, walking each
forward under wick-proof SL showed 8 would-be wins vs 6 losses (57 %
hit-rate). This is exploratory, not a claim.

**H0.** Conditional on a `zone_d1_against/H4/all` entry occurring, the
OOS median pips/trade is **not** materially different across stop
buckets `B ∈ {0-10p, 10-20p, 20-40p, 40-80p, 80p+}` (all buckets
share the alpha-level median +11.34 pips/trade up to bootstrap CI
overlap).

**H1.** At least one bucket has an OOS median pips/trade whose
bootstrap 95 % CI is **strictly above** the alpha-level median (better
than baseline) OR **strictly below zero** (loses money).

**Outcome metric.** OOS median pips/trade per bucket, over the 7
walk-forward test folds (2019-2025, one 1-year OOS window per E004
window). Bootstrap 95 % CI with 5,000 resamples, seed 42.

---

## §2 Separation

- **Does this touch the trading agent?** No. E011 is a read-only
  re-analysis of an existing JSON artefact. The alpha's parameters are
  not tuned; the deployed cell verdict is not amended.
- **Prior uses of the same data slice.** EURUSD H4 2015-2025 has been
  screened by E001, E002, E003, E004, E005 (per `DATA_LEDGER.md`).
  E011 does not compute new stage-level survivor stats and does not
  add to the family FDR; it only stratifies E004's *already-computed*
  OOS trades. Compute-vs-claim principle: statistics are computed on
  every bucket, but a bucket only becomes a claim if H1 is satisfied.

---

## §3 Locked parameters

| Knob | Value | Rationale |
|---|---|---|
| Alpha | `zone_d1_against` | The only production-deployed cell for H4/all |
| Timeframe | H4 | Deployed |
| Session | `all` | Deployed |
| Cell filter | `htf_align="D1", htf_align_mode="against", htf_lookback=10, htf_min_move_pips=60.0` | E004 locked |
| Stop-bucket boundaries | `[0, 10, 20, 40, 80, ∞)` pips | Pre-registered; symmetric log-ish spacing anchored at the live-agent 20-pip sizing threshold |
| Direction convention | Long: `stop_pips = (entry - stop) * 10,000`; Short: symmetric | Matches `SupplyDemandAlpha` output |
| Bootstrap resamples | 5,000 | E004/E006 convention |
| Random seed | 42 | E006/E007 convention |
| n-gate per bucket | 30 trades across the 7 OOS folds | Below this, verdict is `parked_insufficient_n` |
| Verdict effect floor | Bootstrap 95 % CI **strictly** above 0 pips (positive) OR strictly below 0 (loses money) | Prevents claiming buckets whose CI straddles the alpha median |

**Bucket-level verdict (locked):**

- `alive_positive` iff `n ≥ 30` AND bootstrap-95 % CI lower bound > 0
  AND bootstrap-95 % median > alpha-level median (implies bucket
  outperforms).
- `alive_loses_money` iff `n ≥ 30` AND bootstrap-95 % CI upper bound
  < 0 (bucket is a net loser; production should exclude signals with
  that stop-distance).
- `parked_insufficient_n` iff `n < 30`.
- `dead` iff `n ≥ 30` AND bootstrap-95 % CI contains 0 or contains
  the alpha-level median (indistinguishable from the pooled alpha).

**Compute-vs-claim.** Every bucket is scored regardless of `n`. The
`n_gate` governs eligibility to be called `alive_*`, not whether
statistics are computed.

---

## §4 Statistical pipeline

| Stage | Pair(s) | Period | Family | Test | FDR |
|---|---|---|---|---|---|
| 1 - EURUSD OOS | EURUSD | 7 × 1-yr OOS folds (2019-2025) | 5 buckets | Bootstrap-95 % CI per bucket | BH α = 0.05 across 5 buckets |
| 2 - Cross-pair replicate | GBPUSD, USDCAD | 2015-2024 (E005 sealed slices) | Stage-1 `alive_*` survivors | Bootstrap-95 % CI, frozen bucket boundaries | per-cell α = 0.05 |

**Locked stat for the top-line verdict** (registered in
`docs/methodology/gate_verdict_registry.md` on completion): per-bucket
OOS median pips/trade on the pooled 7-window EURUSD test folds, with
bootstrap 95 % CI.

**Cross-pair replicate note (Stage 2).** GBPUSD and USDCAD H4
2015-2024 are E005 sealed slices already consumed for the alpha-level
verdict; the E011 re-analysis is a **new statistic** on those same
trades, so it does not re-seal the slices - but the honest caveat is
that these bars were used in the alpha's locked-parameter selection
and any surprising bucket effect on cross-pair data must be treated as
suggestive, not confirmatory. A fully-sealed cross-pair replicate
would require a fresh 2025-2026 slice on GBPUSD / USDCAD, which is
released for E011 Stage 2 only after Stage 1 has a positive verdict
(`alive_positive` on any bucket).

---

## §5 Stop rules

- **Stage 1 stop.** If **0 of 5** buckets earn `alive_positive` OR
  `alive_loses_money` on EURUSD OOS → **STOP at Stage 1.** Verdict for
  E011: expectancy is uniform across stop buckets; the small-stop
  subset does not carry a distinct edge; E012 pending-limit-entry
  study is **not launched** (its premise is falsified).
- **Stage 2 stop.** If any Stage-1 `alive_positive` bucket fails to
  replicate on GBPUSD + USDCAD → downgrade that bucket to
  `parked_weak_effect` (EURUSD-only). Only buckets that replicate on
  at least one cross-pair are `alive_confirmed`.

Stopping at any stage is a valid outcome and is reported with the same
prominence as a positive verdict.

---

## §6 Amendments

_(No amendments yet - appended after pre-registration commits only.)_

---

## §7 Cross-references

- **E004 walk-forward** ([`../E004_walk_forward/PROTOCOL.md`](../E004_walk_forward/PROTOCOL.md))
  - the source of the OOS trade log we stratify.
- **E005 cross-pair sealed** ([`../E005_cross_pair_sealed/`](../E005_cross_pair_sealed/))
  - the cross-pair replicate source for Stage 2.
- **E012 pending-limit-inside-zone**
  ([`../E012_pending_limit_inside_zone/PROTOCOL.md`](../E012_pending_limit_inside_zone/PROTOCOL.md))
  - directly gated on E011 Stage-1 verdict.
- **Live-agent replay motivation.** Session log entry
  `brain-box/life/finance-research/multi-pair-trading-agent.md` 2026-06-30
  entry documents the 14/22 sizing rejections that motivated E011.

---

## §8 Data-ledger declaration

| Stage | Pair | TF | Slice | Status this experiment | Prior uses |
|---|---|---|---|---|---|
| 1 | EURUSD | H4 | 2015-2025 walk-forward trade log | re-analysis (no new bar consumption) | E001, E002, E003, E004 |
| 2 | GBPUSD | H4 | 2015-2024 | re-analysis of E005 sealed output | E001, E004, E005 |
| 2 | USDCAD | H4 | 2015-2024 | re-analysis of E005 sealed output | E001, E004, E005 |

E011 does not re-seal any slice. The pooled OOS median is a **new
statistic** on already-consumed bars, permitted under compute-vs-claim.

---

**Pre-registration commit:** _(hash after push)_
