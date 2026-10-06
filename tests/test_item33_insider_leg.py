# -*- coding: utf-8 -*-
"""The theme cache's insider column -- two producers, and the writer read the empty one.

    python tests/test_item33_insider_leg.py

MEASURED ON THE 2026-10-05 BUILD. `themes-assemble` succeeded for the first time and wrote
`theme_columns.json` with `coverage {'inst_accum': 0.8547, 'sm_breadth': 0.8547,
'insider_score': 0.012}`. The live hot list then served `theme_contributing.insider` **0.01**
against `institutional` **0.83** -- so the cache was built, the 13F leg worked, and the Form 4
leg contributed nothing.

THE CAUSE IS A B7 SPLIT: two producers, and the cache writer reads the one nothing fills.

  * `M.fetch_all`'s `insider` leg writes `live_themes/insider/<t>.json` and ran for all 1,500
    names (`insider 0+1500` in the log). It TRAVELS to the assemble job in the artifact.
  * `F2.build_live` reads `live_themes/form4_live/<t>.json` -- written ONLY by
    `F2.fetch4(current=True)`, which `main()` never called. The workflow also deliberately keeps
    `form4_live` out of the cache AND the artifact, so it starts empty in that job every time.

THE FIX RUNS THE MISSING PRODUCER RATHER THAN REPOINTING THE READER, and the PANEL is what
settles which is correct -- this is the load-bearing test in the file:

  * `insider_detail` (the crawl leg) returns **50.0** for a quiet window.
  * `insider_score_from_txns` (what `build_live` uses) returns **None**.
  * `fundamental_panel._insider_score` returns **None** when `net == 0 and buys == 0`.

So the gated formula matches the panel and the 50.0 is the deviation. Repointing the reader at
the crawl leg would have lifted coverage to ~85% of names ALL SITTING AT EXACTLY 50 -- the
179-name tie block `FIDELITY-2` rejected. It would have looked fixed and measured nothing, which
is why "coverage went up" is not the property under test here.
"""
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

import scripts.fidelity2_rebuild as F2          # noqa: E402
import scripts.live_theme_sources as M          # noqa: E402
import scripts.theme_cache_build as TC          # noqa: E402


class TheTwoScorersDisagreeExactlyWhereCoverageComesFrom(unittest.TestCase):
    def test_the_gated_formula_refuses_a_quiet_window(self):
        self.assertIsNone(F2.insider_score_from_txns([]))
        self.assertIsNone(F2.insider_score_from_txns(None))
        self.assertIsNone(F2.insider_score_from_txns([{"raw": None}]))

    def test_it_scores_a_window_that_has_transactions(self):
        v = F2.insider_score_from_txns([{"raw": 500_000.0}, {"raw": 250_000.0}])
        self.assertIsNotNone(v)
        self.assertGreater(v, 50.0, "net buying must score above neutral")

    def test_THE_PANEL_ALSO_REFUSES_A_QUIET_WINDOW(self):
        """The authority. If the panel returned a neutral here, the crawl leg's 50.0 would be
        the right behaviour and this whole item would be the wrong fix."""
        from valuation.edge import fundamental_panel as FP
        self.assertIsNone(FP._insider_score([], "2026-10-05"))
        quiet = [{"filingdate": "2026-09-01", "transactionshares": 0.0,
                  "transactionpricepershare": 0.0, "transactionvalue": 0.0}]
        self.assertIsNone(FP._insider_score(quiet, "2026-10-05"),
                          "the panel returned a neutral for a quiet window, which would make "
                          "the crawl leg's 50.0 correct and this fix wrong")

    def test_the_panel_scores_a_real_purchase(self):
        """Non-vacuity: the refusal above must not be 'this function always returns None'."""
        from valuation.edge import fundamental_panel as FP
        rows = [{"filingdate": "2026-09-01", "transactionshares": 1000.0,
                 "transactionpricepershare": 50.0}]
        self.assertIsNotNone(FP._insider_score(rows, "2026-10-05"))


class TheMissingProducerIsRun(unittest.TestCase):
    def _run(self, extra=(), aggregate=("31-DEC-2025", "31-MAR-2026"), coverage=0.84):
        """Drive `main()` far enough to reach the crawl, with every SEC leg stubbed."""
        import contextlib
        import io as _io
        import json as _json
        import tempfile
        d = tempfile.mkdtemp()
        uni = os.path.join(d, "u.txt")
        with open(uni, "w", encoding="utf-8") as fh:
            fh.write("AAPL" + chr(10) + "MSFT" + chr(10))
        root = os.path.join(d, "live_themes")
        os.makedirs(root, exist_ok=True)
        if aggregate:
            with open(os.path.join(root, "13f_aggregate.json"), "w", encoding="utf-8") as fh:
                _json.dump({"periods": list(aggregate), "shape": {}, "by_period": {}}, fh)
        seen = {"fetch4": [], "build_live": 0}

        saved = {"ROOT": M.DEFAULT_ROOT, "b13": M.build_13f, "fa": M.fetch_all,
                 "caps": TC.period_market_caps, "f4": F2.fetch4, "F2": TC.F2,
                 "head": M.head_published}
        M.DEFAULT_ROOT = root
        M.build_13f = lambda *a, **k: {"periods": [], "by_period": {}, "shape": {}}
        M.fetch_all = lambda *a, **k: {}
        M.head_published = lambda *a, **k: True
        TC.period_market_caps = lambda *a, **k: {}

        def _f4(**kw):
            seen["fetch4"].append(kw)
            return {}
        stub = types.SimpleNamespace(
            fetch4=_f4, F4_DIR_LIVE=F2.F4_DIR_LIVE, ROOT=F2.ROOT,
            build_live=lambda **kw: (seen.__setitem__("build_live", seen["build_live"] + 1)
                                     or {"rows": [], "n_served": 0,
                                         "coverage": {"insider_score": coverage}}))
        TC.F2 = stub
        F2.fetch4 = _f4
        buf = _io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(_io.StringIO()):
                rc = TC.main(["--universe", uni, "--as-of", "2026-10-05", *extra])
        finally:
            M.DEFAULT_ROOT, M.build_13f, M.fetch_all = saved["ROOT"], saved["b13"], saved["fa"]
            M.head_published = saved["head"]
            TC.period_market_caps, F2.fetch4, TC.F2 = saved["caps"], saved["f4"], saved["F2"]
        return rc, buf.getvalue(), seen

    def test_the_assemble_path_CRAWLS_the_current_form4_window(self):
        _rc, out, seen = self._run()
        self.assertEqual(len(seen["fetch4"]), 1,
                         "form4_live is never populated, so build_live reads an empty "
                         "directory and the insider column comes out ~0: " + out[-400:])
        self.assertIs(seen["fetch4"][0].get("current"), True,
                      "it crawled the ALIGNED window, which writes form4_aligned -- not the "
                      "directory build_live reads")

    def test_it_is_handed_the_SERVED_universe_and_not_the_pinned_default(self):
        """`fetch4`'s own docstring: the bare call resolves a PINNED snapshot, 'so this could
        only ever crawl the universe that file names, never the 1,500-name broker ranking the
        theme cache is built for' -- which is how the column came out empty the first time."""
        _rc, _out, seen = self._run()
        snap = seen["fetch4"][0].get("snapshot")
        self.assertTrue(snap, "no snapshot passed: it will crawl the pinned universe")
        self.assertNotEqual(snap, M.SNAPSHOT)

    def test_a_SHARD_does_not_crawl_it(self):
        """A shard holds a third of the universe and `fetch4` SKIPS names whose payload exists,
        so a shard's partial form4_live would be indistinguishable from a complete one."""
        _rc, _out, seen = self._run(extra=("--slice", "0/3"))
        self.assertEqual(seen["fetch4"], [], "a shard populated form4_live")

    def test_the_insider_coverage_is_REPORTED(self):
        """A coverage dict buried inside a `wrote ...` line is what let 0.012 pass unnoticed
        through a build that otherwise looked like a success."""
        _rc, out, _seen = self._run()
        self.assertIn("insider      coverage", out)

    def test_a_LOW_coverage_says_so_on_its_own_line(self):
        """0.012 is the figure the 2026-10-05 build actually wrote, so it is the figure used."""
        _rc, out, _seen = self._run(coverage=0.012)
        self.assertIn("BELOW 0.5", out)
        _rc2, out2, _s2 = self._run(coverage=0.84)
        self.assertNotIn("BELOW 0.5", out2, "the warning fires on a healthy coverage too")


class TheReaderIsNotRepointed(unittest.TestCase):
    def test_build_live_still_reads_form4_live_by_default(self):
        """The fix must be the missing PRODUCER. If a later change repoints this at the crawl
        leg, coverage jumps to ~85% of names all at exactly 50 -- the tie block FIDELITY-2
        rejected -- and it looks like a success."""
        import inspect
        src = inspect.getsource(F2.build_live)
        self.assertIn("F4_DIR_LIVE", src)

    def test_the_crawl_legs_scorer_is_still_a_different_object(self):
        """Stated as a measurement rather than trusted: `insider_detail` returns a neutral where
        the panel and the gated formula refuse."""
        import inspect
        src = inspect.getsource(sys.modules["valuation.screener.insider"].insider_detail)
        self.assertIn("50.0", src)
        self.assertIn("genuinely quiet", src)


if __name__ == "__main__":
    import valuation.screener.insider  # noqa: F401  (imported for the source check above)
    unittest.main(verbosity=2)
