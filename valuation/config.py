"""
Central configuration for the valuation tool.

Everything has a sensible default so the tool runs with ZERO setup.
Secrets / overrides are read from environment variables (or a local .env file
if python-dotenv is installed). Nothing here is required.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

# Optionally load a local .env file (never committed) so users can drop keys in.
try:  # pragma: no cover - convenience only
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # dotenv is optional
    pass


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "").strip())
    except (TypeError, ValueError):
        return default


@dataclass
class Config:
    # ------------------------------------------------------------------ #
    # AI qualitative layer (fully optional). Without a key the tool falls
    # back to transparent rule-based commentary and still works end to end.
    # ------------------------------------------------------------------ #
    anthropic_api_key: str = field(default_factory=lambda: _get("ANTHROPIC_API_KEY"))
    openai_api_key: str = field(default_factory=lambda: _get("OPENAI_API_KEY"))
    # "auto" picks Anthropic if a key is present, else OpenAI, else rule-based.
    ai_provider: str = field(default_factory=lambda: _get("AI_PROVIDER", "auto"))
    ai_model_anthropic: str = field(default_factory=lambda: _get("AI_MODEL_ANTHROPIC", "claude-sonnet-5"))
    ai_model_openai: str = field(default_factory=lambda: _get("AI_MODEL_OPENAI", "gpt-4o"))

    # ------------------------------------------------------------------ #
    # Optional paid market-data keys. If present they are preferred; if not,
    # the free stack (yfinance + SEC EDGAR + live Treasury) is used.
    # ------------------------------------------------------------------ #
    fmp_api_key: str = field(default_factory=lambda: _get("FMP_API_KEY"))
    alphavantage_api_key: str = field(default_factory=lambda: _get("ALPHAVANTAGE_API_KEY"))
    # Tradier (intraday signals watcher): real-time quotes + option chains.
    tradier_token: str = field(default_factory=lambda: _get("TRADIER_TOKEN"))
    tradier_env: str = field(default_factory=lambda: _get("TRADIER_ENV", "sandbox"))  # sandbox | live
    # SEPARATE Tradier PAPER (sandbox) credentials, used ONLY by the forward paper track
    # (valuation/edge/paper_broker.py). Deliberately not the same fields as `tradier_token` /
    # `tradier_env`: those are the live app's market-data feed and must keep pointing at
    # production. Splitting them means the paper track cannot be aimed at a real account by an
    # env typo, and flipping the app's feed cannot silently move the paper book.
    tradier_paper_token: str = field(default_factory=lambda: _get("TRADIER_PAPER_TOKEN"))
    tradier_paper_account_id: str = field(default_factory=lambda: _get("TRADIER_PAPER_ACCOUNT_ID"))
    # Contracts per paper option trade. 1 keeps the forward book on the same fixed-1-contract
    # basis the backtested scorecard uses, so paper and backtest expectancy are comparable.
    paper_contracts_per_trade: int = field(
        default_factory=lambda: int(_get_float("PAPER_CONTRACTS_PER_TRADE", 1)))
    # Edge Lab historical data source: free (default) | sharadar | wrds.
    edge_data_provider: str = field(default_factory=lambda: _get("EDGE_DATA_PROVIDER", "free"))
    sharadar_api_key: str = field(default_factory=lambda: _get("SHARADAR_API_KEY"))   # Nasdaq Data Link key
    wrds_data_dir: str = field(default_factory=lambda: _get("WRDS_DATA_DIR"))          # local CRSP/Compustat exports

    # SEC requires a descriptive User-Agent with contact info. Yours is nicer
    # to them but the default works.
    sec_user_agent: str = field(
        default_factory=lambda: _get("SEC_USER_AGENT", "valuation-tool research contact@example.com")
    )

    # ------------------------------------------------------------------ #
    # Global valuation defaults (all overridable per-run in the UI).
    # ------------------------------------------------------------------ #
    equity_risk_premium: float = field(default_factory=lambda: _get_float("EQUITY_RISK_PREMIUM", 0.050))
    default_risk_free: float = field(default_factory=lambda: _get_float("DEFAULT_RISK_FREE", 0.043))
    marginal_tax_rate: float = field(default_factory=lambda: _get_float("MARGINAL_TAX_RATE", 0.21))
    # Long-run terminal growth is capped at ~ the risk-free rate (a perpetuity
    # cannot outgrow the economy forever). We default the cap to 3.0%.
    terminal_growth_cap: float = field(default_factory=lambda: _get_float("TERMINAL_GROWTH_CAP", 0.030))
    montecarlo_trials: int = field(default_factory=lambda: int(_get_float("MONTECARLO_TRIALS", 10000)))

    # ------------------------------------------------------------------ #
    # SaaS / subscription mode (only used when running the hosted app).
    # ------------------------------------------------------------------ #
    secret_key: str = field(default_factory=lambda: _get("SECRET_KEY", "dev-insecure-change-me"))
    # DEV_MODE — opt-in, local-only conveniences that must NEVER be inferred from runtime
    # state. Today it gates exactly one thing: showing a password-reset link in the /forgot
    # response when SMTP isn't configured. That used to be inferred from "the send failed",
    # which meant a flaky prod mail server turned /forgot into an account-takeover endpoint
    # for any address (SECURITY_AUDIT.md C1). Default false; never set it in production.
    dev_mode: bool = field(default_factory=lambda: _get("DEV_MODE", "").lower() in ("1", "true", "yes", "on"))
    database_url: str = field(default_factory=lambda: _get("DATABASE_URL", "sqlite:///data/app.db"))
    stripe_secret_key: str = field(default_factory=lambda: _get("STRIPE_SECRET_KEY"))
    stripe_publishable_key: str = field(default_factory=lambda: _get("STRIPE_PUBLISHABLE_KEY"))
    stripe_webhook_secret: str = field(default_factory=lambda: _get("STRIPE_WEBHOOK_SECRET"))
    stripe_price_pro: str = field(default_factory=lambda: _get("STRIPE_PRICE_PRO"))
    stripe_price_premium: str = field(default_factory=lambda: _get("STRIPE_PRICE_PREMIUM"))
    stripe_price_pro_annual: str = field(default_factory=lambda: _get("STRIPE_PRICE_PRO_ANNUAL"))
    stripe_price_premium_annual: str = field(default_factory=lambda: _get("STRIPE_PRICE_PREMIUM_ANNUAL"))
    smtp_host: str = field(default_factory=lambda: _get("SMTP_HOST"))
    smtp_port: int = field(default_factory=lambda: int(_get_float("SMTP_PORT", 587)))
    smtp_user: str = field(default_factory=lambda: _get("SMTP_USER"))
    smtp_password: str = field(default_factory=lambda: _get("SMTP_PASSWORD"))
    email_from: str = field(default_factory=lambda: _get("EMAIL_FROM", "alerts@example.com"))
    public_base_url: str = field(default_factory=lambda: _get("PUBLIC_BASE_URL", "http://127.0.0.1:5000"))
    admin_token: str = field(default_factory=lambda: _get("ADMIN_TOKEN"))
    # Screaming-buy alerts: a Discord webhook (owner-level, posts to your channel)
    # and opt-in email. alert_min_score is the score bar a signal must clear to alert.
    discord_webhook_url: str = field(default_factory=lambda: _get("DISCORD_WEBHOOK_URL"))
    alert_min_score: float = field(default_factory=lambda: _get_float("ALERT_MIN_SCORE", 80))
    # Term-structure filter on scream-buy alerts (phase 3b: the only signal that survived the
    # fade gate). "flag" annotates every alert, "suppress" drops backwardation ones, "off"
    # restores the pre-3b behaviour. DEFAULT CHANGED to "suppress" (roadmap #21): it used to be
    # "flag" so that a ~60% cut in alert volume would be chosen rather than inherited, and it has
    # now been chosen - an unapplied filter leaves the live alerts carrying the full fade.
    # Missing term data is still never suppressed; see intraday/term_filter.py.
    options_term_filter: str = field(
        default_factory=lambda: os.environ.get("OPTIONS_TERM_FILTER", "suppress"))
    # Dollar risk per scream-buy options suggestion. Whole contracts only; an alert whose single
    # contract exceeds this is skipped rather than taken oversized.
    options_risk_per_trade: float = field(
        default_factory=lambda: _get_float("OPTIONS_RISK_PER_TRADE", 1000))
    # Paper-account sell logic (the Track Record). Buy on entry to the top-N hot
    # list; hold at least min-hold days (no churn); then SELL only when the name is
    # genuinely no longer hot (its hot score falls below paper_exit_score) or it
    # reaches its DCF fair value — NOT merely because it slipped out of the top-N
    # while another name got hotter. No time cap by default, so a gem can compound
    # for years (set PAPER_MAX_HOLD_DAYS>0 to force an eventual review).
    paper_top_n: int = field(default_factory=lambda: int(_get_float("PAPER_TOP_N", 10)))
    paper_min_hold_days: int = field(default_factory=lambda: int(_get_float("PAPER_MIN_HOLD_DAYS", 30)))
    paper_max_hold_days: int = field(default_factory=lambda: int(_get_float("PAPER_MAX_HOLD_DAYS", 0)))
    paper_exit_score: float = field(default_factory=lambda: _get_float("PAPER_EXIT_SCORE", 55))
    paper_max_weight: float = field(default_factory=lambda: _get_float("PAPER_MAX_WEIGHT", 0.20))
    # Realism: per-side transaction cost (bps) charged on the paper account's returns,
    # and a no-trade band so we don't churn on a name dipping a hair below exit_score.
    paper_cost_bps: float = field(default_factory=lambda: _get_float("PAPER_COST_BPS", 5))
    paper_exit_band: float = field(default_factory=lambda: _get_float("PAPER_EXIT_BAND", 3))
    # If a held name drops out of coverage (delisted/acquired) for this many days,
    # close it at its last price so dropped losers can't linger and bias the record.
    paper_coverage_gap_days: int = field(default_factory=lambda: int(_get_float("PAPER_COVERAGE_GAP_DAYS", 21)))
    # Whole-market scan: fetch this many names concurrently (big speedup; each fetch
    # is I/O-bound). Set SCAN_WORKERS=1 to force the old sequential behavior.
    scan_workers: int = field(default_factory=lambda: int(_get_float("SCAN_WORKERS", 8)))
    # How many names the live universe keeps after ranking by dollar liquidity (broker
    # source). 0 = the broker module's own default.
    universe_limit: int = field(default_factory=lambda: int(_get_float("UNIVERSE_LIMIT", 0)))
    # Hard ceiling on FMP requests in ONE scan. This subscription has no bulk endpoint, so
    # every uncached name costs 3 requests; without a ceiling a big universe can spend the
    # whole daily quota in a single run. 0 = unlimited.
    fmp_max_calls: int = field(default_factory=lambda: int(_get_float("FMP_MAX_CALLS", 0)))
    # AUDIT B7/G — BOTH OF THESE DEFAULTED **TRUE** WHILE THE BACKTEST FORCED THEM **FALSE**.
    # `screen.py` calls `build_frame(metrics)` with no keyword arguments, so the live hot list
    # inherited whatever these say. Sector-neutral ranking was tested on the full universe and
    # REJECTED in both held-out directions, then independently re-run on a later panel and
    # rejected again (it buys long-short t and sells top-decile alpha — the wrong trade for a
    # long-only book; see HANDOFF_sector_neutral.md). The code default was never flipped, so
    # unless SCREENER_SECTOR_NEUTRAL=false was set in the environment the product scored names
    # under the one intervention the research eliminated. Defaults now match the research.
    # Set either env var to "true" to A/B against whole-universe scoring.
    sector_neutral: bool = field(default_factory=lambda: _get("SCREENER_SECTOR_NEUTRAL", "false").lower() == "true")
    residual_momentum: bool = field(default_factory=lambda: _get("SCREENER_RESIDUAL_MOMENTUM", "false").lower() == "true")
    soft_bucket: bool = field(default_factory=lambda: _get("SCREENER_SOFT_BUCKET", "true").lower() != "false")
    # Feed EV/Sales + EV/EBITDA into the ESTABLISHED value branch too (they already feed the
    # speculative one). Default OFF pending the full-universe A/B — HANDOFF_growth_evsales.md.
    value_ev_multiples: bool = field(default_factory=lambda: _get("SCREENER_VALUE_EV_MULTIPLES", "false").lower() == "true")
    # Rebuild enterprise value at the REBALANCE date (PIT market cap + filing net debt) rather
    # than using the filing's own `ev`, whose embedded price is ~111 days stale. Affects
    # ebit_ev / ev_sales / ev_ebitda. Default ON since 2026-08-03: a correctness fix, adopted
    # because pricing half the value ratios at the rebalance date and half at a stale quote is
    # indefensible, NOT because it pays — it is a wash at book level. HANDOFF_ev_fix.md.
    # Set EDGE_EV_POINT_IN_TIME=false to get the old stale behaviour back.
    ev_point_in_time: bool = field(default_factory=lambda: _get("EDGE_EV_POINT_IN_TIME", "true").lower() != "false")
    # Historical backtest (Edge Lab) — ALL configured here, not on the data vendor's site.
    # Long window across regimes, but the optimizer weights recent history more (half-life)
    # and only adopts weights that also hold on the recent out-of-sample stretch.
    backtest_universe_limit: int = field(default_factory=lambda: int(_get_float("BACKTEST_UNIVERSE_LIMIT", 3000)))
    backtest_lookback_years: int = field(default_factory=lambda: int(_get_float("BACKTEST_LOOKBACK_YEARS", 18)))
    backtest_horizons: str = field(default_factory=lambda: _get("BACKTEST_HORIZONS", "63,252,756"))  # ~3mo, 1yr, 3yr holds
    backtest_rebalance_days: int = field(default_factory=lambda: int(_get_float("BACKTEST_REBALANCE_DAYS", 63)))
    backtest_top_n: int = field(default_factory=lambda: int(_get_float("BACKTEST_TOP_N", 25)))
    backtest_recency_halflife_years: float = field(default_factory=lambda: _get_float("BACKTEST_RECENCY_HALFLIFE_YEARS", 5))
    # Self-learning: a monthly, out-of-sample-gated re-tune of the screener's factor
    # weights from the tool's own accumulated snapshots + realized forward returns.
    # Adopts a change ONLY if it beats the current weights out-of-sample (no overfit).
    # Purely statistical — no LLM in the loop (the grid + hold-out test IS the decision).
    # Needs enough accrued history first, so early runs correctly decline to change anything.
    learn_enabled: bool = field(default_factory=lambda: _get("LEARN_ENABLED", "true").lower() != "false")
    learn_min_dates: int = field(default_factory=lambda: int(_get_float("LEARN_MIN_DATES", 8)))
    learn_horizon_days: int = field(default_factory=lambda: int(_get_float("LEARN_HORIZON_DAYS", 21)))
    learn_top_per_date: int = field(default_factory=lambda: int(_get_float("LEARN_TOP_PER_DATE", 60)))
    # Owner accounts get permanent free Premium (comma-separated emails).
    owner_emails: str = field(default_factory=lambda: _get("OWNER_EMAILS", "donniecorbin6@gmail.com"))

    # Optional SECOND FMP key used only by the backtest exporters.
    #
    # The live hot-list scan and the grades export both hit FMP, and on the free tier a
    # big export can eat the daily allowance the 22:23 UTC scan needs. Setting
    # FMP_BACKTEST_API_KEY (a second free account is enough) gives the research side its
    # own quota so the two can never starve each other. Falls back to the main key.
    fmp_backtest_api_key: str = field(default_factory=lambda: _get("FMP_BACKTEST_API_KEY", ""))

    @property
    def resolved_fmp_backtest_key(self) -> str:
        return self.fmp_backtest_api_key.strip() or self.fmp_api_key

    # Public contact shown in the footer / about, and where "Send feedback" points.
    # Both are env-overridable so the address can change without a code edit; the
    # feedback link defaults to a mailto: on the contact address (no form to host).
    contact_email: str = field(default_factory=lambda: _get("CONTACT_EMAIL", "donovan.corbin@valquo.co"))
    feedback_url: str = field(default_factory=lambda: _get("FEEDBACK_URL", ""))

    @property
    def resolved_feedback_url(self) -> str:
        """An explicit FEEDBACK_URL (e.g. a Google Form) wins; otherwise a prefilled
        mailto: to the contact address, which needs nothing hosted."""
        if self.feedback_url.strip():
            return self.feedback_url.strip()
        return (f"mailto:{self.contact_email}"
                "?subject=Valquo%20feedback&body=What%20were%20you%20doing%3F%0A%0A"
                "What%20did%20you%20expect%3F%0A%0AWhat%20happened%3F%0A")

    # ------------------------------------------------------------------ #
    # Beta launch switches. While True, the product is "everything unlocked,
    # free" so early users and recruiters get the full thing. Flip these to
    # false (env) when you're ready to start charging — no code change needed.
    # ------------------------------------------------------------------ #
    #   beta_mode          -> shows the "in beta / in development" banner site-wide.
    #   beta_all_premium   -> every signed-in account is treated as Premium, free.
    #   demo_access_token  -> the recruiter master-link. Anyone visiting
    #                         /demo/<token> gets an instant Premium preview with
    #                         NO signup. Keep it working forever (survives beta);
    #                         set it to something unguessable before you charge.
    beta_mode: bool = field(default_factory=lambda: _get("BETA_MODE", "true").lower() != "false")
    beta_all_premium: bool = field(default_factory=lambda: _get("BETA_ALL_PREMIUM", "true").lower() != "false")

    # PRIVATE_MODE — Valquo is a PERSONAL RESEARCH TOOL for the owner, not a product.
    #
    # This is a deliberate licence-compliance posture, not a soft launch. ThetaData's
    # Individual plan and Sharadar's individual terms are "personal use only, no
    # redistribution, no business use"; the Business equivalents are an order of magnitude
    # more expensive. One user, no commercial activity, no third party reading vendor-derived
    # numbers => those terms are cleanly satisfied. Anything that presents Valquo as a service
    # to other people — signup, checkout, tier copy, an anonymous visitor reading scores — is
    # what would break them, so all of it is switched off here rather than trimmed by hand.
    #
    # DEFAULT TRUE, and it OVERRIDES open_access / beta_all_premium / signup / billing rather
    # than being overridden by them: a lockdown that any other flag can silently undo is not a
    # lockdown. It is read in exactly two kinds of place — the derived properties just below
    # (which is why no template ever tests `private_mode` directly) and `saas/private.py`,
    # which owns the request-level policy.
    #
    # NOTHING IS DELETED. Every tier, route, template and Stripe path stays intact and tested,
    # so `PRIVATE_MODE=false` restores the public product exactly as it was — see
    # "Reversing this" in HANDOFF_appfixes.md.
    private_mode: bool = field(default_factory=lambda: _get("PRIVATE_MODE", "true").lower() != "false")

    # PORTFOLIO_PAGE — the ONE deliberate hole in private mode, and its own flag on purpose.
    #
    # Don job-hunts with this project as his portfolio piece, so he needs a single URL a
    # recruiter can open. That is a different question from "is Valquo a product", which is
    # what `private_mode` answers, so it gets a separate switch: the page can be on while the
    # whole rest of the instance stays locked to the owner, and turning it off later cannot
    # accidentally unlock anything else.
    #
    # It is safe to open ONLY because of what the page is: static prose about method, with
    # research statistics Don computed himself. It reads no store, calls no API and renders no
    # vendor row, so no ThetaData or Sharadar licence term is engaged by a stranger loading it
    # (that claim is pinned by tests, not asserted here). Everything a licence would care
    # about — scores, holdings, the Index, the track, any /api route — stays refused.
    #
    # PORTFOLIO_PATH is the URL. It is env-overridable so Don can move the page to something
    # unguessable without a code change, and validated (`resolved_portfolio_path`) because a
    # typo'd value here is the one way this flag could open more than one page.
    portfolio_page: bool = field(default_factory=lambda: _get("PORTFOLIO_PAGE", "true").lower() != "false")
    portfolio_path: str = field(default_factory=lambda: _get("PORTFOLIO_PATH", "/work"))

    # OPEN_ACCESS — Valquo is free and open: every feature available to everyone, no
    # account required, no checkout. This is a FLAG, not a deletion: all the tier,
    # gating and Stripe code is untouched, so OPEN_ACCESS=false restores the paid,
    # signup-required product exactly as it was. It goes further than
    # BETA_ALL_PREMIUM, which still required an account to sign in to.
    #
    # SUPERSEDED BY private_mode while that is on: "open to everyone" and "owner only" are
    # opposite answers to the same question. Read `public_access`, never this field, when the
    # question is "may a stranger see this?" — the raw field survives only so that turning
    # private mode off restores whatever the public product was configured to be.
    open_access: bool = field(default_factory=lambda: _get("OPEN_ACCESS", "true").lower() != "false")
    # NO DEFAULT, deliberately. This used to default to the literal "preview", which grants
    # a permanent Premium session to anyone who guesses /demo/preview. Harmless while
    # OPEN_ACCESS is true (everything is open anyway) and a free-Premium bypass the day you
    # start charging. Unset => /demo is disabled outright. SECURITY_AUDIT.md M4.
    demo_access_token: str = field(default_factory=lambda: _get("DEMO_ACCESS_TOKEN", ""))

    # FEATURE_BILLING — explicit override for the signup/pricing SURFACES (the nav "Pricing"
    # link, the "Get started" CTA, the /register and /pricing routes). Unset by default, in
    # which case it follows OPEN_ACCESS: while the product is open and free there is no paid
    # tier to advertise and no reason to push an account nobody needs.
    #   unset (default) -> surfaces follow OPEN_ACCESS
    #   "on"            -> force them visible (e.g. to test the paid flow while still open)
    #   "off"           -> force them hidden
    # Nothing is deleted: every route, template and Stripe path stays intact, so flipping
    # OPEN_ACCESS=false (or FEATURE_BILLING=on) restores the paid, signup-required product
    # exactly as it was.
    feature_billing: str = field(default_factory=lambda: _get("FEATURE_BILLING", ""))

    @property
    def owner_email_set(self) -> set:
        return {e.strip().lower() for e in self.owner_emails.split(",") if e.strip()}

    @property
    def public_access(self) -> bool:
        """May someone who is NOT the owner read this instance at all?

        The one question every access decision reduces to, so that no caller has to remember
        that private_mode outranks open_access. Under private mode the answer is no for
        everybody — signed-in-but-not-owner included, which is why this is not simply
        `open_access`.
        """
        return (not self.private_mode) and self.open_access

    #: Prefixes the portfolio page may never be mounted on. Each one is either an access
    #: boundary or a route that already exists, and a portfolio page sitting on top of one
    #: would either shadow it or hand its path an anonymous door. Flask keeps the FIRST rule
    #: registered for a path, so a collision would fail silently rather than loudly — which is
    #: exactly why this is checked here instead of being left to whoever sets the env var.
    _PORTFOLIO_RESERVED = ("/api", "/admin", "/static", "/login", "/logout", "/register",
                           "/forgot", "/reset", "/account", "/billing", "/app", "/demo",
                           "/alerts", "/pricing", "/terms", "/privacy", "/methodology",
                           "/robots.txt")

    @property
    def resolved_portfolio_path(self) -> str:
        """Where the portfolio page is mounted — validated, never trusted raw.

        Falls back to the default rather than raising: a bad PORTFOLIO_PATH should cost Don
        the URL he expected, not the whole deploy. The rejections that matter are "/" (which
        would put a public page on the app's own root) and anything under a reserved prefix.
        """
        p = (self.portfolio_path or "").strip()
        if p and not p.startswith("/"):
            p = "/" + p
        p = p.rstrip("/")
        if (len(p) < 2 or "<" in p or ">" in p
                or any(p == r or p.startswith(r + "/") for r in self._PORTFOLIO_RESERVED)):
            return "/work"
        return p

    @property
    def portfolio_page_enabled(self) -> bool:
        """One named read, so nothing else has to know the flag's name.

        Independent of `private_mode` in BOTH directions: the page can be open on a locked
        instance (its reason for existing), and turning it off never re-locks anything else.
        """
        return bool(self.portfolio_page)

    @property
    def signup_enabled(self) -> bool:
        """Show the signup + pricing surfaces at all?

        One named concept so templates never test `not open_access` directly and re-enabling
        is a single flag. LOGIN is deliberately NOT gated by this — existing accounts must
        still be able to sign in when new signups are hidden, and under private mode signing
        in is the ONLY way the owner reaches the tool.
        """
        # Private mode wins over an explicit FEATURE_BILLING=on: a personal tool has nobody to
        # sell to, and "force the pricing page visible" must not be a way around the lockdown.
        if self.private_mode:
            return False
        v = (self.feature_billing or "").strip().lower()
        if v in ("on", "true", "1", "yes"):
            return True
        if v in ("off", "false", "0", "no"):
            return False
        return not self.open_access

    @property
    def billing_enabled(self) -> bool:
        # While the product is open, there is nothing to sell: this hides the Stripe
        # checkout everywhere it's referenced without deleting any billing code, so
        # OPEN_ACCESS=false restores the paid flow exactly as it was.
        #
        # Under private mode NO payment can be initiated at all — checkout, the portal and the
        # webhook all refuse — regardless of whether Stripe keys happen to be configured. The
        # keys staying set is deliberate: reversing this must not require re-entering secrets.
        if self.private_mode:
            return False
        if self.open_access:
            return False
        return bool(self.stripe_secret_key)

    @property
    def beta_banner_enabled(self) -> bool:
        """The site-wide "you're exploring the full app, everything unlocked" strip.

        It is addressed to prospective users, so under private mode it is off: there is no
        beta, no launch and nobody being invited in.
        """
        return self.beta_mode and not self.private_mode

    @property
    def ai_enabled(self) -> bool:
        if self.ai_provider == "none":
            return False
        if self.ai_provider == "anthropic":
            return bool(self.anthropic_api_key)
        if self.ai_provider == "openai":
            return bool(self.openai_api_key)
        # auto
        return bool(self.anthropic_api_key or self.openai_api_key)

    @property
    def resolved_ai_provider(self) -> str:
        if self.ai_provider in ("anthropic", "openai", "none"):
            return self.ai_provider
        if self.anthropic_api_key:
            return "anthropic"
        if self.openai_api_key:
            return "openai"
        return "none"


CONFIG = Config()
