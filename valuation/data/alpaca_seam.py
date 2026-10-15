"""THE ALPACA SEAM MEASUREMENT — and item 62's repair of it.  [items 59, 62]

**ITEM 62: THE FIRST VERSION PASSED ON THREE BARS.** Don ran it on 2026-10-15 at 22:27Z. It
reported the daily-close leg PASSED at `agree_rate 1.000` "across 3 names" — and those three
names were ET, GBTC and TSM, **one bar each, all dated 2026-10-15**, on a run that spent six
requests in total. That is three quotes on one day, reported as a daily-close comparison of a
222-name sample.

FOUR DEFECTS OF MINE PRODUCED IT, and the first explains most of the rest:

  1. **NO DATE WINDOW WAS REQUESTED.** `measure()` was called without `start` or `end`, so
     `client.bars(..., start=None, end=None)` asked Alpaca for no window and got the latest bar.
     One bar per name is why the comparison had one date — **and it is the likeliest reason
     AVB, BK and EQR read as "missing" while being NYSE-listed**: on the free IEX feed a single
     day's bar can be absent for a name that did not print on IEX, and a one-day window turns
     that into "not covered". A real window answers it, and the artifact now records per-name
     bar counts so the next run says which it was rather than leaving it to be guessed.
  2. **THE yfinance LEG COVERED FIVE NAMES.** The door computed its probe list as
     `(missing)[:0] or list(NAMED_GAPS)` — a dead `[:0]` slice I left in, so it ALWAYS fell
     back to the five named-gap probes and then took `[:12]` of them.
  3. **`recorded` WAS NEVER BUILT.** The door declared `recorded = {}` and never filled it, so
     `vs_recorded` — the leg that matters most for switching the Index record — could only ever
     report UNMEASURED. And the switch reported "available" without it.
  4. **`measure()` RAN TWICE**, which is where most of those six requests went.

AND THE DEEP ONE: **THE BAR WAS A RATE WITH NO FLOOR UNDER IT.** 98% agreement is a sensible
threshold and it says nothing about how much was compared; three bars at 100% clear it. A rate
needs a quantity beside it or it is not evidence. So the floors below are on EVIDENCE as well as
on agreement, they are declared with their reasons, and below any of them the result is
**UNMEASURED — never passed**.

WHERE IT RUNS, AND WHY NOT HERE
-------------------------------
The keys exist only on Render, so the measurement runs on the SERVICE behind an owner-only door
(`/admin/alpaca-seam`). A lane never sees a key and tests against recorded fixtures. The bound
Index record is on the service too, which is the other half of why `vs_recorded` can only be
measured there.

THE PULL IS STORED AND RESUMABLE, WHICH IS NOT A CONVENIENCE
------------------------------------------------------------
250 trading days across 222 names is ~55,000 bars from Alpaca and 222 history calls to Yahoo.
That does not reliably finish inside one HTTP request, and a measurement that half-finishes and
then reports a rate over whatever it got is the defect this file exists to repair. So the raw
pull is written to disk as it goes, a re-run CONTINUES it, and the analysis refuses until the
pull is complete. `FMP_SEAM`'s own rule: *"the raw pull is stored so the analysis can be re-run
without spending anything."*

THE SAMPLE IS IMPORTED, NEVER RETYPED
-------------------------------------
`scripts/fmp_seam.sample()` states it — 222 names: the live hot list and dip screen plus named
blocks of 16 banks, 16 REITs, 16 ADRs, 10 regulated utilities and 12 recent splitters with their
split ratios and dates. Importing it is what makes the three vendors comparable **on one
population**, and `B7`: a second copy would drift.

ABSENT IS NEVER ZERO
--------------------
A name Alpaca does not return is `missing`, never an empty series; a comparison with no
overlapping dates is UNMEASURED, never an agreement rate of zero; and an UNMEASURED leg is never
a pass. `V6`/`O21-D2`'s `C5`.
"""
from __future__ import annotations

import json
import os
from typing import Optional

from . import alpaca_data as AD

SCHEMA = "alpaca_seam/2"

#: Where the verdict lives. `data_export/` and not `data/`: `data/` is gitignored, so an artifact
#: there exists only on whichever machine wrote it -- and this project has lost two artifacts to
#: exactly that (`MA28_CARD.json`, `I2_BURN_IN_CENSUS.json`, both stranded in a deleted
#: worktree). `data_export/` is already the tracked directory the Index record is backed up into.
ARTIFACT_NAME = "ALPACA_SEAM.json"

#: And the raw pull, beside it, so the analysis can be re-run without spending a request.
RAW_NAME = "ALPACA_SEAM_RAW.json"

# ---------------------------------------------------------------------------------------------
# THE WINDOW, AND THE FLOORS. Declared here, with reasons, before any number exists.
# ---------------------------------------------------------------------------------------------
#: The brief's own figure: "at least 250 trading days". A year of history is the shortest window
#: in which a dividend basis difference is observable on most payers, which is the question the
#: two bases exist to answer.
WINDOW_TRADING_DAYS = 250

#: The calendar span that reliably contains it. 250 trading days is ~358 calendar days; 400 gives
#: room for holidays and for a vendor whose first bar lands a few sessions late.
WINDOW_CALENDAR_DAYS = 400

#: How close two vendors' closes must sit to count as agreeing, per bar. 20 bps absorbs a
#: rounding difference and nothing larger; a real split or dividend-basis difference is percent,
#: not basis points, so this separates the two questions rather than blurring them.
AGREE_TOL = 0.0020

#: THE AGREEMENT BAR. Unchanged from item 59, because it was never the thing that was wrong.
PASS_AGREE_RATE = 0.98

#: THE EVIDENCE FLOORS -- ITEM 62'S ACTUAL FIX. A rate without a quantity beside it is not
#: evidence: the first run cleared 0.98 on THREE BARS.
#:
#: 200 names of the 222-name sample, because the sample's whole point is its composition (16
#: banks, 16 REITs, 16 ADRs, 10 utilities, 12 splitters) and a figure measured on a convenient
#: subset is the FMP measurement's own failure -- it died at ~12% coverage with zero REITs and
#: zero utilities, which a name-count floor alone would not have caught either, so coverage is
#: ALSO reported by category.
MIN_NAMES_FOR_PASS = 200

#: 40,000 comparable bars: 200 names x 200 bars. It is the brief's figure and it is the product
#: of the two floors beside it, so no single leg can satisfy it alone -- 3 names x 13,000 bars
#: would clear a bar count and fail the name count, and 220 names x 1 bar the reverse.
MIN_BARS_FOR_PASS = 40000

#: And per name: a name is COVERED only if Alpaca returned a real series for it, not one bar.
#: 200 of ~250 trading days allows for a recent listing or a halt without admitting a quote.
MIN_BARS_PER_NAME = 200

#: `vs_recorded` has no percentage floor, deliberately: **EVERY recorded row must be measured.**
#: The bound Index record is the one series that cannot be rebuilt, and a vendor that reproduces
#: three rows of four says nothing about the fourth. The brief's own words: "every recorded row".
RECORDED_REQUIRE_ALL_ROWS = True

#: How far a recomputed row may sit from the recorded one, in basis points of the percentage
#: figures, before the row counts as DISAGREEING. 5 bps is a hair on a cumulative percentage
#: and far below the ~0.02pp seam this project already measured between its own two price
#: routes, so this separates "the same arithmetic on the same basis" from "a different basis".
RECORDED_TOL_BPS = 5.0

# How often the stored pull is flushed to disk, in names. See `pull()` for the trade.
FLUSH_EVERY = 10

#: Named so the measurement answers item 59's and item 62's specific questions rather than only
#: the general one.
NAMED_GAPS = {
    "ET": "unpriced on the current route since 2026-10-05 (item 57 B1)",
    "GBTC": "an OTC-shaped symbol",
    "RHHBY": "an OTC ADR",
    "TSM": "a listed foreign ADR, expected to resolve",
    "BRK.B": "a dotted class share -- the symbol-form question",
    # ITEM 62: the three NYSE-listed names the first run reported missing. Asked by name so the
    # next run answers it rather than leaving the coverage figure untrustworthy.
    "AVB": "NYSE-listed REIT, reported MISSING by the first run (item 62)",
    "BK": "NYSE-listed bank, reported MISSING by the first run (item 62)",
    "EQR": "NYSE-listed REIT, reported MISSING by the first run (item 62)",
}

#: A name with a dividend INSIDE the window, so "raw equals adjusted on every name" can be told
#: apart from "both bases returned the same series". The first run reported a median 52-week-high
#: gap of exactly zero across 60 names and could not distinguish those two.
DIVIDEND_CONTROL = ("KO", "JNJ", "PG", "XOM", "T", "O", "NEE", "DUK", "JPM", "BK")


def artifact_path(root: str = None) -> str:
    base = root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "data_export", ARTIFACT_NAME)


def raw_path(root: str = None) -> str:
    base = root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "data_export", RAW_NAME)


def _read_json(path) -> Optional[dict]:
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else None
    except Exception:                                                   # noqa: BLE001
        return None


def _write_json(path, doc, *, sort_keys: bool = True) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, sort_keys=sort_keys, default=str)
            fh.write("\n")
        os.replace(path + ".tmp", path)
        return True
    except OSError:
        return False


def read_artifact(root: str = None) -> Optional[dict]:
    """The recorded measurement, or `None`. **Never raises, and never invents one.**

    A document carrying an OLDER schema reads as absent, which is how item 59's three-bar pass
    stops being able to license anything: it was written as `alpaca_seam/1` and this is `/2`.
    """
    d = _read_json(artifact_path(root))
    return d if (d or {}).get("schema") == SCHEMA else None


def read_raw(root: str = None) -> dict:
    d = _read_json(raw_path(root)) or {}
    if d.get("schema") != SCHEMA:
        return {"schema": SCHEMA, "alpaca": {}, "yf": {}, "window": {}, "requests": 0}
    for k in ("alpaca", "yf", "window"):
        d.setdefault(k, {})
    d.setdefault("requests", 0)
    return d


def switch_allowed(root: str = None, env=None) -> dict:
    """**THE GATE EVERY SWITCH READS.** `{allowed, reason, ...}`.

    FOUR independent conditions, and each can fail on its own:

      * the artifact EXISTS and carries THIS schema -- an absent measurement is not a pass, and
        item 59's `/1` artifact is not one either;
      * the daily-close leg PASSED, which now requires its evidence floors as well as its
        agreement rate;
      * **`vs_recorded` PASSED** -- item 62's requirement. The first version allowed the switch
        to read "available" while the leg that compares against the bound Index record was
        UNMEASURED, which is precisely backwards: that record is the one series that cannot be
        rebuilt;
      * an explicit opt-in is set, so landing this code switches nothing by itself.

    **THE OPT-IN IS THE LAST CONDITION AND IT IS NOT BELT-AND-BRACES.** `ALPACA_SETUP.md`'s own
    closing line is that changing what prices the bound record *"is Don's call, not a lane's"*.
    """
    e = env if env is not None else os.environ
    opted = (e.get("PRICES_PRIMARY_ALPACA", "") or "").strip().lower() in ("1", "true", "yes")
    art = read_artifact(root)
    if art is None:
        stale = _read_json(artifact_path(root))
        why = ("no seam measurement is recorded")
        if stale:
            why = ("the recorded seam measurement is schema %r and this code requires %r -- "
                   "item 59's run passed on three bars and does not license anything"
                   % (stale.get("schema"), SCHEMA))
        return {"allowed": False, "opted_in": opted, "measured": False,
                "reason": ("%s, so the price vendor order is unchanged. Run POST "
                           "/admin/alpaca-seam?run=1 on the service -- the keys live there and "
                           "nowhere else." % why)}
    closes = art.get("closes") or {}
    rec = art.get("vs_recorded") or {}
    c_ok, r_ok = bool(closes.get("passed")), bool(rec.get("passed"))
    out = {"allowed": bool(c_ok and r_ok and opted), "opted_in": opted, "measured": True,
           "measured_on": art.get("at"), "closes_passed": c_ok, "recorded_passed": r_ok,
           "agree_rate": closes.get("agree_rate"), "n_bars": closes.get("n_bars"),
           "n_names": closes.get("n_names"),
           "coverage": (art.get("coverage") or {}).get("sample_rate")}
    if not c_ok or not r_ok:
        bits = []
        if not c_ok:
            bits.append("daily closes: %s" % (closes.get("reason") or "no reason recorded"))
        if not r_ok:
            bits.append("against the recorded Index series: %s"
                        % (rec.get("reason") or "no reason recorded"))
        out["reason"] = ("the recorded seam measurement did NOT pass, so Alpaca stays off the "
                         "price path -- " + "; ".join(bits))
    elif not opted:
        out["reason"] = ("both legs passed, so the switch is AVAILABLE and has not been taken. "
                         "Set PRICES_PRIMARY_ALPACA=1 on the service to take it -- and per "
                         "ALPACA_SETUP.md that is Don's call, because inside a segment the "
                         "Index's base and mark must come from one vendor.")
    else:
        out["reason"] = ("both legs passed and the opt-in is set: Alpaca is the primary "
                         "daily-close vendor, with yfinance then Stooq as fallbacks.")
    return out


# ---------------------------------------------------------------------------------------------
# comparison
# ---------------------------------------------------------------------------------------------
def _close_map(rows) -> dict:
    """`{YYYY-MM-DD: close}` from Alpaca's bar rows. `t` is an RFC-3339 timestamp."""
    out = {}
    for b in (rows or []):
        d = str((b or {}).get("t") or "")[:10]
        c = (b or {}).get("c")
        if d and isinstance(c, (int, float)):
            out[d] = float(c)
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
    agree = [r for r in diffs if r[1] <= tol]
    # ONLY BARS THAT ACTUALLY MISS THE TOLERANCE. See this patch's note: a "worst offenders"
    # list that lists perfect agreements names innocent tickers as offenders.
    worst = sorted((r for r in diffs if r[1] > tol), key=lambda r: -r[1])[:3]
    return {"measured": True, "n": len(diffs), "n_agree": len(agree),
            "agree_rate": len(agree) / float(len(diffs)),
            "median_abs_rel": sorted(r[1] for r in diffs)[len(diffs) // 2],
            "worst": [{"date": d, "rel": r, "alpaca": x, "other": y} for d, r, x, y in worst]}


# ---------------------------------------------------------------------------------------------
# the pull -- stored, resumable, and it says what it still owes
# ---------------------------------------------------------------------------------------------
def window(end=None) -> dict:
    """The stated window. Declared rather than left to the vendor's default, which is what
    turned the first run into three quotes on one day."""
    import datetime as _dt
    e = end or _dt.date.today()
    if hasattr(e, "date"):
        e = e.date()
    return {"start": str(e - _dt.timedelta(days=WINDOW_CALENDAR_DAYS)), "end": str(e),
            "trading_days_wanted": WINDOW_TRADING_DAYS,
            "calendar_days": WINDOW_CALENDAR_DAYS}


def yf_both_bases(ticker: str, days: int = WINDOW_CALENDAR_DAYS) -> dict:
    """`{"adj": {date: close}, "asof": {date: close}}` from yfinance, BOTH bases in one call.

    **IT ASKS yfinance DIRECTLY RATHER THAN THROUGH `prices`, AND THAT IS NOT A `B7` BREACH.**
    `prices.get_history_df` deliberately serves ONE basis -- the recorded, adjusted one -- and
    forces `auto_adjust=True` to make that the default. The seam's whole question is whether
    Alpaca's two bases land on the right ones, which needs both from the same vendor on the same
    dates. `history(auto_adjust=False)` returns `Close` (as-traded) and `Adj Close` (adjusted)
    together, so one call answers both legs and the two cannot drift apart between calls.

    This is measurement code and it is never on a product path; a test asserts no product module
    imports it.
    """
    out = {"adj": {}, "asof": {}, "error": ""}
    try:
        import yfinance as yf
        h = yf.Ticker(ticker).history(period="%dd" % int(days), interval="1d",
                                      auto_adjust=False)
        if h is None or h.empty:
            out["error"] = "yfinance returned no history"
            return out
        for idx, row in h.iterrows():
            d = str(getattr(idx, "date", lambda: idx)())[:10]
            c, a = row.get("Close"), row.get("Adj Close")
            if c is not None and c == c:
                out["asof"][d] = float(c)
            if a is not None and a == a:
                out["adj"][d] = float(a)
    except Exception as e:                                              # noqa: BLE001
        out["error"] = "%s: %s" % (type(e).__name__, e)
    return out


def pull(*, client=None, names=None, root: str = None, end=None, budget_names: int = 60,
         yf_fetch=None, env=None) -> dict:
    """Fill the stored raw pull, RESUMING where a previous call stopped. Returns a progress report.

    **`budget_names` EXISTS BECAUSE ONE HTTP REQUEST CANNOT DO 222 NAMES OF YAHOO HISTORY.**
    `None` lifts the cap entirely, for a caller with no request to time out.
    It pulls that many NEW names per call and writes what it got, so a re-run continues. The
    analysis refuses until the pull is complete, which is what stops a half-finished pull being
    reported as a rate -- the defect this file exists to repair.
    """
    e = env if env is not None else os.environ
    out = {"ok": False, "reason": "", "window": {}, "n_alpaca": 0, "n_yf": 0,
            "owed": [], "complete": False, "requests": 0, "newly_pulled": []}
    if client is None:
        try:
            client = AD.AlpacaData(env=e)
        except AD.AlpacaDataError as ex:
            out["reason"] = str(ex)
            return out
    names = _sample_names(names, root)
    if isinstance(names, str):
        out["reason"] = names
        return out

    raw = read_raw(root)
    win = window(end)
    # A WINDOW CHANGE INVALIDATES THE STORE. Mixing bars from two windows would make the bar
    # count meaningless, which is the quantity the floor is on.
    if raw.get("window") and raw["window"].get("start") != win["start"]:
        raw = {"schema": SCHEMA, "alpaca": {}, "yf": {}, "window": {}, "requests": 0}
        out["reason"] = "the window moved, so the stored pull was discarded and restarted; "
    raw["window"] = win
    out["window"] = win

    # ---- ALPACA: cheap, multi-symbol, so it is pulled whole on the first call ---------------
    if not raw["alpaca"]:
        for adj in (AD.ADJ_ALL, AD.ADJ_RAW):
            got = client.bars(names, adjustment=adj, start=win["start"], end=win["end"])
            out["requests"] += int(got.get("requests") or 0)
            if not got.get("ok"):
                out["reason"] += "the Alpaca pull failed: %s" % got.get("error")
                _write_json(raw_path(root), raw)
                return out
            # A TRUNCATION IS A FAILURE HERE, NOT A WARNING. `bars()` reports a page-cap stop
            # in `error` while leaving `ok` True -- correct for a caller that wants whatever
            # arrived, and wrong for this one: storing a cut-off series would feed the bar
            # count the floor is computed on, so a truncated pull could read as a thin one
            # rather than as an incomplete one. Two different facts.
            if got.get("error"):
                out["reason"] += ("the Alpaca pull was TRUNCATED and is not stored: %s"
                                  % got.get("error"))
                out["truncated"] = True
                return out
            for sym, rows in (got.get("bars") or {}).items():
                raw["alpaca"].setdefault(str(sym).upper(), {})[adj] = _close_map(rows)
        raw["requests"] = int(raw.get("requests") or 0) + out["requests"]
        _write_json(raw_path(root), raw, sort_keys=False)

    # ---- YAHOO: one call per name, so it is paced and resumable -----------------------------
    fetch = yf_fetch or yf_both_bases
    owed = [n for n in names if n not in (raw.get("yf") or {})]
    # `None` means every name still owed -- see `measure()`, the one-shot entry point.
    todo = owed if budget_names is None else owed[:max(0, int(budget_names))]
    for i, t in enumerate(todo, 1):
        got = fetch(t)
        raw["yf"][t] = {"adj": got.get("adj") or {}, "asof": got.get("asof") or {},
                        "error": got.get("error") or ""}
        out["newly_pulled"].append(t)
        # EVERY TENTH NAME, AND ALWAYS AT THE END. A per-name flush re-serialises the whole
        # growing pull -- ~110,000 numbers written 222 times -- which measured at ~280 seconds
        # and would be spent inside the HTTP request. A timeout now loses at most ten names,
        # and they are simply pulled again on the next call, so RESUMABILITY is unaffected.
        if i % FLUSH_EVERY == 0:
            _write_json(raw_path(root), raw, sort_keys=False)
    _write_json(raw_path(root), raw, sort_keys=False)

    out["n_alpaca"] = len(raw.get("alpaca") or {})
    out["n_yf"] = len(raw.get("yf") or {})
    out["owed"] = [n for n in names if n not in (raw.get("yf") or {})]
    out["complete"] = not out["owed"]
    out["ok"] = True
    out["reason"] += ("the stored pull is COMPLETE: %d names from Alpaca, %d from Yahoo"
                      % (out["n_alpaca"], out["n_yf"])) if out["complete"] else (
        "pulled %d new name(s); %d still owed. Run the door again to continue -- the analysis "
        "refuses until the pull is complete." % (len(out["newly_pulled"]), len(out["owed"])))
    return out


def _sample_names(names, root):
    """The stated sample, or a string explaining why it could not be had."""
    if names is not None:
        return sorted({str(n).strip().upper() for n in names if str(n).strip()})
    try:
        import sys
        rd = root or os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))
        if rd not in sys.path:
            sys.path.insert(0, rd)
        from scripts import fmp_seam as FS
        return sorted(set(FS.sample()) | set(NAMED_GAPS))
    except Exception as ex:                                             # noqa: BLE001
        return "the stated sample could not be built: %r" % (ex,)


def categories(root=None) -> dict:
    try:
        import sys
        rd = root or os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))
        if rd not in sys.path:
            sys.path.insert(0, rd)
        from scripts import fmp_seam as FS
        return dict(FS.CATEGORY)
    except Exception:                                                   # noqa: BLE001
        return {}


# ---------------------------------------------------------------------------------------------
# vs_recorded -- the leg that gates the Index switch
# ---------------------------------------------------------------------------------------------
def alpaca_fetch(raw_by_symbol: dict, basis: str = AD.ADJ_ALL):
    """A `fetch(ticker, days, as_of)` backed by the stored Alpaca pull.

    **IT EXISTS SO `contract_row` COMPUTES THE COMPARISON ROW WITH ITS OWN ARITHMETIC.** The
    alternative is re-deriving the Index's renormalisation, its coverage floor and its
    segment-base rule here -- a second definition of the one series that cannot be rebuilt, and
    exactly the `B7` split this project has paid for repeatedly. `contract_row` already takes an
    injectable `fetch`, so the only thing that changes is where the prices come from.
    """
    import pandas as pd

    def fetch(ticker, days=None, as_of=None):
        m = ((raw_by_symbol or {}).get(str(ticker).upper()) or {}).get(basis) or {}
        if not m:
            return None
        rows = [{"Date": d, "Close": c, "Open": c, "High": c, "Low": c, "Volume": 0}
                for d, c in sorted(m.items())]
        if as_of is not None:
            cut = str(as_of)[:10]
            rows = [r for r in rows if r["Date"] <= cut]
        return pd.DataFrame(rows) if rows else None

    return fetch


def measure_vs_recorded(*, raw_by_symbol: dict, root: str = None, series=None,
                        contract_row=None) -> dict:
    """Recompute EVERY recorded row with Alpaca's prices and compare. ITEM 62 PART 2.

    **EVERY ROW, OR UNMEASURED.** There is no percentage floor here on purpose: the bound record
    is the one series that cannot be rebuilt, and a vendor that reproduces three rows of four
    says nothing about the fourth.

    Agreement is reported per row and the largest gap in BASIS POINTS of the percentage figures,
    because that is the unit the question is asked in -- a 0.02pp seam between two price routes
    is already a measured fact on this project, and bps is the only scale on which that is
    distinguishable from a basis change.
    """
    out = {"passed": False, "measured": False, "n_rows": 0, "n_compared": 0, "n_agree": 0,
           "worst_bps": None, "rows": [], "reason": "", "tol_bps": RECORDED_TOL_BPS}
    if contract_row is None:
        try:
            from ..screener.index_mark import contract_row as contract_row  # noqa: F811
        except Exception as ex:                                          # noqa: BLE001
            out["reason"] = "index_mark could not be imported: %r" % (ex,)
            return out
    if series is None:
        try:
            from ..screener import index_track as IT
            doc = IT.load() or {}
            series = doc.get("series") or doc.get("rows") or []
        except Exception as ex:                                          # noqa: BLE001
            out["reason"] = "the recorded series could not be read: %r" % (ex,)
            return out
    series = [r for r in (series or []) if (r or {}).get("date")]
    out["n_rows"] = len(series)
    if not series:
        out["reason"] = ("the bound Index record carries no rows here, so there is nothing to "
                         "compare against. This leg can only be measured on the service, where "
                         "the record lives.")
        return out

    fetch = alpaca_fetch(raw_by_symbol, AD.ADJ_ALL)
    worst = 0.0
    for r in series:
        d = str(r.get("date"))[:10]
        row = {"date": d, "ok": False, "reason": ""}
        try:
            got = contract_row(as_of=d, fetch=fetch, refuse_before_close=False)
        except Exception as ex:                                          # noqa: BLE001
            row["reason"] = "contract_row raised: %r" % (ex,)
            out["rows"].append(row)
            continue
        if not got.get("ok"):
            row["reason"] = got.get("reason") or "contract_row refused"
            out["rows"].append(row)
            continue
        mine = got.get("row") or {}
        pairs = []
        for k in ("valquo_pct", "spy_pct", "excess_pp"):
            a, b = _f(mine.get(k)), _f(r.get(k))
            if a is None or b is None:
                continue
            pairs.append((k, a, b, abs(a - b) * 100.0))       # percentage points -> bps
        if not pairs:
            row["reason"] = "the recorded row carries none of the comparable fields"
            out["rows"].append(row)
            continue
        gap = max(p[3] for p in pairs)
        worst = max(worst, gap)
        row.update(ok=True, gap_bps=gap, agree=bool(gap <= RECORDED_TOL_BPS),
                   fields={p[0]: {"alpaca": p[1], "recorded": p[2], "gap_bps": p[3]}
                           for p in pairs},
                   n_priced_alpaca=mine.get("n_priced"), n_priced_recorded=r.get("n_priced"))
        out["rows"].append(row)

    done = [x for x in out["rows"] if x.get("ok")]
    out["n_compared"] = len(done)
    out["n_agree"] = sum(1 for x in done if x.get("agree"))
    out["worst_bps"] = (worst if done else None)
    out["measured"] = bool(done)

    if not done:
        out["reason"] = ("no recorded row could be recomputed from Alpaca's prices: %s"
                         % "; ".join(sorted({x.get("reason") or "?"
                                             for x in out["rows"]}))[:300])
        return out
    if RECORDED_REQUIRE_ALL_ROWS and len(done) < len(series):
        missed = [x["date"] for x in out["rows"] if not x.get("ok")]
        out["reason"] = ("%d of %d recorded rows could not be recomputed (%s), and this leg "
                         "requires EVERY row -- the bound record is the one series that cannot "
                         "be rebuilt, so a vendor that reproduces some of it says nothing about "
                         "the rest" % (len(series) - len(done), len(series),
                                       ", ".join(missed[:6])))
        return out
    if out["n_agree"] < len(done):
        bad = [x["date"] for x in done if not x.get("agree")]
        out["reason"] = ("%d of %d recomputed rows differ from the recorded ones by more than "
                         "%.1f bps (worst %.2f bps, on %s)"
                         % (len(done) - out["n_agree"], len(done), RECORDED_TOL_BPS,
                            worst, ", ".join(bad[:6])))
        return out
    out["passed"] = True
    out["reason"] = ("all %d recorded rows reproduce from Alpaca's adjusted closes within %.1f "
                     "bps (worst %.2f bps), using `contract_row`'s own arithmetic"
                     % (len(done), RECORDED_TOL_BPS, worst))
    return out


def _f(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if v != v else v


# ---------------------------------------------------------------------------------------------
# the analysis
# ---------------------------------------------------------------------------------------------
def analyse(*, root: str = None, names=None, series=None, contract_row=None,
            write: bool = True, feeds=None, rate=None) -> dict:
    """Analyse the STORED pull. Spends no request. **Refuses while the pull is incomplete.**"""
    import datetime as _dt
    out = {"schema": SCHEMA, "ok": True, "reason": "",
           "at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "window": {}, "floors": {
               "window_trading_days": WINDOW_TRADING_DAYS,
               "min_names": MIN_NAMES_FOR_PASS, "min_bars": MIN_BARS_FOR_PASS,
               "min_bars_per_name": MIN_BARS_PER_NAME,
               "agree_rate": PASS_AGREE_RATE, "per_bar_tolerance": AGREE_TOL,
               "recorded_requires_every_row": RECORDED_REQUIRE_ALL_ROWS,
               "recorded_tol_bps": RECORDED_TOL_BPS,
               "why": ("ITEM 62: the first run cleared a 0.98 agreement bar on THREE BARS. A "
                       "rate without a quantity beside it is not evidence, so the floors are "
                       "on evidence as well as on agreement and below any of them the result "
                       "is UNMEASURED rather than passed.")},
           "sample": {}, "coverage": {}, "closes": {}, "vs_recorded": {}, "bases": {},
           "fifty_two_week": {}, "named_gaps_note": "",
           "feeds": feeds or {}, "rate": rate or {}, "named_gaps": {},
           "not_carried": list(AD.NOT_CARRIED), "carried_free": list(AD.CARRIED_FREE)}

    nm = _sample_names(names, root)
    if isinstance(nm, str):
        out["ok"] = False
        out["reason"] = nm
        return out
    raw = read_raw(root)
    out["window"] = raw.get("window") or {}
    cats = categories(root)
    out["sample"] = {"n": len(nm), "source": ("scripts.fmp_seam.sample() plus the named gaps "
                                              "-- IMPORTED so the three vendors are compared "
                                              "on ONE population"),
                     "categories": {k: v for k, v in sorted(cats.items())}}

    alp, yfd = raw.get("alpaca") or {}, raw.get("yf") or {}
    owed = [n for n in nm if n not in yfd]

    # ---- coverage, by category, with the gaps NAMED ---------------------------------------
    bars_by_name = {s: len((v or {}).get(AD.ADJ_ALL) or {}) for s, v in alp.items()}
    covered = sorted(s for s in nm if bars_by_name.get(s, 0) >= MIN_BARS_PER_NAME)
    thin = sorted(s for s in nm if 0 < bars_by_name.get(s, 0) < MIN_BARS_PER_NAME)
    out["coverage"] = {
        "sample_n": len(nm), "sample_covered": len(covered),
        "sample_rate": (len(covered) / float(len(nm)) if nm else None),
        "min_bars_per_name": MIN_BARS_PER_NAME,
        "thin": thin[:40],
        "thin_note": ("A name with SOME bars but fewer than the floor is reported separately "
                      "from one with none: item 59's run asked for no window, got one bar per "
                      "name, and then called three of them a daily-close comparison."),
        "missing": sorted(set(nm) - set(covered) - set(thin))[:40],
        "by_category": {},
    }
    for cat in sorted(set(cats.values())):
        members = [s for s in nm if cats.get(s) == cat]
        if not members:
            continue
        got = [s for s in members if s in covered]
        out["coverage"]["by_category"][cat] = {
            "n": len(members), "covered": len(got), "rate": len(got) / float(len(members)),
            "missing": sorted(set(members) - set(got))[:12]}
    out["named_gaps_note"] = (
        "WHY THE FIRST RUN (2026-10-15) REPORTED AVB, BK AND EQR MISSING, and it was ours: the "
        "door sent NO `start` and NO `end`, so Alpaca chose the window and returned ONE "
        "session per name -- a name with no print in that single session read as NOT COVERED "
        "rather than as NOT ASKED. Three other candidate causes were ruled out by test and are "
        "NOT the explanation: pagination is followed to the last token, a 220-name by 250-day "
        "chunked pull loses no symbol, and a dotted class share (BRK.B) survives the round "
        "trip unchanged. A truncated pull is now a refusal rather than a stored partial, and "
        "coverage requires %d bars per name over the %d-session window below."
        % (MIN_BARS_PER_NAME, WINDOW_TRADING_DAYS))
    out["named_gaps"] = {
        t: {"why_asked": why, "bars": bars_by_name.get(t, 0),
            "covered": t in covered,
            "yf_bars": len(((yfd.get(t) or {}).get("adj") or {})),
            "yf_error": (yfd.get(t) or {}).get("error") or ""}
        for t, why in sorted(NAMED_GAPS.items())}

    # ---- the daily-close comparison, BAR-WEIGHTED -----------------------------------------
    per_name, n_bars, n_agree, n_names = {}, 0, 0, 0
    raw_bars, raw_agree = 0, 0
    for s in nm:
        a_all = (alp.get(s) or {}).get(AD.ADJ_ALL) or {}
        a_raw = (alp.get(s) or {}).get(AD.ADJ_RAW) or {}
        y = yfd.get(s) or {}
        row = {}
        if a_all and (y.get("adj") or {}):
            row["all_vs_yf_adjusted"] = compare_closes(a_all, y["adj"])
        if a_raw and (y.get("asof") or {}):
            row["raw_vs_yf_as_traded"] = compare_closes(a_raw, y["asof"])
        if not row:
            continue
        per_name[s] = row
        g = row.get("all_vs_yf_adjusted") or {}
        if g.get("measured"):
            n_names += 1
            n_bars += g["n"]
            n_agree += g["n_agree"]
        h = row.get("raw_vs_yf_as_traded") or {}
        if h.get("measured"):
            raw_bars += h["n"]
            raw_agree += h["n_agree"]

    # **BAR-WEIGHTED, NOT THE MEAN OF PER-NAME RATES.** A mean lets a one-bar name count as much
    # as a 250-bar one, which is how three single-bar names produced `agree_rate 1.000`.
    rate_all = (n_agree / float(n_bars)) if n_bars else None
    out["closes"] = {
        "basis_used": AD.ADJ_FOR_RECORDED_BASIS,
        "n_names": n_names, "n_bars": n_bars, "n_agree": n_agree,
        "agree_rate": rate_all,
        "aggregation": ("BAR-WEIGHTED. A mean of per-name rates lets a one-bar name count as "
                        "much as a 250-bar one, which is how item 59's three single-bar names "
                        "produced an agreement rate of 1.000."),
        "as_traded_leg": {"n_bars": raw_bars, "n_agree": raw_agree,
                          "agree_rate": ((raw_agree / float(raw_bars)) if raw_bars else None)},
        "worst": sorted(
            ({"ticker": s, **((v.get("all_vs_yf_adjusted") or {}).get("worst") or [{}])[0]}
             for s, v in per_name.items()
             if (v.get("all_vs_yf_adjusted") or {}).get("worst")),
            key=lambda r: -(r.get("rel") or 0))[:8],
        "per_name_n": {s: ((v.get("all_vs_yf_adjusted") or {}).get("n") or 0)
                       for s, v in sorted(per_name.items())},
    }

    reasons = []
    if owed:
        reasons.append("the stored pull is INCOMPLETE -- %d of %d names still owed from Yahoo"
                       % (len(owed), len(nm)))
    if n_names < MIN_NAMES_FOR_PASS:
        reasons.append("only %d names could be compared, below the declared floor of %d"
                       % (n_names, MIN_NAMES_FOR_PASS))
    if n_bars < MIN_BARS_FOR_PASS:
        reasons.append("only %s comparable bars, below the declared floor of %s"
                       % (format(n_bars, ","), format(MIN_BARS_FOR_PASS, ",")))
    if rate_all is None:
        reasons.append("the comparison is UNMEASURED, which is not a pass")
    elif rate_all < PASS_AGREE_RATE:
        reasons.append("agreement with yfinance's adjusted close is %.4f, below the declared "
                       "%.2f" % (rate_all, PASS_AGREE_RATE))
    out["closes"]["passed"] = not reasons
    out["closes"]["reason"] = ("; ".join(reasons) if reasons else
                               ("Alpaca's adjustment=all close agrees with yfinance's adjusted "
                                "close on %.4f of %s comparable bars across %d names over %s "
                                "to %s" % (rate_all, format(n_bars, ","), n_names,
                                           (out["window"] or {}).get("start"),
                                           (out["window"] or {}).get("end"))))

    # ---- ARE THE TWO BASES ACTUALLY DIFFERENT? ITEM 62 PART 5 -------------------------------
    # The first run reported every 52-week high identical on both bases and could not tell
    # "the splits are old" from "both bases returned the same series". A dividend payer inside
    # the window separates them: an adjusted close must differ from an as-traded one there.
    ctl = {}
    for s in DIVIDEND_CONTROL:
        a_all = (alp.get(s) or {}).get(AD.ADJ_ALL) or {}
        a_raw = (alp.get(s) or {}).get(AD.ADJ_RAW) or {}
        shared = sorted(set(a_all) & set(a_raw))
        if not shared:
            continue
        diffs = [abs(a_all[d] / a_raw[d] - 1.0) for d in shared if a_raw[d]]
        if not diffs:
            continue
        ctl[s] = {"n": len(diffs), "max_rel": max(diffs),
                  "n_differing": sum(1 for x in diffs if x > 1e-9)}
    differ = [s for s, v in ctl.items() if v["n_differing"] > 0]
    out["bases"] = {
        "control_names": list(DIVIDEND_CONTROL),
        "measured": ctl,
        "distinct": bool(differ),
        "distinct_on": sorted(differ),
        "why": ("A dividend payer inside the window MUST price differently on an adjusted basis "
                "than on an as-traded one. If none of these differ, Alpaca returned one series "
                "under two parameter values and every basis figure here is meaningless -- which "
                "is a thing the first run could not distinguish from 'the splits are old'."),
        "reason": ("the two bases are genuinely distinct: %d of %d dividend controls differ"
                   % (len(differ), len(ctl))) if differ else
                  ("NOT DISTINGUISHABLE on this pull: no dividend control differed between "
                   "adjustment=all and adjustment=raw, so either the window contains no "
                   "dividend or both parameters returned one series"),
    }

    # ---- vs_recorded -----------------------------------------------------------------------
    # ---- the 52-week high on each basis -- RESTORED, see this file's git history -----------
    # The Dip Detector screens on distance below a 52-week high, which makes this the most
    # basis-sensitive number the product renders: an as-traded high read after a split looks
    # like a crash. It is reported so a vendor switch cannot move that screen in silence.
    hi = {}
    for sym in sorted(alp):
        a = (alp.get(sym) or {}).get(AD.ADJ_ALL) or {}
        r = (alp.get(sym) or {}).get(AD.ADJ_RAW) or {}
        if not a or not r:
            continue
        ha, hr = max(a.values()), max(r.values())
        hi[sym] = {"adjusted": ha, "raw": hr,
                   "rel_gap": (abs(ha / hr - 1.0) if hr else None)}
    gaps = sorted((v["rel_gap"] or 0) for v in hi.values())
    out["fifty_two_week"] = {
        "n": len(hi), "median_rel_gap": (gaps[len(gaps) // 2] if gaps else None),
        "n_over_1pct": sum(1 for g in gaps if g > 0.01),
        "worst": sorted(hi.items(), key=lambda kv: -(kv[1]["rel_gap"] or 0))[:5],
        "why": ("the Dip Detector is about this number, and it is the most basis-sensitive "
                "figure the product renders: a raw high after a split reads as a crash"),
    }

    out["vs_recorded"] = measure_vs_recorded(raw_by_symbol=alp, root=root, series=series,
                                             contract_row=contract_row)

    out["pull"] = {"complete": not owed, "n_alpaca": len(alp), "n_yf": len(yfd),
                   "owed": owed[:40], "n_owed": len(owed),
                   "requests_spent": int(raw.get("requests") or 0)}
    out["reason"] = ("closes: %s | recorded: %s" % (out["closes"]["reason"],
                                                    out["vs_recorded"]["reason"]))[:900]
    if write:
        out["written_to"] = artifact_path(root) if _write_json(artifact_path(root), out) else None
    return out


#: Kept so item 59's callers and tests do not break: `measure` now ANALYSES the stored pull.
#: It no longer pulls, because a function that both spends requests and reports a rate is how a
#: half-finished pull came to be reported as a measurement.
def closes_fetch(yf_closes: dict):
    """Adapt a plain `{ticker: {date: close}}` map into the `yf_fetch` shape `pull()` wants.

    The map is read as the ADJUSTED close and ALSO as the as-traded one, which is the honest
    reading of a caller that supplied one series: it says nothing about splits or dividends, so
    the two legs are identical and the `bases` control will say so rather than inferring
    anything from their agreement. A ticker absent from the map yields NO bars -- never a
    fall-through to the live vendor, which is exactly the trap this adapter closes.
    """
    import pandas as pd

    def fetch(ticker, days=None):
        closes = (yf_closes or {}).get(str(ticker).upper())
        if not closes:
            return {"adj": {}, "asof": {}, "error": "not in the supplied closes map"}
        return {"adj": dict(closes), "asof": dict(closes), "error": ""}
    _ = pd
    return fetch


def measure(*, client=None, names=None, root: str = None, end=None, yf_fetch=None,
            yf_closes=None, env=None, series=None, contract_row=None, feeds=None,
            write: bool = True, budget_names: int = None) -> dict:
    """PULL, THEN ANALYSE, in one call. The offline and single-machine entry point.

    **THE DOOR DELIBERATELY DOES NOT USE THIS**, and the reason is a budget rather than a
    doubt: 250 trading days across 222 names is ~55,000 Alpaca bars and 222 Yahoo history
    calls, which does not reliably finish inside one HTTP request, so `/admin/alpaca-seam`
    calls `pull()` with a budget and then `analyse()`, and a re-run continues the stored pull.
    Here there is no request to time out, so the whole thing runs at once -- which is what a
    test holding injected fakes wants, and what a script run on a workstation wants.

    `budget_names=None` means "every name still owed", so a one-shot really is one shot.

    **THERE IS NO `**kwargs` HERE AND THAT IS DELIBERATE.** The version of this shim that
    landed earlier today swallowed unknown keywords, so a caller injecting `yf_closes` had its
    Yahoo leg dropped in silence and the pull reached the real network instead. An unknown
    keyword is now a `TypeError` -- the direction that stops rather than the one that guesses.
    """
    if yf_fetch is None and yf_closes is not None:
        yf_fetch = closes_fetch(yf_closes)
    prog = pull(client=client, names=names, root=root, end=end, yf_fetch=yf_fetch, env=env,
                budget_names=budget_names)
    if not prog.get("ok"):
        return {"schema": SCHEMA, "ok": False, "pull": prog,
                "closes": {"passed": False, "measured": False,
                           "reason": prog.get("reason", "")},
                "vs_recorded": {"passed": False, "measured": False,
                                "reason": "the pull did not run"},
                "passed": False, "reason": prog.get("reason", "")}
    out = analyse(root=root, names=names, series=series, contract_row=contract_row,
                  feeds=feeds, write=write)
    out["pull"] = prog
    return out
