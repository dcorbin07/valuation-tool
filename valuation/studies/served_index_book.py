# -*- coding: utf-8 -*-
"""INDEX-BOOK — backtest the construction the Valquo Index ACTUALLY serves.

Every backtest figure the site shows is the **full-universe, equal-weighted decile** (~156
names, all caps) — `settings.MEASURED_BASIS` says so in terms, and says the served book is
*"not the served score-weighted large-cap book"*. This module measures the served one.

**THE SELECTION IS NOT RE-IMPLEMENTED: `valquo_index.build_index` IS CALLED (`B7`).** The
large-cap tier filter, the `MIN_NAMES` fallback, the no-trade band, the score weighting and the
8% cap with its redistribution loop all live in that one function, which the live site calls.
Re-deriving any of them here would be exactly the defect `B7` exists to prevent — and it would
be the worst case of it, because the whole point of this item is that the served construction
differs from the measured one, so a lookalike would answer the wrong question.

WHAT HAD TO BE SUPPLIED, and both are stated rather than assumed:

* **`hot_score`**, because the panel carries themes and not a score. `screen.py:344` is
  `scored["hot_score"] = scored["composite"].rank(pct=True) * 99 + 1`, so the score is the
  **PERCENTILE RANK of the composite over the WHOLE scored cross-section**, mapped to [1, 100].
  That matters twice over: the ranking it induces is identical to the composite's (a monotone
  transform), and the score WEIGHTING is therefore on ranks rather than on composite
  magnitudes — which is why `MC10` measured the served weighting at rho 0.9968 to equal weight.
  Applying `score - floor + 1.0` to a raw z-scored composite instead would invent a weight
  dispersion the live book does not have.
* **`price`**, because the panel has none. In `build_index` it is used at line 202 as a presence
  filter and at line 280 as an emitted field, and **nowhere in selection, weighting or the cap**
  — verified by reading every use — so a constant is faithful and is passed as one.

$10B IS APPLIED NOMINALLY, EXACTLY AS LIVE DOES. `build_index`'s test is
`market_cap >= large_cap_min` with `LARGE_CAP_MIN = 10e9`, and there is no inflation adjustment
anywhere on that path. On a panel starting 2009 that makes the tier **mechanically wider over
time** — $10B in 2009 is a bigger company than $10B in 2026 — so the eligible count per date is
required output rather than a footnote, and the fallback flag is reported per date because a
date where fewer than `MIN_NAMES` qualify is not a large-cap book at all.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Everything imported, nothing retyped (`B7`, `MA5`).
from ..edge.valquo_index import (build_index, CONTRACT_MIN_POSITIONS, LARGE_CAP_MIN,
                                 MAX_WEIGHT, MIN_NAMES, TOP_DECILE)
from ..edge.no_trade_band import BAND_WIDTH

PER_YEAR = 4.0          # the panel is quarterly; a period is one 63-day forward window
PRICE_PLACEHOLDER = 1.0


def hot_scores(composite):
    """`screen.py:344` verbatim: the percentile rank of the composite over the whole scored
    cross-section, mapped to [1, 100]. Monotone, so the ranking is the composite's."""
    s = pd.Series(composite)
    return (s.rank(pct=True) * 99.0 + 1.0).values


def scan_rows(g, comp):
    """A panel cross-section as the scan rows `build_index` consumes."""
    hs = hot_scores(comp)
    out = []
    for t, m, h in zip(g["ticker"].values, g["market_cap"].values, hs):
        if h != h:
            continue
        out.append({"ticker": str(t), "hot_score": float(h),
                    "market_cap": (None if m != m else float(m)),
                    "price": PRICE_PLACEHOLDER})
    return out


def book_fn(*, large_cap_min=LARGE_CAP_MIN, weighting="score", top_decile=TOP_DECILE,
            exit_frac=BAND_WIDTH, index_fn=None):
    """A `(sub, comp, held) -> {ticker: weight}` hook for `after_tax_backtest`.

    ONE definition of the construction, shared by the cost arms and the tax arms -- so the
    after-tax figure describes the SAME book the net-of-cost figure does. Two constructions
    would make the tax cost the difference between two different books, which is the shape
    `B7` exists to prevent and would be undetectable by inspection.
    """
    _ix = index_fn or build_index

    def _f(sub, comp, held):
        rows = scan_rows(sub, comp)
        if not rows:
            return {}
        bk = _ix(rows, large_cap_min=large_cap_min, top_decile=top_decile,
                 weighting=weighting, exit_frac=exit_frac, held=sorted(held) or None)
        raw = {p["ticker"]: float(p["weight"]) for p in (bk.get("positions") or [])}
        tot = sum(raw.values()) or 1.0
        return {k: v / tot for k, v in raw.items()}

    return _f


def _ann(xs):
    xs = [x for x in xs if x == x]
    if not xs:
        return None
    return float(np.prod([1.0 + x for x in xs]) ** (PER_YEAR / len(xs)) - 1.0)


def _mdd(xs):
    v, peak, worst = 1.0, 1.0, 0.0
    for x in xs:
        if x != x:
            continue
        v *= (1.0 + x)
        peak = max(peak, v)
        worst = min(worst, v / peak - 1.0)
    return float(worst)


def _sharpe(xs):
    """Annualised Sharpe of the period series, or None where it is not a measurable quantity.

    THE FLOOR IS RELATIVE AND THAT IS NOT FASTIDIOUSNESS. `== 0` is a VALUE-DEPENDENT test:
    `[0.1, 0.1, 0.1]` has a `ddof=1` standard deviation of ~1.5e-17 rather than exactly zero, so
    an equality guard misses and this returns ~1.2e16 -- a confident, enormous, meaningless
    Sharpe. That is the same defect as `SECTOR-NEUTRAL-B6`'s `zscore` guard, `U2`'s `theme_ic`
    and `MA58`'s `_tstat`, which this record has now hit four times; it was found here by the
    test written to pin it rather than by reading.
    """
    a = np.asarray([x for x in xs if x == x], dtype=float)
    if len(a) < 3:
        return None
    sd = float(a.std(ddof=1))
    if sd <= 1e-12 * max(1.0, float(np.abs(a).max())):
        return None
    return float(a.mean() / sd * np.sqrt(PER_YEAR))


def run(panel, cols, weights, *, cost_fn=None, composite_fn=None, zscore_fn=None,
        index_fn=None, exit_frac=BAND_WIDTH, large_cap_min=LARGE_CAP_MIN,
        weighting="score", top_decile=TOP_DECILE) -> dict:
    """Walk the panel's dates, forming the SERVED book at each and holding it one period.

    The cost model is the shipped `one_way_cost_bps` applied to `|target - drifted|` over the
    union of the two books — the same trade definition `turnover_and_costs` uses, because
    counting only entries and exits would understate turnover and flatter the net return.
    """
    if cost_fn is None:
        from ..edge.fundamental_panel import one_way_cost_bps as cost_fn
    if composite_fn is None:
        from ..edge.fundamental_panel import composite_from_frame as composite_fn
    if zscore_fn is None:
        from ..screener.cross_sectional import zscore as zscore_fn
    if index_fn is None:
        index_fn = build_index

    dates = sorted(panel["date"].unique())
    prev_w, prev_cost = {}, {}
    per = []
    for d in dates:
        g = panel[panel["date"] == d]
        if len(g) < 20:
            continue
        comp = composite_fn(g, cols, weights, zscore_fn)
        rows = scan_rows(g, comp)
        if not rows:
            continue
        # THE LIVE FUNCTION, CALLED. Tier, fallback, band, score weighting and cap all inside.
        bk = index_fn(rows, large_cap_min=large_cap_min, top_decile=top_decile,
                      weighting=weighting, exit_frac=exit_frac,
                      held=sorted(prev_w) or None)
        pos = bk.get("positions") or []
        if not pos:
            continue
        # build_index rounds the emitted weights to 5dp, so renormalise -- MC10's own note.
        raw = {p["ticker"]: float(p["weight"]) for p in pos}
        tot = sum(raw.values()) or 1.0
        cur_w = {k: v / tot for k, v in raw.items()}

        ret = dict(zip(g["ticker"].values, g["fwd_ret"].values))
        mc = dict(zip(g["ticker"].values, g["market_cap"].values))
        cur_cost = {t: cost_fn(mc.get(t, float("nan"))) for t in cur_w}
        prev_cost.update(cur_cost)

        turn = cost = 0.0
        # SORTED, and this is a reproducibility fix rather than tidiness. Iterating a SET of
        # ticker strings takes an order that depends on the per-process hash salt, so summing
        # these floats in a different order every run moved 482 leaves of the artifact in their
        # last digits -- found by leaf-diffing a change that could not have touched costs at
        # all. This record already warns that a project whose memory is its results files needs
        # those files to be deterministic; a sorted union costs nothing and removes the whole
        # class.
        for t in sorted(set(prev_w) | set(cur_w)):
            dw = abs(cur_w.get(t, 0.0) - prev_w.get(t, 0.0))
            if dw <= 0:
                continue
            turn += dw
            cost += dw * prev_cost.get(t, cost_fn(float("nan"))) * 1e-4

        live = {t: w for t, w in cur_w.items()
                if ret.get(t) is not None and ret.get(t) == ret.get(t)}
        if not live:
            continue
        lt = sum(live.values()) or 1.0
        gross = float(sum(w * ret[t] for t, w in live.items()) / lt)

        allr = g["fwd_ret"].values
        ew = float(np.nanmean(allr)) if np.isfinite(allr).any() else np.nan

        # THE WITHIN-TIER BENCHMARK, and it is the difference between a finding and a
        # misreading. Every arm's `equal_weight` is the ALL-CAP universe -- which is the
        # comparison the live site's own headline makes, so it has to be reported -- but a
        # large-cap book measured against an all-cap average conflates "the composite does not
        # sort this tier" with "this tier returned less than the universe". `U7` and `S10` were
        # both decided by exactly that conflation.
        #
        # The membership test MIRRORS `build_index`'s filter, which would ordinarily be the
        # `B7` defect -- so it is GATED: the mirror's count must equal the live function's own
        # `n_eligible`, or the row records a failure rather than a number. A benchmark that
        # silently drifts from the selection it benchmarks is worse than no benchmark.
        n_mirror = sum(1 for r in rows if (r.get("market_cap") or 0) >= large_cap_min)
        tier_ok = (n_mirror == int(bk.get("n_eligible") or -1))
        tier_r = [ret[str(r["ticker"])] for r in rows
                  if (r.get("market_cap") or 0) >= large_cap_min
                  and ret.get(str(r["ticker"])) == ret.get(str(r["ticker"]))]
        tier_ew = float(np.mean(tier_r)) if (tier_r and tier_ok) else np.nan
        spy = g["bench_ret"].iloc[0]
        spy = float(spy) if spy == spy else np.nan

        per.append({
            "date": str(d), "gross": gross, "net": gross - cost,
            "equal_weight": ew, "tier_equal_weight": tier_ew,
            "tier_mirror_ok": bool(tier_ok), "tier_mirror_n": n_mirror,
            "spy": spy, "turnover_two_way": turn, "cost": cost,
            "n_book": len(cur_w), "n_eligible": int(bk.get("n_eligible") or 0),
            # `tilt` lives under `criteria`, NOT at the top level. Reading `bk["tilt"]` returns
            # None on every date and makes the fallback census read zero vacuously -- which is
            # the one number this item cannot afford to get wrong, because a date on the
            # fallback is not a large-cap book at all.
            "tilt": (bk.get("criteria") or {}).get("tilt"),
            "band_applied": bool((bk.get("no_trade_band") or {}).get("applied")),
            "n_band_retained": int((bk.get("no_trade_band") or {}).get("n_band_retained") or 0),
            "effective_max_weight": (bk.get("criteria") or {}).get("effective_max_weight"),
            "max_weight": max(cur_w.values()), "min_weight": min(cur_w.values()),
            "dropped_weight": 1.0 - lt,
        })

        grown = {t: w * (1.0 + ret[t]) for t, w in live.items()}
        g_tot = sum(grown.values()) or 1.0
        prev_w = {t: v / g_tot for t, v in grown.items()}

    if not per:
        return {"status": "no periods"}
    net = [p["net"] for p in per]
    gross = [p["gross"] for p in per]
    ew = [p["equal_weight"] for p in per]
    tew = [p["tier_equal_weight"] for p in per]
    spy = [p["spy"] for p in per]
    return {
        "n_periods": len(per),
        "first": per[0]["date"], "last": per[-1]["date"],
        "gross_ann": _ann(gross), "net_ann": _ann(net),
        "equal_weight_ann": _ann(ew), "tier_equal_weight_ann": _ann(tew),
        "spy_ann": _ann(spy),
        "tier_mirror_verified_on_dates": sum(1 for p in per if p["tier_mirror_ok"]),
        "net_alpha_vs_tier_equal_weight": (
            None if _ann(tew) is None else _ann(net) - _ann(tew)),
        "net_alpha_vs_equal_weight": (None if _ann(ew) is None else _ann(net) - _ann(ew)),
        "net_alpha_vs_spy": (None if _ann(spy) is None else _ann(net) - _ann(spy)),
        "cost_drag_ann": (None if _ann(gross) is None or _ann(net) is None
                          else _ann(gross) - _ann(net)),
        "net_sharpe": _sharpe(net), "net_max_drawdown": _mdd(net),
        "annual_turnover": float(np.mean([p["turnover_two_way"] for p in per])) / 2.0 * PER_YEAR,
        "realised_one_way_bps": (
            float(sum(p["cost"] for p in per) / sum(p["turnover_two_way"] for p in per) * 1e4)
            if sum(p["turnover_two_way"] for p in per) > 0 else None),
        # The contract's own floor, applied to the backtested book. `CONTRACT_MIN_POSITIONS` is
        # imported, not retyped, and this is a census rather than a gate -- the panel's universe
        # is not the live scan's, so a shortfall here is a fact about the backtest's early
        # cross-sections and not a claim that the live book is non-conformant.
        "dates_below_contract_min_positions": sum(1 for p in per
                                                  if p["n_book"] < CONTRACT_MIN_POSITIONS),
        "contract_min_positions": CONTRACT_MIN_POSITIONS,
        "book_size": {"min": min(p["n_book"] for p in per),
                      "median": float(np.median([p["n_book"] for p in per])),
                      "max": max(p["n_book"] for p in per)},
        "eligible_tier": {"min": min(p["n_eligible"] for p in per),
                          "median": float(np.median([p["n_eligible"] for p in per])),
                          "max": max(p["n_eligible"] for p in per)},
        "tilt_values": sorted({p["tilt"] for p in per if p["tilt"]}),
        "dates_on_the_fallback": sum(1 for p in per
                                     if p["tilt"] != "large-cap only"),
        "dates_with_no_tilt_label": sum(1 for p in per if not p["tilt"]),
        "band_applied_on_dates": sum(1 for p in per if p["band_applied"]),
        "band_retained_total": sum(p["n_band_retained"] for p in per),
        "effective_cap_values": sorted({p["effective_max_weight"] for p in per}),
        "max_weight_seen": max(p["max_weight"] for p in per),
        "cap_binds_on_dates": sum(1 for p in per if p["max_weight"] >= MAX_WEIGHT - 1e-9),
        "constants": {"LARGE_CAP_MIN": LARGE_CAP_MIN, "MAX_WEIGHT": MAX_WEIGHT,
                      "MIN_NAMES": MIN_NAMES, "TOP_DECILE": TOP_DECILE,
                      "BAND_WIDTH": exit_frac},
        "knobs": {"large_cap_min": large_cap_min, "weighting": weighting,
                  "top_decile": top_decile, "exit_frac": exit_frac},
        "series": per,
    }
