#!/usr/bin/env python3
"""
board_state.py - MB27. Derive the board from git instead of typing it out.

    python scripts/board_state.py                 # the report
    python scripts/board_state.py --json          # machine-readable
    python scripts/board_state.py --write         # snapshot to .board_state.json

WHY THIS EXISTS
---------------
`ma_in_flight.json` was hand-typed on 2026-08-14 to answer "which items are being
worked RIGHT NOW". Measured on 2026-08-19 it listed MA13, MA19, MA36, MA37, MA15,
MA16, MA20 and MA35 -- **eight items, all eight now DONE**. Five days stale, 100%
wrong, and carrying its own `how_to_refresh` command that nobody ran.

That is MA59/MA60 one level up. Those items replaced `check_lanes.py`'s hand-typed
import dictionary with a derived graph, after measuring the literal at 13 keys / 40
edges against a real 118 / 546. The disease here is identical: a hand-typed snapshot
of something git already knows.

IT DOES NOT WARN, AND THAT IS THE DESIGN, NOT AN OVERSIGHT
----------------------------------------------------------
MA21 declined a proposed blank-verdict warning because it would have fired on 41
legitimate rows and been switched off inside a week; MB30 names that refusal as
binding on this item. So this script has NO judgement in it. It emits counts and
exits 0 on every finding it can report -- a stale lock, a dirty worktree and an empty
board all exit 0. The only non-zero exit is 2, and it means the SCRIPT failed, not
that the board is bad.

`checkout_drift.py` takes the opposite line ("'I could not tell' and 'all clear' must
never share an exit code") and both are right, because they are different objects: an
ALARM exists to fail, a REPORT exists to describe. What this borrows from the alarm is
the half that always applies -- **an unmeasurable ingredient is reported as `null` and
rendered UNMEASURED, never silently as 0.** A zero that means "nothing in flight" and a
zero that means "git did not answer" would be the same failure in a new costume.

TWO OF THE AUDIT'S FOUR PROPOSED DERIVATIONS ARE WRONG, MEASURED
----------------------------------------------------------------
1. **`IN ?PROGRESS` against the ledger status cell matches a cell that says the
   opposite.** `B13`'s status reads `**PARTIAL - BLOCKED ON DATA, NOT IN PROGRESS**`.
   The naive rule has a **50% false-positive rate on today's two hits**. This project
   already found that exact trap once, by hand, in the PT-WRITER session -- CLAIMED
   items are matched here only when the occurrence is not negated.

2. **A HANDOFF's mtime is not its freshness.** Measured in this worktree immediately
   after `git merge origin/main`: `HANDOFF_edge_audit.md` and `HANDOFF_optionsbot.md`
   both carried an mtime of the merge minute, while `HANDOFF_ci.md`, which the merge
   did not touch, still read three days old. mtime records when git last WROTE the file
   into this checkout, so in a fresh worktree every handoff reads as newly touched. Age
   is taken from **the newest commit touching the file**, which is a property of the
   work, and uncommitted modification is read from `git status` rather than inferred.

WHAT IT ADDS THAT THE HAND FILE COULD NOT
------------------------------------------
`ma_in_flight.json`'s own caveat names its blind spot: *"an agent editing files in a
worktree with nothing committed yet is invisible here"*. That is derivable --
`git status --porcelain` per worktree -- and it is the ingredient most likely to catch
a live collision, so it is measured here. The audit's MB29 records the same class of
miss from the other side: audit #4's own commission sat untracked as
`?? PROMPT_audit4_master.md` while the audit was being written.

It also reports how old `origin/main` itself is. A board that says "0 lanes in flight"
off a week-old fetch is not measuring the board, and nothing in the hand file said when
its refs were last refreshed.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# `--write` goes to a GITIGNORED path, and `ma_in_flight.json` is now a pointer that
# makes no dated claim at all. That is a deliberate departure from MB27, which proposed
# a committed generated board plus a test that fails when it is "older than the newest
# branch tip it claims to describe". Measured against this board's own ingredients, that
# assertion cries wolf: `worktrees_with_uncommitted_work` reads 8 of 12 right now and
# changes whenever anybody saves a file, so a committed snapshot would go stale within
# minutes of every regeneration and the test would be red on ordinary work -- MA21's
# failure mode, reached by a pin instead of by a warning. A generated snapshot rots
# exactly like a hand-typed one; it just rots honestly.
#
# So there is ONE copy of the fact, and it is git. The retired file is kept (rule 9) as
# a pointer plus its own contents, and a file that makes no claim about today cannot
# become wrong -- which is the only version of MB27's assertion that cannot fire on
# somebody doing their job.
SNAPSHOT = ROOT / ".board_state.json"

# MB28's clock writes here. Outside the repo on purpose, for valquo_sync_bootstrap.bat's
# reason: the heartbeat has to keep working while the checkout it measures is stale.
HEARTBEAT = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Valquo" / "drift.json"

OK = 0
BROKEN = 2

# A branch is a LANE only if it is one. rescue/* and backup/* are deliberately-kept refs
# -- the sync bootstrap creates rescue/ branches, and three backup/ refs predate this
# script -- so counting them as in-flight work would put five permanent phantom lanes on
# the board. That is MA21's failure mode reached by arithmetic instead of by a warning.
LANE = re.compile(r"^(?:origin/)?worktree-")
KEEP = re.compile(r"^(?:origin/)?(?:rescue|backup)/")

_CLAIM = re.compile(r"IN[\s_-]?PROGRESS")
_NEGATED = re.compile(r"(?:NOT|NEVER|NO LONGER|WAS|IS NOT)\s*$")


def _git(*args: str, repo: Path | str = ROOT, timeout: int = 60) -> str:
    p = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {p.stderr.strip()[:200]}")
    return p.stdout


def is_claimed(status: str) -> bool:
    """True only for a status cell that CLAIMS the item, not one that disclaims it.

    `B13` reads "PARTIAL - BLOCKED ON DATA, NOT IN PROGRESS". A substring test says
    claimed; the row says the opposite.
    """
    s = re.sub(r"[*_`]", "", status or "").upper()
    for m in _CLAIM.finditer(s):
        if _NEGATED.search(s[max(0, m.start() - 16):m.start()].strip()):
            continue
        return True
    return False


def branches(base: str = "origin/main") -> list[dict]:
    """Every ref carrying commits `base` does not have, classified.

    The unmerged set is taken in ONE `for-each-ref --no-merged` call per scope, and
    `rev-list --count` runs only on what survives. The first cut ran a `rev-list` per
    ref -- 17.3 seconds and ~120 subprocesses to find 7 branches -- which is slow enough
    that a report nobody wants to wait for is a report nobody runs.
    """
    out = []
    fmt = "%(refname:short)\t%(committerdate:unix)"
    for scope in ("refs/heads", "refs/remotes/origin"):
        for line in _git("for-each-ref", "--no-merged", base,
                         "--format=" + fmt, scope).splitlines():
            if not line.strip():
                continue
            name, _, ts = line.partition("\t")
            if name in (base, "origin/HEAD", "main"):
                continue
            ahead = int(_git("rev-list", "--count", f"{base}..{name}").strip())
            if not ahead:
                continue
            kind = "lane" if LANE.match(name) else "kept" if KEEP.match(name) else "other"
            out.append({"ref": name, "ahead": ahead, "kind": kind,
                        "tip_epoch": int(ts or 0),
                        "remote": scope.endswith("origin")})
    return sorted(out, key=lambda r: (-r["tip_epoch"], r["ref"]))


def worktrees(base: str = "origin/main") -> list[dict]:
    """Every worktree, with the thing the hand file admitted it could not see: dirt."""
    out, cur = [], {}
    for line in _git("worktree", "list", "--porcelain").splitlines():
        if not line.strip():
            if cur:
                out.append(cur)
            cur = {}
            continue
        key, _, val = line.partition(" ")
        if key == "worktree":
            cur = {"path": val, "branch": None, "head": None,
                   "locked": False, "detached": False}
        elif key == "HEAD":
            cur["head"] = val[:7]
        elif key == "branch":
            cur["branch"] = val.replace("refs/heads/", "")
        elif key == "detached":
            cur["detached"] = True
        elif key == "locked":
            cur["locked"] = True
    if cur:
        out.append(cur)

    for w in out:
        w["dirty"] = None          # null, never 0 -- see the module docstring
        w["untracked"] = None
        w["ahead"] = None
        w["behind"] = None
        try:
            st = _git("status", "--porcelain", repo=w["path"]).splitlines()
            w["dirty"] = sum(1 for L in st if not L.startswith("??"))
            w["untracked"] = sum(1 for L in st if L.startswith("??"))
        except Exception:
            pass
        try:
            counts = _git("rev-list", "--left-right", "--count",
                          f"{base}...{w['head']}").split()
            w["behind"], w["ahead"] = int(counts[0]), int(counts[1])
        except Exception:
            pass
    return out


def claimed(rows: dict | None = None) -> list[dict]:
    """Ledger rows claiming to be in flight.

    Delegates to `build_ledger.read_ledger` rather than re-parsing the table. Two copies
    of one parser is the defect MA39 and MA5 both closed, and that parser already carries
    the raw-pipe hazard's fix, which a second one would not.
    """
    if rows is None:
        sys.path.insert(0, str(ROOT / "scripts"))
        import build_ledger  # noqa: E402  (path-dependent by design)
        rows = build_ledger.read_ledger()
    return [{"id": k, "status": v.get("status", ""), "handoff": v.get("handoff", ""),
             "date": v.get("date", "")}
            for k, v in rows.items() if is_claimed(v.get("status", ""))]


def handoffs(now: float | None = None) -> list[dict]:
    """Age of every root HANDOFF, from the record rather than from the filesystem."""
    now = time.time() if now is None else now
    names = [p.name for p in sorted(ROOT.glob("HANDOFF_*.md"))]

    # THE SPEEDUP RUNS THE IDENTICAL COMMAND IN PARALLEL, and that is a correctness
    # choice rather than a lazy one. 48 serial `git log -1` calls cost 10.1s, so the
    # first cut replaced them with ONE `git log --name-only` walk taking the first
    # timestamp each filename appears under. Checked against the per-file command
    # rather than assumed inert: **it disagreed on 2 of 48**, both times returning an
    # OLDER commit -- because `--name-only` prints no filenames for a MERGE commit, so
    # a handoff whose newest touch arrived through a merge silently reads as older than
    # it is. On a repo that lands every lane through a merge that is the common case,
    # not a corner. Parallelising the real command cannot drift from it by construction.
    def _last(name: str):
        try:
            raw = _git("log", "-1", "--format=%ct", "--", name).strip()
            return name, (int(raw) if raw else None)
        except Exception:
            return name, None

    newest: dict[str, int | None] = {}
    try:
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            for name, ts in ex.map(_last, names):
                newest[name] = ts
    except Exception:
        newest = {}

    out = []
    for p in sorted(ROOT.glob("HANDOFF_*.md")):
        last = newest.get(p.name)
        out.append({
            "file": p.name,
            "last_commit_epoch": last,
            "age_days": None if last is None else round((now - last) / 86400.0, 2),
        })
    return out


def dirty_handoffs() -> list[str]:
    try:
        st = _git("status", "--porcelain", "--", "HANDOFF_*.md").splitlines()
    except Exception:
        return []
    return sorted({L[3:].strip().strip('"') for L in st if L.strip()})


def locks(now: float | None = None) -> list[dict]:
    """Git locks and their age. Reported; never judged -- an active git holds a lock."""
    now = time.time() if now is None else now
    try:
        common = Path(_git("rev-parse", "--path-format=absolute",
                           "--git-common-dir").strip())
    except Exception:
        common = ROOT / ".git"
    out = []
    seen = set()
    for pat in ("*.lock", "objects/*.lock", "refs/**/*.lock", "worktrees/*/locked"):
        for p in common.glob(pat):
            if p in seen or not p.is_file():
                continue
            seen.add(p)
            out.append({"path": str(p),
                        "age_hours": round((now - p.stat().st_mtime) / 3600.0, 2)})
    return sorted(out, key=lambda r: -r["age_hours"])


def heartbeat(path: Path | None = None, now: float | None = None) -> dict:
    """MB28's clock. Absent means the scheduled task is not installed -- say so."""
    now = time.time() if now is None else now
    p = HEARTBEAT if path is None else path
    if not p.exists():
        return {"path": str(p), "present": False, "age_hours": None,
                "note": "not installed - run install_drift_task.bat once (MB28)"}
    age = round((now - p.stat().st_mtime) / 3600.0, 2)
    d = {"path": str(p), "present": True, "age_hours": age, "note": ""}
    try:
        d["last"] = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        d["note"] = f"unreadable: {e}"
    return d


def fetch_age(now: float | None = None) -> dict:
    """How old the refs this board is derived FROM are."""
    now = time.time() if now is None else now
    try:
        common = Path(_git("rev-parse", "--path-format=absolute",
                           "--git-common-dir").strip())
    except Exception:
        return {"age_hours": None}
    fh = common / "FETCH_HEAD"
    if not fh.exists():
        return {"age_hours": None}
    return {"age_hours": round((now - fh.stat().st_mtime) / 3600.0, 2)}


def prompt_receipts(lanes: list[str]) -> list[dict]:
    """MB29 - per in-flight lane, does a `PROMPT_*.md` exist on it?

    The register discipline requires a `PREREG_*.md` committed ALONE and a strict ancestor of
    every measurement commit, precisely so intent is provably prior to result. MB29 applies the
    same shape one level up: **a lane's first commit is its prompt**, so what was ASKED is
    discoverable on `origin/main` rather than living in a manager's head.

    The miss it closes is dated: at audit #4's start `git status` read
    `?? PROMPT_audit4_master.md` — the commission defining that audit was untracked, so at the
    moment it began no other lane could have discovered what was being worked.

    **REPORTED, NEVER ASSERTED.** This returns a count and a boolean per lane and nothing here
    fails, warns or exits non-zero — MB29's own "false-alarm risk: none", and MB30/MA21's rule
    that a guard firing on legitimate cases gets switched off within a week. A lane without a
    prompt file is a fact about discoverability, not a defect to be alarmed about.
    """
    out = []
    for lane in lanes:
        try:
            files = _git("ls-tree", "-r", "--name-only", f"origin/{lane}").splitlines()
        except Exception:
            out.append({"lane": lane, "prompt": None, "files": None})   # UNMEASURED, not False
            continue
        found = sorted(f for f in files
                       if f.startswith("PROMPT_") and f.endswith(".md"))
        out.append({"lane": lane, "prompt": bool(found), "files": found[:5]})
    return out


def board(now: float | None = None) -> dict:
    now = time.time() if now is None else now
    b = {"_meta": {
        "what": "Board state DERIVED from git. Do not hand-edit; run the command below.",
        "how_to_refresh": "python scripts/board_state.py",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
        "generated_epoch": int(now),
        "warns": "never - this file reports counts and carries no verdict (MB30/MA21)",
        "caveat": "Derived from the refs present when it ran. Check refs_age_hours.",
    }}
    for name, fn in (("branches", branches), ("worktrees", worktrees),
                     ("claimed", claimed)):
        try:
            b[name] = fn()
        except Exception as e:                       # unmeasured, never zero
            b[name] = None
            b["_meta"].setdefault("unmeasured", {})[name] = str(e)[:200]
    for name, fn in (("handoffs", handoffs), ("locks", locks)):
        try:
            b[name] = fn(now)
        except Exception as e:
            b[name] = None
            b["_meta"].setdefault("unmeasured", {})[name] = str(e)[:200]
    b["handoffs_modified"] = dirty_handoffs()
    b["heartbeat"] = heartbeat(None, now)
    b["refs_age_hours"] = fetch_age(now).get("age_hours")

    # ONE lane, not two. `worktree-x` and `origin/worktree-x` are the same lane seen
    # locally and remotely, and the first run of this script counted them separately and
    # reported "LANES IN FLIGHT: 2" for a single live lane. Caught by running it.
    lanes = sorted({r["ref"].removeprefix("origin/")
                    for r in (b["branches"] or []) if r["kind"] == "lane"})
    dirty = [w for w in (b["worktrees"] or []) if (w.get("dirty") or w.get("untracked"))]
    b["lanes"] = lanes
    try:
        b["prompt_receipts"] = prompt_receipts(lanes)          # MB29
    except Exception as e:
        b["prompt_receipts"] = None
        b["_meta"].setdefault("unmeasured", {})["prompt_receipts"] = str(e)[:200]
    _pr = b.get("prompt_receipts") or []
    b["counts"] = {
        "lanes_in_flight": None if b["branches"] is None else len(lanes),
        "lanes_with_a_prompt_receipt": (None if b.get("prompt_receipts") is None
                                        else len([r for r in _pr if r["prompt"]])),
        "kept_refs": None if b["branches"] is None else
                     len([r for r in b["branches"] if r["kind"] == "kept"]),
        "worktrees": None if b["worktrees"] is None else len(b["worktrees"]),
        "worktrees_with_uncommitted_work": None if b["worktrees"] is None else len(dirty),
        "claimed_items": None if b["claimed"] is None else len(b["claimed"]),
        "handoffs": None if b["handoffs"] is None else len(b["handoffs"]),
        "locks": None if b["locks"] is None else len(b["locks"]),
    }
    return b


def _n(v) -> str:
    return "UNMEASURED" if v is None else str(v)


def render(b: dict) -> list[str]:
    c = b["counts"]
    out = ["", "=" * 76, "  BOARD STATE - derived, not typed", "=" * 76,
           f"  generated {b['_meta']['generated_at']}"
           f"   refs {_n(b.get('refs_age_hours'))}h old", ""]

    out.append(f"  LANES IN FLIGHT: {_n(c['lanes_in_flight'])}"
               f"   (kept rescue/backup refs, not lanes: {_n(c['kept_refs'])})")
    for lane in b.get("lanes", []):
        refs = [r for r in (b["branches"] or [])
                if r["ref"].removeprefix("origin/") == lane]
        where = "local+remote" if len(refs) > 1 else (
            "remote only" if refs and refs[0]["remote"] else "local only")
        pr = next((r for r in (b.get("prompt_receipts") or []) if r["lane"] == lane), None)
        # MB29: reported, never asserted. "no prompt" is a discoverability fact, not a defect.
        rec = "" if pr is None else (
            "  prompt: yes" if pr["prompt"] else
            "  prompt: none on branch" if pr["prompt"] is False else "  prompt: UNMEASURED")
        out.append(f"    {lane:<44} +{refs[0]['ahead']:<4} {where}{rec}")
    if c["lanes_in_flight"] == 0:
        out.append("    none - no worktree-* branch carries a commit origin/main lacks")

    out.append("")
    out.append(f"  WORKTREES: {_n(c['worktrees'])}"
               f"   with uncommitted work: {_n(c['worktrees_with_uncommitted_work'])}")
    for w in (b["worktrees"] or []):
        d, u = w.get("dirty"), w.get("untracked")
        if d or u:
            out.append(f"    {Path(w['path']).name:<36} {w['branch'] or 'detached'}"
                       f"  modified={_n(d)} untracked={_n(u)}")

    out.append("")
    out.append(f"  ITEMS CLAIMING TO BE IN FLIGHT: {_n(c['claimed_items'])}")
    for r in (b["claimed"] or []):
        out.append(f"    {r['id']:<10} {r['status'][:52]}   {r['handoff']}")

    stale = sorted([h for h in (b["handoffs"] or []) if h["age_days"] is not None],
                   key=lambda h: -h["age_days"])[:3]
    out.append("")
    out.append(f"  HANDOFFS: {_n(c['handoffs'])}   oldest by last commit:")
    for h in stale:
        out.append(f"    {h['file']:<40} {h['age_days']:>7.2f} d")
    if b["handoffs_modified"]:
        out.append(f"    uncommitted right now: {', '.join(b['handoffs_modified'])}")

    out.append("")
    out.append(f"  GIT LOCKS: {_n(c['locks'])}")
    for L in (b["locks"] or []):
        out.append(f"    {L['age_hours']:>8.2f} h  {L['path']}")

    hb = b["heartbeat"]
    out.append("")
    out.append("  DRIFT HEARTBEAT (MB28): "
               + (f"{hb['age_hours']}h old" if hb["present"] else "NOT INSTALLED"))
    if hb.get("note"):
        out.append(f"    {hb['note']}")

    out += ["", "  This report carries no verdict and exits 0. See MB30.", ""]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Derive the board from git. Never warns.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true",
                    help=f"write a snapshot to {SNAPSHOT.name} (gitignored)")
    ap.add_argument("--out", default=None,
                    help="write the snapshot somewhere else")
    a = ap.parse_args(argv)
    try:
        b = board()
    except Exception as e:                     # the SCRIPT failed, not the board
        print(f"[BROKEN] board_state could not run: {e}", file=sys.stderr)
        return BROKEN
    if a.write or a.out:
        out = Path(a.out) if a.out else SNAPSHOT
        out.write_text(json.dumps(b, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {out}")
    if a.json:
        print(json.dumps(b, indent=1))
    else:
        print("\n".join(render(b)))
    return OK


if __name__ == "__main__":
    sys.exit(main())
