"""O-1 - long puts on accounting-flagged names. Register, kill gate, instrument, arithmetic.

Run as its own process and judged by EXIT CODE (`RUN_RULES` PART 0), never by grepping output.
"""
import ast
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tests.state_isolation  # noqa: F401,E402  MUST precede any valuation import

import numpy as np  # noqa: E402,F401
import pandas as pd  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

REGISTER = os.path.join(REPO, "PREREG_o1_long_puts_accounting_flags.md")
KILL_SRC = os.path.join(REPO, "scripts", "o1_kill.py")
ARM_SRC = os.path.join(REPO, "scripts", "o1_arm.py")


def _src(p):
    return io.open(p, encoding="utf-8").read()


def _tree(p):
    return ast.parse(_src(p))


def _strip_prose(p):
    """Source with comments and string literals removed. A guard that cannot tell CODE from
    PROSE ABOUT CODE is not measuring the tree - `MB15`'s defect, and the substring-ban family
    this record has now paid for five times."""
    import tokenize

    out = []
    with io.open(p, "rb") as fh:
        for tok in tokenize.tokenize(fh.readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            out.append(tok.string)
    return " ".join(out)


class TestRegister(unittest.TestCase):
    def test_the_register_exists_on_disk(self):
        """A citation a reader cannot check is not a citation - V6's own defect."""
        self.assertTrue(os.path.isfile(REGISTER))

    def test_the_register_carries_zero_python(self):
        s = _src(REGISTER)
        self.assertNotIn("def ", s.replace("`def `", ""))

    def test_the_declared_constants_are_the_shipped_ones(self):
        import o1_kill as K
        import o1_arm as A

        self.assertEqual(K.PRIMARY_X, 0.50)          # MA28's own crash definition
        self.assertEqual(K.KILL_RATIO, 2.0)          # MA28's own ratio bar, verbatim
        self.assertEqual(K.BAND, (150, 210))         # sec 4, E-5's arithmetic
        self.assertEqual(A.DTE_BAND, (150, 210))
        self.assertEqual(A.RIGHT, "P")
        self.assertEqual(A.DRAWS, 2000)
        self.assertEqual(A.SEED, 20260824)
        self.assertEqual(A.FLOOR_TRADES, 3600)

    def test_the_tenor_is_not_the_engines_own_band(self):
        """Sec 4 says the engine's 45-75 DTE band is NOT RUN. E-5 measured that the excess crash
        COUNT peaks in the SECOND quarter, so a 45-75 DTE put misses the peak of what it buys."""
        import o1_arm as A

        self.assertGreater(A.DTE_BAND[0], 75)


class TestMedianBan(unittest.TestCase):
    """THE MEDIAN IS BANNED ON A RETURN, and the ban is scoped to RETURNS - a tenor's median is
    an ordinary descriptive. `EVOWN` narrowed it after banning the word and failing against the
    CORRECT tree on a DTE median; that narrowing is inherited here rather than re-derived."""

    def _median_args(self, path):
        args = []
        for node in ast.walk(_tree(path)):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            name = getattr(f, "attr", None) or getattr(f, "id", None)
            if name != "median":
                continue
            for a in node.args:
                args.append(ast.dump(a))
        return args

    def test_no_median_is_taken_of_a_return_in_either_runner(self):
        for path in (KILL_SRC, ARM_SRC):
            for dumped in self._median_args(path):
                for banned in ("'ret'", '"ret"', "'ret_rho'", "'gap'", "'net_pnl'"):
                    self.assertNotIn(banned, dumped,
                                     "a median of a return in %s" % os.path.basename(path))

    def test_the_guard_can_still_bite_a_positive_control(self):
        """A narrowed guard that cannot fire is worse than none. `MB15`'s rule."""
        src = "import numpy as np\nx = np.median(d['ret'])\n"
        found = []
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
                if name == "median":
                    found += [ast.dump(a) for a in node.args]
        self.assertTrue(any("'ret'" in f for f in found))

    def test_a_median_of_a_tenor_is_permitted(self):
        """The narrowing is real, not decorative: this must NOT be caught."""
        src = "import numpy as np\nx = np.median(d['dte'])\n"
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
                if name == "median":
                    for a in node.args:
                        self.assertNotIn("'ret'", ast.dump(a))


class TestKillGate(unittest.TestCase):
    """The arm REFUSES without a passing kill artifact, and the refusal is proved by CONSTRUCTION
    rather than by removing it. `E-1` proved a refusal by flipping its flag and thereby RAN a
    withdrawn arm; the arm is never executed anywhere in this suite."""

    def test_the_refusal_is_conditional_and_not_hard_coded(self):
        fn = None
        for node in ast.walk(_tree(ARM_SRC)):
            if isinstance(node, ast.FunctionDef) and node.name == "require_kill":
                fn = node
        self.assertIsNotNone(fn, "o1_arm has no require_kill")
        raises = [n for n in ast.walk(fn) if isinstance(n, ast.Raise)]
        self.assertGreaterEqual(len(raises), 3, "fewer than three refusal states")
        ifs = [n for n in ast.walk(fn) if isinstance(n, ast.If)]
        self.assertGreaterEqual(len(ifs), 3, "a refusal that is not conditional")

    def test_absent_and_failing_kills_do_not_read_alike(self):
        """`E-1`'s lesson: a hard-coded refusal cannot tell ABSENT from FAILING, and telling a
        reader 'the kill did not pass' when the truth is 'it was never run' is the wrong thing."""
        import o1_arm as A
        import o1_kill as K

        p = K._out(K.OUT)
        real = _src(p) if os.path.isfile(p) else None
        try:
            if real is not None:
                os.remove(p)
            with self.assertRaises(SystemExit) as e1:
                A.require_kill()
            absent = str(e1.exception)

            with io.open(p, "w", encoding="utf-8") as fh:
                json.dump({"kill_fires": True, "kill_statistic": 9.9, "kill_bar": 2.0}, fh)
            with self.assertRaises(SystemExit) as e2:
                A.require_kill()
            fired = str(e2.exception)

            with io.open(p, "w", encoding="utf-8") as fh:
                json.dump({"kill_fires": False, "kill_statistic": None, "kill_bar": 2.0}, fh)
            with self.assertRaises(SystemExit) as e3:
                A.require_kill()
            empty = str(e3.exception)

            self.assertNotEqual(absent, fired)
            self.assertNotEqual(fired, empty)
            self.assertNotEqual(absent, empty)
            self.assertIn("NOT BEEN RUN", absent)
        finally:
            if real is not None:
                io.open(p, "w", encoding="utf-8", newline="").write(real)   # byte-for-byte
            elif os.path.isfile(p):
                os.remove(p)

    def test_the_gate_passes_only_on_a_genuinely_passing_artifact(self):
        import o1_arm as A
        import o1_kill as K

        p = K._out(K.OUT)
        real = _src(p) if os.path.isfile(p) else None
        try:
            with io.open(p, "w", encoding="utf-8") as fh:
                json.dump({"kill_fires": False, "kill_statistic": 1.2, "kill_bar": 2.0}, fh)
            self.assertEqual(A.require_kill()["kill_statistic"], 1.2)
        finally:
            if real is not None:
                io.open(p, "w", encoding="utf-8", newline="").write(real)
            elif os.path.isfile(p):
                os.remove(p)

    def test_build_and_score_both_call_the_gate(self):
        """A gate one entry point skips is not a gate."""
        t = _tree(ARM_SRC)
        for want in ("build", "score"):
            fn = [n for n in ast.walk(t)
                  if isinstance(n, ast.FunctionDef) and n.name == want]
            self.assertEqual(len(fn), 1)
            calls = [getattr(c.func, "id", None) for c in ast.walk(fn[0])
                     if isinstance(c, ast.Call)]
            self.assertIn("require_kill", calls, "%s does not call require_kill" % want)


class TestInstrumentIsImported(unittest.TestCase):
    """`B7`: a second copy of the picker or the exit engine would stop this measuring the
    shipped strategy while keeping its name."""

    def test_the_picker_and_the_exit_engine_are_imported_not_redefined(self):
        t = _tree(ARM_SRC)
        defined = {n.name for n in ast.walk(t) if isinstance(n, ast.FunctionDef)}
        for banned in ("pick_contract", "simulate_trade", "build_flags"):
            self.assertNotIn(banned, defined)
        s = _strip_prose(ARM_SRC)
        self.assertIn("OB . pick_contract", s.replace("OB.pick_contract", "OB . pick_contract"))

    def test_the_contract_multiplier_is_imported_and_never_typed(self):
        """`MA5`: `CONTRACT_MULTIPLIER` is already defined TWICE in this tree. A third would be
        the same defect, and this file's returns depend on it."""
        import o1_arm as A

        self.assertEqual(A.CONTRACT_MULTIPLIER, 100)
        t = _tree(ARM_SRC)
        assigns = [n for n in ast.walk(t)
                   if isinstance(n, ast.Assign)
                   and any(getattr(x, "id", None) == "CONTRACT_MULTIPLIER" for x in n.targets)]
        self.assertEqual(assigns, [], "CONTRACT_MULTIPLIER is re-defined here")

    def test_the_chain_key_carries_the_right(self):
        """`EVOWN`'s three-build-pass defect. A strike/expiry pair names TWO instruments and this
        book holds the expensive one; a history keyed without the right hands the exit engine a
        frame with both."""
        import o1_arm as A
        from evown_build import FreezeChains

        self.assertTrue(issubclass(A.HarvestChains, FreezeChains))
        # index_contracts is INHERITED, not overridden - that is what carries the fix
        self.assertIs(A.HarvestChains.index_contracts, FreezeChains.index_contracts)
        self.assertIs(A.HarvestChains.contract_history, FreezeChains.contract_history)

    def test_the_harvest_loader_reads_both_payload_shapes(self):
        """The EOD freeze pickles a bare frame, the harvest a dict carrying `rows`. Reading only
        the first collects NOTHING and does not raise - every date reads no_chain_on_date."""
        import o1_kill as K

        df = pd.DataFrame({"a": [1]})
        self.assertIs(K.chain_frame.__wrapped__ if hasattr(K.chain_frame, "__wrapped__")
                      else K.chain_frame, K.chain_frame)
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            p1 = os.path.join(d, "bare.pkl")
            p2 = os.path.join(d, "dict.pkl")
            df.to_pickle(p1)
            pd.to_pickle({"schema": 1, "rows": df, "max_dte": 1200}, p2)
            self.assertEqual(len(K.chain_frame(p1)), 1)
            self.assertEqual(len(K.chain_frame(p2)), 1)


class TestReturnArithmetic(unittest.TestCase):
    def test_the_multiplier_identity_holds(self):
        """`net_pnl` is DOLLARS and `entry_fill` is the PER-SHARE premium. The naive ratio reads
        a hundredfold high, and the engine's own constants are what prove the correction: a trade
        exiting at 'target' must land near TARGET_PCT and one exiting at 'stop' near STOP_PCT."""
        from valuation.edge import options_backtest as OB
        import o1_arm as A

        fill, pnl = 7.60, 778.70
        ret = pnl / (fill * A.CONTRACT_MULTIPLIER)
        self.assertAlmostEqual(ret, 1.0246, places=3)
        self.assertGreaterEqual(ret, OB.TARGET_PCT)
        naive = pnl / fill
        self.assertGreater(naive, 100 * OB.TARGET_PCT, "the naive ratio must be absurd")

    def test_a_stop_lands_on_the_engines_own_stop(self):
        from valuation.edge import options_backtest as OB
        import o1_arm as A

        ret = -411.30 / (7.75 * A.CONTRACT_MULTIPLIER)
        self.assertLessEqual(ret, OB.STOP_PCT)
        self.assertGreater(ret, OB.STOP_PCT - 0.15)


class TestPowerBeforeFloors(unittest.TestCase):
    """`EVOWN`'s self-reported defect: an n-floor is not a power floor, and the power must be
    written before the floor rather than after the scoring."""

    def test_the_registers_floor_reproduces_from_mb22s_own_gate(self):
        from valuation.edge import power_gate as pg
        import o1_arm as A

        need = pg.required_n(A.PRIOR_EFFECT_SD, n_trials=308)
        self.assertAlmostEqual(need, 3643, delta=60)
        self.assertAlmostEqual(A.FLOOR_TRADES, need, delta=100)

    def test_the_80_power_multiplier_exceeds_the_50_power_one(self):
        from valuation.edge import statistics as st

        crit = st.hlz_hurdle(308)
        self.assertAlmostEqual(crit, 3.3853, places=3)
        self.assertAlmostEqual((crit + 0.84) / crit, 1.2481, places=3)


class TestScopeAndFraming(unittest.TestCase):
    def test_no_arm_path_reads_a_book_file(self):
        """`MB8` measured the flag nearly DISJOINT from the top-decile book. O-1 is on the PANEL,
        and reading a book file here would silently answer MB8's question instead."""
        s = _strip_prose(ARM_SRC) + " " + _strip_prose(KILL_SRC)
        for banned in ("state_r2_corrected", "EVOWN_BOOK", "paper_track", "options_vrp"):
            self.assertNotIn(banned, s)

    def test_the_pinned_resolver_is_used_and_no_root_is_typed(self):
        s = _strip_prose(ARM_SRC) + " " + _strip_prose(KILL_SRC)
        self.assertNotIn("thetadata", s.lower())
        self.assertIn("resolve_harvest", s)

    def test_rho_is_labelled_an_extrapolation_where_it_is_emitted(self):
        """`O18` measured rho on 35-delta ~60-DTE CALLS; this book is PUTS at 150-210 DTE."""
        s = _src(ARM_SRC)
        self.assertIn("EXTRAPOLATION", s)
        self.assertIn("gap_at_rho_EXTRAPOLATION", s)

    def test_the_verdict_ships_with_its_mde(self):
        s = _src(ARM_SRC)
        for key in ("mde_80_power", "mde_50_power", "observed_over_mde80"):
            self.assertIn(key, s)


class TestBarsContract(unittest.TestCase):
    """A DEFECT OF MINE, pinned so it cannot come back silently.

    The engine expects `bars["date"]` to hold ISO STRINGS - `simulate_trade`'s settle branch does
    `ds <= expiry.isoformat()` and `window_ending` does `d <= as_of`. The canonical cache stores
    strings, and my first cut hand-built a dict of `datetime.date` objects. It raised `TypeError`
    on 26 of 2,688 trades, and those 26 were NOT a random 1%: they are exactly the trades that
    reached the SETTLE branch, which for a LONG PUT is where a deep-ITM expiry pays. The dropout
    therefore ran AGAINST the hypothesis, which is the direction that makes a null look safe.
    """

    def test_the_canonical_cache_stores_string_dates(self):
        from valuation.edge import options_backtest as OB
        import o1_kill as K

        b = OB.load_bars("AAPL", cache_dir=K._bars_dir())
        self.assertIsNotNone(b, "no populated bars cache")
        self.assertIsInstance(b["date"][0], str)
        self.assertTrue(b.get("raw_close"), "raw_close absent - U1-SPLIT needs as-traded")

    def test_the_arm_uses_the_shipped_loader_and_builds_no_bars_dict(self):
        """`B7`: a hand-built stand-in for a shipped object is how the two come apart."""
        t = _tree(ARM_SRC)
        fn = [n for n in ast.walk(t) if isinstance(n, ast.FunctionDef) and n.name == "build"][0]
        calls = []
        for c in ast.walk(fn):
            if isinstance(c, ast.Call):
                calls.append(getattr(c.func, "attr", None) or getattr(c.func, "id", None))
        self.assertIn("load_bars", calls, "build() does not call the shipped loader")
        # and no dict literal in build() carries a 'raw_close' key - that would be a stand-in
        for d in ast.walk(fn):
            if isinstance(d, ast.Dict):
                keys = [k.value for k in d.keys
                        if isinstance(k, ast.Constant) and isinstance(k.value, str)]
                self.assertNotIn("raw_close", keys, "build() hand-builds a bars dict")

    def test_a_date_typed_bars_dict_is_the_positive_control(self):
        """The guard must be about a REAL failure. Feeding the engine `datetime.date` objects
        where it expects strings raises - demonstrated, not asserted."""
        import datetime as _dt

        with self.assertRaises(TypeError):
            _dt.date(2018, 1, 16) <= "2018-06-15"   # noqa: B015  the exact comparison at :512


class TestBookIntegrity(unittest.TestCase):
    """Runs only when the book exists; skips LOUDLY otherwise so a vacuous pass is impossible."""

    def _book(self):
        import o1_kill as K
        import o1_arm as A

        p = K._out(A.BOOK)
        if not os.path.isfile(p):
            self.skipTest("no put book on disk yet (build has not run)")
        return pd.read_pickle(p)

    def test_no_row_was_dropped_to_a_simulator_error(self):
        b = self._book()
        bad = b[b["reason"].astype(str).str.startswith("sim_error")]
        self.assertEqual(len(bad), 0,
                         "%d rows dropped to a simulator error - a non-random dropout" % len(bad))

    def test_the_multiplier_identity_reproduces_on_the_real_book(self):
        b = self._book()
        t = b[b["traded"].fillna(False) & b["ret"].notna()]
        dev = (t["net_pnl"].astype(float)
               - t["ret"].astype(float) * t["entry_premium"].astype(float) * 100).abs().max()
        self.assertLess(float(dev), 1e-8)

    def test_every_contract_is_a_put_at_the_declared_tenor(self):
        import o1_arm as A

        b = self._book()
        t = b[b["traded"].fillna(False)]
        self.assertTrue((t["right"] == "P").all())
        self.assertTrue((t["delta"].dropna() < 0).all(), "a put's delta must be negative")
        self.assertGreaterEqual(int(t["dte"].min()), A.DTE_BAND[0])
        self.assertLessEqual(int(t["dte"].max()), A.DTE_BAND[1])

    def test_no_return_is_absurd(self):
        """`EVOWN`'s contract-key defect produced clean, plausible, enormous numbers and nothing
        raised. A long option cannot gain a hundredfold on a 35-delta put in six months."""
        b = self._book()
        t = b[b["traded"].fillna(False) & b["ret"].notna()]
        self.assertEqual(int((t["ret"] > 10).sum()), 0)
        self.assertLess(float(t["ret"].max()), 10.0)


class TestSplitGuard(unittest.TestCase):
    """`U1-SPLIT`, and omitting it was a DEFECT OF MINE.

    Option strikes are AS-TRADED and never adjusted for splits, while `raw_close` crosses one.
    `simulate_trade`'s `splits` argument DEFAULTS TO NONE - "the historical behaviour exactly" -
    so a caller that forgets it silently gets no guard at all, and nothing raises. Measured on
    this book: MNST entered 2016-10-18 on a 135 strike and split 3-for-1 on 2016-11-10, so the
    settle branch valued a pre-split strike against a post-split underlying and booked a fake
    +1453%. `U1-SPLIT` found the identical defect on GE's 1-for-8 reverse split.
    """

    def test_the_arm_loads_and_passes_splits(self):
        t = _tree(ARM_SRC)
        fn = [n for n in ast.walk(t) if isinstance(n, ast.FunctionDef) and n.name == "build"][0]
        names = [getattr(c.func, "attr", None) or getattr(c.func, "id", None)
                 for c in ast.walk(fn) if isinstance(c, ast.Call)]
        self.assertIn("load_splits", names, "build() never loads the split table")
        passed = False
        for c in ast.walk(fn):
            if not isinstance(c, ast.Call):
                continue
            if (getattr(c.func, "attr", None) or getattr(c.func, "id", None)) != "simulate_trade":
                continue
            for kw in c.keywords:
                if kw.arg == "splits":
                    passed = True
        self.assertTrue(passed, "simulate_trade is called WITHOUT splits= - the guard is off")

    def test_the_split_table_catches_the_real_case(self):
        """A positive control on the exact trade that produced the fake return."""
        import datetime as _dt
        from valuation.edge import options_backtest as OB
        import o1_kill as K

        sp = OB.load_splits(K._data())
        self.assertTrue(sp, "no split table on disk")
        self.assertTrue(OB.split_in_window(sp, "MNST", _dt.date(2016, 10, 18),
                                           _dt.date(2017, 3, 17)))
        # and it must NOT refuse a clean contract life, or it would empty the book
        self.assertFalse(OB.split_in_window(sp, "AAPL", _dt.date(2018, 1, 16),
                                            _dt.date(2018, 7, 20)))

    def test_no_split_spanning_trade_survives_in_the_book(self):
        import datetime as _dt
        from valuation.edge import options_backtest as OB
        import o1_kill as K
        import o1_arm as A

        bp = K._out(A.BOOK)
        if not os.path.isfile(bp):
            self.skipTest("no put book on disk yet")
        b = pd.read_pickle(bp)
        t = b[b["traded"].fillna(False)]
        if not len(t):
            self.skipTest("empty book")
        sp = OB.load_splits(K._data())
        bad = 0
        for tk, d, e in zip(t["ticker"], pd.to_datetime(t["date"]), t["expiration"]):
            if OB.split_in_window(sp, str(tk), d.date(),
                                  pd.Timestamp(str(e)[:10]).date()):
                bad += 1
        self.assertEqual(bad, 0, "%d traded rows span a split" % bad)


class TestFidelityGate(unittest.TestCase):
    def test_both_runners_gate_on_ma28s_published_count(self):
        """`MB21`'s C1 scored a perfect zero on an empty frame by comparing nothing. The COUNT
        is gated, not a rate compared loosely."""
        for path in (KILL_SRC, ARM_SRC):
            s = _strip_prose(path)
            self.assertIn("6542", s.replace(" ", ""),
                          "%s does not gate on MA28's count" % os.path.basename(path))


if __name__ == "__main__":
    unittest.main(verbosity=2)
