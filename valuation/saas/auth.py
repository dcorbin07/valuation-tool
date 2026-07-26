"""Authentication — register/login/logout + password reset via signed email tokens."""
from __future__ import annotations

from flask import request, session, redirect, render_template
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash

from .emailer import send_email

_RESET_SALT = "pw-reset"
_RESET_MAX_AGE = 3600  # 1 hour


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
        if request.method == "POST":
            if not request.form.get("agree"):
                return render_template("register.html", error="Please accept the Terms and Privacy Policy."), 400
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
        instant Premium preview with NO signup. Token must match DEMO_ACCESS_TOKEN.
        Independent of the beta flag, so this keeps working after you start charging."""
        supplied = (token or request.args.get("key", "")).strip()
        want = (cfg.demo_access_token or "").strip()
        if want and supplied == want:
            session.clear()
            session["demo"] = True
            return redirect("/app")
        return redirect("/")   # missing/incorrect token → marketing landing

    @app.route("/logout")
    def logout_view():
        session.clear()
        return redirect("/")

    @app.route("/forgot", methods=["GET", "POST"])
    def forgot_view():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            u = store.get_by_email(email)
            if u:
                token = _serializer(cfg).dumps(u["id"])
                link = f"{cfg.public_base_url}/reset/{token}"
                sent = send_email(cfg, email, "Reset your password",
                                  f'<p>Reset your password (link valid 1 hour):</p>'
                                  f'<p><a href="{link}">{link}</a></p>')
                # Don't reveal whether the email exists. In dev (no SMTP), surface the link.
                dev_link = None if sent else link
                return render_template("forgot.html", sent=True, dev_link=dev_link)
            return render_template("forgot.html", sent=True)  # same message regardless
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
