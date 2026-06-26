# Robinhood AI Swing Trading Assistant

A local **MCP-based swing trading assistant** that combines a disciplined
quantitative screen with an **AI agent** that reasons over news, catalysts, and
event risk — then sizes every trade with strict, volatility-aware risk rules.

The guiding principle (from [`PROJECT_GOAL.md`](PROJECT_GOAL.md)): **never trade
just because one signal says buy.** A trade idea only appears when the trend,
the risk math, the market regime, and the qualitative picture all line up. The
AI can *remove* trades and *shrink* them — it can never invent one or add risk.

> ⚠️ This is research/educational software. It does **not** place live orders by
> default and is not financial advice. Trade real money at your own risk.

## The decision pipeline

```
Regime gate → Quant screen → Research dossier → AI judgment → Risk engine → Trade plan
 (SPY 200DMA)  (trend template)  (earnings/news)  (confirm/veto)  (ATR stops)
```

Each layer is a filter, and a later layer can never override an earlier one.
Full design in [STRATEGY.md](STRATEGY.md); the research behind every choice is
in [RESEARCH.md](RESEARCH.md).

## What's in here

| File | Role |
| --- | --- |
| [`config.py`](config.py) | All tunables (risk %, ATR multiples, thresholds, AI model) from env |
| [`market_data.py`](market_data.py) | Price history via yfinance |
| [`technical_indicators.py`](technical_indicators.py) | SMA, RSI, **ATR, MACD, ADX**, relative strength, breakout |
| [`strategy.py`](strategy.py) | Minervini-style 0–100 trend-template score |
| [`watchlist.py`](watchlist.py) | Liquid core watchlist (+ speculative list) |
| [`earnings.py`](earnings.py) | Earnings-date lookup + blackout enforcement |
| [`dossier.py`](dossier.py) | Per-ticker research packet for the AI |
| [`ai_agent.py`](ai_agent.py) | Claude confirm/caution/veto layer (+ heuristic fallback) |
| [`risk_engine.py`](risk_engine.py) | ATR stops, 2R targets, 1%-risk sizing, portfolio-heat caps |
| [`screener.py`](screener.py) | Orchestrates the full pipeline into a ranked plan |
| [`paper_trades.py`](paper_trades.py) | Paper-trading ledger (win rate, profit factor, R) |
| [`backtest.py`](backtest.py) | Event-driven backtest of the quant + risk core |
| [`server.py`](server.py) | FastMCP server exposing all of the above as tools |
| [`rh_client.py`](rh_client.py), [`risk.py`](risk.py), [`trade_planner.py`](trade_planner.py) | Robinhood reads + tiny live-order guardrails |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill it in
```

`.env` essentials:

```env
RH_USERNAME=your_robinhood_email
RH_PASSWORD=your_robinhood_password

# Optional — without it the bot falls back to a deterministic heuristic
ANTHROPIC_API_KEY=sk-ant-...
AI_MODEL=claude-opus-4-8

MAX_TRADE_DOLLARS=5
ALLOW_LIVE_TRADING=false
```

The risk parameters (1% risk/trade, 2× ATR stop, 6% portfolio heat, etc.) all
have sensible defaults — see [`.env.example`](.env.example) to override.

## Run it

```bash
# Is the market even in a risk-on regime?
python -c "from screener import regime_check; print(regime_check())"

# Full scan (dry run, no tokens spent — AI layer off)
python screener.py

# Deep single-name analysis WITH the AI layer (needs ANTHROPIC_API_KEY)
python -c "from ai_agent import judge; from dossier import build_dossier; \
import json; print(json.dumps(judge(build_dossier('NVDA')), indent=2))"

# Backtest the quant + risk core vs buy-and-hold VOO
python backtest.py --period 5y

# Run the MCP server
python server.py

# Tests
python -m pytest tests/ -q
```

## MCP tools

| Tool | What it does |
| --- | --- |
| `market_regime` | SPY 200-DMA risk-on/off read |
| `scan_swing_candidates` | Full pipeline → ranked, sized trade plan |
| `analyze_symbol_deep` | One ticker: dossier + AI judgment + exact stop/target/size |
| `config_summary` | Active risk/AI configuration |
| `robinhood_account_summary`, `robinhood_holdings` | Account/holdings reads |
| `paper_open_trade`, `paper_close_trade`, `paper_list_trades`, `paper_performance` | Paper-trading ledger |
| `generate_trade_plan` | Legacy CSV-signal plan (superseded by the scanner) |

## Honesty about limits

- The AI layer is **not** in the backtest (you can't replay historical news);
  the quant-only backtest is the floor, not the ceiling.
- yfinance data (incl. earnings dates and news) is best-effort and can be stale
  or missing — the bot degrades gracefully and tells you when a date is unknown.
- Insider/Form-4 data is on the roadmap, not yet wired in.
- This finds and sizes *candidates*. **You** pull the trigger.
