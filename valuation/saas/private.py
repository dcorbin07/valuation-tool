"""
Private mode — the request-level policy that makes Valquo a personal research tool.

WHY THIS EXISTS AS ITS OWN MODULE
---------------------------------
The licence posture (`Config.private_mode`, default true) is a compliance boundary, not a
product preference: ThetaData's Individual plan and Sharadar's individual terms permit
personal use and forbid redistribution or business use. "Personal use" is a claim about who
can READ the numbers, so it has to be enforced at the one place every read passes through,
and it has to be enforceable by reading a single function rather than by auditing a dozen
templates. `check()` below is that function; `app_saas._guard` calls it before anything else.

WHAT IT DOES NOT DO
-------------------
It does not replace the tier/gating system (`gating.py`), the admin-token check (`_admin_ok`)
or CSRF. It sits in FRONT of them and answers one question — "is the person making this
request the owner?" — then hands off. Under `PRIVATE_MODE=false` every function here becomes
a no-op and the public product behaves exactly as it did before, which is the whole point of
doing this as a flag.

THE ALLOWLIST IS THE SECURITY-CRITICAL PART
-------------------------------------------
Everything not named here is denied, so the failure mode of forgetting a route is "the owner
has to log in", never "a stranger reads the book". Each entry below states why it is open.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------------------
# Open to anyone, always. Four narrow categories, none of which serve vendor-derived data.
# ---------------------------------------------------------------------------------------

#: The platform health probe. `render.yaml` sets `healthCheckPath: /api/health`, so blocking
#: it would make Render mark every deploy unhealthy and roll it back — the lockdown would
#: take the service down rather than lock it. It returns three booleans about configuration
#: (ai enabled, provider name, monte-carlo trial count) and NO market data of any kind.
HEALTH_PATHS = frozenset({"/api/health"})

#: Signing in. Necessarily reachable while logged out, or the owner can never get in.
#: /forgot and /reset are the password-recovery pair and are already hardened (they return a
#: byte-identical response whether or not the account exists — SECURITY_AUDIT.md C1).
AUTH_PATHS = frozenset({"/login", "/logout", "/forgot"})
AUTH_PREFIXES = ("/reset/",)

#: Scheduled jobs. These carry `X-Admin-Token` and are checked by `_admin_ok()` in the route
#: itself — this allowlist lets the request REACH that check, it does not skip it. They must
#: stay open because the daily scan, the intraday refresh, the paper track and the Discord
#: recaps are all Render crons that hit HTTP routes with a token and no session, and they are
#: the reason the tool exists. An unset ADMIN_TOKEN still fails closed inside `_admin_ok`.
ADMIN_PREFIXES = ("/admin/", "/api/option-alerts/")

#: One-click unsubscribe from an alert email that was already sent. Signed-token, reveals
#: nothing, and a working unsubscribe link should not require signing in first.
UNSUB_PREFIX = "/alerts/unsubscribe/"

#: Static assets — the login page needs its stylesheet.
STATIC_PREFIX = "/static/"

#: robots.txt. A crawler never logs in, so a 401 here is a file the crawler cannot read — and
#: the file's entire job is to tell it to stay away. It is served to everyone and says
#: `Disallow: /` with no paths named, so it excludes the site without disclosing the portfolio
#: URL to anyone who reads it.
ROBOTS_PATHS = frozenset({"/robots.txt"})


def enabled(cfg) -> bool:
    """Is the lockdown on? The single read of the flag for policy purposes."""
    return bool(getattr(cfg, "private_mode", False))


def is_owner(user, cfg) -> bool:
    """Owner accounts only — a real, signed-in account whose address is in OWNER_EMAILS.

    A demo/preview session is deliberately NOT an owner even though `gating._active` grants it
    Premium: the recruiter master-link is exactly the "someone else reads the numbers" case
    private mode exists to close (prompt item 6). `/demo` is refused outright under private
    mode, and this is the second line of that defence in case a session cookie predates it.
    """
    if not user or user.get("is_demo"):
        return False
    return (user.get("email") or "").strip().lower() in cfg.owner_email_set


def always_open(path: str) -> bool:
    """Paths that stay reachable while logged out. See the module docstring for the rationale.

    UNCONDITIONAL, and deliberately not aware of any config: everything here is open on every
    instance. The portfolio page is NOT here — it is open only while its own flag is on, which
    is `portfolio_open()` below and a separate door on purpose.
    """
    return (path in HEALTH_PATHS
            or path in ROBOTS_PATHS
            or path in AUTH_PATHS
            or path.startswith(AUTH_PREFIXES)
            or path.startswith(ADMIN_PREFIXES)
            or path.startswith(UNSUB_PREFIX)
            or path.startswith(STATIC_PREFIX))


def portfolio_open(path: str, cfg) -> bool:
    """The one deliberate exception to the lockdown: the unlisted portfolio page.

    EXACT match on the configured path, never a prefix. A prefix match would open every route
    that happens to live below it, and the whole value of this function is that it can grant
    at most one URL. `resolved_portfolio_path` has already refused "/" and every reserved
    prefix, so the widest thing this can ever return true for is a single leaf page.

    Why this is a licence-safe hole while `/app` is not: the page is static prose and research
    statistics Don computed. It reads no store, calls no API and renders no vendor row, so a
    stranger loading it obtains nothing ThetaData or Sharadar licensed to him.
    """
    if not getattr(cfg, "portfolio_page_enabled", False):
        return False
    return path == cfg.resolved_portfolio_path


#: What an anonymous caller is told. Deliberately identical for "not signed in" and "signed in
#: as somebody else": the distinction is not information a stranger has any business having,
#: and a personal tool has nothing to explain to them.
_DENY_MESSAGE = ("Valquo is a private research tool for its owner's personal use. "
                 "It is not a product and is not available to other users.")


def check(path: str, user, cfg):
    """None to allow. Otherwise a dict describing the refusal, for the caller to render.

    Returns `{"kind": "json"|"page", "payload": ..., "status": int}`. The caller turns that
    into a response so this module stays free of Flask imports and can be unit-tested as a
    pure function — which is what makes "prove the lockdown holds" a cheap test rather than a
    browser session.
    """
    if not enabled(cfg):
        return None
    if always_open(path):
        return None
    if portfolio_open(path, cfg):
        return None
    if is_owner(user, cfg):
        return None
    if path.startswith("/api/"):
        return {"kind": "json", "status": 401,
                "payload": {"error": _DENY_MESSAGE, "private_mode": True,
                            "need_login": True}}
    return {"kind": "page", "status": 401, "payload": {"message": _DENY_MESSAGE}}
