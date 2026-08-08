#!/usr/bin/env python3
"""
build_ledger.py — regenerate the mechanical columns of VALQUO_LEDGER.md.

WHY THIS EXISTS
---------------
The external audit is 134 items. Their status was scattered across 32
HANDOFF_*.md files, HANDOFF_STATUS.md, CLAUDE.md, VALQUO_ACTION_PLAN.md and
AGENTS.md, and the only way to answer "is S12 done?" was a git dig. Two
mechanical counts of the same corpus disagreed badly (38/134 vs 68/134),
because a line like "feeds U1 at Session 7" is a FORWARD REFERENCE, not U1
being finished, and no naive substring rule separates the two.

WHAT IT DOES
------------
Reads valquo_audit_items.json for id/series/title, scans the handoff corpus and
the git log for evidence, classifies every occurrence of an item id, and emits a
PROPOSAL. It never silently overwrites a human-verified row: every row whose
`src` is anything other than the literal `auto` is authoritative, and a
disagreement is REPORTED, not applied. Rows whose id is not an audit item at
all (OOB*, and the project's own pre-registered experiments) are carried
through verbatim, as is any prose above the table.

    python scripts/build_ledger.py                 # proposal + summary, no writes
    python scripts/build_ledger.py --summary       # counts only
    python scripts/build_ledger.py --evidence S12  # why an item is where it is
    python scripts/build_ledger.py --write         # refresh src=auto rows only

EVIDENCE MODEL (the whole point — read before changing)
-------------------------------------------------------
An occurrence of an id is classified as exactly one of:

  HEADER   the id is a standalone token in a markdown heading, i.e. the file
           devotes a SECTION to it. This is the only strong positive signal.
  COMMIT   the id appears in a git commit subject.
  FORWARD  the line matches a forward-reference cue ("feeds U1", "needed for
           S12", "blocked by O20", "next: B4"). A forward reference is evidence
           that the item EXISTS and is WANTED. It is not evidence it is done.
           Counting these is exactly what inflated the 68 number.
  PROSE    a bare mention. Weak. Never promotes on its own.

DONE requires HEADER-or-COMMIT evidence AND a completion/verdict word in that
same section or subject. Everything else proposes OPEN, with the reason in the
note. An item wrongly DONE stops work happening; an item wrongly OPEN only
costs a re-check, so the asymmetry is deliberate.

NAMESPACE COLLISIONS (real, found while building this)
------------------------------------------------------
The audit's id space overlaps the project's own labels:
  * "P5"/"P6"/"P7"/"P8"/"P10"/"P24.x" in CLAUDE.md and HANDOFF_STATUS.md are
    project PHASES, not audit items P1-P5. P6+ fall outside the audit's P1-P5
    and drop out on their own; P1-P5 genuinely collide and are handled below.
  * "M2" in CLAUDE.md is CODE_AUDIT.md's M2, a different document entirely.
For the colliding series, an occurrence must carry an audit cue nearby or sit in
a file that is unambiguously about the audit, or it is discarded as NOT-AN-ID.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "VALQUO_LEDGER.md"

# --------------------------------------------------------------------------
# locating inputs
# --------------------------------------------------------------------------
# valquo_audit_items.json, VALQUO_EDGE_AUDIT.md, VALQUO_ACTION_PLAN.md and
# AGENTS.md are UNTRACKED in the shared checkout (not gitignored -- never added).
# From a worktree under .claude/worktrees/<lane>/ the shared checkout is three
# levels up, so look there too rather than failing.
SEARCH_DIRS = [ROOT, ROOT.parent.parent.parent]


def find_input(name: str) -> Path | None:
    for d in SEARCH_DIRS:
        p = d / name
        if p.exists():
            return p
    return None


CORPUS_GLOBS = ["HANDOFF_*.md"]
CORPUS_EXTRA = ["CLAUDE.md", "RUN_RULES.md", "VALQUO_ACTION_PLAN.md", "AGENTS.md"]

# Files that are unambiguously about the external audit. Inside these, a bare
# P1-P5 is an audit item; outside them it is probably a project phase.
AUDIT_FILES = {"HANDOFF_edge_audit.md", "HANDOFF_optionsbot.md", "HANDOFF_r1.md",
               "VALQUO_ACTION_PLAN.md", "HANDOFF_free_analysis.md"}

COLLIDING_SERIES = {"P", "M"}
AUDIT_CUE = re.compile(
    r"audit|pre-?regist|threshold|verdict|ADOPTED|REJECTED|INCONCLUSIVE|"
    r"\bNULL\b|item\b", re.I)

# A reference to a DIFFERENT audit document. `CODE_AUDIT.md` also has an "M2",
# and HANDOFF_STATUS.md's "### The audit's M2 (SanDisk/WDC) does not reproduce"
# was mechanically read as the external audit's M2 ("Clustered inference
# default") -- two unrelated items sharing a label. The word "audit" is what
# let it through, so the audit cue alone is not enough.
FOREIGN_AUDIT = re.compile(r"CODE_AUDIT|SECURITY_AUDIT|the audit's\s+[A-Z]\d", re.I)

# The D series (D1..D10) collides with DECILE labels, which this project writes
# constantly: "long-short (D1-D10)", "D1 22.8% -> D10 10.7%". A line in decile
# context is never evidence about a data-purchasing item.
DECILE_CONTEXT = re.compile(
    r"decile|quantile|D1\s*[-–—>]+\s*D10|D10\s*[-–—>]+\s*D1|"
    r"\bbucket\b|long-short", re.I)

# A forward cue that DIRECTLY governs the id, matched against the text
# immediately to its left. This is what distinguishes
#   "## Task 3 — schema conformance (supports D1, the $29/mo switch)"   <- about D1's PREREQUISITE
# from
#   "## D1 — ..."                                                       <- about D1 itself
# The first is a heading and would otherwise count as strong evidence that D1
# is done. It is the heading-level form of the same error that inflated the 68.
FORWARD_GOVERNS = re.compile(
    r"\b(supports?|support(?:ing|ed)|feeds?|feeding|for|towards?|needed for|"
    r"required for|input to|unblocks?|blocks?|blocked by|depends? on|"
    r"prereq\w*|see|cf\.?|per|via|enables?|precondition for)\s+"
    r"(?:the\s+)?(?:audit\s+)?(?:item\s+)?$", re.I)

FORWARD_CUES = re.compile(
    r"\b(feeds?|needed for|needs|required for|prereq\w*|depends? on|"
    r"depend(?:ent|ency)|blocks?|blocked by|blocking|unblocks?|unblocked by|"
    r"waiting on|waits? on|see also|see\b|cf\.|next\b|then\b|after\b|once\b|"
    r"before\b|will\b|should\b|would\b|plan(?:ned|s)?\b|TODO|upcoming|"
    r"plumbing for|input to|precondition)\b", re.I)

DONE_CUES = re.compile(
    r"\b(ADOPTED|REJECTED|INCONCLUSIVE|NULL|DEFERRED|SUPERSEDED|"
    r"DONE|COMPLETE[D]?|SHIPPED|LANDED|FIXED|CLEARED|SETTLED|PASSED|"
    r"CONFIRMED|RETRACTED|ANSWERED|CLOSED|MEASURED|RESOLVED)\b")

# Verdict vocabulary -- the project's existing words. Do not invent new ones.
VERDICTS = ["ADOPTED", "REJECTED", "INCONCLUSIVE", "NULL", "DEFERRED"]
STATUSES = ["OPEN", "IN PROGRESS", "DONE", "BLOCKED", "SUPERSEDED"]

BLOCKED_CUES = re.compile(r"\bBLOCKED\b|\bPARKED\b|cannot (?:be )?run|"
                          r"needs? (?:an? )?(?:API key|licence|license|access)", re.I)


def load_items() -> dict:
    p = find_input("valquo_audit_items.json")
    if p is None:
        sys.exit("valquo_audit_items.json not found in: "
                 + ", ".join(str(d) for d in SEARCH_DIRS))
    return json.loads(p.read_text(encoding="utf-8"))


def id_pattern(ids) -> re.Pattern:
    series = sorted({re.match(r"([A-Z]+)", i).group(1) for i in ids})
    return re.compile(r"(?<![A-Za-z0-9])([" + "".join(series) + r"]\d{1,2})"
                      r"(?![0-9A-Za-z.])")


# --------------------------------------------------------------------------
# evidence collection
# --------------------------------------------------------------------------
Occurrence = collections.namedtuple(
    "Occurrence", "item kind file line text")


def corpus_files() -> list[Path]:
    seen, out = set(), []
    for g in CORPUS_GLOBS:
        for p in sorted(ROOT.glob(g)):
            if p.name not in seen:
                seen.add(p.name)
                out.append(p)
    for name in CORPUS_EXTRA:
        p = find_input(name)
        if p is not None and p.name not in seen:
            seen.add(p.name)
            out.append(p)
    return out


def classify(line: str, is_header: bool, before: str = "") -> str:
    # A governed forward reference is a forward reference wherever it sits --
    # including inside a heading. Check this BEFORE the header promotion.
    if FORWARD_GOVERNS.search(before):
        return "FORWARD"
    if is_header:
        return "HEADER"
    if FORWARD_CUES.search(line):
        return "FORWARD"
    return "PROSE"


def scan_corpus(ids, pat) -> list[Occurrence]:
    occ = []
    for path in corpus_files():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()
        ignoring = False
        for n, line in enumerate(lines, 1):
            # Opt-out markers. A handoff section that WRITES ABOUT the ledger
            # ("these 36 items are never mentioned", "--evidence S12") names
            # ids without being evidence about them, and would otherwise feed
            # its own numbers back in on the next refresh. Wrap such a region in
            # <!-- ledger:ignore --> ... <!-- /ledger:ignore -->.
            if "/ledger:ignore" in line:
                ignoring = False
                continue
            if "ledger:ignore" in line:
                ignoring = True
                continue
            if ignoring:
                continue
            found = {}
            for m in pat.finditer(line):
                if m.group(1) in ids:
                    found.setdefault(m.group(1), m.start(1))
            if not found:
                continue
            # A line that lists many ids is a ROLL-CALL -- a scope list, a
            # session plan, or this ledger's own report enumerating what is
            # still open. It says nothing about any individual item, and
            # counting it makes the ledger self-referential: publishing "these
            # 34 items are never mentioned" would itself become a mention of
            # all 34. Inventory is not evidence.
            if len(found) >= 7:
                continue
            is_header = bool(re.match(r"\s{0,3}#{1,6}\s", line))
            for item, pos in found.items():
                if item[0] == "D" and DECILE_CONTEXT.search(line):
                    continue
                if item[0] in COLLIDING_SERIES:
                    # Project phase P5 vs audit item P5; CODE_AUDIT's M2 vs
                    # audit M2. A line naming a different audit document is
                    # never evidence about this one, whatever file it sits in.
                    if FOREIGN_AUDIT.search(line):
                        continue
                    # Outside the audit-specific files, demand an audit cue.
                    if path.name not in AUDIT_FILES and not AUDIT_CUE.search(line):
                        continue
                occ.append(Occurrence(item,
                                      classify(line, is_header, line[:pos]),
                                      path.name, n, line.strip()))
    return occ


def section_text(path_name: str, start_line: int, limit: int = 120) -> str:
    """The body under a heading, up to the next heading of same-or-higher level."""
    for d in SEARCH_DIRS:
        p = d / path_name
        if p.exists():
            break
    else:
        return ""
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    head = lines[start_line - 1]
    level = len(re.match(r"\s{0,3}(#{1,6})", head).group(1))
    out = [head]
    for line in lines[start_line:start_line + limit]:
        m = re.match(r"\s{0,3}(#{1,6})\s", line)
        if m and len(m.group(1)) <= level:
            break
        out.append(line)
    return "\n".join(out)


def git_commits(ids, pat) -> dict:
    try:
        raw = subprocess.run(
            ["git", "log", "--no-merges", "--date=short",
             "--format=%h%x09%ad%x09%s", "-n", "4000"],
            cwd=ROOT, capture_output=True, text=True, timeout=120).stdout
    except Exception:
        return {}
    hits = collections.defaultdict(list)
    for row in raw.splitlines():
        parts = row.split("\t")
        if len(parts) != 3:
            continue
        sha, date, subj = parts
        for item in dict.fromkeys(m for m in pat.findall(subj) if m in ids):
            if item[0] in COLLIDING_SERIES and not AUDIT_CUE.search(subj):
                continue
            hits[item].append((sha, date, subj))
    return hits


# --------------------------------------------------------------------------
# proposal
# --------------------------------------------------------------------------
_HEADER_COMMIT_CACHE: dict = {}


def commit_for_header(file_name: str, header: str):
    """
    The commit that INTRODUCED a write-up's heading.

    Many items landed in multi-item commits whose subject never names them
    ("eleven Part I corrections"), so scanning subjects leaves the commit column
    empty for most of the B series. The commit that first recorded the section
    is a weaker claim than "the commit that fixed it", but it is a real,
    checkable anchor -- and it is labelled as such in the note.
    """
    key = (file_name, header)
    if key in _HEADER_COMMIT_CACHE:
        return _HEADER_COMMIT_CACHE[key]
    probe = header.strip()[:60]
    res = (None, None)
    try:
        raw = subprocess.run(
            ["git", "log", "--date=short", "--format=%h%x09%ad",
             "-S", probe, "--", file_name],
            cwd=ROOT, capture_output=True, text=True, timeout=60).stdout.strip()
        if raw:
            sha, date = raw.splitlines()[-1].split("\t")  # earliest = introduced
            res = (sha, date)
    except Exception:
        pass
    _HEADER_COMMIT_CACHE[key] = res
    return res


def propose(items, occ, commits) -> dict:
    by_item = collections.defaultdict(list)
    for o in occ:
        by_item[o.item].append(o)

    out = {}
    for item in items:
        os_ = by_item.get(item, [])
        headers = [o for o in os_ if o.kind == "HEADER"]
        fwd = [o for o in os_ if o.kind == "FORWARD"]
        prose = [o for o in os_ if o.kind == "PROSE"]
        cmts = commits.get(item, [])

        status, verdict, handoff, sha, date, note = "OPEN", "", "", "", "", ""

        strong = None
        for h in headers:
            body = section_text(h.file, h.line)
            if DONE_CUES.search(body) or DONE_CUES.search(h.text):
                strong = (h, body)
                break
        if strong is None and headers:
            strong = (headers[0], section_text(headers[0].file, headers[0].line))

        if strong is not None:
            h, body = strong
            handoff = h.file
            if DONE_CUES.search(body):
                status = "DONE"
                for v in VERDICTS:
                    if re.search(r"\b" + v + r"\b", body):
                        verdict = v
                        break
            else:
                status = "IN PROGRESS"
                note = "section exists, no completion word found"
            if BLOCKED_CUES.search(body) and status != "DONE":
                status = "BLOCKED"
        if cmts:
            # Prefer the most recent commit whose SUBJECT reads like the item
            # landing, over an incidental later touch. Without this, C5 cites
            # "gitignore the C5 ingest logs" instead of the commit that fixed it.
            best = next((c for c in cmts if DONE_CUES.search(c[2])), cmts[0])
            sha, date = best[0], best[1]
            if status == "OPEN" and DONE_CUES.search(best[2]):
                status = "DONE"
                note = "commit evidence only, no handoff section"

        if not sha and strong is not None and status in ("DONE", "IN PROGRESS"):
            h, _ = strong
            sha, date = commit_for_header(h.file, h.text)
            if sha:
                note = (note + "; " if note else "") + "commit = wrote-up-in"

        if status == "OPEN" and not note:
            # Deliberately no occurrence COUNT in the note. The corpus includes
            # the handoffs, and a handoff that lists open item ids (this
            # ledger's own report does) bumps every count -- churning every auto
            # row on refresh for no information. `--evidence <ID>` counts on
            # demand, which is when the number is actually worth having.
            if fwd and not prose and not headers:
                note = ("only forward references -- mentioned as a dependency, "
                        "never written up")
            elif prose:
                note = "prose mentions only, no section, no commit"
            elif not os_:
                note = "no mention anywhere in the corpus"

        out[item] = dict(status=status, verdict=verdict, commit=sha,
                         handoff=handoff, date=date, note=note,
                         n_header=len(headers), n_fwd=len(fwd),
                         n_prose=len(prose), n_commit=len(cmts))
    return out


# --------------------------------------------------------------------------
# ledger read / write
# --------------------------------------------------------------------------
COLS = ["id", "series", "title", "status", "verdict", "commit", "handoff",
        "date", "src", "note"]


def esc(s: str) -> str:
    return str(s).replace("|", r"\|").replace("\n", " ").strip()


def read_ledger() -> dict:
    if not LEDGER.exists():
        return {}
    rows = {}
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != len(COLS) or cells[0] in ("id", "---") or set(cells[0]) <= {"-", ":"}:
            continue
        rows[cells[0]] = dict(zip(COLS, cells))
    return rows


def existing_header() -> str:
    """
    Everything above the LEDGER TABLE in the CURRENT file.

    render() used to emit the hard-coded LEDGER_HEADER unconditionally, so
    --write silently deleted any prose a human had added underneath it -- on
    this file that was the whole "Ledger accuracy" section: R3's stale 1.36x
    note and the C6 "the only copy is on machine X" lesson. Same principle as
    the row rule: the script proposes rows, it does not curate prose.

    The boundary is the table's exact COLS header line, NOT the first line
    starting with "|". Splitting on any pipe truncated the header at the first
    ordinary markdown table in the prose -- the counts-by-series table -- and
    deleted every section after it. A ledger that documents its own counts is
    the expected case, so the boundary has to name the one table this script
    owns.

    Prose BELOW the table is still not preserved; render() appends the table
    last, so keep narrative above it.
    """
    if not LEDGER.exists():
        return LEDGER_HEADER
    marker = "| " + " | ".join(COLS) + " |"
    text = LEDGER.read_text(encoding="utf-8")
    head, sep, _ = text.partition(marker)
    if not sep:
        return LEDGER_HEADER
    return head or LEDGER_HEADER


def render(order, rows) -> str:
    head = existing_header()
    body = ["| " + " | ".join(COLS) + " |",
            "|" + "|".join(["---"] * len(COLS)) + "|"]
    for item in order:
        r = rows[item]
        body.append("| " + " | ".join(esc(r.get(c, "")) for c in COLS) + " |")
    return head + "\n".join(body) + "\n"


def summarise(items, rows, audit, extra=()) -> str:
    by_series = collections.defaultdict(collections.Counter)
    total = collections.Counter()
    for item in items:
        s = re.match(r"([A-Z]+)", item).group(1)
        st = rows[item]["status"]
        by_series[s][st] += 1
        total[st] += 1
    lines = ["", "COUNTS BY SERIES (the 134 external-audit items)", "-" * 74,
             f"{'series':8s}" + "".join(f"{s:>13s}" for s in STATUSES) + f"{'total':>8s}"]
    for s in sorted(by_series, key=lambda x: -sum(by_series[x].values())):
        c = by_series[s]
        lines.append(f"{s:8s}" + "".join(f"{c[st]:13d}" for st in STATUSES)
                     + f"{sum(c.values()):8d}")
    lines.append("-" * 74)
    lines.append(f"{'ALL':8s}" + "".join(f"{total[st]:13d}" for st in STATUSES)
                 + f"{sum(total.values()):8d}")
    human = sum(1 for i in items if rows[i].get("src") != "auto")
    lines.append("")
    lines.append(f"hand-verified rows: {human}/{len(items)}   "
                 f"auto rows: {len(items) - human}")
    if extra:
        # Out-of-band rows are real work and are counted separately rather than
        # folded in, so "72 of 134 DONE" keeps meaning what it has always meant.
        ec = collections.Counter(rows[k]["status"] for k in extra)
        lines += ["",
                  f"OUT-OF-BAND rows (not audit items, preserved verbatim): {len(extra)}",
                  "  " + "  ".join(f"{k}={v}" for k, v in sorted(ec.items()))
                  + "   [" + ", ".join(extra) + "]"]
    return "\n".join(lines)


LEDGER_HEADER = """<!-- GENERATED-AND-CURATED. Refresh with: python scripts/build_ledger.py -->
# VALQUO_LEDGER.md — the one place that answers "where do we stand?"

One row per external-audit item (`valquo_audit_items.json`, 134 items). This
file replaces reconstructing project state from git history.

## The contract (three rules — read them, they are why this file exists)

1. **Every agent updates its rows as part of its handoff.** A landed item with
   no ledger row is not finished work — the same standing as the existing
   "code without a handoff entry is not finished work" rule in `RUN_RULES.md`.
2. **The ledger is the answer to "where do we stand."** If it cannot answer,
   the ledger is broken and *fixing the ledger* is the task. Never another
   archaeology dig.
3. **Rows are append-and-amend, never silently rewritten.** A status that
   changes keeps its history in the note (`was X (sha) -> now Y`), because this
   project has already been bitten by claims that quietly changed meaning.

## How to read a row

* **status** — `OPEN` / `IN PROGRESS` / `DONE` / `BLOCKED` / `SUPERSEDED`.
* **verdict** — only for items that were actually measured: `ADOPTED` /
  `REJECTED` / `NULL` / `INCONCLUSIVE` / `DEFERRED`. It is filled in **only when
  the write-up literally uses one of those five words.** Most of the B series
  concluded `FIXED`, and `X8` concluded `REPLICATES` — real outcomes, but not
  verdicts in this vocabulary, so their column is blank and the write-up's own
  word is quoted in the note instead. Blank therefore means *"not measured, or
  measured and reported in different words"* — never *"we don't know"*.
* **commit** — a sha, so any claim here is checkable in one step. It is the
  commit whose *subject names the item* where one exists; otherwise it is the
  commit that **introduced the write-up**. Many items landed inside multi-item
  commits ("eleven Part I corrections") that never name them, so for much of the
  B series this is *"where it was recorded"*, not *"where it was fixed"* — a
  weaker claim, and stated here rather than left to be assumed. Unfinished rows
  carry no sha at all: a commit that merely *mentioned* an item reads as
  evidence of work done, and is worse than a blank.
* **handoff** — where the real write-up lives. The ledger is an index, not a
  replacement for it.
* **src** — `human` = hand-verified against the write-up; `build_ledger.py`
  will NOT overwrite it, only report a disagreement. `auto` = mechanically
  proposed and not yet read by a person; treat as a lead, not a fact.

## Four traps that already produced wrong counts — do not re-make them

1. **A forward reference is not a completion.** "feeds U1", "needed for S12",
   "(supports D1)" say the item is *wanted*, not *done*. Counting these is what
   produced the 68/134 figure against a header-only count of 38/134.
2. **`P1`–`P5` collide with the project's own PHASE labels.** CLAUDE.md's
   "DONE (P4 commit)" is phase P4; audit item P4 is open and explicitly "out of
   band". `P6`–`P10` and `P24.x` are phases only — the audit's P series stops
   at P5.
3. **`M2` is ambiguous across documents.** HANDOFF_STATUS.md's "the audit's M2
   (SanDisk/WDC)" is `CODE_AUDIT.md`'s M2. The external audit's M2 is
   "clustered inference default" and has never been touched.
4. **`D1`–`D10` collide with DECILE labels**, which this project writes
   constantly ("long-short (D1-D10)", "D1 22.8% → D10 10.7%").

`build_ledger.py` encodes all four. If you add a source file, re-check them.

## Refresh

    python scripts/build_ledger.py            # proposal + counts, writes nothing
    python scripts/build_ledger.py --write    # refresh src=auto rows only
    python scripts/build_ledger.py --evidence S12   # show why S12 sits where it does

"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--write", action="store_true",
                    help="refresh src=auto rows in VALQUO_LEDGER.md")
    ap.add_argument("--summary", action="store_true", help="counts only")
    ap.add_argument("--evidence", metavar="ID", help="dump evidence for one item")
    ap.add_argument("--proposal", action="store_true",
                    help="print the full mechanical proposal")
    args = ap.parse_args()

    # The corpus is full of em-dashes and arrows; the Windows console is cp1252.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

    audit = load_items()
    items = list(audit.keys())
    pat = id_pattern(items)
    occ = scan_corpus(set(items), pat)
    commits = git_commits(set(items), pat)
    prop = propose(items, occ, commits)

    if args.evidence:
        item = args.evidence.upper()
        if item not in audit:
            print(f"{item}: not an audit item")
            return 2
        print(f"{item} — {audit[item]['title']}")
        print(f"proposal: {prop[item]}")
        for o in occ:
            if o.item == item:
                print(f"  [{o.kind:7s}] {o.file}:{o.line}  {o.text[:150]}")
        for sha, date, subj in commits.get(item, []):
            print(f"  [COMMIT ] {sha} {date}  {subj[:140]}")
        return 0

    existing = read_ledger()
    rows, disagreements = {}, []
    for item in items:
        p = prop[item]
        base = dict(id=item, series=re.match(r"([A-Z]+)", item).group(1),
                    title=audit[item]["title"], src="auto", **{
                        k: p[k] for k in ("status", "verdict", "commit",
                                          "handoff", "date", "note")})
        old = existing.get(item)
        # ANY src that is not the literal "auto" is a human-curated row. The
        # check used to be `== "human"`, which silently demoted the seven rows
        # a lane had signed `src=pipeline builder` -- they were rewritten from
        # the mechanical proposal on every --write, losing B8's and P4's FIXED
        # verdicts. Trusting the one value the script itself writes is the safe
        # direction: a new src spelling now degrades to "protected", not to
        # "overwrite me".
        if old and old.get("src") != "auto":
            rows[item] = old
            if old.get("status") != p["status"]:
                disagreements.append(
                    (item, old.get("status"), p["status"], p["note"]))
        elif old:
            merged = dict(old)
            merged.update({k: base[k] for k in
                           ("status", "verdict", "commit", "handoff", "date",
                            "note", "title", "series")})
            rows[item] = merged
        else:
            rows[item] = base

    # Rows that are not audit ids at all -- out-of-band findings (OOB*) and the
    # project's own pre-registered experiments (LOO, SELRULE, HACFLOOR, MLCOMB,
    # MLPREREG). render() used to iterate the 134 audit ids, so --write DELETED
    # every one of them; OOB1's own note had to warn readers about it. They are
    # preserved verbatim and in place: this script proposes, it does not curate.
    extra = [k for k in existing if k not in set(items)]
    for k in extra:
        rows[k] = existing[k]
    # Existing file order first, so nothing moves; genuinely new ids append.
    order = list(existing) + [i for i in items if i not in existing]

    if args.proposal:
        for item in items:
            p = prop[item]
            print(f"{item:5s} {p['status']:12s} {p['verdict']:13s} "
                  f"h={p['n_header']} c={p['n_commit']} f={p['n_fwd']} "
                  f"p={p['n_prose']}  {p['handoff']:28s} {p['note'][:60]}")

    if disagreements:
        print("\nDISAGREEMENTS — human row vs mechanical proposal "
              "(human row kept, nothing overwritten)")
        print("-" * 74)
        for item, human, auto, why in disagreements:
            print(f"  {item:5s} human={human:12s} proposal={auto:12s}  {why[:50]}")
    elif existing:
        print("\nno disagreements between hand-verified rows and the proposal")

    print(summarise(items, rows, audit, extra))

    if args.write:
        n_human = sum(1 for i in items if rows[i].get("src") != "auto")
        LEDGER.write_text(render(order, rows), encoding="utf-8")
        print(f"\nwrote {LEDGER} ({len(order)} rows = {len(items)} audit + "
              f"{len(extra)} out-of-band; {n_human} preserved as hand-verified)")
    elif not args.summary:
        print("\n(no files written — pass --write to refresh src=auto rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
