"""
Research dossier builder.

The quant screen tells us a chart is technically valid. Before risking money,
an AI agent gets a structured "dossier" on the name — indicators, earnings
timing, recent news, a plain-English read of the price action — and decides
whether the qualitative picture supports the trade.

Everything here is best-effort and degrades gracefully: if news or company
info can't be fetched, the dossier still builds with what we have.
"""

from datetime import datetime, timezone

import yfinance as yf

from technical_indicators import get_latest_indicators
from strategy import score_technical_setup, classify_score
from earnings import earnings_check


def _recent_news(symbol: str, limit: int = 6) -> list[dict]:
    """Recent headlines for the ticker, normalized across yfinance versions."""
    try:
        raw = yf.Ticker(symbol).news or []
    except Exception:
        return []

    headlines = []
    for item in raw[:limit]:
        # Newer yfinance nests everything under "content"; older is flat.
        content = item.get("content", item) if isinstance(item, dict) else {}
        title = content.get("title") or item.get("title")
        if not title:
            continue

        publisher = (
            content.get("provider", {}).get("displayName")
            if isinstance(content.get("provider"), dict)
            else item.get("publisher")
        )
        published = content.get("pubDate") or item.get("providerPublishTime")
        if isinstance(published, (int, float)):
            published = datetime.fromtimestamp(published, tz=timezone.utc).date().isoformat()

        headlines.append({
            "title": str(title).strip(),
            "publisher": publisher,
            "published": str(published) if published else None,
        })

    return headlines


def _company_profile(symbol: str) -> dict:
    try:
        info = yf.Ticker(symbol).info or {}
    except Exception:
        info = {}

    return {
        "name": info.get("shortName") or info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": info.get("marketCap"),
    }


def price_action_narrative(ind: dict) -> str:
    """Deterministic plain-English read of the chart, so the AI isn't guessing
    what the numbers mean."""

    parts = []

    price = ind.get("price", 0)
    if price > ind.get("sma_50", 0) and price > ind.get("sma_200", 0):
        parts.append("Price is above both its 50- and 200-day moving averages (Stage 2 uptrend).")
    elif price < ind.get("sma_200", 0):
        parts.append("Price is below its 200-day moving average (broken long-term trend).")
    else:
        parts.append("Price is in a mixed position relative to its long-term averages.")

    rs = ind.get("relative_strength_63d", 0)
    if rs > 5:
        parts.append(f"It is outperforming SPY over 3 months by {rs:.1f}%.")
    elif rs < 0:
        parts.append(f"It is lagging SPY over 3 months by {abs(rs):.1f}%.")

    rsi = ind.get("rsi_14", 0)
    if rsi >= 80:
        parts.append(f"RSI is very hot at {rsi:.0f} (extended/overbought).")
    elif rsi >= 70:
        parts.append(f"RSI is elevated at {rsi:.0f}.")
    elif rsi <= 35:
        parts.append(f"RSI is weak at {rsi:.0f}.")

    dist = ind.get("dist_sma_20_pct", 0)
    if dist >= 12:
        parts.append(f"Price is stretched {dist:.0f}% above its 20-day average (chase risk).")

    adx = ind.get("adx_14", 0)
    if adx >= 25:
        parts.append(f"ADX is {adx:.0f}, confirming a strong trend in motion.")
    elif adx and adx < 18:
        parts.append(f"ADX is only {adx:.0f}, suggesting choppy/rangebound action.")

    if ind.get("macd_hist", 0) > 0:
        parts.append("MACD histogram is positive (momentum building).")
    else:
        parts.append("MACD histogram is negative (momentum fading).")

    if ind.get("breakout_20d"):
        parts.append("Price just broke above its prior 20-day high.")

    parts.append(
        f"It sits {ind.get('pct_below_52w_high', 0):.0f}% from its 52-week high "
        f"and {ind.get('pct_above_52w_low', 0):.0f}% above its 52-week low. "
        f"Daily volatility (ATR) is ~{ind.get('atr_pct', 0):.1f}% of price."
    )

    return " ".join(parts)


def build_dossier(symbol: str, indicators: dict | None = None) -> dict:
    """Assemble the full research packet for one ticker."""

    symbol = symbol.upper().strip()
    ind = indicators or get_latest_indicators(symbol)
    score, reasons = score_technical_setup(ind)

    return {
        "symbol": symbol,
        "profile": _company_profile(symbol),
        "technical": {
            "score": score,
            "decision": classify_score(score),
            "reasons": reasons,
        },
        "indicators": ind,
        "narrative": price_action_narrative(ind),
        "earnings": earnings_check(symbol),
        "news": _recent_news(symbol),
        "generated_at": None,  # stamped by the caller if needed
    }


if __name__ == "__main__":
    import json

    print(json.dumps(build_dossier("NVDA"), indent=2, default=str))
