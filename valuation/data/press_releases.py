"""COMPANY PRESS RELEASES, AS FILED WITH THE SEC AS 8-K EXHIBITS.  [item 56 route 1]

WHY THIS SOURCE AND NOT ANOTHER
-------------------------------
Item 55 kept no new source, and the conclusions-only filter it shipped now shows about half of
what the Yahoo feed carries about a company -- so a name like NVDA can show nothing at all. The
binding problem was never the filter; it is that a symbol-requested news feed is mostly about
other companies (42% on-company across four tickers, 1 of 18 on NVDA).

A company's own press release has neither problem. It is about the company **by construction**,
it is a statement the company has signed its name to, and it reaches us as an **exhibit to an
8-K** -- a primary document, under terms the SEC states plainly. Don's ruling called it
*"a verifiable statement by the company, attributed by construction"*, and that is exactly what
the conclusions filter is trying to select for.

THE TITLE IS REAL AND IT IS NOT IN THE METADATA -- THAT WAS MEASURED BEFORE THIS WAS BUILT
------------------------------------------------------------------------------------------
Three cheaper routes were tried first and all three fail, which is why this module fetches the
exhibit itself:

* `submissions` carries `primaryDocDescription`, and on every 8-K checked it is the string
  **`"8-K"`** -- the form's own name, not a title.
* `index.json` carries a `type` field, and for these documents it holds **icon filenames**
  (`"text.gif"`, `"image2.gif"`). It gives the exhibit's **filename** (`exhibit991.htm`,
  `e26287_ex99-1.htm`) and no human-readable title at all.
* The 8-K **item number** IS present and clean (`"2.02,9.01"`, `"5.02"`, `"8.01"`). It is used
  below as a **label**, because it is free -- but it is a category, not a headline: every
  earnings release in history is `2.02`, so on its own it tells a reader nothing they did not
  already know. It is carried beside the title, never instead of it.

So the title is extracted from the exhibit, and the extraction is measured rather than trusted:
see `EXTRACTION_MEASURED`.

AND THE FILENAME IS NOT A USABLE SIGNAL EITHER -- WHICH IS THE FINDING THAT SHAPED THIS MODULE
----------------------------------------------------------------------------------------------
The first cut looked for `EX-99`-shaped filenames, because "usually EX-99.1" is how the exhibit
is described everywhere including Don's own ruling. **Measured across the five names, that rule
finds nothing for three of them**, and the reason is that the press release's EXHIBIT NUMBER is
not in its FILENAME:

    NVDA  q2fy27pr.htm              sbeoainvidia-portsrelease.htm     <- no "99" at all
    APLD  apldq127earningsrelease.htm                                 <- no "99" at all
    KO    a2026q2earningsreleaseex-9.htm      e26287_ex99-1.htm       <- one of each
    TSLA  exhibit991.htm            exhibit991111111.htm
    OCTV  exhibit991q2fy26.htm      exhibit991-informationstat.htm

So a filename pattern is a guess about a filer's naming habit, and filers do not share one.
What IS structural: a filing's document list contains the 8-K body, the EDGAR index pages, the
XBRL render (`R1.htm`), and the exhibits. **The exhibits are what is left after removing the
things that can be identified**, and the question "is this one a press release" is then settled
by reading its heading -- a credit agreement's heading is not a conclusion about the company and
the item 55 filter drops it. Filename tells (`99`, `release`, `pr`) are kept only to ORDER the
candidates so the likely one is read first and the request budget is not spent on an exhibit
nobody wanted.

A SECOND DEFECT, IN THE EXTRACTION, FOUND THE SAME WAY
------------------------------------------------------
EDGAR prepends its own **document header** to the exhibit -- `EX-99.1`, a sequence number, and
the filename -- above the document's real first line. The first cut skipped the two it
recognised, captured `e26287_ex99-1.htm` as the heading, and then stopped at `Exhibit 99.1`
below it. So it produced an empty title for a filing whose heading was plainly there, on the
one name where the exhibit had been found at all. Boilerplate now ends the heading only once a
**plausible** heading has been collected, and a bare filename is boilerplate.

WHAT THE HEADING LOOKS LIKE, AND WHY THE DATELINE IS THE TERMINATOR
-------------------------------------------------------------------
A filed release opens with its heading, sometimes over two lines, and then a **dateline** --
`ATLANTA, June 25, 2026 -` -- before the first sentence. The dateline is the one reliable
boundary in documents with no consistent markup, so it is what stops the read. Measured on KO:

    The Coca-Cola Company Announces CEO Succession Plan;
    Chief Operating Officer Henrique Braun to Succeed James Quincey as CEO in 2026
    ATLANTA, Dec. 10, 2025 - The Coca-Cola Company today announced ...

Two heading lines, then the dateline. Where no heading can be read the filing is **dropped, not
guessed**: a blank title linked to an 8-K would be worse than showing one fewer item.

BUT THE DATELINE IS NOT ALWAYS THERE, AND THAT COST A THIRD ROUND OF REPAIR
---------------------------------------------------------------------------
With the first two defects fixed, all five names produced titles and **four of them were wrong
in the same way** -- the heading had run on into the body, because NVIDIA and Coca-Cola put
their bullet-point highlights ABOVE the dateline:

    NVIDIA Announces Financial Results for Second Quarter Fiscal 2027 - Revenue of $96...
    Coca-Cola Reports Second Quarter 2026 Results and Raises Full Year Guidance Global Unit...

So "read until the dateline" is too permissive on its own. What is reliable is the opposite
test, on SYNTAX rather than on position: a heading's second line is a **subtitle**, and a
subtitle announces itself either by the first line ending in a connector (`;` `,` `:` `and`)
or by its own first word being lower-case (`for North America Operating Unit`). A bullet item
does neither -- it begins with a bullet, a digit or a capital. So the heading is **one line,
extended to a second only on one of those two tells**, and both real two-line cases above are
kept while every run-on is cut.

AND A HEADING CAN BE SPLIT MID-PHRASE, WHICH MADE THE MODULE SHOW THE WRONG RELEASE
-----------------------------------------------------------------------------------
Applied Digital's markup puts its own name on a line of its own:

    Applied
    Digital Signs 210 MW Lease at Delta Forge 2, Expanding Its AI Factory Franchise Model ...

Testing `Applied` for a subtitle tell rejected it, the one-word title failed the length check,
and the module moved on to the NEXT exhibit in the filing -- so it showed a notes-pricing
release instead of the lease that was the day's actual news. **A silent substitution of one
real document for another is the worst shape a defect can take in this module**, because every
field is still correct and nothing looks wrong. The continuation test now applies only once a
plausible heading exists to extend; below that the read is still inside the heading.

TWO MORE THINGS GOT THROUGH AND ARE NOW REJECTED BY WHAT THEY SAY
-----------------------------------------------------------------
* **A slide deck's table of contents.** Tesla files its quarterly update as a deck, and its
  first page reads `Q2 2026 Update 1 Exhibit 99.1 Highlights 03 Financial Summary 04 ...`. It
  is a contents list, not a headline.
* **A bond exhibit.** `NVIDIA Corporation 4.250% Notes due 2028 4.350% Notes due 2029` is an
  Item 8.01 notes filing, not a press release.

Both are rejected on their own text, which is the only thing that can distinguish them -- the
document list cannot (see above).

AND THE ENTITIES HAD TO BE DECODED PROPERLY
--------------------------------------------
The first cut replaced a hand-written list of named entities and left numeric ones alone, so
titles shipped with `&#8226;` and `&#160;` in them. `html.unescape` handles the whole set, and
a bullet is turned into a LINE BREAK rather than a character -- which is also half of why the
run-on above is now cut.

TITLES AND LINKS ONLY, AND THE LINK GOES TO THE FILING
------------------------------------------------------
The exhibit body is fetched because that is where the heading is, and **nothing but the heading
is kept** -- the function returns a title, a date and a URL, and no other text is retained,
shown or sent to a model. A test holds that. The link is the **filing index** on sec.gov, so a
reader lands on the 8-K with its exhibit list rather than on a bare HTML fragment.

COST, MEASURED RATHER THAN ESTIMATED
------------------------------------
The filing index and then up to two documents per filing, so the cost is a function of how many
8-K filings have to be opened before four releases are found. **Measured across the five names
it is 7 to 19 EDGAR requests, 68 in total, averaging 14** -- more than the "at most 8" this
docstring claimed before the measurement was run, and the claim is corrected rather than the
figure being rounded down to it.

At the module's 0.2s gap that is under three seconds, and it happens **once per ticker per
day**: `/api/recent` is fetched after the paint and stored by `ai_auto.store_recent`, keyed on
ticker and day. It is **not charged to the AI cap**, and must not be -- that cap bounds
Anthropic spend, and this is a free government feed; sharing it would let a visitor reading
headlines exhaust the owner's analysis budget.
"""
from __future__ import annotations

import html as _html
import re
from typing import Optional

from .recent import SEC_UA, _sec_get  # one EDGAR identity and one rate gate for the project

#: How many filed releases to read. Each costs two requests, so this is the cost dial.
MAX_RELEASES = 4

#: How many 8-K filings to look through to find them. A company can file an 8-K with no press
#: release attached (a bare Item 5.07 vote result, say), so the search is wider than the keep.
MAX_FILINGS_SCANNED = 8

#: How many documents to read per filing before giving up on it. The filename cannot identify
#: the press release, so this bounds what "let the heading decide" costs.
MAX_TRIES_PER_FILING = 2

#: Documents in an 8-K filing that are never the press release and ARE identifiable: EDGAR's
#: own index pages, and the XBRL viewer renders.
_NEVER = re.compile(r"(-index(-headers)?\.html?$|^R\d+\.htm$|^Financial_Report|\.xml$)", re.I)

#: The 8-K body itself. `nvda-20260826.htm`, `tsla-20261002.htm`, `form8-k.htm`,
#: `octave8-kx05122026.htm` -- a cover page, not a release. It is also caught by
#: `_NOT_A_RELEASE` on its text, so this is the cheap pass that saves a request.
_EIGHT_K_BODY = re.compile(r"(^[a-z]{1,6}-\d{8}\.htm|8-?k|8x?k)", re.I)

#: Filename tells that a document IS a press release. These do not DECIDE anything -- the
#: heading read does -- they only order the candidates so the request budget is spent on the
#: likely one first. All five measured names are covered by one of the three.
_RELEASE_TELL = re.compile(r"(99|release|pr\.html?$)", re.I)


def exhibit_candidates(names) -> list:
    """The documents in an 8-K filing that could be its press release, likeliest first.

    Pure and separately tested, because this is where the first cut was wrong: it required an
    `EX-99`-shaped filename and three of five companies do not use one.
    """
    out = []
    for raw in names or []:
        n = str(raw or "").strip()
        if not n.lower().endswith((".htm", ".html")):
            continue
        if _NEVER.search(n):
            continue
        if _EIGHT_K_BODY.search(n) and not _RELEASE_TELL.search(n):
            continue
        out.append(n)
    # Stable: a filename tell first, then the filing's own order.
    out.sort(key=lambda n: 0 if _RELEASE_TELL.search(n) else 1)
    return out

#: The 8-K item numbers, from SEC Form 8-K itself. Carried as a LABEL beside the title -- see
#: the module docstring for why it is not used AS the title. Only the items a reader would
#: recognise are named; anything else is reported by its number.
ITEM_LABELS = {
    "1.01": "entered a material agreement",
    "1.02": "ended a material agreement",
    "2.01": "completed an acquisition or disposal",
    "2.02": "reported results",
    "2.03": "took on a financial obligation",
    "2.05": "approved a restructuring",
    "3.01": "listing or standard non-compliance",
    "3.02": "sold unregistered shares",
    "4.01": "changed auditor",
    "4.02": "said prior statements cannot be relied on",
    "5.01": "change in control",
    "5.02": "director or officer change",
    "5.03": "changed its charter or by-laws",
    "5.07": "shareholder vote result",
    "7.01": "Regulation FD disclosure",
    "8.01": "other reportable event",
    "9.01": "financial statements and exhibits",
}

#: Lines that appear above a heading and are not the heading. Matched on the WHOLE line after
#: whitespace collapse, never as a substring, so a real heading containing one of these words
#: survives. The first three alternatives are EDGAR's own document header, which sits ABOVE the
#: document's first real line -- a filename among them was captured as a title by the first cut.
_BOILERPLATE = re.compile(
    r"^(exhibit\s*\d+(\.\d+)?|ex-?\s*\d+(\.\d+)?|[\w.\-]+\.(htm|html|txt|pdf)|"
    r"for\s+immediate\s+release|immediate\s+release|"
    r"news\s+release|press\s+release|media\s+release|news|investor\s+relations|"
    r"contacts?|investors?|media|page\s*\d+|\d+)$", re.I)

#: A title that is really the 8-K cover page, a legal agreement, a bond exhibit or a slide
#: deck's contents list -- not a press release. Checked on the finished title, because the
#: document list cannot distinguish them (see the docstring). Every alternative here was added
#: because it got through on one of the five measured names.
_NOT_A_RELEASE = re.compile(
    r"(united\s+states\s+securities\s+and\s+exchange|securities\s+and\s+exchange\s+commission|"
    r"^form\s+8-k|pursuant\s+to\s+section\s+1[35]|^(credit|loan|purchase|merger|employment|"
    r"indenture|underwriting|security|pledge|guarant\w+|lease|license)\s+agreement|"
    r"^amend(ed|ment)|^certificat(e|ion)\s+of|^by-?laws|^articles\s+of|"
    r"^consent\s+of|^subsidiaries\s+of|"
    # A deck's contents list: Tesla's quarterly update exhibit. `exhibit 99.1` appearing IN a
    # title is always document boilerplate that has leaked in, never a headline.
    r"financial\s+summary|table\s+of\s+contents|exhibit\s*\d+\.\d+|"
    r"^q[1-4]\b[^.]{0,24}\bupdate\b|"
    # A notes/bond exhibit: NVIDIA's Item 8.01 filing.
    r"\d\.\d{2,3}\s*%\s*notes|notes\s+due\s+\d{4})", re.I)

#: A dateline: `ATLANTA, June 25, 2026`, `SANTA CLARA, Calif., Aug. 26, 2026`, `New York, NY -`.
#: This is the terminator -- the heading is everything above it.
_MONTH = (r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)"
          r"(uary|ruary|ch|il|e|y|ust|tember|ober|ember)?\.?")
_DATELINE = re.compile(r"^[A-Z][A-Za-z.\- ]{1,28},(\s+[A-Za-z.]{2,14},)?\s+%s\s+\d{1,2},?\s+\d{4}"
                       % _MONTH, re.I)
#: A line that is a date on its own, which some filers use instead of a dateline.
_BARE_DATE = re.compile(r"^%s\s+\d{1,2},?\s+\d{4}\s*$" % _MONTH, re.I)

#: A heading is a heading and not a paragraph. A line this long with this many words and a full
#: stop is the release's first sentence, so reading it would turn a title into prose.
_MAX_TITLE_CHARS = 220

#: Measured 2026-10-13 on NVDA, TSLA, KO, APLD and OCTV -- see `scripts/i56_measure.py`. Stored
#: so a future reader can tell whether EDGAR's shape has changed under this module.
EXTRACTION_MEASURED = {
    "date": "2026-10-13",
    "note": ("filings scanned, exhibits found, headings read and titles kept by the item 55 "
             "conclusions filter, per ticker -- see HANDOFF_appfixes.md item 56"),
}


#: A heading's first line ends like this when a subtitle follows it. The last alternative is a
#: dangling INFINITIVE -- `... Senior Secured Notes to fund` continues on the next line -- and
#: it requires the verb to be lower-case so a complete heading ending `Transition to Cloud` is
#: not joined to whatever follows it.
_CONNECTOR = re.compile(r"([;:,]|\b(and|or|as|with|to|for|of|in|on|after|amid)\s*|"
                        r"\bto\s+[a-z]+)$", re.I)


#: Prose from inside a legal instrument, which reaches a title only when the heading above it
#: was itself an instrument heading.
_LEGAL_PROSE = re.compile(r"(the\s+undersigned|hereby\s+certif|witnesseth|"
                          r"in\s+witness\s+whereof|this\s+agreement\s+is\s+(made|entered))",
                          re.I)


def _opens_in_caps(title: str) -> bool:
    """Do the first two words both read as capitals? Then it is a legal exhibit's heading.

    A company name can legitimately be capitalised (`NVIDIA Announces ...`), so one all-caps
    word decides nothing; two in a row is a document heading. Words of fewer than three letters
    are skipped, because `NO. 1` and `A` are not evidence either way.
    """
    t = str(title or "")
    if _LEGAL_PROSE.search(t):
        return True
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'’]*", t) if len(w) >= 3]
    if len(words) < 2:
        return False
    return all(w.isupper() for w in words[:2])


def _is_continuation(prev: str, line: str) -> bool:
    """Is `line` the second line of a heading whose first line is `prev`?

    Two tells, both syntactic. A bullet point or a new heading satisfies neither, which is the
    point -- see the module docstring.
    """
    if _CONNECTOR.search(prev or ""):
        return True
    first = (line or "").split(" ")[0]
    return bool(first) and first[:1].islower()


def _clean_lines(html: str) -> list:
    """The exhibit's visible lines, in order, with markup and scripts removed."""
    body = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", " ", html or "")
    # A block boundary is a line boundary; an inline tag is not, or a heading split across
    # <b>/<font> runs would arrive as several "lines" and the join would be wrong.
    body = re.sub(r"(?i)<\s*(br|/?p|/?div|/?tr|/?h[1-6]|/?td|/?li|/?table)\b[^>]*>", "\n", body)
    body = re.sub(r"<[^>]+>", " ", body)
    # The WHOLE entity set, not a hand-written list -- the first cut shipped titles containing
    # `&#8226;` and `&#160;` because it only replaced the named ones it had thought of.
    body = _html.unescape(body)
    # A bullet is a LINE BREAK, not a character: it is where a heading stops and the release's
    # highlights begin, and NVIDIA and Coca-Cola both put those above the dateline.
    body = re.sub(r"[\u2022\u2023\u25aa\u25cf\u00b7\u2219]", "\n", body)
    body = body.replace("\u00a0", " ")
    out = []
    for raw in body.split("\n"):
        line = re.sub(r"\s+", " ", raw).strip(" \t ")
        if line:
            out.append(line)
    return out


def extract_heading(html: str) -> dict:
    """The heading of a filed press release, or an empty title with the reason it is empty.

    Pure: it takes the document text and returns a title, so it is testable without a network
    and the fixtures below are real filed exhibits.
    """
    out = {"title": "", "lines_used": 0, "reason": ""}
    lines = _clean_lines(html)
    if not lines:
        out["reason"] = "the exhibit carried no readable text"
        return out
    parts = []

    def _plausible():
        """Enough collected to call it a heading -- so boilerplate below it can end it."""
        return sum(len(p.split()) for p in parts) >= 3

    for line in lines[:40]:
        if _DATELINE.match(line) or _BARE_DATE.match(line):
            break                       # the dateline: everything above it was the heading
        if _BOILERPLATE.match(line):
            if _plausible():
                break                   # boilerplate BELOW a real heading ends it
            # Otherwise this is still EDGAR's document header or the filer's own banner. Drop
            # whatever was collected above it: a line sitting among the header lines is part of
            # the header, not the title. This is the defect the measurement found.
            parts = []
            continue
        # A sentence, not a heading. Stop -- but only once something has been collected, so a
        # release whose heading is itself a sentence is not discarded.
        if _plausible() and line.endswith(".") and len(line.split()) > 12:
            break
        # THE CONTINUATION TEST APPLIES ONLY ONCE THERE IS A HEADING TO EXTEND. Below that, the
        # read is still INSIDE the heading: Applied Digital's markup splits its own name off on
        # to its own line (`Applied` / `Digital Signs 210 MW Lease at Delta Forge 2, ...`), and
        # testing the fragment for a subtitle tell rejected it, failed the length check, and
        # made the module fall through to a DIFFERENT and far less newsworthy exhibit -- a
        # silent substitution, which is the worst shape a defect can take here.
        #
        # Once a plausible heading exists, position cannot decide whether to extend it: NVIDIA
        # and Coca-Cola put bullet highlights ABOVE the dateline, so reading to the dateline
        # ran four of five titles into the body. Syntax can -- a subtitle follows a connector,
        # or begins in lower case -- and a bullet point does neither.
        if _plausible() and not _is_continuation(parts[-1], line):
            break
        parts.append(line)
        if sum(len(p) for p in parts) >= _MAX_TITLE_CHARS or len(parts) >= 3:
            break
    title = " ".join(parts).strip(" -–—;:,")
    title = re.sub(r"\s+", " ", title)
    # A dangling connector means the heading continued on a line the rules above stopped at --
    # `... Senior Secured Notes to fund`. Trim it rather than print it.
    title = re.sub(r"\s+\b(and|or|as|with|to|for|of|in|on|after|amid|the|a|an)\s*$", "",
                   title, flags=re.I).strip(" -–—;:,")
    if len(title) > _MAX_TITLE_CHARS:
        title = title[:_MAX_TITLE_CHARS].rsplit(" ", 1)[0] + "..."
    out["lines_used"] = len(parts)
    # A two-word fragment is not a title. Nine characters rules out "Exhibit", a stray symbol
    # and a bare company abbreviation while keeping genuinely short real headings.
    if len(title) < 12 or len(title.split()) < 3:
        out["reason"] = ("no heading could be read from the exhibit, so this filing is not "
                         "shown rather than being shown with a guessed title")
        return out
    # The document list cannot say which exhibit is the press release, so a candidate that
    # turns out to be the 8-K cover page or a filed agreement is rejected HERE, on what it
    # says about itself, rather than on a guess about its filename.
    #
    # A LEGAL EXHIBIT OPENS IN ALL CAPS AND A PRESS RELEASE DOES NOT. `OFFICERS' CERTIFICATE`
    # and `INCREMENTAL ASSUMPTION AGREEMENT NO. 1` both got through a list of named document
    # types, because that list can only ever name the ones somebody thought of. The casing is
    # the general property, and it has to be read off the FIRST TWO WORDS rather than the whole
    # title -- plenty of companies are called NVIDIA or KO, so an all-caps first word is normal
    # and an all-caps SECOND word is not.
    if _opens_in_caps(title):
        out["reason"] = ("this document's heading is in capitals throughout, which is a filed "
                         "legal document rather than a press release")
        return out
    if _NOT_A_RELEASE.search(title):
        out["reason"] = ("this document is the filing's cover page or a filed agreement rather "
                         "than a press release")
        return out
    out["title"] = title
    return out


def _item_label(items: str) -> str:
    """`"2.02,9.01"` -> `"reported results"`. The first item is the reason for the filing."""
    first = str(items or "").split(",")[0].strip()
    if not first:
        return ""
    return ITEM_LABELS.get(first, "SEC Form 8-K item %s" % first)


def press_releases(cik, limit: int = MAX_RELEASES, *, get=None) -> dict:
    """Recent press releases this company filed as 8-K exhibits. Never raises.

    `get` is the EDGAR fetcher, injected so the tests can exercise the whole walk -- the filing
    list, the exhibit pick and the heading read -- without a network.
    """
    _get = get or _sec_get
    out = {"available": False, "items": [], "source": "SEC EDGAR (8-K exhibits)",
           "terms": ("SEC: \"All Government-created content on sec.gov and EDGAR public filing "
                     "content are free to access and reuse.\" Declared User-Agent, under the "
                     "stated 10 requests/second ceiling."),
           "about_company": "by construction - the company filed it under its own CIK",
           "attribution": "the company's own words, signed and filed",
           # The yield, in the item 55 shape: found / on-company / kept. `on_company` is equal
           # to `n_found` BY CONSTRUCTION here and is reported anyway, because that equality is
           # this source's whole advantage over a news feed and should be visible.
           "filings_scanned": 0, "exhibits_found": 0, "headings_read": 0,
           "n_found": 0, "on_company": 0, "n_shown": 0, "n_excluded": 0,
           "excluded_by_kind": {}, "requests_spent": 0, "reason": "",
           "filter_mode": "filed_by_the_company",
           "filter_note": ("the item 55 conclusions filter in its filed mode: the promotional "
                           "test applies and the attribution test does not, because the "
                           "company filed this itself")}
    try:
        c = re.sub(r"\D", "", str(cik or ""))
        if not c:
            out["reason"] = "no SEC company id (CIK) for this company"
            return out
        cik_i = int(c)
        r = _get("https://data.sec.gov/submissions/CIK%010d.json" % cik_i)
        out["requests_spent"] += 1
        if getattr(r, "status_code", 0) != 200:
            out["reason"] = "EDGAR returned HTTP %s for the filing list" % getattr(
                r, "status_code", "?")
            return out
        rec = ((r.json() or {}).get("filings") or {}).get("recent") or {}
    except Exception as e:                                                  # noqa: BLE001
        out["reason"] = "the EDGAR filing list could not be read (%s)" % type(e).__name__
        return out

    forms = rec.get("form") or []
    dates = rec.get("filingDate") or []
    accs = rec.get("accessionNumber") or []
    items_col = rec.get("items") or []
    found = []
    for i in range(min(len(forms), len(dates), len(accs))):
        if len(found) >= max(0, int(limit)):
            break
        if out["filings_scanned"] >= MAX_FILINGS_SCANNED:
            break
        if str(forms[i] or "").strip() not in ("8-K", "8-K/A"):
            continue
        out["filings_scanned"] += 1
        acc = str(accs[i] or "").replace("-", "")
        base = "https://www.sec.gov/Archives/edgar/data/%d/%s" % (cik_i, acc)
        try:
            idx = _get(base + "/index.json")
            out["requests_spent"] += 1
            if getattr(idx, "status_code", 0) != 200:
                continue
            listing = ((idx.json() or {}).get("directory") or {}).get("item") or []
        except Exception:                                                   # noqa: BLE001
            continue
        exhibits = exhibit_candidates([str(it.get("name") or "") for it in listing])
        if not exhibits:
            continue
        out["exhibits_found"] += 1
        # Read at most MAX_TRIES_PER_FILING of them: the filename cannot say which one is the
        # press release (measured -- see the docstring), so the heading read is the filter, and
        # this is the cap on what that costs.
        head = {"title": ""}
        for cand in exhibits[:MAX_TRIES_PER_FILING]:
            try:
                doc = _get("%s/%s" % (base, cand))
                out["requests_spent"] += 1
                if getattr(doc, "status_code", 0) != 200:
                    continue
                head = extract_heading(doc.text)
            except Exception:                                               # noqa: BLE001
                continue
            if head.get("title"):
                break
        if not head.get("title"):
            continue
        out["headings_read"] += 1
        found.append({
            "title": head["title"],
            # The FILING index, not the raw fragment: a reader lands on the 8-K.
            "url": base + "/",
            "date": str(dates[i] or ""),
            "publisher": "the company (filed with the SEC)",
            "form": str(forms[i] or "").strip(),
            "sec_item": str(items_col[i]).strip() if i < len(items_col) else "",
            "sec_item_label": _item_label(items_col[i] if i < len(items_col) else ""),
        })

    out["n_found"] = len(found)
    out["on_company"] = len(found)          # by construction, and reported so it is visible
    # THE SAME FILTER AS ITEM 55, in its FILED mode. Don's ruling put both new routes "under
    # exactly the same standard and filter", so it was run as written first -- and that is how
    # the departure was found rather than assumed: it dropped `NVIDIA Guarantees ... Campus in
    # Ohio` and `Octave Intelligence Plc Listed on Nasdaq Stockholm`, both real corporate
    # events, because the conclusion list does not contain the verbs a company uses about
    # itself. `classify_filed` keeps the promotional test and drops the attribution test, with
    # that measurement in its docstring. A DECLARED DEPARTURE, not a quiet one.
    from .headline_rules import filter_titles

    split = filter_titles(found, filed_by_the_company=True)
    out["n_shown"] = split["n_shown"]
    out["n_excluded"] = split["n_excluded"]
    out["excluded_by_kind"] = dict(split["excluded_by_kind"])
    shown = split["shown"]
    shown.sort(key=lambda x: x.get("date") or "", reverse=True)
    out["items"] = shown
    # The pre-filter list, for the measurement script only -- never rendered, never sent to a
    # model. It exists so "which titles did the filter drop" is answerable.
    out["_all"] = found
    out["available"] = bool(shown)
    if not shown:
        if not out["filings_scanned"]:
            out["reason"] = "this company has filed no 8-K in its recent filing history"
        elif not out["exhibits_found"]:
            out["reason"] = ("this company's recent 8-K filings carry no press-release exhibit "
                             "(EX-99), so there is no filed release to show")
        elif not out["headings_read"]:
            out["reason"] = ("a press-release exhibit was found but no heading could be read "
                             "from it, so nothing is shown rather than a guessed title")
        else:
            out["reason"] = ("%d filed releases were found and none was a reported fact or an "
                             "attributed conclusion" % out["n_found"])
    return out
