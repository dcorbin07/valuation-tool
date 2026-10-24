"""
Flask web dashboard — the user-facing tool.

Routes:
  GET  /                     the single-page dashboard
  POST /api/value            value one ticker -> full JSON result
  POST /api/rank             score many tickers -> ranked list (watchlist)
  GET  /api/export/excel     download the live Excel model
  GET  /api/export/pdf       download the PDF tearsheet
  GET  /tidemark             TIDEMARK (separate project) — derived stats only
  GET  /api/health           config / status probe
"""
from __future__ import annotations

import io
import os
import tempfile

from flask import Flask, render_template, request, jsonify, send_file

from ..config import CONFIG
from ..safe_error import log_exception, safe_error
from ..engine.pipeline import value_ticker
from ..report import excel as excel_report
from ..report import pdf as pdf_report
from . import resultcache, withhold
from .query_params import clamp_int, clamp_float   # MA50/MA53 — one clamp per caller number
from . import score_confidence as _score_confidence
from . import valuation_verdict as _verdict
from . import ai_auto as _ai_auto
from . import definitions as _definitions
from . import theme_status as _theme_status


def _theme_contributing():
    """`health.theme_contributing` from the latest scan, or None.

    Returns None rather than `{}` when it cannot be read: an empty dict would make every theme
    read as contributing nothing, so the copy would claim the ranking runs on ZERO themes on a
    day the store was merely unreachable. `sentence` has a distinct branch for None and says the
    figure is unavailable.
    """
    try:
        from ..screener.store import Store
        st = Store()
        date = st.latest_scan_date()
        if not date:
            return None
        h = st.get_meta("scan_health_%s" % date)
        if isinstance(h, str):
            import json as _json
            h = _json.loads(h)
        tc = (h or {}).get("theme_contributing")
        return tc if isinstance(tc, dict) and tc else None
    except Exception:                                                   # noqa: BLE001
        return None
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
            # ITEM 52 part 6: injected site-wide for the same reason the calibration is
            # -- so a page cannot render the AI panel while forgetting to say what
            # wrote it.
            "ai_panel_label": _ai_auto.PANEL_LABEL,
            # ITEM 53 part 4: the plain definitions, site-wide for the same reason as the two
            # above. The alternative is a `title=` string written inline beside each number,
            # which is how one term comes to be defined two different ways on one page.
            "definitions": _definitions.payload(),
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
            # HOW MANY THEMES THE RANKING RUNS ON, DERIVED. The literal had already been wrong
            # twice in OPPOSITE directions -- "nine themes" while five were live, then "five of
            # seven" which goes wrong the day the theme cache lands -- and it disagreed with
            # `theme_status` itself, which reported insider and institutional as not dormant
            # (they are WIRED) while the scan reported them contributing 0.0 (they did not MOVE).
            # `counts`/`sentence` name those two facts separately and the copy reads the DAY,
            # which is what it claims.
            "theme_counts": _theme_status.counts(_theme_contributing()),
            "theme_sentence": _theme_status.sentence(_theme_contributing()),
            # What the Dip Detector is allowed to claim, gated on the V6 register. Site-wide
            # for the same reason as the three above — index.html has two renderers — and
            # because this one has a deadline: the copy is written to be REPLACED when V6
            # closes, and a surface holding its own copy is a surface that keeps saying "we
            # are testing it" after the answer has landed.
            "dip_posture": _dip_posture.posture(),
            "live_hero": _live_hero}


def _proof_payload():
    """The evidence for the Proof TAB on the app page — the same payload /proof renders.

    Wrapped so a broken artifact can never take the whole app down: the tab is one surface of
    nine, and a visitor who came for a valuation should get one. The partial renders the
    refusal when `available` is False, so the failure is visible rather than silent."""
    try:
        from . import proof as _proof
        return _proof.payload()
    except Exception as e:                                              # noqa: BLE001
        app.logger.exception("proof payload failed; the tab will say so")
        return {"available": False, "missing": ["proof payload"],
                "reason": f"the evidence could not be assembled ({type(e).__name__})"}


@app.route("/")
def index():
    # Standalone/local use = owner (no auth layer). The SaaS /app route overrides this.
    # signed_in=False here because standalone has no auth, so there's nothing to sign out of.
    return render_template("index.html",
                           ai_enabled=CONFIG.ai_enabled,
                           ai_provider=CONFIG.resolved_ai_provider, is_owner=True,
                           signed_in=False, logout_url="/logout",
                           contact_email=CONFIG.contact_email,
                           feedback_url=CONFIG.resolved_feedback_url,
                           p=_proof_payload())


@app.route("/methodology")
def methodology():
    """How it works — point-in-time, survivorship, costs, the payoff shape, and the weaknesses.

    `payoff` is passed rather than hard-coded into the template so the distribution on the public
    page, the one in `/api/whatdo` and the one on the owner scorecard are the same object. A
    number typed into a template is a number that drifts.
    """
    from . import payoff as _payoff
    # LIVE, NOT TYPED (E9, E12). This page carried "248 by 2026-09-29" and "~800 most liquid"
    # while the log read 578 total and the scan ranks 1,500. One parse, the same one `/proof`
    # and the Deflated Sharpe's own denominator use.
    from . import live_facts as _facts
    return render_template("methodology.html", disclaimer=RISK_DISCLAIMER,
                           payoff=_payoff.payoff_summary(),
                           trials=_facts.trial_counts(),
                           # LIVE, NOT TYPED [item 76]. The cost paragraph carried three
                           # figures from the superseded 2,531-name panel.
                           costs=_facts.costs(),
                           universe=_facts.universe_size(_store()))


@app.route("/proof")
def proof():
    """The evidence — every headline figure, the bar it was measured against, and the fails.

    A SEPARATE PAGE FROM /methodology, deliberately, and the split is by object rather than by
    length: /methodology explains the construction in prose and carries almost no figures;
    this carries the figures and the thresholds and explains almost no construction. Merging
    them would produce one page that is read by nobody, and — worse — two places on the site
    quoting the same statistic, which is the drift this project has paid for repeatedly.

    `payload()` reads both artifacts at request time and types nothing. It also REFUSES rather
    than substituting: a missing artifact costs a section and is named on the page. A proof
    surface that silently falls back to a hard-coded number is the one failure mode that would
    make the whole page worse than not having it.

    Public and ungated, like /methodology and /tidemark. Nothing here is vendor data — every
    figure is a derived research statistic about this project's own model, and the one dataset
    whose licence forbids republication (Global Factor Data, CC BY-NC) is excluded at the
    module level rather than by remembering not to render it.
    """
    from . import proof as _proof
    return render_template("proof.html", disclaimer=RISK_DISCLAIMER, p=_proof.payload())


@app.route("/tidemark")
def tidemark():
    """TIDEMARK — a SEPARATE project's Phase-1 result, reported as a linked page.

    `VALQUO_MASTER_AUDIT_4.md` MB25 specifies a linked page rather than a tab inside the
    hot-list surface, and the reason is the one MB26 then enforces: the two projects have
    different verdict grammars and different denominators, so a tab implies they are one
    product and a reader who averages a Valquo statistic with a TIDEMARK one has been misled
    by the layout.

    `payload()` carries derived statistics only — percentile, episode count, effective n,
    band half-width, tier, refusal, vintage, names. No source series level crosses into this
    process, so the licensed inputs behind TIDEMARK (Case-Shiller via FRED, NAREIT) are never
    reproduced here.

    `t_se` is passed as a CALLABLE rather than precomputed onto each row so the payload stays
    exactly at MB25's nine allowlisted keys; the band is recomputed at render time from the
    percentile and the effective n using TIDEMARK's own formula.
    """
    from . import tidemark_surface as _tidemark
    return render_template("tidemark.html", disclaimer=RISK_DISCLAIMER,
                           t=_tidemark.payload(), t_se=_tidemark.percentile_se)


@app.route("/api/health")
def health():
    # THE SECTOR CHAIN'S OWN HEALTH, on a surface that already exists and needs no token.
    # A service quietly living on the SEC rung looks identical to one whose primary is healthy,
    # and after an INTERMITTENT failure that difference is the entire question. Counts only --
    # no tickers, nothing a log would not already carry.
    try:
        from ..data.sector_resolve import source_census as _sector_census
        _sec_health = _sector_census()
    except Exception:                                                   # noqa: BLE001
        _sec_health = None
    # **WHICH COMMIT IS ACTUALLY SERVING [item 80, 2026-10-23].** Added because confirming a
    # deploy was not possible: `render.yaml` sets `autoDeploy: true` and nothing on any surface
    # said what had deployed, so "the fix is live" could only ever be INFERRED from main's HEAD
    # plus elapsed time. On a night when Don was waiting mid-rebalance on a one-line fix, that
    # is the difference between telling him it is live and telling him it probably is.
    #
    # `RENDER_GIT_COMMIT` is set by Render itself on every deploy. Absent locally, which reads
    # as `null` rather than as a guess. **A commit SHA is not a secret** -- this repository is
    # public by the posture `render.yaml` documents -- and nothing else is added: no path, no
    # branch, no environment, no token.
    _commit = os.environ.get("RENDER_GIT_COMMIT") or None
    return jsonify({"ok": True, "ai_enabled": CONFIG.ai_enabled,
                    "sector_sources": _sec_health,
                    "commit": _commit,
                    "commit_short": (_commit[:7] if _commit else None),
                    "ai_provider": CONFIG.resolved_ai_provider,
                    "mc_trials": CONFIG.montecarlo_trials})


def _recent_block(ticker: str, name: str = "") -> dict:
    """Item 53 part 2's block, cached for the day. ONE builder, two consumers.

    The page fetches it through `/api/recent` and the AI route reads it to put in the prompt,
    and both come through here -- a second path would be two answers to "what has happened to
    this company", which is the whole reason this is a function rather than inline code.

    **CACHED PER TICKER PER DAY, beside the AI analysis**, which is what Don asked for and is
    also what stops a page reload from making four network calls again.
    """
    from . import ai_auto as AA
    hit = AA.cached_recent(ticker)
    if hit is not None:
        out = dict(hit)
        out["cached"] = True
        return out
    from ..data import recent as _recent
    cik = None
    try:
        from ..data import edgar as _edgar
        cik = _edgar.resolve_cik(ticker, CONFIG)
    except Exception:                                                       # noqa: BLE001
        cik = None
    block = _recent.recent_block(ticker, name=name, cik=cik)
    block["cik"] = cik
    AA.store_recent(ticker, block)
    block["cached"] = False
    return block


@app.route("/api/recent", methods=["GET"])
def api_recent():
    """The last reported quarter, recent headlines and recent filings.  [item 53 part 2]

    **GET, AND IT SPENDS NOTHING.** Three free feeds and a cache. It is separate from
    `/api/value` on purpose: those feeds cost up to four network calls, and item 52 measured
    that the page's two seconds are the fetch rather than the model -- so this is fetched
    AFTER the numbers paint, exactly as `loadWhatDo` and the AI panel already are.
    """
    ticker = (request.args.get("ticker") or "").strip().upper()
    if not ticker:
        return jsonify({"error": "No ticker provided."}), 400
    try:
        return jsonify(_recent_block(ticker, name=(request.args.get("name") or "").strip()))
    except Exception as e:                                                  # noqa: BLE001
        log_exception("api_recent")
        return jsonify({"ok": False, "ticker": ticker, "reason": safe_error(e)}), 500


def _may_spend_ai() -> bool:
    """May this request start a PAID AI call? Default-deny.  [item 53 part 5]

    The SaaS layer's `_guard` answers the ownership question and sets `g.may_spend_ai`, the
    same way it sets `g.hotstocks_cap` and `g.may_see_owner` -- this app has no access to
    `auth` or the store, which is why the answer is handed in rather than computed here.

    **AN UNSET FLAG IS A REFUSAL.** The inner app is importable and runnable without the SaaS
    wrapper (every test client does exactly that), so "ran somewhere the guard does not" has
    to fail toward not spending money. `MA6`'s rule: err toward the state that refuses.
    """
    try:
        from flask import g
        return bool(getattr(g, "may_spend_ai", False))
    except Exception:                                                       # noqa: BLE001
        return False


def _company_profile_block(result) -> dict:
    """Item 52 part 5: what the company does, and the handful of facts a reader needs first.

    **THE PAGE CARRIED NO DESCRIPTION AT ALL.** A reader could see a fair value, a 1-100 score
    and nine theme contributions for a company they had been told nothing about.

    **THE DESCRIPTION IS THE VENDOR'S PROSE AND SAYS SO; EVERY FIGURE IS THE ENGINE'S OWN.**
    `yfinance` also ships `revenueGrowth`, `operatingMargins` and `totalRevenue`, and using
    them would put a second source of three numbers this project already computes on the same
    page as the first. Measured on NVDA today: the vendor's `revenueGrowth` reads 1.059 while
    the engine's own last-year revenue growth is 0.77 -- different windows, both defensible,
    and a page carrying each in a different box is a page that disagrees with itself.

    **EVERY FIELD IS NULL-ABLE AND NOTHING IS IMPUTED** (the COVERAGE RULE). An absent margin
    history yields `trend: None`, not a flat line; an absent summary yields an empty string
    with an empty source, not a source stamp on nothing.
    """
    try:
        cd = getattr(result, "company", None)
        if cd is None:
            return {"ok": False, "reason": "no company data on the result"}

        def _g(n):
            try:
                v = cd.revenue_growth(n)
            except Exception:                                          # noqa: BLE001
                return None
            return None if v is None else float(v)

        # ITEM 57 A3: THESE HISTORIES ARE NEWEST-FIRST, and this block was the one reader in
        # the project that assumed otherwise. `models.py` says so on the field itself --
        # "History (most-recent-first, aligned to fiscal_years)" -- and every other reader
        # honours it: `revenue_growth` takes `h[0], h[periods]`, `providers.py` takes
        # `h[1]/h[2]`, the analyst and the assumptions take a median (order-independent), and
        # `excel.py` reads `fiscal_years[0]` as FY0. Which is exactly why nobody noticed: the
        # arithmetic was right everywhere and only the DISPLAY was reversed.
        #
        # Measured live before the fix: NVDA's history is [215938, 130497, 60922, 26974] over
        # [2026, 2025, 2024, 2023] and the page printed $26.97B -- the 2023 figure -- as
        # "Revenue (latest yr)" against a true $215.94B. KNSL printed $838.80M against
        # $1.87B, and its margin trend read "34.4% -> 23.8%" when the margin had RISEN from
        # 23.8% to 34.4%.
        #
        # THE YEARS NOW TRAVEL WITH BOTH ENDPOINTS, which is the part that makes a recurrence
        # visible rather than plausible: a reader who sees "2022 -> 2025" can tell at a glance
        # that it is the right way round, and a reader who saw "34.4% -> 23.8%" could not.
        years = [y for y in (getattr(cd, "fiscal_years", None) or [])]
        hist_pairs = [(m, (years[i] if i < len(years) else None))
                      for i, m in enumerate(getattr(cd, "ebit_margin_history", None) or [])
                      if m is not None]
        # THE TREND IS TWO ENDPOINTS AND A COUNT, NOT A DIRECTION WORD. "improving" would be a
        # judgement about a series this page is not measuring, and two margins with the number
        # of years between them lets a reader make it themselves.
        trend = None
        if len(hist_pairs) >= 2:
            # `from` is the OLDEST and `to` is the NEWEST, so the pair reads left to right in
            # time -- the order a reader assumes and the order the old code inverted.
            old_m, old_y = hist_pairs[-1]
            new_m, new_y = hist_pairs[0]
            trend = {"from": float(old_m), "to": float(new_m), "n_years": len(hist_pairs),
                     "from_year": old_y, "to_year": new_y}
        elif len(hist_pairs) == 1:
            trend = {"from": None, "to": float(hist_pairs[0][0]), "n_years": 1,
                     "from_year": None, "to_year": hist_pairs[0][1]}

        rev_pairs = [(r, (years[i] if i < len(years) else None))
                     for i, r in enumerate(getattr(cd, "revenue_history", None) or [])
                     if r is not None]
        return {
            "ok": True, "reason": "",
            "summary": getattr(cd, "business_summary", "") or "",
            "summary_source": getattr(cd, "business_summary_source", "") or "",
            "sector": getattr(cd, "sector", "") or "",
            "industry": getattr(cd, "industry", "") or "",
            "market_cap": (float(cd.market_cap) if getattr(cd, "market_cap", None)
                           is not None else None),
            # NEWEST, i.e. index 0. See the note above.
            "revenue": (float(rev_pairs[0][0]) if rev_pairs else None),
            "revenue_year": (rev_pairs[0][1] if rev_pairs else None),
            "revenue_growth_1y": _g(1),
            "revenue_growth_3y": _g(3),
            "operating_margin_trend": trend,
            # WHERE EACH HALF CAME FROM, on the payload rather than in a template, because a
            # reader is owed the difference between somebody else's prose and our arithmetic.
            "figures_source": ("Computed by this tool from the filed statements it already "
                               "uses for the valuation."),
        }
    except Exception as e:                                             # noqa: BLE001
        log_exception("company_profile_block")
        return {"ok": False, "reason": safe_error(e)}


def _headline_block(result, payload: dict) -> dict:
    """ITEM 60's headline card, assembled from what the page already computed.

    **BUILT FROM THE PAYLOAD, NOT FROM `result`, AND THAT IS THE POINT.** The withholding pass
    has already run by the time this is called, so a suppressed fair value is visible here as a
    suppressed one -- and "the model withheld its value" is one of the states in which the card
    says there is NO verdict. Reading `result` directly would have seen the value the page
    refuses to show and published a verdict off it.

    **NEVER RAISES.** The card is the first thing on the page and also the newest thing on it,
    so a defect in it must cost the reader the card rather than the valuation. The failure is
    REPORTED in the block rather than swallowed, because an absent card and a broken one are
    different facts -- `price_assumes`' own rule, one block down.
    """
    try:
        cd = getattr(result, "company", None)
        cls = getattr(result, "classification", None)
        blend = getattr(result, "fair_value_blend", None)
        sc = getattr(result, "score", None)
        sc_pay = (payload.get("score") or {}) if isinstance(payload, dict) else {}
        scen = (payload.get("fair_value_scenarios") or {}) if isinstance(payload, dict) else {}
        pa = (payload.get("price_assumes") or {}) if isinstance(payload, dict) else {}

        return _verdict.headline(
            ticker=str(getattr(cd, "ticker", "") or payload.get("ticker") or ""),
            name=str(getattr(cd, "name", "") or ""),
            price=getattr(cd, "price", None),
            # THE SCENARIOS AS THE PAGE HAS THEM, so the card and the range bar below it can
            # never disagree about the same three numbers.
            bear=scen.get("bear"), base=scen.get("base"), bull=scen.get("bull"),
            method=str(scen.get("method") or ""),
            # THE BLEND'S CONFIDENCE, NOT THE SCORE'S -- and they genuinely differ. Measured
            # live on KNSL: `score.confidence` is "low" while `fair_value_blend.confidence` is
            # "medium". The card's range IS the blend's range, so labelling it with the
            # confidence in a DIFFERENT quantity (the 1-100 opportunity score) would be the
            # wrong-object family: a number correctly computed, correctly rendered, and
            # describing something else. The score's own confidence still shows on the gauge
            # where it belongs.
            confidence=str((getattr(blend, "confidence", "") if blend is not None else "")
                           or sc_pay.get("confidence")
                           or getattr(sc, "confidence", "") or ""),
            valuable=bool(getattr(blend, "valuable", False) if blend is not None else False),
            withheld=(getattr(blend, "withheld_value", None) if blend is not None else None),
            dcf_reliability=str(getattr(cls, "dcf_reliability", "") or ""),
            regime=str(getattr(cls, "regime", "") or ""),
            business_quality=str(sc_pay.get("business_quality")
                                 or getattr(sc, "business_quality", "") or ""),
            price_vs_model=str(sc_pay.get("price_vs_model")
                               or getattr(sc, "price_vs_model", "") or ""),
            assumes_sentence=str(((pa.get("lead") or {}) if isinstance(pa, dict) else {})
                                 .get("sentence") or ""),
            warning=((pa.get("warning") or {}) if isinstance(pa, dict) else {}),
        )
    except Exception as e:                                              # noqa: BLE001
        log_exception("headline_block")
        return {"ok": False, "verdict": _verdict.NONE, "label": _verdict.LABEL[_verdict.NONE],
                "no_verdict_cause": "card_failed",
                "no_verdict_reason": ("We could not assemble the summary card for this name. "
                                      "The valuation below is unaffected."),
                "error": type(e).__name__}


def _price_assumes_block(result) -> dict:
    """Item 52 parts 2, 3 and 7b, assembled from what the engine already computed.

    NEVER RAISES. The lead read is the most valuable thing on the page and it is also the
    newest, so a defect in it must cost the reader this block and not the valuation. The
    failure is REPORTED in the block rather than swallowed into an absence -- an empty read
    and a broken one are different facts.
    """
    # IMPORTED OUTSIDE THE `try`, so the failure branch below can name the rule even when the
    # assembly failed. Inside it, `PA` would be unbound exactly when it is needed.
    from ..web import price_assumes as PA
    try:
        cd = getattr(result, "company", None)
        cls = getattr(result, "classification", None)
        rev = getattr(result, "reverse", None)
        regime = str(getattr(cls, "regime", "") or "")
        is_fin = regime == "financial"

        # THE BUSINESS'S OWN LAST-YEAR GROWTH, from the engine's own accessor rather than
        # re-derived here. `blended_growth` is deliberately NOT used: it is a forward-ish
        # estimate that mixes a 3-year CAGR with an analyst figure, and the sentence says
        # "the business grew Y% over the last year", which is a measurement of the past.
        biz = None
        try:
            biz = cd.revenue_growth(1) if cd is not None else None
        except Exception:                                          # noqa: BLE001
            biz = None

        # ITEM 54 PART 4 -- THE FIELD IS `financial_surfaces`, AND `financial_extras` DOES NOT
        # EXIST ON `ValuationResult` AT ALL. Reported by r1 (`valreads.py` carries the same
        # note) and confirmed against the dataclass's own field list.
        #
        # `getattr` WITH A DEFAULT IS WHY IT WAS SILENT: a misspelled field returned `{}`
        # rather than raising, so every bank's "what the price assumes" rendered as
        # unavailable while the engine had the number -- `implied_roe` is computed on every
        # financial (ABCB 12.2%) and was being thrown away one lookup from the page. The
        # wrong-object family, and the kind that a default hides.
        fin_rev = (getattr(result, "financial_surfaces", None) or {}) if is_fin else {}
        fin_rev = (fin_rev.get("reverse") or {}) if isinstance(fin_rev, dict) else {}
        lead = PA.price_assumes(
            rev, biz, is_financial=is_fin,
            implied_roe=(fin_rev.get("implied_roe") if is_fin else None),
            book_roe=(getattr(cd, "roe", None) if is_fin else None))

        blend = getattr(result, "fair_value_blend", None)
        warn = PA.dcf_warning(
            regime=regime,
            dcf_reliability=str(getattr(cls, "dcf_reliability", "") or ""),
            cash_burning=bool(getattr(cls, "cash_burning", False)),
            growth_led=bool(getattr(blend, "growth_led", False)),
            reverse=rev, business_growth=biz)

        return {"ok": True, "lead": lead, "warning": warn,
                "template_note": PA.hypergrowth_template_note(regime, rev),
                "story_rule": PA.STORY_RULE_TEXT, "reason": ""}
    except Exception as e:                                         # noqa: BLE001
        log_exception("price_assumes_block")
        return {"ok": False, "lead": None, "warning": None, "template_note": "",
                "story_rule": PA.STORY_RULE_TEXT,
                "reason": safe_error(e)}


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
        # ITEM 25 -- NOT FOUND IS A 404 WITH NO SCORE, not a 200 with a partial one.
        #
        # Live 2026-10-03: `ZZZZQ` (which does not exist) and `BRK.B` (which does, spelled with
        # a dot) both answered HTTP 200 with `score 40, recommendation "Reduce"`. The 40 is one
        # orphaned sub-score after the valuation was withheld and the weights renormalised.
        #
        # REFUSED AT THE SURFACE RATHER THAN IN THE ENGINE, deliberately: `value_from_company`
        # is also the batch and offline entry point, and those callers hand it a `CompanyData`
        # they built themselves with no `fetch_failed` on it at all. Raising there would change
        # what the backtest does on a shape it has always accepted. The surface is where a
        # user-facing recommendation is decided, so it is where the refusal belongs.
        #
        # IT IS NOT CACHED. `_RESULTS.put` is skipped, because a cache entry for a symbol that
        # does not exist would answer the next request from memory and the refusal would depend
        # on cache state.
        _cd = getattr(result, "company", None)
        if getattr(_cd, "fetch_failed", False):
            return jsonify({
                "error": "ticker not found",
                "ticker": ticker,
                "detail": ("No data source returned anything for this symbol. No score, "
                           "valuation or recommendation is produced for a company that could "
                           "not be found - a partial score here would be one sub-score of "
                           "nothing, rendered as a verdict."),
                "hint": ("Check the spelling. A US share class is written with a hyphen by the "
                         "market-data source (BRK-B, not BRK.B), and that form is now accepted "
                         "either way."),
                "notes": list(getattr(_cd, "quality_notes", None) or [])[:4],
            }), 404
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
        # ---------------------------------------------------------------- ITEM 52 ----------
        # WHAT THE PRICE ASSUMES, AND WHETHER TO USE THE FAIR VALUE AT ALL.
        #
        # Added AFTER the withholding pass on purpose. `withhold_derived_figures` strips
        # everything downstream of a suppressed fair value, and this block is a read ABOUT the
        # price rather than a figure derived from the withheld value -- so it must not be
        # stripped, and it must not be computed from a number that was suppressed either.
        # `price_assumes` takes the reverse-DCF result, which is the engine's own answer to a
        # question that does not go through the fair value.
        payload["price_assumes"] = _price_assumes_block(result)
        payload["headline"] = _headline_block(result, payload)
        payload["profile"] = _company_profile_block(result)
        # ITEM 57 A2: WHETHER THE COMPANY PROFILE CAME FROM A FALLBACK, and which fields did.
        # On the wire because `live_check` has to be able to tell an outage from a data gap,
        # and that is a fact about the SET of names rather than any one of them -- so it needs
        # a per-name flag it can count. `used: false` is the healthy state and is carried too,
        # because an absent key and a measured "no fallback needed" must not read the same.
        # GUARDED THE WHOLE CHAIN, not just the attribute. `result` is a stub in several
        # suites (a SimpleNamespace with no `.company`), which is why every other block here
        # reaches through `getattr` -- and reaching for `result.company` directly turned
        # /api/value into an HTTP 500 for three suites.
        payload["identity_fallback"] = dict(
            getattr(getattr(result, "company", None), "identity_fallback", None)
            or {"used": False})
        # ITEM 53 part 3: what the same model says at beta 1.0. Attached AFTER the withheld
        # branch above on purpose -- `average_risk_read` refuses when there is no published
        # base value, so a withheld name carries `available: false` and the page prints
        # nothing rather than handing back a number the refusal withheld.
        payload["average_risk"] = dict(getattr(result, "average_risk", None) or {})
        # ITEM 76 §3: HOW MUCH THE VALUE DEPENDS ON ONE INPUT — the same model re-solved at the
        # ladder's own beta ±0.3, bounded by the engine's beta limits. Attached in the SAME
        # place and for the same reason as `average_risk` above, which it delegates to rather
        # than reimplementing: a withheld name carries `available: false` and the page prints
        # nothing, so a refusal cannot be undone by a sensitivity strip. Computed on this
        # single-name route and NOT in the engine payload, because the engine payload is also
        # built 1,500 times by a scan and this costs two extra valuations.
        try:
            from . import beta_sensitivity as _bsens
            payload["beta_sensitivity"] = _bsens.strip(result, cfg=CONFIG)
        except Exception:                                                   # noqa: BLE001
            payload["beta_sensitivity"] = {"available": False,
                                           "reason": "the sensitivity could not be computed"}
        return jsonify(payload)
    except Exception as e:
        log_exception()
        return jsonify({"error": f"Valuation failed for {ticker}: {safe_error(e)}"}), 500


@app.route("/api/ai-analysis", methods=["POST"])
def api_ai_analysis():
    """Item 52 part 6. The analysis, served from today's store or run once and stored.

    **POST, NOT GET, AND THE VERB CARRIES THE SPEND.** A GET that could start a 27-second
    paid call is reachable by a retry, a prefetch, a crawler or a pasted link -- the
    `track-row` defect, where the recorded cure was to split the verb, and here the thing on
    the other side costs money rather than a record.

    **A CACHE HIT IS FREE AND INSTANT AND DOES NOT TOUCH THE CAP.** Keyed on ticker and day,
    so the second visitor to a name pays neither the 27 seconds nor the 2.5 cents.

    **WHEN THE DAY'S ALLOWANCE IS GONE IT OFFERS THE BUTTON RATHER THAN SHOWING NOTHING** --
    `force` runs one anyway. That is deliberate and it is not a hole in the cap: the cap
    exists to stop an unattended page spending the month in an afternoon, and a reader who
    clicks is not unattended. Forced runs are charged to the ledger like any other, so the
    day's total still tells the truth about what was spent.
    """
    data = request.get_json(force=True) or {}
    ticker = (data.get("ticker") or "").strip().upper()
    if not ticker:
        return jsonify({"error": "No ticker provided."}), 400
    force = bool(data.get("force"))
    try:
        from . import ai_auto as AA

        # ITEM 53 part 5: A CACHE HIT IS SERVED TO EVERYONE. It costs nothing to show again
        # -- the owner already paid for it and the file is already on disk -- so refusing a
        # public reader the cache was refusing something free. No ownership check here, and
        # that is the change.
        hit = AA.cached(ticker)
        if hit:
            return jsonify({"ok": True, "ticker": ticker, "cached": True, "ran": False,
                            "ai": hit.get("analysis"), "label": AA.PANEL_LABEL,
                            "recent": hit.get("recent") or {},
                            "allowance": AA.allowance(), "cost_usd": hit.get("cost_usd")})

        # ...AND A NEW ONE IS THE OWNER'S TO BUY. Everything past this line can start a paid
        # call, so this is where the gate sits now that the route itself is public.
        #
        # DEFAULT-DENY: `getattr(g, "may_spend_ai", False)` treats an unset flag as a refusal.
        # That matters because the flag is set by the SaaS layer's `_guard`, and the inner app
        # is importable and runnable on its own (every test client does it) -- so the failure
        # mode of "this ran somewhere the guard does not" must be "nothing is bought".
        if not _may_spend_ai():
            return jsonify({
                "ok": True, "ticker": ticker, "cached": False, "ran": False, "ai": None,
                "label": AA.PANEL_LABEL, "owner_only_to_run": True,
                "reason": ("There is no saved analysis for this company today. Running a new "
                           "one costs money, so only the owner can start it."),
            })

        allow = AA.allowance()
        if not allow["may_run"] and not force:
            return jsonify({"ok": True, "ticker": ticker, "cached": False, "ran": False,
                            "ai": None, "label": AA.PANEL_LABEL, "allowance": allow,
                            "capped": True, "offer": AA.CAP_REACHED,
                            "reason": allow["reason"]})

        # ITEM 53 part 2: VALUED WITHOUT THE AI, THEN ANALYSED WITH THE RECENT BLOCK.
        # `run_ai=True` would call the analyst from inside the pipeline, where the earnings
        # and headlines are not in scope -- threading them through `value_ticker` and
        # `value_from_company` would put a presentation fetch into the engine's signature.
        # Calling the analyst here instead keeps the engine unchanged and gives the route the
        # one thing it needs: control over what the model is shown.
        result = value_ticker(ticker, CONFIG, run_ai=False, mc_trials=2000)
        _cd = getattr(result, "company", None)
        if getattr(_cd, "fetch_failed", False):
            return jsonify({"ok": False, "ticker": ticker, "reason": "ticker not found"}), 404
        _recent = {}
        try:
            _recent = _recent_block(ticker, name=getattr(_cd, "name", "") or "")
        except Exception:                                                   # noqa: BLE001
            # The analysis is still worth having without the recent block; `_recent_facts`
            # returns "" for an empty dict, so the prompt falls back to exactly what item 52
            # sent. A failed free feed must not cost the paid call.
            _recent = {}
        try:
            from ..ai.analyst import analyze as _analyze
            result.ai = _analyze(result, CONFIG, recent=_recent)
        except Exception:                                                   # noqa: BLE001
            result.ai = None
        ai = getattr(result, "ai", None)
        if not ai:
            # THE WARNING THE ENGINE ALREADY WROTE IS WHAT IS REPORTED, rather than a fresh
            # guess at why. `value_ticker` appends "AI analysis unavailable: <reason>" and
            # that reason is the one worth a reader's time. NOTHING IS CHARGED to the day: no
            # analysis was stored, so the allowance is intact.
            why = [w for w in (getattr(result, "warnings", None) or [])
                   if "AI analysis unavailable" in str(w)]
            return jsonify({"ok": False, "ticker": ticker, "cached": False, "ran": True,
                            "ai": None, "label": AA.PANEL_LABEL, "allowance": AA.allowance(),
                            "reason": (why[0] if why else "the analysis came back empty")})

        wrote = AA.record(ticker, ai, recent=_recent)
        return jsonify({"ok": True, "ticker": ticker, "cached": False, "ran": True,
                        "forced": force, "ai": ai, "label": AA.PANEL_LABEL,
                        "recent": _recent,
                        "allowance": AA.allowance(),
                        "cost_usd": (ai.get("usage") or {}).get("cost_usd"),
                        "stored": wrote["ok"], "store_reason": wrote["reason"]})
    except Exception as e:                                             # noqa: BLE001
        log_exception("api_ai_analysis")
        return jsonify({"ok": False, "ticker": ticker, "reason": safe_error(e)}), 500


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
                "score": r.score.score,
                # ITEM 52: `recommendation` is GONE, not renamed. The two reads that replace
                # it answer different questions and a consumer that wants a verdict will not
                # find one here, which is the point.
                "business_quality": r.score.business_quality,
                "business_quality_score": r.score.business_quality_score,
                "price_vs_model": r.score.price_vs_model,
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
    """The Valquo Index — THE BOOK IN FORCE, held since the last rebalance.

    **DON'S RULING, 2026-10-02.** Hot stocks and options are daily; the Index is not. It is the
    book formed at the last quarterly rebalance, held unchanged until the next one, and it is
    the same book the forward record measures against SPY and SPMO.

    **WHAT THIS ROUTE USED TO DO, AND WHY IT WAS WRONG.** It called
    `build_index(st.load_snapshot(st.latest_scan_date()))` on every request, so the holdings
    were rebuilt from each day's scan and changed daily — while the forward record beneath them
    tracked a fixed 86-name book formed 2026-07-30. Two different books under one name, which
    Don read as the Index having rebalanced. Measured: the bound record carries 86 positions
    formed 2026-07-30 from scan 2026-07-24, against a default `roth` config serving 25 names off
    today's scan.

    **THE DEFAULT IS NOW THE RECORD AND THE REBUILD IS A LABELLED PREVIEW.** `?preview=1` still
    returns the daily-rebuilt construction for planning, under `is_preview: true` and a
    `not_the_index` note. The route is already owner-only (`surfaces.is_owner_only`), so the
    preview is not a public surface; the label exists so a future reader of the payload cannot
    mistake one for the other.

    **NOTHING ABOUT CONSTRUCTION CHANGES.** `build_index` is untouched and is still the only
    thing that BUILDS a rebalance book — the Oct 22 runbook's `--config taxable` path is
    unaffected — and nothing the writer reads is modified. No scoring, no weight, no
    construction and no recorded figure moves, so this is NOT a vintage event.
    """
    from ..edge.valquo_index import build_index
    from ..screener import settings as S
    from ..screener.index_track import TRACKED_CONFIG
    # ITEM 21 -- THE DEFAULT WAS `DEFAULT_BOOK_CONFIG`, WHICH IS "roth", AND THAT IS WHAT THE
    # CARD RENDERED ABOVE THE CORRECT HOLDINGS.
    #
    # The book in force was right; the CONFIG BLOCK bolted to it was roth's, so the live header
    # read verbatim: "Tax-free (Roth/IRA): highest net alpha, full rotation, ~2-month rebalance
    # -- 85 of undefined eligible (undefined scored) ... backtested net Sharpe 1.10, net excess
    # over the equal-weighted universe 11.6%". Every clause was wrong about the Index: it is
    # QUARTERLY with a 30% no-trade band, and those are the research decile's figures.
    #
    # `DEFAULT_BOOK_CONFIG` is a UI preference for which account type to show FIRST. The book
    # the record is of is `TRACKED_CONFIG`. Session 74 made `summarize` stop reading the
    # preference for exactly this reason and this route was missed.
    name = (request.args.get("config") or TRACKED_CONFIG).lower()
    cfg = (S.BOOK_CONFIGS or {}).get(name)
    if not cfg:
        return jsonify({"error": f"unknown config {name!r}",
                        "known": sorted(S.BOOK_CONFIGS or {})}), 400
    st = _store()

    # ---------------------------------------------------------------- THE BOOK IN FORCE
    if not request.args.get("preview"):
        from ..screener import index_in_force as IF
        book = IF.attach_returns(IF.book_in_force())
        if not book.get("ok"):
            # A REFUSAL, NEVER A FALLBACK TO THE DAILY PICK. Serving the rebuild when the
            # record cannot be read is exactly the substitution this change exists to end:
            # it would look like the Index and be a different book.
            return jsonify({"empty": True, "config": name, "is_preview": False,
                            "message": ("The Index is the book in force from the bound "
                                        "record, and that record could not be read: %s"
                                        % book.get("reason")),
                            "disclaimer": RISK_DISCLAIMER})
        book["sector_mix"] = IF.sector_mix(book, st)
        # ITEM 21 -- the four display columns. See `IF.attach_labels` for why the hot
        # score arrives under a different key than the preview payload uses.
        IF.attach_labels(book, st)
        # THE SCORE BAND ON EACH HOLDING [item 76 §4, Don's ruling 2026-10-21]. Stamped HERE
        # and not inside `index_in_force`, because the band's label and cuts live in
        # `web/score_confidence.py` -- the module that owns the calibrated score copy -- and a
        # `screener/` module importing `web/` would be the one import direction this package
        # does not have anywhere else. `attach_labels` supplies `rank` and `n_scored`; this
        # turns them into the label. DISPLAY ONLY: the book is fixed and no weight moves.
        from . import score_confidence as _sc
        for _p in (book.get("positions") or []):
            if isinstance(_p, dict):
                _b = _sc.band_for(_p.get("rank"), _p.get("n_scored"))
                _p["score_band"] = _b["band"]
                _p["score_band_fraction"] = _b["fraction"]
        # THE FULL `config_block`, not a hand-rolled subset. Consumers already read
        # `config.rebalance_months` and friends off this payload, and replacing it with three
        # keys would break them for no gain -- the account type still describes how the NEXT
        # rebalance is built, which is exactly what the added note says.
        from ..edge.valquo_index import config_block as _cfg_block
        book["config"] = dict(_cfg_block(name, cfg))
        book["config"]["note"] = ("the account-type construction describes how the NEXT "
                                  "rebalance would be built; the book in force is whatever the "
                                  "last rebalance set, and is what these holdings are")
        book["available_configs"] = sorted(S.BOOK_CONFIGS or {})
        book["is_preview"] = False
        # ITEM 57 B1: THE RECORD'S PRICING HEALTH, ON THE CARD. Served from `index_mark` rather
        # than from `book_in_force`, which is deliberately fenced off from price-derived
        # concepts so an acquisition and a vendor gap cannot become one thing. Derived from the
        # recorded `n_priced` column, so it costs no vendor call on this page load.
        try:
            from ..screener import index_mark as _im
            from ..screener import index_track as _it
            # THE ROWS FROM WHEREVER THEY LIVE. On the service the series is in the STORE, not
            # in the CSV -- the first cut read only the CSV and found nothing while
            # /api/index-track was serving 34 rows. `load` then `from_store` is the same
            # order the track card itself resolves in, so both surfaces read one series.
            _d = _it.load()
            _rows = _d.get("series") or []
            if not _rows:
                _rows = (_it.from_store(st) or {}).get("series") or []
            book["track"] = {"unpriced": _im.unpriced_run(
                rows=_rows, n_positions=book.get("n_positions"))}
        except Exception:                                              # noqa: BLE001
            book["track"] = {"unpriced": {"ok": False, "n_unpriced": 0, "alert": False,
                                          "reason": "the pricing-health check could not run"}}
        # ITEM 21 -- THE CARD'S OWN FACTS, SERVED RATHER THAN INFERRED. The JS was reading
        # `n_eligible` and `n_scored`, which belong to a SCAN and are absent from a held book,
        # so both rendered as the string "undefined". A held book's facts are how many it
        # holds, how many left, when it formed and when it next changes -- all of which
        # `book_in_force` already computed and nothing displayed.
        book["card"] = {
            "n_held": book.get("n_positions"),
            "n_exited": book.get("n_exited"),
            "exited": [p.get("ticker") for p in (book.get("positions") or [])
                       if p.get("status") == "exited"] or None,
            "formed_on": book.get("formed_on"),
            "next_rebalance": book.get("next_rebalance"),
            "next_rebalance_basis": book.get("next_rebalance_basis"),
            "held_since_days": book.get("held_since_days"),
            "cadence": IF.cadence_sentence(cfg),
            # NAMED SO A READER CANNOT TAKE IT FOR THE ACCOUNT TYPE. The construction below
            # describes how the NEXT rebalance is built; these holdings are what the LAST one
            # set, and the Index is one book rather than an account-type choice.
            "construction": name,
            "is_tracked_construction": name == TRACKED_CONFIG,
            "not_an_account_type": ("the Valquo Index is one book; the account types describe "
                                    "how a future rebalance would be built, not what is held"),
        }
        book["source_note"] = ("the book formed at the last rebalance and held unchanged "
                               "since — the same book the forward record tracks, not today's "
                               "scan")
        # DATED AGAINST THE BOOK'S OWN FORMATION, not against a scan. The scan-freshness
        # banner answers "is the ranking current", which is not a question about a held book —
        # pointing it at this payload would make a correctly-held book look stale every day.
        book["disclaimer"] = RISK_DISCLAIMER
        return jsonify(book)

    # ---------------------------------------------------------------- THE PREVIEW
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
    payload["is_preview"] = True
    payload["not_the_index"] = ("IF THE REBALANCE WERE TODAY. This is the construction applied "
                                "to today's scan for planning. It is NOT the Valquo Index: the "
                                "Index is the book in force from the bound record, which this "
                                "route returns by default.")
    payload["source_note"] = ("built from the same scan snapshot as the Hot Stocks ranking — "
                              "a preview of the next rebalance, not the book in force")
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
    # THE TRACKED CONSTRUCTION BY DEFAULT, not the site's default account type: this card puts
    # a backtest beside the RECORD, so the backtest has to be of the book the record is of.
    # An explicit `?config=` is still honoured for the owner-only preview of another account
    # type, and the payload names which construction it used.
    name = (request.args.get("config") or index_track.TRACKED_CONFIG).lower()
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
    # PT-SPMO — a REPORTED second benchmark, beside the SPY excess and never instead of it.
    # The contract binds SPY and only SPY, so this block is additive, carries its own label
    # and posture in the payload rather than relying on each surface to remember them, and is
    # read by nothing that computes a verdict. `available: False` with a reason is the normal
    # state on a service that has not recorded a comparison yet, and a surface with no claim
    # must print no claim.
    try:
        from ..screener import reported_benchmark
        out["reported_benchmark"] = reported_benchmark.claim()
        # The chart's third line. `attach_series` hangs the recorded SPMO level on the bound
        # rows that have one and adds nothing to the rows that do not, so the sibling's own
        # start date shows up as a gap in the line rather than as a flat stretch. It is a
        # READ of the sibling: this route writes nothing, and a test byte-compares the file
        # across a request to keep it that way.
        reported_benchmark.attach_series(out)
    except Exception:                                    # noqa: BLE001
        pass                        # a reported benchmark must never break the bound card
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
        # MA53 sweep: this was a bare `float(...)`, so `?risk_budget=nan` parsed cleanly and
        # propagated into position sizing, where every comparison against it is False and the
        # downstream guards therefore read as satisfied. Owner-only, so not a public hole —
        # fixed as the same class rather than left because the blast radius is small.
        _default_budget = (getattr(CONFIG, "options_risk_per_trade", None)
                           or DEFAULT_RISK_BUDGET)
        # The bounds are DOLLARS, not a fraction: DEFAULT_RISK_BUDGET is $1,000 per signal.
        # Writing this as a 0..1 range would have clamped the shipped default to 1.0 and
        # silently re-sized every alert — a clamp is only safe once its units are checked.
        budget = clamp_float(request.args.get("risk_budget"),
                             default=_default_budget, lo=1.0, hi=1_000_000.0)
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
    # ITEM 54 PART 3 — MARK A NAME SCORED ON TOO FEW THEMES. A DISPLAY STAMP ONLY: additive
    # fields, no score and no rank recomputed, and `build_index` is not involved at all.
    #
    # Counted over the WHOLE snapshot and not only the served slice, because the census the
    # page prints ("N of the scan") is a statement about the scan.
    from ..screener import thin_data as _thin
    _thin_census = _thin.mark(rows)
    _thin_all = _thin.mark(all_rows)
    # ...and nothing implausible goes out with it. This estimator has no ceiling: its EV
    # bridge is `3 + 2 x (net debt / market cap)` times the price, so a leveraged name can
    # clear the valuation page's 5x refusal band on this PUBLIC surface while that page is
    # refusing the very same claim. One number, one meaning — the band is the page's own.
    # MA29 — the return value is the count of rows left withheld in the served slice, and it
    # used to be discarded here. It is NOT the third state: it increments for rows already
    # marked withheld at scan time as well as for band breaches, so it is the TOTAL. The third
    # state — a peer estimate that breached the band — is the withheld rows carrying no `kind`,
    # counted separately below. See `web/refusals.py`.
    _band_withheld = withhold.withhold_implausible_fair_values(rows)
    # THE LOW SIDE OF THE SAME BAND [item 76 §2, Don's ruling]. Flags, never withholds, and it
    # runs at the same site so the two sides of one band cannot reach different surfaces.
    _band_low = withhold.flag_implausibly_low_fair_values(rows)
    # THE CONFIDENCE CEILING BELOW HALF THE PRICE [item 79 s1, Don's ruling 2026-10-22].
    # Third pass at the same site, for the same reason the second one is here: the three
    # consequences of one price ratio must not be able to reach different surfaces.
    _capped_conf = withhold.cap_confidence_below_half(rows)
    from ..engine.publication import ROW_WITHHELD as _RW, ROW_WITHHELD_KIND as _RWK
    _peer_only = sum(1 for r in rows
                     if isinstance(r, dict) and r.get(_RW) and not r.get(_RWK))
    scans = st.list_scans()
    meta = next((s for s in scans if s["scan_date"] == scan_date), {})
    # THE SCORE BAND [item 76 §4, Don's ruling 2026-10-21]. Stamped on the served rows so a
    # list can show "top 10%" rather than a per-name score. DERIVED from the row's own rank
    # against this scan's own `scored` count -- the renderer never computes it and the cuts are
    # never typed there. DISPLAY ONLY: no score, rank or sort position changes.
    from . import score_confidence as _sc
    _scored_n = meta.get("scored")
    for _r in rows:
        if isinstance(_r, dict):
            _b = _sc.band_for(_r.get("rank"), _scored_n)
            _r["score_band"] = _b["band"]
            _r["score_band_fraction"] = _b["fraction"]
    try:
        params = _json.loads(meta.get("params") or "{}")
    except Exception:
        params = {}
    from ..screener.freshness import status as _freshness

    def _source_label(health, configured):
        """The derived source label. Never raises: a label must not break the hot list."""
        try:
            from ..screener.providers import served_by
            return served_by(health, configured)
        except Exception:                                    # noqa: BLE001
            return None

    # MA30 — churn disclosure. Additive: it annotates `rows` with `tenure_scans` and never
    # reorders or drops one. Sorting or filtering on this field converts a disclosure into a
    # screen and needs its own register (see web/tenure.py); `tests/test_tenure.py` fails if
    # anyone does. Fail-soft by construction, so it cannot break the public hot list.
    from . import tenure as _tenure
    tenure_block = _tenure.annotate(rows, st)
    # MA29 — "what the model cannot value", said out loud. READS the scan's own
    # `publication_audit` rather than recounting: one number, one meaning. Fail-soft, so a
    # snapshot saved before that block existed reports `available: false` and no sentence
    # rather than a confident "0 refused".
    from . import refusals as _refusals
    _health = params.get("health")
    _health = _health if isinstance(_health, dict) else {}
    refusals_block = _refusals.block(
        _health.get("publication_audit"), scan_date=scan_date,
        displayed=len(rows), display_withheld=_band_withheld,
        display_peer_only=_peer_only)
    # MA28-CARD — the accounting red-flag crash statistic, disclosed rather than applied.
    # READ-ONLY over `rows`: it counts how many could be scored (zero, and the count is measured
    # per request rather than assumed) and returns a block. It annotates no row, reorders none
    # and drops none — `tests/test_accounting_risk.py` fails if that stops being true, on the
    # same rule `tenure.py` and `refusals.py` carry: a disclosure that touches the rows has
    # become a screen and needs its own register.
    from . import accounting_risk as _acct_risk
    accounting_block = _acct_risk.block(rows)
    return jsonify({
                    # ITEM 54 part 3: the rule, the wording and the counts, so the page
                    # states the rule rather than implementing one of its own.
                    "thin_data": {**_thin_census,
                                  "scan_n_thin": _thin_all.get("n_thin"),
                                  "scan_n_rows": _thin_all.get("n_rows"),
                                  "scan_n_uncountable": _thin_all.get("n_uncountable")},
                    "scan_date": scan_date, "rows": rows, "tenure": tenure_block,
                    "refusals": refusals_block,
                    "accounting_risk": accounting_block,
                    "sectors": sector_attractiveness(all_rows),
                    "universe_size": meta.get("universe_size"), "scored": meta.get("scored"),
                    "provider": meta.get("provider"), "filtered": params.get("filtered"),
                    # E8 -- the DERIVED source label, beside the configured one. Computed here
                    # rather than persisted at scan time so that snapshots already on disk get
                    # the honest label too: the census was always stored, it was simply never
                    # consulted by the thing that named the source. `measured: False` on a
                    # snapshot that kept no census, so a surface can tell a reading from a
                    # default.
                    "source": _source_label(params.get("health"), meta.get("provider")),
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
#: What the last background refresh actually did, per source. Published on /api/track so a
#: refresh that fails is visible on the page instead of reading as "accruing" forever -- which is
#: exactly what happened for seven weeks while a tz-aware vendor date crashed every run inside a
#: bare `except: pass`. Per process, like `_PAPER_BENCH`; the store is the durable record.
_TRACK_REFRESH_STATUS = {}
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
            _TRACK_REFRESH_STATUS["paper_bench"] = {"ok": False, "reason": "SPY could not be priced"}
            return
        # Calendar dates, naive -- see `track._calendar_index`. A yfinance-served SPY parsed
        # tz-aware and every `searchsorted` below raised, so this block never produced a number.
        from ..edge.track import _calendar_index
        spy = pd.Series(c, index=_calendar_index(d))
        spy = spy[~spy.index.isna()]
        spy = spy[~spy.index.duplicated(keep="last")].sort_index()

        def at(date):
            i = spy.index.searchsorted(pd.to_datetime(str(date)[:10]))
            return spy.iloc[min(i, len(spy) - 1)] if len(spy) else None

        rt = 2.0 * CONFIG.paper_cost_bps / 1e4          # charge the strategy leg realistic cost
        alphas = []
        for p in allp:
            if not p.get("exit_date"):
                continue
            e, x = p.get("entry_price"), p.get("exit_price")
            # Same rule as positions.paper_summary: a "left coverage" close at exactly the entry
            # price was never re-priced, so its return is unknown -- not flat, and not an alpha.
            if ((p.get("exit_reason") or "").startswith("left coverage") and e is not None
                    and x is not None and float(e) == float(x)):
                continue
            b0, b1 = at(p["entry_date"]), at(p["exit_date"])
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
        # NO "significant" FLAG. It read `abs(t) > 2.0` -- the convention this project retired
        # (X7: noise clears 2.0 far more often than 5% of the time) -- on a handful of
        # overlapping, selected trades. The t-stat still ships, as a rough gauge, labelled so.
        _PAPER_BENCH[source] = {"avg_alpha": (sum(alphas) / len(alphas)) if alphas else None,
                                "n_alpha": len(alphas), "spy_all_time": spy_all, "since": first,
                                "t_stat": t_stat, "t_stat_note": (
                                    "naive t on closed picks; holds overlap and were selected, so "
                                    "this is a rough gauge, not a significance test"),
                                "net_of_costs": True}
        _TRACK_REFRESH_STATUS["paper_bench"] = {"ok": True, "n_alpha": len(alphas)}
    except Exception as e:                                              # noqa: BLE001
        _TRACK_REFRESH_STATUS["paper_bench"] = {"ok": False, "reason": type(e).__name__}


def _track_counts(st, source) -> dict:
    """How much has been LOGGED, and how much has MATURED -- the two numbers the card needs.

    The card used to print the length of the 15-row "recent" list as "N logged so far", so a
    log running back to early August read as fifteen picks.
    """
    picks = st.all_track_picks(source) or []
    dates = sorted({str(p.get("run_date") or "")[:10] for p in picks if p.get("run_date")})
    # E10 -- HOW MANY ROWS SIT ON DAYS THE MARKET WAS SHUT. The logger used to write on a
    # holiday (`track.log_picks` now refuses), and the rows it already wrote are LABELLED
    # rather than deleted: the record keeps what it recorded and says what it is. The count is
    # computed on READ, so it covers rows written before the guard existed -- and it is a
    # DISCLOSURE, so it never drops a pick or changes a return.
    closed, n_closed_rows = [], 0
    try:
        import datetime as _d
        from ..screener.market_session import is_trading_day
        for ds in dates:
            try:
                if not is_trading_day(_d.date.fromisoformat(ds)):
                    closed.append(ds)
            except Exception:                                # noqa: BLE001
                continue
        shut = set(closed)
        n_closed_rows = sum(1 for p in picks
                            if str(p.get("run_date") or "")[:10] in shut)
    except Exception:                                        # noqa: BLE001
        closed, n_closed_rows = [], 0
    return {"n_logged": len(picks), "n_days": len(dates),
            "first_logged": dates[0] if dates else None,
            "last_logged": dates[-1] if dates else None,
            "n_non_trading_days": len(closed),
            "n_rows_on_non_trading_days": n_closed_rows,
            "non_trading_days": closed[:12],
            "n_matured_21": len(st.track_returns(source, 21) or [])}


def _recent_track_picks(st, source, n=15):
    picks = sorted(st.all_track_picks(source), key=lambda p: p.get("run_date") or "", reverse=True)[:n]
    rets = {(r["run_date"], r["ticker"]): r for r in st.track_returns(source, 21)}
    out = []
    for p in picks:
        r = rets.get((p.get("run_date"), p.get("ticker")))
        out.append({"date": p.get("run_date"), "ticker": p.get("ticker"),
                    "ret_1m": (r["fwd_ret"] if r else None), "bench_1m": (r["bench_ret"] if r else None)})
    return out


#: Seconds between refresh STEPS. Short because a step is now bounded work, not a whole cycle.
_TRACK_STEP_GATE_S = 30


def _maybe_refresh_track():
    """Advance the forward-return refresh by one BOUNDED, RESUMABLE step.

    **WHAT THIS REPLACED, AND WHY IT NEVER FINISHED.** The old version held a 12-hour gate and
    the status in module globals, then spawned a daemon thread that scored all ~410 picks in one
    pass with a per-name price fetch. Three separate properties made that unfinishable and all
    three were needed: the gate and cursor died with the process, so every deploy started again
    from nothing; the work was unbounded, so it could not complete between deploys; and the
    per-name fetch paid the dead primary's timeout on every name. Measured on the service
    2026-09-30: **3 of 410 picks scored by 06:51Z across seven deploys**, with `refresh` null on
    every response because the status global was empty in each fresh process.

    Now: the cursor lives in the store (`track.refresh_step`), each call does at most
    `REFRESH_BUDGET` picks, and the prices come from the batch fetcher. A deploy costs at most
    the current slice instead of the whole cycle.

    The short gate is deliberate. It is no longer protecting an expensive job from being
    re-entered -- it is only stopping two near-simultaneous requests doing the same slice twice,
    which is wasteful rather than wrong (`_score_pick` skips horizons already stored).
    """
    import threading
    import time
    now = time.time()
    if now - _LAST_TRACK_REFRESH[0] < _TRACK_STEP_GATE_S:
        return
    _LAST_TRACK_REFRESH[0] = now

    def _work():
        from ..edge import track
        st = _store()
        for src in ("hot10", "options"):
            try:
                track.refresh_step(st, src)
            except Exception:                                           # noqa: BLE001
                log_exception()
        _compute_paper_bench(st, "hot10")
    threading.Thread(target=_work, daemon=True).start()


def _track_refresh_view(store, source: str) -> dict:
    """The refresh status, READ FROM THE STORE so it survives the process that produced it.

    `refresh` used to be a module global and was therefore `null` on every response from a
    freshly-deployed process -- which is exactly when a reader most wants to know the refresh is
    behind. Reporting `remaining` rather than only `done` is the same point: a cycle that is
    part-way through must not be indistinguishable from one that has not started.
    """
    from ..edge import track
    try:
        pr = track.refresh_progress(store, source)
    except Exception:                                                   # noqa: BLE001
        return None
    n, cur = pr.get("picks"), int(pr.get("cursor") or 0)
    return {"at": pr.get("last_at"), "cycle_started": pr.get("cycle_started"),
            "done_at": pr.get("done_at"), "computed": pr.get("computed"),
            "picks": n, "scored_so_far": cur,
            "remaining": (None if n is None else max(0, int(n) - cur)),
            "unpriced": len(pr.get("unpriced") or []), "failed": pr.get("failed", 0),
            "complete": bool(n is not None and cur >= int(n))}


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
                       "recent": _recent_track_picks(st, source),
                       "counts": _track_counts(st, source),
                       "refresh": _track_refresh_view(st, source)}
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
                            "P&L). These are model records with no money in them; the separate broker "
                            "sandbox paper account (simulated orders and fills on delayed data) is the "
                            "\u201cOptions (paper)\u201d figure in the live-track bar at the top of the "
                            "app. Educational only; past results don't predict future performance."})


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
    # ITEM 45 — WHICH FEED SERVED THESE ROWS. Tradier deactivated Don's account and the
    # Signals tab went on serving a frozen snapshot with nothing to say its source had died.
    # The label is read from the RUN that produced the rows (`intraday_runs.provider`), never
    # from the provider selected now, or a page served today would relabel yesterday's
    # real-time rows as delayed. `freshness` already says HOW OLD; this says WHAT FROM.
    from ..intraday.providers import delay_for_label
    meta = st.intraday_run(rt) or {}
    src = (meta.get("provider") or "").strip()
    feed = {"source": src or "unknown",
            "delay": delay_for_label(src),
            # A row set whose source was never recorded is reported as unknown rather than
            # assumed real-time -- every run before this item has no label, and guessing one
            # would put a number's provenance in the payload that nobody measured.
            "recorded": bool(src)}
    return jsonify({"run_time": rt, "rows": st.load_intraday(rt, top=top),
                    "freshness": _freshness(str(rt)[:10], label="signal feed"),
                    "feed": feed,
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
