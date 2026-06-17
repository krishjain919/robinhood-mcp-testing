from rh_client import get_account, get_last_price
from risk import get_max_trade_dollars, validate_buy_order
from sentiment import aggregate_scores


def create_trade_plan():
    """
    Turns the manual signals into a tiny trade plan.

    This does NOT place trades. It just tells me what the bot would consider buying.
    """

    account = get_account()
    signals = aggregate_scores()

    trade_ideas = []

    for signal in signals:
        symbol = signal["symbol"]
        score = signal["total_score"]

        # Keeping this simple: only positive scores become trade ideas.
        if score <= 0:
            continue

        dollars = get_max_trade_dollars()

        try:
            validate_buy_order(account, symbol, dollars)
            last_price = get_last_price(symbol)

            trade_ideas.append({
                "symbol": symbol,
                "action": "BUY",
                "dollars": dollars,
                "last_price": last_price,
                "sentiment_score": score,
                "signal_count": signal["signal_count"],
                "reason": (
                    f"Positive sentiment score of {score} "
                    f"from {signal['signal_count']} signal(s)."
                ),
            })

        except Exception as error:
            trade_ideas.append({
                "symbol": symbol,
                "action": "BLOCKED",
                "sentiment_score": score,
                "reason": str(error),
            })

    return trade_ideas


if __name__ == "__main__":
    # Quick local test:
    # cp signals.example.csv signals.csv
    # python trade_planner.py

    plan = create_trade_plan()

    for idea in plan:
        print(idea)