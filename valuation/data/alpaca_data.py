"""ALPACA MARKET DATA — bars and snapshots, read-only.  [item 59]

Nothing in this project read Alpaca market data before this module. It exists so the seam can be
MEASURED before anything switches, which is item 59's own order: measure first, then switch where
the measurement supports it.

THE ONE THING MOST LIKELY TO GO WRONG, SO IT CANNOT BE DEFAULTED
----------------------------------------------------------------
**Alpaca's own `adjustment` default is `raw` — unadjusted.** The bound Index record's basis is
**ADJUSTED**: `prices.get_history_df`'s docstring records the measurement, re-deriving the
benchmark leg of all 24 recorded rows on both bases and finding that of the 6 rows that can
discriminate, **6 match adjusted exactly and 0 match plain**. So a caller who omitted the
parameter would silently change the basis of the one series that cannot be rebuilt — the
split-trap that already cost items 36 and 39, and the trap this project records as
*"`raw_close` for anything touching a STRIKE, `close` only for a RETURN"*.

So **`adjustment` is a required keyword with no default**. `MA5`'s lesson, in the place it would
cost the most: a default is exactly how a convention changes under you.

WHAT THE FREE PLAN IS, FROM THE DOCS, AND WHERE THE DOCS DISAGREE WITH THEMSELVES
--------------------------------------------------------------------------------
Read 2026-10-14 from Alpaca's own plan comparison and market-data overview:

* **Equities: IEX only.** "All US Exchanges" is listed as an *Algo Trader Plus* upgrade.
* **15-minute delay via API** for real-time access; 7+ years of history (since ~2016).
* **200 API calls/min** on Basic, unlimited on the paid tier.
* **Options: indicative**, never real-time.
* Corporate actions, aggregate bars and snapshots are **identical between plans**.

And the tension, recorded because it is the reason `feed_probe` exists: the same marketing page
claims **"100% market coverage"** beside **"IEX exchange only"**. Those cannot both be the plain
reading, and item 59 asks whether the consolidated (SIP) close is reachable once data is more
than 15 minutes old. **That is not answerable from the documentation**, so this module does not
guess: `feed_probe()` ASKS THE API and records the status it gets back.

WHAT ALPACA DOES NOT CARRY, so nothing here is expected to replace it
---------------------------------------------------------------------
No financial statements, no company descriptions, no earnings dates, no analyst estimates. Those
stay on Yahoo with item 57's SEC fallback, and item 59 says so explicitly.

NO KEY IS EVER PRINTED
----------------------
The credentials travel in HEADERS rather than a query string, which is already safer than FMP's
route — but every error body is still passed through `scrub` before it reaches a log or a
payload, because a vendor is free to echo a header back in a message.
"""
from __future__ import annotations

import json
import os
from typing import Optional

#: The DATA host. Separate from the trading hosts, and it is the same for paper and live keys --
#: market data is not an account action, so there is no paper/live distinction to protect here.
DATA_BASE = "https://data.alpaca.markets"

#: The adjustments Alpaca accepts, verbatim from its docs. `all` = split + dividend + spin-off.
ADJ_RAW, ADJ_SPLIT, ADJ_DIVIDEND, ADJ_ALL = "raw", "split", "dividend", "all"
ADJUSTMENTS = (ADJ_RAW, ADJ_SPLIT, ADJ_DIVIDEND, ADJ_ALL)

#: THE ONE THAT MATCHES THE RECORDED BASIS. `yfinance`'s `auto_adjust=True` applies splits AND
#: dividends, and `prices.VENDOR_ADJUSTMENT` records that as `auto_adjusted`. `all` is the
#: closest Alpaca equivalent; whether they AGREE is a measurement, not an assumption, and that
#: is exactly what the seam study is for.
ADJ_FOR_RECORDED_BASIS = ADJ_ALL

#: The feeds Alpaca names. `iex` is what the free plan is documented to serve.
FEEDS = ("iex", "sip", "delayed_sip", "otc", "boats", "overnight")
FREE_FEED = "iex"

#: 200 requests/min on the Basic plan, published. Used to SIZE batches rather than discovered by
#: hitting it -- item 59's own instruction, and `thetadata-serializes-the-account`'s lesson that
#: a vendor's published limit is cheaper to read than to find.
FREE_RATE_PER_MIN = 200

#: How many symbols travel in one `symbols=` parameter. Alpaca accepts a comma-separated list;
#: the brief's instruction is "the multi-symbol bars and snapshots endpoints, not one call per
#: name". 100 keeps a 222-name sample inside 3 requests per page rather than 222.
SYMBOLS_PER_CALL = 100

#: Read from the response rather than counted locally. Alpaca publishes its own remaining budget,
#: and a locally-counted estimate drifts the moment anything else on the service makes a call.
RATE_HEADERS = ("x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset")

KEY_ID_VAR = "ALPACA_PAPER_KEY_ID"
SECRET_VAR = "ALPACA_PAPER_SECRET_KEY"


class AlpacaDataError(RuntimeError):
    pass


def scrub(text, *secrets) -> str:
    """Remove any credential from a string before it is logged or returned.

    The keys travel in headers here, so an echo is unlikely rather than impossible -- and
    "unlikely" is not a reason to print one. `FMP_SEAM` had to scrub because the key was in the
    query string; this scrubs because a vendor message is not under our control.
    """
    s = "" if text is None else str(text)
    for sec in secrets:
        if sec and len(str(sec)) >= 8:
            s = s.replace(str(sec), "***")
    return s


def credentials(env=None) -> tuple:
    """`(key_id, secret)` or `("", "")`. **Never returns a partial pair as usable.**

    Half a pair cannot authenticate, so reporting it as present would promise a working client
    that does not exist -- `MA6`'s direction, and the same rule `live_cycle.key_presence` uses.
    """
    e = env if env is not None else os.environ
    k = (e.get(KEY_ID_VAR, "") or "").strip()
    s = (e.get(SECRET_VAR, "") or "").strip()
    return (k, s) if (k and s) else ("", "")


def have_keys(env=None) -> bool:
    return bool(credentials(env)[0])


class AlpacaData:
    """Read-only market data. **This class places no orders and has no write method.**

    It is deliberately NOT part of `alpaca_broker`: that module's whole job is refusing to point
    at the live trading host, and market data has no paper/live distinction to protect. Keeping
    them apart means the data path can never acquire an order method by proximity, and a test
    asserts this module defines none.
    """

    def __init__(self, key_id: str = None, secret: str = None, *, base: str = DATA_BASE,
                 env=None, timeout: int = 30, session=None):
        if key_id is None or secret is None:
            key_id, secret = credentials(env)
        if not key_id or not secret:
            raise AlpacaDataError(
                "no Alpaca key pair is configured (%s and %s). Market data needs both; half a "
                "pair cannot authenticate." % (KEY_ID_VAR, SECRET_VAR))
        self.base = base.rstrip("/")
        self._key_id, self._secret = key_id, secret
        self.timeout, self._session = int(timeout), session
        self.last_rate: dict = {}

    # ------------------------------------------------------------------ plumbing
    def _headers(self) -> dict:
        return {"APCA-API-KEY-ID": self._key_id, "APCA-API-SECRET-KEY": self._secret,
                "accept": "application/json"}

    def _get(self, path: str, params: dict) -> dict:
        """One GET. Returns `{ok, status, data, error, rate}`; NEVER raises on an HTTP error.

        A vendor refusal is a FACT the measurement needs to record -- a 403 on `feed=sip` is the
        answer to item 59's plan question -- so it travels back as data rather than as an
        exception the caller has to catch to learn anything.
        """
        import requests
        sess = self._session or requests
        url = "%s/%s" % (self.base, str(path).lstrip("/"))
        try:
            r = sess.request("GET", url, headers=self._headers(), params=params,
                             timeout=self.timeout)
        except Exception as e:                                          # noqa: BLE001
            return {"ok": False, "status": 0, "data": {},
                    "error": scrub("%s: %s" % (type(e).__name__, e), self._key_id,
                                   self._secret),
                    "rate": {}}
        rate = {}
        try:
            for h in RATE_HEADERS:
                if h in (r.headers or {}):
                    rate[h] = r.headers[h]
        except Exception:                                               # noqa: BLE001
            rate = {}
        self.last_rate = rate or self.last_rate
        code = getattr(r, "status_code", 0)
        try:
            payload = r.json()
        except Exception:                                               # noqa: BLE001
            payload = {"raw": scrub(getattr(r, "text", "")[:400], self._key_id, self._secret)}
        if code >= 400:
            return {"ok": False, "status": code, "data": {},
                    "error": scrub(json.dumps(payload)[:400], self._key_id, self._secret),
                    "rate": rate}
        return {"ok": True, "status": code, "data": payload, "error": "", "rate": rate}

    # ------------------------------------------------------------------ bars
    def bars(self, symbols, *, adjustment: str, start: str = None, end: str = None,
             timeframe: str = "1Day", feed: str = None, limit: int = 10000,
             max_pages: int = 20) -> dict:
        """Daily (or other) bars for MANY symbols in one call, paginated.

        **`adjustment` IS REQUIRED AND HAS NO DEFAULT.** See the module docstring: Alpaca's own
        default is `raw`, the recorded basis is adjusted, and a silent `raw` would change the
        basis of the one series that cannot be rebuilt.

        Returns `{ok, bars: {SYM: [bar, ...]}, missing: [...], pages, rate, adjustment, feed,
        error}`. A symbol Alpaca does not return is reported in `missing` rather than as an
        empty list, because "no bars" and "not covered" are different facts and item 40's FMP
        measurement died on exactly the second one.
        """
        if adjustment not in ADJUSTMENTS:
            raise AlpacaDataError(
                "adjustment must be one of %r and must be passed explicitly: Alpaca's own "
                "default is %r, and the recorded Index basis is ADJUSTED, so an omitted "
                "parameter silently changes the basis of a series that cannot be rebuilt."
                % (ADJUSTMENTS, ADJ_RAW))
        want = [str(s).strip().upper() for s in (symbols or []) if str(s).strip()]
        out = {"ok": True, "bars": {}, "missing": [], "pages": 0, "rate": {},
               "adjustment": adjustment, "feed": feed or "(vendor default)", "error": "",
               "requests": 0}
        for i in range(0, len(want), SYMBOLS_PER_CALL):
            chunk = want[i:i + SYMBOLS_PER_CALL]
            token, pages = None, 0
            while True:
                params = {"symbols": ",".join(chunk), "timeframe": timeframe,
                          "adjustment": adjustment, "limit": int(limit)}
                if start:
                    params["start"] = start
                if end:
                    params["end"] = end
                if feed:
                    params["feed"] = feed
                if token:
                    params["page_token"] = token
                got = self._get("/v2/stocks/bars", params)
                out["requests"] += 1
                out["rate"] = got.get("rate") or out["rate"]
                if not got["ok"]:
                    out["ok"] = False
                    out["error"] = "%s (HTTP %s)" % (got["error"], got["status"])
                    return out
                body = got["data"] or {}
                for sym, rows in (body.get("bars") or {}).items():
                    out["bars"].setdefault(str(sym).upper(), []).extend(rows or [])
                token = body.get("next_page_token")
                pages += 1
                out["pages"] += 1
                # A PAGE CAP THAT IS REPORTED RATHER THAN SILENT. Truncating a series without
                # saying so is how a short history reads as a complete one.
                if not token or pages >= int(max_pages):
                    if token:
                        out["error"] = ("stopped at the %d-page cap for %s with more pages "
                                        "available: the series is TRUNCATED"
                                        % (max_pages, chunk[0]))
                    break
        out["missing"] = sorted(s for s in want if s not in out["bars"])
        return out

    def snapshots(self, symbols, *, feed: str = None) -> dict:
        """Latest trade/quote/bar per symbol, many symbols per call.

        No `adjustment` parameter exists on this endpoint and none is invented: Alpaca's own
        note is that **trade and quote data is only ever raw** and only BARS are adjusted. So a
        snapshot's prices are as-traded, which is the right basis for anything touching a
        strike and the WRONG one for the recorded track -- stated here because the two
        endpoints differ and a caller reading one convention onto the other is the whole
        split-trap family.
        """
        want = [str(s).strip().upper() for s in (symbols or []) if str(s).strip()]
        out = {"ok": True, "snapshots": {}, "missing": [], "rate": {}, "error": "",
               "basis": "as-traded (Alpaca adjusts BARS only; trades and quotes are raw)",
               "requests": 0}
        for i in range(0, len(want), SYMBOLS_PER_CALL):
            chunk = want[i:i + SYMBOLS_PER_CALL]
            params = {"symbols": ",".join(chunk)}
            if feed:
                params["feed"] = feed
            got = self._get("/v2/stocks/snapshots", params)
            out["requests"] += 1
            out["rate"] = got.get("rate") or out["rate"]
            if not got["ok"]:
                out["ok"] = False
                out["error"] = "%s (HTTP %s)" % (got["error"], got["status"])
                return out
            body = got["data"] or {}
            rows = body.get("snapshots") if isinstance(body.get("snapshots"), dict) else body
            for sym, snap in (rows or {}).items():
                if isinstance(snap, dict):
                    out["snapshots"][str(sym).upper()] = snap
        out["missing"] = sorted(s for s in want if s not in out["snapshots"])
        return out

    # ------------------------------------------------------------------ the plan question
    def feed_probe(self, symbol: str = "AAPL", *, start: str = None, end: str = None) -> dict:
        """ASK THE API which feeds this key can read. Item 59's plan question, measured.

        The documentation is in tension with itself -- "100% market coverage" beside "IEX
        exchange only", and a 15-minute delay whose feed is not named -- so this does not infer
        the answer. It requests each feed for ONE symbol and records the status.

        **A CONTROL NAME, NOT AN ARBITRARY ONE.** AAPL is priced by every vendor this project
        has ever used, so "it did not resolve" is a fact about the FEED rather than about the
        ticker. That is the `stooq-is-dead` lesson, where a primary vendor returning 404 for
        *every* symbol was only distinguishable from missing tickers by a control.
        """
        out = {"symbol": symbol, "feeds": {}, "readable": [], "refused": [],
               "note": ("measured by asking, because Alpaca's own pages claim '100%% market "
                        "coverage' and 'IEX exchange only' on the same plan")}
        for f in FEEDS:
            got = self._get("/v2/stocks/bars",
                            {"symbols": symbol, "timeframe": "1Day", "adjustment": ADJ_RAW,
                             "limit": 1, "feed": f,
                             **({"start": start} if start else {}),
                             **({"end": end} if end else {})})
            n = len(((got.get("data") or {}).get("bars") or {}).get(symbol.upper()) or [])
            out["feeds"][f] = {"ok": bool(got["ok"]), "status": got["status"], "bars": n,
                               "error": (got["error"] or "")[:200]}
            (out["readable"] if (got["ok"] and n) else out["refused"]).append(f)
        return out

    def rate_budget(self) -> dict:
        """What the VENDOR says is left, plus the published plan limit for context."""
        return {"published_per_min": FREE_RATE_PER_MIN, "headers": dict(self.last_rate),
                "note": ("read from the response headers rather than counted here; a local "
                         "count drifts as soon as anything else on the service calls")}


#: WHAT ALPACA DOES NOT CARRY. Declared so a future reader does not go looking, and so the
#: summary's claim is checkable against the docs rather than against memory.
NOT_CARRIED = (
    "company financial statements (income statement, balance sheet, cash flow)",
    "company descriptions and business summaries",
    "earnings dates and analyst estimates",
    "shares outstanding and market capitalisation as a fundamental field",
)

#: And what it does, on the free plan.
CARRIED_FREE = (
    "daily and intraday aggregate bars, adjustable for splits, dividends and spin-offs",
    "snapshots: latest trade, quote and bar per symbol",
    "corporate actions (identical on the free and paid plans, per Alpaca's plan table)",
    "US options chains at INDICATIVE prices -- adequate for scoring an alert, not for "
    "settling one (O10/O18 measured a real trade paying about two thirds of the quoted "
    "half-spread)",
)
