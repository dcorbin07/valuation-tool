"""O17-C4 as its own strategy, pinned.  [PREREG_o17c4_own_the_event.md]

The assertions that matter are the ones protecting the two things this register exists to get
right:

  * the RULE is the shipped one, called and never re-typed — a second copy of `owns_the_event`
    is the B7 defect, and it would silently answer a different question under this one's name;
  * `None` (UNKNOWN) is DROPPED and never folded into either arm — 29 of 186 names are foreign
    private issuers with no earnings dates, so a filter reading "no date" as "no announcement"
    fails OPEN on a non-random tenth of the book;
  * the bar is derived in a pass that CANNOT import the arms, which is what makes
    "the bar was derived before the arm faced it" structural rather than a claim about ordering.
"""
from __future__ import annotations

import ast
import contextlib
import datetime as dt
import io
import os
import sys
import tokenize

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BARS_SRC = os.path.join(REPO, "scripts", "o17c4_own_the_event.py")
ARMS_SRC = os.path.join(REPO, "scripts", "o17c4_arms.py")


@contextlib.contextmanager
def raises(exc, contains=None):
    try:
        yield
    except exc as e:                                                  # noqa: BLE001
        if contains is not None and contains not in str(e):
            raise AssertionError("expected %r in %r" % (contains, str(e)))
        return
    raise AssertionError("expected %s, nothing raised" % exc.__name__)


def _code_only(path):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    out = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type not in (tokenize.COMMENT, tokenize.STRING):
            out.append(tok.string)
    return " ".join(out)


# ------------------------------------------------------------------ the rule is the shipped one
def test_owns_the_event_is_imported_never_reimplemented():
    """B7. A second copy of the rule would answer a different question under this one's name."""
    for p in (BARS_SRC, ARMS_SRC):
        blob = _code_only(p)
        assert "def owns_the_event" not in blob, "%s re-implements owns_the_event" % p
    tree = ast.parse(open(BARS_SRC, encoding="utf-8").read())
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            for a in n.names:
                names.add(a.name)
    assert "owns_the_event" in names, "the shipped rule is not imported at all"


def test_the_shipped_rule_still_means_what_this_register_assumes():
    """If `owns_the_event` ever changed meaning, every number here would silently change with
    it. Pinned against hand-built cases rather than against the artifact."""
    from valuation.studies.earnings_surface import owns_the_event
    # expiry after the next announcement -> owns it
    assert owns_the_event("2024-01-10", "2024-03-15", ["2024-02-01"]) is True
    # expiry before the next announcement -> does not
    assert owns_the_event("2024-01-10", "2024-01-20", ["2024-02-01"]) is False
    # no earnings dates at all -> UNKNOWN, not False
    assert owns_the_event("2024-01-10", "2024-03-15", []) is None
    # only PAST announcements -> UNKNOWN, not False
    assert owns_the_event("2024-01-10", "2024-03-15", ["2023-11-01"]) is None


# ------------------------------------------------------------------ UNKNOWN is dropped
def test_unknown_is_dropped_and_never_folded_into_either_arm():
    """29 of 186 names are foreign private issuers with ZERO earnings coverage (388 trades,
    10.0%). Reading 'no date' as 'no announcement' fails OPEN on a non-random tenth."""
    from scripts.o17c4_own_the_event import tag
    rows = [
        {"ticker": "AAA", "alert_ts": "2024-01-10", "expiry": "2024-03-15"},   # spans
        {"ticker": "AAA", "alert_ts": "2024-01-10", "expiry": "2024-01-20"},   # not
        {"ticker": "ZZZ", "alert_ts": "2024-01-10", "expiry": "2024-03-15"},   # unknown
    ]
    spans, nots, unk = tag(rows, {"AAA": ["2024-02-01"]})
    assert len(spans) == 1 and len(nots) == 1 and len(unk) == 1
    assert unk[0]["ticker"] == "ZZZ"
    assert all(r["ticker"] != "ZZZ" for r in spans + nots), "an UNKNOWN row entered an arm"


# ------------------------------------------------------------------ bar before arm, structurally
def test_the_bars_pass_cannot_import_the_arms():
    """The bar must be derivable without the arms existing. If the bars module imported the
    arms module, 'derived first' would be a claim about ordering rather than a property."""
    tree = ast.parse(open(BARS_SRC, encoding="utf-8").read())
    top_level_imports = []
    for n in tree.body:                      # MODULE level only — a function-local import in
        if isinstance(n, (ast.Import, ast.ImportFrom)):   # main() is the deferred arms call
            top_level_imports.append(n)
    for n in top_level_imports:
        mods = ([a.name for a in n.names] if isinstance(n, ast.Import)
                else [n.module or ""])
        for m in mods:
            assert "o17c4_arms" not in str(m), "the bars pass imports the arms at module level"


def test_the_arms_refuse_to_run_without_a_bars_artifact():
    import scripts.o17c4_own_the_event as G
    old = G.BARS_JSON
    G.BARS_JSON = os.path.join(REPO, "no_such_bars_artifact_o17c4.json")
    try:
        sys.argv = ["x", "--arms"]
        with raises(SystemExit, contains="REFUSING"):
            G.main()
    finally:
        G.BARS_JSON = old


def test_the_registered_bars_are_not_quietly_widened_by_the_diagnostic():
    """A DEFECT IN MY OWN BARS was found by running them, and the correction is REPORTED.
    The diagnostic must never feed the pass/fail flags — moving a bar after seeing it fail is
    the move TP-BAR exists to refuse."""
    # RAW source, not the comment/string-stripped blob: both names are dict KEYS, i.e. string
    # literals, so the stripper removes exactly what is under test here.
    src = open(BARS_SRC, encoding="utf-8").read()
    i = src.find("B1_B2_DEFECT_DIAGNOSTIC")
    assert i > 0, "the defect diagnostic is gone"
    j = src.find('out["all_bars_pass"]')
    assert 0 < j < i, "all_bars_pass is assigned AFTER the diagnostic — it could read it"
    # and the diagnostic's own keys must not be referenced by the flag computation
    flag_region = src[:j]
    assert "B1_B2_DEFECT_DIAGNOSTIC" not in flag_region


# ------------------------------------------------------------------ the statistic
def test_the_sign_test_uses_name_year_cells_and_needs_both_sides():
    """C-SIGN. R2 established the paired t is the wrong statistic on a barbell payoff; the
    name-year sign test carries the verdict. A cell counts only when BOTH sides have trades."""
    from scripts.o17c4_arms import sign_test_by_name_year
    a = [{"ticker": "AAA", "alert_ts": "2024-02-01", "pnl_pct": 1.0},
         {"ticker": "BBB", "alert_ts": "2024-02-01", "pnl_pct": 1.0}]
    b = [{"ticker": "AAA", "alert_ts": "2024-03-01", "pnl_pct": 0.0}]
    r = sign_test_by_name_year(a, b)
    assert r["n_cells"] == 1, "a cell with no counterpart was scored"
    assert r["wins"] == 1
    empty = sign_test_by_name_year(a, [{"ticker": "CCC", "alert_ts": "2024-02-01", "pnl_pct": 0.0}])
    assert empty["n_cells"] == 0 and empty["z"] is None


def test_halves_split_on_the_registered_date_and_are_disjoint():
    from scripts.o17c4_arms import _half, HALF_SPLIT
    assert HALF_SPLIT == dt.date(2021, 1, 1)
    rows = [{"ticker": "A", "alert_ts": "2019-05-01", "pnl_pct": 0.0},
            {"ticker": "A", "alert_ts": "2023-05-01", "pnl_pct": 0.0}]
    e, l = _half(rows, False), _half(rows, True)
    assert len(e) == 1 and len(l) == 1
    assert not (set(id(x) for x in e) & set(id(x) for x in l)), "halves overlap"


def test_concurrency_counts_simultaneous_positions_not_trades():
    """B3 is O11's question and it is about OVERLAP, not count."""
    from scripts.o17c4_arms import _d  # noqa: F401
    from scripts.o17c4_own_the_event import concurrency
    # three trades fully overlapping -> peak 3
    rows = [{"alert_ts": "2024-01-01", "expiry": "2024-06-01"} for _ in range(3)]
    assert concurrency(rows, caps=(2,))["peak_open"] == 3
    # three trades end to end -> peak 1
    seq = [{"alert_ts": "2024-01-01", "expiry": "2024-01-10"},
           {"alert_ts": "2024-02-01", "expiry": "2024-02-10"},
           {"alert_ts": "2024-03-01", "expiry": "2024-03-10"}]
    assert concurrency(seq, caps=(2,))["peak_open"] == 1


def test_a_cap_refuses_trades_only_when_it_binds():
    from scripts.o17c4_own_the_event import concurrency
    rows = [{"alert_ts": "2024-01-01", "expiry": "2024-06-01"} for _ in range(5)]
    r = concurrency(rows, caps=(2, 50))
    assert r["refused_at_cap_2"] == 3, r
    assert r["refused_at_cap_50"] == 0, r


if __name__ == "__main__":
    fails = 0
    names = [n for n in sorted(globals()) if n.startswith("test_")]
    for name in names:
        try:
            globals()[name]()
            print("PASS", name)
        except Exception as e:                                        # noqa: BLE001
            fails += 1
            print("FAIL", name, "->", repr(e))
    print("%d passed, %d failed" % (len(names) - fails, fails))
    sys.exit(1 if fails else 0)
