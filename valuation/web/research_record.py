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
        for r in RL.rows(path=log_path):
            d = _iso(r.get("date"))
            if d is not None and start <= d <= end:
                win.append((d, r))
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
            before = now - moved
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
    }
