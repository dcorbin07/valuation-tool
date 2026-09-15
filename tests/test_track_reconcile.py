"""PULL BEFORE UPLOAD — and refuse rather than merge two divergent records.

THE SITUATION THIS REPAIRS. `track-row.yml` has committed *"HTTP 422: service refused or
unreachable"* every day for about two weeks: the SERVICE holds recorded history and **no book
file**, so `index_mark` has nothing to mark. The seed attempt was then refused with **409** —
*"an upload may extend the recorded series, never truncate it"* — because the service held 17
rows and the local copy held 6.

**THAT REFUSAL WAS CORRECT AND IS NOT WEAKENED HERE.** There is no `--force`, the check is not
lowered, and an upload still cannot shrink the series. What these tests pin is the missing
other direction: reading the service's record first, and refusing on a *named* row rather than
on a byte prefix.

**WHY THE RECONCILER EXISTS AT ALL, given the door already refuses.** The service enforces a
BYTE PREFIX — the right rule and a terrible diagnostic. A 409 says the upload was refused; it
does not say *which* row disagreed, and "the local file is shorter" and "row 4 has a different
`excess_pp`" are different problems with different fixes.

**AND THE COMPARISON IS STRINGS ON THE BOUND SCHEMA'S OWN COLUMNS**, because the service
returns JSON (`day_n` an int, `excess_pp` a float) while the local file is text. A raw `==`
would report every row as divergent for a reason that is purely transport — which would look
exactly like a corrupted record.

Run: python tests/test_track_reconcile.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from scripts import fetch_track as FT                                    # noqa: E402
from scripts.seed_track import reconcile                                 # noqa: E402

PASSED = FAILED = 0


def check(name, fn):
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print("  ok   %s" % name)
    except Exception as e:                                               # noqa: BLE001
        FAILED += 1
        print("  FAIL %s\n         %s: %s" % (name, type(e).__name__, e))


def _svc(n, start=1):
    """Service rows as the export door returns them — JSON types, not strings."""
    return [{"date": "2026-08-%02d" % (d + 1), "day_n": d, "valquo_pct": 0.5 * d,
             "spy_pct": 0.25 * d, "excess_pp": 0.25 * d, "n_priced": 86}
            for d in range(start, start + n)]


def _local(rows):
    return FT.to_csv(rows)


def test_a_local_series_shorter_than_the_service_is_refused():
    """THE 409 CASE, named rather than inferred: service 17, local 6."""
    svc = _svc(17)
    rec = reconcile(_local(svc[:6]), svc)
    assert rec["ok"] is False, rec
    assert rec["service_extra"] == 11, rec
    assert "truncate" in rec["reason"], rec["reason"]
    assert not rec["disagreements"], "a short file is not a disagreeing file"


def test_a_disagreeing_shared_row_is_refused_and_named():
    """The failure a byte prefix cannot describe."""
    svc = _svc(6)
    local = list(FT.rows_of(_local(svc)))
    local[3]["excess_pp"] = "-9.9999"
    text = FT.to_csv(local)
    rec = reconcile(text, svc)
    assert rec["ok"] is False, rec
    assert len(rec["disagreements"]) == 1, rec["disagreements"]
    d = rec["disagreements"][0]
    assert d["index"] == 3, d
    assert d["columns"] == ["excess_pp"], d
    assert d["local"]["excess_pp"] == "-9.9999" and d["service"]["excess_pp"] != "-9.9999", d


def test_a_genuine_superset_is_allowed():
    """The whole point is that a legitimate EXTENSION still goes through."""
    svc = _svc(6)
    rec = reconcile(_local(svc + _svc(3, start=7)), svc)
    assert rec["ok"] is True, rec
    assert rec["shared"] == 6 and rec["local_extra"] == 3, rec


def test_an_identical_series_is_allowed_and_adds_nothing():
    svc = _svc(6)
    rec = reconcile(_local(svc), svc)
    assert rec["ok"] is True and rec["local_extra"] == 0, rec


def test_json_types_do_not_read_as_a_corrupted_record():
    """`day_n` int vs "5", `excess_pp` float vs "1.25" — transport, not divergence. Without
    this normalisation every row would look wrong and the operator would think the record was
    destroyed."""
    svc = _svc(4)
    rec = reconcile(_local(svc), svc)
    assert rec["ok"] is True, (
        "JSON-vs-text types read as a disagreement: %s" % rec["disagreements"][:2])


def test_order_matters_not_just_membership():
    """Same rows in a different order is a DIFFERENT record, not the same one shuffled."""
    svc = _svc(5)
    shuffled = list(FT.rows_of(_local(svc)))
    shuffled[0], shuffled[1] = shuffled[1], shuffled[0]
    rec = reconcile(FT.to_csv(shuffled), svc)
    assert rec["ok"] is False, "a reordered series was accepted"
    assert rec["disagreements"], rec


def test_the_puller_refuses_to_write_over_the_local_bound_history():
    """The local file is the only evidence of a disagreement; overwriting it in place would
    erase the disagreement rather than resolve it.

    THE FETCH IS STUBBED ON PURPOSE. The first cut let this reach the network, where it
    returned 2 on a DNS failure and `rc != 0` passed WITHOUT the filename guard ever running --
    a test agreeing with itself about a check it never executed.
    """
    import tempfile

    def _run(out):
        real = FT.fetch
        had = os.environ.get("ADMIN_TOKEN")
        FT.fetch = lambda base, token, timeout=120: {"meta": {}, "series": _svc(3)}
        os.environ["ADMIN_TOKEN"] = "test-not-a-real-token"
        try:
            return FT.main(["--url", "https://example.invalid", "--out", out])
        finally:
            FT.fetch = real
            if had is None:
                os.environ.pop("ADMIN_TOKEN", None)
            else:
                os.environ["ADMIN_TOKEN"] = had

    rc = _run(os.path.join("data", "valquo_track_history.csv"))
    assert rc == 3, "writing over the bound history must be refused with 3, got %r" % rc

    # ...and a legitimate destination still writes, so it is a NAMED refusal and not a
    # blanket one that would make the puller useless.
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "valquo_track_service_2026-09-15.csv")
        assert _run(out) == 0
        assert os.path.exists(out) and os.path.getsize(out) > 0


def test_the_csv_render_matches_the_bound_schema_exactly():
    """A file that LOOKS like the record but carries different columns would fail the
    service's byte check for a reason that has nothing to do with the data."""
    from valuation.screener.index_mark import ROW_COLUMNS
    text = FT.to_csv(_svc(2))
    header = text.splitlines()[0]
    assert header == ",".join(ROW_COLUMNS), (header, ROW_COLUMNS)
    assert text.endswith("\r\n"), "the bound file is CRLF; the service's rule is on bytes"


def run():
    global PASSED, FAILED
    print("TRACK PULL / RECONCILE")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            check(name, fn)
    print("\n%d passed, %d failed" % (PASSED, FAILED))
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
