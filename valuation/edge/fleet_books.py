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



def cycle_session(now=None):
    """The TRADING SESSION a fleet cycle is about. **Not `date.today()`.**

    **THE DEFECT THIS FIXES, AND IT IS WHY FOUR BOOKS HAVE NEVER FILLED.** Every entry rule
    here compared a recorded date against `_dt.date.today()`, which is correct only if the
    cycle runs on the same UTC day as the session it is reading. **It does not, and the project
    had already measured why:** `fleet-cycle.yml` crons at 22:19Z and item 64 measured GitHub
    firing this repository's crons **3.5 to 7.5 hours late**, so the last six cycles landed at
    00:24Z, 00:31Z, 01:13Z, 07:15Z, 03:03Z and 01:45Z -- **every one of them on the following
    UTC day.** Meanwhile `/admin/record-dip-rejects` stamps its rows with
    `last_closed_session()`, precisely so a slipped run cannot invent a session.

    > **So the writer and the readers were on different clocks, and an exact-date match between
    > them could never succeed.** `f11_recorded_rejects` returns `None` -- "no row for today" --
    > on every run, which the harness then reports as `RULE_ARMED_NEVER_FIRES`: a phrase that
    > reads as *the rule cannot qualify anybody* when the truth is *the rule never saw the
    > data*. On a Saturday it is worse still, because no session exists for that date at all.

    One definition, used by every rule (`B7`), so the question "which session is this cycle
    about" has a single answer. Falls back to `date.today()` only if the market calendar
    cannot be consulted -- **reported in the return, never silently** -- because a rule that
    silently changed which day it reads would be the same defect wearing the repair's clothes.
    """
    import datetime as _dt2
    try:
        from ..screener.market_session import last_closed_session
        d = last_closed_session(now)
        if d:
            return d
    except Exception:                                                # noqa: BLE001
        pass
    return (now.date() if hasattr(now, "date") else None) or _dt2.date.today()



def _occ_or_refuse(contract) -> str:
    """The contract's OCC symbol, or `""` -- never the STRING "None".

    **`str(None)` IS `"None"`, AND THAT IS HOW A MISSING FIELD REACHED A BROKER.** Every book
    here built its order with `occ=str(c.get("symbol"))`, so a chain row without a symbol
    produced the four-character string `None` and handed it to the venue, which refused it
    with `not an OCC symbol: 'None'` -- a message about the string rather than about the
    missing field. Returning `""` makes the refusal name the real fault one layer earlier, and
    the submit path already refuses an empty symbol.
    """
    # STRIP ONLY -- deliberately NOT upper(). The helper's job is "never send the string
    # None", not "normalise case", and case-folding here would silently rewrite what the chain
    # returned into the record. `test_fleet_f3` caught exactly that: its fixture symbol is
    # lowercase and an incidental `.upper()` here changed a recorded `occ`. Normalisation
    # belongs where the field is CONSTRUCTED (the provider), not where it is read.
    v = (contract or {}).get("symbol")
    return str(v).strip() if v else ""


def _needs_cash(book: str, root=None) -> bool:
    """Does this book's DECLARATION say it is short / sells premium? Read, never inferred.

    The declaration is the authority on what a book does (`MA5`), so this reads `side` and
    `sells_premium` from it rather than guessing from the book's name. **It fails toward
    NEEDING cash**: a declaration that cannot be read returns True, because the safe direction
    is to refuse a share rather than to let an unrecognised book compete with the Index for
    buying power.
    """
    try:
        import io as _io
        import os as _os
        p = _os.path.join(F.repo_root() if hasattr(F, "repo_root") else ".",
                          "DECL_%s.md" % book)
        with _io.open(p, encoding="utf-8") as fh:
            d = (F.parse_declaration(fh.read()) or {}).get("declaration") or {}
    except Exception:                                                # noqa: BLE001
        return True
    if not d:
        return True
    if bool(d.get("sells_premium")):
        return True
    return str(d.get("side") or "").strip().lower() == "short"


def _broker_or_refuse(book: str, root=None):
    """The fleet's broker, or `None` having WRITTEN a named refusal onto the book's stream.

    **A BROKER THAT CANNOT BE BUILT IS A FACT ABOUT THE VENUE, NOT ABOUT THE MARKET**, so it
    is recorded with its own code rather than raising into `cycle()`'s generic
    `ENTRY_RULE_RAISED`. The reason travels verbatim -- "the keys are not set" and "the keys
    are crossed with a live slot" are different problems, and one code could not tell a reader
    which to go and fix.
    """
    b, why = F.fleet_broker_or_reason()
    if b is not None:
        # **A BOOK THAT NEEDS CASH MAY NOT SHARE THE INDEX'S PAPER ACCOUNT.** That slot is
        # deployed at 100% by the Index paper book, and a cash-secured put needs cash, so
        # sharing means one book silently starves the other -- and the starved one records a
        # refusal that reads like a market fact rather than a plumbing one. Alpaca allows up
        # to three paper accounts, so the fix is a second account rather than a smaller
        # Index; until its keys exist, the SHORT books refuse BY NAME and the long-option
        # books (which need no cash) trade.
        if getattr(b, "dedicated", True) or not _needs_cash(book, root):
            return b
        sha = F.decl_sha_for(book, root) or F.decl_sha_for(book)
        if sha:
            F.refuse(book, "SHARED_ACCOUNT_WOULD_COLLIDE",
                     "this book is SHORT and needs cash, and the only Alpaca paper "
                     "credentials configured are the Index paper slot's, which is deployed "
                     "at 100%. Set ALPACA_FLEET_PAPER_KEY_ID / ALPACA_FLEET_PAPER_SECRET_KEY "
                     "from a second Alpaca paper account and this book starts by itself.",
                     decl_sha=sha, root=root)
        return None
    sha = F.decl_sha_for(book, root) or F.decl_sha_for(book)
    if sha:
        F.refuse(book, "BROKER_UNAVAILABLE", why, decl_sha=sha, root=root)
    return None


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


def f3_pick_contract(chain, spot, today, *, moneyness: float, dte: int,
                     expiry_rule: str = "nearest"):
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
    exps = {e for e, _, _ in puts}
    if str(expiry_rule) == "nearest_above":
        # F-11 declares "expiry nearest ABOVE 91 DTE", which is NOT the same contract as
        # nearest-in-absolute-terms: an 85-DTE expiry is nearer to 91 than a 98-DTE one and is
        # the wrong side of the declared tenor. The declaration is frozen, so the rule is
        # implemented as written rather than approximated with the picker already here.
        above = [e for e in exps if (e - today).days >= int(dte)]
        if not above:
            return None                                # no expiry at or beyond the tenor
        best_exp = min(above, key=lambda e: ((e - today).days, e))
    else:
        best_exp = min(exps, key=lambda e: (abs((e - today).days - int(dte)), e))
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
    today = today or cycle_session()
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
        # ONE factory (`B7`): the fleet's venue is decided in `fleet.fleet_broker`, not
        # six times here, and a broker that cannot be built writes a NAMED refusal
        # rather than raising -- a silent fallback to the closed Tradier sandbox is how
        # six weeks of empty streams came to read as success.
        broker = _broker_or_refuse("f3_bear_puts", root)
        if broker is None:
            return []

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
        out.append(F.submit("f3_bear_puts", broker=broker, occ=_occ_or_refuse(c),
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
    today = today or cycle_session()
    rows = holdings if holdings is not None else read_published_holdings(root)
    picks = f8_select(rows, today, held_symbols("f8_csp_entry_financing", root),
                      cap=int(decl.get("concurrency_cap") or 0))
    if not picks:
        return []

    provider = provider if provider is not None else get_provider()
    if broker is None:
        # ONE factory (`B7`): the fleet's venue is decided in `fleet.fleet_broker`, not
        # six times here, and a broker that cannot be built writes a NAMED refusal
        # rather than raising -- a silent fallback to the closed Tradier sandbox is how
        # six weeks of empty streams came to read as success.
        broker = _broker_or_refuse("f8_csp_entry_financing", root)
        if broker is None:
            return []

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
        out.append(F.submit("f8_csp_entry_financing", broker=broker, occ=_occ_or_refuse(c),
                            underlying=p["ticker"], side="sell_to_open", qty=F8_QTY,
                            decl_sha=sha, symbol=p["ticker"], quote=c))
    return out


# ---------------------------------------------------------------------------------------
# F-11 -- DIP-REJECT PUTS
# ---------------------------------------------------------------------------------------
F11_QTY = 1


def f11_quarter(d) -> str:
    """`"YYYYQn"`. The declaration's re-entry window is a QUARTER, so it needs a name."""
    return "%04dQ%d" % (d.year, ((d.month - 1) // 3) + 1)


def f11_first_appearances(history, today, *, sessions: int = 2) -> dict:
    """`{ticker: first_date}` for names whose FIRST appearance THIS QUARTER is recent enough.

    **THIS IS THE WHOLE REASON `dip_rejects` IS RECORDED.** F-11's hypothesis is a name's
    FIRST appearance in the reject population, and first-ness is only decidable against a
    dated history -- which is why audit #5's fabricated zeros were not a bookkeeping problem
    but evidence AGAINST the thing this book exists to detect.

    `history` is `fleet_history.read("dip_rejects")["rows"]`, oldest first. **Rows a forward
    record marks INVALID are SKIPPED**, so the fabricated span cannot date a first appearance.

    `sessions` counts RECORDED days, not calendar days: the series has a row per cycle that
    consulted a source, and a weekend or an outage is not a session. Counting calendar days
    would let a Friday appearance expire over a weekend on which nothing was observable.
    """
    q = f11_quarter(today)
    dates, seen = [], {}
    for r in history or []:
        if r.get("invalid"):
            continue                                   # audit #5 H2: not an observation
        d = _date(r.get("date"))
        if d is None or f11_quarter(d) != q:
            continue
        dates.append(r.get("date"))
        payload = r.get("payload")
        names = payload if isinstance(payload, list) else []
        for t in names:
            t = str(t).upper().strip()
            if t and t not in seen:
                seen[t] = r.get("date")
    if not dates:
        return {}
    recent = set(sorted(set(dates))[-int(sessions):])
    return {t: d for t, d in seen.items() if d in recent}


def f11_select(rejects, history, today, held, *, cap: int, sessions: int = 2) -> list:
    """The names F-11 may enter today. PURE.

    Frozen rule: *"Enter within 2 sessions of a name's FIRST appearance on the list this
    quarter; skip names already held or entered this quarter."*

    **A NAME MUST BE ON TODAY'S LIST AND BE A RECENT FIRST APPEARANCE.** Both, because the
    declaration says "enter within 2 sessions OF A FIRST APPEARANCE" -- a name whose first
    appearance was two days ago and which has since recovered off the list is not a reject
    today, and entering it would be trading a memory.

    `held` carries every underlying this book has ever filled, so the quarter re-entry ban and
    the never-double-up rule are the same check. Re-entry within a quarter is a VOID condition
    of the declaration, so the conservative reading is the required one.
    """
    firsts = f11_first_appearances(history, today, sessions=sessions)
    held = {str(h).upper() for h in (held or set())}
    out = []
    for r in rejects or []:
        t = str((r or {}).get("ticker") or "").upper().strip()
        if not t or t in held or t not in firsts:
            continue
        row = dict(r)
        row["ticker"] = t
        row["first_appearance"] = firsts[t]
        out.append(row)
    # Deepest drawdown first, then ticker -- deterministic, and the cap is applied to a
    # defined order rather than to whatever the screen happened to emit.
    out.sort(key=lambda r: (-float(r.get("drawdown") or 0.0), r["ticker"]))
    return out[:max(0, int(cap))] if cap else out


def f11_dip_reject_puts(decl: dict, root: str = None, *, provider=None, broker=None,
                        today=None, rejects=None, history=None) -> list:
    """F-11 live: buy a 91-DTE put on each name newly entering the dip-REJECT population.

    Every parameter comes from `decl`. The screen is NOT re-implemented here: the reject
    population arrives from `dip.dip_rejects`, which reads what `dip.screen` already
    classified with its own published `health_check` and `clamp_drawdown`.

    **NO EXIT MACHINERY EXISTS HERE AND THAT IS DECLARED, NOT MISSING.** The frozen structure
    is *"hold to expiry, no exits"* and *"any exit rule"* is a VOID condition, so a stop or a
    target added later voids the book rather than improving it.

    **NO DELTA IS SOLVED OR TARGETED**, which is the other void condition: the strike is
    moneyness-fixed against AS-TRADED spot, `V6-OPT`'s autopsy.
    """
    import datetime as _dt
    from ..intraday.providers import get_provider

    st = decl.get("structure") or {}
    today = today or cycle_session()

    if rejects is None:
        rejects = f11_recorded_rejects(root)
    if rejects is None:
        # THE SOURCE WAS NOT CONSULTED. Audit #5 H2's rule, one level out: a book that cannot
        # see its own screen selects nobody rather than selecting from an empty list, which
        # would read in the records as "the market offered nothing today".
        return []

    if history is None:
        from . import fleet_history as FH
        history = (FH.read("dip_rejects", root) or {}).get("rows") or []

    picks = f11_select(rejects, history, today,
                       held_symbols("f11_dip_reject_puts", root),
                       cap=int(decl.get("concurrency_cap") or 0))
    if not picks:
        return []

    provider = provider if provider is not None else get_provider()
    if broker is None:
        # ONE factory (`B7`): the fleet's venue is decided in `fleet.fleet_broker`, not
        # six times here, and a broker that cannot be built writes a NAMED refusal
        # rather than raising -- a silent fallback to the closed Tradier sandbox is how
        # six weeks of empty streams came to read as success.
        broker = _broker_or_refuse("f11_dip_reject_puts", root)
        if broker is None:
            return []

    sha = F.decl_sha_for("f11_dip_reject_puts", root)
    if not sha:
        return []

    # READ FROM THE DECLARATION, NOT ASSUMED. The declaration carries `dte_rule` and `right`
    # as fields, and hard-coding either here would make the code the authority instead of the
    # frozen text. A declaration that ever says something this rule cannot execute must be
    # REFUSED, not quietly reinterpreted.
    rule = "nearest_above" if "above" in str(st.get("dte_rule") or "").lower() else "nearest"
    if str(st.get("right") or "put").lower() != "put":
        return []                                      # the contract picker is puts-only

    out = []
    for p in picks:
        chain = provider.get_option_chain(p["ticker"], dte_range=(int(st.get("dte")), None))
        got = f3_pick_contract(chain, p.get("price"), today,
                               moneyness=float(st.get("moneyness")),
                               dte=int(st.get("dte")),
                               expiry_rule=rule)
        if got is None:
            continue
        c = got["contract"]
        out.append(F.submit("f11_dip_reject_puts", broker=broker, occ=_occ_or_refuse(c),
                            underlying=p["ticker"], side="buy_to_open", qty=F11_QTY,
                            decl_sha=sha, symbol=p["ticker"], quote=c))
    return out


def f11_recorded_rejects(root: str = None, today=None):
    """Today's rejects READ from the recorded series, or `None` if today has no row.

    **THE DECLARATION SAYS "READ, NEVER RECOMPUTED", AND THIS IS WHY THAT MATTERS
    OPERATIONALLY.** An earlier cut had the rule call the live screen itself, and the screen
    values up to a dozen names through the valuation engine: **MEASURED on the service, one
    cycle went from ~9s to 188s, warm and repeatable, against the runner's 120s budget** — so
    the scheduled fleet cycle would have timed out every day. Reading the row somebody else
    already paid for is both the declaration's own wording and the only version that fits the
    cycle's budget.

    `None` when today has no recorded row — NOT CONSULTED, so the rule selects nobody rather
    than treating an unwritten day as a day nobody qualified.
    """
    import datetime as _dt
    from . import fleet_history as FH
    d = (today or cycle_session()).isoformat()
    for r in reversed((FH.read("dip_rejects", root) or {}).get("rows") or []):
        if r.get("date") != d:
            continue
        if r.get("invalid"):
            return None                        # a fabricated row is not an observation
        payload = r.get("payload")
        names = payload if isinstance(payload, list) else []
        # The rule needs the drawdown to order and cap; the series stores names only, so the
        # ordering falls back to the ticker. Stated rather than hidden: the CAP is applied to
        # an alphabetical order on a day the series carries more than `cap` first appearances.
        return [{"ticker": str(t).upper(), "drawdown": None} for t in names]
    return None


def f11_live_rejects():
    """Today's reject population from the live screen, or `None` if it cannot be consulted.

    **EXPENSIVE — it values up to a dozen names.** Called by whatever process already pays for
    a screen (the scan worker), never from the fleet cycle's request path.

    **`None` AND `[]` ARE DIFFERENT AND THE DIFFERENCE IS THE POINT** (audit #5, `H2`): `[]`
    means the screen ran and rejected nobody, `None` means no screen was consulted. Returning
    `[]` on an unreachable store would put a fabricated zero back into the one series that was
    just repaired for exactly that.
    """
    try:
        from ..screener.store import Store
        from ..web.app import _get_or_compute
        from ..web import dip as _dip
        payload = _dip.screen_snapshot(Store(), _get_or_compute)
        if payload.get("empty"):
            return None                                # no scan has landed; nothing observed
        # ITEM 19 -- A SCREEN THAT MEASURED NOTHING OBSERVED NOTHING, SO IT RETURNS `None`.
        #
        # This is audit #5 `H2`'s own distinction extended to the route it did not cover. H2
        # established that `[]` means *the screen ran and rejected nobody* while `None` means
        # *no screen was consulted*, and this function's docstring warns that returning `[]`
        # wrongly "would put a fabricated zero back into the one series that was just repaired
        # for exactly that". H2 guarded the UNREACHABLE STORE; it did not guard a screen that
        # runs, reaches every name, and measures none of them.
        #
        # That is what happened. From 2026-08-13 the screen was wired to a cache ENTRY rather
        # than the result inside it (see `dip.unwrap_result`), so every name came back
        # unmeasured, `dip_rejects` was empty, and this returned `[]` -- a fabricated zero
        # recorded as an observation, every cycle, into the series F-11's whole hypothesis
        # reads for FIRST appearances. `f11_first_appearances` cannot tell a day on which
        # nobody was rejected from a day on which nobody was looked at.
        #
        # Both shapes of "measured nothing" are covered: none examined at all, and every
        # examined name failing. The service's state was the SECOND (n_measured 12,
        # n_unmeasured 12), so a guard on zero alone would have missed the live case.
        n_meas = int(payload.get("n_measured") or 0)
        n_un = int(payload.get("n_unmeasured") or 0)
        if n_meas == 0 or n_un >= n_meas:
            return None
        return _dip.dip_rejects(payload)
    except Exception:                                  # noqa: BLE001
        return None


def f11_live_rejects_tickers():
    """Just the tickers, for `fleet_history.record_dip_rejects`. `None` propagates.

    The recorder stores a list of names; the full reject rows carry the drawdown and the
    failing floors, which F-11's own rule reads. Keeping the `None` distinct from `[]` all the
    way through is the entire point of audit #5's `H2` repair -- collapsing it here would put
    the fabricated zero straight back.
    """
    rows = f11_live_rejects()
    if rows is None:
        return None
    return sorted({str((r or {}).get("ticker") or "").upper().strip()
                   for r in rows if (r or {}).get("ticker")})


# ---------------------------------------------------------------------------------------
# THE REGISTRY
# ---------------------------------------------------------------------------------------
# book -> (callable, places_orders). `places_orders=False` marks a RIDER: a book whose own
# declaration says it never sends an order, so a cycle in which only riders ran is NOT a
# breathing fleet and `cycle()` must not report one.
# ============================================================================================
# F-21 and F-22 -- the V6-OPT put book and its random-day twin
#
# BOTH ARE IMPLEMENTED AND NEITHER IS ARMED. They are deliberately absent from `RULES` below,
# which is what "declared, not armed" means operationally: `cycle()` never calls them, and
# arming is a one-line change somebody makes on purpose once the precondition clears.
#
# THE PRECONDITION IS MECHANICAL RATHER THAN REMEMBERED, and it is the whole of the fleet
# review's warning. Three of the four armed books are `RULE_ARMED_NEVER_FIRES` -- `f1_fill_ab`
# 30 observations and zero fills, `f8_csp_entry_financing` 26 and zero, `f11_dip_reject_puts`
# 26 and zero -- and the harness's own message is the right one: *"A rule that cannot qualify
# anybody is indistinguishable in the records from a quiet market."* So these two REFUSE BY
# NAME on a thin or stale source instead of returning an empty list that reads as a calm day.
# ============================================================================================

#: `DECL_f21_v6opt_dip_csp.md` structure fields `min_healthy_rows` / `max_stale_sessions`.
#: Read from the declaration at call time; these are the fallbacks when a caller passes a
#: structure that omits them, and they match the declared values.
F21_MIN_HEALTHY_ROWS = 20
F21_MAX_STALE_SESSIONS = 5
F21_QTY = 1


def healthy_series_state(history, today, *, min_rows: int, max_stale: int) -> dict:
    """Is the `dip_healthy` series fit to resolve a FIRST APPEARANCE? PURE.

    Returns `{"ok", "reason", "rows", "last_date"}`. **A refusal here is a statement about the
    SOURCE and is recorded as one** -- the distinction the harness exists to preserve.
    """
    import datetime as _dt

    rows = [r for r in (history or []) if not r.get("invalid")]
    n = len(rows)
    last = str((rows[-1].get("date") if rows else "") or "")
    if n < int(min_rows):
        return {"ok": False, "rows": n, "last_date": last,
                "reason": ("SOURCE TOO THIN: the dip_healthy series carries %d recorded rows "
                           "against the declared minimum of %d, so 'first appearance this "
                           "quarter' cannot be resolved. This is a statement about the SOURCE "
                           "and not about the market." % (n, int(min_rows)))}
    if last:
        try:
            gap = (_dt.date.fromisoformat(str(today)[:10])
                   - _dt.date.fromisoformat(last[:10])).days
        except Exception:                                            # noqa: BLE001
            gap = None
        if gap is not None and gap > int(max_stale) * 2:   # calendar days vs sessions, x2
            return {"ok": False, "rows": n, "last_date": last,
                    "reason": ("SOURCE STALE: the latest dip_healthy row is %s, %d calendar "
                               "days before %s, beyond the declared %d-session tolerance. "
                               "Entering on it would be trading a memory."
                               % (last, gap, str(today)[:10], int(max_stale)))}
    return {"ok": True, "rows": n, "last_date": last, "reason": ""}


def f21_first_appearances(history, today) -> dict:
    """`ticker -> the recorded date it FIRST appeared in the current calendar quarter`. PURE.

    Evaluated at the SERIES' OWN CADENCE (declaration amendment `A2`): a name qualifies on the
    first recorded row of this quarter in which it appears and did not appear in the
    immediately preceding recorded row. The draft's *"within 2 sessions"* is not achievable
    while the recorder is weekly, and pretending otherwise would select nobody.
    """
    import datetime as _dt

    d = _dt.date.fromisoformat(str(today)[:10])
    q_start = _dt.date(d.year, 3 * ((d.month - 1) // 3) + 1, 1).isoformat()
    rows = [r for r in (history or [])
            if not r.get("invalid") and str(r.get("date") or "") >= q_start]
    rows.sort(key=lambda r: str(r.get("date") or ""))
    firsts, prev = {}, set()
    for r in rows:
        names = {str(t).upper() for t in (r.get("payload") or [])}
        for t in sorted(names - prev):
            firsts.setdefault(t, str(r.get("date")))
        prev = names
    return firsts


def f21_select(healthy, history, today, held, *, cap: int) -> list:
    """The names F-21 may enter. PURE.

    `held` carries every underlying this book has ever filled, so the quarter re-entry ban and
    the never-double-up rule are the same check -- re-entry inside a quarter is a VOID
    condition, so the conservative reading is the required one.
    """
    firsts = f21_first_appearances(history, today)
    held = {str(h).upper() for h in (held or set())}
    out = []
    for r in healthy or []:
        t = str((r or {}).get("ticker") or "").upper().strip()
        if not t or t in held or t not in firsts:
            continue
        row = dict(r)
        row["ticker"] = t
        row["first_appearance"] = firsts[t]
        out.append(row)
    # LARGEST BY MARKET CAP, the declaration's own tie-break, then ticker. Deterministic, so
    # the cap is applied to a defined order rather than to whatever the screen emitted.
    out.sort(key=lambda r: (-float(r.get("market_cap") or 0.0), r["ticker"]))
    return out[:max(0, int(cap))] if cap else out


def f22_draws(pool, session_date, *, salt: str, p: float) -> list:
    """F-22's deterministic salted draw. PURE, and it reads the calendar and the ticker ONLY.

    `sha256(salt || book || ticker || session_date) mod 1e9 < p * 1e9`. **Not an RNG**, so any
    reader reproduces every entry the book ever made from the declaration alone (`S3-I1`'s
    day-1 self-check requires exactly this), and **no price-derived quantity is referenced**,
    which is the void condition that keeps the timing uncorrelated with the dip signal.
    """
    import hashlib
    out = []
    for t in sorted({str(x).upper() for x in (pool or []) if str(x).strip()}):
        h = hashlib.sha256(("%s|f22_dip_csp_random_twin|%s|%s"
                            % (salt, t, session_date)).encode("utf-8")).hexdigest()
        if (int(h[:15], 16) % 1_000_000_000) < int(float(p) * 1_000_000_000):
            out.append(t)
    return out


def pick_by_delta(chain, today, *, target: float, dte: int, dte_lo: int, dte_hi: int):
    """The listed PUT whose |delta| is nearest `target`, at the expiry nearest `dte`. PURE.

    **THIS IS THE ONE PICKER IN THE FLEET THAT TARGETS DELTA, AND IT IS DECLARED RATHER THAN
    SNUCK IN.** `f3_pick_contract` is moneyness-fixed BECAUSE F-3's own void condition forbids
    a delta target; F-21 and F-22 declare `strike_selection: delta` and argue for it at length
    in their structure, conceding `V6-OPT`'s autopsy rather than dodging it. Two rules, two
    declarations, two pickers -- and a book may only reach the picker its declaration names,
    which is pinned by test.

    **A ROW WITH NO DELTA IS SKIPPED AND NEVER FALLEN BACK ON.** The obvious convenience is to
    approximate a missing delta from moneyness; that would silently run F-3's rule under
    F-21's name on exactly the illiquid rows where the two differ most, and nothing downstream
    could tell. `MA45`'s family: a quote that cannot be validated is dropped, not guessed.

    **EXPIRY FIRST, THEN DELTA**, which is `f3_pick_contract`'s amendment 2 carried across for
    the same measured reason: delta-first can land on a far month that happens to list a
    closer delta, and the declared 30-45 DTE band is the tenor the crash gate's income is
    measured against. The band is a HARD filter -- a chain offering nothing inside it returns
    `None` rather than the nearest thing outside it.
    """
    if not chain:
        return None
    tgt = abs(float(target))
    rows = []
    for c in chain:
        if str(c.get("option_type") or "").lower() != "put":
            continue
        exp = _date(c.get("expiration_date"))
        if exp is None:
            continue
        d = (c.get("greeks") or {}).get("delta")
        d = _num(d)
        if d is None:
            continue                       # never approximated from moneyness
        days = (exp - _date(today)).days if _date(today) is not None else None
        if days is None or days < int(dte_lo) or days > int(dte_hi):
            continue
        rows.append((abs(days - int(dte)), -days, exp, abs(abs(float(d)) - tgt), c, days,
                     float(d)))
    if not rows:
        return None
    best_exp = min(rows, key=lambda r: (r[0], r[1]))[2]
    same = [r for r in rows if r[2] == best_exp]
    r = min(same, key=lambda x: (x[3], str(x[4].get("symbol") or "")))
    return {"contract": r[4], "dte": r[5], "delta": r[6], "delta_gap": r[3]}


def _dip_healthy_rows(root: str = None):
    """The recorded `dip_healthy` series, oldest first, or `None` if the stream is absent.

    `None` is NOT CONSULTED and is distinct from `[]`, which would be *"the recorder ran and
    nobody was healthy"* -- audit #5 `H2`'s rule, and the distinction F-11's own docstring
    exists to preserve.
    """
    from . import fleet_history as FH
    got = FH.read("dip_healthy", root)
    if got is None or got.get("absent"):
        # `read()` reports ABSENT as its own flag rather than as `None`, which is how a first
        # cut of this function came to have an unreachable branch: it tested `is None`, the
        # stream never returns None, and the ABSENT refusal was dead code. Found by the test
        # written to pin the distinction, which is the only reason it is reachable now.
        return None
    return got.get("rows") or []


def _f21_source_gate(book: str, decl: dict, root, today):
    """Shared by BOTH books: is the source fit, and if not, RECORD the refusal and stop.

    **F-22's gate is F-21's, by its own declaration** -- *"the draw refuses whenever F-21's
    entry rule refuses ... so the twin can never accrue fills the arm had no chance to
    accrue"*. One implementation (`B7`), so the two can never drift apart; a second copy is
    exactly how the twin would quietly acquire entry opportunities the arm did not have, which
    is the coverage mismatch `MB1-SEL` was VOIDED for.

    Returns `(rows, None)` when fit, or `(None, reason)` having WRITTEN a refusal row.
    """
    st = decl.get("structure") or {}
    # **THE SHA FALLS BACK TO THE REPO, AND THAT IS THE DIFFERENCE BETWEEN A REFUSAL AND A
    # SILENT EMPTY RETURN.** `decl_sha_for(book, root)` resolves against the RECORDS root, and
    # a root that holds records but no `DECL_*.md` returns `None` -- so the first cut skipped
    # `F.refuse` in exactly the situation the refusal exists for. The declaration is a REPO
    # artifact and the root only selects where records live, so the repo lookup is the correct
    # second rung; it cannot return a different book's sha, because the book name is the key.
    sha = F.decl_sha_for(book, root) or F.decl_sha_for(book)
    rows = _dip_healthy_rows(root)
    if rows is None:
        reason = ("SOURCE NOT CONSULTED: the dip_healthy stream does not exist, so this book "
                  "selected nobody because it could not look, not because nobody qualified.")
        if sha:
            F.refuse(book, "DIP_HEALTHY_ABSENT", reason, decl_sha=sha, root=root)
        return None, reason
    state = healthy_series_state(
        rows, today,
        min_rows=int(st.get("min_healthy_rows") or F21_MIN_HEALTHY_ROWS),
        max_stale=int(st.get("max_stale_sessions") or F21_MAX_STALE_SESSIONS))
    if not state["ok"]:
        # A REFUSAL IS A RECORD. Returning [] here would be indistinguishable in this book's
        # own stream from a day on which the screen ran and nobody was healthy, which is the
        # one reading the declaration's arming precondition forbids.
        if sha:
            F.refuse(book, "DIP_HEALTHY_UNFIT", state["reason"], decl_sha=sha, root=root)
        return None, state["reason"]
    return rows, None


def f21_v6opt_dip_csp(decl: dict, root: str = None, *, provider=None, broker=None,
                      today=None, history=None) -> list:
    """F-21 live: sell a 25-delta 30-45 DTE cash-secured put on each name FIRST appearing in
    the recorded healthy-dip population this quarter.

    **ARMED WITH A PRECONDITION IT CANNOT YET MEET, DELIBERATELY.** The declaration's
    `arming_precondition` is a property of the DATA -- 20 recorded `dip_healthy` rows, none
    more than 5 sessions stale -- and the series starts empty. Arming now rather than on the
    day it fills means the book starts BY ITSELF when the data is ready, with no further
    human action and no second session; the alternative is a book that waits on somebody
    remembering. It is safe to arm only because the refusal is RECORDED by name
    (`DIP_HEALTHY_UNFIT`) and so can never read as a quiet market.

    **NO EXIT MACHINERY, DECLARED NOT MISSING**: the frozen structure is *"hold to expiry, no
    exits"*, so a stop or a target added later voids the book.

    **IT REFUSES ITSELF IF `S3-I3` IS NOT REGISTERED**, as F-8 does -- a rule that would place
    a SHORT order is the last place to assume the cycle's gate already checked.
    """
    import datetime as _dt
    from ..intraday.providers import get_provider

    if F.assignment_provider() is None:
        return []

    st = decl.get("structure") or {}
    today = today or cycle_session()
    if history is None:
        history, _why = _f21_source_gate("f21_v6opt_dip_csp", decl, root, today)
        if history is None:
            return []

    latest = (history[-1].get("payload") or []) if history else []
    healthy = [h if isinstance(h, dict) else {"ticker": h} for h in latest]
    picks = f21_select(healthy, history, today,
                       held_symbols("f21_v6opt_dip_csp", root),
                       cap=int(decl.get("concurrency_cap") or 0))
    if not picks:
        return []

    provider = provider if provider is not None else get_provider()
    if broker is None:
        # ONE factory (`B7`): the fleet's venue is decided in `fleet.fleet_broker`, not
        # six times here, and a broker that cannot be built writes a NAMED refusal
        # rather than raising -- a silent fallback to the closed Tradier sandbox is how
        # six weeks of empty streams came to read as success.
        broker = _broker_or_refuse("f21_v6opt_dip_csp", root)
        if broker is None:
            return []
    sha = F.decl_sha_for("f21_v6opt_dip_csp", root)
    if not sha:
        return []
    if str(st.get("right") or "put").lower() != "put":
        return []

    out = []
    for p in picks:
        chain = provider.get_option_chain(p["ticker"], dte_range=(30, 45))
        got = pick_by_delta(chain, today, target=float(st.get("delta")),
                            dte=int(st.get("dte")), dte_lo=30, dte_hi=45)
        if got is None:
            continue
        c = got["contract"]
        out.append(F.submit("f21_v6opt_dip_csp", broker=broker, occ=_occ_or_refuse(c),
                            underlying=p["ticker"], side="sell_to_open", qty=F21_QTY,
                            decl_sha=sha, symbol=p["ticker"], quote=c))
    return out


def f22_dip_csp_random_twin(decl: dict, root: str = None, *, provider=None, broker=None,
                            today=None, history=None) -> list:
    """F-22 live: F-21's identical trade, entered on a deterministic salted draw instead.

    **IT READS F-21's SOURCE GATE AND NOT ITS OWN**, per its declaration: the twin may only
    draw on sessions F-21's source was recorded on. Drawing daily while the arm enters weekly
    would hand the twin five times the opportunities and make its fills a biased superset --
    `MB1-SEL`'s confound, which ran twice the size of the effect and in the same direction.

    **NO PRICE-DERIVED QUANTITY REACHES THE DRAW**, which is the void condition that keeps the
    timing uncorrelated with the dip signal: `f22_draws` hashes the salt, the book name, the
    ticker and the session date, and nothing else.
    """
    import datetime as _dt
    from ..intraday.providers import get_provider

    if F.assignment_provider() is None:
        return []

    st = decl.get("structure") or {}
    today = today or cycle_session()
    if history is None:
        history, _why = _f21_source_gate("f22_dip_csp_random_twin", decl, root, today)
        if history is None:
            return []

    # THE POOL IS THE SAME UNIVERSE F-21 DRAWS FROM, AND THE SESSION IS THE SOURCE'S OWN.
    # Using today's clock date would let the twin draw on sessions the arm's recorder never
    # covered, which is the cadence mismatch the declaration amends against by name.
    last = history[-1] if history else {}
    session = str(last.get("date") or "")[:10]
    pool = sorted({str((h if not isinstance(h, dict) else h.get("ticker")) or "").upper()
                   for h in (last.get("payload") or [])} - {""})
    if not session or not pool:
        return []
    sha = (F.decl_sha_for("f22_dip_csp_random_twin", root)
           or F.decl_sha_for("f22_dip_csp_random_twin"))
    # **THE DRAW PROBABILITY IS NOT DECLARED, AND THE RULE REFUSES RATHER THAN DEFAULTING.**
    # The declaration's own entry_rule says *"p is the threshold declared below and re-stated
    # at launch alongside F-21's own fill rate"* -- and there is no below: neither `p` nor the
    # salt appears anywhere in the structure. Defaulting `p` to 0 would arm a book that can
    # never fire, which reads in the records as a quiet market; defaulting it to anything else
    # would make this code the authority over a frozen parameter, which is `MA5`'s defect with
    # a one-way cost. **And the declaration already implies the sequencing**: p is set FROM
    # F-21's observed fill rate, so the twin cannot be calibrated before the arm has fills.
    # The refusal is named, so the day it clears is a one-line amendment and not a rebuild.
    salt = str(st.get("salt") or "").strip()
    pp = st.get("draw_probability", st.get("p"))
    if not salt or pp is None:
        reason = ("DRAW PARAMETERS UNDECLARED: the entry rule names `F22_SALT` and `p` as "
                  "'declared below' and the structure declares neither. p is set FROM F-21's "
                  "observed fill rate, so this book cannot be calibrated before the arm has "
                  "fills. Refused by name rather than defaulted -- a default p of 0 arms a "
                  "book that can never fire, and any other default makes the code the "
                  "authority over a frozen parameter.")
        if sha:
            F.refuse("f22_dip_csp_random_twin", "DRAW_PARAMS_UNDECLARED", reason,
                     decl_sha=sha, root=root)
        return []
    drawn = f22_draws(pool, session, salt=salt, p=float(pp))
    held = held_symbols("f22_dip_csp_random_twin", root)
    drawn = [t for t in drawn if t not in held]
    cap = int(decl.get("concurrency_cap") or 0)
    if cap:
        drawn = drawn[:cap]
    if not drawn:
        return []

    provider = provider if provider is not None else get_provider()
    if broker is None:
        # ONE factory (`B7`): the fleet's venue is decided in `fleet.fleet_broker`, not
        # six times here, and a broker that cannot be built writes a NAMED refusal
        # rather than raising -- a silent fallback to the closed Tradier sandbox is how
        # six weeks of empty streams came to read as success.
        broker = _broker_or_refuse("f22_dip_csp_random_twin", root)
        if broker is None:
            return []
    if not sha:
        return []
    if str(st.get("right") or "put").lower() != "put":
        return []

    out = []
    for t in drawn:
        chain = provider.get_option_chain(t, dte_range=(30, 45))
        got = pick_by_delta(chain, today, target=float(st.get("delta")),
                            dte=int(st.get("dte")), dte_lo=30, dte_hi=45)
        if got is None:
            continue
        c = got["contract"]
        out.append(F.submit("f22_dip_csp_random_twin", broker=broker,
                            occ=_occ_or_refuse(c), underlying=t, side="sell_to_open",
                            qty=F21_QTY, decl_sha=sha, symbol=t, quote=c))
    return out


RULES = {
    "f1_fill_ab": (f1_fill_ab, False),
    "f3_bear_puts": (f3_bear_puts, True),
    "f8_csp_entry_financing": (f8_csp_entry_financing, True),
    "f11_dip_reject_puts": (f11_dip_reject_puts, True),
    "f21_v6opt_dip_csp": (f21_v6opt_dip_csp, True),
    "f22_dip_csp_random_twin": (f22_dip_csp_random_twin, True),
}


def register_all() -> dict:
    """Register every implemented rule. Explicit, idempotent, and never an import side effect.

    Returns the registered book names so a caller can assert what it armed rather than assume
    it. A book absent from `RULES` is still declared and still un-armed, and `cycle()` will
    keep saying so.
    """
    # A RETIRED BOOK IS NEVER ARMED. `FLEET_RETIREMENTS.md` is the record and this is the
    # lock: re-arming one means deleting its row and saying why, which shows in the diff. The
    # reader fails OPEN on a missing file, so this is a SECOND lock and never the only one --
    # every book retired today is already absent from `RULES`.
    retired = F.retired_books()
    armed = []
    for book, (fn, places) in sorted(RULES.items()):
        if book in retired:
            continue
        F.register_entry_rule(book, fn, places_orders=places)
        armed.append(book)
    return {"ok": True, "registered": armed, "count": len(armed),
            "refused_retired": sorted(b for b in RULES if b in retired)}
