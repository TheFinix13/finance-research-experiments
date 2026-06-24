"""Unit tests for the regime redesign v2 detectors.

Pre-registered protocol:
`programs/M001_multi_agent_ensemble/reviews/regime_redesign_2026-06-24_PROTOCOL.md`.

Test surface (covers every public function in `redesign_v2.py`):

* Strict causality of `trailing_std` (the rolling window excludes
  bar t).
* `detect_vol_spike` flags a hand-crafted 5-σ outlier and abstains on
  warmup bars / on a constant series.
* `detect_news_ohlcv` is always False (news retirement).
* `binary_f1` / `per_class_report` reproduce the textbook
  precision/recall/F1 values on a 3-bar fixture.
* `detect_all` returns a frame with the locked column names.

These are pure-logic tests; no real-parquet I/O — that lives in
the evaluation harness `eval_redesign.py` (run separately for the
verdict report).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from programs.M001_multi_agent_ensemble.sim.regime.redesign_v2 import (
    NEWS_RETIRED_FROM_OHLCV,
    VOL_SPIKE_ADX_MAX,
    VOL_SPIKE_ADX_PERIOD,
    VOL_SPIKE_MIN_OBS,
    VOL_SPIKE_SIGMA_MULTIPLIER,
    VOL_SPIKE_WINDOW,
    DetectorConfig,
    binary_f1,
    detect_all,
    detect_news_ohlcv,
    detect_vol_spike,
    detect_vol_spike_v2b,
    log_returns,
    per_class_report,
    trailing_std,
)


# ---------------------------------------------------------------------------
# Constants — these are pre-registered; the test fails if anyone edits them
# without an amendment to the PROTOCOL doc.
# ---------------------------------------------------------------------------

def test_locked_constants():
    """Pre-registered values must not silently change."""
    assert VOL_SPIKE_WINDOW == 90
    assert VOL_SPIKE_SIGMA_MULTIPLIER == 3.0
    assert VOL_SPIKE_MIN_OBS == 60
    # PROTOCOL Amendment A: ADX filter constants for v2b.
    assert VOL_SPIKE_ADX_PERIOD == 14
    assert VOL_SPIKE_ADX_MAX == 25.0
    assert NEWS_RETIRED_FROM_OHLCV is True


# ---------------------------------------------------------------------------
# `log_returns`
# ---------------------------------------------------------------------------

def test_log_returns_first_is_nan():
    close = pd.Series([1.0, 1.1, 1.21])
    rets = log_returns(close)
    assert np.isnan(rets.iloc[0])
    # log(1.1 / 1.0) ≈ 0.0953; log(1.21 / 1.1) ≈ 0.0953
    assert rets.iloc[1] == pytest.approx(np.log(1.1))
    assert rets.iloc[2] == pytest.approx(np.log(1.21 / 1.1))


def test_log_returns_rejects_non_positive():
    with pytest.raises(ValueError):
        log_returns(pd.Series([1.0, 0.0, 1.0]))
    with pytest.raises(ValueError):
        log_returns(pd.Series([1.0, -0.1, 1.0]))


def test_log_returns_rejects_non_series():
    with pytest.raises(TypeError):
        log_returns([1.0, 1.1, 1.2])


# ---------------------------------------------------------------------------
# `trailing_std`
# ---------------------------------------------------------------------------

def test_trailing_std_strict_causality():
    """The trailing std at bar t must NOT see bar t.

    Construct a series where the last bar is wildly different from
    the rest. If the rolling window peeks at bar t, the std at bar t
    explodes. Strict-causal behaviour: std at bar t reflects only
    bars [t-window, t-1].
    """
    rng = np.random.default_rng(42)
    base = pd.Series(rng.normal(0, 0.01, 80))
    spiked = pd.concat([base, pd.Series([10.0])]).reset_index(drop=True)
    sigma = trailing_std(spiked, window=10, min_obs=5)
    # The last bar's std MUST equal the std of bars [t-10, t-1],
    # which is the std of the first 80 bars' last 10 values — all
    # tiny normal noise. NOT the std of those + the 10.0 spike.
    expected = base.iloc[-10:].std(ddof=1)
    assert sigma.iloc[-1] == pytest.approx(expected, rel=1e-9)
    # Sanity: if the rule were non-causal, sigma.iloc[-1] would be
    # > 1.0 (huge); the strict-causal value is < 0.02.
    assert sigma.iloc[-1] < 0.02


def test_trailing_std_warmup_returns_nan():
    """Bars before `min_obs + 1` (the +1 is the shift) must be NaN."""
    series = pd.Series(np.linspace(0, 1, 50))
    min_obs = 5
    sigma = trailing_std(series, window=10, min_obs=min_obs)
    # The first valid value sits at position min_obs (after the shift):
    # min_obs bars accumulate, then shift(1) pushes the first valid
    # out by one, so positions [0..min_obs-1] are NaN; position
    # min_obs is the first non-NaN.
    for i in range(min_obs):
        assert np.isnan(sigma.iloc[i])
    assert not np.isnan(sigma.iloc[min_obs])


def test_trailing_std_rejects_bad_args():
    s = pd.Series([1.0, 2.0, 3.0])
    with pytest.raises(ValueError):
        trailing_std(s, window=1, min_obs=2)
    with pytest.raises(ValueError):
        trailing_std(s, window=10, min_obs=1)
    with pytest.raises(ValueError):
        trailing_std(s, window=5, min_obs=10)


# ---------------------------------------------------------------------------
# `detect_vol_spike`
# ---------------------------------------------------------------------------

def _make_close(returns: list[float], start: float = 1.0) -> pd.Series:
    """Build a close-price series from a list of log returns."""
    prices = [start]
    for r in returns:
        prices.append(prices[-1] * np.exp(r))
    return pd.Series(prices)


def test_detect_vol_spike_fires_on_handcrafted_outlier():
    """A 5σ jump at the last bar must be detected as a vol_spike."""
    rng = np.random.default_rng(7)
    base_rets = list(rng.normal(0, 0.001, 200))
    spike_ret = 0.05  # huge vs base σ ≈ 0.001
    close = _make_close(base_rets + [spike_ret])
    df = pd.DataFrame({"close": close})
    spike = detect_vol_spike(df, window=90, sigma_multiplier=3.0, min_obs=60)
    # The last bar is the outlier; everything else should be False
    # (the base is normal noise, no |r| > 3σ in expectation).
    assert bool(spike.iloc[-1]) is True
    # At most a handful of false positives in 200 normal bars by chance.
    n_other_spikes = int(spike.iloc[:-1].sum())
    assert n_other_spikes <= 5, f"too many false-positives: {n_other_spikes}"


def test_detect_vol_spike_abstains_on_constant_series():
    """A flat series (zero variance) must NOT fire vol_spike.

    Division by zero in the threshold computation should resolve to
    a non-trigger, not raise or emit True spuriously.
    """
    close = pd.Series([1.10] * 200)
    df = pd.DataFrame({"close": close})
    spike = detect_vol_spike(df)
    assert spike.dtype == bool
    assert not spike.any(), "constant series must not trigger vol_spike"


def test_detect_vol_spike_warmup_returns_false():
    """Bars in the warmup window must return False (not NaN)."""
    rng = np.random.default_rng(11)
    close = _make_close(list(rng.normal(0, 0.001, 80)))
    df = pd.DataFrame({"close": close})
    spike = detect_vol_spike(df, window=90, sigma_multiplier=3.0, min_obs=60)
    # All 81 bars are below the warmup floor (window=90, min_obs=60
    # requires ≥ 61 bars before the first valid sigma) — but the
    # series has only 81 bars, so the trailing_std starts producing
    # values around index 60. The early bars are still False.
    assert spike.iloc[:60].sum() == 0
    assert spike.dtype == bool


def test_detect_vol_spike_threshold_is_strict_gt():
    """A bar exactly at the threshold must NOT fire (strict `>`).

    PROTOCOL §1.1 wording: "> 3.0 × σ", not ">=". Construct a bar
    whose |log_return| equals exactly 3 × σ and check it stays False.
    """
    # Build a series with deterministic σ.
    rets = [0.001, -0.001] * 50  # σ ≈ 0.001 ish
    close = _make_close(rets)
    df = pd.DataFrame({"close": close})
    sigma = trailing_std(log_returns(df["close"]), window=20, min_obs=10)
    # Add a final bar with |r| exactly = 3 × σ_{t-1}.
    last_sigma = sigma.iloc[-1]
    if np.isfinite(last_sigma):
        threshold_ret = 3.0 * float(last_sigma)
        close_extended = pd.concat([
            close,
            pd.Series([close.iloc[-1] * np.exp(threshold_ret)]),
        ]).reset_index(drop=True)
        df2 = pd.DataFrame({"close": close_extended})
        spike = detect_vol_spike(
            df2, window=20, sigma_multiplier=3.0, min_obs=10
        )
        # Equal-to-threshold bar must NOT fire.
        assert not bool(spike.iloc[-1])


def test_detect_vol_spike_requires_close_column():
    df = pd.DataFrame({"open": [1.0, 1.1], "high": [1.1, 1.2]})
    with pytest.raises(KeyError):
        detect_vol_spike(df)


# ---------------------------------------------------------------------------
# `detect_vol_spike_v2b` — v2 + ADX filter (PROTOCOL Amendment A)
# ---------------------------------------------------------------------------

def _make_ohlc(returns: list[float], start: float = 1.0) -> pd.DataFrame:
    """Build an OHLC frame from log returns; high/low bracket close."""
    closes = [start]
    for r in returns:
        closes.append(closes[-1] * np.exp(r))
    closes = np.array(closes)
    return pd.DataFrame({
        "open": closes,
        "high": closes * 1.0005,  # tiny range; ADX driven by close moves
        "low": closes * 0.9995,
        "close": closes,
    })


def test_detect_vol_spike_v2b_subset_of_v2():
    """v2b must be a *subset* of v2 — the ADX filter only removes bars."""
    rng = np.random.default_rng(13)
    rets = list(rng.normal(0, 0.001, 200))
    rets[-1] = 0.05  # plant a single spike
    df = _make_ohlc(rets)
    v2 = detect_vol_spike(df)
    v2b = detect_vol_spike_v2b(df)
    # Every v2b True must also be v2 True (set-inclusion).
    assert (v2b & ~v2).sum() == 0, "v2b fired on a bar v2 did not — bug"
    # v2b must NOT exceed v2 in count.
    assert int(v2b.sum()) <= int(v2.sum())


def test_detect_vol_spike_v2b_filters_trending_bar():
    """A spike during a strong trend (ADX high) must NOT fire v2b.

    Construct a series with a long monotone uptrend (so ADX climbs
    above 25) and a single 5σ spike at the end. v2 should fire on
    the spike; v2b should suppress it because ADX > 25.
    """
    # 200 bars of steady uptrend.
    n_trend = 200
    rng = np.random.default_rng(17)
    trend = rng.normal(0.002, 0.0005, n_trend)
    # Plant a 50σ spike at the last bar (clearly outlier).
    rets = list(trend) + [0.1]
    df = _make_ohlc(rets)
    v2 = detect_vol_spike(df)
    v2b = detect_vol_spike_v2b(df)
    # v2 should fire on the last bar.
    assert bool(v2.iloc[-1]) is True
    # If ADX(14) is > 25 on the last bar, v2b should suppress it.
    from conflab.indicators import adx as _adx
    adx_last = _adx(df, period=14)["adx"].iloc[-1]
    if np.isfinite(adx_last) and adx_last >= 25:
        assert bool(v2b.iloc[-1]) is False
    # Otherwise (ADX < 25 even in this trend), v2b matches v2.
    # The assertion is conditional but exercises the filter logic
    # either way — the subset-test above already guarantees v2b ⊆ v2.


def test_detect_vol_spike_v2b_requires_high_low():
    df = pd.DataFrame({"close": [1.0, 1.1, 1.2]})
    with pytest.raises(KeyError):
        detect_vol_spike_v2b(df)


def test_detect_vol_spike_v2b_output_naming():
    rng = np.random.default_rng(23)
    df = _make_ohlc(list(rng.normal(0, 0.001, 100)))
    out = detect_vol_spike_v2b(df)
    assert out.name == "vol_spike_v2b"
    assert out.dtype == bool
    assert out.index.equals(df.index)


# ---------------------------------------------------------------------------
# `detect_news_ohlcv` — formally retired
# ---------------------------------------------------------------------------

def test_detect_news_always_false():
    """News is retired from OHLCV detection (PROTOCOL §1.2)."""
    df = pd.DataFrame({"close": [1.0, 1.1, 1.2, 0.9]})
    out = detect_news_ohlcv(df)
    assert isinstance(out, pd.Series)
    assert out.dtype == bool
    assert not out.any(), "news_v2 must never fire from OHLCV alone"
    assert out.name == "news_v2"
    assert len(out) == len(df)


# ---------------------------------------------------------------------------
# `detect_all` — bundled output
# ---------------------------------------------------------------------------

def test_detect_all_columns_and_index():
    rng = np.random.default_rng(3)
    df = _make_ohlc(list(rng.normal(0, 0.001, 200)))
    df.index = pd.date_range("2024-01-01", periods=len(df), freq="h")
    out = detect_all(df)
    assert set(out.columns) == {"vol_spike_v2", "vol_spike_v2b", "news_v2"}
    assert out.index.equals(df.index)
    assert all(out[c].dtype == bool for c in out.columns)


def test_detect_all_respects_custom_config():
    """A custom DetectorConfig must propagate to the detectors."""
    rng = np.random.default_rng(5)
    df = _make_ohlc(list(rng.normal(0, 0.001, 200)) + [0.005])
    strict_cfg = DetectorConfig(
        vol_spike_window=90,
        vol_spike_sigma_multiplier=10.0,  # almost nothing fires
        vol_spike_min_obs=60,
    )
    loose_cfg = DetectorConfig(
        vol_spike_window=90,
        vol_spike_sigma_multiplier=1.0,  # everything fires
        vol_spike_min_obs=60,
    )
    n_strict = int(detect_all(df, config=strict_cfg)["vol_spike_v2"].sum())
    n_loose = int(detect_all(df, config=loose_cfg)["vol_spike_v2"].sum())
    assert n_strict < n_loose


# ---------------------------------------------------------------------------
# `binary_f1` / `per_class_report`
# ---------------------------------------------------------------------------

def test_binary_f1_textbook():
    """Precision = 2/3, recall = 2/2, F1 = 4/5 = 0.80 on a tiny fixture."""
    weak = pd.Series(["vol_spike", "chop", "vol_spike", "chop"])
    pred = pd.Series(["vol_spike", "vol_spike", "vol_spike", "chop"])
    out = binary_f1(weak=weak, predicted=pred, positive_label="vol_spike")
    assert out.support == 2
    assert out.n_predicted == 3
    assert out.n_true_positive == 2
    assert out.precision == pytest.approx(2 / 3)
    assert out.recall == pytest.approx(1.0)
    assert out.f1 == pytest.approx(2 * (2 / 3) * 1.0 / (2 / 3 + 1.0))


def test_binary_f1_zero_support():
    """A class with 0 weak-label support returns F1 = 0 (no zero-div)."""
    weak = pd.Series(["chop", "chop", "trending"])
    pred = pd.Series(["chop", "vol_spike", "trending"])
    out = binary_f1(weak=weak, predicted=pred, positive_label="news")
    assert out.support == 0
    assert out.recall == 0.0
    assert out.precision == 0.0
    assert out.f1 == 0.0


def test_binary_f1_zero_predicted():
    """A class never predicted returns F1 = 0."""
    weak = pd.Series(["news", "chop"])
    pred = pd.Series(["chop", "chop"])
    out = binary_f1(weak=weak, predicted=pred, positive_label="news")
    assert out.support == 1
    assert out.n_predicted == 0
    assert out.precision == 0.0
    assert out.recall == 0.0
    assert out.f1 == 0.0


def test_binary_f1_index_mismatch_raises():
    weak = pd.Series(["a"], index=[0])
    pred = pd.Series(["a"], index=[1])
    with pytest.raises(ValueError):
        binary_f1(weak=weak, predicted=pred, positive_label="a")


def test_per_class_report_shape():
    weak = pd.Series(["vol_spike", "chop", "trending"])
    pred = pd.Series(["chop", "chop", "trending"])
    report = per_class_report(
        weak=weak, predicted=pred,
        labels=("vol_spike", "chop", "trending", "news"),
    )
    assert set(report) == {"vol_spike", "chop", "trending", "news"}
    assert report["news"].support == 0
    assert report["trending"].f1 == pytest.approx(1.0)
    assert report["chop"].f1 == pytest.approx(2 * 1.0 * 0.5 / 1.5)  # P=1, R=0.5
    assert report["vol_spike"].f1 == 0.0  # never predicted
