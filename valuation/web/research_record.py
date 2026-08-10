"""The public research record — what was pre-registered, and how it came out.  [V4]

WHY THIS PAGE EXISTS. Every performance number this project publishes is contestable: it comes
from one panel the model was also tuned on. The METHOD is not contestable in the same way. A
dated register of what was predicted BEFORE the data was looked at, and what the answer turned
out to be — including the many times the answer was "no" — is a stronger credential than any
return figure, because it is the one thing a flattering result cannot be reverse-engineered
into.

SOURCED, NEVER RETYPED. Every row comes from `RESEARCH_LOG.md` through
`valuation.edge.research_log.rows()` — the SAME parse that produces the trial denominator `N`
for the Deflated Sharpe. A page that maintained its own copy of the record would be a second
version of the truth, and this project has shipped that bug twice already (the session-12
`\\bFIXED\\b` grep, and the two forward-track recorders that put a false claim into Discord on
2026-08-05). The pre-registration documents are likewise listed by reading the files.

WHAT MAY BE PUBLISHED, and this is the load-bearing rule. **No performance figures.** Not the
result cells, not the pre-committed thresholds, not the effect sizes quoted in a source note.
The public posture already fixes which figures may appear and where; this page adds none of
them, so it cannot become a back door around that posture as the log grows. Text is passed
through `withhold()`, which replaces anything shaped like a performance figure, and a test
asserts the rendered page contains none. The consequence is deliberate: you can read WHAT was
asked and HOW it came out, and for the number you must go to the surfaces that are allowed to
carry one.

RAW VENDOR DATA NEVER. Vendor NAMES are fine and are part of the record (Sharadar, Tradier,
JKP). The log's `universe` cells — row counts, export sizes, panel dimensions — are vendor
metadata and are not rendered at all.

A REJECTED-HEAVY RECORD IS THE POINT. The counts are shown without apology and the negative
verdicts are not tucked below the positive ones: on this record they are most of it, and a
research log that mostly said "yes" would be evidence of a weaker process, not a stronger one.
"""
from __future__ import annotations

import datetime as _dt
import glob
import os
import re
from typing import Optional

# --------------------------------------------------------------------------- publishing rule
#
# Anything shaped like a performance figure. Deliberately BROAD and deliberately biased toward
# over-withholding: a false positive costs a redacted word in a hypothesis, a false negative
# publishes a number the public posture never approved.
#
#   * a number carrying a performance unit          +7.17%, 134 bps, -2.85 pp, 261%, 3.17x
#   * a named statistic with a value                t 2.62, IC +0.03, Sharpe 1.17, PBO 13.3
#   * money                                         $4.9M, $23M
#   * a bare decimal (every effect size in this log is written as one)
#
# The statistic-name branch REQUIRES a separator — whitespace or an operator — before the
# value. Without that, `P4`, `P10-b` and `P6-1` (row IDs, which are not figures at all) all
# read as "statistic p, value 4", and the page's own guard would fire on its own identifiers.
# Plain integers are deliberately NOT figures: the record's counts, and the trial denominator
# `N`, are already public and are the honest part of this page.
_FIGURE = re.compile(
    r"""(?xi)
    [-+]?\d[\d,]*\.?\d*\s*(?:%|pp\b|bps\b|bp\b|x\b|/\s*yr\b|/\s*trade\b|σ|sigma)
    | \b(?:t|ic|sharpe|alpha|pbo|dsr)(?:\s+|\s*[-+=<>]\s*)\d
    | \$\s?\d[\d,.]*\s*[kmb]?\b
    | [-+]?\d+\.\d+
    """)

WITHHELD = "[figure withheld]"

# Dates and plain integers are NOT figures and must survive: the record is dated, and the
# counts ("32 rejected") are the honest headline. `_FIGURE` requires a unit, a statistic name,
# a currency mark or a decimal point, so `2026-08-09` and `32` both pass through untouched.
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def withhold(text: str) -> str:
    """Replace anything shaped like a performance figure. Dates and plain counts survive."""
    if not text:
        return ""
    keep = {}                                          # protect dates before the figure sweep

    def _stash(m):
        keep[f"\x00{len(keep)}\x00"] = m.group(0)
        return list(keep)[-1]

    t = _DATE.sub(_stash, str(text))
    t = _FIGURE.sub(WITHHELD, t)
    for k, v in keep.items():
        t = t.replace(k, v)
    return t


def contains_figure(text: str) -> bool:
    """True if `text` would publish a performance figure. Used by the page's own test."""
    return bool(_FIGURE.search(_DATE.sub("", str(text or ""))))


# --------------------------------------------------------------------------- verdicts
#
# Buckets, in the order the page shows them. `other` exists because the log records verdicts
# that are genuinely neither an adoption nor a rejection — `NO CONTRAST` (a design that could
# not separate its arms), `SUPERSEDED`, `REGISTERED` — and flattening those into "rejected"
# would overstate how decisive the record is.
BUCKETS = ("adopted", "rejected", "null", "inconclusive", "fixed", "other")

_BUCKET_OF = {"ADOPTED": "adopted", "REJECTED": "rejected", "NULL": "null",
              "INCONCLUSIVE": "inconclusive", "FIXED": "fixed"}

BUCKET_LABEL = {
    "adopted": "Adopted",
    "rejected": "Rejected",
    "null": "Null",
    "inconclusive": "Inconclusive",
    "fixed": "Defect found and fixed",
    "other": "Other verdict",
}

BUCKET_BLURB = {
    "adopted": "The prediction held on data that did not inform it, and the change shipped.",
    "rejected": "The prediction failed its own pre-committed bar. Nothing shipped.",
    "null": "The result could not be separated from zero. A near miss is a null.",
    "inconclusive": "The design could not answer the question either way — recorded as such "
                    "rather than reported as a result.",
    "fixed": "Not a search over the data but a defect in the machinery, found and repaired. "
             "These do not count toward the multiple-testing denominator.",
    "other": "Verdicts that are genuinely neither adoption nor rejection, kept distinct so the "
             "record does not read as more decisive than it is.",
}


def bucket(verdict: str) -> str:
    v = (verdict or "").strip().upper()
    for k, b in _BUCKET_OF.items():
        if v.startswith(k):
            return b
    return "other"


# --------------------------------------------------------------------------- sources
def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


_MD = re.compile(r"[A-Za-z0-9_./-]+\.md")


def source_file(cell: str) -> str:
    """The document a row cites, WITHOUT its parenthetical result note.

    25 of the log's `source` cells carry effect sizes in parentheses — that is where the
    numbers live, so the cell is never rendered whole. The filename alone is what a reader
    needs to know the claim is written down somewhere specific.
    """
    m = _MD.search(cell or "")
    if m:
        return m.group(0)
    return withhold((cell or "").split("(")[0].strip())[:60]


# One line, for a reader who has never heard the term. Required by the V4 spec; kept to one
# sentence on purpose, because the page's job is to show the record, not to teach statistics.
PREREGISTRATION_SENTENCE = (
    "Pre-registration means the question, the measurement and the pass/fail line were written "
    "down and committed before the data was looked at — so a result cannot be turned into a "
    "success after the fact by moving the target."
)


def preregistrations(root: str = None) -> list:
    """The registers on disk — the documents that fixed a question before it was measured.

    Read from the files rather than listed by hand, so a register that is added and never
    mentioned here still appears, and one that is deleted stops appearing.

    NO DATE IS SHOWN, on purpose. The obvious implementation — scrape the first ISO date out of
    the document — gave `PREREG_free_analysis.md` a registration date of 1998-01-01, which is a
    date appearing in its *contents*. A registration date is the one field on this page where a
    wrong value would undermine the exact claim the page is making, so it is not guessed: the
    dates that ARE shown are the log rows', which record when each verdict was entered.
    """
    root = root or _repo_root()
    out = []
    names = sorted(glob.glob(os.path.join(root, "PREREG_*.md")))
    for extra in ("PAPER_TRACK_CONTRACT.md", "VALQUO_EXTENSIONS.md"):
        p = os.path.join(root, extra)
        if os.path.exists(p):
            names.append(p)
    for p in names:
        title = ""
        try:
            with open(p, encoding="utf-8") as f:
                head = f.read(4000)
        except OSError:
            continue
        for line in head.splitlines():
            s = line.strip()
            if s.startswith("# "):
                title = s[2:].strip()
                break
        out.append({"file": os.path.basename(p),
                    "title": withhold(title) or os.path.basename(p)})
    return sorted(out, key=lambda r: r["file"])


# --------------------------------------------------------------------------- the record
def record(log_path: str = None, root: str = None) -> dict:
    """Everything the page renders. Composes; computes no research result of its own."""
    from ..edge import research_log as RL

    raw = RL.rows(path=log_path)
    items = []
    for r in raw:
        b = bucket(r.get("verdict"))
        items.append({
            "id": r.get("id") or "",
            "date": (r.get("date") or "").strip(),
            "domain": (r.get("domain") or "").strip().lower(),
            # `pre` is only present on the retrospective table. Absent means the row does not
            # record it, which is NOT the same as "not pre-registered" — said plainly rather
            # than defaulted to the flattering reading.
            "pre": (r.get("pre") or "").strip().lower(),
            "hypothesis": withhold(r.get("hypothesis")),
            "verdict": withhold(r.get("verdict")) or "—",
            "bucket": b,
            "source": source_file(r.get("source")),
        })

    counts = {b: sum(1 for i in items if i["bucket"] == b) for b in BUCKETS}
    negative = counts["rejected"] + counts["null"] + counts["inconclusive"]
    searches = sum(1 for i in items if i["bucket"] != "fixed")

    # Newest first: the record reads as a running log, and the most recent entries are the ones
    # a reader can check against the repository as it stands today.
    items.sort(key=lambda i: (i["date"] or "", i["id"]), reverse=True)

    return {
        "items": items,
        "counts": counts,
        "buckets": BUCKETS,
        "bucket_label": BUCKET_LABEL,
        "bucket_blurb": BUCKET_BLURB,
        "total": len(items),
        "searches": searches,
        "negative": negative,
        "preregistrations": preregistrations(root),
        "prereg_sentence": PREREGISTRATION_SENTENCE,
        "log_file": "RESEARCH_LOG.md",
        "as_of": _dt.date.today().isoformat(),
    }
