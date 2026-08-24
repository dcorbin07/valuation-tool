"""
S3-I5 — THE TICKER-REUSE ADJUDICATION. Point-in-time identity for a ticker-year.

FIXED-CLASS: facts, not hypotheses. Zero trials. This module states, for a given (ticker, year),
whether the data under that symbol belongs to the company the panel means. It scores nothing.

--------------------------------------------------------------------------------------------
WHY IT BLOCKS THINGS.

The chain harvest stamped 45 units across 26 symbols `pre_panel_history` -- option data for a
year before the panel knew the ticker -- and its handoff says plainly that **nothing built on
Tier C or Tier E is quotable until they are adjudicated**. The flag makes contamination
DETECTABLE; it does not resolve it, and it deliberately over-includes: a December IPO year is
flagged exactly like a wholesale ticker recycle. `SC-3`'s Tier-E strata, `B-14`'s long tenors,
`B-15` and `B-6e` all wait on the difference.

--------------------------------------------------------------------------------------------
THE ANCHOR: `firstpricedate`, AND WHY `permaticker` ALONE WILL NOT DO IT.

The obvious test -- "does this ticker map to two permatickers?" -- FAILS SILENTLY on this data,
and the failure looks like a clean pass. `TICKERS` is a CURRENT snapshot: it carries one row per
ticker per table for the company holding the symbol TODAY, so every one of the 26 returns exactly
one permaticker whether or not the ticker was ever reused. A check built on that would have
reported 26 clean symbols and been wrong about at least nine.

What the snapshot DOES carry is the current holder's **`firstpricedate`** -- the day this company
began trading under this symbol. That is a genuine point-in-time boundary:

    a harvest year entirely BEFORE `firstpricedate` cannot be this company.

Three verdicts follow mechanically, and the middle one is the reason a two-state answer is not
enough:

  * ``SAME_COMPANY``  -- the year starts on or after `firstpricedate`. The `pre_panel_history`
                        flag was a late PANEL debut, not a change of hands.
  * ``REUSED``        -- the whole year predates `firstpricedate`. Another company's data.
  * ``SPLIT_YEAR``    -- `firstpricedate` falls INSIDE the year. Part of that year is this
                        company and part is not, and no row-level filter keyed on the year alone
                        can separate them. A consumer must cut on the date.

--------------------------------------------------------------------------------------------
THREE INDEPENDENT EVIDENCE STREAMS, REPORTED SEPARATELY.

An adjudication that rests on one source is an assertion. Each verdict carries:

  1. **REGISTRY** -- `firstpricedate`, `permaticker`, `name`, `cusips` from `TICKERS`. Decisive
     for the verdict.
  2. **CORPORATE ACTION** -- `listed` / `tickerchangeto` / `tickerchangefrom` / `acquisitionby`
     rows from `ACTIONS`, which NAME the counterparty via `contraticker`/`contraname`. This is
     what turns "not this company" into "it was that one".
  3. **BEHAVIOURAL** -- the median-strike step across the boundary, reusing
     `ticker_reuse_audit.py`'s method (the discriminator that confirmed the WBD/DISCA
     contamination). A price level cannot be faked by a ticker string.

**Where they disagree, the disagreement is RECORDED, not resolved by preference.** The strike
test asks "is the underlying continuous?" and the registry asks "is it the same registrant?" --
different questions with genuinely different answers at a restructuring, where a continuous
business is re-registered as a new entity. Collapsing them would throw away the only signal that
a case is subtle.
"""
from __future__ import annotations

import collections
import csv
import datetime as dt
import json
import os
from typing import Optional

SAME_COMPANY = "SAME_COMPANY"
REUSED = "REUSED"
SPLIT_YEAR = "SPLIT_YEAR"
UNKNOWN = "UNKNOWN"

#: `ticker_reuse_audit.py`'s threshold, reused rather than re-chosen so the two tools cannot
#: drift into disagreeing about what "a step" means.
STEP_SUSPECT = 1.5

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _rows(path: str, keep_ticker=None):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            if keep_ticker is None or row.get("ticker") in keep_ticker:
                out.append(row)
    return out


def _d(v) -> Optional[dt.date]:
    if not v:
        return None
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


class IdentityTable:
    """The adjudicated table. Consumers read THIS, never a re-derivation."""

    def __init__(self, by_symbol: dict, source: dict = None):
        self.by_symbol = by_symbol
        self.source = source or {}

    # ------------------------------------------------------------------ the resolver API
    def verdict(self, ticker: str, year: int) -> str:
        """Point-in-time verdict for one ticker-year.

        Returns UNKNOWN for a symbol the table has never adjudicated -- never SAME_COMPANY.
        That direction matters: this whole instrument exists because a fail-open default turns
        an unexamined symbol into an implicit clean bill of health, which is exactly what the
        `pre_panel_history` flag was invented to stop.
        """
        rec = self.by_symbol.get(str(ticker).upper())
        if not rec:
            return UNKNOWN
        fpd = _d(rec.get("firstpricedate"))
        if fpd is None:
            return UNKNOWN
        y = int(year)
        if fpd <= dt.date(y, 1, 1):
            return SAME_COMPANY
        if fpd > dt.date(y, 12, 31):
            return REUSED
        return SPLIT_YEAR

    def usable_from(self, ticker: str, year: int) -> Optional[str]:
        """The first date in `year` whose rows belong to the panel's company.

        `None` when the whole year is unusable (REUSED) or unknown. For a SPLIT_YEAR this is the
        cut a consumer must apply -- the reason SPLIT_YEAR is its own verdict rather than being
        rounded to either neighbour.
        """
        v = self.verdict(ticker, year)
        if v == SAME_COMPANY:
            return f"{int(year)}-01-01"
        if v == SPLIT_YEAR:
            return self.by_symbol[str(ticker).upper()]["firstpricedate"]
        return None

    def evidence(self, ticker: str) -> dict:
        return dict(self.by_symbol.get(str(ticker).upper(), {}))

    def to_json(self, path: str) -> dict:
        payload = {
            "instrument": "S3-I5",
            "class": "FIXED - facts, not hypotheses",
            "trials": 0,
            "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "anchor": ("TICKERS.firstpricedate -- the day the CURRENT holder began trading "
                       "under this symbol. A year entirely before it cannot be this company."),
            "why_not_permaticker": (
                "TICKERS is a CURRENT snapshot: one row per ticker per table for today's holder, "
                "so every symbol returns exactly one permaticker whether or not it was reused. A "
                "distinct-permaticker check reports a clean pass on a reused ticker."),
            "verdicts": {SAME_COMPANY: "year starts on/after firstpricedate",
                         REUSED: "whole year predates firstpricedate",
                         SPLIT_YEAR: "firstpricedate falls inside the year; cut on the date",
                         UNKNOWN: "not adjudicated -- never treat as SAME_COMPANY"},
            "source": self.source,
            "symbols": self.by_symbol,
        }
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
        return payload

    @classmethod
    def from_json(cls, path: str) -> "IdentityTable":
        with open(path, encoding="utf-8") as fh:
            p = json.load(fh)
        return cls(p["symbols"], p.get("source", {}))


# ---------------------------------------------------------------------------------- build
def build(symbols, tickers_csv: str, actions_csv: str = "",
          strike_fn=None, flagged_years: dict = None) -> IdentityTable:
    """Adjudicate `symbols` from the registry, corporate actions and (optionally) strike levels.

    `strike_fn(sym, year) -> float|None` is injected rather than imported so this module has no
    dependency on the option cache: the registry verdict must be computable with no chains on
    disk, and behavioural evidence is corroboration, not the verdict.
    """
    syms = {str(s).upper() for s in symbols}
    reg = collections.defaultdict(list)
    for row in _rows(tickers_csv, syms):
        reg[row["ticker"]].append(row)
    acts = collections.defaultdict(list)
    if actions_csv:
        for row in _rows(actions_csv, syms):
            if row.get("action") in ("listed", "delisted", "tickerchangeto", "tickerchangefrom",
                                     "acquisitionby", "acquisitionof", "regulatorydelisting"):
                acts[row["ticker"]].append(row)

    out = {}
    for s in sorted(syms):
        rs = reg.get(s, [])
        rec = {"symbol": s, "registry_rows": len(rs)}
        if not rs:
            rec.update({"firstpricedate": None,
                        "note": "absent from TICKERS -- cannot adjudicate, stays UNKNOWN"})
            out[s] = rec
            continue
        # every table (SEP/SF1/SF2) agrees on the identity fields; take the earliest listed date
        # and record whether they ever disagree rather than assuming they do not
        fpds = sorted({r.get("firstpricedate") for r in rs if r.get("firstpricedate")})
        perms = sorted({r.get("permaticker") for r in rs})
        names = sorted({r.get("name") for r in rs})
        rec.update({
            "permaticker": perms[0] if len(perms) == 1 else perms,
            "permaticker_disagreement": len(perms) > 1,
            "current_name": names[0] if len(names) == 1 else names,
            "firstpricedate": fpds[0] if fpds else None,
            "firstpricedate_disagreement": len(fpds) > 1,
            "lastpricedate": sorted({r.get("lastpricedate") for r in rs if r.get("lastpricedate")})[-1:] or None,
            "isdelisted": sorted({r.get("isdelisted") for r in rs}),
            "cusips": sorted({r.get("cusips") for r in rs if r.get("cusips")}),
            "tables": sorted({r.get("table") for r in rs}),
        })
        ev = []
        for a in sorted(acts.get(s, []), key=lambda r: r.get("date") or ""):
            ev.append({"date": a.get("date"), "action": a.get("action"),
                       "name": a.get("name"), "contraticker": a.get("contraticker"),
                       "contraname": a.get("contraname")})
        rec["corporate_actions"] = ev
        # the predecessor, when ACTIONS names one
        prior = [e for e in ev if e["action"] == "tickerchangefrom" and e.get("contraname")]
        rec["predecessor_named_by_actions"] = prior[-1] if prior else None
        # CROSS-TABLE CONTROL. ACTIONS and TICKERS are separate Sharadar tables built from
        # different feeds, so a `listed` row landing on the same day as `firstpricedate` is an
        # independent confirmation of the boundary the whole verdict turns on -- not a
        # restatement of it. Recorded per symbol so the agreement RATE is a measured fact
        # rather than an assumption that the two tables always concur.
        listed = [e["date"] for e in ev if e["action"] == "listed" and e.get("date")]
        rec["actions_listed_dates"] = listed
        rec["listed_matches_firstpricedate"] = (
            bool(listed) and rec.get("firstpricedate") in listed)
        out[s] = rec

    # ------------------------------------------------------- per-year verdicts + behavioural
    tbl = IdentityTable(out, source={"tickers_csv": os.path.basename(tickers_csv),
                                     "actions_csv": os.path.basename(actions_csv or "")})
    for s, rec in out.items():
        years = sorted((flagged_years or {}).get(s, []))
        rec["flagged_years"] = years
        rec["year_verdicts"] = {str(y): tbl.verdict(s, y) for y in years}
        rec["usable_from"] = {str(y): tbl.usable_from(s, y) for y in years}
        if strike_fn and years:
            fpd = _d(rec.get("firstpricedate"))
            before, after = [], []
            if fpd:
                for y in range(min(years) - 1, fpd.year + 3):
                    v = strike_fn(s, y)
                    if v is None:
                        continue
                    (before if y < fpd.year else after).append((y, v))
            rec["strike_before"] = before
            rec["strike_after"] = after
            step = None
            if before and after:
                lo = sorted(v for _, v in before)[len(before) // 2]
                hi = sorted(v for _, v in after)[len(after) // 2]
                if lo and hi:
                    step = round(max(lo, hi) / min(lo, hi), 2)
            rec["strike_step"] = step
            rec["behavioural"] = (None if step is None else
                                  ("STEP" if step >= STEP_SUSPECT else "CONTINUOUS"))
            # THE STRIKE TEST IS ONE-SIDED EVIDENCE AND MUST NOT BE READ AS TWO-SIDED.
            # A LARGE step corroborates a change of hands: two companies at very different price
            # levels cannot be one continuous underlying. A SMALL step proves nothing either way
            # -- unrelated companies routinely trade at similar prices, so `CONTINUOUS` here means
            # "this test found nothing", not "the registry is wrong". SE is the live example:
            # step 1.03 across a boundary where Spectra Energy gave way to Sea Ltd, which is a
            # coincidence of price level and not continuity.
            #
            # So a disagreement NEVER overturns the verdict. It is recorded because the two
            # questions genuinely differ -- the registry asks "same registrant?", the strike test
            # "same underlying?" -- and at a restructuring both answers are honest and opposite.
            regv = {v for v in rec["year_verdicts"].values()}
            rec["evidence_disagreement"] = bool(
                step is not None and rec["behavioural"] == "CONTINUOUS"
                and (REUSED in regv or SPLIT_YEAR in regv))
            rec["disagreement_note"] = ("registry REUSED/SPLIT with no strike step: the "
                                        "behavioural test is one-sided and cannot refute the "
                                        "registry; verdict stands"
                                        ) if rec["evidence_disagreement"] else None
    return tbl
