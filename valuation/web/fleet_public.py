"""THE DECLARED BOOKS, FOR A PUBLIC PAGE — provenance and state, never a track record.

**THE CENTRAL CLAIM IS THE ORDERING, AND IT IS THE ONLY CLAIM HERE.** Every one of these
books had its entry rule, structure, universe, sizing and verdict horizon written down and
committed to git — **alone, in its own commit** — before it recorded a single fill. That is
checkable by anyone with the repository: the sha and the date are on the page for exactly that
reason, and they are the point rather than decoration. What the books have *done* is not on the
page at all.

**WHAT THIS PAGE IS NOT, AND THE COPY IS BUILT AROUND IT.** These are PAPER books in a Tradier
sandbox. No capital is at risk, no verdict is due, and none of them has run long enough to
carry one. The bound track's framing is the model — *"too early to judge"*, *"reported, not
evidence"* — and the same `BANNED` tuple discipline applies: the forbidden wording is asserted
against the **RENDERED payload**, not against this source, because rendering is where copy
leaks (`V3`'s rule, and `hero.py`'s own lesson that a label a surface can decline to show is
not a safeguard).

**ZERO FILLS IS TWO DIFFERENT FACTS AND THIS PAGE NEVER CONFLATES THEM.** `fleet.cycle` already
refuses to: a book whose gate is open and whose rule ran and found nothing is a **market
observation**; a book with no implemented rule at all is a **build gap**, reported as
`ARMED_NO_ENTRY_RULE` and never as *"no candidates today"*. Collapsing the two is how a fleet
that has never placed an order reports a quiet week. The surface carries the distinction in the
state, in the blurb, and in the sentence under the table.

**IT RUNS NO ENTRY RULE AND TOUCHES NO NETWORK.** State is composed from the same primitives
`cycle()` uses — `may_fill` for the gate, `entry_rule` for whether code exists — so there is no
second definition of "blocked", and a page render cannot place an order, take a quote or cost a
runner budget. `cycle()` itself is deliberately NOT called: it executes rules.

**IT READS THE DATE FROM THE MANIFEST WHERE GIT IS ABSENT.** The deployed image excludes
`.git`, which is why `data_export/fleet_declarations.json` exists at all. The sha and date are
computed where git exists and read where it does not, and the payload says which source it
used, so a reader is never left inferring that a manifest fact is a git fact.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Optional

HEADING = "Books declared before they traded"

LEDE = ("Each of these is a paper book whose rule was written down and committed to git — on "
        "its own, in its own commit — before it recorded a single fill. The commit and its "
        "date are shown so that ordering can be checked rather than taken on trust.")

#: THE POSTURE, and it travels in the payload rather than living in a template. Every surface
#: that renders a figure from here renders this with it.
POSTURE = ("Paper books in a broker sandbox. No capital is at risk, none of these has run long "
           "enough to mean anything, and no verdict is due on any of them. This page reports "
           "what was committed and what has happened since — it is not a track record and "
           "nothing here is a recommendation.")

NOT_A_RECORD = ("Fills are recorded here the way a logbook records them, not the way a "
                "performance report does: what was bought or sold and when. How any of it "
                "turned out is a separate question with its own pre-committed horizon, and it "
                "is not answered on this page.")

#: The two ways a book can have written nothing, kept apart. `fleet.cycle`'s own rule.
QUIET_MEANS = ("A book with a working rule that wrote nothing this week is reporting the "
               "market: it looked and found nothing to do. A book with no rule implemented yet "
               "has not looked at all. Those are different facts and the state column says "
               "which one applies — a build gap is never reported as a quiet market.")

ARMED = "ARMED"
ARMED_NO_ENTRY_RULE = "ARMED_NO_ENTRY_RULE"
BLOCKED = "BLOCKED"
NOT_A_DECLARATION = "NOT_A_DECLARATION"

STATE_BLURB = {
    ARMED: "its gate is open and its rule is implemented; a quiet day is the market's answer",
    ARMED_NO_ENTRY_RULE: ("its gate is open and its rule is not implemented yet, so it has not "
                          "looked — this is a build gap, not a quiet market"),
    BLOCKED: "the harness refuses to record a fill for it, for the reason shown",
    NOT_A_DECLARATION: "the file is not a valid declaration and is listed rather than dropped",
}

#: Whole phrases, never bare tokens, and scoped to THIS block. `SC-4` measured what a
#: page-wide tuple costs: fifteen hits on neighbouring items' honest prose, and a guard that
#: cries wolf is switched off within the week.
#:
#: **EVERY ENTRY IS CLAIM-SHAPED, AND THAT IS A REPAIR RATHER THAN A PREFERENCE.** The first
#: cut banned the bare token `track record` — and fired on this module's own `POSTURE`, which
#: says *"it is NOT a track record"*. A denial and an assertion share the noun, so a substring
#: ban cannot tell them apart and the honest sentence is the one that loses. That is this
#: repository's most repeated test defect, recorded five separate times, and the fix each time
#: was the same: ban by ROLE, not by token.
#:
#: So `our track record` and `a track record of` are banned and `not a track record` is
#: sayable; `verified returns` is banned and `no returns are reported` is sayable. A guard the
#: page's own caveats cannot survive is a guard that gets deleted the first week it fires.
BANNED = (
    # forecast
    "will beat", "will outperform", "will continue", "expected to outperform",
    "should outperform", "on track to beat", "poised to",
    # proof
    "proves the", "proven strategy", "guaranteed", "risk-free", "market-beating",
    "audited returns", "verified returns", "independently verified",
    # track-record claims — CLAIM-SHAPED, so a denial survives
    "our track record", "a track record of", "track record of outperformance",
    "consistently beats", "has outperformed the",
    # recommendation
    "buy now", "you should buy", "we recommend", "our pick", "our picks",
    "returns you can expect",
)


#: Where a declaration can be read. Pinned at the introducing COMMIT rather than at a branch,
#: because the page's claim is about what was committed then — a link to `main` would show
#: today's bytes under a sha that promises yesterday's, which is the one thing this shelf
#: exists to make checkable.
#:
#: THE REPOSITORY IS PRIVATE, and the surface says so rather than serving a link that 404s for
#: most readers. The filename and the sha are the durable identifier either way: anyone with a
#: clone can `git show <sha>:DECL_<book>.md` and get the exact bytes, with or without this URL.
REPO_BLOB = "https://github.com/dcorbin07/valuation-tool/blob/%s/%s"

REPO_NOTE = ("Declarations link into the project's git history at the commit that introduced "
             "them. The repository is private, so the link needs access — the filename and the "
             "commit are the identifier that does not.")


def declaration_url(sha: str, filename: str) -> Optional[str]:
    """A permalink to one declaration, or None when there is no commit to pin it to."""
    if not sha or not filename:
        return None
    return REPO_BLOB % (sha, filename)


def violations(text: str) -> list:
    """Banned phrases present in one rendered fleet block.

    Asserted against the RENDERED payload rather than this source: rendering is where copy
    leaks, and a caveat a surface can decline to show is not a safeguard (`hero.py`'s lesson).
    """
    low = (text or "").lower()
    return [p for p in BANNED if p in low]


def own_copy() -> str:
    """Every sentence this module owns, for the guard's NEGATIVE control.

    A banned tuple with no negative control gets deleted the first week it fires on an honest
    caveat — which is exactly what the first cut of `BANNED` did to `POSTURE`.
    """
    return " ".join([HEADING, LEDE, POSTURE, NOT_A_RECORD, QUIET_MEANS]
                    + sorted(STATE_BLURB.values()))


def _fleet():
    try:
        from ..edge import fleet as F                                  # noqa: WPS433
        return F
    except Exception:                                                  # noqa: BLE001
        return None


def _manifest(root: str) -> dict:
    try:
        with open(os.path.join(root, "data_export", "fleet_declarations.json"),
                  encoding="utf-8") as f:
            d = json.load(f)
        return (d or {}).get("books") or {}
    except Exception:                                                  # noqa: BLE001
        return {}


def _iso(s) -> Optional[_dt.date]:
    try:
        return _dt.date.fromisoformat(str(s)[:10])
    except Exception:                                                  # noqa: BLE001
        return None


#: A short memo for the RENDER path, and it is OPT-IN rather than automatic.
#:
#: `may_fill` resolves the declaration's commit, which is four git subprocesses per book where
#: git exists — measured at 0.64s each, so eighteen books cost about 6.7s. That is not a page.
#: On the service it takes the manifest instead and is far cheaper, but a surface should not be
#: fast only in production.
#:
#: DEFAULT OFF, and that is the load-bearing part: every test calls `books()` plainly and gets
#: a fresh read, so no fixture can be answered from a stale memo. Only the route asks for the
#: memo, and the shelf changes at most once a cycle, so sixty seconds is generous.
_MEMO = {}
MEMO_TTL_SECONDS = 60


def reset_memo() -> None:
    """Drop the render memo. For tests, and for a caller that has just recorded a fill."""
    _MEMO.clear()


def books(root: str = None, today=None, *, cache: bool = False) -> dict:
    """Every declared book: what was committed, when, and where it has got to.

    Never raises. An unreadable harness renders an honest empty shelf rather than a stack
    trace on a public page.
    """
    import time as _time

    key = (str(root), str(today))
    if cache:
        hit = _MEMO.get(key)
        if hit and (_time.time() - hit[0]) < MEMO_TTL_SECONDS:
            return hit[1]

    out = _books(root, today)
    if cache:
        _MEMO[key] = (_time.time(), out)
    return out


def _books(root: str = None, today=None) -> dict:
    F = _fleet()
    out = {"available": False, "reason": "", "books": [], "n": 0, "drafts_excluded": 0,
           "heading": HEADING, "lede": LEDE, "posture": POSTURE,
           "not_a_record": NOT_A_RECORD, "quiet_means": QUIET_MEANS, "repo_note": REPO_NOTE,
           "n_fills_total": 0, "n_armed": 0, "n_no_rule": 0, "n_blocked": 0,
           "evidence": None}
    if F is None:
        out["reason"] = "the fleet harness is not importable here"
        return out

    root = root or F.repo_root()
    day = _iso(today) or _dt.date.today()
    man = _manifest(root)
    rows = []
    try:
        declared = F.declared_books(root)
    except Exception as e:                                             # noqa: BLE001
        out["reason"] = "the declared books could not be read (%s)" % type(e).__name__
        return out

    drafts = 0
    for d in declared:
        book = d.get("book")
        # A DRAFT IS NOT A BOOK, and the exclusion is MECHANICAL rather than editorial.
        # `DECL_DRAFT_*.md` files are documents whose own text says they are awaiting the
        # alone-commit that would make them declarations, so they yield a book id prefixed
        # `DRAFT_`. Listing them on a page whose entire claim is "committed before it traded"
        # would assert that claim about three files nobody has committed as declarations.
        #
        # `L7`'s rule is the one being obeyed, not broken: what may never be dropped is a
        # VERIFIED book somebody found uninteresting. Dropping a thing that is not a book by
        # a rule anyone can apply is the safe kind, and the count is reported so the exclusion
        # is visible rather than silent.
        if str(book).startswith("DRAFT_"):
            drafts += 1
            continue
        if not d.get("parses"):
            rows.append({"book": book, "title": book, "state": NOT_A_DECLARATION,
                         "state_blurb": STATE_BLURB[NOT_A_DECLARATION],
                         "reason": d.get("reason") or "", "commit": "", "commit_short": "",
                         "commit_date": None, "commit_day": None,
                         "days_accrued": None, "fills": 0, "records": 0,
                         "fills_needed": None, "horizon": None, "declaration": None,
                         "evidence": None})
            continue

        # ---- provenance: git where it exists, the manifest where it does not -------------
        # THE MANIFEST FIRST, GIT AS THE FALLBACK — and the order is not only a speed choice.
        #
        # `declaration_commit` runs four git subprocesses per book. Eighteen books cost
        # **18.3 seconds** on a page render, measured, which is not a page. The manifest holds
        # the same three facts (sha, date, committed-alone) in one JSON read, and it is the
        # ONLY source the deployed service has, since the image excludes `.git`.
        #
        # So preferring it makes a local render behave like production instead of quietly
        # exercising a path the service can never take — the `fleet_gates` lesson, where a rule
        # that reads what the image lacks passes in a worktree and fails on the service, in the
        # worst possible place to find out. Git remains the fallback for a book the manifest
        # has not been regenerated for, and the payload SAYS which source answered.
        m = man.get(book) or {}
        sha, when, evidence = "", None, None
        if m.get("commit"):
            sha, when, evidence = m["commit"], m.get("commit_date"), "manifest"
        else:
            try:
                c = F.declaration_commit(book, root)
                if c.get("ok"):
                    sha, when, evidence = c["commit"], c.get("commit_date"), "git"
            except Exception:                                          # noqa: BLE001
                pass

        # ---- what the declaration committed to ------------------------------------------
        decl = m.get("declaration") or {}
        if not decl:
            try:
                with open(F.declaration_path(book, root), encoding="utf-8") as f:
                    p = F.parse_declaration(f.read())
                decl = p.get("declaration") or {} if p.get("ok") else {}
            except Exception:                                          # noqa: BLE001
                decl = {}
        hz = decl.get("verdict_horizon") if isinstance(decl.get("verdict_horizon"), dict) else {}
        needed = hz.get("fills_needed")
        try:
            needed = int(needed) if needed is not None else None
        except (TypeError, ValueError):
            needed = None
        earliest = str(hz.get("earliest_honest_read") or "").strip()
        horizon = earliest if _iso(earliest) else None

        # ---- what has happened since ----------------------------------------------------
        fills = records = 0
        try:
            rec = F.read_records(book, root)
            if rec.get("ok"):
                rr = rec.get("rows") or []
                records = len(rr)
                fills = sum(1 for r in rr if (r.get("kind") or "") == "fill")
        except Exception:                                              # noqa: BLE001
            pass

        cd = _iso(when)
        days = (day - cd).days if cd else None

        # ---- state, composed from the SAME primitives `cycle` uses ----------------------
        state, reason = ARMED, ""
        try:
            gate = F.may_fill(book, root)
            if not gate.get("ok"):
                state = BLOCKED
                reason = gate.get("reason") or gate.get("code") or ""
            elif F.entry_rule(book) is None:
                state = ARMED_NO_ENTRY_RULE
        except Exception as e:                                         # noqa: BLE001
            state, reason = BLOCKED, "the gate could not be read (%s)" % type(e).__name__

        rows.append({
            "book": book,
            "title": (decl.get("entry_rule") or book).split(".")[0][:90] or book,
            "commit": sha, "commit_short": sha[:12], "commit_date": when,
            "commit_day": cd.isoformat() if cd else None,
            "evidence": evidence,
            "days_accrued": days,
            "fills": fills, "records": records,
            "fills_needed": needed, "horizon": horizon,
            "state": state, "state_blurb": STATE_BLURB[state], "reason": reason,
            "declaration": "DECL_%s.md" % book,
            "declaration_url": declaration_url(sha, "DECL_%s.md" % book),
        })

    rows.sort(key=lambda r: (r["state"] != ARMED, r["book"]))
    out.update(
        available=True, books=rows, n=len(rows), drafts_excluded=drafts,
        n_fills_total=sum(r["fills"] for r in rows),
        n_armed=sum(1 for r in rows if r["state"] == ARMED),
        n_no_rule=sum(1 for r in rows if r["state"] == ARMED_NO_ENTRY_RULE),
        n_blocked=sum(1 for r in rows if r["state"] == BLOCKED),
        evidence=("git" if any(r.get("evidence") == "git" for r in rows)
                  else ("manifest" if any(r.get("evidence") == "manifest" for r in rows)
                        else None)),
    )
    return out
