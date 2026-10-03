"""
Company classification — the "adaptive" part of the engine.

Different kinds of companies need different DCF assumptions. A mature, cash-
generative firm (Nike, Coca-Cola) is modeled very differently from a fast-
growing cash-burner (early-stage SaaS) or a cyclical (energy, materials). We
detect the regime from the financials and let it drive the assumption logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..data.models import CompanyData

# THE REGIME FOR "WE DO NOT KNOW WHAT THIS IS". Every other regime is a claim about the
# business; this one is a claim about our own knowledge, and it exists because the alternative
# -- letting an unknown sector fall through to the growth branch -- valued four of four
# financials with the unlevered FCFF model on the public site on 2026-09-30.
UNKNOWN = "unknown"

CYCLICAL_SECTORS = {"Energy", "Basic Materials", "Industrials"}
FINANCIAL_SECTORS = {"Financial Services", "Financials", "Financial"}

# ITEM 25 -- `"reit\u2014"` WAS AN EM DASH AND HAS THEREFORE NEVER MATCHED ANYTHING.
#
# The live industry strings are `"REIT - Retail"` and `"REIT - Industrial"`: a HYPHEN-MINUS with
# spaces. The hint carried U+2014 EM DASH, so `"reit\u2014" in "reit - retail"` is False and
# every REIT fell straight through to the growth/mature branches. Measured on the service
# 2026-10-03: Realty Income (O) came back `regime: growth, dcf_reliability: high` with a fair
# value of $9.46 against a $54.13 price, and Prologis (PLD) `regime: mature, high` at $20.39
# against $128.91.
#
# A TYPOGRAPHIC CHARACTER IN A MATCHER AGAINST VENDOR DATA IS NOT A TYPO, IT IS A DEFECT THAT
# CANNOT FIRE -- and it fails SILENTLY, because the fall-through produces a confident number
# rather than an error. The hint is removed from this tuple entirely: a REIT is not a financial
# and routing it there would hand it the justified-P/B-from-ROE model, which is a bank's model
# and not a REIT's. It gets its own regime below.
FINANCIAL_INDUSTRY_HINTS = ("bank", "insurance", "capital markets", "mortgage")

# --- REITs -------------------------------------------------------------------------------
#
# WHY A REIT CANNOT BE VALUED BY UNLEVERED FCFF, stated as the measurement that shows it: on
# the live service O's DCF-per-share came back at **$0.7455** and carried **75% of the blend**,
# giving $9.46 on a $54.13 stock. That is not a data error. A REIT's capex IS its business --
# acquiring and developing property -- so free cash flow AFTER capex is small or negative by
# construction, every year, for a healthy company. The model is answering a question the
# business does not pose.
#
# The warning the site showed said *"almost certainly a data problem (currency or share count),
# not a real opportunity. Verify the figures"*. That is the WRONG CAUSE, and a mis-attributed
# warning is worse than none: it points the reader, and the next person to look at the code, at
# the data when the model is what is wrong.
REIT_SECTORS = {"Real Estate"}
#: Matched case-insensitively as a SUBSTRING of the industry, so "REIT - Retail",
#: "REIT—Diversified" and "Reit Office" all match. A separator is deliberately NOT required:
#: requiring one is how the em dash above came to be load-bearing.
REIT_INDUSTRY_HINTS = ("reit", "real estate investment trust")

# --- Regulated utilities -----------------------------------------------------------------
#
# THE SAME PROBLEM AND A SECOND ONE. A regulated utility's capex is RATE-BASE INVESTMENT -- the
# asset the regulator allows it to earn a return on -- so persistent negative free cash flow is
# the business model rather than a burn. Measured on the service: NEE came back `regime: growth,
# dcf_reliability: high` (and `confidence: high`, with NO implausibility warning at all) at a
# fair value of $15.89 against $76.83; DUK came back `mature` at $43.50 against $114.13, with
# `is_cash_burning` True and the driver *"Cash-burning: ~0.1 yrs of runway at the current
# burn"*.
#
# **A REGULATED UTILITY READING AS ~0.1 YEARS FROM INSOLVENCY IS A CATEGORY ERROR**, and it is
# the sharper half: the FCFF number is merely wrong, while the runway sentence is a solvency
# claim about a company whose negative FCF is a regulatory asset.
#
# NOTE THE TWO NAMES LAND IN DIFFERENT REGIMES -- NEE in growth, DUK in mature -- purely because
# NEE's blended growth (0.1045) clears the 0.10 bar and DUK's (0.0469) does not. So the defect
# produced two different wrong outputs from one cause, which is why the sector is tested BEFORE
# the growth branches rather than after, as `CYCLICAL_SECTORS` is.
REGULATED_SECTORS = {"Utilities"}
REGULATED_INDUSTRY_HINTS = ("utilities", "regulated electric", "regulated gas",
                            "regulated water")


def _note_sector_source(c, cd) -> None:
    """Say WHERE the sector came from, in the same object as the decision it drove.

    The live defect disclosed itself in `quality_notes` -- *"Yahoo `info` unavailable"* -- while
    `classification.reasons` gave a confident, coherent *"High revenue growth (~26%)"* and said
    nothing about the industry being unknown. **A disclosure in a different object from the
    decision it qualifies is one a reader of the decision never sees.** So when the sector came
    from anywhere other than the ordinary primary fetch, the classification says so itself.
    """
    src = getattr(cd, "sector_source", "") or ""
    if src and src != "primary":
        c.reasons.append("Sector resolved from %s (the market-data profile did not return one)."
                         % {"scan": "the latest scan snapshot",
                            "sec_sic": "the SEC's filed SIC code",
                            "fmp_profile": "the profile API"}.get(src, src))


@dataclass
class Classification:
    regime: str = "mature"           # mature | growth | hypergrowth | cyclical | financial
    is_cash_burning: bool = False
    blended_growth: Optional[float] = None   # best forward-ish revenue growth estimate
    rule_of_40: Optional[float] = None       # growth% + fcf-margin% (for growth names)
    dcf_reliability: str = "high"    # high | medium | low  (how much to trust the DCF)
    reasons: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "regime": self.regime,
            "is_cash_burning": self.is_cash_burning,
            "blended_growth": self.blended_growth,
            "rule_of_40": self.rule_of_40,
            "dcf_reliability": self.dcf_reliability,
            "reasons": self.reasons,
        }


# The band a next-year REVENUE growth estimate must fall in to be believed. These are
# the same numbers the blend has always clamped to — the change is rejecting an input
# that lands outside them instead of squashing it onto the boundary.
_PLAUSIBLE_GROWTH = (-0.30, 1.00)

#: Blended revenue growth at or below which a company is DECLINING rather than mature.
#:
#: ITEM 25. NOT a calibrated bar and it is labelled as one of convenience, because nothing in
#: this project has measured where "mature" stops and "shrinking" starts. What it has to do is
#: narrow: separate a company whose revenue is genuinely contracting from one that is merely
#: growing slowly, and do it without re-labelling the second as the first. MRNA at -16.05% is
#: the case it exists for; TSLA at +7.84% must not be touched by it, and is not.
#:
#: -5% rather than 0% for a measured reason: `_blended_growth` mixes a 3-year CAGR with the
#: latest year-on-year reading, so a flat business with one soft year lands slightly negative,
#: and a 0% bar would relabel it as declining on noise. A margin keeps the branch for companies
#: whose contraction is the trend rather than the sampling.
DECLINING_GROWTH = -0.05


def _blended_growth(cd: CompanyData) -> Optional[float]:
    """A robust forward-ish growth estimate: analyst consensus if available,
    otherwise blend of 3y CAGR and latest YoY, bounded to sane values."""
    candidates = []
    # An "analyst revenue growth" outside the plausible band is not an aggressive
    # forecast, it is the wrong number — DISCARD it rather than clamp it. Clamping was
    # the actual defect: the bound at the bottom of this function squashed GILD's 15.0829
    # and MRK's 2.4942 into a tidy-looking 1.00, which then read as a legitimate 100%
    # growth forecast, classified two mature pharma names as HYPERGROWTH, and handed them
    # a 60% start growth for 10 years (revenue x17.2). Squashing garbage to the edge of
    # the valid range disguises it as data; rejecting it lets the 3y CAGR and TTM carry
    # the estimate, which for those two names is ~3%.
    # Source of the garbage, upstream and NOT fixed here (different lane): yahoo.py:293
    # reads `growth_estimates.loc["+1y"].iloc[0]`, which is the `stockTrend` column —
    # EARNINGS growth, not revenue — and it explodes off a negative base.
    a_g = cd.analyst_rev_growth_next
    if a_g is not None and _PLAUSIBLE_GROWTH[0] <= a_g <= _PLAUSIBLE_GROWTH[1]:
        candidates.append(("analyst", a_g, 0.5))
    if cd.rev_cagr_3y is not None:
        candidates.append(("3y_cagr", cd.rev_cagr_3y, 0.3))
    if cd.rev_growth_ttm is not None:
        candidates.append(("ttm_yoy", cd.rev_growth_ttm, 0.2))
    if not candidates:
        return None
    wsum = sum(w for _, _, w in candidates)
    g = sum(v * w for _, v, w in candidates) / wsum
    # Bound to a plausible modeling range.
    return max(-0.30, min(1.00, g))


def classify(cd: CompanyData) -> Classification:
    c = Classification()
    g = _blended_growth(cd)
    c.blended_growth = g
    fcf_m = cd.fcf_margin
    c.is_cash_burning = (cd.fcf is not None and cd.fcf < 0)

    # Rule of 40 (growth% + FCF-margin%): a durable-growth quality check.
    if g is not None and fcf_m is not None:
        c.rule_of_40 = (g + fcf_m) * 100.0

    sector = (cd.sector or "")
    industry = (cd.industry or "").lower()

    # --- THE SECTOR IS UNKNOWN: refuse a regime rather than infer one ------------------------
    #
    # An empty sector used to match neither `FINANCIAL_SECTORS` nor any industry hint, so the
    # name fell through to the growth branch below and got a model chosen by its revenue growth
    # alone. Measured on valquo.co 2026-09-30 ~13:45 ET, four of four financials: KNSL ->
    # hypergrowth at ~$625, TRV -> mature at ~$702, PGR and JPM -> growth. The same service had
    # read KNSL as `financial` ten hours earlier, so the fault is intermittent and a single run
    # cannot see it.
    #
    # THE TEST IS THE SOURCE, NOT THE EMPTINESS. `sector_source == "unresolved"` means the
    # fallback chain ran and every rung failed. A blank `sector_source` means nobody asked --
    # the offline and batch paths that build a `CompanyData` by hand -- and those keep the old
    # behaviour exactly, so this cannot change a single existing test's answer by accident.
    if getattr(cd, "sector_source", "") == "unresolved" and not sector and not industry:
        c.regime = UNKNOWN
        c.dcf_reliability = "low"
        c.reasons.append(
            "Industry could not be determined from any source (the market-data profile, the "
            "latest scan, the SEC's filed SIC code, or the profile API). No valuation model is "
            "published, because choosing one requires knowing what kind of business this is.")
        return c

    # --- REITs: FCFF is near zero BY CONSTRUCTION, because capex is the business -----------
    #
    # BEFORE the growth branches, deliberately. A REIT with 11% revenue growth is still a REIT,
    # and ordering the test after the growth check is exactly how O got `regime: growth` while
    # PLD at 8.8% got `mature` -- one cause, two wrong answers, decided by which side of an
    # unrelated threshold the name happened to fall.
    if sector in REIT_SECTORS or any(h in industry for h in REIT_INDUSTRY_HINTS):
        c.regime = "reit"
        c.dcf_reliability = "low"
        c.reasons.append(
            "REIT: a property trust's capex IS its business, so unlevered free cash flow after "
            "capex is near zero or negative for a healthy company every year. An FCFF DCF "
            "therefore answers a question this business does not pose, and is not used. Valued "
            "on multiples instead; FFO/AFFO and P/NAV are the right lenses and are not built "
            "here, so the valuation is published only where multiples can carry it.")
        _note_sector_source(c, cd)
        return c

    # --- Regulated utilities: negative FCF is the rate base, not a burn --------------------
    if sector in REGULATED_SECTORS or any(h in industry for h in REGULATED_INDUSTRY_HINTS):
        c.regime = "regulated"
        c.dcf_reliability = "low"
        c.reasons.append(
            "Regulated utility: capex is rate-base investment the regulator allows a return "
            "on, so persistent negative free cash flow is the business model rather than a "
            "cash burn. An unlevered FCFF DCF reads that investment as value destruction and "
            "is not used; the cash-runway warning does not apply either, because the spending "
            "it reads as a burn is the asset. Valued on multiples and dividend/earnings power.")
        _note_sector_source(c, cd)
        return c

    # --- Financials: FCFF/DCF is not appropriate (debt is raw material) ---
    if sector in FINANCIAL_SECTORS or any(h in industry for h in FINANCIAL_INDUSTRY_HINTS):
        c.regime = "financial"
        c.dcf_reliability = "low"
        c.reasons.append("Bank/insurer/financial: unlevered FCF DCF is unreliable; "
                         "lean on multiples and dividend/earnings power instead.")
        _note_sector_source(c, cd)
        return c

    gg = g if g is not None else 0.05

    # --- Hypergrowth / cash-burning growth ---
    if gg >= 0.25 or (gg >= 0.15 and c.is_cash_burning):
        c.regime = "hypergrowth"
        c.dcf_reliability = "low" if c.is_cash_burning else "medium"
        c.reasons.append(f"High revenue growth (~{gg:.0%})"
                         + (" with negative FCF (cash-burning)" if c.is_cash_burning else "")
                         + ": modeled with a long runway and margin convergence to maturity.")
        return c

    # --- Growth ---
    if gg >= 0.10:
        c.regime = "growth"
        c.dcf_reliability = "medium" if c.is_cash_burning else "high"
        c.reasons.append(f"Solid growth (~{gg:.0%}): extended forecast with a fading growth path.")
        return c

    # --- Cyclical (only if not already growthy) ---
    if sector in CYCLICAL_SECTORS:
        c.regime = "cyclical"
        c.dcf_reliability = "medium"
        c.reasons.append("Cyclical sector: margins normalized toward the mid-cycle average "
                         "rather than the latest (possibly peak/trough) year.")
        return c

    # --- Declining: a shrinking business is not a stable one -------------------------------
    #
    # ITEM 25 asked me to check the regime classifier's INPUTS for TSLA and MRNA. **The inputs
    # are right and the DEFAULT BRANCH is what is wrong**, and the two names come apart:
    #
    #   TSLA  blended growth +0.0784, FCF-positive  -> `mature`, and that is DEFENSIBLE.
    #   MRNA  blended growth -0.1605, cash-burning  -> `mature`, "stable profile", which is not.
    #
    # **`mature` IS THE FALL-THROUGH, SO IT MAKES A POSITIVE CLAIM ABOUT EVERY COMPANY THE
    # OTHER BRANCHES DECLINED TO CLAIM.** "Mature, stable profile" is an assertion; being
    # un-matched by four tests is not evidence for it. That is exactly why `UNKNOWN` exists one
    # layer up -- its own comment records that letting an unresolved sector fall through to the
    # growth branch valued four of four financials with the unlevered model -- and this is the
    # same defect in the regime layer rather than the sector layer.
    #
    # **IT CHANGES NO MODEL, DELIBERATELY.** A 5-year FCFF DCF on a shrinking profitable
    # business is structurally coherent in a way it is not for a REIT, so the lens is kept and
    # only the LABEL and the RELIABILITY move. Inventing a decline model here would be a
    # construction change smuggled in behind a labelling fix.
    #
    # **AND TSLA IS DELIBERATELY NOT RE-ROUTED.** Its $23.42 against a $370.59 price comes from
    # ROIC 5% against a **WACC of 14%** -- a high beta discounted at a 5.28% risk-free rate,
    # which item 25 states plainly is the real 10-year yield and the model working as written.
    # Routing a profitable, FCF-positive, single-digit-growth manufacturer out of `mature` to
    # make its number look better would be choosing the regime on the output.
    if g is not None and g <= DECLINING_GROWTH:
        c.regime = "declining"
        c.dcf_reliability = "low" if c.is_cash_burning else "medium"
        c.reasons.append(
            "Revenue is SHRINKING (~%.0f%%)%s: this is not a mature, stable profile and is not "
            "modelled as one. The cash-flow model still applies structurally, but a forecast "
            "built on a declining base is the least reliable thing this engine produces -- the "
            "question is where the decline stops, and nothing here estimates that."
            % (g * 100.0,
               " while burning cash" if c.is_cash_burning else ""))
        return c

    # --- Mature / stable (default) ---
    c.regime = "mature"
    c.dcf_reliability = "high"
    c.reasons.append("Mature, stable profile: standard 5-year FCFF DCF.")
    if c.is_cash_burning:
        c.dcf_reliability = "medium"
        c.reasons.append("Note: currently FCF-negative despite low growth — watch cash runway.")
    return c
