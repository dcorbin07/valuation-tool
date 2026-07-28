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
  * established/profit -> DCF-weighted, with multiples as the cross-check
  * growth / pre-profit-> multiples-weighted, with the DCF down-weighted or dropped
  * nothing applicable -> NO fair value, and we say so

The established<->speculative position is continuous, not a switch: `p_established`
is a sigmoid on operating margin (0% -> 0.50, +5% -> 0.73, -5% -> 0.27), mirroring the
screener's soft bucketing so the two halves of the app agree about what a company is.
The DCF's share of the blend is then

    w_dcf = dcf_quality[reliability] * p_established        (renormalized over live lenses)

which lands ~0.75 on a mature profitable name, ~0.44 on a profitable grower, and ~0.05
on a loss-making hypergrowth name — a gradient rather than a cliff.

A lens only participates if it produced a POSITIVE, usable number. That is what stops a
negative DCF from dragging the blend down: it is dropped, not averaged in. If no lens
survives, `valuable` is False and the caller must show "not DCF-valuable" rather than
invent a figure.

On the reverse DCF: it does not produce an independent fair value — solving for the
growth implied by today's price and then valuing the company at our own growth just
returns the DCF, so blending it in would be double-counting. Its honest role here is a
plausibility check: when the market is already pricing growth far above our base case,
we attach a note and mark confidence down, because that is exactly when a growth name's
DCF is least trustworthy.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

# How much of the blend the DCF may claim, before the p_established taper.
DCF_QUALITY = {"high": 0.75, "medium": 0.55, "low": 0.25}

# The market-implied growth has to clear BOTH of these before we flag it as demanding.
IMPLIED_GROWTH_ABS = 0.25          # >25%/yr priced in
IMPLIED_GROWTH_REL = 1.5           # and >1.5x our own base case


@dataclass
class FairValueBlend:
    value: Optional[float] = None          # blended per-share fair value (None if not valuable)
    valuable: bool = False                 # False -> UI must show "not DCF-valuable"
    reason: str = ""                       # why there's no value (when valuable is False)
    method: str = ""                       # human-readable mix, e.g. "62% multiples · 38% DCF"
    p_established: Optional[float] = None
    dcf_meaningful: bool = True            # False when the DCF itself was unusable/dropped
    lenses: dict = field(default_factory=dict)   # name -> {"value":…, "weight":…}
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"value": self.value, "valuable": self.valuable, "reason": self.reason,
                "method": self.method, "p_established": self.p_established,
                "dcf_meaningful": self.dcf_meaningful, "lenses": self.lenses,
                "notes": self.notes}


def p_established(cd) -> float:
    """Continuous 0..1 'how established is this company', from operating margin.

    Same sigmoid the screener uses for soft bucketing, so a name is treated
    consistently whether it's being ranked or valued. Falls back to 0.5 (genuinely
    undecided) when there's no margin to read.
    """
    # CompanyData exposes this as `ebit_margin`; the screener's metrics dicts call the
    # same quantity `op_margin`. Accept either so both callers get identical bucketing.
    om = getattr(cd, "ebit_margin", None)
    if om is None:
        om = getattr(cd, "op_margin", None)
    try:
        om = float(om)
    except (TypeError, ValueError):
        return 0.5
    if om != om:
        return 0.5
    return 1.0 / (1.0 + math.exp(-(om / 0.05)))


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
                       reverse=None) -> FairValueBlend:
    """Blend the applicable valuation lenses for this company's archetype."""
    p = p_established(cd)
    out = FairValueBlend(p_established=round(p, 3))

    dcf = _usable(dcf_per_share)
    mult = _usable(comps_fair_value)
    out.dcf_meaningful = dcf is not None

    # --- Financials: the P/B-ROE model already replaced the DCF upstream, so the
    # "dcf" figure handed to us IS that model. Use it alone; FCFF never applies here.
    if getattr(cls, "regime", "") == "financial":
        if dcf is not None:
            out.value, out.valuable = dcf, True
            out.method = "justified P/B from ROE"
            out.lenses = {"pb_roe": {"value": dcf, "weight": 1.0}}
            out.notes.append("Valued as a financial: book value x justified P/B from ROE, "
                             "not an unlevered cash-flow DCF.")
        else:
            out.reason = ("Not valuable from the available data — a bank/insurer needs book "
                          "value and ROE, and at least one is missing.")
        return out

    # --- Everything else: DCF and multiples, weighted by archetype.
    quality = DCF_QUALITY.get(getattr(cls, "dcf_reliability", "medium"), 0.55)
    w_dcf = quality * p
    w_mult = 1.0 - w_dcf

    live = {}
    if dcf is not None:
        live["dcf"] = (dcf, w_dcf)
    if mult is not None:
        live["multiples"] = (mult, w_mult)

    if not live:
        out.reason = _no_value_reason(cd, dcf_per_share, comps_fair_value)
        return out

    total = sum(w for _, w in live.values()) or 1.0
    out.value = sum(v * w for v, w in live.values()) / total
    out.valuable = True
    out.lenses = {k: {"value": round(v, 4), "weight": round(w / total, 3)}
                  for k, (v, w) in live.items()}
    out.method = " · ".join(
        f"{round(w / total * 100):.0f}% {'DCF' if k == 'dcf' else 'multiples'}"
        for k, (v, w) in sorted(live.items(), key=lambda kv: -kv[1][1]))

    if dcf is None:
        out.notes.append(
            "The discounted-cash-flow model doesn't apply to this company — it isn't "
            "generating the positive free cash flow a DCF needs — so this is a "
            "multiples-based estimate from what comparable companies trade at.")
    elif w_dcf / total < 0.4:
        out.notes.append(
            "Growth/early-stage profile: the DCF is down-weighted here because its "
            "margin and terminal-value assumptions carry most of the answer.")

    # Reverse-DCF plausibility (a check, not a lens — see the module docstring).
    note = _implied_growth_note(reverse)
    if note:
        out.notes.append(note)
    return out


def _no_value_reason(cd, dcf_per_share, comps_fair_value) -> str:
    """Say specifically WHY there's no fair value — a generic 'n/a' teaches nothing."""
    neg_dcf = dcf_per_share is not None and float(dcf_per_share) <= 0
    has_rev = _usable(getattr(cd, "revenue", None)) is not None
    if neg_dcf and not has_rev:
        return ("Not DCF-valuable: the company doesn't generate positive free cash flow, and "
                "there's no revenue to value it on a sales multiple either.")
    if neg_dcf:
        return ("Not DCF-valuable: projected free cash flow is negative, so a DCF returns a "
                "meaningless (negative) figure. No usable comparable multiple either — "
                "judge this one on growth, cash runway and dilution instead.")
    return ("Not valuable from the available data — the inputs a DCF or a multiple would "
            "need (cash flow, earnings or revenue) are missing.")


def _implied_growth_note(reverse) -> Optional[str]:
    """Flag when today's price already demands growth well above our base case."""
    if reverse is None:
        return None
    imp = getattr(reverse, "implied_avg_growth", None)
    base = getattr(reverse, "base_avg_growth", None)
    try:
        imp, base = float(imp), float(base)
    except (TypeError, ValueError):
        return None
    if imp != imp or base != base or base <= 0:
        return None
    if imp >= IMPLIED_GROWTH_ABS and imp >= IMPLIED_GROWTH_REL * base:
        return (f"Today's price already implies ~{imp:.0%}/yr revenue growth versus our "
                f"~{base:.0%} base case — the market is pricing in a lot, so treat any "
                f"upside here with extra caution.")
    return None
