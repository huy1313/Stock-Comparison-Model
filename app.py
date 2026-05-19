"""
app.py — Streamlit web interface
=================================
This is the file Streamlit runs. It controls everything the user sees.
Structure:
  1. Page config & header
  2. Ticker input + Compare button
  3. Data fetch (calls data.py)
  4. Summary metrics table
  5. Four interactive charts (Plotly)
  6. Data tables: Raw Data section + Calculations section (with color coding)
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from data import build_dataset, calculate_metrics

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
    </style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────

st.title("📊 Stock Comparison Model")
st.markdown(
    "Compare two public companies across 10 years of fundamental data. "
    "Fundamentals sourced from **SEC EDGAR** (official 10-K annual filings — always current). "
    "Stock prices from **Yahoo Finance**."
)
st.markdown("---")

# ── Ticker Input ──────────────────────────────────────────────────────────────

col_a, col_b, col_btn = st.columns([2, 2, 1])

with col_a:
    ticker_a = st.text_input(
        "Company A Ticker",
        value="AAPL",
        placeholder="e.g. AAPL",
        help="Enter a US-listed stock ticker symbol"
    ).upper().strip()

with col_b:
    ticker_b = st.text_input(
        "Company B Ticker",
        value="MSFT",
        placeholder="e.g. MSFT",
        help="Enter a US-listed stock ticker symbol"
    ).upper().strip()

with col_btn:
    st.write("")
    st.write("")
    compare_clicked = st.button("Compare ▶", type="primary", use_container_width=True)

# ── Helper: safe number formatter ────────────────────────────────────────────

def fmt(value, format_str):
    """Format a number safely — returns '—' for None or NaN."""
    try:
        if value is None or pd.isna(value):
            return "—"
        return format_str.format(value)
    except Exception:
        return "—"

# ── Main Logic ────────────────────────────────────────────────────────────────

if compare_clicked and ticker_a and ticker_b:

    if ticker_a == ticker_b:
        st.warning("Please enter two different ticker symbols.")
        st.stop()

    with st.spinner(f"Fetching live data from SEC EDGAR for {ticker_a} and {ticker_b}..."):
        try:
            data_a    = build_dataset(ticker_a)
            metrics_a = calculate_metrics(data_a)
        except ValueError as e:
            st.error(f"**{ticker_a}**: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Error fetching {ticker_a}: {e}")
            st.stop()

        try:
            data_b    = build_dataset(ticker_b)
            metrics_b = calculate_metrics(data_b)
        except ValueError as e:
            st.error(f"**{ticker_b}**: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Error fetching {ticker_b}: {e}")
            st.stop()

    # ── Company Headers ───────────────────────────────────────────────────────

    st.markdown("---")
    MONTH_NAMES = {
        1:"January", 2:"February", 3:"March", 4:"April",
        5:"May", 6:"June", 7:"July", 8:"August",
        9:"September", 10:"October", 11:"November", 12:"December"
    }

    h_col_a, h_col_b = st.columns(2)
    with h_col_a:
        st.markdown(
            f"<div style='background:#e8f0fe;padding:14px;border-radius:8px;'>"
            f"<h3 style='margin:0;color:#1a56db'>🔵 {data_a['name']}</h3>"
            f"<p style='margin:4px 0 0;color:#555'>Ticker: <b>{ticker_a}</b> &nbsp;|&nbsp; "
            f"Fiscal Year ends: <b>{MONTH_NAMES[data_a['fy_end_month']]}</b></p></div>",
            unsafe_allow_html=True
        )
    with h_col_b:
        st.markdown(
            f"<div style='background:#fff3e0;padding:14px;border-radius:8px;'>"
            f"<h3 style='margin:0;color:#c45000'>🟠 {data_b['name']}</h3>"
            f"<p style='margin:4px 0 0;color:#555'>Ticker: <b>{ticker_b}</b> &nbsp;|&nbsp; "
            f"Fiscal Year ends: <b>{MONTH_NAMES[data_b['fy_end_month']]}</b></p></div>",
            unsafe_allow_html=True
        )

    st.write("")

    # ── Most Recent Year Summary — using native Streamlit (fixes HTML wall of text) ──

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

    # Build as a clean DataFrame — no raw HTML, no rendering issues
    summary_df = pd.DataFrame({
        "Metric": [r[0] for r in summary_rows],
        ticker_a: [fmt(r[1], r[3]) for r in summary_rows],
        ticker_b: [fmt(r[2], r[3]) for r in summary_rows],
    }).set_index("Metric")

    st.dataframe(summary_df, use_container_width=True)

    # ── Charts ────────────────────────────────────────────────────────────────

    st.markdown("---")
    st.markdown("### 10-Year Historical Charts")

    YEARS     = list(range(2015, 2025))
    COLOR_A   = "#1a56db"
    COLOR_B   = "#e07b00"

    # Shared layout settings for readable chart text
    CHART_FONT   = dict(family="Arial", size=13, color="#222")
    AXIS_FONT    = dict(size=12, color="#333")
    TITLE_FONT   = dict(size=14, color="#111", family="Arial")

    def get_vals(series, years, scale=1):
        return [
            round(series.get(y) / scale, 2)
            if (series.get(y) is not None and pd.notna(series.get(y)))
            else None
            for y in years
        ]

    def apply_shared_layout(fig, rows=1):
        fig.update_layout(
            font=CHART_FONT,
            plot_bgcolor="white",
            paper_bgcolor="white",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.05,
                xanchor="right", x=1,
                font=dict(size=13),
            ),
            margin=dict(t=60, b=50, l=60, r=20),
        )
        # Apply axis styling to all subplots
        fig.update_xaxes(
            tickformat="d", dtick=1,
            tickfont=AXIS_FONT,
            title_font=AXIS_FONT,
            showgrid=True, gridcolor="#e8e8e8",
            linecolor="#ccc", linewidth=1,
        )
        fig.update_yaxes(
            tickfont=AXIS_FONT,
            title_font=AXIS_FONT,
            showgrid=True, gridcolor="#e8e8e8",
            linecolor="#ccc", linewidth=1,
            zeroline=True, zerolinecolor="#bbb",
        )
        # Style subplot titles
        for annotation in fig.layout.annotations:
            annotation.font = TITLE_FONT

    # ── Chart 1: Revenue & Net Income (Bar) ──────────────────────────────────

    fig1 = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Annual Revenue ($B)", "Net Income ($B)"),
        horizontal_spacing=0.12,
    )

    for col_idx, key in enumerate(["revenue", "net_income"], 1):
        vals_a = get_vals(data_a[key], YEARS, scale=1e9)
        vals_b = get_vals(data_b[key], YEARS, scale=1e9)
        fig1.add_trace(
            go.Bar(name=ticker_a, x=YEARS, y=vals_a, marker_color=COLOR_A,
                   legendgroup="a", showlegend=(col_idx == 1),
                   text=[f"${v:.0f}B" if v else "" for v in vals_a],
                   textposition="outside", textfont=dict(size=9)),
            row=1, col=col_idx
        )
        fig1.add_trace(
            go.Bar(name=ticker_b, x=YEARS, y=vals_b, marker_color=COLOR_B,
                   legendgroup="b", showlegend=(col_idx == 1),
                   text=[f"${v:.0f}B" if v else "" for v in vals_b],
                   textposition="outside", textfont=dict(size=9)),
            row=1, col=col_idx
        )

    fig1.update_layout(barmode="group", height=440)
    apply_shared_layout(fig1)
    fig1.update_yaxes(tickprefix="$", ticksuffix="B")
    st.plotly_chart(fig1, use_container_width=True)

    # ── Chart 2: P/E Ratio & EPS (Line) ──────────────────────────────────────

    fig2 = make_subplots(
        rows=1, cols=2,
        subplot_titles=("P/E Ratio (×)", "Earnings Per Share ($)"),
        horizontal_spacing=0.12,
    )

    for col_idx, (key_a_vals, key_b_vals, y_fmt) in enumerate([
        (get_vals(metrics_a["pe"], YEARS),  get_vals(metrics_b["pe"], YEARS),  "{}×"),
        (get_vals(metrics_a["eps"], YEARS), get_vals(metrics_b["eps"], YEARS), "${}"),
    ], 1):
        for ticker, vals, color, grp in [
            (ticker_a, key_a_vals, COLOR_A, "a2"),
            (ticker_b, key_b_vals, COLOR_B, "b2"),
        ]:
            fig2.add_trace(
                go.Scatter(
                    name=ticker, x=YEARS, y=vals,
                    mode="lines+markers+text",
                    line=dict(color=color, width=2.5),
                    marker=dict(size=7),
                    text=[f"{v:.1f}" if v else "" for v in vals],
                    textposition="top center",
                    textfont=dict(size=9, color=color),
                    legendgroup=grp, showlegend=(col_idx == 1),
                ),
                row=1, col=col_idx
            )

    fig2.update_layout(height=440)
    apply_shared_layout(fig2)
    st.plotly_chart(fig2, use_container_width=True)

    # ── Data Tables ───────────────────────────────────────────────────────────

    st.markdown("---")
    st.markdown("### 📋 Data Tables")
    st.caption(
        "Mirrors the Excel model structure: Raw Data (inputs from SEC filings) "
        "and Calculations (derived metrics). Green = positive change, Red = negative."
    )

    YEARS_STR = [str(y) for y in YEARS]

    def to_m(series):
        """Convert a Series from raw dollars to millions, rounded to 1 decimal."""
        return series.apply(lambda x: round(x / 1e6, 1) if pd.notna(x) else None)

    def to_m_shares(series):
        return series.apply(lambda x: round(x / 1e6, 1) if pd.notna(x) else None)

    def reindex_str(series):
        """Reindex a Series to MODEL_YEARS and convert index to strings."""
        s = series.reindex(YEARS)
        s.index = YEARS_STR
        return s

    # ── Section 1: Raw Data ───────────────────────────────────────────────────

    with st.expander("📥 Raw Data  —  sourced directly from SEC EDGAR 10-K filings", expanded=True):

        raw_tab_a, raw_tab_b = st.tabs([f"🔵 {ticker_a}", f"🟠 {ticker_b}"])

        for tab, ds, color in [
            (raw_tab_a, data_a, "#1a56db"),
            (raw_tab_b, data_b, "#e07b00"),
        ]:
            with tab:
                raw_df = pd.DataFrame({
                    "Revenue ($M)":       reindex_str(to_m(ds["revenue"])),
                    "Net Income ($M)":    reindex_str(to_m(ds["net_income"])),
                    "Equity ($M)":        reindex_str(to_m(ds["equity"])),
                    "Shares (M)":         reindex_str(to_m_shares(ds["shares"])),
                    "Op. Cash Flow ($M)": reindex_str(to_m(ds["ocf"])),
                    "Stock Price ($)":    reindex_str(ds["price"]),
                }).T

                st.dataframe(
                    raw_df.style.format(
                        "{:,.1f}", na_rep="—"
                    ).set_table_styles([
                        {"selector": "th", "props": [("font-size", "12px"), ("font-weight", "bold")]},
                        {"selector": "td", "props": [("font-size", "12px")]},
                    ]),
                    use_container_width=True,
                )

    # ── Section 2: Calculations ───────────────────────────────────────────────

    with st.expander("🧮 Calculations  —  derived metrics & ratios", expanded=True):

        calc_tab_a, calc_tab_b = st.tabs([f"🔵 {ticker_a}", f"🟠 {ticker_b}"])

        def color_growth(val):
            """Green for positive growth, red for negative, grey for missing."""
            if val is None or pd.isna(val):
                return "color: #999"
            if val > 0:
                return "background-color: #d4edda; color: #155724; font-weight: bold"
            elif val < 0:
                return "background-color: #f8d7da; color: #721c24; font-weight: bold"
            return ""

        for tab, ds, metrics in [
            (calc_tab_a, data_a, metrics_a),
            (calc_tab_b, data_b, metrics_b),
        ]:
            with tab:
                calc_df = pd.DataFrame({
                    "EPS ($)":           reindex_str(metrics["eps"]),
                    "Book Value/Share ($)": reindex_str(metrics["bvps"]),
                    "CF/Share ($)":      reindex_str(metrics["cfps"]),
                    "P/E Ratio (×)":     reindex_str(metrics["pe"]),
                    "P/B Ratio (×)":     reindex_str(metrics["pb"]),
                    "P/CF Ratio (×)":    reindex_str(metrics["pcf"]),
                    "Revenue Growth":    reindex_str(metrics["rev_growth"]),
                    "Net Income Growth": reindex_str(metrics["ni_growth"]),
                    "EPS Growth":        reindex_str(metrics["eps_growth"]),
                }).T

                # Apply color to growth rows only
                growth_rows = ["Revenue Growth", "Net Income Growth", "EPS Growth"]

                def style_calc_df(df):
                    styled = pd.DataFrame("", index=df.index, columns=df.columns)
                    for row in growth_rows:
                        if row in df.index:
                            for col in df.columns:
                                val = df.loc[row, col]
                                styled.loc[row, col] = color_growth(val)
                    return styled

                # Format display: percentages for growth rows, numbers for others
                def fmt_cell(val, row_label):
                    if val is None or pd.isna(val):
                        return "—"
                    if row_label in growth_rows:
                        return f"{val:.1%}"
                    if "Ratio" in row_label:
                        return f"{val:.1f}×"
                    return f"{val:.2f}"

                # Build formatted string version for display
                calc_display = calc_df.copy().astype(object)
                for row in calc_df.index:
                    for col in calc_df.columns:
                        calc_display.loc[row, col] = fmt_cell(calc_df.loc[row, col], row)

                # Apply background color styles using the raw float values
                styled = calc_display.style.apply(
                    lambda _: style_calc_df(calc_df), axis=None
                ).set_table_styles([
                    {"selector": "th", "props": [("font-size", "12px"), ("font-weight", "bold")]},
                    {"selector": "td", "props": [("font-size", "12px")]},
                ])

                st.dataframe(styled, use_container_width=True)

                st.caption(
                    "🟢 Green = positive growth &nbsp; 🔴 Red = negative growth &nbsp; "
                    "Growth rows: Revenue Growth, Net Income Growth, EPS Growth"
                )

    # ── Data Source Footer ────────────────────────────────────────────────────

    st.markdown("---")
    st.info(
        "🔄 **Data freshness:** SEC EDGAR data is fetched live each time you click Compare — "
        "it always reflects the most recent 10-K annual filing on record. "
        "Stock prices are pulled from Yahoo Finance at the fiscal year-end date for each company.",
        icon=None
    )
    st.caption(
        "📁 Fundamental data: [SEC EDGAR XBRL API](https://www.sec.gov/dera/data/financial-statements) "
        "— 10-K annual filings &nbsp;|&nbsp; "
        "📈 Stock prices: Yahoo Finance (fiscal year-end closing price)"
    )
