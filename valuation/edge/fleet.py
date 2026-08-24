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
import json
import os
import re
import subprocess
from typing import Optional

from . import append_only as AO
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
)

EVENT_KINDS = ("selfcheck", "fill", "refusal", "meter_read", "close")

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
REQUIRED_SHORT_FIELDS = ("assignment", "margin", "secured_cash_is_denominator")

DOMAINS = ("equity", "options")
HYPOTHESIS_CLASSES = ("edge", "cost", "utility")
SIDES = ("long", "short")
STRIKE_SELECTION = ("moneyness", "fixed", "delta")

# ---------------------------------------------------------------------------------------
# THE S3-I3 SEAM. Defined here, BUILT BY r1. This module computes no assignment and no margin.
# ---------------------------------------------------------------------------------------
ASSIGNMENT_INTERFACE = {
    "module": "valuation.edge.assignment (S3-I3, r1's)",
    "callables": {
        "assign_at_expiry": "(occ, settle_price, side, qty) -> dict with keys "
                            "{assigned: bool, shares: int, cash: float, basis: str}",
        "early_assignment_flag": "(occ, as_of, q) -> dict with keys {flagged: bool, reason: str} "
                                 "-- q is the dividend yield, O21's machinery",
        "secured_cash": "(occ, strike, qty) -> float, the Reg-T cash-secured convention; this "
                        "IS the denominator of every return the book quotes",
    },
    "registered_by": "fleet.register_assignment_provider(obj)",
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
    r = []
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

    if decl.get("side") == "short":
        for f in REQUIRED_SHORT_FIELDS:
            if decl.get(f) in (None, "", [], {}):
                r.append("MISSING_SHORT_FIELD:" + f)
        if _PROVIDER is None:
            r.append("SHORT_BOOK_WITHOUT_ASSIGNMENT")

    extra = decl.get("records_schema")
    if isinstance(extra, list):
        clash = [c for c in extra if c in RECORD_COLUMNS]
        if clash:
            r.append("RECORDS_SCHEMA_CLASHES_WITH_BASE:" + ",".join(sorted(clash)))

    return {"ok": not r, "refusals": sorted(set(r)),
            "detail": {"assignment_interface": ASSIGNMENT_INTERFACE} if
            any(x == "SHORT_BOOK_WITHOUT_ASSIGNMENT" for x in r) else {}}


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
            h.update(open(p, "rb").read())
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
def may_fill(book: str, root: str = None) -> dict:
    """Every precondition on recording a fill, checked together. Refusals are RECORDS.

    Order is deliberate: the declaration is checked before the self-check, because a book with
    no valid declaration has nowhere to record a refusal about its self-check.
    """
    path = declaration_path(book, root)
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return {"ok": False, "code": "DECLARATION_MISSING", "reason": path + " not found"}

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
            "sandbox_caveat": SANDBOX_CAVEAT}


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
def fill_fields(*, symbol: str, occ: str, side: str, qty: int, order_type: str,
                quote: dict, order: dict = None, submitted_ts: str, filled_ts: str = None,
                limit_price=None, arm: str = "", fallback: str = "",
                venue: str = "") -> dict:
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
    mid = round((bid + ask) / 2.0, 4) if (bid is not None and ask is not None
                                          and ask > 0 and ask >= bid) else None
    fill = None
    if order:
        fill = _f(order.get("avg_fill_price")) or _f(order.get("price"))
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
        "fate": "filled" if fill is not None else "unfilled",
        "fallback": fallback, "venue": venue,
        "detail": SANDBOX_CAVEAT,
    }


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
def ledger_row(decl: dict, *, status: str = "DECLARED - no verdict", note: str = "") -> str:
    """The book's `VALQUO_LEDGER.md` row, ten cells, REFUSING any raw pipe in the prose.

    `M1-PARSE` is this record's most repeated clerical defect and it has NO ESCAPE:
    `research_log._parse` and the ledger builder both split on a bare pipe and honour no
    backslash, so one in a cell shifts every column after it and the row silently changes
    meaning. `E-2` hit it three days ago by writing an absolute value in prose. Emitting the
    row and REFUSING the character is cheaper than catching it after the fact.
    """
    book = str(decl.get("book") or "")
    cells = [
        "F-" + book, "F", str(decl.get("entry_rule") or "")[:180], status,
        "No verdict at declaration; amended at first verdict read",
        "PENDING", "DECL_" + book + ".md", _dt.date.today().isoformat(), "human",
        (note or ("Fleet book under S3-I1. Trial: 1 " + str((decl.get("trial") or {}).get("domain"))
                  + ", charged at FIRST VERDICT READ. Horizon "
                  + str((decl.get("verdict_horizon") or {}).get("fills_needed"))
                  + " fills, earliest honest read "
                  + str((decl.get("verdict_horizon") or {}).get("earliest_honest_read"))
                  + ". " + O11_SENTENCE)),
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
        "records_schema": [],
        "verdict_horizon": {
            "expected_fills_per_month": 0, "min_effect": 0.0, "sigma": 0.0, "rho": 3.0,
            "alpha": 0.05, "fills_needed": 0, "earliest_honest_read": "TODO YYYY-MM-DD"},
        "verdict_grammar": ["TODO", "NO CONCLUSION", "horizon-not-reached"],
        "trial": {"domain": domain, "charged_at": "first_verdict_read"},
        "o11_sentence": O11_SENTENCE,
    }
    if side == "short":
        d["assignment"] = "TODO at expiry per moneyness; early flagged via O21's q-machinery"
        d["margin"] = "TODO Reg-T cash-secured"
        d["secured_cash_is_denominator"] = True
    return ("# DECL " + book + "\n\n**Committed ALONE, before this book's first fill.**\n\n"
            "```json\n" + json.dumps(d, indent=2) + "\n```\n")


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
