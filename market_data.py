import yfinance as yf


def get_price_history(symbol: str, period: str = "6mo", interval: str = "1d"):
    """
    Pulls candle data for a ticker.

    Keeping this as yfinance for now because it is simple and good enough
    for testing swing trade logic.
    """

    symbol = symbol.upper().strip()

    data = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
    )

    if data.empty:
        raise ValueError(f"No price history found for {symbol}")

    data = data.reset_index()

    # yfinance can sometimes return weird multi-index columns, so flatten if needed.
    data.columns = [
        col[0] if isinstance(col, tuple) else col
        for col in data.columns
    ]

    return data


def get_latest_price(symbol: str) -> float:
    data = get_price_history(symbol, period="5d", interval="1d")
    return float(data["Close"].iloc[-1])


if __name__ == "__main__":
    df = get_price_history("NVDA")
    print(df.tail())
    print("Latest price:", get_latest_price("NVDA"))