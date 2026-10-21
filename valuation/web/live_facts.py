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


#: Pairs that were true of the SUPERSEDED 2,531-name panel and are not true of the canonical
#: one. Held as data so `tests/test_item76.py` can fail on any public page that carries one.
#:
#: **ITEM 76's OWN SUBJECT.** `methodology.html` and `portfolio.html` carried "134 bps against a
#: measured 33 bps" and a "fourfold" margin long after the canonical panel moved to 9,645 names
#: at item 47. The figures were right when they were typed, which is the whole reason a page
#: must read them instead.
SUPERSEDED_COST_FIGURES = (
    ("134 bps", "the 2,531-name panel's breakeven"),
    ("134 basis points", "the 2,531-name panel's breakeven"),
    ("33 bps", "the 2,531-name panel's realised cost"),
    ("236 bps", "the pre-B6 void panel's breakeven"),
    ("146.3", "the restricted 3,049-name panel's breakeven, never a published object"),
    ("98.3 bps", "UNIVERSE-BIAS's exploratory corrected run, superseded by the landed move"),
)


def costs(results=None) -> dict:
    """The cost pair, READ from the tracked `BACKTEST_RESULTS.json`. Never typed. [item 76]

    `{available, breakeven_bps, realised_bps, margin, turnover_pct, n_names, n_dates, book,
    account, reason}`.

    **EVERY FIELD IS STAMPED WITH WHAT IT DESCRIBES**, because the review found the same page
    carrying two different pairs with nothing to say which book either belonged to. The cost
    pair is a measurement of the **research decile** — the ranking across the whole universe —
    and NOT of the served Index, which is a different, narrower book. `DECISIONS.md`'s standing
    rule is that any research-decile figure on a public page must say so in the same sentence
    and name its universe.

    **THE ACCOUNT TYPE MATTERS AND IS NOT THE SAME FOR BOTH BOOKS.** The canonical backtest's
    cost figures are the DEPLOYED equal-weight decile at quarterly rebalancing, which is the
    `taxable` configuration's cadence; `roth` is a top-25 book whose own breakeven is a
    different number entirely (`CANONICAL_MOVE_TABLE.md` measures it at 31.3 bps against the
    same 77.0 realised, i.e. **below** cost). So the stamp names `taxable`, and a page quoting
    this pair beside a `roth` claim would be comparing two books.

    Degrades to `available: False` with a reason rather than to a number — the page loses a
    figure instead of gaining a wrong one.
    """
    import io
    import json
    import os

    if results is None:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        p = os.path.join(root, "BACKTEST_RESULTS.json")
        try:
            results = json.load(io.open(p, encoding="utf-8"))
        except (OSError, ValueError):
            return {"available": False, "breakeven_bps": None, "realised_bps": None,
                    "margin": None, "turnover_pct": None, "n_names": None, "n_dates": None,
                    "book": None, "account": None,
                    "reason": "BACKTEST_RESULTS.json could not be read, so no cost figure "
                              "is shown"}

    c = ((results.get("costs") or {}).get("top_decile") or {})
    u = results.get("universe") or {}

    def _f(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return None
        return v if v == v else None

    bk, rl, to = _f(c.get("breakeven_one_way_bps")), _f(c.get("realised_one_way_bps")), \
        _f(c.get("annual_turnover"))
    if bk is None or rl is None or rl <= 0:
        return {"available": False, "breakeven_bps": None, "realised_bps": None,
                "margin": None, "turnover_pct": None, "n_names": u.get("n_names"),
                "n_dates": u.get("n_dates"), "book": None, "account": None,
                "reason": "the artifact carries no usable cost pair"}
    return {
        "available": True,
        "breakeven_bps": bk,
        "realised_bps": rl,
        # **THE MARGIN IS DERIVED, NOT STATED.** The pages said "about fourfold" from the old
        # pair; on the canonical panel it is far smaller, and a word like "fourfold" is a
        # figure wearing prose so it rots exactly as a number does.
        "margin": bk / rl,
        "turnover_pct": (to * 100.0) if to is not None else None,
        "n_names": u.get("n_names"),
        "n_dates": u.get("n_dates"),
        "book": "research decile (deployed equal-weight, flat 1/7)",
        "account": "taxable",
        "reason": "",
    }


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


def panel(results=None) -> dict:
    """The headline statistics, READ from the tracked artifact. Never typed.  [item 76]

    `{available, n_names, n_dates, ls_t, ls_t_nw, ls_ann, decile_alpha, decile_alpha_t,
    decile_alpha_t_hac, monotonicity, hlz_hurdle, hlz_clears, hlz_trials, x7_floor, reason}`.

    **WHY THIS EXISTS AND WHAT IT CAUGHT.** `portfolio.html`'s "What survives" section stated
    six figures as literals -- a long-short *t* of 2.84, a Newey-West 2.62, a grid range of
    2.70-3.52, a long-only 4.38, and a 2,531-name 69-date panel -- and then drew a conclusion
    from them: that the headline sits BELOW the Harvey-Liu-Zhu hurdle. On the canonical
    9,645-name panel the long-short Newey-West *t* is 4.59 against a hurdle of 3.36, so it
    CLEARS, and the page was telling readers the opposite of what the artifact says. A stale
    figure is bad; a stale figure with an inference built on top of it is worse, because
    correcting the number silently inverts the sentence around it.

    **THE HAC *t* FOR THE LONG-ONLY DECILE IS `None` ON THIS PANEL, AND THAT IS REPORTED AS
    ABSENT RATHER THAN SUBSTITUTED.** The artifact carries `top_decile_alpha_tstat` (naive) and
    `top_decile_alpha_tstat_hac: null`. `R9` made the autocorrelation-corrected figure the one
    this project quotes, so printing the naive *t* under the words "Newey-West" would be the
    wrong-object family. The template says which estimator it has and does not claim the other.
    """
    import io
    import json
    import os

    _ABSENT = {"available": False, "n_names": None, "n_dates": None, "ls_t": None,
               "ls_t_nw": None, "ls_ann": None, "decile_alpha": None, "decile_alpha_t": None,
               "decile_alpha_t_hac": None, "monotonicity": None, "hlz_hurdle": None,
               "hlz_clears": None, "hlz_trials": None, "x7_floor": None}

    if results is None:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        p = os.path.join(root, "BACKTEST_RESULTS.json")
        try:
            results = json.load(io.open(p, encoding="utf-8"))
        except (OSError, ValueError):
            d = dict(_ABSENT)
            d["reason"] = ("BACKTEST_RESULTS.json could not be read, so no headline statistic "
                           "is shown")
            return d

    c = results.get("construction") or {}
    u = results.get("universe") or {}
    h = ((results.get("multiple_testing") or {}).get("hlz") or {})

    def _f(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return None
        return v if v == v else None

    ls_nw = _f(c.get("long_short_tstat_nw"))
    if ls_nw is None:
        d = dict(_ABSENT)
        d["n_names"], d["n_dates"] = u.get("n_names"), u.get("n_dates")
        d["reason"] = "the artifact carries no long-short t-statistic"
        return d
    return {
        "available": True,
        "n_names": u.get("n_names"),
        "n_dates": u.get("n_dates"),
        "ls_t": _f(c.get("long_short_tstat")),
        "ls_t_nw": ls_nw,
        "ls_ann": _f(c.get("long_short_ann")),
        "decile_alpha": _f(c.get("top_decile_alpha")),
        "decile_alpha_t": _f(c.get("top_decile_alpha_tstat")),
        # NOT FILLED IN FROM THE NAIVE ONE. See the docstring: `None` here means the page says
        # it does not have the Newey-West figure for this object.
        "decile_alpha_t_hac": _f(c.get("top_decile_alpha_tstat_hac")),
        "monotonicity": _f(c.get("monotonicity")),
        "hlz_hurdle": _f(h.get("hurdle_sqrt_2_ln_N")),
        "hlz_clears": h.get("clears_hlz_hurdle"),
        "hlz_trials": h.get("n_trials_equity"),
        "x7_floor": _f(h.get("x7_calibrated_floor")),
        "reason": "",
    }
