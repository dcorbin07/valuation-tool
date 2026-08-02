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

from flask import request, render_template, redirect, jsonify, g

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

    def _fire_alerts(intraday_store):
        """Send screaming-buy alerts after an intraday refresh (never blocks it)."""
        try:
            from . import notify
            return notify.run_alerts(cfg, intraday_store, store)
        except Exception:
            return {"new": 0}

    auth.register(app, store, cfg)
    billing.register(app, store, cfg)

    @app.context_processor
    def _inject():
        u = auth.current_user(store)
        eff = gating._active(u) if u else "free"
        return {"user": u, "eff_tier": eff, "feats": gating.features(eff),
                "open_access": cfg.open_access,
                "billing_enabled": cfg.billing_enabled,
                # Whether to show signup / pricing surfaces at all. Login is NOT gated by
                # this — existing accounts must still be able to sign in.
                "signup_enabled": cfg.signup_enabled,
                "stripe_pk": cfg.stripe_publishable_key,
                "beta_mode": cfg.beta_mode,
                "is_demo": bool(u and u.get("is_demo"))}

    # ---- Options outcome API (the Cowork/Robinhood filler) ------------------------------
    # Real fills and contract marks live behind the broker connector, which this web app
    # cannot reach. So the app LOGS alerts and exposes two endpoints for an external job to
    # read the work list and write outcomes back. Guarded by the same X-Admin-Token as the
    # learning hook rather than a session: the caller is a scheduled process, not a browser,
    # and these write to the record the scorecard is computed from.
    def _admin_ok():
        return bool(cfg.admin_token) and request.headers.get("X-Admin-Token") == cfg.admin_token

    @app.route("/api/option-alerts/open")
    def api_option_alerts_open():
        """Alerts still awaiting an outcome — the filler's work list."""
        if not _admin_ok():
            return jsonify({"error": "unauthorized"}), 401
        from ..edge.options_tracker import open_alerts
        from ..screener.store import Store
        try:
            limit = min(int(request.args.get("limit", 500)), 2000)
        except (TypeError, ValueError):
            limit = 500
        # NOTE: `store` in this factory is the UserStore (accounts). option_alerts lives in
        # the SCREENER store — a different database entirely.
        rows = open_alerts(Store(), limit=limit)
        return jsonify({"n": len(rows), "alerts": rows})

    @app.route("/api/option-alerts/outcome", methods=["POST"])
    def api_option_alerts_outcome():
        """Write a realized contract outcome back. Accepts one object or a list.

        P&L is NOT taken from the caller — record_outcome recomputes it from the stored entry
        premium, so the scorecard can never disagree with the prices it was logged against.
        """
        if not _admin_ok():
            return jsonify({"error": "unauthorized"}), 401
        from ..edge.options_tracker import record_outcome
        from ..screener.store import Store
        scr = Store()                     # screener DB, not the accounts UserStore
        body = request.get_json(silent=True)
        items = body if isinstance(body, list) else [body or {}]
        if len(items) > 500:
            return jsonify({"error": "too many outcomes in one call (max 500)"}), 400
        written, failed = 0, []
        for it in items:
            it = it or {}
            ok = record_outcome(
                scr, alert_id=it.get("alert_id"), occ=it.get("occ_symbol"),
                alert_ts=it.get("alert_ts"), ticker=it.get("ticker"),
                exit_premium=it.get("exit_premium"), exit_ts=it.get("exit_ts"),
                exit_reason=it.get("exit_reason"), contracts=it.get("contracts", 1))
            if ok:
                written += 1
            else:
                # An unmatched or already-closed alert is reported, not silently dropped —
                # the filler needs to know its write did not land.
                failed.append({k: it.get(k) for k in ("alert_id", "ticker", "alert_ts",
                                                      "occ_symbol")})
        return jsonify({"written": written, "failed": len(failed), "failures": failed[:20]})

    @app.route("/admin/run-learning", methods=["POST"])
    def admin_run_learning():
        # Monthly self-learning: OOS-gated re-tune of the screener weights.
        if not cfg.admin_token or request.headers.get("X-Admin-Token") != cfg.admin_token:
            return jsonify({"error": "unauthorized"}), 401
        if not cfg.learn_enabled:
            return jsonify({"ok": False, "status": "learning disabled"})
        from ..edge.autolearn import run_learning
        from ..screener.store import Store
        try:
            store = Store()
            report = run_learning(cfg, store)
            try:                                    # per-number IC visibility (never tunes)
                from ..edge.diagnostics import run_number_diagnostics
                run_number_diagnostics(cfg, store)
            except Exception:
                pass
            _email_owner_learning(cfg, report)
            return jsonify(report)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    def _email_owner_learning(cfg, report):
        """Private monthly note to the owner(s) only — what the learner changed, if anything."""
        try:
            from .emailer import send_email, learning_digest_html
            owners = sorted(cfg.owner_email_set)
            if not owners:
                return
            changed = any(b.get("adopted") for b in (report.get("buckets") or {}).values())
            subject = ("🧠 Valquo self-learning — weights updated" if changed
                       else "🧠 Valquo self-learning — monthly check (no change)")
            html = learning_digest_html(report)
            for addr in owners:
                send_email(cfg, addr, subject, html)
        except Exception:
            pass          # email must never break the learning run

    @app.route("/admin/run-fundamental-backtest", methods=["POST"])
    def admin_run_fundamental_backtest():
        # Heavy: builds a point-in-time panel from the historical provider (Sharadar/WRDS)
        # and backtests + optimizes vs the S&P. Token-protected; result stored for the owner view.
        if not cfg.admin_token or request.headers.get("X-Admin-Token") != cfg.admin_token:
            return jsonify({"error": "unauthorized"}), 401
        try:
            from ..edge.data_providers import get_historical_provider
            from ..edge.fundamental_panel import run_backtests
            from ..screener import universe as U
            from ..screener.store import Store
            prov = get_historical_provider(cfg)
            limit = int(request.args.get("limit", cfg.backtest_universe_limit))
            # Prefer the provider's own survivorship-free universe (incl. delisted); else bundled.
            tickers = prov.universe(limit=limit) or list(U.bundled_tickers())[:limit]
            horizons = [int(x) for x in str(cfg.backtest_horizons).split(",") if x.strip()]
            hl = int(cfg.backtest_recency_halflife_years * 252)
            res = run_backtests(prov, tickers, horizons=horizons, rebalance_days=cfg.backtest_rebalance_days,
                                top_n=cfg.backtest_top_n, lookback_years=cfg.backtest_lookback_years,
                                recency_halflife_days=hl)
            try:
                import datetime as _dt
                res["computed_at"] = _dt.datetime.utcnow().isoformat()
                Store().set_meta("fundamental_backtest", res)
            except Exception:
                pass
            return jsonify(res)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/admin/adopt-backtest-weights", methods=["POST"])
    def admin_adopt_backtest_weights():
        # Promote the backtest's optimized weights into the LIVE tuner — but only a
        # weighting that beat the default out-of-sample (the same anti-overfit gate).
        if not cfg.admin_token or request.headers.get("X-Admin-Token") != cfg.admin_token:
            return jsonify({"error": "unauthorized"}), 401
        from ..screener.store import Store
        st = Store()
        res = st.get_meta("fundamental_backtest") or {}
        horizons = res.get("horizons") or {}
        H = request.args.get("horizon") or res.get("primary_horizon")
        h = horizons.get(str(H)) if H else None
        if not h or not h.get("accepted") or not h.get("optimized_weights"):
            return jsonify({"ok": False, "error": "No out-of-sample-accepted weighting to adopt for that horizon. "
                                                  "Run the backtest first; adopt only when it beat the default OOS."})
        weights = h["optimized_weights"]
        st.save_learned("established", weights,
                        {"source": "historical_backtest", "horizon": H, "out_sample_ic": h.get("out_sample_ic")},
                        True, f"Adopted from historical backtest (horizon {H}, OOS IC {h.get('out_sample_ic')}).")
        return jsonify({"ok": True, "adopted": weights, "horizon": H,
                        "note": "Live scorer now uses these as the starting weights; the monthly learner refines from here."})

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

    @app.route("/admin/run-intraday", methods=["POST"])
    def admin_run_intraday():
        # Token-protected intraday refresh — an every-N-minutes cron hits this so
        # the Signals feed is "always running" during market hours.
        if not cfg.admin_token or request.headers.get("X-Admin-Token") != cfg.admin_token:
            return jsonify({"error": "unauthorized"}), 401
        from ..intraday.scan import run_intraday
        from ..intraday.ai import explain_top
        from ..screener.store import Store
        st = Store()
        try:
            res = run_intraday(cfg, store=st, save=True)
            ai = explain_top(res["rows"], cfg, n=10)
            for tkr, txt in ai.items():
                st.update_intraday_ai(res["run_time"], tkr, txt)
            alerts = _fire_alerts(st)
            from . import tracker
            tracker.log_options(st, res["rows"], cfg.alert_min_score)
            return jsonify({"ok": True, "run_time": res["run_time"], "scored": res["scored"], "alerts": alerts})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/admin/ingest-snapshot", methods=["POST"])
    def admin_ingest_snapshot():
        # Free-tier bridge: a CI runner (GitHub Actions) does the heavy whole-market
        # scan where there's real RAM + internet, then POSTs the finished rows here.
        # The 512 MB web box only does a light DB write — it never runs the scan.
        if not cfg.admin_token or request.headers.get("X-Admin-Token") != cfg.admin_token:
            return jsonify({"error": "unauthorized"}), 401
        data = request.get_json(silent=True) or {}
        rows = data.get("rows") or []
        if not rows:
            return jsonify({"error": "no rows"}), 400
        import datetime as _dt
        from ..screener.store import Store
        scan_date = data.get("scan_date") or _dt.date.today().isoformat()
        try:
            st = Store()
            done_key = f"hot_processed_{scan_date}"
            already = bool(st.get_meta(done_key))       # idempotency: a backup run for a day already done
            st.save_snapshot(scan_date, rows, data.get("provider", "ci"), data.get("params") or {})
            if not already:                             # fire side-effects ONCE per scan_date only
                from . import tracker, notify
                tracker.log_hot(st, scan_date, rows, cfg)   # log top-10 + update the paper account
                try:
                    from ..screener.sectors import sector_attractiveness
                    notify.post_hot_digest(cfg, st, scan_date, rows, sector_attractiveness(rows))
                except Exception:
                    pass
                try:
                    st.set_meta(done_key, {"at": _dt.datetime.utcnow().isoformat(), "rows": len(rows)})
                except Exception:
                    pass
            return jsonify({"ok": True, "scan_date": scan_date, "rows": len(rows), "reprocessed": already})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/admin/ingest-intraday", methods=["POST"])
    def admin_ingest_intraday():
        # Same pattern for the Premium Signals feed (technical + options + AI).
        if not cfg.admin_token or request.headers.get("X-Admin-Token") != cfg.admin_token:
            return jsonify({"error": "unauthorized"}), 401
        data = request.get_json(silent=True) or {}
        rows = data.get("rows") or []
        if not rows:
            return jsonify({"error": "no rows"}), 400
        import datetime as _dt
        from ..screener.store import Store
        run_time = data.get("run_time") or _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        try:
            st = Store()
            st.save_intraday(run_time, rows, data.get("provider", "ci"))
            alerts = _fire_alerts(st)
            from . import tracker
            tracker.log_options(st, rows, cfg.alert_min_score)   # log screaming buys into the tracker
            return jsonify({"ok": True, "run_time": run_time, "rows": len(rows), "alerts": alerts})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/app")
    def dashboard():
        u = auth.current_user(store)
        if not u and not cfg.open_access:
            return redirect("/login?next=/app")
        u = u or {}                       # open access: anonymous visitors get the app
        is_owner = u.get("email", "").strip().lower() in cfg.owner_email_set
        # signed_in drives the Sign out control. Under open access `u` may be empty
        # (anonymous), and showing "Sign out" to someone who never signed in is wrong.
        return render_template("index.html", ai_enabled=cfg.ai_enabled,
                               ai_provider=cfg.resolved_ai_provider, is_owner=is_owner,
                               signed_in=bool(u), logout_url="/logout",
                               contact_email=cfg.contact_email,
                               feedback_url=cfg.resolved_feedback_url)

    @app.route("/pricing")
    def pricing():
        # No paid tier exists while the product is open and free, so the pricing page is
        # hidden too — a stale link or search result should not land on a plan comparison for
        # plans nobody can buy. Route-level for the same reason as /register: hiding the nav
        # link does not make the URL unreachable. Re-enable with OPEN_ACCESS=false or
        # FEATURE_BILLING=on; the template and Stripe wiring are untouched.
        if not cfg.signup_enabled:
            return redirect("/")
        return render_template("pricing.html", tiers=gating.TIER_FEATURES)

    @app.route("/admin/ingest-index-track", methods=["POST"])
    def admin_ingest_index_track():
        """Accept the Valquo Index's live forward track from the external tracker.

        The tracker runs on the Cowork side and writes to `data/`, which is gitignored — so
        without this endpoint the live-vs-backtested comparison would work on a laptop and be
        permanently empty in production. Body mirrors the tracker's own files:
            {"inception_date": ..., "benchmark": "SPY",
             "series": [{"date","valquo","spy","excess","n_priced"}, ...]}
        Percentages are cumulative-since-inception, in percent, exactly as the CSV holds them.
        """
        if not cfg.admin_token or request.headers.get("X-Admin-Token") != cfg.admin_token:
            return jsonify({"error": "unauthorized"}), 401
        data = request.get_json(silent=True) or {}
        series = data.get("series") or []
        if not isinstance(series, list) or not series:
            return jsonify({"error": "no series"}), 400
        from ..screener.store import Store
        from ..screener import index_track
        try:
            Store().set_meta(index_track.STORE_KEY, {
                "inception_date": data.get("inception_date"),
                "benchmark": data.get("benchmark") or "SPY",
                "scan_date": data.get("scan_date"),
                "series": series[-2000:],          # bounded; this is a daily series
            })
            return jsonify({"ok": True, "days": len(series)})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # /methodology is registered on the shared app object in web/app.py — the SaaS layer uses
    # the SAME Flask app (`app = tool_app` above), so declaring it again is a duplicate
    # endpoint and the process would refuse to start.
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
        return render_template("account.html", watchlist=store.watchlist(u["id"]),
                               alerts_on=bool(u.get("alerts_email_opt_in")))

    @app.route("/account/alerts", methods=["POST"])
    def account_alerts():
        u = auth.current_user(store)
        if not u:
            return redirect("/login?next=/account")
        store.set_alerts_opt_in(u["id"], bool(request.form.get("alerts")))
        return redirect("/account")

    @app.route("/alerts/unsubscribe/<token>")
    def alerts_unsub(token):
        from . import notify
        uid = notify.unsub_user_id(cfg, token)
        if uid is not None:
            store.set_alerts_opt_in(uid, False)
            return ("<div style='font-family:sans-serif;max-width:520px;margin:60px auto;text-align:center'>"
                    "<h2 style='color:#1f3864'>Unsubscribed</h2><p>You won't receive screaming-buy emails "
                    "anymore. You can re-enable them anytime in your account.</p>"
                    "<a href='/'>Back to the app</a></div>")
        return ("<div style='font-family:sans-serif;max-width:520px;margin:60px auto;text-align:center'>"
                "<h2>Invalid or expired link</h2></div>", 400)

    @app.before_request
    def _guard():
        path = request.path
        if path.startswith("/static/"):
            return None
        # Marketing landing for anonymous visitors at "/". Under open access the landing
        # page still shows (it explains what the tool is), but nothing behind it is
        # locked — /app renders for anonymous visitors too.
        if path == "/":
            if auth.current_user(store):
                return redirect("/app")
            return render_template("landing.html")
        # API gating.
        if path.startswith("/api/"):
            body = request.get_json(silent=True) or {}
            u = auth.current_user(store)
            # How many hot-stocks rows this tier may see (free 10 / pro 100 / premium 500).
            g.hotstocks_cap = gating.features(gating._active(u))["hotstocks_top"]
            blocked = gating.check_request(path, request.method, body, u, store)
            if blocked:
                payload, status = blocked
                return jsonify(payload), status
        return None

    return app


# For gunicorn: `gunicorn "valuation.saas.app_saas:app"`
app = create_saas_app()
