"""
PRICE ROUTING, THE RESUMABLE TRACK REFRESH, AND THE FLEET DOOR THAT COULD NOT ANSWER.

Three symptoms, measured on the service 2026-09-30, with one cause between two of them:

  * `/api/track` had scored **3 of 410** hot10 picks by 06:51Z. The refresh was a per-process
    daemon thread behind a 12-hour gate held in a module global, doing every pick in one pass
    with a per-name fetch. Seven deploys that night; each one restarted it from nothing.
  * PT-WRITER's server-side write took ~10 minutes for 87 names, and `GET /admin/track-row`
    measured from outside returned **502 after 163.8s** -- Render's proxy gives up first.
  * fleet-cycle runs #39 and #40 died on `curl: (28) ... 120000 milliseconds with 0 BYTES
    RECEIVED`; run #38 was a plain **502 in 16s**, a restarting service, a different cause.

The price cause is one ratio: `Ticker.history` returned MSFT in **0.4s** while one Stooq
request took **30.1s** to time out on the same machine on the same day. Stooq was the PRIMARY,
so every name paid the failing vendor before reaching the working one.

The fleet cause is NOT pricing -- traced and refuted here, since every book is
SELFCHECK_ABSENT so `cycle` returns at the gate and never calls an entry rule at all.
`run_day1` was the next suspect and is now GATED, and **that fix was then REFUTED on the
service**: run 36700697816, on the deployed change, still returned `000` at 120s. The slow step
is UNIDENTIFIED -- timed in a worktree the whole door is 6.6s and every step is instant, so the
cost is a property of the service's store. What ships is instrumentation: the door reports
`timings_ms` unconditionally and returns a labelled partial body rather than 0 bytes, so the
next scheduled run names the culprit instead of a fourth person guessing.

Run:  python -m pytest tests/test_price_routing.py
      python tests/test_price_routing.py
"""
# REAL STATE IS OFF LIMITS (audit LA15). This suite builds the SaaS app and calls the live
# fleet door, so without this it would read and register against the repository's own
# `data/fleet` -- and the gate runs suites in parallel, which is how a 50-second fleet suite in
# another process comes back red for reasons that have nothing to do with it. Imported ABOVE
# every `valuation` import, because the redirection has to be in place before the modules bind
# their paths.
import state_isolation  # noqa: F401  (import order is the point)

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402  — LA15: temp state only, BEFORE `valuation`

import pandas as pd  # noqa: E402

from valuation.edge import track  # noqa: E402
from valuation.screener import prices as PR  # noqa: E402


def _frame(dates, closes):
    return pd.DataFrame({"Date": list(dates), "Open": closes, "High": closes,
                         "Low": closes, "Close": list(closes), "Volume": [1] * len(closes)})


# --------------------------------------------------------------------------- (a) routing
def test_yfinance_is_the_primary_and_stooq_the_fallback():
    """The ORDER is the change. Asserted by which vendor is consulted first, not by a comment."""
    seen = []
    real_yf, real_st = PR._yf_history, PR._stooq_history
    PR._yf_history = lambda t, d, as_of=None: (seen.append("yf"), _frame(["2026-09-29"], [1.0]))[1]
    PR._stooq_history = lambda t, d=400, as_of=None: (seen.append("stooq"), None)[1]
    try:
        PR.get_history_df("AAPL")
    finally:
        PR._yf_history, PR._stooq_history = real_yf, real_st
    assert seen == ["yf"], "stooq was consulted before (or instead of) the primary: %r" % seen


def test_an_empty_yfinance_frame_means_TRY_STOOQ_and_never_no_price():
    """The contract that makes the fallback reachable at all.

    Treating "Yahoo does not carry this name" as "this name has no price" is how a working
    fallback would never be consulted -- the defect this ordering exists to avoid, one vendor
    along.
    """
    seen = []
    real_yf, real_st = PR._yf_history, PR._stooq_history
    PR._yf_history = lambda t, d, as_of=None: None
    PR._stooq_history = lambda t, d=400, as_of=None: (seen.append(t), "STOOQ")[1]
    try:
        assert PR.get_history_df("ZZZZ") == "STOOQ"
    finally:
        PR._yf_history, PR._stooq_history = real_yf, real_st
    assert seen == ["ZZZZ"], seen


def test_exhausting_every_vendor_is_UNPRICED_and_is_counted():
    """GUARDRAIL (i), FAIL CLOSED. Never a stale frame, never a last-known close."""
    real = (PR._yf_history, PR._stooq_history, PR._fmp_history)
    PR._yf_history = lambda t, d, as_of=None: None
    PR._stooq_history = lambda t, d=400, as_of=None: None
    PR._fmp_history = lambda t, d, as_of=None: None
    try:
        PR.reset_census()
        got = PR.get_history_df("ZZZZ", as_of="2026-09-29")
        assert got is None, "a name no vendor could price returned a frame: %r" % (got,)
        assert PR.source_census().get("unpriced") == 1, PR.source_census()
    finally:
        PR._yf_history, PR._stooq_history, PR._fmp_history = real


def test_a_429_is_throttled_not_a_vendor_failure():
    """GUARDRAIL (iv). 'Unpriced this run, retry next run' -- a throttled afternoon must not
    read as a dead vendor, or the census stops distinguishing them."""
    assert PR._is_throttle(Exception("HTTP Error 429: Too Many Requests"))
    assert PR._is_throttle(Exception("rate limit exceeded"))
    # A 404 is a genuine miss and must NOT be laundered into a throttle, or a dead vendor would
    # look like a busy one forever.
    assert not PR._is_throttle(Exception("404 Client Error: Not Found"))

    # The TYPE rule must stand on its own, or a vendor reword silently reclassifies a throttle.
    from yfinance.exceptions import YFRateLimitError as _RL
    class _Reworded(_RL):
        def __str__(self):
            return "request refused, please slow down"
    assert PR._is_throttle(_Reworded()), "a throttle is only recognised by its message text"

    # THE DOUBLE RAISES WHAT THE VENDOR RAISES. An earlier cut of this test raised a bare
    # `RuntimeError`, which yfinance never raises -- harmless under a broad `except Exception`
    # and, once the primary's catch was narrowed to named vendor errors, a test asserting the
    # classifier works on a type that cannot occur. Both realistic shapes are exercised.
    import yfinance as yf
    import requests
    from yfinance.exceptions import YFRateLimitError
    real = yf.Ticker
    shapes = {
        # No message argument: the class carries its own, which is exactly why classifying a
        # throttle by message text alone is fragile.
        "YFRateLimitError": YFRateLimitError(),
        "requests.HTTPError": requests.HTTPError(
            "429 Client Error: Too Many Requests for url: ..."),
    }
    try:
        for label, exc in shapes.items():
            class _Boom:
                def __init__(self, *a, **k):
                    pass
                def history(self, *a, **k):
                    raise exc
            yf.Ticker = _Boom
            PR.reset_census()
            assert PR._yf_history("AAPL", 400) is None, label
            c = PR.source_census()
            assert c.get("throttled") == 1, (label, c)
            assert c.get("primary_failures", 0) == 0, (
                "%s: a throttle was counted as a vendor failure: %r" % (label, c))
    finally:
        yf.Ticker = real


def test_a_YFNotImplementedError_is_a_VENDOR_DECLINE_and_not_a_500():
    """The one vendor class that does NOT derive from `YFException`.

    Its MRO is NotImplementedError -> RuntimeError, so naming only the base would let it escape
    the primary's catch and surface as a 500 on a request that should simply have fallen through
    to Stooq. Found by mutation: dropping it from the tuple left every test green, because
    widening a catch is invisible to a suite that never exercises the widened case.

    It is named EXPLICITLY rather than caught by widening to `RuntimeError`, which would put
    genuine programming errors back inside the vendor bucket -- the defect the narrowing exists
    to prevent.
    """
    import yfinance as yf
    from yfinance.exceptions import YFNotImplementedError
    real = yf.Ticker

    class _Boom:
        def __init__(self, *a, **k):
            pass

        def history(self, *a, **k):
            raise YFNotImplementedError("history")

    yf.Ticker = _Boom
    try:
        PR.reset_census()
        assert PR._yf_history("AAPL", 400) is None, "it escaped the primary's catch"
        c = PR.source_census()
        assert c.get("primary_failures") == 1, ("a vendor decline was not counted as one: %r" % c)
    finally:
        yf.Ticker = real


def test_the_batch_falls_back_per_name_and_a_throttled_chunk_does_not_abort_it():
    """GUARDRAIL (iv). One bad chunk costs a chunk, not the run."""
    import yfinance as yf
    from yfinance.exceptions import YFRateLimitError
    real_dl, real_single = yf.download, PR.get_history_df
    def _boom(*a, **k):
        raise YFRateLimitError()
    asked = []
    yf.download = _boom
    PR.get_history_df = lambda t, days=400, as_of=None: (asked.append(t), "PER-NAME")[1]
    try:
        PR.reset_census()
        out = PR.get_history_batch(["A", "B", "C"], days=400)
    finally:
        yf.download, PR.get_history_df = real_dl, real_single
    assert out == {"A": "PER-NAME", "B": "PER-NAME", "C": "PER-NAME"}, out
    assert asked == ["A", "B", "C"], asked
    assert PR.source_census().get("throttled") == 3, PR.source_census()


def test_fmp_stays_gated_off():
    """GUARDRAIL (iii). A key alone must not enable it; the opt-in is separate and deliberate."""
    old_key = os.environ.get("FMP_API_KEY")
    old_allow = os.environ.get("PRICES_ALLOW_FMP")
    os.environ["FMP_API_KEY"] = "test-key-not-real"
    os.environ.pop("PRICES_ALLOW_FMP", None)
    import requests
    calls = []
    real_get = requests.get
    requests.get = lambda *a, **k: (calls.append(a), real_get(*a, **k))[1]
    try:
        assert PR._fmp_history("AAPL", 400) is None, "FMP priced a name without the opt-in"
        # THE GATE, NOT THE OUTCOME. A bogus key makes the request fail and return None too, so
        # asserting None alone passed with the gate deleted -- mutation proved it. What must
        # hold is that no request was ATTEMPTED.
        assert calls == [], "FMP was contacted despite the opt-in being unset: %r" % (calls,)
    finally:
        requests.get = real_get
        if old_key is None:
            os.environ.pop("FMP_API_KEY", None)
        else:
            os.environ["FMP_API_KEY"] = old_key
        if old_allow is not None:
            os.environ["PRICES_ALLOW_FMP"] = old_allow


# --------------------------------------------------------------------------- (b) the refresh
class _Store:
    def __init__(self, n):
        self.meta, self.returns = {}, {}
        self.picks = [{"ticker": "T%03d" % i, "run_date": "2025-06-02", "rank": 1}
                      for i in range(n)]

    def all_track_picks(self, source):
        return list(self.picks)

    def set_meta(self, k, v):
        self.meta[k] = v

    def get_meta(self, k, default=None):
        return self.meta.get(k, default)

    def has_track_return(self, *a):
        return a in self.returns

    def save_track_return(self, source, rd, t, h, r, b):
        self.returns[(source, rd, t, h)] = (r, b)


_DATES = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2025-01-01", "2026-09-29")]


def _prices(ts):
    return {t: _frame(_DATES, [100.0 + i + j * 0.1 for j in range(len(_DATES))])
            for i, t in enumerate(ts)}


def test_the_refresh_is_bounded_per_call():
    st = _Store(210)
    r = track.refresh_step(st, "hot10", budget=60, price_batch=_prices)
    assert r["stepped"] == 60 and r["cursor"] == 60, r


def test_the_refresh_RESUMES_across_a_deploy_instead_of_restarting():
    """The whole defect. The cursor must live in the store, not in the process."""
    st = _Store(210)
    track.refresh_step(st, "hot10", budget=60, price_batch=_prices)

    # A deploy: a brand-new process that has only what was PERSISTED.
    fresh = _Store(210)
    fresh.meta = dict(st.meta)
    assert fresh.get_meta(track.REFRESH_KEY % "hot10")["cursor"] == 60

    r2 = track.refresh_step(fresh, "hot10", budget=60, price_batch=_prices)
    assert r2["cursor"] == 120, ("the refresh restarted instead of resuming: %r" % r2)


def test_the_refresh_converges_and_marks_itself_done():
    st = _Store(150)
    for _ in range(10):
        r = track.refresh_step(st, "hot10", budget=60, price_batch=_prices)
        if r["cursor"] >= r["picks"]:
            break
    fin = st.get_meta(track.REFRESH_KEY % "hot10")
    assert fin["cursor"] == 150 and fin["done_at"], fin
    assert fin["computed"] > 0, fin


def test_no_benchmark_leaves_the_cursor_UNMOVED():
    """GUARDRAIL (i) for progress: never record having scored names that were not scored."""
    st = _Store(210)
    r = track.refresh_step(st, "hot10", budget=60,
                           price_batch=lambda ts: {t: None for t in ts})
    assert r["benchmark_priced"] is False and r["stepped"] == 0, r
    assert st.get_meta(track.REFRESH_KEY % "hot10")["cursor"] == 0, "the cursor advanced"


def test_a_name_no_vendor_can_price_is_counted_unpriced_not_skipped():
    """It is attempted, recorded, and the cursor moves past it -- next cycle asks again."""
    st = _Store(3)

    def _partial(ts):
        out = _prices(ts)
        out["T001"] = None                      # one name no vendor could serve
        return out

    r = track.refresh_step(st, "hot10", budget=60, price_batch=_partial)
    assert "T001" in r["unpriced"], r
    assert r["cursor"] == 3, r


def test_the_refresh_status_survives_the_process_that_produced_it():
    """`refresh` was null on every response from a freshly deployed process."""
    from valuation.web import app as W
    st = _Store(10)
    track.refresh_step(st, "hot10", budget=5, price_batch=_prices)
    view = W._track_refresh_view(st, "hot10")
    assert view and view["scored_so_far"] == 5 and view["remaining"] == 5, view
    assert view["complete"] is False, view
    # AND IT MUST BE WIRED INTO THE PAYLOAD. Testing the helper alone left the call site free
    # to return null -- which is exactly the symptom being fixed, so mutation caught it.
    import inspect
    src = inspect.getsource(W)
    assert '"refresh": _track_refresh_view(st, source)' in src,         "/api/track no longer reports the stored refresh status"


# --------------------------------------------------------------------------- (c) fleet door
_TOKEN = "test-token-not-a-secret"


def _fleet_client():
    """An app whose admin token is set ON THE LIVE CONFIG, not via the environment.

    `create_saas_app` is IDEMPOTENT: a test that sets an env var and then builds "a fresh app"
    gets the app an earlier test already built, so the variable never takes effect and the door
    answers 401 -- a test that passes for the wrong reason, or here fails for one. The token is
    written onto the config object the handler actually reads, and restored by the caller.
    """
    from valuation.saas.app_saas import create_saas_app
    app = create_saas_app()
    app.config["TESTING"] = True
    return app


def _with_token(fn):
    # `create_saas_app(cfg=CONFIG)` binds the DEFAULT argument once, so the object the handler
    # closes over is this module-level singleton -- not a copy, and not anything an env var set
    # after import can reach.
    from valuation.config import CONFIG as cfg
    app = _fleet_client()
    assert hasattr(cfg, "admin_token"), "cannot reach the config the handler reads"
    was = cfg.admin_token
    try:
        cfg.admin_token = _TOKEN
        return fn(app.test_client())
    finally:
        cfg.admin_token = was


def test_the_fleet_door_ALWAYS_reports_its_own_timings():
    """Runs #39, #40 and the post-fix #36700697816 all returned 0 BYTES at 120s.

    A request that sends nothing says only that something was slow. Flask buffers the whole
    JSON, so one slow step destroys the timings of every step that was fine -- which is why
    three attempts at this produced no measurement of the real path. The timings are
    UNCONDITIONAL: a diagnostic that has to be asked for is not there on the day it is needed.
    """
    r = _with_token(lambda c: c.get("/admin/fleet-cycle",
                                    headers={"X-Admin-Token": _TOKEN}))
    assert r.status_code == 200, r.status_code
    d = r.get_json()
    assert isinstance(d.get("timings_ms"), dict), "the door does not time itself"
    assert "cycle" in d["timings_ms"], sorted(d["timings_ms"])
    assert isinstance(d.get("elapsed_ms"), int), d.get("elapsed_ms")
    # Every recorded value is a real measurement, not a placeholder.
    for k, v in d["timings_ms"].items():
        assert isinstance(v, int) and v >= 0, (k, v)


def test_a_BLOWN_BUDGET_returns_a_LABELLED_BODY_and_never_zero_bytes():
    """The whole point. `budget=0` forces the deadline so the branch is REACHABLE in a test.

    A body naming what it skipped is strictly more useful than 120s of silence, and it is the
    only way the runner learns which step spent the budget.
    """
    r = _with_token(lambda c: c.get("/admin/fleet-cycle?budget=0",
                                    headers={"X-Admin-Token": _TOKEN}))
    assert r.status_code == 200, r.status_code
    d = r.get_json()
    assert d.get("partial") is True, d.get("partial")
    assert d.get("deferred"), "it skipped work without naming it"
    assert "gates" in d["deferred"], d["deferred"]
    assert "budget" in (d.get("partial_reason") or ""), d.get("partial_reason")
    assert isinstance(d.get("timings_ms"), dict) and d["timings_ms"], "no timings on the way out"


def test_the_deadline_NEVER_defers_a_RECORDER():
    """A missing history day is the failure `fleet_history` exists to prevent.

    Deferring the reporting is a convenience; deferring a recorder would silently lose a day of
    a series that cannot be reconstructed, so the deferrable set is asserted by NAME rather than
    left to whatever happens to sit after the deadline check.
    """
    import ast
    import io as _io
    src = _io.open("valuation/saas/app_saas.py", encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "admin_fleet_cycle")
    named = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.List):
            vals = [e.value for e in node.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            if "gates" in vals:
                named |= set(vals)
    assert named, "the deferred list is no longer a literal this guard can read"
    forbidden = {"record_all", "invalidate_fabricated_span", "history", "cycle"}
    assert not (named & forbidden), "a recorder is in the deferrable set: %s" % (named & forbidden)


def test_the_fleet_door_no_longer_certifies_on_every_cycle():
    """The livelock: certifying could not finish inside 120s, so nothing ever certified.

    Read from the SOURCE because the door needs a live store, a token and a broker to run --
    what is pinned is that the expensive call is gated on an explicit opt-in and that a plain
    `run=1` cannot reach it.
    """
    import inspect
    from valuation.saas import app_saas
    src = inspect.getsource(app_saas)
    i_gate = src.index("wants_selfcheck")
    i_call = src.index("_sc.run_day1(")
    assert i_gate < i_call, "run_day1 is reachable without the opt-in"
    line = [l for l in src.splitlines() if "_sc.run_day1(" in l][0]
    guard = [l for l in src.splitlines() if "if wants_run and stale and wants_selfcheck" in l]
    assert guard, "the three-part guard on certification is gone"
    assert "selfcheck_pending" in src, "a cycle blocked on certification says nothing about it"


def test_the_fleet_path_does_not_price_names():
    """A refuted hypothesis, pinned so it is not re-adopted.

    The obvious suspect for a door that cannot answer in 120s was `get_history_df` on the
    request thread -- it is the cause for the writer and the refresh. It is NOT the cause here:
    the fleet entry-rule path reaches no price fetcher at all.
    """
    import inspect
    from valuation.edge import fleet, fleet_books
    for mod in (fleet, fleet_books):
        src = inspect.getsource(mod)
        assert "get_history_df" not in src, (
            "%s now prices names -- the fleet timeout diagnosis needs re-deriving" % mod.__name__)


if __name__ == "__main__":
    import traceback
    fails = 0
    for name, fn in sorted(list(globals().items())):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("  ok   %s" % name)
            except Exception:
                fails += 1
                print("  FAIL %s" % name)
                traceback.print_exc()
    print("\n%s" % ("all passed" if not fails else "%d failed" % fails))
    sys.exit(1 if fails else 0)
