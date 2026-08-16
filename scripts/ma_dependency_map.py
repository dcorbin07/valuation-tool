#!/usr/bin/env python3
"""
ma_dependency_map.py - build MA_DEPENDENCY_MAP.md and ma_dependency_edges.json.

    python scripts/ma_dependency_map.py            # write both artifacts
    python scripts/ma_dependency_map.py --check    # regenerate and diff (CI-safe)

Follows the audit-#1 precedent (valquo_audit_items.json + check_lanes.py +
VALQUO_AUDIT_DEPENDENCY_MAP.md): the items file is the record, and the map is
GENERATED from it so the two cannot drift. That drift is the failure the first
map's own closing section warned about.

SOURCE, and why there are two
-----------------------------
Prefers valquo_master_audit_ultimate_items.json (the merged 60-row record of
audit #3, Pass A MA1-35 + Pass B MA36-60) and falls back to the 35-row
valquo_master_audit_items.json. The fallback is not decoration: at the time this
was written the ultimate file existed only on an unlanded branch, and a generator
that hard-required it would have been broken on main.

FOUR KINDS OF EDGE, kept apart because the cures differ
-------------------------------------------------------
  explicit     the item's own depends_on. The audit's claim.
  hard-file    two items name the same file. A textual conflict is likely, so
               they need one owner or a landing order - not two branches.
  soft-import  two items touch files where one imports the other. The merge is
               CLEAN and the build can still break. This is the class the first
               map found between B1 and B2, and it is invisible to git.
  logical      derived here, with a reason string. Not in the audit; argued.

Pass B items (MA36-MA60) ship empty modifies/creates/depends_on, so every edge
they carry is derived from `files` - which is why hard-file edges are computed
from `files` for ALL items rather than from `modifies`. Using `modifies` would
have silently produced zero collisions for 25 of the 60 items.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
CANDIDATES = ["valquo_master_audit_ultimate_items.json", "valquo_master_audit_items.json"]
MD_OUT = ROOT / "MA_DEPENDENCY_MAP.md"
JSON_OUT = ROOT / "ma_dependency_edges.json"

# --------------------------------------------------------------------------- lanes
# The five standing lanes. "owner" is the human/agent shorthand the project uses.
LANES = {
    "pipeline":   "edge / research / backtest - the panel and the statistics",
    "options-bot": "options engine, chains, ticks, greeks, the forward options book",
    "app-fixer":  "web + saas - public surfaces, auth, rate limits, templates",
    "greeks":     "screener + engine + intraday - the live scoring and marking path",
    "infra":      "CI, workflows, backup, docs, process, the register machinery",
}
# Ties are broken in this order. Pipeline first because a statistics or panel change
# is the one that invalidates published numbers; infra last because an infra file
# alongside real code is usually incidental (a workflow, a doc).
TIE_ORDER = ["pipeline", "options-bot", "app-fixer", "greeks", "infra"]


def lane_of_file(path: str) -> str:
    p = path.lower().replace("\\", "/").strip()
    p = p.split(":")[0] if re.match(r"^[a-z0-9_./-]+\.[a-z]+:", p) else p
    if p.startswith("c:/") or p.startswith("data/"):
        # A data path is owned by whoever owns the code that writes it.
        return "options-bot" if "option" in p else "pipeline"
    if p.startswith("options-bot/"):
        return "options-bot"
    # Options beats edge: an options file under valuation/edge/ is the options lane's.
    if re.search(r"(option|theta|blackscholes|scream|vrp)", p):
        return "options-bot"
    if p.startswith(".github/") or p.endswith((".bat", ".ps1", ".yml", ".yaml")) \
       or p.startswith("requirements") or p.startswith("dockerfile") or p == "check_lanes.py":
        return "infra"
    # RESEARCH_LOG.md is deliberately NOT here: it is the trial counter, and the edge lane
    # owns the denominator. Filing it under docs sent two research items to infra.
    if re.match(r"^(claude|run_rules|readme|agents|start_here|backtest_runbook|"
                r"valquo_ledger|env_reference|security_audit|paper_track_contract|"
                r"where_we_stand)", p):
        return "infra"
    if p.startswith("research_log"):
        return "pipeline"
    if p.startswith("scripts/build_ledger"):
        return "infra"
    if p.startswith(("valuation/web/", "valuation/saas/")):
        return "app-fixer"
    if p.startswith(("valuation/screener/", "valuation/intraday/", "valuation/engine/")) \
       or p.startswith("screener/"):
        return "greeks"
    if p.startswith(("valuation/edge/", "valuation/research/", "valuation/backtest/",
                     "scripts/", "prereg_")) or p.startswith("backtest_results"):
        return "pipeline"
    return "pipeline"


# Where the file counts give the wrong answer, say so out loud rather than tuning the
# classifier until it agrees. Each override is a judgement, and it is reviewable here.
LANE_OVERRIDE = {
    "MA1":  ("pipeline",  "the write path is saas, but the object being governed is the live "
                          "weight vector and its vintage - an edge-lane contract"),
    "MA4":  ("greeks",    "index_mark.py is the screener's writer for the contract-bound history"),
    "MA18": ("greeks",    "the writer lives in screener/index_mark.py; the DAILY WRITE itself is "
                          "Cowork's, and no repo lane can close this alone"),
    "MA34": ("pipeline",  "the contract text is the deliverable, but the prior belongs to the "
                          "lane that owns track_meter and the meter's power arithmetic"),
    "MA49": ("pipeline",  "a bundle spanning statistics, scripts and param_search; statistics.py "
                          "has ten importers and decides the lane"),
    "MA59": ("infra",     "a deletion/archival policy question across four lanes' dead files - "
                          "process, not any one engine"),
    # The deliverable is backup_to_D.ps1. The scripts/ paths are only where the data gets
    # READ, and counting them sent the backup items to the pipeline lane.
    "MA15": ("infra",     "the change is one allowlist entry in backup_to_D.ps1; the tickflow "
                          "scripts are consumers, not the work"),
    "MA16": ("infra",     "same - one $SKIP entry moved to $KEEP in backup_to_D.ps1"),
    "MA35": ("infra",     ".gitattributes - repository plumbing"),
    "MA10": ("app-fixer", "the credential is the product's; the workflow and render.yaml are "
                          "consumers of it, and they outvoted the owner"),
    "MA30": ("greeks",    "a display change on the screener's hot list; the panel reference is "
                          "the definition of tenure, not a panel edit"),
    "MA31": ("options-bot", "an options-surface arm on the raw chains"),
    "MA32": ("options-bot", "an options-volume arm on the raw chains"),
    "MA36": ("options-bot", "the forward OPTIONS book's censored -100% tail"),
    "MA56": ("options-bot", "residual term-slope is an options-entry feature"),
}

# --------------------------------------------------------------------------- imports
# Reused verbatim from check_lanes.py, which extracted them by grepping every from/import
# in the tree. Not re-derived here: a second, drifting copy of an import graph is worse
# than one shared one.
IMPORTS = {
    "valuation/edge/options_universe.py": {
        "valuation/edge/options_backtest.py", "valuation/edge/options_fill.py",
        "valuation/edge/options_signals_v2.py", "valuation/edge/options_autopsy.py",
        "valuation/edge/options_tracker.py", "valuation/edge/statistics.py"},
    "valuation/edge/options_backtest.py": {
        "valuation/edge/options_fill.py", "valuation/edge/options_tracker.py",
        "valuation/edge/blackscholes.py"},
    "valuation/edge/options_autopsy.py": {
        "valuation/edge/options_signals_v2.py", "valuation/edge/options_tracker.py",
        "valuation/edge/statistics.py"},
    "valuation/edge/options_greeks.py": {"valuation/edge/blackscholes.py"},
    "valuation/edge/fundamental_panel.py": {
        "valuation/screener/factors.py", "valuation/screener/settings.py",
        "valuation/screener/cross_sectional.py", "valuation/edge/statistics.py",
        "valuation/edge/research_log.py", "valuation/edge/results_file.py",
        "valuation/edge/payload_schema.py", "valuation/edge/walkforward.py",
        "valuation/edge/ablation.py"},
    "valuation/screener/screen.py": {
        "valuation/screener/factors.py", "valuation/screener/settings.py",
        "valuation/screener/cross_sectional.py", "valuation/config.py"},
    "valuation/edge/autolearn.py": {
        "valuation/backtest/optimize.py", "valuation/edge/fundamental_panel.py"},
    "valuation/saas/app_saas.py": {
        "valuation/saas/ratelimit.py", "valuation/saas/surfaces.py",
        "valuation/saas/auth.py", "valuation/screener/store.py"},
    "valuation/web/app.py": {
        "valuation/saas/ratelimit.py", "valuation/screener/store.py",
        "valuation/web/withhold.py"},
    "valuation/edge/paper_track.py": {
        "valuation/edge/options_tracker.py", "valuation/screener/index_track.py"},
    "valuation/edge/shadow_vintage.py": {"valuation/edge/track_meter.py"},
    # MA23 moved this out of `valuation/edge/` into `valuation/studies/`. The map's own
    # "What this map does not know" section says write-sets are the audit's PROPOSAL and that
    # an executing session must record the files it actually touched and regenerate — this is
    # that. The AUDIT's items file is deliberately NOT edited: it is the record of what the
    # audit said, and rewriting it would make the record agree with the tree by fiat.
    "valuation/studies/param_search.py": {"valuation/edge/fundamental_panel.py"},
    "valuation/intraday/options.py": {"valuation/edge/options_backtest.py"},
}

# --------------------------------------------------------------------------- logical
# Edges the audit does not state. Each is an argument, so each carries its reason.
LOGICAL = [
    ("MA5",  "MA6",  "the sqrt(2 ln N) bar IS a function of N, so it cannot be reconciled "
                     "against the 3.0 constant while the N counter still has a silent path"),
    ("MA19", "MA6",  "a calibrated floor is a percentile of a null the trials haircut moves; "
                     "X7RECON measured a floor changing because N changed"),
    ("MA19", "MA13", "re-deriving floors at N=224 asserts an N that nothing can currently "
                     "tamper-check"),
    ("MA2",  "MA19", "recalibrating the learner's gate against floors that are themselves two "
                     "N-regimes stale would bank the staleness into the live model"),
    ("MA12", "MA11", "pinning the dependency set is what makes the unreviewed Action's fresh "
                     "install reproducible; unpinned, reviewing the workflow secures little"),
    # deploy-only: real, but about the MACHINE, not the work. Excluded from the wave
    # computation - otherwise MA20 would appear to block items whose code is already written.
    ("MA15", "MA20", "DEPLOYMENT ONLY, not authorship: backup_to_D.ps1 is executed from the "
                     "shared checkout, so an allowlist fix on main is not a fix on the machine",
     "deploy"),
    ("MA16", "MA20", "DEPLOYMENT ONLY - and measured 2026-08-14: the stale checkout's "
                     "backup_now.bat put 42 GB of .claude/.git back on D: in one manual run",
     "deploy"),
    ("MA33", "MA19", "a monthly panel is a different panel, and X7's floors are panel-specific; "
                     "arms scored on it have no calibrated bar until they are re-derived"),
    ("MA55", "MA25", "both read the valuation panel's liquidity/lens fields; MA25 settles what "
                     "those fields actually are before an arm is built on them"),
    ("MA37", "MA36", "both re-shape the live options record; fixing the censored -100% tail "
                     "changes the very rows the epoch filter must then scope"),
    ("MA46", "MA37", "reconciling two pnl_pct definitions is only meaningful once the record "
                     "they are computed over has a defined epoch"),
    ("MA60", "MA13", "mechanising the register's honesty-dependent steps presupposes the "
                     "denominator those steps write is tamper-evident"),
    # Direction matters: the LOW item follows the HIGH one. Written the other way round it
    # would have made a HIGH severity endpoint hole wait on a cosmetic 500.
    ("MA53", "MA50", "the same two endpoints and the same unvalidated numeric params - one "
                     "input-validation pass closes both, and splitting them invites a re-break"),
]

# The ultimate file's _meta records a Pass B re-rating its own item body never received.
# Applied here, visibly, rather than silently trusting either half.
SEVERITY_OVERRIDE = {
    "MA18": ("HIGH", "_meta.corrections_to_pass_A re-rates MA18 MEDIUM->HIGH (run #2 has "
                     "recorded zero rows ever); the item body still reads MEDIUM. The file "
                     "disagrees with itself and the correction is the later statement."),
}

# Items that must charge a trial / need a written register before they can run.
RESEARCH = {"MA24", "MA26", "MA27", "MA28", "MA30", "MA31", "MA32", "MA33",
            "MA54", "MA55", "MA57", "MA58"}
DONE = {"MA35"}          # landed c759250, verified: .gitattributes carries `*.pdf binary`


def load_items():
    for name in CANDIDATES:
        p = ROOT / name
        if p.exists():
            raw = p.read_text(encoding="utf-8-sig")
            return name, {k: v for k, v in json.loads(raw).items() if k != "_meta"}
    raise SystemExit("no audit items file found: " + ", ".join(CANDIDATES))


# --------------------------------------------------------------------------- moves
# Files an EXECUTING session relocated after the audit named them.  [AUDIT MA23]
#
# WHY AN ALIAS AND NOT AN EDIT TO THE ITEMS FILE. `valquo_master_audit_ultimate_items.json` is
# the RECORD of what the audit said; rewriting its paths would make the record agree with the
# tree by fiat and destroy the ability to check what was originally claimed. But a collision
# map whose keys are stale is worse than useless — it reports NO collision between two items
# that do touch the same file, which is the one direction this map must never fail in.
#
# MEASURED, NOT ASSUMED: applying the MA23 move without this table dropped 187 lines of
# soft-import collisions from the artifact, because item files still read
# `valuation/edge/param_search.py` while the import graph had moved to
# `valuation/studies/param_search.py`. The two stopped matching and the collisions vanished
# silently. Found by diffing the regenerated artifact rather than by reading the code.
MOVED = {
    "valuation/edge/ev_multiples_study.py": "valuation/studies/ev_multiples_study.py",
    "valuation/edge/convex_overlay.py": "valuation/studies/convex_overlay.py",
    "valuation/edge/earnings_surface.py": "valuation/studies/earnings_surface.py",
    "valuation/edge/kelly.py": "valuation/studies/kelly.py",
    "valuation/edge/loo_holdout.py": "valuation/studies/loo_holdout.py",
    "valuation/edge/ml_combiner.py": "valuation/studies/ml_combiner.py",
    "valuation/edge/surface_stock.py": "valuation/studies/surface_stock.py",
    "valuation/edge/live_replay.py": "valuation/studies/live_replay.py",
    "valuation/edge/bucket_floor.py": "valuation/studies/bucket_floor.py",
    "valuation/edge/portfolio_capacity.py": "valuation/studies/portfolio_capacity.py",
    "valuation/edge/param_search.py": "valuation/studies/param_search.py",
    "valuation/research/lazy_prices_ic.py": "valuation/studies/lazy_prices_ic.py",
}


def norm(f: str) -> str:
    """'valuation/web/app.py:519' -> 'valuation/web/app.py'. Parentheticals dropped, and a
    trailing FIELD reference dropped too.

    That last rule is not cosmetic. Three items name BACKTEST_RESULTS.json and two of them
    qualify it with the block they mean ('... cpcv.adopt_detail', '... multiple_testing.hlz').
    Without this the three normalise to three different strings and the map reports NO
    collision between items that edit the same file - a false negative, in the one direction
    a collision map must not fail."""
    f = f.strip().replace("\\", "/")
    f = re.sub(r"\s*\(.*?\)\s*$", "", f)
    f = re.sub(r":[\d,\-\s]+$", "", f).strip()
    head = f.split()[0] if f.split() else f
    # Only when the first token really is a filename - 'owned daily closes' must stay whole.
    if " " in f and re.fullmatch(r"[\w./-]+\.\w+", head):
        f = head
    # Resolve audit-era paths to where the file lives TODAY, so a relocated file still
    # collides with everything it collided with before. See MOVED above.
    return MOVED.get(f, f)


def build(items: dict) -> dict:
    files = {k: sorted({norm(f) for f in v.get("files", []) if norm(f)}) for k, v in items.items()}

    lanes, why = {}, {}
    for k, v in items.items():
        if k in LANE_OVERRIDE:
            lanes[k], why[k] = LANE_OVERRIDE[k]
            continue
        tally = defaultdict(int)
        for f in files[k]:
            tally[lane_of_file(f)] += 1
        if not tally:
            lanes[k], why[k] = "infra", "no files named"
            continue
        best = max(tally.values())
        lanes[k] = sorted([l for l, n in tally.items() if n == best],
                          key=TIE_ORDER.index)[0]
        why[k] = f"{dict(tally)}"

    co = {k: sorted({lane_of_file(f) for f in files[k]}, key=TIE_ORDER.index)
          for k in items}

    edges = []
    for k, v in items.items():
        for d in v.get("depends_on") or []:
            if d in items:
                edges.append({"from": k, "needs": d, "kind": "explicit",
                              "reason": "declared in the item's depends_on"})
    for row in LOGICAL:
        a, b, r = row[0], row[1], row[2]
        scope = row[3] if len(row) > 3 else "work"
        if a in items and b in items:
            edges.append({"from": a, "needs": b, "kind": "logical", "reason": r,
                          "scope": scope})

    # hard-file and soft-import are SYMMETRIC (a collision, not a direction).
    collisions = []
    ks = sorted(items, key=lambda x: int(x[2:]))
    for i, a in enumerate(ks):
        for b in ks[i + 1:]:
            shared = sorted(set(files[a]) & set(files[b]))
            if shared:
                collisions.append({"a": a, "b": b, "kind": "hard-file", "files": shared})
                continue
            soft = []
            for fa in files[a]:
                for fb in files[b]:
                    if fb in IMPORTS.get(fa, ()) or fa in IMPORTS.get(fb, ()):
                        soft.append(f"{fa} <-> {fb}")
            if soft:
                collisions.append({"a": a, "b": b, "kind": "soft-import",
                                   "files": sorted(set(soft))})

    # ------------------------------------------------------------------ waves
    needs = defaultdict(set)
    blocking = defaultdict(set)      # deploy-scope edges do NOT gate a wave
    for e in edges:
        needs[e["from"]].add(e["needs"])
        if e.get("scope", "work") != "deploy":
            blocking[e["from"]].add(e["needs"])

    sev_of = {k: SEVERITY_OVERRIDE.get(k, ((v.get("severity") or "").upper(), None))[0]
              for k, v in items.items()}

    wave, note = {}, {}
    for k, v in items.items():
        sev = sev_of[k]
        if k in DONE:
            wave[k], note[k] = 0, "already landed"
        elif sev in ("CRITICAL", "HIGH") and not blocking[k]:
            wave[k], note[k] = 1, "top severity, nothing to wait for"
        elif sev in ("HYPOTHESIS", "LOW") or k in RESEARCH:
            wave[k], note[k] = 3, ("charges trials - needs a register first" if k in RESEARCH
                                   else "speculative or low severity")
        else:
            wave[k], note[k] = 2, ("severity-first: unblocked by wave 1"
                                   if sev in ("CRITICAL", "HIGH")
                                   else "unblocked, zero trial cost")

    return {"items": items, "files": files, "lanes": lanes, "lane_why": why,
            "co_lanes": co, "edges": edges, "collisions": collisions, "sev": sev_of,
            "wave": wave, "wave_note": note, "needs": {k: sorted(v) for k, v in needs.items()}}


def emit_json(m: dict, source: str, in_flight: dict) -> dict:
    return {
        "_meta": {
            "generated_by": "scripts/ma_dependency_map.py",
            "source": source,
            "n_items": len(m["items"]),
            "lanes": LANES,
            "edge_kinds": {
                "explicit": "the item's own depends_on",
                "logical": "derived in the generator, with a reason - argued, not declared",
                "hard-file": "same file named by both items; symmetric; expect a text conflict",
                "soft-import": "import-coupled files; the merge is clean and the build can break",
            },
            "wave_rule": "1 = CRITICAL/HIGH with no unmet edge. 2 = everything else with no "
                         "trial cost, severity-first. 3 = HYPOTHESIS/LOW or charges a trial. "
                         "0 = already landed.",
            "caveat": "Pass B items (MA36-MA60) declare no modifies/creates/depends_on, so their "
                      "edges are derived from `files` only. An item that will touch a file the "
                      "audit did not name carries an edge this map cannot see.",
        },
        "severity_overrides": {k: {"applied": s, "was": items_sev, "why": w}
                               for k, (s, w) in SEVERITY_OVERRIDE.items()
                               for items_sev in [(m["items"][k].get("severity") or "").upper()]},
        "nodes": {k: {"title": v.get("title"), "severity": m["sev"][k],
                      "severity_as_written": (v.get("severity") or "").upper(),
                      "mandate": v.get("mandate"), "lane": m["lanes"][k],
                      "co_lanes": m["co_lanes"][k], "files": m["files"][k],
                      "wave": m["wave"][k], "wave_reason": m["wave_note"][k],
                      "needs_first": m["needs"].get(k, []),
                      "trial_cost": v.get("trial_cost"),
                      "in_flight": in_flight.get(k),
                      "lane_evidence": m["lane_why"][k]}
                  for k, v in sorted(m["items"].items(), key=lambda x: int(x[0][2:]))},
        "edges": m["edges"],
        "collisions": m["collisions"],
    }


WAVE_TITLE = {
    1: "WAVE 1 - CRITICAL and HIGH with nothing to wait for",
    2: "WAVE 2 - unblocked by wave 1, zero trial cost (severity-first)",
    3: "WAVE 3 - HYPOTHESIS, LOW, and everything that charges a trial",
}


def emit_md(m: dict, doc: dict, source: str) -> str:
    n = doc["nodes"]
    L = []
    A = L.append

    A("# Valquo - MA item dependency, lane and wave map")
    A("")
    A(f"**Companion to `VALQUO_MASTER_AUDIT_ULTIMATE.md`.** Generated by "
      f"`scripts/ma_dependency_map.py` from `{source}` ({len(n)} items), so the map cannot "
      f"drift from the record the way the first one warned it would. Regenerate after any "
      f"change to the items file; `--check` fails if the artifact is stale.")
    A("")
    A("| file | what it is |")
    A("|---|---|")
    A(f"| `{source}` | the record: per item, severity, files, depends_on |")
    A("| `ma_dependency_edges.json` | machine-readable: nodes with lane + wave, four kinds of edge, every collision |")
    A("| `ma_in_flight.json` | what is being worked RIGHT NOW, so nothing is dispatched twice |")
    A("| this document | the human-readable version |")
    A("")
    A("---")
    A("")
    A("## Four things worth knowing before dispatching anything")
    A("")

    w1 = [k for k in n if n[k]["wave"] == 1]
    w1_coll = [c for c in doc["collisions"] if c["a"] in w1 and c["b"] in w1]
    hot = sorted(((sum(1 for v in n.values() if f in v["files"]), f)
                  for f in {f for v in n.values() for f in v["files"]}), reverse=True)

    A(f"**1. Wave 1 is eleven items across all five lanes - and it is NOT eleven parallel "
      f"branches.** There are {len(w1_coll)} collisions inside wave 1 alone, and "
      f"{len([c for c in w1_coll if 'MA1' in (c['a'], c['b'])])} of them involve MA1, which "
      f"reaches into `app_saas.py`, `track_meter.py` and `auto-scan.yml` at once. MA1 is the "
      f"CRITICAL item and the most entangled one in the catalogue; it wants a single owner and "
      f"a quiet tree, not a slot in a fan-out.")
    A("")
    A(f"**2. `{hot[0][1]}` is still the programme.** {hot[0][0]} of {len(n)} items name it. "
      f"That is a smaller share than audit #1's 46-of-134, but it is the same fact: the panel "
      f"cannot be split across owners, and MA23 (break the finished one-shot studies out of "
      f"`valuation/edge/`) is the item that would change it.")
    A("")
    # Computed, not typed: these are exactly the numbers a lane override would move.
    tot = {L: sum(1 for v in n.values() if v["lane"] == L) for L in TIE_ORDER}
    inw1 = {L: sum(1 for k in w1 if n[k]["lane"] == L) for L in TIE_ORDER}
    A(f"**3. The size of a lane is a poor guide to how much of it is urgent.** Pipeline carries "
      f"{tot['pipeline']} of {len(n)} items but only {inw1['pipeline']} of the {len(w1)} in "
      f"wave 1; infra carries {tot['infra']} and {inw1['infra']} of wave 1. Wave 1 spreads "
      f"{'/'.join(str(inw1[L]) for L in TIE_ORDER)} across "
      f"{'/'.join(TIE_ORDER)} - the urgent work is thin and even, which is the argument for "
      f"running wave 1 wide rather than deep.")
    A("")
    A("**4. Two of the wave-1 items are already delivered by the branch that wrote this map** "
      "(MA15, MA16), and a third (MA20) has its alarm delivered with the cure left to Don. "
      "See `ma_in_flight.json` before starting anything.")
    A("")
    A("---")
    A("")
    A("## Corrections this map makes to its own brief")
    A("")
    A("**The in-flight list was wrong, and it matters because it routes work.** The brief named "
      "MA1-MA3 and MA5/MA6 as in flight. Measured on every local and remote branch, on `main`, "
      "and across all eleven registered worktrees: **none of the five has a commit anywhere.** "
      "What IS in flight is **MA13 + MA19** (`worktree-options-live`, PREREG committed 20:22) "
      "and **MA36 + MA37** (`worktree-optionsbot-lane`, PREREG committed 20:28) - both within "
      "twenty minutes of this map being built. Dispatching MA19 on the brief's list would have "
      "put two lanes on the same recalibration.")
    A("")
    A("**The three-wave rule as stated leaves a CRITICAL item in no wave at all.** Taken "
      "literally - wave 1 is CRITICAL+HIGH with no unmet deps, wave 2 is *MEDIUMs* - then MA2 "
      "(CRITICAL, needs MA1), MA3, MA10 and MA19 belong to nothing. They are placed at the "
      "**head of wave 2, severity-first**, and the rule is restated in the JSON's `wave_rule` "
      "so the next reader inherits the fix rather than the gap.")
    A("")
    A("**The items file disagrees with itself about MA18.** Its `_meta.corrections_to_pass_A` "
      "re-rates MA18 MEDIUM -> HIGH; the item body still reads MEDIUM. This map applies the "
      "later statement (HIGH, so wave 1) and records both readings on the node as `severity` "
      "and `severity_as_written`. Nothing is silently overwritten.")
    A("")
    A("**`modifies` cannot be used to find collisions here.** All 25 Pass B items (MA36-MA60) "
      "ship empty `modifies`/`creates`/`depends_on`. Computing collisions from `modifies`, as "
      "the audit-#1 machinery does, returns zero for 25 of 60 items - a clean map that is "
      "silently blind to nearly half the catalogue. Collisions are computed from `files`.")
    A("")
    A("---")
    A("")
    A("## Hot files")
    A("")
    A("| items | file | who |")
    A("|---|---|---|")
    for c, f in hot:
        if c >= 3:
            who = " ".join(sorted([k for k in n if f in n[k]["files"]],
                                  key=lambda x: int(x[2:])))
            A(f"| {c} | `{f}` | {who} |")
    A("")
    A("---")
    A("")
    A("## Lanes")
    A("")
    for lane in TIE_ORDER:
        ids = sorted([k for k in n if n[k]["lane"] == lane], key=lambda x: int(x[2:]))
        if not ids:
            continue
        A(f"### {lane} - {len(ids)} items")
        A("")
        A(f"*{LANES[lane]}*")
        A("")
        A("| ID | wave | sev | item | needs first | also touches |")
        A("|---|---|---|---|---|---|")
        for k in ids:
            v = n[k]
            nf = " ".join(v["needs_first"]) or "-"
            co = " ".join(x for x in v["co_lanes"] if x != lane) or "-"
            fl = v.get("in_flight") or {}
            st = (fl.get("state") or "").split(" -")[0].split(",")[0].strip()
            flag = f" **[{st or 'IN FLIGHT'}]**" if fl else ""
            A(f"| **{k}** | {v['wave'] or 'done'} | {v['severity']} | "
              f"{v['title'][:88]}{flag} | {nf} | {co} |")
        A("")
    A("---")
    A("")
    A("## The three waves")
    A("")
    for w in (1, 2, 3):
        ids = sorted([k for k in n if n[k]["wave"] == w], key=lambda x: int(x[2:]))
        A(f"### {WAVE_TITLE[w]} - {len(ids)} items")
        A("")
        A("| ID | sev | lane | item |")
        A("|---|---|---|---|")
        for k in ids:
            v = n[k]
            fl = v.get("in_flight") or {}
            st = (fl.get("state") or "").split(" -")[0].split(",")[0].strip()
            flag = f" **[{st or 'IN FLIGHT'}]**" if fl else ""
            A(f"| **{k}** | {v['severity']} | {v['lane']} | {v['title'][:92]}{flag} |")
        A("")
    done = sorted([k for k in n if n[k]["wave"] == 0], key=lambda x: int(x[2:]))
    if done:
        A(f"**Already landed:** {' '.join(done)} - "
          f"{n[done[0]]['title'][:70]} (verified on main).")
        A("")
    A("---")
    A("")
    A("## Wave 1: what may run concurrently")
    A("")
    A("These pairs may **not**, because they name the same file (`hard`) or import-coupled "
      "files (`soft` - the merge is clean and the build can still break):")
    A("")
    A("```")
    for c in w1_coll:
        A(f"{c['kind']:<12} {c['a']} x {c['b']}: {c['files'][0]}")
    A("```")
    A("")
    free = [k for k in w1 if not any(k in (c["a"], c["b"]) for c in w1_coll)]
    A(f"**Collision-free against everything in wave 1:** "
      f"{' '.join(sorted(free, key=lambda x: int(x[2:]))) or '(none)'}.")
    A("")
    # A safe fan-out is an INDEPENDENT SET in the collision graph, not a hand-picked list.
    # Written by hand the first time, this recommendation contained two colliding pairs.
    bad = {frozenset((c["a"], c["b"])) for c in w1_coll}
    order = sorted(w1, key=lambda k: (-sum(1 for c in w1_coll if k in (c["a"], c["b"])),
                                      int(k[2:])))
    picked = []
    for k in order:                      # most-entangled first, so MA1 anchors the set
        if all(frozenset((k, p)) not in bad for p in picked):
            picked.append(k)
    rest = sorted(set(w1) - set(picked), key=lambda x: int(x[2:]))
    A(f"**A safe first fan-out - computed as an independent set of the collision graph above, "
      f"not chosen by eye: `{' '.join(sorted(picked, key=lambda x: int(x[2:])))}`.** That is "
      f"{len(picked)} of the 11 running at once with no shared file and no import coupling. "
      f"The remaining {len(rest)} ({' '.join(rest)}) each collide with something in that set and "
      f"belong in the next round or under the same owner.")
    A("")
    A("---")
    A("")
    A("## Edges that actually constrain the order")
    A("")
    A("| chain | kind | why |")
    A("|---|---|---|")
    for e in sorted(doc["edges"], key=lambda x: (x["kind"], int(x["from"][2:]))):
        k = e["kind"] + ("/deploy" if e.get("scope") == "deploy" else "")
        A(f"| `{e['from']}` needs `{e['needs']}` | {k} | {e['reason']} |")
    A("")
    A("`explicit` is the audit's own `depends_on`. `logical` is derived here and argued - "
      "disagree with the reason and the edge goes. `logical/deploy` edges are real but concern "
      "the MACHINE rather than the work, and deliberately do **not** gate a wave: MA15 and MA16 "
      "are written and landed; what MA20 gates is whether they are running on Don's PC.")
    A("")
    A("---")
    A("")
    A("## Merge protocol at the hot files")
    A("")
    A("- **`fundamental_panel.py`** - one owner at a time. Twelve items land here; if two must "
      "overlap, do them as sequential commits on one branch, never two branches.")
    A("- **`app_saas.py`** - MA1, MA3, MA7, MA9 and MA10 all touch it, and MA1/MA3 change the "
      "same live-weight write path. This file is the app lane's bottleneck the way the panel is "
      "the edge lane's.")
    A("- **`.github/workflows/*`** - MA1, MA10, MA11, MA12, MA20 and MA60. Workflow files "
      "conflict textually on almost any edit; batch them.")
    A("- **`statistics.py`** - ten importers. A change here is global: land it alone, on a quiet "
      "tree, with the full suite green.")
    A("- **`backup_to_D.ps1`** - MA15 and MA16 are one commit's worth of work, and were done as "
      "one. Splitting them across branches guarantees a conflict in `$KEEP`.")
    A("")
    A("---")
    A("")
    A("## What this map does not know")
    A("")
    A("- **Write-sets are the audit's PROPOSAL.** An executing session that solves an item a "
      "different way changes its write-set, and this map goes stale. Record the files actually "
      "touched and regenerate.")
    A("- **Pass B items name files, not intentions.** MA36-MA60 declare no `modifies`, so an "
      "item that ends up editing a file the audit did not name carries an edge nothing here "
      "can see.")
    A("- **`ma_in_flight.json` sees only committed work.** An agent with uncommitted edits in a "
      "worktree is invisible, and so is any other machine. Absence is not evidence an item is "
      "free.")
    A("- **The import graph is grepped, not executed.** A dynamic import or runtime lookup would "
      "not appear. Nothing suggested one; the map cannot prove their absence.")
    A("- **Lane assignment is counted, then overridden by hand where counting was wrong** "
      f"({len(LANE_OVERRIDE)} overrides, each with its reason on the node as `lane_evidence` "
      "and in the generator). It is a dispatch aid, not a statement about who is allowed to "
      "touch what.")
    A("")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="regenerate in memory and fail if the artifacts are stale")
    a = ap.parse_args(argv)

    source, items = load_items()
    m = build(items)
    in_flight = json.loads((ROOT / "ma_in_flight.json").read_text(encoding="utf-8")) \
        if (ROOT / "ma_in_flight.json").exists() else {}
    doc = emit_json(m, source, in_flight)
    text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"

    md = emit_md(m, doc, source)

    if a.check:
        for path, want in ((JSON_OUT, text), (MD_OUT, md)):
            if not path.exists():
                print(f"MISSING {path.name}; run scripts/ma_dependency_map.py")
                return 1
            # Compare with line endings normalised. .gitattributes checks these files out
            # CRLF on Windows and LF on the Linux runner, so a byte comparison would call
            # the artifact stale on one platform and current on the other - a check that
            # fails for a reason unrelated to what it is checking.
            on_disk = path.read_text(encoding="utf-8").replace("\r\n", "\n")
            if on_disk != want.replace("\r\n", "\n"):
                print(f"STALE {path.name}: the items file has moved under it. Regenerate.")
                return 1
        print(f"{JSON_OUT.name} and {MD_OUT.name} are current against {source} "
              f"({len(items)} items)")
        return 0

    MD_OUT.write_text(md, encoding="utf-8")
    JSON_OUT.write_text(text, encoding="utf-8")
    print(f"wrote {JSON_OUT.name}: {len(items)} items from {source}, "
          f"{len(m['edges'])} edges, {len(m['collisions'])} collisions")
    for w in (1, 2, 3):
        ids = [k for k in sorted(m['wave'], key=lambda x: int(x[2:])) if m['wave'][k] == w]
        print(f"  wave {w}: {len(ids):2d}  {' '.join(ids)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
