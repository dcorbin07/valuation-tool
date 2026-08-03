"""
What the landing page shows on arrival — a real, cached sample valuation and the live track.

WHY IT IS CACHED AND NOT COMPUTED PER VISIT. A full valuation is a network-heavy, multi-second
job (`engine.pipeline.value_ticker`: filings, prices, comps, Monte Carlo). Running it inside
the request that renders the landing page would mean every first-time visitor waits several
seconds on a 512 MB box that also has to serve everyone else — the exact opposite of the goal,
which is to demonstrate the product in about two seconds. So the valuation is computed OUT of
band (the CI scan already has real RAM and a real network) and posted to the store; the
landing route only reads it.

A cached sample is also the honest thing to show: it is a real run of the real engine on real
filings, stamped with the date it was computed. It is not a hand-written mock-up, and the
template always renders that date so nobody reads a week-old sample as a live quote.

DEGRADES, NEVER BREAKS. If no sample has been ingested yet, `landing_context` returns
`sample=None` and the template falls back to the static value-props. A landing page that
renders a broken widget is worse than one that renders less, and this is the first thing a
visitor ever sees.
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional

SAMPLE_KEY = "landing_sample"
DEFAULT_TICKER = "AAPL"
# Past this the sample is labelled rather than hidden: an old sample is still a real valuation,
# and saying "as of the 3rd" is more honest than silently dropping the only proof on the page.
STALE_AFTER_DAYS = 7


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and v not in (float("inf"), float("-inf")) else None


def build(ticker: str = DEFAULT_TICKER, cfg=None) -> dict:
    """Run the real valuation and reduce it to the handful of numbers the landing shows.

    Deliberately narrow: the landing needs the headline, the range and the reverse-DCF read,
    not the whole 200-key payload. Called from CI, never from a web request.
    """
    from ..config import CONFIG
    from ..engine.pipeline import value_ticker

    res = value_ticker(ticker, cfg or CONFIG)
    d = res.to_dict()
    company = d.get("company") or {}
    scen = d.get("fair_value_scenarios") or {}
    score = d.get("score") or {}
    reverse = d.get("reverse") or {}

    return {
        "ticker": ticker.upper(),
        "name": company.get("name") or ticker.upper(),
        "sector": company.get("sector") or "",
        "price": _f(company.get("price")),
        "fair_value": _f(d.get("base_fair_value")),
        "upside": _f(d.get("upside")),
        # The 1-100 opportunity score and its verdict, exactly as the app shows them.
        "score": _f(score.get("score")),
        "verdict": score.get("recommendation") or "",
        "confidence": score.get("confidence") or "",
        "bear": _f(scen.get("bear")),
        "base": _f(scen.get("base")),
        "bull": _f(scen.get("bull")),
        # Reverse DCF: the growth rate today's price already implies. The most persuasive
        # number the engine produces, because it reframes "is it cheap?" as "do you believe
        # this?". `bounded` is carried so the template can say "at least ~X%" rather than
        # quoting a solver bound as if it were an estimate.
        "implied_growth": _f(reverse.get("implied_start_growth")),
        "implied_growth_bounded": reverse.get("implied_growth_bounded") or "",
        "base_growth": _f(reverse.get("base_start_growth")),
        "as_of": _dt.date.today().isoformat(),
    }


def save(store, payload: dict) -> None:
    store.set_meta(SAMPLE_KEY, payload)


# The template formats these with "%.2f", which raises on None — and that would happen INSIDE
# render_template, outside the landing route's try/except, i.e. it would 500 the home page
# rather than degrade. So a sample missing any of them is treated as no sample at all.
_REQUIRED = ("ticker", "price", "fair_value")


def load(store) -> Optional[dict]:
    try:
        s = store.get_meta(SAMPLE_KEY)
    except Exception:
        return None
    if not isinstance(s, dict):
        return None
    return s if all(s.get(k) is not None for k in _REQUIRED) else None


def _age_days(as_of: Optional[str], today: Optional[_dt.date] = None) -> Optional[int]:
    try:
        d = _dt.date.fromisoformat(str(as_of)[:10])
    except (TypeError, ValueError):
        return None
    return ((today or _dt.date.today()) - d).days


def sparkline(series, width: int = 560, height: int = 90, pad: int = 6) -> dict:
    """Two SVG polyline paths (index, benchmark) scaled to a shared axis.

    Inline SVG rather than a chart library: the landing page must paint immediately, and the
    strict CSP on this site blocks external scripts anyway. A shared y-axis is the point —
    drawing each line to its own scale would make a line that LOST look like it won.
    """
    pts = [p for p in (series or []) if p and p.get("date")]
    if len(pts) < 2:
        return {"ok": False}
    a = [_f(p.get("valquo")) or 0.0 for p in pts]
    b = [_f(p.get("spy")) or 0.0 for p in pts]
    lo, hi = min(min(a), min(b)), max(max(a), max(b))
    if hi - lo < 1e-9:
        lo, hi = lo - 1.0, hi + 1.0
    n = len(pts)

    def path(vals):
        out = []
        for i, v in enumerate(vals):
            x = pad + (width - 2 * pad) * (i / (n - 1))
            y = height - pad - (height - 2 * pad) * ((v - lo) / (hi - lo))
            out.append(f"{x:.1f},{y:.1f}")
        return " ".join(out)

    return {"ok": True, "width": width, "height": height,
            "index": path(a), "bench": path(b),
            "last_index": a[-1], "last_bench": b[-1],
            "start": pts[0]["date"], "end": pts[-1]["date"], "n": n}


def range_bar(sample: dict) -> Optional[dict]:
    """Where bear / base / bull and today's PRICE sit on one shared bar, as 0-100 percents.

    The price marker is the point of this. When the price sits outside the bear-bull range —
    which is exactly what a strongly over- or under-valued name looks like — the marker is
    clamped to the end of the bar and `price_outside` is set, so the template can say so
    instead of silently drawing it at the edge as though it were inside.
    """
    bear, base, bull = sample.get("bear"), sample.get("base"), sample.get("bull")
    price = sample.get("price")
    if bear is None or bull is None or bull <= bear:
        return None
    span = bull - bear

    def pos(v):
        return max(0.0, min(100.0, (v - bear) / span * 100.0))

    out = {"bear": bear, "base": base, "bull": bull, "price": price,
           "base_pos": pos(base) if base is not None else 50.0}
    if price is not None:
        out["price_pos"] = pos(price)
        out["price_outside"] = "above" if price > bull else ("below" if price < bear else "")
    return out


def landing_context(store) -> dict:
    """Everything the landing template needs, with every piece independently optional.

    One dead component must not take the page down, so each block is built defensively and
    the template checks for None. This is the first thing a visitor sees.
    """
    ctx = {"sample": None, "sample_age": None, "sample_stale": False, "bar": None,
           "track": None, "spark": None, "scan": None}

    sample = load(store)
    if sample:
        age = _age_days(sample.get("as_of"))
        ctx["sample"] = sample
        ctx["sample_age"] = age
        ctx["sample_stale"] = bool(age is not None and age > STALE_AFTER_DAYS)
        ctx["bar"] = range_bar(sample)

    # The live forward track. Reuses the same summarize() the Index tab uses, so the landing
    # can never disagree with the page it links to — including on whether the live numbers are
    # allowed to lead yet.
    #
    # Carried even when the live track has NOT started. `summarize` still returns the
    # backtested figures and `headline: "backtested"`, and the template shows those, labelled,
    # alongside "the live paper track has not started". Drawing a backtested curve under a
    # "live" heading would be the one dishonest thing this page could do.
    try:
        from ..screener.index_track import summarize
        t = summarize("roth", store=store)
        if t:
            ctx["track"] = t
            if t.get("available"):
                ctx["spark"] = sparkline(t.get("series") or [])
    except Exception:
        ctx["track"] = None

    # Proof that the ranking is real and current: how many names were scored, and when.
    try:
        scan_date = store.latest_scan_date()
        if scan_date:
            from ..screener.freshness import status as _freshness
            ctx["scan"] = {"date": scan_date, "freshness": _freshness(scan_date, label="ranking")}
    except Exception:
        ctx["scan"] = None
    return ctx
