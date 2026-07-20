# E021 — Partial exit at fixed-R milestone — REPORT

**Verdict:** `dead` · **Date:** 2026-07-20 · **Generator commit:** `7e1a3e7`

- Pre-registration: [`PROTOCOL.md`](./PROTOCOL.md)
- Full numeric artefact: [`../../programs/E021/results.json`](../../programs/E021/results.json)
- Data plane: [`../../programs/_shared/counterfactual_replay/SPEC.md`](../../programs/_shared/counterfactual_replay/SPEC.md) (PRE-0)
- Stop notice: [`STOP_NOTICE.md`](./STOP_NOTICE.md)
- Sibling result for context: [`../E020_mfe_ratcheted_trail/REPORT.md`](../E020_mfe_ratcheted_trail/REPORT.md)

## §1 Verdict summary

Zero of the nine arms on the frozen §4 grid meet the `alive` criteria of
PROTOCOL §6. **All nine arms show a statistically significant NEGATIVE
ΔSharpe** on the pooled per-trade R sequence, with pooled bootstrap-95 %
CIs that lie entirely below 0. BH-FDR at α = 0.10 rejects H0 in the
*opposite* direction from H1 for every arm — i.e. every arm on the grid
HURTS the deployed cell's Sharpe on this trade population.

The H2 special case (`parked_lower_variance_lower_return`) does **not**
rescue any arm: while Δ variance of R is statistically negative for all
nine arms (CI-UB below 0 for the variance shift), the ΔSharpe CI for
every arm sits **entirely below 0**, not straddling it. Per PROTOCOL
§5.3, H2 requires ΔSharpe CI to *include* 0 — which is not met.
Numerically, E021's variance reduction is real, but it is dominated by a
larger reduction in mean R, so the Sharpe direction is unambiguously
down.

The stop rule from PROTOCOL §6 fires: **keep the shipped `all_on` cell
as-is; keep `LiveConfig.partial_exits = False`; write `STOP_NOTICE.md`;
do not open a Phase 2b; do not extend the grid; do not promote a
secondary metric to primary post hoc.**

## §2 Headline numbers (9 arms × 5 folds × 3 symbols pooled, n = 2,388)

| arm_id | ΔSharpe | 95 % CI | BH-adj p | folds+ | ΔVariance R | ΔVar CI-UB | fire-rate | verdict |
|---|---:|---|---:|---:|---:|---:|---:|---|
| pR0.7_pf0.25 | −0.1161 | [−0.1472, −0.0869] | 0.0000 | 0/5 | −0.6986 | −0.6443 | 63.23 % | dead |
| pR0.7_pf0.4  | −0.1245 | [−0.1565, −0.0936] | 0.0000 | 0/5 | −0.8261 | −0.7725 | 63.23 % | dead |
| pR0.7_pf0.5  | −0.1314 | [−0.1638, −0.0997] | 0.0000 | 0/5 | −0.8981 | −0.8445 | 63.23 % | dead |
| pR1.0_pf0.25 | −0.1116 | [−0.1428, −0.0827] | 0.0000 | 0/5 | −0.5706 | −0.5161 | 56.66 % | dead |
| pR1.0_pf0.4  | −0.1158 | [−0.1472, −0.0863] | 0.0000 | 0/5 | −0.6374 | −0.5843 | 56.66 % | dead |
| pR1.0_pf0.5  | −0.1192 | [−0.1508, −0.0893] | 0.0000 | 0/5 | −0.6757 | −0.6233 | 56.66 % | dead |
| **pR1.3_pf0.25** | **−0.1076** | **[−0.1385, −0.0790]** | **0.0000** | **0/5** | **−0.4895** | **−0.4346** | **46.82 %** | **dead** |
| pR1.3_pf0.4  | −0.1087 | [−0.1399, −0.0800] | 0.0000 | 0/5 | −0.5166 | −0.4618 | 46.82 % | dead |
| pR1.3_pf0.5  | −0.1097 | [−0.1408, −0.0810] | 0.0000 | 0/5 | −0.5323 | −0.4780 | 46.82 % | dead |

`pR1.3_pf0.25` is the **least-bad** arm (highest ΔSharpe, lowest
fire-rate); it still finishes deeply in the `dead` region.

**BH-FDR at α = 0.10** rejects H0 for all 9 arms — but the rejection is
in the direction of DEGRADATION, not improvement (single-tailed
inspection: every arm's CI-high is strictly below 0). No arm is
`alive`. No arm is `parked_low_yield` (parked-low-yield requires the
point estimate > 0 with thin evidence; here every point is negative).
No arm is `parked_lower_variance_lower_return` (the H2 gate demands
ΔSharpe CI *include* 0; every arm's CI lies entirely below 0).

## §3 Mechanism — the partial IS working, but its price is too high

The guardrails and mechanism diagnostics confirm the partial-exit
mechanic is behaving exactly as PROTOCOL §3 predicts — it just doesn't
pay in Sharpe terms on this cell:

| Guardrail / diagnostic | Baseline | Arm (pR=0.7, pf=0.4) | Δ | Reading |
|---|---:|---:|---:|---|
| Tail-mean R (worst 10 %) | −2.00 | −1.00 | **+1.00** | Partial caps the tail exactly like BE-at-1R — worst decile lifts from −2R to −1R. |
| Δ mean R (whole population) | — | — | **−0.22** | The mean is where the damage lands: banking early caps the residual runner. |
| Δ variance of R | — | — | **−0.83** (CI-UB −0.77) | Real, statistically-significant variance reduction — but not enough for H2. |
| Fire-rate | — | — | **63 %** | 1,510 of 2,388 trades cross ≥ 0.7R at some point on their intraday path and fire the partial. |
| P(alt.r > 0 &#124; partial fired) | 0.749 | 0.896 | **+0.15** | The partial does rescue: +15 pp of fired trades convert from would-be losers to net winners. |
| Δ mean R on the fired cohort | 0.97 | 0.82 | **−0.15** | The cost: on the *fired* subset, mean R falls because banking 40 % at 0.7R caps the runner's 1.5R residual. |

Two consistent stories across the grid:

1. **Give-back protection is real.** For `partial_R = 1.0` arms, 100 %
   of fired trades end at alt_r > 0 (compared to 82 % under baseline),
   because banking 25–50 % of the position at exactly 1R locks in a
   guaranteed positive component even if the residual gives back to BE.
   The `partial_R = 0.7` arms convert +15 pp of losers to winners; the
   `partial_R = 1.0` arms convert +18 pp; the `partial_R = 1.3` arms
   convert +7 pp (much less headroom above 1.3R and below the 1.5R TP).
2. **The cost is winner-choke.** Every fired trade whose baseline was
   ≥ 1.0R sees its residual (`1 − partial_fraction`) truncated to a
   fraction of the original R gain. On a TP-clean base winner
   (baseline r = 1.5), `(pR=1.0, pf=0.4)` produces
   `alt_r = 0.4·1.0 + 0.6·1.5 = 1.30` — a 0.20R give-up. Aggregated
   over ~56 % of the cell's trades, this dominates the tail-cap and
   rescue gains.

## §4 Why parsimony (higher `partial_R`, lower `partial_fraction`) doesn't rescue

PROTOCOL §4 predicted a parsimony gradient: higher `partial_R` fires
less (disturbs fewer runners), lower `partial_fraction` gives up less on
each firing. The results show the gradient is monotone but never
crosses zero:

- Holding `partial_fraction = 0.25` (lightest scale-out): pR=0.7 gives
  ΔSharpe = −0.116; pR=1.3 gives −0.108. Only a ~0.008 gap over the
  whole `partial_R` range — the mechanism can't be tuned into the
  positive half-plane by moving the trigger later.
- Holding `partial_R = 1.3` (latest fire): pf=0.25 gives −0.108;
  pf=0.5 gives −0.110. Only a ~0.002 gap over the whole
  `partial_fraction` range.

The best arm (`pR1.3_pf0.25`) trades off half the fire rate (47 % vs
63 %) for a 0.024 ΔSharpe improvement over the worst arm — but that
improvement leaves ΔSharpe at −0.108 (CI [−0.139, −0.079]), still
comfortably in the `dead` region.

**Diagnostic reading:** the fundamental problem is not the fire-point
or the fraction. It is that the deployed cell's TP = 1.5R geometry and
existing BE-at-1R protection leave very little Sharpe headroom for a
mechanical partial-close: the winners you protect are already being
protected by BE, and the winners you truncate are the ones that would
have carried the mean R.

## §5 Per-symbol stratification (PROTOCOL §5.5 diagnostic)

Winning-arm-by-symbol is a common single-symbol-luck failure mode. Here
the diagnostic simply confirms uniformity: no arm-symbol pair is close
to zero, and USDCAD (the H4-only-path symbol) hurts consistently more
than the M5/M15-path symbols.

| Arm | EURUSD ΔSharpe | GBPUSD ΔSharpe | USDCAD ΔSharpe |
|---|---:|---:|---:|
| pR0.7_pf0.25 | −0.099 | −0.096 | −0.160 |
| pR0.7_pf0.5  | −0.114 | −0.107 | −0.181 |
| pR1.0_pf0.25 | −0.094 | −0.093 | −0.154 |
| pR1.0_pf0.5  | −0.100 | −0.099 | −0.166 |
| pR1.3_pf0.25 | −0.089 | −0.091 | −0.149 |
| pR1.3_pf0.5  | −0.088 | −0.093 | −0.154 |

USDCAD's H4-only path resolution (SPEC amendment 2026-07-20) is the
most-degraded symbol on this metric under every arm. This is
diagnostic-interesting for the shared engine: at coarser path
resolution, the partial-trigger detection may be firing on more
intra-bar wicks that a finer-grained path would have paired with a
subsequent extension to TP. Reported here as engine-behaviour context
for a future PRE-0 amendment; it does not change the verdict, since
even the M5-path EURUSD trades are still deeply negative
(−0.089 ΔSharpe at the least-bad arm).

## §6 Comparison to the E020 verdict — same-cell exit-mechanism family

E020 (MFE-ratcheted trailing stop) landed `dead` on 2026-07-20 with
ΔSharpe range [−0.114, −0.103] across its 12 arms. E021's range is
comparably negative — [−0.131, −0.108] across 9 arms. Both studies
share the underlying explanation: the deployed `all_on` cell's stack
(wick-proof SL + BE-at-1R + PLG) already absorbs the tail risk that
mechanical MFE-based intervention would try to add. Where E020 saw
"the ratchet chokes runners", E021 sees "the partial banks early but
caps residual runners". Different mechanisms, same net effect on this
cell's Sharpe.

**One structural difference worth recording:** E021's variance
reduction is a first-order effect (ΔVar CI-UB < 0 by 0.43 – 0.85 on all
arms) — larger and more uniformly detected than E020's tail-mean gain.
That makes E021 a genuine *variance generator* candidate for a joint
stack, but only if a partner mechanism can restore the mean R without
un-doing the partial's tail protection. Per PROTOCOL §6 stop rule, this
observation is recorded for future E025 consideration but is **not**
grounds to promote any single E021 arm.

## §7 What this study does / does not tell E025

E021 has just handed the exit-management campaign a second cheap,
honest, population-level negative result. That produces three
downstream implications for the joint-stack study (E025):

1. **E021 cannot be stacked as an alpha-additive.** Under this cell's
   BE + wick-proof + PLG stack, adding a mechanical partial at any
   ``partial_R ∈ {0.7, 1.0, 1.3}`` × ``partial_fraction ∈
   {0.25, 0.4, 0.5}`` produces a statistically-detectable Sharpe
   REDUCTION. E025's search-space should NOT include E021 as an
   additive stack component in its "add mechanism M on top of `all_on`"
   family.
2. **E021's variance-generator property survives.** Although the H2
   `parked_lower_variance_lower_return` special case did not fire (the
   Sharpe CI was too negative to straddle 0), the *sign* of the
   variance shift is what E025 would care about in a risk-budget-stack
   context. Δ variance of R ≤ −0.49 (CI-UB) at every arm, monotone in
   both `partial_R` and `partial_fraction`. E025 could still consider
   E021 in a **variance-target substitution** role — trading strict
   Sharpe maximisation for lower R variance — but this would be a new
   study framing, not a promotion of E021 as-is. Per PROTOCOL §6, that
   framing needs its own pre-registration; it is not authorised here.
3. **Family-multiplicity budget reduction.** E021's 9 arms join E020's
   12 as "search width consumed and rejected". E025's family-size
   argument for the deflated Sharpe (`bailey2014deflated`) now
   subtracts 9 more arms from the campaign's effective search width.
   The E025 protocol will need a fresh count of the effective family
   size after both E020 and E021 lockings.

E023 (post-BE structure trail) and E024 (near-TP stall exit) remain the
open exit-mechanism questions. E024 in particular has a structurally
narrower trigger than E021 (fires only when price stalls near TP), so
it should not share the runner-choke pathology E021 exhibits. E024
remains worth running.

## §8 What we DO NOT do (§6 stop rule)

Per PROTOCOL §6 and `PROTOCOL_DISCIPLINE.md` §5, the `dead` verdict
triggers explicit non-actions:

1. **Do not** extend the arm grid to search for a positive arm.
2. **Do not** promote a secondary metric (e.g. Δ tail-mean R = +1.00 on
   the worst decile, or Δ variance R = −0.5 to −0.9 R² — real effects
   but neither is the primary decision variable) to primary post hoc.
3. **Do not** ship any partial-exit variant to the deployed cell.
4. **Do** keep the shipped `all_on` cell (wick-proof SL + BE-at-1R +
   PLG, `LiveConfig.partial_exits = False`) as-is.
5. **Do** register a `STOP_NOTICE.md` in this directory that captures
   the specific mechanism (real variance reduction + real tail cap +
   real rescue, dominated by mean-R give-up on the ~50–63 % fired
   cohort).

## §9 Ex-post replay of the PROTOCOL §5.4 motivating GBPUSD trades

PROTOCOL §5.4 anchors three motivating trades. The population-level
finding necessarily supersedes the n = 1–2 case-study, but the case
computation confirms the mechanism side:

- **GBPUSD ticket 2966547972** (TP-clean +1.96R winner) under arm
  `(partial_R=1.0, partial_fraction=0.4)`:
  `alt_r = 0.4·1.0 + 0.6·1.5 = 1.30R`. A **0.66R give-up on a TP-clean
  winner** — exactly the winner-choke cost the population verdict
  attributes the negative ΔSharpe to.
- **GBPUSD ticket 2969136564** (open at freeze; MFE 1.49R then fading)
  under the same arm: worst case `alt_r = 0.4R`, best case
  `alt_r = 1.30R`. On a *MFE-then-fade runner*, the partial delivers
  the +0.15pp rescue effect the pooled `p_arm_positive_on_fired = 1.0`
  number captures.
- **USDCAD full-cycle loser at −1.02R**: never reaches +0.7R, no partial
  fires, `alt_r = baseline r = −1.02` — the reversal-guard invariant
  (§3.4) holds trivially.

None of these single trades is a statistical claim; the pooled verdict
(§1) is. The case-study just confirms that the pooled numbers describe
the same regime the review flagged.

## §10 Reproducibility

```bash
cd finance-research-experiments
PYTHONPATH=../multi-pair-trading-agent:.:scripts \
    ../multi-pair-trading-agent/.venv/bin/python \
    programs/E021/run_e021_validation.py \
    --output programs/E021/results.json
```

- Wall-clock: **7.1 seconds** for the full 9-arm × 5-fold × 3-symbol
  sweep (2,388 pooled trades, 5,000 bootstrap resamples per arm).
- Deterministic (bootstrap seed 42, single primary metric, no post-hoc
  tuning); re-running produces byte-identical `results.json` on the
  same PRE-0 ledgers.
- Reproducing requires PRE-0 path ledgers under
  `programs/_shared/counterfactual_replay/data/` (regenerable via
  `programs/_shared/counterfactual_replay/export_ledger_with_paths.py`
  per SPEC §8 delivery order).
- Unit tests: `pytest programs/E021/tests/test_e021_rule.py` — 3
  passing (null-partial identity, partial-fires-at-trigger-price,
  partial-preempted-by-SL).

Full numeric detail (per-fold ΔSharpe with CIs, guardrails, mechanism
diagnostics, per-symbol stratification, BH-FDR flags + adjusted p, per-arm
verdicts) is in
[`../../programs/E021/results.json`](../../programs/E021/results.json).
