"""Forward paper-track tests (offline; a fake broker, no network).

Run: python tests/test_paper_track.py

These test the two things that would silently ruin a forward track: submitting a trade that
should not have been submitted (back-filling old alerts, double-submitting on a retry, pointing
at a non-sandbox endpoint), and producing a number that flatters itself (marking one leg of the
index without the other, leaving losers open forever, calling a five-trade book a result).
"""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import options_tracker as OT           # noqa: E402
from valuation.edge import paper_track as PT               # noqa: E402
from valuation.edge.paper_broker import (                  # noqa: E402
    NotSandboxError, PaperBroker, SANDBOX_BASE, assert_sandbox)


# ----------------------------------------------------------------- fixtures
def _store():
    import tempfile
    from valuation.screener.store import Store
    return Store(os.path.join(tempfile.mkdtemp(prefix="valquo_paper_"), "s.db"))


class _Cfg:
    tradier_token = "PRODUCTION-TOKEN"
    tradier_paper_token = "PAPER-TOKEN"
    tradier_paper_account_id = "VA00000000"
    paper_contracts_per_trade = 1


class FakeBroker(PaperBroker):
    """A PaperBroker with the HTTP layer replaced. Everything above it is the real code."""

    def __init__(self, quotes=None, fail_place=False):
        super().__init__(_Cfg(), base=SANDBOX_BASE, token="PAPER-TOKEN",
                         account_id="VA00000000")
        self._q = dict(quotes or {})
        self._orders = {}
        self._next = 100
        self.fail_place = fail_place
        self.placed = []

    def quotes(self, symbols):
        syms = [symbols] if isinstance(symbols, str) else list(symbols or [])
        return {s: self._q[s] for s in syms if s in self._q}

    def _place(self, kind, **kw):
        if self.fail_place:
            return {"ok": False, "http_status": 400, "error": {"errors": "rejected"}}
        self._next += 1
        oid = str(self._next)
        self._orders[oid] = {"id": oid, "status": "open", **kw}
        self.placed.append({"id": oid, "kind": kind, **kw})
        return {"ok": True, "order": {"id": oid, "status": "ok"}, "dry_run": self.dry_run}

    def place_option(self, occ_symbol, underlying, side, quantity, price=None, duration="day"):
        return self._place("option", option_symbol=occ_symbol, symbol=underlying, side=side,
                           quantity=quantity, price=price)

    def place_equity(self, ticker, side, quantity, price=None, duration="day"):
        return self._place("equity", symbol=ticker, side=side, quantity=quantity, price=price)

    def order(self, order_id):
        return self._orders.get(str(order_id), {})

    def orders(self):
        return list(self._orders.values())

    def fill(self, order_id, price):
        o = self._orders[str(order_id)]
        o.update(status="filled", avg_fill_price=price, exec_quantity=o.get("quantity", 1))

    def balances(self):
        return {"total_equity": 100000.0, "total_cash": 100000.0, "account_type": "margin"}


def _alert(store, ticker="AAPL", ts=None, expiry=None, entry=5.0, dte=60):
    """A logged scream-buy alert with a real contract, as options_live now writes them."""
    ts = ts or (dt.date.today().isoformat() + "T14:30:00")
    expiry = expiry or (dt.date.today() + dt.timedelta(days=dte)).isoformat()
    OT.log_alert(store, {
        "alert_ts": ts, "ticker": ticker, "opt_right": "call", "strike": 250.0,
        "expiry": expiry, "entry_premium": entry, "underlying_price": 240.0, "score": 93.0,
        "iv": 0.35, "iv_rank": 45.0, "horizon": "swing", "target_delta": 0.35, "dte": dte,
        "features": {"exit_policy": {"target_pct": 1.00, "stop_pct": -0.50,
                                     "time_stop_frac": 0.50}}})
    return OT.occ_symbol(ticker, expiry, "call", 250.0)


# ----------------------------------------------------------------- the sandbox guard
def test_sandbox_guard_rejects_production_and_lookalikes():
    assert assert_sandbox(SANDBOX_BASE) == SANDBOX_BASE
    for bad in ("https://api.tradier.com/v1",
                "https://api.tradier.com/v1?env=sandbox",       # substring check would pass
                "http://sandbox.tradier.com/v1",                # not https
                "https://sandbox.tradier.com.evil.io/v1",
                "", None):
        try:
            assert_sandbox(bad)
            raise AssertionError(f"accepted a non-sandbox endpoint: {bad!r}")
        except NotSandboxError:
            pass


def test_broker_refuses_missing_or_production_token():
    class NoPaper(_Cfg):
        tradier_paper_token = ""
    try:
        PaperBroker(NoPaper())
        raise AssertionError("constructed with no paper token")
    except NotSandboxError:
        pass

    class Crossed(_Cfg):
        tradier_paper_token = "PRODUCTION-TOKEN"      # same as tradier_token
    try:
        PaperBroker(Crossed())
        raise AssertionError("constructed on the production token")
    except NotSandboxError:
        pass


def test_broker_cannot_be_pointed_at_production():
    try:
        PaperBroker(_Cfg(), base="https://api.tradier.com/v1")
        raise AssertionError("constructed against production")
    except NotSandboxError:
        pass


# ----------------------------------------------------------------- submission discipline
def test_old_alerts_are_not_back_filled():
    """The track's only claim is that it was recorded before the outcome was known."""
    st = _store()
    old = (dt.date.today() - dt.timedelta(days=PT.MAX_ALERT_AGE_DAYS + 5))
    occ = _alert(st, "OLD", ts=old.isoformat() + "T14:30:00")
    b = FakeBroker(quotes={occ: {"bid": 5.0, "ask": 5.2}})
    res = PT.submit_new_alerts(st, b, cfg=_Cfg())
    assert res["submitted"] == 0 and res["skipped"] == 1, res
    assert "back-fill" in res["skips"][0]["reason"]
    assert not b.placed


def test_alert_without_a_contract_is_skipped_not_guessed():
    st = _store()
    OT.log_alert(st, {"alert_ts": dt.date.today().isoformat() + "T10:00:00",
                      "ticker": "NOCHAIN", "score": 91.0, "horizon": "swing"})
    b = FakeBroker()
    res = PT.submit_new_alerts(st, b, cfg=_Cfg())
    assert res["submitted"] == 0 and not b.placed
    assert "no contract" in res["skips"][0]["reason"]


def test_submission_is_idempotent_across_runs():
    st = _store()
    occ = _alert(st)
    b = FakeBroker(quotes={occ: {"bid": 5.0, "ask": 5.2}})
    first = PT.submit_new_alerts(st, b, cfg=_Cfg())
    assert first["submitted"] == 1 and len(b.placed) == 1
    for _ in range(3):
        again = PT.submit_new_alerts(st, b, cfg=_Cfg())
        assert again["submitted"] == 0, again
    assert len(b.placed) == 1, "the same alert was submitted more than once"


def test_interrupted_run_adopts_its_order_instead_of_double_submitting():
    """A crash between placing and recording must not buy the contract twice."""
    st = _store()
    occ = _alert(st)
    b = FakeBroker(quotes={occ: {"bid": 5.0, "ask": 5.2}})
    PT.submit_new_alerts(st, b, cfg=_Cfg())
    rows = PT.paper_orders(st)
    # Simulate the crash: the order is live at the broker but we never recorded its id.
    PT._update(st, rows[0]["alert_id"], state="claimed", entry_order_id=None)
    res = PT.submit_new_alerts(st, b, cfg=_Cfg())
    assert res["adopted"] == 1, res
    assert len(b.placed) == 1, "resuming placed a second order for the same contract"


def test_entry_is_the_ask_not_the_mid():
    """Every validated options number is net of buy-the-ask; paying the mid forward would beat
    the backtest for a reason unrelated to the signal."""
    st = _store()
    occ = _alert(st)
    b = FakeBroker(quotes={occ: {"bid": 4.0, "ask": 6.0}})
    PT.submit_new_alerts(st, b, cfg=_Cfg())
    assert abs(b.placed[0]["price"] - 6.0) < 1e-9, b.placed[0]


def test_a_rejected_entry_is_recorded_not_retried_forever():
    st = _store()
    occ = _alert(st)
    b = FakeBroker(quotes={occ: {"bid": 5.0, "ask": 5.2}}, fail_place=True)
    res = PT.submit_new_alerts(st, b, cfg=_Cfg())
    assert res["rejected"] == 1
    row = PT.paper_orders(st)[0]
    assert row["state"] == "rejected" and "rejected" in (row["note"] or "")


# ----------------------------------------------------------------- marks and exits
def _open_position(entry=5.0, ask=5.0):
    st = _store()
    occ = _alert(st, entry=entry)
    b = FakeBroker(quotes={occ: {"bid": ask - 0.1, "ask": ask}})
    PT.submit_new_alerts(st, b, cfg=_Cfg())
    b.fill(b.placed[0]["id"], ask)
    PT.mark_open(st, b)
    return st, b, occ


def test_marks_actually_reach_the_book():
    """The book sat all-open because nothing fed it marks — this is that gap."""
    st, b, occ = _open_position()
    row = PT.paper_orders(st)[0]
    assert row["state"] == "open" and abs(row["entry_premium"] - 5.0) < 1e-9
    assert row["last_mark"] is not None and row["last_mark_ts"]


def test_target_closes_and_writes_through_record_outcome():
    st, b, occ = _open_position(ask=5.0)
    b._q[occ] = {"bid": 10.4, "ask": 10.6}        # mid 10.5 >= 10.0 target
    PT.mark_open(st, b)
    res = PT.close_matured(st, b)
    assert res["closing"] == 1
    exit_order = [p for p in b.placed if p["side"] == "sell_to_close"][0]
    assert abs(exit_order["price"] - 10.4) < 1e-9, "exit must be at the BID"
    b.fill(exit_order["id"], 10.4)
    res2 = PT.close_matured(st, b)
    assert res2["closed"] == 1 and res2["recorded"] == 1
    sc = OT.scorecard(st)["overall"]
    assert sc["n_closed"] == 1
    assert abs(sc["expectancy_pct"] - (10.4 / 5.0 - 1)) < 1e-9, sc


def test_stop_beats_target_when_both_could_be_read():
    row = {"last_mark": 2.0, "target_premium": 10.0, "stop_premium": 2.5,
           "expiry": "2099-01-01", "time_stop_date": "2099-01-01"}
    assert PT._exit_decision(row, dt.date.today()) == "stop"
    row["last_mark"] = 11.0
    assert PT._exit_decision(row, dt.date.today()) == "target"


def test_time_stop_and_expiry_fire_without_a_mark():
    today = dt.date(2026, 8, 3)
    assert PT._exit_decision({"expiry": "2026-08-04", "time_stop_date": "2099-01-01"},
                             today) == "expiry"
    assert PT._exit_decision({"expiry": "2099-01-01", "time_stop_date": "2026-08-01"},
                             today) == "time_stop"
    assert PT._exit_decision({"expiry": "2099-01-01", "time_stop_date": "2099-01-01"},
                             today) is None


def test_a_losing_trade_cannot_sit_open_when_the_exit_is_rejected():
    """Otherwise the closed-trade statistics quietly survivor-bias toward winners."""
    st, b, occ = _open_position(ask=5.0)
    b._q[occ] = {"bid": 1.0, "ask": 1.2}          # mid 1.1 <= 2.5 stop
    PT.mark_open(st, b)
    b.fail_place = True
    res = PT.close_matured(st, b)
    assert res["closed"] == 1 and res["recorded"] == 1
    sc = OT.scorecard(st)["overall"]
    assert sc["n_closed"] == 1 and sc["expectancy_pct"] < 0
    assert "rejected" in (PT.paper_orders(st)[0]["exit_reason"] or "")


def test_dry_run_places_nothing_live():
    st = _store()
    occ = _alert(st)
    b = FakeBroker(quotes={occ: {"bid": 5.0, "ask": 5.2}})
    b.dry_run = True
    PT.submit_new_alerts(st, b, cfg=_Cfg())
    row = PT.paper_orders(st)[0]
    assert row["state"] == "skipped" and "dry run" in (row["note"] or "")


# ----------------------------------------------------------------- the index book
_BOOK = {"positions": [{"ticker": "AAA", "weight": 0.5}, {"ticker": "BBB", "weight": 0.5}]}


def test_index_tracks_each_name_against_spy_over_its_own_window():
    st = _store()
    b = FakeBroker(quotes={"AAA": {"last": 100.0}, "BBB": {"last": 200.0},
                           "SPY": {"last": 500.0}})
    seed = PT.seed_book(st, b, _BOOK)
    assert seed["added"] == 2 and seed["orders"] == 0, "quote-marked by default"
    b._q = {"AAA": {"last": 110.0}, "BBB": {"last": 210.0}, "SPY": {"last": 525.0}}
    pt = PT.index_point(st, b)
    assert pt["ok"] and pt["n_priced"] == 2
    assert abs(pt["index_ret"] - (0.5 * 0.10 + 0.5 * 0.05)) < 1e-9, pt
    assert abs(pt["bench_ret"] - 0.05) < 1e-9
    assert abs(pt["active_ret"] - 0.025) < 1e-9


def test_reseeding_does_not_reset_accrued_entry_prices():
    st = _store()
    b = FakeBroker(quotes={"AAA": {"last": 100.0}, "BBB": {"last": 200.0},
                           "SPY": {"last": 500.0}})
    PT.seed_book(st, b, _BOOK)
    b._q = {"AAA": {"last": 300.0}, "BBB": {"last": 600.0}, "SPY": {"last": 500.0}}
    again = PT.seed_book(st, b, _BOOK)
    assert again["added"] == 0 and again["held"] == 2
    pt = PT.index_point(st, b)
    assert abs(pt["index_ret"] - 2.0) < 1e-9, "entry prices were reset by the re-seed"


def test_a_name_priced_on_one_leg_only_is_dropped_from_both():
    st = _store()
    b = FakeBroker(quotes={"AAA": {"last": 100.0}, "BBB": {"last": 200.0},
                           "SPY": {"last": 500.0}})
    PT.seed_book(st, b, _BOOK)
    b._q = {"AAA": {"last": 150.0}, "SPY": {"last": 500.0}}      # BBB has no quote today
    pt = PT.index_point(st, b)
    assert pt["n_priced"] == 1
    assert abs(pt["index_ret"] - 0.50) < 1e-9, "the priced name must be re-weighted to 1.0"
    assert abs(pt["bench_ret"] - 0.0) < 1e-9


def test_index_point_is_idempotent_per_day():
    st = _store()
    b = FakeBroker(quotes={"AAA": {"last": 100.0}, "BBB": {"last": 200.0},
                           "SPY": {"last": 500.0}})
    PT.seed_book(st, b, _BOOK)
    for _ in range(3):
        PT.index_point(st, b)
    assert PT.index_summary(st)["n_days"] == 1


def test_equity_mirror_is_opt_in_and_sizes_whole_shares():
    st = _store()
    b = FakeBroker(quotes={"AAA": {"last": 100.0}, "BBB": {"last": 200.0},
                           "SPY": {"last": 500.0}})
    seed = PT.seed_book(st, b, _BOOK, place_equity=True, capital=10000.0)
    assert seed["orders"] == 2
    qty = {p["symbol"]: p["quantity"] for p in b.placed}
    assert qty["AAA"] == 50 and qty["BBB"] == 25       # $5,000 / 100 and / 200


# ----------------------------------------------------------------- honest labelling
def test_a_thin_track_says_so_and_keeps_the_backtest_as_the_headline():
    st = _store()
    occ = _alert(st)
    b = FakeBroker(quotes={occ: {"bid": 5.0, "ask": 5.2}})
    PT.submit_new_alerts(st, b, cfg=_Cfg())
    s = PT.summary(st)
    assert "paper" in s["options"]["label"] and "thin" in s["options"]["label"]
    assert "Backtested expectancy remains the headline" in s["headline"]
    assert s["options"]["meaningful"] is False
    assert s["options"]["min_closed_for_meaning"] == OT.MIN_CLOSED_PER_BUCKET
    assert "delayed" in s["data_caveat"]
    assert "sandbox" in s["venue"].lower()


def test_summary_survives_an_untouched_database():
    """`/api/track` must render before the track has ever run."""
    s = PT.summary(_store())
    assert s["options"]["started"] is False and s["index"]["started"] is False


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
    print(f"\n{passed}/{len(tests)} paper-track tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
