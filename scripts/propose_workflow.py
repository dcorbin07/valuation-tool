# -*- coding: utf-8 -*-
"""ITEM 44 - put a proposed workflow where `install_workflows.bat` will find it.

WHY THE TRACKED COPY LIVES IN `scripts/workflows/` AND NOT IN `data/pending_workflows/`.
`.github/` is refused to lanes by the land gate, so a workflow reaches `main` only through
`data/pending_workflows/<name>.yml` plus `install_workflows.bat` (DECISIONS 2026-10-04). But
**`/data/` is gitignored** (`.gitignore:33`) and `publish_folder._blocked` refuses to commit
anything under it, deliberately -- so **the pending `.yml` can never be the tracked copy of
itself**, and a lane that wrote only into its own worktree's `data/` would produce a file that
dies with the worktree. That stranded-artifact failure is on this project's record twice
(`MA28_CARD.json`, `I2_BURN_IN_CENSUS.json`).

So the tracked original sits in `scripts/workflows/`, which is an ordinary reviewable path, and
this copies it into the pending directory. **One definition** (`B7`): the tracked file is the
text, the pending copy is a deployment of it, and the tests read the tracked one -- which also
means they do not SKIP on a CI runner, where `data/` is empty. A suite that skips because its
subject is absent is a vacuous pass, and this proposal carries a token with real trading rights
behind it.

    python scripts/propose_workflow.py --list
    python scripts/propose_workflow.py tradier-seam.yml
    python scripts/propose_workflow.py tradier-seam.yml --root "C:\\Users\\donni\\Downloads\\valuation-tool"
"""
from __future__ import annotations

import argparse
import io
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(REPO, "scripts", "workflows")
PENDING_REL = os.path.join("data", "pending_workflows")


def available() -> list:
    if not os.path.isdir(SOURCE_DIR):
        return []
    return sorted(f for f in os.listdir(SOURCE_DIR) if f.endswith((".yml", ".yaml")))


def read(name: str) -> str:
    """The tracked text of a proposed workflow. Raises rather than returning empty."""
    path = os.path.join(SOURCE_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError("no proposed workflow %r in scripts/workflows/" % name)
    text = io.open(path, encoding="utf-8").read()
    if not text.strip():
        raise ValueError("%s is empty; refusing to propose a blank workflow" % name)
    return text


def place(name: str, root: str) -> str:
    """Copy the tracked proposal into `<root>/data/pending_workflows/`."""
    text = read(name)
    d = os.path.join(root, PENDING_REL)
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, name)
    # LF forced: a file whose line endings depend on which machine wrote it makes every later
    # diff unreadable, and GitHub Actions reads either.
    with io.open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Stage a proposed workflow for installation.")
    ap.add_argument("name", nargs="?")
    ap.add_argument("--root", default=REPO,
                    help="the checkout whose data/pending_workflows/ to write into")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)

    if a.list or not a.name:
        print("")
        print("  proposed workflows in scripts/workflows/:")
        for f in available() or ["(none)"]:
            print("    %s" % f)
        print("")
        return 0

    out = place(a.name, a.root)
    print("")
    print("  staged %s" % out)
    print("")
    print("  Next, two steps and one click:")
    print("    1. double-click install_workflows.bat")
    print("    2. GitHub -> Actions -> the workflow's name -> Run workflow")
    print("")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
