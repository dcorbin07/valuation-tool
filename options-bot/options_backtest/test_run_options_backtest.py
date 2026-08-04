"""
Regression tests for the O8 data layer and result serialization.

Both defects these cover are why the index-VRP backtest had never produced a
result: the data source stopped serving CSV, and the results file could not be
written even when the run succeeded. Neither raised anything a reader would
recognise as a failure.

    python -m unittest test_run_options_backtest -v
"""
import json
import unittest
from datetime import date

import run_options_backtest as R


class StooqChallengeDetection(unittest.TestCase):
    """
    Stooq now answers with a JavaScript browser-verification page instead of
    CSV. csv.DictReader parses that HTML into ZERO rows without raising, so the
    old code reported a live-but-blocked feed as "no data available" — which is
    how a dead source becomes a wrong conclusion rather than an error.
    """

    def _patched(self, status, body):
        class _Resp:
            text = body
            def raise_for_status(self):
                if status >= 400:
                    raise RuntimeError(f"HTTP {status}")
        import sys, types
        fake = types.ModuleType("requests")
        fake.get = lambda *a, **k: _Resp()
        real = sys.modules.get("requests")
        sys.modules["requests"] = fake
        try:
            return R._fetch_stooq("SPY", date(2018, 1, 1), date(2018, 2, 1))
        finally:
            if real is not None:
                sys.modules["requests"] = real
            else:
                del sys.modules["requests"]

    def test_js_challenge_body_is_rejected(self):
        body = ('<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>'
                '<noscript>This site requires JavaScript to verify your browser.'
                '</noscript></body></html>')
        self.assertEqual(self._patched(200, body), {},
                         "a 200 carrying an HTML challenge must not count as data")

    def test_real_csv_is_parsed(self):
        body = "Date,Open,High,Low,Close,Volume\n2018-01-02,268.0,268.8,267.4,268.77,86655700\n"
        self.assertEqual(self._patched(200, body), {date(2018, 1, 2): 268.77})

    def test_http_error_is_not_fatal(self):
        self.assertEqual(self._patched(404, "nope"), {})


class CsvParsing(unittest.TestCase):
    def test_cboe_date_format(self):
        """Cboe uses MM/DD/YYYY and upper-case headers; Stooq uses YYYY-MM-DD."""
        body = "DATE,OPEN,HIGH,LOW,CLOSE\n01/02/2018,9.7,10.3,9.5,9.77\n"
        self.assertEqual(R._parse_csv_closes(body, "%m/%d/%Y", "DATE", "CLOSE"),
                         {date(2018, 1, 2): 9.77})

    def test_unparseable_rows_are_skipped_not_fatal(self):
        body = "DATE,CLOSE\n01/02/2018,9.77\nnot-a-date,x\n01/03/2018,\n"
        self.assertEqual(R._parse_csv_closes(body, "%m/%d/%Y", "DATE", "CLOSE"),
                         {date(2018, 1, 2): 9.77})


class ResultsAreSerializable(unittest.TestCase):
    """
    Every Trade carries `entry_date`/`exit_date` as real `date` objects. Without
    default=str, json.dumps raised TypeError AFTER the report printed and BEFORE
    the file was written, so a fully successful run left nothing on disk.
    """

    def test_dates_in_the_trade_log_encode(self):
        res = {"trades": [{"entry_date": date(2020, 3, 2), "exit_date": date(2020, 3, 20),
                           "reason": "stop", "pnl": -1234.5}]}
        with self.assertRaises(TypeError):
            json.dumps(res)
        round_tripped = json.loads(json.dumps(res, indent=2, default=str))
        self.assertEqual(round_tripped["trades"][0]["entry_date"], "2020-03-02")


class SymbolConvention(unittest.TestCase):
    def test_indices_take_no_market_suffix(self):
        self.assertEqual(R.stooq_symbol("^VIX"), "^vix")
        self.assertEqual(R.stooq_symbol("SPY"), "spy.us")
        self.assertEqual(R.stooq_symbol("spy.us"), "spy.us")

    def test_cboe_only_answers_for_cboe_indices(self):
        self.assertEqual(R._fetch_cboe("SPY", date(2018, 1, 1), date(2018, 2, 1)), {},
                         "the Cboe index feed must not be asked for an ETF")


if __name__ == "__main__":
    unittest.main()
