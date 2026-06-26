"""Technical scoring and classification."""

from strategy import score_technical_setup, classify_score


STRONG = {
    "price": 110, "sma_20": 105, "sma_50": 100, "sma_150": 90, "sma_200": 85,
    "rsi_14": 60, "volume_ratio": 1.6, "return_20d": 8,
    "relative_strength_63d": 12, "breakout_20d": True,
    "pct_below_52w_high": -5, "pct_above_52w_low": 40,
}

WEAK = {
    "price": 80, "sma_20": 85, "sma_50": 90, "sma_150": 95, "sma_200": 100,
    "rsi_14": 40, "volume_ratio": 0.5, "return_20d": -5,
    "relative_strength_63d": -8, "breakout_20d": False,
    "pct_below_52w_high": -40, "pct_above_52w_low": 5,
}


def test_strong_setup_scores_high():
    score, reasons = score_technical_setup(STRONG)
    assert score >= 90
    assert classify_score(score) == "BUY_CANDIDATE"
    assert len(reasons) > 5


def test_weak_setup_scores_low():
    score, _ = score_technical_setup(WEAK)
    assert score < 30
    assert classify_score(score) == "IGNORE"


def test_classification_thresholds():
    assert classify_score(80) == "BUY_CANDIDATE"
    assert classify_score(60) == "WATCH"
    assert classify_score(40) == "IGNORE"


def test_score_never_exceeds_100():
    score, _ = score_technical_setup(STRONG)
    assert score <= 100
