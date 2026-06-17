import os
from dotenv import load_dotenv

load_dotenv()


def get_max_trade_dollars() -> float:
    # Keeping this tiny while I test so one bug doesn't nuke my account.
    return float(os.getenv("MAX_TRADE_DOLLARS", "5"))


def is_live_trading_enabled() -> bool:
    # I kept the default false so I do not accidentally submit actual orders when testing.
    return os.getenv("ALLOW_LIVE_TRADING", "false").lower() == "true"


def validate_buy_order(account: dict, symbol: str, dollars: float):
    """
    Basic guardrails before a buy order.

    This is not supposed to be smart yet. It is just here to stop dumb mistakes.
    """

    symbol = symbol.upper()
    cash = float(account.get("cash", 0))
    max_trade_dollars = get_max_trade_dollars()

    if dollars <= 0:
        raise ValueError("Trade amount must be greater than zero.")

    if dollars > max_trade_dollars:
        raise ValueError(
            f"Trade blocked: ${dollars} is above my test limit of ${max_trade_dollars}."
        )

    # LOOK HERE!!!!
    # Robinhood buying_power can include margin. I only want this bot using real cash.
    if dollars > cash:
        raise ValueError(
            f"Trade blocked: ${dollars} is above available cash of ${cash}."
        )

    # Not touching leveraged/inverse stuff while testing this.
    blocked_symbols = {"TQQQ", "SQQQ", "SOXL", "UVXY"}

    if symbol in blocked_symbols:
        raise ValueError(f"Trade blocked: {symbol} is restricted in this project.")

    return True