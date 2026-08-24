# TAQ PULL PLAN — read this before planning around WRDS TAQ

**For: the day-trading sibling project. Written by the data-miner lane, 2026-08-24.
Zero trials — facts about entitlement and size, not a research result.**

> **THE FILE DID NOT EXIST WHEN IT WAS ASKED FOR.** It was requested by name; it was not in the
> worktree, not in the main checkout where Cowork writes, not on any of ~40 remote refs, and not
> in git history. So this is the first version, written from a live measurement of the account
> rather than from anyone's recollection of what WRDS includes.

---

## THE ANSWER IN ONE LINE

**This WRDS account cannot source TAQ. Do not plan around it.**

Full TAQ **exists on WRDS and is DENIED to us** — which is a different and more useful fact than
"missing", because it means the fix is an entitlement conversation, not a search for another
table name.

| probe | result | what it means |
|---|---|---|
| `taqmsec.ctm_20200102` | **DENIED** | TAQ Millisecond is there; we may not read it |
| `taqm_2020.ctm_20200102` | **DENIED** | the year-partitioned millisecond library, same |
| `taq.ct_20200102` | **ABSENT** | the legacy daily library is not in our catalogue at all |
| `taqmsamp.ctm_20090213` | **ENTITLED** | the *sample*, one day |
| `taqsamp.ct_20080107` | **ENTITLED** | the *sample*, five days |

**The originating brief said "flag size only, do not bulk-pull (terabytes)". The premise is
void — there is nothing terabyte-scale to avoid, because there is nothing to pull.**

---

## WHAT IS ACTUALLY REACHABLE — 8 days, and they are useful for exactly one thing

| library | contents | dates |
|---|---|---|
| `taqsamp` / `taqsamp_all` | legacy daily TAQ: `ct_` trades, `cq_` quotes, `mast_200801` master, `div_200801` | **2008-01-07 … 01-11** (5 days) |
| `taqmsamp` / `taqmsamp_all` | millisecond: `ctm_`, `cqm_`, `nbbom_` (NBBO), plus `ix_` index files | **2009-02-13** (1 day) |
| both | exchange integrated feed: `nyse_idf_*`, `arca_idf_*` | **2021-10-04, 10-05** (2 days) |
| `wrdsapps_link_crsp_taq` | `tclink` — the CRSP↔TAQ symbol bridge | — |

**These are enough to build and unit-test a parser, a clock-alignment routine and an NBBO
reconstruction. They are not enough to measure anything.** Eight non-contiguous days across
2008/2009/2021 cannot support a strategy claim, a microstructure estimate, or a cost model —
and a result computed on them would be a sample of three market regimes chosen by a vendor for
demonstration purposes.

---

## THE SIZE NUMBER YOU ACTUALLY NEED — measured, not estimated

**One day of TAQ trades is ~30–35 million rows.**

| table | rows | note |
|---|---|---|
| `taqmsamp.ctm_20090213` | **35,386,359** | trades, one day, 2009 |
| `taqsamp.ct_20080107` | **29,275,686** | trades, one day, 2008 |

Quotes run several times larger than trades, and both grow substantially after 2009 — 2009 is
before the bulk of the HFT quote-rate expansion, so **treat 35M as a floor for a modern day, not
a typical value.** At ~13 columns and mixed dtypes, one day of *trades alone* is on the order of
1–2 GB uncompressed.

So the original instinct was right about the magnitude — a multi-year TAQ pull is genuinely
terabyte-scale — but the constraint that actually binds is entitlement, not disk.

`ctm_` columns (millisecond trades): `date, time_m, ex, sym_root, sym_suffix, tr_scond, size,
price, tr_stopind, tr_corr, tr_seqnum, tr_source, tr_rf`.
`ct_` columns (legacy daily): `symbol, date, time, price, size, g127, corr, cond, ex`.
**They are not the same schema** — a parser written against one will not read the other, and the
sample gives you both, which is the one genuinely valuable thing about it.

---

## THE SAMPLING RECIPE — scoped to what exists, and honest that it is a rehearsal

If full TAQ is ever entitled, this is the shape that will not blow up. **Nothing here has been
executed** beyond the two probes above.

1. **Never `SELECT *` a day.** Project the columns you need — for trade-side work that is
   typically `time_m, sym_root, price, size, tr_corr, tr_scond`. Dropping the exchange/sequence
   columns roughly halves the payload.
2. **Chunk by (date × symbol-bucket), never by date alone.** A single day is one table on WRDS
   (`ctm_YYYYMMDD`), so the chunk key is the table; within it, filter `sym_root IN (...)` in
   batches of a few hundred names. A whole-day unfiltered fetch is the request that gets killed
   server-side.
3. **Filter server-side, always.** `tr_corr = '00'` (uncorrected) and a `tr_scond` allow-list
   belong in the SQL, not in pandas. Moving 35M rows to filter down to 5M is 30M rows of wasted
   transfer.
4. **Resume per (date, bucket)**, payload written atomically before its manifest line — the same
   discipline as `scripts/wrds_pull.py` and the ThetaData harvest. At this row count a re-run
   that cannot resume is a day lost.
5. **Storage: `D:\wrds\taq\` if it ever happens.** Licensed rows never leave that root, are
   never committed, and never reach a public surface. Derived statistics only.
6. **Prototype on the 8 sample days first** and prove the parser round-trips both schemas before
   asking for entitlement. That is what the samples are for.

---

## WHAT TO DO NEXT

1. **Tell the day-trading lane it does not have a TAQ source**, before it plans a strategy that
   assumes one. That is the entire point of this file.
2. **If TAQ matters, it is an entitlement request, not an engineering task.** WRDS TAQ is
   licensed separately from CRSP/Compustat/IBES; our account has the latter three and not this.
   Route it to Don as a subscription question with the size numbers above attached.
3. **Consider whether TAQ is even the right source.** We already hold a ThetaData tick cache at
   `data/options_ticks/` (4.72 GB, 3,884 alert-days, 70.3 M prints) — options ticks rather than
   equity ticks, but real, owned, and already banked. For an equity-tick day-trading question the
   honest comparison is TAQ-via-subscription against ThetaData equity tick, and nobody has priced
   the second.

**Nothing in this file is a research result. No arm, no verdict, zero trials.**
Reproduce the entitlement probes with `python -m scripts.wrds_census`; raw probe output is at
`D:\wrds\TAQ_PROBE.json`. Full entitlement picture: `WRDS_CENSUS.md`.
