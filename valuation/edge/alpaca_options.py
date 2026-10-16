"""ALPACA PAPER **OPTIONS** client — the paper broker every options fleet book trades in.

WHY THIS IS A SEPARATE MODULE FROM `alpaca_broker.py`
-----------------------------------------------------
`alpaca_broker.AlpacaPaperBroker` is the EQUITIES path and is another lane's file (item 65).
This builds beside it and **imports its safety model rather than restating it** (`B7`): the
host check, the live-slot clash check and `NotPaperError` all come from there, so there is one
definition of "this is the paper account" and not two that can drift apart.

WHAT IS MEASURED, NOT ASSUMED, ABOUT ALPACA PAPER OPTIONS (read 2026-10-16)
---------------------------------------------------------------------------
* **PAPER ACCOUNTS GET LEVEL 3 AUTOMATICALLY.** Alpaca: *"All paper trading accounts will
  automatically have access to Level 3 strategies. You only need to apply for your desired
  level if you are looking to live trade options."* So nothing has to be applied for, and the
  approval step that blocks a real IRA does not block the paper record.
* **MARKET AND LIMIT ONLY, AND NO EXTENDED HOURS.** Alpaca: *"Extended hours is not supported
  for options trading"* and *"options market orders are only allowed during market hours"*.
  **This is a live constraint on a scheduled fleet cycle**, which runs after the close — a
  market order sent then is rejected, so this module's default is a LIMIT order and the
  caller must ask for a market one explicitly.
* **THE FREE FEED IS `indicative`, AND IT IS NOT AN EXECUTABLE QUOTE.** Alpaca's own
  description: the indicative feed is *"a free derivative of the original OPRA feed where
  quotes are not actual OPRA quotes but indicative derivatives"*, trades are **delayed 15
  minutes**, and their staff say it is *"not real data and should not be used for live
  trading but it provides numbers to use for debugging one's code."* `opra` is the real
  consolidated feed and is a paid subscription.
* **HOW PAPER FILLS AN OPTION ORDER IS NOT DOCUMENTED.** Searched; Alpaca does not say. A user
  measured the paper chain as 15 minutes delayed. **So a paper options fill is evidence that
  the MACHINERY runs and is NOT evidence about execution quality**, which is exactly what
  `ALPACA_SETUP.md` predicted ("scoring yes, settling no") and what `O10`/`O18` already priced:
  a real options trade pays about **two thirds** of the quoted half-spread (rho 0.6743) and a
  passive fill loses **74%** of its gross saving to adverse selection. Every fill this module
  records therefore carries `feed` and `executable=False`, and `FILL_REALISM_CAVEAT` is the
  sentence any surface showing one must print.

THE REFUSALS, AND WHY THEY ARE HERE RATHER THAN IN A BOOK
----------------------------------------------------------
A book's declaration is frozen and a broker is shared, so the broker is where a structure that
**no IRA at Level 2 can hold** has to be stopped — otherwise every future book re-implements
the same check and one of them forgets. Refused by default:

  * **a naked short call** — Level 3 at best, and not permitted in a retirement account at any
    level this project could use;
  * **a short put that is not cash-secured** — the IRA form is cash-secured only.

`allow=` is the single, explicit door: a declaration that genuinely covers the structure
(`f6_collar_ledger`'s short call leg is covered by stock) passes its own reason in, and the
reason is recorded on the refusal-or-fill either way.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from ..config import CONFIG
from .alpaca_broker import (NotPaperError, PAPER_BASE, _clashes_with_a_live_slot,  # noqa: F401
                            assert_paper, live_slot_credentials)

#: Alpaca's market-data host. Orders go to the paper trading host; quotes come from here.
DATA_BASE = "https://data.alpaca.markets"

#: The only options feed a free plan gets. Named rather than defaulted, because the whole
#: point of recording it on every fill is that a later reader can tell which feed priced it.
FREE_FEED = "indicative"

#: The sentence any surface showing one of these fills must print. `O10`/`O18` are this
#: project's own measurements and are what make the caveat a number rather than a worry.
FILL_REALISM_CAVEAT = (
    "Alpaca paper options fills are priced off the free INDICATIVE feed - Alpaca's own words: "
    "quotes are 'not actual OPRA quotes but indicative derivatives', trades are delayed 15 "
    "minutes, and the feed is 'not real data and should not be used for live trading'. How "
    "paper fills an option order is NOT documented. This project measured a real options "
    "trade paying about two thirds of the quoted half-spread (O10/O18, rho 0.6743), so these "
    "fills are evidence that the machinery runs and are NOT evidence about execution quality.")

#: Structures refused outright. The key is (right, side).
_NEVER_IN_AN_IRA = {
    ("C", "sell"): ("a naked short call is Level 3 at best and is not permitted in a "
                    "retirement account at any level this project could use"),
}


class OptionStructureRefused(RuntimeError):
    """A structure no IRA at Level 2 can hold, refused before it reaches the wire."""


def parse_occ(occ: str) -> dict:
    """`AAPL240223C00095000` -> its parts. PURE, and it REFUSES a malformed symbol.

    Refusing matters more than parsing: the right/side pair is what the IRA guard reads, so a
    symbol this cannot parse must never reach `place_option` and be treated as a put by
    default. A wrong default here is a naked short call on the wire.
    """
    s = str(occ or "").strip().upper()
    if len(s) < 16:
        raise ValueError("not an OCC symbol: %r" % occ)
    tail = s[-15:]
    root = s[:-15]
    if not root or not root.isalpha():
        raise ValueError("not an OCC symbol (root %r): %r" % (root, occ))
    yy, mm, dd, right, strike = tail[0:2], tail[2:4], tail[4:6], tail[6], tail[7:]
    if right not in ("C", "P") or not (yy + mm + dd + strike).isdigit():
        raise ValueError("not an OCC symbol: %r" % occ)
    return {"underlying": root, "expiration": "20%s-%s-%s" % (yy, mm, dd),
            "right": right, "strike": int(strike) / 1000.0, "occ": s}


class AlpacaPaperOptions:
    """Options on the Alpaca PAPER account. Paper-only by construction, per `alpaca_broker`."""

    def __init__(self, cfg=CONFIG, base: str = PAPER_BASE, key_id: Optional[str] = None,
                 secret: Optional[str] = None, timeout: int = 20):
        # GUARD 1 and 3: the host is validated once here and every path is rebuilt from it.
        self.base = assert_paper(base)
        self.data_base = DATA_BASE
        self.timeout = int(timeout)
        # THE FLEET'S OWN SLOT FIRST, THE SHARED INDEX SLOT SECOND, AND WHICH ONE WAS USED
        # IS RECORDED. Alpaca allows up to three paper accounts, so the fleet can have its
        # own; until it does, a book that needs CASH cannot safely share with the Index slot
        # (deployed at 100%), and `dedicated` is what `fleet_books` reads to refuse those.
        fleet_id = getattr(cfg, "alpaca_fleet_paper_key_id", "") or ""
        fleet_sec = getattr(cfg, "alpaca_fleet_paper_secret_key", "") or ""
        self.dedicated = bool(fleet_id and fleet_sec) and key_id is None and secret is None
        self.key_id = key_id or fleet_id or getattr(cfg, "alpaca_paper_key_id", "") or ""
        self.secret = secret or fleet_sec or getattr(cfg, "alpaca_paper_secret_key", "") or ""
        if not self.key_id or not self.secret:
            raise NotPaperError(
                "no Alpaca paper credentials: set ALPACA_FLEET_PAPER_KEY_ID / "
                "ALPACA_FLEET_PAPER_SECRET_KEY (the fleet's own paper account), or "
                "ALPACA_PAPER_KEY_ID / ALPACA_PAPER_SECRET_KEY. This refuses "
                "rather than falling back to any other credential, because a broker that "
                "quietly finds a key elsewhere is how a live key comes to serve a paper book.")
        # GUARD 2: never a live slot's credential, even pointed at the paper host.
        clash = _clashes_with_a_live_slot(self.key_id, self.secret)
        if clash:
            raise NotPaperError(
                "the configured paper credential matches %s. Refusing: a crossed credential "
                "is the mistake worth catching before a scheduler runs." % clash)

    # ----------------------------------------------------------------- plumbing
    def _headers(self) -> dict:
        return {"APCA-API-KEY-ID": self.key_id, "APCA-API-SECRET-KEY": self.secret,
                "accept": "application/json", "content-type": "application/json"}

    def _request(self, method: str, url: str, body: dict = None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace") if hasattr(e, "read") else str(e)
            try:
                return {"error": json.loads(raw), "http_status": e.code}
            except Exception:                                        # noqa: BLE001
                return {"error": raw, "http_status": e.code}
        except Exception as e:                                       # noqa: BLE001
            return {"error": str(e)}
        try:
            return json.loads(raw) if raw else {}
        except Exception:                                            # noqa: BLE001
            return {"error": "non-JSON response", "raw": raw[:500]}

    def _trade(self, path: str, method: str = "GET", body: dict = None):
        return self._request(method, "%s/v2/%s" % (self.base, path.lstrip("/")), body)

    # ----------------------------------------------------------------- reads
    def quotes(self, symbols, *, feed: str = FREE_FEED) -> dict:
        """`{occ: {bid, ask, mid, feed, executable}}` for OCC symbols. Never raises.

        **`executable` IS ALWAYS FALSE ON THE FREE FEED AND IS CARRIED ON THE QUOTE**, so a
        caller cannot take a mid from here and record it as though it were a firm one. The
        fleet writes `quote_bid`/`quote_ask`/`quote_mid` straight onto the fill (`V5`'s two
        columns that nobody took), and this is what tells a later reader what they are.
        """
        syms = [str(s).strip().upper() for s in (symbols or []) if str(s).strip()]
        if not syms:
            return {}
        url = "%s/v1beta1/options/quotes/latest?%s" % (
            self.data_base, urllib.parse.urlencode({"symbols": ",".join(syms), "feed": feed}))
        got = self._request("GET", url) or {}
        out = {}
        for occ, q in ((got.get("quotes") or {}) if isinstance(got, dict) else {}).items():
            bid, ask = _num(q.get("bp")), _num(q.get("ap"))
            mid = ((bid + ask) / 2.0) if (bid is not None and ask is not None
                                          and ask > 0 and bid > 0) else None
            out[str(occ)] = {"bid": bid, "ask": ask, "mid": mid, "feed": feed,
                             "executable": False, "asof": q.get("t")}
        return out

    def chain(self, underlying: str, *, feed: str = FREE_FEED, limit: int = 1000) -> dict:
        """The option chain snapshot for one underlying. Never raises."""
        url = "%s/v1beta1/options/snapshots/%s?%s" % (
            self.data_base, urllib.parse.quote(str(underlying).upper()),
            urllib.parse.urlencode({"feed": feed, "limit": int(limit)}))
        return self._request("GET", url) or {}

    def account(self) -> dict:
        return self._trade("account") or {}

    def positions(self) -> list:
        got = self._trade("positions")
        return got if isinstance(got, list) else []

    def order(self, order_id) -> dict:
        if not order_id:
            return {}
        return self._trade("orders/%s" % urllib.parse.quote(str(order_id))) or {}

    def cancel(self, order_id) -> dict:
        if not order_id:
            return {}
        return self._trade("orders/%s" % urllib.parse.quote(str(order_id)),
                           method="DELETE") or {}

    # ----------------------------------------------------------------- the guard
    @staticmethod
    def check_structure(occ: str, side: str, *, allow: str = "") -> Optional[str]:
        """`None` if the structure may be placed, else the REASON it is refused. PURE.

        `allow` is the one door and it is a REASON rather than a boolean, so a declaration
        that opens it has to say why and the why is recorded.
        """
        p = parse_occ(occ)
        key = (p["right"], str(side or "").strip().lower())
        why = _NEVER_IN_AN_IRA.get(key)
        if why is None:
            return None
        if str(allow or "").strip():
            return None
        return why

    # ----------------------------------------------------------------- the write
    def place_option(self, occ: str, underlying: str = None, side: str = "buy", qty: int = 1,
                     price: float = None, *, allow: str = "", order_type: str = None,
                     time_in_force: str = "day") -> dict:
        """One single-leg option order on the PAPER account.

        **THE DEFAULT IS A LIMIT ORDER WHEN A PRICE IS GIVEN AND A MARKET ORDER ONLY WHEN ONE
        IS NOT**, because Alpaca rejects an options market order outside market hours and the
        fleet cycle runs after the close. The caller may force either with `order_type`.

        Signature matches `paper_broker.PaperBroker.place_option` so the fleet can swap brokers
        without the call site changing (`underlying` is accepted and unused — Alpaca derives it
        from the OCC symbol — and dropping the parameter would break that swap).
        """
        refused = self.check_structure(occ, side, allow=allow)
        if refused:
            raise OptionStructureRefused(refused)
        p = parse_occ(occ)
        typ = order_type or ("limit" if price is not None else "market")
        body = {"symbol": p["occ"], "qty": str(int(qty)),
                "side": "buy" if str(side).lower().startswith("buy") else "sell",
                "type": typ, "time_in_force": time_in_force}
        if typ == "limit":
            if price is None:
                return {"error": "a limit order needs a price", "refused": True}
            body["limit_price"] = str(round(float(price), 2))
        res = self._trade("orders", method="POST", body=body) or {}
        res["_submitted"] = {"occ": p["occ"], "side": body["side"], "qty": int(qty),
                             "type": typ, "limit_price": body.get("limit_price"),
                             "allow_reason": str(allow or "")}
        return res

    # ----------------------------------------------------------------- response parsers
    #
    # THESE ARE WHY THE FLEET COULD NOT SIMPLY BE REPOINTED. `fleet.submit` parsed every
    # response with Tradier's `PaperBroker.order_id`, which reads `res["order"]["id"]` --
    # Alpaca returns `id` at the TOP LEVEL, so the id would have come back `None` on every
    # order and the harness would have recorded a submission it could never poll. That is
    # EXACTLY F-3's state on the Tradier sandbox: 72 orders, all `fate=working`, no fill
    # price, and no order-id column at all. Swapping the broker without these would have
    # reproduced the dead end in a new venue.
    @staticmethod
    def order_id(res: Optional[dict]) -> Optional[str]:
        oid = (res or {}).get("id")
        return str(oid) if oid not in (None, "") else None

    @staticmethod
    def fill_price(order: Optional[dict]) -> Optional[float]:
        o = order or {}
        v = _num(o.get("filled_avg_price"))
        q = _num(o.get("filled_qty"))
        if v is not None and v > 0 and q is not None and q > 0:
            return v
        return None

    def health(self) -> dict:
        a = self.account() or {}
        return {"broker": "alpaca_paper_options", "host": self.base,
                "feed": FREE_FEED, "executable_quotes": False,
                "dedicated_fleet_account": bool(self.dedicated),
                "ok": bool(a and not a.get("error")),
                "account_number_shape": str(a.get("account_number", ""))[:1],
                "caveat": FILL_REALISM_CAVEAT}


def _num(x) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:                                                # noqa: BLE001
        return None
