"""
The daily decision pipeline.

This is the conductor. It runs the layers in order and never lets a later,
softer layer override an earlier, harder one:

    1. Market regime gate   -> is it even safe to be long? (SPY vs 200DMA)
    2. Quant screen         -> which charts are valid swing setups?
    3. Research dossier      -> gather earnings, news, price-action context.
    4. AI judgment           -> confirm / caution / veto the qualitative case.
    5. Risk engine           -> ATR stops + position size within heat limits.

The output is a ranked, fully-sized trade plan with a written rationale for
every name — and an explicit status (ACTIONABLE / WATCH / VETOED / ...) so it
is always clear *why* something is or isn't a trade today.
"""

import config
from market_data import get_price_history
from technical_indicators import add_indicators, get_latest_indicators
from strategy import score_technical_setup, classify_score
from watchlist import get_core_watchlist
from dossier import build_dossier
from ai_agent import judge
from risk_engine import compute_trade_levels, portfolio_heat, can_add_position

DEFAULT_EQUITY = 10_000.0

# Don't run the AI over an unbounded universe — cap how many buy candidates we
# deeply evaluate per scan (each one costs a model call + data fetches).
MAX_AI_EVALUATIONS = 8


def regime_check(market: str = "SPY") -> dict:
    """Is the broad market in a risk-on regime? Long swing setups only earn
    their edge when it is."""

    try:
        data = get_price_history(market, period="2y", interval="1d")
        data = add_indicators(data)
        latest = data.iloc[-1]
    except Exception as error:
        return {"market": market, "risk_on": False, "error": str(error),
                "note": "Could not load market data; treating regime as risk-off."}

    price = float(latest["Close"])
    sma_50 = float(latest["SMA_50"])
    sma_200 = float(latest["SMA_200"])
    return_20d = float(latest["return_20d"])

    reasons = []
    risk_on = True

    if price < sma_200:
        risk_on = False
        reasons.append("SPY is below its 200-day moving average (downtrend).")
    else:
        reasons.append("SPY is above its 200-day moving average.")

    if sma_50 < sma_200:
        risk_on = False
        reasons.append("50-day MA is below the 200-day MA (death-cross territory).")

    if return_20d < -7.5:
        risk_on = False
        reasons.append(f"SPY is down {return_20d:.1f}% over 20 days (sharp selloff).")

    return {
        "market": market,
        "risk_on": risk_on,
        "price": round(price, 2),
        "sma_50": round(sma_50, 2),
        "sma_200": round(sma_200, 2),
        "return_20d": round(return_20d, 2),
        "reasons": reasons,
        "note": "Risk-on: full swing scanning enabled."
        if risk_on
        else "Risk-off: hold cash; setups are flagged as WATCH only.",
    }


def _screen_universe(watchlist: list[str]) -> list[dict]:
    """Run the cheap, deterministic quant screen over the whole watchlist."""

    rows = []
    for symbol in watchlist:
        try:
            ind = get_latest_indicators(symbol)
        except Exception as error:
            rows.append({"symbol": symbol.upper(), "error": str(error)})
            continue

        score, reasons = score_technical_setup(ind)
        rows.append({
            "symbol": symbol.upper(),
            "price": ind.get("price"),
            "score": score,
            "decision": classify_score(score),
            "reasons": reasons,
            "indicators": ind,
        })

    scored = [r for r in rows if "error" not in r]
    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored


def scan(
    watchlist: list[str] | None = None,
    equity: float = DEFAULT_EQUITY,
    top_n: int = config.MAX_POSITIONS,
    use_ai: bool = True,
) -> dict:
    """Full pipeline. Returns the regime read plus a ranked, sized trade plan."""

    watchlist = watchlist or get_core_watchlist()
    regime = regime_check()

    screened = _screen_universe(watchlist)
    watch = [r for r in screened if r["score"] >= config.MIN_WATCH_SCORE]
    buy_candidates = [r for r in screened if r["score"] >= config.MIN_BUY_SCORE]

    plan = []
    open_risk: list[float] = []
    actionable_count = 0

    for row in buy_candidates[:MAX_AI_EVALUATIONS]:
        symbol = row["symbol"]
        ind = row["indicators"]

        dossier = build_dossier(symbol, indicators=ind)
        verdict = judge(dossier) if use_ai else {
            "source": "disabled", "verdict": "CONFIRM", "conviction": 1.0,
            "tradeable": True, "sentiment": "NEUTRAL", "event_risk": "LOW",
            "catalyst": None, "thesis": "AI layer disabled for this scan.",
            "key_risks": [],
        }

        levels = compute_trade_levels(
            entry_price=ind["price"],
            atr=ind.get("atr_14", 0.0),
            equity=equity,
            conviction=verdict["conviction"],
        )

        # Decide the status, hardest constraint first.
        if not regime["risk_on"]:
            status = "REGIME_OFF"
        elif not verdict["tradeable"]:
            status = "VETOED"
        elif levels.shares <= 0:
            status = "SIZE_ZERO"
        elif actionable_count >= top_n:
            status = "POSITION_CAP"
        elif not can_add_position(
            portfolio_heat(open_risk, equity), levels.risk_pct_of_equity
        ):
            status = "HEAT_CAP"
        else:
            status = "ACTIONABLE"
            open_risk.append(levels.risk_dollars)
            actionable_count += 1

        plan.append({
            "symbol": symbol,
            "status": status,
            "technical_score": row["score"],
            "decision": row["decision"],
            "ai": {
                "source": verdict["source"],
                "verdict": verdict["verdict"],
                "conviction": verdict["conviction"],
                "sentiment": verdict["sentiment"],
                "event_risk": verdict["event_risk"],
                "catalyst": verdict["catalyst"],
                "thesis": verdict["thesis"],
                "key_risks": verdict["key_risks"],
            },
            "earnings": dossier["earnings"],
            "trade": levels.to_dict(),
        })

    return {
        "regime": regime,
        "equity": equity,
        "config": config.summary(),
        "universe_size": len(watchlist),
        "watchlist_passing_screen": [
            {"symbol": r["symbol"], "score": r["score"], "decision": r["decision"]}
            for r in watch
        ],
        "plan": plan,
        "portfolio_heat_pct": portfolio_heat(open_risk, equity),
        "actionable_count": actionable_count,
    }


if __name__ == "__main__":
    import json

    result = scan(use_ai=False)  # cheap dry run without spending tokens
    print(json.dumps(result["regime"], indent=2))
    print(f"\nActionable: {result['actionable_count']}  "
          f"Heat: {result['portfolio_heat_pct']}%\n")
    for item in result["plan"]:
        print(f"{item['symbol']:6}  {item['status']:12}  "
              f"score={item['technical_score']:>3}  "
              f"shares={item['trade']['shares']:>4}  "
              f"stop={item['trade']['stop_price']}  "
              f"target={item['trade']['target_price']}")
