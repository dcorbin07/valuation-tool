# -*- coding: utf-8 -*-
"""HOW MUCH THIS VALUE DEPENDS ON ONE INPUT — the fair value re-solved at beta ±0.3.

**WHAT THE REVIEW FOUND (2026-10-21).** KO reads about $58.50 at its vendor beta of 0.32 and
about $35.11 at beta 1.0. Nothing beside the headline said so. A DCF's discount rate runs
straight off beta through CAPM, so on a low-beta name the figure is as much a statement about
one vendor field as about the company — and the page presented it as a single number.

**IT DELEGATES TO `engine/average_risk.average_risk_read`, WHICH ALREADY DOES THIS AT BETA 1.0.**
That is the whole design, and the alternative was the mistake. Item 53 part 3 built exactly this
machinery — re-run the real `value_from_company` with `beta` overridden and nothing else touched
— and its function already takes a `beta` parameter. A first draft of this module called the
pipeline itself, and would have reintroduced two defects that one solves and documents:

  * **`value_from_company` APPENDS TO `cd.quality_notes`**, and that list becomes the result's
    `warnings`. A second pass over the same `CompanyData` duplicates every note on the FIRST
    result — a number already shown to the reader changing because a sensitivity strip was
    drawn. `average_risk_read` snapshots and restores the notes in a `finally`.
  * **THE MONTE CARLO IS THE SLOW PART.** Re-solving at full trial count twice per page view
    pays for a distribution this strip never reads. `average_risk_read` passes
    `REVALUE_TRIALS`.

So this module contributes the ±0.3 points, the clamp, and the shape — and no valuation
arithmetic of any kind. `B7`: one definition of the second pass.

**BOUNDED BY THE ENGINE'S OWN BETA LIMITS, IMPORTED.** `wacc.BETA_HIGH_CAP` is the top of the
band the ladder accepts at all, and a beta must be strictly positive or CAPM is meaningless. The
±0.3 points are clamped into `(0, BETA_HIGH_CAP]` rather than run at a beta the engine would
refuse, and when a clamp bites the strip reports the beta it actually used. Never retyped here.

**THE POINT VALUE DOES NOT CHANGE.** §3's own words. The anchor's value is READ from the
valuation the page already has, so the strip's middle point cannot disagree with the headline
above it, and no score, verdict, blend or recorded figure reads anything here.

**EVERY FIGURE DEGRADES TO `None`.** A page that cannot re-solve shows no strip rather than a
plausible one — `live_facts`'s rule, for the same reason.
"""
from __future__ import annotations

from typing import Optional

#: How far either side of the anchor beta to re-solve. §3 fixes this at 0.3. A DISPLAY span:
#: nothing gates on it, so it is not a calibrated threshold and is not treated as one.
BETA_DELTA = 0.3

#: The label §3 asks for, verbatim. Here rather than in a renderer for this project's standing
#: reason about calibrated copy — prose in a template is a second claim about a measurement.
LABEL = "how much this value depends on one input"

CAVEAT = (
    "Beta sets the discount rate through CAPM, so it moves the fair value directly. These are "
    "the same model re-solved at a different beta — nothing else is changed. A wide spread does "
    "not mean the value is wrong; it means one vendor field is carrying a lot of it."
)


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and v not in (float("inf"), float("-inf")) else None


def beta_bounds() -> tuple:
    """`(low, high)` — the band the shipped ladder accepts, IMPORTED from `wacc`."""
    from ..engine.wacc import BETA_HIGH_CAP
    # Strictly positive: `_resolve_beta`'s own in-range test is `0 < vendor <= BETA_HIGH_CAP`.
    # 0.01 is the smallest step this surface will show rather than a threshold — a beta of
    # exactly zero makes the cost of equity the risk-free rate, which is not a company.
    return (0.01, float(BETA_HIGH_CAP))


def strip(result, cd=None, cfg=None, *, delta: float = BETA_DELTA, read_fn=None) -> dict:
    """`{available, label, caveat, anchor, points, delta, bounds, clamped, reason}`.

    `points` is a list of `{beta, value, wacc, delta_vs_anchor, pct_vs_anchor, is_anchor,
    clamped}`, low beta first.

    `read_fn` defaults to `engine.average_risk.average_risk_read`; a test may inject a counter
    to prove this module calls the shipped second pass and derives nothing itself.
    """
    out = {"available": False, "label": LABEL, "caveat": CAVEAT, "anchor": None,
           "points": [], "delta": float(delta), "bounds": None, "clamped": False,
           "reason": ""}

    if cd is None:
        cd = getattr(result, "company", None)
    if cd is None:
        out["reason"] = "no company data, so the fair value cannot be re-solved"
        return out
    if cfg is None:
        from ..config import CONFIG as cfg                                # noqa: N806
    if read_fn is None:
        from ..engine.average_risk import average_risk_read as read_fn    # noqa: N806

    lo_b, hi_b = beta_bounds()
    out["bounds"] = {"low": lo_b, "high": hi_b}

    w = getattr(result, "wacc", None)
    # THE ANCHOR IS THE BETA THE LADDER ACTUALLY CHOSE, not `cd.beta`. They differ whenever the
    # ladder corroborated or fell back — which is what the ladder is for — and a strip centred
    # on the vendor field would be centred on a beta the valuation did not use.
    anchor_beta = _f(getattr(w, "beta", None)) or _f(getattr(cd, "beta", None))
    anchor_wacc = _f(getattr(w, "wacc", None))
    anchor_value = _f(getattr(result, "base_fair_value", None))

    if anchor_beta is None or anchor_beta <= 0:
        out["reason"] = "this name has no usable beta, so there is nothing to vary"
        return out
    if anchor_value is None:
        # The same refusal `average_risk_read` makes, for the same reason: "the value would be
        # $X at a different beta", beside a headline the model DECLINED to publish, hands the
        # reader the number the refusal withheld.
        out["reason"] = "the model published no base value for this company"
        return out

    # The pipeline hands `average_risk_read` its own `value_from_company` as `revalue`. This
    # surface has only the finished result, so it supplies the same callable the same way —
    # imported here rather than at module scope so importing this module costs nothing.
    from ..engine.pipeline import value_from_company as _vfc

    def _revalue(_cd, _cfg, overrides, mc_trials):
        return _vfc(_cd, _cfg, overrides=overrides, mc_trials=mc_trials)

    seen, pts = set(), []
    for i, b in enumerate((anchor_beta - delta, anchor_beta, anchor_beta + delta)):
        bb = min(max(b, lo_b), hi_b)
        was_clamped = abs(bb - b) > 1e-12
        if was_clamped:
            out["clamped"] = True
        is_anchor = (i == 1)
        # DEDUPLICATED ON THE BETA ACTUALLY USED. A clamp can collapse two points onto one beta
        # (a name at 2.9 against a 3.0 cap), and printing "3.00 and 3.00" as two sensitivities
        # would be a strip claiming to vary something it did not.
        key = round(bb, 6)
        if key in seen and not is_anchor:
            continue
        seen.add(key)

        if is_anchor:
            pts.append({"beta": bb, "requested_beta": b, "value": anchor_value,
                        "wacc": anchor_wacc, "is_anchor": True, "clamped": was_clamped,
                        "delta_vs_anchor": 0.0, "pct_vs_anchor": 0.0, "reason": ""})
            continue

        r = read_fn(cd, cfg, deployed_wacc=anchor_wacc, deployed_beta=anchor_beta,
                    deployed_value=anchor_value, revalue=_revalue, beta=bb)
        v = _f((r or {}).get("value"))
        pts.append({
            "beta": bb, "requested_beta": b, "value": v,
            "wacc": _f((r or {}).get("wacc")),
            "is_anchor": False, "clamped": was_clamped,
            "delta_vs_anchor": (v - anchor_value) if v is not None else None,
            "pct_vs_anchor": ((v / anchor_value) - 1.0)
                             if (v is not None and anchor_value) else None,
            # CARRIED, NOT SWALLOWED. "The model values this name at its own beta and refuses
            # at another" is a fact about the model's own stability, and `average_risk_read`
            # already words it.
            "reason": (r or {}).get("reason") or "",
        })

    out["anchor"] = {"beta": anchor_beta, "value": anchor_value, "wacc": anchor_wacc}
    out["points"] = pts
    # NON-VACUITY, ENFORCED RATHER THAN HOPED FOR: "this value depends on one input" is not
    # demonstrated by one value, so at least one point BESIDE the anchor must have re-solved.
    if sum(1 for p in pts if p["value"] is not None and not p["is_anchor"]) < 1:
        out["reason"] = ("the valuation could not be re-solved at a different beta, so no "
                         "sensitivity is shown")
        return out
    out["available"] = True
    return out
