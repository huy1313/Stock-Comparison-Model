"""
data.py — All data fetching and calculation logic
=================================================
Two data sources:
  1. SEC EDGAR  → fundamentals (Revenue, Net Income, Equity, Shares, Cash Flow)
                  Free, official, pulled directly from 10-K annual filings
  2. Yahoo Finance → stock prices only (not available on EDGAR)

Flow for each ticker:
  get_cik() → get_company_info() → get_company_facts() → extract each metric
  → get_year_end_prices() → calculate_metrics()
"""

import requests
import pandas as pd
import yfinance as yf
import calendar
import streamlit as st

# ── Constants ─────────────────────────────────────────────────────────────────

EDGAR_BASE = "https://data.sec.gov"

# EDGAR requires a User-Agent header identifying who is making requests
EDGAR_HEADERS = {
    "User-Agent": "StockComparisonModel contact@stockmodel.com",
    "Accept-Encoding": "gzip, deflate",
}

# Years our model covers
MODEL_YEARS = list(range(2015, 2025))

# Revenue can be tagged differently by different companies in EDGAR
# (Older standard vs. newer ASC 606 accounting standard)
REVENUE_CONCEPTS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",  # Modern standard
    "Revenues",                                              # General
    "SalesRevenueNet",                                       # Older standard
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueGoodsNet",
]


# ── Step 1: Look up the company's CIK number ─────────────────────────────────
# CIK = Central Index Key. Every public company has one. Required for EDGAR API.

@st.cache_data(ttl=86400)   # Cache for 24 hours (changes rarely)
def _load_ticker_map():
    """Download the full SEC ticker → CIK mapping. Cached for 24h."""
    url = "https://www.sec.gov/files/company_tickers.json"
    resp = requests.get(url, headers=EDGAR_HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    # Build a dict: {"AAPL": "0000320193", "MSFT": "0000789019", ...}
    return {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in data.values()}


def get_cik(ticker: str) -> str | None:
    """Return the 10-digit CIK for a ticker, or None if not found."""
    mapping = _load_ticker_map()
    return mapping.get(ticker.upper())


@st.cache_data(ttl=86400)
def get_ticker_options() -> list[str]:
    """
    Return a sorted list of 'TICKER — Company Name' strings for autocomplete.
    Sourced from SEC EDGAR's full company ticker list.
    """
    url = "https://www.sec.gov/files/company_tickers.json"
    resp = requests.get(url, headers=EDGAR_HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    options = [
        f"{v['ticker'].upper()} — {v['name']}"
        for v in data.values()
        if v.get("ticker") and v.get("name")
    ]
    return sorted(options)


# ── Step 2: Get company name and fiscal year end ──────────────────────────────

@st.cache_data(ttl=86400)
def get_company_info(cik: str) -> dict:
    """
    Returns company name and fiscal year end month.
    e.g. Apple → name='Apple Inc.', fy_end_month=9 (September)
         Microsoft → name='Microsoft Corp', fy_end_month=6 (June)
    """
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    resp = requests.get(url, headers=EDGAR_HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    # fiscalYearEnd is stored as "MMDD" string, e.g. "0930" = September 30
    fy_raw = data.get("fiscalYearEnd", "1231")
    return {
        "name": data.get("name", "Unknown"),
        "fy_end_month": int(fy_raw[:2]),   # First two digits = month number
    }


# ── Step 3: Download all XBRL financial facts for the company ────────────────

@st.cache_data(ttl=0)   # No cache — always pull the latest filing from EDGAR
def get_company_facts(cik: str) -> dict:
    """
    Fetch all XBRL-tagged financial data for a company from EDGAR.
    This is a large JSON file containing every reported number.
    We pull from it in subsequent functions.
    """
    url = f"{EDGAR_BASE}/api/xbrl/companyfacts/CIK{cik}.json"
    resp = requests.get(url, headers=EDGAR_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ── Step 4: Extract a specific metric from the facts ─────────────────────────

def extract_annual(facts: dict, concept: str, unit: str = "USD") -> dict:
    """
    Pull annual 10-K values for one XBRL concept (e.g. 'NetIncomeLoss').

    Why 10-K only? The user wants fiscal year totals. A 10-K IS the annual
    filing — it already contains the full-year aggregated numbers that were
    built from the four 10-Q quarterly filings throughout the year.
    Pulling from 10-K gives us the most accurate, audited annual figure.

    Returns: {year: value} dict
    """
    try:
        records = facts["facts"]["us-gaap"][concept]["units"][unit]
    except KeyError:
        return {}

    df = pd.DataFrame(records)

    # Keep only annual filings (10-K and 10-K/A which is an amended annual)
    df = df[df["form"].isin(["10-K", "10-K/A"])].copy()

    if df.empty:
        return {}

    df["end"] = pd.to_datetime(df["end"])
    df["year"] = df["end"].dt.year

    # If there are multiple filings for the same year (e.g. amendments),
    # keep the most recently filed one — it's the most accurate
    df = df.sort_values("filed").drop_duplicates("year", keep="last")

    return df.set_index("year")["val"].to_dict()


def get_revenue(facts: dict) -> dict:
    """Try multiple XBRL tags for revenue — different companies use different ones."""
    for concept in REVENUE_CONCEPTS:
        data = extract_annual(facts, concept)
        if len(data) >= 2:   # Found something useful
            return data
    return {}


# ── Step 5: Get stock prices from Yahoo Finance ───────────────────────────────

@st.cache_data(ttl=3600)
def get_year_end_prices(ticker: str, fy_end_month: int) -> dict:
    """
    Get the stock's closing price on each fiscal year-end date.
    Example: Apple FY2023 ended Sep 30, 2023 → price on that date.

    Why Yahoo Finance? SEC EDGAR only contains company filings.
    Stock prices are market data, not reported to the SEC.
    """
    stock = yf.Ticker(ticker)
    hist = stock.history(period="15y")

    if hist.empty:
        return {}

    # Make index timezone-naive for comparison
    hist.index = hist.index.tz_localize(None)

    prices = {}
    for year in MODEL_YEARS:
        # Build the target date (last day of fiscal year end month)
        last_day = calendar.monthrange(year, fy_end_month)[1]
        target = pd.Timestamp(f"{year}-{fy_end_month:02d}-{last_day}")

        # Find the most recent trading day on or before that date
        available = hist.index[hist.index <= target]
        if len(available) > 0:
            prices[year] = round(float(hist.loc[available[-1], "Close"]), 2)

    return prices


# ── Step 6: Assemble everything into one dataset ─────────────────────────────

def build_dataset(ticker: str) -> dict:
    """
    Main function. Fetches all data for one ticker.
    Returns a dict of {metric_name: pd.Series indexed by year}.
    """
    ticker = ticker.upper().strip()

    # Check if this is an ETF or fund via Yahoo Finance — these have no 10-K filings
    try:
        import yfinance as _yf
        quote_type = _yf.Ticker(ticker).info.get("quoteType", "")
        if quote_type in ("ETF", "MUTUALFUND", "INDEX", "FUTURE", "CURRENCY"):
            raise ValueError(
                f"'{ticker}' is a {quote_type} — not a company stock. "
                "This model is designed for individual company stocks that file "
                "annual reports (10-K) with the SEC. ETFs and mutual funds do not "
                "report revenue, net income, or equity, so ratios like P/E and P/B "
                "cannot be calculated. Try a stock like AAPL, MSFT, TSLA, or NVDA."
            )
    except ValueError:
        raise   # Re-raise our own error
    except Exception:
        pass    # If Yahoo check fails, continue and let EDGAR handle it

    # Look up the company's CIK
    cik = get_cik(ticker)
    if not cik:
        raise ValueError(
            f"'{ticker}' not found in SEC EDGAR. "
            "Only US-listed public company stocks are supported. "
            "ETFs, mutual funds, and foreign-listed companies are not available."
        )

    # Get company metadata
    info = get_company_info(cik)

    # Download all facts from EDGAR
    facts = get_company_facts(cik)

    fy_month = info["fy_end_month"]

    # Extract each line item — filter to MODEL_YEARS after building Series
    def to_series(d: dict) -> pd.Series:
        s = pd.Series(d)
        return s[s.index.isin(MODEL_YEARS)].sort_index()

    revenue    = to_series(get_revenue(facts))
    net_income = to_series(extract_annual(facts, "NetIncomeLoss"))
    equity     = to_series(extract_annual(facts, "StockholdersEquity"))
    shares     = to_series(extract_annual(facts, "CommonStockSharesOutstanding", unit="shares"))
    ocf        = to_series(extract_annual(facts, "NetCashProvidedByUsedInOperatingActivities"))
    prices     = to_series(get_year_end_prices(ticker, fy_month))

    return {
        "name":         info["name"],
        "ticker":       ticker,
        "fy_end_month": fy_month,
        "revenue":      revenue,
        "net_income":   net_income,
        "equity":       equity,
        "shares":       shares,
        "ocf":          ocf,
        "price":        prices,
    }


# ── Step 7: Calculate ratios and growth rates ─────────────────────────────────

def calculate_metrics(ds: dict) -> dict:
    """
    Compute all derived metrics from raw data.
    This is the same logic we designed in the Excel Calculations sheet,
    now expressed as Python formulas.
    """
    def safe_divide(a, b):
        """Divide two Series, replacing infinities and errors with None."""
        result = a / b
        return result.replace([float("inf"), -float("inf")], None)

    # Per-share metrics (divide dollar amounts by share count)
    eps  = safe_divide(ds["net_income"], ds["shares"])   # Earnings per share
    bvps = safe_divide(ds["equity"],     ds["shares"])   # Book value per share
    cfps = safe_divide(ds["ocf"],        ds["shares"])   # Cash flow per share

    # Valuation ratios (what the market charges vs. what the company produces)
    pe  = safe_divide(ds["price"], eps)    # Price / Earnings
    pb  = safe_divide(ds["price"], bvps)   # Price / Book Value
    pcf = safe_divide(ds["price"], cfps)   # Price / Cash Flow

    # Year-over-year growth rates
    # pct_change() computes (current - prior) / prior automatically
    rev_growth = ds["revenue"].pct_change()
    ni_growth  = ds["net_income"].pct_change()
    eps_growth = eps.pct_change()

    return {
        "eps":        eps.round(4),
        "bvps":       bvps.round(4),
        "cfps":       cfps.round(4),
        "pe":         pe.round(2),
        "pb":         pb.round(2),
        "pcf":        pcf.round(2),
        "rev_growth": rev_growth.round(4),
        "ni_growth":  ni_growth.round(4),
        "eps_growth": eps_growth.round(4),
    }
