"""
Archetype-adaptive blended fair value.

One model does not fit every company. An unlevered FCFF DCF is the right lens for a
mature, profitable, cash-generative business; it is close to meaningless for a
pre-profit growth name (garbage-in on margins and terminal value) and structurally
wrong for a bank (debt is raw material, not financing). Forcing every ticker through
the DCF is how you end up publishing a *negative* fair value for an unprofitable
company — a number that looks precise and is simply not information.

So we compute each lens that is genuinely applicable and blend them by archetype:

  * financial          -> justified P/B from ROE  (see financials.py; used alone)
  * established/profit -> DCF-weighted, with mature multiples as the cross-check
  * growth / pre-profit-> REVENUE-multiple-weighted (growth.py), DCF down-weighted
  * nothing applicable -> NO fair value, and we say so

The position on that spectrum is continuous, not a switch. `maturity` (growth.py)
is a weighted sigmoid blend of operating margin, cash generation, revenue growth
and size — 1.0 = large, profitable, slow; 0.0 = small, loss-making, fast. The
weights are then

    w_dcf    = dcf_quality[reliability] * maturity
    w_mult   = (1 - dcf_quality[reliability]) * maturity
    w_growth = 1 - maturity                       (all renormalized over live lenses)

so the two "value it on today's profit" lenses split the mature half between them
and the revenue lens takes the rest. A mature profitable name lands ~0.65 DCF; a
loss-making hypergrowth name lands ~0.85 growth-lens; nothing jumps at a threshold.

A lens only participates if it produced a POSITIVE, usable number. That is what stops a
negative DCF from dragging the blend down: it is dropped, not averaged in. If no lens
survives, `valuable` is False and the caller must show "not DCF-valuable" rather than
invent a figure.

On the reverse DCF: it does not produce an independent fair value — solving for the
growth implied by today's price and then valuing the company at our own growth just
returns the DCF, so blending it in would be double-counting. Its honest role is as
the HEADLINE for a growth name: when the revenue lens is carrying the valuation, the
useful statement is "the price already implies ~94%/yr growth against our ~34% base",
not a two-decimal fair value. `headline_mode` says which of the two the UI should lead
with, and `confidence` marks growth-led valuations down where they belong.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .growth import maturity_from_company

# How much of the mature half of the blend the DCF may claim; the rest goes to
# the mature-multiples lens.
DCF_QUALITY = {"high": 0.75, "medium": 0.55, "low": 0.25}

# The market-implied growth has to clear BOTH of these before we flag it as demanding.
IMPLIED_GROWTH_ABS = 0.25          # >25%/yr priced in
IMPLIED_GROWTH_REL = 1.5           # and >1.5x our own base case

# Above this share of the blend, the revenue lens is effectively the valuation —
# lead with the implied-growth read and mark confidence down.
GROWTH_LED = 0.50

# --- Terminal-share bands (HANDOFF_live_data_bugs.md Part 9) --------------------------------
# The confidence label used to describe where the DATA came from and which lens carried the
# blend, and never what the number was MADE OF. A DCF that is 93% terminal value is a claim
# about year 11-to-infinity wearing a ten-year model's clothes.
#
# A HIGH TERMINAL SHARE IS NORMAL — do not read these as defect thresholds. Measured across the
# 201 DCF-participating names of the 241-name universe, the MEDIAN is 77.7% and p90 is 87.4%;
# a 70% bar would flag three names in four and carry no information.
#
#   0.90  — just past p90, and where the histogram collapses (69 names in 80-90%, 9 in 90-100%).
#           Under a tenth of the value then comes from the decade we actually model.
#   1.00  — NOT a calibrated number: a sign change. TV > EV means PV(explicit forecast) < 0, so
#           the modelled decade destroys value and the terminal pays for all of it plus the
#           shortfall. That is a different object, not a fragile version of the same one.
TV_SHARE_MEDIUM = 0.90
TV_SHARE_LOW = 1.00

_CONF_RANK = {"low": 0, "medium": 1, "high": 2}

_LENS_LABEL = {"dcf": "DCF", "multiples": "multiples", "growth": "growth (revenue multiple)",
               "pb_roe": "P/B–ROE"}


@dataclass
class FairValueBlend:
    value: Optional[float] = None          # blended per-share fair value (None if not valuable)
    valuable: bool = False                 # False -> UI must show "not DCF-valuable"
    reason: str = ""                       # why there's no value (when valuable is False)
    method: str = ""                       # human-readable mix, e.g. "62% multiples · 38% DCF"
    maturity: Optional[float] = None       # 0..1, see growth.maturity_score
    maturity_parts: dict = field(default_factory=dict)
    p_established: Optional[float] = None  # legacy alias for `maturity`
    dcf_meaningful: bool = True            # False when the DCF itself was unusable/dropped
    growth_led: bool = False               # True -> the revenue lens carries the valuation
    headline_mode: str = "point"           # "point" | "implied_growth"
    headline: str = ""                     # the sentence the UI should lead with
    confidence: str = "medium"             # high | medium | low
    tv_share: Optional[float] = None       # DCF terminal value as a share of enterprise value
    value_low: Optional[float] = None      # bear end of the same-method range
    value_high: Optional[float] = None     # bull end
    lenses: dict = field(default_factory=dict)   # name -> {"value":…, "weight":…}
    notes: list = field(default_factory=list)
    # The value the publication guard SUPPRESSED, kept so downstream sanity checks can
    # still evaluate it. Without this, scoring.py's ">5x fair value is a data problem"
    # cap silently stopped firing the moment the guard did its job — a check that only
    # works when the unsafe thing is present. Never publish this; it is for guards only.
    withheld_value: Optional[float] = None

    def to_dict(self) -> dict:
        return {"value": self.value, "valuable": self.valuable, "reason": self.reason,
                "method": self.method, "maturity": self.maturity,
                "maturity_parts": self.maturity_parts, "p_established": self.p_established,
                "dcf_meaningful": self.dcf_meaningful, "growth_led": self.growth_led,
                "headline_mode": self.headline_mode, "headline": self.headline,
                "confidence": self.confidence, "tv_share": self.tv_share,
                "value_low": self.value_low,
                "value_high": self.value_high, "lenses": self.lenses, "notes": self.notes,
                "withheld_value": self.withheld_value}


def _usable(x) -> Optional[float]:
    """A positive, finite number, else None. A non-positive fair value is not a
    cheap stock — it means the lens doesn't apply to this company."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if v != v or v in (float("inf"), float("-inf")) or v <= 0:
        return None
    return v


def blended_fair_value(cd, cls, dcf_per_share, comps_fair_value,
                       reverse=None, growth_value=None, maturity=None,
                       maturity_parts=None, quiet=False) -> FairValueBlend:
    """Blend the applicable valuation lenses for this company's archetype.

    `growth_value` is the per-share number from growth.growth_fair_value (None if
    that lens didn't apply). `maturity` may be passed in so every scenario in a
    run shares one maturity score; it's computed here when omitted. `quiet`
    suppresses the prose notes — used when blending the bear/bull scenarios,
    which only need the number.
    """
    if maturity is None:
        maturity, maturity_parts = maturity_from_company(cd)
    m = max(0.0, min(1.0, float(maturity)))
    out = FairValueBlend(maturity=round(m, 3), p_established=round(m, 3),
                         maturity_parts={k: round(v, 3) for k, v in (maturity_parts or {}).items()})

    dcf = _usable(dcf_per_share)
    mult = _usable(comps_fair_value)
    grow = _usable(growth_value)
    out.dcf_meaningful = dcf is not None

    # --- Financials: the P/B-ROE model already replaced the DCF upstream, so the
    # "dcf" figure handed to us IS that model. Use it alone; FCFF never applies here.
    if getattr(cls, "regime", "") == "financial":
        if dcf is not None:
            out.value, out.valuable = dcf, True
            out.method = "justified P/B from ROE"
            out.lenses = {"pb_roe": {"value": dcf, "weight": 1.0}}
            out.confidence = "medium"
            if not quiet:
                out.notes.append("Valued as a financial: book value x justified P/B from ROE, "
                                 "not an unlevered cash-flow DCF.")
        else:
            out.reason = ("Not valuable from the available data — a bank/insurer needs book "
                          "value and ROE, and at least one is missing.")
        return out

    # --- Everything else: DCF, mature multiples and the revenue lens, by maturity.
    quality = DCF_QUALITY.get(getattr(cls, "dcf_reliability", "medium"), 0.55)
    live = {}
    if dcf is not None:
        live["dcf"] = (dcf, quality * m)
    if mult is not None:
        live["multiples"] = (mult, (1.0 - quality) * m)
    if grow is not None:
        live["growth"] = (grow, 1.0 - m)

    live = {k: v for k, v in live.items() if v[1] > 1e-9}
    if not live:
        out.reason = _no_value_reason(cd, dcf_per_share, comps_fair_value, growth_value)
        return out

    total = sum(w for _, w in live.values())
    out.value = sum(v * w for v, w in live.values()) / total
    out.valuable = True
    out.lenses = {k: {"value": round(v, 4), "weight": round(w / total, 3)}
                  for k, (v, w) in live.items()}
    out.method = " · ".join(
        f"{round(w / total * 100):.0f}% {_LENS_LABEL.get(k, k)}"
        for k, (v, w) in sorted(live.items(), key=lambda kv: -kv[1][1]))

    w_growth = live.get("growth", (0.0, 0.0))[1] / total
    out.growth_led = w_growth >= GROWTH_LED
    out.confidence = ("low" if (out.growth_led or dcf is None)
                      else ("medium" if w_growth > 0.2 or quality < 0.75 else "high"))

    # Reverse-DCF plausibility. For a growth-led name this IS the headline: a
    # point value on a pre-profit company is false precision, but "the price
    # already demands X% growth against our Y%" is a decision-grade statement.
    imp, base_g = _implied_vs_base(reverse)
    if out.growth_led and imp is not None:
        # "at least" when the solver hit its bound — the price demands more growth than
        # the model can even express, and saying "~94%" would understate that.
        floor = "at least " if getattr(reverse, "implied_growth_bounded", "") == "above" else ""
        out.headline_mode = "implied_growth"
        out.headline = (f"Today's price implies {floor}~{imp:.0%}/yr revenue growth; our base case is "
                        f"~{base_g:.0%}. Judge this one on whether that gap is achievable — "
                        f"the fair-value range below is indicative, not a point estimate.")
    elif out.growth_led:
        out.headline_mode = "implied_growth"
        out.headline = ("A pre-profit growth name: the value depends almost entirely on revenue "
                        "years out, so treat the range below as indicative, not a point estimate.")

    if quiet:
        return out

    if dcf is None:
        out.notes.append(
            "The discounted-cash-flow model doesn't apply to this company — it isn't "
            "generating the positive free cash flow a DCF needs — so this is valued on "
            "revenue and on what comparable companies trade at.")
    elif live["dcf"][1] / total < 0.4:
        out.notes.append(
            "Growth/early-stage profile: the DCF is down-weighted here because its "
            "margin and terminal-value assumptions carry most of the answer.")
    if out.growth_led:
        out.notes.append(
            "Growth valuations are inherently wide. This one assumes the capital funding "
            "that growth is raised without heavy dilution, and that the business exits at a "
            "mature multiple — either assumption moving materially moves the value.")
    note = _implied_growth_note(imp, base_g)
    if note and out.headline_mode != "implied_growth":
        out.notes.append(note)
    return out


def terminal_share_cap(confidence: str, tv_share) -> tuple:
    """Cap a confidence label by the DCF's terminal share. Returns (label, note or None).

    PURE, and deliberately so: it takes a label and a number and returns a label. It cannot see
    a fair value, a score or a company, which is what makes "labels only, zero value changes" a
    structural property of the change rather than something the sweep merely failed to catch.

    MONOTONE DOWNWARD — `min` over the rank, never `max`. The cap can only ever mark a
    valuation down, so it can never rescue one, and a name already "low" is left alone.

    Callers apply it only when the DCF lens is actually in the blend; terminal share says
    nothing about a name valued on P/B-ROE or on a revenue multiple.
    """
    try:
        share = float(tv_share)
    except (TypeError, ValueError):
        return confidence, None
    if share != share or share in (float("inf"), float("-inf")):
        return confidence, None

    if share >= TV_SHARE_LOW:
        ceiling, note = "low", (
            f"{share:.0%} of this DCF's enterprise value is terminal value — more than the whole "
            f"company, which means the ten years we actually model are worth less than nothing on "
            f"these assumptions and the perpetuity is carrying all of it. Confidence is marked "
            f"down: this is a bet on the terminal assumption, not on the forecast.")
    elif share >= TV_SHARE_MEDIUM:
        ceiling, note = "medium", (
            f"{share:.0%} of this DCF's value sits in the terminal value, so only {1 - share:.0%} "
            f"comes from the decade we forecast with this company's own numbers. That is high even "
            f"for a DCF, where a high terminal share is normal — the typical name here is ~78%. "
            f"Confidence is marked down accordingly.")
    else:
        return confidence, None

    # The note tracks the FACT, not the label delta: a name already marked "low" for another
    # reason still deserves to have this one stated, or the reader learns nothing from the
    # cases where two weaknesses coincide.
    rank = min(_CONF_RANK.get(confidence, 1), _CONF_RANK[ceiling])
    capped = next(k for k, v in _CONF_RANK.items() if v == rank)
    return capped, note


def _no_value_reason(cd, dcf_per_share, comps_fair_value, growth_value=None) -> str:
    """Say specifically WHY there's no fair value — a generic 'n/a' teaches nothing."""
    neg_dcf = dcf_per_share is not None and float(dcf_per_share) <= 0
    has_rev = _usable(getattr(cd, "revenue", None)) is not None
    if neg_dcf and not has_rev:
        return ("Not DCF-valuable: the company doesn't generate positive free cash flow, and "
                "there's no revenue to value it on a sales multiple either.")
    if neg_dcf:
        return ("Not DCF-valuable: projected free cash flow is negative, so a DCF returns a "
                "meaningless (negative) figure. No usable revenue or comparable multiple "
                "either — judge this one on growth, cash runway and dilution instead.")
    return ("Not valuable from the available data — the inputs a DCF or a multiple would "
            "need (cash flow, earnings or revenue) are missing.")


def _implied_vs_base(reverse):
    """(implied avg growth, base avg growth) from a ReverseDCFResult, or (None, None)."""
    if reverse is None:
        return None, None
    imp = getattr(reverse, "implied_avg_growth", None)
    base = getattr(reverse, "base_avg_growth", None)
    try:
        imp, base = float(imp), float(base)
    except (TypeError, ValueError):
        return None, None
    if imp != imp or base != base:
        return None, None
    return imp, base


def _implied_growth_note(imp, base) -> Optional[str]:
    """Flag when today's price already demands growth well above our base case."""
    if imp is None or base is None or base <= 0:
        return None
    if imp >= IMPLIED_GROWTH_ABS and imp >= IMPLIED_GROWTH_REL * base:
        return (f"Today's price already implies ~{imp:.0%}/yr revenue growth versus our "
                f"~{base:.0%} base case — the market is pricing in a lot, so treat any "
                f"upside here with extra caution.")
    return None
