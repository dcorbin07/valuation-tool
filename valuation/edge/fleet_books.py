"""THE DECLARED FLEET BOOKS' ENTRY RULES -- the code a declaration froze in prose.

**A DECLARATION FREEZES AN ENTRY RULE. IT DOES NOT EXECUTE ONE.** Seventeen books were
declared on 2026-08-24 and `cycle()` measured `entry_rules_implemented: 0`; every cycle would
have placed nothing, forever, and reported it honestly as `ARMED_NO_ENTRY_RULE`. This module
is the other half: the rules as code.

THE LAW THIS MODULE IS WRITTEN UNDER, and it is narrower than "make it work":

  * **THE CODE MATCHES THE FROZEN PROSE EXACTLY.** No improvement, no tuning, no parameter
    the declaration does not state. Where a declaration says "the 3 largest by market cap,
    alphabetical tie-break", that is the rule -- not the better rule, and not the rule with a
    sensible extra filter. A book's declaration is its pre-registration; code that quietly
    improves on it is measuring something nobody registered.
  * **AMBIGUITY IS AMENDED IN THE OPEN OR REFUSED BACK, NEVER INTERPRETED SILENTLY.** Every
    place the prose could not be executed as written carries a dated AMENDMENT section in the
    declaration file itself, and the amendment is a NEW section -- never an edit -- on
    `PT-AMEND1`'s rule: a correction that leaves no record of what it replaced is
    indistinguishable from the text having always said so.
  * **REGISTRATION IS AN EXPLICIT CALL, NEVER AN IMPORT SIDE EFFECT.** `register_all()` has to
    be invoked by whatever process drives a cycle. Importing this module registers nothing,
    so a test, a script and the runner all get the same empty seam until they ask -- `S3-I3`'s
    own convention, and the reason a stray import cannot silently arm a fleet.

WHAT A RULE RETURNS. `fn(decl, root) -> list[dict]`, each dict being kwargs for
`fleet.fill_fields`. **Returning `[]` means the rule ran and today qualifies nobody, which is
a market observation.** Not being registered at all means the rule was never built, which is
not. `cycle()` keeps those apart and so must this module.
"""
from __future__ import annotations

import os

from . import fleet as F


# ---------------------------------------------------------------------------------------
# F-1 -- THE FILL A/B
# ---------------------------------------------------------------------------------------
def f1_fill_ab(decl: dict, root: str = None) -> list:
    """F-1 places no orders. Its evidence is every OTHER book's fill row.

    **THIS RULE RETURNS `[]` AND THAT IS THE IMPLEMENTATION, NOT A STUB.** The declaration's
    frozen entry rule opens *"No entries of its own"*, and its universe is *"whatever the
    other fleet books trade"*. A rule that manufactured F-1 orders would be trading a book
    that declared it does not trade.

    **THE WORK F-1 ACTUALLY NEEDED IS IN `fleet.submit`**, which is where the frozen sentence
    puts it: *"**Every order any fleet book submits** is assigned by the harness's
    deterministic randomizer to arm A or arm B."* The assignment is a property of the
    harness's submission path, so no per-book callable could implement it -- F-1's callable
    cannot reach the orders of books that are not F-1. Registering it here with
    `places_orders=False` is what stops `cycle()` counting a rider as a breathing fleet.

    ITS RECORD STREAM STAYS EMPTY BY DESIGN. `records_schema` is `[]` in its own declaration
    and the draft says the per-order capture is *"computed at read time, not stored"*, so the
    verdict is read from the union of the other books' `arm`-stamped fill rows. Nothing is
    mirrored into F-1's own chain: a mirror would be a second copy of a fact, and the first
    copy is already hash-chained on the host's stream.
    """
    return []


# ---------------------------------------------------------------------------------------
# Shared helpers. Small, and deliberately NOT clever.
# ---------------------------------------------------------------------------------------
def _num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def _date(x):
    import datetime as _dt
    try:
        return _dt.date.fromisoformat(str(x)[:10])
    except (TypeError, ValueError):
        return None


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def held_symbols(book: str, root: str = None) -> set:
    """Underlyings this book already has on its own record stream.

    **CONSERVATIVE ON PURPOSE: a name that has ever filled counts as held.** No exit machinery
    exists yet, so there is no honest way to tell a closed position from an open one, and the
    two possible errors are not symmetric -- treating a closed name as held costs one skipped
    entry, treating an open one as free doubles a position against a declared concurrency cap.
    """
    rows = (F.read_records(book, root) or {}).get("rows") or []
    out = set()
    for r in rows:
        if (r.get("kind") or "") != "fill":
            continue
        if (r.get("fate") or "") in ("filled", "partial"):
            sym = str(r.get("symbol") or "").upper().strip()
            if sym:
                out.add(sym)
    return out


# ---------------------------------------------------------------------------------------
# F-3 -- BEAR-SCANNER PUTS
# ---------------------------------------------------------------------------------------
# The scanner's ENTIRE label vocabulary comes from `valuation/intraday/bearish.py` and
# `signals.evaluate_bearish`. F-3 skips a name *"ONLY if the scanner's own signal names the
# event"* -- and NONE of those labels names an event, so the clause is STRUCTURALLY INERT.
# That is a MEASUREMENT, not an assumption: `tests/test_fleet_f3.py` derives the vocabulary
# from the two source files and fails if a label ever begins naming one, at which point the
# clause becomes live and somebody has to decide what it means. Recorded, never dropped.
F3_EVENT_LABELS = ()          # empty BY MEASUREMENT, and pinned as empty

# "the scanner's top-N bearish verdicts (N=3)" -- the declaration's PROSE, which is where this
# number lives. Named here as the declaration's figure, not as a choice made in code.
F3_TOP_N = 3

# Amendment 3: the declaration says *"equal premium per position"* and states NO allocation,
# so the rule has no denominator. One contract per position until an allocation is declared --
# and the verdict statistic is RETURN ON PREMIUM, which is invariant to quantity, so this is
# measurement-neutral rather than a silent sizing choice.
F3_QTY = 1


def f3_select(rows, held, *, n: int, cap: int) -> list:
    """The frozen rule: top-N bearish verdicts among names not already held. PURE.

    `n` and `cap` have NO DEFAULTS. A default is exactly how a pre-committed bar freezes and
    then drifts from the declaration that set it (`MA5`'s measured lesson; `I-3`'s rule that a
    library carries no bar-shaped constant of its own). The caller reads them from the
    declaration or it does not get to call this.

    **THE TIE-BREAK IS ALPHABETICAL AND THE DECLARATION DOES NOT STATE ONE** -- amendment 1 in
    `DECL_f3_bear_puts.md`. Six other books in the fleet state alphabetical explicitly; an
    unstated tie-break is a non-reproducible rule, and a pre-registration cannot be that.
    """
    room = max(0, int(cap) - len(held))
    if room <= 0:
        return []
    out = []
    for r in rows:
        t = str(r.get("ticker") or "").upper().strip()
        if not t or t in held:
            continue
        sc = _num(r.get("bear_score"))
        if sc is None:
            continue
        labels = [str(x) for x in (r.get("labels_bear") or [])]
        if any(lab in F3_EVENT_LABELS for lab in labels):
            continue
        out.append({"ticker": t, "score": sc, "labels": labels, "price": r.get("price")})
    out.sort(key=lambda d: (-d["score"], d["ticker"]))
    return out[:min(int(n), room)]


def f3_pick_contract(chain, spot, today, *, moneyness: float, dte: int):
    """The listed PUT nearest `moneyness` x as-traded spot, at the expiry nearest `dte`. PURE.

    **EXPIRY FIRST, THEN STRIKE** -- amendment 2. The frozen sentence names both targets and
    not their precedence, and the two orders pick different contracts: strike-first can land
    on an expiry weeks away from 60 DTE because some far month happens to list a closer
    strike. Expiry-first keeps the declared 60-DTE tenor, which is the parameter this book's
    theta bleed is measured against.

    **THE SPOT IS AS-TRADED AND MUST BE.** A strike compared against a split-adjusted price
    picks a contract nowhere near the money and fails SILENTLY -- this record measured
    `raw_close` 411.80 against an adjusted 8.236 on one real row. A live quote is as-traded by
    construction, which is why this takes a live spot and never a panel price.

    NO DELTA IS SOLVED OR TARGETED ANYWHERE: F-3's own void condition is *"delta-targeted
    strikes"*, honouring `V6-OPT`'s autopsy. This is moneyness-fixed by construction.
    """
    tgt_spot = _num(spot)
    if not chain or tgt_spot is None:
        return None
    target = tgt_spot * float(moneyness)
    puts = []
    for c in chain:
        if str(c.get("option_type") or "").lower() != "put":
            continue
        exp, k = _date(c.get("expiration_date")), _num(c.get("strike"))
        if exp is None or k is None:
            continue
        puts.append((exp, k, c))
    if not puts:
        return None
    best_exp = min({e for e, _, _ in puts},
                   key=lambda e: (abs((e - today).days - int(dte)), e))
    same = [(k, c) for e, k, c in puts if e == best_exp]
    k, c = min(same, key=lambda kc: (abs(kc[0] - target), kc[0]))
    return {"contract": c, "expiration": best_exp.isoformat(), "strike": k,
            "target_strike": round(target, 4), "dte": (best_exp - today).days}


def f3_bear_puts(decl: dict, root: str = None, *, store=None, provider=None,
                 broker=None, today=None) -> list:
    """F-3 live. Reads the scanner's own stored verdicts; every parameter comes from `decl`.

    The injectable `store`/`provider`/`broker`/`today` exist so the rule is testable without a
    broker or a network, and default to the live objects. Nothing about the RULE changes with
    them -- the selection and the contract choice are the two pure functions above, and this
    is the plumbing that feeds them.
    """
    import datetime as _dt
    from ..screener.store import Store
    from ..intraday.providers import get_provider

    st = decl.get("structure") or {}
    today = today or _dt.date.today()
    store = store if store is not None else Store()
    provider = provider if provider is not None else get_provider()

    rows = []
    for r in (store.load_intraday() or []):
        d = r.get("detail") or {}
        rows.append({"ticker": r.get("ticker"),
                     "bear_score": (d.get("scores_bear") or {}).get("swing"),
                     "labels_bear": d.get("labels_bear") or [],
                     "price": d.get("price")})

    picks = f3_select(rows, held_symbols("f3_bear_puts", root),
                      n=F3_TOP_N, cap=int(decl.get("concurrency_cap") or 0))
    if not picks:
        return []

    if broker is None:
        from .paper_broker import PaperBroker
        broker = PaperBroker()

    # AUDIT #5 H1 - ROUTED THROUGH THE ONE RESOLVER. Reading DECL_*.md directly
    # RAISES in the image, where `.dockerignore` excludes `*.md`, and it raises
    # only on a day this book actually has a pick -- so every quiet cycle looked
    # healthy and the defect would have fired exactly once, on the first day that
    # would have been evidence. `decl_sha_for` falls back to the shipped manifest.
    sha = F.decl_sha_for("f3_bear_puts", root)
    if not sha:
        # No declaration by EITHER route: refuse the candidates rather than
        # filling against an unidentified declaration.
        return []
    out = []
    for p in picks:
        got = f3_pick_contract(provider.get_option_chain(p["ticker"], dte_range=(45, 75)),
                               p["price"], today,
                               moneyness=float(st.get("moneyness")), dte=int(st.get("dte")))
        if got is None:
            continue
        c = got["contract"]
        out.append(F.submit("f3_bear_puts", broker=broker, occ=str(c.get("symbol")),
                            underlying=p["ticker"], side="buy_to_open", qty=F3_QTY,
                            decl_sha=sha, symbol=p["ticker"], quote=c))
    return out


# ---------------------------------------------------------------------------------------
# F-8 -- CSP ENTRY FINANCING  (SHORT: needs S3-I3 registered, which the runner's door does)
# ---------------------------------------------------------------------------------------
# Amendment 1: the declared tie-break is "highest composite score" and the PUBLISHED artifact
# does not carry one -- `paper_track_holdings.csv` is ticker, weight, entry_date, entry_price,
# bench_entry_price, shares, order_id, note. The declaration also forbids the obvious
# workaround by name: *"a published artifact, never the scoring path"*. Resolved on `weight`
# descending, which the Index derives FROM the score -- with the honest limit that the 8% cap
# compresses the top, so where it binds two different scores can share a weight and the
# alphabetical tie-break then decides. It only bites when more than `cap` names enter at once.
F8_QTY = 1


def f8_select(rows, today, held, *, cap: int) -> list:
    """Names NEWLY ENTERING the published paper index book today. PURE.

    A name is newly entering on date D exactly when its published `entry_date` IS D. That
    needs no rebalance calendar and cannot drift from one: the artifact's own dates are the
    definition, and on a day with no entries the rule returns `[]`, which is a market
    observation rather than a build gap.

    `cap` has NO DEFAULT -- `MA5`. Read it from the declaration.
    """
    room = max(0, int(cap) - len(held))
    if room <= 0:
        return []
    out = []
    for r in rows:
        t = str(r.get("ticker") or "").upper().strip()
        if not t or t in held:
            continue
        if str(r.get("entry_date") or "")[:10] != str(today)[:10]:
            continue
        out.append({"ticker": t, "weight": _num(r.get("weight")) or 0.0,
                    "entry_price": _num(r.get("entry_price"))})
    out.sort(key=lambda d: (-d["weight"], d["ticker"]))
    return out[:room]


def read_published_holdings(root: str = None) -> list:
    """The PUBLISHED artifact, never the scoring path -- the declaration says so twice.

    `data_export/` is tracked and is NOT excluded from the deployed image, which is the whole
    reason this book can run on the service at all while six of its siblings cannot.
    """
    import csv
    base = root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base, "data_export", "paper_track_holdings.csv")
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    except OSError:
        return []


def f8_csp_entry_financing(decl: dict, root: str = None, *, provider=None, broker=None,
                           today=None, holdings=None) -> list:
    """F-8 live: sell a cash-secured put on each name newly entering the published book.

    **IT REFUSES ITSELF IF S3-I3 IS NOT REGISTERED**, rather than trusting the cycle's gate to
    have done it. The gate does check -- `validate_declaration` refuses every short book
    without a provider -- but a rule that would place a short order is the last place that
    should assume somebody else checked. Belt and braces, and the braces are one line.
    """
    import datetime as _dt
    from ..intraday.providers import get_provider

    if F.assignment_provider() is None:
        return []

    st = decl.get("structure") or {}
    today = today or _dt.date.today()
    rows = holdings if holdings is not None else read_published_holdings(root)
    picks = f8_select(rows, today, held_symbols("f8_csp_entry_financing", root),
                      cap=int(decl.get("concurrency_cap") or 0))
    if not picks:
        return []

    provider = provider if provider is not None else get_provider()
    if broker is None:
        from .paper_broker import PaperBroker
        broker = PaperBroker()

    # AUDIT #5 H1 - ROUTED THROUGH THE ONE RESOLVER. Reading DECL_*.md directly
    # RAISES in the image, where `.dockerignore` excludes `*.md`, and it raises
    # only on a day this book actually has a pick -- so every quiet cycle looked
    # healthy and the defect would have fired exactly once, on the first day that
    # would have been evidence. `decl_sha_for` falls back to the shipped manifest.
    sha = F.decl_sha_for("f8_csp_entry_financing", root)
    if not sha:
        # No declaration by EITHER route: refuse the candidates rather than
        # filling against an unidentified declaration.
        return []
    out = []
    for p in picks:
        got = f3_pick_contract(provider.get_option_chain(p["ticker"], dte_range=(20, 45)),
                               p["entry_price"], today,
                               moneyness=float(st.get("moneyness")), dte=int(st.get("dte")))
        if got is None:
            continue
        c = got["contract"]
        out.append(F.submit("f8_csp_entry_financing", broker=broker, occ=str(c.get("symbol")),
                            underlying=p["ticker"], side="sell_to_open", qty=F8_QTY,
                            decl_sha=sha, symbol=p["ticker"], quote=c))
    return out


# ---------------------------------------------------------------------------------------
# THE REGISTRY
# ---------------------------------------------------------------------------------------
# book -> (callable, places_orders). `places_orders=False` marks a RIDER: a book whose own
# declaration says it never sends an order, so a cycle in which only riders ran is NOT a
# breathing fleet and `cycle()` must not report one.
RULES = {
    "f1_fill_ab": (f1_fill_ab, False),
    "f3_bear_puts": (f3_bear_puts, True),
    "f8_csp_entry_financing": (f8_csp_entry_financing, True),
}


def register_all() -> dict:
    """Register every implemented rule. Explicit, idempotent, and never an import side effect.

    Returns the registered book names so a caller can assert what it armed rather than assume
    it. A book absent from `RULES` is still declared and still un-armed, and `cycle()` will
    keep saying so.
    """
    for book, (fn, places) in sorted(RULES.items()):
        F.register_entry_rule(book, fn, places_orders=places)
    return {"ok": True, "registered": sorted(RULES), "count": len(RULES)}
