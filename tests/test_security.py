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
        # ...while the operator still gets the full, unedited detail server-side.
        assert "financialmodelingprep" in logged, "the real error must still reach the log"
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
    # Reads are untouched.
    for path in ("/api/hotstocks", "/api/health", "/api/signals", "/api/valquo-index"):
        assert ratelimit.bucket_for(path, {}) is None, f"{path} must NOT be limited"
    # /api/value is the core action and stays free — unless it asks for the AI layer,
    # which is a paid API call per request.
    assert ratelimit.bucket_for("/api/value", {"ticker": "NKE"}) is None
    assert ratelimit.bucket_for("/api/value", {"ticker": "NKE", "run_ai": True}) == "ai:value"


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
