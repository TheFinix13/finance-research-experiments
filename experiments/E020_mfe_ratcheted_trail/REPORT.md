# E020 — MFE-ratcheted trailing stop — REPORT

**Verdict:** `dead` · **Date:** 2026-07-20 · **Generator commit:** `faf186f`

- Pre-registration: [`PROTOCOL.md`](./PROTOCOL.md)
- Full numeric artefact: [`../../programs/E020/results.json`](../../programs/E020/results.json)
- Data plane: [`../../programs/_shared/counterfactual_replay/SPEC.md`](../../programs/_shared/counterfactual_replay/SPEC.md) (PRE-0)
- Stop notice: [`STOP_NOTICE.md`](./STOP_NOTICE.md)

## §1 Verdict summary

Zero of the twelve arms on the frozen §4 grid meet the `alive` criteria
of PROTOCOL §6. **All twelve arms show a statistically significant
NEGATIVE ΔSharpe** on the pooled per-trade R sequence, with pooled
bootstrap-95 % CIs that lie entirely below 0. BH-FDR at α = 0.10 rejects
H0 in the *opposite* direction from H1 for every arm — i.e. the ratchet
significantly HURTS the deployed cell's Sharpe on this trade population.

The stop rule from PROTOCOL §6 fires: **keep the shipped `all_on` cell
as-is; write `STOP_NOTICE.md`; do not open a Phase 2b; do not extend the
grid; do not promote a secondary metric to primary post hoc.**

## §2 Headline numbers (12 arms × 5 folds × 3 symbols pooled, n = 2,388)

| arm | ΔSharpe | 95 % CI | pooled p | folds+ | BH-FDR | verdict |
|---|---:|---|---:|---:|:---:|---|
| a1.0_l0.4 | −0.114 | [−0.146, −0.083] | 0.0000 | 0/5 | reject | dead |
| a1.0_l0.5 | −0.114 | [−0.147, −0.084] | 0.0000 | 0/5 | reject | dead |
| a1.0_l0.6 | −0.110 | [−0.143, −0.079] | 0.0000 | 0/5 | reject | dead |
| a1.0_l0.7 | −0.104 | [−0.137, −0.072] | 0.0000 | 0/5 | reject | dead |
| a1.2_l0.4 | −0.110 | [−0.142, −0.080] | 0.0000 | 0/5 | reject | dead |
| a1.2_l0.5 | −0.110 | [−0.142, −0.080] | 0.0000 | 0/5 | reject | dead |
| a1.2_l0.6 | −0.108 | [−0.140, −0.077] | 0.0000 | 0/5 | reject | dead |
| a1.2_l0.7 | −0.106 | [−0.139, −0.076] | 0.0000 | 0/5 | reject | dead |
| a1.3_l0.4 | −0.108 | [−0.139, −0.078] | 0.0000 | 0/5 | reject | dead |
| a1.3_l0.5 | −0.106 | [−0.138, −0.077] | 0.0000 | 0/5 | reject | dead |
| a1.3_l0.6 | −0.105 | [−0.136, −0.075] | 0.0000 | 0/5 | reject | dead |
| a1.3_l0.7 | −0.103 | [−0.134, −0.073] | 0.0000 | 0/5 | reject | dead |

**BH-FDR at α = 0.10** rejects H0 for all 12 arms — but the rejection is
in the direction of DEGRADATION, not improvement. All arms fail the
primary criterion (CI lower > 0) and the robustness criterion (≥ 4/5
folds positive). None is `alive`. None is `parked_low_yield` (parked
requires the point estimate to be > 0 with thin evidence; here every
point estimate is negative).

## §3 Mechanism check — the ratchet IS working, but its EV is wrong

The guardrails and mechanism diagnostics confirm the ratchet is
behaving exactly as PROTOCOL §3 predicts — it just doesn't pay:

| Guardrail | Baseline | Arm (a1.0_l0.4) | Δ | Reading |
|---|---:|---:|---:|---|
| Tail-mean R (worst 10 %) | −2.00 | −1.00 | **+1.00** | Ratchet caps tail at −1R (BE floor + ratchet), from −2R (panic exit) |
| Max consecutive-loss streak | 8 | 7 | −1 | Slight streak improvement |
| P(winner reaches ≥ 1 R) | 0.553 | 0.333 | **−0.22** | Ratchet chops 22 pp of would-be 1R+ winners |
| Sharpe (arm vs base) | 0.277 | 0.163 | −0.11 | Net Sharpe cost |

The tail-cap gain (+1R on the worst decile ≈ +239 R aggregate) is
dominated by the runner-choke cost. The mechanism diagnostic
`n_fired_no_reach` = **299 trades** where the ratchet activated
(MFE ≥ 1R) but the trade did not hit TP; their mean baseline R is
**−0.36** — meaning many of these were give-back trades where a naïve
BE-only stack also lost money, but the ratchet made the loss profile
worse by chopping the OTHER trades in this cohort that would have
extended back to TP after retrace-and-recover.

## §4 Why the higher-`activation_R` / higher-`lock_fraction` arms don't rescue

PROTOCOL §1 H2 anticipated a parsimony tie-break: if the winner-set was
non-empty, prefer higher `activation_R` (fires less) and higher
`lock_fraction` (locks more). The results show the trade-off is
monotone but NEVER crosses zero:

- Holding `lock_fraction` = 0.7 (tightest lock, banks most of MFE):
  a=1.0 gives ΔSharpe = −0.104; a=1.3 gives −0.103. Only ~0.001 gap.
- Holding `activation_R` = 1.3 (fires latest): l=0.4 gives −0.108;
  l=0.7 gives −0.103. Only ~0.005 gap.

The ratchet's incremental hurt is REMARKABLY UNIFORM across the grid.
This is diagnostic: it says the ratchet's fundamental interaction with
the deployed cell's BE + wick-proof + panic stops is the problem, not
the specific fire-point or lock ratio. Moving the ratchet later (higher
`a`) reduces how many trades it disturbs; moving the lock tighter
(higher `ℓ`) reduces the per-firing cost; but neither correction gets
close to zero net impact — because BE-at-1R already provides most of
the tail cap the ratchet could ever add on this cell.

## §5 Ex-post replay of the motivating GBPUSD trade

PROTOCOL §5.5 illustrates the anchor arm `(a=1.2, l=0.6)` on GBPUSD
ticket 2969136564 (the give-back that motivated the study). Under the
frozen rule, the ratchet would have banked **+47.5 pips ≈ +0.90 R**
instead of leaving the trade to give back 36.5 pips of MFE. That
n = 1 case-study snapshot is preserved in PROTOCOL §5.5 — but as
PROTOCOL §5.5 explicitly notes, this is descriptive-only and **cannot
rescue a losing pooled verdict**. The population-level finding is that
the same rule that would have saved this one trade would have chopped
many others: the pooled ΔSharpe is unambiguously negative even at that
arm.

`(a=1.2, l=0.6)` pooled ΔSharpe = **−0.108** with CI [−0.140, −0.077],
p = 0.0000, 0/5 folds positive.

## §6 What we DO NOT do (§6 stop rule)

Per PROTOCOL §6 and `PROTOCOL_DISCIPLINE.md` §5, the `dead` verdict
triggers explicit non-actions:

1. **Do not** extend the arm grid to search for a positive arm.
2. **Do not** promote a secondary metric (e.g. Δ tail-mean R = +1.00
   on the worst decile — a real effect but not the primary decision
   variable) to primary post hoc.
3. **Do not** ship any ratchet variant to the deployed cell.
4. **Do** keep the shipped `all_on` cell (wick-proof SL + BE-at-1R +
   PLG) as-is.
5. **Do** register a `STOP_NOTICE.md` in this directory that captures
   the specific mechanism (tail-cap gain dominated by runner-choke cost
   on this cell's TP=1.5R geometry).

## §7 What this DOES tell the campaign

E020 has just given the exit-management campaign a cheap, honest,
population-level negative result. That has three downstream implications:

1. **E023 (post-BE structure trail)** is pre-registered as "deferred
   until E020 verdict lands" (see EXPERIMENTS.md campaign group note).
   The dead verdict on E020's MFE-based tightening means a *structure-*
   based post-BE trail (E023) is now the natural next question if we
   still want to solve the give-back problem. E023 is unblocked but
   should be run only with the same disciplined pre-registration.
2. **E024 (near-TP stall exit)** is a different mechanism: it fires
   only when price stalls near TP for long enough that the arm is
   effectively booking a nearly-realised win. That is a much narrower
   trigger than E020's continuous MFE-tightening and does not share
   the runner-choke pathology. E024 remains worth running.
3. **E021 (partial exit at 1R)** faces a similar objection to E020 —
   it fires on the same "1R banked" event that E020's a=1.0 arms hinge
   on. E021 should be evaluated with awareness that E020's a=1.0
   arms have already failed on this cell; but E021 books only a
   *partial*, leaving the runner intact, so the pathology is
   structurally different.

## §8 Reproducibility

```bash
cd finance-research-experiments
PYTHONPATH=../multi-pair-trading-agent:.:scripts \
    ../multi-pair-trading-agent/.venv/bin/python \
    programs/E020/run_e020_validation.py \
    --output programs/E020/results.json
```

Wall-clock 9 seconds. Deterministic (bootstrap seed 42). Reproducing
requires PRE-0 path ledgers under
`programs/_shared/counterfactual_replay/data/` (regenerable via the
exporter — see `programs/_shared/counterfactual_replay/README.md`).

Full numeric detail (per-fold ΔSharpe with CIs, guardrails, mechanism
diagnostics, BH-FDR flags, per-arm verdicts) is in
[`programs/E020/results.json`](../../programs/E020/results.json).
