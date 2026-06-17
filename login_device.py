import os
import time
import robin_stocks.robinhood as rh
from dotenv import load_dotenv

load_dotenv()

username = os.getenv("RH_USERNAME")
password = os.getenv("RH_PASSWORD")

if not username or not password:
    raise ValueError("Missing RH_USERNAME or RH_PASSWORD in .env")

print("Logging into Robinhood...")
print("If your phone asks 'Are you logging in?', tap YES.")

login = rh.login(
    username=username,
    password=password,
    store_session=True
)

print("Login completed. Not printing tokens.")

time.sleep(3)

account = rh.profiles.load_account_profile()

print("Login worked.")
print("Buying power:", account.get("buying_power"))
print("Cash:", account.get("cash"))