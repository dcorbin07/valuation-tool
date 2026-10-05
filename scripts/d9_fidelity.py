# -*- coding: utf-8 -*-
"""D9 STEP 1 — run the fidelity check. ZERO TRIALS (`MB1-SEL`).

Every constant is from `PREREG_d9_free_route_fidelity.md`. Changing one after a cross-vendor
number is read voids the item.

`--sharadar` scores the two Sharadar readings and banks them; `--compare` reads them and the
live snapshot and produces the verdict. Two passes, because the bars must be fixed before any
cross-vendor number is read and the register is the thing that fixes them.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
DATA = os.path.join(_ROOT, "data")
FA = os.path.join(DATA, "free_analysis")
LIVE_0808 = os.path.join(DATA, "live_cache", "snapshot_2026-08-08.json")
SHAR_CACHE = os.path.join(FA, "D9_SHARADAR_SCORES.pkl")
OUT = os.path.join(FA, "D9_FIDELITY.json")
ROWS_OUT = os.path.join(FA, "D9_FIDELITY_ROWS.pkl")

#: The register's two Sharadar readings.
#: THE FREEZE MIRRORS THE LAYOUT ONE LEVEL DOWN. `data/backtest_freeze_2026-08/` holds
#: MANIFEST / backtest / bulk / raw, and the per-ticker prices the scorer needs live in
#: `.../backtest/prices/`. Pointing a provider at the freeze ROOT indexes nothing, and
#: `score_universe_now` then returns EMPTY -- silently, because an empty universe is a
#: legitimate state. Caught by a 3-element result on a 2,531-name universe. Verified against
#: the stores themselves: the freeze's AAPL.csv ends 2026-07-31 and data/backtest's ends
#: 2026-07-24, exactly as the brief states.
READINGS = (("freeze_2026-07-31",
             os.path.join(DATA, "backtest_freeze_2026-08", "backtest"), "2026-07-31"),
            ("backtest_2026-07-24", os.path.join(DATA, "backtest"), "2026-07-24"))

#: The live book's own tier floor, from the served payload's `criteria.large_cap_min`.
LARGE_CAP_MIN = 1e10
TOP_DECILE = 0.10

#: THE BARS. From the register, section 4. Not to be moved.
B1_COMPOSITE_SPEARMAN = 0.80
B2_DECILE_OVERLAP = 0.60
B3_THEME_SPEARMAN = 0.70
#: The five themes the like-for-like composite is built from -- exactly those BOTH sides expose.
LIKE_FOR_LIKE = ("value", "quality", "momentum", "insider", "size")
#: The four that carry a B3 bar. `insider` is cited from FIDELITY-2 (B4), not re-derived here.
B3_THEMES = ("value", "quality", "momentum", "size")
#: FIDELITY-2's measured figures. CITED, never re-derived (register section 4 B4).
FIDELITY2 = {"institutional": 0.9190, "insider": 0.8726}


def _zneg_log_mktcap(mc: np.ndarray) -> np.ndarray:
    """`factors.py`'s `size` theme, rebuilt identically on both sides.

    `size = z_neg_log_mktcap`: the z-score of MINUS log market cap, so small is high. Rebuilt
    rather than read because the served payload does not expose it -- LABELLED a reconstruction
    in the register, and it is the same expression on both sides so it cannot favour either.
    """
    x = -np.log(np.asarray(mc, dtype=float))
    ok = np.isfinite(x)
    out = np.full(x.shape, np.nan)
    if ok.sum() > 1:
        out[ok] = (x[ok] - x[ok].mean()) / (x[ok].std(ddof=0) or 1.0)
    return out


def _flat_composite(df: pd.DataFrame, themes) -> np.ndarray:
    """Equal-weight mean of the z-themes present, ONE code path for both sides.

    NaN-skipping, matching `df[cols].mean(axis=1)` -- the shipped theme convention. A row with no
    theme at all returns NaN and is dropped by the caller rather than scored as average.
    """
    have = [t for t in themes if t in df.columns]
    if not have:
        return np.full(len(df), np.nan)
    return df[have].astype(float).mean(axis=1, skipna=True).to_numpy()


def score_sharadar() -> dict:
    from valuation.edge.fundamental_panel import score_universe_now
    from valuation.edge.data_providers import WRDSProvider
    out = {}
    for label, root, as_of in READINGS:
        class _C:
            wrds_data_dir = root

        prov = WRDSProvider(_C())
        ok, msg = prov.ready()
        if not ok:
            out[label] = {"error": "provider not ready: %s" % msg}
            print("  %-22s NOT READY: %s" % (label, msg), flush=True)
            continue
        tickers = prov.universe(None)
        t0 = time.time()
        print("  %-22s scoring %d names as_of=%s ..." % (label, len(tickers), as_of),
              flush=True)
        res = score_universe_now(prov, tickers, as_of=as_of,
                                 with_themes=True, with_numbers=True)
        # `score_universe_now` RETURNS TWO DIFFERENT TYPES: a dict on success and a bare `[]`
        # on either early exit (`if not kept` / `if fr.empty`). So `len(res)` is 3 on success
        # and `res["rows"]` raises on failure -- one idiom cannot serve both. Handled explicitly
        # and REPORTED as a bug rather than papered over.
        rows = res.get("rows") if isinstance(res, dict) else list(res)
        print("     -> %d rows in %.1f min%s"
              % (len(rows), (time.time() - t0) / 60.0,
                 "" if isinstance(res, dict) else "   [EMPTY-LIST return path]"), flush=True)
        out[label] = {"as_of": as_of, "root": root, "rows": rows,
                      "return_was_dict": isinstance(res, dict),
                      "dropped_mc_divergence": (res.get("dropped_mc_divergence")
                                                if isinstance(res, dict) else None)}
    pd.to_pickle(out, SHAR_CACHE)
    return out


def _sharadar_frame(rows) -> pd.DataFrame:
    d = pd.DataFrame(rows)
    d["ticker"] = d["ticker"].astype(str).str.upper()
    d = d[~d["ticker"].duplicated()].set_index("ticker")
    keep = [c for c in ("composite", "hot_score", "market_cap") if c in d.columns]
    z = {t: ("z_%s" % t) for t in LIKE_FOR_LIKE}
    for t, col in z.items():
        if t == "size":
            continue
        for cand in (col, t):
            if cand in d.columns:
                d[t] = pd.to_numeric(d[cand], errors="coerce")
                break
    if "market_cap" in d.columns:
        d["size"] = _zneg_log_mktcap(pd.to_numeric(d["market_cap"], errors="coerce").to_numpy())
    return d[[c for c in keep + list(LIKE_FOR_LIKE) if c in d.columns]]


def _live_frame(path) -> pd.DataFrame:
    with open(path, encoding="utf-8") as fh:
        j = json.load(fh)
    d = pd.DataFrame(j["rows"])
    d["ticker"] = d["ticker"].astype(str).str.upper()
    d = d[~d["ticker"].duplicated()].set_index("ticker")
    for t in LIKE_FOR_LIKE:
        if t == "size":
            continue
        c = "z_%s" % t
        if c in d.columns:
            d[t] = pd.to_numeric(d[c], errors="coerce")
    d["market_cap"] = pd.to_numeric(d["market_cap"], errors="coerce")
    d["size"] = _zneg_log_mktcap(d["market_cap"].to_numpy())
    d["composite_served"] = pd.to_numeric(d["composite"], errors="coerce")
    cols = ["market_cap", "composite_served"] + [t for t in LIKE_FOR_LIKE if t in d.columns]
    return d[cols], j


def _sp(a, b):
    a, b = pd.Series(np.asarray(a, float)), pd.Series(np.asarray(b, float))
    m = a.notna() & b.notna()
    if int(m.sum()) < 20:
        return None, int(m.sum())
    return float(a[m].corr(b[m], method="spearman")), int(m.sum())


def compare(cache=None, live_path=None, labels=None, out_path=None) -> int:
    # Paths are PARAMETERS, not module globals. `--same-date` used to overwrite the two-reading
    # cache `--sharadar` builds, so running the renewal re-check destroyed the artifact the
    # original comparison rests on. A mode that clobbers another mode's output is a defect even
    # when both are "just" intermediates.
    sh = pd.read_pickle(cache or SHAR_CACHE)
    live, lj = _live_frame(live_path or LIVE_0808)
    out = {"item": "D9", "step": "1 compare", "trials": 0,
           "live": {"scan_date": lj.get("scan_date"), "provider": lj.get("provider"),
                    "scored": lj.get("scored"), "universe_size": lj.get("universe_size"),
                    "rows": int(len(live))},
           "bars": {"B1_composite_spearman": B1_COMPOSITE_SPEARMAN,
                    "B2_decile_overlap": B2_DECILE_OVERLAP,
                    "B3_theme_spearman": B3_THEME_SPEARMAN,
                    "B4_cited_from_FIDELITY2": FIDELITY2},
           "readings": {}}

    live_tier = live[live["market_cap"] >= LARGE_CAP_MIN].copy()
    live_tier["ll_composite"] = _flat_composite(live_tier, LIKE_FOR_LIKE)
    out["live"]["large_cap_tier_rows"] = int(len(live_tier))

    for label in (labels or ("freeze_2026-07-31", "backtest_2026-07-24")):
        blk = sh.get(label) or {}
        if "rows" not in blk:
            out["readings"][label] = {"error": blk.get("error", "absent")}
            continue
        s = _sharadar_frame(blk["rows"])
        s_tier = s[pd.to_numeric(s["market_cap"], errors="coerce") >= LARGE_CAP_MIN].copy()
        s_tier["ll_composite"] = _flat_composite(s_tier, LIKE_FOR_LIKE)

        both = s_tier.index.intersection(live_tier.index)
        r = {"sharadar_tier_rows": int(len(s_tier)),
             "live_tier_rows": int(len(live_tier)),
             "overlapping_names": int(len(both))}

        rho, n = _sp(s_tier.loc[both, "ll_composite"], live_tier.loc[both, "ll_composite"])
        r["B1_like_for_like_composite_spearman"] = rho
        r["B1_n"] = n
        r["B1_pass"] = bool(rho is not None and rho >= B1_COMPOSITE_SPEARMAN)

        # the SERVED composite, secondary and labelled -- carries the weighting difference
        if "composite" in s_tier.columns:
            rho2, n2 = _sp(s_tier.loc[both, "composite"],
                           live_tier.loc[both, "composite_served"])
            r["secondary_served_composite_spearman"] = rho2
            r["secondary_n"] = n2
            r["secondary_note"] = ("carries the weighting difference of register section 1c "
                                   "(bucket-specific live weights vs flat 1/7) and therefore "
                                   "measures vendor AND weighting together; it carries no bar")

        # B2 -- the Sharadar decile's share also in the live decile, on the OVERLAPPING tier so
        # a name the live universe never had cannot count as a disagreement (that is the
        # coverage census's job, section 5, not this bar's).
        sa = s_tier.loc[both, "ll_composite"].dropna()
        lb = live_tier.loc[both, "ll_composite"].dropna()
        na = max(1, int(round(len(sa) * TOP_DECILE)))
        nb = max(1, int(round(len(lb) * TOP_DECILE)))
        ta, tb = set(sa.nlargest(na).index), set(lb.nlargest(nb).index)
        r["B2_sharadar_decile_n"] = len(ta)
        r["B2_live_decile_n"] = len(tb)
        r["B2_decile_overlap"] = len(ta & tb) / max(1, len(ta))
        r["B2_pass"] = bool(r["B2_decile_overlap"] >= B2_DECILE_OVERLAP)

        # B3 -- per theme
        r["B3_themes"] = {}
        for t in B3_THEMES:
            if t in s_tier.columns and t in live_tier.columns:
                rt, nt = _sp(s_tier.loc[both, t], live_tier.loc[both, t])
                r["B3_themes"][t] = {"spearman": rt, "n": nt,
                                     "pass": bool(rt is not None and rt >= B3_THEME_SPEARMAN)}
            else:
                r["B3_themes"][t] = {"spearman": None, "n": 0, "pass": False,
                                     "note": "theme absent on one side"}
        # growth is served but is NOT one of the deployed seven -- diagnostic, no bar
        if "z_growth" in pd.DataFrame(blk["rows"]).columns:
            pass
        r["B3_pass"] = all(v["pass"] for v in r["B3_themes"].values())
        r["capital_discipline"] = ("NOT MEASURED -- z_neg_issuance is not served; recorded as "
                                   "not-measured, never as agreeing")

        # ---- section 5: the coverage census
        sh_dec_full = s_tier["ll_composite"].dropna()
        nfull = max(1, int(round(len(sh_dec_full) * TOP_DECILE)))
        dec_full = sh_dec_full.nlargest(nfull).index
        absent = [t for t in dec_full if t not in live.index]
        r["coverage_census"] = {
            "sharadar_decile_n": int(len(dec_full)),
            "absent_from_live_universe": len(absent),
            "absent_share": len(absent) / max(1, len(dec_full)),
            "names": [{"ticker": t,
                       "market_cap": float(s_tier.at[t, "market_cap"])}
                      for t in absent],
        }
        if absent:
            mcs = [x["market_cap"] for x in r["coverage_census"]["names"]]
            tier_med = float(pd.to_numeric(s_tier["market_cap"], errors="coerce").median())
            r["coverage_census"]["median_market_cap_of_absent"] = float(np.median(mcs))
            r["coverage_census"]["tier_median_market_cap"] = tier_med
            r["coverage_census"]["absent_are_smaller_than_tier_median"] = bool(
                np.median(mcs) < tier_med)

        r["VERDICT"] = ("GO" if (r["B1_pass"] and r["B2_pass"] and r["B3_pass"])
                        else "NO-GO")
        r["failing"] = [k for k, v in (("B1", r["B1_pass"]), ("B2", r["B2_pass"]),
                                       ("B3", r["B3_pass"])) if not v]
        out["readings"][label] = r

        # bank every per-name row (A9)
        pd.to_pickle({"sharadar": s_tier, "live": live_tier, "overlap": list(both)},
                     ROWS_OUT.replace(".pkl", "_%s.pkl" % label))

    prim = out["readings"].get("freeze_2026-07-31") or {}
    out["VERDICT"] = prim.get("VERDICT", "NO-GO")
    out["verdict_basis"] = "freeze_2026-07-31 is the register's PRIMARY reading"
    json.dump(out, open(out_path or OUT, "w"), indent=1, default=str)
    printable = {k: v for k, v in out.items()}
    for lab in printable.get("readings", {}):
        cc = printable["readings"][lab].get("coverage_census")
        if cc and len(cc.get("names", [])) > 12:
            cc["names"] = cc["names"][:12] + [{"...": "truncated for print; full list in artifact"}]
    print(json.dumps(printable, indent=1, default=str))
    print("\nwrote", OUT)
    return 0


def same_date(root, as_of, live_path=None) -> int:
    """THE RENEWAL RE-CHECK, in one command.

        python scripts/d9_fidelity.py --same-date --sharadar-root <dir> --as-of YYYY-MM-DD

    Scores the fresh Sharadar export at `as_of`, takes the live scan for the SAME date, and runs
    the comparison. Same-date is the whole point: it removes the 6-trading-day drift and the
    ~0.95 within-vendor ceiling from the comparison entirely, so what is left is vendor
    disagreement and nothing else.

    `--live` defaults to the live service, which serves `latest_scan_date()`; the date it
    returns is CHECKED against `as_of` and a mismatch REFUSES rather than silently comparing
    across a gap, which is the whole defect this mode exists to remove.
    """
    # ---- THE LIVE SIDE AND ITS DATE COME FIRST, BEFORE THE PROVIDER IS TOUCHED.
    # The date check is the cheap refusal and the provider load is the expensive one, so
    # ordering them the other way round means a caller on the wrong date pays for an export
    # index before being told the comparison is invalid -- and on a machine with no export at
    # all it dies with "provider not ready" and never reaches the refusal, which is exactly how
    # `test_same_date_refuses_a_date_mismatch` passed here and failed in CI.
    if live_path:
        with open(live_path, encoding="utf-8") as fh:
            lj = json.load(fh)
    else:
        import urllib.request
        with urllib.request.urlopen(
                "https://valquo.co/api/hotstocks?top=500", timeout=120) as r:
            lj = json.loads(r.read().decode("utf-8"))
        live_path = os.path.join(FA, "D9_LIVE_%s.json" % str(lj.get("scan_date"))[:10])
        with open(live_path, "w", encoding="utf-8") as fh:
            json.dump(lj, fh)
    live_date = str(lj.get("scan_date"))[:10]
    if live_date != str(as_of)[:10]:
        raise SystemExit(
            "REFUSING: the live scan is %s and --as-of is %s. This mode exists to compare the "
            "SAME date; comparing across a gap is what D9 already measured and what the "
            "~0.95 ceiling makes uninterpretable. Re-run when the live scan reaches %s, or "
            "pass --as-of %s to score Sharadar on the live date instead."
            % (live_date, str(as_of)[:10], str(as_of)[:10], live_date))

    # ---- only now the expensive side
    from valuation.edge.fundamental_panel import score_universe_now
    from valuation.edge.data_providers import WRDSProvider

    class _C:
        wrds_data_dir = root

    prov = WRDSProvider(_C())
    ok, msg = prov.ready()
    if not ok:
        raise SystemExit("provider not ready at %s: %s" % (root, msg))

    print("  same-date re-check: Sharadar %s at %s  vs  live %s" % (root, as_of, live_date),
          flush=True)
    tickers = prov.universe(None)
    res = score_universe_now(prov, tickers, as_of=as_of,
                             with_themes=True, with_numbers=True)
    rows = res.get("rows") if isinstance(res, dict) else list(res)
    # AND THE EXPORT MUST ACTUALLY REACH `as_of`. `score_universe_now` resolves `as_of` with
    # `searchsorted(cal, as_of, "right") - 1`, i.e. the last session AT OR BEFORE it -- so a
    # stale export scores an OLD cross-section under a FRESH label, silently. A renewal
    # re-check is exactly the situation where that matters, so the returned `as_of` is compared
    # with the requested one and a mismatch REFUSES.
    used = str((res.get("as_of") if isinstance(res, dict) else None) or "")[:10]
    if used and used != str(as_of)[:10]:
        raise SystemExit(
            "REFUSING: --as-of %s was requested but the export's latest session at or before "
            "it is %s, so this would score a stale cross-section under a fresh date. The "
            "export does not reach %s." % (str(as_of)[:10], used, str(as_of)[:10]))
    print("     -> %d Sharadar rows (export reached %s)" % (len(rows), used or as_of),
          flush=True)
    sd_cache = os.path.join(FA, "D9_SHARADAR_SCORES_SAMEDATE.pkl")
    # THE READING IS KEYED BY WHAT IT IS, NOT BY THE READING IT RESEMBLES. This used to write
    # under `freeze_2026-07-31`, so `compare` emitted the same-date result UNDER THE PUBLISHED
    # READING'S NAME and overwrote both `D9_FIDELITY.json` and
    # `D9_FIDELITY_ROWS_freeze_2026-07-31.pkl` -- the landed B1 0.4321 / B2 0.2326 destroyed by
    # a mode whose only job is to re-check them. The comment above `compare` already names this
    # defect for the SCORES CACHE and fixed it there; the OUTPUT was left keyed the old way, so
    # the fix was HALF APPLIED. Recovered by re-running `--compare`, which reproduced both
    # published figures at 0.000e+00 against the constants `index_choice_buildable` preserves.
    label = "same_date_%s" % str(as_of)[:10]
    pd.to_pickle({label: {"as_of": as_of, "root": root, "rows": rows,
                          "return_was_dict": isinstance(res, dict),
                          "dropped_mc_divergence": None}}, sd_cache)
    return compare(cache=sd_cache, live_path=live_path, labels=(label,),
                   out_path=os.path.join(FA, "D9_FIDELITY_SAMEDATE.json"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sharadar", action="store_true")
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--same-date", action="store_true",
                    help="one-command renewal re-check: score a fresh export at --as-of and "
                         "compare against the live scan for the SAME date")
    ap.add_argument("--sharadar-root", default=os.path.join(DATA, "backtest"))
    ap.add_argument("--as-of", default=None)
    ap.add_argument("--live", default=None,
                    help="a saved live snapshot json; omit to read the live service")
    a = ap.parse_args(argv)
    if getattr(a, "same_date"):
        if not a.as_of:
            raise SystemExit("--same-date needs --as-of YYYY-MM-DD")
        return same_date(a.sharadar_root, a.as_of, a.live)
    if a.sharadar:
        score_sharadar()
    if a.compare:
        return compare()
    if not (a.sharadar or a.compare):
        print("pass --sharadar then --compare, or --same-date --as-of YYYY-MM-DD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
