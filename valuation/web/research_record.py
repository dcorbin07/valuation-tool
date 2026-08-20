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
    """True if `text` would publish a performance figure. Used by the page's own test.

    ONE EXEMPTION, AND IT IS NARROWER THAN IT LOOKS.  [MB38]

    A multiplicity hurdle is a bare decimal, so `_FIGURE`'s effect-size branch redacts it —
    measured before any of `MB38`'s copy was written, which is what its kill condition asks
    for. But `sqrt(2 * ln N)` is not a performance figure in the sense this rule exists to
    stop: it is arithmetic on a count of this project's own decisions, it carries no vendor
    data, and it says nothing whatever about how the strategy performed. Two different
    numbers were being caught by one pattern.

    So the guard is made PRECISE rather than weaker. It still fires on every `_FIGURE` match
    it ever fired on, with exactly one exception: a match that is, character for character,
    a hurdle DERIVABLE FROM THE REGISTER RIGHT NOW. Three properties make that hole
    measurable rather than a matter of trust:

      * it is DERIVED, never typed, so it cannot be a literal that rots (`derived_hurdles()`
        reads `research_log`, the same parse that sets the Deflated Sharpe's denominator);
      * it is EMPTY when the register cannot be read, so a broken parse CLOSES the guard
        rather than opening it;
      * it matches WHOLE `_FIGURE` MATCHES, not substrings, so `13.3031` still fires (it is
        a different number), `3.3031%` still fires (the percent branch matches the unit with
        it, and a percentage is a performance figure whatever its digits), and `t 3.3031`
        still fires (the statistic-name branch matches `t 3`). Naming it as a statistic is
        enough to bring it back under the rule.

    `withhold()` deliberately does NOT get this exemption. It is the redactor for text this
    page does not own — log rows, register titles — and it stays maximally conservative
    there. The exemption belongs only to the question "would this publish a performance
    figure", asked of the page's own rendered output, where the hurdle is a value the page
    itself derived a moment earlier.
    """
    t = _DATE.sub("", str(text or ""))
    exempt = derived_hurdles()
    for m in _FIGURE.finditer(t):
        if m.group(0).strip() not in exempt:
            return True
    return False


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


# --------------------------------------------------------------------------- the denominator
#
# MB38. The register already ships; what nobody publishes is the DENOMINATOR — an honest count
# of how many things a research project tried, the multiplicity hurdle that count implies, and
# whether its own headline clears it. All three are computed here; none is typed.
#
# THE TWO OPERANDS STAY WITHHELD AND THE COMPARISON DOES NOT. The headline statistic and the
# calibrated floor live below as module constants because the page needs to COMPARE against
# them, and a comparison whose operands are invented is worthless. They are never placed in
# the payload and never rendered — pinned by test, which is the only form of "withheld" worth
# anything. Knowing a statistic falls short of a published hurdle bounds it from above; it
# does not give you its value, and that asymmetry is stated on the page rather than glossed.
#
# Both constants are already public in this repository's own record (`CLAUDE.md`, MIT, public
# since 2026-08-16). The rule MB38 respects is about what the SITE publishes, not about what
# the source contains — so quoting them here is not the leak; rendering them would be.

# The long-short spread's autocorrelation-corrected t-statistic (R9 made the HAC figure the
# one this project quotes; R4 compared it to the hurdle for the first time). NEVER RENDERED.
HEADLINE_STATISTIC = 2.6199121240414884

# X7's calibrated floor for the same statistic: the 95th percentile of what came back when
# 100 deliberately worthless signals were pushed through the identical pipeline. Re-derived at
# N = 224 by MA19 and unmoved at every N this project has run. NEVER RENDERED.
PLACEBO_FLOOR = 2.2837

HEADLINE_LABEL = ("the long-short spread's t-statistic, corrected for the autocorrelation "
                  "the record measured in it")

MULTIPLICITY_HEADING = "How many things we tried, and what that count demands"

MULTIPLICITY_LEDE = (
    "Every result should be read against the number of things that were tried to get it. "
    "Almost no research record publishes that number. This one does. One entry in the log "
    "can be worth more than one trial: a test that swept a grid of settings is charged "
    "once for every setting, which is why the total below is larger than the number of "
    "entries above it.")

MULTIPLICITY_PARAGRAPH = (
    "Trying many things and keeping the best inflates the winner by luck alone, so the "
    "standard correction asks the winner to clear a bar that grows with the size of the "
    "search. The counts above are not a summary written by hand: they come out of the log on "
    "this page, through the same parse that sets the trial count inside the model's own "
    "significance correction, so the two cannot drift apart. The bar is arithmetic on the "
    "count, and it only ever rises as the search gets bigger.")

MULTIPLICITY_BOTH_SIDES = (
    "There is a second bar, and the record holds both against the same statistic rather than "
    "quoting whichever is kinder. The second one was measured instead of assumed: a hundred "
    "deliberately worthless signals were pushed through the identical pipeline, and the bar "
    "was set where only the luckiest one in twenty of them reached. A bar calibrated that way "
    "answers a different question from a bar derived by counting — how far noise gets on this "
    "data, rather than how far the best of many attempts should be expected to get — and the "
    "two can disagree about the same number.")

MULTIPLICITY_CAVEAT = (
    "The registered argument against the strict reading, stated once and not argued: the "
    "trial-counting hurdle prices the best of N attempts, and the model that is deployed is "
    "not the best of anything — its weights are flat, chosen in advance and never tuned — so "
    "the trials counted here are overwhelmingly alternatives that were rejected, not "
    "candidates it beat.")

MULTIPLICITY_WHY_PUBLISHABLE = (
    "This page carries no performance figures, and these are not an exception to that. A "
    "trial count is a count of this project's own decisions, not a derivation of anyone's "
    "market data, and the bar is arithmetic on that count. The statistic they are about is "
    "still withheld: knowing that it falls short of the bar puts a ceiling on it and does "
    "not tell you what it is.")

# The verdict WORDS. Chosen so neither reads as a number and neither reads as a boast.
VERDICT_FAIL = "does not clear it"
VERDICT_PASS = "clears it"

_HURDLE_CACHE = {}


def multiplicity(log_path: str = None) -> dict:
    """N by domain, the hurdle that count implies, and the verdict WORD.  [MB38]

    DERIVED AT RENDER, EVERY TIME. The audit that proposed this item quoted 549 trials at a
    hurdle of 3.3031; measured on the day it was built the register read 551, and the options
    count it quoted was wrong by two. A hard-coded count on a public page goes stale inside a
    week of ordinary work, and a stale denominator makes a claim about multiplicity that is
    itself untrue.

    The hurdle is NOT computed here. `sqrt(2 * ln N)` is written exactly once in the shipped
    package, in `statistics.hlz_hurdle` — MA5's rule, which exists because the same idea
    written four times is how a hard-coded 3.0 (that expression frozen at N = 90) survived in
    three of them.

    FAILS CLOSED. Any failure to read the register returns `available: False` with no numbers,
    so the section renders nothing rather than rendering something wrong — and the guard's
    exemption is empty in exactly the same case.
    """
    out = {"available": False, "reason": "the research log could not be read",
           "equity": None, "options": None, "infra": None, "trials": None,
           "hurdle": None, "hurdle_text": None, "hurdle_n": None,
           "verdict": None, "placebo_verdict": None}
    try:
        from ..edge import research_log as RL
        from ..edge.statistics import hlz_hurdle

        d = RL.detail(path=log_path)
        by = d.get("by_domain") or {}
        eq = int(by.get("equity") or 0)
        if eq <= 0:
            out["reason"] = "the register reports no equity trials"
            return out
        op = int(by.get("options") or 0)
        inf = int(by.get("infra") or 0)
        total = int(d.get("trials_logged") or (eq + op + inf))
        h = hlz_hurdle(eq)
        out.update(
            available=True,
            reason="derived from RESEARCH_LOG.md at render time",
            equity=eq, options=op, infra=inf, trials=total,
            hurdle=h, hurdle_text=("%.4f" % h), hurdle_n=eq,
            # The comparison is real; its operands are not in this dict and never reach the
            # template. That is what "the statistic stays withheld" means here.
            verdict=(VERDICT_PASS if HEADLINE_STATISTIC > h else VERDICT_FAIL),
            placebo_verdict=(VERDICT_PASS if HEADLINE_STATISTIC > PLACEBO_FLOOR
                             else VERDICT_FAIL),
        )
    except Exception:                                  # noqa: BLE001 — fail closed, always
        return out
    return out


def derived_hurdles() -> frozenset:
    """The hurdle strings the page may render right now — the guard's ONE exemption.  [MB38]

    Derived from the live register, cached because the rendered-page test asks the guard
    about every line of the page. Empty when the register cannot be read, so a parse failure
    closes the guard instead of opening it.
    """
    if "texts" not in _HURDLE_CACHE:
        m = multiplicity()
        _HURDLE_CACHE["texts"] = (frozenset({m["hurdle_text"]})
                                  if m.get("available") and m.get("hurdle_text")
                                  else frozenset())
    return _HURDLE_CACHE["texts"]


def reset_hurdle_cache() -> None:
    """Drop the memo. For tests that move `N` and re-ask."""
    _HURDLE_CACHE.clear()


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
        # MB38 — the denominator. Note what is NOT here: the statistic the verdict is about.
        "multiplicity": multiplicity(log_path),
        "mult_heading": MULTIPLICITY_HEADING,
        "mult_lede": MULTIPLICITY_LEDE,
        "mult_paragraph": MULTIPLICITY_PARAGRAPH,
        "mult_both_sides": MULTIPLICITY_BOTH_SIDES,
        "mult_caveat": MULTIPLICITY_CAVEAT,
        "mult_why": MULTIPLICITY_WHY_PUBLISHABLE,
    }
