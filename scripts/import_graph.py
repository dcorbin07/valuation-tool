#!/usr/bin/env python3
"""
import_graph.py -- the project's import graph, DERIVED rather than typed.

    python scripts/import_graph.py                 # summary
    python scripts/import_graph.py --unreachable   # modules no entry point reaches
    python scripts/import_graph.py --importers valuation/edge/statistics.py

Why this module exists (master audit MA59 + MA60, 2026-08-15).

MA60's third bullet: `check_lanes.py` decided whether two audit items could run
in parallel using a HAND-TYPED dict of import edges, and the audit's charge was
that it had "admitted gaps". Measured, the charge understates it -- the dict
held 13 keys and 40 edges against a real 118 keys and 546 edges, 105 files with
real imports were absent from it entirely, and 12 of its 13 keys were wrong.
Worse than absent, it was wrong in a direction that reads as safe: four options
modules were recorded as importing `statistics.py` when they actually import
`options_stats.py`, so a SOFT collision between two options items fired against
a file they do not share and never fired against the file they do.

MA59's list of dead modules rests on the same computation from the other end:
"nothing reaches it" is a statement about the graph. Deriving it once means the
quarantine proof and the lane checker cannot drift apart -- which is exactly
the defect MA39 found (one list in the module that PRODUCES the blocks, a
second copy in the module that SCANS them, and a later change made to one only).

DEADNESS IS TRANSITIVE, AND THAT IS THE WHOLE POINT. Counting direct importers
says `surface_xsec` is production code, because a file under `valuation/`
imports it. That file is `tickflow_signals`, which nothing but a closed study's
own script reaches. Reachability from a real entry point is the honest test,
and it is the one this module implements.
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# What actually runs in production. A module is "live" if and only if one of
# these can reach it. Entry points that do not exist are skipped, not assumed:
# a typo here would silently shrink the reachable set and turn a live module
# into an apparently-dead one, which is the direction that gets code deleted.
ENTRY_POINTS = (
    "valuation/saas/app_saas.py",   # the Flask app Render serves
    "valuation/web/app.py",         # the standalone web app
)

PACKAGE = "valuation"


def _dotted(rel: str) -> str:
    d = rel[:-3].replace("/", ".")
    return d[: -len(".__init__")] if d.endswith(".__init__") else d


def modules() -> dict[str, str]:
    """dotted name -> repo-relative path, for every module in the package."""
    out: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(ROOT / PACKAGE):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            rel = os.path.relpath(Path(dirpath) / fn, ROOT).replace("\\", "/")
            out[_dotted(rel)] = rel
    return out


def _imports(rel: str, mods: dict[str, str]) -> set[str]:
    """Every in-package module `rel` imports, by path.

    Both `import a.b` and `from a import b` are resolved, because the second
    form is how this package imports most things and a resolver that only
    handled the first would have reported almost every file as importing
    nothing -- a false all-clear.
    """
    try:
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return set()
    pkg = _dotted(rel)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:                       # relative import
                base = pkg.rsplit(".", node.level)[0] if "." in pkg else ""
                mod = f"{base}.{node.module}" if node.module else base
            else:
                mod = node.module or ""
            names.add(mod)
            # `from x import y` where y is itself a module, not an attribute
            names.update(f"{mod}.{a.name}" for a in node.names)
    return {mods[n] for n in names if n in mods and mods[n] != rel}


def graph() -> dict[str, set[str]]:
    """path -> set of in-package paths it imports."""
    mods = modules()
    return {rel: _imports(rel, mods) for rel in mods.values()}


def reachable() -> set[str]:
    """Every module reachable from a real entry point, transitively."""
    g = graph()
    seen: set[str] = set()
    stack = [e for e in ENTRY_POINTS if (ROOT / e).exists()]
    while stack:
        rel = stack.pop()
        if rel in seen:
            continue
        seen.add(rel)
        stack.extend(d for d in g.get(rel, ()) if d not in seen)
    return seen


def unreachable() -> set[str]:
    return set(graph()) - reachable()


def importers(target: str) -> set[str]:
    return {src for src, dsts in graph().items() if target in dsts}


def main(argv: list[str]) -> int:
    g = graph()
    live = reachable()
    if "--unreachable" in argv:
        for rel in sorted(unreachable()):
            print(rel)
        return 0
    if "--importers" in argv:
        target = argv[argv.index("--importers") + 1]
        for rel in sorted(importers(target)):
            print(rel)
        return 0
    print(f"modules      : {len(g)}")
    print(f"edges        : {sum(len(v) for v in g.values())}")
    print(f"reachable    : {len(live)}")
    print(f"unreachable  : {len(g) - len(live)}")
    for e in ENTRY_POINTS:
        print(f"entry point  : {e}{'' if (ROOT / e).exists() else '   ABSENT'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
