# Φ4.1 squad gate v1 -- cross-statistic robustness addendum

**Addendum date:** 2026-06-24.

**Addendum author:** Φ4.1 gate worker (post-verdict).

**Companion to:** `reviews/phi41_squad_v1.md` (auto-generated harness
verdict; canonical FAIL at 0.92×) and
`reviews/phi41_squad_v1_addendum.md` (hand-written interpretation: Nagi
predicate-starvation fixed; Isagi/Barou crowd-out is the new failure
mode).

**Why this exists.** The `07-research-standards.md` §11 verdict-
comparator discipline + the Φ4 precedent (`reviews/phi4_squad_v1_
addendum.md`) make a cross-statistic robustness table **mandatory** at
every G5-squad gate. The locked verdict statistic is
**median across OOS windows of per-window mean TQS (F12)**; this
addendum publishes how sensitive the Φ4.1 verdict is to the choice of
aggregator. The cross-statistic table is a *diagnostic*, not a verdict
input -- the registry forbids swapping mid-evaluation
(`docs/methodology/gate_verdict_registry.md` v0.1 + the Worked Example
2 in that doc shows the exact pattern this addendum follows).

The locked statistic and verdict are unchanged from the committed
`phi41_squad_v1.md` and `phi41_squad_v1_addendum.md`. This addendum
adds only the cross-statistic diagnostic table that those two docs do
not publish.

---

## Statistic used in the original report

The auto-generated `phi41_squad_v1.md` decides the verdict on this row
of its **Squad TQS vs Isagi-alone** table:

> `| Median OOS-window mean TQS (F12) | **0.292** | 0.317 | **0.92x** |`

And the verdict line:

> "squad TQS 0.292 is 0.92× Isagi-alone (0.317) -- expanding the
> roster did not close the gap; reported honestly."

I.e. the harness decided the FAIL on **median across OOS windows of
per-window mean TQS (F12)**, comparator Isagi-alone Φ3 baseline 0.317
(more precisely 0.3175 recomputed from
`reviews/phi3_gate_isagi_v1_trades.jsonl`), threshold ≥ 1.10× for PASS.

This is the **G5-squad locked statistic** per
`docs/methodology/gate_verdict_registry.md` v0.1. The harness's choice
matches the registry-locked rule exactly; no swap is required.

---

## Verdict under the locked rule (recomputed for transparency)

Computed exactly from `reviews/phi41_squad_v1_trades.jsonl` (squad,
3,714 trades on EURUSD + GBPUSD + USDCAD H4 2015-2025):

| OOS year | Squad n | Squad mean pips | Squad mean TQS |
|---|---|---|---|
| 2019 | 358 | +8.41 | 0.3176 |
| 2020 | 355 | +0.95 | 0.2922 |
| 2021 | 354 | +9.88 | 0.2999 |
| 2022 | 367 | +5.62 | 0.2735 |
| 2023 | 364 | +9.32 | 0.3166 |
| 2024 | 270 | +7.27 | 0.2865 |
| 2025 | 261 | +18.57 | 0.2831 |

Squad window-mean-TQS sorted: `[0.2735, 0.2831, 0.2865, 0.2922, 0.2999,
0.3166, 0.3176]`. **Median = 0.2922.**

Isagi-alone Φ3 baseline (from `reviews/phi3_gate_isagi_v1_trades.jsonl`,
recomputed): window means `[0.3690, 0.3168, 0.3175, 0.2939, 0.3271,
0.3920, 0.3075]`, sorted `[0.2939, 0.3075, 0.3168, 0.3175, 0.3271,
0.3690, 0.3920]`. **Median = 0.3175.**

Ratio = 0.2922 / 0.3175 = **0.9203×**.

0.9203 < 1.00 → **FAIL** (per registry: ratio < 1.00 means the squad
*lost* edge; PARTIAL requires 1.00 ≤ r < 1.10; PASS requires r ≥ 1.10).

---

## Cross-statistic diagnostic table (journalled, NOT scored)

This is the table neither the auto-report nor the hand-written
addendum publishes. It shows **how sensitive the Φ4.1 verdict is to
the choice of aggregator**, in the same format as
`reviews/phi4_squad_v1_addendum.md`.

Computed from `reviews/phi41_squad_v1_trades.jsonl` (squad: all 3,714
trades on EURUSD + GBPUSD + USDCAD) and
`reviews/phi3_gate_isagi_v1_trades.jsonl` (Isagi-alone: 856 EURUSD
trades). Both files are pure JSONL trade journals; numbers reproducible
by a one-shot read.

| Candidate statistic | Squad (Φ4.1) | Isagi-alone (Φ3) | Ratio | Verdict if this were locked |
|---|---|---|---|---|
| **Median OOS-window mean-TQS** *(locked statistic)* | **0.2922** | **0.3175** | **0.92×** | **FAIL** |
| Mean OOS-window mean-TQS | 0.2956 | 0.3320 | 0.89× | FAIL |
| Pooled per-trade mean TQS | 0.2955 | 0.3150 | 0.94× | FAIL |
| Pooled per-trade median TQS | 0.0000 | 0.0000 | n/a | undefined (structural zero at RR 1.5 per F12) |
| Median OOS-window mean-pips | +8.41 | +11.04 | 0.76× | FAIL |
| Mean OOS-window mean-pips | +8.57 | +9.87 | 0.87× | FAIL |
| Pooled per-trade mean pips | +9.49 | +6.28 | 1.51× | (would be PASS under pips — but pips is forbidden as a scoring metric per `09` §1.4) |
| Pooled per-trade median pips | -12.47 | -11.28 | n/a (structural negative at RR 1.5) | -- |
| Pooled per-trade trimmed mean pips (10 %) | +4.74 | +3.77 | 1.26× | (forbidden as locked: cumulative-pips family) |
| Pooled per-trade winsorized mean pips (5 / 95) | +8.22 | +5.86 | 1.40× | (forbidden as locked) |
| Cumulative pips | +35,264 | +5,380 | **6.56×** | **forbidden** as locked per `09` §1.4 |
| Hit rate | 48.12 % | 48.60 % | -0.48 pp | guardrail only (C1 § 7.1: must stay within −2 pp; ✓) |

---

## Four observations the existing reports could not state without this table

### 1. The FAIL is robust across every TQS-family aggregator

Median-of-window-means (0.92×), mean-of-window-means (0.89×), and
pooled-mean-per-trade (0.94×) all sit at or below 0.94×. The closest
the squad gets to a non-FAIL TQS reading is 0.94× pooled mean TQS,
which is still meaningfully below the 1.00× PARTIAL band. **No
TQS-family aggregator rescues this FAIL.** The locked-statistic
choice did not flatter nor punish the result; it landed where every
reasonable TQS-aggregator landed.

### 2. Φ4.1 is a *stronger* FAIL than Φ4 by every TQS-family aggregator

| Statistic | Φ4 ratio | Φ4.1 ratio | Delta |
|---|---|---|---|
| Median OOS-window mean-TQS *(locked)* | 0.98× | **0.92×** | −0.06× |
| Mean OOS-window mean-TQS | 0.97× | 0.89× | −0.08× |
| Pooled per-trade mean TQS | 1.007× *(PARTIAL)* | 0.94× | −0.07× |

The Φ4 addendum had to publish a curious split: the locked statistic
said FAIL (0.98×), but the pooled-per-trade-mean-TQS row showed a
*positive* lift (1.007×, in PARTIAL territory). The Φ4 addendum's
core argument was that the registry-locked rule was the right
authoritative reading and the 1.007× pooled-mean reading was a
diagnostic that could not promote the run. **Φ4.1 removes that
ambiguity entirely.** Every TQS-family statistic now agrees the squad
LOST edge. There is no "but pooled-mean shows positive lift" softening
available for Φ4.1.

This makes the registry's discipline easier to defend at Φ4.1 than at
Φ4: the cross-statistic table is internally consistent, not just
locked-by-fiat.

### 3. The pips-family disagreement is twice as wide as Φ4

| Statistic | Φ4 ratio | Φ4.1 ratio | Delta |
|---|---|---|---|
| Pooled per-trade mean pips | 1.32× | **1.51×** | +0.19× |
| Pooled per-trade winsorized mean pips (5/95) | 1.20× | 1.40× | +0.20× |
| Pooled per-trade trimmed mean pips (10 %) | 1.21× | 1.26× | +0.05× |
| Cumulative pips | 3.09× | **6.56×** | +3.47× |

If the gate were decided on **cumulative pips**, Φ4.1 would be a
runaway PASS at 6.56× the Isagi-alone Φ3 baseline. `09-experiment-
architecture.md` §1.4 explicitly forbids using cumulative-pips family
statistics as the scoring metric (*"No configuration may be promoted
because it 'made more money' on a sealed panel if TQS did not
improve"*).

**This is the cleanest empirical demonstration the program has of
*why* that rule exists.** The Φ4 addendum opened with a 3.09× ratio
under cumulative pips; Φ4.1 doubles it to 6.56× and the locked TQS
statistic STILL says FAIL. The verdict-comparator discipline is now
load-bearing: without the locked-statistic rule, the Φ4.1 squad would
look like a triumph (`+35,264` cumulative pips vs Isagi-alone's
`+5,380`). With the rule, it is honestly FAIL because per-trade
quality (TQS) did not move.

### 4. The "Bachira mean-positive / TQS-flat" property is now the dominant signal

Φ4 attributed the cross-statistic split to Barou's mean-positive /
median-negative property on USDCAD. Φ4.1 generalises it: Bachira
runs the same pattern across all 3 symbols, scaled up.

Bachira's per-trade behaviour (from
`reviews/phi41_squad_v1_trades.jsonl`):

| Symbol | n | Mean pips | Median pips | Mean TQS |
|---|---|---|---|---|
| EURUSD | 628 | +4.49 | -- | 0.318 |
| GBPUSD | 1,081 | +13.39 | -- | 0.308 |
| USDCAD | 1,131 | +9.75 | -- | 0.302 |
| **Squad (all agents)** | **3,714** | **+9.49** | **-12.47** | **0.2955** |

Bachira's EURUSD TQS (0.318) is statistically indistinguishable from
Isagi-alone's Φ3 baseline (0.3175). The squad's drag below 0.317 is
not coming from Bachira on EURUSD; it comes from (a) Bachira diluted
across the two new symbols GBPUSD/USDCAD (TQS 0.302-0.308 vs the
EURUSD-only Isagi reference) and (b) Chigiri (0.229) and Rin (0.277)
dragging the squad-wide mean. The F12 TQS metric's R^0.7 concavity
caps Bachira's right tail; Bachira's extra trades show up cleanly in
pips but not in TQS. **TQS does its job here precisely by refusing to
reward more-trades-with-equivalent-quality.**

---

## Final restated verdict under the locked rule

**Φ4.1 → Φ5 (G5-squad) expanded squad-vs-Isagi-alone gate: `FAIL`.**

The auto-report's FAIL verdict holds verbatim under the registry's
locked rule. The locked statistic equals the statistic the harness
used; the numbers do not change; the verdict does not change.

What this cross-statistic addendum adds beyond the existing
committed reports:

- The FAIL is **robust across every TQS-family aggregator** at
  0.89×-0.94× (Φ4: 0.97×-1.007×). Φ4.1 is a *stronger* FAIL than Φ4
  on every TQS-family statistic.
- The FAIL is **fragile to the choice of metric family**: cumulative
  pips ratio doubled from Φ4's 3.09× to Φ4.1's 6.56×, demonstrating
  more starkly than Φ4 why `09` §1.4 forbids pips-family scoring.
- The cross-statistic split is now internally consistent (no
  PARTIAL-under-pooled-mean-TQS escape hatch like Φ4 had), making
  the verdict-comparator discipline easier to defend.

The existing `phi41_squad_v1_addendum.md`'s prescription stands: the
Φ5 lever is the **aggregator** (HRP risk budget + TQS-conditional
conviction floor + same-direction merge), not more strikers. The
cross-statistic numbers here support that conclusion -- the pips-
family ratios show the squad already makes plenty of edge in absolute
terms; what is missing is the per-trade quality lift that the
aggregator's equal-weight-by-conviction selection cannot deliver.

---

## References

- Auto-generated verdict: `reviews/phi41_squad_v1.md`
- Hand-written interpretation: `reviews/phi41_squad_v1_addendum.md`
- Per-trade ledger (squad Φ4.1): `reviews/phi41_squad_v1_trades.jsonl`
- Per-trade ledger (Isagi-alone Φ3 baseline):
  `reviews/phi3_gate_isagi_v1_trades.jsonl`
- Φ4 cross-statistic precedent:
  `reviews/phi4_squad_v1_addendum.md`
- Verdict-comparator registry (G5-squad row):
  `docs/methodology/gate_verdict_registry.md` v0.1 (commit `aaa5ed1`)
- Research-standards binding rule: `07-research-standards.md` §11
- Architecture spec (TQS-only optimisation, pips forbidden):
  `09-experiment-architecture.md` §1.4, §1.5
- Charter C1 (hit-rate guardrail): `00-charter.md` §7.1
- F12 (TQS): `04-quant-foundations.md`
