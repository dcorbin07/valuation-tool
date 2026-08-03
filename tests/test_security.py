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
        web_app.app.config.update(TESTING=True)
        c = web_app.app.test_client()
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
