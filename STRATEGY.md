# Strategy & architecture

The bot is a **layered decision engine**. Each layer is a filter, and the rule
is simple and strict: **a softer, later layer can never override a harder,
earlier one.** The market regime can shut everything off; the risk engine can
veto on size; the AI can only ever remove or shrink a trade. Nothing downstream
can manufacture risk.

```
                ┌─────────────────────────────────────────────┐
   1. REGIME    │  Is SPY above its 200-day MA? (risk on/off)  │
                └───────────────────────┬─────────────────────┘
                                        │ risk-on only
                ┌───────────────────────▼─────────────────────┐
   2. SCREEN    │  Minervini trend template, 0–100 score       │
                │  (trend · relative strength · breakout/vol)  │
                └───────────────────────┬─────────────────────┘
                                        │ score ≥ buy threshold
                ┌───────────────────────▼─────────────────────┐
   3. DOSSIER   │  Earnings date · recent news · price-action  │
                │  narrative · company profile                 │
                └───────────────────────┬─────────────────────┘
                                        │
                ┌───────────────────────▼─────────────────────┐
   4. AI JUDGE  │  Claude: CONFIRM / CAUTION / VETO            │
                │  + conviction 0–1 (size multiplier only)     │
                └───────────────────────┬─────────────────────┘
                                        │ tradeable
                ┌───────────────────────▼─────────────────────┐
   5. RISK      │  ATR stop · 2R target · 1%-risk sizing ·     │
                │  portfolio-heat & position caps              │
                └───────────────────────┬─────────────────────┘
                                        │
                              Ranked, sized trade plan
```

## Layer 1 — Market regime gate
`regime_check()` in [`screener.py`](screener.py). No new long swing entries
unless SPY is above its 200-day MA, the 50-day MA is above the 200-day, and SPY
isn't in a sharp 20-day selloff. Historically this is the difference between
compounding and bleeding out in bear markets (see [RESEARCH.md](RESEARCH.md) §3).

## Layer 2 — Quant screen
[`strategy.py`](strategy.py) scores each ticker 0–100 on a Minervini-style trend
template: 40 pts trend structure, 25 pts 3-month relative strength vs SPY, 20
pts breakout + volume, 15 pts risk quality (RSI, recent return, distance from
52-week low). ≥70 = buy candidate, ≥55 = watch, else ignore. Cheap and
deterministic, so it can run over the whole universe before any expensive step.

## Layer 3 — Research dossier
[`dossier.py`](dossier.py) gathers the context the screen can't see: the next
earnings date, recent news headlines, a company profile, and a deterministic
plain-English read of the chart. This is the packet the AI reasons over.

## Layer 4 — AI judgment (the edge)
[`ai_agent.py`](ai_agent.py) sends the dossier to Claude (`claude-opus-4-8` by
default, adaptive thinking, structured JSON output) acting as a **disciplined
risk reviewer**. It returns `CONFIRM | CAUTION | VETO`, a `conviction` in
[0, 1], plus sentiment, event-risk, a thesis, and key risks.

Safety envelope — enforced in code, not left to the prompt:
- **VETO** → conviction 0, not tradeable.
- **CAUTION** → conviction capped at 0.6 (always sizes down).
- **CONFIRM** → conviction floored at 0.5.
- Conviction is **only ever a downward multiplier** on position size.
- An earnings date inside the blackout window is an **automatic VETO** before
  any model call.
- **No API key?** A deterministic heuristic stands in (earnings veto, overbought
  caution, bearish-keyword caution), so the pipeline always runs.

## Layer 5 — Risk engine
[`risk_engine.py`](risk_engine.py) is deliberately not clever:
- Stop = `min(ATR × 2, 8% of price)` — volatility-aware but hard-capped.
- Target = entry + stop-distance × 2 (a 2R target).
- Size so that hitting the stop loses exactly **1% of equity** (× AI conviction).
- Equal-weight concentration cap per name; **6% total portfolio-heat** cap.

## What the backtest does and doesn't prove
[`backtest.py`](backtest.py) is an **event-driven** simulation of layers 1, 2,
and 5 — real ATR stops, 2R targets, time stop, trend stop, the regime gate, and
risk-based sizing, with fills against each day's high/low and gap handling.

It deliberately **excludes the AI layer**, because you can't faithfully replay
historical news/earnings context — backtesting the LLM's calls would be
fiction. Since the AI layer only ever *removes* trades, the quant-only backtest
is the **floor**, not the ceiling. Trade-level stats (win rate, profit factor,
expectancy in R) are reported alongside the equity curve because they show
whether the edge is real or just one lucky run.

5-year run (illustrative, will drift with the date/data):

```
Strategy:   +104% total · 19.6% annualized · −25% maxDD · Sharpe 1.06
            705 trades · 43% win · profit factor 1.29 · +0.13R expectancy
Buy & hold VOO: +83% · 13% annualized · −24.5% maxDD · Sharpe 0.81
```

A 43% win rate that still makes money is the trend-following signature: small
losses (cut by stops), larger wins (let run to a 2R target).

## Safety posture
- Read-only by default; the MCP server never places a live order.
- Live-trade guardrails stay tiny (`MAX_TRADE_DOLLARS`, `ALLOW_LIVE_TRADING`).
- Cash-only sizing — buying power / margin is never used.
- Paper-trading ledger ([`paper_trades.py`](paper_trades.py)) is the bridge
  between backtest and real money: log what the bot *would* do, then measure
  win rate / profit factor / expectancy on your own universe before risking a
  cent.

## Roadmap
- Wire the paper ledger to auto-log `ACTIONABLE` scans on a schedule.
- Add a mark-to-market / exit-signal check for open paper positions (stop /
  target / earnings-approaching).
- Pull real Form 4 insider data (currently out of scope) into the dossier.
- Promote the AI layer from single-judge to a small debate (bull vs. bear)
  for higher-conviction names, per the TradingAgents pattern.
