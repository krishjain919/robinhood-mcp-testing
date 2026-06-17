# Robinhood MCP Testing

This is a small project I built to test out Robinhood access with Python and eventually connect it to an MCP server.

Right now, the project is mostly focused on making sure I can log in, read my account data, and pull my holdings correctly. The longer-term goal is to grow this into a simple trading assistant that can look at signals, sentiment, and my portfolio, then suggest small trades with strict limits.

## Why I Built This

I built this because I wanted to experiment with Robinhood MCP-style workflows and see how far I could take it.

The idea is not to build some huge trading bot right away. I just wanted a clean starting point where I can test Robinhood login, account reads, holdings, and eventually safe trade planning.

## What This Does

Right now, this project can:

* Log into Robinhood locally
* Load a saved Robinhood session
* Read buying power and cash
* Read portfolio equity
* Print current holdings
* Show shares, equity, and percent change for each holding

This is mainly a read-only test right now.

## Current Files

* `login_device.py` — tests Robinhood login and device approval
* `test_robinhood_mcp.py` — tests reading account and portfolio data
* `.env.example` — example environment variables
* `requirements.txt` — Python dependencies

## Setup

Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install requirements:

```bash
pip install -r requirements.txt
```

Create a local `.env` file:

```bash
cp .env.example .env
```

Then add your own Robinhood login info inside `.env`:

```env
RH_USERNAME=your_robinhood_email
RH_PASSWORD=your_robinhood_password
```

## Running It

First test login:

```bash
python login_device.py
```

Then test reading account data:

```bash
python test_robinhood_mcp.py
```

If it works, it should print account cash, buying power, portfolio equity, and current holdings.

## Next Steps

I want to keep building this into a cleaner MCP project with:

* A real MCP server wrapper
* Portfolio summary tools
* Manual sentiment signal input
* Trade plan generation
* Dry-run trades
* Small live trade testing with strict max dollar limits

Eventually, I want it to use signals from X/Twitter and other market sources, but for now I am keeping it simple and focused on testing the Robinhood connection.
