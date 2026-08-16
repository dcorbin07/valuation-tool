#!/usr/bin/env python3
"""
suite_manifest.py -- which test suites gate a LANDING, and which pin a CLOSED
STUDY. Derived from the import graph, not hand-listed.

    python scripts/suite_manifest.py              # summary
    python scripts/suite_manifest.py --product    # suites the land gate needs
    python scripts/suite_manifest.py --register   # suites that pin closed studies

WHY (master audit MA60, second bullet). The auto-land gate runs every
`tests/test_*.py`, and the audit's point is that every closed experiment's pin
test therefore runs on every land, forever -- the gate grew from the ~24 suites
its own livelock arithmetic assumed to 88 today. The audit asks to split
product suites (on land) from register-pin suites (nightly).

THE SPLIT IS SHIPPED HERE; THE WORKFLOW CHANGE IS NOT, AND THAT IS DELIBERATE.
MA11 (landed 2026-08-15) gave the repo a land policy that REFUSES any branch
touching `.github/`, precisely so branch code cannot edit the gate that judges
it. Splitting the gate means editing `.github/workflows/land-agent-branch.yml`,
so this item cannot auto-land its own last step, and weakening the policy to
let it through would be silencing a check to make a run green. The judgement
call -- which suite is which -- is the part that needed a person, and it is
here. Applying it is a two-line workflow edit for a human.

THE RULE, and it is derived so it cannot go stale: a suite is a REGISTER PIN if
every in-package module it imports is unreachable from a production entry
point. If it touches even one live module, it is a PRODUCT suite and must run
on every land. The default for an unclassifiable suite is PRODUCT -- the safe
direction, since the cost of running a pin test on a land is time, and the cost
of NOT running a product test is a broken deploy.
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import import_graph  # noqa: E402


def _suite_imports(path: Path, mods: dict[str, str]) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names.add(mod)
            names.update(f"{mod}.{a.name}" for a in node.names)
    # Package `__init__` modules are excluded. `from valuation.studies import kelly`
    # resolves BOTH `valuation.studies` and `valuation.studies.kelly`, and the package
    # (path updated by MA23, which moved `kelly` out of `valuation/edge/`; the reasoning
    # below is unchanged and still holds for whichever package the study lives in)
    # init is reachable from the live app, so counting it made every closed
    # study's pin test look like production code -- 92 of 94 suites classified
    # 'product' on the first cut. Importing a package is not touching live code.
    return {mods[n] for n in names if n in mods
            and not mods[n].endswith("__init__.py")}


def classify() -> dict[str, str]:
    """suite filename -> 'product' | 'register-pin'."""
    mods = import_graph.modules()
    live = import_graph.reachable()
    out: dict[str, str] = {}
    for p in sorted((ROOT / "tests").glob("test_*.py")):
        touched = _suite_imports(p, mods)
        if touched and not (touched & live):
            out[p.name] = "register-pin"
        else:
            # Imports nothing in-package, or touches a live module: run it.
            out[p.name] = "product"
    return out


def main(argv: list[str]) -> int:
    c = classify()
    if "--product" in argv:
        print("\n".join(n for n, k in c.items() if k == "product"))
        return 0
    if "--register" in argv:
        print("\n".join(n for n, k in c.items() if k == "register-pin"))
        return 0
    prod = [n for n, k in c.items() if k == "product"]
    reg = [n for n, k in c.items() if k == "register-pin"]
    print(f"suites total : {len(c)}")
    print(f"product      : {len(prod)}   (must run on every land)")
    print(f"register-pin : {len(reg)}   (candidates for nightly)")
    print("\nregister-pin suites:")
    for n in reg:
        print(f"  {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
