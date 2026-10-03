# -*- coding: utf-8 -*-
"""THE DEFAULT A ROUTE RESOLVES IS INVISIBLE TO A TEST THAT CALLS THE CALLEE.

WHY THIS SUITE EXISTS
---------------------
Item 18 pointed the Index's performance card at `index_book_measured.card()` -- the served
book's own measurement -- and shipped a gate so that a named account type still gets its own
labelled preview::

    is_preview = config is not None

That is wrong by one step, and the step is in the CALLER. `/api/index-track` resolves its
default before calling::

    name = (request.args.get("config") or index_track.TRACKED_CONFIG).lower()

so `config` was never `None` inside `summarize`, `is_preview` was True on every request, and
the served card was **unreachable**. The live tab kept serving the +26.15% gross / +19.35% net
all-cap equal-weighted research decile -- the exact figure item 18 exists to retire -- for a
month, and 42 tests across two suites passed throughout.

Every one of those tests called `summarize()` directly, where the default really is `None`. So
the single path the public uses was the single path never exercised. **A default resolved in
the caller is invisible to a test that calls the callee**, and the only cure is to drive the
route.

It was found by the item-20/21/22 ground rule rather than by the suite: exercise the feature on
the live service after the land and report what it returned. `/api/index-track` on valquo.co
answered with `card.config: "taxable"`, `gross 0.2614725683528105`, and a
`generated_at_utc` a month old.

WHAT THIS SUITE PINS, AND WHAT IT DELIBERATELY DOES NOT
-------------------------------------------------------
It pins WHICH CARD each request gets, through the Flask test client, with no config argument
-- the shape a browser produces. It does not re-assert the served figures themselves;
`tests/test_index_book_measured.py` owns those, and a second copy of a number is a second
definition of it.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from valuation.screener.index_track import TRACKED_CONFIG, summarize   # noqa: E402
from valuation.screener import index_book_measured as M                # noqa: E402
from valuation.screener import settings as S                           # noqa: E402

#: What `index_book_measured.card()` stamps on itself. Read from the module rather than typed,
#: so renaming it there cannot leave this suite asserting a string nothing produces.
SERVED_CONFIG = M.card().get("config")
SERVED_MODE = M.card().get("mode")


def _client():
    from valuation.web.app import app
    app.config["TESTING"] = True
    return app.test_client()


class TheMarkerIsReal(unittest.TestCase):
    """Vacuity control: the two cards must be distinguishable at all."""

    def test_the_served_card_stamps_itself(self):
        self.assertTrue(SERVED_CONFIG, "the served card carries no `config` stamp")
        self.assertEqual(SERVED_MODE, "served")

    def test_no_account_type_is_named_served_index_book(self):
        """If a config were ever named this, every assertion below would go vacuous."""
        self.assertNotIn(SERVED_CONFIG, (S.BOOK_CONFIGS or {}))


class TheRouteServesTheServedBook(unittest.TestCase):
    """THE ASSERTION THE LIVE TAB FAILED FOR A MONTH."""

    def setUp(self):
        self.c = _client()

    def _card(self, qs=""):
        r = self.c.get("/api/index-track" + qs)
        self.assertEqual(r.status_code, 200, r.data[:300])
        d = json.loads(r.data.decode("utf-8"))
        if not d.get("available", True) and "backtested" not in d:
            self.skipTest("the live-track block is unavailable in this environment: %s"
                          % str(d.get("error"))[:200])
        return d, (d.get("backtested") or {}), ((d.get("backtested") or {}).get("card") or {})

    def test_the_bare_request_gets_the_served_books_card(self):
        """No query string -- what a browser sends."""
        d, bt, card = self._card()
        self.assertEqual(card.get("config"), SERVED_CONFIG,
                         "the default request served card.config=%r. That is the research "
                         "decile's derived card; item 18 requires the served book's own "
                         "measurement here." % (card.get("config"),))
        self.assertEqual(card.get("mode"), SERVED_MODE)
        self.assertIs(bt.get("is_the_served_book"), True)

    def test_asking_for_the_tracked_config_BY_NAME_gets_the_same_card(self):
        """`?config=taxable` is not a preview of anything: it IS the tracked construction."""
        _, bt, card = self._card("?config=" + TRACKED_CONFIG)
        self.assertEqual(card.get("config"), SERVED_CONFIG)
        self.assertIs(bt.get("is_the_served_book"), True)

    def test_the_route_does_not_serve_the_retired_provisional_figures(self):
        """+26.15% gross / +19.35% net, by value rather than by label.

        The strongest form available: it does not matter which key they arrive under or what
        they are called, they may not be on this card at all.
        """
        _, _, card = self._card()
        flat = json.dumps(card)
        for retired in ("0.2614725683528105", "0.1935258461619922"):
            self.assertNotIn(retired, flat,
                             "the retired provisional figure %s is on the Index's card"
                             % retired)

    def test_the_served_figures_ARE_on_the_card(self):
        """The positive half: absence of the wrong number is not presence of the right one."""
        _, _, card = self._card()
        keys = {ln.get("key") for ln in (card.get("lines") or [])}
        self.assertIn("roth", keys)
        self.assertIn("taxable", keys)
        self.assertIn("vs_spy", keys)

    def test_the_roth_line_leads(self):
        """18-AMEND: the Index is a Roth product, so the Roth treatment is first."""
        _, _, card = self._card()
        lines = card.get("lines") or []
        self.assertTrue(lines, "the card has no lines")
        self.assertEqual(lines[0].get("key"), "roth")


class AnotherAccountTypeIsStillAPreview(unittest.TestCase):
    """The positive control. Without this, 'always serve the served card' would pass every
    assertion above -- and that is the same defect pointed the other way, which is what the
    mutation cited in `index_track`'s own comment found."""

    def setUp(self):
        self.c = _client()

    def test_roth_gets_its_own_labelled_card(self):
        other = [n for n in (S.BOOK_CONFIGS or {}) if n != TRACKED_CONFIG]
        if not other:
            self.skipTest("only one book config exists, so there is no preview to test")
        name = other[0]
        r = self.c.get("/api/index-track?config=" + name)
        self.assertEqual(r.status_code, 200)
        d = json.loads(r.data.decode("utf-8"))
        bt = d.get("backtested") or {}
        card = bt.get("card") or {}
        if card.get("available") is False:
            self.skipTest("the derived card is unavailable here: %s"
                          % str(card.get("unavailable"))[:160])
        self.assertEqual(card.get("config"), name)
        self.assertNotEqual(card.get("config"), SERVED_CONFIG)
        self.assertIs(bt.get("is_the_served_book"), False)


class TheGateItself(unittest.TestCase):
    """`summarize`'s own predicate, stated as the three cases that occur."""

    def test_none_is_the_served_book(self):
        bt = summarize(None).get("backtested") or {}
        self.assertIs(bt.get("is_the_served_book"), True)

    def test_the_tracked_name_is_the_served_book(self):
        bt = summarize(TRACKED_CONFIG).get("backtested") or {}
        self.assertIs(bt.get("is_the_served_book"), True)

    def test_the_tracked_name_in_any_case_is_the_served_book(self):
        """The route lowercases, but `summarize` is importable and callers are not all routes."""
        bt = summarize(TRACKED_CONFIG.upper()).get("backtested") or {}
        self.assertIs(bt.get("is_the_served_book"), True)

    def test_another_name_is_a_preview(self):
        other = [n for n in (S.BOOK_CONFIGS or {}) if n != TRACKED_CONFIG]
        if not other:
            self.skipTest("only one book config exists")
        bt = summarize(other[0]).get("backtested") or {}
        self.assertIs(bt.get("is_the_served_book"), False)

    def test_the_predicate_is_not_keyed_on_whether_a_name_was_given(self):
        """Read from the source, because that IS the defect.

        Both the broken and the fixed version serve *a* card, so output alone cannot
        distinguish them on the one input the route never passes.
        """
        import ast
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "valuation", "screener", "index_track.py")
        with open(p, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        found = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == "is_preview"):
                found.append(ast.unparse(node.value))
        self.assertEqual(len(found), 1, "expected exactly one `is_preview = ...`: %r" % found)
        expr = found[0]
        self.assertIn("TRACKED_CONFIG", expr,
                      "the preview gate does not compare against the tracked config: " + expr)
        self.assertNotEqual(expr.replace(" ", ""), "configisnotNone",
                            "the gate is back to asking whether a name was given, which the "
                            "route always supplies")


if __name__ == "__main__":
    unittest.main(verbosity=2)
