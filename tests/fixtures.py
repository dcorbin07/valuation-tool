"""Synthetic CompanyData fixtures for offline testing (no network)."""
from valuation.data.models import CompanyData


def build_nike() -> CompanyData:
    """Reconstruction of Donovan's Nike FY2025 model inputs."""
    return CompanyData(
        ticker="NKE", name="NIKE, Inc.", sector="Consumer Cyclical",
        industry="Footwear & Accessories", currency="USD",
        price=42.5, shares_diluted=1480.0, market_cap=42.5 * 1480, beta=1.1,
        revenue=46309, ebit=3700, gross_profit=0.44 * 46309, net_income=3200,
        effective_tax_rate=0.21, da=810, capex=926, total_debt=8000, cash_sti=8100,
        interest_expense=280, invested_capital=13900, fcf=4800, total_equity=14000,
        fiscal_years=[2025, 2024, 2023, 2022, 2021],
        revenue_history=[46309, 51362, 46710, 44538, 37403],
        ebit_history=[3700, 6007, 5886, 6899, 5610],
        ebit_margin_history=[0.080, 0.117, 0.126, 0.155, 0.150],
        ma_200=44.0, ret_6m=-0.08, ret_1m=0.02, price_52w_high=58.0, price_52w_low=38.0,
        risk_free_rate=0.043,
    )


def build_growth() -> CompanyData:
    """A cash-burning hypergrowth SaaS company."""
    return CompanyData(
        ticker="GROW", name="Hypergrowth SaaS Co", sector="Technology",
        industry="Software—Application", currency="USD",
        price=50.0, shares_diluted=300.0, market_cap=50 * 300, beta=1.6,
        revenue=2000, ebit=-200, gross_profit=0.75 * 2000, net_income=-250,
        effective_tax_rate=0.0, da=40, capex=60, total_debt=200, cash_sti=1500,
        interest_expense=10, invested_capital=1200, fcf=-300, total_equity=1000,
        fiscal_years=[2025, 2024, 2023, 2022, 2021],
        revenue_history=[2000, 1400, 950, 620, 400],
        ebit_history=[-200, -260, -300, -280, -240],
        ebit_margin_history=[-0.10, -0.186, -0.316, -0.452, -0.60],
        analyst_rev_growth_next=0.35,
        ma_200=44.0, ret_6m=0.22, ret_1m=0.05, price_52w_high=62.0, price_52w_low=28.0,
        risk_free_rate=0.043,
    )
