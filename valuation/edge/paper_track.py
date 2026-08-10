"""
The forward paper track — roadmap #12, the project's #1 remaining validation.

WHAT THIS IS FOR. Everything Valquo claims rests on data that has already been looked at: the
fundamental edge on ONE 18-year Sharadar panel, the options edge on ONE reconstructed alert
history. Both clear their internal bars, and neither has ever been tested on data nobody had
seen when the rules were fixed. A forward track starting today is the only thing that does
that, and its value comes entirely from being recorded honestly BEFORE the outcome is known.

WHAT IT DOES. Two books, both in Tradier's sandbox (`paper_broker.PaperBroker`, which refuses
any non-sandbox endpoint):

  * OPTIONS. Every new scream-buy alert the app logs with a real contract gets a paper
    buy_to_open. The position is marked daily and closed on the alert's OWN exit policy
    (+100% target / -50% stop / half-DTE time stop), and the close calls the EXISTING
    `options_tracker.record_outcome` with the paper fill. That is the whole point: the book
    has been sitting all-open since it was built because nothing fed it marks.
  * STOCKS. The Valquo Index book is held and marked against SPY over the SAME window per
    name, which is the methodology `edge/track.py` already uses, so the two records mean the
    same thing. Equity orders are OPT-IN (`place_equity=True`); by default the index is marked
    from sandbox quotes, because the index is a weights-and-returns claim and placing 86
    fractional-share-free orders adds rounding noise without testing anything.

WHAT IT DELIBERATELY DOES NOT DO.

  * It does not select contracts. The contract on the alert row is the one `options_live`
    already picked with the backtested selector; re-picking here would be the second
    implementation that module exists to prevent.
  * It does not compute P&L. `record_outcome` recomputes it from the stored entry premium, so
    the forward scorecard cannot silently disagree with the prices it was logged against.
  * It does not back-fill. `MAX_ALERT_AGE_DAYS` stops the first run from retro-submitting a
    backlog of old alerts at today's prices, which would manufacture a track record out of
    hindsight. Alerts older than the window are marked skipped, with the reason recorded.

IDEMPOTENCY AND RESUMABILITY. `paper_option_orders.alert_id` is a PRIMARY KEY and every alert
is CLAIMED (row inserted) before any order is sent, so two concurrent runs cannot both submit
one alert. If a run dies between placing and recording, the next run finds a claimed row with
no order id and ADOPTS the live broker order for that contract instead of sending a second one
(`_adopt_open_entry`). Every state transition is a single UPDATE on that row.

HONESTY OF THE NUMBERS. Sandbox quotes are ~15 minutes delayed, so fills and marks are
approximate — `paper_broker.DATA_CAVEAT` says so and it is carried into the API payload.
`summary()` labels the track "thin" until it clears `MIN_CLOSED_FOR_MEANING` closed options
trades / `MIN_DAYS_FOR_MEANING` days of index history, and while thin it explicitly says the
backtested expectancy remains the headline. A five-trade paper book is an anecdote and must
read as one.
"""
from __future__ import annotations

import datetime as _dt
import json
from typing import Optional

from ..config import CONFIG
from . import options_tracker as OT
from .paper_broker import DATA_CAVEAT, PaperBroker, now_iso, today_iso

# An alert older than this is NOT submitted. The forward track's only claim is that it was
# recorded before the outcome was known; buying a three-week-old signal at today's price
# quietly breaks that, and it is the single easiest way to fake this record.
MAX_ALERT_AGE_DAYS = 3

# Close this many calendar days before expiry rather than letting a long call expire. A
# position taken to expiry is decided by one day's move rather than by the strategy, and the
# backtest's time stop already closes well before then.
CLOSE_BEFORE_EXPIRY_DAYS = 2

# Evidence floors. Below these the track is reported as an anecdote, not a result.
MIN_CLOSED_FOR_MEANING = OT.MIN_CLOSED_PER_BUCKET      # 30 — same floor the scorecard tunes on
MIN_DAYS_FOR_MEANING = 126                             # ~6 months of index history

_STATES = ("claimed", "submitted", "open", "closing", "closed", "rejected", "skipped")

# Exit levels are stored rounded to 4dp, so two of them agree when they are within half a unit
# of the last place. Used only to decide whether a level needs repairing, never to trigger an
# exit: `_exit_decision` compares the mark to the level exactly, as it always has.
_LEVEL_TOL = 5e-5

# SESSION 16 (PT-SPLIT) — what a deliberately non-conforming book is stamped with, on the row.
EXPERIMENT_STAMP = ("REGISTERED EXPERIMENT - not the contract-bound Valquo Index and may never "
                    "be quoted as it (PAPER_TRACK_CONTRACT.md 5b)")


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


# ============================== schema =====================================================
def ensure_schema(store) -> None:
    """Create the paper-track tables. Lazily, in this module, on purpose.

    They belong to the paper track alone and nothing else in the app reads them, so keeping
    them here means the track can be added, changed or dropped without editing the screener's
    shared schema — which several other agents are concurrently touching.
    """
    with store._conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS paper_option_orders (
            alert_id INTEGER PRIMARY KEY,
            ticker TEXT, occ_symbol TEXT, expiry TEXT, contracts INTEGER,
            state TEXT NOT NULL DEFAULT 'claimed',
            entry_order_id TEXT, entry_premium REAL, entry_ts TEXT,
            target_premium REAL, stop_premium REAL, time_stop_date TEXT,
            last_mark REAL, last_mark_ts TEXT, last_mid REAL,
            exit_order_id TEXT, exit_premium REAL, exit_ts TEXT, exit_reason TEXT,
            note TEXT, created_at TEXT, updated_at TEXT)""")
        c.execute("CREATE INDEX IF NOT EXISTS ix_paper_orders_state "
                  "ON paper_option_orders(state)")
        # AUDIT B5a — `last_mark` is now the BID (what the position can be sold at, and what
        # the backtest triggers on); `last_mid` carries the mid alongside it for VALUATION.
        # Added by migration so an existing book is not dropped.
        _cols = {r[1] for r in c.execute("PRAGMA table_info(paper_option_orders)")}
        if "last_mid" not in _cols:
            c.execute("ALTER TABLE paper_option_orders ADD COLUMN last_mid REAL")
        # The index book. `bench_entry_price` is SPY on the day the name was added, so each
        # name is compared with the benchmark over ITS OWN window — the same construction
        # edge/track.py uses, rather than one inception date applied to later additions.
        c.execute("""CREATE TABLE IF NOT EXISTS paper_index_holdings (
            ticker TEXT PRIMARY KEY, weight REAL, entry_price REAL, bench_entry_price REAL,
            entry_date TEXT, shares REAL, order_id TEXT, note TEXT)""")
        # AUDIT P4 — a name that LEAVES the exported book must be sold. `seed_book` only ever
        # inserted, so the paper index was an ever-growing union of everything the screener had
        # ever liked: it stopped being the Valquo Index the day the first name dropped out, and
        # every session after that accumulated under rules no backtest describes.
        #
        # Departed names are CLOSED INTO THIS TABLE, never deleted. Deleting them would be the
        # more obvious repair and it would be reverse survivorship bias: names leave this book
        # when their composite decays, so erasing them removes disproportionately the ones that
        # did badly and silently flatters the track.
        #
        # A SEPARATE TABLE rather than a `status` column on the holdings, for one concrete
        # reason: `paper_index_holdings.ticker` is a PRIMARY KEY and the insert is
        # INSERT OR IGNORE, so a closed row left in place would make a name that RE-ENTERS the
        # book silently un-addable. Keying history on (ticker, entry_date) also lets one name
        # hold several separate stints, which is what a real book does.
        c.execute("""CREATE TABLE IF NOT EXISTS paper_index_closed (
            ticker TEXT, weight REAL, entry_price REAL, bench_entry_price REAL,
            entry_date TEXT, exit_price REAL, exit_bench_price REAL, exit_date TEXT,
            shares REAL, order_id TEXT, note TEXT,
            PRIMARY KEY (ticker, entry_date))""")
        c.execute("""CREATE TABLE IF NOT EXISTS paper_index_track (
            as_of TEXT PRIMARY KEY, index_ret REAL, bench_ret REAL, active_ret REAL,
            n_positions INTEGER, n_priced INTEGER, inception TEXT, detail TEXT)""")


def _row(store, alert_id):
    with store._conn() as c:
        cur = c.execute("SELECT * FROM paper_option_orders WHERE alert_id = ?", (alert_id,))
        r = cur.fetchone()
        if not r:
            return None
        return dict(zip([d[0] for d in cur.description], r))


def _update(store, alert_id, **fields) -> None:
    if not fields:
        return
    fields["updated_at"] = now_iso()
    sets = ", ".join(f"{k} = ?" for k in fields)
    with store._conn() as c:
        c.execute(f"UPDATE paper_option_orders SET {sets} WHERE alert_id = ?",
                  list(fields.values()) + [alert_id])


def paper_orders(store, states=None, limit: int = 1000) -> list:
    ensure_schema(store)
    sql = "SELECT * FROM paper_option_orders"
    args = []
    if states:
        sql += f" WHERE state IN ({','.join('?' * len(states))})"
        args = list(states)
    sql += " ORDER BY COALESCE(entry_ts, created_at) DESC LIMIT ?"
    args.append(int(limit))
    with store._conn() as c:
        cur = c.execute(sql, args)
        keys = [d[0] for d in cur.description]
        return [dict(zip(keys, r)) for r in cur.fetchall()]


# ============================== options: submit =============================================
def _features(alert: dict) -> dict:
    """The alert's logged `features` blob, however it arrived (JSON text or dict)."""
    try:
        feats = alert.get("features")
        feats = json.loads(feats) if isinstance(feats, str) else (feats or {})
        return feats if isinstance(feats, dict) else {}
    except (ValueError, TypeError, AttributeError):
        return {}


def _exit_policy(alert: dict) -> dict:
    """The alert's OWN exit policy, as logged. Defaults only when the row predates it."""
    pol = _features(alert).get("exit_policy") or {}
    return {"target_pct": _f(pol.get("target_pct")) if _f(pol.get("target_pct")) is not None
                          else OT.DEFAULT_TARGET_PCT,
            "stop_pct": _f(pol.get("stop_pct")) if _f(pol.get("stop_pct")) is not None
                        else OT.DEFAULT_STOP_PCT,
            "time_stop_frac": (_f(pol.get("time_stop_frac"))
                               if _f(pol.get("time_stop_frac")) is not None
                               else OT.DEFAULT_TIME_STOP_FRAC)}


def _alert_row(store, alert_id) -> dict:
    """The ORIGINATING alert row, by id.

    Needed because `paper_option_orders` carries no `features` column, so an order row cannot
    answer "what exit policy did this alert specify?" — see `_policy_for`.
    """
    if alert_id is None:
        return {}
    try:
        with store._conn() as c:
            cur = c.execute("SELECT * FROM option_alerts WHERE id = ?", (alert_id,))
            r = cur.fetchone()
            if not r:
                return {}
            return dict(zip([d[0] for d in cur.description], r))
    except Exception:                                                # noqa: BLE001
        return {}


def _policy_for(store, order_row: dict) -> dict:
    """The exit policy for an ORDER row, read from the alert it came from.

    SESSION 16 — this exists because `_exit_policy(dict(order_row))` is silently wrong.
    `paper_option_orders` has no `features` column (see `ensure_schema`), so handing it an order
    row makes `_features` return `{}` and the policy collapse to
    DEFAULT_TARGET_PCT / DEFAULT_STOP_PCT with no error. Audit B5c's comment claims the resume
    branch "rebuilds the exit policy the same way the fresh path does" — the fresh path reads the
    ALERT, the resume branch was reading the order, and for any alert whose policy differs from
    the default that is a different strategy, arrived at silently. Same failure family as B5c
    itself, one layer down. Falling back to the order row keeps the old behaviour when the alert
    has been purged, rather than losing the policy entirely.
    """
    return _exit_policy(_alert_row(store, order_row.get("alert_id")) or dict(order_row))


def _levels_from(store, order_row: dict, price) -> dict:
    """`target_premium` / `stop_premium` for an order row at `price`, on the alert's own policy."""
    px = _f(price)
    if px is None or px <= 0:
        return {}
    pol = _policy_for(store, order_row)
    return {"target_premium": round(px * (1.0 + (pol["target_pct"] or 0)), 4),
            "stop_premium": round(px * (1.0 + (pol["stop_pct"] or 0)), 4)}


def _sizing(alert: dict) -> dict:
    """The alert's OWN position sizing, as logged by `notify.py`."""
    sz = _features(alert).get("sizing")
    return sz if isinstance(sz, dict) else {}


def _eligible(alert: dict, today: _dt.date) -> tuple:
    """(ok, reason). A tradeable paper entry needs a real, unexpired, recent contract that the
    alert's own sizing did not refuse."""
    if not alert.get("occ_symbol"):
        return False, "no contract on the alert (chain unavailable when it fired)"
    exp = _d(alert.get("expiry"))
    if exp is None:
        return False, "no expiry"
    if (exp - today).days <= CLOSE_BEFORE_EXPIRY_DAYS:
        return False, "contract already at/past its expiry"
    ad = _d(alert.get("alert_ts"))
    if ad is None:
        return False, "unparseable alert timestamp"
    age = (today - ad).days
    if age > MAX_ALERT_AGE_DAYS:
        return False, (f"alert is {age} days old (>{MAX_ALERT_AGE_DAYS}); entering now would "
                       f"back-fill the track with hindsight")
    # SESSION 16 (routed as BUG 2 by the options-bot lane) — the alert's OWN sizing veto.
    # `notify.py` logs `features.sizing`, and `options_live` sets `skip: true` when the position
    # cannot be sized inside the risk budget; the product surfaces that as not-actionable. This
    # function tested only the contract, the expiry and the age, so the paper book bought names
    # the alert itself refused — ETN entered on a `skip: true` row whose reason was "one contract
    # costs $1,610, above the $1,000 budget" and became the LARGEST position in the book. A
    # forward track that takes trades the live product declines is not tracking the live product.
    #
    # The VETO is honoured; the QUANTITY deliberately is not. Reading `sizing.contracts` would
    # change the book's construction (position size), which is a different decision and is not
    # this repair's — see PREREG_session16_paper_track_repair.md §3.
    sz = _sizing(alert)
    if sz.get("skip"):
        why = str(sz.get("reason") or "").strip() or "no reason recorded on the alert"
        return False, f"the alert's own sizing refused this trade: {why}"
    return True, ""


def _adopt_open_entry(broker, occ: str) -> Optional[dict]:
    """Find an existing sandbox order for this contract, so a retry cannot double-submit.

    Only reached when a previous run claimed the alert and died before recording the order id.
    """
    try:
        for o in broker.orders():
            if (str(o.get("option_symbol") or "").upper() == str(occ).upper()
                    and str(o.get("side") or "") == "buy_to_open"
                    and str(o.get("status") or "").lower() not in ("canceled", "rejected",
                                                                   "expired")):
                return o
    except Exception:                                                # noqa: BLE001
        return None
    return None


def submit_new_alerts(store, broker: PaperBroker, cfg=CONFIG, limit: int = 25,
                      today=None) -> dict:
    """Place a paper buy_to_open for each new, tradeable scream-buy alert.

    Entry is a LIMIT at the current ASK, not the mid: `options_fill.DEFAULT_AGGRESSION = 1.0`
    is the punishing fill every validated options number in this repo is net of, and paying
    the mid forward would make the paper book beat the backtest for a reason that has nothing
    to do with the signal.
    """
    ensure_schema(store)
    day = _d(today) or _dt.date.today()
    n_contracts = max(1, int(getattr(cfg, "paper_contracts_per_trade", 1) or 1))
    out = {"considered": 0, "submitted": 0, "skipped": 0, "rejected": 0, "adopted": 0,
           "errors": [], "skips": []}

    known = {r["alert_id"] for r in paper_orders(store, limit=100000)}
    # Resume any row claimed by a run that died before it recorded an order id.
    #
    # AUDIT B5c — BOTH branches below used to leave `target_premium` and `stop_premium` NULL,
    # and the re-place branch additionally sent a MARKET order (no `price`). `_exit_decision`
    # reads those two columns, so a resumed position could never take profit and could never
    # stop out: it exited only on time or expiry. A crashed run silently converted trades into
    # a DIFFERENT STRATEGY, in the book whose entire purpose is to be comparable to the
    # backtest. Both branches now rebuild the price and the exit policy the same way the fresh
    # path does.
    # "pending" is the state a DRY RUN leaves behind (audit B5b) — it must be resumable,
    # or the preview has burned the alert by a different route than the one just fixed.
    for r in paper_orders(store, states=("claimed", "pending")):
        out["considered"] += 1
        _rq = broker.quotes([r["occ_symbol"]]).get(r["occ_symbol"]) if r.get("occ_symbol") else None
        _rask = _f((_rq or {}).get("ask"))
        # SESSION 16 — was `_exit_policy(dict(r))`, which reads `features` off an ORDER row that
        # has no such column and so silently returned the DEFAULT policy. See `_policy_for`.
        _rpol = _policy_for(store, r)
        existing = _adopt_open_entry(broker, r["occ_symbol"])
        if existing:
            _fields = {"state": "submitted",
                       "entry_order_id": str(existing.get("id") or ""),
                       "note": "adopted an order left by an interrupted run"}
            _rprice = _f(PaperBroker.fill_price(existing)) or _rask
            _rlv = _levels_from(store, r, _rprice)
            if _rlv:
                _fields.update(_rlv)
            else:
                _fields["note"] += " (NO exit levels: no usable price — audit B5c)"
            _update(store, r["alert_id"], **_fields)
            out["adopted"] += 1
            continue
        if _rask is None or _rask <= 0:
            # No quote: do NOT fall back to a market order with no exit levels. Leave the row
            # claimed so a later run can resume it properly.
            out["skipped"] += 1
            out["skips"].append({"alert_id": r["alert_id"], "ticker": r.get("ticker"),
                                 "reason": "resume deferred: no quote for the contract, and a "
                                           "market order with no target/stop is a different "
                                           "strategy (audit B5c)"})
            continue
        res = _place_entry(store, broker, r["alert_id"], r["ticker"], r["occ_symbol"],
                           n_contracts, price=_rask, policy=_rpol)
        out["submitted" if res else "rejected"] += 1

    for a in OT.open_alerts(store, limit=500):
        if a["id"] in known:
            continue
        out["considered"] += 1
        ok, why = _eligible(a, day)
        if not ok:
            _claim(store, a, n_contracts, state="skipped", note=why)
            out["skipped"] += 1
            out["skips"].append({"alert_id": a["id"], "ticker": a.get("ticker"), "reason": why})
            continue
        if out["submitted"] >= limit:
            break
        q = broker.quotes([a["occ_symbol"]]).get(a["occ_symbol"])
        ask = _f((q or {}).get("ask"))
        if ask is None or ask <= 0:
            # No two-sided market on the sandbox: leave the alert UNCLAIMED so a later run can
            # try again. This is a data gap, not a decision about the trade.
            out["skipped"] += 1
            out["skips"].append({"alert_id": a["id"], "ticker": a.get("ticker"),
                                 "reason": "no sandbox quote for the contract (not claimed; "
                                           "will retry next run)"})
            continue
        pol = _exit_policy(a)
        dte = _f(a.get("dte"))
        exp = _d(a.get("expiry"))
        if dte is None and exp is not None:
            dte = float((exp - day).days)
        ts_days = int(round((dte or 0) * (pol["time_stop_frac"] or 0.5)))
        _claim(store, a, n_contracts, state="claimed",
               time_stop_date=(day + _dt.timedelta(days=max(1, ts_days))).isoformat())
        if _place_entry(store, broker, a["id"], a.get("ticker"), a["occ_symbol"], n_contracts,
                        price=ask, policy=pol):
            out["submitted"] += 1
        else:
            out["rejected"] += 1
    return out


def _claim(store, alert: dict, contracts: int, state: str = "claimed", note: str = "",
           time_stop_date: Optional[str] = None) -> None:
    """Insert the claim row BEFORE any order is sent. The PK makes double-submit impossible."""
    with store._conn() as c:
        c.execute("""INSERT OR IGNORE INTO paper_option_orders
            (alert_id, ticker, occ_symbol, expiry, contracts, state, time_stop_date,
             note, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
                  (alert["id"], alert.get("ticker"), alert.get("occ_symbol"),
                   alert.get("expiry"), int(contracts), state, time_stop_date, note or None,
                   now_iso(), now_iso()))


def _place_entry(store, broker: PaperBroker, alert_id, ticker, occ, contracts,
                 price: Optional[float] = None, policy: Optional[dict] = None) -> bool:
    res = broker.place_option(occ, ticker, "buy_to_open", contracts, price=price)
    if not res.get("ok"):
        _update(store, alert_id, state="rejected",
                note=f"broker rejected the entry: {json.dumps(res.get('error'))[:280]}")
        return False
    oid = PaperBroker.order_id(res)
    fields = {"state": "submitted", "entry_order_id": oid, "entry_ts": now_iso()}
    if policy:
        px = _f(price)
        if px:
            fields["target_premium"] = round(px * (1.0 + (policy["target_pct"] or 0)), 4)
            fields["stop_premium"] = round(px * (1.0 + (policy["stop_pct"] or 0)), 4)
    if res.get("dry_run"):
        # A preview validated the order at the broker but created nothing. Record that
        # plainly instead of leaving a row that looks like a live position.
        #
        # AUDIT B5b — this used to write state="skipped", and skipped alerts are PERMANENTLY
        # excluded from the live track. So any alert a dry run happened to touch could never
        # enter the real book afterwards, silently and forever. A preview is a no-op: the row
        # goes back to the queue instead, and the note records that it was previewed.
        fields["state"] = "pending"
        fields["note"] = ("dry run - broker previewed and accepted the order; nothing placed. "
                          "Left PENDING so a real run can still take this alert (audit B5b).")
    _update(store, alert_id, **fields)
    return True


# ============================== options: mark ==============================================
def mark_open(store, broker: PaperBroker) -> dict:
    """Refresh entry fills and daily marks. This is what the book was missing entirely."""
    ensure_schema(store)
    out = {"filled": 0, "still_working": 0, "rejected": 0, "marked": 0, "errors": [],
           "levels_repaired": 0, "level_repairs": [], "level_repairs_deferred": []}

    for r in paper_orders(store, states=("submitted",)):
        try:
            o = broker.order(r["entry_order_id"]) if r.get("entry_order_id") else {}
        except Exception as e:                                       # noqa: BLE001
            out["errors"].append(f"{r['ticker']}: {type(e).__name__}")
            continue
        status = str(o.get("status") or "").lower()
        fill = PaperBroker.fill_price(o)
        if status == "filled" and fill:
            # SESSION 16 (routed as BUG 1) — the exit levels MUST be re-derived from the fill.
            # `_place_entry` anchors them to the price the order was SUBMITTED at; this branch
            # then overwrote `entry_premium` with the broker's actual fill and left the levels
            # alone, so the live target and stop described a price the book never paid. It is
            # systematic, not occasional: `auto-scan.yml` runs the cycle AFTER the close, the
            # limit is set from a post-close quote and the day order fills at the next open, so
            # the two prices routinely differ (2 of the first 3 fills were off spec — TGT ran a
            # +150.7% target against an intended +100%, MET a -46.7% stop against -50%).
            _update(store, r["alert_id"], state="open", entry_premium=fill,
                    entry_ts=o.get("transaction_date") or now_iso(),
                    **_levels_from(store, r, fill))
            out["filled"] += 1
        elif status in ("canceled", "rejected", "expired"):
            _update(store, r["alert_id"], state="rejected",
                    note=f"entry order ended {status} without a fill")
            out["rejected"] += 1
        else:
            out["still_working"] += 1

    # SESSION 16 — repair rows that were already open when the fix above landed.
    #
    # Fixing `mark_open`'s fill branch only protects FUTURE entries: the three positions the book
    # already held had passed through that branch weeks earlier and carry levels anchored to
    # their submit price forever. So the correct levels are re-derived here, every cycle, from
    # the stored fill and the alert's own policy. It is idempotent — a conforming row is skipped,
    # not rewritten — which also makes it a standing GUARD rather than a one-shot migration: if
    # any future path writes a level that disagrees with the fill, this repairs it and says so.
    #
    # A REPAIR MAY NOT EXECUTE A TRADE. If the corrected level is already crossed by the last
    # mark, the write is DEFERRED and reported in `level_repairs_deferred` instead, because
    # writing it would make the next `close_matured` sell the position — a bug fix silently
    # closing a live position is not a bug fix. That case needs a human, so it is surfaced in
    # `options_summary()` too rather than left in a cycle log nobody reads.
    for r in paper_orders(store, states=("open", "closing")):
        entry = _f(r.get("entry_premium"))
        want = _levels_from(store, r, entry) if entry else {}
        if not want:
            continue
        cur_t, cur_s = _f(r.get("target_premium")), _f(r.get("stop_premium"))
        if (cur_t is not None and abs(cur_t - want["target_premium"]) <= _LEVEL_TOL
                and cur_s is not None and abs(cur_s - want["stop_premium"]) <= _LEVEL_TOL):
            continue
        detail = {"alert_id": r["alert_id"], "ticker": r.get("ticker"), "entry_premium": entry,
                  "target_was": cur_t, "target_now": want["target_premium"],
                  "stop_was": cur_s, "stop_now": want["stop_premium"]}
        mark = _f(r.get("last_mark"))
        if mark is not None and (mark <= want["stop_premium"] or mark >= want["target_premium"]):
            detail["deferred_because"] = (
                f"the corrected level is already crossed by the last mark ({mark}); writing it "
                f"would close this position on the next cycle. Needs a decision, not a repair.")
            out["level_repairs_deferred"].append(detail)
            continue
        _update(store, r["alert_id"], **want,
                note=(f"session 16: exit levels re-derived from the FILL ({entry}) on the "
                      f"alert's own policy; they had been anchored to the submit price"))
        out["levels_repaired"] += 1
        out["level_repairs"].append(detail)

    live = paper_orders(store, states=("open", "closing"))
    if live:
        quotes = broker.quotes([r["occ_symbol"] for r in live if r.get("occ_symbol")])
        for r in live:
            _q = quotes.get(r.get("occ_symbol"))
            # AUDIT B5a — `last_mark` is what `_exit_decision` compares against target/stop, so
            # it must be the price this long position could actually be SOLD at: the BID, which
            # is what the backtest triggers on. Marking at the mid reached +100% earlier and
            # -50% later than the backtest would, by roughly 5pp on a 10%-wide quote — a
            # systematic difference on exactly the axis the forward track exists to test.
            # The mid is kept alongside it for VALUING the position, which is a different job.
            mark = PaperBroker.exit_mark_from_quote(_q)
            mid = PaperBroker.mark_from_quote(_q)
            if mark is not None:
                _update(store, r["alert_id"], last_mark=mark, last_mark_ts=now_iso(),
                        last_mid=mid)
                out["marked"] += 1
    return out


# ============================== options: close =============================================
def _exit_decision(row: dict, today: _dt.date) -> Optional[str]:
    """Which exit rule (if any) fires. Order matters: a hard stop beats a soft time stop."""
    mark = _f(row.get("last_mark"))
    target, stop = _f(row.get("target_premium")), _f(row.get("stop_premium"))
    if mark is not None:
        if stop is not None and mark <= stop:
            return "stop"
        if target is not None and mark >= target:
            return "target"
    exp = _d(row.get("expiry"))
    if exp is not None and (exp - today).days <= CLOSE_BEFORE_EXPIRY_DAYS:
        return "expiry"
    tsd = _d(row.get("time_stop_date"))
    if tsd is not None and today >= tsd:
        return "time_stop"
    return None


def close_matured(store, broker: PaperBroker, today=None) -> dict:
    """Sell to close on the alert's exit policy, then hand the fill to `record_outcome`.

    The exit is a LIMIT at the current BID for the same reason the entry is at the ask: sell
    the bid is the fill convention the validated numbers assume.
    """
    ensure_schema(store)
    day = _d(today) or _dt.date.today()
    out = {"closed": 0, "closing": 0, "recorded": 0, "errors": [], "exits": []}

    # 1) Positions whose exit order is already working — finish them if they filled.
    for r in paper_orders(store, states=("closing",)):
        try:
            o = broker.order(r["exit_order_id"]) if r.get("exit_order_id") else {}
        except Exception as e:                                       # noqa: BLE001
            out["errors"].append(f"{r['ticker']}: {type(e).__name__}")
            continue
        fill = PaperBroker.fill_price(o)
        status = str(o.get("status") or "").lower()
        if status == "filled" and fill:
            if _record(store, r, fill, r.get("exit_reason") or "exit", out):
                out["closed"] += 1
        elif status in ("canceled", "rejected", "expired"):
            # The exit could not be worked. Fall back to the last mark so the trade is scored
            # rather than left open forever — recorded with a reason that says which happened.
            mark = _f(r.get("last_mark"))
            if mark is not None and _record(store, r, mark,
                                            f"{r.get('exit_reason') or 'exit'} (marked; exit "
                                            f"order {status})", out):
                out["closed"] += 1
            else:
                _update(store, r["alert_id"], state="open",
                        note=f"exit order {status}; will retry")
        else:
            out["closing"] += 1

    # 2) Open positions that have hit a rule.
    for r in paper_orders(store, states=("open",)):
        reason = _exit_decision(r, day)
        if not reason:
            continue
        q = broker.quotes([r["occ_symbol"]]).get(r["occ_symbol"]) if r.get("occ_symbol") else None
        bid = _f((q or {}).get("bid"))
        # AUDIT B5 (lesser) — a missing bid used to send price=None, i.e. a MARKET order, which
        # is outside the stated ask-in / bid-out convention every validated options number in
        # this repo is net of. If there is no bid there is no two-sided market and no defensible
        # exit price; defer to the next run rather than take an unmodelled fill.
        if not (bid and bid > 0):
            _update(store, r["alert_id"],
                    note=f"{reason} deferred: no bid, and a market order is outside the "
                         f"bid-out convention (audit B5)")
            out.setdefault("deferred_no_bid", 0)
            out["deferred_no_bid"] += 1
            continue
        res = broker.place_option(r["occ_symbol"], r["ticker"], "sell_to_close",
                                  int(r.get("contracts") or 1), price=bid)
        if not res.get("ok"):
            # A rejected exit still has to produce a number, or a losing trade could sit open
            # forever and quietly flatter the closed-trade statistics.
            mark = _f(r.get("last_mark"))
            if mark is not None and _record(store, r, mark, f"{reason} (marked; exit rejected)",
                                            out):
                out["closed"] += 1
            else:
                _update(store, r["alert_id"],
                        note=f"exit rejected and no mark available: "
                             f"{json.dumps(res.get('error'))[:200]}")
            continue
        if res.get("dry_run"):
            out["exits"].append({"ticker": r["ticker"], "reason": reason, "dry_run": True})
            continue
        _update(store, r["alert_id"], state="closing", exit_reason=reason,
                exit_order_id=PaperBroker.order_id(res))
        out["closing"] += 1
        out["exits"].append({"ticker": r["ticker"], "reason": reason})
    return out


def _record(store, row: dict, exit_premium: float, reason: str, out: dict) -> bool:
    """Close the paper row AND write the outcome through the existing tracker."""
    # AUDIT B5d — hand over the price actually PAID at the broker. Without it `record_outcome`
    # computes the return against the ALERT-TIME ASK and the paper fill is decorative.
    ok = OT.record_outcome(store, alert_id=row["alert_id"], exit_premium=exit_premium,
                           exit_ts=now_iso(), exit_reason=reason,
                           contracts=int(row.get("contracts") or 1),
                           entry_premium=_f(row.get("entry_premium")))
    _update(store, row["alert_id"], state="closed", exit_premium=exit_premium,
            exit_ts=now_iso(), exit_reason=reason,
            note=None if ok else "DESYNC: record_outcome did not match an open alert — this "
                                 "paper row is closed but the scorecard has no outcome for it "
                                 "(audit B5)")
    if ok:
        out["recorded"] += 1
    else:
        out.setdefault("desynced", 0)
        out["desynced"] += 1
    # AUDIT B5 — this used to `return True` unconditionally, so a failed write looked identical
    # to a successful one and the two tables drifted apart in silence.
    return ok


def run_options_cycle(store, broker: PaperBroker, cfg=CONFIG, limit: int = 25,
                      today=None) -> dict:
    """Submit -> mark -> close, in that order.

    Order matters. Marking before closing means the close decision uses TODAY's mark rather
    than yesterday's, and submitting first means a contract alerted this morning is marked in
    the same run rather than a day later.
    """
    res = {"submitted": submit_new_alerts(store, broker, cfg=cfg, limit=limit, today=today)}
    res["marked"] = mark_open(store, broker)
    res["closed"] = close_matured(store, broker, today=today)
    return res


# ============================== the index book =============================================
def _bench_price(broker: PaperBroker, symbol: str = "SPY") -> Optional[float]:
    q = broker.quotes([symbol]).get(symbol)
    return _f((q or {}).get("last")) or PaperBroker.mark_from_quote(q)


# A book that has shrunk below this fraction of the current open holdings is treated as a
# FAILED EXPORT rather than a real rebalance, and closes nothing. Deliberately loose: real
# book sizes move with the universe, and the job of this number is to catch a truncated file,
# not to police ordinary turnover.
MIN_BOOK_RETENTION = 0.5


def _close_departed(store, broker: PaperBroker, gone, day: str) -> dict:
    """Mark names that have left the book as sold, at today's price and today's benchmark.

    The exit legs are stored so a closed position keeps a COMPLETE record — entry price, entry
    benchmark, exit price, exit benchmark — and its realised return against SPY over its own
    window stays computable forever. A row with no exit price would be indistinguishable from
    an open one after the fact.
    """
    quotes = broker.quotes(list(gone))
    bench = _bench_price(broker)
    closed, unpriced = [], []
    for t in gone:
        px = _f((quotes.get(t) or {}).get("last")) or PaperBroker.mark_from_quote(quotes.get(t))
        if px is None or px <= 0:
            # Left OPEN on purpose. Closing at an unknown price would either invent a number or
            # write a NULL exit that silently reads as a zero return later; it closes on the
            # next run that can price it.
            unpriced.append(t)
            continue
        with store._conn() as c:
            cur = c.execute("SELECT * FROM paper_index_holdings WHERE ticker = ?", (t,))
            row = cur.fetchone()
            if not row:
                continue
            h = dict(zip([d[0] for d in cur.description], row))
            # Insert the history row BEFORE dropping the live one, so a crash between the two
            # leaves a name double-counted rather than erased. An over-counted position is
            # visible in the next reconciliation; a vanished one is not recoverable.
            c.execute("""INSERT OR REPLACE INTO paper_index_closed
                (ticker, weight, entry_price, bench_entry_price, entry_date, exit_price,
                 exit_bench_price, exit_date, shares, order_id, note)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                      (t, h.get("weight"), h.get("entry_price"), h.get("bench_entry_price"),
                       h.get("entry_date"), px, bench, day, h.get("shares"), h.get("order_id"),
                       (h.get("note") or "") + f" | left the book {day}"))
            c.execute("DELETE FROM paper_index_holdings WHERE ticker = ?", (t,))
        closed.append(t)
    return {"closed": len(closed), "closed_tickers": closed, "close_unpriced": unpriced}


def book_conformance(book: dict) -> dict:
    """Does this payload describe the contract-bound Valquo Index, or a different book?

    SESSION 16 (PT-SPLIT). Delegates to `valquo_index.conformance` rather than re-deriving the
    rule, so there is one definition of "is this the Index" in the project. Falls back to
    measuring the positions directly when the payload predates the block.

    FAILS CLOSED: anything unreadable is NOT conforming, because the error this must never make
    is admitting a book it could not check.
    """
    try:
        from . import valquo_index as VI
        blk = (book or {}).get("contract_conformance")
        if isinstance(blk, dict) and "conforms" in blk:
            return blk
        positions = (book or {}).get("positions") or []
        cap = _f(((book or {}).get("criteria") or {}).get("effective_max_weight"))
        if cap is None:
            weights = [_f(p.get("weight")) or 0.0 for p in positions]
            cap = max(weights) if weights else 1.0
        return VI.conformance(len(positions), cap)
    except Exception as e:                                           # noqa: BLE001 - fail closed
        return {"conforms": False, "n_positions": None, "why_not":
                [f"conformance unreadable: {type(e).__name__}"]}


def seed_book(store, broker: PaperBroker, book: dict, place_equity: bool = False,
              capital: float = 100000.0, today=None, close_exits: bool = True,
              experiment: bool = False) -> dict:
    """Take the exported Valquo Index and hold it in the paper account.

    Names already held are LEFT ALONE — a re-run must not reset an entry price and wipe the
    accrued return. New names enter at today's price with today's SPY as their benchmark
    entry, so each position is compared with SPY over its own window.

    NAMES THAT HAVE LEFT THE BOOK ARE SOLD [AUDIT P4]. Until this was fixed the function only
    ever inserted, so a name entered once and was held forever: the paper index drifted into an
    ever-growing union of everything the screener had ever liked, which is not the strategy any
    backtest describes. Exits are CLOSED, not deleted — see `ensure_schema` for why deleting
    them would be reverse survivorship bias.

    `close_exits=False` restores the old accumulate-only behaviour for anyone who needs to
    reproduce a historical run. It is not the default, because the old behaviour is the bug.

    THE GUARD ON THE CLOSE. A truncated or failed export is indistinguishable from a genuinely
    smaller book at this layer, and acting on one would liquidate a real track. So a book that
    has shrunk to less than `MIN_BOOK_RETENTION` of the current open holdings closes NOTHING
    and says so in `close_refused`. That is a sanity check, not a silenced one: the run reports
    the refusal and the reason rather than proceeding quietly.

    `place_equity` mirrors the book as sandbox equity orders. Off by default: the index is a
    weights-and-returns claim, and whole-share rounding on an 8%-capped 86-name book adds
    tracking error that tests nothing about the signal.
    """
    ensure_schema(store)
    day = (_d(today) or _dt.date.today()).isoformat()
    positions = (book or {}).get("positions") or []
    conf = book_conformance(book)
    out = {"held": 0, "added": 0, "unpriced": [], "orders": 0, "place_equity": place_equity,
           "closed": 0, "closed_tickers": [], "close_refused": None,
           "conformance": conf, "experiment": bool(experiment), "seed_refused": None}
    if not positions:
        out["error"] = "the exported book has no positions"
        return out

    # SESSION 16 (PT-SPLIT) — THE ALIGNMENT GATE.
    #
    # `/admin/run-paper-track` reads `data/valquo_index.json` if it exists and otherwise rebuilds
    # from the STORE's latest scan. That fallback is silent and it is how the engine came to
    # record a 10-name book while the published Index held 86: the store's eligible large-cap
    # tier is under 100 names, so `n` clamps to `MIN_NAMES`. The two recorders were then read as
    # one track (`PT-OUTBOUND`: a Discord recap quoted the engine's +0.18pp while the bound
    # recorder read -2.85pp).
    #
    # So a book that is not the Index may not be seeded as if it were. The refusal is LOUD and
    # the run continues — `index_point` still marks whatever is already held — because silently
    # liquidating a live sandbox book on a conformance rule would be worse than the split.
    #
    # `experiment=True` is the ONLY other way through, and it stamps every row it creates. There
    # is no third state: a book is the Index, or it is a registered experiment that may never be
    # quoted as the Index.
    if not conf.get("conforms") and not experiment:
        out["seed_refused"] = (
            "this book is not the contract-bound Valquo Index, so it was NOT seeded: "
            + "; ".join(conf.get("why_not") or ["no reason recorded"])
            + ". Pass experiment=True to record it deliberately as a separate experiment.")
        return out

    with store._conn() as c:
        existing = {r[0] for r in c.execute("SELECT ticker FROM paper_index_holdings")}
    out["held"] = len(existing)
    target = {p["ticker"] for p in positions if p.get("ticker")}

    if close_exits:
        gone = sorted(existing - target)
        if gone and len(target) < MIN_BOOK_RETENTION * len(existing):
            out["close_refused"] = (
                f"exported book has {len(target)} names against {len(existing)} open holdings "
                f"(<{MIN_BOOK_RETENTION:.0%}); a truncated export looks exactly like a shrunken "
                f"book here, so nothing was closed")
        elif gone:
            out.update(_close_departed(store, broker, gone, day))

    fresh = [p for p in positions if p.get("ticker") and p["ticker"] not in existing]
    if not fresh:
        return out

    bench = _bench_price(broker)
    quotes = broker.quotes([p["ticker"] for p in fresh])
    for p in fresh:
        t = p["ticker"]
        px = _f((quotes.get(t) or {}).get("last")) or PaperBroker.mark_from_quote(quotes.get(t))
        if px is None or px <= 0:
            out["unpriced"].append(t)
            continue
        w = _f(p.get("weight")) or 0.0
        shares, oid = None, None
        if place_equity and w > 0:
            shares = int((capital * w) // px)
            if shares > 0:
                res = broker.place_equity(t, "buy", shares)
                oid = PaperBroker.order_id(res) if res.get("ok") else None
                if oid:
                    out["orders"] += 1
        with store._conn() as c:
            note = "quote-marked" if not place_equity else "equity order placed"
            if experiment:
                # Stamped on the ROW, not just returned to the caller: a label a surface can
                # decline to show is not a safeguard (the PT-OUTBOUND lesson).
                note += f" | {EXPERIMENT_STAMP}"
            c.execute("""INSERT OR IGNORE INTO paper_index_holdings
                (ticker, weight, entry_price, bench_entry_price, entry_date, shares, order_id,
                 note) VALUES (?,?,?,?,?,?,?,?)""",
                      (t, w, px, bench, day, shares, oid, note))
        out["added"] += 1
    return out


def index_point(store, broker: PaperBroker, today=None) -> dict:
    """Append today's Index-vs-SPY point. Idempotent per day (PK on `as_of`).

    Per-name return vs SPY over the SAME window, weight-averaged — the identical construction
    `edge/track.py` uses for the hot-list track, so the two records are directly comparable.
    """
    ensure_schema(store)
    day = (_d(today) or _dt.date.today()).isoformat()
    with store._conn() as c:
        cur = c.execute("SELECT * FROM paper_index_holdings")
        keys = [d[0] for d in cur.description]
        holds = [dict(zip(keys, r)) for r in cur.fetchall()]
    if not holds:
        return {"ok": False, "reason": "no index holdings seeded yet"}

    bench_now = _bench_price(broker)
    quotes = broker.quotes([h["ticker"] for h in holds])
    num_i, num_b, wsum, priced = 0.0, 0.0, 0.0, 0
    for h in holds:
        p0, b0 = _f(h.get("entry_price")), _f(h.get("bench_entry_price"))
        q = quotes.get(h["ticker"])
        p1 = _f((q or {}).get("last")) or PaperBroker.mark_from_quote(q)
        w = _f(h.get("weight")) or 0.0
        # BOTH legs or NEITHER. A name priced on one side only would move the index return
        # without moving the benchmark it is measured against, which is how a tracking record
        # quietly acquires alpha that is really a missing quote.
        if not (p0 and p1 and b0 and bench_now and w > 0):
            continue
        num_i += w * (p1 / p0 - 1.0)
        num_b += w * (bench_now / b0 - 1.0)
        wsum += w
        priced += 1
    if wsum <= 0:
        return {"ok": False, "reason": "no position could be priced against the benchmark"}

    idx_ret, bench_ret = num_i / wsum, num_b / wsum
    # AUDIT P4 — inception spans CLOSED stints too. Taking the minimum over open holdings only
    # would walk the track's start date forward every time the oldest position left the book,
    # so a record would appear to get younger the longer it ran.
    with store._conn() as c:
        _first_closed = c.execute(
            "SELECT MIN(entry_date) FROM paper_index_closed").fetchone()[0]
    inception = min([h.get("entry_date") or day for h in holds]
                    + ([_first_closed] if _first_closed else []))
    detail = {"weight_priced": round(wsum, 4), "n_holdings": len(holds),
              "bench": "SPY", "data_caveat": DATA_CAVEAT,
              # The daily point is a snapshot of OPEN holdings. A closed stint's realised
              # return is preserved in `paper_index_closed` and reported by index_summary, but
              # it does not feed this series — stated here so the limitation travels with the
              # number rather than being inferred from the schema. Chaining realised stints
              # into the series is a construction change, not a bug fix, and was not made.
              "scope": "open holdings only; closed stints in index_summary.realized"}
    with store._conn() as c:
        c.execute("""INSERT INTO paper_index_track
            (as_of, index_ret, bench_ret, active_ret, n_positions, n_priced, inception, detail)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(as_of) DO UPDATE SET index_ret=excluded.index_ret,
              bench_ret=excluded.bench_ret, active_ret=excluded.active_ret,
              n_positions=excluded.n_positions, n_priced=excluded.n_priced,
              detail=excluded.detail""",
                  (day, idx_ret, bench_ret, idx_ret - bench_ret, len(holds), priced,
                   inception, json.dumps(detail)))
    return {"ok": True, "as_of": day, "index_ret": idx_ret, "bench_ret": bench_ret,
            "active_ret": idx_ret - bench_ret, "n_positions": len(holds), "n_priced": priced,
            "inception": inception}


# ============================== the read model =============================================
def _label(inception: Optional[str], n_closed: int, n_days: int) -> str:
    """The honest one-liner shown wherever this track is quoted."""
    since = f"since {inception}" if inception else "not started"
    thin = n_closed < MIN_CLOSED_FOR_MEANING or n_days < MIN_DAYS_FOR_MEANING
    return (f"paper (Tradier sandbox), {since}"
            + (", thin - not yet a result" if thin else ", sample now meaningful"))


def held_book_conformance(store) -> dict:
    """Conformance of the book the engine is ACTUALLY HOLDING, measured from the holdings.

    SESSION 16 (PT-SPLIT). `seed_book`'s gate describes the payload that was offered; this
    describes what is on the books, which is the thing every surface reads. They can differ —
    the four days recorded before the gate existed are exactly that case — so the answer is
    measured from the rows rather than remembered from a seed run.
    """
    try:
        from . import valquo_index as VI
        with store._conn() as c:
            rows = list(c.execute("SELECT weight, note FROM paper_index_holdings"))
        if not rows:
            return {"conforms": None, "n_positions": 0,
                    "why_not": ["no holdings yet - nothing to conform"]}
        weights = [float(w or 0.0) for w, _ in rows]
        conf = VI.conformance(len(rows), max(weights) if weights else 1.0)
        conf["registered_experiment"] = any(EXPERIMENT_STAMP in (n or "") for _, n in rows)
        conf["registered_as"] = ("the contract-bound Valquo Index" if conf["conforms"]
                                 else "a registered experiment - NEVER quotable as the Index")
        return conf
    except Exception as e:                                           # noqa: BLE001 - fail closed
        return {"conforms": False, "why_not": [f"unreadable: {type(e).__name__}"],
                "registered_as": "a registered experiment - NEVER quotable as the Index"}


def index_summary(store) -> dict:
    ensure_schema(store)
    with store._conn() as c:
        cur = c.execute("SELECT * FROM paper_index_track ORDER BY as_of")
        keys = [d[0] for d in cur.description]
        rows = [dict(zip(keys, r)) for r in cur.fetchall()]
        n_hold = c.execute("SELECT COUNT(*) FROM paper_index_holdings").fetchone()[0]
        cur = c.execute("SELECT * FROM paper_index_closed")
        ckeys = [d[0] for d in cur.description]
        closed = [dict(zip(ckeys, r)) for r in cur.fetchall()]
    # AUDIT P4 — names that have LEFT the book. Before the fix they were held forever and this
    # block was always empty because nothing could ever leave. Reported rather than discarded:
    # a name exits when its composite decays, so dropping these stints from the record would
    # remove disproportionately the ones that did badly.
    real = {"n_closed": len(closed), "mean_active_ret": None, "n_priced": 0}
    if closed:
        act = [(_f(h.get("exit_price")) / _f(h.get("entry_price")) - 1.0)
               - (_f(h.get("exit_bench_price")) / _f(h.get("bench_entry_price")) - 1.0)
               for h in closed
               if _f(h.get("entry_price")) and _f(h.get("exit_price"))
               and _f(h.get("bench_entry_price")) and _f(h.get("exit_bench_price"))]
        real["n_priced"] = len(act)
        real["mean_active_ret"] = (sum(act) / len(act)) if act else None
        real["note"] = ("realised vs SPY over each stint's own window; NOT chained into the "
                        "daily series, which is a snapshot of open holdings")
    if not rows:
        # `book_conformance` belongs on BOTH returns. A book can be held before its first
        # series point exists, and that is exactly when a wrong book is cheapest to catch.
        return {"started": False, "n_holdings": int(n_hold), "n_days": 0, "realized": real,
                "book_conformance": held_book_conformance(store),
                "label": _label(None, 0, 0)}
    last, first = rows[-1], rows[0]
    gate = _contract_gate()
    return {"started": True, "inception": last.get("inception") or first["as_of"],
            "as_of": last["as_of"], "n_days": len(rows), "n_holdings": int(n_hold),
            "realized": real,
            "index_ret": last.get("index_ret"), "bench_ret": last.get("bench_ret"),
            "active_ret": last.get("active_ret"), "n_priced": last.get("n_priced"),
            # BOTH conditions, never either alone. The day count is not sufficient: audit OOB5
            # closed the same hole in `index_track` and found this one still open behind it --
            # `hero` falls back to THIS function when the Cowork tracker files are absent, which
            # is precisely the fresh-deploy case, so a day count alone could still promote a
            # paper track to the headline. Same authority as `index_track.gate_state()`, not a
            # second flag: one copy of the fact, in the contract Don signed.
            "meaningful": len(rows) >= MIN_DAYS_FOR_MEANING and bool(gate.get("passed")),
            "min_days_for_meaning": MIN_DAYS_FOR_MEANING,
            "contract_gate": gate,
            "book_conformance": held_book_conformance(store),
            "history": [{"as_of": r["as_of"], "index_ret": r.get("index_ret"),
                         "bench_ret": r.get("bench_ret")} for r in rows[-260:]],
            "label": _label(last.get("inception") or first["as_of"], MIN_CLOSED_FOR_MEANING,
                            len(rows))}


def _contract_gate() -> dict:
    """The paper track's operational gate, read from the ONE place that carries it.

    `PAPER_TRACK_CONTRACT.md` §5's `Operational gate passed` row, parsed by
    `index_track.gate_state()`. Deliberately delegated rather than re-implemented: a second
    parser is a second record of the same fact, free to disagree with the document Don signed.

    FAIL-CLOSED. Anything that goes wrong here -- import failure, unreadable contract, malformed
    row -- resolves to NOT passed, so the error this cannot reach is "a thin track leads the
    page". The conservative error is a mature track still labelled backtested.
    """
    try:
        from ..screener.index_track import gate_state
        return gate_state() or {"passed": False, "reason": "gate_state returned nothing"}
    except Exception as e:                                   # noqa: BLE001 - fail closed
        return {"passed": False, "reason": f"operational gate unreadable: {type(e).__name__}"}


def options_summary(store) -> dict:
    """The paper options book: how many are actually live, and what has closed.

    Reports the SCOREBOARD from the existing `options_tracker.scorecard` rather than
    recomputing expectancy, so there is exactly one definition of it in the project.
    """
    ensure_schema(store)
    rows = paper_orders(store, limit=100000)
    by_state = {}
    for r in rows:
        by_state[r.get("state") or "?"] = by_state.get(r.get("state") or "", 0) + 1
    sc = OT.scorecard(store)
    n_closed = (sc.get("overall") or {}).get("n_closed") or 0
    inception = min((r.get("created_at") or "")[:10] for r in rows) if rows else None
    return {"started": bool(rows), "inception": inception or None,
            "by_state": by_state, "n_live": by_state.get("open", 0) + by_state.get("closing", 0),
            "n_closed_paper": by_state.get("closed", 0),
            "scorecard": sc.get("overall"),
            "meaningful": n_closed >= MIN_CLOSED_FOR_MEANING,
            "min_closed_for_meaning": MIN_CLOSED_FOR_MEANING,
            "level_conformance": _level_conformance(store, rows),
            "label": _label(inception, n_closed, MIN_DAYS_FOR_MEANING)}


def _level_conformance(store, rows) -> dict:
    """Do the live exit levels match the fill they are supposed to be derived from?

    SESSION 16, the read-only half of the BUG 1 repair. `mark_open` fixes rows when a cycle runs;
    this reports on every request whether any LIVE position is still trading to a target or stop
    the backtest does not describe. Read-only on purpose: a summary must never write.

    It stays after the bug is fixed because that is the point -- the first time this book was
    inspected, 2 of 3 open positions were off spec and nothing anywhere said so.
    """
    off, checked = [], 0
    for r in rows:
        if (r.get("state") or "") not in ("open", "closing"):
            continue
        entry = _f(r.get("entry_premium"))
        want = _levels_from(store, r, entry) if entry else {}
        if not want:
            continue
        checked += 1
        cur_t, cur_s = _f(r.get("target_premium")), _f(r.get("stop_premium"))
        if (cur_t is None or abs(cur_t - want["target_premium"]) > _LEVEL_TOL
                or cur_s is None or abs(cur_s - want["stop_premium"]) > _LEVEL_TOL):
            off.append({"alert_id": r.get("alert_id"), "ticker": r.get("ticker"),
                        "entry_premium": entry,
                        "target_is": cur_t, "target_should_be": want["target_premium"],
                        "stop_is": cur_s, "stop_should_be": want["stop_premium"]})
    return {"checked": checked, "off_spec": len(off), "ok": not off, "detail": off}


def _contract_track() -> dict:
    """The CONTRACT-bound track's recording status and withheld meter, for every request.

    A different object from everything else in this module, and labelled as one: `options` and
    `index` here are the Tradier SANDBOX engine, while this is the published Valquo Index that
    `PAPER_TRACK_CONTRACT.md` actually binds. The two record different books (§0a.2), so they
    are reported side by side and never merged.

    Why it is surfaced on every request rather than checked at the gate: the contract's 6-month
    operational gate tests whether the track is being RECORDED, and a recording failure that
    nobody notices until gate day has already cost the whole window. `track_meter.detail()`
    names every missing trading day, so the failure is visible continuously.
    """
    try:
        from . import track_meter
        return track_meter.detail()
    except Exception as e:                                   # noqa: BLE001 - never break /api/track
        return {"available": False, "reason": f"contract track unreadable: {type(e).__name__}"}


def summary(store) -> dict:
    """Everything `/api/track` needs, with the caveats attached to the numbers themselves."""
    opt, idx = options_summary(store), index_summary(store)
    meaningful = bool(opt.get("meaningful")) and bool(idx.get("meaningful"))
    return {
        "options": opt, "index": idx,
        "contract_track": _contract_track(),
        "venue": "Tradier sandbox (paper). No real money and no real orders.",
        "data_caveat": DATA_CAVEAT,
        "headline": ("Backtested expectancy remains the headline result - this forward paper "
                     "track is too thin to carry a claim yet."
                     if not meaningful else
                     "The forward paper track now has a meaningful sample; read it alongside "
                     "the backtest, which it was built to test."),
        "how_to_read": ("Every position here was recorded BEFORE its outcome was known, which "
                        "is the one thing the backtest cannot claim. Fills are sandbox fills "
                        "on ~15-minute-delayed quotes, entries at the ask and exits at the "
                        "bid - the same punishing convention the backtest used."),
    }
