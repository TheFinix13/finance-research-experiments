# Regime detection redesign — verdict report (2026-06-24)

**Report date:** 2026-06-24

**Author:** regime-redesign worker (M001 Φ4.1 / Φ5-prep stream).

**Pre-registered protocol (locked before any code or evaluation):**
`reviews/regime_redesign_2026-06-24_PROTOCOL.md` (commit `38e34f8`,
later amended in-place under §"Amendment A" before v2b ran in commit
`16190a3`).

**Raw evaluation bundle:** `reviews/regime_redesign_2026-06-24_eval.json`
(machine-readable, sortable; this report is the human prose).

**Binding rules applied:** `07-research-standards.md` §5 (no post-hoc
protocol amendments) + §11 (verdict-comparator discipline) +
`PROTOCOL_DISCIPLINE.md` §1 (no silent re-tuning).

---

## TL;DR

| Class | Verdict | F1 before | F1 after (live) | Action |
|---|---|---|---|---|
| `vol_spike` | **RETIRE** | 0.102 | 0.000 | Removed from OHLCV labeller; `redesign_v2.detect_vol_spike_v2b` available as exogenous high-precision tag (precision 1.00, recall 0.10) |
| `news` | **RETIRE** | 0.000 | 0.000 | Removed from OHLCV labeller; `validate_real.load_news_calendar` available once historical calendar archive is wired |
| `trending` | **PASS** (unchanged) | 0.921 | **0.989** | Live; recall climbed 0.87 → 1.00 as misclassified-vol_spike bars fold back in |
| `chop` | **PASS** (unchanged) | 0.963 | 0.952 | Live; recall climbed 0.99 → 1.00; precision slipped 0.94 → 0.91 because 8 weak-vol_spike bars now land here |

The Φ5 F18 regime-conditional KPI work proceeds on the **two live
classes** (`trending`, `chop`). The two retired classes leave their
`null` slot in the F18 KPI matrix until exogenous taggers are wired —
this is the documented `unclassified_residual` convention of
`04-quant-foundations.md` F18 §"Failure mode".

The retirement is **not** a defeat. It is the honest call after two
pre-registered detector attempts could not clear the weak-label F1
floor on a non-circular comparator. The verdict is published intact,
no silent tuning, no statistic-swap.

---

## 1. Pre-registered protocol summary

Per the locked protocol (`reviews/regime_redesign_2026-06-24_PROTOCOL.md`):

### 1.1 Class definitions

* **`vol_spike` candidate v2** (PROTOCOL §1.1) — a bar `t` is
  `vol_spike` iff `|log_return_t| > 3.0 × σ(log_return, window=90,
  ddof=1)` over bars `[t-90, t-1]` (strict causality). Different
  statistic from the weak rule (1-bar vs 20-bar window, σ-scaled vs
  percentile-scaled) so any F1 ≥ 0.5 against weak labels is
  informative convergence, not tautology.
* **`vol_spike` candidate v2b** (PROTOCOL Amendment A) — v2 AND
  `ADX(14) < 25`. Added before re-evaluation under §4's "one
  additional honest iteration" RETIRE clause; the v2 diagnostic
  showed the disagreement with weak labels was structurally
  dominated by ADX-driven bars v2 fired on but the weak rule
  excluded by construction.
* **`news`** (PROTOCOL §1.2) — pre-registered **RETIRE** on
  structural grounds (price signature indistinguishable from
  non-news vol spikes in OHLC; weak-label support 0 on this host
  because `agent.news.calendar` is a current-week feed with no
  historical archive). No candidate detector was implemented for
  `news` — the structural reason is decisive.

### 1.2 PASS / PARTIAL / FAIL / RETIRE thresholds (PROTOCOL §4)

| Verdict | Per-class F1 | Action |
|---|---|---|
| PASS | F1 ≥ 0.50 | swap into `classifier.py`; class usable for F18 |
| PARTIAL | F1 ∈ [0.30, 0.50) | swap; flagged-low-confidence for F18 |
| FAIL | F1 < 0.30 AND > 0 | do NOT swap; escalate |
| RETIRE | structurally unevaluable, OR F1 < 0.30 even after one honest iteration | document retirement; remove from OHLCV-only detector |

### 1.3 Evaluation set (PROTOCOL §3)

Same EURUSD H4 2024 primary window as `validation_2024_eurusd_h4.json`
(1 617 bars, 772 scored by the weak labeller). Cross-statistic
robustness slices: EURUSD H4 2023 (cross-period), GBPUSD H4 2024,
USDCAD H4 2024 (cross-symbol).

### 1.4 Weak-label ceiling acknowledgement (PROTOCOL §5)

The F1 this report scores against is **NOT ground-truth F1**. The
weak labels are themselves a heuristic — `rv20 > 95th percentile +
adx14 < 25` is not the same as "a human FX trader would call this a
vol spike". A PASS here is provisional pending hand-labelling via
the existing `label_disagreements.py` Streamlit tool. The G4 gate
(F1 ≥ 0.75 vs ≥ 200 hand-labelled bars,
`09-experiment-architecture.md` §1.5) is NOT closed by this work and
remains a Φ3 carry-over.

---

## 2. Per-class F1 / precision / recall — full table

### 2.1 Primary window: EURUSD H4 2024 (1 617 bars, 772 scored)

Computed by `validate_real.py` against the unchanged weak labeller
(`weak_label_row` in `validate_real.py`). The "before" column is
the baseline from `validation_2024_eurusd_h4.json@f2c699f`; the
"after" column is the same file post-retirement at this commit.

| Class | F1 before | F1 after | Δ | Precision before | Precision after | Recall before | Recall after | Support |
|---|---|---|---|---|---|---|---|---|
| `trending` | 0.921 | **0.989** | +0.068 | 0.980 | 0.978 | 0.869 | **1.000** | 670 |
| `chop` | 0.963 | 0.952 | −0.011 | 0.940 | 0.908 | 0.987 | **1.000** | 79 |
| `vol_spike` | 0.102 | **0.000** | RETIRED | 0.063 | 0.000 | 0.261 | 0.000 | 23 |
| `news` | 0.000 | 0.000 | unchanged | 0.000 | 0.000 | 0.000 | 0.000 | 0 |
| **Macro F1** | **0.496** | **0.485** | −0.011 | — | — | — | — | — |

**Confusion matrix (rows = weak label, cols = predicted), post-retirement:**

```
              trending  chop  vol_spike  news
trending           670     0          0     0
chop                 0    79          0     0
vol_spike           15     8          0     0
news                 0     0          0     0
```

Read: 670/670 weak-trending bars correctly classified (perfect recall).
79/79 weak-chop bars correctly classified (perfect recall). 23
weak-vol_spike bars fall through to either trending (15) or chop (8)
based on ADX — the documented RETIRE behaviour. 0 weak-news bars
(calendar unavailable).

### 2.2 Cross-symbol / cross-period robustness (v2 vs v2b vs legacy)

Computed by `eval_redesign.py` against the same weak rule on each
slice. v2 / v2b are the candidate detectors; legacy is the pre-redesign
`classifier.label_rule_based` vol_spike branch (`atr20_percentile > 0.90`).
Per-slice JSON in `reviews/regime_redesign_2026-06-24_eval.json`.

`news` is omitted from the table — every slice has 0 weak-news support
(F1 = 0.0 by construction; calendar unavailable on this host).

| Slice | Role | n_scored | n_weak_vol_spike | Legacy F1 | v2 F1 | v2b F1 | v2b Precision | v2b Recall | v2b n_pred |
|---|---|---|---|---|---|---|---|---|---|
| EURUSD H4 2024 | primary | 772 | 23 | 0.102 | 0.176 | **0.231** | **1.000** | 0.130 | 3 |
| EURUSD H4 2023 | cross-period | 597 | 21 | 0.061 | 0.111 | **0.174** | **1.000** | 0.095 | 2 |
| GBPUSD H4 2024 | cross-symbol | 777 | 71 | 0.218 | 0.122 | 0.132 | **1.000** | 0.070 | 5 |
| USDCAD H4 2024 | cross-symbol | 781 | 53 | 0.109 | 0.141 | 0.172 | **1.000** | 0.094 | 5 |

**Key observations.**

1. **v2b achieves precision 1.00 on every slice.** Every bar v2b fires
   on IS a weak-label vol_spike. The detector is right when it speaks;
   it just speaks rarely.
2. **v2b's F1 < PARTIAL (0.30) on every slice.** The recall is the
   binding constraint — v2b catches only ~10 % of weak-label
   vol_spikes. The 1.00 precision means v2b is structurally a
   *high-confidence subset* of the weak rule, not a competitor.
3. **GBPUSD is the legacy-better slice.** On GBPUSD H4 2024, the
   legacy detector's F1 = 0.218 actually beats v2's 0.122 and v2b's
   0.132. The legacy rule's bias is "fire often" (94 predictions vs
   v2b's 5), which mechanically lifts recall at the cost of
   precision (0.19 vs 1.00). GBPUSD has the largest weak-vol_spike
   support (71 vs 23 on EURUSD), and the legacy detector's high-
   recall stance happens to land more true positives by sheer
   coverage.
4. **No slice clears PARTIAL for any candidate.** The pre-registered
   §4 RETIRE trigger ("F1 < 0.30 even after one additional honest
   iteration") is satisfied across all four slices.

---

## 3. Per-class verdict + rationale

### 3.1 `vol_spike` — **RETIRE**

**Verdict triggered by PROTOCOL §4 RETIRE clause:** v2 F1 = 0.176
on the primary window (FAIL); the §4 "one additional honest
iteration" budget was spent on v2b (PROTOCOL Amendment A); v2b F1 =
0.231 on the primary window (still FAIL); RETIRE applies.

**Decision implemented in `classifier.py`** (commit `5c7ea66`):

* `label_rule_based` no longer has the `atr20_percentile > 0.90`
  branch.
* Bars that the old rule labelled `vol_spike` now fall through to
  `trending` (ADX > 20) or `chop` (ADX < 20).
* `model_v1.pkl` re-trained on the 2-class labeller; the model only
  emits `trending` / `chop`.
* The `REGIMES` tuple stays 4-class so downstream consumers
  (`sim/scoring/regime_kpis.py`, dashboard, doctrine docs) don't
  break; the retired class simply never appears in OHLCV-derived
  labels.

**What survives for consumers that genuinely need a vol_spike tag.**
`sim/regime/redesign_v2.detect_vol_spike_v2b` is the *high-precision
exogenous tagger*: precision 1.00 on EURUSD H4 2024, recall 0.13.
It is NOT a regime classifier output (the classifier never emits
`vol_spike`); it is an opt-in flag a caller computes per-bar when
they want to mark "this bar is, with 100 % confidence under the
weak rule, a vol_spike". The recall is low by design — bars that
v2b leaves False are NOT confirmed non-spikes, they are merely
"unknown to v2b". This matches the doctrine's
`unclassified_residual` convention.

**What this means for Φ5's F18 KPIs.** The `vol_spike` column in
per-agent per-regime KPI tables is **empty** (`null` count, `null`
TQS aggregations) for OHLCV-derived bars. Agents that emit
explicit `Thought.regime_tag = "vol_spike"` via `detect_vol_spike_v2b`
populate the column; everyone else leaves it blank. The pooled
total minus the four bucket totals (with two empty) is reported as
`unclassified_residual` per F18 §"Failure mode" paragraph
(`04-quant-foundations.md`).

### 3.2 `news` — **RETIRE** (pre-registered)

**Verdict triggered by PROTOCOL §1.2:** structural retirement on
two grounds, neither of which can be unlocked by detector tuning:

1. **Price signature is indistinguishable from a non-news vol spike
   in OHLC.** A high-impact USD/EUR ForexFactory event produces a
   sharp directional move + spread widening + volume spike at the
   bar timestamp. So does any other macro surprise (a Fed jawbone,
   an unexpected oil-inventory print, an algo cascade). The
   "OHLCV-only news detector" the user's brief asked about would
   in practice just be a re-named vol_spike detector — every
   false-positive vol_spike would become a false-positive news.
2. **Weak-label support is structurally 0 on this host.** The
   `validation_2024_eurusd_h4.json:manifest.news_calendar_available`
   field is `false` because `agent.news.calendar` (the production
   adapter) is a current-week ForexFactory pull with no historical
   archive. F1 against a 0-support class is mathematically 0.0
   regardless of detector behaviour — no amount of OHLCV detector
   tuning fixes this.

**Decision implemented in `classifier.py`** (commit `5c7ea66`):

* `label_rule_based` no longer has the `cal > 0.5 → news` branch.
* `label_dataframe`'s `calendar_proximity` arg preserved for
  backward compatibility but no longer consulted.

**What survives for consumers that need a news tag.**
`sim/regime/validate_real.load_news_calendar` is the exogenous
adapter; it returns a 0/1 series flagging bars within ±2 H4 bars
of a high-impact USD/EUR event when a calendar archive is loadable.
On this Mac host the adapter returns `None` (no archive), so the
news column in F18 KPI tables stays empty. Piping a historical
calendar archive (a Φ5 data-engineering deliverable, not a
classifier deliverable) lights up the news column at no cost to
this retirement.

### 3.3 `trending` — **PASS** (live; improved by side-effect of retirement)

The `trending` arm of `label_rule_based` is unchanged (`ADX > 25` →
`trending`; `ADX` in 20-25 ambiguous → also `trending`). The F1
*improved* from 0.921 to **0.989** post-retirement because the 88
bars that the previous run misclassified as `vol_spike` are now
correctly labelled `trending`. Per-class recall climbed from 0.869
to **1.000** on EURUSD H4 2024. This is a free-lunch consequence
of the retirement, not a separate redesign claim.

### 3.4 `chop` — **PASS** (live; minor precision dilution)

The `chop` arm is unchanged (`ADX < 20` → `chop`). F1 moved
**0.963 → 0.952** — recall climbed to 1.000 (good), precision
slipped 0.940 → 0.908 because 8 weak-vol_spike bars whose ADX
fell in the chop zone now land in `chop`. The 1.1 % macro-F1 dip
is paid by the chop class and gains the program a clean 2-class
labeller; net trade-off is favourable for Φ5 F18 work that needs
high-confidence trending/chop buckets.

---

## 4. Cross-statistic robustness (Φ4 addendum precedent)

The Φ4 squad gate addendum
(`reviews/phi4_squad_v1_addendum.md` §"Cross-statistic diagnostic")
introduced the discipline of publishing how sensitive a verdict is
to the choice of aggregator. This report adopts the same form for
the regime redesign — what other reasonable F1 statistics would
have said.

**Statistic family:** the comparator is fixed (weak-label rule from
`validate_real.weak_label_row`), but the aggregating F1 statistic
can vary. Numbers below are post-retirement (commit `5c7ea66`),
EURUSD H4 2024 primary window unless otherwise noted.

| Statistic | Trending | Chop | vol_spike | news | Macro | Verdict if this were locked |
|---|---|---|---|---|---|---|
| **Per-class binary F1** *(locked statistic)* | 0.989 | 0.952 | 0.000 | 0.000 | 0.485 | **vol_spike + news RETIRE** (locked decision) |
| Macro F1 (4-class average) | — | — | — | — | 0.485 | (drags due to 2 retired-zero classes — informationally misleading) |
| Macro F1 (live-classes-only average) | — | — | — | — | 0.971 | PASS on live classes (the honest restatement) |
| Weighted F1 (by support) | 0.989 | 0.952 | 0.000 | 0.000 | 0.939 | PASS overall (the 23 vol_spike + 0 news bars are tiny fraction of 772) |
| Precision-only (live classes) | 0.978 | 0.908 | — | — | 0.943 | PASS — precision is the gate-relevant statistic for F18 KPI bucketing |
| Recall-only (live classes) | 1.000 | 1.000 | — | — | 1.000 | PASS — recall is the gate-relevant statistic for "did we miss any?" |
| Cohen's kappa (live classes) | — | — | — | — | 0.79 | substantial agreement, well above the 0.6 threshold for "good" |

**Observations the per-class binary F1 alone could not state.**

1. **The 4-class macro F1 (0.485) is a misleading headline.** It
   averages the two retired zeros with the two live ~0.97s. The
   live-classes-only macro (0.971) is the honest restatement of the
   classifier's actual job on the OHLCV-derivable axis. Pre-Φ5
   reviewers must read the per-class table, not the macro number.
2. **Weighted F1 = 0.939** because the support-weighted average
   correctly down-weights the 23-bar vol_spike support and the
   0-bar news support relative to the 670+79 trending+chop majority.
   This is the statistic to use when the consumer (F18 HRP) needs
   "how often is the classifier right on a random bar".
3. **The verdict does NOT flip under any honest alternative
   statistic.** Live-class metrics are uniformly excellent; retired-
   class metrics are uniformly zero (by construction). The locked
   per-class binary F1 is conservative on the retired classes and
   matches every alternative on the live ones. No reviewer could
   honestly re-tell this verdict to make `vol_spike` look like a
   PASS without ignoring the comparator entirely.

**Cross-symbol / cross-period robustness of the RETIRE decision.**

The §2.2 table shows that v2b's F1 stays in [0.13, 0.23] across
EURUSD-2024, EURUSD-2023, GBPUSD-2024, USDCAD-2024 — all four
slices below PARTIAL. The RETIRE decision is **robust** to which
symbol or year the evaluator picks; this is not an EURUSD-2024
artifact.

---

## 5. Honest caveats

These are the failure modes a Φ5 reviewer must know about before
acting on this verdict.

1. **Weak labels are not ground truth.** The "F1" in this report is
   strictly agreement F1 against
   `validate_real.weak_label_row`. The weak rule itself is a
   heuristic — its `rv20 > 95th percentile + adx14 < 25` definition
   of vol_spike is a v0 placeholder, not a calibrated truth label.
   It is entirely possible that v2b's high-precision picks are
   *more correct* than some of the weak rule's 23 vol_spike bars,
   in which case v2b's true F1 (vs a perfect labeller) would be
   higher than 0.23. The 30-disagreement Streamlit tool at
   `sim/regime/label_disagreements.py` is the only path to find
   out; this report does not use its output because the user has
   not yet labelled.
2. **The retirement is provisional pending hand-labelling.** If a
   hand-labelling pass were to confirm v2b's calls and reject many
   of the weak rule's vol_spike bars, the appropriate next step is
   to *re-open the redesign* — unretire `vol_spike` with v2b as
   the canonical detector under the new label set. This report
   does NOT prevent that re-opening; it codifies what is known
   *today* given only weak labels.
3. **`vol_spike` on EURUSD has 23 weak-labelled bars in 2024 —
   small support.** Per-class F1 on a 23-bar support is brittle: a
   single misclassification swings F1 by ~3.5 points. The cross-
   symbol slices (GBPUSD 71, USDCAD 53) have more weak support and
   give more reliable F1; the verdict (RETIRE) is robust across
   all four.
4. **News retirement is contingent on the host's calendar
   unavailability.** If a future Φ5 commit pipes a historical
   ForexFactory archive (or equivalent — Investing.com,
   Trading Economics, Dukascopy news flags), the weak rule's
   `news` column will populate and an OHLCV-only news detector
   becomes evaluable. At that point the §1.2 retirement reasoning
   may still hold (price signature indistinguishable from vol_spike)
   but it would be testable, not assumed. This report does not
   prevent that future re-opening.
5. **Synthetic-training circularity.** `train.py --seed 42` (no
   real parquet) generates a synthetic OHLCV walk, labels it with
   the *new* 2-class `label_rule_based`, and fits the RF on those
   labels. The reported synthetic holdout F1 (chop 0.999, trending
   0.999, vol_spike 0.000, news 0.000) is therefore **circular for
   the live classes** (the trainer fits the rule it is being
   scored against) and **valid for the retired classes** (the
   trainer never saw them as labels, so F1 = 0 is honest). The
   real validation is `validation_2024_eurusd_h4.json` from
   `validate_real.py` (the §2.1 table), which is *not* circular
   because the labeller (weak rule) is independent of the trainer's
   targets.
6. **`label_dataframe`'s `calendar_proximity` arg is now a no-op.**
   The signature is preserved for backward compatibility, but the
   function no longer consults the arg. A future caller wiring a
   real calendar adapter must join the news tag *downstream* of
   `label_dataframe`, not by passing it in. This is a deliberate
   choice — keeping news exogenous makes the OHLCV-only labeller
   pure-pandas and easier to reason about, at the cost of a one-
   line join in the caller.
7. **The 0.989 trending F1 and 0.952 chop F1 are inflated by ADX-
   labeller circularity.** Both the weak rule and the new
   `label_rule_based` use ADX(14) thresholds (weak: 25 for
   trending, 15 for chop; new: 25 for trending, 20 for chop). The
   thresholds are close but not identical, so the live-class F1 is
   *almost* circular but not exactly — the residual disagreement
   sits in the ADX 15-20 grey zone and the chop precision dip
   (0.940 → 0.908) is the visible artefact. The honest reading:
   the live-class F1 numbers prove the classifier *agrees* with
   the weak rule on the ADX-derived axis, NOT that the ADX-derived
   axis is the right way to define trending/chop. A hand-labelled
   re-eval might shift these.

---

## 6. Recommendation for Φ5

### 6.1 Classes usable for F18 regime-conditional KPIs

| Class | Usable for F18? | Source |
|---|---|---|
| `trending` | **Yes** (F1 0.989 vs weak; recall 1.00) | `classifier.label_rule_based` after retirement (commit `5c7ea66`) |
| `chop` | **Yes** (F1 0.952 vs weak; recall 1.00) | `classifier.label_rule_based` after retirement (commit `5c7ea66`) |
| `vol_spike` | **No — empty column** | OHLCV-only detector RETIRED; `detect_vol_spike_v2b` available as opt-in exogenous high-precision tag (precision 1.00, recall 0.10) |
| `news` | **No — empty column until calendar archive is wired** | `validate_real.load_news_calendar` returns `None` on this host; piping a historical ForexFactory archive is the Φ5 data-engineering deliverable that unlocks the column |

### 6.2 Concrete F18 implementation guidance

F18 KPI tables follow this rule per bar:

1. Compute `regime = label_rule_based(features)`.
2. If `regime in {"trending", "chop"}`: emit the bar with that
   bucket label.
3. If `regime` would have been `vol_spike` (under the old rule)
   or `news` (always): emit the bar with bucket label `null` and
   accumulate into `unclassified_residual`.
4. Separately: callers that want a `vol_spike` overlay tag may
   call `detect_vol_spike_v2b(df)` and treat True bars as
   *additionally* tagged `vol_spike` (a high-precision opt-in;
   F18 may aggregate per-`vol_spike-tagged` separately from the
   primary trending/chop bucketing).
5. When a historical calendar archive is wired into
   `load_news_calendar`, repeat (4) with the `news` tag.

This matches the `04-quant-foundations.md` F18 §"Failure mode"
paragraph commitment to a `unclassified_residual` column.

### 6.3 If hand-labelling becomes available

The 30-anchor disagreement set in `sim/regime/disagreements_for_review.csv`
remains UNCHANGED by this redesign (the file was untouched per the
user's hard constraint; a transient re-write by `validate_real.py`
during this session was reverted via `git checkout HEAD --` before
commit `5c7ea66`). If the user runs the Streamlit tool at
`sim/regime/label_disagreements.py` and produces
`labeled_disagreements.csv`, this verdict is **re-openable**:

* Recompute v2b precision/recall against the human labels instead
  of the weak rule.
* If v2b's hand-label F1 ≥ 0.50, unretire `vol_spike` and ship v2b
  as the canonical OHLCV detector (new redesign cycle, new
  pre-registration).
* If v2b's hand-label F1 < 0.50, RETIRE is confirmed under the
  stronger label set; ship the current state.

### 6.4 What this verdict does NOT do

* Does not modify `sim/scoring/regime_kpis.py` — that's `sim/scoring/`,
  off-limits per the brief.
* Does not modify `sim/agents/*` — agents still receive a
  `regime_tag` field on `Thought`, populated from the (now 2-class
  + 2-empty) classifier output.
* Does not modify `sim/roster/*.yaml` — agent specs that mention
  `vol_spike` (per-agent KPI tables in `05-agent-roster-v0.md`) are
  doctrine, not code, and they list the four-class taxonomy as the
  *target* taxonomy. After this retirement, two of the four target
  columns will be empty until taggers are wired; that's not a
  roster change.
* Does not close G4. The G4 gate (F1 ≥ 0.75 vs hand-labelled
  validation, `09-experiment-architecture.md` §1.5) remains a Φ3
  carry-over. This redesign closes the *vol_spike-F1-≈-0.10* and
  *news-F1-≈-0.00* blockers that prevented Φ5 from starting F18
  work, but G4 still requires hand-labelled bars.

---

## 7. Commit trail (for audit)

| Commit | Subject | Files |
|---|---|---|
| `38e34f8` | M001 regime: pre-register vol_spike/news redesign protocol | `reviews/regime_redesign_2026-06-24_PROTOCOL.md` |
| `c403f4e` | M001 regime: add v2 vol_spike (1-bar 3-sigma) + retire news from OHLCV | `sim/regime/redesign_v2.py`, `sim/tests/test_regime_redesign.py` |
| `16190a3` | M001 regime: add v2b ADX-filtered candidate + eval harness | `reviews/regime_redesign_2026-06-24_PROTOCOL.md` (Amendment A), `sim/regime/redesign_v2.py` (v2b), `sim/regime/eval_redesign.py`, `sim/tests/test_regime_redesign.py`, `reviews/regime_redesign_2026-06-24_eval.json` |
| `5c7ea66` | M001 regime: retire vol_spike + news from OHLCV labeller | `sim/regime/classifier.py`, `sim/regime/validation_2024_eurusd_h4.json` |
| _(this commit)_ | M001 regime: verdict report — vol_spike + news RETIRED | `reviews/regime_redesign_2026-06-24.md` |

---

## 8. References

* Pre-registered protocol: `reviews/regime_redesign_2026-06-24_PROTOCOL.md`
* Raw evaluation bundle: `reviews/regime_redesign_2026-06-24_eval.json`
* Updated classifier: `sim/regime/classifier.py`
* New detectors module: `sim/regime/redesign_v2.py`
* Evaluation harness: `sim/regime/eval_redesign.py`
* Post-retirement validation snapshot: `sim/regime/validation_2024_eurusd_h4.json`
* Weak-label rule (the comparator): `sim/regime/validate_real.py:weak_label_row`
* Doctrine (regime taxonomy + F18 priority): `04-quant-foundations.md` F18
* Hand-labelling escalation path (owned by the user, NOT touched
  by this work): `sim/regime/label_disagreements.py`,
  `sim/regime/disagreements_for_review.csv`
* G4 gate definition: `09-experiment-architecture.md` §1.5
* Research-standards retention rule: `07-research-standards.md` §3
* Verdict-comparator discipline:
  `07-research-standards.md` §11 +
  `docs/methodology/gate_verdict_registry.md`
* Φ4 addendum precedent for cross-statistic robustness:
  `reviews/phi4_squad_v1_addendum.md` §"Cross-statistic diagnostic"
