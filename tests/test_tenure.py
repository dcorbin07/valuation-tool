"""MA30 — tenure on the hot list, and the two rules the audit fixed before it was built.

The arithmetic is the easy half. The half worth testing is the pair of constraints, because
both are the kind that rot silently:

  * THE CLAIM IT MUST NOT MAKE. `S22` measured a term structure of the SIGNAL, not of
    TENURE, and no arm has tested tenure as a predictor. So the copy may describe churn and
    may not imply that long-tenured names are better. `BANNED` is asserted against the
    RENDERED payload, not against the source, because rendering is where copy leaks.
  * A REGISTER THE MOMENT ANYONE SORTS OR FILTERS BY IT. Displaying tenure discloses churn;
    ranking or filtering on it is a new selection rule and needs the both-halves gate. A
    source-level sweep fails if the field reaches a sort key or a filter predicate.

Every fixture is synthetic and no test touches the real store. The numbers this module will
show on the live service have never been observed — see the module docstring.

Run: python tests/test_tenure.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.web import tenure  # noqa: E402


class _FakeStore:
    def __init__(self, history, boom=False):
        self._h, self._boom = history, boom

    def recent_ranks(self, n_scans=20):
        if self._boom:
            raise RuntimeError("store is unreachable")
        return self._h[:n_scans]


def _hist(*days):
    """`days` are newest-first `(scored, {ticker: rank})` pairs."""
    return [("2026-08-%02d" % (20 - i), s, r) for i, (s, r) in enumerate(days)]


# ============================== the arithmetic =============================================
def test_a_streak_counts_back_from_the_newest_scan_and_stops_at_the_first_miss():
    h = _hist((100, {"AAA": 3, "BBB": 50}),
              (100, {"AAA": 9, "BBB": 4}),
              (100, {"AAA": 1, "BBB": 2}))
    s = tenure.streaks(h)
    assert s["AAA"]["scans"] == 3, s          # 3, 9, 1 — all inside the top 10 of 100
    assert s["BBB"]["scans"] == 0, s          # rank 50 on the NEWEST scan breaks it at once


def test_absence_from_a_scan_is_a_miss_and_not_a_skip():
    """A name the scan did not rank and a name it ranked poorly are the same thing to a
    reader of the list: it was not on it that day."""
    h = _hist((100, {"AAA": 2}), (100, {}), (100, {"AAA": 1}))
    assert tenure.streaks(h)["AAA"]["scans"] == 1


def test_a_scan_with_no_recorded_size_is_skipped_rather_than_counted_either_way():
    """A missing denominator must not read as 'everybody qualified' OR as a miss."""
    h = _hist((100, {"AAA": 2}), (None, {"AAA": 999}), (100, {"AAA": 3}))
    assert tenure.decile_cutoff(None) is None
    assert tenure.streaks(h)["AAA"]["scans"] == 2, "the sizeless scan was not skipped"


def test_the_decile_is_taken_over_the_scan_and_not_over_what_the_viewer_asked_for():
    """`?top=` differs per tier, so measuring against it would give one name two tenures."""
    assert tenure.decile_cutoff(1000) == 100
    assert tenure.decile_cutoff(95) == 10        # ceil, so a 95-name scan admits 10
    assert tenure.decile_cutoff(3) == 1          # never zero: a tiny scan still has a top
    assert tenure.decile_cutoff(0) is None and tenure.decile_cutoff(-5) is None


def test_a_name_at_the_lookback_cap_says_so_rather_than_implying_a_ceiling_is_a_count():
    h = _hist(*[(100, {"AAA": 1}) for _ in range(tenure.LOOKBACK_SCANS)])
    s = tenure.streaks(h)["AAA"]
    assert s["scans"] == tenure.LOOKBACK_SCANS and s["capped"] is True, s
    short = tenure.streaks(_hist((100, {"AAA": 1})))["AAA"]
    assert short["capped"] is False, short


# ============================== additive and fail-soft =====================================
def test_annotate_never_reorders_or_drops_a_row():
    rows = [{"ticker": t, "rank": i + 1} for i, t in enumerate(("AAA", "BBB", "CCC"))]
    before = [r["ticker"] for r in rows]
    tenure.annotate(rows, _FakeStore(_hist((100, {"AAA": 1, "BBB": 2, "CCC": 3}))))
    assert [r["ticker"] for r in rows] == before, "the disclosure reordered the hot list"
    assert len(rows) == 3


def test_an_unreachable_store_leaves_the_rows_untouched_and_says_it_is_unavailable():
    """A display disclosure must never be able to fail a public scan render."""
    rows = [{"ticker": "AAA"}]
    block = tenure.annotate(rows, _FakeStore([], boom=True))
    assert block["available"] is False, block
    assert "tenure_scans" not in rows[0], "a missing count was defaulted onto the row"


def test_no_history_is_reported_missing_rather_than_as_one_scan_for_everybody():
    """Defaulting to 1 would render 'new today' for every name — a confident wrong caption."""
    rows = [{"ticker": "AAA"}]
    block = tenure.annotate(rows, _FakeStore([]))
    assert block["available"] is False and block["scans_available"] == 0, block
    assert "tenure_scans" not in rows[0]


def test_a_present_count_reaches_the_row():
    rows = [{"ticker": "AAA"}, {"ticker": "ZZZ"}]
    block = tenure.annotate(rows, _FakeStore(_hist((100, {"AAA": 4}), (100, {"AAA": 4}))))
    assert block["available"] is True and block["scans_available"] == 2, block
    assert rows[0]["tenure_scans"] == 2 and rows[1]["tenure_scans"] == 0, rows


# ============================== the store reader ===========================================
def test_recent_ranks_reads_the_scans_own_recorded_size_and_not_a_live_row_count():
    """A partially deleted snapshot must not shrink the decile and admit names that were
    never in the top tenth of the scan that actually ran."""
    import tempfile

    from valuation.screener.store import Store
    with tempfile.TemporaryDirectory() as d:
        st = Store(os.path.join(d, "s.db"))
        st.save_snapshot("2026-08-10",
                         [{"ticker": "T%03d" % i, "rank": i + 1} for i in range(50)],
                         provider="fixture")
        with st._conn() as c:                       # simulate a damaged/partial snapshot
            c.execute("DELETE FROM snapshot_rows WHERE scan_date=? AND rank > 5",
                      ("2026-08-10",))
        (_, scored, ranks), = st.recent_ranks(5)
        assert len(ranks) == 5, ranks
        assert scored == 50, ("recent_ranks recomputed the size from the surviving rows; "
                              "the decile would have been 1 instead of 5")
        assert tenure.decile_cutoff(scored) == 5


# ============================== the copy rule ==============================================
def test_the_rendered_payload_never_claims_a_longer_tenure_is_a_better_name():
    """Asserted against what is SERVED, which is where copy leaks — not against the source."""
    rows = [{"ticker": "AAA"}]
    block = tenure.annotate(rows, _FakeStore(_hist((100, {"AAA": 1}))))
    rendered = " ".join(str(v) for v in block.values())
    assert not tenure.violations(rendered), tenure.violations(rendered)


def test_the_banned_list_is_not_vacuous():
    assert tenure.violations("our highest conviction pick") == ["conviction pick"]
    assert tenure.violations("A CONSISTENT PERFORMER") == ["consistent performer"]
    assert tenure.violations("in the top 10% for four scans") == []


def test_the_explainer_says_out_loud_that_tenure_was_never_tested_as_a_predictor():
    """The disclosure's whole value is that a reader cannot mistake it for a signal."""
    low = tenure.EXPLAINER.lower()
    assert "churn" in low, tenure.EXPLAINER
    assert "never tested" in low or "not tested" in low, tenure.EXPLAINER
    assert "not a measure of quality" in low, tenure.EXPLAINER


# ============================== the register rule ==========================================
def _sources():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel in ("valuation/web/app.py", "valuation/web/tenure.py",
                "valuation/screener/screen.py", "valuation/screener/store.py"):
        p = os.path.join(root, rel)
        if os.path.exists(p):
            yield rel, open(p, encoding="utf-8").read()


def test_nothing_sorts_or_filters_on_tenure_without_a_register():
    """MA30's standing condition. Displaying churn is free; screening on it is a selection
    rule and needs the both-halves gate, so it must not arrive by accident."""
    bad = []
    for rel, src in _sources():
        for i, line in enumerate(src.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") or "tenure_scans" not in stripped:
                continue
            for verb in ("sort(", "sorted(", "key=", "filter(", "if r[", "order_by", "ORDER BY"):
                if verb in stripped:
                    bad.append(f"{rel}:{i}: {stripped}")
    assert not bad, ("tenure is being used to order or select names, which needs its own "
                     "register (see web/tenure.py): " + "; ".join(bad))


def test_the_register_sweep_would_catch_a_real_violation():
    """Non-vacuity: the sweep only means something if the pattern it hunts is findable."""
    line = 'rows = sorted(rows, key=lambda r: -r.get("tenure_scans", 0))'
    hits = [v for v in ("sort(", "sorted(", "key=", "filter(") if v in line]
    assert "tenure_scans" in line and hits, "the sweep's own pattern does not match a screen"


def test_the_hot_list_payload_carries_the_block_and_the_module_owns_the_copy():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = open(os.path.join(root, "valuation", "web", "app.py"), encoding="utf-8").read()
    assert '"tenure": tenure_block' in src, "the hot list does not serve the tenure block"
    for phrase in (tenure.LABEL, tenure.EXPLAINER[:40]):
        assert phrase not in src, ("the copy is duplicated in app.py; one module owns it "
                                   "(the score_confidence.py rule)")


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
    print("\n" + str(passed) + "/" + str(len(tests)) + " MA30 tenure tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
