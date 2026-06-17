import os
import robin_stocks.robinhood as rh
from dotenv import load_dotenv

load_dotenv()

_logged_in = False


def login():
    global _logged_in

    if _logged_in:
        return True

    username = os.getenv("RH_USERNAME")
    password = os.getenv("RH_PASSWORD")

    if not username or not password:
        raise ValueError("Missing RH_USERNAME or RH_PASSWORD in .env")

    rh.login(
        username=username,
        password=password,
        store_session=True
    )

    _logged_in = True
    return True


def get_account():
    login()
    return rh.profiles.load_account_profile()


def get_portfolio():
    login()
    return rh.profiles.load_portfolio_profile()


def get_holdings():
    login()
    return rh.account.build_holdings()


def get_quote(symbol: str):
    login()
    symbol = symbol.upper()
    quotes = rh.stocks.get_quotes(symbol)

    if not quotes:
        raise ValueError(f"No quote found for {symbol}")

    return quotes[0]


def get_last_price(symbol: str) -> float:
    quote = get_quote(symbol)
    return float(quote["last_trade_price"])