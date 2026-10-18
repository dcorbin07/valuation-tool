# -*- coding: utf-8 -*-
"""ITEM 71 -- HOW MANY TRANSITION-TABLE ROWS THE CODE GOT WRONG BEFORE THIS ITEM.

    python scripts/i71_table_before.py

**THE CONTROL THAT MAKES `tests/test_item71_table.py` EVIDENCE RATHER THAN A MIRROR.** A
declaration read off the implementation would agree with it everywhere, including on the bugs --
so the table proves nothing until it is shown to DISAGREE with a tree that has them. This
restores the pre-item-71 sources from git, runs the same declaration against them, and counts.

MEASURED 2026-10-17 against `da2c07e` (item 70 landed; the tree the auditor's sixth review
examined):

    rows            2240
    wrong           1641     <- genuinely different behaviour
    artefact only      2     <- see below
    kinds
      1524  WROTE the record when no write is permitted        (blocker C + two more sites)
       320  armed=False where the wind-down must arm           (blocker A)
       320  sell_only=False                                    (blocker A)
       271  CLOSED the event with no evidence                  (blockers B, C and the fifth)
       275  the self-report disagreed with the record          (mostly the artefact below)

**ONE KIND IS AN ARTEFACT AND IS EXCLUDED FROM THE 1,641.** `event_closed` is a field item 71
introduced, so on the old tree it reads `False` everywhere and the self-report-versus-record
check fires wherever the record says closed. That is the field's absence rather than a defect,
and counting it would inflate the number in this item's own favour. Only **2** rows are
artefact-only; the rest carry a real complaint as well.

**MY FIRST ATTEMPT AT THIS REPORTED "2,240 of 2,240 WRONG", WHICH WAS A `TypeError`** -- the old
`run_cycle` has no `may_write` parameter. Counting an API mismatch as 2,240 defects would have
been a flattering number produced by a broken harness. The old tree is now driven the way it
ACTUALLY behaved: `may_write` is dropped, which is exactly the old behaviour -- a GET ran a dry
cycle and that dry cycle wrote.

Sources are restored byte-for-byte afterwards and the restore is VERIFIED, because a harness
that cannot put a file back is worse than none.
"""
import hashlib
import io
import os
import subprocess
import sys

BASE = "da2c07e"
FILES = ["valuation/edge/live_cycle.py", "valuation/edge/live_slots.py",
         "valuation/saas/app_saas.py"]


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


before = {p: sha(p) for p in FILES}
saved = {p: io.open(p, "rb").read() for p in FILES}
CODE = '''
import collections
import json
import os
import sys
sys.path.insert(0, os.path.join(os.getcwd(), "tests"))
sys.path.insert(0, os.getcwd())
import tests.test_item71_table as T
from valuation.edge import live_cycle as LC

# THE OLD API, DRIVEN AS IT ACTUALLY BEHAVED. `may_write` did not exist, and a GET ran a dry
# cycle that wrote -- which is blocker C. Dropping the kwarg reproduces that exactly.
_real = LC.run_cycle


def shim(*a, **kw):
    kw.pop("may_write", None)
    return _real(*a, **kw)


LC.run_cycle = shim
rows = T.all_rows()
wrong, kinds = [], collections.Counter()
for r in rows:
    try:
        w = T.check_row(r)
    except Exception as e:                        # noqa: BLE001
        w = "%s: %s" % (type(e).__name__, e)
    if w:
        wrong.append(w)
        tail = w.split("::", 1)[-1]
        for part in tail.split(";"):
            part = part.strip()
            if part:
                kinds[part.split(",")[0][:58]] += 1
# **ONE KIND IS AN ARTEFACT AND IS COUNTED SEPARATELY.** `event_closed` is a field
# item 71 introduced, so on the old tree it is always False and the
# self-report-versus-record check fires wherever the record says closed. That is the
# field's absence, not a defect, and counting it as one would inflate the number in my
# own favour.
ART = "event_closed="
real = []
for w in wrong:
    parts = [p.strip() for p in w.split("::", 1)[-1].split(";") if p.strip()]
    if not all(p.startswith(ART) for p in parts):
        real.append(w)
print(json.dumps({"rows": len(rows), "wrong_any": len(wrong),
                  "wrong_real": len(real),
                  "artefact_only": len(wrong) - len(real),
                  "kinds": kinds.most_common(12)}, indent=1))
'''
try:
    for p in FILES:
        r = subprocess.run(["git", "show", "%s:%s" % (BASE, p)], capture_output=True)
        assert r.returncode == 0, r.stderr[:300]
        io.open(p, "wb").write(r.stdout)
    r = subprocess.run([sys.executable, "-c", CODE], capture_output=True, text=True)
    print("exit", r.returncode)
    print((r.stdout or "")[-3000:])
    if r.returncode != 0:
        print("STDERR:", (r.stderr or "")[-1200:])
finally:
    for p in FILES:
        io.open(p, "wb").write(saved[p])
    after = {p: sha(p) for p in FILES}
    assert after == before, "RESTORE FAILED"
    print("sources restored byte-for-byte")
