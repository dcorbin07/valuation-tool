"""
S3-I5 — adjudicate the 26 `pre_panel_history` symbols and write the table resolvers read.

    python -m scripts.s3i5_ticker_adjudication

FIXED-class. Zero trials, no verdict about returns, nothing adopted. The flagged symbols and
years come from the harvest manifest itself, so the scope is measured rather than transcribed --
a hand-copied list of 26 is exactly the kind of thing that goes stale the next time a tier runs.

Writes `TICKER_REUSE_ADJUDICATION.json` at the repo root, TRACKED. It has to be tracked: the
whole point is that `SC-3`, `B-14`, `B-15` and `B-6e` read one table instead of each deciding
for itself, and a resolver cannot read a file that lives only in a gitignored directory on one
machine. It carries listing dates and company names for 26 tickers -- identity facts, not a
licensed bulk export, and no prices, fundamentals or option rows.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import ticker_identity as TI                        # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "TICKER_REUSE_ADJUDICATION.json")


#: The files this script actually needs. Probing for the DIRECTORY is not enough: a worktree
#: carries a thin `data/bulk` with a couple of caches and none of the registry, and the first cut
#: of this resolver selected it happily. Every symbol then came back UNKNOWN -- which is the
#: right FAILURE DIRECTION and the wrong outcome, and it would have been easy to read the
#: all-UNKNOWN table as "adjudicated, nothing conclusive" rather than "pointed at an empty
#: cupboard". Probe for the file, not the folder.
_NEEDED = (("backtest_freeze_2026-08", "bulk", "tickers.csv"),)


def _data_root() -> str:
    """Announced, never silently chosen -- `data/` is absent (or thin) inside a worktree."""
    for root, why in ((os.path.join(REPO, "data"), "worktree"),
                      (r"C:\Users\donni\Downloads\valuation-tool\data", "main checkout")):
        if all(os.path.exists(os.path.join(root, *p)) for p in _NEEDED):
            print(f"[s3i5] data root: {root}  ({why})", flush=True)
            return root
    raise SystemExit(
        "[s3i5] TICKERS registry not found under either data root -- an adjudication with no "
        "registry produces an all-UNKNOWN table that LOOKS like a completed run. Refusing. "
        "Pass --tickers/--actions explicitly.")


def flagged_from_manifest(path: str) -> dict:
    """{symbol: [years]} for every unit the harvest stamped `pre_panel_history`."""
    out = collections.defaultdict(set)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("pre_panel_history"):
                out[str(r["symbol"]).upper()].add(int(r["year"]))
    return {k: sorted(v) for k, v in out.items()}


def main(argv=None):
    data = _data_root()
    ap = argparse.ArgumentParser(description="S3-I5 ticker-reuse adjudication (FIXED class)")
    ap.add_argument("--tickers", default=os.path.join(
        data, "backtest_freeze_2026-08", "bulk", "tickers.csv"))
    ap.add_argument("--actions", default=os.path.join(data, "bulk", "actions.csv"))
    ap.add_argument("--manifest", default=r"D:\thetadata\manifest.jsonl")
    ap.add_argument("--chains", default=os.path.join(data, "options"))
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)

    flagged = flagged_from_manifest(a.manifest)
    if not flagged:
        raise SystemExit(f"[s3i5] no pre_panel_history units in {a.manifest} -- nothing to "
                         f"adjudicate, and an empty run must not write an empty all-clear.")
    print(f"[s3i5] flagged: {sum(len(v) for v in flagged.values())} units, "
          f"{len(flagged)} symbols", flush=True)

    def strike_fn(sym, year):
        """`ticker_reuse_audit.py`'s discriminator, reused. Independent of the registry."""
        import pandas as pd
        p = os.path.join(a.chains, sym, f"{sym}-{year}.pkl")
        if not os.path.exists(p):
            return None
        try:
            obj = pd.read_pickle(p)
            df = obj["rows"] if isinstance(obj, dict) and "rows" in obj else obj
            s = pd.to_numeric(df["strike"], errors="coerce").dropna()
            if not len(s):
                return None
            if s.max() > 10000:
                s = s / 1000.0
            return round(float(s.median()), 2)
        except Exception:                                               # noqa: BLE001
            return None

    tbl = TI.build(flagged.keys(), a.tickers, a.actions,
                   strike_fn=strike_fn, flagged_years=flagged)
    payload = tbl.to_json(a.out)

    roll = collections.Counter()
    for s, rec in payload["symbols"].items():
        for _, v in rec.get("year_verdicts", {}).items():
            roll[v] += 1
    print(f"[s3i5] unit verdicts: {dict(roll)}", flush=True)

    print(f"\n{'sym':6s} {'firstpricedate':15s} {'years':22s} {'verdict(s)':34s} step  name")
    for s in sorted(payload["symbols"]):
        rec = payload["symbols"][s]
        vs = rec.get("year_verdicts", {})
        uniq = sorted(set(vs.values()))
        step = rec.get("strike_step")
        flag = " <-- EVIDENCE DISAGREES" if rec.get("evidence_disagreement") else ""
        print(f"{s:6s} {str(rec.get('firstpricedate')):15s} "
              f"{','.join(sorted(vs)):22s} {'/'.join(uniq):34s} "
              f"{('-' if step is None else f'{step:.2f}'):5s} "
              f"{str(rec.get('current_name'))[:34]}{flag}")
    print(f"\n[s3i5] wrote {a.out}")
    return payload


if __name__ == "__main__":
    main()
