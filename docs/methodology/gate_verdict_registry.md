# Methodology: gate-verdict comparator registry

**Status:** `BINDING v0.1` — 2026-06-24.

> **Naming note.** There is already a `docs/methodology/verdict_registry.md`
> in this repo — that one is the lab's **four-tier outcome registry**
> (`alive` / `parked_weak_effect` / `parked_insufficient_n` / `dead`) and
> classifies the *result* of a stage-FDR run on a single cell. **This**
> file is a different object: it locks, per phase gate, **which summary
> statistic decides the PASS / PARTIAL / FAIL verdict** at that gate.
> The two registries are complementary — the outcome registry labels
> what a cell *is*, this registry pins how a gate *decides*.

## Purpose

Two evaluations have landed under M001 — Φ3 (A1 Isagi wrapper PASS,
`reviews/phi3_gate_isagi_v1.md`) and Φ4 (4-agent squad gate FAIL,
`reviews/phi4_squad_v1.md`) — and each used a *different* aggregating
statistic. Φ3 was decided on **median across OOS windows of per-window
mean per-trade pips**; Φ4 was decided on **median across OOS windows of
per-window mean TQS (F12)**. Both choices were defensible in isolation,
but the choice happened **inside the evaluation worker**, not before it.
That is the textbook post-hoc-statistic risk: a future worker could pick
the metric that flatters the result and the verdict would still look
clean.

The Φ3 worker was initially confused about whether the comparator was
the *median across windows* or the *median of pooled trades*; the
verdict only resolved once the comparator was clarified by hand against
E004. The Φ4 worker correctly used median-of-OOS-window mean-TQS, but
that statistic *hides* a non-trivial property of one of the new agents
(Barou is mean-positive on pips and on TQS, but median-negative on
pips). Without a locked rule, a future worker could legitimately retell
the same data under "pooled per-trade mean TQS" (squad 0.317 vs
Isagi-alone 0.315 → 1.007×, a *positive* lift) and the FAIL would
quietly soften.

This registry exists to remove that degree of freedom. **Every gate
declares its locked statistic, its comparator, and its PARTIAL / PASS
thresholds before any evaluation under that gate is run.** Statistics
chosen post-hoc are disallowed (see `07-research-standards.md` §11).

---

## Glossary of candidate aggregating statistics

Every statistic listed here is a *real* candidate that has been
considered at some gate. The "tradeoff" column is the honest reason a
gate would or would not pick it.

| Statistic | One-line definition | Tradeoff (why pick / why not) |
|---|---|---|
| **Median of OOS-window mean-TQS** | For each rolling OOS window, compute the mean TQS (F12) across trades in that window; take the median of those window-level means across windows. | **+** Robust to one fat-tailed window dominating the headline. Matches `09-experiment-architecture.md` §1.5's framing of TQS as the primary scoring metric. **−** Hides per-trade behaviour of fat-right-tail agents (e.g. Barou: pools median-negative trades into window means that the median-across-windows then smooths over). |
| **Mean of OOS-window mean-TQS** | As above but take the mean (not median) across windows. | **+** Treats every OOS year equally, even outlier years. **−** A single 5σ year (e.g. 2025 +16.13 squad-pips) skews the headline; the OOS sample is too small (7 windows) for the central-limit assumption to hold. |
| **Per-trade mean TQS (pooled)** | Compute mean TQS across **all** OOS trades regardless of window. | **+** Maximum statistical power (n in the thousands, not 7). Honest about trade-level distribution. **−** Treats a 2019 trade and a 2025 trade as exchangeable, which assumes regime-stationarity that FX does not honour. Hides per-year behaviour entirely. |
| **Per-trade median TQS (pooled)** | Median TQS across all OOS trades. | **+** Robust to right tails. **−** At target-RR 1.5 with ~49 % hit rate, the per-trade median TQS is structurally **0.000** for these zone strategies (loss trades score 0 by F12 design). The statistic carries zero information for any RR > 1 strategy. Documented in `04-quant-foundations.md` F12. |
| **Per-trade trimmed mean (10 % trimmed)** | Pooled mean after dropping top and bottom 10 % of trades. | **+** Robust to outliers without being uninformative. **−** The 10 % cut is a parameter; not standardised across the repo. Used as a *cross-check*, not a primary statistic. |
| **Per-trade winsorized mean** | Pooled mean after clipping the top and bottom 5 % to the 5th / 95th percentile values. | **+** Similar to trimmed mean but keeps the count. **−** Same param-choice debt. Used as a cross-check only. |
| **Cumulative P&L (pips)** | Sum of `pnl_pips` across all OOS trades. | **+** Speaks the language of capital. **−** Explicitly **forbidden** as a scoring metric by `09-experiment-architecture.md` §1.4: "No configuration may be promoted because it 'made more money' on a sealed panel if TQS did not improve." Reported in journal for sanity only. |
| **Sharpe ratio (deflated; F6)** | Bailey-LdP DSR of trade-level returns. | **+** Portfolio-level industry standard. **−** Requires n_trades ≥ 30 per arm (F6 failure mode). Allocator-level metric, not a per-gate scoring metric in v0.4. |
| **Pain Ratio** | Cumulative return / average drawdown. | **+** Sensitive to drawdown asymmetry. **−** Not yet wired into the simulator's per-trade journal; deferred to Φ5 alongside HRP. |
| **Hit rate** | Fraction of trades with `pnl_pips > 0`. | **+** Cheap and interpretable. **−** Guardrail only per C1 (`00-charter.md` §7.1): must stay within −2 pp of baseline. Not a scoring statistic. |

**Single-source-of-truth rule.** Every gate row below picks **exactly
one** statistic from this glossary as the locked decision metric. Other
statistics from the glossary may be reported next to the headline as
diagnostic cross-checks, but **only the locked statistic decides the
verdict**.

---

## Registry table

One row per phase gate. The "Locked statistic" column is the **single**
metric that decides PASS / PARTIAL / FAIL. Sub-gates listed in the
"Notes" column are independent boolean checks that must additionally
pass before the locked-statistic verdict counts.

| Gate ID | Phase | Locked statistic | Comparator | PARTIAL band | PASS band | Rationale |
|---|---|---|---|---|---|---|
| **G1** | Φ1 → Φ2 | checklist (≥ 10 papers consumed, formulas extracted) | — | n/a | all checklist items ✓ | Literature gate; not a numeric comparator. `09` §1.5. |
| **G2** | Φ2 → Φ2.5 | checklist (architecture + roster v0 reviewed; fusion API typed objects frozen) | — | n/a | all checklist items ✓ | Frozen-API gate; not numeric. `09` §1.5. |
| **G3** | Φ2.5 → Φ3 | checklist (data manifest verifiable, MLflow live, null-baseline suite scaffolded, standards doc reviewed) | — | n/a | all checklist items ✓ | Infrastructure gate; not numeric. `09` §1.5. |
| **G4** | Φ3 → Φ4 (replay fidelity) | **Median across OOS windows of per-window mean per-trade pips** | E004 frozen baseline (`zone_d1_against / H4 / all`, median +11.34 pips/trade across 7 OOS windows; `docs/findings/2026-06-09_walk_forward_validation.md`) | 5 % < \|Δ\| ≤ 10 % from baseline | \|Δ\| ≤ 5 % from baseline | E004 headline was reported in *per-window mean pips* and decided by the median across 7 OOS windows; replay fidelity must use the *identical* statistic so wrapper drift is detectable. Sub-gates (must additionally pass): regime macro-F1 ≥ 0.75 vs hand-labelled set ≥ 200 bars; six dashboard panels render. |
| **G5-alone** | Φ4 → Φ5 (Isagi v1 vs Sae) | **Median across OOS windows of per-window mean TQS (F12)** | Sae composite (F16) computed on identical sealed panel; v0 placeholder is Frozen-Sae (`zone_d1_against`) — must be migrated to F16 before Φ5. | ratio 1.00 ≤ r < 1.10 | ratio r ≥ 1.10 | TQS is the locked optimisation target per `09` §1.4. F12 is per-trade quality; median-of-window-means is the lift form that mirrors E004's pip-based fidelity statistic but on the TQS axis. Sub-gates: 10 agents implemented in `sim/agents/`; ΔInfo (F17) measured for all 10; ≥ 6 agents with TQS > 0 in ≥ 1 regime bucket (F18); information tiers frozen post-F17. |
| **G5-squad** | Φ4 → Φ5 (4-agent MVP squad vs Isagi-alone) | **Median across OOS windows of per-window mean TQS (F12)** for the squad's fused trade stream | Isagi-alone Φ3 baseline on the same sealed panel (`reviews/phi3_gate_isagi_v1.md` median 0.317) | ratio 1.00 ≤ r < 1.10 | ratio r ≥ 1.10 | This is the gate the Φ4 v1 report (`reviews/phi4_squad_v1.md`) actually evaluated. Φ4-MVP allowance from `09` §1.5 + §2 lets the first fusion sweep test the 4-agent roster *vs Isagi-alone* before the 10-agent infrastructure is complete. The locked statistic is the same as G5-alone so the two tests are commensurable. Sub-gates (advisory at G5-squad; binding at G5-alone): same as G5-alone. |
| **G6** | Φ5 → Φ6 (full squad TQS vs Sae) | **Median across OOS windows of per-window mean TQS (F12)** for the full ensemble | Sae composite (F16) TQS on sealed 2026 H1 | ratio 1.00 ≤ r < 1.10 | ratio r ≥ 1.10 | The squad-level form of G5-alone, after the 10-agent roster + HRP allocator land. Same statistic family so G4 → G5 → G6 forms a coherent ladder of comparators. Sub-gate: zero Sentinel R1–R5 violations on replay. |
| **G7** | Φ6 → live demo | **Median across rolling 12-week windows of per-window mean TQS** for the squad | Kaiser personalised baseline (`09` §1.7): rolling 12-week median TQS of the human's high-conviction trades | ratio 1.00 ≤ r < 1.10 | ratio r ≥ 1.10 | Adversarial-cohort gate. Personalised because the human's edge is a moving target; the universal floor (Random, Sae, Frozen-Sae) is gated separately at G4–G6. Sub-gate: F13 coverage ≥ 0.6 (≥ 60 % of human coordinates overlapped by an agent coordinate). |
| **C1** | charter promotion gate | **Median across OOS windows of per-window mean TQS (F12)** | Sae composite (F16) — `00-charter.md` §7.1: TQS ≥ baseline × 1.10 | ratio 1.00 ≤ r < 1.10 | ratio r ≥ 1.10 | Same metric family as G5-alone / G6. C1 is the doctrine-level gate; G5/G6 are the phase-gate equivalents. Sub-gates: hit rate ≥ baseline − 2 pp; max drawdown ≤ baseline + 25 %. |

**Φ0 has no row.** Φ0 is the charter / archive / literature-plan phase
(`00-charter.md` table of phases). Its exit gate is implicit (user
review of `00`–`02` docs) and carries no numeric comparator.

**G5 has two rows.** G5-alone is the gate as written in `09` §1.5
(Isagi v1 vs Sae). G5-squad is the gate the Φ4 v1 report actually ran
(squad vs Isagi-alone). Both are valid evaluations under the MVP
allowance in `09` §1.5; the registry lists them separately so the
locked statistic and comparator are unambiguous for each. G5-alone is
the *required* gate before Φ5 can advance; G5-squad is the *first
fusion experiment* result and is informational until the squad-vs-Sae
form (G6) lands at Φ5 → Φ6.

---

## Worked examples

These walk through how the registry resolves the two cases that
motivated it.

### Example 1 — Φ3 (a G4-style replay-fidelity gate)

The Φ3 v1 report (`reviews/phi3_gate_isagi_v1.md`) measured A1 Isagi
v1's per-trade behaviour on EURUSD H4 2015–2025 against the E004
`zone_d1_against / H4 / all` baseline.

Under the registry:

1. The gate is **G4** (Φ3 → Φ4 replay fidelity).
2. The locked statistic is **median across OOS windows of per-window
   mean per-trade pips**.
3. The comparator is the E004 baseline median **+11.34 pips/trade**.
4. Isagi v1 produced **+11.04 pips/trade** under the locked statistic.
5. Δ = (+11.04 − +11.34) / 11.34 = **−2.7 %**.
6. Verdict: −2.7 % is inside the ±5 % PASS band → **PASS**.

If a future worker were tempted to swap to "pooled per-trade mean
pips" (Isagi v1: +6.28 pips/trade), the comparator E004 number reported
in that form would be **+0.81 pips/trade** (`reviews/phi3_gate_isagi_v1_
trades.jsonl`, mean across 7 OOS-window mean-pips) — and the ratio would
look very different. The registry forbids that swap: G4 is locked to
**median-of-window-means** because that is the statistic E004's headline
used. Cross-statistic comparisons are *journalled* (see addendum), not
*scored*.

### Example 2 — Φ4 (a G5-squad gate, squad TQS vs Isagi-alone)

The Φ4 v1 report (`reviews/phi4_squad_v1.md`) measured the 4-agent MVP
squad against Isagi-alone on EURUSD + USDCAD H4 2015–2025.

Under the registry:

1. The gate is **G5-squad** (MVP fusion sweep vs Isagi-alone).
2. The locked statistic is **median across OOS windows of per-window
   mean TQS (F12)** for the squad's fused trade stream.
3. The comparator is the Isagi-alone Φ3 baseline **0.317**.
4. Squad produced **0.311** under the locked statistic.
5. Ratio = 0.311 / 0.317 = **0.98×**.
6. Verdict: ratio < 1.00 → **FAIL** (the squad *lost* edge vs Isagi-
   alone; PARTIAL would require a positive lift below 1.10×; PASS
   would require ≥ 1.10×).

Cross-statistic diagnostic (journalled, not scored):

| Candidate statistic | Squad | Isagi-alone | Ratio | If used as locked |
|---|---|---|---|---|
| Median OOS-window mean-TQS *(locked)* | 0.3111 | 0.3175 | 0.98× | **FAIL** |
| Mean OOS-window mean-TQS | 0.3218 | 0.3320 | 0.97× | FAIL |
| Pooled per-trade mean TQS | 0.3172 | 0.3150 | 1.007× | PARTIAL (positive lift, below 1.10×) |
| Pooled per-trade median TQS | 0.0000 | 0.0000 | n/a | undefined (structural zero at RR 1.5) |
| Median OOS-window mean-pips | +4.42 | +11.04 | 0.40× | FAIL |
| Mean OOS-window mean-pips | +6.22 | +9.87 | 0.63× | FAIL |
| Pooled per-trade mean pips | +8.29 | +6.28 | 1.32× | (would be PASS under pips, but pips is not a scoring metric per `09` §1.4) |
| Pooled per-trade trimmed mean pips (10 %) | +4.57 | +3.77 | 1.21× | (forbidden as locked: cumulative pips family) |
| Cumulative pips | +16 637 | +5 380 | 3.09× | **forbidden** as locked per `09` §1.4 |
| Hit rate | 49.30 % | 48.60 % | +0.7 pp | guardrail only |

The registry's value here is visible in row 3: under *pooled per-trade
mean TQS*, the squad shows a small but positive lift (1.007×). A worker
without a locked statistic could legitimately re-tell the Φ4 result as
"PARTIAL — positive TQS lift, below the 1.10× PASS threshold". Under
the locked statistic that reading is disallowed — G5-squad is decided
on median-of-OOS-window-mean-TQS, and that statistic says FAIL.

(Cross-statistic numbers are the addendum's job to publish; the
registry exists to forbid swapping between them mid-evaluation.)

---

## Amendment procedure

A locked statistic, comparator, or threshold can only be changed via
the same discipline as a pre-registered protocol amendment
(`PROTOCOL_DISCIPLINE.md` §5):

1. **Pre-register the amendment.** New subsection at the bottom of
   this file under **`## Amendments`** with date, rationale, and a
   guarantee that the affected gate has not yet been re-evaluated under
   the new rule.
2. **Dedicated commit before the affected analysis runs.** Commit
   prefix `M001 methodology:` per `07-research-standards.md` §2.
3. **Preserve the prior locked statistic** in git history; never
   silent-edit a row above. A row change must add an amendment row;
   the original row is annotated `(superseded by amendment YYYY-MM-DD)`
   in place.
4. **Re-evaluate any sealed verdict** that was decided under the old
   rule as a new addendum to its review doc — never overwrite the
   original review.

The Φ3 / Φ4 addenda
(`programs/M001_multi_agent_ensemble/reviews/phi3_gate_isagi_v1_
addendum.md`, `programs/M001_multi_agent_ensemble/reviews/phi4_squad_
v1_addendum.md`) are the templates: original review preserved,
addendum next door, locked-rule outcome stated explicitly.

This makes the registry's discipline symmetric with the four-tier
outcome registry's append-only rule (`docs/methodology/verdict_
registry.md`, §"Registry"): the registry can grow, but it cannot
silently re-decide a past gate.

---

## Cross-references

- `07-research-standards.md` §11 — verdict-comparator discipline,
  the binding rule that this file is the single source of truth.
- `09-experiment-architecture.md` §1.5 — phase-gate numeric exit
  criteria. Where this file and `09` §1.5 disagree on a threshold,
  `09` §1.5 wins and this file is updated by amendment.
- `04-quant-foundations.md` F12 / F17 / F18 — the formulas behind
  the TQS-family statistics.
- `04-quant-foundations.md` F16 — the Sae composite baseline. C1 /
  G5-alone / G6 / C6 comparators upgrade from Frozen-Sae to F16 at
  Φ5.
- `docs/methodology/verdict_registry.md` — the **outcome** registry
  (alive / parked / dead). Distinct concept; complementary.
- `PROTOCOL_DISCIPLINE.md` §5 — amendment discipline. This file's
  amendment procedure inherits from that rule.

---

## Amendments

_(none yet — registry initialised at v0.1, 2026-06-24.)_
