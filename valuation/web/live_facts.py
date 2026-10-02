# -*- coding: utf-8 -*-
"""LIVE FACTS FOR PUBLIC COPY — numbers a page must read rather than state.

**THE DEFECT CLASS.** `/methodology` and `/work` carried hard-coded figures: "248 by
2026-09-29", "578 across the whole project, as of 2026-09-30", "~800 most liquid US names".
Measured 2026-10-02 the trial counts read 248/578 on this branch and 252/582 on the live main --
which is the point: a figure typed into a template is right on the day it is typed and wrong
afterwards, and the SAME figure differs between branches, so no single literal can be correct.
`/proof` already reads the log; these pages did not.

**THE UNIVERSE IS 1,500, NOT ~800.** Three public surfaces said ~800. The screener's own
`universe_size` is the authority and the scan reports it.

**WHY THIS IS SAFE ON `/work`, WHICH IS PINNED BYTE-IDENTICAL ACROSS REQUESTS.** That page's
contract is that it reads no store, exposes no vendor data and makes no `/api/` call, so the
response cannot vary between two requests. `RESEARCH_LOG.md` is a TRACKED FILE, not a clock and
not a store: its bytes change only when the repository changes, so the page stays byte-identical
within a deploy while tracking the committed log instead of a stale literal. Nothing here reads
a date, a scan or a vendor.

**EVERY FIGURE DEGRADES TO `None`, NEVER TO A NUMBER.** A page that cannot read the log must say
so rather than print a plausible count -- which is how the stale literals read in the first
place.
"""
from __future__ import annotations


#: Below this a snapshot is a fixture rather than the live universe -- see `universe_size`.
MIN_PLAUSIBLE_UNIVERSE = 100


def trial_counts() -> dict:
    """`{equity, options, infra, total, available}` from the research log.

    ONE PARSE, the same `research_log` that sets the Deflated Sharpe's own denominator -- so the
    number on the page and the number inside the model's significance test cannot disagree.
    """
    try:
        from ..edge import research_log as RL
        d = RL.detail() or {}
        by = d.get("by_domain") or {}
    except Exception:                                                   # noqa: BLE001
        return {"available": False, "equity": None, "options": None, "infra": None,
                "total": None,
                "reason": "the research log could not be read, so no trial count is shown"}
    eq, op, inf = by.get("equity"), by.get("options"), by.get("infra")
    if eq is None:
        return {"available": False, "equity": None, "options": None, "infra": None,
                "total": None,
                "reason": "the research log carries no equity trial count"}
    # THE TOTAL IS SUMMED FROM THE BUCKETS, not read from a `trials` key: `detail()` returns
    # None for that key on this parse, and a page that printed None as "0" would understate
    # every multiple-testing statement on it.
    total = sum(v for v in (eq, op, inf) if isinstance(v, int))
    return {"available": True, "equity": eq, "options": op, "infra": inf, "total": total,
            "reason": ""}


def universe_size(store=None) -> dict:
    """How many names the live scan actually ranks, from the latest snapshot.

    `~800` was on three public surfaces; the scan ranks 1,500. Counted from the snapshot the
    ranking is served from, so it cannot drift from what the Hot Stocks tab shows.
    """
    try:
        if store is None:
            from ..screener.store import Store
            store = Store()
        d = store.latest_scan_date()
        rows = store.load_snapshot(d) if d else []
    except Exception:                                                   # noqa: BLE001
        return {"available": False, "n": None, "scan_date": None,
                "reason": "no scan snapshot could be read"}
    if not rows:
        return {"available": False, "n": None, "scan_date": d,
                "reason": "the latest scan snapshot is empty"}
    n = len(rows)
    # A FLOOR, STATED AS A JUDGEMENT. A development store holds a one-name fixture (measured:
    # scan date 2099-01-01, 1 row), and "the 1 most liquid US names" on a public page is worse
    # than the stale "~800" this replaces. Below the floor the figure is withheld and the copy
    # falls back to a phrase with no number in it -- the page loses a count, never gains a
    # wrong one. 100 is not derived from anything; it is far below any real universe and far
    # above any fixture.
    if n < MIN_PLAUSIBLE_UNIVERSE:
        return {"available": False, "n": None, "scan_date": d, "counted": n,
                "reason": ("the latest snapshot holds %d names, below the %d floor at which "
                           "this is taken to be a real universe rather than a fixture"
                           % (n, MIN_PLAUSIBLE_UNIVERSE))}
    return {"available": True, "n": n, "scan_date": d, "reason": ""}
