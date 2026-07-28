"""
Lightweight peer-relative fair value for the hot list.

The full DCF is network-heavy (seconds per name), so only the top handful of picks get
one — every other row used to show "—" in the Fair value column. This fills those in with
a multiples-based estimate: what the stock would be worth if it re-rated to what its
sector peers actually trade at.

Both inputs are EQUITY yields (measured against market cap), so the mapping to a
per-share value is direct — no enterprise-value-to-equity bridge, and no net-debt guess:

    earnings_yield = net income     / market cap
    fcf_yield      = free cash flow / market cap
    implied value  = price * (own yield / peer median yield)

A name yielding twice its peers' median is worth ~2x its price on that multiple. We take
the MEDIAN across whichever yields are present so a single broken input can't run away
with the estimate, and clamp the re-rating so a near-zero peer median can't produce a
nonsense number.

Deliberately NOT used: ev_ebitda / ev_sales. Those are enterprise multiples, and turning
one into a per-share equity value needs net debt, which the scan doesn't carry per row —
applying them directly would quietly misprice every leveraged name.

This is a cross-check, not a valuation. It says "cheap relative to peers", which is a
weaker and different claim than the DCF's "worth this much". Callers should label it as
an estimate so the two are never confused.
"""
from __future__ import annotations

from statistics import median

# Equity yields only — see the module docstring for why EV multiples are excluded.
YIELD_KEYS = ("earnings_yield", "fcf_yield")

MIN_PEERS = 5          # below this a sector median is noise; fall back to the whole universe
MAX_RERATE = 3.0       # cap the implied move at 3x up / 1/3 down


def _pos_yield(row, key):
    """A usable, positive yield for `key`, else None.

    Negative or zero yields are dropped on purpose: a loss-making company has a negative
    earnings yield, and 'price * (negative / positive)' would hand back a negative fair
    value that looks authoritative and is meaningless.
    """
    v = (row.get("extra") or {}).get(key)
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    if v != v or v <= 0:          # NaN or non-positive
        return None
    return v


def _price(row):
    try:
        p = float(row.get("price"))
    except (TypeError, ValueError):
        return None
    return p if (p == p and p > 0) else None


def peer_medians(rows) -> dict:
    """Median positive yield per (sector, key), plus a (None, key) whole-universe fallback.

    Sectors with fewer than MIN_PEERS usable names are omitted so callers fall back to the
    universe median rather than anchoring on one or two comparables.
    """
    buckets: dict = {}
    for r in rows:
        sector = (r.get("sector") or "").strip() or None
        for key in YIELD_KEYS:
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


def estimate_fair_values(rows, peer_rows=None) -> int:
    """Fill in `fair_value` / `upside` for rows that don't have a DCF. Mutates `rows`.

    `peer_rows` is the population the medians are computed from — pass the FULL scan when
    `rows` is only the displayed top slice, so the peer group doesn't shrink to whatever
    happens to be on screen. Returns the number of rows estimated.

    Rows that already carry a DCF fair value are left untouched and tagged
    `fair_value_method = "dcf"`; estimated rows are tagged "multiples" so the UI can show
    which is which.
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
        sector = (r.get("sector") or "").strip() or None
        implied = []
        for key in YIELD_KEYS:
            own = _pos_yield(r, key)
            if own is None:
                continue
            peer = meds.get((sector, key))
            if peer is None:
                peer = meds.get((None, key))
            if not peer or peer <= 0:
                continue
            ratio = own / peer
            ratio = max(1.0 / MAX_RERATE, min(MAX_RERATE, ratio))
            implied.append(price * ratio)
        if not implied:
            continue
        fv = median(implied)
        r["fair_value"] = fv
        r["upside"] = fv / price - 1.0
        r["fair_value_method"] = "multiples"
        n += 1
    return n
