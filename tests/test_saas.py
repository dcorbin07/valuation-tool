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

# Most tests below exercise the REAL per-tier gating. Two launch-time overrides that
# unlock everything are turned off here so the tier assertions mean something; the
# beta/demo/open-access tests re-enable them locally.
#   beta_all_premium -> Premium for every signed-in account
#   open_access      -> the whole product free, no account at all (current default)
CONFIG.beta_all_premium = False
CONFIG.open_access = False
# THREE overrides now. private_mode ships DEFAULT TRUE (Valquo is a personal research tool —
# see config.py), and under it there are no tiers, no signup and no anonymous reader, so every
# tier assertion in this file would be asserting against a product that is switched off.
#
# Turning it off here is not a workaround: this suite is what proves the PUBLIC product still
# works, which is the thing `PRIVATE_MODE=false` is promised to restore. If these tests only
# ran in private mode, "flipping the flag back brings the product back" would be an untested
# claim. The lockdown itself is tested in tests/test_private.py.
CONFIG.private_mode = False


def _csrf(c):
    """Establish a CSRF token on this client and return it (SECURITY_AUDIT.md M2).

    Real browsers get one from the hidden field the context processor renders into every
    form; a test client can just seed the session directly."""
    with c.session_transaction() as s:
        s["_csrf_token"] = "test-csrf-token"
    return "test-csrf-token"


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
    # beta_mode is turned on locally: it ships DEFAULT FALSE since the public+free posture
    # landed (its copy promised a paid product later), and this test is about what the banner
    # SAYS when there is a beta, not about whether there is one.
    CONFIG.beta_mode = True
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
    CONFIG.demo_access_token = ""                     # restore default (M4: no default token)
    CONFIG.beta_mode = False


def test_demo_signup_converts_to_real_account():
    # Signing up from the preview should drop the demo flag and take over as a real account.
    import uuid
    CONFIG.beta_mode = True                            # see the note in the test above
    CONFIG.demo_access_token = "sekret-xyz"
    from valuation.saas.app_saas import create_saas_app
    app = create_saas_app(CONFIG); app.config.update(TESTING=True)
    c = app.test_client()
    c.get("/demo/sekret-xyz")                          # enter the preview
    assert b"get ahead of the beta" in c.get("/app").data
    email = "conv_" + uuid.uuid4().hex[:8] + "@ex.com"
    r = c.post("/register", data={"email": email, "password": "password123",
                                  "agree": "on", "_csrf": _csrf(c)})
    assert r.status_code in (301, 302)                 # redirected to /app as the new user
    after = c.get("/app").data
    assert b"get ahead of the beta" not in after       # demo flag cleared → generic banner
    CONFIG.demo_access_token = ""
    CONFIG.beta_mode = False


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


def test_open_access_makes_everything_free_and_anonymous():
    """OPEN_ACCESS: the whole product, for everyone, with no account and no checkout.

    Restores the flag afterwards so the per-tier tests around it keep meaning something.
    """
    s = _store()
    CONFIG.open_access = True
    try:
        # An anonymous visitor is treated as the top tier.
        assert gating._active(None) == "premium"
        assert gating.features(gating._active(None))["hotstocks_top"] == 500
        # Every previously gated or login-walled route is open, with no user at all.
        for path, body in (("/api/value", {"ticker": "NKE"}),
                           ("/api/signals", {}), ("/api/signals/run", {}),
                           ("/api/backtest/run", {}), ("/api/portfolio", {}),
                           ("/api/export/excel", {}), ("/api/export/pdf", {}),
                           ("/api/optimize/run", {}),
                           ("/api/scan/run", {"scope": "whole_market"})):
            assert gating.check_request(path, "POST", body, None, s) is None, path
        # No daily cap: well past the old free limit of 5.
        u = s.create_user("open@b.com", "password123")
        for _ in range(12):
            assert gating.check_request("/api/value", "POST", {"ticker": "NKE"}, u, s) is None
        # Nothing to sell while it's free.
        assert CONFIG.billing_enabled is False
        # The owner research bench is still NOT public - it's not a withheld feature.
        assert gating.check_request("/api/edge/backtest", "POST", {}, None, s)[1] == 403
    finally:
        CONFIG.open_access = False


def test_open_access_off_restores_the_paywall():
    """The flag must be a genuine switch, not a one-way door."""
    s = _store()
    assert CONFIG.open_access is False           # module default for these tests
    assert gating._active(None) == "anon"
    assert gating.check_request("/api/backtest/run", "POST", {}, None, s)[1] == 401


def test_valquo_index_is_a_slice_of_the_hot_stocks_ranking():
    """One ranking, two views: the Index must be built from the SAME snapshot the Hot Stocks
    tab reads, so there is never a second competing screen. The account toggle switches which
    validated construction is applied."""
    from valuation.screener import settings as S
    from valuation.edge.valquo_index import build_index
    # A realistic ranked snapshot: 400 large caps, descending hot score.
    rows = [{"ticker": f"T{i:03d}", "hot_score": 100.0 - i * 0.2, "price": 50.0,
             "market_cap": 5e10, "rank": i + 1} for i in range(400)]
    roth = build_index(rows, top_n=S.BOOK_CONFIGS["roth"]["top_n"])
    tax = build_index(rows, top_decile=S.BOOK_CONFIGS["taxable"]["top_frac"])
    assert roth["n_positions"] == 25, roth["n_positions"]
    assert tax["n_positions"] == 40, tax["n_positions"]        # decile of 400 eligible
    # Both must be TOP slices of the same order — the Index never reorders the ranking.
    assert [p["ticker"] for p in roth["positions"]] == [f"T{i:03d}" for i in range(25)]
    assert [p["ticker"] for p in tax["positions"][:25]] == [p["ticker"] for p in roth["positions"]]
    # ...so roth is strictly contained in taxable: one ranking, two cuts of it.
    assert set(p["ticker"] for p in roth["positions"]) <= set(p["ticker"] for p in tax["positions"])


def test_valquo_index_api_config_toggle():
    """The endpoint's own contract. The Index became OWNER-ONLY when the public/owner split
    landed (saas/surfaces.py), so the split is switched off for the duration — this test is
    about the config toggle, and the access policy is tested in tests/test_public.py."""
    from valuation.saas.app_saas import create_saas_app
    CONFIG.owner_split = False
    try:
        _valquo_index_config_toggle(create_saas_app().test_client())
    finally:
        CONFIG.owner_split = True


def _valquo_index_config_toggle(c):
    bad = c.get("/api/valquo-index?config=nonsense")
    assert bad.status_code == 400 and "known" in bad.get_json()
    for name in ("roth", "taxable"):
        r = c.get(f"/api/valquo-index?config={name}")
        assert r.status_code == 200
        j = r.get_json()
        if not j.get("empty"):
            assert j["config"]["name"] == name
            assert j["config"]["rebalance_months"]
            assert "same scan snapshot" in j.get("source_note", "")
    # The Hot Stocks page carries both blurbs and the toggle. Asserted on the TEMPLATE rather
    # than a rendered /app, because whether /app renders depends on CONFIG.open_access, which
    # sibling tests in this module flip — that is auth state, not what this test is about.
    import os as _os
    _tpl = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                         "valuation", "web", "templates", "index.html")
    with open(_tpl, encoding="utf-8") as _fh:
        h = _fh.read()
    assert 'id="bookConfig"' in h, "account-type toggle missing"
    # The second blurb moved inside the owner-only block when the Index tab did, and was
    # re-worded there; matched on the phrase that survives the line break.
    assert "discovery" in h and "backtested top-slice" in h, "blurbs missing"


def test_methodology_page_is_public_and_states_the_weaknesses():
    """The methodology page is the trust moat — it is worthless if it only lists strengths,
    and it must not sit behind a login."""
    from valuation.saas.app_saas import create_saas_app
    app = create_saas_app(CONFIG)
    app.config.update(TESTING=True)
    c = app.test_client()
    r = c.get("/methodology")
    assert r.status_code == 200
    body = r.data.decode("utf-8", "ignore").lower()
    for must in ("point-in-time", "survivorship", "breakeven", "not investment advice"):
        assert must in body, f"methodology must cover {must!r}"
    # The honest half. If these go missing the page has become marketing.
    # "undeflated" replaces the old "saturated": audit B9 found the statistic is not a
    # Deflated Sharpe at all, and the page now discloses the mislabelling rather than the
    # symptom. Both are asserted so a future edit cannot drop the correction and keep the
    # softer word.
    for weakness in ("one 18-year", "saturates", "undeflated", "dormant"):
        assert weakness in body, f"methodology must keep the weakness: {weakness!r}"
    # The alpha figure is permitted (audit R1 cleared its pre-registered threshold) but only
    # wearing its labels. A page that prints +8.81% without them is the exact failure this
    # whole posture exists to prevent.
    if "8.81" in body:
        for label in ("historical simulation", "not an expected", "placebo"):
            assert label in body, f"the alpha figure lost its label: {label!r}"


def test_landing_renders_the_sample_and_survives_having_none():
    """The landing must SHOW the product. It must also still be a finished page when nothing
    has been ingested yet — a broken hero is worse than a plain one, and this is the first
    thing a visitor ever sees."""
    from valuation.saas.app_saas import create_saas_app
    from valuation.web import showcase

    sample = {"ticker": "TSTQ", "name": "Test Corp", "sector": "Technology", "price": 100.0,
              "fair_value": 150.0, "upside": 0.5, "score": 72.0, "verdict": "Buy",
              "confidence": "high", "bear": 120.0, "base": 150.0, "bull": 190.0,
              "implied_growth": 0.04, "base_growth": 0.09, "implied_growth_bounded": "",
              "as_of": "2026-08-02"}

    real_ctx = showcase.landing_context
    # **kw, not a bare `store`: landing_context gained `with_track` when the owner split
    # landed, and a stub that does not accept it raises inside the route's try/except — which
    # renders the fallback page and fails these assertions for the wrong reason.
    showcase.landing_context = lambda store, **kw: {
        "sample": sample, "bar": showcase.range_bar(sample), "sample_stale": False,
        "sample_age": 0, "track": None, "spark": None, "scan": None}
    try:
        c = create_saas_app(CONFIG).test_client()
        html = c.get("/").data.decode()
        assert "TSTQ" in html and "Test Corp" in html
        assert "150.00" in html and "72" in html
        assert "4% a year" in html, "the reverse-DCF read is the most persuasive number"
    finally:
        showcase.landing_context = real_ctx

    # Nothing ingested: no exception, no empty widget, still a real page with the CTA.
    showcase.landing_context = lambda store: {}
    try:
        c = create_saas_app(CONFIG).test_client()
        r = c.get("/")
        assert r.status_code == 200
        html = r.data.decode()
        assert "Live sample" not in html
        # Asserted on the static section, not the CTA: the CTA wording flips with
        # signup_enabled, which other tests in this file mutate on the shared CONFIG.
        assert "Adaptive DCF" in html and "Valquo" in html
    finally:
        showcase.landing_context = real_ctx


def test_landing_never_500s_when_the_showcase_blows_up():
    """The store can be missing or corrupt on a fresh box. That must cost a section, not the
    home page."""
    from valuation.saas.app_saas import create_saas_app
    from valuation.web import showcase

    real = showcase.landing_context

    def _boom(store):
        raise RuntimeError("store exploded")
    showcase.landing_context = _boom
    try:
        r = create_saas_app(CONFIG).test_client().get("/")
        assert r.status_code == 200, r.status_code
        assert "Adaptive DCF" in r.data.decode(), "the static page must still be there"
    finally:
        showcase.landing_context = real


def test_sample_ingest_requires_a_token_and_rejects_an_empty_sample():
    from valuation.saas.app_saas import create_saas_app
    CONFIG.admin_token = "tok-123"
    c = create_saas_app(CONFIG).test_client()
    good = {"ticker": "AAPL", "fair_value": 119.6, "as_of": "2026-08-02"}
    assert c.post("/admin/ingest-sample", json=good).status_code == 401
    hdr = {"X-Admin-Token": "tok-123"}
    # A sample with no fair value renders an empty hero — refuse it rather than publish it.
    assert c.post("/admin/ingest-sample", json={"ticker": "AAPL"}, headers=hdr).status_code == 400
    assert c.post("/admin/ingest-sample", json={}, headers=hdr).status_code == 400
    assert c.post("/admin/ingest-sample", json=good, headers=hdr).status_code == 200


def test_paper_track_endpoint_skips_when_the_session_has_not_closed():
    """The scheduled cycle must refuse to run mid-session.

    The crons are pinned to a fixed UTC time, but 4pm Eastern moves an hour against UTC twice
    a year — 20:45 UTC is 4:45pm ET in summer and 3:45pm ET in WINTER. Without this guard the
    whole winter would have been marked and entered on intraday prices, and every run would
    have looked completely normal. The skip must also be visibly a skip, not an empty success.
    """
    import datetime as dt
    from valuation.saas.app_saas import create_saas_app
    from valuation.screener import market_session as MS

    real = MS.session_state
    MS.session_state = lambda now=None: real(dt.datetime(2026, 8, 5, 15, 45))   # mid-session
    try:
        CONFIG.admin_token = "tok-123"
        app = create_saas_app(CONFIG)
        app.config.update(TESTING=True)
        c = app.test_client()
        assert c.post("/admin/run-paper-track", json={}).status_code == 401
        r = c.post("/admin/run-paper-track", json={}, headers={"X-Admin-Token": "tok-123"})
        assert r.status_code == 200, r.data
        body = r.get_json()
        assert body.get("skipped") is True, body
        assert "not closed" in body["session"]["reason"], body["session"]
    finally:
        MS.session_state = real


def test_index_track_ingest_requires_the_admin_token():
    """The live-track ingest writes what the site publishes as its real performance record.
    An open endpoint would let anyone post a track."""
    from valuation.saas.app_saas import create_saas_app
    CONFIG.admin_token = "tok-123"
    app = create_saas_app(CONFIG)
    app.config.update(TESTING=True)
    c = app.test_client()
    payload = {"inception_date": "2026-07-01", "benchmark": "SPY",
               "series": [{"date": "2026-07-01", "valquo": 0.5, "spy": 0.3}]}
    assert c.post("/admin/ingest-index-track", json=payload).status_code == 401
    ok = c.post("/admin/ingest-index-track", json=payload, headers={"X-Admin-Token": "tok-123"})
    assert ok.status_code == 200, ok.data
    assert ok.get_json()["days"] == 1
    # An empty series is a no-op, not a way to blank the published record.
    bad = c.post("/admin/ingest-index-track", json={"series": []},
                 headers={"X-Admin-Token": "tok-123"})
    assert bad.status_code == 400


def test_forgot_never_discloses_a_reset_link_in_production():
    """SECURITY_AUDIT.md C1 — account takeover via /forgot.

    The old code set `dev_link = None if sent else link`, and `send_email` returned False
    for BOTH "no SMTP configured" and "the send threw". So a production mail server merely
    being down turned /forgot into: POST any address, get a valid 1-hour reset token. The
    owner address is a committed default, and the owner account unlocks /api/edge/*.

    A reset link may ONLY appear when DEV_MODE is explicitly set AND no SMTP exists.
    """
    import uuid
    from valuation.saas import auth as auth_mod
    from valuation.saas import emailer
    from valuation.saas.app_saas import create_saas_app

    app = create_saas_app(CONFIG)
    app.config.update(TESTING=True)
    c = app.test_client()

    # A real account, in the same database the app's store is bound to.
    real = "fgt_" + uuid.uuid4().hex[:8] + "@ex.com"
    UserStore(CONFIG.database_url).create_user(real, "password123")
    unknown = "nobody_" + uuid.uuid4().hex[:8] + "@ex.com"

    orig_send, orig_dev = auth_mod.send_status, CONFIG.dev_mode
    try:
        # --- 1. Production, SMTP configured but FAILING: no token, ever. ---
        CONFIG.dev_mode = False
        auth_mod.send_status = lambda *a, **k: emailer.FAILED
        tok = _csrf(c)
        body = c.post("/forgot", data={"email": real, "_csrf": tok}).data.decode("utf-8", "ignore")
        assert "/reset/" not in body, "a failing prod mail server must not leak a reset link"

        # --- 2. No account-enumeration tell: byte-identical response either way. ---
        miss = c.post("/forgot", data={"email": unknown, "_csrf": tok}).data.decode("utf-8", "ignore")
        assert body == miss, "response differs for a known vs unknown address"

        # --- 3. Not configured at all, but still not DEV_MODE: still no token. ---
        auth_mod.send_status = lambda *a, **k: emailer.NOT_CONFIGURED
        b3 = c.post("/forgot", data={"email": real, "_csrf": tok}).data.decode("utf-8", "ignore")
        assert "/reset/" not in b3, "absent SMTP alone must not imply a dev box"

        # --- 4. DEV_MODE + no SMTP: the local convenience still works... ---
        CONFIG.dev_mode = True
        b4 = c.post("/forgot", data={"email": real, "_csrf": tok}).data.decode("utf-8", "ignore")
        assert "/reset/" in b4, "DEV_MODE with no SMTP should still surface the link locally"

        # --- 5. ...but even in DEV_MODE a mere send FAILURE discloses nothing. ---
        auth_mod.send_status = lambda *a, **k: emailer.FAILED
        b5 = c.post("/forgot", data={"email": real, "_csrf": tok}).data.decode("utf-8", "ignore")
        assert "/reset/" not in b5, "send failure must never be treated as 'we're in dev'"
    finally:
        auth_mod.send_status, CONFIG.dev_mode = orig_send, orig_dev


def test_post_recap_endpoint_is_gated_validated_and_quiet_without_a_webhook():
    """The recap trigger the daily/weekly crons call.

    NOTE the webhook is cleared for the duration: this test must never be able to post into a
    real Discord channel from a developer's machine, and clearing it also exercises the path
    the crons will hit until Don sets the secret.
    """
    from valuation.saas.app_saas import create_saas_app
    orig_token, orig_hook = CONFIG.admin_token, CONFIG.discord_webhook_url
    CONFIG.admin_token, CONFIG.discord_webhook_url = "test-admin-recap", ""
    try:
        c = create_saas_app(CONFIG).test_client()
        hdr = {"X-Admin-Token": "test-admin-recap"}
        assert c.post("/admin/post-recap", json={"kind": "daily"}).status_code == 401
        assert c.post("/admin/post-recap", json={"kind": "daily"},
                      headers={"X-Admin-Token": "nope"}).status_code == 401
        bad = c.post("/admin/post-recap", json={"kind": "monthly"}, headers=hdr)
        assert bad.status_code == 400, bad.get_json()
        # force skips the market-session guard so the real build/post path runs here.
        r = c.post("/admin/post-recap", json={"kind": "weekly", "force": True}, headers=hdr)
        assert r.status_code == 200, r.get_json()
        body = r.get_json()
        assert body["ok"] is True and body["posted"] is False
        assert "DISCORD_WEBHOOK_URL" in body["reason"], body
    finally:
        CONFIG.admin_token, CONFIG.discord_webhook_url = orig_token, orig_hook


# The custom-backtest UI block in app.js (runBacktest / renderBacktest / eqChart / qChart /
# renderBtStats) references a form that is no longer in index.html, and nothing calls it. It
# is dead, not broken, and removing it is a separate decision from this test — but it must not
# grow, and it must not hide a genuine typo in a live feature.
_KNOWN_ORPHAN_IDS = {
    "btBench", "btCost", "btErr", "btHorizon", "btLoader", "btRebal", "btResults",
    "btSource", "btStats", "btTickers", "btVerdict", "eqChart", "qChart",
}


def test_every_element_the_dashboard_writes_to_actually_exists():
    """A renamed id fails silently: the write lands on nothing and the panel just stays blank.

    Nothing else in the stack catches that — the Python tests never touch the DOM, and the
    page renders fine with a dead panel in it. So the wiring is checked statically.
    """
    import re
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    js = open(os.path.join(root, "valuation", "web", "static", "app.js"), encoding="utf-8").read()
    html = open(os.path.join(root, "valuation", "web", "templates", "index.html"),
                encoding="utf-8").read()

    refs = set(re.findall(r'getElementById\("([A-Za-z0-9_-]+)"\)', js))
    refs |= set(re.findall(r'setHtml\("([A-Za-z0-9_-]+)"', js))
    refs |= set(re.findall(r'\beshow\("([A-Za-z0-9_-]+)"', js))
    # `toggle("id", on)` is the app's own helper; `classList.toggle("active")` is not.
    refs |= set(re.findall(r'(?<!classList\.)\btoggle\("([A-Za-z0-9_-]+)",', js))

    ids = set(re.findall(r'id="([A-Za-z0-9_-]+)"', html))
    missing = refs - ids - _KNOWN_ORPHAN_IDS
    assert not missing, f"app.js writes to elements that do not exist: {sorted(missing)}"

    # And the dead block has not grown.
    still_dead = (refs & _KNOWN_ORPHAN_IDS) - ids
    assert still_dead == _KNOWN_ORPHAN_IDS - ids, (
        "the known-dead backtest UI changed — re-check whether it is live now: "
        f"{sorted(still_dead)}")


def test_the_new_ui_surfaces_are_wired_to_real_elements():
    """Named explicitly, so a rename of one of THESE is a loud failure, not an allowlist edit."""
    import re
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html = open(os.path.join(root, "valuation", "web", "templates", "index.html"),
                encoding="utf-8").read()
    ids = set(re.findall(r'id="([A-Za-z0-9_-]+)"', html))
    for needed in ("whatDoCard", "whatDoBody", "hotCache", "indexCache",
                   "hotTable", "valquoIndexBody", "indexPerfBody", "trackResults"):
        assert needed in ids, needed


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
