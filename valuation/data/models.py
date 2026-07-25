"""
Normalized data structures shared across the whole tool.

The data layer (yfinance / SEC EDGAR / macro) maps raw, messy source data into
these clean objects so the valuation engine never has to know where a number
came from. All monetary values are in millions of the reporting currency.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional
import math


def _safe(x) -> Optional[float]:
    """Coerce to float, turning NaN/inf/None into None."""
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


# Statement-derived monetary fields (in millions of the reporting currency).
# apply_fx() scales these; margins/ratios recompute from them so they're untouched.
_MONETARY_FIELDS = ("revenue", "ebit", "gross_profit", "net_income", "da", "capex",
                    "total_debt", "cash_sti", "interest_expense", "invested_capital",
                    "fcf", "total_equity")
_MONETARY_HISTORIES = ("revenue_history", "ebit_history", "fcf_history", "net_income_history")


@dataclass
class CompanyData:
    ticker: str
    name: str = ""
    sector: str = ""
    industry: str = ""
    currency: str = "USD"                # currency the PRICE / market cap trade in
    financial_currency: str = ""         # currency the STATEMENTS are reported in
    fx_rate: Optional[float] = None      # reporting->price FX rate that was applied, if any
    fx_unresolved: bool = False          # currencies differ but the FX rate couldn't be fetched
    as_of: str = ""
    quote_type: str = ""     # EQUITY / ETF / MUTUALFUND / ... (from the data source)

    # --- Market data (per share values in currency; caps/values in millions) ---
    price: Optional[float] = None
    shares_diluted: Optional[float] = None      # millions
    market_cap: Optional[float] = None          # millions
    beta: Optional[float] = None

    # --- Latest fundamentals (TTM or most recent FY), millions ---
    revenue: Optional[float] = None
    ebit: Optional[float] = None
    gross_profit: Optional[float] = None
    net_income: Optional[float] = None
    effective_tax_rate: Optional[float] = None
    da: Optional[float] = None                   # depreciation & amortization
    capex: Optional[float] = None                # positive number
    total_debt: Optional[float] = None
    cash_sti: Optional[float] = None             # cash + short-term investments
    interest_expense: Optional[float] = None     # positive number
    invested_capital: Optional[float] = None
    fcf: Optional[float] = None                  # latest free cash flow (levered proxy)
    total_equity: Optional[float] = None         # book equity

    # --- History (most-recent-first, aligned to fiscal_years) ---
    fiscal_years: list = field(default_factory=list)
    revenue_history: list = field(default_factory=list)
    ebit_history: list = field(default_factory=list)
    fcf_history: list = field(default_factory=list)
    ebit_margin_history: list = field(default_factory=list)
    net_income_history: list = field(default_factory=list)

    # --- Analyst / consensus (optional) ---
    analyst_rev_growth_next: Optional[float] = None    # next-FY revenue growth
    analyst_target_price: Optional[float] = None

    # --- Price history / momentum (optional) ---
    ma_200: Optional[float] = None
    ret_6m: Optional[float] = None
    ret_1m: Optional[float] = None
    price_52w_high: Optional[float] = None
    price_52w_low: Optional[float] = None

    # --- Macro (attached by the fetcher) ---
    risk_free_rate: Optional[float] = None

    # --- Meta ---
    sources: list = field(default_factory=list)
    quality_notes: list = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Derived convenience metrics
    # ------------------------------------------------------------------ #
    @property
    def net_debt(self) -> Optional[float]:
        if self.total_debt is None and self.cash_sti is None:
            return None
        return (self.total_debt or 0.0) - (self.cash_sti or 0.0)

    @property
    def ebit_margin(self) -> Optional[float]:
        if self.revenue and self.ebit is not None and self.revenue != 0:
            return self.ebit / self.revenue
        return None

    @property
    def gross_margin(self) -> Optional[float]:
        if self.revenue and self.gross_profit is not None and self.revenue != 0:
            return self.gross_profit / self.revenue
        return None

    @property
    def fcf_margin(self) -> Optional[float]:
        if self.revenue and self.fcf is not None and self.revenue != 0:
            return self.fcf / self.revenue
        return None

    @property
    def net_margin(self) -> Optional[float]:
        if self.revenue and self.net_income is not None and self.revenue != 0:
            return self.net_income / self.revenue
        return None

    def revenue_growth(self, periods: int = 1) -> Optional[float]:
        """CAGR over `periods` fiscal years using the history (recent-first)."""
        h = [v for v in self.revenue_history if _safe(v) is not None]
        if len(h) <= periods:
            return None
        newest, older = h[0], h[periods]
        if older is None or older <= 0 or newest is None or newest <= 0:
            return None
        return (newest / older) ** (1.0 / periods) - 1.0

    @property
    def rev_growth_ttm(self) -> Optional[float]:
        return self.revenue_growth(1)

    @property
    def rev_cagr_3y(self) -> Optional[float]:
        return self.revenue_growth(3)

    @property
    def rev_cagr_5y(self) -> Optional[float]:
        return self.revenue_growth(5)

    @property
    def roic(self) -> Optional[float]:
        """Return on invested capital = NOPAT / invested capital."""
        if self.ebit is None or self.invested_capital in (None, 0):
            return None
        tax = self.effective_tax_rate if self.effective_tax_rate is not None else 0.21
        tax = min(max(tax, 0.0), 0.45)
        nopat = self.ebit * (1 - tax)
        if self.invested_capital <= 0:
            return None
        return nopat / self.invested_capital

    @property
    def interest_coverage(self) -> Optional[float]:
        if self.ebit is None or not self.interest_expense:
            return None
        if self.interest_expense == 0:
            return None
        return self.ebit / self.interest_expense

    @property
    def net_debt_to_ebitda(self) -> Optional[float]:
        ebitda = None
        if self.ebit is not None and self.da is not None:
            ebitda = self.ebit + self.da
        if ebitda is None or ebitda <= 0 or self.net_debt is None:
            return None
        return self.net_debt / ebitda

    @property
    def cash_runway_years(self) -> Optional[float]:
        """For cash burners: years of cash left at the current FCF burn rate."""
        if self.fcf is None or self.fcf >= 0:
            return None  # not burning
        if not self.cash_sti or self.cash_sti <= 0:
            return 0.0
        return self.cash_sti / abs(self.fcf)

    def apply_fx(self, rate: float) -> None:
        """Scale all statement-derived monetary values by `rate` (units of the
        PRICE currency per 1 unit of the reporting currency). Used for ADRs /
        foreign listings whose statements are in a different currency than the
        price. Market data (price, market cap, shares) is left untouched, and
        margins/ratios recompute from the scaled fields, so only the raw
        currency amounts change."""
        if not rate or rate <= 0:
            return
        for f in _MONETARY_FIELDS:
            v = getattr(self, f)
            if v is not None:
                setattr(self, f, v * rate)
        for f in _MONETARY_HISTORIES:
            seq = getattr(self, f) or []
            setattr(self, f, [(x * rate if x is not None else None) for x in seq])
        self.fx_rate = rate

    def to_dict(self) -> dict:
        d = asdict(self)
        # add computed fields the UI wants
        d.update(
            net_debt=self.net_debt,
            ebit_margin=self.ebit_margin,
            gross_margin=self.gross_margin,
            fcf_margin=self.fcf_margin,
            net_margin=self.net_margin,
            rev_growth_ttm=self.rev_growth_ttm,
            rev_cagr_3y=self.rev_cagr_3y,
            rev_cagr_5y=self.rev_cagr_5y,
            roic=self.roic,
            interest_coverage=self.interest_coverage,
            net_debt_to_ebitda=self.net_debt_to_ebitda,
            cash_runway_years=self.cash_runway_years,
        )
        return d
