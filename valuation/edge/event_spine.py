"""
I-4 — THE EVENT SPINE. One canonical point-in-time earnings-date table, and nothing else.

COLLECTION-AND-PROVENANCE CLASS. Zero trials. This module answers exactly one question --
*when did this name announce earnings, and do we know?* -- and it answers it the same way for
every consumer. It computes no signal, scores no arm, and returns no verdict.

--------------------------------------------------------------------------------------------
WHY ONE TABLE AND NOT A HELPER EACH.

The project has already paid for two mechanisms describing one named object: `PT-SPLIT` was two
recorders disagreeing about what the Valquo Index held, and it shipped an engine figure as an
Index claim. An earnings date is the same shape of object -- several lanes need it, each could
derive it plausibly, and two derivations that drift are indistinguishable from one derivation
that is right until something downstream disagrees.

So: **X-2's census, O-2's 2x2 and every EO follow-on read THIS table and nothing else.** The
agreement test at the bottom of `tests/test_event_spine.py` is what makes that enforceable
rather than aspirational -- it re-derives the SHIPPED `refuse_within` / `owns_the_event`
decisions from the spine and requires either agreement or an explicit, listed disagreement.

--------------------------------------------------------------------------------------------
THE ONE RULE, INHERITED FROM O17 AND NOT NEGOTIABLE HERE EITHER.

**A missing earnings date is UNKNOWN, never "no announcement".** `coverage()` returns a state,
never a bool, and `dates()` on a name with no coverage raises rather than returning `[]`, because
an empty list is exactly what a caller silently treats as "nothing announced".

This is not hypothetical. **29 of the options book's 186 names are foreign private issuers with
ZERO code-22 coverage** -- they file 20-F/6-K, not 8-K -- and they carry **10.0% of the trades**.
A filter reading "no date" as "safe" fails open on a systematically non-random tenth of the book,
and the failure is invisible because those rows look like passes. `FAIL_CLOSED` names are listed
by name in the census so a consumer drops them deliberately rather than by accident.

--------------------------------------------------------------------------------------------
PROVENANCE, so nobody re-derives what is already settled.

* **Code 22 = "Results of Operations and Financial Condition"** -- the Form 8-K item an earnings
  release is filed under. Decoded EMPIRICALLY in `bulk.py` (2026-08-01) by timing-vs-filing and
  by information content, then **CONFIRMED against the published legend** in
  `SHARADAR_REFERENCE.md` §2, which `S17`'s correction retrieved from
  `SHARADAR/INDICATORS?table=EVENTCODES`. It is no longer an inference. Legend totals: 385,896
  occurrences over 10,149 tickers, 2004-08-23 .. 2026-07-31.
* **`bulk.py` IS the decode layer and is reused, not reimplemented.** This module calls
  `bulk.prepare_events` and `bulk.earnings_dates`; it does not re-parse the CSV, and it does not
  keep its own copy of `EARNINGS_CODES`. A test pins that.
* **CODES 34 AND 35 SUNSET, AND THEIR DISAPPEARANCE IS NOT A SIGNAL.** Schedule 13G (34) stops
  **2024-12-17** and Schedule 13D (35) stops **2025-05-16**, from the legend's own first/last-seen
  columns; every other code in `S17`'s arm set runs to 2026-07-31. A code that stops being emitted
  is era-concentrated BY CONSTRUCTION. Recorded here -- attached to the table every event-time
  consumer reads -- specifically so a future study does not discover the cliff in its own data and
  report it as a finding. **It touches no earnings date**: code 22 has no sunset, and the spine is
  code 22 only. Whether the sunset drives anything anywhere is UNMEASURED.

--------------------------------------------------------------------------------------------
WHAT THIS IS NOT.

Not a full earnings calendar. Code 22 appears ~2.83 times per ticker-year against the ~4 a
complete quarterly calendar would give, so coverage is PARTIAL even for names that have it --
which is precisely why the coverage state is per NAME-YEAR rather than per name, and why
`PARTIAL` is its own state rather than being rounded to `COVERED`.
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import os
from typing import Iterable, Optional, Sequence

from valuation.edge import bulk

# --------------------------------------------------------------------------------------------
# Coverage states. Three, never two -- the whole point is that "no rows" is not "no events".
COVERED = "COVERED"          # >= EXPECTED_MIN code-22 dates in the year
PARTIAL = "PARTIAL"          # 1..EXPECTED_MIN-1 dates: real coverage, demonstrably incomplete
FAIL_CLOSED = "FAIL_CLOSED"  # zero dates for the name ANYWHERE: unknown, never "none"
GAP = "GAP"                  # name has coverage elsewhere but none in THIS year

#: A quarterly filer announces four times a year. Code 22's measured rate is ~2.83/ticker-year,
#: so 4 would mark almost everything PARTIAL and tell a consumer nothing. 3 is the honest line
#: between "a year that looks like a filing calendar" and "a year with a hole in it", and it is
#: recorded rather than tuned -- no arm anywhere selects on this number.
EXPECTED_MIN = 3

#: The legend's own first/last-seen dates. Not earnings codes; carried so the sunset travels with
#: the table every event-time consumer reads. See the module docstring.
CODE_SUNSETS = {
    "34": {"meaning": "Schedule 13G Filing", "first": "1994-01-04", "last": "2024-12-17"},
    "35": {"meaning": "Schedule 13D Filing", "first": "1993-11-08", "last": "2025-05-16"},
}

#: Code 22's own legend row, for the same reason: a consumer should be able to see that the
#: earnings code does NOT sunset without opening another file.
EARNINGS_CODE_LEGEND = {
    "code": "22",
    "meaning": "Results of Operations and Financial Condition",
    "occurrences": 385896,
    "tickers": 10149,
    "first": "2004-08-23",
    "last": "2026-07-31",
    "source": "SHARADAR/INDICATORS?table=EVENTCODES, transcribed in SHARADAR_REFERENCE.md §2",
    "empirical_decode": "bulk.py 2026-08-01, timing-vs-filing + information content",
}

DEFAULT_EVENTS_CSV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "bulk", "events.csv")


class UnknownCoverage(LookupError):
    """Raised by `dates()` for a name with no coverage.

    Deliberately an EXCEPTION and not an empty list. `[]` is what a caller folds into "no
    announcement in the window" without noticing; a raise cannot be folded into anything.
    """


def _d(v) -> Optional[dt.date]:
    if v is None:
        return None
    if isinstance(v, dt.date):
        return v
    s = str(v)[:10]
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        return None


class EventSpine:
    """The canonical table. Build once, share it; every consumer reads the same object."""

    def __init__(self, by_ticker: dict, source: str = "", built_utc: str = ""):
        #: {ticker: [ISO date, ...]} ascending, deduplicated. Code 22 only.
        self.by_ticker = {t: sorted(set(ds)) for t, ds in by_ticker.items() if ds}
        #: names present in the source with NO code-22 date anywhere
        self.zero_coverage = sorted(t for t, ds in by_ticker.items() if not ds)
        self.source = source
        self.built_utc = built_utc or dt.datetime.now(dt.timezone.utc).isoformat(
            timespec="seconds")
        #: {"TICKER|ISO-date": "code22" | "<label>" | "both"} -- populated by `merge_source`.
        #: Empty on a single-source spine, and empty is the honest state: every date came from
        #: `self.source`. It is NOT defaulted to "code22" for every date, because then a reader
        #: could not tell a stamped spine from an unstamped one.
        self.date_sources: dict = {}
        self.merged_from: dict = {}

    # ----------------------------------------------------------------- construction
    @classmethod
    def build(cls, names: Optional[Iterable[str]] = None, csv_path: str = "",
              cache_dir: str = "") -> "EventSpine":
        """Build from `bulk.prepare_events` -- the existing decode, not a new parser.

        `names` scopes the table to a universe; omitted, every ticker in the file is kept. A name
        that is ASKED FOR and absent from the file is recorded with zero dates (so it becomes
        FAIL_CLOSED) rather than dropped -- a name that is missing from the table entirely cannot
        be flagged, and an unflagged missing name is the fail-open bug.
        """
        path = csv_path or DEFAULT_EVENTS_CSV
        kw = {"cache_dir": cache_dir} if cache_dir else {}
        raw = bulk.prepare_events(path, **kw)
        keys = list(names) if names is not None else list(raw.keys())
        by = {}
        for t in keys:
            t = str(t).upper()
            by[t] = [str(d)[:10] for d in (bulk.earnings_dates(raw, t) or [])]
        return cls(by, source=path)

    # ----------------------------------------------------------------- the one rule
    def coverage(self, ticker: str, year: Optional[int] = None) -> str:
        """Coverage STATE for a name, or a name-year. Never a bool, never None-as-False."""
        t = str(ticker).upper()
        ds = self.by_ticker.get(t)
        if not ds:
            return FAIL_CLOSED
        if year is None:
            return COVERED if len(ds) >= EXPECTED_MIN else PARTIAL
        n = sum(1 for d in ds if d[:4] == str(year))
        if n == 0:
            return GAP
        return COVERED if n >= EXPECTED_MIN else PARTIAL

    def is_known(self, ticker: str) -> bool:
        """True only when the name has SOME coverage. FAIL_CLOSED names return False."""
        return self.coverage(ticker) != FAIL_CLOSED

    def dates(self, ticker: str) -> list:
        """Announcement dates, ascending. RAISES for a FAIL_CLOSED name -- see the class docstring."""
        t = str(ticker).upper()
        ds = self.by_ticker.get(t)
        if not ds:
            raise UnknownCoverage(
                f"{t}: no code-22 coverage. UNKNOWN, not 'no announcement' -- 29 of the options "
                f"book's names are foreign private issuers filing 20-F/6-K rather than 8-K. "
                f"Drop this row deliberately, or call dates_or_unknown().")
        return list(ds)

    def dates_or_unknown(self, ticker: str) -> Optional[list]:
        """`dates()` for a covered name, `None` for an uncovered one.

        `None`, never `[]`, so it lines up with the shipped predicates' UNKNOWN sentinel and
        cannot be iterated into a false negative.
        """
        try:
            return self.dates(ticker)
        except UnknownCoverage:
            return None

    def next_after(self, ticker: str, when) -> Optional[str]:
        """First announcement strictly after `when`; None if unknown OR none scheduled.

        The two Nones are genuinely different and a caller that needs to tell them apart must ask
        `coverage()` first. That is stated rather than papered over with a third return type,
        because every consumer so far only needs "can I use this row".
        """
        ds = self.dates_or_unknown(ticker)
        if ds is None:
            return None
        w = _d(when)
        if w is None:
            return None
        nxt = [d for d in ds if _d(d) and _d(d) > w]
        return nxt[0] if nxt else None

    # ----------------------------------------------------------------- census
    def census(self, names: Optional[Sequence[str]] = None,
               years: Optional[Sequence[int]] = None) -> dict:
        """Per name-year coverage census, plus the FAIL_CLOSED roll.

        The FAIL_CLOSED names are listed BY NAME, not merely counted, because a consumer has to
        be able to drop them deliberately -- and because "10% of trades" is the kind of figure
        that gets rounded to "a few" once it is only a number.
        """
        keys = [str(n).upper() for n in (names if names is not None else self.by_ticker)]
        keys = sorted(set(keys) | set(self.zero_coverage if names is None else []))
        if years is None:
            seen = {int(d[:4]) for t in keys for d in self.by_ticker.get(t, [])}
            years = sorted(seen)
        per_year = collections.Counter()
        per_name_year = {}
        for t in keys:
            row = {}
            for y in years:
                st = self.coverage(t, y)
                row[str(y)] = st
                per_year[(y, st)] += 1
            per_name_year[t] = row
        fail = sorted(t for t in keys if self.coverage(t) == FAIL_CLOSED)
        states = collections.Counter(self.coverage(t) for t in keys)
        # SOURCE-BOUNDED YEARS. The first and last years of the feed are partial FOR CALENDAR
        # REASONS, not data-quality ones: code 22 begins 2004-08-23 and the extract ends
        # 2026-07-31, so both end years show a wall of PARTIAL that means "the source does not
        # cover the whole year", never "coverage is degrading". Marked rather than left to be
        # rediscovered -- the identical mistake (reading a not-yet-complete period as a defect)
        # cost this project a whole tier of a harvest, and an unmarked cliff at the end of a
        # census is exactly what a trend-spotting consumer reports as a finding.
        first_y, last_y = int(EARNINGS_CODE_LEGEND["first"][:4]), int(
            EARNINGS_CODE_LEGEND["last"][:4])
        bounded = {}
        if first_y in [int(y) for y in years]:
            bounded[str(first_y)] = f"source begins {EARNINGS_CODE_LEGEND['first']}"
        if last_y in [int(y) for y in years]:
            bounded[str(last_y)] = f"source ends {EARNINGS_CODE_LEGEND['last']}"
        return {
            "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "source": self.source,
            "earnings_code": EARNINGS_CODE_LEGEND,
            "expected_min_per_year": EXPECTED_MIN,
            "n_names": len(keys),
            "name_states": dict(states),
            "fail_closed_names": fail,
            "n_fail_closed": len(fail),
            "years": [int(y) for y in years],
            "per_year": {f"{y}|{st}": n for (y, st), n in sorted(per_year.items())},
            "per_name_year": per_name_year,
            "source_bounded_years": bounded,
            "source_bounded_note": (
                "A year listed here is PARTIAL because the SOURCE does not span it, not because "
                "coverage is degrading. Code 22 begins 2004-08-23 and this extract ends "
                "2026-07-31, so the first and last years show a wall of PARTIAL by calendar. "
                "Do not read either end as a trend."),
            "code_sunsets": CODE_SUNSETS,
            "sunset_note": (
                "Codes 34 (Schedule 13G) and 35 (Schedule 13D) STOP being emitted on 2024-12-17 "
                "and 2025-05-16. Every other S17 arm code runs to 2026-07-31. A code that stops "
                "is era-concentrated BY CONSTRUCTION, so its disappearance must never be read as "
                "a signal. It touches NO earnings date: code 22 has no sunset and this spine is "
                "code 22 only. Whether the sunset drives anything is UNMEASURED."),
            "rule": (
                "A missing earnings date is UNKNOWN, never 'no announcement'. FAIL_CLOSED names "
                "must be dropped and counted, never treated as having no event."),
        }

    # ----------------------------------------------------------------- W-3b: the second source
    def merge_source(self, other: dict, label: str,
                     precedence: str = "other") -> "EventSpine":
        """Return a NEW spine merging a second dated source, stamping every date with its origin.

        `other` is `{ticker: [ISO date, ...]}`. `precedence` decides which source supplies a date
        when both do -- and it is fixed in the register BEFORE agreement is measured, because
        picking the winner after seeing which one you prefer is choosing the design on the
        outcome.

        **THE PARAMETER WAS ACCEPTED AND SILENTLY IGNORED IN THE FIRST CUT OF THIS METHOD.** It
        validated the argument, stored it on the result, and then took the union regardless, so a
        caller asking for either precedence got neither. That is `S3-I1`'s `columns=` regression
        in a second place -- an argument the signature promises and the body drops -- and it is
        not cosmetic here: the union ADDS the non-earnings Item 2.02 dates that the precedence
        rule exists to displace, so the two produce materially different spines. `union` is now a
        third named value rather than what a caller gets by accident.

        NEVER A SILENT UNION. Three states survive the merge and are distinguishable afterwards
        via `date_sources`: a date only code 22 has, a date only the second source has, and a
        date both have. A name neither source covers stays FAIL_CLOSED -- **no date is ever
        imputed from cadence**, which is this register's first void condition. `S3-I6`'s guidance
        table may CONFIRM a date; it may not supply one.

        Returns a new object rather than mutating: consumers hold the spine and a mutating merge
        would change what an already-running study is reading.
        """
        if precedence not in ("self", "other", "union"):
            raise ValueError("precedence must be 'self', 'other' or 'union'")
        merged, sources = {}, {}
        names = set(self.by_ticker) | set(self.zero_coverage) | set(other)
        for t in sorted(names):
            mine = {str(d)[:10] for d in self.by_ticker.get(t, [])}
            theirs = {str(d)[:10] for d in (other.get(t) or [])}
            if precedence == "union":
                alld = mine | theirs
            else:
                # PRECEDENCE IS RESOLVED PER NAME-YEAR, not per name and not per date.
                # Per name would let one covered year silence a source across two decades;
                # per date is not a precedence rule at all, it is a union, because two sources
                # never emit the identical string for a date they disagree about. A year is the
                # grain at which "this source covers this name" is actually true or false.
                win, lose = (theirs, mine) if precedence == "other" else (mine, theirs)
                years = {d[:4] for d in win}
                alld = set(win) | {d for d in lose if d[:4] not in years}
            if alld:
                merged[t] = sorted(alld)
            for d in alld:
                if d in mine and d in theirs:
                    sources[f"{t}|{d}"] = "both"
                elif d in theirs:
                    sources[f"{t}|{d}"] = label
                else:
                    sources[f"{t}|{d}"] = self.source_label
        out = EventSpine(merged, source=f"{self.source} + {label} [{precedence}]")
        out.date_sources = sources
        out.merged_from = {"base": self.source_label, "added": label,
                           "precedence": precedence}
        return out

    #: Label for dates originating in THIS spine. A merge that could not name its own side would
    #: leave a reader unable to tell which source a date came from, which is the whole point.
    source_label = "code22"

    def write_census(self, path: str, names: Optional[Sequence[str]] = None,
                     years: Optional[Sequence[int]] = None) -> dict:
        c = self.census(names, years)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(c, fh, indent=1)
        return c


# ------------------------------------------------------------------------------------------
# Agreement with the SHIPPED predicates.
#
# `valuation/studies/earnings_surface.py` is ARCHIVED and quarantined (MA59), so the spine does
# NOT import it -- doing so from a live module would make the archived study reachable again and
# `tests/test_ma59_quarantine.py` would fail, correctly. Instead the spine re-implements the two
# decisions here, and the TEST imports both sides and requires them to agree.
#
# That direction matters: the duplication is confined to a comparison harness whose only job is
# to fail when the two disagree. It is not a second production path.

def refuse_within(spine: "EventSpine", ticker: str, entry, window_days: int) -> Optional[bool]:
    """True = an announcement lands within `window_days` after `entry`. None = UNKNOWN."""
    ds = spine.dates_or_unknown(ticker)
    if ds is None:
        return None
    e = _d(entry)
    if e is None:
        return None
    for d in ds:
        a = _d(d)
        if a is not None and 0 <= (a - e).days <= int(window_days):
            return True
    return False


def owns_the_event(spine: "EventSpine", ticker: str, entry, expiry) -> Optional[bool]:
    """True = the contract's expiry falls after the next announcement. None = UNKNOWN."""
    ds = spine.dates_or_unknown(ticker)
    if ds is None:
        return None
    e, x = _d(entry), _d(expiry)
    if e is None or x is None:
        return None
    nxt = [a for a in (_d(d) for d in ds) if a is not None and a > e]
    if not nxt:
        return None
    return bool(x > sorted(nxt)[0])
