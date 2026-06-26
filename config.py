"""
Central configuration.

Everything tunable lives here and is driven by environment variables so I can
change risk settings without editing code. Defaults are deliberately
conservative — this bot is supposed to protect capital first and chase return
second.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _flt(name: str, default: str) -> float:
    return float(os.getenv(name, default))


def _int(name: str, default: str) -> int:
    return int(os.getenv(name, default))


def _bool(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Risk engine
# ---------------------------------------------------------------------------
# Percent of account equity risked on a single trade. Research consensus for
# swing trading is 0.5%-2%; 1% lets you survive a long losing streak.
ACCOUNT_RISK_PER_TRADE_PCT = _flt("ACCOUNT_RISK_PER_TRADE_PCT", "1.0")

# Total simultaneous risk across all open positions ("portfolio heat").
# Should stay <= ~6% so a correlated selloff can't wreck the account.
MAX_PORTFOLIO_HEAT_PCT = _flt("MAX_PORTFOLIO_HEAT_PCT", "6.0")

# ATR-based stop/target distances. 1.5-2x ATR is the sweet spot for 3-15 day
# swing holds; target at 2R (twice the stop distance) by default.
ATR_STOP_MULTIPLIER = _flt("ATR_STOP_MULTIPLIER", "2.0")
ATR_TARGET_R_MULTIPLE = _flt("ATR_TARGET_R_MULTIPLE", "2.0")

# Hard ceiling on stop distance regardless of ATR (Minervini's 7-8% max loss).
MAX_STOP_DISTANCE_PCT = _flt("MAX_STOP_DISTANCE_PCT", "8.0")

# Review/exit a position that has gone nowhere after this many trading days.
TIME_STOP_DAYS = _int("TIME_STOP_DAYS", "15")

# Most concurrent swing positions to hold.
MAX_POSITIONS = _int("MAX_POSITIONS", "5")


# ---------------------------------------------------------------------------
# Earnings / event risk
# ---------------------------------------------------------------------------
# Don't enter (and flag exits for) swing trades within this many trading days
# of a scheduled earnings report. Holding through earnings turns a managed
# swing trade into a coin-flip on an overnight gap.
EARNINGS_BLACKOUT_DAYS = _int("EARNINGS_BLACKOUT_DAYS", "3")


# ---------------------------------------------------------------------------
# Screening thresholds
# ---------------------------------------------------------------------------
# Technical score (0-100) needed to be a buy candidate vs. a watch vs. ignore.
MIN_BUY_SCORE = _int("MIN_BUY_SCORE", "70")
MIN_WATCH_SCORE = _int("MIN_WATCH_SCORE", "55")


# ---------------------------------------------------------------------------
# AI agent
# ---------------------------------------------------------------------------
# Master switch. Even when on, the agent only ever CONFIRMS, VETOES, or
# SIZES DOWN a quant candidate — it can never invent a trade or add risk.
USE_AI_AGENT = _bool("USE_AI_AGENT", "true")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
# Default to the most capable model. Override with AI_MODEL=claude-sonnet-4-6
# if you want to run the scanner cheaper across a large universe.
AI_MODEL = os.getenv("AI_MODEL", "claude-opus-4-8")
AI_EFFORT = os.getenv("AI_EFFORT", "medium")  # low | medium | high | max


def ai_available() -> bool:
    """True only if the AI layer is switched on and has a key to use."""
    return USE_AI_AGENT and bool(ANTHROPIC_API_KEY)


# ---------------------------------------------------------------------------
# Live-trading guardrails (kept tiny on purpose)
# ---------------------------------------------------------------------------
MAX_TRADE_DOLLARS = _flt("MAX_TRADE_DOLLARS", "5")
ALLOW_LIVE_TRADING = _bool("ALLOW_LIVE_TRADING", "false")


def summary() -> dict:
    """Snapshot of the active configuration (no secrets)."""
    return {
        "risk_per_trade_pct": ACCOUNT_RISK_PER_TRADE_PCT,
        "max_portfolio_heat_pct": MAX_PORTFOLIO_HEAT_PCT,
        "atr_stop_multiplier": ATR_STOP_MULTIPLIER,
        "atr_target_r_multiple": ATR_TARGET_R_MULTIPLE,
        "max_stop_distance_pct": MAX_STOP_DISTANCE_PCT,
        "time_stop_days": TIME_STOP_DAYS,
        "max_positions": MAX_POSITIONS,
        "earnings_blackout_days": EARNINGS_BLACKOUT_DAYS,
        "min_buy_score": MIN_BUY_SCORE,
        "min_watch_score": MIN_WATCH_SCORE,
        "ai_agent_enabled": USE_AI_AGENT,
        "ai_agent_available": ai_available(),
        "ai_model": AI_MODEL if USE_AI_AGENT else None,
        "max_trade_dollars": MAX_TRADE_DOLLARS,
        "allow_live_trading": ALLOW_LIVE_TRADING,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(summary(), indent=2))
