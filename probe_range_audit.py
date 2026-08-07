"""Measure what `no_data_in_range` names ACTUALLY have, instead of inferring it (audit O15/B4 follow-up).

WHY THIS EXISTS. The breadth miner's probe is bounded: it tries 2024, then one more year, and
if both are empty it records `no_data_in_range`. That label is a claim about the WHOLE 2016-2025
mining range, but the measurement behind it covers only two years - and at least one name breaks
the difference. `UI` (Ubiquiti) is empty in 2024 and 2025, so it carries the label, yet `UBNT`
returns 620 rows for a ten-day span in 2018. The name has history; the probe simply never looked
that far back.

Shipping a status that claims more than it measured is the exact defect this session already
fixed once (`skipped_thin` was being written both for "measured and untradeable" and for "no data
to measure"). So the fix is to MEASURE the range rather than to widen the probe - widening it
would cost ten pulls for every genuinely dead ticker, and there are only a handful of these.

WHAT IT DOES. For every `no_data_in_range` name, probes a short span in each year of the mining
range under the name AND its aliases, and records `years_with_data` in the manifest. Names that
turn out to have real history are promoted back to unjudged so the next miner run picks them up;
names with nothing anywhere keep the label, which is then true.

READ-ONLY on the option cache: it issues EOD probes and writes nothing under `data/options/<SYM>/`.
The only thing it edits is the manifest.

    python probe_range_audit.py --dry-run     # measure and print, change nothing
    python probe_range_audit.py               # measure, then correct the manifest
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from valuation.edge.theta_bulk import ALIASES, CACHE_ROOT, ThetaBulk  # noqa: E402

MANIFEST = os.path.join(CACHE_ROOT, "cache_manifest.json")
# Evidence lives beside the manifest but NOT inside it - see the note in main().
AUDIT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PROBE_RANGE_AUDIT.json")
YEARS = list(range(2016, 2026))
PROBE_DAYS = 10
# ANY year of real data is enough to withdraw the verdict. The threshold used to be 3, on the
# reasoning that one stray year is not a usable history -- but that is the LIQUIDITY SCREEN's
# call to make, on measured data, not this tool's to pre-empt with a round number. The audit's
# job is only to establish that there is something to judge.
#
# This is only safe because `mine_options_cache.PROBE_YEARS_TRIED` now covers the whole range.
# While the probe was bounded at two years, promoting a name whose history is entirely
# historical (ECHO's ends in 2021, UI's in 2023) made the miner re-probe 2024/2025, find them
# empty, and re-apply the identical verdict -- an infinite churn across runs.
MIN_YEARS_TO_PROMOTE = 1


def log(m):
    print(f"[range-audit] {m}", flush=True)


def probe(tb, cli, sym, year):
    """Rows in a short mid-year span, or None if the CALL failed (unknown, not absent)."""
    start = dt.date(year, 6, 1)
    df = tb._call_with_timeout(cli.option_history_eod, start_date=start,
                               end_date=start + dt.timedelta(days=PROBE_DAYS),
                               symbol=sym, expiration="*", max_dte=90)
    if isinstance(df, str):
        return None
    return 0 if df is None else len(df)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(MANIFEST, encoding="utf-8") as f:
        man = json.load(f)
    targets = sorted(k for k, v in man.items()
                     if isinstance(v, dict) and v.get("status") == "no_data_in_range")
    if not targets:
        log("no names carry the label; nothing to audit")
        return
    log(f"{len(targets)} names labelled no_data_in_range: {', '.join(targets)}")

    tb = ThetaBulk()
    if not tb._key:
        log("NO THETADATA KEY - refusing to run (would record absence as a measurement)")
        return
    cli = tb._cli()

    promote, confirmed = [], []
    for sym in targets:
        found, faults = {}, 0
        for y in YEARS:
            best, used = 0, None
            for cand in [sym] + list(ALIASES.get(sym, [])):
                n = probe(tb, cli, cand, y)
                if n is None:
                    faults += 1
                    continue
                if n > best:
                    best, used = n, cand
            if best:
                found[y] = {"rows_in_probe": best, "symbol": used}
        man[sym]["years_with_data"] = {str(k): v for k, v in sorted(found.items())}
        man[sym]["range_audited"] = dt.date.today().isoformat()
        man[sym]["range_audit_call_faults"] = faults
        if len(found) >= MIN_YEARS_TO_PROMOTE:
            promote.append((sym, sorted(found)))
        else:
            confirmed.append((sym, sorted(found)))
        log(f"  {sym:6s} data in {len(found)}/{len(YEARS)} years "
            f"{sorted(found) if found else ''}"
            + (f" via {sorted({v['symbol'] for v in found.values()})}" if found else "")
            + (f"  [{faults} call faults]" if faults else ""))

    log(f"PROMOTE {len(promote)}: {[s for s, _ in promote]}")
    log(f"CONFIRMED empty {len(confirmed)}: {[s for s, _ in confirmed]}")

    if args.dry_run:
        log("dry run - manifest not written")
        return

    # A name with real history goes back to UNJUDGED so the next miner run mines it properly.
    # Leaving it labelled while recording contrary evidence would be the worst of both.
    #
    # The withdrawn verdicts go to a SEPARATE file, not into the manifest under a `_audit_`
    # key: every consumer treats the manifest as one-entry-per-NAME and derives counts from
    # `len(man)` (`mine_status.py`'s queue figure, `dte_extend.ranked_names`), so a
    # non-name key there would quietly corrupt them.
    withdrawn = {}
    if os.path.exists(AUDIT_JSON):
        try:
            with open(AUDIT_JSON, encoding="utf-8") as f:
                withdrawn = json.load(f).get("withdrawn", {})
        except (OSError, ValueError):
            withdrawn = {}
    for sym, yrs in promote:
        rec = man.pop(sym)
        log(f"  {sym}: removing the no_data_in_range verdict; it has {len(yrs)} years "
            f"({yrs[0]}-{yrs[-1]}). Next miner run will mine it.")
        withdrawn[sym] = {"was": "no_data_in_range",
                          "years_with_data": rec.get("years_with_data"),
                          "withdrawn_on": dt.date.today().isoformat()}
    with open(AUDIT_JSON, "w", encoding="utf-8") as f:
        json.dump({"generated": dt.date.today().isoformat(),
                   "confirmed_empty": {s: man[s].get("years_with_data") for s, _ in confirmed},
                   "withdrawn": withdrawn}, f, indent=1, sort_keys=True)
    tmp = MANIFEST + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(man, f, indent=1, sort_keys=True)
    os.replace(tmp, MANIFEST)
    log(f"manifest updated: {len(promote)} verdicts withdrawn, "
        f"{len(confirmed)} confirmed with the evidence recorded")


if __name__ == "__main__":
    main()
