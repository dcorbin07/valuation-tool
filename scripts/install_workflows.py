"""Install the workflow files that ORIGIN/MAIN itself carries -- and nothing else.

Item 85, and it exists because the batch file it replaces chose its source wrongly. The old
`install_workflows.bat` copied `%~dp0pending_workflows\\*.yml` -- the folder the bat happened to
sit in. A copy of that bat sits in every worktree, and on 2026-10-27 one was run from
`.claude\\worktrees\\dipcall\\`, whose pending folder held 10-16/10-17 versions of two live
workflows. Commit `ad29600` installed them over main, deleting 338 lines: every item-74
healthchecks ping and Discord failure notifier from both files, and item 65's per-field summary,
cycle-body artifact and fractional census from `live-cycle.yml`. Nothing raised. The install
reported success, because from the bat's point of view it had done exactly what it was told.

So the source is no longer a parameter of WHERE THE SCRIPT LIVES. It is always the tracked
`pending_workflows/` of the fetched `origin/main`, read inside the temporary worktree this script
creates. There is one authority for what a workflow should contain, and it is reviewable in the
repository -- audit `B7`, the same lesson as every other one-definition repair here.

THE AGE RULE, AND WHY THE OBVIOUS FORM OF IT IS THE WRONG OBJECT. The brief asks this script to
refuse when the file being installed is "older in git history than the one it replaces". Read as
a comparison of the two PATHS' last-touching commits, that rule refuses the repair it was written
to enable: `pending_workflows/fleet-cycle.yml` was last committed 2026-10-20 while
`.github/workflows/fleet-cycle.yml` was last committed by the bad install itself, 2026-10-27. The
defective file is the newer one. A second candidate -- "refuse unless the installed content never
came from the pending path" -- was MEASURED AND REFUTED: the stale lane folder held genuine older
versions of the tracked files, so the bad content sits in the pending path's history too.

What discriminates is POSITION WITHIN THE PENDING PATH'S OWN LINEAGE. Rank every version that
path has ever held, newest first, and compare where each side's content sits. Measured against
the accident:

    fleet-cycle.yml   .github held rank 0, the lane folder offered rank 1  -> BACKWARD, refuse
    live-cycle.yml    .github held rank 0, the lane folder offered rank 3  -> BACKWARD, refuse

That is `ad29600`, refused. And today's repair reads FORWARD on all three files, so one plain run
installs them -- which is the test of a guard worth keeping: it must bite on the event it was
written for and stay out of the way of the fix.

Nothing here prints a key or a token, and nothing reaches an account. It moves YAML.

    python -m scripts.install_workflows           # report only, changes nothing
    python -m scripts.install_workflows --send    # commit the changes and push to main
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

#: The tracked handover directory. Item 58b chose it over the gitignored
#: `data/pending_workflows`, because an untracked file is unreviewable in the repo and unpinnable
#: by any test. This script reads ONLY this one, inside the fetched origin/main.
PENDING_DIR = "pending_workflows"

#: Where the installed copies live.
TARGET_DIR = ".github/workflows"

#: The legacy, gitignored route. **NOT A SOURCE UNLESS EVERY FILE IN IT IS NAMED ON THE COMMAND
#: LINE**, which is the brief's second option and the one this had to take: `scripts/
#: propose_workflow.py` stages into exactly this directory (`PENDING_REL`), so deleting the
#: route outright would break a working mechanism for no gain -- the accident came from
#: `%~dp0pending_workflows`, the TRACKED name read out of a worktree, and not from here. Files
#: left in it without the flag are REPORTED as ignored, because silently skipping them is how
#: someone concludes the install worked while their file went nowhere.
LEGACY_DIR = os.path.join("data", "pending_workflows")

#: A path containing this is a per-lane worktree, never the folder to install from.
WORKTREE_MARKER = os.path.join(".claude", "worktrees")

#: Exit codes. `NOTHING_TO_DO` is its own code rather than 0 so the batch wrapper can skip its
#: "install these?" prompt instead of asking about an empty list -- a prompt that offers to do
#: nothing teaches the reader to answer it without looking.
OK = 0
NOTHING_TO_DO = 4
REFUSED = 2
PUSH_FAILED = 3


class GitError(RuntimeError):
    pass


class Git(object):
    """The few git reads and writes this script needs, against one repository."""

    def __init__(self, root):
        self.root = root

    def __call__(self, *args, **kw):
        check = kw.pop("check", False)
        out = subprocess.run(["git", "-C", self.root] + list(args), capture_output=True)
        if check and out.returncode != 0:
            raise GitError("git %s failed: %s"
                           % (" ".join(args), out.stderr.decode("utf-8", "replace").strip()))
        if out.returncode != 0:
            return None
        return out.stdout.decode("utf-8", "replace").strip()

    def blob(self, ref, path):
        """The object id of `path` at `ref`, or None when the path is absent there."""
        return self("rev-parse", "%s:%s" % (ref, path))

    def bytes_at(self, ref, path):
        out = subprocess.run(["git", "-C", self.root, "show", "%s:%s" % (ref, path)],
                             capture_output=True)
        return out.stdout if out.returncode == 0 else None


def _comparable(path):
    """A path flattened so the comparison means the same thing on every platform.

    **`os.path.normcase` IS A NO-OP ON POSIX AND THAT FAILED THE LAND.** The first cut compared
    `normcase(normpath(abspath(x)))` against `normcase(WORKTREE_MARKER)`, which is right on
    Windows -- where the installer actually runs -- and wrong on the Linux runner, where
    `normcase` neither lowercases nor touches separators, so `.CLAUDE\\Worktrees` did not match
    `.claude/worktrees` and the case test went red. `MB42`'s family, which this project has
    already paid for once: a path comparison that behaves differently under `ntpath` and
    `posixpath` is a guard whose real execution is the one nobody tested.

    So the flattening is explicit: backslashes to forward slashes, then lowercase. A guard
    protecting a Windows folder layout has to give the same answer wherever it is asserted.
    """
    return path.replace("\\", "/").lower()


def refuse_reason(script_dir):
    """Why this script must not run from `script_dir`, or None when it may.

    The one refusal that would have prevented `ad29600` outright. Keyed on the path rather than on
    anything inside the folder, because a lane worktree is a complete checkout and looks exactly
    like the real thing from the inside.
    """
    # **NO `abspath` HERE, AND THAT IS THE SECOND HALF OF THE SAME LESSON.** Resolving the input
    # against the current directory makes the answer depend on where the suite happens to be
    # run: under `posixpath` a Windows-absolute path like `C:/Users/...` is RELATIVE, so
    # `abspath` prepends the cwd -- and running the tests from inside a worktree then made this
    # guard refuse an ordinary folder, i.e. the positive control inverted. Measured, not
    # imagined. `main` resolves its own path before calling; the comparison itself is pure.
    if _comparable(WORKTREE_MARKER) in _comparable(script_dir):
        return ("this is a lane worktree (%s), and a worktree carries its own stale copy of the "
                "handover folder -- run the installer from your main Valquo folder" % script_dir)
    return None


def classify(pending, installed):
    """NEW, CHANGED or unchanged -- compared on BYTES, which is what gets committed."""
    if installed is None:
        return "NEW"
    if pending == installed:
        return "unchanged"
    return "CHANGED"


def pending_lineage(git, name, ref="origin/main"):
    """Every version the tracked pending copy has ever held: {blob id: (rank, "sha date")}.

    Rank 0 is the most recent. `--all` rather than one ref, so a version that landed on a branch
    still counts as having existed -- the stale lane folders are full of exactly those.
    """
    rel = "%s/%s" % (PENDING_DIR, name)
    revs = (git("log", "--all", "--format=%H", "--", rel) or "").split()
    out = {}
    for rev in revs:
        blob = git("rev-parse", "%s:%s" % (rev, rel))
        if blob and blob not in out:
            out[blob] = (len(out), git("log", "-1", "--format=%h %ci", rev) or rev[:12])
    return out


def direction(lineage, pending_blob, installed_blob):
    """FORWARD, no-op, BACKWARD or UNKNOWN, by position in the pending path's own lineage.

    UNKNOWN means the installed content is not any version this pending path has held, i.e.
    `.github` was changed by something other than this handover. That is refused too: the point
    of the handover is that nothing else writes there.
    """
    if installed_blob is None:
        return "FORWARD"
    if pending_blob == installed_blob:
        return "no-op"
    here = lineage.get(pending_blob)
    there = lineage.get(installed_blob)
    if here is None or there is None:
        return "UNKNOWN"
    if here[0] < there[0]:
        return "FORWARD"
    if here[0] == there[0]:
        return "no-op"
    return "BACKWARD"


def plan(git, worktree, ref="origin/main"):
    """One row per tracked pending workflow: what it is, and whether it may be installed.

    The WORKTREE supplies only the LIST of names (and later the bytes to copy). Both sides of
    every comparison are read from `ref` through git, and that is not fussiness: read from disk,
    the pending copy carries CRLF after a Windows checkout while its blob holds LF, so comparing
    disk against blob reported SIX files CHANGED that were byte-identical in the repository --
    found by running this and disbelieving a table that said `CHANGED` and `no-op` on one row.
    An installer whose report is wrong about what it is about to do is the defect this item is
    already about, one level down.
    """
    src = os.path.join(worktree, PENDING_DIR)
    rows = []
    if not os.path.isdir(src):
        return rows
    for name in sorted(f for f in os.listdir(src) if f.endswith(".yml")):
        pending = git.bytes_at(ref, "%s/%s" % (PENDING_DIR, name))
        installed = git.bytes_at(ref, "%s/%s" % (TARGET_DIR, name))
        state = classify(pending, installed)
        if state == "unchanged":
            rows.append({"name": name, "state": state, "direction": "no-op",
                         "note": "", "ok": True})
            continue
        lineage = pending_lineage(git, name, ref=ref)
        pending_blob = git.blob(ref, "%s/%s" % (PENDING_DIR, name))
        installed_blob = git.blob(ref, "%s/%s" % (TARGET_DIR, name))
        way = direction(lineage, pending_blob, installed_blob)
        note = ""
        if way == "BACKWARD":
            note = ("what is on main is NEWER than this (%s) -- refusing"
                    % lineage.get(installed_blob, (0, "?"))[1])
        elif way == "UNKNOWN":
            note = ("what is on main did not come from this handover folder, so something else "
                    "wrote .github/workflows -- refusing")
        rows.append({"name": name, "state": state, "direction": way, "note": note,
                     "ok": way in ("FORWARD", "no-op")})
    return rows


def legacy_leftovers(repo_root):
    """Any .yml sitting in the gitignored route, which is read only when every one is named."""
    d = os.path.join(repo_root, LEGACY_DIR)
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d) if f.endswith(".yml"))


def legacy_confirmed(present, named):
    """The typed confirmation, or a reason it is refused.

    Returns `(ok, reason)`. **EVERY file present must be named**, not merely a subset: confirming
    two of three and having the third install anyway is the same class of surprise as the whole
    item, and confirming two and having the third silently skipped is the other half of it. The
    operator has to have looked at the directory.
    """
    present, named = sorted(present), sorted(named)
    if not named:
        return False, "not confirmed"
    if present != named:
        extra = [n for n in named if n not in present]
        missed = [n for n in present if n not in named]
        bits = []
        if missed:
            bits.append("not named: %s" % ", ".join(missed))
        if extra:
            bits.append("named but not present: %s" % ", ".join(extra))
        return False, "the confirmation does not match the directory (%s)" % "; ".join(bits)
    return True, "confirmed by hand: %s" % ", ".join(named)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--send", action="store_true",
                    help="commit the changes and push them to main")
    ap.add_argument("--repo", default=None, help="repository root (default: this script's repo)")
    ap.add_argument("--legacy-confirm", nargs="+", metavar="FILE", default=(),
                    help="also install these files from the gitignored data/pending_workflows; "
                         "every .yml in that directory must be named")
    args = ap.parse_args(argv)

    # Resolved HERE rather than inside `refuse_reason`, so the guard itself has no hidden
    # dependence on the current directory.
    repo_root = os.path.abspath(
        args.repo or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    why = refuse_reason(repo_root)
    if why:
        print("REFUSED: %s" % why)
        return REFUSED

    git = Git(repo_root)
    print("Fetching the newest main from GitHub...")
    if git("fetch", "-q", "origin", "main") is None:
        print("REFUSED: could not reach GitHub, so the newest main is unknown.")
        return REFUSED

    left = legacy_leftovers(repo_root)
    legacy_ok, legacy_why = legacy_confirmed(left, args.legacy_confirm) if left else (False, "")
    if left:
        print()
        if legacy_ok:
            print("LEGACY ROUTE: %s" % legacy_why)
            print("      from %s -- no lineage check applies to these, so the confirmation"
                  % LEGACY_DIR)
            print("      above is the only thing standing in for it.")
        else:
            print("NOTE: %d file(s) in %s are IGNORED (%s)."
                  % (len(left), LEGACY_DIR, legacy_why))
            print("      The installer reads the tracked %s/ of origin/main. To install these"
                  % PENDING_DIR)
            print("      as well, name every one of them:")
            print("        python -m scripts.install_workflows --send --legacy-confirm %s"
                  % " ".join(left))

    worktree = tempfile.mkdtemp(prefix="valquo_install_wf_")
    os.rmdir(worktree)
    try:
        if git("worktree", "add", "-q", "--detach", worktree, "origin/main") is None:
            print("REFUSED: could not check out origin/main.")
            return REFUSED

        rows = plan(git, worktree)
        if not rows and not (legacy_ok and left):
            print("Nothing to install: origin/main carries no %s/*.yml." % PENDING_DIR)
            return NOTHING_TO_DO

        print()
        print("  %-22s %-10s %-9s %s" % ("file", "state", "move", "note"))
        for r in rows:
            print("  %-22s %-10s %-9s %s" % (r["name"], r["state"], r["direction"], r["note"]))

        refused = [r for r in rows if not r["ok"]]
        todo = [r for r in rows if r["ok"] and r["state"] != "unchanged"]
        print()
        if refused:
            print("REFUSED: %d file(s) would go backwards, or came from outside this handover."
                  % len(refused))
            print("Nothing was installed. Fix %s/ on main first." % PENDING_DIR)
            return REFUSED
        if not todo and not (legacy_ok and left):
            print("Already installed on main -- nothing to change.")
            return NOTHING_TO_DO
        legacy = list(left) if legacy_ok else []
        print("To install: %s" % ", ".join([r["name"] for r in todo] + legacy))
        if not args.send:
            print("Report only. Re-run with --send to install.")
            return OK

        # **THE ORDER IS THE GUARANTEE, AND MY FIRST CUT HAD IT BACKWARDS.** `test_item74`'s
        # `test_ONE_INSTALL_LEAVES_EXACTLY_ONE_COPY_OF_EACH` pins that a name present in BOTH
        # directories ends up as one file carrying the TRACKED content, and it caught this: I
        # copied the tracked files first and the legacy ones after, so the gitignored copy won.
        # The legacy route goes first and the tracked one last, exactly as the bat did.
        clash = sorted(set(legacy) & {r["name"] for r in todo})
        for name in legacy:
            shutil.copy2(os.path.join(repo_root, LEGACY_DIR, name),
                         os.path.join(worktree, TARGET_DIR, name))
        for r in todo:
            shutil.copy2(os.path.join(worktree, PENDING_DIR, r["name"]),
                         os.path.join(worktree, TARGET_DIR, r["name"]))
        if clash:
            print("NOTE: %s exist in both handover folders; the TRACKED copy is what installs."
                  % ", ".join(clash))
        wt = Git(worktree)
        wt("add", TARGET_DIR, check=True)
        if wt("diff", "--cached", "--quiet") is not None:
            print("Already installed on main -- nothing to change.")
            return NOTHING_TO_DO
        names = " ".join([r["name"] for r in todo] + legacy)
        # The message names its SOURCE, because the whole item is about an install whose source
        # nobody could tell from the record it left behind.
        source = "main's own pending_workflows"
        if legacy:
            source += " plus %d hand-confirmed legacy file(s)" % len(legacy)
        wt("commit", "-q", "-m",
           "Install workflow(s): %s (from %s)" % (names, source), check=True)
        if wt("push", "-q", "origin", "HEAD:main") is None:
            print("Main moved while this ran -- retrying once on top of the newest main...")
            wt("pull", "-q", "--rebase", "origin", "main")
            if wt("push", "-q", "origin", "HEAD:main") is None:
                print("PUSH FAILED. Nothing reached GitHub.")
                return PUSH_FAILED
        print()
        print("INSTALLED on main: %s" % names)
    finally:
        git("worktree", "remove", "--force", worktree)
    return OK


if __name__ == "__main__":
    sys.exit(main())
