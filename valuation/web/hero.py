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
    """The Index vs its benchmark since inception, from the contract-bound recorder ONLY.

    THE FALLBACK THAT USED TO LIVE HERE IS GONE — REMOVED 2026-08-09, and it was the same
    defect that put a false claim into Discord. When the Cowork tracker files were absent
    (i.e. on every fresh deploy, since `data/` is gitignored) this function fell back to
    `paper_track.index_summary` and rendered it under the heading "Valquo Index". That is a
    different book: 10 names against the published book's 86, from a 2026-08-03 inception. It
    also took its own `(idx - bench) * 100` — a second definition of excess return, free to
    drift from the recorder's.

    CORRECTED 2026-08-11 (cold audit LA11, which did not list this file — found by sweeping for
    the claim rather than by following the audit's citations). The description above used to add
    that the engine's 10% weights "violate `PAPER_TRACK_CONTRACT.md`'s own 8% cap". They do not;
    session 16 (`PT-SPLIT`) retracted that. `valquo_index.build_index` sets
    `cap = max(MAX_WEIGHT, 1/len(picks))` deliberately, since ten names at 8% sum to 80%. The
    weights were right for the book; the BOOK was wrong, on SIZE. Nothing about the removal of
    this fallback depended on the retracted reason.

    Naming the source in the payload was not enough protection, and that is the lesson worth
    keeping: the old code DID set `source: "paper-sandbox"`, honestly, and the template never
    rendered it. A label that a surface can decline to show is not a safeguard. So the wrong
    book is no longer reachable from here at all, and an absent track renders nothing.
    """
    try:
        from ..screener.index_track import summarize
        t = summarize(store=store) or {}
    except Exception:
        t = {}
    live = t.get("live") or {}
    if not (t.get("available") and live):
        return {"available": False,
                "reason": "the contract-bound track has not reported yet"}

    series = t.get("series") or []
    return {
        "available": True, "source": "index-track",
        "since": live.get("since") or t.get("inception"), "as_of": live.get("as_of"),
        "days": live.get("days"), "benchmark": t.get("benchmark") or "SPY",
        # LA8 — `days` is the ROW COUNT and stays one, because the gate reads it. `age` is the
        # display vocabulary: how old the track is, and how many of those days were recorded.
        # A surface that renders `days` under the word "Days" is stating a coverage number as
        # an age, which is the defect LA8 names.
        "age": live.get("age"),
        "cum_pct": _f(live.get("cum_valquo_pct")), "bench_pct": _f(live.get("cum_spy_pct")),
        "excess_pp": _f(live.get("excess_pp")),
        # Book and window travel WITH the numbers so the template cannot render a figure
        # without the two facts that make it meaningful. Both come from the recorder.
        "book": live.get("book"), "window": live.get("window"), "claim": live.get("claim"),
        "recorder": live.get("recorder"),
        "thin": bool(t.get("thin")), "min_days": t.get("min_live_days"),
        "series": series[-SPARK_POINTS:],
        "note": t.get("note"),
    }


def _reported_block(idx: dict) -> dict:
    """The REPORTED benchmark, for the band. ONE SOURCE OF TRUTH, and it is the point.

    This calls `reported_benchmark.claim()` — the SAME function `/api/index-track` serves to
    the Index tab's forward card. It does not read the sibling file, does not divide two
    levels, and computes no excess of its own. A second implementation of one number is the
    `B7` defect class this project has paid for repeatedly, and the module directly above this
    one records the sharper version of it: the fallback removed in 2026-08-09 took *"its own
    `(idx - bench) * 100` — a second definition of excess return, free to drift from the
    recorder's"*. There is exactly one definition of the SPMO excess and both surfaces render
    it.

    THE WORDING TRAVELS WITH THE FIGURE RATHER THAN BEING WRITTEN HERE. `label`, `why` and
    `posture` come out of `reported_benchmark` — `V3`'s precedent, one module owning the
    calibrated wording — so the band and the tab cannot come to describe the same number
    differently. The band renders NOTHING when the claim is unavailable: a surface with no
    claim must print no claim.

    AND THE AS-OF IS CHECKED, NOT ASSUMED. The bound series and the sibling are appended by
    the same door on the same day, but they are different files and can legitimately end on
    different dates — the sibling begins when its first comparison was recorded. When they
    disagree the band says so beside the figure, because a reported excess measured to a
    different date than the bound one, rendered flush against it, is two windows presented as
    one.
    """
    try:
        from ..screener import reported_benchmark as RB
        c = RB.claim()
    except Exception:                                    # noqa: BLE001
        return {"available": False, "reason": "the reported benchmark could not be read"}

    if not isinstance(c, dict) or not c.get("available"):
        return {"available": False,
                "reason": (c or {}).get("reason") or "no reported comparison recorded yet"}
    if c.get("spmo_pct") is None or c.get("excess_pp") is None:
        return {"available": False, "reason": "the reported comparison carries no figure"}

    as_of = c.get("as_of")
    bound_as_of = (idx or {}).get("as_of")
    return {
        "available": True,
        "ticker": c.get("ticker"),
        "mark_pct": c.get("spmo_pct"),
        "excess_pp": c.get("excess_pp"),
        "as_of": as_of,
        "n_points": c.get("n_points"),
        # False whenever the two series do not end on the same date. Rendered, not silently
        # tolerated: the alternative is two windows presented as one row of figures.
        "aligned": bool(as_of and bound_as_of and as_of == bound_as_of),
        "bound_as_of": bound_as_of,
        # OWNED BY `reported_benchmark`, never retyped here.
        "label": c.get("label"),
        "why": c.get("why"),
        "posture": c.get("posture"),
    }


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
    # PT-SPMO on the band. Additive, and it can never gate `show`: the reported benchmark is
    # context, so a band that appeared because of it — or that vanished with it — would be
    # treating it as the claim.
    try:
        rep = _reported_block(idx)
    except Exception:
        rep = {"available": False}

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
        "index": idx, "options": opt, "spark": spark, "reported": rep,
        "caveat": ("Paper, not real money, and educational only. The backtest stays the "
                   "headline result until this track is long enough to carry a claim."),
    }
