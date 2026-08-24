"""S3-I3 — the assignment and margin model every short-side forward book must carry.

Don's ruling #1: **no short book declares without it.** `SEASON3_MAP.md` tracks this as its own
deliverable; `PREREG_DRAFT_fleet_harness.md` (S3-I1) §1.4 is the interface it plugs into, and
§4's refusal test — *"a short book without the assignment module is REFUSED"* — is
`validate_declaration` below.

WHY A SHORT BOOK NEEDS ITS OWN MODULE AND CANNOT REUSE THE LONG ONE. Every settlement
convention this project owns was written for a book that BUYS options, and each one is wrong
by a sign when the book sells:

* `MA36` settles a worthless expiry at 0.00 and posts **-100%** — correct for a long holder,
  for whom a dead option is a total loss. For a SHORT the identical event is the best possible
  outcome: the obligation settles at exactly its intrinsic value, which is **zero**, and the
  full credit is retained. A short book that inherited MA36's rule would book its winners as
  total losses. `settle_short` and `test_short_book.py` pin the mirror.
* `options_sizing` makes the PREMIUM the capital at risk, because a long option cannot lose
  more than it cost. A short's exposure is the STRIKE, which is one to two orders of magnitude
  larger, and S3-I1 §1.4 makes the secured cash *"the denominator of every return quoted"*.
* Early exercise is the LONG holder's option. It is therefore the SHORT's risk, arriving
  unannounced, and it has no analogue at all in a long book.

THREE CONVENTIONS ENFORCED HERE, EACH BECAUSE IT HAS COST THIS PROJECT SOMETHING:

* **`raw_close` for anything touching a STRIKE, `close` only for a RETURN** (`U1-SPLIT`, then
  session 30's O6/O7/O17). Strikes are as-traded and the prepared `close` is split- and
  dividend-adjusted; settling a $300 strike against a $72 adjusted close books a ~76%
  assignment loss on a trade that never happened, and it fails SILENTLY because the trade still
  prices. Every entry point here demands `spot_basis` explicitly and REFUSES the adjusted one.
  The declaration is cheap and total; `portfolio_capacity.assert_raw_spot` is the MEASUREMENT
  that proves a series matches the declaration, and the two are deliberately different jobs
  rather than two copies of one (B7).
* **A missing expiry spot is a REFUSAL, never a guess.** `MA36`'s reasoning applies unchanged:
  substituting today's underlying books a fake outcome whenever the stock moved after expiry,
  with the error running in the flattering direction.
* **ONE definition of a settled put.** `csp_surface.settle_put` is V6-OPT's, it is landed, and
  660 real trades reproduce from it at max |delta| 0.000e+00. `settle_short` DELEGATES to it
  for the put case rather than reimplementing the arithmetic — `B7`'s nine-call-sites lesson,
  which `MA5` found again in the Harvey-Liu-Zhu hurdle and `I-3` in MA28's crash machinery.

NO BAR-SHAPED CONSTANT LIVES HERE. `I-3`'s design decision, for its stated reason: `MA5`
measured that a default is exactly how a threshold freezes, so a library default would let a
future declaration inherit a convention it never wrote down. Every choice a book could make
differently — the margin method, the price basis — is a keyword-only argument with NO default,
and `test_short_book.py` asserts the module contains no threshold-shaped literal.

WHAT THIS DOES NOT MODEL, named so it is not mistaken for modelled:

* **Naked shorts.** The scope is the Reg-T CASH-SECURED convention and the covered-call
  convention. A genuinely naked short needs the FINRA 4210 maintenance formula
  (`premium + max(20% x underlying - OTM, 10% floor)`, with its own per-contract minimum),
  which is not built here and is REFUSED by name rather than approximated.
* **The stock leg of a covered call.** This module returns the OPTION leg's P&L and the share
  consequence of assignment; the host book already owns the stock and already marks it.
  Modelling it here would double-count it.
* **Assignment PROBABILITY.** `early_assignment_flag` reports whether assignment is RATIONAL
  for the holder right now. Whether a particular holder acts is not observable and is not
  estimated.
"""
from __future__ import annotations

from typing import Optional

from valuation.edge import dividends as DIV
from valuation.edge.csp_surface import settle_put
from valuation.edge.options_fill import CONTRACT_MULTIPLIER

# The as-traded / adjusted distinction, spelled rather than passed as a bare bool, so a caller
# cannot get it right by accident or wrong by a typo -- an unknown basis is refused.
AS_TRADED = "as_traded"
ADJUSTED = "adjusted"

# The margin conventions this module implements. Naked is named so the refusal can name it.
CASH_SECURED_PUT = "cash_secured_put"
CASH_SECURED_PUT_NET = "cash_secured_put_net"
COVERED_CALL = "covered_call"
NAKED = "naked"

METHODS = (CASH_SECURED_PUT, CASH_SECURED_PUT_NET, COVERED_CALL)


class ShortBookError(ValueError):
    """A refusal. Raised rather than returned because every one of these is silent if ignored."""


# ------------------------------------------------------------------------------------------- #
# helpers
# ------------------------------------------------------------------------------------------- #
def _right(right) -> str:
    r = str(right or "").strip().lower()
    if r in ("c", "call"):
        return "call"
    if r in ("p", "put"):
        return "put"
    raise ShortBookError("right must be call or put, got %r" % (right,))


def _check_basis(spot_basis) -> str:
    """The U1-SPLIT guard, as a DECLARATION rather than a measurement.

    A caller that has not thought about the basis cannot pass this, which is the point: the
    defect it guards is invisible in the output, so the only reliable place to catch it is the
    call site. `portfolio_capacity.assert_raw_spot` is the separate, measured half -- it proves
    a price SERIES matches the declaration. Two jobs, not two copies of one definition.
    """
    b = str(spot_basis or "").strip().lower()
    if b == ADJUSTED:
        raise ShortBookError(
            "spot_basis=%r: option strikes are AS-TRADED and the prepared `close` is split- and "
            "dividend-adjusted, so settling a strike against it is the U1-SPLIT defect - it "
            "prices cleanly and is wrong by the split ratio. Use `raw_close` and declare "
            "spot_basis=%r." % (ADJUSTED, AS_TRADED))
    if b != AS_TRADED:
        raise ShortBookError(
            "spot_basis must be declared as %r (there is no default: an undeclared basis is how "
            "the adjusted series gets used by accident); got %r" % (AS_TRADED, spot_basis))
    return b


def _pos(x, name: str) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise ShortBookError("%s must be a number, got %r" % (name, x))
    if not (v > 0):
        raise ShortBookError("%s must be positive, got %r" % (name, x))
    return v


# ------------------------------------------------------------------------------------------- #
# 1. Assignment at expiry, per moneyness
# ------------------------------------------------------------------------------------------- #
def assignment_at_expiry(*, spot_at_expiry, strike, right, spot_basis, contracts: int = 1) -> dict:
    """Is the short assigned at expiry, and what does it owe?

    THE MONEYNESS RULE IS STRICT INEQUALITY, matching `csp_surface.settle_put` (`s < k`) and
    `paper_track`'s MA36 guard (`under < strike` for a put, `under > strike` for a call). Exactly
    at the money is NOT assigned and owes exactly zero. The OCC's real auto-exercise threshold is
    $0.01 in the money, which differs from this only on a knife edge; the divergence is NAMED
    rather than silently reconciled, because changing it would move a landed V6-OPT figure and
    that needs a decision, not a default.

    `intrinsic_obligation` is per share and is exactly what the short owes: `max(0, K - S)` for a
    put, `max(0, S - K)` for a call. It is ZERO for a worthless expiry, which is the mirror of
    MA36 and the single most important line in this module.

    A missing or non-positive `spot_at_expiry` RAISES. There is no fallback to a later quote --
    MA36's reasoning, unchanged: the substitution's error runs in the flattering direction.
    """
    r = _right(right)
    _check_basis(spot_basis)
    k = _pos(strike, "strike")
    n = int(contracts)
    if n <= 0:
        raise ShortBookError("contracts must be a positive integer, got %r" % (contracts,))
    if spot_at_expiry is None:
        raise ShortBookError(
            "spot_at_expiry is missing and this module will not guess it. Substituting a later "
            "quote books a fake outcome whenever the underlying moved after expiry, and the "
            "error runs in the flattering direction (MA36, and V6-OPT's settlement trap).")
    s = _pos(spot_at_expiry, "spot_at_expiry")

    assigned = (s < k) if r == "put" else (s > k)
    obligation = DIV.intrinsic(s, k, r)          # O21's definition, imported not re-derived
    mult = CONTRACT_MULTIPLIER * n
    return {
        "assigned": bool(assigned),
        "right": r,
        "strike": k,
        "spot_at_expiry": s,
        "moneyness": s / k,
        "intrinsic_obligation": float(obligation),          # per share
        "obligation_total": float(obligation) * mult,
        # what the position becomes. A short put assigned BUYS stock; a short call DELIVERS it.
        "shares_delta": (mult if (assigned and r == "put") else
                         (-mult if assigned else 0)),
        "cash_delta": ((-k * mult) if (assigned and r == "put") else
                       ((k * mult) if assigned else 0.0)),
        "spot_basis": AS_TRADED,
        "contracts": n,
    }


# ------------------------------------------------------------------------------------------- #
# 2. Margin / cash-securing -- the denominator of every return the book quotes
# ------------------------------------------------------------------------------------------- #
def secured_cash(*, method, strike, right, credit, contracts: int = 1,
                 underlying_at_entry=None) -> dict:
    """What the book must set aside, i.e. S3-I1 §1.4's return denominator.

    `cash_secured_put`      -- the full strike, credit NOT netted. This is V6-OPT's landed
                               convention (`settle_put` returns `pnl / k`), so it is the one a
                               book should choose unless it has a reason; 660 real trades tie it
                               to a published figure.
    `cash_secured_put_net`  -- strike less the credit already received. Brokers genuinely differ
                               here, so it is offered and must be DECLARED. It flatters the
                               return by roughly the credit fraction, and the report says so.
    `covered_call`          -- secured by SHARES, not cash. The denominator is the stock's value
                               at entry, which needs `underlying_at_entry`.

    A naked short is REFUSED BY NAME. The FINRA 4210 formula is a different model with its own
    maintenance mechanics and its own floor, and approximating it with a cash-secured number
    would understate the requirement -- the unsafe direction.
    """
    r = _right(right)
    m = str(method or "").strip().lower()
    n = int(contracts)
    if n <= 0:
        raise ShortBookError("contracts must be a positive integer, got %r" % (contracts,))
    if m == NAKED:
        raise ShortBookError(
            "method=%r is NOT modelled here. A naked short's requirement is FINRA 4210's "
            "premium plus the greater of 20 percent of the underlying less the out-of-the-money "
            "amount and a 10 percent floor, with a per-contract minimum -- a maintenance model "
            "this instrument does not build. Approximating it with a cash-secured figure "
            "UNDERSTATES the requirement, which is the unsafe direction. Declare a cash-secured "
            "or covered structure, or build the naked model in its own register." % (NAKED,))
    if m not in METHODS:
        raise ShortBookError("method must be one of %s, got %r" % (list(METHODS), method))

    k = _pos(strike, "strike")
    c = float(credit or 0.0)
    if c < 0:
        raise ShortBookError("credit is what the book RECEIVES for selling; it cannot be "
                             "negative, got %r" % (credit,))
    mult = CONTRACT_MULTIPLIER * n

    if m == COVERED_CALL:
        if r != "call":
            raise ShortBookError("method=%r applies to a short CALL; got right=%r" % (m, r))
        u = _pos(underlying_at_entry, "underlying_at_entry")
        per_share = u
        note = ("secured by SHARES the host book already owns; the denominator is the stock's "
                "value at entry, and this module does NOT mark the stock leg (the host does)")
    else:
        if r != "put":
            raise ShortBookError("method=%r applies to a short PUT; got right=%r" % (m, r))
        per_share = (k - c) if m == CASH_SECURED_PUT_NET else k
        note = ("full strike, credit not netted -- V6-OPT's landed convention"
                if m == CASH_SECURED_PUT else
                "strike less credit received; flatters the return versus the gross convention "
                "by roughly credit/strike, declared rather than assumed")
    if not (per_share > 0):
        raise ShortBookError("secured cash computed as %r per share, which cannot be a return "
                             "denominator (a credit at or above the strike is not a real quote)"
                             % (per_share,))
    return {"method": m, "secured_cash": float(per_share) * mult,
            # THE PER-SHARE FIGURE IS NOT DECORATION -- it is what the return is computed on, and
            # the reason is a defect this module's own B7 gate caught on the first real row.
            # `(pnl * 100) / (k * 100)` is NOT the same float as `pnl / k`: the multiplier
            # round-trip loses a bit, and `settle_put` divides by the bare strike. Scaling both
            # sides and then dividing was gratuitous arithmetic that broke an exact identity, so
            # the ratio is taken per share and the multiplier only ever scales absolute cash.
            "secured_per_share": float(per_share),
            "contracts": n, "multiplier": CONTRACT_MULTIPLIER,
            "credit_netted": (m == CASH_SECURED_PUT_NET), "note": note}


# ------------------------------------------------------------------------------------------- #
# 3. Settlement -- assignment and margin composed
# ------------------------------------------------------------------------------------------- #
def settle_short(*, strike, credit, spot_at_expiry, right, spot_basis, method,
                 contracts: int = 1, underlying_at_entry=None) -> dict:
    """One short option held to expiry, returned on its own secured cash.

    THE PUT CASE DELEGATES TO `csp_surface.settle_put` AND IS ASSERTED AGAINST IT. There is one
    definition of a settled put in this project and it is V6-OPT's; this function's job is to
    add the CALL case, the securing convention and the share consequence, not to have an opinion
    about the arithmetic. When the method is the gross cash-secured one the two must agree
    EXACTLY, and they are checked on every call rather than only in a test.
    """
    a = assignment_at_expiry(spot_at_expiry=spot_at_expiry, strike=strike, right=right,
                             spot_basis=spot_basis, contracts=contracts)
    sec = secured_cash(method=method, strike=strike, right=right, credit=credit,
                       contracts=contracts, underlying_at_entry=underlying_at_entry)
    c = float(credit or 0.0)
    pnl_per_share = c - a["intrinsic_obligation"]
    mult = CONTRACT_MULTIPLIER * int(contracts)
    pnl_total = pnl_per_share * mult
    # PER SHARE, deliberately. Dividing the scaled numerator by the scaled denominator loses a
    # bit and breaks the exact identity with `settle_put` -- see `secured_cash`'s own comment.
    ret = pnl_per_share / sec["secured_per_share"]

    if sec["method"] == CASH_SECURED_PUT:
        ref = settle_put(strike, credit, spot_at_expiry)
        if ref is None:
            raise ShortBookError("csp_surface.settle_put refused inputs this module accepted; "
                                 "the two definitions have diverged and that is a defect here")
        # Not a tolerance, and it earned that: this is now literally `pnl / k`, the same
        # operation on the same floats, so equality is exact by construction. A tolerance would
        # have hidden the multiplier round-trip that made it inexact in the first place.
        if (ref["assigned"] != a["assigned"] or ref["pnl_per_share"] != pnl_per_share
                or ref["ret_on_strike"] != ret):
            raise ShortBookError(
                "B7 VIOLATION: this module and csp_surface.settle_put disagree - "
                "assigned %r/%r, pnl %r/%r, ret %r/%r"
                % (a["assigned"], ref["assigned"], pnl_per_share, ref["pnl_per_share"],
                   ret, ref["ret_on_strike"]))

    out = dict(a)
    out.update({
        "credit": c,
        "pnl_per_share": pnl_per_share,
        "pnl_total": pnl_total,
        "secured_cash": sec["secured_cash"],
        "margin_method": sec["method"],
        "ret_on_secured": ret,
        "expired_worthless": (not a["assigned"]),
        # NAMED ON THE ROW rather than left to the docstring, because a covered call's option
        # leg looks like a loss exactly when the position did well: `credit - (S - K)` goes
        # negative as the stock rises through the strike, and the stock leg the host book holds
        # is what offsets it. A consumer summing `pnl_total` across a collar or a covered-call
        # book without reading this field would report the overlay as the whole position.
        "pnl_scope": ("option_leg_only; the host book marks the shares"
                      if sec["method"] == COVERED_CALL else "whole_position"),
    })
    return out


# ------------------------------------------------------------------------------------------- #
# 4. Early assignment -- O21's machinery, imported
# ------------------------------------------------------------------------------------------- #
def early_assignment_flag(*, right, spot, strike, option_bid, spot_basis,
                          divs: Optional[dict] = None, ticker: Optional[str] = None,
                          as_of=None, expiry=None) -> dict:
    """Is early assignment RATIONAL for the holder right now?

    TWO TRIGGERS, AND THE ASYMMETRY BETWEEN THE RIGHTS IS REAL RATHER THAN TIDINESS.

    1. **Model-free (`O21`'s D1, imported).** `dividends.exercise_gain` is what a holder leaves
       on the table by SELLING at the bid instead of exercising. Strictly positive means
       exercising dominates, so the short should expect assignment. This applies to BOTH rights
       and needs no dividend model, no rate and no volatility -- which is why O21 was allowed to
       carry a verdict on it.

    2. **Dividend-driven, SHORT CALLS ONLY.** A holder exercises an in-the-money call the day
       before an ex-date to capture the dividend. For a short PUT the same dividend runs the
       OTHER WAY -- holding the stock pays you, so a dividend DISCOURAGES early put exercise,
       whose real driver is interest on the strike. Flagging a short put on dividend grounds
       would be a sign error, so it is not done, and the exposure is reported as a note instead.

    `q_trailing` is reported when a ticker and dividend table are supplied, because `O21`
    established it is the point-in-time one; `q_scheduled` reads the contract's life and O21's
    register forbids it from carrying a verdict, so it is reported ONLY as a labelled secondary.
    Neither DRIVES the flag -- the ex-date census does -- but a book's declaration needs the
    number and would otherwise compute its own.

    This is a RATIONALITY flag, not a probability. Whether a given holder acts is unobservable,
    so no rate is estimated and none may be read off this.
    """
    r = _right(right)
    _check_basis(spot_basis)
    s = _pos(spot, "spot")
    k = _pos(strike, "strike")
    bid = float(option_bid or 0.0)
    if bid < 0:
        raise ShortBookError("option_bid cannot be negative, got %r" % (option_bid,))

    itm = (s < k) if r == "put" else (s > k)
    gain = DIV.exercise_gain(bid, s, k, r)               # O21, imported
    model_free = bool(gain > 0.0)

    ex_dates, q_pit, q_life = [], None, None
    if divs is not None and ticker and as_of is not None and expiry is not None:
        ex_dates = [str(d) for d, _ in DIV.dividends_between(divs, ticker, as_of, expiry)]
        q_pit = DIV.q_trailing(divs, ticker, as_of, s)
        q_life = DIV.q_scheduled(divs, ticker, as_of, expiry, s)

    dividend_driven = bool(r == "call" and itm and ex_dates)
    return {
        "right": r,
        "in_the_money": bool(itm),
        "flagged": bool(model_free or dividend_driven),
        "model_free_trigger": model_free,
        "exercise_gain": float(gain),
        "dividend_trigger": dividend_driven,
        "ex_dates_in_window": ex_dates,
        "q_trailing": q_pit,                 # O21: point-in-time, may carry a verdict
        "q_scheduled": q_life,               # O21: reads the contract's life, may NOT
        "q_scheduled_is_secondary": True,
        "note": ("a dividend inside the window DISCOURAGES early exercise of a short put, whose "
                 "driver is interest on the strike, so no dividend flag is raised on this right"
                 if r == "put" else
                 "an in-the-money short call is assignable the day before any ex-date"),
    }


# ------------------------------------------------------------------------------------------- #
# 5. The declaration validator -- S3-I1 §4's refusal, in code
# ------------------------------------------------------------------------------------------- #
REQUIRED_SHORT_FIELDS = ("assignment_model", "margin_method", "spot_basis",
                         "early_assignment_flag", "return_denominator")


def is_short_book(decl: dict) -> bool:
    """Does this declaration sell premium? An explicit field, never inferred from prose.

    Inferring it from a structure string would make the refusal depend on wording, and a book
    that phrased itself unusually would slip the gate silently -- which is the whole failure.
    """
    if not isinstance(decl, dict):
        raise ShortBookError("declaration must be a mapping, got %r" % type(decl).__name__)
    v = decl.get("sells_premium")
    if v is None:
        raise ShortBookError(
            "declaration does not state `sells_premium`. It is mandatory for EVERY book, not "
            "only short ones: an absent field would let a short book pass by omission, which is "
            "exactly the refusal S3-I1 section 4 asks for.")
    if not isinstance(v, bool):
        raise ShortBookError("`sells_premium` must be a bool, got %r" % (v,))
    return v


def validate_declaration(decl: dict) -> dict:
    """REFUSE a short book that does not carry the assignment module. S3-I1 sections 1.4 and 4.

    Returns a report for the harness's records on success and RAISES on failure, because a
    refusal that returns a flag is a refusal somebody forgets to read.
    """
    short = is_short_book(decl)
    if not short:
        return {"sells_premium": False, "short_module_required": False,
                "ok": True, "note": "long-only book; the short module does not apply"}

    missing = [f for f in REQUIRED_SHORT_FIELDS if not decl.get(f)]
    if missing:
        raise ShortBookError(
            "SHORT BOOK REFUSED (Don's ruling #1, S3-I1 section 1.4): the declaration is missing "
            "%s. A book that sells premium must state how assignment is modelled, how the "
            "position is secured, which price basis settles a strike, how early assignment is "
            "flagged, and which denominator its returns are quoted on." % (missing,))

    method = str(decl.get("margin_method") or "").strip().lower()
    if method == NAKED:
        raise ShortBookError(
            "SHORT BOOK REFUSED: margin_method=%r is not modelled by this instrument (see "
            "`secured_cash`). Declare a cash-secured or covered structure." % (NAKED,))
    if method not in METHODS:
        raise ShortBookError("SHORT BOOK REFUSED: margin_method must be one of %s, got %r"
                             % (list(METHODS), decl.get("margin_method")))

    basis = str(decl.get("spot_basis") or "").strip().lower()
    if basis != AS_TRADED:
        raise ShortBookError(
            "SHORT BOOK REFUSED: spot_basis must be %r. Strikes are as-traded; settling one "
            "against the adjusted series is the U1-SPLIT defect and it fails silently."
            % (AS_TRADED,))

    denom = str(decl.get("return_denominator") or "").strip().lower()
    if denom != "secured_cash":
        raise ShortBookError(
            "SHORT BOOK REFUSED: S3-I1 section 1.4 makes the secured cash the denominator of "
            "every return quoted; return_denominator reads %r. A short's return quoted on the "
            "premium overstates it by roughly strike/premium, which on this book's own numbers "
            "is one to two orders of magnitude." % (decl.get("return_denominator"),))

    return {"sells_premium": True, "short_module_required": True, "ok": True,
            "margin_method": method, "spot_basis": basis, "return_denominator": denom,
            "fields_checked": list(REQUIRED_SHORT_FIELDS)}


# ------------------------------------------------------------------------------------------- #
# 6. THE S3-I1 SEAM -- `fleet.ASSIGNMENT_INTERFACE`, satisfied
# ------------------------------------------------------------------------------------------- #
# `S3-I1` landed AFTER this module was frozen against its DRAFT, and it defines a concrete
# provider seam this module must satisfy or **every short book in the fleet is REFUSED**
# (`fleet.py`: *"Until r1 lands one, every short book is REFUSED"*, refusal code
# `SHORT_BOOK_WITHOUT_ASSIGNMENT`). The seam is duck-typed on three callables, deliberately, so
# that `fleet` never imports a module that might not exist.
#
# THE ADAPTER ADDS NO ARITHMETIC. Every number below comes from the functions above, which are
# the ones validated against V6-OPT's 660 real settled puts at max |delta| 0.000e+00. A seam
# that re-derived its own assignment would be the `B7` defect at the exact join it exists to
# make -- and `fleet`'s own docstring says it "computes no assignment and no margin", so if this
# adapter computed any, the project would have two.

import re as _re

# NOT bars, and named so the no-threshold guard can tell the difference. `1000` is the OCC
# symbol format's own strike scale (strikes are encoded in thousandths) and `1e-9` is a
# float-equality tolerance for comparing two spellings of the same strike. Neither is a
# pre-registrable threshold, which is what `I-3`'s no-default rule is about.
_OCC_STRIKE_SCALE = 1000.0
_STRIKE_EPS = 1e-9

_OCC = _re.compile(r"^\s*(?P<root>[A-Z][A-Z0-9.\-]{0,5})\s*"
                   r"(?P<yy>\d{2})(?P<mm>\d{2})(?P<dd>\d{2})"
                   r"(?P<right>[CP])(?P<strike>\d{8})\s*$")


def parse_occ(occ) -> dict:
    """`AAPL  260619C00150000` -> root, expiry, right, strike.

    REFUSES anything it cannot parse rather than guessing a strike. A mis-parsed strike is the
    U1-SPLIT failure in a new costume: it would price cleanly and settle against the wrong
    number, and nothing would raise.
    """
    m = _OCC.match(str(occ or "").upper())
    if not m:
        raise ShortBookError(
            "cannot parse %r as an OCC option symbol (expected ROOT + YYMMDD + C/P + strike in "
            "thousandths, e.g. 'AAPL  260619C00150000'). Refusing rather than guessing a "
            "strike." % (occ,))
    g = m.groupdict()
    return {"root": g["root"], "expiry": "20%s-%s-%s" % (g["yy"], g["mm"], g["dd"]),
            "right": "call" if g["right"] == "C" else "put",
            "strike": int(g["strike"]) / _OCC_STRIKE_SCALE}


class _AssignmentProvider(object):
    """`fleet.ASSIGNMENT_INTERFACE`'s three callables, delegating to this module."""

    interface_version = "S3-I3/1"

    def assign_at_expiry(self, occ, settle_price, side, qty) -> dict:
        """`(occ, settle_price, side, qty) -> {assigned, shares, cash, basis}`.

        `settle_price` MUST be the as-traded close. The seam cannot police that from a bare
        float, so the basis is DECLARED in the return and every path here runs through
        `_check_basis` -- a caller that hands over an adjusted price gets a wrong answer this
        module cannot detect, which is why `basis` ships on the row for the recorder to keep and
        why `portfolio_capacity.assert_raw_spot` remains the measured half.

        `side` is `fleet.SIDES`. A SHORT is assigned; a LONG auto-exercises, which is the exact
        mirror -- so the long case is the short case negated rather than a second derivation.
        """
        s = str(side or "").strip().lower()
        if s not in ("long", "short"):
            raise ShortBookError("side must be 'long' or 'short' (fleet.SIDES), got %r" % (side,))
        p = parse_occ(occ)
        a = assignment_at_expiry(spot_at_expiry=settle_price, strike=p["strike"],
                                 right=p["right"], spot_basis=AS_TRADED, contracts=qty)
        sign = 1 if s == "short" else -1
        return {"assigned": a["assigned"],
                "shares": int(sign * a["shares_delta"]),
                "cash": float(sign * a["cash_delta"]),
                "basis": AS_TRADED,
                # beyond the seam's four keys, and useful to the recorder: what is owed.
                "intrinsic_obligation": a["intrinsic_obligation"],
                "right": p["right"], "strike": p["strike"], "expiry": p["expiry"]}

    def early_assignment_flag(self, occ, as_of, q, *, spot=None, option_bid=None,
                              divs=None) -> dict:
        """`(occ, as_of, q) -> {flagged, reason}`, with O21's fuller test available.

        THE SEAM'S THREE ARGUMENTS CANNOT REACH O21's STRONGEST TEST, and that is stated rather
        than papered over. `exercise_gain` -- the model-free trigger O21 was allowed to carry a
        verdict on -- needs the SPOT and the option's BID, and the seam passes neither. With
        `(occ, as_of, q)` alone the only honest signal is the dividend one, which applies to
        short CALLS only (a dividend DISCOURAGES early exercise of a put, whose driver is
        interest on the strike, so flagging one would be a sign error).

        `spot` and `option_bid` are keyword-only EXTRAS. The harness calls with three positional
        arguments and gets the dividend reading; a caller holding a quote gets the model-free
        test too. Optional, so the seam is satisfied either way.
        """
        p = parse_occ(occ)
        if spot is not None and option_bid is not None:
            f = early_assignment_flag(right=p["right"], spot=spot, strike=p["strike"],
                                      option_bid=option_bid, spot_basis=AS_TRADED,
                                      divs=divs, ticker=p["root"], as_of=as_of,
                                      expiry=p["expiry"])
            reason = ("holder does better exercising than selling (O21 model-free, gain %.4f)"
                      % f["exercise_gain"]) if f["model_free_trigger"] else (
                      "in-the-money short call with an ex-date inside the window"
                      if f["dividend_trigger"] else "no trigger")
            return {"flagged": f["flagged"], "reason": reason, "detail": f}

        try:
            qy = float(q)
        except (TypeError, ValueError):
            qy = 0.0
        divi = bool(p["right"] == "call" and qy > 0.0)
        return {
            "flagged": divi,
            "reason": ("a dividend-paying underlying (q=%.4f) makes an in-the-money short call "
                       "assignable around any ex-date" % qy) if divi else
                      ("a dividend DISCOURAGES early exercise of a put, whose driver is interest "
                       "on the strike, so q raises no flag on this right" if p["right"] == "put"
                       else "no dividend yield, so no ex-date trigger"),
            "detail": {"q": qy, "right": p["right"], "as_of": str(as_of),
                       "moneyness_unknown": True,
                       "limitation": ("the seam passes no spot and no bid, so O21's model-free "
                                      "exercise_gain test could not run and this flag is the "
                                      "dividend reading only -- pass spot= and option_bid= for "
                                      "the full test")}}

    def secured_cash(self, occ, strike, qty) -> float:
        """`(occ, strike, qty) -> float`, the Reg-T cash-secured convention.

        This IS the denominator of every return the book quotes (`S3-I1` section 1.4). The
        seam's `strike` is redundant with `occ` and is therefore CROSS-CHECKED rather than
        trusted: a disagreement means the caller and the symbol describe different contracts,
        which is exactly the mismatch that settles a trade against the wrong number.

        A short CALL is REFUSED here. Cash-securing a call is unbounded -- that is a naked
        short, which this instrument does not model. A covered call is secured by SHARES, so its
        denominator needs the stock price and the caller must ask for it explicitly.
        """
        p = parse_occ(occ)
        k = _pos(strike, "strike")
        if abs(k - p["strike"]) > _STRIKE_EPS:
            raise ShortBookError(
                "strike %r disagrees with the OCC symbol's %r (%s). One of them describes a "
                "different contract, and settling against the wrong one fails silently."
                % (k, p["strike"], occ))
        if p["right"] != "put":
            raise ShortBookError(
                "secured_cash's Reg-T CASH-SECURED convention applies to a short PUT. %s is a "
                "CALL: cash-securing one is unbounded (that is a naked short, not modelled "
                "here), and a COVERED call is secured by shares -- call "
                "`secured_cash(method=COVERED_CALL, ..., underlying_at_entry=...)` directly, "
                "which needs the stock price the seam does not pass." % (occ,))
        return secured_cash(method=CASH_SECURED_PUT, strike=k, right="put", credit=0.0,
                            contracts=qty)["secured_cash"]


PROVIDER = _AssignmentProvider()


def register(fleet_module=None) -> dict:
    """Hand `PROVIDER` to `fleet.register_assignment_provider`. Until this runs, every short
    book is refused with `SHORT_BOOK_WITHOUT_ASSIGNMENT`.

    Registration is an explicit CALL and never an import side effect, so importing this module
    to read one number cannot silently unblock every short book in the fleet. `fleet_module` is
    injectable for tests; `fleet` does not import this module (its check is duck-typed on
    purpose), so the dependency runs one way only.
    """
    if fleet_module is None:
        from valuation.edge import fleet as fleet_module
    return fleet_module.register_assignment_provider(PROVIDER)
