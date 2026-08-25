"""S3-I1 THE FLEET HARNESS -- the convention, enforced, plus the recorder that enforces it.

Register: `PREREG_s3i1_fleet_harness.md` (accepted from the Frontier Scout's draft, committed
ALONE). **Zero trials.** This module states no hypothesis, sets no bar, returns no verdict and
computes no outcome relationship. It RECORDS.

WHAT A FLEET BOOK IS, and every clause below is enforced by code in this file rather than
promised in prose:

  1. A declaration `DECL_<book>.md` **committed ALONE, before the book's first fill**. The
     commit is the tamper-evidence, so it is checked against git: the file's introducing
     commit must exist, must be an ANCESTOR of HEAD, and must have touched EXACTLY ONE file.
  2. Append-only records through `valuation.edge.append_only` -- the same implementation the
     contract-bound track history uses, keyed here on a monotone sequence rather than a date,
     because a book records many orders per day (register section E2).
  3. Fill recording is V5-grade: **bid, ask and mid at submission**, order type, fill price,
     time-to-fill, unfilled fate. Those first three are precisely the columns
     `scripts/slippage_report.py` says it needed and could not recover -- *"the fix is two
     columns written in `_place_entry` ... this is ROUTED"*. Nobody took it; the fleet does.
  4. A short book models assignment and margin or **it is REFUSED**. `S3-I3` builds that
     model; this file defines the interface and refuses in its absence.
  5. One ledger row per book at declaration; amended at verdict.
  6. `O11` binds every book. Sandbox only. **Nothing here licenses real money.**

TRIAL ACCOUNTING (register section 2, and section E4 is why it is enforceable). **One trial
per book, charged at FIRST VERDICT READ, not at declaration.** A meter read IS a verdict read,
so **every meter read is itself a record** -- otherwise the rule is an honour system and
"nobody peeked" is a memory rather than a dated fact.

WHAT THE HASH CHAIN BUYS, STATED AS THE BOUND RATHER THAN THE CLAIM (register section E3).
Each row carries the hash of the row before it, anchored at the DECLARATION's content hash.
That detects **reordering, an interior deletion, a truncation, and any edit by anything that
does not recompute the chain**. It is **NOT tamper-proof against a writer that recomputes the
chain.** Records live under `data/`, which is gitignored, so no committed literal can anchor a
growing stream -- the declaration is the strongest anchor available and the draft's appeal to
`MA13`'s committed-literal idiom does not carry.

SANDBOX FILLS ARE OPTIMISTIC, and the caveat is stamped on every fill rather than remembered.
Tradier's sandbox quotes are delayed ~15 minutes and its fills are simulated against them, so
**a measured cost BELOW the model is the direction the measurement error already points and is
weak evidence; a measured cost ABOVE the model runs against the bias.**
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import time as _time
import json
import os
import re
import subprocess
from typing import Optional

from . import append_only as AO
# NOTE: `assignment.py` (S3-I3) is deliberately NOT imported -- see THE S3-I3 SEAM below.
from . import track_meter as TM

# ---------------------------------------------------------------------------------------
# The convention, as a quotable string. Every declaration carries clause 6 VERBATIM.
# ---------------------------------------------------------------------------------------
O11_SENTENCE = ("O11 binds this book: positive per-trade expectancy is not survivability. "
                "Sandbox only. Nothing here licenses real money.")

SANDBOX_CAVEAT = ("Tradier sandbox quotes are delayed ~15 minutes and fills are simulated "
                  "against them, so a measured cost BELOW the model is the direction the "
                  "measurement error already points and is weak evidence; a measured cost "
                  "ABOVE the model runs against the bias.")

CHAIN_BOUND = ("The chain detects reordering, interior deletion, truncation and any edit by "
               "anything that does not recompute it. It is NOT tamper-proof against a writer "
               "that recomputes the chain. Its anchor is the declaration's content hash.")

# ---------------------------------------------------------------------------------------
# Record schema. `seq` is the key: zero-padded so lexicographic order IS append order, which
# is what makes `append_only`'s "at or before the last key is REFUSED" mean "out of order".
# ---------------------------------------------------------------------------------------
SEQ_WIDTH = 8
RECORD_COLUMNS = (
    "seq", "ts", "kind", "book", "decl_sha", "prev_hash", "row_hash",
    # --- the V5-grade fill block ---
    "symbol", "occ", "side", "arm", "order_type", "qty",
    "quote_bid", "quote_ask", "quote_mid", "limit_price",
    "fill_price", "submitted_ts", "filled_ts", "time_to_fill_s", "fate", "fallback",
    "venue",
    # --- refusals, meter reads and lifecycle ---
    "refusal_code", "detail",
    # --- (C) multi-leg structures and first-class skips, added 2026-08-24 ---
    # ADDITIVE. `verify_chain` reads each file's OWN header, so streams written before these
    # existed still verify; and `harness_fingerprint` moves, so every book's day-1 self-check
    # goes STALE and must be re-run. That is the STALE state working, not a regression.
    "structure_id", "leg_index", "net_cost", "skip_reason",
)

EVENT_KINDS = ("selfcheck", "fill", "refusal", "meter_read", "close", "skip")

# Every clause a declaration must state. Absent -> REFUSED, and the refusal names the field.
REQUIRED_DECL_FIELDS = (
    "book", "domain", "hypothesis_class", "entry_rule", "structure", "universe",
    "sizing", "concurrency_cap", "side", "records_schema", "verdict_horizon",
    "verdict_grammar", "trial", "o11_sentence",
)
REQUIRED_HORIZON_FIELDS = (
    "expected_fills_per_month", "min_effect", "sigma", "rho", "alpha",
    "fills_needed", "earliest_honest_read",
)
# A short book states these or it does not exist (draft section 1.4, Don's ruling #1).
#
# THE LIST IS `S3-I3`'s, PINNED AS A LITERAL RATHER THAN IMPORTED, AND THE DISTINCTION IS THE
# WHOLE POINT. The seam DRIFTED between two lanes: this module froze `("assignment", "margin",
# "secured_cash_is_denominator")` before the model existed, and r1 landed the five below --
# none of the names shared. The runbook settles which WINS (*"confirm the interface text
# against the LANDED S3-I3"*): r1's five are the contract the model enforces and are strictly
# stronger, so they are adopted whole.
#
# It is a LITERAL because `assignment.py` states the dependency direction and this file must
# honour it: *"fleet does not import this module ... so the dependency runs one way only."*
# `tuple(_SB.REQUIRED_SHORT_FIELDS)` would have inverted that. Drift is caught instead by
# `test_fleet_harness`, which imports BOTH and asserts equality -- `MA13`'s committed-literal
# idiom, where the production code holds the literal and a test holds the comparison.
REQUIRED_SHORT_FIELDS = ("assignment_model", "margin_method", "spot_basis",
                         "early_assignment_flag", "return_denominator")

DOMAINS = ("equity", "options")
HYPOTHESIS_CLASSES = ("edge", "cost", "utility")
SIDES = ("long", "short")
STRIKE_SELECTION = ("moneyness", "fixed", "delta")

# ---------------------------------------------------------------------------------------
# THE S3-I3 SEAM -- SETTLED WITH r1, 2026-08-24, AND THE MIDDLE VERSION WAS THE WRONG ONE
#
# This module computes no assignment and no margin; `valuation/edge/assignment.py` (r1's) does.
#
# THE HISTORY MATTERS BECAUSE THE SEAM MOVED TWICE. `S3-I1` froze three duck-typed callables
# before any model existed. Mid-ceremony this file was "reconciled to the landed module" --
# repointed at `short_book.py`'s own five function names and importing it at module scope --
# on the runbook's instruction to confirm against the LANDED S3-I3. **That reconciliation is
# now REVERTED, and it was wrong on both counts.**
#
#   1. r1 had already built `_AssignmentProvider`, an ADAPTER exposing exactly the three names
#      frozen here. The interface never needed changing; r1 had adapted to it, which is what a
#      published interface is for. Chasing the module's internal names made this file depend
#      on r1's private vocabulary instead of on the contract between us.
#   2. `assignment.py` states the direction explicitly -- *"fleet does not import this module
#      (its check is duck-typed on purpose), so the dependency runs one way only"* -- and that
#      registration is *"an explicit CALL and never an import side effect, so importing this
#      module to read one number cannot silently unblock every short book in the fleet."*
#      The module-scope `from . import short_book` plus auto-registration was precisely that
#      side effect. r1's design is the better one and this file yields to it.
#
# THE COLLISION IS ALSO THE LESSON. The rename `short_book.py` -> `assignment.py` merged
# CLEANLY into this branch and the tree then DID NOT IMPORT: no file was edited by both sides,
# so there was no conflict to resolve and nothing to review. `MA23`'s `parity_flow` collision
# in a new costume -- a clean merge is not a safe one.
# ---------------------------------------------------------------------------------------
ASSIGNMENT_INTERFACE = {
    "module": "valuation.edge.assignment (S3-I3, r1's, LANDED). Registered by ITS OWN "
              "`assignment.register()`, never by an import here.",
    "callables": {
        "assign_at_expiry": "(occ, settle_price, side, qty) -> dict. The settle price must be "
                            "AS-TRADED: r1's C3 measured 29.1% of assignment verdicts flipping "
                            "when settled against an adjusted close instead of `raw_close`.",
        "secured_cash": "(occ, qty) -> float. THE DENOMINATOR of every return a short book "
                        "quotes. `options_sizing` makes the PREMIUM the capital at risk, which "
                        "overstates a short's return by ~40x on r1's own book.",
        "early_assignment_flag": "(occ, as_of, q, ...) -> dict. Reports RATIONALITY; whether a "
                                 "holder acts is unobservable and no probability is estimated.",
    },
    "registered_by": "assignment.register() -> fleet.register_assignment_provider(PROVIDER)",
    "refusal_if_absent": "SHORT_BOOK_WITHOUT_ASSIGNMENT",
}

_PROVIDER = None


def register_assignment_provider(obj) -> dict:
    """Register `S3-I3`'s model. Until r1 lands one, every short book is REFUSED.

    The check is on the INTERFACE, not on an import, so this file never depends on a module
    that does not exist yet and a half-built provider is refused rather than half-used.
    """
    global _PROVIDER
    missing = [n for n in ASSIGNMENT_INTERFACE["callables"] if not callable(getattr(obj, n, None))]
    if missing:
        return {"ok": False, "registered": False, "missing": missing,
                "reason": "provider does not satisfy ASSIGNMENT_INTERFACE: missing "
                          + ", ".join(missing)}
    _PROVIDER = obj
    return {"ok": True, "registered": True, "missing": []}


def assignment_provider():
    return _PROVIDER


# NOTHING IS REGISTERED HERE, ON PURPOSE, AND THE COST IS STATED SO NOBODY "FIXES" IT.
#
# An earlier cut of this file did `_S3I3_REGISTRATION = register_assignment_provider(_SB)` at
# module scope, reasoning that a provider nobody remembers to register refuses the six short
# books forever. That reasoning is real and it loses to r1's: an import-time registration means
# ANY code path that imports the assignment model -- a script reading one number, a test, a
# notebook -- silently unblocks every short book in the fleet. **Refusing by default is the
# safe direction; auto-registering is not.**
#
# THE CONSEQUENCE, NAMED RATHER THAN DISCOVERED LATER: until something calls
# `assignment.register()`, `may_fill` returns `SHORT_BOOK_WITHOUT_ASSIGNMENT` for F-4, F-6,
# F-8, F-10, F-17 and F-18. That is correct -- a short book with no assignment model must not
# fill -- and it is the runner's job to make the call, not this module's.


# ---------------------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------------------
def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def fleet_dir(root: str = None) -> str:
    return os.path.join(root or repo_root(), "data", "fleet")


def records_path(book: str, root: str = None) -> str:
    return os.path.join(fleet_dir(root), book + ".csv")


def declaration_path(book: str, root: str = None) -> str:
    return os.path.join(root or repo_root(), "DECL_" + book + ".md")


# ---------------------------------------------------------------------------------------
# Declarations
# ---------------------------------------------------------------------------------------
_BLOCK = re.compile(r"```json\s*\n(.*?)\n```", re.S)


def parse_declaration(text: str) -> dict:
    """The single fenced ```json block. More than one is REFUSED, not merged.

    Two blocks are two declarations, and picking one is choosing which rules the book is held
    to after the fact.
    """
    blocks = _BLOCK.findall(text or "")
    if not blocks:
        return {"ok": False, "reason": "no fenced ```json declaration block"}
    if len(blocks) > 1:
        return {"ok": False, "reason": "%d fenced json blocks; a declaration is exactly one, "
                                       "and choosing between two is choosing the rules after "
                                       "the fact" % len(blocks)}
    try:
        d = json.loads(blocks[0])
    except Exception as e:                                    # noqa: BLE001
        return {"ok": False, "reason": "declaration block is not valid JSON: " + str(e)}
    if not isinstance(d, dict):
        return {"ok": False, "reason": "declaration block is not an object"}
    return {"ok": True, "declaration": d, "reason": ""}


def validate_declaration(decl: dict, *, book: str = None) -> dict:
    """Every refusal the harness owns, collected. `ok` only if the list is empty.

    Refusals are COLLECTED rather than raised one at a time, so an author fixes a declaration
    in one pass instead of discovering its faults serially.
    """
    r, short_detail = [], ""
    if not isinstance(decl, dict):
        return {"ok": False, "refusals": ["DECLARATION_NOT_AN_OBJECT"], "detail": {}}

    # PRESENCE, NOT TRUTHINESS. The first cut tested `in (None, "", [], {})` and refused every
    # book declaring NO extra record columns, because an empty list is a legitimate answer to
    # `records_schema` and a falsy one. A validator that cannot tell "unanswered" from
    # "answered with nothing" refuses correct declarations, so the emptiness rules are stated
    # per field below instead of inferred from a truth value.
    for f in REQUIRED_DECL_FIELDS:
        if f not in decl or decl.get(f) is None or decl.get(f) == "":
            r.append("MISSING_FIELD:" + f)
    for f in ("entry_rule", "universe", "sizing"):
        if not str(decl.get(f) or "").strip():
            r.append("EMPTY_FIELD:" + f)
    if not isinstance(decl.get("structure"), dict) or not decl.get("structure"):
        r.append("EMPTY_FIELD:structure")
    if not isinstance(decl.get("records_schema"), list):
        r.append("RECORDS_SCHEMA_NOT_A_LIST")
    if not isinstance(decl.get("verdict_grammar"), list) or not decl.get("verdict_grammar"):
        r.append("EMPTY_FIELD:verdict_grammar")
    try:
        if int(decl.get("concurrency_cap")) < 1:
            r.append("CONCURRENCY_CAP_BELOW_ONE")
    except (TypeError, ValueError):
        r.append("BAD_CONCURRENCY_CAP")

    if book and decl.get("book") != book:
        r.append("BOOK_ID_DOES_NOT_MATCH_FILENAME")
    if decl.get("domain") not in DOMAINS:
        r.append("BAD_DOMAIN")
    if decl.get("hypothesis_class") not in HYPOTHESIS_CLASSES:
        r.append("BAD_HYPOTHESIS_CLASS")
    if decl.get("side") not in SIDES:
        r.append("BAD_SIDE")

    # O11 verbatim, not paraphrased: a book that softens it has changed what it claims.
    if decl.get("o11_sentence") != O11_SENTENCE:
        r.append("O11_SENTENCE_NOT_VERBATIM")

    st = decl.get("structure") or {}
    sel = st.get("strike_selection") if isinstance(st, dict) else None
    if sel not in STRIKE_SELECTION:
        r.append("BAD_STRIKE_SELECTION")
    elif sel == "delta" and not (st.get("v6opt_argument") or "").strip():
        # The draft's own clause: a delta-targeted strike must argue past V6-OPT's autopsy,
        # which measured a delta-targeted rule NEUTRALISING the very risk difference the trade
        # was built to exploit. Silence is not an argument.
        r.append("DELTA_STRIKE_WITHOUT_V6OPT_ARGUMENT")

    h = decl.get("verdict_horizon") or {}
    if not isinstance(h, dict):
        r.append("BAD_VERDICT_HORIZON")
    else:
        for f in REQUIRED_HORIZON_FIELDS:
            if h.get(f) in (None, ""):
                r.append("MISSING_HORIZON_FIELD:" + f)
        for f in ("sigma", "rho", "alpha", "min_effect"):
            try:
                if float(h.get(f)) <= 0:
                    r.append("NON_POSITIVE_HORIZON_FIELD:" + f)
            except (TypeError, ValueError):
                pass
        try:
            if int(h.get("fills_needed")) < 1:
                r.append("FILLS_NEEDED_BELOW_ONE")
        except (TypeError, ValueError):
            pass

    t = decl.get("trial") or {}
    if not isinstance(t, dict) or t.get("charged_at") != "first_verdict_read":
        r.append("TRIAL_NOT_CHARGED_AT_FIRST_VERDICT_READ")
    if isinstance(t, dict) and t.get("domain") not in DOMAINS + ("none",):
        r.append("BAD_TRIAL_DOMAIN")
    # A utility book claims no edge, so it charges nothing -- the draft's F-6 framing.
    if decl.get("hypothesis_class") == "utility" and isinstance(t, dict) \
            and t.get("domain") != "none":
        r.append("UTILITY_BOOK_CHARGES_A_TRIAL")

    # ---- the short leg DELEGATES to the landed S3-I3 rather than re-deciding it -------------
    #
    # `sells_premium` IS MANDATORY ON EVERY BOOK, and that is r1's rule adopted whole: an
    # absent field would let a short book pass by OMISSION, which is exactly the refusal Don's
    # ruling asks for. It is also a SECOND source of truth alongside this file's `side`, so the
    # two are required to AGREE -- a declaration reading `side: long` with `sells_premium: true`
    # is refused as self-contradictory rather than silently resolved in either direction.
    sp = decl.get("sells_premium")
    if not isinstance(sp, bool):
        r.append("MISSING_FIELD:sells_premium")
    elif (decl.get("side") == "short") != sp:
        r.append("SIDE_AND_SELLS_PREMIUM_DISAGREE")

    if sp is True or decl.get("side") == "short":
        # DELEGATED TO THE MODEL, LAZILY AND OPTIONALLY -- never imported at module scope.
        # r1's `assignment.py` states the dependency direction explicitly: *"fleet does not
        # import this module (its check is duck-typed on purpose), so the dependency runs one
        # way only"*, and registration is *"an explicit CALL and never an import side effect,
        # so importing this module to read one number cannot silently unblock every short book
        # in the fleet."* Both are right and this harness yields to them.
        # PRESENCE IS THIS HARNESS'S OWN GATE and is checked here rather than delegated.
        #
        # THE DEFECT THIS CLOSES WAS CAUGHT BY THE DAY-1 SELF-CHECK, and it is the exact shape
        # this project keeps recording: making the delegation OPTIONAL silently switched the
        # short-field rules OFF, because r1's `_AssignmentProvider` exposes the three interface
        # callables and NOT `validate_declaration`. A short book missing `margin_method`
        # validated CLEANLY. A guard that quietly stops running is worse than one that was
        # never written, and the split of duties is now explicit: **this harness checks that a
        # short book STATES its clauses; the model checks that the stated VALUES cohere.**
        for f in REQUIRED_SHORT_FIELDS:
            if not str(decl.get(f) or "").strip():
                r.append("MISSING_FIELD:" + f)

        # REPORTED, NOT WORKED AROUND: with r1's current provider the VALUE rules -- `naked`
        # refused, `spot_basis` as-traded, `return_denominator` secured cash -- are NOT enforced
        # at declaration time, because the adapter does not carry the validator. Adding
        # `validate_declaration` to `_AssignmentProvider` restores them through this seam with
        # no change here. Re-implementing them in this file would be a second short-book
        # contract (B7) and is deliberately not done.
        v = getattr(_PROVIDER, "validate_declaration", None)
        if callable(v):
            try:
                v(decl)
            except Exception as e:                            # noqa: BLE001
                # The model RAISES, because "a refusal that returns a flag is a refusal
                # somebody forgets to read". This harness COLLECTS refusals so an author fixes
                # a declaration in one pass, so the raise is converted -- and its message is
                # carried verbatim into `detail`, never discarded.
                r.append("SHORT_BOOK_REFUSED_BY_S3I3")
                short_detail = str(e)
        if _PROVIDER is None:
            r.append("SHORT_BOOK_WITHOUT_ASSIGNMENT")

    extra = decl.get("records_schema")
    if isinstance(extra, list):
        clash = [c for c in extra if c in RECORD_COLUMNS]
        if clash:
            r.append("RECORDS_SCHEMA_CLASHES_WITH_BASE:" + ",".join(sorted(clash)))

    detail = {}
    if "SHORT_BOOK_WITHOUT_ASSIGNMENT" in r:
        detail["assignment_interface"] = ASSIGNMENT_INTERFACE
    if short_detail:
        detail["s3i3_refusal"] = short_detail
    return {"ok": not r, "refusals": sorted(set(r)), "detail": detail}


def declaration_sha(text: str) -> str:
    """The declaration's content hash -- the chain's anchor and the randomizer's salt."""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------------------
# DECLARATION BEFORE FILL, enforced against git (register section E8)
# ---------------------------------------------------------------------------------------
def _git(args, root=None):
    try:
        p = subprocess.run(["git", "-C", root or repo_root()] + args,
                           capture_output=True, text=True)
    except Exception as e:                                    # noqa: BLE001
        return None, str(e)
    if p.returncode != 0:
        return None, (p.stderr or "").strip()
    return p.stdout, ""


def declaration_commit(book: str, root: str = None) -> dict:
    """The commit that introduced `DECL_<book>.md`, and whether it satisfies the convention.

    THREE CONDITIONS, ALL REQUIRED: the commit EXISTS, it is an ANCESTOR of HEAD (so it has
    landed rather than merely existing on some branch), and it touched EXACTLY ONE file --
    that declaration. "Committed ALONE" is what makes the commit tamper-evidence at all: a
    declaration landed alongside code cannot be shown to predate the code.

    THE HONEST LIMIT, stated here rather than left to be assumed: this proves the declaration
    landed before the fill was RECORDED, on this harness's clock. It CANNOT prove no order was
    placed at a broker beforehand. The record stream is the evidence; the broker is not.
    """
    rel = "DECL_" + book + ".md"
    # `--all`, NOT the default walk from HEAD, and the reason is a defect mutation found in
    # this very function. Searching only HEAD's history means a declaration committed on an
    # unmerged branch is never SEEN, so the ancestor check below could never fire -- it was
    # unreachable code, and the refusal a reader got was the misleading "not committed" when
    # the truth is "committed, but not landed here". Searching all refs makes the ancestor
    # condition both reachable and the one that reports honestly.
    out, err = _git(["log", "--all", "--diff-filter=A", "--format=%H", "--", rel], root)
    if out is None:
        return {"ok": False, "code": "GIT_UNAVAILABLE", "reason": err or "git not available"}
    shas = [s for s in (out or "").split() if s]
    if not shas:
        return {"ok": False, "code": "DECLARATION_NOT_COMMITTED",
                "reason": rel + " has no commit that adds it; the commit IS the tamper-"
                                "evidence, so an uncommitted declaration is not one"}
    sha = shas[0]

    anc, _ = _git(["merge-base", "--is-ancestor", sha, "HEAD"], root)
    if anc is None:
        return {"ok": False, "code": "DECLARATION_NOT_ANCESTOR", "commit": sha,
                "reason": sha[:9] + " is not an ancestor of HEAD; it has not landed here"}

    files, err = _git(["show", "--name-only", "--format=", sha], root)
    if files is None:
        return {"ok": False, "code": "GIT_UNAVAILABLE", "reason": err}
    touched = sorted(f.strip().replace("\\", "/") for f in files.splitlines() if f.strip())
    if touched != [rel]:
        return {"ok": False, "code": "DECLARATION_NOT_COMMITTED_ALONE", "commit": sha,
                "touched": touched,
                "reason": sha[:9] + " touched " + str(len(touched)) + " files ("
                          + ", ".join(touched[:6]) + "); a declaration lands ALONE or its "
                          "commit proves nothing about what predated what"}
    return {"ok": True, "code": "", "commit": sha, "touched": touched, "reason": ""}


# ---------------------------------------------------------------------------------------
# The deterministic A/B randomizer (draft section 4)
# ---------------------------------------------------------------------------------------
def arm(book: str, date: str, symbol: str, decl_sha: str) -> str:
    """`"A"` (marketable) or `"B"` (mid-limit, worked) -- reproducible and unriggable.

    Derived from (book, date, symbol) SALTED WITH THE DECLARATION HASH, so the assignment is
    fixed the moment the declaration lands and cannot be re-rolled by re-submitting: the same
    order always lands in the same arm, and changing the arm requires changing a committed
    file. Nothing about the quote or the outcome enters, which is what stops the split being
    chosen on what it would produce.
    """
    key = "|".join([decl_sha or "", book or "", date or "", (symbol or "").upper()])
    return "A" if hashlib.sha256(key.encode("utf-8")).digest()[0] % 2 == 0 else "B"


# ---------------------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------------------
def _cell(v) -> str:
    """The cell exactly as the CSV writer will persist it."""
    return "" if v is None else str(v)


def _canonical(payload: dict) -> str:
    """THE HASH IS OVER WHAT IS PERSISTED, NOT OVER WHAT WAS PASSED IN.

    The first cut hashed the payload with its native types -- `2.5`, `1`, `True` -- and every
    value comes back from CSV as a STRING, so `verify_chain` could not reproduce a single row
    and the whole chain read as broken on its own first run. Canonicalising to the written
    cell makes the invariant checkable: hash what you store.
    """
    return json.dumps({k: _cell(v) for k, v in payload.items()},
                      sort_keys=True, separators=(",", ":"))


def row_hash(prev_hash: str, payload: dict) -> str:
    return hashlib.sha256(((prev_hash or "") + _canonical(payload)).encode("utf-8")).hexdigest()


def read_records(book: str, root: str = None) -> dict:
    rows, header, err = AO.read_rows(records_path(book, root))
    if err:
        return {"ok": False, "reason": err, "rows": [], "columns": []}
    return {"ok": True, "reason": "", "rows": rows, "columns": header}


def verify_chain(book: str, root: str = None, decl_sha: str = None) -> dict:
    """Recompute the chain. Reports the FIRST break and its index; see `CHAIN_BOUND`."""
    rd = read_records(book, root)
    if not rd["ok"]:
        return {"ok": False, "reason": rd["reason"], "n": 0, "bound": CHAIN_BOUND}
    rows = rd["rows"]
    if not rows:
        # An empty stream is reported VACUOUS, never PASSING: a chain that verified nothing
        # and a chain that verified everything must not read the same (`O21-D2`'s C5).
        return {"ok": True, "vacuous": True, "n": 0, "reason": "no records",
                "bound": CHAIN_BOUND}
    prev = decl_sha or (rows[0].get("decl_sha") or "")
    last_seq = ""
    # The payload keys come from the FILE'S OWN HEADER, not from `RECORD_COLUMNS`, so a book
    # declaring extra columns still verifies -- and so does a stream written before a column
    # was added. Reading the constant instead would make the chain unverifiable for exactly
    # the books that use `records_schema`.
    keys = [c for c in (rd["columns"] or RECORD_COLUMNS) if c not in ("prev_hash", "row_hash")]
    for i, r in enumerate(rows):
        payload = {k: r.get(k) for k in keys}
        want = row_hash(prev, payload)
        if (r.get("prev_hash") or "") != prev:
            return {"ok": False, "vacuous": False, "n": len(rows), "broken_at": i,
                    "reason": "prev_hash mismatch at row %d" % i, "bound": CHAIN_BOUND}
        if (r.get("row_hash") or "") != want:
            return {"ok": False, "vacuous": False, "n": len(rows), "broken_at": i,
                    "reason": "row_hash mismatch at row %d" % i, "bound": CHAIN_BOUND}
        if (r.get("seq") or "") <= last_seq:
            return {"ok": False, "vacuous": False, "n": len(rows), "broken_at": i,
                    "reason": "sequence not strictly increasing at row %d" % i,
                    "bound": CHAIN_BOUND}
        last_seq = r.get("seq") or ""
        prev = r.get("row_hash") or ""
    return {"ok": True, "vacuous": False, "n": len(rows), "head": prev, "reason": "",
            "bound": CHAIN_BOUND}


def _next_seq(rows) -> str:
    n = 0
    for r in rows:
        try:
            n = max(n, int((r.get("seq") or "0").strip()))
        except ValueError:
            pass
    return str(n + 1).zfill(SEQ_WIDTH)


def record(book: str, kind: str, fields: dict, *, decl_sha: str, root: str = None,
           columns=None, ts: str = None) -> dict:
    """Append one event. THE ONLY WRITE DOOR. Append-only, chained, atomic.

    Every kind goes through here -- a fill, a refusal, a meter read, a self-check, a close --
    because a refusal recorded by a different route is a refusal that can be lost, and the
    draft's section 4 requires the refusal to be a RECORD rather than a crash.
    """
    if kind not in EVENT_KINDS:
        return {"ok": False, "wrote": False, "reason": "unknown event kind: " + str(kind)}
    cols = list(RECORD_COLUMNS) + [c for c in (columns or []) if c not in RECORD_COLUMNS]
    rd = read_records(book, root)
    if not rd["ok"]:
        return {"ok": False, "wrote": False, "reason": rd["reason"]}
    rows = rd["rows"]
    prev = (rows[-1].get("row_hash") if rows else None) or decl_sha

    payload = {k: "" for k in cols}
    payload.update({k: v for k, v in (fields or {}).items() if k in cols})
    payload["seq"] = _next_seq(rows)
    payload["ts"] = ts or _dt.datetime.now().isoformat(timespec="seconds")
    payload["kind"] = kind
    payload["book"] = book
    payload["decl_sha"] = decl_sha
    hashed = {k: payload.get(k) for k in cols if k not in ("prev_hash", "row_hash")}
    payload["prev_hash"] = prev
    payload["row_hash"] = row_hash(prev, hashed)

    return AO.append(payload, records_path(book, root), key="seq", columns=cols,
                     append_only=True,
                     backfill_hint=" A fleet record stream is append-only by construction; a "
                                   "correction is a NEW dated row, never an edit "
                                   "(PT-AMEND1's shape).")


# ---------------------------------------------------------------------------------------
# The day-1 self-verification gate (register section E6, Don's ruling)
# ---------------------------------------------------------------------------------------
def harness_fingerprint() -> str:
    """Hash of the harness's own sources, so a self-check goes STALE when the harness moves."""
    h = hashlib.sha256()
    for p in (os.path.abspath(__file__),
              os.path.join(os.path.dirname(os.path.abspath(__file__)), "append_only.py")):
        try:
            # `with`, not a bare open: this runs on every gate check, so on a long-lived
            # service the leaked handles accumulate. Surfaced as a ResourceWarning by the
            # endpoint test, which is the first caller to hit it in a loop.
            with open(p, "rb") as fh:
                h.update(fh.read())
        except OSError:
            h.update(b"<missing>")
    return h.hexdigest()


def selfcheck_state(book: str, root: str = None) -> dict:
    """Is the last recorded self-check present, current and passing?

    ABSENT, STALE and FAILING are three states and are reported as three, because "no check
    has run" and "a check ran and failed" are different facts and only one of them is a bug.
    """
    rd = read_records(book, root)
    if not rd["ok"]:
        return {"ok": False, "state": "UNREADABLE", "reason": rd["reason"]}
    checks = [r for r in rd["rows"] if (r.get("kind") or "") == "selfcheck"]
    if not checks:
        return {"ok": False, "state": "ABSENT",
                "reason": "no self-check on record; under Don's ruling no book fills until "
                          "the harness passes its own first-day verification"}
    last = checks[-1]
    if (last.get("detail") or "") != harness_fingerprint():
        return {"ok": False, "state": "STALE", "reason": "the harness changed since the last "
                                                         "self-check; re-run it"}
    if (last.get("fate") or "") != "pass":
        return {"ok": False, "state": "FAILING", "reason": "the last self-check did not pass"}
    return {"ok": True, "state": "PASS", "reason": ""}


# ---------------------------------------------------------------------------------------
# The one entry point a book's runner calls
# ---------------------------------------------------------------------------------------
MANIFEST_REL = os.path.join("data_export", "fleet_declarations.json")


def declaration_manifest(root: str = None) -> dict:
    """The shipped manifest, or an ABSENT marker. Never raises.

    Built by `scripts/fleet_export_declarations.py` where git exists, consumed where it does
    not. See that module for why shipping the markdown alone would have fixed nothing.
    """
    path = os.path.join(root or repo_root(), MANIFEST_REL)
    try:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
    except OSError:
        return {"ok": False, "absent": True, "books": {},
                "reason": "no declaration manifest at " + path}
    except ValueError as e:
        return {"ok": False, "absent": False, "books": {},
                "reason": "declaration manifest is not valid JSON: %s" % e}
    if payload.get("schema") != "fleet_declarations/1":
        return {"ok": False, "absent": False, "books": {},
                "reason": "manifest schema is %r" % payload.get("schema")}
    return {"ok": True, "absent": False, "books": payload.get("books") or {},
            "head": payload.get("head", ""), "reason": ""}


def may_fill(book: str, root: str = None) -> dict:
    """Every precondition on recording a fill, checked together. Refusals are RECORDS.

    Order is deliberate: the declaration is checked before the self-check, because a book with
    no valid declaration has nowhere to record a refusal about its self-check.

    **TWO EVIDENCE GRADES, AND THE RESULT ALWAYS SAYS WHICH.** Where the `DECL_*.md` and `.git`
    are both present -- any worktree -- the declaration is read from disk and its commit facts
    are RE-DERIVED from git every time, and the manifest is not consulted at all. In the
    deployed image neither exists (`.dockerignore` excludes `*.md` AND `.git`), so the gate
    falls back to the shipped manifest and reports `evidence: "manifest"`.

    **THAT FALLBACK IS A REAL WEAKENING AND IS NEVER SILENT.** A manifest-graded gate trusts a
    file that was built from a commit and shipped in an image; a git-graded one re-derives the
    proof. Both are recorded, so no fill can later be read as carrying git-grade evidence when
    it does not -- which is the whole reason the field exists rather than a boolean "ok".
    """
    path = declaration_path(book, root)
    text = None
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        pass

    if text is None:
        man = declaration_manifest(root)
        entry = (man.get("books") or {}).get(str(book))
        if not entry:
            return {"ok": False, "code": "DECLARATION_MISSING",
                    "reason": (path + " not found and no manifest entry for " + str(book)
                               + "; " + man.get("reason", ""))}
        v = validate_declaration(entry.get("declaration") or {}, book=book)
        if not v["ok"]:
            return {"ok": False, "code": "DECLARATION_INVALID",
                    "reason": ",".join(v["refusals"]), "refusals": v["refusals"],
                    "evidence": "manifest", "detail": v.get("detail", {})}
        sha = entry.get("decl_sha") or ""
        s = selfcheck_state(book, root)
        if not s["ok"]:
            return {"ok": False, "code": "SELFCHECK_" + s["state"], "reason": s["reason"],
                    "decl_sha": sha, "evidence": "manifest"}
        ch = verify_chain(book, root, decl_sha=sha)
        if not ch["ok"]:
            return {"ok": False, "code": "CHAIN_BROKEN", "reason": ch["reason"],
                    "decl_sha": sha, "evidence": "manifest"}
        return {"ok": True, "code": "", "reason": "", "decl_sha": sha,
                "declaration": entry.get("declaration") or {},
                "commit": entry.get("commit", ""), "evidence": "manifest",
                "sandbox_caveat": SANDBOX_CAVEAT}

    p = parse_declaration(text)
    if not p["ok"]:
        return {"ok": False, "code": "DECLARATION_UNPARSEABLE", "reason": p["reason"]}
    v = validate_declaration(p["declaration"], book=book)
    if not v["ok"]:
        return {"ok": False, "code": "DECLARATION_INVALID", "reason": ",".join(v["refusals"]),
                "refusals": v["refusals"], "detail": v.get("detail", {})}

    c = declaration_commit(book, root)
    if not c["ok"]:
        return {"ok": False, "code": c["code"], "reason": c["reason"]}

    sha = declaration_sha(text)
    s = selfcheck_state(book, root)
    if not s["ok"]:
        return {"ok": False, "code": "SELFCHECK_" + s["state"], "reason": s["reason"],
                "decl_sha": sha}

    ch = verify_chain(book, root, decl_sha=sha)
    if not ch["ok"]:
        return {"ok": False, "code": "CHAIN_BROKEN", "reason": ch["reason"], "decl_sha": sha}

    return {"ok": True, "code": "", "reason": "", "decl_sha": sha,
            "declaration": p["declaration"], "commit": c["commit"],
            "evidence": "git", "sandbox_caveat": SANDBOX_CAVEAT}


def refuse(book: str, code: str, reason: str, *, decl_sha: str, root: str = None) -> dict:
    """A refusal is a record, not a crash (draft section 4)."""
    return record(book, "refusal", {"refusal_code": code, "detail": reason},
                  decl_sha=decl_sha, root=root)


# ---------------------------------------------------------------------------------------
# The per-book anytime-valid meter (PT-METER pattern) -- and reading it IS a verdict read
# ---------------------------------------------------------------------------------------
def book_meter(values, *, sigma: float, rho: float, alpha: float,
               min_effect: float, fills_needed: int) -> dict:
    """Robbins normal-mixture boundary on the running sum, per book, on the book's own frozen
    parameters.

    `track_meter.boundary` IS the implementation -- imported, never re-derived. Its own
    docstring says the arguments exist for calibration and "NOT so a caller can retune the
    live meter", and that is honoured: a fleet book's sigma/rho/alpha are frozen in its
    DECLARATION, before any fill, and this function has no defaults to fall back on.

    A `NO CONCLUSION` state is NOT evidence of absence (register void condition 9), so the
    minimum effect and the horizon travel with every reading rather than being available on
    request.
    """
    xs = [float(v) for v in (values or [])]
    n = len(xs)
    out = {"n": n, "fills_needed": int(fills_needed), "min_effect": float(min_effect),
           "params": {"sigma": float(sigma), "rho": float(rho), "alpha": float(alpha)},
           "horizon_reached": n >= int(fills_needed),
           "not_evidence_of_absence": ("A NO CONCLUSION state means this design could not "
                                       "separate an effect of %g at this n. It is not "
                                       "evidence of absence." % float(min_effect))}
    if n < 1:
        out.update({"computable": False, "state": "NO DATA"})
        return out
    s = sum(xs)
    b = TM.boundary(n, sigma=sigma, rho=rho, alpha=alpha)
    out.update({
        "computable": True,
        "sum": s, "mean": s / n,
        "boundary_sum": b,
        "ci_lower": (s - b) / n, "ci_upper": (s + b) / n,
        "crossed": "up" if s >= b else ("down" if s <= -b else None),
        "state": "SUPPORTED" if s >= b else ("UNSUPPORTED" if s <= -b else "NO CONCLUSION"),
    })
    # The bound assumes sigma. If realised volatility exceeds it the band is too narrow, and
    # sigma may only ever be RAISED, with the change logged -- never lowered to fit.
    if n >= 2:
        mu = s / n
        sd = (sum((x - mu) ** 2 for x in xs) / (n - 1)) ** 0.5
        out["realised_sd"] = sd
        out["sigma_breach"] = sd > float(sigma)
    else:
        out["realised_sd"] = None
        out["sigma_breach"] = False
    return out


def read_meter(book: str, values, *, decl_sha: str, root: str = None, why: str = "") -> dict:
    """Read a book's meter AND RECORD THE READ. There is no unrecorded door.

    Register section E4: the draft's own section 2 makes a peek the verdict read that books
    the trial, and that rule is an honour system unless the peek is a dated fact. So this is
    the only reader, and it writes before it returns.
    """
    path = declaration_path(book, root)
    try:
        with open(path, encoding="utf-8") as fh:
            decl = parse_declaration(fh.read()).get("declaration") or {}
    except OSError:
        return {"ok": False, "reason": path + " not found"}
    h = decl.get("verdict_horizon") or {}
    try:
        m = book_meter(values, sigma=float(h["sigma"]), rho=float(h["rho"]),
                       alpha=float(h["alpha"]), min_effect=float(h["min_effect"]),
                       fills_needed=int(h["fills_needed"]))
    except (KeyError, TypeError, ValueError) as e:
        return {"ok": False, "reason": "declaration's verdict_horizon is incomplete: " + str(e)}

    prior = [r for r in read_records(book, root)["rows"] if (r.get("kind") or "") == "meter_read"]
    m["is_first_verdict_read"] = not prior
    m["prior_reads"] = len(prior)
    m["trial_charge"] = ("CHARGE ONE TRIAL NOW, to " + str((decl.get("trial") or {}).get("domain"))
                         if not prior and (decl.get("trial") or {}).get("domain") != "none"
                         else "already charged" if prior else "utility book, charges nothing")
    m["early"] = not m["horizon_reached"]
    w = record(book, "meter_read",
               {"fate": m["state"], "detail": (why or "")[:200],
                "refusal_code": "EARLY_READ" if m["early"] else ""},
               decl_sha=decl_sha, root=root)
    m["recorded"] = bool(w.get("wrote"))
    m["record_reason"] = w.get("reason", "")
    m["ok"] = True
    return m


# ---------------------------------------------------------------------------------------
# THE TRADIER SEAM -- V5-grade fill recording, consuming the sandbox's own shapes
# ---------------------------------------------------------------------------------------
# The fate vocabulary. A fate is read from the BROKER'S STATE, never inferred from whether a
# number happens to be present -- which is how a pending order came to be recorded as filled.
FATES = ("filled", "partial", "working", "rejected", "canceled", "expired", "unknown")


def _fate(order: dict, fill) -> str:
    """What actually happened to the order, in the broker's own terms."""
    o = order or {}
    st = str(o.get("status") or "").strip().lower()
    if st in ("rejected", "canceled", "cancelled", "expired"):
        return "canceled" if st == "cancelled" else st
    try:
        execd = float(o.get("exec_quantity") or 0)
        want = float(o.get("quantity") or 0)
    except (TypeError, ValueError):
        execd = want = 0.0
    if fill is not None and execd > 0:
        return "filled" if (want and execd >= want) else "partial"
    if st in ("pending", "open", "partially_filled"):
        return "working"
    if not st:
        return "unknown"
    return "working"


def quote_mid(quote: dict):
    """THE one definition of this book's mid. `None` when the quote is one-sided.

    `B7`. `fill_fields` records the mid and `submit` PRICES arm B's limit at it, and the two
    must be the same number by construction -- a book whose subject is half-spread capture
    cannot afford a limit priced by one convention and a record written by another. The
    convention is `PaperBroker.mark_from_quote`'s: the mid when there are two sides, and
    EMPTY when there are not, never a fallback to `last`. A stale `last` under the name
    `quote_mid` is the wrong-object family.
    """
    q = quote or {}

    def _n(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return None
        return v if v == v else None

    bid, ask = _n(q.get("bid")), _n(q.get("ask"))
    if bid is None or ask is None or ask <= 0 or ask < bid:
        return None
    return round((bid + ask) / 2.0, 4)


def fill_fields(*, symbol: str, occ: str, side: str, qty: int, order_type: str,
                quote: dict, order: dict = None, submitted_ts: str, filled_ts: str = None,
                limit_price=None, arm: str = "", fallback: str = "",
                venue: str = "", structure_id: str = "", leg_index=None,
                net_cost=None) -> dict:
    """One V5-grade fill record from a Tradier quote and order. Records, never decides.

    **THE BID, ASK AND MID AT SUBMISSION ARE STORED, and that is the whole point.**
    `scripts/slippage_report.py` states its own binding gap -- *"`paper_option_orders` stores
    no bid, ask or mid at submit time ... The ASK is recoverable ... the MID is not recoverable
    by any route ... The fix is two columns written in `_place_entry` ... this is ROUTED"* --
    and nobody took it. A half-spread needs a mid, so V5's headline measure could only ever
    cover the exit leg. Every fleet book records as if it were the fills experiment, because
    `F-1` reads every book's fills.

    `mid` is taken from `PaperBroker.mark_from_quote`'s convention -- the MID when there are
    two sides -- and is left EMPTY when there are not, rather than falling back to `last`. A
    stale `last` recorded under the name `quote_mid` is the wrong-object family, and a missing
    mid is a fact about the quote that `F-1` needs to see.

    NO DERIVED OUTCOME STATISTIC IS STORED. Half-spread capture is computed at READ time, per
    the `F-1` draft's own rule, so the record stream carries observations and not conclusions.
    """
    q = quote or {}

    def _f(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return None
        return v if v == v else None

    bid, ask = _f(q.get("bid")), _f(q.get("ask"))
    mid = quote_mid(q)
    # THE FILL PRICE COMES FROM THE BROKER'S OWN HELPER, NEVER RE-DERIVED HERE.
    #
    # THE DEFECT THIS REPLACES FABRICATED A FILL, and the live leg caught it on its first real
    # order. The first cut read `avg_fill_price or price`; Tradier reports an unfilled limit
    # order as `status: pending, avg_fill_price: 0.0, exec_quantity: 0.0, price: <the limit>`,
    # and `0.0` is FALSY -- so the fallback took the LIMIT and this function reported a
    # PENDING order as FILLED at its own limit price. On `F-1`, the book whose entire subject
    # is fill quality and which reads every other book's fills, that is the worst silent
    # corruption available: every unfilled order becomes a perfect fill at the price asked for.
    #
    # `PaperBroker.fill_price` already gates on `exec_quantity`, so this delegates (B7).
    fill = None
    if order:
        from .paper_broker import PaperBroker as _PB
        fill = _PB.fill_price(order)
    ttf = ""
    if submitted_ts and filled_ts:
        try:
            a = _dt.datetime.fromisoformat(str(submitted_ts))
            b = _dt.datetime.fromisoformat(str(filled_ts))
            ttf = int((b - a).total_seconds())
        except ValueError:
            ttf = ""
    return {
        "symbol": symbol, "occ": occ, "side": side, "qty": qty, "arm": arm,
        "order_type": order_type,
        "quote_bid": "" if bid is None else bid,
        "quote_ask": "" if ask is None else ask,
        "quote_mid": "" if mid is None else mid,
        "limit_price": "" if limit_price is None else limit_price,
        "fill_price": "" if fill is None else fill,
        "submitted_ts": submitted_ts or "", "filled_ts": filled_ts or "",
        "time_to_fill_s": ttf,
        "fate": _fate(order, fill),
        "fallback": fallback, "venue": venue,
        # A single-leg fill leaves these EMPTY rather than defaulting to a fake structure of
        # one: "not part of a structure" and "leg 0 of a structure" are different facts.
        "structure_id": structure_id,
        "leg_index": "" if leg_index is None else int(leg_index),
        "net_cost": "" if net_cost is None else net_cost,
        "detail": SANDBOX_CAVEAT,
    }


# ---------------------------------------------------------------------------------------
# F-1's ARM POLICY -- the harness's single order door
# ---------------------------------------------------------------------------------------
WORK_SECONDS = 60          # F-1 frozen: arm B is "worked 60 seconds". Not a tuning knob.

_TERMINAL = ("filled", "rejected", "canceled", "cancelled", "expired", "error")


def _status(order: dict) -> str:
    return str((order or {}).get("status") or "").strip().lower()


def submit(book: str, *, broker, occ: str, underlying: str, side: str, qty: int,
           decl_sha: str, symbol: str = None, date: str = None, quote: dict = None,
           work_seconds: int = WORK_SECONDS, clock=None, sleep=None, now=None) -> dict:
    """Submit ONE order under `F-1`'s frozen arm policy. Returns `fill_fields` kwargs.

    **THIS IS `F-1`'s ENTRY RULE, AND IT DELIBERATELY DOES NOT LIVE IN `F-1`.** That book's
    declaration says *"No entries of its own. **Every order any fleet book submits** is
    assigned by the harness's deterministic randomizer"* -- so the policy belongs to the
    harness's submission path, and a per-book callable could not reach the orders of books
    that are not it. Every fleet book routes its orders through here; that is what makes the
    A/B a property of the fleet rather than an opt-in.

    Arm A is marketable. Arm B is a limit at the mid, worked `WORK_SECONDS`, then
    cancel-and-market with the fallback FLAGGED so it is never pooled with a clean B fill --
    the draft's own rule, and the reason the record carries `fallback` as a first-class
    column rather than a derived one.

    **THE CANCEL IS CHECKED BEFORE THE MARKET LEG IS SENT.** If the cancel fails the limit is
    still live, and sending a market order beside it opens a DOUBLE POSITION on the one book
    whose subject is fill quality. That case returns the working order flagged
    `B-cancel-failed` and sends nothing further: an unfilled order is an observation, and a
    doubled one is a corrupted measurement.
    """
    from .paper_broker import PaperBroker as _PB
    clock = clock or _time.monotonic
    sleep = sleep or _time.sleep
    now = now or (lambda: _dt.datetime.now().isoformat(timespec="seconds"))
    symbol = symbol or underlying
    date = date or _dt.date.today().isoformat()

    a = arm(book, date, symbol, decl_sha)
    if quote is None:
        quote = (broker.quotes([occ]) or {}).get(occ) or {}

    def _kw(order, order_type, fallback, limit_price=None, filled_ts=None, submitted_ts=None):
        return {"symbol": symbol, "occ": occ, "side": side, "qty": qty,
                "order_type": order_type, "quote": quote, "order": order or {},
                "submitted_ts": submitted_ts, "filled_ts": filled_ts,
                "limit_price": limit_price, "arm": a, "fallback": fallback, "venue": ""}

    def _market(fallback):
        ts = now()
        res = broker.place_option(occ, underlying, side, qty)
        oid = _PB.order_id(res)
        order = broker.order(oid) if oid else {}
        fts = now() if _PB.fill_price(order) is not None else None
        return _kw(order, "market", fallback, submitted_ts=ts, filled_ts=fts)

    if a == "A":
        return _market("")

    mid = quote_mid(quote)
    if mid is None:
        # AMENDMENT 1 to DECL_f1_fill_ab.md, 2026-08-24. Arm B is "limit at mid" and a
        # one-sided quote HAS no mid, so the frozen rule has nothing to price. Recorded as
        # its OWN fallback value rather than pooled with either arm, because "B could not be
        # attempted" and "B was attempted and did not fill" are different observations and
        # only the second is evidence about working a limit.
        return _market("B-nomid")

    ts = now()
    res = broker.place_option(occ, underlying, side, qty, price=mid)
    oid = _PB.order_id(res)
    if not oid:
        return _kw(res.get("order") or {}, "limit", "B-unplaced", limit_price=mid,
                   submitted_ts=ts)

    deadline = clock() + float(work_seconds)
    order = broker.order(oid) or {}
    while _PB.fill_price(order) is None and _status(order) not in _TERMINAL:
        if clock() >= deadline:
            break
        sleep(1)
        order = broker.order(oid) or {}

    if _PB.fill_price(order) is not None:
        return _kw(order, "limit", "", limit_price=mid, submitted_ts=ts, filled_ts=now())

    cancelled = broker.cancel(oid) or {}
    if not cancelled.get("ok"):
        return _kw(order, "limit", "B-cancel-failed", limit_price=mid, submitted_ts=ts)

    out = _market("B-fallback")
    out["limit_price"] = mid
    return out


# ---------------------------------------------------------------------------------------
# (C) MULTI-LEG STRUCTURES -- one order, one net-cost constraint, never a naked leg
# ---------------------------------------------------------------------------------------
NET_DEBIT_ONLY = "debit_only"
NET_ANY = "any"
NET_RULES = (NET_DEBIT_ONLY, NET_ANY)


def net_cost(legs) -> Optional[float]:
    """Net cost of a structure at MARKETABLE prices. `None` if any leg is not two-sided.

    Buys are priced at the ASK and sells at the BID -- `options_fill.DEFAULT_AGGRESSION = 1.0`,
    the punishing convention every validated options number in this repo is net of. A mid-based
    net would make a collar look financeable at prices nobody can trade, which is precisely the
    error `F-1` exists to measure and must not be baked into the structure that F-1 measures.

    POSITIVE is a debit (you pay), NEGATIVE is a credit (you are paid).
    """
    total = 0.0
    for leg in legs or ():
        q = leg.get("quote") or {}

        def _n(x):
            try:
                v = float(x)
            except (TypeError, ValueError):
                return None
            return v if v == v else None

        bid, ask = _n(q.get("bid")), _n(q.get("ask"))
        if bid is None or ask is None or ask <= 0 or ask < bid:
            return None
        qty = int(leg.get("qty") or 0)
        if str(leg.get("side", "")).startswith("buy"):
            total += ask * qty
        else:
            total -= bid * qty
    return round(total, 4)


def check_structure(legs, *, net_rule: str) -> dict:
    """Every refusal a multi-leg structure can earn, checked BEFORE anything is placed.

    **THE NAKED-SHORT REFUSAL IS THE ONE THAT MATTERS.** `S3-I3` refuses a naked short BY NAME
    -- FINRA 4210's maintenance formula has its own floor and a cash-secured stand-in would
    UNDERSTATE the requirement, which is the unsafe direction. A structure whose only option
    leg is a short is that trade, whatever the declaration calls it.
    """
    legs = list(legs or ())
    r = []
    if len(legs) < 2:
        r.append("MULTILEG_SINGLE_LEG")
    if str(net_rule) not in NET_RULES:
        r.append("MULTILEG_UNKNOWN_NET_RULE:" + str(net_rule))
    shorts = [l for l in legs if str(l.get("side", "")).startswith("sell")]
    longs = [l for l in legs if str(l.get("side", "")).startswith("buy")]
    if shorts and not longs:
        r.append("MULTILEG_NAKED_SHORT")
    nc = net_cost(legs)
    if nc is None:
        r.append("MULTILEG_UNUSABLE_QUOTE")
    elif net_rule == NET_DEBIT_ONLY and nc < 0:
        r.append("MULTILEG_NET_CREDIT")
    return {"ok": not r, "refusals": r, "net_cost": nc,
            "n_legs": len(legs), "n_short": len(shorts), "n_long": len(longs)}


def submit_multileg(book: str, *, broker, underlying: str, legs, decl_sha: str,
                    net_rule: str = NET_DEBIT_ONLY, symbol: str = None, date: str = None,
                    now=None) -> dict:
    """Submit ONE multi-leg order, or refuse the whole structure. Never a partial structure.

    Returns `{"ok", "refusals", "net_cost", "structure_id", "candidates"}`, where
    `candidates` is one `fill_fields` kwargs dict PER LEG, sharing a `structure_id`, the arm
    and the net cost. One record per leg keeps the V5-grade per-leg quote block that `F-1`
    reads off every book's fills; the shared id is what makes the structure recoverable.

    **THE ARM IS ASSIGNED ONCE FOR THE STRUCTURE, not per leg.** F-1's unit is an ORDER and
    this is one order; arming legs independently would put one collar in both arms and make
    its half-spread capture uninterpretable.

    **A REFUSAL IS A RECORD, NOT A CRASH**, and no order is placed on any refusal -- the check
    runs first and returns before the broker is touched, which is what stops a naked leg
    existing for the duration of an exception.
    """
    now = now or (lambda: _dt.datetime.now().isoformat(timespec="seconds"))
    symbol = symbol or underlying
    date = date or _dt.date.today().isoformat()

    chk = check_structure(legs, net_rule=net_rule)
    if not chk["ok"]:
        return {"ok": False, "refusals": chk["refusals"], "net_cost": chk["net_cost"],
                "structure_id": "", "candidates": []}

    a = arm(book, date, symbol, decl_sha)
    sid = hashlib.sha256(
        "|".join([decl_sha or "", book or "", date or "", symbol or "",
                  ",".join(str(l.get("occ")) for l in legs)]).encode("utf-8")
    ).hexdigest()[:12]

    ts = now()
    otype = "even" if abs(chk["net_cost"]) < 0.005 else "debit"
    res = broker.place_multileg(underlying, legs, order_type=otype, price=chk["net_cost"])
    from .paper_broker import PaperBroker as _PB
    oid = _PB.order_id(res)
    order = broker.order(oid) if oid else {}
    fts = now() if _PB.fill_price(order) is not None else None

    cands = []
    for i, leg in enumerate(legs):
        cands.append({
            "symbol": symbol, "occ": leg["occ"], "side": leg["side"],
            "qty": int(leg["qty"]), "order_type": otype, "quote": leg.get("quote") or {},
            "order": order or {}, "submitted_ts": ts, "filled_ts": fts,
            "limit_price": chk["net_cost"], "arm": a, "fallback": "", "venue": "",
            "structure_id": sid, "leg_index": i, "net_cost": chk["net_cost"],
        })
    return {"ok": True, "refusals": [], "net_cost": chk["net_cost"],
            "structure_id": sid, "candidates": cands}


# ---------------------------------------------------------------------------------------
# (C) FIRST-CLASS SKIPS -- an observation a book declared, not the absence of one
# ---------------------------------------------------------------------------------------
def skip_fields(*, symbol: str, skip_reason: str, occ: str = "", quote: dict = None,
                detail: str = "") -> dict:
    """One SKIP observation. `F-14` declares *"the skips ARE the control population"*.

    Before this existed a rule could record only fills, so a book whose control arm is its
    skipped candidates could not represent the half that makes it interpretable -- it would
    have published a treatment arm with no control and no way to say so.

    THE QUOTE IS RECORDED WHERE THERE IS ONE, deliberately: `F-2`'s gate wants *"the
    would-have-been quote pair"* on a refused entry, and a skip with no quote block cannot
    answer what the trade would have cost. `skip_reason` is REQUIRED and has no default,
    because an unexplained skip is indistinguishable from a rule that silently did nothing.
    """
    if not str(skip_reason or "").strip():
        raise ValueError("a skip must carry a reason; an unexplained skip is not an "
                         "observation, it is a gap")
    q = quote or {}
    mid = quote_mid(q)

    def _c(x):
        return "" if x is None else x

    return {"symbol": symbol, "occ": occ, "side": "", "qty": 0, "arm": "",
            "order_type": "", "quote_bid": _c(q.get("bid")), "quote_ask": _c(q.get("ask")),
            "quote_mid": _c(mid), "limit_price": "", "fill_price": "",
            "submitted_ts": "", "filled_ts": "", "time_to_fill_s": "",
            "fate": "", "fallback": "", "venue": "",
            "skip_reason": str(skip_reason), "detail": detail or SANDBOX_CAVEAT}


def record_skip(book: str, fields: dict, root: str = None) -> dict:
    """Record one skip AFTER re-checking every precondition -- the same gate a fill passes.

    A skip places no order, so it is tempting to let it through a looser door. It must not:
    a skip is a ROW on an append-only, hash-chained stream that a verdict will be read from,
    so the declaration, the self-check and the chain all have to hold exactly as they do for a
    fill. The gate is about the RECORD, not about the order.
    """
    gate = may_fill(book, root)
    if not gate["ok"]:
        sha = gate.get("decl_sha") or ""
        if sha:
            refuse(book, gate["code"], gate["reason"], decl_sha=sha, root=root)
        return {"ok": False, "wrote": False, "code": gate["code"], "reason": gate["reason"],
                "refusal_recorded": bool(sha)}
    out = record(book, "skip", fields, decl_sha=gate["decl_sha"], root=root)
    out["code"] = ""
    return out


def record_fill(book: str, fields: dict, root: str = None) -> dict:
    """Record one fill AFTER re-checking every precondition. The gate is not optional.

    `may_fill` runs here rather than in a caller, so no book runner can reach the record
    stream without the declaration, the self-check and the chain all passing -- and a refusal
    becomes a REFUSAL RECORD on the book's own stream rather than an exception a scheduler
    swallows.
    """
    gate = may_fill(book, root)
    if not gate["ok"]:
        sha = gate.get("decl_sha") or ""
        if sha:
            refuse(book, gate["code"], gate["reason"], decl_sha=sha, root=root)
        return {"ok": False, "wrote": False, "code": gate["code"], "reason": gate["reason"],
                "refusal_recorded": bool(sha)}
    out = record(book, "fill", fields, decl_sha=gate["decl_sha"], root=root)
    out["code"] = ""
    return out


# ---------------------------------------------------------------------------------------
# One ledger row per book (draft section 1.5) -- emitted, so nobody hand-types a pipe
# ---------------------------------------------------------------------------------------
def _first_sentence(s) -> str:
    """The first sentence of `s`, split on a period FOLLOWED BY A SPACE.

    Splitting on a bare period truncates `"0.3 years at the projected 45.00 fills/month"` to
    `"0"` -- which reads as a horizon of zero, i.e. *"readable now"*, the exact misreading the
    horizon field exists to prevent. Caught by reading the emitted row rather than by any test,
    which is why the row is printed and inspected before it is pasted anywhere.
    """
    s = str(s or "").strip()
    for i in range(len(s) - 1):
        if s[i] == "." and s[i + 1] == " ":
            return s[:i]
    return s


def horizon_note(decl: dict) -> str:
    """The verdict horizon, FIELD BY FIELD, as one pipe-free ledger sentence.

    Every field is named with its own value rather than summarised, because the horizon's
    whole job is to stop a book being read early and a summary is exactly what gets rounded.
    `sigma_provenance` travels with `sigma` for the reason `MB8` paid for: it borrowed a
    standard error measured on a different perturbation size and was wrong by six-fold. An
    ASSUMED sigma and a MEASURED one are different objects and the row says which.
    """
    h = decl.get("verdict_horizon") or {}
    t = decl.get("trial") or {}
    dom = str(t.get("domain") or "")
    charge = ("ZERO TRIALS - hypothesis_class %r charges nothing and no meter is ever read"
              % str(decl.get("hypothesis_class") or "")
              if dom in ("", "none") else
              "Trial 1 %s, charged at %s" % (dom, t.get("charged_at") or "first_verdict_read"))
    sig = h.get("sigma")
    prov = str(h.get("sigma_provenance") or "")
    measured = prov.strip().upper().startswith("MEASURED")
    return (
        "Fleet book under S3-I1, declared and committed ALONE before any fill. %s. "
        "VERDICT HORIZON, field by field: min_effect %s; sigma %s (%s); rho %s; alpha %s; "
        "fills_needed %s, DERIVED as the smallest n at which the anytime-valid boundary falls "
        "to min_effect and NOT the drafts' round 30; expected_fills_per_month %s; "
        "years_to_horizon_at_projected_rate %s; earliest_honest_read %s. "
        "sigma may only ever be RAISED, never lowered. %s"
        % (charge, h.get("min_effect"), sig,
           "MEASURED" if measured else "PRIOR, not measured - replace with the realised SD at "
           "first read",
           h.get("rho"), h.get("alpha"), h.get("fills_needed"),
           h.get("expected_fills_per_month"), h.get("years_to_horizon_at_projected_rate"),
           _first_sentence(h.get("earliest_honest_read")), O11_SENTENCE))


def ledger_row(decl: dict, *, status: str = "DECLARED - no verdict", note: str = "",
               tag: str = None, commit: str = "PENDING", handoff: str = None,
               date: str = None) -> str:
    """The book's `VALQUO_LEDGER.md` row, ten cells, REFUSING any raw pipe in the prose.

    `M1-PARSE` is this record's most repeated clerical defect and it has NO ESCAPE:
    `research_log._parse` and the ledger builder both split on a bare pipe and honour no
    backslash, so one in a cell shifts every column after it and the row silently changes
    meaning. `E-2` hit it three days ago by writing an absolute value in prose. Emitting the
    row and REFUSING the character is cheaper than catching it after the fact.

    `tag` and `commit` were ADDED AT THE CEREMONY (2026-08-24) and the defect they close is
    this function's own. It was written while no book had been accepted, so it hard-coded the
    id as `"F-" + book` -- which yields `F-f13_second_event` where the map says **F-13** -- and
    the commit as the literal `PENDING`, which was true when nothing was committed and became
    false the moment seventeen declarations landed. Both defaults are UNCHANGED so every
    existing caller and test is bit-identical; the ceremony passes the real values.
    """
    book = str(decl.get("book") or "")
    cells = [
        tag or ("F-" + book), "F", str(decl.get("entry_rule") or "")[:180], status,
        "No verdict at declaration; amended at first verdict read",
        commit or "PENDING", handoff or ("DECL_" + book + ".md"),
        date or _dt.date.today().isoformat(), "human",
        (note or horizon_note(decl)),
    ]
    bad = [i for i, c in enumerate(cells) if "|" in c]
    if bad:
        raise ValueError("M1-PARSE: a raw pipe in cell(s) %s would shift every column after "
                         "it, and no escape exists. Reword the prose." % bad)
    return "| " + " | ".join(cells) + " |"


def declaration_template(book: str, *, domain: str = "options", side: str = "long") -> str:
    """A skeleton `DECL_<book>.md`. Every field present, every value obviously a placeholder.

    THE FORMAT IS A FENCED `json` BLOCK AND PROSE IS REFUSED, ON PURPOSE: prose cannot be
    validated, and the register's subject is a convention enforced MECHANICALLY rather than
    promised. The scout's four `DECL_DRAFT_*` files are prose and are refused as they stand --
    which is the machinery working, not a defect in them. This exists so the ~18-book wave
    Don's ruling calls for is cheap rather than eighteen hand-built JSON blocks.
    """
    d = {
        "book": book, "domain": domain, "hypothesis_class": "edge",
        "entry_rule": "TODO computable from data available at entry time, code-level pseudocode",
        "structure": {"strike_selection": "moneyness", "moneyness": 0.90, "dte": [30, 45]},
        "universe": "TODO", "sizing": "TODO", "concurrency_cap": 10, "side": side,
        # Mandatory on EVERY book, long or short -- an absent field would let a short book pass
        # by omission, which is the refusal Don's ruling #1 asks for (S3-I3's rule).
        "sells_premium": side == "short",
        "records_schema": [],
        "verdict_horizon": {
            "expected_fills_per_month": 0, "min_effect": 0.0, "sigma": 0.0, "rho": 3.0,
            "alpha": 0.05, "fills_needed": 0, "earliest_honest_read": "TODO YYYY-MM-DD"},
        "verdict_grammar": ["TODO", "NO CONCLUSION", "horizon-not-reached"],
        "trial": {"domain": domain, "charged_at": "first_verdict_read"},
        "o11_sentence": O11_SENTENCE,
    }
    if side == "short":
        # r1's five fields, not my three. `spot_basis` and `return_denominator` are pinned
        # rather than left TODO because S3-I3 accepts exactly one value for each and a
        # placeholder there would only ever be refused.
        d["assignment_model"] = "TODO at expiry per moneyness"
        d["margin_method"] = "cash_secured_put"
        d["spot_basis"] = "as_traded"
        d["early_assignment_flag"] = "TODO O21's q-machinery"
        d["return_denominator"] = "secured_cash"
    return ("# DECL " + book + "\n\n**Committed ALONE, before this book's first fill.**\n\n"
            "```json\n" + json.dumps(d, indent=2) + "\n```\n")


# ---------------------------------------------------------------------------------------
# THE DAILY CYCLE -- what a scheduler kicks, and what it honestly does today
# ---------------------------------------------------------------------------------------
_ENTRY_RULES: dict = {}


def register_entry_rule(book: str, fn, *, places_orders: bool = True) -> dict:
    """Register the CALLABLE that decides whether `book` enters today.

    A declaration FREEZES an entry rule in prose; it does not execute one. Nothing in this
    repository turns `"names whose flag count transitions from 0-or-1 to >=2"` into an order,
    and pretending otherwise is how a paper fleet reports a cycle that placed nothing as a
    cycle that found nothing. **The two are different facts and `cycle()` keeps them apart.**

    `fn(decl, root) -> list[dict]` returns zero or more candidate fills, each a kwargs dict
    for `fill_fields`. Returning `[]` means *the rule ran and today qualifies nobody*, which
    is a real observation. Not being registered at all means *the rule has never been built*,
    which is not.
    """
    if not callable(fn):
        raise TypeError("an entry rule must be callable")
    _ENTRY_RULES[str(book)] = {"fn": fn, "places_orders": bool(places_orders)}
    return {"ok": True, "book": str(book), "places_orders": bool(places_orders)}


def entry_rule(book: str):
    e = _ENTRY_RULES.get(str(book))
    return e["fn"] if e else None


def places_orders(book: str) -> bool:
    """False for a RIDER -- a book whose own declaration says it never sends an order.

    **THREE OF THE SEVENTEEN DECLARED BOOKS CAN NEVER PRODUCE A FILL OF THEIR OWN**, by their
    own frozen prose: `F-1` (*"No entries of its own"*), `F-2` (*"A GATE, holds no
    positions"*) and `F-19` (*"A LABELING GATE, refuses nothing"*). Their records accrue only
    when a HOST book fills.

    This is declared at REGISTRATION rather than sniffed out of the declaration's prose,
    because detecting it by substring is the family this record has been bitten by repeatedly
    -- a guard keyed on wording fires against correct text and misses a rephrasing.

    It exists so `cycle()` cannot report the fleet as breathing on the strength of a book that
    is not able to trade. A rider returning `[]` is not *"the market qualified nobody"*; it is
    a book doing exactly what it declared, and pooling the two would be the same blur
    `ARMED_NO_ENTRY_RULE` was created to prevent, one level up.
    """
    e = _ENTRY_RULES.get(str(book))
    return True if e is None else bool(e["places_orders"])


def declared_books(root: str = None) -> list:
    """Every book with a `DECL_<book>.md` carrying a machine-checkable block, in name order.

    Discovery is by parse rather than by a hand-kept list, so a book cannot be declared and
    then silently left out of the cycle -- `MA5`'s lesson, where one hand-typed copy of a
    fact drifted from another. Files that do not parse are RETURNED with their reason rather
    than skipped: `CEREMONY_RUNBOOK.md` is not a book and neither is a prose draft, and
    the difference between *"not a book"* and *"a book whose declaration is broken"* is
    exactly what a silent skip would destroy.
    """
    d = root or repo_root()
    out = []
    try:
        names = sorted(os.listdir(d))
    except OSError:
        names = []
    if not any(n.startswith("DECL_") and n.endswith(".md") for n in names):
        # NO MARKDOWN HERE. In the deployed image that is the ORDINARY case rather than a
        # fault: `.dockerignore` excludes `*.md`, so `DECL_*.md` never ships and a
        # directory-only discovery finds zero books -- which is exactly what production
        # returned on the first real dispatch (`books_declared: 0` beside a non-empty
        # `entry_rules_registered`). Fall back to the shipped manifest.
        man = declaration_manifest(root)
        return [{"book": b, "parses": True, "reason": "", "source": "manifest"}
                for b in sorted(man.get("books") or {})]
    for fn in names:
        if not (fn.startswith("DECL_") and fn.endswith(".md")):
            continue
        book = fn[len("DECL_"):-len(".md")]
        try:
            with open(os.path.join(d, fn), encoding="utf-8") as fh:
                text = fh.read()
        except OSError as e:
            out.append({"book": book, "parses": False, "reason": str(e)})
            continue
        p = parse_declaration(text)
        out.append({"book": book, "parses": bool(p["ok"]),
                    "reason": "" if p["ok"] else p["reason"]})
    return out


def _not_breathing_reason(books_only, implemented, blocked, ran) -> str:
    """The DOMINANT measured cause, in a short code. `""` when the fleet IS breathing.

    Ordered most-fundamental first, because a fleet with no books also has no implemented
    rules and no blocked books, and reporting the downstream symptom would send a reader to
    the wrong fix -- which is precisely what happened on the first production dispatch.
    """
    if ran:
        return ""
    if not books_only:
        return "NO_BOOKS_VISIBLE"
    if implemented == 0:
        return "NO_ENTRY_RULE_IMPLEMENTED"
    if blocked == len(books_only):
        codes = sorted({r.get("state", "") for r in books_only if not r.get("may_fill")})
        return "ALL_BOOKS_BLOCKED_AT_GATE:" + ",".join(c for c in codes if c)[:80]
    return "NO_ARMED_BOOK_RAN"


def cycle(root: str = None, *, write: bool = False, books: list = None) -> dict:
    """One fleet cycle. Reports every book's gate state, and fills only where a rule exists.

    **THIS FUNCTION RECORDS NOTHING WHEN THERE IS NOTHING TO RECORD, ON PURPOSE.** The obvious
    alternative -- write a row per book per day saying "could not fill" -- would put roughly
    4,250 rows a year of pure noise into streams whose whole value is that every row is an
    event. The gap is reported in the response and, once a day, in the Action's log; it does
    not need to be in the chain to be visible.

    `write=False` (the default) is a DRY RUN that computes the identical report and records
    nothing, so a scheduler, a health check and a human all read the same object and only the
    POST can move the record -- the `track-row` split, for the same reason: a side-effecting
    GET on an append-only record is reachable by a retry, a prefetch or a pasted link.
    """
    root = root or repo_root()
    today = _dt.date.today().isoformat()
    rows, armed, filled, blocked = [], 0, 0, 0
    for d in declared_books(root):
        if books is not None and d["book"] not in books:
            continue
        if not d["parses"]:
            # Not a book. Reported, never counted, never silently dropped.
            rows.append({"book": d["book"], "is_book": False, "state": "NOT_A_DECLARATION",
                         "reason": d["reason"]})
            continue
        book = d["book"]
        gate = may_fill(book, root)
        rec = read_records(book, root)
        item = {"book": book, "is_book": True, "may_fill": bool(gate["ok"]),
                "state": gate.get("code") or "ARMED", "reason": gate.get("reason", ""),
                "records": len(rec.get("rows") or []),
                "entry_rule_implemented": entry_rule(book) is not None}
        if not gate["ok"]:
            blocked += 1
            rows.append(item)
            continue
        armed += 1
        fn = entry_rule(book)
        if fn is None:
            # THE HONEST DISTINCTION. The gate permits a fill and no code exists to decide
            # one, which is a BUILD gap and not a market observation. It is never reported as
            # "no candidates today".
            item["state"] = "ARMED_NO_ENTRY_RULE"
            rows.append(item)
            continue
        try:
            cands = list(fn(gate["declaration"], root) or [])
        except Exception as e:                                   # noqa: BLE001
            item["state"] = "ENTRY_RULE_RAISED"
            item["reason"] = str(e)
            rows.append(item)
            continue
        item["candidates"] = len(cands)
        item["places_orders"] = places_orders(book)
        item["state"] = "RAN" if item["places_orders"] else "RAN_RIDER"
        # A candidate may declare its KIND. `fill` is the legacy shape and stays the default
        # so every rule written before skips existed is untouched; `skip` is F-14's control
        # population. An UNRECOGNISED kind is REFUSED onto the book's own stream rather than
        # dropped -- a candidate the cycle cannot classify is a defect in a rule, and a silent
        # drop is how it would survive.
        item["skipped"] = 0
        if write:
            wrote = []
            for c in cands:
                c = dict(c)
                kind = str(c.pop("kind", "fill"))
                if kind == "fill":
                    wrote.append(record_fill(book, fill_fields(**c), root))
                    filled += 1
                elif kind == "skip":
                    wrote.append(record_skip(book, skip_fields(**c), root))
                    item["skipped"] += 1
                else:
                    refuse(book, "UNKNOWN_CANDIDATE_KIND",
                           "entry rule returned kind=%r; expected fill or skip" % kind,
                           decl_sha=gate["decl_sha"], root=root)
            item["wrote"] = len(wrote)
        rows.append(item)

    books_only = [r for r in rows if r.get("is_book")]
    unscheduled = [r["book"] for r in books_only if r["state"] == "ARMED_NO_ENTRY_RULE"]
    # COUNTED, not derived. The first cut computed this as `declared - unscheduled - blocked`,
    # which is right only while no book is both blocked AND unimplemented -- true today by
    # accident and false the moment one book's self-check lands. A number that is
    # coincidentally correct is the `MB8` family: an arithmetic that was never checked against
    # the thing it claims to count.
    implemented = sum(1 for r in books_only if r["entry_rule_implemented"])
    riders = [r["book"] for r in books_only if r["state"] == "RAN_RIDER"]
    # `RAN_RIDER` is excluded ON PURPOSE. A gate that ran is not a fleet that traded.
    ran = any(r["state"] == "RAN" for r in books_only)
    return {
        "ok": True, "date": today, "wrote": bool(write),
        "books_declared": len(books_only), "armed": armed, "blocked": blocked,
        "fills_written": filled,
        "entry_rules_implemented": implemented,
        "books_with_no_entry_rule": unscheduled,
        "riders_ran": riders,
        "breathing": bool(filled) or ran,
        # THE CAUSE IS MEASURED, NEVER GUESSED -- and this exists because a GUESSED one shipped
        # and was wrong in production. `fleet-cycle.yml`'s annotation prints "no entry rule
        # implemented" whenever `breathing` is not true, having tested only `breathing`. On the
        # first real dispatch the true cause was `books_declared: 0` (no `DECL_*.md` in the
        # image) while the rules WERE registered, so the annotation blamed the one thing that
        # was not wrong. A short machine-readable code now travels in the body so a log reader
        # -- and a future one-line workflow fix -- can print the cause that was actually found.
        "not_breathing_reason": _not_breathing_reason(books_only, implemented, blocked, ran),
        "note": ("" if ran else
                 "DECLARED-BUT-NOT-BREATHING (%s): %d books declared, %d entry rules "
                 "implemented, %d blocked at the gate."
                 % (_not_breathing_reason(books_only, implemented, blocked, ran),
                    len(books_only), implemented, blocked)),
        "sandbox_caveat": SANDBOX_CAVEAT,
        "books": rows,
    }


# ---------------------------------------------------------------------------------------
# Void condition 3: a cross-book aggregate is not a verdict, so it is not offered
# ---------------------------------------------------------------------------------------
def fleet_aggregate(*_a, **_k):
    """Deliberately unavailable. Register section 5, void condition 3.

    Each book has its own meter, its own frozen parameters and its own horizon; a fleet-level
    "portfolio" reading is its own future register, not a convenience on this one. Raising
    beats returning something a reader would quote.
    """
    raise NotImplementedError(
        "S3-I1 void condition 3: reading any cross-book aggregate as a verdict voids the "
        "register. Each book carries its own meter; a fleet-level portfolio reading needs its "
        "own register and its own trials.")
