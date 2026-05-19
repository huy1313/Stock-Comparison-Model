"""
app.py — Streamlit web interface
=================================
Structure:
  1. Sidebar — Top Growth Stocks Today (live, refreshed every 5 min)
  2. Header + searchable ticker dropdowns (embedded list, no API dependency)
  3. Summary table + metric explanations
  4. Four separate full-width interactive charts
  5. Raw Data + Calculations tables with color coding
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf
from data import build_dataset, calculate_metrics

# ── Page Setup ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Stock Comparison Model",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Popular Tickers (embedded — no API call needed, instant autocomplete) ─────
# Format: ("TICKER", "Company Name")

POPULAR_TICKERS = [
    ("AAPL","Apple Inc."), ("MSFT","Microsoft Corporation"), ("GOOGL","Alphabet Inc. (Google)"),
    ("GOOG","Alphabet Inc. Class C"), ("AMZN","Amazon.com Inc."), ("NVDA","NVIDIA Corporation"),
    ("TSLA","Tesla Inc."), ("META","Meta Platforms Inc."), ("BRK.B","Berkshire Hathaway Inc."),
    ("JPM","JPMorgan Chase & Co."), ("V","Visa Inc."), ("JNJ","Johnson & Johnson"),
    ("WMT","Walmart Inc."), ("PG","Procter & Gamble Co."), ("MA","Mastercard Inc."),
    ("HD","Home Depot Inc."), ("DIS","Walt Disney Co."), ("BAC","Bank of America Corp."),
    ("ADBE","Adobe Inc."), ("CRM","Salesforce Inc."), ("NFLX","Netflix Inc."),
    ("INTC","Intel Corporation"), ("AMD","Advanced Micro Devices Inc."), ("QCOM","Qualcomm Inc."),
    ("PYPL","PayPal Holdings Inc."), ("UBER","Uber Technologies Inc."), ("SHOP","Shopify Inc."),
    ("SQ","Block Inc."), ("SNOW","Snowflake Inc."), ("PLTR","Palantir Technologies Inc."),
    ("COIN","Coinbase Global Inc."), ("ROKU","Roku Inc."), ("ABNB","Airbnb Inc."),
    ("DASH","DoorDash Inc."), ("RBLX","Roblox Corporation"), ("U","Unity Software Inc."),
    ("NET","Cloudflare Inc."), ("DDOG","Datadog Inc."), ("ZS","Zscaler Inc."),
    ("CRWD","CrowdStrike Holdings Inc."), ("OKTA","Okta Inc."), ("TWLO","Twilio Inc."),
    ("ZM","Zoom Video Communications"), ("DOCU","DocuSign Inc."), ("SPOT","Spotify Technology"),
    ("LYFT","Lyft Inc."), ("PINS","Pinterest Inc."), ("SNAP","Snap Inc."),
    ("BABA","Alibaba Group Holding"), ("PDD","PDD Holdings Inc."), ("JD","JD.com Inc."),
    ("NIO","NIO Inc."), ("XPEV","XPeng Inc."), ("LI","Li Auto Inc."),
    ("GS","Goldman Sachs Group Inc."), ("MS","Morgan Stanley"), ("WFC","Wells Fargo & Co."),
    ("C","Citigroup Inc."), ("AXP","American Express Co."), ("BLK","BlackRock Inc."),
    ("SCHW","Charles Schwab Corp."), ("USB","U.S. Bancorp"), ("PNC","PNC Financial Services"),
    ("UNH","UnitedHealth Group Inc."), ("CVS","CVS Health Corp."), ("ABBV","AbbVie Inc."),
    ("LLY","Eli Lilly and Co."), ("PFE","Pfizer Inc."), ("MRK","Merck & Co. Inc."),
    ("BMY","Bristol-Myers Squibb Co."), ("GILD","Gilead Sciences Inc."), ("AMGN","Amgen Inc."),
    ("BIIB","Biogen Inc."), ("MRNA","Moderna Inc."), ("BNTX","BioNTech SE"),
    ("XOM","Exxon Mobil Corp."), ("CVX","Chevron Corp."), ("COP","ConocoPhillips"),
    ("SLB","Schlumberger Ltd."), ("EOG","EOG Resources Inc."), ("MPC","Marathon Petroleum Corp."),
    ("NEE","NextEra Energy Inc."), ("DUK","Duke Energy Corp."), ("SO","Southern Co."),
    ("AEP","American Electric Power"), ("D","Dominion Energy Inc."), ("EXC","Exelon Corp."),
    ("CAT","Caterpillar Inc."), ("DE","Deere & Company"), ("HON","Honeywell International"),
    ("GE","General Electric Co."), ("MMM","3M Company"), ("RTX","RTX Corporation"),
    ("BA","Boeing Co."), ("LMT","Lockheed Martin Corp."), ("NOC","Northrop Grumman Corp."),
    ("F","Ford Motor Co."), ("GM","General Motors Co."), ("RIVN","Rivian Automotive Inc."),
    ("LCID","Lucid Group Inc."), ("STLA","Stellantis N.V."), ("TM","Toyota Motor Corp."),
    ("MCD","McDonald's Corp."), ("SBUX","Starbucks Corp."), ("CMG","Chipotle Mexican Grill"),
    ("YUM","Yum! Brands Inc."), ("DPZ","Domino's Pizza Inc."), ("QSR","Restaurant Brands"),
    ("KO","Coca-Cola Co."), ("PEP","PepsiCo Inc."), ("MDLZ","Mondelez International"),
    ("GIS","General Mills Inc."), ("K","Kellanova"), ("HSY","Hershey Co."),
    ("NKE","Nike Inc."), ("LULU","Lululemon Athletica Inc."), ("UA","Under Armour Inc."),
    ("TGT","Target Corp."), ("COST","Costco Wholesale Corp."), ("AMZN","Amazon.com Inc."),
    ("LOW","Lowe's Companies Inc."), ("TJX","TJX Companies Inc."), ("ROST","Ross Stores Inc."),
    ("T","AT&T Inc."), ("VZ","Verizon Communications"), ("TMUS","T-Mobile US Inc."),
    ("CMCSA","Comcast Corp."), ("CHTR","Charter Communications"), ("NFLX","Netflix Inc."),
    ("ORCL","Oracle Corporation"), ("IBM","IBM Corp."), ("SAP","SAP SE"),
    ("NOW","ServiceNow Inc."), ("WDAY","Workday Inc."), ("INTU","Intuit Inc."),
    ("AMAT","Applied Materials Inc."), ("LRCX","Lam Research Corp."), ("KLAC","KLA Corp."),
    ("ASML","ASML Holding N.V."), ("TSM","Taiwan Semiconductor"), ("MU","Micron Technology"),
    ("WBA","Walgreens Boots Alliance"), ("MCK","McKesson Corp."), ("ABC","AmerisourceBergen"),
    ("SPG","Simon Property Group"), ("PLD","Prologis Inc."), ("AMT","American Tower Corp."),
    ("O","Realty Income Corp."), ("WELL","Welltower Inc."), ("PSA","Public Storage"),
    # Semiconductors & AI
    ("ARM","ARM Holdings plc"), ("SMCI","Super Micro Computer Inc."), ("MSTR","MicroStrategy Inc."),
    ("AVGO","Broadcom Inc."), ("PANW","Palo Alto Networks Inc."), ("FTNT","Fortinet Inc."),
]

# Build the dropdown option strings: "AAPL — Apple Inc."
TICKER_OPTIONS = sorted(
    [f"{ticker} — {name}" for ticker, name in POPULAR_TICKERS],
    key=lambda x: x.split(" — ")[0]
)

def parse_ticker(selection: str) -> str:
    return selection.split(" — ")[0].strip().upper()

# ── Sidebar — Top Growth Stocks Today ────────────────────────────────────────

GROWTH_WATCHLIST = [
    "NVDA","META","AMZN","GOOGL","MSFT","AAPL","TSLA","AMD","CRM","NOW",
    "ADBE","NFLX","SNOW","PLTR","CRWD","NET","DDOG","SHOP","UBER","COIN",
    "MSTR","ARM","SMCI","AVGO","ORCL","PANW","ZS","OKTA","FTNT","INTU",
]

WATCHLIST_NAMES = {
    "NVDA":"NVIDIA — Semiconductors / AI chips",
    "META":"Meta Platforms — Social media / AR",
    "AMZN":"Amazon — E-commerce / Cloud (AWS)",
    "GOOGL":"Alphabet — Search / YouTube / Cloud",
    "MSFT":"Microsoft — Software / Cloud (Azure)",
    "AAPL":"Apple — Consumer electronics / Services",
    "TSLA":"Tesla — Electric vehicles / Energy",
    "AMD":"AMD — CPUs & GPUs / Data center chips",
    "CRM":"Salesforce — CRM / Enterprise SaaS",
    "NOW":"ServiceNow — IT workflow automation",
    "ADBE":"Adobe — Creative & document software",
    "NFLX":"Netflix — Streaming entertainment",
    "SNOW":"Snowflake — Cloud data platform",
    "PLTR":"Palantir — AI / Government analytics",
    "CRWD":"CrowdStrike — Cybersecurity / EDR",
    "NET":"Cloudflare — Network security / CDN",
    "DDOG":"Datadog — Cloud monitoring / observability",
    "SHOP":"Shopify — E-commerce platform",
    "UBER":"Uber — Ride-sharing / Delivery",
    "COIN":"Coinbase — Crypto exchange",
    "MSTR":"MicroStrategy — Bitcoin treasury / BI",
    "ARM":"ARM Holdings — Chip architecture licensing",
    "SMCI":"Super Micro Computer — AI servers",
    "AVGO":"Broadcom — Networking chips / Software",
    "ORCL":"Oracle — Database / Cloud ERP",
    "PANW":"Palo Alto Networks — Cybersecurity platform",
    "ZS":"Zscaler — Zero-trust cloud security",
    "OKTA":"Okta — Identity & access management",
    "FTNT":"Fortinet — Network security appliances",
    "INTU":"Intuit — TurboTax / QuickBooks / Mint",
}

@st.cache_data(ttl=300)   # Refresh every 5 minutes
def get_top_movers(tickers):
    try:
        raw = yf.download(tickers, period="2d", progress=False, auto_adjust=True)
        if raw.empty:
            return pd.DataFrame()

        # Handle MultiIndex columns from multi-ticker download
        if isinstance(raw.columns, pd.MultiIndex):
            closes = raw["Close"]
        else:
            closes = raw[["Close"]]
            closes.columns = tickers[:1]

        pct = closes.pct_change().iloc[-1].dropna()
        prices = closes.iloc[-1].dropna()

        df = pd.DataFrame({"Change (%)": pct * 100, "Price ($)": prices})
        return df.sort_values("Change (%)", ascending=False).round(2)
    except Exception:
        return pd.DataFrame()

# ── CSS: sticky input row + watchlist tooltips ────────────────────────────────

st.markdown("""
<style>
/* Sticky input row */
div[data-testid="stMain"] > div > div.block-container > div[data-testid="stVerticalBlock"]
  > div[data-testid="stVerticalBlock"]:nth-child(3) {
    position: sticky;
    top: 0;
    z-index: 100;
    background-color: #0e1117;
    padding-bottom: 8px;
}
/* CSS tooltip for watchlist rows */
.wl-row { position: relative; display: flex; justify-content: space-between;
           padding: 6px 4px; border-bottom: 1px solid #333; cursor: default; }
.wl-tt  { display: none; position: absolute; left: 0; top: 110%; min-width: 200px;
           background: #1e2130; color: #e0e0e0; font-size: 0.78rem; padding: 5px 8px;
           border-radius: 5px; border: 1px solid #444; z-index: 9999;
           white-space: normal; line-height: 1.4; pointer-events: none; }
.wl-row:hover .wl-tt { display: block; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    # ── Top Movers ────────────────────────────────────────────────────────────
    st.markdown("## 🚀 Top Movers Today")
    st.caption("Growth watchlist · Hover a ticker for details · Refreshed every 5 min")

    movers = get_top_movers(GROWTH_WATCHLIST)

    if not movers.empty:
        for ticker, row in movers.head(10).iterrows():
            chg = row["Change (%)"]
            price = row["Price ($)"]
            arrow = "▲" if chg >= 0 else "▼"
            color = "#27ae60" if chg >= 0 else "#e74c3c"
            desc = WATCHLIST_NAMES.get(ticker, ticker)
            st.markdown(
                f"<div class='wl-row'>"
                f"<span style='font-weight:600'>{ticker}</span>"
                f"<span style='color:{color};font-weight:600'>{arrow} {chg:+.2f}%</span>"
                f"<span style='color:#aaa;font-size:0.85rem'>${price:.2f}</span>"
                f"<div class='wl-tt'>{desc}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown("")
        st.caption("Source: Yahoo Finance")
    else:
        st.info("Market data unavailable right now.")

    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.caption(
        "Compares US-listed public company stocks using SEC EDGAR (10-K filings) "
        "and Yahoo Finance. ETFs and mutual funds are not supported."
    )

# ── Header ────────────────────────────────────────────────────────────────────

st.title("📊 Stock Comparison Model")
st.markdown(
    "Compare two US-listed public companies across 10 years of fundamental data. "
    "Fundamentals from **SEC EDGAR** (official 10-K filings). "
    "Prices from **Yahoo Finance**."
)
st.markdown("---")

# ── Ticker Input ──────────────────────────────────────────────────────────────

col_a, col_b, col_btn = st.columns([3, 3, 1])

with col_a:
    ticker_a = st.text_input(
        "🔵 Company A — enter ticker",
        value="AAPL",
        placeholder="e.g. AAPL, ARM, NVDA",
        help="Type any US-listed stock ticker symbol",
    ).upper().strip()

with col_b:
    ticker_b = st.text_input(
        "🟠 Company B — enter ticker",
        value="MSFT",
        placeholder="e.g. MSFT, TSLA, META",
        help="Type any US-listed stock ticker symbol",
    ).upper().strip()

with col_btn:
    st.write("")
    st.write("")
    compare_clicked = st.button("Compare ▶", type="primary", use_container_width=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt(value, format_str):
    try:
        if value is None or pd.isna(value):
            return "—"
        return format_str.format(value)
    except Exception:
        return "—"

YEARS     = list(range(2015, 2025))
YEARS_STR = [str(y) for y in YEARS]
COLOR_A   = "#1a56db"
COLOR_B   = "#e07b00"

MONTH_NAMES = {
    1:"January", 2:"February", 3:"March", 4:"April", 5:"May", 6:"June",
    7:"July", 8:"August", 9:"September", 10:"October", 11:"November", 12:"December"
}

def chart_layout(fig, title, y_title):
    fig.update_layout(
        title_text=title,
        title_font_size=17,
        height=400,
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin_t=65,
        margin_b=60,
        margin_l=75,
        margin_r=30,
        legend_orientation="h",
        legend_yanchor="bottom",
        legend_y=1.02,
        legend_xanchor="right",
        legend_x=1,
    )
    fig.update_xaxes(
        title_text="Fiscal Year",
        dtick=1,
        tickangle=-30,
        gridcolor="rgba(255,255,255,0.12)",
        linecolor="rgba(255,255,255,0.2)",
    )
    fig.update_yaxes(
        title_text=y_title,
        zeroline=True,
        zerolinecolor="rgba(255,255,255,0.25)",
        gridcolor="rgba(255,255,255,0.12)",
    )
    return fig

def get_vals(series, years, scale=1):
    return [
        round(series.get(y) / scale, 3)
        if (series.get(y) is not None and pd.notna(series.get(y)))
        else None
        for y in years
    ]

# ── Main Logic ────────────────────────────────────────────────────────────────

if compare_clicked:

    if ticker_a == ticker_b:
        st.warning("Please select two different companies.")
        st.stop()

    with st.spinner(f"Fetching live data from SEC EDGAR for {ticker_a} and {ticker_b}..."):
        try:
            data_a    = build_dataset(ticker_a)
            metrics_a = calculate_metrics(data_a)
        except ValueError as e:
            st.error(f"**{ticker_a}**: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Unexpected error fetching {ticker_a}: {e}")
            st.stop()

        try:
            data_b    = build_dataset(ticker_b)
            metrics_b = calculate_metrics(data_b)
        except ValueError as e:
            st.error(f"**{ticker_b}**: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Unexpected error fetching {ticker_b}: {e}")
            st.stop()

    # ── Company Headers ───────────────────────────────────────────────────────

    st.markdown("---")
    h_col_a, h_col_b = st.columns(2)

    with h_col_a:
        st.markdown(
            f"<div style='background:#e8f0fe;padding:14px;border-radius:8px;'>"
            f"<h3 style='margin:0;color:#1a56db'>🔵 {data_a['name']}</h3>"
            f"<p style='margin:4px 0 0;color:#555'>Ticker: <b>{ticker_a}</b> &nbsp;|&nbsp; "
            f"Fiscal Year ends: <b>{MONTH_NAMES.get(data_a['fy_end_month'], '?')}</b></p></div>",
            unsafe_allow_html=True
        )
    with h_col_b:
        st.markdown(
            f"<div style='background:#fff3e0;padding:14px;border-radius:8px;'>"
            f"<h3 style='margin:0;color:#c45000'>🟠 {data_b['name']}</h3>"
            f"<p style='margin:4px 0 0;color:#555'>Ticker: <b>{ticker_b}</b> &nbsp;|&nbsp; "
            f"Fiscal Year ends: <b>{MONTH_NAMES.get(data_b['fy_end_month'], '?')}</b></p></div>",
            unsafe_allow_html=True
        )

    st.write("")

    # ── Summary Table ─────────────────────────────────────────────────────────

    years_with_pe = set(metrics_a["pe"].dropna().index) & set(metrics_b["pe"].dropna().index)
    last_year = max(years_with_pe) if years_with_pe else 2024

    st.markdown(f"### Most Recent Year ({last_year}) — Side by Side")

    summary_rows = [
        ("Stock Price",               data_a["price"].get(last_year),          data_b["price"].get(last_year),          "${:.2f}"),
        ("EPS  =  Net Income ÷ Shares",       metrics_a["eps"].get(last_year),         metrics_b["eps"].get(last_year),         "${:.2f}"),
        ("P/E  =  Price ÷ EPS",               metrics_a["pe"].get(last_year),          metrics_b["pe"].get(last_year),          "{:.1f}×"),
        ("P/B  =  Price ÷ Book Value/Share",  metrics_a["pb"].get(last_year),          metrics_b["pb"].get(last_year),          "{:.1f}×"),
        ("P/CF =  Price ÷ Cash Flow/Share",   metrics_a["pcf"].get(last_year),         metrics_b["pcf"].get(last_year),         "{:.1f}×"),
        ("Revenue Growth (YoY %)",            metrics_a["rev_growth"].get(last_year),  metrics_b["rev_growth"].get(last_year),  "{:.1%}"),
        ("Net Income Growth (YoY %)",         metrics_a["ni_growth"].get(last_year),   metrics_b["ni_growth"].get(last_year),   "{:.1%}"),
    ]

    summary_df = pd.DataFrame({
        "Metric":  [r[0] for r in summary_rows],
        ticker_a:  [fmt(r[1], r[3]) for r in summary_rows],
        ticker_b:  [fmt(r[2], r[3]) for r in summary_rows],
    }).set_index("Metric")

    st.dataframe(summary_df, use_container_width=True)
    st.caption(
        "**Reading the ratios:** Lower P/E, P/B, P/CF = cheaper relative to earnings/assets/cash. "
        "Higher = market expects more growth, or stock may be pricey. "
        "Stock Price shown at each company's fiscal year-end date."
    )

    # ── Charts ────────────────────────────────────────────────────────────────

    st.markdown("---")
    st.markdown("### 10-Year Historical Charts")
    st.caption("💡 Hover over any point or bar to see exact values for both companies. Use the toolbar (top-right) to zoom, pan, or save.")

    # ── Chart 1: Annual Revenue ───────────────────────────────────────────────

    rev_a = get_vals(data_a["revenue"], YEARS, scale=1e9)
    rev_b = get_vals(data_b["revenue"], YEARS, scale=1e9)

    fig_rev = go.Figure()
    fig_rev.add_trace(go.Bar(
        name=ticker_a, x=YEARS, y=rev_a, marker_color=COLOR_A, opacity=0.88,
        hovertemplate=f"<b>{ticker_a}</b><br>Revenue: $%{{y:.2f}}B<extra></extra>",
    ))
    fig_rev.add_trace(go.Bar(
        name=ticker_b, x=YEARS, y=rev_b, marker_color=COLOR_B, opacity=0.88,
        hovertemplate=f"<b>{ticker_b}</b><br>Revenue: $%{{y:.2f}}B<extra></extra>",
    ))
    fig_rev.update_layout(barmode="group")
    chart_layout(fig_rev, "📊 Annual Revenue", "Revenue ($B)")
    st.plotly_chart(fig_rev, use_container_width=True)

    # ── Chart 2: Net Income ───────────────────────────────────────────────────

    ni_a = get_vals(data_a["net_income"], YEARS, scale=1e9)
    ni_b = get_vals(data_b["net_income"], YEARS, scale=1e9)

    fig_ni = go.Figure()
    fig_ni.add_trace(go.Bar(
        name=ticker_a, x=YEARS, y=ni_a, marker_color=COLOR_A, opacity=0.88,
        hovertemplate=f"<b>{ticker_a}</b><br>Net Income: $%{{y:.2f}}B<extra></extra>",
    ))
    fig_ni.add_trace(go.Bar(
        name=ticker_b, x=YEARS, y=ni_b, marker_color=COLOR_B, opacity=0.88,
        hovertemplate=f"<b>{ticker_b}</b><br>Net Income: $%{{y:.2f}}B<extra></extra>",
    ))
    fig_ni.update_layout(barmode="group")
    chart_layout(fig_ni, "💰 Net Income", "Net Income ($B)")
    st.plotly_chart(fig_ni, use_container_width=True)

    # ── Chart 3: P/E Ratio ────────────────────────────────────────────────────

    pe_a = get_vals(metrics_a["pe"], YEARS)
    pe_b = get_vals(metrics_b["pe"], YEARS)

    fig_pe = go.Figure()
    for ticker, vals, color in [(ticker_a, pe_a, COLOR_A), (ticker_b, pe_b, COLOR_B)]:
        fig_pe.add_trace(go.Scatter(
            name=ticker, x=YEARS, y=vals,
            mode="lines+markers",
            line=dict(color=color, width=2.5),
            marker=dict(size=9, color=color, line=dict(width=2, color="white")),
            hovertemplate=f"<b>{ticker}</b><br>P/E Ratio: %{{y:.1f}}×<extra></extra>",
        ))
    chart_layout(fig_pe, "📈 P/E Ratio — Price-to-Earnings", "P/E (×)")
    st.plotly_chart(fig_pe, use_container_width=True)

    # ── Chart 4: Earnings Per Share ───────────────────────────────────────────

    eps_a = get_vals(metrics_a["eps"], YEARS)
    eps_b = get_vals(metrics_b["eps"], YEARS)

    fig_eps = go.Figure()
    for ticker, vals, color in [(ticker_a, eps_a, COLOR_A), (ticker_b, eps_b, COLOR_B)]:
        fig_eps.add_trace(go.Scatter(
            name=ticker, x=YEARS, y=vals,
            mode="lines+markers",
            line=dict(color=color, width=2.5),
            marker=dict(size=9, color=color, line=dict(width=2, color="white")),
            hovertemplate=f"<b>{ticker}</b><br>EPS: $%{{y:.2f}}<extra></extra>",
        ))
    chart_layout(fig_eps, "💵 Earnings Per Share (EPS)", "EPS ($)")
    st.plotly_chart(fig_eps, use_container_width=True)

    # ── Data Tables ───────────────────────────────────────────────────────────

    st.markdown("---")
    st.markdown("### 📋 Data Tables")
    st.caption("🟢 Green = positive growth &nbsp;&nbsp; 🔴 Red = negative growth")

    def to_m(s): return s.apply(lambda x: round(x/1e6,1) if pd.notna(x) else None)
    def reindex_str(s):
        r = s.reindex(YEARS); r.index = YEARS_STR; return r

    GROWTH_ROWS = ["Revenue Growth", "Net Income Growth", "EPS Growth"]

    # Raw Data
    with st.expander("📥  Raw Data — from SEC EDGAR 10-K filings", expanded=True):
        rt_a, rt_b = st.tabs([f"🔵 {ticker_a}", f"🟠 {ticker_b}"])
        for tab, ds in [(rt_a, data_a), (rt_b, data_b)]:
            with tab:
                raw_df = pd.DataFrame({
                    "Revenue ($M)":        reindex_str(to_m(ds["revenue"])),
                    "Net Income ($M)":     reindex_str(to_m(ds["net_income"])),
                    "Equity ($M)":         reindex_str(to_m(ds["equity"])),
                    "Shares (M)":          reindex_str(to_m(ds["shares"])),
                    "Op. Cash Flow ($M)":  reindex_str(to_m(ds["ocf"])),
                    "Stock Price ($)":     reindex_str(ds["price"]),
                }).T
                st.dataframe(raw_df.style.format("{:,.1f}", na_rep="—"), use_container_width=True)

    # Calculations
    with st.expander("🧮  Calculations — derived ratios & growth rates", expanded=True):
        ct_a, ct_b = st.tabs([f"🔵 {ticker_a}", f"🟠 {ticker_b}"])

        def color_growth(val):
            if val is None or pd.isna(val): return "color:#aaa"
            if val > 0: return "background-color:#d4edda;color:#155724;font-weight:600"
            if val < 0: return "background-color:#f8d7da;color:#721c24;font-weight:600"
            return ""

        def fmt_calc(val, row):
            if val is None or (isinstance(val, float) and pd.isna(val)): return "—"
            if row in GROWTH_ROWS: return f"{val:.1%}"
            if "Ratio" in row: return f"{val:.1f}×"
            return f"{val:.2f}"

        for tab, metrics in [(ct_a, metrics_a), (ct_b, metrics_b)]:
            with tab:
                raw_calc = pd.DataFrame({
                    "EPS ($)":              reindex_str(metrics["eps"]),
                    "Book Value/Share ($)": reindex_str(metrics["bvps"]),
                    "CF/Share ($)":         reindex_str(metrics["cfps"]),
                    "P/E Ratio (×)":        reindex_str(metrics["pe"]),
                    "P/B Ratio (×)":        reindex_str(metrics["pb"]),
                    "P/CF Ratio (×)":       reindex_str(metrics["pcf"]),
                    "Revenue Growth":       reindex_str(metrics["rev_growth"]),
                    "Net Income Growth":    reindex_str(metrics["ni_growth"]),
                    "EPS Growth":           reindex_str(metrics["eps_growth"]),
                }).T

                display = raw_calc.copy().astype(object)
                for row in raw_calc.index:
                    for col in raw_calc.columns:
                        display.loc[row, col] = fmt_calc(raw_calc.loc[row, col], row)

                def apply_styles(df):
                    styles = pd.DataFrame("", index=df.index, columns=df.columns)
                    for row in GROWTH_ROWS:
                        if row in df.index:
                            for col in df.columns:
                                styles.loc[row, col] = color_growth(raw_calc.loc[row, col])
                    return styles

                st.dataframe(display.style.apply(apply_styles, axis=None), use_container_width=True)

    # ── Footer ────────────────────────────────────────────────────────────────

    st.markdown("---")
    st.info(
        "🔄 Data is fetched live from SEC EDGAR every time you click Compare — "
        "always reflects the most recent 10-K filing. "
        "Only US-listed public company stocks are supported. "
        "ETFs (e.g. VOO, SPY) and mutual funds are not available."
    )
    st.caption(
        "📁 Fundamentals: SEC EDGAR XBRL API (10-K filings) &nbsp;|&nbsp; "
        "📈 Prices & movers: Yahoo Finance"
    )
