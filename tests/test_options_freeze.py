"""Pins for the option-chain freeze and the replay pin (audit O16 follow-on).

A separate file rather than an addition to tests/test_edge.py, for the same reason
tests/test_term_slope_decomp.py is separate: parallel lanes edit that file and it is not
union-merged, so a new suite cannot conflict with another lane's work.

The properties pinned here are the ones whose failure would be SILENT in production: a
fingerprint that does not notice a rewrite, a sidecar cache that serves a stale hash after the
file moves, a content digest that cannot tell a re-pickle from a data change, and a replay pin
that fails open.
"""
import datetime as dt
import gzip
import os
import pickle
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from valuation.edge import options_freeze as FZ  # noqa: E402
from valuation.edge import theta_bulk as TB  # noqa: E402


def _frame(bids=(1.0, 2.0, 3.0)):
    n = len(bids)
    return pd.DataFrame({
        "expiration": [dt.date(2020, 3, 20)] * n,
        "strike": [100.0 + i for i in range(n)],
        "right": ["C"] * n,
        "date": [dt.date(2020, 1, 2)] * n,
        "bid": list(bids),
        "ask": [b + 0.1 for b in bids],
        "volume": [10] * n,
        "open_interest": [100] * n,
    })


class FreezeTestBase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="freeze_test_")
        os.makedirs(os.path.join(self.root, "AAPL"), exist_ok=True)
        self.p = TB.year_path("AAPL", 2020, self.root)
        self._write(self.p, _frame())
        self.addCleanup(shutil.rmtree, self.root, True)
        self.addCleanup(TB.set_replay_pin, None)

    @staticmethod
    def _write(path, df):
        with open(path, "wb") as f:
            pickle.dump(df, f, protocol=4)


class TheFingerprintNoticesWhatItMustNotice(FreezeTestBase):

    def test_the_hash_is_stable_across_repeated_reads(self):
        a = FZ.file_sha256(self.p)
        b = FZ.file_sha256(self.p)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)

    def test_a_missing_file_hashes_to_none_rather_than_raising(self):
        self.assertIsNone(FZ.file_sha256(os.path.join(self.root, "nope.pkl")))

    def test_the_sidecar_cache_is_written_and_reused(self):
        FZ.file_sha256(self.p)
        self.assertTrue(os.path.exists(self.p + ".sha256"))
        with open(self.p + ".sha256", encoding="utf-8") as f:
            self.assertIn("|", f.read())

    def test_the_sidecar_is_invalidated_when_the_file_size_changes(self):
        """The cache key is (size, mtime_ns), so a size change always invalidates it.

        NOTE THE NARROWED CLAIM. This test used to assert that ANY rewrite invalidates the
        sidecar, using a same-shape frame — and it was passing only because the mtime happened
        to tick between the two writes. Under load it failed, which is how the false-negative
        mode below was found. The general claim was simply untrue; this is the part that holds.
        """
        before = FZ.file_sha256(self.p)
        self._write(self.p, _frame(bids=(9.0, 9.0, 9.0, 9.0)))       # 4 rows, not 3
        self.assertNotEqual(FZ.file_sha256(self.p), before)

    def test_the_uncached_path_agrees_with_the_cached_one(self):
        self.assertEqual(FZ.file_sha256(self.p, use_cache=False),
                         FZ.file_sha256(self.p, use_cache=True))

    def test_a_same_size_rewrite_that_keeps_its_mtime_defeats_the_cache(self):
        """THE CACHE HAS A REAL FALSE-NEGATIVE MODE, and it is pinned here rather than hidden.

        The sidecar key is (size, mtime_ns). A rewrite of identical size landing inside the
        filesystem's timestamp granularity collides with its own entry and the STALE hash is
        served. Reproduced deterministically with os.utime. This is why every blocking path
        (the replay pin, verify_stamp) passes use_cache=False.
        """
        st = os.stat(self.p)
        cached_before = FZ.file_sha256(self.p, use_cache=True)
        self._write(self.p, _frame(bids=(4.0, 5.0, 6.0)))          # same shape => same size
        os.utime(self.p, ns=(st.st_atime_ns, st.st_mtime_ns))      # and same mtime
        self.assertEqual(os.stat(self.p).st_size, st.st_size)      # precondition of the trap

        self.assertEqual(FZ.file_sha256(self.p, use_cache=True), cached_before)   # WRONG
        self.assertNotEqual(FZ.file_sha256(self.p, use_cache=False), cached_before)  # right

    def test_the_replay_pin_catches_a_rewrite_the_cache_would_miss(self):
        """The consequence of the above, at the level that matters: the gate must still fire."""
        st = os.stat(self.p)
        stamp = FZ.stamp_years([("AAPL", 2020)], root=self.root)
        self._write(self.p, _frame(bids=(4.0, 5.0, 6.0)))
        os.utime(self.p, ns=(st.st_atime_ns, st.st_mtime_ns))
        with FZ.replay_pin(stamp, root=self.root):
            with self.assertRaises(FZ.ChainDrift):
                TB.ThetaBulk(api_key="", root=self.root).chain_on("AAPL", dt.date(2020, 1, 2))


class TheContentDigestSeparatesARepickleFromADataChange(FreezeTestBase):

    def test_row_order_does_not_change_the_content_digest(self):
        a = FZ.content_digest(self.p)
        df = _frame()
        self._write(self.p, df.iloc[::-1].reset_index(drop=True))
        self.assertEqual(FZ.content_digest(self.p), a)

    def test_a_repickle_changes_the_bytes_but_not_the_content(self):
        byte_a, cont_a = FZ.file_sha256(self.p), FZ.content_digest(self.p)
        df = _frame()
        with open(self.p, "wb") as f:            # a DIFFERENT pickle protocol, same rows
            pickle.dump(df, f, protocol=5)
        self.assertNotEqual(FZ.file_sha256(self.p), byte_a)
        self.assertEqual(FZ.content_digest(self.p), cont_a)

    def test_changed_rows_change_the_content_digest(self):
        cont_a = FZ.content_digest(self.p)
        self._write(self.p, _frame(bids=(1.0, 2.0, 3.5)))
        self.assertNotEqual(FZ.content_digest(self.p), cont_a)

    def test_an_extra_column_does_not_change_the_digest_of_the_kept_ones(self):
        cont_a = FZ.content_digest(self.p)
        df = _frame()
        df["nonsense"] = 1
        self._write(self.p, df)
        self.assertEqual(FZ.content_digest(self.p), cont_a)


class TheStampRecordsAbsenceAsAFact(FreezeTestBase):

    def test_a_present_year_is_stamped_with_its_hash(self):
        st = FZ.stamp_years([("AAPL", 2020)], root=self.root)
        self.assertTrue(st["AAPL-2020"]["present"])
        self.assertEqual(st["AAPL-2020"]["sha256"], FZ.file_sha256(self.p))

    def test_an_absent_year_is_recorded_not_omitted(self):
        """'We read nothing here' and 'we forgot to record this' must not look the same."""
        st = FZ.stamp_years([("AAPL", 2020), ("MSFT", 1999)], root=self.root)
        self.assertIn("MSFT-1999", st)
        self.assertFalse(st["MSFT-1999"]["present"])
        self.assertIsNone(st["MSFT-1999"]["sha256"])

    def test_the_stamp_is_deduplicated_and_case_normalised(self):
        st = FZ.stamp_years([("aapl", 2020), ("AAPL", 2020)], root=self.root)
        self.assertEqual(list(st), ["AAPL-2020"])


class TheVerificationBucketsAreCorrect(FreezeTestBase):

    def test_an_untouched_store_verifies_clean(self):
        st = FZ.stamp_years([("AAPL", 2020)], root=self.root)
        v = FZ.verify_stamp(st, root=self.root)
        self.assertEqual(v["ok"], ["AAPL-2020"])
        self.assertTrue(v["clean"])
        self.assertEqual(v["frac_ok"], 1.0)

    def test_changed_rows_are_reported_as_changed(self):
        st = FZ.deepen_stamp(FZ.stamp_years([("AAPL", 2020)], root=self.root), root=self.root)
        self._write(self.p, _frame(bids=(1.0, 2.0, 99.0)))
        v = FZ.verify_stamp(st, root=self.root)
        self.assertEqual(v["changed"], ["AAPL-2020"])
        self.assertFalse(v["clean"])

    def test_a_repickle_is_reported_as_benign_not_as_drift(self):
        """A stamp that cries wolf on a harmless re-pickle trains the reader to ignore it."""
        st = FZ.deepen_stamp(FZ.stamp_years([("AAPL", 2020)], root=self.root), root=self.root)
        with open(self.p, "wb") as f:
            pickle.dump(_frame(), f, protocol=5)
        v = FZ.verify_stamp(st, root=self.root)
        self.assertEqual(v["repickled"], ["AAPL-2020"])
        self.assertEqual(v["changed"], [])
        self.assertTrue(v["clean"])

    def test_without_a_banked_content_digest_the_verdict_is_undecided_not_guessed(self):
        st = FZ.stamp_years([("AAPL", 2020)], root=self.root)     # NOT deepened
        with open(self.p, "wb") as f:
            pickle.dump(_frame(), f, protocol=5)
        v = FZ.verify_stamp(st, root=self.root)
        self.assertEqual(v["changed_or_repickled"], ["AAPL-2020"])
        self.assertEqual(v["changed"], [])
        self.assertEqual(v["repickled"], [])
        self.assertFalse(v["clean"])

    def test_a_deleted_year_is_missing_and_a_new_one_is_appeared(self):
        st = FZ.stamp_years([("AAPL", 2020), ("MSFT", 2020)], root=self.root)
        os.remove(self.p)
        os.makedirs(os.path.join(self.root, "MSFT"), exist_ok=True)
        self._write(TB.year_path("MSFT", 2020, self.root), _frame())
        v = FZ.verify_stamp(st, root=self.root)
        self.assertEqual(v["missing"], ["AAPL-2020"])
        self.assertEqual(v["appeared"], ["MSFT-2020"])

    def test_shallow_verification_does_not_promote_a_mismatch_to_changed(self):
        st = FZ.deepen_stamp(FZ.stamp_years([("AAPL", 2020)], root=self.root), root=self.root)
        with open(self.p, "wb") as f:
            pickle.dump(_frame(), f, protocol=5)
        v = FZ.verify_stamp(st, root=self.root, deep=False)
        self.assertEqual(v["changed_or_repickled"], ["AAPL-2020"])
        self.assertEqual(v["changed"], [])


class TheReplayPinBlocksOnlyWhatItShould(FreezeTestBase):

    def _bulk(self):
        return TB.ThetaBulk(api_key="", root=self.root)

    def test_unpinned_is_the_default_and_reads_are_served(self):
        self.assertIsNone(getattr(TB, "_REPLAY_PIN", None))
        self.assertEqual(len(self._bulk().chain_on("AAPL", dt.date(2020, 1, 2))), 3)

    def test_a_clean_store_replays_inside_the_pin(self):
        st = FZ.stamp_years([("AAPL", 2020)], root=self.root)
        with FZ.replay_pin(st, root=self.root):
            self.assertEqual(len(self._bulk().chain_on("AAPL", dt.date(2020, 1, 2))), 3)

    def test_a_drifted_store_raises_instead_of_serving_the_wrong_rows(self):
        st = FZ.stamp_years([("AAPL", 2020)], root=self.root)
        self._write(self.p, _frame(bids=(5.0, 5.0, 5.0)))
        with FZ.replay_pin(st, root=self.root):
            with self.assertRaises(FZ.ChainDrift):
                self._bulk().chain_on("AAPL", dt.date(2020, 1, 2))

    def test_a_symbol_year_absent_from_the_stamp_is_not_a_violation(self):
        """Absent from the pin means this replay never read it -- not that it drifted."""
        os.makedirs(os.path.join(self.root, "MSFT"), exist_ok=True)
        self._write(TB.year_path("MSFT", 2020, self.root), _frame())
        st = FZ.stamp_years([("AAPL", 2020)], root=self.root)
        with FZ.replay_pin(st, root=self.root):
            self.assertEqual(len(self._bulk().chain_on("MSFT", dt.date(2020, 1, 2))), 3)

    def test_the_pin_is_removed_even_if_the_body_raises(self):
        st = FZ.stamp_years([("AAPL", 2020)], root=self.root)
        try:
            with FZ.replay_pin(st, root=self.root):
                raise ValueError("boom")
        except ValueError:
            pass
        self.assertIsNone(getattr(TB, "_REPLAY_PIN", None))

    def test_the_drift_error_names_the_symbol_year(self):
        st = FZ.stamp_years([("AAPL", 2020)], root=self.root)
        self._write(self.p, _frame(bids=(7.0, 7.0, 7.0)))
        with FZ.replay_pin(st, root=self.root):
            with self.assertRaises(FZ.ChainDrift) as cm:
                self._bulk().chain_on("AAPL", dt.date(2020, 1, 2))
        self.assertIn("AAPL", str(cm.exception))
        self.assertIn("2020", str(cm.exception))

    def test_the_drifted_year_is_not_left_in_the_memory_cache(self):
        """Validating after the unpickle would leave the wrong rows memoised for the process."""
        st = FZ.stamp_years([("AAPL", 2020)], root=self.root)
        # A DIFFERENT ROW COUNT, so the file size changes too. The earlier version of this test
        # used a same-shape frame and passed only by luck: with the cache consulted on the
        # blocking path it depended on the mtime ticking between writes. That flake was a real
        # bug and is now pinned directly by the two cache-collision tests above.
        self._write(self.p, _frame(bids=(3.0, 3.0, 3.0, 3.0, 3.0)))
        b = self._bulk()
        with FZ.replay_pin(st, root=self.root):
            with self.assertRaises(FZ.ChainDrift):
                b.chain_on("AAPL", dt.date(2020, 1, 2))
        self.assertNotIn(("AAPL", 2020), b._mem)


class TheFrozenCopyIsABankedArtifact(FreezeTestBase):

    def _rows(self):
        return [{"ticker": "AAPL", "alert_ts": "2020-01-02", "expiry": "2020-03-20",
                 "strike": 100.0, "opt_right": "C"}]

    def test_consumed_pairs_spans_alert_year_through_expiry_year(self):
        rows = [{"ticker": "AAPL", "alert_ts": "2019-12-30", "expiry": "2021-01-15",
                 "strike": 1.0, "opt_right": "C"}]
        self.assertEqual(FZ.consumed_pairs(rows),
                         {("AAPL", 2019), ("AAPL", 2020), ("AAPL", 2021)})

    def test_the_freeze_round_trips(self):
        out = os.path.join(self.root, "frozen.pkl.gz")
        res = FZ.freeze_book(self._rows(), out, root=self.root)
        self.assertGreater(res["rows"], 0)
        df = FZ.load_frozen(out)
        self.assertIn("symbol", df.columns)
        self.assertEqual(set(df["symbol"]), {"AAPL"})

    def test_it_refuses_to_overwrite_a_freeze_unless_asked(self):
        out = os.path.join(self.root, "frozen.pkl.gz")
        FZ.freeze_book(self._rows(), out, root=self.root)
        with self.assertRaises(FileExistsError):
            FZ.freeze_book(self._rows(), out, root=self.root)
        FZ.freeze_book(self._rows(), out, root=self.root, overwrite=True)   # deliberate

    def test_a_manifest_round_trips(self):
        p = os.path.join(self.root, "MAN.json")
        st = FZ.stamp_years([("AAPL", 2020)], root=self.root)
        FZ.write_manifest(p, "test_book.pkl", st)
        man = FZ.read_manifest(p)
        self.assertEqual(man["book"], "test_book.pkl")
        self.assertEqual(man["n_symbol_years"], 1)
        self.assertIn("AAPL-2020", man["stamp"])

    def test_reading_a_missing_manifest_returns_none_rather_than_raising(self):
        self.assertIsNone(FZ.read_manifest(os.path.join(self.root, "nope.json")))


class TheFrozenCopyIsTheContentRecord(FreezeTestBase):
    """`verify_against_frozen` asks the PRECISE question -- are the rows this book consumed
    still identical -- which a whole-year digest cannot answer without false positives."""

    def setUp(self):
        super().setUp()
        self.rows = [{"ticker": "AAPL", "alert_ts": "2020-01-02", "expiry": "2020-03-20",
                      "strike": 100.0, "opt_right": "C"}]
        self.frozen = os.path.join(self.root, "frozen.pkl.gz")
        FZ.freeze_book(self.rows, self.frozen, root=self.root)

    def test_an_untouched_store_matches_the_frozen_copy_exactly(self):
        v = FZ.verify_against_frozen(self.frozen, self.rows, root=self.root)
        self.assertTrue(v["ok"])
        self.assertEqual(v["frac_rows_identical"], 1.0)
        self.assertEqual(v["differing"], 0)

    def test_changed_consumed_rows_are_detected(self):
        self._write(self.p, _frame(bids=(1.0, 2.0, 42.0)))
        v = FZ.verify_against_frozen(self.frozen, self.rows, root=self.root)
        self.assertEqual(v["differing"], 1)
        self.assertLess(v["frac_rows_identical"], 1.0)

    def test_a_repickle_of_the_same_rows_still_matches(self):
        with open(self.p, "wb") as f:
            pickle.dump(_frame(), f, protocol=5)
        v = FZ.verify_against_frozen(self.frozen, self.rows, root=self.root)
        self.assertEqual(v["frac_rows_identical"], 1.0)

    def test_rows_added_on_dates_the_book_never_read_do_not_count_as_drift(self):
        """The whole reason the bank does not deepen: a re-mine that touches OTHER dates is
        not a change to THIS book's inputs, and must not be reported as one."""
        df = _frame()
        extra = _frame(bids=(50.0, 60.0, 70.0))
        extra["date"] = [dt.date(2020, 6, 15)] * len(extra)
        self._write(self.p, pd.concat([df, extra]).reset_index(drop=True))
        v = FZ.verify_against_frozen(self.frozen, self.rows, root=self.root)
        self.assertEqual(v["frac_rows_identical"], 1.0)
        self.assertEqual(v["differing"], 0)

    def test_a_deleted_year_is_reported_absent_not_identical(self):
        os.remove(self.p)
        v = FZ.verify_against_frozen(self.frozen, self.rows, root=self.root)
        self.assertEqual(v["absent"], 1)


class TheRunnerStampIsNeverAllowedToSinkAFinishedRun(FreezeTestBase):
    """`stamp_run` executes AFTER the scoring is banked. If it can raise, it can destroy a
    completed run, and then it gets switched off -- which is how the store came to move under
    the book in the first place."""

    def _rows(self):
        return [{"ticker": "AAPL", "alert_ts": "2020-01-02", "expiry": "2020-03-20",
                 "strike": 100.0, "opt_right": "C"}]

    def test_it_writes_a_chain_stamp_beside_the_book(self):
        p = FZ.stamp_run(self.root, "state.pkl", self._rows(), quiet=True)
        self.assertTrue(os.path.exists(p))
        man = FZ.read_manifest(p)
        self.assertIn("AAPL-2020", man["stamp"])
        self.assertEqual(man["n_trades"], 1)

    def test_a_dict_of_arms_is_flattened_like_the_entry_lab_banks_it(self):
        p = FZ.stamp_run(self.root, "state.pkl",
                         {"armA": self._rows(), "armB": self._rows()}, quiet=True)
        self.assertEqual(FZ.read_manifest(p)["n_trades"], 2)

    def test_a_missing_output_directory_is_created_rather_than_failing(self):
        p = FZ.stamp_run(os.path.join(self.root, "no", "such", "dir"), "s.pkl",
                         self._rows(), quiet=True)
        self.assertIsNotNone(p)
        self.assertTrue(os.path.exists(p))

    def test_an_internal_failure_returns_none_instead_of_propagating(self):
        """The property that matters: a stamping bug must not take a banked run down with it."""
        orig = FZ.stamp_years
        FZ.stamp_years = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            self.assertIsNone(FZ.stamp_run(self.root, "s.pkl", self._rows(), quiet=True))
        finally:
            FZ.stamp_years = orig

    def test_rows_with_junk_dates_do_not_raise(self):
        rows = [{"ticker": "AAPL", "alert_ts": "not-a-date", "expiry": None,
                 "strike": 1.0, "opt_right": "C"}]
        p = FZ.stamp_run(self.root, "state.pkl", rows, quiet=True)
        self.assertIsNotNone(p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
