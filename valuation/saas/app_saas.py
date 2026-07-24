"""
SaaS app factory — wraps the existing valuation dashboard with accounts, a
landing/pricing marketing front, subscription gating, and Stripe billing.

It reuses the whole tool app (all /api routes, the dashboard) and layers on:
  /            marketing landing page
  /app         the dashboard (login required; features gated by tier)
  /pricing     plans + Stripe checkout
  /account     subscription management
  /login /register /logout /billing/*
A single before_request enforces "landing for anonymous" and per-tier API gating.
"""
from __future__ import annotations

from flask import request, render_template, redirect, jsonify

from ..config import CONFIG
from ..web.app import app as tool_app
from .models import UserStore
from . import auth, billing, gating

PUBLIC_PATHS = {"/", "/login", "/register", "/logout", "/pricing", "/billing/webhook",
                "/api/health", "/favicon.ico", "/terms", "/privacy", "/forgot"}


def create_saas_app(cfg=CONFIG):
    app = tool_app
    if getattr(app, "_saas_ready", False):   # idempotent: wrap the tool app only once
        return app
    app._saas_ready = True
    app.secret_key = cfg.secret_key
    store = UserStore(cfg.database_url)

    auth.register(app, store, cfg)
    billing.register(app, store, cfg)

    @app.context_processor
    def _inject():
        u = auth.current_user(store)
        eff = gating._active(u) if u else "free"
        return {"user": u, "eff_tier": eff, "feats": gating.features(eff),
                "billing_enabled": cfg.billing_enabled,
                "stripe_pk": cfg.stripe_publishable_key}

    @app.route("/admin/run-scan", methods=["POST"])
    def admin_run_scan():
        # Token-protected so an external cron (cron-job.org / Render Cron) can
        # refresh the weekly snapshot inside this service — no shared disk needed.
        if not cfg.admin_token or request.headers.get("X-Admin-Token") != cfg.admin_token:
            return jsonify({"error": "unauthorized"}), 401
        from .scan_worker import run_weekly
        try:
            return jsonify(run_weekly(cfg))
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/app")
    def dashboard():
        if not auth.current_user(store):
            return redirect("/login?next=/app")
        return render_template("index.html", ai_enabled=cfg.ai_enabled,
                               ai_provider=cfg.resolved_ai_provider)

    @app.route("/pricing")
    def pricing():
        return render_template("pricing.html", tiers=gating.TIER_FEATURES)

    @app.route("/terms")
    def terms():
        return render_template("terms.html")

    @app.route("/privacy")
    def privacy():
        return render_template("privacy.html")

    @app.route("/account")
    def account():
        u = auth.current_user(store)
        if not u:
            return redirect("/login?next=/account")
        return render_template("account.html", watchlist=store.watchlist(u["id"]))

    @app.before_request
    def _guard():
        path = request.path
        if path.startswith("/static/"):
            return None
        # Marketing landing for anonymous visitors at "/".
        if path == "/":
            if auth.current_user(store):
                return redirect("/app")
            return render_template("landing.html")
        # API gating.
        if path.startswith("/api/"):
            body = request.get_json(silent=True) or {}
            u = auth.current_user(store)
            blocked = gating.check_request(path, request.method, body, u, store)
            if blocked:
                payload, status = blocked
                return jsonify(payload), status
        return None

    return app


# For gunicorn: `gunicorn "valuation.saas.app_saas:app"`
app = create_saas_app()
