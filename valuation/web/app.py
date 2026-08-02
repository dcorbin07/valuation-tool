"""
Flask web dashboard — the user-facing tool.

Routes:
  GET  /                     the single-page dashboard
  POST /api/value            value one ticker -> full JSON result
  POST /api/rank             score many tickers -> ranked list (watchlist)
  GET  /api/export/excel     download the live Excel model
  GET  /api/export/pdf       download the PDF tearsheet
  GET  /api/health           config / status probe
"""
from __future__ import annotations

import io
import tempfile
import traceback

from flask import Flask, render_template, request, jsonify, send_file

from ..config import CONFIG
from ..engine.pipeline import value_ticker
from ..report import excel as excel_report
from ..report import pdf as pdf_report

app = Flask(__name__)

# Shown wherever the product outputs something that looks like a recommendation. Kept as one
# string so the Index, the signals feed and the methodology page cannot drift apart on what
# the product claims — the wording is the claim.
RISK_DISCLAIMER = (
    "Educational research tool — not investment advice, and not a recommendation to buy or "
    "sell any security. Backtested results are hypothetical, come from one 18-year dataset "
    "the model was also tuned on, and are not a promise about the future. The live forward "
    "track is real but short. You can lose money. Do your own research."
)

# In-memory cache of the last full result per ticker (local single-user tool),
# so exports match exactly what's on screen without re-fetching.
_LAST: dict = {}


def _parse_overrides(src: dict) -> dict:
    """Pull recognized numeric override keys from a request payload."""
    keys = ["start_growth", "target_margin", "terminal_growth", "n_years",
            "sales_to_capital", "tax_rate", "wacc", "beta", "erp", "risk_free"]
    out = {}
    for k in keys:
        v = src.get(k)
        if v is None or v == "":
            continue
        try:
            out[k] = float(v)
        except (TypeError, ValueError):
            continue
    return out


@app.context_processor
def _site_context():
    """Site-wide template vars (footer contact, feedback link, theme).

    Registered on the shared app object, so the SaaS blueprint inherits them too and a
    render site that forgets to pass one still gets a working link rather than an empty
    href. Explicit values passed to render_template() still take precedence.
    """
    return {"contact_email": CONFIG.contact_email,
            "feedback_url": CONFIG.resolved_feedback_url,
            "signed_in": False, "logout_url": "/logout"}


@app.route("/")
def index():
    # Standalone/local use = owner (no auth layer). The SaaS /app route overrides this.
    # signed_in=False here because standalone has no auth, so there's nothing to sign out of.
    return render_template("index.html",
                           ai_enabled=CONFIG.ai_enabled,
                           ai_provider=CONFIG.resolved_ai_provider, is_owner=True,
                           signed_in=False, logout_url="/logout",
                           contact_email=CONFIG.contact_email,
                           feedback_url=CONFIG.resolved_feedback_url)


@app.route("/methodology")
def methodology():
    """How it works — point-in-time, survivorship, costs, and the weaknesses."""
    return render_template("methodology.html", disclaimer=RISK_DISCLAIMER)


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "ai_enabled": CONFIG.ai_enabled,
                    "ai_provider": CONFIG.resolved_ai_provider,
                    "mc_trials": CONFIG.montecarlo_trials})


@app.route("/api/value", methods=["POST"])
def api_value():
    data = request.get_json(force=True) or {}
    ticker = (data.get("ticker") or "").strip().upper()
    if not ticker:
        return jsonify({"error": "No ticker provided."}), 400
    overrides = _parse_overrides(data)
    peers = data.get("peers") or None
    run_ai = bool(data.get("run_ai", False))
    try:
        result = value_ticker(ticker, CONFIG, overrides=overrides, peers=peers, run_ai=run_ai)
        _LAST[ticker] = result
        payload = result.to_dict()
        if result.base_fair_value is None:
            payload.setdefault("warnings", []).append(
                "Could not compute a per-share value (missing shares/price). "
                "Check the ticker symbol.")
        return jsonify(payload)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Valuation failed for {ticker}: {e}"}), 500


@app.route("/api/rank", methods=["POST"])
def api_rank():
    data = request.get_json(force=True) or {}
    tickers = [t.strip().upper() for t in (data.get("tickers") or []) if t.strip()]
    run_ai = bool(data.get("run_ai", False))
    rows = []
    for t in tickers[:25]:
        try:
            r = value_ticker(t, CONFIG, run_ai=run_ai, mc_trials=2000)
            _LAST[t] = r
            rows.append({
                "ticker": t, "name": r.company.name, "price": r.company.price,
                "fair_value": r.base_fair_value, "upside": r.upside,
                "score": r.score.score, "recommendation": r.score.recommendation,
                "regime": r.classification.regime, "confidence": r.score.confidence,
            })
        except Exception as e:
            rows.append({"ticker": t, "error": str(e)})
    rows.sort(key=lambda x: (x.get("score") is not None, x.get("score", -1)), reverse=True)
    return jsonify({"rows": rows})


def _get_or_compute(ticker: str):
    ticker = ticker.upper()
    if ticker in _LAST:
        return _LAST[ticker]
    r = value_ticker(ticker, CONFIG)
    _LAST[ticker] = r
    return r


@app.route("/api/export/excel")
def export_excel():
    ticker = (request.args.get("ticker") or "").strip().upper()
    if not ticker:
        return jsonify({"error": "No ticker"}), 400
    try:
        result = _get_or_compute(ticker)
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        excel_report.build_workbook(result, tmp.name)
        return send_file(tmp.name, as_attachment=True,
                         download_name=f"{ticker}_DCF_Model.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/export/pdf")
def export_pdf():
    ticker = (request.args.get("ticker") or "").strip().upper()
    if not ticker:
        return jsonify({"error": "No ticker"}), 400
    try:
        result = _get_or_compute(ticker)
        if result.ai is None:
            try:
                from ..ai.analyst import analyze
                result.ai = analyze(result, CONFIG)
            except Exception:
                pass
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        pdf_report.build_pdf(result, tmp.name)
        return send_file(tmp.name, as_attachment=True,
                         download_name=f"{ticker}_Valuation_Report.pdf",
                         mimetype="application/pdf")
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# =========================================================================== #
#  Screener / hot-stocks / backtest routes
# =========================================================================== #
def _store():
    from ..screener.store import Store
    return Store()


@app.route("/api/valquo-index")
def api_valquo_index():
    """The Valquo Index — the CONSTRUCTED TOP-SLICE of the same ranking Hot Stocks shows.

    Deliberately built from the SAME snapshot the Hot Stocks tab reads, so there is exactly one
    ranking in the product and the Index is a disciplined selection from it, not a second
    competing screen. `config` picks the validated construction:

        roth     top-25, ~2-month rebalance, no no-trade band   (tax-free: Sharpe-optimal)
        taxable  decile, quarterly, 20% band                    (after-tax-optimal)
    """
    from ..edge.valquo_index import build_index
    from ..screener import settings as S
    name = (request.args.get("config") or S.DEFAULT_BOOK_CONFIG or "roth").lower()
    cfg = (S.BOOK_CONFIGS or {}).get(name)
    if not cfg:
        return jsonify({"error": f"unknown config {name!r}",
                        "known": sorted(S.BOOK_CONFIGS or {})}), 400
    st = _store()
    scan_date = st.latest_scan_date()
    if not scan_date:
        return jsonify({"empty": True, "config": name,
                        "message": "No scan snapshot yet — the Index is built from the same "
                                   "ranking the Hot Stocks tab shows, so it appears once a "
                                   "scan has run."})
    rows = st.load_snapshot(scan_date)
    kw = {}
    if cfg.get("top_n"):
        kw["top_n"] = cfg["top_n"]
    if cfg.get("top_frac"):
        kw["top_decile"] = cfg["top_frac"]
    payload = build_index(rows, **kw)
    payload["config"] = {
        "name": name, "label": cfg.get("label"),
        "rebalance_days": cfg.get("rebalance_days"),
        "rebalance_months": (round(cfg["rebalance_days"] / 21.0, 1)
                             if cfg.get("rebalance_days") else None),
        "exit_frac": cfg.get("exit_frac"),
        "band_note": ("hold a position until it falls past this fraction; applied at rebalance "
                      "against the previous book, not in this snapshot"),
        "measured": cfg.get("measured")}
    payload["scan_date"] = scan_date
    payload["available_configs"] = sorted(S.BOOK_CONFIGS or {})
    payload["source_note"] = ("built from the same scan snapshot as the Hot Stocks ranking — "
                              "the Index is its disciplined top-slice, not a separate screen")
    # The scan silently stopped running for four days in July and the site kept serving the
    # last snapshot as if it were today's. Every scan-derived surface now dates itself.
    from ..screener.freshness import status as _freshness
    payload["freshness"] = _freshness(scan_date, label="book")
    payload["disclaimer"] = RISK_DISCLAIMER
    return jsonify(payload)


@app.route("/api/index-track")
def api_index_track():
    """The Valquo Index's LIVE forward track, beside the backtested figures.

    Deliberately two separate blocks with a `headline` field naming which one may lead. The
    live track is the only non-backtested evidence the product has, and it is also brand new
    — so it is shown from day one for transparency but cannot become the headline until it
    has enough history to mean anything.
    """
    from ..screener import index_track
    from ..screener import settings as S
    name = (request.args.get("config") or S.DEFAULT_BOOK_CONFIG or "roth").lower()
    try:
        out = index_track.summarize(name, store=_store())
    except Exception as e:
        return jsonify({"available": False, "error": str(e),
                        "note": "Live track unavailable."}), 200
    out["disclaimer"] = RISK_DISCLAIMER
    return jsonify(out)


@app.route("/api/options-scorecard")
def api_options_scorecard():
    """Expectancy of the scream-buy options alerts, from REAL closed contract outcomes.

    Deliberately not a "success rate": for a payoff this asymmetric, hit rate without win/loss
    size is uninformative. Outcomes are written back by the external Robinhood job, so early on
    this legitimately reports mostly-open alerts and near-empty statistics — which is the
    honest state, not a bug.
    """
    from ..edge.options_tracker import scorecard, tuning_candidates
    from ..screener.store import Store
    try:
        st = Store()
        sc = scorecard(st)
        sc["tuning"] = tuning_candidates(st)
        return jsonify(sc)
    except Exception as e:
        return jsonify({"error": str(e), "overall": {"n_closed": 0}, "n_open": 0}), 200


@app.route("/api/options-alerts")
def api_options_alerts():
    """Live scream-buy alerts: the real contract, its confidence, and a contract count.

    The contract comes from the broker chain via the SAME selector the backtest used, so what is
    shown here is the trade that was validated rather than a description of it. `confidence` is
    EXPECTANCY-confidence and carries its own disclaimer - the backtested hit rate is 37%, so a
    high level must never be rendered as "likely to win". `sizing` is a suggestion; nothing here
    is routed to a broker.

    Chain fetches cost several calls per name, so this is capped and defaults to the top few.
    """
    from ..edge.options_live import build_alerts, DEFAULT_RISK_BUDGET
    from ..intraday.providers import get_provider
    from ..saas.notify import screaming_buys_with_stats
    from ..screener.store import Store
    try:
        st = Store()
        rt = st.latest_intraday_time()
        if not rt:
            return jsonify({"empty": True, "message": "No intraday scan yet — hit Refresh."})
        picks, term_stats = screaming_buys_with_stats(st.load_intraday(rt),
                                                      CONFIG.alert_min_score)
        top = max(1, min(int(request.args.get("top", 5)), 15))
        budget = float(request.args.get("risk_budget",
                                        getattr(CONFIG, "options_risk_per_trade", None)
                                        or DEFAULT_RISK_BUDGET))
        with_chain = request.args.get("chain", "1") != "0"
        alerts, stats = build_alerts(picks[:top],
                                     provider=get_provider(CONFIG) if with_chain else None,
                                     risk_budget=budget)
        return jsonify({"run_time": rt, "alerts": alerts, "stats": stats,
                        "term_filter": term_stats, "risk_budget": budget,
                        "n_screaming": len(picks)})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e), "alerts": []}), 200


@app.route("/api/options-paper")
def api_options_paper():
    """Forward paper book vs the backtest reference it is actually comparable to.

    Reports the GATED late-half number (+12.88%) as the primary reference, not the +10.4%
    full-sample headline: the live book runs behind the term filter and cannot be judged against
    an unfiltered figure dominated by 2016-2020.
    """
    from ..edge.options_paper import paper_report
    from ..screener.store import Store
    try:
        return jsonify(paper_report(Store()))
    except Exception as e:
        return jsonify({"error": str(e), "n_closed": 0, "thin": True}), 200


@app.route("/api/hotstocks")
def api_hotstocks():
    """Read the latest cached scan snapshot + sector attractiveness (instant)."""
    from flask import g
    from ..screener.sectors import sector_attractiveness
    cap = getattr(g, "hotstocks_cap", 500)          # per-tier cap (set by the SaaS layer)
    top = min(int(request.args.get("top", 100)), cap)
    st = _store()
    scan_date = st.latest_scan_date()
    if not scan_date:
        return jsonify({"empty": True,
                        "message": "The daily hot list hasn't loaded into this site yet — it's generated "
                                   "automatically by the background scan and then shows here instantly. If it "
                                   "stays empty after a scan has run, the site needs a persistent disk to keep "
                                   "the results between restarts."})
    import json as _json
    rows = st.load_snapshot(scan_date, top=top)
    all_rows = st.load_snapshot(scan_date)
    # Every listed name gets a fair value. Only the top few carry a full DCF (too slow to
    # run on the whole list), so the rest get a peer-relative multiples estimate — computed
    # here rather than in the scan so it also fills in snapshots that were saved earlier.
    # Medians come from the FULL scan, not the displayed slice, so the peer group is stable.
    from ..screener.fairvalue import estimate_fair_values
    estimate_fair_values(rows, peer_rows=all_rows)
    scans = st.list_scans()
    meta = next((s for s in scans if s["scan_date"] == scan_date), {})
    try:
        params = _json.loads(meta.get("params") or "{}")
    except Exception:
        params = {}
    from ..screener.freshness import status as _freshness
    return jsonify({"scan_date": scan_date, "rows": rows,
                    "sectors": sector_attractiveness(all_rows),
                    "universe_size": meta.get("universe_size"), "scored": meta.get("scored"),
                    "provider": meta.get("provider"), "filtered": params.get("filtered"),
                    "health": params.get("health"),
                    "freshness": _freshness(scan_date, label="ranking"),
                    "disclaimer": RISK_DISCLAIMER,
                    "history": [s["scan_date"] for s in scans][:12]})


@app.route("/api/tickers")
def api_tickers():
    """Ticker typeahead for the Single-valuation box.

    Local-only and instant: matches against the latest scan snapshot (which carries real
    company names) and falls back to the bundled universe so it still works before any
    scan has run. No network call — this fires on every keystroke.
    """
    q = (request.args.get("q") or "").strip().upper()
    if not q:
        return jsonify({"results": []})
    limit = min(int(request.args.get("limit", 8) or 8), 25)

    seen, cands = set(), []
    try:
        for r in _store().load_snapshot() or []:
            t = (r.get("ticker") or "").upper()
            if t and t not in seen:
                seen.add(t)
                cands.append((t, r.get("name") or "", r.get("sector") or ""))
    except Exception:
        pass                                   # no snapshot yet — bundled list still works
    try:
        from ..screener.universe import bundled_sector_map
        for t, sector in bundled_sector_map().items():
            if t not in seen:
                seen.add(t)
                cands.append((t, "", sector))
    except Exception:
        pass

    # Rank: exact ticker, then ticker prefix, then name prefix, then anything containing q.
    def rank(c):
        t, name, _ = c
        n = name.upper()
        if t == q:
            return 0
        if t.startswith(q):
            return 1
        if n.startswith(q):
            return 2
        return 3

    hits = [c for c in cands if q in c[0] or q in c[1].upper()]
    hits.sort(key=lambda c: (rank(c), len(c[0]), c[0]))
    return jsonify({"results": [{"ticker": t, "name": n, "sector": s}
                                for t, n, s in hits[:limit]]})


_LAST_TRACK_REFRESH = [0.0]
_PAPER_BENCH = {}
_REGIME = {"data": None, "ts": 0.0}


@app.route("/api/regime")
def api_regime():
    """Market-context readout (NOT a stock factor): 10Y yield, VIX, S&P vs its 200-day.
    Cached ~1h. This is the honest use of a 'Buffett-indicator'-style gauge — it describes
    the whole market's weather; it can't rank one stock above another."""
    import time
    import datetime as _dt
    now = time.time()
    if _REGIME["data"] and now - _REGIME["ts"] < 3600:
        return jsonify(_REGIME["data"])
    out = {"as_of": _dt.date.today().isoformat()}
    try:
        from ..data import macro
        out["ten_year"] = round(macro.risk_free_rate(CONFIG)[0] * 100, 2)
    except Exception:
        out["ten_year"] = None
    try:
        import yfinance as yf
        v = yf.Ticker("^VIX").fast_info.get("lastPrice")
        out["vix"] = round(float(v), 1) if v else None
    except Exception:
        out["vix"] = None
    trend = None
    try:
        from ..screener.prices import get_history_df
        df = get_history_df("SPY", 260)
        if df is not None and len(df) > 200:
            closes = [float(x) for x in df["Close"].tolist()]
            ma200 = sum(closes[-200:]) / 200.0
            out["sp_above_200dma_pct"] = round((closes[-1] / ma200 - 1) * 100, 1)
            trend = closes[-1] > ma200
    except Exception:
        pass
    out["sp_uptrend"] = trend
    score = 0
    if out.get("vix") is not None:
        score += 1 if out["vix"] < 20 else (-1 if out["vix"] > 28 else 0)
    if trend is not None:
        score += 1 if trend else -1
    out["regime"] = "risk-on" if score > 0 else ("risk-off" if score < 0 else "neutral")
    _REGIME.update(data=out, ts=now)
    return jsonify(out)


def _compute_paper_bench(st, source="hot10"):
    """Paper account vs SPY over the same span (background; needs price history)."""
    try:
        import pandas as pd
        from ..screener.prices import close_series
        allp = st.all_positions(source)
        if not allp:
            return
        d, c = close_series("SPY", 1500)
        if not (d and c):
            return
        spy = pd.Series(c, index=pd.to_datetime(d))

        def at(date):
            i = spy.index.searchsorted(pd.to_datetime(date))
            return spy.iloc[min(i, len(spy) - 1)] if len(spy) else None

        rt = 2.0 * CONFIG.paper_cost_bps / 1e4          # charge the strategy leg realistic cost
        alphas = []
        for p in allp:
            if not p.get("exit_date"):
                continue
            b0, b1 = at(p["entry_date"]), at(p["exit_date"])
            e, x = p.get("entry_price"), p.get("exit_price")
            if b0 and b1 and b0 > 0 and e and x and e > 0:
                alphas.append((x / e - 1 - rt) - (b1 / b0 - 1))
        first = min(p["entry_date"] for p in allp)
        b_first = at(first)
        spy_all = float(spy.iloc[-1] / b_first - 1) if (b_first and b_first > 0) else None
        # Is the average alpha real, or noise? A simple t-stat on per-trade alpha vs 0.
        t_stat = None
        if len(alphas) >= 3:
            import statistics as _stats
            m = sum(alphas) / len(alphas)
            sd = _stats.stdev(alphas)
            if sd > 0:
                t_stat = m / (sd / (len(alphas) ** 0.5))
        _PAPER_BENCH[source] = {"avg_alpha": (sum(alphas) / len(alphas)) if alphas else None,
                                "n_alpha": len(alphas), "spy_all_time": spy_all, "since": first,
                                "t_stat": t_stat, "significant": (abs(t_stat) > 2.0) if t_stat is not None else None,
                                "net_of_costs": True}
    except Exception:
        pass


def _recent_track_picks(st, source, n=15):
    picks = sorted(st.all_track_picks(source), key=lambda p: p.get("run_date") or "", reverse=True)[:n]
    rets = {(r["run_date"], r["ticker"]): r for r in st.track_returns(source, 21)}
    out = []
    for p in picks:
        r = rets.get((p.get("run_date"), p.get("ticker")))
        out.append({"date": p.get("run_date"), "ticker": p.get("ticker"),
                    "ret_1m": (r["fwd_ret"] if r else None), "bench_1m": (r["bench_ret"] if r else None)})
    return out


def _maybe_refresh_track():
    """Refresh matured forward returns in the background, at most every 12h, so the
    page load stays instant while the record accrues."""
    import time
    import threading
    now = time.time()
    if now - _LAST_TRACK_REFRESH[0] < 12 * 3600:
        return
    _LAST_TRACK_REFRESH[0] = now

    def _work():
        from ..edge import track
        st = _store()
        for src in ("hot10", "options"):
            try:
                track.update_returns(st, src)
            except Exception:
                pass
        _compute_paper_bench(st, "hot10")
    threading.Thread(target=_work, daemon=True).start()


@app.route("/api/track")
def api_track():
    """Live forward track record: the top-10 hot stocks + screaming-buy options vs the S&P,
    plus the paper account (sell-logic positions)."""
    from ..edge import track, positions
    st = _store()
    _maybe_refresh_track()
    out = {}
    for source in ("hot10", "options"):
        out[source] = {"summary": track.summary(st, source),
                       "recent": _recent_track_picks(st, source)}
    try:
        snap = st.load_snapshot() or []
        pmap = {r.get("ticker"): r.get("price") for r in snap if r.get("price")}
        smap = {r.get("ticker"): r.get("hot_score") for r in snap}
        vmap = {r.get("ticker"): (r.get("extra") or {}).get("vol") for r in snap}
        paper = positions.paper_summary(st, "hot10", pmap, smap, max_weight=CONFIG.paper_max_weight,
                                        cost_bps=CONFIG.paper_cost_bps, vol_map=vmap)
        paper["bench"] = _PAPER_BENCH.get("hot10")
    except Exception:
        paper = {"summary": {}, "watching": [], "closed": []}
    return jsonify({"sources": out, "paper": paper,
                    "note": "Forward, survivorship-free record of real dated picks vs the S&P 500. Options "
                            "are tracked by the underlying's forward return (signal accuracy, not option "
                            "P&L). Educational only; past results don't predict future performance."})


@app.route("/api/edge/learning")
def api_edge_learning():
    """Owner-only (gated by the SaaS layer): current adopted weights + learning audit log."""
    from ..screener.store import Store
    from ..screener.screen import _effective_weights
    st = Store()
    est, spec = _effective_weights(st)
    return jsonify({"current": {"established": est, "speculative": spec},
                    "history": st.learning_history(24),
                    "number_ic": st.get_meta("number_ic"),
                    "fundamental_backtest": st.get_meta("fundamental_backtest")})


@app.route("/api/scan/run", methods=["POST"])
def api_scan_run():
    """Trigger a scan. Network-heavy; keep the universe modest from the web —
    use the CLI / weekly job for the whole market."""
    from ..screener.screen import run_scan
    data = request.get_json(force=True) or {}
    scope = data.get("scope", "bundled")
    limit = data.get("limit")
    run_dcf_top = int(data.get("run_dcf_top", 0))
    try:
        res = run_scan(scope=scope, limit=(int(limit) if limit else None), cfg=CONFIG,
                       store=_store(), run_dcf_top=run_dcf_top, save=True)
        return jsonify({"ok": True, "scan_date": res["scan_date"], "scored": res["scored"],
                        "universe_size": res["universe_size"], "provider": res.get("provider")})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/portfolio", methods=["POST"])
def api_portfolio():
    from ..screener.portfolio import build_portfolio
    data = request.get_json(force=True) or {}
    st = _store()
    rows = st.load_snapshot(top=int(data.get("pool", 40)))
    if not rows:
        return jsonify({"error": "No scan snapshot. Run a scan first."}), 400
    pf = build_portfolio(rows, n=int(data.get("n", 15)),
                         weighting=data.get("weighting", "score"),
                         max_sector_weight=float(data.get("max_sector_weight", 0.35)))
    return jsonify(pf)


@app.route("/api/backtest/run", methods=["POST"])
def api_backtest_run():
    from ..backtest.run import run_from_tickers, run_from_store
    data = request.get_json(force=True) or {}
    kw = dict(horizon_days=int(data.get("horizon_days", 21)),
              lookback_years=int(data.get("lookback_years", 5)),
              rebalance_days=int(data.get("rebalance_days", 21)),
              benchmark=data.get("benchmark", "SPY"),
              cost_bps=float(data.get("cost_bps", 5.0)))
    try:
        if data.get("source") == "custom" and data.get("tickers"):
            tickers = [t.strip().upper() for t in data["tickers"] if t.strip()]
            res = run_from_tickers(tickers, **kw)
        else:
            res = run_from_store(_store(), top=int(data.get("top", 50)), **kw)
        return jsonify(res)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/signals")
def api_signals():
    """Latest intraday buy-setup snapshot (fast read; the dashboard polls this)."""
    from ..screener.store import Store
    st = Store()
    rt = st.latest_intraday_time()
    if not rt:
        return jsonify({"empty": True, "message": "No intraday scan yet — hit Refresh. "
                        "Add a TRADIER_TOKEN for real-time; otherwise it uses free delayed data."})
    top = int(request.args.get("top", 40))
    # Intraday feed: a run_time is a timestamp, so freshness is measured off its DATE. An
    # options signal from three days ago is not a signal, it is a historical note.
    from ..screener.freshness import status as _freshness
    return jsonify({"run_time": rt, "rows": st.load_intraday(rt, top=top),
                    "freshness": _freshness(str(rt)[:10], label="signal feed"),
                    "disclaimer": RISK_DISCLAIMER})


@app.route("/api/signals/run", methods=["POST"])
def api_signals_run():
    """Trigger an intraday scan + AI reasoning for the top 10 (bounded cost)."""
    from ..intraday.scan import run_intraday
    from ..intraday.ai import explain_top
    from ..screener.store import Store
    data = request.get_json(silent=True) or {}
    st = Store()
    try:
        res = run_intraday(CONFIG, store=st, limit=int(data.get("limit", 60)),
                           with_options=bool(data.get("with_options", True)), save=True)
        ai = explain_top(res["rows"], CONFIG, n=10)
        for r in res["rows"]:
            if r["ticker"] in ai:
                st.update_intraday_ai(res["run_time"], r["ticker"], ai[r["ticker"]])
        return jsonify({"ok": True, "run_time": res["run_time"], "scored": res["scored"],
                        "universe": res["universe"], "provider": res["provider"]})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/edge/backtest", methods=["POST"])
def api_edge_backtest():
    from ..edge.lab import run_backtest
    d = request.get_json(silent=True) or {}
    try:
        return jsonify(run_backtest(strategy=d.get("strategy", "momentum"),
                                    hold_top=int(d.get("hold", 15)),
                                    rebalance_days=int(d.get("rebalance", 21)),
                                    limit=int(d.get("limit", 100))))
    except Exception as e:
        traceback.print_exc(); return jsonify({"error": str(e)}), 500


@app.route("/api/edge/optimize", methods=["POST"])
def api_edge_optimize():
    from ..edge.lab import run_optimize
    d = request.get_json(silent=True) or {}
    try:
        return jsonify(run_optimize(limit=int(d.get("limit", 100))))
    except Exception as e:
        traceback.print_exc(); return jsonify({"error": str(e)}), 500


@app.route("/api/edge/track", methods=["POST"])
def api_edge_track():
    from ..edge.lab import run_track
    d = request.get_json(silent=True) or {}
    try:
        return jsonify(run_track(source=d.get("source", "hot")))
    except Exception as e:
        traceback.print_exc(); return jsonify({"error": str(e)}), 500


def create_app():
    return app
