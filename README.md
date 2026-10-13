# Investment Advisor

A standalone app that analyzes stocks, ETFs and mutual funds and gives
BUY / HOLD / SELL calls with projections, risk stats and (optionally)
Claude-written deep-dive reports. It can also review your portfolio.

## Run

Easiest: double-click `run.bat` (Windows) or `run.command` (Mac). To put it online and on your phone, see `DEPLOY.md`.

Or from a terminal:

```
pip install -r requirements.txt
streamlit run app.py
```

Optional: `export ANTHROPIC_API_KEY=...` (or paste it in the sidebar) to enable
written reports.

## How it works

Each asset gets six factor scores from -2 to +2, weighted into a -100..+100 composite:

| Factor | Stocks | ETFs / mutual funds |
|---|---|---|
| Trend (20%) | 50/200-day averages | same |
| Momentum (15%) | RSI, MACD, 6/12-month returns | same |
| Valuation (20%) | forward P/E, PEG, analyst target | expense ratio |
| Quality (15%) | margins, ROE, growth, debt | fund size |
| Risk (15%) | Sharpe, drawdown, volatility | same |
| Projection (15%) | Monte Carlo odds and expected return | same |

Missing data is dropped and weights renormalized; the confidence label drops
accordingly. Calls: >= +45 strong buy, >= +20 buy, within ±20 hold, <= -20 sell,
<= -45 strong sell.

The Portfolio tab adds position-level actions (add / hold / trim, with a tax
reminder), concentration, correlation and beta checks.

## Limits

- Data comes from Yahoo Finance via yfinance (unofficial, can be delayed or incomplete).
- Valuation is absolute, not sector-relative. Fund analysis uses price history and
  cost only, not holdings.
- Projections are statistical simulations, not predictions.
- Not financial advice.

## Files

- `engine.py`: data, scoring, projections, portfolio logic, Claude prompts
- `app.py`: Streamlit interface
