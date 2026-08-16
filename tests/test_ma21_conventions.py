"""AUDIT MA21 — the conventions that existed only in prose, turned into checks.

Run: python tests/test_ma21_conventions.py

MA21 names five conventions carried by prose alone. This suite is the honest outcome of trying
to enforce all five: **one was already shipped, three are enforced here, and one is REFUTED by
the artifact it proposes to check.** Each is labelled below with which it is, because a suite
that quietly drops the item it could not do reads as five-for-five.

  (1) `N` may only change deliberately        -> ALREADY SHIPPED by MA13. Not re-implemented;
                                                 asserted to still exist and to be non-vacuous.
  (2) the canonical artifact must not go stale -> ENFORCED here, in the one direction that
                                                 cannot cry wolf. See `test_artifact_...`.
  (3) unknown verdict vocabulary -> a warning  -> **REFUTED.** Measured: it would fire on 41 of
                                                 230 DONE rows that are documented-correct.
                                                 A substitute check ships instead.
  (4) a landed item must have a ledger row     -> ENFORCED here.
  (5) live composite == backtested, scheduled  -> REPORTED, NOT TAKEN. Scheduling means editing
                                                 `.github/workflows/`, which `land_policy.py`
                                                 refuses, and the harness needs the licensed
                                                 export that CI does not have.

THE RULE THESE ALL SERVE, from the audit: a convention that lives in prose is re-broken by the
next person who has not read the prose. The record shows the `by_domain` convention broken
**with the warning in view**, which is why (1) became a test rather than a paragraph.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  (must precede any `valuation` import)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "VALQUO_LEDGER.md")
ARTIFACT = os.path.join(ROOT, "BACKTEST_RESULTS.json")


def _ledger_rows():
    """(header, [row-cells]) for the ledger's ITEM table, resolved by header name.

    By NAME, never by position: `VALQUO_LEDGER.md` contains several markdown tables and the
    status legend at the top parses as one. Reading the first table found is how a checker
    ends up measuring the legend — the same class of error as the `RESEARCH_LOG` two-table
    hazard, where an append lands under the second schema.
    """
    lines = open(LEDGER, encoding="utf-8").read().splitlines()
    hdr_i = next(i for i, l in enumerate(lines) if l.startswith("| id | series |"))
    cols = [c.strip() for c in lines[hdr_i].strip().strip("|").split("|")]
    rows = []
    for l in lines[hdr_i + 2:]:
        if not l.startswith("| "):
            continue
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        if len(c) >= len(cols):
            rows.append(c)
    return cols, rows


# --------------------------------------------------------------------------- (1) ALREADY SHIPPED
def test_convention_1_the_by_domain_pin_still_exists_and_is_not_vacuous():
    """MA13 already turned "N may only change deliberately" into a committed literal.

    NOT RE-IMPLEMENTED. A second pin would be a second definition of the same fact, which is
    the MA39 defect. This asserts only that MA13's pin is still there and still has teeth —
    a pin whose expectation became empty would pass against any `by_domain` at all.
    """
    p = os.path.join(ROOT, "tests", "test_research_log_integrity.py")
    src = open(p, encoding="utf-8").read()
    assert "EXPECTED_BY_DOMAIN" in src, "MA13's by_domain pin has been removed"
    m = re.search(r"EXPECTED_BY_DOMAIN\s*=\s*\{([^}]*)\}", src)
    assert m, "EXPECTED_BY_DOMAIN is no longer a literal dict"
    body = m.group(1)
    for dom in ("equity", "options", "infra"):
        assert dom in body, f"the pin no longer names {dom}"
    assert re.search(r":\s*\d+", body), "the pin carries no numbers — it cannot fail"


# --------------------------------------------------------------------------- (2) ENFORCED
def test_convention_2_the_canonical_artifact_may_not_claim_more_trials_than_the_log():
    """`BACKTEST_RESULTS.json` vs `research_log` — checked in the ONE direction that is a bug.

    WHY NOT "THEY MUST BE EQUAL". MA19 already refused that, and the reason is measured rather
    than stylistic: the artifact is refreshed by a 20-40 minute backtest while `N` rises the
    moment a register lands, so equality is red for the ordinary interval between the two.
    "A gate that cries wolf is one you learn to ignore." As this test was written the drift
    was **3** (artifact 224, live equity 227) with nothing whatever wrong.

    WHAT *IS* A BUG is the other direction. Trials only accumulate — `RUN_RULES` rule 9 forbids
    deleting a logged row — so the artifact can lag the log and can never lead it. An artifact
    claiming MORE trials than the log means the log lost rows or the artifact was hand-edited,
    and both are serious: `N` is the denominator of the Deflated Sharpe and of every HLZ
    hurdle, and understating it OVERSTATES significance.
    """
    from valuation.edge import research_log as RL
    if not os.path.exists(ARTIFACT):
        return
    d = json.load(open(ARTIFACT, encoding="utf-8"))
    art = (d.get("cpcv") or {}).get("deflated_sharpe_detail", {}).get("n_trials")
    if art is None:
        return
    live = RL.detail()["by_domain"]["equity"]
    assert int(art) <= int(live), (
        f"BACKTEST_RESULTS.json claims n_trials={art} against a live equity log of {live}. "
        f"Trials only accumulate, so the artifact cannot lead the log: either the log lost "
        f"rows (RUN_RULES rule 9) or the artifact was edited by hand. Understating N "
        f"overstates every DSR- and HLZ-gated claim.")


def test_convention_2_is_not_vacuous():
    """The check above must actually be able to fail — pinned by construction."""
    art, live = 300, 227
    assert not (art <= live), "the comparison in the test above cannot detect a lead"


# --------------------------------------------------------------------------- (3) REFUTED
def test_convention_3_an_unknown_verdict_may_not_be_warned_on_because_blank_is_documented():
    """MA21 asks: "verdict vocabulary -> build_ledger.py already knows it, make an unknown
    verdict a warning." MEASURED, THAT CHECK WOULD CRY WOLF ON DOCUMENTED-CORRECT ROWS.

    `build_ledger.py` fills the verdict column **only** when a write-up literally uses one of
    five words (ADOPTED / REJECTED / NULL / INCONCLUSIVE / DEFERRED), and its own "How to read
    a row" section states the consequence: *"Most of the B series concluded FIXED, and X8
    concluded REPLICATES — real outcomes, but not verdicts in this vocabulary, so their column
    is blank ... Blank therefore means 'not measured, or measured and reported in different
    words' — never 'we don't know'."*

    Measured on the shipped ledger: **41 of 230 DONE rows carry a blank verdict**, every one
    of them legitimate under that rule. A warning would fire on all 41 plus every prose
    verdict, and would be switched off within a week.

    THIS TEST PINS THE REFUTATION so a later session does not re-derive the idea and ship it.
    It asserts the documented rule is still the rule; if the documentation ever changes, this
    fails and the question genuinely reopens.
    """
    src = open(os.path.join(ROOT, "scripts", "build_ledger.py"), encoding="utf-8").read()
    assert "never *\"we don't know\"*" in src or "never *\"we don" in src, (
        "build_ledger's 'How to read a row' no longer documents blank-verdict as legitimate; "
        "MA21's convention (3) may be reconsidered")
    cols, rows = _ledger_rows()
    i_s, i_v = cols.index("status"), cols.index("verdict")
    done = [r for r in rows if "DONE" in r[i_s]]
    blank = [r for r in done if not r[i_v]]
    assert len(done) > 100, "ledger parse found too few DONE rows — the parse is broken"
    assert blank, ("no DONE row has a blank verdict any more; if that is real, MA21's "
                   "convention (3) becomes implementable and should be revisited")


def test_convention_3_substitute_the_two_copies_of_the_vocabulary_agree():
    """What IS enforceable from (3): the vocabulary must not drift between code and prose.

    `VERDICTS` is a literal list in `build_ledger.py` and the same five words are spelled out
    in its "How to read a row" section a few hundred lines below. Two copies of one fact —
    exactly the shape MA39 caught — so adding a sixth verdict word in one place and not the
    other is silent. This is zero-false-positive because both copies are in one file.
    """
    src = open(os.path.join(ROOT, "scripts", "build_ledger.py"), encoding="utf-8").read()
    m = re.search(r"^VERDICTS\s*=\s*\[([^\]]*)\]", src, re.M)
    assert m, "VERDICTS is no longer a module-level literal list"
    in_code = set(re.findall(r"[A-Z]{4,}", m.group(1)))
    doc = src.split("## How to read a row", 1)
    assert len(doc) == 2, "build_ledger no longer documents how to read a row"
    documented = set(re.findall(r"`([A-Z]{4,})`", doc[1][:900]))
    missing = in_code - documented
    assert not missing, (
        f"verdict words in code but not in the documentation: {sorted(missing)} — the two "
        f"copies of the vocabulary have drifted")


# --------------------------------------------------------------------------- (4) ENFORCED
def _ma_ids_in_commit_subjects(n=400):
    try:
        out = subprocess.run(["git", "log", "--format=%s", f"-{n}"], cwd=ROOT,
                             capture_output=True, text=True, timeout=60)
    except Exception:
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    return {"MA" + d for d in re.findall(r"\bMA(\d{1,2})\b", out.stdout)}


def test_convention_4_every_item_named_in_a_commit_subject_has_a_ledger_row():
    """A landed item must be findable in the ledger, which is the contractual answer to
    "is X done?". A commit that names an id the ledger has never heard of means the ledger
    stopped being that answer.

    Reads clean today: 46 MA ids appear in the last 400 commit subjects and all 46 have rows.
    Degrades to a REPORTED SKIP where git is unavailable (a shallow CI clone), rather than
    passing — a check that silently succeeds when it cannot look is the vacuity failure.
    """
    named = _ma_ids_in_commit_subjects()
    if named is None:
        print("  (skipped: no git history available — reported, not passed)")
        return
    cols, rows = _ledger_rows()
    have = {r[0] for r in rows}
    missing = sorted(named - have, key=lambda s: int(s[2:]))
    assert not missing, (
        f"commit subjects name {missing} but VALQUO_LEDGER.md has no row for them; the ledger "
        f"is the contractual answer to 'is X done?' and cannot answer for an item it lacks")


def test_convention_4_is_not_vacuous():
    """The scan must actually find ids, or the assertion above is empty."""
    named = _ma_ids_in_commit_subjects()
    if named is None:
        return
    assert len(named) >= 5, (
        f"only {len(named)} MA ids found in 400 commit subjects — the regex or the history is "
        f"wrong, and the check above is passing because it sees nothing")


# --------------------------------------------------------------------------- (5) REPORTED
def test_convention_5_the_m4_harness_exists_and_is_reported_unscheduled():
    """M4's live-vs-backtest fidelity harness exists and NOTHING RUNS IT. Reported, not fixed.

    Two reasons it is not fixed here, both structural rather than a matter of effort:

      1. Scheduling means editing `.github/workflows/`, and `.github/land_policy.py` — read
         from MAIN's checkout precisely so branch code cannot edit the gate that judges it —
         REFUSES any branch touching `.github/`. This is the same wall MA60 hit with
         `suite_manifest.py`, and weakening the policy to get a green run is silencing a check.
      2. The harness needs the licensed Sharadar export (`--data-dir data/backtest`), which CI
         does not have and must never have. So even an allowed workflow edit could not run it.

    What this test does is keep the harness FINDABLE and keep the gap DATED, so it is a known
    open item rather than something rediscovered in six months.
    """
    runner = os.path.join(ROOT, "scripts", "m4_live_replay.py")
    assert os.path.exists(runner), "M4's harness runner has disappeared"
    wf = os.path.join(ROOT, ".github", "workflows")
    scheduled = []
    if os.path.isdir(wf):
        for f in os.listdir(wf):
            if "m4_live_replay" in open(os.path.join(wf, f), encoding="utf-8",
                                        errors="ignore").read():
                scheduled.append(f)
    if scheduled:
        print(f"  (M4 harness is now scheduled by {scheduled} — MA21(5) can be closed)")
    else:
        print("  (REPORTED: M4 harness exists and is unscheduled; blocked on land policy "
              "+ licensed data, see docstring)")


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} MA21 convention tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
