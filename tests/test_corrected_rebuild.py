# -*- coding: utf-8 -*-
"""`CORRECTED-REBUILD` — one rebuild of the corrected full-universe panel.

Structural tests run everywhere; data-dependent ones SKIP LOUDLY (`data/` is gitignored, so a CI
runner has none of it). Nothing here imports a module that resolves a data root at IMPORT time —
`CORRECTED-FLOORS` part 1 failed its land on exactly that.
"""
from __future__ import annotations

import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

_SKIPS = []


def _skip(n, w):
    _SKIPS.append("%s (%s)" % (n, w))


def _src(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def _tree(rel):
    return ast.parse(_src(rel))


def _consts(rel):
    out = {}
    for n in _tree(rel).body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                and isinstance(n.targets[0], ast.Name):
            try:
                out[n.targets[0].id] = ast.literal_eval(n.value)
            except (ValueError, SyntaxError):
                pass
    return out



_PIT = {"loaded": False, "row": None}


def _pit_row():
    """ONE point-in-time row, loaded once and shared.

    Each test that wanted it was loading a 495MB export separately and the suite took 138s. The
    gate runs 255 suites, so a two-minute suite is a tax on every land.
    """
    if _PIT["loaded"]:
        return _PIT["row"]
    _PIT["loaded"] = True
    try:
        from scripts.index_best import _data_root
        from valuation.edge.data_providers import WRDSProvider
        export = os.path.join(_data_root(), "full2009", "backtest")
        if not os.path.exists(export):
            return None

        class _C:
            wrds_data_dir = export

        pr = WRDSProvider(_C())
        pr.ready()
        _PIT["row"] = pr.fundamentals_pit("AAPL", "2019-06-28")
    except Exception:                                   # noqa: BLE001
        _PIT["row"] = None
    return _PIT["row"]


def _artifact(name):
    try:
        import json
        from scripts.index_best import _data_root
        p = os.path.join(_data_root(), "free_analysis", name)
        if not os.path.exists(p):
            return None
        with io.open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:                                   # noqa: BLE001
        return None


class TheKeepAdditionIsPurelyAdditive(unittest.TestCase):
    """**A DEFECT OF MY OWN, CAUGHT ON THE COLUMN COUNT.** My first patch to `_KEEP` replaced a
    line instead of inserting after it, so 45 columns became 44 — it dropped `assets`, `debtnc`,
    `currentratio` and `assetturnover` and added a duplicate. **`assets` is precisely the column
    whose silent loss once left `capital_discipline` half-empty in every prior run.** Reverted and
    redone as an insertion; these pin the property so a future edit cannot repeat it."""

    def _keep(self):
        from valuation.edge.data_providers import WRDSProvider
        return list(WRDSProvider._KEEP["fundamentals"])

    def test_the_two_payout_columns_are_present(self):
        k = self._keep()
        for c in ("ncfdiv", "ncfcommon"):
            self.assertIn(c, k)

    def test_nothing_was_dropped_and_there_are_no_duplicates(self):
        k = self._keep()
        self.assertEqual(len(k), len(set(k)), "duplicate columns in the allowlist")
        for c in ("assets", "ncfo", "debtnc", "currentratio", "assetturnover",
                  "netinc", "fcf", "marketcap", "equity", "sharesbas"):
            self.assertIn(c, k, "%s is load-bearing and must not be dropped" % c)

    def test_the_allowlist_grew_by_exactly_seven(self):
        """Pinned as a literal (`MA13`'s idiom) so a silent widening shows as a diff here.

        45 before this item; +2 for batch 2's payout legs and +5 for batch 3's columns (folded
        into the same pass per addendum 2, so no batch-3 arm is later NOT RUN for a missing
        column) = 52."""
        self.assertEqual(len(self._keep()), 52,
                         "the allowlist was 45 before CORRECTED-REBUILD; +2 payout +5 batch-3 "
                         "= 52, and any other count means something else moved")

    def test_batch_3s_five_columns_are_present_with_their_coverage_recorded(self):
        k = self._keep()
        for c in ("capex", "liabilities", "assetsc", "workingcapital", "retearn"):
            self.assertIn(c, k)
        s = _src("valuation/edge/data_providers.py")
        for n in ("0.9479", "0.9995", "0.7986", "0.7950", "0.9583"):
            self.assertIn(n, s, "the measured coverage %s is not recorded beside the column" % n)

    def test_NO_REBUILD_was_claimed_for_the_batch_3_columns_and_the_reason_is_recorded(self):
        """`_KEEP` is applied as a pure column SELECTION, so adding a name can only widen what is
        kept. The claim is empirical, not architectural: the panel built WITHOUT the payout pair
        and the one built WITH it agree on 3,251,787 cells with ZERO moved."""
        s = _src("valuation/edge/data_providers.py")
        self.assertIn("NO REBUILD WAS NEEDED", s)
        self.assertIn("3,251,787", s)
        prov = _src("valuation/edge/data_providers.py")
        self.assertIn("[c for c in keep if c in df.columns]", prov,
                      "if _KEEP stopped being a pure selection, adding a column could change "
                      "another column's value and the no-rebuild claim would not hold")

    def test_the_capex_SIGN_identity_is_pinned_and_holds_on_real_rows(self):
        """`capex = fcf - ncfo`, because Sharadar stores capex as a NEGATIVE outflow. The draft
        records that its own first reading had this BACKWARDS, which would flip the sign of every
        capex leg downstream. Reproduced independently on 646,020 complete ARQ rows of the
        corrected universe: `ncfo - fcf == -capex` on 0.999844 against `== +capex` on 0.081419,
        and `capex < 0` on 0.8732."""
        s = _src("valuation/edge/data_providers.py")
        self.assertIn("capex = fcf - ncfo", s)
        self.assertIn("NEGATIVE cash outflow", s)
        self.assertIn("0.999844", s)
        # and the identity on a NAMED example, to the dollar
        r = _pit_row()
        if not r or r.get("capex") is None:
            _skip("capex", "corrected export / AAPL row unavailable")
            return
        self.assertEqual(r["fcf"] - r["ncfo"], r["capex"],
                         "the capex identity does not hold to the dollar on a named row")
        self.assertLess(r["capex"], 0, "Sharadar's capex should be a negative outflow")

    def test_the_coverage_that_licensed_the_addition_is_recorded_beside_it(self):
        """THE COVERAGE RULE: five wired factors were silently empty for this project's entire
        history. The measurement must travel with the column, not live only in a handoff."""
        s = _src("valuation/edge/data_providers.py")
        self.assertIn("COVERAGE RULE", s)
        for n in ("0.9338", "0.9484", "0.9242", "0.9383"):
            self.assertIn(n, s, "the measured coverage %s is not recorded beside the column" % n)

    def test_the_non_zero_figure_is_distinguished_from_coverage(self):
        """For a PAYOUT column zero is a legitimate value, so non-null is coverage and non-zero
        is economic incidence. They differ by two thirds here and conflating them would
        understate the usable population."""
        s = _src("valuation/edge/data_providers.py")
        self.assertIn("ECONOMIC INCIDENCE", s)
        self.assertIn("33.55", s)
        self.assertIn("50.79", s)


class TheThreeChangesAreDeclaredAndNoMore(unittest.TestCase):
    """The whole value of one rebuild is that successors can treat it as `UNIVERSE-BIAS`'s panel
    plus three named additions. A fourth undeclared change would make every successor figure
    incomparable to `CORRECTED-FLOORS`' floors."""

    def test_the_extra_horizons_are_S22s_own_grid(self):
        c = _consts("scripts/corrected_rebuild.py")
        eh = tuple(c["EXTRA_HORIZONS"])
        from scripts.term_structure import HORIZONS
        self.assertEqual(eh, tuple(HORIZONS),
                         "the rebuild's horizons must be S22's OWN grid, base included, or S22 "
                         "reads columns the panel does not carry")
        self.assertEqual(HORIZONS[0], 63, "S22's base horizon moved; the rebuild assumed 63")
        # A DEFECT OF MY OWN, PINNED SO IT CANNOT COME BACK. v2 shipped `HORIZONS[1:]` on the
        # reasoning that 63 duplicates the panel's own `horizon`. It does not duplicate it: it
        # is S22's `C0` control, and `fundamental_panel`'s own comment says so. The arms were
        # unaffected -- `ret_col(63)` returns `fwd_ret` -- so the CONTROL was the only casualty,
        # which is why `test_every_S22_horizon_column_exists` passed while C0 KeyError'd.
        self.assertIn(63, eh,
                      "S22's C0 control reads `fwd_ret_h63` directly to check that the "
                      "extra_horizons machinery reproduces the shipped `fwd_ret`; dropping 63 "
                      "removes the control's input, and copying `fwd_ret` into it would make C0 "
                      "pass BY CONSTRUCTION")

    def test_keep_numbers_is_True_and_the_horizon_is_63(self):
        t = _tree("scripts/corrected_rebuild.py")
        call = None
        for n in ast.walk(t):
            if isinstance(n, ast.Call) and getattr(n.func, "id", None) == \
                    "build_fundamental_panel":
                call = n
        self.assertIsNotNone(call, "no build call")
        kw = {k.arg: k.value for k in call.keywords}
        self.assertIn("keep_numbers", kw)
        self.assertIsInstance(kw["keep_numbers"], ast.Constant)
        self.assertIs(kw["keep_numbers"].value, True)
        self.assertIn("extra_horizons", kw)
        self.assertIsInstance(kw["horizon"], ast.Constant)
        self.assertEqual(kw["horizon"].value, 63)

    def test_rebalance_and_lookback_come_from_CONFIG_and_are_not_retyped(self):
        """`UNIVERSE-BIAS` read both from `CONFIG`; retyping either is a fourth change."""
        t = _tree("scripts/corrected_rebuild.py")
        call = next(n for n in ast.walk(t) if isinstance(n, ast.Call)
                    and getattr(n.func, "id", None) == "build_fundamental_panel")
        kw = {k.arg: ast.dump(k.value) for k in call.keywords}
        for a in ("rebalance_days", "lookback_years"):
            self.assertIn("CONFIG", kw.get(a, ""), "%s is retyped rather than read" % a)

    def test_it_refuses_to_overwrite_its_own_output(self):
        s = _src("scripts/corrected_rebuild.py")
        self.assertIn("REFUSING", s)
        self.assertIn("already exists", s)
        t = ast.parse(s)
        guarded = False
        for n in ast.walk(t):
            if isinstance(n, ast.If) and "already exists" in ast.dump(
                    ast.Module(body=n.body, type_ignores=[])):
                self.assertNotIn("Constant(value=False)", ast.dump(n.test))
                guarded = True
        self.assertTrue(guarded)

    def test_the_banked_panels_are_never_opened_for_writing(self):
        """Read as AST write-mode calls and as the declared output name, not as a banned
        substring — the script legitimately NAMES the banked panels in its own disclosure."""
        c = _consts("scripts/corrected_rebuild.py")
        self.assertEqual(c["OUT_PANEL"], "UNIVERSE_BIAS_PANEL_full_v3.pkl")
        # EVERY banked panel, and the list GROWS as panels land. v2 is itself banked now -- the
        # v2-to-v3 additivity proof reads it -- so the guard that protected the lean panel and
        # S23's must protect v2 too. This test FIRED on the v3 rename, which is the guard
        # working: it pins that the output is the DECLARED name and not a banked one.
        for banked in ("UNIVERSE_BIAS_PANEL_full.pkl", "panel_corrected_69d.pkl",
                       "UNIVERSE_BIAS_PANEL_full_v2.pkl",
                       "UNIVERSE_BIAS_PANEL_restricted.pkl"):
            self.assertNotEqual(c["OUT_PANEL"], banked,
                                "the rebuild would overwrite the banked %s" % banked)
        for n in ast.walk(_tree("scripts/corrected_rebuild.py")):
            if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "to_pickle":
                self.assertTrue(n.args, "to_pickle with no destination")
                self.assertIsInstance(n.args[0], ast.Name,
                                      "the destination must be the resolved `dest` local, never "
                                      "a literal path")


class TheLiveThemeGateRunsBeforeAnythingReadsIt(unittest.TestCase):
    """`UNIVERSE-BIAS` shipped a SIX-theme confounded panel whose `insider` was constant at one
    distinct value at 100% non-null, and its runner reported "themes 7" because it counted
    columns PRESENT. **Coverage is not fidelity.**"""

    def test_it_RAISES_rather_than_writing_a_panel_with_a_dead_weighted_theme(self):
        s = _src("scripts/corrected_rebuild.py")
        self.assertIn("REFUSING TO WRITE", s)
        self.assertIn("coverage is not fidelity", s.lower())
        t = ast.parse(s)
        # the refusal must come BEFORE the write, or a dead-theme panel lands anyway
        order = []
        for n in ast.walk(t):
            if isinstance(n, ast.Raise) and "REFUSING TO WRITE" in ast.dump(n):
                order.append(("raise", n.lineno))
            if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "to_pickle":
                order.append(("write", n.lineno))
        self.assertTrue(any(k == "raise" for k, _ in order))
        self.assertTrue(any(k == "write" for k, _ in order))
        r = min(l for k, l in order if k == "raise")
        w = min(l for k, l in order if k == "write")
        self.assertLess(r, w, "the live-theme refusal is AFTER the write, so a dead-theme panel "
                              "lands before it fires")
        # A MUTATION MISS CLOSED. `if False:` keeps the string AND the line order, so ordering
        # and presence are both satisfied by a guard that can never fire -- MB31's unreachable
        # `DUE` and STAGE1-BATCH1's `if False` refusal, for the third time. The guarding
        # CONDITION is read off the AST and a constant is rejected.
        guarded = False
        for n in ast.walk(t):
            if not isinstance(n, ast.If):
                continue
            if "REFUSING TO WRITE" not in ast.dump(ast.Module(body=n.body, type_ignores=[])):
                continue
            test = ast.dump(n.test)
            self.assertNotIn("Constant(value=False)", test,
                             "the live-theme refusal is guarded by a constant, so a dead-theme "
                             "panel would land")
            self.assertNotIn("Constant(value=True)", test,
                             "a constant-True guard would refuse every build")
            self.assertIn("missing", test,
                          "the refusal must be guarded by the computed missing-theme list")
            guarded = True
        self.assertTrue(guarded, "no `if` guards the live-theme refusal at all")

    def test_the_liveness_rule_is_IMPORTED_from_UNIVERSE_BIAS(self):
        """Two definitions of "is this theme alive" is `B7`'s defect, and one of them would be
        free to count a constant column as present."""
        s = _src("scripts/corrected_rebuild.py")
        self.assertIn("from scripts.universe_bias_arms import", s)
        self.assertIn("live_themes", s)
        self.assertIn("MIN_DISTINCT_PER_THEME", s)


    def test_the_inertness_floor_is_pinned_IN_THE_SOURCE_too(self):
        """A MUTATION MISS CLOSED, and the reason is worth keeping: shrinking `MIN_CELLS` in the
        SCRIPT left the artifact on disk untouched, so an artifact-only check could not see it.
        **An artifact check cannot detect a source mutation unless the artifact is
        regenerated** -- the same shape as `STAGE1-BATCH1`'s inlined verdict rule. So the floor
        is pinned where the mutation lives as well as where its output lands."""
        c = _consts("scripts/corrected_rebuild_inert.py")
        self.assertEqual(c["MIN_CELLS"], 100000,
                         "the inertness floor was lowered in the source; a count gate only means "
                         "something if its floor is fixed (MB21)")


class TheRebuildOnDisk(unittest.TestCase):
    """SKIPS LOUDLY without the panel."""

    @classmethod
    def setUpClass(cls):
        cls.d = _artifact("CORRECTED_REBUILD.json")
        cls.i = _artifact("CORRECTED_REBUILD_INERT.json")
        if cls.d is None:
            _skip("rebuild", "CORRECTED_REBUILD.json absent")

    def test_all_seven_weighted_themes_are_live(self):
        if self.d is None:
            return
        lt = self.d["live_themes"]
        self.assertTrue(lt["weighted_all_live"])
        for t in ("value", "quality", "momentum", "insider", "capital_discipline", "size",
                  "institutional"):
            self.assertIn(t, lt["alive"], "%s is not LIVE on the rebuilt panel" % t)

    def test_every_S22_horizon_column_exists(self):
        if self.d is None:
            return
        from scripts.term_structure import HORIZONS, ret_col
        have = set(self.d["forward_return_columns"])
        for h in HORIZONS:
            self.assertIn(ret_col(h), have, "S22 would read a column the panel lacks: %s"
                          % ret_col(h))
        # AND THE CONTROL'S COLUMN, WHICH `ret_col` DOES NOT NAME. `ret_col(63)` returns
        # `fwd_ret`, so the loop above is satisfied by a panel that has no `fwd_ret_h63` at all
        # -- which is exactly how v2 passed this test while S22's C0 raised KeyError. A guard
        # that covers the measurement path and not the control path is not covering the study.
        self.assertIn("fwd_ret_h63", have,
                      "S22's C0 control reads `fwd_ret_h63` directly and `ret_col` never names "
                      "it, so this is a separate assertion rather than part of the loop")

    def test_the_z_columns_came_back(self):
        """`keep_numbers=True`'s whole purpose: `CORRECTED-FLOORS` part 2 reported four claims
        UNMEASURED for want of them."""
        if self.d is None:
            return
        self.assertGreater(self.d["z_columns"], 40,
                           "keep_numbers=True did not persist the z_ columns")

    def test_the_three_changes_are_ADDITIVE_on_the_real_panels(self):
        """The substantive control: if any shared theme VALUE moved, the successors are reading a
        different object than the one CORRECTED-FLOORS calibrated its floors on."""
        if self.i is None:
            _skip("inertness", "CORRECTED_REBUILD_INERT.json absent")
            return
        self.assertTrue(self.i["additive"], "shared values moved: %s" % self.i["columns_moved"])
        self.assertEqual(self.i["columns_moved"], {})
        self.assertEqual(self.i["removed_columns"], [])
        self.assertTrue(self.i["key_sets_identical"])
        # A MUTATION MISS CLOSED: comparing the artifact against ITS OWN gate is satisfied by
        # shrinking the gate. `MIN_CELLS = 1` passed. The floor is pinned as a LITERAL here, so
        # the comparison is against a fixed number rather than against whatever the script says.
        self.assertEqual(self.i["min_cells_gate"], 100000,
                         "the inertness floor was lowered; a p-free count gate only means "
                         "something if the floor is fixed (MB21)")
        self.assertGreaterEqual(self.i["cells_compared"], 100000,
                                "MB21: a perfect zero over too few cells is not a pass")
        self.assertGreater(self.i["cells_compared"], 1000000,
                           "the real comparison spans ~3.25M cells; anything near the floor "
                           "means the panels barely overlap and the proof is thin")

    def test_all_seven_added_columns_reach_fundamentals_pit_with_no_rebuild(self):
        """Addendum 2's requirement, verified rather than argued: an arm reads these per-name and
        per-date, so the loader change is sufficient and the panel need not be rebuilt."""
        r = _pit_row()
        if not r:
            _skip("pit", "corrected export / AAPL row unavailable")
            return
        for c in ("ncfdiv", "ncfcommon", "capex", "liabilities", "assetsc",
                  "workingcapital", "retearn"):
            self.assertIn(c, r, "%s does not reach fundamentals_pit" % c)
            self.assertIsNotNone(r[c], "%s is present but null on this row" % c)

    def test_the_payout_columns_reach_the_POINT_IN_TIME_row_not_the_panel(self):
        """They produce NO derived panel column, and that is expected: `_KEEP` makes them
        available to the LOADER, and `B5` reads them through `fundamentals_pit`. Recorded so a
        successor does not look for a panel column that was never going to exist."""
        if self.d is None:
            return
        self.assertEqual(self.d["payout_columns_present"], {"ncfdiv": [], "ncfcommon": []},
                         "if a derived column appeared, something consumed them and that is a "
                         "fourth undeclared change")


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=1).result
    if _SKIPS:
        print("\nSKIPPED (data absent) - NOT counted as passes:")
        for s in _SKIPS:
            print("   - " + s)
    sys.exit(0 if r.wasSuccessful() else 1)
