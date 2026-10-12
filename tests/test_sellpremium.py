"""SELL-PREMIUM — what these tests pin, and why each one exists.

Register: `PREREG_sellpremium.md`, committed ALONE at `2e9fe7b`.

THE LOAD-BEARING ONES, in order of what they would cost if they failed silently:

1. **THE TWO PRICE BASES, FROM BOTH SIDES.** The chain is AS-TRADED and the prepared price file
   is split- and dividend-adjusted — AAPL 2018-01-02 reads 172.260 against 40.234, a factor of
   4.28. `O-1` booked a fake +1453% matching an as-traded strike against an adjusted close, and
   `V6`'s `C5` is the mirror. Pinned with a positive control, or the guard passes by detecting
   that two numbers differ rather than detecting the adjustment.

2. **THE QUOTE FUNNEL READS THE RAW LAYER.** `options_derived` is two-sided on 1.0000 of its
   rows BY CONSTRUCTION, so `K1`'s funnel measured there would read 1.000 having checked
   nothing — `MB21`'s `C1`, which scored a perfect 0.000e+00 on an empty frame.

3. **THE ARM GATE REFUSES, IN THREE DISTINCT STATES.** `E-1`: a hard-coded refusal cannot tell
   "the control never ran" from "the control ran and fired". Exercised by its own function on
   synthetic artifacts; **the arm is never run**, which is `E-1`'s other lesson — a test proving
   a refusal by REMOVING it is unsafe when the thing behind it is forbidden.

4. **NO BAR IS RETYPED IN A SCRIPT** (`MA5`), read from the SYNTAX TREE and not grepped, because
   `MA49` recorded a fixture failing against the FIXED tree when a repair comment quoted the
   defect verbatim.

5. **DON'S RULING IS IN THE REGISTER, VERBATIM AND ATTRIBUTED TO HIM.** It is the thing that
   filled the draft's one blank, and a register that paraphrased it would be an executor choice
   wearing an owner's authority.

    python tests/test_sellpremium.py
"""
from __future__ import annotations

import ast
import io
import json
import os
import subprocess
import sys
import unittest

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.studies import dipcall as D  # noqa: E402
from valuation.studies import sellpremium as SP  # noqa: E402

_SKIPS = []


def _skip(t, why):
    _SKIPS.append(why)
    t.skipTest(why)


def _src(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def _art(name):
    if not D.have_data():
        return None
    p = D.out_path(name)
    if not os.path.isfile(p):
        return None
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


# =============================================================================================
# 1. THE REGISTER
# =============================================================================================
class Register(unittest.TestCase):
    REG = "PREREG_sellpremium.md"

    def test_it_exists_and_was_committed_ALONE_and_is_an_ANCESTOR(self):
        self.assertTrue(os.path.isfile(os.path.join(REPO, self.REG)))

        def git(*a):
            return subprocess.run(("git",) + a, cwd=REPO, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL).stdout.decode("utf-8", "replace")
        sha = ""
        for line in git("log", "--format=%H", "--", self.REG).splitlines():
            sha = line.strip()                      # the OLDEST commit touching it
        if not sha:
            _skip(self, "no git history for %s in this checkout" % self.REG)
        files = [x for x in git("show", "--name-only", "--format=", sha).split() if x]
        self.assertEqual(files, [self.REG],
                         "the register was NOT committed alone: %s" % files)
        self.assertTrue(all(f.endswith(".md") for f in files))
        anc = subprocess.run(("git", "merge-base", "--is-ancestor", sha, "HEAD"), cwd=REPO,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertEqual(anc.returncode, 0, "the register is not an ancestor of HEAD")

    def test_it_declares_all_thirteen_amendments_and_the_void_conditions(self):
        txt = _src(self.REG)
        for a in ["## S%d" % i for i in range(1, 14)]:
            self.assertIn(a, txt, "the register is missing amendment %s" % a)
        self.assertIn("VOID CONDITIONS", txt.upper())
        self.assertIn("LABELLED UNCALIBRATED", txt)

    def test_DONS_RULING_is_quoted_VERBATIM_and_attributed_to_HIM(self):
        """`S1`. A paraphrase would be an executor choice wearing an owner's authority."""
        txt = _src(self.REG)
        self.assertIn("its own system, not judged against the Index or against holding the", txt)
        self.assertIn("Don's ruling and not an executor choice", txt)
        self.assertIn("2026-10-12", txt)

    def test_it_records_that_the_ruling_is_NOT_in_DECISIONS_md(self):
        """The premise correction. Reported, not edited — `DECISIONS.md` is the manager's."""
        self.assertIn("It is not there", _src(self.REG))
        self.assertNotIn("2026-10-12", _src("DECISIONS.md"),
                         "DECISIONS.md now carries the ruling; this register's premise "
                         "correction is stale and should be re-read")

    def test_the_ELIGIBLE_BUT_UNRESOLVED_label_is_pre_committed(self):
        """`S10`. Stage 1 holds ZERO 30% crashes and a short-vol book's risk is all in those."""
        txt = _src(self.REG)
        self.assertIn("ELIGIBLE-BUT-UNRESOLVED", txt)
        self.assertIn("ZERO 30% crashes", txt)


# =============================================================================================
# 2. THE SPLIT TRAP, BOTH DIRECTIONS (S4)
# =============================================================================================
class PriceBasis(unittest.TestCase):
    def test_spot_comes_from_the_CHAIN_and_never_from_the_prepared_price_file(self):
        """AST, not a grep (`MA49`). `spot_by_date` must not reach `dipcall.read_prices`, which
        returns the ADJUSTED series."""
        tree = ast.parse(_src("valuation/studies/sellpremium.py"))
        fn = [n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "spot_by_date"]
        self.assertEqual(len(fn), 1)
        calls = {ast.unparse(n.func) for n in ast.walk(fn[0]) if isinstance(n, ast.Call)}
        for banned in ("D.read_prices", "read_prices", "D.prices_dir", "prices_dir"):
            self.assertNotIn(banned, calls,
                             "spot_by_date reaches the ADJUSTED price file: %s" % banned)
        self.assertIn("derived_dir", " ".join(calls))

    def test_the_two_bases_differ_MATERIALLY_on_a_split_name(self):
        """The positive control: if they agreed, every guard above would be vacuous."""
        if not D.have_data():
            _skip(self, "no populated data root (data/ is gitignored, so CI has none)")
        if not SP.has_chain("AAPL", 2018):
            _skip(self, "AAPL-2018 chain absent")
        spot = SP.spot_by_date("AAPL", 2018)
        px = D.read_prices("AAPL")
        self.assertTrue(spot)
        d = "2018-01-02"
        adj = float(px[px["date"] == d]["close"].iloc[0])
        self.assertGreater(spot[d] / adj, 3.0,
                           "the chain's spot and the prepared close agree, so the split trap "
                           "cannot be detected by anything here")

    def test_settlement_imports_the_shipped_primitive_and_writes_no_arithmetic(self):
        """`B7`/`S5`. One definition of a settled put, and it is `V6-OPT`'s."""
        src = _src("scripts/sellpremium_kills.py")
        self.assertIn("settle_short", src)
        tree = ast.parse(src)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertNotIn("intrinsic_obligation", names,
                         "settlement arithmetic was re-implemented instead of imported")

    def test_the_shipped_primitive_REFUSES_an_adjusted_basis(self):
        """`S4` is enforced by the primitive, not only by intention."""
        from valuation.edge.assignment import settle_short, CASH_SECURED_PUT
        with self.assertRaises(Exception):
            settle_short(strike=100.0, credit=1.0, spot_at_expiry=95.0, right="put",
                         spot_basis="adjusted", method=CASH_SECURED_PUT)
        ok = settle_short(strike=100.0, credit=1.0, spot_at_expiry=95.0, right="put",
                          spot_basis=SP.AS_TRADED, method=CASH_SECURED_PUT)
        self.assertTrue(ok["assigned"])
        self.assertAlmostEqual(ok["ret_on_secured"], (1.0 - 5.0) / 100.0, places=12)


# =============================================================================================
# 3. THE FUNNEL AND THE PICK
# =============================================================================================
def _chain(rows):
    return pd.DataFrame(rows, columns=["expiration", "strike", "right", "date", "bid", "ask",
                                       "volume", "open_interest"])


class Funnel(unittest.TestCase):
    def setUp(self):
        self.spot = {"2018-03-01": 100.0}
        self.raw = _chain([
            ["2018-04-05", 90.0, "P", "2018-03-01", 1.00, 1.10, 10, 100],   # usable
            ["2018-04-05", 93.0, "P", "2018-03-01", 1.40, 1.50, 10, 100],   # usable
            ["2018-04-05", 80.0, "P", "2018-03-01", 0.30, 0.40, 10, 100],   # out of band
            ["2018-04-05", 91.0, "P", "2018-03-01", 0.00, 0.50, 10, 100],   # ONE-SIDED
            ["2018-03-05", 90.0, "P", "2018-03-01", 0.20, 0.30, 10, 100],   # 4 DTE, out of band
            ["2018-04-05", 90.0, "C", "2018-03-01", 9.00, 9.10, 10, 100],   # a CALL
        ])

    def test_a_ONE_SIDED_quote_is_excluded_and_a_two_sided_one_is_KEPT(self):
        f = SP.put_funnel(self.raw, self.spot, "2018-03-01")
        self.assertEqual(f["any_put"], 5, "the call leaked into a put funnel")
        self.assertEqual(f["in_dte"], 4)
        self.assertEqual(f["in_moneyness"], 3)
        self.assertEqual(f["two_sided"], 2, "the zero-bid row survived the quote step")
        self.assertEqual(len(f["cands"]), 2)

    def test_a_missing_spot_is_a_NAMED_state_and_never_a_silent_zero(self):
        f = SP.put_funnel(self.raw, {}, "2018-03-01")
        self.assertTrue(f.get("no_spot"))
        self.assertEqual(f["two_sided"], 0)

    def test_pick_takes_the_strike_nearest_the_target_moneyness_and_is_deterministic(self):
        f = SP.put_funnel(self.raw, self.spot, "2018-03-01")
        a = SP.pick_put(f["cands"])
        b = SP.pick_put(f["cands"])
        self.assertEqual(a["strike"], 90.0)
        self.assertAlmostEqual(a["moneyness"], 0.90, places=12)
        self.assertEqual(a, b, "the pick is not deterministic, so a re-run is not bit-identical")

    def test_the_funnel_reads_the_RAW_layer_and_the_derived_one_is_vacuous_there(self):
        """`MB21`'s `C1` family. Measured on real data when it is present."""
        c = _art("SELLPREMIUM_CONTROLS.json")
        if not c:
            _skip(self, "SELLPREMIUM_CONTROLS.json absent (data/ is gitignored)")
        cells = c["C3_derived_vacuity"]["cells"]
        self.assertTrue(cells)
        for x in cells:
            self.assertGreaterEqual(x["derived_two_sided_share"], 0.9999)
            self.assertLess(x["raw_two_sided_share"], 0.95,
                            "the raw layer is also all two-sided, so reading it buys nothing")


# =============================================================================================
# 4. K3's ARITHMETIC
# =============================================================================================
class CrashStress(unittest.TestCase):
    def test_years_of_premium_reproduces_a_hand_case(self):
        """0.90 moneyness, a 45.65% fall: loss = (0.4565 - 0.10)/0.90 = 0.39611..."""
        y = SP.years_of_premium(0.4565, 0.90, 0.007778, 5.727)
        self.assertAlmostEqual((0.4565 - 0.10) / 0.90, 0.3961111, places=6)
        self.assertAlmostEqual(y, 0.3961111 / (0.007778 * 5.727), places=4)

    def test_a_fall_inside_the_cushion_costs_NOTHING(self):
        """A 0.90-moneyness put is unharmed by a fall of less than 10%, which is the whole
        reason the moneyness is a design choice and not a detail."""
        self.assertEqual(SP.years_of_premium(0.05, 0.90, 0.01, 5.0), 0.0)

    def test_K3_FIRED_on_the_real_artifact_and_the_bar_was_not_relaxed(self):
        a = _art("SELLPREMIUM_KILLS.json")
        if not a:
            _skip(self, "SELLPREMIUM_KILLS.json absent (data/ is gitignored)")
        self.assertEqual(a["K3_crash"]["bar"], SP.K3_MAX_YEARS_OF_PREMIUM)
        self.assertEqual(SP.K3_MAX_YEARS_OF_PREMIUM, 6.0, "the pre-committed bar moved (W-28)")
        self.assertFalse(a["gates"]["K3_crash_stress"])
        self.assertGreater(a["K3_crash"]["worst_years_of_premium"], 6.0)
        self.assertFalse(a["all_pass"])

    def test_the_binding_row_carries_its_loss_field(self):
        """It did not, on the first pass, and it is the row that decided the gate."""
        a = _art("SELLPREMIUM_KILLS.json")
        if not a:
            _skip(self, "SELLPREMIUM_KILLS.json absent (data/ is gitignored)")
        row = a["K3_crash"]["table"]["single_name_at_1.4x_the_worst_index_episode"]
        self.assertIn("loss_on_secured_cash", row)
        self.assertTrue(np.isfinite(float(row["loss_on_secured_cash"])))


# =============================================================================================
# 5. THE ARM GATE REFUSES, THREE DISTINCT STATES, AND THE ARM IS NEVER RUN
# =============================================================================================
class ArmGate(unittest.TestCase):
    def _gate(self):
        sys.path.insert(0, os.path.join(REPO, "scripts"))
        from scripts import sellpremium_arm as A
        return A

    def test_an_ABSENT_artifact_and_a_FIRED_one_give_DIFFERENT_refusals(self):
        import tempfile
        A = self._gate()
        with tempfile.TemporaryDirectory() as d:
            missing = os.path.join(d, "nope.json")
            with self.assertRaises(SystemExit) as e1:
                A.require_kills(missing)
            fired = os.path.join(d, "fired.json")
            with io.open(fired, "w", encoding="utf-8") as fh:
                json.dump({"gates": {"K1": True, "K3": False}}, fh)
            with self.assertRaises(SystemExit) as e2:
                A.require_kills(fired)
            empty = os.path.join(d, "empty.json")
            with io.open(empty, "w", encoding="utf-8") as fh:
                json.dump({"nothing": 1}, fh)
            with self.assertRaises(SystemExit) as e3:
                A.require_kills(empty)
        msgs = [str(e1.exception), str(e2.exception), str(e3.exception)]
        self.assertIn("ABSENT", msgs[0])
        self.assertIn("FIRED", msgs[1])
        self.assertIn("no `gates` block", msgs[2])
        self.assertEqual(len(set(msgs)), 3, "two refusal states share a message (E-1)")

    def test_a_PASSING_artifact_is_accepted_so_the_refusal_is_a_GATE_not_a_hard_stop(self):
        import tempfile
        A = self._gate()
        with tempfile.TemporaryDirectory() as d:
            ok = os.path.join(d, "ok.json")
            with io.open(ok, "w", encoding="utf-8") as fh:
                json.dump({"gates": {"K1": True, "K2": True, "K3": True, "K4": True}}, fh)
            got = A.require_kills(ok)
        self.assertTrue(all(got["gates"].values()))

    def test_NO_ARM_IS_BUILT_and_no_arm_artifact_exists(self):
        """`S10`/`E-1`. The arms are named as NOT BUILT; an arm artifact would mean one ran."""
        src = _src("scripts/sellpremium_arm.py")
        self.assertIn("NOT BUILT", src)
        for banned in ("permutation_null", "clustered", "sign_test", "paired"):
            self.assertNotIn("def %s" % banned, src)
        if D.have_data():
            self.assertFalse(os.path.isfile(D.out_path("SELLPREMIUM_ARM.json")),
                             "an arm artifact exists and the register's kill fired")

    def test_the_gate_refuses_against_the_REAL_artifact(self):
        A = self._gate()
        if not D.have_data() or not os.path.isfile(D.out_path("SELLPREMIUM_KILLS.json")):
            _skip(self, "SELLPREMIUM_KILLS.json absent (data/ is gitignored)")
        with self.assertRaises(SystemExit) as e:
            A.require_kills()
        self.assertIn("K3_crash_stress", str(e.exception))


# =============================================================================================
# 6. NO BAR IS RETYPED (MA5), AND BH's k DOES NOT SHRINK (W-28)
# =============================================================================================
class BarsAndMultiplicity(unittest.TestCase):
    BARS = {400: "K1_MIN_EVENTS", 150: "K1_MIN_COVERED_DAYS", 6.0: "K3_MAX_YEARS_OF_PREMIUM",
            0.90: "MONEYNESS_TARGET"}

    def test_no_script_COMPARES_against_a_bar_defined_in_the_study_module(self):
        """`MA5`: a default is exactly how the Harvey-Liu-Zhu bar froze at 3.0, and these bars
        are PRE-COMMITTED. Read from the SYNTAX TREE (`MA49`) — and read as a COMPARISON rather
        than as a bare literal.

        A first cut banned the bare literal and **fired against the correct tree**: `150` is the
        modulus of a progress print (`i % 150 == 0`), not `K1_MIN_COVERED_DAYS`. A bare integer
        is too weak a signal for a guard, which is the never-ban-a-substring family one level
        down. The property that actually matters is that a script never **tests** a measured
        quantity against a retyped bar, so the guard reads the DIRECT constant operands of
        `Compare` nodes: `len(picks) >= 400` is caught and `i % 150 == 0` is not.
        """
        for rel in ("scripts/sellpremium_kills.py", "scripts/sellpremium_arm.py"):
            tree = ast.parse(_src(rel))
            operands = []
            for n in ast.walk(tree):
                if isinstance(n, ast.Compare):
                    for side in [n.left] + list(n.comparators):
                        if isinstance(side, ast.Constant) and isinstance(
                                side.value, (int, float)) and not isinstance(side.value, bool):
                            operands.append(side.value)
            for v, name in self.BARS.items():
                self.assertNotIn(v, operands,
                                 "%s compares against the retyped bar %r (SP.%s)"
                                 % (rel, v, name))

    def test_and_that_guard_is_NOT_vacuous_it_catches_a_retyped_bar(self):
        """The positive control. Without it the test above passes on an empty operand list."""
        tree = ast.parse("import x\nif len(x) >= 400:\n    pass\n")
        operands = [s.value for n in ast.walk(tree) if isinstance(n, ast.Compare)
                    for s in [n.left] + list(n.comparators)
                    if isinstance(s, ast.Constant) and isinstance(s.value, (int, float))]
        self.assertIn(400, operands)

    def test_each_bar_is_REFERENCED_BY_NAME_where_it_is_used(self):
        """The other half: a guard that only bans a literal passes on a script that uses no bar
        at all. The kills script must reach every one of them through the module."""
        src = _src("scripts/sellpremium_kills.py")
        for name in ("K1_MIN_EVENTS", "K1_MIN_COVERED_DAYS", "K3_MAX_YEARS_OF_PREMIUM",
                     "MONEYNESS_TARGET"):
            self.assertIn("SP.%s" % name, src, "the kills script never reads SP.%s" % name)

    def test_the_study_module_holds_them_once(self):
        self.assertEqual(SP.K1_MIN_EVENTS, 400)
        self.assertEqual(SP.K1_MIN_COVERED_DAYS, 150)
        self.assertEqual(SP.K3_MAX_YEARS_OF_PREMIUM, 6.0)
        self.assertEqual(SP.MONEYNESS_TARGET, 0.90)
        self.assertEqual(SP.MONEYNESS_BAND, (0.85, 0.95))
        self.assertEqual(SP.DTE_BAND, (20, 60))

    def test_BH_k_is_FIXED_at_five_and_a_firing_kill_does_not_shrink_it(self):
        self.assertEqual(SP.BH_K, 5)
        rows = SP.benjamini_hochberg([0.001, 0.5])
        self.assertEqual([r["bh_threshold"] for r in rows], [0.02, 0.04])
        # If k had shrunk to the two arms actually scored, rank 1 would be 0.05 -- easier.
        self.assertNotEqual(rows[0]["bh_threshold"], SP.BH_Q / 2.0)

    def test_the_event_and_tier_are_IMPORTED_from_dipcall_and_not_redefined(self):
        """`B7`/`S5`. A second event definition is how two registers report two numbers."""
        tree = ast.parse(_src("valuation/studies/sellpremium.py"))
        assigned = {t.id for n in ast.walk(tree) if isinstance(n, ast.Assign)
                    for t in n.targets if isinstance(t, ast.Name)}
        for banned in ("K_PRIMARY", "VOL_WIN", "MIN_VOL_OBS", "TIER_FLOOR"):
            self.assertNotIn(banned, assigned,
                             "sellpremium re-defines dipcall's %s" % banned)
        self.assertIn("from valuation.studies import dipcall as D",
                      _src("valuation/studies/sellpremium.py"))


# =============================================================================================
# 7. THE LANDED RECORD
# =============================================================================================
class LandedRecord(unittest.TestCase):
    def test_K1_cleared_both_floors_and_K2_flattened(self):
        a = _art("SELLPREMIUM_KILLS.json")
        if not a:
            _skip(self, "SELLPREMIUM_KILLS.json absent (data/ is gitignored)")
        k1, k2 = a["K1_coverage"], a["K2_premise"]
        self.assertTrue(k1["pass"])
        self.assertGreaterEqual(k1["priceable_events"], SP.K1_MIN_EVENTS)
        self.assertGreaterEqual(k1["covered_event_days"], SP.K1_MIN_COVERED_DAYS)
        self.assertTrue(k2["pass"])
        # The finding: the naked gradient is an order of magnitude flatter than A3's spread one.
        self.assertGreater(k2["gradient_top_minus_bottom_pp"],
                           k2["a3_banked_spread_gradient_pp"])
        self.assertEqual(k2["coverage"], 1.0,
                         "K2 priced a SUBSET of A3's era trades and is a different object (S6)")

    def test_the_trials_stayed_charged_after_the_kill_fired(self):
        """`E-1`/`MA6`. Un-booking after watching a kill fire is the shape to distrust."""
        from valuation.edge import research_log
        self.assertEqual(research_log.detail()["by_domain"]["options"], 315)
        self.assertIn("| SELL-PREMIUM |", _src("RESEARCH_LOG.md"))


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
