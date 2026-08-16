"""
MA29 — "WHAT THE MODEL CANNOT VALUE". The refusal count, said out loud on the hot list.

WHY IT IS A FEATURE AND NOT PLUMBING. `LA1` was BLOCKING precisely because a refusal that
fails to record is invisible: `screen.py::_enrich_with_dcf` wrote `fair_value = None` on a
refusal, `estimate_fair_values` read that None as "no DCF yet" and substituted a peer estimate,
and the erased refusal let a name the model had declined outright sit on the public list with a
fair value on it. The recording half of that is fixed (`publication.record_refusal`). This is
the OTHER half: the count reaches a reader, so the failure mode is loud instead of silent and
the product's own users are the guard. Audit #2's structural finding was "correct in-process,
blind at the output boundary"; this is the cheapest available fix for it.

THE CLAIM IT MUST NEVER MAKE. Nothing here says a refused name is overvalued, risky or worth
avoiding. **A refusal is a statement about the MODEL, not about the company.** The model
produced a number, its own guard rejected the number, and the name is ranked exactly as any
other because the ranking never used a fair value. `BANNED` enumerates the wordings that would
assert otherwise and `violations()` is asserted against the RENDERED payload rather than
against this file, because rendering is where copy leaks (`dip_posture.py`'s design, carried
forward on the record's own recommendation, as `tenure.py` did for MA30).

FOUR THINGS THE AUDIT'S OWN PROPOSED SENTENCE GETS WRONG, each verified before this was built.
The proposal reads: *"Today the engine refused to publish a fair value for N of M names it
scored, because its estimate was more than X× the market price."*

  1. IT CONFLATES TWO KINDS OF SILENCE THAT `publication.py` EXISTS TO SEPARATE. `refused`
     means the model produced a number and the guard rejected it — a stable statement about the
     valuation. `unavailable` means the data could not be fetched, so the model never had an
     opinion — a TEMPORARY statement about the feed. That module's own comment says collapsing
     them "is how 'we could not look' gets read as 'we looked and refused', which would make a
     transient feed problem look like a permanent verdict on a company". They are counted and
     worded separately here. This is not hypothetical: `record_unavailable` was adopted on
     measured evidence that ~5% of served rows were affected, and the live scan of 2026-08-14
     read ZERO — so the two counts move independently and a day of feed trouble is exactly when
     a collapsed count would mislead most.
  2. THE CAUSE CLAUSE IS FALSE FOR SOME REFUSALS. `decide()` refuses for TWO reasons — the band
     (`ratio > FV_BAND_HIGH`) and an unresolved currency mismatch — and a currency refusal
     carries `ratio = None`, so there is no multiple to quote. Measured: `decide(100, 92.19,
     cd=<KZT statements, USD price>)` returns `ratio None`. The copy below therefore names the
     band as the USUAL cause without asserting it was this one.
  3. THE DENOMINATOR IS NOT "NAMES IT SCORED". Only the first `refusal_screen` ranked names are
     ASKED whether the model refuses them (production runs 500). On the live 2026-08-14 scan
     795 names were scored and 500 were checked, so "N of 795" would understate the rate by
     1.6x. The denominator here is `rows_checked` — **how many were asked** — and it is read
     from the audit block rather than recomputed.
  4. "TODAY" IS WRONG ON A STALE SCAN. The payload's own `scan_date` is what this describes,
     and a reader looking at a three-day-old scan should not be told it is today's.

ONE NUMBER, ONE MEANING. Every figure here is READ from `screen.publication_audit`, which
already computes `rows_checked`, `withheld_refused` and `withheld_no_data` on every scan and
already ships inside `health`. Nothing is recounted from the rows. A second count would be a
second definition of "refused" free to drift from the first, which is the defect
`engine/publication.py` was created to end — it found five copies of this one decision.

THE THIRD STATE, REPORTED BECAUSE IT IS REAL AND NOT IN THE AUDIT. `withhold_implausible_fair_
values` runs at SERVE time over the displayed slice and withholds a peer estimate that breaches
the band. It sets the withheld flag and a reason but **no KIND**, so it is neither `refused` nor
`unavailable` — a third meaning of "withheld", and a statement about the PEER ESTIMATOR rather
than about the model's own DCF. Its count was computed and thrown away at the call site (the
return value of that function was discarded), which is the same computed-and-discarded shape
`MA39` found in the results writer. It is captured and reported separately, with its own
denominator, because it is tier-dependent: it applies to the rows a given reader was served.

WHAT IT COSTS: zero trials. It measures no hypothesis and clears no threshold; it reports a
count that the scan already produced.

WHAT HAS BEEN SEEN, AND WHAT HAS NOT. The quantities WERE measured against the live public
payload on 2026-08-15 (scan of 2026-08-14): 800 universe, 795 scored, 500 asked, **2 refused, 0
unavailable**, and both withheld rows carried kind `refused`. So the arithmetic is verified
against production and not only against fixtures. The rendered wording has never been seen by a
user, and the third state above read zero on that day — it is verified by fixture only.
"""
from __future__ import annotations

import math
from typing import Any, Optional

#: The calibrated wording. One module owns it and a test pins it verbatim — the `V3` /
#: `score_confidence.py` rule, because copy that lives in a template drifts silently.
LABEL = "Names the model would not value"

EXPLAINER = (
    "Before a name is listed, the model is asked what it is worth and its own guard checks the "
    "answer. When the answer fails that check the number is not published — for this name, on "
    "any surface. This counts how often that happened. It is a statement about the MODEL, not "
    "about the company: the usual cause is a currency or share-count problem that makes the "
    "estimate wrong, not a finding that the stock is expensive. The ranking does not use a fair "
    "value, so these names are ranked on exactly the same basis as every other name here."
)

#: Wordings that would turn the disclosure into the claim it must not make. Checked against the
#: rendered payload, lower-cased, substring — deliberately blunt, since a near-miss costs a
#: reader a false inference about a real company and a false positive costs an author one edit.
BANNED = (
    "overvalued",
    "over-valued",
    "too expensive",
    "avoid these",
    "steer clear",
    "red flag",
    "warning sign",
    "poor quality",
    "low quality",
    "bad company",
    "not worth",
    "sell these",
    "worth avoiding",
    "failed our",
    "failed its",
)


def violations(text: str) -> list:
    """Which banned phrases a rendered string contains. Empty is the only passing answer."""
    low = (text or "").lower()
    return [p for p in BANNED if p in low]


def _int(x) -> Optional[int]:
    """A count, or None. A missing count must never read as zero — see `block`."""
    if isinstance(x, bool):          # bool is an int subclass; a flag is not a count
        return None
    try:
        n = int(x)
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None


def _plural(n: int, one: str, many: str) -> str:
    return one if n == 1 else many


def sentence(asked: int, refused: int, band: float, scan_date: str = "") -> str:
    """The refusal claim, in words, with no cause asserted that was not measured.

    The band is named as the USUAL cause rather than THE cause: `decide()` also refuses on an
    unresolved currency mismatch, and that branch carries no ratio at all (finding 2 above).
    """
    when = f"On the {scan_date} scan" if scan_date else "On this scan"
    if refused <= 0:
        return (f"{when} the model was asked to value the top {asked:,} names and declined "
                f"none of them.")
    nm = _plural(refused, "name", "names")
    it = _plural(refused, "it", "them")
    return (f"{when} the model was asked to value the top {asked:,} names and declined to "
            f"publish a fair value for {refused:,} of them. In each case the model produced a "
            f"number and its own guard rejected {it} — usually because the estimate came out "
            f"past {band:g}x the market price, which is almost always a currency or share-count "
            f"problem rather than an opportunity. The {nm} "
            f"{_plural(refused, 'is', 'are')} still ranked normally: the ranking never uses a "
            f"fair value.")


def unavailable_sentence(unavailable: int) -> str:
    """The OTHER kind, worded as temporary — because it is. See finding 1."""
    nm = _plural(unavailable, "name", "names")
    return (f"A further {unavailable:,} {nm} had no fair value this scan because "
            f"{_plural(unavailable, 'its', 'their')} data could not be fetched, so the model "
            f"was never able to form a view. That is a temporary feed problem, not a judgement "
            f"about the {_plural(unavailable, 'company', 'companies')} — the next scan retries "
            f"{_plural(unavailable, 'it', 'them')} automatically.")


def display_sentence(n: int, displayed: int, band: float) -> str:
    """The third state: a PEER estimate that breached the band on the rows actually served.

    `n` must be the count of served rows that are withheld and carry NO `kind` — not the return
    value of `withhold_implausible_fair_values`, which increments for pre-marked rows too and
    is therefore the TOTAL withheld in the slice. Using the return value here would have
    described the model's own refusals as peer-estimate withholds.
    """
    nm = _plural(n, "name", "names")
    return (f"On the {displayed:,} {_plural(displayed, 'name', 'names')} shown here, {n:,} "
            f"{nm} also had a quick peer-relative estimate withheld for breaching the same "
            f"{band:g}x band. That is a limit on the shortcut estimate, not on the model.")


def block(publication_audit: Any, *, scan_date: str = "", displayed=None,
          display_withheld=None, display_peer_only=None) -> dict:
    """The MA29 payload block. READS the scan's own audit; recounts nothing.

    ADDITIVE AND FAIL-SOFT. A scan with no audit block — every snapshot saved before
    `publication_audit` existed — returns `available: False` and no sentence, rather than
    `0 refused`, which would be a confident wrong claim that the model refused nobody. A
    missing count and a zero count are different statements and only one of them is true.
    """
    out = {
        "available": False,
        "label": LABEL,
        "explainer": EXPLAINER,
        "asked": None,
        "refused": None,
        "unavailable": None,
        "band": None,
        "sentence": None,
        "unavailable_sentence": None,
        "display_withheld": None,
        "display_peer_only": None,
        "displayed": None,
        "display_sentence": None,
    }
    pa = publication_audit if isinstance(publication_audit, dict) else {}
    asked = _int(pa.get("rows_checked"))
    refused = _int(pa.get("withheld_refused"))
    unavailable = _int(pa.get("withheld_no_data"))
    # `float()` accepts "nan" and "inf" where `int()` raises — MA53's finding — and a NaN band
    # would render as "past nanx the market price" rather than failing. Refuse it outright.
    try:
        band = float(pa.get("band"))
    except (TypeError, ValueError):
        band = None
    if band is not None and not math.isfinite(band):
        band = None
    if asked is None or refused is None or band is None or asked <= 0:
        return out

    out["available"] = True
    out["asked"] = asked
    out["refused"] = refused
    out["band"] = band
    out["sentence"] = sentence(asked, refused, band, scan_date=scan_date)
    if unavailable is not None:
        out["unavailable"] = unavailable
        if unavailable > 0:
            out["unavailable_sentence"] = unavailable_sentence(unavailable)

    # The serve-time figures, kept apart from the two scan-time kinds and carrying their own
    # denominator because they are tier-dependent — a reader served 50 rows and one served 500
    # are looking at different slices, and one number cannot describe both.
    #
    # TWO DIFFERENT QUANTITIES, AND CONFLATING THEM WAS A REAL DEFECT IN THIS MODULE'S FIRST
    # CUT. `display_withheld` is the return value of `withhold_implausible_fair_values`, which
    # increments for rows that were ALREADY marked withheld at scan time as well as for rows it
    # newly withholds — so it is the TOTAL withheld in the served slice, and on the live scan it
    # includes the 2 model refusals. `display_peer_only` is the third state proper: withheld
    # with NO `kind`, i.e. a peer estimate that breached the band. Only the second gets the
    # sentence, because only the second is a statement about the shortcut estimator.
    n_shown = _int(displayed)
    n_total, n_peer = _int(display_withheld), _int(display_peer_only)
    if n_shown is not None and n_shown > 0:
        if n_total is not None:
            out["display_withheld"] = n_total
        if n_peer is not None:
            out["display_peer_only"] = n_peer
        if n_total is not None or n_peer is not None:
            out["displayed"] = n_shown
        if n_peer:
            out["display_sentence"] = display_sentence(n_peer, n_shown, band)
    return out


def rendered_text(blk: dict) -> str:
    """Every string this block would put in front of a reader, for the copy assertion.

    The BANNED check runs against THIS — the rendered payload — and not against the module
    source, because a phrase can be assembled at render time from parts that are each innocent.
    """
    if not isinstance(blk, dict):
        return ""
    keys = ("label", "explainer", "sentence", "unavailable_sentence", "display_sentence")
    return " ".join(str(blk.get(k) or "") for k in keys)
