"""THE §8 REAL-MONEY LIVE PATH, ON ALPACA, SHIPPING AT 0%.  [item 58 B]

WHAT THIS IS, AND WHAT DON ASKED FOR VERBATIM
---------------------------------------------
`PAPER_TRACK_CONTRACT.md` §8 (signed 2026-09-02, restored 2026-09-15) authorises a
percentage-of-equity real-money path. It was never built: refused twice, and the second refusal
measured the reason the vendor had to change — Tradier takes whole shares only, so at $5,000 of
book **51 of 68 Index names got zero shares** and the minimum whole book was **$128,562**.
Alpaca allows fractional shares, which is why Don moved.

Don's instruction, 2026-10-14, quoted because it IS the specification:

> *"I want it to be fully disciplined. Buy and hold and pilot at whatever percentage of the
> account is authorized and does that math per stock. Buying and selling only at quarterly
> rebalances and when that percentage changes. Otherwise no other restrictions because that's
> the whole point. If not, then we just have extra room for bugs, errors, and complications"*

THE WHOLE BEHAVIOUR
-------------------
Each stock's target value is `slot_pct × account_equity × weight_in_the_Index_book_in_force`.
The slot buys or sells fractional shares to reach that target, and acts on **exactly three
events**:

  1. a **new rebalance event** on the bound Index record;
  2. a **change in the slot's own percentage** — 0→X buys in, X→Y resizes, X→0 sells out;
  3. **nothing else.** No loss stops, no drawdown rule, no drift rebalancing, no trading
     between events. Dividends sit as cash until the next event.

**THE LOSS STOPS §8 REQUIRED ARE REMOVED BY DON'S INSTRUCTION**, and that removal is recorded in
the contract's §8a rather than inferred from this file. Nothing here halts, trims or freezes on
performance; there is no code path that reads a return and decides to trade.

WHY "FULLY DISCIPLINED" MAKES THE CODE SMALLER, WHICH IS HIS OWN ARGUMENT
-------------------------------------------------------------------------
Every extra rule is a branch that can fire when it should not. The only reads that can cause an
order here are: the book in force, its weights, the account's equity, and the slot's percentage.
A price is read to set a limit, never to decide.

IF ANYTHING IS BROKEN, THE SLOT DOES NOT TRADE
----------------------------------------------
Before any order is sent, `preflight` checks the inputs and the arithmetic. If any check fails
the slot sends **no orders that cycle**, alerts Don with the reason, and checks again next
cycle. **An error never causes a sale and never changes holdings** — which is why every refusal
returns the same empty order list rather than a partial one. These checks are about the
software, never about performance.

SEPARATION, WHICH IS THE PART THAT MATTERS MOST
-----------------------------------------------
* The live client is a **different class** from the paper broker and accepts **only** the live
  host (`_LiveClient`). `alpaca_broker.AlpacaPaperBroker` accepts only the paper host. Neither
  can be pointed at the other's.
* **No live client is constructed at all** unless the slot's keys exist, `LIVE_PILOT_ENABLED=1`,
  its percentage is above 0, and — for any slot but 1 — the contract carries that holder's own
  signed authorization. At 0%, which is how every slot ships, the cycle computes the orders it
  *would* place, logs them, diffs them against the paper book, and **returns without
  constructing a client**.
* A lane never sets a percentage, never enters a key and never triggers a live order: the only
  trigger is the service's own scheduled cycle, and the keys exist only in Render's environment.

PAUSING IS NOT ZERO, AND CONFUSING THEM WOULD SELL DON'S BOOK
-------------------------------------------------------------
* `LIVE_PILOT_ENABLED=0` — **PAUSE.** Every slot stops acting. Nothing is sold, holdings stay
  exactly as they are, and no target is computed. It is the global kill switch §8 requires.
* `ALPACA_ACCOUNT_<n>_LIVE_PCT=0` — **A TARGET OF ZERO.** That is an instruction to hold
  nothing, so the slot SELLS what it bought, at the next cycle.

They are opposite in effect and one character apart in an environment panel, so `status()`
states the difference in words on every read.
"""
from __future__ import annotations

import datetime as _dt
import os
import re
from typing import Optional
from urllib.parse import urlparse

#: The LIVE host. This module is the only one permitted to name it as a target.
LIVE_BASE = "https://api.alpaca.markets"
LIVE_HOST = "api.alpaca.markets"

#: The paper host, named ONLY to refuse it: a live slot pointed at paper would silently do
#: nothing real while reporting success, which is the same class of error as the reverse.
PAPER_HOST = "paper-api.alpaca.markets"

#: The global kill switch, §8's requirement. Anything other than exactly "1" is a pause --
#: `MA6`'s rule, err toward the state that refuses, so a typo pauses rather than arms.
ENABLED_VAR = "LIVE_PILOT_ENABLED"

#: Retired by item 58. `ALPACA_LIVE_PCT` was an earlier draft's single-account name and is
#: READ NOWHERE: a slot's percentage comes only from `ALPACA_ACCOUNT_<n>_LIVE_PCT`. Honouring
#: it as an alias would mean an old variable silently arming slot 1.
RETIRED_VARS = ("ALPACA_LIVE_PCT",)

_SLOT_RX = re.compile(r"^ALPACA_ACCOUNT_(\d+)_KEY_ID$")

#: How a holder's authorization is recognised in the contract, read the way
#: `index_track.gate_state()` reads its own row: a table row, matched on the slot number, whose
#: verdict cell is an explicit YES. Anything unrecognised is NOT authorized.
_AUTH_RX_TMPL = (r"^\|\s*Slot\s+%d\s+live\s+authorization\s*\|\s*"
                 r"(YES[^|]*|yes[^|]*)\|")


class NotLiveError(RuntimeError):
    """Raised when anything about a live slot's configuration is not unambiguously correct."""


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def assert_live_host(base: str) -> str:
    """Fail unless `base` is exactly Alpaca's LIVE endpoint. Returns it normalised."""
    b = (base or "").strip().rstrip("/")
    u = urlparse(b)
    host = (u.hostname or "").lower()
    if u.scheme != "https" or host != LIVE_HOST:
        raise NotLiveError(
            "the live path refuses %r: it must be %r (host %s). A live slot pointed at the "
            "paper host would report success while doing nothing real." % (b, LIVE_BASE,
                                                                           LIVE_HOST))
    return b


def pilot_enabled(env=None) -> bool:
    """Is the global switch on? Anything but exactly "1" is a pause."""
    e = env if env is not None else os.environ
    return str(e.get(ENABLED_VAR, "") or "").strip() == "1"


def discover_slots(env=None) -> list:
    """Every slot `n` that has BOTH keys, in numeric order. Keys are never returned.

    Discovery is by the presence of a KEY PAIR rather than of a percentage, deliberately: a
    slot whose percentage variable is missing **defaults to 0** and must still be discovered,
    or a new account would be invisible rather than idle.
    """
    e = env if env is not None else os.environ
    out = []
    for name in e:
        m = _SLOT_RX.match(name or "")
        if not m:
            continue
        n = int(m.group(1))
        if not (e.get("ALPACA_ACCOUNT_%d_KEY_ID" % n, "") or "").strip():
            continue
        if not (e.get("ALPACA_ACCOUNT_%d_SECRET_KEY" % n, "") or "").strip():
            continue
        out.append(n)
    return sorted(set(out))


def slot_pct(n: int, env=None) -> dict:
    """The slot's percentage, 0-100, or a refusal. A missing value is 0, never a default-on."""
    e = env if env is not None else os.environ
    raw = (e.get("ALPACA_ACCOUNT_%d_LIVE_PCT" % n, "") or "").strip()
    if raw == "":
        return {"ok": True, "pct": 0.0, "stated": False,
                "reason": "no percentage is set, so this slot is at 0% and does nothing"}
    v = _f(raw)
    if v is None or v < 0.0 or v > 100.0:
        # A BAD VALUE IS NOT 0 AND IS NOT IGNORED. It is a broken input, so the slot refuses
        # to act -- treating it as 0 would SELL the book on a typo.
        return {"ok": False, "pct": None, "stated": True,
                "reason": ("ALPACA_ACCOUNT_%d_LIVE_PCT is %r, which is not a number between 0 "
                           "and 100. The slot sends no orders and alerts, because reading it "
                           "as 0 would sell the book on a typo." % (n, raw))}
    return {"ok": True, "pct": float(v), "stated": True, "reason": ""}


def holder(n: int, env=None) -> str:
    e = env if env is not None else os.environ
    return (e.get("ALPACA_ACCOUNT_%d_HOLDER" % n, "") or "").strip() or "unnamed"


def holder_authorized(n: int, contract_text: str = None) -> dict:
    """Is this slot's holder authorized by the contract? Slot 1 is Don's and needs no row.

    §8: *"Family slots remain at 0 until each account holder's own signed authorization"*. Read
    from `PAPER_TRACK_CONTRACT.md` the way `index_track.gate_state()` reads its gate row, so
    there is one way this project turns a signed document into a boolean.
    """
    if int(n) == 1:
        return {"ok": True, "authorized": True, "reason": "slot 1 is Don's own account",
                "row": "n/a"}
    txt = contract_text
    if txt is None:
        try:
            from ..screener import index_track as IT
            with open(IT.contract_path(), encoding="utf-8") as fh:
                txt = fh.read()
        except Exception as e:                                          # noqa: BLE001
            return {"ok": False, "authorized": False,
                    "reason": ("the contract could not be read (%s), so no holder "
                               "authorization can be confirmed" % type(e).__name__)}
    rx = re.compile(_AUTH_RX_TMPL % int(n), re.M)
    if rx.search(txt or ""):
        return {"ok": True, "authorized": True,
                "reason": "the contract carries a signed authorization for slot %d" % n,
                "row": "Slot %d live authorization" % n}
    # EVERY UNRECOGNISED OUTCOME IS NOT-AUTHORIZED: a missing file, a malformed table, a row
    # that says anything but YES. The failure direction is "stays at 0%".
    return {"ok": True, "authorized": False,
            "reason": ("the contract carries no signed authorization row for slot %d, so it "
                       "stays at 0%% whatever its percentage says" % n),
            "row": "Slot %d live authorization" % n}


def isolation(env=None) -> dict:
    """Do any two slots share a credential? Returns the clashes; never the credentials."""
    e = env if env is not None else os.environ
    seen, clashes = {}, []
    for n in discover_slots(e):
        for which in ("KEY_ID", "SECRET_KEY"):
            v = (e.get("ALPACA_ACCOUNT_%d_%s" % (n, which), "") or "").strip()
            if not v:
                continue
            if v in seen and seen[v] != n:
                clashes.append({"slots": sorted([seen[v], n]), "field": which.lower()})
            else:
                seen[v] = n
    return {"ok": not clashes, "clashes": clashes,
            "reason": ("" if not clashes else
                       "two slots share a credential, so they are the same account under two "
                       "names: %s" % clashes)}


def armed(n: int, env=None, contract_text: str = None) -> dict:
    """Is this slot allowed to send a real order? Four conditions, all required.

    **THIS IS THE ONLY FUNCTION THAT MAY SAY YES**, and nothing constructs a live client without
    it. The conditions are evaluated in the order that reveals the most useful reason first.
    """
    e = env if env is not None else os.environ
    out = {"slot": int(n), "armed": False, "reason": "", "holder": holder(n, e),
           "pct": None, "pilot_enabled": pilot_enabled(e)}
    if int(n) not in discover_slots(e):
        out["reason"] = "slot %d has no key pair configured" % n
        return out
    if not out["pilot_enabled"]:
        out["reason"] = ("%s is not 1, so every slot is PAUSED. Nothing is sold and holdings "
                         "stay exactly as they are." % ENABLED_VAR)
        return out
    p = slot_pct(n, e)
    out["pct"] = p.get("pct")
    if not p["ok"]:
        out["reason"] = p["reason"]
        return out
    if (p["pct"] or 0.0) <= 0.0:
        out["reason"] = ("slot %d is at 0%%, so it holds nothing. At 0%% the cycle computes "
                         "and logs the orders it would place and sends none." % n)
        return out
    auth = holder_authorized(n, contract_text)
    if not auth["authorized"]:
        out["reason"] = auth["reason"]
        return out
    iso = isolation(e)
    if not iso["ok"]:
        out["reason"] = iso["reason"]
        return out
    out["armed"] = True
    out["reason"] = "slot %d is armed at %.4g%% for %s" % (n, p["pct"], out["holder"])
    return out


# --------------------------------------------------------------------------- #
# The per-stock arithmetic — the whole of what the slot decides
# --------------------------------------------------------------------------- #
def targets(pct: float, equity: float, positions) -> dict:
    """`{ticker: target_value}` for a slot. THE ONLY SIZING RULE IN THE LIVE PATH.

    `target_i = pct/100 × equity × w_i`, with the weights renormalised over the HELD names so
    a book carrying an exited position at zero weight still deploys the slot's full percentage.
    Returns a refusal rather than a partial map when the inputs cannot support it.
    """
    p, eq = _f(pct), _f(equity)
    if p is None or p < 0 or p > 100:
        return {"ok": False, "reason": "the percentage %r is not between 0 and 100" % (pct,)}
    if eq is None or eq <= 0:
        return {"ok": False, "reason": "account equity %r is not a positive number" % (equity,)}
    held = [q for q in (positions or [])
            if str((q or {}).get("ticker") or "").strip()
            and (_f((q or {}).get("weight")) or 0.0) > 0]
    tw = sum(_f(q.get("weight")) or 0.0 for q in held)
    if not held or tw <= 0:
        return {"ok": False, "reason": "the book carries no held position with a weight"}
    slot_value = (p / 100.0) * eq
    out = {}
    for q in held:
        w = (_f(q.get("weight")) or 0.0) / tw
        out[str(q["ticker"]).upper()] = slot_value * w
    return {"ok": True, "targets": out, "slot_value": slot_value, "n": len(out),
            "weights_renormalised_over": len(held)}


def order_plan(targets_map: dict, held_by_slot: dict, marks: dict, *,
               min_order_value: float = 1.0) -> dict:
    """The orders that move the slot's own holdings to `targets_map`. Limit orders only.

    `held_by_slot` is **the slot's OWN record** of what it bought, never the broker's whole
    position list — Don's other holdings in the account are never touched, and that is enforced
    by what this function is given rather than by a filter it could forget to apply.
    """
    orders, skipped = [], []
    for tkr, tgt in sorted((targets_map or {}).items()):
        mark = _f((marks or {}).get(tkr, {}).get("mid") if isinstance(
            (marks or {}).get(tkr), dict) else (marks or {}).get(tkr))
        if mark is None or mark <= 0:
            # A MISSING PRICE IS A BROKEN INPUT, not a reason to trade at any price. The caller
            # turns this into "no orders this cycle" -- see `preflight`.
            skipped.append({"ticker": tkr, "reason": "no usable mark"})
            continue
        have_qty = _f((held_by_slot or {}).get(tkr)) or 0.0
        have_val = have_qty * mark
        delta = tgt - have_val
        if abs(delta) < float(min_order_value):
            continue
        side = "buy" if delta > 0 else "sell"
        qty = abs(delta) / mark
        if side == "sell":
            qty = min(qty, have_qty)      # NEVER sell more than this slot bought
            if qty <= 0:
                continue
        orders.append({"ticker": tkr, "side": side, "qty": round(qty, 9),
                       "limit_price": round(mark, 2), "target_value": round(tgt, 2),
                       "current_value": round(have_val, 2)})
    return {"orders": orders, "skipped": skipped}


def preflight(*, book: dict, equity, marks: dict, slot_record: dict, pct,
              broker_positions=None, tolerance: float = 0.01) -> dict:
    """Every "is anything broken" check, in one place. `ok: False` means NO ORDERS this cycle.

    The list is the brief's, and each entry exists because the alternative is an order placed
    on a number nobody checked. **None of these is about performance.**
    """
    problems = []
    if not isinstance(book, dict) or not book.get("ok"):
        problems.append("the Index book in force could not be read: %s"
                        % ((book or {}).get("reason") or "no reason given"))
    else:
        held = [q for q in (book.get("positions") or []) if q.get("status") == "held"]
        if not held:
            problems.append("the book in force carries no held positions")
        if not book.get("formed_on"):
            problems.append("the book carries no formation date, so it cannot be checked "
                            "for staleness against its own rebalance")
    if _f(equity) is None or (_f(equity) or 0) <= 0:
        problems.append("account equity could not be read as a positive number")
    p = _f(pct)
    if p is None or p < 0 or p > 100:
        problems.append("the slot's percentage is not a number between 0 and 100")
    if not isinstance(marks, dict):
        problems.append("no price map was supplied")
    elif isinstance(book, dict) and book.get("ok"):
        need = [str(q.get("ticker") or "").upper()
                for q in (book.get("positions") or []) if q.get("status") == "held"]
        missing = [t for t in need
                   if not _f((marks.get(t) or {}).get("mid")
                             if isinstance(marks.get(t), dict) else marks.get(t))]
        if missing:
            problems.append("no usable price for %d name(s) the cycle would trade: %s"
                            % (len(missing), ", ".join(missing[:8])))
    if broker_positions is not None:
        # THE SLOT'S OWN RECORD MUST AGREE WITH THE BROKER on the names it believes it holds.
        # A disagreement means one of the two is wrong, and trading on either would be a guess.
        # EITHER SHAPE. A list of `{ticker, qty}` is what `AlpacaPaperBroker.positions`
        # returns and what this function documents; a `{SYM: qty}` mapping is the obvious
        # thing for a caller to build, and iterating one yields its KEYS -- so the strict
        # version raised `AttributeError` on a string, which a caller's own `except` would
        # report as "this slot failed" and NOT as "the shapes disagree". Accepting both is
        # two lines and removes a whole class of silent misreport.
        if hasattr(broker_positions, "items"):
            by_broker = {str(k).upper(): _f(v) for k, v in broker_positions.items()}
        else:
            by_broker = {str((q or {}).get("ticker") or "").upper(): _f((q or {}).get("qty"))
                         for q in broker_positions}
        for tkr, qty in (slot_record or {}).items():
            theirs = by_broker.get(str(tkr).upper())
            mine = _f(qty) or 0.0
            if theirs is None:
                problems.append("this slot's record holds %s and the broker reports no such "
                                "position" % tkr)
            elif abs((theirs or 0.0) - mine) > max(float(tolerance), abs(mine) * 0.001):
                problems.append("this slot's record holds %.6f of %s and the broker reports "
                                "%.6f" % (mine, tkr, theirs or 0.0))
    return {"ok": not problems, "problems": problems,
            "reason": ("" if not problems else
                       "the slot sends NO orders this cycle and alerts Don: %s"
                       % "; ".join(problems))}


def event_for(slot_state: dict, book: dict, pct) -> dict:
    """Which of the three events, if any, applies this cycle.

    `slot_state` is the slot's own last-acted record: `{last_event_date, last_pct}`.
    """
    last_ev = str((slot_state or {}).get("last_event_date") or "")
    last_pct = _f((slot_state or {}).get("last_pct"))
    formed = str((book or {}).get("formed_on") or "")
    now_pct = _f(pct)
    if formed and formed != last_ev:
        return {"act": True, "event": "rebalance",
                "reason": "the Index book in force was formed %s and this slot last acted on "
                          "%s" % (formed, last_ev or "nothing")}
    if now_pct is not None and (last_pct is None or abs(now_pct - last_pct) > 1e-9):
        kind = ("buy-in" if (last_pct or 0) == 0 and now_pct > 0 else
                ("sell-out" if now_pct == 0 else "resize"))
        return {"act": True, "event": "pct_change", "kind": kind,
                "reason": "the slot's percentage moved from %s to %s (%s)"
                          % ("unset" if last_pct is None else last_pct, now_pct, kind)}
    return {"act": False, "event": "none",
            "reason": ("no rebalance since %s and no percentage change, so the slot does "
                       "nothing -- which is the whole point" % (last_ev or "inception"))}


def status(env=None, contract_text: str = None) -> dict:
    """Every slot: holder, percentage, armed or not, and what pausing means. Owner-only.

    **NO CREDENTIAL APPEARS IN THIS PAYLOAD**, and no live client is constructed to build it.
    """
    e = env if env is not None else os.environ
    slots = []
    for n in discover_slots(e):
        a = armed(n, e, contract_text)
        p = slot_pct(n, e)
        slots.append({"slot": n, "holder": holder(n, e),
                      "pct": p.get("pct"), "pct_stated": p.get("stated"),
                      "armed": a["armed"], "reason": a["reason"],
                      "authorized": holder_authorized(n, contract_text)["authorized"]})
    retired = [v for v in RETIRED_VARS if (e.get(v, "") or "").strip() != ""]
    return {
        "slots": slots,
        "n_slots": len(slots),
        "pilot_enabled": pilot_enabled(e),
        "isolation": isolation(e),
        # THE DIFFERENCE, IN WORDS, ON EVERY READ. These two are opposite in effect and one
        # character apart in an environment panel.
        "pause_vs_zero": {
            "pause": ("%s=0 PAUSES every slot. Nothing is sold, holdings stay exactly as they "
                      "are, and no target is computed." % ENABLED_VAR),
            "zero_pct": ("ALPACA_ACCOUNT_<n>_LIVE_PCT=0 is a TARGET OF ZERO: an instruction to "
                         "hold nothing, so the slot SELLS what it bought at the next cycle."),
        },
        "retired_variables_set": retired,
        "retired_note": ("%s is retired and is read NOWHERE. If it is set, delete it and use "
                         "ALPACA_ACCOUNT_1_LIVE_PCT -- honouring an alias would let an old "
                         "variable arm a slot." % ", ".join(RETIRED_VARS)),
        "loss_stops": ("REMOVED by Don's instruction of 2026-10-14 (contract section 8a). "
                       "Nothing here halts, trims or freezes on performance."),
        "as_of": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


class _LiveClient:
    """The LIVE Alpaca client. Constructed only by `arm_and_trade`, only when `armed` says so.

    A separate class from `AlpacaPaperBroker` rather than a flag on it: a boolean that chooses
    between paper and real money is one typo from a real order, and a flag would also let a
    paper book reach this code by passing it.
    """

    def __init__(self, slot: int, key_id: str, secret_key: str, base: str = LIVE_BASE,
                 timeout: int = 25, session=None):
        self.base = assert_live_host(base)
        if not (key_id or "").strip() or not (secret_key or "").strip():
            raise NotLiveError("slot %s has no key pair; no live client is constructed" % slot)
        self.slot = int(slot)
        self._key_id, self._secret = key_id.strip(), secret_key.strip()
        self.timeout, self._session = int(timeout), session

    def _headers(self) -> dict:
        return {"APCA-API-KEY-ID": self._key_id,
                "APCA-API-SECRET-KEY": self._secret,
                "Content-Type": "application/json"}

    def _request(self, method: str, path: str, body: dict = None, params: dict = None):
        import json as _j

        import requests
        sess = self._session or requests
        r = sess.request(method, "%s/%s" % (self.base, str(path).lstrip("/")),
                         headers=self._headers(), params=params or None,
                         data=(_j.dumps(body) if body is not None else None),
                         timeout=self.timeout)
        code = getattr(r, "status_code", 0)
        try:
            payload = r.json()
        except Exception:                                               # noqa: BLE001
            payload = {"raw": getattr(r, "text", "")[:400]}
        if code >= 400:
            return {"ok": False, "status": code, "error": payload}
        return {"ok": True, "status": code, "data": payload}

    def account(self) -> dict:
        return self._request("GET", "/v2/account")

    def positions(self) -> dict:
        return self._request("GET", "/v2/positions")

    def orders(self, status: str = "all", limit: int = 100) -> list:
        """THIS SLOT'S ORDERS, raw, for `live_cycle.reconcile` to total the fills from.

        Returns a LIST and never raises, matching `AlpacaPaperBroker.orders` exactly -- because
        `reconcile` runs on both and a shape difference between the two clients would make the
        paper slot prove a program the live slot does not run.

        Without this a live slot's holdings record would never advance past empty, and every
        cycle would plan the full buy-in again: the defect that was just repaired, surviving on
        the one path where repeating an order costs real money.
        """
        got = self._request("GET", "/v2/orders",
                            params={"status": status, "limit": int(limit)})
        return list(got.get("data") or []) if got.get("ok") else []

    def place_limit(self, ticker: str, side: str, qty: float, limit_price: float,
                    client_order_id: str = None) -> dict:
        """A LIMIT order, `time_in_force=day`, per §8 and Alpaca's fractional constraint."""
        body = {"symbol": str(ticker).upper(), "side": str(side).lower(), "type": "limit",
                "qty": ("%.9f" % float(qty)).rstrip("0").rstrip("."),
                "limit_price": "%.2f" % float(limit_price), "time_in_force": "day"}
        if client_order_id:
            body["client_order_id"] = str(client_order_id)
        return self._request("POST", "/v2/orders", body=body)
