"""
app.py — Streamlit web interface
=================================
Structure:
  1. Page config & header
  2. Searchable ticker dropdowns (autocomplete from SEC EDGAR list)
  3. Data fetch (calls data.py)
  4. Summary metrics table
  5. Interactive Plotly charts (hover tooltips, no cramped labels)
  6. Raw Data + Calculations tables with color coding
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from data import build_dataset, calculate_metrics, get_ticker_options

# ── Page Setup ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Stock Comparison Model",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
    <style>
    thead tr th { font-size: 0.9rem !important; font-weight: 600 !important; }
    div[data-testid="stSelectbox"] label { font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────

st.title("📊 Stock Comparison Model")
st.markdown(
    "Compare two US-listed public companies across 10 years of fundamental data. "
    "Fundamentals from **SEC EDGAR** (official 10-K annual filings). "
    "Stock prices from **Yahoo Finance**. &nbsp;⚠️ ETFs and mutual funds are not supported."
)
st.markdown("---")

# ── Ticker Autocomplete ───────────────────────────────────────────────────────

# Load the full EDGAR ticker list once (cached 24h)
with st.spinner("Loading ticker list from SEC EDGAR..."):
    try:
        ticker_options = get_ticker_options()
    except Exception:
        ticker_options = []
        st.warning("Could not load ticker list. You can still type a ticker manually.")

def parse_ticker(selection: str) -> str:
    """Extract the ticker symbol from a 'TICKER — Company Name' string."""
    return selection.split(" — ")[0].strip().upper()

# Default selections
default_a = next((o for o in ticker_options if o.startswith("AAPL —")), ticker_options[0] if ticker_options else "")
default_b = next((o for o in ticker_options if o.startswith("MSFT —")), ticker_options[1] if ticker_options else "")

col_a, col_b, col_btn = st.columns([3, 3, 1])

with col_a:
    if ticker_options:
        sel_a = st.selectbox(
            "🔵 Company A — type to search",
            options=ticker_options,
            index=ticker_options.index(default_a) if default_a in ticker_options else 0,
            help="Search by ticker symbol or company name",
        )
        ticker_a = parse_ticker(sel_a)
    else:
        ticker_a = st.text_input("Company A Ticker", value="AAPL").upper().strip()

with col_b:
    if ticker_options:
        sel_b = st.selectbox(
            "🟠 Company B — type to search",
            options=ticker_options,
            index=ticker_options.index(default_b) if default_b in ticker_options else 0,
            help="Search by ticker symbol or company name",
        )
        ticker_b = parse_ticker(sel_b)
    else:
        ticker_b = st.text_input("Company B Ticker", value="MSFT").upper().strip()

with col_btn:
    st.write("")
    st.write("")
    compare_clicked = st.button("Compare ▶", type="primary", use_container_width=True)

# ── Helper ────────────────────────────────────────────────────────────────────

def fmt(value, format_str):
    """Safely format a number, returning '—' for None/NaN."""
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
    1:"January", 2:"February", 3:"March", 4:"April",
    5:"May", 6:"June", 7:"July", 8:"August",
    9:"September", 10:"October", 11:"November", 12:"December"
}

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

    # ── Most Recent Year Summary ──────────────────────────────────────────────

    years_with_pe = (
        set(metrics_a["pe"].dropna().index) &
        set(metrics_b["pe"].dropna().index)
    )
    last_year = max(years_with_pe) if years_with_pe else 2024

    st.markdown(f"### Most Recent Year ({last_year}) — Side by Side")

    summary_rows = [
        ("Stock Price",          data_a["price"].get(last_year),          data_b["price"].get(last_year),          "${:.2f}"),
        ("Earnings Per Share",   metrics_a["eps"].get(last_year),         metrics_b["eps"].get(last_year),         "${:.2f}"),
        ("P/E Ratio",            metrics_a["pe"].get(last_year),          metrics_b["pe"].get(last_year),          "{:.1f}×"),
        ("P/B Ratio",            metrics_a["pb"].get(last_year),          metrics_b["pb"].get(last_year),          "{:.1f}×"),
        ("P/CF Ratio",           metrics_a["pcf"].get(last_year),         metrics_b["pcf"].get(last_year),         "{:.1f}×"),
        ("Revenue Growth (YoY)", metrics_a["rev_growth"].get(last_year),  metrics_b["rev_growth"].get(last_year),  "{:.1%}"),
        ("Net Income Growth",    metrics_a["ni_growth"].get(last_year),   metrics_b["ni_growth"].get(last_year),   "{:.1%}"),
    ]

    summary_df = pd.DataFrame({
        "Metric":  [r[0] for r in summary_rows],
        ticker_a:  [fmt(r[1], r[3]) for r in summary_rows],
        ticker_b:  [fmt(r[2], r[3]) for r in summary_rows],
    }).set_index("Metric")

    st.dataframe(summary_df, use_container_width=True)

    # ── Charts ────────────────────────────────────────────────────────────────

    st.markdown("---")
    st.markdown("### 10-Year Historical Charts")
    st.caption("💡 Hover over any point or bar to see exact values. Use the toolbar (top-right of each chart) to zoom, pan, or download.")

    def get_vals(series, years, scale=1):
        return [
            round(series.get(y) / scale, 2)
            if (series.get(y) is not None and pd.notna(series.get(y)))
            else None
            for y in years
        ]

    def apply_chart_style(fig):
        """Apply consistent, readable styling to any Plotly figure."""
        fig.update_layout(
            font=dict(family="Arial", size=13, color="#222"),
            plot_bgcolor="white",
            paper_bgcolor="white",
            legend=dict(
                orientation="h",
                yanchor="bottom", y=1.04,
                xanchor="right", x=1,
                font=dict(size=13, color="#222"),
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="#ddd",
                borderwidth=1,
            ),
            margin=dict(t=70, b=55, l=70, r=30),
            hovermode="x unified",   # Shows all series in one tooltip on hover
            hoverlabel=dict(
                bgcolor="white",
                font_size=13,
                font_family="Arial",
                bordercolor="#ddd",
            ),
        )
        fig.update_xaxes(
            tickformat="d",
            dtick=1,
            tickfont=dict(size=12, color="#333"),
            title_font=dict(size=13),
            showgrid=True, gridcolor="#ececec", gridwidth=1,
            linecolor="#ccc", linewidth=1,
            tickangle=-30,
        )
        fig.update_yaxes(
            tickfont=dict(size=12, color="#333"),
            title_font=dict(size=13),
            showgrid=True, gridcolor="#ececec", gridwidth=1,
            linecolor="#ccc", linewidth=1,
            zeroline=True, zerolinecolor="#bbb", zerolinewidth=1,
        )
        for ann in fig.layout.annotations:
            ann.font = dict(size=14, color="#111", family="Arial")
        return fig

    # ── Chart 1: Revenue & Net Income ────────────────────────────────────────

    fig1 = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Annual Revenue ($B)", "Net Income ($B)"),
        horizontal_spacing=0.13,
    )

    for col_idx, (key, ylabel) in enumerate([("revenue", "$B"), ("net_income", "$B")], 1):
        vals_a = get_vals(data_a[key], YEARS, scale=1e9)
        vals_b = get_vals(data_b[key], YEARS, scale=1e9)

        fig1.add_trace(go.Bar(
            name=ticker_a, x=YEARS, y=vals_a,
            marker_color=COLOR_A, opacity=0.85,
            legendgroup="g1a", showlegend=(col_idx == 1),
            hovertemplate=f"<b>{ticker_a}</b><br>%{{x}}: $%{{y:.2f}}B<extra></extra>",
        ), row=1, col=col_idx)

        fig1.add_trace(go.Bar(
            name=ticker_b, x=YEARS, y=vals_b,
            marker_color=COLOR_B, opacity=0.85,
            legendgroup="g1b", showlegend=(col_idx == 1),
            hovertemplate=f"<b>{ticker_b}</b><br>%{{x}}: $%{{y:.2f}}B<extra></extra>",
        ), row=1, col=col_idx)

    fig1.update_layout(barmode="group", height=450)
    apply_chart_style(fig1)
    st.plotly_chart(fig1, use_container_width=True)

    # ── Chart 2: P/E Ratio & EPS ──────────────────────────────────────────────

    fig2 = make_subplots(
        rows=1, cols=2,
        subplot_titles=("P/E Ratio (×)", "Earnings Per Share ($)"),
        horizontal_spacing=0.13,
    )

    chart2_data = [
        (get_vals(metrics_a["pe"], YEARS),  get_vals(metrics_b["pe"], YEARS),  "P/E",  "{:.1f}×", "$"),
        (get_vals(metrics_a["eps"], YEARS), get_vals(metrics_b["eps"], YEARS), "EPS",  "${:.2f}",  ""),
    ]

    for col_idx, (vals_a, vals_b, label, hover_fmt, prefix) in enumerate(chart2_data, 1):
        for ticker, vals, color, grp in [
            (ticker_a, vals_a, COLOR_A, "g2a"),
            (ticker_b, vals_b, COLOR_B, "g2b"),
        ]:
            fig2.add_trace(go.Scatter(
                name=ticker, x=YEARS, y=vals,
                mode="lines+markers",
                line=dict(color=color, width=2.5),
                marker=dict(size=8, color=color,
                            line=dict(width=1.5, color="white")),
                legendgroup=grp, showlegend=(col_idx == 1),
                hovertemplate=(
                    f"<b>{ticker}</b><br>%{{x}}: {prefix}%{{y:.2f}}"
                    + ("×" if "P/E" in label else "")
                    + "<extra></extra>"
                ),
            ), row=1, col=col_idx)

    fig2.update_layout(height=450)
    apply_chart_style(fig2)
    st.plotly_chart(fig2, use_container_width=True)

    # ── Data Tables ───────────────────────────────────────────────────────────

    st.markdown("---")
    st.markdown("### 📋 Data Tables")
    st.caption(
        "Mirrors the Excel model structure — Raw Data (from SEC filings) and "
        "Calculations (derived metrics). 🟢 Green = positive change &nbsp; 🔴 Red = negative change."
    )

    def to_m(series):
        return series.apply(lambda x: round(x / 1e6, 1) if pd.notna(x) else None)

    def reindex_str(series):
        s = series.reindex(YEARS)
        s.index = YEARS_STR
        return s

    # ── Raw Data Section ──────────────────────────────────────────────────────

    with st.expander("📥  Raw Data — sourced directly from SEC EDGAR 10-K filings", expanded=True):
        raw_tab_a, raw_tab_b = st.tabs([f"🔵 {ticker_a}", f"🟠 {ticker_b}"])

        for tab, ds in [(raw_tab_a, data_a), (raw_tab_b, data_b)]:
            with tab:
                raw_df = pd.DataFrame({
                    "Revenue ($M)":        reindex_str(to_m(ds["revenue"])),
                    "Net Income ($M)":     reindex_str(to_m(ds["net_income"])),
                    "Equity ($M)":         reindex_str(to_m(ds["equity"])),
                    "Shares (M)":          reindex_str(to_m(ds["shares"])),
                    "Op. Cash Flow ($M)":  reindex_str(to_m(ds["ocf"])),
                    "Stock Price ($)":     reindex_str(ds["price"]),
                }).T

                st.dataframe(
                    raw_df.style.format("{:,.1f}", na_rep="—"),
                    use_container_width=True,
                )

    # ── Calculations Section ──────────────────────────────────────────────────

    with st.expander("🧮  Calculations — derived ratios & growth rates", expanded=True):
        calc_tab_a, calc_tab_b = st.tabs([f"🔵 {ticker_a}", f"🟠 {ticker_b}"])

        GROWTH_ROWS = ["Revenue Growth", "Net Income Growth", "EPS Growth"]

        def build_calc_df(metrics):
            return pd.DataFrame({
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

        def fmt_calc_cell(val, row_label):
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return "—"
            if row_label in GROWTH_ROWS:
                return f"{val:.1%}"
            if "Ratio" in row_label:
                return f"{val:.1f}×"
            return f"{val:.2f}"

        def color_growth(val):
            if val is None or pd.isna(val):
                return "color: #aaa"
            if val > 0:
                return "background-color: #d4edda; color: #155724; font-weight: 600"
            if val < 0:
                return "background-color: #f8d7da; color: #721c24; font-weight: 600"
            return ""

        for tab, metrics in [(calc_tab_a, metrics_a), (calc_tab_b, metrics_b)]:
            with tab:
                raw_calc = build_calc_df(metrics)

                # Build display version with formatted strings
                display = raw_calc.copy().astype(object)
                for row in raw_calc.index:
                    for col in raw_calc.columns:
                        display.loc[row, col] = fmt_calc_cell(raw_calc.loc[row, col], row)

                # Apply background color using raw float values
                def apply_styles(df):
                    styles = pd.DataFrame("", index=df.index, columns=df.columns)
                    for row in GROWTH_ROWS:
                        if row in df.index:
                            for col in df.columns:
                                styles.loc[row, col] = color_growth(raw_calc.loc[row, col])
                    return styles

                styled = display.style.apply(apply_styles, axis=None)
                st.dataframe(styled, use_container_width=True)

    # ── Footer ────────────────────────────────────────────────────────────────

    st.markdown("---")
    st.info(
        "🔄 **Data is fetched live from SEC EDGAR every time you click Compare** — "
        "always reflects the most recent 10-K filing on record. "
        "Only US-listed public company stocks are supported. "
        "ETFs (e.g. VOO, SPY), mutual funds, and indices are not available."
    )
    st.caption(
        "📁 Fundamentals: [SEC EDGAR XBRL API](https://www.sec.gov/dera/data/financial-statements) "
        "— 10-K annual filings &nbsp;|&nbsp; "
        "📈 Prices: Yahoo Finance (fiscal year-end closing price)"
    )
