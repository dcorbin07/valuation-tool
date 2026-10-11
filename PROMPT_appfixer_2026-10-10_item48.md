# PROMPT — app fixer — 2026-10-10 — item 48 (URGENT, before anything else): the gate is red for every lane

Every landing since run #696 has FAILED, so nothing pushed on 2026-10-10 is on main — your item 46,
the scout's SELL-PREMIUM draft, and r1's CANONICAL_MOVE_TABLE. origin/main is still 4e413da
(2026-10-09 20:01, markdown only). Every failed run shows the same annotations:

- `tests/test_paper_track.py FAILED`
- `no book passed the commit check; refusing to write an empty manifest`
- `the fleet backup came back SHORTER than the committed copy: hwbook 3 -> 1`

Reproduced on a clean clone of origin/main: test_paper_track.py reads 73/76 and the three failures
are the recap health-note tests, i.e. they depend on TODAY's date (2026-10-10 is a Saturday):

    FAIL test_health_note_STILL_FIRES_on_a_genuinely_missed_session
    FAIL test_health_note_bounds_expected_by_the_window_collect_actually_used   (2026-10-03)
    FAIL test_health_note_reports_no_hole_when_the_reader_runs_on_a_WEEKEND

1. Fix them so they inject their dates rather than reading the clock — a test that passes Monday
   to Friday and fails on Saturday is a time bomb, and this one blocks every lane. Keep what each
   asserts; if the PRODUCT code is what reads the clock wrongly on a weekend, fix the product and
   say so (the third test's name says that is exactly the case it guards).
2. Say whether the other two annotations are expected output of passing suites or real problems
   (the "fleet backup came back SHORTER ... hwbook 3 -> 1" line in particular), and act on it.
3. Land it, then re-run the three failed land runs (`gh run rerun` for #696, #698/#697 and #699),
   or ask each lane to re-push, so item 46, SELL-PREMIUM and CANONICAL_MOVE_TABLE land. Confirm
   each is on origin/main.

Then continue with item 47.

Done means the gate green and all three on origin/main.
