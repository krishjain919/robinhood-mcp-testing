# Research notes — what actually works in swing trading, and where an AI agent adds edge

This file records the research the strategy is built on, so every design choice
in the code traces back to something defensible rather than a hunch. It is the
"why" behind [STRATEGY.md](STRATEGY.md).

## 1. The base strategy: trend + relative strength (Minervini-style)

The most durable, well-documented edge in swing trading is **buying strong
stocks in confirmed uptrends**, not bottom-fishing. Mark Minervini's SEPA /
Trend Template is the canonical, rule-based version of this and is what the
quant screen implements:

- Price above the 50-, 150-, and 200-day moving averages; 50 > 150 > 200; the
  200-day trending up.
- Price within ~25% of its 52-week high and at least ~30% above its 52-week low.
- A relative-strength rank in the top ~30% of the market.
- **Risk:** a hard stop **7–8% max** below entry, partial profits taken into
  strength at a **2–3R** multiple, stop moved to breakeven once a gain is
  established, then trail with a moving average or swing-low structure.
- Typical hold: a few weeks to a few months while the Stage-2 uptrend holds.

Sources: [Minervini SEPA/VCP/Trend Template](https://www.financialtechwiz.com/post/mark-minervini-trading-strategy/),
[ChartMill — Think & Trade Like a Champion filters](https://www.chartmill.com/documentation/stock-screener/fundamental-analysis-investing-strategies/464-Mark-Minervini-Strategy-Think-and-Trade-Like-a-Champion-Part-1),
[Deepvue — Trend Template screener](https://deepvue.com/screener/minervini-trend-template/),
[QuantStrategy.io — SEPA explained](https://quantstrategy.io/blog/sepa-strategy-explained-mastering-trend-following-with-mark/).

## 2. Risk management: ATR stops + fixed-fraction sizing

The single biggest determinant of whether a swing strategy survives is **risk
math, not entries**. The consensus from the literature:

- **Risk 0.5–2% of account equity per trade** (1% default). This lets you
  survive 10+ consecutive losers without a catastrophic drawdown.
- **ATR-based stops at 1.5–2× ATR** adapt to each stock's real volatility and
  cut premature stop-outs by up to ~35% versus flat percentage stops. ~1.5–2×
  ATR is cited as best risk-adjusted for 3–15 day holds.
- **Position size = dollar risk ÷ (ATR × multiplier)** — higher volatility
  automatically means a smaller position, lower volatility a larger one.
- **Portfolio heat ≤ ~6%** total simultaneous risk, so a correlated selloff
  across several open positions can't blow up the account.

Sources: [Trade That Swing — ATR trend strategy](https://tradethatswing.com/trend-trading-strategy-for-high-momentum-stocks-atr-based/),
[QuantVPS — ATR for stop placement](https://www.quantvps.com/blog/using-average-true-range-for-stop-loss-placement),
[TradeAlgo — swing risk management](https://www.tradealgo.com/trading-guides/stocks/swing-trading-risk-management-position-sizing-stop-losses-and-portfolio-rules),
[Alphaex Capital — ATR stops & sizing](https://www.alphaexcapital.com/prop-trading/risk-money-management-and-psychology-in-prop-trading/prop-risk-management-framework/atr-based-stop-loss-and-sizing).

## 3. The market regime filter (the bear-market seatbelt)

Long swing setups only earn their edge in a friendly tape. The simplest,
most-validated filter is the **200-day moving average on the index**:

- A widely cited S&P 500 study (1929–2020) found ~**+14%/yr** annualized when
  SPY is above its 200-day MA versus ~**−6%/yr** when below.
- The signal mechanically caught the major drawdowns — 2008, 2020, and 2022.
- Caveat: a moving average describes the past. Use it to **confirm** a trend
  (gate risk), not to predict one.

The bot's regime gate: no new long swing entries unless SPY is above its 200-day
MA, the 50-day is above the 200-day, and SPY isn't in a sharp 20-day selloff.

Sources: [QuantifiedStrategies — 200-day MA backtest](https://www.quantifiedstrategies.com/200-day-moving-average-trading-strategy/),
[Paper to Profit — 200-day regime change](https://papertoprofit.substack.com/p/how-i-rode-a-200-day-regime-change),
[Ashim Nandi — market regimes](https://medium.com/@ashimnandi07/market-regimes-adaptation-is-the-edge-b6c90504ca0f).

## 4. Earnings / binary-event risk (why we exit before earnings)

Holding a swing trade through an earnings report converts a risk-managed setup
into a coin flip:

- Individual stocks routinely **gap 5–20%** after earnings, in either
  direction. A gap can teleport price straight past your stop overnight — so
  your "1R risk" is fiction; the real risk is wherever it gaps to.
- Best practice: **close or reduce 2–3 trading days before** the report, or cut
  size by ~50% if you deliberately hold a small earnings position.

The bot enforces a hard earnings blackout: no new entries within N days
(default 3) of a known earnings date, and it flags open positions heading into
one.

Sources: [The Arca Labs — swing risk management](https://thearcalabs.com/en/insights/swing-trading-risk-management/),
[Tradewink — earnings trading guide](https://www.tradewink.com/learn/earnings-trading-strategy-guide),
[Trading Setups Review — managing gap risk](https://www.tradingsetupsreview.com/manage-gap-risk-swing-trading/).

## 5. Where the AI agent adds real edge

A pure-quant screen sees numbers; it can't read context. Recent research on
LLMs in markets shows their value is exactly in the **unstructured layer** the
quant screen is blind to:

- A review of **84 studies (2022–early 2025)** finds LLMs convert previously
  overlooked textual data — news, earnings-call transcripts, analyst notes,
  social sentiment — into actionable signals alongside structured metrics.
- The **TradingAgents** framework formalizes this as specialized LLM roles
  (fundamental / sentiment / technical analysts, bull & bear researchers, and a
  **risk-management team**) debating before a trade.

The lesson this project takes from that work: use the LLM as a **qualitative
confirmation-and-veto layer on top of a disciplined quant engine**, with a
hard-coded risk team it cannot override — *not* as a free-roaming "buy what
sounds bullish" bot (which is exactly what the project goal warned against).
The agent can confirm, caution (size down), or veto. It can never invent a
trade or add risk.

Sources: [LLMs in equity markets — review of 84 studies (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12421730/),
[TradingAgents — multi-agent LLM framework](https://tradingagents-ai.github.io/),
[TradingAgents (GitHub)](https://github.com/TauricResearch/TradingAgents),
[QuantInsti — trading using LLMs & sentiment](https://blog.quantinsti.com/trading-using-llm/).

## 6. How this maps to the code

| Research finding | Implemented in |
| --- | --- |
| Trend-template screen | [`strategy.py`](strategy.py) |
| ATR + MACD + ADX indicators | [`technical_indicators.py`](technical_indicators.py) |
| 1% risk, 1.5–2× ATR stop, 6% heat cap | [`risk_engine.py`](risk_engine.py), [`config.py`](config.py) |
| 200-day regime gate | `regime_check()` in [`screener.py`](screener.py) |
| Earnings blackout | [`earnings.py`](earnings.py) |
| LLM confirm/caution/veto layer | [`dossier.py`](dossier.py) + [`ai_agent.py`](ai_agent.py) |
| Event-driven validation with stops | [`backtest.py`](backtest.py) |
