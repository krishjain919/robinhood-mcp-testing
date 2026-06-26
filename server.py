"""
MCP server — the interface an AI assistant (or you, via an MCP client) uses to
drive the swing trading bot.

The tools mirror the pipeline: check the regime, scan for setups, analyze one
name deeply (with the AI layer), and log/track paper trades. Account-read tools
are kept too. Nothing here places a real order — execution stays manual on
purpose.
"""

from fastmcp import FastMCP

import config
from rh_client import get_account, get_portfolio, get_holdings
from trade_planner import create_trade_plan
from screener import scan, regime_check, DEFAULT_EQUITY
from dossier import build_dossier
from ai_agent import judge
from risk_engine import compute_trade_levels
import paper_trades

mcp = FastMCP("Robinhood Swing Trading MCP")


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------
@mcp.tool()
def robinhood_account_summary():
    """Account cash/equity. Cash (not buying power) is what the bot sizes from,
    so margin never gets touched."""
    account = get_account()
    portfolio = get_portfolio()
    return {
        "cash": account.get("cash"),
        "buying_power": account.get("buying_power"),
        "portfolio_equity": portfolio.get("equity"),
        "note": "Use cash, not buying power, so margin does not get touched.",
    }


@mcp.tool()
def robinhood_holdings():
    """Current Robinhood holdings."""
    return get_holdings()


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------
@mcp.tool()
def market_regime():
    """Is the broad market (SPY) in a risk-on regime? Long swing setups only
    earn their edge above the 200-day moving average."""
    return regime_check()


@mcp.tool()
def scan_swing_candidates(equity: float = DEFAULT_EQUITY, top_n: int = config.MAX_POSITIONS,
                          use_ai: bool = True):
    """Run the full pipeline: regime gate -> technical screen -> research
    dossier -> AI judgment -> ATR risk sizing. Returns a ranked, fully-sized
    trade plan with a written rationale and a status for every name."""
    return scan(equity=equity, top_n=top_n, use_ai=use_ai)


@mcp.tool()
def analyze_symbol_deep(symbol: str, equity: float = DEFAULT_EQUITY):
    """Deep-dive one ticker: technical score, research dossier, AI confirm/
    veto/size-down judgment, and the exact ATR-based stop, target, and share
    size it implies."""
    dossier = build_dossier(symbol)
    verdict = judge(dossier)
    ind = dossier["indicators"]
    levels = compute_trade_levels(
        entry_price=ind["price"],
        atr=ind.get("atr_14", 0.0),
        equity=equity,
        conviction=verdict["conviction"],
    )
    return {
        "symbol": dossier["symbol"],
        "technical": dossier["technical"],
        "narrative": dossier["narrative"],
        "earnings": dossier["earnings"],
        "news": dossier["news"],
        "ai_judgment": verdict,
        "trade_levels": levels.to_dict(),
    }


@mcp.tool()
def config_summary():
    """Current risk/AI configuration the bot is running with."""
    return config.summary()


@mcp.tool()
def generate_trade_plan():
    """Legacy: simple trade plan from the manual sentiment CSV. Kept for
    backward compatibility; prefer scan_swing_candidates."""
    return create_trade_plan()


# ---------------------------------------------------------------------------
# Paper trading
# ---------------------------------------------------------------------------
@mcp.tool()
def paper_open_trade(symbol: str, entry_price: float, stop_price: float,
                     target_price: float, shares: int, thesis: str = ""):
    """Log a simulated entry to the paper-trading ledger."""
    return paper_trades.open_trade(symbol, entry_price, stop_price, target_price,
                                   shares, thesis=thesis)


@mcp.tool()
def paper_close_trade(trade_id: str, exit_price: float, reason: str = "manual"):
    """Close a simulated trade and record realized P&L (dollars, %, and R)."""
    return paper_trades.close_trade(trade_id, exit_price, reason)


@mcp.tool()
def paper_list_trades(status: str = ""):
    """List paper trades, optionally filtered by OPEN or CLOSED."""
    return paper_trades.list_trades(status or None)


@mcp.tool()
def paper_performance():
    """Win rate, profit factor, expectancy (R), and total P&L over closed
    paper trades."""
    return paper_trades.performance()


if __name__ == "__main__":
    mcp.run()
