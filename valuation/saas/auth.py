"""Authentication — register/login/logout + password reset via signed email tokens."""
from __future__ import annotations

import hmac
import sys

from flask import request, session, redirect, render_template, make_response
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash

from . import ratelimit
from .emailer import send_status, NOT_CONFIGURED, SENT

_RESET_SALT = "pw-reset"
_RESET_MAX_AGE = 3600  # 1 hour

#: Rate-limit bucket for demo-session creation. Generous for a recruiter opening the link a
#: few times (and re-opening it after a logout), tight for a script. Registered in
#: `ratelimit.LIMITS` so the shared eviction and window logic applies unchanged.
DEMO_BUCKET = "demo:session"


def _noindex(resp):
    """Every /demo response, including the refusals, tells crawlers to stay away.

    Same header `/work` sends. The redirects matter as much as the successes: a 302 with a
    Location is exactly what a crawler follows, and the link now sits behind a button on a
    public page rather than only on a résumé.
    """
    resp = make_response(resp)
    resp.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive, nosnippet"
    return resp


def _demo_user():
    """Synthetic, no-database 'user' for the recruiter master-link preview.
    Shaped like a real users-table row so every template/route works, plus an
    is_demo flag that gating._active reads to grant Premium."""
    return {
        "id": 0, "email": "preview@valquo.demo", "password_hash": "",
        "tier": "premium", "subscription_status": "comped",
        "stripe_customer_id": None, "stripe_subscription_id": None,
        "created_at": "", "email_opt_in": 0, "is_demo": True,
    }


def current_user(store):
    # A demo/preview session has no DB row — hand back the synthetic Premium user.
    if session.get("demo"):
        return _demo_user()
    uid = session.get("uid")
    return store.get_by_id(uid) if uid else None


def _serializer(cfg):
    return URLSafeTimedSerializer(cfg.secret_key, salt=_RESET_SALT)


def register(app, store, cfg):
    @app.route("/register", methods=["GET", "POST"])
    def register_view():
        # Signup is hidden while the product is open and free (CONFIG.signup_enabled — see
        # config.py). Guarded at the ROUTE, not just in the templates: hiding a button leaves
        # the endpoint reachable to anyone with the URL, a bookmark or a stale link, and a
        # half-gated signup would create accounts the product no longer expects. Nothing is
        # deleted — flip OPEN_ACCESS=false (or FEATURE_BILLING=on) and this returns as-is.
        if not cfg.signup_enabled:
            return redirect("/app")
        if request.method == "POST":
            if not request.form.get("agree"):
                return render_template("register.html", error="Please accept the Terms and Privacy Policy."), 400
            # Owner privilege is granted by matching this typed string against OWNER_EMAILS
            # (gating.py) and there is NO email verification anywhere in the codebase — so
            # if no account with the owner address exists yet, the first stranger to type
            # it into signup inherits /api/edge/*: the learning history, the adopted
            # weights, the research bench. The owner address is not a secret; it is a
            # committed default in config.py. Owner accounts are provisioned deliberately,
            # never self-served. SECURITY_AUDIT.md H3.
            if request.form.get("email", "").strip().lower() in cfg.owner_email_set:
                return render_template(
                    "register.html",
                    error="That address can't be registered here. Contact support."), 400
            try:
                u = store.create_user(request.form.get("email", ""), request.form.get("password", ""))
                session.pop("demo", None)   # signing up from the preview takes over as a real account
                session["uid"] = u["id"]
                return redirect("/app")
            except ValueError as e:
                return render_template("register.html", error=str(e)), 400
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login_view():
        if request.method == "POST":
            u = store.verify(request.form.get("email", ""), request.form.get("password", ""))
            if u:
                session.pop("demo", None)   # a real login supersedes a preview session
                session["uid"] = u["id"]
                return redirect(request.args.get("next") or "/app")
            return render_template("login.html", error="Incorrect email or password."), 401
        return render_template("login.html")

    @app.route("/demo")
    @app.route("/demo/<token>")
    def demo_view(token=None):
        """Recruiter master-link: /demo/<token> (or /demo?key=<token>) opens an
        instant read-only preview of the FULL owner view with NO signup. Token must match
        DEMO_ACCESS_TOKEN. Independent of the beta flag, so this keeps working after you
        start charging.

        WHAT THE SESSION MAY DO is decided in `saas/surfaces.py`, not here: it reads every
        owner surface and may change nothing. This route only decides whether a session is
        created at all.

        THREE PIECES OF TOKEN HYGIENE live here, because the token is the only gate:
          * noindex on every response, so the link stays out of search even if it is pasted
            onto a page somewhere. `/work` — which now carries a button to it — already does
            the same three ways;
          * a per-IP rate limit on session CREATION, so a leaked or guessed token shows up
            as traffic and cannot be used to farm sessions in a loop; and
          * a log line per outcome, so "did the link travel?" is answerable from the Render
            logs rather than being invisible. The token itself is never logged.
        """
        # Private mode disables the recruiter link outright (prompt item 6, handled
        # conservatively). It is the one route whose entire purpose is to let a third party
        # read the tool without an account, which is precisely what the personal-use licence
        # terms do not permit — so it is refused here rather than merely hidden, and
        # `private.is_owner` separately refuses to treat any surviving demo cookie as the
        # owner. Turning PRIVATE_MODE off brings it back unchanged, token and all.
        if cfg.private_mode:
            return _noindex(redirect("/"))
        ip = ratelimit.client_ip(request)
        retry = ratelimit.check(ip, DEMO_BUCKET)
        if retry is not None:
            # Rate-limited BEFORE the token comparison, so the limit applies to guessing as
            # well as to farming valid sessions.
            print(f"[demo] rate-limited session creation from {ip}", file=sys.stderr)
            return _noindex(make_response(
                ("<div style='font-family:sans-serif;max-width:520px;margin:60px auto;"
                 "text-align:center'><h2>Too many preview sessions</h2><p>Try again in a "
                 "few minutes.</p></div>"), 429, {"Retry-After": str(retry)}))
        supplied = (token or request.args.get("key", "")).strip()
        want = (cfg.demo_access_token or "").strip()
        # `want` empty => /demo is off entirely (M4: there is no default token any more).
        # compare_digest for the same reason as the admin token.
        if want and hmac.compare_digest(supplied, want):
            session.clear()
            session["demo"] = True
            # Logged so a link that has travelled beyond the résumé is visible as traffic
            # rather than invisible. The token is NOT logged: a log is not a safe place for
            # a live credential (same rule as the password-reset route below).
            print(f"[demo] preview session opened from {ip}", file=sys.stderr)
            return _noindex(redirect("/app"))
        print(f"[demo] rejected preview attempt from {ip} "
              f"(token {'absent' if not want else 'mismatch'})", file=sys.stderr)
        return _noindex(redirect("/"))   # missing/incorrect token → marketing landing

    @app.route("/logout")
    def logout_view():
        session.clear()
        return redirect("/")

    @app.route("/forgot", methods=["GET", "POST"])
    def forgot_view():
        """Password reset request.

        Two properties this route MUST hold, both of which it used to violate:

        1. A reset link is NEVER placed in the HTTP response unless DEV_MODE is
           explicitly on AND no SMTP is configured at all. It used to be disclosed
           whenever `send_email` returned False — which is also what a merely *failing*
           production mail server returns, so anyone could POST the owner's address
           (a committed default) and be handed a valid token. See SECURITY_AUDIT.md C1.
        2. The response is byte-identical whether or not the account exists. The old
           code returned an extra block for real accounts, turning it into an account
           enumeration oracle.
        """
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            u = store.get_by_email(email)
            dev_link = None
            if u:
                token = _serializer(cfg).dumps(u["id"])
                link = f"{cfg.public_base_url}/reset/{token}"
                status = send_status(cfg, email, "Reset your password",
                                     f'<p>Reset your password (link valid 1 hour):</p>'
                                     f'<p><a href="{link}">{link}</a></p>')
                if status == NOT_CONFIGURED and cfg.dev_mode:
                    dev_link = link      # local development only, never inferred at runtime
                elif status != SENT:
                    # Log that it failed, NOT the token — logs are not a safe place for
                    # a live credential either (SECURITY_AUDIT.md M1/L3).
                    print("[auth] password-reset email could not be sent "
                          f"(smtp status: {status})", file=sys.stderr)
            # Identical response in every case: exists or not, sent or not.
            return render_template("forgot.html", sent=True, dev_link=dev_link)
        return render_template("forgot.html")

    @app.route("/reset/<token>", methods=["GET", "POST"])
    def reset_view(token):
        try:
            uid = _serializer(cfg).loads(token, max_age=_RESET_MAX_AGE)
        except (BadSignature, SignatureExpired):
            return render_template("reset.html", invalid=True), 400
        if request.method == "POST":
            pw = request.form.get("password", "")
            if len(pw) < 8:
                return render_template("reset.html", token=token, error="Password must be at least 8 characters."), 400
            with store._conn() as c:
                c.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(pw), uid))
            return redirect("/login")
        return render_template("reset.html", token=token)
