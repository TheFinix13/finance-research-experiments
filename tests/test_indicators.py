"""Indicator sanity contracts on synthetic data."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conflab import indicators as ind
from conflab.data import synthetic_frame

DF = synthetic_frame(400, seed=11)


def test_rsi_bounded():
    r = ind.rsi(DF)
    assert ((r >= 0) & (r <= 100)).all()


def test_bollinger_ordering():
    bb = ind.bollinger(DF).dropna()
    assert (bb["bb_upper"] >= bb["bb_mid"]).all()
    assert (bb["bb_mid"] >= bb["bb_lower"]).all()


def test_ema_constant_series_converges():
    flat = DF.copy()
    flat["close"] = 1.2345
    assert ind.ema(flat, 20).iloc[-1] == pytest.approx(1.2345, abs=1e-6)


def test_atr_positive():
    a = ind.atr(DF).dropna()
    assert (a > 0).all()


def test_donchian_contains_closes():
    dc = ind.donchian(DF).dropna()
    closes = DF["close"].loc[dc.index]
    assert (closes <= dc["dc_upper"] + 1e-12).all()
    assert (closes >= dc["dc_lower"] - 1e-12).all()


def test_stochastic_bounded():
    st = ind.stochastic(DF).dropna()
    assert ((st >= -1e-9) & (st <= 100 + 1e-9)).all().all()


def test_adx_finite_after_warmup():
    a = ind.adx(DF).iloc[50:]
    assert np.isfinite(a["adx"].to_numpy()).all()


def test_macd_obv_cci_vwap_williams_shapes():
    assert len(ind.macd(DF)) == len(DF)
    assert len(ind.obv(DF)) == len(DF)
    assert len(ind.cci(DF)) == len(DF)
    v = ind.vwap(DF)
    assert np.isfinite(v.to_numpy()).all()
    w = ind.williams_r(DF).dropna()
    assert ((w <= 1e-9) & (w >= -100 - 1e-9)).all()
