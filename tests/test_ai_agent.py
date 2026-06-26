"""AI decision layer — focus on the safety envelope, not the model itself."""

from ai_agent import judge, _finalize, _heuristic_judgment


def _dossier(earnings_blocked=False, rsi=60, dist=2, news=None):
    return {
        "symbol": "TEST",
        "narrative": "test narrative",
        "indicators": {"rsi_14": rsi, "dist_sma_20_pct": dist},
        "earnings": {"blocked": earnings_blocked, "note": "earnings soon"},
        "news": news or [],
    }


def test_earnings_blackout_forces_veto():
    result = judge(_dossier(earnings_blocked=True))
    assert result["verdict"] == "VETO"
    assert result["tradeable"] is False
    assert result["conviction"] == 0.0
    assert result["event_risk"] == "HIGH"


def test_veto_zeroes_conviction():
    out = _finalize({"verdict": "VETO", "conviction": 0.9}, "x", None)
    assert out["conviction"] == 0.0
    assert out["tradeable"] is False


def test_caution_caps_conviction_at_half():
    out = _finalize({"verdict": "CAUTION", "conviction": 0.95}, "x", None)
    assert out["conviction"] <= 0.6
    assert out["tradeable"] is True


def test_confirm_floors_conviction():
    out = _finalize({"verdict": "CONFIRM", "conviction": 0.1}, "x", None)
    assert out["conviction"] >= 0.5


def test_heuristic_flags_overbought_as_caution():
    out = _heuristic_judgment(_dossier(rsi=85, dist=18))
    assert out["verdict"] == "CAUTION"
    assert out["conviction"] <= 0.6


def test_heuristic_bearish_news_lowers_conviction():
    news = [{"title": "Company faces SEC investigation and downgrade"}]
    out = _heuristic_judgment(_dossier(news=news))
    assert out["sentiment"] == "BEARISH"
    assert out["conviction"] < 1.0
