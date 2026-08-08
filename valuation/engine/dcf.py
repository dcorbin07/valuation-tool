"""
Core DCF engine — unlevered free cash flow to the firm (FCFF).

Design choices that make it work for ANY company, not just mature ones:

  * Reinvestment is tied to growth via a sales-to-capital ratio
    (reinvestment = ΔRevenue / sales-to-capital), the standard way to value
    growth firms — instead of fixed capex/D&A percentages that break when a
    company is scaling.
  * Early-year operating losses accrue a net-operating-loss (NOL) balance that
    shields future taxes, so pre-profit cash-burners are taxed realistically.
  * The terminal value uses a reinvestment rate consistent with terminal ROIC
    (reinvestment = g / ROIC), so perpetual growth is paid for and the terminal
    value can't quietly assume free growth.

Equity value = Enterprise value − net debt; per share = equity / diluted shares.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..data.models import CompanyData
from .assumptions import AssumptionSet


# --------------------------------------------------------------------------- #
# TERMINAL-VALUE SANITY KNOBS. Defaults below are the behaviour as of 2026-08-05;
# they are named constants so a candidate fix can be measured against the live
# universe rather than argued about. See HANDOFF_live_data_bugs.md Part 2.
#
# MIN_TERMINAL_SPREAD was 0.005 — a 0.5pp floor is a 200x terminal multiple, i.e.
# nominally a guard and effectively none. It never bound on a real name.
#
# 3.0pp = a 33.3x terminal multiple, the generous end of what a mature business supports.
# ADOPTED ON COHERENCE, NULL ON PERFORMANCE (Don's call, 2026-08-05): measured on the
# 241-name universe it resolved NONE of the withheld names — it did not pass the
# pre-registered resolve-the-names test in HANDOFF_live_data_bugs.md Part 2 — but its
# measured harm is zero (median |delta| 0.000%, 0/128 names moved >25%, 0 pushed out of
# the guard band). It ships because a floor that has never bound is not a floor, the same
# way the point-in-time EV fix shipped on correctness rather than performance.
MIN_TERMINAL_SPREAD = 0.030
# None = uncapped. A cap of N reads as "we will not assume a business is worth
# more than N x its terminal free cash flow".
MAX_TERMINAL_MULTIPLE = None

# --------------------------------------------------------------------------- #
# REINVESTMENT FLOOR. See HANDOFF_live_data_bugs.md Part 8.
#
# Reinvestment is modelled as `delta revenue / sales_to_capital` — GROWTH CAPITAL ONLY. That is
# the standard Damodaran formulation and it is right when capital needs scale with growth. It
# collapses when revenue is flat: a capex-heavy company that must spend billions simply to stand
# still is charged almost nothing, and a SHRINKING one is credited cash it never releases
# (XOM −17,131, TTE −12,778 against real positive net capital spend).
#
# The floor charges at least the company's own observed net capital spend, scaled with revenue:
#     floor_t = w_t * (capex − D&A) * rev_t / rev_0
# GATED ON `capex − D&A > 0`, which is what makes a control group exist: a name with capex <= D&A,
# or missing either input, never enters this path and is bit-identical by construction.
#
#   "off"        — the pre-Part-8 behaviour.
#   "decay"      — ARM A: w_t fades linearly 1 -> 0 across the forecast; terminal UNTOUCHED.
#   "persistent" — ARM B: w_t = 1 throughout, and the terminal charge is floored too.
#
# The terminal is the whole question: the worst-undercharged names carry 80%+ of EV there, so an
# arm that stops at the explicit forecast cannot fix most of the problem by construction.
REINVESTMENT_FLOOR_MODE = "off"


def _terminal_roic(cd: CompanyData, wacc: float) -> float:
    """Terminal return on invested capital. Defaults to a slim moat over WACC,
    nudged by the firm's current ROIC, bounded so terminal value stays sane."""
    base = wacc + 0.01
    cur = cd.roic
    if cur is not None and cur > 0:
        base = 0.5 * base + 0.5 * cur
    return max(wacc + 0.005, min(base, wacc + 0.06))


@dataclass
class DCFResult:
    per_share: Optional[float]
    equity_value: float
    enterprise_value: float
    pv_explicit: float
    pv_terminal: float
    terminal_value: float
    tv_pct_of_ev: float
    wacc: float
    terminal_growth: float
    terminal_roic: float
    net_debt: float
    shares: Optional[float]
    label: str
    rows: list = field(default_factory=list)
    terminal_multiple: Optional[float] = None   # TV per unit of terminal FCFF (1/spread)
    assumed_terminal_growth: Optional[float] = None  # before the spread clamp, if it bound
    # Year-1 modelled reinvestment against the company's OBSERVED net capital spend
    # (capex - D&A). Reinvestment is modelled as `delta revenue / sales_to_capital`, which
    # goes to zero when revenue is flat — so a capex-heavy company that must spend billions
    # simply to stand still is charged almost nothing. Reported, NOT corrected: changing how
    # reinvestment is modelled moves every valuation in the product and needs its own
    # pre-registered task. See HANDOFF_live_data_bugs.md Part 4 item 2.
    reinvestment_y1: Optional[float] = None
    observed_net_capex: Optional[float] = None

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        return d


def _net_capex_floor(cd: CompanyData, a: AssumptionSet):
    """`(nc, rev_0)` when the reinvestment floor applies to this name, else `(None, None)`.

    THE GATE IS THE CONTROL GROUP. `capex <= D&A`, or either input missing, returns None and the
    caller's arithmetic is untouched — bit-identical by construction rather than by tolerance.
    """
    if REINVESTMENT_FLOOR_MODE == "off":
        return None, None
    if cd.capex is None or cd.da is None:
        return None, None
    nc = cd.capex - cd.da
    rev0 = a.base_revenue
    if nc <= 0 or not rev0 or rev0 <= 0:
        return None, None
    return nc, rev0


def _project(cd: CompanyData, a: AssumptionSet, wacc: float, troic: float, collect_rows: bool):
    """Shared projection core. Returns (per_share, ev, pv_explicit, pv_tv, tv, rows)."""
    nc, rev0_floor = _net_capex_floor(cd, a)
    rev_prev = a.base_revenue
    nol = 0.0
    pv_explicit = 0.0
    rows = [] if collect_rows else None

    last_rev = rev_prev
    for t in range(1, a.n_years + 1):
        g = a.rev_growth_path[t - 1]
        rev = rev_prev * (1 + g)
        m = a.op_margin_path[t - 1]
        ebit = rev * m

        if ebit <= 0:
            taxes = 0.0
            nol += -ebit
        else:
            taxable = max(0.0, ebit - nol)
            nol -= (ebit - taxable)
            taxes = taxable * a.tax_rate
        nopat = ebit - taxes

        d_rev = rev - rev_prev
        reinvest = d_rev / a.sales_to_capital if a.sales_to_capital else 0.0
        if nc is not None:
            # Arm A fades the floor out as growth normalises; Arm B holds it.
            if REINVESTMENT_FLOOR_MODE == "decay":
                w = (a.n_years - t) / (a.n_years - 1) if a.n_years > 1 else 1.0
            else:
                w = 1.0
            reinvest = max(reinvest, w * nc * rev / rev0_floor)
        fcff = nopat - reinvest

        disc = 1.0 / (1.0 + wacc) ** t
        pv = fcff * disc
        pv_explicit += pv

        if collect_rows:
            rows.append({
                "year": t, "revenue": rev, "growth": g, "op_margin": m, "ebit": ebit,
                "taxes": -taxes, "nopat": nopat, "reinvestment": -reinvest, "fcff": fcff,
                "discount_factor": disc, "pv_fcff": pv,
            })
        rev_prev = rev
        last_rev = rev

    # Terminal value (Gordon growth) with ROIC-consistent reinvestment.
    # Terminal growth is held at least MIN_TERMINAL_SPREAD below the discount rate, and
    # the SAME clamped g feeds the numerator (growth and its reinvestment charge) as the
    # denominator — flooring only the denominator would price cash flows that grow at a
    # rate the terminal value refuses to discount for.
    g_term = min(a.terminal_growth, wacc - MIN_TERMINAL_SPREAD)
    denom = max(wacc - g_term, MIN_TERMINAL_SPREAD)
    term_margin = a.op_margin_path[-1]
    ebit_next = last_rev * (1 + g_term) * term_margin
    nopat_next = ebit_next * (1 - a.tax_rate)
    reinvest_rate_term = min(0.9, g_term / troic) if troic > 0 else 0.0
    if nc is not None and REINVESTMENT_FLOOR_MODE == "persistent":
        # ARM B ONLY. Without this the fix stops at the explicit forecast, and the worst-
        # undercharged names carry 80%+ of their EV in the terminal — so leaving it out fixes
        # a fraction of the problem while looking like a fix.
        # The untouched branch keeps its ORIGINAL expression verbatim: rewriting
        # `nopat*(1-r)` as `nopat - nopat*r` differs in the last ulp and would move every
        # name in the control group for no reason.
        rev_term = last_rev * (1 + g_term)
        fcff_term = nopat_next - max(nopat_next * reinvest_rate_term,
                                     nc * rev_term / rev0_floor)
    else:
        fcff_term = nopat_next * (1 - reinvest_rate_term)
    tv = fcff_term / denom
    if MAX_TERMINAL_MULTIPLE is not None and fcff_term > 0:
        tv = min(tv, MAX_TERMINAL_MULTIPLE * fcff_term)
    disc_n = 1.0 / (1.0 + wacc) ** a.n_years
    pv_tv = tv * disc_n

    ev = pv_explicit + pv_tv
    net_debt = cd.net_debt if cd.net_debt is not None else 0.0
    equity = ev - net_debt
    shares = cd.shares_diluted
    per_share = (equity / shares) if (shares and shares > 0) else None
    # `g_term` is the EFFECTIVE terminal growth actually used, which may be below the
    # assumption when the spread clamp binds; `tv_multiple` is the implied terminal
    # multiple (TV per unit of terminal FCFF) — the number this whole defect is about.
    tv_multiple = (tv / fcff_term) if fcff_term > 0 else None
    return (per_share, ev, pv_explicit, pv_tv, tv, equity, net_debt, shares, rows,
            g_term, tv_multiple)


def intrinsic_per_share(cd: CompanyData, a: AssumptionSet, wacc: float,
                        troic: Optional[float] = None) -> Optional[float]:
    """Fast path used by Monte Carlo / reverse DCF (no row collection)."""
    troic = troic if troic is not None else _terminal_roic(cd, wacc)
    ps, *_ = _project(cd, a, wacc, troic, collect_rows=False)
    return ps


def run_dcf(cd: CompanyData, a: AssumptionSet, wacc: float,
            troic: Optional[float] = None) -> DCFResult:
    troic = troic if troic is not None else _terminal_roic(cd, wacc)
    (per_share, ev, pv_explicit, pv_tv, tv, equity, net_debt, shares, rows,
     g_eff, tv_multiple) = _project(cd, a, wacc, troic, collect_rows=True)
    return DCFResult(
        per_share=per_share, equity_value=equity, enterprise_value=ev,
        pv_explicit=pv_explicit, pv_terminal=pv_tv, terminal_value=tv,
        tv_pct_of_ev=(pv_tv / ev if ev else 0.0), wacc=wacc, terminal_growth=g_eff,
        terminal_roic=troic, net_debt=net_debt, shares=shares, label=a.label, rows=rows,
        terminal_multiple=tv_multiple, assumed_terminal_growth=a.terminal_growth,
        reinvestment_y1=(-rows[0]["reinvestment"] if rows else None),
        observed_net_capex=((cd.capex - cd.da)
                            if (cd.capex is not None and cd.da is not None) else None),
    )
