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


def record_refusal(row: dict, reason: str) -> None:
    """Mark a scan row as REFUSED rather than merely empty.

    The one-line half of CONSOLIDATE-1 and the highest-value line in it. A blank
    `fair_value` reads downstream as "not computed yet" and invites a substitute; a recorded
    refusal reads as a decision and is honoured.
    """
    row["fair_value"] = None
    row["upside"] = None
    row[ROW_WITHHELD] = True
    row[ROW_WITHHELD_REASON] = reason or "No fair value is published for this name."
