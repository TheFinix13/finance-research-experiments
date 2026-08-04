# E031 — STOP NOTICE

**Stopped 2026-08-04 at the Stage-1 go/no-go: 0/4 arms alive → DEAD.**
Stop rule §5 ("Stage 1: 0/4 arms alive → STOP") fired. Confirm
(2022–2024) and sealed (2025 → 2026-07-25) reservations are RELEASED
un-consumed — zero OOS cost.

Pre-registration commit `c838b28` (protocol frozen before any
computation); harness + this notice committed together 2026-08-04.

---

## 1. What was tested

Whether relaxing the per-symbol position cap (cap=2, cap=3) or
replacing a losing incumbent ticket with a fresh signal
(replace at ≤ −0.25R unrealized; same-direction variant) improves
pooled portfolio Sharpe over the reconstructed cap=1 baseline, on the
frozen production `zone_d1_against` signal stream
(EURUSD/GBPUSD/USDCAD H4, 2015-01-01 → 2021-12-31 screen).

Motivation was live: 6/6 GBPUSD signals blocked by
`risk_manager: max_positions` across two consecutive live weeks
resolved as +1.5R winners while a losing carried ticket held the slot.

## 2. Stage 0 — feasibility: PASSED decisively

Slot-conflict events (signal arrives while the cap=1 slot is full),
screen period — floor was ≥ 100/symbol:

| Symbol | Slot conflicts |
|---|---|
| EURUSD | 741 |
| GBPUSD | 1,212 |
| USDCAD | 804 |

The live pattern has an enormous base rate. The question was never
"does blocking happen" — it was "are the blocked signals worth taking".

## 3. Stage 1 — screen: 0/4 arms alive

Baseline A0 (cap=1): 2,068 trades, annualised daily-return Sharpe
+2.01, MaxDD −16.9% (reconstruction-grade numbers; deltas are the
verdict-bearing quantity). Moving-block bootstrap (block 20 days,
5,000 reps), BH-FDR α = 0.05 across 4 arms, ≥ 4/5 folds required:

| Arm | n trades | ΔSharpe | 95% CI | p (one-sided) | Folds + | Replacements | Verdict |
|---|---|---|---|---|---|---|---|
| A1 cap=2 | 3,178 | −0.095 | [−0.382, +0.212] | 0.725 | 1/5 | — | dead |
| A2 cap=3 | 3,867 | −0.326 | [−0.653, +0.045] | 0.958 | 2/5 | — | dead (MaxDD also ~58% worse rel.) |
| B1 replace-losing | 2,827 | −0.266 | [−0.572, +0.059] | 0.950 | 1/5 | 515 | dead |
| B2 replace-same-dir | 2,813 | −0.222 | [−0.530, +0.100] | 0.913 | 1/5 | 506 | dead |

Every arm's point estimate is NEGATIVE. No BH pass, no fold
consistency, and the dose-response goes the wrong way (cap=3 is worse
than cap=2).

## 4. Interpretation

The live anecdote is recorded as **anecdote-not-confirmed** (per §5).
Two mechanisms show up in the reconstruction:

1. **Marginal-signal quality.** The signals the cap throws away are,
   on average over 7 years, no better than the incumbents already
   holding the slot — extra trades dilute rather than add (A1/A2 take
   54–87% more trades for less Sharpe).
2. **The fade needs room to be wrong.** Replacement arms fired ~510
   times each; cutting an incumbent at −0.25R forfeits exactly the
   mean-reverting recovery the `zone_d1_against` edge lives on, and
   the replacement's own expectancy doesn't cover the realized losses
   it crystallizes.

The 6/6 live week clustered around one pathological carried ticket in
one trending week — a tail configuration, not the base rate.

## 5. Consequences

- **No change to production `max_open_positions=1`.** The cap is not
  a measurable leak at portfolio level; if anything it is protective.
- The E031/E032 joint-interaction clause is moot (E032 also stopped).
- Live evidence class "resolver counterfactual winners blocked by
  max_positions" should keep being tracked in weekly reviews, but the
  burden for re-opening this line is now a mechanism DIFFERENT from
  simple cap relaxation / R-threshold replacement (both measured dead).

## 6. Deviations from protocol

- Incumbent replacement executes at the NEXT bar's open (protocol
  said "at market"; the H4 replay's closest honest market fill is the
  next open). Same fill convention as new entries — no arm-asymmetry.
- Conviction was declared fixed 0.65 in §3 but is unused because
  sizing is fixed 1% × risk_scale (declared in the same table).
- SL-first intrabar tie-break (conservative house convention),
  identical across arms including baseline.
