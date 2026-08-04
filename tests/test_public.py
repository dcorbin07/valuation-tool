"""
The PUBLIC posture and the owner split (offline, deterministic — no network).

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
    assert surfaces.may_see_owner_surfaces({"email": OWNER, "is_demo": True}, on) is False, \
        "a demo session is not the owner"


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
