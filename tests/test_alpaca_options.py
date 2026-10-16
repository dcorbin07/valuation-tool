"""The Alpaca paper OPTIONS client and the fleet's move onto it - what these pin.

THE LOAD-BEARING ONES, in order of what they would cost if they failed silently:

1. **THE PAPER-ONLY MODEL IS IMPORTED, NOT RESTATED** (`B7`). `alpaca_broker` owns the host
   check and the live-slot clash check; a second copy here is two definitions of "this is the
   paper account" that can drift apart, and the one that drifts is the one that lets a live
   key through. Pinned from the SYNTAX TREE.

2. **A NAKED SHORT CALL IS REFUSED BEFORE THE WIRE**, and the door out is a REASON rather than
   a boolean so a declaration that opens it has to say why. With a positive control, or a
   guard that refused everything would pass.

3. **A MALFORMED OCC SYMBOL RAISES RATHER THAN DEFAULTING.** The right/side pair is what the
   IRA guard reads, so a symbol the parser cannot read must never reach `place_option` - a
   wrong default there is a naked short call on the wire.

4. **THE BROKER'S OWN RESPONSE PARSERS ARE USED BY THE FLEET.** Tradier reads
   `res["order"]["id"]`; Alpaca returns `id` at the top level. The fleet used Tradier's parser
   at every call site, so repointing the venue without this would have recorded an order it
   could never poll - which is EXACTLY `f3_bear_puts`'s 72 `working` rows. Pinned both ways,
   including that the Tradier path is unchanged.

5. **THE FACTORY FAILS TOWARD RECORDING, NOT TOWARD TRADING.** No credentials means a named
   refusal, never a silent fallback to the closed Tradier sandbox.

6. **EVERY QUOTE CARRIES `executable=False` AND ITS FEED.** The free feed is indicative and
   Alpaca says so; a mid taken from here must not be recorded as a firm one.

    python tests/test_alpaca_options.py
"""
from __future__ import annotations

import ast
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.edge import alpaca_options as AO   # noqa: E402
from valuation.edge import fleet as F             # noqa: E402

CALL = "AAPL240223C00095000"
PUT = "AAPL240223P00095000"


def _src(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


class TestTheSafetyModelIsImported(unittest.TestCase):
    """(1)."""

    def test_the_guards_come_from_alpaca_broker_and_are_not_redefined(self):
        tree = ast.parse(_src("valuation/edge/alpaca_options.py"))
        imported = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and (n.module or "").endswith("alpaca_broker"):
                imported |= {a.name for a in n.names}
        for name in ("assert_paper", "_clashes_with_a_live_slot", "NotPaperError"):
            self.assertIn(name, imported, "%s must be imported, not restated" % name)
        defined = {d.name for d in ast.walk(tree) if isinstance(d, ast.FunctionDef)}
        for name in ("assert_paper", "_clashes_with_a_live_slot"):
            self.assertNotIn(name, defined, "%s is redefined here" % name)

    def test_the_host_guard_actually_refuses_the_live_host(self):
        with self.assertRaises(AO.NotPaperError):
            AO.assert_paper("https://api.alpaca.markets")
        # and the substring trap the broker's docstring names
        with self.assertRaises(AO.NotPaperError):
            AO.assert_paper("https://api.alpaca.markets/?x=paper")
        self.assertTrue(AO.assert_paper(AO.PAPER_BASE))


class TestTheIRAGuard(unittest.TestCase):
    """(2) and (3)."""

    def test_a_naked_short_call_is_refused_with_a_reason(self):
        why = AO.AlpacaPaperOptions.check_structure(CALL, "sell")
        self.assertTrue(why)
        self.assertIn("naked short call", why)

    def test_positive_control_the_three_IRA_legal_structures_pass(self):
        for occ, side in ((CALL, "buy"), (PUT, "buy"), (PUT, "sell")):
            self.assertIsNone(AO.AlpacaPaperOptions.check_structure(occ, side),
                              "%s %s is Level 2 legal and must not be refused" % (side, occ))

    def test_the_door_out_is_a_REASON_and_an_empty_one_does_not_open_it(self):
        self.assertIsNone(AO.AlpacaPaperOptions.check_structure(
            CALL, "sell", allow="F-6's short call leg is covered by stock"))
        for empty in ("", "   ", None):
            self.assertTrue(AO.AlpacaPaperOptions.check_structure(CALL, "sell", allow=empty),
                            "an empty reason must not open the door")

    def test_a_malformed_symbol_RAISES_rather_than_defaulting(self):
        for bad in ("", "AAPL", "NOTANOCC", "240223C00095000", "AA$L240223C00095000",
                    "AAPL240223X00095000"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                AO.parse_occ(bad)

    def test_the_parser_reads_the_right_and_the_strike(self):
        p = AO.parse_occ(CALL)
        self.assertEqual(p["right"], "C")
        self.assertEqual(p["underlying"], "AAPL")
        self.assertAlmostEqual(p["strike"], 95.0)
        self.assertEqual(p["expiration"], "2024-02-23")
        self.assertEqual(AO.parse_occ(PUT)["right"], "P")


class TestTheResponseParsers(unittest.TestCase):
    """(4). The reason a repoint alone would have reproduced F-3's dead end."""

    def test_alpaca_reads_its_own_shape_and_not_tradiers(self):
        self.assertEqual(AO.AlpacaPaperOptions.order_id({"id": "abc"}), "abc")
        self.assertIsNone(AO.AlpacaPaperOptions.order_id({"order": {"id": "abc"}}),
                          "that is Tradier's shape, and reading it here would be luck")

    def test_the_two_brokers_disagree_which_is_the_whole_point(self):
        from valuation.edge.paper_broker import PaperBroker
        alpaca_shape = {"id": "abc"}
        self.assertIsNone(PaperBroker.order_id(alpaca_shape),
                          "Tradier's parser returns None on an Alpaca response - the order "
                          "would be placed and never pollable (f3_bear_puts, 72 rows)")
        self.assertEqual(AO.AlpacaPaperOptions.order_id(alpaca_shape), "abc")

    def test_fill_price_needs_both_a_price_and_a_filled_quantity(self):
        self.assertAlmostEqual(
            AO.AlpacaPaperOptions.fill_price({"filled_avg_price": "1.23", "filled_qty": "1"}),
            1.23)
        for bad in ({"filled_avg_price": "1.23", "filled_qty": "0"},
                    {"filled_avg_price": "0", "filled_qty": "1"},
                    {"filled_qty": "1"}, {}, None):
            self.assertIsNone(AO.AlpacaPaperOptions.fill_price(bad), repr(bad))

    def test_the_fleet_uses_the_brokers_parser_and_tradier_is_unchanged(self):
        from valuation.edge.paper_broker import PaperBroker

        class _Alpaca:
            order_id = staticmethod(AO.AlpacaPaperOptions.order_id)
            fill_price = staticmethod(AO.AlpacaPaperOptions.fill_price)

        class _Bare:
            pass

        self.assertEqual(F._broker_order_id(_Alpaca(), {"id": "zz"}), "zz")
        self.assertEqual(F._broker_order_id(PaperBroker, {"order": {"id": "tt"}}), "tt")
        # a broker providing neither still parses, by the documented fallback
        self.assertEqual(F._broker_order_id(_Bare(), {"order": {"id": "ff"}}), "ff")

    def test_fill_fields_takes_the_already_parsed_price(self):
        """It has no broker in scope, so a parser cannot be chosen there."""
        row = F.fill_fields(symbol="AAPL", occ=CALL, side="buy", qty=1, order_type="limit",
                            quote={"bid": 1.0, "ask": 1.2}, order={"filled_avg_price": "1.1",
                                                                   "filled_qty": "1"},
                            submitted_ts="2026-10-16T20:00:00Z", fill_price=1.1)
        self.assertAlmostEqual(float(row["fill_price"]), 1.1)
        # and with nothing supplied it still reads a TRADIER order, unchanged
        row2 = F.fill_fields(symbol="AAPL", occ=CALL, side="buy", qty=1, order_type="limit",
                             quote={}, order={"avg_fill_price": "2.2", "exec_quantity": "1"},
                             submitted_ts="2026-10-16T20:00:00Z")
        self.assertAlmostEqual(float(row2["fill_price"]), 2.2)


class TestTheFactoryFailsTowardRecording(unittest.TestCase):
    """(5)."""

    def test_no_credentials_means_a_reason_and_never_a_tradier_fallback(self):
        b, why = F.fleet_broker_or_reason("alpaca")
        if b is not None:
            self.skipTest("Alpaca paper credentials are configured here")
        self.assertTrue(why)
        self.assertIn("ALPACA_PAPER_KEY_ID", why)
        from valuation.edge.paper_broker import PaperBroker
        self.assertNotIsInstance(b, PaperBroker)

    def test_the_venue_is_switchable_and_tradier_still_builds(self):
        b, why = F.fleet_broker_or_reason("tradier")
        from valuation.edge.paper_broker import PaperBroker
        self.assertIsInstance(b, PaperBroker, why)

    def test_the_default_venue_is_alpaca_because_tradier_closed(self):
        src = _src("valuation/edge/fleet.py")
        self.assertIn('os.environ.get(FLEET_VENUE_ENV) or "alpaca"', src)

    def test_every_fleet_book_asks_the_factory_rather_than_constructing_one(self):
        tree = ast.parse(_src("valuation/edge/fleet_books.py"))
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                self.assertNotEqual(n.func.id, "PaperBroker",
                                    "a book must not construct its own broker (B7)")


class TestTheQuotesAreLabelledNonExecutable(unittest.TestCase):
    """(6)."""

    def test_the_free_feed_is_named_and_the_caveat_carries_the_measurement(self):
        self.assertEqual(AO.FREE_FEED, "indicative")
        c = AO.FILL_REALISM_CAVEAT
        for must in ("indicative", "15 minutes", "two thirds", "0.6743",
                     "not evidence about execution quality"):
            self.assertIn(must, c.lower(), must)

    def test_a_quote_shape_carries_its_feed_and_executable_false(self):
        class _Stub(AO.AlpacaPaperOptions):
            def __init__(self):            # bypass the credential guard for a pure test
                self.base = AO.PAPER_BASE
                self.data_base = AO.DATA_BASE
                self.timeout = 1
                self.key_id = self.secret = "x"

            def _request(self, method, url, body=None):
                return {"quotes": {CALL: {"bp": 1.0, "ap": 1.2, "t": "2026-10-16T20:00:00Z"}}}

        q = _Stub().quotes([CALL])[CALL]
        self.assertAlmostEqual(q["mid"], 1.1)
        self.assertEqual(q["feed"], "indicative")
        self.assertFalse(q["executable"],
                         "the free feed is indicative; a mid from it is not a firm quote")

    def test_a_one_sided_quote_has_no_mid(self):
        class _Stub(AO.AlpacaPaperOptions):
            def __init__(self):
                self.base = AO.PAPER_BASE
                self.data_base = AO.DATA_BASE
                self.timeout = 1
                self.key_id = self.secret = "x"

            def _request(self, method, url, body=None):
                return {"quotes": {CALL: {"bp": 0.0, "ap": 1.2}}}

        self.assertIsNone(_Stub().quotes([CALL])[CALL]["mid"])


class TestTheSharedAccountCollision(unittest.TestCase):
    """The Index paper slot is deployed at 100%, so a CASH book may not share it."""

    def test_which_books_need_cash_is_READ_from_the_declarations(self):
        from valuation.edge import fleet_books as B
        self.assertFalse(B._needs_cash("f3_bear_puts"), "F-3 buys puts; it needs no cash")
        self.assertFalse(B._needs_cash("f11_dip_reject_puts"))
        for short in ("f8_csp_entry_financing", "f21_v6opt_dip_csp",
                      "f22_dip_csp_random_twin"):
            self.assertTrue(B._needs_cash(short), "%s is short and needs cash" % short)

    def test_an_unreadable_declaration_fails_TOWARD_needing_cash(self):
        from valuation.edge import fleet_books as B
        self.assertTrue(B._needs_cash("no_such_book_at_all"),
                        "the safe direction is to refuse a share, not to let an "
                        "unrecognised book compete with the Index for buying power")

    def test_the_fleet_slot_is_preferred_and_which_one_was_used_is_recorded(self):
        src = _src("valuation/edge/alpaca_options.py")
        self.assertIn("alpaca_fleet_paper_key_id", src)
        self.assertIn("dedicated_fleet_account", src)
        cfg = _src("valuation/config.py")
        self.assertIn("ALPACA_FLEET_PAPER_KEY_ID", cfg)
        self.assertIn("ALPACA_FLEET_PAPER_SECRET_KEY", cfg)

    def test_explicit_keys_are_not_counted_as_the_dedicated_account(self):
        o = AO.AlpacaPaperOptions(key_id="k", secret="s")
        self.assertFalse(o.dedicated,
                         "keys passed by a caller say nothing about which account they are")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
