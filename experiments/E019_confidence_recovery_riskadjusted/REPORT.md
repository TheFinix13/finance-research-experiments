# E019 — Risk-adjusted confidence recovery (redesign of the parked E017)

**Date:** 2026-07-14 · **Protocol:** [`PROTOCOL.md`](PROTOCOL.md) · **Status:** `dead` / STOP (Phase 3 blocked).
**Verdict artefact:** [`results.json`](results.json) · **Stop notice:** [`STOP_NOTICE.md`](STOP_NOTICE.md).
**Harness:** [`../../programs/E019/`](../../programs/E019/) (`confidence_sim.py`, `run_e019_validation.py`, `tests/`).

## Abstract

E017 scored a graduated-confidence risk overlay on **raw terminal equity** — a
level metric that structurally rewards staying maximally deployed — and returned
an honest `parked_capital_cost` negative. E019 re-registered the study around a
**risk-adjusted** primary metric (CDaR-adjusted return `RaC_β = AnnRet / CDaR_β`,
β = 0.95), re-baselined it against the **shipped auto-clearing kill switch (AK)**
rather than E017's 48 h-blind hard-kill, and redesigned the recovery function to
re-arm confidence in proportion to *demonstrated risk-adjusted progress*
(`R-riskadj`) or a *risk-constrained-Kelly fraction* (`R-kelly`). A vectorised
Monte-Carlo panel (N = 10,000 paths, 11,000-day horizon, two DGPs × two
correlation settings = six cells, 12 arm-configs vs AK) shows that **no frozen
configuration beats AK on `RaC_β` in any cell**: median GR-S `RaC_β` ≈ **0.03–0.10**
against AK's **≈ 11.6–15.5** on the positive-edge generators. The mechanism does
what a brake should — it cuts worst-path drawdown (**0.09 vs 0.36**), CDaR
(**0.027 vs 0.097**) and, in the zero-edge regime, risk-of-ruin (**0.0 vs 0.38**)
— but its *annualised return numerator collapses to ≈ 0.2 %/yr* because the equity
gauge suppresses real exposure whenever equity sits off its peak, so
return-per-drawdown is also ≈ 0. The single pre-registered primary therefore
ranks AK strictly above every overlay. Guardrails (DD/ruin/time-to-resume), the
no-IPC gauge-convergence check, and the 2026-07-08 replay all pass; H2 shows
shadow recovery adds nothing over time decay; BH-FDR rejects no null and the
deflated statistic is negative. **Verdict: `dead` — keep the shipped AK
auto-clear; Phase 3 does not proceed.**

## 1. Introduction

### 1.1 Motivation and the E017 post-mortem

E017 ([`../E017_confidence_gated_cooldown/`](../E017_confidence_gated_cooldown/))
established that a continuous, loss-scaled confidence overlay eliminates blind
dead time (median 0 h vs 6,500 h) and crushes drawdown (2.5 % vs 16.9 %), yet
**failed its Pareto gate on one leg only — median terminal equity** — because a
de-risked/shadow-heavy arm forgoes the compounding that a fully-deployed baseline
captures under a positive-edge ledger. E017's methodological error was scoring a
*risk* mechanism on a *level* metric (`chekhlov2005drawdown`, `busseti2016kelly`):
ranking a brake by how fast the car goes.

### 1.2 What E019 changed (pre-registered, frozen)

1. **Primary metric → `RaC_β = AnnRet / CDaR_β` (β = 0.95).** Return per unit of
   *tail* drawdown; scale-free in the level of return, so a flat-but-safe curve
   *can* win if its denominator shrinks faster than its numerator.
2. **Baseline → AK**, mirroring the daily-DD auto-clear shipped in
   `multi-pair-trading-agent` on 2026-07-14: a clean daily-DD kill auto-clears at
   the next UTC rollover, manual/non-DD halts stay sticky, and a thrash guard
   escalates to a sticky halt after 3 consecutive DD-halt days.
3. **Recovery function → tied to the scored objective.** `R-riskadj` re-arms
   `c_s` in proportion to a demonstrated return-per-drawdown score `Ŝ_s`;
   `R-kelly` re-arms in proportion to a risk-constrained-Kelly fraction `f*_s`.

### 1.3 Contributions

1. A reproducible, **path-vectorised** MC harness (`programs/E019/`) that
   re-scores the E017 overlay on `RaC_β` and re-baselines it against AK,
   single-process (no `ProcessPoolExecutor` sandbox failure).
2. A pre-registered, literature-grounded redesign of the recovery law.
3. An honest **`dead`/STOP** verdict with the deeper diagnosis that the failure
   is *not* the metric choice (E017's hypothesis) but the **gauge suppressing
   compounding**, which drives the risk-adjusted numerator to ≈ 0.

## 2. Background

Drawdown-constrained exposure rules scale risk smoothly rather than switching off
(`grossman1993drawdowns`; discrete-time caveat `klass2005grossmanzhou`).
Risk-constrained Kelly trades growth for drawdown probability with a single
risk-aversion parameter (`busseti2016kelly`, `kelly1956`). CDaR penalises
sustained underwater periods, is coherent, and grounds both the primary metric
and the G-cdar gauge (`chekhlov2005drawdown`). Drawdown- and volatility-ratio
evaluation of risk rules is standard (Calmar / drawdown ratio: `young1991`,
`magdon2004maximumdrawdown` — *to add*; Sharpe: `sharpe1966`/`sharpe1994` — *to
add*). Multiplicity and overfitting hygiene follow `benjamini1995controlling`,
`harvey2016cross`, `bailey2016pbo`, `bailey2014deflated`; the negative-reporting
ethos follows `nosek2018preregistration`.

## 3. Methodology

Frozen per PROTOCOL §4–§6. Three arms on identical simulated trade streams:

| Arm | Behaviour |
|---|---|
| **AK** (baseline) | 3 % daily-DD breach → protective close + halt rest of day, **auto-clears at UTC rollover**; catastrophic/non-DD → sticky 48 h; 3 consecutive DD-halt days → sticky escalation. |
| **GR-S** | Same protective close; keep evaluating; suspend real orders while κ < τ_live = 0.30; **shadow-demonstrated** recovery raises `c_s` via `R-riskadj`/`R-kelly`; taper real risk by κ until κ ≥ τ_full = 0.80. |
| **GR-T** | As GR-S but recovery is **time-decay only** (+0.06/day, capped at 0.75 < τ_full), shadow ledger disabled — the H2 control. |

**Effective confidence** κ = c_s · g, gauge g ∈ {G-surplus, G-cdar}, floors
C_min = 0.15, g_min = 0.25 (all carried unchanged from E017 §3).

**Frozen grid.** PROTOCOL §4 frames "recovery × gauge = 4 configs / 8
arm-configs" while §5 freezes `S_target ∈ {1.0, 2.0}`. Dropping a frozen
parameter value would itself breach discipline, so we ran the **full frozen set**
— `{R-riskadj(S=1.0), R-riskadj(S=2.0), R-kelly} × {G-surplus, G-cdar}` = **6
configs × {GR-S, GR-T} = 12 arm-configs** — and set the FDR family size to the
true count (6 GR-S configs). Running *more* candidates is strictly conservative
for the "at least one alive" gate.

**Panel.** N = 10,000 paths; 11,000-day horizon; two DGPs — (a) bootstrap of the
E013 production ledger (`trade_ledger_EURUSD_H4.json`, 737 trades, hit-rate
0.5577, mean R 0.382) and (b) synthetic Bernoulli p_win ∈ {0.40, 0.55},
R_win = +1.5, R_loss = −1.0 — × cross-symbol correlation ρ ∈ {0.0, 0.5} =
**six cells**. Seed 42; 5,000 bootstrap resamples. Cross-symbol correlation is
induced by a Gaussian copula (logistic-CDF approximation, scipy-free). CDaR is
computed per path from an underwater histogram (1,000 bins); the G-cdar rolling
gauge refreshes every 5 days over a 250-day window.

## 4. Implementation

`programs/E019/confidence_sim.py` — vectorised (numpy, all N paths at once)
simulator, `RaC_β`/CDaR/Calmar/Sharpe metric primitives, the `R-riskadj`/`R-kelly`
recovery laws, gauge functions, bootstrap CI, BH-FDR, PBO and deflated-statistic
routines. `programs/E019/run_e019_validation.py` — cell loop (optional process
pool, which works outside the sandbox), gate evaluation, verdict classifier,
`results.json` writer. `programs/E019/tests/test_confidence_sim.py` — **16**
unit tests (metric correctness, arm behaviour, recovery monotonicity,
determinism/seed, statistics helpers). Full grid ran single-machine in **1,189 s**
(8 workers).

## 5. Results

### 5.1 Primary metric — `RaC_β` (N = 10,000, seed 42)

**Table 1. Best GR-S config vs AK per cell (median `RaC_β`).**

| Cell | AK `RaC_β` | best GR-S `RaC_β` | GR-S AnnRet | AK AnnRet | GR-S CDaR | AK CDaR | primary win? |
|---|---:|---:|---:|---:|---:|---:|:--:|
| bootstrap, ρ=0.0 | **12.93** | 0.063 | 0.0017 | 1.265 | 0.028 | 0.097 | ✗ |
| bootstrap, ρ=0.5 | **11.59** | 0.055 | 0.0016 | 1.255 | 0.029 | 0.108 | ✗ |
| synthetic p=0.40, ρ=0.0 | 0.012 | −0.012 | −0.0003 | 0.0072 | 0.027 | 0.563 | ✗ |
| synthetic p=0.40, ρ=0.5 | 0.005 | −0.012 | −0.0003 | 0.0031 | 0.027 | 0.578 | ✗ |
| synthetic p=0.55, ρ=0.0 | **15.46** | 0.099 | 0.0026 | 1.248 | 0.026 | 0.081 | ✗ |
| synthetic p=0.55, ρ=0.5 | **14.17** | 0.082 | 0.0022 | 1.244 | 0.027 | 0.088 | ✗ |

The pre-registered gate requires the GR-S bootstrap-95 % CI **lower bound** to
exceed the AK **point estimate** in **all** cells for at least one config.
**Every one of the 6 configs loses the primary in all 6 cells** (36/36
per-cell `primary_win = False`). The bootstrap one-sided superiority p-value is
**1.000** for every config in every cell.

**Diagnosis (the decisive finding).** GR-S's `RaC_β` is small not because its
denominator is large — its CDaR (0.026–0.029) is **~3.5× smaller** than AK's on
the positive-edge generators — but because its **numerator collapses**: median
annualised return is ≈ **0.17–0.26 %/yr** versus AK's ≈ **125 %/yr**. The equity
gauge forces κ = c_s·g below τ_full whenever equity is off its running peak
(G-surplus reaches 0.80 only within ~0.6 % of the peak), so GR spends almost its
entire life in tapered/shadow mode and **never compounds**. A return-per-drawdown
ratio with a ≈ 0 numerator cannot beat a compounding baseline no matter how small
the denominator — E017's terminal-equity failure re-appears one level up.

### 5.2 Capital-preservation & operational guardrails

GR-S **passes** all guardrails — it is unambiguously the *safer* arm:

| Metric | AK (bootstrap ρ=0) | best GR-S | AK (synthetic p=0.40 ρ=0.5) | GR-S |
|---|---:|---:|---:|---:|
| worst-path max drawdown | 0.355 | **0.089** | 0.907 | **0.079** |
| risk-of-ruin | 0.000 | 0.000 | **0.413** | **0.000** |
| median time-to-resume (h) | 12 | **0** | 12 | **0** |
| median dead hours | >0 (rest-of-day halts) | **0** | — | **0** |

In the zero-edge regime AK suffers **38–41 % risk-of-ruin** and ~0.91 worst
drawdown while GR-S never ruins. But guardrails are pass/fail floors, **not** the
decision variable; the single pre-registered primary (`RaC_β`) governs, and it
ranks AK above GR-S. Promoting the safety story to primary post hoc is exactly
the anti-cherry-pick behaviour PROTOCOL §7 forbids.

### 5.3 H2 — shadow vs time-decay recovery

On the headline cell, GR-S and GR-T are indistinguishable on `RaC_β` (relative
difference ≤ 1.2 % for every config). `shadow_adds_value_any = false`: the
shadow-recovery machinery earns no keep even before the primary gate is applied.

### 5.4 Gauge convergence (§4a)

Max pairwise disagreement = **0.0** for all 6 configs (the gauge is a
deterministic function of the shared equity feed). **PASS.**

### 5.5 Multiplicity & overfitting (§7)

BH-FDR over the family of 6 GR-S configs rejects **no** null (worst-cell
p = 1.000 for all). PBO = **0.0** (no config is selected-and-overfit because none
wins). Deflated statistic: selected median `RaC_β` = 0.063 vs expected-max under
6 independent trials = 0.071 → deflated z = **−0.39** (the "best" config does not
even reach the null expectation of the maximum). All three concur with the raw
gate: nothing to select.

### 5.6 Incident replay 2026-07-08 (descriptive, n = 1)

| | HK (old, observed) | AK (shipped) | GR-S (replay) |
|---|---:|---:|---:|
| dead time | 50.9 h | ~12 h (auto-clears at rollover) | 0 h |
| protective close preserved | yes | yes | yes |
| re-opened before protective intent | — | — | no |

GR-S preserves the protective close and removes the blind window descriptively —
but this is illustrative, not an FDR-family claim, and cannot rescue the primary.

## 6. Discussion

E019 falsifies its own animating hypothesis. E017 argued the overlay lost only
because terminal equity is the wrong yardstick for a brake; E019 built the *right*
yardstick (`RaC_β`) and the overlay **still loses — decisively and in every
cell** — because the equity gauge drives the *return* component of the
risk-adjusted ratio to ≈ 0. The problem was never purely the metric; it is that
the confidence×gauge architecture keeps the agent de-risked so persistently that
it forgoes essentially all compounding. Under a positive-edge ledger a ratio
`(≈0)/(small)` cannot beat `(large)/(moderate)`.

**`dead` vs `parked_baseline_sufficient`.** Operationally both mean "keep AK,
ship nothing." The pre-registered labels differ: `parked_baseline_sufficient`
(H3) is reserved for a *statistical tie* AK ≈ GR-S. Here GR-S is far **worse** on
the primary (rel_diff ≈ −0.99 in the headline cell), which is literally the §6
`dead`/STOP condition ("GR-S does not beat AK on `RaC_β`"). We therefore report
`dead` as the frozen gate returns, while noting the practical decision — the
cheap shipped auto-clear is enough — coincides with the spirit of H3.

**A defensible reframe would need a fresh pre-registration.** The overlay is a
genuine *risk reducer* (lower DD, lower CDaR, zero ruin in the losing regime). A
future study could pre-register a **loss-regime-conditioned** objective (where
capital preservation dominates and AK's 38–41 % ruin is the headline), or relax
the gauge so real exposure resumes nearer the peak (higher τ_live headroom / a
less peak-sensitive gauge) so the overlay can compound. Neither is a post-freeze
retune of E019 — both require a new study id.

**Limitations.** Day-driven trade arrival; single shared R-distribution across
symbols; Gaussian-copula correlation via a logistic-CDF approximation; CDaR
histogram-quantised to 0.1 %; the recovery `Ŝ_s` uses the running max-drawdown of
the post-anchor cumulative-R curve (a Calmar-style drawdown functional) rather
than the full tail-mean CDaR, disclosed here as a vectorisation-friendly
operationalization of "CDaR-adjusted return over the post-halt window." None of
these bear on the direction of the result: GR's ≈ 0 %/yr return is structural.

## 7. Conclusion

**E019 verdict: `dead` / STOP.** No frozen configuration beats the shipped AK
auto-clear on the pre-registered primary `RaC_β` in any DGP × correlation cell;
shadow recovery adds no value over time decay (H2); the gauge-convergence check
passes; multiplicity and deflation confirm there is nothing to select. The
graduated overlay is *safer* but does not deliver superior risk-adjusted returns,
because the equity gauge suppresses compounding and collapses the risk-adjusted
numerator. **Phase 3 production wiring does not proceed.** The 2026-07-14 daily-DD
auto-clear remains the production risk overlay. A new study id (E020+) with a
fresh pre-registration is required for any further attempt — see
[`STOP_NOTICE.md`](STOP_NOTICE.md).

## References

Existing in [`../../reviews/refs.bib`](../../reviews/refs.bib):
`chekhlov2005drawdown`, `busseti2016kelly`, `kelly1956`, `grossman1993drawdowns`,
`klass2005grossmanzhou`, `maillard2010erc`, `chen2024darkside`,
`subrahmanyam1994circuit`, `bailey2016pbo`, `bailey2014deflated`,
`benjamini1995controlling`, `harvey2016cross`, `nosek2018preregistration`,
`chan2009quantitative`.

**To add before archival (flagged for the coordinator — not edited here to avoid
a concurrent-write race on the shared bib):** a Sharpe source
(`sharpe1966`/`sharpe1994`) and a Calmar / maximum-drawdown-ratio source
(`young1991` and/or `magdon2004maximumdrawdown`), backing the §3.3 secondary
metrics. The primary (`RaC_β`) is already covered by `chekhlov2005drawdown`.
