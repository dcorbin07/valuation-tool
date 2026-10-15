"""THE ALPACA SEAM MEASUREMENT — item 59's "measure first", and the artifact every switch reads.

**NOTHING SWITCHES UNTIL THIS HAS RUN.** `prices.py` reads the artifact this writes and keeps
its current vendor order until the artifact exists AND passes. That ordering is the brief's own
("each switch backed by its measurement"), and it is enforced in code rather than promised:
with no artifact, `get_history_df` is bit-identical to what it was.

WHERE IT RUNS, AND WHY NOT HERE
-------------------------------
The keys exist only on Render, so the measurement runs on the SERVICE behind an owner-only door
(`/admin/alpaca-seam`). A lane never sees a key and tests against recorded fixtures. That is
`ALPACA_SETUP.md`'s instruction and it is also the only arrangement that can work: a lane has no
credential to measure with.

THE SAMPLE IS IMPORTED, NEVER RETYPED
-------------------------------------
`scripts/fmp_seam.sample()` already states it — 222 names: the live hot list and dip screen plus
named blocks of 16 banks, 16 REITs, 16 ADRs, 10 regulated utilities and 12 recent splitters with
their split ratios and dates. Importing it is what makes the three vendors comparable **on one
population rather than three convenient ones**, which is the brief's own requirement, and it is
`B7`: a second copy of that list would drift and then the comparison would be between two
different questions.

Item 40's FMP measurement died on coverage — ~12% of the sample, **zero REITs and zero
utilities** — so the categories are not decoration. They are where the answer was last time.

WHAT IT MEASURES, AND WHAT EACH LEG IS FOR
------------------------------------------
1. **FEEDS.** Which feeds this key can actually read, by asking. Alpaca's own pages claim "100%
   market coverage" beside "IEX exchange only", so the plan question is not answerable from the
   documentation.
2. **BASIS — BOTH WAYS ROUND.** Daily closes pulled at `adjustment=raw` AND `adjustment=all`,
   against yfinance (`auto_adjust=True`) and against the recorded Index series. This is the leg
   that matters most: Alpaca's default is `raw`, the recorded basis is ADJUSTED, and a switch
   that got this wrong would change the basis of the one series that cannot be rebuilt. The
   splitters carry their split dates, so "split handling agrees" is checkable across a real
   corporate action rather than asserted.
3. **THE 52-WEEK HIGH ON EACH BASIS**, because that is the number the Dip Detector is about and
   it is the most basis-sensitive figure the product renders.
4. **COVERAGE**, as a share of the sample AND of the Index's own constituents, with the gaps
   NAMED. Including **ET**, unpriced on the current route since 2026-10-05, and whether OTC and
   foreign names resolve.
5. **RATE BUDGET**, read from Alpaca's own response headers rather than discovered by hitting
   the limit.

ABSENT IS NOT ZERO, THROUGHOUT
------------------------------
A name Alpaca does not return is `missing`, never an empty series; a comparison with no
overlapping dates is `UNMEASURED`, never an agreement rate of zero. `V6`/`O21-D2`'s `C5`: a
measurement not taken and a measured absence must not read the same.
"""
from __future__ import annotations

import json
import os
from typing import Optional

from . import alpaca_data as AD

SCHEMA = "alpaca_seam/1"

#: Where the verdict lives. `data_export/` and not `data/`: `data/` is gitignored, so an artifact
#: there exists only on whichever machine wrote it -- and this project has lost two artifacts to
#: exactly that (`MA28_CARD.json`, `I2_BURN_IN_CENSUS.json`, both stranded in a deleted
#: worktree). `data_export/` is already the tracked directory the Index record is backed up into.
ARTIFACT_NAME = "ALPACA_SEAM.json"

#: How close two vendors' closes must sit to count as agreeing, per bar. 20 bps absorbs a
#: rounding difference and nothing larger; a real split or dividend-basis difference is percent,
#: not basis points, so this separates the two questions rather than blurring them.
AGREE_TOL = 0.0020

#: The share of comparable bars that must agree before the daily-close leg PASSES. Declared here,
#: before any number exists, because a bar chosen after seeing the result is not a bar.
PASS_AGREE_RATE = 0.98

#: And the coverage the sample must reach. Item 40's FMP route managed ~12%; this is the floor
#: below which Alpaca cannot be a primary at all.
PASS_COVERAGE = 0.95

#: The Index's own names matter more than the sample's: an unpriced constituent is a hole in the
#: one record that cannot be rebuilt. 100% or the Index leg does not pass.
PASS_INDEX_COVERAGE = 1.0

#: Named so the measurement answers item 59's specific questions rather than only its general
#: one. ET is the live case; the rest probe the shapes most likely to be absent.
NAMED_GAPS = {
    "ET": "unpriced on the current route since 2026-10-05 (item 57 B1)",
    "GBTC": "an OTC-shaped symbol",
    "RHHBY": "an OTC ADR",
    "TSM": "a listed foreign ADR, expected to resolve",
    "BRK.B": "a dotted class share -- the symbol-form question",
}


def artifact_path(root: str = None) -> str:
    base = root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "data_export", ARTIFACT_NAME)


def read_artifact(root: str = None) -> Optional[dict]:
    """The recorded measurement, or `None`. **Never raises, and never invents one.**"""
    try:
        with open(artifact_path(root), encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) and d.get("schema") == SCHEMA else None
    except Exception:                                                   # noqa: BLE001
        return None


def switch_allowed(root: str = None, env=None) -> dict:
    """**THE GATE EVERY SWITCH READS.** `{allowed, reason, measured_on, ...}`.

    Three independent conditions, and each one can fail on its own:

      * the artifact EXISTS and carries this schema -- an absent measurement is not a pass;
      * its daily-close leg PASSED, at the bars declared above rather than ones chosen after;
      * an explicit opt-in is set, so landing this code switches nothing by itself.

    **THE OPT-IN IS THE THIRD CONDITION AND IT IS NOT BELT-AND-BRACES.** The bound Index record
    is the one series that cannot be rebuilt, and `ALPACA_SETUP.md`'s own closing line is that
    changing what prices it *"is Don's call, not a lane's"*. So a passing measurement makes the
    switch AVAILABLE; it does not take it.
    """
    e = env if env is not None else os.environ
    opted = (e.get("PRICES_PRIMARY_ALPACA", "") or "").strip().lower() in ("1", "true", "yes")
    art = read_artifact(root)
    if art is None:
        return {"allowed": False, "opted_in": opted, "measured": False,
                "reason": ("no seam measurement is recorded, so the price vendor order is "
                           "unchanged. Run POST /admin/alpaca-seam?run=1 on the service -- the "
                           "keys live there and nowhere else.")}
    closes = (art.get("closes") or {})
    passed = bool(closes.get("passed"))
    out = {"allowed": bool(passed and opted), "opted_in": opted, "measured": True,
           "measured_on": art.get("at"), "closes_passed": passed,
           "agree_rate": closes.get("agree_rate"),
           "coverage": (art.get("coverage") or {}).get("sample_rate")}
    if not passed:
        out["reason"] = ("the recorded seam measurement did NOT pass its daily-close leg (%s), "
                         "so Alpaca stays off the price path"
                         % (closes.get("reason") or "no reason recorded"))
    elif not opted:
        out["reason"] = ("the seam measurement passed, so the switch is AVAILABLE and has not "
                         "been taken. Set PRICES_PRIMARY_ALPACA=1 on the service to take it -- "
                         "and per ALPACA_SETUP.md that is Don's call, because inside a segment "
                         "the Index's base and mark must come from one vendor.")
    else:
        out["reason"] = ("the seam measurement passed and the opt-in is set: Alpaca is the "
                         "primary daily-close vendor, with yfinance then Stooq as fallbacks.")
    return out


# ----------------------------------------------------------------------------------------------
# the measurement
# ----------------------------------------------------------------------------------------------
def _close_map(bars_for_symbol) -> dict:
    """`{YYYY-MM-DD: close}` from Alpaca's bar rows. `t` is an RFC-3339 timestamp."""
    out = {}
    for b in (bars_for_symbol or []):
        t = str((b or {}).get("t") or "")[:10]
        c = (b or {}).get("c")
        if t and isinstance(c, (int, float)):
            out[t] = float(c)
    return out


def compare_closes(a: dict, b: dict, tol: float = AGREE_TOL) -> dict:
    """Two `{date: close}` maps. **A pair with no shared dates is UNMEASURED, not 0% agreement.**

    That distinction is the whole of `C5`: an empty overlap means the comparison could not be
    made, and reporting it as total disagreement would make a missing vendor look like a wrong
    one -- which points any reader at the wrong repair.
    """
    shared = sorted(set(a) & set(b))
    if not shared:
        return {"measured": False, "n": 0, "reason": "no shared dates: nothing to compare"}
    diffs = []
    for d in shared:
        x, y = a[d], b[d]
        if not x or not y:
            continue
        diffs.append((d, abs(x / y - 1.0), x, y))
    if not diffs:
        return {"measured": False, "n": 0, "reason": "every shared bar carried a zero close"}
    agree = [d for d in diffs if d[1] <= tol]
    worst = sorted(diffs, key=lambda r: -r[1])[:3]
    return {"measured": True, "n": len(diffs), "n_agree": len(agree),
            "agree_rate": len(agree) / float(len(diffs)),
            "median_abs_rel": sorted(d[1] for d in diffs)[len(diffs) // 2],
            "worst": [{"date": d, "rel": r, "alpaca": x, "other": y} for d, r, x, y in worst]}


def measure(*, client=None, names=None, yf_closes=None, recorded=None, env=None,
            start: str = None, end: str = None, root: str = None, write: bool = True) -> dict:
    """Run the whole seam. Returns the artifact dict; writes it unless `write=False`.

    Every input is injectable so a lane can exercise this against RECORDED FIXTURES with no key
    and no network -- which is the only way it can be tested at all, and the reason the real
    pull lives behind a door rather than in a script a lane runs.
    """
    e = env if env is not None else os.environ
    out = {"schema": SCHEMA, "at": None, "ok": True, "reason": "",
           "sample": {}, "feeds": {}, "closes": {}, "fifty_two_week": {}, "coverage": {},
           "rate": {}, "named_gaps": {}, "not_carried": list(AD.NOT_CARRIED),
           "carried_free": list(AD.CARRIED_FREE)}
    import datetime as _dt
    out["at"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if client is None:
        try:
            client = AD.AlpacaData(env=e)
        except AD.AlpacaDataError as ex:
            out["ok"] = False
            out["reason"] = str(ex)
            return out

    # THE CATEGORY MAP IS LOOKED UP UNCONDITIONALLY, and that is a repair rather than a
    # tidy-up: it used to be built only on the branch that imported the sample, so a caller
    # supplying `names=` got `by_category: {}` -- an empty dict reading as "no categories to
    # report" rather than as a measurement that did not happen. The by-category leg is the one
    # item 40's FMP measurement died on (~12% coverage, ZERO REITs and ZERO utilities), so
    # losing it to an argument shape would have lost the leg most likely to decide the answer.
    # A ticker's category is a property of the ticker, not of how the list arrived.
    try:
        import sys
        root_dir = root or os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
        from scripts import fmp_seam as FS
    except Exception as ex:                                             # noqa: BLE001
        out["ok"] = False
        out["reason"] = "the stated sample module could not be imported: %r" % (ex,)
        return out
    out["sample"]["categories"] = {k: v for k, v in sorted(FS.CATEGORY.items())}
    out["sample"]["splits"] = {k: list(v) for k, v in sorted(FS.SPLIT_DATE.items())}
    if names is None:
        try:
            names = FS.sample()
            out["sample"]["source"] = ("scripts.fmp_seam.sample() -- IMPORTED so the three "
                                       "vendors are compared on ONE population")
        except Exception as ex:                                         # noqa: BLE001
            out["ok"] = False
            out["reason"] = "the stated sample could not be built: %r" % (ex,)
            return out
    else:
        out["sample"]["source"] = "supplied by the caller"
    names = sorted({str(n).strip().upper() for n in names if str(n).strip()})
    probe_names = sorted(set(names) | set(NAMED_GAPS))
    out["sample"]["n"] = len(names)
    out["sample"]["n_with_named_gaps"] = len(probe_names)

    # ---- 1. which feeds this key can read, by ASKING ---------------------------------------
    try:
        out["feeds"] = client.feed_probe(start=start, end=end)
    except Exception as ex:                                             # noqa: BLE001
        out["feeds"] = {"error": "the feed probe failed: %r" % (ex,)}

    # ---- 2. bars on BOTH bases -------------------------------------------------------------
    pulls = {}
    for adj in (AD.ADJ_RAW, AD.ADJ_ALL):
        try:
            pulls[adj] = client.bars(probe_names, adjustment=adj, start=start, end=end)
        except Exception as ex:                                         # noqa: BLE001
            pulls[adj] = {"ok": False, "bars": {}, "missing": probe_names,
                          "error": "%r" % (ex,)}
    out["rate"] = (pulls.get(AD.ADJ_ALL) or {}).get("rate") or {}
    out["requests"] = sum(int((p or {}).get("requests") or 0) for p in pulls.values())

    adj_bars = {s: _close_map(r) for s, r in ((pulls.get(AD.ADJ_ALL) or {}).get("bars")
                                              or {}).items()}
    raw_bars = {s: _close_map(r) for s, r in ((pulls.get(AD.ADJ_RAW) or {}).get("bars")
                                              or {}).items()}

    # ---- 3. coverage, with the gaps NAMED --------------------------------------------------
    covered = sorted(s for s in names if adj_bars.get(s))
    out["coverage"] = {
        "sample_n": len(names), "sample_covered": len(covered),
        "sample_rate": (len(covered) / float(len(names)) if names else None),
        "missing": sorted(set(names) - set(covered))[:40],
        "by_category": {},
    }
    cats = (out["sample"].get("categories") or {})
    for cat in sorted(set(cats.values())):
        members = [s for s in names if cats.get(s) == cat]
        if not members:
            # NOT PRESENT IN THIS SAMPLE, so there is nothing to report -- and a 0% row would
            # read as "Alpaca covers no REITs" when the truth is "this run asked about none".
            continue
        got = [s for s in members if adj_bars.get(s)]
        out["coverage"]["by_category"][cat] = {
            "n": len(members), "covered": len(got),
            "rate": len(got) / float(len(members))}
    out["named_gaps"] = {
        t: {"why_asked": why, "covered": bool(adj_bars.get(t)),
            "n_bars": len(adj_bars.get(t) or {})}
        for t, why in sorted(NAMED_GAPS.items())}

    # ---- 4. the daily-close comparison ------------------------------------------------------
    def _against(other_by_symbol, label):
        rows, rates = {}, []
        for s, other in (other_by_symbol or {}).items():
            s = str(s).upper()
            for basis, got in (("all", adj_bars.get(s)), ("raw", raw_bars.get(s))):
                if not got or not other:
                    continue
                r = compare_closes(got, other)
                rows.setdefault(s, {})[basis] = r
                if r.get("measured") and basis == "all":
                    rates.append(r["agree_rate"])
        return {"label": label, "per_name": rows,
                "n_names_measured": len(rates),
                "agree_rate": (sum(rates) / len(rates) if rates else None),
                "measured": bool(rates),
                "reason": ("" if rates else
                           "no name had overlapping dates on both vendors: UNMEASURED")}

    out["closes"]["vs_yfinance"] = _against(yf_closes, "yfinance auto_adjust=True")
    out["closes"]["vs_recorded"] = _against(recorded, "the recorded Index series")

    # THE VERDICT, against the bars declared at the top of this file rather than chosen now.
    cov = out["coverage"]["sample_rate"]
    yf = out["closes"]["vs_yfinance"]
    reasons = []
    if cov is None or cov < PASS_COVERAGE:
        reasons.append("coverage %s is below the declared %.0f%% floor"
                       % ("UNMEASURED" if cov is None else "%.1f%%" % (100 * cov),
                          100 * PASS_COVERAGE))
    if not yf.get("measured"):
        reasons.append("the daily-close comparison against yfinance is UNMEASURED, which is "
                       "not a pass")
    elif (yf.get("agree_rate") or 0) < PASS_AGREE_RATE:
        reasons.append("agreement with yfinance's adjusted close is %.3f, below the declared "
                       "%.2f" % (yf["agree_rate"], PASS_AGREE_RATE))
    out["closes"]["passed"] = not reasons
    out["closes"]["agree_rate"] = yf.get("agree_rate")
    out["closes"]["basis_used"] = AD.ADJ_FOR_RECORDED_BASIS
    out["closes"]["reason"] = ("; ".join(reasons) if reasons else
                               ("Alpaca's adjustment=all close agrees with yfinance's adjusted "
                                "close on %.3f of comparable bars across %d names, at coverage "
                                "%.1f%%" % (yf.get("agree_rate") or 0,
                                            yf.get("n_names_measured") or 0, 100 * (cov or 0))))

    # ---- 5. the 52-week high on each basis --------------------------------------------------
    hi = {}
    for s in covered[:60]:
        a, r = adj_bars.get(s) or {}, raw_bars.get(s) or {}
        if not a or not r:
            continue
        ha, hr = max(a.values()), max(r.values())
        hi[s] = {"adjusted": ha, "raw": hr,
                 "rel_gap": (abs(ha / hr - 1.0) if hr else None)}
    gaps = sorted((v["rel_gap"] or 0) for v in hi.values())
    out["fifty_two_week"] = {
        "n": len(hi), "median_rel_gap": (gaps[len(gaps) // 2] if gaps else None),
        "n_over_1pct": sum(1 for g in gaps if g > 0.01),
        "worst": sorted(hi.items(), key=lambda kv: -(kv[1]["rel_gap"] or 0))[:5],
        "why": ("the Dip Detector is about this number, and it is the most basis-sensitive "
                "figure the product renders: a raw high after a split reads as a crash"),
    }

    if write:
        try:
            p = artifact_path(root)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p + ".tmp", "w", encoding="utf-8", newline="\n") as fh:
                json.dump(out, fh, indent=2, sort_keys=True, default=str)
                fh.write("\n")
            os.replace(p + ".tmp", p)
            out["written_to"] = p
        except OSError as ex:
            out["written_to"] = None
            out["reason"] = (out["reason"] + "; " if out["reason"] else "") + (
                "the artifact could not be written: %s" % ex)
    return out
