"""Indicator math on synthetic data (no network)."""

import numpy as np
import pandas as pd

from technical_indicators import add_sma, add_rsi, add_atr, add_macd, add_adx


def _synthetic(n=300, start=50.0, drift=0.4, noise=0.5):
    rng = np.random.default_rng(42)
    closes = start + np.cumsum(np.full(n, drift) + rng.normal(0, noise, n))
    closes = np.maximum(closes, 1.0)
    highs = closes + rng.uniform(0.1, 1.0, n)
    lows = closes - rng.uniform(0.1, 1.0, n)
    return pd.DataFrame({
        "Date": pd.date_range("2022-01-01", periods=n, freq="D"),
        "Open": closes,
        "High": highs,
        "Low": lows,
        "Close": closes,
        "Volume": rng.integers(1_000, 10_000, n),
    })


def test_sma_matches_rolling_mean():
    df = add_sma(_synthetic(), 20)
    assert "SMA_20" in df.columns
    assert abs(df["SMA_20"].iloc[-1] - df["Close"].iloc[-20:].mean()) < 1e-6


def test_rsi_bounded_0_100():
    df = add_rsi(_synthetic(), 14)
    rsi = df["RSI_14"].dropna()
    assert rsi.between(0, 100).all()


def test_atr_positive_and_percent():
    df = add_atr(_synthetic(), 14)
    assert df["atr_14"].iloc[-1] > 0
    assert df["atr_pct"].iloc[-1] > 0
    # ATR% should be a small single/double-digit fraction of price, not huge.
    assert df["atr_pct"].iloc[-1] < 50


def test_macd_histogram_is_macd_minus_signal():
    df = add_macd(_synthetic())
    last = df.iloc[-1]
    assert abs(last["macd_hist"] - (last["macd"] - last["macd_signal"])) < 1e-9


def test_adx_in_uptrend_is_meaningful():
    df = add_adx(_synthetic(drift=0.5, noise=0.2), 14)
    adx = df["adx_14"].dropna()
    assert adx.between(0, 100).all()
    assert len(adx) > 0
