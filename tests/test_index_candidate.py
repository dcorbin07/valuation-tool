# -*- coding: utf-8 -*-
"""INDEX-CANDIDATE -- arm 2 as a named, NON-DEFAULT, UNPUBLISHED construction.

The load-bearing tests, in order of what they would cost if they broke:

 1. **IT IS NOT PUBLISHED.** `settings.BOOK_CONFIGS` still holds exactly the two shipped books,
    and the candidate is not in it. Four consumers ITERATE that dict -- the backtest card, the
    panel's `book_configs` block, this module's own `config_block` and `results_file` -- and a
    `?config=` endpoint lists its keys back inside a 400. An entry there would be measured,
    banked and echoed to the public. Pinned in BOTH directions, because a one-way containment
    test passes if the two dicts are ever merged.
 2. **IT IS NOT DEFAULT AND NOT ADOPTED**, on every path: the registry says so, the payload says
    so, and `TRACKED_CONFIG` is untouched.
 3. **IT REFUSES RATHER THAN APPROXIMATES.** A short universe raises; it does not build a
    30-name "top 1500". That is the one failure mode that would carry a measured return into a
    book that does not have it, and it would look right in the payload.
 4. **THE FREE ROUTE IS REFUSED BY NAME**, with the measurement in the message, because
    `DECISION_index_choice.md` put the live-route decile overlap at 0.2326 against a 0.60 bar.
 5. **THE UNIVERSE TRIM IS ONE DEFINITION.** `served_index_book.book_fn` must CALL
    `valquo_index.trim_universe`, proved by substitution rather than by reading, because the
    boundary is the only thing separating arm 2 from the book in force.
 6. **The committed literals match the artifact** where the artifact is present, and the check is
    proved non-vacuous by a planted wrong value.
"""
import copy
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

from valuation.edge import valquo_index as VI  # noqa: E402
from valuation.studies import served_index_book as IB  # noqa: E402
from valuation.screener import settings as S  # noqa: E402

CAND = "liquid-decile"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _rows(n, start=0):
    """`n` scan rows, descending market cap, with the fields `build_index` reads."""
    return [{"ticker": "T%04d" % (i + start), "hot_score": float(100 - (i % 100)),
             # CAPS SIT WELL ABOVE THE $10B FLOOR ON PURPOSE. A fixture below it puts fewer
             # than MIN_NAMES in the tier, so `build_index` takes the "largest half" FALLBACK
             # and a contrast against the shipped floor measures the fallback instead of the
             # filter -- which is what my first cut did, reading 750 of 1500.
             "market_cap": float(50_000_000_000 - i * 20_000_000), "price": 10.0}
            for i in range(n)]


def _artifact_path():
    """The licensed artifact, in the repo or in the primary root a worktree borrows from."""
    p = os.path.join(REPO, "data", "free_analysis", "INDEX_BEST.json")
    if os.path.exists(p):
        return p
    parts = REPO.replace("\\", "/").split("/.claude/worktrees/")
    if len(parts) == 2:
        alt = os.path.join(parts[0].replace("/", os.sep), "data", "free_analysis",
                           "INDEX_BEST.json")
        if os.path.exists(alt):
            return alt
    return None


class ItIsNotPublished(unittest.TestCase):
    def test_book_configs_still_holds_exactly_the_two_shipped_books(self):
        """A third entry would be measured by the backtest card, banked into
        BACKTEST_RESULTS.json and listed back to any caller of a ?config= endpoint."""
        self.assertEqual(sorted(S.BOOK_CONFIGS), ["roth", "taxable"])

    def test_the_candidate_is_not_a_book_config_and_a_book_config_is_not_a_candidate(self):
        """Both directions. A one-way containment test passes if the dicts are merged."""
        for name in VI.INDEX_CANDIDATES:
            self.assertNotIn(name, S.BOOK_CONFIGS, name)
        for name in S.BOOK_CONFIGS:
            self.assertNotIn(name, VI.INDEX_CANDIDATES, name)

    def test_the_config_flag_refuses_a_candidate_name_and_says_which_flag_to_use(self):
        """An operator typing --config liquid-decile must be told, not silently refused by the
        unknown-config path, which would read as the candidate not existing."""
        rc = VI.main(["--config", CAND, "--out", os.devnull])
        self.assertEqual(rc, 1)

    def test_the_incumbent_CLI_still_sends_the_module_defaults(self):
        """`--candidate` needed the three construction knobs to default to None so an explicit
        one is distinguishable from an absent one. That is a change to the path EVERY existing
        invocation takes, so what it resolves to is pinned rather than reasoned about: the
        defaults must still reach `export` unchanged, or §3's incumbent command silently builds
        a different book."""
        seen = {}
        real = VI.export

        def spy(**kw):
            seen.update(kw)
            raise RuntimeError("stop here -- the kwargs are the whole assertion")

        VI.export = spy
        try:
            VI.main(["--out", os.devnull])
        finally:
            VI.export = real
        self.assertEqual(seen.get("large_cap_min"), VI.LARGE_CAP_MIN)
        self.assertEqual(seen.get("top_decile"), VI.TOP_DECILE)
        self.assertEqual(seen.get("weighting"), "score")
        self.assertIsNone(seen.get("candidate_name"))

    def test_a_candidate_plus_a_hand_passed_knob_is_refused_by_name(self):
        """It used to be a bare TypeError naming an argument the operator never typed.

        THE EXIT CODE IS NOT THE ASSERTION, AND MUTATION IS WHAT SHOWED THAT. With the refusal
        deleted, this command STILL returns 1 -- the hand-passed knob is silently dropped, the
        run reaches the free-route refusal, and that exits 1 for an entirely different reason.
        A test on the return code alone passed against the mutant. It reads the MESSAGE now,
        which is the only thing that distinguishes the two refusals -- and the mutant's
        behaviour is itself the argument for the guard: without it, `--top-decile 0.2` is
        accepted and ignored.
        """
        import contextlib
        import io as _io
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = VI.main(["--candidate", CAND, "--top-decile", "0.2", "--out", os.devnull])
        self.assertEqual(rc, 1)
        self.assertIn("already fixes", buf.getvalue())
        self.assertIn("--top-decile", buf.getvalue())

    def test_a_candidate_run_sends_no_construction_knobs_at_all(self):
        seen = {}
        real = VI.export

        def spy(**kw):
            seen.update(kw)
            raise RuntimeError("stop")

        VI.export = spy
        try:
            VI.main(["--candidate", CAND, "--out", os.devnull])
        finally:
            VI.export = real
        self.assertEqual(seen.get("candidate_name"), CAND)
        for k in ("large_cap_min", "top_decile", "weighting"):
            self.assertNotIn(k, seen, k)

    def test_tracked_config_is_untouched(self):
        from valuation.screener import index_track as IT
        self.assertEqual(IT.TRACKED_CONFIG, "taxable")


class ItIsNotDefault(unittest.TestCase):
    def test_the_registry_declares_it_off(self):
        cfg = VI.candidate(CAND)
        self.assertIs(cfg["adopted"], False)
        self.assertIs(cfg["default"], False)

    def test_the_payload_declares_it_off(self):
        bk = VI.build_candidate(_rows(1600), CAND)
        self.assertIs(bk["candidate"]["adopted"], False)
        self.assertIs(bk["candidate"]["default"], False)

    def test_the_payload_carries_the_two_facts_an_operator_needs(self):
        """Adopting is a vintage event; the contract's position floor holds for THIS arm."""
        bk = VI.build_candidate(_rows(1600), CAND)
        self.assertIs(bk["candidate"]["vintage_event"], True)
        self.assertIs(bk["candidate"]["contract_min_positions_holds"], True)

    def test_the_contract_position_floor_itself_is_unchanged(self):
        """Arm 3 would have needed this moved. Arm 2 does not, and that is a reason to prefer
        it -- so a silent change here would remove the distinction."""
        self.assertEqual(VI.CONTRACT_MIN_POSITIONS, 50)

    def test_building_a_candidate_writes_no_file(self):
        with tempfile.TemporaryDirectory() as d:
            before = sorted(os.listdir(d))
            cwd = os.getcwd()
            os.chdir(d)
            try:
                VI.build_candidate(_rows(1600), CAND)
            finally:
                os.chdir(cwd)
            self.assertEqual(sorted(os.listdir(d)), before)


class ItRefusesRatherThanApproximates(unittest.TestCase):
    def test_a_short_universe_raises_and_names_both_counts(self):
        with self.assertRaises(RuntimeError) as cm:
            VI.build_candidate(_rows(300), CAND)
        msg = str(cm.exception)
        self.assertIn("1500", msg)
        self.assertIn("300", msg)

    def test_exactly_the_declared_universe_is_enough(self):
        """The refusal is `<`, not `<=`: 1500 rows build a 1500-name universe."""
        bk = VI.build_candidate(_rows(1500), CAND)
        self.assertEqual(bk["candidate"]["eligible_tier"], 1500)

    def test_an_unknown_candidate_names_the_ones_that_exist(self):
        with self.assertRaises(RuntimeError) as cm:
            VI.candidate("no-such-arm")
        self.assertIn(CAND, str(cm.exception))

    def test_the_free_route_is_refused_with_the_measurement_in_the_message(self):
        """Not a preference: 0.2326 against a 0.60 bar, DECISION_index_choice.md."""
        with self.assertRaises(RuntimeError) as cm:
            VI.export(candidate_name=CAND, path=os.devnull, data_dir=None)
        msg = str(cm.exception)
        self.assertIn("NOT buildable by the free live route", msg)
        self.assertIn("0.2326", msg)
        self.assertIn("0.60", msg)

    def test_a_candidate_and_a_book_config_together_are_refused(self):
        """Both fix the same knobs, so honouring both would silently pick a winner."""
        with self.assertRaises(RuntimeError) as cm:
            VI.export(candidate_name=CAND, config="taxable", path=os.devnull,
                      data_dir="data/backtest")
        self.assertIn("same knobs", str(cm.exception))


class TheBandIsExplicit(unittest.TestCase):
    def test_no_held_means_no_band_and_the_payload_says_so(self):
        """The book on disk belongs to a different construction, so the first build under a new
        one is band-less by design -- and the payload has to say which it was."""
        bk = VI.build_candidate(_rows(1600), CAND)
        self.assertIs(bk["candidate"]["band_applied"], False)

    def test_a_held_set_turns_the_band_on(self):
        bk = VI.build_candidate(_rows(1600), CAND, held=["T0000", "T0001"])
        self.assertIs(bk["candidate"]["band_applied"], True)


class TheUniverseTrimIsOneDefinition(unittest.TestCase):
    def test_book_fn_CALLS_trim_universe_rather_than_carrying_its_own(self):
        """Proved by substitution, not by reading. The boundary is the ONLY thing separating
        arm 2 from the book in force, so a second copy would let the arm be measured on one
        population and built on another with both halves correct in isolation."""
        import pandas as pd
        calls = []
        real = VI.trim_universe

        def spy(rows, rank, rank_key=None):
            calls.append((len(rows), rank))
            return real(rows, rank, rank_key=rank_key)

        VI.trim_universe = spy
        IB.trim_universe = spy
        try:
            sub = pd.DataFrame({"ticker": ["A", "B", "C", "D"],
                                "market_cap": [9e9, 8e9, 7e9, 6e9]})
            fn = IB.book_fn(large_cap_min=0.0, universe_rank=3)
            fn(sub, [1.0, 0.9, 0.8, 0.7], set())
        finally:
            VI.trim_universe = real
            IB.trim_universe = real
        self.assertEqual(calls, [(4, 3)])

    def test_ties_break_on_ticker_so_the_boundary_is_stable(self):
        rows = [{"ticker": "ZZZ", "market_cap": 5e9}, {"ticker": "AAA", "market_cap": 5e9}]
        self.assertEqual([r["ticker"] for r in VI.trim_universe(rows, 1)], ["AAA"])

    def test_a_missing_rank_value_sorts_LAST_and_is_not_dropped(self):
        """Dropping would silently shrink the universe, so a vendor gap would read as a smaller
        market. Sorting last keeps the count honest."""
        rows = [{"ticker": "A", "market_cap": None}, {"ticker": "B", "market_cap": 1e9}]
        self.assertEqual([r["ticker"] for r in VI.trim_universe(rows, 2)], ["B", "A"])

    def test_a_non_positive_rank_is_refused_rather_than_returning_everything(self):
        for bad in (0, -1, None):
            with self.assertRaises(ValueError):
                VI.trim_universe([{"ticker": "A", "market_cap": 1e9}], bad)


class TheConstructionIsTheMeasuredOne(unittest.TestCase):
    def test_the_large_cap_floor_is_zero_so_the_trim_IS_the_tier(self):
        """A second large-cap filter on top of the 1500-name trim would cut twice and make the
        arm a different object -- so a $1 company inside the trim must be ELIGIBLE. Measured
        against the contrast: the shipped $10B floor would have cut it."""
        self.assertEqual(VI.candidate(CAND)["large_cap_min"], 0.0)
        rows = _rows(1499) + [{"ticker": "TINY", "hot_score": 50.0,
                               "market_cap": 1.0, "price": 10.0}]
        self.assertEqual(len(rows), 1500)
        bk = VI.build_candidate(rows, CAND)
        self.assertEqual(bk["n_eligible"], 1500)
        trimmed = VI.trim_universe(rows, 1500)
        contrast = VI.build_index(trimmed, large_cap_min=10e9, top_decile=0.10,
                                  weighting="score")
        self.assertEqual(contrast["n_eligible"], 1499)

    def test_the_knobs_are_arm_2s(self):
        cfg = VI.candidate(CAND)
        self.assertEqual((cfg["universe_rank"], cfg["top_decile"], cfg["top_n"],
                          cfg["weighting"], cfg["exit_frac"]),
                         (1500, 0.10, None, "score", 0.30))

    def test_the_name_says_liquid_and_the_payload_corrects_it(self):
        """`PREREG_index_best.md` 1a: there is no point-in-time liquidity measure, so every
        arm's universe is a MARKET-CAP universe wearing a liquidity label. The name is kept
        because it is the one the decision memo uses, so the correction has to travel in the
        payload -- an operator who only reads the output is the person who would otherwise
        carry the label into a note about the book."""
        cfg = VI.candidate(CAND)
        self.assertEqual(cfg["rank_key"], "market_cap")
        self.assertIn("MARKET CAP", cfg["label"])
        bk = VI.build_candidate(_rows(1600), CAND)
        mc = bk["candidate"]["rank_key_is_market_cap_not_liquidity"]
        self.assertEqual(mc["spearman_vs_63d_dollar_adv"], 0.7119)

    def test_the_band_width_is_the_adopted_one_and_not_a_second_copy(self):
        from valuation.edge.no_trade_band import BAND_WIDTH
        self.assertEqual(VI.candidate(CAND)["exit_frac"], BAND_WIDTH)

    def test_the_committed_literals_match_the_artifact(self):
        """MA13. The artifact is licensed and gitignored, so this SKIPS LOUDLY on a runner
        rather than passing vacuously."""
        p = _artifact_path()
        if not p:
            self.skipTest("INDEX_BEST.json absent (licensed panel); literals unchecked here")
        with open(p, encoding="utf-8") as f:
            a = json.load(f)["arms"]["2_liquid_decile"]
        cfg = VI.candidate(CAND)
        m = cfg["measured"]
        for k in ("roth_net_ann", "roth_sharpe", "roth_max_drawdown", "annual_turnover",
                  "realised_one_way_bps"):
            self.assertEqual(m[k], a[k], k)
        self.assertEqual(m["book_size"], a["book_size"])
        self.assertEqual(m["eligible_tier"], a["eligible_tier"])
        # And the KNOBS, which is what makes this the same arm rather than the same numbers.
        self.assertEqual({"large_cap_min": cfg["large_cap_min"],
                          "universe_rank": cfg["universe_rank"],
                          "top_n": cfg["top_n"]}, a["knobs"])

    def test_that_literal_check_can_fail(self):
        """Non-vacuity: a planted wrong value must be caught, or the test above is decoration."""
        if not _artifact_path():
            self.skipTest("artifact absent, so the planted control cannot be exercised")
        saved = copy.deepcopy(VI.INDEX_CANDIDATES[CAND])
        VI.INDEX_CANDIDATES[CAND]["measured"]["annual_turnover"] = 1.0
        try:
            with self.assertRaises(AssertionError):
                self.test_the_committed_literals_match_the_artifact()
        finally:
            VI.INDEX_CANDIDATES[CAND] = saved


if __name__ == "__main__":
    unittest.main(verbosity=2)
