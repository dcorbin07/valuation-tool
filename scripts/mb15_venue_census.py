"""MB15 pass 1 - instrument census of the tick cache's venue axis.

READ-ONLY. NO ARM, NO TRIALS, NO VERDICT ABOUT ANY RETURN.

MB15 registers a kill condition that is a statement about the INSTRUMENT - "the venue->retail
mapping must reproduce the published retail share (~60%) on the pooled cache to within +/-15pp,
or the proxy is invalid" - so it cannot be assessed without first knowing what the venue axis
contains.  This pass measures that and nothing else.

It also records a fingerprint of every unit read.  There is NO pinned freeze for the tick cache -
`D:\\thetadata` holds only the two CHAIN freezes - so the brief's "read through the pinned freeze
resolver only" cannot be followed literally here.  A recorded fingerprint is the substance of what
pinning protects: it makes a later mutation detectable, which is how the harvest freeze being
rewritten under this lane was caught.

    python -m scripts.mb15_venue_census
"""
import hashlib
import io
import json
import os
from collections import Counter

import pandas as pd


def _data_root():
    """The tick cache lives in the primary checkout; a worktree carries only a partial `data/`.

    Probed for the thing actually wanted rather than for the directory - `DEEPITM-FIN` shipped a
    resolver that took an EMPTY `bars` dir over a populated one because it tested existence.
    Existence is not population.
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for cand in (os.path.join(here, "data"),
                 os.path.abspath(os.path.join(here, "..", "..", "..", "data"))):
        if os.path.isdir(os.path.join(cand, "options_ticks")):
            return cand
    raise SystemExit("no options_ticks cache found")


DATA = _data_root()
ROOT = os.path.join(DATA, "options_ticks")
OUT = os.path.join(DATA, "free_analysis", "MB15_VENUE_CENSUS.json")


def main():
    trade_ex, bid_ex, ask_ex = Counter(), Counter(), Counter()
    keys_seen = Counter()
    prints = units = size1 = 0
    symbols, dates = set(), set()
    h = hashlib.sha256()

    syms = sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d)))
    print("[MB15] %d symbol directories" % len(syms), flush=True)

    for si, sym in enumerate(syms):
        sd = os.path.join(ROOT, sym)
        for f in sorted(os.listdir(sd)):
            if not f.endswith(".pkl"):
                continue
            p = os.path.join(sd, f)
            st = os.stat(p)
            h.update(("%s|%d|%d" % (f, st.st_size, int(st.st_mtime))).encode())
            obj = pd.read_pickle(p)
            for k in obj.keys():
                keys_seen[k] += 1
            r = obj["rows"]
            units += 1
            symbols.add(obj.get("symbol", sym))
            dates.add(str(obj.get("date"))[:10])
            prints += len(r)
            trade_ex.update(r["exchange"].value_counts().to_dict())
            bid_ex.update(r["bid_exchange"].value_counts().to_dict())
            ask_ex.update(r["ask_exchange"].value_counts().to_dict())
            size1 += int((r["size"] == 1).sum())
        if si % 20 == 0:
            print("[MB15]   %d/%d symbols, %s units, %s prints"
                  % (si, len(syms), "{:,}".format(units), "{:,}".format(prints)), flush=True)

    tot = sum(trade_ex.values())
    shares = {int(k): v / tot for k, v in sorted(trade_ex.items(), key=lambda kv: -kv[1])}

    out = {
        "item": "MB15",
        "pass": "instrument-census",
        "status": "READ-ONLY FACTS - no arm, no trials, no verdict",
        "root": ROOT,
        "fingerprint_sha256": h.hexdigest(),
        "fingerprint_basis": "(filename, size, mtime) per unit, in walk order",
        "no_pinned_freeze_exists_for_ticks": True,
        "units": units, "symbols": len(symbols), "dates": len(dates), "prints": prints,
        "size_eq_1_share": (size1 / prints) if prints else None,
        "payload_keys": dict(keys_seen),
        "pre_panel_history_key_present": "pre_panel_history" in keys_seen,
        "trade_exchange_codes": len(trade_ex),
        "trade_exchange_shares": shares,
        "bid_exchange_codes": len(bid_ex),
        "ask_exchange_codes": len(ask_ex),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)

    print()
    print("[MB15] units %s  symbols %d  dates %d  prints %s"
          % ("{:,}".format(units), len(symbols), len(dates), "{:,}".format(prints)))
    print("[MB15] distinct trade-venue codes: %d" % len(trade_ex))
    for k, v in shares.items():
        print("         code %3d  %8.4f%%" % (k, 100 * v))
    print("[MB15] wrote %s" % OUT)


if __name__ == "__main__":
    main()
