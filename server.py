from fastmcp import FastMCP

from rh_client import get_account, get_portfolio, get_holdings
from trade_planner import create_trade_plan

mcp = FastMCP("Robinhood Trading MCP")


@mcp.tool()
def robinhood_account_summary():
    """
    Basic account summary.

    I return buying power too, but I do not want to use it for trade sizing
    because it can include margin.
    """

    account = get_account()
    portfolio = get_portfolio()

    return {
        "cash": account.get("cash"),
        "buying_power": account.get("buying_power"),
        "portfolio_equity": portfolio.get("equity"),
        "note": "Use cash, not buying power, so margin does not get touched."
    }


@mcp.tool()
def robinhood_holdings():
    """Return my current Robinhood holdings."""
    return get_holdings()


@mcp.tool()
def generate_trade_plan():
    """
    Generate a simple trade plan from manual sentiment signals.

    Still just planning. No real orders here.
    """

    return create_trade_plan()


if __name__ == "__main__":
    mcp.run()