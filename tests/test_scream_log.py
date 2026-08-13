"""Scream-buy record tests — the archive, the status vocabulary, the read-time quote.

Run: python tests/test_scream_log.py

Three things here would each silently ruin the record, and each has a test that fails loudly
rather than a comment asking someone to be careful:

  * a reset that DELETES (the whole point is that it archives);
  * a time stop reported as a hard stop, because "time_stop" contains "stop" — the two mean
    opposite things for expectancy;
  * a current price that gets STORED, which is a price that was current once and lies from the
    moment it is written.
"""
import ast
import datetime as dt
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge import options_tracker as OT           # noqa: E402
from valuation.edge import paper_track as PT               # noqa: E402
from valuation.edge import payload_schema as PS            # noqa: E402
from valuation.edge import scream_log as SL                # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        FAILS.append(name)


def _store():
    from valuation.screener.store import Store
    return Store(os.path.join(tempfile.mkdtemp(prefix="valquo_scream_"), "s.db"))


def _alert(store, ticker="AAPL", ts="2026-08-01T14:30:00", entry=2.00, dte=60,
           expiry="2026-10-16", **kw):
    a = {"alert_ts": ts, "ticker": ticker, "opt_right": "call", "strike": 200.0,
         "expiry": expiry, "entry_premium": entry, "dte": dte, "score": 92.0,
         "horizon": "swing", "underlying_price": 198.0,
         "features": {"exit_policy": {"target_pct": 1.00, "stop_pct": -0.50,
                                      "time_stop_frac": 0.50},
                      "contract_source": "live chain"}}
    a.update(kw)
    return OT.log_alert(store, a)


# =============================== status vocabulary =========================================
def test_status_vocabulary():
    print("\n[status vocabulary]")
    day = dt.date(2026, 9, 1)
    live = {"status": "open", "expiry": "2026-10-16"}
    check("an open, unexpired alert is LIVE",
          SL.display_status(live, today=day) == SL.STATUS_LIVE)

    # THE TRAP: "time_stop" contains "stop". A substring match reports every scheduled close as
    # a stop-out, which inverts what the row says about the strategy.
    ts_row = {"status": "closed", "exit_reason": "time_stop"}
    check("time_stop is TIME-STOPPED, not STOPPED",
          SL.display_status(ts_row, today=day) == SL.STATUS_TIME_STOPPED,
          f"got {SL.display_status(ts_row, today=day)!r}")
    check("stop is STOPPED",
          SL.display_status({"status": "closed", "exit_reason": "stop"},
                            today=day) == SL.STATUS_STOPPED)
    check("target is HIT TARGET",
          SL.display_status({"status": "closed", "exit_reason": "target"},
                            today=day) == SL.STATUS_HIT)
    check("expiry is EXPIRED",
          SL.display_status({"status": "closed", "exit_reason": "expiry"},
                            today=day) == SL.STATUS_EXPIRED)

    # audit B5d appends a provenance suffix to the reason.
    check("a B5d '[pnl vs fill]' suffix does not break the mapping",
          SL.display_status({"status": "closed", "exit_reason": "time_stop [pnl vs fill]"},
                            today=day) == SL.STATUS_TIME_STOPPED)

    # An unmapped reason must NOT read as LIVE — that would put a closed trade back in the book.
    unk = {"status": "closed", "exit_reason": "no entry premium"}
    check("an unmapped close reason is reported, never LIVE",
          SL.display_status(unk, today=day) == SL.STATUS_CLOSED_OTHER)

    # Reachable with NO close-path write at all — the case a stored status field would miss.
    check("an OPEN alert past its expiry reads EXPIRED",
          SL.display_status({"status": "open", "expiry": "2026-08-15"},
                            today=day) == SL.STATUS_EXPIRED)
    check("is_open is False for an expired-but-unclosed alert",
          not SL.is_open({"status": "open", "expiry": "2026-08-15"}, today=day))


def test_every_exit_reason_the_close_path_emits_is_mapped():
    """VACUITY-PROOF: the tokens are enumerated out of `paper_track`'s SOURCE, not listed here.

    A registry-driven check cannot see an unregistered value (M3). So this reads the literal
    strings `_exit_decision` can return and fails if any lacks a status — which is what happens
    the day somebody adds a fifth exit rule.
    """
    print("\n[exit-reason coverage, enumerated from source]")
    src = open(PT.__file__, encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "_exit_decision"), None)
    check("_exit_decision was found in paper_track source", fn is not None)
    if fn is None:
        return
    tokens = sorted({n.value.value for n in ast.walk(fn)
                     if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant)
                     and isinstance(n.value.value, str)})
    # Non-vacuity: if the parse found nothing, the test would pass by seeing nothing.
    check("the enumeration is non-vacuous (found >= 4 exit tokens)", len(tokens) >= 4,
          f"found {tokens}")
    unmapped = [t for t in tokens if t not in SL.EXIT_REASON_TO_STATUS]
    check("every exit reason the close path emits has a display status", not unmapped,
          f"unmapped: {unmapped}")
    check("mapped statuses are all in ALL_STATUSES",
          all(v in SL.ALL_STATUSES for v in SL.EXIT_REASON_TO_STATUS.values()))


# =============================== exit levels ===============================================
def test_levels_are_derived_in_one_place():
    print("\n[exit levels]")
    lv = SL.levels_for(2.00, {"target_pct": 1.00, "stop_pct": -0.50})
    check("target is +100% of entry", lv["target_premium"] == 4.0, lv)
    check("stop is -50% of entry", lv["stop_premium"] == 1.0, lv)

    lv2 = SL.levels_for(3.00, {"target_pct": 0.50, "stop_pct": -0.25})
    check("the alert's OWN policy is honoured, not the default",
          (lv2["target_premium"], lv2["stop_premium"]) == (4.5, 2.25), lv2)

    check("no entry premium yields NO levels rather than zeros", SL.levels_for(None) == {})
    check("a non-positive entry yields no levels", SL.levels_for(0.0) == {})

    # The default is the +100% Don named.
    d = SL.levels_for(1.00, {})
    check("the default target is +100%", d["target_premium"] == 2.0, d)

    # paper_track must not carry a second copy of the arithmetic.
    st = _store()
    aid = _alert(st)
    PT.ensure_schema(st)
    row = {"alert_id": aid}
    check("paper_track._levels_from delegates to the one derivation",
          PT._levels_from(st, row, 2.00) == SL.levels_for(2.00, SL.policy_of({})),
          PT._levels_from(st, row, 2.00))

    psrc = open(PT.__file__, encoding="utf-8").read()
    check("paper_track no longer computes a target inline",
          "1.0 + (policy[" not in psrc and 'policy["target_pct"] or 0' not in psrc)


def test_policy_defaults_only_when_absent():
    print("\n[exit policy]")
    p = SL.policy_of({"features": json.dumps(
        {"exit_policy": {"target_pct": 0.75, "stop_pct": -0.3, "time_stop_frac": 0.4}})})
    check("a logged policy is read back", (p["target_pct"], p["stop_pct"]) == (0.75, -0.3), p)
    check("a logged policy is not flagged default", p["is_default"] is False)
    d = SL.policy_of({"features": None})
    check("a missing policy defaults to +100/-50", (d["target_pct"], d["stop_pct"]) ==
          (OT.DEFAULT_TARGET_PCT, OT.DEFAULT_STOP_PCT), d)
    check("a defaulted policy says so", d["is_default"] is True)
    check("malformed features JSON does not raise",
          SL.policy_of({"features": "{not json"})["target_pct"] == OT.DEFAULT_TARGET_PCT)


# =============================== the record ================================================
def test_record_fields():
    print("\n[record fields]")
    st = _store()
    _alert(st, entry=2.00, dte=60, expiry="2026-10-16")
    recs = SL.records(st, today=dt.date(2026, 9, 1))
    check("one alert produces one record", len(recs) == 1, len(recs))
    r = recs[0]
    check("price bought in is the alert-time premium", r["entry_premium"] == 2.00)
    check("target sale is on the record", r["target_premium"] == 4.00)
    check("stop is on the record", r["stop_premium"] == 1.00)
    check("status is LIVE", r["status"] == SL.STATUS_LIVE)

    # The two DTEs are different quantities and must not be conflated.
    check("dte_at_alert is what was stored", r["dte_at_alert"] == 60)
    check("dte_remaining is measured from today", r["dte_remaining"] == 45,
          r["dte_remaining"])
    check("the two DTEs are genuinely different here",
          r["dte_at_alert"] != r["dte_remaining"])

    check("every declared RECORD_FIELD is present",
          set(SL.RECORD_FIELDS) == set(r), set(SL.RECORD_FIELDS) ^ set(r))
    check("no live-quote field is present before enrichment",
          not any(f in r for f in SL.LIVE_FIELDS))


def test_m6_guard_catches_a_dropped_column():
    print("\n[M6 field-level guard]")
    st = _store()
    _alert(st)
    with st._conn() as c:
        c.execute("ALTER TABLE option_alerts ADD COLUMN newly_computed_thing REAL")
        c.execute("UPDATE option_alerts SET newly_computed_thing = 1.23")
    try:
        SL.records(st, today=dt.date(2026, 9, 1))
        check("an unaccounted stored column fails the run", False, "no error raised")
    except PS.PayloadSchemaError as e:
        check("an unaccounted stored column fails the run",
              "newly_computed_thing" in str(e), str(e)[:120])

    # NON-VACUITY: the guard must be looking at real columns, not passing by seeing nothing.
    with st._conn() as c:
        cur = c.execute("SELECT * FROM option_alerts LIMIT 1")
        row = dict(zip([d[0] for d in cur.description], cur.fetchone()))
    check("the guard inspects a non-trivial number of stored columns", len(row) >= 25, len(row))
    rec = SL.alert_record(row)
    dropped = SL.dropped_record_fields(row, rec)
    check("the guard reports exactly the unaccounted column",
          dropped == ["newly_computed_thing"], dropped)


# =============================== live marks ================================================
def _q(bid, ask, age_seconds, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    ms = int((now - dt.timedelta(seconds=age_seconds)).timestamp() * 1000)
    return {"bid": bid, "ask": ask, "bid_date": ms, "ask_date": ms}


def test_live_marks_are_read_time_and_stale_marked():
    print("\n[live marks]")
    now = dt.datetime.now(dt.timezone.utc)
    rec = {"occ_symbol": "AAPL261016C00200000", "entry_premium": 2.00,
           "status": SL.STATUS_LIVE}

    fresh = SL.attach_live_marks([rec], {"AAPL261016C00200000": _q(2.9, 3.1, 30, now)},
                                 now=now)[0]
    check("a fresh quote gives a current premium", fresh["current_premium"] == 3.0,
          fresh["current_premium"])
    check("a fresh quote is not stale", fresh["current_premium_stale"] is False)
    check("live P&L is computed from entry", abs(fresh["pnl_pct_live"] - 0.5) < 1e-9,
          fresh["pnl_pct_live"])

    old = SL.attach_live_marks([rec], {"AAPL261016C00200000": _q(2.9, 3.1, 3600, now)},
                               now=now)[0]
    check("an hour-old quote is marked stale", old["current_premium_stale"] is True)
    check("a stale quote still reports its price", old["current_premium"] == 3.0)

    none = SL.attach_live_marks([rec], {}, now=now)[0]
    check("a missing quote gives no price", none["current_premium"] is None)
    check("a missing quote is stale, never fresh", none["current_premium_stale"] is True)
    check("a missing quote gives no live P&L", none["pnl_pct_live"] is None)
    check("a missing quote says it is unavailable",
          none["current_premium_source"] == "unavailable")

    # Tradier reports epoch MILLISECONDS. Reading them as seconds dates every quote to 1970.
    check("millisecond timestamps are not read as 1970",
          fresh["current_premium_age_seconds"] is not None
          and fresh["current_premium_age_seconds"] < 120,
          fresh["current_premium_age_seconds"])
    check("the quote timestamp round-trips to this century",
          str(fresh["current_premium_ts"]).startswith("20"), fresh["current_premium_ts"])

    # A quote with no timestamp at all must read STALE, not fresh.
    nots = SL.attach_live_marks([rec], {"AAPL261016C00200000": {"bid": 1, "ask": 2}},
                                now=now)[0]
    check("a quote with no timestamp is stale", nots["current_premium_stale"] is True)


def test_current_price_is_never_persisted():
    print("\n[current price is not stored]")
    st = _store()
    _alert(st)
    now = dt.datetime.now(dt.timezone.utc)
    recs = SL.records(st, today=dt.date(2026, 9, 1))
    SL.attach_live_marks(recs, {r["occ_symbol"]: _q(9.0, 9.2, 10, now) for r in recs}, now=now)
    with st._conn() as c:
        cols = {r[1] for r in c.execute("PRAGMA table_info(option_alerts)").fetchall()}
    leaked = sorted(set(SL.LIVE_FIELDS) & cols)
    check("no live-quote field became a stored column", not leaked, leaked)
    check("nothing wrote a mark onto the row",
          "current_premium" not in cols and "last_mark" not in cols)


# =============================== archive + reset ===========================================
def test_reset_archives_and_never_deletes():
    print("\n[archive + reset]")
    st = _store()
    for i in range(3):
        _alert(st, ticker=f"TCK{i}", ts=f"2026-08-0{i + 1}T14:30:00")
    out = tempfile.mkdtemp(prefix="valquo_arch_")

    before = SL.records(st, today=dt.date(2026, 9, 1))
    check("three alerts are in the record before the reset", len(before) == 3, len(before))

    man = SL.reset_record(st, out, as_of="2026-08-13")
    check("the archive file exists", os.path.exists(man["path"]), man["path"])
    check("the manifest counts every row", man["n_rows"] == 3, man)

    payload = json.load(open(man["path"], encoding="utf-8"))
    check("the archive holds every row", len(payload["rows"]) == 3)
    check("the archive holds full rows, not summaries",
          "entry_premium" in payload["rows"][0] and "features" in payload["rows"][0])

    # NOTHING DELETED.
    with st._conn() as c:
        n = c.execute("SELECT COUNT(*) FROM option_alerts").fetchone()[0]
    check("the reset deleted nothing", n == 3, n)

    # The prior record is still queryable as its own epoch.
    prior = SL.records(st, epoch=SL.EPOCH_ORIGINAL, today=dt.date(2026, 9, 1))
    check("the prior record is still queryable", len(prior) == 3, len(prior))

    # The current record is empty and the new epoch is live.
    now_recs = SL.records(st, today=dt.date(2026, 9, 1))
    check("the current record starts empty", len(now_recs) == 0, len(now_recs))
    check("the epoch moved", SL.current_epoch(st) == "reset-2026-08-13", SL.current_epoch(st))

    # A new alert lands in the NEW epoch.
    _alert(st, ticker="NEW", ts="2026-08-14T14:30:00")
    after = SL.records(st, today=dt.date(2026, 9, 1))
    check("a new alert joins the new epoch", len(after) == 1 and after[0]["ticker"] == "NEW",
          after)
    check("the prior record is unchanged by the new alert",
          len(SL.records(st, epoch=SL.EPOCH_ORIGINAL, today=dt.date(2026, 9, 1))) == 3)


def test_register_note_matches_dons_wording():
    print("\n[register note]")
    st = _store()
    _alert(st)
    out = tempfile.mkdtemp(prefix="valquo_arch_")
    man = SL.reset_record(st, out, as_of="2026-08-13")
    note = man["note"]
    for frag in ("record reset 2026-08-13 at Don's direction",
                 "prior record archived at",
                 "reason: predates the corrected alert stack (B1 price basis, C-series fixes)",
                 "lacked entry/target/current fields"):
        check(f"the note carries {frag[:38]!r}", frag in note, note)
    summary = SL.record_summary(st)
    check("the footer can read the note without the file",
          summary["reset"] and summary["reset"]["note"] == note)
    check("the footer reports the prior-epoch count", summary["n_prior_epochs"] == 1,
          summary)
    check("the footer reports the current-epoch count", summary["n_current_epoch"] == 0,
          summary)


def test_a_second_reset_does_not_overwrite_the_first_archive():
    print("\n[archive is never overwritten]")
    st = _store()
    _alert(st, ticker="ONE")
    out = tempfile.mkdtemp(prefix="valquo_arch_")
    m1 = SL.reset_record(st, out, as_of="2026-08-13")
    _alert(st, ticker="TWO", ts="2026-08-14T10:00:00")
    m2 = SL.reset_record(st, out, as_of="2026-08-13")
    check("the second archive is a different file", m1["path"] != m2["path"],
          (m1["path"], m2["path"]))
    check("the first archive still exists", os.path.exists(m1["path"]))
    p1 = json.load(open(m1["path"], encoding="utf-8"))
    check("the first archive still holds its own row count", p1["n_rows"] == 1, p1["n_rows"])
    check("the second archive holds both rows", m2["n_rows"] == 2, m2)
    hist = st.get_meta(SL.META_ARCHIVES) or []
    check("both resets are in the register history", len(hist) == 2, len(hist))


def test_a_failed_archive_leaves_the_record_untouched():
    """FAIL-CLOSED: no archive, no reset. The other order is the silent wipe."""
    print("\n[fail-closed]")
    st = _store()
    _alert(st)
    epoch_before = SL.current_epoch(st)
    # A path that cannot be created: an existing FILE used as the output directory.
    bad_dir = os.path.join(tempfile.mkdtemp(prefix="valquo_arch_"), "not_a_dir")
    with open(bad_dir, "w", encoding="utf-8") as fh:
        fh.write("x")
    raised = False
    try:
        SL.reset_record(st, bad_dir, as_of="2026-08-13")
    except Exception:                                                    # noqa: BLE001
        raised = True
    check("an unwritable archive raises", raised)
    check("the epoch did not move", SL.current_epoch(st) == epoch_before,
          SL.current_epoch(st))
    check("the record is still readable in its original epoch",
          len(SL.records(st, today=dt.date(2026, 9, 1))) == 1)


def test_epoch_of_null_is_the_original_record():
    print("\n[epoch defaults]")
    st = _store()
    _alert(st)
    SL.ensure_schema(st)
    with st._conn() as c:
        c.execute("UPDATE option_alerts SET record_epoch = NULL")
    check("a NULL epoch reads as the original record",
          SL.epoch_of({"record_epoch": None}) == SL.EPOCH_ORIGINAL)
    check("a pre-existing row is still in the record",
          len(SL.records(st, today=dt.date(2026, 9, 1))) == 1)


def test_live_quotes_only_asks_for_open_contracts():
    print("\n[quote fan-out]")
    asked = {}

    class _B:
        def quotes(self, syms):
            asked["syms"] = list(syms)
            return {}

    recs = [{"occ_symbol": "A", "status": SL.STATUS_LIVE},
            {"occ_symbol": "B", "status": SL.STATUS_EXPIRED},
            {"occ_symbol": "C", "status": SL.STATUS_HIT}]
    SL.live_quotes_for(recs, broker=_B())
    check("only LIVE contracts are quoted", asked.get("syms") == ["A"], asked)

    class _Boom:
        def quotes(self, syms):
            raise RuntimeError("broker down")

    check("a quote outage degrades rather than raising",
          SL.live_quotes_for(recs, broker=_Boom()) == {})


if __name__ == "__main__":
    test_status_vocabulary()
    test_every_exit_reason_the_close_path_emits_is_mapped()
    test_levels_are_derived_in_one_place()
    test_policy_defaults_only_when_absent()
    test_record_fields()
    test_m6_guard_catches_a_dropped_column()
    test_live_marks_are_read_time_and_stale_marked()
    test_current_price_is_never_persisted()
    test_reset_archives_and_never_deletes()
    test_register_note_matches_dons_wording()
    test_a_second_reset_does_not_overwrite_the_first_archive()
    test_a_failed_archive_leaves_the_record_untouched()
    test_epoch_of_null_is_the_original_record()
    test_live_quotes_only_asks_for_open_contracts()
    print("\n" + ("ALL SCREAM-LOG TESTS PASSED" if not FAILS
                  else f"{len(FAILS)} FAILED: {FAILS}"))
    sys.exit(1 if FAILS else 0)
