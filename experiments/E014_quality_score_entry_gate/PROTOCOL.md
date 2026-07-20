# E014 - Zone quality-score entry gate for `zone_d1_against` H4 (pre-registered)

**Status:** PRE-REGISTERED 2026-07-01 · **Date frozen:** 2026-07-01

The production zone detector already computes a 0-100 quality score
(`agent.detectors.zones.compute_zone_quality`) at signal time, weighing
origin type, base tightness, departure aggressiveness, FVG-left-behind,
and formation session. This score is currently **computed but never
consulted** by `SupplyDemandAlpha`: the alpha uses the legacy raw
`Zone` from `detect_zones`, not the `QualifiedZone` chain.

E014 asks: **does gating `zone_d1_against` entries on
`quality_score ≥ θ` improve OOS Sharpe over the ungated baseline?**

Motivation: the current deployed cell's OOS median is +11.34
pips/trade with ~66 trades/year. If the low-quality tail (zones with
score < θ) is a net loser or a break-even drag, gating on quality
would raise per-trade expectancy without harming the alpha's regime
edge - but only if the tail is separately identifiable OOS. That is
the empirical question E014 answers.

Follow [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md). Registered
in [`EXPERIMENTS.md`](../../EXPERIMENTS.md). Data accounting in
[`DATA_LEDGER.md`](../../DATA_LEDGER.md).

---

## §0 Reuse declaration (no re-derived detector)

E014 uses `detect_qualified_zones` exactly as committed. The ONLY
new code is a research-side alpha subclass that consults
`qz.quality.quality_score` before emitting a signal; the zone
boundaries, order-block logic, quality-score formula, and session
tagging are frozen.

| Purpose | Module / artefact |
|---|---|
| Zone detector | `multi-pair-trading-agent/agent/detectors/zones.py::detect_qualified_zones` (frozen) |
| Quality score | `multi-pair-trading-agent/agent/detectors/zones.py::compute_zone_quality` (frozen; 0-100 scale) |
| Base alpha | `multi-pair-trading-agent/agent/alphas/concepts/zone_alpha.py::SupplyDemandAlpha` (read-only; subclass overrides zone source) |
| Alpha fork | `finance-research-experiments/programs/E014/alpha_quality_gated.py::SupplyDemandAlpha_QualityGated` (new) |
| Walk-forward driver | `finance-research-experiments/scripts/run_walk_forward_ab.py` (reused with `alpha_name = "zone_d1_against_quality"`) |
| Bootstrap CI | `multi-pair-trading-agent/agent/backtest/metrics.py::bootstrap_p_value` |

**Alpha fork semantics.** The subclass replaces
`ctx.zones` (legacy raw zones) with `[qz.zone for qz in
detect_qualified_zones(...) if qz.quality.quality_score >= θ]` at
signal time. All other detector parameters, HTF filters, exit rules,
and session filters are inherited unchanged from the production alpha.

---

## §1 Hypothesis (operational)

**Threshold grid (frozen).** `θ ∈ {30, 50, 70}` on the 0-100 scale.
Rationale: 30 gates only the deepest tail (origin type absent AND
weak departure AND non-killzone); 50 is the midpoint that keeps roughly
half of raw signals; 70 keeps only zones with strong origin + tight
base + killzone timing. The grid is pre-registered here; no threshold
tuning is permitted post-hoc.

**Threshold-locking protocol.** On the 4-year IS portion of each
walk-forward window, the θ with the highest IS Sharpe is selected
per-window. That θ is then LOCKED for that window's OOS evaluation.
Across the 7 windows we produce a locked-θ sequence; the overall E014
verdict is on the pooled OOS trades using each window's own locked θ.

**H0.** OOS pooled median pips/trade of the quality-gated variant is
**not** materially higher than the baseline `zone_d1_against/H4/all`
median (E004: +11.34 pips/trade), after adjusting for the reduced
trade count via bootstrap CI.

**H1.** Bootstrap-95 % CI of the quality-gated OOS median is
**strictly above** the baseline OOS median, at a trade-count ≥ 40 %
of baseline (variant keeps at least 4 of every 10 baseline signals).

**Trade-count H2.** Variant keeps < 25 % of baseline signals →
`parked_low_yield` regardless of expectancy (too few live trades to
matter in production).

**Outcome metric.** OOS pooled median pips/trade under each window's
locked θ, 7 walk-forward windows, bootstrap 95 % CI, 5,000 resamples,
seed 42.

---

## §2 Separation

- **Does this touch the trading agent?** No. The alpha fork lives in
  this repo under `programs/E014/`. Production `SupplyDemandAlpha`
  and `zone_routing.py` are read-only.
- **Prior uses of the same data slice.** EURUSD H4 2015-2025 has been
  screened by E001-E005, re-analysed by E011, and re-simulated by E013.
  E014 is another new statistical draw (different signal set → different
  outcome sample). DATA_LEDGER row added at Stage 1.

---

## §3 Locked parameters

| Knob | Value | Rationale |
|---|---|---|
| Alpha family | `SupplyDemandAlpha_QualityGated` (subclass) | Only override = zone source |
| HTF filter | `htf_align="D1", htf_align_mode="against", htf_lookback=10, htf_min_move_pips=60.0` | E004 locked |
| Timeframe | H4 | Deployed |
| Session | `all` | Deployed |
| Quality-score threshold grid | `{30, 50, 70}` | Frozen at pre-reg commit; no post-hoc grid extension |
| `min_impulse_pips` | 30.0 (detector default) | Frozen |
| `base_lookback` | 5 (detector default) | Frozen |
| `max_base_candles` | 5 (detector default) | Frozen |
| `median_window` | 200 (detector default) | Frozen |
| Backtest harness | `run_alpha` via `run_walk_forward_ab.py` all-off arm | Baseline exit path; no safety layers |
| Bootstrap resamples | 5,000 | Convention |
| Random seed | 42 | Convention |
| n-gate | 30 trades OOS per window | Below this, per-window is dropped from pool |
| Verdict effect floor | Bootstrap-95 % CI lower bound strictly above baseline OOS median | Standard |

**Verdict (locked):**

- `alive_positive` iff pooled OOS bootstrap-95 % CI lower bound >
  baseline OOS median AND trade count ≥ 40 % of baseline.
- `alive_equivalent_higher_hit_rate` iff CI contains baseline median
  AND OOS hit-rate is > 1.10 × baseline hit-rate AND trade count ≥
  40 % (variant produces the same P&L via a cleaner curve → still a
  win for psychological / drawdown reasons).
- `parked_low_yield` iff trade count < 25 % of baseline.
- `parked_weak_effect` iff n ≥ 30 AND CI contains baseline median
  AND no hit-rate improvement.
- `dead` iff CI upper bound < baseline median.

---

## §4 Statistical pipeline

| Stage | Pair | Period | Family | Test | FDR |
|---|---|---|---|---|---|
| 0 - Threshold-lock (per-window) | EURUSD | 7 × 4-yr IS folds | 3 θ values | IS Sharpe (highest wins per window) | No multiplicity claim; IS Sharpe is the selection statistic, not a verdict |
| 1 - OOS pooled | EURUSD | 7 × 1-yr OOS folds under per-window locked θ | 1 variant | Bootstrap-95 % CI on pooled OOS trades | per-cell α = 0.05 |
| 2 - Cross-pair replicate | GBPUSD, USDCAD | 2015-2024 (E005 sealed) | Stage-1 survivors | Bootstrap-95 % CI, frozen θ = mode(locked-θ sequence) | per-cell α = 0.05 |

**Threshold-lock stage semantics.** The threshold grid ({30, 50, 70})
is small enough that the winner is a discrete choice; there is no
p-value on the IS selection. Reporting includes the full IS-Sharpe
table per (window, θ) so a reader can see whether the winner is
stable across windows.

**Cross-pair (Stage 2) frozen-θ choice.** The mode of the 7 locked-θ
values is used on the cross-pair slice. If the mode is not unique
(bimodal or all-different), Stage 2 is run separately at each mode
candidate and any one of them replicating counts as `alive` for that
θ; a divergent Stage 2 across the mode candidates is a
`parked_unstable_theta` verdict.

---

## §5 Stop rules

- **Stage 0.** If no θ produces an IS Sharpe > raw-baseline IS Sharpe
  on any of the 7 windows → **STOP at Stage 0.** Verdict:
  `dead_no_ranking`. E015 (conviction-from-quality) is **not launched**
  (its premise depends on quality-score having a monotone relationship
  with expectancy).
- **Stage 1.** If OOS pooled CI is `dead` or `parked_low_yield` →
  **STOP at Stage 1.** Do not consume cross-pair slice.
- **Stage 2.** If cross-pair fails → downgrade to
  `parked_weak_effect` (EURUSD-only). Production port (Wave 6) is
  not authorised.

---

## §6 Amendments

_(No amendments yet - appended after pre-registration commits only.)_

---

## §7 Cross-references

- **E004 walk-forward** ([`../E004_walk_forward/PROTOCOL.md`](../E004_walk_forward/PROTOCOL.md))
  - baseline OOS median.
- **E005 cross-pair sealed** ([`../E005_cross_pair_sealed/`](../E005_cross_pair_sealed/))
  - Stage-2 replicate.
- **E015 conviction-from-quality**
  ([`../E015_conviction_from_quality/PROTOCOL.md`](../E015_conviction_from_quality/PROTOCOL.md))
  - downstream dependency.
- **Related M001 aggregator finding.** The M001 Φ5 Arm 2 (TQS floor)
  post-hoc computation showed +0.0187 TQS lift from filtering
  low-conviction proposals at the SQUAD level. E014 is the analogous
  question at the ROSTER-member level for the deployed cell.
- **Detector reference.**
  `multi-pair-trading-agent/agent/detectors/zones.py::compute_zone_quality`

---

## §8 Data-ledger declaration

| Stage | Pair | TF | Slice | Status this experiment | Prior uses |
|---|---|---|---|---|---|
| 0-1 | EURUSD | H4 | 2015-2025 | new sim (quality-gated fork) | E001-E005, E011, E013 |
| 2 | GBPUSD | H4 | 2015-2024 | new sim on E005 sealed slice | E001, E004, E005 |
| 2 | USDCAD | H4 | 2015-2024 | new sim on E005 sealed slice | E001, E004, E005 |

The re-consumption of E005-sealed cross-pair slices for a strategy
variant is disclosed here per DATA_LEDGER discipline.

---

**Pre-registration commit:** _(hash after push)_
