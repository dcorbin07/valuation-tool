"""ALPACA PAPER broker client — the paper account every paper book trades in.  [item 58 A]

WHY ALPACA REPLACES THE TRADIER SANDBOX
---------------------------------------
Don's ruling, 2026-10-14: every paper book moves to Alpaca paper because **Alpaca's paper fills
are matched against the real-time national best bid and offer**, while the Tradier sandbox's
market data is ~15 minutes delayed. A forward paper track exists to make execution failures
visible; one priced off stale quotes hides exactly the thing it was built to show.

PAPER ONLY. THIS IS THE WHOLE SAFETY MODEL, SO IT IS ENFORCED RATHER THAN DOCUMENTED
------------------------------------------------------------------------------------
Modelled on `paper_broker.PaperBroker`, whose three-guard shape this mirrors:

  1. **THE HOST MUST BE EXACTLY `paper-api.alpaca.markets`**, checked by parsing the URL and
     comparing the hostname — not `"paper" in url`, which `https://api.alpaca.markets/?x=paper`
     would satisfy.
  2. **THE KEYS MUST BE THE DEDICATED PAPER KEYS.** Construction fails if either is missing, and
     fails if either equals **any live slot's** credential — see `_clashes_with_a_live_slot`.
     A live key pointed at the paper host would not trade real money, but it would mean two
     credentials had been crossed, which is the mistake worth catching before it reaches a
     scheduler.
  3. **NOTHING HERE CAN REACH THE LIVE HOST.** Every request path is rebuilt from `self.base`,
     validated once at construction and never taken from a caller.

THE BRIEF ASKED FOR A FOURTH GUARD AND IT DOES NOT EXIST — MEASURED, NOT ASSUMED
--------------------------------------------------------------------------------
Item 58 A1 says *"the account endpoint must confirm a paper account (find the field; do not
assume a prefix)"*. **There is no such field.** `GET /v2/account` returns
`account_blocked, account_number, accrued_fees, balance_asof, buying_power, cash, created_at,
crypto_status, currency, equity, id, …, trading_blocked, transfers_blocked` — and **not one of
them distinguishes paper from live**: no `is_paper`, no `account_type`, no `environment`.

The only hint Alpaca's own documentation gives is an example account number rendered
`PALPACA_123`, i.e. **a prefix** — which is precisely what the brief forbids relying on, and
rightly: a prefix is an undocumented formatting detail that can change without notice.

**So the safety cannot rest on the account endpoint, and this module does not pretend it does.**
The host IS the environment — Alpaca's docs state the API is identical between paper and live
and that *"only the host and the keys differ"* — so guard 1 is the real guarantee. The account
number's shape is recorded as **corroboration** (`paper_corroboration`), never as the gate, in
the same way this project treats WBS's missing price as corroboration of an acquisition rather
than evidence of one.

WHAT ALPACA PAPER DOES AND DOES NOT SIMULATE — FROM ITS OWN DOCS, VERBATIM
--------------------------------------------------------------------------
Carried in `DATA_CAVEAT` and travelling in every payload, because a fill assumption left in a
docstring is an assumption nobody reads:

* *"Orders are filled only when they become marketable… a non-marketable buy limit order will
  not be filled until its limit price is equal to or greater than the best ask price"*;
* no **order queue position** and no **price improvement** are modelled;
* *"Your order quantity is not checked against the NBBO quantities"* — a fill can exceed the
  liquidity that actually existed;
* *"When orders are eligible to be filled, they will receive partial fills for a random size
  10% of the time"*;
* **no regulatory fees** and **no dividends** are simulated.

The last one is a standing hole rather than a caveat: a paper book holding shares through an
ex-date earns nothing in this account. See `DIVIDENDS_NOT_PAID`.

DATA PLAN
---------
The free plan is **IEX-only** for stocks and an indicative feed for options; the full
consolidated feed is $99/month and is not bought. So a paper fill is priced against IEX's view
of the NBBO rather than the whole tape, and `feed` records which feed answered — the brief's
A2 requirement, and the input to the A4 feed-gap measurement.
"""
from __future__ import annotations

import datetime as _dt
import json as _json
import os
import re
from typing import Optional
from urllib.parse import urlparse

from ..config import CONFIG

#: The paper trading host, from Alpaca's own documentation:
#: *"you need to set an environment variable APCA_API_BASE_URL = https://paper-api.alpaca.markets"*
PAPER_BASE = "https://paper-api.alpaca.markets"
PAPER_HOST = "paper-api.alpaca.markets"

#: The LIVE host, named here ONLY so it can be refused by name. No code in this module ever
#: builds a request against it, and a test asserts that.
LIVE_HOST = "api.alpaca.markets"

#: Alpaca's own statement of what paper does not model. Travels in the payload.
DATA_CAVEAT = (
    "Alpaca paper fills are matched against the real-time NBBO, which is closer to reality "
    "than a delayed sandbox - but paper does NOT model order queue position or price "
    "improvement, does NOT check order size against available liquidity, fills a random "
    "partial 10% of the time, and charges no regulatory fees. On the free plan the stock feed "
    "is IEX only, not the full consolidated tape.")

#: A standing hole, not a caveat: it changes the measured return of any book that holds through
#: an ex-date. Stated wherever a paper position is reported.
DIVIDENDS_NOT_PAID = (
    "Alpaca paper does not pay dividends. A paper book holding shares through an ex-date "
    "receives nothing, so its return understates a real holding's by the dividend.")

#: `time_in_force` for every fractional order. Alpaca's orders reference permits market, limit,
#: stop and stop-limit for fractional quantities with `day` ONLY -- `gtc`, `ioc`, `fok`, `opg`
#: and `cls` all return "No". A `day` limit expiring at the close is also exactly the behaviour
#: the live path wants (re-price and re-send next cycle), so the constraint and the design agree.
FRACTIONAL_TIF = "day"


class NotPaperError(RuntimeError):
    """Raised when anything about the configuration is not unambiguously the paper account."""


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def assert_paper(base: str) -> str:
    """Fail unless `base` is exactly Alpaca's paper endpoint. Returns it normalised."""
    b = (base or "").strip().rstrip("/")
    u = urlparse(b)
    host = (u.hostname or "").lower()
    if u.scheme != "https" or host != PAPER_HOST:
        raise NotPaperError(
            "the paper books refuse a non-paper endpoint: %r. It must be %r (host %s). "
            "The host IS the environment here -- Alpaca's API is identical between paper and "
            "live and only the host and keys differ -- so this check is the whole guarantee."
            % (b, PAPER_BASE, PAPER_HOST))
    return b


def live_slot_credentials() -> set:
    """Every credential string configured for a LIVE slot, for the clash check only.

    **IT RETURNS THE VALUES AND NOTHING ELSE EVER LOGS THEM.** The only consumer compares them
    for equality; no caller may print, store or transmit one. Reading the environment directly
    rather than through `CONFIG` is deliberate -- a live key must not become an attribute that
    every module holding a config object can reach.
    """
    out = set()
    for name, val in os.environ.items():
        if re.match(r"^ALPACA_ACCOUNT_\d+_(KEY_ID|SECRET_KEY)$", name or ""):
            v = (val or "").strip()
            if v:
                out.add(v)
    return out


def _clashes_with_a_live_slot(key_id: str, secret: str) -> Optional[str]:
    """Which of the two paper credentials is also configured as a live one, if either."""
    live = live_slot_credentials()
    if key_id and key_id in live:
        return "key id"
    if secret and secret in live:
        return "secret key"
    return None


class AlpacaPaperBroker:
    """Alpaca PAPER account client: quotes, orders, positions, balances.

    The same surface the paper books already call on `PaperBroker`, so a book switches by
    configuration rather than by a code change: `quotes`, `balances`, `positions`, `orders`,
    `place_equity`, `cancel`, `order_id`, `fill_price`, `health`.
    """

    def __init__(self, cfg=CONFIG, base: str = PAPER_BASE, key_id: Optional[str] = None,
                 secret_key: Optional[str] = None, dry_run: bool = False, timeout: int = 25,
                 session=None):
        self.base = assert_paper(base)
        self.cfg = cfg
        self.dry_run = bool(dry_run)
        self.timeout = int(timeout)
        self._session = session
        kid = (key_id if key_id is not None
               else getattr(cfg, "alpaca_paper_key_id", "") or "").strip()
        sec = (secret_key if secret_key is not None
               else getattr(cfg, "alpaca_paper_secret_key", "") or "").strip()
        if not kid or not sec:
            raise NotPaperError(
                "ALPACA_PAPER_KEY_ID and ALPACA_PAPER_SECRET_KEY are not both set. The paper "
                "books will NOT fall back to any other Alpaca credential -- a live key is the "
                "one thing that must never serve a paper book.")
        clash = _clashes_with_a_live_slot(kid, sec)
        if clash:
            raise NotPaperError(
                "the paper %s is also configured as a LIVE slot credential "
                "(ALPACA_ACCOUNT_<n>_*). Those must be two different keys; refusing to run a "
                "paper book on a live credential even against the paper host." % clash)
        self._key_id, self._secret = kid, sec

    # ------------------------------------------------------------------ plumbing
    def _url(self, path: str) -> str:
        """Every request path is rebuilt from the validated base. Never from a caller."""
        return "%s/%s" % (self.base, str(path or "").lstrip("/"))

    def _headers(self) -> dict:
        return {"APCA-API-KEY-ID": self._key_id,
                "APCA-API-SECRET-KEY": self._secret,
                "Content-Type": "application/json"}

    def _request(self, method: str, path: str, body: dict = None, params: dict = None):
        import requests
        sess = self._session or requests
        url = self._url(path)
        r = sess.request(method, url, headers=self._headers(), params=params or None,
                         data=(_json.dumps(body) if body is not None else None),
                         timeout=self.timeout)
        code = getattr(r, "status_code", 0)
        try:
            payload = r.json()
        except Exception:                                               # noqa: BLE001
            payload = {"raw": getattr(r, "text", "")[:400]}
        if code >= 400:
            # THE STATUS AND THE BODY, because an Alpaca rejection says why in the body and a
            # bare status turns a fixable order error into a mystery.
            return {"ok": False, "status": code, "error": payload}
        return {"ok": True, "status": code, "data": payload}

    # ------------------------------------------------------------------ reads
    def account(self) -> dict:
        got = self._request("GET", "/v2/account")
        if not got.get("ok"):
            return {"ok": False, "reason": "the account could not be read", "detail": got}
        d = got["data"] or {}
        acct = str(d.get("account_number") or "")
        return {
            "ok": True,
            # WHICH ACCOUNT, so the live path can assert it is not trading THIS one. [item 63]
            # The account number was already read here and consumed only into the
            # corroboration note below; the `id` is the stable identifier and was dropped.
            "account_id": (str(d.get("id") or "") or None),
            "account_number": (acct or None),
            "equity": _f(d.get("equity")),
            "cash": _f(d.get("cash")),
            "buying_power": _f(d.get("buying_power")),
            "status": d.get("status"),
            "trading_blocked": bool(d.get("trading_blocked")),
            "account_blocked": bool(d.get("account_blocked")),
            "multiplier": _f(d.get("multiplier")),
            # CORROBORATION, NEVER THE GATE. There is no paper/live field on this endpoint
            # (see the module docstring); the account number's shape is the only hint Alpaca
            # gives and it is an undocumented prefix, so it is recorded and not relied on.
            "paper_corroboration": {
                "account_number_shape": ("starts with P" if acct[:1].upper() == "P"
                                         else "does not start with P"),
                "is_the_gate": False,
                "note": ("GET /v2/account carries no paper/live field. The HOST is the "
                         "guarantee; this is only corroboration."),
            },
            "host": PAPER_HOST,
        }

    def quotes(self, symbols) -> dict:
        """Latest quote per symbol, from the data host. `{SYM: {bid, ask, mid, feed}}`."""
        syms = [str(s).upper().strip() for s in (symbols or []) if str(s or "").strip()]
        if not syms:
            return {}
        import requests
        sess = self._session or requests
        r = sess.request("GET", "https://data.alpaca.markets/v2/stocks/quotes/latest",
                         headers=self._headers(), params={"symbols": ",".join(syms)},
                         timeout=self.timeout)
        try:
            payload = r.json() if getattr(r, "status_code", 0) < 400 else {}
        except Exception:                                               # noqa: BLE001
            payload = {}
        out = {}
        for sym, q in ((payload or {}).get("quotes") or {}).items():
            bid, ask = _f((q or {}).get("bp")), _f((q or {}).get("ap"))
            mid = None
            if bid and ask and bid > 0 and ask > 0:
                mid = (bid + ask) / 2.0
            out[str(sym).upper()] = {
                "bid": bid, "ask": ask, "mid": mid,
                # WHICH FEED PRICED IT -- the brief's A2 requirement, and the input to the
                # A4 feed-gap measurement. `iex` on the free plan; absent means the vendor
                # did not say, which must never be resolved to the full tape.
                "feed": (q or {}).get("z") or (payload or {}).get("feed") or "unstated",
                "as_of": (q or {}).get("t"),
            }
        return out

    @staticmethod
    def mark_from_quote(q: Optional[dict]) -> Optional[float]:
        """The mid, or None. NEVER the last trade: a stale print is not a mark."""
        if not isinstance(q, dict):
            return None
        return _f(q.get("mid"))

    def balances(self) -> dict:
        return self.account()

    def positions(self) -> list:
        got = self._request("GET", "/v2/positions")
        if not got.get("ok"):
            return []
        out = []
        for p in (got.get("data") or []):
            out.append({"ticker": str(p.get("symbol") or "").upper(),
                        "qty": _f(p.get("qty")),
                        "avg_price": _f(p.get("avg_entry_price")),
                        "market_value": _f(p.get("market_value")),
                        "side": p.get("side")})
        return out

    def orders(self, status: str = "all", limit: int = 100) -> list:
        got = self._request("GET", "/v2/orders",
                            params={"status": status, "limit": int(limit)})
        return list(got.get("data") or []) if got.get("ok") else []

    def order(self, order_id) -> dict:
        got = self._request("GET", "/v2/orders/%s" % order_id)
        return dict(got.get("data") or {}) if got.get("ok") else {"ok": False, "detail": got}

    # ------------------------------------------------------------------ writes
    def place_equity(self, ticker: str, side: str, quantity, limit_price=None,
                     time_in_force: str = FRACTIONAL_TIF, client_order_id: str = None) -> dict:
        """A limit order for a possibly-FRACTIONAL quantity. Returns the broker's reply.

        **FRACTIONAL IS ALLOWED HERE AND WAS NOT ON TRADIER**, which is the reason Don moved:
        Tradier rejects a decimal quantity outright, and at $5,000 of book that left 51 of 68
        Index names at zero shares. Alpaca's orders reference permits market, limit, stop and
        stop-limit for fractional quantities with `time_in_force=day`.

        `qty` IS USED RATHER THAN `notional`, deliberately: a notional order **cannot be
        replaced** (*"Any attempt to modify a notional order via the replace (PATCH) endpoint …
        will be rejected"*), and the live path has to be able to re-price an unfilled order.
        """
        q = _f(quantity)
        if q is None or q <= 0:
            return {"ok": False, "reason": "quantity %r is not a positive number" % (quantity,)}
        sd = str(side or "").lower().strip()
        if sd not in ("buy", "sell"):
            return {"ok": False, "reason": "side must be buy or sell, not %r" % (side,)}
        lp = _f(limit_price)
        if lp is None or lp <= 0:
            # LIMIT ONLY. §8 requires it, and a market order on a fractional quantity is the
            # one shape that can fill at a price nobody chose.
            return {"ok": False,
                    "reason": ("a limit price is required: this client places LIMIT orders "
                               "only, per PAPER_TRACK_CONTRACT section 8")}
        tif = str(time_in_force or FRACTIONAL_TIF).lower()
        if q != int(q) and tif != FRACTIONAL_TIF:
            return {"ok": False,
                    "reason": ("a fractional quantity requires time_in_force=%r; Alpaca "
                               "permits no other for fractional orders" % FRACTIONAL_TIF)}
        body = {"symbol": str(ticker or "").upper().strip(), "side": sd, "type": "limit",
                "qty": ("%.9f" % q).rstrip("0").rstrip("."), "limit_price": "%.2f" % lp,
                "time_in_force": tif}
        if client_order_id:
            body["client_order_id"] = str(client_order_id)
        if self.dry_run:
            # NOTHING IS SENT. Alpaca has no preview endpoint, so a dry run returns the exact
            # body that WOULD have been sent rather than asking the broker to validate it.
            return {"ok": True, "dry_run": True, "would_send": body,
                    "note": ("no order was sent; Alpaca has no order-preview endpoint, so a "
                             "dry run reports the request body instead"),
                    "data_caveat": DATA_CAVEAT}
        got = self._request("POST", "/v2/orders", body=body)
        if not got.get("ok"):
            return {"ok": False, "reason": "the broker rejected the order", "detail": got,
                    "sent": body}
        return {"ok": True, "data": got.get("data") or {}, "sent": body,
                "data_caveat": DATA_CAVEAT}

    def place_limit(self, ticker: str, side: str, qty: float, limit_price: float,
                    client_order_id: str = None) -> dict:
        """THE NAME `run_slot` CALLS. Delegates to `place_equity`; adds no behaviour. [item 63]

        **IT EXISTS BECAUSE ITS ABSENCE MEANT THE PAPER SLOT COULD NOT PLACE AN ORDER AT ALL.**
        `live_cycle.run_slot` is deliberately one runner for both clients, and it transmits by
        calling `client.place_limit(...)`. This class had only `place_equity`, so every paper
        order raised `AttributeError`, was caught into a `broker_error` alert, and nothing was
        sent -- while the suite stayed green, because every test handed `run_slot` a stub that
        defined `place_limit`. The paper slot is the whole mechanism by which the real-money
        path is proven before real money, and it had never run.

        **WHY A SECOND NAME RATHER THAN RENAMING `place_equity`:** `place_equity` is the paper
        books' own call (`fleet`, `paper_track` and the options books all reach it), and
        renaming it would move a shipped interface to repair an unshipped one. This is the
        narrower change, and `tests/test_item63.py` asserts the two stay in step by reading the
        delegation out of the source rather than trusting this docstring.

        **IT IS A DELEGATION AND NOT A COPY** (`B7`): every validation `place_equity` performs
        -- limit-only, positive quantity, the fractional `time_in_force` rule -- applies here
        unchanged, because this function performs none of them itself.
        """
        return self.place_equity(ticker, side, qty, limit_price=limit_price,
                                 client_order_id=client_order_id)

    def cancel(self, order_id) -> dict:
        got = self._request("DELETE", "/v2/orders/%s" % order_id)
        return {"ok": bool(got.get("ok")), "detail": got}

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def order_id(res: Optional[dict]) -> Optional[str]:
        d = ((res or {}).get("data") or {}) if isinstance(res, dict) else {}
        oid = d.get("id") or (res or {}).get("id")
        return str(oid) if oid else None

    @staticmethod
    def fill_price(order: Optional[dict]) -> Optional[float]:
        """The average fill, or None. `filled_avg_price` is null until something fills."""
        if not isinstance(order, dict):
            return None
        d = order.get("data") if isinstance(order.get("data"), dict) else order
        return _f((d or {}).get("filled_avg_price"))

    def health(self) -> dict:
        """Is this client usable, and against what? Never raises."""
        out = {"broker": "alpaca-paper", "host": PAPER_HOST, "ok": False,
               "data_caveat": DATA_CAVEAT, "dividends": DIVIDENDS_NOT_PAID,
               "checked_at": _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"}
        try:
            acct = self.account()
        except Exception as e:                                           # noqa: BLE001
            out["reason"] = "the account could not be read (%s)" % type(e).__name__
            return out
        if not acct.get("ok"):
            out["reason"] = acct.get("reason") or "the account could not be read"
            return out
        out["ok"] = not (acct.get("trading_blocked") or acct.get("account_blocked"))
        out["equity"] = acct.get("equity")
        out["status"] = acct.get("status")
        out["paper_corroboration"] = acct.get("paper_corroboration")
        if not out["ok"]:
            out["reason"] = "the account reports trading or account blocked"
        return out
