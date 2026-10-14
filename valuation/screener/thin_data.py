"""A NAME SCORED ON TOO FEW THEMES IS MARKED, AND NOT RANKED AT THE TOP.  [item 54 part 3]

THE TEST CASE IS THE #1 NAME ON THE LIVE LIST
---------------------------------------------
Item 53 part 7 found `SMFSY` at **rank 1 of 1,440 with a hot score of 100.0, scored on ONE
theme** — `size` alone, which `CLAUDE.md` records as having the **worst** theme IC (−0.30) of
the nine while carrying the composite's entire statistical significance. Two more sat in the
served top 100 on three themes or fewer (`WPP` rank 18 on three, `WFG` rank 95 on two).

**WHY IT IS INVISIBLE WITHOUT THIS.** `_branch` redistributes a missing theme's weight across
the themes that remain, deliberately and correctly, so the composite stays *comparable* — a
one-theme name produces a number on the same scale as an eight-theme name, and nothing about
the number says which it is. That is exactly what makes it worth marking.

WHAT THIS IS AND IS NOT
-----------------------
**IT IS A DISPLAY RULE.** No score changes, no weight changes, no rank is recomputed, and
`build_index` and the rebalance path are not touched at all — that would be a construction
change and therefore a vintage event, which Don's ruling explicitly excludes. A thin name keeps
its score and its rank; what changes is that the page says so and stops presenting it at the top
of a list as though it were measured like its neighbours.

Scope, from the ruling: **the live hot list and the Index tab's "today's hot score" labels
only.**

THE RULE, STATED RATHER THAN BURIED
-----------------------------------
Fewer than **four** scored themes is thin. The denominator is the **seven** themes each rulebook
weights — measured, not assumed: `WEIGHTS_ESTABLISHED` carries seven non-zero weights (and no
`growth` key at all) and `WEIGHTS_SPECULATIVE` carries seven (and no `quality` key), so the
union across both is eight and any single name's own rulebook weights seven of them. `low_risk`
and `sentiment` are 0.0 in both and can never contribute to anybody, so they are excluded from
the count — including them would mark every name in the product as thin.

**FOUR IS A MAJORITY OF SEVEN, which is the whole derivation.** It is not tuned and nothing was
swept to find it: a name scored on most of what its rulebook weights is being measured, and a
name scored on a minority of it is being extrapolated from. The number is stated on the page so
a reader can disagree with it.

THE WORDING IS `score_confidence.THIN_DATA`, NOT A NEW SENTENCE
---------------------------------------------------------------
V3 measured this exact effect — *"names near the top are scored on less information than the
average name, more so than chance would produce"* (real top-decile present-weight 0.94798
against 9 of 500 noise draws that thin, empirical p 0.018) — and that module exists because a
surface which rewrites a calibrated sentence is how a hedge becomes a claim. So this module
holds the RULE and points at that module for the LANGUAGE.
"""
from __future__ import annotations

#: Scored themes at or above this many: measured. Below it: thin. See the docstring for why
#: four, and `RULE_TEXT` for what the page says.
MIN_THEMES = 4

#: The two themes that carry weight 0.0 in BOTH rulebooks, so they can never contribute to any
#: name's composite and must not be counted against it. `low_risk` was zeroed on a held-out
#: test; `sentiment` has never been fed.
ZERO_WEIGHT = ("low_risk", "sentiment")

#: What the page says, in its own words, so a reader can check the rule rather than trust it.
RULE_TEXT = (
    "Scored on fewer than %d of the seven themes this name's rulebook weights. The ranking "
    "spreads a missing theme's weight over the rest so the number stays comparable, which is "
    "why a name like this can rank highly on very little information." % MIN_THEMES
)

#: The group heading on the hot list.
GROUP_LABEL = "Scored on too little data to rank"

#: One line beside the group, for a reader who wants the consequence rather than the rule.
GROUP_NOTE = (
    "These names are shown separately rather than mixed into the ranking above. Their scores "
    "and ranks are unchanged — nothing has been re-scored — but each rests on fewer than %d "
    "themes, so it is not comparable with a name scored on all of them." % MIN_THEMES
)


def weighted_theme_names(settings=None) -> list:
    """The themes that can contribute to any name, DERIVED from the weight sets.

    Derived rather than typed, which is the `MA5` lesson: a hand-maintained list of themes
    beside the weights that define them is how the two come apart. Returns the union across
    both rulebooks, minus anything weighted zero in both.
    """
    try:
        if settings is None:
            from . import settings as settings       # noqa: PLW0127
        names = set()
        for attr in ("WEIGHTS_ESTABLISHED", "WEIGHTS_SPECULATIVE"):
            for k, v in (getattr(settings, attr, None) or {}).items():
                if v:
                    names.add(str(k))
        return sorted(n for n in names if n not in ZERO_WEIGHT)
    except Exception:                                                       # noqa: BLE001
        return []


def theme_count(row) -> int:
    """How many themes this scan row was actually scored on.

    Counts `extra.factors`, which item 53 part 7a established is the exact discriminator: it
    is non-null on every attributed theme and on exactly the scored-but-zero ones, with zero
    disagreements over 800 (row, theme) cells. The attribution list is NOT used, because
    `row_attribution` also drops a theme whose contribution rounds to zero -- a scored theme.
    """
    try:
        fac = ((row or {}).get("extra") or {}).get("factors") or {}
    except Exception:                                                       # noqa: BLE001
        return 0
    if not isinstance(fac, dict):
        return 0
    return sum(1 for k, v in fac.items() if v is not None and k not in ZERO_WEIGHT)


def assess(row) -> dict:
    """Is this row thin, and on what count? Never raises.

    `known` is False when the row carries no factor dict at all — an older snapshot, say.
    **A row we cannot count is NOT marked thin**, because "we do not know" and "scored on one
    theme" are different facts and marking the first as the second would put every row from a
    pre-item-53 snapshot into the thin group.
    """
    try:
        fac = ((row or {}).get("extra") or {}).get("factors") or {}
    except Exception:                                                       # noqa: BLE001
        fac = {}
    known = isinstance(fac, dict) and bool(fac)
    n = theme_count(row) if known else 0
    return {"known": bool(known), "themes_scored": n,
            "thin": bool(known and n < MIN_THEMES),
            "min_themes": MIN_THEMES,
            "rule": RULE_TEXT if (known and n < MIN_THEMES) else ""}


def mark(rows) -> dict:
    """Stamp `thin_data`, `themes_scored` and `thin_rule` onto each row. Returns a census.

    **IN PLACE AND ADDITIVE**: no row loses a field and no row's score or rank is touched, so
    every existing consumer of a scan row is unaffected.
    """
    n_thin = n_known = 0
    thin_tickers = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        a = assess(r)
        r["themes_scored"] = a["themes_scored"]
        r["thin_data"] = a["thin"]
        r["thin_rule"] = a["rule"]
        r["themes_known"] = a["known"]
        if a["known"]:
            n_known += 1
        if a["thin"]:
            n_thin += 1
            if r.get("ticker"):
                thin_tickers.append(str(r["ticker"]).upper())
    return {"min_themes": MIN_THEMES, "rule": RULE_TEXT, "label": GROUP_LABEL,
            "note": GROUP_NOTE, "n_rows": len(rows or []), "n_countable": n_known,
            "n_thin": n_thin, "thin_tickers": thin_tickers[:25],
            # A row whose theme count is UNKNOWN is reported separately from a thin one: an
            # absent measurement and a measurement of one theme must not read the same (`V6`).
            "n_uncountable": max(0, len(rows or []) - n_known)}
