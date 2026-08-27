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
    today = today or _dt.date.today()

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
        from .paper_broker import PaperBroker
        broker = PaperBroker()

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
        out.append(F.submit("f11_dip_reject_puts", broker=broker, occ=str(c.get("symbol")),
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
    d = (today or _dt.date.today()).isoformat()
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
RULES = {
    "f1_fill_ab": (f1_fill_ab, False),
    "f3_bear_puts": (f3_bear_puts, True),
    "f8_csp_entry_financing": (f8_csp_entry_financing, True),
    "f11_dip_reject_puts": (f11_dip_reject_puts, True),
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
