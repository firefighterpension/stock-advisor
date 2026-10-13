"""Investment Advisor: standalone Streamlit app.  Run:  streamlit run app.py"""
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import engine

st.set_page_config(page_title="Investment Advisor", page_icon="📈", layout="centered")

INK, SLATE, LINE = "#14202B", "#5B6B7A", "#DCE3E8"
BUY, HOLD, SELL = "#1F8A70", "#8A97A3", "#B8453A"
REC_COLOR = {"STRONG BUY": BUY, "BUY": BUY, "HOLD": HOLD, "SELL": SELL, "STRONG SELL": SELL}
REC_TEXT = {"STRONG BUY": "Strong buy", "BUY": "Buy", "HOLD": "Hold", "SELL": "Sell", "STRONG SELL": "Strong sell"}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400;500;600;700&display=swap');
.stApp, .stMarkdown, .stMarkdown p, label, input, button, textarea {{
  font-family: 'Schibsted Grotesk', system-ui, sans-serif;
}}
.stApp {{ background: #F3F6F8; color: {INK}; }}
header[data-testid="stHeader"] {{ background: transparent; }}
#MainMenu, footer {{ visibility: hidden; }}
.block-container {{ max-width: 760px; padding-top: 2.2rem; padding-bottom: 4rem; }}
h1 {{ font-weight: 700; letter-spacing: -0.02em; font-size: 2rem; padding-bottom: .2rem; }}
.sub {{ color: {SLATE}; margin: 0 0 1.4rem; }}
div[data-testid="stForm"] {{ border: 0; padding: 0; }}
.stTextInput input {{ background: #fff; border: 1px solid {LINE}; border-radius: 10px; padding: .7rem .9rem; }}
.stButton > button, .stFormSubmitButton > button {{
  border-radius: 10px; border: 1px solid {LINE}; background: #fff; color: {INK}; font-weight: 600; padding: .55rem 1.1rem;
}}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{ background: {INK}; color: #fff; border-color: {INK}; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 600; }}
.hero-ticker {{ font-size: 2.6rem; font-weight: 700; letter-spacing: -0.02em; line-height: 1; }}
.hero-name {{ color: {SLATE}; margin-top: .25rem; }}
.verdict {{ font-size: 1.5rem; font-weight: 600; margin-top: 1.2rem; line-height: 1.25; }}
.reason {{ color: {SLATE}; margin-top: .3rem; }}
.meter {{ position: relative; height: 8px; border-radius: 99px; margin: 1.7rem 0 .45rem;
  background: linear-gradient(90deg, {SELL}, #C9D1D8 50%, {BUY}); }}
.marker {{ position: absolute; top: -6px; width: 20px; height: 20px; border-radius: 50%;
  background: #fff; border: 3px solid {INK}; transform: translateX(-50%); }}
.meter-labels {{ display: flex; justify-content: space-between; color: {SLATE}; font-size: .8rem; }}
.stats {{ display: flex; gap: 2.4rem; margin: 1.6rem 0 1rem; flex-wrap: wrap; }}
.stat .v {{ font-size: 1.3rem; font-weight: 600; font-variant-numeric: tabular-nums; }}
.stat .l {{ color: {SLATE}; font-size: .85rem; }}
.pill {{ display: inline-block; padding: .12rem .65rem; border-radius: 99px; font-size: .8rem; font-weight: 600; color: #fff; }}
.factor {{ display: grid; grid-template-columns: 110px 1fr; gap: .15rem 1rem; padding: .75rem 0; border-bottom: 1px solid {LINE}; }}
.factor .n {{ font-weight: 600; }}
.bar {{ position: relative; height: 6px; background: #E6EBEF; border-radius: 99px; margin-top: .45rem; }}
.bar i {{ position: absolute; top: 0; height: 100%; border-radius: 99px; }}
.bar b {{ position: absolute; left: 50%; top: -3px; width: 1px; height: 12px; background: {SLATE}; opacity: .5; }}
.notes {{ grid-column: 2; color: {SLATE}; font-size: .88rem; }}
.row {{ display: grid; grid-template-columns: 1.1fr .9fr .6fr .8fr; gap: .2rem 1rem; align-items: center;
  padding: .8rem 0; border-bottom: 1px solid {LINE}; }}
.row .t {{ font-weight: 600; }}
.row .act {{ grid-column: 1 / -1; color: {SLATE}; font-size: .88rem; }}
.muted {{ color: {SLATE}; font-size: .85rem; }}
.fine {{ color: {SLATE}; font-size: .78rem; margin-top: 3rem; }}
@media (max-width: 560px) {{ .row {{ grid-template-columns: 1fr 1fr; }} .stats {{ gap: 1.4rem; }} }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ----------------------------- helpers ---------------------------------
@st.cache_data(ttl=900, show_spinner=False)
def run_analysis(ticker: str, days: int) -> dict:
    return engine.analyze(ticker, days)


def pill(rec: str) -> str:
    return f"<span class='pill' style='background:{REC_COLOR[rec]}'>{REC_TEXT[rec]}</span>"


def money(x: float) -> str:
    return f"${x:,.2f}" if x < 1000 else f"${x:,.0f}"


def headline(res: dict) -> tuple[str, str]:
    rec = res["recommendation"]
    verdict = {
        "STRONG BUY": "Strong case to buy",
        "BUY": "Leans buy",
        "HOLD": "Hold for now",
        "SELL": "Leans sell",
        "STRONG SELL": "Strong case to sell",
    }[rec]
    names = {"trend": "price trend", "momentum": "momentum", "valuation": "valuation",
             "quality": "business quality", "risk": "risk profile", "projection": "projected odds"}
    if res["type"] != "Stock":
        names["valuation"], names["quality"] = "low cost", "fund size"
    ranked = sorted(((v["score"], k) for k, v in res["factors"].items() if v["score"] is not None))
    if len(ranked) < 2:
        return verdict, "Not enough data for a full picture."
    strong = f"Strongest: {names[ranked[-1][1]]}."
    if ranked[0][0] > 0:
        return verdict, f"{strong} No clear weak spots."
    return verdict, f"{strong} Weakest: {names[ranked[0][1]]}."


def meter(composite: float) -> str:
    pos = max(0, min(100, (composite + 100) / 2))
    return (f"<div class='meter'><div class='marker' style='left:{pos}%'></div></div>"
            "<div class='meter-labels'><span>Sell</span><span>Hold</span><span>Buy</span></div>")


def factor_rows(res: dict) -> str:
    out = []
    for name, f in res["factors"].items():
        s = f["score"]
        if s is None:
            bar = "<div class='bar'><b></b></div>"
        else:
            w = abs(s) / 2 * 50
            left = 50 if s >= 0 else 50 - w
            color = BUY if s >= 0 else SELL
            bar = f"<div class='bar'><b></b><i style='left:{left}%;width:{w}%;background:{color}'></i></div>"
        notes = "; ".join(f["notes"]) if f["notes"] else "No data available"
        out.append(f"<div class='factor'><div class='n'>{name.title()}</div>{bar}<div class='notes'>{notes}</div></div>")
    return "".join(out)


def fan_chart(res: dict) -> go.Figure:
    hist = res["history"].iloc[-180:]
    fan = res["projection"]["fan"]
    future = pd.bdate_range(hist.index[-1], periods=len(fan["p50"]) + 1)[1:]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist.values, line=dict(color=INK, width=2), name="Price"))
    fig.add_trace(go.Scatter(x=future, y=fan["p90"], line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=future, y=fan["p10"], fill="tonexty", fillcolor="rgba(31,138,112,0.16)",
                             line=dict(width=0), name="Likely range"))
    fig.add_trace(go.Scatter(x=future, y=fan["p50"], line=dict(color=BUY, width=2, dash="dot"), name="Base case"))
    fig.add_hline(y=res["review_level"], line=dict(color=SELL, width=1, dash="dot"))
    fig.update_layout(
        height=300, margin=dict(l=0, r=0, t=8, b=0), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, showline=False, tickfont=dict(color=SLATE)),
        yaxis=dict(gridcolor="#E6EBEF", zeroline=False, tickfont=dict(color=SLATE), side="right"),
        font=dict(family="Schibsted Grotesk, sans-serif"),
    )
    return fig


def asset_view(res: dict, position: dict | None = None, ctx: str = "r"):
    p, rk = res["projection"], res["risk"]
    verdict, reason = headline(res)
    kind = res["type"] + (f" · {res['category']}" if res.get("category") else "")
    st.markdown(
        f"<div class='hero-ticker'>{res['ticker']} <span style='font-size:1.1rem;font-weight:500;color:{SLATE}'>{money(res['price'])}</span></div>"
        f"<div class='hero-name'>{res['name']} · {kind}</div>"
        f"<div class='verdict' style='color:{REC_COLOR[res['recommendation']]}'>{verdict}</div>"
        f"<div class='reason'>{reason} Confidence: {res['confidence'].lower()}.</div>"
        + meter(res["composite"])
        + "<div class='stats'>"
        f"<div class='stat'><div class='v'>{money(p['base'])} <span style='font-size:.9rem;color:{SLATE}'>{p['exp_return']:+.1%}</span></div><div class='l'>Base case in {p['days']} trading days</div></div>"
        f"<div class='stat'><div class='v'>{money(p['bear'])} – {money(p['bull'])}</div><div class='l'>Likely range</div></div>"
        f"<div class='stat'><div class='v'>{p['prob_up']:.0%}</div><div class='l'>Chance of gain</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(fan_chart(res), use_container_width=True, config={"displayModeBar": False}, key=f"chart-{ctx}-{res['ticker']}")
    st.markdown(f"<div class='muted'>Dotted red line: review level near {money(res['review_level'])}, where a drop is unusual enough to re-check your thesis.</div>", unsafe_allow_html=True)

    if position:
        pl = position["unrealized_pl"]
        st.markdown(
            f"<div class='verdict' style='font-size:1.1rem;margin-top:1.4rem'>Your position: {money(position['value'])}"
            + (f" ({pl:+.1%})" if pl is not None else "")
            + f"</div><div class='reason'>{position['action']}.</div>",
            unsafe_allow_html=True,
        )

    with st.expander("Why this call"):
        st.markdown(factor_rows(res), unsafe_allow_html=True)
        beta = rk["beta"]
        st.markdown(
            f"<div class='muted' style='margin-top:.8rem'>Volatility {rk['volatility']:.0%} a year · "
            f"worst drop {rk['max_drawdown']:.0%} · Sharpe {rk['sharpe']:.2f}"
            + (f" · beta {beta:.2f}" if beta is not None else "") + "</div>"
            if None not in (rk["volatility"], rk["max_drawdown"], rk["sharpe"]) else "",
            unsafe_allow_html=True,
        )

    key = f"report-{res['ticker']}-{p['days']}"
    btn_key = f"btn-{ctx}-{key}"
    if key in st.session_state.reports:
        st.markdown("#### Full report")
        st.markdown(st.session_state.reports[key])
    elif st.button("Write full report", key=btn_key):
        with st.spinner("Writing report..."):
            try:
                txt = engine.ai_asset_report(res, position, api_key=st.session_state.api_key or None)
            except Exception as e:
                txt = None
                st.error(f"Report failed: {e}")
        if txt:
            st.session_state.reports[key] = txt
            st.rerun()
        elif not (st.session_state.api_key or os.getenv("ANTHROPIC_API_KEY")):
            st.info("Add an Anthropic API key under Settings to write full reports.")


# ------------------------------- state ---------------------------------
for k, v in {"results": [], "reports": {}, "api_key": "", "days": 30, "port": None}.items():
    st.session_state.setdefault(k, v)

# -------------------------------- header --------------------------------
top, gear = st.columns([5, 1])
with top:
    st.markdown("# Investment Advisor")
    st.markdown("<p class='sub'>Plain-English buy, hold and sell calls for stocks, ETFs and mutual funds.</p>", unsafe_allow_html=True)
with gear:
    with st.popover("Settings"):
        st.session_state.days = st.slider("Look ahead (trading days)", 10, 252, st.session_state.days)
        st.session_state.api_key = st.text_input(
            "Anthropic API key", type="password",
            value=st.session_state.api_key or os.getenv("ANTHROPIC_API_KEY", ""),
            help="Only needed for written reports. Kept for this session.")

tab_a, tab_p = st.tabs(["Research", "My portfolio"])

# -------------------------------- research -------------------------------
with tab_a:
    with st.form("search"):
        c1, c2 = st.columns([4, 1])
        raw = c1.text_input("Tickers", placeholder="AAPL, VTI, VFIAX", label_visibility="collapsed")
        go_btn = c2.form_submit_button("Analyze", type="primary", use_container_width=True)
    if go_btn and raw.strip():
        results = []
        for t in [x.strip().upper() for x in raw.replace(";", ",").split(",") if x.strip()]:
            try:
                with st.spinner(f"Analyzing {t}..."):
                    results.append(run_analysis(t, st.session_state.days))
            except Exception as e:
                st.error(f"Couldn't analyze {t}: {e} Check the ticker symbol and try again.")
        st.session_state.results = results

    results = st.session_state.results
    if not results:
        st.markdown(
            f"<p class='muted' style='margin-top:1rem'>Enter one or more ticker symbols, separated by commas. "
            f"Try a stock like AAPL, an ETF like VTI or a mutual fund like VFIAX.</p>",
            unsafe_allow_html=True)
    elif len(results) == 1:
        asset_view(results[0])
    else:
        tabs = st.tabs([f"{r['ticker']}" for r in results])
        for t, r in zip(tabs, results):
            with t:
                asset_view(r)

# -------------------------------- portfolio ------------------------------
with tab_p:
    st.markdown("<p class='muted'>Enter what you own. Cost basis is the price you paid per share.</p>", unsafe_allow_html=True)
    df = st.data_editor(
        pd.DataFrame({"Ticker": ["AAPL", "VTI"], "Shares": [10.0, 20.0], "Cost per share": [150.0, 200.0]}),
        num_rows="dynamic", use_container_width=True, hide_index=True, key="port_editor")
    if st.button("Review portfolio", type="primary"):
        res_map, positions = {}, []
        for _, row in df.dropna(subset=["Ticker", "Shares"]).iterrows():
            t = str(row["Ticker"]).strip().upper()
            if not t:
                continue
            try:
                with st.spinner(f"Analyzing {t}..."):
                    res_map[t] = run_analysis(t, st.session_state.days)
                cost = row["Cost per share"]
                positions.append(engine.position_view(res_map[t], float(row["Shares"]),
                                                      float(cost) if pd.notna(cost) else 0.0))
            except Exception as e:
                st.error(f"Couldn't analyze {t}: {e} Check the ticker symbol and try again.")
        if positions:
            st.session_state.port = (positions, engine.portfolio_summary(positions, res_map), res_map)

    if st.session_state.port:
        positions, summ, res_map = st.session_state.port
        beta = summ["weighted_beta"]
        st.markdown(
            "<div class='stats'>"
            f"<div class='stat'><div class='v'>{money(summ['total_value'])}</div><div class='l'>Total value</div></div>"
            f"<div class='stat'><div class='v'>{'n/a' if beta is None else f'{beta:.2f}'}</div><div class='l'>Sensitivity to the market (beta)</div></div>"
            f"<div class='stat'><div class='v'>{len(positions)}</div><div class='l'>Holdings</div></div></div>",
            unsafe_allow_html=True)
        rows = []
        for p in sorted(positions, key=lambda x: -x["value"]):
            pl = "" if p["unrealized_pl"] is None else f"{p['unrealized_pl']:+.1%}"
            rows.append(
                f"<div class='row'><div class='t'>{p['ticker']}</div><div>{money(p['value'])} · {p['weight']:.0%}</div>"
                f"<div class='muted'>{pl}</div><div>{pill(p['rec'])}</div><div class='act'>{p['action']}</div></div>")
        st.markdown("".join(rows), unsafe_allow_html=True)
        if summ["flags"]:
            st.markdown("#### Worth a look")
            for f in summ["flags"]:
                st.markdown(f"- {f}")
        if "portfolio-report" in st.session_state.reports:
            st.markdown("#### Portfolio review")
            st.markdown(st.session_state.reports["portfolio-report"])
        elif st.button("Write portfolio review"):
            with st.spinner("Writing review..."):
                try:
                    txt = engine.ai_portfolio_report(positions, summ, res_map, api_key=st.session_state.api_key or None)
                except Exception as e:
                    txt = None
                    st.error(f"Review failed: {e}")
            if txt:
                st.session_state.reports["portfolio-report"] = txt
                st.rerun()
            elif not (st.session_state.api_key or os.getenv("ANTHROPIC_API_KEY")):
                st.info("Add an Anthropic API key under Settings to write reviews.")
        pick = st.selectbox("See details for", [p["ticker"] for p in positions])
        asset_view(res_map[pick], next(p for p in positions if p["ticker"] == pick), ctx="port")

st.markdown(f"<div class='fine'>{engine.DISCLAIMER}</div>", unsafe_allow_html=True)
