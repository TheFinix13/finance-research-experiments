# `sim/regime/` — four-class regime classifier

**Status:** Φ2.5 scaffold + Φ3-prep weak-label validation —
2026-06-24. Binding spec: [`../../09-experiment-architecture.md`](../../09-experiment-architecture.md) §1.5
(G4) and [`../../04-quant-foundations.md`](../../04-quant-foundations.md) F18.

Four classes, priority `news > vol_spike > trending > chop`:

| Class | Heuristic (weak label) |
|---|---|
| `news` | within ±2 bars of a high-impact USD/EUR ForexFactory event |
| `vol_spike` | realised_vol(20) > rolling 95th pct AND ADX(14) < 25 |
| `trending` | ADX(14) > 25 AND \|close − SMA(20)\| > 0.5 × ATR(14) |
| `chop` | ADX(14) < 15 AND realised_vol(20) < rolling 30th pct |

## Files

```
classifier.py             RandomForest wrapper + rule-based fallback (F18)
train.py                  Trainer; synthetic-OHLC smoke mode by default
eval.py                   Holdout eval against the G4 gate
validate_real.py          Φ3-prep weak-label validation (this README)
model_v1.pkl              Trained artefact (seed 42, synthetic source)
model_v1.pkl.manifest.json
validation_2024_eurusd_h4.json
disagreements_for_review.csv
```

## Why the Φ2.5 synthetic F1 ≈ 0.999 is not the G4 gate

`train.py --seed 42` (no real parquet) generates a synthetic OHLCV
walk, runs the **F18 rule-based labeller** on it to produce
training targets, then fits a RandomForest on those same labels.
The reported holdout F1 ≈ 0.999 is therefore a **circular**
metric: the trainer fits to the rule it is being scored against.
It only proves the classifier can memorise the rule it was trained
on. It does **not** prove the rule is right on real bars.

`09-experiment-architecture.md` §1.5 G4 requires **holdout F1 ≥ 0.75
vs a hand-labelled validation set (≥ 200 bars)**. Hand labels do
not yet exist for this repo — see "What G4 still needs" below.

## What `validate_real.py` actually measures (and what it does not)

`validate_real.py` runs the trained classifier on real EURUSD H4
bars (the production parquet cache at
`../multi-pair-trading-agent/data/parquet/EURUSD_H4.parquet`) for
2024-01-01 → 2024-12-31 and scores it against the heuristic weak
labels above. The output JSON carries:

* **agreement_f1_macro** — macro-F1 of the classifier's predictions
  vs the heuristic, computed on the subset of bars where the
  heuristic gives a confident vote.
* **per_class precision / recall / F1** — same split per class.
* **confusion_matrix_rows_weak_cols_pred** — rows are the heuristic
  label (the "weak truth"), columns are the classifier prediction.
* **counts.n_total_bars / n_scored_bars / n_unknown_weak_label** —
  how many bars the heuristic abstained on (mostly bars in the
  ADX 15-25 grey zone or where realised_vol was between the 30th
  and 95th percentile). Those bars are excluded from the metric.
* **gate.threshold_agreement_f1** — set to **0.50**. Below this the
  classifier is doing worse than the rule on the real bars it was
  meant to generalise; that is a signal to escalate to
  hand-labelling, not a reason to discard the classifier outright.

### What the number is not

The agreement F1 is **NOT** ground-truth F1. The heuristic itself
is a flawed labeller (no calibration, no human review, abstains on
~half the year). Three concrete asymmetries to remember:

1. **News class is currently un-evaluable on this host.** The
   ForexFactory feed in the production repo is a current-week
   pull; historical 2024 events are not cached. `validate_real.py`
   degrades the news rule to "abstain" when the calendar is
   unavailable, so `support` for `news` is 0 in the per-class
   metrics and the macro-F1 drags a class with no data.
2. **Vol-spike rule is conservative.** The 95th-percentile floor on
   a rolling 500-bar window is sparse on H4 (~5 % of scored bars).
   Small support means a single disagreement swings the F1 by tens
   of points.
3. **No hand-labelled bars exist.** A classifier prediction that
   disagrees with the heuristic might still be **right** — humans
   would routinely classify an ADX-22 bar with a clean SMA pull as
   trending even though the heuristic abstains.

### How to read the 2026-06-24 baseline

The first run (`validation_2024_eurusd_h4.json`) reported:

| Field | Value |
|---|---|
| `agreement_f1_macro` | **0.496** |
| `n_total_bars` | 1617 |
| `n_scored_bars` | 772 (47.7 % of year — heuristic confident) |
| `n_unknown_weak_label` | 845 (52.3 % — heuristic abstained) |
| `n_disagreements_total` | 106 |
| `n_disagreements_sampled` | 30 |
| Per-class F1 | trending **0.92** · chop **0.96** · vol_spike **0.10** · news **0.00** |
| Gate pass vs weak labels | **FAIL** (0.496 < 0.50) |

Interpretation:

* **Trending and chop are fine.** F1 0.92 / 0.96 vs the heuristic on
  ~95 % of the scored bars is a sane "the classifier learned the
  obvious rule" outcome. Not surprising — the synthetic trainer
  produces those two classes most of the time.
* **Vol_spike is broken on real data.** F1 0.10 means the classifier
  almost never agrees with the heuristic on the 23 bars the rule
  flagged as a vol spike. The 95th-percentile floor on H4 is a
  hard target the synthetic walker doesn't reproduce; the model
  hasn't seen the relevant feature distribution.
* **News is invisible.** support=0 on this host because the FF
  calendar pipe isn't wired for historical look-up.
* **Macro drags below 0.5 because of vol_spike and news.** The
  signal is "this classifier should not be relied on to fire the
  vol_spike branch of the F18 priority in production", not "the
  classifier is universally broken".

Recommended next moves (in priority order):

1. **Hand-label the 30 sampled disagreements.** Each is a real bar
   with 50 bars of preceding OHLC context in
   `disagreements_for_review.csv`; chart, decide, score.
2. **Train a Φ3 classifier on real 2015–2023 EURUSD H4 bars** with
   the weak labels as the *initial* target, then iterate with
   hand-labelled corrections.
3. **Pipe a historical ForexFactory archive** (or any analogous
   calendar source — Investing.com, Trading Economics, dukascopy
   news flags) so the news class is evaluable.
4. **Re-run `validate_real.py`** against the new model; the
   agreement F1 should climb to ≥ 0.65 on real-trained models
   before any G4 claim.

## What G4 still needs

| Item | Status | Owner |
|---|---|---|
| Trained classifier with weights | done (`model_v1.pkl`) | — |
| Synthetic holdout F1 ≥ 0.75 | trivially passes (0.999); not the gate | — |
| **Real-data weak-label F1 ≥ 0.50** | **FAIL (0.496) on 2024 EURUSD H4** | Φ3 |
| Hand-labelled validation bars (≥ 200) | **not started** | Φ3 |
| Hand-labelled holdout F1 ≥ 0.75 | **not measurable yet** | Φ3 |

The `disagreements_for_review.csv` is the seed dataset for the
hand-labelling step. 30 bars × 51 OHLC context rows each; a human
can label all 30 in a single review session.

## Running the validator

```bash
PYTHONPATH=../multi-pair-trading-agent:. \
  ../multi-pair-trading-agent/.venv/bin/python \
  -m programs.M001_multi_agent_ensemble.sim.regime.validate_real
```

Defaults:

* parquet: `../multi-pair-trading-agent/data/parquet/EURUSD_H4.parquet`
* model: `sim/regime/model_v1.pkl`
* window: `2024-01-01 → 2025-01-01`
* output: `validation_2024_eurusd_h4.json` +
  `disagreements_for_review.csv`

Override the window with `--window-start YYYY-MM-DD --window-end YYYY-MM-DD`.
If the requested window has fewer than 200 bars, the script
substitutes the most recent 12 months of available bars and
records the substitution in `manifest.window_substitution`.

## Cross-references

* G4 gate definition: `../../09-experiment-architecture.md` §1.5
* F18 regime taxonomy + priority: `../../04-quant-foundations.md`
* Research standards on labelling hygiene:
  `../../07-research-standards.md` §4 (no synthetic-only F1 claims)
* `sim/README.md` — Φ2→Φ3 gate row, sim-wide test surface
