#!/usr/bin/env python3
r"""
sync_checkout.py - the CURE for MA20. `checkout_drift.py` is the alarm.

    python scripts/sync_checkout.py --dry-run     # say exactly what it would do
    python scripts/sync_checkout.py               # do the safe part, alarm on the rest
    python scripts/sync_checkout.py --adopt-remote   # finish, once the work is provably safe
    python scripts/sync_checkout.py --repo X --json

WHAT DRIFT ACTUALLY LOOKS LIKE HERE
-----------------------------------
Measured on the real shared checkout 2026-08-15: **540 behind, 1 ahead, 27 dirty
entries** (2 modified tracked files, 25 untracked). `sync.bat` is named everywhere as
"the cure" and CANNOT cure that state, for three separate reasons found by reading it:

  1. it pushes `refs/heads/worktree-*` only, so a commit sitting on `main` is never sent;
  2. its `git merge --ff-only origin/main` is impossible on a diverged branch, and its
     exit code is not checked, so the failure scrolls past;
  3. with no `worktree-*` branch pending it then prints "everything is merged. You are
     fully up to date" -- a FALSE ALL-CLEAR on the exact state the machine is in.

So the drift was not invisible for want of a cure. It was invisible because the cure
reported success. That is the thing this file is built not to do.

WHAT IT DOES, IN ORDER
----------------------
  A. RESCUE COMMITS      push unpushed commits on the local branch to `rescue/<branch>-<sha>`.
  B. SNAPSHOT WORKTREE   push uncommitted TRACKED modifications as a commit, without
                         touching HEAD, the index or a single file on disk.
  C. FAST-FORWARD        only when the local branch is strictly behind. Untracked files
                         that block it are MOVED to `_sync_quarantine/<ts>/`, never deleted.
  D. REPORT              exit 0 only if nothing is left outstanding.

A and B are unconditional, additive, and cannot lose anything: they only ever create refs
on the remote. C is the only phase that writes to the working tree.

WHY IT RESCUES TO `rescue/*` AND NOT TO `worktree-*`
----------------------------------------------------
`worktree-*` is auto-landed by the gate Action. Landing a stranded commit unreviewed is a
bad default in general, and MEASURED it is a bad idea for the commit actually sitting there:
41d7b12 diffs as 2,226 insertions / 2,212 deletions of HANDOFF_STATUS.md, of which
`--ignore-all-space --ignore-blank-lines` shows the real content is **14 added lines** -- the
rest is CRLF churn, the whole-tree renormalisation `.gitattributes` says it deliberately
avoids. That file is also `merge=union`, so a merge would keep BOTH sides and roughly double
it. Rescuing is about work existing in two places; landing is a separate, deliberate act.
`--land` opts into the gated route for callers who want it.

WHY IT REFUSES THE LAST STEP BY DEFAULT
---------------------------------------
Once a branch has diverged, un-diverging means discarding either the local commits or the
remote's. Doing that unattended is the one operation here that can destroy work, so it is not
the default: the tool completes everything additive, then alarms loudly and names the single
command. `--adopt-remote` does it, and refuses unless it has just VERIFIED on the remote that
every local commit and every local modification is reachable there. It moves a branch pointer
whose content is provably duplicated -- it does not discard work.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.checkout_drift import (  # noqa: E402
    ALARM, OK, SHARED_CHECKOUT, DriftUnknown, measure,
)

QUARANTINE = "_sync_quarantine"

# git names the files it refuses to clobber, one per line, indented, between a known
# header and a blank line. Parsing git's own answer beats re-deriving which files
# collide: git already knows, and a second implementation would drift from it.
_UNTRACKED_HDR = "untracked working tree files would be overwritten"
_TRACKED_HDR = "local changes to the following files would be overwritten"


def _git(repo: str, *args: str, timeout: int = 300, env: dict | None = None,
         check: bool = True) -> subprocess.CompletedProcess:
    e = {**os.environ, **(env or {})}
    try:
        p = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True,
                           timeout=timeout, env=e)
    except FileNotFoundError:
        raise DriftUnknown("git is not on PATH")
    except subprocess.TimeoutExpired:
        raise DriftUnknown(f"git {' '.join(args)} timed out after {timeout}s")
    except NotADirectoryError:
        raise DriftUnknown(f"not a directory: {repo}")
    if check and p.returncode != 0:
        err = ((p.stderr or "") + (p.stdout or "")).strip().splitlines()
        raise DriftUnknown(f"git {' '.join(args)} failed: {err[0] if err else '?'}")
    return p


def _out(repo: str, *args: str, **kw) -> str:
    return _git(repo, *args, **kw).stdout.strip()


def _blocked_files(text: str, header: str) -> list[str]:
    """Pull the indented file list git prints under `header`.

    Matches the header case-insensitively but returns the file names in their ORIGINAL
    case -- these become paths that get moved on disk, and lower-casing them would
    silently quarantine the wrong thing (or nothing) on a case-sensitive filesystem.
    """
    out: list[str] = []
    grabbing = False
    for ln in text.splitlines():
        if header.lower() in ln.lower():
            grabbing = True
            continue
        if grabbing:
            if ln.startswith((" ", "\t")) and ln.strip():
                out.append(ln.strip())
            elif out:
                break
    return out


# ---------------------------------------------------------------------------- state
def survey(repo: str, branch: str, remote: str, fetch: bool = True) -> dict:
    """Everything the plan depends on, measured once."""
    st = measure(repo, remote, branch, fetch=fetch)
    head_branch = _out(repo, "rev-parse", "--abbrev-ref", "HEAD")
    # NOT _out(): that strips the whole blob, which eats the LEADING SPACE of porcelain's
    # first line -- ` M HANDOFF_STATUS.md` became `M HANDOFF_STATUS.md`, and a fixed
    # `ln[3:]` slice then read the path as `ANDOFF_STATUS.md`. Caught by --dry-run before
    # any run touched disk; a phantom filename here is one that gets moved into
    # quarantine, so the failure would have been a file silently not preserved.
    porcelain = _git(repo, "status", "--porcelain").stdout
    modified, untracked = [], []
    for ln in porcelain.splitlines():
        if not ln.strip():
            continue
        m = re.match(r"^(..) (.+)$", ln.rstrip("\r\n"))
        if not m:
            continue
        code, path = m.group(1), m.group(2).strip().strip('"')
        if " -> " in path:            # rename/copy: the destination is what exists now
            path = path.split(" -> ", 1)[1].strip().strip('"')
        (untracked if code.strip() == "??" else modified).append(path)
    st.update(head_branch=head_branch, modified=modified, untracked=untracked,
              on_branch=(head_branch == branch), remote=remote)
    return st


# ------------------------------------------------------------------- A: rescue commits
def rescue_commits(repo: str, st: dict, dry: bool, land: bool) -> dict:
    """Push the local branch's unpushed commits to a remote ref. Idempotent."""
    if not st["ahead"]:
        return {"phase": "rescue-commits", "done": True, "action": "none",
                "detail": "no unpushed commits"}
    sha = _out(repo, "rev-parse", st["branch"])
    prefix = "worktree-sync" if land else "rescue"
    ref = f"{prefix}/{st['branch']}-{sha[:7]}" if not land else f"{prefix}-{st['branch']}-{sha[:7]}"
    ls = _out(repo, "ls-remote", "--heads", st["remote"], ref)
    if ls.split() and ls.split()[0] == sha:
        return {"phase": "rescue-commits", "done": True, "action": "already-rescued",
                "ref": ref, "sha": sha[:7], "commits": st["stranded"]}
    if dry:
        return {"phase": "rescue-commits", "done": False, "action": "would-push",
                "ref": ref, "sha": sha[:7], "commits": st["stranded"]}
    _git(repo, "push", st["remote"], f"{sha}:refs/heads/{ref}")
    return {"phase": "rescue-commits", "done": True, "action": "pushed", "ref": ref,
            "sha": sha[:7], "commits": st["stranded"]}


def _remote_tree(repo: str, remote: str, ref: str) -> str | None:
    """The tree of a remote branch's tip, or None if it cannot be established.

    Fetched into a private `refs/valquo/` ref rather than FETCH_HEAD, so this never
    disturbs a scratch ref the user or another tool might be relying on.
    """
    p = _git(repo, "fetch", remote, f"+refs/heads/{ref}:refs/valquo/synccheck",
             check=False)
    if p.returncode != 0:
        return None
    q = _git(repo, "rev-parse", "refs/valquo/synccheck^{tree}", check=False)
    return q.stdout.strip() if q.returncode == 0 else None


# ---------------------------------------------------------------- B: snapshot worktree
def snapshot_worktree(repo: str, st: dict, dry: bool) -> dict:
    """Commit the current TRACKED working-tree state to the remote without touching
    HEAD, the index, or any file on disk.

    Uses a throwaway index (GIT_INDEX_FILE) plus write-tree/commit-tree, so nothing
    the user can see changes. `git stash` is deliberately not used: the stash stack is
    shared across every worktree of this repository and other sessions pop it.

    Untracked files are NOT included -- sweeping up an arbitrary tree would bank
    _to_delete/, .tgz archives and whatever else is lying around. They are reported,
    and the ones that actually block a fast-forward are preserved by quarantine.
    """
    if not st["modified"]:
        return {"phase": "snapshot-worktree", "done": True, "action": "none",
                "detail": "no tracked modifications", "untracked_not_banked": st["untracked"]}
    if dry:
        return {"phase": "snapshot-worktree", "done": False, "action": "would-snapshot",
                "files": st["modified"], "untracked_not_banked": st["untracked"]}

    fd, idx = tempfile.mkstemp(prefix="sync_idx_")
    os.close(fd)
    os.unlink(idx)  # git wants to create it itself
    try:
        env = {"GIT_INDEX_FILE": idx}
        _git(repo, "read-tree", "HEAD", env=env)
        _git(repo, "add", "-u", env=env)          # tracked modifications + deletions only
        tree = _out(repo, "write-tree", env=env)
        head = _out(repo, "rev-parse", "HEAD")
        msg = (f"sync_checkout: working-tree snapshot of {st['branch']} @ {head[:7]}\n\n"
               "Uncommitted tracked changes, banked so they exist somewhere other than\n"
               "one laptop. Nothing on disk was touched to make this commit.\n"
               f"Files: {', '.join(st['modified'])}\n")
        commit = _out(repo, "commit-tree", tree, "-p", head, "-m", msg, env=env)
        ref = f"rescue/wip-{st['branch']}-{tree[:7]}"
        ls = _out(repo, "ls-remote", "--heads", st["remote"], ref)
        if ls.split():
            # Compare TREES, not commits. `commit-tree` stamps a fresh timestamp on every
            # run, so an unchanged working tree still produces a NEW commit sha -- one that
            # is a SIBLING of the one already on the ref, not a descendant. Comparing
            # commits therefore never matches and the push is rejected as a
            # non-fast-forward, which is exactly what the daily task hit on its second run.
            remote_tree = _remote_tree(repo, st["remote"], ref)
            if remote_tree == tree:
                action = "already-snapshotted"
            else:
                # Cannot prove it is the same content, so do not touch the existing ref:
                # push a fresh one rather than fail or force.
                ref = f"{ref}-{commit[:7]}"
                _git(repo, "push", st["remote"], f"{commit}:refs/heads/{ref}")
                action = "pushed"
        else:
            _git(repo, "push", st["remote"], f"{commit}:refs/heads/{ref}")
            action = "pushed"
        return {"phase": "snapshot-worktree", "done": True, "action": action, "ref": ref,
                "tree": tree[:7], "commit": commit[:7], "files": st["modified"],
                "untracked_not_banked": st["untracked"]}
    finally:
        if os.path.exists(idx):
            os.unlink(idx)


# ------------------------------------------------------------------- C: fast-forward
def _quarantine(repo: str, files: list[str], stamp: str) -> list[str]:
    """MOVE blocking untracked files aside. Never deletes; preserves relative paths."""
    moved = []
    for rel in files:
        src = Path(repo) / rel
        if not src.exists():
            continue
        dst = Path(repo) / QUARANTINE / stamp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        moved.append(rel)
    return moved


def fast_forward(repo: str, st: dict, dry: bool) -> dict:
    """Advance the local branch to the remote, when that is a pure fast-forward.

    The collision check is `git merge --ff-only` itself rather than a re-implementation:
    on failure git changes nothing and names the files, which is both the safest
    behaviour and the most accurate list.
    """
    r = {"phase": "fast-forward", "done": False, "quarantined": []}
    if st["ahead"]:
        r.update(action="refused", reason="diverged",
                 detail=f"{st['ahead']} local commit(s) are not on {st['upstream']}; "
                        "a fast-forward is impossible until the branch pointer moves")
        return r
    if not st["behind"]:
        r.update(done=True, action="none", detail="already current")
        return r
    if not st["on_branch"]:
        # Not checked out: update the ref directly. git refuses a non-fast-forward here,
        # so this cannot rewrite history even if the survey were stale.
        if dry:
            r.update(action="would-fetch-ref",
                     detail=f"{st['branch']} is not checked out ({st['head_branch']} is); "
                            f"would move the ref by {st['behind']} commits")
            return r
        _git(repo, "fetch", st["remote"], f"{st['branch']}:{st['branch']}")
        r.update(done=True, action="ref-updated", commits=st["behind"])
        return r
    if dry:
        r.update(action="would-fast-forward", commits=st["behind"],
                 blockers_expected=sorted(set(st["modified"]) | set(st["untracked"])))
        return r

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    for attempt in (1, 2):
        p = _git(repo, "merge", "--ff-only", st["upstream"], check=False)
        if p.returncode == 0:
            r.update(done=True, action="fast-forwarded", commits=st["behind"])
            return r
        msg = ((p.stderr or "") + (p.stdout or ""))
        untracked = _blocked_files(msg, _UNTRACKED_HDR)
        tracked = _blocked_files(msg, _TRACKED_HDR)
        if untracked and attempt == 1:
            r["quarantined"] = _quarantine(repo, untracked, stamp)
            r["quarantine_dir"] = f"{QUARANTINE}/{stamp}"
            continue
        r.update(action="refused",
                 reason="local-changes" if tracked else "merge-refused",
                 blocking_tracked=tracked,
                 detail=msg.strip().splitlines()[0] if msg.strip() else "git refused")
        return r
    r.update(action="refused", reason="still-blocked",
             detail="quarantining the untracked files was not enough")
    return r


# ---------------------------------------------------------------- D: adopt (opt-in)
def adopt_remote(repo: str, st: dict, rescued: dict, snapped: dict, dry: bool) -> dict:
    """Move the local branch pointer to the remote, once the work is provably duplicated.

    The safety is a VERIFICATION, not an assumption: every unpushed commit must be an
    ancestor of the ref this run just pushed, read back from the remote, and every
    tracked modification must be inside the snapshot commit. Without both, it refuses.
    """
    r = {"phase": "adopt-remote", "done": False}
    if not st["ahead"] and not st["modified"]:
        r.update(action="none", detail="nothing to adopt past")
        return r
    if st["ahead"]:
        ref = rescued.get("ref")
        if not ref or rescued.get("action") == "would-push":
            r.update(action="refused", reason="unverified",
                     detail="the local commits have not been pushed anywhere")
            return r
        remote_sha = (_out(repo, "ls-remote", "--heads", st["remote"], ref).split() or [""])[0]
        local_sha = _out(repo, "rev-parse", st["branch"])
        if remote_sha != local_sha:
            r.update(action="refused", reason="unverified",
                     detail=f"{st['remote']}/{ref} is {remote_sha[:7] or 'absent'}, "
                            f"local {st['branch']} is {local_sha[:7]}")
            return r
    if st["modified"] and snapped.get("action") not in ("pushed", "already-snapshotted"):
        r.update(action="refused", reason="unverified",
                 detail=f"{len(st['modified'])} tracked file(s) modified and not snapshotted")
        return r
    if dry:
        r.update(action="would-reset", target=st["upstream"])
        return r
    _git(repo, "reset", "--hard", st["upstream"])
    r.update(done=True, action="reset", target=st["upstream"])
    return r


# ------------------------------------------------------------------------- driver
def run(repo: str = SHARED_CHECKOUT, branch: str = "main", remote: str = "origin",
        dry: bool = False, fetch: bool = True, land: bool = False,
        adopt: bool = False) -> dict:
    st = survey(repo, branch, remote, fetch=fetch)
    phases = [rescue_commits(repo, st, dry, land), snapshot_worktree(repo, st, dry)]
    if adopt:
        phases.append(adopt_remote(repo, st, phases[0], phases[1], dry))
        if phases[-1].get("done"):
            st = survey(repo, branch, remote, fetch=False)
    phases.append(fast_forward(repo, st, dry))
    outstanding = [p for p in phases if not p["done"]]
    return {"repo": repo, "branch": branch, "before": {k: st[k] for k in
            ("head", "ahead", "behind", "head_branch")},
            "modified": st["modified"], "untracked": len(st["untracked"]),
            "dry_run": dry, "phases": phases,
            "outstanding": [p["phase"] for p in outstanding],
            "alarm": bool(outstanding)}


def render(r: dict) -> list[str]:
    o = ["", "=" * 68, "  SYNC SHARED CHECKOUT" + ("  (DRY RUN - nothing changed)" if r["dry_run"] else ""),
         "=" * 68, f"  {r['repo']}",
         f"  {r['branch']} @ {r['before']['head']}   behind {r['before']['behind']}"
         f"   ahead {r['before']['ahead']}"
         f"   ({len(r['modified'])} modified, {r['untracked']} untracked)", ""]
    for p in r["phases"]:
        mark = "OK " if p["done"] else "!! "
        o.append(f"  [{mark}] {p['phase']}: {p.get('action', '?')}")
        for key in ("ref", "detail", "reason", "quarantine_dir", "target"):
            if p.get(key):
                o.append(f"          {key}: {p[key]}")
        for key in ("commits", "files", "blocking_tracked", "quarantined"):
            v = p.get(key)
            if isinstance(v, list) and v:
                for item in v[:8]:
                    o.append(f"            - {item}")
                if len(v) > 8:
                    o.append(f"            ... and {len(v) - 8} more")
            elif isinstance(v, int) and v:
                o.append(f"          {key}: {v}")
    o.append("")
    if not r["alarm"]:
        o += ["  [OK] The checkout is current and nothing is stranded.", ""]
        return o
    o += ["  [ALARM] Not finished: " + ", ".join(r["outstanding"]), ""]
    ff = next((p for p in r["phases"] if p["phase"] == "fast-forward"), {})
    if ff.get("reason") == "diverged":
        o += ["  The work is safe (see the refs above). To finish, once you are happy:",
              "      python scripts/sync_checkout.py --adopt-remote",
              "  That moves the local branch pointer to GitHub's. It refuses unless it has",
              "  just re-read the remote and confirmed every local commit is there.", ""]
    elif ff.get("reason") == "local-changes":
        o += ["  Uncommitted edits block the update. They are banked on the remote already;",
              "  commit or revert them, then run this again.", ""]
    return o


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fast-forward the shared checkout and rescue "
                                             "anything that exists only there.")
    ap.add_argument("--repo", default=SHARED_CHECKOUT)
    ap.add_argument("--branch", default="main")
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--land", action="store_true",
                    help="rescue onto worktree-sync-* so the gate Action lands it, instead "
                         "of rescue/* which is preserved but not merged")
    ap.add_argument("--adopt-remote", action="store_true",
                    help="finish a diverged branch by moving its pointer to the remote, "
                         "after verifying on the remote that nothing is lost")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    try:
        r = run(a.repo, a.branch, a.remote, dry=a.dry_run, fetch=not a.no_fetch,
                land=a.land, adopt=a.adopt_remote)
    except DriftUnknown as e:
        if a.json:
            print(json.dumps({"alarm": True, "unknown": str(e), "repo": a.repo}, indent=1))
        else:
            print(f"\n  [ALARM] Could not sync {a.repo}: {e}")
            print("          Unknown is not the same as fine, so this exits non-zero.\n")
        return ALARM
    print(json.dumps(r, indent=1) if a.json else "\n".join(render(r)))
    return ALARM if r["alarm"] else OK


if __name__ == "__main__":
    sys.exit(main())
