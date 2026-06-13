"""Classic technical indicators, pure pandas (no TA-Lib dependency).

Every function takes an OHLCV DataFrame (columns: open, high, low, close,
volume; DatetimeIndex) and returns a Series or DataFrame aligned to it.
Defaults are the standard textbook parameters and are FIXED for the
experiment — tuning them to make confluence "work" is forbidden by the
protocol in PROTOCOL.md.

Note on volume: FX retail feeds carry tick volume only. OBV/VWAP here are
tick-volume proxies, not institutional order flow.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(df: pd.DataFrame, period: int = 20, col: str = "close") -> pd.Series:
    return df[col].rolling(period).mean()


def ema(df: pd.DataFrame, period: int = 20, col: str = "close") -> pd.Series:
    return df[col].ewm(span=period, adjust=False).mean()


def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder's RSI, bounded [0, 100]."""
    delta = df["close"].diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.fillna(50.0)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder's Average True Range."""
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def bollinger(df: pd.DataFrame, period: int = 20, n_std: float = 2.0) -> pd.DataFrame:
    mid = sma(df, period)
    std = df["close"].rolling(period).std(ddof=0)
    return pd.DataFrame({
        "bb_mid": mid,
        "bb_upper": mid + n_std * std,
        "bb_lower": mid - n_std * std,
    })


def macd(df: pd.DataFrame, fast: int = 12, slow: int = 26,
         signal: int = 9) -> pd.DataFrame:
    line = ema(df, fast) - ema(df, slow)
    sig = line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame({
        "macd": line, "macd_signal": sig, "macd_hist": line - sig,
    })


def stochastic(df: pd.DataFrame, k_period: int = 14,
               d_period: int = 3) -> pd.DataFrame:
    low_min = df["low"].rolling(k_period).min()
    high_max = df["high"].rolling(k_period).max()
    rng = (high_max - low_min).replace(0.0, np.nan)
    k = 100 * (df["close"] - low_min) / rng
    return pd.DataFrame({"stoch_k": k, "stoch_d": k.rolling(d_period).mean()})


def roc(df: pd.DataFrame, period: int = 10) -> pd.Series:
    """Rate of change (momentum), percent."""
    return df["close"].pct_change(period) * 100


def adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Wilder's ADX with +DI / -DI."""
    up = df["high"].diff()
    down = -df["low"].diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    tr = atr(df, period)
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / tr
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / tr
    denom = (plus_di + minus_di).replace(0.0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / denom
    return pd.DataFrame({
        "plus_di": plus_di, "minus_di": minus_di,
        "adx": dx.ewm(alpha=1 / period, adjust=False).mean(),
    })


def obv(df: pd.DataFrame) -> pd.Series:
    """On-balance (tick) volume — proxy only, see module docstring."""
    direction = np.sign(df["close"].diff()).fillna(0.0)
    return (direction * df["volume"]).cumsum()


def cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    ma = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - ma) / (0.015 * mad.replace(0.0, np.nan))


def donchian(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    upper = df["high"].rolling(period).max()
    lower = df["low"].rolling(period).min()
    return pd.DataFrame({
        "dc_upper": upper, "dc_lower": lower, "dc_mid": (upper + lower) / 2,
    })


def keltner(df: pd.DataFrame, period: int = 20,
            atr_mult: float = 2.0) -> pd.DataFrame:
    mid = ema(df, period)
    band = atr_mult * atr(df, period)
    return pd.DataFrame({
        "kc_mid": mid, "kc_upper": mid + band, "kc_lower": mid - band,
    })


def vwap(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Rolling tick-volume-weighted average price (session VWAP needs session
    boundaries; the rolling form keeps it causal and timeframe-agnostic)."""
    tp = (df["high"] + df["low"] + df["close"]) / 3
    vol = df["volume"].replace(0.0, np.nan)
    num = (tp * vol).rolling(period).sum()
    den = vol.rolling(period).sum()
    return (num / den).fillna(tp)


def williams_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_max = df["high"].rolling(period).max()
    low_min = df["low"].rolling(period).min()
    rng = (high_max - low_min).replace(0.0, np.nan)
    return -100 * (high_max - df["close"]) / rng
