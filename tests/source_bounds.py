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
    with io.open(path, encoding="utf-8") as fh:          # closed, or a ResourceWarning rides
        src = fh.read()                                  # into every suite that imports this
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


def js_function_source(path: str, name: str) -> str:
    """The source of `function name(...) { ... }`, bounded by its own BRACES.

    THE SAME RULE ONE LANGUAGE OVER. `app.js` carries the Dip Detector's rendering, and guards
    over it were the worst offenders in the census above -- `test_index_book_publish.py` read
    4,000 characters from a landmark and went red the day a comment moved. A brace match is the
    JS analogue of `ast.get_source_segment`: it bounds the function, so a comment inside it
    cannot push a needle out and a change to the NEXT function cannot pull one in.

    IT IS A MATCHER, NOT A PARSER, and it says so. Strings (single, double and template), `//`
    and block comments are skipped so a brace inside one cannot unbalance the count; a REGEX
    LITERAL containing an unmatched brace would still fool it, which is why the result is
    CHECKED rather than trusted -- the segment must begin at the declaration, end at a closing
    brace, and be shorter than the file. An unbalanced scan RAISES rather than returning the
    remainder of the file, because the vacuous direction (a bound that is really the whole file)
    makes every `assertIn` pass while bounding nothing.
    """
    with io.open(path, encoding="utf-8") as fh:
        src = fh.read()
    needle = "function %s(" % name
    i = src.find(needle)
    if i < 0:
        raise AssertionError("no `function %s(` in %s" % (name, path))
    j = src.find("{", i)
    if j < 0:
        raise AssertionError("no body for `function %s` in %s" % (name, path))

    depth, k, n = 0, j, len(src)
    while k < n:
        c = src[k]
        if c in "\"'`":                                    # a string literal
            q, k = c, k + 1
            while k < n and src[k] != q:
                k += 2 if src[k] == "\\" else 1
            k += 1
            continue
        if c == "/" and k + 1 < n and src[k + 1] == "/":   # line comment
            k = src.find("\n", k)
            if k < 0:
                break
            continue
        if c == "/" and k + 1 < n and src[k + 1] == "*":   # block comment
            k = src.find("*/", k)
            if k < 0:
                break
            k += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                seg = src[i:k + 1]
                if (not seg.startswith(needle) or not seg.endswith("}")
                        or len(seg) >= len(src)):
                    raise AssertionError(
                        "the bound for %r in %s is not a function body" % (name, path))
                return seg
        k += 1
    raise AssertionError("braces never balanced for %r in %s" % (name, path))


def code_only(segment: str) -> str:
    """`segment` with comments and string literals removed, so a guard sees CODE.

    THE COMPANION DEFECT TO THE CHARACTER WINDOW, and the one this project has paid for most
    often: a guard that bans a token fires against the CORRECT tree, because the comment
    explaining the rule quotes the thing the rule forbids. `MA49`, `MB1` (three times in one
    register), `MB15` and `I-2` are all this shape -- and the first cut of
    `test_item38_health_not_scored.py` asserted that `dip.py` spells no regime name, against a
    comment whose whole job is to say WHY it must not.

    `tokenize` rather than a regex, because a `#` inside a string and a quote inside a comment
    defeat the regex in opposite directions.

    IT RAISES ON UNPARSEABLE INPUT rather than returning the segment unchanged. A stripper that
    silently gives back prose makes the ban it feeds fire on prose again -- the defect,
    restored. And one that returned `""` would make every ban PASS while seeing nothing, which
    is worse, so a caller should also assert something it expects to SURVIVE.
    """
    import io as _io
    import tokenize as _tok

    # TOKENS ARE JOINED WITH A SPACE, and the first cut joined them with NOTHING. Two costs,
    # one of each sign: a multi-token needle (`qual and not n_high`) became unmatchable, so the
    # assertion could never pass; and adjacent tokens FUSE, so `a` followed by `b` reads as
    # `ab` and a needle could match text that is not there. The false-positive direction is the
    # one that matters -- it is a guard passing on the wrong evidence.
    out, last_line = [], 1
    try:
        for tk in _tok.generate_tokens(_io.StringIO(segment).readline):
            if tk.type in (_tok.COMMENT, _tok.STRING):
                continue
            out.append(" ")
            out.append(tk.string)
            last_line = tk.end[0]
    except (_tok.TokenError, IndentationError) as e:
        raise AssertionError("code_only could not tokenize the segment: %s" % e)
    return " ".join("".join(out).split())
