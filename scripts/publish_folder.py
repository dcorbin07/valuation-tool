# -*- coding: utf-8 -*-
"""ITEM 43 - publish THIS FOLDER's own edits to GitHub, in an order that cannot diverge.

THE DEFECT, REPRODUCED ON A REAL TEMPORARY REPO BEFORE IT WAS REPAIRED. The one sequence Don
runs every day - he has edits, lanes have landed - produced a divergence nothing he runs could
cure:

  1. the folder has uncommitted edits to TRACKED files the remote also changed (on 2026-10-08:
     `DECISIONS.md` and the `PROMPT_*` files, which `517cf0b` had touched on main);
  2. `git_push.bat` ran `sync_checkout.py` FIRST, which correctly REFUSES a fast-forward that
     would overwrite them, parking a copy on `rescue/wip-*`;
  3. it then `git add -A` and committed those edits **on top of stale main**;
  4. main was now **ahead 1 / behind 1 - DIVERGED** - and `git push` was rejected as a
     non-fast-forward;
  5. `sync.bat` refuses a diverged branch BY DESIGN, so the cure was not available either.

Measured exactly that way: `ahead 1 / behind 1`, `! [rejected] main -> main
(non-fast-forward)`, second sync `[!! ] fast-forward: refused / reason: diverged`.

**THE ORDER WAS THE WHOLE BUG.** Every step was individually correct and defensible - the sync
is right to refuse, the commit is right to happen, the push is right to be rejected. Committing
BEFORE the fetch is what makes a divergence out of two things that were merely out of step.

THE ORDER THIS USES, AND WHY EACH STEP IS WHERE IT IS:

  1. **COMMIT FIRST.** A clean tree is what lets the fetch and the replay proceed at all; a
     dirty one forces every later step to choose between refusing and overwriting.
  2. **FETCH.**
  3. **BEHIND ONLY -> fast-forward.** Nothing of ours to replay.
  4. **DIVERGED -> REBASE our commits onto the remote.** This is the step that was missing.
     It replays only the commits that exist solely here, which is exactly what the folder owns.
  5. **PUSH**, which is now a fast-forward by construction rather than by luck.

EVERY EXISTING GUARANTEE IS KEPT, and each is a line of code rather than an intention:

  * **TESTS BEFORE PUSH / NEVER PUSH RED** - `git_push.bat` still runs the suite and only calls
    this on green. This module also refuses to run without `--tests-passed`, so a future caller
    cannot reach the push by forgetting.
  * **AGENT BRANCHES ARE NEVER MERGED LOCALLY** - this touches `branch` and `remote/branch` and
    nothing else. No `worktree-*` ref is read, merged or deleted. Pinned by test.
  * **NOTHING IS DISCARDED** - the pre-rebase tip is saved to a local backup ref BEFORE the
    rebase, and a conflict runs `rebase --abort` and reports. The backup is reported by name so
    recovery is a copy-paste rather than an archaeology exercise.
  * **`.env` AND `data/` ARE NEVER COMMITTED** - checked against what is actually STAGED, after
    `add -A`, which is the only moment the answer is knowable.

`rebase_push.bat` IS REMOVED RATHER THAN DOCUMENTED, and that is a decision the brief asks for.
Its logic (fetch, rebase, abort on conflict, push) is correct and is now step 4 of the normal
path. Keeping it as well would be a SECOND implementation of one cure - audit `B7`'s shape, the
defect this project has paid for most - and the second copy is the one that drifts. There is
nothing left for it to recover from: the state it cured can no longer be reached.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.checkout_drift import DriftUnknown, _git, measure        # noqa: E402

OK, FAILED = 0, 1


def _run(repo: str, *args: str) -> tuple[int, str]:
    """A git call that is ALLOWED to fail, with its output.

    `checkout_drift._git` raises on non-zero, which is right for an alarm and wrong for the
    two calls here whose failure is a legitimate OUTCOME rather than a fault -- the rebase
    (conflict) and the push (someone landed a second ago). That module is deliberately NOT
    given a `check=` flag: it is another lane's alarm, and widening a shared primitive to
    suit one new caller is how a guard acquires a mode nobody tests.

    Bytes are decoded here with `errors="replace"` rather than by `text=True`. On Windows
    `text=True` reads git's output as cp1252, so a conflict message carrying a non-ASCII
    filename or an em-dash raises mid-failure -- a crash inside the branch whose whole job is
    to report a failure calmly. The decoding feeds the human-readable report only; the verdict
    is the return code.
    """
    p = subprocess.run(["git", *args], cwd=repo, capture_output=True, timeout=600)
    out = ((p.stdout or b"").decode("utf-8", "replace")
           + (p.stderr or b"").decode("utf-8", "replace"))
    return p.returncode, out.strip()


def _staged(repo: str) -> list[str]:
    out = _git(repo, "diff", "--cached", "--name-only")
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def _blocked(paths: list[str]) -> list[str]:
    """Paths that must never be committed, whatever `git add -A` picked up.

    `.gitignore` already covers these, so this is the belt to that braces -- and it is the one
    that matters, because a `git add -f` or a stale index entry defeats the ignore file while
    this reads what is actually STAGED. ONE definition; nothing else in this module names them.
    """
    bad = []
    for p in paths:
        q = p.replace("\\", "/")
        # `.lstrip("./")` was the first cut and it is a REAL defect, caught by this module's
        # own test: lstrip takes a SET OF CHARACTERS, not a prefix, so ".env" came back as
        # "env" and the one guard standing between a secret and a public remote matched
        # nothing. Strip the prefix as a prefix.
        while q.startswith("./"):
            q = q[2:]
        if q == ".env" or q.startswith(".env.") or q.startswith("data/"):
            bad.append(p)
    return bad


def _dirty(repo: str) -> bool:
    return bool(_git(repo, "status", "--porcelain").strip())


def publish(repo: str, remote: str = "origin", branch: str = "main",
            dry: bool = False, stamp: str | None = None) -> dict:
    """Commit, fetch, replay, push. Returns a step-by-step record; never raises for a conflict.

    `stamp` is injectable so a test can assert the commit message without depending on the
    clock -- `Date.now()`-shaped non-determinism in a tested path is how a suite becomes
    flaky at midnight.
    """
    steps: list[dict] = []
    rec = {"repo": repo, "branch": branch, "remote": remote, "steps": steps,
           "pushed": False, "failed": None, "backup": None}

    def step(name, **kw):
        steps.append({"step": name, **kw})
        return steps[-1]

    head_branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if head_branch != branch:
        # REFUSED, NOT SWITCHED. Checking out `main` under someone who is deliberately on
        # another branch is the kind of help that loses work.
        step("on-branch", ok=False, head=head_branch, want=branch)
        rec["failed"] = ("this folder is on %r, not %r -- publishing from here would move the "
                         "wrong branch" % (head_branch, branch))
        return rec
    step("on-branch", ok=True, head=head_branch)

    # ---------------------------------------------------------------- 1. commit FIRST --------
    if _dirty(repo):
        if dry:
            step("commit", ok=True, action="would-commit")
        else:
            _git(repo, "add", "-A")
            blocked = _blocked(_staged(repo))
            if blocked:
                # UNSTAGED, NOT COMMITTED-THEN-FIXED. A secret in a commit is in the history
                # even if the next commit removes it, and this folder pushes to a public remote.
                _git(repo, "reset", "-q")
                step("commit", ok=False, blocked=blocked)
                rec["failed"] = ("refusing to commit files that must never be pushed: %s"
                                 % ", ".join(blocked))
                return rec
            if _git(repo, "diff", "--cached", "--name-only").strip():
                msg = "Update %s" % (stamp or datetime.now().strftime("%Y-%m-%d %H:%M"))
                _git(repo, "commit", "-q", "-m", msg)
                step("commit", ok=True, action="committed", message=msg)
            else:
                step("commit", ok=True, action="nothing-to-stage")
    else:
        step("commit", ok=True, action="clean")

    # ---------------------------------------------------------------- 2. fetch ---------------
    try:
        # A DRY RUN STILL FETCHES, and that was a defect in the first cut found by its own
        # test: with `fetch=False` it read a stale remote-tracking ref, reported "in step" and
        # so could not name the step it would actually take -- a preview that previews nothing.
        # The fetch is the one write a dry run makes, it touches only a remote-tracking ref,
        # and `measure` never prunes.
        st = measure(repo, remote, branch, fetch=True)
    except DriftUnknown as e:
        step("fetch", ok=False, error=str(e))
        rec["failed"] = "could not read GitHub: %s" % e
        return rec
    ahead, behind = st["ahead"], st["behind"]
    # A DRY RUN HAS NOT COMMITTED, SO IT MUST COUNT THE COMMIT IT WOULD HAVE MADE. The first
    # cut did not, so on the exact state this item is about -- dirty and one behind -- it
    # previewed "would fast-forward" for a run that will rebase. A preview of the wrong branch
    # of the code is worse than no preview, because it is believed.
    if dry and any(s["step"] == "commit" and s.get("action") == "would-commit"
                   for s in steps):
        ahead += 1
    step("fetch", ok=True, ahead=ahead, behind=behind)

    # ---------------------------------------------------------------- 3/4. align -------------
    if behind and not ahead:
        if dry:
            step("fast-forward", ok=True, action="would-fast-forward", commits=behind)
        else:
            # REPORTED, NOT RAISED. The tree is clean by now, so the only way a fast-forward
            # can still be refused is a file git does not track here -- a `.gitignore`d or
            # untracked path that the incoming commit adds as tracked. Rare, and `_git` would
            # turn it into an exception out of the middle of Don's daily tool.
            rc, out = _run(repo, "merge", "--ff-only", "%s/%s" % (remote, branch))
            if rc != 0:
                step("fast-forward", ok=False, commits=behind, detail=out.splitlines()[:4])
                rec["failed"] = ("GitHub's latest adds a file this folder already has but does "
                                 "not track, so catching up would overwrite it. Nothing was "
                                 "changed. Move or delete the file git named above, then run "
                                 "this again.")
                return rec
            step("fast-forward", ok=True, action="fast-forwarded", commits=behind)
    elif ahead and behind:
        backup = "backup/%s-%s" % (branch, _git(repo, "rev-parse", "--short", "HEAD"))
        if dry:
            step("rebase", ok=True, action="would-rebase", ours=ahead, theirs=behind,
                 backup=backup)
        else:
            # THE TIP IS SAVED BEFORE ANYTHING MOVES. `rebase --abort` restores it anyway and
            # the reflog would hold it for 90 days -- but "nothing is discarded" should be a
            # ref somebody can read, not a property of a command's failure path.
            _git(repo, "branch", "-f", backup, "HEAD")
            rec["backup"] = backup
            rc, out = _run(repo, "rebase", "%s/%s" % (remote, branch))
            if rc != 0:
                _run(repo, "rebase", "--abort")
                step("rebase", ok=False, action="aborted", ours=ahead, theirs=behind,
                     backup=backup, detail=out.splitlines()[:4])
                rec["failed"] = (
                    "your edits and GitHub's changed the same lines, so the replay was undone "
                    "and NOTHING was lost. Your commits are still here and also on %r. Open "
                    "the files git named above, keep the version you want, then run this "
                    "again." % backup)
                return rec
            step("rebase", ok=True, action="rebased", ours=ahead, theirs=behind, backup=backup)
    elif ahead:
        step("align", ok=True, action="already-on-top", ours=ahead)
    else:
        step("align", ok=True, action="in-step")

    # ---------------------------------------------------------------- 5. push ----------------
    outstanding = int(_git(repo, "rev-list", "--count",
                           "%s/%s..HEAD" % (remote, branch)) or 0)
    if not outstanding:
        step("push", ok=True, action="nothing-to-push")
        rec["pushed"] = True
        return rec
    if dry:
        step("push", ok=True, action="would-push", commits=outstanding)
        rec["pushed"] = True
        return rec
    rc, out = _run(repo, "push", remote, "HEAD:%s" % branch)
    if rc != 0:
        step("push", ok=False, commits=outstanding, detail=out.splitlines()[:4])
        rec["failed"] = ("the push was rejected even after replaying. Someone landed again in "
                         "the last few seconds -- run this once more.")
        return rec
    step("push", ok=True, action="pushed", commits=outstanding)
    rec["pushed"] = True
    return rec


def render(rec: dict) -> list[str]:
    """The exact sequence Don should expect to see printed."""
    out = ["", "  PUBLISHING THIS FOLDER'S EDITS", "  " + "-" * 56]
    label = {"on-branch": "on the right branch", "commit": "saving your edits",
             "fetch": "checking GitHub", "fast-forward": "catching up to GitHub",
             "rebase": "replaying your edits on top of GitHub", "align": "already in step",
             "push": "pushing"}
    for s in rec["steps"]:
        mark = "[OK ]" if s.get("ok") else "[!! ]"
        bits = [("%s=%s" % (k, v)) for k, v in s.items()
                if k not in ("step", "ok", "detail")]
        out.append("  %s %-38s %s" % (mark, label.get(s["step"], s["step"]),
                                      " ".join(bits)))
        for ln in (s.get("detail") or []):
            out.append("         | %s" % str(ln)[:92])
    if rec["failed"]:
        out += ["", "  [!] %s" % rec["failed"]]
        if rec.get("backup"):
            out.append("      Your own commits are also saved on the local branch %r."
                       % rec["backup"])
    elif rec["pushed"]:
        out += ["", "  [OK] GitHub is up to date."]
    out.append("")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Commit, replay and push this folder's own edits.")
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stamp", default=None)
    ap.add_argument("--tests-passed", action="store_true",
                    help="the caller has run the suite and it is green. REQUIRED: 'never push "
                         "red' must be a condition of entry rather than a habit of the one "
                         "caller that currently remembers.")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if not a.tests_passed and not a.dry_run:
        print("\n  [!] refusing to publish without --tests-passed. Run the suite first "
              "(git_push.bat does).\n")
        return FAILED
    try:
        rec = publish(a.repo, a.remote, a.branch, dry=a.dry_run, stamp=a.stamp)
    except DriftUnknown as e:
        print("\n  [!] could not publish: %s\n" % e)
        return FAILED
    if a.json:
        import json
        print(json.dumps(rec, indent=1))
    else:
        print("\n".join(render(rec)))
    return OK if (rec["pushed"] and not rec["failed"]) else FAILED


if __name__ == "__main__":
    sys.exit(main())
