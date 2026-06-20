CORE_SWING_WATCHLIST = [
    "AAPL",
    "MSFT",
    "NVDA",
    "AMD",
    "AVGO",
    "META",
    "GOOGL",
    "AMZN",
    "TSLA",
    "NFLX",
    "PLTR",
    "HOOD",
    "ORCL",
    "DDOG",
    "CRWD",
    "NET",
    "SNOW",
    "SHOP",
    "COIN",
    "MSTR",
    "QQQ",
    "SPY",
]


SPECULATIVE_WATCHLIST = [
    "ASST",
    "BMNR",
    "NBIS",
]


def get_core_watchlist():
    """
    Liquid names first.

    Keeping tiny/speculative stuff separate because small caps can make a
    backtest look weird if the data is messy or the stock barely traded before.
    """

    return CORE_SWING_WATCHLIST.copy()


def get_speculative_watchlist():
    return SPECULATIVE_WATCHLIST.copy()


if __name__ == "__main__":
    print(get_core_watchlist())