"""F-21 / F-22 — the V6-OPT put book, its random-day twin, and the series they needed.

THE LOAD-BEARING ONES:

1. **THE ENTRY SOURCE EXISTS NOW AND IS NOT `dip_rejects`.** `dip_rejects` is the COMPLEMENT of
   F-21's entry population; before `dip_healthy` the book's own names were recorded nowhere and
   it would have armed and qualified nobody — `RULE_ARMED_NEVER_FIRES`, which the harness itself
   calls *"indistinguishable in the records from a quiet market."*

2. **`None` REFUSES AND `[]` RECORDS** (audit #5 `H2`). *Ran and kept nobody* is an observation;
   *no screen ran* is a GAP. A zero written for a screen that never ran is a positive assertion
   of ABSENCE that a first-appearance study cannot tell from a real one.

3. **A THIN OR STALE SOURCE REFUSES BY NAME.** The declared precondition is mechanical, so the
   book reports a thin source as a thin source rather than returning an empty list.

4. **NEITHER BOOK IS ARMED**, and that is checkable: both are absent from `fleet_books.RULES`.

5. **F-22's DRAW IS DETERMINISTIC, SALTED, AND READS NO PRICE.** Any reader reproduces every
   entry from the declaration alone, and the timing cannot correlate with the dip signal.

    python tests/test_f21_f22.py
"""
from __future__ import annotations

import ast
import io
import json
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import state_isolation  # noqa: F401,E402

from valuation.edge import fleet as F  # noqa: E402
from valuation.edge import fleet_books as FB  # noqa: E402
from valuation.edge import fleet_history as FH  # noqa: E402

_SKIPS = []


def _skip(t, why):
    _SKIPS.append(why)
    t.skipTest(why)


def _src(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def _decl(book):
    t = _src("DECL_%s.md" % book)
    m = re.search(r"```json\n(.*?)\n```", t, re.S)
    assert m, "no fenced json block in DECL_%s.md" % book
    return json.loads(m.group(1))


class Declarations(unittest.TestCase):
    BOOKS = ("f21_v6opt_dip_csp", "f22_dip_csp_random_twin")

    def test_each_was_committed_ALONE(self):
        def git(*a):
            return subprocess.run(("git",) + a, cwd=REPO, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL).stdout.decode("utf-8", "replace")
        for b in self.BOOKS:
            rel = "DECL_%s.md" % b
            sha = ""
            for line in git("log", "--format=%H", "--", rel).splitlines():
                sha = line.strip()
            if not sha:
                _skip(self, "no git history for %s" % rel)
            files = [x for x in git("show", "--name-only", "--format=", sha).split() if x]
            self.assertEqual(files, [rel], "%s was NOT committed alone: %s" % (rel, files))

    def test_both_validate_with_ZERO_refusals(self):
        from valuation.edge import assignment as A
        A.register()
        for b in self.BOOKS:
            r = F.validate_declaration(_decl(b), book=b)
            self.assertTrue(r["ok"], "%s: %s" % (b, r["refusals"]))
            self.assertEqual(r["refusals"], [])

    def test_a_short_book_without_the_provider_is_REFUSED(self):
        """The positive control: without `assignment.register()` both must refuse, or the test
        above is passing on a validator that checks nothing."""
        import importlib
        from valuation.edge import assignment as A
        importlib.reload(F)
        r = F.validate_declaration(_decl("f21_v6opt_dip_csp"), book="f21_v6opt_dip_csp")
        self.assertIn("SHORT_BOOK_WITHOUT_ASSIGNMENT", r["refusals"])
        A.register()

    def test_the_schema_fields_do_not_collide_with_the_base_columns(self):
        for b in self.BOOKS:
            for f in _decl(b)["records_schema"]:
                self.assertNotIn(f, F.RECORD_COLUMNS,
                                 "%s: %r collides with a base RECORD_COLUMN" % (b, f))

    def test_F2_and_F19_are_folded_in_as_RECORDED_FIELDS(self):
        """The fleet review: both say of themselves that they are conventions, not books."""
        for b in self.BOOKS:
            sch = _decl(b)["records_schema"]
            self.assertIn("menu_depth", sch)
            self.assertIn("density_percentile", sch)

    def test_the_twin_inherits_the_ARM_s_clock_and_its_refusal(self):
        """`B1`: `MB1-SEL` was VOIDED because the covered subset was selected differently in two
        arms, with the confound twice the size of the effect and in the same direction."""
        d = _decl("f22_dip_csp_random_twin")
        self.assertEqual(d["structure"]["min_healthy_rows"],
                         _decl("f21_v6opt_dip_csp")["structure"]["min_healthy_rows"])
        self.assertEqual(d["structure"]["max_stale_sessions"],
                         _decl("f21_v6opt_dip_csp")["structure"]["max_stale_sessions"])
        self.assertIn("MB1-SEL", d["structure"]["cadence_amendment"])

    def test_the_twin_references_NO_price_derived_quantity_in_its_entry_rule(self):
        rule = _decl("f22_dip_csp_random_twin")["entry_rule"].lower()
        self.assertIn("calendar and the ticker and nothing else", rule)
        self.assertIn("sha256", rule)


class TheSeriesThatDidNotExist(unittest.TestCase):
    def test_dip_healthy_is_a_registered_series_and_is_NOT_dip_rejects(self):
        self.assertIn("dip_healthy", FH.SERIES)
        self.assertIn("dip_rejects", FH.SERIES)
        self.assertNotEqual(FH.SERIES["dip_healthy"], FH.SERIES["dip_rejects"])
        self.assertIn("COMPLEMENT", FH.SERIES["dip_healthy"][1])

    def test_None_REFUSES_and_an_EMPTY_LIST_is_an_observation(self):
        """Audit #5 `H2`, one level out. These must not read the same."""
        r = FH.record_dip_healthy(healthy=None)
        self.assertTrue(r["not_consulted"])
        self.assertFalse(r["wrote"])
        self.assertIn("did not run", r["reason"])
        # `[]` is a real observation -- it must NOT be refused as not-consulted.
        import inspect
        body = inspect.getsource(FH.record_dip_healthy)
        self.assertIn("if healthy is None", body,
                      "the refusal must key on None and never on falsiness, or an empty "
                      "screen is indistinguishable from an unrun one")

    def test_record_all_carries_the_new_series(self):
        import inspect
        self.assertIn("dip_healthy", inspect.getsource(FH.record_all))
        self.assertIn("healthy=None", inspect.signature(FH.record_all).__str__())

    def test_it_is_recorded_where_the_screen_is_ALREADY_paid_for_and_nowhere_new(self):
        """The fleet cycle deliberately does not run the dip screen -- ~188s against a 120s
        budget on its own comment. Adding a screen anywhere would re-create that timeout."""
        for rel in ("valuation/saas/scan_worker.py", "valuation/saas/app_saas.py"):
            self.assertIn("record_dip_healthy", _src(rel))
        # and no NEW screen call was introduced alongside it
        w = _src("valuation/saas/scan_worker.py")
        self.assertEqual(w.count("screen_snapshot("), 1,
                         "a second screen call appeared in the scan worker")


class EntryRules(unittest.TestCase):
    HIST = [{"date": "2026-10-02", "payload": ["AAA", "BBB"]},
            {"date": "2026-10-09", "payload": ["AAA", "CCC"]},
            {"date": "2026-10-16", "payload": ["CCC", "DDD"]}]

    def test_NEITHER_BOOK_IS_ARMED(self):
        """`declared, not armed` is checkable rather than asserted: `cycle()` reads `RULES`."""
        self.assertNotIn("f21_v6opt_dip_csp", FB.RULES)
        self.assertNotIn("f22_dip_csp_random_twin", FB.RULES)

    def test_a_THIN_series_refuses_BY_NAME_rather_than_returning_an_empty_list(self):
        st = FB.healthy_series_state([], "2026-10-13", min_rows=20, max_stale=5)
        self.assertFalse(st["ok"])
        self.assertIn("SOURCE TOO THIN", st["reason"])
        self.assertIn("not about the market", st["reason"])

    def test_a_STALE_series_refuses_BY_NAME(self):
        rows = [{"date": "2026-01-%02d" % d, "payload": ["A"]} for d in range(1, 25)]
        st = FB.healthy_series_state(rows, "2026-10-13", min_rows=20, max_stale=5)
        self.assertFalse(st["ok"])
        self.assertIn("SOURCE STALE", st["reason"])

    def test_and_a_HEALTHY_series_PASSES_so_the_refusal_is_not_vacuous(self):
        rows = [{"date": "2026-10-%02d" % d, "payload": ["A"]} for d in range(1, 25)]
        st = FB.healthy_series_state(rows, "2026-10-24", min_rows=20, max_stale=5)
        self.assertTrue(st["ok"])
        self.assertEqual(st["rows"], 24)

    def test_first_appearance_is_evaluated_at_the_SERIES_OWN_CADENCE(self):
        f = FB.f21_first_appearances(self.HIST, "2026-10-20")
        self.assertEqual(f, {"AAA": "2026-10-02", "BBB": "2026-10-02",
                             "CCC": "2026-10-09", "DDD": "2026-10-16"})

    def test_a_PRIOR_quarters_appearance_does_not_count(self):
        self.assertEqual(
            FB.f21_first_appearances([{"date": "2026-09-30", "payload": ["ZZZ"]}],
                                     "2026-10-20"), {})

    def test_select_skips_HELD_names_and_caps_by_MARKET_CAP(self):
        healthy = [{"ticker": "CCC", "market_cap": 5e10},
                   {"ticker": "DDD", "market_cap": 2e10},
                   {"ticker": "AAA", "market_cap": 9e10}]
        got = [r["ticker"] for r in FB.f21_select(healthy, self.HIST, "2026-10-20",
                                                  {"DDD"}, cap=2)]
        self.assertEqual(got, ["AAA", "CCC"])

    def test_a_name_NOT_on_the_recorded_list_is_never_entered(self):
        """Entering a name whose appearance was last week and which has since recovered off the
        list would be trading a memory -- `f11_select`'s own rule."""
        got = FB.f21_select([{"ticker": "BBB", "market_cap": 1e11}], self.HIST,
                            "2026-10-20", set(), cap=5)
        self.assertEqual([r["ticker"] for r in got], ["BBB"])
        got2 = FB.f21_select([{"ticker": "QQQ", "market_cap": 1e11}], self.HIST,
                             "2026-10-20", set(), cap=5)
        self.assertEqual(got2, [], "a name never on the recorded list was selected")

    def test_the_twin_draw_is_DETERMINISTIC_and_SALTED(self):
        pool = ["AAA", "BBB", "CCC", "DDD", "EEE"]
        a = FB.f22_draws(pool, "2026-10-13", salt="S", p=0.4)
        b = FB.f22_draws(pool, "2026-10-13", salt="S", p=0.4)
        self.assertEqual(a, b, "the draw is not reproducible from the declaration alone")
        self.assertNotEqual(a, FB.f22_draws(pool, "2026-10-13", salt="OTHER", p=0.4),
                            "the salt does nothing, so the draw is not salted")
        self.assertNotEqual(a, FB.f22_draws(pool, "2026-10-20", salt="S", p=0.4),
                            "the session date does nothing, so every day draws the same names")

    def test_the_twin_draw_reads_NO_PRICE(self):
        """AST, not a grep. The void condition is that the timing cannot correlate with the
        dip signal, and the only way to guarantee that is for no price to reach the draw."""
        tree = ast.parse(_src("valuation/edge/fleet_books.py"))
        fn = [n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "f22_draws"]
        self.assertEqual(len(fn), 1)
        names = {n.id for n in ast.walk(fn[0]) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(fn[0]) if isinstance(n, ast.Attribute)}
        for banned in ("drawdown", "price", "spot", "health", "iv", "vol", "close"):
            self.assertNotIn(banned, names,
                             "f22_draws reads %r, so its timing can correlate with the "
                             "signal" % banned)

    def test_the_draw_rate_tracks_p(self):
        pool = ["T%03d" % i for i in range(1000)]
        lo = len(FB.f22_draws(pool, "2026-10-13", salt="S", p=0.05))
        hi = len(FB.f22_draws(pool, "2026-10-13", salt="S", p=0.50))
        self.assertLess(lo, 120)
        self.assertGreater(hi, 400)
        self.assertLess(hi, 600)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
