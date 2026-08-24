# -*- coding: utf-8 -*-
"""S3-I3 validation — the short-book model against V6-OPT's 660 real settled puts.

`I-3`'s pattern, for `I-3`'s reason: an instrument is validated BEFORE anything new consumes it
(`MB15`), against a figure that was banked by someone else, so a later disagreement is
attributable to this module rather than to drift.

FIVE CONTROLS. C1 and C3 are the load-bearing ones; the rest bound what the module is for.

  C1  B7 FIDELITY ON REAL ROWS. `settle_short` must reproduce `csp_surface.settle_put` -- and
      therefore V6-OPT's landed `ret_on_strike` and `assigned` -- on every trade in the banked
      book. The COUNT is gated, because `MB21`'s C1 scored a perfect 0.000e+00 on an empty
      frame by comparing nothing.
  C2  The trades reproduce the artifact's own published `n`, so this is V6-OPT's book and not a
      lookalike.
  C3  THE SPLIT TRAP, MEASURED RATHER THAN ASSERTED. Every trade is re-settled against the
      ADJUSTED close instead of `raw_close`. If the two bases agree everywhere the guard is
      decoration; the census says whether it is live on real rows and how large the damage is.
  C4  THE MA36 MIRROR ON REAL ROWS. Every unassigned trade must owe EXACTLY zero, and the
      long-side rule would have posted -100% on each -- the census sizes what inheriting it
      would have cost.
  C5  Early-assignment flag census over the book's own dividend table, reported as a DIAGNOSTIC
      with no verdict: it is a rationality flag, not a probability, and no rate may be read off
      it.

ZERO TRIALS. No hypothesis, no bar, no verdict against a threshold -- the `S25` / `MB15` /
`I-2` / `I-3` class. Nothing here scores an outcome relationship: `ret_on_strike` is compared
FOR EQUALITY against a published figure, never read for a verdict.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import dividends as DIV                                        # noqa: E402
from valuation.edge import short_book as SB                                        # noqa: E402
from valuation.edge.csp_surface import settle_put                                  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


REQUIRED = "V6OPT_STAGE2_TRADES.pkl"


def _populated(root: str) -> bool:
    """EXISTENCE IS NOT POPULATION, and this project has paid for the difference.

    `DEEPITM-FIN` resolved paths with `os.path.exists` and an EMPTY `data/bulk/prepared/bars` in
    the worktree shadowed the primary's 502 files, so the run reported `spot series: 0` and
    scored nothing. The worktree here carries exactly that shape: `data/free_analysis` EXISTS
    and holds nothing. So the probe is for the FILE this validation cannot run without.
    """
    return os.path.isfile(os.path.join(root, "free_analysis", REQUIRED))


def _data_root(explicit=None) -> str:
    """The PRIMARY checkout's data root, not the worktree's.

    Two items in two sessions found an artifact STRANDED in a worktree that later disappeared
    (`MA28_CARD.json`, then `I2_BURN_IN_CENSUS.json`). A worktree-run script must resolve to the
    primary root or its output does not survive.
    """
    if explicit:
        return explicit
    cands = [os.path.join(HERE, "data")]
    marker = os.path.join(".claude", "worktrees")
    if marker in HERE:
        cands.append(os.path.join(HERE.split(marker)[0].rstrip(os.sep), "data"))
    for c in cands:
        if _populated(c):
            return c
    raise SystemExit(
        "cannot resolve a data root holding free_analysis/%s (tried %s). `data/` is gitignored, "
        "so a fresh checkout has none; pass --data-root." % (REQUIRED, cands))


def _load(root):
    tp = os.path.join(root, "free_analysis", "V6OPT_STAGE2_TRADES.pkl")
    ep = os.path.join(root, "free_analysis", "V6OPT_STAGE1_EVENTS.pkl")
    jp = os.path.join(root, "free_analysis", "V6OPT_STAGE2.json")
    for p in (tp, ep, jp):
        if not os.path.isfile(p):
            raise SystemExit(
                "REFUSING: %s is absent. This validation exists to compare against a BANKED "
                "figure; running it without one would pass vacuously, which is the failure it "
                "is built to prevent." % os.path.basename(p))
    trades = pd.read_pickle(tp)
    events = pd.read_pickle(ep)
    with io.open(jp, encoding="utf-8") as fh:
        pub = json.load(fh)
    return trades, events, pub


def _join(trades, events):
    """Recover strike and credit for each settled trade from the stage-1 event rows."""
    e = events[["date", "ticker", "strike", "credit"]].copy()
    e["date"] = pd.to_datetime(e["date"])
    t = trades.copy()
    t["entry"] = pd.to_datetime(t["entry"])
    m = t.merge(e, left_on=["ticker", "entry"], right_on=["ticker", "date"], how="left")
    matched = int(m["strike"].notna().sum())
    if matched == 0:
        raise SystemExit("REFUSING: the strike/credit join matched ZERO rows. A comparison over "
                         "nothing scores perfectly, which is MB21's C1 defect.")
    return m, matched


def _bars(root, tickers):
    """{ticker: {date -> (raw_close, close)}} from the prepared bars cache."""
    out = {}
    d = os.path.join(root, "bulk", "prepared", "bars")
    if not os.path.isdir(d):
        return out
    for tk in sorted(set(tickers)):
        p = os.path.join(d, "%s.pkl" % tk)
        if not os.path.isfile(p):
            continue
        try:
            b = pd.read_pickle(p)
        except Exception:                                            # noqa: BLE001
            continue
        dates = [str(x)[:10] for x in (b.get("date") or [])]
        raw = list(b.get("raw_close") or [])
        adj = list(b.get("close") or [])
        if not dates or len(raw) != len(dates) or len(adj) != len(dates):
            continue
        out[tk] = {dt: (r, a) for dt, r, a in zip(dates, raw, adj)}
    return out


# ------------------------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=None)
    args = ap.parse_args()
    root = _data_root(args.data_root)
    print("data root: %s" % root)

    trades, events, pub = _load(root)
    m, matched = _join(trades, events)
    rows = m.dropna(subset=["strike", "credit", "spot_expiry"])
    n = len(rows)
    print("banked trades %d, strike/credit matched %d, scoreable %d" % (len(trades), matched, n))

    # ---- C1  B7 fidelity on real rows -----------------------------------------------------
    dev_ret, dev_pnl, mism, compared = [], [], 0, 0
    worthless, assigned_n = 0, 0
    for r in rows.itertuples():
        mine = SB.settle_short(strike=float(r.strike), credit=float(r.credit),
                               spot_at_expiry=float(r.spot_expiry), right="put",
                               spot_basis=SB.AS_TRADED, method=SB.CASH_SECURED_PUT)
        ref = settle_put(float(r.strike), float(r.credit), float(r.spot_expiry))
        compared += 1
        dev_ret.append(abs(mine["ret_on_secured"] - ref["ret_on_strike"]))
        dev_pnl.append(abs(mine["pnl_per_share"] - ref["pnl_per_share"]))
        if mine["assigned"] != ref["assigned"] or mine["assigned"] != bool(r.assigned):
            mism += 1
        # against V6-OPT's own PUBLISHED per-trade return, not merely against settle_put
        dev_ret.append(abs(mine["ret_on_secured"] - float(r.ret_on_strike)))
        if mine["assigned"]:
            assigned_n += 1
        else:
            worthless += 1
    if compared == 0:
        raise SystemExit("REFUSING: C1 compared zero rows (MB21 C1).")
    c1 = {"compared": compared, "max_abs_delta_ret": float(max(dev_ret)),
          "max_abs_delta_pnl": float(max(dev_pnl)), "assignment_mismatches": int(mism),
          "assigned": assigned_n, "expired_worthless": worthless,
          "ok": bool(max(dev_ret) == 0.0 and max(dev_pnl) == 0.0 and mism == 0)}
    print("C1 fidelity: %d rows, max |delta| ret %.3e pnl %.3e, mismatches %d -> %s"
          % (compared, c1["max_abs_delta_ret"], c1["max_abs_delta_pnl"], mism,
             "OK" if c1["ok"] else "FAIL"))

    # ---- C2  it is V6-OPT's own book -------------------------------------------------------
    pub_n = int(((pub.get("arms") or {}).get("A_healthy_csp") or {}).get("n") or 0)
    c2 = {"published_n": pub_n, "trades_in_pkl": int(len(trades)),
          "ok": bool(pub_n > 0 and pub_n == len(trades))}
    print("C2 published n %d vs banked %d -> %s" % (pub_n, len(trades),
                                                    "OK" if c2["ok"] else "FAIL"))

    # ---- C3  the split trap, measured ------------------------------------------------------
    bars = _bars(root, rows["ticker"].tolist())
    checked = flips = 0
    worst = None
    ratios = []
    for r in rows.itertuples():
        day = str(pd.Timestamp(r.expiry))[:10]
        rec = (bars.get(r.ticker) or {}).get(day)
        if not rec:
            continue
        raw, adj = rec
        if not (np.isfinite(raw) and np.isfinite(adj) and raw > 0 and adj > 0):
            continue
        checked += 1
        ratios.append(abs(adj / raw - 1.0))
        a_raw = SB.assignment_at_expiry(spot_at_expiry=float(raw), strike=float(r.strike),
                                        right="put", spot_basis=SB.AS_TRADED)
        # the DEFECT, reproduced deliberately: the adjusted number passed off as as-traded
        a_adj = SB.assignment_at_expiry(spot_at_expiry=float(adj), strike=float(r.strike),
                                        right="put", spot_basis=SB.AS_TRADED)
        if a_raw["assigned"] != a_adj["assigned"]:
            flips += 1
            gap = abs(a_adj["intrinsic_obligation"] - a_raw["intrinsic_obligation"]) / r.strike
            if worst is None or gap > worst[0]:
                worst = (float(gap), r.ticker, day, float(raw), float(adj), float(r.strike))
    c3 = {"checked": checked, "verdict_flips": flips,
          "flip_share": (flips / checked) if checked else None,
          "median_abs_basis_gap": (float(np.median(ratios)) if ratios else None),
          "share_gap_over_5pct": (float(np.mean([x > 0.05 for x in ratios])) if ratios else None),
          "worst_flip": ({"obligation_gap_frac_of_strike": worst[0], "ticker": worst[1],
                          "expiry": worst[2], "raw_close": worst[3], "adjusted_close": worst[4],
                          "strike": worst[5]} if worst else None),
          "live_on_this_book": bool(flips > 0)}
    print("C3 split trap: %d rows checked, %d assignment verdicts FLIP under the adjusted basis "
          "(%s)" % (checked, flips, "LIVE" if flips else "not triggered on this book"))
    if checked == 0:
        print("    C3 is VACUOUS rather than passing - the bars cache reached none of these "
              "(ticker, expiry) pairs. A filter that never ran and a filter that ran and found "
              "nothing must not read the same (O21-D2's C5 precedent).")

    # ---- C4  the MA36 mirror on real rows --------------------------------------------------
    bad = [float(r.strike) for r in rows.itertuples()
           if not bool(r.assigned)
           and SB.settle_short(strike=float(r.strike), credit=float(r.credit),
                               spot_at_expiry=float(r.spot_expiry), right="put",
                               spot_basis=SB.AS_TRADED,
                               method=SB.CASH_SECURED_PUT)["intrinsic_obligation"] != 0.0]
    ma36_cost = worthless          # trades MA36's long rule would have booked at -100%
    c4 = {"worthless_expiries": worthless, "obligation_nonzero_on_any": len(bad),
          "trades_ma36_long_rule_would_book_at_minus_100pct": ma36_cost,
          "ok": bool(worthless > 0 and not bad)}
    print("C4 MA36 mirror: %d worthless expiries, all owe exactly zero -> %s  (inheriting the "
          "long-side rule would have booked every one of them at -100%%)"
          % (worthless, "OK" if c4["ok"] else "FAIL"))

    # ---- C5  early-assignment census, DIAGNOSTIC ONLY --------------------------------------
    divs = DIV.load_dividends(root)
    ex_hits = with_divs = 0
    for r in rows.itertuples():
        if not divs.get(r.ticker):
            continue
        with_divs += 1
        if DIV.dividends_between(divs, r.ticker, r.entry, r.expiry):
            ex_hits += 1
    c5 = {"dividend_table_names": len(divs), "trades_with_a_dividend_history": with_divs,
          "trades_spanning_an_ex_date": ex_hits,
          "vacuous": bool(with_divs == 0),
          "note": ("DIAGNOSTIC, NO VERDICT. These are short PUTS, and a dividend inside the "
                   "window DISCOURAGES early exercise of a put -- the census sizes the exposure "
                   "for the CALL books (F-7, F-18) and says nothing about these rows. The flag "
                   "reports rationality, never a probability, so no assignment rate may be read "
                   "off it.")}
    print("C5 early-assignment census: %d of %d trades span an ex-date%s"
          % (ex_hits, with_divs, "  (VACUOUS - no dividend table)" if not with_divs else ""))

    out = {"item": "S3-I3", "instrument": "valuation/edge/short_book.py",
           "trials": 0, "class": "FIXED",
           "interface": "PREREG_DRAFT_fleet_harness.md section 1.4 (S3-I1)",
           "corpus": "V6OPT_STAGE2_TRADES.pkl x V6OPT_STAGE1_EVENTS.pkl",
           "controls": {"C1_b7_fidelity": c1, "C2_same_book": c2, "C3_split_trap": c3,
                        "C4_ma36_mirror": c4, "C5_early_assignment_census": c5},
           "all_controls_pass": bool(c1["ok"] and c2["ok"] and c4["ok"]),
           "no_outcome_relationship_scored": ("ret_on_strike is compared FOR EQUALITY against a "
                                              "published figure and is never read for a verdict")}
    dest = os.path.join(root, "free_analysis", "S3I3_SHORT_BOOK_VALIDATION.json")
    with io.open(dest, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=2, sort_keys=True))
    print("\nwrote %s" % dest)
    print("ALL GATING CONTROLS PASS" if out["all_controls_pass"] else "CONTROLS FAILED")
    return 0 if out["all_controls_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
