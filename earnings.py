"""
Earnings / binary-event awareness.

Holding a swing trade through an earnings report turns a risk-managed setup
into a coin flip — the stock can gap straight past your stop overnight. So the
bot treats an upcoming earnings date as a hard blackout: it won't open a new
swing position inside the window, and it flags any open position that is
heading into one.

yfinance is the data source. It can be flaky, so every lookup is wrapped and
degrades gracefully (unknown date -> we simply don't block, but we say so).
"""

from datetime import date, datetime

import yfinance as yf

import config

# Tiny in-process cache so a scan over a watchlist doesn't hammer the network.
_cache: dict[str, date | None] = {}


def _coerce_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except Exception:
        return None


def get_next_earnings_date(symbol: str) -> date | None:
    """
    Best-effort next scheduled earnings date, or None if unknown.

    Tries the structured earnings-dates table first, then the calendar.
    """

    symbol = symbol.upper().strip()
    if symbol in _cache:
        return _cache[symbol]

    today = date.today()
    result: date | None = None

    try:
        ticker = yf.Ticker(symbol)

        # Preferred: the earnings-dates table (future rows included).
        try:
            table = ticker.get_earnings_dates(limit=12)
            if table is not None and not table.empty:
                upcoming = [
                    d.date() if hasattr(d, "date") else d
                    for d in table.index.to_pydatetime()
                ]
                future = sorted(d for d in upcoming if d >= today)
                if future:
                    result = future[0]
        except Exception:
            pass

        # Fallback: the calendar object.
        if result is None:
            calendar = ticker.calendar
            raw = None
            if isinstance(calendar, dict):
                raw = calendar.get("Earnings Date")
                if isinstance(raw, (list, tuple)) and raw:
                    raw = raw[0]
            elif calendar is not None and hasattr(calendar, "loc"):
                try:
                    raw = calendar.loc["Earnings Date"][0]
                except Exception:
                    raw = None
            result = _coerce_date(raw)
            if result is not None and result < today:
                result = None
    except Exception:
        result = None

    _cache[symbol] = result
    return result


def days_until_earnings(symbol: str, as_of: date | None = None) -> int | None:
    """Calendar days until the next earnings date, or None if unknown."""
    next_date = get_next_earnings_date(symbol)
    if next_date is None:
        return None
    as_of = as_of or date.today()
    return (next_date - as_of).days


def earnings_check(symbol: str, as_of: date | None = None) -> dict:
    """
    Structured verdict the rest of the system can act on.

    `blocked` is True only when we KNOW earnings fall inside the blackout
    window. Unknown dates do not block (we flag the uncertainty instead).
    """

    next_date = get_next_earnings_date(symbol)
    days = days_until_earnings(symbol, as_of)
    blackout = config.EARNINGS_BLACKOUT_DAYS

    if next_date is None:
        return {
            "symbol": symbol.upper(),
            "next_earnings_date": None,
            "days_until": None,
            "blocked": False,
            "note": "Earnings date unknown — proceed but confirm manually.",
        }

    blocked = days is not None and 0 <= days <= blackout
    if blocked:
        note = (
            f"Earnings in {days} day(s) (<= {blackout}-day blackout). "
            f"No new swing entries; exit open positions before the report."
        )
    else:
        note = f"Next earnings in {days} day(s) — outside the blackout window."

    return {
        "symbol": symbol.upper(),
        "next_earnings_date": next_date.isoformat(),
        "days_until": days,
        "blocked": blocked,
        "note": note,
    }


if __name__ == "__main__":
    import json

    for sym in ["NVDA", "AAPL", "TSLA"]:
        print(json.dumps(earnings_check(sym), indent=2))
