"""Risk engine math — the part that must never be wrong."""

import config
from risk_engine import (
    compute_stop_distance,
    compute_trade_levels,
    portfolio_heat,
    can_add_position,
)


def test_atr_stop_used_when_inside_cap():
    # 2x ATR of $2 = $4 stop, which is 4% of $100 — under the 8% cap.
    dist, notes = compute_stop_distance(entry_price=100.0, atr=2.0)
    assert dist == 4.0
    assert any("ATR" in n for n in notes)


def test_stop_distance_capped_at_max_pct():
    # 2x ATR of $10 = $20 (20%), must be tightened to the 8% hard cap.
    dist, notes = compute_stop_distance(entry_price=100.0, atr=10.0)
    assert dist == config.MAX_STOP_DISTANCE_PCT  # 8% of $100 = 8.0
    assert any("cap" in n.lower() for n in notes)


def test_position_sizing_risks_fixed_fraction():
    # $50k account, 1% risk, ATR $2.50 -> $5 stop -> 100 shares (textbook case).
    levels = compute_trade_levels(entry_price=100.0, atr=2.50, equity=50_000)
    assert levels.shares == 100
    assert levels.risk_dollars == 500.0
    assert abs(levels.risk_pct_of_equity - 1.0) < 0.001


def test_conviction_scales_size_down_only():
    full = compute_trade_levels(100.0, 2.50, 50_000, conviction=1.0)
    half = compute_trade_levels(100.0, 2.50, 50_000, conviction=0.5)
    assert half.shares < full.shares
    # Conviction above 1.0 is clamped — it can never increase risk.
    over = compute_trade_levels(100.0, 2.50, 50_000, conviction=5.0)
    assert over.shares == full.shares


def test_target_is_r_multiple_of_stop():
    levels = compute_trade_levels(100.0, 2.0, 50_000)
    stop_dist = levels.entry_price - levels.stop_price
    target_dist = levels.target_price - levels.entry_price
    assert abs(target_dist - stop_dist * config.ATR_TARGET_R_MULTIPLE) < 0.01


def test_concentration_cap_limits_low_volatility_names():
    # Tiny ATR would otherwise size a huge position; equal-weight cap stops it.
    levels = compute_trade_levels(entry_price=10.0, atr=0.05, equity=10_000)
    assert levels.position_dollars <= 10_000 / config.MAX_POSITIONS + 10.0


def test_portfolio_heat_and_cap():
    assert portfolio_heat([100, 100, 100], 10_000) == 3.0
    assert can_add_position(current_heat_pct=5.0, new_risk_pct=1.0) is True
    assert can_add_position(current_heat_pct=5.5, new_risk_pct=1.0) is False
