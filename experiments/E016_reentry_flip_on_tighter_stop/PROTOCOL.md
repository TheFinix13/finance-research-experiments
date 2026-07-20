# E016 - Re-entry / flip on tighter-stop signal for `zone_d1_against` H4 (pre-registered)

**Status:** PRE-REGISTERED 2026-07-01 · **Date frozen:** 2026-07-01 ·
**Gate:** conditional on BOTH E011 Stage-1 verdict `alive_positive`
AND E014 Stage-1 verdict `alive_positive` OR
`alive_equivalent_higher_hit_rate` (i.e., we trust both that small-stop
trades have edge AND that quality_score ranks that edge honestly).

The current live loop obeys a strict "one position per symbol" rule
(see `agent/live/signal_loop.py::_maybe_enter`). If a trade is open
and a **new, tighter-stop signal fires in the same or opposite
direction while the current position is in drawdown**, the new signal
is dropped. E016 asks: **should it be?**

Three sub-questions map to three sub-arms:

1. **Hold arm.** Current behaviour: ignore the new signal. Baseline.
2. **Close-and-flip arm.** If the new signal is OPPOSITE the current
   position AND the current position is at ≥ 0.5R drawdown AND the
   new signal has a strictly tighter stop → close the current position
   at market and open the new signal.
3. **Add-on-same-side arm.** If the new signal is SAME direction as
   the current position AND the current position is at ≥ 0.5R drawdown
   AND the new signal has a strictly tighter stop → open a second
   position at the new signal's tighter stop. The second position is
   sized at `max_added_conviction × baseline_risk` (frozen 0.5).

E016 is the most speculative of the six studies. It runs LAST because
its premise depends on TWO prior verdicts being positive, AND because
adding positions changes the risk model non-trivially.

Follow [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md). Registered
in [`EXPERIMENTS.md`](../../EXPERIMENTS.md). Data accounting in
[`DATA_LEDGER.md`](../../DATA_LEDGER.md).

---

## §0 Reuse declaration

E016 reuses the following artefacts. New code is limited to the
sub-arm decision logic + a multi-position-aware walk-forward driver.

| Purpose | Module / artefact |
|---|---|
| Alpha family | `SupplyDemandAlpha_QualityGated` @ E014 locked θ (from E014) |
| Multi-position driver | `finance-research-experiments/programs/E016/run_reentry_walk_forward.py` (new) |
| Bar loader | `multi-pair-trading-agent/agent/data/loader.py::BarLoader` |
| Bootstrap CI | `multi-pair-trading-agent/agent/backtest/metrics.py::bootstrap_p_value` |
| E011 + E014 verdicts | Both must be `alive_*` at Stage 0 |

**Trigger-condition primitives (frozen).**

- "New signal is tighter-stop" ≡ `new_signal.stop_pips <
  0.75 * open_position.stop_pips` (must be at least 25 % tighter to
  count).
- "Current position at ≥ 0.5R drawdown" ≡ current mark-to-market
  P&L in pips is ≤ `-0.5 × open_position.stop_pips`.
- "Opposite direction" ≡ new signal direction ≠ open position
  direction.
- "Same direction" ≡ new signal direction == open position direction.

Any change to these primitives is a §6 amendment.

---

## §1 Hypothesis (operational)

**Trade-episode definition.** An "episode" begins when a trade is
opened and ends when the last position within that episode closes.
For the hold arm, episodes are one-position. For close-and-flip
episodes are two positions in opposite directions. For
add-on-same-side episodes are two positions in the same direction
with different stops.

Episodes qualifying for E016 are the ones where a re-entry trigger
condition (§0) was met during the open trade's lifetime. All other
signals proceed under E014-baseline single-position behaviour and are
NOT part of E016's outcome pool.

**Baseline arm (hold).** Ignore the tighter-stop signal. This is the
current live behaviour; it re-runs against the same signal set as
the two variants for statistical parity.

**H0 (per variant).** Variant's per-episode net pips is **not**
materially different from baseline (hold) per-episode net pips on the
qualifying-episode subset (bootstrap 95 % CI contains 0).

**H1 (per variant).** Variant's per-episode net pips bootstrap 95 %
CI is **strictly above** 0.

**Guardrail H2 (episode-count).** If fewer than 20 qualifying
episodes fire across the 7 walk-forward OOS folds combined, verdict
is `parked_insufficient_n` and the variant is not carried to Stage 2.

**Guardrail H3 (drawdown-scaling).** For the add-on-same-side variant,
per-episode maximum drawdown must NOT exceed 2 × baseline stop
distance. Larger drawdowns imply overexposure; production port
requires this constraint.

**Outcome metric.** Pooled per-episode net pips over the 7 walk-forward
OOS folds, per variant, bootstrap 95 % CI, 5,000 resamples, seed 42.

---

## §2 Separation

- **Does this touch the trading agent?** No. Multi-position driver
  lives in this repo under `programs/E016/`. Production
  `signal_loop.py` "one-position-per-symbol" rule is unchanged.
- **Prior uses of the same data slice.** EURUSD H4 2015-2025 used by
  E001-E005 + E011 + E013 + E014 + E015 (when it runs). E016 is a
  new statistical draw (different close/open sequence → different
  outcome sample). DATA_LEDGER row added at Stage 1.

---

## §3 Locked parameters

| Knob | Value | Rationale |
|---|---|---|
| Alpha family | `SupplyDemandAlpha_QualityGated` @ E014 locked θ | Inherits E014 verdict |
| Tighter-stop factor | 0.75 (new stop < 0.75 × open stop) | Frozen; a 25 % tightening is the minimum that matters for sizing |
| Drawdown trigger | 0.5R | Frozen; half-R DD is where the "am I wrong?" question genuinely applies |
| Add-on sizing factor | 0.5 × baseline risk | Frozen; total exposure at 1.5× baseline is the pre-registered ceiling |
| Backtest cost | `cost_for("H4")` from `BacktestConfig` | Standard |
| Bootstrap resamples | 5,000 | Convention |
| Random seed | 42 | Convention |
| n-gate | 20 qualifying episodes total (OOS pool) | Below this, `parked_insufficient_n` |

**Verdict (locked, per variant):**

- `alive_positive` iff bootstrap-95 % CI lower bound > 0 pips per
  episode AND H2 satisfied AND (for add-on-same-side) H3 satisfied.
- `parked_insufficient_n` iff qualifying episodes < 20.
- `dead` iff CI upper bound < 0.
- `dead_guardrail` iff H3 violated (add-on-same-side only).

Verdicts are per-variant. The close-and-flip variant can be `alive`
while the add-on-same-side variant is `dead_guardrail`; each stands
on its own.

---

## §4 Statistical pipeline

| Stage | Pair | Period | Family | Test | FDR |
|---|---|---|---|---|---|
| 1 - Walk-forward | EURUSD | 7 × 1-yr OOS folds | 2 variants (close-and-flip, add-on-same-side) | Bootstrap-95 % CI vs baseline | BH α = 0.05 across 2 |
| 2 - Cross-pair replicate | GBPUSD, USDCAD | 2015-2024 (E005 sealed) | Stage-1 survivors | Bootstrap-95 % CI, frozen params | per-cell α = 0.05 |

---

## §5 Stop rules

- **Stage 0 gate.** If E011 verdict is not `alive_positive` OR E014
  verdict is not `alive_positive` / `alive_equivalent_higher_hit_rate`
  → **DO NOT RUN E016.** Publish the dependency chain as the honest
  reason; the study does not fire.
- **Stage 1.** If both variants land in `dead` / `dead_guardrail` /
  `parked_insufficient_n` → **STOP at Stage 1.** Do not consume
  cross-pair slice.
- **Stage 2.** If any Stage-1 survivor fails cross-pair → downgrade
  to `parked_weak_effect` (EURUSD-only).

---

## §6 Amendments

_(No amendments yet - appended after pre-registration commits only.)_

---

## §7 Cross-references

- **E011 small-stop subset**
  ([`../E011_small_stop_subset_expectancy/PROTOCOL.md`](../E011_small_stop_subset_expectancy/PROTOCOL.md))
  - upstream dependency (small-stop signals must have edge).
- **E014 quality-score entry gate**
  ([`../E014_quality_score_entry_gate/PROTOCOL.md`](../E014_quality_score_entry_gate/PROTOCOL.md))
  - upstream dependency (quality-ranked signals are what we're
  swapping into).
- **Production one-position-per-symbol rule.**
  `multi-pair-trading-agent/agent/live/signal_loop.py::_maybe_enter`
- **Related M001 finding.** The M001 Φ4.1 "single-position-per-symbol
  queue with conviction-only ranking is the binding constraint"
  insight (see `finance-research-experiments/ai_context.md`) is the
  squad-level analogue of E016's cell-level question. E016 findings
  are advisory to M001 Φ5 Arm 4 (multi-position).

---

## §8 Data-ledger declaration

| Stage | Pair | TF | Slice | Status this experiment | Prior uses |
|---|---|---|---|---|---|
| 1 | EURUSD | H4 | 2015-2025 | new sim (multi-position fork) | E001-E005, E011, E013, E014, E015 |
| 2 | GBPUSD | H4 | 2015-2024 | new sim on E005 sealed slice | E001, E004, E005 |
| 2 | USDCAD | H4 | 2015-2024 | new sim on E005 sealed slice | E001, E004, E005 |

---

**Pre-registration commit:** _(hash after push)_
