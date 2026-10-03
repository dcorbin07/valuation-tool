# -*- coding: utf-8 -*-
"""E8 — the hot list credited a vendor that served nothing, and said so in the same payload.

THE DEFECT
----------
`screen.run` returned `provider: provider.name` -- a fact about CONFIGURATION -- and the hot
list's meta line rendered it. The `health` dict in the SAME response recorded
`api_budget.served_by_fmp: 0`, `api_budget.fmp_disabled_mid_scan: true` and a 402 Payment
Required in `fmp_error_sample`, with 698 names served by the free fallback and 1,415 carrying
broker data. So the header read "Financial Modeling Prep" for a scan in which Financial
Modeling Prep served zero names, and the evidence was one key away.

WHY THIS IS A FAMILY AND NOT A ONE-OFF
--------------------------------------
`hero.py` carries the sharpest version of the opposite direction: a payload that honestly set
`source: "paper-sandbox"` while the template never rendered it, and the lesson recorded there
is that *"a label that a surface can decline to show is not a safeguard"*. This is the inverse
and it is worse, because nothing looks wrong: a label that is never required to AGREE with the
census beside it is not a measurement, however honest the census is.

WHAT THE REPAIR DOES NOT DO
---------------------------
It does not redefine `provider`. `save_snapshot` and `archive_scan` persist that string, so
changing its meaning would quietly change what every archived row says. The derived label is
ADDITIVE -- PT-SPMO's judgement -- and the configured name travels beside it, because "what
was this meant to use" is a real question and the two disagreeing is the part worth seeing.

It is also derived at READ time in `/api/hotstocks` rather than persisted at scan time, so
snapshots already on disk get the honest label: the census was always stored, it was simply
never consulted by the thing that named the source.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from valuation.screener.providers import served_by, FreeProvider, FMPProvider  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPJS = os.path.join(REPO, "valuation", "web", "static", "app.js")

CONFIGURED = FMPProvider.name

#: The state measured on the live service, from the brief. Reproduced as a fixture so the
#: assertions below are about THAT scan and not about a hypothetical one.
LIVE = {
    "api_budget": {"served_by_fmp": 0, "served_by_free_fallback": 698,
                   "fmp_disabled_mid_scan": True, "fmp_errors": 3,
                   "fmp_error_sample": ["402 Payment Required"]},
    "fundamentals": {"broker": {"names_with_broker_data": 1415, "names_broker_only": 702}},
}


class TheLiveState(unittest.TestCase):
    """The scan that was on the site when this was raised."""

    def setUp(self):
        self.r = served_by(LIVE, CONFIGURED)

    def test_it_does_NOT_credit_the_configured_vendor(self):
        """The whole defect in one assertion."""
        self.assertNotEqual(self.r["label"], CONFIGURED)

    def test_it_names_the_stack_that_actually_served(self):
        self.assertEqual(self.r["label"], FreeProvider.name)

    def test_it_is_marked_measured_and_degraded(self):
        self.assertTrue(self.r["measured"])
        self.assertTrue(self.r["degraded"])

    def test_it_says_why_in_terms_of_what_the_census_recorded(self):
        why = self.r["reason"]
        self.assertIn("disabled mid-scan", why)
        self.assertIn(CONFIGURED, why)

    def test_the_configured_name_is_kept_rather_than_replaced(self):
        self.assertEqual(self.r["configured"], CONFIGURED)

    def test_the_counts_travel_with_the_label(self):
        c = self.r["counts"]
        self.assertEqual(c["fmp"], 0)
        self.assertEqual(c["free_fallback"], 698)
        self.assertEqual(c["names_with_broker_data"], 1415)
        self.assertTrue(c["fmp_disabled_mid_scan"])


class TheOtherStates(unittest.TestCase):
    """A label that only ever says one thing is not reading the census."""

    def test_the_configured_vendor_is_credited_when_it_really_served(self):
        r = served_by({"api_budget": {"served_by_fmp": 1500, "served_by_free_fallback": 0}},
                      CONFIGURED)
        self.assertEqual(r["label"], CONFIGURED)
        self.assertFalse(r["degraded"])
        self.assertTrue(r["measured"])

    def test_a_mixed_scan_names_both(self):
        r = served_by({"api_budget": {"served_by_fmp": 200, "served_by_free_fallback": 100}},
                      CONFIGURED)
        self.assertIn(CONFIGURED, r["label"])
        self.assertIn(FreeProvider.name, r["label"])
        self.assertTrue(r["degraded"])
        self.assertIn("200", r["reason"])
        self.assertIn("100", r["reason"])

    def test_an_all_cache_scan_says_cache_rather_than_naming_a_vendor(self):
        """Neither counter fires on a cache hit, so the counts need not sum to the scan size.
        Claiming a vendor served names it never saw would be the same defect again."""
        r = served_by({"api_budget": {"served_by_fmp": 0, "served_by_free_fallback": 0,
                                      "calls_used": 0}}, CONFIGURED)
        self.assertEqual(r["label"], "cache")
        self.assertNotIn(CONFIGURED, r["label"])

    def test_broker_data_alone_is_enough_to_refuse_the_configured_label(self):
        """A scan served entirely by the broker still must not credit the paid vendor."""
        r = served_by({"api_budget": {"served_by_fmp": 0, "served_by_free_fallback": 0},
                       "fundamentals": {"broker": {"names_with_broker_data": 900}}},
                      CONFIGURED)
        self.assertNotEqual(r["label"], CONFIGURED)
        self.assertEqual(r["label"], FreeProvider.name)


class WithNoCensus(unittest.TestCase):
    """The honest degradation: name the configured provider, and SAY it is not a measurement."""

    def test_it_falls_back_to_the_configured_name(self):
        self.assertEqual(served_by({}, CONFIGURED)["label"], CONFIGURED)

    def test_but_it_is_marked_NOT_measured(self):
        r = served_by({}, CONFIGURED)
        self.assertFalse(r["measured"],
                         "a surface must be able to tell a reading from a default")
        self.assertIn("no source census", r["reason"])

    def test_a_malformed_health_block_does_not_raise(self):
        for bad in (None, "", [], {"api_budget": None}, {"api_budget": "x"}):
            try:
                r = served_by(bad, CONFIGURED)
            except Exception as e:                           # noqa: BLE001
                self.fail("served_by raised on %r: %r" % (bad, e))
            self.assertIn("label", r)


class TheScanResultCarriesIt(unittest.TestCase):
    """Read through the AST, not through a text sweep.

    MY FIRST CUT USED A COMMENT STRIPPER AND IT DESTROYED THE THING IT WAS LOOKING FOR. The
    stripper blanked every STRING token -- which is what makes a docstring-satisfied positive
    assertion impossible -- and the assertions here are on string LITERALS (`"source"` as a
    dict key), so they could never match. The tree is the right instrument: it sees the key
    and the call and cannot see prose about either.
    """

    def test_screen_run_returns_a_source_block_built_from_the_census(self):
        keys = _dict_keys_returned(os.path.join(REPO, "valuation", "screener", "screen.py"),
                                   "run_scan")
        self.assertIn("source", keys, "the scan result does not carry the derived label")
        self.assertIn("served_by", _calls_in(
            os.path.join(REPO, "valuation", "screener", "screen.py"), "run_scan"))

    def test_the_configured_provider_is_still_what_gets_ARCHIVED(self):
        """Redefining `provider` would change what every archived row means, so both the
        archive call and the returned `provider` key must survive unchanged."""
        path = os.path.join(REPO, "valuation", "screener", "screen.py")
        self.assertIn("provider", _dict_keys_returned(path, "run_scan"))
        self.assertIn("archive_scan", _calls_in(path, "run_scan"))


class TheApiCarriesIt(unittest.TestCase):
    def test_hotstocks_serves_the_derived_source(self):
        path = os.path.join(REPO, "valuation", "web", "app.py")
        fn = _hotstocks_fn(path)
        self.assertIsNotNone(fn, "could not find the hot-stocks handler")
        keys = _dict_keys_in(fn)
        self.assertIn("source", keys)
        self.assertIn("provider", keys, "the configured name is reported beside it")
        self.assertIn("_source_label", _calls_in_node(fn))


class TheRendererReadsIt(unittest.TestCase):
    """Read on the CODE, comments stripped.

    A positive assertion satisfied by a comment goes GREEN, which is the worse half of the
    comment-versus-code family: the test passes while the renderer ignores the field. The
    stripper is the one `test_accounting_risk.py` wrote after its own guard fired on its own
    block comment.
    """

    def _body(self):
        src = open(APPJS, encoding="utf-8").read()
        i = src.index("function renderHot")
        j = src.index("\nfunction ", i + 1)
        return _strip_js_comments(src[i:j])

    def test_the_meta_line_reads_the_derived_label(self):
        body = self._body()
        self.assertIn("d.source", body)
        self.assertIn("src.label", body)

    def test_the_meta_line_no_longer_renders_the_configured_name_directly(self):
        """`d.provider` survives only as the no-census fallback, never as the primary."""
        body = self._body()
        self.assertNotIn("scored · ${d.provider", body)

    def test_the_configured_name_is_SHOWN_when_the_two_disagree(self):
        """MUTATION FOUND THIS TEST, NOT THE CODE. The first cut asserted only that
        `src.configured` appears in the body -- and it appears in the `if` CONDITION
        (`src.label !== src.configured`) as well as in the rendered string, so deleting the
        append left the assertion passing while nothing reached the page. Referencing a field
        is not rendering it; the user-visible word is what has to be asserted."""
        body = self._body()
        self.assertIn("src.configured", body)
        self.assertIn("configured:", body,
                      "the configured vendor is referenced but never shown to a reader")

    def test_the_stripper_is_not_vacuous(self):
        """Both directions: it must keep code and drop comments, or every assertion above is
        passing on an empty string."""
        kept = _strip_js_comments("const a = 1; // note\n/* block */\nconst b = 2;")
        self.assertIn("const a = 1;", kept)
        self.assertIn("const b = 2;", kept)
        self.assertNotIn("note", kept)
        self.assertNotIn("block", kept)
        self.assertIn("function renderHot", self._body())


def _strip_js_comments(js: str) -> str:
    js = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
    return "\n".join(re.sub(r"//.*$", "", ln) for ln in js.splitlines())


def _tree(path):
    import ast
    return ast.parse(open(path, encoding="utf-8").read())


def _fn(path, name):
    import ast
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _hotstocks_fn(path):
    """The handler, found by the ROUTE it serves rather than by a function name nobody
    promised to keep."""
    import ast
    for node in ast.walk(_tree(path)):
        if not isinstance(node, ast.FunctionDef):
            continue
        for d in node.decorator_list:
            for s in ast.walk(d):
                if isinstance(s, ast.Constant) and s.value == "/api/hotstocks":
                    return node
    return None


def _dict_keys_in(node):
    import ast
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Dict):
            for k in n.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    out.add(k.value)
    return out


def _dict_keys_returned(path, fname):
    import ast
    fn = _fn(path, fname)
    assert fn is not None, "no function %r in %s" % (fname, path)
    out = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Return) and n.value is not None:
            out |= _dict_keys_in(n.value)
    return out


def _calls_in_node(node):
    import ast
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                out.add(f.id)
            elif isinstance(f, ast.Attribute):
                out.add(f.attr)
    return out


def _calls_in(path, fname):
    fn = _fn(path, fname)
    assert fn is not None, "no function %r in %s" % (fname, path)
    return _calls_in_node(fn)


if __name__ == "__main__":
    unittest.main(verbosity=2)
