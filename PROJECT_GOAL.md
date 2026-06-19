# Robinhood MCP Swing Trading Bot Goal

This project started as a simple Robinhood MCP test, but the bigger goal is to turn it into a swing trading assistant.

I do not want this to just blindly buy stocks because someone on X says something is bullish. The goal is to build a system that combines normal market data, technical indicators, public sentiment, public insider data, and strict risk rules before making any trade recommendation.

## Long-Term Goal

Build a local MCP trading assistant that can:

* read my Robinhood account and holdings
* scan stocks for swing trade setups
* analyze candles, trend, volume, and momentum
* read manual or automated X/Twitter sentiment signals
* track public insider buying/selling data from SEC filings
* create buy, hold, watch, or sell recommendations
* explain why it made each recommendation
* log paper trades before doing real trades
* eventually test tiny live trades with strict max dollar limits

The goal is not to make a random hype bot. The goal is to make a decision engine that can help find better swing trade setups and manage exits.

## Core Buy Logic

A stock should only become a buy idea if multiple signals agree.

Basic buy idea:

```text
BUY / WATCH if:
- price is above the 20-day moving average
- 20-day moving average is above the 50-day moving average
- volume is above recent average
- RSI is not extremely overbought
- sentiment score is positive
- public insider data is neutral or positive
- position size stays small
- trade uses cash, not margin
```

Example scoring idea:

```text
final_score =
    technical_score * 0.50
  + sentiment_score * 0.25
  + insider_score * 0.15
  + risk_score * 0.10
```

Example decisions:

```text
score >= 75  -> possible buy
score 50-74  -> watchlist
score < 50   -> ignore
```

## Core Sell Logic

The bot should know when to exit before it ever enters.

Basic sell/review logic:

```text
SELL / REVIEW if:
- position is up 8-15% and momentum is fading
- price closes below the 20-day moving average
- stop loss hits around -5% to -8%
- sentiment flips negative
- public insider selling becomes unusually strong
- position has been held too long without moving
```

Simple first version:

```text
take profit: +10%
stop loss: -6%
time stop: review after 15 trading days
trend stop: review/sell if price closes below 20-day moving average
```

## Data Sources I Want Eventually

Market data:

```text
candles
daily price history
volume
moving averages
RSI
recent returns
volatility
```

Sentiment data:

```text
manual CSV signals first
later X/Twitter accounts
source weighting by historical accuracy
ticker mention frequency
confidence/timeframe tags
```

Public insider data:

```text
SEC Form 4 filings
insider buys
insider sells
cluster buying
CEO/CFO/director transaction weighting
```

Robinhood data:

```text
cash
holdings
portfolio value
position sizes
current gains/losses
```

## Development Plan

Phase 1: Robinhood + MCP basics

```text
login
read account
read holdings
basic MCP tools
manual sentiment CSV
simple trade planner
```

Phase 2: Swing trading logic

```text
market data fetcher
technical indicators
technical score
strategy score
watchlist generation
exit rules
```

Phase 3: Paper trading

```text
log fake trades
track entry price
track exit price
calculate 1d / 5d / 20d returns
measure win rate
measure average return
```

Phase 4: Better signals

```text
source weighting
X/Twitter signal input
public insider data
confidence weighting
sentiment trend over time
```

Phase 5: Tiny live testing

```text
dry-run orders first
manual confirmation
max trade size around $5
cash-only trades
no margin
no options
no shorting
```

## Main Rule

The bot should never trade just because one signal says buy.

It should only create a trade idea when price action, risk rules, sentiment, and public data all line up enough to justify testing the trade.
