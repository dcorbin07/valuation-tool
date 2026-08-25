"""S25 — THE POINT-IN-TIME SECTOR MAP. A dated GICS history, crosswalked to the panel's names.

**THE FIRST PERMANENTLY-CLOSED LEDGER ROW WHOSE OWN NAMED EXIT CRITERION HAS BEEN MET.** `S25`
closed `UNOBTAINABLE-WITHOUT-NEW-DATA` on 2026-08-12, and its route back was written down at the
time: *"a historical GICS snapshot, not sold as history"*. `comp.co_hgic` is that, dated —
45,838 rows, `indfrom`/`indthru`, 94.9% of our universe, and 30.2% of gvkeys carrying more than
one row, which is what makes it a HISTORY rather than a snapshot wearing a date.

**THE CROSSWALK IS DECLARED IN `PREREG_s25_sector_crosswalk.md`, COMMITTED ALONE BEFORE THIS
FILE EXISTED.** Eleven GICS sectors and eleven panel sectors admit many mappings; the one below
is fixed there with a reason per cell, so no figure produced here can have chosen it. **Reading
that register is not optional for anyone consuming this module** — it carries the cost, the
decomposition and the void conditions.

**WHAT THIS MODULE IS FOR, AND WHAT IT IS NOT FOR.** Its immediate consumer is the LOOK-AHEAD
REPAIR: `calibration.py` passes TODAY's sector into `pit_company` for a 1998 or 2009 valuation,
where it selects `SECTOR_TARGET_MARGIN` (a 2.70x spread) and `SECTOR_MULTIPLES`. **It is NOT a
re-opening of sector-neutral ranking**, which was REJECTED TWICE on measurement in both held-out
directions; a dated map removes the DATA objection and does not touch the REJECTION.

**THE TWO THINGS A CONSUMER MUST NOT GET WRONG:**

  * **THE LABELS MAP 1:1 AND THE MEMBERSHIP DOES NOT.** `taxonomy_disagreement()` measures the
    vendor disagreement on TODAY's date, where both labels are observable, and it must be
    quoted beside any figure produced by the FULL variant. A sector that changes under the
    crosswalk has not necessarily been reclassified.
  * **A TAXONOMY REVISION IS NOT A CORPORATE EVENT.** Real Estate split from Financials in 2016
    and Communication Services was created in 2018; both move every firm in a group on one date
    and none of those firms did anything. Every transition carries `revision`, and a consumer
    reading `indfrom` as an event date without it is measuring an index provider's paperwork.
"""
from __future__ import annotations

import bisect
import datetime as _dt
import os
from typing import Optional

#: THE CROSSWALK, exactly as declared in `PREREG_s25_sector_crosswalk.md` section 2. Any edit
#: here without a dated amendment there is a void condition of that register.
GICS_TO_PANEL = {
    "10": "Energy",
    "15": "Basic Materials",
    "20": "Industrials",
    "25": "Consumer Cyclical",
    "30": "Consumer Defensive",
    "35": "Healthcare",
    "40": "Financial Services",
    "45": "Technology",
    "50": "Communication Services",
    "55": "Utilities",
    "60": "Real Estate",
}

#: The eleven strings the ENGINE is keyed on. Imported from the engine rather than retyped, so
#: the crosswalk cannot drift from the dicts it exists to feed (`MA5` -- four copies of one
#: fact, and only one of them saw the floor).
def engine_sector_keys() -> set:
    from valuation.engine.assumptions import SECTOR_TARGET_MARGIN
    return set(SECTOR_TARGET_MARGIN)


#: GICS's own revisions inside the covered window. NOT corporate events.
#: (label, first date the new code can appear, the codes it moved names INTO)
TAXONOMY_REVISIONS = (
    ("REAL_ESTATE_2016", "2016-08-31", "2016-09-30", ("60",)),
    ("COMM_SERVICES_2018", "2018-09-01", "2018-10-31", ("50",)),
)

UNMAPPED = "UNMAPPED"
AMBIGUOUS_TICKER = "AMBIGUOUS_TICKER"
NOT_COVERED = "NOT_COVERED"
BEFORE_GICS = "BEFORE_GICS"

#: GICS did not exist before this. A sector cannot be dated earlier and the module refuses to
#: invent one -- `S23`'s valuation path reaches 1998 and its earliest rows are NOT repairable.
GICS_EPOCH = "1999-06-30"


def crosswalk(gsector) -> str:
    """One GICS sector code -> one panel sector string, or `UNMAPPED`.

    `UNMAPPED` is returned rather than an empty string ON PURPOSE. Both engine dicts FAIL OPEN
    -- `SECTOR_TARGET_MARGIN.get(sector, 0.12)` and `SECTOR_MULTIPLES.get(sector, _DEFAULT)` --
    so an empty sector is silently given the middle of the range. **A crosswalk that returns
    nothing is not neutral; it is a vote for 0.12.** Naming the state lets a caller count it.
    """
    key = str(gsector or "").strip()
    if key.endswith(".0"):
        key = key[:-2]
    return GICS_TO_PANEL.get(key, UNMAPPED)


def _d(x) -> Optional[str]:
    if x is None:
        return None
    s = str(x)[:10]
    try:
        _dt.date.fromisoformat(s)
    except ValueError:
        return None
    return s


class SectorMap:
    """A dated sector history per ticker. Build once, share it; every consumer reads one object.

    `spans[ticker]` is a list of `(indfrom, indthru_or_None, gsector, panel_sector)` sorted by
    `indfrom`. A lookup is a binary search, so a 108,241-row panel costs one pass.
    """

    def __init__(self, spans: dict, ambiguous: dict = None, source: str = "",
                 built_utc: str = ""):
        self.spans = {t: sorted(v, key=lambda r: r[0]) for t, v in spans.items() if v}
        self.ambiguous = dict(ambiguous or {})
        self.source = source
        self.built_utc = built_utc or _dt.datetime.now(_dt.timezone.utc).isoformat(
            timespec="seconds")
        self._starts = {t: [r[0] for r in v] for t, v in self.spans.items()}

    # ------------------------------------------------------------------ the one lookup
    def at(self, ticker: str, as_of) -> dict:
        """The panel sector for `ticker` on `as_of`. THREE STATES, never a bare string.

        Returns `{"sector", "state", "gsector", "indfrom", "indthru"}` where `state` is `OK`,
        `NOT_COVERED`, `AMBIGUOUS_TICKER`, `BEFORE_GICS` or `UNMAPPED`. **A caller that reads
        `sector` without reading `state` will treat "we do not know" as "no sector", and the
        engine turns that into 0.12 without saying so.**
        """
        t = str(ticker or "").upper().strip()
        d = _d(as_of)
        out = {"sector": None, "state": NOT_COVERED, "gsector": None,
               "indfrom": None, "indthru": None}
        if t in self.ambiguous:
            out["state"] = AMBIGUOUS_TICKER
            out["candidates"] = list(self.ambiguous[t])
            return out
        if d is None:
            return out
        if d < GICS_EPOCH:
            out["state"] = BEFORE_GICS
            return out
        rows = self.spans.get(t)
        if not rows:
            return out
        i = bisect.bisect_right(self._starts[t], d) - 1
        if i < 0:
            # The name exists but its first classification POSTDATES this row. Not covered --
            # never the first span, which would be a look-ahead of exactly the kind this
            # module exists to remove.
            return out
        frm, thru, gs, panel = rows[i]
        if thru is not None and d > thru:
            # Fell in a GAP between spans. Reported as not covered rather than carried
            # forward: a lapsed classification is not evidence about this date.
            return out
        out.update({"sector": panel if panel != UNMAPPED else None,
                    "state": "OK" if panel != UNMAPPED else UNMAPPED,
                    "gsector": gs, "indfrom": frm, "indthru": thru})
        return out

    def current(self, ticker: str) -> dict:
        """The LATEST classification -- what a snapshot source would have said."""
        return self.at(ticker, _dt.date.today().isoformat())

    # ------------------------------------------------------------------ diagnostics
    def transitions(self, ticker: str = None) -> list:
        """Every dated change, each labelled TAXONOMY_REVISION or FIRM_RECLASSIFICATION.

        **A REVISION IS FLAGGED, NOT DELETED**, and the register says why: for a VALUATION
        repair a revision really does change which margin a name is scored against, whatever
        caused it. The label exists so an EVENT study cannot count it, and so the repair can
        report how much of its own movement is an index provider's paperwork.
        """
        out = []
        names = [ticker.upper()] if ticker else sorted(self.spans)
        for t in names:
            rows = self.spans.get(t) or []
            for prev, cur in zip(rows, rows[1:]):
                out.append({
                    "ticker": t, "date": cur[0],
                    "from_gsector": prev[2], "to_gsector": cur[2],
                    "from_sector": prev[3], "to_sector": cur[3],
                    "revision": classify_transition(cur[0], cur[2]),
                })
        return out

    def coverage(self) -> dict:
        n_multi = sum(1 for v in self.spans.values() if len(v) > 1)
        return {"tickers": len(self.spans), "ambiguous": len(self.ambiguous),
                "reclassified": n_multi, "rows": sum(len(v) for v in self.spans.values()),
                "source": self.source, "built_utc": self.built_utc}


def classify_transition(date, to_gsector) -> str:
    """`TAXONOMY_REVISION` when the date AND the destination code both match a known revision.

    **BOTH CONDITIONS, because either alone over-claims.** A date window alone would relabel
    every ordinary reclassification that happened to occur in that month; a code alone would
    relabel every move into Real Estate for the next decade. Requiring the pair keeps the flag
    to what the revision actually did -- move firms INTO a new code, on its date.
    """
    d = _d(date)
    if d is None:
        return "FIRM_RECLASSIFICATION"
    code = str(to_gsector or "").strip()
    if code.endswith(".0"):
        code = code[:-2]
    for label, lo, hi, codes in TAXONOMY_REVISIONS:
        if lo <= d <= hi and code in codes:
            return "TAXONOMY_REVISION:" + label
    return "FIRM_RECLASSIFICATION"


def taxonomy_disagreement(smap: "SectorMap", panel_sector: dict) -> dict:
    """How often `crosswalk(GICS today)` disagrees with the PANEL's own sector, today.

    **THE PRICE OF SPEAKING ONE VENDOR'S OPINION IN ANOTHER'S VOCABULARY, and it is not a
    defect.** It is required output because without it a repair that changes a name's sector
    cannot be attributed: the change could be look-ahead being fixed, or it could be the
    taxonomy switch, and those are different things. `PREREG_s25` section 3.
    """
    agree, disagree, uncovered, pairs = 0, 0, 0, {}
    for t, panel in panel_sector.items():
        got = smap.current(t)
        if got["state"] != "OK":
            uncovered += 1
            continue
        if got["sector"] == panel:
            agree += 1
        else:
            disagree += 1
            pairs[(panel, got["sector"])] = pairs.get((panel, got["sector"]), 0) + 1
    n = agree + disagree
    return {"compared": n, "agree": agree, "disagree": disagree,
            "uncovered": uncovered,
            "disagreement_rate": (disagree / n) if n else None,
            "top_pairs": sorted(({"panel": k[0], "gics_crosswalked": k[1], "n": v}
                                 for k, v in pairs.items()),
                                key=lambda r: -r["n"])[:12]}


def load(path: str = "") -> "SectorMap":
    """Read the built map from its JSON artifact."""
    import json
    p = path or default_path()
    with open(p, encoding="utf-8") as fh:
        payload = json.load(fh)
    spans = {t: [tuple(r) for r in v] for t, v in (payload.get("spans") or {}).items()}
    return SectorMap(spans, payload.get("ambiguous") or {},
                     source=payload.get("source", ""),
                     built_utc=payload.get("built_utc", ""))


def default_path() -> str:
    """Where the built map lives -- FOUND, never assumed.

    `DEEPITM-FIN`'s defect: a worktree ships an EMPTY `data/`, which SHADOWS the populated
    primary root, so a path built by string arithmetic resolves to a directory that exists and
    contains nothing. **Existence is not population.** This walks up until it finds the file
    itself and falls back to the nearest `data/free_analysis` so a caller writing a new
    artifact still gets a sane destination.
    """
    d = os.path.dirname(os.path.abspath(__file__))
    fallback = ""
    for _ in range(8):
        cand = os.path.join(d, "data", "free_analysis", "S25_SECTOR_MAP.json")
        if os.path.exists(cand):
            return cand
        if not fallback and os.path.isdir(os.path.join(d, "data", "free_analysis")):
            fallback = cand
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return fallback or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "free_analysis", "S25_SECTOR_MAP.json")
