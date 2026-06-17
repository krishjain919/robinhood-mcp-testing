from rh_client import get_account, get_portfolio, get_holdings

print("Testing Robinhood session...")

account = get_account()
portfolio = get_portfolio()
positions = get_holdings()

print("\nBuying Power:")
print(account.get("buying_power"))

print("\nCash:")
print(account.get("cash"))

print("\nPortfolio Equity:")
print(portfolio.get("equity"))

print("\nHoldings:")
for symbol, data in positions.items():
    print(
        f"{symbol}: {data.get('quantity')} shares, "
        f"equity={data.get('equity')}, "
        f"percent_change={data.get('percent_change')}"
    )

print("\nRobinhood read test passed.")