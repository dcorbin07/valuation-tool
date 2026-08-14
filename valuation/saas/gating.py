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

    Premium is granted, in priority order, to:
      1. recruiter/demo preview sessions (is_demo) — always, even after beta ends;
      2. owner emails (config OWNER_EMAILS) — permanent free Premium;
      3. every signed-in account while BETA_ALL_PREMIUM is on (the free beta);
      4. anyone with a genuinely active paid subscription.
    Flip BETA_ALL_PREMIUM=false (env) to end the free beta with no code change.

    OPEN_ACCESS overrides all of it: the full product for everyone, account or not.

    PRIVATE_MODE overrides even that, in the other direction: the owner gets everything and
    everyone else gets the "anon" stub, including demo sessions and (unlike every rule below)
    signed-in accounts. `app_saas._guard` refuses non-owners long before this runs, so this is
    defence in depth rather than the enforcement point — but a tier function that hands out
    Premium to strangers whenever some other flag is set is exactly the kind of thing that
    turns a future refactor into a leak."""
    from ..config import CONFIG
    # 0a. Private mode — a personal tool. Deliberately the first rule, ahead of open access,
    #     the demo link and the beta grant, all three of which would otherwise unlock it.
    if CONFIG.private_mode:
        from .private import is_owner
        return "premium" if is_owner(user, CONFIG) else "anon"
    # 0b. Open access — deliberately ahead of the `not user` check, because that IS the
    #    point: an anonymous visitor gets the whole product, not the "anon" stub tier.
    if CONFIG.open_access:
        return "premium"
    if not user:
        return "anon"
    # 1. Recruiter master-link preview — independent of the beta flag so the
    #    link on the résumé keeps working forever.
    if user.get("is_demo"):
        return "premium"
    # 2. Owner.
    if user.get("email", "").strip().lower() in CONFIG.owner_email_set:
        return "premium"
    # 3. Free beta: everyone who signs up gets the full product.
    if CONFIG.beta_all_premium:
        return "premium"
    # 4. Real paying subscribers.
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
    from ..config import CONFIG
    tier = _active(user)
    feats = features(tier if tier != "anon" else "free")

    # Edge Lab stays private even under open access: it's the owner's research bench,
    # not a withheld product feature. Nothing a *user* would want is behind this.
    if path.startswith("/api/edge/"):
        owner = bool(user) and user.get("email", "").strip().lower() in CONFIG.owner_email_set
        # A demo/preview session READS the bench (PROMPT_recruiter_master_link.md,
        # 2026-08-07): the Edge Lab is the most interesting thing a recruiter can be shown,
        # and it publishes derived statistics Don computed, never a vendor row. The three
        # POST runners stay shut — they recompute, they write, and they spend the budget.
        # `surfaces.DEMO_DENIED_PATHS` already refuses them in `_guard` before this runs;
        # the method test here is the second, independent line of that defence.
        #
        # PUBLIC_FULL_VIEW (2026-08-13) joins the demo session on the SAME single read, and
        # this is the SECOND gate that had to learn it. The flag was wired into
        # `surfaces.check` and not here, so an anonymous visitor passed the surface split,
        # reached `/api/edge/learning`, and was refused by this line instead — and because
        # `switchTab` auto-calls `edgeLearning()` for any session without the runner buttons,
        # the Edge Lab tab opened onto a red "Owner-only research tools." bar. A gate the
        # ungating did not know about is exactly the failure a THREE-gate stack invites, and
        # the first ungating's tests missed it because they exercised `surfaces` as a pure
        # function plus two non-`/api/edge/` routes end to end.
        #
        # Scoped to the IDENTICAL path and method as the demo session, deliberately: the flag
        # means anonymous == demo, so widening this to `/api/edge/` generally would make an
        # anonymous visitor strictly WIDER than the preview it is supposed to equal. The three
        # POST runners stay shut for both, here and in `surfaces.DEMO_DENIED_PATHS`.
        from .surfaces import public_full_view
        read_tier = (bool(user) and bool(user.get("is_demo"))) or public_full_view(CONFIG)
        demo_read = path == "/api/edge/learning" and method == "GET" and read_tier
        if not (owner or demo_read):
            return ({"error": "Owner-only research tools.", "owner_only": True}, 403)

    # Private mode: the only caller that gets this far is the owner (see _guard), and the
    # owner has no tier caps, no daily valuation limit and nothing to upgrade to. Skipped
    # wholesale for the same reason open access skips it — every rule below describes a
    # commercial product that is switched off.
    if CONFIG.private_mode:
        return None

    # Open access: no login wall, no feature locks, no usage caps. Everything below this
    # line exists only for the paid product, and is skipped wholesale.
    if CONFIG.open_access:
        return None

    # Login required for any /api that isn't public reads.
    # /api/valquo-index is the constructed top-slice of the SAME ranking
    # /api/hotstocks serves, so it is a public read for exactly the same reason —
    # login-walling one view of a ranking while the other is open makes no sense.
    public = path in ("/api/health", "/api/hotstocks", "/api/track",
                      "/api/valquo-index")
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
