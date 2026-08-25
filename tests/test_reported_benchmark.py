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
    """`/api/index-track` gains additive keys, and every one of them is inside a handler.

    Asserted on the SOURCE so it is checked even where the route needs a store the test does
    not have, and on the SYNTAX TREE rather than on the source text.

    IT USED TO MEASURE A DISTANCE, and that is why it is written this way now. The first
    version required the string `except Exception` to appear within 400 characters after the
    assignment — which is a proxy for "inside a try" that a comment can break without
    changing a line of behaviour, and one did. The rule being asserted is structural: every
    statement that touches the reported benchmark sits inside a `try` that catches, so a
    reported benchmark cannot take the bound card down with it. A tree check cannot be
    fooled by how much prose sits in between, and it also catches the case a character
    window never could — a SECOND reported-benchmark statement added outside the handler.
    """
    src = open(os.path.join(ROOT, "valuation", "web", "app.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "api_index_track"), None)
    assert fn is not None, "api_index_track is gone"

    def _mentions_rb(node) -> bool:
        for n in ast.walk(node):
            if isinstance(n, ast.Constant) and n.value == "reported_benchmark":
                return True
            if isinstance(n, ast.Attribute) and n.attr in ("claim", "attach_series"):
                return True
            if isinstance(n, ast.Name) and n.id == "reported_benchmark":
                return True
        return False

    guarded, unguarded = [], []
    for node in fn.body:
        if isinstance(node, ast.Try):
            if not _mentions_rb(node):
                continue
            assert node.handlers, "the reported-benchmark block has no handler at all"
            guarded.append(node)
        elif _mentions_rb(node):
            unguarded.append(node)

    assert guarded, "the payload does not carry the reported-benchmark block"
    assert not unguarded, ("a reported-benchmark statement sits outside the handler at line "
                           + ", ".join(str(n.lineno) for n in unguarded)
                           + " -- it can break the bound card")
    assert 'out["reported_benchmark"]' in src, "the payload key was renamed"


def test_the_derivation_note_is_written_beside_the_sibling():
    with tempfile.TemporaryDirectory() as d:
        meta, hist = _bound(d)
        out = rb.backfill(fetch=_tape(SPMO_TAPE), meta_path=meta, bound_history_path=hist)
        note = out.get("note_path")
        assert note and os.path.exists(note), out
        text = open(note, encoding="utf-8").read()
        assert "never re-derived here" in text, text[:400]
        assert "not bound" in text.lower(), text[:400]


# =======================================================================================
# THE HERO CARD — the sparkline's third line and the numbers row's fourth tile
# =======================================================================================
def _app_js() -> str:
    return open(os.path.join(ROOT, "valuation", "web", "static", "app.js"),
                encoding="utf-8").read()


def test_the_series_is_read_only_and_both_files_are_byte_identical_after_it():
    """A chart that could write the series it draws is a chart that can invent history."""
    with tempfile.TemporaryDirectory() as d:
        meta, hist = _bound(d)
        rb.backfill(fetch=_tape(SPMO_TAPE), meta_path=meta, bound_history_path=hist)
        sib = rb.sibling_path(hist)
        before_bound = open(hist, "rb").read()
        before_sib = open(sib, "rb").read()

        rb.series(bound_history_path=hist)
        rb.attach_series({"series": [{"date": "2026-08-06", "valquo": 1.0, "spy": 1.0}]},
                         bound_history_path=hist)
        rb.claim(bound_history_path=hist)

        assert open(hist, "rb").read() == before_bound, "the bound file moved on a READ path"
        assert open(sib, "rb").read() == before_sib, "the sibling moved on a READ path"


def test_the_series_returns_levels_in_date_order_and_not_the_excess():
    """Levels, because the chart plots levels. The two excesses are different quantities."""
    with tempfile.TemporaryDirectory() as d:
        meta, hist = _bound(d)
        rb.backfill(fetch=_tape(SPMO_TAPE), meta_path=meta, bound_history_path=hist)
        ser = rb.series(bound_history_path=hist)
        assert ser["available"], ser["reason"]
        dates = [p["date"] for p in ser["points"]]
        assert dates == sorted(dates), dates
        assert dates == ["2026-07-31", "2026-08-06", "2026-08-13", "2026-08-17"], dates

        # Every point must be the recorded LEVEL, never the recorded excess.
        rows = {r["date"]: r for r in index_mark._read_history(rb.sibling_path(hist))["rows"]}
        for pt in ser["points"]:
            r = rows[pt["date"]]
            assert abs(pt["spmo"] - float(r["spmo_pct"])) < 1e-12, (pt, r)
            if abs(float(r["spmo_pct"]) - float(r["excess_pp"])) > 1e-9:
                assert abs(pt["spmo"] - float(r["excess_pp"])) > 1e-9, \
                    "series() is emitting the excess where a level belongs"


def test_attach_series_adds_the_level_only_where_it_was_recorded():
    with tempfile.TemporaryDirectory() as d:
        meta, hist = _bound(d)
        rb.backfill(fetch=_tape(SPMO_TAPE), meta_path=meta, bound_history_path=hist)
        payload = {"series": [{"date": "2026-07-31", "valquo": 0.4126, "spy": 0.6903},
                              {"date": "2026-08-06", "valquo": 0.776, "spy": 3.6228}]}
        rb.attach_series(payload, bound_history_path=hist)
        assert all("spmo" in r for r in payload["series"]), payload


def test_attach_series_leaves_a_gap_rather_than_carrying_a_level_forward():
    """A day the sibling does not carry gets NO key, so the line breaks instead of flattening.

    Joining across a hole draws a flat stretch that reads as a day the benchmark did not
    move, which is a claim nobody measured.
    """
    with tempfile.TemporaryDirectory() as d:
        meta, hist = _bound(d)
        rb.backfill(fetch=_tape(SPMO_TAPE), meta_path=meta, bound_history_path=hist)
        payload = {"series": [{"date": "2026-07-31", "valquo": 0.4126, "spy": 0.6903},
                              {"date": "2026-08-04", "valquo": 0.5, "spy": 1.0},
                              {"date": "2026-08-06", "valquo": 0.776, "spy": 3.6228}]}
        rb.attach_series(payload, bound_history_path=hist)
        assert "spmo" in payload["series"][0]
        assert "spmo" not in payload["series"][1], \
            "a date the sibling never recorded was given a level"
        assert "spmo" in payload["series"][2]

        # And the client must be told not to bridge it.
        js = _app_js()
        assert "spanGaps: false" in js, "the chart may bridge a gap it should draw"


def test_attach_series_is_inert_when_no_sibling_exists():
    """The normal state on a service that has not recorded a comparison yet."""
    with tempfile.TemporaryDirectory() as d:
        _, hist = _bound(d)
        payload = {"series": [{"date": "2026-07-31", "valquo": 0.4126, "spy": 0.6903}]}
        before = json.dumps(payload, sort_keys=True)
        rb.attach_series(payload, bound_history_path=hist)
        assert json.dumps(payload, sort_keys=True) == before, payload


def test_attach_series_never_touches_a_bound_value_or_the_row_order():
    """Additive only: it may add `spmo` and may change nothing else."""
    with tempfile.TemporaryDirectory() as d:
        meta, hist = _bound(d)
        rb.backfill(fetch=_tape(SPMO_TAPE), meta_path=meta, bound_history_path=hist)
        rows = [{"date": "2026-08-13", "valquo": 4.25, "spy": 4.88, "excess": -0.62},
                {"date": "2026-07-31", "valquo": 0.4126, "spy": 0.6903, "excess": -0.2777}]
        payload = {"series": rows, "available": True}
        before = [dict(r) for r in rows]
        rb.attach_series(payload, bound_history_path=hist)
        assert [r["date"] for r in payload["series"]] == [b["date"] for b in before], \
            "attach_series reordered the bound rows"
        for got, was in zip(payload["series"], before):
            for k, v in was.items():
                assert got[k] == v, (k, got[k], v)
            assert set(got) - set(was) == {"spmo"}, set(got) - set(was)


def test_the_numbers_row_labels_the_spmo_tile_reported():
    """THE WHOLE POINT OF THE TILE. It sits in the same row as the bound SPY level, so the
    word that separates them has to be in the row — a caption underneath does not survive
    the row being screenshotted on its own."""
    js = _app_js()
    i = js.find("const rbTile")
    assert i > 0, "no SPMO tile is built"
    tile = js[i:i + 700]
    assert "reported" in tile, tile[:300]
    assert "rb.spmo_pct" in tile, "the tile is not showing the recorded SPMO level"

    # ...and it is rendered INSIDE the bound numbers row, immediately after Excess.
    j = js.find('${metric("Excess"')
    assert j > 0
    after = js[j:j + 260]
    assert "${rbTile}" in after, after


def test_the_third_chart_line_is_distinct_and_shares_the_one_scale():
    """SPY is already broken, so a third broken line must not share its geometry.

    And it must share the y-axis: a second scale lets two different arithmetics share a
    picture and look comparable, when the whole value of this line is that it IS comparable.

    IT USED TO PIN THE LITERAL GEOMETRIES (`[2, 3]` and `[5, 4]`), which is a check on the
    NUMBERS rather than on the property they were chosen for. When the two lines were later
    made more distinct — because in practice they still read alike where they converge — this
    test failed against an improvement. The property is that the two benchmarks do not share a
    dash geometry and that the reported one is the finer of the two; the exact values are a
    design choice and belong to whoever is looking at the chart.
    """
    chart = _chart_datasets()
    assert "r.spmo" in chart, "the chart never reads the attached SPMO level"
    dashes = re.findall(r"borderDash: \[([0-9.]+), ([0-9.]+)\]", chart)
    assert len(dashes) == 2, "expected exactly two broken lines, got %r" % (dashes,)
    assert dashes[0] != dashes[1], "the two benchmarks share a dash geometry: %r" % (dashes,)
    assert float(dashes[1][0]) < float(dashes[0][0]), (
        "the reported line's dashes are not finer than the bound one's: %r" % (dashes,))
    assert "yAxisID" not in _chart_config(), "a second axis was introduced on THIS chart"
    assert "reported" in chart, "the legend does not mark the line as reported"


def test_the_chart_caption_says_the_reported_line_is_not_the_contract():
    """A chart travels further than the card around it."""
    js = _app_js()
    i = js.find("Cumulative return of the MODEL portfolio")
    assert i > 0
    cap = js[i:i + 900]
    assert "reported benchmark" in cap, cap[:400]
    assert "contract" in cap, cap[:400]


def test_the_index_route_attaches_the_series_and_writes_nothing():
    """The route may READ the sibling. An AST check, because a runtime one only sees the
    paths a test happens to exercise."""
    src = open(os.path.join(ROOT, "valuation", "web", "app.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "api_index_track"), None)
    assert fn is not None, "api_index_track is gone"
    called = {n.func.attr for n in ast.walk(fn)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "attach_series" in called, "the route never attaches the reported series"
    for writer in ("record", "backfill", "append_row", "write"):
        assert writer not in called, \
            "the index route calls %s -- a display path must not write the record" % writer


def test_the_rendered_payload_with_the_series_carries_no_banned_phrase():
    """The banned check runs on what a surface actually renders, including the new fields."""
    with tempfile.TemporaryDirectory() as d:
        meta, hist = _bound(d)
        rb.backfill(fetch=_tape(SPMO_TAPE), meta_path=meta, bound_history_path=hist)
        c = rb.claim(bound_history_path=hist)
        ser = rb.series(bound_history_path=hist)
        text = " ".join([str(v) for v in c.values() if isinstance(v, str)]
                        + [str(ser.get("reason") or ""), str(ser.get("ticker") or "")])
        assert rb.violations(text) == [], rb.violations(text)
        # the negative control: the honest sentence must survive, and it is not a trivial one
        assert "contract" in c["label"] and "t 3.65" in c["why"], c


# =======================================================================================
# THE HERO BAND — one source of truth, and a distinction carried visually
# =======================================================================================
HERO = os.path.join(ROOT, "valuation", "web", "hero.py")
INDEX_HTML = os.path.join(ROOT, "valuation", "web", "templates", "index.html")
STYLE_CSS = os.path.join(ROOT, "valuation", "web", "static", "style.css")

#: A claim with the module's OWN wording and figures that differ from each other, so a test
#: cannot pass by rendering the wrong field.
HERO_CLAIM = {
    "available": True, "reason": "", "ticker": "SPMO",
    "label": rb.LABEL, "why": rb.WHY, "posture": rb.POSTURE,
    "as_of": "2026-08-24", "since": "2026-07-31", "n_points": 9,
    "valquo_pct": 4.2107, "spmo_pct": 1.9043, "excess_pp": 2.3064,
    "valquo_src": "recorded",
}


def _with_claim(claim):
    """Swap `reported_benchmark.claim` for a fixed one. Returns a restorer."""
    was = rb.claim
    rb.claim = lambda **k: (dict(claim) if isinstance(claim, dict) else claim)

    def restore():
        rb.claim = was
    return restore


def _render_band(claim=None, index_over=None) -> str:
    """The rendered band, as a visitor receives it."""
    from valuation.saas.app_saas import create_saas_app
    from valuation.web import hero as H
    from flask import render_template

    restore = _with_claim(HERO_CLAIM if claim is None else claim)
    try:
        idx = {"available": True, "benchmark": "SPY", "cum_pct": 4.2107, "bench_pct": 1.5,
               "excess_pp": 2.7107, "days": 9, "book": "86 names",
               "window": "since 2026-07-31", "as_of": "2026-08-24",
               "age": {"age": 17, "recorded": 9, "complete": False, "short": "17d"}}
        idx.update(index_over or {})
        hero = {"show": True, "thin": True, "may_lead": False, "since": "2026-07-31",
                "label": "paper, since 2026-07-31, thin", "index": idx,
                "options": {"available": False}, "spark": None,
                "reported": H._reported_block(idx), "caveat": "Paper, not real money."}
        app = create_saas_app()
        with app.test_request_context():
            html = render_template("index.html", live_hero=lambda: hero,
                                   may_see_owner=True, work_url="/work")
    finally:
        restore()
    i = html.find('class="livebar')
    j = html.find("<!-- SINGLE -->", i)
    return html[i:j] if i >= 0 else ""


def test_the_hero_and_the_index_tab_read_the_same_reported_function():
    """ONE SOURCE OF TRUTH. Two implementations of one number is `B7`'s defect class, and
    `hero.py`'s own docstring records the sharper version: the fallback removed in 2026-08-09
    took *its own `(idx - bench) * 100`, a second definition of excess return, free to drift
    from the recorder's*.

    Asserted on the SYNTAX TREE of both call sites, because a runtime check only sees the
    paths a test happens to exercise.
    """
    def _calls(path, fn_name):
        tree = ast.parse(open(path, encoding="utf-8").read())
        fn = next((n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == fn_name), None)
        assert fn is not None, "%s is gone from %s" % (fn_name, path)
        return {n.func.attr for n in ast.walk(fn)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}

    hero_calls = _calls(HERO, "_reported_block")
    api_calls = _calls(os.path.join(ROOT, "valuation", "web", "app.py"), "api_index_track")
    assert "claim" in hero_calls, "the hero does not read reported_benchmark.claim"
    assert "claim" in api_calls, "the index route does not read reported_benchmark.claim"


def test_the_hero_never_recomputes_the_reported_excess():
    """It COPIES `excess_pp`. A hero that divided two levels would be the second definition."""
    src = open(HERO, encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "_reported_block")
    for node in ast.walk(fn):
        assert not isinstance(node, ast.BinOp), (
            "the hero does arithmetic on the reported benchmark at line %d — it must copy the "
            "recorder's figure, never derive one" % node.lineno)


def test_the_reported_figures_reach_the_band_and_are_the_recorders():
    band = _render_band()
    assert "+1.90%" in band, "the SPMO mark is not on the band"
    assert "+2.31pp" in band, "the SPMO excess is not on the band"
    # ...and the BOUND excess is a different number, still present and unchanged.
    assert "+2.71pp" in band, "the bound excess moved"


def test_the_not_bound_wording_survives_into_the_rendered_band():
    """V3's precedent: one module owns the calibrated wording, asserted VERBATIM against the
    RENDERED payload rather than the source.

    `hero.py`'s own lesson is why it is the rendered payload: the removed fallback DID set
    `source: "paper-sandbox"`, honestly, and the template never rendered it — *a label that a
    surface can decline to show is not a safeguard*.
    """
    band = _render_band()
    import html as _h
    plain = _h.unescape(band)
    assert rb.LABEL in plain, "the reported-benchmark LABEL is not rendered on the band"
    assert rb.POSTURE in plain, "the posture sentence is not rendered on the band"
    assert "reported" in band, "the inline `reported` tag is missing"
    for banned in rb.BANNED:
        assert banned not in plain.lower(), "the band carries a banned phrase: %r" % banned


def test_the_band_makes_no_reported_claim_when_none_is_recorded():
    """The normal state on a service that has recorded no comparison yet."""
    band = _render_band(claim={"available": False, "reason": "nothing recorded yet"})
    assert "SPMO" not in band, "the band named a benchmark it has no figure for"
    assert "rep-tag" not in band, "an empty reported block still rendered its tag"
    # The bound claim is untouched by its absence.
    assert "+2.71pp" in band, "the bound excess vanished with the reported one"


def test_the_reported_block_can_never_gate_the_band():
    """Context may not decide whether the claim is shown. `show` is computed from the index
    and options blocks only, asserted on the tree."""
    tree = ast.parse(open(HERO, encoding="utf-8").read())
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "live_hero")
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id in ("show", "thin") for t in node.targets):
            names = {n.id for n in ast.walk(node.value) if isinstance(n, ast.Name)}
            assert "rep" not in names, (
                "the reported benchmark participates in `%s` at line %d"
                % (node.targets[0].id, node.lineno))


def test_the_day_and_recorded_counts_agree_across_both_surfaces():
    """A hero card and a detail box disagreeing about how much evidence exists is worse than
    either number being wrong. Both read `index_track.summarize`'s `live.age`, so this pins
    that neither surface derives its own."""
    hero_src = open(HERO, encoding="utf-8").read()
    js = open(os.path.join(ROOT, "valuation", "web", "static", "app.js"),
              encoding="utf-8").read()
    assert '"age": live.get("age")' in hero_src, "the hero stopped taking age from the recorder"
    assert "live.age" in js, "the Index tab stopped taking age from the recorder"
    # Neither surface may count rows and call it an age — LA8's defect.
    tree = ast.parse(hero_src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "_index_block")
    got = {n.args[0].value for n in ast.walk(fn)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
           and n.func.attr == "get" and n.args and isinstance(n.args[0], ast.Constant)}
    assert "age" in got and "days" in got, got


def test_an_as_of_mismatch_is_disclosed_rather_than_absorbed():
    """The two series are different files and can end on different dates. Rendered flush
    against each other with no note, that is two windows presented as one."""
    from valuation.web import hero as H
    restore = _with_claim(HERO_CLAIM)
    try:
        assert H._reported_block({"as_of": "2026-08-24"})["aligned"] is True
        assert H._reported_block({"as_of": "2026-08-22"})["aligned"] is False
    finally:
        restore()
    band = _render_band(index_over={"as_of": "2026-08-22"})
    assert "Measured to 2026-08-24" in band, "a date mismatch was rendered silently"
    assert "Measured to" not in _render_band(), "the note shows when the dates agree"


def test_the_reported_tiles_are_subordinate_on_axes_that_are_not_colour():
    """A hierarchy that lives only in colour is lost to a greyscale print and to a colourblind
    reader. SIZE and WEIGHT are asserted numerically; the inline tag is a WORD."""
    css = open(STYLE_CSS, encoding="utf-8").read()
    claim = re.search(r"\.lb-stat \.v\{([^}]*)\}", css).group(1)
    rep = re.search(r"\.lb-stat\.rep \.v\{([^}]*)\}", css)
    assert rep, ".lb-stat.rep .v is not styled at all"
    rep = rep.group(1)

    def _num(block, prop):
        m = re.search(prop + r":([0-9.]+)", block)
        return float(m.group(1)) if m else None

    assert _num(rep, "font-size") < _num(claim, "font-size"), (claim, rep)
    assert _num(rep, "font-weight") < _num(claim, "font-weight"), (claim, rep)
    # A NON-ZERO border, and every `.lb-stat.rep{...}` block is examined rather than the
    # first match. The first version of this assertion searched for the SUBSTRING
    # `border-left` and was satisfied by the mobile override, which sets `border-left:0` —
    # so deleting the real separator left the test green. Found by mutation.
    blocks = re.findall(r"\.lb-stat\.rep\{([^}]*)\}", css)
    assert blocks, ".lb-stat.rep is not styled at all"
    widths = [re.search(r"border-left:\s*([0-9.]+)", b) for b in blocks]
    assert any(m and float(m.group(1)) > 0 for m in widths), (
        "no non-colour separator between the claim and the context: %r" % blocks)
    band = _render_band()
    # BOTH tiles, counted. Asserting `in` passed a mutation that stripped the class from only
    # the first of the two — found by the tripwire run, which is what tripwires are for.
    assert band.count('class="lb-stat rep"') == 2, (
        "expected both reported tiles to carry the subordinate class, found %d"
        % band.count('class="lb-stat rep"'))
    assert band.count("rep-tag") == 2, (
        "expected both reported tiles to carry the inline tag, found %d"
        % band.count("rep-tag"))


# =======================================================================================
# THE CHART — three lines a reader can order in one second, without colour
# =======================================================================================
def _chart_config() -> str:
    """The index chart's whole `new Chart(el, {...})` config, brace-balanced.

    Scoped rather than file-wide: `app.js` draws several charts and some of them legitimately
    use a second axis, so asking whether `yAxisID` appears ANYWHERE answers a different
    question from the one being asked.
    """
    js = _app_js()
    i = js.find("STATE.charts.idx")
    assert i > 0, "the index chart is gone"
    j = js.index("{", js.index("new Chart(", i))
    depth = 0
    for k in range(j, len(js)):
        if js[k] == "{":
            depth += 1
        elif js[k] == "}":
            depth -= 1
            if depth == 0:
                return js[j:k + 1]
    raise AssertionError("unbalanced chart config")


def _chart_datasets() -> str:
    """The chart's `datasets: [...]` array, extracted by BALANCING BRACKETS.

    NOT a fixed character window. The first cut of these tests took `js[i:i + 2600]` from
    `STATE.charts.idx`, and adding a comment above the datasets pushed the third line out of
    the window — the test then reported that the chart *"never reads the attached SPMO level"*
    when the chart was fine. That is the same defect shape as the 400-character
    `except Exception` window in `test_the_api_payload_exposes_the_block_without_breaking_the_
    bound_card`, which a comment of mine also broke: a guard whose reach is measured in
    characters is a guard that prose can silently move out from under.
    """
    js = _app_js()
    i = js.find("STATE.charts.idx")
    assert i > 0, "the index chart is gone"
    start = js.find("datasets: [", i)
    assert start > 0, "the chart has no datasets array"
    depth, j = 0, js.index("[", start)
    for k in range(j, len(js)):
        if js[k] == "[":
            depth += 1
        elif js[k] == "]":
            depth -= 1
            if depth == 0:
                return js[j:k + 1]
    raise AssertionError("unbalanced datasets array")


def test_the_three_lines_differ_in_geometry_and_in_weight_not_only_in_hue():
    """SPY and SPMO used to be two light greys, one dashed and one dotted, and read as the
    same series wherever they converged — which on two large-cap US benchmarks is most of the
    time. Geometry, weight and tone now vary together, so ANY ONE of the three is enough to
    order them."""
    ds = _chart_datasets()
    dashes = re.findall(r"borderDash: \[([0-9.]+), ([0-9.]+)\]", ds)
    widths = [float(w) for w in re.findall(r"borderWidth: ([0-9.]+)", ds)]
    colours = re.findall(r'borderColor: "(#[0-9a-fA-F]{6})"', ds)

    assert len(dashes) == 2, dashes                     # the subject line is SOLID
    assert len(set(dashes)) == 2, "the two benchmarks share a dash geometry: %r" % dashes
    assert len(widths) == 3 and len(set(widths)) == 3, "line weights are not distinct: %r" % widths
    assert len(colours) == 3 and len(set(colours)) == 3, "line tones are not distinct: %r" % colours

    # The ordering is the hierarchy: subject widest, reported thinnest.
    assert widths[0] == max(widths), "the subject is not the widest line: %r" % widths
    assert widths[-1] == min(widths), "the reported line is not the thinnest: %r" % widths


def test_the_subject_line_is_the_only_solid_one():
    ds = _chart_datasets()
    first = ds[:ds.find("borderDash")]
    assert "Valquo Index" in first, "the first dataset is not the subject"
    assert "borderDash" not in first, "the subject line is broken rather than solid"


def test_the_legend_says_which_benchmark_is_bound_and_which_is_reported():
    ds = _chart_datasets()
    assert "contract benchmark" in ds, "the legend does not mark SPY as the bound one"
    assert "reported, not bound" in ds, "the legend does not mark SPMO as reported"


def test_the_chart_caption_keeps_its_distinction():
    js = _app_js()
    i = js.find("Cumulative return of the MODEL portfolio")
    assert i > 0
    cap = js[i:i + 900]
    assert "reported benchmark" in cap and "contract" in cap, cap[:300]


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
