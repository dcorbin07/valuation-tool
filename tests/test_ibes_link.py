# -*- coding: utf-8 -*-
"""`CORRECTED-FLOORS` part 3 -- the dated IBES link, as an instrument.

Structural tests run everywhere. Data-dependent ones SKIP LOUDLY: the licensed rows live on
`D:\\wrds`, which a CI runner does not have, and a guard whose input is absent passes while
checking nothing.
"""
from __future__ import annotations

import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import pandas as pd                                                         # noqa: E402

from valuation.edge import ibes_link as L                                   # noqa: E402

_SKIPS = []


def _skip(name, why):
    _SKIPS.append("%s (%s)" % (name, why))


def _src(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def _fixture():
    """A table with the EXACT hazard measured on the real data: one `oftic` claimed by several
    IBES tickers, interleaved in time."""
    return pd.DataFrame([
        ("ABT",  "ABT", "00282410", "ABBOTT LABS",      "1976-01-15", 1),
        ("@APL", "ABT", "AA604700", "APOLLO BATTERIES", "1993-12-16", 0),
        ("ABT",  "ABT", "00282410", "ABBOTT LABS",      "1998-02-19", 1),
        ("ABT1", "ABT", "00386B10", "ABSOLUTE SOFTWAR", "2000-07-20", 0),
        ("SOLO", "SOL", "11111110", "SOLO ONE",         "2005-01-01", 1),
    ], columns=["ticker", "oftic", "cusip", "cname", "sdates", "usfirm"])


class TheSpanBelongsToTheIbesTickerAndNotToTheExchangeTicker(unittest.TestCase):
    """**THE DEFECT THIS CLASS EXISTS FOR, measured on the real table.** `oftic == 'ABT'` is
    claimed by SIX different IBES tickers -- Abbott Labs, Apollo Batteries, Absolute Software,
    Ambit Properties, Aqua Bio Tech -- because companies on different exchanges share an exchange
    ticker. My first `spans()` grouped by `oftic` and took `shift(-1)` within it, which
    INTERLEAVED them: Abbott's span ended the day Apollo Batteries appeared in 1993 and a 2009
    date landed inside another company's span. Caught by disbelieving a route-agreement rate of
    0.742 whose examples returned `@39I` for Abbott."""

    def test_spans_are_grouped_by_the_ibes_ticker(self):
        t = ast.parse(_src("valuation/edge/ibes_link.py"))
        fn = next(n for n in ast.walk(t)
                  if isinstance(n, ast.FunctionDef) and n.name == "spans")
        gb = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
              and getattr(n.func, "attr", None) == "groupby"]
        self.assertTrue(gb, "spans() does not group at all")
        for c in gb:
            self.assertTrue(c.args, "groupby with no key")
            a = c.args[0]
            self.assertIsInstance(a, ast.Constant,
                                  "the grouping key must be a literal, not the `key` parameter")
            self.assertEqual(a.value, "ibes_ticker",
                             "grouping by %r interleaves companies that share an exchange "
                             "ticker -- the measured defect" % (a.value,))

    def test_abbotts_span_is_not_ended_by_apollo_batteries(self):
        """The regression itself, on a fixture carrying the real hazard."""
        sp, _cen = L.spans(_fixture(), key="oftic")
        got, st = L.resolve(sp, "ABT", "1995-06-01", key="oftic")
        # 1995 sits inside Abbott's 1976 span AND inside Apollo's 1993 span, so the honest
        # answer is AMBIGUOUS -- NOT Apollo, and NOT a silent Abbott.
        self.assertEqual(st, L.AMBIGUOUS,
                         "two companies hold this exchange ticker at this date; resolving to "
                         "either one silently is the defect")
        # and in 1980 only Abbott holds it
        got, st = L.resolve(sp, "ABT", "1980-06-01", key="oftic")
        self.assertEqual((got, st), ("ABT", L.OK))

    def test_the_cusip_route_is_unambiguous_where_the_ticker_route_is_not(self):
        """Why the CUSIP route is the PRIMARY: a CUSIP identifies a security, an exchange ticker
        does not."""
        sp, _ = L.spans(_fixture(), key="cusip")
        self.assertEqual(L.resolve(sp, "00282410", "1995-06-01", key="cusip"), ("ABT", L.OK))
        self.assertEqual(L.resolve(sp, "AA604700", "1995-06-01", key="cusip"), ("@APL", L.OK))


class TheLookAheadRefusalIsThePropertyItExistsFor(unittest.TestCase):
    """`S25`: returning the first span would read as coverage, produce a plausible identifier and
    be undetectable downstream -- the exact defect being removed, re-introduced by the thing
    removing it."""

    def test_a_date_before_the_first_span_is_NOT_COVERED_and_never_the_first_span(self):
        sp, _ = L.spans(_fixture(), key="cusip")
        got, st = L.resolve(sp, "11111110", "1999-01-01", key="cusip")
        self.assertEqual(st, L.NOT_COVERED)
        self.assertIsNone(got, "it returned the first span, which is the whole defect")

    def test_the_POSITIVE_control_so_it_cannot_pass_by_refusing_everything(self):
        sp, _ = L.spans(_fixture(), key="cusip")
        self.assertEqual(L.resolve(sp, "11111110", "2010-01-01", key="cusip"), ("SOLO", L.OK))

    def test_an_unknown_key_is_UNMAPPED_and_not_NOT_COVERED(self):
        """Two different facts: the key is absent, versus the key exists and the date is outside
        every span. `MB15`: a filter that never ran and one that ran and found nothing must not
        read the same."""
        sp, _ = L.spans(_fixture(), key="cusip")
        self.assertEqual(L.resolve(sp, "ZZZZZZZZ", "2010-01-01", key="cusip"),
                         (None, L.UNMAPPED))

    def test_the_last_span_is_left_OPEN_rather_than_given_a_sentinel(self):
        """A far-future sentinel stored in the table reads as coverage. It is used only inside
        the vectorised comparison and never persisted."""
        sp, _ = L.spans(_fixture(), key="cusip")
        last = sp[sp["ibes_ticker"] == "SOLO"]
        self.assertTrue(last["end"].isna().all(), "the open span was given an end date")


class TheVectorisedPathMustAgreeWithTheScalarDefinition(unittest.TestCase):
    """`B7`: a second implementation is PROVED to match, never assumed to. The scalar `resolve`
    is the definition; `resolve_many` exists because the per-cell loop was a full table scan per
    cell over 289,659 cells and would not have finished."""

    def test_they_agree_on_every_state_including_the_refusals(self):
        sp, _ = L.spans(_fixture(), key="oftic")
        cells = pd.DataFrame({
            "ticker": ["ABT", "ABT", "ABT", "SOL", "SOL", "ZZZ"],
            "date": pd.to_datetime(["1980-06-01", "1995-06-01", "2010-01-01",
                                    "1999-01-01", "2010-01-01", "2010-01-01"]),
        })
        many = L.resolve_many(sp, cells, key="oftic")
        seen = set()
        for i, (t, d) in enumerate(zip(cells["ticker"], cells["date"])):
            got, st = L.resolve(sp, t, d, key="oftic")
            self.assertEqual(st, many["state"].iloc[i], "state disagrees on %s %s" % (t, d))
            if st == L.OK:
                self.assertEqual(got, many["resolved"].iloc[i])
            seen.add(st)
        # NON-VACUITY: the comparison must span more than one state, or it proves nothing
        self.assertGreaterEqual(len(seen), 3,
                                "the fixture exercises only %r -- a one-state comparison is "
                                "not an agreement check" % (seen,))

    def test_the_runner_ABORTS_if_they_disagree(self):
        src = _src("scripts/ibes_link_validate.py")
        self.assertIn("disagrees with the scalar definition", src)
        t = ast.parse(src)
        guarded = False
        for n in ast.walk(t):
            if isinstance(n, ast.If) and "disagrees with the scalar definition" in ast.dump(
                    ast.Module(body=n.body, type_ignores=[])):
                self.assertNotIn("Constant(value=False)", ast.dump(n.test))
                guarded = True
        self.assertTrue(guarded, "nothing guards the abort")


class ItComputesNoOutcomeStatisticAnywhere(unittest.TestCase):
    """`MB15`: the instrument is validated BEFORE any hypothesis reads it. An instrument that
    scores an outcome on the way past is not an instrument."""

    FILES = ("valuation/edge/ibes_link.py", "scripts/ibes_link_validate.py")

    def test_no_forward_return_is_read_and_no_arm_is_scored(self):
        for rel in self.FILES:
            t = ast.parse(_src(rel))
            for n in ast.walk(t):
                if isinstance(n, ast.Constant) and isinstance(n.value, str):
                    continue                      # prose may NAME what the rule forbids
                if isinstance(n, ast.Attribute) and n.attr in ("fwd_ret", "forward_return"):
                    self.fail("%s reads a forward return" % rel)
                if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant):
                    if n.slice.value in ("fwd_ret", "bench_ret"):
                        self.fail("%s subscripts %r" % (rel, n.slice.value))
                if isinstance(n, ast.Call):
                    nm = getattr(n.func, "id", getattr(n.func, "attr", None))
                    if nm in ("quantile_backtest", "theme_ic", "cpcv_validate",
                              "incremental_ic", "composite_from_frame"):
                        self.fail("%s calls %s -- that is an arm, not an instrument" % (rel, nm))

    def test_the_artifact_declares_zero_trials_and_no_outcome(self):
        src = _src("scripts/ibes_link_validate.py")
        self.assertIn('"trials": 0', src)
        self.assertIn('"no_outcome_read": True', src)
        self.assertIn("MB15", src)

    def test_A9_is_named_as_NOT_RUN(self):
        """A9 is untested, not rejected, and its size-costume kill must be read FIRST."""
        src = _src("scripts/ibes_link_validate.py")
        self.assertIn("NO ARM", src)
        self.assertIn("A9 is NOT run", src)
        self.assertIn("size-costume", src)


class NoWrdsConnectionIsMade(unittest.TestCase):
    """`DECISIONS.md` 2026-10-04: one attempt per session, never a retry loop -- repeated
    failures disabled the account. Everything here reads the 2026-08-24 pull, so the rule is not
    engaged at all, which is the safest outcome available."""

    def test_nothing_imports_or_calls_wrds(self):
        for rel in ("valuation/edge/ibes_link.py", "scripts/ibes_link_validate.py"):
            t = ast.parse(_src(rel))
            for n in ast.walk(t):
                if isinstance(n, (ast.Import, ast.ImportFrom)):
                    mods = ([a.name for a in n.names]
                            + ([n.module] if isinstance(n, ast.ImportFrom) and n.module else []))
                    for m in mods:
                        self.assertNotIn("wrds", (m or "").lower().split(".")[0],
                                         "%s imports a WRDS client" % rel)
                if isinstance(n, ast.Call):
                    nm = getattr(n.func, "id", getattr(n.func, "attr", None))
                    self.assertNotIn(nm, ("connect", "Connection", "get_table", "raw_sql"),
                                     "%s makes a connection-shaped call" % rel)

    def test_licensed_rows_are_read_from_the_D_drive_and_never_the_repo(self):
        c = {}
        for n in ast.parse(_src("valuation/edge/ibes_link.py")).body:
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
                try:
                    c[n.targets[0].id] = ast.literal_eval(n.value)
                except (ValueError, SyntaxError):
                    pass
        raw = c.get("RAW")
        if raw is None:
            # it is an os.environ.get(...) call with a default -- read the default
            src = _src("valuation/edge/ibes_link.py")
            self.assertIn('"D:\\\\wrds"', src,
                          "the raw root must default to D:\\\\wrds, never inside the checkout")
        else:
            self.assertTrue(str(raw).upper().startswith("D:"))


class TheCoverageVerdictIsNotRoundedIntoAPass(unittest.TestCase):
    """SKIPS LOUDLY without the licensed pull. Route B's cell coverage is 0.69999551 against an
    inherited 0.70 floor -- it FAILS by 4.5e-6, about 1.3 cells in 289,659. `W-28`'s rule is
    that a pre-committed bar may not be relaxed after watching it fail, and the temptation here
    is to call it 0.70."""

    @classmethod
    def setUpClass(cls):
        cls.d = None
        import json
        try:
            from scripts.index_best import _data_root
            p = os.path.join(_data_root(), "free_analysis", "IBES_LINK_VALIDATION.json")
            if not os.path.exists(p):
                _skip("coverage", "IBES_LINK_VALIDATION.json absent")
                return
            with io.open(p, encoding="utf-8") as fh:
                cls.d = json.load(fh)
        except Exception as exc:                       # noqa: BLE001
            _skip("coverage", "%s" % exc)

    def test_the_floor_is_INHERITED_and_not_chosen_here(self):
        src = _src("scripts/ibes_link_validate.py")
        self.assertIn("COVERAGE_FLOOR = 0.70", src)
        self.assertIn("INHERITED", src)

    def test_a_route_below_the_floor_is_reported_below_it(self):
        if self.d is None:
            return
        cl = self.d["clears_inherited_floor"]
        cov = self.d["coverage"]
        for route, block in cov.items():
            k = "route_a_cells" if "route_a" in route else "route_b_cells"
            self.assertEqual(cl[k], bool(block["cell_coverage"] >= 0.70),
                             "%s's verdict disagrees with its own number" % route)

    def test_the_knife_edge_is_not_rounded(self):
        if self.d is None:
            return
        b = self.d["coverage"]["route_b_via_crsp_cusip"]["cell_coverage"]
        self.assertLess(b, 0.70, "route B is reported as clearing a floor it misses")
        self.assertGreater(b, 0.6999, "if this moved materially the write-up needs re-reading")

    def test_the_two_routes_agree_where_both_resolve(self):
        if self.d is None:
            return
        a = self.d["agreement_between_routes"]
        self.assertGreater(a["cells_both_resolve"], 1000,
                           "MB21: a perfect agreement over nothing is not a validation")
        self.assertGreater(a["agreement_rate"], 0.95,
                           "two dated routes disagreeing this much means one is wrong; the "
                           "first cut read 0.742 and the cause was my span construction")

    def test_the_look_ahead_refusal_is_non_vacuous_on_the_real_data(self):
        if self.d is None:
            return
        la = self.d["look_ahead_refusal"]
        self.assertGreater(la["cells_before_first_span"], 0,
                           "no cell predates its first span, so the refusal was never exercised")
        self.assertTrue(la["all_refused"])


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=1).result
    if _SKIPS:
        print("\nSKIPPED (licensed pull absent) - NOT counted as passes:")
        for s in _SKIPS:
            print("   - " + s)
    sys.exit(0 if r.wasSuccessful() else 1)
