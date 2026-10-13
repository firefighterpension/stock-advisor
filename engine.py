"""
Analysis engine for the Investment Advisor app.

Handles stocks, ETFs and mutual funds. Each asset is scored on six factors
(trend, momentum, valuation/cost, quality, risk, projection), combined into a
-100..+100 composite, and mapped to STRONG BUY / BUY / HOLD / SELL / STRONG SELL.

Not financial advice. Scores are rules-based screens built on past data.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
import pandas as pd

RF = 0.04  # annual risk-free rate used for Sharpe
BENCHMARK = "SPY"

DISCLAIMER = (
    "This tool is for education and research, not financial advice. Scores come "
    "from historical data and simple rules; they can't see news, earnings "
    "surprises, taxes or your personal situation. Consider a licensed advisor."
)

WEIGHTS = {
    "trend": 0.20,
    "momentum": 0.15,
    "valuation": 0.20,
    "quality": 0.15,
    "risk": 0.15,
    "projection": 0.15,
}


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
def _num(x):
    try:
        v = float(x)
        return None if math.isnan(v) or math.isinf(v) else v
    except (TypeError, ValueError):
        return None


def load_prices(ticker: str, period: str = "5y") -> pd.Series:
    import yfinance as yf

    df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    if df is None or df.empty:
        raise ValueError(f"No price data found for '{ticker}'.")
    s = df["Close"].dropna().astype(float)
    if getattr(s.index, "tz", None) is not None:
        s.index = s.index.tz_localize(None)
    return s


def get_info(ticker: str) -> dict:
    import yfinance as yf

    try:
        return yf.Ticker(ticker).info or {}
    except Exception:
        return {}


def asset_type(info: dict) -> str:
    qt = str(info.get("quoteType", "")).upper()
    return {"EQUITY": "Stock", "ETF": "ETF", "MUTUALFUND": "Mutual Fund"}.get(qt, "Other")


# --------------------------------------------------------------------------
# Indicators and risk
# --------------------------------------------------------------------------
def rsi(close: pd.Series, n: int = 14) -> float | None:
    d = close.diff()
    gain = d.clip(lower=0).rolling(n).mean()
    loss = (-d.clip(upper=0)).rolling(n).mean()
    rs = gain / loss.replace(0, np.nan)
    return _num((100 - 100 / (1 + rs)).iloc[-1])


def macd_hist(close: pd.Series) -> float | None:
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    return _num((macd - macd.ewm(span=9, adjust=False).mean()).iloc[-1])


def trailing_return(close: pd.Series, days: int) -> float | None:
    if len(close) <= days:
        return None
    return _num(close.iloc[-1] / close.iloc[-days - 1] - 1)


def risk_stats(close: pd.Series, bench: pd.Series | None) -> dict:
    rets = close.pct_change().dropna()
    vol = _num(rets.std() * math.sqrt(252))
    dd = close / close.cummax() - 1
    sharpe = None
    if vol:
        sharpe = _num((rets.mean() * 252 - RF) / vol)
    beta = None
    if bench is not None:
        j = pd.concat([rets, bench.pct_change().dropna()], axis=1, join="inner").dropna()
        if len(j) > 60 and j.iloc[:, 1].var() > 0:
            beta = _num(j.iloc[:, 0].cov(j.iloc[:, 1]) / j.iloc[:, 1].var())
    return {
        "volatility": vol,
        "max_drawdown": _num(dd.min()),
        "current_drawdown": _num(dd.iloc[-1]),
        "sharpe": sharpe,
        "beta": beta,
    }


# --------------------------------------------------------------------------
# Projection (bootstrapped Monte Carlo)
# --------------------------------------------------------------------------
def project(close: pd.Series, days: int, sims: int = 5000, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    rets = np.log(close / close.shift(1)).dropna().values[-756:]  # up to ~3y
    rets = rets - rets.mean() * 0.5  # shrink noisy historical drift toward zero
    draws = rng.choice(rets, size=(sims, days), replace=True)
    last = float(close.iloc[-1])
    paths = last * np.exp(draws.cumsum(axis=1))
    final = paths[:, -1]
    p10, p50, p90 = np.percentile(paths, [10, 50, 90], axis=0)
    return {
        "last": last,
        "days": days,
        "bear": float(np.percentile(final, 10)),
        "base": float(np.median(final)),
        "bull": float(np.percentile(final, 90)),
        "prob_up": float((final > last).mean()),
        "exp_return": float(np.median(final) / last - 1),
        "fan": {"p10": p10.tolist(), "p50": p50.tolist(), "p90": p90.tolist()},
    }


# --------------------------------------------------------------------------
# Factor scores: each returns (score in [-2, 2] or None, notes)
# --------------------------------------------------------------------------
def _clip(x):
    return max(-2.0, min(2.0, x))


def score_trend(price, sma50, sma200):
    if sma50 is None or sma200 is None:
        return None, ["Not enough history for trend"]
    s, notes = 0.0, []
    s += 0.75 if price > sma200 else -0.75
    notes.append("Price above 200-day average" if price > sma200 else "Price below 200-day average")
    s += 0.5 if price > sma50 else -0.5
    notes.append("Price above 50-day average" if price > sma50 else "Price below 50-day average")
    s += 0.75 if sma50 > sma200 else -0.75
    notes.append("50-day above 200-day (bullish cross)" if sma50 > sma200 else "50-day below 200-day (bearish cross)")
    return _clip(s), notes


def score_momentum(r, hist, r6, r12):
    s, notes, n = 0.0, [], 0
    if r is not None:
        n += 1
        if r < 30:
            s += 0.5; notes.append(f"Oversold (RSI {r:.0f}), possible bounce")
        elif r > 75:
            s -= 0.75; notes.append(f"Overbought (RSI {r:.0f}), pullback risk")
        else:
            notes.append(f"RSI neutral ({r:.0f})")
    if hist is not None:
        n += 1
        s += 0.5 if hist > 0 else -0.5
        notes.append("MACD momentum positive" if hist > 0 else "MACD momentum negative")
    if r6 is not None:
        n += 1
        if r6 > 0.10: s += 0.75
        elif r6 < -0.10: s -= 0.75
        notes.append(f"6-month return {r6:+.0%}")
    if r12 is not None:
        n += 1
        if r12 > 0.15: s += 0.5
        elif r12 < -0.15: s -= 0.5
        notes.append(f"12-month return {r12:+.0%}")
    return (_clip(s) if n else None), notes


def expense_ratio(info: dict):
    er = _num(info.get("annualReportExpenseRatio"))  # fraction, e.g. 0.0003
    if er is not None:
        return er
    net = _num(info.get("netExpenseRatio"))  # percent, e.g. 0.03
    return net / 100 if net is not None else None


def score_valuation(kind, info, price):
    s, notes, n = 0.0, [], 0
    if kind == "Stock":
        fpe = _num(info.get("forwardPE"))
        if fpe and fpe > 0:
            n += 1
            s += 1 if fpe < 15 else 0.5 if fpe < 25 else -0.5 if fpe < 40 else -1
            notes.append(f"Forward P/E {fpe:.1f}")
        peg = _num(info.get("pegRatio")) or _num(info.get("trailingPegRatio"))
        if peg and peg > 0:
            n += 1
            s += 1 if peg < 1 else 0 if peg < 2 else -0.5
            notes.append(f"PEG {peg:.2f}")
        tgt = _num(info.get("targetMeanPrice"))
        if tgt and price:
            n += 1
            up = tgt / price - 1
            s += 1 if up > 0.20 else 0.5 if up > 0.08 else -1 if up < -0.05 else 0
            notes.append(f"Analyst mean target implies {up:+.0%}")
    else:
        er = expense_ratio(info)
        if er is not None:
            n += 1
            s += 2 if er < 0.001 else 1.5 if er < 0.003 else 0.5 if er < 0.0075 else -0.5 if er < 0.015 else -1.5
            notes.append(f"Expense ratio {er:.2%}")
    return (_clip(s) if n else None), notes


def score_quality(kind, info):
    s, notes, n = 0.0, [], 0
    if kind == "Stock":
        m = _num(info.get("profitMargins"))
        if m is not None:
            n += 1
            s += 1 if m > 0.20 else 0.5 if m > 0.10 else -1 if m < 0 else 0
            notes.append(f"Profit margin {m:.0%}")
        roe = _num(info.get("returnOnEquity"))
        if roe is not None:
            n += 1
            s += 0.5 if roe > 0.15 else -1 if roe < 0 else 0
            notes.append(f"Return on equity {roe:.0%}")
        g = _num(info.get("revenueGrowth"))
        if g is not None:
            n += 1
            s += 0.5 if g > 0.10 else -0.5 if g < 0 else 0
            notes.append(f"Revenue growth {g:+.0%}")
        de = _num(info.get("debtToEquity"))  # reported in percent
        if de is not None:
            n += 1
            s += 0.5 if de < 50 else -0.5 if de > 200 else 0
            notes.append(f"Debt/equity {de/100:.1f}x")
    else:
        aum = _num(info.get("totalAssets"))
        if aum:
            n += 1
            s += 0.5 if aum > 1e9 else -1 if aum < 5e7 else 0
            notes.append(f"Fund size ${aum/1e9:.2f}B" if aum >= 1e9 else f"Fund size ${aum/1e6:.0f}M")
    return (_clip(s) if n else None), notes


def score_risk(kind, rk):
    s, notes, n = 0.0, [], 0
    sh = rk.get("sharpe")
    if sh is not None:
        n += 1
        s += 1 if sh > 1 else 0.5 if sh > 0.5 else -1 if sh < 0 else 0
        notes.append(f"Sharpe ratio {sh:.2f}")
    dd = rk.get("max_drawdown")
    if dd is not None:
        n += 1
        s += 0.5 if dd > -0.20 else -1 if dd < -0.40 else 0
        notes.append(f"Worst drawdown {dd:.0%}")
    v = rk.get("volatility")
    if v is not None:
        n += 1
        limit = 0.50 if kind == "Stock" else 0.30
        if v > limit:
            s -= 1
        notes.append(f"Volatility {v:.0%}/yr")
    return (_clip(s) if n else None), notes


def score_projection(proj):
    s = 0.0
    p, e = proj["prob_up"], proj["exp_return"]
    s += 1 if p > 0.60 else 0.5 if p > 0.52 else -1 if p < 0.45 else 0
    s += 1 if e > 0.03 else -1 if e < -0.03 else 0
    return _clip(s), [f"{p:.0%} simulated chance of gain over {proj['days']} trading days"]


def recommendation(composite: float) -> str:
    if composite >= 45: return "STRONG BUY"
    if composite >= 20: return "BUY"
    if composite > -20: return "HOLD"
    if composite > -45: return "SELL"
    return "STRONG SELL"


# --------------------------------------------------------------------------
# Main analysis
# --------------------------------------------------------------------------
_bench_cache: dict = {}


def _bench():
    if "b" not in _bench_cache:
        try:
            _bench_cache["b"] = load_prices(BENCHMARK, "5y")
        except Exception:
            _bench_cache["b"] = None
    return _bench_cache["b"]


def analyze(ticker: str, days: int = 30) -> dict:
    ticker = ticker.strip().upper()
    close = load_prices(ticker)
    info = get_info(ticker)
    return analyze_from_data(ticker, close, info, _bench(), days)


def analyze_from_data(ticker, close, info, bench, days=30) -> dict:
    kind = asset_type(info)
    if kind == "Other":
        kind = "Stock" if info.get("forwardPE") or info.get("profitMargins") else "ETF"
    price = float(close.iloc[-1])
    sma50 = _num(close.rolling(50).mean().iloc[-1])
    sma200 = _num(close.rolling(200).mean().iloc[-1])
    r6, r12 = trailing_return(close, 126), trailing_return(close, 252)
    rk = risk_stats(close, bench)
    proj = project(close, days)

    factors = {
        "trend": score_trend(price, sma50, sma200),
        "momentum": score_momentum(rsi(close), macd_hist(close), r6, r12),
        "valuation": score_valuation(kind, info, price),
        "quality": score_quality(kind, info),
        "risk": score_risk(kind, rk),
        "projection": score_projection(proj),
    }
    used = {k: v for k, v in factors.items() if v[0] is not None}
    wsum = sum(WEIGHTS[k] for k in used)
    composite = sum(WEIGHTS[k] * used[k][0] for k in used) / wsum / 2 * 100 if wsum else 0.0
    confidence = "High" if wsum >= 0.85 else "Medium" if wsum >= 0.60 else "Low"

    # Review level: roughly 2 standard deviations of a month's move below price.
    daily_vol = (rk["volatility"] or 0.3) / math.sqrt(252)
    review_level = price * (1 - min(0.35, 2 * daily_vol * math.sqrt(21)))

    return {
        "ticker": ticker,
        "name": info.get("longName") or info.get("shortName") or ticker,
        "type": kind,
        "category": info.get("category") or info.get("sector"),
        "price": price,
        "composite": round(composite, 1),
        "recommendation": recommendation(composite),
        "confidence": confidence,
        "factors": {k: {"score": v[0], "notes": v[1]} for k, v in factors.items()},
        "risk": rk,
        "returns": {"6m": r6, "12m": r12},
        "projection": proj,
        "review_level": review_level,
        "history": close,
    }


# --------------------------------------------------------------------------
# Positions and portfolio
# --------------------------------------------------------------------------
def position_view(res: dict, shares: float, cost_basis: float) -> dict:
    value = shares * res["price"]
    pl = (res["price"] / cost_basis - 1) if cost_basis else None
    rec = res["recommendation"]
    if rec in ("SELL", "STRONG SELL"):
        action = "Consider trimming or exiting"
        if pl is not None and pl > 0:
            action += " (selling a gain may trigger taxes; check holding period)"
        elif pl is not None and pl < 0:
            action += " (loss may be harvestable for tax purposes)"
    elif rec in ("BUY", "STRONG BUY"):
        action = "Consider adding on weakness"
    else:
        action = "Hold and monitor"
    return {"ticker": res["ticker"], "value": value, "unrealized_pl": pl, "action": action, "rec": rec}


def portfolio_summary(positions: list[dict], results: dict) -> dict:
    total = sum(p["value"] for p in positions) or 1.0
    for p in positions:
        p["weight"] = p["value"] / total
    flags = []
    for p in positions:
        if p["weight"] > 0.25:
            flags.append(f"{p['ticker']} is {p['weight']:.0%} of the portfolio (concentration risk).")
        if p["weight"] > 0.15 and p["rec"] in ("SELL", "STRONG SELL"):
            flags.append(f"{p['ticker']} is a large holding ({p['weight']:.0%}) with a {p['rec']} signal.")
    mix: dict = {}
    for p in positions:
        t = results[p["ticker"]]["type"]
        mix[t] = mix.get(t, 0) + p["weight"]
    betas = [(p["weight"], results[p["ticker"]]["risk"].get("beta")) for p in positions]
    betas = [(w, b) for w, b in betas if b is not None]
    wbeta = sum(w * b for w, b in betas) / sum(w for w, _ in betas) if betas else None
    avg_corr = None
    try:
        rets = pd.concat(
            {p["ticker"]: results[p["ticker"]]["history"].pct_change().iloc[-252:] for p in positions}, axis=1
        ).dropna()
        if rets.shape[1] > 1 and len(rets) > 60:
            c = rets.corr().values
            avg_corr = float((c.sum() - len(c)) / (len(c) * (len(c) - 1)))
            if avg_corr > 0.7:
                flags.append(f"Holdings are highly correlated (avg {avg_corr:.2f}); diversification is limited.")
    except Exception:
        pass
    if len(positions) < 5:
        flags.append("Fewer than 5 holdings; consider broader diversification (e.g., a total-market fund).")
    return {"total_value": total, "mix": mix, "weighted_beta": wbeta, "avg_correlation": avg_corr, "flags": flags}


# --------------------------------------------------------------------------
# Claude deep-dive reports (optional)
# --------------------------------------------------------------------------
MODEL = "claude-sonnet-5-5"


def _compact(res: dict) -> dict:
    p = res["projection"]
    return {
        "ticker": res["ticker"], "name": res["name"], "type": res["type"], "category": res["category"],
        "price": round(res["price"], 2), "composite_score": res["composite"],
        "rule_based_recommendation": res["recommendation"], "confidence": res["confidence"],
        "factors": res["factors"], "risk": res["risk"], "returns": res["returns"],
        "projection": {k: p[k] for k in ("days", "bear", "base", "bull", "prob_up", "exp_return")},
        "review_level": round(res["review_level"], 2),
    }


def _ask_claude(prompt: str, api_key: str | None) -> str | None:
    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    import anthropic

    msg = anthropic.Anthropic(api_key=key).messages.create(
        model=MODEL, max_tokens=1400, messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text


GEMINI_MODEL = "gemini-2.5-flash"


def _ask_gemini(prompt: str, api_key: str | None) -> str | None:
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    import requests

    resp = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": GEMINI_MODEL,
              "messages": [{"role": "user", "content": prompt}],
              "max_tokens": 1400},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _ask_llm(prompt: str, api_key: str | None = None, gemini_key: str | None = None) -> str | None:
    """Prefer Gemini (free tier) when its key is available; otherwise Claude."""
    if gemini_key or os.getenv("GEMINI_API_KEY"):
        return _ask_gemini(prompt, gemini_key)
    return _ask_claude(prompt, api_key)


def ai_asset_report(res: dict, position: dict | None = None, api_key: str | None = None, gemini_key: str | None = None) -> str | None:
    data = {"analysis": _compact(res), "position": position}
    prompt = (
        "You are a careful, independent investment research analyst. Using ONLY the quantitative "
        "data below (do not invent figures, news or earnings), write a concise report with these "
        "sections: Verdict (buy/hold/sell and why, noting where you agree or disagree with the "
        "rule-based call), Thesis, Key Risks, What Would Change the View, and Suggested Next Steps "
        "(position-sizing and entry/exit discipline in general terms; if a position is given, say "
        "whether to add, hold or trim). For a fund or ETF, focus on cost, diversification and role "
        "in a portfolio. State limits of the data. End with a one-line note that this is not "
        "financial advice.\n\n" + json.dumps(data, default=str)
    )
    return _ask_llm(prompt, api_key, gemini_key)


def ai_portfolio_report(positions: list[dict], summary: dict, results: dict, api_key: str | None = None, gemini_key: str | None = None) -> str | None:
    data = {
        "summary": summary,
        "positions": [
            {**p, "analysis": {k: _compact(results[p["ticker"]])[k]
                               for k in ("type", "composite_score", "rule_based_recommendation", "risk")}}
            for p in positions
        ],
    }
    prompt = (
        "You are a careful portfolio analyst. Using ONLY the data below, write a brief portfolio "
        "review: overall health, biggest risks (concentration, correlation, beta), which holdings "
        "look strongest and weakest and why, and a prioritized list of rebalancing ideas. Do not "
        "invent figures. End with a one-line note that this is not financial advice.\n\n"
        + json.dumps(data, default=str)
    )
    return _ask_llm(prompt, api_key, gemini_key)


ADVISOR_BRIEF = """You are Marcel's personal investment advisor, answering in a chat box inside his portfolio app. Follow these rules strictly:
1. Think in structural catalysts (policy, subsidies, procurement, secular demand) — never chase headlines or delayed filings.
2. Favor low-cost compounding vehicles, strong ROE and free cash flow, secular tailwinds. No meme or speculative assets.
3. Be mathematically rigorous: numbered actions with exact allocations and rationale. Never vague platitudes.
4. Act as risk officer: challenge assumptions, flag concentration and overlap, consider taxes and account location (taxable brokerage vs 457(b)).
Use ONLY the portfolio context and analysis data given. Do not invent prices, news, or earnings. Keep answers tight and readable on a phone. End with a one-line note that this is not financial advice."""


def ask_advisor(question: str, context: str, api_key: str | None = None, gemini_key: str | None = None) -> str | None:
    prompt = ADVISOR_BRIEF + "\n\nPortfolio context:\n" + context + "\n\nQuestion: " + question
    return _ask_llm(prompt, api_key, gemini_key)
