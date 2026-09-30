# -*- coding: utf-8 -*-
"""MC9 — the SEP $ADV / OHLC instrument.

WHAT THESE PIN, and every one is a defect this project has already paid for once:

* **The window is the LIVE SCREEN'S, and there is only one copy of it.** `MIN_AVG_DOLLAR_VOLUME`
  is calibrated against `prices.py:243`'s ~60-session mean, so a second `60` declared here would
  be `MA5`'s frozen-constant family: two definitions that must agree and nothing making them.
* **The roll is DELEGATED, not re-implemented** (`B7`). One shift-and-roll, so the SEP and CRSP
  series cannot drift apart in what they mean.
* **A missing export RAISES.** Returning an empty result would read as "this universe has no
  volume" -- which is precisely the false claim (`P1`: *"SEP is not on disk in any form"*) this
  instrument exists to correct.
* **`MB15` ORDERING IS STRUCTURAL.** Nothing in the module or its runners may rank, filter or
  score, and that is asserted against the syntax tree rather than promised in a docstring.
* **The sidecars go BESIDE the shipped price files** (`C3`: default payloads bit-identical).
"""
from __future__ import annotations

import ast
import io
import os
import unittest

import pandas as pd

import state_isolation  # noqa: F401  (must precede any `valuation` import)

from valuation.edge import adv_sep as A
from valuation.edge import adv as ADV

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with io.open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def _tree(*parts):
    return ast.parse(_read(*parts))


class TestTheWindowIsTheLiveScreens(unittest.TestCase):

    def test_there_is_no_second_sixty_declared_here(self):
        """`MA5`: the constant is IMPORTED from `adv.py`, which already ties it to the live
        screen. A module-level `60` here would be a second definition of a calibrated bar."""
        self.assertIs(A.ADV_WINDOW_SESSIONS, ADV.ADV_WINDOW_SESSIONS)
        tree = _tree("valuation", "edge", "adv_sep.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and "WINDOW" in t.id.upper():
                        self.fail("adv_sep declares its own window constant: %s" % t.id)

    def test_the_live_screens_window_has_not_moved(self):
        """Read the SYNTAX TREE of `prices.py`, not its text.

        The existing pin in `tests/test_adv.py:124` asserts the SUBSTRING `"min(60, n)"` appears
        in the source, which would also pass if the only occurrence were inside a comment or a
        docstring -- the substring family this record has been bitten by repeatedly. This finds
        the actual `min(60, n)` CALL and reads its literal.
        """
        tree = _tree("valuation", "screener", "prices.py")
        windows = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "min" and len(node.args) == 2
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, int)
                    and isinstance(node.args[1], ast.Name) and node.args[1].id == "n"):
                windows.append(node.args[0].value)
        self.assertIn(ADV.ADV_WINDOW_SESSIONS, windows,
                      "the live screen's ADV window moved (found %r); the panel instrument now "
                      "measures a different quantity from the constant it shares with "
                      "MIN_AVG_DOLLAR_VOLUME" % (windows,))

    def test_the_ast_pin_is_not_vacuous(self):
        """A positive control: the finder must locate at least one such call, or the test above
        passes by seeing nothing."""
        tree = _tree("valuation", "screener", "prices.py")
        n = sum(1 for x in ast.walk(tree)
                if isinstance(x, ast.Call) and isinstance(x.func, ast.Name)
                and x.func.id == "min")
        self.assertGreater(n, 0)


class TestTheRollIsDelegated(unittest.TestCase):

    def test_adv_sep_calls_advs_roll_rather_than_rewriting_it(self):
        tree = _tree("valuation", "edge", "adv_sep.py")
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("adv"):
                imported.update((a.asname or a.name) for a in node.names)
        self.assertIn("_crsp_adv_series", imported,
                      "the CRSP roll is not imported; B7 says one implementation")
        self.assertNotIn("rolling", _read("valuation", "edge", "adv_sep.py"),
                         "adv_sep re-implements the rolling window instead of delegating")

    def test_the_window_ends_on_the_PRIOR_session(self):
        """A screen applied when selecting on D may not read D's own tape. The last session's
        volume must not enter its own ADV."""
        rows = [("2020-01-%02d" % d, 1.0, 1.0, 1.0, 10.0, 100.0, 10.0)
                for d in range(1, 26)]
        rows.append(("2020-01-26", 1.0, 1.0, 1.0, 10.0, 10_000_000.0, 10.0))
        s = A.adv_series({"AAA": rows}, window=60, min_sessions=5)
        last = s[s["date"].astype(str).str[:10] == "2020-01-26"]
        self.assertEqual(len(last), 1)
        self.assertLess(float(last["adv"].iloc[0]), 10_000.0,
                        "the selection day's own enormous volume entered its ADV")


class TestMissingIsNotEmpty(unittest.TestCase):

    def test_a_missing_export_raises(self):
        with self.assertRaises(A.SepUnavailable):
            A.assert_header(os.path.join(ROOT, "no_such_sep.csv"))

    def test_a_changed_header_raises_rather_than_being_read_positionally(self):
        import tempfile
        p = os.path.join(tempfile.mkdtemp(), "sep.csv")
        with io.open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write("ticker,date,close,volume\n")
        with self.assertRaises(A.SepUnavailable):
            A.assert_header(p)


class TestTheSplitPairing(unittest.TestCase):
    """Dollar volume is split-INVARIANT when both legs share a basis. SEP pairs adjusted close
    with adjusted volume; the one wrong combination is `closeunadj * volume`, and it is wrong by
    exactly the split factor."""

    def test_dollar_volume_does_not_apply_crsps_abs(self):
        """`adv.dollar_volume` takes `abs(prc)` for CRSP's negative bid/ask convention. SEP has
        no such convention, so borrowing it would turn a negative close -- a data fault worth
        seeing -- into a positive dollar volume.

        THE FIRST CUT OF THIS TEST BANNED THE SUBSTRING `"abs("` AND FIRED ON THE DOCSTRING
        THAT EXPLAINS WHY `abs()` IS NOT USED -- the substring-ban family, in a test written by
        someone who had just recorded that family twice in the same session. The ban is on a
        CALL, so the check reads call nodes and the prose is invisible to it.
        """
        src = _read("valuation", "edge", "adv_sep.py")
        fn = [n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "dollar_volume"][0]
        calls = []
        for n in ast.walk(fn):
            if isinstance(n, ast.Call):
                f = n.func
                name = f.id if isinstance(f, ast.Name) else getattr(f, "attr", None)
                if name == "abs":
                    calls.append(ast.unparse(n))
        self.assertEqual(calls, [],
                         "adv_sep.dollar_volume applies abs(): that is CRSP's negative "
                         "bid/ask convention, which SEP does not have, and it would hide a "
                         "negative close instead of surfacing it")

    def test_the_abs_ban_is_not_vacuous(self):
        """A positive control: the finder must see a call in a function that HAS one, or the
        check above passes by never looking at a call node."""
        fn = [n for n in ast.walk(_tree("valuation", "edge", "adv.py"))
              if isinstance(n, ast.FunctionDef) and n.name == "dollar_volume"][0]
        found = [ast.unparse(n) for n in ast.walk(fn)
                 if isinstance(n, ast.Call)
                 and (getattr(n.func, "id", None) == "abs"
                      or getattr(n.func, "attr", None) == "abs")]
        self.assertTrue(found, "adv.dollar_volume no longer calls abs(); the control is stale")

    def test_the_invariance_holds_on_a_synthetic_two_for_one(self):
        """Before a 2:1 split an adjusted close of 50 pairs with an adjusted volume of 200;
        as-traded that is 100 and 100. Both give 10,000."""
        adj = A.dollar_volume([50.0], [200.0])
        astraded = A.dollar_volume([100.0], [100.0])
        self.assertAlmostEqual(float(adj[0]), float(astraded[0]), places=9)
        # and the MIXED pairing is wrong by the factor, which is the defect being guarded
        mixed = A.dollar_volume([100.0], [200.0])
        self.assertAlmostEqual(float(mixed[0]) / float(adj[0]), 2.0, places=9)


class TestItRanksNothing(unittest.TestCase):
    """`MB15` ordering, asserted against the tree rather than promised."""

    FORBIDDEN = ("fwd_ret", "MIN_AVG_DOLLAR_VOLUME", "quantile_backtest",
                 "holdout_compare_panels", "top_decile_alpha")

    def _names(self, *parts):
        tree = _tree(*parts)
        out = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Name):
                out.add(n.id)
            elif isinstance(n, ast.Attribute):
                out.add(n.attr)
            elif isinstance(n, ast.Constant) and isinstance(n.value, str):
                out.add(n.value)
        return out

    def test_the_module_scores_nothing(self):
        got = self._names("valuation", "edge", "adv_sep.py")
        for f in self.FORBIDDEN:
            self.assertNotIn(f, got, "adv_sep references %r; MB15 forbids an arm here" % f)

    def test_the_runners_score_nothing(self):
        for s in ("mc9_adv_sep.py", "mc9_fidelity.py"):
            got = self._names("scripts", s)
            for f in self.FORBIDDEN:
                self.assertNotIn(f, got, "%s references %r; MB15 forbids an arm here" % (s, f))


class TestTheSidecarsGoBeside(unittest.TestCase):

    def test_the_output_dir_is_not_the_shipped_price_dir(self):
        """`C3`: the default panel payloads stay bit-identical, which requires that nothing is
        written into `data/backtest/prices/`."""
        self.assertNotIn("prices", A.OHLCV_DIRNAME.replace(os.sep, "/").split("/"))
        self.assertEqual(A.OHLCV_HEADER[0], "date")
        self.assertIn("volume", A.OHLCV_HEADER)

    def test_the_shipped_price_header_is_still_two_columns(self):
        """The record correction rests on this: the derived price files carry date,close ONLY."""
        for root in (os.path.join(ROOT, "data"),
                     r"C:\Users\donni\Downloads\valuation-tool\data"):
            p = os.path.join(root, "backtest", "prices", "AAPL.csv")
            if os.path.exists(p):
                with io.open(p, encoding="utf-8") as fh:
                    self.assertEqual(fh.readline().strip(), "date,close")
                return
        self.skipTest("data/backtest/prices absent (gitignored); nothing to check")


class TestNonPositiveVolumeIsCounted(unittest.TestCase):

    def test_a_zero_volume_session_is_counted_and_not_scored(self):
        """A zero dollar volume sits below every floor, so admitting it converts 'we cannot see
        this session' into 'this name did not trade'."""
        import tempfile
        p = os.path.join(tempfile.mkdtemp(), "sep.csv")
        with io.open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(",".join(A.SEP_HEADER) + "\n")
            fh.write("AAA,2020-01-02,1,1,1,10,0,10,10,2020-01-03\n")
            fh.write("AAA,2020-01-03,1,1,1,10,500,10,10,2020-01-04\n")
        res = A.scan(p, ["AAA"], start="2019-01-01")
        self.assertEqual(res["census"]["nonpositive_volume_rows"], 1)
        self.assertEqual(res["census"]["rows_kept"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
