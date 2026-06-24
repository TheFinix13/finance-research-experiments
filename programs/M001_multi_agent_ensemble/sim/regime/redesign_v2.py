"""Regime detection redesign v2 — candidate detectors for `vol_spike`.

Pre-registered in `programs/M001_multi_agent_ensemble/reviews/
regime_redesign_2026-06-24_PROTOCOL.md` (2026-06-24). Lands the
deterministic, ML-free detectors for the two regime classes that
failed weak-label F1 in `validation_2024_eurusd_h4.json`:

* `vol_spike` — replaces the existing rule (`rv20 > rolling_500_q95
  AND adx14 < 25`, F1 ≈ 0.10) with a strictly-causal 1-bar 3-sigma
  detector (`vol_spike_v2`).
* `news` — formally **retired** from OHLCV-only detection. This
  module exposes a no-op detector (`news_v2 := always False`) for
  symmetry and so the priority pipeline can call it uniformly; the
  retirement rationale lives in the PROTOCOL §1.2.

Design rules per `09-experiment-architecture.md` §1.2:

* All functions are pure (no global state, no `now()`, no random).
* All rolling statistics exclude bar `t` itself (no look-ahead).
* All thresholds are pre-registered constants — no learned weights.

Once the verdict report is committed, the winning detector folds
into `classifier.py:label_rule_based` and the legacy heuristic
(`atr20_percentile > 0.90`) is removed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Pre-registered constants (PROTOCOL §1.1 — do not edit without amendment)
# ---------------------------------------------------------------------------

#: Lookback window for the trailing log-return std.
VOL_SPIKE_WINDOW: int = 90

#: Multiplier on the trailing std defining the spike threshold.
VOL_SPIKE_SIGMA_MULTIPLIER: float = 3.0

#: Minimum observations required in the trailing window for the
#: detector to fire. Below this the detector abstains (returns False)
#: rather than emitting a noisy True/False decision on insufficient
#: data.
VOL_SPIKE_MIN_OBS: int = 60

# News retirement marker — kept as a constant so callers can branch on
# it explicitly rather than encoding "news is retired" in a magic value.
NEWS_RETIRED_FROM_OHLCV: bool = True


# ---------------------------------------------------------------------------
# `vol_spike` v2 — 1-bar 3-σ detector
# ---------------------------------------------------------------------------

def log_returns(close: pd.Series) -> pd.Series:
    """Closed-form log-return series; `log_returns(close)[0]` is NaN.

    Returns are computed as `log(close_t / close_{t-1})`. Output is
    aligned to `close.index`; the first row is `NaN` by construction.
    """
    if not isinstance(close, pd.Series):
        raise TypeError(f"expected pd.Series, got {type(close).__name__}")
    if (close <= 0).any():
        raise ValueError("close prices must be strictly positive for log-returns")
    return np.log(close / close.shift(1))


def trailing_std(
    series: pd.Series,
    *,
    window: int = VOL_SPIKE_WINDOW,
    min_obs: int = VOL_SPIKE_MIN_OBS,
) -> pd.Series:
    """Trailing sample standard deviation excluding the current bar.

    Strict-causal contract: the value at index `t` is computed from
    bars `[t-window, t-1]` inclusive. This is the pre-registration's
    "σ_{t-1}, not σ_t" rule from PROTOCOL §1.1.

    The implementation is the standard pandas idiom — compute the
    rolling std with the current bar included, then `.shift(1)` to
    drop the current bar. The min-periods floor is enforced after
    the shift so a series of length `window + 1` does not trigger
    on the first bar past the warmup boundary.
    """
    if window < 2:
        raise ValueError("window must be >= 2 for sample std")
    if min_obs < 2:
        raise ValueError("min_obs must be >= 2 for sample std")
    if min_obs > window:
        raise ValueError("min_obs must be <= window")
    rolled = series.rolling(window=window, min_periods=min_obs).std(ddof=1)
    return rolled.shift(1)


def detect_vol_spike(
    df: pd.DataFrame,
    *,
    window: int = VOL_SPIKE_WINDOW,
    sigma_multiplier: float = VOL_SPIKE_SIGMA_MULTIPLIER,
    min_obs: int = VOL_SPIKE_MIN_OBS,
) -> pd.Series:
    """Strict-causal 1-bar 3-σ vol_spike detector (PROTOCOL §1.1).

    A bar `t` is flagged `vol_spike` iff
    ``|log_return_t| > sigma_multiplier × σ_{t-1}`` where ``σ_{t-1}``
    is the sample standard deviation of `log_returns` over the
    trailing `window` bars **excluding** bar `t`.

    Parameters
    ----------
    df
        OHLCV bar frame with a ``close`` column. Index is preserved.
    window, sigma_multiplier, min_obs
        Pre-registered constants per the PROTOCOL. Exposed as keyword
        args so unit tests can exercise edge cases (very small
        windows, etc.); production callers should rely on the
        defaults so the detector matches the locked rule.

    Returns
    -------
    pd.Series of bool aligned to ``df.index``. ``True`` iff the bar
    is a vol_spike. Bars without enough trailing history return
    ``False`` (the detector abstains rather than emitting noise).
    """
    if "close" not in df.columns:
        raise KeyError("dataframe must contain a 'close' column")
    rets = log_returns(df["close"])
    sigma = trailing_std(rets, window=window, min_obs=min_obs)
    threshold = sigma_multiplier * sigma
    # Strict inequality so the detector matches the PROTOCOL wording
    # ("> 3.0 × σ", not ">="). NaNs (from the warmup boundary or the
    # log_return[0]=NaN) cleanly evaluate to False under pandas.
    spike = rets.abs() > threshold
    spike = spike.fillna(False).astype(bool)
    spike.name = "vol_spike_v2"
    return spike


# ---------------------------------------------------------------------------
# `news` v2 — formally retired from OHLCV-only detection (PROTOCOL §1.2)
# ---------------------------------------------------------------------------

def detect_news_ohlcv(df: pd.DataFrame) -> pd.Series:
    """Always-False detector — `news` is retired from OHLCV signals.

    See `regime_redesign_2026-06-24_PROTOCOL.md` §1.2 for the
    two binding reasons (indistinguishable from non-news vol spikes
    in OHLCV; 0-support in the held-out weak-label set).

    Downstream consumers needing a `news` regime tag must use the
    exogenous calendar adapter from `validate_real.py::load_news_
    calendar`. This function exists purely so the priority pipeline
    in `combined_label` can call `detect_news_ohlcv` symmetrically
    with the other detectors and produce a uniform OHLCV-only label
    stream.
    """
    return pd.Series(False, index=df.index, name="news_v2", dtype=bool)


# ---------------------------------------------------------------------------
# Combined OHLCV-only label (priority-ordered, F18-compliant)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DetectorConfig:
    """Locked threshold bundle for the redesigned detectors.

    Mirrors the constants at module top; defaults match the
    pre-registered values. Custom configs are allowed in unit tests
    (e.g. shrinking the window for synthetic-fixture tests) but are
    NOT used by production callers.
    """

    vol_spike_window: int = VOL_SPIKE_WINDOW
    vol_spike_sigma_multiplier: float = VOL_SPIKE_SIGMA_MULTIPLIER
    vol_spike_min_obs: int = VOL_SPIKE_MIN_OBS


def detect_all(
    df: pd.DataFrame,
    *,
    config: DetectorConfig | None = None,
) -> pd.DataFrame:
    """Run every v2 detector and return a per-bar bool matrix.

    Columns: ``vol_spike_v2``, ``news_v2`` (always False). Index is
    ``df.index``. Used by the verdict harness and the unit tests.
    Does NOT compute `trending` / `chop` — those classes weren't
    broken in `validation_2024_eurusd_h4.json` and this redesign
    leaves them alone.
    """
    cfg = config or DetectorConfig()
    return pd.DataFrame(
        {
            "vol_spike_v2": detect_vol_spike(
                df,
                window=cfg.vol_spike_window,
                sigma_multiplier=cfg.vol_spike_sigma_multiplier,
                min_obs=cfg.vol_spike_min_obs,
            ),
            "news_v2": detect_news_ohlcv(df),
        },
        index=df.index,
    )


# ---------------------------------------------------------------------------
# Evaluation helpers (used by `eval_redesign.py` and tests)
# ---------------------------------------------------------------------------

@dataclass
class PerClassMetrics:
    """Lightweight per-class metric bundle (no sklearn dependency)."""

    label: str
    support: int          # n bars where weak label == this class
    n_predicted: int      # n bars where detector predicted this class
    n_true_positive: int  # support ∩ predicted
    precision: float
    recall: float
    f1: float

    def to_jsonable(self) -> dict:
        return {
            "label": self.label,
            "support": int(self.support),
            "n_predicted": int(self.n_predicted),
            "n_true_positive": int(self.n_true_positive),
            "precision": float(self.precision),
            "recall": float(self.recall),
            "f1": float(self.f1),
        }


def binary_f1(
    *,
    weak: pd.Series,
    predicted: pd.Series,
    positive_label: str,
) -> PerClassMetrics:
    """Compute precision / recall / F1 for a single class label.

    `weak` and `predicted` are aligned string series; bars where
    `weak == positive_label` form the support set, bars where
    `predicted == positive_label` form the prediction set, and F1 is
    the harmonic mean of precision and recall.

    Zero-support classes (no bar carries the positive label in the
    weak series) return F1 = 0.0 with `support = 0`. This matches
    sklearn's `zero_division=0` convention used elsewhere in the
    regime pipeline (see `classifier.py:fit`).
    """
    if not isinstance(weak, pd.Series) or not isinstance(predicted, pd.Series):
        raise TypeError("weak and predicted must be pd.Series")
    if not weak.index.equals(predicted.index):
        raise ValueError("weak and predicted must share the same index")
    is_support = weak == positive_label
    is_predicted = predicted == positive_label
    support = int(is_support.sum())
    n_predicted = int(is_predicted.sum())
    n_tp = int((is_support & is_predicted).sum())
    precision = n_tp / n_predicted if n_predicted > 0 else 0.0
    recall = n_tp / support if support > 0 else 0.0
    f1 = (
        2.0 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    return PerClassMetrics(
        label=positive_label,
        support=support,
        n_predicted=n_predicted,
        n_true_positive=n_tp,
        precision=precision,
        recall=recall,
        f1=f1,
    )


def per_class_report(
    *,
    weak: pd.Series,
    predicted: pd.Series,
    labels: Iterable[str],
) -> dict[str, PerClassMetrics]:
    """Bundle `binary_f1` across every label and return a dict."""
    return {
        label: binary_f1(weak=weak, predicted=predicted, positive_label=label)
        for label in labels
    }
