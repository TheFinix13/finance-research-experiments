# Phi4 squad gate -- 4-agent MVP -- addendum under locked verdict-comparator registry

**Addendum date:** 2026-06-24

**Addendum author:** verdict-comparator-discipline worker.

**Original report (preserved, not modified):** `reviews/phi4_squad_v1.md`.

**Binding rule applied:** `docs/methodology/gate_verdict_registry.md`
v0.1 + `07-research-standards.md` §11 (verdict-comparator discipline).

---

## Context — why an addendum

The verdict-comparator registry (`docs/methodology/gate_verdict_
registry.md` v0.1) locks the aggregating statistic for each phase gate
**before** any evaluation under that gate runs. The Φ4 v1 squad gate
report (preserved as-is at `reviews/phi4_squad_v1.md`) was decided on
**median-of-OOS-window mean-TQS**, but until the registry landed there
was no binding rule that this was *the* statistic. A reviewer could in
principle have substituted a different aggregator (pooled per-trade
mean TQS, mean of window means, …) and reported a different verdict.

This addendum re-checks the Φ4 FAIL under the registry-locked rule, and
publishes the cross-statistic diagnostic table so the verdict's
**sensitivity to the statistic choice** is visible. The original
report is preserved in place per the registry's amendment procedure (no
in-place rewrites of sealed reviews).

## Statistic used in the original report

The Φ4 v1 report decided the verdict on this line of its **Squad TQS
vs Isagi-alone** table:

> `| Median OOS-window mean TQS (F12) | **0.311** | 0.317 | **0.98×** |`
> (`reviews/phi4_squad_v1.md`, "Squad TQS vs Isagi-alone").

And the verdict line:

> "squad TQS 0.311 is 0.98× Isagi-alone (0.317) — adding agents LOST
> edge; reported honestly."

I.e. the Φ4 worker decided the FAIL on **median across OOS windows of
per-window mean TQS (F12)**, comparator Isagi-alone Φ3 baseline 0.317,
threshold ≥ 1.10× for PASS.

## Newly-locked statistic for this gate

Per `docs/methodology/gate_verdict_registry.md` v0.1, the registry row
for this gate is:

| Gate ID | Locked statistic | Comparator | PARTIAL band | PASS band |
|---|---|---|---|---|
| **G5-squad** (Φ4 → Φ5, 4-agent MVP squad vs Isagi-alone) | Median across OOS windows of per-window mean TQS (F12) for the squad's fused trade stream | Isagi-alone Φ3 baseline (`reviews/phi3_gate_isagi_v1.md` median 0.317) | ratio 1.00 ≤ r < 1.10 | ratio r ≥ 1.10 |

This is **identical** to the statistic the Φ4 worker used. The Φ4 v1
report decided the verdict under the very statistic that the registry
later locked, so the registry endorses the original choice; no swap is
required.

(The registry also defines a sibling gate **G5-alone** — Isagi-alone vs
Sae — which is the strict reading of `09-experiment-architecture.md`
§1.5's G5 row. G5-squad is the gate the Φ4 v1 report actually ran
under the `09` §1.5 + §2 MVP allowance. Both rows are in the registry;
this addendum is about G5-squad. G5-alone is not yet evaluated; it
requires the F16 Sae composite baseline to land, which is parked behind
the Φ4 carryovers in `ai_context.md`.)

## Verdict under the locked rule

Recomputed from `reviews/phi4_squad_v1_trades.jsonl` for transparency
(numbers match the original report's walk-forward table; the trade
journal is the same one the original report rolled up):

| OOS year | Squad n | Squad mean pips | Squad mean TQS |
|---|---|---|---|
| 2019 | 157 | +8.88 | 0.3381 |
| 2020 | 195 | +2.52 | 0.3111 |
| 2021 | 182 | +5.38 | 0.3046 |
| 2022 | 217 | +2.18 | 0.3066 |
| 2023 | 184 | +4.03 | 0.3485 |
| 2024 | 132 | +4.42 | 0.3332 |
| 2025 | 132 | +16.13 | 0.3104 |

Squad window-mean-TQS sorted: `[0.3046, 0.3066, 0.3104, 0.3111, 0.3332,
0.3381, 0.3485]`. **Median = 0.3111.**

Isagi-alone Φ3 baseline (from `reviews/phi3_gate_isagi_v1.md` table):
**Median = 0.3175** across windows `[0.294, 0.308, 0.317, 0.317, 0.327,
0.369, 0.392]`.

Ratio = 0.3111 / 0.3175 = **0.98×**.

Ratio = 0.98 < 1.00 → **FAIL** (per registry: ratio < 1.00 means the
squad *lost* edge; PARTIAL requires positive lift 1.00 ≤ r < 1.10;
PASS requires r ≥ 1.10).

## Cross-statistic diagnostic (journalled, not scored)

This is the table the original Φ4 report did not publish. It shows
**how sensitive the Φ4 verdict is to the choice of aggregator**.

Computed from `reviews/phi4_squad_v1_trades.jsonl` (squad: all 2 006
trades on EURUSD + USDCAD) and `reviews/phi3_gate_isagi_v1_trades.jsonl`
(Isagi-alone: 856 EURUSD trades). Both files are pure JSONL trade
journals; numbers reproducible by a one-shot read.

| Candidate statistic | Squad (Φ4) | Isagi-alone (Φ3) | Ratio | Verdict if this were locked |
|---|---|---|---|---|
| **Median OOS-window mean-TQS** *(locked statistic)* | **0.3111** | **0.3175** | **0.98×** | **FAIL** |
| Mean OOS-window mean-TQS | 0.3218 | 0.3320 | 0.97× | FAIL |
| Pooled per-trade mean TQS | 0.3172 | 0.3150 | 1.007× | PARTIAL (positive lift, below 1.10× PASS) |
| Pooled per-trade median TQS | 0.0000 | 0.0000 | n/a | undefined (structural zero at RR 1.5 per F12) |
| Median OOS-window mean-pips | +4.42 | +11.04 | 0.40× | FAIL |
| Mean OOS-window mean-pips | +6.22 | +9.87 | 0.63× | FAIL |
| Pooled per-trade mean pips | +8.29 | +6.28 | 1.32× | (would be PASS under pips — but pips is forbidden as a scoring metric per `09` §1.4) |
| Pooled per-trade trimmed mean pips (10 %) | +4.57 | +3.77 | 1.21× | (forbidden as locked: cumulative-pips family) |
| Pooled per-trade winsorized mean pips (5 / 95) | +7.04 | +5.86 | 1.20× | (forbidden as locked) |
| Cumulative pips | +16 637 | +5 380 | 3.09× | **forbidden** as locked per `09` §1.4 |
| Hit rate | 49.30 % | 48.60 % | +0.7 pp | guardrail only |

**Three observations the original report could not state without this
table.**

1. **The FAIL is robust across every TQS-family aggregator that the
   architecture permits.** Median-of-window-means, mean-of-window-means,
   and pooled-mean all keep the squad at or below 1.007× — never near
   the 1.10× PASS band. The locked-statistic choice did not flatter
   nor punish the result; it landed where every reasonable TQS-aggregator
   landed.
2. **Pooled per-trade mean TQS reports a *positive* lift (1.007×), but
   only PARTIAL territory.** This is the subtle case the registry was
   built for. Without a locked rule, a future worker could legitimately
   re-tell the Φ4 result as "PARTIAL — squad delivered a small positive
   TQS lift over Isagi-alone, but below the 1.10× PASS threshold."
   Under the registry's locked statistic (median-of-window-means), that
   reading is disallowed: the gate is decided by 0.98×, which is FAIL.
   The 1.007× pooled-mean reading does not vanish — it is published
   here as a diagnostic — but it cannot decide the gate.
3. **Pips-based statistics tell a very different story.** Pooled mean
   pips (1.32×), trimmed mean pips (1.21×), winsorized mean pips (1.20×),
   and cumulative pips (3.09×) all show the squad winning by a wide
   margin. The architecture spec `09` §1.4 forbids using pips-family
   statistics as the scoring metric ("No configuration may be promoted
   because it 'made more money' on a sealed panel if TQS did not
   improve"). This is the cleanest empirical demonstration the program
   has of *why* that rule exists: the squad makes 3× more cumulative
   pips than Isagi-alone, but every TQS-family statistic says the
   trades are no better per unit of risk and quality. The registry's
   refusal to allow cumulative pips as a scoring metric is what
   prevents the squad from being promoted on the wrong evidence.

**Barou's mean-positive / median-negative property is now visible.** In
the cross-statistic table, Barou's signature is in the difference
between *pooled mean pips* (Squad +8.29 vs Isagi-alone +6.28 → Barou's
fat right tail boosts the squad mean) and *pooled median pips* (Squad
−9.59 vs Isagi-alone −11.28 → Barou's median is slightly less negative
than Isagi-alone's by absolute value, but both are deeply below the
profit threshold because target_rr = 1.5 means most trades hit SL by
design). The TQS aggregator collapses both behaviours to ≈ 0.317 because
F12's R^0.7 concavity caps the right tail and the structural zero on
losses removes the median's distinguishing power. **This is the design
intent of TQS, not a defect** — the locked statistic does its job.

## Per-agent KPIs (unchanged, recomputed for transparency)

Reproducing the original report's per-agent table from the same JSONL,
plus the trimmed and winsorized rows for completeness:

| Agent | Trades | Mean pips | Median pips | Mean TQS | Trimmed mean (10 %) | Winsorized (5 / 95) | Hit % |
|---|---|---|---|---|---|---|---|
| `isagi_yoichi` | 856 | +6.29 | −11.28 | 0.3150 | +3.77 | +5.86 | 48.60 % |
| `barou_shoei` | 1 150 | +9.79 | −7.28 | 0.3189 | +5.19 | +8.24 | 49.83 % |
| `nagi_seishiro` | 0 | — | — | — | — | — | — |
| `kunigami_rensuke` | 0 | — | — | — | — | — | — |

The Nagi-starved / Kunigami-silent rows are unchanged from the original
report and explained in its **Diagnosis** section (Nagi predicate-
starved by the 2-distinct-peer floor; Kunigami's 3-of-5 loss-streak
predicate never tripped). The locked-statistic re-check does not change
those findings.

## Final restated verdict under the locked rule

**Phi4 → Phi5 (G5-squad) MVP squad-vs-Isagi-alone gate: `FAIL`.**

The original Φ4 FAIL verdict holds verbatim under the registry's locked
rule. The locked statistic equals the statistic the original worker
used; the numbers do not change; the verdict does not change.

Additional honesty surfaced by the locked-rule re-check (this is the
addendum's main *new* contribution beyond the original report):

- The FAIL is **robust across every TQS-family aggregator** (median-of-
  window-means, mean-of-window-means, pooled-mean) at or below 1.007×.
  The closest the squad gets to a non-FAIL reading is pooled-per-trade
  mean TQS = 1.007×, which is PARTIAL but still below the PASS band.
- The FAIL is **fragile to the choice of metric family**: every pips-
  family statistic shows the squad winning by 1.20×–3.09×, and the
  architecture spec `09` §1.4 explicitly forbids using pips as a
  scoring metric. This is the empirical demonstration the program now
  has of why `09` §1.4 exists; the registry's refusal to allow pips as
  a locked statistic at G5-squad is what keeps the FAIL from being
  silently relabelled.
- The original report's `phi4_squad_v1.md` Diagnosis section identifies
  three failure modes (Nagi predicate-starved, Barou median-dilutes,
  highest-conviction-wins suppresses Isagi). The locked-rule re-check
  endorses all three diagnoses and adds a fourth, methodological one:
  **the TQS aggregator does its job here precisely by refusing to
  reward cumulative-pips growth that is not matched by per-trade
  quality growth**. Squad cumulative pips +16 637 vs Isagi-alone
  +5 380 (3.09×) would have been a PASS under raw P&L; locked TQS says
  FAIL because the per-trade quality did not move.

## References

- Original Φ4 report: `reviews/phi4_squad_v1.md`
- Per-trade journal (squad): `reviews/phi4_squad_v1_trades.jsonl`
- Per-trade journal (Isagi-alone Φ3 baseline): `reviews/phi3_gate_isagi_v1_trades.jsonl`
- Companion rejection analysis: `reviews/phi4_isagi_rejection_analysis.md`
- Verdict-comparator registry: `docs/methodology/gate_verdict_registry.md`
- Research-standards binding rule: `07-research-standards.md` §11
- Architecture spec G5 / §1.4 (TQS-only optimisation): `09-experiment-architecture.md` §1.4, §1.5
- Charter C1: `00-charter.md` §7.1
- F12 (TQS): `04-quant-foundations.md`
