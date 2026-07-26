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


@app.route("/")
def index():
    # Standalone/local use = owner (no auth layer). The SaaS /app route overrides this.
    return render_template("index.html",
                           ai_enabled=CONFIG.ai_enabled,
                           ai_provider=CONFIG.resolved_ai_provider, is_owner=True)


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
    scans = st.list_scans()
    meta = next((s for s in scans if s["scan_date"] == scan_date), {})
    try:
        params = _json.loads(meta.get("params") or "{}")
    except Exception:
        params = {}
    return jsonify({"scan_date": scan_date, "rows": rows,
                    "sectors": sector_attractiveness(all_rows),
                    "universe_size": meta.get("universe_size"), "scored": meta.get("scored"),
                    "provider": meta.get("provider"), "filtered": params.get("filtered"),
                    "history": [s["scan_date"] for s in scans][:12]})


_LAST_TRACK_REFRESH = [0.0]


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
    threading.Thread(target=_work, daemon=True).start()


@app.route("/api/track")
def api_track():
    """Live forward track record: the top-10 hot stocks + screaming-buy options vs the S&P."""
    from ..edge import track
    st = _store()
    _maybe_refresh_track()
    out = {}
    for source in ("hot10", "options"):
        out[source] = {"summary": track.summary(st, source),
                       "recent": _recent_track_picks(st, source)}
    return jsonify({"sources": out,
                    "note": "Forward, survivorship-free record of real dated picks vs the S&P 500. Options "
                            "are tracked by the underlying's forward return (signal accuracy, not option "
                            "P&L). Educational only; past results don't predict future performance."})


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
    return jsonify({"run_time": rt, "rows": st.load_intraday(rt, top=top)})


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
