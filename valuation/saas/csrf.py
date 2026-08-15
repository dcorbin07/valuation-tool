"""CSRF protection for the cookie-authenticated HTML form POSTs.

SECURITY_AUDIT.md M2: /login, /register, /reset/<token>, /forgot, /account/alerts,
/billing/checkout and /billing/portal are all session-cookie form POSTs with no token, so
any page on the internet could submit them on a logged-in user's behalf -- silently
switching their alert preferences, or opening a Stripe portal/checkout session as them.

Standard-library only, matching models.py's "deliberately dependency-light" stance: this is
a per-session random token compared with hmac.compare_digest. It is the double-submit
pattern with the reference copy held server-side in the signed session cookie.

NOT protected, on purpose:
  /billing/webhook  -- Stripe posts it from outside any browser session, and it is already
                       authenticated by construct_event's signature check.
  /admin/*          -- authenticated by the X-Admin-Token header, which a cross-site form
                       cannot set. Header auth is not ambient the way a cookie is.
  /api/*            -- same reasoning where a token is required; the open endpoints change
                       no per-user state.
"""
from __future__ import annotations

import hmac
import secrets

from flask import request, session

FIELD = "_csrf"
_SESSION_KEY = "_csrf_token"

# Exact paths that must carry a token. /reset/<token> is prefix-matched below.
PROTECTED = {"/login", "/register", "/forgot", "/account/alerts",
             "/billing/checkout", "/billing/portal",
             # /preview (MA9) creates a session and calls session.clear() first, so an
             # unprotected cross-site POST could log a signed-in owner out of their own
             # account. SameSite=Lax does NOT close this: the cookie is simply not SENT on a
             # cross-site POST, so the route cannot see the existing uid to refuse it, while
             # the response's own Set-Cookie still replaces the victim's session. The token
             # closes it because the attacker can neither read nor send it.
             "/preview"}


def token() -> str:
    """The caller's CSRF token, minting one into the session on first use.

    Called from the template context processor, so simply rendering any page with a form
    establishes the token -- including /login and /register, where the visitor has no
    account yet and therefore no other reason to have a session.
    """
    t = session.get(_SESSION_KEY)
    if not t:
        t = secrets.token_urlsafe(32)
        session[_SESSION_KEY] = t
    return t


def needs_protection(path: str, method: str) -> bool:
    return method == "POST" and (path in PROTECTED or path.startswith("/reset/"))


def validate() -> bool:
    want = session.get(_SESSION_KEY)
    got = request.form.get(FIELD, "")
    if not want or not got:
        return False
    return hmac.compare_digest(str(want), str(got))
