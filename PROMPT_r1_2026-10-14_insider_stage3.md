# PROMPT — r1 — 2026-10-14 — clustered insider buying: the older-data rung, a forward paper book, and one test fix

Read these first:

- `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path — your worktree's copy may
  be out of date; the 2026-10-14 "CLUSTERED INSIDER BUYING" entry);
- `RESEARCH_CHARTER.md` §5 Stage 3;
- your `HANDOFF_insider_cluster_wide.md`.

INSIDER-WIDE confirmed on the `$500M+` cell at +3.49pp gross and +2.91pp net. Don wants stage 3:
one older-data read, plus a forward paper book in shares started now.

## 1. The older-data rung: feasibility first (zero trials)

The manager measured that `data/backtest/insiders.csv` has filing dates only from **2008** on. The
P-code counts by filing year are 32,794 in 2008, 12,795 in 2009 and 9,244 in 2010. The cluster rule
also needs each insider's two prior calendar years of history. So on owned data the first usable
event is about 2010, and the 1999-2008 read cannot be run. Do the following:

1. **Confirm the gap**, and give the first date the frozen construction can emit an event.
2. **Check, from the SEC's own pages, whether its free insider data reaches earlier.** Report the
   first year a Form 4 can be read in structured form, and the first year the two-prior-year rule
   could then emit events.
3. **State the power of that window before any outcome is read.** Use the build cell's realised
   `se`, scaled with the ~1.5× era correction your own §5d measured.
4. **Decide the outcome:**
   - If no free source can supply a powered window, record the rung as unobtainable on owned data,
     the `S25` way, and stop.
   - If one can, **report the build's size and stop**. Don decides whether to pay for it. Do not
     build it.

## 2. The forward paper book in shares

Use the fleet harness (`S3-I1`), the same route F-21 and F-22 use.

1. **Commit the declaration ALONE.** It is a fenced json block that passes `validate_declaration`.
2. **Freeze the entry rule from the registered construction:** the `$500M+` tier at point-in-time
   cap, h=63, and the cluster rule verbatim.
3. **Declare before the first fill:** sizing, concurrency, benchmark, and the seven-field verdict
   horizon with its power. Quote `O11` verbatim.
4. **State the late-half caveat** (2023-2026 nets about zero) inside the declaration itself.
5. **Find a live source for new Form 4 filings.** The SF2 export is a snapshot.
   - Prove the source reproduces SF2's cluster events on an overlapping recent window before it
     feeds the book.
   - Record each entry at a real quote taken after the cluster is public.
   - Never backfill. Nothing before the declaration commit counts.
6. **Retirement rule:** a NOT CONFIRMED older-data read retires the book. If the rung is
   unobtainable, the book carries on and says so.

## 3. `tests/test_valreads.py` fails on Windows

The options lane reported this in its handoff §87b. The mutation needle is LF, but a Windows
checkout is CRLF, so the needle never matches.

- Make the needle line-ending-agnostic.
- Show that the case still fails on a real mutation, on both a CRLF tree and an LF tree (materialise
  the blobs; `git archive` applies the CRLF filter).
- Restore sources byte-for-byte.

## Rules and done

Paper only: no real orders, and nothing is adopted. Check landing once after each push, with no
wait loops. Done means on origin/main, with a plain-words summary for Don that covers what the older
data can and cannot answer, and when the book's first fill can come.
