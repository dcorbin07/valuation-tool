"""loo_holdout.py — the PRE-REGISTERED, held-out leave-one-out ablation. [session 7]

WHY THIS IS NOT `holdout_theme_validate`, AND WHY THAT MATTERS.

`holdout_theme_validate` decides with a fixed rule: a theme is a candidate for zeroing if its
MEDIAN IC on the decide half is <= 0. That rule cannot express the hypothesis this module
tests. Measured on the corrected 69-date panel (audit B8, same session), it never fires on
`quality`, `capital_discipline` or `institutional` in either direction, because their ICs are
comfortably positive — and `capital_discipline` is precisely the theme session 6's exploratory
leave-one-out nominated as worth dropping.

That is X3's central result arriving a second time, as a property of the instrument: **theme IC
does not predict marginal contribution.** `size` has the WORST theme IC (-0.30) and carries the
composite's entire statistical significance. An IC-gated selection rule would therefore build
the very error X3 exposed into the design of the test meant to check it.

So the decide rule here is the LEAVE-ONE-OUT EFFECT ITSELF, measured on the decide half. That
is the quantity the hypothesis is about.

THE PROTOCOL, fixed before any number existed (`HANDOFF_edge_audit.md`, session 7 §1):

  1. Split the rebalance dates in half BY TIME and EMBARGO the boundary date. With
     rebalance == horizon == 63d, that date's forward window is the only one that can straddle
     the split. Identical machinery and identical embargo to `holdout_theme_validate`, so the
     two are comparable.
  2. DECIDE half: run all seven arms — the flat composite with one theme dropped and the
     remainder re-normalised to flat 1/(k-1) — and rank by decide-half top-decile alpha gain
     against the full composite. SELECT THE SINGLE BEST ARM.
  3. MEASURE half: measure ONLY that arm. One selection, one degree of freedom. The measure
     half informs nothing about which arm was chosen.
  4. Both directions, so no verdict rests on one arbitrary split.

WHAT MAKES THIS A REAL TEST RATHER THAN A RE-QUOTE. Session 6's leave-one-out was seven
correlated comparisons on the full sample, reported for their extremes, generated after seeing
the prefix curve. The maximum of seven noisy draws is biased upward by construction. Re-running
those seven comparisons and quoting the best one again would measure nothing new. Selecting on
data you may look at and measuring on data you may not is the only thing that distinguishes a
real effect from that bias.

VERDICT, against the margins already committed before the P6 runs (`MIN_HOLDOUT_*` — 100bps of
annual alpha, on economic grounds, and 0.25 of long-short t as a noise floor). Reusing them is
deliberate: inventing a fresh pair after seeing session 6's exploratory numbers would be
threshold-shopping.

  * `adopted_eligible` — the selected arm clears BOTH margins in BOTH directions. Eligible, not
    adopted: a weight change needs its own gate on top of this.
  * `rejected`         — the selected arm is negative on the measure half in both directions.
  * `null`             — anything else. Per RUN_RULES 6 a result that is ambiguous against its
    own threshold IS a null, not a judgement call.

The full seven-arm measure-half distribution is reported alongside and CARRIES NO VERDICT. It
is there so the selected arm can be read against the spread it was drawn from, which is the
context that makes a single number interpretable.
"""
from __future__ import annotations

from .fundamental_panel import (MIN_HOLDOUT_ALPHA_GAIN, MIN_HOLDOUT_TSTAT_GAIN,
                                quantile_backtest)

DIRECTIONS = ("decide_early_measure_late", "decide_late_measure_early")


def flat(cols) -> dict:
    """Equal weight across whatever themes are present.

    The deployed composite is flat 1/7 and was never tuned, so a dropped-theme arm is flat
    1/6 rather than 1/7-with-a-hole: the question is "this composite without that theme", not
    "this composite with six sevenths of its mass".
    """
    n = len(cols)
    return {c: (1.0 / n if n else 0.0) for c in cols}


def split(dates, embargo=True):
    """Halve the date list by time, dropping the boundary date to the embargo.

    Returned as (early, late). The boundary is excluded from BOTH halves rather than assigned
    to one — with rebalance == horizon it is the single date whose forward window straddles
    the split, so putting it in either half leaks that window across it.
    """
    ds = sorted(dates)
    mid = len(ds) // 2
    return ds[:mid], (ds[mid + 1:] if embargo else ds[mid:]), (ds[mid] if embargo else None)


def _score(panel, cols, weights, n_q, horizon) -> dict:
    r = quantile_backtest(panel, cols, weights, n_q=n_q, horizon=horizon) or {}
    return {"top_decile_alpha": r.get("top_decile_alpha"),
            "long_short_tstat": r.get("long_short_tstat"),
            "monotonicity": r.get("monotonicity")}


def _gain(arm, base) -> dict:
    def d(k):
        a, b = arm.get(k), base.get(k)
        return None if a is None or b is None else a - b
    return {"d_top_decile_alpha": d("top_decile_alpha"),
            "d_long_short_tstat": d("long_short_tstat")}


def arms_on(panel, cols, n_q=10, horizon=63) -> dict:
    """Every leave-one-out arm on one block of dates, plus the full-composite baseline."""
    base = _score(panel, cols, flat(cols), n_q, horizon)
    out = {"baseline": base, "arms": {}}
    for c in cols:
        rest = [x for x in cols if x != c]
        s = _score(panel, rest, flat(rest), n_q, horizon)
        out["arms"][c] = {"dropped": c, "cols": rest, **s, **_gain(s, base)}
    return out


def loo_holdout(panel, cols, n_q=10, horizon=63, min_dates=16,
                min_alpha_gain=MIN_HOLDOUT_ALPHA_GAIN,
                min_tstat_gain=MIN_HOLDOUT_TSTAT_GAIN) -> dict:
    """The pre-registered test. See the module docstring for the protocol and the verdict rule."""
    out = {"protocol": "select the best leave-one-out arm on the decide half by top-decile "
                       "alpha gain; measure that arm only on the held-out half; both directions",
           "decide_statistic": "top_decile_alpha gain vs the full flat composite",
           "min_alpha_gain": min_alpha_gain, "min_tstat_gain": min_tstat_gain,
           "n_arms": len(cols), "cols": list(cols), "splits": {}}
    if panel is None or getattr(panel, "empty", True) or len(cols) < 3:
        return {**out, "status": "need a panel and at least 3 themes"}
    dates = sorted(panel["date"].unique())
    if len(dates) < min_dates:
        return {**out, "status": f"only {len(dates)} dates, need {min_dates}"}

    early, late, boundary = split(dates)
    out["boundary_date_embargoed"] = str(boundary)
    out["n_dates"] = {"total": len(dates), "early": len(early), "late": len(late)}
    halves = {DIRECTIONS[0]: (early, late), DIRECTIONS[1]: (late, early)}

    for name, (dec, mea) in halves.items():
        p_dec = panel[panel["date"].isin(dec)]
        p_mea = panel[panel["date"].isin(mea)]
        d = arms_on(p_dec, cols, n_q=n_q, horizon=horizon)
        m = arms_on(p_mea, cols, n_q=n_q, horizon=horizon)

        # SELECTION — decide half only. A theme whose arm could not be scored is not eligible;
        # it is not silently treated as a zero gain, which would let a failed arm win a weak
        # field.
        ranked = sorted([(c, v["d_top_decile_alpha"]) for c, v in d["arms"].items()
                         if v["d_top_decile_alpha"] is not None],
                        key=lambda kv: -kv[1])
        sel = ranked[0][0] if ranked else None
        sm = (m["arms"].get(sel) or {}) if sel else {}
        da, dt = sm.get("d_top_decile_alpha"), sm.get("d_long_short_tstat")
        out["splits"][name] = {
            "decide_dates": len(dec), "measure_dates": len(mea),
            "decide_ranking": [{"dropped": c, "d_top_decile_alpha": g} for c, g in ranked],
            "selected": sel,
            "selected_decide_gain": ranked[0][1] if ranked else None,
            "measure_baseline": m["baseline"],
            "measure_selected": sm,
            # NO VERDICT — the spread the selected arm has to be read against.
            "measure_all_arms": [{"dropped": c,
                                  "d_top_decile_alpha": v["d_top_decile_alpha"],
                                  "d_long_short_tstat": v["d_long_short_tstat"]}
                                 for c, v in m["arms"].items()],
            "clears_alpha_margin": bool(da is not None and da >= min_alpha_gain),
            "clears_tstat_margin": bool(dt is not None and dt >= min_tstat_gain),
            "improves": bool(da is not None and dt is not None
                             and da >= min_alpha_gain and dt >= min_tstat_gain),
            "negative": bool(da is not None and da < 0),
        }

    picks = [out["splits"][s]["selected"] for s in DIRECTIONS]
    good = [out["splits"][s]["improves"] for s in DIRECTIONS]
    neg = [out["splits"][s]["negative"] for s in DIRECTIONS]
    out["same_theme_selected_both_directions"] = bool(picks[0] is not None and picks[0] == picks[1])
    out["selected"] = {s: out["splits"][s]["selected"] for s in DIRECTIONS}
    out["verdict"] = ("adopted_eligible" if all(good)
                      else "rejected" if all(neg) else "null")
    return out
