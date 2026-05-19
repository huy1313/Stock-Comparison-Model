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
  6. Raw data table (expandable)
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

# Custom styling
st.markdown("""
    <style>
    .metric-label { font-size: 0.85rem; color: #666; }
    .company-header { padding: 12px; border-radius: 8px; margin-bottom: 8px; }
    </style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────

st.title("📊 Stock Comparison Model")
st.markdown(
    "Compare two public companies across 10 years of fundamental data. "
    "Fundamentals sourced from **SEC EDGAR** (official quarterly filings). "
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
    st.write("")   # Spacing to align button with inputs
    st.write("")
    compare_clicked = st.button("Compare ▶", type="primary", use_container_width=True)

# ── Main Logic: runs when Compare button is clicked ──────────────────────────

if compare_clicked and ticker_a and ticker_b:

    if ticker_a == ticker_b:
        st.warning("Please enter two different ticker symbols.")
        st.stop()

    # Fetch data for both companies (shows a spinner while loading)
    with st.spinner(f"Fetching SEC EDGAR data for {ticker_a} and {ticker_b}..."):
        try:
            data_a   = build_dataset(ticker_a)
            metrics_a = calculate_metrics(data_a)
        except ValueError as e:
            st.error(f"**{ticker_a}**: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Error fetching {ticker_a}: {e}")
            st.stop()

        try:
            data_b   = build_dataset(ticker_b)
            metrics_b = calculate_metrics(data_b)
        except ValueError as e:
            st.error(f"**{ticker_b}**: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Error fetching {ticker_b}: {e}")
            st.stop()

    # ── Company Headers ───────────────────────────────────────────────────────

    st.markdown("---")
    h_col_a, h_col_b = st.columns(2)

    MONTH_NAMES = {
        1:"January", 2:"February", 3:"March", 4:"April",
        5:"May", 6:"June", 7:"July", 8:"August",
        9:"September", 10:"October", 11:"November", 12:"December"
    }

    with h_col_a:
        st.markdown(
            f"<div style='background:#e8f0fe;padding:14px;border-radius:8px;'>"
            f"<h3 style='margin:0;color:#1a56db'>🔵 {data_a['name']}</h3>"
            f"<p style='margin:4px 0 0 0;color:#555'>Ticker: <b>{ticker_a}</b> &nbsp;|&nbsp; "
            f"Fiscal Year ends: <b>{MONTH_NAMES[data_a['fy_end_month']]}</b></p>"
            f"</div>",
            unsafe_allow_html=True
        )

    with h_col_b:
        st.markdown(
            f"<div style='background:#fff3e0;padding:14px;border-radius:8px;'>"
            f"<h3 style='margin:0;color:#c45000'>🟠 {data_b['name']}</h3>"
            f"<p style='margin:4px 0 0 0;color:#555'>Ticker: <b>{ticker_b}</b> &nbsp;|&nbsp; "
            f"Fiscal Year ends: <b>{MONTH_NAMES[data_b['fy_end_month']]}</b></p>"
            f"</div>",
            unsafe_allow_html=True
        )

    # ── Most Recent Year Summary ──────────────────────────────────────────────

    st.markdown("### Most Recent Year — Side by Side")

    # Find the most recent year where both companies have P/E data
    years_with_data = (
        set(metrics_a["pe"].dropna().index) &
        set(metrics_b["pe"].dropna().index)
    )
    last_year = max(years_with_data) if years_with_data else 2024

    def fmt(value, format_str):
        """Safely format a value, returning '—' if None or NaN."""
        try:
            if value is None or pd.isna(value):
                return "—"
            return format_str.format(value)
        except Exception:
            return "—"

    # Build summary table
    summary_rows = [
        ("P/E Ratio",             metrics_a["pe"].get(last_year),         metrics_b["pe"].get(last_year),         "{:.1f}×"),
        ("P/B Ratio",             metrics_a["pb"].get(last_year),         metrics_b["pb"].get(last_year),         "{:.1f}×"),
        ("P/CF Ratio",            metrics_a["pcf"].get(last_year),        metrics_b["pcf"].get(last_year),        "{:.1f}×"),
        ("Earnings Per Share",    metrics_a["eps"].get(last_year),        metrics_b["eps"].get(last_year),        "${:.4f}"),
        ("Revenue Growth (YoY)",  metrics_a["rev_growth"].get(last_year), metrics_b["rev_growth"].get(last_year), "{:.1%}"),
        ("Net Income Growth",     metrics_a["ni_growth"].get(last_year),  metrics_b["ni_growth"].get(last_year),  "{:.1%}"),
        ("Stock Price",           data_a["price"].get(last_year),         data_b["price"].get(last_year),         "${:.2f}"),
    ]

    # Display as styled table
    summary_html = f"""
    <table style='width:100%;border-collapse:collapse;font-size:0.95rem;'>
        <thead>
            <tr style='background:#f0f0f0;'>
                <th style='padding:10px;text-align:left;border-bottom:2px solid #ddd;'>Metric ({last_year})</th>
                <th style='padding:10px;text-align:center;border-bottom:2px solid #ddd;color:#1a56db'>{ticker_a}</th>
                <th style='padding:10px;text-align:center;border-bottom:2px solid #ddd;color:#c45000'>{ticker_b}</th>
            </tr>
        </thead>
        <tbody>
    """
    for i, (label, val_a, val_b, fmt_str) in enumerate(summary_rows):
        bg = "#ffffff" if i % 2 == 0 else "#f9f9f9"
        summary_html += f"""
            <tr style='background:{bg};'>
                <td style='padding:9px 10px;border-bottom:1px solid #eee;'>{label}</td>
                <td style='padding:9px 10px;text-align:center;border-bottom:1px solid #eee;font-weight:500;'>{fmt(val_a, fmt_str)}</td>
                <td style='padding:9px 10px;text-align:center;border-bottom:1px solid #eee;font-weight:500;'>{fmt(val_b, fmt_str)}</td>
            </tr>
        """
    summary_html += "</tbody></table>"
    st.markdown(summary_html, unsafe_allow_html=True)

    # ── Charts ────────────────────────────────────────────────────────────────

    st.markdown("---")
    st.markdown("### 10-Year Historical Charts")

    YEARS = list(range(2015, 2025))
    COLOR_A = "#1a56db"   # Blue for Company A
    COLOR_B = "#c45000"   # Orange for Company B

    def get_vals(series, years, scale=1):
        """Get a list of values for given years. None = missing data (shows gap in chart)."""
        return [
            round(series.get(y) / scale, 2) if series.get(y) is not None and pd.notna(series.get(y)) else None
            for y in years
        ]

    # ── Chart Row 1: Revenue & Net Income ────────────────────────────────────

    fig1 = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Annual Revenue ($B)", "Net Income ($B)"),
        horizontal_spacing=0.1
    )

    for col_idx, (key, label) in enumerate([("revenue", "Revenue"), ("net_income", "Net Income")], 1):
        vals_a = get_vals(data_a[key], YEARS, scale=1e9)   # Convert to billions
        vals_b = get_vals(data_b[key], YEARS, scale=1e9)

        fig1.add_trace(
            go.Bar(name=ticker_a, x=YEARS, y=vals_a, marker_color=COLOR_A,
                   legendgroup="a", showlegend=(col_idx == 1)),
            row=1, col=col_idx
        )
        fig1.add_trace(
            go.Bar(name=ticker_b, x=YEARS, y=vals_b, marker_color=COLOR_B,
                   legendgroup="b", showlegend=(col_idx == 1)),
            row=1, col=col_idx
        )

    fig1.update_layout(
        barmode="group", height=400,
        margin=dict(t=50, b=30, l=10, r=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    fig1.update_xaxes(tickformat="d", dtick=1)
    fig1.update_yaxes(tickprefix="$", ticksuffix="B")
    st.plotly_chart(fig1, use_container_width=True)

    # ── Chart Row 2: P/E Ratio & EPS ─────────────────────────────────────────

    fig2 = make_subplots(
        rows=1, cols=2,
        subplot_titles=("P/E Ratio (×)", "Earnings Per Share ($)"),
        horizontal_spacing=0.1
    )

    pe_a  = get_vals(metrics_a["pe"],  YEARS)
    pe_b  = get_vals(metrics_b["pe"],  YEARS)
    eps_a = get_vals(metrics_a["eps"], YEARS)
    eps_b = get_vals(metrics_b["eps"], YEARS)

    for col_idx, (vals_a, vals_b) in enumerate([(pe_a, pe_b), (eps_a, eps_b)], 1):
        fig2.add_trace(
            go.Scatter(name=ticker_a, x=YEARS, y=vals_a, mode="lines+markers",
                       line=dict(color=COLOR_A, width=2),
                       marker=dict(size=6),
                       legendgroup="a2", showlegend=(col_idx == 1)),
            row=1, col=col_idx
        )
        fig2.add_trace(
            go.Scatter(name=ticker_b, x=YEARS, y=vals_b, mode="lines+markers",
                       line=dict(color=COLOR_B, width=2),
                       marker=dict(size=6),
                       legendgroup="b2", showlegend=(col_idx == 1)),
            row=1, col=col_idx
        )

    fig2.update_layout(
        height=400,
        margin=dict(t=50, b=30, l=10, r=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    fig2.update_xaxes(tickformat="d", dtick=1)
    st.plotly_chart(fig2, use_container_width=True)

    # ── Raw Data Table (expandable) ───────────────────────────────────────────

    with st.expander("📋 View Raw Data Table"):
        def build_table(ds, metrics, name):
            rows = {
                "Revenue ($M)":      ds["revenue"].apply(lambda x: round(x/1e6,1) if pd.notna(x) else None),
                "Net Income ($M)":   ds["net_income"].apply(lambda x: round(x/1e6,1) if pd.notna(x) else None),
                "Equity ($M)":       ds["equity"].apply(lambda x: round(x/1e6,1) if pd.notna(x) else None),
                "Shares (M)":        ds["shares"].apply(lambda x: round(x/1e6,1) if pd.notna(x) else None),
                "Op. Cash Flow ($M)":ds["ocf"].apply(lambda x: round(x/1e6,1) if pd.notna(x) else None),
                "Stock Price ($)":   ds["price"],
                "EPS ($)":           metrics["eps"],
                "P/E Ratio (×)":     metrics["pe"],
                "P/B Ratio (×)":     metrics["pb"],
                "P/CF Ratio (×)":    metrics["pcf"],
                "Revenue Growth":    metrics["rev_growth"].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "—"),
                "NI Growth":         metrics["ni_growth"].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "—"),
            }
            df = pd.DataFrame(rows).T
            df.columns = [str(y) for y in df.columns]
            return df

        tab_a, tab_b = st.tabs([ticker_a, ticker_b])
        with tab_a:
            st.dataframe(build_table(data_a, metrics_a, ticker_a), use_container_width=True)
        with tab_b:
            st.dataframe(build_table(data_b, metrics_b, ticker_b), use_container_width=True)

    # ── Data Source Footer ────────────────────────────────────────────────────

    st.markdown("---")
    st.caption(
        "📁 **Fundamental data** (Revenue, Net Income, Equity, Shares, Operating Cash Flow): "
        "[SEC EDGAR XBRL API](https://www.sec.gov/dera/data/financial-statements) — "
        "pulled directly from 10-K annual filings &nbsp;|&nbsp; "
        "📈 **Stock prices**: Yahoo Finance (fiscal year-end closing price)"
    )
