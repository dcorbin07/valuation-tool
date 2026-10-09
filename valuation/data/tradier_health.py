# -*- coding: utf-8 -*-
"""ITEM 45 - does the live Tradier token WORK? One definition, asked once per process.

THE DEFECT, AND IT WAS IN THREE PLACES AT ONCE. `intraday/providers.get_provider`,
`screener/broker_universe.available` and `screener/broker_fundamentals.available` all answered
"have we got a broker?" with `bool(cfg.tradier_token)` -- **the token's PRESENCE, never whether
it works.** Don withdrew his funds, Tradier deactivated the account, and the token stayed
non-empty while every request began answering `401 "Access Token not approved"`. So:

  * the intraday scan still chose Tradier, every method swallowed its 401 into `None`, and the
    run printed `scored 0 of 150 names -- nothing scored -- not ingesting` and exited 1
    (run 37853898863, 2026-10-08 22:31 UTC) while `/api/signals` froze at 2026-10-08 00:20;
  * the hot scan still chose the broker universe and the broker fundamentals prefetch, which
    then loaded nothing -- `broker fundamentals loaded for 0 of 1500 names`.

**A PRESENT TOKEN IS NOT A WORKING TOKEN, and nothing can tell the difference without making a
request.** So one read-only request decides it, in one place, and the three callers ask here.

WHY IT IS CACHED PER PROCESS. The hot scan asks twice (universe, then fundamentals) and the
intraday scan once; a probe per call would add requests to every scan to re-answer a question
whose answer cannot change mid-run. `refresh=True` re-asks, and the cache key is a DIGEST of
the credentials rather than the credentials, so nothing here can leak a token into a dict a
caller might print.

WHY AN UNREACHABLE HOST ANSWERS "NO". A probe that cannot reach Tradier does not know whether
the token is good -- but the two actions available are "use Tradier" and "use the documented
free route", and the free route works either way. Degrading on uncertainty is the safe
direction; claiming availability on uncertainty is the behaviour this module exists to end.
The DISTINCTION IS STILL REPORTED in the detail string, so a network outage is never written
down as a dead account.
"""
from __future__ import annotations

import hashlib

from ..config import CONFIG

LIVE_BASE = "https://api.tradier.com/v1"
SANDBOX_BASE = "https://sandbox.tradier.com/v1"

#: Read-only, and the same endpoint the Signals scan actually reads, so a pass here means the
#: thing the caller is about to do will work -- not merely that some endpoint answered.
PROBE_PATH = "/markets/quotes"
PROBE_SYMBOL = "AAPL"

_CACHE: dict = {}


def base_for(cfg=CONFIG) -> str:
    return LIVE_BASE if str(getattr(cfg, "tradier_env", "")).lower() == "live" else SANDBOX_BASE


def _key(token: str, base: str) -> str:
    """A digest, never the token. Caching on the value itself would put a live credential in a
    module-level dict, which is one `repr()` away from a log line."""
    return hashlib.sha256(("%s|%s" % (base, token)).encode("utf-8")).hexdigest()[:16]


def live_token_works(cfg=CONFIG, *, refresh: bool = False, timeout: int = 20) -> tuple:
    """`(works, detail)`. Never returns, logs or caches the token itself.

    `detail` is empty on success and otherwise says WHY, scrubbed: `no TRADIER_TOKEN
    configured`, `HTTP 401: Access Token not approved`, `unreachable (ConnectionError)`.
    """
    token = (getattr(cfg, "tradier_token", "") or "").strip()
    if not token:
        return False, "no TRADIER_TOKEN configured"

    base = base_for(cfg)
    k = _key(token, base)
    if not refresh and k in _CACHE:
        return _CACHE[k]

    try:
        import requests
        r = requests.get(base + PROBE_PATH, params={"symbols": PROBE_SYMBOL},
                         headers={"Authorization": "Bearer " + token,
                                  "Accept": "application/json"}, timeout=timeout)
    except Exception as e:                                            # noqa: BLE001
        out = (False, "unreachable (%s)" % type(e).__name__)
        _CACHE[k] = out
        return out

    if r.status_code == 200:
        out = (True, "")
    elif r.status_code in (401, 403):
        fault = ""
        try:
            fault = ((r.json() or {}).get("fault") or {}).get("faultstring") or ""
        except Exception:                                             # noqa: BLE001
            fault = ""
        fault = str(fault).replace(token, "<REDACTED>")
        out = (False, "HTTP %d%s" % (r.status_code, ": " + fault if fault else ""))
    else:
        out = (False, "HTTP %d" % r.status_code)
    _CACHE[k] = out
    return out


def reset_cache() -> None:
    """For tests. A process-level cache that a test cannot clear is a test-ordering bug
    waiting to be written."""
    _CACHE.clear()
