# -*- coding: utf-8 -*-
"""`F23-JOIN` — the SEC ticker join repair.

The load-bearing test is `test_the_repair_fails_on_the_old_join`: it builds the exact shape the
diagnosis measured — one issuer filing as both `KO` and `(KO)` — and asserts the **as-filed** join
resolves none of the dirty rows while the repair resolves all of them. It fails against the old
behaviour by construction, which is what the brief asked the pin to do.
"""
from __future__ import annotations

import ast
import os
import sys
import unittest

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.studies import sec_ticker_join as SJ                         # noqa: E402

PANEL = {"KO", "FBC", "NHF", "SPAR", "CALX", "NOG", "EPG", "BRK.B", "ABC"}


def _rows(triples):
    return pd.DataFrame([{"cik": c, "filingdate": d, "ticker": s} for (c, d, s) in triples])


class CleanSymbol(unittest.TestCase):
    """The measured free-text shapes, one case per shape found in the real data."""

    def test_the_shapes_measured_in_the_real_data(self):
        for raw, want in (('"NHF"', "NHF"),
                          ("( EPG )", "EPG"),
                          ('("SPAR")', "SPAR"),
                          ("(CALX)", "CALX"),
                          ("(KO)", "KO"),
                          ("(NYSE:FBC)", "FBC"),
                          ("NASDAQ: ABC", "ABC"),
                          ("N O G", "NOG"),
                          ("ko", "KO"),
                          ("  KO  ", "KO"),
                          ("BRK.B", "BRK.B")):
            self.assertEqual(SJ.clean_symbol(raw), want, raw)

    def test_a_value_meaning_no_symbol_returns_empty(self):
        for raw in ("", "   ", "(NONE)", "NONE", "N/A", "NA", "none", None, float("nan")):
            self.assertEqual(SJ.clean_symbol(raw), "", repr(raw))

    def test_it_refuses_to_guess_rather_than_returning_a_plausible_wrong_symbol(self):
        """MA31's direction: a clean, confident, wrong ticker is worse than a missing one."""
        for raw in ("ACME CORPORATION", "FOO BAR CORP", "SEE EXHIBIT 99", "1234567",
                    "TOOLONGSYMBOL", "A B CORP"):
            self.assertEqual(SJ.clean_symbol(raw), "", repr(raw))

    def test_the_symbol_shape_is_not_vacuous(self):
        """A positive control on the gate itself: it must reject something, or every case above
        passes for the wrong reason."""
        self.assertIsNone(SJ._SYMBOL.match("TOOLONGSYMBOL"))
        self.assertIsNotNone(SJ._SYMBOL.match("KO"))

    def test_welding_is_restricted_to_single_letters(self):
        """`N O G` -> `NOG` is right; `FOO BAR` -> `FOOBAR` would be an invention."""
        self.assertEqual(SJ.clean_symbol("N O G"), "NOG")
        self.assertEqual(SJ.clean_symbol("FOO BAR"), "")


class PanelVariants(unittest.TestCase):
    def test_a_separator_insensitive_key_finds_a_class_share(self):
        v = SJ.panel_variants({"BRK.B", "KO"})
        self.assertEqual(v.get("BRKB"), "BRK.B")

    def test_a_colliding_key_is_dropped_rather_than_resolved_arbitrarily(self):
        v = SJ.panel_variants({"BRK.A", "BRKA"})
        self.assertNotIn("BRKA", v)


class DatedResolution(unittest.TestCase):

    def test_the_resolution_is_strictly_backward_looking(self):
        """A later rename may never reach back to an earlier filing."""
        rows = _rows([("1", "2010-01-01", "ABC"), ("1", "2015-01-01", "KO")])
        j = SJ.SecTickerJoin(rows, PANEL)
        self.assertEqual(j.resolve("1", "2009-06-01", as_filed="(GARBAGE CORP)"), "")
        self.assertEqual(j.resolve("1", "2012-06-01", as_filed="(GARBAGE CORP)"), "ABC")
        self.assertEqual(j.resolve("1", "2016-06-01", as_filed="(GARBAGE CORP)"), "KO")

    def test_an_unresolvable_filer_returns_empty_and_is_never_guessed_at(self):
        j = SJ.SecTickerJoin(_rows([("9", "2010-01-01", "ZZZZQQ")]), PANEL)
        self.assertEqual(j.resolve("9", "2011-01-01", as_filed="ZZZZQQ"), "")
        self.assertEqual(j.resolve("nosuchcik", "2011-01-01"), "")

    def test_the_as_filed_symbol_wins_when_it_resolves(self):
        """The most specific evidence on the row is preferred to the CIK's history."""
        rows = _rows([("1", "2010-01-01", "ABC"), ("1", "2011-01-01", "KO")])
        j = SJ.SecTickerJoin(rows, PANEL)
        self.assertEqual(j.resolve("1", "2011-01-01", as_filed="KO"), "KO")

    def test_the_full_history_variant_can_only_resolve_more(self):
        rows = _rows([("1", "2015-01-01", "KO")])
        j = SJ.SecTickerJoin(rows, PANEL)
        probe = _rows([("1", "2009-01-01", "(GARBAGE)")])
        self.assertEqual(list(j.resolve_frame(probe)), [""])
        self.assertEqual(list(j.resolve_frame_full_history(probe)), ["KO"])


class TheRepair(unittest.TestCase):

    def test_the_repair_fails_on_the_old_join(self):
        """THE PIN. One issuer, two spellings — the shape the diagnosis measured.

        `(KO)` is 18.1%-of-CIKs territory: the same filer appears under a dirty spelling and a
        clean one. The old join is `ticker.isin(panel)`, which resolves the clean rows and none of
        the dirty ones; the repair resolves both. Asserting both halves is what makes this a pin
        rather than a restatement — it fails if the repair is reverted AND it fails if the repair
        starts resolving rows the old join already handled differently.
        """
        rows = _rows([("1", "2010-01-04", "KO"),
                      ("1", "2010-02-04", "(KO)"),
                      ("1", "2010-03-04", '"KO"'),
                      ("1", "2010-04-04", "(NYSE:KO)")])
        old = rows["ticker"].isin(PANEL)
        self.assertEqual(int(old.sum()), 1, "the old join resolves only the clean spelling")

        new = SJ.repair(rows, PANEL)
        self.assertEqual(list(new["ticker"]), ["KO"] * 4)
        self.assertEqual(int(new["ticker"].isin(PANEL).sum()), 4)

    def test_an_unresolved_row_keeps_the_symbol_as_filed(self):
        """So the row set is comparable before and after: only newly-resolved rows move."""
        rows = _rows([("1", "2010-01-04", "ZZZZQQ")])
        self.assertEqual(list(SJ.repair(rows, PANEL)["ticker"]), ["ZZZZQQ"])

    def test_the_repair_does_not_mutate_its_input(self):
        rows = _rows([("1", "2010-01-04", "(KO)")])
        SJ.repair(rows, PANEL)
        self.assertEqual(list(rows["ticker"]), ["(KO)"])

    def test_the_cik_history_is_built_from_every_row_handed_in(self):
        """A caller passing the whole pull must get a complete history; truncating it first would
        resolve fewer rows for a reason unrelated to the date rule."""
        rows = _rows([("1", "2008-01-04", "KO"), ("1", "2010-01-04", "(GARBAGE)")])
        out = SJ.repair(rows, PANEL)
        self.assertEqual(list(out["ticker"]), ["KO", "KO"])


class TheMeasurementReadsNoOutcome(unittest.TestCase):

    def test_the_join_measurement_module_never_loads_a_forward_return(self):
        p = os.path.join(ROOT, "scripts", "f23_join_repair.py")
        src = open(p, encoding="utf-8").read()
        tree = ast.parse(src)
        names = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute):
                names.add(n.attr)
            elif isinstance(n, ast.Name):
                names.add(n.id)
            elif isinstance(n, ast.Constant) and isinstance(n.value, str):
                names.add(n.value)
        for banned in ("fwd_ret", "abnormal", "permutation_null", "score"):
            self.assertNotIn(banned, names,
                             "the join measurement must not reach an outcome (%s)" % banned)

    def test_the_banned_set_is_not_vacuous(self):
        """Positive control: the same scan DOES find those names in the arm that legitimately
        uses them, so the guard above is looking at something."""
        p = os.path.join(ROOT, "scripts", "insider_wide_arm.py")
        tree = ast.parse(open(p, encoding="utf-8").read())
        found = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        found |= {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertTrue({"abnormal", "permutation_null"} & found)


if __name__ == "__main__":
    unittest.main(verbosity=2)
