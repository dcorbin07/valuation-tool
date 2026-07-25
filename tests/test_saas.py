"""
SaaS + optimizer tests (offline, deterministic — temp DB, no network).
    python tests/test_saas.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.config import CONFIG
from valuation.saas.models import UserStore
from valuation.saas import gating
from valuation.saas.auth import _demo_user
from valuation.backtest.panel import build_synthetic_panel
from valuation.backtest.optimize import optimize_weights

# Most tests below exercise the REAL per-tier gating. Beta mode (a launch-time
# override that unlocks Premium for everyone) is turned off here so the tier
# assertions mean something; the beta/demo tests re-enable it locally.
CONFIG.beta_all_premium = False


def _store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return UserStore("sqlite:///" + path)


def test_user_create_and_verify():
    s = _store()
    u = s.create_user("a@b.com", "password123")
    assert u["tier"] == "free"
    assert s.verify("a@b.com", "password123")["id"] == u["id"]
    assert s.verify("a@b.com", "wrong") is None


def test_duplicate_and_validation():
    s = _store()
    s.create_user("a@b.com", "password123")
    for bad in [("a@b.com", "password123"), ("no-at", "password123"), ("x@y.com", "short")]:
        try:
            s.create_user(*bad); assert False, "should have raised"
        except ValueError:
            pass


def test_subscription_and_gating_tiers():
    s = _store()
    u = s.create_user("p@b.com", "password123")
    # free user blocked from paid features
    assert gating.check_request("/api/backtest/run", "POST", {}, u, s)[1] == 402
    assert gating.check_request("/api/scan/run", "POST", {"scope": "whole_market"}, u, s)[1] == 402
    assert gating.check_request("/api/scan/run", "POST", {"scope": "bundled"}, u, s) is None
    # upgrade to pro (active) -> unlocked
    s.set_subscription(u["id"], tier="pro", status="active")
    u = s.get_by_id(u["id"])
    assert gating.check_request("/api/backtest/run", "POST", {}, u, s) is None
    assert gating.check_request("/api/scan/run", "POST", {"scope": "whole_market"}, u, s) is None
    # premium-only optimizer still locked for pro
    assert gating.check_request("/api/optimize/run", "POST", {}, u, s)[1] == 402


def test_login_required_for_api():
    s = _store()
    assert gating.check_request("/api/backtest/run", "POST", {}, None, s)[1] == 401
    # public reads allowed anonymously
    assert gating.check_request("/api/hotstocks", "GET", {}, None, s) is None


def test_free_daily_valuation_limit():
    s = _store()
    u = s.create_user("v@b.com", "password123")
    codes = [gating.check_request("/api/value", "POST", {"ticker": "NKE"}, u, s) for _ in range(6)]
    assert all(c is None for c in codes[:5])       # 5/day allowed
    assert codes[5][1] == 402                       # 6th blocked


def test_optimizer_accepts_signal_rejects_noise():
    d = {"momentum": 0.5, "value": 0.5}
    sig = optimize_weights(build_synthetic_panel(140, 44, signal=0.1, seed=5),
                           ["momentum", "value"], step=0.1, default_weights=d)
    noise = optimize_weights(build_synthetic_panel(140, 44, signal=0.0, seed=6),
                             ["momentum", "value"], step=0.1, default_weights=d)
    assert sig["accepted"] is True
    assert noise["accepted"] is False and noise["recommended_weights"] == d


def test_beta_all_premium_unlocks_everyone():
    s = _store()
    u = s.create_user("beta@b.com", "password123")   # a plain free signup
    assert gating._active(u) == "free"               # beta off (module default)
    CONFIG.beta_all_premium = True
    try:
        assert gating._active(u) == "premium"        # now everyone is Premium
        assert gating.check_request("/api/backtest/run", "POST", {}, u, s) is None
        assert gating.check_request("/api/optimize/run", "POST", {}, u, s) is None
        # premium has no daily valuation cap — 6 in a row all allowed
        codes = [gating.check_request("/api/value", "POST", {"ticker": "NKE"}, u, s) for _ in range(6)]
        assert all(c is None for c in codes)
    finally:
        CONFIG.beta_all_premium = False


def test_demo_preview_is_premium_but_not_owner():
    s = _store()
    d = _demo_user()
    # Recruiter preview gets Premium even with beta OFF (link must outlive beta).
    assert CONFIG.beta_all_premium is False
    assert gating._active(d) == "premium"
    assert gating.check_request("/api/optimize/run", "POST", {}, d, s) is None
    # ...but the private Edge Lab stays owner-only — a demo visitor is blocked.
    assert gating.check_request("/api/edge/backtest", "POST", {}, d, s)[1] == 403


def test_master_link_route_and_banner():
    # End-to-end through the real Flask app: token gate + demo session + banner.
    CONFIG.demo_access_token = "sekret-xyz"
    from valuation.saas.app_saas import create_saas_app
    app = create_saas_app(CONFIG)
    app.config.update(TESTING=True)
    c = app.test_client()
    assert c.get("/demo/wrong").headers["Location"].endswith("/")             # → landing "/"
    assert c.get("/demo/sekret-xyz").headers["Location"].endswith("/app")     # → dashboard
    page = c.get("/app")
    assert page.status_code == 200
    assert b"Recruiter preview" in page.data          # demo-variant beta banner rendered
    CONFIG.demo_access_token = "preview"              # restore default


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
    print(f"\n{passed}/{len(tests)} SaaS tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
