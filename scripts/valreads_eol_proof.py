# -*- coding: utf-8 -*-
"""Proof that `test_valreads.py`'s mutation case bites on a CRLF tree AND an LF tree.

    python -m scripts.valreads_eol_proof

`HANDOFF_optionsbot.md` §87b reported that
`test_append_only_case_fails_when_the_manifest_stops_being_append_only` **cannot pass on a Windows
checkout**: its needle spans a newline and is written with **LF**, `core.autocrlf` is `true`, so
the module is **CRLF on disk** and the needle never matched.

**THE TREES ARE MATERIALISED FROM THE STORED BLOBS, NOT WITH `git archive`.** `git archive` applies
the **CRLF filter** on Windows, so it cannot produce a true LF tree here and a proof built on it
would be measuring the filter rather than the fix — the memory note
`git-archive-is-not-a-CI-simulation`, which this lane has already paid for once.

Four cells, and all four are required:

| tree | test file | expected |
|---|---|---|
| LF | **fixed** | PASS |
| CRLF | **fixed** | PASS — the repair's whole point |
| LF | **pre-fix** | PASS — so the pre-fix needle was not simply broken everywhere |
| CRLF | **pre-fix** | **FAIL** — the reported defect, reproduced |

The last two are the **non-vacuity** half: without them a passing fixed case is consistent with
the bug never having existed.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

CASE = ("TestEachSelfCheckCaseCanActuallyFail."
        "test_append_only_case_fails_when_the_manifest_stops_being_append_only")

#: Extensions git would treat as text under `core.autocrlf=true`. Binary files are copied through
#: untouched — translating a `.pkl` would corrupt it, which is how a "simulation" stops simulating.
TEXT_EXT = {".py", ".md", ".txt", ".yml", ".yaml", ".json", ".cfg", ".ini", ".csv", ".bat", ".sh"}


def _run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd or _HERE, capture_output=True)


def materialise(dest: str, eol: bytes) -> dict:
    """Write every TRACKED file from its STORED BLOB, with text files forced to `eol`.

    One `git cat-file --batch` stream rather than a process per file, so this is seconds and not
    minutes. `data/` is gitignored, so nothing licensed is copied — which is also why the suite
    under test must not need it.
    """
    out = _run(["git", "ls-files", "-s"])
    if out.returncode != 0:
        raise SystemExit("git ls-files failed: %r" % out.stderr.decode("utf-8", "replace"))
    entries = []
    for line in out.stdout.decode("utf-8", "replace").splitlines():
        if not line.strip():
            continue
        meta, _, path = line.partition("\t")
        parts = meta.split()
        if len(parts) >= 2:
            entries.append((parts[1], path))

    req = "\n".join(sha for sha, _ in entries) + "\n"
    proc = subprocess.Popen(["git", "cat-file", "--batch"], cwd=_HERE,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    blob, _ = proc.communicate(req.encode("ascii"))

    n_text = n_bin = 0
    pos = 0
    for sha, path in entries:
        nl = blob.index(b"\n", pos)
        header = blob[pos:nl].decode("ascii")
        size = int(header.split()[-1])
        body = blob[nl + 1:nl + 1 + size]
        pos = nl + 1 + size + 1          # trailing newline after each object
        full = os.path.join(dest, path.replace("/", os.sep))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        if os.path.splitext(path)[1].lower() in TEXT_EXT:
            # The blob is canonical LF; force it to the tree's own convention.
            body = body.replace(b"\r\n", b"\n")
            if eol != b"\n":
                body = body.replace(b"\n", eol)
            n_text += 1
        else:
            n_bin += 1
        with io.open(full, "wb") as fh:
            fh.write(body)
    return {"files": len(entries), "text": n_text, "binary": n_bin}


def check_eol(root: str, rel: str) -> dict:
    b = io.open(os.path.join(root, rel.replace("/", os.sep)), "rb").read()
    crlf = b.count(b"\r\n")
    return {"crlf": crlf, "bare_lf": b.count(b"\n") - crlf}


def run_case(root: str) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = root
    r = subprocess.run([sys.executable, os.path.join(root, "tests", "test_valreads.py"), CASE],
                       cwd=root, capture_output=True, env=env)
    tail = r.stderr.decode("utf-8", "replace").strip().splitlines()[-6:]
    return {"exit": r.returncode, "passed": r.returncode == 0, "tail": tail}


def main(argv=None):
    tmp = tempfile.mkdtemp(prefix="valreads-eol-")
    results = {}
    try:
        prefix_src = _run(["git", "show", "HEAD:tests/test_valreads.py"]).stdout
        fixed_src = io.open(os.path.join(_HERE, "tests", "test_valreads.py"), "rb").read()
        if prefix_src == fixed_src.replace(b"\r\n", b"\n"):
            raise SystemExit("REFUSING: HEAD's test file is identical to the working one, so "
                             "there is no pre-fix version to compare against and the "
                             "non-vacuity half of this proof cannot run.")

        for tree, eol in (("lf", b"\n"), ("crlf", b"\r\n")):
            root = os.path.join(tmp, tree)
            print("[proof] materialising the %s tree from stored blobs ..." % tree.upper(),
                  flush=True)
            info = materialise(root, eol)
            info["module_eol"] = check_eol(root, "valuation/edge/valreads.py")
            print("    %d files (%d text, %d binary); module has %d CRLF / %d bare LF"
                  % (info["files"], info["text"], info["binary"],
                     info["module_eol"]["crlf"], info["module_eol"]["bare_lf"]), flush=True)

            cells = {}
            for variant, src in (("fixed", fixed_src), ("prefix", prefix_src)):
                body = src.replace(b"\r\n", b"\n")
                if eol != b"\n":
                    body = body.replace(b"\n", eol)
                with io.open(os.path.join(root, "tests", "test_valreads.py"), "wb") as fh:
                    fh.write(body)
                cells[variant] = run_case(root)
                print("    %-6s -> exit %d (%s)"
                      % (variant, cells[variant]["exit"],
                         "PASS" if cells[variant]["passed"] else "FAIL"), flush=True)
            results[tree] = {"tree": info, "cells": cells}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    exp = {("lf", "fixed"): True, ("crlf", "fixed"): True,
           ("lf", "prefix"): True, ("crlf", "prefix"): False}
    verdict = {}
    ok = True
    for (tree, variant), want in exp.items():
        got = results.get(tree, {}).get("cells", {}).get(variant, {}).get("passed")
        verdict["%s/%s" % (tree, variant)] = {"expected_pass": want, "passed": got,
                                              "as_expected": bool(got == want)}
        ok = ok and (got == want)

    out = {"item": "VALREADS-EOL", "part": "the mutation needle is line-ending-agnostic",
           "reported_by": "HANDOFF_optionsbot.md section 87b (RUN_RULES rule 3)",
           "case": CASE, "results": results, "expected_matrix": verdict,
           "all_as_expected": bool(ok),
           "WHY_NOT_GIT_ARCHIVE": ("git archive applies the CRLF filter on Windows, so it cannot "
                                   "produce a true LF tree here -- the memory note "
                                   "git-archive-is-not-a-CI-simulation, already paid for once"),
           "NON_VACUITY": ("the two pre-fix cells are the proof that the defect was real: the LF "
                           "tree must PASS pre-fix and the CRLF tree must FAIL pre-fix, or a "
                           "passing fixed case says nothing")}
    from valuation.studies import dipcall as D
    p = D.out_path("VALREADS_EOL_PROOF.json")
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    print("\n[proof] matrix: %s" % json.dumps(
        {k: ("as expected" if v["as_expected"] else "UNEXPECTED")
         for k, v in verdict.items()}), flush=True)
    print("[proof] all_as_expected %s -- wrote %s" % (ok, p), flush=True)
    return out


if __name__ == "__main__":
    r = main()
    raise SystemExit(0 if r["all_as_expected"] else 2)
