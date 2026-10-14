"""WHICH HEADLINE SOURCES ARE ALLOWED, AND WHERE THE CONCLUSION/NARRATIVE LINE SITS.
[item 55]

Don's ruling, 2026-10-13: *"HEADLINES MAY COME FROM ANY VERIFIABLE, TRUSTWORTHY SOURCE, NOT ONLY
SEC AND YAHOO. The line is between a conclusion and a narrative: a reported fact or a conclusion
attributed to someone (guidance, an analyst's rating change, a regulator's decision, a press
release) is allowed; opinion and promotional pieces ("should you buy", "3 reasons it will soar",
price-prediction hype, paid promotion) are not. Every headline names its source and links to
it."*

THE STANDARD A SOURCE MUST MEET
-------------------------------
1. **A named publisher accountable for what it prints** — a wire service, an established
   financial or general news outlet, a company press-release wire, a regulator or an exchange.
2. **A link to the original**, so a reader can check the item rather than trust this page.
3. **Terms that allow showing a title and a link.** No paid source, no key, and no automated
   retrieval from a site whose terms forbid it.
4. **A per-company route.** A market-wide feed is the wrong SHAPE for a per-name page, and the
   measurements below show why rather than asserting it.

EVERY CANDIDATE THE RULING NAMED WAS MEASURED. NONE OF THEM EARNED A PLACE.
---------------------------------------------------------------------------
That is a finding, not a failure to do the work — the ruling's own instruction was to *"keep
only sources that earn their place"*. Measured on **NVDA, TSLA, KO, APLD and OCTV** (the last
two small, as asked), on 2026-10-13:

| candidate | result | why it is not kept |
|---|---|---|
| **SEC EDGAR** | **KEPT** | per-CIK, so every item is about the company *by construction*; terms unambiguous |
| **Yahoo Finance RSS** | **KEPT** | syndication feed, no key, publisher named per item; **44 of 86 titles (51%)** name the company |
| Seeking Alpha per-symbol RSS | **REJECTED ON TERMS** | the **best yield measured** — 102 of 132 (**77%**), 30 items a symbol — and its own terms forbid both halves: *"Use any robot, spider … to download, retrieve, index, 'data mine', 'scrape', 'harvest'"* and *"may not use, copy, display … republish … without our prior written consent"* |
| Nasdaq per-symbol | unreachable | `ReadTimeout` on **two endpoints at 60s**, after 45s in item 53's probe — three attempts |
| GlobeNewswire | HTTP 403 | both the keyword search and the subject feed |
| PR Newswire | reachable, wrong shape | 20 items, **0** naming any of the five; no per-company free route |
| Business Wire | no per-symbol feed | the published feed is market-wide |
| CNBC public RSS | reachable, wrong shape | 30 items, **0** naming any of the five |
| FDA / FTC / DOJ press feeds | reachable, wrong shape | **0 of 55** items named any of the five |

**THE MARKET-WIDE FEEDS ARE NOT WORTHLESS, THEY ARE THE WRONG SHAPE**, and the distinction
matters for whoever revisits this: an FDA decision feed is exactly the right source for a
biotech on an approval day, but an agency-wide feed of ~20 items has a vanishing chance of
naming any particular company, and none of these publishers offers a per-company query without a
key. **0 of 105 items across five such feeds** is the measurement; the route, not the publisher,
is what fails.

THE FILTER IS AN ALLOWLIST OF CONCLUSIONS, NOT A DENYLIST OF OPINION
--------------------------------------------------------------------
**MEASURED, AND THIS IS WHY.** A first cut denied the promotional shapes the ruling names —
"should you buy", "N reasons", price-prediction hype — and kept **93%** of Yahoo's on-company
titles and **97%** of Seeking Alpha's, including *"Coca-Cola or Chevron: The One Dividend Stock
I'd Hold for the Next 20 Years"*, *"Nvidia: The Buyback Is The Opportunity"* and *"Applied
Digital: More Than 600MW Could Drive The Next Leg Of Growth"* — all three opinion, all three
kept. **A denylist of opinion cannot be completed, because opinion is infinitely phrasable.**

A conclusion is not. Guidance, a rating change, a regulator's decision, a lawsuit, a contract, a
results release, an appointment, an acquisition — these have recognisable, enumerable markers,
and an allowlist of them can be audited by reading it. So an item is shown only if it carries a
**conclusion marker**, and is dropped if it carries a **promotional marker** even then.

**THE COST IS RECALL, AND IT IS PAID DELIBERATELY.** A genuine news item phrased unusually will
be dropped. The ruling's own remedy is carried: every exclusion is **counted**, so the page says
*"N headlines found, M shown"* and a reader can see the filter is doing something rather than
discovering a quiet list.
"""
from __future__ import annotations

import re

#: Sources allowed to supply a headline, with the reason each one meets the standard. A dict
#: rather than a list so the reason travels with the permission -- a bare allowlist is how a
#: source comes to be trusted because it is in a list.
ALLOWED_SOURCES = {
    "SEC EDGAR": {
        "kind": "regulator",
        "per_company": "by construction -- the feed is this company's own CIK",
        "terms": ("SEC: \"All Government-created content on sec.gov and EDGAR public filing "
                  "content are free to access and reuse.\" Declared User-Agent, under the "
                  "stated 10 requests/second ceiling."),
        "publisher_named": True,
    },
    "Yahoo Finance RSS": {
        "kind": "aggregator (each item names its own publisher)",
        "per_company": "a per-symbol feed, measured at 51% on-company over 86 titles",
        "terms": ("a public syndication feed served without a key; titles, publishers, dates "
                  "and links only, and no article text is ever requested"),
        "publisher_named": True,
    },
}

#: Why each measured candidate is NOT allowed. Kept in the code rather than only in a handoff,
#: because the next person to ask "why not Nasdaq?" will be reading this file.
REJECTED_SOURCES = {
    "Seeking Alpha per-symbol RSS":
        ("terms: its own ToS forbids automated retrieval (\"robot, spider ... 'scrape', "
         "'harvest'\") AND display (\"may not ... display ... republish ... without our prior "
         "written consent\"). The best yield measured -- 102 of 132 titles (77%) -- and not "
         "usable."),
    "Nasdaq per-symbol": ("unreachable: ReadTimeout on two endpoints at 60s, after 45s in "
                          "item 53's probe. Three attempts."),
    "GlobeNewswire": "HTTP 403 on both the keyword search and the subject feed.",
    "PR Newswire": ("reachable but market-wide: 20 items, 0 naming any of the five test "
                    "names. No per-company free route."),
    "Business Wire": "no per-symbol feed; the published one is market-wide.",
    "CNBC public RSS": "reachable but market-wide: 30 items, 0 naming any of the five.",
    "FDA / FTC / DOJ press feeds":
        ("reachable but market-wide: 0 of 55 items named any of the five. The right publisher "
         "for a regulatory event and the wrong ROUTE -- none offers a per-company query "
         "without a key."),
    "Stocktwits RSS": "HTTP 404 on every symbol.",
}

#: What makes an item a CONCLUSION: a reported fact, or a conclusion attributed to somebody.
#: Grouped so a reader can see the ruling's own categories in the code.
CONCLUSION_PATTERNS = {
    "results and guidance": [
        r"\bq[1-4]\b", r"\b(first|second|third|fourth)[- ]quarter\b", r"\bfull[- ]year\b",
        r"\bresults?\b", r"\bearnings\b", r"\breports?\b", r"\breported\b",
        r"\bguidance\b", r"\bforecasts?\b", r"\boutlook\b", r"\brevenue (rose|fell|up|down)\b",
        r"\bbeats?\b", r"\bmisses\b", r"\bto report\b", r"\bpre-?announce",
    ],
    # THE RULING ALLOWS "a conclusion ATTRIBUTED TO SOMEONE", and the canonical form of that
    # is "X says Y" -- which had no marker at all in the first cut, so
    # "EXCLUSIVE: Ross Gerber Says Tesla May Make Just 'a Few Hundred' Roadsters" was dropped
    # as unattributed when it is the most attributed shape there is. A fidelity gap against
    # the ruling rather than a tuning choice.
    "attributed statements": [
        r"\bsays?\b", r"\bsaid\b", r"\btold\b", r"\badmits?\b", r"\bconfirms?\b",
        r"\bdenies\b", r"\bwarns?\b", r"\bexpects?\b", r"\baccording to\b",
        r"\bexclusive:\b", r"\bcomments?\b", r"\binterview\b",
    ],
    # A price or volume MOVE is a reported fact: "Why Octave Intelligence Stock Slumped Today"
    # states what happened. These were all dropped as unattributed.
    "reported moves": [
        r"\bsoars?\b", r"\bslump(s|ed)?\b", r"\btumbles?\b", r"\bplunge[sd]?\b",
        r"\bjump(s|ed)?\b", r"\bsurge[sd]?\b", r"\bclimb(s|ed)?\b", r"\bslide[sd]?\b",
        r"\bsinks?\b", r"\brallie[sd]\b", r"\bgain(s|ed)?\b", r"\blose[sd]?\b",
        r"\bhits? (a )?(record|high|low)\b", r"\bup \d+%", r"\bdown \d+%",
    ],
    "analyst actions": [
        r"\b(upgrade[sd]?|downgrade[sd]?)\b", r"\binitiated at\b", r"\bresumed at\b",
        r"\bprice target (raised|lowered|cut|increased|trimmed)\b",
        r"\btarget (raised|lowered|cut)\b", r"\breiterate[sd]?\b",
        r"\b(overweight|underweight|equal[- ]weight|outperform|underperform)\b",
        r"\banalysts?\b", r"\brating\b",
    ],
    "regulators and courts": [
        r"\bfda\b", r"\bftc\b", r"\bdoj\b", r"\bsec\b", r"\bnhtsa\b", r"\beu\b",
        r"\bapprove[sd]?\b", r"\bclearance\b", r"\brejects?\b", r"\bprobe[sd]?\b",
        r"\binvestigat", r"\bsubpoena", r"\blawsuit\b", r"\bsue[sd]?\b", r"\bsettle[sd]?\b",
        r"\bfine[sd]?\b", r"\brecall[s]?\b", r"\bantitrust\b", r"\bcourt\b", r"\bruling\b",
        r"\bban(s|ned)?\b", r"\btariff",
    ],
    "corporate events": [
        r"\bannounce[sd]?\b", r"\bto acquire\b", r"\bacquisition\b", r"\bmerger?\b",
        r"\bstake\b", r"\bdivests?\b", r"\bspin[- ]?off\b", r"\bipo\b",
        r"\b(names|appoints|hires|elects)\b", r"\b(ceo|cfo|coo|chair)\b", r"\bresign",
        r"\bsteps? down\b", r"\bdividends?\b", r"\bbuybacks?\b", r"\brepurchases?\b",
        r"\bsurveys?\b", r"\bfinds\b", r"\bopens?\b", r"\bclose[sd]?\b",
        r"\bsplit\b", r"\boffering\b", r"\bconvertible\b", r"\bnotes?\b",
        r"\bcontract\b", r"\bdeal\b", r"\bpartner(s|ship|ed)?\b", r"\bcollaborat",
        r"\bwins?\b", r"\bawarded?\b", r"\blaunch(es|ed)?\b", r"\bunveils?\b",
        r"\bexpands?\b", r"\binvest(s|ment|ing)?\b", r"\blayoffs?\b", r"\bcuts? \d+",
        r"\bfiles?\b", r"\bfiling\b", r"\b8-k\b", r"\b10-[qk]\b",
    ],
}

#: Promotional and opinion formats, which drop an item even if it also matched above. The
#: ruling names the first four shapes; the rest are the forms they actually take in a feed.
PROMOTIONAL_PATTERNS = [
    r"\bshould you (buy|sell|own|hold)\b", r"\bis .{0,28}\ba (buy|sell|steal|bargain)\b",
    r"^\s*\d+\s+(reasons?|stocks?|things?|charts?|ways?|picks?)\b",
    r"\b\d+\s+reasons?\b", r"\b(top|best)\s+\d+\b", r"\bbest .{0,24}stocks? to buy\b",
    r"\bcould (soar|double|triple|skyrocket|explode|make you)\b",
    r"\bprice prediction\b", r"\bmillionaire\b", r"\bif you('d| had) invested\b",
    r"\bturn \$?\d+\b", r"\bretire (on|early|at)\b", r"\bhold forever\b",
    r"\bsponsored\b", r"\bpaid (post|promotion)\b", r"\bad(vertisement)?:\b",
    # First-person and judgement formats -- opinion by form rather than by topic.
    r"\bmy (notes|take|thesis|view|pick|portfolio)\b", r"\bi (understand|think|like|would|'d)\b",
    r"\bi'?m\b", r"\bhere'?s why\b", r"\bnot buying\b", r"\btrades? at \d",
    r"\bwhat could derail\b", r"\bwants? to\b",
    r"\bi'?d\b", r"\bwe (like|prefer|think)\b", r"\bdeserves? a\b",
    r"\blooks too (low|high|cheap|expensive)\b", r"\b(under|over)valued\b",
    r"\bfair value\b", r"\bbuy the dip\b", r"\bis the opportunity\b",
    r"\bwhere .{0,28}could be headed\b", r"\bin \d+ years?\b", r"\bvs\.? \w+: which\b",
    r"\bdividend king\b", r"\bthe one .{0,24}i\b", r"\bcould drive\b",
    r"\bthe next leg\b", r"\bwhy .{0,24}is (the|a) \b",
]

_CONCL = [(g, re.compile(p, re.I)) for g, ps in CONCLUSION_PATTERNS.items() for p in ps]
_PROMO = [re.compile(p, re.I) for p in PROMOTIONAL_PATTERNS]


def classify(title: str) -> dict:
    """Is this headline a CONCLUSION we may show, and why or why not?

    Returns `{"show": bool, "kind": str, "reason": str, "matched": str}`. Never raises.

    **A PROMOTIONAL MARKER OVERRIDES A CONCLUSION MARKER**, deliberately: "3 Reasons Nvidia
    Could Soar After Earnings" matches `earnings` and is exactly what the ruling excludes. So
    the order is drop-first, and that order is the rule.
    """
    t = str(title or "").strip()
    if not t:
        return {"show": False, "kind": "empty", "reason": "no title", "matched": ""}
    for p in _PROMO:
        m = p.search(t)
        if m:
            return {"show": False, "kind": "promotional",
                    "reason": ("an opinion or promotional format, which the ruling excludes"),
                    "matched": m.group(0)}
    for group, p in _CONCL:
        m = p.search(t)
        if m:
            return {"show": True, "kind": group,
                    "reason": "a reported fact or a conclusion attributed to someone",
                    "matched": m.group(0)}
    return {"show": False, "kind": "unattributed",
            "reason": ("no reported fact or attributed conclusion could be identified in the "
                       "title, so it is not shown"),
            "matched": ""}


def filter_titles(items, key="title") -> dict:
    """Split a list of headline dicts into shown and excluded, with counts.

    **THE COUNTS ARE PART OF THE ANSWER**, per the ruling: the page says "N found, M shown", so
    a reader can see the filter is working rather than discover a quiet list.
    """
    shown, excluded = [], []
    by_reason = {}
    for it in items or []:
        title = (it or {}).get(key) if isinstance(it, dict) else str(it)
        c = classify(title)
        if isinstance(it, dict):
            it = dict(it)
            it["kind"] = c["kind"]
        if c["show"]:
            shown.append(it)
        else:
            excluded.append(it)
            by_reason[c["kind"]] = by_reason.get(c["kind"], 0) + 1
    return {"shown": shown, "excluded": excluded,
            "n_found": len(items or []), "n_shown": len(shown),
            "n_excluded": len(excluded), "excluded_by_kind": by_reason}
