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
    # Paper-account sell logic (the Track Record). Buy on entry to the top-N hot
    # list; hold at least min-hold days (no churn); sell when it leaves the list,
    # hits fair value, or reaches the max-hold time stop.
    paper_top_n: int = field(default_factory=lambda: int(_get_float("PAPER_TOP_N", 10)))
    paper_min_hold_days: int = field(default_factory=lambda: int(_get_float("PAPER_MIN_HOLD_DAYS", 30)))
    paper_max_hold_days: int = field(default_factory=lambda: int(_get_float("PAPER_MAX_HOLD_DAYS", 180)))
    # Owner accounts get permanent free Premium (comma-separated emails).
    owner_emails: str = field(default_factory=lambda: _get("OWNER_EMAILS", "donniecorbin6@gmail.com"))

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
    demo_access_token: str = field(default_factory=lambda: _get("DEMO_ACCESS_TOKEN", "preview"))

    @property
    def owner_email_set(self) -> set:
        return {e.strip().lower() for e in self.owner_emails.split(",") if e.strip()}

    @property
    def billing_enabled(self) -> bool:
        return bool(self.stripe_secret_key)

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
