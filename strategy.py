from technical_indicators import get_latest_indicators


def get_value(indicators: dict, *keys, default=0):
    for key in keys:
        if key in indicators:
            return indicators[key]

    return default


def score_technical_setup(indicators: dict):
    """
    Scores a ticker from 0-100.

    This version is more like a real swing trading filter:
    trend first, then relative strength, then breakout/volume, then risk quality.
    """

    score = 0
    reasons = []

    price = get_value(indicators, "price", "Close")
    sma_20 = get_value(indicators, "sma_20", "SMA_20")
    sma_50 = get_value(indicators, "sma_50", "SMA_50")
    sma_150 = get_value(indicators, "sma_150", "SMA_150")
    sma_200 = get_value(indicators, "sma_200", "SMA_200")

    rsi = get_value(indicators, "rsi_14", "RSI_14")
    volume_ratio = get_value(indicators, "volume_ratio")
    return_20d = get_value(indicators, "return_20d")
    relative_strength = get_value(indicators, "relative_strength_63d")
    breakout_20d = get_value(indicators, "breakout_20d")
    pct_below_52w_high = get_value(indicators, "pct_below_52w_high")
    pct_above_52w_low = get_value(indicators, "pct_above_52w_low")

    # Trend template: 40 points
    if price > sma_50:
        score += 8
        reasons.append("price is above SMA50")

    if price > sma_200:
        score += 8
        reasons.append("price is above SMA200")

    if sma_50 > sma_150:
        score += 8
        reasons.append("SMA50 is above SMA150")

    if sma_150 > sma_200:
        score += 8
        reasons.append("SMA150 is above SMA200")

    if pct_below_52w_high >= -25:
        score += 8
        reasons.append("price is within 25% of 52-week high")

    # Relative strength: 25 points
    if relative_strength >= 10:
        score += 25
        reasons.append("very strong 3-month relative strength vs SPY")
    elif relative_strength >= 5:
        score += 20
        reasons.append("strong 3-month relative strength vs SPY")
    elif relative_strength > 0:
        score += 15
        reasons.append("positive 3-month relative strength vs SPY")
    else:
        reasons.append("weak relative strength vs SPY")

    # Breakout and volume: 20 points
    if breakout_20d:
        score += 10
        reasons.append("breaking above recent 20-day high")

    if volume_ratio >= 1.5:
        score += 10
        reasons.append("volume is very strong")
    elif volume_ratio >= 1.2:
        score += 7
        reasons.append("volume is above average")
    elif volume_ratio >= 1.0:
        score += 4
        reasons.append("volume is normal")
    else:
        reasons.append("volume is weak")

    # Risk quality: 15 points
    if 45 <= rsi <= 70:
        score += 8
        reasons.append("RSI is in a good swing range")
    elif 70 < rsi <= 78:
        score += 4
        reasons.append("RSI is high but not insane")
    else:
        reasons.append("RSI is not ideal")

    if return_20d > 0:
        score += 4
        reasons.append("20-day return is positive")

    if pct_above_52w_low >= 30:
        score += 3
        reasons.append("price is well above 52-week low")

    return min(round(score, 2), 100), reasons


def classify_score(score: int):
    if score >= 75:
        return "BUY_CANDIDATE"

    if score >= 55:
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
    symbols = ["NVDA", "PLTR", "TSLA", "META", "HOOD", "QQQ"]

    for symbol in symbols:
        result = analyze_symbol(symbol)

        print("\n" + symbol)
        print("Decision:", result["decision"])
        print("Score:", result["technical_score"])
        print("Price:", result["indicators"]["price"])

        for reason in result["reasons"]:
            print("-", reason)