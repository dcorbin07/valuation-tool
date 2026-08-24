"""EXPORT THE FLEET'S GATE FLAGS — derived booleans only, so the runner can read them.

    python -m scripts.fleet_export_gates            # write data_export/fleet_gates.json
    python -m scripts.fleet_export_gates --check    # recompute and diff, write nothing

THE PROBLEM THIS SOLVES, and it is a deployment fact rather than a coding one. Six declared
fleet books gate on flags computed from the licensed Sharadar exports. **`.dockerignore`
excludes `data/` WHOLESALE** -- its own comment says *"The WHOLE data directory, not just the
databases"* -- and the fleet cycle runs on the Render service, because only that process holds
the sandbox token, the network and the records store at once (`PT-WRITER`'s architecture). So
a rule reading `data/` passes here and **fails there**, which is the worst place to find out.

THE ROUTE TAKEN, and why it is this one. `data_export/` is TRACKED and is NOT excluded from
the image -- it is how the paper track already publishes. So the gates travel as a **derived
artifact** on that precedent, and the rules read the artifact rather than the export.

**WHAT LEAVES THE LICENSED STORE: A TICKER SYMBOL AND A BOOLEAN. NOTHING ELSE.**

That is a structural guarantee rather than a promise, and `tests/test_fleet_gates.py` holds it:
every value in every gate map must be a `bool`. **A boolean cannot carry a vendor row.** No
price, no financial-statement line, no Beneish M, no Altman Z, no external-financing ratio, no
tail mass, no date per name -- the inputs are read, reduced to one bit per name, and dropped.
The reduction is many-rows-to-one-bit and is not reversible.

**THE LICENSING JUDGEMENT IS ROUTED TO DON, NOT MADE HERE.** This lane's position is that a
per-name boolean derived from thousands of rows is not the vendor's dataset, and the artifact
carries that reasoning in its own `license_note`. It is a decision with legal texture and the
safe direction is available and taken: booleans only, and the exporter refuses to widen.

WHAT THIS DOES NOT FIX, named so the artifact is not mistaken for a general answer:

  * **STALENESS TRAVELS WITH EACH GATE and is stamped per gate, never at the top.** The MA28
    flags are a QUARTERLY compute (latest 2026-01-28) and E-4's tail panel ends 2025-10-27.
    Both are declared `as_of` and a consumer that ignores them is reading a stale bit as fresh.
    F-4 and F-10 say *"at the latest quarterly compute"*, so for MA28 that IS the rule.
  * **F-12 AND F-15 ARE NOT SERVED BY THIS ARTIFACT.** Their rules need per-name DATES (an
    earnings calendar; insider filing dates), and a date per name is much closer to the
    vendor's dataset than a bit is. Exporting them needs its own decision and is deliberately
    not taken here -- the safe direction again.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCHEMA = "fleet_gates/1"

#: Where the derived artifact lands. TRACKED and shipped in the image, unlike `data/`.
OUT_REL = os.path.join("data_export", "fleet_gates.json")

#: The ONLY gates this exporter knows how to emit. A gate absent here is absent from the
#: artifact, and the reader reports it as UNKNOWN rather than defaulting it either way.
GATES = ("ma28_clean", "evt_clean", "optionable")

LICENSE_NOTE = (
    "DERIVED, NOT REDISTRIBUTED. Each value is a single boolean per ticker, reduced from "
    "thousands of licensed Sharadar rows by a published rule. No vendor row, price, "
    "financial-statement line or score is present, and the reduction is not reversible. "
    "The licensing judgement is Don's; this lane took the safe direction (booleans only) "
    "and the exporter refuses to widen. Do not add a numeric field to this artifact without "
    "putting that decision to him first."
)


def _repo() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _primary_data() -> str:
    """The PRIMARY data root, not the worktree's.

    `DEEPITM-FIN`'s defect: a worktree carries an EMPTY `data/` that shadows the populated
    primary and turns a real read into a silent zero. Resolved by probing for the file this
    exporter cannot run without, never by `isdir`.
    """
    here = _repo()
    cands = [os.path.join(here, "data"),
             os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(here))), "data")]
    for c in cands:
        if os.path.exists(os.path.join(c, "free_analysis", "E5_FLAGS.pkl")):
            return c
    raise SystemExit(
        "no data root carries free_analysis/E5_FLAGS.pkl. This exporter must run where the "
        "licensed exports are; it is offline machinery and never runs in the image.")


def _ma28_clean(data_root: str) -> dict:
    """`n_flags == 0` at the LATEST panel date. MA28's own 2-of-3 rule, not re-derived."""
    import pandas as pd
    df = pd.read_pickle(os.path.join(data_root, "free_analysis", "E5_FLAGS.pkl"))
    as_of = str(max(df["date"]))[:10]
    cur = df[df["date"].astype(str).str[:10] == as_of]
    return {
        "as_of": as_of,
        "source": "MA28 accounting flags (Beneish M, Altman Z, external financing); "
                  "clean means 0 of 3 fired at the latest quarterly compute",
        "rule": "n_flags == 0",
        "n_tickers": int(len(cur)),
        "tickers": {str(t).upper(): bool(int(n) == 0)
                    for t, n in zip(cur["ticker"], cur["n_flags"])},
    }


def _evt_clean(data_root: str) -> dict:
    """NOT in E-4's worst tail-mass quintile on its latest covered date.

    The quintile is `market_tail.within_date_worst_quintile`, IMPORTED rather than
    reimplemented -- `B7`, and it carries the register's own `q` and `min_names`.
    """
    import pandas as pd
    from valuation.studies import market_tail as mt

    path = os.path.join(data_root, "free_analysis", "E4_TAIL_PANEL.pkl")
    if not os.path.exists(path):
        return {"absent": True,
                "reason": "E4_TAIL_PANEL.pkl not found under this data root. E-4's artifacts "
                          "were STRANDED in .claude/worktrees/worktree-greeks -- the third "
                          "sighting of that pattern. Copy it to the primary root and re-run."}
    df = pd.read_pickle(path)
    df = df[df["usable"].astype(bool)] if "usable" in df.columns else df
    as_of = str(max(df["date"]))[:10]
    cur = df[df["date"].astype(str).str[:10] == as_of].copy()
    flag = mt.within_date_worst_quintile(cur, "tail_mass")
    return {
        "as_of": as_of,
        "source": "E-4 market-implied left-tail mass, worst within-date quintile; clean "
                  "means the name is in the bottom four quintiles",
        "rule": "not within_date_worst_quintile(tail_mass)",
        "n_tickers": int(len(cur)),
        "tickers": {str(s).upper(): bool(not f) for s, f in zip(cur["symbol"], flag)},
    }


def _optionable(data_root: str) -> dict:
    """The mined optionable universe, as one bit per name.

    Five books say *"optionable names"* and `options_universe.universe()` reads
    `data/options_universe/`, which is under the directory the image excludes -- so the
    universe LIST has exactly the same deployment problem as the flags do, and the same
    answer. It is already a derived selection (names whose chains passed the miner's own
    viability bar), so one bit per name loses nothing a rule needs.

    THE SELECTION IS HINDSIGHT AND THE ARTIFACT SAYS SO. `O20` measured it: names were ranked
    into the mining pool by TODAY's market cap, so a name that was liquid in 2016 and has since
    shrunk was never cached. That is a property of the universe every consumer inherits, and it
    travels in `source` rather than being left in a module docstring nobody reads at 3am.
    """
    from valuation.edge import options_universe as OU
    names = OU.universe(data_root)
    return {
        "as_of": dt.date.today().isoformat(),
        "source": "options_universe.universe() -- the mined optionable set. SELECTION IS "
                  "HINDSIGHT (O20): the mining pool was ranked by TODAY's market cap, so "
                  "names that were liquid earlier and have since shrunk were never cached.",
        "rule": "ticker in options_universe.universe()",
        "n_tickers": int(len(names)),
        "tickers": {str(t).upper(): True for t in names},
    }


def build(data_root: str = None) -> dict:
    root = data_root or _primary_data()
    gates = {"ma28_clean": _ma28_clean(root), "evt_clean": _evt_clean(root),
             "optionable": _optionable(root)}
    assert set(gates) == set(GATES), "a gate was emitted that GATES does not name"
    return {
        "schema": SCHEMA,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "license_note": LICENSE_NOTE,
        "gates": gates,
    }


def _assert_booleans_only(payload: dict) -> int:
    """THE GUARANTEE, enforced at WRITE time and not only in a test.

    A test can be skipped, and this artifact's whole safety argument is that nothing but a bit
    per name leaves the licensed store. So the writer refuses rather than trusting the caller.
    """
    n = 0
    for name, g in (payload.get("gates") or {}).items():
        for t, v in (g.get("tickers") or {}).items():
            if not isinstance(v, bool):
                raise SystemExit("gate %s ticker %s carries a %s, not a bool. This artifact "
                                 "ships in the deployed image; only booleans leave."
                                 % (name, t, type(v).__name__))
            if not isinstance(t, str) or not t or len(t) > 12:
                raise SystemExit("gate %s has an implausible ticker key %r" % (name, t))
            n += 1
    return n


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    payload = build()
    n = _assert_booleans_only(payload)
    out = os.path.join(_repo(), OUT_REL)
    if "--check" in argv:
        print(json.dumps({k: v for k, v in payload.items() if k != "gates"}, indent=2))
        for name, g in payload["gates"].items():
            print("  %-12s as_of=%-12s n=%s%s"
                  % (name, g.get("as_of", "-"), g.get("n_tickers", 0),
                     "  ABSENT: " + g["reason"] if g.get("absent") else ""))
        print("%d booleans, nothing else. NOT written (--check)." % n)
        return 0
    with io.open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("wrote %s -- %d booleans across %d gates" % (OUT_REL, n, len(payload["gates"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
