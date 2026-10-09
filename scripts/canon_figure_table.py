# -*- coding: utf-8 -*-
"""`DECISION_canonical_move.md` steps 5 and 6 -- ONE table, every public figure, old -> new.

Addendum 1: *"hand the app fixer a single table of every public figure old -> new with where each
lives."* This builds it, and it builds it by **UNION of the artifacts that already measured each
figure** rather than by re-deriving anything -- re-deriving a landed figure in a third place is
how two numbers for one question come about (`B7`), and every row here already carries its own
register's verdict.

Sources, each already landed by this lane:

* `CORRECTED_CLAIMS.json`           -- part 1's eleven claims
* `CORRECTED_CLAIMS2_VERDICT.json`  -- part 2's fourteen (S22, hold_horizon, score_confidence,
                                       V6-B, R1 net-of-cost)
* `CORRECTED_FLOORS.json`           -- the seven calibrated floors
* `INDEX_BOOK_THREE_WAY.json`       -- the Index book's published / restricted / corrected columns
* the canonical `BACKTEST_RESULTS.json` -- the headline blocks

**THE THREE-STATE VOCABULARY IS CARRIED, NOT RE-DECIDED.** A row's `state` is whatever its own
register recorded. `UNMEASURED` rows keep their reason, because a row that cannot say why it is
unmeasured is indistinguishable from one nobody looked at.

**AND EVERY ROW NAMES ITS WEIGHTING.** Every figure is the DEPLOYED book (flat 1/7). Part 1b is
why that label is load-bearing rather than decorative: on this universe CPCV adopts
`ic-proportional`, and the adopted book's top-decile alpha is 2.83% against the deployed 6.07%.
"""
import io
import json
import os
import sys

WT = r"C:/Users/donni/Downloads/valuation-tool/.claude/worktrees/r1b"
FA = r"C:/Users/donni/Downloads/valuation-tool/data/free_analysis"
TMP = r"C:/Users/donni/.claude/jobs/2f90bb74/tmp/canon"
if WT not in sys.path:
    sys.path.insert(0, WT)

OUT_JSON = os.path.join(TMP, "CANONICAL_FIGURE_TABLE.json")
#: THE MARKDOWN GOES IN THE REPO, because addendum 1 asks for *"a single table ... handed to the
#: app fixer"* and a table in a gitignored scratch directory is not handed to anyone. The JSON
#: stays out of the repo: it is a research artifact and `data/` is where those live.
OUT_MD = os.path.join(WT, "CANONICAL_FIGURE_TABLE.md")


def load(name, root=FA):
    p = os.path.join(root, name)
    if not os.path.exists(p):
        return None
    return json.load(io.open(p, encoding="utf-8"))


def fmt(v):
    if isinstance(v, bool) or v is None:
        return repr(v)
    if isinstance(v, float):
        return "%.6f" % v
    if isinstance(v, (dict, list)):
        return json.dumps(v)[:120]
    return str(v)


def g(doc, *path):
    cur = doc
    for p in path:
        cur = (cur or {}).get(p) if isinstance(cur, dict) else None
    return cur


rows = []

# ------------------------------------------------------------------ parts 1 and 2, carried whole
for src, art in (("CORRECTED-CLAIMS part 1", load("CORRECTED_CLAIMS.json")),
                 ("CORRECTED-CLAIMS-2", load("CORRECTED_CLAIMS2_VERDICT.json"))):
    if not art:
        rows.append({"group": src, "figure": "(artifact absent)", "state": "UNMEASURED",
                     "why": "artifact not on this host"})
        continue
    for c in art.get("claims") or []:
        rows.append({
            "group": src,
            "figure": c.get("claim"),
            "published": c.get("published"),
            "corrected": c.get("corrected"),
            "state": c.get("state"),
            "why": c.get("why"),
            "surface": c.get("surface"),
            "note": c.get("note"),
        })

# ---------------------------------------------------------------------------------- the floors
fl = load("CORRECTED_FLOORS.json")
if fl:
    for f in fl.get("floors") or []:
        rows.append({
            "group": "calibrated floors (X7's sweep, re-run on this universe)",
            "figure": "%s floor (%s)" % (f.get("floor"), f.get("percentile")),
            "published": f.get("current"),
            "corrected": f.get("corrected"),
            "state": ("SURVIVES" if f.get("headline_clears_corrected_floor")
                      else "NO LONGER HOLDS"),
            "surface": ("valuation/web/research_record.py PLACEBO_FLOOR"
                        if f.get("key") == "long_short_tstat_nw" else None),
            "note": ("HARDER on the corrected universe" if f.get("harder")
                     else "easier on the corrected universe"),
        })

# ------------------------------------------------------------------------------- the Index book
tw = load("INDEX_BOOK_THREE_WAY.json")
if tw:
    for r in tw.get("served_arm_table") or []:
        if not isinstance(r, dict):
            continue
        rows.append({
            "group": "Index book (served construction)",
            "figure": r.get("metric") or r.get("name") or r.get("key"),
            "published": r.get("published"),
            "corrected": r.get("corrected"),
            "restricted": r.get("restricted"),
            "state": ("RESTATEMENT" if r.get("published") != r.get("corrected")
                      else "SURVIVES"),
            "surface": "valuation/screener/index_book_measured.py (committed literals)",
            "note": "the RESTRICTED column separates newer data from wider universe",
        })

# --------------------------------------------------------------------- the canonical headlines
canon = load("BACKTEST_RESULTS.json", root=WT)
before = load("BACKTEST_RESULTS.before.json", root=TMP)
if canon and before:
    for label, path, surface in (
        ("top-decile alpha (annualised)", ("construction", "top_decile_alpha"), None),
        ("long-short t (naive)", ("construction", "long_short_tstat"), None),
        ("long-short t (HAC) -- THE HEADLINE",
         ("construction", "long_short_tstat_nw"),
         "valuation/web/research_record.py HEADLINE_STATISTIC"),
        ("top-decile alpha t (HAC)", ("construction", "top_decile_alpha_tstat_nw"), None),
        ("monotonicity", ("construction", "monotonicity"), None),
        # PBO and the Deflated Sharpe ship as {value, want, meaning} dicts -- the FIGURE is one
        # level down. And the hurdle key is `multiple_testing.hlz.hurdle_sqrt_2_ln_N`, not
        # `hlz_hurdle`: a wrong path here does not raise, it returns None on BOTH sides and
        # reads as "unchanged".
        #
        # ** AND THESE TWO DESCRIBE A DIFFERENT BOOK FROM EVERY OTHER ROW IN THIS GROUP. **
        # `cpcv_validate` scores whichever scheme adoption chose, and on this universe CPCV
        # ADOPTED `ic-proportional`. So `construction.*` above is the DEPLOYED book and
        # `cpcv.*` is the ADOPTED one -- see the note in the table.
        ("PBO (ADOPTED book)", ("cpcv", "pbo", "value"), None),
        ("Deflated Sharpe (ADOPTED book)", ("cpcv", "deflated_sharpe", "value"), None),
        ("HLZ hurdle sqrt(2 ln N)", ("multiple_testing", "hlz", "hurdle_sqrt_2_ln_N"), None),
        ("HLZ: clears the hurdle?", ("multiple_testing", "hlz", "clears_hlz_hurdle"), None),
        ("trials, equity", ("multiple_testing", "by_domain", "equity"), None),
        ("universe n_names", ("universe", "n_names"), None),
        ("universe n_dates", ("universe", "n_dates"), None),
        ("book_configs.roth.net_alpha (PUBLIC: landing page)",
         ("book_configs", "roth", "net_alpha"),
         "valuation/screener/settings.py measured() -> index_track.backtested"),
        ("book_configs.roth.net_max_drawdown (PUBLIC)",
         ("book_configs", "roth", "net_max_drawdown"),
         "valuation/screener/settings.py measured()"),
        ("book_configs.taxable.after_tax_alpha (PUBLIC)",
         ("book_configs", "taxable", "after_tax_alpha"),
         "valuation/screener/settings.py measured()"),
    ):
        o, n = g(before, *path), g(canon, *path)
        rows.append({
            "group": "BACKTEST_RESULTS.json (canonical, DEPLOYED book)",
            "figure": label,
            "published": o,
            "corrected": n,
            "state": ("SURVIVES" if o == n else "RESTATEMENT"),
            "surface": surface,
            "note": "the headline is the DEPLOYED flat 1/7 book (step 1)",
        })

res = {
    "item": "CANONICAL-MOVE",
    "part": "steps 5 and 6 -- every public figure, old -> new, with where it lives",
    "trials": 0,
    "trial_class": "CONSOLIDATION -- a union of landed artifacts. No hypothesis, no bar, no arm, "
                   "no new outcome statistic.",
    "weighting": "DEPLOYED (flat 1/7) on every row; CPCV is never the headline (step 1)",
    "sources": ["CORRECTED_CLAIMS.json", "CORRECTED_CLAIMS2_VERDICT.json",
                "CORRECTED_FLOORS.json", "INDEX_BOOK_THREE_WAY.json", "BACKTEST_RESULTS.json"],
    "n_rows": len(rows),
    "rows": rows,
}
by_state = {}
for r in rows:
    by_state[r.get("state")] = by_state.get(r.get("state"), 0) + 1
res["tally"] = by_state

io.open(OUT_JSON, "w", encoding="utf-8").write(json.dumps(res, indent=1))

# ---------------------------------------------------------------------------- the markdown table
md = ["# The canonical move — every public figure, old → new",
      "",
      "**For the app-fixer lane.** Generated by `scripts/canon_figure_table.py`; do not hand-edit.",
      "Sources are named at the bottom. Full reasoning: `DECISION_canonical_move.md`.",
      "",
      "**Weighting: the DEPLOYED book (flat 1/7) on every row.** Step 1 made that the canonical",
      "headline, and on this universe it is load-bearing rather than decorative: **CPCV ADOPTED",
      "`ic-proportional`** (median out-of-sample IC +0.096 against the default's +0.057, positive",
      "in 100% of 15 paths), and the adopted book's top-decile alpha is **2.83%** against the",
      "deployed **6.07%**. Without step 1 the canonical headline would have re-pointed to a book",
      "nobody runs — and it would have flattered DOWNWARD.",
      "",
      "**Every row's state is its own register's verdict, carried rather than re-decided.**",
      "",
      "---",
      "",
      "## THE CAVEAT THAT BOUNDS EVERY ROW BELOW: the two panels share ZERO rebalance dates",
      "",
      "| | published | corrected |",
      "|---|---|---|",
      "| names | 2,531 | 9,645 |",
      "| rebalance dates | 69 | 69 |",
      "| first / last | 2009-01-15 / 2026-01-28 | 2009-03-27 / 2026-04-09 |",
      "| **dates in common** | — | **0** |",
      "",
      "The grid is derived from the universe's own trading calendar, so a 3.8× wider universe",
      "shifts every date. **`X2` measured the grid ALONE moving the long-short *t* by 0.81**",
      "(2.703–3.517 across seven equally valid offsets on one universe). So every `RESTATEMENT`",
      "below is a restatement under a universe change **and** a grid change, and the two are not",
      "separated. The corrected figure is still the right figure for the corrected panel — what",
      "is unattributable is *why* it moved, not *what* it is.",
      "",
      "**The measurement itself is controlled:** all seven of `CORRECTED-FLOORS` part 1b's",
      "independently landed deployed statistics reproduce in the canonical file at",
      "**|dev| 0.000e+00** on the same 9,645 names, by a different call path.",
      "",
      "---",
      "",
      "## READ THIS FIRST — what changes on the PUBLIC SITE, with no app-lane edit",
      "",
      "`BACKTEST_RESULTS.json` is **tracked**, ships in the deploy image, and",
      "`settings.measured()` reads it **at request time** → `index_track.backtested` → the",
      "landing page's *\"Backtested net alpha\"*. So these three move on the next deploy by",
      "themselves:",
      "",
      "| public figure | published | corrected |",
      "|---|---|---|",
      "| `book_configs.roth.net_alpha` | **+11.63%/yr** | **−4.70%/yr** |",
      "| `book_configs.roth.net_max_drawdown` | −26.2% | **−59.7%** |",
      "| `book_configs.taxable.after_tax_alpha` | +2.11% | **−0.57%** |",
      "",
      "**A sign flip on the headline number a visitor sees.** The direction is coherent —",
      "`roth` is a concentrated **top-25** book, and top-25-of-9,645 is the top 0.26% of a",
      "universe whose ~7,100 added names are overwhelmingly small, which is exactly where",
      "`UNIVERSE-BIAS` and `TIERED-POOL` measured that reaching down the cap scale does not pay.",
      "**It is Don's call whether this ships**; `DECISION_canonical_move.md` §8.9 states the",
      "three options and this lane's recommendation (report the `$10B` Index book, which is the",
      "book a visitor can actually buy, rather than the all-cap top-25 `roth` config).",
      "",
      "**And one result in the other direction:** the headline long-short HAC *t* now **clears",
      "the Harvey-Liu-Zhu hurdle** for the first time — 4.5945 against √(2·ln 285) = 3.3623,",
      "where the published 2.6199 fell short of 3.2899. It clears the corrected placebo floor",
      "too, so both bars pass at once. **Not a new result** — the same composite on a wider",
      "universe and a disjoint grid.",
      ""]
groups = []
for r in rows:
    if r["group"] not in groups:
        groups.append(r["group"])
for grp in groups:
    md += ["## %s" % grp, "",
           "| figure | published | corrected | state | where it lives |",
           "|---|---|---|---|---|"]
    for r in rows:
        if r["group"] != grp:
            continue
        md.append("| %s | %s | %s | **%s** | %s |"
                  % (str(r.get("figure"))[:78].replace("|", "\\|"),
                     fmt(r.get("published")).replace("|", "\\|"),
                     fmt(r.get("corrected")).replace("|", "\\|"),
                     r.get("state"),
                     (r.get("surface") or "-- (research record only)").replace("|", "\\|")))
    md.append("")
md += ["---", "", "## Sources — every figure is read from a landed artifact, none re-derived here",
       ""] + ["* `%s`" % x for x in res["sources"]]
io.open(OUT_MD, "w", encoding="utf-8", newline="\n").write("\n".join(md) + "\n")

print("rows %d | tally %r" % (len(rows), by_state))
print("-> %s" % OUT_JSON)
print("-> %s" % OUT_MD)
