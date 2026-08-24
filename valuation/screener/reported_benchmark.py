"""
SPMO AS A **REPORTED** SECOND BENCHMARK FOR THE VALQUO INDEX TRACK.  [`PT-SPMO`]

`PAPER_TRACK_CONTRACT.md` binds SPY and ONLY SPY. The anytime-valid meter, the operational
gate and the 2031 statistical verdict all attach to the SPY excess and NONE of them may read
anything in this module. That is not a caution, it is the design: this module writes its own
file, exposes its own claim, and is imported by nothing that computes a verdict. Tests pin
each half of that separately, because the two failure modes are different -- a meter that
silently switched benchmark, and a contract file that silently gained a column.

WHY SPMO AND NOT SOMETHING EASIER. The book measurably loads on momentum: `R1`'s factor
regression on the corrected panel puts it on **UMD +0.205 at t +3.65**, one of only two
standard premia it loads on (HML +0.251 at t +2.93 is the other). A cap-weighted broad-market
benchmark charges the book nothing for that exposure, so beating SPY can be a momentum
premium wearing a stock-picking label. Invesco's S&P 500 Momentum ETF is the same exposure in
a form a user can actually buy, which makes it the HARDER comparison and the fairer one. It
is added because it is harder, and the first thing it did was make the record look worse.

**IT MAKES THE RECORD LOOK WORSE, AND THAT IS SAID HERE RATHER THAN DISCOVERED.** Measured
on the four recorded rows at 2026-08-20, the SPMO excess is BELOW the SPY excess on THREE of
the four -- not all four, which is what a first draft of this paragraph claimed before the
numbers were read: on day 1 it is slightly ABOVE (+0.13pp against -0.28pp). On the latest row
the two disagree by 4.01pp, SPY excess +2.79pp against SPMO -1.22pp, because SPMO has outrun
SPY over this particular stretch. A second benchmark that flattered the book would be worth
very little; this one does not, which is the only reason it is worth adding without a
register. **Twelve trading days is not evidence of anything in either direction**, and no
figure this module produces may be quoted as a result -- see `POSTURE` below, which travels
with the numbers in the payload rather than sitting in a docstring nobody renders.

WHY A SIBLING FILE RATHER THAN A COLUMN. `data/valquo_track_history.csv` is protected by a
byte-prefix append-only rule that `.github/workflows/track-row.yml` verifies with `cmp` on
`head -n N`. Adding a column widens the header, which rewrites every line, which cannot
preserve that prefix -- so the bound file would have to be re-seeded to gain an SPMO column,
and re-seeding the one dataset that cannot be re-derived to add a REPORTED benchmark is a bad
trade at any price. The sibling is a different file for that reason and no other.

THE VALQUO LEG IS **COPIED, NEVER RE-DERIVED**, AND THE FILE SAYS SO ON EVERY ROW. Both
series must show the same Valquo number or the product publishes two of them -- which this
project has already done once, from two different books, and the cure recorded at the time
was ONE authority rather than better reconciliation. So:

  * `backfill` copies `valquo_pct` out of the bound file **as the raw cell text**, so the two
    files' Valquo legs are byte-identical rather than agreeing to a rounding;
  * the live path copies whatever the bound door SETTLED ON -- which on an idempotent second
    POST is the row already on disk, not the freshly computed one, because `append_row` is
    explicit that those two can differ when a vendor revises;
  * every row carries `valquo_src`, `recorded` or `computed`, so the provenance is per-row and
    cannot go stale the way a file-level note would.

`valquo_src` IS ALSO THE HONEST PLACE FOR A SEAM THAT ALREADY EXISTS. `index_mark`'s own
reproduction note records that its book leg lands ~0.02pp from the two hand-made rows while
its benchmark leg reproduces exactly, so a series that mixes hand-made and mechanism-written
rows carries a small discontinuity. Copying rather than re-deriving means the sibling inherits
that seam instead of adding a second one of its own, and the column names which side each row
came from.

REFUSALS ARE MOSTLY INHERITED, WHICH IS THE POINT OF BUILDING ON THE BOUND ROW. A sibling row
can only be built where a bound row exists, so the closed-session refusal, the trading-day
check, the unreadable book, the unpriceable benchmark and the coverage floor are all already
answered upstream by `index_mark.contract_row` and cannot be answered differently here. This
module adds exactly ONE refusal of its own -- SPMO cannot be priced at inception or at the
mark date -- and, like every refusal in `index_mark`, it returns no number when it fires. A
reported benchmark that fills its own gaps with a guess is worse than no reported benchmark.

THE VENDOR, MEASURED RATHER THAN ASSUMED (2026-08-20). Prices come from the shipped
`screener/prices.py`, no new vendor and no key. Its primary is Stooq and its fallback is
yfinance, and **the fallback is what serves this today**: Stooq's daily-CSV endpoint returned
**HTTP 404 for every symbol tried from this machine, including AAPL and SPY** -- the controls
-- so *"does SPMO resolve on Stooq"* is NOT ANSWERABLE from here and is recorded as unresolved
rather than as a gap in SPMO. yfinance returns SPMO cleanly on every date the series needs.
That `get_history_df` swallows the primary's failure and falls through silently is a property
of the shipped module, reported and not repaired here.

**REPAIRED 2026-08-21 (`PRICES-SRC`), and this module gets the fix for free.** The fallback
stays -- resilience was never the defect, silence was -- but every frame `get_history_df`
returns now carries `df.attrs["valquo_src"]` (`stooq` or `yfinance`) and `valquo_adjusted`, read
with `prices.source_of(df)` / `prices.adjustment_of(df)`, and a `WARNING` names the primary's
actual exception when it falls through. **The measurement above was independently reproduced
that day on ten tickers -- Stooq served 0 of 10 -- so this module's "the fallback is what serves
this today" is confirmed rather than merely suspected.**

**AND IT MATTERS HERE SPECIFICALLY, because yfinance AUTO-ADJUSTS.** `PRICES-SRC` measured that
the adjustment flag alone accounts for the whole +0.0201pp book-leg seam `index_mark` documents
(adjusted 0.7961, unadjusted 0.7760, recorded 0.7760, benchmark leg identical at 3.6228 under
both). A reported benchmark priced on an auto-adjusted basis is a TOTAL-RETURN series; if that
is not what the copy claims, the copy is wrong rather than the number. Not changed here -- this
module's basis is its own lane's call -- but it is now a labelled fact rather than an unknown.
"""
from __future__ import annotations

import datetime as _dt
import os
from typing import Callable, Optional

#: The reported benchmark. One spelling; the ticker, the column and the copy all derive from
#: it, so a second benchmark cannot be half-added.
TICKER = "SPMO"

#: The sibling file's name, beside the bound series in the same `data/` directory.
SIBLING_FILENAME = "valquo_vs_spmo.csv"

#: The sibling's header, in order. `excess_pp` is `valquo_pct - spmo_pct` and is deliberately
#: the same NAME as the bound file's excess while being a DIFFERENT QUANTITY -- which is
#: exactly why the two never share a file and why every surface that renders this one is
#: required to carry `LABEL`.
SIBLING_COLUMNS = ("date", "day_n", "valquo_pct", "valquo_src", "spmo_pct", "excess_pp")

#: What a row's Valquo leg came from. `recorded` = copied verbatim out of the bound CSV by
#: `backfill`; `computed` = copied from the row the live bound door settled on that day.
#: Neither value means "re-derived here", because nothing here re-derives it.
SRC_RECORDED = "recorded"
SRC_COMPUTED = "computed"

#: The label every surface must render beside these figures. Not advisory: `claim()` puts it
#: in the payload and a test asserts it survives into the rendered page, because a second
#: benchmark shown without it is indistinguishable from the bound one at a glance.
LABEL = "reported benchmark — not bound by the contract"

#: The one sentence of why, and its two figures are FACTOR LOADINGS rather than returns.
WHY = ("The book measurably loads on momentum (R1: UMD t 3.65), so an investable momentum "
       "ETF is the harder, fairer comparison than a cap-weighted broad-market index.")

#: What this series is NOT, carried in the payload rather than left to each surface to
#: remember. The meter, the gate and the 2031 verdict attach to SPY alone.
POSTURE = ("The meter, the operational gate and the 2031 verdict attach to SPY only. This "
           "comparison is reported for context and settles nothing.")

#: Phrases that must never appear in a rendered SPMO block. Scoped to THIS item's own section
#: and matched as whole phrases rather than bare tokens -- a guard that bans a token fires on
#: innocent prose and on its own documentation, which this repository has now paid for five
#: times. Each entry is forecast-shaped, claim-shaped or boast-shaped; none is a word that an
#: honest sentence about a twelve-day record would reach for.
BANNED = (
    # forecast
    "will beat", "will outperform", "will continue", "expected to outperform",
    "should outperform", "on track to beat",
    # a claim this record cannot support
    "proves", "proven", "guaranteed", "consistently beats", "has outperformed the market",
    "risk-free",
    # boast
    "crushes", "smashes", "best-in-class", "market-beating",
)


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def _date(s) -> Optional[_dt.date]:
    try:
        return _dt.date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def sibling_path(bound_history_path: str = None) -> str:
    """`data/valquo_vs_spmo.csv`, resolved beside whatever bound series is in play.

    Derived from the bound path rather than from the repo root so that a test pointing the
    bound series at a temp directory gets its sibling in the SAME temp directory. A sibling
    that silently resolved to the real `data/` while its bound partner was a fixture is how a
    test suite writes into the one file that cannot be re-derived -- which `MB1` did once,
    and reported.
    """
    from . import index_track
    _, hp = index_track.default_paths()
    base = bound_history_path or hp
    return os.path.join(os.path.dirname(os.path.abspath(base)), SIBLING_FILENAME)


def note_path(bound_history_path: str = None) -> str:
    """The derivation note written beside the sibling CSV."""
    return sibling_path(bound_history_path) + ".NOTE.md"


NOTE_TEXT = (
    "# " + SIBLING_FILENAME + " — how this file was derived\n"
    "\n"
    "A **reported** second benchmark for the Valquo Index forward track. It is NOT bound by\n"
    "`PAPER_TRACK_CONTRACT.md`: the anytime-valid meter, the operational gate and the 2031\n"
    "statistical verdict attach to SPY and to nothing else.\n"
    "\n"
    "* `valquo_pct` is **copied from `valquo_track_history.csv`, never re-derived here.**\n"
    "  Rows carrying `valquo_src=recorded` were copied as the raw cell text, so this file's\n"
    "  Valquo leg is byte-identical to the bound file's. Rows carrying `valquo_src=computed`\n"
    "  were copied from the row the bound write door settled on that day.\n"
    "* `spmo_pct` is " + TICKER + "'s cumulative percent return since the book's inception\n"
    "  date, from public closes via the shipped `valuation/screener/prices.py`.\n"
    "* `excess_pp` is `valquo_pct - spmo_pct`. It is a DIFFERENT QUANTITY from the bound\n"
    "  file's `excess_pp` despite the shared column name, which is why the two never share a\n"
    "  file.\n"
    "\n"
    "Written by `valuation/screener/reported_benchmark.py`. Nothing here is a result: the\n"
    "record is a handful of trading days long.\n"
)


def _closes(ticker: str, fetch: Callable) -> dict:
    """Delegates to `index_mark._closes` — one price-reading implementation, not two.

    Deliberately not re-implemented. `index_mark._closes` already carries the `utc=True` fix
    for the fact that the two vendors return tz-aware and naive stamps, and a private copy
    here would be the same module-level split this package keeps paying for.
    """
    from . import index_mark
    return index_mark._closes(ticker, fetch)


def row_for(bound_row: dict, inception, *, fetch: Callable = None,
            src: str = SRC_COMPUTED) -> dict:
    """One sibling row from one bound row, or a refusal that says why.

    `bound_row` is a row of the bound series -- `date`, `day_n` and `valquo_pct` are read and
    NOTHING is recomputed. `valquo_pct` is passed through **exactly as given**: a string stays
    a string so that a copied cell is byte-identical on the way back out, and a float stays a
    float so that a live row keeps the type the bound door wrote.

    On success:  `{"ok": True, "row": {...SIBLING_COLUMNS...}}`
    On refusal:  `{"ok": False, "reason": "...", "row": None}` — never a partial number.
    """
    from . import prices as _prices
    fetch = fetch or _prices.get_history_df

    inc = _date(inception)
    if inc is None:
        return {"ok": False, "reason": "the book carries no readable inception_date",
                "row": None}
    mark = _date((bound_row or {}).get("date"))
    if mark is None:
        return {"ok": False, "reason": "the bound row carries no readable date", "row": None}

    raw_valquo = (bound_row or {}).get("valquo_pct")
    v = _f(raw_valquo)
    if v is None:
        return {"ok": False,
                "reason": ("the bound row for " + mark.isoformat() + " carries no readable "
                           "valquo_pct, and this series copies that leg rather than "
                           "re-deriving it"),
                "row": None}

    base_key, mark_key = inc.isoformat(), mark.isoformat()
    closes = _closes(TICKER, fetch)
    b, m = closes.get(base_key), closes.get(mark_key)
    if not b or not m:
        which = ("inception " + base_key) if not b else ("mark date " + mark_key)
        return {"ok": False,
                "reason": (TICKER + " could not be priced on the " + which
                           + "; the reported comparison is omitted for that day rather than "
                             "filled in, exactly as the bound door omits a day it cannot "
                             "price"),
                "row": None}

    spmo_pct = (m / b - 1.0) * 100.0
    return {"ok": True, "reason": "", "row": {
        "date": mark_key,
        "day_n": (bound_row or {}).get("day_n"),
        "valquo_pct": raw_valquo,            # verbatim: copied, never re-derived
        "valquo_src": src,
        "spmo_pct": round(spmo_pct, 4),
        "excess_pp": round(v - spmo_pct, 4),
    }, "ticker": TICKER, "inception": base_key,
        "source": "screener/prices.py (Stooq -> yfinance)"}


def record(bound_row: dict, inception, *, fetch: Callable = None,
           bound_history_path: str = None, src: str = SRC_COMPUTED,
           append_only: bool = True) -> dict:
    """Build and append one sibling row, under the bound door's own rules.

    Runs `index_mark.append_row` with this file's `columns`, so the three append-only
    refusals, the idempotent no-op on a repeated date and the byte-prefix property are the
    SAME implementation the bound series uses rather than a second one that resembles it.
    """
    from . import index_mark
    built = row_for(bound_row, inception, fetch=fetch, src=src)
    if not built.get("ok"):
        return built
    path = sibling_path(bound_history_path)
    ap = index_mark.append_row(built["row"], path, append_only=append_only,
                              columns=SIBLING_COLUMNS)
    out = dict(built)
    out["append"] = ap
    out["path"] = path
    out["ok"] = bool(ap.get("ok"))
    if not ap.get("ok"):
        out["reason"] = ap.get("reason") or "the sibling append was refused"
    return out


def backfill(*, fetch: Callable = None, meta_path: str = None,
             bound_history_path: str = None, write: bool = True) -> dict:
    """Rebuild the whole sibling series from the recorded bound series.

    The Valquo leg is taken as the RAW CELL TEXT of the bound file, so the two files' Valquo
    columns are byte-identical rather than merely equal after rounding. Rows the reported
    benchmark cannot be priced on are SKIPPED and listed, never estimated.

    `write=False` returns what it would write and touches nothing, which is what the tests
    and `--dry-run` use.
    """
    from . import index_mark, index_track

    _, hp = index_track.default_paths()
    bound_history_path = bound_history_path or hp

    book = index_mark.load_book(meta_path)
    if not book.get("inception_date"):
        return {"ok": False, "reason": book.get("reason") or "no readable inception date",
                "rows": [], "skipped": []}
    inception = book["inception_date"]

    hist = index_mark._read_history(bound_history_path)
    if not hist.get("ok"):
        return {"ok": False, "reason": hist.get("reason"), "rows": [], "skipped": []}
    if not hist.get("rows"):
        return {"ok": False,
                "reason": ("the bound series " + str(bound_history_path) + " has no recorded "
                           "rows, so there is nothing to report a second benchmark against"),
                "rows": [], "skipped": []}

    rows, skipped = [], []
    for r in hist["rows"]:
        built = row_for(r, inception, fetch=fetch, src=SRC_RECORDED)
        if built.get("ok"):
            rows.append(built["row"])
        else:
            skipped.append({"date": (r or {}).get("date"), "reason": built.get("reason")})

    out = {"ok": bool(rows), "reason": "" if rows else "no bound row could be priced against "
           + TICKER, "rows": rows, "skipped": skipped, "ticker": TICKER,
           "inception": inception.isoformat(), "path": sibling_path(bound_history_path),
           "bound_history": bound_history_path, "wrote": False,
           "source": "screener/prices.py (Stooq -> yfinance)"}
    if not rows or not write:
        return out

    payload = index_mark._canonical_csv(rows, list(SIBLING_COLUMNS))
    err = index_mark._write_atomic(out["path"], payload)
    if err:
        out["ok"], out["reason"] = False, err
        return out
    note_err = index_mark._write_atomic(note_path(bound_history_path),
                                        NOTE_TEXT.encode("utf-8"))
    out["wrote"] = True
    out["note_path"] = note_path(bound_history_path)
    out["note_error"] = note_err                 # reported; a note is not worth failing over
    return out


def claim(*, bound_history_path: str = None, meta_path: str = None) -> dict:
    """The reported-benchmark figure for a surface to render, or `available: False`.

    Mirrors `index_track.vs_spy_claim`'s shape and posture deliberately: an unavailable
    source returns a REASON and no number, because a surface with no claim must print no
    claim. It reads only the sibling file -- it never falls back to recomputing, and it never
    reads the bound file's excess, which is a different quantity.
    """
    from . import index_mark

    out = {"available": False, "reason": "", "ticker": TICKER, "label": LABEL, "why": WHY,
           "posture": POSTURE, "bound": False, "as_of": None, "since": None, "n_points": 0,
           "valquo_pct": None, "spmo_pct": None, "excess_pp": None, "valquo_src": None}

    path = sibling_path(bound_history_path)
    hist = index_mark._read_history(path)
    if not hist.get("ok"):
        out["reason"] = hist.get("reason") or ("could not read " + str(path))
        return out
    rows = hist.get("rows") or []
    if not rows:
        out["reason"] = ("no " + TICKER + " comparison has been recorded yet, so there is no "
                         "reported-benchmark figure to show")
        return out

    last = index_mark.typed_row(rows[-1])
    out.update(available=True, as_of=last.get("date"), since=rows[0].get("date"),
               n_points=len(rows), valquo_pct=_f(last.get("valquo_pct")),
               spmo_pct=_f(last.get("spmo_pct")), excess_pp=_f(last.get("excess_pp")),
               valquo_src=last.get("valquo_src"))
    return out


def violations(text: str) -> list:
    """Banned phrases present in one rendered SPMO block.

    SCOPED TO THE BLOCK, NOT THE PAGE, and that is not a convenience. A banned tuple run
    page-wide fires on every neighbouring item's honest prose -- measured at fifteen hits the
    first time `SC-4` tried it -- and a guard that cries wolf is switched off within the week.
    Whole phrases rather than bare tokens, for the same reason.
    """
    low = (text or "").lower()
    return [p for p in BANNED if p in low]
