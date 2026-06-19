import pandas as pd

from market_data import get_price_history


def add_sma(data: pd.DataFrame, window: int):
    data[f"SMA_{window}"] = data["Close"].rolling(window=window).mean()
    return data


def add_rsi(data: pd.DataFrame, window: int = 14):
    """
    Basic RSI calculation.

    Not trying to be fancy here. Just enough to tell if a stock is getting
    too stretched or still has room.
    """

    delta = data["Close"].diff()

    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    avg_gain = gains.rolling(window=window).mean()
    avg_loss = losses.rolling(window=window).mean()

    rs = avg_gain / avg_loss
    data[f"RSI_{window}"] = 100 - (100 / (1 + rs))

    return data


def add_volume_ratio(data: pd.DataFrame, window: int = 20):
    data["avg_volume_20"] = data["Volume"].rolling(window=window).mean()
    data["volume_ratio"] = data["Volume"] / data["avg_volume_20"]
    return data


def add_returns(data: pd.DataFrame):
    data["return_5d"] = data["Close"].pct_change(5) * 100
    data["return_20d"] = data["Close"].pct_change(20) * 100
    return data


def add_indicators(data: pd.DataFrame):
    data = data.copy()

    data = add_sma(data, 20)
    data = add_sma(data, 50)
    data = add_rsi(data, 14)
    data = add_volume_ratio(data, 20)
    data = add_returns(data)

    return data


def get_latest_indicators(symbol: str):
    data = get_price_history(symbol)
    data = add_indicators(data)

    latest = data.iloc[-1]

    return {
        "symbol": symbol.upper(),
        "price": round(float(latest["Close"]), 2),
        "sma_20": round(float(latest["SMA_20"]), 2),
        "sma_50": round(float(latest["SMA_50"]), 2),
        "rsi_14": round(float(latest["RSI_14"]), 2),
        "volume_ratio": round(float(latest["volume_ratio"]), 2),
        "return_5d": round(float(latest["return_5d"]), 2),
        "return_20d": round(float(latest["return_20d"]), 2),
    }


if __name__ == "__main__":
    print(get_latest_indicators("NVDA"))