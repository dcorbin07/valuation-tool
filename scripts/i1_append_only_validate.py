"""S3-I1 gate: the extracted append-only writer reproduces the PRE-REFACTOR source exactly.

`PREREG_s3i1_fleet_harness.md` section E2 fixes this before anything new may use the writer
(`MB15`'s ordering: validate the instrument BEFORE the hypothesis that needs it). Three
obligations, all pre-committed:

  1. Reproduce the pre-refactor `index_mark.append_row` BIT-IDENTICALLY over a randomised case
     sweep covering every branch -- first write, duplicate key, backward key, header widening,
     ragged file, missing file, ignored fields, replacement.
  2. Reproduce the BYTE-LEVEL PREFIX guarantee `.github/workflows/track-row.yml` verifies.
  3. `tests/test_index_mark.py` passes unchanged (run separately, by the suite runner).

WHY THE COMPARISON IS AGAINST GIT AND NOT AGAINST MY EXPECTATION. `MA5` consolidated four
copies of one hurdle and proved the refactor inert by diffing values, not by asserting it;
`I-3` did the same against a banked artifact AND against the pre-refactor source restored from
git, because only the second isolates the refactor from drift in the data. There is no banked
artifact here, so the git route is the whole proof and it is the stronger one.

THE COMPARISON IS ON BYTES AND ON THE RETURNED DICT, not on one or the other. A writer can
return the right dict and write the wrong file.

Run:  python -m scripts.i1_append_only_validate
"""
from __future__ import annotations

import csv
import io
import json
import os
import random
import subprocess
import sys
import tempfile
import time
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The commit whose `index_mark.py` still carried the inline implementation. Pinned, because a
# moving baseline is not a baseline -- if this ever fails to resolve, the run REFUSES rather
# than silently comparing the new code against itself.
PRE_REFACTOR_REF = "b995940"

# Every branch the sweep must actually exercise. A sweep that misses one is a vacuous pass, so
# the coverage is COUNTED and gated rather than assumed (`MB21`'s C1 lesson).
REQUIRED_BRANCHES = (
    "first_write", "duplicate_key", "backward_key", "header_widen",
    "ragged_file", "no_key", "ignored_fields", "replacement", "append_forward",
)
MIN_CASES = 200


def _old_module():
    """`index_mark` as it stood at `PRE_REFACTOR_REF`, imported under its own name.

    Loaded as a synthetic module with the package's real `__package__`, so its relative
    imports resolve against the installed tree exactly as they did then.
    """
    src = subprocess.run(
        ["git", "-C", REPO, "show", PRE_REFACTOR_REF + ":valuation/screener/index_mark.py"],
        capture_output=True)
    if src.returncode != 0 or not src.stdout:
        raise SystemExit("REFUSING: could not restore " + PRE_REFACTOR_REF
                         + ":valuation/screener/index_mark.py -- a baseline that does not "
                           "resolve is not a baseline, and comparing the new code against "
                           "itself would pass vacuously.")
    text = src.stdout.decode("utf-8")
    if "from . import index_track" not in text or "AO.append(" in text:
        raise SystemExit("REFUSING: " + PRE_REFACTOR_REF + " does not carry the INLINE "
                         "implementation -- the baseline is wrong, not the code.")
    mod = types.ModuleType("_index_mark_pre_refactor")
    mod.__package__ = "valuation.screener"
    mod.__file__ = os.path.join(REPO, "valuation", "screener", "index_mark.py")
    exec(compile(text, mod.__file__, "exec"), mod.__dict__)
    return mod


def _write(path, header, rows):
    """The fixture is built with `csv.DictWriter`, the same writer under test.

    NOT a convenience. The first cut emitted `"\\n"` line endings by hand while the writer
    emits `"\\r\\n"` on this platform, so the byte-prefix obligation failed on 33 of 33
    append-only writes -- and it was measuring the FIXTURE's line endings, not the writer's
    guarantee. A prefix check is only meaningful against bytes the writer would itself have
    produced.
    """
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in header})


def _read_bytes(path):
    try:
        return open(path, "rb").read()
    except FileNotFoundError:
        return None


def _case(rng, i):
    """One randomised case, labelled with the branch it is built to reach."""
    cols = ["date", "day_n", "valquo_pct", "spy_pct", "excess_pp", "n_priced"]
    base = [{"date": "2026-08-%02d" % d, "day_n": d, "valquo_pct": round(rng.uniform(-9, 9), 4),
             "spy_pct": round(rng.uniform(-9, 9), 4), "excess_pp": round(rng.uniform(-3, 3), 4),
             "n_priced": rng.randint(50, 90)} for d in range(1, rng.randint(2, 7))]
    branch = REQUIRED_BRANCHES[i % len(REQUIRED_BRANCHES)]
    header, rows, row, append_only = list(cols), list(base), None, bool(i % 2)

    if branch == "first_write":
        rows, header = [], list(cols)
        row = {"date": "2026-09-01", "day_n": 1, "valquo_pct": 1.5, "spy_pct": 1.0,
               "excess_pp": 0.5, "n_priced": 86}
    elif branch == "duplicate_key":
        row = dict(rows[-1]); row["valquo_pct"] = 99.0        # differs from disk on purpose
    elif branch == "backward_key":
        row = dict(rows[0]); row["date"] = "2026-07-01"
    elif branch == "header_widen":
        header = [c for c in cols if c != "n_priced"]
        rows = [{k: v for k, v in r.items() if k != "n_priced"} for r in rows]
        row = {"date": "2026-09-01", "day_n": 40, "valquo_pct": 2.0, "spy_pct": 1.0,
               "excess_pp": 1.0, "n_priced": 86}
    elif branch == "ragged_file":
        row = {"date": "2026-09-01", "day_n": 40, "valquo_pct": 2.0, "spy_pct": 1.0,
               "excess_pp": 1.0, "n_priced": 86}
    elif branch == "no_key":
        row = {"day_n": 40, "valquo_pct": 2.0}
    elif branch == "ignored_fields":
        row = {"date": "2026-09-01", "day_n": 40, "valquo_pct": 2.0, "spy_pct": 1.0,
               "excess_pp": 1.0, "n_priced": 86, "vintage": 4, "typo_column": "x"}
    elif branch == "append_forward":
        # THE ONLY BRANCH THAT REACHES THE BYTE-PREFIX GUARANTEE: a forward key, an unchanged
        # header, append-only. Added after the first run reported the guarantee "held" on ZERO
        # writes -- every other append-only branch legitimately refuses or no-ops, so without
        # this one the check was scoring an empty comparison (`MB21`'s C1).
        row = {"date": "2026-09-%02d" % rng.randint(1, 28), "day_n": 99,
               "valquo_pct": 3.0, "spy_pct": 2.0, "excess_pp": 1.0, "n_priced": 86}
        append_only = True
    else:                                                     # replacement
        row = dict(rows[-1]); row["valquo_pct"] = 77.0
        append_only = False
    return branch, header, rows, row, append_only


def _norm(res, tmpdir):
    """The returned dict as sorted JSON, with the fixture's own directory removed.

    The first cut of this harness ran the two implementations against `old.csv` and `new.csv`
    and then compared a `path` field, so all 175 reported "mismatches" were the harness
    describing its own fixture. A comparator that cannot tell the object apart from the
    scaffolding is not measuring the object.
    """
    txt = json.dumps(res, sort_keys=True, default=str)
    return txt.replace(json.dumps(tmpdir)[1:-1], "<DIR>").replace(tmpdir, "<DIR>")


def _run(fn, tmpdir, branch, header, rows, row, append_only):
    path = os.path.join(tmpdir, "book.csv")
    if branch == "ragged_file":
        _write(path, header, rows)
        with io.open(path, "a", encoding="utf-8", newline="") as f:
            f.write("2026-08-30,30,1,2,3,80,SURPLUS\n")
    elif rows or branch != "first_write":
        _write(path, header, rows)
    before = _read_bytes(path)
    # BOUNDED RETRY ON ONE ENVIRONMENTAL FAILURE, COUNTED AND REPORTED -- never silenced.
    # `os.replace` on this platform intermittently raises WinError 32 under sustained temp-
    # volume contention; `MB16` and `MB21` both measured the same class, and it is invisible
    # on a Linux runner. A retry here is not tolerance for a real failure: only this exact
    # message retries, at most twice, and the count ships in the artifact.
    attempts = 0
    for attempts in range(1, 4):
        try:
            res = fn(row, path, append_only=append_only)
        except Exception as e:                                # noqa: BLE001
            res = {"__raised__": type(e).__name__ + ": " + str(e)}
        if "WinError 32" not in str(res.get("reason", "")) + str(res.get("__raised__", "")):
            break
        time.sleep(0.05)
    return res, before, _read_bytes(path), attempts - 1


def main() -> int:
    old = _old_module()
    from valuation.screener import index_mark as new

    rng = random.Random(20260823)
    seen, mismatches, prefix_checked, prefix_ok, env_retries = {}, [], 0, 0, 0

    for i in range(MIN_CASES):
        branch, header, rows, row, append_only = _case(rng, i)
        seen[branch] = seen.get(branch, 0) + 1
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            r_old, b_old_before, b_old_after, ro = _run(
                old.append_row, d1, branch, header, rows, row, append_only)
            r_new, b_new_before, b_new_after, rn = _run(
                new.append_row, d2, branch, header, rows, row, append_only)
            env_retries += ro + rn
            n_old, n_new = _norm(r_old, d1), _norm(r_new, d2)

        if b_old_before != b_new_before:
            mismatches.append({"case": i, "branch": branch, "why": "fixture differed"})
            continue
        if n_old != n_new:
            mismatches.append({"case": i, "branch": branch, "why": "returned dict",
                               "old": n_old[:400], "new": n_new[:400]})
        if b_old_after != b_new_after:
            mismatches.append({"case": i, "branch": branch, "why": "file bytes"})

        # Obligation 2: after an append-only WRITE the old bytes are an exact prefix.
        if append_only and r_new.get("wrote") and b_new_before is not None:
            prefix_checked += 1
            if b_new_after is not None and b_new_after.startswith(b_new_before):
                prefix_ok += 1

    missing = [b for b in REQUIRED_BRANCHES if not seen.get(b)]
    out = {
        "instrument": "S3-I1 append-only writer",
        "baseline_ref": PRE_REFACTOR_REF,
        "cases": MIN_CASES,
        "branches_exercised": seen,
        "branches_missing": missing,
        "mismatches": mismatches,
        "n_mismatches": len(mismatches),
        "prefix_guarantee_checked": prefix_checked,
        "prefix_guarantee_held": prefix_ok,
        "environmental_retries_winerror32": env_retries,
        "bit_identical": (not mismatches) and not missing,
    }
    print(json.dumps(out, indent=2))

    if missing:
        print("\nREFUSED: branches never exercised: " + ", ".join(missing)
              + " -- a sweep that misses a branch passes vacuously.")
        return 2
    if mismatches:
        print("\nFAILED: %d mismatches against %s. Per the register's E2, the refactor is "
              "REVERTED rather than patched." % (len(mismatches), PRE_REFACTOR_REF))
        return 1
    if prefix_checked == 0:
        print("\nREFUSED: the byte-prefix guarantee was never exercised -- reporting it as "
              "held would be reporting on an empty comparison.")
        return 2
    if prefix_ok != prefix_checked:
        print("\nFAILED: byte-prefix guarantee broken on %d of %d append-only writes."
              % (prefix_checked - prefix_ok, prefix_checked))
        return 1
    print("\nPASS: bit-identical to %s across %d cases and all %d branches; the byte-prefix "
          "guarantee held on %d of %d append-only writes."
          % (PRE_REFACTOR_REF, MIN_CASES, len(REQUIRED_BRANCHES), prefix_ok, prefix_checked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
