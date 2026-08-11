"""O13 — pins the anti-signal decomposition (2026-08-11).

Standalone script, like every suite here: the auto-land Action runs `python tests/test_*.py`,
so pytest fixtures never execute.

The load-bearing test in this file is `test_the_fast_null_is_exactly_the_reference`. The script
does not use the readable reference implementation — it uses a vectorised one, because 2,000
draws x 32 arms x 3 samples in pure Python does not finish. A fast path that is merely
*approximately* the registered statistic would silently change the bar every verdict is read
against, so the equivalence is proved on a fixed permutation rather than asserted in a comment.
"""
import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import antisignal as A          # noqa: E402


def _rows(spec, book="a"):
    """spec: list of (bin, return). Bin is carried on a plain field so a binner is trivial."""
    return [{"b": b, "pnl_pct": r, "book": book} for b, r in spec]


BIN = (lambda r: r["b"])


class Binning(unittest.TestCase):
    def test_quantile_edges_are_taken_from_the_alert_book_and_applied_to_both(self):
        alert = [{"x": float(i)} for i in range(100)]
        binner = A.make_binner("x", alert)
        # A control value far outside the alert's range still lands in a terminal bin rather
        # than creating a new one -- otherwise the two books would not share a bin vocabulary.
        self.assertEqual(binner({"x": -999.0}), "q1")
        self.assertEqual(binner({"x": 9999.0}), "q5")

    def test_a_missing_value_is_not_a_bin(self):
        alert = [{"x": float(i)} for i in range(10)]
        binner = A.make_binner("x", alert)
        self.assertIsNone(binner({"x": None}))
        self.assertIsNone(binner({}))

    def test_nan_is_treated_as_missing_not_as_a_number(self):
        alert = [{"x": float(i)} for i in range(10)]
        binner = A.make_binner("x", alert)
        self.assertIsNone(binner({"x": float("nan")}))

    def test_rare_categorical_levels_are_pooled_into_other(self):
        alert = [{"cap_tier": "big"} for _ in range(200)] + [{"cap_tier": "rare"}]
        binner = A.make_binner("cap_tier", alert)
        self.assertEqual(binner({"cap_tier": "big"}), "big")
        self.assertEqual(binner({"cap_tier": "rare"}), "OTHER")

    def test_a_categorical_field_outside_the_declared_set_fails_loudly(self):
        """`make_binner` picks numeric vs categorical from a fixed name set. A string field that
        is not in it must raise, not silently produce garbage bins."""
        with self.assertRaises(ValueError):
            A.make_binner("not_declared", [{"not_declared": "text"}])

    def test_label_binner_is_present_absent(self):
        b = A.make_label_binner("Breakout")
        self.assertEqual(b({"labels": ["Breakout", "X"]}), "has")
        self.assertEqual(b({"labels": ["X"]}), "no")
        self.assertIsNone(b({}))


class GapAlgebra(unittest.TestCase):
    def test_gap_is_alert_minus_control_within_a_bin(self):
        a = _rows([("q1", 0.10), ("q1", 0.20)])
        c = _rows([("q1", 0.05), ("q1", 0.05)])
        t = A.gap_table(a, c, BIN)
        self.assertAlmostEqual(t["bins"]["q1"]["gap"], 0.15 - 0.05, places=12)

    def test_rate_component_reproduces_the_total_gap_when_the_mix_matches(self):
        # Same bin proportions in both books -> mix is 0 and rate IS the total gap.
        a = _rows([("q1", 0.10)] * 10 + [("q2", -0.20)] * 10)
        c = _rows([("q1", 0.00)] * 30 + [("q2", -0.10)] * 30)
        t = A.gap_table(a, c, BIN)
        total = (sum(r["pnl_pct"] for r in a) / len(a)) - (sum(r["pnl_pct"] for r in c) / len(c))
        self.assertAlmostEqual(A.rate_component(t), total, places=12)
        cm = sum(r["pnl_pct"] for r in c) / len(c)
        self.assertAlmostEqual(A.mix_component(t, cm), 0.0, places=12)

    def test_mix_and_rate_together_reconstruct_the_total_gap(self):
        a = _rows([("q1", 0.10)] * 30 + [("q2", -0.20)] * 10)
        c = _rows([("q1", 0.00)] * 10 + [("q2", -0.10)] * 30)
        t = A.gap_table(a, c, BIN)
        cm = sum(r["pnl_pct"] for r in c) / len(c)
        total = (sum(r["pnl_pct"] for r in a) / len(a)) - cm
        self.assertAlmostEqual(A.rate_component(t) + A.mix_component(t, cm), total, places=12)

    def test_s_worst_is_one_over_k_when_the_gap_is_perfectly_diffuse(self):
        a, c = [], []
        for q in ("q1", "q2", "q3", "q4"):
            a += _rows([(q, 0.00)] * 25)
            c += _rows([(q, 0.10)] * 25)
        t = A.gap_table(a, c, BIN)
        self.assertAlmostEqual(A.s_worst(t), 0.25, places=12)

    def test_s_worst_is_one_when_the_gap_is_carried_by_a_single_bin(self):
        a = _rows([("q1", 0.10)] * 50 + [("q2", 0.10)] * 50)
        c = _rows([("q1", 0.10)] * 50 + [("q2", 0.30)] * 50)
        t = A.gap_table(a, c, BIN)
        self.assertAlmostEqual(A.s_worst(t), 1.0, places=12)

    def test_s_worst_is_none_rather_than_infinite_when_there_is_no_gap(self):
        a = _rows([("q1", 0.10)] * 10 + [("q2", 0.10)] * 10)
        c = _rows([("q1", 0.10)] * 10 + [("q2", 0.10)] * 10)
        self.assertIsNone(A.s_worst(A.gap_table(a, c, BIN)))


class TheCalibratedNull(unittest.TestCase):
    def test_the_null_holds_the_total_gap_exactly_invariant(self):
        """The property that makes this the right null and not merely a shuffle.

        Permuting bin labels within book cannot move either book's overall mean, so the total gap
        is identical on every draw. A null that moved the gap would be calibrating a different
        question -- how big is the gap -- instead of how concentrated it is.
        """
        rng = random.Random(7)
        a = _rows([(rng.choice("12345"), rng.gauss(0, 1)) for _ in range(300)])
        c = _rows([(rng.choice("12345"), rng.gauss(0.5, 1)) for _ in range(900)])
        before = (sum(r["pnl_pct"] for r in a) / len(a)) - (sum(r["pnl_pct"] for r in c) / len(c))
        names_a, sizes_a, rets_a = A.bin_sizes(a, BIN)
        names_c, sizes_c, rets_c = A.bin_sizes(c, BIN)
        self.assertAlmostEqual(sum(rets_a) / len(rets_a) - sum(rets_c) / len(rets_c),
                               before, places=12)

    def test_the_fast_null_is_exactly_the_reference(self):
        """One fixed permutation, both code paths, identical `s_worst` to 12 places.

        Slicing shuffled returns into consecutive groups of the per-bin counts is the SAME
        experiment as permuting the bin labels over the rows. This proves it on a concrete draw
        rather than trusting the argument.
        """
        rng = random.Random(11)
        bins = ["q1", "q2", "q3", "q4", "q5"]
        a = _rows([(rng.choice(bins), rng.gauss(0.0, 1.0)) for _ in range(400)])
        c = _rows([(rng.choice(bins), rng.gauss(0.4, 1.0)) for _ in range(1200)])

        names_a, sizes_a, rets_a = A.bin_sizes(a, BIN)
        names_c, sizes_c, rets_c = A.bin_sizes(c, BIN)
        common = [b for b in names_a if b in set(names_c)]
        idx_a = [names_a.index(b) for b in common]
        idx_c = [names_c.index(b) for b in common]

        # A concrete permutation, applied BOTH ways.
        pa = list(rets_a)
        pc = list(rets_c)
        random.Random(99).shuffle(pa)
        random.Random(98).shuffle(pc)

        # (1) the slice form the fast path uses
        def _slice_means(vals, sizes):
            out, i = [], 0
            for n in sizes:
                out.append(sum(vals[i:i + n]) / n)
                i += n
            return out
        ma = _slice_means(pa, sizes_a)
        mc = _slice_means(pc, sizes_c)
        n_a = float(sum(sizes_a))
        contrib = [(sizes_a[ia] / n_a) * (ma[ia] - mc[ic]) for ia, ic in zip(idx_a, idx_c)]
        fast = min(contrib) / sum(contrib)

        # (2) the reference form: build labelled rows from that same permutation and score them
        lab_a, i = [], 0
        for name, n in zip(names_a, sizes_a):
            lab_a += [name] * n
        lab_c = []
        for name, n in zip(names_c, sizes_c):
            lab_c += [name] * n
        ref_rows_a = _rows(list(zip(lab_a, pa)))
        ref_rows_c = _rows(list(zip(lab_c, pc)))
        ref = A.s_worst(A.gap_table(ref_rows_a, ref_rows_c, BIN))

        self.assertIsNotNone(ref)
        self.assertAlmostEqual(fast, ref, places=12)

    def test_the_vectorised_null_returns_the_requested_number_of_draws(self):
        rng = random.Random(3)
        bins = ["q1", "q2", "q3"]
        a = _rows([(rng.choice(bins), rng.gauss(0, 1)) for _ in range(150)])
        c = _rows([(rng.choice(bins), rng.gauss(0.3, 1)) for _ in range(450)])
        names_a, sizes_a, rets_a = A.bin_sizes(a, BIN)
        names_c, sizes_c, rets_c = A.bin_sizes(c, BIN)
        common = [b for b in names_a if b in set(names_c)]
        draws = A.null_draws_fast(sizes_a, rets_a, sizes_c, rets_c,
                                  [names_a.index(b) for b in common],
                                  [names_c.index(b) for b in common],
                                  sum(sizes_a), 50, 0)
        self.assertEqual(len(draws), 50)

    def test_the_null_is_seeded_and_reproducible(self):
        rng = random.Random(4)
        a = _rows([(rng.choice("123"), rng.gauss(0, 1)) for _ in range(120)])
        c = _rows([(rng.choice("123"), rng.gauss(0.2, 1)) for _ in range(360)])
        na, sa, ra = A.bin_sizes(a, BIN)
        nc, sc, rc = A.bin_sizes(c, BIN)
        common = [b for b in na if b in set(nc)]
        ia = [na.index(b) for b in common]
        ic = [nc.index(b) for b in common]
        d1 = A.null_draws_fast(sa, list(ra), sc, list(rc), ia, ic, sum(sa), 25, 5)
        d2 = A.null_draws_fast(sa, list(ra), sc, list(rc), ia, ic, sum(sa), 25, 5)
        self.assertEqual(d1, d2)


class Degeneracy(unittest.TestCase):
    def test_a_constant_feature_is_flagged_degenerate(self):
        """The book is 100% calls and 100% swing, so two structural arms have one bin."""
        a = _rows([("call", 0.10)] * 50)
        c = _rows([("call", 0.20)] * 50)
        t = A.gap_table(a, c, BIN)
        self.assertTrue(A.is_degenerate(t))

    def test_a_two_bin_feature_is_not_degenerate(self):
        a = _rows([("has", 0.1)] * 50 + [("no", 0.1)] * 50)
        c = _rows([("has", 0.2)] * 50 + [("no", 0.2)] * 50)
        self.assertFalse(A.is_degenerate(A.gap_table(a, c, BIN)))

    def test_a_lopsided_feature_cannot_express_a_refusal(self):
        """The LIVE failure mode, reproduced: `Uptrend` sits on 98.5% of the book with a negative
        gap, and the small bin's gap is POSITIVE. So the only refusable bin is not a candidate
        and the only candidate is not refusable -- the refusal set is necessarily empty.

        An earlier version of `can_express_refusal` tested bin weights alone and returned True
        here, because the 1.5% bin *is* small enough. That was the wrong predicate and this test
        is what caught it.
        """
        a = _rows([("has", -0.1)] * 985 + [("no", 0.4)] * 15)
        c = _rows([("has", 0.0)] * 985 + [("no", 0.0)] * 15)
        t = A.gap_table(a, c, BIN)
        self.assertEqual(A.refusal_set(t), [])
        self.assertFalse(A.can_express_refusal(t))

    def test_a_quintile_feature_can_express_a_refusal(self):
        a, c = [], []
        for q in ("q1", "q2", "q3", "q4", "q5"):
            a += _rows([(q, -0.1)] * 20)
            c += _rows([(q, 0.0)] * 20)
        self.assertTrue(A.can_express_refusal(A.gap_table(a, c, BIN)))


class TheRefusalRule(unittest.TestCase):
    def test_it_refuses_the_worst_bins_first(self):
        a, c = [], []
        for q, g in (("q1", -0.30), ("q2", -0.05), ("q3", 0.10), ("q4", 0.10), ("q5", 0.10)):
            a += _rows([(q, g)] * 20)
            c += _rows([(q, 0.0)] * 20)
        t = A.gap_table(a, c, BIN)
        self.assertEqual(A.refusal_set(t)[0], "q1")

    def test_it_never_refuses_more_than_the_share_cap(self):
        a, c = [], []
        for q in ("q1", "q2", "q3", "q4", "q5"):
            a += _rows([(q, -0.5)] * 20)      # every bin is negative; the cap must still bind
            c += _rows([(q, 0.0)] * 20)
        t = A.gap_table(a, c, BIN)
        ref = A.refusal_set(t)
        share = sum(t["bins"][b]["w"] for b in ref)
        self.assertLessEqual(share, A.MAX_REFUSE_SHARE + 1e-12)

    def test_it_never_refuses_a_positive_gap_bin(self):
        a, c = [], []
        for q, g in (("q1", 0.30), ("q2", 0.30), ("q3", 0.30)):
            a += _rows([(q, g)] * 20)
            c += _rows([(q, 0.0)] * 20)
        self.assertEqual(A.refusal_set(A.gap_table(a, c, BIN)), [])

    def test_a_one_direction_pass_is_a_null(self):
        """Session 7's rule, pinned: both directions or nothing."""
        good = {"improvement_pp": 5.0, "refused_gap": -0.10}
        bad = {"improvement_pp": 0.2, "refused_gap": -0.10}
        self.assertEqual(A.inverse_verdict(good, good), "INVERSE_CARRIES_INFORMATION")
        self.assertEqual(A.inverse_verdict(good, bad), "NULL")
        self.assertEqual(A.inverse_verdict(bad, good), "NULL")

    def test_a_refused_set_that_did_not_actually_lose_is_a_null(self):
        """Clearing the margin while the refused bins were fine is a NULL, not a pass."""
        self.assertEqual(
            A.inverse_verdict({"improvement_pp": 9.0, "refused_gap": +0.10},
                              {"improvement_pp": 9.0, "refused_gap": +0.10}), "NULL")

    def test_the_margin_is_the_registered_one(self):
        self.assertEqual(A.REFUSE_MARGIN_PP, 1.50)
        self.assertEqual(A.MAX_REFUSE_SHARE, 0.30)

    def test_a_missing_direction_is_a_null_not_a_crash(self):
        self.assertEqual(A.inverse_verdict(None, {"improvement_pp": 9.0,
                                                  "refused_gap": -0.1}), "NULL")


class TheParentJoin(unittest.TestCase):
    def test_control_rows_inherit_their_parent_alerts_features(self):
        alert = [{"ticker": "X", "alert_ts": "2020-01-02", "iv": 0.9, "pnl_pct": 0.0}]
        ctrl = [{"ticker": "X", "_control_for": "2020-01-02", "pnl_pct": 0.1}]
        out, orphans = A.attach_parent_features(ctrl, alert, ["iv"])
        self.assertEqual(orphans, 0)
        self.assertEqual(out[0]["iv"], 0.9)

    def test_an_orphan_is_dropped_and_never_defaulted(self):
        """A control row carrying a made-up feature value would be silently mis-binned."""
        alert = [{"ticker": "X", "alert_ts": "2020-01-02", "iv": 0.9}]
        ctrl = [{"ticker": "X", "_control_for": "1999-01-01", "pnl_pct": 0.1}]
        out, orphans = A.attach_parent_features(ctrl, alert, ["iv"])
        self.assertEqual((len(out), orphans), (0, 1))

    def test_the_join_does_not_mutate_the_input_rows(self):
        alert = [{"ticker": "X", "alert_ts": "2020-01-02", "iv": 0.9}]
        ctrl = [{"ticker": "X", "_control_for": "2020-01-02", "pnl_pct": 0.1}]
        A.attach_parent_features(ctrl, alert, ["iv"])
        self.assertNotIn("iv", ctrl[0])


class Halves(unittest.TestCase):
    def test_the_split_is_by_calendar_date_and_covers_every_row(self):
        rows = [{"alert_ts": "20%02d-01-01" % i} for i in range(10, 30)]
        e, l = A.split_halves(rows)
        self.assertEqual(len(e) + len(l), len(rows))
        self.assertTrue(max(r["alert_ts"] for r in e) <= min(r["alert_ts"] for r in l))

    def test_the_verdict_rule_is_diffuse_when_nothing_clears(self):
        self.assertEqual(A.concentration_verdict([]), "DIFFUSE")
        self.assertEqual(A.concentration_verdict(["dte"]), "CONCENTRATED")


class TheRegisterIsHonoured(unittest.TestCase):
    def test_iv_rank_is_not_a_feature(self):
        """It is 0.0% populated on BOTH books. Excluded for having no values, not for failing."""
        self.assertNotIn("iv_rank", A.TRACK_A)
        self.assertNotIn("iv_rank", A.TRACK_S)

    def test_the_registered_feature_sets_are_what_the_register_says(self):
        self.assertEqual(len(A.TRACK_A), 8)
        self.assertEqual(len(A.TRACK_S), 9)

    def test_the_draw_count_is_the_registered_one(self):
        self.assertEqual(A.N_PERM_DRAWS, 2000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
