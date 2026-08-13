"""The scream-buy track record: the reset, and the fields it may not recompute.

WHAT THESE TESTS ARE FOR:

1. **A reset must never become a deletion.** The module must contain no write, the register
   note must ship with every response, and an archived row must be counted rather than
   vanishing. A track record that can be silently truncated is worth nothing.
2. **Entry / target / stop / current are READ, never derived.** Session 16 found 2 of 3 open
   positions trading to levels no backtest describes, because the target was anchored to the
   submit price while the entry was overwritten with the fill. A display that computed
   `entry x 2.0` would agree with the repaired code by coincidence and stop agreeing the
   first time an alert carried its own policy.
3. **A stale mark is labelled, and no mark at all is stale.** Rendering an unmarked position's
   price as current is the failure the flag exists for.
4. **The R2 context travels with the table**, from the one module that owns it.
"""
import datetime as _dt
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.web import scream_track as ST  # noqa: E402
from valuation.web import payoff  # noqa: E402

PASSED = []
FAILED = []
TODAY = _dt.date(2026, 8, 20)


def check(name, fn):
    try:
        fn()
        PASSED.append(name)
        print(f"  PASS  {name}")
    except AssertionError as e:
        FAILED.append((name, str(e)))
        print(f"  FAIL  {name}: {e}")
    except Exception as e:                                            # noqa: BLE001
        FAILED.append((name, f"{type(e).__name__}: {e}"))
        print(f"  ERROR {name}: {type(e).__name__}: {e}")


def _order(**kw):
    o = {"alert_id": 1, "ticker": "AAA", "occ_symbol": "AAA260101C00100000",
         "expiry": "2026-09-18", "state": "open", "contracts": 1,
         "entry_premium": 2.00, "target_premium": 4.00, "stop_premium": 1.00,
         "last_mark": 2.50, "last_mark_ts": "2026-08-19", "created_at": "2026-08-14"}
    o.update(kw)
    return o


def _alert(**kw):
    a = {"id": 1, "ticker": "AAA", "alert_ts": "2026-08-14T15:30:00",
         "opt_right": "call", "strike": 100.0, "expiry": "2026-09-18"}
    a.update(kw)
    return a


# ----------------------------------------------------------------------------------------
# 1. THE RESET IS A DISPLAY EPOCH, NOT A DELETION
# ----------------------------------------------------------------------------------------

def _module_code(name="scream_track.py"):
    """The module's source with docstrings and comments removed.

    Needed because this module DISCUSSES the things it must not do — the register note itself
    contains the sentence "Nothing was deleted". A naive substring scan flags that prose as
    the defect it documents, which would push the explanation out of the tree to make a check
    go green. The same trap the theme-legend tests hit.
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = open(os.path.join(here, "valuation", "web", name), encoding="utf-8").read()
    code = re.sub(r'"""[\s\S]*?"""', " ", src)
    return re.sub(r"^\s*#.*$", " ", code, flags=re.M)


def test_the_module_issues_no_write_statement():
    # The strongest available form of "nothing was deleted": there is no statement here that
    # could. Checked against the SQL this module executes, not against its prose — the note
    # legitimately contains the word "deleted".
    code = _module_code()
    stmts = re.findall(r"execute\(\s*(.*?)\)", code, re.S)
    for s in stmts:
        up = s.upper()
        for verb in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE"):
            assert verb not in up, f"{verb} in an executed statement: {s[:80]}"
    assert "commit(" not in code, "a read-only display module must not commit"
    assert stmts, "expected at least one SELECT, or this test is passing vacuously"


def test_that_write_check_would_actually_catch_a_write():
    # A scan that finds nothing proves nothing unless it can find something. Calibrating it
    # against a known-bad string is the difference between a pin and a decoration.
    bad = 'c.execute("DELETE FROM option_alerts")'
    stmts = re.findall(r"execute\(\s*(.*?)\)", bad, re.S)
    assert stmts and "DELETE" in stmts[0].upper(), stmts


def test_the_register_note_ships_with_every_response_including_an_empty_one():
    out = ST.build_rows([], {}, today=TODAY)
    reg = out["register"]
    assert reg["reset_date"] == ST.RESET_DATE
    assert reg["archive_path"] == ST.ARCHIVE_PATH
    assert reg["note"], "the reset must never render without its reason"
    for must in ("archived", "reason", ST.RESET_DATE):
        assert must in reg["note"], (must, reg["note"])


def test_the_note_states_that_nothing_was_deleted():
    assert "deleted" in ST.RESET_NOTE.lower(), ST.RESET_NOTE


def test_the_archive_path_actually_exists_in_the_repository():
    # A register note pointing at a file that is not there is worse than no note: it reads as
    # a promise the archive is inspectable.
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert os.path.exists(os.path.join(here, ST.ARCHIVE_PATH)), ST.ARCHIVE_PATH


def test_the_archive_actually_contains_the_scream_record():
    # ...and that it is the right file: it has to carry the alerts table, or the note is
    # pointing at an archive of something else.
    import json
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, ST.ARCHIVE_PATH), encoding="utf-8") as f:
        pay = json.load(f)
    assert "option_alerts" in pay, sorted(pay)
    assert "paper_orders" in pay, sorted(pay)


def test_the_long_form_register_document_exists_and_is_tracked():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(here, ST.REGISTER_DOC)
    assert os.path.exists(path), ST.REGISTER_DOC
    body = open(path, encoding="utf-8").read()
    assert ST.RESET_DATE in body
    assert ST.ARCHIVE_PATH in body


def test_a_pre_reset_row_is_counted_as_archived_not_silently_dropped():
    old = _order(alert_id=1)
    new = _order(alert_id=2)
    alerts = {1: _alert(id=1, alert_ts="2026-08-01T10:00:00"),
              2: _alert(id=2, alert_ts="2026-08-14T10:00:00")}
    out = ST.build_rows([old, new], alerts, today=TODAY)
    assert out["n_rows"] == 1, out["n_rows"]
    assert out["n_archived"] == 1, out["n_archived"]
    assert out["rows"][0]["alert_id"] == 2


def test_an_undated_row_counts_as_archived_rather_than_current():
    # Treating "no date" as "after the reset" would let the old record leak back in through
    # exactly the rows whose provenance is least clear.
    o = _order(alert_id=9, created_at=None)
    out = ST.build_rows([o], {9: {"id": 9, "ticker": "AAA"}}, today=TODAY)
    assert out["n_rows"] == 0, out["rows"]
    assert out["n_archived"] == 1


def test_a_row_on_the_reset_date_itself_is_in_the_new_record():
    o = _order(alert_id=3)
    a = {3: _alert(id=3, alert_ts=ST.RESET_DATE + "T09:30:00")}
    out = ST.build_rows([o], a, today=TODAY)
    assert out["n_rows"] == 1, out


# ----------------------------------------------------------------------------------------
# 2. THE FIELDS ARE READ, NOT RECOMPUTED
# ----------------------------------------------------------------------------------------

def test_the_four_fields_don_asked_for_are_read_straight_from_the_order_row():
    out = ST.build_rows([_order()], {1: _alert()}, today=TODAY)
    r = out["rows"][0]
    assert r["entry_premium"] == 2.00
    assert r["target_premium"] == 4.00
    assert r["stop_premium"] == 1.00
    assert r["current_premium"] == 2.50


def test_a_non_default_policy_is_shown_as_stored_and_not_re_derived_to_the_default():
    # THE SESSION-16 TEST. If the display computed `entry x 2.0` it would print 4.00 here and
    # be wrong: this alert's stored target is 3.00. The stored level is the strategy.
    out = ST.build_rows([_order(target_premium=3.00, stop_premium=1.40)],
                        {1: _alert()}, today=TODAY)
    r = out["rows"][0]
    assert r["target_premium"] == 3.00, r["target_premium"]
    assert abs(r["target_pct"] - 0.50) < 1e-9, r["target_pct"]
    assert abs(r["stop_pct"] - (-0.30)) < 1e-9, r["stop_pct"]


def test_the_default_policy_reads_plus_100_and_minus_50_on_the_premium():
    out = ST.build_rows([_order()], {1: _alert()}, today=TODAY)
    r = out["rows"][0]
    assert abs(r["target_pct"] - 1.00) < 1e-9, r["target_pct"]
    assert abs(r["stop_pct"] - (-0.50)) < 1e-9, r["stop_pct"]


def test_a_missing_level_is_none_rather_than_a_guess():
    out = ST.build_rows([_order(target_premium=None, stop_premium=None)],
                        {1: _alert()}, today=TODAY)
    r = out["rows"][0]
    assert r["target_premium"] is None
    assert r["target_pct"] is None
    assert r["stop_pct"] is None


def test_a_closed_row_shows_its_exit_not_a_leftover_mark():
    # Showing a stale mark beside a realised outcome invites a reader to compute a third P&L.
    out = ST.build_rows(
        [_order(state="closed", exit_reason="target", exit_premium=4.10, last_mark=2.50)],
        {1: _alert()}, today=TODAY)
    r = out["rows"][0]
    assert r["current_premium"] == 4.10, r["current_premium"]
    assert abs(r["current_pct"] - 1.05) < 1e-9, r["current_pct"]


# ----------------------------------------------------------------------------------------
# 3. STATUS AND STALENESS
# ----------------------------------------------------------------------------------------

def test_every_status_don_named_is_reachable():
    want = {"LIVE", "HIT TARGET", "STOPPED", "TIME-STOPPED", "EXPIRED"}
    got = {ST.status_for({"state": "open"})}
    for reason in ("target", "stop", "time_stop", "expiry"):
        got.add(ST.status_for({"state": "closed", "exit_reason": reason}))
    assert got == want, got


def test_a_closing_position_is_still_live():
    # An exit order is working but the position is on. Calling it closed books an outcome
    # that has not happened.
    assert ST.status_for({"state": "closing"}) == ST.LIVE


def test_an_unmapped_exit_reason_shows_itself_rather_than_the_nearest_label():
    got = ST.status_for({"state": "closed", "exit_reason": "broker_liquidation"})
    assert got == "BROKER LIQUIDATION", got
    assert got not in ST.STATUS_BY_REASON.values()


def test_a_status_map_that_gains_a_reason_does_not_silently_bucket_it():
    assert set(ST.STATUS_BY_REASON) == {"target", "stop", "time_stop", "expiry"}


def test_an_unmarked_live_position_is_stale_not_fresh():
    age = ST.mark_age(None, TODAY)
    assert age["stale"] is True, age
    assert age["days"] is None
    out = ST.build_rows([_order(last_mark_ts=None)], {1: _alert()}, today=TODAY)
    assert out["rows"][0]["mark_stale"] is True


def test_a_fresh_mark_is_not_flagged_and_an_old_one_is():
    assert ST.mark_age("2026-08-19", TODAY)["stale"] is False
    assert ST.mark_age("2026-08-10", TODAY)["stale"] is True
    o_fresh = ST.build_rows([_order(last_mark_ts="2026-08-19")], {1: _alert()}, today=TODAY)
    o_old = ST.build_rows([_order(last_mark_ts="2026-08-01")], {1: _alert()}, today=TODAY)
    assert o_fresh["rows"][0]["mark_stale"] is False
    assert o_old["rows"][0]["mark_stale"] is True


def test_staleness_does_not_borrow_the_scan_freshness_constant():
    # A quote and a daily scan are different objects on different clocks. Borrowing one
    # constant across two is how MIN_LIVE_DAYS and MIN_DAYS_FOR_MEANING came to govern one
    # track with two numbers.
    # Checked against the CODE: the docstring names the constant precisely in order to
    # explain why it is not used, and reading raw source would flag that explanation.
    code = _module_code()
    assert "WARN_AFTER" not in code, "the scan's freshness constant is used for a quote's age"
    assert "freshness" not in code, "this module should not import the scan freshness module"
    assert isinstance(ST.STALE_MARK_DAYS, int) and ST.STALE_MARK_DAYS > 0


def test_dte_counts_down_and_reports_a_past_expiry_rather_than_clamping():
    assert ST.dte("2026-08-30", TODAY) == 10
    assert ST.dte("2026-08-10", TODAY) == -10, "a past expiry must be visible, not clamped"
    assert ST.dte(None, TODAY) is None


# ----------------------------------------------------------------------------------------
# 4. THE R2 CONTEXT
# ----------------------------------------------------------------------------------------

def test_the_r2_context_is_quoted_from_the_module_that_owns_it():
    out = ST.build_rows([], {}, today=TODAY)
    assert out["context"] == payoff.NOT_A_CLAIM
    assert out["context_source"] == payoff.SOURCE


def test_the_context_still_says_the_entry_signal_lost_to_random_entry():
    out = ST.build_rows([], {}, today=TODAY)
    low = out["context"].lower()
    assert "random entry" in low, out["context"]
    assert "not a demonstrated" in low or "idea generator" in low, out["context"]


def test_the_scream_module_holds_no_second_copy_of_the_r2_number():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = open(os.path.join(here, "valuation", "web", "scream_track.py"), encoding="utf-8")
    code = src.read()
    src.close()
    body = re.sub(r'"""[\s\S]*?"""', " ", code)
    assert "5.06" not in body, "the R2 gap is restated in code instead of quoted from payoff"


# ----------------------------------------------------------------------------------------
# 5. THE SURFACE
# ----------------------------------------------------------------------------------------

def test_the_record_is_owner_only():
    from valuation.saas import surfaces
    assert surfaces.is_owner_only("/api/scream-track"), \
        "a forward performance record naming live contracts must not be public"


def test_the_route_answers_and_carries_its_register_even_when_the_book_is_empty():
    from valuation.web.app import app
    d = app.test_client().get("/api/scream-track").get_json()
    assert d is not None
    assert (d.get("register") or {}).get("reset_date") == ST.RESET_DATE, d.get("register")
    assert "rows" in d


def test_a_broken_read_still_returns_the_register_rather_than_a_bare_error():
    class _Boom:
        def _conn(self):
            raise RuntimeError("db gone")

    out = ST.summary(_Boom(), today=TODAY)
    assert out["unavailable"] is True, out
    assert out["register"]["reset_date"] == ST.RESET_DATE
    assert out["rows"] == []


def test_the_renderer_labels_a_stale_mark_and_does_not_hide_it():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    js = open(os.path.join(here, "valuation", "web", "static", "app.js"),
              encoding="utf-8").read()
    m = re.search(r"function renderScreamTrack\([\s\S]*?\n\}", js)
    assert m, "renderScreamTrack not found"
    body = m.group(0)
    for col in ("entry_premium", "target_premium", "stop_premium", "current_premium"):
        assert col in body, f"{col} is not rendered"
    assert "reg.note" in body, "the register note is not rendered with the table"

    # THE FLAG MUST DRIVE THE BADGE, not merely appear near it. Asserting that the string
    # "mark_stale" occurs somewhere in the function is far too weak: it survives
    # `const stale = false && r.mark_stale`, which renders every stale mark as fresh while
    # keeping the identifier in the file. Found by mutation. So pin the ASSIGNMENT.
    a = re.search(r"const stale\s*=\s*([^\n;]+)", body)
    assert a, "no `stale` assignment in the renderer"
    expr = a.group(1).strip()
    assert expr.startswith("r.mark_stale"), \
        f"the stale badge is not driven directly by the flag: {expr!r}"
    for killer in ("false &&", "true ?", "0 &&"):
        assert killer not in expr, f"the staleness check is short-circuited: {expr!r}"


if __name__ == "__main__":
    print("Scream-buy track record — reset, fields and staleness")
    for _n, _f in sorted(list(globals().items())):
        if _n.startswith("test_") and callable(_f):
            check(_n, _f)
    print(f"\n{len(PASSED)}/{len(PASSED) + len(FAILED)} scream-track tests passed")
    if FAILED:
        for n, e in FAILED:
            print(f"  FAILED {n}: {e}")
        sys.exit(1)
