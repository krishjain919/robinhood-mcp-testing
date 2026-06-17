import pandas as pd

# Super basic for now.
# Later I want this to use actual X/Twitter data, but a CSV is easier to test first.
BULLISH_WORDS = [
    "buy",
    "long",
    "bullish",
    "breakout",
    "undervalued",
    "accumulate",
    "strong",
    "upside",
    "beat",
]

BEARISH_WORDS = [
    "sell",
    "short",
    "bearish",
    "overvalued",
    "dump",
    "weak",
    "downside",
    "miss",
    "avoid",
]


def score_text(text: str) -> int:
    """
    Very rough sentiment score.

    Not trying to make this perfect yet. Just want enough to test the pipeline.
    """

    text = text.lower()
    score = 0

    for word in BULLISH_WORDS:
        if word in text:
            score += 1

    for word in BEARISH_WORDS:
        if word in text:
            score -= 1

    return score


def load_signal_scores(csv_path: str = "signals.csv"):
    """
    Reads my manual signal CSV.

    Expected columns:
    source,symbol,text
    """

    df = pd.read_csv(csv_path)

    required_columns = {"source", "symbol", "text"}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(f"Missing columns in signals CSV: {missing_columns}")

    signals = []

    for _, row in df.iterrows():
        source = str(row["source"]).strip()
        symbol = str(row["symbol"]).upper().strip()
        text = str(row["text"])

        signals.append({
            "source": source,
            "symbol": symbol,
            "text": text,
            "score": score_text(text),
        })

    return signals


def aggregate_scores(csv_path: str = "signals.csv"):
    """
    Groups scores by ticker.

    Example: 3 bullish NVDA signals should matter more than 1 random NVDA signal.
    """

    signals = load_signal_scores(csv_path)
    scores_by_symbol = {}

    for signal in signals:
        symbol = signal["symbol"]

        if symbol not in scores_by_symbol:
            scores_by_symbol[symbol] = {
                "symbol": symbol,
                "total_score": 0,
                "signal_count": 0,
                "sources": [],
            }

        scores_by_symbol[symbol]["total_score"] += signal["score"]
        scores_by_symbol[symbol]["signal_count"] += 1
        scores_by_symbol[symbol]["sources"].append(signal["source"])

    return list(scores_by_symbol.values())