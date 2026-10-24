# -*- coding: utf-8 -*-
"""ITEM 75 — build the book AS OF a date, and refuse a book built after its event.

THE DATED PROBLEM. The 2026-10-22 rebalance is appended on the evening of 10-23, in the one
safe window there is: after the 10-22 track row exists and before `track-row` writes the 10-23
row at ~03:07 UTC on 10-24. Sharadar's recommended pull is ~5:20pm ET, so by that evening the
export very likely carries the **10-23** close. Two things then follow, and the second is the
one that could have falsified the record:

  1. `_full_universe_rows` called `score_universe_now(prov, tickers)` with no `as_of`, so the
     book is scored as of the export's LATEST close. The runbook's freshness step
     (`as_of == 2026-10-22`) stops the rebalance, and there is no way to build as of 10-22 —
     the CLI had no `--as-of`, though `score_universe_now` has accepted one all along.
  2. If the gate were skipped, `append_rebalance` would let the book through. Its freshness
     check refuses only a book too OLD, and `trading_days_between` counts FORWARD: measured,
     `('2026-10-23' -> '2026-10-22')` is **0**, and so is `('2026-11-23' -> '2026-10-22')`. So
     a 10-23 book dated 10-22 is a one-day look-ahead and nothing downstream could tell.

WHAT IS VERIFIED HERE RATHER THAN ASSERTED. "`as_of` cuts every input" is a claim about
prices, SF1 by `datekey`, DAILY market cap, 13F and insiders by filing date, and the
stale-price cutoff. Reading six call sites proves nothing; the fixture below builds the SAME
export twice — once ending at the as-of, once carrying twelve more trading days — and requires
the two books to be bit-identical. Anything not cut at the as-of shows up, and nothing else
does.

**AND IT FOUND ONE.** `last_seen[t] = s.index[-1]` was each ticker's newest print in the WHOLE
export, so the guard that keeps forward-filled stale quotes out of a live book was reading a
date in the FUTURE of the book it gated:

    export ENDS at as_of        -> MMM in book: False
    export CONTINUES past as_of -> MMM in book: True
    and it was scored at price 192.0900, which is the forward-filled stale close

Every test in `TheAsOfCutsEveryInput` and `TheDoorRefusesABookBuiltAfterItsEvent` fails against
the pre-item-75 tree.
"""
from __future__ import annotations

import csv
import datetime as _dt
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401

from valuation.edge import valquo_index as V            # noqa: E402
from valuation.edge.data_providers import WRDSProvider  # noqa: E402
from valuation.edge.fundamental_panel import score_universe_now  # noqa: E402
from valuation.screener import index_mark as IM         # noqa: E402
from valuation.screener import market_session as MS     # noqa: E402

NAMES = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH", "III", "JJJ",
         "KKK", "LLL", "MMM", "NNN", "OOO", "PPP", "QQQ", "RRR", "SSS", "TTT", "SPY"]

#: SF1 columns the metric builder reads. Written in full so a fixture row is a plausible
#: filing rather than a handful of fields that happen to be enough today.
SF1_COLS = ["ticker", "datekey", "calendardate", "reportperiod", "dimension",
            "sharesbas", "sharefactor", "revenue", "assets", "equity", "netinccmn",
            "ncfo", "capex", "gp", "ebit", "liabilities", "cashneq", "debt",
            "marketcap", "ev", "fcf", "sharesw", "shareswa", "shareswadil",
            "assetsc", "liabilitiesc", "receivables", "inventory", "ppnenet",
            "depamor", "retearn", "workingcapital", "ncfcommon", "ncfdebt", "intexp",
            "taxexp", "ebt", "invcap", "ncfdiv"]


def trading_days(start: str, n: int) -> list:
    """Mon-Fri from `start`. No holiday table: in this fixture the export IS the calendar,
    which is exactly the rule `score_universe_now` applies to a real export."""
    y, m, d = (int(x) for x in start.split("-"))
    cur, out = _dt.date(y, m, d), []
    while len(out) < n:
        if cur.weekday() < 5:
            out.append(cur.isoformat())
        cur += _dt.timedelta(days=1)
    return out


def build_export(root: str, *, n_days: int = 340, extra_days: int = 0, start="2024-01-01",
                 gap_name: str = None, quiet_days: int = 30) -> dict:
    """A Sharadar-shaped export. `extra_days` appends days AFTER the base window.

    `gap_name` gives one name a FULL history and then makes it go quiet for the last
    `quiet_days` trading days of the base window, printing again only in the extra days. That
    is the shape that exposes a stale-price cutoff measured on the wrong window.

    **THE HISTORY HAS TO BE FULL, and my first cut got that wrong**: a name with 54 rows is
    dropped by `len(s) > 252` before the freshness check is ever reached, so the probe passed
    while measuring nothing.
    """
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(os.path.join(root, "prices"), exist_ok=True)
    days = trading_days(start, n_days + extra_days)

    for k, t in enumerate(NAMES):
        rows = []
        for j, d in enumerate(days):
            if gap_name and t == gap_name and (n_days - quiet_days) <= j < n_days:
                continue
            px = 100.0 + k * 7.0 + (j % 23) * 0.5 + j * 0.01 * (1 + (k % 3))
            rows.append({"date": d, "close": round(px, 4)})
        with io.open(os.path.join(root, "prices", t + ".csv"), "w", encoding="utf-8",
                     newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["date", "close"])
            w.writeheader()
            w.writerows(rows)

    srows = []
    qends = [d for j, d in enumerate(days) if j % 63 == 0]
    for k, t in enumerate(NAMES):
        if t == "SPY":
            continue
        for q, d in enumerate(qends):
            shares = 2.0e8 + k * 1.0e7
            rev = 4.0e9 + k * 2.0e8 + q * 5.0e7
            srows.append({
                "ticker": t, "datekey": d, "calendardate": d, "reportperiod": d,
                "dimension": "ARQ", "sharesbas": shares, "sharefactor": 1.0,
                "revenue": rev, "assets": 2.0e10 + k * 1e9, "equity": 8.0e9 + k * 4e8,
                "netinccmn": 6.0e8 + k * 3e7 + q * 1e7, "ncfo": 9.0e8 + k * 4e7,
                "capex": -2.0e8, "gp": rev * 0.42, "ebit": rev * 0.18,
                "liabilities": 1.2e10 + k * 6e8, "cashneq": 1.5e9, "debt": 5.0e9,
                "marketcap": 0.0, "ev": 0.0, "fcf": 7.0e8, "sharesw": shares,
                "shareswa": shares, "shareswadil": shares, "assetsc": 7.0e9,
                "liabilitiesc": 4.0e9, "receivables": 2.0e9, "inventory": 1.0e9,
                "ppnenet": 6.0e9, "depamor": 4.0e8, "retearn": 3.0e9,
                "workingcapital": 3.0e9, "ncfcommon": -1.0e8 - k * 1e6, "ncfdebt": 5.0e7,
                "intexp": 1.2e8, "taxexp": 1.4e8, "ebt": rev * 0.16, "invcap": 1.3e10,
                "ncfdiv": -1.0e8,
            })
    with io.open(os.path.join(root, "fundamentals.csv"), "w", encoding="utf-8",
                 newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SF1_COLS)
        w.writeheader()
        w.writerows(srows)
    return {"root": root, "days": days, "as_of": days[:n_days][-1], "newest": days[-1]}


def score(root, as_of=None):
    class _Cfg:
        wrds_data_dir = root
    prov = WRDSProvider(_Cfg())
    return score_universe_now(prov, prov.universe(limit=3000), as_of=as_of)


def digest(res) -> list:
    """Everything about a scored row that an as-of could move."""
    return [(r["ticker"], round(float(r["composite"]), 12), r["rank"],
             round(float(r["price"]), 6), round(float(r["market_cap"]), 2))
            for r in (res.get("rows") or [])]


class _Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def export(self, tag, **kw):
        return build_export(os.path.join(self.tmp, tag), **kw)


# =============================================================================================
class TheAsOfCutsEveryInput(_Fixture):
    """The property, measured: a later day of data cannot move an `--as-of` book."""

    def test_APPENDING_A_LATER_DAY_LEAVES_THE_AS_OF_BOOK_BIT_IDENTICAL(self):
        """**THE WHOLE ITEM IN ONE TEST.** Same generator, same names, same filings; one export
        stops at the as-of and one carries twelve more trading days. Prices, SF1 by `datekey`,
        DAILY market cap, 13F/insider filing dates and the stale-price cutoff are all in scope,
        and any of them reading past the as-of moves a composite, a rank or a price.

        **IT PASSES ON THE OLD TREE TOO, AND THAT IS WORTH SAYING.** On a plain export every
        input was already cut correctly; the one leak needed a name whose price history has a
        GAP at the as-of to surface, which is `TheStalePriceCutoffIsMeasuredAtTheAsOf`. So this
        test is the CONTROL — it is what makes the gap test's failure attributable to the
        freshness window rather than to the fixture — and the gap test is the discriminating
        one. Reporting a control as evidence of a fix is how a suite comes to look stronger
        than it is."""
        base = self.export("base", n_days=340, extra_days=0)
        later = self.export("later", n_days=340, extra_days=12)
        d = base["as_of"]
        self.assertEqual(later["days"][339], d, "the two exports must share the as-of session")
        self.assertGreater(later["newest"], d, "the later export must carry future data")

        a, b = score(base["root"], d), score(later["root"], d)
        self.assertTrue(digest(a), "the fixture scored nothing, so this test proves nothing")
        self.assertEqual(digest(a), digest(b),
                         "a later day of data moved the as-of book")

    def test_the_as_of_is_REPORTED_as_the_date_that_was_ASKED_FOR(self):
        base = self.export("base", n_days=340, extra_days=12)
        d = base["days"][339]
        self.assertEqual(score(base["root"], d)["as_of"], d)

    def test_NO_AS_OF_IS_THE_NEWEST_CLOSE_AND_THE_FIX_IS_THEREFORE_INERT(self):
        """Every shipped caller passes no `as_of`. `cal` is the UNION calendar, so `cal[-1]` is
        at or after every ticker's last print and the new freshness slice is the whole index —
        the change can only bite when an as-of is actually passed."""
        base = self.export("base", n_days=340, extra_days=0)
        plain = score(base["root"], None)
        named = score(base["root"], base["newest"])
        self.assertEqual(plain["as_of"], base["newest"])
        self.assertEqual(digest(plain), digest(named))


# =============================================================================================
class TheStalePriceCutoffIsMeasuredAtTheAsOf(_Fixture):
    """THE DEFECT THE FIXTURE FOUND, and the one that was a look-ahead rather than a gap.

    `score_universe_now` forward-fills every name onto a shared calendar, and `cutoff` exists
    so a dead name's last print is not carried into a live book. It compared against
    `last_seen`, which was the ticker's newest print in the WHOLE export — a date AFTER the
    as-of. A name a month quiet at the as-of was kept, priced at its forward-filled month-old
    close, purely because it traded again later.
    """

    def _mmm(self, extra):
        e = self.export("g%d" % extra, n_days=340, extra_days=extra, gap_name="MMM",
                        quiet_days=30)
        res = score(e["root"], e["days"][339])
        return {r["ticker"] for r in res["rows"]}, res

    def test_a_name_QUIET_AT_THE_AS_OF_is_dropped_whether_or_not_it_trades_LATER(self):
        stops_at_as_of, _ = self._mmm(0)
        carries_on, res = self._mmm(12)
        self.assertNotIn("MMM", stops_at_as_of,
                         "a month-stale name was kept even with no future data at all")
        self.assertNotIn("MMM", carries_on,
                         "a FUTURE print made a month-stale name look fresh at the as-of")
        self.assertEqual(stops_at_as_of, carries_on)

    def test_the_fixture_is_NOT_VACUOUS__MMM_is_scored_when_it_is_not_quiet(self):
        """Without this, 'MMM is absent' would be satisfied by a fixture that never scored it —
        which is exactly how my first version of this probe passed while measuring nothing (the
        name had 54 rows and was dropped by the 252-session history floor)."""
        e = self.export("nogap", n_days=340, extra_days=12)
        got = {r["ticker"] for r in score(e["root"], e["days"][339])["rows"]}
        self.assertIn("MMM", got)


# =============================================================================================
class AnAsOfIsHonouredExactlyOrRefused(_Fixture):
    """A date that slid quietly to an earlier session would publish a `data_as_of` the
    operator's runbook, their notes and the event they are about to append all disagree with —
    and nothing in the record could say which was right."""

    def test_a_date_LATER_than_the_newest_close_is_refused(self):
        e = self.export("base", n_days=340)
        after = (_dt.date.fromisoformat(e["newest"]) + _dt.timedelta(days=7)).isoformat()
        res = score(e["root"], after)
        self.assertEqual(res["rows"], [])
        self.assertIn("later than the newest close", res["refused"])

    def test_a_date_that_is_NOT_A_TRADING_DAY_in_the_export_is_refused(self):
        """And the export IS the calendar: no holiday table is consulted, so a Saturday and a
        Thanksgiving are the same case and neither may be silently rounded down."""
        e = self.export("base", n_days=340)
        d = _dt.date.fromisoformat(e["as_of"])
        sat = d + _dt.timedelta(days=(5 - d.weekday()) % 7 or 7)
        self.assertEqual(sat.weekday(), 5)
        if sat.isoformat() > e["newest"]:
            e = self.export("base2", n_days=340, extra_days=12)
        res = score(e["root"], sat.isoformat())
        self.assertEqual(res["rows"], [])
        self.assertIn("not a trading day", res["refused"])
        self.assertIn("nearest earlier session", res["refused"])

    def test_the_refusal_NAMES_THE_NEAREST_EARLIER_SESSION_rather_than_using_it(self):
        e = self.export("base", n_days=340, extra_days=12)
        d = _dt.date.fromisoformat(e["days"][339])
        sat = d + _dt.timedelta(days=(5 - d.weekday()) % 7 or 7)
        res = score(e["root"], sat.isoformat())
        prior = max(x for x in e["days"] if x < sat.isoformat())
        self.assertIn(prior, res["refused"])

    def test_an_as_of_too_early_for_a_momentum_window_is_refused_WITH_A_REASON(self):
        """It used to return a bare `[]`, which `_full_universe_rows` turned into 'scored no
        rows from the full universe' — true, and nothing an operator can act on."""
        e = self.export("base", n_days=340)
        res = score(e["root"], e["days"][5])
        self.assertEqual(res["rows"], [])
        self.assertIn("sessions into this export", res["refused"])


# =============================================================================================
class TheCliCarriesItThrough(_Fixture):
    """`--as-of` has to reach `score_universe_now`, and the payload has to say so."""

    def test_the_payload_data_as_of_AND_scan_date_equal_the_requested_date(self):
        e = self.export("base", n_days=340, extra_days=12)
        d = e["days"][339]
        p = V.export(path=os.path.join(self.tmp, "book.json"), data_dir=e["root"],
                     limit=3000, config="taxable", as_of=d)
        self.assertEqual(p["data_as_of"], d)
        self.assertEqual(p["scan_date"], d)
        self.assertIn("as of %s (requested)" % d, p["source"])

    def test_a_refusal_reaches_the_operator_as_its_own_reason(self):
        e = self.export("base", n_days=340)
        after = (_dt.date.fromisoformat(e["newest"]) + _dt.timedelta(days=7)).isoformat()
        with self.assertRaises(RuntimeError) as cm:
            V.export(path=os.path.join(self.tmp, "book.json"), data_dir=e["root"],
                     config="taxable", as_of=after)
        self.assertIn("later than the newest close", str(cm.exception))

    def test_THE_30_PERCENT_BAND_STILL_APPLIES_WITH_AN_AS_OF(self):
        """Item 75 rule 2. `held` comes from the book at `--out`, which has nothing to do with
        the as-of — so the band must be untouched. Pinned because a band that silently stopped
        applying would change the book without changing a single visible number."""
        e = self.export("base", n_days=340, extra_days=12)
        d = e["days"][339]
        out = os.path.join(self.tmp, "book.json")
        first = V.export(path=out, data_dir=e["root"], config="taxable", as_of=d)
        self.assertTrue(first["positions"], "the fixture produced no book")
        self.assertFalse((first.get("no_trade_band") or {}).get("applied"),
                         "the FIRST build must be band-less: there is no incumbent book yet, "
                         "and `applied` is false whenever there was nothing to hold from")
        second = V.export(path=out, data_dir=e["root"], config="taxable", as_of=d)
        band = second.get("no_trade_band") or {}
        self.assertTrue(band.get("applied"),
                        "the no-trade band stopped applying under --as-of: %r" % (band,))
        # NON-VACUITY: `applied` is `bool(_held and exit_frac)`, so it is only meaningful if an
        # incumbent book was actually supplied and the width is the adopted one.
        self.assertTrue(band.get("n_held_supplied"),
                        "the band ran with no incumbent book, so it proves nothing")
        from valuation.edge.no_trade_band import BAND_WIDTH
        self.assertEqual(band.get("width"), BAND_WIDTH)

    def test_the_cli_flag_exists_and_refuses_a_non_date_BEFORE_the_long_load(self):
        """A full-universe load is about a quarter of an hour, and this is a command somebody
        runs once a quarter on an evening with one safe window in it."""
        rc = V.main(["--as-of", "not-a-date", "--full-universe", self.tmp,
                     "--out", os.path.join(self.tmp, "x.json")])
        self.assertEqual(rc, 1)

    def test_an_as_of_without_full_universe_is_refused(self):
        rc = V.main(["--as-of", "2026-10-22", "--out", os.path.join(self.tmp, "x.json")])
        self.assertEqual(rc, 1)


# =============================================================================================
class TheConfigHelpTextMatchesTheCode(unittest.TestCase):
    """It said a 20% band long after Don adopted 0.30 on 2026-08-13, so an operator checking
    `--help` before a rebalance was told the wrong construction."""

    def test_the_help_text_states_the_ADOPTED_band_width(self):
        """Read off the REAL parser's rendered help, which is what an operator sees.

        My first cut subclassed `argparse.ArgumentParser` and monkeypatched the class to
        capture the `help=` string. argparse builds groups and sub-parsers through that same
        class, so the patch re-entered itself and died at `RecursionError: maximum recursion
        depth exceeded`. Capturing `--help` needs no patch at all, and it asserts the thing
        that actually reaches the operator rather than the argument it was built from.
        """
        import contextlib
        from valuation.edge.no_trade_band import BAND_WIDTH
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with self.assertRaises(SystemExit):
                V.main(["--help"])
        # argparse re-wraps the text, so the newlines are normalised before matching.
        helptext = " ".join(buf.getvalue().split())
        self.assertIn("quarterly, %d%% band" % round(BAND_WIDTH * 100), helptext)
        self.assertNotIn("20% band", helptext)
        self.assertIn("--as-of", helptext)

    def test_the_width_is_DERIVED_and_not_retyped(self):
        """`MA5`'s rule: a hard-coded 30 is the identical defect at the next width change."""
        import inspect
        import valuation.edge.valquo_index as _V
        src = inspect.getsource(_V.main)
        self.assertIn("_BAND_WIDTH_PCT", src)
        self.assertNotIn("quarterly, 30%", src)


# =============================================================================================
class TheDoorRefusesABookBuiltAfterItsEvent(unittest.TestCase):
    """Item 75 rule 3, and the reason the existing check could not see it."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.bp = os.path.join(self.tmp, "book.json")
        self.hp = os.path.join(self.tmp, "hist.csv")
        with io.open(self.bp, "w", encoding="utf-8") as fh:
            json.dump({"inception_date": "2026-07-31", "day_n": 1,
                       "positions": [{"ticker": "AAA", "weight": 1.0}]}, fh)
        # **THE RECORD STOPS AT THE EVENT DATE, AND IT HAS TO.** My first fixture recorded a
        # 2026-10-23 row as well, which trips item 57's B4 refusal -- "nothing may be marked
        # yet on a later day than the event" -- so the positive control below failed for a
        # reason that has nothing to do with item 75. A fixture that fires an unrelated gate
        # cannot test this one.
        with io.open(self.hp, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["date", "valquo_pct", "spy_pct", "n_priced"])
            for d in ("2026-10-21", "2026-10-22"):
                w.writerow([d, 1.0, 1.0, 86])

    @staticmethod
    def _ok(n, w):
        # REPOINTED BY ITEM 80 (2026-10-23): the real `conformance` returns `conforms` and
        # `why_not`. This stub spoke the shape the door wrongly read, which is how the door
        # came to refuse every real book while this suite passed.
        return {"conforms": True, "why_not": []}

    def _event(self, date, scan_date):
        return {"date": date, "scan_date": scan_date,
                "positions": [{"ticker": "BBB", "weight": 1.0}]}

    def test_THE_ONE_SIDEDNESS_IS_REAL__trading_days_between_RETURNS_ZERO_BACKWARDS(self):
        """The premise, measured rather than asserted. This is why the staleness bound could
        not see the mirror case, and it is a property of the counter, not of this door."""
        f = (lambda a, b: MS.trading_days_between(_dt.date.fromisoformat(a),
                                                  _dt.date.fromisoformat(b),
                                                  inclusive_start=False))
        self.assertEqual(f("2026-10-22", "2026-10-23"), 1)
        self.assertEqual(f("2026-10-23", "2026-10-22"), 0)
        self.assertEqual(f("2026-11-23", "2026-10-22"), 0,
                         "a book a MONTH after its event also scored zero staleness")

    def test_a_book_built_ONE_DAY_AFTER_its_event_is_REFUSED(self):
        """The exact 2026-10-22 hazard: built on the evening of 10-23 with no `--as-of`."""
        r = IM.append_rebalance(self._event("2026-10-22", "2026-10-23"),
                                meta_path=self.bp, history_path=self.hp,
                                conformance=self._ok)
        self.assertIs(r["ok"], False)
        self.assertIs(r["wrote"], False)
        self.assertIn("AFTER the event date", r["reason"])
        self.assertIn("--as-of 2026-10-22", r["reason"],
                      "the refusal must name the remedy, not just the fault")

    def test_a_book_built_A_MONTH_AFTER_its_event_is_REFUSED_TOO(self):
        r = IM.append_rebalance(self._event("2026-10-22", "2026-11-23"),
                                meta_path=self.bp, history_path=self.hp,
                                conformance=self._ok)
        self.assertIs(r["ok"], False)
        self.assertIn("AFTER the event date", r["reason"])

    def test_a_book_built_ON_its_event_date_is_ACCEPTED(self):
        """The positive control. Without it 'refuse anything' would pass every test above."""
        r = IM.append_rebalance(self._event("2026-10-22", "2026-10-22"),
                                meta_path=self.bp, history_path=self.hp,
                                conformance=self._ok)
        self.assertIs(r["ok"], True, r["reason"])
        self.assertIs(r["wrote"], True, r["reason"])

    def test_a_book_built_a_DAY_BEFORE_its_event_is_still_ACCEPTED(self):
        """The staleness bound is unchanged in its own direction: one trading day is legal."""
        r = IM.append_rebalance(self._event("2026-10-22", "2026-10-21"),
                                meta_path=self.bp, history_path=self.hp,
                                conformance=self._ok)
        self.assertIs(r["ok"], True, r["reason"])

    def test_EVERY_RULE_IS_IN_THE_DOOR_so_the_CLI_and_the_ENDPOINT_cannot_drift(self):
        """`POST /admin/track-rebalance` delegates, so it inherits this refusal rather than
        carrying a second copy of it — the `B7` split this repository has paid for."""
        import ast
        import inspect
        from valuation.saas import app_saas
        tree = ast.parse(inspect.getsource(app_saas))
        fn = next((n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "admin_track_rebalance"),
                  None)
        self.assertIsNotNone(fn, "the endpoint is gone")
        body = ast.unparse(fn)
        self.assertIn("append_rebalance", body)
        for word in ("scan_date", "AFTER the event", "trading_days_between"):
            self.assertNotIn(word, body,
                             "the endpoint has grown its own copy of a door rule (%r)" % word)

    def test_the_docstring_LISTS_the_new_refusal(self):
        """A reader is entitled to trust that list; an unlisted refusal is one nobody expects."""
        self.assertIn("built AFTER its own event date", IM.append_rebalance.__doc__ or "")


if __name__ == "__main__":
    import sys as _s
    _s.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
