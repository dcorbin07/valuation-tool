"""Are the LIVE factor values believable? — the correctness half of the health panel.

AUDIT MA14. `signal_coverage` and the health panel's `theme_coverage` answer PRESENCE: is the
column filled. `fundamental_panel.sanity_check` answers SANITY: are the numbers in it possible.
The second existed only on the BACKTEST side, where the input is a static licensed export that
does not drift — and did not exist on the live path, where the input is a set of vendor feeds
that drift constantly and have already broken this product twice.

THE PRECEDENT IS EXACT AND IT IS `OOB2`. Yahoo dropped one beta field, `wacc.py` substituted a
1.10 default, and MRK went from "cannot value" to a **91 Strong Buy**. Nothing was empty and
nothing raised; a plausible wrong number was served. Fail-closed covers a field that VANISHES.
Nothing covered a field that goes wrong-but-plausible, which is the failure mode a live vendor
actually produces.

WHAT THIS IS NOT. It is a DETECTOR, not a gate: it returns flags and never raises, never
withholds a row and never changes a score. A check that can kill a scan gets deleted the first
time it misfires; one that reports loudly gets read. Scoring behaviour is unchanged by design
and pinned by test.

THE BANDS ARE IMPORTED, NEVER RETYPED. `valuation/edge/sanity_spec.py` is the one definition
(MA39's pattern), so the live path and the backtest cannot drift apart into two different
opinions about what "implausible" means.

ABSENCE IS REPORTED, NOT SILENTLY SKIPPED. `sanity_check` does `if col not in panel.columns:
continue`, which is right for a backtest whose panel is built to a known schema. On a live
frame it would mean a rename or a dropped column produces ZERO checks and an empty flag list —
a clean bill of health from a check that looked at nothing. Every absent column is named in
`columns_absent`, and `checked` counts what was actually examined.
"""
from __future__ import annotations

from ..edge.sanity_spec import (SANE_RANGE_EXEMPT, SANE_RANGES, SANE_VIOLATION_SHARE,
                                SUBGROUP_PEG_PCTILE)


def _series(df, col):
    """`df[col]` as a float Series with nulls dropped, or None if the column is absent."""
    import pandas as pd
    if col not in getattr(df, "columns", []):
        return None
    return pd.to_numeric(df[col], errors="coerce").dropna()


def live_sanity(df, ranges=None, foreign_col="is_foreign") -> dict:
    """Range, sign and subgroup-pegging checks on the LIVE scored frame.

    Returns a dict shaped like `fundamental_panel.sanity_check`'s so a reader who knows one
    knows the other, plus `columns_absent` / `checked`, which the backtest version does not
    need and the live one cannot do without.
    """
    ranges = SANE_RANGES if ranges is None else ranges
    out = {"available": False, "n_rows": 0, "checked": 0, "columns_absent": [],
           "checks": {"range": {}, "sign": {}, "subgroup": {}}, "flags": []}
    if df is None or not len(df):
        out["note"] = "no scored rows"
        return out
    out["available"] = True
    out["n_rows"] = int(len(df))

    # ---- 1. sane ranges on the raw ratio levels ----
    for name, (lo, hi) in ranges.items():
        s = _series(df, name)
        if s is None:
            out["columns_absent"].append(name)
            continue
        if s.empty:
            out["columns_absent"].append(name + " (all-null)")
            continue
        out["checked"] += 1
        bad = int(((s < lo) | (s > hi)).sum())
        share = bad / float(len(s))
        out["checks"]["range"][name] = {
            "n": int(len(s)), "outside": bad, "share": share, "lo": lo, "hi": hi,
            "median": float(s.median()), "max_abs": float(s.abs().max())}
        if share > SANE_VIOLATION_SHARE:
            out["flags"].append({
                "check": "range", "factor": name, "share_outside": share, "band": [lo, hi],
                "max_abs": float(s.abs().max()),
                "detail": (f"{share:.2%} of live rows outside [{lo}, {hi}] — systematic, not a "
                           f"fat tail; this is the P7 currency signature")})

    # ---- 2. SIGN check on the range-exempt ratios (audit B18) ----
    for name in SANE_RANGE_EXEMPT:
        s = _series(df, name)
        if s is None:
            out["columns_absent"].append(name)
            continue
        if s.empty:
            out["columns_absent"].append(name + " (all-null)")
            continue
        out["checked"] += 1
        neg = int((s < 0).sum())
        out["checks"]["sign"][name] = {"n": int(len(s)), "negative": neg,
                                       "share": neg / float(len(s))}
        if neg:
            out["flags"].append({
                "check": "sign", "factor": name, "negative": neg,
                "share_negative": neg / float(len(s)),
                "detail": (f"{neg} live rows of {name} are NEGATIVE — a negative multiple "
                           f"sorts to the wrong end of the value theme once negated")})

    # ---- 3. subgroup pegging ----
    # The check that would have caught P7 on its FIRST run: "every foreign reporter sits in the
    # top 2% of book_to_price" is the currency bug's exact signature, and no range band is
    # needed to see it. Only runs when the subgroup is identifiable AND non-degenerate.
    import pandas as pd
    if foreign_col in getattr(df, "columns", []):
        flag = df[foreign_col].fillna(False).astype(bool)
        n_for = int(flag.sum())
        out["checks"]["subgroup"]["foreign"] = {"n_rows": n_for,
                                                "share_of_rows": n_for / float(len(df))}
        if 0 < n_for < len(df):
            for name in list(ranges) + list(SANE_RANGE_EXEMPT):
                if name not in getattr(df, "columns", []):
                    continue
                s = pd.to_numeric(df[name], errors="coerce")
                pct = s.rank(pct=True)
                med = pct[flag].median()
                if med != med:                       # NaN: no foreign row carries this factor
                    continue
                out["checked"] += 1
                out["checks"]["subgroup"].setdefault("median_pctile", {})[name] = float(med)
                if med >= SUBGROUP_PEG_PCTILE or med <= (1.0 - SUBGROUP_PEG_PCTILE):
                    out["flags"].append({
                        "check": "subgroup", "factor": name, "subgroup": "foreign",
                        "median_pctile": float(med),
                        "detail": (f"foreign reporters sit at the {med:.0%} percentile of "
                                   f"{name} — a subgroup should not systematically peg a "
                                   f"factor")})
    else:
        out["columns_absent"].append(foreign_col)

    # THE VACUITY DISCLOSURE. `flags: []` from `checked: 0` is not a clean bill of health, it
    # is a check that found nothing to look at — and that is precisely how a renamed column
    # would turn this guard off in silence.
    out["vacuous"] = bool(out["checked"] == 0)
    out["note"] = ("NO CHECK RAN — every named factor column is absent from the live frame; "
                   "an empty `flags` here means nothing"
                   if out["vacuous"] else
                   f"{out['checked']} checks ran over {out['n_rows']} live rows")
    return out
