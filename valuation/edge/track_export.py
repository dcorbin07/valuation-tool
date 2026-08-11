"""
Back up the forward track — the one dataset in this project that cannot be re-derived.

WHY THIS EXISTS
---------------
Everything else Valquo knows can be rebuilt: the panel re-reads the Sharadar exports, the
backtest re-runs, the hot list re-scans. The FORWARD track cannot. It is a record of what the
model said on days that have already happened, and its entire value is that nobody could have
looked at the outcome first. Re-creating it later from today's data would produce a different
object with the same column names — which is worse than losing it, because it would look fine.

It currently lives in exactly one place: the SQLite database on the Render web service's
persistent disk (`render.yaml`: disk `data`, `/app/data`, 1GB). That disk survives redeploys.
It does not survive the service being deleted and recreated, the disk being detached, or the
free-tier reaper. Months of out-of-sample record sit behind one un-backed-up volume.

WHAT IT WRITES
--------------
Plain, human-readable, deterministic files under `data_export/`:

  paper_track_history.json   everything below, structured, one file
  paper_track_index.csv      the TRADIER SANDBOX book's daily vs-SPY series
  paper_track_trades.csv     every closed paper option trade, entry -> exit -> P&L
  paper_track_holdings.csv   the sandbox index book the series is computed from
  valquo_index_track.csv     THE CONTRACT-BOUND Valquo Index daily series
  valquo_index_meta.json     that series' inception, benchmark and 86-name book

NAMING, corrected 2026-08-09. `paper_track_index.csv` was described here as "the daily
Valquo-Index-vs-SPY series". It is not: it is the Tradier sandbox engine's book (10 names,
equal-weighted at 10%, inception 2026-08-03), whose weights violate the 8% cap in
`PAPER_TRACK_CONTRACT.md`. The contract-bound Valquo Index series is the ingested Cowork
tracker, backed up below under the `index_track` meta key. The two were conflated in prose
here and in code in `saas/recap.py`, where it put a false "Index beating SPY" claim into
Discord on 2026-08-05. These files are a BACKUP and make no claim of their own — but the
label is how the confusion travels, so it is stated exactly.

LA2, 2026-08-10 — THE BACKUP WAS BACKING UP THE WRONG BOOK, AND THE GUARD WAS GUARDING IT.
Everything above was true in prose and false in effect. `payload()` did reach for the bound
series (`ingested_index_track`), but only through `store.get_meta` — and nothing has ever
ingested that key on the live service, so every committed backup carried
`ingested_index_days: 0` and `ingested_index_track: null` while faithfully preserving four
days of the sandbox book. The anti-regression guard counted `paper_track_index.csv`, i.e. the
book that is NOT the one that cannot be re-derived; the bound series could go from two rows to
zero without tripping anything, because it was never counted at all. Three repairs:

  * the bound series is gathered from EVERY place it can live — the committed backup, the
    local `data/` tracker files, and the live store's `index_track` meta — and merged by date
    (`merge_bound_rows`), so no source that happens to be empty can erase one that is not;
  * it is written as its own CSV, so it is countable, diffable and restorable on its own;
  * `guard_counts()` reports the bound row count for the workflow to enforce.

WHY THE BOUND SERIES IS COMMITTED AND `data/` STILL IS NOT. The repo-root `data/` is
gitignored because it holds the licensed Sharadar exports, which may not be redistributed —
that rule is unchanged and nothing here touches it. The bound series is a different object: it
is Valquo's own output, 127 bytes of it, derived and unlicensed, and until now it existed on
exactly one laptop with no writer anywhere in this repository to reproduce it. So a COPY lives
under `data_export/` with the rest of the backup.

IT IS A BACKUP, NOT A SECOND RECORDER — this is the part that matters. `index_track.load()`
still reads `data/valquo_track*` and nothing else, so there is still exactly ONE authority for
a vs-SPY claim (`index_track.vs_spy_claim`). This module writes a copy and never reads one
back into the live path. The project has already been bitten twice by two recorders of one
number disagreeing (audit B7 on the site, the Discord recap on 2026-08-05); a backup that
quietly became an input would be that bug a third time.

The prompt asked for "a .csv + a .json". It is three CSVs because the backup holds three
genuinely different record types, and merging a daily return series with per-contract trades
into one table would need a `record_type` column and a union of ~30 columns, most of them null
on any given row — a format nobody can read in a spreadsheet, which is the point of CSV here.
The JSON is the complete artifact; the CSVs are the readable view of it.

BOTH forward records are captured. There are two: the Tradier paper sandbox book that this
service runs itself, and the ingested Cowork tracker series (`meta` key `index_track`). Both
are point-in-time records that cannot be reconstructed, so backing up only the one the hero
happens to lead with would quietly lose the other.

IDEMPOTENT AND REWRITE-IN-FULL. Every file is regenerated from the database on each run, rows
sorted by a stable key, floats rounded to a fixed precision. Same database in, byte-identical
files out — so a weekly commit is a no-op when nothing changed, and a real diff when it did.
Deliberately NOT append-only: append-only would preserve a corrupted or half-written row
forever, and the database, not this file, is the source of truth.

NO SECRETS. Only market data, timestamps and sandbox broker order ids. No tokens, no
credentials, no account numbers, no vendor raw rows — see the vendor table in
HANDOFF_appfixes.md.

USAGE
-----
    python -m valuation.edge.track_export                     # local DB -> data_export/
    python -m valuation.edge.track_export --out somewhere/
    python -m valuation.edge.track_export --from-json dump.json   # CI: from the live service
    python -m valuation.edge.track_export --from-json -           # ... reading stdin

The last form is how it runs in CI: GitHub Actions cannot read Render's disk, and Render
cannot commit to git, so the web service exposes the payload at `/admin/export-track` (admin
token) and the workflow pipes it here and commits the result.
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
import sys

#: Bumped when the shape of the payload changes, so a future reader can tell which layout a
#: committed file is in rather than guessing from which keys happen to be present.
SCHEMA_VERSION = 1

#: Round every float to this many places before writing. Without it, SQLite's float repr can
#: differ in the last bit between runs and produce a git diff on a day nothing happened —
#: which trains you to ignore the diff, which is how a real change gets missed.
_PRECISION = 10


def _round(v):
    return round(v, _PRECISION) if isinstance(v, float) else v


def _rows(store, table: str, order_by: str) -> list:
    """All rows of a table, or [] if it was never created.

    The paper-track tables are created lazily by `paper_track.ensure_schema`, so on a database
    where the track has never run they legitimately do not exist. A missing table is an empty
    backup, not an error — but a missing table is NOT silently identical to an empty one in
    the payload, which records `tables_present` so "the track has no data" and "the export
    could not see the track" stay distinguishable.
    """
    try:
        with store._conn() as c:
            cur = c.execute(f"SELECT * FROM {table} ORDER BY {order_by}")
            keys = [d[0] for d in cur.description]
            return [{k: _round(v) for k, v in zip(keys, r)} for r in cur.fetchall()]
    except Exception:
        return []


def _table_exists(store, table: str) -> bool:
    try:
        with store._conn() as c:
            r = c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                          (table,)).fetchone()
        return bool(r)
    except Exception:
        return False


_TABLES = {
    "index_series": ("paper_index_track", "as_of"),
    "index_holdings": ("paper_index_holdings", "ticker"),
    "paper_orders": ("paper_option_orders", "COALESCE(entry_ts, created_at), alert_id"),
    "option_alerts": ("option_alerts", "alert_ts, id"),
}

# --------------------------------------------------------------------------------------- #
# THE CONTRACT-BOUND VALQUO INDEX SERIES (LA2). Not the sandbox engine — see the header.
# --------------------------------------------------------------------------------------- #
BOUND_INDEX_CSV = "valquo_index_track.csv"
BOUND_INDEX_META = "valquo_index_meta.json"

#: Deliberately the SAME column names as `data/valquo_track_history.csv`, so restoring is a
#: copy rather than a transformation. A restore that has to rename columns is a restore that
#: gets done wrong at 2am; `index_track.load()` reads these exact headers.
_BOUND_COLS = ["date", "valquo_pct", "spy_pct", "excess_pp", "n_priced"]


def _bound_rows(track: dict) -> list:
    """`index_track`'s in-memory row shape -> this backup's column names.

    `index_track` names the columns `valquo`/`spy`/`excess` once loaded; the file on disk
    calls them `valquo_pct`/`spy_pct`/`excess_pp`. The file's names win here, per _BOUND_COLS.
    """
    out = []
    for r in (track or {}).get("series") or []:
        d = str(r.get("date") or "").strip()
        if not d:
            continue
        out.append({"date": d, "valquo_pct": _round(r.get("valquo")),
                    "spy_pct": _round(r.get("spy")), "excess_pp": _round(r.get("excess")),
                    "n_priced": r.get("n_priced")})
    return out


def merge_bound_rows(*sources) -> list:
    """Union bound-series rows by date, sorted by date.

    PRECEDENCE IS EXPLICIT AND ONE-DIRECTIONAL: a later source overrides an earlier one for a
    date they share, and **no date present in any source is ever dropped**. That asymmetry is
    the whole point. The failure this exists to prevent is a source that is legitimately empty
    (a fresh Render disk, a service that never ingested the tracker) overwriting a source that
    is not — which is precisely how LA2's backup came to hold zero bound rows while looking
    like a successful weekly job for months.

    Callers pass sources oldest-authority-first: committed backup, then live/local.
    """
    by_date = {}
    for src in sources:
        for r in src or []:
            d = str(r.get("date") or "").strip()
            if not d:
                continue
            by_date[d] = {c: (d if c == "date" else r.get(c)) for c in _BOUND_COLS}
    return [by_date[k] for k in sorted(by_date)]


def _f(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def read_bound_csv(path: str) -> list:
    """Rows already committed under `data_export/`. A missing file is zero rows.

    A missing file is normal (the first run) and returns []. A file that EXISTS but cannot be
    parsed raises, deliberately: this module wrote it, so a parse failure means it was
    corrupted or hand-edited, and the safe response to "I cannot read the backup" is to stop —
    not to report zero rows and let the merge treat the record as never having existed.
    """
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            d = (r.get("date") or "").strip()
            if not d:
                continue
            rows.append({c: (d if c == "date" else _f(r.get(c))) for c in _BOUND_COLS})
    return rows


def bound_series(store=None, meta_path: str = None, history_path: str = None,
                 committed_dir: str = None) -> dict:
    """The bound Index series and its book, gathered from every place it can live.

    Three sources, none of which is reliably populated on its own:
      1. `committed_dir` — what a previous backup already committed (present in CI, which is
         the only place with no other source at all);
      2. the local tracker files under `data/` — the Cowork side's authority, present on Don's
         machine and absent everywhere else because `data/` is gitignored;
      3. the live store's `index_track` meta — populated by `/admin/ingest-snapshot`.

    Merged in that order, so the freshest wins a shared date and nothing is ever lost.
    `sources` records which ones actually contributed, so "the backup is thin" and "the backup
    could not see the tracker" stay distinguishable — the same reason `tables_present` exists.
    """
    from ..screener import index_track

    committed = read_bound_csv(os.path.join(committed_dir, BOUND_INDEX_CSV)) \
        if committed_dir else []

    files = index_track.load(meta_path, history_path)
    ingested = index_track.from_store(store) if store is not None else {"meta": {}, "series": []}

    rows = merge_bound_rows(committed, _bound_rows(files), _bound_rows(ingested))
    # The book: prefer the richer file (it carries `positions`), fall back to the store's meta.
    meta = files.get("meta") or {}
    if not meta.get("inception_date"):
        meta = {k: v for k, v in (ingested.get("meta") or {}).items() if v is not None} or meta
    return {
        "meta": meta,
        "series": rows,
        "recorder": index_track.RECORDER,
        "book": index_track.BOOK,
        "sources": {"committed_backup": len(committed),
                    "tracker_files": len(files.get("series") or []),
                    "ingested_store": len(ingested.get("series") or [])},
    }


def payload(store, generated_at: str = None, bound_paths: tuple = None) -> dict:
    """The complete backup, as a plain dict. Pure read — writes nothing, computes nothing.

    Deliberately raw-ish: this is a BACKUP, so it stores what the tables hold rather than the
    summarised, caveated read-model that `paper_track.summary()` builds for the UI. A summary
    cannot be un-summarised later, and the whole point is to be able to reconstruct the record
    if the disk is gone.
    """
    out = {
        "schema_version": SCHEMA_VERSION,
        # Passed in by the caller (or stamped now) rather than embedded mid-computation, so a
        # test can produce a fixed artifact and a re-run on unchanged data differs only here.
        # Timezone-aware then stripped: `utcnow()` is deprecated in 3.12+ and this module runs
        # unattended in CI, where a DeprecationWarning on every run is noise that trains you
        # to ignore the log. Same string as before, so committed files do not churn.
        "generated_at": generated_at or _dt.datetime.now(_dt.timezone.utc).replace(
            tzinfo=None).isoformat(timespec="seconds"),
        "what_this_is": (
            "Forward, out-of-sample paper record of the Valquo model. Every row was written "
            "before its outcome was known. Paper only - Tradier sandbox, no real money. "
            "This file exists because this record cannot be reconstructed if it is lost."),
        "tables_present": {},
    }
    for key, (table, order_by) in _TABLES.items():
        out["tables_present"][table] = _table_exists(store, table)
        out[key] = _rows(store, table, order_by)

    # The SECOND forward record: the externally-ingested Cowork tracker series, which lives in
    # `meta` rather than a table of its own. Same irreplaceability, so same backup.
    try:
        from ..screener import index_track
        out["ingested_index_track"] = store.get_meta(index_track.STORE_KEY) or None
    except Exception:
        out["ingested_index_track"] = None

    # THE CONTRACT-BOUND SERIES (LA2). Kept SEPARATE from `ingested_index_track` above rather
    # than replacing it: that key is what previous backups committed, and a restore reading an
    # older file must keep working. This one is the merged, authoritative view.
    try:
        out["bound_index_track"] = bound_series(store, *(bound_paths or (None, None)))
    except Exception as e:                                    # pragma: no cover - defensive
        # Never let the bound series take the whole backup down: the sandbox rows are still
        # worth committing. But say so loudly in the payload rather than emitting an empty
        # series that reads as "there is nothing to back up".
        out["bound_index_track"] = {"meta": {}, "series": [], "error": str(e),
                                    "sources": {}}

    out["counts"] = {
        "index_days": len(out["index_series"]),
        "index_holdings": len(out["index_holdings"]),
        "paper_orders": len(out["paper_orders"]),
        "paper_orders_closed": sum(1 for r in out["paper_orders"]
                                   if (r.get("state") or "") == "closed"),
        "option_alerts": len(out["option_alerts"]),
        "option_alerts_closed": sum(1 for r in out["option_alerts"]
                                    if (r.get("status") or "") == "closed"),
        "ingested_index_days": len(((out.get("ingested_index_track") or {})
                                    .get("series")) or []),
        # THE COUNT THE WORKFLOW GUARDS ON (LA2). Named for the contract, not for the engine,
        # because `index_days` above means the sandbox book and the two were already conflated
        # once in this file's own prose.
        "bound_index_days": len(((out.get("bound_index_track") or {}).get("series")) or []),
    }
    return out


# ------------------------------------------------------------------------------------------
# CSV views. Explicit column lists, not `row.keys()`: a column added to a table upstream must
# not silently reorder or widen a committed CSV, because that turns one real new field into a
# whole-file diff and hides whatever else changed that week.
# ------------------------------------------------------------------------------------------
_INDEX_COLS = ["as_of", "index_ret", "bench_ret", "active_ret",
               "n_positions", "n_priced", "inception"]
_HOLDING_COLS = ["ticker", "weight", "entry_date", "entry_price", "bench_entry_price",
                 "shares", "order_id", "note"]
#: Entry, exit and P&L for each contract. `alert_ts` is when the model spoke; `entry_ts` is
#: when the paper order filled. Both are kept — the gap between them is the part of a forward
#: record that a backtest cannot have.
_TRADE_COLS = ["alert_id", "ticker", "occ_symbol", "opt_right", "strike", "expiry",
               "contracts", "state", "alert_ts", "entry_ts", "entry_premium",
               "exit_ts", "exit_premium", "exit_reason", "pnl_pct", "pnl_dollars"]


def _trade_rows(pay: dict) -> list:
    """Join the paper broker's orders to the alerts that produced them.

    The two tables hold different halves of the same trade: `option_alerts` is what the model
    said (and carries the recomputed P&L — `record_outcome` derives it from the stored entry
    premium so the scorecard can never disagree with the prices it was logged against), while
    `paper_option_orders` is what the sandbox broker actually did. A backup that kept only one
    would lose either the claim or the fill.
    """
    alerts = {r.get("id"): r for r in pay.get("option_alerts") or []}
    rows = []
    for o in pay.get("paper_orders") or []:
        a = alerts.get(o.get("alert_id")) or {}
        rows.append({
            "alert_id": o.get("alert_id"), "ticker": o.get("ticker") or a.get("ticker"),
            "occ_symbol": o.get("occ_symbol") or a.get("occ_symbol"),
            "opt_right": a.get("opt_right"), "strike": a.get("strike"),
            "expiry": o.get("expiry") or a.get("expiry"),
            "contracts": o.get("contracts"), "state": o.get("state"),
            "alert_ts": a.get("alert_ts"), "entry_ts": o.get("entry_ts"),
            "entry_premium": o.get("entry_premium"), "exit_ts": o.get("exit_ts"),
            "exit_premium": o.get("exit_premium"), "exit_reason": o.get("exit_reason"),
            # P&L from the ALERT row, which is the one `record_outcome` recomputes.
            "pnl_pct": a.get("pnl_pct"), "pnl_dollars": a.get("pnl_dollars"),
        })
    # Closed alerts whose paper order never existed (e.g. outcomes written back by the Cowork
    # filler rather than placed in the sandbox) would otherwise be dropped from the backup.
    seen = {r["alert_id"] for r in rows}
    for a in pay.get("option_alerts") or []:
        if a.get("id") in seen or (a.get("status") or "") != "closed":
            continue
        rows.append({
            "alert_id": a.get("id"), "ticker": a.get("ticker"),
            "occ_symbol": a.get("occ_symbol"), "opt_right": a.get("opt_right"),
            "strike": a.get("strike"), "expiry": a.get("expiry"),
            "contracts": None, "state": "closed(no paper order)",
            "alert_ts": a.get("alert_ts"), "entry_ts": None,
            "entry_premium": a.get("entry_premium"), "exit_ts": a.get("exit_ts"),
            "exit_premium": a.get("exit_premium"), "exit_reason": a.get("exit_reason"),
            "pnl_pct": a.get("pnl_pct"), "pnl_dollars": a.get("pnl_dollars"),
        })
    rows.sort(key=lambda r: (str(r.get("alert_ts") or ""), str(r.get("alert_id") or "")))
    return rows


def _write_csv(path: str, cols: list, rows: list) -> None:
    # newline="" per the csv module's contract on Windows; without it every row gets a blank
    # line after it and the committed file double-spaces.
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c) for c in cols})


def write(pay: dict, out_dir: str = "data_export", merge_committed: bool = True) -> dict:
    """Write the payload to `out_dir`. Returns {filename: row_count}.

    `merge_committed` (default ON) folds any bound-series rows ALREADY committed in `out_dir`
    into the payload before writing anything. This is what makes the CI path safe: the
    workflow renders a payload fetched from a live service that may hold zero bound rows, and
    without this the render would faithfully overwrite the committed record with nothing. Pass
    False only to test the un-merged behaviour.
    """
    os.makedirs(out_dir, exist_ok=True)
    written = {}

    # MERGE BEFORE THE DUMP, so the JSON and the CSV cannot disagree about the same series.
    bound = dict(pay.get("bound_index_track") or {"meta": {}, "series": []})
    committed = read_bound_csv(os.path.join(out_dir, BOUND_INDEX_CSV)) if merge_committed else []
    bound["series"] = merge_bound_rows(committed, bound.get("series"))
    # DELIBERATELY NOT RECORDED IN THE ARTIFACT: how many rows the merge took from the
    # committed copy. It is 0 on a first write and N on every write after, so storing it makes
    # two runs of identical input differ — the exact churn `_PRECISION` exists to prevent, and
    # it broke this module's own idempotence promise the first time it was tested (LA2). The
    # merge is an operational fact and goes to the run log; `sources` keeps the provenance the
    # SERVICE saw, which is a property of the record and is stable.
    pay = dict(pay, bound_index_track=bound)
    pay["counts"] = dict(pay.get("counts") or {}, bound_index_days=len(bound["series"]))

    jpath = os.path.join(out_dir, "paper_track_history.json")
    with open(jpath, "w", encoding="utf-8") as f:
        # sort_keys so the committed JSON is stable across runs and Python versions.
        json.dump(pay, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    written["paper_track_history.json"] = 1

    trades = _trade_rows(pay)
    for name, cols, rows in (
            ("paper_track_index.csv", _INDEX_COLS, pay.get("index_series") or []),
            ("paper_track_trades.csv", _TRADE_COLS, trades),
            ("paper_track_holdings.csv", _HOLDING_COLS, pay.get("index_holdings") or []),
            (BOUND_INDEX_CSV, _BOUND_COLS, bound["series"])):
        _write_csv(os.path.join(out_dir, name), cols, rows)
        written[name] = len(rows)

    # The book that series is measured on, beside the series. Without it a restored CSV is a
    # column of numbers with no statement of what was held — and the 8% weight cap is exactly
    # what distinguishes the bound Index from the sandbox engine it kept being confused with.
    with open(os.path.join(out_dir, BOUND_INDEX_META), "w", encoding="utf-8") as f:
        json.dump({"what_this_is": ("The contract-bound Valquo Index: the book and inception "
                                    "PAPER_TRACK_CONTRACT.md binds. NOT the Tradier sandbox "
                                    "engine, whose files are named paper_track_*."),
                   "recorder": bound.get("recorder"), "book": bound.get("book"),
                   "sources": bound.get("sources") or {}, **(bound.get("meta") or {})},
                  f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    written[BOUND_INDEX_META] = 1

    _write_readme(out_dir)
    written["README.md"] = 1
    return written


def guard_counts(out_dir: str = "data_export") -> dict:
    """Row counts the anti-regression guard compares. Pure read.

    LA2: the guard used to count `paper_track_index.csv` — the SANDBOX book — so the one
    series the whole backup exists to protect could fall to zero rows without tripping it.
    Both are reported now, and the workflow fails on a regression in EITHER; but the bound
    count is the one the contract binds and it is named accordingly.
    """
    return {
        "bound_index_days": _csv_rows(os.path.join(out_dir, BOUND_INDEX_CSV)),
        "sandbox_index_days": _csv_rows(os.path.join(out_dir, "paper_track_index.csv")),
    }


def _csv_rows(path: str) -> int:
    """Data rows in a CSV, 0 if absent. Counts through the csv module, not `wc -l`, so an
    embedded newline inside a quoted field cannot inflate the count the guard trusts."""
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def _write_readme(out_dir: str) -> None:
    # A README next to the data, because a bare CSV found in a repo years later is a mystery.
    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(_README)


_README = """# data_export — backup of the forward paper track

**These files are a backup, not an input.** Nothing reads them; the live record lives in the
screener database on the Render service's persistent disk. They exist because that disk is the
only copy, and this record is the one thing in the project that cannot be re-derived: it is
what the model said on days that have already happened. Re-creating it later from current data
would produce a different object with the same column names.

Written by `python -m valuation.edge.track_export`, regenerated in full each run (idempotent —
same database in, byte-identical files out), and committed weekly by the `track-backup`
GitHub Actions workflow, which pulls them from the live service's `/admin/export-track`.

## TWO DIFFERENT BOOKS ARE BACKED UP HERE. THEY ARE NOT ONE TRACK RECORDED TWICE.

Read this before quoting any figure out of these files.

**The contract-bound Valquo Index** — `valquo_index_*` — is the record
`PAPER_TRACK_CONTRACT.md` binds: 86 names, score-weighted, capped at 8%, inception
2026-07-30. It is the ONLY series that may be cited as evidence under that contract, and
`index_track.vs_spy_claim()` is the only function allowed to make a vs-SPY statement from it.

**The Tradier sandbox engine** — `paper_track_*` — is a different book: 10 names,
equal-weighted at 10% each, inception 2026-08-03. Those 10% weights break the contract's own
8% cap, so **the sandbox is not the Index and may never be quoted as it.** On 2026-08-05 a
Discord recap printed the sandbox's numbers under the words "Valquo Index vs SPY" and claimed
the Index was beating SPY on a day the bound recorder had it 2.85pp behind.

| File | What |
|---|---|
| `valquo_index_track.csv` | **the contract-bound Index**, daily vs SPY, cumulative since inception |
| `valquo_index_meta.json` | that Index's inception, benchmark and 86-name book |
| `paper_track_history.json` | everything here, structured — the complete artifact |
| `paper_track_index.csv` | **the SANDBOX engine's** daily vs-SPY series — NOT the Index |
| `paper_track_trades.csv` | every paper option trade: entry, exit, reason, P&L |
| `paper_track_holdings.csv` | the sandbox book its daily series is measured from |

**Paper only.** Tradier sandbox fills on delayed quotes, entries at the ask and exits at the
bid. No real money and no real orders. It is a forward, out-of-sample record — which is the
one thing the backtest cannot claim — and it is thin, and thin records mean very little.

To restore the sandbox tables: read `paper_track_history.json` and re-insert into
`paper_index_track`, `paper_index_holdings`, `paper_option_orders` and `option_alerts`.
Column names in the JSON match the table columns exactly, which is why the JSON is stored raw
rather than summarised.

To restore the bound Index: copy `valquo_index_track.csv` to `data/valquo_track_history.csv`
and `valquo_index_meta.json` to `data/valquo_track.json`. The column names are deliberately
identical to the tracker's own, so this is a copy and not a transformation.

**Why the bound Index is committed here when `data/` is gitignored.** `data/` is ignored
because it holds the licensed Sharadar exports, which may not be redistributed. The bound
series is a different object: Valquo's own output, a few hundred bytes, derived and
unlicensed — and until 2026-08-10 it existed on exactly one laptop, with no writer anywhere
in this repository able to reproduce it. This copy is a BACKUP, never an input: nothing reads
it back, and `index_track.load()` still reads `data/` and only `data/`, so there is still
exactly one authority for what the Index did.

No secrets: market data, timestamps and sandbox order ids only.
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--out", default="data_export", help="output directory")
    ap.add_argument("--from-json", default=None,
                    help="read a payload produced by /admin/export-track instead of a local "
                         "database ('-' for stdin). This is how CI runs it.")
    ap.add_argument("--db", default=None, help="screener database path (default: config)")
    ap.add_argument("--no-merge-committed", action="store_true",
                    help="do NOT fold already-committed bound rows into the output. Refuses to "
                         "protect the record from an empty source; for tests only.")
    ap.add_argument("--guard-against", default=None, metavar="DIR",
                    help="after writing, fail if either index series has FEWER rows than the "
                         "copy in DIR (the committed version). This is the CI guard.")
    args = ap.parse_args(argv)

    if args.from_json:
        # utf-8-sig, not utf-8: `curl` writes the response raw and never adds a BOM, but this
        # flag also documents "a hand-saved response works", and a response saved by hand on
        # Windows (PowerShell's Out-File, Notepad) does carry one. utf-8-sig reads plain UTF-8
        # unchanged, so this can only accept input that would otherwise have crashed.
        raw = sys.stdin.read() if args.from_json == "-" else open(
            args.from_json, encoding="utf-8-sig").read()
        pay = json.loads(raw)
        # The endpoint wraps the payload; accept either shape so a hand-saved response works.
        pay = pay.get("export", pay)
    else:
        from ..screener.store import Store
        pay = payload(Store(args.db) if args.db else Store())

    written = write(pay, args.out, merge_committed=not args.no_merge_committed)
    counts = pay.get("counts") or {}
    # Counted off the FILES that were just written, not off the payload that was meant to
    # produce them. The bound count in particular is a merge result, so reporting the payload's
    # own figure would print the number the run intended rather than the number it achieved.
    on_disk = guard_counts(args.out)
    print(f"wrote {len(written)} files to {args.out}/")
    for k, v in sorted(written.items()):
        print(f"  {k}: {v} rows" if k.endswith(".csv") else f"  {k}")
    print(f"BOUND Valquo Index days: {on_disk['bound_index_days']}  "
          f"(sandbox engine days: {on_disk['sandbox_index_days']}, "
          f"closed option trades: {counts.get('option_alerts_closed', 0)})")
    if not on_disk["bound_index_days"]:
        # The LA2 failure, made loud. A backup that preserves the sandbox book and zero rows of
        # the contract-bound series is not a backup of the thing that cannot be re-derived, and
        # it looked like a healthy weekly job for months.
        print("WARNING: ZERO rows of the CONTRACT-BOUND Valquo Index were backed up. That is "
              "the series PAPER_TRACK_CONTRACT.md binds and the one thing here that cannot be "
              "re-derived. Check data/valquo_track_history.csv and the live service's "
              "index_track meta.", file=sys.stderr)
    if not any(counts.values()) and not on_disk["bound_index_days"]:
        print("WARNING: the track is EMPTY — nothing has been recorded yet, or this ran "
              "against the wrong database. A backup file was still written.", file=sys.stderr)

    if args.guard_against:
        old, new, bad = guard_counts(args.guard_against), on_disk, []
        for k in ("bound_index_days", "sandbox_index_days"):
            if new[k] < old[k]:
                bad.append(f"{k}: committed={old[k]} new={new[k]}")
        print(f"guard: committed={old} new={new}")
        if bad:
            print("ERROR: the new export has FEWER rows than the committed backup — "
                  + "; ".join(bad) + ". Refusing. The live record may have been reset; "
                  "investigate before overwriting.", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
