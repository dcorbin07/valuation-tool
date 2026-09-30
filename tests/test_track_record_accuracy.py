"""The Track Record tab records what it says it records, and the public copy matches the project.

    python tests/test_track_record_accuracy.py

Found 2026-09-30, measured on valquo.co before any change:

1. NOTHING HAD EVER MATURED. `/api/track` returned `summary: null` at every horizon for both
   sources, and the options source's OLDEST shown pick (2026-08-24) still read "—" five weeks
   later. Cause, reproduced offline: the yfinance fallback returns `2026-09-29 00:00:00-04:00`,
   which parses TZ-AWARE, while `run_date` parses naive, so `searchsorted` raised TypeError on the
   first such ticker and `_maybe_refresh_track` swallowed it in a bare `except: pass`. The paper
   account's SPY comparison (`bench: null`) died the same way.
2. The card printed the 15-row "recent" list's length as "N logged so far".
3. 19 of the paper account's first 23 exits were "left coverage", several booked at EXACTLY the
   entry price -- a name the scan never saw again closed at minus costs, which is not a return.
4. The Signals tab's scream-buy record read "could not be read just now": MA46 added two columns
   to `option_alerts` and the record's M6 guard, correctly, refused every row until someone
   decided whether the tab carries them.
5. Copy that contradicted the site as it runs: /terms showed visitors a note headed "not shown
   to visitors"; /privacy showed visitors a DRAFT for a paid product (Stripe, sign-up,
   "[bracketed]" placeholders); /methodology and /work said the book and its record were
   private; the landing page advertised a backtest UI that no longer exists.
"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — temp state only. Import BEFORE `valuation`.

import pandas as pd                                                  # noqa: E402

from valuation.config import CONFIG                                  # noqa: E402

CONFIG.private_mode = False
CONFIG.owner_split = True
CONFIG.open_access = True
CONFIG.public_full_view = True        # the posture valquo.co runs under (Don, 2026-08-13)

from valuation.screener.store import Store                          # noqa: E402
from valuation.edge import track, positions                          # noqa: E402


def _store():
    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p)
    return Store(p)


_IDX = pd.bdate_range("2026-06-01", "2026-09-29", tz="America/New_York")


def _yf_like(t):
    """Exactly what `close_series` returns when the yfinance fallback served the frame."""
    return [str(x) for x in _IDX.astype(str)], [100.0 + i * 0.1 for i in range(len(_IDX))]


def _stooq_like(t):
    return [x.strftime("%Y-%m-%d") for x in _IDX], [100.0 + i * 0.1 for i in range(len(_IDX))]


# ------------------------------------------------------------------ 1. maturation
def test_a_yfinance_served_series_matures_instead_of_raising():
    st = _store()
    track.log_picks(st, "hot10", "2026-08-07", ["AAA", "BBB"])
    r = track.update_returns(st, "hot10", price_fn=_yf_like)
    # 08-07 -> 09-29 is ~36 trading days: the 21-day horizon has matured, 63+ have not.
    assert r["computed"] == 2, r
    assert len(st.track_returns("hot10", 21)) == 2
    s = track.summary(st, "hot10")
    assert s["21"] and s["21"]["n"] == 2 and s["all"]


def test_both_vendor_shapes_give_the_same_numbers():
    """The fix normalises dates; it must not move a single figure on the Stooq path."""
    a, b = _store(), _store()
    for st in (a, b):
        track.log_picks(st, "hot10", "2026-08-07", ["AAA"])
    track.update_returns(a, "hot10", price_fn=_yf_like)
    track.update_returns(b, "hot10", price_fn=_stooq_like)
    for h in (21, 0):
        ra, rb = a.track_returns("hot10", h), b.track_returns("hot10", h)
        assert len(ra) == len(rb) == 1, (h, ra, rb)
        assert abs(ra[0]["fwd_ret"] - rb[0]["fwd_ret"]) < 1e-12
        assert abs(ra[0]["bench_ret"] - rb[0]["bench_ret"]) < 1e-12


def test_one_bad_ticker_does_not_stop_the_rest():
    st = _store()
    track.log_picks(st, "hot10", "2026-08-07", ["BAD", "GOOD"])

    def fn(t):
        if t == "BAD":
            raise RuntimeError("vendor blew up")
        return _stooq_like(t)
    r = track.update_returns(st, "hot10", price_fn=fn)
    assert "BAD" in r["unpriced"]
    assert any(x["ticker"] == "GOOD" for x in st.track_returns("hot10", 21))


def test_no_benchmark_is_reported_not_silent():
    st = _store()
    track.log_picks(st, "hot10", "2026-08-07", ["AAA"])
    r = track.update_returns(st, "hot10", price_fn=lambda t: (None, None) if t == "SPY" else _stooq_like(t))
    assert r["benchmark_priced"] is False and r["computed"] == 0


def test_the_paper_account_benchmark_survives_a_tz_aware_spy():
    from valuation.web import app as W
    from valuation.screener import prices
    st = _store()
    st.open_position("hot10", "AAA", "2026-08-07", 100.0)
    st.close_position("hot10", "AAA", "2026-08-07", "2026-09-10", 110.0, "hit fair value")
    # A never-repriced exit must not enter the alpha either.
    st.open_position("hot10", "ZZZ", "2026-08-07", 50.0)
    st.close_position("hot10", "ZZZ", "2026-08-07", "2026-09-10", 50.0, "left coverage")
    orig = prices.close_series
    prices.close_series = lambda t, days=1500: _yf_like(t)
    W._PAPER_BENCH.pop("hot10", None)
    try:
        W._compute_paper_bench(st, "hot10")
    finally:
        prices.close_series = orig
    b = W._PAPER_BENCH.get("hot10")
    assert b and b["n_alpha"] == 1 and b["spy_all_time"] is not None, b
    assert "significant" not in b, "the retired |t| > 2 badge came back"


# ------------------------------------------------------------------ 2. the count
def test_the_card_counts_the_log_not_the_table():
    from valuation.web import app as W
    st = W._store()
    for d in pd.bdate_range("2026-08-03", "2026-08-21"):
        track.log_picks(st, "hot10", d.strftime("%Y-%m-%d"), [f"T{i}" for i in range(10)])
    c = W._track_counts(st, "hot10")
    assert c["n_logged"] >= 150 and c["n_days"] >= 15 and c["first_logged"] <= "2026-08-03", c
    W._LAST_TRACK_REFRESH[0] = time.time()          # no background vendor fetch from a test
    with W.app.test_client() as cl:
        d = cl.get("/api/track").get_json()
    hot = d["sources"]["hot10"]
    assert hot["counts"]["n_logged"] == c["n_logged"] and len(hot["recent"]) == 15
    assert "`paper_sandbox`" not in d["note"], "the note still names a JSON key to users"


def test_the_card_script_reads_the_count_and_not_the_row_list():
    js = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "valuation", "web", "static", "app.js"), encoding="utf-8").read()
    i = js.index("function _trackCard(")
    fn = js[i:js.index("\nfunction ", i + 10)]
    assert "rec.length} logged" not in fn, "the old rec.length count is back"
    assert "ct.n_logged" in fn and "overlap" in fn


# ------------------------------------------------------------------ 3. paper account
def test_a_skipped_holding_is_repriced_without_resetting_its_coverage_clock():
    st = _store()
    row = lambda t, px: [{"ticker": t, "price": px, "hot_score": 90, "rank": 1}]
    positions.update_positions(st, "hot10", "2026-08-03", row("AAA", 100.0), top_n=5,
                               min_hold_days=0, coverage_gap_days=21)
    # AAA drops out of the scan; the vendor still prices it.
    positions.update_positions(st, "hot10", "2026-08-10", row("ZZZ", 50.0), top_n=5,
                               min_hold_days=0, coverage_gap_days=21, price_fn=lambda t: 104.0)
    p = [x for x in st.open_positions("hot10") if x["ticker"] == "AAA"][0]
    assert p["last_price"] == 104.0 and p["last_seen_date"] == "2026-08-03", p
    positions.update_positions(st, "hot10", "2026-09-01", row("ZZZ", 50.0), top_n=5,
                               min_hold_days=0, coverage_gap_days=21, price_fn=lambda t: 108.0)
    a = [x for x in st.all_positions("hot10") if x["ticker"] == "AAA"][0]
    assert a["exit_reason"] == "left coverage" and a["exit_price"] == 108.0, a


def test_an_exit_never_repriced_is_unknown_not_flat():
    st = _store()
    st.open_position("hot10", "AAA", "2026-08-03", 100.0)
    st.close_position("hot10", "AAA", "2026-08-03", "2026-09-01", 100.0, "left coverage")
    st.open_position("hot10", "BBB", "2026-08-03", 100.0)
    st.close_position("hot10", "BBB", "2026-08-03", "2026-09-01", 120.0, "hit fair value")
    s = positions.paper_summary(st, "hot10", cost_bps=10)
    assert s["summary"]["n_unpriced_exits"] == 1
    assert s["summary"]["win_rate"] == 1.0, "the never-repriced exit was averaged in as a loss"
    aaa = [x for x in s["closed"] if x["ticker"] == "AAA"][0]
    assert aaa["unpriced"] is True and aaa["ret"] is None


def test_an_open_name_the_scan_skipped_is_marked_at_its_last_real_price():
    st = _store()
    st.open_position("hot10", "AAA", "2026-08-03", 100.0)
    st.mark_position("hot10", "AAA", "2026-08-03", 110.0)
    s = positions.paper_summary(st, "hot10", latest_price_map={})
    w = s["watching"][0]
    assert w["marked_from"] == "last price" and abs(w["ret"] - 0.10) < 1e-12
    assert s["summary"]["n_open_marked"] == 1


# ------------------------------------------------------------------ 4. scream-buy record
def test_the_scream_record_reads_with_ma46_columns_present():
    from valuation.edge import scream_log as SL, options_tracker as OT
    st = _store()
    SL.ensure_schema(st); OT.ensure_pnl_schema(st)
    with st._conn() as c:
        c.execute("INSERT INTO option_alerts (alert_ts,ticker,opt_right,strike,expiry,occ_symbol,"
                  "entry_premium,exit_premium,exit_ts,status) VALUES ('2026-09-01T20:00:00','AAPL',"
                  "'call',200,'2026-11-20','AAPL261120C00200000',5.0,7.0,'2026-09-10','closed')")
    recs = SL.records(st)
    assert len(recs) == 1 and recs[0]["pnl_pct_net"] is not None
    assert recs[0]["pnl_pct_net"] < 0.40, "net must be below the gross +40%"


# ------------------------------------------------------------------ 5. copy
def _client():
    from valuation.saas.app_saas import create_saas_app
    a = create_saas_app(CONFIG)
    a.config["TESTING"] = True
    return a.test_client()


def test_a_visitor_is_not_shown_notes_addressed_to_the_owner():
    c = _client()
    for page in ("/terms", "/privacy"):
        body = c.get(page).get_data(as_text=True)
        assert "Owner-only note" not in body, f"{page} shows a visitor the owner's note"
        assert "not shown to visitors" not in body


def test_the_privacy_page_describes_this_site_and_not_a_draft():
    body = _client().get("/privacy").get_data(as_text=True)
    for gone in ("DRAFT", "[bracketed]", "[DATE PUBLISHED]", "Stripe", "subscribe",
                 "hello@yourdomain", "plan limits"):
        assert gone not in body, f"/privacy still carries {gone!r}"
    for must in ("no visitor accounts", "No analytics", "local storage"):
        assert must in body, f"/privacy lost {must!r}"


def test_public_pages_no_longer_say_the_public_parts_are_private():
    c = _client()
    retired = {
        "/methodology": ("kept private precisely", "That book and its\n  record are not published",
                         "not yet the same function"),
        CONFIG.resolved_portfolio_path: ("private to its owner", "It is days old", "628 tests",
                                         "3,042", "+5.14%", "the 3.0 hurdle",
                                         "backfill is not\n    finished"),
        "/landing": ("self-calibrating", "Honest backtest", "Prove the edge"),
        # The Index tab: the band is 0.30 since S14 (2026-08-13), and "rebuilt after each close"
        # described the daily holdings as if they were the fixed, quarterly forward book.
        "/app": ("20% no-trade band", "name, rebuilt after each close"),
    }
    for page, phrases in retired.items():
        body = c.get(page).get_data(as_text=True)
        for ph in phrases:
            assert ph not in body, f"{page} still says {ph!r}"


def test_the_work_page_attributes_the_licensed_factor_data():
    body = _client().get(CONFIG.resolved_portfolio_path).get_data(as_text=True)
    assert "Global Factor Data" in body and "CC BY-NC 4.0" in body


def test_the_methodology_gap_is_the_corrected_one():
    body = _client().get("/methodology").get_data(as_text=True)
    assert "−5.06 percentage points" in body, "methodology is not quoting payoff.R2_GAP_PP"


# ------------------------------------------------------------------ 6. writer diagnostics
def test_a_benchmark_refusal_says_what_the_vendor_returned():
    from valuation.screener import index_mark
    import json as _json
    tmp = tempfile.mkdtemp()
    meta = os.path.join(tmp, "book.json")
    with open(meta, "w", encoding="utf-8") as fh:
        _json.dump({"inception_date": "2026-07-30", "benchmark": "SPY",
                    "positions": [{"ticker": "AAA", "weight": 1.0}]}, fh)

    def fetch(t, days=400):
        return pd.DataFrame({"Date": ["2026-09-28", "2026-09-29"], "Close": [1.0, 1.0]})
    r = index_mark.contract_row("2026-09-29", meta_path=meta, fetch=fetch,
                                refuse_before_close=False)
    assert r["ok"] is False and "inception" in r["reason"], r
    dg = r.get("diagnostics") or {}
    assert dg.get("first_close") == "2026-09-28" and dg.get("n_closes") == 2, dg


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    ok = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}"); ok += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:                                          # noqa: BLE001
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{ok}/{len(tests)} track-record-accuracy tests passed")
    return ok == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
