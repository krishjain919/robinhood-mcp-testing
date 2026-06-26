"""
Position sizing and exit math.

This is the part of the system that is NOT allowed to be clever. Stops and
size are computed deterministically from volatility (ATR) and a fixed
fraction of account equity. The AI layer can lower conviction, but it can
never widen a stop or grow a position past what these rules allow.

Core ideas (all backed by standard swing-trading risk practice):
  * Risk a small fixed % of equity per trade (default 1%).
  * Place the stop a multiple of ATR away, capped at a hard max % loss.
  * Size the position so that hitting the stop loses exactly that % — no more.
  * Cap total simultaneous risk across positions ("portfolio heat").
"""

import math
from dataclasses import dataclass, asdict

import config


@dataclass
class TradeLevels:
    entry_price: float
    stop_price: float
    target_price: float
    stop_distance: float        # dollars per share from entry to stop
    stop_pct: float             # that distance as a percent of entry
    risk_per_share: float       # == stop_distance
    shares: int
    position_dollars: float
    risk_dollars: float         # what you lose if the stop hits
    risk_pct_of_equity: float
    reward_to_risk: float       # target distance / stop distance (the R multiple)
    notes: list

    def to_dict(self) -> dict:
        return asdict(self)


def compute_stop_distance(entry_price: float, atr: float) -> tuple[float, list]:
    """
    ATR-based stop, capped so it never exceeds the hard max loss percent.

    Returns (stop_distance_in_dollars, notes).
    """

    notes = []

    atr_stop = atr * config.ATR_STOP_MULTIPLIER
    max_stop = entry_price * (config.MAX_STOP_DISTANCE_PCT / 100.0)

    if atr <= 0:
        # No usable volatility reading — fall back to the hard cap distance.
        notes.append("ATR unavailable; using max stop distance.")
        return max_stop, notes

    if atr_stop > max_stop:
        notes.append(
            f"{config.ATR_STOP_MULTIPLIER}x ATR stop "
            f"({atr_stop:.2f}) exceeds {config.MAX_STOP_DISTANCE_PCT}% cap; "
            f"tightened to {max_stop:.2f}."
        )
        return max_stop, notes

    notes.append(f"Stop set at {config.ATR_STOP_MULTIPLIER}x ATR.")
    return atr_stop, notes


def compute_trade_levels(
    entry_price: float,
    atr: float,
    equity: float,
    risk_pct: float | None = None,
    conviction: float = 1.0,
) -> TradeLevels:
    """
    Turn an entry price + volatility + account size into a full trade plan.

    `conviction` (0-1) is the ONLY hook the AI layer has here, and it can only
    shrink the position: risk is multiplied by it, so 0.5 conviction halves
    the size. It can never push conviction above 1.0.
    """

    conviction = max(0.0, min(1.0, conviction))
    risk_pct = config.ACCOUNT_RISK_PER_TRADE_PCT if risk_pct is None else risk_pct

    stop_distance, notes = compute_stop_distance(entry_price, atr)
    stop_price = max(0.01, entry_price - stop_distance)

    reward_to_risk = config.ATR_TARGET_R_MULTIPLE
    target_price = entry_price + stop_distance * reward_to_risk

    risk_dollars = equity * (risk_pct / 100.0) * conviction
    if conviction < 1.0:
        notes.append(f"AI conviction {conviction:.2f} -> position scaled down.")

    risk_per_share = stop_distance
    shares = 0
    if risk_per_share > 0:
        shares = math.floor(risk_dollars / risk_per_share)

    # Concentration cap: never let one name exceed an equal-weight slice.
    max_position_dollars = equity / max(1, config.MAX_POSITIONS)
    if shares * entry_price > max_position_dollars:
        capped = math.floor(max_position_dollars / entry_price)
        if capped < shares:
            notes.append(
                f"Position capped at equal weight "
                f"(~{max_position_dollars:,.0f}); {shares} -> {capped} shares."
            )
            shares = capped

    shares = max(0, shares)
    position_dollars = shares * entry_price
    actual_risk_dollars = shares * risk_per_share

    return TradeLevels(
        entry_price=round(entry_price, 2),
        stop_price=round(stop_price, 2),
        target_price=round(target_price, 2),
        stop_distance=round(stop_distance, 2),
        stop_pct=round((stop_distance / entry_price) * 100, 2) if entry_price else 0,
        risk_per_share=round(risk_per_share, 2),
        shares=shares,
        position_dollars=round(position_dollars, 2),
        risk_dollars=round(actual_risk_dollars, 2),
        risk_pct_of_equity=round((actual_risk_dollars / equity) * 100, 3) if equity else 0,
        reward_to_risk=round(reward_to_risk, 2),
        notes=notes,
    )


def portfolio_heat(open_risk_dollars: list[float], equity: float) -> float:
    """Total open risk as a percent of equity."""
    if equity <= 0:
        return 0.0
    return round((sum(open_risk_dollars) / equity) * 100, 2)


def can_add_position(current_heat_pct: float, new_risk_pct: float) -> bool:
    """Would adding this trade keep us under the portfolio heat cap?"""
    return (current_heat_pct + new_risk_pct) <= config.MAX_PORTFOLIO_HEAT_PCT


if __name__ == "__main__":
    # Worked example from the research: $50k account, 1% risk, ATR $2.50.
    levels = compute_trade_levels(entry_price=100.0, atr=2.50, equity=50_000)
    import json

    print(json.dumps(levels.to_dict(), indent=2))
