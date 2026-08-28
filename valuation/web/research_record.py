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
    # TWO exemptions now, unioned. SC-1 adds the calibration section's half-width and its
    # pre-committed ceiling on exactly MB38's terms — derived, empty when unreadable, whole
    # matches only. They are kept as separate sets rather than merged into one because they
    # fail closed independently: a register this page cannot parse must not withdraw the
    # calibration exemption, and a calibration card that goes missing must not withdraw the
    # hurdle's.
    exempt = derived_hurdles() | derived_calibration_figures()
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
        texts = set()
        m = multiplicity()
        # FAILS CLOSED AS A UNIT, AND THIS IS TIGHTER THAN IT WAS.  [SC-4]
        #
        # SC-4 added a second contributor to this set and, in doing so, broke the property the
        # first one was built for: with the level unavailable, the motion block still read the
        # register on its own and re-opened the hole. MB38's own fail-closed test caught it.
        #
        # The repair is to close on the WEAKER of the two rather than to teach the test about
        # the new source. Both read the same file, so a register the level cannot parse is not
        # one the motion may parse either, and requiring both is the conservative direction:
        # the cost of being wrong here is an over-redacted page, and the cost of the other
        # direction is a published figure nobody approved.
        if not (m.get("available") and m.get("hurdle_text")):
            _HURDLE_CACHE["texts"] = frozenset()
            return _HURDLE_CACHE["texts"]
        texts.add(m["hurdle_text"])
        # SC-4 widens this from ONE string to at most SIX — three books, each before and
        # after. The widening was measured before the copy was written, and the measurement is
        # pinned by test rather than described: over every trial count from 2 to 1200, exactly
        # ten hurdle strings collide with something the register itself writes as a whole
        # figure. Eight of the ten are this project's OWN earlier hurdles, quoted in the log,
        # which is a collision between a hurdle and a hurdle. One is not: at 225 equity trials
        # the bar reads the same as an autocorrelation-corrected t recorded elsewhere in the
        # log.
        #
        # THAT COLLISION IS SAFE, AND SAYING WHY IS THE POINT. The exemption does not publish
        # anything — `withhold()` never consults it, so every log row is redacted exactly as
        # before. It only tells the page's own test that a string it is looking at is a bar
        # rather than a result. A reader who sees that string sees it labelled as the bar at
        # 225 trials, and learns nothing whatever about the unrelated t that shares its value.
        #
        # The set is bounded to the strings the page is ACTUALLY rendering right now, not to a
        # range of counts it might one day render, so it is as small as the page allows.
        w = weekly()
        if w.get("available"):
            texts.update(w.get("hurdle_texts") or ())
        _HURDLE_CACHE["texts"] = frozenset(texts)
    return _HURDLE_CACHE["texts"]


def reset_hurdle_cache() -> None:
    """Drop the memo. For tests that move `N` and re-ask."""
    _HURDLE_CACHE.clear()


# ------------------------------------------------------------------- SC-4: the record's motion
#
# `MB38` publishes the denominator as a LEVEL: how many things were tried, and what that count
# demands. This publishes its MOTION: what the level did over the last week, which register
# entries moved it, what came back, and whether any calibrated instrument fell due as a result.
#
# WHY MOTION IS THE PART WORTH PUBLISHING. A level can be assembled after the fact by anyone
# willing to count once. A dated diff cannot: it only exists if the record was being kept
# continuously, and it is falsifiable by a reader who comes back next week. That is the whole
# claim this page makes, so it is the one thing worth rendering.
#
# SOURCED FROM THE SAME PARSE AS `N`. Every count, date and verdict below comes out of
# `research_log`, the parse that sets the trial denominator inside the model's own significance
# correction. A DELIBERATE DEVIATION FROM THE ITEM AS PROPOSED: it also named `VALQUO_LEDGER.md`
# as a source. It is not read here. The ledger answers "where do we stand" and the log answers
# "what was searched over the data", and this block is about the search; wiring a second reader
# of the same facts is the defect this module's own docstring already says the project has
# shipped twice. One source, or the counts and the verdicts can drift apart.

#: How far back "this week" reaches, inclusive of today.
WEEK_DAYS = 7

#: How many entries the list shows before trimming. A DISPLAY PARAMETER, not a count derived
#: from the register: it does not move when the record does and it cannot go stale. Named
#: because it must be excluded from the no-typed-count check by IDENTITY rather than by value
#: — on the day this was written the infrastructure book's own "before" count reached 12 and
#: the check fired on this literal, which is a real collision between a derived count and a
#: constant that has nothing to do with it.
WEEK_MAX_ROWS = 12

#: `MB31`'s banked measurement: the margin-to-standard-error ratio of the first placebo draw
#: whose CPCV adopt decision is still to flip. NEVER RENDERED — it is a bare decimal and the
#: guard is right to treat it as one. The trial count it implies is DERIVED from it below and
#: never transcribed, so the two cannot drift.
FLOOR_FLIP_MARGIN_OVER_SE = 3.3191884951841053

WEEK_HEADING = "What the record did this week"

WEEK_LEDE = (
    "The block above is a level: how many things have been tried, and what that count demands "
    "of a result. This one is the same record in motion. It is rebuilt from the register every "
    "time the page is loaded, so it is a claim that can be checked again next week and found "
    "to have moved — which is the part of a research record that cannot be assembled after the "
    "fact.")

WEEK_HURDLE_NOTE = (
    "Each book carries its own count and therefore its own bar, and they are shown apart rather "
    "than pooled: a search of the equity book says nothing about how hard the options book "
    "should have to work. The bar only ever rises, so every entry here makes the standing "
    "results harder to believe rather than easier — which is the direction that makes it worth "
    "publishing.")

WEEK_VERDICT_NOTE = (
    "Verdicts are given as the word that was recorded and nothing more. What each result "
    "actually measured is in the record below; how large it was is not on this page at all.")

WEEK_FLOOR_NOTE = (
    "There is a second family of bars on this project, set by measurement rather than by "
    "counting, and those move in steps rather than continuously — they can only change when a "
    "particular one of the stored comparison runs changes its mind, and that happens at a "
    "count which is known in advance. So it is possible to say now, rather than discover later, "
    "how much further the search can go before they have to be worked out again.")

WEEK_QUIET = (
    "Nothing was added to the register in the last seven days. That is recorded plainly rather "
    "than by the section disappearing: a changelog that renders nothing on a quiet week is "
    "indistinguishable from one that has stopped working.")

WEEK_NOT_A_RESULT = (
    "None of this is a result. It is a count of what was attempted and a record of which way "
    "each attempt came out — reporting only, with no hypothesis, no threshold and no verdict "
    "of its own."
)


#: Phrasing this section may never carry, in three families.  [SC-4]
#:
#: The risk here is not that someone writes a lie. It is SUMMARISATION DRIFT: a changelog of
#: research activity is one careless edit away from reading as a progress report, and a
#: progress report about a research record is a performance claim wearing a process claim's
#: clothes. These are the shapes that edit takes.
#:
#: SCOPED TO THIS SECTION, NOT THE PAGE. `/work/research` renders 200-odd log rows written by
#: other items, and a tuple run across all of them fires on innocent pre-existing prose - the
#: defect `MA28-CARD-UI` names, which `MB38`'s boast check hit on the word "provenance" and
#: `MB11`'s hit on `tradable`. The section this item owns is the section it polices.
#:
#: DELIBERATELY NOT BANNED: "proof" and "will". The floor paragraph has to be able to say that
#: nothing has moved YET and that this is NOT proof it will hold - which is the most important
#: sentence in the block, and a tuple that forbade it would have defeated the item it guards.
#: `MB11`'s rule, restated: ban the CLAIM, never the vocabulary the honest sentence needs.
WEEK_BANNED = (
    # (1) FORECAST — the record's motion said to imply where it is going.
    "on track", "we expect", "expected to", "should improve", "is improving", "trending",
    "momentum is", "getting closer", "closing in", "nearly there", "any week now",
    # (2) PERFORMANCE — a result, an effect size, or a comparison between two of them.
    "outperform", "beat the", "ahead of the market", "returned", "gains", "profit",
    "the edge is real", "proves", "confirms the edge", "validates the strategy",
    "better than the market", "worse than the market",
    # (3) BOAST — the tone this page exists to not have.
    "breakthrough", "world-class", "industry-leading", "unmatched", "unprecedented",
    "remarkable", "extraordinary", "rigorous beyond",
)

#: Named statistics. The section may say a verdict LANDED and give the WORD; naming the
#: quantity is how a comparison gets in without a number attached to it.
WEEK_BANNED_STATISTICS = ("t-statistic", "t-stat", "sharpe", "p-value", "alpha",
                          "information ratio", "effect size", "drawdown")


def week_violations(text: str) -> list:
    """Which banned phrasings appear in `text`. Case-insensitive substring.  [SC-4]"""
    t = (text or "").lower()
    return [b for b in (WEEK_BANNED + WEEK_BANNED_STATISTICS) if b in t]


def floor_flip_n() -> int:
    """The equity trial count at which the measured floors must be worked out again.  [SC-4]

    DERIVED, NEVER TYPED. `MB31` reports this as 247. Transcribing that would put a fourth
    copy of a derived quantity into the tree — the `MA5` defect — and it would rot silently if
    the banked draws were ever re-scored. Here it is recovered from the draw's own recorded
    margin ratio through the ONE hurdle definition, so it is right by construction.
    """
    from ..edge.statistics import hlz_hurdle

    n = 2
    while n < 100000 and hlz_hurdle(n) <= FLOOR_FLIP_MARGIN_OVER_SE:
        n += 1
    return n


def _iso(d):
    try:
        return _dt.date.fromisoformat((d or "").strip())
    except Exception:                                  # noqa: BLE001
        return None


def weekly(log_path: str = None, today=None, days: int = None) -> dict:
    """The register's own motion over the last `days`, derived at render.  [SC-4]

    FAILS CLOSED, like `multiplicity`. Any failure to read the register returns
    `available: False` with no numbers and no hurdle strings, so the section renders nothing
    rather than something wrong — and the guard's exemption stays shut in the same case.
    """
    span = int(days or WEEK_DAYS)
    out = {"available": False, "reason": "the research log could not be read",
           "days": span, "start": None, "end": None, "rows": 0, "charged": 0,
           "domains": [], "verdicts": [], "entries": [], "shown": 0, "hidden": 0,
           "vintages": [], "floor": None, "quiet": False, "hurdle_texts": []}
    try:
        from ..edge import research_log as RL
        from ..edge.statistics import hlz_hurdle

        end = today or _dt.date.today()
        start = end - _dt.timedelta(days=span - 1)
        out.update(start=start.isoformat(), end=end.isoformat())

        live = (RL.detail(path=log_path) or {}).get("by_domain") or {}
        win = []
        after = {}
        for r in RL.rows(path=log_path):
            d = _iso(r.get("date"))
            if d is None:
                continue
            if start <= d <= end:
                win.append((d, r))
            elif d > end:
                # Trials charged on rows dated AFTER the window. `now` is the all-time live
                # count, so without this they would be swept into `before` — see the comment
                # on `before` below. Empty on the live page, where `end` is today.
                dom = (r.get("domain") or "").strip().lower()
                after[dom] = after.get(dom, 0) + int(r.get("n_trials") or 0)
        win.sort(key=lambda p: (p[0], p[1].get("id") or ""), reverse=True)

        charged = {}
        for _, r in win:
            dom = (r.get("domain") or "").strip().lower()
            charged[dom] = charged.get(dom, 0) + int(r.get("n_trials") or 0)

        hurdle_texts = []
        domains = []
        for key, label in (("equity", "Equity"), ("options", "Options"),
                           ("infra", "Infrastructure")):
            now = int(live.get(key) or 0)
            if now <= 0:
                continue
            moved = int(charged.get(key) or 0)
            # `now` is the ALL-TIME live count and `moved` is only what the window carries, so
            # `now - moved` sweeps up rows on BOTH sides of the window. Rows dated after `end`
            # are not "before" anything, and attributing them there overstates the prior book
            # and hands `hlz_hurdle` a count that never existed at that moment.
            #
            # Inert on the live page, where `end` is today and nothing postdates it. It fires
            # whenever `today` is back-dated - which this module supports as a parameter and its
            # own tests use - or whenever a row is logged ahead of the render. Found when an
            # options row dated one day past a fixture's `today` moved that book's `before` from
            # 0 to 2 and silently made a floored bar look defined.
            before = now - moved - int(after.get(key) or 0)
            # A "before" below where the correction is defined is stated as such rather than
            # floored silently — `hlz_hurdle` floors at 2, and a floored bar quoted as a real
            # one would be a number that never existed.
            ok = before >= 2
            b_text = ("%.4f" % hlz_hurdle(before)) if ok else None
            a_text = "%.4f" % hlz_hurdle(now)
            if b_text:
                hurdle_texts.append(b_text)
            hurdle_texts.append(a_text)
            domains.append({
                "key": key, "label": label, "before": before, "now": now, "charged": moved,
                "moved": bool(moved), "hurdle_before": b_text, "hurdle_after": a_text,
                "hurdle_before_defined": ok,
            })

        tally = {}
        for _, r in win:
            b = bucket(r.get("verdict"))
            tally[b] = tally.get(b, 0) + 1
        verdicts = [{"bucket": b, "label": BUCKET_LABEL.get(b, b), "n": tally[b]}
                    for b in BUCKETS if tally.get(b)]

        items = []
        for _, r in win:
            items.append({
                "id": r.get("id") or "",
                "date": (r.get("date") or "").strip(),
                "domain": (r.get("domain") or "").strip().lower(),
                "bucket": bucket(r.get("verdict")),
                "label": BUCKET_LABEL.get(bucket(r.get("verdict")), "Other verdict"),
                "source": source_file(r.get("source")),
                "trials": int(r.get("n_trials") or 0),
            })
        # NO SILENT CAP. The list is trimmed because a busy week runs to dozens of entries and
        # the full record is on this same page — but the number trimmed is rendered, because a
        # truncated list with nothing said about it reads as "that was all of it".
        shown = items[:WEEK_MAX_ROWS]
        hidden = max(0, len(items) - WEEK_MAX_ROWS)

        vints = []
        try:
            from ..edge.track_meter import VINTAGES
            for v in VINTAGES:
                for kind, when in (("opened", v.get("opened")), ("closed", v.get("closed"))):
                    if when and start <= when <= end:
                        vints.append({
                            "n": v.get("vintage"), "event": kind,
                            "date": when.isoformat(), "status": v.get("status"),
                            # Another module's prose, so it goes through the same withholder
                            # every log row does. It carries a construction PARAMETER, which
                            # the rule redacts — over-withholding by design, and left visible
                            # as a redaction rather than special-cased around.
                            "label": withhold(v.get("label")),
                        })
            vints.sort(key=lambda x: (x["date"], x["n"]))
        except Exception:                              # noqa: BLE001
            vints = []

        flip = floor_flip_n()
        n_eq = int(live.get("equity") or 0)
        out["floor"] = {"flip_n": flip, "n": n_eq, "headroom": max(0, flip - n_eq),
                        "due": n_eq >= flip}

        out.update(available=True, reason="derived from RESEARCH_LOG.md at render time",
                   rows=len(win), charged=sum(charged.values()), domains=domains,
                   verdicts=verdicts, entries=shown, shown=len(shown), hidden=hidden,
                   vintages=vints, quiet=(not win),
                   hurdle_texts=sorted(set(hurdle_texts)))
    except Exception:                                  # noqa: BLE001 — fail closed, always
        return {"available": False, "reason": "the research log could not be read",
                "days": span, "start": None, "end": None, "rows": 0, "charged": 0,
                "domains": [], "verdicts": [], "entries": [], "shown": 0, "hidden": 0,
                "vintages": [], "floor": None, "quiet": False, "hurdle_texts": []}
    return out


# ------------------------------------------------------------- S3-I7: the declared books
#
# A pre-registration fixes a QUESTION before the data is looked at. A book declaration fixes a
# PORTFOLIO before the data it will be judged on exists at all -- the rule, the structure, the
# horizon, written down and committed ALONE, and then left alone while the future arrives.
# That is a stronger claim than pre-registration and it is worth showing on its own, because
# the thing a reader can check is not the return: it is the commit.
#
# SO THE SHELF SHOWS PROVENANCE AND NOT PERFORMANCE. No return, no excess, no figure of any
# kind -- `MB38`'s gate governs here exactly as it governs the rest of the page, and a shelf
# that quoted how the books are doing would be the back door around it.
#
# IT READS `S3-I1`'s FORMAT, NOT ONE OF ITS OWN. The harness (`valuation.edge.fleet`) defines
# a declaration as `DECL_<book>.md` carrying exactly ONE fenced ```json block, committed
# ALONE before the book's first fill; it records events under `data/fleet/<book>.csv` with
# kinds `selfcheck`, `fill`, `refusal`, `meter_read`, `close`. This module PREFERS the
# harness's own parser wherever it can import it, so the page and the harness cannot come to
# disagree about what a declaration is, and falls back to reading the same one block itself
# where it cannot -- which is the state today, since `S3-I1` has not landed.
#
# A DRAFT IS NOT A DECLARATION, AND THIS IS THE ONE THAT WOULD HAVE PUBLISHED A FALSE CLAIM.
# The scout lane carries twenty `DECL_DRAFT_*.md` files whose own text says they are *"to be
# committed ALONE ... before any fleet order is placed"* -- i.e. they are awaiting the very
# commit that would make them declarations. A glob of `DECL_*.md` lists all twenty as
# declared books, on a page whose entire claim is that these things were committed in
# advance. Drafts are excluded by name, and a test pins it.
#
# THE DATE IS READ FROM THE DECLARATION'S OWN FIELD OR NOT AT ALL. `preregistrations()` above
# records why: scraping the first ISO date out of a document gave one register a registration
# date of 1998-01-01, from its own contents. The horizon here comes out of the structured
# block (`verdict_horizon.earliest_honest_read`), never out of the prose.
DECL_GLOB = "DECL_*.md"

#: A draft awaiting its own alone-commit. NOT a declaration, and the distinction is the point.
DECL_DRAFT_PREFIX = "DECL_DRAFT_"

DECLARED, FILLING, VERDICT_READ = "DECLARED", "FILLING", "VERDICT-READ"
#: CLOSED was added at the ceremony of 2026-08-24, and the defect it closes was live and
#: PUBLIC. The harness has always been able to write a `close` record — the day-1 test-book
#: was deliberately closed with a zero-charge row — and this vocabulary had no word for it, so
#: a closed book rendered as **FILLING**: *"the record it will be judged on is still filling"*,
#: said of a book that will never fill again. A page whose entire claim is provenance cannot
#: describe a shut book as running.
CLOSED = "CLOSED"
DECL_STATUSES = (DECLARED, FILLING, VERDICT_READ, CLOSED)

DECL_STATUS_BLURB = {
    DECLARED: "committed, with nothing recorded against it yet",
    FILLING: "committed, and the record it will be judged on is still filling",
    VERDICT_READ: "its meter was read, which is the moment the trial is charged",
    CLOSED: "closed on the record; it takes no further fills",
}

#: The harness's own event kinds, in the order that decides a status. A meter read IS a
#: verdict read under `S3-I1` section 2, which is why it outranks a fill.
#:
#: CLOSED OUTRANKS BOTH, because it is the last thing that can happen to a book and the only
#: one of the three that is terminal. A closed book that was also read still reads as closed;
#: reporting it as VERDICT-READ would say the meter is the latest news when the shutter is.
_DECL_KIND_STATUS = ((("close",), CLOSED), (("meter_read",), VERDICT_READ),
                     (("fill",), FILLING))

_JSON_BLOCK = re.compile(r"```json\s*\n(.*?)\n```", re.S)

#: A leading `DECL` / `DECL DRAFT` marker in a document's own heading. Stripped for display.
#:
#: MEASURED 2026-08-24: 17 of the 18 COMMITTED declarations still open with `# DECL DRAFT —`.
#: The fleet lane renamed them out of `DECL_DRAFT_*`, gave them their json blocks and committed
#: them alone — which is what makes them declarations — and left the heading behind. Rendering
#: that verbatim puts the word DRAFT on every row of a shelf whose entire claim is that these
#: books were committed in advance, which is the same false impression as listing drafts, in
#: the opposite direction.
#:
#: The status column is this page's own and is derived from the harness, so the document's
#: heading has no business restating it. Stripping the marker is a DISPLAY normalisation and
#: not a rewrite: the documents are another lane's and are untouched, and the discrepancy is
#: reported rather than quietly papered over.
_DECL_TITLE_MARK = re.compile(r"^\s*DECL(\s+DRAFT)?\s*[\u2014\u2013:\-]*\s*", re.I)

DECL_HEADING = "Books declared before their data existed"

DECL_LEDE = (
    "A registered question fixes what will be asked. A declared book goes further: the "
    "portfolio itself — the rule, the structure, the horizon it will be judged over — is "
    "written down and committed on its own before any of the history it will be judged on "
    "has happened. What makes that checkable is not the outcome, it is the commit: a "
    "declaration cannot be quietly improved afterwards without the change showing.")

DECL_NO_FIGURES = (
    "This shelf deliberately carries no performance figures. It is a record of what was "
    "committed and when, which is the part a reader can verify independently; how the books "
    "have done is a separate question and is not answered here.")

DECL_EMPTY = (
    "No books have been declared yet. This shelf lists them as they are committed, and it is "
    "shown while it is empty on purpose — a surface that appeared only once it had something "
    "flattering to show would be worth nothing.")

DECL_PENDING_RECORD = (
    "The declarations below are read from the committed documents. The commit each one landed "
    "in, and how far its record has filled, come from the harness that keeps them; those "
    "columns read as not yet recorded wherever that harness cannot be reached rather than "
    "being inferred from anything else.")

DECL_OVERDUE_NOTE = (
    "A book whose earliest honest read has arrived without its meter having been read is "
    "shown as such rather than quietly rolled forward. Reaching a horizon is not the same as "
    "reading the answer, and only the second one charges a trial.")

DECL_DRAFTS_NOTE = (
    "Drafts are not listed. A declaration counts from the commit that carries it and nothing "
    "earlier, so a document still being written is not a book.")


def _fleet():
    """`valuation.edge.fleet` if it is importable, else None. Never raises.

    PREFERRED RATHER THAN REQUIRED. Where the harness is present the page uses ITS parser and
    ITS paths, so the two cannot drift apart about what a declaration is. Where it is absent —
    which is the state until `S3-I1` lands — the shelf reads the same single fenced block
    itself and says plainly that the recorded columns are unavailable.
    """
    try:
        from ..edge import fleet as F                                  # noqa: WPS433
        return F
    except Exception:                                                  # noqa: BLE001
        return None


def _declaration(text: str, F=None) -> dict:
    """The declaration's structured block, through the harness's parser where possible."""
    if F is not None:
        try:
            got = F.parse_declaration(text)
            if got.get("ok"):
                return got.get("declaration") or {}
            return {}
        except Exception:                                              # noqa: BLE001
            return {}
    m = _JSON_BLOCK.findall(text or "")
    if len(m) != 1:            # two blocks are two declarations; picking one chooses the rules
        return {}
    try:
        import json
        d = json.loads(m[0])
        return d if isinstance(d, dict) else {}
    except Exception:                                                  # noqa: BLE001
        return {}


def _decl_status(F, book: str, root: str) -> tuple:
    """(status, commit, recorded) from the harness. Never inferred from the calendar."""
    if F is None:
        return DECLARED, "", False
    status, commit, recorded = DECLARED, "", False
    try:
        got = F.declaration_commit(book, root)
        if isinstance(got, dict) and got.get("ok"):
            commit = str(got.get("commit") or "")[:12]
    except Exception:                                                  # noqa: BLE001
        commit = ""
    try:
        rd = F.read_records(book, root)
        if rd.get("ok"):
            recorded = True
            kinds = {(r.get("kind") or "") for r in (rd.get("rows") or [])}
            for names, st in _DECL_KIND_STATUS:
                if kinds.intersection(names):
                    status = st
                    break
    except Exception:                                                  # noqa: BLE001
        pass
    return status, commit, recorded


def declared_books(root: str = None, today=None) -> dict:
    """The declared-book shelf. Provenance only — no figure of any kind reaches this. [S3-I7]

    Tolerant of an EMPTY fleet by design: it renders a sentence saying so rather than hiding,
    because a shelf that appeared only once it had something to show would be evidence of
    nothing.
    """
    root = root or _repo_root()
    # Compared as DATES, never as strings. A malformed horizon parses to None and the book is
    # simply never overdue, which is the safe direction: calling a book overdue because its
    # date failed to parse invents the one state here that reads as a broken promise.
    day = _iso(today) if isinstance(today, str) else today
    day = day or _dt.date.today()
    F = _fleet()

    books, drafts = [], 0
    for path in sorted(glob.glob(os.path.join(root, DECL_GLOB))):
        name = os.path.basename(path)
        if name.startswith(DECL_DRAFT_PREFIX):
            drafts += 1
            continue
        book = name[len("DECL_"):-len(".md")]
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue

        title, title_said_draft = "", False
        for line in text.splitlines():
            t = line.strip()
            if t.startswith("# "):
                head = t[2:].strip()
                title_said_draft = bool(re.match(r"^\s*DECL\s+DRAFT\b", head, re.I))
                title = withhold(_DECL_TITLE_MARK.sub("", head).strip())
                break

        decl = _declaration(text, F)
        hz = decl.get("verdict_horizon") if isinstance(decl.get("verdict_horizon"), dict) else {}
        # ONLY A DATE THAT PARSES. The harness's own template ships this field as the literal
        # placeholder "TODO YYYY-MM-DD", so accepting the raw string publishes a to-do on a
        # public page. A horizon that does not parse is reported as unlabelled, which is what
        # it is, and the fills count below carries the honest answer for a book whose horizon
        # is an event count rather than a calendar date -- several of the drafted ones are.
        raw_hz = str(hz.get("earliest_honest_read") or "").strip()
        horizon = raw_hz if _iso(raw_hz) else None
        # A fill count is a plain integer and is not a figure; it is also the honest answer
        # where a book's horizon is an event count rather than a date, which several of the
        # drafted books' are.
        fills_needed = hz.get("fills_needed")
        try:
            fills_needed = int(fills_needed) if fills_needed is not None else None
        except (TypeError, ValueError):
            fills_needed = None

        status, commit, recorded = _decl_status(F, book, root)
        h = _iso(horizon) if horizon else None
        overdue = bool(h and h <= day and status != VERDICT_READ)
        books.append({
            "file": name,
            "book": book,
            "title": title or book,
            # True when the DOCUMENT still calls itself a draft while being a committed
            # declaration. Reported in the payload rather than only smoothed over, because a
            # display fix that hides a real inconsistency is how it stays unfixed.
            "title_said_draft": title_said_draft,
            "commit": commit,
            "commit_known": bool(commit),
            "horizon": horizon,
            "horizon_labelled": horizon is not None,
            "fills_needed": fills_needed,
            "status": status,
            "status_blurb": DECL_STATUS_BLURB[status],
            "recorded": recorded,
            "overdue": overdue,
        })

    # ---- the OPERATIONAL half, from `fleet_public` so there is no second definition -----
    #
    # The shelf's own columns answer "was this committed before its data existed". A reader
    # also needs to know where each book has GOT to — the commit's date, how long it has been
    # accruing, how many fills it has written, and whether it is armed, unimplemented or
    # blocked. Those come from `fleet_public.books()`, which composes them from the same
    # `may_fill`/`entry_rule` primitives `fleet.cycle` uses, so "blocked" means here exactly
    # what it means in the cycle. Merged by book id and additive: every existing field keeps
    # its meaning, and a failure to read the operational half leaves the provenance half
    # intact rather than emptying the shelf.
    ops, ops_meta = {}, {}
    try:
        from . import fleet_public as FP
        _fp = FP.books(root, today=today)
        if _fp.get("available"):
            ops = {b["book"]: b for b in _fp["books"]}
            ops_meta = {"n_fills_total": _fp["n_fills_total"], "n_armed": _fp["n_armed"],
                        "n_no_rule": _fp["n_no_rule"], "n_blocked": _fp["n_blocked"],
                        "evidence": _fp["evidence"], "posture": _fp["posture"],
                        "not_a_record": _fp["not_a_record"],
                        "quiet_means": _fp["quiet_means"],
                        "repo_note": _fp["repo_note"]}
    except Exception:                                                  # noqa: BLE001
        ops, ops_meta = {}, {}

    for b in books:
        o = ops.get(b["book"]) or {}
        b["commit_date"] = o.get("commit_day")
        b["days_accrued"] = o.get("days_accrued")
        b["fills"] = o.get("fills")
        b["state"] = o.get("state")
        b["state_blurb"] = o.get("state_blurb")
        b["state_reason"] = o.get("reason") or ""
        b["evidence"] = o.get("evidence")
        b["declaration_url"] = o.get("declaration_url")

    return {
        "available": True,
        "books": books,
        "n": len(books),
        "ops": ops_meta,
        "empty": not books,
        "drafts_excluded": drafts,
        "harness_available": F is not None,
        "record_available": any(b["recorded"] for b in books),
        "any_overdue": any(b["overdue"] for b in books),
        "any_unlabelled": any(not b["horizon_labelled"] for b in books),
        "titles_saying_draft": sum(1 for b in books if b["title_said_draft"]),
        "heading": DECL_HEADING,
        "lede": DECL_LEDE,
        "no_figures": DECL_NO_FIGURES,
        "empty_note": DECL_EMPTY,
        "pending_note": DECL_PENDING_RECORD,
        "overdue_note": DECL_OVERDUE_NOTE,
        "drafts_note": DECL_DRAFTS_NOTE,
        "statuses": DECL_STATUSES,
    }


# ----------------------------------------------------------- SC-1: the record's calibration
#
# The denominator says how many things were tried. It says nothing about whether the guesses
# were any good, and those are different questions: a project can count its trials honestly
# and still be systematically over-confident every time it writes a probability down. `SC-1`
# scored the record's own stated priors against what happened, and `SC-1b` re-ran the scoring
# with the pairs grouped by ITEM rather than by FILE -- a change `SC-1` named in writing
# BEFORE its own interval existed, which is a stronger licence than any argument assembled
# afterwards.
#
# DERIVED AT RENDER, NOT TYPED, and the count is the reason. The number of scored predictions
# grows every time this project writes another one down, so a hard-coded count on a public
# page is stale the week after it ships -- `MB38`'s own argument for deriving the trial
# denominator, applied to the other number on this page that moves.
#
# WHERE IT READS FROM, AND WHY IT IS NOT THE ARTIFACT ITSELF. The study's artifact lives
# under the repo-root `data/`, which is gitignored and never ships with a deploy: a surface
# reading it directly would be permanently unavailable in production, which is the constraint
# `optionable_partition` documents and answers by transcribing literals. Transcribing is
# exactly what the count may not be. So `scripts/publish_calibration_card.py` derives a strict
# subset of the artifact into `data_export/` -- tracked, shipped in the image, and already the
# place this project publishes things derived out of the ignored data root -- and the card
# carries the artifact's SHA-256 so a test can prove which artifact it came from. One
# authority, one direction, and a test that re-derives the card whenever the artifact is
# present and fails if the committed file has drifted from it.
#
# FAIL-CLOSED, exactly as the denominator is. A missing card, a malformed card, a card with a
# verdict this page has no word for -- every one returns `available: False` with a reason and
# the section does not render. A page that guessed at a calibration verdict would be the one
# claim on it that nobody could check.
CALIBRATION_CARD = os.path.join("data_export", "calibration_card.json")

#: The verdict WORDS. A card carrying a verdict absent from this table is unavailable rather
#: than rendered raw: the vocabulary is the page's, and an unrecognised verdict is a study
#: this page has not been taught to describe. `MB38`'s rule that the verdict is a word.
CALIBRATION_PHRASE = {
    "CALIBRATED-IN-THE-LARGE": "came back calibrated in the large",
    "MISCALIBRATED-OPTIMISTIC": "came back miscalibrated, in the flattering direction",
    "MISCALIBRATED-PESSIMISTIC": "came back miscalibrated, in the cautious direction",
    "CANNOT-TELL": "could not be told apart from chance at this resolution",
}

CALIBRATION_HEADING = "Whether the predictions themselves were any good"

CALIBRATION_LEDE = (
    "Counting the searches says nothing about the quality of the guesses. A project can be "
    "scrupulous about its denominator and still be over-confident every time it writes a "
    "probability down. This record attaches a stated probability to many of its predictions "
    "before the answer is known, which makes them scoreable after the fact — so they were "
    "scored.")

CALIBRATION_METHOD = (
    "The pairs are grouped by the item that produced them rather than by the document they "
    "were written in, because several predictions from one study are not several independent "
    "pieces of evidence. That grouping was named in writing before the first interval was "
    "computed, which matters more than the argument for it: choosing how to group after "
    "seeing the answer is choosing the design on the outcome.")

CALIBRATION_LIMIT = (
    "Read it for exactly what it is. It is an AGGREGATE property and it validates no "
    "individual prediction on this page. The measured gap is smaller than the smallest gap "
    "this design had a coin-flip's chance of detecting, so \"calibrated\" here means \"no "
    "miscalibration this test could have seen\", not \"no miscalibration\". And the pairs "
    "are picked out of the record by a keyword rule whose miss rate has never been measured: "
    "a prediction written as a numbered list instead of a table is invisible to it, which the "
    "study reports against itself.")

CALIBRATION_WHY_PUBLISHABLE = (
    "As with the counts above, these are not performance figures and are not an exception to "
    "the rule against them. A calibration gap is arithmetic on this project's own written "
    "predictions and their outcomes; it derives from no vendor's data and says nothing "
    "whatever about how the strategy performed.")

_CALIBRATION_CACHE = {}


def _fmt(x, places: int) -> str:
    """A fixed-precision decimal with trailing zeros trimmed, so `0.15` renders as `0.15`.

    The rendered STRING is what the guard's exemption is built from, so this function and the
    exemption cannot be allowed to disagree -- they call it on the same value.
    """
    t = ("%%.%df" % places) % float(x)
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    return t or "0"


def calibration(card_path: str = None) -> dict:
    """The record's own calibration verdict, derived from the published card.  [SC-1]

    Everything measured is read; nothing measured is typed. Fails closed on any malformed
    input, and returns a REASON rather than a blank so a missing section is explicable.
    """
    import json

    out = {"available": False, "reason": "", "heading": CALIBRATION_HEADING}
    path = card_path or os.path.join(_repo_root(), CALIBRATION_CARD)
    try:
        with open(path, encoding="utf-8") as f:
            card = json.load(f)
        if not isinstance(card, dict):
            raise ValueError("the calibration card is not an object")
        verdict = str(card["verdict"])
        phrase = CALIBRATION_PHRASE.get(verdict)
        if not phrase:
            out["reason"] = ("the calibration card carries a verdict this page has no "
                             "vocabulary for")
            return out
        n, n_clusters = int(card["n"]), int(card["n_clusters"])
        gap = float(card["gap"])
        half_width, bar = float(card["half_width"]), float(card["bar"])
        # The detection threshold the honest reading depends on. Cluster-adjusted where the
        # card carries it, because the pairs are clustered and the naive figure would flatter
        # the design's resolution.
        thresh = float(card.get("cluster_adjusted_detection_threshold_50pct")
                       or card["detection_threshold_50pct"])
        quoted = [str(x) for x in (card.get("may_not_be_quoted_as") or [])]
    except Exception as e:                                             # noqa: BLE001
        out["reason"] = ("the calibration card could not be read (%s); the section is "
                         "withheld rather than guessed at" % type(e).__name__)
        return out

    if n <= 0 or half_width <= 0 or bar <= 0:
        out["reason"] = "the calibration card is not internally consistent"
        return out

    # DERIVED, INCLUDING THE VERDICT WORD. The card records the study's verdict and this
    # re-derives the comparison behind it, so a card whose verdict disagreed with its own
    # numbers renders as unavailable instead of publishing the disagreement.
    clears = half_width <= bar
    if clears != verdict.startswith("CALIBRATED"):
        out["reason"] = ("the calibration card's verdict disagrees with its own interval; "
                         "the section is withheld")
        return out

    # The direction, in words. A NEGATIVE gap means the record predicted a thing less often
    # than it went on to happen -- under-confident, which is the cautious direction. "If
    # anything" is not a hedge for its own sake: the gap is below the threshold above, so the
    # direction is a lean this design could not have resolved.
    #
    # SAID IN FULL RATHER THAN NAMED. The technical word for a negative gap is "pessimistic",
    # and on a page that sits two clicks from a performance card that word reads as a view
    # about the market rather than a property of the predictions. So the direction is spelled
    # out: what was predicted, against what happened.
    small = abs(gap) < thresh
    if gap == 0:
        direction = "there is no lean in either direction"
    elif gap < 0:
        direction = ("cautious — the record predicted these things slightly LESS often than "
                     "they went on to happen")
    else:
        direction = ("flattering — the record predicted these things slightly MORE often "
                     "than they went on to happen")
    if small and gap != 0:
        direction = "mildly " + direction[0].lower() + direction[1:]

    out.update(
        available=True,
        verdict=verdict,
        verdict_phrase=phrase,
        n=n,
        n_clusters=n_clusters,
        half_width_text=_fmt(half_width, 4),
        bar_text=_fmt(bar, 4),
        clears=clears,
        clears_word=VERDICT_PASS if clears else VERDICT_FAIL,
        direction=direction,
        below_detection=small,
        may_not_be_quoted_as=quoted,
        register=str(card.get("register") or ""),
        register_commit=str(card.get("register_commit") or ""),
        corpus_pinned_to=str(card.get("corpus_pinned_to") or ""),
        lede=CALIBRATION_LEDE,
        method=CALIBRATION_METHOD,
        limit=CALIBRATION_LIMIT,
        why=CALIBRATION_WHY_PUBLISHABLE,
    )
    return out


def derived_calibration_figures() -> frozenset:
    """The calibration strings the page may render -- the guard's SECOND exemption.  [SC-1]

    Built on exactly `MB38`'s three properties, and for the same reason: a half-width and a
    pre-committed ceiling are bare decimals, so `_FIGURE` redacts them, and they are not
    performance figures in the sense that rule exists to stop.

      * DERIVED from the published card, never typed, so it cannot rot into a literal;
      * EMPTY when the card cannot be read, so a broken card CLOSES the guard rather than
        opening it;
      * WHOLE `_FIGURE` matches only, so `0.1432%` still fires (a percentage is a performance
        figure whatever its digits) and `t 0.1432` still fires (naming it as a statistic
        brings it straight back under the rule).

    Bounded to the two strings the section is ACTUALLY rendering, not to a range it might one
    day render. And `withhold()` does NOT get this exemption -- it is the redactor for text
    this page does not own, and a log row carrying either value is redacted exactly as before.
    """
    if "texts" not in _CALIBRATION_CACHE:
        c = calibration()
        if not c.get("available"):
            _CALIBRATION_CACHE["texts"] = frozenset()
        else:
            _CALIBRATION_CACHE["texts"] = frozenset(
                {c["half_width_text"], c["bar_text"]})
    return _CALIBRATION_CACHE["texts"]


def reset_calibration_cache() -> None:
    """Drop the memo. For tests that move the card and re-ask."""
    _CALIBRATION_CACHE.clear()


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
        # SC-4 — the same denominator in MOTION. Note again what is NOT here: no effect size,
        # no statistic, no comparison. A verdict WORD and a count, and the bar each count
        # implies.
        "weekly": weekly(log_path),
        "week_heading": WEEK_HEADING,
        "week_lede": WEEK_LEDE,
        "week_hurdle_note": WEEK_HURDLE_NOTE,
        "week_verdict_note": WEEK_VERDICT_NOTE,
        "week_floor_note": WEEK_FLOOR_NOTE,
        "week_quiet": WEEK_QUIET,
        "week_not_a_result": WEEK_NOT_A_RESULT,
        # SC-1 — whether the predictions themselves were any good. An AGGREGATE property with
        # its own limits shipped beside it, and the study's own list of what it may not be
        # quoted as, carried in the payload rather than left to each surface to remember.
        "calibration": calibration(),
        "cal_heading": CALIBRATION_HEADING,
        # S3-I7 — the declared books. Provenance, never performance.
        "declared": declared_books(root),
        "decl_heading": DECL_HEADING,
    }
