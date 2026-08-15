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

from flask import Flask, render_template, request, jsonify, send_file

from ..config import CONFIG
from ..safe_error import log_exception, safe_error
from ..engine.pipeline import value_ticker
from ..report import excel as excel_report
from ..report import pdf as pdf_report
from . import resultcache, withhold
from .query_params import clamp_int          # MA50 — one clamp for every caller row limit
from . import score_confidence as _score_confidence
from . import theme_status as _theme_status
from . import hold_horizon as _hold_horizon
from . import dip_posture as _dip_posture

app = Flask(__name__)

# Shown wherever the product outputs something that looks like a recommendation. Kept as one
# string so the Index, the signals feed and the methodology page cannot drift apart on what
# the product claims — the wording is the claim.
RISK_DISCLAIMER = (
    "Educational research tool — not investment advice, and not a recommendation to buy or "
    "sell any security. Backtested results are hypothetical, come from one 18-year dataset "
    "the model was also tuned on, and are not a promise about the future. The forward track "
    "is a model portfolio and a sandbox paper account — no money is invested in either, so "
    "no figure here is a return anyone received — and it is short. You can lose money. Do "
    "your own research."
)

# The exports render the document behind the page the visitor is looking at, so they serve
# the result the page rendered rather than recomputing it against a different quote. This
# used to be a bare `_LAST: dict` keyed by ticker with no timestamp, no expiry and no bound
# — see `resultcache.py` for what that got wrong and what it cost. Same idea, three missing
# properties added: the key is the whole request, every entry is stamped, and it is bounded.
_RESULTS = resultcache.ResultCache()


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
    def _live_hero():
        """The forward-track hero band, computed only if a template actually asks for it.

        A callable rather than a value: this context processor runs on EVERY render, including
        error pages, and the hero costs a couple of DB reads. Templates that don't show it
        don't pay for it. Failure returns the not-started shape — a hero band is never a
        reason for a page to 500.
        """
        try:
            from .hero import live_hero
            return live_hero(_store())
        except Exception:
            return {"show": False, "may_lead": False, "thin": True,
                    "label": "the forward paper track has not started",
                    "index": {"available": False}, "options": {"available": False},
                    "spark": None, "caveat": ""}

    return {"contact_email": CONFIG.contact_email,
            "feedback_url": CONFIG.resolved_feedback_url,
            "signed_in": False, "logout_url": "/logout",
            # Also supplied by the SaaS context processor, which overrides this one. Declared
            # here too so the standalone tool app (no accounts layer) renders index.html with
            # the same framing instead of falling back to Jinja's undefined — a template that
            # silently treats "no such variable" as false would quietly restore the product
            # copy on the one deployment shape that has no auth at all.
            "private_mode": CONFIG.private_mode,
            # V3's noise calibration governs how precisely the hot score may be described.
            # Site-wide rather than per-route: index.html is rendered by BOTH web/app.py and
            # saas/app_saas.py, and a surface that renders the score while forgetting the
            # calibration is the failure this is here to prevent. Cheap constants, no I/O.
            "score_confidence": _score_confidence.for_template(),
            # S22's term structure governs what may be said about how long the edge lasted.
            # Same reason it sits here and not on a route: the horizon figures are the most
            # flattering numbers the backtest produces, and the caveats S22 registered as
            # mandatory travel with them from one source or not at all.
            "hold_horizon": _hold_horizon.for_template(),
            # What each theme is made of, and which ones reach a live score. Same one-source
            # rule as the two above, and for a demonstrated reason: the hand-maintained legend
            # in app.js described `capital_discipline` as dormant on the very day it was
            # restored, and listed an input the theme had stopped using.
            "theme_status": _theme_status.payload(),
            # What the Dip Detector is allowed to claim, gated on the V6 register. Site-wide
            # for the same reason as the three above — index.html has two renderers — and
            # because this one has a deadline: the copy is written to be REPLACED when V6
            # closes, and a surface holding its own copy is a surface that keeps saying "we
            # are testing it" after the answer has landed.
            "dip_posture": _dip_posture.posture(),
            "live_hero": _live_hero}


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
    """How it works — point-in-time, survivorship, costs, the payoff shape, and the weaknesses.

    `payoff` is passed rather than hard-coded into the template so the distribution on the public
    page, the one in `/api/whatdo` and the one on the owner scorecard are the same object. A
    number typed into a template is a number that drifts.
    """
    from . import payoff as _payoff
    return render_template("methodology.html", disclaimer=RISK_DISCLAIMER,
                           payoff=_payoff.payoff_summary())


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
        entry = _RESULTS.put(ticker, result, overrides=overrides, peers=peers)
        payload = result.to_dict()
        # When these numbers were produced. The page prints it and so do the exports, so a
        # reader can see for themselves that the document and the screen describe the same
        # moment. `company.as_of` is the FUNDAMENTALS date and reads as today even when the
        # figures are hours old — it never answered this question.
        payload["computed_at"] = entry.stamp
        # A refusal and a data gap both leave base_fair_value None, and they need
        # opposite messages: "check the ticker symbol" is wrong and misleading on a name
        # the model deliberately declined to value.
        if withhold.is_withheld(payload):
            # Nothing downstream of the withheld fair value goes on the wire. The page used
            # to print the suppressed number back to the reader three cards later.
            payload = withhold.withhold_derived_figures(payload)
        elif result.base_fair_value is None:
            payload.setdefault("warnings", []).append(
                "Could not compute a per-share value (missing shares/price). "
                "Check the ticker symbol.")
        return jsonify(payload)
    except Exception as e:
        log_exception()
        return jsonify({"error": f"Valuation failed for {ticker}: {safe_error(e)}"}), 500


@app.route("/api/rank", methods=["POST"])
def api_rank():
    data = request.get_json(force=True) or {}
    tickers = [t.strip().upper() for t in (data.get("tickers") or []) if t.strip()]
    run_ai = bool(data.get("run_ai", False))
    rows = []
    for t in tickers[:25]:
        try:
            r = value_ticker(t, CONFIG, run_ai=run_ai, mc_trials=2000)
            _RESULTS.put(t, r)
            # A withheld name still returns a score — a PARTIAL one, built on four of the
            # five sub-scores (scoring.py:202). The watchlist puts it in a column beside full
            # scores, so it has to carry the flag or the table silently compares two
            # different things.
            partial = withhold.is_withheld_result(r)
            rows.append({
                "ticker": t, "name": r.company.name, "price": r.company.price,
                "fair_value": r.base_fair_value, "upside": r.upside,
                "score": r.score.score, "recommendation": r.score.recommendation,
                "regime": r.classification.regime, "confidence": r.score.confidence,
                "score_partial": partial,
                "fair_value_withheld": partial,
                "fair_value_withheld_reason": withhold.refusal_reason(r) if partial else None,
            })
        except Exception as e:
            rows.append({"ticker": t, "error": safe_error(e)})
    rows.sort(key=lambda x: (x.get("score") is not None, x.get("score", -1)), reverse=True)
    return jsonify({"rows": rows})


def _get_or_compute(ticker: str, overrides: dict = None, peers: list = None):
    """The result for THIS request — the cached one if it is still fresh, else a new one.

    On a miss it recomputes under the same assumptions the page used, which is the whole
    point: a miss (different worker, or an entry past its TTL) now costs a computation
    instead of silently handing back an answer to a different question. Returns the cache
    entry rather than the result, because the caller has to stamp the document with when
    the numbers were made.
    """
    ticker = ticker.upper()
    hit = _RESULTS.get(ticker, overrides=overrides, peers=peers)
    if hit is not None:
        return hit
    r = value_ticker(ticker, CONFIG, overrides=overrides or {}, peers=peers)
    return _RESULTS.put(ticker, r, overrides=overrides, peers=peers)


# A download is a publication, so the workbook and the tearsheet obey the same rule as the
# page: no figure derived from a withheld valuation appears in them. This lane used to
# DECLINE the request with a 409 because `report/**` was another lane's; it is not any more,
# and an error was the wrong answer — it says the export is broken, when the export is fine
# and the valuation is withheld. `report/pdf.py` and `report/excel.py` now build a document
# that says exactly that, with the reason on it. Nothing is refused at the route.
@app.route("/api/export/excel")
def export_excel():
    ticker = (request.args.get("ticker") or "").strip().upper()
    if not ticker:
        return jsonify({"error": "No ticker"}), 400
    try:
        # The assumptions travel with the download. Without them the export could only ask
        # "the last NKE anyone computed on this worker", which is a different question from
        # "the NKE on my screen" whenever the visitor has touched the assumption panel.
        entry = _get_or_compute(ticker, overrides=_parse_overrides(request.args),
                                peers=request.args.getlist("peers") or None)
        result = entry.result
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        excel_report.build_workbook(result, tmp.name, computed_at=entry.stamp)
        return send_file(tmp.name, as_attachment=True,
                         download_name=f"{ticker}_DCF_Model.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        log_exception()
        return jsonify({"error": safe_error(e)}), 500


@app.route("/api/export/pdf")
def export_pdf():
    ticker = (request.args.get("ticker") or "").strip().upper()
    if not ticker:
        return jsonify({"error": "No ticker"}), 400
    try:
        entry = _get_or_compute(ticker, overrides=_parse_overrides(request.args),
                                peers=request.args.getlist("peers") or None)
        result = entry.result
        if result.ai is None:
            try:
                from ..ai.analyst import analyze
                result.ai = analyze(result, CONFIG)
            except Exception:
                pass
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        pdf_report.build_pdf(result, tmp.name, computed_at=entry.stamp)
        return send_file(tmp.name, as_attachment=True,
                         download_name=f"{ticker}_Valuation_Report.pdf",
                         mimetype="application/pdf")
    except Exception as e:
        log_exception()
        return jsonify({"error": safe_error(e)}), 500


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
    # S14 ADOPTION (2026-08-13): this route used to build the book with NO band while publishing
    # a config block that advertised one, so it served a DIFFERENT book from the exported Index
    # under the same name -- the B7 disease on a public surface. It now applies the same band,
    # against the same previous book on disk, through the same imported rule.
    #
    # A fixed-N config (roth) stays band-less: `exit_frac` is a fraction of the ranked UNIVERSE
    # and is not the arm S14 measured for a 25-name book.
    from ..edge.valquo_index import config_block, _previous_book, DEFAULT_PATH
    if cfg.get("exit_frac") and not cfg.get("top_n"):
        kw["exit_frac"] = cfg["exit_frac"]
        kw["held"] = _previous_book(DEFAULT_PATH)
    payload = build_index(rows, **kw)
    payload["config"] = config_block(name, cfg)
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
        return jsonify({"available": False, "error": safe_error(e),
                        "note": "Live track unavailable."}), 200
    # WHICH BOOK THIS RECORD IS OF. Contract §5a Rule 4: a verdict is a statement about a
    # vintage and must name it. This card is the closest thing the product has to one, and until
    # now it named an inception date but never the vintage that date belongs to -- so a reader
    # could not tell that the series restarted, or that a predecessor is being shadowed.
    #
    # Derived in `track_meter` from the register itself, never typed here: the label and the
    # clock have to move together, and this route is exactly where they would drift apart.
    # Owner-only (`saas/surfaces.py` lists this path), and it carries no measurement -- the
    # shadow's NUMBERS remain fenced off every outbound surface, which is what PT-OUTBOUND asks.
    try:
        from ..edge import track_meter
        out["vintage"] = track_meter.vintage_label()
    except Exception:                                    # noqa: BLE001
        pass                                             # a label must never break the card
    out["disclaimer"] = RISK_DISCLAIMER
    return jsonify(out)


def _closed_streak(store, payoff):
    """The realized losing streak, judged against the banked distribution.

    ORDERED BY `alert_ts`, NOT BY EXIT. That is a deliberate choice and it is the one that makes
    the comparison legitimate: the banked streak table was measured on a sequence ordered by
    entry date, so ordering the live book by exit date would score one sequence against another
    sequence's distribution. Trades of different horizons close out of order, so the two really
    do differ.

    A closed trade with no scoreable return is skipped rather than counted either way — see
    `payoff.longest_loss_run`.
    """
    with store._conn() as c:
        cur = c.execute("SELECT pnl_pct FROM option_alerts WHERE status='closed' "
                        "ORDER BY alert_ts")
        pnl = [r[0] for r in cur.fetchall()]
    outcomes = [None if p is None else (float(p) > 0) for p in pnl]
    scored = [o for o in outcomes if o is not None]
    longest = payoff.longest_loss_run(outcomes)

    # The run still open right now — what the reader is actually living through. The VERDICT is
    # on the longest, because "longest run inside a stretch" is the statistic the table measures;
    # quoting the current run against that distribution would compare two different things.
    current = 0
    for o in reversed(outcomes):
        if o is None:
            continue
        if o:
            break
        current += 1

    out = payoff.streak_verdict(len(scored), longest)
    out["current_loss_run"] = current
    out["current_is_longest"] = bool(current and current == longest)
    return out


@app.route("/api/options-scorecard")
def api_options_scorecard():
    """Expectancy of the scream-buy options alerts, from REAL closed contract outcomes.

    Deliberately not a "success rate": for a payoff this asymmetric, hit rate without win/loss
    size is uninformative. Outcomes are written back by the external Robinhood job, so early on
    this legitimately reports mostly-open alerts and near-empty statistics — which is the
    honest state, not a bug.

    It also carries the RUNNING LOSING STREAK against the modelled distribution. This is the
    surface a discouraged reader actually opens, and until now it could tell them their hit rate
    was 20% without telling them whether that was a bad run or a broken product. `streak` answers
    exactly that, and it is capable of answering "this is worse than the record" — see
    `payoff.streak_verdict`.
    """
    from ..edge.options_tracker import scorecard, tuning_candidates
    from ..screener.store import Store
    from . import payoff
    try:
        st = Store()
        sc = scorecard(st)
        sc["tuning"] = tuning_candidates(st)
        sc["payoff"] = payoff.payoff_summary()
        sc["streak"] = _closed_streak(st, payoff)
        return jsonify(sc)
    except Exception as e:
        return jsonify({"error": safe_error(e), "overall": {"n_closed": 0}, "n_open": 0}), 200


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
        # Already two-sided before MA50 — this is the site the other four should have copied.
        # Routed through the shared clamp anyway so the sweep leaves NO hand-rolled clamp
        # behind: one correct copy beside four wrong ones is how the wrong ones survive.
        top = clamp_int(request.args.get("top"), default=5, cap=15)
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
        log_exception()
        return jsonify({"error": safe_error(e), "alerts": []}), 200


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
        return jsonify({"error": safe_error(e), "n_closed": 0, "thin": True}), 200


@app.route("/api/hotstocks")
def api_hotstocks():
    """Read the latest cached scan snapshot + sector attractiveness (instant)."""
    from flask import g
    from ..screener.sectors import sector_attractiveness
    cap = getattr(g, "hotstocks_cap", 500)          # per-tier cap (set by the SaaS layer)
    # MA50: this read `min(int(...), cap)`, which bounds from above only. `min(-1, 500)` is
    # -1, and `store.load_snapshot` interpolates it into `LIMIT -1`, which SQLite treats as
    # UNLIMITED — so `?top=-1` returned the whole snapshot and defeated the per-tier cap that
    # IS the paywall. Masked in production only by OPEN_ACCESS=true.
    top = clamp_int(request.args.get("top"), default=100, cap=cap)
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
    # ...and nothing implausible goes out with it. This estimator has no ceiling: its EV
    # bridge is `3 + 2 x (net debt / market cap)` times the price, so a leveraged name can
    # clear the valuation page's 5x refusal band on this PUBLIC surface while that page is
    # refusing the very same claim. One number, one meaning — the band is the page's own.
    withhold.withhold_implausible_fair_values(rows)
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


@app.route("/api/dip")
def api_dip():
    """The Dip Detector: healthy names trading well below their own 52-week high.

    A SCREEN, NOT A PREDICTION, and the payload says so in its own `posture` block rather
    than leaving it to the template — see `dip_posture` for why that is a module and what the
    V6 close-out flips.

    THE COST MODEL IS THE INTERESTING PART. The whole universe is sieved for free off the
    cached scan snapshot (publication flags, then a cross-sectional prefilter), ordered
    EXACTLY by drawdown using the persisted `z_high_prox` — standardisation within a date is
    strictly monotone, so the ordering is identical to ordering by the raw ratio — and only
    the top few names are actually valued. Each valuation goes through the SAME TTL cache the
    single-name page uses, so a row here can never disagree with that name's own page, and a
    reader who opens one has warmed the cache for the other.

    Everything the bound dropped is reported (`capped`, `n_unmeasured`): a screen that
    silently truncates reads as coverage.
    """
    from . import dip
    try:
        st = _store()
        scan_date = st.latest_scan_date()
        posture = _dip_posture.posture()
        if not scan_date:
            return jsonify({"empty": True, "posture": posture, "rows": [],
                            "disclaimer": RISK_DISCLAIMER,
                            "message": "The daily scan hasn't loaded into this site yet — the "
                                       "Dip Detector reads the same snapshot the hot list does."})
        # The snapshot load, both publication passes, the screen and the call budget now live
        # in `dip.screen_snapshot`, because the Discord digest became a second caller and two
        # copies of this sequence is how the Index and the hot list came to disagree once
        # already. The route contributes the request parsing and nothing else.
        # Two-sided already; routed through the shared clamp for the parse guard and so the
        # sweep leaves nothing hand-rolled behind (MA50).
        shortlist = clamp_int(request.args.get("shortlist"),
                              default=dip.DEFAULT_SHORTLIST, cap=dip.MAX_SHORTLIST)
        out = dip.screen_snapshot(st, _get_or_compute,
                                  min_drawdown=request.args.get("min_drawdown"),
                                  shortlist=shortlist, scan_date=scan_date)
        out["posture"] = posture
        out["disclaimer"] = RISK_DISCLAIMER
        from ..screener.freshness import status as _freshness
        out["freshness"] = _freshness(scan_date, label="screen")
        return jsonify(out)
    except Exception as e:
        log_exception()
        return jsonify({"error": safe_error(e), "rows": [],
                        "posture": _dip_posture.posture()}), 200


@app.route("/api/scream-track")
def api_scream_track():
    """The scream-buy record: every alert with what it was bought at, sold at and is worth now.

    A pure CONSUMER of `edge/scream_log.py`, which the greeks lane owns — see that module's
    field contract in `HANDOFF_appfixes.md`. Nothing here recomputes a premium, a status, a
    staleness flag or the epoch boundary, and this route cannot trigger the reset.

    `entry_premium` is the ALERT-TIME premium and is NOT the paper broker's fill. Those are
    two different books, and session 16 exists because they were once conflated.

    The footer travels with the table on every response, including `n_prior_epochs` — the
    number that makes a reset visible rather than merely honest.
    """
    from . import scream_track
    try:
        return jsonify(scream_track.summary(_store()))
    except Exception as e:
        log_exception()
        return jsonify({"error": safe_error(e), "rows": [], "n_rows": 0,
                        "summary": {"epoch": None, "reset": None,
                                    "n_prior_epochs": None, "unavailable": True}}), 200


@app.route("/api/whatdo")
def api_whatdo():
    """One name across BOTH books — the ranking, the book position, the options alert.

    Composed from stored state only (scan snapshot, constructed book, logged alerts, paper
    positions), so it is cheap enough to fire alongside every valuation and can never disagree
    with the tabs it summarizes: each figure comes back from the module that owns it.
    """
    from flask import g
    from .unified import name_view
    ticker = (request.args.get("ticker") or "").strip().upper()
    if not ticker:
        return jsonify({"error": "ticker required"}), 400
    try:
        return jsonify(name_view(_store(), ticker,
                                 book_config=request.args.get("config"),
                                 with_options=getattr(g, "may_see_options", True),
                                 # Defaults to True so a direct/standalone run (no SaaS layer,
                                 # i.e. the owner on a laptop) is unchanged; the SaaS guard
                                 # sets it False for every public visitor.
                                 with_book=getattr(g, "may_see_owner", True)))
    except Exception as e:
        log_exception()
        # This panel is an ADDITION to a valuation that already rendered. A failure here must
        # never take the page down with it.
        return jsonify({"ticker": ticker, "error": safe_error(e),
                        "stock": {"in_scan": False}, "options": {}, "action": []}), 200


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
    # MA50 class. Public (this fires on every keystroke in the search box) and previously
    # one-sided: `limit=-1` slid straight through into the slice below.
    limit = clamp_int(request.args.get("limit"), default=8, cap=25)

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
    # The Tradier-sandbox forward track (roadmap #12): real paper orders, real fills, and the
    # Index-vs-SPY record since inception. Read-only here and never allowed to break the page —
    # an empty or absent paper book must render as "not started", not as a 500.
    try:
        from ..edge import paper_track
        sandbox = paper_track.summary(st)
    except Exception:
        sandbox = {"options": {"started": False}, "index": {"started": False},
                   "headline": "The forward paper track has not been started."}
    return jsonify({"sources": out, "paper": paper, "paper_sandbox": sandbox,
                    "note": "Forward, survivorship-free record of real dated picks vs the S&P 500. Options "
                            "are tracked by the underlying's forward return (signal accuracy, not option "
                            "P&L). `paper_sandbox` is the separate Tradier PAPER account track — real "
                            "simulated orders and fills on ~15-min-delayed data, thin until it says "
                            "otherwise. Educational only; past results don't predict future performance."})


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
        log_exception()
        return jsonify({"error": safe_error(e)}), 500


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
        log_exception()
        return jsonify({"error": safe_error(e)}), 500


@app.route("/api/signals")
def api_signals():
    """Latest intraday buy-setup snapshot (fast read; the dashboard polls this)."""
    from ..screener.store import Store
    st = Store()
    rt = st.latest_intraday_time()
    if not rt:
        return jsonify({"empty": True, "message": "No intraday scan yet — hit Refresh. "
                        "Add a TRADIER_TOKEN for real-time; otherwise it uses free delayed data."})
    # MA50, same class: this was an unclamped `int(...)` feeding `load_intraday(top=...)`,
    # which builds the same `LIMIT {int(top)}`. Owner-only today, so the exposure is smaller
    # than /api/hotstocks — but it is the identical defect and is fixed with it, because the
    # one that gets fixed alone is the one that comes back.
    top = clamp_int(request.args.get("top"), default=40, cap=500)
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
        log_exception()
        return jsonify({"error": safe_error(e)}), 500


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
        log_exception(); return jsonify({"error": safe_error(e)}), 500


@app.route("/api/edge/optimize", methods=["POST"])
def api_edge_optimize():
    from ..edge.lab import run_optimize
    d = request.get_json(silent=True) or {}
    try:
        return jsonify(run_optimize(limit=int(d.get("limit", 100))))
    except Exception as e:
        log_exception(); return jsonify({"error": safe_error(e)}), 500


@app.route("/api/edge/track", methods=["POST"])
def api_edge_track():
    from ..edge.lab import run_track
    d = request.get_json(silent=True) or {}
    try:
        return jsonify(run_track(source=d.get("source", "hot")))
    except Exception as e:
        log_exception(); return jsonify({"error": safe_error(e)}), 500


def create_app():
    return app
