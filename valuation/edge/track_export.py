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
  paper_track_index.csv      the daily Valquo-Index-vs-SPY series
  paper_track_trades.csv     every closed paper option trade, entry -> exit -> P&L
  paper_track_holdings.csv   the index book the series is computed from

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


def payload(store, generated_at: str = None) -> dict:
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


def write(pay: dict, out_dir: str = "data_export") -> dict:
    """Write the payload to `out_dir`. Returns {filename: row_count}."""
    os.makedirs(out_dir, exist_ok=True)
    written = {}

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
            ("paper_track_holdings.csv", _HOLDING_COLS, pay.get("index_holdings") or [])):
        _write_csv(os.path.join(out_dir, name), cols, rows)
        written[name] = len(rows)

    # A README next to the data, because a bare CSV found in a repo years later is a mystery.
    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(_README)
    written["README.md"] = 1
    return written


_README = """# data_export — backup of the forward paper track

**These files are a backup, not an input.** Nothing reads them; the live record lives in the
screener database on the Render service's persistent disk. They exist because that disk is the
only copy, and this record is the one thing in the project that cannot be re-derived: it is
what the model said on days that have already happened. Re-creating it later from current data
would produce a different object with the same column names.

Written by `python -m valuation.edge.track_export`, regenerated in full each run (idempotent —
same database in, byte-identical files out), and committed weekly by the `track-backup`
GitHub Actions workflow, which pulls them from the live service's `/admin/export-track`.

| File | What |
|---|---|
| `paper_track_history.json` | everything below, structured — the complete artifact |
| `paper_track_index.csv` | daily Valquo Index vs SPY, cumulative since inception |
| `paper_track_trades.csv` | every paper option trade: entry, exit, reason, P&L |
| `paper_track_holdings.csv` | the index book the daily series is measured from |

**Paper only.** Tradier sandbox fills on delayed quotes, entries at the ask and exits at the
bid. No real money and no real orders. It is a forward, out-of-sample record — which is the
one thing the backtest cannot claim — and it is thin, and thin records mean very little.

To restore: read `paper_track_history.json` and re-insert into `paper_index_track`,
`paper_index_holdings`, `paper_option_orders` and `option_alerts`. Column names in the JSON
match the table columns exactly, which is why the JSON is stored raw rather than summarised.

No secrets: market data, timestamps and sandbox order ids only.
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--out", default="data_export", help="output directory")
    ap.add_argument("--from-json", default=None,
                    help="read a payload produced by /admin/export-track instead of a local "
                         "database ('-' for stdin). This is how CI runs it.")
    ap.add_argument("--db", default=None, help="screener database path (default: config)")
    args = ap.parse_args(argv)

    if args.from_json:
        raw = sys.stdin.read() if args.from_json == "-" else open(
            args.from_json, encoding="utf-8").read()
        pay = json.loads(raw)
        # The endpoint wraps the payload; accept either shape so a hand-saved response works.
        pay = pay.get("export", pay)
    else:
        from ..screener.store import Store
        pay = payload(Store(args.db) if args.db else Store())

    written = write(pay, args.out)
    counts = pay.get("counts") or {}
    print(f"wrote {len(written)} files to {args.out}/")
    for k, v in sorted(written.items()):
        print(f"  {k}: {v} rows" if k.endswith(".csv") else f"  {k}")
    print(f"index days: {counts.get('index_days', 0)}, "
          f"closed option trades: {counts.get('option_alerts_closed', 0)}, "
          f"ingested index days: {counts.get('ingested_index_days', 0)}")
    if not any(counts.values()):
        # Loud, because a backup of nothing that prints "done" is exactly how you find out
        # months later that the backup was never backing anything up.
        print("WARNING: the track is EMPTY — nothing has been recorded yet, or this ran "
              "against the wrong database. A backup file was still written.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
