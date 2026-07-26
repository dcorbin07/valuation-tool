"""
SaaS + optimizer tests (offline, deterministic — temp DB, no network).
    python tests/test_saas.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.config import CONFIG
from valuation.saas.models import UserStore
from valuation.saas import gating
from valuation.saas.auth import _demo_user
from valuation.backtest.panel import build_synthetic_panel
from valuation.backtest.optimize import optimize_weights

# Most tests below exercise the REAL per-tier gating. Beta mode (a launch-time
# override that unlocks Premium for everyone) is turned off here so the tier
# assertions mean something; the beta/demo tests re-enable it locally.
CONFIG.beta_all_premium = False


def _store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return UserStore("sqlite:///" + path)


def test_user_create_and_verify():
    s = _store()
    u = s.create_user("a@b.com", "password123")
    assert u["tier"] == "free"
    assert s.verify("a@b.com", "password123")["id"] == u["id"]
    assert s.verify("a@b.com", "wrong") is None


def test_duplicate_and_validation():
    s = _store()
    s.create_user("a@b.com", "password123")
    for bad in [("a@b.com", "password123"), ("no-at", "password123"), ("x@y.com", "short")]:
        try:
            s.create_user(*bad); assert False, "should have raised"
        except ValueError:
            pass


def test_subscription_and_gating_tiers():
    s = _store()
    u = s.create_user("p@b.com", "password123")
    # free user blocked from paid features
    assert gating.check_request("/api/backtest/run", "POST", {}, u, s)[1] == 402
    assert gating.check_request("/api/scan/run", "POST", {"scope": "whole_market"}, u, s)[1] == 402
    assert gating.check_request("/api/scan/run", "POST", {"scope": "bundled"}, u, s) is None
    # upgrade to pro (active) -> unlocked
    s.set_subscription(u["id"], tier="pro", status="active")
    u = s.get_by_id(u["id"])
    assert gating.check_request("/api/backtest/run", "POST", {}, u, s) is None
    assert gating.check_request("/api/scan/run", "POST", {"scope": "whole_market"}, u, s) is None
    # premium-only optimizer still locked for pro
    assert gating.check_request("/api/optimize/run", "POST", {}, u, s)[1] == 402


def test_login_required_for_api():
    s = _store()
    assert gating.check_request("/api/backtest/run", "POST", {}, None, s)[1] == 401
    # public reads allowed anonymously
    assert gating.check_request("/api/hotstocks", "GET", {}, None, s) is None


def test_free_daily_valuation_limit():
    s = _store()
    u = s.create_user("v@b.com", "password123")
    codes = [gating.check_request("/api/value", "POST", {"ticker": "NKE"}, u, s) for _ in range(6)]
    assert all(c is None for c in codes[:5])       # 5/day allowed
    assert codes[5][1] == 402                       # 6th blocked


def test_optimizer_accepts_signal_rejects_noise():
    d = {"momentum": 0.5, "value": 0.5}
    sig = optimize_weights(build_synthetic_panel(140, 44, signal=0.1, seed=5),
                           ["momentum", "value"], step=0.1, default_weights=d)
    noise = optimize_weights(build_synthetic_panel(140, 44, signal=0.0, seed=6),
                             ["momentum", "value"], step=0.1, default_weights=d)
    assert sig["accepted"] is True
    assert noise["accepted"] is False and noise["recommended_weights"] == d


def test_beta_all_premium_unlocks_everyone():
    s = _store()
    u = s.create_user("beta@b.com", "password123")   # a plain free signup
    assert gating._active(u) == "free"               # beta off (module default)
    CONFIG.beta_all_premium = True
    try:
        assert gating._active(u) == "premium"        # now everyone is Premium
        assert gating.check_request("/api/backtest/run", "POST", {}, u, s) is None
        assert gating.check_request("/api/optimize/run", "POST", {}, u, s) is None
        # premium has no daily valuation cap — 6 in a row all allowed
        codes = [gating.check_request("/api/value", "POST", {"ticker": "NKE"}, u, s) for _ in range(6)]
        assert all(c is None for c in codes)
    finally:
        CONFIG.beta_all_premium = False


def test_demo_preview_is_premium_but_not_owner():
    s = _store()
    d = _demo_user()
    # Recruiter preview gets Premium even with beta OFF (link must outlive beta).
    assert CONFIG.beta_all_premium is False
    assert gating._active(d) == "premium"
    assert gating.check_request("/api/optimize/run", "POST", {}, d, s) is None
    # ...but the private Edge Lab stays owner-only — a demo visitor is blocked.
    assert gating.check_request("/api/edge/backtest", "POST", {}, d, s)[1] == 403


def test_master_link_route_and_banner():
    # End-to-end through the real Flask app: token gate + demo session + banner.
    CONFIG.demo_access_token = "sekret-xyz"
    from valuation.saas.app_saas import create_saas_app
    app = create_saas_app(CONFIG)
    app.config.update(TESTING=True)
    c = app.test_client()
    assert c.get("/demo/wrong").headers["Location"].endswith("/")             # → landing "/"
    assert c.get("/demo/sekret-xyz").headers["Location"].endswith("/app")     # → dashboard
    page = c.get("/app")
    assert page.status_code == 200
    assert b"get ahead of the beta" in page.data      # inclusive demo banner copy
    assert b'href="/register"' in page.data           # + a sign-up call to action
    CONFIG.demo_access_token = "preview"              # restore default


def test_demo_signup_converts_to_real_account():
    # Signing up from the preview should drop the demo flag and take over as a real account.
    import uuid
    CONFIG.demo_access_token = "sekret-xyz"
    from valuation.saas.app_saas import create_saas_app
    app = create_saas_app(CONFIG); app.config.update(TESTING=True)
    c = app.test_client()
    c.get("/demo/sekret-xyz")                          # enter the preview
    assert b"get ahead of the beta" in c.get("/app").data
    email = "conv_" + uuid.uuid4().hex[:8] + "@ex.com"
    r = c.post("/register", data={"email": email, "password": "password123", "agree": "on"})
    assert r.status_code in (301, 302)                 # redirected to /app as the new user
    after = c.get("/app").data
    assert b"get ahead of the beta" not in after       # demo flag cleared → generic banner
    CONFIG.demo_access_token = "preview"


def test_ci_ingest_snapshot_roundtrip():
    # The free-tier bridge: a CI runner POSTs a finished snapshot; the site serves it.
    CONFIG.admin_token = "test-admin-xyz"
    from valuation.saas.app_saas import create_saas_app
    app = create_saas_app(CONFIG); app.config.update(TESTING=True)
    c = app.test_client()
    rows = [{"ticker": "TESTX", "name": "Test Co", "sector": "Technology",
             "rank": 1, "hot_score": 91.0, "composite": 1.2, "price": 10.0}]
    # wrong/absent token is rejected
    assert c.post("/admin/ingest-snapshot", json={"rows": rows},
                  headers={"X-Admin-Token": "nope"}).status_code == 401
    assert c.post("/admin/ingest-snapshot", json={"rows": rows}).status_code == 401
    # correct token stores it
    ok = c.post("/admin/ingest-snapshot", json={"scan_date": "2099-01-01", "rows": rows},
                headers={"X-Admin-Token": "test-admin-xyz"})
    assert ok.status_code == 200 and ok.get_json()["rows"] == 1
    # and every visitor now sees it instantly at the public hot-list endpoint
    d = c.get("/api/hotstocks").get_json()
    assert d.get("scan_date") == "2099-01-01"
    assert any(x["ticker"] == "TESTX" for x in d.get("rows", []))
    CONFIG.admin_token = ""   # restore


def test_screaming_buys_filter():
    from valuation.saas.notify import screaming_buys
    rows = [
        {"ticker": "A", "score": 85, "labels": ["Call-heavy flow (P/C 0.40)", "Uptrend (>50 & >200 DMA)"]},
        {"ticker": "B", "score": 85, "labels": ["Overbought (RSI 82)"]},   # high score, not bullish → excluded
        {"ticker": "C", "score": 60, "labels": ["Call-heavy flow"]},        # bullish, low score → excluded
    ]
    assert [r["ticker"] for r in screaming_buys(rows, 80)] == ["A"]


def test_alert_dedup_and_optin():
    import tempfile, uuid
    from valuation.screener.store import Store
    # de-dupe: one alert per ticker per day
    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p)
    st = Store(p)
    assert st.alerted_today("NVDA") is False
    st.mark_alerted("NVDA", "2026-07-27 10:00")
    assert st.alerted_today("NVDA") is True
    # email opt-in defaults OFF; toggles on and off
    s = _store()
    u = s.create_user("al_" + uuid.uuid4().hex[:6] + "@ex.com", "password123")
    assert not s.get_by_id(u["id"]).get("alerts_email_opt_in")
    assert s.alert_subscribers() == []
    s.set_alerts_opt_in(u["id"], True)
    assert [x["id"] for x in s.alert_subscribers()] == [u["id"]]
    s.set_alerts_opt_in(u["id"], False)
    assert s.alert_subscribers() == []


def test_tracker_logs_and_summary():
    import tempfile
    from valuation.screener.store import Store
    from valuation.saas import tracker
    from valuation.edge import track
    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p)
    st = Store(p)
    rows = [{"ticker": f"T{i}", "rank": i + 1, "score": 90 if i < 3 else 40,
             "labels": ["Uptrend (>50 & >200 DMA)"] if i < 3 else []} for i in range(15)]
    tracker.log_hot(st, "2026-07-01", rows)
    assert len(st.all_track_picks("hot10")) == 10                 # top-10 only
    tracker.log_options(st, rows, 80)                             # screaming = score≥80 + bullish tag
    assert len(st.all_track_picks("options")) == 3
    # a matured forward return flows into the horizon summary
    st.save_track_return("hot10", "2026-07-01", "T0", 21, 0.05, 0.02)
    s = track.summary(st, "hot10")
    assert s["21"]["n"] == 1 and abs(s["21"]["avg_alpha"] - 0.03) < 1e-9


def test_paper_account_sell_logic():
    import tempfile
    from valuation.screener.store import Store
    from valuation.edge import positions
    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.remove(p)
    st = Store(p)

    def rows(rs, price):   # rs: {ticker: (rank, hot_score)}
        return [{"ticker": t, "rank": rk, "hot_score": sc, "price": price} for t, (rk, sc) in rs.items()]

    kw = dict(top_n=1, min_hold_days=30, max_hold_days=0, exit_score=55)
    # A enters the top-1
    positions.update_positions(st, "hot10", "2026-01-01", rows({"A": (1, 90)}, 100.0), **kw)
    assert any(p["ticker"] == "A" for p in st.open_positions("hot10"))
    # day 10: A's score collapses to 40 but it's < min-hold -> still held (no early churn)
    positions.update_positions(st, "hot10", "2026-01-11", rows({"A": (1, 40)}, 105.0), **kw)
    assert any(p["ticker"] == "A" for p in st.open_positions("hot10"))
    # day 40: still cold (40) and past min-hold -> sold "no longer hot"
    positions.update_positions(st, "hot10", "2026-02-10", rows({"A": (1, 40)}, 110.0), **kw)
    ap = [p for p in st.all_positions("hot10") if p["ticker"] == "A"][0]
    assert ap["exit_date"] and "no longer hot" in (ap["exit_reason"] or "") and ap["exit_price"] == 110.0
    # A gem that stays hot but gets pushed out of the top and held for a year+ is NOT sold:
    positions.update_positions(st, "hot10", "2026-03-01", rows({"C": (1, 92)}, 50.0), **kw)
    positions.update_positions(st, "hot10", "2027-06-01", rows({"E": (1, 96), "C": (12, 85)}, 60.0), **kw)
    assert any(p["ticker"] == "C" for p in st.open_positions("hot10"))   # rank slip alone doesn't sell
    # sizing is score-weighted, capped, and normalizes to 1
    summ = positions.paper_summary(st, "hot10", latest_price_map={"C": 60.0, "E": 100.0},
                                   latest_score_map={"C": 85.0, "E": 96.0}, max_weight=0.20)
    w = summ["watching"]
    assert w and abs(sum(x["weight"] for x in w) - 1.0) < 1e-6


def test_hot_digest_text():
    from valuation.saas.notify import hot_digest_text
    rows = [{"rank": i + 1, "ticker": f"T{i}", "hot_score": 90 - i, "sector": "Technology",
             "price": 100.0 + i} for i in range(12)]
    txt = hot_digest_text("2026-07-27", rows, [{"sector": "Technology"}, {"sector": "Energy"}])
    assert "Hot Stocks of the Day" in txt and "2026-07-27" in txt
    assert "T9" in txt and "T11" not in txt          # top-10 only (T0..T9)
    assert "Technology" in txt


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
    print(f"\n{passed}/{len(tests)} SaaS tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
