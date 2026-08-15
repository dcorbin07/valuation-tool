"""MA50 (row-cap bypass) and MA10 (one admin credential for the product AND the record).

MA50 — `/api/hotstocks?top=-1` defeated the per-tier row cap. `min(int(...), cap)` bounds from
above only, `min(-1, 500)` is -1, and `store.load_snapshot` interpolates that into
`LIMIT {int(top)}`, which SQLite treats as UNLIMITED. The cap IS the paywall. Masked in
production only because OPEN_ACCESS=true makes everyone premium.

MA10 — one `X-Admin-Token` opened every /admin/ route, including the two that rewrite the LIVE
scoring weights, and it bypassed the rate limiter entirely.

The MA50 route tests record the value that reaches the STORE rather than counting rows in a
response. That is deliberate: the defect is the number handed to SQL, and a test that counts
rows would pass on an empty database — which is exactly the state a fresh CI checkout is in.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.config import CONFIG                    # noqa: E402
from valuation.web.query_params import clamp_int       # noqa: E402

CONFIG.private_mode = False
CONFIG.open_access = True
ADMIN = "test-admin-token-ma10"
WRITE = "test-admin-write-token-ma10"
CONFIG.admin_token = ADMIN
CONFIG.admin_write_token = ""
#: These tests POST to the two LIVE-WEIGHT WRITERS to prove which credential opens them. The
#: learner is switched off so what is measured is the AUTH GATE and not a real re-tune: with
#: it on, a passing test would mean the suite had just retrained the shipped model. The gate
#: runs before this flag is read, so an unauthorized caller still gets its 401.
CONFIG.learn_enabled = False

from valuation.saas.app_saas import create_saas_app    # noqa: E402

APP = create_saas_app(CONFIG)
APP.config["TESTING"] = True


# ============================== MA50 — the clamp itself ====================================
def test_the_clamp_never_returns_a_value_outside_the_range():
    """The whole contract, swept. No input may escape [floor, cap] or raise."""
    cap = 10
    for raw in ("-1", "-99999", "0", "1", "5", "10", "11", "99999", "abc", "", None,
                "1e9", "3.7", " 4 ", "0x10", "-0", "NaN", "None", [], {}, 4.9):
        got = clamp_int(raw, default=100, cap=cap)
        assert isinstance(got, int), f"{raw!r} -> {got!r}, not an int"
        assert 1 <= got <= cap, f"{raw!r} escaped the range: {got}"


def test_a_negative_is_the_floor_and_an_absurd_value_is_the_cap():
    """The two directions of the bug, named. `-1` was the exploit; a huge value is the same
    request wearing an honest face, and it must come back as the tier's cap."""
    assert clamp_int("-1", default=100, cap=500) == 1
    assert clamp_int("-1", default=100, cap=10) == 1
    assert clamp_int("99999", default=100, cap=10) == 10, "an absurd value must give the cap"
    assert clamp_int("99999", default=100, cap=500) == 500


def test_garbage_degrades_to_the_default_and_never_to_the_cap():
    """A limiter whose failure mode is 'serve everything' is the failure being fixed. On a
    free tier (cap 10, default 100) unparseable input must land at 10 by the CAP, not by the
    default sliding through unclamped."""
    assert clamp_int("abc", default=100, cap=10) == 10
    assert clamp_int(None, default=5, cap=10) == 5, "a missing value keeps the default"
    assert clamp_int("abc", default=5, cap=10) == 5


def test_the_cap_beats_the_floor_when_they_disagree():
    """A cap below the floor is a config error, and the entitlement must still win — a floor
    that could lift a caller above their cap would reintroduce the bug from the other side."""
    assert clamp_int("5", default=1, cap=0) == 0
    assert clamp_int("-1", default=1, cap=0) == 0


def test_it_is_the_audits_own_arithmetic_and_not_a_variation_on_it():
    """The registered remedy is `min(max(1, int(...)), cap)`. Pinned against a reference
    implementation so a future 'tidy-up' cannot quietly change the semantics; the only
    declared difference is the parse guard, so only parseable inputs are compared."""
    for raw in ("-5", "-1", "0", "1", "7", "10", "99", "500"):
        for cap in (1, 10, 500):
            assert clamp_int(raw, default=100, cap=cap) == min(max(1, int(raw)), cap), \
                f"clamp_int diverges from the audit's fix at raw={raw} cap={cap}"


# ============================== MA50 — the wiring ==========================================
class _RecordingStore:
    """Stands in for the screener Store and remembers the `top` it was handed."""
    seen = []

    def latest_scan_date(self):
        return "2026-08-14"

    def load_snapshot(self, scan_date=None, top=None):
        _RecordingStore.seen.append(top)
        return []

    def latest_intraday_time(self):
        return None

    def get_meta(self, *a, **k):
        return {}

    def __getattr__(self, name):
        # The route calls a handful of other read methods (list_scans, and whatever it grows
        # next) purely to decorate the payload. Standing in for them with an empty read keeps
        # this double focused on the one thing it exists to observe — the `top` handed to the
        # SQL LIMIT — instead of breaking every time the response gains a field.
        return lambda *a, **k: []


def _hotstocks_top_for(query, tier_cap):
    """Call /api/hotstocks and return every `top` that reached the store."""
    from valuation.web import app as webapp
    from valuation.saas import gating
    _RecordingStore.seen = []
    orig_store, orig_feats = webapp._store, gating.features
    webapp._store = lambda: _RecordingStore()
    gating.features = lambda tier: dict(orig_feats(tier), hotstocks_top=tier_cap)
    try:
        with APP.test_client() as c:
            c.get(f"/api/hotstocks{query}")
    finally:
        webapp._store, gating.features = orig_store, orig_feats
    return [t for t in _RecordingStore.seen if t is not None]


def test_a_negative_top_can_no_longer_reach_the_sql_limit():
    """MA50, at the site. `LIMIT -1` is unlimited in SQLite, so the value handed to the store
    is the whole vulnerability — not the row count, which is empty in a fresh checkout."""
    tops = _hotstocks_top_for("?top=-1", tier_cap=10)
    assert tops, "the route never reached the store, so this test proves nothing"
    for t in tops:
        assert t >= 1, f"a negative top still reaches the SQL LIMIT: {t}"


def test_an_absurd_top_comes_back_as_the_tier_cap():
    """The paywall, stated as an assertion: a free visitor asking for everything gets 10."""
    for q in ("?top=99999", "?top=-1", "?top=abc", "?top=0", ""):
        tops = _hotstocks_top_for(q, tier_cap=10)
        assert tops, f"{q!r} never reached the store"
        for t in tops:
            assert 1 <= t <= 10, f"{q!r} escaped the tier cap of 10: {t}"
    assert max(_hotstocks_top_for("?top=99999", tier_cap=10)) == 10, \
        "an absurd request should be served the cap, not the floor"


def test_the_tier_cap_is_what_moves_when_the_tier_does():
    """Guards against a fix that hard-codes a number instead of honouring the cap — which
    would pass every assertion above while silently unpricing the premium tier."""
    assert max(_hotstocks_top_for("?top=99999", tier_cap=500)) == 500
    assert max(_hotstocks_top_for("?top=99999", tier_cap=10)) == 10


def test_no_hand_rolled_row_clamp_survives_anywhere_in_the_web_surfaces():
    """THE SWEEP. Five sites had the one-sided clamp, written independently each time, so
    fixing the reported one and leaving the others is how this comes back. Fails if any
    `int(request.args...)` is used for a row count outside the shared helper."""
    import pathlib
    import re
    root = pathlib.Path(__file__).resolve().parent.parent / "valuation"
    # The lookbehind excludes `clamp_int(request.args.get(...))` — the fix itself — while
    # still catching a bare `int(request.args.get(...))`. Without it this matched the tail of
    # every call to the helper and reported the repair as the defect.
    pattern = re.compile(r"(?<![_A-Za-z])int\(\s*request\.args\.get\(", re.S)
    offenders = []
    for py in list((root / "web").rglob("*.py")) + list((root / "saas").rglob("*.py")):
        if py.name == "query_params.py":
            continue          # the module documents the old shape in its docstring
        src = py.read_text(encoding="utf-8")
        for m in pattern.finditer(src):
            line = src[:m.start()].count("\n") + 1
            offenders.append(f"{py.relative_to(root)}:{line}")
    assert not offenders, (
        "hand-rolled int() on a query parameter (MA50 class) at: "
        + ", ".join(offenders) + " — route it through web.query_params.clamp_int")


# ============================== MA10 — the capability split ================================
#: Derived from the app, not restated: a third live-weight writer added later must be caught
#: by this suite rather than quietly inherit the blanket admin token.
WEIGHT_WRITE_ROUTES = ("/admin/run-learning", "/admin/adopt-backtest-weights")


def _post(path, token=None, header="X-Admin-Token"):
    with APP.test_client() as c:
        return c.post(path, headers={header: token} if token else {})


def test_unset_write_token_leaves_behaviour_bit_identical():
    """The split ships INERT. Setting ADMIN_WRITE_TOKEN is a Render/GitHub env change no code
    lane can make, and a gate that failed closed on deploy would break five crons to fix a
    hardening item. Until it is set, the ordinary admin token still opens these routes."""
    CONFIG.admin_write_token = ""
    for r in WEIGHT_WRITE_ROUTES:
        assert _post(r, ADMIN).status_code != 401, f"{r} refused the admin token while unsplit"
        assert _post(r).status_code == 401, f"{r} answered with no token at all"
        assert _post(r, "wrong").status_code == 401, f"{r} accepted a wrong token"


def test_setting_the_write_token_closes_the_routes_to_the_ordinary_admin_token():
    """The split, activated. This is the property the whole item exists for: the credential
    that runs the daily scan stops being the credential that can re-tune the live model."""
    CONFIG.admin_write_token = WRITE
    try:
        for r in WEIGHT_WRITE_ROUTES:
            assert _post(r, ADMIN).status_code == 401, \
                f"{r} still opens to the ordinary ADMIN_TOKEN, so the split does nothing"
            assert _post(r, WRITE).status_code != 401, f"{r} refused the write token"
            assert _post(r, WRITE, header="X-Admin-Write-Token").status_code != 401, \
                f"{r} does not accept the dedicated header"
            assert _post(r, "wrong").status_code == 401
    finally:
        CONFIG.admin_write_token = ""


def test_the_split_does_not_touch_the_read_and_trigger_routes():
    """Scope. Splitting the two writers must not lock the other admin routes out of the
    credential their callers actually hold — that would break the crons it exists to protect."""
    CONFIG.admin_write_token = WRITE
    try:
        with APP.test_client() as c:
            r = c.get("/admin/export-track", headers={"X-Admin-Token": ADMIN})
        assert r.status_code != 401, "the split locked a READ route out of ADMIN_TOKEN"
    finally:
        CONFIG.admin_write_token = ""


def test_an_empty_configured_write_token_can_never_match():
    """Fail closed, the same rule as `_admin_ok`. An empty ADMIN_WRITE_TOKEN falls back to
    ADMIN_TOKEN; it must never be satisfied by an empty header."""
    CONFIG.admin_write_token = ""
    before = CONFIG.admin_token
    CONFIG.admin_token = ""
    try:
        for r in WEIGHT_WRITE_ROUTES:
            assert _post(r).status_code == 401, f"{r} opened with both tokens unset"
            assert _post(r, "").status_code == 401
    finally:
        CONFIG.admin_token = before


# ============================== MA10 — the limiter =========================================
def _bucket_used(headers):
    """Which limit bucket one request to a limited path lands in.

    `ratelimit.check` is stubbed to RECORD and then refuse, so the request is answered 429 in
    `before_request` and the route never executes. Exhausting the real limit here would mean
    running a whole-market scan several hundred times, which is how the first draft of this
    test hung the suite.

    `/api/value` with `run_ai` rather than `/api/scan/run` or `/api/portfolio`: both of those
    are refused by `surfaces.check` (may_act / owner-only) BEFORE the limiter is consulted, so
    the anonymous control would read "no bucket" for a reason with nothing to do with MA10.
    `/api/value` is the product's core public action and is limited only when it asks for the
    AI layer — which is exactly the owner-spend case this bucket exists for.
    """
    from valuation.saas import ratelimit
    seen = []
    orig = ratelimit.check
    ratelimit.check = lambda ip, bucket: (seen.append(bucket), 60)[1]
    try:
        with APP.test_client() as c:
            c.post("/api/value", headers=headers,
                   json={"ticker": "AAPL", "run_ai": True})
    finally:
        ratelimit.check = orig
    return seen


def test_the_admin_token_no_longer_bypasses_the_rate_limiter_entirely():
    """It used to skip the limiter outright (`if bucket and not _admin_ok()`), making one
    credential simultaneously the key to the product and an uncapped lever on the owner's
    Anthropic and FMP spend. It now has a ceiling instead of an exemption."""
    from valuation.saas import ratelimit
    admin = _bucket_used({"X-Admin-Token": ADMIN})
    assert admin, "an admin caller still reaches no limiter at all"
    assert admin == [ratelimit.ADMIN_BUCKET], \
        f"admin traffic landed in {admin}, not the admin bucket"


def test_an_anonymous_caller_still_lands_in_the_endpoints_own_bucket():
    """The control. Without it, 'admin is limited now' could be satisfied by routing
    EVERYONE into the generous admin bucket — which would loosen the public limits that
    exist to protect the owner's vendor spend."""
    anon = _bucket_used({})
    assert anon == ["ai:value"], \
        f"anonymous traffic landed in {anon}, not the endpoint's own bucket"


def test_the_admin_ceiling_actually_refuses_once_it_is_reached():
    """That a bucket is consulted is not that it bites. Checked against the real limiter with
    the ceiling temporarily lowered, so the property is proved without several hundred scans."""
    from valuation.saas import ratelimit
    orig = ratelimit.LIMITS[ratelimit.ADMIN_BUCKET]
    ratelimit.LIMITS[ratelimit.ADMIN_BUCKET] = (2, 3600)
    ratelimit.reset()
    try:
        ip = "203.0.113.7"
        codes = [ratelimit.check(ip, ratelimit.ADMIN_BUCKET) for _ in range(4)]
        assert codes[0] is None and codes[1] is None, "the ceiling fired too early"
        assert codes[2] is not None, "the admin ceiling never refuses, i.e. it is still infinite"
    finally:
        ratelimit.LIMITS[ratelimit.ADMIN_BUCKET] = orig
        ratelimit.reset()


def test_the_admin_ceiling_is_far_above_anything_the_crons_do():
    """The other half of the same decision, and the one that keeps this from being a
    regression. Ten scheduled jobs on an hourly-at-most cadence must never come near it."""
    from valuation.saas import ratelimit
    n, window = ratelimit.LIMITS[ratelimit.ADMIN_BUCKET]
    assert window <= 3600 and n >= 300, \
        f"the admin bucket ({n} per {window}s) is tight enough to break a scheduled job"


def test_an_admin_caller_does_not_share_a_counter_with_anonymous_traffic():
    """Otherwise a flood of anonymous requests could starve the scan cron — the limiter
    turning into the outage it exists to prevent."""
    from valuation.saas import ratelimit
    assert ratelimit.ADMIN_BUCKET not in ("/api/scan/run", "/api/signals/run",
                                          "/api/portfolio", "ai:value"), \
        "admin traffic shares a bucket with the public endpoint it is exempted from"
    assert ratelimit.ADMIN_BUCKET in ratelimit.LIMITS, "the admin bucket has no limit defined"


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
    print(f"\n{passed}/{len(tests)} row-cap + admin-split tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
