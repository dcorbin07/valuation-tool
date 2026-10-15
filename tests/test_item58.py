"""ITEM 58 -- Alpaca paper for every paper book, and the §8 live path shipping at 0%.

THE "DONE" LIST IS THE TEST LIST. The brief names eight failure modes that must fail a test:
a live host in a paper book; a missing key; an order on a day with no event; an order at 0%;
an order touching a position the slot did not buy; a pause that sells; and any broken input
that still produces an order rather than no order plus an alert.

NOTHING HERE CONSTRUCTS A LIVE CLIENT WITH A REAL KEY, and a test asserts that the environment
this suite runs in carries none.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402  must precede any `valuation` import

from valuation.edge import alpaca_broker as AB                        # noqa: E402
from valuation.edge import live_slots as LS                           # noqa: E402


class _Resp:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code, self._p, self.text = status, payload, text

    def json(self):
        if self._p is None:
            raise ValueError("no json")
        return self._p


class _Session:
    """Records every request and answers from a table. Nothing leaves the process."""

    def __init__(self, table=None):
        self.calls, self.table = [], table or {}

    def request(self, method, url, **kw):
        self.calls.append({"method": method, "url": url, "data": kw.get("data"),
                           "params": kw.get("params")})
        for key, resp in self.table.items():
            if key in url:
                return resp
        return _Resp(200, {})


# --------------------------------------------------------------------------- #
# A. the paper broker
# --------------------------------------------------------------------------- #
class A_PaperHostIsTheWholeGuarantee(unittest.TestCase):

    def test_a_LIVE_host_in_a_paper_book_is_REFUSED(self):
        """The first item on the brief's Done list."""
        for bad in ("https://api.alpaca.markets",
                    "https://api.alpaca.markets/v2",
                    "https://api.alpaca.markets/?x=paper-api.alpaca.markets",
                    "http://paper-api.alpaca.markets",
                    "https://evil.example/paper-api.alpaca.markets",
                    "https://paper-api.alpaca.markets.evil.example"):
            with self.assertRaises(AB.NotPaperError, msg=bad):
                AB.assert_paper(bad)

    def test_the_paper_host_is_accepted_and_normalised(self):
        self.assertEqual(AB.assert_paper("https://paper-api.alpaca.markets/"),
                         "https://paper-api.alpaca.markets")

    def test_the_check_is_a_PARSE_not_a_substring(self):
        """`"paper" in url` would pass a live URL carrying it as a query parameter."""
        import inspect
        src = inspect.getsource(AB.assert_paper)
        self.assertIn("urlparse", src)
        self.assertIn("hostname", src)

    def test_a_MISSING_key_is_REFUSED(self):
        """The second item on the Done list."""
        for kid, sec in (("", ""), ("k", ""), ("", "s"), ("   ", "s")):
            with self.assertRaises(AB.NotPaperError):
                AB.AlpacaPaperBroker(key_id=kid, secret_key=sec)

    def test_a_key_that_is_ALSO_a_live_slots_is_REFUSED(self):
        os.environ["ALPACA_ACCOUNT_7_KEY_ID"] = "SHARED-KEY"
        os.environ["ALPACA_ACCOUNT_7_SECRET_KEY"] = "SHARED-SEC"
        try:
            with self.assertRaises(AB.NotPaperError):
                AB.AlpacaPaperBroker(key_id="SHARED-KEY", secret_key="x")
            with self.assertRaises(AB.NotPaperError):
                AB.AlpacaPaperBroker(key_id="x", secret_key="SHARED-SEC")
            # And a genuinely separate pair is fine.
            AB.AlpacaPaperBroker(key_id="papery", secret_key="papers")
        finally:
            del os.environ["ALPACA_ACCOUNT_7_KEY_ID"]
            del os.environ["ALPACA_ACCOUNT_7_SECRET_KEY"]

    def test_every_request_path_is_rebuilt_from_the_validated_base(self):
        b = AB.AlpacaPaperBroker(key_id="k", secret_key="s")
        for path in ("/v2/orders", "v2/orders", "/v2/account"):
            self.assertTrue(b._url(path).startswith("https://paper-api.alpaca.markets/"))

    def test_the_module_never_builds_a_request_against_the_live_host(self):
        """It NAMES the live host so it can be refused; it must never target it."""
        with open(AB.__file__, encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn('"https://api.alpaca.markets"', src)
        self.assertIn("LIVE_HOST", src)


class A_TheAccountEndpointCannotConfirmPaper(unittest.TestCase):
    """The brief asked for a fourth guard and Alpaca does not provide one."""

    def test_the_account_number_shape_is_recorded_but_is_NOT_the_gate(self):
        sess = _Session({"/v2/account": _Resp(200, {
            "account_number": "PA3XYZ", "equity": "1000", "cash": "500",
            "buying_power": "1000", "status": "ACTIVE"})})
        b = AB.AlpacaPaperBroker(key_id="k", secret_key="s", session=sess)
        got = b.account()
        self.assertTrue(got["ok"])
        corr = got["paper_corroboration"]
        self.assertFalse(corr["is_the_gate"])
        self.assertIn("no paper/live field", corr["note"])

    def test_an_account_number_WITHOUT_a_paper_shape_still_works(self):
        """Because the shape is not the gate: relying on it would be the prefix assumption
        the brief forbids, and `GET /v2/account` carries no paper/live field at all."""
        sess = _Session({"/v2/account": _Resp(200, {
            "account_number": "010203ABCD", "equity": "1", "status": "ACTIVE"})})
        b = AB.AlpacaPaperBroker(key_id="k", secret_key="s", session=sess)
        self.assertTrue(b.account()["ok"])


class A_FillAssumptionsTravelInThePayload(unittest.TestCase):

    def test_the_caveat_names_every_thing_paper_does_not_model(self):
        for needle in ("queue position", "price improvement", "liquidity", "partial",
                       "regulatory fees", "IEX"):
            self.assertIn(needle.lower(), AB.DATA_CAVEAT.lower(), needle)

    def test_dividends_are_stated_as_a_HOLE_not_a_caveat(self):
        self.assertIn("does not pay dividends", AB.DIVIDENDS_NOT_PAID)
        self.assertIn("understates", AB.DIVIDENDS_NOT_PAID)

    def test_a_fill_records_the_feed_it_was_priced_against(self):
        sess = _Session({"quotes/latest": _Resp(200, {"quotes": {
            "KO": {"bp": 90.0, "ap": 90.2, "z": "iex", "t": "2026-10-14T19:00:00Z"}}})})
        b = AB.AlpacaPaperBroker(key_id="k", secret_key="s", session=sess)
        q = b.quotes(["KO"])["KO"]
        self.assertEqual(q["feed"], "iex")
        self.assertAlmostEqual(q["mid"], 90.1)

    def test_an_unstated_feed_is_never_resolved_to_the_full_tape(self):
        sess = _Session({"quotes/latest": _Resp(200, {"quotes": {
            "KO": {"bp": 90.0, "ap": 90.2}}})})
        b = AB.AlpacaPaperBroker(key_id="k", secret_key="s", session=sess)
        self.assertEqual(b.quotes(["KO"])["KO"]["feed"], "unstated")

    def test_the_mark_is_the_MID_and_never_the_last_trade(self):
        self.assertIsNone(AB.AlpacaPaperBroker.mark_from_quote({"last": 100.0}))
        self.assertEqual(AB.AlpacaPaperBroker.mark_from_quote({"mid": 90.1}), 90.1)


class A_FractionalLimitOrders(unittest.TestCase):
    """Verified against Alpaca's own orders reference, not against the brief."""

    def test_a_fractional_LIMIT_order_is_built_with_day_tif(self):
        b = AB.AlpacaPaperBroker(key_id="k", secret_key="s", dry_run=True)
        got = b.place_equity("KO", "buy", 0.4237, limit_price=90.11)
        self.assertTrue(got["ok"])
        sent = got["would_send"]
        self.assertEqual(sent["type"], "limit")
        self.assertEqual(sent["time_in_force"], AB.FRACTIONAL_TIF)
        self.assertEqual(sent["time_in_force"], "day")
        self.assertEqual(sent["qty"], "0.4237")
        self.assertEqual(sent["limit_price"], "90.11")

    def test_a_MARKET_order_is_refused_because_section_8_says_limit_only(self):
        b = AB.AlpacaPaperBroker(key_id="k", secret_key="s", dry_run=True)
        got = b.place_equity("KO", "buy", 1, limit_price=None)
        self.assertFalse(got["ok"])
        self.assertIn("LIMIT orders only", got["reason"])

    def test_a_fractional_quantity_with_a_non_day_tif_is_refused(self):
        """Alpaca permits `day` ONLY for fractional: gtc, ioc, fok, opg and cls all return No."""
        b = AB.AlpacaPaperBroker(key_id="k", secret_key="s", dry_run=True)
        got = b.place_equity("KO", "buy", 0.5, limit_price=90.0, time_in_force="gtc")
        self.assertFalse(got["ok"])
        self.assertIn("day", got["reason"])

    def test_it_uses_qty_and_NOT_notional(self):
        """A notional order cannot be REPLACED, and the live path must be able to re-price."""
        b = AB.AlpacaPaperBroker(key_id="k", secret_key="s", dry_run=True)
        sent = b.place_equity("KO", "buy", 0.5, limit_price=90.0)["would_send"]
        self.assertIn("qty", sent)
        self.assertNotIn("notional", sent)

    def test_a_dry_run_sends_NOTHING(self):
        sess = _Session()
        b = AB.AlpacaPaperBroker(key_id="k", secret_key="s", dry_run=True, session=sess)
        b.place_equity("KO", "buy", 1.0, limit_price=90.0)
        self.assertEqual(sess.calls, [], "a dry run contacted the broker")

    def test_a_bad_side_or_quantity_is_refused_rather_than_coerced(self):
        b = AB.AlpacaPaperBroker(key_id="k", secret_key="s", dry_run=True)
        for kw in ({"side": "short"}, {"quantity": 0}, {"quantity": -1}, {"quantity": "x"}):
            args = {"ticker": "KO", "side": "buy", "quantity": 1.0, "limit_price": 90.0}
            args.update(kw)
            self.assertFalse(b.place_equity(**args)["ok"], kw)


# --------------------------------------------------------------------------- #
# B. the live path
# --------------------------------------------------------------------------- #
def _env(**kw):
    """A clean slot environment. Never the real one."""
    e = {}
    e.update(kw)
    return e


class B_Separation(unittest.TestCase):

    def test_the_live_client_accepts_ONLY_the_live_host(self):
        for bad in ("https://paper-api.alpaca.markets", "http://api.alpaca.markets",
                    "https://api.alpaca.markets.evil.example"):
            with self.assertRaises(LS.NotLiveError, msg=bad):
                LS.assert_live_host(bad)
        self.assertEqual(LS.assert_live_host("https://api.alpaca.markets/"),
                         "https://api.alpaca.markets")

    def test_the_paper_broker_cannot_be_pointed_at_the_live_host_and_vice_versa(self):
        with self.assertRaises(AB.NotPaperError):
            AB.assert_paper(LS.LIVE_BASE)
        with self.assertRaises(LS.NotLiveError):
            LS.assert_live_host(AB.PAPER_BASE)

    def test_the_live_client_is_a_DIFFERENT_class_not_a_flag(self):
        """A boolean choosing between paper and real money is one typo from a real order."""
        self.assertIsNot(LS._LiveClient, AB.AlpacaPaperBroker)
        self.assertFalse(issubclass(LS._LiveClient, AB.AlpacaPaperBroker))

    def test_no_live_client_is_constructed_without_a_key_pair(self):
        with self.assertRaises(LS.NotLiveError):
            LS._LiveClient(1, "", "")

    def test_no_paper_book_imports_the_live_module(self):
        """READ THROUGH THE AST, NOT AS A SUBSTRING. The first cut grepped for "live_slots"
        and flagged `config.py`, whose COMMENT names the module to explain why the live keys
        are deliberately NOT in the dataclass. That is this project's substring-ban family: a
        guard tripped by prose documenting the very rule it enforces. An `import` is a
        syntactic fact, so it is read syntactically.
        """
        import ast

        import valuation
        root = os.path.dirname(os.path.abspath(valuation.__file__))
        offenders = []
        for dirpath, _d, files in os.walk(root):
            if "__pycache__" in dirpath:
                continue
            for fn in files:
                if not fn.endswith(".py") or fn == "live_slots.py":
                    continue
                p = os.path.join(dirpath, fn)
                with open(p, encoding="utf-8") as fh:
                    try:
                        tree = ast.parse(fh.read())
                    except SyntaxError:
                        continue
                for node in ast.walk(tree):
                    mods = []
                    if isinstance(node, ast.Import):
                        mods = [a.name for a in node.names]
                    elif isinstance(node, ast.ImportFrom):
                        mods = [node.module or ""] + [a.name for a in node.names]
                    if any("live_slots" in (m or "") for m in mods):
                        offenders.append(os.path.relpath(p, root).replace("\\", "/"))

        # REPOINTED BY ITEM 58b, IN THE SAME COMMIT AS THE CHANGE THAT FIRED IT.
        #
        # At item 58 this read `== []`, and that was correct: the safety core had no caller, so
        # "nobody imports it" guaranteed the separation rule for free. Item 58b built the
        # caller, so the free guarantee is spent and the real property has to be asserted.
        #
        # TWO IMPORTERS, NAMED, EACH WITH ITS REASON. A third is red.
        allowed = {
            # The live path's own caller. It is the ONLY module that may construct a live
            # client, and the count check below is what enforces that.
            "edge/live_cycle.py",
            # The service, for the two owner-only doors. It imports `live_slots` for `status()`
            # and `discover_slots()` -- reads, never a client; a separate test asserts the
            # status door reaches for no constructor at all.
            "saas/app_saas.py",
        }
        self.assertEqual(sorted(set(offenders) - allowed), [],
                         "modules IMPORT the live path that may not: %r"
                         % (sorted(set(offenders) - allowed),))

        # AND THE HALF OF THE RULE THAT IS STILL ABSOLUTE: NO PAPER BOOK. A paper book able to
        # reach a live client is the entire hazard this rule exists for, and nothing in item
        # 58b changes that.
        paper = [f for f in offenders
                 if os.path.basename(f).startswith(("fleet", "paper_", "options_"))
                 or os.path.basename(f) in ("paper_track.py", "alpaca_broker.py")]
        self.assertEqual(paper, [], "a PAPER BOOK imports the live path: %r" % paper)

    def test_a_live_client_is_CONSTRUCTED_in_exactly_one_place(self):
        """THE CHECK THAT REPLACES "nobody imports it", AND IT IS STRONGER THAN WHAT IT
        REPLACES. An import is harmless; a construction is the thing that can authenticate
        against the live host. One site, and a second is red whatever it is called.

        `live_cycle` also accepts a `live_client_factory` for tests, and that is NOT a second
        site: it is a parameter the production path leaves `None`, and the default branch below
        is the one construction. A test asserts the factory is only ever supplied by a caller.
        """
        import ast

        import valuation
        root = os.path.dirname(os.path.abspath(valuation.__file__))
        sites = []
        for dirpath, _d, files in os.walk(root):
            if "__pycache__" in dirpath:
                continue
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                p = os.path.join(dirpath, fn)
                with open(p, encoding="utf-8") as fh:
                    try:
                        tree = ast.parse(fh.read())
                    except SyntaxError:
                        continue
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    f = node.func
                    name = (f.attr if isinstance(f, ast.Attribute) else
                            (f.id if isinstance(f, ast.Name) else ""))
                    if name == "_LiveClient":
                        sites.append("%s:%d" % (os.path.relpath(p, root).replace("\\", "/"),
                                                node.lineno))
        self.assertEqual(len(sites), 1,
                         "a live client is constructed in %d places: %r" % (len(sites), sites))
        self.assertTrue(sites[0].startswith("edge/live_cycle.py"), sites)

    def test_the_one_construction_site_sits_behind_armed_AND_send(self):
        """Counting the sites is not enough -- the one site has to be GATED. Read structurally:
        the construction must be inside an `if` whose test names both `armed` and `send`."""
        import ast
        import inspect

        from valuation.edge import live_cycle as LC
        tree = ast.parse(inspect.getsource(LC))
        gated = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            test_src = ast.dump(node.test)
            if "armed" not in test_src or "send" not in test_src:
                continue
            for inner in ast.walk(node):
                if (isinstance(inner, ast.Call)
                        and getattr(inner.func, "attr", getattr(inner.func, "id", ""))
                        == "_LiveClient"):
                    gated = True
        self.assertTrue(gated, "the live client is constructed outside an armed-and-send gate")

    def test_NOTHING_OUTSIDE_the_package_reaches_the_live_path_either(self):
        """THE BRIEF SAYS "no CLI, script, test or admin door", AND MY FIRST VERSION OF THE
        GUARD ABOVE WALKED ONLY `valuation/`. A `scripts/` entry point is exactly the shape
        that would let a lane trigger a live order from a terminal, which is the thing question
        4 of the auditor review asks about -- so the walk has to cover it.

        `tests/test_item58.py` is excluded because this file legitimately imports the module to
        test it, and `_LiveClient` is only ever constructed here with fake keys.
        """
        import ast
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        me = os.path.abspath(__file__)
        offenders = []
        for sub in ("scripts", "tests"):
            base = os.path.join(root, sub)
            if not os.path.isdir(base):
                continue
            for dirpath, _d, files in os.walk(base):
                if "__pycache__" in dirpath:
                    continue
                for fn in files:
                    if not fn.endswith(".py"):
                        continue
                    p = os.path.join(dirpath, fn)
                    if os.path.abspath(p) == me:
                        continue
                    with open(p, encoding="utf-8", errors="replace") as fh:
                        try:
                            tree = ast.parse(fh.read())
                        except SyntaxError:
                            continue
                    for node in ast.walk(tree):
                        mods = []
                        if isinstance(node, ast.Import):
                            mods = [a.name for a in node.names]
                        elif isinstance(node, ast.ImportFrom):
                            mods = [node.module or ""] + [a.name for a in node.names]
                        if any("live_slots" in (m or "") for m in mods):
                            rel = os.path.relpath(p, root).replace("\\", "/")
                            # REPOINTED BY ITEM 58b. A TEST of the live path must import it --
                            # that is what testing it means, and `tests/test_item58.py` was
                            # already excluded for exactly that reason. `tests/test_item58b.py`
                            # and `tests/test_item58b_doors.py` are the same case.
                            #
                            # WHAT STAYS ABSOLUTE IS `scripts/`: an entry point there is the
                            # shape that would let a lane trigger a live order from a terminal,
                            # which is question 4 of the auditor review. The check below is
                            # keyed on the DIRECTORY, so a script is red however it is named.
                            if rel.startswith("tests/"):
                                continue
                            offenders.append(rel)
        self.assertEqual(sorted(set(offenders)), [],
                         "a script or test reaches the live path: %r"
                         % (sorted(set(offenders)),))

    def test_no_workflow_carries_an_alpaca_credential(self):
        """The keys live in the SERVICE's environment and nowhere else. Every workflow asks the
        service to do the work -- confirmed: `fleet-cycle.yml` POSTs to it -- so no GitHub
        secret is needed, and a workflow naming one would be a live key on GitHub."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        wf = os.path.join(root, ".github", "workflows")
        if not os.path.isdir(wf):
            self.skipTest("no .github/workflows in this checkout")
        bad = []
        for fn in sorted(os.listdir(wf)):
            if not fn.endswith((".yml", ".yaml")):
                continue
            with open(os.path.join(wf, fn), encoding="utf-8", errors="replace") as fh:
                body = fh.read()
            if "ALPACA" in body.upper():
                bad.append(fn)
        self.assertEqual(bad, [], "a workflow names an Alpaca credential: %r" % (bad,))

    def test_that_guard_is_not_vacuous(self):
        """It must still bite on a real import, or it passes by seeing nothing."""
        import ast
        tree = ast.parse("from ..edge import live_slots\n")
        found = [a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                 for a in n.names]
        self.assertIn("live_slots", found)

    def test_this_suite_runs_with_NO_real_live_key_in_the_environment(self):
        """Nothing in tests or CI may construct the live client with real keys."""
        self.assertEqual(LS.discover_slots(), [],
                         "a real slot credential is present in the test environment")


class B_PauseIsNotZero(unittest.TestCase):

    def test_a_PAUSE_does_not_sell_and_computes_no_target(self):
        """The brief's Done list: 'a pause that sells'."""
        e = _env(LIVE_PILOT_ENABLED="0", ALPACA_ACCOUNT_1_KEY_ID="k",
                 ALPACA_ACCOUNT_1_SECRET_KEY="s", ALPACA_ACCOUNT_1_LIVE_PCT="25")
        a = LS.armed(1, e)
        self.assertFalse(a["armed"])
        self.assertIn("PAUSED", a["reason"])
        self.assertIn("Nothing is sold", a["reason"])

    def test_anything_but_1_is_a_pause(self):
        """SURROUNDING WHITESPACE IS STRIPPED AND NOTHING ELSE IS, and the line between those
        two is intent. `"1 "` is a copy-paste artefact of someone who typed 1 and plainly
        means armed, so treating it as a pause would silently disarm a slot Don believes is
        on. `"true"`, `"yes"` and `"01"` are DIFFERENT STRINGS, not sloppy ones, and a switch
        that guesses at them is a switch that can be turned on by accident."""
        for v in ("", "0", "true", "yes", "01", "TRUE", "on", "1.0", "-1"):
            e = _env(LIVE_PILOT_ENABLED=v, ALPACA_ACCOUNT_1_KEY_ID="k",
                     ALPACA_ACCOUNT_1_SECRET_KEY="s", ALPACA_ACCOUNT_1_LIVE_PCT="25")
            self.assertFalse(LS.pilot_enabled(e), repr(v))
        for v in ("1", " 1", "1 ", "\t1\n"):
            self.assertTrue(LS.pilot_enabled(_env(LIVE_PILOT_ENABLED=v)), repr(v))

    def test_the_status_states_the_difference_in_words_every_time(self):
        st = LS.status(_env())
        self.assertIn("PAUSES", st["pause_vs_zero"]["pause"])
        self.assertIn("SELLS", st["pause_vs_zero"]["zero_pct"])


class B_ZeroPercentIsHowEverySlotShips(unittest.TestCase):

    def test_a_slot_with_no_percentage_is_0_and_is_still_DISCOVERED(self):
        e = _env(LIVE_PILOT_ENABLED="1", ALPACA_ACCOUNT_2_KEY_ID="k",
                 ALPACA_ACCOUNT_2_SECRET_KEY="s")
        self.assertEqual(LS.discover_slots(e), [2])
        p = LS.slot_pct(2, e)
        self.assertTrue(p["ok"])
        self.assertEqual(p["pct"], 0.0)
        self.assertFalse(p["stated"])

    def test_at_0_percent_a_slot_is_NOT_armed(self):
        """The brief's Done list: 'an order at 0%'."""
        e = _env(LIVE_PILOT_ENABLED="1", ALPACA_ACCOUNT_1_KEY_ID="k",
                 ALPACA_ACCOUNT_1_SECRET_KEY="s", ALPACA_ACCOUNT_1_LIVE_PCT="0")
        a = LS.armed(1, e)
        self.assertFalse(a["armed"])
        self.assertIn("0%", a["reason"])

    def test_a_NON_NUMERIC_percentage_refuses_rather_than_reading_as_zero(self):
        """Reading a typo as 0 would SELL the book."""
        for bad in ("abc", "25%", "-1", "101", "1e9"):
            p = LS.slot_pct(1, _env(ALPACA_ACCOUNT_1_LIVE_PCT=bad))
            self.assertFalse(p["ok"], bad)
            self.assertIn("sell the book", p["reason"])

    def test_the_retired_variable_is_read_NOWHERE(self):
        e = _env(LIVE_PILOT_ENABLED="1", ALPACA_ACCOUNT_1_KEY_ID="k",
                 ALPACA_ACCOUNT_1_SECRET_KEY="s", ALPACA_LIVE_PCT="50")
        self.assertEqual(LS.slot_pct(1, e)["pct"], 0.0)
        self.assertFalse(LS.armed(1, e)["armed"])
        st = LS.status(e)
        self.assertIn("ALPACA_LIVE_PCT", st["retired_variables_set"])


class B_HolderAuthorization(unittest.TestCase):

    def test_slot_1_needs_no_row_because_it_is_Dons_own(self):
        got = LS.holder_authorized(1, contract_text="")
        self.assertTrue(got["authorized"])

    def test_any_OTHER_slot_stays_at_zero_without_a_signed_row(self):
        for txt in ("", "no table here",
                    "| Slot 2 live authorization | pending |",
                    "| Slot 2 live authorization | NO |",
                    "| Slot 3 live authorization | YES - 2026-10-20 |"):
            got = LS.holder_authorized(2, contract_text=txt)
            self.assertFalse(got["authorized"], txt)

    def test_a_signed_row_authorizes_exactly_that_slot(self):
        txt = "| Slot 2 live authorization | YES - 2026-10-20, signed by the holder |"
        self.assertTrue(LS.holder_authorized(2, contract_text=txt)["authorized"])
        self.assertFalse(LS.holder_authorized(3, contract_text=txt)["authorized"])

    def test_an_unreadable_contract_is_NOT_authorization(self):
        got = LS.holder_authorized(2, contract_text=None)
        # Either it read the real contract (which has no slot-2 row) or it failed to; both
        # must answer "not authorized".
        self.assertFalse(got["authorized"])


class B_Isolation(unittest.TestCase):

    def test_two_slots_sharing_a_credential_are_refused(self):
        e = _env(LIVE_PILOT_ENABLED="1",
                 ALPACA_ACCOUNT_1_KEY_ID="same", ALPACA_ACCOUNT_1_SECRET_KEY="s1",
                 ALPACA_ACCOUNT_2_KEY_ID="same", ALPACA_ACCOUNT_2_SECRET_KEY="s2",
                 ALPACA_ACCOUNT_1_LIVE_PCT="10")
        iso = LS.isolation(e)
        self.assertFalse(iso["ok"])
        self.assertEqual(iso["clashes"][0]["slots"], [1, 2])
        self.assertFalse(LS.armed(1, e)["armed"])

    def test_distinct_slots_are_isolated(self):
        e = _env(ALPACA_ACCOUNT_1_KEY_ID="a", ALPACA_ACCOUNT_1_SECRET_KEY="b",
                 ALPACA_ACCOUNT_2_KEY_ID="c", ALPACA_ACCOUNT_2_SECRET_KEY="d")
        self.assertTrue(LS.isolation(e)["ok"])

    def test_the_status_never_carries_a_credential(self):
        e = _env(ALPACA_ACCOUNT_1_KEY_ID="SECRET-KEY-ID",
                 ALPACA_ACCOUNT_1_SECRET_KEY="SECRET-SECRET",
                 ALPACA_ACCOUNT_1_HOLDER="Don")
        blob = repr(LS.status(e))
        self.assertNotIn("SECRET-KEY-ID", blob)
        self.assertNotIn("SECRET-SECRET", blob)
        self.assertIn("Don", blob)


class B_TheThreeEvents(unittest.TestCase):

    def test_no_event_means_NO_ORDERS(self):
        """The brief's Done list: 'an order on a day with no event'."""
        got = LS.event_for({"last_event_date": "2026-07-30", "last_pct": 25.0},
                           {"formed_on": "2026-07-30"}, 25.0)
        self.assertFalse(got["act"])
        self.assertEqual(got["event"], "none")
        self.assertIn("whole point", got["reason"])

    def test_a_NEW_rebalance_event_acts(self):
        got = LS.event_for({"last_event_date": "2026-07-30", "last_pct": 25.0},
                           {"formed_on": "2026-10-22"}, 25.0)
        self.assertTrue(got["act"])
        self.assertEqual(got["event"], "rebalance")

    def test_zero_to_X_is_a_buy_in_and_X_to_zero_is_a_sell_out(self):
        buy = LS.event_for({"last_event_date": "2026-07-30", "last_pct": 0.0},
                           {"formed_on": "2026-07-30"}, 25.0)
        self.assertEqual(buy["kind"], "buy-in")
        sell = LS.event_for({"last_event_date": "2026-07-30", "last_pct": 25.0},
                            {"formed_on": "2026-07-30"}, 0.0)
        self.assertEqual(sell["kind"], "sell-out")
        resize = LS.event_for({"last_event_date": "2026-07-30", "last_pct": 25.0},
                              {"formed_on": "2026-07-30"}, 10.0)
        self.assertEqual(resize["kind"], "resize")

    def test_nothing_in_the_module_reads_a_RETURN_to_decide_to_trade(self):
        """No loss stops, no drawdown rule -- removed by Don's instruction. The checks are
        about the software, never about performance."""
        with open(LS.__file__, encoding="utf-8") as fh:
            src = fh.read()
        import ast
        tree = ast.parse(src)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        for banned in ("max_daily_loss", "max_drawdown", "drawdown_pct", "stop_loss",
                       "trailing_stop"):
            self.assertNotIn(banned, names)
        self.assertNotIn("MAX_DAILY_LOSS_PCT", src.replace(
            "MAX_DAILY_LOSS_PCT and MAX_DRAWDOWN_PCT", ""))


class B_ThePerStockMath(unittest.TestCase):

    def test_the_target_is_pct_times_equity_times_weight(self):
        got = LS.targets(25.0, 100000.0, [{"ticker": "A", "weight": 0.6},
                                          {"ticker": "B", "weight": 0.4}])
        self.assertTrue(got["ok"])
        self.assertAlmostEqual(got["slot_value"], 25000.0)
        self.assertAlmostEqual(got["targets"]["A"], 15000.0)
        self.assertAlmostEqual(got["targets"]["B"], 10000.0)

    def test_weights_are_renormalised_so_an_exited_name_does_not_strand_cash(self):
        got = LS.targets(10.0, 1000.0, [{"ticker": "A", "weight": 0.5},
                                        {"ticker": "B", "weight": 0.3},
                                        {"ticker": "GONE", "weight": 0.0}])
        self.assertAlmostEqual(sum(got["targets"].values()), 100.0, places=6)
        self.assertNotIn("GONE", got["targets"])

    def test_bad_inputs_refuse_rather_than_returning_a_partial_map(self):
        for args in ((101.0, 1000.0), (-1.0, 1000.0), (25.0, 0.0), (25.0, None)):
            self.assertFalse(LS.targets(args[0], args[1],
                                        [{"ticker": "A", "weight": 1.0}])["ok"], args)
        self.assertFalse(LS.targets(25.0, 1000.0, [])["ok"])

    def test_the_plan_buys_the_shortfall_and_sells_the_excess(self):
        plan = LS.order_plan({"A": 1000.0, "B": 500.0}, {"A": 5.0, "B": 10.0},
                             {"A": {"mid": 100.0}, "B": {"mid": 100.0}})
        by = {o["ticker"]: o for o in plan["orders"]}
        self.assertEqual(by["A"]["side"], "buy")
        self.assertAlmostEqual(by["A"]["qty"], 5.0)
        self.assertEqual(by["B"]["side"], "sell")
        self.assertAlmostEqual(by["B"]["qty"], 5.0)

    def test_every_order_is_a_LIMIT_at_the_mark(self):
        plan = LS.order_plan({"A": 1000.0}, {}, {"A": {"mid": 90.11}})
        self.assertAlmostEqual(plan["orders"][0]["limit_price"], 90.11)

    def test_it_NEVER_sells_more_than_the_slot_bought(self):
        """The brief's Done list: 'an order touching a position the slot did not buy'."""
        plan = LS.order_plan({"A": 0.0}, {"A": 2.0}, {"A": {"mid": 100.0}})
        self.assertAlmostEqual(plan["orders"][0]["qty"], 2.0)
        plan2 = LS.order_plan({"A": 0.0}, {}, {"A": {"mid": 100.0}})
        self.assertEqual(plan2["orders"], [], "it planned a sale of a position it never held")

    def test_a_name_the_slot_did_not_buy_is_not_in_the_plan_at_all(self):
        """Don's other holdings in the account are never touched, and that is enforced by
        what the planner is GIVEN rather than by a filter it could forget."""
        plan = LS.order_plan({"A": 100.0}, {"A": 1.0, "DONS_OWN": 50.0},
                             {"A": {"mid": 100.0}, "DONS_OWN": {"mid": 10.0}})
        self.assertEqual([o["ticker"] for o in plan["orders"]], [])

    def test_a_missing_mark_skips_the_name_rather_than_trading_at_any_price(self):
        plan = LS.order_plan({"A": 100.0, "B": 100.0}, {}, {"A": {"mid": 100.0}})
        self.assertEqual([o["ticker"] for o in plan["orders"]], ["A"])
        self.assertEqual(plan["skipped"][0]["ticker"], "B")


class B_BrokenInputsProduceNoOrdersAndAnAlert(unittest.TestCase):
    """The brief's Done list: 'any broken input that still produces an order rather than no
    order plus an alert'. Each entry is one of the brief's named conditions."""

    def _ok_args(self):
        return {
            "book": {"ok": True, "formed_on": "2026-10-22",
                     "positions": [{"ticker": "A", "weight": 1.0, "status": "held"}]},
            "equity": 1000.0, "marks": {"A": {"mid": 100.0}},
            "slot_record": {}, "pct": 25.0,
        }

    def test_the_happy_path_passes_so_the_checks_are_not_vacuous(self):
        got = LS.preflight(**self._ok_args())
        self.assertTrue(got["ok"], got["problems"])

    def test_an_unreadable_book_blocks_the_cycle(self):
        a = self._ok_args()
        a["book"] = {"ok": False, "reason": "the record could not be read"}
        got = LS.preflight(**a)
        self.assertFalse(got["ok"])
        self.assertIn("NO orders", got["reason"])

    def test_a_book_with_no_held_positions_blocks_the_cycle(self):
        a = self._ok_args()
        a["book"] = {"ok": True, "formed_on": "2026-10-22", "positions": []}
        self.assertFalse(LS.preflight(**a)["ok"])

    def test_a_book_with_no_formation_date_blocks_the_cycle(self):
        a = self._ok_args()
        a["book"] = dict(a["book"], formed_on="")
        self.assertFalse(LS.preflight(**a)["ok"])

    def test_unreadable_equity_blocks_the_cycle(self):
        for bad in (None, 0, -5, "x"):
            a = self._ok_args()
            a["equity"] = bad
            self.assertFalse(LS.preflight(**a)["ok"], bad)

    def test_a_missing_price_for_a_name_the_cycle_would_trade_blocks_it(self):
        a = self._ok_args()
        a["marks"] = {}
        got = LS.preflight(**a)
        self.assertFalse(got["ok"])
        self.assertIn("no usable price", got["reason"])

    def test_a_bad_percentage_blocks_the_cycle(self):
        a = self._ok_args()
        a["pct"] = 101.0
        self.assertFalse(LS.preflight(**a)["ok"])

    def test_the_slots_own_record_disagreeing_with_the_broker_blocks_it(self):
        a = self._ok_args()
        a["slot_record"] = {"A": 5.0}
        a["broker_positions"] = [{"ticker": "A", "qty": 3.0}]
        got = LS.preflight(**a)
        self.assertFalse(got["ok"])
        self.assertIn("broker reports", got["reason"])

    def test_a_position_the_broker_does_not_report_at_all_blocks_it(self):
        a = self._ok_args()
        a["slot_record"] = {"A": 5.0}
        a["broker_positions"] = []
        self.assertFalse(LS.preflight(**a)["ok"])

    def test_an_agreeing_record_passes(self):
        a = self._ok_args()
        a["slot_record"] = {"A": 5.0}
        a["broker_positions"] = [{"ticker": "A", "qty": 5.0}]
        self.assertTrue(LS.preflight(**a)["ok"])

    def test_a_refusal_returns_NO_partial_order_list(self):
        """An error never causes a sale and never changes holdings, so a refusal cannot
        carry some of the orders."""
        a = self._ok_args()
        a["equity"] = None
        got = LS.preflight(**a)
        self.assertFalse(got["ok"])
        self.assertNotIn("orders", got)


class B_TheStatusSurface(unittest.TestCase):

    def test_it_shows_every_slot_with_holder_pct_and_armed(self):
        e = _env(LIVE_PILOT_ENABLED="1",
                 ALPACA_ACCOUNT_1_KEY_ID="a", ALPACA_ACCOUNT_1_SECRET_KEY="b",
                 ALPACA_ACCOUNT_1_LIVE_PCT="0", ALPACA_ACCOUNT_1_HOLDER="Don",
                 ALPACA_ACCOUNT_2_KEY_ID="c", ALPACA_ACCOUNT_2_SECRET_KEY="d",
                 ALPACA_ACCOUNT_2_HOLDER="Family")
        st = LS.status(e)
        self.assertEqual(st["n_slots"], 2)
        s1 = [s for s in st["slots"] if s["slot"] == 1][0]
        self.assertEqual(s1["holder"], "Don")
        self.assertEqual(s1["pct"], 0.0)
        self.assertFalse(s1["armed"])
        s2 = [s for s in st["slots"] if s["slot"] == 2][0]
        self.assertFalse(s2["authorized"])

    def test_it_records_that_the_loss_stops_were_removed_by_instruction(self):
        st = LS.status(_env())
        self.assertIn("REMOVED", st["loss_stops"])
        self.assertIn("8a", st["loss_stops"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
