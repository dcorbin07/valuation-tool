"""
The scream-buy record — logged fields, status vocabulary, and the ARCHIVED reset.

Don's direction, 2026-08-13 (`PROMPT_dip_detector_and_screamtrack.md` item 2): *"the options
scream buys track record wiped, and include target sale, price bought in, and current price,
same as our paper account tracks."* This module is the backend half. The rendering is the app
fixer's; the field names it consumes are `RECORD_FIELDS` below.

THREE THINGS THIS MODULE IS, AND ONE IT DELIBERATELY IS NOT.

1. THE RESET IS AN ARCHIVE, NEVER A DELETE, AND IT IS NOT EVEN AN OVERWRITE. A silent wipe of a
   track record is the one thing this project must never do. But "archive then delete" still
   destroys the rows, and a dated JSON file is a weaker object than a database row — it cannot be
   queried, joined or scored. So the reset stamps an EPOCH on the existing rows and starts a new
   one. Nothing is removed, `record_epoch` says which era a row belongs to, and the old record
   stays queryable forever. This is the same reasoning `paper_index_closed` already carries: rows
   leave a book when they do badly, so erasing them flatters the record.

2. THE STATUS IS DERIVED, NOT STORED — AND THAT IS A DEPARTURE FROM THE LITERAL ASK, MADE ON
   PURPOSE. The prompt asks for "a status field the close path maintains". The close path already
   maintains two fields the status is a pure function of (`status`, `exit_reason`), so storing a
   third would be a copy that can disagree with them — the B7 disease in miniature. Deriving also
   answers a case storing cannot: an alert whose contract simply EXPIRED with nobody closing it
   keeps `status='open'` forever, because no close path ever ran on it. A stored field would read
   LIVE for a contract that has not existed for months. `display_status` reads EXPIRED from the
   expiry date without needing anyone to have written anything.

3. CURRENT PRICE IS NEVER STORED. Don asked for it on the row and it is emitted on the row — but
   it is fetched at READ time and marked stale, never persisted. A stored "current" price is a
   price that was current once, and the moment it is written it begins lying. `attach_live_marks`
   is the read-time path; `LIVE_FIELDS` is what it adds. Nothing in this module writes them.

WHAT IT IS NOT: a second logger. `options_tracker.log_alert` still writes the row and
`notify.log_scream_buys` still calls it. This module adds the epoch, the vocabulary and the
archive around that existing write, and moves the exit-level arithmetic into one place.

ONE DERIVATION OF THE EXIT LEVELS. `levels_for` is the only place `target_premium` and
`stop_premium` are computed from a policy. `paper_track` had that arithmetic written out twice
(`_place_entry` inline, and `_levels_from`), which is how a corrected level and an uncorrected
one come to coexist — the exact defect session 16 found in this same file's exit levels.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Optional

from . import options_tracker as OT
from . import payload_schema as _schema

# The five statuses Don named, plus one honest fallback. A closed row whose reason maps to none
# of the five (`record_outcome` writes "no entry premium" for an unscoreable close) is reported
# as what it is rather than forced into a bucket it does not belong in.
STATUS_LIVE = "LIVE"
STATUS_HIT = "HIT TARGET"
STATUS_STOPPED = "STOPPED"
STATUS_TIME_STOPPED = "TIME-STOPPED"
STATUS_EXPIRED = "EXPIRED"
STATUS_CLOSED_OTHER = "CLOSED (unscoreable)"

ALL_STATUSES = (STATUS_LIVE, STATUS_HIT, STATUS_STOPPED, STATUS_TIME_STOPPED,
                STATUS_EXPIRED, STATUS_CLOSED_OTHER)

# `paper_track._exit_decision` returns exactly these four tokens; `record_outcome` may append a
# provenance suffix (audit B5d writes "... [pnl vs fill]"), so the reason is matched on its
# LEADING TOKEN and not by substring.
#
# ORDER IS NOT WHAT SAVES US HERE, EXACT MATCHING IS: "time_stop" CONTAINS "stop", so a
# substring test that checked "stop" first would report every time stop as a hard stop — a
# strategy that closed on schedule would be recorded as one that got stopped out. The two have
# opposite meanings for expectancy. `tests/test_scream_log.py` enumerates the tokens out of
# `paper_track`'s source and fails if a new one appears here unmapped.
EXIT_REASON_TO_STATUS = {
    "target": STATUS_HIT,
    "stop": STATUS_STOPPED,
    "time_stop": STATUS_TIME_STOPPED,
    "expiry": STATUS_EXPIRED,
}

# Meta keys on the store. The manifest is kept in the database as well as in the archive file so
# the tab footer can render "record reset <date>, N rows archived at <path>" without reading — or
# being able to find — the file itself, which lives on the service's own disk.
META_EPOCH = "scream_record_epoch"
META_ARCHIVES = "scream_record_archives"

# The epoch every row written before the first reset belongs to. Rows logged before this module
# existed have no `record_epoch` at all, and a NULL reads as this value rather than as "unknown":
# they are, precisely, the original record.
EPOCH_ORIGINAL = "original"

# The register note. Format fixed by Don's prompt and reproduced verbatim apart from the two
# substitutions, so the wording in the repo and the wording on the tab cannot drift.
REGISTER_NOTE = ("record reset {date} at Don's direction; prior record archived at {path}; "
                 "reason: predates the corrected alert stack (B1 price basis, C-series fixes) "
                 "and lacked entry/target/current fields")

# What `attach_live_marks` adds at read time. Named here so the app fixer consumes a constant
# rather than a list copied out of a docstring, and so a rename is one edit.
LIVE_FIELDS = ("current_premium", "current_premium_ts", "current_premium_stale",
               "current_premium_age_seconds", "current_premium_source", "pnl_pct_live")

# A quote older than this is rendered as stale. Fifteen minutes because the free provider is
# explicitly delayed and the sandbox goes quiet outside market hours; the point is that the
# reader is told, not that the number is withheld.
STALE_QUOTE_SECONDS = 15 * 60


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def _d(x) -> Optional[_dt.date]:
    try:
        return _dt.date.fromisoformat(str(x)[:10])
    except (TypeError, ValueError):
        return None


# ============================== schema ======================================================
def ensure_schema(store) -> None:
    """Add `record_epoch` to `option_alerts`, lazily, in this module.

    Deliberately NOT in `screener/store.py`, for the reason `paper_track.ensure_schema` already
    gives: several agents touch that shared schema concurrently, and a column that belongs to one
    feature should not force an edit there. A database created before this column simply has NULL
    in it, which `epoch_of` reads as the original record — the correct answer, since that is
    exactly what those rows are.
    """
    with store._conn() as c:
        cols = {r[1] for r in c.execute("PRAGMA table_info(option_alerts)").fetchall()}
        if "record_epoch" not in cols:
            c.execute("ALTER TABLE option_alerts ADD COLUMN record_epoch TEXT")
        c.execute("CREATE INDEX IF NOT EXISTS ix_option_alerts_epoch "
                  "ON option_alerts(record_epoch)")


def epoch_of(row: dict) -> str:
    """The epoch a row belongs to. NULL means the original record, never 'unknown'."""
    return str((row or {}).get("record_epoch") or EPOCH_ORIGINAL)


def current_epoch(store) -> str:
    """The epoch new alerts are written into. Untouched database => the original record."""
    try:
        return str(store.get_meta(META_EPOCH) or EPOCH_ORIGINAL)
    except Exception:                                                    # noqa: BLE001
        return EPOCH_ORIGINAL


# ============================== exit levels =================================================
def levels_for(entry_premium, policy: Optional[dict] = None) -> dict:
    """`target_premium` / `stop_premium` for an entry price on an exit policy.

    THE ONLY PLACE THIS ARITHMETIC LIVES. It returns {} for a missing or non-positive entry,
    because a target derived from no entry price is not a level, it is a fabrication — and the
    caller must be able to tell "no policy could be applied" from "the target happens to be 0".
    """
    px = _f(entry_premium)
    if px is None or px <= 0:
        return {}
    pol = policy or {}
    t = _f(pol.get("target_pct"))
    s = _f(pol.get("stop_pct"))
    t = OT.DEFAULT_TARGET_PCT if t is None else t
    s = OT.DEFAULT_STOP_PCT if s is None else s
    return {"target_premium": round(px * (1.0 + t), 4),
            "stop_premium": round(px * (1.0 + s), 4)}


def policy_of(row: dict) -> dict:
    """The alert's OWN exit policy from its logged `features`, defaulted when absent.

    The +100% target is a DEFAULT, not a constant: an alert that logged its own policy keeps it,
    which is the whole reason the policy is stored on the row rather than read from settings at
    display time. A later change of policy must not retroactively re-price old alerts.
    """
    feats = row.get("features") if isinstance(row, dict) else None
    try:
        feats = json.loads(feats) if isinstance(feats, str) else (feats or {})
    except (ValueError, TypeError):
        feats = {}
    pol = (feats or {}).get("exit_policy") if isinstance(feats, dict) else None
    pol = pol if isinstance(pol, dict) else {}
    out = {}
    for key, default in (("target_pct", OT.DEFAULT_TARGET_PCT),
                         ("stop_pct", OT.DEFAULT_STOP_PCT),
                         ("time_stop_frac", OT.DEFAULT_TIME_STOP_FRAC)):
        v = _f(pol.get(key))
        out[key] = default if v is None else v
    out["is_default"] = not pol
    return out


# ============================== status ======================================================
def _reason_token(exit_reason) -> Optional[str]:
    """The leading token of a stored `exit_reason`, or None.

    Exact-token matching rather than substring, for the "time_stop contains stop" reason given
    at `EXIT_REASON_TO_STATUS`.
    """
    if not exit_reason:
        return None
    raw = str(exit_reason).strip().lower()
    # `record_outcome` appends " [pnl vs fill]" (audit B5d); the reason itself is the head.
    head = raw.split("[")[0].strip()
    return head or None


def display_status(row: dict, today=None) -> str:
    """The status Don's table shows, derived from what the close path maintains.

    A pure function of (`status`, `exit_reason`, `expiry`) — see this module's docstring for why
    it is derived rather than stored. An OPEN row whose contract is past expiry reads EXPIRED:
    nothing closed it, but it is not live either, and reporting it as LIVE would leave dead
    contracts accumulating at the top of the table forever.
    """
    row = row or {}
    status = str(row.get("status") or "").strip().lower()
    if status == "closed":
        tok = _reason_token(row.get("exit_reason"))
        return EXIT_REASON_TO_STATUS.get(tok, STATUS_CLOSED_OTHER)
    exp = _d(row.get("expiry"))
    day = _d(today) or _dt.date.today()
    if exp is not None and exp < day:
        return STATUS_EXPIRED
    return STATUS_LIVE


def is_open(row: dict, today=None) -> bool:
    """Still awaiting an outcome. EXPIRED is not open, even when nothing closed it."""
    return display_status(row, today=today) == STATUS_LIVE


# ============================== the record ==================================================
# Every field the tab renders. Emitted as a constant so the app fixer consumes names rather than
# copying them, and so adding one is a single edit that the schema guard immediately checks.
RECORD_FIELDS = (
    "alert_id", "alert_ts", "ticker", "occ_symbol", "opt_right", "strike", "expiry",
    "entry_premium",            # "price bought in" — the alert-time premium
    "target_premium",           # "target sale"     — from the alert's OWN exit policy
    "stop_premium",
    "target_pct", "stop_pct", "policy_is_default",
    "dte_at_alert",             # DTE when the alert fired  (stored)
    "dte_remaining",            # DTE as of now             (derived, never stored)
    "status", "exit_reason", "exit_premium", "exit_ts", "pnl_pct",
    "record_epoch", "underlying_price", "score", "horizon", "contract_source",
)

# Stored columns deliberately NOT carried onto the display record, each with its reason. An
# entry without a reason should be read as a bug in this table, not a settled decision (M6).
_RECORD_ALLOW = {
    "id": "republished as `alert_id`, which is unambiguous across tables",
    "status": "republished as the derived display status; the raw open/closed is not shown",
    "dte": "republished as `dte_at_alert`, to keep it distinct from `dte_remaining`",
    "features": "unpacked into target_pct/stop_pct/policy_is_default/contract_source",
    "labels": "the alert's own text labels; the tab renders the fingerprint separately",
    "momentum_score": "sub-score; the tab shows the composite `score`",
    "technical_score": "sub-score; the tab shows the composite `score`",
    "iv": "fingerprint detail, not part of the track-record table",
    "iv_rank": "fingerprint detail, not part of the track-record table",
    "target_delta": "contract-selection detail, not part of the track-record table",
    "flow_read": "fingerprint detail, not part of the track-record table",
    "pnl_dollars": "the table reports pnl_pct; dollars depend on a sizing the record does not fix",
}


def alert_record(row: dict, today=None) -> dict:
    """One stored alert as the tab's row. No live quote — see `attach_live_marks`."""
    row = dict(row or {})
    pol = policy_of(row)
    entry = _f(row.get("entry_premium"))
    lv = levels_for(entry, pol)
    exp = _d(row.get("expiry"))
    day = _d(today) or _dt.date.today()
    feats = row.get("features")
    try:
        feats = json.loads(feats) if isinstance(feats, str) else (feats or {})
    except (ValueError, TypeError):
        feats = {}
    return {
        "alert_id": row.get("id"),
        "alert_ts": row.get("alert_ts"),
        "ticker": row.get("ticker"),
        "occ_symbol": row.get("occ_symbol"),
        "opt_right": row.get("opt_right"),
        "strike": _f(row.get("strike")),
        "expiry": row.get("expiry"),
        "entry_premium": entry,
        "target_premium": lv.get("target_premium"),
        "stop_premium": lv.get("stop_premium"),
        "target_pct": pol["target_pct"],
        "stop_pct": pol["stop_pct"],
        "policy_is_default": pol["is_default"],
        "dte_at_alert": row.get("dte"),
        "dte_remaining": ((exp - day).days if exp is not None else None),
        "status": display_status(row, today=day),
        "exit_reason": row.get("exit_reason"),
        "exit_premium": _f(row.get("exit_premium")),
        "exit_ts": row.get("exit_ts"),
        "pnl_pct": _f(row.get("pnl_pct")),
        "record_epoch": epoch_of(row),
        "underlying_price": _f(row.get("underlying_price")),
        "score": _f(row.get("score")),
        "horizon": row.get("horizon"),
        "contract_source": (feats or {}).get("contract_source"),
    }


def dropped_record_fields(row: dict, record: dict) -> list:
    """AUDIT M6, applied to this payload: stored columns the record silently loses.

    The guard iterates the columns the DATABASE actually returned, not a registry — an
    unregistered field is invisible to a registry-driven check, which is the whole finding of M3.
    So a column added to `option_alerts` by any lane shows up here until somebody decides, in a
    diff, whether the tab carries it.
    """
    return _schema.dropped_fields(row or {}, record or {},
                                  renames={"id": "alert_id", "dte": "dte_at_alert"},
                                  allow=_RECORD_ALLOW)


def records(store, epoch=None, limit: int = 500, today=None) -> list:
    """The tab's rows for one epoch (default: the current one), newest first.

    Raises `PayloadSchemaError` if the projection drops a stored column nobody has accounted for.
    Loud on purpose: the failure this guards against is a field being computed and thrown away,
    which is invisible precisely because everything still works.
    """
    ensure_schema(store)
    ep = epoch or current_epoch(store)
    with store._conn() as c:
        if ep == EPOCH_ORIGINAL:
            cur = c.execute("SELECT * FROM option_alerts WHERE COALESCE(record_epoch, ?) = ? "
                            "ORDER BY alert_ts DESC, id DESC LIMIT ?",
                            (EPOCH_ORIGINAL, EPOCH_ORIGINAL, int(limit)))
        else:
            cur = c.execute("SELECT * FROM option_alerts WHERE record_epoch = ? "
                            "ORDER BY alert_ts DESC, id DESC LIMIT ?", (ep, int(limit)))
        keys = [d[0] for d in cur.description]
        rows = [dict(zip(keys, r)) for r in cur.fetchall()]
    out = []
    for r in rows:
        rec = alert_record(r, today=today)
        missing = dropped_record_fields(r, rec)
        if missing:
            raise _schema.PayloadSchemaError(
                "scream-buy record drops stored column(s) nobody accounted for: "
                + ", ".join(missing)
                + " - carry them in RECORD_FIELDS/alert_record, or add a reason to _RECORD_ALLOW")
        out.append(rec)
    return out


# ============================== live marks (read time) ======================================
def attach_live_marks(recs, quotes: Optional[dict] = None, now=None) -> list:
    """Add the CURRENT premium from a live quote map. Read-time only; nothing is persisted.

    `quotes` is {occ_symbol: quote dict} exactly as `PaperBroker.quotes` returns — the same shape
    the paper track already marks against, so there is one quote convention and not two.

    A missing quote leaves the fields None and `current_premium_stale` True. Absent is not zero
    and it is not fresh: a row the market could not price must never render as a live price.
    """
    from .paper_broker import PaperBroker

    quotes = quotes or {}
    ts_now = now or _dt.datetime.now(_dt.timezone.utc)
    out = []
    for rec in recs or []:
        r = dict(rec)
        q = quotes.get(r.get("occ_symbol")) if r.get("occ_symbol") else None
        mark = PaperBroker.mark_from_quote(q) if q else None
        age = _quote_age_seconds(q, ts_now)
        r["current_premium"] = mark
        r["current_premium_ts"] = _quote_ts_iso(q)
        r["current_premium_age_seconds"] = age
        # Stale when the quote is old, when it carries no timestamp to judge, or when there is
        # no quote at all. Unknown age reads STALE rather than fresh: the failure that matters
        # is a months-old price rendered as today's.
        r["current_premium_stale"] = bool(mark is None or age is None
                                          or age > STALE_QUOTE_SECONDS)
        r["current_premium_source"] = ("live quote" if mark is not None else "unavailable")
        entry = _f(r.get("entry_premium"))
        r["pnl_pct_live"] = ((mark / entry - 1.0)
                             if (mark is not None and entry and entry > 0) else None)
        out.append(r)
    return out


def _quote_epoch_seconds(q) -> Optional[float]:
    """The freshest timestamp on a Tradier quote, in epoch SECONDS.

    Tradier reports `bid_date`/`ask_date`/`trade_date` in epoch MILLISECONDS. Reading those as
    seconds would date every quote to 1970 and mark it stale forever — which fails safe, but
    would make the staleness flag useless rather than informative.
    """
    if not isinstance(q, dict):
        return None
    best = None
    for k in ("bid_date", "ask_date", "trade_date"):
        v = _f(q.get(k))
        if v is None or v <= 0:
            continue
        secs = v / 1000.0 if v > 1e11 else v
        best = secs if best is None else max(best, secs)
    return best


def _quote_age_seconds(q, now) -> Optional[float]:
    secs = _quote_epoch_seconds(q)
    if secs is None:
        return None
    try:
        ts = _dt.datetime.fromtimestamp(secs, _dt.timezone.utc)
    except (ValueError, OSError, OverflowError):
        return None
    return max(0.0, (now - ts).total_seconds())


def _quote_ts_iso(q) -> Optional[str]:
    secs = _quote_epoch_seconds(q)
    if secs is None:
        return None
    try:
        return _dt.datetime.fromtimestamp(secs, _dt.timezone.utc).isoformat()
    except (ValueError, OSError, OverflowError):
        return None


def live_quotes_for(recs, broker=None) -> dict:
    """Fetch quotes for the open contracts in `recs`. Convenience for the read path.

    Only rows that are still LIVE are quoted — an expired or closed contract has no current
    price worth fetching, and quoting the whole record would grow one broker call per historical
    alert forever. Never raises: a quote outage degrades the table to stale marks, it does not
    take the tab down.
    """
    occs = sorted({r.get("occ_symbol") for r in (recs or [])
                   if r.get("occ_symbol") and r.get("status") == STATUS_LIVE})
    if not occs:
        return {}
    try:
        if broker is None:
            from .paper_broker import PaperBroker
            broker = PaperBroker()
        return broker.quotes(occs) or {}
    except Exception:                                                    # noqa: BLE001
        return {}


# ============================== archive + reset =============================================
def archive_payload(store, as_of=None) -> dict:
    """Every stored alert, with a manifest. The thing written to the dated archive file."""
    ensure_schema(store)
    with store._conn() as c:
        cur = c.execute("SELECT * FROM option_alerts ORDER BY id")
        keys = [d[0] for d in cur.description]
        rows = [dict(zip(keys, r)) for r in cur.fetchall()]
    day = str(as_of or _dt.date.today().isoformat())[:10]
    by_epoch = {}
    for r in rows:
        by_epoch[epoch_of(r)] = by_epoch.get(epoch_of(r), 0) + 1
    return {
        "archived_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "as_of": day,
        "n_rows": len(rows),
        "n_by_epoch": by_epoch,
        "n_by_status": _count_by_status(rows),
        "columns": keys if rows else [],
        "rows": rows,
    }


def _count_by_status(rows) -> dict:
    out = {}
    for r in rows:
        s = display_status(r)
        out[s] = out.get(s, 0) + 1
    return out


def archive_record(store, out_dir, as_of=None) -> dict:
    """Write the dated archive file. Returns its manifest. Never deletes, never overwrites.

    FAIL-CLOSED ON AN EXISTING FILE. Two resets on one day must not have the second silently
    replace the first's archive — that would destroy exactly the record this function exists to
    preserve. The second gets a `-2` suffix instead.
    """
    payload = archive_payload(store, as_of=as_of)
    os.makedirs(out_dir, exist_ok=True)
    base = f"scream_buys_archive_{payload['as_of']}"
    path = os.path.join(out_dir, base + ".json")
    n = 1
    while os.path.exists(path):
        n += 1
        path = os.path.join(out_dir, f"{base}-{n}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, default=str)
    return {"path": path, "n_rows": payload["n_rows"], "as_of": payload["as_of"],
            "n_by_status": payload["n_by_status"], "n_by_epoch": payload["n_by_epoch"],
            "archived_at": payload["archived_at"]}


def reset_record(store, out_dir, as_of=None, new_epoch=None) -> dict:
    """Archive the record, then start a new epoch. NOTHING IS DELETED.

    The rows stay in `option_alerts` with their old `record_epoch`, so the prior record remains
    queryable, scoreable and joinable — a dated JSON file alone would have been a downgrade.

    WHY THE ARCHIVE IS WRITTEN FIRST AND THE EPOCH ONLY MOVES IF IT SUCCEEDED: if the write
    raises, the reset has not happened and the record is untouched. The other order would leave
    a reset record with no archive, which is the silent wipe this whole design exists to prevent.
    """
    ensure_schema(store)
    day = str(as_of or _dt.date.today().isoformat())[:10]
    man = archive_record(store, out_dir, as_of=day)
    epoch = str(new_epoch or f"reset-{day}")
    with store._conn() as c:
        c.execute("UPDATE option_alerts SET record_epoch = COALESCE(record_epoch, ?) "
                  "WHERE record_epoch IS NULL", (EPOCH_ORIGINAL,))
    note = REGISTER_NOTE.format(date=day, path=man["path"])
    entry = dict(man, epoch_closed=EPOCH_ORIGINAL if man["n_by_epoch"].get(EPOCH_ORIGINAL)
                 else None, epoch_opened=epoch, note=note)
    try:
        prior = store.get_meta(META_ARCHIVES) or []
    except Exception:                                                    # noqa: BLE001
        prior = []
    store.set_meta(META_ARCHIVES, list(prior) + [entry])
    store.set_meta(META_EPOCH, epoch)
    return entry


def register_note(store) -> Optional[dict]:
    """The most recent reset's note + manifest, for the tab footer. None if never reset."""
    try:
        hist = store.get_meta(META_ARCHIVES) or []
    except Exception:                                                    # noqa: BLE001
        return None
    return dict(hist[-1]) if hist else None


DEFAULT_ARCHIVE_DIR = "data_export"


def _cli(argv=None) -> int:
    """`python -m valuation.edge.scream_log [--status | --archive | --reset]`.

    THE RESET IS NOT AUTOMATIC AND IS NOT RUN BY ANY SCAN. It is a deliberate, dated act on
    Don's direction, so it takes an explicit flag and prints what it did. `--status` is the safe
    default: it reads and changes nothing, which is what somebody checking the record wants.
    """
    import argparse

    from ..screener.store import Store

    p = argparse.ArgumentParser(description="Scream-buy record: inspect, archive, reset.")
    p.add_argument("--db", default=None, help="store path (default: the app's own)")
    p.add_argument("--out-dir", default=DEFAULT_ARCHIVE_DIR,
                   help=f"archive directory (default: {DEFAULT_ARCHIVE_DIR})")
    p.add_argument("--as-of", default=None, help="archive date (default: today)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--status", action="store_true", help="report the record (default)")
    g.add_argument("--archive", action="store_true", help="write an archive, do NOT reset")
    g.add_argument("--reset", action="store_true",
                   help="archive, then open a new epoch. Deletes nothing.")
    a = p.parse_args(argv)

    store = Store(a.db) if a.db else Store()
    if a.reset:
        man = reset_record(store, a.out_dir, as_of=a.as_of)
        print(json.dumps(man, indent=2, default=str))
        print("\nNOTHING WAS DELETED. The prior record is queryable at "
              f"epoch={man.get('epoch_closed') or EPOCH_ORIGINAL!r}.")
        return 0
    if a.archive:
        print(json.dumps(archive_record(store, a.out_dir, as_of=a.as_of), indent=2,
                         default=str))
        return 0
    print(json.dumps(record_summary(store), indent=2, default=str))
    return 0


def record_summary(store, today=None) -> dict:
    """What the tab needs beside the table: the epoch, the reset note, and the counts.

    `n_prior_epochs` is what makes a reset visible rather than merely honest — a record showing
    three rows reads very differently when the footer says 41 alerts sit in an earlier epoch.
    """
    ensure_schema(store)
    ep = current_epoch(store)
    with store._conn() as c:
        cur = c.execute("SELECT COALESCE(record_epoch, ?) AS e, COUNT(*) FROM option_alerts "
                        "GROUP BY COALESCE(record_epoch, ?)", (EPOCH_ORIGINAL, EPOCH_ORIGINAL))
        counts = {str(r[0]): int(r[1]) for r in cur.fetchall()}
    return {
        "epoch": ep,
        "n_current_epoch": counts.get(ep, 0),
        "n_prior_epochs": sum(v for k, v in counts.items() if k != ep),
        "n_by_epoch": counts,
        "reset": register_note(store),
        "statuses": list(ALL_STATUSES),
        "live_fields": list(LIVE_FIELDS),
        "stale_after_seconds": STALE_QUOTE_SECONDS,
    }


if __name__ == "__main__":                                   # pragma: no cover - entry point
    import sys as _sys

    _sys.exit(_cli())
