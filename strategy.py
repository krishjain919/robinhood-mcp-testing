from technical_indicators import get_latest_indicators


def score_technical_setup(indicators: dict):
    """
    Scores a ticker from 0-100 based on simple swing trade rules.

    This is the first rough version. The goal is to create a ranking system,
    not some perfect prediction machine.
    """

    score = 0
    reasons = []

    price = indicators["price"]
    sma_20 = indicators["sma_20"]
    sma_50 = indicators["sma_50"]
    rsi = indicators["rsi_14"]
    volume_ratio = indicators["volume_ratio"]
    return_5d = indicators["return_5d"]
    return_20d = indicators["return_20d"]

    if price > sma_20:
        score += 20
        reasons.append("price is above the 20-day moving average")
    else:
        reasons.append("price is below the 20-day moving average")

    if sma_20 > sma_50:
        score += 20
        reasons.append("20-day moving average is above the 50-day moving average")
    else:
        reasons.append("20-day moving average is not above the 50-day moving average")

    if 45 <= rsi <= 70:
        score += 20
        reasons.append("RSI is in a decent swing trading range")
    elif rsi > 70:
        score += 5
        reasons.append("RSI is high, so this might be stretched")
    else:
        reasons.append("RSI is weak")

    if volume_ratio >= 1.1:
        score += 15
        reasons.append("volume is above average")
    else:
        reasons.append("volume is not confirming yet")

    if return_5d > 0:
        score += 10
        reasons.append("5-day return is positive")

    if return_20d > 0:
        score += 15
        reasons.append("20-day return is positive")

    return min(score, 100), reasons


def classify_score(score: int):
    if score >= 75:
        return "BUY_CANDIDATE"

    if score >= 50:
        return "WATCH"

    return "IGNORE"


def analyze_symbol(symbol: str):
    indicators = get_latest_indicators(symbol)
    score, reasons = score_technical_setup(indicators)

    return {
        "symbol": symbol.upper(),
        "decision": classify_score(score),
        "technical_score": score,
        "indicators": indicators,
        "reasons": reasons,
    }


if __name__ == "__main__":
    symbols = ["NVDA", "PLTR", "TSLA", "META", "VOO","ASST"]

    for symbol in symbols:
        result = analyze_symbol(symbol)

        print("\n" + symbol)
        print("Decision:", result["decision"])
        print("Score:", result["technical_score"])
        print("Price:", result["indicators"]["price"])

        for reason in result["reasons"]:
            print("-", reason)