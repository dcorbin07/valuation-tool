"""
EV multiples in the value theme — the A/B, on the full universe.

WHY THIS EXISTS
---------------
The growth-valuation calibration (HANDOFF_growth_calibration.md) found that a plain EV/Sales
sort out-ranks the entire blended fair-value engine, and even the `size` theme. Chasing that
lead down surfaced something the project had not noticed: `neg_ev_sales` IS already a wired
value input with a median IC of +0.0214 and an IC t of +2.11 on the full panel — the second
strongest of the six — but the value theme is BUCKET-SPLIT, and EV/Sales only ever feeds the
SPECULATIVE branch. It has never scored a single profitable company. `ev_ebitda` was not
computed by the panel at all.

So the question is not "is EV/Sales a real signal" (it is, and it is already measured). It is
"does extending it — and EV/EBITDA — to the ESTABLISHED branch make the composite better".
That is what `CONFIG.value_ev_multiples` toggles and what this module measures.

WHAT IT DOES
------------
Reads a panel built with keep_numbers=True (dumped by a normal backtest via EDGE_PANEL_PICKLE)
and reconstructs the WITH arm from the stored z-columns. That reconstruction is EXACT, not an
approximation: the flag only changes which z-columns get averaged into `value`, and
standardization happens strictly before the composite, so every z-column is identical across
arms. `test_value_is_recomputable_from_the_stored_z_columns` pins exactly this, and the two
independent full CLI runs in HANDOFF_growth_evsales.md confirm it end to end.

It then reports, in the order the project's rules demand:
  1. COVERAGE FIRST — including per-bucket, because a signal can be 96% covered overall and
     still never reach the branch that would use it. That is precisely the situation here.
  2. Per-number IC, overall and WITHIN the established branch only (the rows the change can
     actually touch).
  3. CORRELATION against the incumbent value inputs, and the INCREMENTAL test: residualize the
     candidate on the four incumbents cross-sectionally and measure whether what is LEFT still
     predicts. A signal that is merely a repackaging of book/earnings/FCF yields has a dead
     residual; a signal carrying new information does not.
  4. Theme- and composite-level A/B (value IC, long-short t, top-decile alpha, monotonicity).
  5. HELD-OUT BOTH DIRECTIONS, against the SAME pre-specified margins the theme-zeroing gate
     uses (MIN_HOLDOUT_ALPHA_GAIN / MIN_HOLDOUT_TSTAT_GAIN). Those margins were committed
     before P6 and are not re-chosen here.

Run:
    python -m valuation.studies.ev_multiples_study --panel <panel.pkl> --json <out.json>
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from ..screener import settings as S
from ..edge.fundamental_panel import (
    MIN_HOLDOUT_ALPHA_GAIN,
    MIN_HOLDOUT_TSTAT_GAIN,
    _spearman,
    quantile_backtest,
    theme_ic,
)

# The incumbent established-branch value inputs, and the two candidates.
INCUMBENT = ["z_earnings_yield", "z_fcf_yield", "z_ebit_ev", "z_book_to_price"]
CANDIDATES = ["z_neg_ev_sales", "z_neg_ev_ebitda"]
VALUE_Z = INCUMBENT + CANDIDATES + ["z_neg_ps"]

MIN_NAMES = 20          # names per date before a cross-section is worth a correlation/IC
MIN_DATES = 8


# --------------------------------------------------------------------------- #
#  arm reconstruction
# --------------------------------------------------------------------------- #
def with_value(panel: pd.DataFrame) -> pd.Series:
    """The `value` column as it would be WITH the flag on.

    Only established rows change: the speculative branch already carried EV/Sales and is
    deliberately untouched. Returns a new Series; the panel is not mutated.
    """
    out = panel["value"].astype(float).copy()
    est = panel["bucket"].eq("established")
    cols = [c for c in INCUMBENT + CANDIDATES if c in panel.columns]
    out.loc[est] = panel.loc[est, cols].mean(axis=1)
    return out


def _arms(panel: pd.DataFrame):
    """(without_panel, with_panel) — identical except for the `value` column."""
    a = panel.copy()
    b = panel.copy()
    b["value"] = with_value(panel)
    return a, b


# --------------------------------------------------------------------------- #
#  1. coverage  (the rule: check this BEFORE trusting any IC)
# --------------------------------------------------------------------------- #
def coverage(panel: pd.DataFrame) -> dict:
    out = {"rows": int(len(panel)), "dates": int(panel["date"].nunique()),
           "names": int(panel["ticker"].nunique()), "overall": {}, "by_bucket": {}}
    est = panel["bucket"].eq("established")
    out["established_rows"] = int(est.sum())
    out["speculative_rows"] = int((~est).sum())
    for c in VALUE_Z:
        if c not in panel.columns:
            out["overall"][c] = None
            continue
        out["overall"][c] = round(float(panel[c].notna().mean()), 4)
        out["by_bucket"][c] = {
            "established": round(float(panel.loc[est, c].notna().mean()), 4) if est.any() else None,
            "speculative": round(float(panel.loc[~est, c].notna().mean()), 4) if (~est).any() else None,
        }
    # The headline of this whole study: how many rows the change can actually reach.
    if "z_neg_ev_sales" in panel.columns:
        reach = est & panel["z_neg_ev_sales"].notna()
        out["rows_ev_sales_newly_scores"] = int(reach.sum())
        out["share_of_panel_newly_scored"] = round(float(reach.mean()), 4)
    return out


# --------------------------------------------------------------------------- #
#  2. per-number IC, overall and inside the established branch
# --------------------------------------------------------------------------- #
def _ic_stats(sub: pd.DataFrame, col: str, ret="fwd_ret") -> dict:
    ics = []
    for _d, g in sub.groupby("date"):
        ss = g.dropna(subset=[col, ret])
        if len(ss) >= MIN_NAMES:
            ic = _spearman(ss[col].values, ss[ret].values)
            if ic == ic:
                ics.append(ic)
    if len(ics) < MIN_DATES:
        return {"median_ic": None, "ic_tstat": None, "n_dates": len(ics)}
    a = np.asarray(ics, dtype=float)
    sd = float(a.std(ddof=1))
    return {"median_ic": round(float(np.median(a)), 5),
            "ic_tstat": round(float(a.mean() / (sd / len(a) ** 0.5)), 3) if sd > 0 else 0.0,
            "n_dates": len(a)}


def number_ic(panel: pd.DataFrame) -> dict:
    est = panel[panel["bucket"].eq("established")]
    out = {}
    for c in VALUE_Z:
        if c not in panel.columns:
            continue
        out[c] = {"all_rows": _ic_stats(panel, c), "established_only": _ic_stats(est, c)}
    return out


# --------------------------------------------------------------------------- #
#  3. correlation + the incremental (residualized) test
# --------------------------------------------------------------------------- #
def correlations(panel: pd.DataFrame) -> dict:
    """Mean per-date Spearman correlation between the value inputs, established rows only.

    Per-date rather than pooled: a pooled correlation blends cross-sectional structure with
    drift in the level over 18 years and can read high for two signals that never actually
    agree within a single cross-section.
    """
    est = panel[panel["bucket"].eq("established")]
    cols = [c for c in VALUE_Z if c in est.columns]
    acc = {}
    for _d, g in est.groupby("date"):
        for i, a in enumerate(cols):
            for b in cols[i + 1:]:
                ss = g.dropna(subset=[a, b])
                if len(ss) >= MIN_NAMES:
                    r = _spearman(ss[a].values, ss[b].values)
                    if r == r:
                        acc.setdefault((a, b), []).append(r)
    return {f"{a}|{b}": round(float(np.mean(v)), 4)
            for (a, b), v in sorted(acc.items()) if len(v) >= MIN_DATES}


def incremental(panel: pd.DataFrame) -> dict:
    """Does the candidate still predict once the incumbents are projected out?

    Cross-sectionally, per date, regress the candidate on the four incumbent z-scores (with an
    intercept) and keep the residual — the part of EV/Sales that book/earnings/FCF cheapness
    cannot explain. Then measure that residual's IC exactly like any other signal.

    Reading it: a residual IC near zero with a raw IC that was strong means the candidate is a
    repackaging of what the theme already had. A residual IC that survives means it carries
    information the incumbents do not, which is the only thing that justifies a new input.
    """
    est = panel[panel["bucket"].eq("established")]
    inc = [c for c in INCUMBENT if c in est.columns]
    out = {}
    for cand in CANDIDATES:
        if cand not in est.columns:
            continue
        rows = []
        r2s = []
        for d, g in est.groupby("date"):
            ss = g.dropna(subset=[cand, "fwd_ret"] + inc)
            if len(ss) < MIN_NAMES:
                continue
            X = np.column_stack([np.ones(len(ss))] + [ss[c].values for c in inc])
            y = ss[cand].values.astype(float)
            try:
                beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            except np.linalg.LinAlgError:
                continue
            resid = y - X @ beta
            var = float(np.var(y))
            if var > 0:
                r2s.append(1.0 - float(np.var(resid)) / var)
            rows.append(pd.DataFrame({"date": d, "resid": resid,
                                      "fwd_ret": ss["fwd_ret"].values}))
        if not rows:
            continue
        rp = pd.concat(rows, ignore_index=True)
        out[cand] = {
            "raw_ic": _ic_stats(est, cand),
            "residual_ic": _ic_stats(rp, "resid"),
            # How much of the candidate the incumbents already explain. High R^2 + dead
            # residual = duplicate. Low R^2 = it was largely orthogonal all along.
            "mean_r2_explained_by_incumbents": round(float(np.mean(r2s)), 4) if r2s else None,
        }
    return out


# --------------------------------------------------------------------------- #
#  4 + 5. composite A/B, and the held-out gate
# --------------------------------------------------------------------------- #
def _weights(cols, scheme="live"):
    """`live` = the shipped WEIGHTS_ESTABLISHED, which zero low_risk and sentiment.

    Equal-weighting every column instead would silently hand low_risk back 1/8 of the book —
    a theme P5 deliberately zeroed after confirming it out-of-sample. The project's
    theme-zeroing gate equal-weights on purpose (it is asking "this theme in vs out"), but the
    question here is whether a change helps the book Don actually runs, so `live` is primary
    and `equal` is reported alongside it as a robustness check.
    """
    if scheme == "equal":
        return {c: 1.0 / len(cols) for c in cols}
    w = {c: float(S.WEIGHTS_ESTABLISHED.get(c, 0.0)) for c in cols}
    return w if sum(w.values()) > 0 else {c: 1.0 / len(cols) for c in cols}


def _qb(panel, cols, n_q=10, horizon=63, scheme="live") -> dict:
    r = quantile_backtest(panel, cols, _weights(cols, scheme), n_q=n_q, horizon=horizon) or {}
    return {k: r.get(k) for k in ("long_short_tstat", "long_short_ann",
                                  "top_decile_alpha", "monotonicity")}


def composite_ab(panel: pd.DataFrame, horizon=63) -> dict:
    """Theme IC and equal-weight composite performance, WITHOUT vs WITH."""
    a, b = _arms(panel)
    cols = [c for c in S.BUCKET_FACTORS["established"]
            if c in panel.columns and panel[c].notna().any()]
    out = {"cols": cols, "horizon": horizon}
    for name, p in (("without", a), ("with", b)):
        ti = theme_ic(p).get("value") or {}
        out[name] = {
            "value_theme": {"median_ic": ti.get("median_ic"), "ic_tstat": ti.get("ic_tstat"),
                            "coverage": ti.get("coverage"), "n_dates": ti.get("n_dates")},
            "composite": _qb(p, cols, horizon=horizon, scheme="live"),
            "composite_equal_weight": _qb(p, cols, horizon=horizon, scheme="equal"),
        }
    return out


def holdout_ab(panel: pd.DataFrame, horizon=63, n_q=10, min_dates=16) -> dict:
    """Both split directions, judged against the pre-specified margins.

    Same protocol as holdout_theme_validate: split the dates by time, EMBARGO the boundary
    date (with rebalance == horizon it is the only forward window that can straddle the
    split), measure on the half that did not inform anything, and run it both ways. The
    difference is what is being compared — two DEFINITIONS of the value theme rather than a
    theme in vs out.

    There is no "decide" step here, so this is a cleaner test than the theme-zeroing one: the
    change under test was not selected by looking at this panel's composite at all. It came
    from a separate study of the fair-value gap. Both halves are therefore honest measurements
    — which is also why agreement across the two directions is the whole point.
    """
    out = {"min_alpha_gain": MIN_HOLDOUT_ALPHA_GAIN, "min_tstat_gain": MIN_HOLDOUT_TSTAT_GAIN,
           "splits": {}}
    dates = sorted(panel["date"].unique())
    if len(dates) < min_dates:
        return {**out, "status": f"only {len(dates)} dates, need {min_dates}"}
    mid = len(dates) // 2
    out["boundary_date_embargoed"] = str(dates[mid])
    cols = [c for c in S.BUCKET_FACTORS["established"]
            if c in panel.columns and panel[c].notna().any()]
    halves = {"early_half": dates[:mid], "late_half": dates[mid + 1:]}

    passed = []
    for name, ds in halves.items():
        sub = panel[panel["date"].isin(ds)]
        a, b = _arms(sub)
        wo = _qb(a, cols, n_q=n_q, horizon=horizon, scheme="live")
        wi = _qb(b, cols, n_q=n_q, horizon=horizon, scheme="live")
        d_t = (None if wi["long_short_tstat"] is None or wo["long_short_tstat"] is None
               else round(wi["long_short_tstat"] - wo["long_short_tstat"], 3))
        d_a = (None if wi["top_decile_alpha"] is None or wo["top_decile_alpha"] is None
               else round(wi["top_decile_alpha"] - wo["top_decile_alpha"], 5))
        ok = (d_t is not None and d_a is not None
              and d_t >= MIN_HOLDOUT_TSTAT_GAIN and d_a >= MIN_HOLDOUT_ALPHA_GAIN)
        passed.append(bool(ok))
        out["splits"][name] = {"dates": len(ds), "without": wo, "with": wi,
                               "delta_long_short_tstat": d_t, "delta_top_decile_alpha": d_a,
                               "clears_margin": bool(ok)}
    out["both_directions_clear"] = all(passed) and len(passed) == 2
    out["verdict"] = "confirmed" if out["both_directions_clear"] else "not_replicated"
    return out


# --------------------------------------------------------------------------- #
#  driver
# --------------------------------------------------------------------------- #
def run_study(panel: pd.DataFrame, horizon=63) -> dict:
    if "bucket" not in panel.columns:
        return {"status": "panel has no `bucket` column — rebuild it with the current code"}
    return {
        "coverage": coverage(panel),
        "number_ic": number_ic(panel),
        "correlations": correlations(panel),
        "incremental": incremental(panel),
        "composite_ab": composite_ab(panel, horizon=horizon),
        "holdout_ab": holdout_ab(panel, horizon=horizon),
    }


def _pct(x, p="+.2%"):
    return "n/a" if x is None else format(x, p)


def _report(res: dict) -> None:
    cov = res["coverage"]
    print("\n=== EV multiples in the value theme — full-universe A/B ===")
    print(f"  panel: {cov['rows']:,} rows / {cov['names']:,} names / {cov['dates']} dates "
          f"({cov['established_rows']:,} established, {cov['speculative_rows']:,} speculative)")

    print("\n--- 1. COVERAGE (checked before any IC) ---")
    print(f"  {'signal':<20} {'overall':>8} {'establ.':>8} {'specul.':>8}")
    for c, v in cov["overall"].items():
        bb = cov["by_bucket"].get(c) or {}
        print(f"  {c:<20} {_pct(v, '.1%'):>8} {_pct(bb.get('established'), '.1%'):>8} "
              f"{_pct(bb.get('speculative'), '.1%'):>8}")
    if "share_of_panel_newly_scored" in cov:
        print(f"  -> EV/Sales newly scores {cov['rows_ev_sales_newly_scores']:,} rows "
              f"({cov['share_of_panel_newly_scored']:.1%} of the panel) that it never touched before")

    print("\n--- 2. PER-NUMBER IC ---")
    print(f"  {'signal':<20} {'all medIC':>10} {'all t':>7} {'est medIC':>10} {'est t':>7}")
    for c, v in res["number_ic"].items():
        a, e = v["all_rows"], v["established_only"]
        print(f"  {c:<20} {_pct(a['median_ic'], '+.4f'):>10} {_pct(a['ic_tstat'], '+.2f'):>7} "
              f"{_pct(e['median_ic'], '+.4f'):>10} {_pct(e['ic_tstat'], '+.2f'):>7}")

    print("\n--- 3a. CORRELATION with the incumbents (established rows, mean per-date Spearman) ---")
    for k, v in res["correlations"].items():
        a, b = k.split("|")
        if a in CANDIDATES or b in CANDIDATES:
            print(f"  {a:<20} vs {b:<20} {v:+.3f}")

    print("\n--- 3b. INCREMENTAL: does anything survive projecting out the incumbents? ---")
    for c, v in res["incremental"].items():
        raw, rsd = v["raw_ic"], v["residual_ic"]
        print(f"  {c}")
        print(f"      raw       medIC {_pct(raw['median_ic'], '+.4f')}  t {_pct(raw['ic_tstat'], '+.2f')}")
        print(f"      residual  medIC {_pct(rsd['median_ic'], '+.4f')}  t {_pct(rsd['ic_tstat'], '+.2f')}"
              f"   (incumbents explain R^2 {_pct(v['mean_r2_explained_by_incumbents'], '.1%')})")

    ab = res["composite_ab"]
    print("\n--- 4. A/B on the full panel ---")
    print(f"  {'':<22} {'WITHOUT':>12} {'WITH':>12}")
    wo, wi = ab["without"], ab["with"]
    for lbl, key, fmt in (("value theme medIC", "median_ic", "+.4f"), ("value theme IC t", "ic_tstat", "+.3f")):
        print(f"  {lbl:<22} {_pct(wo['value_theme'][key], fmt):>12} {_pct(wi['value_theme'][key], fmt):>12}")
    print("  -- live weights (WEIGHTS_ESTABLISHED; low_risk & sentiment at 0) --")
    for lbl, key, fmt in (("long-short t", "long_short_tstat", "+.3f"),
                          ("long-short /yr", "long_short_ann", "+.2%"),
                          ("top-decile alpha", "top_decile_alpha", "+.2%"),
                          ("monotonicity", "monotonicity", "+.3f")):
        print(f"  {lbl:<22} {_pct(wo['composite'][key], fmt):>12} {_pct(wi['composite'][key], fmt):>12}")
    print("  -- equal weights (robustness check) --")
    for lbl, key, fmt in (("long-short t", "long_short_tstat", "+.3f"),
                          ("top-decile alpha", "top_decile_alpha", "+.2%")):
        print(f"  {lbl:<22} {_pct(wo['composite_equal_weight'][key], fmt):>12} "
              f"{_pct(wi['composite_equal_weight'][key], fmt):>12}")

    ho = res["holdout_ab"]
    print("\n--- 5. HELD-OUT, both directions "
          f"(bar: dt >= +{ho['min_tstat_gain']}, dalpha >= +{ho['min_alpha_gain']:.0%}) ---")
    if ho.get("status"):
        print(f"  {ho['status']}")
    else:
        for name, s in ho["splits"].items():
            print(f"  {name:<12} ({s['dates']} dates)  dt {_pct(s['delta_long_short_tstat'], '+.3f')}   "
                  f"dalpha {_pct(s['delta_top_decile_alpha'], '+.2%')}   "
                  f"{'CLEARS' if s['clears_margin'] else 'does not clear'}")
        print(f"\n  VERDICT: {ho['verdict'].upper()}")


def main(argv=None):
    import argparse
    import sys
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="EV multiples in the value theme — full-universe A/B.")
    ap.add_argument("--panel", required=True, help="pickle dumped via EDGE_PANEL_PICKLE")
    ap.add_argument("--json", default=None)
    ap.add_argument("--horizon", type=int, default=63)
    args = ap.parse_args(argv)

    panel = pd.read_pickle(args.panel)
    res = run_study(panel, horizon=args.horizon)
    if res.get("status"):
        print(res["status"])
        return 1
    _report(res)
    if args.json:
        with open(args.json, "w") as f:
            json.dump(res, f, indent=2, default=str)
        print(f"\nFull results -> {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
