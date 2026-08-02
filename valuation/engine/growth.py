"""
Growth / pre-profit valuation — value a company on where its REVENUE is going.

Why this exists
---------------
The DCF and the comps table both need something a pre-profit company hasn't got.
The DCF needs positive free cash flow; the comps table, as it was, priced every
name off *sector-typical* multiples. Rocket Lab (RKLB) is the worked example: an
Industrials benchmark of 2.0x EV/Sales applied to a company growing ~40-140%/yr
and trading at 66x sales produced a "fair value" of $2.63 against a $65 price.
That number was not a bearish view — it was a mature-company multiple pointed at
a company that isn't mature, and it was published to 2 decimal places.

What this module does instead
-----------------------------
Value the business at the point it MATURES, then discount that back:

    revenue at horizon = revenue_today x (the same faded growth path the DCF uses)
    value at horizon   = revenue at horizon x a MATURE exit multiple on sales
    value today        = value at horizon / (the faded discount path)
    equity             = that, minus the operating losses it must fund on the way,
                         minus net debt (so net cash is added back)

Two of those deserve their own note, because they are what stop this from being a
license to print a big number:

  * The discount rate FADES from today's WACC to a mature one (risk-free + one ERP).
    Discounting nine years at a 17.5% pre-profit WACC while applying an exit multiple
    that was observed on companies with a ~9% WACC is internally inconsistent, and it
    is inconsistent in the direction that crushes every growth name to nearly zero.
  * The PV of the OPERATING losses between here and maturity is charged. Cash raised
    to cover losses is dilution that no exit multiple compensates you for. Growth
    CAPEX is deliberately NOT charged here — the exit multiple is the value of the
    business that capital builds, and the DCF lens already charges it in full. The two
    lenses bracket the answer, which is exactly why the blend shows both.

The exit multiple is built from the company's own sustainable operating margin
(assumptions._target_margin, already capped at ~85% of gross margin) applied to
a mature EV/EBIT multiple, averaged with the sector EV/Sales benchmark — and it
uses the PEER median instead of the sector benchmark whenever real peers were
supplied. So the sales multiple this implies TODAY is explicitly scaled to the
growth rate: RKLB's ~17x revenue growth over the horizon turns a mature ~1.9x
sales into a justified ~6x sales today, versus the 66x it actually trades at.

The horizon is not a constant: it is `n_years x (1 - maturity)`, so as a company
matures the horizon shrinks toward zero and this lens degenerates smoothly into
a plain sales multiple. Blended by the same maturity score (see blend.py), the
whole thing is a gradient, not a switch.

What it deliberately does NOT model
-----------------------------------
Interim cash flows and the dilution needed to fund them. A company that burns
cash for eight years to reach that revenue will issue stock to do it, and the
per-share number here does not charge for that. This is the standard "exit
multiple" / venture method and it is a RANGE, not a point estimate — which is
why callers mark growth-led valuations low-confidence and lead with the
reverse-DCF implied-growth read instead of a two-decimal figure.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

# Maturity-score weights. Profitability (margin + cash) carries most of it, the
# growth rate is the next strongest tell, size is a mild nudge — a $40B company
# is more "arrived" than a $400M one even when both are losing money.
MATURITY_WEIGHTS = {"margin": 0.35, "cash": 0.25, "growth": 0.25, "size": 0.15}

GROWTH_NEUTRAL = 0.15          # revenue growth at which the growth term is 50/50
SIZE_NEUTRAL_LOG10 = 3.7       # $5bn market cap (values are in $ millions)
SIZE_SPREAD = 0.6              # ~1 decade of market cap per 2 sigma

MULTIPLE_FLOOR, MULTIPLE_CAP = 0.3, 20.0     # sanity bounds on an exit EV/Sales
MIN_HORIZON, MAX_HORIZON = 0.0, 15.0
MATURE_WACC_BOUNDS = (0.05, 0.15)            # what a grown-up version of this firm discounts at

# Scenario shifts applied to the EXIT MULTIPLE (on top of the growth/margin
# shifts the DCF scenarios already use). Multiple compression is the dominant
# risk in a growth name, so the scenario cone has to include it.
SCENARIO_MULTIPLE = {"bear": 0.80, "base": 1.00, "bull": 1.25}


def _sig(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, x))))


def _f(x) -> Optional[float]:
    """Finite float or None."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if v != v or v in (float("inf"), float("-inf")):
        return None
    return v


def maturity_score(op_margin=None, fcf_margin=None, growth=None, market_cap=None):
    """Continuous 0..1 "how mature is this company", from the four tells the
    valuation actually turns on: operating margin, cash generation, revenue
    growth and size.

    1.0 = a large, profitable, slow-growing business (value it on cash flow).
    0.0 = a small, loss-making, fast-growing one (value it on revenue).

    Returns (score, components). Missing inputs are dropped and the remaining
    weights renormalized, so a name with only a margin still gets a sane score;
    a name with nothing at all gets 0.5 (genuinely undecided), same as before.
    """
    comps, weights = {}, {}
    om, fm = _f(op_margin), _f(fcf_margin)
    g, mc = _f(growth), _f(market_cap)

    if om is not None:
        comps["margin"] = _sig(om / 0.05)
    if fm is not None:
        comps["cash"] = _sig(fm / 0.05)
    if g is not None:
        comps["growth"] = _sig((GROWTH_NEUTRAL - g) / 0.10)
    if mc is not None and mc > 0:
        comps["size"] = _sig((math.log10(mc) - SIZE_NEUTRAL_LOG10) / SIZE_SPREAD)

    for k in comps:
        weights[k] = MATURITY_WEIGHTS[k]
    tot = sum(weights.values())
    if not tot:
        return 0.5, comps
    score = sum(comps[k] * weights[k] for k in comps) / tot
    return max(0.0, min(1.0, score)), comps


def maturity_from_company(cd, growth=None):
    """maturity_score() for a CompanyData (the deep-valuation path)."""
    g = growth
    if g is None:
        g = getattr(cd, "rev_growth_ttm", None)
        if g is None:
            g = getattr(cd, "rev_cagr_3y", None)
    return maturity_score(op_margin=getattr(cd, "ebit_margin", None),
                          fcf_margin=getattr(cd, "fcf_margin", None),
                          growth=g, market_cap=getattr(cd, "market_cap", None))


def years_to_maturity(n_years: float, maturity: float) -> float:
    """How long until this company is worth a mature multiple.

    A deep-growth name gets the full forecast horizon; an already-mature one
    gets ~0 years, at which point the lens is just today's sales multiple. That
    continuity is what stops the blend from jumping when a company crosses some
    profitability threshold.
    """
    n = _f(n_years) or 5.0
    m = _f(maturity)
    m = 0.5 if m is None else max(0.0, min(1.0, m))
    return max(MIN_HORIZON, min(MAX_HORIZON, n * (1.0 - m)))


def fade_path(g0: float, g_term: float, n: int, plateau: int = 0) -> list:
    """Growth held for `plateau` years then faded linearly to `g_term` by year n.
    Same shape as assumptions._fade_path, duplicated here so the screener (which
    has no AssumptionSet) can build a path from a single growth number."""
    n = max(1, int(n))
    plateau = max(0, min(int(plateau), n - 1))
    path = []
    for t in range(1, n + 1):
        if t <= plateau:
            path.append(g0)
        else:
            path.append(g0 + (g_term - g0) * ((t - plateau) / (n - plateau)))
    return path


def compound_growth(path, years: float) -> float:
    """Cumulative revenue multiple over `years` (fractional allowed) of `path`.

    Past the end of the path the last (terminal) rate repeats, so a horizon
    longer than the explicit forecast doesn't silently stop compounding.
    """
    years = _f(years) or 0.0
    if years <= 0 or not path:
        return 1.0
    c, remaining, i = 1.0, years, 0
    while remaining > 1e-9:
        g = path[i] if i < len(path) else path[-1]
        step = min(1.0, remaining)
        c *= (1.0 + max(-0.95, g)) ** step
        remaining -= step
        i += 1
    return c


def mature_discount_rate(risk_free=None, erp=None, wacc=None) -> float:
    """What a matured version of this company should be discounted at: the risk-free
    rate plus one equity risk premium (i.e. beta ~1, lightly levered). Never above
    today's WACC — maturing shouldn't make a company riskier."""
    rf, e = _f(risk_free), _f(erp)
    r = (rf + e) if (rf is not None and e is not None) else 0.09
    r = max(MATURE_WACC_BOUNDS[0], min(MATURE_WACC_BOUNDS[1], r))
    w = _f(wacc)
    return min(r, w) if w is not None else r


def cumulative_discount(r_now: float, r_mature: float, years: float) -> float:
    """Divisor for a cash flow `years` out, with the rate fading r_now -> r_mature.

    Year 1 discounts at (close to) today's rate; the last year discounts at the
    mature rate. Returns 1.0 for a zero horizon.
    """
    years = max(0.0, _f(years) or 0.0)
    if years <= 0:
        return 1.0
    a = _f(r_now)
    b = _f(r_mature)
    a = 0.09 if a is None else max(0.0, min(0.40, a))
    b = a if b is None else max(0.0, min(0.40, b))
    f, remaining, t = 1.0, years, 0
    while remaining > 1e-9:
        step = min(1.0, remaining)
        frac = min(1.0, (t + step) / years)          # 0 -> today's rate, 1 -> mature
        r = a + (b - a) * frac
        f *= (1.0 + r) ** step
        remaining -= step
        t += 1
    return f


def operating_loss_pv(base_revenue, growth_path, margin_path, horizon,
                      r_now, r_mature) -> float:
    """PV of the operating losses the company must fund before it matures.

    Only LOSS years count, and only the part of them inside the horizon. This is the
    cash a pre-profit company has to raise from someone — dilution the exit multiple
    does not pay you back for. Profitable years are not credited (that surplus is
    already inside the exit value), so the charge is one-sided by design.
    """
    rev = _f(base_revenue)
    if rev is None or rev <= 0 or not growth_path or not margin_path:
        return 0.0
    h = max(0.0, _f(horizon) or 0.0)
    if h <= 0:
        return 0.0
    total, r = 0.0, rev
    for t in range(1, int(math.ceil(h)) + 1):
        g = growth_path[t - 1] if t <= len(growth_path) else growth_path[-1]
        m = margin_path[t - 1] if t <= len(margin_path) else margin_path[-1]
        r = r * (1.0 + max(-0.95, g))
        ebit = r * m
        if ebit >= 0:
            continue
        weight = min(1.0, h - (t - 1))                # partial final year
        total += (-ebit) * weight / cumulative_discount(r_now, r_mature, t)
    return total


def fundamental_sales_multiple(target_margin, mature_rate=0.09, terminal_growth=0.03,
                               tax_rate=0.21, roic=None) -> Optional[float]:
    """What a MATURE business earning `target_margin` is worth, per $1 of sales.

        EV/Sales = margin x (1 - tax) x (1 - g/ROIC) / (r - g)

    i.e. a Gordon-growth value on the NOPAT that margin produces, with growth paid
    for out of reinvestment. This is the anchor the peer multiples get checked
    against, because a sector's CURRENT EV/Sales embeds the growth the sector is
    expected to deliver — using it as an EXIT multiple, after already compounding
    revenue to the horizon, counts that growth twice.
    """
    tm = _f(target_margin)
    if tm is None or tm <= 0:
        return None
    r = max(0.05, min(0.20, _f(mature_rate) or 0.09))
    g = max(0.0, min(r - 0.01, _f(terminal_growth) or 0.03))
    tax = max(0.0, min(0.45, _f(tax_rate) if tax_rate is not None else 0.21))
    ri = _f(roic)
    ri = (r + 0.03) if (ri is None or ri <= g) else max(ri, g + 0.005)
    reinvest = min(0.9, g / ri) if ri > 0 else 0.0
    return max(MULTIPLE_FLOOR, min(MULTIPLE_CAP,
                                   tm * (1.0 - tax) * (1.0 - reinvest) / (r - g)))


def exit_sales_multiple(bench: dict, target_margin=None, mature_rate=0.09,
                        terminal_growth=0.03, tax_rate=0.21, roic=None) -> Optional[float]:
    """The EV/Sales a MATURE version of this business should command.

    Three reads. The fundamental one above is the anchor; the sector/peer EV/Sales
    benchmark and the sector/peer EV/EBIT(DA) benchmark applied to this company's own
    sustainable margin are the market check — that pair is what makes the answer
    reflect real comparables, but it is capped at 2x the fundamental so a sector
    trading on froth can't be laundered into an exit assumption.
    """
    bench = bench or {}
    fundamental = fundamental_sales_multiple(target_margin, mature_rate,
                                             terminal_growth, tax_rate, roic)
    peers = []
    evs = _f(bench.get("ev_sales"))
    if evs and evs > 0:
        peers.append(evs)
    eve, tm = _f(bench.get("ev_ebitda")), _f(target_margin)
    if eve and eve > 0 and tm and tm > 0:
        peers.append(eve * tm)
    if not peers:
        ps = _f(bench.get("ps"))
        if ps and ps > 0:
            peers.append(ps)

    peer = (sum(peers) / len(peers)) if peers else None
    if peer is None and fundamental is None:
        return None
    if fundamental is None:
        out = peer
    elif peer is None:
        out = fundamental
    else:
        out = 0.5 * fundamental + 0.5 * min(peer, 2.0 * fundamental)
    return max(MULTIPLE_FLOOR, min(MULTIPLE_CAP, out))


@dataclass
class GrowthValue:
    """A revenue-multiple valuation, with every input it used exposed."""
    value: Optional[float] = None            # per-share equity value (None = N/A)
    equity_value: Optional[float] = None     # $mm
    enterprise_value: Optional[float] = None  # $mm, today
    revenue_at_horizon: Optional[float] = None
    horizon_years: Optional[float] = None
    exit_multiple: Optional[float] = None    # EV/Sales at maturity
    implied_ev_sales_now: Optional[float] = None   # what that means TODAY
    current_ev_sales: Optional[float] = None       # what it actually trades at
    funding_gap_pv: Optional[float] = None   # PV of operating losses charged, $mm
    discount_rate: Optional[float] = None    # today's WACC (start of the fade)
    mature_discount_rate: Optional[float] = None   # end of the fade
    applies: bool = False
    reason: str = ""
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def growth_equity_value(revenue, growth_path, horizon_years, exit_multiple,
                        discount_rate, net_debt=0.0, mature_rate=None,
                        funding_gap=0.0):
    """The core arithmetic, in $mm. Returns (equity, ev_now, revenue_at_horizon).

    Kept free of CompanyData so the screener can call it with plain numbers.
    """
    rev = _f(revenue)
    mult = _f(exit_multiple)
    r = _f(discount_rate)
    if rev is None or rev <= 0 or not mult or mult <= 0 or r is None:
        return None, None, None
    r = max(0.02, min(0.40, r))
    rm = mature_discount_rate(wacc=r) if mature_rate is None else max(0.02, min(0.40, float(mature_rate)))
    h = max(0.0, _f(horizon_years) or 0.0)
    rev_h = rev * compound_growth(growth_path, h)
    ev_now = rev_h * mult / cumulative_discount(r, rm, h)
    nd = _f(net_debt) or 0.0
    return ev_now - nd - (_f(funding_gap) or 0.0), ev_now, rev_h


def growth_fair_value(cd, assumptions, wacc, maturity, bench,
                      multiple_mult: float = 1.0, mature_rate=None) -> GrowthValue:
    """Per-share growth valuation for the deep-valuation path.

    Uses the assumption set's own faded growth path, margin path and sustainable
    margin, and the company's own WACC, so this lens and the DCF disagree about the
    ANSWER but never about the inputs.
    """
    out = GrowthValue()
    rev = _f(getattr(cd, "revenue", None))
    shares = _f(getattr(cd, "shares_diluted", None))
    if rev is None or rev <= 0:
        out.reason = "No revenue to value on a sales multiple."
        return out
    if not shares or shares <= 0:
        out.reason = "No diluted share count — can't turn an equity value into a per-share one."
        return out

    rm = mature_discount_rate(wacc=wacc) if mature_rate is None else mature_rate
    mult = exit_sales_multiple(bench, getattr(assumptions, "target_margin", None),
                               mature_rate=rm,
                               terminal_growth=getattr(assumptions, "terminal_growth", 0.03),
                               tax_rate=getattr(assumptions, "tax_rate", 0.21),
                               roic=getattr(cd, "roic", None))
    if mult is None:
        out.reason = "No usable peer/sector multiple to exit on."
        return out
    mult *= max(0.1, float(multiple_mult or 1.0))

    horizon = years_to_maturity(getattr(assumptions, "n_years", 5), maturity)
    path = list(getattr(assumptions, "rev_growth_path", None) or [])
    margins = list(getattr(assumptions, "op_margin_path", None) or [])
    nd = _f(getattr(cd, "net_debt", None)) or 0.0
    gap = operating_loss_pv(rev, path, margins, horizon, wacc, rm)

    equity, ev_now, rev_h = growth_equity_value(
        rev, path, horizon, mult, wacc, net_debt=nd, mature_rate=rm, funding_gap=gap)
    if equity is None:
        out.reason = "Growth valuation inputs incomplete."
        return out

    out.horizon_years = round(horizon, 2)
    out.exit_multiple = round(mult, 3)
    out.revenue_at_horizon = rev_h
    out.enterprise_value = ev_now
    out.equity_value = equity
    out.funding_gap_pv = gap
    out.implied_ev_sales_now = round(ev_now / rev, 2) if rev else None
    out.discount_rate = wacc
    out.mature_discount_rate = rm
    mc = _f(getattr(cd, "market_cap", None))
    if mc:
        out.current_ev_sales = round((mc + nd) / rev, 2)
    if equity <= 0:
        out.reason = ("What the business is worth on a growth-adjusted sales multiple doesn't "
                      "cover the losses it must fund and the debt it already carries.")
        return out

    out.value = equity / shares
    out.applies = True
    out.notes.append(
        f"Growth valuation: revenue compounds to ~${rev_h:,.0f}mm over ~{horizon:.1f} years, "
        f"exits at {mult:.1f}x sales, discounted back at a rate fading {wacc:.1%} -> {rm:.1%} "
        f"— a justified {out.implied_ev_sales_now:.1f}x sales TODAY"
        + (f" versus the {out.current_ev_sales:.1f}x it trades at." if out.current_ev_sales else "."))
    if gap > 0:
        out.notes.append(
            f"Charged ${gap:,.0f}mm (PV) for the operating losses funded before it gets there — "
            f"that cash has to be raised, and an exit multiple doesn't pay you back for it.")
    out.notes.append(
        "Growth CAPEX is NOT charged in this lens (the exit multiple is the value of what that "
        "capital builds); the DCF lens charges it in full. The two bracket the answer.")
    return out


def build_growth_scenarios(cd, cls, base_assumptions, wacc, maturity, bench,
                           mature_rate=None) -> dict:
    """bear / base / bull growth valuations, shifted the same way the DCF's are
    (growth + margin) PLUS exit-multiple compression/expansion, which is the risk
    a growth name actually carries."""
    from .assumptions import shift_assumptions
    from .scenarios import _DELTAS

    dg, dm, dt, _stc = _DELTAS.get(getattr(cls, "regime", "mature"), _DELTAS["mature"])
    out = {}
    for name, gd, md in (("bear", -dg, -dm), ("base", 0.0, 0.0), ("bull", +dg, +dm)):
        a = base_assumptions if name == "base" else shift_assumptions(
            base_assumptions, gd, md, 0.0, label=name)
        out[name] = growth_fair_value(cd, a, wacc, maturity, bench,
                                      multiple_mult=SCENARIO_MULTIPLE[name],
                                      mature_rate=mature_rate)
    return out
