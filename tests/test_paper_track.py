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
from valuation.saas import recap as RC                     # noqa: E402


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


def test_dry_run_places_nothing_live_and_does_not_burn_the_alert():
    """AUDIT B5b. A dry run placed nothing but wrote state='skipped' — and skipped alerts are
    PERMANENTLY excluded from the live track. So any alert a preview happened to touch could
    never enter the real book afterwards, silently and forever, in the one instrument the
    project has that runs on unseen data. A preview is a no-op; the row goes back to the queue."""
    st = _store()
    occ = _alert(st)
    b = FakeBroker(quotes={occ: {"bid": 5.0, "ask": 5.2}})
    b.dry_run = True
    PT.submit_new_alerts(st, b, cfg=_Cfg())
    row = PT.paper_orders(st)[0]
    assert "dry run" in (row["note"] or "")
    assert row["state"] != "skipped", "a preview must not permanently exclude the alert"
    assert row["state"] == "pending"

    # and a real run afterwards can still take it
    b.dry_run = False
    PT.submit_new_alerts(st, b, cfg=_Cfg())
    assert PT.paper_orders(st)[0]["state"] in ("claimed", "submitted", "open")


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


def test_a_day_count_alone_can_never_make_the_index_track_meaningful():
    """The SECOND ungated door, found by audit OOB5 after it closed the first.

    `index_track` was gated on the contract's operational gate, but `hero` falls back to
    `paper_track.index_summary` when the Cowork tracker files are absent -- which is exactly the
    fresh-deploy case, since `data/` is gitignored. If `meaningful` were a pure day count, a
    paper track could still lead the page on elapsed time alone, defeating the gate one layer
    down. `meaningful` therefore requires BOTH, and this pins that the day count alone is never
    enough at any n.
    """
    st = _store()
    b = FakeBroker(quotes={"AAA": {"last": 100.0}, "BBB": {"last": 200.0},
                           "SPY": {"last": 500.0}})
    PT.seed_book(st, b, _BOOK)
    with st._conn() as c:
        rows = [(f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}", 0.05, 0.01, 0.04, 2, 2,
                 "2026-01-01") for i in range(PT.MIN_DAYS_FOR_MEANING + 40)]
        c.executemany(
            "INSERT OR REPLACE INTO paper_index_track"
            " (as_of, index_ret, bench_ret, active_ret, n_positions, n_priced, inception)"
            " VALUES (?,?,?,?,?,?,?)", rows)
    out = PT.index_summary(st)
    assert out["n_days"] >= PT.MIN_DAYS_FOR_MEANING, out["n_days"]
    # The real contract on disk records the gate as pending, so this must be False.
    assert out["contract_gate"]["passed"] is False, out["contract_gate"]
    assert out["meaningful"] is False, "a day count alone promoted a paper track"


def test_the_index_gate_fails_closed_when_the_contract_cannot_be_read():
    """Any failure reaching the gate must resolve to NOT passed, never to passed."""
    import valuation.screener.index_track as IT
    orig = IT.gate_state
    try:
        IT.gate_state = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        g = PT._contract_gate()
    finally:
        IT.gate_state = orig
    assert g["passed"] is False
    assert "unreadable" in g["reason"]


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


# ----------------------------------------------------------------- the Discord recap
# These test the thing a recap gets wrong: reporting an empty or one-trade book as if it were
# a measured result, and losing the disclaimers to a message-length limit.
class _RecapCfg(_Cfg):
    discord_webhook_url = "https://discord.example/webhook"


class _Sent:
    """Stands in for notify.send_discord and records what would have been posted."""

    def __init__(self, ok=True):
        self.ok, self.posts = ok, []

    def __call__(self, cfg, content):
        self.posts.append(content)
        return self.ok


def _patched(sender):
    RC.send_discord = sender
    return sender


def _book_with_one_closed_winner():
    """A paper book with one open position and one trade closed at its target."""
    st = _store()
    occ_a, occ_m = _alert(st, "AAPL", entry=5.0), _alert(st, "MSFT", entry=3.0)
    b = FakeBroker(quotes={occ_a: {"bid": 5.0, "ask": 5.2}, occ_m: {"bid": 3.0, "ask": 3.1}})
    PT.submit_new_alerts(st, b, cfg=_Cfg())
    for o in b.orders():
        b.fill(o["id"], 5.2 if o["option_symbol"] == occ_a else 3.1)
    PT.mark_open(st, b)
    b._q[occ_a] = {"bid": 11.0, "ask": 11.4}        # through the +100% target
    PT.mark_open(st, b)
    PT.close_matured(st, b)
    for o in b.orders():
        if o.get("side") == "sell_to_close":
            b.fill(o["id"], 11.0)
    PT.close_matured(st, b)
    return st, b


def test_recap_says_no_closed_trades_rather_than_reporting_zeros():
    """An empty scorecard printed as 0% hit rate / $0 expectancy reads as a measured result."""
    st = _store()
    occ = _alert(st)
    b = FakeBroker(quotes={occ: {"bid": 5.0, "ask": 5.2}})
    PT.submit_new_alerts(st, b, cfg=_Cfg())
    text = RC.build(st, kind="daily")
    assert "No closed trades yet" in text, text
    for forbidden in ("expectancy +0.0%", "hit rate 0%", "$0 on a 1-contract"):
        assert forbidden not in text, f"reported an empty book as a number: {forbidden}"


def test_recap_will_not_quote_a_hit_rate_as_a_rate_below_the_evidence_floor():
    """'hit rate 100%' off one winner is the most flattering untrue number available."""
    st, _ = _book_with_one_closed_winner()
    text = RC.build(st, kind="weekly")
    assert "1 of 1 won" in text and "too few to read as a rate" in text, text
    assert "hit rate 100%" not in text
    assert f"below the {OT.MIN_CLOSED_PER_BUCKET}-trade floor" in text


def test_every_recap_carries_the_paper_thin_and_convexity_labels():
    st, _ = _book_with_one_closed_winner()
    for kind in ("daily", "weekly"):
        text = RC.build(st, kind=kind)
        assert "paper (Tradier sandbox)" in text and "thin" in text, kind
        assert "CONVEX" in text and "37%" in text, f"{kind}: hit-rate shape missing"
        assert "Educational only, not investment advice" in text, kind
        # The backtest is a reference point, never a target.
        assert "not a target and not a promise" in text, kind


def test_recap_prints_the_tracked_pnl_rather_than_recomputing_it():
    """One definition of P&L. If the recap recomputed, this deliberately-odd value would not
    appear — and the Discord post would eventually disagree with the API."""
    st, _ = _book_with_one_closed_winner()
    with st._conn() as c:
        c.execute("UPDATE option_alerts SET pnl_pct = 0.4242, pnl_dollars = 123.0 "
                  "WHERE status='closed'")
    text = RC.build(st, kind="daily")
    assert "+42.4%" in text and "+$123" in text, text


def test_recap_falls_back_to_the_stored_premiums_when_the_trade_was_never_scored():
    """A closed row with no matching scored alert must appear, not vanish from the book."""
    st = _store()
    PT.ensure_schema(st)
    with st._conn() as c:
        c.execute("""INSERT INTO paper_option_orders
            (alert_id, ticker, occ_symbol, expiry, contracts, state, entry_premium,
             exit_premium, exit_ts, exit_reason, created_at)
            VALUES (9001,'ZZZ','ZZZ260101C00010000','2026-01-01',1,'closed',2.0,3.0,?,
                    'target',?)""",
                  (dt.date.today().isoformat() + "T16:05:00", dt.date.today().isoformat()))
    text = RC.build(st, kind="daily")
    assert "ZZZ" in text and "+50.0%" in text, text


def test_recap_health_note_does_not_report_a_hole_before_inception():
    """A track that started yesterday must not claim it missed the four days before it existed."""
    st = _store()
    b = FakeBroker(quotes={"AAA": {"last": 100.0}, "BBB": {"last": 200.0},
                           "SPY": {"last": 500.0}})
    PT.seed_book(st, b, _BOOK)
    PT.index_point(st, b)
    note = RC.health_note(RC.collect(st))
    assert "hole in it" not in note, note
    assert "since inception" in note, note


def test_recap_fits_discords_limit_without_losing_the_disclaimer():
    """Truncation happens from the END, which is where every caveat lives."""
    st = _store()
    PT.ensure_schema(st)
    today = dt.date.today().isoformat()
    with st._conn() as c:
        for i in range(40):
            c.execute("""INSERT INTO paper_option_orders
                (alert_id, ticker, occ_symbol, expiry, contracts, state, entry_premium,
                 exit_premium, exit_ts, exit_reason, created_at)
                VALUES (?,?,?,'2026-01-01',1,'closed',2.0,3.0,?,
                        'a deliberately long exit reason to pad the message',?)""",
                      (5000 + i, f"TK{i:02d}", f"TK{i:02d}260101C00010000",
                       today + "T16:05:00", today))
    for kind in ("daily", "weekly"):
        text = RC.build(st, kind=kind)
        assert len(text) <= RC.MAX_CHARS, f"{kind}: {len(text)} chars would be truncated"
        assert text.rstrip().endswith("delayed quotes._"), f"{kind} lost its disclaimer"


def test_fit_drops_detail_not_caveats_and_says_that_it_did():
    lines = ["**header**"] + [f"    trade {i} " + "x" * 80 for i in range(60)]
    lines += ["_convexity caveat_", "_educational only_"]
    out = RC._fit(lines, keep_tail=2)
    assert len(out) <= RC.MAX_CHARS
    assert out.startswith("**header**")
    assert out.endswith("_convexity caveat_\n_educational only_")
    assert "trimmed" in out, "detail was dropped without saying so"


def test_recap_posts_at_most_once_per_kind_per_day():
    st, _ = _book_with_one_closed_winner()
    sent = _patched(_Sent())
    cfg = _RecapCfg()
    first = RC.post(cfg, st, kind="daily")
    assert first["posted"] and len(sent.posts) == 1
    for _ in range(3):
        again = RC.post(cfg, st, kind="daily")
        assert again["posted"] is False and again["duplicate"] is True, again
    assert len(sent.posts) == 1, "the daily recap was posted more than once"
    # A different kind on the same day is a different post, not a duplicate.
    assert RC.post(cfg, st, kind="weekly")["posted"] and len(sent.posts) == 2


def test_recap_without_a_webhook_fails_quietly():
    """A missing optional secret must not turn the cron red."""
    st, _ = _book_with_one_closed_winner()
    _patched(_Sent())
    out = RC.post(_Cfg(), st, kind="daily")            # _Cfg has no discord_webhook_url
    assert out["posted"] is False and "DISCORD_WEBHOOK_URL" in out["reason"]


def test_a_failed_post_is_not_marked_so_the_backup_cron_can_retry():
    st, _ = _book_with_one_closed_winner()
    down = _patched(_Sent(ok=False))
    cfg = _RecapCfg()
    assert RC.post(cfg, st, kind="daily")["posted"] is False
    _patched(_Sent())                                   # Discord comes back
    assert RC.post(cfg, st, kind="daily")["posted"] is True
    assert len(down.posts) == 1


def test_recap_survives_an_untouched_database():
    for kind in ("daily", "weekly"):
        text = RC.build(_store(), kind=kind)
        assert "Not started" in text and "Educational only" in text, kind


# ---------------------------------------------------------------------------------------- #
# The live-track HERO band. It is the most prominent thing on the page and the thinnest
# evidence in the product, so the gates that keep it honest are worth more tests than the
# layout is.
# ---------------------------------------------------------------------------------------- #
def test_hero_stays_hidden_until_the_track_actually_reports():
    """No data means no band. A 'coming soon' strip is clutter; a backtested curve under a
    'live' heading would be a lie."""
    from valuation.web.hero import live_hero
    h = live_hero(_store())
    assert h["show"] is False and h["may_lead"] is False
    assert "not started" in h["label"]
    assert h["index"]["available"] is False and h["options"]["available"] is False


def test_hero_labels_the_track_paper_and_thin_with_its_inception_date():
    from valuation.web.hero import live_hero
    st, _ = _book_with_one_closed_winner()
    h = live_hero(st)
    assert h["show"] is True
    assert h["label"].startswith("paper, since ")
    assert h["label"].endswith(", thin")
    # Thin means shown, not celebrated: the band renders but may not carry the claim.
    assert h["thin"] is True and h["may_lead"] is False


def test_hero_withholds_an_expectancy_below_the_evidence_floor():
    """One closed winner must not become a headline expectancy."""
    from valuation.web.hero import live_hero
    st, _ = _book_with_one_closed_winner()
    o = live_hero(st)["options"]
    assert o["available"] is True and o["n_closed"] == 1
    assert o["expectancy_pct"] is None, "printed an expectancy off one trade"
    assert o["thin"] is True and o["min_closed"] >= 1


def test_hero_expectancy_comes_from_the_scorecard_not_a_second_calculation():
    """Whatever the scorecard says IS what the hero shows, once the sample clears the floor."""
    from valuation.web import hero as H
    st, _ = _book_with_one_closed_winner()

    real = H._options_block(st)
    assert real["expectancy_pct"] is None            # thin, as above

    # Same book, but the floor lowered so the sample counts. The number must be the
    # scorecard's, to the digit — the hero may not re-derive expectancy from premiums.
    from valuation.edge import paper_track as _PT
    keep = _PT.MIN_CLOSED_FOR_MEANING
    try:
        _PT.MIN_CLOSED_FOR_MEANING = 1
        block = H._options_block(st)
        expected = (_PT.options_summary(st)["scorecard"] or {}).get("expectancy_pct")
    finally:
        _PT.MIN_CLOSED_FOR_MEANING = keep
    assert expected is not None
    assert block["expectancy_pct"] == expected
    assert block["thin"] is False


def test_hero_will_not_render_the_sandbox_book_as_the_index():
    """REPLACES `test_hero_names_which_forward_record_it_drew` (2026-08-09), and is STRICTLY
    HARDER to satisfy — the old behaviour it pinned cannot pass this one.

    That test asserted the hero may fall back to `paper_track.index_summary` provided it sets
    `source: "paper-sandbox"`, on the reasoning that "an unlabelled fallback would swap the
    number's meaning". The labelling was real and honest — and no template ever rendered
    `source`, so a visitor saw the sandbox book's return under the heading "Valquo Index" with
    nothing to say otherwise. Two days after that test was written the same defect, in the same
    shape, put a false claim into Discord (2026-08-05, +0.18 pp).

    The repair is not a better label. A surface that CAN reach the wrong book eventually shows
    it, so the fallback is gone: with no contract-bound rows the hero reports nothing, however
    much the engine has to say.
    """
    from valuation.web.hero import live_hero
    st, _ = _book_with_one_closed_winner()
    PT.ensure_schema(st)
    with st._conn() as c:
        c.execute("INSERT INTO paper_index_track (as_of, inception, index_ret, bench_ret, "
                  "active_ret, n_priced) VALUES (?,?,?,?,?,?)",
                  ("2026-08-03", "2026-08-01", 0.0182, 0.0091, 0.0091, 25))
    idx = live_hero(st)["index"]
    assert idx["available"] is False, (
        "the hero rendered the Tradier sandbox book as the Valquo Index: " + repr(idx))
    for k in ("cum_pct", "bench_pct", "excess_pp"):
        assert idx.get(k) is None, f"a sandbox figure leaked into the hero as {k}"


def test_hero_index_figures_carry_their_book_and_window(tmpdir=None):
    """When the hero DOES have a figure, the book and the window come with it — the two facts
    whose absence made +0.18 pp look like a claim about the Index."""
    import valuation.web.hero as H
    import valuation.screener.index_track as IT
    orig = IT.summarize
    try:
        IT.summarize = lambda *a, **k: {
            "available": True, "benchmark": "SPY", "inception": "2026-07-30", "thin": True,
            "min_live_days": IT.MIN_LIVE_DAYS, "series": [], "note": "",
            "live": {"days": 2, "since": "2026-07-31", "as_of": "2026-08-06",
                     "cum_valquo_pct": 0.776, "cum_spy_pct": 3.6228, "excess_pp": -2.8468,
                     "book": IT.BOOK_SHORT, "window": "since inception 2026-07-30 through "
                                                      "2026-08-06 (2 recorded sessions)",
                     "claim": "…", "recorder": IT.RECORDER},
        }
        idx = H._index_block(_store())
    finally:
        IT.summarize = orig
    assert idx["available"] is True and idx["source"] == "index-track"
    assert idx["book"] == IT.BOOK_SHORT and "2026-08-06" in idx["window"]
    assert idx["recorder"] == IT.RECORDER
    assert abs(idx["excess_pp"] + 2.8468) < 1e-9


def test_hero_never_raises_and_never_takes_the_page_down():
    """The band decorates a page that must render without it."""
    from valuation.web.hero import live_hero

    class _Dead:
        def get_meta(self, k, default=None):
            raise RuntimeError("no db")

        def _conn(self):
            raise RuntimeError("no db")
    h = live_hero(_Dead())
    assert h["show"] is False and h["may_lead"] is False



# --------------------------------------------------------------- AUDIT P4: exits are sold
_BOOK_ONE = {"positions": [{"ticker": "AAA", "weight": 1.0}]}


def test_p4_a_name_that_leaves_the_book_is_closed_not_deleted():
    """The bug: seed_book only ever INSERTED, so the paper index was an ever-growing union of
    everything the screener had ever liked. The fix must SELL the departed name and must keep
    its record — deleting it would drop names that left after their composite decayed, which
    flatters the track in exactly the direction nobody would notice.
    """
    st = _store()
    b = FakeBroker(quotes={"AAA": {"last": 100.0}, "BBB": {"last": 200.0},
                           "SPY": {"last": 500.0}})
    PT.seed_book(st, b, _BOOK)
    b._q = {"AAA": {"last": 100.0}, "BBB": {"last": 240.0}, "SPY": {"last": 550.0}}
    out = PT.seed_book(st, b, _BOOK_ONE)                      # BBB has left the book
    assert out["closed"] == 1 and out["closed_tickers"] == ["BBB"], out

    with st._conn() as c:
        assert [r[0] for r in c.execute("SELECT ticker FROM paper_index_holdings")] == ["AAA"]
        row = c.execute("SELECT ticker, entry_price, exit_price, bench_entry_price, "
                        "exit_bench_price, exit_date FROM paper_index_closed").fetchall()
    assert len(row) == 1, "the departed name was deleted instead of closed"
    t, ep, xp, be, xb, xd = row[0]
    assert (t, ep, xp, be, xb) == ("BBB", 200.0, 240.0, 500.0, 550.0)
    assert xd, "a closed stint with no exit date is indistinguishable from an open one"

    # +20% against SPY's +10% = +10pp of realised active return, kept and reported.
    real = PT.index_summary(st)["realized"]
    assert real["n_closed"] == 1 and real["n_priced"] == 1
    assert abs(real["mean_active_ret"] - 0.10) < 1e-9, real


def test_p4_a_closed_name_stops_moving_the_index_and_can_re_enter_later():
    """Two failures in one test, because the second is the trap in the obvious fix.

    A sold name must stop contributing to future points. And it must be able to COME BACK:
    `paper_index_holdings.ticker` is a PRIMARY KEY and the insert is INSERT OR IGNORE, so
    parking closed rows in that table would make a re-entering name silently un-addable — the
    original bug's mirror image, and just as quiet.
    """
    st = _store()
    b = FakeBroker(quotes={"AAA": {"last": 100.0}, "BBB": {"last": 200.0},
                           "SPY": {"last": 500.0}})
    PT.seed_book(st, b, _BOOK)
    b._q = {"AAA": {"last": 110.0}, "BBB": {"last": 999.0}, "SPY": {"last": 500.0}}
    PT.seed_book(st, b, _BOOK_ONE)
    pt = PT.index_point(st, b)
    assert pt["n_positions"] == 1 and pt["n_priced"] == 1
    assert abs(pt["index_ret"] - 0.10) < 1e-9, "the sold name is still moving the index"

    back = PT.seed_book(st, b, _BOOK)                          # BBB returns
    assert back["added"] == 1, "a re-entering name was silently refused"
    with st._conn() as c:
        assert c.execute("SELECT COUNT(*) FROM paper_index_holdings").fetchone()[0] == 2
        # the earlier stint survives the re-entry rather than being overwritten
        assert c.execute("SELECT COUNT(*) FROM paper_index_closed").fetchone()[0] == 1


def test_p4_a_truncated_export_closes_nothing():
    """A failed export and a genuinely smaller book are indistinguishable at this layer, and
    acting on the wrong one liquidates a real track. The guard refuses and SAYS SO — it does
    not proceed quietly, which would be silencing a check.
    """
    st = _store()
    b = FakeBroker(quotes={f"T{i}": {"last": 100.0} for i in range(10)} | {"SPY": {"last": 500.0}})
    big = {"positions": [{"ticker": f"T{i}", "weight": 0.1} for i in range(10)]}
    PT.seed_book(st, b, big)
    out = PT.seed_book(st, b, {"positions": [{"ticker": "T0", "weight": 1.0}]})
    assert out["closed"] == 0, "a 90% shrink was treated as a real rebalance"
    assert out["close_refused"] and "truncated" in out["close_refused"]
    with st._conn() as c:
        assert c.execute("SELECT COUNT(*) FROM paper_index_holdings").fetchone()[0] == 10

    # An ordinary rebalance is NOT refused: the guard catches a truncated file, not turnover.
    ok = PT.seed_book(st, b, {"positions": [{"ticker": f"T{i}", "weight": 0.125}
                                            for i in range(8)]})
    assert ok["closed"] == 2 and ok["close_refused"] is None, ok


def test_p4_inception_does_not_walk_forward_when_the_oldest_name_is_sold():
    """Taking the minimum entry date over OPEN holdings only would make the track appear to get
    younger the longer it ran — the record's start date would follow its oldest survivor.
    """
    st = _store()
    b = FakeBroker(quotes={"AAA": {"last": 100.0}, "BBB": {"last": 200.0},
                           "SPY": {"last": 500.0}})
    PT.seed_book(st, b, _BOOK, today="2026-01-05")
    PT.index_point(st, b, today="2026-01-05")
    first = PT.index_summary(st)["inception"]

    PT.seed_book(st, b, {"positions": [{"ticker": "CCC", "weight": 1.0}]}, today="2026-06-01")
    b._q = {"CCC": {"last": 50.0}, "SPY": {"last": 500.0}}
    PT.index_point(st, b, today="2026-06-01")
    assert PT.index_summary(st)["inception"] == first, "inception followed the surviving names"


def test_p4_seed_book_can_still_accumulate_when_asked():
    """The old behaviour is reachable for reproducing a historical run — but it is not the
    default, because the old behaviour is the bug.
    """
    st = _store()
    b = FakeBroker(quotes={"AAA": {"last": 100.0}, "BBB": {"last": 200.0},
                           "SPY": {"last": 500.0}})
    PT.seed_book(st, b, _BOOK)
    out = PT.seed_book(st, b, _BOOK_ONE, close_exits=False)
    assert out["closed"] == 0
    with st._conn() as c:
        assert c.execute("SELECT COUNT(*) FROM paper_index_holdings").fetchone()[0] == 2

# ---------------------------------------------------------------------------------------- #
# ONE RECORDER FOR EVERY OUTBOUND vs-SPY CLAIM.
#
# THE INCIDENT THESE PIN. On 2026-08-05 the Discord recap posted "Since inception 2026-08-03
# (3 sessions): index +3.22%, SPY +3.05% -> **+0.18 pp**" — the Valquo Index beating SPY. The
# contract-bound recorder over that window reads -0.2777pp (2026-07-31) and -2.8468pp
# (2026-08-06); it was never above SPY. No arithmetic was wrong. The recap read the Tradier
# sandbox ENGINE (10 names, equal-weighted at 10%, inception 2026-08-03 — weights that violate
# PAPER_TRACK_CONTRACT.md's own 8% cap) and printed it under the words "Valquo Index vs SPY".
#
# WHY THESE ARE STRICTER THAN THE SITE'S. A wrong figure on a page is corrected by a deploy.
# A wrong figure in Discord is delivered once, to people, and no correction ever catches it.
# ---------------------------------------------------------------------------------------- #
_FAKE_CLAIM = {
    "available": True, "reason": "", "recorder": "FAKE_RECORDER", "book": "FAKEBOOK",
    "book_short": "FAKEBOOK", "benchmark": "SPY", "window": "FAKEWINDOW",
    "window_kind": "inception", "since": "2026-01-01", "as_of": "2026-01-09", "n_points": 2,
    # DELIBERATELY INCONSISTENT: +5.00 - +1.00 is +4.00 pp, and the recorder says -9.99.
    # Nothing downstream may "fix" that — the recorder is the definition, not a suggestion.
    "valquo_pct": 5.0, "spy_pct": 1.0, "excess_pp": -9.99, "excess_source": "recorded",
    "text": "FAKEBOOK vs SPY, FAKEWINDOW: Index +5.00%, SPY +1.00% → -9.99 pp",
}


def test_the_recap_prints_the_recorders_excess_and_never_recomputes_it():
    """THE PIN THE TASK ASKED FOR: a digest that computes its own excess return fails here.

    The recorder is handed a claim whose excess (-9.99 pp) is not the difference of its own two
    legs (+4.00 pp). Any surface that re-derived `valquo - spy` would print +4.00. Only a
    surface that treats the recorder as the single definition prints -9.99.
    """
    import valuation.screener.index_track as IT
    orig = IT.vs_spy_claim
    try:
        IT.vs_spy_claim = lambda *a, **k: dict(_FAKE_CLAIM)
        text = RC.build(_store(), kind="daily")
    finally:
        IT.vs_spy_claim = orig
    assert "-9.99 pp" in text, f"the recap did not print the recorder's excess:\n{text}"
    assert "+4.00 pp" not in text, ("the recap RECOMPUTED the excess from the two legs instead "
                                    f"of reading it:\n{text}")
    # The book and the window must travel with the number, in the message itself.
    assert "FAKEBOOK" in text and "FAKEWINDOW" in text, text


def test_no_outbound_surface_may_quote_the_sandbox_engine_as_the_index():
    """The 2026-08-05 regression, reconstructed from the engine's own committed export.

    The engine holds exactly the rows it held that day and the bound track holds nothing. The
    correct post says it has no Index figure. A post that reaches for the engine prints
    +0.18 pp, which is the false claim that was actually sent.
    """
    st = _store()
    PT.ensure_schema(st)
    rows = [("2026-08-03", 0.0172942154, 0.0142430692, 0.0030511461),
            ("2026-08-04", 0.0404483143, 0.0325288141, 0.0079195002),
            ("2026-08-05", 0.0322393165, 0.0304673172, 0.0017719993)]
    with st._conn() as c:
        c.executemany("INSERT OR REPLACE INTO paper_index_track (as_of, index_ret, bench_ret,"
                      " active_ret, n_positions, n_priced, inception) VALUES (?,?,?,?,10,10,"
                      "'2026-08-03')", rows)
    text = RC.build(st, kind="daily", day="2026-08-05")
    assert "+0.18 pp" not in text, f"THE 2026-08-05 FALSE CLAIM IS BACK:\n{text}"
    assert "+3.22%" not in text and "+3.05%" not in text, (
        f"the sandbox engine's returns are being reported as the Index:\n{text}")
    assert "No Index-vs-SPY figure" in text, (
        f"with no bound rows the recap must decline to report, not substitute:\n{text}")


def test_the_recap_does_not_consult_the_engine_for_an_index_claim_at_all():
    """Not "prefers the recorder" — cannot reach the engine. `index_summary` is made to
    explode; a recap that still builds is one that never calls it for this."""
    st = _store()
    PT.ensure_schema(st)
    orig = PT.index_summary
    try:
        PT.index_summary = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("the recap asked the sandbox engine for an Index-vs-SPY figure"))
        text = RC.build(st, kind="daily")
    finally:
        PT.index_summary = orig
    assert "Valquo Index" in text and "vs SPY" in text, text


def test_outbound_modules_contain_no_second_definition_of_excess_return():
    """Structural backstop: no outbound composer may subtract one return series from another.

    The behavioural tests above catch a recomputation that CHANGES a printed number. This
    catches one that happens to agree today — the state the site and the recap were in before
    2026-08-05, when two definitions matched and nothing said which was authoritative. The
    single legal site of this arithmetic is `index_track._window_return_pct` / `vs_spy_claim`,
    which is deliberately not in this list.
    """
    import ast
    import os
    # Every module that composes something a person receives: Discord, email, the site's hero.
    outbound = ["valuation/saas/recap.py", "valuation/saas/notify.py",
                "valuation/saas/emailer.py", "valuation/web/hero.py"]
    # Both operands must be return-ish for a subtraction to count, which is what keeps
    # `len(lines) - keep_tail` and `today - timedelta(...)` out of it.
    vocab = ("valquo", "spy", "bench", "index_ret", "excess", "active_ret", "cum_pct",
             "cum_valquo_pct", "cum_spy_pct", "bench_pct", "bench_ret")

    def nameish(node):
        if isinstance(node, ast.Name):
            return node.id.lower()
        if isinstance(node, ast.Attribute):
            return node.attr.lower()
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            return str(node.slice.value).lower()
        if isinstance(node, ast.Call):                 # r.get("index_ret")
            for a in node.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    return a.value.lower()
        return ""

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    offences = []
    for rel in outbound:
        path = os.path.join(root, *rel.split("/"))
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=rel)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub)):
                continue
            l, r = nameish(node.left), nameish(node.right)
            if any(v in l for v in vocab) and any(v in r for v in vocab):
                offences.append(f"{rel}:{node.lineno}  {l} - {r}")
    assert not offences, (
        "an outbound surface computes its own excess return; it must read "
        "index_track.vs_spy_claim instead:\n  " + "\n  ".join(offences))


def test_the_email_digest_makes_no_unsourced_vs_spy_claim():
    """The email digest currently makes NO vs-SPY claim, and this keeps it that way by
    accident-proofing rather than by memory: if one is ever added, it must come from the
    recorder. Checked on the rendered output, not the source, so a claim assembled from
    f-strings cannot slip past."""
    from valuation.saas import emailer
    html = (emailer.weekly_digest_html("2026-08-05", [], []) or "") + \
           (emailer.learning_digest_html({}) or "")
    if "SPY" in html.upper():
        import valuation.screener.index_track as IT
        assert IT.RECORDER in html or IT.BOOK_SHORT in html, (
            "the email digest quotes SPY without naming the contract-bound recorder or book")


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
