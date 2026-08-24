"""PT-SPMO — SPMO as a REPORTED second benchmark beside the contract-bound SPY track.

The contract binds SPY and only SPY. Everything here is written against the ways a SECOND
benchmark corrupts a first one, rather than against the arithmetic, because the arithmetic is
one division and the containment is the whole risk:

  * THE BOUND FILE IS BYTE-COMPARED ACROSS EVERY SIBLING OPERATION
    (`test_no_sibling_operation_changes_one_byte_of_the_bound_file`). Not "the same rows" —
    the same BYTES, because the append-only guarantee `.github/workflows/track-row.yml`
    verifies is a byte-prefix property and a value-level check cannot see a header widening
    or a re-serialisation.
  * THE VALQUO LEG IS COPIED, NOT RE-DERIVED
    (`test_the_backfill_reproduces_the_bound_valquo_leg_byte_for_byte`). Two files showing two
    different Valquo numbers is a failure this project has already shipped once, from two
    different books. The sibling copies the RAW CELL TEXT so the two legs cannot drift by a
    rounding, and the test compares strings rather than floats for exactly that reason.
  * THE METER, THE GATE AND THE VERDICT STAY SPY-ONLY
    (`test_the_contract_machinery_never_reads_the_reported_benchmark`), asserted on the SOURCE
    of every module that computes one, because a runtime check only sees the paths a test
    happens to exercise.
  * REFUSALS MIRROR THE MAIN DOOR AND RETURN NO NUMBER
    (`test_no_refusal_path_ever_leaks_a_number`, `test_the_sibling_inherits_the_bound_doors_
    append_only_refusals`). A reported benchmark that fills its own gaps with a guess is worse
    than no reported benchmark.
  * THE BANNED CHECK RUNS ON THE RENDERED PAYLOAD AND HAS BOTH CONTROLS
    (`test_the_rendered_payload_carries_no_banned_phrase`, `..._is_not_vacuous`,
    `..._does_not_forbid_the_honest_sentence`). A guard with no positive control passes by
    seeing nothing; a guard with no negative control gets deleted the first week it fires on
    honest copy.

Prices are injected everywhere, so the whole module runs offline against fixed numbers — the
same discipline `test_index_mark.py` states. The one test naming REAL closes
(`test_it_reproduces_the_recorded_spy_leg_on_the_two_dates_index_mark_documents`) pins the
convention against values `index_mark`'s own docstring recorded independently.

Run: python tests/test_reported_benchmark.py
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.screener import index_mark              # noqa: E402
from valuation.screener import index_track             # noqa: E402
from valuation.screener import reported_benchmark as rb  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCEPTION = "2026-07-30"

#: The bound series exactly as it is recorded, including the ragged precision of the
#: hand-written rows — `0.776` and `4.25` are what is actually on disk, and a copy that
#: normalised them to `0.7760` and `4.2500` would already have re-derived the leg.
BOUND_CSV = (
    "date,day_n,valquo_pct,spy_pct,excess_pp,n_priced\r\n"
    "2026-07-31,1,0.4126,0.6903,-0.2777,86\r\n"
    "2026-08-06,5,0.776,3.6228,-2.8468,86\r\n"
    "2026-08-13,10,4.25,4.88,-0.62,86\r\n"
    "2026-08-17,12,6.9705,4.1769,2.7936,86\r\n"
)

#: A deterministic SPMO tape covering inception and every recorded date. The closes are the
#: real ones read on 2026-08-20, so the arithmetic the tests pin is the arithmetic that ran.
SPMO_TAPE = {
    "SPMO": {"2026-07-30": 143.4199981689453, "2026-07-31": 143.8300018310547,
             "2026-08-06": 149.10000610351562, "2026-08-13": 152.72000122070312,
             "2026-08-17": 155.16000366210938},
    "SPY": {"2026-07-30": 741.6900024414062, "2026-07-31": 747.030029296875,
            "2026-08-06": 768.5599975585938, "2026-08-13": 777.8800048828125,
            "2026-08-17": 772.6699829101562},
}


def _tape(mapping: dict):
    import pandas as pd

    def fetch(ticker, days=400):
        series = mapping.get(ticker.upper())
        if series is None:
            return None
        return pd.DataFrame({"Date": list(series.keys()), "Close": list(series.values())})
    return fetch


def _bound(tmpdir, csv_text: str = None, inception: str = INCEPTION):
    """Write a book and a bound history into `tmpdir`; return (meta_path, history_path)."""
    meta = os.path.join(tmpdir, "valquo_track.json")
    with open(meta, "w", encoding="utf-8") as f:
        json.dump({"inception_date": inception, "benchmark": "SPY",
                   "positions": [{"ticker": "AAA", "weight": 1.0}]}, f)
    hist = os.path.join(tmpdir, "valquo_track_history.csv")
    with open(hist, "wb") as f:
        f.write((csv_text if csv_text is not None else BOUND_CSV).encode("utf-8"))
    return meta, hist


def _bound_cells(csv_text: str, column: str) -> list:
    """The raw cell TEXT of one column, without going through any float."""
    lines = [l for l in csv_text.replace("\r\n", "\n").split("\n") if l.strip()]
    head = lines[0].split(",")
    i = head.index(column)
    return [l.split(",")[i] for l in lines[1:]]


# =======================================================================================
# CONTAINMENT — the bound file, byte for byte
# =======================================================================================
def test_no_sibling_operation_changes_one_byte_of_the_bound_file():
    """THE REQUIRED PIN. Backfill, append, refuse — the bound file is identical throughout.

    Bytes rather than rows. A value-level comparison passes through a header widening, a
    re-quoted cell and a line-ending change, and every one of those breaks the byte-prefix
    rule the landing Action checks with `cmp`.
    """
    with tempfile.TemporaryDirectory() as d:
        meta, hist = _bound(d)
        before = open(hist, "rb").read()

        out = rb.backfill(fetch=_tape(SPMO_TAPE), meta_path=meta, bound_history_path=hist)
        assert out["ok"], out.get("reason")
        assert open(hist, "rb").read() == before, "the backfill modified the bound file"

        rec = rb.record({"date": "2026-08-18", "day_n": 13, "valquo_pct": 7.5},
                        INCEPTION, fetch=_tape(SPMO_TAPE), bound_history_path=hist)
        assert open(hist, "rb").read() == before, "an append modified the bound file"

        # And a refusal path, which is where a half-written file would show up.
        rb.record({"date": "2026-08-19", "day_n": 14, "valquo_pct": 7.5},
                  INCEPTION, fetch=_tape({"SPMO": {}}), bound_history_path=hist)
        assert open(hist, "rb").read() == before, "a refusal modified the bound file"
        assert rec is not None


def test_the_bound_file_never_gains_a_column():
    """The contract-bound header is exactly what it was. Stated separately from the byte
    compare above because this is the failure mode the hard rule NAMES, and a reader looking
    for it should find a test with its name on it."""
    with tempfile.TemporaryDirectory() as d:
        meta, hist = _bound(d)
        rb.backfill(fetch=_tape(SPMO_TAPE), meta_path=meta, bound_history_path=hist)
        header = open(hist, encoding="utf-8").read().splitlines()[0]
        assert header == "date,day_n,valquo_pct,spy_pct,excess_pp,n_priced", header
        assert "spmo" not in header.lower(), header


def test_the_sibling_lands_beside_its_own_bound_file_and_not_in_the_real_data_dir():
    """A sibling that resolved to the repo's real `data/` while its bound partner was a
    fixture is how a test suite writes into the one file that cannot be re-derived."""
    with tempfile.TemporaryDirectory() as d:
        _, hist = _bound(d)
        p = rb.sibling_path(hist)
        assert os.path.dirname(os.path.abspath(p)) == os.path.abspath(d), p
        assert os.path.basename(p) == rb.SIBLING_FILENAME, p


# =======================================================================================
# THE VALQUO LEG — copied, never re-derived
# =======================================================================================
def test_the_backfill_reproduces_the_bound_valquo_leg_byte_for_byte():
    """Every sibling row's `valquo_pct` is the bound file's cell TEXT, unchanged.

    Strings, not floats. `0.776` and `4.25` are on disk with the precision a human typed;
    a copy that round-tripped them through `float` and back would write `0.776` and `4.25`
    today and could write `0.7760` tomorrow under a different formatter, and the two files
    would then disagree in the bytes while agreeing in the numbers.
    """
    with tempfile.TemporaryDirectory() as d:
        meta, hist = _bound(d)
        out = rb.backfill(fetch=_tape(SPMO_TAPE), meta_path=meta, bound_history_path=hist)
        assert out["ok"], out.get("reason")

        want = _bound_cells(BOUND_CSV, "valquo_pct")
        got = _bound_cells(open(out["path"], encoding="utf-8").read(), "valquo_pct")
        assert got == want, (got, want)


def test_every_backfilled_row_declares_where_its_valquo_leg_came_from():
    with tempfile.TemporaryDirectory() as d:
        meta, hist = _bound(d)
        out = rb.backfill(fetch=_tape(SPMO_TAPE), meta_path=meta, bound_history_path=hist)
        srcs = set(_bound_cells(open(out["path"], encoding="utf-8").read(), "valquo_src"))
        assert srcs == {rb.SRC_RECORDED}, srcs


def test_nothing_in_the_module_recomputes_the_valquo_leg():
    """SOURCE-LEVEL, because a runtime test only sees the paths it exercises.

    The book's return is a weighted sum over positions. If this module ever grew one it would
    be re-deriving the leg it promises to copy — the two-numbers failure — so the syntax tree
    is asked whether anything here reads a position weight at all.
    """
    src = open(os.path.join(ROOT, "valuation", "screener", "reported_benchmark.py"),
               encoding="utf-8").read()
    tree = ast.parse(src)
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and node.value in ("weight", "positions", "valquo_pct_recomputed"):
            hits.append(node.value)
        if isinstance(node, ast.Attribute) and node.attr in ("build_frame", "run_scan"):
            hits.append(node.attr)
    assert not hits, ("this module reached for the book itself (%s); the Valquo leg is "
                      "COPIED from the bound row and must never be rebuilt here" % sorted(set(hits)))


def test_the_live_path_copies_the_row_the_bound_door_settled_on():
    """On an idempotent second POST the bound door returns the row ALREADY ON DISK, which can
    differ from the freshly computed one. The sibling must follow the file, not the
    computation, or the two series show two Valquo numbers for one day."""
    with tempfile.TemporaryDirectory() as d:
        _, hist = _bound(d)
        settled = {"date": "2026-08-17", "day_n": 12, "valquo_pct": "6.9705"}
        out = rb.row_for(settled, INCEPTION, fetch=_tape(SPMO_TAPE))
        assert out["ok"], out.get("reason")
        assert out["row"]["valquo_pct"] == "6.9705", out["row"]
        assert hist


# =======================================================================================
# SPY-ONLY — the meter, the gate and the verdict
# =======================================================================================
def test_the_contract_machinery_never_reads_the_reported_benchmark():
    """SOURCE-LEVEL over every module that computes a meter, a gate or a verdict.

    Named individually rather than swept, so adding a new one is a deliberate act: a sweep
    over a directory would quietly start covering modules nobody meant it to and quietly stop
    covering a renamed one.
    """
    watched = [
        os.path.join("valuation", "edge", "track_meter.py"),
        os.path.join("valuation", "edge", "shadow_vintage.py"),
        os.path.join("valuation", "screener", "index_track.py"),
        os.path.join("valuation", "screener", "index_mark.py"),
    ]
    bad = []
    for rel in watched:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        tree = ast.parse(open(p, encoding="utf-8").read())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "")] + [a.name for a in node.names]
            if any("reported_benchmark" in (n or "") for n in names):
                bad.append(rel)
    assert not bad, ("the contract machinery imports the reported benchmark: %s. The meter, "
                     "the gate and the 2031 verdict attach to SPY only." % sorted(set(bad)))


def test_the_meter_payload_carries_no_reported_benchmark_figure():
    """Runtime companion to the source check above: whatever the meter says today, no SPMO
    figure is inside it."""
    from valuation.edge import track_meter
    blob = json.dumps(track_meter.detail(), default=str).lower()
    assert "spmo" not in blob, "the contract meter's payload mentions the reported benchmark"


def test_the_vs_spy_claim_is_untouched_by_the_sibling():
    """`index_track.vs_spy_claim` is the ONE authority for a vs-SPY figure. Building the
    sibling must not move it by a digit."""
    with tempfile.TemporaryDirectory() as d:
        meta, hist = _bound(d)
        before = index_track.vs_spy_claim(meta_path=meta, history_path=hist)
        rb.backfill(fetch=_tape(SPMO_TAPE), meta_path=meta, bound_history_path=hist)
        after = index_track.vs_spy_claim(meta_path=meta, history_path=hist)
        assert before == after, (before, after)
        assert after.get("benchmark") == "SPY", after


# =======================================================================================
# REFUSALS — mirroring the main door
# =======================================================================================
def test_no_refusal_path_ever_leaks_a_number():
    """Every refusal returns `row: None`. A mechanism that fills a gap with its best guess is
    worse than no mechanism, because the gap is then invisible."""
    cases = [
        ("SPMO unpriceable at inception",
         rb.row_for({"date": "2026-08-06", "valquo_pct": 1.0}, INCEPTION,
                    fetch=_tape({"SPMO": {"2026-08-06": 100.0}}))),
        ("SPMO unpriceable at the mark date",
         rb.row_for({"date": "2026-08-06", "valquo_pct": 1.0}, INCEPTION,
                    fetch=_tape({"SPMO": {INCEPTION: 100.0}}))),
        ("no readable inception",
         rb.row_for({"date": "2026-08-06", "valquo_pct": 1.0}, "not-a-date",
                    fetch=_tape(SPMO_TAPE))),
        ("no readable bound date",
         rb.row_for({"date": "", "valquo_pct": 1.0}, INCEPTION, fetch=_tape(SPMO_TAPE))),
        ("no readable valquo leg",
         rb.row_for({"date": "2026-08-06", "valquo_pct": ""}, INCEPTION,
                    fetch=_tape(SPMO_TAPE))),
    ]
    for label, res in cases:
        assert res["ok"] is False, (label, res)
        assert res["row"] is None, (label, res)
        assert res["reason"], label


def test_an_unpriceable_day_is_skipped_and_listed_rather_than_estimated():
    """A gap stays a gap and is NAMED. Interpolating a missing benchmark close produces a
    perfectly plausible file with an invented number in it."""
    tape = dict(SPMO_TAPE)
    tape["SPMO"] = {k: v for k, v in SPMO_TAPE["SPMO"].items() if k != "2026-08-13"}
    with tempfile.TemporaryDirectory() as d:
        meta, hist = _bound(d)
        out = rb.backfill(fetch=_tape(tape), meta_path=meta, bound_history_path=hist)
        assert out["ok"], out.get("reason")
        assert [s["date"] for s in out["skipped"]] == ["2026-08-13"], out["skipped"]
        dates = [r["date"] for r in out["rows"]]
        assert "2026-08-13" not in dates, dates
        assert len(dates) == 3, dates


def test_the_sibling_inherits_the_bound_doors_append_only_refusals():
    """The same three refusals, because it is the same function — not a second one that
    resembles it."""
    with tempfile.TemporaryDirectory() as d:
        meta, hist = _bound(d)
        rb.backfill(fetch=_tape(SPMO_TAPE), meta_path=meta, bound_history_path=hist)

        # (a) a repeated date is an idempotent NO-OP that returns what is on disk
        again = rb.record({"date": "2026-08-17", "day_n": 12, "valquo_pct": 999.0},
                          INCEPTION, fetch=_tape(SPMO_TAPE), bound_history_path=hist)
        ap = again["append"]
        assert ap["ok"] and ap["wrote"] is False and ap["already_present"], ap
        assert ap["existing"]["valquo_pct"] == 6.9705, ap["existing"]

        # (b) a backwards date is REFUSED — an unattended writer cannot rewrite history.
        # It must be a day the reported benchmark CAN price, or the refusal would come from
        # this module's own price check instead and prove nothing about the inherited rule:
        # `row_for` runs first, so an unpriceable backwards day is refused for the wrong
        # reason. Both refuse; only one of them is the rule under test.
        priceable = {"SPMO": dict(SPMO_TAPE["SPMO"], **{"2026-08-14": 153.0})}
        back = rb.record({"date": "2026-08-14", "day_n": 11, "valquo_pct": 2.0},
                         INCEPTION, fetch=_tape(priceable), bound_history_path=hist)
        assert back["ok"] is False, back
        assert "append" in back, ("the append-only rule never ran — this refusal came from "
                                  "somewhere else: %r" % back.get("reason"))
        assert back["append"]["would_modify"] is True, back["append"]

        # (c) a forwards date is accepted, so (b) is a refusal and not a broken path
        tape = {"SPMO": dict(SPMO_TAPE["SPMO"], **{"2026-08-18": 156.0})}
        fwd = rb.record({"date": "2026-08-18", "day_n": 13, "valquo_pct": 7.0},
                        INCEPTION, fetch=_tape(tape), bound_history_path=hist)
        assert fwd["ok"] and fwd["append"]["wrote"], fwd


def test_the_append_only_write_preserves_the_siblings_own_byte_prefix():
    """The property the bound series' landing Action verifies with `cmp`, held for the
    sibling too — which is the whole reason `append_row` was parameterised rather than
    copied."""
    with tempfile.TemporaryDirectory() as d:
        meta, hist = _bound(d)
        rb.backfill(fetch=_tape(SPMO_TAPE), meta_path=meta, bound_history_path=hist)
        p = rb.sibling_path(hist)
        before = open(p, "rb").read()
        tape = {"SPMO": dict(SPMO_TAPE["SPMO"], **{"2026-08-18": 156.0})}
        rb.record({"date": "2026-08-18", "day_n": 13, "valquo_pct": 7.0}, INCEPTION,
                  fetch=_tape(tape), bound_history_path=hist)
        after = open(p, "rb").read()
        assert after.startswith(before), "the append did not preserve the previous bytes"
        assert len(after) > len(before)


# =======================================================================================
# THE ARITHMETIC — pinned against numbers measured elsewhere
# =======================================================================================
def test_the_reported_excess_is_valquo_minus_spmo_and_not_the_bound_excess():
    """The two `excess_pp` columns share a NAME and are different quantities. A sibling that
    accidentally carried the bound excess would look completely normal."""
    with tempfile.TemporaryDirectory() as d:
        meta, hist = _bound(d)
        out = rb.backfill(fetch=_tape(SPMO_TAPE), meta_path=meta, bound_history_path=hist,
                          write=False)
        by_date = {r["date"]: r for r in out["rows"]}
        r = by_date["2026-08-17"]
        # SPMO 143.4199981689453 -> 155.16000366210938 = +8.1858%; 6.9705 - 8.1858 = -1.2153
        assert abs(r["spmo_pct"] - 8.1858) < 5e-4, r
        assert abs(r["excess_pp"] - (-1.2153)) < 5e-4, r
        # and it is NOT the bound file's +2.7936
        assert abs(r["excess_pp"] - 2.7936) > 1.0, r


def test_it_reproduces_the_recorded_spy_leg_on_the_two_dates_index_mark_documents():
    """A CONVENTION CONTROL, and the strongest one available offline.

    The sibling's SPMO leg is `close(mark)/close(inception) - 1`. Run that same arithmetic on
    SPY over the same tape and it must reproduce the RECORDED `spy_pct` on the two dates
    `index_mark`'s docstring independently reports as exact (2026-08-06 -> 3.6228). If the
    convention were wrong — a daily return, a wrong base date — this would miss by percent
    rather than by a rounding, and the SPMO leg would be wrong in exactly the same way with
    nothing to compare it against.
    """
    spy = SPMO_TAPE["SPY"]
    got = (spy["2026-08-06"] / spy[INCEPTION] - 1.0) * 100.0
    assert abs(round(got, 4) - 3.6228) < 1e-9, got
    got2 = (spy["2026-08-17"] / spy[INCEPTION] - 1.0) * 100.0
    assert abs(round(got2, 4) - 4.1769) < 1e-9, got2


def test_the_parameterised_append_row_is_inert_on_the_bound_default():
    """`columns` was added to `index_mark.append_row` for this item. The default path must be
    bit-identical, or PT-SPMO silently re-specified the contract-bound writer."""
    with tempfile.TemporaryDirectory() as d:
        row = {"date": "2026-08-18", "day_n": 13, "valquo_pct": 1.0, "spy_pct": 2.0,
               "excess_pp": -1.0, "n_priced": 86}
        a = os.path.join(d, "a.csv")
        b = os.path.join(d, "b.csv")
        index_mark.append_row(row, a)
        index_mark.append_row(row, b, columns=index_mark.ROW_COLUMNS)
        assert open(a, "rb").read() == open(b, "rb").read()
        assert open(a, encoding="utf-8").read().splitlines()[0] == ",".join(
            index_mark.ROW_COLUMNS)


# =======================================================================================
# THE RENDERED PAYLOAD — label, posture, banned phrases
# =======================================================================================
def _rendered(tmpdir) -> tuple:
    """(claim, the text a surface would render from it)."""
    meta, hist = _bound(tmpdir)
    rb.backfill(fetch=_tape(SPMO_TAPE), meta_path=meta, bound_history_path=hist)
    c = rb.claim(bound_history_path=hist)
    text = " ".join(str(v) for v in c.values() if isinstance(v, str))
    return c, text


def test_the_rendered_payload_carries_no_banned_phrase():
    with tempfile.TemporaryDirectory() as d:
        c, text = _rendered(d)
        assert c["available"], c
        assert rb.violations(text) == [], rb.violations(text)


def test_the_banned_check_is_not_vacuous():
    """POSITIVE CONTROL. The check above passes by finding nothing, which is exactly what a
    broken matcher returns."""
    planted = "The Valquo Index will outperform SPMO and this record proves it."
    hits = rb.violations(planted)
    assert "will outperform" in hits, hits
    assert "proves" in hits, hits


def test_the_banned_check_does_not_forbid_the_honest_sentence():
    """NEGATIVE CONTROL. A guard that fires on the copy it is meant to permit gets switched
    off within the week — this repository has written that down about five separate guards,
    and the SPMO block's own label contains the word 'contract' and its why-sentence contains
    a t-statistic, both of which a careless tuple would have caught."""
    honest = " ".join([rb.LABEL, rb.WHY, rb.POSTURE,
                       "Twelve recorded trading days. SPMO has outrun SPY over this stretch, "
                       "so the reported excess is below the bound one on three of four rows.",
                       "This settles nothing and is not a forecast."])
    assert rb.violations(honest) == [], rb.violations(honest)


def test_the_label_and_the_posture_reach_the_payload_rather_than_the_template():
    """A surface that worded its own caveat is exactly where 'not bound by the contract'
    would quietly soften. The strings come from the module."""
    with tempfile.TemporaryDirectory() as d:
        c, _ = _rendered(d)
        assert c["label"] == rb.LABEL
        assert c["posture"] == rb.POSTURE
        assert c["why"] == rb.WHY
        assert c["bound"] is False
        assert "not bound by the contract" in c["label"].lower()


def test_the_index_tab_renders_the_label_beside_the_figure():
    """The template/JS must not print the excess without the label. Asserted on the SHIPPED
    render source, where the two either travel together or they do not."""
    js = open(os.path.join(ROOT, "valuation", "web", "static", "app.js"),
              encoding="utf-8").read()
    i = js.find("const rbRows")
    assert i > 0, "the reported-benchmark block is not in the index-track render"
    block = js[i:i + 900]
    assert "rb.excess_pp" in block, block[:200]
    assert "rb.label" in block, "the excess renders without its label"
    assert "rb.posture" in block, "the excess renders without its posture"


def test_a_surface_with_no_recorded_comparison_prints_no_claim():
    with tempfile.TemporaryDirectory() as d:
        _, hist = _bound(d)
        c = rb.claim(bound_history_path=hist)     # sibling never built
        assert c["available"] is False, c
        assert c["reason"], c
        for k in ("valquo_pct", "spmo_pct", "excess_pp"):
            assert c[k] is None, (k, c[k])


def test_the_api_payload_exposes_the_block_without_breaking_the_bound_card():
    """`/api/index-track` gains one additive key. Asserted on the SOURCE so it is checked even
    where the route needs a store the test does not have."""
    src = open(os.path.join(ROOT, "valuation", "web", "app.py"), encoding="utf-8").read()
    i = src.find("def api_index_track")
    assert i > 0
    body = src[i:i + 3000]
    assert 'out["reported_benchmark"]' in body, "the payload does not carry the block"
    assert "except Exception" in body.split('out["reported_benchmark"]')[1][:400], \
        "a reported benchmark can break the bound card"


def test_the_derivation_note_is_written_beside_the_sibling():
    with tempfile.TemporaryDirectory() as d:
        meta, hist = _bound(d)
        out = rb.backfill(fetch=_tape(SPMO_TAPE), meta_path=meta, bound_history_path=hist)
        note = out.get("note_path")
        assert note and os.path.exists(note), out
        text = open(note, encoding="utf-8").read()
        assert "never re-derived here" in text, text[:400]
        assert "not bound" in text.lower(), text[:400]


def test_no_test_in_this_file_is_shadowed_by_a_duplicate_name():
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    names = re.findall(r"^def (test_\w+)", src, re.M)
    dupes = sorted({n for n in names if names.count(n) > 1})
    assert not dupes, ", ".join(dupes)
    live = [k for k in globals() if k.startswith("test_") and callable(globals()[k])]
    assert len(live) == len(names), (len(names), len(live))


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t(); print("  PASS  " + t.__name__); passed += 1
        except AssertionError as e:
            print("  FAIL  " + t.__name__ + ": " + str(e))
        except Exception as e:
            print("  ERROR " + t.__name__ + ": " + type(e).__name__ + ": " + str(e))
    print("\n" + str(passed) + "/" + str(len(tests)) + " PT-SPMO reported-benchmark tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
