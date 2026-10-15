"""AN UNDEFINED-VARIABLE CHECK FOR `app.js`, IN PURE PYTHON.  [item 57 A1]

WHY THIS EXISTS, AND WHY IT IS HAND-WRITTEN
-------------------------------------------
Item 57 A1: `runValue` called `loadRecent(ticker, (d.company && d.company.name) || "")` where
the variable in scope is `data`. Every search on valquo.co threw
`ReferenceError: d is not defined`, the red error box painted over a valuation that had already
rendered, and the earnings/press-release/headline panel never loaded for any name. `node --check`
cannot see it -- the file is syntactically perfect -- and the defect survived in production.

There is no linter available to catch it. `npx eslint` needs a network install, there is no
`package.json`, and CI installs the hash-checked **Python** lock only, so a JS dependency cannot
be added without changing what CI installs. Shelling out to `node` would make the check SKIP
wherever node is absent, which is the "guards that fail open in CI" family this project has
been bitten by before. So the check is pure Python and always runs.

WHAT IT IS AND, MORE IMPORTANTLY, WHAT IT IS NOT
------------------------------------------------
**It is a scope checker, not a JavaScript parser, and it is deliberately CONSERVATIVE.** It
treats a function body plus everything nested inside it as ONE scope and takes the union of
every declaration in it. That over-declares -- an inner `const x` counts as declared in the
outer body too -- so it can MISS a defect. It cannot invent one, which is the direction that
matters: a check that cries wolf on this file would be switched off within a week (`MA21`).

The two things that make it worth having anyway:

* it catches the family that actually bites here -- a short data-ish name (`d`, `r`, `res`,
  `row`) read in a function that declares no such thing, which is what a copy-paste between
  two handlers produces; and
* it is proved NON-VACUOUS against git: `test_item57.py` restores the pre-fix `app.js` and
  requires this to report exactly the `d` in `runValue`.

Strings, template literals, regex literals and comments are stripped before anything is read,
because `"d"` in a string and `/d+/` in a regex are not references. Property accesses (`a.d`),
object keys (`{d: 1}`) and labels are excluded for the same reason.
"""
from __future__ import annotations

import os
import re

#: Browser and language globals this file legitimately reads. Not a convenience list: every
#: name here is one a browser supplies, so omitting one would be a false positive and adding a
#: project symbol would be a hole. Project-level symbols are DERIVED instead (see `globals_of`).
BROWSER_GLOBALS = {
    "window", "document", "console", "fetch", "location", "history", "navigator", "localStorage",
    "sessionStorage", "setTimeout", "clearTimeout", "setInterval", "clearInterval", "alert",
    "confirm", "prompt", "requestAnimationFrame", "cancelAnimationFrame", "URL",
    "URLSearchParams", "Blob", "File", "FileReader", "FormData", "Headers", "Request",
    "Response", "AbortController", "Event", "CustomEvent", "MutationObserver",
    "IntersectionObserver", "ResizeObserver", "getComputedStyle", "matchMedia", "btoa", "atob",
    "encodeURIComponent", "decodeURIComponent", "encodeURI", "decodeURI", "structuredClone",
    "Math", "JSON", "Object", "Array", "String", "Number", "Boolean", "Date", "RegExp", "Error",
    "TypeError", "RangeError", "SyntaxError", "ReferenceError", "Promise", "Map", "Set",
    "WeakMap", "WeakSet", "Symbol", "Proxy", "Reflect", "BigInt", "Intl", "isNaN", "isFinite",
    "parseInt", "parseFloat", "undefined", "NaN", "Infinity", "globalThis", "this", "arguments",
    "super", "new", "typeof", "instanceof", "void", "delete", "in", "of", "let", "const", "var",
    "function", "class", "return", "if", "else", "for", "while", "do", "switch", "case",
    "default", "break", "continue", "throw", "try", "catch", "finally", "await", "async",
    "yield", "true", "false", "null", "extends", "static", "get", "set", "import", "export",
    "from", "as", "with", "debugger",
    # Charting library, loaded from a script tag.
    "Chart",
}

#: A declaration statement, captured to its END rather than to its first `=`. The first cut
#: stopped at `=`, so `const q = a, h = b, f = c` -- which this file writes constantly, and
#: `loadRecent` writes on its own first line -- declared only `q`, and `h` and `f` read as
#: undefined. That alone was 220 false positives.
#: THE DECLARATION KEYWORD ONLY. What follows it is PARSED, not matched -- see
#: `_declared_in_text`. Three regexes were tried and each broke a different real shape in this
#: file, which is the argument for parsing:
#:
#:   1. `[^=;\n]+`           -- stopped at the first `=`, so `const q = a, h = b` declared only
#:                              `q`. 220 false positives.
#:   2. `(?:[^;{}]|\{[^{}]*\})*` -- allowed `{}` in an initialiser and therefore SWALLOWED a
#:                              nested arrow body, hiding the `const w` inside it. 17.
#:   3. `[^;{}]*`             -- stopped at the `{` of `(d.price_assumes || {})`, so `_w` in
#:                              `const _pa = (... || {}), _w = (...)` was never declared. 78.
#:
#: All three failures are the same shape as the defect this checker exists for: something that
#: looks declared and is not.
_DECL_KW = re.compile(r"\b(?:const|let|var)\s+")
_FUNC = re.compile(r"\b(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)?\s*\(([^)]*)\)")
_ARROW_PARAMS = re.compile(r"(?:\(([^)]*)\)|([A-Za-z_$][\w$]*))\s*=>")
_CATCH = re.compile(r"\bcatch\s*\(\s*([A-Za-z_$][\w$]*)\s*\)")
_FOR_DECL = re.compile(r"\bfor\s*\(\s*(?:const|let|var)\s+([A-Za-z_$][\w$]*)")
_IDENT = re.compile(r"[A-Za-z_$][\w$]*")
_LABEL = re.compile(r"^\s*[A-Za-z_$][\w$]*\s*:")


#: What can precede a REGEX literal but not a division: an operator, an opening bracket, a
#: comma, a colon, a keyword, or the start of the file. After a value (`)`, `]`, an identifier,
#: a number) a `/` is division.
_BEFORE_REGEX = set("=(,:[!&|?{};+-*%~^<>") | {"return", "typeof", "case", "in", "of", "do",
                                               "else", "yield", "await", "new", "delete",
                                               "void", "instanceof"}


def _regex_starts_here(src: str, i: int) -> bool:
    """Is the `/` at `i` the start of a regex literal rather than a division?"""
    j = i - 1
    while j >= 0 and src[j] in " \t\n\r":
        j -= 1
    if j < 0:
        return True
    if src[j] in _BEFORE_REGEX:
        return True
    k = j
    while k >= 0 and (src[k].isalnum() or src[k] in "_$"):
        k -= 1
    return src[k + 1:j + 1] in _BEFORE_REGEX


def strip_noncode(src: str) -> str:
    """Blank comments, strings and template TEXT; keep `${...}` expressions. Offsets preserved.

    A TEMPLATE LITERAL IS BOTH TEXT AND CODE, and the first cut of this function treated it as
    all code -- so every HTML tag name inside one (`div`, `span`, `$`) read as an undefined
    variable and the checker reported **515 findings on a correct file**. A check with 515
    false positives is not a check; it is a thing somebody deletes. The literal's text is
    blanked and each `${...}` is kept, with brace depth tracked and nested templates handled
    by recursion, because `app.js` nests them several deep inside `.map()` calls.
    """
    out = [" "] * len(src)
    n = len(src)

    def copy(a, b):
        for k in range(a, min(b, n)):
            out[k] = src[k]

    def blank_newlines(a, b):
        for k in range(a, min(b, n)):
            out[k] = "\n" if src[k] == "\n" else " "

    def scan(i, stop_at_backtick=False, depth=0):
        """Copy code from `i`; returns the index just past where it stopped."""
        while i < n:
            c = src[i]
            nxt = src[i + 1] if i + 1 < n else ""
            if c == "/" and nxt == "/":
                j = src.find("\n", i)
                j = n if j < 0 else j
                blank_newlines(i, j)
                i = j
            elif c == "/" and nxt == "*":
                j = src.find("*/", i + 2)
                j = n if j < 0 else j + 2
                blank_newlines(i, j)
                i = j
            elif c in "\"'":
                quote, j = c, i + 1
                while j < n:
                    if src[j] == "\\":
                        j += 2
                        continue
                    if src[j] == quote:
                        j += 1
                        break
                    if src[j] == "\n":        # an unterminated quote: do not run away
                        break
                    j += 1
                blank_newlines(i, j)
                i = j
            elif c == "`":
                i = template(i)
            elif c == "/" and _regex_starts_here(src, i):
                # A REGEX LITERAL, not division. `.replace(/_/g, " ")` was contributing `_`
                # and `g` as undefined variables -- 20 of the 49 remaining false positives.
                # Telling a regex from a division needs the PRECEDING token, which is what
                # `_regex_starts_here` reads; `app.js` writes both.
                j = i + 1
                in_class = False
                while j < n:
                    if src[j] == "\\":
                        j += 2
                        continue
                    if src[j] == "[":
                        in_class = True
                    elif src[j] == "]":
                        in_class = False
                    elif src[j] == "/" and not in_class:
                        j += 1
                        while j < n and src[j].isalpha():      # flags: g, i, m, s, u, y
                            j += 1
                        break
                    elif src[j] == "\n":
                        break                                   # not a regex after all
                    j += 1
                blank_newlines(i, j)
                i = j
            elif stop_at_backtick and c == "}" and depth == 0:
                return i
            else:
                if stop_at_backtick and c == "{":
                    depth += 1
                elif stop_at_backtick and c == "}":
                    depth -= 1
                out[i] = c
                i += 1
        return i

    def template(i):
        """Blank a template's text, keep its `${...}` expressions. Returns index past it."""
        out[i] = " "
        i += 1
        while i < n:
            c = src[i]
            if c == "\\":
                blank_newlines(i, i + 2)
                i += 2
                continue
            if c == "`":
                out[i] = " "
                return i + 1
            if c == "$" and i + 1 < n and src[i + 1] == "{":
                out[i] = out[i + 1] = " "
                j = scan(i + 2, stop_at_backtick=True)
                if j < n and src[j] == "}":
                    out[j] = " "
                    j += 1
                i = j
                continue
            out[i] = "\n" if c == "\n" else " "
            i += 1
        return i

    scan(0)
    return "".join(out)


def _names(blob: str) -> set:
    """Declared names out of a declaration or parameter list, destructuring included."""
    got = set()
    for m in _IDENT.finditer(blob or ""):
        nm = m.group(0)
        # `{a: b}` in a BINDING position declares `b`, not `a`; taking both over-declares,
        # which is the safe direction for this checker.
        if nm not in BROWSER_GLOBALS:
            got.add(nm)
    return got


def _declared_in(blob: str) -> set:
    """Names BOUND by a declaration statement's declarator list.

    A declarator list is `name = expr, name = expr, ...`, so the bound names are the one at
    the start and the one after each TOP-LEVEL comma -- top-level meaning outside parentheses,
    brackets and braces, or `const a = f(x, y)` would declare `y`. Destructuring patterns
    (`const {a, b} = o`) are passed to `_names`, which over-declares and is the safe
    direction.
    """
    got = set()
    depth = 0
    start = 0
    parts = []
    for i, ch in enumerate(blob or ""):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(blob[start:i])
            start = i + 1
    parts.append((blob or "")[start:])
    for part in parts:
        head = part.split("=", 1)[0].strip()
        if not head:
            continue
        if head[:1] in "{[":
            got |= _names(head)                 # a destructuring pattern
        else:
            m = _IDENT.match(head)
            if m and m.group(0) not in BROWSER_GLOBALS:
                got.add(m.group(0))
    return got


def _declared_in_text(text: str) -> set:
    """Every name bound by every `const`/`let`/`var` in `text`, at any nesting depth.

    EACH KEYWORD IS PARSED INDEPENDENTLY, which is the whole point: a regex match consumes the
    text it matched, so an outer declaration whose initialiser contains a nested `const` hid
    that nested one from `finditer` entirely (failure 2 in the note on `_DECL_KW`). Scanning
    for every keyword and parsing each one forward cannot have that problem.

    The declarator list ends at a `;` or a `}` at depth 0 -- or at a newline when no `;` has
    been seen and the depth is 0, because this file does not always terminate a statement.
    """
    got = set()
    for m in _DECL_KW.finditer(text or ""):
        i, n = m.end(), len(text)
        depth, start, heads = 0, i, []
        while i < n:
            ch = text[i]
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                if depth == 0:
                    break
                depth -= 1
            elif depth == 0:
                if ch == ";":
                    break
                if ch == ",":
                    heads.append(text[start:i])
                    start = i + 1
                elif ch == "\n":
                    # A continuation line is still the same statement when it ends on a comma
                    # or an operator; otherwise stop. Over-stopping only loses declarations,
                    # which is the safe direction.
                    tail = text[start:i].rstrip()
                    if tail.endswith((",", "=", "+", "?", ":", "&", "|", "(")):
                        pass
                    else:
                        break
            i += 1
        heads.append(text[start:i])
        for head in heads:
            h = head.split("=", 1)[0].strip()
            if not h:
                continue
            if h[:1] in "{[":
                got |= _names(h)                    # a destructuring pattern
            else:
                mm = _IDENT.match(h)
                if mm and mm.group(0) not in BROWSER_GLOBALS:
                    got.add(mm.group(0))
    return got


def globals_of(code: str) -> set:
    """Top-level declarations in `app.js` -- its own globals, derived rather than listed."""
    got = set()
    depth = 0
    for line in code.split("\n"):
        if depth == 0:
            got |= _declared_in_text(line)
            for m in _FUNC.finditer(line):
                if m.group(1):
                    got.add(m.group(1))
        depth += line.count("{") - line.count("}")
        depth = max(0, depth)
    return got


def _bodies(code: str):
    """`(name, body)` for every top-level `function name(...) {...}`, by brace matching."""
    for m in re.finditer(r"\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{",
                         code):
        start = m.end() - 1
        depth, i, n = 0, start, len(code)
        while i < n:
            if code[i] == "{":
                depth += 1
            elif code[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        yield m.group(1), m.group(2), code[start + 1:i]


def undefined_reads(path: str, extra_globals=()) -> list:
    """`[(function, name, line)]` for identifiers read but declared nowhere in scope."""
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    code = strip_noncode(raw)
    top = globals_of(code) | set(extra_globals) | BROWSER_GLOBALS
    findings = []
    for fname, params, body in _bodies(code):
        declared = set(top) | _names(params)
        declared |= _declared_in_text(body)
        for rx in (_FOR_DECL, _CATCH):
            for m in rx.finditer(body):
                declared |= _names(m.group(1))
        for m in _ARROW_PARAMS.finditer(body):
            declared |= _names(m.group(1) or m.group(2) or "")
        for m in _FUNC.finditer(body):
            if m.group(1):
                declared.add(m.group(1))
            declared |= _names(m.group(2))
        # Reads: an identifier not preceded by `.` and not followed by `:` (an object key).
        for m in _IDENT.finditer(body):
            nm = m.group(0)
            if nm in declared:
                continue
            # `1e6` is a NUMBER, and `_IDENT` happily matches the `e6` inside it -- which is
            # where the `e6` findings came from. An identifier cannot begin immediately after
            # a digit or another word character.
            if m.start() > 0 and (body[m.start() - 1].isdigit()
                                  or body[m.start() - 1] in "_$"
                                  or body[m.start() - 1].isalpha()):
                continue
            before = body[:m.start()]
            if before.rstrip().endswith(".") or before.rstrip().endswith("?."):
                continue
            after = body[m.end():]
            if after.lstrip().startswith(":"):
                continue
            if _LABEL.match(body[body.rfind("\n", 0, m.start()) + 1:m.end() + 2] or ""):
                continue
            line = raw[:code.find(body) + m.start()].count("\n") + 1 if body in code else 0
            findings.append((fname, nm, line))
    return findings


def app_js(root=None) -> str:
    base = root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "valuation", "web", "static", "app.js")
