"""
Subscription gating — what each tier can do.

Free is a genuine, useful taste (a few full valuations a day, read the latest hot
list). Pro unlocks the heavy machinery (whole-market scans, backtest, portfolio
builder, exports, weekly email). Premium adds the factor-weight optimizer and API
access. All limits live here so pricing changes are a one-file edit.
"""
from __future__ import annotations

TIER_FEATURES = {
    "free": {
        "label": "Free", "valuations_per_day": 5, "whole_market": False, "backtest": False,
        "portfolio": False, "exports": False, "weekly_email": False, "optimizer": False, "api": False,
        "intraday": False, "hotstocks_top": 10,
    },
    "pro": {
        "label": "Pro", "valuations_per_day": 100, "whole_market": True, "backtest": True,
        "portfolio": True, "exports": True, "weekly_email": True, "optimizer": False, "api": False,
        "intraday": False, "hotstocks_top": 100,
    },
    "premium": {
        "label": "Premium", "valuations_per_day": None, "whole_market": True, "backtest": True,
        "portfolio": True, "exports": True, "weekly_email": True, "optimizer": True, "api": True,
        "intraday": True, "hotstocks_top": 500,
    },
}


def features(tier: str) -> dict:
    return TIER_FEATURES.get(tier or "free", TIER_FEATURES["free"])


def _active(user) -> str:
    """Effective tier — falls back to free if the subscription isn't active.
    Owner emails (config OWNER_EMAILS) always get Premium, free forever."""
    if not user:
        return "anon"
    from ..config import CONFIG
    if user.get("email", "").strip().lower() in CONFIG.owner_email_set:
        return "premium"
    if user.get("tier") in ("pro", "premium") and user.get("subscription_status") in ("active", "trialing", "comped"):
        return user["tier"]
    return "free"


# API path -> required boolean feature (None = login only). Body-sensitive rules
# are handled in check_request (e.g. whole-market scans).
_FEATURE_ROUTES = {
    "/api/backtest/run": "backtest",
    "/api/portfolio": "portfolio",
    "/api/export/excel": "exports",
    "/api/export/pdf": "exports",
    "/api/optimize/run": "optimizer",
    "/api/signals": "intraday",
    "/api/signals/run": "intraday",
}


def check_request(path: str, method: str, body: dict, user, store) -> tuple | None:
    """Return None to allow, or (payload_dict, status_code) to block."""
    tier = _active(user)
    feats = features(tier if tier != "anon" else "free")

    # Login required for any /api that isn't public reads.
    public = path in ("/api/health", "/api/hotstocks")
    if path.startswith("/api/") and not public and user is None:
        return ({"error": "Please sign in to use this.", "need_login": True}, 401)

    # Feature-locked routes.
    feat = _FEATURE_ROUTES.get(path)
    if feat and not feats.get(feat):
        return ({"error": f"{feat.replace('_', ' ').title()} is a paid feature.",
                 "upgrade": True, "tier": tier}, 402)

    # Whole-market scan needs 'whole_market'.
    if path == "/api/scan/run":
        if user is None:
            return ({"error": "Please sign in.", "need_login": True}, 401)
        if (body or {}).get("scope") == "whole_market" and not feats.get("whole_market"):
            return ({"error": "Whole-market scanning is a Pro feature. Upgrade to scan the full market.",
                     "upgrade": True}, 402)

    # Free-tier daily valuation limit.
    if path == "/api/value" and user is not None:
        limit = feats.get("valuations_per_day")
        if limit is not None:
            used = store.usage_today(user["id"], "valuation")
            if used >= limit:
                return ({"error": f"Daily limit reached ({limit} valuations on the {feats['label']} plan). "
                         "Upgrade for more.", "upgrade": True}, 402)
            store.bump_usage(user["id"], "valuation")
    return None
