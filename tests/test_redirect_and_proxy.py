"""MA51 + MA8 + MA53 — untrusted request inputs: where they go, and who they identify.

Three audit items, one suite, because they are one question asked three times: what does this
app do with a value the caller chose?

  * MA51 (MEDIUM) — `next` chose the page a freshly-logged-in user lands on. Open redirect.
  * MA8  (LOW)    — `X-Forwarded-For` chooses which bucket the rate limiter charges, and the
                    code could not tell whether it was reading a visitor or a proxy.
  * MA53 (LOW)    — malformed numeric params, and LA12's population mix. Both VERIFIED CLOSED
                    on arrival; the tests here exist so they cannot re-open silently.

The sweeps matter more than the unit tests. A guard inside one view cannot be asserted over a
codebase, so each item ships a test that fails when the NEXT such site is written.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import state_isolation  # noqa: F401  (must precede any `valuation` import)

import unittest

from valuation.saas import ratelimit
from valuation.saas.safe_redirect import safe_next_path
from valuation.web.query_params import clamp_int, clamp_float

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read().replace("\r\n", "\n")


def _redirect_offenders_in(source, rel):
    """Every `redirect(...)` in `source` whose first argument is neither a literal nor validated.

    An AST walk rather than a line grep, deliberately. A grep cannot tell a call from the same
    text quoted inside a docstring — and this module's own docstring quotes MA51's defective
    line verbatim, so a grep-based sweep would have to carry a file exemption to stay green.
    An exemption list is the thing that makes a sweep stop finding the next case.
    """
    import ast
    out = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", "")
        if name != "redirect" or not node.args:
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            continue                      # a server-written literal; no caller involved
        seg = ast.dump(arg)
        if "safe_next_path" in seg:
            continue
        if "request" not in seg and "next" not in seg.lower():
            continue                      # a server-computed value (e.g. a Stripe session url)
        out.append(f"{rel}:{getattr(node, 'lineno', '?')}")
    return out


def _redirect_offenders():
    offenders, scanned = [], 0
    for dirpath, _dirs, files in os.walk(os.path.join(ROOT, "valuation")):
        if "__pycache__" in dirpath:
            continue
        for fname in sorted(files):
            if not fname.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fname), ROOT)
            src = _src(rel)
            scanned += src.count("redirect(")
            offenders += _redirect_offenders_in(src, rel)
    return offenders, scanned


# ---------------------------------------------------------------------------------------
# MA51 — the open redirect
# ---------------------------------------------------------------------------------------
class TestSafeNextPath(unittest.TestCase):

    def test_the_audit_s_own_attack_string_is_refused(self):
        """`/login?next=https://evil.example` is the exact payload MA51 names."""
        self.assertEqual(safe_next_path("https://evil.example"), "/app")

    def test_a_protocol_relative_url_is_refused_though_it_starts_with_a_slash(self):
        """The bypass the naive rule misses.

        `//evil.example` satisfies `startswith("/")` and browsers resolve it to a DIFFERENT
        ORIGIN. A validator that implemented the audit's prescription literally would pass
        this through, which is why the audit itself calls out `not //`.
        """
        for payload in ("//evil.example", "///evil.example", "//evil.example/path?a=b"):
            self.assertEqual(safe_next_path(payload), "/app", payload)

    def test_a_backslash_authority_is_refused_even_though_urlsplit_calls_it_a_path(self):
        """`/\\evil.example` — the parser and the browser disagree, and the browser navigates.

        This is the one rejection that cannot be justified from the RFC: `urlsplit` reports an
        empty netloc, so the value looks same-origin to correct standards-based code. Browsers
        normalise the backslash into the authority position and go elsewhere.
        """
        from urllib.parse import urlsplit
        # The premise, asserted rather than assumed — if a future urllib normalises this, the
        # comment above becomes wrong and this test says so.
        self.assertEqual(urlsplit("/\\evil.example").netloc, "")
        for payload in ("/\\evil.example", "\\evil.example", "\\\\evil.example"):
            self.assertEqual(safe_next_path(payload), "/app", payload)

    def test_a_triple_slash_is_refused_though_urlsplit_reports_it_same_origin(self):
        """`///evil.example` parses to an EMPTY netloc and path `/evil.example`.

        So a validator that delegates the authority question to `urlsplit` accepts it. Found
        by this suite failing when an earlier draft of the validator did exactly that.
        """
        from urllib.parse import urlsplit
        self.assertEqual(urlsplit("///evil.example").netloc, "")
        self.assertTrue(urlsplit("///evil.example").path.startswith("/"))
        self.assertEqual(safe_next_path("///evil.example"), "/app")

    def test_schemes_that_are_not_http_are_refused(self):
        for payload in ("javascript:alert(1)", "data:text/html,<script>", "  https://x.example"):
            self.assertEqual(safe_next_path(payload), "/app", payload)

    def test_a_single_slash_scheme_is_refused_and_only_the_scheme_check_catches_it(self):
        """`https:/evil.example` — one slash, not two. Browsers resolve it off-origin anyway.

        This payload is the whole reason the scheme check exists, which mutation testing is
        what proved: with the other payloads alone, deleting `if parts.scheme` passed every
        test, because `https://evil.example` parses to an EMPTY path and is already caught by
        the relative-path branch. `https:/evil.example` parses to path `/evil.example`, which
        starts with a slash and sails through everything except the scheme check.
        """
        from urllib.parse import urlsplit
        self.assertTrue(urlsplit("https:/evil.example").path.startswith("/"))
        for payload in ("https:/evil.example", "http:/evil.example", "HTTPS:/evil.example"):
            self.assertEqual(safe_next_path(payload), "/app", payload)

    def test_control_characters_are_refused(self):
        """Response splitting. Werkzeug also refuses; this is depth, not the only guard."""
        for payload in ("/app\r\nSet-Cookie: a=b", "/app\n/x", "/app\x00"):
            self.assertEqual(safe_next_path(payload), "/app", payload)

    def test_a_bare_relative_path_is_refused_rather_than_prefixed(self):
        """`evil.example` must not become `/evil.example` — nor be resolved relative."""
        self.assertEqual(safe_next_path("evil.example"), "/app")
        self.assertEqual(safe_next_path("app"), "/app")

    def test_the_legitimate_producers_all_survive(self):
        """Every `next` this codebase actually writes must still work.

        Read from the SOURCE rather than listed by hand: if a route starts sending a new
        `next`, this test covers it automatically instead of going quietly out of date.
        """
        produced = set()
        for rel in ("valuation/saas/app_saas.py", "valuation/saas/billing.py"):
            produced |= set(re.findall(r'redirect\("(/login\?next=[^"]+)"\)', _src(rel)))
        self.assertGreaterEqual(len(produced), 3, "expected the known /login?next= producers")
        for url in produced:
            target = url.split("next=", 1)[1]
            self.assertEqual(safe_next_path(target), target,
                             f"{target} is produced by this codebase and must survive")

    def test_a_query_string_and_fragment_survive(self):
        """Pins the docstring's claim. Neither can change the ORIGIN, which is what is guarded."""
        for ok in ("/app", "/app?tab=holdings", "/app?a=1&b=2#top", "/account", "/"):
            self.assertEqual(safe_next_path(ok), ok)

    def test_empty_and_missing_degrade_to_the_default_not_an_error(self):
        for payload in (None, "", "   ", 0, [], {}):
            self.assertEqual(safe_next_path(payload), "/app", repr(payload))

    def test_the_default_is_honoured_so_the_helper_is_not_hardwired_to_one_route(self):
        self.assertEqual(safe_next_path("https://evil.example", default="/account"), "/account")

    def test_no_redirect_in_the_codebase_takes_a_request_value_unvalidated(self):
        """THE SWEEP. This is what makes the fix structural rather than local.

        Fails if any `redirect(...)` anywhere under `valuation/` is handed something derived
        from the request without passing through `safe_next_path`. The next route to honour a
        caller-chosen destination trips this on the way in.
        """
        offenders, scanned = _redirect_offenders()
        self.assertGreater(scanned, 15, "the AST walk found almost no redirect() calls — it is "
                                        "probably no longer matching, and would pass forever")
        self.assertEqual(offenders, [], "redirect() fed an unvalidated caller value:\n"
                                        + "\n".join(offenders))

    def test_the_sweep_is_not_vacuous(self):
        """A sweep that matches nothing passes forever. Prove it flags MA51's original line.

        Run against the real defect as it was written, through the SAME predicate the sweep
        uses — not a restatement of it, which could drift from the sweep and still pass.
        """
        bad = 'from flask import redirect, request\ndef v():\n' \
              '    return redirect(request.args.get("next") or "/app")\n'
        self.assertEqual(len(_redirect_offenders_in(bad, "<synthetic>")), 1)
        fixed = 'from flask import redirect, request\ndef v():\n' \
                '    return redirect(safe_next_path(request.args.get("next")))\n'
        self.assertEqual(_redirect_offenders_in(fixed, "<synthetic>"), [])

    def test_the_login_route_calls_the_validator(self):
        src = _src("valuation/saas/auth.py")
        self.assertIn("safe_next_path(request.args.get(\"next\")", src)
        self.assertNotIn('redirect(request.args.get("next")', src)

    def test_a_real_login_cannot_be_redirected_off_site(self):
        """END TO END, through a real login. The source check above proves the validator is
        WIRED; only this proves it WORKS — and MA51's whole point is what happens after a
        successful authentication, which no unit test of the helper can reach.
        """
        import uuid
        from valuation.config import CONFIG
        from valuation.saas.app_saas import create_saas_app
        from valuation.saas.models import UserStore

        app = create_saas_app(CONFIG)
        app.config.update(TESTING=True)
        c = app.test_client()

        def _csrf():
            with c.session_transaction() as s:
                s["_csrf_token"] = "test-csrf-token"
            return "test-csrf-token"

        # The user is created through the STORE, not through `/register`.
        #
        # My first draft posted to `/register` and treated a 302 as success. `signup_enabled`
        # is False by default and a DISABLED signup also returns 302 — to `/app` — so the
        # test's own guard passed on a redirect that had created nothing, and the real login
        # then failed for a reason that had nothing to do with MA51. A status code shared by
        # the success and the refusal cannot be used to tell them apart.
        email = "ma51_" + uuid.uuid4().hex[:8] + "@example.com"
        store = UserStore(CONFIG.database_url)     # isolated by state_isolation, never real
        store.create_user(email, "password123")
        self.assertTrue(store.verify(email, "password123"), "fixture user was not created")

        r = c.post("/login?next=https://evil.example",
                   data={"email": email, "password": "password123", "_csrf": _csrf()})
        self.assertIn(r.status_code, (301, 302))
        loc = r.headers.get("Location", "")
        self.assertNotIn("evil.example", loc)
        self.assertTrue(loc.endswith("/app"), loc)

        # ...and the legitimate case still lands where it was asked to.
        c.get("/logout")
        r2 = c.post("/login?next=/account",
                    data={"email": email, "password": "password123", "_csrf": _csrf()})
        self.assertTrue(r2.headers.get("Location", "").endswith("/account"),
                        r2.headers.get("Location"))


# ---------------------------------------------------------------------------------------
# MA8 — who the limiter thinks the caller is
# ---------------------------------------------------------------------------------------
class _Req:
    def __init__(self, xff=None, remote="9.9.9.9"):
        self.headers = {"X-Forwarded-For": xff} if xff else {}
        self.remote_addr = remote


class TestProxyShape(unittest.TestCase):

    def setUp(self):
        ratelimit.reset()
        os.environ.pop("TRUSTED_PROXY_HOPS", None)

    def tearDown(self):
        os.environ.pop("TRUSTED_PROXY_HOPS", None)

    def test_the_default_is_bit_identical_to_the_behaviour_it_replaced(self):
        """MA8 changes what is CONFIGURABLE, not what happens by default.

        The old code was `parts[-1]`. At one hop the new code must agree on every shape,
        including the empty and whitespace cases — otherwise this is a behaviour change
        wearing a diagnostic's clothes.
        """
        for xff in (None, "", "  ", "1.1.1.1", "1.1.1.1, 2.2.2.2",
                    "1.1.1.1,2.2.2.2,3.3.3.3", " 1.1.1.1 ,, 2.2.2.2 "):
            req = _Req(xff)
            parts = [p.strip() for p in (xff or "").split(",") if p.strip()]
            old = parts[-1] if parts else (req.remote_addr or "unknown")
            self.assertEqual(ratelimit.client_ip(req), old, repr(xff))

    def test_two_hops_takes_the_second_from_the_right(self):
        os.environ["TRUSTED_PROXY_HOPS"] = "2"
        self.assertEqual(ratelimit.client_ip(_Req("1.1.1.1, 2.2.2.2, 3.3.3.3")), "2.2.2.2")

    def test_a_chain_shorter_than_configured_falls_back_to_remote_addr_not_the_leftmost(self):
        """Fail to the address that cannot be forged, never to the client's own claim."""
        os.environ["TRUSTED_PROXY_HOPS"] = "2"
        self.assertEqual(ratelimit.client_ip(_Req("1.1.1.1", remote="8.8.8.8")), "8.8.8.8")

    def test_a_malformed_hop_setting_does_not_break_the_limiter(self):
        for bad in ("abc", "", "0", "-3"):
            os.environ["TRUSTED_PROXY_HOPS"] = bad
            self.assertEqual(ratelimit.client_ip(_Req("1.1.1.1, 2.2.2.2")), "2.2.2.2", bad)

    def test_the_shape_report_refuses_a_verdict_before_it_has_evidence(self):
        """Not vacuously green: three requests may not produce a confident 'consistent'."""
        for _ in range(3):
            ratelimit.client_ip(_Req("1.1.1.1"))
        rep = ratelimit.forwarded_shape()
        self.assertEqual(rep["verdict"], "insufficient")
        self.assertIn("not evidence", rep["note"])

    def test_the_shape_report_detects_the_cdn_world_that_shares_one_bucket(self):
        """The failure MA8 is actually about, made visible."""
        for _ in range(ratelimit._SHAPE_MIN_OBSERVATIONS + 5):
            ratelimit.client_ip(_Req("1.1.1.1, 2.2.2.2"))
        rep = ratelimit.forwarded_shape()
        self.assertEqual(rep["modal_chain_length"], 2)
        self.assertEqual(rep["verdict"], "mismatch")
        self.assertIn("sharing one", rep["note"])

    def test_the_shape_report_is_consistent_when_the_world_matches(self):
        for _ in range(ratelimit._SHAPE_MIN_OBSERVATIONS + 5):
            ratelimit.client_ip(_Req("1.1.1.1"))
        self.assertEqual(ratelimit.forwarded_shape()["verdict"], "consistent")

    def test_the_diagnostic_retains_no_addresses(self):
        """It answers a question about SHAPE. It must not become an access log."""
        ratelimit.client_ip(_Req("1.2.3.4, 5.6.7.8"))
        blob = repr(ratelimit.forwarded_shape()) + repr(ratelimit._xff_depths)
        for octet in ("1.2.3.4", "5.6.7.8"):
            self.assertNotIn(octet, blob)
        self.assertFalse(ratelimit.forwarded_shape()["stores_addresses"])

    def test_a_pathological_header_cannot_grow_the_counter_without_bound(self):
        ratelimit.client_ip(_Req(", ".join(f"10.0.0.{i}" for i in range(200))))
        self.assertLessEqual(max(ratelimit._xff_depths), 10)

    def test_the_diagnostic_route_is_owner_only_and_read_only(self):
        """It reports infrastructure shape, so it is behind the admin token like MA1's.

        Also pinned READ-ONLY: `GET` alone. A diagnostic that could be POSTed to would be a
        state change wearing a report's name, and this one exists to be trusted.
        """
        from valuation.config import CONFIG
        from valuation.saas.app_saas import create_saas_app

        app = create_saas_app(CONFIG)
        app.config.update(TESTING=True)
        c = app.test_client()
        orig = CONFIG.admin_token
        try:
            CONFIG.admin_token = "shape-token-xyz"
            self.assertEqual(c.get("/admin/proxy-shape").status_code, 401)
            self.assertEqual(c.get("/admin/proxy-shape",
                                   headers={"X-Admin-Token": "wrong"}).status_code, 401)
            r = c.get("/admin/proxy-shape", headers={"X-Admin-Token": "shape-token-xyz"})
            self.assertEqual(r.status_code, 200)
            body = r.get_json()
            self.assertIn("verdict", body)
            self.assertIn("trusted_proxy_hops", body)
            self.assertFalse(body["stores_addresses"])
            # Read-only: no write verb is routed here.
            self.assertEqual(c.post("/admin/proxy-shape",
                                    headers={"X-Admin-Token": "shape-token-xyz"}).status_code,
                             405)
        finally:
            CONFIG.admin_token = orig

    def test_an_unset_admin_token_cannot_open_the_diagnostic(self):
        """Fails CLOSED, matching `_admin_ok`'s documented behaviour everywhere else."""
        from valuation.config import CONFIG
        from valuation.saas.app_saas import create_saas_app

        app = create_saas_app(CONFIG)
        app.config.update(TESTING=True)
        c = app.test_client()
        orig = CONFIG.admin_token
        try:
            CONFIG.admin_token = ""
            self.assertEqual(c.get("/admin/proxy-shape").status_code, 401)
            self.assertEqual(c.get("/admin/proxy-shape",
                                   headers={"X-Admin-Token": ""}).status_code, 401)
        finally:
            CONFIG.admin_token = orig


# ---------------------------------------------------------------------------------------
# MA53 — verified closed on arrival; pinned so it stays closed
# ---------------------------------------------------------------------------------------
class TestMalformedNumericParams(unittest.TestCase):

    def test_the_500_on_a_malformed_param_is_closed_by_the_shared_clamp(self):
        """MA53 says `?top=abc` raises an unhandled 500. It does not, since MA50 landed."""
        for raw in ("abc", "", None, "1e9999", "nan", "-1", "3.7", []):
            self.assertIsInstance(clamp_int(raw, default=100, cap=500), int, repr(raw))

    def test_a_min_max_clamp_is_order_dependent_on_nan_which_is_why_clamp_float_exists(self):
        """The premise of `clamp_float`, measured rather than asserted about.

        My first draft of this test claimed NaN survives `max(lo, min(v, hi))`. It does not —
        that ordering coerces NaN to the FLOOR. The real defect is worse than the one I
        guessed: the outcome depends on which of three equivalent-looking spellings the author
        picked, and two of the three pass NaN through untouched. Pinned so the docstring's
        table cannot quietly become wrong.
        """
        nan = float("nan")
        self.assertEqual(max(1.0, min(nan, 10.0)), 1.0)          # garbage -> a valid-looking floor
        self.assertNotEqual(min(max(nan, 1.0), 10.0), min(max(nan, 1.0), 10.0))   # still NaN
        self.assertNotEqual(max(min(nan, 10.0), 1.0), max(min(nan, 10.0), 1.0))   # still NaN

    def test_clamp_float_refuses_nan_and_infinity(self):
        for raw in ("nan", "inf", "-inf", "NaN", "Infinity", "abc", None):
            got = clamp_float(raw, default=1000.0, lo=1.0, hi=1e6)
            self.assertEqual(got, 1000.0, repr(raw))

    def test_clamp_float_bounds_from_both_sides(self):
        self.assertEqual(clamp_float("-5", default=1000.0, lo=1.0, hi=1e6), 1.0)
        self.assertEqual(clamp_float("1e12", default=1000.0, lo=1.0, hi=1e6), 1e6)
        self.assertEqual(clamp_float("2500", default=1000.0, lo=1.0, hi=1e6), 2500.0)

    def test_the_risk_budget_default_survives_its_own_bounds(self):
        """The near-miss this session actually made: the bounds are DOLLARS, not a fraction.

        Written as 0..1 the clamp would have silently re-sized every alert to $1. The shipped
        default must land inside the shipped range, whatever either becomes.
        """
        from valuation.edge.options_live import DEFAULT_RISK_BUDGET
        src = _src("valuation/web/app.py")
        m = re.search(r"clamp_float\(request\.args\.get\(\"risk_budget\"\),\s*"
                      r"default=_default_budget,\s*lo=([0-9_.e]+),\s*hi=([0-9_.e]+)\)", src)
        self.assertIsNotNone(m, "the risk_budget clamp is no longer where this test looks")
        lo, hi = float(m.group(1).replace("_", "")), float(m.group(2).replace("_", ""))
        self.assertGreaterEqual(float(DEFAULT_RISK_BUDGET), lo)
        self.assertLessEqual(float(DEFAULT_RISK_BUDGET), hi)

    def test_no_raw_numeric_parse_of_a_request_param_survives_anywhere(self):
        """THE SWEEP. `int(request.args...)` / `float(request.args...)` must go through a clamp."""
        pat = re.compile(r"(?<![_A-Za-z])(int|float)\(\s*request\.(args|form|values)")
        offenders = []
        for rel in ("valuation/web/app.py", "valuation/saas/app_saas.py",
                    "valuation/saas/auth.py", "valuation/saas/billing.py"):
            for i, line in enumerate(_src(rel).split("\n"), 1):
                if pat.search(line):
                    offenders.append(f"{rel}:{i}: {line.strip()}")
        self.assertEqual(offenders, [], "unclamped numeric parse of a caller value:\n"
                                        + "\n".join(offenders))


class TestLA12PopulationMix(unittest.TestCase):

    def test_the_median_always_travels_with_its_own_denominator(self):
        """MA53 calls LA12 unfixed. The REMEDY was disclosure, not equalising the population.

        `median_upside` really is computed over only the DCF'd names while `count` reports the
        whole sector — the mix the audit describes is real. What LA12 shipped is
        `median_upside_n`, so the median can no longer be read against the wrong denominator.
        This pins that remedy; it does not claim the populations are equal.
        """
        from valuation.screener.sectors import sector_attractiveness
        rows = [{"sector": "Tech", "composite": 1.0, "rank": 1, "upside": 0.25},
                {"sector": "Tech", "composite": 0.9, "rank": 2},
                {"sector": "Tech", "composite": 0.8, "rank": 3},
                {"sector": "Banks", "composite": 0.5, "rank": 4}]
        out = {o["sector"]: o for o in sector_attractiveness(rows)}
        self.assertEqual(out["Tech"]["count"], 3)
        self.assertEqual(out["Tech"]["median_upside_n"], 1)
        self.assertIsNotNone(out["Tech"]["median_upside"])
        # The invariant that makes the number safe to render.
        for o in out.values():
            self.assertEqual(o["median_upside"] is None, o["median_upside_n"] == 0)

    def test_every_sector_row_carries_the_denominator(self):
        """A row that omits it would read as a plain median and re-open LA12 silently."""
        from valuation.screener.sectors import sector_attractiveness
        rows = [{"sector": s, "composite": 0.5, "rank": i} for i, s in enumerate("ABCD", 1)]
        for o in sector_attractiveness(rows):
            self.assertIn("median_upside_n", o)
            self.assertEqual(o["median_upside_n"], 0)
            self.assertIsNone(o["median_upside"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
