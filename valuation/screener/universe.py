"""
The scanning universe.

Two ways to get the list of tickers to score:
  * BUNDLED_UNIVERSE — a curated set of liquid US large/mid-caps across all 11
    sectors, sector-labeled so the free path works out of the box with no keys.
  * A provider's whole-market list (FMP screener, or SEC EDGAR's full filer list)
    when you want the full ~5,000+ names.

The bundled list is deliberately a "solid section of the market," not exhaustive;
set an FMP key (or run the EDGAR universe) to scan everything.
"""
from __future__ import annotations

# sector -> representative liquid tickers (GICS-ish buckets)
BUNDLED_UNIVERSE = {
    "Technology": ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "ADBE", "AMD", "CSCO", "ACN",
                   "INTC", "TXN", "QCOM", "IBM", "NOW", "INTU", "AMAT", "MU", "PANW", "SNPS",
                   "CRWD", "PLTR", "SNOW", "DELL", "ANET"],
    "Communication Services": ["GOOGL", "META", "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS",
                               "CHTR", "EA", "TTD", "WBD", "OMC", "PINS", "SNAP"],
    "Consumer Cyclical": ["AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "SBUX", "TJX", "BKNG",
                          "ABNB", "MAR", "GM", "F", "CMG", "ROST", "ORLY", "LULU", "DHI"],
    "Consumer Defensive": ["WMT", "PG", "KO", "PEP", "COST", "PM", "MDLZ", "CL", "MO", "TGT",
                           "KMB", "GIS", "KHC", "SYY", "KR", "MNST"],
    "Healthcare": ["UNH", "JNJ", "LLY", "ABBV", "MRK", "TMO", "ABT", "PFE", "DHR", "AMGN",
                   "ISRG", "BMY", "GILD", "CVS", "MDT", "VRTX", "REGN", "CI", "HCA", "ELV"],
    "Financial Services": ["BRK.B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP", "SCHW",
                           "C", "BLK", "SPGI", "CB", "PGR", "PNC", "USB", "COF", "MET", "AIG"],
    "Industrials": ["CAT", "GE", "RTX", "HON", "UNP", "BA", "UPS", "DE", "LMT", "ADP",
                    "ETN", "GD", "NOC", "CSX", "EMR", "FDX", "WM", "ITW", "PH", "TT"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "OXY", "WMB", "VLO",
               "KMI", "HES", "DVN", "HAL", "OKE"],
    "Basic Materials": ["LIN", "SHW", "APD", "ECL", "FCX", "NEM", "DOW", "NUE", "DD", "PPG",
                        "VMC", "MLM", "ALB", "CF"],
    "Utilities": ["NEE", "SO", "DUK", "SRE", "AEP", "D", "EXC", "XEL", "PEG", "ED",
                  "WEC", "PCG", "EIX", "AWK"],
    "Real Estate": ["PLD", "AMT", "EQIX", "PSA", "O", "CCI", "SPG", "WELL", "DLR", "VICI",
                    "SBAC", "AVB", "EXR", "IRM"],
}


def bundled_tickers() -> list[str]:
    out = []
    for tickers in BUNDLED_UNIVERSE.values():
        out.extend(tickers)
    return out


def bundled_sector_map() -> dict:
    m = {}
    for sector, tickers in BUNDLED_UNIVERSE.items():
        for t in tickers:
            m[t] = sector
    return m
