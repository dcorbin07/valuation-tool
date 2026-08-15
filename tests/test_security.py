"""
Security regression tests — the findings from SECURITY_AUDIT.md, pinned.

    python tests/test_security.py

Every test here corresponds to a numbered finding. They are deliberately written to fail
if the CLASS of bug reopens, not just the one instance that was found: the FMP key leak was
fixed once in `screener/providers.py` and immediately re-appeared in 23 other handlers
because nothing stopped a new `jsonify({"error": str(e)})` from being written.
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.safe_error import redact, safe_error, strip_paths

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Shape-only, not a live credential. 32 hex chars is the FMP key format.
FAKE_KEY = "DkkPylwVxZZ91CAiCOhXshz7fQbETlUS"

# Built ONCE, at import, before any test issues a request. The SaaS layer wraps the same
# Flask object as the tool app, and Flask refuses to register routes after the first
# request is handled — so a test that hits the bare tool app first would break every
# later create_saas_app() call.
from valuation.config import CONFIG                      # noqa: E402
from valuation.saas.app_saas import create_saas_app      # noqa: E402

# private_mode ships default TRUE and refuses every non-owner before any route runs, which
# would make most of the findings below untestable — a lockdown trivially "passes" an
# account-enumeration or signup test by refusing the request. These tests exist to prove the
# PUBLIC product is safe, because that is the product `PRIVATE_MODE=false` restores, so the
# suite runs against it. The lockdown has its own suite: tests/test_private.py.
CONFIG.private_mode = False

APP = create_saas_app(CONFIG)
APP.config.update(TESTING=True)


def _read(rel):
    with io.open(os.path.join(_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------------- #
#  H2 — no handler may return raw exception text to an anonymous caller
# --------------------------------------------------------------------------- #
def test_redact_scrubs_every_shape_a_key_arrives_in():
    """Both paid providers put the credential in the query string, so `requests`'
    HTTPError text carries it verbatim. Bearer headers and bare assignments too."""
    cases = [
        f"402 Client Error for url: https://x/company-screener?exchange=NYSE&apikey={FAKE_KEY}",
        f"failed https://api.tradier.com/v1/q?token={FAKE_KEY}&y=1",
        f"GET https://data.nasdaq.com/api/v3/SF1.json?ticker=AAPL&api_key={FAKE_KEY}",
        f"Authorization: Bearer {FAKE_KEY}",
        f'{{"api_key": "{FAKE_KEY}"}}',
        f"ConnectionError(api_key={FAKE_KEY})",
    ]
    for msg in cases:
        out = redact(msg)
        assert FAKE_KEY not in out, f"key survived redaction: {out}"
        assert "<redacted>" in out, out


def test_safe_error_redacts_before_it_truncates():
    """Order matters. Truncating first can cut a URL mid-key and strand a usable prefix
    of the credential in the output — the redaction has to happen on the full string."""
    long_url = ("500 Server Error for url: https://financialmodelingprep.com/api/v3/"
                + "x" * 300 + f"?apikey={FAKE_KEY}")
    out = safe_error(long_url, limit=200)
    assert FAKE_KEY not in out
    assert FAKE_KEY[:8] not in out, "a truncated prefix of the key leaked"
    assert len(out) <= 210


def test_safe_error_strips_absolute_server_paths():
    """L4 — a FileNotFoundError stringifies to the deployment's real filesystem layout."""
    for msg, keep in (("[Errno 2] No such file: '/app/data/backtest/SHARADAR_SF1.csv'",
                       "SHARADAR_SF1.csv"),
                      (r"Cannot open C:\Users\donni\Downloads\valuation-tool\data\app.db",
                       "app.db")):
        out = strip_paths(msg)
        assert keep in out, out          # which file is missing stays useful
        assert "/app/data" not in out and "Users" not in out, out


def test_safe_error_leaves_ordinary_urls_readable():
    """Path stripping must not mangle the vendor URL in an error — that is the part that
    tells you which API failed. Only filesystem-looking absolute paths get collapsed."""
    out = safe_error("502 Bad Gateway for url: https://financialmodelingprep.com/api/v3/quote/NKE")
    assert "financialmodelingprep.com" in out and "/api/v3/quote/NKE" in out, out


def test_no_handler_returns_raw_exception_text():
    """The structural guard. This is what actually keeps H2 closed: it fails on the next
    `jsonify({"error": str(e)})` anyone writes, not just on the 23 that existed."""
    bad = []
    for rel in ("valuation/web/app.py", "valuation/saas/app_saas.py",
                "valuation/saas/billing.py", "valuation/saas/auth.py"):
        for i, line in enumerate(_read(rel).splitlines(), 1):
            if "safe_error" in line or line.lstrip().startswith("#"):
                continue
            # An exception interpolated into something being RETURNED to a caller.
            if re.search(r"return .*(?:jsonify|f\").*(?:str\(e\)|\{e\})", line):
                bad.append(f"{rel}:{i}  {line.strip()}")
    assert not bad, ("raw exception text returned to callers — wrap in safe_error():\n  "
                     + "\n  ".join(bad))


def test_api_value_error_response_carries_no_key():
    """End to end through the real Flask app, on the most exposed handler there is:
    /api/value is unauthenticated under OPEN_ACCESS and sits directly on the fetcher stack."""
    from valuation.web import app as web_app

    boom = Exception("500 Server Error for url: "
                     f"https://financialmodelingprep.com/api/v3/profile/NKE?apikey={FAKE_KEY}")

    orig, orig_stderr = web_app.value_ticker, sys.stderr
    try:
        def _raise(*a, **k):
            raise boom
        web_app.value_ticker = _raise
        c = APP.test_client()
        sys.stderr = io.StringIO()          # the handler's traceback.print_exc() is expected
        r = c.post("/api/value", json={"ticker": "NKE"})
        logged = sys.stderr.getvalue()
        sys.stderr = orig_stderr
        body = r.data.decode("utf-8", "ignore")
        assert r.status_code == 500
        assert FAKE_KEY not in body, f"live key published to an anonymous caller: {body}"
        assert "<redacted>" in body, body
        # ...while the operator still gets the full stack trace server-side (L3) — with
        # the credential scrubbed there too, because Render logs are not a safe home
        # for a live key either.
        assert "financialmodelingprep" in logged, "the real error must still reach the log"
        assert "Traceback" in logged, "the stack trace must survive redaction"
        assert FAKE_KEY not in logged, "the key reached the server log"
    finally:
        web_app.value_ticker, sys.stderr = orig, orig_stderr


# --------------------------------------------------------------------------- #
#  H1 — the endpoints that spend the owner's budget are rate limited
# --------------------------------------------------------------------------- #
def test_only_money_and_cpu_endpoints_are_rate_limited():
    """Open access is a product decision, not a bug: reading stays free and unlimited.
    What must not be free is spending the owner's Anthropic and FMP budget in a loop."""
    from valuation.saas import ratelimit

    # The four the audit named, plus the CPU-heavy ones.
    for path in ("/api/signals/run", "/api/scan/run", "/api/backtest/run", "/api/portfolio"):
        assert ratelimit.bucket_for(path, {}) == path, f"{path} must be limited"
    # Reads are untouched. These serve the cached snapshot and make no upstream call.
    for path in ("/api/hotstocks", "/api/health", "/api/signals", "/api/valquo-index"):
        assert ratelimit.bucket_for(path, {}) is None, f"{path} must NOT be limited"

    # CORRECTED 2026-08-14 (audit MA7). These two lines used to assert
    #     bucket_for("/api/value", {"ticker": "NKE"}) is None
    # under the comment "/api/value is the core action and stays free". That was the DEFECT,
    # pinned: the plain valuation runs the full adaptive DCF on a caller-supplied symbol, so
    # it spends the same FMP quota this module caps /api/scan/run at 3/hour to protect. The
    # cache stops repeats; nothing stopped enumeration over ~7,100 names.
    #
    # The AI cap is UNCHANGED and still applies — it is now charged ALONGSIDE the vendor
    # budget rather than instead of it, which is what the old single-bucket form could not do.
    assert ratelimit.bucket_for("/api/value", {"ticker": "NKE"}) == ratelimit.VENDOR_BUCKET
    named = dict(ratelimit.buckets_for("/api/value", {"ticker": "NKE", "run_ai": True}))
    assert named.get("ai:value") == 1, "the AI cap stopped applying to an AI request"
    assert named.get(ratelimit.VENDOR_BUCKET) == 1, \
        "an AI request escapes the vendor budget it also spends"


def test_rate_limit_counts_blocks_and_drains():
    from valuation.saas import ratelimit
    ratelimit.reset()
    ratelimit.LIMITS["__test__"] = (3, 60)
    try:
        t0 = 1_000_000.0
        assert [ratelimit.check("1.2.3.4", "__test__", t0 + i) for i in range(3)] == [None] * 3
        blocked = ratelimit.check("1.2.3.4", "__test__", t0 + 3)
        assert blocked and 1 <= blocked <= 60, blocked
        # A different caller is unaffected.
        assert ratelimit.check("5.6.7.8", "__test__", t0 + 3) is None
        # Hammering while blocked must not extend the penalty...
        for i in range(20):
            ratelimit.check("1.2.3.4", "__test__", t0 + 4 + i)
        # ...so the window still drains exactly on schedule.
        assert ratelimit.check("1.2.3.4", "__test__", t0 + 61) is None
    finally:
        ratelimit.LIMITS.pop("__test__", None)
        ratelimit.reset()


def test_client_ip_uses_the_rightmost_forwarded_hop():
    """The leftmost X-Forwarded-For entry is whatever the client typed, so trusting it
    makes the limiter bypassable with a header. With one trusted proxy the rightmost hop
    is the address the proxy actually observed."""
    from valuation.saas import ratelimit

    class _Req:
        def __init__(self, xff):
            self.headers = {"X-Forwarded-For": xff} if xff else {}
            self.remote_addr = "10.0.0.1"

    assert ratelimit.client_ip(_Req("9.9.9.9, 203.0.113.7")) == "203.0.113.7"
    assert ratelimit.client_ip(_Req("")) == "10.0.0.1"


def test_rate_limit_is_enforced_by_the_app_and_bypassed_by_the_admin_token():
    """Wiring test. Uses a bucket forced to 0 so the limiter answers BEFORE the handler —
    which is the point of putting the check first: a flood must cost a dict lookup, not a
    whole-market scan."""
    from valuation.saas import ratelimit

    c = APP.test_client()
    ratelimit.reset()
    orig_limit, orig_token = ratelimit.LIMITS["/api/export/pdf"], CONFIG.admin_token
    try:
        ratelimit.LIMITS["/api/export/pdf"] = (0, 900)
        r = c.get("/api/export/pdf?ticker=NKE")
        assert r.status_code == 429, r.status_code
        assert r.headers.get("Retry-After") == "900", r.headers
        assert r.get_json()["retry_after_seconds"] == 900

        # The cron jobs hit these on a schedule and are already authenticated.
        CONFIG.admin_token = "tok-rl-test"
        r2 = c.get("/api/export/pdf?ticker=NKE", headers={"X-Admin-Token": "tok-rl-test"})
        assert r2.status_code != 429, "the admin token must bypass the limiter"
    finally:
        ratelimit.LIMITS["/api/export/pdf"] = orig_limit
        CONFIG.admin_token = orig_token
        ratelimit.reset()


# --------------------------------------------------------------------------- #
#  M2 — CSRF on the cookie-authenticated form POSTs, and cookie hardening
# --------------------------------------------------------------------------- #
def test_form_posts_require_a_csrf_token():
    from valuation.saas import csrf

    c = APP.test_client()
    # No token at all -> rejected before the handler runs.
    r = c.post("/forgot", data={"email": "someone@example.com"})
    assert r.status_code == 400, r.status_code
    # A wrong token -> also rejected.
    with c.session_transaction() as s:
        s["_csrf_token"] = "the-real-one"
    assert c.post("/forgot", data={"email": "x@y.com", "_csrf": "guessed"}).status_code == 400
    # The matching token -> allowed through.
    assert c.post("/forgot", data={"email": "x@y.com",
                                   "_csrf": "the-real-one"}).status_code == 200

    # Stripe's webhook must stay exempt: it is posted from outside any browser session
    # and is already authenticated by its signature.
    assert not csrf.needs_protection("/billing/webhook", "POST")
    assert not csrf.needs_protection("/admin/ingest-snapshot", "POST")
    # ...and every form the audit named must be covered.
    for p in ("/login", "/register", "/forgot", "/account/alerts",
              "/billing/checkout", "/billing/portal", "/reset/sometoken"):
        assert csrf.needs_protection(p, "POST"), p
        assert not csrf.needs_protection(p, "GET"), p


def test_every_form_template_carries_the_csrf_field():
    """Structural guard: a new form without the hidden field would be rejected at runtime
    with a confusing 400, so catch it here instead."""
    import glob
    missing = []
    for path in glob.glob(os.path.join(_ROOT, "valuation/web/templates/*.html")):
        with io.open(path, encoding="utf-8") as fh:
            html = fh.read()
        for form in re.findall(r'<form\s[^>]*method="POST"[^>]*>.*?</form>', html, re.S | re.I):
            if 'name="_csrf"' not in form:
                missing.append(os.path.basename(path))
    assert not missing, f"form POST without a CSRF field in: {sorted(set(missing))}"


def test_session_cookie_is_hardened():
    assert APP.config["SESSION_COOKIE_HTTPONLY"] is True
    assert APP.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert APP.config["PERMANENT_SESSION_LIFETIME"].days == 30


# --------------------------------------------------------------------------- #
#  M3 / M5 / L1 / L2 / L5 / L6
# --------------------------------------------------------------------------- #
def test_refuses_to_boot_on_the_committed_secret_key_in_production():
    """M3 — SECRET_KEY signs session cookies AND reset tokens AND unsubscribe tokens.
    Its default is a literal in this repo, so a fail-open default means anyone who can
    read the repo can forge a session for any uid."""
    from valuation.saas import app_saas

    class _Cfg:
        secret_key = "dev-insecure-change-me"
        dev_mode = False

    orig = os.environ.get("RENDER")
    try:
        os.environ["RENDER"] = "true"
        assert app_saas._looks_like_production(_Cfg()) is True
        _Cfg.dev_mode = True                     # the explicit local escape hatch
        assert app_saas._looks_like_production(_Cfg()) is False
    finally:
        if orig is None:
            os.environ.pop("RENDER", None)
        else:
            os.environ["RENDER"] = orig
    # A laptop with no platform env var is not production, whatever PUBLIC_BASE_URL says.
    _Cfg.dev_mode = False
    assert app_saas._looks_like_production(_Cfg()) is False


def test_admin_token_is_compared_in_constant_time():
    """M5 — `==` short-circuits on the first differing byte. Also re-asserts the
    fail-closed behaviour when ADMIN_TOKEN is unset, which is load-bearing."""
    src = _read("valuation/saas/app_saas.py")
    assert "hmac.compare_digest" in src
    assert 'request.headers.get("X-Admin-Token") != cfg.admin_token' not in src, \
        "an inline == admin comparison came back"

    c = APP.test_client()
    orig = CONFIG.admin_token
    try:
        CONFIG.admin_token = ""          # unset must fail CLOSED, not open
        assert c.post("/admin/run-scan").status_code == 401
        assert c.post("/admin/run-scan", headers={"X-Admin-Token": ""}).status_code == 401
        CONFIG.admin_token = "right-token"
        assert c.post("/admin/ingest-snapshot", json={"rows": []},
                      headers={"X-Admin-Token": "wrong-token"}).status_code == 401
    finally:
        CONFIG.admin_token = orig


def test_dead_public_paths_allowlist_is_gone():
    """L1 — it was never referenced, so it read like enforced access control and enforced
    nothing. A trap for the next reader."""
    from valuation.saas import app_saas
    assert not hasattr(app_saas, "PUBLIC_PATHS")


def test_security_headers_are_sent():
    """L2 — there was no after_request hook in the codebase at all."""
    r = APP.test_client().get("/api/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_dockerignore_excludes_the_whole_licensed_data_dir():
    """L5 — Dockerfile does `COPY . .`, and the old rules only excluded data/*.db, so
    data/raw/ and the licensed Sharadar CSVs got baked into a locally built image."""
    ignore = _read(".dockerignore").splitlines()
    assert "data/" in [ln.strip() for ln in ignore], ignore


def test_unsubscribe_tokens_expire_but_old_links_still_work():
    """L6 — these were minted with the untimed serializer, so every one ever emailed
    stayed valid forever. The legacy fallback keeps already-sent emails working."""
    from itsdangerous import URLSafeSerializer
    from valuation.saas import notify

    class _Cfg:
        secret_key = "unit-test-key"

    cfg = _Cfg()
    assert notify.unsub_user_id(cfg, notify.unsub_token(cfg, 42)) == 42
    legacy = URLSafeSerializer(cfg.secret_key, salt=notify._UNSUB_SALT).dumps(7)
    assert notify.unsub_user_id(cfg, legacy) == 7, "pre-fix email links must keep working"
    assert notify.unsub_user_id(cfg, "not-a-real-token") is None
    # Forged with the wrong key -> rejected by both loaders.
    class _Other:
        secret_key = "a-different-key"
    assert notify.unsub_user_id(cfg, notify.unsub_token(_Other(), 42)) is None


def test_llm_output_is_escaped_before_it_reaches_innerhtml():
    """M6 — the model writes from filings and news text, which outsiders influence. Every
    such field is concatenated into a string assigned to innerHTML."""
    js = _read("valuation/web/static/app.js")
    block = js[js.index("function aiBox("):js.index("function warnBox(")]
    # Only the lines that build the innerHTML string. `ai.source` is assigned via
    # textContent, which is already inert — and escaping it there would render literal
    # &amp; entities to the user.
    raw = []
    for line in block.splitlines():
        if "html +=" not in line and "<li>" not in line:
            continue
        raw += re.findall(r"\$\{(ai\.[A-Za-z_.]+(?:\s*\|\|\s*\"\")?)\}", line)
        raw += re.findall(r"\$\{(x)\}", line)          # the list() helper's item
    assert not raw, f"model output interpolated into innerHTML without esc(): {raw}"
    assert "esc(ai.business_summary)" in block and "esc(ai.overall_take)" in block
    assert "innerHTML" in block, "test is anchored on the wrong function"


# --------------------------------------------------------------------------- #
#  H3 / M4 — latent today, live the day OPEN_ACCESS goes false
# --------------------------------------------------------------------------- #
def test_signup_cannot_claim_an_owner_address():
    """H3 — owner privilege is granted by matching a typed string against OWNER_EMAILS,
    there is no email verification anywhere, and the owner address is a committed default.
    So the first stranger to register it would inherit /api/edge/*."""
    import uuid

    c = APP.test_client()
    orig_signup, orig_owners = CONFIG.feature_billing, CONFIG.owner_emails
    try:
        CONFIG.feature_billing = "on"           # force the signup surface open
        CONFIG.owner_emails = "boss@valquo.co"
        assert CONFIG.signup_enabled is True
        with c.session_transaction() as s:
            s["_csrf_token"] = "t"
        r = c.post("/register", data={"email": "BOSS@Valquo.co", "password": "password123",
                                      "agree": "on", "_csrf": "t"})
        assert r.status_code == 400, "an owner address must not be self-registerable"
        # Case and whitespace must not be a way around it.
        r2 = c.post("/register", data={"email": "  boss@valquo.co  ", "password": "password123",
                                       "agree": "on", "_csrf": "t"})
        assert r2.status_code == 400
        # A normal address still registers fine.
        ok = c.post("/register", data={"email": "ok_" + uuid.uuid4().hex[:8] + "@ex.com",
                                       "password": "password123", "agree": "on", "_csrf": "t"})
        assert ok.status_code in (301, 302), ok.status_code
    finally:
        CONFIG.feature_billing, CONFIG.owner_emails = orig_signup, orig_owners


def test_demo_token_has_no_guessable_default():
    """M4 — DEMO_ACCESS_TOKEN defaulted to the literal "preview", so /demo/preview handed
    out a permanent Premium session. Unset must disable /demo entirely."""
    from valuation.config import Config
    assert Config().demo_access_token == "" or os.environ.get("DEMO_ACCESS_TOKEN")

    c = APP.test_client()
    orig = CONFIG.demo_access_token
    try:
        CONFIG.demo_access_token = ""
        for guess in ("preview", "demo", "test"):
            r = c.get(f"/demo/{guess}")
            assert r.headers["Location"].endswith("/"), f"/demo/{guess} must not grant access"
            with c.session_transaction() as s:
                assert not s.get("demo"), f"/demo/{guess} opened a premium session"
    finally:
        CONFIG.demo_access_token = orig


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
    print(f"\n{passed}/{len(tests)} security tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
