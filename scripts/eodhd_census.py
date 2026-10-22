# -*- coding: utf-8 -*-
"""`EODHD-CENSUS` — what the EODHD Fundamentals feed actually carries. ZERO TRIALS.

    python -m scripts.eodhd_census --probe        # step A: endpoint shapes, ~30 calls
    python -m scripts.eodhd_census --coverage     # step B: universe + tier coverage
    python -m scripts.eodhd_census --pit          # step C: point-in-time vs restated

**NO FORWARD RETURN IS LOADED AND NO OUTCOME IS COMPUTED** — pinned by test. This is a coverage and
entitlement census in the style of `WRDS_CENSUS.md`: every line is a real request, and a product
being named on the pricing page is not evidence it answers.

--------------------------------------------------------------------------------------------
THE LICENCE FENCE, WHICH IS THE FIRST THING THIS FILE OBEYS.

`DECISIONS.md` 2026-10-22: the EODHD **personal** plan permits storing and analysing the data for
private, non-commercial use and **forbids displaying, redistributing or granting access to it "in
its original or repackaged form."** The repo is PUBLIC and MIT. Therefore:

  * **raw rows are written under `D:\\eodhd` and nowhere else** — never into the repo, never into
    `data_export/`, never onto a page;
  * **the committed artifact carries DERIVED STATISTICS ONLY** — availability, counts, coverage
    rates, date spans, field NAMES (schema, not data) and disagreement rates. **No per-name
    financial value is ever written to a tracked file**, which a test asserts;
  * the key is read from the environment and **never printed, logged or committed** — not at debug,
    not in an exception message. The helper below returns a URL-safe request object and never the
    token, and every error message is scrubbed.

--------------------------------------------------------------------------------------------
THE BUDGET IS REAL AND IS READ RATHER THAN ASSUMED.

100,000 calls a day, 1,000 a minute, and **one fundamentals request costs 10 calls**, so about
10,000 names a day. `/api/user` reports the plan and the day's consumption, so the census asks the
API what it has spent rather than counting locally and hoping.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

RAW_ROOT = r"D:\eodhd"
BASE = "https://eodhd.com/api"
UA = "Valquo private research (donniecorbin6@gmail.com)"

#: Fundamentals cost 10; most others cost 1. Declared so the budget arithmetic is visible.
COST = {"fundamentals": 10}


class KeyMissing(RuntimeError):
    """Raised when `.env` has no EODHD key. Names the KEY and never a value."""


def _repo_root() -> str:
    """The checkout that owns this worktree — a worktree has no `.env`, its owner does."""
    d = _HERE
    for _ in range(6):
        if os.path.isfile(os.path.join(d, ".env")):
            return d
        nxt = os.path.dirname(d)
        if nxt == d:
            break
        d = nxt
    return _HERE


def api_key() -> str:
    """The key, from the environment or the owning checkout's `.env`. NEVER returned to a printer.

    `wrds_client`'s law, applied to a second vendor: nothing here returns a secret to a caller
    that might serialise it, and the one consumer is `_get` below.
    """
    k = os.environ.get("EODHD_API_KEY", "").strip()
    if k:
        return k
    p = os.path.join(_repo_root(), ".env")
    if os.path.isfile(p):
        for ln in io.open(p, encoding="utf-8", errors="replace"):
            if ln.strip().startswith("#") or "=" not in ln:
                continue
            name, val = ln.split("=", 1)
            if name.strip() == "EODHD_API_KEY":
                v = val.strip().strip('"').strip("'")
                if v:
                    return v
    raise KeyMissing("EODHD_API_KEY is absent from the environment and from the owning "
                     "checkout's .env. Stopping; no value is printed.")


def _scrub(s: str, key: str) -> str:
    """Remove the token from any string that might be printed or stored."""
    out = s.replace(key, "<REDACTED>")
    return re.sub(r"api_token=[^&\s\"']+", "api_token=<REDACTED>", out)


def _get(path: str, params: dict = None, timeout: int = 90):
    """One request. Returns (status, parsed-or-text). The token never appears in any output."""
    key = api_key()
    q = dict(params or {})
    q.setdefault("api_token", key)
    q.setdefault("fmt", "json")
    url = "%s/%s?%s" % (BASE, path.lstrip("/"), urllib.parse.urlencode(q))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
            try:
                return r.status, json.loads(body)
            except ValueError:
                return r.status, body[:400]
    except urllib.error.HTTPError as e:
        return e.code, _scrub(str(e.reason), key)
    except Exception as e:                                               # noqa: BLE001
        return -1, _scrub("%s: %s" % (type(e).__name__, e), key)


def _shape(v, depth: int = 0):
    """A structural description — keys and types, never values."""
    if isinstance(v, dict):
        if depth >= 2:
            return {"_type": "dict", "_keys": len(v)}
        return {k: _shape(val, depth + 1) for k, val in list(v.items())[:40]}
    if isinstance(v, list):
        return {"_type": "list", "_len": len(v),
                "_first": _shape(v[0], depth + 1) if v else None}
    return type(v).__name__


def save_raw(name: str, obj) -> str:
    """Raw payload goes to D:\\eodhd and ONLY there."""
    os.makedirs(RAW_ROOT, exist_ok=True)
    p = os.path.join(RAW_ROOT, name)
    with io.open(p, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, default=str)
    return p
