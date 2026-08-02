"""
Lightweight peer-relative fair value for the hot list.

The full DCF is network-heavy (seconds per name), so only the top handful of picks get
one — every other row used to show "—" in the Fair value column. This fills those in
without another fetch, using two lenses and blending them by how MATURE the company is:

  * mature lens — what the stock would be worth if it re-rated to what its sector peers
    actually trade at, on whichever of earnings yield / FCF yield / EV-Sales / EV-EBITDA
    it has. Right for a profitable company; useless for one with no profit.
  * growth lens — where revenue is going, valued at a mature exit multiple and discounted
    back (valuation.engine.growth, the same module the deep valuation page uses). Right
    for a pre-profit grower; degenerates smoothly into a plain sales multiple as a
    company matures, so there is no cliff between the two.

The blend weight is `maturity` (operating margin, cash generation, revenue growth, size),
so a profitable mega-cap is ~all mature lens and a loss-making hypergrowth name is ~all
growth lens, with everything in between getting a mix.

WHAT CHANGED AND WHY (2026-08): this module used to be equity-yield-only, and said so:

    "Deliberately NOT used: ev_ebitda / ev_sales. Those are enterprise multiples, and
     turning one into a per-share equity value needs net debt, which the scan doesn't
     carry per row."

The scan now carries `net_debt` per row (providers.company_to_metrics -> screen._rows_from),
so the bridge is available and those multiples are used:

    implied EV     = current EV x (peer multiple / own multiple)
    implied equity = implied EV - net debt
    implied price  = price x implied equity / market cap

That matters most for exactly the names the old version couldn't touch at all: a
loss-making company has a negative earnings yield and a negative FCF yield, so BOTH of
the old inputs were dropped and it got no fair value (or, on the deep page, a mature
sector multiple that produced numbers like Rocket Lab's $2.63 against a $65 price).

This is still a cross-check, not a valuation. Callers should label it an estimate, and
`fair_value_confidence` is "low" whenever the growth lens is carrying the answer —
growth valuation is a range, not a point.
"""
from __future__ import annotations

import math
from statistics import median

from ..engine.assumptions import SECTOR_TARGET_MARGIN
from ..engine.comps import SECTOR_MULTIPLES, _DEFAULT as _DEFAULT_MULTIPLES
from ..engine.growth import (compound_growth, cumulative_discount, exit_sales_multiple,
                             fade_path, maturity_score, operating_loss_pv, years_to_maturity)

# Equity yields: higher = cheaper, and they map straight to a per-share value.
YIELD_KEYS = ("earnings_yield", "fcf_yield")
# Enterprise multiples: lower = cheaper, and they need the net-debt bridge above.
EV_MULTIPLE_KEYS = ("ev_sales", "ev_ebitda")

MIN_PEERS = 5          # below this a sector median is noise; fall back to the whole universe
MAX_RERATE = 3.0       # cap the implied move at 3x up / 1/3 down

# Growth-lens assumptions. The screener has no per-name WACC (that needs a beta and a
# capital structure the scan doesn't fetch), so it uses one growth-name cost of capital
# fading to a mature one. The deep valuation page uses the company's real WACC instead —
# these numbers are for ranking a list, not for a final valuation.
GROWTH_DISCOUNT_NOW = 0.13
GROWTH_DISCOUNT_MATURE = 0.09
GROWTH_HORIZON_YEARS = 10        # full horizon for a zero-maturity name
GROWTH_TERMINAL = 0.03           # growth fades to roughly nominal GDP
GROWTH_START_CAP = 0.60          # nobody compounds faster than this in a forecast
MAX_GROWTH_VALUE = 20.0          # sanity: never publish >20x the current price


def _num(v):
    """A usable finite float, else None."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if (v != v or v in (float("inf"), float("-inf"))) else v


def _pos_yield(row, key):
    """A usable, positive yield for `key`, else None.

    Negative or zero yields are dropped on purpose: a loss-making company has a negative
    earnings yield, and 'price * (negative / positive)' would hand back a negative fair
    value that looks authoritative and is meaningless.
    """
    v = _num((row.get("extra") or {}).get(key))
    return v if (v is not None and v > 0) else None


def _price(row):
    p = _num(row.get("price"))
    return p if (p is not None and p > 0) else None


def _mcap(row):
    mc = _num(row.get("market_cap"))
    if mc is None:
        mc = _num((row.get("extra") or {}).get("market_cap"))
    return mc if (mc is not None and mc > 0) else None


def peer_medians(rows) -> dict:
    """Median usable multiple per (sector, key), plus a (None, key) universe fallback.

    Sectors with fewer than MIN_PEERS usable names are omitted so callers fall back to the
    universe median rather than anchoring on one or two comparables. Both families are
    collected here: equity yields (higher = cheaper) and EV multiples (lower = cheaper).
    """
    buckets: dict = {}
    for r in rows:
        sector = (r.get("sector") or "").strip() or None
        for key in YIELD_KEYS + EV_MULTIPLE_KEYS:
            y = _pos_yield(r, key)
            if y is None:
                continue
            buckets.setdefault((sector, key), []).append(y)
            buckets.setdefault((None, key), []).append(y)

    out = {}
    for (sector, key), vals in buckets.items():
        if sector is not None and len(vals) < MIN_PEERS:
            continue                      # too thin to trust — universe median will be used
        out[(sector, key)] = median(vals)
    return out


def _peer(meds, sector, key):
    p = meds.get((sector, key))
    if p is None:
        p = meds.get((None, key))
    return p if (p and p > 0) else None


def _mature_value(row, meds, price):
    """Peer re-rating on whichever multiples this name has. None if it has none.

    Equity yields map straight to price. EV multiples go through the net-debt bridge,
    which is why they were unusable here before the scan started carrying net debt.
    """
    sector = (row.get("sector") or "").strip() or None
    extra = row.get("extra") or {}
    implied = []

    for key in YIELD_KEYS:
        own = _pos_yield(row, key)
        peer = _peer(meds, sector, key)
        if own is None or peer is None:
            continue
        ratio = max(1.0 / MAX_RERATE, min(MAX_RERATE, own / peer))
        implied.append(price * ratio)

    mc, nd = _mcap(row), _num(extra.get("net_debt"))
    if mc is not None and nd is not None:
        ev = mc + nd
        for key in EV_MULTIPLE_KEYS:
            own = _pos_yield(row, key)          # a multiple, so LOWER is cheaper
            peer = _peer(meds, sector, key)
            if own is None or peer is None or ev <= 0:
                continue
            ratio = max(1.0 / MAX_RERATE, min(MAX_RERATE, peer / own))
            equity = ev * ratio - nd
            if equity > 0:
                implied.append(price * equity / mc)

    return median(implied) if implied else None


def _growth_value(row, price):
    """Value the row on where its REVENUE is going, not on profit it doesn't have.

    Returns (value, maturity) — value is None when the inputs aren't there. Uses the
    same engine.growth math as the deep valuation page: compound revenue over a horizon
    that shrinks as the company matures, exit at a mature sales multiple, discount back
    on a fading rate, charge the operating losses funded on the way, bridge EV -> equity
    with net debt.
    """
    extra = row.get("extra") or {}
    rev = _num(extra.get("revenue"))
    mc = _mcap(row)
    g = _num(extra.get("revenue_growth"))
    om = _num(extra.get("op_margin"))
    nd = _num(extra.get("net_debt"))

    fcf_margin = None
    fcfy = _num(extra.get("fcf_yield"))
    if fcfy is not None and mc and rev:
        fcf_margin = fcfy * mc / rev
    maturity, _parts = maturity_score(op_margin=om, fcf_margin=fcf_margin,
                                      growth=g, market_cap=mc)

    if rev is None or rev <= 0 or mc is None or nd is None or g is None:
        return None, maturity

    sector = (row.get("sector") or "").strip()
    bench = SECTOR_MULTIPLES.get(sector, _DEFAULT_MULTIPLES)
    target_margin = SECTOR_TARGET_MARGIN.get(sector, 0.12)
    gm = _num(extra.get("gross_margin"))
    if gm and gm > 0:
        target_margin = min(target_margin, gm * 0.85)     # can't out-earn the gross margin
    mult = exit_sales_multiple(bench, target_margin)
    if mult is None:
        return None, maturity

    horizon = years_to_maturity(GROWTH_HORIZON_YEARS, maturity)
    if horizon <= 0:
        return None, maturity
    g0 = max(-0.15, min(GROWTH_START_CAP, g))
    n = max(1, int(math.ceil(horizon)))
    path = fade_path(g0, GROWTH_TERMINAL, n, plateau=(2 if g0 >= 0.25 else 0))
    margins = [om + (target_margin - om) * (t / n) for t in range(1, n + 1)] if om is not None else []

    gap = operating_loss_pv(rev, path, margins, horizon,
                            GROWTH_DISCOUNT_NOW, GROWTH_DISCOUNT_MATURE) if margins else 0.0
    ev_now = (rev * compound_growth(path, horizon) * mult
              / cumulative_discount(GROWTH_DISCOUNT_NOW, GROWTH_DISCOUNT_MATURE, horizon))
    equity = ev_now - nd - gap
    if equity <= 0:
        return None, maturity
    value = price * equity / mc
    if value > price * MAX_GROWTH_VALUE:
        return None, maturity                  # implausible; say nothing rather than shout
    return value, maturity


def estimate_fair_values(rows, peer_rows=None) -> int:
    """Fill in `fair_value` / `upside` for rows that don't have a DCF. Mutates `rows`.

    `peer_rows` is the population the medians are computed from — pass the FULL scan when
    `rows` is only the displayed top slice, so the peer group doesn't shrink to whatever
    happens to be on screen. Returns the number of rows estimated.

    Rows that already carry a DCF fair value are left untouched and tagged
    `fair_value_method = "dcf"`; estimated rows are tagged "multiples", "growth" or
    "blended" for which lens carried them, with `fair_value_confidence` marking the
    growth-led ones low.
    """
    meds = peer_medians(peer_rows if peer_rows is not None else rows)
    n = 0
    for r in rows:
        if r.get("fair_value") is not None:
            r.setdefault("fair_value_method", "dcf")
            continue
        price = _price(r)
        if price is None:
            continue

        mature = _mature_value(r, meds, price)
        growth, maturity = _growth_value(r, price)

        lenses = {}
        if mature is not None:
            lenses["multiples"] = (mature, maturity)
        if growth is not None:
            lenses["growth"] = (growth, 1.0 - maturity)
        lenses = {k: v for k, v in lenses.items() if v[1] > 1e-9}
        if not lenses:
            continue

        total = sum(w for _, w in lenses.values())
        fv = sum(v * w for v, w in lenses.values()) / total
        w_growth = lenses.get("growth", (0.0, 0.0))[1] / total

        r["fair_value"] = fv
        r["upside"] = fv / price - 1.0
        r["fair_value_method"] = ("blended" if len(lenses) > 1 else
                                  ("growth" if "growth" in lenses else "multiples"))
        r["fair_value_confidence"] = "low" if w_growth >= 0.5 else "medium"
        n += 1
    return n
