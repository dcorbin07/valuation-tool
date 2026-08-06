"""
When the model refuses to value a name, the whole payload must refuse.

THE BUG THIS EXISTS FOR (2026-08-05). `publication_guard` (engine/pipeline.py:50) marks a
blend not-valuable and blanks `blend.value`, so the headline correctly read

    Fair value: "Not DCF-valuable"   Upside: n/a
    "Cannot value this name: the model's $1,289.68 is 14.0x the $92.19 price ..."

and then, three inches below on the same page, FAIR VALUE & SCENARIOS printed

    BEAR $620.31 (+573%)  BASE $1,289.68 (+1299%)  BULL $2,888.33 (+3033%)

— the withheld number itself, twice as large, in green. Every other card downstream of the
DCF did the same thing: the Monte Carlo card published a $2,335 median and "100% of trials
value it above today's price", the sensitivity grid published a 5x5 table of per-share values
up to $8,632, the comps card published a $326 implied value against a $92 price, and the
reverse-DCF card concluded "expectations look cheap". The suppression was defeated by its
own page seven times over.

THE RULE. A refusal is a refusal. When the guard fires, nothing that depends on the
per-share valuation is published — not a smaller version of it, not a distribution around
it, not a grid of it, not a percentage derived from it. This module strips those figures
from the API payload BEFORE it reaches the browser, so the numbers are not merely un-drawn:
they are not in the response, not in `view-source:`, not in the network tab. The renderer
(static/app.js) refuses in parallel, but the wire is the authority.

WHAT SURVIVES, and why:
  * price, name, badges, earnings — not valuation output.
  * `subject` and `benchmark` MULTIPLES (P/E, EV/EBITDA, P/S, EV/Sales) — a ratio of two
    figures in the same currency is currency-neutral, so it is unaffected by the mismatch
    that triggers most refusals. The per-share values IMPLIED by those multiples are not:
    they price a reporting-currency per-share figure against a USD quote, which is exactly
    how KSPI produced a "$326 implied value" on a $92 stock.
  * quality / growth / health / momentum sub-scores — computed from ratios and price, with
    no fair value in them.
  * the REASON. The guard's own sentence quotes the withheld figure ("the model's $1,289.68
    is 14.0x the $92.19 price"). That is the one place the number belongs: it is the
    evidence for withholding, not a valuation. It is deliberately kept.

WHAT DOES NOT SURVIVE, and the honest reason it does not:
  * the composite score and its recommendation. See `SCORE_NOTE` below — this is not a
    display preference, it is a live defect in the score itself.
"""
from __future__ import annotations

from typing import Any, Optional

# Marker written onto every block this module empties, so the renderer can tell
# "withheld on purpose" apart from "the data never arrived" and say so.
WITHHELD = "withheld"

# The refusal wording used wherever a card would otherwise have drawn a number. The
# blend's own `reason` is appended by the caller; this is the connective tissue that says
# WHY this particular card went away.
CARD_REASONS = {
    "scenarios": "Bear, base and bull are the same valuation re-run on shifted assumptions, "
                 "so they are withheld with it.",
    "montecarlo": "The distribution is that same valuation re-run thousands of times, so it "
                  "is withheld with it — including the share of trials that came out above "
                  "the price.",
    "sensitivity": "The grid is that same valuation at other discount and growth rates, so "
                   "it is withheld with it.",
    "fcf": "The projection is the forecast the valuation was built from, so it is withheld "
           "with it.",
    "comps": "Multiples are ratios and are shown. The per-share values implied by them are "
             "not: they apply a peer multiple to this company's own reported figures, which "
             "is the step the refusal is about.",
    "reverse": "The market-implied growth read is solved from the same model, so it is "
               "withheld with it.",
    "score": "The valuation part of the score is computed from figures that were withheld, "
             "so the overall score and its recommendation are not shown for this name.",
}

# ---------------------------------------------------------------------------- #
# WHY THE SCORE GOES TOO — measured, not assumed (KSPI, 2026-08-05).
#
# The engine lane reported that `publication_guard` runs BEFORE `compute_score`, so the
# score might legitimately be "everything except the DCF". It is not. `compute_score` is
# called with `base_fv=None` (pipeline.py:280), which correctly drops the margin-of-safety
# term — and then `_valuation_score` (scoring.py:83-90) rebuilds the same number out of two
# survivors:
#
#     scoring.py:83  mc.prob_undervalued        weight 0.30 of the valuation sub-score
#     scoring.py:86  comps.comps_fair_value     weight 0.15 of the valuation sub-score
#
# `mc.prob_undervalued` is the share of Monte Carlo trials whose value exceeds the price —
# trials of the withheld DCF. On KSPI it is 1.00, so the withheld valuation enters the score
# at full strength through the back door, and the valuation sub-score printed 100.0/100 on a
# name the model had just declined to value. The comps term ($326 implied vs a $92 price) is
# corrupted by the same currency mismatch.
#
# It is worse than a leak. The composite has a sanity cap — scoring.py:228, "never surface a
# >5x fair value as a strong buy", which caps the score at 50 — and it is written
# `if base_fv and ...`, so it CANNOT fire once the guard has set `base_fv = None`. Publishing
# the bad number capped KSPI at 50; withholding it let KSPI print 93 "Strong Buy".
#
# Measured on the seven names in the report, guard firing, before this change:
#     KSPI 93 Strong Buy (valuation 100.0) · GILD 87 Strong Buy (80.2) · JD 79 Buy (99.1)
#     CI 71 Buy (99.6) · CHTR 69 Buy (100.0) · STLA 45 Reduce (48.2)
#
# Fixing that belongs to the engine lane and is NOT done here: this module must not quietly
# redefine what the score means to solve a display problem. What it does instead is refuse to
# publish a number it can show is contaminated, and say so on the page in those words.
SCORE_NOTE = (
    "The overall score is not shown for this name. Its valuation component is computed in "
    "part from the same figures the model just declined to publish, so the composite would "
    "not mean what it appears to mean. The components that do not depend on a fair value — "
    "quality, growth, financial health and momentum — are shown below."
)


def is_withheld(payload: dict) -> bool:
    """True when the publication guard refused to publish a fair value for this name.

    Deliberately the SAME test the renderer's headline uses (`app.js:205`): the blend says
    not-valuable AND no headline value survived. Both halves matter — a name with no blend
    at all is a different (missing-data) state and is not this one.
    """
    if not isinstance(payload, dict):
        return False
    blend = payload.get("fair_value_blend") or {}
    return blend.get("valuable") is False and payload.get("base_fair_value") is None


def _blank(d: Optional[dict], keys, marker: str = WITHHELD) -> Optional[dict]:
    """Set `keys` to None on a copy of `d` and mark it withheld."""
    if not isinstance(d, dict):
        return d
    out = dict(d)
    for k in keys:
        if k in out:
            out[k] = None
    out[marker] = True
    return out


# Per-share money, in the reporting currency, that the refusal is about.
_DCF_MONEY = ("per_share", "equity_value", "enterprise_value", "pv_explicit",
              "pv_terminal", "terminal_value", "net_debt")
_MC_MONEY = ("mean", "median", "std", "p5", "p10", "p25", "p75", "p90", "p95",
             "prob_undervalued", "hist_bins", "hist_counts")


def withhold_derived_figures(payload: dict) -> dict:
    """Strip every figure derived from a fair value the model refused to publish.

    Returns the payload unchanged when the guard did not fire. Pure: takes and returns a
    plain dict, so the whole rule is unit-testable without a browser or a network call.
    """
    if not is_withheld(payload):
        return payload

    out = dict(payload)
    reason = ((out.get("fair_value_blend") or {}).get("reason") or "").strip()
    out[WITHHELD] = {"reason": reason, "cards": dict(CARD_REASONS), "score_note": SCORE_NOTE}

    # 1. The scenario cone — the bug as reported.
    fvs = dict(out.get("fair_value_scenarios") or {})
    out["fair_value_scenarios"] = {"method": fvs.get("method", ""), "bear": None,
                                   "base": None, "bull": None, WITHHELD: True}

    # 2. The raw DCF the cone was built from, in every shape it is carried in.
    out["dcf_per_share"] = None
    scen = dict(out.get("scenarios") or {})
    for case in ("bear", "base", "bull"):
        if isinstance(scen.get(case), dict):
            case_d = _blank(scen[case], _DCF_MONEY)
            case_d["rows"] = []          # the FCF projection the valuation was built from
            scen[case] = case_d
        scen[case + "_price"] = None
    scen[WITHHELD] = True
    out["scenarios"] = scen

    # 3. The blend's own lens values and its bear/bull band — the withheld number by parts.
    blend = dict(out.get("fair_value_blend") or {})
    blend["lenses"] = {}
    blend["value_low"] = blend["value_high"] = None
    out["fair_value_blend"] = blend
    out["growth_lens"] = None

    # 4. Monte Carlo, sensitivity, reverse DCF — the same valuation in three other costumes.
    out["montecarlo"] = _blank(out.get("montecarlo"), _MC_MONEY)
    sens = dict(out.get("sensitivity") or {})
    sens["grid"] = []
    sens[WITHHELD] = True
    out["sensitivity"] = sens
    out["reverse"] = _blank(out.get("reverse"),
                            ("implied_start_growth", "implied_avg_growth", "base_start_growth",
                             "base_avg_growth", "implied_target_margin", "base_target_margin",
                             "growth_verdict", "margin_verdict", "implied_growth_bounded"))

    # 5. Comps: ratios stay, per-share values implied from them do not.
    comps = dict(out.get("comps") or {})
    comps["implied"] = {}
    comps["comps_fair_value"] = None
    comps[WITHHELD] = True
    out["comps"] = comps

    # 6. The score — contaminated by (2) and (5) through the back door. See SCORE_NOTE.
    score = dict(out.get("score") or {})
    subs = dict(score.get("subscores") or {})
    subs["valuation"] = None
    score["subscores"] = subs
    score["score"] = None
    score["recommendation"] = None
    score["confidence"] = "low"
    score["drivers"] = [d for d in (score.get("drivers") or [])
                        if not _quotes_withheld_value(d)]
    score[WITHHELD] = True
    out["score"] = score
    return out


# Driver lines that quote a withheld figure. `_valuation_score` writes exactly three shapes
# (scoring.py:81/85/90); matching on their wording is brittle by nature, so the test suite
# pins it against real driver strings rather than trusting this list to stay right.
_WITHHELD_DRIVER_MARKERS = (
    "base fair value",          # "Base fair value $X vs $Y -> +N% margin of safety."
    "monte carlo",              # "Monte Carlo: N% of trials value it above the price."
    "comps imply",              # "Comps imply $X (+N%)."
    "model fair value",         # the >5x / <0.2x sanity lines
)


def _quotes_withheld_value(line: Any) -> bool:
    s = str(line or "").lower()
    return any(m in s for m in _WITHHELD_DRIVER_MARKERS)
