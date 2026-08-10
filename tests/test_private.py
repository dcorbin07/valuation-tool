"""
Private mode + track backup (offline, deterministic — temp DBs, no network).

    python tests/test_private.py

Two things are pinned here, and they are the two that would be expensive to get wrong.

1. THE LOCKDOWN. Valquo runs on market data licensed under INDIVIDUAL, personal-use terms
   (ThetaData Individual, Sharadar individual). "Personal use" is a claim about who can read
   the numbers, so a leak is a licence problem, not just a privacy one. The tests below are
   written so that ADDING a route cannot quietly open a hole: the allowlist is asserted to be
   exactly what it is, and every /api route registered on the app is swept.

2. THE BACKUP. The forward paper track cannot be re-derived — it is a record of what the model
   said on days that have already happened. These tests check the export actually contains it,
   is byte-stable across runs (so a weekly commit diffs only on real change), and degrades
   safely on an empty database rather than writing a confident-looking empty file.

The COMPLEMENT of this file is tests/test_saas.py and tests/test_security.py, which both turn
private mode OFF and test the public product. Between them, both sides of the flag are covered
— which is what makes "PRIVATE_MODE=false restores the product" a tested claim.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.config import CONFIG, Config          # noqa: E402
from valuation.saas import private                   # noqa: E402

# Explicit, not inherited from the environment: this suite is meaningless if a stray
# PRIVATE_MODE=false in a .env turns it into a no-op that still reports PASS.
CONFIG.private_mode = True

from valuation.saas.app_saas import create_saas_app  # noqa: E402
from valuation.saas.models import UserStore          # noqa: E402

APP = create_saas_app(CONFIG)
APP.config["TESTING"] = True
OWNER = sorted(CONFIG.owner_email_set)[0]


def _users():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return UserStore("sqlite:///" + path.replace("\\", "/"))


def _csrf(c):
    with c.session_transaction() as s:
        s["_csrf_token"] = "t"
    return "t"


def _as_owner(c):
    """A session for the owner, seeded directly.

    The store the app was built with is not the one this test can construct, so the session
    is seeded with the uid and the app's own `current_user` resolves it. Simpler than
    round-tripping a login form, and it tests the same thing: private mode reads the resolved
    user, not the login flow.
    """
    from valuation.saas import auth
    orig = auth.current_user

    def patched(store):
        return {"id": 1, "email": OWNER, "tier": "premium",
                "subscription_status": "active", "is_demo": False}
    auth.current_user = patched
    return orig


def _restore(orig):
    from valuation.saas import auth
    auth.current_user = orig


# ============================== the flag itself ============================================
def test_private_mode_is_off_by_default_but_still_works_when_asked_for():
    """DEFAULT CHANGED TO FALSE (2026-08-04): Valquo is public and free, with the sensitive
    half held back by the owner split (saas/surfaces.py) rather than by locking the door.

    The flag is not deleted and this whole suite still runs it ON, which is what keeps
    "PRIVATE_MODE=true restores the personal-tool posture" a tested claim rather than a
    promise. The parse is asserted too: `== "true"` and not `!= "false"`, so a typo'd or
    empty value comes up PUBLIC-with-the-split rather than half-locked.
    """
    import valuation.config as C
    src = open(C.__file__, encoding="utf-8").read()
    assert '_get("PRIVATE_MODE", "false").lower() == "true"' in src, \
        "PRIVATE_MODE must default to false now; the lockdown is opt-in"
    assert Config(private_mode=True).private_mode is True    # ...and still honoured


def test_private_mode_overrides_every_flag_that_would_open_the_product():
    """A lockdown any other flag can undo is not a lockdown.

    open_access, BETA_ALL_PREMIUM and an explicit FEATURE_BILLING=on all mean "let more
    people in". Each is tested against private mode individually, because the failure that
    matters is one of them being forgotten, not all of them.
    """
    c = Config(private_mode=True, open_access=True, feature_billing="on",
               beta_mode=True, beta_all_premium=True, stripe_secret_key="sk_test_x")
    assert c.public_access is False, "open_access must not survive private mode"
    assert c.signup_enabled is False, "FEATURE_BILLING=on must not re-open signup"
    assert c.billing_enabled is False, "a configured Stripe key must not re-enable checkout"
    assert c.beta_banner_enabled is False, "the beta strip addresses users; there are none"


def test_turning_it_off_restores_the_public_product():
    """The reversal path, asserted rather than promised."""
    c = Config(private_mode=False, open_access=False, feature_billing="",
               stripe_secret_key="sk_test_x")
    assert c.public_access is False      # open_access was off in this config
    assert c.signup_enabled is True
    assert c.billing_enabled is True
    assert Config(private_mode=False, open_access=True).public_access is True


# ============================== the policy function ========================================
def test_owner_is_a_real_account_not_a_demo_session():
    """The recruiter/demo preview must never count as the owner — it is precisely the
    'someone else reads the numbers' case private mode exists to close."""
    assert private.is_owner({"email": OWNER}, CONFIG) is True
    assert private.is_owner({"email": OWNER.upper()}, CONFIG) is True, "case must not matter"
    assert private.is_owner({"email": f"  {OWNER}  "}, CONFIG) is True, "nor whitespace"
    assert private.is_owner(None, CONFIG) is False
    assert private.is_owner({"email": "someone@else.com"}, CONFIG) is False
    assert private.is_owner({"email": OWNER, "is_demo": True}, CONFIG) is False, \
        "a demo session with the owner address is still a demo session"


def test_the_allowlist_is_exactly_what_it_claims():
    """Pinned deliberately: this list IS the security boundary, so it should be impossible to
    widen by accident. Adding a path here should require editing this test and saying why."""
    assert private.always_open("/api/health") is True          # platform health probe
    assert private.always_open("/login") is True               # the owner must get in
    assert private.always_open("/forgot") is True
    assert private.always_open("/reset/sometoken") is True
    assert private.always_open("/static/style.css") is True
    assert private.always_open("/admin/run-scan") is True      # crons: token-checked inside
    assert private.always_open("/api/option-alerts/open") is True
    assert private.always_open("/alerts/unsubscribe/tok") is True
    # A crawler never logs in, and the file's whole job is to tell it to go away.
    assert private.always_open("/robots.txt") is True
    for closed in ("/", "/app", "/api/hotstocks", "/api/track", "/pricing", "/account",
                   "/methodology", "/api/valquo-index", "/demo", "/register",
                   "/billing/checkout", "/api/edge/learning", "/terms", "/privacy"):
        assert private.always_open(closed) is False, f"{closed} must NOT be always-open"
    # The portfolio page is open, but through its OWN flag-gated door — never this one.
    # If it ever appears here it would survive PORTFOLIO_PAGE=false, which is the one way
    # that switch could stop meaning anything.
    assert private.always_open(CONFIG.resolved_portfolio_path) is False


def test_check_is_a_no_op_when_the_flag_is_off():
    off = Config(private_mode=False)
    assert private.check("/api/hotstocks", None, off) is None
    assert private.check("/app", None, off) is None


def test_api_refusal_carries_no_data_and_names_itself():
    d = private.check("/api/hotstocks", None, CONFIG)
    assert d["kind"] == "json" and d["status"] == 401
    assert d["payload"]["private_mode"] is True
    # The refusal must not become a place where the answer leaks out in a hint.
    body = json.dumps(d["payload"]).lower()
    for leak in ("rows", "score", "ticker", "series", "alpha"):
        assert leak not in body, f"the refusal payload mentions {leak}"


def test_the_refusal_does_not_distinguish_signed_in_from_anonymous():
    """A stranger learning 'that account exists but is not the owner' is information they have
    no business having, and it is a free account-enumeration oracle."""
    anon = private.check("/app", None, CONFIG)
    other = private.check("/app", {"email": "someone@else.com"}, CONFIG)
    assert anon == other


# ============================== end to end through the app =================================
def test_anonymous_gets_the_holding_page_not_the_marketing_landing():
    with APP.test_client() as c:
        r = c.get("/")
        assert r.status_code == 401
        body = r.get_data(as_text=True)
        assert "private research tool" in body.lower()
        # None of the landing page's proof surfaces may appear.
        for marketing in ("Create your free account", "hotTable", "livebar",
                          "og:image", "Start free"):
            assert marketing not in body, f"holding page leaked {marketing!r}"
        assert "noindex" in body, "a private instance must not invite indexing"


def test_every_api_route_on_the_app_refuses_an_anonymous_caller():
    """Swept from the app's own URL map rather than a hand-written list, so a route added
    later is covered the day it is added — the failure mode this guards is 'someone ships a
    new /api/ endpoint and nobody remembers the lockdown'."""
    paths = set()
    for rule in APP.url_map.iter_rules():
        p = str(rule)
        if p.startswith("/api/") and "<" not in p and not private.always_open(p):
            paths.add(p)
    assert len(paths) >= 15, f"expected to sweep the real API surface, found {len(paths)}"
    with APP.test_client() as c:
        for p in sorted(paths):
            r = c.open(p, method="GET" if "GET" in
                       next(x.methods for x in APP.url_map.iter_rules() if str(x) == p)
                       else "POST")
            assert r.status_code == 401, f"{p} returned {r.status_code} to an anonymous caller"
            assert b"private_mode" in r.data, f"{p} refused for the wrong reason"


def test_the_cron_routes_still_reach_their_token_check():
    """The whole point of the tool keeps running. A WRONG token is used on purpose: a correct
    one would actually run a market scan / broker cycle / Discord post. The discriminator is
    WHICH layer refused — private mode says private_mode, _admin_ok says unauthorized."""
    with APP.test_client() as c:
        for p in ("/admin/run-scan", "/admin/run-intraday", "/admin/run-paper-track",
                  "/admin/post-recap", "/admin/ingest-snapshot", "/admin/export-track"):
            r = c.post(p, headers={"X-Admin-Token": "wrong"}, json={})
            assert r.status_code == 401, f"{p} -> {r.status_code}"
            assert b"private_mode" not in r.data, \
                f"{p} was blocked by private mode; the cron behind it is now dead"
            assert b"unauthorized" in r.data, f"{p} did not reach the admin token check"


def test_the_recruiter_demo_link_is_refused():
    """Handled conservatively per the brief: gated with everything else, not left live."""
    with APP.test_client() as c:
        for p in ("/demo", "/demo/anything", "/demo?key=anything"):
            r = c.get(p)
            assert r.status_code in (401, 302), f"{p} -> {r.status_code}"
            with c.session_transaction() as s:
                assert not s.get("demo"), "a demo session was granted under private mode"


def test_no_payment_can_be_initiated():
    orig = _as_owner(APP.test_client())          # even the owner cannot start a checkout
    try:
        with APP.test_client() as c:
            t = _csrf(c)
            for p in ("/billing/checkout", "/billing/portal"):
                r = c.post(p, data={"plan": "pro", "_csrf": t})
                assert r.status_code == 403, f"{p} -> {r.status_code}"
                assert b"not for sale" in r.data or b"no subscription" in r.data
    finally:
        _restore(orig)


def test_the_owner_still_gets_the_whole_tool():
    """The lockdown must not lock Don out — the failure that would make all of this useless."""
    orig = _as_owner(APP.test_client())
    try:
        with APP.test_client() as c:
            for p in ("/app", "/api/hotstocks", "/api/track", "/methodology"):
                r = c.get(p)
                assert r.status_code == 200, f"owner blocked from {p} ({r.status_code})"
            assert c.get("/").status_code == 302, "the owner should land in the app"
    finally:
        _restore(orig)


def test_gating_gives_the_owner_premium_and_everyone_else_nothing():
    from valuation.saas import gating
    assert gating._active({"email": OWNER}) == "premium"
    assert gating._active({"email": "x@y.com"}) == "anon"
    assert gating._active({"email": "x@y.com", "is_demo": True}) == "anon", \
        "the demo grant must not survive private mode"
    assert gating._active(None) == "anon"


# ============================== the portfolio page =========================================
# The ONE deliberate hole in the lockdown (PROMPT_recruiter_page.md). Everything below exists
# to make that hole exactly one page wide, and to make "no vendor data on it" a property of
# the code rather than a promise in a comment.

PORTFOLIO = CONFIG.resolved_portfolio_path


def test_the_two_flags_are_independent_in_both_directions():
    """The point of a second flag. The page may be open on a locked instance, and closing it
    must not re-open — or further lock — anything else."""
    on = Config(private_mode=True, portfolio_page=True)
    off = Config(private_mode=True, portfolio_page=False)
    assert on.portfolio_page_enabled is True and off.portfolio_page_enabled is False
    # Neither setting touches the lockdown itself.
    assert on.public_access is False and off.public_access is False
    assert on.signup_enabled is False and off.signup_enabled is False
    # And private mode does not silently switch the page off either.
    assert Config(private_mode=False, portfolio_page=True).portfolio_page_enabled is True


def test_the_path_is_validated_because_a_typo_is_the_only_way_this_widens():
    """`resolved_portfolio_path` is the whole blast radius of PORTFOLIO_PATH. A value of "/"
    would mount a world-readable page on the app's root; a reserved prefix would shadow a real
    route (Flask keeps the first rule registered, so it would fail silently)."""
    assert Config(portfolio_path="/portfolio").resolved_portfolio_path == "/portfolio"
    assert Config(portfolio_path="work").resolved_portfolio_path == "/work", "leading slash"
    assert Config(portfolio_path="/work/").resolved_portfolio_path == "/work", "trailing slash"
    for bad in ("/", "", "  ", "/api", "/api/hotstocks", "/app", "/admin/run-scan",
                "/static/x", "/login", "/billing/checkout", "/robots.txt", "/<path>"):
        assert Config(portfolio_path=bad).resolved_portfolio_path == "/work", \
            f"PORTFOLIO_PATH={bad!r} was accepted"


def test_the_policy_grants_exactly_one_path_and_only_while_the_flag_is_on():
    on = Config(private_mode=True, portfolio_page=True, portfolio_path="/work")
    off = Config(private_mode=True, portfolio_page=False, portfolio_path="/work")
    assert private.check("/work", None, on) is None, "the page must be readable"
    assert private.check("/work", None, off) is not None, "the flag must actually gate it"
    # Exact match, never a prefix: a prefix grant would open every route beneath it.
    for near in ("/work/secret", "/work2", "/works", "/work/api/hotstocks"):
        assert private.check(near, None, on) is not None, f"{near} was opened by the page"


def test_an_anonymous_visitor_can_read_the_page_and_nothing_else():
    """The verification the brief asks for, as a test: the page renders logged out while the
    product stays shut. Both halves in one test on purpose — they are one claim."""
    with APP.test_client() as c:
        r = c.get(PORTFOLIO)
        assert r.status_code == 200, f"{PORTFOLIO} -> {r.status_code}"
        for still_shut in ("/", "/app", "/methodology", "/account", "/api/hotstocks",
                           "/api/track", "/api/valquo-index"):
            assert c.get(still_shut).status_code in (401, 302), \
                f"{still_shut} opened up when the portfolio page did"


def test_the_page_is_static_so_no_vendor_data_can_reach_it():
    """The licence-critical property, pinned two ways.

    BYTE-IDENTICAL across requests => it read no store and no clock. NO "/api/" anywhere =>
    the browser makes no follow-up call, so nothing can arrive after render either. Together
    these make "no ThetaData or Sharadar value appears here" checkable by machine, which is
    the only way it stays true after the next edit.
    """
    with APP.test_client() as c:
        a = c.get(PORTFOLIO).get_data(as_text=True)
        b = c.get(PORTFOLIO).get_data(as_text=True)
    assert a == b, "the page changed between requests, so something live is feeding it"
    low = a.lower()
    for live in ("/api/", "fetch(", "xmlhttprequest", "<script", "sharadar", "thetadata",
                 "tradier"):
        assert live not in low, f"the portfolio page references {live!r}"


def test_the_page_shows_no_picks_and_labels_what_it_does_show():
    """Content rules from the brief, as assertions. A future edit that adds a holdings table
    or drops the paper-account label should fail here, not in a compliance conversation."""
    with APP.test_client() as c:
        body = c.get(PORTFOLIO).get_data(as_text=True)
    low = body.lower()
    for required in ("not investment advice", "paper account", "no real money",
                     "historical simulation", "hypothetical"):
        assert required in low, f"the page no longer says {required!r}"
    for forbidden in ("buy now", "sign up", "subscribe", "price target", "current holdings",
                      "today's picks"):
        assert forbidden not in low, f"the page reads as a product: {forbidden!r}"


def test_the_page_refuses_indexing_three_ways():
    with APP.test_client() as c:
        r = c.get(PORTFOLIO)
        assert "noindex" in r.get_data(as_text=True), "missing the <meta> robots tag"
        assert "noindex" in (r.headers.get("X-Robots-Tag") or ""), "missing the header"
        rob = c.get("/robots.txt")
        assert rob.status_code == 200, "a crawler cannot log in to read robots.txt"
        txt = rob.get_data(as_text=True)
        assert "Disallow: /" in txt
        # Naming the path in a world-readable file would publish the URL it is hiding.
        assert PORTFOLIO.strip("/") not in txt, "robots.txt discloses the portfolio path"


def test_turning_the_flag_off_closes_the_page_under_both_postures():
    """PORTFOLIO_PAGE=false must actually shut it, and the refusal differs by design.

    Under private mode the page falls back into the lockdown and returns the same 401 holding
    page as every other path — it tells a visitor nothing about whether that URL means
    anything. On a PUBLIC instance there is no lockdown to fall back on, so the route itself
    404s; a redirect there would confirm the path exists. Both branches are asserted because
    the second one is the one nobody would notice was missing.

    Patched on CONFIG itself: that is the object the route and the guard both closed over.
    """
    CONFIG.portfolio_page = False
    try:
        with APP.test_client() as c:
            r = c.get(PORTFOLIO)
            assert r.status_code == 401, f"private mode should absorb it, got {r.status_code}"
            assert b"private research tool" in r.data, "it must be the ordinary refusal"
        CONFIG.private_mode = False
        with APP.test_client() as c:
            assert c.get(PORTFOLIO).status_code == 404, "a public instance must 404 it"
    finally:
        CONFIG.private_mode = True
        CONFIG.portfolio_page = True
    with APP.test_client() as c:
        assert c.get(PORTFOLIO).status_code == 200, "the flags did not restore"


# ============================== the track backup ===========================================
def _seeded_store():
    """A screener store with a small, realistic forward track in it."""
    from valuation.screener.store import Store
    from valuation.edge import paper_track as PT
    d = tempfile.mkdtemp()
    st = Store(os.path.join(d, "screener.db"))
    PT.ensure_schema(st)
    with st._conn() as c:
        for i, day in enumerate(("2026-06-01", "2026-06-02", "2026-06-03")):
            c.execute("INSERT INTO paper_index_track (as_of, index_ret, bench_ret, "
                      "active_ret, n_positions, n_priced, inception, detail) "
                      "VALUES (?,?,?,?,?,?,?,?)",
                      (day, 0.01 * (i + 1), 0.005 * (i + 1), 0.005 * (i + 1), 10, 10,
                       "2026-06-01", "{}"))
        c.execute("INSERT INTO paper_index_holdings (ticker, weight, entry_price, "
                  "bench_entry_price, entry_date, shares, order_id, note) "
                  "VALUES ('AAPL', 0.2, 190.0, 500.0, '2026-06-01', 3, 'ord-1', '')")
        c.execute("INSERT INTO option_alerts (id, alert_ts, ticker, opt_right, strike, "
                  "expiry, occ_symbol, entry_premium, exit_ts, exit_premium, exit_reason, "
                  "pnl_pct, pnl_dollars, status) VALUES "
                  "(7,'2026-06-01T14:30','AAPL','call',200,'2026-07-18','AAPL260718C00200000',"
                  "2.50,'2026-06-20T15:00',4.10,'target',0.64,160.0,'closed')")
        c.execute("INSERT INTO paper_option_orders (alert_id, ticker, occ_symbol, expiry, "
                  "contracts, state, entry_premium, entry_ts, exit_premium, exit_ts, "
                  "exit_reason, created_at) VALUES "
                  "(7,'AAPL','AAPL260718C00200000','2026-07-18',1,'closed',2.50,"
                  "'2026-06-01T14:35',4.10,'2026-06-20T15:00','target','2026-06-01T14:30')")
    return st, d


def test_the_export_actually_contains_the_irreplaceable_record():
    from valuation.edge.track_export import payload
    st, _ = _seeded_store()
    p = payload(st, generated_at="2026-06-04T00:00:00")
    assert p["counts"]["index_days"] == 3
    assert p["counts"]["option_alerts_closed"] == 1
    assert p["counts"]["index_holdings"] == 1
    # The entry AND the exit, or it is not a record of a completed trade.
    a = p["option_alerts"][0]
    assert a["entry_premium"] == 2.50 and a["exit_premium"] == 4.10
    assert a["exit_reason"] == "target"
    assert p["index_series"][0]["as_of"] == "2026-06-01"


def test_the_export_is_byte_stable_across_runs():
    """A weekly commit must diff only when the record changed. If SQLite float repr or dict
    ordering leaked through, every week would produce a diff and Don would stop reading them."""
    from valuation.edge.track_export import payload, write
    st, _ = _seeded_store()
    outs = []
    for _ in range(2):
        d = tempfile.mkdtemp()
        write(payload(st, generated_at="2026-06-04T00:00:00"), d)
        outs.append({f: open(os.path.join(d, f), encoding="utf-8").read()
                     for f in sorted(os.listdir(d))})
    assert outs[0] == outs[1], "the export is not deterministic"


def test_the_csv_is_readable_and_joins_the_alert_to_its_fill():
    import csv as _csv
    from valuation.edge.track_export import payload, write
    st, _ = _seeded_store()
    d = tempfile.mkdtemp()
    write(payload(st, generated_at="2026-06-04T00:00:00"), d)

    idx = list(_csv.DictReader(open(os.path.join(d, "paper_track_index.csv"),
                                    encoding="utf-8")))
    assert len(idx) == 3 and idx[0]["as_of"] == "2026-06-01"
    assert idx[-1]["active_ret"], "the excess-vs-SPY column must be populated"

    tr = list(_csv.DictReader(open(os.path.join(d, "paper_track_trades.csv"),
                                   encoding="utf-8")))
    assert len(tr) == 1
    row = tr[0]
    # The claim (alert) and the fill (paper order) are different halves of one trade; the
    # backup is worthless if it keeps only one.
    assert row["alert_ts"] == "2026-06-01T14:30" and row["entry_ts"] == "2026-06-01T14:35"
    assert row["pnl_dollars"] == "160.0" and row["exit_reason"] == "target"
    assert row["ticker"] == "AAPL" and row["contracts"] == "1"
    assert os.path.exists(os.path.join(d, "README.md")), "a bare CSV in a repo is a mystery"


def test_the_export_carries_no_secrets():
    from valuation.edge.track_export import payload, write
    st, _ = _seeded_store()
    d = tempfile.mkdtemp()
    write(payload(st, generated_at="2026-06-04T00:00:00"), d)
    # DATA files only. README.md is prose that says "No secrets", and scanning it for the
    # word "secret" fails on its own reassurance — a false positive that would have to be
    # silenced later, which is how a real one gets silenced with it.
    data_files = [f for f in os.listdir(d) if f.endswith((".json", ".csv"))]
    assert data_files, "nothing was written"
    blob = "".join(open(os.path.join(d, f), encoding="utf-8").read()
                   for f in data_files).lower()
    for secret in ("api_key", "apikey", "token", "password", "secret", "authorization",
                   "sk_live", "sk_test", "bearer", "x-admin"):
        assert secret not in blob, f"the committed backup contains {secret!r}"


def test_an_empty_database_exports_safely_and_says_so():
    """The dangerous case: a service comes up on a fresh disk and the backup faithfully
    records nothing. It must still be distinguishable from a real empty track."""
    from valuation.screener.store import Store
    from valuation.edge.track_export import payload, write
    d = tempfile.mkdtemp()
    st = Store(os.path.join(d, "empty.db"))
    p = payload(st, generated_at="2026-06-04T00:00:00")
    assert p["counts"]["index_days"] == 0
    assert p["tables_present"]["paper_index_track"] is False, \
        "'table missing' and 'table empty' must stay distinguishable"
    out = tempfile.mkdtemp()
    write(p, out)          # must not raise
    assert os.path.exists(os.path.join(out, "paper_track_history.json"))


def test_the_backup_workflow_guards_against_clobbering_a_good_backup():
    """The export runs unattended and commits. The one unrecoverable outcome is overwriting
    months of record with an empty file, so the workflow must refuse to shrink."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    wf = open(os.path.join(root, ".github", "workflows", "track-backup.yml"),
              encoding="utf-8").read()
    assert "Refuse to overwrite a real backup" in wf
    assert "-lt" in wf, "the shrink check must actually compare row counts"
    assert "curl -fsS" in wf, "an HTTP error must fail the step, not get committed"
    assert "data_export/" in wf


def test_data_export_is_not_gitignored():
    """The whole design depends on these files being committable. `data/` IS ignored and the
    names are one underscore apart, so this is a cheap guard against a future .gitignore edit
    silently turning the backup into a no-op."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ig = open(os.path.join(root, ".gitignore"), encoding="utf-8").read()
    for line in ig.splitlines():
        s = line.strip()
        if s in ("data_export/", "data_export", "data*", "data*/"):
            raise AssertionError(f".gitignore line {s!r} would exclude the track backup")


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
    print(f"\n{passed}/{len(tests)} private-mode tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
