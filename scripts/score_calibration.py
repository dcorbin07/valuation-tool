#!/usr/bin/env python3
"""score_calibration.py — what does the LIVE hot score look like when nothing agrees?  [V3]

X7 pointed a placebo at the research pipeline and turned four conventions into measured floors.
This points the same idea at the PRODUCT. The hot score is a percentile rank of a composite, and
a high composite asserts something specific to a reader: *this name is strong across several
themes at once*. That assertion has never been measured against what chance produces.

THE QUESTION. If every theme number were exactly as it is, but their co-occurrence within a single
name were pure chance, how good would the top of the book still look?

TWO PERMUTATIONS, AND ONLY ONE OF THEM IS THE INSTRUMENT.

  H1 (PRIMARY) — coverage-preserving, within-column. For each (date, bucket) group and each theme
    column INDEPENDENTLY, permute the observed values among the rows that have them; leave every
    NaN exactly where it is. Preserved: each theme's marginal distribution within the bucket, its
    coverage, and each ROW's coverage pattern — hence its renormalization denominator. Destroyed:
    cross-theme agreement within a name, and nothing else. Because the denominator is identical
    between real and null, a difference in the composite distribution is attributable to agreement
    alone rather than to a name being scored on fewer themes.

  H0 (CONTROL) — X7's own scheme: the whole row's theme vector shuffled together. Registered with
    the prediction that it is a NEAR NO-OP on the composite distribution, because a row's theme
    vector and its denominator both travel intact and only the ticker label changes. It is run to
    make that explicit and measured rather than asserted: X7's permutation was built for
    return-based statistics, and a score is not one. If H0 moves the composite distribution
    materially, this is a HARNESS FAILURE and no calibration may be quoted from the run.

WHAT IS SCORED. `attribution.decompose` — the live scorer — with the deployed weights, imported
read-only. Nothing under `valuation/` is edited by this item.

LIMITATION, STATED BY THE OUTPUT ITSELF. The panel carries no `value_est` / `value_spec` /
`op_margin`, so `decompose` takes its documented hard-bucket branch rather than the soft blend.
The deployed weights, within-bucket standardization and present-weight renormalization ARE the
live ones; the soft blend of the two `value` branches is not exercised. Real and null are scored
by the identical call, so this is a caveat on transfer to the live book, not on the comparison.

Pre-registered in PREREG_v3_score_calibration.md, committed blind at 251c989. Thresholds are NOT
restated from results.

    python -m scripts.score_calibration --panel <panel.pkl> --out data/free_analysis/SCORE_CALIBRATION.json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time

import numpy as np
import pandas as pd

from valuation.screener import settings as S
from valuation.screener.attribution import decompose
from valuation.screener.cross_sectional import standardize_factors

# The rank ladder. 184 is the top-decile boundary of the 1,842-name primary cross-section and is
# appended per-date at runtime, so a date with a different cross-section still reports its own
# decile edge rather than a borrowed one.
LADDER = [1, 2, 3, 5, 10, 15, 20, 25, 50, 100]
PRIMARY_RANK = 10          # the pre-registered primary statistic
SEED0 = 3000


# --------------------------------------------------------------------------- permutations

def _bucket_positions(cs: pd.DataFrame) -> dict:
    """Positional row indices per bucket. Positional, not label-based: the permutations below
    write through numpy, and `.loc[idx, col] = array` would realign on the index and silently
    undo the shuffle."""
    b = cs["bucket"].astype(object).values
    return {name: np.where(b == name)[0] for name in pd.unique(b)}


def permute_within_column(cs: pd.DataFrame, cols, groups, rng) -> pd.DataFrame:
    """H1 — the instrument. Per column, per bucket, observed values only; NaNs stay put."""
    out = cs.copy()
    arrs = {c: out[c].to_numpy(dtype=float, copy=True) for c in cols}
    for idx in groups.values():
        for c in cols:
            a = arrs[c]
            sel = idx[~np.isnan(a[idx])]
            if sel.size < 2:
                continue
            vals = a[sel]
            a[sel] = vals[rng.permutation(sel.size)]
    for c in cols:
        out[c] = arrs[c]
    return out


def permute_block(cs: pd.DataFrame, cols, groups, rng) -> pd.DataFrame:
    """H0 — the control. X7's scheme: the whole theme vector travels together."""
    out = cs.copy()
    mat = out[cols].to_numpy(dtype=float, copy=True)
    for idx in groups.values():
        if idx.size < 2:
            continue
        mat[idx] = mat[idx][rng.permutation(idx.size)]
    for j, c in enumerate(cols):
        out[c] = mat[:, j]
    return out


SCHEMES = {"within_column": permute_within_column, "block": permute_block}


# --------------------------------------------------------------------------- the statistic

def _present_weight_fraction(cs: pd.DataFrame) -> pd.Series:
    """Per row: the share of its bucket's total weight that is actually scored on it.

    This is `_branch`'s `denom` divided by the full weight mass — the exact quantity that makes a
    thinly covered name's composite noisier than a fully covered one, since the composite is an
    average over whatever survives. Computed through `standardize_factors` rather than a raw
    notna() because that is what `_branch` itself tests: a present-but-constant column z-scores to
    all-NaN and carries no weight.
    """
    out = pd.Series(np.nan, index=cs.index, dtype=float)
    for name, w in (("established", S.WEIGHTS_ESTABLISHED), ("speculative", S.WEIGHTS_SPECULATIVE)):
        sub = cs[cs["bucket"] == name]
        if sub.empty:
            continue
        src = sub if len(sub) >= 5 else cs          # mirrors `decompose`'s small-bucket fallback
        cols = list(w.keys())
        z = standardize_factors(src, cols).reindex(index=sub.index)
        wser = pd.Series(w, dtype=float)
        total = float(wser.sum()) or np.nan
        out.loc[sub.index] = (z[cols].notna().astype(float) * wser).sum(axis=1) / total
    return out


def statistic(cs: pd.DataFrame, ladder, decile_n: int) -> dict:
    """One scored cross-section -> the pre-registered numbers."""
    comp, contrib = decompose(cs, S.WEIGHTS_ESTABLISHED, S.WEIGHTS_SPECULATIVE, soft=True)
    s = comp.dropna().sort_values(ascending=False)
    rec = {f"c_at_{k}": (float(s.iloc[k - 1]) if len(s) >= k else None) for k in ladder}

    top = s.index[:decile_n]
    rec["top_decile_mean"] = float(s.iloc[:decile_n].mean()) if len(s) else None
    rec["composite_sd"] = float(s.std(ddof=1)) if len(s) > 1 else None
    rec["n_scored"] = int(len(s))

    # Computed ONCE and sliced. It was computed twice in the first cut — same answer, but it
    # dominated the per-draw cost and would have turned the registered sweep into a three-hour
    # run for no extra information.
    pwf = _present_weight_fraction(cs)
    pw = pwf.reindex(top)
    rec["top_decile_present_weight"] = float(pw.mean()) if pw.notna().any() else None
    rec["universe_present_weight"] = float(pwf.mean())

    # Composition: of everything that pushed a top-decile name, what share was each theme.
    sub = contrib.reindex(index=top).abs()
    tot = sub.sum(axis=1).replace(0, np.nan)
    rec["top_decile_composition"] = {
        c: (float(v) if v == v else None) for c, v in sub.div(tot, axis=0).mean().items()}
    return rec


# --------------------------------------------------------------------------- the sweep

def run_date(cs: pd.DataFrame, scheme: str, n: int, ladder, decile_n: int,
             seed0: int = SEED0, log=None) -> tuple:
    """(real, draws) for one cross-section under one permutation scheme.

    The real cross-section is measured through the IDENTICAL `statistic` call before any draw is
    taken, so a gap between this harness and the shipped scorer shows up as a harness bug rather
    than being read as a finding. That is X7's discipline and it is the reason its floors survived
    two re-runs.
    """
    cols = [c for c in S.FACTORS_ALL if c in cs.columns]
    groups = _bucket_positions(cs)
    fn = SCHEMES[scheme]

    real = statistic(cs, ladder, decile_n)
    draws = []
    for k in range(n):
        seed = seed0 + k
        rng = np.random.default_rng(seed)
        d = statistic(fn(cs, cols, groups, rng), ladder, decile_n)
        d["seed"] = seed
        draws.append(d)
        if log and (k + 1) % 50 == 0:
            print(f"    {log} {k + 1}/{n}", flush=True)
    return real, draws


def _pct(vals, p):
    v = [float(x) for x in vals if x is not None and x == x]
    return float(np.percentile(v, p)) if len(v) >= 2 else None


def calibrate(real: dict, draws: list, ladder) -> dict:
    """The deliverable table: per rank, what noise reaches and how often it beats the real book."""
    n = len(draws)
    table = {}
    for k in ladder:
        key = f"c_at_{k}"
        vals = [d.get(key) for d in draws]
        clean = [float(x) for x in vals if x is not None and x == x]
        r = real.get(key)
        ge = sum(1 for x in clean if r is not None and x >= r)
        table[k] = {
            "real": r,
            "noise_p50": _pct(vals, 50), "noise_p90": _pct(vals, 90),
            "noise_p95": _pct(vals, 95), "noise_p99": _pct(vals, 99),
            "noise_max": (max(clean) if clean else None),
            "noise_mean": (float(np.mean(clean)) if clean else None),
            "noise_sd": (float(np.std(clean, ddof=1)) if len(clean) > 1 else None),
            "n_noise_ge_real": ge,
            # Empirical p with the draws banked, so a later re-read needs no re-run.
            "empirical_p": (ge / n if n else None),
            "clears_p95": (bool(r is not None and _pct(vals, 95) is not None
                                and r >= _pct(vals, 95))),
        }
    return table


def _sentence(k: int, row: dict) -> str:
    """One plain sentence per rank band, written for the product, not for the log."""
    r, p95, p = row.get("real"), row.get("noise_p95"), row.get("empirical_p")
    if r is None or p95 is None or p is None:
        return f"Rank #{k}: not measurable on this cross-section."
    if row["clears_p95"]:
        pct = max(p, 1.0 / 500) * 100
        return (f"The #{k} name scores {r:.3f}. Fewer than {pct:.1f}% of universes with no "
                f"cross-theme agreement reach that at rank {k} (noise gets to {p95:.3f}).")
    return (f"The #{k} name scores {r:.3f}, which {p * 100:.0f}% of no-agreement universes match "
            f"or beat at rank {k} (noise reaches {p95:.3f}). At this rank the score is not "
            f"distinguishable from chance.")


# --------------------------------------------------------------------------- entry point

def main(argv=None):
    ap = argparse.ArgumentParser(description="V3 — noise-calibrated hot score.")
    ap.add_argument("--panel", required=True)
    ap.add_argument("--out", default="data/free_analysis/SCORE_CALIBRATION.json")
    ap.add_argument("--n-primary", type=int, default=500)
    ap.add_argument("--n-robust", type=int, default=100)
    ap.add_argument("--seed0", type=int, default=SEED0)
    ap.add_argument("--max-dates", type=int, default=0, help="0 = every date (robustness arm)")
    args = ap.parse_args(argv)

    panel = pd.read_pickle(args.panel)
    dates = sorted(panel["date"].unique())
    primary_date = dates[-1]
    cs0 = panel[panel["date"] == primary_date].copy().set_index("ticker")
    decile0 = max(1, len(cs0) // 10)
    ladder0 = sorted(set(LADDER + [decile0]))

    print(f"[v3] panel {len(panel):,} rows · {len(dates)} dates · primary {primary_date} "
          f"n={len(cs0)} · decile edge #{decile0}", flush=True)

    out = {
        "test": "V3 — noise-calibrated hot score",
        "prereg": "PREREG_v3_score_calibration.md (committed blind at 251c989)",
        "scorer": "valuation.screener.attribution.decompose (LIVE path, read-only import)",
        "weights": {"established": S.WEIGHTS_ESTABLISHED, "speculative": S.WEIGHTS_SPECULATIVE},
        "panel": args.panel,
        "primary_date": str(primary_date),
        "primary_n_names": int(len(cs0)),
        "decile_edge_rank": int(decile0),
        "ladder": ladder0,
        "seeds": f"{args.seed0}..{args.seed0 + args.n_primary - 1}",
        "limitation": (
            "The panel carries no value_est/value_spec/op_margin, so `decompose` takes its "
            "documented HARD-bucket branch rather than the soft blend. Deployed weights, "
            "within-bucket standardization and present-weight renormalization are the live ones; "
            "the soft blend of the two value branches is not exercised. Real and null are scored "
            "by the identical call, so this is a caveat on transfer to the live book, not on the "
            "comparison."),
        "trial_cost": "ZERO — a calibration searches nothing (session-10 precedent). Equity N unchanged.",
    }

    all_draws = []      # flat rows for the CSV — RUN_RULES A9

    # ---- primary cross-section, both schemes -------------------------------------------------
    for scheme in ("within_column", "block"):
        t0 = time.time()
        print(f"[v3] primary · {scheme} · {args.n_primary} draws", flush=True)
        real, draws = run_date(cs0, scheme, args.n_primary, ladder0, decile0,
                               args.seed0, log=scheme)
        out[f"primary_{scheme}"] = {
            "real": real,
            "n_draws": len(draws),
            "table": calibrate(real, draws, ladder0),
            "null_top_decile_mean": {
                "p50": _pct([d["top_decile_mean"] for d in draws], 50),
                "p95": _pct([d["top_decile_mean"] for d in draws], 95),
                "max": max(d["top_decile_mean"] for d in draws),
            },
            "null_composite_sd": {
                "p50": _pct([d["composite_sd"] for d in draws], 50),
                "p95": _pct([d["composite_sd"] for d in draws], 95),
            },
            "null_top_decile_present_weight_p50":
                _pct([d["top_decile_present_weight"] for d in draws], 50),
            "null_top_decile_composition": {
                c: _pct([d["top_decile_composition"].get(c) for d in draws], 50)
                for c in (real.get("top_decile_composition") or {})},
        }
        for d in draws:
            all_draws.append({"arm": scheme, "date": str(primary_date), **
                              {k: v for k, v in d.items() if k != "top_decile_composition"}})
        print(f"[v3]   {scheme} done in {time.time() - t0:.0f}s", flush=True)
        _write(args.out, out, all_draws)

    # The control's verdict, computed rather than asserted.
    pr = out["primary_within_column"]["real"]
    ctl = out["primary_block"]
    ctl_sd = ctl["null_composite_sd"]["p50"]
    real_sd = pr["composite_sd"]
    out["control_check"] = {
        "prediction": "H0 (block) is a near no-op on the composite distribution.",
        "real_composite_sd": real_sd,
        "block_null_composite_sd_p50": ctl_sd,
        "ratio": (ctl_sd / real_sd if (ctl_sd and real_sd) else None),
        # A material move is a harness failure per the pre-registration. 5% of the real sd is the
        # line; it is generous, and the point is to catch a scheme that is secretly informative.
        "harness_ok": bool(ctl_sd and real_sd and abs(ctl_sd / real_sd - 1.0) < 0.05),
    }

    # ---- robustness: every date, H1 only ------------------------------------------------------
    rob_dates = dates if not args.max_dates else dates[-args.max_dates:]
    print(f"[v3] robustness · {len(rob_dates)} dates × {args.n_robust} draws", flush=True)
    per_date = []
    for i, d in enumerate(rob_dates, 1):
        cs = panel[panel["date"] == d].copy().set_index("ticker")
        if len(cs) < 50:
            per_date.append({"date": str(d), "n": int(len(cs)), "skipped": "cross-section under 50 names"})
            continue
        dec = max(1, len(cs) // 10)
        lad = sorted(set(LADDER + [dec]))
        real, draws = run_date(cs, "within_column", args.n_robust, lad, dec, args.seed0)
        tab = calibrate(real, draws, lad)
        row = tab.get(PRIMARY_RANK, {})
        per_date.append({
            "date": str(d), "n": int(len(cs)), "decile_edge_rank": int(dec),
            "real_at_primary_rank": row.get("real"),
            "noise_p95_at_primary_rank": row.get("noise_p95"),
            "empirical_p": row.get("empirical_p"),
            "clears_p95": row.get("clears_p95"),
            "real_top_decile_mean": real.get("top_decile_mean"),
            "noise_top_decile_mean_p95": _pct([x["top_decile_mean"] for x in draws], 95),
            "real_composite_sd": real.get("composite_sd"),
            "noise_composite_sd_p50": _pct([x["composite_sd"] for x in draws], 50),
        })
        for x in draws:
            all_draws.append({"arm": "within_column_robust", "date": str(d), **
                              {k: v for k, v in x.items() if k != "top_decile_composition"}})
        print(f"[v3]   {i}/{len(rob_dates)} {d} n={len(cs)} "
              f"clears_p95={row.get('clears_p95')} p={row.get('empirical_p')}", flush=True)
        _write(args.out, out, all_draws)

    scored = [r for r in per_date if r.get("clears_p95") is not None]
    n_clear = sum(1 for r in scored if r["clears_p95"])
    out["robustness"] = {
        "per_date": per_date,
        "n_dates_scored": len(scored),
        "n_dates_clearing_p95": n_clear,
        "fraction_clearing": (n_clear / len(scored) if scored else None),
        # The pre-registered generality gate: >= 42 of 69.
        "generality_gate": "clears on >= 42 of 69 dates (60%)",
        "generality_met": bool(len(scored) and n_clear >= 42),
    }

    # ---- the pre-registered verdict -----------------------------------------------------------
    prow = out["primary_within_column"]["table"].get(PRIMARY_RANK, {})
    # PREREG §7 states the bar as "real >= the H1 noise p95 (empirical p <= 0.05)". Those two
    # readings are the same quantity asymptotically but can disagree at the boundary, because a
    # percentile is interpolated between order statistics while the empirical p counts them. When
    # they disagree the result is ambiguous against its own threshold, and RUN_RULES A6 says that
    # is a NULL, not a judgement call — which the pre-registration also says in as many words.
    # Implementing that is enforcing the registered rule, not narrowing it after the fact.
    clears, ep = prow.get("clears_p95"), prow.get("empirical_p")
    if not out["control_check"]["harness_ok"]:
        verdict = "NULL — control failed; no calibration quoted"
    elif clears and ep is not None and ep <= 0.05:
        verdict = "DISTINGUISHABLE"
    elif (not clears) and ep is not None and ep > 0.05:
        verdict = "NOT DISTINGUISHABLE — the product's confidence language must weaken"
    else:
        verdict = ("NULL — ambiguous against the registered bar (the p95 test and the empirical-p "
                   "test disagree at the boundary)")
    out["verdict"] = {
        "rule": "composite at rank 10 vs the H1 noise p95 (PREREG §7)",
        "primary_rank": PRIMARY_RANK,
        "real": prow.get("real"),
        "noise_p95": prow.get("noise_p95"),
        "empirical_p": prow.get("empirical_p"),
        "clears_p95": clears,
        "verdict": verdict,
        "generality": ("quotable as a property of the product"
                       if out["robustness"]["generality_met"]
                       else "quotable for the primary cross-section only"),
    }
    out["sentences"] = {str(k): _sentence(k, v)
                        for k, v in out["primary_within_column"]["table"].items()}

    _write(args.out, out, all_draws)
    print(f"\n[v3] VERDICT: {verdict}", flush=True)
    print(f"[v3] {len(all_draws):,} draws -> {args.out}", flush=True)
    return 0


def _write(path, out, draws):
    with open(path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    # RUN_RULES A9 — the per-draw rows, not just the percentiles. A summary answers the question
    # you had; the draws answer the one you get asked later.
    if not draws:
        return
    keys, seen = [], set()
    for d in draws:
        for k in d:
            if k not in seen:
                seen.add(k)
                keys.append(k)
    with open(path.replace(".json", "") + ".draws.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(draws)


if __name__ == "__main__":
    sys.exit(main())
