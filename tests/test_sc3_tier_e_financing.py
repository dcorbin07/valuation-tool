"""SC-3 (TIER-E-FIN) — the long-tenor financing measurement.

Judged by EXIT CODE (`RUN_RULES` PART 0), never by grepping output.

CI-SAFE BY CONSTRUCTION — `O-1`'s lesson applied upfront rather than after a failed land. `data/`
is gitignored, so every guard about the REGISTER and the SOURCE runs everywhere and only the
artifact-bound checks skip, LOUDLY. `MB42`: a guard whose only real execution is skipped IS the
defect.
"""
import ast
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tests.state_isolation  # noqa: F401,E402  MUST precede any valuation import

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

REGISTER = os.path.join(REPO, "PREREG_sc3_tier_e_financing.md")
COV_SRC = os.path.join(REPO, "scripts", "sc3_coverage.py")
ARM_SRC = os.path.join(REPO, "scripts", "sc3_arm.py")


def _src(p):
    with io.open(p, encoding="utf-8") as fh:
        return fh.read()


def _tree(p):
    return ast.parse(_src(p))


def _artifact(name):
    for cand in (os.path.join(REPO, "data"),
                 os.path.abspath(os.path.join(REPO, "..", "..", "..", "data"))):
        p = os.path.join(cand, "free_analysis", name)
        if os.path.isfile(p):
            return p
    return None


def _load(tc, name):
    p = _artifact(name)
    if p is None:
        tc.skipTest("no %s on this machine (data/ is gitignored; CI has none of it). The "
                    "REGISTER and SOURCE guards in this file still run." % name)
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


class TestRegister(unittest.TestCase):
    def test_the_register_exists_and_carries_zero_python(self):
        self.assertTrue(os.path.isfile(REGISTER))
        self.assertNotIn("def ", _src(REGISTER))

    def test_the_declared_constants_are_the_shipped_ones(self):
        import sc3_arm as A
        import sc3_coverage as COV

        self.assertEqual(COV.YEARS, (2016, 2017, 2018))
        self.assertEqual((COV.LONG_LO, COV.LONG_HI), (200, 858))
        self.assertEqual(A.STRATA, ((200, 300), (300, 450), (450, 650), (650, 858)))
        self.assertEqual(A.MIN_NAMES_PER_STRATUM, 100)
        self.assertEqual(A.SEED, 20260825)
        self.assertEqual(A.DRAWS, 2000)

    def test_the_tenor_starts_where_the_owned_cache_stops(self):
        """`MB4` closed this as unownable because the owned cache is capped at 200 DTE. Every
        pair here must be one `DEEPITM-FIN` structurally could not see."""
        import sc3_coverage as COV

        self.assertGreaterEqual(COV.LONG_LO, 200)

    def test_the_strata_are_declared_in_the_register_itself(self):
        """Fixed BEFORE any cost is read, so nothing is swept and reported at its best cell."""
        s = _src(REGISTER)
        for tok in ("200–300", "300–450", "450–650", "650–858"):
            self.assertIn(tok, s, "stratum %s is not declared in the register" % tok)

    def test_the_register_obeys_mb4s_do_not_re_derive_instruction(self):
        s = _src(REGISTER)
        self.assertIn("does not re-derive", s)
        self.assertIn("702", s)

    def test_the_register_states_the_binding_limitation_before_the_run(self):
        s = _src(REGISTER)
        self.assertIn("2016", s)
        self.assertIn("near-zero", s.lower())
        self.assertIn("UNMEASURED", s)


class TestInstrumentIsImported(unittest.TestCase):
    """`B7`: a second copy of the pair builder would stop this being the same measurement at a
    different tenor. Only the DTE band may move."""

    def test_nothing_redefines_deepitm_fins_primitives(self):
        for path in (COV_SRC, ARM_SRC):
            defined = {n.name for n in ast.walk(_tree(path))
                       if isinstance(n, ast.FunctionDef)}
            for banned in ("matched_pairs", "implied_rate", "call_delta", "pv_dividends",
                           "annual_cost", "load_spot", "load_dividends"):
                self.assertNotIn(banned, defined,
                                 "%s redefines %s" % (os.path.basename(path), banned))

    def test_the_rate_source_is_deepitm_fins_own_object(self):
        """One source for `rf`. Importing blackscholes a second time by name would be a second
        path to the same primitive."""
        import sc3_coverage as COV
        import deepitm_financing as D

        self.assertIs(COV.BS, D.BS)

    def test_the_delta_band_and_min_n_are_deepitm_fins_and_not_retuned(self):
        import sc3_coverage as COV
        import sc3_arm as A
        import deepitm_financing as D

        self.assertEqual((COV.DELTA_LO, COV.DELTA_HI), (D.DELTA_LO, D.DELTA_HI))
        self.assertEqual(A.MIN_N, D.MIN_N)

    def test_the_arm_calls_deepitm_fins_builder_and_cost_function(self):
        t = _tree(ARM_SRC)
        names = [getattr(c.func, "attr", None) or getattr(c.func, "id", None)
                 for c in ast.walk(t) if isinstance(c, ast.Call)]
        self.assertIn("build", names)
        self.assertIn("annual_cost", names)

    def test_the_dte_band_is_restored_after_being_moved(self):
        """The band is a MODULE constant on DEEPITM-FIN; moving it and not restoring would leave
        a global mutated for every later caller in the process."""
        for path in (COV_SRC, ARM_SRC):
            src = _src(path)
            self.assertIn("finally:", src, "%s moves the band without a finally" % path)
            self.assertIn("D.DTE_LO, D.DTE_HI = old", src)


class TestScopeAndFraming(unittest.TestCase):
    def test_the_pinned_resolver_is_used_and_no_root_is_typed(self):
        for path in (COV_SRC, ARM_SRC):
            s = _src(path)
            self.assertIn("resolve_harvest", s)
            self.assertNotIn("D:\\thetadata", s)

    def test_the_cards_are_labelled_assumptions(self):
        s = _src(ARM_SRC)
        self.assertIn("ASSUMPTION", s)

    def test_the_verdict_ships_with_its_mde(self):
        s = _src(ARM_SRC)
        for k in ("mde_80_power_bps", "mde_50_power_bps"):
            self.assertIn(k, s)

    def test_the_rho_leg_is_labelled_an_extrapolation(self):
        """`O18` measured rho on 35-delta ~60-DTE contracts; this is 200-858 DTE."""
        s = _src(ARM_SRC)
        self.assertIn("EXTRAPOLATION", s)

    def test_no_return_claim_is_made_anywhere(self):
        """`P1S0` closed the options-expression family on the RETURN side; this is a COST
        measurement and does not reopen it."""
        s = _src(ARM_SRC).lower()
        for banned in ("expectancy", "sharpe", "alpha"):
            self.assertNotIn(banned, s)


class TestMeasuredFindings(unittest.TestCase):
    """Skips LOUDLY where the artifact is absent."""

    def test_coverage_is_what_the_register_quotes(self):
        d = _load(self, "SC3_COVERAGE.json")
        self.assertEqual(d["scoreable_pairs"], 2352345)
        self.assertEqual(d["scoreable_names"], 411)
        self.assertEqual(d["names_reaching_min_n"], 408)
        self.assertEqual(d["dte_distribution"]["max"], 858)

    def test_the_arm_scored_every_declared_stratum(self):
        import sc3_arm as A

        d = _load(self, "SC3_ARM.json")
        for lo, hi in A.STRATA:
            self.assertIn("%d_%d" % (lo, hi), d["results"]["quoted_spread_primary"],
                          "a declared stratum is missing - quoting a subset is a void condition")

    def test_the_unit_of_independence_is_the_name(self):
        d = _load(self, "SC3_ARM.json")
        self.assertIn("NAME", d["unit_of_independence"])
        for k, v in d["results"]["quoted_spread_primary"].items():
            if v.get("verdict") == "UNDERPOWERED":
                continue
            # n used for the interval must be names, which is far below the pair count
            self.assertLess(v["names"], v["pairs"] / 100)

    def test_the_verdict_is_taken_on_the_executable_leg(self):
        d = _load(self, "SC3_ARM.json")
        self.assertIn("EXECUTABLE", d["verdict_basis"])

    def test_the_liquidity_caution_is_quantified_rather_than_asserted(self):
        """A single-name smoke test on the most liquid name read ~10x cheaper than the cross-name
        median. The per-name unit exists for exactly that reason, and the caution is a NUMBER."""
        d = _load(self, "SC3_ARM.json")
        c = d.get("liquidity_caution")
        if not c:
            self.skipTest("no liquidity caution block (AAPL absent from the stratum)")
        self.assertLess(c["all_in_bps"], c["cross_name_median_bps"])
        self.assertLess(c["percentile_of_names_cheaper"], 10.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
