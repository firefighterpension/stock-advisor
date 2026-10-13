"""Investment Advisor: standalone Streamlit app.  Run:  streamlit run app.py"""
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import engine

st.set_page_config(page_title="Investment Advisor", page_icon="📈", layout="centered")

INK, SLATE, LINE = "#14202B", "#5B6B7A", "#DCE3E8"
BUY, HOLD, SELL = "#1F8A70", "#8A97A3", "#B8453A"
CARD = "#FFFFFF"
REC_COLOR = {"STRONG BUY": BUY, "BUY": BUY, "HOLD": HOLD, "SELL": SELL, "STRONG SELL": SELL}
REC_TEXT = {"STRONG BUY": "Strong buy", "BUY": "Buy", "HOLD": "Hold", "SELL": "Sell", "STRONG SELL": "Strong sell"}

HOLDINGS = ["NVDA", "MU", "SWLGX", "PLTR", "AVGO", "QQQM", "SNXFX"]

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400;500;600;700&display=swap');
.stApp, .stMarkdown, .stMarkdown p, label, input, button, textarea {{
  font-family: 'Schibsted Grotesk', system-ui, sans-serif;
}}
.stApp {{ background: #F3F6F8; color: {INK}; }}
header[data-testid="stHeader"] {{ background: transparent; }}
#MainMenu, footer {{ visibility: hidden; }}
.block-container {{ max-width: 780px; padding-top: 2rem; padding-bottom: 4rem; }}
h1 {{ font-weight: 700; letter-spacing: -0.02em; font-size: 2rem; padding-bottom: .2rem; }}
.sub {{ color: {SLATE}; margin: 0 0 1.2rem; }}
div[data-testid="stForm"] {{ border: 0; padding: 0; }}
.stTextInput input {{ background: #fff; border: 1px solid {LINE}; border-radius: 12px; padding: .75rem .95rem; font-size: 1rem; }}
.stButton > button, .stFormSubmitButton > button {{
  border-radius: 12px; border: 1px solid {LINE}; background: #fff; color: {INK}; font-weight: 600; padding: .6rem 1.1rem;
}}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{ background: {INK}; color: #fff; border-color: {INK}; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 600; }}
/* holdings quick-pick */
.hold-label {{ color: {SLATE}; font-size: .85rem; font-weight: 600; margin: 0 0 .35rem; text-transform: uppercase; letter-spacing: .04em; }}
div[data-testid="stSegmentedControl"] {{ margin-bottom: .4rem; }}
/* hero verdict card */
.hero {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 18px; padding: 1.4rem 1.5rem 1.2rem;
  margin: 1rem 0 1.2rem; box-shadow: 0 2px 10px rgba(20,32,43,.05); border-top: 5px solid {INK}; }}
.hero-top {{ display: flex; align-items: baseline; gap: .7rem; flex-wrap: wrap; }}
.hero-ticker {{ font-size: 2.4rem; font-weight: 700; letter-spacing: -0.02em; line-height: 1; }}
.hero-price {{ font-size: 1.25rem; font-weight: 600; color: {SLATE}; }}
.hero-name {{ color: {SLATE}; margin-top: .3rem; font-size: .95rem; }}
.hero-verdict {{ display: flex; align-items: center; gap: .9rem; margin-top: 1rem; flex-wrap: wrap; }}
.score-big {{ font-size: 2rem; font-weight: 700; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }}
.reason {{ color: {SLATE}; margin-top: .45rem; font-size: .95rem; }}
.meter {{ position: relative; height: 10px; border-radius: 99px; margin: 1.3rem 0 .4rem;
  background: linear-gradient(90deg, {SELL}, #C9D1D8 50%, {BUY}); }}
.marker {{ position: absolute; top: -6px; width: 22px; height: 22px; border-radius: 50%;
  background: #fff; border: 3px solid {INK}; transform: translateX(-50%); box-shadow: 0 1px 4px rgba(20,32,43,.25); }}
.meter-labels {{ display: flex; justify-content: space-between; color: {SLATE}; font-size: .8rem; }}
.stats {{ display: flex; gap: 2.2rem; margin: 1.4rem 0 1rem; flex-wrap: wrap; }}
.stat .v {{ font-size: 1.35rem; font-weight: 700; font-variant-numeric: tabular-nums; letter-spacing: -0.01em; }}
.stat .l {{ color: {SLATE}; font-size: .85rem; margin-top: .15rem; }}
.pill {{ display: inline-block; padding: .3rem .9rem; border-radius: 99px; font-size: .95rem; font-weight: 700; color: #fff; }}
/* factor cards */
.fcard {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 14px; padding: .85rem 1.05rem; margin-bottom: .6rem; }}
.factor {{ display: grid; grid-template-columns: 110px 1fr; gap: .15rem 1rem; align-items: center; }}
.factor .n {{ font-weight: 700; }}
.bar {{ position: relative; height: 7px; background: #E6EBEF; border-radius: 99px; margin-top: .45rem; }}
.bar i {{ position: absolute; top: 0; height: 100%; border-radius: 99px; }}
.bar b {{ position: absolute; left: 50%; top: -3px; width: 1px; height: 13px; background: {SLATE}; opacity: .5; }}
.notes {{ grid-column: 2; color: {SLATE}; font-size: .88rem; margin-top: .25rem; }}
/* portfolio cards */
.prow {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 14px; padding: .95rem 1.1rem; margin-bottom: .65rem; }}
.prow .top {{ display: flex; align-items: center; justify-content: space-between; gap: .8rem; flex-wrap: wrap; }}
.prow .t {{ font-weight: 700; font-size: 1.05rem; }}
.prow .vals {{ display: flex; gap: 1.4rem; align-items: baseline; font-variant-numeric: tabular-nums; }}
.prow .act {{ color: {SLATE}; font-size: .9rem; margin-top: .35rem; }}
.muted {{ color: {SLATE}; font-size: .85rem; }}
.fine {{ color: {SLATE}; font-size: .78rem; margin-top: 3rem; }}
.chart-card {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 18px; padding: 1rem .8rem .4rem; margin-bottom: 1rem; }}
@media (max-width: 560px) {{
  .hero {{ padding: 1.1rem 1.1rem 1rem; border-radius: 15px; }}
  .hero-ticker {{ font-size: 2rem; }}
  .score-big {{ font-size: 1.6rem; }}
  .stats {{ gap: 1.3rem; }}
  .factor {{ grid-template-columns: 92px 1fr; }}
  .block-container {{ padding-top: 1.2rem; }}
}}
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


def factor_cards(res: dict) -> str:
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
        out.append(
            f"<div class='fcard'><div class='factor'><div class='n'>{name.title()}</div>{bar}"
            f"<div class='notes'>{notes}</div></div></div>")
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
        height=320, margin=dict(l=0, r=0, t=8, b=0), showlegend=False,
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
    color = REC_COLOR[res["recommendation"]]
    st.markdown(
        f"<div class='hero' style='border-top-color:{color}'>"
        f"<div class='hero-top'><span class='hero-ticker'>{res['ticker']}</span>"
        f"<span class='hero-price'>{money(res['price'])}</span></div>"
        f"<div class='hero-name'>{res['name']} · {kind}</div>"
        f"<div class='hero-verdict'>{pill(res['recommendation'])}"
        f"<span class='score-big' style='color:{color}'>{res['composite']:+.0f}</span></div>"
        f"<div class='reason'>{verdict} — {reason} Confidence: {res['confidence'].lower()}.</div>"
        + meter(res["composite"]) + "</div>"
        + "<div class='stats'>"
        f"<div class='stat'><div class='v'>{money(p['base'])} <span style='font-size:.9rem;color:{SLATE}'>{p['exp_return']:+.1%}</span></div><div class='l'>Base case in {p['days']} trading days</div></div>"
        f"<div class='stat'><div class='v'>{money(p['bear'])} – {money(p['bull'])}</div><div class='l'>Likely range</div></div>"
        f"<div class='stat'><div class='v'>{p['prob_up']:.0%}</div><div class='l'>Chance of gain</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    with st.container():
        st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
        st.plotly_chart(fan_chart(res), use_container_width=True, config={"displayModeBar": False}, key=f"chart-{ctx}-{res['ticker']}")
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='muted'>Dotted red line: review level near {money(res['review_level'])}, where a drop is unusual enough to re-check your thesis.</div>", unsafe_allow_html=True)

    if position:
        pl = position["unrealized_pl"]
        st.markdown(
            f"<div class='fcard' style='margin-top:1.1rem'><div style='font-weight:700;font-size:1.05rem'>Your position: {money(position['value'])}"
            + (f" ({pl:+.1%})" if pl is not None else "")
            + f"</div><div class='reason'>{position['action']}.</div></div>",
            unsafe_allow_html=True,
        )

    with st.expander("Why this call"):
        st.markdown(factor_cards(res), unsafe_allow_html=True)
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
for k, v in {"results": [], "reports": {}, "api_key": "", "days": 30, "port": None,
             "hold_pick": None, "hold_pick_done": None}.items():
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
    st.markdown("<div class='hold-label'>Your holdings — tap to analyze</div>", unsafe_allow_html=True)
    pick = st.segmented_control("Your holdings", HOLDINGS, selection_mode="single",
                               key="hold_pick", label_visibility="collapsed")
    if pick and st.session_state.hold_pick_done != pick:
        st.session_state.hold_pick_done = pick
        with st.spinner(f"Analyzing {pick}..."):
            try:
                st.session_state.results = [run_analysis(pick, st.session_state.days)]
            except Exception as e:
                st.error(f"Couldn't analyze {pick}: {e} Check the ticker symbol and try again.")

    with st.form("search"):
        c1, c2 = st.columns([4, 1])
        raw = c1.text_input("Tickers", placeholder="AAPL, VTI, VFIAX", label_visibility="collapsed")
        go_btn = c2.form_submit_button("Analyze", type="primary", use_container_width=True)
    if go_btn and raw.strip():
        st.session_state.hold_pick_done = None
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
            f"<p class='muted' style='margin-top:1rem'>Tap one of your holdings above, or enter any ticker symbols separated by commas. "
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
        pd.DataFrame({"Ticker": pd.Series(dtype=str), "Shares": pd.Series(dtype=float),
                      "Cost per share": pd.Series(dtype=float)}),
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
        for p in sorted(positions, key=lambda x: -x["value"]):
            pl = "" if p["unrealized_pl"] is None else f"{p['unrealized_pl']:+.1%}"
            st.markdown(
                f"<div class='prow'><div class='top'><span class='t'>{p['ticker']}</span>{pill(p['rec'])}</div>"
                f"<div class='top' style='margin-top:.35rem'><span class='vals'><span>{money(p['value'])} · {p['weight']:.0%}</span>"
                f"<span class='muted'>{pl}</span></span></div>"
                f"<div class='act'>{p['action']}</div></div>",
                unsafe_allow_html=True)
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
