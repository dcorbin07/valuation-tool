"""
The PUBLIC posture and the public/demo/owner split (offline, deterministic — no network).

    python tests/test_public.py

Valquo is public and free to anyone, forever, with no billing and no signup. That makes two
claims load-bearing, and this file exists to keep both of them true after the next edit:

1. THE PUBLIC HALF REALLY IS PUBLIC. A visitor with no account gets the valuation tool, the
   ranking, the methodology and the portfolio page — fully rendered, not a teaser. If that
   quietly regresses into a login wall, the posture is a lie in the other direction.

2. THE OWNER HALF REALLY IS HELD BACK. Performance claims (the sandbox paper track), actionable
   live picks (the constructed book, live option alerts, the intraday feed, the portfolio
   builder) and backtest/vendor internals (the Edge Lab) refuse anonymous callers — and refuse
   them OUTRIGHT, not with a partial render. This is a liability boundary and a licence
   boundary at once: Sharadar and ThetaData are backtest-only vendors whose individual terms
   forbid redistribution, so their derived output must not reach a public surface.

3. THE MIDDLE SIDE EXISTS AND IS READ-ONLY. Since 2026-08-07 a valid recruiter master-link
   session (`/demo/<token>`, reached from a button on the portfolio page) reads every owner
   surface and may change nothing. That is an AUTHORIZED widening — Don's decision, recorded
   in PROMPT_recruiter_master_link.md — and the tests below pin the new three-way split
   rather than the old two-way one, so the next auditor sees a decision instead of a posture
   that quietly weakened. Anonymous-vs-owner is unchanged by it.

The complement is tests/test_private.py, which runs the same app with the lockdown ON. Between
them both postures are covered, which is what makes "either flag restores the other" testable.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.config import CONFIG, Config           # noqa: E402
from valuation.saas import surfaces                   # noqa: E402

# Explicit, not inherited from the environment: this suite is meaningless if a stray
# PRIVATE_MODE=true in a .env turns every assertion below into "the lockdown refused it".
CONFIG.private_mode = False
CONFIG.owner_split = True
CONFIG.open_access = True
#: Explicit for the same reason as the flags above: DEMO_ACCESS_TOKEN comes from env, and a
#: machine without one would turn every demo assertion below into "the token was empty", i.e.
#: into a silent skip. A literal here means the demo half of the split is always exercised.
DEMO_TOKEN = "test-demo-token-not-a-real-one"
CONFIG.demo_access_token = DEMO_TOKEN

from valuation.saas.app_saas import create_saas_app   # noqa: E402

APP = create_saas_app(CONFIG)
APP.config["TESTING"] = True
OWNER = sorted(CONFIG.owner_email_set)[0]

#: The surfaces a visitor must be able to read in full. Each is the actual product, not a
#: preview of it.
PUBLIC_PAGES = ("/", "/app", "/methodology", "/terms", "/privacy",
                CONFIG.resolved_portfolio_path)


def _as_owner():
    """Patch `auth.current_user` to return the owner, as tests/test_private.py does."""
    from valuation.saas import auth
    orig = auth.current_user
    auth.current_user = lambda store: {"id": 1, "email": OWNER, "tier": "premium",
                                       "subscription_status": "active", "is_demo": False}
    return orig


def _restore(orig):
    from valuation.saas import auth
    auth.current_user = orig


def _open_demo(c):
    """Open a real preview session through the real route, not by forging a cookie.

    Forging `session["demo"] = True` would skip the token comparison, the rate limit and the
    noindex header — i.e. exactly the three things that make the link's risk manageable. The
    counter is reset first because the limiter is per-IP and process-global, so a suite that
    opens twenty sessions from 127.0.0.1 would otherwise start rate-limiting itself.
    """
    from valuation.saas import ratelimit
    ratelimit.reset()
    r = c.get(f"/demo/{DEMO_TOKEN}")
    assert r.status_code == 302, f"/demo/<token> -> {r.status_code}, not a session"
    return r


# ============================== the posture ================================================
def test_the_instance_is_public_free_and_not_selling_anything():
    """Four flags have to agree, or the posture is only half applied."""
    assert CONFIG.public_access is True, "a stranger must be able to use it"
    assert CONFIG.signup_enabled is False, "there is no public signup — owner account only"
    assert CONFIG.billing_enabled is False, "nothing is for sale; no payment may be initiated"
    assert CONFIG.beta_banner_enabled in (True, False)      # cosmetic; just must not raise
    # A configured Stripe key must not quietly re-open checkout on a free instance.
    assert Config(private_mode=False, open_access=True,
                  stripe_secret_key="sk_test_x").billing_enabled is False


def test_registration_is_closed_and_creates_nothing():
    """'Owner account only' has to hold on POST, not just by hiding the form — a stale link
    or a bookmark reaches the endpoint directly."""
    with APP.test_client() as c:
        with c.session_transaction() as s:
            s["_csrf_token"] = "t"
        r = c.post("/register", data={"email": "stranger@example.com",
                                      "password": "abcdefgh1234", "agree": "1", "_csrf": "t"})
        assert r.status_code in (302, 403, 404), f"/register POST -> {r.status_code}"
        with c.session_transaction() as s:
            assert not s.get("uid"), "an account was created on a closed-signup instance"
            assert not s.get("demo")


# ============================== the split, as policy =======================================
def test_every_api_route_is_knowingly_public_or_knowingly_owner_only():
    """Swept from the app's own URL map. A route added later lands in NEITHER list and fails
    here — which is the point: the split should be a decision someone made, not an omission.
    """
    unclassified = []
    for rule in APP.url_map.iter_rules():
        p = str(rule)
        if not p.startswith("/api/") or "<" in p:
            continue
        if p.startswith("/api/option-alerts/"):
            continue                      # admin-token endpoints; not part of the split
        if p in surfaces.PUBLIC_API or surfaces.is_owner_only(p):
            continue
        unclassified.append(p)
    assert not unclassified, f"unclassified API routes: {sorted(unclassified)}"


def test_the_owner_only_list_covers_every_category_it_claims_to():
    """Pinned by category, so removing an entry has to be a deliberate edit to this test.

    These are the three reasons a surface is held back — a performance claim, an actionable
    live pick, backtest/vendor internals — with one representative of each.
    """
    for performance_claim in ("/api/track", "/api/index-track", "/api/options-paper",
                              "/api/options-scorecard"):
        assert surfaces.is_owner_only(performance_claim), performance_claim
    for live_pick in ("/api/valquo-index", "/api/options-alerts", "/api/signals",
                      "/api/portfolio"):
        assert surfaces.is_owner_only(live_pick), live_pick
    for internals in ("/api/edge/learning", "/api/edge/backtest", "/api/backtest/run",
                      "/api/scan/run"):
        assert surfaces.is_owner_only(internals), internals
    # ...and the analysis stays public.
    for public in ("/api/value", "/api/hotstocks", "/api/whatdo", "/api/tickers",
                   "/api/regime", "/api/health"):
        assert not surfaces.is_owner_only(public), f"{public} must stay public"


def test_the_split_is_a_flag_that_actually_reverts():
    on = Config(private_mode=False, owner_split=True)
    off = Config(private_mode=False, owner_split=False)
    assert surfaces.check("/api/track", None, on) is not None
    assert surfaces.check("/api/track", None, off) is None, "OWNER_SPLIT=false must revert it"
    assert surfaces.may_see_owner_surfaces(None, off) is True
    assert surfaces.may_see_owner_surfaces(None, on) is False
    assert surfaces.may_see_owner_surfaces({"email": OWNER}, on) is True
    # AMENDED 2026-08-07 — PROMPT_recruiter_master_link.md. This used to assert that a demo
    # session may NOT read the owner surfaces. Don's decision reverses that deliberately:
    # the recruiter master-link opens the full READ-ONLY owner view. What has not changed,
    # and is asserted right below, is that a demo session is still not an OWNER — it may
    # read, never act, and `private.is_owner` still refuses it under the licence lockdown.
    demo = {"email": OWNER, "is_demo": True}
    assert surfaces.may_see_owner_surfaces(demo, on) is True, \
        "the recruiter preview reads the owner surfaces (authorized 2026-08-07)"
    assert surfaces.is_owner(demo, on) is False, "a demo session is still not the owner"
    assert surfaces.may_act(demo, on) is False, "and it may still not change anything"


def test_the_demo_preview_is_read_only_under_every_flag_combination():
    """The load-bearing property of the whole change.

    The demo gains owner READ access by a blanket rule, so `DEMO_DENIED_PATHS` is the only
    thing between a link on a résumé and a state change. It is asserted with the split ON and
    OFF because it is deliberately NOT gated on that flag: OWNER_SPLIT is a decision about
    what strangers may READ, and flipping it must never hand the preview the scan trigger.
    """
    demo = {"email": "preview@valquo.demo", "is_demo": True}
    for cfg in (Config(private_mode=False, owner_split=True),
                Config(private_mode=False, owner_split=False)):
        for path in sorted(surfaces.DEMO_DENIED_PATHS):
            d = surfaces.check(path, demo, cfg)
            assert d is not None, f"the preview could reach {path} (owner_split={cfg.owner_split})"
            assert d["status"] == 403
            # ...and the owner is unaffected by it.
            assert surfaces.check(path, {"email": OWNER}, cfg) is None, \
                f"the demo rule blocked the OWNER at {path}"
        assert surfaces.may_act(demo, cfg) is False


def test_every_route_that_writes_is_on_the_demo_denied_list():
    """Swept from the app's own URL map, so a new POST route has to be classified.

    The rule (surfaces.py): a route that writes, or spends the owner's vendor/AI budget, or
    belongs to the account rather than the product, is denied to the preview. POST routes
    that only COMPUTE are the exception and are named here individually, which is what makes
    adding one a deliberate act.
    """
    COMPUTES_ONLY = {
        "/api/value",       # the visitor's own DCF — the product's core action
        "/api/rank",        # scores a watchlist the caller supplied
        "/api/portfolio",   # builds an allocation from the existing snapshot; writes nothing
    }
    EXEMPT_PREFIXES = ("/admin/", "/api/option-alerts/", "/billing/webhook")
    unclassified = []
    for rule in APP.url_map.iter_rules():
        p = str(rule)
        if "POST" not in rule.methods or "<" in p:
            continue
        if p.startswith(EXEMPT_PREFIXES):     # X-Admin-Token / Stripe signature, not sessions
            continue
        if p in ("/login", "/register", "/forgot"):   # auth; a demo session bypasses them
            continue
        if p in COMPUTES_ONLY or surfaces.is_demo_denied(p):
            continue
        unclassified.append(p)
    assert not unclassified, (
        f"POST routes reachable by the read-only preview and not classified: "
        f"{sorted(unclassified)} — add each to surfaces.DEMO_DENIED_PATHS or to "
        f"COMPUTES_ONLY here, with a reason")


# ============================== the split, end to end ======================================
def test_the_public_pages_render_in_full_for_a_visitor():
    """Not a teaser and not a redirect to a login: 200, with real content."""
    with APP.test_client() as c:
        for p in PUBLIC_PAGES:
            r = c.get(p)
            assert r.status_code == 200, f"{p} -> {r.status_code} for an anonymous visitor"
            assert len(r.data) > 1500, f"{p} rendered a stub ({len(r.data)} bytes)"
        for p in ("/api/health", "/api/hotstocks", "/api/tickers?q=AA"):
            assert c.get(p).status_code == 200, f"{p} must serve a visitor"


def test_every_owner_only_api_refuses_a_visitor_outright():
    """403 and an `owner_only` marker — never a 200 with the sensitive half missing. A partial
    render is how a performance claim leaks: the caller cannot tell it was withheld."""
    with APP.test_client() as c:
        for p in sorted(surfaces.OWNER_ONLY_PATHS):
            methods = next(r.methods for r in APP.url_map.iter_rules() if str(r) == p)
            r = c.open(p, method="GET" if "GET" in methods else "POST", json={})
            assert r.status_code == 403, f"{p} -> {r.status_code} for an anonymous caller"
            assert b"owner_only" in r.data, f"{p} refused for the wrong reason"
            body = r.get_data(as_text=True).lower()
            for leak in ("cum_", "excess", "expectancy", "holdings", "occ_symbol"):
                assert leak not in body, f"{p} leaked {leak!r} in its refusal"


def test_the_owner_still_gets_everything():
    orig = _as_owner()
    try:
        with APP.test_client() as c:
            for p in ("/app", "/api/track", "/api/valquo-index", "/api/options-paper",
                      "/api/edge/learning", "/api/signals"):
                r = c.get(p)
                assert r.status_code == 200, f"the owner was blocked from {p} ({r.status_code})"
    finally:
        _restore(orig)


def test_the_dashboard_shows_a_visitor_no_owner_surface_at_all():
    """The tabs are removed from the DOM rather than hidden, so their loaders never fire and
    no owner-only endpoint is called for a visitor in the first place."""
    with APP.test_client() as c:
        html = c.get("/app").get_data(as_text=True)
    for owner_ui in ('id="tab-index"', 'id="tab-track"', 'id="tab-signals"', 'id="tab-edge"',
                     "livebar", "Portfolio builder", "Run scan now"):
        assert owner_ui not in html, f"the public dashboard still renders {owner_ui!r}"
    # And it must not call them either — a fetch that 403s still tells the reader they exist.
    for owner_call in ("/api/track", "/api/valquo-index", "/api/index-track", "/api/signals",
                       "/api/options-paper", "/api/edge/"):
        assert owner_call not in html, f"the public dashboard references {owner_call}"


def test_the_owner_dashboard_keeps_them():
    orig = _as_owner()
    try:
        with APP.test_client() as c:
            html = c.get("/app").get_data(as_text=True)
        for owner_ui in ('id="tab-index"', 'id="tab-track"', 'id="tab-signals"',
                         'id="tab-edge"', "Portfolio builder"):
            assert owner_ui in html, f"the owner lost {owner_ui!r}"
    finally:
        _restore(orig)


def test_the_index_stays_owner_only_and_says_why_on_its_own_face():
    """The Valquo Index tab — holdings plus a cumulative-vs-S&P chart — was re-examined in
    Session 13 and DELIBERATELY left owner-only. Two independent reasons, either sufficient:

      1. it publishes names WITH WEIGHTS as of today, which is an allocation rather than an
         analysis — the exact line the split is drawn on; and
      2. the card above the holdings is a cumulative-return chart against the S&P, which is a
         performance-claim SHAPE whatever caption sits under it, and the public posture is
         "no performance claims in public".

    The middle option (publish the curve, withhold the holdings) was considered and rejected:
    it fails (2) on its own, so it gives up the clarity of one rule and buys nothing.

    The second half of this test is the one that matters if the decision is ever reversed:
    even for the owner, the surface must call itself a MODEL PORTFOLIO on its own face — not
    only in the terms — because a screenshot travels without the terms.
    """
    assert surfaces.is_owner_only("/api/valquo-index")
    assert surfaces.is_owner_only("/api/index-track")
    orig = _as_owner()
    try:
        with APP.test_client() as c:
            html = c.get("/app").get_data(as_text=True)
    finally:
        _restore(orig)
    # collapse whitespace: the copy is wrapped in the template, and re-flowing legal-ish
    # wording to satisfy a substring match is the wrong way round
    low = re.sub(r"\s+", " ", html.lower())
    assert "model portfolio" in low, "the Index never calls itself a model portfolio"
    assert "not a traded account" in low
    assert "no money is invested" in low or "no capital" in low
    assert "the book you would actually hold" not in low, \
        "that copy reads as an allocation the reader should hold"
    # the chart's own caption has to carry it too — a chart is what gets screenshotted
    js = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "valuation", "web", "static", "app.js"), encoding="utf-8").read()
    i = js.index("function indexChart(")
    cap = js[i:js.index("\n}", js.index("STATE.charts.idx", i))]
    assert "MODEL portfolio" in cap and "not fills" in cap, \
        "the cumulative chart's caption does not say what it is"


def test_the_public_landing_carries_no_forward_track():
    """The landing is the most public surface there is, and the forward track is a sandbox
    paper account. It is not computed for a visitor at all, rather than computed and hidden."""
    with APP.test_client() as c:
        html = c.get("/").get_data(as_text=True)
    for claim in ("Valquo Index vs", "paper · live", "Difference", "cum_valquo"):
        assert claim not in html, f"the public landing shows {claim!r}"
    low = html.lower()
    assert "not investment advice" in low or "not advice" in low, "no disclaimer on the landing"


def test_the_name_view_withholds_the_book_and_says_which():
    """`/api/whatdo` spans the public ranking and two owner-only halves. A visitor must still
    get the ranking, and the withheld half must SAY it was withheld — an absent key reads as
    'not in the book', which is a different and false statement."""
    from valuation.web.unified import name_view

    class _Store:
        def latest_scan_date(self):
            return "2026-08-03"

        def load_snapshot(self, *a, **k):
            return [{"ticker": "AAPL", "name": "Apple", "sector": "Technology", "price": 200.0,
                     "hot_score": 91.0, "rank": 1, "composite": 1.4, "bucket": "established",
                     "extra": {}}]

    v = name_view(_Store(), "AAPL", with_options=False, with_book=False)
    assert v["stock"]["in_scan"] is True and v["stock"]["hot_score"] == 91.0, \
        "the public half must survive"
    assert v["stock"]["book_withheld"] is True
    assert v["stock"]["paper_position"] is None
    assert v["stock"]["index"] == {"withheld": True}
    joined = " ".join(l["text"] for l in v["action"] if l.get("text"))
    assert "not published" in joined, "the withholding must be stated, not silent"
    assert "HELD in the Valquo Index" not in joined


# ============================== the demo preview, end to end ===============================
def test_the_demo_session_reads_every_owner_surface():
    """The point of the change, asserted through the real route on the real app.

    THE PROPERTY IS "the preview sees what the OWNER sees", so it is asserted DIFFERENTIALLY:
    each surface is fetched as the owner and as the preview, on the same store, and the two
    answers must agree. Plus the preview must never be turned away by the split itself, which
    is a 403 carrying `owner_only`.

    IT USED TO ASSERT A LITERAL 200 AND THAT WAS WRONG — CI caught it (run #133, and the
    diagnosis is in HANDOFF_appfixes.md §8b before the fix). `/api/portfolio` returns 400
    "No scan snapshot" when there is no snapshot; `data/` is gitignored, so a fresh CI
    checkout has none and a dev worktree does. The old assertion was therefore really
    asserting "a scan snapshot exists", which is not a fact about the split.

    The differential form is STRICTER, not looser: on a populated store it still requires
    owner 200 -> demo 200, on an empty one it requires owner 400 -> demo 400 rather than
    accepting any non-403, and it newly catches a preview that gets a DIFFERENT answer from
    the owner — which the 200-literal version could not see at all.
    """
    paths = [p for p in sorted(surfaces.OWNER_ONLY_PATHS | {"/api/edge/learning"})
             if p not in surfaces.DEMO_DENIED_PATHS]

    def fetch_all(client):
        out = {}
        for p in paths:
            methods = next(r.methods for r in APP.url_map.iter_rules() if str(r) == p)
            r = client.open(p, method="GET" if "GET" in methods else "POST", json={})
            out[p] = (r.status_code, b"owner_only" in r.data)
        return out

    orig = _as_owner()
    try:
        with APP.test_client() as c:
            as_owner = fetch_all(c)
    finally:
        _restore(orig)
    with APP.test_client() as c:
        _open_demo(c)
        as_demo = fetch_all(c)

    for p in paths:
        o_status, o_owner_only = as_owner[p]
        d_status, d_owner_only = as_demo[p]
        assert not d_owner_only, f"the split refused the preview at {p}"
        assert d_status != 403, f"the preview was refused {p} (403)"
        assert d_status == o_status, (
            f"{p}: the owner got {o_status} and the preview got {d_status} — the preview is "
            f"supposed to see what the owner sees")
        assert not o_owner_only, f"{p} refused the OWNER — fix that first"


def test_the_demo_session_may_not_change_anything():
    """The other half, and the one that matters if the link travels.

    Asserted with a VALID CSRF token so that a 403 here means the policy refused it, not
    that the form check happened to fire first — those are different guarantees and only one
    of them is the one being claimed.
    """
    # NON-VACUITY PIN, added after a mutation check (2026-08-07). This test LOOPS OVER the
    # very set it is checking, so emptying `DEMO_DENIED_PATHS` made it pass with an empty
    # loop — measured, not theorised: the mutation run reported it "blind" while the preview
    # could reach every trigger. Naming the routes here means the set cannot be gutted
    # without a test saying so, and it is the four that actually spend money or corrupt state.
    for critical in ("/api/scan/run", "/api/signals/run", "/api/edge/optimize",
                     "/account/alerts"):
        assert critical in surfaces.DEMO_DENIED_PATHS, \
            f"{critical} fell off the demo denied list — the preview can now reach it"

    with APP.test_client() as c:
        _open_demo(c)
        with c.session_transaction() as s:
            s["_csrf_token"] = "tok"
        from valuation.saas import csrf
        for p in sorted(surfaces.DEMO_DENIED_PATHS):
            methods = next(r.methods for r in APP.url_map.iter_rules() if str(r) == p)
            method = "GET" if "GET" in methods else "POST"
            if csrf.needs_protection(p, method):
                # `csrf.validate` reads request.form ONLY, so a JSON body would be rejected
                # at 400 before the policy ever ran and this test would prove nothing.
                r = c.post(p, data={csrf.FIELD: "tok"})
            else:
                r = c.open(p, method=method, json={})
            assert r.status_code == 403, f"the preview reached {p} ({r.status_code})"
            body = r.get_data(as_text=True).lower()
            assert "read-only preview" in body, \
                f"{p} refused the preview for the wrong reason: {body[:120]!r}"


def test_the_demo_dashboard_shows_the_owner_tabs_and_none_of_the_triggers():
    """Rendered HTML, not policy. A trigger the API will refuse is worse than no trigger:
    it teaches the reader the tool is broken rather than that the preview is read-only."""
    with APP.test_client() as c:
        _open_demo(c)
        html = c.get("/app").get_data(as_text=True)
    for owner_ui in ('id="tab-index"', 'id="tab-track"', 'id="tab-signals"', 'id="tab-edge"',
                     "Portfolio builder", "Self-learning log"):
        assert owner_ui in html, f"the preview lost {owner_ui!r}"
    for trigger in ("Run scan now", "Refresh signals now", "Backtest vs SPY",
                    "Walk-forward optimize", "Update track record"):
        assert trigger not in html, f"the read-only preview renders the trigger {trigger!r}"
    # It must also say what it is. "Everything unlocked" was true when the preview saw the
    # public half; since it sees the owner view, read-only is the honest word.
    assert "read-only" in html.lower(), "the preview never tells the reader it is read-only"


def test_the_demo_view_keeps_every_disclaimer_the_owner_view_carries():
    """The demo view IS the owner view, so this should hold by construction — which is
    exactly why it is worth pinning, since 'by construction' is how a caveat goes missing."""
    with APP.test_client() as c:
        _open_demo(c)
        demo = re.sub(r"\s+", " ", c.get("/app").get_data(as_text=True).lower())
    orig = _as_owner()
    try:
        with APP.test_client() as c:
            owner = re.sub(r"\s+", " ", c.get("/app").get_data(as_text=True).lower())
    finally:
        _restore(orig)
    for phrase in ("not investment advice", "model portfolio", "not a traded account",
                   "no money is invested", "risk of loss", "not an autotrader"):
        assert phrase in owner, f"the OWNER view lost {phrase!r} — fix that first"
        assert phrase in demo, f"the preview path dropped {phrase!r}"


def test_the_work_button_carries_the_current_token_and_rotation_kills_old_links():
    """The whole security model of the button, as three assertions.

    Rotating DEMO_ACCESS_TOKEN on Render must (a) re-point the button with no deploy, (b)
    invalidate every /demo/<token> URL copied out of it, and (c) remove the button entirely
    when the token is cleared. If any of those stops holding, the kill switch is gone.
    """
    href = re.compile(r'class="demo-cta" href="([^"]*)"')
    with APP.test_client() as c:
        m = href.search(c.get(CONFIG.resolved_portfolio_path).get_data(as_text=True))
    assert m and m.group(1) == f"/demo/{DEMO_TOKEN}", "the button does not carry the token"

    CONFIG.demo_access_token = "rotated-token-value"
    try:
        with APP.test_client() as c:
            m = href.search(c.get(CONFIG.resolved_portfolio_path).get_data(as_text=True))
            assert m and m.group(1) == "/demo/rotated-token-value", \
                "rotation did not re-point the button"
            _open_demo_expect_refusal(c, DEMO_TOKEN)
        CONFIG.demo_access_token = ""
        with APP.test_client() as c:
            body = c.get(CONFIG.resolved_portfolio_path).get_data(as_text=True)
            assert not href.search(body), "the button survives an empty token"
            _open_demo_expect_refusal(c, DEMO_TOKEN)
    finally:
        CONFIG.demo_access_token = DEMO_TOKEN


def _open_demo_expect_refusal(c, token):
    from valuation.saas import ratelimit
    ratelimit.reset()
    c.get(f"/demo/{token}")
    with c.session_transaction() as s:
        assert not s.get("demo"), f"a stale /demo/{token[:6]}... link still opened a session"


def test_every_demo_response_refuses_indexing_including_the_refusals():
    """The redirects matter as much as the successes — a 302 with a Location is precisely
    what a crawler follows, and the link now sits behind a button on a public page."""
    for token in (DEMO_TOKEN, "wrong-token"):
        with APP.test_client() as c:
            from valuation.saas import ratelimit
            ratelimit.reset()
            r = c.get(f"/demo/{token}")
            assert "noindex" in (r.headers.get("X-Robots-Tag") or ""), \
                f"/demo/{token[:5]}... -> {r.status_code} with no X-Robots-Tag"


def test_demo_session_creation_is_rate_limited():
    """A leaked token should show up as refused traffic rather than being farmed silently."""
    from valuation.saas import ratelimit
    ratelimit.reset()
    limit = ratelimit.LIMITS["demo:session"][0]
    with APP.test_client() as c:
        codes = [c.get(f"/demo/{DEMO_TOKEN}").status_code for _ in range(limit + 2)]
    assert 429 in codes, f"unlimited demo-session creation: {codes}"
    assert codes[0] == 302, "the limit fired before the first legitimate visit"
    ratelimit.reset()


def test_a_demo_session_is_still_not_the_owner():
    """The line that must not move. Owner-only-vs-anonymous is untouched by this change, and
    the licence lockdown still refuses a preview outright."""
    from valuation.saas import private
    demo = {"email": OWNER, "is_demo": True}
    assert private.is_owner(demo, CONFIG) is False
    assert surfaces.is_owner(demo, CONFIG) is False
    with APP.test_client() as c:
        _open_demo(c)
        # /account is the account surface, not the product: refused even though the
        # preview may read every performance-shaped surface there is.
        assert c.get("/account").status_code == 403


# ============================== liability copy =============================================
def test_every_public_surface_carries_the_disclaimer():
    """'Visible on every public surface, not buried.' Asserted per page, because the failure
    mode is one template quietly losing the footer."""
    with APP.test_client() as c:
        for p in PUBLIC_PAGES:
            body = c.get(p).get_data(as_text=True).lower()
            assert "not investment advice" in body, f"{p} has no not-advice line"
            assert ("risk of loss" in body or "risk" in body), f"{p} does not mention risk"


def test_the_terms_carry_the_four_clauses_the_posture_depends_on():
    with APP.test_client() as c:
        # Whitespace-collapsed: these clauses are long enough to wrap in the template, and a
        # test that breaks on a line break trains people to reflow legal copy to please it.
        body = re.sub(r"\s+", " ", c.get("/terms").get_data(as_text=True)).lower()
    for clause, why in (
            ("no advisory", "no advisory relationship"),
            ("without warranties of any kind", "no warranty"),
            ("not liable", "limitation of liability"),
            ("no duty to update", "no duty to maintain"),
            ("historical simulation", "backtests labelled as simulation"),
            ("no real money", "the paper account labelled")):
        assert clause in body, f"the Terms lost {why}"
    # The old draft described a subscription that no longer exists, in placeholders.
    assert "[date published]" not in body and "[company llc" not in body, \
        "the Terms still carry unfilled placeholders"
    assert "attorney review required" not in body, \
        "a public draft banner tells the reader the disclaimer is not meant seriously"


def test_no_public_surface_makes_a_performance_claim():
    """The one thing a free educational site must never read as. Numbers that could be taken
    for realised returns are owner-only; anything quoted publicly must wear its label."""
    with APP.test_client() as c:
        for p in PUBLIC_PAGES:
            body = c.get(p).get_data(as_text=True)
            low = body.lower()
            for banned in ("track record since inception", "our returns", "we returned",
                           "annualized return of", "profit since"):
                assert banned not in low, f"{p} reads as a performance claim: {banned!r}"
            # The backtested alpha figure is permitted (audit R1 cleared its pre-registered
            # threshold) but only alongside the words that stop it being read as a return.
            if re.search(r"\b8\.81\b", body):
                assert "historical simulation" in low or "backtest" in low, \
                    f"{p} prints the alpha with no simulation label"
                assert "not an expected" in low, f"{p} prints the alpha as achievable"


def test_the_owner_login_exists_but_does_not_compete_with_the_product():
    """Unobtrusive by requirement: a small footer link, not a call to action in the nav."""
    with APP.test_client() as c:
        landing = c.get("/").get_data(as_text=True)
    assert 'href="/login"' in landing, "the owner needs a way in"
    assert "Owner login" in landing
    assert 'href="/login" class="cta"' not in landing, "login must not be a nav CTA"
    assert 'href="/register"' not in landing, "there is no public signup to advertise"


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
    print(f"\n{passed}/{len(tests)} public-posture tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
