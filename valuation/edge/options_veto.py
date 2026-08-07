"""options_veto.py — the equity composite as a VETO on options alerts.  [AUDIT U7]

`VALQUO_EDGE_AUDIT.md:2109` proposes the cheap inverse of U1: keep the existing alert
generation and simply refuse any alert whose underlying sits in the BOTTOM decile of the
equity composite. A veto needs only that the bottom decile underperforms — which the panel's
monotonicity already establishes — whereas an entry signal needs the top decile to move enough,
within the contract's life, to beat decay and spread. Strictly the easier bar.

**The join did not exist before this file, and it is the part that can silently be wrong.**
Alerts are daily (2016-01 → 2025-10); the panel has 69 quarterly-ish rebalance dates. The
composite attached to an alert must come from the most recent rebalance date **strictly ≤** the
alert date. The tempting alternative — the *enclosing* rebalance, i.e. the nearest date in
either direction — scores the alert with filings that were not public when it fired. That is
look-ahead of up to a full quarter, it would flatter every U7 number, and it is exactly the
failure mode this module is most likely to have. `as_of_index` therefore implements only the
backward-looking join, and `enclosing_index` exists solely so a test can prove the two differ
and that the shipped path is the conservative one.

**Two claims live here and they are not the same claim** (pre-registered, session 6):

  * **U7-A, practical.** Does vetoing lift the shipped book's expectancy at an acceptable
    retention rate? A live product does not care where its improvement comes from.
  * **U7-B, mechanism.** Is the composite improving the ALERT, or merely describing the
    UNDERLYING? The identical veto is applied to the random-entry control book. If the control
    lifts as much, the composite has learned nothing about the alert's day-selection, and the
    honest sentence is "a property of the underlying, not of the alert". This is the R10/O20
    lesson applied in advance: the point-in-time liquidity screen helped the control too, and
    nobody had checked until it was measured.

Every number produced here sits inside a book that R2 showed loses to random entry
(+3.41%/trade against a control's +10.06%). A veto that improves this book improves a book with
a negative day-selection edge. That sentence travels with the results.
"""
from __future__ import annotations

import bisect
from typing import Optional

import numpy as np

from . import options_stats as OS


# --------------------------------------------------------------------------- the join ------
def as_of_index(rebalance_dates, alert_date) -> Optional[int]:
    """Index of the most recent rebalance date **strictly ≤ `alert_date`**, or None.

    `rebalance_dates` must be sorted ISO date strings. None means the alert fired before any
    rebalance the panel knows about; such an alert is EXCLUDED, never imputed to the first
    date, because imputing would score a 2016 alert with 2009 fundamentals and call it coverage.
    """
    i = bisect.bisect_right(rebalance_dates, alert_date)
    return (i - 1) if i > 0 else None


def enclosing_index(rebalance_dates, alert_date) -> Optional[int]:
    """The NEAREST rebalance date in either direction — the look-ahead variant.

    Not used by anything that produces a number. It exists so `test_u7_the_join_is_backward_
    looking_only` can assert that the two disagree on real dates and that the shipped join is
    the one that never reaches forward. A join whose correctness is asserted only by a comment
    is a join nobody has tested.
    """
    if not rebalance_dates:
        return None
    i = bisect.bisect_left(rebalance_dates, alert_date)
    if i == 0:
        return 0
    if i >= len(rebalance_dates):
        return len(rebalance_dates) - 1
    before, after = rebalance_dates[i - 1], rebalance_dates[i]
    return i if (_days(after, alert_date) < _days(alert_date, before)) else i - 1


def _days(a: str, b: str) -> int:
    import datetime as dt
    return abs((dt.date.fromisoformat(a[:10]) - dt.date.fromisoformat(b[:10])).days)


def composite_by_date(panel, cols, weights) -> dict:
    """{iso_date: {ticker: (composite, pct_rank_within_that_cross_section)}}.

    The composite is `composite_from_frame`, i.e. the ONE composite B7 left in the tree — the
    same object the backtest ranks deciles with and the same one the live screener scores.
    Building a second one here would reintroduce exactly the disagreement B7 removed.

    `pct_rank` is 0.0 for the WORST composite in the cross-section and 1.0 for the best, so
    "bottom decile" is `pct_rank < 0.1` regardless of how many names the panel carries that
    date. Ranking on percentile rather than on the raw score is deliberate: composite scale
    drifts across dates and a fixed score cut would veto different fractions in different years.
    """
    from ..screener.cross_sectional import zscore
    from .fundamental_panel import composite_from_frame

    out = {}
    for d in sorted(panel["date"].unique()):
        sub = panel[panel["date"] == d]
        comp = composite_from_frame(sub, cols, weights, zscore)
        tk = sub["ticker"].values
        ok = np.isfinite(comp)
        if int(ok.sum()) < 20:
            continue
        c_ok = comp[ok]
        order = np.argsort(np.argsort(c_ok))          # 0 = worst composite
        pct = order / max(1, len(c_ok) - 1)
        key = str(d)[:10]
        out[key] = {str(t): (float(c), float(p))
                    for t, c, p in zip(tk[ok], c_ok, pct)}
    return out


def join_alerts(rows, by_date: dict, universe: Optional[set] = None) -> dict:
    """Attach the as-of composite and its percentile to every alert row.

    Returns `{"rows": [...], "coverage": {...}}`. Joined rows gain `u7_comp`, `u7_pct`,
    `u7_asof` and — when `universe` is supplied — `u7_pct_univ`, the percentile computed
    **within the options universe only**.

    The second percentile matters and is pre-registered as its own cell. The options book is
    187 megacaps inside a ~1,500-name cross-section that reaches down to sub-dollar stocks;
    if those 187 never populate the full panel's bottom decile, a full-panel bottom-decile veto
    retains 100% of alerts and is vacuously "adoptable". Measuring both is the only way to find
    that out rather than assume it either way.
    """
    dates = sorted(by_date)
    joined, no_ticker, no_date = [], 0, 0
    seen_names, joined_names = set(), set()
    for r in rows:
        tk = str(r.get("ticker") or "")
        seen_names.add(tk)
        a = str(r.get("alert_ts") or "")[:10]
        i = as_of_index(dates, a) if (a and dates) else None
        if i is None:
            no_date += 1
            continue
        row_map = by_date[dates[i]]
        hit = row_map.get(tk)
        if hit is None:
            no_ticker += 1
            continue
        c, p = hit
        r2 = dict(r)
        r2["u7_comp"], r2["u7_pct"], r2["u7_asof"] = c, p, dates[i]
        joined.append(r2)
        joined_names.add(tk)

    if universe:
        _rank_within_universe(joined, by_date, universe)

    n = len(rows)
    return {"rows": joined,
            "coverage": {"n_alerts": n, "n_joined": len(joined),
                         "alert_coverage": (len(joined) / n) if n else None,
                         "n_unjoined_no_composite_for_ticker": no_ticker,
                         "n_unjoined_before_first_rebalance": no_date,
                         "n_names_in_alerts": len(seen_names),
                         "n_names_joined": len(joined_names),
                         "name_coverage": (len(joined_names) / len(seen_names)
                                           if seen_names else None),
                         "names_never_joined": sorted(seen_names - joined_names)[:60]}}


def _rank_within_universe(joined, by_date, universe):
    """Second percentile: the alert's composite rank among the OPTIONS names only, as of the
    same rebalance date. Computed per date so a name's standing is judged against the pool it
    is actually competing with for alert attention."""
    cache = {}
    for d, row_map in by_date.items():
        vals = sorted((v[0], t) for t, v in row_map.items() if t in universe)
        if len(vals) < 5:
            continue
        cache[d] = {t: (i / (len(vals) - 1)) for i, (_, t) in enumerate(vals)}
    for r in joined:
        m = cache.get(r["u7_asof"])
        if m is not None and r["ticker"] in m:
            r["u7_pct_univ"] = float(m[r["ticker"]])


# --------------------------------------------------------------------------- the veto ------
def apply_veto(rows, cut: float, field: str = "u7_pct") -> tuple:
    """(kept, dropped) — drop every alert whose percentile is BELOW `cut`.

    A row missing `field` is KEPT. A veto that also silently discards everything it could not
    score would conflate "the composite says no" with "the composite has no opinion", and the
    retention figure — which is what the pre-registered adoption rule turns on — would be
    measuring coverage instead of the filter.
    """
    kept, dropped = [], []
    for r in rows:
        p = r.get(field)
        (dropped if (p is not None and float(p) < cut) else kept).append(r)
    return kept, dropped


def decile_table(rows, field: str = "u7_pct", n_q: int = 10) -> list:
    """Expectancy per composite decile — the audit's actual instruction, before any filter.

    Decile 1 is the BEST composite, matching `quantile_backtest`'s convention (buckets ordered
    best-first) so the two objects can be read side by side without a sign flip. The project
    has already spent a correction on reading `monotonicity` backwards; the ordering here is
    the same ordering, deliberately.
    """
    out = []
    have = [r for r in rows if r.get(field) is not None]
    for q in range(n_q):
        lo, hi = 1.0 - (q + 1) / n_q, 1.0 - q / n_q
        sel = [r for r in have
               if (lo <= float(r[field]) < hi) or (q == 0 and float(r[field]) >= hi)]
        m = OS.mean_pnl(sel)
        wins = [r for r in sel if OS._f(r.get("pnl_pct")) is not None
                and float(r["pnl_pct"]) > 0]
        out.append({"decile": q + 1, "pct_range": [round(lo, 3), round(hi, 3)],
                    "n_trades": len(sel), "mean_pnl_pct": m,
                    "win_rate": (len(wins) / len(sel)) if sel else None})
    return out


def veto_report(real_rows, cut: float, field: str = "u7_pct",
                control_rows=None, seed: int = 0, draws: int = OS.BOOTSTRAP_DRAWS) -> dict:
    """One pre-registered cell of U7: retention, lift, and the control's lift beside it.

    `lift` is mean(kept) − mean(all), i.e. what the shipped book's expectancy becomes if the
    veto is switched on. It is bootstrapped with `date_block_diff` on calendar-month blocks, so
    a drawn month contributes to BOTH arms and the common calendar variance drops out — the
    R3 machinery, unchanged, because the kept book and the full book share their calendar
    exactly.

    When `control_rows` is given the same veto runs on the random-entry control and the two
    lifts are differenced. **That difference, not the real book's lift, is what decides whether
    the composite is telling us anything about the ALERT.**
    """
    kept, dropped = apply_veto(real_rows, cut, field)
    n = len(real_rows)
    rep = {"cut": cut, "field": field, "n_in": n, "n_kept": len(kept),
           "n_dropped": len(dropped),
           "retention": (len(kept) / n) if n else None,
           "mean_all": OS.mean_pnl(real_rows), "mean_kept": OS.mean_pnl(kept),
           "mean_dropped": OS.mean_pnl(dropped),
           "lift": None, "lift_boot": None}
    if rep["mean_kept"] is not None and rep["mean_all"] is not None:
        rep["lift"] = rep["mean_kept"] - rep["mean_all"]
        rep["lift_boot"] = fast_block_diff(kept, real_rows, seed=seed, draws=draws)

    if control_rows is not None:
        ck, cd = apply_veto(control_rows, cut, field)
        c_all, c_kept = OS.mean_pnl(control_rows), OS.mean_pnl(ck)
        rep["control"] = {"n_in": len(control_rows), "n_kept": len(ck),
                          "n_dropped": len(cd),
                          "retention": (len(ck) / len(control_rows)) if control_rows else None,
                          "mean_all": c_all, "mean_kept": c_kept,
                          "lift": (None if c_kept is None or c_all is None
                                   else c_kept - c_all)}
        if rep["control"]["lift"] is not None:
            rep["control"]["lift_boot"] = fast_block_diff(ck, control_rows, seed=seed,
                                                          draws=draws)
        # U7-B. Bootstrapped as a difference-of-differences on shared months: within a drawn
        # month the real book's lift and the control's lift are computed from the same
        # calendar, so what survives is the interaction and not the market.
        if rep["lift"] is not None and rep["control"]["lift"] is not None:
            rep["interaction"] = _lift_gap_boot(real_rows, kept, control_rows, ck,
                                                seed=seed, draws=draws)
    return rep


def _block_sums(rows) -> tuple:
    """(keys, sums, counts) — the only two numbers a block contributes to a mean.

    `date_block_bootstrap` rebuilds the concatenated trade list on every draw and re-reads every
    `pnl_pct`, which on the five-seed control book is ~30,000 Python-level float conversions per
    draw per book, four books, four thousand draws. The mean of a concatenation of blocks is
    exactly `sum(block sums) / sum(block counts)`, so the per-trade work is redundant: it can be
    done once and the bootstrap reduced to adding a few hundred floats per draw.

    This is an EXACT rewrite, not an approximation, and
    `test_u7_the_fast_block_bootstrap_is_exact` asserts it reproduces `OS.date_block_diff` to
    floating point on the same seed by replaying the identical `Random.randrange` sequence.
    """
    g = OS.group_by_block(rows)
    keys = sorted(g)
    sums, counts = {}, {}
    for k in keys:
        v = [OS._f(r.get("pnl_pct")) for r in g[k]]
        v = [x for x in v if x is not None]
        sums[k], counts[k] = float(sum(v)), len(v)
    return keys, sums, counts


def _mean_from_blocks(picks, sums, counts) -> Optional[float]:
    s = 0.0
    n = 0
    for k in picks:
        s += sums[k]
        n += counts[k]
    return (s / n) if n else None


def fast_block_diff(a_rows, b_rows, seed: int = 0, draws: int = OS.BOOTSTRAP_DRAWS) -> dict:
    """`OS.date_block_diff` with the per-trade work hoisted out. Identical output, same seed."""
    import random
    ka, sa, ca = _block_sums(a_rows)
    kb, sb, cb = _block_sums(b_rows)
    keys = sorted(set(ka) & set(kb))
    pa, pb = OS.mean_pnl(a_rows), OS.mean_pnl(b_rows)
    if pa is None or pb is None or len(keys) < 2:
        return {"ok": False, "reason": f"{len(keys)} shared blocks"}
    rnd = random.Random(seed)
    diffs = []
    for _ in range(draws):
        picks = [keys[rnd.randrange(len(keys))] for _ in range(len(keys))]
        va = _mean_from_blocks(picks, sa, ca)
        vb = _mean_from_blocks(picks, sb, cb)
        if va is not None and vb is not None:
            diffs.append(va - vb)
    if len(diffs) < 100:
        return {"ok": False, "reason": "too few usable draws"}
    diffs.sort()
    lo = diffs[int(0.025 * len(diffs))]
    hi = diffs[min(len(diffs) - 1, int(0.975 * len(diffs)))]
    return {"ok": True, "a": pa, "b": pb, "diff": pa - pb, "ci95": [lo, hi],
            "draws": len(diffs), "n_blocks": len(keys), "block": OS.DEFAULT_BLOCK,
            "excludes_zero": bool(lo > 0 or hi < 0),
            "negative_at_significance": bool(hi < 0),
            "positive_at_significance": bool(lo > 0),
            "se": OS._sd(diffs),
            "note": "paired block bootstrap: a drawn month contributes to BOTH arms."}


def _lift_gap_boot(real_all, real_kept, ctrl_all, ctrl_kept, seed=0,
                   draws=OS.BOOTSTRAP_DRAWS) -> dict:
    """CI on (real lift − control lift) by resampling calendar months once for all four books.

    Four books, ONE draw of months. Drawing March 2020 pulls March 2020 out of the real book,
    the vetoed real book, the control and the vetoed control simultaneously. Resampling them
    independently would treat the same month's crash as four separate shocks and would widen
    the interval on a quantity from which the crash largely cancels.
    """
    import random
    blocks = [_block_sums(x) for x in (real_all, real_kept, ctrl_all, ctrl_kept)]
    keys = sorted(set(blocks[0][0]) & set(blocks[1][0])
                  & set(blocks[2][0]) & set(blocks[3][0]))
    if len(keys) < 2:
        return {"ok": False, "reason": f"{len(keys)} shared blocks"}
    rnd = random.Random(seed)
    vals = []
    for _ in range(draws):
        picks = [keys[rnd.randrange(len(keys))] for _ in range(len(keys))]
        m = [_mean_from_blocks(picks, s, c) for _, s, c in blocks]
        if all(x is not None for x in m):
            vals.append((m[1] - m[0]) - (m[3] - m[2]))
    if len(vals) < 100:
        return {"ok": False, "reason": "too few usable draws"}
    vals.sort()
    lo = vals[int(0.025 * len(vals))]
    hi = vals[min(len(vals) - 1, int(0.975 * len(vals)))]
    point = ((OS.mean_pnl(real_kept) - OS.mean_pnl(real_all))
             - (OS.mean_pnl(ctrl_kept) - OS.mean_pnl(ctrl_all)))
    return {"ok": True, "point": point, "ci95": [lo, hi], "draws": len(vals),
            "n_blocks": len(keys), "excludes_zero": bool(lo > 0 or hi < 0),
            "positive_at_significance": bool(lo > 0),
            "note": "difference of lifts; one month draw shared by all four books."}
