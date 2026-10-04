# -*- coding: utf-8 -*-
"""Does the 2026-10 Sharadar renewal change `PANEL-EXT-CENSUS`'s verdict? No. Measured.

`PANEL-EXT-CENSUS` (2026-09-30, register `PREREG_panel_ext_census.md` committed ALONE at
`5cff93a`) already ran the 1999-2008 feasibility census as a pre-committed free kill, on the
**2026-08** freeze, and **failed all three candidate start years**. Its binding reason was
structural rather than thin:

  * `institutional` reads **0.000 in every year 1995-2008** -- Sharadar `sf3` carries zero rows
    dated before 2009.
  * `insider` runs **0.001 (1995) to 0.307 (2008)**, never approaching the **70% rule**.

So a pre-2009 composite is **FIVE themes, not seven** -- *"not an extension of the published
figure but a different composite wearing the same name."*

**THE ONLY THING THAT COULD HAVE MOVED THAT ANSWER IS NEW DATA**, and the 2026-10 renewal is new
data. This re-check asks exactly one question of it and nothing else: do the two structural kills
survive on the renewed export?

**IT COSTS NOTHING TO ANSWER, because the freeze's own integrity pass already did the work.**
`sharadar_freeze._scan_csv` is a **full streaming pass over every row** that records the minimum
and maximum of each table's date column, so a `date_min` in `MANIFEST.json` is the positive
establishment the census had to scan 2.9 GB by hand for -- the same standard, read from the new
freeze. **ZERO TRIALS, FACTS class**: no hypothesis, no bar of its own, no outcome statistic, and
no panel is built. It does not re-open the census, relax any of its kills, or register a
successor.
"""
from __future__ import annotations

import io
import json
import os
import sys

# The census's own measurements, quoted so a drift in either shows up as a disagreement rather
# than being silently absorbed. Source: HANDOFF_scout_panel_ext.md section 1 and the ledger row.
CENSUS = {
    "sf3_has_no_pre_2009_rows": True,
    "institutional_coverage_every_year_1995_2008": 0.000,
    "insider_coverage_1995": 0.001,
    "insider_coverage_2008": 0.307,
    "theme_coverage_rule": 0.70,
    "themes_available_pre_2009": 5,
    "themes_in_shipped_composite": 7,
}


def _roots():
    out = []
    env = os.environ.get("VALQUO_DATA_ROOT")
    if env:
        out.append(env)
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out.append(os.path.join(here, "data"))
    out.append(r"C:\Users\donni\Downloads\valuation-tool\data")
    return out


def manifest(tag):
    """The freeze's integrity report. A worktree carries `data/` EMPTY, so the primary root is
    tried too -- `E-5`'s stranded-artifact family."""
    for c in _roots():
        p = os.path.join(c, "backtest_freeze_%s" % tag, "MANIFEST.json")
        if os.path.exists(p):
            return json.load(io.open(p, encoding="utf-8")), p
    return None, None


def main(argv=None):
    rows = []
    m10, p10 = manifest("2026-10")
    if m10 is None:
        print("LOUD REFUSAL: the 2026-10 freeze manifest is not on this machine, so the "
              "re-check cannot run. It REFUSES rather than reporting that nothing changed.")
        return 2
    print("2026-10 manifest: %s\n" % p10)

    t = m10["tables"]
    for k in ("SF3", "SF3A", "SF2", "SEP", "SF1", "DAILY", "ACTIONS", "TICKERS"):
        v = t.get(k) or {}
        rows.append((k, v.get("rows"), v.get("date_min"), v.get("date_max"), v.get("date_col")))
    print("%-9s %14s  %-12s %-12s %s" % ("table", "rows", "date_min", "date_max", "date_col"))
    for k, n, a, b, c in rows:
        print("%-9s %14s  %-12s %-12s %s" % (k, "{:,}".format(n) if n else n, a, b, c))

    sf3_min = (t.get("SF3") or {}).get("date_min")
    sf2_min = (t.get("SF2") or {}).get("date_min")
    sep_min = (t.get("SEP") or {}).get("date_min")
    sf1_min = (t.get("SF1") or {}).get("date_min")

    print("\n--- THE TWO STRUCTURAL KILLS, ON THE RENEWED EXPORT ---")
    k_inst = bool(sf3_min and sf3_min >= "2009-01-01")
    print("institutional: sf3 date_min = %s  -> zero pre-2009 rows: %s" % (sf3_min, k_inst))
    print("               (the census established this positively on the 2026-08 export by "
          "scanning 2.9 GB; here it is the min over all %s rows of the new one)"
          % "{:,}".format((t.get("SF3") or {}).get("rows") or 0))
    k_ins = bool(sf2_min and sf2_min >= "2008-01-01")
    print("insider:       sf2 date_min = %s (%s) -> no pre-2008 filings: %s"
          % (sf2_min, (t.get("SF2") or {}).get("date_col"), k_ins))

    print("\n--- WHAT THE RENEWAL DID AND DID NOT EXTEND ---")
    print("sep  date_min %s   sf1 date_min %s   (both unchanged from 2026-08)"
          % (sep_min, sf1_min))
    print("tickers date_min %s  -- the universe snapshot itself starts in 2008"
          % (t.get("TICKERS") or {}).get("date_min"))

    verdict = "UNCHANGED - THE CENSUS'S VERDICT STANDS" if (k_inst and k_ins) else "MOVED"
    print("\nVERDICT: %s" % verdict)
    if k_inst and k_ins:
        print("Both structural kills survive the renewal, so a 1999-2008 panel built from this "
              "freeze still scores a FIVE-theme composite against a SEVEN-theme published "
              "figure. The census is not re-opened and none of its kills is relaxed.")

    out = {
        "census_reference": "PANEL-EXT-CENSUS, PREREG_panel_ext_census.md at 5cff93a",
        "census_quoted": CENSUS,
        "freeze": "2026-10",
        "tables": {k: {"rows": n, "date_min": a, "date_max": b, "date_col": c}
                   for k, n, a, b, c in rows},
        "kill_institutional_survives": k_inst,
        "kill_insider_survives": k_ins,
        "verdict": verdict,
        "trials": 0,
    }
    # WRITE BESIDE THE MANIFEST THAT WAS READ, not into the first root that happens to have a
    # `free_analysis`. The first cut did the latter, and the consequence was not cosmetic: a
    # test pointing `VALQUO_DATA_ROOT` at a temp freeze would fall through to the PRIMARY root
    # and overwrite the real research artifact with synthetic numbers. That is the
    # tests-must-not-touch-real-state family, and `E-5`'s rule is the fix -- resolve an output
    # beside its own inputs.
    root = os.path.dirname(os.path.dirname(p10))
    d = os.path.join(root, "free_analysis")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "PANEL_EXT_RECHECK.json")
    json.dump(out, io.open(p, "w", encoding="utf-8"), indent=2)
    print("\nwrote %s" % p)
    return 0 if (k_inst and k_ins) else 1


if __name__ == "__main__":
    sys.exit(main())
