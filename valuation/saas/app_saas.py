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

import datetime as _dt
import hmac
import os

from flask import request, render_template, redirect, jsonify, g, abort, make_response

from ..config import CONFIG
from ..safe_error import safe_error
from ..web.app import app as tool_app
from ..web.query_params import clamp_int as _clamp_int   # MA50 — the one clamp
from .models import UserStore
from . import auth, billing, csrf, gating, index_book, private, ratelimit, surfaces

# NOTE: a PUBLIC_PATHS set used to sit here. It was never referenced anywhere — _guard
# implements a different and narrower policy — so it read like enforced access control
# while enforcing nothing (SECURITY_AUDIT.md L1). Deleted rather than wired in, because
# _guard is the real policy and two overlapping allowlists is how they drift apart.

_INSECURE_SECRET = "dev-insecure-change-me"


PLATFORM_ENV = ("RENDER", "DYNO", "KUBERNETES_SERVICE_HOST",
                "AWS_EXECUTION_ENV", "WEBSITE_INSTANCE_ID", "PRODUCTION")


def _looks_like_production(cfg) -> bool:
    """Are we actually deployed? Gates the SECRET_KEY hard-fail, Secure cookies and HSTS.

    Deliberately keyed on the HOSTING PLATFORM's own env vars (Render sets RENDER=true)
    plus an explicit PRODUCTION=1 escape hatch for anywhere else — NOT on PUBLIC_BASE_URL.
    An earlier version used the URL and was wrong: Don's laptop has a production
    PUBLIC_BASE_URL in .env, so every local run and every test looked like production and
    the app refused to boot. A false positive here is a dev box that will not start, and a
    security check that gets in the way on a laptop is a security check that gets deleted.
    Render is the real deployment target and sets RENDER, so the protection holds where it
    counts. Self-hosting elsewhere: set PRODUCTION=1.
    """
    if cfg.dev_mode:
        return False
    return any(os.environ.get(v) for v in PLATFORM_ENV)


def create_saas_app(cfg=CONFIG):
    app = tool_app
    if getattr(app, "_saas_ready", False):   # idempotent: wrap the tool app only once
        return app
    app._saas_ready = True

    # SECRET_KEY signs the session cookie AND the password-reset tokens AND the unsubscribe
    # tokens. Its default is a literal committed to this repo, so falling back to it means
    # anyone who can read the repo can forge a session for any uid and mint valid reset
    # tokens. render.yaml sets generateValue:true, so this is a fail-OPEN default rather
    # than a live breach — refuse to boot on it instead (SECURITY_AUDIT.md M3).
    if cfg.secret_key == _INSECURE_SECRET and _looks_like_production(cfg):
        raise RuntimeError(
            "SECRET_KEY is still the committed development default. It signs session "
            "cookies and password-reset tokens, so on a public host it lets anyone forge "
            "either. Set SECRET_KEY to a random value (render.yaml already does this via "
            "generateValue), or set DEV_MODE=1 if this really is a local box.")
    app.secret_key = cfg.secret_key

    # Session cookie hardening (SECURITY_AUDIT.md M2). None of these were set, so the
    # cookie had no SameSite protection and would ride over plain HTTP. Secure is tied to
    # the production check so local http://127.0.0.1 development still works.
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=_looks_like_production(cfg),
        PERMANENT_SESSION_LIFETIME=_dt.timedelta(days=30),
    )
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
                # public_access, not the raw open_access field: under private mode "open to
                # everyone" is not what is happening, and a template that renders "free and
                # open" copy on a locked-down personal tool is the exact misrepresentation
                # this change exists to remove.
                "open_access": cfg.public_access,
                "billing_enabled": cfg.billing_enabled,
                # Whether to show signup / pricing surfaces at all. Login is NOT gated by
                # this — existing accounts must still be able to sign in.
                "signup_enabled": cfg.signup_enabled,
                "stripe_pk": cfg.stripe_publishable_key,
                # Off under private mode: the strip is addressed to prospective users
                # ("everything unlocked, no sign-up needed") and there are none.
                "beta_mode": cfg.beta_banner_enabled,
                # Lets the shared chrome describe what this instance IS, rather than every
                # template having to reason about a combination of access flags.
                "private_mode": cfg.private_mode,
                # THE OWNER SPLIT, in one name every template can test. Performance claims and
                # live positions render only where this is true; everything else is public.
                # Injected here rather than passed per-route so a template that forgets it
                # shows LESS, never more — `{% if may_see_owner %}` around a block that is
                # never given the variable simply renders nothing.
                "may_see_owner": surfaces.may_see_owner_surfaces(u, cfg),
                # ...and whether they may CHANGE anything. Owner yes, demo preview no. A
                # trigger rendered to a session the API will refuse reads as a broken tool
                # rather than a read-only one, so every button that writes tests this
                # instead of `may_see_owner`.
                "may_act": surfaces.may_act(u, cfg),
                "owner_split": cfg.owner_split,
                # Shared chrome (footer, terms) needs these on every page, not just the two
                # routes that used to pass them by hand.
                "contact_email": cfg.contact_email,
                "feedback_url": cfg.resolved_feedback_url,
                # Every form template renders this into a hidden field; simply rendering a
                # page with a form is what establishes the token for anonymous visitors.
                "csrf_token": csrf.token(),
                "is_demo": bool(u and u.get("is_demo"))}

    # ---- Options outcome API (the Cowork/Robinhood filler) ------------------------------
    # Real fills and contract marks live behind the broker connector, which this web app
    # cannot reach. So the app LOGS alerts and exposes two endpoints for an external job to
    # read the work list and write outcomes back. Guarded by the same X-Admin-Token as the
    # learning hook rather than a session: the caller is a scheduled process, not a browser,
    # and these write to the record the scorecard is computed from.
    def _admin_ok():
        # compare_digest, not == : a plain string compare short-circuits on the first
        # differing byte and leaks the token's prefix through timing (M5). Note the
        # `bool(cfg.admin_token)` guard — an unset token must fail CLOSED, and that
        # behaviour is deliberate and load-bearing in all eight admin endpoints.
        supplied = request.headers.get("X-Admin-Token") or ""
        return bool(cfg.admin_token) and hmac.compare_digest(supplied, cfg.admin_token)

    def _admin_write_ok():
        """The gate on the two routes that can rewrite the LIVE scoring weights. [MA10]

        `/admin/run-learning` and `/admin/adopt-backtest-weights` are the entire blast radius
        of MA1 and MA3 — a scheduled caller changing the live composite, invisibly to the
        vintage contract. Every other admin route reads, triggers a scan, or posts a recap.
        Sharing one credential across both classes means the token that runs the daily scan is
        also the token that can re-tune the model.

        TWO STATES, AND THE SPLIT IS OFF UNTIL DON TURNS IT ON:
          * ADMIN_WRITE_TOKEN unset  -> delegates to `_admin_ok()`. Bit-identical to the
            behaviour before this function existed, so no cron breaks on deploy.
          * ADMIN_WRITE_TOKEN set    -> the caller must present THAT value. The ordinary
            ADMIN_TOKEN no longer opens these two routes, which is the point of the split.

        Accepted in either `X-Admin-Write-Token` or the existing `X-Admin-Token` header, so
        activating the split is a secret-value change in the two jobs that need it rather than
        a code change in the callers. `compare_digest` for the same timing reason as above,
        and the same fail-closed guard: an empty configured token can never match.
        """
        want = (cfg.admin_write_token or "").strip()
        if not want:
            return _admin_ok()
        supplied = (request.headers.get("X-Admin-Write-Token")
                    or request.headers.get("X-Admin-Token") or "")
        return hmac.compare_digest(supplied, want)

    @app.route("/api/option-alerts/open")
    def api_option_alerts_open():
        """Alerts still awaiting an outcome — the filler's work list."""
        if not _admin_ok():
            return jsonify({"error": "unauthorized"}), 401
        from ..edge.options_tracker import open_alerts
        from ..screener.store import Store
        # MA50 class: the try/except was here, the FLOOR was not, so `?limit=-1` survived.
        limit = _clamp_int(request.args.get("limit"), default=500, cap=2000)
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
        # MA10: this route WRITES LIVE WEIGHTS, so it takes the write gate, not the blanket
        # admin one. Inert until ADMIN_WRITE_TOKEN is set — see `_admin_write_ok`.
        if not _admin_write_ok():
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
            return jsonify({"error": safe_error(e)}), 500

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
        if not _admin_ok():
            return jsonify({"error": "unauthorized"}), 401
        try:
            from ..edge.data_providers import get_historical_provider
            from ..edge.fundamental_panel import run_backtests
            from ..screener import universe as U
            from ..screener.store import Store
            prov = get_historical_provider(cfg)
            # MA50 class, and the widest of them: an unclamped int that becomes a UNIVERSE
            # SIZE on a 512 MB box. A negative silently emptied the run; an absurd positive
            # is a CPU lever. Capped at the full Sharadar universe, which is the largest
            # number that means anything here.
            limit = _clamp_int(request.args.get("limit"),
                               default=cfg.backtest_universe_limit, cap=5000)
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
            return jsonify({"error": safe_error(e)}), 500

    @app.route("/admin/adopt-backtest-weights", methods=["POST"])
    def admin_adopt_backtest_weights():
        # Promote the backtest's optimized weights into the LIVE tuner — but only a
        # weighting that beat the default out-of-sample (the same anti-overfit gate).
        # MA10: the second of the two live-weight writers. Same gate as run-learning.
        if not _admin_write_ok():
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
        # MASTER AUDIT MA3. `h["accepted"]` comes from `_weighted_optimize` — a SINGLE 50/50 time
        # split. `CLAUDE.md`'s core-file section is explicit that `cpcv_validate` is THE AUTHORITY
        # for weights and that a CPCV rejection means keep the defaults rather than falling back
        # to walk-forward; this endpoint fell back to something weaker than walk-forward, and CPCV
        # rejects on every run the project has done (`adopt: false`, PBO 0.7333). It also wrote
        # ONLY the "established" bucket, so the two buckets could end up on different regimes with
        # nothing reporting the split. The refusal below is not this handler's own — it comes from
        # `save_learned`, the funnel both weight writers share, so neither can be fixed alone.
        from ..edge.weight_adoption import VintageRefusal, authorisation
        try:
            st.save_learned("established", weights,
                            {"source": "historical_backtest", "horizon": H,
                             "out_sample_ic": h.get("out_sample_ic"),
                             "gate": "single 50/50 split — NOT CPCV"},
                            True, f"Adopted from historical backtest (horizon {H}, OOS IC {h.get('out_sample_ic')}).")
        except VintageRefusal as e:
            # `safe_error`, not `str(e)` — the security suite forbids raw exception text in a
            # response and is right to: the refusal is a fixed string today, but nothing stops a
            # future `require()` from interpolating a path. The actionable detail is carried by
            # the structured `authorisation` block, which is built from the register and cannot
            # contain server state.
            return jsonify({"ok": False, "adopted": None, "error": safe_error(e),
                            "authorisation": authorisation("established"),
                            "would_have_adopted": weights, "horizon": H}), 403
        return jsonify({"ok": True, "adopted": weights, "horizon": H,
                        "note": "Live scorer now uses these as the starting weights; the monthly learner refines from here."})

    @app.route("/admin/learned-weight-status", methods=["GET"])
    def admin_learned_weight_status():
        """MASTER AUDIT MA1 step 5 — is anything overriding settings.WEIGHTS_* right now?

        READ-ONLY, and deliberately so. An adopted row written before the gate existed is a live
        vintage violation: it must be surfaced with its date, not repaired on the way past, or the
        record ends up saying the track was clean through a window in which it was not. The audit
        asked whether this could be answered without a SQL console on Render's disk; it could not,
        and now it can.
        """
        if not _admin_ok():
            return jsonify({"error": "unauthorized"}), 401
        try:
            from ..edge.weight_adoption import live_override_report
            from ..screener.store import Store
            return jsonify(live_override_report(Store()))
        except Exception as e:
            return jsonify({"error": safe_error(e)}), 500

    @app.route("/admin/proxy-shape", methods=["GET"])
    def admin_proxy_shape():
        """MASTER AUDIT MA8 — is the rate limiter bucketing visitors, or one proxy?

        READ-ONLY. `client_ip` takes the Nth X-Forwarded-For entry from the right, and N was
        never written down anywhere; the audit's point is that the code cannot tell whether it
        is behind one proxy or two. If it is two, every visitor shares a single bucket and the
        per-IP limiter is a global cap one scraper can exhaust for everyone — which, from the
        inside, is indistinguishable from the limiter working.

        The audit's own prescribed check was a deploy and a grep. This answers the same
        question from traffic the app is already serving. It reports COUNTS ONLY — no address
        is retained anywhere in this path.
        """
        if not _admin_ok():
            return jsonify({"error": "unauthorized"}), 401
        try:
            return jsonify(ratelimit.forwarded_shape())
        except Exception as e:
            return jsonify({"error": safe_error(e)}), 500

    @app.route("/admin/run-scan", methods=["POST"])
    def admin_run_scan():
        # Token-protected so an external cron (cron-job.org / Render Cron) can
        # refresh the weekly snapshot inside this service — no shared disk needed.
        if not _admin_ok():
            return jsonify({"error": "unauthorized"}), 401
        from .scan_worker import run_weekly
        try:
            return jsonify(run_weekly(cfg))
        except Exception as e:
            return jsonify({"error": safe_error(e)}), 500

    @app.route("/admin/run-intraday", methods=["POST"])
    def admin_run_intraday():
        # Token-protected intraday refresh — an every-N-minutes cron hits this so
        # the Signals feed is "always running" during market hours.
        if not _admin_ok():
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
            return jsonify({"error": safe_error(e)}), 500

    @app.route("/admin/run-paper-track", methods=["POST"])
    def admin_run_paper_track():
        """One day of the forward paper track (roadmap #12) — Tradier SANDBOX only.

        Runs HERE rather than on a CI runner because the alerts, the paper order state and the
        index holdings all live in this service's screener database on the persistent disk. A
        GitHub runner gets a fresh empty DB every time: it would find no alerts, submit
        nothing, and lose the state that makes the cycle idempotent.

        The broker refuses to construct on anything but the sandbox endpoint and the dedicated
        TRADIER_PAPER_TOKEN, so this route cannot reach a funded account even if misconfigured.
        Without those secrets it reports `configured: false` and does nothing — the endpoint
        existing is not the same as the track running.
        """
        if not _admin_ok():
            return jsonify({"error": "unauthorized"}), 401
        from ..edge import paper_track as PT
        from ..edge.paper_broker import NotSandboxError, PaperBroker
        from ..screener.market_session import session_state
        from ..screener.store import Store
        body = request.get_json(silent=True) or {}

        # Only run once the session has actually closed. The crons are pinned to a fixed UTC
        # time, but 4:00pm Eastern moves an hour against UTC twice a year — 20:45 UTC is
        # 4:45pm ET in summer and 3:45pm ET in winter. Without this the whole winter would
        # have been marked and entered mid-session, on intraday prices, with nothing in the
        # output looking wrong. Also skips weekends and market holidays, which have no close.
        # `force` is the manual escape hatch for testing; `dry_run` never needs it blocked.
        if not body.get("force"):
            sess = session_state()
            if not sess["ok"]:
                return jsonify({"ok": True, "configured": True, "skipped": True,
                                "session": sess}), 200
        try:
            broker = PaperBroker(cfg, dry_run=bool(body.get("dry_run")))
        except NotSandboxError as e:
            return jsonify({"ok": False, "configured": False, "reason": safe_error(e)}), 200
        st = Store()
        out = {"ok": True, "configured": True, "health": broker.health()}
        if not out["health"].get("ok"):
            return jsonify({**out, "ok": False}), 200
        try:
            out["options"] = PT.run_options_cycle(st, broker, cfg=cfg,
                                                  limit=int(body.get("limit", 25)))
        except Exception as e:
            out["options_error"] = f"{type(e).__name__}: {e}"
        # The index leg must not be able to take down the options leg, or a stale book file
        # would silently stop the options book being marked.
        try:
            import json as _json
            import os as _os
            path = body.get("book") or _os.path.join("data", "valquo_index.json")
            if _os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    book = _json.load(f)
            else:
                from ..edge.valquo_index import export
                book = export(store=st, path=path)
            out["seed"] = PT.seed_book(st, broker, book,
                                       place_equity=bool(body.get("place_equity")))
            out["index"] = PT.index_point(st, broker)
        except Exception as e:
            out["index_error"] = f"{type(e).__name__}: {e}"
        out["summary"] = PT.summary(st)
        return jsonify(out)

    @app.route("/admin/post-recap", methods=["POST"])
    def admin_post_recap():
        """Post the daily or weekly paper-track recap to Discord.

        Runs HERE for the same reason the paper track does: the alerts, the paper order state
        and the index holdings live in this service's screener database. A CI runner reading
        its own empty copy would post a perfectly formatted recap of nothing.

        Nothing here is computed — `recap` reads the tracked record and formats it. A missing
        DISCORD_WEBHOOK_URL, an already-posted day and a Discord outage all return 200 with a
        reason, because this is one optional notification in a cron family whose real job is
        the track itself.
        """
        if not _admin_ok():
            return jsonify({"error": "unauthorized"}), 401
        from ..saas import recap as RC
        from ..screener.market_session import session_state
        from ..screener.store import Store
        body = request.get_json(silent=True) or {}
        kind = str(body.get("kind") or "daily").lower()
        if kind not in RC.KINDS:
            return jsonify({"error": f"kind must be one of {list(RC.KINDS)}"}), 400

        # Same guard as the paper track, for the same DST reason: a recap posted before the
        # close would report a half-finished session as the day's result, and one posted on a
        # holiday would report yesterday's twice.
        if not body.get("force"):
            sess = session_state()
            if not sess["ok"]:
                return jsonify({"ok": True, "posted": False, "skipped": True, "kind": kind,
                                "session": sess}), 200
        try:
            out = RC.post(cfg, Store(), kind=kind, day=body.get("day"),
                          force=bool(body.get("force")))
            return jsonify({"ok": True, **out})
        except Exception as e:
            return jsonify({"ok": False, "error": safe_error(e)}), 500

    @app.route("/admin/export-track", methods=["GET", "POST"])
    def admin_export_track():
        """The forward track, in full, for backup. Read-only; writes and computes nothing.

        This service's persistent disk holds the ONLY copy of the forward record, and the
        record is the one dataset here that cannot be re-derived — see edge/track_export.py.
        Render cannot commit to git and GitHub Actions cannot read Render's disk, so the
        backup crosses the gap here: the weekly `track-backup` workflow GETs this with the
        admin token and commits the files it renders.

        GET as well as POST because it is a pure read and `curl` a URL is the whole client.
        Same X-Admin-Token as every other admin route — this returns the complete forward
        record, which is exactly the kind of thing that should not be world-readable, and
        under private mode nothing else is either.
        """
        if not _admin_ok():
            return jsonify({"error": "unauthorized"}), 401
        try:
            from ..edge.track_export import payload
            from ..screener.store import Store
            return jsonify({"ok": True, "export": payload(Store())})
        except Exception as e:
            return jsonify({"ok": False, "error": safe_error(e)}), 500

    @app.route("/admin/track-row", methods=["GET", "POST"])
    def admin_track_row():
        """Today's contract row for the bound Valquo Index track: the Index mark, the SPY
        mark and the date. THE ANSWER TO `PT-WRITER`.

        The recorder lane refused to write on 2026-08-10 because "the mechanism for
        retrieving daily closing prices ... is NOT DOCUMENTED IN THIS REPOSITORY", and
        would not guess at a vendor. `screener/index_mark.py` is that mechanism and this is
        its HTTP door, for a writer that runs off-box; `python -m scripts.track_row` is the
        same call for a writer that runs in the repo. Both delegate to the one function, so
        there is no second implementation to drift — the B7 split this project keeps paying
        for.

        GET COMPUTES AND RETURNS. POST?append=1 WRITES. The verb is the whole distinction
        and it is enforced, not conventional: `?append=1` on a GET is refused with a 405 and
        writes nothing. It used to write, which is the defect this split closes — a
        side-effecting GET on the one dataset here that cannot be re-derived is reachable by
        a retry, a prefetch, a proxy or a pasted link, and none of those is a decision to
        record a day.

        THE CONTRACT'S RULES BIND THE WRITE, AND THEY LIVE IN `index_mark.append_row(
        append_only=True)` RATHER THAN HERE. A gap stays a logged gap; no prior row is ever
        modified; a second POST for a date already recorded is a no-op that returns the row
        ON DISK, never the freshly computed one. Putting them in the library is what keeps
        the CLI and this door on one implementation — the B7 split this project keeps paying
        for — and it is also why this handler does no arithmetic and no file IO of its own.

        THE STATUS CODE CARRIES THE OUTCOME, because the caller is an unattended writer that
        must branch on it without parsing prose:

            201  a row was written
            200  the date was already recorded — no-op, `existing` is the row on disk
            409  refused: append-only. The date is at or before the last recorded row.
            422  refused: the mechanism declined to produce a row. Most often "the session
                 has not closed yet", which is the ordinary evening case, and also every
                 non-trading day, unreadable book, unpriceable benchmark and coverage miss.
            500  an unexpected exception, and only that.

        4xx RATHER THAN 5xx IS THE POINT, AND IT IS NOT A REVERSAL OF THE OLD RULE. The
        original handler returned refusals as 200 with the reason "a 5xx would tell a
        scheduler to retry something that is not broken" — which is right about 5xx and does
        not require 200. A 4xx says "this did not happen and retrying unchanged will not
        change that", which is exactly the signal wanted, while a 200 for a refusal makes
        "wrote" and "refused" indistinguishable from the status line alone.

        GET KEEPS ITS 200 ON A REFUSAL, deliberately, and the asymmetry is principled rather
        than legacy: a GET asks *what would today's row be* and "no row, because the session
        has not closed" is a complete and successful answer to that question. A POST asks for
        a write and must report whether the write happened.

        Same `X-Admin-Token` as every other admin route, and it inherits `/admin/` — no new
        entry in any posture allowlist, because this is a performance-record surface and
        those are owner-only across the board. Deliberately NOT `_admin_write_ok()`: MA10's
        split guards the two routes that can re-tune the live composite, and recording a
        day's mark changes no model.
        """
        if not _admin_ok():
            return jsonify({"error": "unauthorized"}), 401
        try:
            from ..screener import index_mark
            body = request.get_json(silent=True) or {}
            date = request.args.get("date") or body.get("date")
            wants_append = bool(request.args.get("append") or body.get("append"))

            if wants_append and request.method != "POST":
                return jsonify({
                    "ok": False, "wrote": False,
                    "error": "append is POST-only",
                    "reason": ("writing the contract-bound series is POST-only. A GET may "
                               "compute and return the row; it may not record it."),
                }), 405

            # `refuse_before_close` is NOT a parameter of this door, on purpose. The recorded
            # day-1 row appears to carry an intraday mark under a closing-price column (see
            # PAPER_TRACK_CONTRACT.md section 7.2a) and that is the failure this refusal
            # exists to prevent, so there is no query string that can switch it off. A caller
            # that genuinely needs to backfill a closed day uses the CLI, in the repo, on
            # purpose.
            res = index_mark.contract_row(date)

            if not wants_append:
                return jsonify(res)

            if not res.get("ok"):
                # The mechanism declined. Nothing was written and nothing will be by retrying
                # this minute; the reason is already in `res`.
                return jsonify(res), 422

            res["append"] = index_mark.append_row(res["row"], append_only=True)
            ap = res["append"]
            if not ap.get("ok"):
                return jsonify(res), 409
            if ap.get("already_present"):
                # The row the caller asked for is the one already on disk, not the one just
                # computed — see append_row's docstring for why those can differ.
                res["row"] = ap.get("existing") or res["row"]
                res["reported_benchmark"] = _record_reported_benchmark(res["row"])
                return jsonify(res), 200
            res["reported_benchmark"] = _record_reported_benchmark(res["row"])
            return jsonify(res), 201
        except Exception as e:
            return jsonify({"ok": False, "error": safe_error(e)}), 500

    @app.route("/admin/fleet-cycle", methods=["GET", "POST"])
    def admin_fleet_cycle():
        """The daily cycle for the S3-I1 declared fleet. THE RUNNER'S DOOR.

        `PT-WRITER`'s lesson is the architecture and this is the same shape. A fleet cycle
        needs three things at once -- the Tradier sandbox token, network, and the fleet
        records store -- and only the Render service holds all three. Cowork has the book and
        no network; a GitHub runner has network and no book. So the runner is a cron POSTing
        this door, exactly as `track-row.yml` does for the bound Index track.

        GET COMPUTES AND RETURNS. POST?run=1 MAY WRITE. Same split as `/admin/track-row`, for
        the same reason: the fleet records are APPEND-ONLY and hash-chained, and a
        side-effecting GET on an append-only record is reachable by a retry, a prefetch, a
        proxy or a pasted link -- none of which is a decision to record a trading day.

        **WHAT IT HONESTLY DOES TODAY, and the handoff says this in bold: NOTHING FILLS.**
        Seventeen books are declared and their entry rules are FROZEN IN PROSE; not one is
        implemented as code, so there is nothing for a scheduler to execute. `cycle()` reports
        that as `ARMED_NO_ENTRY_RULE` and never as *"no candidates today"* -- a build gap and
        a market observation are different facts, and collapsing them is how a paper fleet
        reports a cycle that placed nothing as a cycle that found nothing. Scheduling this
        door before the rules exist is still worth doing: it dates the silence, it proves the
        path end to end, and it means the first implemented rule starts accruing immediately
        rather than after somebody remembers to wire a cron.

        Owner-only via the same `X-Admin-Token` as every other admin route, inheriting
        `/admin/` so no posture allowlist gains an entry. Deliberately NOT `_admin_write_ok()`
        -- `MA10`'s split guards the two routes that can re-tune the live composite, and a
        sandbox paper fill changes no model and touches no real money (`O11` binds).
        """
        if not _admin_ok():
            return jsonify({"error": "unauthorized"}), 401
        try:
            from ..edge import fleet
            body = request.get_json(silent=True) or {}
            wants_run = bool(request.args.get("run") or body.get("run"))
            only = request.args.get("book") or body.get("book")

            if wants_run and request.method != "POST":
                return jsonify({
                    "ok": False, "wrote": False, "error": "run is POST-only",
                    "reason": ("recording fills against append-only, hash-chained streams is "
                               "POST-only. A GET may compute the cycle and return it; it may "
                               "not record it."),
                }), 405

            # S3-I3 IS REGISTERED HERE, AND THE QUARANTINE OBJECTION THAT BLOCKED IT IS GONE
            # RATHER THAN OVERRIDDEN.
            #
            # This handler used to refuse to register it, because `MA59` caught that
            # `valuation/edge/assignment.py` imports `valuation/edge/dividends.py`, an ARCHIVED
            # study — *"reaching one from the live app means the product is running an
            # experiment."* That was correct at the time and the fix was NOT to silence it.
            #
            # `dividends.py` WAS MOVED OUT OF THE ARCHIVE on 2026-08-24, because MA59's own
            # criterion — *"modules whose only importer is a closed study's own script"* — had
            # stopped being true of it: S3-I3 delegates five primitives to it (B7), so it is
            # load-bearing for every short book. **It moved between two CHECKED lists, archived
            # (asserts UNREACHABLE) to load-bearing (asserts REACHABLE), so the guard now bites
            # in the opposite direction rather than not at all.** What stays closed is O21's
            # STUDY; what is reachable is its arithmetic.
            #
            # Registration is an explicit CALL, never an import side effect (r1's convention,
            # and the same one `fleet_books` follows below), so nothing is unblocked by a stray
            # import — this door is the composition root and says so.
            from ..edge import assignment as _s3i3
            _s3i3.register(fleet)
            # THE ENTRY RULES *ARE* REGISTERED HERE, AND THE CONTRAST WITH S3-I3 ABOVE IS THE
            # WHOLE POINT: THE QUARANTINE IS THE TEST, NOT A BLANKET BAN ON REGISTERING.
            #
            # `fleet_books` is registered because its dependency closure is quarantine-CLEAN,
            # measured rather than assumed -- `bearish`, `dip`, `name_percentile`,
            # `event_spine`, `catalyst_calendar`, `options_universe` and `paper_broker` reach
            # nothing on `MA59`'s archived list. `assignment` is NOT registered because its
            # closure reaches `dividends`, which is archived. Same rule, two answers.
            #
            # WITHOUT THIS CALL THE ARMING IS INVISIBLE WHERE IT MATTERS. Registration is an
            # explicit call and never an import side effect (`S3-I3`'s convention), so nothing
            # else was going to make it happen: the door would have gone on reporting
            # `entry_rules_implemented: 0` with the rules sitting built and unreachable, which
            # is a worse failure than not building them -- it looks like the work was not done.
            from ..edge import fleet_books
            from ..edge import fleet_gates
            res_reg = fleet_books.register_all()

            res = fleet.cycle(write=wants_run, books=[only] if only else None)
            res["entry_rules_registered"] = res_reg["registered"]

            # (D) THE RECORDERS. Four books gate on a series nothing wrote, and no amount of
            # coding produces one retroactively -- a book that needs two years of history
            # should be banking day 1 TODAY. They run on the WRITE path only: a dry-run GET
            # must stay side-effect free, which is the same split the verb already carries.
            from ..edge import fleet_history
            res["history"] = fleet_history.coverage()
            if wants_run:
                res["history_recorded"] = fleet_history.record_all()
            # Flat, to match `history`. A consumer reading two coverage blocks in one body
            # should not have to remember that one of them nests and the other does not.
            _g = fleet_gates.coverage()
            res["gates"] = _g.get("gates") or {}
            res["gates_ok"] = bool(_g.get("ok"))
            if not _g.get("ok"):
                res["gates_reason"] = _g.get("reason", "")
            res["assignment_provider_registered"] = fleet.assignment_provider() is not None
            res["assignment_note"] = (
                "S3-I3 registered: the six short books no longer refuse with "
                "SHORT_BOOK_WITHOUT_ASSIGNMENT. valuation.edge.dividends was moved from "
                "MA59's ARCHIVED list to its LOAD_BEARING list on 2026-08-24 -- the "
                "classification had gone stale, since S3-I3 delegates five primitives to it. "
                "O21's STUDY stays closed; its arithmetic is what is reachable."
                if res["assignment_provider_registered"] else
                "S3-I3 did NOT register in this process. Every short book will refuse with "
                "SHORT_BOOK_WITHOUT_ASSIGNMENT. This is a real fault, not the documented "
                "quarantine state, which was resolved on 2026-08-24.")
            # 200 on a dry run OR a run that legitimately produced nothing. A cycle that
            # placed no fill is not an error -- it is the ordinary case and, today, the only
            # case. The body's `breathing` flag and `note` carry that, so a scheduler can
            # alert on it without treating a quiet day as a failure.
            return jsonify(res), 200
        except Exception as e:
            return jsonify({"ok": False, "error": safe_error(e)}), 500

    def _record_reported_benchmark(bound_row: dict) -> dict:
        """PT-SPMO's sibling series, written from the row the BOUND door just settled on.

        IT RUNS AFTER THE BOUND WRITE AND CANNOT AFFECT IT. The status code, the body's `row`
        and every existing key are decided before this is called, and everything here is
        inside one `except Exception` that returns a reason instead of raising. A REPORTED
        benchmark that could fail the recording of the CONTRACT-BOUND one would be a strictly
        worse product than not having it, and `data/` on a fresh service is exactly the kind
        of place a second write finds a surprise.

        IT COPIES, IT DOES NOT RECOMPUTE. `bound_row` is whatever `append_row` settled on —
        the freshly written row on a 201, the row already on disk on a 200 — so the two files
        can never show two different Valquo numbers. That failure has happened here before,
        from two different books, and the recorded cure was one authority rather than better
        reconciliation.

        THE FIRST CALL BACKFILLS AND EVERY LATER ONE APPENDS, which is a real distinction and
        not an optimisation. A full write cannot preserve the byte prefix, so it happens once,
        when the file does not exist yet; from then on the sibling is append-only under
        `index_mark.append_row`'s own three refusals. On that first call today's row is
        already IN the bound CSV — the append above put it there — so the backfill picks it up
        with the rest and no separate write is needed.
        """
        try:
            from ..screener import index_mark, reported_benchmark as rb
            book = index_mark.load_book()
            inception = book.get("inception_date")
            if not inception:
                return {"ok": False, "wrote": False,
                        "reason": book.get("reason") or "no readable inception date"}
            if not os.path.exists(rb.sibling_path()):
                out = rb.backfill()
                out["mode"] = "backfill"
                return out
            out = rb.record(bound_row, inception, src=rb.SRC_COMPUTED)
            out["mode"] = "append"
            return out
        except Exception as e:                                   # noqa: BLE001
            return {"ok": False, "wrote": False, "mode": "error",
                    "reason": "the reported-benchmark sibling was not written: "
                              + safe_error(e)}

    @app.route("/admin/track-seed", methods=["POST"])
    def admin_track_seed():
        """Install the bound book and its recorded history on a service that has neither.

        WHY THIS EXISTS, AND IT IS A MEASUREMENT RATHER THAN A DESIGN PREFERENCE. On
        2026-08-18 the PT-WRITER Action reached `POST /admin/track-row?append=1` here,
        authenticated, and was refused: *"the book file /app/data/valquo_track.json is
        missing or unreadable"*. That is `index_mark.load_book` working exactly as written.
        `data/` is gitignored, so the book has never shipped with any deploy — it exists only
        on Don's machine. The write door was not the blocker; THE SERVICE HAS NOTHING TO MARK.

        AFTER A SUCCESSFUL SEED THE SERVICE COPY IS THE RECORD, and the local files become a
        stale backup. Nothing syncs them back, on purpose: this project has already published
        two different "Valquo Index vs SPY" numbers from two books, and the cure for that is
        ONE authority rather than better reconciliation between several.

        Body is JSON, mirroring the two files:

            {"book": {"inception_date": ..., "benchmark": "SPY", "positions": [...]},
             "history": "date,day_n,valquo_pct,...\r\n2026-07-31,1,..."}

        `history` may be omitted ONLY when the service already holds rows — seeding a book
        onto an empty series would let the first append start a fresh series at today's date,
        with every earlier day silently absent and a plausible `day_n` making the loss
        invisible. `index_mark.seed` refuses that, and this handler does not second-guess it.

        THE RULES LIVE IN `index_mark.seed`, NOT HERE, for the same reason the write door's
        rules live in `append_row`: one implementation per rule, so the HTTP door and any
        future caller cannot drift apart. This handler authenticates, hands over two values,
        and turns the outcome into a status code. It does no validation, no arithmetic and no
        file IO of its own, and a test pins that.

        THE STATUS CODE CARRIES THE OUTCOME, because the caller is a script that must branch
        without parsing prose:

            201  the service's copy changed — the book, the history, or both
            200  nothing changed; the service already held exactly this
            409  REFUSED: the upload disagrees with the recorded series. It rewrites a
                 recorded day, truncates it, reshapes its header, or cannot preserve the byte
                 prefix. An upload may EXTEND the record and may never rewrite it.
            422  REFUSED: the book is not the contract-bound Index (`conformance`), or a book
                 was offered with no history to stand on, or the upload is malformed.
            400  no book in the body at all.
            500  an unexpected exception, and only that.

        Same `X-Admin-Token` as every other admin route, and it inherits `/admin/`. NOT
        `_admin_write_ok()`: MA10's split guards the two routes that can re-tune the live
        composite, and installing a performance record changes no model. It is nonetheless
        the most destructive admin route here by a distance — which is why every one of its
        refusals is in the library, tested, and mutation-checked.
        """
        if not _admin_ok():
            return jsonify({"error": "unauthorized"}), 401
        try:
            from ..screener import index_mark
            body = request.get_json(silent=True) or {}
            book = body.get("book")
            if not isinstance(book, dict) or not book:
                return jsonify({"ok": False, "reason": "no book in the request body"}), 400
            history = body.get("history")
            if history is not None and not isinstance(history, str):
                return jsonify({"ok": False,
                                "reason": "history must be the CSV file's text"}), 422

            res = index_mark.seed(book, history)
            if not res.get("ok"):
                # 409 for "you disagree with the record", 422 for "this is not the Index" and
                # for a malformed upload. Both are 4xx: nothing happened, and retrying the same
                # bytes will not change that. A 5xx would tell a caller to retry something that
                # is not broken — the same reasoning the write door's docstring sets out.
                return jsonify(res), (409 if res.get("would_rewrite") else 422)
            return jsonify(res), (201 if res.get("changed") else 200)
        except Exception as e:
            return jsonify({"ok": False, "error": safe_error(e)}), 500

    @app.route("/admin/ingest-sample", methods=["POST"])
    def admin_ingest_sample():
        """The landing page's sample valuation, computed in CI and posted here.

        Computed out of band on purpose: a full valuation is a multi-second, network-heavy
        job, and running it inside the request that renders the landing page would make every
        first-time visitor wait — on the box least able to afford it. CI already has the RAM
        and the network, so it does the work and this only stores the result.
        """
        if not _admin_ok():
            return jsonify({"error": "unauthorized"}), 401
        data = request.get_json(silent=True) or {}
        # A sample with no ticker or no fair value would render an empty card, which is worse
        # than the static fallback. Refuse it rather than publish a broken hero.
        if not data.get("ticker") or data.get("fair_value") is None:
            return jsonify({"error": "a sample needs at least a ticker and a fair_value"}), 400
        try:
            from ..screener.store import Store
            from ..web import showcase
            showcase.save(Store(), data)
            return jsonify({"ok": True, "ticker": data["ticker"], "as_of": data.get("as_of")})
        except Exception as e:
            return jsonify({"error": safe_error(e)}), 500

    @app.route("/admin/ingest-snapshot", methods=["POST"])
    def admin_ingest_snapshot():
        # Free-tier bridge: a CI runner (GitHub Actions) does the heavy whole-market
        # scan where there's real RAM + internet, then POSTs the finished rows here.
        # The 512 MB web box only does a light DB write — it never runs the scan.
        if not _admin_ok():
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
            # PUBLISH THE INDEX BOOK — the cross-lane item Session 16 §7 named to this lane.
            #
            # `/admin/run-paper-track` reads `data/valquo_index.json` when it exists and SILENTLY
            # rebuilds from the store's latest scan when it does not; that rebuild is how the
            # engine came to record a 10-name book while the published Index held 86. Writing the
            # file here is what makes the engine record the RIGHT book instead of a truncated one.
            #
            # Deliberately OUTSIDE the `already` guard: the backup cron exists because GitHub
            # drops scheduled runs, and a day whose primary ingest published nothing must still
            # get a book. Publishing is idempotent (same rows -> same book) and refuses to write
            # a non-conforming one, so a second call is a no-op or a repair, never a corruption.
            #
            # Never fatal. The daily hot list must not fail to land because a book could not be
            # built — `publish` catches its own errors and reports them in the response.
            book = index_book.publish(st)
            return jsonify({"ok": True, "scan_date": scan_date, "rows": len(rows),
                            "reprocessed": already, "index_book": book})
        except Exception as e:
            return jsonify({"error": safe_error(e)}), 500

    @app.route("/admin/ingest-intraday", methods=["POST"])
    def admin_ingest_intraday():
        # Same pattern for the Premium Signals feed (technical + options + AI).
        if not _admin_ok():
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
            return jsonify({"error": safe_error(e)}), 500

    @app.route("/app")
    def dashboard():
        u = auth.current_user(store)
        # public_access rather than open_access: under private mode _guard has already
        # refused every non-owner, and this second check means a future caller that reaches
        # /app by another path still cannot get an anonymous render.
        if not u and not cfg.public_access:
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
        if not _admin_ok():
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
            return jsonify({"error": safe_error(e)}), 500

    # /methodology is registered on the shared app object in web/app.py — the SaaS layer uses
    # the SAME Flask app (`app = tool_app` above), so declaring it again is a duplicate
    # endpoint and the process would refuse to start.
    @app.route("/terms")
    def terms():
        return render_template("terms.html")

    @app.route("/privacy")
    def privacy():
        return render_template("privacy.html")

    @app.route(cfg.resolved_portfolio_path)
    def portfolio_page():
        """The unlisted portfolio page — the one route a stranger may read under private mode.

        STATIC BY CONSTRUCTION. It takes no arguments, reads no store, and its template makes
        no fetch: every number on it is a research statistic typed into the template from this
        repository's own handoffs, with its source named on the page. That is not a stylistic
        choice — it is what makes "no vendor data is exposed here" a property of the code
        rather than a promise, and `tests/test_private.py` pins it by asserting the page is
        byte-identical across requests and contains no `/api/` call.

        404, not a redirect, when the flag is off: a redirect confirms the path exists.
        """
        if not cfg.portfolio_page_enabled:
            abort(404)
        # MA9 — THE TOKEN IS NO LONGER RENDERED. This used to build
        # `demo_url = f"/demo/{token}"`, publishing DEMO_ACCESS_TOKEN in the HTML of an
        # anonymous page: anyone who viewed source held a permanent, shareable credential,
        # and after PUBLIC_FULL_VIEW=false that token is the only gate on every owner API.
        # The button now POSTs to /preview and the server sets the session (auth.py:
        # demo_grant_view). What reaches the template is a BOOLEAN, so there is no code path
        # by which the value can reach a response body.
        #
        # The token still decides whether the button exists, so clearing DEMO_ACCESS_TOKEN
        # remains the single off switch for the whole preview — unchanged from before.
        token = (cfg.demo_access_token or "").strip()
        demo_available = bool(token) and not cfg.private_mode
        # The research record (V4). Derived from the same config path, so rotating
        # PORTFOLIO_PATH moves the page and this link together. It is a PATH, not a number —
        # the page stays static by construction.
        # MB11 — the optionable partition, a REPORTED DIAGNOSTIC. Literals only: the module
        # takes no argument, reads no store and has no clock, so the page stays byte-identical
        # across requests exactly as this docstring promises. It is imported here rather than
        # at module scope for the same reason the other web helpers are — this blueprint is
        # built once and the import graph stays flat.
        from ..web import optionable_partition as _optionable
        resp = make_response(render_template("portfolio.html",
                                             contact_email=cfg.contact_email,
                                             demo_available=demo_available,
                                             optionable=_optionable.payload(),
                                             research_url=cfg.resolved_portfolio_path
                                             + "/research"))
        # Belt and braces with the <meta> tag and robots.txt. The header is the one of the
        # three that a crawler cannot miss and a scraper cannot ignore by not parsing HTML.
        resp.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive, nosnippet"
        return resp

    @app.route(cfg.resolved_portfolio_path + "/research")
    def research_record_page():
        """The public research record — every pre-registration and every verdict.  [V4]

        A CHILD OF /work, deliberately. It inherits that page's gate, its `noindex` header and
        its place under the blanket `Disallow: /` in robots.txt, and rotating `PORTFOLIO_PATH`
        moves both together — a second hard-coded path would be one more thing to forget.

        NO VENDOR DATA AND NO PERFORMANCE FIGURES. It reads two things, both from this
        repository: `RESEARCH_LOG.md` (through the same parse that produces the trial
        denominator `N`, so the page and the statistic cannot disagree) and the pre-registration
        documents on disk. `research_record.withhold()` strips anything shaped like a
        performance figure before it reaches the template, and `tests/test_research_page.py`
        asserts the rendered HTML contains none.

        404, not a redirect, when the flag is off — a redirect confirms the path exists.
        """
        if not cfg.portfolio_page_enabled:
            abort(404)
        from ..web import research_record
        resp = make_response(render_template(
            "research.html", work_url=cfg.resolved_portfolio_path, **research_record.record()))
        resp.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive, nosnippet"
        return resp

    @app.route("/robots.txt")
    def robots_txt():
        """Blanket exclusion, naming nothing.

        `Disallow: /` covers the portfolio page without listing it. Naming the path would be
        self-defeating: robots.txt is world-readable, so a file that says `Disallow: /work` is
        a public index of the URL it is trying to keep out of the public index.
        """
        resp = make_response("User-agent: *\nDisallow: /\n")
        resp.mimetype = "text/plain"
        return resp

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

    @app.after_request
    def _security_headers(resp):
        """L2 — there was no after_request hook in the codebase at all.

        No CSP here: the dashboard uses inline handlers and inline <style>, so a policy
        strict enough to be worth having would break the page, and a policy loose enough
        to not break it (`unsafe-inline`) buys nothing. Recorded as deferred in
        HANDOFF_security_fixes.md rather than shipped as security theatre.
        """
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if _looks_like_production(cfg):
            resp.headers.setdefault("Strict-Transport-Security",
                                    "max-age=31536000; includeSubDomains")
        return resp

    @app.before_request
    def _guard():
        path = request.path
        if path.startswith("/static/"):
            return None
        # CSRF on the cookie-authenticated form POSTs (M2). Checked first: a request that
        # cannot prove it came from our own page should not reach the handler at all.
        if csrf.needs_protection(path, request.method) and not csrf.validate():
            return render_template("csrf_error.html"), 400

        # ---- PRIVATE MODE ----------------------------------------------------------------
        # The licence boundary (personal use only — see saas/private.py). Deliberately the
        # FIRST access decision after CSRF and ahead of every branch below, because those
        # branches implement the public product: the landing page, the tier caps, the
        # rate-limit-per-visitor. Running any of them first would mean a stranger's request
        # had already been shaped by "what may a visitor see" logic before we asked the only
        # question that matters here, which is whether there is supposed to be a visitor.
        if private.enabled(cfg):
            denial = private.check(path, auth.current_user(store), cfg)
            if denial:
                if denial["kind"] == "json":
                    return jsonify(denial["payload"]), denial["status"]
                # A plain holding page, not the marketing landing: the landing page is a
                # pitch, and there is nothing to pitch. It carries a login link for the
                # owner and no scores, no track, no valuation, no vendor data at all.
                return render_template("private_landing.html",
                                       **denial["payload"]), denial["status"]
            if path == "/":
                # The owner is the only one who reaches this line under private mode.
                return redirect("/app")

        # ---- OWNER SPLIT -----------------------------------------------------------------
        # On a PUBLIC instance this is the liability boundary: performance claims, actionable
        # live picks and backtest/vendor internals stay owner-only while the analysis is open
        # to everyone (saas/surfaces.py names the reason and the vendor for each). It runs
        # after private mode and before gating for the same reason private mode runs first —
        # the tier logic below describes a commercial product, and "may this person read a
        # paper-account P&L" is not a tier question.
        #
        # ADMIN TOKEN BYPASSES IT, deliberately: the scan, intraday, paper-track and recap
        # crons hit these routes with a token and no session, and they are the reason the tool
        # exists. `_admin_ok` fails closed on an unset token.
        #
        # CALLED UNCONDITIONALLY (2026-08-07): `surfaces.check` reads the flag itself, and it
        # now carries one rule that is deliberately NOT flag-gated — a demo/preview session is
        # read-only whatever OWNER_SPLIT says. Testing `enabled(cfg)` here would have made
        # OWNER_SPLIT=false hand the recruiter link the scan trigger.
        if not _admin_ok():
            denial = surfaces.check(path, auth.current_user(store), cfg)
            if denial:
                if denial["kind"] == "json":
                    return jsonify(denial["payload"]), denial["status"]
                return render_template("owner_only.html",
                                       **denial["payload"]), denial["status"]

        # Marketing landing for anonymous visitors at "/". Under open access the landing
        # page still shows (it explains what the tool is), but nothing behind it is
        # locked — /app renders for anonymous visitors too.
        if path == "/":
            if auth.current_user(store):
                return redirect("/app")
            # Server-rendered proof: a real cached valuation, read straight from the screener
            # store. The live forward track is passed only to the owner — it is a paper-account
            # performance claim, and the landing page is the most public surface there is.
            # Wrapped because this is the FIRST thing a visitor sees — a missing sample must
            # cost us a section, never the page.
            try:
                from ..screener.store import Store as _ScreenerStore
                from ..web import showcase
                ctx = showcase.landing_context(
                    _ScreenerStore(),
                    with_track=surfaces.may_see_owner_surfaces(auth.current_user(store), cfg))
            except Exception:
                # Swallowed so the page still renders, but never silently: a landing that
                # quietly loses its only proof looks fine and is the whole problem.
                app.logger.exception("landing showcase failed; falling back to static copy")
                ctx = {}
            return render_template("landing.html", **ctx)
        # API gating.
        if path.startswith("/api/"):
            body = request.get_json(silent=True) or {}
            # Rate limit BEFORE anything expensive, and before gating, so a flood costs
            # us a dict lookup rather than an Anthropic call (SECURITY_AUDIT.md H1).
            # The admin token bypasses it: the cron jobs legitimately hit these on a
            # schedule and are already authenticated.
            # MA7: buckets_for, plural — a request can be scarce in two ways at once (an
            # /api/value with run_ai spends the FMP quota AND an Anthropic call), and it
            # carries a COST, because /api/rank and /api/dip fan out over up to 25 names.
            # request.args is passed because /api/dip takes its fan-out from the query string.
            buckets = ratelimit.buckets_for(path, body, request.args)
            # MA10: an admin caller used to skip this block outright. It now moves to a
            # separate, deliberately generous bucket instead — the crons stay comfortably
            # inside it, and a leaked token can no longer spend without bound. A CEILING
            # replaces an exemption; nothing legitimate should ever notice.
            if buckets and _admin_ok():
                buckets = ((ratelimit.ADMIN_BUCKET, 1),)
            for _bucket, _cost in buckets:
                # Note: an earlier bucket has already recorded its hit when a later one
                # refuses, so a 429 can cost the caller a little of the budget it cleared.
                # That errs TIGHT, which is the right direction for a spend limiter.
                retry = ratelimit.check(ratelimit.client_ip(request), _bucket, cost=_cost)
                if retry is not None:
                    return jsonify({
                        "error": "Rate limit reached for this endpoint. It runs live data "
                                 "and AI calls, so it's capped per visitor.",
                        "retry_after_seconds": retry,
                    }), 429, {"Retry-After": str(retry)}
            u = auth.current_user(store)
            # How many hot-stocks rows this tier may see (free 10 / pro 100 / premium 500).
            _feats = gating.features(gating._active(u))
            g.hotstocks_cap = _feats["hotstocks_top"]
            # The unified name view spans a public ranking AND two owner-only halves — the
            # specific option contract, and where the name sits in the constructed book and
            # the paper account. Rather than refuse the whole panel, each half is switched off
            # with a reason, so a visitor still gets the ranking they asked about.
            g.may_see_owner = surfaces.may_see_owner_surfaces(u, cfg)
            g.may_see_options = bool(_feats.get("intraday")) and g.may_see_owner
            blocked = gating.check_request(path, request.method, body, u, store)
            if blocked:
                payload, status = blocked
                return jsonify(payload), status
        return None

    return app


# For gunicorn: `gunicorn "valuation.saas.app_saas:app"`
app = create_saas_app()
