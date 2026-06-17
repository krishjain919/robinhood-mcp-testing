# Robinhood MCP Testing

This is a small project I made to mess around with Robinhood access in Python and start building toward a simple MCP trading setup.

Right now it can log into Robinhood, save/load sessions, read account info, pull holdings, and make a very basic trade plan from manual signal data.

## Why I Built This

I wanted to test what a Robinhood MCP workflow could look like before trying to build anything too complicated.

The main goal right now is just to get the basics working: login, portfolio reads, holdings, simple signal parsing, and eventually small trade testing.

## How It Works

The project uses `robin-stocks` to connect to Robinhood and `fastmcp` for the MCP server.

For sentiment, I am starting simple. Instead of connecting to X/Twitter right away, I am using a local CSV with example signals. The project scores those signals and turns them into a basic trade plan.

## Files

* `login_device.py` — login test
* `test_robinhood_mcp.py` — account/portfolio read test
* `rh_client.py` — Robinhood helper functions
* `risk.py` — small trade limits and cash-only checks
* `sentiment.py` — basic signal scoring
* `trade_planner.py` — creates a simple trade plan
* `server.py` — MCP server starter
* `signals.example.csv` — sample signal data

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install everything:

```bash
pip install -r requirements.txt
```

Create your local env file:

```bash
cp .env.example .env
```

Then fill in `.env`:

```env
RH_USERNAME=your_robinhood_email
RH_PASSWORD=your_robinhood_password
MAX_TRADE_DOLLARS=5
ALLOW_LIVE_TRADING=false
```

## Run It

Test Robinhood login:

```bash
python login_device.py
```

Test account reads:

```bash
python test_robinhood_mcp.py
```

Test the trade planner:

```bash
cp signals.example.csv signals.csv
python trade_planner.py
```

Run the MCP server:

```bash
python server.py
```

## Current Status

This is still early. The read tests work, the basic trade planner works, and the MCP server has starter tools for account summary, holdings, and trade planning.

Next I want to clean up the MCP flow, add dry-run trades, and eventually connect better signal sources instead of using a CSV.
