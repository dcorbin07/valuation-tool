"""MA7 — the public endpoints that spend the owner's vendor quota are capped.

THE DEFECT. `ratelimit` capped `/api/scan/run` at 3/hour because *"FMP quota, 3 requests per
uncached name"*, and deliberately left `/api/value` unlimited unless `run_ai` was set, because
*"the plain valuation is the product's core action"*. But the plain valuation runs the full
adaptive DCF on a CALLER-SUPPLIED symbol, so it reaches the same upstream. The result cache
defends against REPEATS; nothing defended against ENUMERATION, and the universe is ~7,100
names. `/api/rank` was worse and was in no bucket at all: up to 25 `value_ticker` calls per
request, 2,000 Monte Carlo trials each, on a 512 MB box.

AND A THIRD THE AUDIT DID NOT NAME, found by the sweep it asked for: `/api/dip` is public, in
no bucket, and fans out through the same `_get_or_compute` for up to `MAX_SHORTLIST` names —
with the fan-out taken from a CALLER-SUPPLIED query parameter.

WHY THE BUDGET IS DENOMINATED IN NAME-VALUATIONS. The requests differ in cost by up to 25x, so
a per-REQUEST cap has to be set for the worst case and is then absurdly tight for the common
one. Charging the actual scarce unit means 120 buys either 120 single valuations or ~5 full
25-name ranks or any mix — the audit's own number, charged correctly.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.config import CONFIG                      # noqa: E402
from valuation.saas import ratelimit                     # noqa: E402

CONFIG.private_mode = False
CONFIG.open_access = True

VB = ratelimit.VENDOR_BUCKET


# ============================== the endpoints are in a bucket at all =======================
def test_every_endpoint_that_valuates_a_caller_supplied_name_is_capped():
    """The three that reach `value_ticker` on names the CALLER chooses. Anything that only
    reads the cached snapshot is deliberately not here — reading stays free."""
    for path in ("/api/value", "/api/rank", "/api/dip"):
        b = dict(ratelimit.buckets_for(path, {"tickers": ["AAPL"]}))
        assert VB in b, f"{path} spends the vendor quota and is in no budget"


def test_the_plain_valuation_is_capped_not_only_the_ai_one():
    """The exact defect MA7 names: `run_ai` was the only thing that bought a bucket."""
    assert dict(ratelimit.buckets_for("/api/value", {"ticker": "NKE"})).get(VB) == 1


def test_an_ai_request_is_charged_for_both_things_it_spends():
    """It spends the FMP quota AND an Anthropic call. The old single-bucket form could only
    charge one of them, and it charged the wrong one — the vendor cap went unenforced."""
    b = dict(ratelimit.buckets_for("/api/value", {"ticker": "NKE", "run_ai": True}))
    assert b.get("ai:value") == 1 and b.get(VB) == 1


def test_reads_are_still_free():
    """Open access is a product decision, not a bug. A fix that capped reading would be a
    worse outcome than the defect."""
    for path in ("/api/hotstocks", "/api/health", "/api/signals", "/api/valquo-index",
                 "/api/track", "/api/index-track"):
        assert ratelimit.buckets_for(path, {}) == (), f"{path} became limited"


# ============================== the cost is the fan-out ====================================
def test_rank_is_charged_per_NAME_and_not_per_request():
    """The whole point. A 25-name rank costs 25x a single valuation because it does 25x the
    upstream work; charging it once is what let it be a 25x amplifier."""
    for n in (1, 3, 25):
        cost = dict(ratelimit.buckets_for("/api/rank", {"tickers": ["T%d" % i for i in range(n)]}))
        assert cost[VB] == n, f"a {n}-name rank was charged {cost[VB]}"


def test_the_charge_cannot_exceed_what_the_route_will_actually_value():
    """Charging for names the route slices off would be a limiter reporting work nobody did."""
    over = dict(ratelimit.buckets_for("/api/rank", {"tickers": ["T%d" % i for i in range(500)]}))
    assert over[VB] == ratelimit.RANK_MAX


def test_the_rank_ceiling_matches_the_slice_the_route_actually_takes():
    """Pins the charge to the DOING. `api_rank` slices `tickers[:25]`; if that number moves and
    RANK_MAX does not, the limiter silently under- or over-charges every rank request."""
    import re
    import pathlib
    src = (pathlib.Path(__file__).resolve().parent.parent
           / "valuation" / "web" / "app.py").read_text(encoding="utf-8")
    m = re.search(r"for t in tickers\[:(\d+)\]", src)
    assert m, "the rank slice is no longer a literal — re-pin this against whatever replaced it"
    assert int(m.group(1)) == ratelimit.RANK_MAX, \
        f"api_rank values {m.group(1)} names but the limiter charges {ratelimit.RANK_MAX}"


def test_dip_is_charged_its_caller_supplied_shortlist():
    """The endpoint the audit did not name. Its fan-out comes from the QUERY STRING, so the
    cost is caller-controlled — the same property that made /api/rank the sharper case."""
    from valuation.web import dip
    assert dict(ratelimit.buckets_for("/api/dip", {}, {}))[VB] == dip.DEFAULT_SHORTLIST
    assert dict(ratelimit.buckets_for("/api/dip", {}, {"shortlist": "25"}))[VB] == 25
    # ...and a caller cannot ask for a cheap charge and a big fan-out: the same clamp the
    # route uses decides both, so an absurd or negative value lands inside [1, MAX].
    for bad in ("99999", "-1", "0", "abc", ""):
        c = dict(ratelimit.buckets_for("/api/dip", {}, {"shortlist": bad}))[VB]
        assert 1 <= c <= dip.MAX_SHORTLIST, f"shortlist={bad!r} charged {c}"


def test_an_unknown_fan_out_is_charged_the_ceiling_not_a_free_pass():
    """Fail EXPENSIVE. If the cost cannot be computed the request must be charged the most it
    could possibly cost — the opposite default is a limiter that opens under its own errors."""
    import valuation.saas.ratelimit as rl
    real = rl._vendor_cost.__globals__.get("__builtins__")
    # Force the lazy import inside _vendor_cost to fail by pointing at a bad module path.
    orig = sys.modules.pop("valuation.web.dip", None)
    sys.modules["valuation.web.dip"] = None      # import returns None -> AttributeError
    try:
        cost = dict(rl.buckets_for("/api/dip", {}, {}))[VB]
    finally:
        if orig is not None:
            sys.modules["valuation.web.dip"] = orig
        else:
            sys.modules.pop("valuation.web.dip", None)
    assert real is not None
    assert cost == 25, f"an uncomputable fan-out was charged {cost}, not the ceiling"


# ============================== the cap actually bites =====================================
def test_the_budget_refuses_once_it_is_spent():
    """A bucket that is consulted is not a bucket that bites."""
    ratelimit.reset()
    limit = ratelimit.LIMITS[VB][0]
    ip = "198.51.100.4"
    assert ratelimit.check(ip, VB, cost=limit) is None, "the first full spend was refused"
    assert ratelimit.check(ip, VB, cost=1) is not None, "the budget never runs out"
    ratelimit.reset()


def test_one_expensive_request_spends_what_many_cheap_ones_would():
    """The equivalence that makes the denomination honest: 25 single valuations and one
    25-name rank must leave the caller in the same place."""
    limit = ratelimit.LIMITS[VB][0]

    def _remaining(ip):
        """How many more single valuations this IP can still afford."""
        n = 0
        while ratelimit.check(ip, VB, cost=1) is None:
            n += 1
        return n

    ratelimit.reset()
    a, b = "198.51.100.5", "198.51.100.6"
    for _ in range(25):                       # 25 single valuations
        assert ratelimit.check(a, VB, cost=1) is None
    assert ratelimit.check(b, VB, cost=25) is None       # ...against one 25-name rank
    left_a, left_b = _remaining(a), _remaining(b)
    assert left_a == left_b == limit - 25, \
        f"25 singles left {left_a} but one 25-name rank left {left_b} (limit {limit})"
    ratelimit.reset()


def test_a_request_that_cannot_afford_its_cost_is_refused_WHOLE():
    """Never partially admitted. Charging 12 of a 25-name request and then running all 25
    would be a limiter that reports a number it did not enforce."""
    ratelimit.reset()
    ip = "198.51.100.7"
    limit = ratelimit.LIMITS[VB][0]
    ratelimit.check(ip, VB, cost=limit - 5)
    assert ratelimit.check(ip, VB, cost=25) is not None, "an unaffordable request was admitted"
    # ...and it did not silently consume the 5 that were left.
    assert ratelimit.check(ip, VB, cost=5) is None, "a refused request still spent the budget"
    ratelimit.reset()


def test_a_cost_above_the_whole_limit_is_refused_without_dividing_by_nothing():
    """An empty window plus a cost larger than the entire budget has no first timestamp to
    measure a retry against. It must refuse cleanly rather than raise."""
    ratelimit.reset()
    retry = ratelimit.check("198.51.100.8", VB, cost=ratelimit.LIMITS[VB][0] + 1)
    assert isinstance(retry, int) and retry > 0
    ratelimit.reset()


def test_default_cost_is_one_so_every_existing_bucket_is_unchanged():
    """The regression guard on the `cost` parameter: per-request buckets must behave exactly
    as they did, or MA7 quietly re-tunes limits it was not asked to touch."""
    ratelimit.reset()
    ratelimit.LIMITS["__ma7_test__"] = (3, 60)
    try:
        ip = "198.51.100.9"
        assert [ratelimit.check(ip, "__ma7_test__") for _ in range(3)] == [None, None, None]
        assert ratelimit.check(ip, "__ma7_test__") is not None
    finally:
        ratelimit.LIMITS.pop("__ma7_test__", None)
        ratelimit.reset()


# ============================== the sweep ==================================================
def test_no_public_route_reaches_a_per_name_valuation_without_a_budget():
    """THE SWEEP MA7 ASKED FOR, done against the source rather than a remembered list.

    Any public route whose body reaches `value_ticker` or the `_get_or_compute` helper that
    wraps it must appear in `buckets_for`. This is what turned up `/api/dip`, which the audit
    itself did not name.
    """
    import re
    import pathlib
    from valuation.saas import surfaces
    src = (pathlib.Path(__file__).resolve().parent.parent
           / "valuation" / "web" / "app.py").read_text(encoding="utf-8")
    SPENDS = ("value_ticker(", "_get_or_compute")
    unbudgeted = []
    for block in re.split(r"(?=@app\.route\()", src):
        m = re.match(r'@app\.route\("([^"]+)"', block)
        if not m:
            continue
        path = m.group(1)
        if "<" in path or not any(s in block for s in SPENDS):
            continue
        if surfaces.is_owner_only(path):        # owner-gated: not an anonymous spend lever
            continue
        if ratelimit.buckets_for(path, {}, {}):
            continue
        unbudgeted.append(path)
    assert not unbudgeted, (
        "public routes that valuate caller-supplied names with no budget: "
        f"{sorted(unbudgeted)} — add each to ratelimit.buckets_for with a cost")


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
    print(f"\n{passed}/{len(tests)} vendor-quota tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
