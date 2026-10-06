"""The paper-track health-note clock: the defect, the fix, and the proof the alarm still works.

THE DEFECT. `paper_track.index_point` dates its row with `_session_today()` -- `ITEM 20`, which
exists because *"the service runs UTC: a job delivered after 20:00 ET is already the next calendar
day in UTC"* -- while `recap.health_note` built its denominator from `_dt.date.today()`, the raw
UTC date. One concept, two definitions, in two modules: `B7`.

WHAT IT COST. From about 23:54 UTC on 2026-10-04 the landing gate went red for EVERY lane at once
-- `worktree-crowding-p2`, `worktree-scout-research-reset`, and r1's `D9-SAMEDATE` and
`INDEX-CHOICE-ARM4` -- all on one assertion, because `born` was the Friday session while `today`
had rolled to Monday. `expected` held two sessions against one recorded, and the note truthfully
reported a hole in a track that had none.

THE PROPERTY THIS SCRIPT EXISTS TO PROTECT. `session_date()` reads the MARKET CALENDAR, not the
recorded data, so a session the market held and the cron missed is STILL in `expected` and is
STILL reported. Anchoring on the last RECORDED session would have made the check vacuous;
anchoring on the last REAL session does not. Leg 4 below is the proof, and it is the leg that
matters -- a "fix" that stopped the alarm firing would be a silencing, not a repair.

    python -m scripts.diagnose_paper_track_clock

Read-only: it writes to a temporary store and edits nothing.
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
from valuation.edge import paper_track as PT  # noqa: E402
from valuation.saas import recap as RC  # noqa: E402
from valuation.screener.market_session import is_trading_day  # noqa: E402

FRI = dt.date(2026, 10, 2)          # a session
SAT = dt.date(2026, 10, 3)
SUN = dt.date(2026, 10, 4)
MON = dt.date(2026, 10, 5)          # a session, and the UTC date CI had rolled to
XMAS = dt.date(2026, 12, 25)        # a market holiday


def _fixture(session):
    """A store whose writer stamped exactly `session`, with the clock pinned there."""
    real = PT._session_today
    PT._session_today = lambda: session
    try:
        st = T._store()
        b = T.FakeBroker(quotes={"AAA": {"last": 100.0}, "BBB": {"last": 200.0},
                                 "SPY": {"last": 500.0}})
        T._seed(st, b, T._BOOK)
        PT.index_point(st, b)
        return st
    finally:
        PT._session_today = real


def _note(st, reader_session, day=None):
    """`health_note` as it reads with the session clock pinned to `reader_session`."""
    real = PT._session_today
    PT._session_today = lambda: reader_session
    try:
        return RC.health_note(RC.collect(st), day=day)
    finally:
        PT._session_today = real


def main():
    ok = True
    print("is_trading_day: Fri %s  Sat %s  Sun %s  Mon %s  25-Dec %s"
          % (is_trading_day(FRI), is_trading_day(SAT), is_trading_day(SUN),
             is_trading_day(MON), is_trading_day(XMAS)))
    print()

    # 1-3: the reader runs on a weekend or a holiday. `session_date()` returns the last real
    # session, so writer and reader agree and there is no hole to report.
    for label, session in (("1. reader on SATURDAY (session is Friday)", FRI),
                           ("2. reader on SUNDAY   (session is Friday)", FRI),
                           ("3. reader on a HOLIDAY (25 Dec, session is the 24th)",
                            dt.date(2026, 12, 24))):
        st = _fixture(session)
        note = _note(st, session)
        hole = "hole in it" in note
        ok &= not hole
        print("%s\n   %s\n   -> %s" % (label, note, "HOLE (bad)" if hole else "clean"))
    print()

    # 4: THE ALARM MUST STILL FIRE. The market held Monday's session and the cron recorded only
    # Friday's. This is a REAL hole and the note must say so -- if this leg goes quiet the fix
    # has silenced the check rather than repaired it.
    st = _fixture(FRI)
    note = _note(st, MON)
    fired = "hole in it" in note
    ok &= fired
    print("4. a GENUINELY missed session (market traded Monday, only Friday recorded)")
    print("   %s" % note)
    print("   -> %s" % ("alarm FIRED, correctly" if fired
                        else "SILENT -- the fix would be a silencing, not a repair"))
    print()

    # 5: NON-VACUITY. The old anchor was the raw UTC date, which `day=` reproduces exactly.
    # At 00:04 UTC on Monday the session was still Friday, so the old reader invented a hole.
    st = _fixture(FRI)
    old = _note(st, FRI, day=MON)
    new = _note(st, FRI)
    print("5. the OLD anchor (raw UTC date, rolled to Monday while the session is Friday)")
    print("   old: %s\n   new: %s" % (old, new))
    differs = ("hole in it" in old) and ("hole in it" not in new)
    ok &= differs
    print("   -> %s" % ("the old path invented a hole and the new one does not"
                        if differs else "NO DIFFERENCE -- this probe is not measuring the fix"))

    print("\n%s" % ("ALL LEGS AS EXPECTED" if ok else "SOMETHING IS WRONG -- see above"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
