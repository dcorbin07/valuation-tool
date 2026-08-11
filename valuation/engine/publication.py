"""THE publication decision. One function, one band, one reason string.

Why this module exists (CONSOLIDATE-1, 2026-08-06)
--------------------------------------------------
"May this fair value be shown?" had no owner, so every surface answered it independently and
they disagreed. Four sessions in a row found "a new bug" that was the same decision implemented
one more time:

  * the valuation page refused above 5x price          (`pipeline.publication_guard`)
  * the screener's growth lens capped at 20x           (`fairvalue.MAX_GROWTH_VALUE`)
  * the screener's multiples lens capped at nothing    (`fairvalue._mature_value`)
  * `pipeline.py` and `scoring.py` each restated `ratio > 5 or ratio < 0.2` as literals
  * `screen.py::_enrich_with_dcf` wrote `fair_value = None` on a refusal and recorded nothing,
    so `estimate_fair_values` read that None as "no DCF computed yet" and substituted a peer
    estimate -- **erasing the refusal**, which is how KSPI, STLA and CHTR sat on the public hot
    list with fair values while their own valuation page refused them outright.

Nothing had regressed. There were simply five copies. This module is the one copy.

The rule for anyone adding a surface: **import `decide` and read its verdict.** Do not read the
band and compare it yourself, do not restate the threshold, and do not write your own words for
the refusal. `test_publication_sites_are_not_duplicated` fails on the day you do.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# THE band. A fair value more than this multiple of the market price is treated as a data
# problem (currency, share count, a one-off) rather than an opportunity. Every surface that
# needs it imports it from here.
#
# The comparison is `ratio > FV_BAND_HIGH` refuses, `ratio == FV_BAND_HIGH` publishes. That
# matches both historical forms it replaces, so no name sitting exactly on the band changes
# state as a result of the consolidation.
FV_BAND_HIGH = 5.0

# The LOW side deliberately warns rather than refuses. A fair value far BELOW the price is not
# the failure this guards against -- the product is not telling anyone to buy -- and suppressing
# it would hide legitimate "this is expensive" verdicts, including the honest net-cash floor on
# a revenue-less shell. Established in Part 1 by a test that caught the symmetric version.
FV_BAND_LOW = 0.2

# Canonical row keys for a recorded refusal. `valuation/web/withhold.py` already honours these
# names; they live here so the scan and the web surface cannot drift apart.
ROW_WITHHELD = "fair_value_withheld"
ROW_WITHHELD_REASON = "fair_value_withheld_reason"

# WHICH KIND OF SILENCE THIS IS. Both blank the fair value; they are not the same claim and
# they must not read as the same claim.
#
#   refused      the model produced a number and the guard REJECTED it. A statement about the
#                VALUATION. Stable: it will say the same thing tomorrow.
#   unavailable  the data for this name could not be fetched on this scan, so the model was
#                never in a position to have an opinion. A statement about the FETCH, and
#                TEMPORARY — the quota resets and the next scan retries it with no
#                intervention.
#
# Collapsing these is how "we could not look" gets read as "we looked and refused", which
# would make a transient feed problem look like a permanent verdict on a company.
ROW_WITHHELD_KIND = "fair_value_withheld_kind"
KIND_REFUSED = "refused"
KIND_UNAVAILABLE = "unavailable"

UNAVAILABLE_REASON = (
    "No fair value this scan: the data for this name could not be fetched, so the model was "
    "never able to form a view. This is a temporary data problem, not a judgement about the "
    "company — the next scan retries it automatically.")

# --------------------------------------------------------------------------------------- #
# THE LABELS THAT DESCRIBE THE VALUE, AND WHY THEY GO WITH IT (LA10, 2026-08-10).
#
# `estimate_fair_values` writes `fair_value_method` ("blended") and `fair_value_confidence`
# ("medium") alongside the number. The band withhold in `web/withhold.py` then blanked the
# number and left both labels standing, so a refused row shipped as
#
#     {fair_value: null, fair_value_method: "blended", fair_value_confidence: "medium",
#      fair_value_withheld: true}
#
# — the confidence of a number that is not there. Cosmetic today (no surface draws it), and
# it is exactly the shape this module exists to eliminate: a label outliving the value it
# described. The audit found the same shape three times in documentation; this is the one
# instance of it in a served payload.
#
# THE TWO FIELDS ARE TREATED DIFFERENTLY, ON PURPOSE.
#   * `fair_value_method` is SET to "withheld" rather than cleared. That word is already this
#     project's vocabulary for it — `fairvalue.py`'s own refusal branch writes it and
#     `tests/test_guards.py` pins it — and a positive label beats an empty cell for the same
#     reason a refusal writes a REASON instead of leaving a gap: a blank invites someone to
#     "fix" the missing data later.
#   * `fair_value_confidence` is CLEARED. It is a graded scale ("low" / "medium") with no
#     withheld rung, and writing a word into a scale invites a renderer to sort or compare it.
#     The row already carries `fair_value_withheld: true` as the positive marker.
ROW_WITHHELD_METHOD = "withheld"

#: Everything derived from the fair value that a refusal must clear. `fair_value` and
#: `fair_value_method` are handled explicitly in `strip_derived_fields` (one is the value,
#: the other is set rather than cleared), so they are deliberately not in this tuple.
ROW_DERIVED_FIELDS = ("upside", "fair_value_confidence")


@dataclass(frozen=True)
class PublicationVerdict:
    """The answer, the bar it was measured against, and why — computed once."""
    publish: bool
    value: Optional[float]           # the publishable value, or None when refused
    withheld_value: Optional[float]  # what was suppressed (for guards only; never shown)
    ratio: Optional[float]           # observed fair value / price
    band: float                      # the bar it was measured against
    reason: str                      # empty when publishable

    @property
    def implausible_high(self) -> bool:
        """The >band case specifically — the one that also caps the opportunity score."""
        return self.ratio is not None and self.ratio > self.band


def _currency_refusal(cd) -> str:
    """Statements in one currency and a price in another, with no usable conversion."""
    if cd is None:
        return ""
    fin = (getattr(cd, "financial_currency", "") or "").upper()
    px_ccy = (getattr(cd, "currency", "") or "USD").upper()
    if getattr(cd, "fx_unresolved", False):
        return (f"Cannot value this name: the statements are reported in "
                f"{fin or 'a foreign currency'} but the price is in {px_ccy}, and the exchange "
                f"rate could not be resolved. Every figure would be wrong by an unknown factor, "
                f"so no fair value is published.")
    if fin and fin != px_ccy and getattr(cd, "fx_rate", None) is None:
        return (f"Cannot value this name: the statements are in {fin} and the price is in "
                f"{px_ccy}, but no currency conversion was applied. No fair value is published.")
    return ""


def decide(value, price, *, cd=None, growth_led: bool = False) -> PublicationVerdict:
    """Decide whether `value` may be published against `price`. THE decision.

    `cd` is optional: the engine passes a CompanyData so the currency checks apply; the
    screener's lenses have only a number and a price and pass neither. `growth_led` is
    accepted for callers that carry it — it affects the LOW-side wording, never the refusal,
    because the low side does not refuse.
    """
    band = FV_BAND_HIGH
    ccy = _currency_refusal(cd)
    if ccy:
        return PublicationVerdict(False, None, _f(value), None, band, ccy)

    v, px = _f(value), _f(price)
    if v is None or px is None or px <= 0 or v <= 0:
        # Not a refusal — there is simply nothing to publish. Callers distinguish the two by
        # `reason`, which stays empty here.
        return PublicationVerdict(False, None, None, None, band, "")

    ratio = v / px
    if ratio > band:
        return PublicationVerdict(
            False, None, v, ratio, band,
            f"Cannot value this name: the model's ${v:,.2f} is {ratio:.1f}x the ${px:,.2f} "
            f"price. That gap is a data problem (currency or share count), not an "
            f"opportunity, so no fair value is published.")
    return PublicationVerdict(True, v, None, ratio, band, "")


def _f(x) -> Optional[float]:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if (x != x or x in (float("inf"), float("-inf"))) else x


def strip_derived_fields(row: dict) -> None:
    """Clear the value AND every label that described it. See ROW_DERIVED_FIELDS above.

    Split out from `record_refusal` so the band withhold in `web/withhold.py` can apply the
    identical rule at the other end of the pipeline. Two places decide a row is withheld;
    there is one definition of what that does to the row, because two would drift — the same
    argument this module makes about the band itself.

    Does NOT set the withheld flag or reason: those say a refusal happened, this says what a
    refusal does to the row, and the band path writes its own reason.
    """
    row["fair_value"] = None
    for k in ROW_DERIVED_FIELDS:
        if k in row:
            row[k] = None
    row["fair_value_method"] = ROW_WITHHELD_METHOD


def record_refusal(row: dict, reason: str) -> None:
    """Mark a scan row as REFUSED rather than merely empty.

    The one-line half of CONSOLIDATE-1 and the highest-value line in it. A blank
    `fair_value` reads downstream as "not computed yet" and invites a substitute; a recorded
    refusal reads as a decision and is honoured.
    """
    strip_derived_fields(row)
    row["upside"] = None                 # explicit: `upside` is cleared even if it was absent
    row[ROW_WITHHELD] = True
    row[ROW_WITHHELD_REASON] = reason or "No fair value is published for this name."
    row[ROW_WITHHELD_KIND] = KIND_REFUSED


def record_unavailable(row: dict, reason: str = "") -> None:
    """Mark a row as WITHHELD BECAUSE WE COULD NOT LOOK — the fail-closed half.

    Adopted 2026-08-11 on Don's decision, and the evidence for it is this project's own
    measurement: failing OPEN served peer estimates up to 2.1x the model's own valuation on
    names whose data never arrived (DB 88.69 against the model's 42.25; CIB 167.42 against
    90.93), alongside one name the model refuses outright at 5.6x. A peer estimate nobody
    checked is the confident-wrong-number failure this module exists to prevent, and the ~5%
    of served rows this blanks is the accepted price.

    Deliberately NOT `record_refusal` with different wording. The KIND is its own field so the
    two survive the database round trip and the UI can render them differently: a reader shown
    the same badge for "we could not fetch this today" and "the model rejects this valuation"
    has been told one thing when two are true. And this one is TEMPORARY — the quota resets and
    the next scan retries the name with no intervention, which the reason text says out loud so
    a withheld name does not read as a permanent verdict.
    """
    strip_derived_fields(row)
    row["upside"] = None
    row[ROW_WITHHELD] = True
    row[ROW_WITHHELD_REASON] = reason or UNAVAILABLE_REASON
    row[ROW_WITHHELD_KIND] = KIND_UNAVAILABLE
