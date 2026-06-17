import os
import robin_stocks.robinhood as rh
from dotenv import load_dotenv

load_dotenv()

username = os.getenv("RH_USERNAME")
password = os.getenv("RH_PASSWORD")

if not username or not password:
    raise ValueError("Missing RH_USERNAME or RH_PASSWORD in .env")

print("Logging in / loading saved Robinhood session...")

login = rh.login(
    username=username,
    password=password,
    store_session=True
)

print("Login loaded.")
print("Testing Robinhood session...")

account = rh.profiles.load_account_profile()
portfolio = rh.profiles.load_portfolio_profile()
positions = rh.account.build_holdings()

print("\nBuying Power:")
print(account.get("buying_power"))

print("\nCash:")
print(account.get("cash"))

print("\nPortfolio Equity:")
print(portfolio.get("equity"))

print("\nHoldings:")
for symbol, data in positions.items():
    print(f"{symbol}: {data.get('quantity')} shares, equity={data.get('equity')}, percent_change={data.get('percent_change')}")

print("\nMCP Robinhood read test passed.")