# PROMPT — app fixer — 2026-10-07 — item 36

Read `DECISIONS.md` first. Item 35 verified live: /api/dip at 0.10 serves 210 qualified, 30 rows,
87 rejected on health, 3 shallow, 90 unmeasured, capped 0, source precomputed. Live check 28/0/1.

## (a) The 90 dip names with no 52-week high

You reported that 90 of 210 qualifying names carry no 52-week high from either source, so the
screen can never show more than ~120 of them however it is spent. Find where the high is supposed
to come from (`prices` / `broker_universe` / the scan snapshot), and compute it from price history
the scan already fetches wherever the feed leaves it blank — a 252-session max of the as-traded
close, on the same basis the drawdown is measured against (state which, and never mix adjusted and
raw). Report the before/after counts live at 0.10 / 0.20 / 0.30 and keep the identity check.

## (b) The comment-length test guards near firing

You listed three tests that read a fixed character window and are close to failing on a comment
(`test_valuation_routing.py:681` at 60%, `test_hotlist_financial_fv.py:348`,
`test_free_kills_census.py:96`). Repoint them the way you did `test_index_book_publish.py`
(`ast.get_source_segment` with a non-vacuity check), so the next lane does not lose a session to it.

## (c) HOLD until Don decides — the /proof disclosure

`DECISION_canonical_universe.md` routes the public-page question to Don. Do not change /proof,
/methodology or the landing tiles until DECISIONS.md records his ruling.

Done means on origin/main, verified live.
