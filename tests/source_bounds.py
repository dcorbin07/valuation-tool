# -*- coding: utf-8 -*-
"""Bound a slice of source by its SYNTAX, never by a character count.

WHY THIS MODULE EXISTS, AS A COUNT RATHER THAN A PREFERENCE. Five guards in this suite read a
fixed character window from a landmark -- `src[i:i + 4000]`, `+ 2000`, `+ 1400`, `+ 1200`,
`+ 420` -- and asserted a needle appears inside it. The window is a PROXY for "this function" or
"this block", and a comment moves it, so the guard fails against a tree where the property it
tests is intact. Measured:

  * `test_index_mark.py` records the defect TWICE at 2,000 characters, in its own comments;
  * `test_index_book_publish.py` went red on 2026-10-07 when item 35's dip-cache block pushed
    `"index_book"` past the 4,000th character of `admin_ingest_snapshot`;
  * measured slack on the three that survived -- `test_valuation_routing.py` **60% used** (485
    characters, about six comment lines from firing), `test_hotlist_financial_fv.py` 33%,
    `test_free_kills_census.py` 27% and 32%.

**THE FAILURE MODE IS THE EXPENSIVE KIND**, because the natural response to a guard that goes red
on a correct tree is to widen the window or delete the guard -- so a proxy that drifts costs the
property it was protecting. It is the same shape as a substring ban: a test of something adjacent
to the rule rather than of the rule.

EVERY FUNCTION HERE RAISES RATHER THAN RETURNING EMPTY. A bound that silently came back `""`
would make every `assertIn` against it fail, and one that came back with the WHOLE FILE would
make every `assertIn` pass while bounding nothing -- the vacuous direction, which is worse. So
the callers get an exception naming what was not found, and each returns a segment the caller can
check the extent of.
"""
from __future__ import annotations

import ast
import io


def _parse(path: str):
    src = io.open(path, encoding="utf-8").read()
    return src, ast.parse(src)


def function_source(path: str, name: str) -> str:
    """The source of the top-level-or-nested `def name`, bounded by the function itself."""
    src, tree = _parse(path)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            seg = ast.get_source_segment(src, node)
            if seg:
                return seg
    raise AssertionError("no function %r in %s" % (name, path))


def if_body_source(path: str, anchor: str) -> str:
    """The BODY of the `if` whose TEST contains `anchor` — the `elif`/`else` arms excluded.

    Excluding the other arms is the point rather than tidiness: the chain this was written for
    has a branch saying "almost certainly a data problem" and the branch under test says "NOT a
    data problem", so a bound covering both would pass on either.
    """
    src, tree = _parse(path)
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = ast.get_source_segment(src, node.test) or ""
        if anchor in test:
            body = [ast.get_source_segment(src, st) or "" for st in node.body]
            return "\n".join(body)
    raise AssertionError("no `if` testing %r in %s" % (anchor, path))


def statement_source(path: str, anchor: str) -> str:
    """The SMALLEST statement whose source contains `anchor`.

    For a landmark inside a string literal — a SQL statement, a message — where the thing to
    bound is the call that holds it rather than any enclosing block.
    """
    src, tree = _parse(path)
    best = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.stmt):
            continue
        seg = ast.get_source_segment(src, node)
        if seg and anchor in seg and (best is None or len(seg) < len(best)):
            best = seg
    if best is None:
        raise AssertionError("no statement containing %r in %s" % (anchor, path))
    return best
