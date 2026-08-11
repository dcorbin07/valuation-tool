"""composite_entry.py — the equity composite as an options ENTRY signal.  [AUDIT U1]

Pre-registered in `PREREG_u1_composite_entry.md`, committed alone at `7d7c414` before this file
existed. Read that document first; it fixes every threshold, arm, control and verdict rule here,
and this module deliberately implements it rather than deciding anything of its own.

U7 asked the cheap inverse — can the composite *refuse* an alert — and failed with a mechanism:
inside 187 megacaps the composite decile is largely a market-cap sort. U1 asks the expensive
question the ledger gated behind that finding: **if you ignore the alert entirely and enter on
the composite's own top names, do you beat entering at random?**

THREE THINGS THIS MODULE IS BUILT AROUND, each of which is a way the answer could be silently
wrong:

  * **ONE MINE, MANY SUBSETS.** Every arm and every null draw is a subset of a single mined grid
    (182 names x 39 rebalance dates). Two arms therefore cannot differ by fill model, contract
    choice, exit policy or calendar — only by which cells they selected. Mining each arm
    separately would reintroduce all four differences and no test could tell them apart.

  * **DATE COMPOSITION IS HELD EXACTLY FIXED.** A null draw takes, *per date*, the same number of
    cells the real arm took on that date. A rule that happened to concentrate in 2020 would
    otherwise be scored against draws that did not, and the comparison would measure the calendar.

  * **THE NULL IS NOT A NO-EFFECT NULL.** Every draw is a real book of real trades on the real
    grid, so the null *contains* whatever the grid earns. Its p95 answers "is this rule
    distinguished among rules of its own size?", never "does selecting names do anything". The
    same distinction TP-BAR turned on, stated here because it is the easiest thing to over-read.

R2 STANDS AND TRAVELS WITH EVERY NUMBER PRODUCED HERE: the shipped alert loses to a five-seed
random-entry control (+3.27%/trade vs +8.33%, sign z -4.961, split-clean per U1-SPLIT
2026-08-11; as published +3.41 vs +10.06, z -4.903). U1 does not repair that, and a
positive U1 would not make the alert tradeable.
"""
from __future__ import annotations

import bisect
from typing import Optional

import numpy as np


# The options cache window, restated from `options_universe` so this module carries no second
# opinion about it. Imported rather than copied wherever the real constants are reachable.
def window() -> tuple:
    from .options_universe import ENTRY_START, ENTRY_END
    return ENTRY_START, ENTRY_END


# --------------------------------------------------------------------------- the grid ------
def universe_percentiles(panel, cols, weights, universe: set) -> dict:
    """{iso_date: {ticker: (composite, pct_within_the_OPTIONS_universe)}}.

    The percentile is computed among the optionable names ONLY — the ledger's reopen condition
    for U1, and the reason a full-panel percentile appears nowhere in this module. Inside 182
    megacaps a full-panel decile is close to a market-cap statement (U7's mechanism); ranking
    within the pool a name actually competes in is the correction.

    The composite is `composite_from_frame`, the one composite B7 left in the tree, so this is
    the same object the backtest ranks deciles with and the live screener scores. Building a
    second one here would reintroduce exactly the disagreement B7 removed.

    0.0 is the WORST composite in the cross-section and 1.0 the best, matching
    `options_veto._rank_within_universe` so the two objects can be read side by side.
    """
    from ..screener.cross_sectional import zscore
    from .fundamental_panel import composite_from_frame

    out = {}
    for d in sorted(panel["date"].unique()):
        sub = panel[panel["date"] == d]
        mask = sub["ticker"].astype(str).isin(universe)
        sub = sub[mask]
        if len(sub) < 20:
            continue
        comp = composite_from_frame(sub, cols, weights, zscore)
        tk = sub["ticker"].values
        ok = np.isfinite(comp)
        if int(ok.sum()) < 20:
            continue
        c_ok = comp[ok]
        order = np.argsort(np.argsort(c_ok))          # 0 = worst composite
        pct = order / max(1, len(c_ok) - 1)
        out[str(d)[:10]] = {str(t): (float(c), float(p))
                            for t, c, p in zip(tk[ok], c_ok, pct)}
    return out


def entry_day_after(bar_dates, rebalance: str, end: str) -> Optional[str]:
    """The first trading day **strictly after** `rebalance`, or None past `end`.

    Strictly after, not on. Entering on the rebalance date itself satisfies the U7 join's
    "most recent rebalance <= entry date" only at the boundary; stepping one day past makes the
    inequality strict with no argument to have, and costs one day of a ~45-day trade. Cheap
    conservatism on the one axis — look-ahead — that has cost this project the most.
    """
    i = bisect.bisect_right(bar_dates, rebalance)
    if i >= len(bar_dates):
        return None
    d = bar_dates[i]
    return d if d <= end else None


def grid_cells(by_date: dict, bars_by_ticker: dict, start: str, end: str) -> list:
    """Every (rebalance date, ticker) candidate entry, with its as-of composite percentile.

    A cell carries `asof` — the rebalance whose composite it uses — and `entry` — the trading day
    the option is actually bought on. They are deliberately different fields: conflating them is
    how a backward-looking join turns into an enclosing one.
    """
    cells = []
    for asof in sorted(by_date):
        if not (start <= asof <= end):
            continue
        for tk, (comp, pct) in by_date[asof].items():
            bd = bars_by_ticker.get(tk)
            if not bd:
                continue
            e = entry_day_after(bd, asof, end)
            if e is None:
                continue
            cells.append({"asof": asof, "entry": e, "ticker": tk,
                          "u1_comp": comp, "u1_pct_univ": pct})
    return cells


# ------------------------------------------------------- corporate actions (U1-SPLIT) ------
# FOUND 2026-08-11 WHILE CALIBRATING U1, BEFORE ANY ARM WAS SCORED. The ThetaData option chains
# are AS-TRADED and are not adjusted for splits; `bars` (Sharadar SEP) ARE adjusted. Nothing in
# the options lane ever consulted the split table, though `bulk.py:312` documents the hazard in
# so many words: "an unadjusted split looks [like a huge move]".
#
# The signature is a REVERSE split. GE split 1-for-8 on 2021-08-02; a $14-strike call bought
# 2021-07-23 at $0.27 settles at expiry against a ~$104 post-split underlying on a strike that
# was never re-based, and books +31,921%. That ONE row is 6.28pp of the 5,186-trade U1 grid's
# 9.93% mean. Forward splits (AAPL 4:1, NVDA 10:1, AVGO 10:1) do NOT show the same signature and
# return plausible 1.1x-2.9x figures, so this is not a blanket claim that every split is corrupt
# — it is that a trade whose contract life crosses one is not verifiable and cannot be scored.
#
# The exclusion is defined by an EXTERNAL table and a date comparison, never by the size of a
# return. A rule that dropped "implausibly large" P&L would be selecting on the outcome, which is
# the one thing a null must not let the arm do.
def load_splits(data_root: str) -> dict:
    """{ticker: [(iso_date, ratio)]} — DELEGATES to `options_backtest.load_splits`.

    One split table in the project. This used to carry its own copy; the repair moved the
    canonical implementation down to `options_backtest`, where the entry guard also lives, and
    `test_composite_entry` fails if this ever stops delegating. A project with two split tables
    ends up with two answers.
    """
    from .options_backtest import load_splits as _ls
    return _ls(data_root)


def spans_split(row, splits: dict) -> bool:
    """True if a split falls inside this trade's contract life, `(alert_ts, expiry]`.

    DELEGATES the window test to `options_backtest.split_in_window`, which is the same predicate
    the entry guard applies — so a row filtered out of a banked book here is exactly a candidate
    the guard would have refused at source. That equivalence is what lets the books be re-banked
    by filtering instead of re-mined.
    """
    from .options_backtest import split_in_window
    a = str(row.get("alert_ts") or "")[:10]
    exp = str(row.get("expiry") or "")[:10]
    if not a or not exp:
        return False
    return split_in_window(splits, str(row.get("ticker") or ""), a, exp)


def drop_split_spanners(rows, splits: dict) -> tuple:
    """(kept, dropped). Applied to the GRID, so every arm and every null draw inherits it — they
    are subsets of the grid and cannot reintroduce a row the grid does not have."""
    kept, dropped = [], []
    for r in rows:
        (dropped if spans_split(r, splits) else kept).append(r)
    return kept, dropped


# --------------------------------------------------------------------------- the arms ------
ARMS = {
    "TOP10": (0.90, 1.01),
    "TOP20": (0.80, 1.01),
    "BOT10": (-0.01, 0.10),
}


def select(rows, lo: float, hi: float) -> list:
    """Rows whose within-universe percentile is in [lo, hi). Bounds come from `ARMS`."""
    out = []
    for r in rows:
        p = r.get("u1_pct_univ")
        if p is not None and lo <= float(p) < hi:
            out.append(r)
    return out


def by_date_counts(rows) -> dict:
    """{asof: n} — the per-date shape a null draw must reproduce exactly."""
    out = {}
    for r in rows:
        out[r["asof"]] = out.get(r["asof"], 0) + 1
    return out


def mean_pnl(rows) -> Optional[float]:
    from . import options_stats as OS
    return OS.mean_pnl(rows)


def decile_table(rows, n_q: int = 10) -> list:
    """Expectancy per composite decile on the grid. Decile 1 is the BEST composite, matching
    `quantile_backtest` and `options_veto.decile_table`, so no sign flip is needed to read it
    beside them. The project has already spent one correction on reading an ordering backwards.
    """
    from . import options_stats as OS
    out = []
    have = [r for r in rows if r.get("u1_pct_univ") is not None]
    for q in range(n_q):
        lo, hi = 1.0 - (q + 1) / n_q, 1.0 - q / n_q
        sel = [r for r in have
               if (lo <= float(r["u1_pct_univ"]) < hi)
               or (q == 0 and float(r["u1_pct_univ"]) >= hi)]
        wins = [r for r in sel if OS._f(r.get("pnl_pct")) is not None
                and float(r["pnl_pct"]) > 0]
        out.append({"decile": q + 1, "pct_range": [round(lo, 3), round(hi, 3)],
                    "n_trades": len(sel), "mean_pnl_pct": OS.mean_pnl(sel),
                    "win_rate": (len(wins) / len(sel)) if sel else None})
    return out


# --------------------------------------------------------------------------- the null ------
def percentile(xs, p: float) -> float:
    """Linear-interpolated percentile. Same implementation as `scripts/tp_bar.py`, kept explicit
    rather than imported from numpy so the bar this project quotes is one readable line and a
    library default can never silently change it."""
    s = sorted(float(x) for x in xs)
    if not s:
        return float("nan")
    if len(s) == 1:
        return float(s[0])
    k = (len(s) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return float(s[lo] + (s[hi] - s[lo]) * (k - lo))


def _tier_hist(rows) -> dict:
    h = {}
    for r in rows:
        h[r.get("cap_tier")] = h.get(r.get("cap_tier"), 0) + 1
    return h


def draw_null(pool_by_date: dict, counts: dict, seed: int,
              tier_targets: Optional[dict] = None) -> list:
    """One null draw: `counts[date]` cells sampled **without replacement** from that date's pool.

    `tier_targets`, when given, is `{date: {cap_tier: n}}` — the real arm's own market-cap tier
    histogram on that date — and the draw samples within tier. **That is the size-neutralised
    null and it is the ledger's reopen condition for U1**: it makes it impossible for a selection
    rule to clear the bar by preferring a cap bucket, which is precisely how U7's veto failed.

    A tier short of cells is filled from the remaining pool and the shortfall is counted, never
    silently ignored — a matched null that quietly stops matching is worse than an unmatched one,
    because it still calls itself matched.
    """
    import random
    rnd = random.Random(seed)
    picked, shortfall = [], 0
    for d, n in counts.items():
        pool = pool_by_date.get(d) or []
        if not pool:
            continue
        if tier_targets is None:
            k = min(n, len(pool))
            picked.extend(rnd.sample(pool, k))
            continue
        want = dict(tier_targets.get(d) or {})
        by_tier = {}
        for r in pool:
            by_tier.setdefault(r.get("cap_tier"), []).append(r)
        taken, used = [], set()
        for tier, k in want.items():
            avail = [r for r in by_tier.get(tier, [])]
            take = min(k, len(avail))
            if take:
                got = rnd.sample(avail, take)
                taken.extend(got)
                used.update(id(x) for x in got)
            shortfall += (k - take)
        need = min(n, len(pool)) - len(taken)
        if need > 0:
            rest = [r for r in pool if id(r) not in used]
            if rest:
                taken.extend(rnd.sample(rest, min(need, len(rest))))
        picked.extend(taken)
    return picked, shortfall


def arm_shape(arm_rows, match_tier: bool) -> tuple:
    """(per-date counts, per-date tier histogram or None) — everything a null draw needs.

    **The shape is all the null is allowed to know about the arm.** It is fixed entirely by the
    pre-registered selection rule — how many cells the rule takes on each date, and in which cap
    tiers — and contains no P&L whatsoever. That is what makes it legitimate to compute the bar
    from the real arm's shape *before* the arm is scored: `null_gains` below is handed this tuple
    and never sees `arm_rows`, so the bar cannot be a function of the answer.
    """
    counts = by_date_counts(arm_rows)
    tier_targets = None
    if match_tier:
        tier_targets = {}
        for r in arm_rows:
            tier_targets.setdefault(r["asof"], {})
            t = r.get("cap_tier")
            tier_targets[r["asof"]][t] = tier_targets[r["asof"]].get(t, 0) + 1
    return counts, tier_targets


def null_gains(grid_rows, counts: dict, tier_targets: Optional[dict],
               n_draws: int, seed0: int) -> dict:
    """`n_draws` gains of a random selection rule of the given per-date shape, and the p95 bar.

    Takes a SHAPE, never an arm. No arm P&L is reachable from here, which is why the bar produced
    by this function can be committed before the arm is scored and the ordering can be checked
    from the commit rather than believed.
    """
    pool_by_date = {}
    for r in grid_rows:
        pool_by_date.setdefault(r["asof"], []).append(r)
    base = mean_pnl(grid_rows)
    gains, shortfalls = [], 0
    for i in range(n_draws):
        rows, sf = draw_null(pool_by_date, counts, seed0 + i, tier_targets)
        shortfalls += sf
        m = mean_pnl(rows)
        if m is not None and base is not None:
            gains.append(m - base)
    return {"n_draws": len(gains), "match_tier": bool(tier_targets is not None),
            "grid_mean_pct": base,
            "bar_pp": 100.0 * percentile(gains, 95.0) if gains else None,
            "p5_pp": 100.0 * percentile(gains, 5.0) if gains else None,
            "median_pp": 100.0 * percentile(gains, 50.0) if gains else None,
            "min_pp": 100.0 * min(gains) if gains else None,
            "max_pp": 100.0 * max(gains) if gains else None,
            "tier_shortfall_cells": shortfalls,
            "gains_pp": [100.0 * g for g in gains]}


def arm_position(gains_pp, arm_gain_pp) -> Optional[float]:
    """Where the arm sits inside an already-computed null, in percentiles.

    Reported alongside every pass/fail because a bare verdict hides the distance: an arm at the
    82nd percentile and an arm at the 4th both "fail a p95 bar" and they are not the same result.
    """
    if not gains_pp or arm_gain_pp is None:
        return None
    return 100.0 * sum(1 for g in gains_pp if g < arm_gain_pp) / len(gains_pp)
