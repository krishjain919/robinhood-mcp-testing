"""
Event-driven backtest of the quant + risk core.

This simulates the strategy the way it actually trades: ATR-based stops, a
2R take-profit, a time stop, a trend stop (close below the 20-day MA), the
SPY regime gate, and risk-based position sizing — one trade at a time, with
real fills against each day's high/low and gap handling on the open.

Important honesty note: the AI judgment layer is NOT in this backtest. You
can't replay historical news and earnings context faithfully, so backtesting
the LLM's calls would be fiction. What this DOES validate is the engine the
AI sits on top of — the screen, the stops, the sizing, the regime filter.
The AI layer's job in live trading is to *remove* bad trades this engine would
otherwise take, so a profitable core here is the floor, not the ceiling.

Trade-level stats (win rate, profit factor, expectancy in R) matter more than
the equity curve alone, because they tell you whether the EDGE is real or just
one lucky run.
"""

import argparse
import math

import numpy as np
import pandas as pd

import config
from market_data import get_price_history
from technical_indicators import add_indicators
from strategy import score_technical_setup
from watchlist import get_core_watchlist


INITIAL_CASH = 10_000.0
TRADING_COST = 0.0005  # 0.05% per fill, applied on entry and exit


def is_market_regime_active(row: pd.Series) -> bool:
    """SPY regime gate — the single biggest defense against bear markets."""
    if row["Close"] < row["SMA_200"]:
        return False
    if row["SMA_50"] < row["SMA_200"]:
        return False
    if row["return_20d"] < -7.5:
        return False
    return True


def build_snapshots(symbol: str, benchmark_data: pd.DataFrame, period: str):
    """Precompute, for every day, the fields + technical score we need so the
    simulation loop is just lookups."""

    try:
        data = get_price_history(symbol, period=period, interval="1d")
        data = add_indicators(data, benchmark_data)
        data = data.dropna().reset_index(drop=True)
    except Exception as error:
        print(f"Skipping {symbol}: {error}")
        return None

    if len(data) < 252:
        return None

    snapshots = {}
    for _, row in data.iterrows():
        snap = {
            "open": row["Open"],
            "high": row["High"],
            "low": row["Low"],
            "close": row["Close"],
            "sma_20": row["SMA_20"],
            "atr_14": row["atr_14"],
            "return_1d": row["return_1d"],
        }
        score, _ = score_technical_setup({
            "price": row["Close"],
            "sma_20": row["SMA_20"], "sma_50": row["SMA_50"],
            "sma_150": row["SMA_150"], "sma_200": row["SMA_200"],
            "rsi_14": row["RSI_14"], "volume_ratio": row["volume_ratio"],
            "return_20d": row["return_20d"],
            "relative_strength_63d": row["relative_strength_63d"],
            "breakout_20d": row["breakout_20d"],
            "pct_below_52w_high": row["pct_below_52w_high"],
            "pct_above_52w_low": row["pct_above_52w_low"],
        })
        snap["score"] = score
        snapshots[row["Date"]] = snap

    return snapshots


def stop_distance(entry: float, atr: float) -> float:
    atr_stop = atr * config.ATR_STOP_MULTIPLIER
    max_stop = entry * (config.MAX_STOP_DISTANCE_PCT / 100.0)
    if atr <= 0:
        return max_stop
    return min(atr_stop, max_stop)


def evaluate_exit(position: dict, snap: dict, days_held: int):
    """Return (exit_price, reason) if the position should close today, else None.

    Order is conservative: stops are checked before targets, and gaps through
    a level fill at the open."""

    o, h, l, c = snap["open"], snap["high"], snap["low"], snap["close"]
    stop, target = position["stop"], position["target"]

    if o <= stop:
        return o, "stop_gap"
    if l <= stop:
        return stop, "stop"
    if o >= target:
        return o, "target_gap"
    if h >= target:
        return target, "target"
    if days_held >= config.TIME_STOP_DAYS:
        return c, "time_stop"
    if c < snap["sma_20"]:
        return c, "trend_stop"
    return None


def run_backtest(period: str, benchmark: str, market: str, top_n: int, min_score: int):
    print(f"Loading market data for {market}...")
    market_data = add_indicators(get_price_history(market, period=period, interval="1d"))
    market_by_date = {row["Date"]: row for _, row in market_data.dropna().iterrows()}

    watchlist = get_core_watchlist()
    print(f"Building snapshots for {len(watchlist)} symbols...")
    snaps = {}
    for symbol in watchlist:
        s = build_snapshots(symbol, market_data, period)
        if s is not None:
            snaps[symbol] = s

    dates = sorted(market_by_date.keys())

    cash = INITIAL_CASH
    positions: dict[str, dict] = {}
    trades: list[dict] = []
    equity_rows = []

    for i, today in enumerate(dates):
        # 1. Process exits on existing positions.
        for symbol in list(positions.keys()):
            snap = snaps.get(symbol, {}).get(today)
            if snap is None:
                continue
            pos = positions[symbol]
            days_held = i - pos["entry_index"]
            result = evaluate_exit(pos, snap, days_held)
            if result is not None:
                exit_price, reason = result
                proceeds = exit_price * pos["shares"] * (1 - TRADING_COST)
                cash += proceeds
                pnl = proceeds - pos["cost_basis"]
                r_mult = (exit_price - pos["entry"]) / pos["risk_per_share"] if pos["risk_per_share"] else 0
                trades.append({
                    "symbol": symbol, "entry": pos["entry"], "exit": round(exit_price, 2),
                    "reason": reason, "days_held": days_held,
                    "pnl": round(pnl, 2), "r_multiple": round(r_mult, 2),
                })
                del positions[symbol]

        # 2. Mark-to-market equity at today's close.
        holdings_value = 0.0
        for symbol, pos in positions.items():
            snap = snaps.get(symbol, {}).get(today)
            price = snap["close"] if snap else pos["entry"]
            holdings_value += price * pos["shares"]
        equity = cash + holdings_value
        equity_rows.append({"Date": today, "strategy_value": equity,
                            "positions": ",".join(positions) or "CASH"})

        # 3. Entries — only when the regime is risk-on and we have room.
        market_row = market_by_date[today]
        if not is_market_regime_active(market_row):
            continue
        if len(positions) >= top_n:
            continue

        candidates = []
        for symbol, by_date in snaps.items():
            if symbol in positions:
                continue
            snap = by_date.get(today)
            if snap and snap["score"] >= min_score and snap["atr_14"] > 0:
                candidates.append((snap["score"], symbol, snap))
        candidates.sort(reverse=True, key=lambda c: c[0])

        for _, symbol, snap in candidates:
            if len(positions) >= top_n:
                break
            entry = snap["close"]
            dist = stop_distance(entry, snap["atr_14"])
            if dist <= 0:
                continue

            risk_dollars = equity * (config.ACCOUNT_RISK_PER_TRADE_PCT / 100.0)
            shares = math.floor(risk_dollars / dist)
            # Equal-weight concentration cap, mirroring the live risk engine.
            max_dollars = equity / max(1, top_n)
            shares = min(shares, math.floor(max_dollars / entry))
            cost = shares * entry * (1 + TRADING_COST)
            if shares <= 0 or cost > cash:
                continue

            cash -= cost
            positions[symbol] = {
                "shares": shares, "entry": entry, "cost_basis": cost,
                "stop": entry - dist, "target": entry + dist * config.ATR_TARGET_R_MULTIPLE,
                "risk_per_share": dist, "entry_index": i,
            }

    equity_curve = pd.DataFrame(equity_rows)
    report(equity_curve, trades, benchmark, period)
    equity_curve.to_csv("backtest_equity_curve.csv", index=False)
    print("\nSaved: backtest_equity_curve.csv")


def equity_metrics(equity_curve: pd.DataFrame) -> dict:
    equity = equity_curve["strategy_value"]
    returns = equity.pct_change().dropna()
    years = len(equity_curve) / 252

    total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
    annualized = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1 if years > 0 else 0
    drawdown = (equity / equity.cummax()) - 1
    sharpe = 0
    if returns.std() and not math.isnan(returns.std()):
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252)

    return {
        "final_value": equity.iloc[-1],
        "total_return": total_return,
        "annualized_return": annualized,
        "max_drawdown": drawdown.min(),
        "sharpe": sharpe,
    }


def trade_metrics(trades: list[dict]) -> dict:
    if not trades:
        return {"trades": 0}
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    return {
        "trades": len(trades),
        "win_rate": len(wins) / len(trades),
        "avg_win": gross_win / len(wins) if wins else 0,
        "avg_loss": gross_loss / len(losses) if losses else 0,
        "profit_factor": (gross_win / gross_loss) if gross_loss else float("inf"),
        "expectancy_r": sum(t["r_multiple"] for t in trades) / len(trades),
    }


def buy_and_hold_metrics(symbol: str, period: str) -> dict:
    data = get_price_history(symbol, period=period, interval="1d")
    data["daily_return"] = data["Close"].pct_change().fillna(0)
    data["strategy_value"] = INITIAL_CASH * (1 + data["daily_return"]).cumprod()
    return equity_metrics(data[["Date", "strategy_value"]])


def report(equity_curve, trades, benchmark, period):
    strat = equity_metrics(equity_curve)
    tm = trade_metrics(trades)
    bench = buy_and_hold_metrics(benchmark, period)

    print("\n===== SWING STRATEGY (quant + risk core) =====")
    print(f"Final value:       ${strat['final_value']:,.2f}")
    print(f"Total return:      {strat['total_return'] * 100:.2f}%")
    print(f"Annualized:        {strat['annualized_return'] * 100:.2f}%")
    print(f"Max drawdown:      {strat['max_drawdown'] * 100:.2f}%")
    print(f"Sharpe:            {strat['sharpe']:.2f}")

    if tm.get("trades"):
        pf = tm["profit_factor"]
        print(f"\nTrades:            {tm['trades']}")
        print(f"Win rate:          {tm['win_rate'] * 100:.1f}%")
        print(f"Avg win:           ${tm['avg_win']:.2f}")
        print(f"Avg loss:          ${tm['avg_loss']:.2f}")
        print(f"Profit factor:     {pf:.2f}" if pf != float('inf') else "Profit factor:     inf")
        print(f"Expectancy:        {tm['expectancy_r']:.2f}R per trade")

    print(f"\n===== BUY & HOLD {benchmark} =====")
    print(f"Final value:       ${bench['final_value']:,.2f}")
    print(f"Total return:      {bench['total_return'] * 100:.2f}%")
    print(f"Annualized:        {bench['annualized_return'] * 100:.2f}%")
    print(f"Max drawdown:      {bench['max_drawdown'] * 100:.2f}%")
    print(f"Sharpe:            {bench['sharpe']:.2f}")

    print("\n===== RESULT =====")
    winner = "Strategy" if strat["final_value"] > bench["final_value"] else benchmark
    print(f"{winner} finished ahead on total return.")
    print("(Note: the AI layer is not simulated here — it only removes trades,")
    print(" so live results should diverge from this quant-only floor.)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default="5y")
    parser.add_argument("--benchmark", default="VOO")
    parser.add_argument("--market", default="SPY")
    parser.add_argument("--top", type=int, default=config.MAX_POSITIONS)
    parser.add_argument("--min-score", type=int, default=config.MIN_BUY_SCORE)
    args = parser.parse_args()

    run_backtest(args.period, args.benchmark, args.market, args.top, args.min_score)


if __name__ == "__main__":
    main()
