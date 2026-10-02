# -*- coding: utf-8 -*-
"""THE BOOK IN FORCE — the Valquo Index as a held book, not a daily pick.

**DON'S RULING, 2026-10-02.** Hot stocks and options are daily; the Valquo Index is not. The
Index is the book formed at the last quarterly rebalance, held unchanged until the next one, and
it is the same book the forward record measures against SPY and SPMO.

**THE DEFECT.** `/api/valquo-index` called `build_index(st.load_snapshot(latest_scan_date))` on
every request, so the tab's holdings were rebuilt from each day's scan and changed daily — while
the forward record beneath them tracked a fixed 86-name book formed 2026-07-30. The tab's own
intro said so out loud ("The holdings are rebuilt from each day's scan. The forward record
further down is a separate, fixed book"). Two different books under one name, which Don read as
the Index having rebalanced. Measured: the bound record carries **86 positions** formed
**2026-07-30** from scan **2026-07-24**, against a default `roth` config that serves **25**
names off today's scan.

**WHAT THIS MODULE IS AND IS NOT.** It READS the bound record and reports what is in force. It
does not build a book, does not score, does not weight, and writes nothing — so adopting it
changes no scoring, no weight, no construction and no recorded figure, and it is NOT a vintage
event. `valquo_index.build_index` is untouched and still the only thing that BUILDS a rebalance
book (the Oct 22 runbook's `--config taxable` path is unaffected), and nothing the writer reads
is modified.

**NOT A SECOND IMPLEMENTATION (B7).** The events, the inception-as-event-zero convention and
the which-event-governs rule all come from `index_mark` — `load_book`, `rebalance_events`,
`event_in_force` — imported, never re-derived. A second copy of "which book is in force" is
precisely how the tab and the record came to disagree in the first place.
"""
from __future__ import annotations

import datetime as _dt
import os

#: Trading days from a book's SCAN DATE to its next scheduled rebalance.
#:
#: DERIVED, NOT A PINNED DATE. `REBALANCE_RUNBOOK_2026-10-22.md` fixes the next one by its own
#: arithmetic -- "63 trading days from the 2026-07-24 scan is Thursday 2026-10-22" -- and that
#: reproduces exactly from the bound record's own `scan_date` (verified in the test suite). A
#: hard-coded 2026-10-22 would be right for one quarter and silently wrong for every quarter
#: after it, which is the clock-shaped guard this project has repointed three times.
#:
#: NOTE IT IS THE SCAN DATE AND NOT INCEPTION: 63 trading days after 2026-07-30 is 2026-10-28,
#: six days adrift of the runbook.
REBALANCE_TRADING_DAYS = 63

#: CORPORATE EXITS, DECLARED RATHER THAN INFERRED.
#:
#: **WHY A LIST AND NOT A RULE.** The tempting rule is "a holding no vendor can price today has
#: left the book", and it is wrong in exactly the way `E-5` already paid for: an acquisition is
#: a TERMINAL value while an administrative gap in a vendor's file is CENSORING, and the two
#: look identical from here. WBS's yfinance frame stops on 2026-08-19 -- which is corroboration
#: of the acquisition rather than evidence of it, since an unpriceable name looks the same.
#:
#: So an exit is a FACT someone decided, carried with its provenance, and a test bans inferring
#: one from unpriceability. `PAPER_TRACK_CONTRACT.md` will codify the treatment; until it does,
#: this is Don's ruling of 2026-10-02 and is labelled as one.
EXITS = (
    {"ticker": "WBS", "date": "2026-08-20", "reason": "acquired",
     "treatment": "sold at last close; weight spread pro-rata across survivors",
     "ruling": "Don 2026-10-02; PAPER_TRACK_CONTRACT amendment outstanding"},
)


def _f(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if v != v else v


def _date(x):
    try:
        return _dt.date.fromisoformat(str(x)[:10])
    except (TypeError, ValueError):
        return None


def next_rebalance(scan_date, n: int = REBALANCE_TRADING_DAYS):
    """`n` trading days after `scan_date`, as an ISO string, or None.

    The trading calendar is `market_session`'s -- the same authority `missing_dates` and the
    contract's own gap report use, so this cannot disagree with them about which days count.
    """
    from . import market_session as _ms
    d = _date(scan_date)
    if d is None or n is None or n < 0:
        return None
    left = int(n)
    while left > 0:
        d += _dt.timedelta(days=1)
        if _ms.is_trading_day(d):
            left -= 1
    return d.isoformat()


def book_in_force(*, meta_path: str = None, as_of=None) -> dict:
    """The book governing `as_of` (default today), from the SERVICE'S BOUND RECORD.

    Returns `ok: False` with a reason rather than raising, and never a partial book: a caller
    that cannot tell "no book" from "a book I could only half read" is how a thin holding list
    gets published as the Index.
    """
    from . import index_mark as IM

    book = IM.load_book(meta_path=meta_path) if meta_path else IM.load_book()
    if not book.get("ok"):
        return {"ok": False, "reason": book.get("reason") or "the bound book is unreadable",
                "positions": []}
    mark = _date(as_of) or _dt.date.today()
    events = book.get("rebalances") or []
    ev = IM.event_in_force(events, mark)
    if not ev:
        return {"ok": False, "positions": [],
                "reason": ("no rebalance event is in force on %s -- the book's inception is "
                           "later than the date asked about" % mark.isoformat())}

    formed = ev["date"]
    scan = ev.get("scan_date") or book.get("scan_date")
    raw = [{"ticker": str(p.get("ticker") or "").upper(), "weight": _f(p.get("weight"))}
           for p in (ev.get("positions") or [])]
    raw = [p for p in raw if p["ticker"] and p["weight"]]

    # EXITS APPLY ONLY IF THEY FALL INSIDE THE SEGMENT THIS EVENT GOVERNS. An exit before the
    # book was formed is not this book's exit, and one after `as_of` has not happened yet --
    # both would otherwise silently reshape a historical view.
    ex = {}
    for e in EXITS:
        d = _date(e.get("date"))
        if d is None or d < formed or d > mark:
            continue
        ex[str(e.get("ticker") or "").upper()] = dict(e, date=d.isoformat())

    exited_w = sum(p["weight"] for p in raw if p["ticker"] in ex)
    live_w = sum(p["weight"] for p in raw if p["ticker"] not in ex)
    # PRO-RATA, AND THE SCALE IS REPORTED. Spreading an exited name's weight across survivors
    # in proportion to their own weights is `1/(1 - exited)` on each -- stated as a number so a
    # reader can check the column rather than trust it.
    scale = (1.0 / live_w) if live_w > 0 else None

    out = []
    for p in raw:
        gone = ex.get(p["ticker"])
        row = {"ticker": p["ticker"],
               "weight_at_formation": round(p["weight"], 6),
               # `weight` is kept as the CURRENT weight because the allocation tool and the
               # holdings table already read that key -- changing its meaning silently would
               # be worse than either name.
               "weight": (0.0 if gone else
                          (round(p["weight"] * scale, 6) if scale else p["weight"])),
               "status": "exited" if gone else "held"}
        if gone:
            row["exit"] = {"date": gone["date"], "reason": gone["reason"],
                           "treatment": gone["treatment"], "ruling": gone["ruling"]}
        out.append(row)

    return {"ok": True, "reason": "",
            "formed_on": formed.isoformat(),
            "scan_date": scan,
            "benchmark": book.get("benchmark") or "SPY",
            "inception_date": (book.get("inception_date").isoformat()
                               if hasattr(book.get("inception_date"), "isoformat")
                               else book.get("inception_date")),
            "is_inception_book": bool(ev.get("is_inception")),
            "n_rebalances_so_far": max(0, len(events) - 1),
            "next_rebalance": next_rebalance(scan),
            "next_rebalance_basis": ("%d trading days from the book's scan date (%s)"
                                     % (REBALANCE_TRADING_DAYS, scan)),
            "positions": out,
            "n_positions": sum(1 for r in out if r["status"] == "held"),
            "n_exited": len(ex),
            "weight_exited": round(exited_w, 6),
            "prorata_scale": (round(scale, 6) if scale else None),
            "as_of": mark.isoformat(),
            "held_since_days": (mark - formed).days,
            "source": "the service's bound record (data/valquo_track.json plus its rebalance "
                      "events) -- NOT today's scan"}


def sector_mix(book: dict, store=None) -> dict:
    """Sector weights for the book in force, from the scan snapshot's own sector labels.

    FREE: the snapshot is already loaded for every other surface on the page and carries a
    `sector` per name, so this costs no vendor call. A name the snapshot does not carry is
    counted as `unknown` rather than dropped -- dropping it would make the weights sum to less
    than the book and look like a rounding error.
    """
    rows = []
    if store is not None:
        try:
            rows = store.load_snapshot(store.latest_scan_date()) or []
        except Exception:                                               # noqa: BLE001
            rows = []
    by = {}
    for r in rows:
        t = str(r.get("ticker") or "").upper()
        if t:
            by[t] = str(r.get("sector") or "").strip() or "unknown"
    mix, n_unknown = {}, 0
    for p in book.get("positions") or []:
        if p.get("status") != "held":
            continue
        s = by.get(p["ticker"]) or "unknown"
        if s == "unknown":
            n_unknown += 1
        mix[s] = round(mix.get(s, 0.0) + (p.get("weight") or 0.0), 6)
    held = sum(1 for p in (book.get("positions") or []) if p.get("status") == "held")
    # ALL-UNKNOWN IS NOT A SECTOR MIX, AND IT MUST NOT RENDER AS ONE. The labels come from the
    # LATEST scan, while the book was formed from an earlier one -- so a name the current
    # universe no longer carries has no label here. Measured on a fixture store (scan date
    # 2099-01-01) every one of the 85 held names came back unknown, which would have drawn a
    # single 100% "unknown" wedge and looked like a finding about the book. `available` is
    # False when NOTHING could be labelled, so a caller can say "not available" instead.
    return {"mix": dict(sorted(mix.items(), key=lambda kv: -kv[1])),
            "n_unknown_sector": n_unknown,
            "n_held": held,
            "available": bool(held) and n_unknown < held,
            "reason": ("" if (held and n_unknown < held) else
                       ("none of the %d held names appears in the latest scan snapshot, so no "
                        "sector label could be resolved" % held)),
            "basis": "weights as held today, sector labels from the latest scan snapshot"}


# ------------------------------------------------------------------------------------------
# RETURNS SINCE FORMATION — the one expensive part, and it is deliberately OFF the request path
# ------------------------------------------------------------------------------------------
#: Where the computed returns are parked for the tab to read.
RETURNS_CACHE = os.path.join("data", "live_cache", "index_in_force_returns.json")


def returns_cache_path() -> str:
    return (os.environ.get("INDEX_IN_FORCE_RETURNS") or "").strip() or RETURNS_CACHE


def compute_returns(book: dict, *, fetch=None, as_of=None) -> dict:
    """Each holding's return since formation. ONE VENDOR CALL PER TICKER.

    **WHY IT IS NOT COMPUTED ON A PAGE LOAD.** It needs a close at the formation date and a
    close today for ~86 names. Through the per-run memo that is 87 fetches, and the same
    machinery was measured at ~26s for 87 tickers the day this was written -- fine for a
    writer, not for a public tab. So this function is for a CALLER THAT HAS TIME, it writes a
    cache, and the API serves the cache and says how old it is. A tab that cannot find the
    cache shows holdings and weights and says returns are unavailable, which is a degradation
    rather than a blank page.

    The memo is `track_reconstruct._PriceMemo`, imported rather than rebuilt: it already
    anchors on the earliest date of the run, caches a failure so a dead vendor costs its
    timeout once, and inspects the base fetcher before handing it an `as_of`.
    """
    from .track_reconstruct import _PriceMemo
    from . import index_mark as IM

    if not book.get("ok"):
        return {"ok": False, "reason": book.get("reason") or "no book in force"}
    formed = book["formed_on"]
    mark = str(_date(as_of) or _dt.date.today())
    tickers = [p["ticker"] for p in book["positions"]]
    memo = _PriceMemo([formed, mark], base=fetch)

    out, priced, unpriced = {}, 0, []
    for p in book["positions"]:
        t = p["ticker"]
        closes = IM._closes(t, memo, None, as_of=None)
        p0 = closes.get(formed)
        if p0 is None:
            # The formation date may be a holiday for one vendor's file; take the last close
            # at or before it rather than refusing the name outright.
            earlier = [d for d in closes if d <= formed]
            p0 = closes[max(earlier)] if earlier else None
        # AN EXITED NAME IS PRICED AT ITS LAST CLOSE, which is what "sold at last close" means.
        if p.get("status") == "exited":
            later = [d for d in closes if d <= p["exit"]["date"]] or list(closes)
            p1 = closes[max(later)] if later else None
        else:
            upto = [d for d in closes if d <= mark]
            p1 = closes[max(upto)] if upto else None
        if p0 and p1 and p0 > 0:
            out[t] = {"price_at_formation": round(p0, 6), "price_now": round(p1, 6),
                      "return_pct": round((p1 / p0 - 1.0) * 100.0, 4),
                      # THE DATE OF THE CLOSE USED, for a held name AND an exited one.
                      # The first cut dated an exited name by its EXIT date here, which
                      # is a day after the close for WBS (exit 08-20, last close 08-19)
                      # -- a price captioned with a day it did not come from.
                      "priced_through": (max(later) if p.get("status") == "exited"
                                         else max([d for d in closes if d <= mark]
                                                  or [None]))}
            priced += 1
        elif p.get("status") == "exited" and p1:
            # AN EXITED NAME WHOSE FORMATION PRICE THE VENDOR NO LONGER CARRIES. Measured on
            # WBS: yfinance keeps exactly ONE row for it, 2026-08-19 -- the final close -- and
            # drops the history, so `price_at_formation` is gone and the return since formation
            # is not computable from a free source. The last close IS available and is the
            # number Don's ruling names, so it is reported with the return left EXPLICITLY
            # absent and the reason attached. Imputing a formation price here would put a
            # fabricated return on the one holding whose treatment is a standing decision.
            out[t] = {"price_at_formation": None, "price_now": round(p1, 6),
                      "return_pct": None,
                      "return_unavailable": ("the vendor no longer carries this name's close "
                                             "on the formation date, so its return since "
                                             "formation is not computable from a free source"),
                      # THE DATE OF THE CLOSE ACTUALLY USED, not the exit date. WBS's last
                      # close is 2026-08-19 while its exit is dated 08-20, so reporting the
                      # exit date would caption a price with a day it did not come from.
                      "priced_through": (max(later) if later else None)}
            priced += 1
        else:
            unpriced.append(t)
    # NO BOOK-LEVEL TOTAL IS COMPUTED HERE, AND THAT IS DELIBERATE. A weighted average of
    # these per-holding returns would exclude any name the vendor cannot price -- WBS today --
    # and would then disagree with the RECORDED series, which is the contract's own number and
    # the only thing that may be quoted as the Index's return. Two totals under one name is how
    # the tab and the record came to disagree in the first place. A test pins that no key here
    # looks like one.
    return {"ok": True, "formed_on": formed, "as_of": mark,
            "returns": out, "n_priced": priced, "unpriced": unpriced,
            "n_tickers": len(tickers),
            "no_book_total_here": ("per-holding only; the Index's own return is the recorded "
                                   "series in the bound track, never a sum of these"),
            "prices": memo.stats(),
            "computed_at": _dt.datetime.now().replace(microsecond=0).isoformat()}


def save_returns(res: dict, *, path: str = None) -> dict:
    """Park the computed returns beside the other live-cache files.

    REFUSES TO WRITE A RESULT THAT PRICED NOTHING, for the reason `track_reconstruct.save` has
    the same refusal: one throttled run must not replace a good file with an empty one.
    """
    import json
    if not res.get("ok") or not res.get("returns"):
        return {"ok": False, "reason": "nothing was priced, so nothing is written"}
    p = path or returns_cache_path()
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    os.replace(tmp, p)
    return {"ok": True, "path": p, "n": len(res["returns"])}


def load_returns(*, path: str = None) -> dict:
    """The parked returns, or an explicit absence. NEVER a silent empty dict."""
    import json
    p = path or returns_cache_path()
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:                                                   # noqa: BLE001
        return {"available": False, "reason": "no returns have been computed yet"}
    if not isinstance(d, dict) or not d.get("returns"):
        return {"available": False, "reason": "the returns cache is empty or unreadable"}
    age = None
    c = d.get("computed_at")
    if c:
        try:
            age = (_dt.datetime.now()
                   - _dt.datetime.fromisoformat(str(c))).total_seconds() / 86400.0
        except (TypeError, ValueError):
            age = None
    return {"available": True, "returns": d["returns"], "formed_on": d.get("formed_on"),
            "as_of": d.get("as_of"), "computed_at": c,
            "age_days": (round(age, 2) if age is not None else None),
            "n_priced": d.get("n_priced"), "unpriced": d.get("unpriced") or []}


def attach_returns(book: dict, *, path: str = None) -> dict:
    """Merge the parked returns onto the book's positions, in place, and report the state.

    The book is returned whether or not returns are available: holdings and weights are the
    answer to "what is the Index", and the return column is an addition to it.
    """
    got = load_returns(path=path)
    book["returns_state"] = {k: v for k, v in got.items() if k != "returns"}
    if not got.get("available"):
        return book
    # STALE AGAINST A DIFFERENT BOOK IS NOT STALE, IT IS WRONG. A returns file computed for an
    # earlier formation date describes a book that is no longer in force, so it is refused
    # rather than shown against today's holdings.
    if got.get("formed_on") and got["formed_on"] != book.get("formed_on"):
        book["returns_state"] = {"available": False,
                                 "reason": ("the parked returns were computed for the book "
                                            "formed %s, not the one in force (%s)"
                                            % (got["formed_on"], book.get("formed_on")))}
        return book
    r = got["returns"]
    for p in book.get("positions") or []:
        v = r.get(p["ticker"])
        if v:
            p.update(v)
            # `price` is what the allocation tool reads; it wants the CURRENT price.
            p["price"] = v.get("price_now")
    return book
