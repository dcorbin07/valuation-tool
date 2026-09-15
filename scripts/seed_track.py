"""
Install the bound Valquo Index book and its recorded history on the live service.

    python -m scripts.seed_track                  # show what would be sent, send nothing
    python -m scripts.seed_track --send           # do it
    python -m scripts.seed_track --send --book-only   # re-install the book, leave the series

WHY THIS EXISTS, AND IT IS A MEASUREMENT. On 2026-08-18 the PT-WRITER Action reached
`POST /admin/track-row?append=1` on the live service, authenticated, and was refused:

    {"ok": false, "reason": "the book file /app/data/valquo_track.json is missing or
     unreadable", "row": null}

That is `index_mark.load_book` working exactly as written. `data/` is gitignored, so the
book has never shipped with any deploy - it exists only on this machine. The write door was
never the blocker: THE SERVICE HAS NOTHING TO MARK. This is the one command that fixes it.

AFTER THIS RUNS, THE SERVICE COPY IS THE RECORD. The two local files become a stale backup
the moment the service writes its first row, and nothing syncs them back. That is a
deliberate choice of ONE recorder over two - this project has already published two
different "Valquo Index vs SPY" numbers from two books, and the cure for that is a single
authority rather than better reconciliation. If you want the service's copy afterwards, the
weekly `track-backup` Action is what archives it.

IT IS SAFE TO RE-RUN. The service refuses any upload that rewrites or truncates the recorded
series (it may only EXTEND it), and re-sending exactly what is already installed writes
nothing and answers 200. Every rule is enforced service-side in `index_mark.seed`, not here
- this script is a file reader and an HTTP client, deliberately, so there is nothing in it
that can disagree with the door.

CONFIGURATION comes from `.env` (or the environment):

    SITE_BASE_URL   the service, e.g. https://valquo.co   (PUBLIC_BASE_URL is accepted too,
                    because that is the name already in this project's .env; SITE_BASE_URL is
                    the name the GitHub Actions secret uses)
    ADMIN_TOKEN     the same admin token every other admin route takes

EXIT CODES, because this is meant to be checkable:

    0  installed (201), or the service already held exactly this (200)
    2  REFUSED by the service - the reason is printed verbatim; nothing was changed
    3  a configuration or transport problem - nothing was sent, or the send failed

The token is never printed, on any path, including the failure paths.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

from valuation.screener import index_track



from valuation.screener.index_mark import ROW_COLUMNS  # noqa: E402

def reconcile(local_text: str, service_rows: list) -> dict:
    """Is the LOCAL series a superset of the SERVICE's — same rows, same order, cell for cell?

    THE ONLY SAFE PRECONDITION FOR AN UPLOAD, and the reason it is computed here rather than
    trusted to the door: the service enforces a BYTE PREFIX, which is the right rule and a
    terrible diagnostic. A 409 tells you the upload was refused; it does not tell you WHICH row
    disagreed, and "the local file is shorter" and "row 4 has a different excess_pp" are very
    different problems with very different fixes.

    **A SILENT MERGE OF TWO DIVERGENT RECORDS IS HOW A TRACK RECORD BECOMES FICTION**, so a
    disagreement on any shared row is a REFUSAL that names the row, never a reconciliation.

    Returns `{ok, reason, shared, local_extra, service_extra, disagreements}`.
    """
    from scripts.fetch_track import rows_of

    local = rows_of(local_text)
    svc = list(service_rows or [])
    cols = list(ROW_COLUMNS)

    def norm(r):
        # Compared as STRINGS on the bound schema's own columns: the service returns JSON
        # (day_n an int, excess_pp a float) while the local file is text, so a raw == would
        # report every row as different for a reason that is purely transport.
        return tuple("" if r.get(c) is None else str(r.get(c)).strip() for c in cols)

    n = min(len(local), len(svc))
    bad = []
    for i in range(n):
        a, b = norm(local[i]), norm(svc[i])
        if a != b:
            bad.append({"index": i, "local": dict(zip(cols, a)), "service": dict(zip(cols, b)),
                        "columns": [c for c, x, y in zip(cols, a, b) if x != y]})

    out = {"shared": n, "local_extra": max(0, len(local) - n),
           "service_extra": max(0, len(svc) - n), "disagreements": bad, "ok": False,
           "reason": ""}
    if bad:
        out["reason"] = ("%d shared row(s) disagree; refusing rather than merging two "
                         "divergent records" % len(bad))
    elif out["service_extra"]:
        out["reason"] = ("the service holds %d row(s) the local file does not, so the local "
                         "series is NOT a superset and an upload would truncate the record"
                         % out["service_extra"])
    else:
        out["ok"] = True
        out["reason"] = ("the local series matches the service on all %d shared row(s) and "
                         "adds %d" % (n, out["local_extra"]))
    return out


def _base_url() -> str:
    for k in ("SITE_BASE_URL", "PUBLIC_BASE_URL"):
        v = (os.environ.get(k) or "").strip()
        if v:
            return v.rstrip("/")
    return ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--pull", action="store_true",
                    help="pull the service's recorded series first and refuse to upload "
                         "unless the local one is a superset of it, cell for cell")
    ap.add_argument("--send", action="store_true",
                    help="actually POST. Without it this is a dry run that sends nothing.")
    ap.add_argument("--book-only", action="store_true",
                    help="send the book and leave the recorded series alone. The service "
                         "refuses this unless it already holds rows.")
    ap.add_argument("--book", default=None, help="path to valquo_track.json")
    ap.add_argument("--history", default=None, help="path to valquo_track_history.csv")
    ap.add_argument("--url", default=None, help="override SITE_BASE_URL")
    a = ap.parse_args(argv)

    # `valuation.config` loads .env on import; importing it is what makes `.env` visible here.
    try:
        from valuation.config import CONFIG                      # noqa: F401
    except Exception:                                            # noqa: BLE001
        pass

    mp, hp = index_track.default_paths()
    book_path = a.book or mp
    hist_path = a.history or hp

    try:
        with open(book_path, encoding="utf-8") as f:
            book = json.load(f)
    except Exception as e:                                       # noqa: BLE001
        print("cannot read the book at " + str(book_path) + ": " + str(e), file=sys.stderr)
        return 3

    history = None
    if not a.book_only:
        try:
            # utf-8-sig strips a BOM if Excel has been near the file; `newline=""` keeps the
            # line terminators exactly as recorded, because the service's prefix rule is
            # defined on bytes and normalising them here would be a silent rewrite.
            with open(hist_path, encoding="utf-8-sig", newline="") as f:
                history = f.read()
        except Exception as e:                                   # noqa: BLE001
            print("cannot read the history at " + str(hist_path) + ": " + str(e),
                  file=sys.stderr)
            return 3

    n_pos = len(book.get("positions") or [])
    n_rows = 0 if history is None else max(0, len(history.strip().splitlines()) - 1)
    print("book     " + str(book_path))
    print("         " + str(n_pos) + " positions, inception "
          + str(book.get("inception_date")) + ", benchmark " + str(book.get("benchmark")))
    print("history  " + ("(not sent - --book-only)" if history is None else str(hist_path)))
    if history is not None:
        print("         " + str(n_rows) + " recorded rows, " + str(len(history)) + " bytes")

    base = (a.url or _base_url()).rstrip("/")
    token = (os.environ.get("ADMIN_TOKEN") or "").strip()
    if not base:
        print("no SITE_BASE_URL (or PUBLIC_BASE_URL) - nothing to send to", file=sys.stderr)
        return 3
    if not token:
        print("no ADMIN_TOKEN in the environment or .env", file=sys.stderr)
        return 3
    print("target   " + base + "/admin/track-seed")

    # RECONCILE BEFORE SENDING. Runs on a dry run too, because the whole value of the check
    # is being able to see the answer WITHOUT committing to an upload.
    if a.pull:
        from scripts.fetch_track import fetch
        try:
            got = fetch(base, token)
        except Exception as e:                                   # noqa: BLE001
            print("could not pull the service's series: " + str(e), file=sys.stderr)
            return 2
        svc = got["series"]
        print("pulled   " + str(len(svc)) + " recorded row(s) from the service")
        if history is None:
            print("         (--book-only: the series is not being sent, so nothing to check)")
        else:
            rec = reconcile(history, svc)
            print("         local " + str(n_rows) + " row(s), service " + str(len(svc))
                  + " - " + rec["reason"])
            for d in rec["disagreements"][:10]:
                print("         ROW " + str(d["index"]) + " differs on "
                      + ", ".join(d["columns"]))
                print("            local  : " + json.dumps(d["local"], sort_keys=True))
                print("            service: " + json.dumps(d["service"], sort_keys=True))
            if not rec["ok"]:
                print("\nREFUSING to upload. " + rec["reason"], file=sys.stderr)
                print("The service's copy is the record; pull it with "
                      "`python -m scripts.fetch_track` and reconcile by hand before sending. "
                      "Nothing here will merge two divergent records for you.", file=sys.stderr)
                return 4

    if not a.send:
        print("\nDRY RUN - nothing was sent. Re-run with --send to install it.")
        print("After it installs, the service's own copy is the record and these two local "
              "files become a stale backup.")
        return 0

    payload = {"book": book}
    if history is not None:
        payload["history"] = history
    req = urllib.request.Request(
        base + "/admin/track-seed",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Admin-Token": token},
        method="POST")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            code, raw = resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        code, raw = e.code, e.read().decode("utf-8", "replace")
    except Exception as e:                                       # noqa: BLE001
        # Deliberately does NOT print the request: it carries the token in a header.
        print("could not reach " + base + ": " + type(e).__name__ + ": " + str(e),
              file=sys.stderr)
        return 3

    try:
        body = json.loads(raw)
    except Exception:                                            # noqa: BLE001
        body = {"raw": raw[:2000]}
    print("\nHTTP " + str(code))
    print(json.dumps(body, indent=2, default=str)[:4000])

    if code in (200, 201):
        if code == 201:
            print("\nInstalled. THE SERVICE COPY IS NOW THE RECORD - these local files are a "
                  "backup from here on, and the weekly track-backup Action archives the "
                  "service's copy.")
        else:
            print("\nThe service already held exactly this. Nothing was written.")
        print("Next: the PT-WRITER Action's POST /admin/track-row?append=1 should now write "
              "rather than refuse. Trigger it from the Actions tab to confirm without "
              "waiting for the schedule.")
        return 0

    print("\nREFUSED - nothing on the service was changed.", file=sys.stderr)
    if code == 409:
        print("The upload disagrees with the series already recorded there. This door may "
              "EXTEND the record and may never rewrite it; the local copy is probably behind "
              "the service. Fetch the service's copy before re-running.", file=sys.stderr)
    elif code == 422:
        print("The book is not the contract-bound Index, or there is no history to stand on. "
              "The reason above says which.", file=sys.stderr)
    elif code == 401:
        print("ADMIN_TOKEN was not accepted.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
