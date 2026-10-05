"""Prove the paper-track blocker is a CLOCK artefact, on files this lane does not modify.

Locally "today" is Sunday 2026-10-04, so the test passes and the mechanism is invisible. This
forces the reader's clock to Monday 2026-10-05 -- exactly what the CI runner saw at 00:04 UTC --
and shows the same fixture flip from PASS to FAIL with nothing else changed.

If it flips, the failure is the date and not either lane's code. Nothing is edited.
"""
import datetime as dt
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tests"))

import state_isolation  # noqa: F401,E402

import tests.test_paper_track as T  # noqa: E402
from valuation.saas import recap as RC  # noqa: E402
from valuation.edge import paper_track as PT  # noqa: E402

print("files this lane modifies: HANDOFF, scripts/oos1_gates.py, scripts/wrds_pull.py,")
print("  tests/test_oos1_gates.py, valuation/edge/compustat_provider.py")
print("files the failing test exercises: valuation/saas/recap.py, valuation/edge/paper_track.py")
print()

st = T._store()
b = T.FakeBroker(quotes={"AAA": {"last": 100.0}, "BBB": {"last": 200.0},
                         "SPY": {"last": 500.0}})
T._seed(st, b, T._BOOK)
PT.index_point(st, b)

sessions = RC._sandbox_sessions(st)
print("what the WRITER recorded (paper_track.index_point, _session_today):")
print("   as_of rows: %r" % (sessions,))
print("   real calendar today (this machine): %s (%s)"
      % (dt.date.today().isoformat(), dt.date.today().strftime("%A")))
print()

for label, day in (("as the READER sees it locally (Sunday)", None),
                   ("as the READER saw it in CI (Monday 2026-10-05)", dt.date(2026, 10, 5))):
    # `health_note` carries its OWN `day`, so both must be moved or the reader keeps the real
    # clock -- which is why the first attempt at this probe did not reproduce the failure.
    cyc = RC.collect(st, day=day)
    note = RC.health_note(cyc, day=day)
    hole = "hole in it" in note
    print("%s:" % label)
    print("   first=%r sessions_in_window=%r"
          % (cyc["sandbox_cycle"]["first"], cyc["sandbox_cycle"]["sessions_in_window"]))
    print("   note: %s" % note)
    print("   the test's assertion ('hole in it' NOT in note): %s"
          % ("FAILS" if hole else "passes"))
    print()

print("CONCLUSION: the only thing that changed between the two readings is the reader's DATE.")
