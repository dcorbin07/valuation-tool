"""U6's coverage correction, pinned.  [PREREG_u6_overwrite_leg.md PART A]

ZERO TRIALS — this pins a CORRECTION, not a test. What has to be protected is the thing that
makes the correction checkable rather than merely different from the ledger:

  * the decile is the SHIPPED one (argsort(-composite) split into ten), so "top decile" here is
    the same object every published top-decile figure describes;
  * the two reproduction controls are asserted, because without them a 5x coverage difference
    is indistinguishable from measuring a different set;
  * and the FINDING THAT REFUTES THE RE-OPEN'S OWN PREMISE is pinned so a later reader cannot
    quietly restore the wrong story: holdings are NOT better covered than entries.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("VALQUO_DATA_ROOT", r"C:\Users\donni\Downloads\valuation-tool\data")
ART = os.path.join(DATA, "free_analysis", "U6_OVERWRITE_COVERAGE.json")

# The two numbers this correction must reproduce to be comparable with the ledger at all.
LEDGER_ENTRY_EVENTS = 7132          # VALQUO_LEDGER.md, the U6 row
PUBLISHED_DECILE_ROWS = 11426       # S10, and V6-B's C7 independently


def _art():
    if not os.path.exists(ART):
        return None
    with open(ART) as fh:
        return json.load(fh)


def test_the_artifact_exists_and_declares_itself_zero_trials():
    a = _art()
    if a is None:
        print("   (skipped: artifact not built in this checkout)")
        return
    assert "ZERO TRIALS" in a["what_this_is"]


def test_entry_events_reproduce_the_ledgers_own_count():
    """Without this the 5x coverage difference could be a different set, not a correction."""
    a = _art()
    if a is None:
        print("   (skipped)")
        return
    got = a["all_dates_like_for_like"]["entries_total"]
    assert abs(got - LEDGER_ENTRY_EVENTS) / LEDGER_ENTRY_EVENTS < 0.01, (
        "entry events %d vs the ledger's %d — this is not the same object" %
        (got, LEDGER_ENTRY_EVENTS))


def test_decile_membership_reproduces_the_published_count_exactly():
    """S10 and V6-B's C7 both report 11,426 top-decile rows over 69 dates. Reproducing it
    EXACTLY is what establishes that this uses the shipped decile convention."""
    a = _art()
    if a is None:
        print("   (skipped)")
        return
    assert a["all_dates_like_for_like"]["holdings_total"] == PUBLISHED_DECILE_ROWS


def test_the_reopens_own_premise_is_refuted_and_stays_refuted():
    """THE LOAD-BEARING ASSERTION. U6 was to be re-opened because the blocker measured ENTRIES
    while an overwrite is written on HOLDINGS. Measured, holdings are NOT better covered — so
    the correction is the UNIVERSE, not the leg. If this ever flips, the write-up is wrong."""
    a = _art()
    if a is None:
        print("   (skipped)")
        return
    lfl = a["all_dates_like_for_like"]
    ent = lfl["entries_any_chain"] / lfl["entries_total"]
    hold = lfl["holdings_any_chain"] / lfl["holdings_total"]
    assert hold < ent, (
        "holdings (%.4f) are better covered than entries (%.4f) — the entries-vs-holdings "
        "story would then be right after all and the write-up must change" % (hold, ent))
    assert hold > 0.05, "holdings coverage collapsed to near zero; re-check the partition"


def test_the_correction_is_material_and_in_the_stated_direction():
    """1.81% -> ~9% on entries. The claim is a ~5x rise, matching the ~4.8x universe ratio."""
    a = _art()
    if a is None:
        print("   (skipped)")
        return
    share = a["all_dates_like_for_like"]["share_any_chain"]
    assert share > 0.05, "the corrected entry coverage is not materially above the ledger's 1.81%%"
    assert 3.0 < (share / 0.0181) < 8.0, (
        "the correction ratio %.2fx is outside the range the universe ratio explains"
        % (share / 0.0181))


def test_no_covered_date_has_zero_optionable_holdings():
    """The specific thing the ledger row asserts ('ZERO covered entries on 18 of 68 dates') is
    what makes the leg look unbuildable. On holdings it is false on every covered date."""
    a = _art()
    if a is None:
        print("   (skipped)")
        return
    assert a["on_covered_dates"]["covered_dates_with_zero_any_holdings"] == 0
    assert a["on_covered_dates"]["covered_dates_with_zero_liquid_holdings"] == 0


def test_the_bound_travels_with_the_unblocking():
    """The overwrite can only ever touch a small share of the book, and the register says that
    matters more than the unblocking. Pinned so the unblocking cannot be quoted alone."""
    a = _art()
    if a is None:
        print("   (skipped)")
        return
    share = a["on_covered_dates"]["share_of_decile_slots_any_chain"]
    assert 0.0 < share < 0.30, (
        "share of decile slots that are optionable is %.4f — if this ever exceeds ~30%% the "
        "'bounded at ~7-13%% of the book' sentence in the write-up is stale" % share)


def test_the_script_uses_the_shipped_composite_and_does_not_retype_weights():
    src = open(os.path.join(REPO, "scripts", "u6_overwrite_coverage.py"), encoding="utf-8").read()
    assert "composite_from_frame" in src, "the shipped composite is not used"
    assert "from scripts.term_structure import DEPLOYED" in src, (
        "the deployed weight vector is not imported — a re-typed copy would drift")
    assert "0.125" not in src, "the weight vector is hard-coded here"


if __name__ == "__main__":
    fails = 0
    names = [n for n in sorted(globals()) if n.startswith("test_")]
    for name in names:
        try:
            globals()[name]()
            print("PASS", name)
        except Exception as e:                                        # noqa: BLE001
            fails += 1
            print("FAIL", name, "->", repr(e))
    print("%d passed, %d failed" % (len(names) - fails, fails))
    sys.exit(1 if fails else 0)
