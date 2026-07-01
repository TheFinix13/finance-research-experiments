# E015 - Conviction-from-quality sizing for `zone_d1_against` H4 (pre-registered)

**Status:** PRE-REGISTERED 2026-07-01 · **Date frozen:** 2026-07-01 ·
**Gate:** conditional on E014 verdict `alive_positive` OR
`alive_equivalent_higher_hit_rate`.

`SupplyDemandAlpha` currently emits every signal with a **hardcoded
`conviction = 0.65`** ([`zone_alpha.py:229`](https://github.com/finance/multi-pair-trading-agent/blob/main/agent/alphas/concepts/zone_alpha.py#L229)),
which means the position sizer's 0.5-2 % risk band never varies with
signal quality: every trade risks the same 1.475 %. This has two
consequences:

1. Live sizing never rewards a *known-better* signal with more risk
   capital, so the account cannot compound quickly on high-quality
   zones.
2. Live sizing never punishes a marginal signal with less risk, so the
   low-quality tail contributes full-weight losses.

E015 asks: **does wiring `conviction = f(quality_score)` produce a
higher terminal-equity ratio (vs the flat-0.65 baseline) on the 7
walk-forward windows at a fixed starting balance?**

This is a genuine strategy change. E015 does NOT ship to production
without a positive verdict here PLUS a Wave-6 validation on the
production repo's own pipeline. The change also depends on E014
because it presumes quality_score correlates with expectancy - E015
is the sizing consequence of E014's binary gating question.

Follow [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md). Registered
in [`EXPERIMENTS.md`](../../EXPERIMENTS.md). Data accounting in
[`DATA_LEDGER.md`](../../DATA_LEDGER.md).

---

## §0 Reuse declaration

E015 reuses the following artefacts exactly. The ONLY new code is
(a) a conviction-mapping function on `quality_score` and
(b) a sizing-aware walk-forward driver that tracks a running balance
per arm.

| Purpose | Module / artefact |
|---|---|
| Alpha family | `finance-research-experiments/programs/E014/alpha_quality_gated.py::SupplyDemandAlpha_QualityGated` (from E014, frozen at E014 pre-reg commit) |
| Position sizer reference | `multi-pair-trading-agent/agent/live/position_sizer.py::PositionSizer` (behaviour mirrored in driver; not called live) |
| Sizing-aware driver | `finance-research-experiments/programs/E015/run_sizing_walk_forward.py` (new; extends `run_walk_forward_ab.py`) |
| Bar loader | `multi-pair-trading-agent/agent/data/loader.py::BarLoader` |
| Bootstrap CI | `multi-pair-trading-agent/agent/backtest/metrics.py::bootstrap_p_value` |
| E014 verdict | `finance-research-experiments/experiments/E014_quality_score_entry_gate/REPORT.md` (must be `alive_*` before E015 runs) |

**Conviction-mapping function (frozen).**

```python
def conviction_from_quality(quality_score: float) -> float:
    """Linear map from 0-100 quality_score to 0.30-0.95 conviction band.
    quality_score < 30 -> 0.30 (rejected by E014 gate; here as safety net)
    quality_score = 50 -> 0.55
    quality_score = 70 -> 0.75
    quality_score >= 90 -> 0.95 (clamp)
    """
    q = max(0.0, min(100.0, quality_score))
    return 0.30 + 0.65 * (q / 100.0)
```

The mapping bounds (0.30 minimum, 0.95 maximum) match the sizer's
`risk_min_pct=0.005` / `risk_max_pct=0.02` band; conviction is the
sizer's interpolation input in
[`position_sizer.risk_pct_for_conviction`](multi-pair-trading-agent/agent/live/position_sizer.py).
The mapping is LINEAR at pre-reg to avoid over-fitting curvature to
one week of live data. Any curvature study is a separate future
experiment.

---

## §1 Hypothesis (operational)

**Baseline arm.** `SupplyDemandAlpha_QualityGated` (E014 fork) with
`conviction = 0.65` flat, sized under the production `PositionSizer`
rules mirrored in the driver. Same $100 starting balance.

**Variant arm.** Same alpha, but `conviction = conviction_from_quality(
qz.quality.quality_score)` per signal.

**H0.** Terminal equity ratio `(variant / baseline)` pooled across
the 7 walk-forward windows is **not** materially above 1.0
(bootstrap 95 % CI contains 1.0).

**H1.** Terminal equity ratio bootstrap 95 % CI is **strictly above**
1.0 (variant grows the account faster than baseline on the same
signal set).

**Guardrail H2 (maximum drawdown).** Variant maximum drawdown must
NOT be > 1.25 × baseline maximum drawdown on any single window.
Higher edge with proportionally-higher drawdown is not a win; sizing
should be sharpe-preserving, not merely return-inflating.

**Outcome metric.** Per-window terminal-equity ratio (variant final
balance / baseline final balance), pooled across 7 windows, bootstrap
95 % CI, 5,000 resamples, seed 42.

**Secondary metric (reported, not gated).** Per-window Sharpe delta
(variant - baseline) via the same driver's trade P&L stream.

---

## §2 Separation

- **Does this touch the trading agent?** No. The conviction-mapping
  function and sizing-aware driver live in this repo. Production
  `SupplyDemandAlpha` still emits `conviction = 0.65`. Production
  `PositionSizer` is read for reference only.
- **Prior uses of the same data slice.** EURUSD H4 2015-2025 has been
  screened by E001-E005, re-analysed by E011, re-simulated by E013,
  and re-simulated by E014. E015 is another new statistical draw
  because sizing changes the compounded balance trajectory. DATA_LEDGER
  row added at Stage 1.

---

## §3 Locked parameters

| Knob | Value | Rationale |
|---|---|---|
| Alpha family | `SupplyDemandAlpha_QualityGated` @ E014 locked θ | Inherits E014 verdict; no threshold re-tuning |
| Conviction map | `0.30 + 0.65 * (quality_score / 100)` linear | Pre-registered; no post-hoc curvature |
| Starting balance | 100 (currency-agnostic) | Matches live-agent $100 demo baseline |
| Sizer risk band | `risk_min_pct=0.005, risk_max_pct=0.02` | Matches `LiveConfig` |
| Sizer minimum lot | `lot_min=0.01` | Matches production `RiskConfig.lot_min` |
| Sizer lot step | `lot_step=0.01` | Matches production |
| Tiered lot cap | `lot_hard_cap_under_300=0.01, lot_hard_cap_under_1000=0.10, lot_hard_cap=1.0` | Matches production |
| Compounding | Yes; each closed trade updates running balance | Matches live-agent behaviour |
| Backtest cost | `cost_for("H4")` from `BacktestConfig` | Standard |
| Bootstrap resamples | 5,000 | Convention |
| Random seed | 42 | Convention |
| n-gate | 15 trades per window per arm | Below this, per-window is dropped |

**Verdict (locked):**

- `alive_positive` iff terminal-equity ratio bootstrap-95 % CI lower
  bound > 1.0 AND max drawdown constraint (H2) is satisfied on every
  window.
- `alive_but_riskier` iff CI lower bound > 1.0 AND H2 violated on
  one or more windows. Requires the H2 violation windows to be
  disclosed; downstream production-port decision is a judgement call,
  not an automatic promote.
- `parked_weak_effect` iff CI contains 1.0.
- `dead` iff CI upper bound < 1.0 (variant compounds slower).

---

## §4 Statistical pipeline

| Stage | Pair | Period | Family | Test | FDR |
|---|---|---|---|---|---|
| 1 - Walk-forward | EURUSD | 7 × 1-yr OOS folds | 1 variant | Bootstrap-95 % CI on terminal-equity ratio | per-cell α = 0.05 |
| 2 - Cross-pair replicate | GBPUSD, USDCAD | 2015-2024 (E005 sealed) | Stage-1 survivors | Bootstrap-95 % CI, frozen params | per-cell α = 0.05 |

---

## §5 Stop rules

- **Stage 1.** If terminal-equity ratio CI is `dead` OR max-drawdown
  guardrail (H2) fails on any window → **STOP at Stage 1.** Do not
  consume cross-pair slice. Production port is not authorised.
- **Stage 2.** If cross-pair fails → downgrade to
  `parked_weak_effect` (EURUSD-only).

---

## §6 Amendments

_(No amendments yet - appended after pre-registration commits only.)_

---

## §7 Cross-references

- **E014 quality-score entry gate**
  ([`../E014_quality_score_entry_gate/PROTOCOL.md`](../E014_quality_score_entry_gate/PROTOCOL.md))
  - upstream dependency.
- **Live-agent sizer.**
  `multi-pair-trading-agent/agent/live/position_sizer.py`
- **Live-agent conviction hardcode.**
  `multi-pair-trading-agent/agent/alphas/concepts/zone_alpha.py:229`
  and `:252` (both zone directions).
- **Live-agent risk band.**
  `multi-pair-trading-agent/agent/live/config.py::LiveConfig` -
  `risk_min_pct=0.005`, `risk_max_pct=0.02`, `max_trade_risk_pct=0.02`.

---

## §8 Data-ledger declaration

| Stage | Pair | TF | Slice | Status this experiment | Prior uses |
|---|---|---|---|---|---|
| 1 | EURUSD | H4 | 2015-2025 | new sim (sizing-variant fork) | E001-E005, E011, E013, E014 |
| 2 | GBPUSD | H4 | 2015-2024 | new sim on E005 sealed slice | E001, E004, E005 |
| 2 | USDCAD | H4 | 2015-2024 | new sim on E005 sealed slice | E001, E004, E005 |

---

**Pre-registration commit:** _(hash after push)_
