"""Per-process cache of computed valuations, so a download matches the page it came from.

WHY A CACHE AT ALL. `/api/export/excel` and `/api/export/pdf` render the document behind
the page the visitor is looking at. Recomputing from scratch would spend a second vendor
call and — worse — would price the model off a different quote, so the workbook would
quietly disagree with the screen it was downloaded from. Serving the result the page
rendered is the right idea. The previous implementation was a bare module-level dict
(`_LAST`), and it got three things wrong:

  KEYED BY THE TICKER ALONE. The cache ignored the assumptions the result was computed
  under, so one visitor's overridden valuation was served as the next visitor's default
  document. Measured on the NKE fixture: a `wacc=0.25` override moves fair value $40.15 ->
  $22.97, and the second visitor's export was handed the $22.97 one. The key here is the
  whole request — ticker plus overrides plus peer set — so two different questions can
  never collide on one answer.

  UNSTAMPED. Nothing recorded when a result was computed, and nothing expires, so an entry
  lived until the worker restarted and a document rendered from a days-old result was
  indistinguishable from a fresh one. (`data/macro.py` already does this correctly: a `ts`
  and a TTL.) Every entry now carries `computed_at`, the reports print it, and anything
  past TTL_SECONDS is recomputed instead of served.

  UNBOUNDED. Every ticker ever valued stayed resident for the life of the process. ~9 KB
  pickled per result is not a crisis, but it is monotonic on a 512 MB box running two
  workers, and a bound costs one line.

Deliberately still PER PROCESS. Production runs `--workers ${WEB_CONCURRENCY:-2}`, so
there are two of these and a visitor's page and their download can be answered by
different ones. That is fine now and was not before: on a miss the export recomputes under
the SAME assumptions the page used (they travel in the query string), so the worst case is
a fresh computation rather than another worker's stale answer. A shared cache would need
Redis or the database, which is a much larger change for a document that is cheap to
rebuild.

No Flask import: the policy is a plain object so it can be tested without a request.
"""
from __future__ import annotations

import datetime as _dt
import threading
from collections import OrderedDict
from typing import Any, Optional

#: How long a computed valuation may still be served as "the page you were looking at".
#: The real gap between rendering the page and clicking Export is seconds; fifteen minutes
#: covers a distracted user and still bounds how far the document can drift from the quote
#: it was priced against. Past this the export recomputes, which is the honest answer.
TTL_SECONDS = 900

#: Entries retained per worker, least-recently-used evicted first.
MAX_ENTRIES = 256


class Entry:
    """One cached valuation and the facts needed to know whether it still applies."""

    __slots__ = ("result", "computed_at", "key")

    def __init__(self, result: Any, computed_at: float, key: str):
        self.result = result
        self.computed_at = computed_at
        self.key = key

    def age(self, now: float) -> float:
        return max(0.0, now - self.computed_at)

    @property
    def stamp(self) -> str:
        return stamp(self.computed_at)


def stamp(computed_at: Optional[float]) -> Optional[str]:
    """The compute time as the documents and the page print it.

    UTC and minute resolution on purpose: this is a "how fresh is this" marker, not a
    timestamp anyone should parse, and a server-local time would mean different things on
    a laptop and on Render.
    """
    if computed_at is None:
        return None
    dt = _dt.datetime.fromtimestamp(float(computed_at), _dt.timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def request_key(ticker: str, overrides: Optional[dict] = None,
                peers: Optional[list] = None) -> str:
    """The identity of the QUESTION, not just the company.

    Two requests share an answer only if they would produce the same one. Overrides are
    formatted rather than repr'd so 0.1 and 0.10000000000000001 land on the same key;
    non-numeric junk is kept as-is rather than dropped, because dropping it would merge
    two requests that are not the same.
    """
    parts = [(ticker or "").strip().upper()]
    for k in sorted((overrides or {}).keys()):
        v = (overrides or {})[k]
        try:
            parts.append(f"{k}={float(v):.10g}")
        except (TypeError, ValueError):
            parts.append(f"{k}={v!r}")
    if peers:
        parts.append("peers=" + ",".join(sorted(str(p).strip().upper() for p in peers)))
    return "|".join(parts)


class ResultCache:
    """Bounded, expiring, request-keyed store of `ValuationResult`s.

    Thread-safe because gunicorn runs four threads per worker: the LRU touch and the
    eviction are read-modify-write sequences, not single atomic dict operations.
    """

    def __init__(self, ttl_seconds: float = TTL_SECONDS, max_entries: int = MAX_ENTRIES):
        self.ttl_seconds = float(ttl_seconds)
        self.max_entries = int(max_entries)
        self._entries: "OrderedDict[str, Entry]" = OrderedDict()
        self._lock = threading.Lock()

    # -- reads ------------------------------------------------------------------
    def get(self, ticker: str, overrides: Optional[dict] = None,
            peers: Optional[list] = None, now: Optional[float] = None) -> Optional[Entry]:
        """The entry for this exact request if it is still fresh, else None.

        An expired entry is dropped rather than returned-and-ignored, so a name nobody
        asks for again does not sit in memory forever.
        """
        now = _now(now)
        key = request_key(ticker, overrides, peers)
        with self._lock:
            e = self._entries.get(key)
            if e is None:
                return None
            if e.age(now) > self.ttl_seconds:
                self._entries.pop(key, None)
                return None
            self._entries.move_to_end(key)
            return e

    # -- writes -----------------------------------------------------------------
    def put(self, ticker: str, result: Any, overrides: Optional[dict] = None,
            peers: Optional[list] = None, now: Optional[float] = None) -> Entry:
        now = _now(now)
        key = request_key(ticker, overrides, peers)
        e = Entry(result, now, key)
        with self._lock:
            self._entries[key] = e
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
        return e

    # -- housekeeping -----------------------------------------------------------
    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._entries


def _now(now: Optional[float]) -> float:
    if now is not None:
        return float(now)
    import time
    return time.time()
