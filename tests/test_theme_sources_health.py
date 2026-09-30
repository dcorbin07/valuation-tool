"""AUDIT 6 (2026-09-29) — the scan's health block must say where the restored themes' inputs
came from, and in particular whether the FIDELITY-2 cache was there at all.

THE DEFECT, measured on the live service on 2026-09-29: `theme_contributing` read
`institutional: 0.0, insider: 0.0` on a scan whose vintage declares both themes live.
`live_themes.status()` -- "the build date ... for the scan health block" -- was computed on
every scan and discarded: `_enrich_with_live_themes` returned it and `run_scan` never read the
return value. So a cache that was missing (it was: `data/` never ships and the CI job never
builds it) was indistinguishable from one that was present, and the module's promise that
"a cache nobody refreshed is visible rather than quietly ageing" was false in the way it warned
about. This suite pins the fix: the health block carries `theme_sources`, and it says
available-or-not with a reason.

Run: python tests/test_theme_sources_health.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.screener import live_themes as LT           # noqa: E402
from valuation.screener import screen as SC                # noqa: E402
from valuation.screener.store import Store                 # noqa: E402
from screener_fixtures import SyntheticProvider            # noqa: E402


def _scan():
    tmp = os.path.join(tempfile.mkdtemp(prefix="valquo_ts_"), "screener.db")
    return SC.run_scan(scope="synthetic", cfg=None, store=Store(tmp),
                       provider=SyntheticProvider(6), run_dcf_top=0, save=False)


class TheHealthBlockSaysWhereTheThemesCameFrom(unittest.TestCase):
    def setUp(self):
        self._cache, self._issuance = LT.CACHE, os.environ.get("SCREENER_LIVE_ISSUANCE")
        os.environ["SCREENER_LIVE_ISSUANCE"] = "0"          # no SEC calls from a unit test
        LT.reset_cache()

    def tearDown(self):
        LT.CACHE = self._cache
        if self._issuance is None:
            os.environ.pop("SCREENER_LIVE_ISSUANCE", None)
        else:
            os.environ["SCREENER_LIVE_ISSUANCE"] = self._issuance
        LT.reset_cache()

    def test_a_missing_cache_is_REPORTED_not_silent(self):
        """The live condition on 2026-09-29: no cache anywhere the scan could read."""
        LT.CACHE = os.path.join(tempfile.mkdtemp(), "no_such_cache.json")
        LT.reset_cache()
        res = _scan()
        ts = res["health"]["theme_sources"]
        self.assertIs(ts["live_themes"]["cache"]["available"], False, ts)
        self.assertIn("no readable cache", ts["live_themes"]["cache"]["reason"], ts)
        self.assertEqual(ts["live_themes"]["filled"], 0, ts)
        self.assertIs(ts["issuance"].get("disabled"), True, ts)
        # ...and the consequence the block exists to explain is visible beside it.
        self.assertEqual(res["health"]["theme_contributing"].get("institutional"), 0.0)

    def test_a_present_cache_reports_its_build_date_and_what_it_filled(self):
        d = tempfile.mkdtemp()
        LT.CACHE = os.path.join(d, "theme_columns.json")
        uni = SyntheticProvider(6).get_universe()
        rows = {u["ticker"]: {"inst_accum": 0.01 * i, "sm_breadth": 0.02 * i,
                              "insider_score": 40.0 + i}
                for i, u in enumerate(uni)}
        with open(LT.CACHE, "w", encoding="utf-8") as f:
            json.dump({"built": dt.date.today().isoformat(), "rows": rows}, f)
        LT.reset_cache()
        res = _scan()
        ts = res["health"]["theme_sources"]
        self.assertIs(ts["live_themes"]["cache"]["available"], True, ts)
        self.assertEqual(ts["live_themes"]["cache"]["built"], dt.date.today().isoformat())
        self.assertGreater(ts["live_themes"]["filled"], 0, ts)
        self.assertGreater(ts["live_themes"]["fields"].get("inst_accum", 0), 0, ts)
        self.assertGreater(res["health"]["theme_contributing"].get("institutional", 0), 0.5)

    def test_a_stale_cache_is_reported_as_stale_and_not_used(self):
        d = tempfile.mkdtemp()
        LT.CACHE = os.path.join(d, "theme_columns.json")
        old = (dt.date.today() - dt.timedelta(days=LT.MAX_AGE_DAYS + 1)).isoformat()
        with open(LT.CACHE, "w", encoding="utf-8") as f:
            json.dump({"built": old, "rows": {"SYN0000": {"inst_accum": 1.0}}}, f)
        LT.reset_cache()
        res = _scan()
        c = res["health"]["theme_sources"]["live_themes"]["cache"]
        self.assertIs(c["available"], False, c)
        self.assertEqual(c["built"], old)
        self.assertGreater(c["age_days"], LT.MAX_AGE_DAYS)
        self.assertEqual(res["health"]["theme_sources"]["live_themes"]["filled"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
