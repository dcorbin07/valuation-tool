"""W-6 — CRSP delisting cross-check of the survivorship mask.

Register: `PREREG_w6_crsp_delist_xcheck.md` (committed ALONE at 921c810).

WHAT THIS IS
    A CONTROL. It asks whether the ACTIONS survivorship mask the panel is built on is
    independently contradicted by CRSP's own delisting record for the same securities. Under
    `MB1-SEL` a control can only BLOCK a finding and never produce one, so it charges ZERO
    trials and adopts nothing.

AGREEMENT IS NOT PROOF
    Both vendors ultimately read the same exchange and regulator notices. Two transcriptions
    agreeing shows neither mangled the transcription; it does not show the notice was right.
    Every PASS below means "not independently contradicted", never "correct". The register says
    this first, and so does the artifact.

THE JOIN IS DATED AND THE FUNCTIONS ARE IMPORTED
    `ticker_permno_intervals` / `permno_on` come from `valuation/edge/adv.py` (`W-3b`'s scoping)
    rather than being reimplemented -- `B7`. Their own docstring carries the reason: 1,053 of
    2,271 matched tickers map to more than one permno, so an undated `{ticker: permno}` map
    misattributes one company's record to another SILENTLY.

THE CRSP CUT IS HONOURED IN ADVANCE
    CRSP ends 2024-12-31 on this account. The panel's five later rebalance dates are
    UNVERIFIABLE by construction and are LISTED, never scored. `W-28` read this exact cut as a
    coverage gap, saw per-date coverage of zero on 2025-26 rows, and had to repair its
    instrument mid-item.

WHAT V3 ACTUALLY COMPARES, because the two terminal returns are DIFFERENT OBJECTS
    The panel's terminal return for a name that stops trading inside its window is
    `last_close / c0 - 1` (`E-5`: a delisted name has a TERMINAL value). CRSP's `dlret` is the
    return OF the delisting event, which can include a final liquidating distribution. They are
    not the same quantity and comparing them directly would be the wrong-object family. So the
    comparison is between the panel's terminal return and the SAME return with CRSP's delisting
    return applied at the end:

        panel      : r        = fwd_ret
        CRSP-adjusted: r_crsp = (1 + fwd_ret) * (1 + dlret) - 1

    which is exactly the quantity the register's "rows whose terminal return would CHANGE under
    CRSP's dlret" asks for.

RUN
    python -m scripts.w6_crsp_delist_xcheck            # controls, then kills, then bars
    python -m scripts.w6_crsp_delist_xcheck --controls-only
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import datetime as dt

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

from valuation.edge.adv import ticker_permno_intervals, permno_on      # noqa: E402
import valuation.edge.fundamental_panel as FP                          # noqa: E402

RAW_ROOT = r"D:\wrds"
PANEL = os.path.join("free_analysis", "panel_corrected_69d.pkl")

CRSP_CUT = "2024-12-31"
PANEL_START = "2009-01-15"

THEMES = ("value", "quality", "momentum", "insider", "capital_discipline", "size",
          "institutional")
W = 0.125

#: C1's target -- the published record the panel must reproduce before anything is joined.
REC = {"top_decile_alpha": 0.07174142332098163,
       "long_short_tstat": 2.8360640685320595,
       "long_short_tstat_nw": 2.6199121240414884,
       "monotonicity": -0.8909090909090909}

# ---- BARS. Every one from the register. Changing a value here voids the item. ----
V1_BAR = 0.95            # flag agreement, share of matched names
V2_BAR = 0.95            # date agreement, share of matched events
V2_DAYS = 3              # +/- calendar days
V3_BAR = 0.90            # terminal-return agreement, share of matched events
V3_TOL = 0.01            # absolute, on the return; 9.3% of the panel's median |fwd_ret|
K1_BAR = 0.80            # dated link share of names carrying an ACTIONS delisting event
K2_MIN_DATES = 16        # the shipped min_dates floor, reused verbatim


def _data_root():
    d = REPO
    for _ in range(6):
        if os.path.isfile(os.path.join(d, "data", PANEL)):
            return os.path.join(d, "data")
        p = os.path.dirname(d)
        if p == d:
            break
        d = p
    raise SystemExit("REFUSING: no data root holding %s. A worktree carries data/ EMPTY." % PANEL)


def _banked(rel):
    """Banked WRDS frames are gzip-compressed behind a bare `.pkl`; pandas infers none."""
    return pd.read_pickle(os.path.join(RAW_ROOT, rel), compression="gzip")


# ---------------------------------------------------------------------------
# CONTROLS -- own pass, read BEFORE the comparison
# ---------------------------------------------------------------------------
def c1_fidelity(panel):
    """The panel must BE the published one. ABORTS if it is not.

    A cross-check against a panel that is not the object the record describes measures nothing,
    so this is a gate and not a diagnostic.
    """
    res = FP.quantile_backtest(panel, list(THEMES), {t: W for t in THEMES}, n_q=10)
    got, worst, at = {}, 0.0, None
    for k, want in REC.items():
        v = res.get(k)
        got[k] = float(v) if v is not None else None
        d = abs((got[k] if got[k] is not None else float("nan")) - want)
        if d == d and d > worst:
            worst, at = d, k
    return {"got": got, "want": REC, "max_abs_delta": worst, "worst_at": at,
            "pass": bool(worst == 0.0)}


# ---------------------------------------------------------------------------
# THE COMPARISON
# ---------------------------------------------------------------------------
#: Sharadar's own disambiguators, which CRSP's exchange ticker does not carry.
_SUFFIX_DIGIT = re.compile(r"^([A-Z.\-]{2,}?)([1-9])$")     # ticker REUSED by a later company
_SUFFIX_Q = re.compile(r"^([A-Z.\-]{2,})Q$")                # company in bankruptcy


def _strip_vendor_suffix(t):
    """Sharadar's suffix stripped so the SAME security can be found in CRSP. A FALLBACK ONLY.

    A DEFECT IN THIS INSTRUMENT, FOUND BY READING THE SHAPE OF ITS OWN FAILURE. The first cut
    joined on the raw Sharadar ticker and K1 fired at a dated link of 0.6633 -- and ALL 199
    unmatched names failed at the ticker-to-permno step, with ZERO having a permno that lacked a
    CRSP delisting record. Censused, 179 of those 199 carry a vendor suffix: 109 a trailing digit
    (Sharadar appends one when a ticker is REUSED by a different company) and 70 a trailing Q
    (bankruptcy). CRSP uses neither convention. So the join was failing on exactly the names most
    likely to have delisted -- the bankrupt ones and the reused ones -- which is a KEY MISMATCH
    and not evidence that CRSP lacks 199 companies.

    THE BAR IS NOT TOUCHED. K1 stays at 0.80; what is repaired is the key. Void condition 1
    forbids relaxing a bar and void condition 4 forbids an UNDATED map -- the retry stays
    date-scoped, so both hold.

    AND THE RESCUE IS VALIDATED RATHER THAN TRUSTED, because stripping a suffix could match a
    DIFFERENT company -- W-28's contamination shape. The date scoping is the first guard: the
    base ticker must have denoted that permno ON the event date. The second is free and is
    reported: V2 and V3 are computed SEPARATELY for the raw-matched and suffix-stripped routes.
    If the rescue were matching the wrong company its delisting dates would not agree, so the
    rescued route's own V2 rate IS the test of whether the rescue is sound.
    """
    t = str(t).upper().strip()
    m = _SUFFIX_DIGIT.match(t)
    if m:
        return m.group(1)
    m = _SUFFIX_Q.match(t)
    if m:
        return m.group(1)
    return None


def actions_delistings(freeze):
    a = pd.read_csv(os.path.join(freeze, "bulk", "actions.csv"),
                    usecols=["date", "action", "ticker"], low_memory=False)
    de = a[a["action"].astype(str).str.lower().str.contains("delist", na=False)].copy()
    de["date"] = de["date"].astype(str).str.slice(0, 10)
    return de, len(a)


def build(panel, freeze):
    de, n_actions = actions_delistings(freeze)
    names = set(panel["ticker"].astype(str).str.upper())

    ev = de[de["ticker"].astype(str).str.upper().isin(names)].copy()
    ev["ticker"] = ev["ticker"].astype(str).str.upper()
    in_window = ev[(ev["date"] >= PANEL_START) & (ev["date"] <= CRSP_CUT)].copy()
    past_cut = ev[ev["date"] > CRSP_CUT].copy()

    # earliest in-window delisting per name is the event under test
    first = in_window.sort_values("date").drop_duplicates("ticker", keep="first")

    sn = _banked("crsp_stocknames/crsp_stocknames_all.pkl")
    iv = ticker_permno_intervals(sn)
    dl = _banked("crsp_delist/crsp_delist_all.pkl").copy()
    dl["dlstdt"] = dl["dlstdt"].astype(str).str.slice(0, 10)
    by_permno = {int(r.permno): r for r in dl.itertuples()}

    rows = []
    for r in first.itertuples():
        p = permno_on(iv, r.ticker, r.date)
        route = "raw"
        if p is None:
            base = _strip_vendor_suffix(r.ticker)
            if base:
                p = permno_on(iv, base, r.date)      # STILL DATE-SCOPED
                if p is not None:
                    route = "suffix_stripped"
        rec = {"ticker": r.ticker, "actions_date": r.date, "permno": p,
               "match_route": (route if p is not None else None)}
        if p is None:
            rec["state"] = "NO_DATED_INTERVAL"
        else:
            c = by_permno.get(int(p))
            if c is None:
                rec["state"] = "NO_CRSP_DELIST_RECORD"
            else:
                rec["state"] = "MATCHED"
                rec["dlstdt"] = c.dlstdt
                rec["dlstcd"] = (None if pd.isna(c.dlstcd) else int(c.dlstcd))
                rec["dlret"] = (None if pd.isna(c.dlret) else float(c.dlret))
        rows.append(rec)
    return (pd.DataFrame(rows), first, in_window, past_cut, n_actions,
            {"stocknames_rows": int(len(sn)), "dsedelist_rows": int(len(dl))})


def score(x, panel):
    """V1, V2, V3 -- and every rate carries the count it was computed over (C3)."""
    n_names = int(len(x))
    matched = x[x["state"] == "MATCHED"].copy()
    n_matched = int(len(matched))

    by_route = x[x["state"] == "MATCHED"]["match_route"].value_counts().to_dict()
    n_raw = int(by_route.get("raw", 0))
    n_resc = int(by_route.get("suffix_stripped", 0))
    out = {"names_with_actions_event": n_names,
           "names_matched_to_crsp": n_matched,
           "dated_link_share": (round(n_matched / n_names, 6) if n_names else None),
           "matched_by_route": {"raw": n_raw, "suffix_stripped": n_resc},
           "dated_link_share_RAW_ONLY": (round(n_raw / n_names, 6) if n_names else None),
           "route_note": ("the RAW-ONLY share is what the first cut of this instrument measured "
                          "and it fired K1 at 0.6633; 179 of its 199 failures carried a Sharadar "
                          "suffix CRSP does not use, which is a key mismatch rather than a "
                          "coverage gap. The bar is unchanged at %.2f." % K1_BAR)}

    # ---- C6: the unmatched, counted AND listed, never read as agreement ----
    gap_iv = x[x["state"] == "NO_DATED_INTERVAL"]["ticker"].tolist()
    gap_rec = x[x["state"] == "NO_CRSP_DELIST_RECORD"]["ticker"].tolist()
    out["C6_no_dated_interval"] = {"n": len(gap_iv), "tickers": sorted(gap_iv)[:200]}
    out["C6_no_crsp_delist_record"] = {"n": len(gap_rec), "tickers": sorted(gap_rec)[:200]}

    # ---- V1 ----
    out["V1"] = {"rate": out["dated_link_share"], "n_compared": n_names, "bar": V1_BAR,
                 "pass": (None if not n_names else bool(n_matched / n_names >= V1_BAR)),
                 "vacuous": not n_names}

    # ---- V2 ----
    if n_matched:
        a = pd.to_datetime(matched["actions_date"], errors="coerce")
        b = pd.to_datetime(matched["dlstdt"], errors="coerce")
        gap = (b - a).dt.days.abs()
        ok = (gap <= V2_DAYS)
        out["V2"] = {"rate": round(float(ok.mean()), 6), "n_compared": int(ok.notna().sum()),
                     "bar": V2_BAR, "days": V2_DAYS, "pass": bool(ok.mean() >= V2_BAR),
                     "median_abs_gap_days": (None if gap.dropna().empty
                                             else float(gap.median())),
                     "vacuous": False}
        matched = matched.assign(_gap_days=gap, _ok2=ok)
        # THE RESCUE'S OWN TEST. If suffix-stripping matched the wrong company its delisting
        # dates would not agree, so this per-route rate validates the repair rather than
        # assuming it. Reported whichever way it comes out.
        out["V2_by_route"] = {}
        for rt, g in matched.groupby("match_route"):
            out["V2_by_route"][str(rt)] = {"rate": round(float(g["_ok2"].mean()), 6),
                                           "n_compared": int(len(g))}
    else:
        out["V2"] = {"rate": None, "n_compared": 0, "bar": V2_BAR, "pass": None,
                     "vacuous": True}

    # ---- V3: the panel's terminal return vs the same return with dlret applied ----
    pan = panel.assign(_t=panel["ticker"].astype(str).str.upper(),
                       _d=panel["date"].astype(str).str.slice(0, 10))
    eff = pan[pan["_d"] <= CRSP_CUT]
    last_row = (eff.sort_values("_d").drop_duplicates("_t", keep="last")
                   .set_index("_t")[["_d", "fwd_ret"]])
    m = matched.join(last_row, on="ticker")
    m = m[m["dlret"].notna() & m["fwd_ret"].notna()].copy()
    if len(m):
        m["r_panel"] = m["fwd_ret"].astype(float)
        m["r_crsp"] = (1.0 + m["r_panel"]) * (1.0 + m["dlret"].astype(float)) - 1.0
        m["delta"] = (m["r_crsp"] - m["r_panel"]).abs()
        ok = m["delta"] <= V3_TOL
        out["V3"] = {"rate": round(float(ok.mean()), 6), "n_compared": int(len(m)),
                     "bar": V3_BAR, "tolerance": V3_TOL, "pass": bool(ok.mean() >= V3_BAR),
                     "median_abs_delta": float(m["delta"].median()),
                     "p95_abs_delta": float(m["delta"].quantile(0.95)),
                     "construction": ("panel r = fwd_ret on the name's last EFFECTIVE date; "
                                      "CRSP-adjusted r = (1+r)*(1+dlret)-1"),
                     "vacuous": False}
        out["rows_whose_terminal_return_would_change"] = {
            "n": int((~ok).sum()), "of": int(len(m)),
            "note": "exceeds the pre-committed +/-%.2f tolerance" % V3_TOL}
        m = m.assign(_ok3=ok)
        out["V3_by_route"] = {}
        for rt, g in m.groupby("match_route"):
            out["V3_by_route"][str(rt)] = {"rate": round(float(g["_ok3"].mean()), 6),
                                           "n_compared": int(len(g))}
    else:
        out["V3"] = {"rate": None, "n_compared": 0, "bar": V3_BAR, "pass": None,
                     "vacuous": True}
        out["rows_whose_terminal_return_would_change"] = {"n": 0, "of": 0,
                                                          "note": "VACUOUS -- nothing compared"}
    return out, matched, m


def disagreement_set(x, matched, m):
    """W-3b's taxonomy: a bare rate cannot separate two causes implying opposite actions."""
    gap = int((x["state"] != "MATCHED").sum())
    conflict_date = 0
    if "_gap_days" in matched.columns:
        conflict_date = int((matched["_gap_days"] > V2_DAYS).sum())
    conflict_ret = int((m["delta"] > V3_TOL).sum()) if len(m) else 0
    tot = gap + conflict_date + conflict_ret
    return {
        "COVERAGE_GAP": {"n": gap, "share": (round(gap / tot, 6) if tot else None),
                         "meaning": "CRSP has no dated interval or no record, so there was "
                                    "never a counterpart to agree with"},
        "REAL_CONFLICT_date": {"n": conflict_date,
                               "meaning": "CRSP has a record and its date disagrees by more "
                                          "than the pre-committed window"},
        "REAL_CONFLICT_terminal_return": {"n": conflict_ret,
                                          "meaning": "CRSP's dlret moves the terminal return "
                                                     "past the pre-committed tolerance"},
        "total": tot,
    }


def halves(matched, m):
    """K2 plus the by-half count, on EFFECTIVE dates only."""
    if not len(matched):
        return {"status": "VACUOUS", "reason": "no matched events"}
    d = pd.to_datetime(matched["actions_date"], errors="coerce").dropna()
    if d.empty:
        return {"status": "VACUOUS", "reason": "no parseable event dates"}
    mid = d.quantile(0.5)
    early_dates = int(d[d <= mid].dt.date.nunique())
    late_dates = int(d[d > mid].dt.date.nunique())
    out = {"boundary": str(mid.date()), "early_event_dates": early_dates,
           "late_event_dates": late_dates, "K2_min_dates": K2_MIN_DATES,
           "K2_split_available": bool(late_dates >= K2_MIN_DATES
                                      and early_dates >= K2_MIN_DATES)}
    if len(m):
        md = pd.to_datetime(m["actions_date"], errors="coerce")
        changed = m["delta"] > V3_TOL
        out["changed_terminal_returns_early"] = int((changed & (md <= mid)).sum())
        out["changed_terminal_returns_late"] = int((changed & (md > mid)).sum())
    if not out["K2_split_available"]:
        out["note"] = ("the both-halves split is UNAVAILABLE and is reported as unavailable "
                       "rather than computed on a thin cell")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--controls-only", action="store_true")
    ap.add_argument("--out-json", default=os.path.join(RAW_ROOT, "W6_CRSP_DELIST_XCHECK.json"))
    ap.add_argument("--out-md", default=os.path.join(REPO, "W6_CRSP_DELIST_XCHECK.md"))
    args = ap.parse_args(argv)

    root = _data_root()
    freeze = os.path.join(root, "backtest_freeze_2026-08")
    panel = pd.read_pickle(os.path.join(root, PANEL))
    dates = sorted(panel["date"].astype(str).str.slice(0, 10).unique())
    past_cut_dates = [d for d in dates if d > CRSP_CUT]

    art = {"item": "MC13 / W-6", "class": "CONTROL", "trials": 0,
           "register": "PREREG_w6_crsp_delist_xcheck.md",
           "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "data_root_resolved": root,
           "panel": {"rows": int(len(panel)), "names": int(panel["ticker"].nunique()),
                     "dates": len(dates), "first": dates[0], "last": dates[-1]},
           "crsp_cut": CRSP_CUT,
           "UNVERIFIABLE_rebalance_dates_past_the_cut": past_cut_dates,
           "agreement_is_not_proof": ("both vendors derive from the same exchange notices, so a "
                                      "PASS means the mask is not independently contradicted "
                                      "and never that it is correct"),
           "bars": {"V1": V1_BAR, "V2": V2_BAR, "V2_days": V2_DAYS, "V3": V3_BAR,
                    "V3_tolerance": V3_TOL, "K1": K1_BAR, "K2_min_dates": K2_MIN_DATES}}

    print("[w6] C1 fidelity -- the panel must BE the published one ...", flush=True)
    c1 = c1_fidelity(panel)
    art["C1_fidelity"] = c1
    for k, want in REC.items():
        print("       %-22s got %r  want %r" % (k, c1["got"][k], want))
    print("       max |delta| %.3e at %s -> %s"
          % (c1["max_abs_delta"], c1["worst_at"], "PASS" if c1["pass"] else "FAIL"), flush=True)
    if not c1["pass"]:
        art["verdict"] = "ABORTED: C1 fidelity failed; no agreement rate was computed"
        _write(art, args)
        raise SystemExit("[w6] ABORT: the panel does not reproduce the published record")

    if args.controls_only:
        art["verdict"] = "CONTROLS ONLY -- no comparison run"
        _write(art, args)
        return 0

    print("[w6] building the dated join ...", flush=True)
    x, first, in_window, past, n_actions, shapes = build(panel, freeze)
    art["sources"] = dict(shapes, actions_rows=n_actions,
                          actions_delist_events_on_panel_names=int(len(in_window)),
                          actions_delist_events_PAST_CUT_not_scored=int(len(past)))

    res, matched, m = score(x, panel)
    art.update(res)

    # ---- K1, read FIRST ----
    link = res["dated_link_share"]
    k1_pass = (None if link is None else bool(link >= K1_BAR))
    art["K1"] = {"dated_link_share": link, "bar": K1_BAR, "pass": k1_pass,
                 "consequence_if_failed": "STOP and report the coverage figure"}
    print("[w6] K1 dated link %s against %.2f -> %s"
          % (link, K1_BAR, "PASS" if k1_pass else "FIRES"), flush=True)
    if k1_pass is False:
        art["verdict"] = ("K1 FIRES: the dated link reaches %.4f of the %d panel names carrying "
                          "an ACTIONS delisting event, below the pre-committed %.2f. The item "
                          "STOPS and the coverage figure IS the result. The bar is not relaxed."
                          % (link, res["names_with_actions_event"], K1_BAR))
        art["disagreement_set"] = disagreement_set(x, matched, m)
        _write(art, args)
        print("[w6] " + art["verdict"])
        return 0

    art["disagreement_set"] = disagreement_set(x, matched, m)
    art["halves"] = halves(matched, m)

    bars = {k: res[k]["pass"] for k in ("V1", "V2", "V3")}
    if all(v is True for v in bars.values()):
        v = "NOT INDEPENDENTLY CONTRADICTED -- all three bars clear"
    elif any(v is None for v in bars.values()):
        v = "NULL -- at least one bar is VACUOUS and is reported as vacuous, never as passing"
    else:
        failed = [k for k, val in bars.items() if val is False]
        v = ("NULL on a pre-committed bar (A6): %s below bar. The disagreement set is the "
             "deliverable and a failing bar licenses a NEW register, not a repair here."
             % ", ".join(failed))
    art["verdict"] = v
    print("[w6] VERDICT: %s" % v)
    _write(art, args)
    return 0


def _write(art, args):
    os.makedirs(os.path.dirname(args.out_json), exist_ok=True)
    with io.open(args.out_json, "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    print("banked %s" % args.out_json)
    L = []
    A = L.append
    A("# W6_CRSP_DELIST_XCHECK — CRSP delisting cross-check (CONTROL, zero trials)")
    A("")
    A("Register: `PREREG_w6_crsp_delist_xcheck.md`. Generated `%s`." % art["utc"])
    A("")
    A("**%s**" % art["agreement_is_not_proof"].capitalize())
    A("")
    A("CRSP is cut at **%s**. The panel's %d later rebalance dates are UNVERIFIABLE by "
      "construction and are listed, never scored: %s."
      % (art["crsp_cut"], len(art["UNVERIFIABLE_rebalance_dates_past_the_cut"]),
         ", ".join("`%s`" % d for d in art["UNVERIFIABLE_rebalance_dates_past_the_cut"])))
    A("")
    c1 = art["C1_fidelity"]
    A("## C1 — fidelity (gate)")
    A("")
    A("| field | got | want |")
    A("|---|---|---|")
    for k, want in c1["want"].items():
        A("| `%s` | %r | %r |" % (k, c1["got"][k], want))
    A("")
    A("max |delta| **%.3e** at `%s` — **%s**"
      % (c1["max_abs_delta"], c1["worst_at"], "PASS" if c1["pass"] else "FAIL"))
    A("")
    if "V1" in art:
        A("## Bars — every rate with the count it was computed over (C3)")
        A("")
        A("| bar | rate | n compared | bar | verdict |")
        A("|---|---|---|---|---|")
        for k in ("V1", "V2", "V3"):
            b = art[k]
            A("| %s | %s | %s | %s | %s |"
              % (k, b.get("rate"), b.get("n_compared"), b.get("bar"),
                 "VACUOUS" if b.get("vacuous") else ("PASS" if b.get("pass") else "FAIL")))
        A("")
        A("`K1` dated link **%s** against **%s** — %s"
          % (art["K1"]["dated_link_share"], art["K1"]["bar"],
             "PASS" if art["K1"]["pass"] else "**FIRES**"))
        A("")
    if "disagreement_set" in art:
        A("## The disagreement set, split by cause (`W-3b`'s taxonomy)")
        A("")
        A("| cause | n | meaning |")
        A("|---|---|---|")
        for k, v in art["disagreement_set"].items():
            if isinstance(v, dict):
                A("| %s | %s | %s |" % (k, v.get("n"), v.get("meaning", "")))
        A("")
    A("## Verdict")
    A("")
    A("**%s**" % art.get("verdict", "(not reached)"))
    A("")
    A("Zero trials. ADOPTS NOTHING — a control can only block, never produce (`MB1-SEL`). A "
      "failing bar licenses a NEW register with its own charge and Don's decision.")
    A("")
    with io.open(args.out_md, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L))
    print("wrote %s" % args.out_md)


if __name__ == "__main__":
    sys.exit(main())
