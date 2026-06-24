"""Four-class regime classifier — trending / chop / vol_spike / news.

Foundations F18 (`04-quant-foundations.md`):

* Inputs: D1 ADX bucket, 10-bar realised sigma percentile, calendar tag.
* Priority on multi-label ties: ``news > vol_spike > trending > chop``.

This Phi2.5 implementation adds two more features for the supervised
model (so a classifier can do better than the rule-based heuristic):

* 20-bar ATR percentile
* 50-bar realised vol z-score

Train on 2015-2023, validate on 2024. Phase 2->3 gate (G4) requires
holdout F1 >= 0.75.

The artefact is a small `RegimeClassifier` wrapping a sklearn
RandomForest. Both fit and predict are deterministic via the seed
plumbed through from `sim.core.seed`.

Regime-redesign retirement (2026-06-24, see
`reviews/regime_redesign_2026-06-24.md`):

* `vol_spike` — **RETIRED** from this OHLCV-only labeller. The
  weak-label F1 of the legacy rule (`atr20_percentile > 0.90`) was
  0.10, and the redesign attempts (v2 1-bar 3σ and v2b 3σ+ADX<25)
  could only reach F1 ≈ 0.23 on EURUSD H4 2024 — below the
  pre-registered PARTIAL floor of 0.30. Per
  `regime_redesign_2026-06-24_PROTOCOL.md` §4 RETIRE rule, the
  vol_spike branch is removed from `label_rule_based`. Consumers
  needing high-precision vol_spike tagging should call
  `sim.regime.redesign_v2.detect_vol_spike_v2b` directly — it is a
  *precision-1.00 / recall-0.10* tagger, not a regime classifier
  output.
* `news` — **RETIRED** from OHLCV-only emission. The price signature
  of a high-impact news event is indistinguishable from a non-news
  vol spike on OHLC bars alone, and the historical FF calendar feed
  is not available on this host (the `calendar_event_proximity`
  feature is 0 everywhere). Consumers needing news tagging should
  use `sim.regime.validate_real.load_news_calendar` once a
  historical calendar archive is piped (a Φ5 data-engineering
  deliverable).

The `REGIMES` tuple remains 4-class so downstream consumers
(`sim/scoring/regime_kpis.py`, dashboard, doctrine docs) do not
break. Retired classes simply never appear in OHLCV-derived labels;
the corresponding columns in F18 KPI tables stay empty until the
exogenous taggers fire.
"""
from __future__ import annotations

import json
import pickle
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Literal, Sequence

import numpy as np
import pandas as pd

# Use the lab's pure-pandas indicators so the classifier and the
# agents see the same numbers.
from conflab.indicators import adx, atr

RegimeLabel = Literal["trending", "chop", "vol_spike", "news"]
REGIMES: tuple[RegimeLabel, ...] = ("trending", "chop", "vol_spike", "news")
_LABEL_TO_INT = {r: i for i, r in enumerate(REGIMES)}
_INT_TO_LABEL = {i: r for r, i in _LABEL_TO_INT.items()}

FEATURE_NAMES = (
    "atr20_percentile",
    "rv50_zscore",
    "adx14",
    "calendar_event_proximity",
)


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def _rolling_percentile(series: pd.Series, window: int) -> pd.Series:
    """Rolling rank-percentile of the current value within the window."""
    return series.rolling(window).apply(
        lambda x: float((x[-1] >= x).mean()), raw=True
    )


def _realised_vol_zscore(close: pd.Series, window: int) -> pd.Series:
    """Z-score of trailing realised log-return std vs trailing mean+std."""
    log_ret = np.log(close / close.shift(1))
    rv = log_ret.rolling(window).std()
    mu = rv.rolling(window).mean()
    sigma = rv.rolling(window).std().replace(0.0, np.nan)
    return (rv - mu) / sigma


def extract_features(
    df: pd.DataFrame,
    *,
    calendar_proximity: pd.Series | None = None,
) -> pd.DataFrame:
    """Compute the four-feature matrix from an OHLCV bar frame.

    `calendar_proximity` is a 0-or-1 series (or float for soft scoring)
    aligned to `df.index`; the engine fills it from the calendar feed.
    Defaults to zero everywhere if not provided.
    """
    if calendar_proximity is None:
        calendar_proximity = pd.Series(0.0, index=df.index)
    feats = pd.DataFrame(index=df.index)
    feats["atr20_percentile"] = _rolling_percentile(atr(df, period=14), 20)
    feats["rv50_zscore"] = _realised_vol_zscore(df["close"], 50)
    feats["adx14"] = adx(df, period=14)["adx"]
    feats["calendar_event_proximity"] = calendar_proximity.astype(float)
    return feats


# ---------------------------------------------------------------------------
# Rule-based fallback (matches F18 priority)
# ---------------------------------------------------------------------------

def label_rule_based(row: pd.Series) -> RegimeLabel:
    """Deterministic rule-based labeller — `vol_spike`/`news` RETIRED.

    Original F18 priority was `news > vol_spike > trending > chop`.
    After the 2026-06-24 regime-redesign retirement (module docstring
    above; `reviews/regime_redesign_2026-06-24.md`), only the
    trending/chop arms remain. Bars that the old rule would have
    labelled `vol_spike` (`atr20_percentile > 0.90`, F1=0.10 vs weak)
    or `news` (`calendar_event_proximity > 0.5`, structurally
    OHLCV-undetectable) now fall through to trending/chop based on
    ADX.

    Priority: `trending` (ADX > 25 or ADX in 20-25 ambiguity band)
    over `chop` (ADX < 20).
    """
    adx_val = float(row.get("adx14", 0.0))
    if not np.isfinite(adx_val):
        return "chop"
    if adx_val > 25:
        return "trending"
    if adx_val < 20:
        return "chop"
    # ADX between 20-25 is ambiguous — leans trending by F18 priority order.
    return "trending"


def label_dataframe(
    df: pd.DataFrame, *, calendar_proximity: pd.Series | None = None
) -> pd.Series:
    """Apply `label_rule_based` row-wise on a feature DataFrame.

    `calendar_proximity` is preserved as a function argument for
    backward compatibility — it is no longer consulted by
    `label_rule_based` after the news retirement (see module
    docstring). Callers wiring an exogenous calendar adapter should
    use `sim.regime.validate_real.load_news_calendar` and join the
    news tag downstream of this rule's trending/chop output.
    """
    feats = extract_features(df, calendar_proximity=calendar_proximity)
    return feats.apply(label_rule_based, axis=1).astype("string")


# ---------------------------------------------------------------------------
# Supervised model
# ---------------------------------------------------------------------------

@dataclass
class TrainingResult:
    """Metrics emitted by `RegimeClassifier.fit`."""

    n_train: int
    n_holdout: int
    holdout_f1_macro: float
    per_class_f1: dict[str, float]
    per_class_precision: dict[str, float]
    per_class_recall: dict[str, float]
    confusion_matrix: list[list[int]]

    def to_jsonable(self) -> dict:
        return {
            "n_train": int(self.n_train),
            "n_holdout": int(self.n_holdout),
            "holdout_f1_macro": float(self.holdout_f1_macro),
            "per_class_f1": {k: float(v) for k, v in self.per_class_f1.items()},
            "per_class_precision": {
                k: float(v) for k, v in self.per_class_precision.items()
            },
            "per_class_recall": {
                k: float(v) for k, v in self.per_class_recall.items()
            },
            "confusion_matrix": self.confusion_matrix,
        }


@dataclass
class RegimeClassifier:
    """Random-forest regime classifier with rule-based fallback.

    Phi2.5 keeps the model very small (200 trees, max_depth 8) so the
    artefact stays under 1 MB and CI fits don't need GPUs. Phi3 may
    swap to a gradient-boosted model if F18 fairness work demands it.
    """

    seed: int = 42
    model: object | None = None
    feature_names: tuple[str, ...] = field(default_factory=lambda: FEATURE_NAMES)

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: Sequence[RegimeLabel],
        X_val: pd.DataFrame,
        y_val: Sequence[RegimeLabel],
    ) -> TrainingResult:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import (
            classification_report,
            confusion_matrix,
            f1_score,
        )

        Xt = X_train[list(self.feature_names)].fillna(0.0).to_numpy()
        Xv = X_val[list(self.feature_names)].fillna(0.0).to_numpy()
        yt = np.array([_LABEL_TO_INT[label] for label in y_train])
        yv = np.array([_LABEL_TO_INT[label] for label in y_val])

        clf = RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=int(self.seed),
            n_jobs=1,  # deterministic
        )
        clf.fit(Xt, yt)
        self.model = clf

        yhat = clf.predict(Xv)
        all_labels = list(range(len(REGIMES)))
        report = classification_report(
            yv, yhat,
            labels=all_labels,
            target_names=list(REGIMES),
            output_dict=True, zero_division=0,
        )
        per_f1 = {r: float(report[r]["f1-score"]) for r in REGIMES}
        per_prec = {r: float(report[r]["precision"]) for r in REGIMES}
        per_rec = {r: float(report[r]["recall"]) for r in REGIMES}
        cm = confusion_matrix(yv, yhat, labels=all_labels)
        macro_f1 = float(
            f1_score(yv, yhat, average="macro", labels=all_labels, zero_division=0)
        )
        return TrainingResult(
            n_train=int(len(yt)),
            n_holdout=int(len(yv)),
            holdout_f1_macro=macro_f1,
            per_class_f1=per_f1,
            per_class_precision=per_prec,
            per_class_recall=per_rec,
            confusion_matrix=cm.tolist(),
        )

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            # Fallback to the rule-based labeller if the model isn't trained.
            return np.array([label_rule_based(row) for _, row in X.iterrows()])
        Xn = X[list(self.feature_names)].fillna(0.0).to_numpy()
        yhat_int = self.model.predict(Xn)
        return np.array([_INT_TO_LABEL[int(i)] for i in yhat_int])

    def predict_proba(self, X: pd.DataFrame) -> pd.DataFrame:
        if self.model is None:
            raise RuntimeError("model not trained; call fit() first")
        Xn = X[list(self.feature_names)].fillna(0.0).to_numpy()
        proba = self.model.predict_proba(Xn)
        return pd.DataFrame(proba, columns=list(REGIMES), index=X.index)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str | Path, *, manifest: dict | None = None) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            pickle.dump(
                {
                    "seed": int(self.seed),
                    "feature_names": list(self.feature_names),
                    "model": self.model,
                },
                fh,
            )
        if manifest is not None:
            manifest_path = path.with_suffix(path.suffix + ".manifest.json")
            manifest_path.write_text(
                json.dumps(
                    manifest
                    | {
                        "datetime_utc": datetime.now(timezone.utc).isoformat(),
                        "feature_names": list(self.feature_names),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )

    @classmethod
    def load(cls, path: str | Path) -> "RegimeClassifier":
        with Path(path).open("rb") as fh:
            blob = pickle.load(fh)
        inst = cls(seed=int(blob["seed"]))
        inst.feature_names = tuple(blob["feature_names"])
        inst.model = blob["model"]
        return inst
