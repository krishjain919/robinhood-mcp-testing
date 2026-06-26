import pandas as pd

from market_data import get_price_history


def add_sma(data: pd.DataFrame, window: int):
    data[f"SMA_{window}"] = data["Close"].rolling(window=window).mean()
    return data


def add_rsi(data: pd.DataFrame, window: int = 14):
    delta = data["Close"].diff()

    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    avg_gain = gains.rolling(window=window).mean()
    avg_loss = losses.rolling(window=window).mean()

    rs = avg_gain / avg_loss
    data[f"RSI_{window}"] = 100 - (100 / (1 + rs))

    return data


def add_volume_ratio(data: pd.DataFrame, window: int = 50):
    data[f"avg_volume_{window}"] = data["Volume"].rolling(window=window).mean()
    data["volume_ratio"] = data["Volume"] / data[f"avg_volume_{window}"]
    return data


def add_returns(data: pd.DataFrame):
    data["return_1d"] = data["Close"].pct_change()
    data["return_5d"] = data["Close"].pct_change(5) * 100
    data["return_20d"] = data["Close"].pct_change(20) * 100
    data["return_63d"] = data["Close"].pct_change(63) * 100
    return data


def _true_range(data: pd.DataFrame) -> pd.Series:
    """
    True Range = max of (today's high-low), (high - prev close), (prev close - low).

    Uses High/Low/Close so it captures gaps, which a Close-only range misses.
    """

    prev_close = data["Close"].shift(1)
    high_low = data["High"] - data["Low"]
    high_close = (data["High"] - prev_close).abs()
    low_close = (data["Low"] - prev_close).abs()

    return pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)


def add_atr(data: pd.DataFrame, window: int = 14):
    """
    Average True Range — the workhorse volatility measure for swing stops.

    atr_pct expresses it as a share of price so it's comparable across tickers.
    """

    tr = _true_range(data)
    data["true_range"] = tr
    data[f"atr_{window}"] = tr.rolling(window=window).mean()
    data["atr_pct"] = (data[f"atr_{window}"] / data["Close"]) * 100
    return data


def add_macd(data: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = data["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = data["Close"].ewm(span=slow, adjust=False).mean()

    data["macd"] = ema_fast - ema_slow
    data["macd_signal"] = data["macd"].ewm(span=signal, adjust=False).mean()
    data["macd_hist"] = data["macd"] - data["macd_signal"]
    return data


def add_adx(data: pd.DataFrame, window: int = 14):
    """
    Average Directional Index — trend STRENGTH (not direction).

    ADX > ~20-25 means a trend is actually in motion, which is exactly the
    condition swing breakouts want. Below that, price is usually chopping.
    """

    up_move = data["High"].diff()
    down_move = -data["Low"].diff()

    plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
    minus_dm = ((down_move > up_move) & (down_move > 0)) * down_move

    tr = _true_range(data)
    atr = tr.rolling(window=window).mean()

    plus_di = 100 * (plus_dm.rolling(window=window).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=window).mean() / atr)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    data["adx_14"] = dx.rolling(window=window).mean()
    return data


def add_distance_metrics(data: pd.DataFrame):
    """How stretched price is from its key moving averages, in percent."""
    data["dist_sma_20_pct"] = ((data["Close"] / data["SMA_20"]) - 1) * 100
    data["dist_sma_50_pct"] = ((data["Close"] / data["SMA_50"]) - 1) * 100
    return data


def add_breakout_data(data: pd.DataFrame):
    # Previous 20-day high, not including today.
    data["prior_20d_high"] = data["Close"].rolling(20).max().shift(1)
    data["breakout_20d"] = data["Close"] > data["prior_20d_high"]

    data["high_52w"] = data["Close"].rolling(252).max()
    data["low_52w"] = data["Close"].rolling(252).min()

    data["pct_below_52w_high"] = ((data["Close"] / data["high_52w"]) - 1) * 100
    data["pct_above_52w_low"] = ((data["Close"] / data["low_52w"]) - 1) * 100

    return data


def add_relative_strength(data: pd.DataFrame, benchmark_data: pd.DataFrame | None = None):
    """
    Simple relative strength:
    stock 3-month return minus SPY 3-month return.
    """

    if benchmark_data is None:
        data["relative_strength_63d"] = 0
        return data

    benchmark = benchmark_data.copy()
    benchmark = add_returns(benchmark)

    benchmark_rs = benchmark[["Date", "return_63d"]].rename(
        columns={"return_63d": "benchmark_return_63d"}
    )

    data = data.merge(benchmark_rs, on="Date", how="left")
    data["relative_strength_63d"] = data["return_63d"] - data["benchmark_return_63d"]

    return data


def add_indicators(data: pd.DataFrame, benchmark_data: pd.DataFrame | None = None):
    data = data.copy()

    for window in [20, 50, 150, 200]:
        data = add_sma(data, window)

    data = add_rsi(data, 14)
    data = add_volume_ratio(data, 50)
    data = add_returns(data)
    data = add_breakout_data(data)
    data = add_relative_strength(data, benchmark_data)
    data = add_atr(data, 14)
    data = add_macd(data)
    data = add_adx(data, 14)
    data = add_distance_metrics(data)

    return data


def safe_float(value, default=0.0):
    if pd.isna(value):
        return default

    return float(value)


def get_latest_indicators(symbol: str):
    benchmark_data = get_price_history("SPY", period="2y", interval="1d")
    data = get_price_history(symbol, period="2y", interval="1d")
    data = add_indicators(data, benchmark_data)

    latest = data.iloc[-1]

    return {
        "symbol": symbol.upper(),
        "price": round(safe_float(latest["Close"]), 2),
        "sma_20": round(safe_float(latest["SMA_20"]), 2),
        "sma_50": round(safe_float(latest["SMA_50"]), 2),
        "sma_150": round(safe_float(latest["SMA_150"]), 2),
        "sma_200": round(safe_float(latest["SMA_200"]), 2),
        "rsi_14": round(safe_float(latest["RSI_14"]), 2),
        "volume_ratio": round(safe_float(latest["volume_ratio"]), 2),
        "return_5d": round(safe_float(latest["return_5d"]), 2),
        "return_20d": round(safe_float(latest["return_20d"]), 2),
        "return_63d": round(safe_float(latest["return_63d"]), 2),
        "relative_strength_63d": round(safe_float(latest["relative_strength_63d"]), 2),
        "breakout_20d": bool(latest["breakout_20d"]),
        "pct_below_52w_high": round(safe_float(latest["pct_below_52w_high"]), 2),
        "pct_above_52w_low": round(safe_float(latest["pct_above_52w_low"]), 2),
        "atr_14": round(safe_float(latest["atr_14"]), 2),
        "atr_pct": round(safe_float(latest["atr_pct"]), 2),
        "macd": round(safe_float(latest["macd"]), 3),
        "macd_signal": round(safe_float(latest["macd_signal"]), 3),
        "macd_hist": round(safe_float(latest["macd_hist"]), 3),
        "adx_14": round(safe_float(latest["adx_14"]), 2),
        "dist_sma_20_pct": round(safe_float(latest["dist_sma_20_pct"]), 2),
        "dist_sma_50_pct": round(safe_float(latest["dist_sma_50_pct"]), 2),
    }


if __name__ == "__main__":
    print(get_latest_indicators("NVDA"))