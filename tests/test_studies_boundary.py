"""The product/study boundary MA23 drew, pinned so it cannot silently erode.

WHY A TEST AND NOT A CONVENTION. The twelve modules under `valuation/studies/` were in
`valuation/edge/` for months precisely because nothing said they should not be. A boundary
that lives only in a docstring is re-crossed by the first person who needs one function from
one study, and the crossing is invisible in review — it is one import line.

THE LOAD-BEARING ASSERTION IS THE DIRECTION, NOT THE LOCATION. A study importing the engine
is correct and expected (that is what a harness does). The engine importing a study is what
makes the study product code again and puts it back in the deploy image. Only the second is
refused.

THESE TESTS ARE CHECKED FOR VACUITY. A boundary test that passes because it found nothing to
look at is worthless, so each one asserts a non-zero census before asserting the property —
the `sector-neutral` lesson (a guard whose subject is empty reports success).
"""
from __future__ import annotations

import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  (must precede any `valuation` import)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALUATION = os.path.join(REPO, "valuation")
STUDIES = os.path.join(VALUATION, "studies")

# The twelve MA23 moved. Named as a literal rather than derived from the directory listing:
# deriving it would make the test agree with whatever the directory happens to contain, which
# is exactly the property under test.
MOVED = (
    "ev_multiples_study", "convex_overlay", "earnings_surface", "kelly",
    "loo_holdout", "ml_combiner", "surface_stock", "live_replay",
    "bucket_floor", "portfolio_capacity", "param_search", "lazy_prices_ic",
)


def _py_files(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for f in filenames:
            if f.endswith(".py"):
                yield os.path.join(dirpath, f)


def _imports(path: str):
    """Every module string this file imports, absolute and relative alike.

    Relative imports are resolved against the file's own package so `..edge.statistics` from
    `valuation/studies/` comes back as `valuation.edge.statistics` — a boundary check that
    could not see relative imports would miss the only form the moved modules actually use.
    """
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        src = fh.read()
    tree = ast.parse(src)
    rel = os.path.relpath(path, os.path.dirname(VALUATION)).replace(os.sep, ".")
    pkg = rel[:-3].rsplit(".", 1)[0]          # drop ".py", then the module name
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parts = pkg.split(".")
                base = parts[: len(parts) - (node.level - 1)] if node.level > 1 else parts
                mod = ".".join(base + ([node.module] if node.module else []))
            else:
                mod = node.module or ""
            out.append(mod)
            for a in node.names:
                out.append((mod + "." + a.name) if mod else a.name)
    return out


def test_the_twelve_modules_are_where_MA23_put_them():
    """Vacuity guard for every other test here: the package must be populated."""
    assert os.path.isdir(STUDIES), "valuation/studies/ does not exist"
    present = {f[:-3] for f in os.listdir(STUDIES)
               if f.endswith(".py") and f != "__init__.py"}
    missing = sorted(set(MOVED) - present)
    assert not missing, "MA23 modules missing from valuation/studies/: %s" % missing
    # And they must NOT still be sitting in their old homes, or the move was a copy.
    for m in MOVED:
        assert not os.path.exists(os.path.join(VALUATION, "edge", m + ".py")), \
            "%s is still in valuation/edge/ — the move was a copy, not a move" % m
        assert not os.path.exists(os.path.join(VALUATION, "research", m + ".py")), \
            "%s is still in valuation/research/" % m


def test_no_engine_module_imports_a_study():
    """THE DIRECTION IS ONE-WAY. This is the assertion the package exists to protect."""
    scanned = 0
    offenders = []
    for path in _py_files(VALUATION):
        if os.path.abspath(path).startswith(os.path.abspath(STUDIES)):
            continue                                   # a study may import a study
        scanned += 1
        for mod in _imports(path):
            if mod.startswith("valuation.studies"):
                offenders.append((os.path.relpath(path, REPO).replace(os.sep, "/"), mod))
    assert scanned > 50, "only %d non-study modules scanned — the walk is broken" % scanned
    assert not offenders, (
        "engine code imports a study, which puts it back in the deploy image: %s" % offenders)


def test_a_study_may_import_the_engine_and_at_least_one_does():
    """The permitted direction, asserted so the test above is not passing by forbidding both."""
    importers = []
    for path in _py_files(STUDIES):
        for mod in _imports(path):
            if mod.startswith("valuation.edge") or mod.startswith("valuation.screener"):
                importers.append(os.path.basename(path))
                break
    assert len(importers) >= 4, (
        "expected several studies to import the engine; found %s. If this drops to zero the "
        "one-way test above becomes vacuous." % importers)


def test_every_moved_module_still_imports():
    """A rename that leaves a broken relative import fails at import time, not at read time."""
    import importlib
    for m in MOVED:
        mod = importlib.import_module("valuation.studies." + m)
        assert mod is not None
        # `param_search` and `loo_holdout` reach the panel through `..edge`; if that depth were
        # wrong the import above would already have raised, so this pins the resolved name.
        assert mod.__name__ == "valuation.studies." + m


def _code_only(src: str) -> str:
    """`src` with every comment and string literal blanked out.

    A GUARD THAT CANNOT TELL CODE FROM PROSE ABOUT CODE IS NOT MEASURING THE TREE. The first
    cut of the test below grepped raw source and fired on `scripts/suite_manifest.py`, whose
    COMMENT explains a classifier bug using `from valuation.edge import kelly` as its example —
    documentation of the very thing being checked, not a live import. This is the same defect,
    and the same repair, as the MA5 source sweep.
    """
    import io
    import tokenize
    lines = src.splitlines(keepends=True)
    # Blank the comment/string SPANS in place rather than re-joining tokens. Re-joining with a
    # separator turns `valuation.edge` into `valuation . edge` and the check then matches
    # nothing — which the vacuity test below caught on the first cut of this helper.
    try:
        spans = [(t.start, t.end) for t in tokenize.generate_tokens(io.StringIO(src).readline)
                 if t.type in (tokenize.COMMENT, tokenize.STRING)]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return src            # unparseable: fall back to the strict reading
    buf = [list(ln) for ln in lines]
    for (r0, c0), (r1, c1) in spans:
        for r in range(r0, r1 + 1):
            if r - 1 >= len(buf):
                continue
            row = buf[r - 1]
            lo = c0 if r == r0 else 0
            hi = c1 if r == r1 else len(row)
            for c in range(lo, min(hi, len(row))):
                if row[c] != "\n":
                    row[c] = " "
    return "".join("".join(r) for r in buf)


def test_the_old_import_paths_are_gone_from_the_tree():
    """No caller may still name `valuation.edge.<study>` — a stale path fails only when run."""
    stale = []
    for sub in ("scripts", "tests", "valuation"):
        for path in _py_files(os.path.join(REPO, sub)):
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                src = _code_only(fh.read())
            for m in MOVED:
                for bad in ("valuation.edge." + m, "valuation.research." + m):
                    if bad in src:
                        stale.append((os.path.relpath(path, REPO).replace(os.sep, "/"), bad))
    assert not stale, "stale import paths remain: %s" % stale


def test_the_stale_path_check_is_not_vacuous():
    """`_code_only` must blank prose WITHOUT blanking a real import — checked both ways, or
    the test above could pass by seeing nothing at all."""
    real = "from valuation.edge import kelly\n"
    prose = "# from valuation.edge import kelly\n"
    assert "valuation.edge" in _code_only(real)
    assert "valuation.edge" not in _code_only(prose)


def test_the_panel_is_not_among_the_moved_files():
    """MA23 does NOT shrink `fundamental_panel.py`, and the map says otherwise.

    `MA_DEPENDENCY_MAP.md` calls MA23 "the item that would change" the panel's
    one-owner-at-a-time constraint. It cannot: the panel is a file, and it is not one of the
    files moved. Pinned so nobody later reads the move as having resolved that constraint.
    """
    assert "fundamental_panel" not in MOVED
    panel = os.path.join(VALUATION, "edge", "fundamental_panel.py")
    assert os.path.exists(panel), "the panel moved, which MA23 never proposed"
    with open(panel, "r", encoding="utf-8", errors="ignore") as fh:
        n = len(fh.readlines())
    assert n > 4000, "panel is %d lines; the constraint on it was never MA23's to lift" % n


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} studies-boundary tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
