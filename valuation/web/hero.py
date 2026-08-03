"""
The live forward track, promoted to the top of the app.

WHY THIS IS THE HERO. Every other number in the product is backtested — measured on panels the
model was also tuned on, and defended at length in the methodology. The forward track is the
only evidence nobody could have fitted, because it did not exist when the rules were written.
It is also the one thing a competitor cannot copy honestly. So it leads the page, from the day
it has data.

WHAT IT MAY NOT DO. Lead is not the same as boast. Three rules, all enforced here rather than
in the template:

  * It is PAPER, always labelled so, with the inception date attached. `label` comes from the
    track modules themselves (`paper_track._label`, `index_track.summarize`) rather than being
    re-worded here, so the hero cannot grade the track more generously than the API does.
  * It stays THIN until the underlying module says otherwise, and `may_lead` is False while it
    is thin — a week of noise gets shown, not celebrated.
  * With no data it does not render at all for a visitor. A backtested curve under a "live"
    heading would be the single most dishonest thing this page could contain, and an empty
    "coming soon" band is just clutter. The owner gets a muted "not started" line so a silent
    failure is still visible to the person who can fix it.

This composes; it does not compute. Both halves come back from the modules that own them
(`index_track.summarize`, `paper_track.summary`), the same ones the Index and Track tabs read,
so the hero and the tab it links to cannot disagree.
"""
from __future__ import annotations

from typing import Optional

# How many points the hero sparkline draws. The full series can run to hundreds of days; a
# 220px-wide strip cannot show them and does not need to.
SPARK_POINTS = 90


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def _index_block(store) -> dict:
    """Index vs benchmark since inception, from whichever live track is actually reporting.

    Two forward records exist and neither is a substitute for the other: the ingested Cowork
    tracker (`index_track`, which the Index tab leads with and which carries a series to draw)
    and the Tradier-sandbox paper book (`paper_track.index_summary`). The hero prefers the
    first and falls back to the second, and NAMES which one it drew — an unlabelled fallback
    would silently swap the meaning of the number between deploys.
    """
    out = {"available": False}
    try:
        from ..screener.index_track import summarize
        t = summarize(store=store) or {}
    except Exception:
        t = {}
    live = t.get("live") or {}
    if t.get("available") and live:
        series = t.get("series") or []
        return {
            "available": True, "source": "index-track",
            "since": live.get("since") or t.get("inception"), "as_of": live.get("as_of"),
            "days": live.get("days"), "benchmark": t.get("benchmark") or "SPY",
            "cum_pct": _f(live.get("cum_valquo_pct")), "bench_pct": _f(live.get("cum_spy_pct")),
            "excess_pp": _f(live.get("excess_pp")),
            "thin": bool(t.get("thin")), "min_days": t.get("min_live_days"),
            "series": series[-SPARK_POINTS:],
            "note": t.get("note"),
        }

    # Fallback: the sandbox paper index. It carries returns but no valquo/spy series in the
    # shape the sparkline wants, so the hero shows the figures without a curve.
    try:
        from ..edge.paper_track import index_summary
        p = index_summary(store) or {}
    except Exception:
        p = {}
    if p.get("started"):
        idx, bench = _f(p.get("index_ret")), _f(p.get("bench_ret"))
        out = {
            "available": True, "source": "paper-sandbox",
            "since": p.get("inception"), "as_of": p.get("as_of"), "days": p.get("n_days"),
            "benchmark": "SPY",
            # paper_track reports fractions; the hero speaks in percent throughout.
            "cum_pct": None if idx is None else idx * 100.0,
            "bench_pct": None if bench is None else bench * 100.0,
            "excess_pp": (None if (idx is None or bench is None) else (idx - bench) * 100.0),
            "thin": not bool(p.get("meaningful")), "min_days": p.get("min_days_for_meaning"),
            "series": [], "note": p.get("label"),
        }
    return out


def _options_block(store) -> dict:
    """The paper options book. Expectancy comes from the scorecard or not at all."""
    try:
        from ..edge.paper_track import options_summary
        o = options_summary(store) or {}
    except Exception:
        return {"available": False}
    if not o.get("started"):
        return {"available": False}
    sc = o.get("scorecard") or {}
    n_closed = sc.get("n_closed") or 0
    return {
        "available": True, "since": o.get("inception"), "label": o.get("label"),
        "n_live": o.get("n_live"), "n_closed": n_closed,
        # Below the floor an expectancy is one lucky contract wide. Withheld rather than
        # printed small, because a printed number gets quoted and a withheld one gets read.
        "expectancy_pct": (_f(sc.get("expectancy_pct")) if o.get("meaningful") else None),
        "thin": not bool(o.get("meaningful")),
        "min_closed": o.get("min_closed_for_meaning"),
    }


def live_hero(store) -> dict:
    """One band: is the forward track real yet, and what does it say?"""
    try:
        idx = _index_block(store)
    except Exception:
        idx = {"available": False}
    try:
        opt = _options_block(store)
    except Exception:
        opt = {"available": False}

    show = bool(idx.get("available") or opt.get("available"))
    thin = bool(idx.get("thin", True) or opt.get("thin", True))
    since = idx.get("since") or opt.get("since")

    spark = None
    if idx.get("series"):
        try:
            from .showcase import sparkline
            # Same shared-axis sparkline the landing page draws, at strip size. Drawing each
            # line to its own scale would make a line that LOST look like it won.
            s = sparkline(idx["series"], width=260, height=58, pad=4)
            spark = s if s.get("ok") else None
        except Exception:
            spark = None

    label = "the forward paper track has not started"
    if show:
        label = "paper" + (f", since {since}" if since else "")
        if thin:
            label += ", thin"

    return {
        "show": show,
        # Thin is not a headline. The band renders either way when there is data; this is
        # what the template keys the "evidence" wording off, never a return figure it liked.
        "may_lead": show and not thin,
        "thin": thin, "since": since, "label": label,
        "index": idx, "options": opt, "spark": spark,
        "caveat": ("Paper, not real money, and educational only. The backtest stays the "
                   "headline result until this track is long enough to carry a claim."),
    }
