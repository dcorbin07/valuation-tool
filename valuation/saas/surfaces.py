"""
The public / demo / owner split — which surfaces a stranger may read on a PUBLIC instance.

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

THE THIRD SIDE: THE DEMO SESSION (added 2026-08-07, PROMPT_recruiter_master_link.md)
------------------------------------------------------------------------------------
Don's decision, recorded so nobody re-litigates it from the code alone: the recruiter
master-link (`/demo/<token>`, and the button on `/work` that carries it) opens the full
READ-ONLY owner view — Track Record, the Index, Signals, the Edge Lab. He wants recruiters
to see the tool that exists rather than the public half of it, the link goes on his résumé,
and he has accepted in writing that a button on a public page makes that view effectively
one click deep. The mitigations that make it acceptable are all here or next to it:

  * READ-ONLY. `DEMO_DENIED_PATHS` below is the enforcement, and it is deliberately NOT
    gated on `owner_split`: "a preview session must not change anything" is a different
    policy from "strangers must not read the paper track", and flipping OWNER_SPLIT=false
    must never hand a résumé link the scan trigger or the account page.
  * NO RAW VENDOR ROWS. The owner surfaces the demo gains publish derived statistics Don
    computed (adopted weights, ICs, the backtest summary block, expectancy) — the standing
    posture line. Nothing under `/api/edge/` returns a Sharadar or ThetaData row; the three
    POST runners that would COMPUTE new ones are denied above.
  * THE DISCLAIMERS ARE UNCHANGED, because the demo view IS the owner view: the same
    templates, the same paper/not-advice framing, rendered by the same code path.

A demo session is still NOT an owner. `is_owner` is unchanged, `private.is_owner` still
refuses it outright under the licence lockdown, and `/demo` is refused there too.

THE FOURTH SIDE, AND IT IS TEMPORARY: PUBLIC_FULL_VIEW (added 2026-08-13)
------------------------------------------------------------------------
Don's decision, recorded verbatim because the code cannot justify itself here:

    "/app must be 100% ungated - I know the risks - I've submitted applications with the
     non-master link; when I hear back we regate."

He sent applications carrying the plain `/app` URL rather than the master link, so recruiters
are arriving at the public half and seeing a fraction of the tool. `PUBLIC_FULL_VIEW=true`
makes an ANONYMOUS visitor equivalent to a DEMO session — the same read-only full view the
`/work` button already grants, and nothing beyond it.

It reuses the demo rail entirely rather than adding a parallel one, which is what keeps the
blast radius small: `DEMO_DENIED_PATHS` still applies to a stranger under the flag, so every
trigger, the account and billing stay refused; `may_act` does not read the flag AT ALL, so no
mutation surface can move; and every disclaimer, vintage label and paper-account caveat is
untouched, because — as with demo — this renders the same templates by the same code path.

WHAT IT IS NOT: it is not `OWNER_SPLIT=false`. That would ALSO make `may_act` true for
everyone, handing anonymous callers `/api/scan/run`, `/api/signals/run` and both Edge Lab
runners — a free DoS lever on a 512 MB box that spends Don's FMP and Anthropic budget per
request. The whole reason this is a separate flag is that the obvious lever is the wrong one.

THE REGATE IS ONE FLAG. Set `PUBLIC_FULL_VIEW=false` in the Render dashboard, on Don's word,
when he hears back. No code change, nothing deleted, and the split underneath is intact and
still tested in both states.

RAW VENDOR ROWS ARE A LICENCE QUESTION AND ARE NOT COVERED BY "I know the risks", which
answers for liability. They do not move: the audit that cleared the demo tier route by route
(HANDOFF_appfixes.md Session 18) applies unchanged, because this grants the demo tier and not
a wider one — `DEMO_DENIED_VENDOR_ROWS` remains the place any future Sharadar-backed READ
route must be listed.

FAILURE MODE, DELIBERATELY CHOSEN
---------------------------------
This is an explicit DENY list, not an allowlist, which is the opposite of `private.py`. That
is a considered trade: under the lockdown, forgetting a route meant leaking the book, so it
had to fail closed. Here, forgetting to list a route means a new ANALYTICAL surface is public
by default, and the surfaces that matter are enumerated, stable, and pinned by a test that
walks the app's own URL map. `PUBLIC_API` below records the other half explicitly, so the test
can assert that every registered /api route is knowingly on one of the THREE sides below — a
new route lands in none of them and fails the suite until someone decides.

THE THIRD SIDE OF THE /api SPLIT: ADMIN-TOKEN ROUTES (corrected 2026-08-10, LA13)
--------------------------------------------------------------------------------
This docstring used to say "one side or the other", naming two categories. There have always
been three. `/api/option-alerts/open` and `/api/option-alerts/outcome` are in neither
`PUBLIC_API` nor `OWNER_ONLY_PATHS`; they are session-less endpoints for the Cowork/Robinhood
outcome filler, guarded by `X-Admin-Token` inside the handler. The test exempted them by a
hard-coded prefix skip, so the property this module ADVERTISED — every /api route is
knowingly classified — was not the property enforced, and this module had no record that a
third category existed at all. A future admin-token route under a different prefix would have
got neither a list nor the exemption, and would have landed on the public side by default.

The exemption is correct and is now WRITTEN DOWN, as `ADMIN_TOKEN_PREFIXES` below, taken from
`private.ADMIN_PREFIXES` rather than restated — the same list that lets these routes through
the lockdown must be the list that classifies them here, or one of the two will be edited
alone. `classify()` is the single reader, so the test walks this module's own answer instead
of keeping a second copy of the policy in the suite.

THE CLASSIFICATION IS NOT THE GUARD, and the difference is the whole lesson of LA13. Naming a
route "admin-token" here does nothing to it: the enforcement is `_admin_ok()` in the handler.
So `tests/test_public.py` asserts BOTH halves — that every /api route is classified, and that
every route classified admin-token actually refuses an un-tokened caller. Without the second
assertion this list would be a way to move a route out of the public set without securing it,
which is strictly worse than the hard-coded skip it replaces.
"""
from __future__ import annotations

#: Safe at module scope: `private.py` imports nothing from this package, so there is no cycle.
from .private import ADMIN_PREFIXES as _PRIVATE_ADMIN_PREFIXES

# ---------------------------------------------------------------------------------------
# OWNER-ONLY. Each entry names its reason (1/2/3 above) and the vendor behind its numbers.
# ---------------------------------------------------------------------------------------
OWNER_ONLY_PATHS = frozenset({
    # (1) Performance claims — the Tradier SANDBOX paper track. No real money, ever.
    "/api/track",             # forward record + paper account + paper_sandbox block  [Tradier sandbox / FMP]
    "/api/index-track",       # the Index's live equity curve vs SPY                  [Tradier sandbox / FMP]
    "/api/options-paper",     # the paper option book vs its backtest reference       [Tradier sandbox / ThetaData ref]
    "/api/options-scorecard",  # expectancy of closed alerts                          [broker fills / ThetaData ref]
    "/api/scream-track",      # the rebuilt scream-buy record: entry, target, stop,
                              # current mark and status per alert. Category (1) twice
                              # over — it is a forward performance record AND it names
                              # live open contracts with the levels they are trading
                              # to.                                                    [Tradier sandbox]

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
    "/api/dip",               # the Dip Detector: the same snapshot the hot list
                              # publishes, filtered on drawdown and health. Public for
                              # the same reason /api/hotstocks is — it is model output
                              # over names, not a book, a weight or a contract — and it
                              # carries no forward-return claim at all until the V6
                              # register closes (see web/dip_posture.py).              [FMP]
    "/api/whatdo",            # one name across the product; book/options half is
                              # stripped for non-owners inside `unified.name_view`    [FMP]
    "/api/tickers",           # local typeahead, no network                           [none]
    "/api/regime",            # market weather: 10Y, VIX, SPY vs its 200dma           [FMP / yfinance]
    "/api/export/excel",      # the visitor's own valuation, exported                 [FMP]
    "/api/export/pdf",        # ditto                                                 [FMP]
})

# ---------------------------------------------------------------------------------------
# ADMIN-TOKEN. Neither public nor session-owner: a scheduled process authenticating with
# `X-Admin-Token`, checked by `_admin_ok()` in the handler itself. Derived from the lockdown's
# own list so the two cannot be edited apart — see the docstring's third-side section.
#
# `_admin_ok` fails CLOSED on an unset token, so the worst case for a machine with no
# ADMIN_TOKEN is that these routes are unreachable, never that they are open.
# ---------------------------------------------------------------------------------------
ADMIN_TOKEN_PREFIXES = tuple(p for p in _PRIVATE_ADMIN_PREFIXES if p.startswith("/api/"))

# ---------------------------------------------------------------------------------------
# THE DEMO EXCLUSIONS. A valid demo session reads every owner surface EXCEPT these.
#
# This is an allowlist in disguise and is meant to be: the demo gains read access by a
# blanket rule, so the only thing standing between a résumé link and a state change is this
# set. Every entry says which of the prompt's two non-negotiable exclusions it serves —
# (1) no account/admin surfaces and nothing that mutates, (2) no raw vendor rows.
#
# The rule for adding to it: if a route WRITES anything (a store row, a session, a file), or
# spends the owner's vendor/AI budget, or belongs to the account rather than the product, it
# goes here. A route that only computes and returns does not.
# ---------------------------------------------------------------------------------------
DEMO_DENIED_PATHS = frozenset({
    # (1) Triggers — each writes to the store AND spends the owner's money on every call.
    "/api/scan/run",          # writes a scan snapshot; 3 FMP requests per uncached name
    "/api/signals/run",       # writes intraday rows + alerts; one Anthropic call per run
    "/api/backtest/run",      # CPU-heavy on a 512 MB box; a free DoS lever otherwise
    "/api/edge/backtest",     # the research bench's own runner
    "/api/edge/optimize",     # walk-forward weight search
    "/api/edge/track",        # rewrites the tracked record

    # (1) The account, which is settings rather than product. A demo user has no database
    #     row at all (`auth._demo_user` is synthetic, id 0), so /account/alerts would write
    #     an opt-in against a user that does not exist — a mutation AND a corrupt one.
    "/account",
    "/account/alerts",

    # (1) Money. Billing is off on this instance, but "the preview cannot initiate a
    #     payment" should not depend on a separate flag staying off.
    "/billing/checkout",
    "/billing/portal",
})

#: Not currently used — every raw-vendor surface is already denied above by the mutation
#: rule, and no READ route returns a vendor row verbatim (checked route by route, recorded
#: in HANDOFF_appfixes.md Session 18). It exists so that exclusion (2) has somewhere
#: obvious to go when the next Sharadar-backed read route is added, instead of being
#: remembered.
DEMO_DENIED_VENDOR_ROWS = frozenset()


def is_demo(user) -> bool:
    """A recruiter master-link preview session. Not an owner, never an owner."""
    return bool(user and user.get("is_demo"))


def public_full_view(cfg) -> bool:
    """ANONYMOUS == DEMO, temporarily. Don's decision, 2026-08-13.

        "/app must be 100% ungated - I know the risks - I've submitted applications with the
         non-master link; when I hear back we regate."

    The single read of the flag for policy purposes, same as `enabled` above.

    WHAT IT GRANTS: exactly the demo tier's READ access, to everybody, with no token. Nothing
    wider. `DEMO_DENIED_PATHS` still applies (see `check`), so the account, the billing routes
    and every trigger stay refused to a stranger.

    WHAT IT CANNOT GRANT, and this is the property worth protecting: it is not consulted by
    `may_act`. Widening reading and widening writing are separate functions here precisely so
    one cannot silently become the other, and this flag only ever touches the reading one.
    `test_public_full_view.py` pins that `may_act` is unmoved in every combination.

    THE REGATE: set it back to `false`. One flag, no code change, nothing deleted.
    """
    return bool(getattr(cfg, "public_full_view", False))


def is_demo_denied(path: str) -> bool:
    return path in DEMO_DENIED_PATHS or path in DEMO_DENIED_VENDOR_ROWS


#: What the preview is told when it reaches something it may not have. Says it is the
#: PREVIEW that is limited, not the reader — a recruiter who hits this should understand
#: they are looking at a read-only copy, not that they did something wrong.
DEMO_DENY_MESSAGE = ("This is a read-only preview of the full tool. It can show you "
                     "everything the owner sees, but it can't run scans, spend the "
                     "data budget or change any setting.")

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


def is_admin_token(path: str) -> bool:
    """Guarded by `X-Admin-Token` in the handler rather than by the session split.

    Note what this does NOT do: it grants nothing and refuses nothing. `check()` deliberately
    ignores it — an admin-token route is not owner-only (a session owner has no business
    reaching it either) and not public (a stranger gets 401 from `_admin_ok`). It exists so
    the route is CLASSIFIED rather than skipped, and so the suite can then go and verify that
    the handler's own guard is really there.
    """
    return bool(ADMIN_TOKEN_PREFIXES) and path.startswith(ADMIN_TOKEN_PREFIXES)


#: The three sides, in the order a path is tested against them. Owner-only is checked before
#: public so that a path appearing in both lists is treated as the more restrictive of the
#: two rather than silently taking the loose answer.
def classify(path: str):
    """Which side of the /api split a path is on: 'owner', 'admin-token', 'public', or None.

    None means UNCLASSIFIED, and it is the answer `tests/test_public.py` fails on. The single
    reader of the three lists above — the suite walks this rather than re-deriving the policy,
    which is how the old two-category claim survived beside a three-category reality.
    """
    if is_owner_only(path):
        return "owner"
    if is_admin_token(path):
        return "admin-token"
    if path in PUBLIC_API:
        return "public"
    return None


def may_see_owner_surfaces(user, cfg) -> bool:
    """MAY READ the owner surfaces. Owner or demo preview.

    With the split OFF this is true for everyone, which is what makes the flag a real revert
    rather than a partial one.

    Demo was added 2026-08-07 (PROMPT_recruiter_master_link.md) and is the whole point of the
    recruiter link. It grants READING only — `may_act` below is the other half, and the two
    are separate functions precisely so that widening one cannot silently widen the other.

    `public_full_view` (2026-08-13, Don's decision) is the third grant and rides the SAME
    read-only rail: it makes an anonymous visitor equivalent to a demo session. It is added
    here and NOT to `may_act`, which is the whole safety property.
    """
    if not enabled(cfg):
        return True
    return is_owner(user, cfg) or is_demo(user) or public_full_view(cfg)


def may_act(user, cfg) -> bool:
    """MAY CHANGE SOMETHING. The owner alone — never a demo session.

    Templates read this to decide whether to render a trigger (Run scan, Refresh signals,
    the three Edge Lab runners). Rendering a button the API will refuse is worse than
    rendering nothing: it teaches the reader the preview is broken rather than read-only.

    Deliberately NOT true-for-everyone when the split is off, in the one case that matters:
    a demo session stays read-only under every flag combination, because the flag governs
    who may READ the paper track and has nothing to say about who may spend the budget.
    """
    if is_demo(user):
        return False
    if not enabled(cfg):
        return True
    return is_owner(user, cfg)


def check(path: str, user, cfg):
    """None to allow. Otherwise a dict the caller renders — same shape as `private.check`.

    JSON for /api (the dashboard's own fetches read `owner_only` and hide their panel rather
    than printing an error), and a page refusal for anything else.
    """
    # The demo read-only rule runs FIRST and outside the flag. See the module docstring:
    # OWNER_SPLIT=false is a decision about what strangers may read, and it must not be
    # able to turn a résumé link into a scan trigger as a side effect.
    #
    # `public_full_view` joins this rule rather than bypassing it, and that is the point: it
    # lifts anonymous to the DEMO tier, and the demo tier's defining property is that this set
    # is refused. An anonymous visitor under the flag therefore reaches every owner READ and no
    # trigger, no account page and no billing route.
    #
    # `not is_owner(...)` guards the owner out of it. Without that clause the flag would refuse
    # the OWNER his own /account and billing pages the moment it was switched on — the flag is
    # about widening a stranger's reach, and it must not narrow Don's.
    if (not is_owner(user, cfg) and (is_demo(user) or public_full_view(cfg))
            and is_demo_denied(path)):
        if path.startswith("/api/"):
            return {"kind": "json", "status": 403,
                    "payload": {"error": DEMO_DENY_MESSAGE, "owner_only": True,
                                "demo_read_only": True}}
        return {"kind": "page", "status": 403, "payload": {"message": DEMO_DENY_MESSAGE}}
    if not enabled(cfg):
        return None
    if not is_owner_only(path):
        return None
    if is_owner(user, cfg) or is_demo(user) or public_full_view(cfg):
        return None
    if path.startswith("/api/"):
        return {"kind": "json", "status": 403,
                "payload": {"error": DENY_MESSAGE, "owner_only": True}}
    return {"kind": "page", "status": 403, "payload": {"message": DENY_MESSAGE}}
