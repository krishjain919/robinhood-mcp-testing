import argparse
import math

import numpy as np
import pandas as pd

from market_data import get_price_history
from technical_indicators import add_indicators
from strategy import score_technical_setup
from watchlist import get_core_watchlist


INITIAL_CASH = 10_000
TRADING_COST = 0.001  # 0.1% rough cost whenever positions change


def prepare_data(symbol: str, benchmark_data: pd.DataFrame, period: str):
    try:
        data = get_price_history(symbol, period=period, interval="1d")
        data = add_indicators(data, benchmark_data)
        data["symbol"] = symbol
        return data.dropna().reset_index(drop=True)
    except Exception as error:
        print(f"Skipping {symbol}: {error}")
        return None


def build_indicator_snapshot(row: pd.Series):
    return {
        "price": row["Close"],
        "sma_20": row["SMA_20"],
        "sma_50": row["SMA_50"],
        "sma_150": row["SMA_150"],
        "sma_200": row["SMA_200"],
        "rsi_14": row["RSI_14"],
        "volume_ratio": row["volume_ratio"],
        "return_20d": row["return_20d"],
        "relative_strength_63d": row["relative_strength_63d"],
        "breakout_20d": row["breakout_20d"],
        "pct_below_52w_high": row["pct_below_52w_high"],
        "pct_above_52w_low": row["pct_above_52w_low"],
    }


def is_market_regime_active(benchmark_row: pd.Series):
    """
    Simple regime gate.

    Swing trading is only turned on when the market is not broken.
    """

    price = benchmark_row["Close"]
    sma_50 = benchmark_row["SMA_50"]
    sma_200 = benchmark_row["SMA_200"]
    return_20d = benchmark_row["return_20d"]

    if price < sma_200:
        return False

    if sma_50 < sma_200:
        return False

    if return_20d < -7.5:
        return False

    return True


def calculate_metrics(equity_curve: pd.DataFrame):
    equity = equity_curve["strategy_value"]
    returns = equity.pct_change().dropna()

    total_return = (equity.iloc[-1] / equity.iloc[0]) - 1

    years = len(equity_curve) / 252
    annualized_return = 0

    if years > 0:
        annualized_return = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1

    running_max = equity.cummax()
    drawdown = (equity / running_max) - 1
    max_drawdown = drawdown.min()

    sharpe = 0

    if returns.std() != 0 and not math.isnan(returns.std()):
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252)

    return {
        "final_value": equity.iloc[-1],
        "total_return": total_return,
        "annualized_return": annualized_return,
        "max_drawdown": max_drawdown,
        "sharpe": sharpe,
    }


def buy_and_hold_metrics(symbol: str, period: str):
    data = get_price_history(symbol, period=period, interval="1d")
    data["daily_return"] = data["Close"].pct_change().fillna(0)
    data["strategy_value"] = INITIAL_CASH * (1 + data["daily_return"]).cumprod()
    return calculate_metrics(data[["Date", "strategy_value"]])


def print_metrics(title: str, metrics: dict):
    print(f"\n===== {title} =====")
    print(f"Final value: ${metrics['final_value']:,.2f}")
    print(f"Total return: {metrics['total_return'] * 100:.2f}%")
    print(f"Annualized return: {metrics['annualized_return'] * 100:.2f}%")
    print(f"Max drawdown: {metrics['max_drawdown'] * 100:.2f}%")
    print(f"Sharpe: {metrics['sharpe']:.2f}")


def run_backtest(period: str, benchmark: str, market: str, top_n: int, min_score: int):
    print(f"Downloading market data for {market}...")
    market_data = get_price_history(market, period=period, interval="1d")
    market_data = add_indicators(market_data)

    watchlist = get_core_watchlist()
    print(f"Preparing data for {len(watchlist)} symbols...")

    data_by_symbol = {}

    for symbol in watchlist:
        prepared = prepare_data(symbol, market_data, period)

        if prepared is not None and len(prepared) > 252:
            data_by_symbol[symbol] = prepared

    dates = sorted(set(market_data["Date"]))

    portfolio_value = INITIAL_CASH
    positions = {}
    rows = []

    for i in range(1, len(dates)):
        today = dates[i]
        yesterday = dates[i - 1]

        daily_return = 0

        for symbol, weight in positions.items():
            symbol_data = data_by_symbol.get(symbol)

            if symbol_data is None:
                continue

            match = symbol_data[symbol_data["Date"] == today]

            if match.empty:
                continue

            symbol_return = match.iloc[0]["return_1d"]
            daily_return += weight * symbol_return

        portfolio_value *= 1 + daily_return

        # Rebalance every 5 trading days.
        if i % 5 == 0:
            market_match = market_data[market_data["Date"] == yesterday]

            if market_match.empty:
                continue

            market_row = market_match.iloc[0]
            regime_active = is_market_regime_active(market_row)

            new_positions = {}

            if regime_active:
                candidates = []

                for symbol, symbol_data in data_by_symbol.items():
                    symbol_match = symbol_data[symbol_data["Date"] == yesterday]

                    if symbol_match.empty:
                        continue

                    row = symbol_match.iloc[0]
                    snapshot = build_indicator_snapshot(row)
                    score, reasons = score_technical_setup(snapshot)

                    if score >= min_score:
                        candidates.append({
                            "symbol": symbol,
                            "score": score,
                            "reasons": reasons,
                        })

                candidates = sorted(
                    candidates,
                    key=lambda item: item["score"],
                    reverse=True,
                )

                selected = candidates[:top_n]

                if selected:
                    weight = 0.95 / len(selected)

                    for item in selected:
                        new_positions[item["symbol"]] = weight

            old_symbols = set(positions.keys())
            new_symbols = set(new_positions.keys())
            turnover_symbols = old_symbols.symmetric_difference(new_symbols)

            portfolio_value *= 1 - (len(turnover_symbols) * TRADING_COST * 0.1)
            positions = new_positions

        rows.append({
            "Date": today,
            "strategy_value": portfolio_value,
            "positions": ",".join(positions.keys()) if positions else "CASH",
        })

    equity_curve = pd.DataFrame(rows)
    strategy_metrics = calculate_metrics(equity_curve)
    benchmark_metrics = buy_and_hold_metrics(benchmark, period)

    print_metrics("SWING STRATEGY", strategy_metrics)
    print_metrics(f"BUY AND HOLD {benchmark}", benchmark_metrics)

    print("\n===== RESULT =====")

    if strategy_metrics["final_value"] > benchmark_metrics["final_value"]:
        print(f"Strategy beat {benchmark}.")
    else:
        print(f"{benchmark} beat the strategy.")

    print("\nLatest positions:")
    print(equity_curve.iloc[-1]["positions"])

    equity_curve.to_csv("backtest_equity_curve.csv", index=False)
    print("\nSaved: backtest_equity_curve.csv")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default="5y")
    parser.add_argument("--benchmark", default="VOO")
    parser.add_argument("--market", default="SPY")
    parser.add_argument("--top", type=int, default=3)
    parser.add_argument("--min-score", type=int, default=75)
    args = parser.parse_args()

    run_backtest(
        period=args.period,
        benchmark=args.benchmark,
        market=args.market,
        top_n=args.top,
        min_score=args.min_score,
    )


if __name__ == "__main__":
    main()