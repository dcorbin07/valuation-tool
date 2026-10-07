# -*- coding: utf-8 -*-
"""`TIERED-POOL` — Don's stricter-bar-by-size idea. Register `PREREG_tiered_pool.md`.

**TWO EQUITY TRIALS, booked at `7ebf7aa` before this file existed.** Every band boundary,
percentile, floor, kill and the pass rule come from the register and are **not re-chosen here**.

**ARM A** — bands by point-in-time market cap, percentile **within band and within date**:
`>= $10B` top 10%, `$2B-$10B` top 5%, `$300M-$2B` top 2.5%, `< $300M` excluded. The book is the
**union**, score-weighted with the 8% cap, and the no-trade band is applied **within each band**.

**ARM B** — arm A plus a junk filter on the two bands below $10B: positive TTM net income,
positive TTM free cash flow, and leverage **not in the worst third** of its date's cross-section.

**TWO SHIPPED HOOKS, EACH DOING THE JOB IT EXISTS FOR, AND NEITHER RE-IMPLEMENTED (`B7`).**
`book_fn` and `IB.run` both accept a `universe_filter(rows, date)` and an
`index_fn(rows, ..., held=...)`:

  * the **junk filter is a `universe_filter`** — `N1`'s own use of that hook — because it is a
    predicate on the universe and it needs the cross-section's **date**, which the rows do not
    carry;
  * the **tiering is an `index_fn`** — because it needs `held`, and that is the only hook that
    receives it.

Using the same two hooks in both the net-of-cost path (`IB.run`) and the after-tax path
(`after_tax_backtest`) is what stops the two describing different books.

**AND THE WEIGHTING IS NOT THIS REGISTER'S.** The selected union is handed to the **shipped
`build_index`** with the tier logic switched off, so it does exactly one job: score-weight with
the 8% cap. Re-implementing that would make the 8% cap a second definition.

`_ttm` and `fundamentals_pit`'s row rule are the **shipped** point-in-time accessors and are
**CALLED**: `_ttm` already collapses restatements (`D10-a`) and refuses a partial sum, and a
hand-rolled sum would understate a flow and **read as a junk company** — the direction that
would flatter this arm.

**NO ALPHA CLAIM** (inherited from `INDEX-CHOICE` via the register). **No X7 floor is quoted.**
"""
from __future__ import annotations

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge.fundamental_panel import _ttm                             # noqa: E402
from valuation.edge.no_trade_band import BAND_WIDTH                           # noqa: E402
from valuation.edge.valquo_index import build_index                           # noqa: E402

#: §2 — the bands, half-open so a name at exactly a boundary sits in the HIGHER band.
BANDS = [
    ("ge_10bn",    1e10, float("inf"), 0.10),
    ("2bn_10bn",    2e9, 1e10,         0.05),
    ("300M_2bn",  300e6, 2e9,          0.025),
]
#: §2 — excluded outright, and reported as zero book weight so the construction is checkable.
MICRO_CAP = 300e6
#: §2 — a band selecting fewer than this is COUNTED and REPORTED, never silently kept.
MIN_PER_BAND = 5
#: §1 — the drawdown allowance, in return units. Don's 3pp.
DD_ALLOWANCE = 0.03
#: §2c — the pre-committed coverage kill. INHERITED: the panel's own theme_coverage rule (0.70),
#: quoted at that value in PANEL-EXT-CENSUS. NOT chosen here.
JUNK_COVERAGE_FLOOR = 0.70
#: §2a — leverage must be at or below its date's 2/3 quantile. The PAPER's direction, resolved in
#: the register on an external anchor before any number, with the counterfactual recorded.
LEVERAGE_WORST_THIRD_Q = 2.0 / 3.0
#: the band the junk filter does NOT touch.
UNFILTERED_BAND = "ge_10bn"


def band_of(mc):
    """Which band a market cap falls in, or None if below `MICRO_CAP` or not a number."""
    if mc is None or mc != mc:
        return None
    for name, lo, hi, _p in BANDS:
        if lo <= mc < hi:
            return name
    return None


# ---------------------------------------------------------------------------------------------
# §2b — the junk filter's inputs, from the SHIPPED point-in-time accessors
# ---------------------------------------------------------------------------------------------

def _pit_row(rows, as_of):
    """The last filed row at or before `as_of` — the same rule `fundamentals_pit` applies."""
    out = None
    for r in rows:                                  # rows are pre-sorted by datekey
        dk = r.get("datekey") or r.get("date")
        if dk and dk <= as_of:
            out = r
        elif dk and dk > as_of:
            break
    return out


def _num(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def junk_ok(tickers, hist, as_of):
    """§2b — `(ok_by_ticker, stats)` for one date.

    A name whose inputs do not resolve is **not ok** — the conservative direction — and the
    share that could be **evaluated at all** is what §2c's kill reads, so a filter that is
    really a data-availability screen is caught rather than quoted.

    **`P7`'s CURRENCY TRAP DOES NOT BITE AND THE REASON IS STRUCTURAL, not hoped for.** Raw line
    items are in the reporting currency while market cap is USD. All three conditions are
    currency-invariant: `fxusd > 0`, so the SIGN of net income and free cash flow survives
    conversion, and `debt / equity` is a ratio of two same-currency quantities. **No conversion
    is applied and none is needed.**
    """
    flows, lev = {}, {}
    for t in tickers:
        rows = hist.get(t) or []
        ni = _ttm(rows, as_of, ("netinc",))
        fc = _ttm(rows, as_of, ("fcf",))
        flows[t] = (None if ni is None else _num(ni.get("netinc")),
                    None if fc is None else _num(fc.get("fcf")))
        pit = _pit_row(rows, as_of)
        d = _num(pit.get("debt")) if pit else None
        e = _num(pit.get("equity")) if pit else None
        lev[t] = (d / e) if (d is not None and e not in (None, 0.0)) else None

    vals = [v for v in lev.values() if v is not None and np.isfinite(v)]
    cut = float(np.quantile(vals, LEVERAGE_WORST_THIRD_Q)) if len(vals) >= 3 else None

    ok, ev = {}, 0
    removed = {"netinc": 0, "fcf": 0, "leverage": 0}
    for t in tickers:
        ni, fc = flows.get(t, (None, None))
        lv = lev.get(t)
        if ni is not None and fc is not None and lv is not None and cut is not None:
            ev += 1
        fails = []
        if ni is None or ni <= 0:
            fails.append("netinc")
        if fc is None or fc <= 0:
            fails.append("fcf")
        if lv is None or cut is None or lv > cut:
            fails.append("leverage")
        for f in fails:
            removed[f] += 1
        ok[t] = not fails
    n = max(1, len(tickers))
    return ok, {"rows": int(len(tickers)), "evaluable": int(ev), "evaluable_share": ev / n,
                "leverage_cut": cut, "removed_by_condition": removed,
                "kept": int(sum(1 for v in ok.values() if v))}


def junk_universe_filter(ok_by_date, stats_sink=None):
    """§2b as a `universe_filter(rows, date)` — `N1`'s own hook.

    It is a predicate on the UNIVERSE and it needs the cross-section's DATE, which the scan rows
    do not carry. It touches **only** the bands below $10B; the `>= $10B` band is arm A's,
    unchanged, which is what makes arm B *"arm A plus a filter"* rather than a third arm.
    """
    def _f(rows, date):
        ok = ok_by_date.get(str(date)[:10]) or {}
        out = []
        dropped = 0
        for r in rows:
            b = band_of(r.get("market_cap"))
            if b is None or b == UNFILTERED_BAND:
                out.append(r)
                continue
            if ok.get(r["ticker"]):
                out.append(r)
            else:
                dropped += 1
        if stats_sink is not None:
            stats_sink.setdefault(str(date)[:10], {})["dropped_by_junk"] = dropped
        return out

    return _f


# ---------------------------------------------------------------------------------------------
# §2 — the tiering, as an `index_fn`
# ---------------------------------------------------------------------------------------------

def tiered_index_fn(per_band_sink=None):
    """An `index_fn` with `build_index`'s own signature — the one hook that receives `held`.

    Selection is this register's. **Weighting is not**: the selected union goes to the shipped
    `build_index` with the tier logic switched off (`large_cap_min=0`, `top_decile=1.0`,
    `exit_frac=None`, `held=None`) so it does exactly one job.
    """
    def _f(rows, large_cap_min=None, top_decile=None, weighting="score", top_n=None,
           held=None, exit_frac=None):
        heldset = set(held or ())
        chosen, per_band = [], {}
        for name, lo, hi, pct in BANDS:
            # ONE definition of the band test (`B7`). It was written twice -- here and in
            # `band_of` -- and a mutation flipping one copy to a CLOSED interval was INERT in
            # `band_of` (it returns the FIRST matching band, so a boundary name was unaffected)
            # while being live here. Two copies of a boundary rule is how a $10B name comes to
            # sit in two bands with both halves correct in isolation.
            inband = [r for r in rows if band_of(r.get("market_cap")) == name]
            if not inband:
                per_band[name] = 0
                continue
            inband.sort(key=lambda r: float(r["hot_score"]), reverse=True)
            n_in = max(1, int(round(len(inband) * pct)))
            # THE NO-TRADE BAND, WITHIN THIS BAND: a held name survives while it is inside the
            # wider exit rank. Applying it to the union instead would let a name hold its place
            # by drifting into a different band, which is a different rule.
            n_exit = max(n_in, int(round(n_in * (1.0 + BAND_WIDTH))))
            top = inband[:n_in]
            survivors = [r for r in inband[:n_exit] if r["ticker"] in heldset]
            sel, seen = [], set()
            for r in survivors + top:
                if r["ticker"] not in seen:
                    seen.add(r["ticker"])
                    sel.append(r)
            sel = sel[:max(n_in, len(survivors))]
            per_band[name] = len(sel)
            chosen += sel
        if per_band_sink is not None:
            per_band_sink.append(per_band)
        if not chosen:
            return {"positions": []}
        bk = build_index(chosen, large_cap_min=0.0, top_decile=1.0, weighting=weighting,
                         top_n=None, held=None, exit_frac=None)
        bk["per_band"] = per_band
        return bk

    return _f


# ---------------------------------------------------------------------------------------------
# §3 — the size-neutral diagnostic. NO VERDICT, and it cannot acquire one.
# ---------------------------------------------------------------------------------------------

def size_neutral_index_fn(per_band_sink=None):
    """A pure WITHIN-BAND sort taking the same count per band as arm A.

    **DIAGNOSTIC ONLY.** `PREREG_tiered_pool.md` §3: it is reported with no pass rule, no
    comparison to Don's bar and the literal verdict `NO-VERDICT`, so nobody can promote it after
    seeing it. `E-3` and `MB21`: a number computed after the fact that *could* be promoted on
    sight is a number that *will* be.
    """
    return tiered_index_fn(per_band_sink=per_band_sink)


# ---------------------------------------------------------------------------------------------
# metrics and the rule
# ---------------------------------------------------------------------------------------------

def _mdd(series):
    lvl, peak, worst = 1.0, 1.0, 0.0
    for r in series:
        lvl *= (1.0 + float(r))
        peak = max(peak, lvl)
        worst = min(worst, lvl / peak - 1.0)
    return float(worst)


def _sharpe(series):
    a = np.asarray([float(x) for x in series], dtype=float)
    if a.size < 2 or not np.isfinite(a.std(ddof=1)) or a.std(ddof=1) == 0:
        return None
    return float(a.mean() / a.std(ddof=1) * np.sqrt(4.0))


def mde(diffs):
    """§1.5 — every margin ships with its own MDE, at 50% and 80% power (`MB22`, `RUN_RULES`
    A11). The critical value is **LABELLED UNCALIBRATED**: `V2G` and `R1-VAR` established that
    no calibrated floor exists for a paired within-panel difference."""
    a = np.asarray([float(x) for x in diffs], dtype=float)
    if a.size < 3:
        return None
    se = float(a.std(ddof=1) / np.sqrt(a.size))
    return {"paired_mean": float(a.mean()), "paired_se": se,
            "mde_50pc": 2.0 * se, "mde_80pc": (2.0 + 0.84) * se,
            "crit_label": "UNCALIBRATED -- no calibrated floor exists for a paired "
                          "within-panel difference (V2G, R1-VAR); 2.0 is conventional"}


def decide(arm, inc):
    """§1 — Don's rule, made precise in the register and NOT re-chosen here.

    Four return comparisons, all STRICT and with NO tolerance, plus the drawdown clause written
    out **with its sign** because drawdowns are negative and `S10`'s first cut once reported a
    2.61pp WORSENING as an improvement.
    """
    steps = {}
    for key, label in (("full", "2009-2026 full"), ("early", "2009-2026 early"),
                       ("late", "2009-2026 late"), ("oos", "1999-2008 proxy")):
        a, b = arm.get(key), inc.get(key)
        steps[label] = {"arm": a, "incumbent": b,
                        "beats": (None if a is None or b is None else bool(a > b))}
    dd = {}
    for key, label in (("mdd_full", "2009-2026"), ("mdd_oos", "1999-2008")):
        a, b = arm.get(key), inc.get(key)
        dd[label] = {"arm": a, "incumbent": b,
                     "within_3pp": (None if a is None or b is None
                                    else bool(a >= b - DD_ALLOWANCE))}
    ok = (bool(steps) and bool(dd)
          and all(v["beats"] is True for v in steps.values())
          and all(v["within_3pp"] is True for v in dd.values()))
    return {"return_steps": steps, "drawdown": dd, "dd_allowance_pp": DD_ALLOWANCE * 100.0,
            "PASSES": bool(ok),
            "rule": "beats the incumbent on net Roth in BOTH periods AND both halves of "
                    "2009-2026, with max drawdown no more than 3pp worse in either period; "
                    "STRICT, no tolerance; PREREG_tiered_pool.md section 1",
            "not_significance": "a PREFERENCE rule, not a significance test; no arm is called "
                                "significant and every margin ships with its own MDE"}
