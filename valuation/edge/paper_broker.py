"""
Tradier SANDBOX broker client — the paper account the forward track trades in.

WHY A BROKER AND NOT A QUOTE SIM. The project's #1 remaining validation is a forward,
out-of-sample track: every number in BACKTEST_RESULTS.md comes from one 18-year Sharadar panel
that has now been looked at many times, and the options edge from one reconstructed alert
history. A quote-based simulation forward would inherit the same optimism a backtest has — it
prices at whatever mark you choose and always "fills". Submitting the order to a real broker
API, even a simulated one, forces the trade through real order validation, real market hours,
real symbol resolution and a real fill/reject, so the failures that only show up in execution
(unfillable strike, order rejected, quote missing) become visible instead of assumed away.

--------------------------------------------------------------------------------------------
SANDBOX ONLY. THIS IS THE WHOLE SAFETY MODEL, SO IT IS ENFORCED, NOT DOCUMENTED.

Three independent guards, each of which fails the constructor loudly:

  1. THE BASE URL MUST BE THE SANDBOX HOST. Checked by parsing the URL and comparing the
     hostname exactly — not `"sandbox" in url`, which a string like
     `https://api.tradier.com/v1?x=sandbox` would satisfy.
  2. THE TOKEN MUST BE THE DEDICATED PAPER TOKEN. If it is empty, or if it equals the
     production `TRADIER_TOKEN` the live app's feed uses, construction fails. A production
     token pointed at the sandbox host would not trade real money, but it would mean the two
     credentials had been crossed somewhere, and that is precisely the mistake worth catching
     early rather than after it has been copied into a scheduler.
  3. NOTHING IN THIS MODULE CAN REACH PRODUCTION. `_url()` rebuilds every request path from
     `self.base`, which was validated once at construction and is never taken from a caller.

`dry_run=True` additionally sends Tradier's own `preview=true`, which runs the broker's full
order validation (buying power, symbol, strategy, commission) and returns the would-be cost
without creating an order. That is the mode used in tests and in `--dry-run` runs.

This is paper money: validation, not execution. It is consistent with the project's
no-real-trades rule — no path here can touch a funded account.
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional
from urllib.parse import urlparse

from ..config import CONFIG
from ..intraday.providers import TRADIER_SANDBOX_BASE, TradierProvider

SANDBOX_BASE = TRADIER_SANDBOX_BASE
SANDBOX_HOST = "sandbox.tradier.com"

# Sandbox market data is delayed (~15 minutes). Every mark and fill this module produces
# therefore approximates what a live account would have got, and the track must say so —
# see `DATA_CAVEAT`, which is carried through into the API payload rather than left in a
# docstring nobody reads.
DATA_CAVEAT = ("Tradier sandbox quotes are delayed ~15 minutes, so paper fills and marks are "
               "approximate - close to, but not, what a live account would have received.")


class NotSandboxError(RuntimeError):
    """Raised when anything about the configuration is not unambiguously the paper sandbox."""


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def assert_sandbox(base: str) -> str:
    """Fail unless `base` is exactly the Tradier sandbox endpoint. Returns it normalised."""
    b = (base or "").strip().rstrip("/")
    u = urlparse(b)
    if u.scheme != "https" or (u.hostname or "").lower() != SANDBOX_HOST:
        raise NotSandboxError(
            f"paper track refuses a non-sandbox endpoint: {b!r}. It must be "
            f"{SANDBOX_BASE!r} (host {SANDBOX_HOST}).")
    return b


class PaperBroker:
    """Sandbox-only Tradier account client: quotes, orders, positions, balances.

    Market data reuses the existing `TradierProvider` (pointed at the sandbox on the paper
    token) rather than a second chain reader, so the contract the paper book buys is selected
    by the same code the live alert used.
    """

    def __init__(self, cfg=CONFIG, base: str = SANDBOX_BASE, token: Optional[str] = None,
                 account_id: Optional[str] = None, dry_run: bool = False, timeout: int = 25):
        self.base = assert_sandbox(base)
        self.cfg = cfg
        self.dry_run = bool(dry_run)
        self.timeout = int(timeout)
        tok = (token if token is not None else getattr(cfg, "tradier_paper_token", "") or "").strip()
        if not tok:
            raise NotSandboxError(
                "TRADIER_PAPER_TOKEN is not set. The paper track will not fall back to "
                "TRADIER_TOKEN — that is the live app's production feed.")
        prod = (getattr(cfg, "tradier_token", "") or "").strip()
        if prod and tok == prod:
            raise NotSandboxError(
                "TRADIER_PAPER_TOKEN is identical to the production TRADIER_TOKEN. Those must "
                "be two different credentials; refusing to run the paper track on the "
                "production token.")
        self._token = tok
        self.account_id = (account_id if account_id is not None
                           else getattr(cfg, "tradier_paper_account_id", "") or "").strip()

    # ------------------------------------------------------------------ plumbing
    @property
    def provider(self) -> TradierProvider:
        """The existing market-data client, bound to the sandbox on the paper token."""
        if not hasattr(self, "_provider"):
            self._provider = TradierProvider(self.cfg, base=self.base, token=self._token)
        return self._provider

    def _url(self, path: str) -> str:
        # Rebuilt from the validated base every time: a caller cannot smuggle in a host.
        return f"{self.base}/{str(path).lstrip('/')}"

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}

    def _require_account(self) -> str:
        if not self.account_id:
            raise NotSandboxError("TRADIER_PAPER_ACCOUNT_ID is not set — no paper account to "
                                  "place or read orders against.")
        return self.account_id

    def _get(self, path: str, **params) -> dict:
        import requests
        r = requests.get(self._url(path), params=params, headers=self._headers(),
                         timeout=self.timeout)
        r.raise_for_status()
        return r.json() or {}

    def _post(self, path: str, data: dict) -> dict:
        import requests
        r = requests.post(self._url(path), data=data, headers=self._headers(),
                          timeout=self.timeout)
        # A rejected order is INFORMATION, not a crash: Tradier returns 400 with a reason, and
        # "this contract could not be bought" is exactly the kind of execution reality the paper
        # track exists to surface. Surface it as a structured error instead of an exception.
        if r.status_code >= 400:
            try:
                body = r.json()
            except ValueError:
                body = {"error": r.text[:300]}
            return {"ok": False, "http_status": r.status_code, "error": body}
        out = r.json() or {}
        out["ok"] = True
        return out

    # ------------------------------------------------------------------ market data
    def quotes(self, symbols) -> dict:
        """symbol -> quote dict. Accepts equity tickers and OCC option symbols alike."""
        syms = [s for s in ([symbols] if isinstance(symbols, str) else list(symbols or [])) if s]
        if not syms:
            return {}
        out = {}
        # Tradier caps a symbols list; chunk so a wide book cannot silently truncate.
        for i in range(0, len(syms), 100):
            chunk = syms[i:i + 100]
            try:
                d = self._get("markets/quotes", symbols=",".join(chunk), greeks="false")
            except Exception:                                        # noqa: BLE001
                continue
            q = ((d or {}).get("quotes") or {}).get("quote")
            if not q:
                continue
            for row in (q if isinstance(q, list) else [q]):
                if isinstance(row, dict) and row.get("symbol"):
                    out[row["symbol"]] = row
        return out

    @staticmethod
    def mark_from_quote(q: Optional[dict]) -> Optional[float]:
        """The mark for an option quote: mid when there are two sides, else last.

        Mid rather than last, because an option that has not traded today carries a stale
        `last` that can be days old while the bid/ask is current.
        """
        if not isinstance(q, dict):
            return None
        bid, ask = _f(q.get("bid")), _f(q.get("ask"))
        if bid is not None and ask is not None and ask > 0 and ask >= bid:
            return round((bid + ask) / 2.0, 4)
        for k in ("last", "close", "prevclose"):
            v = _f(q.get(k))
            if v is not None and v > 0:
                return v
        return None

    @staticmethod
    def exit_mark_from_quote(q: Optional[dict]) -> Optional[float]:
        """The price a LONG position could actually be SOLD at right now — the bid.

        AUDIT B5a. The exit trigger fired on `mark_from_quote`, i.e. the MID, while the backtest
        fires on the BID (`options_backtest.py` marks with `fill_price(q, "sell", aggression=1)`).
        On a 10%-wide quote that is roughly five percentage points of measured return, and it is
        ASYMMETRIC: marking at the mid reaches +100% earlier and -50% later than the backtest
        would. The forward track exists precisely to test the backtest's numbers on unseen data,
        so a systematic difference on that axis makes the two non-comparable — which is the one
        thing the track cannot afford.

        The mid remains the right number for VALUING an open position (`mark_from_quote`); it is
        the wrong number for deciding whether an exit has triggered.
        """
        if not isinstance(q, dict):
            return None
        bid, ask = _f(q.get("bid")), _f(q.get("ask"))
        if bid is not None and bid > 0 and (ask is None or ask >= bid):
            return round(bid, 4)
        return PaperBroker.mark_from_quote(q)

    # ------------------------------------------------------------------ account
    def balances(self) -> dict:
        return (self._get(f"accounts/{self._require_account()}/balances") or {}).get("balances") or {}

    def positions(self) -> list:
        d = self._get(f"accounts/{self._require_account()}/positions") or {}
        p = (d.get("positions") or {})
        # Tradier serialises "no positions" as the STRING "null", not as null.
        if not isinstance(p, dict):
            return []
        rows = p.get("position")
        if not rows:
            return []
        return rows if isinstance(rows, list) else [rows]

    def orders(self) -> list:
        d = self._get(f"accounts/{self._require_account()}/orders") or {}
        o = (d.get("orders") or {})
        if not isinstance(o, dict):
            return []
        rows = o.get("order")
        if not rows:
            return []
        return rows if isinstance(rows, list) else [rows]

    def order(self, order_id) -> dict:
        if order_id in (None, ""):
            return {}
        d = self._get(f"accounts/{self._require_account()}/orders/{order_id}") or {}
        return (d.get("order") or {})

    # ------------------------------------------------------------------ orders
    def place_option(self, occ_symbol: str, underlying: str, side: str, quantity: int,
                     price: Optional[float] = None, duration: str = "day") -> dict:
        """Single-leg option order. `side` is buy_to_open / sell_to_close.

        LIMIT when a price is given, MARKET otherwise. The paper book prices entries at the ASK
        and exits at the BID, matching `options_fill.DEFAULT_AGGRESSION = 1.0` — the punishing
        fill convention every validated options number in this repo is net of. Marking the
        paper book at the mid would quietly make the forward track look better than the
        backtest it is meant to test.
        """
        payload = {"class": "option", "symbol": str(underlying).upper(),
                   "option_symbol": str(occ_symbol).upper(), "side": side,
                   "quantity": str(int(quantity)), "duration": duration}
        px = _f(price)
        if px is not None and px > 0:
            payload["type"], payload["price"] = "limit", f"{px:.2f}"
        else:
            payload["type"] = "market"
        if self.dry_run:
            payload["preview"] = "true"
        res = self._post(f"accounts/{self._require_account()}/orders", payload)
        res["dry_run"] = self.dry_run
        return res

    def place_equity(self, ticker: str, side: str, quantity: int,
                     price: Optional[float] = None, duration: str = "day") -> dict:
        """Equity order (buy / sell). Used only by the opt-in equity mirror of the Index."""
        payload = {"class": "equity", "symbol": str(ticker).upper(), "side": side,
                   "quantity": str(int(quantity)), "duration": duration}
        px = _f(price)
        if px is not None and px > 0:
            payload["type"], payload["price"] = "limit", f"{px:.2f}"
        else:
            payload["type"] = "market"
        if self.dry_run:
            payload["preview"] = "true"
        res = self._post(f"accounts/{self._require_account()}/orders", payload)
        res["dry_run"] = self.dry_run
        return res

    def _delete(self, path: str) -> dict:
        import requests
        r = requests.delete(self._url(path), headers=self._headers(), timeout=self.timeout)
        if r.status_code >= 400:
            try:
                body = r.json()
            except ValueError:
                body = {"error": r.text[:300]}
            return {"ok": False, "http_status": r.status_code, "error": body}
        out = r.json() or {}
        out["ok"] = True
        return out

    def cancel(self, order_id) -> dict:
        """Cancel a working order. Added for `F-1`'s frozen arm B, not as a convenience.

        The declaration's arm B is *"limit at mid, worked 60 seconds, then
        cancel-and-market"*. There was no cancel on this broker, so that clause was
        **unimplementable as written** -- and the honest fix is to build the missing verb
        rather than to quietly redefine arm B as *"place a limit and hope"*. A limit left
        working while a market order is sent beside it is a DOUBLE POSITION, which on a book
        whose entire subject is fill quality would corrupt exactly the measurement it exists
        to take.

        A failed cancel is returned, never raised: the caller must be able to see that the
        limit is still live and decline to send the market leg. Sending both is the one
        outcome worse than sending neither.
        """
        return self._delete(f"accounts/{self._require_account()}/orders/{order_id}")

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def order_id(res: Optional[dict]) -> Optional[str]:
        o = ((res or {}).get("order") or {})
        oid = o.get("id")
        return str(oid) if oid not in (None, "") else None

    @staticmethod
    def fill_price(order: Optional[dict]) -> Optional[float]:
        """Average fill price of a (possibly partially) filled order, else None."""
        o = order or {}
        for k in ("avg_fill_price", "last_fill_price", "price"):
            v = _f(o.get(k))
            if v is not None and v > 0 and _f(o.get("exec_quantity")):
                return v
        v = _f(o.get("avg_fill_price"))
        return v if (v is not None and v > 0) else None

    def health(self) -> dict:
        """One call a runner can log: is the sandbox reachable and is this the paper account."""
        out = {"base": self.base, "sandbox": True, "account_id": self.account_id,
               "dry_run": self.dry_run, "data_caveat": DATA_CAVEAT}
        try:
            b = self.balances()
            out["ok"] = True
            out["total_equity"] = _f(b.get("total_equity"))
            out["total_cash"] = _f(b.get("total_cash"))
            out["account_type"] = b.get("account_type")
        except Exception as e:                                       # noqa: BLE001
            out["ok"] = False
            out["error"] = f"{type(e).__name__}: {e}"
        return out


def today_iso() -> str:
    return _dt.date.today().isoformat()


def now_iso() -> str:
    return _dt.datetime.now().replace(microsecond=0).isoformat()
