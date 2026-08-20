"""SC-1b -- sharpening SC-1's CANNOT-TELL by clustering the gap by ITEM.
`PREREG_sc1b_cluster_by_item.md`, committed ALONE at `329402d`; the single INFRA trial was
booked at `58cf538`, before this file existed: infra 19 -> 20.

**ONE THING CHANGES: THE CLUSTERING KEY.** Every statistic, bar, regex, constant and seed comes
from `scripts/sc1_prior_calibration.py` by IMPORT -- nothing is re-implemented (`B7`), and `G1`
proves it by requiring this run to reproduce `SC-1`'s banked artifact at tolerance **0.0**.

**THE CORPUS IS PINNED TO `SC-1`'s OWN MEASUREMENT COMMIT, AND THAT IS FORCED BY THE REGISTER
RATHER THAN CHOSEN.** §0 says SC-1b changes exactly one thing and §6.2 forbids adding a pair,
so the pair set must be SC-1's -- and the record has GROWN since: four items' worth of scored
expectations landed the same day this ran, including three of this lane's own. Running on
today's tree would confound *more data* with *different clustering*, which is precisely the
comparison the register exists to isolate. Today's corpus is reported separately as a
**labelled diagnostic carrying no verdict**.

**NO MARKET DATA IS OPENED** -- inherited from `SC-1`'s C3 and pinned again here by an AST test.

Run:
    python -m scripts.sc1b_cluster_by_item --controls   # G1..G4, no verdict formed
    python -m scripts.sc1b_cluster_by_item --arms       # REFUSES without a passing controls file
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

import sc1_prior_calibration as SC1                                  # noqa: E402
from valuation.edge import power_gate as PG                          # noqa: E402

# ---------------------------------------------------------------------------------------
# EVERY CONSTANT IS SC-1's, BY IMPORT. Re-typing one here would be the re-choosing the
# register exists to avoid, so the only literals below are this item's own provenance.
# ---------------------------------------------------------------------------------------
SC1_COMMIT = "8e2e9fe"                 # SC-1's measurement commit -- the pinned corpus
SC1_JSON = os.path.join(r"C:\Users\donni\Downloads\valuation-tool", "data", "free_analysis",
                        "SC1_PRIOR_CALIBRATION.json")
SELF = "PREREG_sc1b_cluster_by_item.md"          # a register does not supply priors to its own
CTRL_JSON = "SC1B_CONTROLS.json"
ARMS_JSON = "SC1B_CLUSTER_BY_ITEM.json"
DEFAULT_OUT = os.path.join(r"C:\Users\donni\Downloads\valuation-tool", "data", "free_analysis")

#: §2 -- the item key. Level 1 or 2 only: the write-ups put one item per top-level section and
#: reserve `###` for subsections, so keying on ANY heading would merge two items' identically
#: titled "Expectations, scored" tables.
HEADING = re.compile(r"^(#{1,2})\s+(.+?)\s*$")


def _log(m):
    print(m, flush=True)


def _w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=float)


# ---------------------------------------------------------------------------------------
# the pinned corpus
# ---------------------------------------------------------------------------------------
def materialise(commit: str, dest: str) -> List[str]:
    """Write every corpus file AS OF `commit` into `dest`, keeping basenames.

    `SC-1`'s functions key on `os.path.basename`, so a faithful replay needs the same names and
    the same contents -- not today's.
    """
    listing = subprocess.run(["git", "ls-tree", "-r", "--name-only", commit],
                             cwd=REPO, capture_output=True, text=True, check=True).stdout
    want = []
    for path in listing.splitlines():
        if "/" in path:
            continue                                   # the corpus is repo-root markdown only
        b = os.path.basename(path)
        if (b.startswith("PREREG_") or b.startswith("DESIGN_") or b.startswith("HANDOFF_")
                or b.startswith("VALQUO_MASTER_AUDIT") or b == "VALQUO_EDGE_AUDIT.md"
                or b == "CLAUDE.md"):
            want.append(path)
    os.makedirs(dest, exist_ok=True)
    for path in want:
        blob = subprocess.run(["git", "show", f"{commit}:{path}"],
                              cwd=REPO, capture_output=True, check=True).stdout
        with open(os.path.join(dest, os.path.basename(path)), "wb") as fh:
            fh.write(blob)
    return want


def corpus(root: str) -> Tuple[List[str], List[str]]:
    """`SC-1`'s own file selection, reproduced against a root. Its `SELF`/`DRAFT` exclusions are
    imported; this register's own file is excluded on the same principle."""
    import glob
    prereg = sorted(glob.glob(os.path.join(root, "PREREG_*.md")))
    prereg = [p for p in prereg
              if os.path.basename(p) not in (SC1.SELF, SC1.DRAFT, SELF)]
    audits = sorted(glob.glob(os.path.join(root, "VALQUO_MASTER_AUDIT*.md")))
    audits += [p for p in sorted(glob.glob(os.path.join(root, "VALQUO_EDGE_AUDIT.md")))]
    designs = sorted(glob.glob(os.path.join(root, "DESIGN_*.md")))
    adjud = sorted(glob.glob(os.path.join(root, "HANDOFF_*.md")))
    adjud += [os.path.join(root, "CLAUDE.md")]
    return ([p for p in prereg + audits + designs if os.path.isfile(p)],
            [p for p in adjud if os.path.isfile(p)])


# ---------------------------------------------------------------------------------------
# the item key
# ---------------------------------------------------------------------------------------
def heading_rows(path: str) -> List[Tuple[str, float, str, str]]:
    """Re-scan one file with `SC-1`'s OWN predicate, recording the item heading per matched row.

    **THE PREDICATE IS NOT RE-INVENTED**: `SC1.MARK`, `SC1.ODDS` and the `!= 1` odds rule are
    imported, so only the ~10-line loop is duplicated -- and `G1b` then requires this scan to
    produce the SAME rows in the SAME order as `SC1.scoring_rows`, so the duplication is CHECKED
    rather than trusted. `E-5`'s C7 pattern: prove two loops are the same by measurement.
    """
    name = os.path.basename(path)
    out: List[Tuple[str, float, str, str]] = []
    item = "(no heading)"
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            h = HEADING.match(line)
            if h:
                item = h.group(2).strip()
                continue
            if "|" not in line:
                continue
            m = SC1.MARK.search(line)
            if not m:
                continue
            odds = [(int(a) / 100.0) for a, b in
                    ((mm.group(1), mm.group(2)) for mm in SC1.ODDS.finditer(line))
                    if int(a) + int(b) == 100]
            if len(odds) != 1:
                continue
            out.append((name, odds[0], m.group(1).upper(), f"{name} :: {item}"))
    return out


def attach_items(pairs: List[dict], adjud: List[str]) -> Dict[str, object]:
    """Attach `item_cluster` to every scored row, and PROVE the attachment is aligned."""
    scan: List[Tuple[str, float, str, str]] = []
    for p in adjud:
        scan.extend(heading_rows(p))
    ok = len(scan) == len(pairs)
    mismatch = None
    if ok:
        for i, (row, s) in enumerate(zip(pairs, scan)):
            if (row["source_file"] != s[0] or abs(row["p"] - s[1]) > 0 or
                    row["marker"] != s[2]):
                ok, mismatch = False, {"index": i, "scored": [row["source_file"], row["p"],
                                                              row["marker"]],
                                       "rescan": [s[0], s[1], s[2]]}
                break
    if ok:
        for row, s in zip(pairs, scan):
            row["item_cluster"] = s[3]
    return {"rows_scored": len(pairs), "rows_rescanned": len(scan),
            "aligned": bool(ok), "first_mismatch": mismatch,
            "note": ("G1b. SC-1's scoring_rows records no line number, so the heading is "
                     "attached by a re-scan using SC-1's OWN regexes and predicate; this gate "
                     "requires the two to agree row-for-row and in order, so the duplication is "
                     "checked rather than trusted.")}


# ---------------------------------------------------------------------------------------
def build(root: str) -> Tuple[List[dict], Dict[str, object], List[str], List[dict]]:
    sources, adjud = corpus(root)
    rows, _rej = SC1.extract_primary(sources)
    scored = SC1.adjudicate(SC1.scoring_rows(adjud), rows)
    scoreable = [s for s in scored
                 if s["outcome"] is not None and s["prior_traceable_to_a_register"]]
    pairs = [s for s in scoreable if s["class"] == "OUTCOME"]
    align = attach_items(scored, adjud)
    return pairs, align, adjud, rows


def double_entry(sources: List[str], rows: List[dict]) -> float:
    """`SC-1` §2.4, re-derived rather than assumed from its published 11.7%."""
    rng = random.Random(SC1.SEED)
    sample = (rng.sample(rows, max(1, int(round(SC1.DOUBLE_ENTRY_FRAC * len(rows)))))
              if rows else [])
    sec = SC1.extract_secondary(sources)
    idx: Dict[str, List[dict]] = {}
    for s in sec:
        idx.setdefault(s["source_file"], []).append(s)
    dis = 0
    for r in sample:
        # SC-1's EXACT predicate: the second pass must find the same odds value AND the same
        # class. Matching the value alone returns a confident 0.0000 -- the class is the
        # discriminating half, and dropping it makes the check unfailable.
        cand = [s for s in idx.get(r["source_file"], []) if abs(s["p"] - r["p"]) < 1e-9]
        if not (cand and any(c["class"] == r["class"] for c in cand)):
            dis += 1
    return (dis / len(sample)) if sample else 1.0


def _half(ci) -> Optional[float]:
    return None if ci is None or ci[0] is None else (ci[1] - ci[0]) / 2.0


def measure(pairs: List[dict]) -> Dict[str, object]:
    g = SC1.gap(pairs)
    nlo, nhi = SC1.naive_bootstrap(pairs, SC1.gap)
    flo, fhi = SC1.cluster_bootstrap(pairs, "source_file", SC1.gap)
    ilo, ihi = SC1.cluster_bootstrap(pairs, "item_cluster", SC1.gap)
    b = SC1.brier(pairs)
    base = sum(r["outcome"] for r in pairs) / len(pairs)
    b_base = sum((base - r["outcome"]) ** 2 for r in pairs) / len(pairs)
    b_half = sum((0.5 - r["outcome"]) ** 2 for r in pairs) / len(pairs)
    return {
        "n": len(pairs), "gap": g, "base_rate": base,
        "mean_p": sum(r["p"] for r in pairs) / len(pairs),
        "naive_ci95": [nlo, nhi], "naive_half_width": _half([nlo, nhi]),
        "file_ci95": [flo, fhi], "file_half_width": _half([flo, fhi]),
        "item_ci95": [ilo, ihi], "item_half_width": _half([ilo, ihi]),
        "n_clusters_file": len({r["source_file"] for r in pairs}),
        "n_clusters_item": len({r["item_cluster"] for r in pairs}),
        "brier": b,
        "brier_skill_vs_base_rate": 1 - b / b_base if b_base else None,
        "brier_skill_vs_uniform": 1 - b / b_half if b_half else None,
        "murphy": SC1.murphy(pairs),
    }


def power_block(pairs: List[dict], m: Dict[str, object]) -> Dict[str, object]:
    """§5 -- `SC-1`'s declared defect D1 REPAIRED: the se is formed from `Var(p - y)`."""
    d = [r["p"] - r["outcome"] for r in pairs]
    n = len(d)
    mu = sum(d) / n
    sd = math.sqrt(sum((x - mu) ** 2 for x in d) / (n - 1))
    se = sd / math.sqrt(n)
    deff = None
    if m["item_half_width"] and m["naive_half_width"]:
        deff = (m["item_half_width"] / m["naive_half_width"]) ** 2
    return {
        "sd_of_p_minus_y": sd, "iid_se": se, "n": n,
        "detection_threshold_50pct_power": PG.detection_threshold(se, crit=2.0),
        "mde_at_80pct_power": (2.0 + PG.Z_POWER_CONVENTION) * se,
        "realised_design_effect_item_vs_naive": deff,
        "cluster_adjusted_se": (se * math.sqrt(deff)) if deff else None,
        "cluster_adjusted_detection_threshold_50pct":
            (PG.detection_threshold(se * math.sqrt(deff), crit=2.0)) if deff else None,
        "cluster_adjusted_mde_at_80pct":
            ((2.0 + PG.Z_POWER_CONVENTION) * se * math.sqrt(deff)) if deff else None,
        "vocabulary": ("MB22: crit x se is a 50%-POWER detection threshold; the 80%-power "
                       "figure adds 0.84 se. Both printed, each labelled."),
        "D1_repaired": ("SC-1's section 5 formed the MDE from BRIER variance where the gap "
                        "needs Var(p - y); it declared that as defect D1 before running and "
                        "directed readers to its empirical line. This computes it correctly."),
    }


# ---------------------------------------------------------------------------------------
def run_controls(args) -> int:
    with tempfile.TemporaryDirectory() as td:
        files = materialise(SC1_COMMIT, td)
        _log(f"[corpus] pinned to SC-1's measurement commit {SC1_COMMIT}: {len(files)} files")
        pairs, align, adjud, rows = build(td)
        sources, _ = corpus(td)
        _log(f"[pairs] {len(pairs)} OUTCOME pairs; alignment ok={align['aligned']}")
        m = measure(pairs) if (pairs and align["aligned"]) else None
        de = double_entry(sources, rows)

        with open(SC1_JSON, encoding="utf-8") as fh:
            banked = json.load(fh)

        # ---- G1 IDENTITY, tolerance 0.0 ----
        checks = {}
        if m:
            for mine, theirs in (("n", "n"), ("gap", "gap"), ("brier", "brier"),
                                 ("base_rate", "base_rate"), ("mean_p", "mean_p"),
                                 ("brier_skill_vs_base_rate", "brier_skill_vs_base_rate"),
                                 ("brier_skill_vs_uniform", "brier_skill_vs_uniform")):
                checks[theirs] = {"mine": m[mine], "banked": banked.get(theirs),
                                  "equal": m[mine] == banked.get(theirs)}
            checks["ci95_file"] = {"mine": m["file_ci95"], "banked": banked.get("ci95"),
                                   "equal": m["file_ci95"] == banked.get("ci95")}
            checks["naive_ci95"] = {"mine": m["naive_ci95"], "banked": banked.get("naive_ci95"),
                                    "equal": m["naive_ci95"] == banked.get("naive_ci95")}
            checks["murphy"] = {"mine": m["murphy"], "banked": banked.get("murphy"),
                                "equal": m["murphy"] == banked.get("murphy")}
        g1 = bool(checks) and all(c["equal"] for c in checks.values())
        _log(f"[G1] identity vs SC-1's banked artifact at tolerance 0.0 -> {g1}")
        for k, c in checks.items():
            if not c["equal"]:
                _log(f"     MISMATCH {k}: mine {c['mine']} banked {c['banked']}")

        g2 = bool(m and m["n"] >= SC1.KILL_MIN_PAIRS and de <= SC1.KILL_MAX_DISAGREE)
        _log(f"[G2] inherited kill: {m['n'] if m else 0} pairs (>= {SC1.KILL_MIN_PAIRS}), "
             f"double-entry {de:.4f} (<= {SC1.KILL_MAX_DISAGREE}) -> {g2}")

        g3 = bool(m and m["item_half_width"] is not None
                  and m["item_half_width"] >= m["naive_half_width"])
        _log(f"[G3] C4 at the item key: item half-width "
             f"{m['item_half_width'] if m else None} >= naive "
             f"{m['naive_half_width'] if m else None} -> {g3}")

        g4 = bool(m and m["n_clusters_item"] > m["n_clusters_file"])
        _log(f"[G4] clusters: item {m['n_clusters_item'] if m else 0} > file "
             f"{m['n_clusters_file'] if m else 0} -> {g4}")

        out = {
            "item": "SC-1b", "register": "PREREG_sc1b_cluster_by_item.md",
            "register_commit_alone": "329402d", "trial_booked": "58cf538",
            "domain": "infra", "trials": 1, "opens_market_data": False,
            "corpus_pinned_to": SC1_COMMIT,
            "why_pinned": ("register §0 and §6.2: SC-1b changes exactly ONE thing and may not "
                           "add a pair, so the pair set must be SC-1's. The record has grown "
                           "since -- four items' expectations landed the same day, three of "
                           "them this lane's own -- and running on today's tree would confound "
                           "MORE DATA with DIFFERENT CLUSTERING."),
            "corpus_files": len(files),
            "G1b_alignment": align, "G1_identity": {"checks": checks, "ok": g1},
            "G2_inherited_kill": {"n_pairs": m["n"] if m else 0,
                                  "double_entry_disagreement": de,
                                  "min_pairs": SC1.KILL_MIN_PAIRS,
                                  "max_disagree": SC1.KILL_MAX_DISAGREE, "ok": g2},
            "G3_c4_at_item_key": {"ok": g3,
                                  "note": ("an interval NARROWER than naive voids §1's bound; "
                                           "the register makes that SUSPECT and forces "
                                           "CANNOT-TELL regardless of half-width")},
            "G4_successor_differs": {"ok": g4},
            "measurement": m,
            "all_gating_pass": bool(g1 and g2 and g3 and g4 and align["aligned"]),
        }
        _w(os.path.join(args.out_dir, CTRL_JSON), out)
        _log(f"[controls] all_gating_pass={out['all_gating_pass']} -> {CTRL_JSON}")
        return 0 if out["all_gating_pass"] else 3


def verdict_for(m: Dict[str, object], g3_ok: bool) -> str:
    lo, hi = m["item_ci95"]
    if not g3_ok:
        return "CANNOT-TELL"                      # §4 G3: a suspect interval carries no verdict
    if lo > 0:
        return "OVERCONFIDENT-OPTIMISTIC"
    if hi < 0:
        return "OVERCONFIDENT-PESSIMISTIC"
    if m["item_half_width"] <= SC1.CALIBRATED_MAX_HALFWIDTH:
        return "CALIBRATED-IN-THE-LARGE"
    return "CANNOT-TELL"


def run_arms(args) -> int:
    ctrl_path = os.path.join(args.out_dir, CTRL_JSON)
    if not os.path.exists(ctrl_path):
        _log("[arms] REFUSED: controls artifact missing. Run --controls first.")
        return 2
    with open(ctrl_path, encoding="utf-8") as fh:
        ctrl = json.load(fh)
    if not ctrl.get("all_gating_pass"):
        _log("[arms] REFUSED: controls artifact does not pass its gates.")
        return 2
    _log("[arms] controls artifact read and passing -- proceeding")

    with tempfile.TemporaryDirectory() as td:
        materialise(SC1_COMMIT, td)
        pairs, align, _adjud, _rows = build(td)
        m = measure(pairs)
        pw = power_block(pairs, m)
    v = verdict_for(m, bool(ctrl["G3_c4_at_item_key"]["ok"]))

    # ---- the today's-corpus DIAGNOSTIC: no verdict, no bar, reported for robustness ----
    diag = None
    try:
        pairs_now, align_now, _a, _r = build(REPO)
        if align_now["aligned"] and pairs_now:
            mn = measure(pairs_now)
            diag = {"n": mn["n"], "gap": mn["gap"],
                    "item_ci95": mn["item_ci95"], "item_half_width": mn["item_half_width"],
                    "n_clusters_item": mn["n_clusters_item"],
                    "would_be_verdict": verdict_for(
                        mn, mn["item_half_width"] >= mn["naive_half_width"]),
                    "carries": "NO VERDICT",
                    "why": ("the corpus has GROWN since SC-1 ran. This shows whether the "
                            "conclusion survives that, and it is NOT the registered "
                            "comparison: it confounds more data with the clustering change, "
                            "and it includes expectations this lane wrote and scored the same "
                            "day. A DISAGREEMENT here is a caveat on generality, never a "
                            "second verdict.")}
        else:
            diag = {"carries": "NO VERDICT", "unavailable": True,
                    "aligned": align_now["aligned"]}
    except Exception as exc:                                   # a diagnostic may never break a run
        diag = {"carries": "NO VERDICT", "error": str(exc)[:200]}

    out = {
        "item": "SC-1b", "register": "PREREG_sc1b_cluster_by_item.md",
        "register_commit_alone": "329402d", "trial_booked": "58cf538",
        "domain": "infra", "trials": 1, "opens_market_data": False,
        "corpus_pinned_to": SC1_COMMIT,
        "verdict": v,
        "measurement": m, "power": pw,
        "the_three_rung_ladder": {
            "naive_half_width": m["naive_half_width"],
            "item_half_width": m["item_half_width"],
            "file_half_width_SC1s_own": m["file_half_width"],
            "bar": SC1.CALIBRATED_MAX_HALFWIDTH,
            "note": ("§1 bracketed this in advance between the naive floor and SC-1's "
                     "file-clustered value, with the 0.15 bar inside the bracket."),
        },
        "structural_bound_from_section_1": {
            "gap_is_fixed_by_the_pair_set": m["gap"],
            "ci_contains_zero": bool(m["item_ci95"][0] <= 0 <= m["item_ci95"][1]),
            "claim": ("both miscalibration verdicts were declared UNREACHABLE before running, "
                      "because SC-1's naive CI already contains zero and C4 requires the "
                      "cluster interval to be no narrower. This records whether that held."),
        },
        "todays_corpus_diagnostic": diag,
        "may_not_be_quoted_as": [
            "validation of any individual prior -- calibration-in-the-large is an aggregate "
            "property (SC-1 §231)",
            "a re-scoring of any item, or a reason to re-open one",
            "evidence about whether the priors are INFORMATIVE -- that is SC-1's separate "
            "Brier-skill finding and this register neither strengthens nor weakens it",
        ],
        "controls_read_from": CTRL_JSON,
    }
    _w(os.path.join(args.out_dir, ARMS_JSON), out)
    _log(f"\n[SC-1b] VERDICT {v}")
    _log(f"[SC-1b] gap {m['gap']:.6f}  item CI95 [{m['item_ci95'][0]:.6f}, "
         f"{m['item_ci95'][1]:.6f}]  half-width {m['item_half_width']:.6f} "
         f"vs bar {SC1.CALIBRATED_MAX_HALFWIDTH}")
    _log(f"[SC-1b] ladder: naive {m['naive_half_width']:.6f} | item "
         f"{m['item_half_width']:.6f} | file {m['file_half_width']:.6f}")
    _log(f"[SC-1b] clusters: item {m['n_clusters_item']} vs file {m['n_clusters_file']}")
    _log(f"[SC-1b] MDE 50% {pw['detection_threshold_50pct_power']:.6f}, 80% "
         f"{pw['mde_at_80pct_power']:.6f} (iid); design effect "
         f"{pw['realised_design_effect_item_vs_naive']}")
    _log(f"[SC-1b] -> {ARMS_JSON}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=DEFAULT_OUT)
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--arms", action="store_true")
    a = ap.parse_args()
    return run_arms(a) if a.arms else run_controls(a)


if __name__ == "__main__":
    raise SystemExit(main())
