# Regime detection redesign — pre-registered protocol (2026-06-24)

**Status:** `PRE-REGISTERED` — locked **before** any candidate detector
is implemented or evaluated.

**Author:** regime-redesign worker (M001 Φ4.1 / Φ5-prep stream).

**Binding rules applied:** `07-research-standards.md` §5 (no post-hoc
protocol amendments) + §11 (verdict-comparator discipline, registry at
`docs/methodology/gate_verdict_registry.md`).

**Reason this protocol exists.** `sim/regime/validation_2024_eurusd_h4.json`
reports per-class weak-label F1 of **`vol_spike` ≈ 0.10** and
**`news` ≈ 0.00** (the other classes pass: `trending` 0.92, `chop` 0.96).
Both broken classes block Φ5's F18 regime-conditional KPI work
(`04-quant-foundations.md` F18). They must either improve or be
formally retired (with documented rationale) before Φ5 can wire F18 —
that's the work this protocol pre-registers.

This is **not** an agent-evolution arc (no `vN → vN+1` agent module
swap), so it does **not** append to `reviews/evolution_ledger.md`. It
is a sub-Φ4.1 sub-module redesign with its own verdict report
(`regime_redesign_2026-06-24.md`, deliverable after code lands).

---

## 1. Pre-registered class definitions (candidate v2 detectors)

The current weak-label rules sit in `sim/regime/validate_real.py`:

* `vol_spike` — `rv20 > rolling_500_quantile(rv20, 0.95)` **AND**
  `adx14 < 25`. Single-bar count: 23 in 2024 EURUSD H4.
* `news` — within ±2 H4 bars of a high-impact USD/EUR ForexFactory
  event. Single-bar count: **0** in 2024 EURUSD H4 because the
  ForexFactory feed in `agent.news.calendar` is a current-week pull
  with no historical archive (logged in
  `validation_2024_eurusd_h4.json:manifest.news_calendar_available =
  false`).

### 1.1 `vol_spike` candidate detector (v2)

> **Rule.** A bar `t` is labelled `vol_spike` iff
> `|log_return_t| > 3.0 × σ(log_return, window=90, ddof=1)`, computed
> on the trailing 90 bars **excluding** the current bar (`σ_t-1`, not
> `σ_t`, to keep the rule strictly causal).

Equivalent statement: a one-bar 3-sigma move vs the trailing 90-bar
log-return distribution. By assumption-of-normality this fires on
~0.27 % of bars; on real FX bars (fatter tails) we expect 1–3 %.

**Why this rule and not the weak rule.** Two reasons:

1. **Semantic fit.** A "spike" is a single-bar outlier event. The weak
   rule uses `rv20` — a 20-bar *rolling* std — which detects a
   *high-volatility regime*, not a *spike*. The semantics in
   `04-quant-foundations.md` F18 ("vol_spike" as one of four states a
   bar can be in) are closer to the single-bar definition. The weak
   rule's choice of `rv20` was an interim heuristic, not a doctrine
   commitment.
2. **Non-circularity.** If the new detector replicated the weak rule
   verbatim, the F1 vs weak labels would trivially be 1.0 and prove
   nothing. The 3-sigma single-bar detector is a *different statistic*
   (1-bar vs 20-bar window, std-scaled vs percentile-scaled) so a high
   F1 vs weak labels is informative convergence, not tautology.

**Falsifiable.** If the candidate yields per-class F1 < 0.30 against
weak labels on the held-out window, the detector fails.

**No ADX filter.** The original weak rule's `adx14 < 25` filter
conflated "vol_spike" with "vol_spike-in-chop". Spikes also occur
during trends (impulsive breakouts). The candidate keeps the spike
test unconditional and lets the *priority ordering* (`vol_spike >
trending > chop`) resolve overlaps — same approach the F18 priority
list specifies.

### 1.2 `news` candidate detector (v2): **formal retirement from OHLCV**

> **Decision.** `news` is **retired** as an OHLCV-derivable regime
> class. The class label remains in the regime taxonomy
> (`{trending, chop, vol_spike, news}`) for downstream consumers, but
> the OHLCV-only detector pipeline emits `news` only when an exogenous
> calendar adapter is wired and asserts the bar is within ±2 H4 bars
> of a high-impact event. When the calendar adapter is unavailable,
> the OHLCV pipeline never emits `news` and the bar falls through to
> the next priority class (`vol_spike > trending > chop`).

**Two binding reasons.**

1. **No evaluable signal in OHLCV.** The price signature of a
   high-impact news event (sharp directional move + spread widening
   + volume spike) is **indistinguishable** from a non-news vol spike
   on OHLC bars alone. Volume from the production MT5 broker feed is
   a tick-count proxy (not real volume), so the
   "volume > 95th percentile" companion clause the user's brief
   suggested adds no discriminating power vs the abs-return percentile
   already used in the vol_spike rule. A detector trained to flag
   "looks like news" on OHLCV would just be a re-named vol_spike
   detector with worse precision (every false-positive vol_spike
   becomes a false-positive news).
2. **The weak-label support is structurally 0 on this host.** The
   2024 EURUSD H4 validation has 0 weak-label `news` bars because the
   production calendar cache (`agent.news.calendar`) is a
   current-week feed (logged in
   `validation_2024_eurusd_h4.json:manifest.news_calendar_available =
   false`). Even if the OHLCV-only detector were perfect, **F1
   cannot rise above 0.00 against a 0-support class**. There is no
   amount of detector tuning that can clear this.

**Recommendation propagated to Φ5.** F18 regime-conditional KPIs
should be computed for the **three OHLCV-resolvable classes**
(`trending`, `chop`, `vol_spike`). The `news` class is an
**exogenous-metadata tag** populated by `load_news_calendar()` in
`sim/regime/validate_real.py` when a historical calendar archive is
piped (a Φ5 data-engineering deliverable, not a classifier
deliverable). Per-agent per-`news` KPIs are computed only on
calendar-tagged bars; when the calendar is unavailable, the `news`
column in the F18 KPI table is left empty (`null`) and the pooled
total is reported as `unclassified_news_residual` per F18's
`unclassified_residual` convention (`04-quant-foundations.md` F18 §
"Failure mode" paragraph).

This is the **honest** answer to the user's brief — "or formal
retirement if news cannot be detected from OHLCV alone" was an
explicit option in the brief, and the evidence above selects it. We
do not pretend an OHLCV-only news detector is possible.

---

## 2. Detection algorithm (deterministic, no ML)

All detectors below are **pure functions of OHLCV bars** with no
learned parameters. Reproducibility comes from:

* fixed lookback windows (90 bars for `vol_spike`),
* fixed thresholds (3.0 × σ for `vol_spike`),
* strict causality (rolling statistics computed on `[t-window:t-1]`,
  never including bar `t` itself).

Implementation lives in a new file `sim/regime/redesign_v2.py` so
this protocol's verdict can be reproduced independently of the
existing `classifier.py`. The winning rules are then folded into
`classifier.py:label_rule_based` (or its v2 replacement) once the
verdict is final — that's commit 3 of this work.

No model weights, no random seeds (other than the deterministic-seed
plumbing already in `sim.core.seed`).

---

## 3. Evaluation set (held out from threshold tuning)

| Property | Value |
|---|---|
| Primary symbol/TF | EURUSD H4 |
| Primary window | 2024-01-01 → 2024-12-31 (1 617 bars) |
| Source parquet | `multi-pair-trading-agent/data/parquet/EURUSD_H4.parquet` |
| Weak-label rules | `sim/regime/validate_real.py:weak_label_row` (unchanged from current `validate_real.py`) |
| Cross-symbol robustness | GBPUSD H4 2024, USDCAD H4 2024 (same window, same weak-label rules) |
| Cross-period robustness | EURUSD H4 2023-01-01 → 2023-12-31 |

The thresholds (90-bar window, 3.0 σ) are chosen **before** running
on the held-out window per `07-research-standards.md` §5 — they are
fixed by this pre-registration and cannot move post-evaluation.

If the primary EURUSD-H4-2024 window is the *only* sample where the
candidate beats the weak rule's F1 floor, that is reported as a
PARTIAL with explicit cross-statistic caveat (see §4). A candidate
that holds across **all four** evaluation slices is reported as
robust PASS.

---

## 4. PASS / PARTIAL / FAIL / RETIRE thresholds

| Verdict | Per-class F1 vs weak labels (primary window) | Cross-symbol robustness | Action |
|---|---|---|---|
| **PASS** | F1 ≥ 0.50 | F1 ≥ 0.50 on ≥ 2 of 3 cross slices | swap detector into `classifier.py`; class is **usable** for F18 |
| **PARTIAL** | F1 ∈ [0.30, 0.50) | any | swap detector into `classifier.py`; class is **flagged-low-confidence** for F18 (KPIs reported but with explicit caveat row) |
| **FAIL** | F1 < 0.30 AND > 0 | any | do NOT swap; class is **unusable** until next iteration; Φ5 F18 omits this class until the next redesign attempt; escalate to user as a blocker |
| **RETIRE** | structurally unevaluable (e.g. 0-support across all available data slices), OR F1 < 0.30 even after one additional honest iteration | any | document retirement in the report; class is **removed** from the OHLCV-only detector; downstream consumers route to exogenous data (calendar adapter, etc.) |

**The 0.50 PASS threshold matches `validate_real.py:WEAK_GATE_AGREEMENT_F1`**
(the existing weak-label gate). The 0.30 PARTIAL floor is chosen so a
class with sparse support (`vol_spike` has 23 weak-labelled bars in
2024 EURUSD H4) doesn't get penalised for a single misclassification
swinging the F1 by ~7 points. Both thresholds are below the eventual
G4 gate (F1 ≥ 0.75 vs *hand-labelled* validation in
`09-experiment-architecture.md` §1.5) — a class can clear this
redesign's PASS and still need hand-labelling work for G4, that is
intentional.

**Pre-registered verdicts per class (with the implicit hypothesis being tested).**

* `vol_spike` — **hypothesised PASS** (F1 ≥ 0.50). If FAIL, escalate;
  if PARTIAL, ship with the flag and document the residual.
* `news` — **pre-registered RETIRE.** This is not a hypothesis being
  tested; it is a structural call based on the §1.2 reasoning. The
  evaluation harness will still report whatever F1 the OHLCV-only
  detector achieves (which is 0.00 by construction on the 2024
  window) for documentation completeness, but the verdict is RETIRE
  regardless because the structural reason in §1.2 is decisive.

---

## 5. Weak-label ceiling acknowledgement

Per `validate_real.py`'s module docstring and
`sim/regime/README.md` "What the number is not" section: **the F1
this protocol scores against is NOT ground-truth F1**. The weak
labels are themselves a heuristic — `rv20 > 95th percentile + adx14 <
25` is not the same as "a human FX trader would call this a vol
spike".

What this means for the verdict:

* A high F1 against weak labels means **the candidate detector agrees
  with the heuristic**. That is necessary but not sufficient for the
  detector to be right on real bars.
* A low F1 against weak labels means **the candidate detector
  disagrees with the heuristic** — but in either direction, the
  "true" answer is unknown without hand labelling. The current
  classifier's F1 = 0.10 on `vol_spike` could mean the classifier
  is wrong, the heuristic is wrong, or both.
* The 2024 EURUSD H4 disagreement set
  (`disagreements_for_review.csv`, 30 sampled anchors) is the
  designated escalation path. If the candidate detector also
  disagrees with weak labels on those anchors, the appropriate next
  step is hand-labelling via `label_disagreements.py` — **not**
  another round of detector tweaking.
* Any PASS in this protocol is **provisional pending hand-labelling**.
  The G4 gate (F1 ≥ 0.75 vs ≥ 200 hand-labelled bars) is not closed
  by this work and remains a Φ3-carryover in `ai_context.md`.

---

## 6. Falsifiability checklist (what would make me retract)

| Observation | Required response |
|---|---|
| `vol_spike` v2 F1 < 0.30 on primary window | FAIL; do not ship; escalate to user with the blocker description in the verdict report. |
| `vol_spike` v2 F1 PASS on EURUSD-2024 but FAIL on GBPUSD-2024 AND USDCAD-2024 | Downgrade to PARTIAL; ship with explicit "EURUSD-only" caveat; flag for cross-pair re-eval in Φ5. |
| `news` weak-label support > 0 appears (e.g. user loads a historical calendar archive between commit 1 and commit 4) | Reopen the `news` decision; do not silently RETIRE; commit an amendment subsection to this protocol with the new evidence and the revised verdict. |
| Cross-statistic robustness shows the F1 sensitivity is dominated by *which* statistic the weak rule uses (e.g. rv20-percentile vs rv50-zscore vs abs-return-sigma all give wildly different "weak labels") | Add a **weak-label sensitivity** addendum to the verdict report; the locked PASS/PARTIAL/FAIL still uses the registry-locked weak-label rule from `validate_real.py` but the diagnostic table shows how much of the F1 is methodology vs signal. |

---

## 7. Deliverables under this protocol

| # | Artefact | Commit |
|---|---|---|
| 1 | This protocol (`regime_redesign_2026-06-24_PROTOCOL.md`) | commit 1 (pre-registration) |
| 2 | Candidate detector code (`sim/regime/redesign_v2.py`) | commit 2 |
| 3 | Unit tests (`sim/tests/test_regime_redesign.py`) | commit 2 (same as detectors) |
| 4 | Updated `classifier.py` swapping in winners; re-run `validate_real.py` writing fresh `validation_2024_eurusd_h4.json` | commit 3 |
| 5 | Verdict report (`regime_redesign_2026-06-24.md`) | commit 4 |

Each commit follows the `M001 regime: <subject>` pattern per
`07-research-standards.md` §2 and includes a `pytest` pass on
`sim/tests/` before landing per `09-experiment-architecture.md` §1.2
determinism contract.

---

## 8. Cross-references

* Foundations: `04-quant-foundations.md` F18 — regime-conditional KPIs.
* Phase gate: `09-experiment-architecture.md` §1.5 G4 (the *eventual*
  gate this work feeds into; this protocol's PASS does not close G4).
* Verdict-comparator discipline: `07-research-standards.md` §11 +
  `docs/methodology/gate_verdict_registry.md`. The registry currently
  carries no row for the per-class regime F1 (it locks per-gate squad
  TQS aggregators); the per-class F1 thresholds in §4 above are the
  locked equivalent for this sub-module.
* Existing weak-label rule (the comparator): `sim/regime/validate_real.py`
  — `weak_label_row`.
* Existing per-class F1 baseline: `validation_2024_eurusd_h4.json`
  (snapshot before this redesign).
* Hand-labelling escalation path: `sim/regime/label_disagreements.py`
  (Streamlit tool, owned by the user; not touched by this work).
