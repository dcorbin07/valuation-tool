"""MA36 + MA37 — the live options record is censored at one end and blended at the other.

Run: python tests/test_ma36_ma37_record_integrity.py

Registered in `PREREG_ma36_ma37_record_integrity.md`, committed alone before any repair existed.
Both items are HIGH in `VALQUO_MASTER_AUDIT_ULTIMATE.md` section 3 and both are about the record
rather than the strategy:

  MA36 a long option that decays to NO BID after expiry deferred forever, so the -100% tail was
       dropped while winners and quoted losers were scored. One-sided censoring in the project's
       #1 remaining validation.
  MA37 `record_epoch` was stamped on every row and read as a filter by `scream_log` alone, so
       the expectancy on every other surface — and the TUNING LOOP — blended an era the project
       formally retired.

The controls C1-C6 of the register are the tests named `*_control_*` below.
"""
import datetime as dt
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge import options_paper as OP             # noqa: E402
from valuation.edge import options_tracker as OT           # noqa: E402
from valuation.edge import paper_track as PT               # noqa: E402
from valuation.edge import scream_log as SL                # noqa: E402
from valuation.edge.paper_broker import PaperBroker, SANDBOX_BASE   # noqa: E402

STRIKE = 250.0


def _store():
    from valuation.screener.store import Store
    return Store(os.path.join(tempfile.mkdtemp(prefix="valquo_ma36_"), "s.db"))


class _Cfg:
    tradier_token = "PRODUCTION-TOKEN"
    tradier_paper_token = "PAPER-TOKEN"
    tradier_paper_account_id = "VA00000000"
    paper_contracts_per_trade = 1


class FakeBroker(PaperBroker):
    def __init__(self, quotes=None):
        super().__init__(_Cfg(), base=SANDBOX_BASE, token="PAPER-TOKEN",
                         account_id="VA00000000")
        self._q = dict(quotes or {})
        self._orders = {}
        self._next = 100
        self.placed = []

    def quotes(self, symbols):
        syms = [symbols] if isinstance(symbols, str) else list(symbols or [])
        return {s: self._q[s] for s in syms if s in self._q}

    def _place(self, kind, **kw):
        self._next += 1
        oid = str(self._next)
        self._orders[oid] = {"id": oid, "status": "open", **kw}
        self.placed.append(self._orders[oid])
        return {"ok": True, "order": {"id": oid, "status": "ok"}}

    def place_option(self, occ_symbol, underlying, side, quantity, price=None, duration="day"):
        return self._place("option", option_symbol=occ_symbol, side=side, price=price)

    def place_equity(self, ticker, side, quantity, price=None, duration="day"):
        return self._place("equity", symbol=ticker, side=side, price=price)

    def order(self, order_id):
        return self._orders.get(str(order_id), {})

    def fill(self, order_id, price):
        o = self._orders[str(order_id)]
        o.update(status="filled", avg_fill_price=price, exec_quantity=1)


def _alert(store, ticker="AAPL", expiry=None, entry=5.0, ts=None):
    expiry = expiry or (dt.date.today() + dt.timedelta(days=30)).isoformat()
    OT.log_alert(store, {
        "alert_ts": ts or (dt.date.today().isoformat() + "T14:30:00"),
        "ticker": ticker, "opt_right": "call", "strike": STRIKE, "expiry": expiry,
        "entry_premium": entry, "underlying_price": 240.0, "score": 93.0, "iv": 0.35,
        "iv_rank": 45.0, "horizon": "swing", "target_delta": 0.35, "dte": 30,
        "features": {"exit_policy": {"target_pct": 1.00, "stop_pct": -0.50,
                                     "time_stop_frac": 0.50}}})
    return OT.occ_symbol(ticker, expiry, "call", STRIKE)


# The contract must be LIVE when the position is opened — `submit_new_alerts` will not buy an
# already-expired contract, and rightly so. Expiry is therefore always in the future here and
# time is advanced by passing a later `today` to `close_matured`, which is how it happens in
# reality: the position is opened, and then the contract dies underneath it.
EXPIRY = (dt.date.today() + dt.timedelta(days=30))


def _open_position(expiry=None, entry=5.0, ticker="AAPL"):
    """An OPEN paper position on a contract expiring on `expiry` (default: 30 days out)."""
    st = _store()
    occ = _alert(st, ticker=ticker, expiry=(expiry or EXPIRY).isoformat(), entry=entry)
    b = FakeBroker(quotes={occ: {"bid": entry - 0.1, "ask": entry}})
    PT.submit_new_alerts(st, b, cfg=_Cfg())
    b.fill(b.placed[0]["id"], entry)
    PT.mark_open(st, b)
    assert PT.paper_orders(st)[0]["state"] == "open"
    return st, b, occ


def _dead(b, occ, underlying):
    """The contract stops being quoted; the underlying still is."""
    b._q.pop(occ, None)
    if underlying is not None:
        b._q["AAPL"] = {"bid": underlying, "ask": underlying + 0.1}


# =============================== MA36 — the censored tail ====================================
def test_ma36_a_worthless_expired_position_is_settled_at_minus_100_and_not_stranded():
    """THE DEFECT ITSELF. A dead contract has no quote, so the B5-lesser no-bid branch deferred
    it every cycle forever; `_stats` counts `status='closed'` only, so the total loss was not a
    loser, it was ABSENT. The backtest this book validates posts -100% for the same event."""
    st, b, occ = _open_position()
    _dead(b, occ, 200.0)                            # dead contract; underlying BELOW the 250 strike
    later = EXPIRY + dt.timedelta(days=10)          # ten days after it expired

    res = PT.close_matured(st, b, today=later)
    assert res["closed"] == 1 and res["recorded"] == 1, res
    assert res.get("expired_worthless") == 1, res
    assert not res.get("deferred_no_bid"), "it must not ALSO be counted as a defer"

    sc = OT.scorecard(st)["overall"]
    assert sc["n_closed"] == 1, sc
    assert abs(sc["expectancy_pct"] - (-1.0)) < 1e-12, sc["expectancy_pct"]
    row = PT.paper_orders(st)[0]
    assert row["state"] == "closed" and abs(row["exit_premium"] - 0.0) < 1e-12
    assert "expired worthless" in (row["exit_reason"] or "")
    assert "MA36" in (row["exit_reason"] or "")


def test_ma36_control_C3_before_expiry_a_no_bid_position_STILL_DEFERS():
    """C3. B5-lesser is not being reversed. Inside CLOSE_BEFORE_EXPIRY_DAYS the contract is
    alive and carries time value, so settling it at intrinsic would book a loss the market never
    charged. The register makes the test STRICTLY `today > expiry` for exactly this reason."""
    st, b, occ = _open_position()
    _dead(b, occ, 200.0)
    day = EXPIRY - dt.timedelta(days=1)              # inside the 2-day window, NOT past

    assert PT._exit_decision(PT.paper_orders(st)[0], day) == "expiry"
    res = PT.close_matured(st, b, today=day)
    assert res["closed"] == 0 and res.get("deferred_no_bid") == 1, res
    assert PT.paper_orders(st)[0]["state"] == "open"
    assert OT.scorecard(st)["overall"]["n_closed"] == 0


def test_ma36_on_the_expiry_day_itself_it_is_not_yet_settled():
    """The boundary. `day <= exp` defers; only a day strictly past expiry settles."""
    st, b, occ = _open_position()
    _dead(b, occ, 200.0)
    assert PT.close_matured(st, b, today=EXPIRY)["closed"] == 0
    # ...and one day later it does settle, on the identical row.
    assert PT.close_matured(st, b, today=EXPIRY + dt.timedelta(days=1))["closed"] == 1


def test_ma36_control_C4_an_in_the_money_expiry_is_BLOCKED_not_settled_at_zero():
    """C4. The guard can only ever PREVENT an automatic -100%, so it cannot manufacture a loss.
    An expired-but-ITM contract is not the worthless case; a human gets a named anomaly."""
    st, b, occ = _open_position()
    _dead(b, occ, 300.0)                             # ABOVE the 250 strike

    res = PT.close_matured(st, b, today=EXPIRY + dt.timedelta(days=10))
    assert res["closed"] == 0, res
    blocked = res.get("settlement_blocked") or []
    assert len(blocked) == 1 and blocked[0]["ticker"] == "AAPL", res
    assert "IN THE MONEY" in blocked[0]["why"]
    assert PT.paper_orders(st)[0]["state"] == "open"
    assert OT.scorecard(st)["overall"]["n_closed"] == 0
    assert "BLOCKED" in (PT.paper_orders(st)[0]["note"] or "")


def test_ma36_no_underlying_quote_blocks_rather_than_ASSUMING_worthless():
    """A dead feed and a worthless option look identical from the option quote alone. Guessing
    -100% because a data source is down would be a fabricated loss."""
    st, b, occ = _open_position()
    _dead(b, occ, None)                              # no option quote AND no underlying quote
    res = PT.close_matured(st, b, today=EXPIRY + dt.timedelta(days=10))
    assert res["closed"] == 0
    assert "underlying quote unavailable" in (res["settlement_blocked"][0]["why"])


def test_ma36_a_non_expiry_reason_with_no_bid_is_untouched_by_this_repair():
    """Scope. A stop that cannot be filled still defers — the class is NOT closed, and saying so
    in a test stops the next reader believing it is."""
    st, b, occ = _open_position(dt.date.today() + dt.timedelta(days=90))
    b._q[occ] = {"bid": 1.0, "ask": 1.2}             # mid 1.1 <= 2.5 stop -> reason 'stop'
    PT.mark_open(st, b)
    b._q[occ] = {"bid": 0.0, "ask": 0.4}             # ...and now no bid
    res = PT.close_matured(st, b, today=dt.date.today())
    assert res["closed"] == 0 and res.get("deferred_no_bid") == 1, res
    assert not res.get("expired_worthless")


def test_ma36_control_C6_a_zero_exit_premium_yields_exactly_minus_one():
    """C6. The whole repair rests on `record_outcome` treating 0.0 as a PRICE and not as
    missing. Its guard is `if ex is None`, so a falsy-but-valid zero passes — pinned here
    because a `if not exit_premium` anywhere upstream would silently drop every total loss."""
    st = _store()
    _alert(st, entry=4.0)
    aid = OT.open_alerts(st)[0]["id"]
    assert OT.record_outcome(st, alert_id=aid, exit_premium=0.0, exit_ts="2026-08-14T20:00:00",
                             exit_reason="expiry", entry_premium=4.0) is True
    sc = OT.scorecard(st)["overall"]
    assert sc["n_closed"] == 1 and abs(sc["expectancy_pct"] + 1.0) < 1e-12


def test_ma36_control_C1_a_row_that_was_already_closed_is_never_re_touched():
    """C1 (GATES). The repair may only ever act on rows that were `open`."""
    st, b, occ = _open_position()
    _dead(b, occ, 200.0)
    later = EXPIRY + dt.timedelta(days=10)
    PT.close_matured(st, b, today=later)
    before = OT.scorecard(st)["overall"]
    # Run it again, twice. A settled row must not be settled a second time.
    for _ in range(2):
        res = PT.close_matured(st, b, today=later)
        assert res["closed"] == 0 and not res.get("expired_worthless"), res
    assert OT.scorecard(st)["overall"] == before


def test_ma36_the_settlement_basis_is_recorded_on_the_row_not_left_to_be_inferred():
    """A -100% that cannot be explained afterwards is a number nobody can audit."""
    st, b, occ = _open_position()
    _dead(b, occ, 200.0)
    PT.close_matured(st, b, today=EXPIRY + dt.timedelta(days=7))
    reason = PT.paper_orders(st)[0]["exit_reason"] or ""
    for piece in ("expired worthless", "7d past expiry", "settled at 0.00", "MA36", "250.0"):
        assert piece in reason, (piece, reason)


def test_ma36_the_restatement_is_DATED_and_keeps_the_figure_it_replaced():
    """Settling the censored tail RESTATES a published number. A restatement that keeps no
    record of what it replaced is indistinguishable from the figure having always been that —
    so the archive convention `scream_log` sets for the record is applied to the statistic."""
    st, b, occ = _open_position()
    # A closed WINNER first, so the pre-restatement expectancy is not itself -100%.
    _alert(st, ticker="WIN", entry=2.0, ts="2026-08-01T14:30:00")
    aid = [a for a in OT.open_alerts(st) if a["ticker"] == "WIN"][0]["id"]
    OT.record_outcome(st, alert_id=aid, exit_premium=4.0, exit_ts="2026-08-02T20:00:00",
                      exit_reason="target", entry_premium=2.0)
    assert abs(OT.scorecard(st)["overall"]["expectancy_pct"] - 1.0) < 1e-12

    _dead(b, occ, 200.0)
    later = EXPIRY + dt.timedelta(days=3)
    PT.close_matured(st, b, today=later)

    rs = PT.restatements(st)
    assert len(rs) == 1, rs
    r = rs[0]
    assert r["as_of"] == later.isoformat()
    assert r["n_settled"] == 1 and r["settled"][0]["ticker"] == "AAPL"
    assert r["settled"][0]["days_past_expiry"] == 3
    assert r["n_closed_before"] == 1 and r["n_closed_after"] == 2
    assert abs(r["expectancy_before"] - 1.0) < 1e-12
    assert abs(r["expectancy_after"] - 0.0) < 1e-12          # +100% and -100% average to zero
    # THE DIRECTION IS THE POINT: the repair can only ever ADD -100% trades.
    assert r["expectancy_after"] < r["expectancy_before"]
    assert "MA36" in r["note"]
    assert PT.options_summary(st)["restatements"] == rs


def test_ma36_a_cycle_that_settles_nothing_writes_no_restatement():
    """A dated note per cycle would turn the record into noise and make a real restatement
    invisible among them."""
    st, b, occ = _open_position()
    assert PT.close_matured(st, b, today=dt.date.today())["closed"] == 0
    assert PT.restatements(st) == []
    assert PT.options_summary(st)["restatements"] == []


# =============================== MA37 — the blended eras =====================================
def _two_era_store():
    """One closed WINNER in the archived era, one closed LOSER in the current era."""
    st = _store()
    _alert(st, ticker="OLD", entry=2.0, ts="2026-07-01T14:30:00")
    aid = OT.open_alerts(st)[0]["id"]
    OT.record_outcome(st, alert_id=aid, exit_premium=4.0, exit_ts="2026-07-05T20:00:00",
                      exit_reason="target", entry_premium=2.0)          # +100%
    SL.reset_record(st, tempfile.mkdtemp(prefix="valquo_arch_"), as_of="2026-08-13")
    _alert(st, ticker="NEW", entry=2.0, ts="2026-08-14T14:30:00")
    aid2 = [a for a in OT.open_alerts(st) if a["ticker"] == "NEW"][0]["id"]
    OT.record_outcome(st, alert_id=aid2, exit_premium=1.0, exit_ts="2026-08-14T20:00:00",
                      exit_reason="stop", entry_premium=2.0)            # -50%
    return st


def test_ma37_the_scorecard_is_scoped_to_the_CURRENT_era_by_default():
    """THE DEFECT. `SELECT * FROM option_alerts WHERE status='closed'` with no epoch clause, so
    a record the project retired for predating the corrected alert stack still drove the number
    every user sees."""
    st = _two_era_store()
    sc = OT.scorecard(st)
    assert sc["record_epoch"] == "reset-2026-08-13", sc["record_epoch"]
    assert sc["overall"]["n_closed"] == 1
    assert abs(sc["overall"]["expectancy_pct"] - (-0.5)) < 1e-12, sc["overall"]


def test_ma37_control_C5_the_BLEND_is_still_computable_and_is_the_old_number():
    """C5. The old figure was FILTERED, never lost — which is what makes this a scope change
    and not a deletion. +100% and -50% average to +25%: the blend the surfaces used to show."""
    st = _two_era_store()
    blended = OT.scorecard(st, epoch=OT.EPOCH_ALL)["overall"]
    assert blended["n_closed"] == 2
    assert abs(blended["expectancy_pct"] - 0.25) < 1e-12, blended["expectancy_pct"]
    # ...and it differs materially from the default, i.e. the repair is not cosmetic.
    assert abs(blended["expectancy_pct"] - OT.scorecard(st)["overall"]["expectancy_pct"]) > 0.01


def test_ma37_the_archived_era_is_EXCLUDED_but_never_INVISIBLE():
    """`scream_log`'s first principle is that a reset is an archive, never a delete. Filtering an
    era out of a statistic without saying it exists would honour the letter and not the point."""
    st = _two_era_store()
    for payload in (OT.scorecard(st), OP.paper_report(st), OT.tuning_candidates(st)):
        eras = payload["epochs"]
        assert eras.get("original") == 1 and eras.get("reset-2026-08-13") == 1, eras
        assert payload["record_epoch"] == "reset-2026-08-13"


def test_ma37_control_C2_filtering_deletes_nothing_and_moves_no_row_between_eras():
    """C2 (GATES). MA37 is a filter. If it were a purge this test would fail."""
    st = _two_era_store()
    before = OT.epoch_census(st)
    for _ in range(3):
        OT.scorecard(st)
        OP.paper_report(st)
        OT.tuning_candidates(st)
        OT.scorecard(st, epoch=OT.EPOCH_ALL)
    assert OT.epoch_census(st) == before == {"original": 1, "reset-2026-08-13": 1}


def test_ma37_paper_report_live_since_does_not_come_from_the_archived_era():
    """The more misleading half of the blend: `live_since = min(alert_ts)` over EVERY row made
    the live book look older than it is by dating it from a record that had been retired."""
    st = _two_era_store()
    r = OP.paper_report(st)
    assert r["live_since"].startswith("2026-08-14"), r["live_since"]
    assert r["n_logged"] == 1 and r["n_closed"] == 1
    assert OP.paper_report(st, epoch=OT.EPOCH_ALL)["live_since"].startswith("2026-07-01")


def test_ma37_the_tuning_loop_learns_only_from_the_current_era():
    """The consumer that matters most: it PROPOSES which fingerprints to favour. A suggestion
    resting on retired rows is the defect, not the display."""
    st = _two_era_store()
    tc = OT.tuning_candidates(st)
    assert tc["record_epoch"] == "reset-2026-08-13"
    # Both eras' rows are far below MIN_CLOSED_PER_BUCKET, so nothing is actionable either way -
    # what is pinned is WHICH rows were considered, not the verdict.
    assert tc["ready"] is False
    considered = {b["bucket"] for b in tc["blocked"]}
    assert "swing" in considered
    assert all(b["n_closed"] <= 1 for b in tc["blocked"]), tc["blocked"]


def test_ma37_an_untouched_database_reports_the_original_era_and_does_not_crash():
    """A store that has never been reset has no META_EPOCH and NULL in every `record_epoch`;
    a NULL IS the original record, never 'unknown'."""
    st = _store()
    _alert(st)
    assert OT.scorecard(st)["record_epoch"] == SL.EPOCH_ORIGINAL
    assert OT.epoch_census(st) == {SL.EPOCH_ORIGINAL: 1}
    assert OP.paper_report(st)["n_logged"] == 1


def test_ma37_the_default_is_the_current_era_and_that_is_pinned_against_a_silent_widening():
    """Void condition 5 of the register: the default may not be widened when the current era is
    thin. A store whose current era holds NOTHING must report nothing, not fall back to the
    blend — 'no live alerts logged yet' is the honest state."""
    st = _store()
    _alert(st, ticker="OLD", entry=2.0, ts="2026-07-01T14:30:00")
    aid = OT.open_alerts(st)[0]["id"]
    OT.record_outcome(st, alert_id=aid, exit_premium=9.0, exit_ts="2026-07-05T20:00:00",
                      exit_reason="target", entry_premium=2.0)
    SL.reset_record(st, tempfile.mkdtemp(prefix="valquo_arch_"), as_of="2026-08-13")
    r = OP.paper_report(st)
    assert r["n_logged"] == 0 and r["n_closed"] == 0
    assert r["live"]["expectancy_pct"] is None, r["live"]
    assert r["label"] == "no live alerts logged yet"
    assert r["epochs"].get("original") == 1, "the archived row must still be visible"


def _main():
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    bad = 0
    for name, fn in fns:
        try:
            fn()
            print("  PASS  %s" % name)
        except Exception as e:                                       # noqa: BLE001
            bad += 1
            print("  FAIL  %s: %s: %s" % (name, type(e).__name__, e))
    print("\n%d/%d MA36+MA37 record-integrity tests passed" % (len(fns) - bad, len(fns)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(_main())
