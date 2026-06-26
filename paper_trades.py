"""
Paper-trading ledger.

Before risking a cent of real money, the bot logs every trade idea it would
have taken to a local JSON ledger, then tracks how those trades actually play
out. This is how you find out whether the strategy works on *your* universe in
*current* conditions — the part backtests can't tell you, because the AI layer
can't be replayed historically.

Stores realized P&L in R-multiples (profit/loss as a multiple of the dollar
risked), which is the honest way to measure a risk-based strategy.
"""

import json
import os
from datetime import datetime, timezone

LEDGER_PATH = os.path.join(os.path.dirname(__file__), "paper_trades.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load() -> list[dict]:
    if not os.path.exists(LEDGER_PATH):
        return []
    try:
        with open(LEDGER_PATH, "r") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return []


def _save(trades: list[dict]) -> None:
    with open(LEDGER_PATH, "w") as fh:
        json.dump(trades, fh, indent=2)


def open_trade(
    symbol: str,
    entry_price: float,
    stop_price: float,
    target_price: float,
    shares: int,
    thesis: str = "",
    source: str = "screener",
) -> dict:
    """Record a new simulated entry."""

    trades = _load()
    risk_per_share = max(0.01, entry_price - stop_price)

    trade = {
        "id": f"{symbol.upper()}-{int(datetime.now(timezone.utc).timestamp())}",
        "symbol": symbol.upper(),
        "status": "OPEN",
        "opened_at": _now(),
        "entry_price": round(entry_price, 2),
        "stop_price": round(stop_price, 2),
        "target_price": round(target_price, 2),
        "shares": int(shares),
        "risk_per_share": round(risk_per_share, 2),
        "risk_dollars": round(risk_per_share * shares, 2),
        "thesis": thesis,
        "source": source,
        "closed_at": None,
        "exit_price": None,
        "exit_reason": None,
        "pnl_dollars": None,
        "pnl_pct": None,
        "r_multiple": None,
    }

    trades.append(trade)
    _save(trades)
    return trade


def close_trade(trade_id: str, exit_price: float, reason: str = "manual") -> dict:
    """Close an open trade and compute realized P&L in dollars, percent, and R."""

    trades = _load()
    for trade in trades:
        if trade["id"] == trade_id and trade["status"] == "OPEN":
            shares = trade["shares"]
            entry = trade["entry_price"]
            pnl_dollars = (exit_price - entry) * shares
            pnl_pct = ((exit_price / entry) - 1) * 100 if entry else 0
            r_multiple = (
                (exit_price - entry) / trade["risk_per_share"]
                if trade["risk_per_share"]
                else 0
            )

            trade.update({
                "status": "CLOSED",
                "closed_at": _now(),
                "exit_price": round(exit_price, 2),
                "exit_reason": reason,
                "pnl_dollars": round(pnl_dollars, 2),
                "pnl_pct": round(pnl_pct, 2),
                "r_multiple": round(r_multiple, 2),
            })
            _save(trades)
            return trade

    raise ValueError(f"No open trade with id {trade_id}")


def list_trades(status: str | None = None) -> list[dict]:
    trades = _load()
    if status:
        return [t for t in trades if t["status"] == status.upper()]
    return trades


def performance() -> dict:
    """Summary stats over all closed paper trades."""

    closed = [t for t in _load() if t["status"] == "CLOSED"]
    if not closed:
        return {"closed_trades": 0, "note": "No closed paper trades yet."}

    wins = [t for t in closed if t["pnl_dollars"] > 0]
    losses = [t for t in closed if t["pnl_dollars"] <= 0]

    gross_win = sum(t["pnl_dollars"] for t in wins)
    gross_loss = abs(sum(t["pnl_dollars"] for t in losses))

    avg_win = gross_win / len(wins) if wins else 0
    avg_loss = gross_loss / len(losses) if losses else 0
    profit_factor = (gross_win / gross_loss) if gross_loss else float("inf")
    avg_r = sum(t["r_multiple"] for t in closed) / len(closed)

    return {
        "closed_trades": len(closed),
        "open_trades": len(list_trades("OPEN")),
        "win_rate_pct": round(len(wins) / len(closed) * 100, 1),
        "avg_win_dollars": round(avg_win, 2),
        "avg_loss_dollars": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else "inf",
        "expectancy_r": round(avg_r, 2),
        "total_pnl_dollars": round(sum(t["pnl_dollars"] for t in closed), 2),
    }


if __name__ == "__main__":
    print(json.dumps(performance(), indent=2))
