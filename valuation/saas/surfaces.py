"""
The public / owner split — which surfaces a stranger may read on a PUBLIC instance.

WHY THIS EXISTS AS ITS OWN MODULE
---------------------------------
`private.py` answers "may anyone other than the owner use this instance at all?" Since
2026-08-04 the answer is yes: Valquo is public and free to anyone, forever, with no billing
and no accounts. That makes a second, narrower question the important one — "which surfaces
create a liability or a licence problem when a stranger reads them?" — and it needs its own
answer in one file, for the same reason the lockdown did: a policy spread across a dozen
templates is a policy nobody can audit.

THE THREE REASONS A SURFACE IS OWNER-ONLY
-----------------------------------------
1. **It is a performance claim.** The forward paper track, its equity curve, the paper option
   book. These are real forward records, but they are a SANDBOX PAPER ACCOUNT with no real
   money, and any number that can be read as "what Valquo returned" is a claim a free
   educational site should not be making at all.
2. **It is an actionable live pick.** The constructed Index book, live scream-buy options
   alerts with a specific contract, the intraday signal feed, the portfolio builder. A ranking
   is analysis; "hold these fifteen names at these weights, today" is a recommendation.
3. **It is backtest or vendor internals.** The Edge Lab, the backtest runners, the learning
   log. These read Sharadar and ThetaData, whose individual plans permit personal use and
   forbid redistribution. Derived summary statistics Don computed are his and may be published
   (that is what the portfolio page does); rows and per-name internals are not.

WHAT THIS MODULE DOES NOT DO
----------------------------
It does not replace `private.check` (which still runs first when the lockdown is on), the
admin-token check, CSRF, or the tier system. It sits between them and answers one question,
and — like `private.py` — it is a pure function of (path, user, cfg) so that "prove the split
holds" is a unit test rather than a browser session.

FAILURE MODE, DELIBERATELY CHOSEN
---------------------------------
This is an explicit DENY list, not an allowlist, which is the opposite of `private.py`. That
is a considered trade: under the lockdown, forgetting a route meant leaking the book, so it
had to fail closed. Here, forgetting to list a route means a new ANALYTICAL surface is public
by default, and the surfaces that matter are enumerated, stable, and pinned by a test that
walks the app's own URL map. `PUBLIC_API` below records the other half explicitly, so the test
can assert that every registered /api route is knowingly on one side or the other — a new
route lands in neither list and fails the suite until someone decides.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------------------
# OWNER-ONLY. Each entry names its reason (1/2/3 above) and the vendor behind its numbers.
# ---------------------------------------------------------------------------------------
OWNER_ONLY_PATHS = frozenset({
    # (1) Performance claims — the Tradier SANDBOX paper track. No real money, ever.
    "/api/track",             # forward record + paper account + paper_sandbox block  [Tradier sandbox / FMP]
    "/api/index-track",       # the Index's live equity curve vs SPY                  [Tradier sandbox / FMP]
    "/api/options-paper",     # the paper option book vs its backtest reference       [Tradier sandbox / ThetaData ref]
    "/api/options-scorecard",  # expectancy of closed alerts                          [broker fills / ThetaData ref]

    # (2) Actionable live picks.
    "/api/valquo-index",      # the constructed book: names AND weights, today        [FMP]
    "/api/options-alerts",    # a specific contract, a size, a risk budget            [Tradier chains]
    "/api/signals",           # the intraday scream-buy feed                          [Tradier / free stack]
    "/api/signals/run",       # ...and triggering it (also a real cost per call)      [Tradier / AI]
    "/api/portfolio",         # n names at weights with a sector cap — an allocation  [FMP, via the snapshot]

    # (3) Backtest / vendor internals, and the expensive triggers.
    "/api/backtest/run",      # price-history backtest runner                         [FMP / yfinance]
    "/api/scan/run",          # triggers a market scan; burns vendor quota            [FMP / yfinance]
})

#: Everything under these is owner-only. `/api/edge/` is the research bench — the Edge Lab,
#: the adopted-weight learning log, and the fundamental-backtest metadata, which is the one
#: place Sharadar-derived output reaches an HTTP route.
OWNER_ONLY_PREFIXES = ("/api/edge/",)

# ---------------------------------------------------------------------------------------
# PUBLIC. Listed explicitly so the split is a decision rather than an omission — a route in
# neither set fails `test_public.py` until someone puts it in one.
# ---------------------------------------------------------------------------------------
PUBLIC_API = frozenset({
    "/api/health",            # config booleans, no market data                       [none]
    "/api/value",             # the DCF for one ticker the visitor asked for          [FMP]
    "/api/rank",              # score a small watchlist                               [FMP]
    "/api/hotstocks",         # the ranking — analysis, and the product               [FMP]
    "/api/whatdo",            # one name across the product; book/options half is
                              # stripped for non-owners inside `unified.name_view`    [FMP]
    "/api/tickers",           # local typeahead, no network                           [none]
    "/api/regime",            # market weather: 10Y, VIX, SPY vs its 200dma           [FMP / yfinance]
    "/api/export/excel",      # the visitor's own valuation, exported                 [FMP]
    "/api/export/pdf",        # ditto                                                 [FMP]
})

#: What an owner-only surface says when a stranger asks for it. It names the reason, because
#: "this is a paper account, not a track record" is exactly the thing a visitor should learn
#: from being refused — and because a bare 403 on a free site reads like a bug.
DENY_MESSAGE = ("This part of Valquo is owner-only. It shows a paper-account record and "
                "live model positions, which are not published: a free educational tool "
                "should not be making performance claims or handing out positions to take. "
                "The valuation tool, the ranking and the methodology are open to everyone.")


def enabled(cfg) -> bool:
    """Is the split on? The single read of the flag for policy purposes."""
    return bool(getattr(cfg, "owner_split", False))


def is_owner(user, cfg) -> bool:
    """Owner accounts only — deliberately the same rule as the lockdown's.

    Imported from `private` rather than re-implemented: two definitions of "owner" is how one
    of them ends up wrong. A demo/preview session is not an owner.
    """
    from .private import is_owner as _is_owner
    return _is_owner(user, cfg)


def is_owner_only(path: str) -> bool:
    """Path-level classification, independent of who is asking."""
    return path in OWNER_ONLY_PATHS or path.startswith(OWNER_ONLY_PREFIXES)


def may_see_owner_surfaces(user, cfg) -> bool:
    """The one question templates and views ask.

    With the split OFF this is true for everyone, which is what makes the flag a real revert
    rather than a partial one.
    """
    if not enabled(cfg):
        return True
    return is_owner(user, cfg)


def check(path: str, user, cfg):
    """None to allow. Otherwise a dict the caller renders — same shape as `private.check`.

    JSON for /api (the dashboard's own fetches read `owner_only` and hide their panel rather
    than printing an error), and a page refusal for anything else.
    """
    if not enabled(cfg):
        return None
    if not is_owner_only(path):
        return None
    if is_owner(user, cfg):
        return None
    if path.startswith("/api/"):
        return {"kind": "json", "status": 403,
                "payload": {"error": DENY_MESSAGE, "owner_only": True}}
    return {"kind": "page", "status": 403, "payload": {"message": DENY_MESSAGE}}
