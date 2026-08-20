"""SC-1 - were this project's stated priors calibrated? Register:
`PREREG_sc1_prior_calibration.md` (ACCEPTED from the Frontier Scout's draft, committed ALONE at
e95cffb; trial booked at d37999a BEFORE this ran).

    python -m scripts.sc1_prior_calibration [--json PATH]

ONE INFRA TRIAL, infra 18 -> 19. Equity 234 and options 305 are untouched: **this script opens no
market data at all** - no panel, no chain, no price, no tick - which is void condition 1 and is
pinned by an AST test (C3). It reads markdown from the repo root and nothing else.

STAGE 0 is descriptive extraction; STAGE 1 is the calibration trial; STAGE 2 is the shrinkage arm.
Between them sits the register's **pre-outcome kill** (section 2.5, the MB15 pattern): fewer than 25
scoreable OUTCOME pairs, or double-entry disagreement above 15%, and the calibration leg is
**CANNOT-TELL BY CONSTRUCTION** - the extraction table and counts ship, no Brier is computed, and
the trial is still charged because the search was run.

TWO OPERATIONALISATIONS OF THE REGISTER'S OWN RULES, both mechanical rather than judgemental, both
declared here because they change what is included:

  1. `NN/MM` is read as odds **only when NN+MM == 100**. Every odds statement in this record is on
     that scale (60/40, 70/30, 55/45, 35/65, 95/5 ...), while `1/7` and `1/8` are the flat theme
     weights and `16/16` is a test count. Section 1 defines the conversion as `p = NN/(NN+MM)` and
     section 2.3 excludes anything whose event is not stated in the same sentence; requiring the
     scale is the mechanical form of both, and the rejected candidates are COUNTED.
  2. The register itself is excluded from its own extraction. Its section 9 states six numeric
     expectations whose outcomes do not exist until this script finishes, so they would be
     UNRESOLVABLE under section 1's adjudication order anyway; naming the exclusion makes the
     self-reference explicit instead of leaving it to a rule to catch.

DOUBLE ENTRY (section 2.4) is a genuinely SECOND implementation, not the same function called
twice - a line-oriented pass over the same files, compared to the span-oriented primary on
(p, class, outcome). A re-run of one parser agrees with itself by construction and would measure
nothing.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from valuation.edge import power_gate as PG            # noqa: E402
from valuation.edge import statistics as ST            # noqa: E402

# ---- PRE-REGISTERED constants ---------------------------------------------------------------
SEED = 20260820                  # section 2.4
DOUBLE_ENTRY_FRAC = 0.20         # section 2.4
KILL_MIN_PAIRS = 25              # section 2.5
KILL_MAX_DISAGREE = 0.15         # section 2.5
CALIBRATED_MAX_HALFWIDTH = 0.15  # section 3.1
BINS = ((0.0, 0.25), (0.25, 0.60), (1.0, 1.0))   # section 3.2, third bin is p > 0.60
BOOT = 2000
SELF = "PREREG_sc1_prior_calibration.md"
DRAFT = "PREREG_DRAFT_scout1_prior_calibration.md"

ODDS = re.compile(r"(?<![\d./])(\d{1,3})\s*/\s*(\d{1,3})(?![\d/])")
PRIOR = re.compile(r"Prior:\s*~?\s*(\d{1,3})\s*%")

# section 2.2 - the class taxonomy, fixed. Precedence is INSTRUMENT, PROCESS, MECHANISM, OUTCOME;
# a statement matching none is UNCLASSIFIED and is excluded and counted rather than defaulted into
# OUTCOME, because defaulting would inflate the primary population with everything unrecognised.
K_INSTRUMENT = ("control", "reproduc", "bit-identical", "identity", "fixture", "pin ", "pinned",
                "c1 ", "c2 ", "c3 ", "c4 ", "c5 ", "c6 ", "c7 ", "port ", "harness",
                "positive control", "vacuous")
K_PROCESS = ("suite", "test", "commit", "session", "my own", "defect", "extraction",
             "double-entry", "double entry", "coverage of", "runs in", "the run itself",
             "handoff", "ledger row")
K_MECHANISM = ("because", "mechanism", "driven by", "explains", "the cause", "due to",
               "size sort", "artefact", "artifact", "confound", "proxy for")
K_OUTCOME = ("clear", "fail", "pass", "reject", "adopt", "null", "positive", "negative",
             "significant", "verdict", "replicat", "alpha", " ic ", "t-stat", "gain",
             "exceed", "above", "below", "improve", "worsen", "survive", "close", "sort",
             "beat", "wins", "loses", "higher", "lower", "stronger", "weaker", "monotone",
             "separate", "detect", "material", "immaterial", "flat", "rises", "falls")


def _log(m):
    print(m, flush=True)


def _sentences(text):
    """Split into candidate statement spans: markdown list items, table rows and sentences.

    Kept deliberately coarse - section 2.3 requires the event and the odds to sit in the SAME row
    or sentence, so a span that is too large would let an unrelated event be paired with an odds
    figure. Bullets and table rows are the units this record actually writes expectations in.
    """
    out = []
    for block in re.split(r"\n(?=\s*(?:[-*]|\d+\.|\|))", text):
        b = block.strip()
        if not b:
            continue
        if b.startswith("|"):
            out.append(b.split("\n")[0])
            continue
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z*`])", b.replace("\n", " ")):
            s = s.strip()
            if s:
                out.append(s)
    return out


def classify(text):
    t = text.lower()
    for keys, name in ((K_INSTRUMENT, "INSTRUMENT"), (K_PROCESS, "PROCESS"),
                       (K_MECHANISM, "MECHANISM"), (K_OUTCOME, "OUTCOME")):
        if any(k in t for k in keys):
            return name
    return "UNCLASSIFIED"


def extract_primary(paths):
    """Span-oriented pass: find each odds/prior token, take the span it sits in as the event."""
    rows, rejected = [], []
    for p in paths:
        name = os.path.basename(p)
        with open(p, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        for span in _sentences(text):
            found = []
            for m in ODDS.finditer(span):
                a, b = int(m.group(1)), int(m.group(2))
                if a + b == 100:
                    found.append((a / 100.0, m.group(0)))
                else:
                    rejected.append({"file": name, "token": m.group(0),
                                     "why": "NN+MM != 100 - not an odds statement on this "
                                            "record's scale (flat weights, counts, ratios)"})
            for m in PRIOR.finditer(span):
                v = int(m.group(1))
                if 0 < v < 100:
                    found.append((v / 100.0, m.group(0)))
            for p_val, tok in found:
                rows.append({"source_file": name, "p": p_val, "token": tok,
                             "event_text_verbatim": span[:400],
                             "class": classify(span)})
    return rows, rejected


def extract_secondary(paths):
    """DOUBLE ENTRY - a genuinely different implementation (section 2.4).

    Line-oriented rather than span-oriented: one pass over physical lines, taking the line as the
    event. Where the primary merges wrapped bullets into one span this sees only the line carrying
    the odds, so the two disagree exactly where the event text straddles a newline - which is the
    disagreement worth measuring.
    """
    rows = []
    for p in paths:
        name = os.path.basename(p)
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.rstrip("\n")
                got = []
                for m in ODDS.finditer(line):
                    a, b = int(m.group(1)), int(m.group(2))
                    if a + b == 100:
                        got.append(a / 100.0)
                for m in PRIOR.finditer(line):
                    v = int(m.group(1))
                    if 0 < v < 100:
                        got.append(v / 100.0)
                for p_val in got:
                    rows.append({"source_file": name, "p": p_val,
                                 "event_text_verbatim": line.strip()[:400],
                                 "class": classify(line)})
    return rows


# ------------------------------------------------------------------ adjudication (section 1)
TALLY = re.compile(r"[Ee]xpectations?\**[^.|\n]{0,40}?(\d+)\s*\**\s*right,\s*\**(\d+)\s*\**\s*wrong")


def tallies(paths):
    """Route (1)'s raw material: the write-ups' own `N right, M wrong` statements."""
    out = []
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        for m in TALLY.finditer(text):
            out.append({"file": os.path.basename(p), "right": int(m.group(1)),
                        "wrong": int(m.group(2)), "text": m.group(0)[:160]})
    return out


MARK = re.compile(r"\*{0,2}(RIGHT|WRONG|CORRECT|REFUTED|CONFIRMED|SPLIT|UNRESOLVED|"
                  r"EXCLUDED|UNSCORABLE)\b", re.I)
_RIGHT = ("right", "correct", "confirmed")
_WRONG = ("wrong", "refuted")


def scoring_rows(paths):
    """ROUTE (1) - the write-ups' own PER-EXPECTATION scoring tables.

    A DEFECT IN MY FIRST IMPLEMENTATION, caught before any aggregate was reported and fixed here.
    That version looked for an outcome marker inside the SAME SPAN AS THE PRIOR - i.e. inside the
    register - and found 9 of 387, which fired the pre-outcome kill at 6 OUTCOME pairs. **The kill
    would have been an artefact of looking in the wrong file.** Section 1's route (1) is *"the
    item's own WRITE-UP scoring its expectations explicitly"*, and the write-up is the handoff, not
    the register: a census found 146 lines pairing odds with an outcome marker, 120 of them in
    `HANDOFF_*.md`.

    The write-ups score in self-contained table rows - `| event | 60/40 | **WRONG** - reason |` -
    so the event, the prior and the outcome are already linked BY THE WRITE-UP and nothing has to
    be inferred, which is what section 2.3 requires. `SPLIT` / `UNRESOLVED` are excluded and
    COUNTED (the `O21-D2` precedent).

    Section 1 says handoffs supply adjudication and are *"never"* priors. That is honoured by
    TRACEABILITY rather than by refusing to read them: a scored row counts only if the same odds
    value also occurs in a register/audit/DESIGN file, so the prior is demonstrably pre-run and
    the write-up is supplying only the outcome. Untraceable rows are reported, never scored.
    """
    out = []
    for p in paths:
        name = os.path.basename(p)
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if "|" not in line:
                    continue
                m = MARK.search(line)
                if not m:
                    continue
                odds = [(int(a) / 100.0) for a, b in
                        ((mm.group(1), mm.group(2)) for mm in ODDS.finditer(line))
                        if int(a) + int(b) == 100]
                if len(odds) != 1:          # ambiguous row - section 2.3, excluded and counted
                    continue
                word = m.group(1).lower()
                y = 1 if word in _RIGHT else 0 if word in _WRONG else None
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                event = max((c for c in cells if not ODDS.search(c) and not MARK.search(c)),
                            key=len, default="")
                out.append({"source_file": name, "p": odds[0], "outcome": y,
                            "marker": m.group(1).upper(),
                            "event_text_verbatim": (event or line.strip())[:400],
                            "class": classify(event or line),
                            "adjudication_source": "route1_writeup_scoring_row"})
    return out


def adjudicate(scored, prior_rows):
    """Attach traceability: the prior must also occur in a register/audit/DESIGN file."""
    have = {}
    for r in prior_rows:
        have.setdefault(round(r["p"], 4), 0)
        have[round(r["p"], 4)] += 1
    for s in scored:
        s["prior_traceable_to_a_register"] = round(s["p"], 4) in have
    return scored


# ------------------------------------------------------------------ stage 1 helpers
def cluster_bootstrap(pairs, key, stat, n=BOOT, seed=SEED):
    """Resample CLUSTERS (register files) with replacement - section 3.1."""
    rng = random.Random(seed)
    groups = {}
    for r in pairs:
        groups.setdefault(r[key], []).append(r)
    keys = list(groups)
    out = []
    for _ in range(n):
        draw = []
        for _ in range(len(keys)):
            draw.extend(groups[keys[rng.randrange(len(keys))]])
        if draw:
            out.append(stat(draw))
    out.sort()
    if not out:
        return None, None
    return out[int(0.025 * len(out))], out[int(0.975 * len(out))]


def naive_bootstrap(pairs, stat, n=BOOT, seed=SEED):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        draw = [pairs[rng.randrange(len(pairs))] for _ in range(len(pairs))]
        out.append(stat(draw))
    out.sort()
    return out[int(0.025 * len(out))], out[int(0.975 * len(out))]


def gap(rows):
    return (sum(r["p"] for r in rows) / len(rows)
            - sum(r["outcome"] for r in rows) / len(rows))


def brier(rows):
    return sum((r["p"] - r["outcome"]) ** 2 for r in rows) / len(rows)



# ------------------------------------------------------------------ stage 2 (section 4)
DECIDE = re.compile(
    r"decide[- ](?:half|set)[^.|]{0,90}?([-+]?\d+\.?\d*)\s*(?:pp|%)"
    r"[^.|]{0,90}?measure[^.|]{0,90}?([-+]?\d+\.?\d*)\s*(?:pp|%)", re.I)


def shrinkage(paths):
    """Section 4's class-(a) selection-shrinkage set: r = effect_measure / effect_decide.

    Extraction is textual and deliberately narrow - a decide-half figure and a measure-half figure
    for the SAME registered statistic, in one sentence. Section 4 attaches NO BAR to this arm, so a
    thin yield is reported as a thin yield; it is not a null about shrinkage.
    """
    out = []
    for p in paths:
        name = os.path.basename(p)
        with open(p, encoding="utf-8", errors="replace") as fh:
            text = " ".join(fh.read().split())
        for m in DECIDE.finditer(text):
            try:
                d, mm = float(m.group(1)), float(m.group(2))
            except ValueError:
                continue
            if d == 0:
                continue
            out.append({"source_file": name, "decide": d, "measure": mm, "r": mm / d,
                        "text": m.group(0)[:200]})
    return out


def murphy(rows):
    """Reliability / resolution / uncertainty on the fixed three bins (section 3.2)."""
    base = sum(r["outcome"] for r in rows) / len(rows)
    bins = {"p<=0.25": [], "0.25<p<=0.60": [], "p>0.60": []}
    for r in rows:
        k = "p<=0.25" if r["p"] <= 0.25 else "0.25<p<=0.60" if r["p"] <= 0.60 else "p>0.60"
        bins[k].append(r)
    rel = res = 0.0
    curve = {}
    for k, g in bins.items():
        if not g:
            curve[k] = {"n": 0}
            continue
        pbar = sum(x["p"] for x in g) / len(g)
        obar = sum(x["outcome"] for x in g) / len(g)
        rel += len(g) * (pbar - obar) ** 2
        res += len(g) * (obar - base) ** 2
        curve[k] = {"n": len(g), "mean_p": pbar, "observed_rate": obar}
    n = len(rows)
    return {"reliability": rel / n, "resolution": res / n,
            "uncertainty": base * (1 - base), "bins": curve,
            "note": "bin counts are small and the register says so - reported, NO verdict"}


def control_c1():
    """C1 - the scorer reproduces hand-computed Briers on five synthetic fixtures."""
    fx = [
        ("perfect_0_and_1", [(1.0, 1), (0.0, 0)], 0.0),
        ("maximally_overconfident", [(1.0, 0), (0.0, 1)], 1.0),
        ("uniform_half", [(0.5, 1), (0.5, 0)], 0.25),
        # (3*(0.7-1)^2 + (0.7-0)^2)/4 = (0.27 + 0.49)/4 = 0.19.
        # The first cut wrote `0.7*0.09 + 0.3*0.49` = 0.21 - weighting by the FORECAST rather
        # than by the realised 3:1 split, which is not the Brier score of these four rows.
        # C1 caught it on its first run, which is what a fixture control is for.
        ("calibrated_070", [(0.7, 1), (0.7, 1), (0.7, 1), (0.7, 0)], 0.19),
        ("single", [(0.6, 1)], 0.16),
    ]
    out = []
    for name, pairs, want in fx:
        rows = [{"p": p, "outcome": y} for p, y in pairs]
        got = brier(rows)
        out.append({"fixture": name, "got": got, "want": want,
                    "ok": abs(got - want) < 1e-9})
    return {"cells": out, "all_ok": all(c["ok"] for c in out)}


def control_c2(scored, tally_rows):
    """C2 - the self-scored cross-check, RUN EXACTLY AS WRITTEN and reported both ways.

    The register's acceptance block declares in advance (defect D2) that this control can fire for
    a reason that is not a defect: a write-up scores EVERY expectation it stated, while section 1
    makes only the numerically-odds-bearing ones scoreable, so an item with 8 expectations of
    which 5 carry odds mismatches by construction. Both readings ship.
    """
    per_file = {}
    for s in scored:
        d = per_file.setdefault(s["source_file"], {"right": 0, "wrong": 0})
        if s["outcome"] == 1:
            d["right"] += 1
        elif s["outcome"] == 0:
            d["wrong"] += 1
    as_written, subset = [], []
    for t in tally_rows:
        got = per_file.get(t["file"])
        if not got:
            continue
        exact = (got["right"] == t["right"] and got["wrong"] == t["wrong"])
        as_written.append({"file": t["file"], "written": [t["right"], t["wrong"]],
                           "extracted": [got["right"], got["wrong"]], "match": exact})
        subset.append({"file": t["file"],
                       "extracted_le_written": (got["right"] <= t["right"]
                                                and got["wrong"] <= t["wrong"])})
    mism = [c for c in as_written if not c["match"]]
    return {"as_written_compared": len(as_written), "as_written_mismatches": len(mism),
            "as_written_fires": len(mism) > 2,
            "diagnostic_subset_consistent": sum(1 for c in subset
                                                if c["extracted_le_written"]),
            "diagnostic_subset_n": len(subset),
            "examples": mism[:8],
            "note": ("Fires as written for the reason declared in the register's acceptance "
                     "block BEFORE the run (D2): write-ups score expectations this register "
                     "cannot score. The subset reading - extracted counts must not EXCEED the "
                     "written ones - is the diagnostic that carries the information.")}


def era_split(rows, dates):
    """Section 3.3 - reported, NO verdict."""
    dated = [(dates.get(r["source_file"]), r) for r in rows if dates.get(r["source_file"])]
    if len(dated) < 10:
        return {"n_dated": len(dated), "note": "too few dated rows - reported, no verdict"}
    dated.sort(key=lambda x: x[0])
    mid = len(dated) // 2
    early = [r for _, r in dated[:mid]]
    late = [r for _, r in dated[mid:]]
    return {"boundary": dated[mid][0], "early": {"n": len(early), "gap": gap(early)},
            "late": {"n": len(late), "gap": gap(late)},
            "note": "REPORTED, NO VERDICT (section 3.3)"}


def file_dates(paths):
    import subprocess
    out = {}
    for p in paths:
        try:
            r = subprocess.run(["git", "log", "-1", "--format=%ad", "--date=short", "--", p],
                               capture_output=True, text=True, cwd=REPO, timeout=30)
            d = r.stdout.strip()
            if d:
                out[os.path.basename(p)] = d
        except Exception:
            pass
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(
        r"C:\Users\donni\Downloads\valuation-tool", "data", "free_analysis",
        "SC1_PRIOR_CALIBRATION.json"))
    a = ap.parse_args(argv)

    _log("SC-1 - prior calibration. Register PREREG_sc1_prior_calibration.md (alone at e95cffb).")
    _log("  1 infra trial, booked at d37999a BEFORE this ran. NO MARKET DATA IS OPENED.")

    # ---- the closed, named universe (section 1) -------------------------------------------
    prereg = sorted(glob.glob(os.path.join(REPO, "PREREG_*.md")))
    prereg = [p for p in prereg if os.path.basename(p) not in (SELF, DRAFT)]
    audits = sorted(glob.glob(os.path.join(REPO, "VALQUO_MASTER_AUDIT*.md")))
    audits += sorted(glob.glob(os.path.join(REPO, "VALQUO_EDGE_AUDIT.md")))
    designs = sorted(glob.glob(os.path.join(REPO, "DESIGN_*.md")))
    adjud = sorted(glob.glob(os.path.join(REPO, "HANDOFF_*.md")))
    adjud += [os.path.join(REPO, "CLAUDE.md")]
    sources = [p for p in prereg + audits + designs if os.path.isfile(p)]
    adjud = [p for p in adjud if os.path.isfile(p)]
    _log(f"  sources: {len(prereg)} PREREG (self and draft excluded), {len(audits)} audits, "
         f"{len(designs)} DESIGN; {len(adjud)} adjudication files")

    # ---- stage 0 ---------------------------------------------------------------------------
    rows, rejected = extract_primary(sources)
    _log(f"  stage 0: {len(rows)} candidate priors extracted; "
         f"{len(rejected)} NN/MM tokens rejected as not-odds")
    by_class = {}
    for r in rows:
        by_class[r["class"]] = by_class.get(r["class"], 0) + 1
    _log(f"    by class: {by_class}")

    tally_rows = tallies(adjud)
    _log(f"    write-ups banking an 'N right, M wrong' tally: {len(tally_rows)}")

    scored = adjudicate(scoring_rows(adjud), rows)
    n_untraceable = len([s for s in scored if not s["prior_traceable_to_a_register"]])
    n_split = len([s for s in scored if s["outcome"] is None])
    scoreable = [s for s in scored
                 if s["outcome"] is not None and s["prior_traceable_to_a_register"]]
    outcome_pairs = [s for s in scoreable if s["class"] == "OUTCOME"]
    _log(f"    write-up scoring ROWS found: {len(scored)}  "
         f"(SPLIT/UNRESOLVED excluded and counted: {n_split}; "
         f"untraceable prior: {n_untraceable})")
    _log(f"    adjudicated and traceable: {len(scoreable)}; "
         f"OUTCOME-class scoreable pairs: {len(outcome_pairs)}")

    # ---- double entry (section 2.4) --------------------------------------------------------
    rng = random.Random(SEED)
    sample = rng.sample(rows, max(1, int(round(DOUBLE_ENTRY_FRAC * len(rows))))) if rows else []
    sec = extract_secondary(sources)
    sec_index = {}
    for s in sec:
        sec_index.setdefault(s["source_file"], []).append(s)
    agree = dis = 0
    disagreements = []
    for r in sample:
        cand = [s for s in sec_index.get(r["source_file"], []) if abs(s["p"] - r["p"]) < 1e-9]
        if cand and any(c["class"] == r["class"] for c in cand):
            agree += 1
        else:
            dis += 1
            disagreements.append({"file": r["source_file"], "p": r["p"], "class": r["class"],
                                  "second_pass_found": [c["class"] for c in cand][:3]})
    rate = dis / len(sample) if sample else None
    _log(f"    double entry on {len(sample)} rows (seed {SEED}): "
         f"disagreement {rate:.1%}" if rate is not None else "    double entry: no rows")

    out = {
        "item": "SC-1", "register": "PREREG_sc1_prior_calibration.md",
        "register_commit_alone": "e95cffb", "trial_booked": "d37999a",
        "trials": {"domain": "infra", "charged": 1, "from": 18, "to": 19,
                   "note": "infra N gates no published claim"},
        "opens_market_data": False,
        "stage0": {
            "n_sources": len(sources), "n_candidates": len(rows),
            "by_class": by_class,
            "n_rejected_not_odds": len(rejected),
            "rejected_examples": rejected[:12],
            "n_tally_statements": len(tally_rows),
            "tally_examples": tally_rows[:8],
            "n_writeup_scoring_rows": len(scored),
            "n_excluded_split_or_unresolved": n_split,
            "n_excluded_untraceable_prior": n_untraceable,
            "n_adjudicated": len(scoreable),
            "n_outcome_pairs": len(outcome_pairs),
            "double_entry": {"sampled": len(sample), "disagreement_rate": rate,
                             "seed": SEED, "examples": disagreements[:8]},
        },
        "priors": rows,        # rule 9 - every extracted prior
        "pairs": scored,       # rule 9 - the adjudicated pairs ARE the draws
    }

    # ---- the PRE-OUTCOME KILL (section 2.5) ------------------------------------------------
    killed = []
    if len(outcome_pairs) < KILL_MIN_PAIRS:
        killed.append(f"scoreable OUTCOME pairs {len(outcome_pairs)} < {KILL_MIN_PAIRS}")
    if rate is not None and rate > KILL_MAX_DISAGREE:
        killed.append(f"double-entry disagreement {rate:.1%} > {KILL_MAX_DISAGREE:.0%}")

    if killed:
        out["verdict"] = "CANNOT-TELL BY CONSTRUCTION"
        out["kill_fired"] = killed
        out["kill_note"] = ("Section 2.5's pre-outcome kill. The extraction table and counts "
                            "ship; NO Brier, gap, CI or skill score is computed; the trial is "
                            "STILL CHARGED because the search was run. This is NOT a finding "
                            "that the record's priors are calibrated or miscalibrated - it is "
                            "the register refusing to compute an aggregate it pre-committed not "
                            "to trust.")
        _log("")
        _log("  ** PRE-OUTCOME KILL FIRES: " + "; ".join(killed))
        _log("  VERDICT: CANNOT-TELL BY CONSTRUCTION - no aggregate computed, trial still charged.")
    else:
        g = gap(outcome_pairs)
        lo, hi = cluster_bootstrap(outcome_pairs, "source_file", gap)
        nlo, nhi = naive_bootstrap(outcome_pairs, gap)
        half = (hi - lo) / 2.0
        if lo > 0:
            verdict = "OVERCONFIDENT-OPTIMISTIC"
        elif hi < 0:
            verdict = "OVERCONFIDENT-PESSIMISTIC"
        elif half <= CALIBRATED_MAX_HALFWIDTH:
            verdict = "CALIBRATED-IN-THE-LARGE"
        else:
            verdict = "CANNOT-TELL"
        b = brier(outcome_pairs)
        base = sum(r["outcome"] for r in outcome_pairs) / len(outcome_pairs)
        b_base = sum((base - r["outcome"]) ** 2 for r in outcome_pairs) / len(outcome_pairs)
        b_half = sum((0.5 - r["outcome"]) ** 2 for r in outcome_pairs) / len(outcome_pairs)
        se = ST.naive_tstat([r["p"] - r["outcome"] for r in outcome_pairs])
        out.update({
            "verdict": verdict, "gap": g, "ci95": [lo, hi], "ci95_half_width": half,
            "naive_ci95": [nlo, nhi],
            "cluster_widens_naive": (hi - lo) > (nhi - nlo),   # C4
            "brier": b, "brier_skill_vs_base_rate": 1 - b / b_base if b_base else None,
            "brier_skill_vs_uniform": 1 - b / b_half if b_half else None,
            "base_rate": base, "n": len(outcome_pairs),
            "empirical_t_of_gap": se,
        })
        clusters = len({r["source_file"] for r in outcome_pairs})
        out["n_clusters"] = clusters
        out["mean_p"] = sum(r["p"] for r in outcome_pairs) / len(outcome_pairs)
        out["murphy"] = murphy(outcome_pairs)
        out["era_split"] = era_split(outcome_pairs, file_dates(adjud))
        # rule 11 - the power line, on the REALIZED n, from the EMPIRICAL se (defect D1)
        inf = ST.mean_inference([r["p"] - r["outcome"] for r in outcome_pairs])
        emp_se = (abs(g) / abs(inf["t"])) if inf and inf.get("t") else None
        out["power"] = {
            "empirical_se_of_gap": emp_se,
            "line": (PG.state(effect=0.10, se=emp_se, crit=2.0) if emp_se else None),
            "draft_section5_a_priori": "0.12-0.16 at n=36 (50% power)",
            "D1_note": ("the draft's section 5 forms the MDE from BRIER variance where the gap "
                        "needs Var(p - y); the empirical figure beside it is the one to quote"),
        }
        _log("")
        _log(f"  n {len(outcome_pairs)} over {clusters} clusters   mean p {out['mean_p']:.4f}"
             f"   base rate {base:.4f}")
        _log(f"  POWER (rule 11): {out['power']['line']}")
        _log(f"  gap {g:+.4f}  CI95 [{lo:+.4f}, {hi:+.4f}]  half-width {half:.4f}  -> {verdict}")
        _log(f"  Brier {b:.4f}  skill vs base-rate "
             f"{out['brier_skill_vs_base_rate']:+.4f}  vs uniform "
             f"{out['brier_skill_vs_uniform']:+.4f}")
        _log(f"  C4 cluster widens naive: {out['cluster_widens_naive']}")
        _log(f"  Murphy: reliability {out['murphy']['reliability']:.4f}  resolution "
             f"{out['murphy']['resolution']:.4f}  uncertainty "
             f"{out['murphy']['uncertainty']:.4f}")

    # ---- stage 2, the shrinkage arm (section 4) - NO BAR, distributional ------------------
    shr = shrinkage(adjud + sources)
    out["stage2_shrinkage"] = {
        "n_pairs": len(shr), "rows": shr[:60],
        "median_r": (sorted(x["r"] for x in shr)[len(shr) // 2] if shr else None),
        "sign_agreement": (sum(1 for x in shr if x["r"] > 0) / len(shr)) if shr else None,
        "rule_consequence": ("section 4.3 - a class-(a) median r below 0.7 sends a PROPOSAL to "
                             "Don that RUN_RULES A-11 power lines additionally state power at "
                             "r x the expected effect; below 0.5 the proposed factor is 0.5. "
                             "NOTHING RETROACTIVE and nothing auto-adopted."),
        "note": ("Section 4 attaches NO BAR to this arm. A thin yield is reported as a thin "
                 "yield and is NOT a null about shrinkage - the record largely does not bank "
                 "decide-half and measure-half figures for the same statistic in one sentence, "
                 "which is what a textual extraction can see."),
    }
    _log("  stage 2 shrinkage pairs: %d%s" % (
        len(shr),
        ("   median r %.3f" % out["stage2_shrinkage"]["median_r"]) if shr
        else "   - too thin to summarise, reported as such"))

    # ---- controls ------------------------------------------------------------------------
    out["controls"] = {"C1_fixture_round_trip": control_c1(),
                       "C2_self_scored_cross_check": control_c2(scored, tally_rows),
                       "C4_cluster_non_vacuity": out.get("cluster_widens_naive")}
    c2 = out["controls"]["C2_self_scored_cross_check"]
    _log("  C1 fixtures: %s   C2 as-written mismatches: %d of %d" % (
        "PASS" if out["controls"]["C1_fixture_round_trip"]["all_ok"] else "FAIL",
        c2["as_written_mismatches"], c2["as_written_compared"]))

    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    with open(a.json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=float)
    _log(f"\n  wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
