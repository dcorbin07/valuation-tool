"""LA2 — the track backup must protect the CONTRACT-BOUND Index, not just the sandbox engine.

`valuation/edge/track_export.py` shipped with no test suite of any kind, which is part of how
LA2 survived: every committed backup carried `ingested_index_days: 0` while faithfully
preserving four days of a book the contract does not bind, and nothing anywhere asserted
otherwise. The defect was invisible because the job was green.

The tests here are written against the FAILURE, not against the feature:

  * a source that is legitimately empty must never be able to erase a source that is not
    (`test_an_empty_payload_cannot_erase_the_committed_bound_series`) — this is the exact
    shape of the LA2 incident and the one that would cost the record;
  * the guard must COUNT the bound file (`test_the_guard_counts_the_bound_series...`), because
    the old guard counted the sandbox and would have passed a run that dropped every bound row;
  * the emitted README must not call the sandbox file "Valquo Index vs SPY"
    (`test_the_readme_does_not_label_the_sandbox_file_the_valquo_index`) — that exact mislabel
    put a false "Index beating SPY" claim into Discord on 2026-08-05;
  * the backup must actually RESTORE (`test_the_bound_csv_restores_through_index_track_load`).
    A backup nobody has restored is a hypothesis.

Run: python tests/test_track_export.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import track_export as T          # noqa: E402
from valuation.screener import index_track            # noqa: E402


# The two rows the bound recorder actually holds, used verbatim so a test failure is legible
# against the real record rather than against invented numbers.
_REAL_ROWS = [
    {"date": "2026-07-31", "valquo_pct": 0.4126, "spy_pct": 0.6903,
     "excess_pp": -0.2777, "n_priced": 86.0},
    {"date": "2026-08-06", "valquo_pct": 0.776, "spy_pct": 3.6228,
     "excess_pp": -2.8468, "n_priced": 86.0},
]


def _payload(bound_rows=None, sandbox_days=2, **kw):
    """A payload shaped like the live endpoint's, with the parts these tests vary."""
    pay = {
        "schema_version": T.SCHEMA_VERSION,
        "generated_at": "2026-08-10T00:00:00",
        "index_series": [{"as_of": f"2026-08-0{i + 3}", "index_ret": 0.01 * i,
                          "bench_ret": 0.02, "active_ret": -0.01, "n_positions": 10,
                          "n_priced": 10, "inception": "2026-08-03"}
                         for i in range(sandbox_days)],
        "index_holdings": [], "paper_orders": [], "option_alerts": [],
        "tables_present": {}, "counts": {},
    }
    if bound_rows is not None:
        pay["bound_index_track"] = {"meta": {"inception_date": "2026-07-30",
                                             "benchmark": "SPY"},
                                    "series": bound_rows, "sources": {}}
    pay.update(kw)
    return pay


def _seed_committed(d, rows=_REAL_ROWS):
    """Put a previously-committed bound backup in place, as the repo would have."""
    T._write_csv(os.path.join(d, T.BOUND_INDEX_CSV), T._BOUND_COLS, rows)


# --------------------------------------------------------------------------------------- #
# The incident itself.
# --------------------------------------------------------------------------------------- #

def test_an_empty_payload_cannot_erase_the_committed_bound_series():
    """THE LA2 REGRESSION TEST. A live service holding zero bound rows is a NORMAL state — a
    fresh Render disk, or a store that never ingested the tracker, which is exactly what was
    true every week this ran. Rendering that payload must not overwrite the committed record
    with nothing."""
    with tempfile.TemporaryDirectory() as d:
        _seed_committed(d)
        T.write(_payload(bound_rows=[]), d)
        kept = T.read_bound_csv(os.path.join(d, T.BOUND_INDEX_CSV))
        assert len(kept) == 2, f"the committed bound series was destroyed: {kept}"
        assert kept[1]["excess_pp"] == -2.8468, kept[1]


def test_a_payload_from_an_older_service_cannot_erase_it_either():
    """The deployed service predates this change, so its payload has NO `bound_index_track`
    key at all — a different code path from an empty one, and the one that will actually run
    on the next scheduled backup."""
    with tempfile.TemporaryDirectory() as d:
        _seed_committed(d)
        pay = _payload()                       # no bound_index_track key whatsoever
        assert "bound_index_track" not in pay
        T.write(pay, d)
        assert len(T.read_bound_csv(os.path.join(d, T.BOUND_INDEX_CSV))) == 2


def test_the_guard_counts_the_bound_series_and_would_have_caught_la2():
    """The old guard counted `paper_track_index.csv` — the SANDBOX book. Reproduce the LA2
    state exactly (sandbox rows present, bound rows zero) and assert the guard now sees it."""
    with tempfile.TemporaryDirectory() as d:
        T.write(_payload(bound_rows=[], sandbox_days=4), d, merge_committed=False)
        c = T.guard_counts(d)
        assert c["sandbox_index_days"] == 4, c        # the old guard was happy here
        assert c["bound_index_days"] == 0, c          # and this is what it never looked at


def test_the_guard_fails_the_run_when_bound_rows_regress():
    """End-to-end through main(): a fresh export with fewer bound rows than the committed one
    must exit non-zero rather than commit the loss."""
    with tempfile.TemporaryDirectory() as old, tempfile.TemporaryDirectory() as new:
        _seed_committed(old)                          # committed: 2 bound rows
        with open(os.path.join(new, "payload.json"), "w", encoding="utf-8") as f:
            json.dump({"export": _payload(bound_rows=[])}, f)
        rc = T.main(["--from-json", os.path.join(new, "payload.json"), "--out", new,
                     "--no-merge-committed", "--guard-against", old])
        assert rc == 1, "a bound-series regression did not fail the run"


def test_the_guard_passes_when_nothing_regressed():
    """The control for the test above — otherwise it could pass by always failing."""
    with tempfile.TemporaryDirectory() as old, tempfile.TemporaryDirectory() as new:
        _seed_committed(old)
        _seed_committed(new)
        with open(os.path.join(new, "payload.json"), "w", encoding="utf-8") as f:
            json.dump({"export": _payload(bound_rows=_REAL_ROWS)}, f)
        rc = T.main(["--from-json", os.path.join(new, "payload.json"), "--out", new,
                     "--guard-against", old])
        assert rc == 0, "an export that lost nothing was rejected"


# --------------------------------------------------------------------------------------- #
# Merge semantics — the property the safety rests on.
# --------------------------------------------------------------------------------------- #

def test_merge_never_drops_a_date_and_later_sources_win_a_shared_one():
    rows = T.merge_bound_rows(
        [{"date": "2026-07-31", "valquo_pct": 0.1}, {"date": "2026-08-06", "valquo_pct": 9.9}],
        [{"date": "2026-08-06", "valquo_pct": 0.776}, {"date": "2026-08-07", "valquo_pct": 1.0}])
    assert [r["date"] for r in rows] == ["2026-07-31", "2026-08-06", "2026-08-07"]
    assert rows[1]["valquo_pct"] == 0.776, "the later source did not win a shared date"
    assert rows[0]["valquo_pct"] == 0.1, "a date only the earlier source had was dropped"


def test_merge_is_sorted_by_date_regardless_of_input_order():
    rows = T.merge_bound_rows([{"date": "2026-08-06"}, {"date": "2026-07-31"}])
    assert [r["date"] for r in rows] == ["2026-07-31", "2026-08-06"]


def test_merge_ignores_rows_with_no_date():
    """A dateless row cannot be placed in a time series; silently keying it on "" would put a
    phantom first row ahead of inception."""
    rows = T.merge_bound_rows([{"date": "", "valquo_pct": 1.0}, {"valquo_pct": 2.0},
                               {"date": "2026-07-31"}])
    assert [r["date"] for r in rows] == ["2026-07-31"]


def test_a_corrupt_committed_backup_raises_rather_than_reading_as_zero_rows():
    """The whole LA2 failure mode is "unreadable" quietly becoming "empty". A missing file is
    genuinely empty and returns []; a file that exists but cannot be parsed must stop the run,
    because merging [] would then discard the record it failed to read."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, T.BOUND_INDEX_CSV)
        assert T.read_bound_csv(p) == [], "a missing backup should be zero rows, not an error"
        with open(p, "wb") as f:
            f.write(b"date,valquo_pct\n\xff\xfe\x00 not utf-8 at all\n")
        try:
            T.read_bound_csv(p)
        except Exception:
            return
        raise AssertionError("a corrupt committed backup was read as if it were empty")


# --------------------------------------------------------------------------------------- #
# The label. This is the half of LA2 that reached a human.
# --------------------------------------------------------------------------------------- #

def test_the_readme_does_not_label_the_sandbox_file_the_valquo_index():
    with tempfile.TemporaryDirectory() as d:
        T.write(_payload(bound_rows=_REAL_ROWS), d)
        readme = open(os.path.join(d, "README.md"), encoding="utf-8").read()
        for line in readme.splitlines():
            if "`paper_track_index.csv`" in line and line.strip().startswith("|"):
                assert "Valquo Index vs SPY" not in line, \
                    f"the sandbox file is still labelled the Index: {line}"
                assert "SANDBOX" in line.upper(), \
                    f"the sandbox file's row does not say it is the sandbox: {line}"
                break
        else:
            raise AssertionError("no table row for paper_track_index.csv in the README")


def test_the_readme_names_the_bound_file_as_the_contract_bound_one():
    with tempfile.TemporaryDirectory() as d:
        T.write(_payload(bound_rows=_REAL_ROWS), d)
        readme = open(os.path.join(d, "README.md"), encoding="utf-8").read()
        assert T.BOUND_INDEX_CSV in readme
        assert "PAPER_TRACK_CONTRACT.md" in readme
        # The distinguishing fact, in the file a restorer reads first.
        #
        # CORRECTED 2026-08-11 (cold audit LA11). This asserted `"8%" in readme and "10%" in
        # readme`, with the message "the README does not state the weight caps that tell the
        # two books apart". The weight caps are exactly what does NOT tell them apart —
        # session 16 (`PT-SPLIT`) established that `cap = max(MAX_WEIGHT, 1/len(picks))` is
        # deliberate and the sandbox's weights were correct for its book. So this test was
        # pinning the retracted diagnosis INTO the emitted artifact: it would have failed had
        # the README been fixed and left alone. It now pins what actually separates them, the
        # book SIZE, which is the ground the conclusion really rests on.
        assert "86" in readme and "10 names" in readme, \
            "the README does not state the book sizes, which are what tell the two books apart"


def test_the_two_books_are_written_as_separate_files():
    """They are different objects — 86 names score-weighted vs 10 names equal-weighted. If a
    refactor ever aliased them, every claim made from either would be suspect."""
    with tempfile.TemporaryDirectory() as d:
        T.write(_payload(bound_rows=_REAL_ROWS, sandbox_days=4), d)
        bound = T.read_bound_csv(os.path.join(d, T.BOUND_INDEX_CSV))
        assert len(bound) == 2 and T._csv_rows(os.path.join(d, "paper_track_index.csv")) == 4


# --------------------------------------------------------------------------------------- #
# Does the backup actually restore?
# --------------------------------------------------------------------------------------- #

def test_the_bound_csv_restores_through_index_track_load():
    """THE POINT OF THE WHOLE FILE. Write the backup, copy it back to the tracker's own paths
    exactly as the README instructs, and read it with the LIVE loader — no transformation.
    A backup that has never been restored is a hypothesis."""
    with tempfile.TemporaryDirectory() as d:
        T.write(_payload(bound_rows=_REAL_ROWS), d)
        restored = index_track.load(os.path.join(d, T.BOUND_INDEX_META),
                                    os.path.join(d, T.BOUND_INDEX_CSV))
        assert len(restored["series"]) == 2, restored
        assert restored["series"][1]["date"] == "2026-08-06"
        assert abs(restored["series"][1]["excess"] - (-2.8468)) < 1e-9
        assert restored["meta"].get("inception_date") == "2026-07-30"


def test_a_restored_backup_reproduces_the_published_vs_spy_claim():
    """Stronger than a row count: the ONE authority for a vs-SPY statement must produce the
    same -2.8468pp from the restored copy that it produces from the live tracker."""
    with tempfile.TemporaryDirectory() as d:
        T.write(_payload(bound_rows=_REAL_ROWS), d)
        claim = index_track.vs_spy_claim(
            "inception", meta_path=os.path.join(d, T.BOUND_INDEX_META),
            history_path=os.path.join(d, T.BOUND_INDEX_CSV))
        assert claim["available"] is True, claim.get("reason")
        assert abs(claim["excess_pp"] - (-2.8468)) < 1e-9, claim
        assert claim["excess_pp"] < 0, "the restored record must still show the track BEHIND SPY"


def test_the_bound_csv_uses_the_trackers_own_column_names():
    """So restoring is `cp`, not a transformation written at 2am against a lost original."""
    with tempfile.TemporaryDirectory() as d:
        T.write(_payload(bound_rows=_REAL_ROWS), d)
        with open(os.path.join(d, T.BOUND_INDEX_CSV), encoding="utf-8", newline="") as f:
            header = next(csv.reader(f))
        assert header == ["date", "valquo_pct", "spy_pct", "excess_pp", "n_priced"], header


# --------------------------------------------------------------------------------------- #
# Properties the existing backup already promised and nothing checked.
# --------------------------------------------------------------------------------------- #

def test_the_export_is_idempotent_byte_for_byte():
    """Claimed in the module docstring since it was written, never tested. If it is false the
    weekly job commits churn, and churn is how a real change stops being noticed."""
    with tempfile.TemporaryDirectory() as d:
        pay = _payload(bound_rows=_REAL_ROWS)
        T.write(pay, d)
        first = {n: open(os.path.join(d, n), "rb").read() for n in os.listdir(d)}
        T.write(pay, d)
        for n, b in first.items():
            assert open(os.path.join(d, n), "rb").read() == b, f"{n} is not byte-stable"


def test_the_json_and_the_csv_agree_about_the_bound_series():
    """They are written from the same merged list; a future edit that merges after the dump
    would silently ship two different answers in one commit."""
    with tempfile.TemporaryDirectory() as d:
        _seed_committed(d)
        T.write(_payload(bound_rows=[{"date": "2026-08-07", "valquo_pct": 1.0,
                                      "spy_pct": 1.0, "excess_pp": 0.0, "n_priced": 86}]), d)
        js = json.load(open(os.path.join(d, "paper_track_history.json"), encoding="utf-8"))
        csv_rows = T.read_bound_csv(os.path.join(d, T.BOUND_INDEX_CSV))
        assert len(js["bound_index_track"]["series"]) == len(csv_rows) == 3
        assert js["counts"]["bound_index_days"] == 3


def test_the_meta_file_says_which_book_it_is():
    with tempfile.TemporaryDirectory() as d:
        T.write(_payload(bound_rows=_REAL_ROWS), d)
        meta = json.load(open(os.path.join(d, T.BOUND_INDEX_META), encoding="utf-8"))
        assert meta.get("inception_date") == "2026-07-30"
        assert "sandbox" in meta["what_this_is"].lower()


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} LA2 track-export tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
