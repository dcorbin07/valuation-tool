"""
Compute the days the automated writer missed, ON THE SERVICE, and store them beside the record.

    python -m scripts.reconstruct_track            # compute and report, store nothing
    python -m scripts.reconstruct_track --write    # store them

WHY IT RUNS ON THE SERVICE RATHER THAN HERE, AND IT IS A MEASUREMENT. The reconstruction needs
three things in one place: the book in force, the recorded series to subtract, and a price
vendor. The service has all three. This machine has the book and a STALE copy of the record --
`data/valquo_track_history.csv` holds 8 rows against the service's 24, it disagrees with the
service on 3 of those 8 (08-21, 08-27, and 09-24 on BOTH legs), and it carries a row,
2026-09-17, that is NOT IN THE RECORD AT ALL. Subtracting the local copy would draw
"reconstructed" points on dates that ARE recorded, which is exactly the confusion the separate
store exists to prevent.

So `/api/index-track` served `n_reconstructed: 0` not because the computation failed -- it ran
here and produced 19 points -- but because it ran somewhere the record is not, and `data/` is
not deployed.

NOTHING IS WRITTEN TO THE BOUND SERIES. The door writes one file, the reconstruction store,
through `track_reconstruct.save`. That module's own suite pins that it names no bound file in
CODE and that the bound file and every gate/meter input are byte-identical with the feature
present and absent. The points are excluded from the recorded-day count, the evidence meter,
the operational gate and every verdict, and `excluded_from` travels with the payload.

READ THE VALIDATION BEFORE TRUSTING THE POINTS. The response carries
`validate_against_record`, which reconstructs days the record ALREADY holds and reports the
disagreement leg by leg. Measured locally against the service's 24 rows: the benchmark leg is
EXACT on 22 of 24 and the book leg on 11 of 24 at a median 0.0005pp, with every non-zero delta
sitting on a day whose name count differs -- one name (WBS) that no vendor can price today, so
it is absent from the reconstruction of every day including the ones it was live.

IT IS SAFE TO RE-RUN. A run that priced nothing is REFUSED rather than allowed to overwrite a
populated store, so one throttled attempt cannot replace 19 good points with an empty file.
Every rule is enforced service-side in the door, not here -- this script is an HTTP client,
deliberately, so there is nothing in it that can disagree with the door.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = os.environ.get("BASE_URL") or "https://valquo.co"


def call(base: str, token: str, write: bool) -> tuple:
    """`(status, payload)` from the door. GET to compute, POST to store."""
    url = base.rstrip("/") + "/admin/track-reconstruct" + ("?write=1" if write else "")
    req = urllib.request.Request(url, method="POST" if write else "GET")
    req.add_header("X-Admin-Token", token)
    if write:
        # A body is not required, but a POST with no content-length upsets some proxies.
        req.data = b"{}"
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(body or "{}")
        except ValueError:
            return e.code, {"error": body[:400]}


def report(p: dict) -> None:
    print("record        %s rows, %s" % (p.get("record_rows"), p.get("record_span")))
    print("missing       %s sessions" % p.get("n_missing"))
    print("computed      %s" % p.get("n_computed"))
    for r in (p.get("refused") or [])[:8]:
        print("   refused %s  %s" % (r.get("date"), str(r.get("reason"))[:90]))
    v = p.get("validation") or {}
    if v.get("n_compared"):
        print("validation    compared %s days, refused %s" % (v["n_compared"], v["n_refused"]))
        print("              benchmark exact on %s of %s, max |delta| %s pp"
              % (v.get("bench_exact_days"), v["n_compared"], v.get("bench_max_abs")))
        print("              book max |delta| %s pp, median %s pp"
              % (v.get("book_max_abs"), v.get("book_median_abs")))
    else:
        print("validation    NOT RUN -- nothing was compared, so it proves nothing")
    print("excluded from %s" % (p.get("excluded_from") or []))
    print("written       %s" % p.get("written"))
    if p.get("store"):
        print("store         %s (%s points, computed_at %s)"
              % (p["store"].get("path"), p["store"].get("n"), p["store"].get("computed_at")))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--write", action="store_true",
                    help="store the points (without it the door computes and returns only)")
    a = ap.parse_args(argv)

    token = os.environ.get("ADMIN_TOKEN") or ""
    if not token:
        # NEVER printed, and never accepted on the command line: an argument lands in the shell
        # history and in the process list, where a token does not belong.
        print("REFUSED: set ADMIN_TOKEN in the environment (it is never taken as an argument "
              "and never printed)", file=sys.stderr)
        return 2

    status, payload = call(a.base, token, a.write)
    if status == 401:
        print("REFUSED: the service rejected the token", file=sys.stderr)
        return 3
    if status == 405:
        print("REFUSED: %s" % payload.get("error"), file=sys.stderr)
        return 4
    if not payload.get("ok"):
        print("REFUSED (%s): %s" % (status, payload.get("reason") or payload.get("error")),
              file=sys.stderr)
        report(payload)
        return 5
    report(payload)
    if not a.write:
        print()
        print("nothing stored. Re-run with --write to store these points.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
