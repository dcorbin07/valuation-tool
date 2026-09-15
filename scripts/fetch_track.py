"""Pull the SERVICE's recorded forward track and write it locally, to a NEW file.

WHY THIS EXISTS. `seed_track --send` was refused with 409 — *"an upload may extend the
recorded series, never truncate it"* — because the SERVICE holds 17 recorded rows and the
LOCAL copy holds 6. **That refusal was correct and protected 11 real rows**, and nothing here
weakens it: there is no `--force`, the check is not lowered, and an upload still may not
shrink the series. What was missing was the other direction — a way to *read* the service's
record before deciding what, if anything, to send.

**IT NEVER OVERWRITES `data/valquo_track_history.csv`.** The pull writes a dated,
separately-named file. The local file is a backup of a record whose authority now lives on the
service; silently replacing it in place would destroy the only evidence of a disagreement at
exactly the moment a disagreement matters.

**READ-ONLY, THROUGH THE EXISTING DOOR.** `GET /admin/export-track` already exists for the
weekly backup and computes nothing. No new admin surface is added.

    python -m scripts.fetch_track                 # write data/valquo_track_service_<date>.csv
    python -m scripts.fetch_track --print         # print the rows, write nothing

CONFIGURATION, identical to `seed_track` so there is one spelling: `SITE_BASE_URL` (or
`PUBLIC_BASE_URL`) and `ADMIN_TOKEN`, from the environment or `.env`. **The token is read and
never printed.**
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import io
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

#: The bound series' header, IMPORTED rather than retyped — `index_mark.ROW_COLUMNS` is the
#: single spelling of it, and a second copy here is how a puller and a writer come to disagree
#: about what a row is.
from valuation.screener.index_mark import ROW_COLUMNS                    # noqa: E402


def _base_url() -> str:
    for k in ("SITE_BASE_URL", "PUBLIC_BASE_URL"):
        v = (os.environ.get(k) or "").strip()
        if v:
            return v.rstrip("/")
    return ""


def fetch(base: str, token: str, timeout: int = 120) -> dict:
    """The service's bound track, as `{"meta": {...}, "series": [ {...}, ... ]}`.

    Raises on anything that is not a clean, well-formed answer: a puller that returned an
    empty series on an error would look exactly like a service with no record, and the caller's
    next step is a decision about whether to upload.
    """
    req = urllib.request.Request(base.rstrip("/") + "/admin/export-track",
                                 headers={"X-Admin-Token": token}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", "replace")
    body = json.loads(raw)
    if not body.get("ok"):
        raise RuntimeError("the export door refused: %s" % (body.get("error") or raw[:200]))
    bound = ((body.get("export") or {}).get("bound_index_track") or {})
    if bound.get("error"):
        raise RuntimeError("the service could not build its bound series: %s" % bound["error"])
    series = bound.get("series")
    if series is None:
        raise RuntimeError("the export carries no bound series at all")
    return {"meta": bound.get("meta") or {}, "series": list(series)}


def to_csv(series) -> str:
    """The service's rows in the bound file's own schema, byte-comparable with the local one.

    `\\r\\n` and `utf-8` because that is what `index_mark` writes and what the service's prefix
    rule is defined on. Rendering it any other way would produce a file that LOOKS like the
    record and fails a byte comparison for a reason that has nothing to do with the data.
    """
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(ROW_COLUMNS), lineterminator="\r\n",
                       extrasaction="ignore")
    w.writeheader()
    for row in series:
        w.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in ROW_COLUMNS})
    return buf.getvalue()


def rows_of(text: str) -> list:
    """Parse a bound CSV into a list of dicts, for cell-for-cell comparison."""
    return list(csv.DictReader(io.StringIO(text, newline=""), restkey="__extra__",
                              restval="__missing__"))


def out_path(today: _dt.date = None) -> str:
    d = (today or _dt.date.today()).isoformat()
    return os.path.join(ROOT, "data", "valquo_track_service_%s.csv" % d)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Pull the service's recorded forward track.")
    ap.add_argument("--url", default="")
    ap.add_argument("--print", dest="show", action="store_true",
                    help="print the rows and write nothing")
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)

    base = (a.url or _base_url()).rstrip("/")
    token = (os.environ.get("ADMIN_TOKEN") or "").strip()
    if not base:
        print("no SITE_BASE_URL (or PUBLIC_BASE_URL) - nothing to pull from", file=sys.stderr)
        return 3
    if not token:
        print("no ADMIN_TOKEN in the environment or .env", file=sys.stderr)
        return 3

    try:
        got = fetch(base, token)
    except urllib.error.HTTPError as e:
        print("the service answered %s pulling the track" % e.code, file=sys.stderr)
        return 2
    except Exception as e:                                               # noqa: BLE001
        print("could not pull the track: %s" % e, file=sys.stderr)
        return 2

    series = got["series"]
    print("service  %s/admin/export-track" % base)
    print("         %d recorded row(s)" % len(series))
    if series:
        print("         first %s   last %s" % (series[0].get("date"), series[-1].get("date")))

    text = to_csv(series)
    if a.show:
        print()
        print(text, end="")
        return 0

    p = a.out or out_path()
    # A NEW FILE, EVERY TIME. Never `valquo_track_history.csv`: that local copy is the only
    # evidence of a disagreement, and overwriting it in place would erase the disagreement
    # rather than resolve it.
    base_name = os.path.basename(p).lower()
    if base_name == "valquo_track_history.csv":
        print("REFUSING to write over the local bound history; pull to a new file",
              file=sys.stderr)
        return 3
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print("wrote    %s" % p)
    print("         the LOCAL data/valquo_track_history.csv is untouched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
