"""
PUBLIC_FULL_VIEW — anonymous == demo, temporarily (offline, deterministic — no network).

    python tests/test_public_full_view.py

THE DECISION THIS PINS, recorded verbatim because the code cannot justify itself here.
Don, 2026-08-13:

    "/app must be 100% ungated - I know the risks - I've submitted applications with the
     non-master link; when I hear back we regate."

Applications went out carrying the plain `/app` URL rather than the recruiter master link, so
recruiters were arriving at the public half and seeing a fraction of the tool. The flag lifts
an ANONYMOUS visitor to the DEMO tier — the same read-only full view the `/work` button
already grants — and nothing more.

WHY BOTH STATES ARE PINNED, AND WHY NO POSTURE TEST WAS DELETED TO MAKE ROOM. The regate is
planned, not hypothetical: Don flips `PUBLIC_FULL_VIEW=false` when he hears back. A suite that
only pinned the ungated state would go green on the day of the regate while proving nothing
about it, and a suite that had DELETED the old assertions could not tell anyone what the
posture used to be. So every assertion below runs TWICE — once with the flag on, once with it
off — and `tests/test_public.py` is untouched and still pins the flag-off world in full.

THE SAFETY PROPERTY, which is the reason this is a new flag rather than `OWNER_SPLIT=false`:
turning the split off would also make `surfaces.may_act` true for everyone, handing anonymous
callers `/api/scan/run`, `/api/signals/run` and both Edge Lab runners — a free DoS lever on a
512 MB box that spends Don's FMP and Anthropic budget per request. This flag cannot do that,
and `test_the_flag_can_never_widen_what_may_be_CHANGED` reads the source to prove it rather
than trusting the behaviour of the cases that happen to be enumerated here.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402  — must precede the valuation imports

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import inspect  # noqa: E402
import re  # noqa: E402

from valuation.config import CONFIG, Config  # noqa: E402
from valuation.saas import surfaces as S  # noqa: E402

PASSED, FAILED = [], []


def check(name, fn):
    try:
        fn()
        PASSED.append(name)
        print(f"  PASS  {name}")
    except AssertionError as e:
        FAILED.append(name)
        print(f"  FAIL  {name}\n          {e}")


class _Cfg:
    """A cfg with the two flags that matter and nothing else — `surfaces` is a pure function."""

    def __init__(self, owner_split=True, public_full_view=False):
        self.owner_split = owner_split
        self.public_full_view = public_full_view
        self.owner_email_set = {"donniecorbin6@gmail.com"}


ANON = None
DEMO = {"is_demo": True, "id": 0}
OWNER = {"email": "donniecorbin6@gmail.com"}
STRANGER = {"email": "someone@example.com"}

# A read surface on each side of the boundary Don named.
OWNER_READS = ("/api/index-track", "/api/options-alerts", "/api/scream-track",
               "/api/edge/summary")


# ----------------------------------------------------------------------------------------
# 1. THE FLAG DOES WHAT IT SAYS — in BOTH states
# ----------------------------------------------------------------------------------------

def test_flag_OFF_reproduces_the_prior_split_exactly():
    """The regate target. This is the state Don returns to when he hears back."""
    cfg = _Cfg(public_full_view=False)
    assert S.may_see_owner_surfaces(ANON, cfg) is False
    for p in OWNER_READS:
        r = S.check(p, ANON, cfg)
        assert r is not None, f"{p} must refuse an anonymous reader with the flag off"
        assert r["status"] == 403, r


def test_flag_ON_lifts_anonymous_to_the_demo_tier():
    cfg = _Cfg(public_full_view=True)
    assert S.may_see_owner_surfaces(ANON, cfg) is True
    for p in OWNER_READS:
        assert S.check(p, ANON, cfg) is None, f"{p} must be readable signed out under the flag"


def test_the_lift_is_exactly_the_demo_tier_and_not_wider():
    """ANONYMOUS == DEMO. Not more than demo, which is the whole shape of the decision."""
    on = _Cfg(public_full_view=True)
    for p in sorted(S.OWNER_ONLY_PATHS) + ["/api/edge/anything", "/account", "/billing/checkout"]:
        assert S.check(p, ANON, on) == S.check(p, DEMO, on), (
            f"anonymous and demo disagree about {p}; the flag is meant to make them equal")


# ----------------------------------------------------------------------------------------
# 2. THE LINES THAT DO NOT MOVE UNDER ANY FLAG
# ----------------------------------------------------------------------------------------

def test_no_mutation_endpoint_moves_in_any_combination():
    """`may_act` is the other half of the split and the flag must never touch it."""
    for split in (True, False):
        for full in (True, False):
            cfg = _Cfg(owner_split=split, public_full_view=full)
            # The flag changes NOTHING about may_act, for anybody, ever.
            base = _Cfg(owner_split=split, public_full_view=False)
            for who in (ANON, DEMO, OWNER, STRANGER):
                assert S.may_act(who, cfg) is S.may_act(who, base), (
                    f"may_act moved under public_full_view={full}, split={split}")
            assert S.may_act(DEMO, cfg) is False, "a preview session may never act"


def test_the_flag_can_never_widen_what_may_be_CHANGED():
    """Read the SOURCE, not the enumerated cases.

    The behavioural test above can only cover the combinations someone thought to list. This
    asserts the structural property those cases are evidence for: `may_act` does not consult
    the flag at all, so no future edit can widen mutation by widening reading.
    """
    src = inspect.getsource(S.may_act)
    src = re.sub(r'"""[\s\S]*?"""', " ", src)          # the docstring DISCUSSES the flag
    assert "public_full_view" not in src, (
        "may_act now reads public_full_view — reading and writing must stay separate functions")


def test_the_triggers_and_the_account_stay_refused_to_a_stranger_under_the_flag():
    """Don's non-negotiables: no mutation endpoints, no admin/account surfaces."""
    on = _Cfg(public_full_view=True)
    for p in sorted(S.DEMO_DENIED_PATHS):
        r = S.check(p, ANON, on)
        assert r is not None, f"{p} must stay refused signed out under the flag"
        assert r["status"] == 403, r
        if p.startswith("/api/"):
            assert r["payload"].get("demo_read_only") is True, r


def test_every_trigger_don_named_is_actually_in_the_denied_set():
    """A guard that reads a registry cannot see an unregistered value — M3's finding.

    If a new runner is added and not listed, the test above passes by not looking at it. This
    asserts the set really does contain the four trigger classes Don's instruction names, so it
    cannot go quietly empty or lose an entry.
    """
    must = {"/api/scan/run", "/api/signals/run", "/api/backtest/run", "/api/edge/backtest",
            "/api/edge/optimize", "/api/edge/track", "/account", "/billing/checkout"}
    missing = must - set(S.DEMO_DENIED_PATHS)
    assert not missing, f"denied set lost entries: {sorted(missing)}"
    assert len(S.DEMO_DENIED_PATHS) >= 10, len(S.DEMO_DENIED_PATHS)


def test_the_owner_is_not_NARROWED_by_a_flag_that_exists_to_widen():
    """The demo-denied rule now also catches anonymous, so it must step around the owner.

    Without the `not is_owner(...)` clause, switching the flag on would have refused DON his
    own /account and billing pages — a flag about strangers quietly taking something from him.
    """
    on = _Cfg(public_full_view=True)
    for p in ("/account", "/account/alerts", "/billing/portal", "/api/scan/run"):
        assert S.check(p, OWNER, on) is None, f"the owner lost access to {p} under the flag"


def test_the_flag_is_not_a_licence_decision_and_the_vendor_hook_survives():
    """"I know the risks" answers for LIABILITY. It cannot answer for a vendor's licence.

    This grants the DEMO tier, so the route-by-route audit that cleared demo applies unchanged
    — but the place a future Sharadar-backed READ route must be listed has to still exist, or
    the next such route is published by default.
    """
    assert hasattr(S, "DEMO_DENIED_VENDOR_ROWS"), "the vendor-row hook was removed"
    assert S.is_demo_denied.__doc__ is not None or True
    # ...and it is consulted, not merely present.
    src = inspect.getsource(S.is_demo_denied)
    assert "DEMO_DENIED_VENDOR_ROWS" in src, "the vendor-row set is no longer consulted"


# ----------------------------------------------------------------------------------------
# 3. END TO END, ON THE LIVE CONFIG — with a control, because the app is idempotent
# ----------------------------------------------------------------------------------------

def _client():
    """The app the rest of the suite already built. `create_saas_app` is IDEMPOTENT — building
    a 'second app' with different flags returns the FIRST one, so a test that does that passes
    vacuously. Flip the live CONFIG instead."""
    from valuation.saas.app_saas import create_saas_app
    return create_saas_app(CONFIG)


def test_signed_out_app_gains_the_owner_reads_when_the_flag_is_on_AND_loses_them_when_off():
    """Both directions against the real app, with the flip as its own control.

    The control is the point: if flipping the flag changed nothing observable, both halves
    would agree and the test would pass while proving the flag inert.
    """
    app = _client()
    orig_split, orig_full = CONFIG.owner_split, CONFIG.public_full_view
    try:
        CONFIG.owner_split = True

        CONFIG.public_full_view = False
        with app.test_client() as c:
            off = {p: c.get(p).status_code for p in ("/api/index-track", "/api/scream-track")}

        CONFIG.public_full_view = True
        with app.test_client() as c:
            on = {p: c.get(p).status_code for p in ("/api/index-track", "/api/scream-track")}

        assert off != on, (
            "the flag changed nothing observable on the live app — it is inert, and every "
            "other assertion in this file is then about a pure function nobody calls")
        for p in off:
            assert off[p] == 403, f"{p} should refuse signed out with the flag off: {off[p]}"
            assert on[p] != 403, f"{p} should be readable signed out with the flag on: {on[p]}"
    finally:
        CONFIG.owner_split, CONFIG.public_full_view = orig_split, orig_full


def test_a_trigger_stays_refused_signed_out_even_with_the_flag_on():
    app = _client()
    orig = CONFIG.public_full_view
    try:
        CONFIG.public_full_view = True
        with app.test_client() as c:
            for p in ("/api/scan/run", "/api/signals/run", "/api/backtest/run"):
                r = c.post(p)
                assert r.status_code in (403, 405), (
                    f"{p} answered {r.status_code} to an anonymous POST under the flag")
    finally:
        CONFIG.public_full_view = orig


def test_the_disclaimers_and_labels_are_untouched_by_the_flag():
    """Don's instruction: every disclaimer / vintage / paper-account label stays exactly where
    it is — 'the surfaces carry their own caveats and that is why this is survivable'."""
    app = _client()
    orig = CONFIG.public_full_view
    try:
        CONFIG.public_full_view = True
        with app.test_client() as c:
            page = c.get("/app").get_data(as_text=True).lower()
        for phrase in ("not investment advice", "paper"):
            assert phrase in page, f"the signed-out full view dropped {phrase!r}"
    finally:
        CONFIG.public_full_view = orig


def test_the_ungated_view_shows_no_locked_door_banners():
    """Don, 2026-08-13: hide the section entirely rather than showing a locked-door notice —
    "the ungated view should read as complete, not as a view with holes labelled".

    Asserted against the RENDERED page with HTML COMMENTS STRIPPED. That is not a detail: the
    template carries four `owner-only` mentions and three are comments explaining WHY a block
    is gated. A naive substring scan over the raw HTML fails on those forever, so the next
    person deletes the test instead of the banner.
    """
    app = _client()
    orig = CONFIG.public_full_view
    try:
        CONFIG.public_full_view = True
        with app.test_client() as c:
            page = c.get("/app").get_data(as_text=True)
        visible = re.sub(r"<!--.*?-->", " ", page, flags=re.S)
        for phrase in ("Owner-only", "owner-only", "owner only",
                       "visitors see nothing here"):
            assert phrase.lower() not in visible.lower(), (
                f"a locked-door banner is still rendered to an anonymous visitor: {phrase!r}")
    finally:
        CONFIG.public_full_view = orig


def test_the_edge_lab_read_actually_answers_instead_of_painting_the_red_bar():
    """THE DEFECT THIS PINS, and it is a gap the first ungating left.

    `switchTab` auto-calls `edgeLearning()` for any session without the runner buttons, so the
    Edge Lab tab opens by fetching `/api/edge/learning`. PUBLIC_FULL_VIEW was wired into
    `surfaces.check` but NOT into `gating.check_request`, which tested `user.get("is_demo")` —
    false for an anonymous visitor. The request passed the surface split and was refused by the
    second gate, and the JS painted "Owner-only research tools." across the tab.

    Three gates stack on this path (`private`, `surfaces`, `gating`). Wiring a flag into one of
    them is not wiring it in. Both directions are pinned so the regate is covered too.
    """
    app = _client()
    orig = CONFIG.public_full_view
    try:
        CONFIG.public_full_view = True
        with app.test_client() as c:
            assert c.get("/api/edge/learning").status_code == 200, (
                "the Edge Lab read still refuses an anonymous visitor under the flag — the "
                "tab will open onto the red owner-only bar")
        CONFIG.public_full_view = False
        with app.test_client() as c:
            assert c.get("/api/edge/learning").status_code == 403, (
                "the regate must close the Edge Lab read again")
    finally:
        CONFIG.public_full_view = orig


def test_the_edge_lab_RUNNERS_never_open_no_matter_the_flag():
    """"The tools behind it stay owner-locked (they mutate records - that line never moves)."""
    app = _client()
    orig = CONFIG.public_full_view
    try:
        for state in (True, False):
            CONFIG.public_full_view = state
            with app.test_client() as c:
                for p in ("/api/edge/backtest", "/api/edge/optimize", "/api/edge/track"):
                    r = c.post(p, json={})
                    assert r.status_code in (403, 405), (
                        f"{p} answered {r.status_code} to anonymous with flag={state}")
    finally:
        CONFIG.public_full_view = orig


def test_the_gating_layers_own_scoping_holds_INDEPENDENTLY_of_the_surface_split():
    """Pin `gating.check_request` DIRECTLY, not through the app.

    WHY THIS EXISTS, and it is a mutation finding. Widening `gating`'s `demo_read` to every
    `/api/edge/` path, or dropping its method test, does NOT change what the app returns —
    because `surfaces.DEMO_DENIED_PATHS` refuses those routes in `_guard` BEFORE `gating` runs.
    Defence in depth working exactly as designed, and the end-to-end test passes.

    But that means the end-to-end test pins the OUTER layer, not this one. `gating`'s own
    comment calls itself "the second, independent line of that defence", and a second line that
    is only ever exercised through the first is not independent — it is unverified. If a future
    edit removed the `surfaces` entry, nothing would catch the widening here.

    So the two layers are pinned separately, which is the only way "independent" is a fact
    rather than a claim.
    """
    from valuation.saas import gating
    orig = CONFIG.public_full_view
    try:
        CONFIG.public_full_view = True
        # The ONE read the demo session gets, anonymous, with no store needed.
        assert gating.check_request("/api/edge/learning", "GET", {}, None, None) is None, (
            "the Edge Lab read is still blocked at the gating layer")
        # ...and nothing wider. These must stay blocked HERE, regardless of `surfaces`.
        for path, method in (("/api/edge/backtest", "POST"), ("/api/edge/optimize", "POST"),
                             ("/api/edge/track", "POST"), ("/api/edge/summary", "GET"),
                             ("/api/edge/learning", "POST")):
            r = gating.check_request(path, method, {}, None, None)
            assert r is not None and r[1] == 403, (
                f"gating stopped refusing {method} {path} to anonymous — the flag means "
                f"anonymous == demo, and the demo tier gets GET /api/edge/learning only")
        # With the flag off, even the one read closes again.
        CONFIG.public_full_view = False
        r = gating.check_request("/api/edge/learning", "GET", {}, None, None)
        assert r is not None and r[1] == 403, "the regate must close the read at this layer too"
    finally:
        CONFIG.public_full_view = orig


def test_the_owner_still_sees_the_owner_notices():
    """"Owner view unchanged." The fix hides a banner from VISITORS; it must not delete it.

    The not-started forward-track bar is a note to Don. Moving it from `may_see_owner` to
    `is_owner` is only correct if the owner still gets it — otherwise this "fix" quietly
    removed a piece of his dashboard.
    """
    from flask import render_template
    from valuation.web.app import app as tool_app
    hero = {"label": "X", "index": None}
    with tool_app.test_request_context("/"):
        owner = render_template("index.html", may_see_owner=True, may_act=True, is_owner=True,
                                ai_enabled=False, ai_provider="", hero=hero)
        visitor = render_template("index.html", may_see_owner=True, may_act=False,
                                  is_owner=False, ai_enabled=False, ai_provider="", hero=hero)
    assert "visitors see nothing here" in owner, "the owner lost his own not-started notice"
    assert "visitors see nothing here" not in visitor, "the visitor still sees the notice"
    # The runners are the owner's; the read the preview came for is not.
    assert "edgeBacktest()" in owner and "edgeBacktest()" not in visitor
    assert "edgeLearning()" in visitor, (
        "hiding the banner must not also hide the one thing a read-only session can do")


def test_the_config_default_is_the_SAFE_one_so_a_fork_is_never_ungated_by_accident():
    """Production opts in through render.yaml. The code default stays false, so a fresh
    instance, a test box or a fork is gated unless somebody deliberately says otherwise."""
    env = dict(os.environ)
    try:
        os.environ.pop("PUBLIC_FULL_VIEW", None)
        assert Config().public_full_view is False
        os.environ["PUBLIC_FULL_VIEW"] = "true"
        assert Config().public_full_view is True
        os.environ["PUBLIC_FULL_VIEW"] = "TRUE"
        assert Config().public_full_view is True, "the flag must not be case-sensitive"
        os.environ["PUBLIC_FULL_VIEW"] = "yes"
        assert Config().public_full_view is False, (
            "only an explicit 'true' ungates; anything else must fail closed")
    finally:
        os.environ.clear()
        os.environ.update(env)


def test_the_regate_is_one_flag_and_render_yaml_says_so():
    """The handoff promises Don a one-value regate. Assert the value is where it says it is,
    or the promise is prose."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    y = open(os.path.join(root, "render.yaml"), encoding="utf-8").read()
    assert "PUBLIC_FULL_VIEW" in y, "the flag is not in render.yaml, so there is nothing to flip"
    m = re.search(r"key:\s*PUBLIC_FULL_VIEW\s*\n\s*value:\s*\"(\w+)\"", y)
    assert m, "PUBLIC_FULL_VIEW has no literal value in render.yaml"
    assert m.group(1) == "true", f"expected the ungated value while this is live, got {m.group(1)}"
    assert "REGATE" in y.upper(), "render.yaml does not tell the next reader how to regate"


if __name__ == "__main__":
    print("PUBLIC_FULL_VIEW — anonymous == demo, both states pinned")
    for _n, _f in sorted(list(globals().items())):
        if _n.startswith("test_") and callable(_f):
            check(_n, _f)
    print(f"\n{len(PASSED)}/{len(PASSED) + len(FAILED)} public-full-view tests passed")
    sys.exit(1 if FAILED else 0)
