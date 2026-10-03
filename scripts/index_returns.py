# -*- coding: utf-8 -*-
"""Refresh each Valquo Index holding's return since formation.

ONE COMMAND:

    python -m scripts.index_returns --send          # compute on the service AND store
    python -m scripts.index_returns --send --dry    # compute on the service, store nothing

WHY IT HAS TO RUN ON THE SERVICE. `index_in_force.compute_returns` needs the book in force and
a price vendor, and `/api/valquo-index` serves the cache it writes. A developer machine has the
book but writes the cache where nothing reads it -- the same reason `/admin/track-reconstruct`
exists. `--local` is offered for inspection only and says so.

WHY THIS IS NOT A WORKFLOW. The land policy refuses any branch touching `.github/`, so the lane
that built this cannot add the cron line. `PT-WRITER` ended the same way: the door and the
command ship, and the schedule is Don's. Call it once a trading day, after the close.

THE TOKEN IS READ FROM THE ENVIRONMENT AND NEVER PRINTED. `ADMIN_TOKEN`, or `--token`.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

DEFAULT_BASE = os.environ.get("VALQUO_BASE", "https://valquo.co")


def _send(base: str, token: str, write: bool) -> int:
    import urllib.error
    import urllib.request
    url = base.rstrip("/") + "/admin/index-returns" + ("?write=1" if write else "")
    req = urllib.request.Request(url, data=b"", method="POST")
    req.add_header("X-Admin-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            body = json.loads(r.read().decode("utf-8"))
            code = r.status
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:                                    # noqa: BLE001
            body = {"error": "unreadable error body"}
        code = e.code
    except Exception as e:                                   # noqa: BLE001
        print("REQUEST FAILED: %s" % type(e).__name__)
        return 2

    if code != 200 or not body.get("ok"):
        # The reason travels, because a refusal that cannot be read is a refusal nobody fixes.
        print("REFUSED (%s): %s" % (code, body.get("reason") or body.get("error")))
        return 1

    c = body.get("computed") or {}
    print("formed %s, marked %s" % (c.get("formed_on"), c.get("as_of")))
    print("priced %s of %s holdings" % (c.get("n_priced"), c.get("n_positions")))
    if c.get("unpriced"):
        # Named, never silently averaged over: an unpriced holding is not a flat one.
        print("UNPRICED (stored as null, not zero): %s" % ", ".join(c["unpriced"][:12]))
    print("stored: %s" % ("yes" if body.get("stored") else "NO (dry run)"))
    return 0


def _local() -> int:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from valuation.screener import index_in_force as IF
    book = IF.book_in_force()
    if not book.get("ok"):
        print("no book in force: %s" % book.get("reason"))
        return 1
    res = IF.compute_returns(book)
    if not res.get("ok"):
        print("could not compute: %s" % res.get("reason"))
        return 1
    print("INSPECTION ONLY -- nothing stored, and a local cache is not what the API reads.")
    print("priced %s of %s" % (res.get("n_priced"), res.get("n_positions")))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--send", action="store_true", help="run it on the service")
    ap.add_argument("--dry", action="store_true", help="with --send: compute, store nothing")
    ap.add_argument("--local", action="store_true",
                    help="compute here for inspection; stores nothing")
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--token", default=os.environ.get("ADMIN_TOKEN", ""))
    a = ap.parse_args()

    if a.local:
        return _local()
    if not a.send:
        ap.print_help()
        return 2
    if not a.token:
        print("no admin token: set ADMIN_TOKEN or pass --token (it is never printed)")
        return 2
    return _send(a.base, a.token, write=not a.dry)


if __name__ == "__main__":
    raise SystemExit(main())
