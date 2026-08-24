"""
S3-I2 — THE CATALYST CALENDAR. Forward-only, free tier, one canonical table.

COLLECTION-AND-PROVENANCE. Zero trials. Scores nothing, predicts nothing, adopts nothing.

--------------------------------------------------------------------------------------------
THE HONEST NOTE, FIRST, BECAUSE IT BOUNDS EVERYTHING BELOW.

**This table has no history and cannot be given one.** It records what a free surface published
ON THE DAY WE ASKED. Every row is stamped with the moment it was observed, snapshots are
APPEND-ONLY, and nothing is ever rewritten. So the usable record starts the day the first
snapshot lands and accrues forward at one day per day: **the earliest honest event-study on this
data is roughly a year out, by construction.** That is a property of the instrument, not a
shortfall in it, and any consumer that wants a longer history has to buy one.

**NEVER BACKFILLED FROM MEMORY.** Not from the model's knowledge of when a PDUFA date was, not
from a remembered Russell reconstitution schedule, not from a plausible reconstruction. A row
exists only if a fetch produced it, and `add_snapshot` REFUSES rows whose `source_id` has no
fetch record in the same snapshot. That refusal is the mechanism; the sentence above is only its
description.

--------------------------------------------------------------------------------------------
FAIL-CLOSED ON PRECISION — the biggest trap in this data, measured not assumed.

The free FDA surface publishes a `date` field for every event, and **most of those are not
dates.** Measured on the first live pull, 2026-08-23: of 452 events, **124 carry day precision,
270 are month-precision and 58 quarter-precision.** A consumer reading `date` as a day would
silently acquire a 270-row phantom calendar of events that are only known to a month.

So precision is a first-class field and `usable_date()` returns `None` for anything coarser than
a day. `IMPRECISE` is its own state, never rounded to the first of the month -- rounding invents
a day the source never published, which is backfilling from inference rather than from memory
and is no better for it.

--------------------------------------------------------------------------------------------
SOURCES: NAMED, LICENSED, AND RECORDED WHEN THEY FAIL.

A source that could not be reached is recorded with its failure, not omitted. An absent source
and an empty source are different facts, and a table that cannot tell them apart will read as
"no catalysts" on the day a scraper silently breaks -- the fail-open shape this project has paid
for repeatedly.

`STATUS_BLOCKED` in particular means *we did not have permission to look*, which is a different
statement from *we looked and found nothing*, and it is the reason the index-reconstitution half
of this instrument ships as BLOCKED rather than as an empty table.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import os
import ssl
import urllib.error
import urllib.request
from typing import Optional

# ---------------------------------------------------------------------------- precision states
DAY = "day"
IMPRECISE = "IMPRECISE"          # month- or quarter-precision: real event, not a date
UNKNOWN_PRECISION = "UNKNOWN"

# ---------------------------------------------------------------------------- source states
STATUS_OK = "OK"
STATUS_UNREACHABLE = "UNREACHABLE"   # network/TLS failure; we tried and could not connect
STATUS_BLOCKED = "BLOCKED"           # permission could not be established; we did NOT scrape
STATUS_EMPTY = "EMPTY"               # reached, parsed, zero rows -- a real observation

USER_AGENT = ("Mozilla/5.0 (compatible; ValquoResearchBot/1.0; "
              "+mailto:donniecorbin6@gmail.com)")

#: Every surface this instrument is allowed to touch, with why it is allowed.
#: A source is added here with its robots position stated, or it is not fetched.
SOURCES = {
    "pdufa_bio_events": {
        "name": "pdufa.bio",
        "url": "https://www.pdufa.bio/api/v1/events",
        "kind": "FDA",
        "robots": "explicitly Allow: /api/v1/ (while /api/ is disallowed) as of 2026-08-23",
        "license": ("Attribution + link-back required; facts and historical statistics only. "
                    "Carried per row in `license` and reproduced in the artifact."),
        "attribution": "https://www.pdufa.bio/",
    },
    "sp_index_announcements": {
        "name": "S&P Dow Jones Indices — index announcements",
        "url": "https://www.spglobal.com/spdji/en/index-news-and-announcements/",
        "kind": "INDEX_RECONSTITUTION",
        "robots": ("UNDETERMINABLE: https://www.spglobal.com/robots.txt returns HTTP 403, so "
                   "crawl permission cannot be established. Not fetched."),
        "license": "unknown — not fetched",
        "preset_status": STATUS_BLOCKED,
    },
    "ftse_russell_recon": {
        "name": "FTSE Russell — reconstitution calendar",
        "url": "https://www.ftserussell.com/",
        "kind": "INDEX_RECONSTITUTION",
        "robots": ("UNDETERMINABLE: /robots.txt soft-404s to an HTML page rather than serving a "
                   "robots file. Not fetched."),
        "license": "unknown — not fetched",
        "preset_status": STATUS_BLOCKED,
    },
}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fetch(source_id: str, timeout: int = 30) -> dict:
    """Fetch one source. ALWAYS returns a record -- success and failure are both observations."""
    src = SOURCES[source_id]
    rec = {"source_id": source_id, "url": src["url"], "fetched_utc": _now(),
           "robots": src.get("robots"), "license": src.get("license")}
    if src.get("preset_status"):
        rec.update({"status": src["preset_status"], "http": None, "sha256": None,
                    "note": "not fetched — see `robots`"})
        return rec
    try:
        req = urllib.request.Request(src["url"], headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout,
                                    context=ssl.create_default_context()) as r:
            body = r.read()
            rec.update({"status": STATUS_OK, "http": r.status, "bytes": len(body),
                        "sha256": _sha(body)})
            rec["_body"] = body
    except Exception as e:                                              # noqa: BLE001
        rec.update({"status": STATUS_UNREACHABLE, "http": None, "sha256": None,
                    "error": f"{type(e).__name__}: {str(e)[:200]}"})
    return rec


def parse_pdufa_bio(body: bytes) -> tuple:
    """(rows, meta) from pdufa.bio's v1 payload. Precision is carried, never normalised away."""
    d = json.loads(body.decode("utf-8", "replace"))
    meta = d.get("meta", {})
    rows = []
    for x in d.get("data", []):
        prec = (x.get("date_precision") or "").lower()
        rows.append({
            "source_id": "pdufa_bio_events",
            "source_row_id": x.get("id"),
            "ticker": (x.get("ticker") or "").upper() or None,
            "company": x.get("company"),
            "event_type": x.get("type"),
            "event_name": x.get("name"),
            "date_raw": x.get("date"),
            "precision": DAY if prec == "day" else (
                IMPRECISE if prec in ("month", "quarter") else UNKNOWN_PRECISION),
            "precision_raw": prec or None,
            "status": x.get("status"),
            "url": x.get("url"),
            "source_updated_at": x.get("updated_at"),
        })
    return rows, {"as_of": meta.get("as_of"), "total": meta.get("total"),
                  "returned": meta.get("returned"), "license": meta.get("license"),
                  "request_id": meta.get("request_id"), "tier": meta.get("tier")}


PARSERS = {"pdufa_bio_events": parse_pdufa_bio}


class CatalystCalendar:
    """Append-only snapshots. What was known, and when we knew it."""

    def __init__(self, snapshots=None):
        self.snapshots = list(snapshots or [])

    # ------------------------------------------------------------------ writing
    def add_snapshot(self, fetches: list, rows: list, observed_utc: str = "") -> dict:
        """Append one observation. REFUSES any row whose source has no fetch record here.

        This is the enforcement of "never backfilled from memory". A row can only enter the
        table attached to a fetch that happened in the same snapshot, so there is no code path
        by which a remembered date, a reconstructed schedule, or a hand-typed correction becomes
        a row. It raises rather than dropping, because a silently discarded row is how a partial
        write looks like a complete one.
        """
        have = {f["source_id"] for f in fetches}
        orphan = sorted({r.get("source_id") for r in rows} - have)
        if orphan:
            raise ValueError(
                f"rows cite sources with no fetch record in this snapshot: {orphan}. "
                f"Every row must be attached to an observation -- this table is never "
                f"backfilled from memory, inference or a previous run.")
        ok = {f["source_id"] for f in fetches if f["status"] == STATUS_OK}
        bad = sorted({r.get("source_id") for r in rows} - ok)
        if bad:
            raise ValueError(f"rows cite sources whose fetch did not succeed: {bad}")
        snap = {
            "observed_utc": observed_utc or _now(),
            "fetches": [{k: v for k, v in f.items() if k != "_body"} for f in fetches],
            "n_rows": len(rows),
            "rows": rows,
        }
        self.snapshots.append(snap)
        return snap

    # ------------------------------------------------------------------ reading
    def latest(self) -> Optional[dict]:
        return self.snapshots[-1] if self.snapshots else None

    def usable_date(self, row: dict) -> Optional[str]:
        """The event's DAY, or None. Never a rounded month or quarter.

        Rounding an imprecise date to the first of the month invents a day the source never
        published. That is backfilling from inference rather than from memory, and it is no
        better for being arithmetic.
        """
        if row.get("precision") != DAY:
            return None
        return row.get("date_raw") or None

    def forward_rows(self, as_of: str = "", usable_only: bool = True) -> list:
        """Rows dated strictly after `as_of`. Forward-only is the point of the instrument."""
        snap = self.latest()
        if not snap:
            return []
        cut = (as_of or dt.date.today().isoformat())[:10]
        out = []
        for r in snap["rows"]:
            d = self.usable_date(r) if usable_only else r.get("date_raw")
            if d and d > cut:
                out.append(r)
        return out

    def coverage(self) -> dict:
        """What this snapshot actually contains — precision and source states, never a total."""
        snap = self.latest()
        if not snap:
            return {"snapshots": 0, "note": "no observation yet — NOT 'no catalysts'"}
        prec = collections.Counter(r.get("precision") for r in snap["rows"])
        kinds = collections.Counter(r.get("event_type") for r in snap["rows"])
        src = {f["source_id"]: f["status"] for f in snap["fetches"]}
        usable = [r for r in snap["rows"] if self.usable_date(r)]
        return {
            "snapshots": len(self.snapshots),
            "observed_utc": snap["observed_utc"],
            "n_rows": snap["n_rows"],
            "by_precision": dict(prec),
            "by_event_type": dict(kinds),
            "n_day_precision": len(usable),
            "n_imprecise": snap["n_rows"] - len(usable),
            "source_status": src,
            "sources_blocked": sorted(k for k, v in src.items() if v == STATUS_BLOCKED),
            "sources_unreachable": sorted(k for k, v in src.items()
                                          if v == STATUS_UNREACHABLE),
            "n_tickers": len({r.get("ticker") for r in snap["rows"] if r.get("ticker")}),
        }

    # ------------------------------------------------------------------ persistence
    def save(self, path: str) -> dict:
        payload = {
            "instrument": "S3-I2",
            "class": "collection-and-provenance",
            "trials": 0,
            "forward_only": True,
            "history_note": (
                "This table has NO history and cannot be given one. It records what a free "
                "surface published on the day we asked; snapshots are append-only and nothing "
                "is ever rewritten. The usable record starts at the first snapshot and accrues "
                "one day per day — the earliest honest event-study is ~1 year out."),
            "never_backfilled": (
                "A row exists only if a fetch produced it. add_snapshot() REFUSES rows whose "
                "source has no successful fetch record in the same snapshot."),
            "precision_rule": (
                "Only day-precision rows have a usable date. Month and quarter precision are "
                "IMPRECISE and never rounded — rounding invents a day the source never gave."),
            "sources": {k: {kk: vv for kk, vv in v.items() if kk != "preset_status"}
                        for k, v in SOURCES.items()},
            "snapshots": self.snapshots,
        }
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
        os.replace(tmp, path)
        return payload

    @classmethod
    def load(cls, path: str) -> "CatalystCalendar":
        if not os.path.exists(path):
            return cls([])
        with open(path, encoding="utf-8") as fh:
            return cls(json.load(fh).get("snapshots", []))
