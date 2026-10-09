# -*- coding: utf-8 -*-
"""ITEM 44 - the one authoritative reader for a `.github/workflows/` file.

THE DEFECT THIS EXISTS FOR, AND IT IS A STRUCTURAL GUARANTEE RATHER THAN BAD LUCK. Item 42
reported that `auto-scan.yml` "still has no `53 17-19` cron, so the backup has run zero days".
**It had carried it since `d66155e`, installed 2026-10-08 08:15 ET.** The lane read the copy in
its own worktree, which was branched before that commit.

That is not a one-off slip, and this is the part worth keeping: **the land gate REFUSES any
branch that touches `.github/`** (`land_policy.py`), so a workflow file can only ever change on
`main`, by Don running `install_workflows.bat`. A lane therefore cannot have made the change
itself, cannot land it, and has no reason for its own copy to be current -- so **for `.github/`
specifically, a lane's local copy is NEVER authoritative, and reading it to make a claim about
what GitHub is scheduling is wrong by construction rather than by accident.**

So this module reads `origin/main`'s copy, and when it cannot it says so instead of quietly
substituting the local one. `valquo_sync_bootstrap.bat` already applies exactly this reasoning
one level up -- it fetches `scripts/sync_checkout.py` from `origin/main` rather than running the
folder's copy, because "a launcher that ran this folder's copy would be as stale as the folder".

WHY `read()` RETURNS THE SOURCE ALONGSIDE THE TEXT. A helper that silently fell back to the
local file would reproduce the original defect with an extra layer of indirection: the caller
would believe it had the authoritative copy. Every caller gets told which copy it is holding,
and `authoritative` is a boolean it has to look at.
"""
from __future__ import annotations

import io
import os
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW_DIR = os.path.join(".github", "workflows")

#: Where a lane's proposed workflow waits for Don. Not authoritative for anything live -- it is
#: a PROPOSAL, and conflating the two is how a check ends up asserting against a file GitHub has
#: never seen.
PENDING_DIR = os.path.join("data", "pending_workflows")


def _git(*args: str, timeout: int = 60):
    try:
        p = subprocess.run(["git", *args], cwd=REPO, capture_output=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired, NotADirectoryError):
        return None
    if p.returncode != 0:
        return None
    return (p.stdout or b"").decode("utf-8", "replace")


def local_path(name: str) -> str:
    return os.path.join(REPO, WORKFLOW_DIR, name)


def read(name: str, ref: str = "origin/main") -> dict:
    """The authoritative text of a workflow, with its provenance.

    Returns `{"name", "text", "source", "authoritative", "local_text", "differs", "reason"}`.

    `source` is `"origin/main"` when the ref could be read and `"local"` otherwise, and
    `authoritative` is True only in the first case. A caller that ignores `authoritative` is
    making item 42's mistake again -- which is why `differs` is computed too: even on the
    fallback path, a local copy that disagrees with the ref is reported.
    """
    rel = "%s/%s" % (WORKFLOW_DIR.replace(os.sep, "/"), name)
    text = _git("show", "%s:%s" % (ref, rel))

    lp = local_path(name)
    local_text = None
    if os.path.exists(lp):
        local_text = io.open(lp, encoding="utf-8", errors="replace").read()

    if text is None:
        return {"name": name, "text": local_text, "source": "local",
                "authoritative": False, "local_text": local_text, "differs": None,
                "reason": "could not read %s:%s (no remote ref, offline, or not a repo) -- "
                          "this is the LOCAL copy and a lane's local copy of a .github file is "
                          "never authoritative" % (ref, rel)}

    differs = (local_text is not None and local_text != text)
    return {"name": name, "text": text, "source": ref, "authoritative": True,
            "local_text": local_text, "differs": differs,
            "reason": ("the local copy DIFFERS from %s -- read the ref, not the file" % ref)
                      if differs else ""}


def strip_comments(text: str) -> str:
    """YAML with `#` comments removed, quotes respected.

    Hand-rolled rather than `yaml.safe_load`: **PyYAML is not installed in CI**, which item 37
    found the expensive way -- a `yaml.safe_load` in a test took the land gate red with
    `ModuleNotFoundError`. A `skipUnless` would have turned the gate green and left the check
    silently absent, which is worse than the failure.
    """
    out = []
    for line in text.splitlines():
        q = None
        cut = None
        for i, ch in enumerate(line):
            if q:
                if ch == q:
                    q = None
            elif ch in "\"'":
                q = ch
            elif ch == "#":
                cut = i
                break
        out.append(line if cut is None else line[:cut])
    return "\n".join(out)


def crons(text: str) -> list:
    """Every `- cron: "..."` in the file, in order, comments stripped."""
    import re
    return re.findall(r'-\s*cron:\s*["\']([^"\']+)["\']', strip_comments(text))


def main(argv=None) -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="Read a workflow from the ref that runs it.")
    ap.add_argument("name", nargs="?", default="auto-scan.yml")
    ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    got = read(a.name, a.ref)
    if a.json:
        print(json.dumps({k: v for k, v in got.items()
                          if k not in ("text", "local_text")}
                         | {"crons": crons(got["text"] or "")}, indent=1))
        return 0
    print("")
    print("  %s" % a.name)
    print("  source        : %s" % got["source"])
    print("  authoritative : %s" % got["authoritative"])
    if got["differs"]:
        print("  [!] %s" % got["reason"])
    elif not got["authoritative"]:
        print("  [!] %s" % got["reason"])
    for c in crons(got["text"] or ""):
        print("      cron %s" % c)
    print("")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
