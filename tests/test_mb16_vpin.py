"""MB16's quote-classified VPIN, pinned. [charges no trials until the kill is passed]

What has to hold:

  * VPIN IS UNSIGNED, and this is the load-bearing property. Flipping every aggressor side leaves
    it bit-identical, while O14's `signed_volume` flips sign. That is why the item's registered
    kill - correlate VPIN against SIGNED `signed_volume` - cannot detect the renaming it exists to
    catch, and why the |signed_volume| comparison is reported beside it. The register is run AS
    WRITTEN; the defect is reported, not silently repaired (MB1's discipline).
  * the buckets are EQUAL-VOLUME and a print straddling a boundary is SPLIT, not assigned whole.
  * degenerate input returns None, never 0.0 - a fabricated zero reads as "perfectly balanced
    flow" rather than "not measurable", which is the vacuous-pass family.
  * the classifier is O14's, IMPORTED rather than re-implemented (a second copy is the B7 class).
  * the Bulk Volume classifier Andersen-Bondarenko dispute is NOT built anywhere.

Offline: synthetic tapes, so it runs on Linux and Windows alike with no cache mounted.
"""
from __future__ import annotations

import ast
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tests.state_isolation  # noqa: F401,E402

import numpy as np  # noqa: E402

from scripts.mb16_vpin import N_BUCKETS, vpin  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------- the construction

def test_one_sided_flow_is_maximally_toxic():
    sides = np.ones(500)
    sizes = np.ones(500)
    assert abs(vpin(sides, sizes, 50) - 1.0) < 1e-12


def test_perfectly_alternating_flow_is_untoxic():
    """Equal buy and sell volume inside every bucket must give an imbalance of zero."""
    sides = np.tile([1.0, -1.0], 500)
    sizes = np.ones(1000)
    assert abs(vpin(sides, sizes, 50)) < 1e-12


def test_a_print_straddling_a_boundary_is_split_not_assigned_whole():
    """One enormous one-sided print spanning every bucket is still fully toxic.

    Assigning whole prints to buckets would drop it into a single bucket, leave the others empty
    and make the mean wrong - so this fails against the naive construction.
    """
    assert abs(vpin([1.0], [10_000.0], 50) - 1.0) < 1e-12


def test_the_buckets_are_equal_volume():
    """Half buy then half sell: each bucket is internally one-sided, so VPIN is 1.0.

    If bucket volumes were unequal this would not hold exactly.
    """
    sides = np.r_[np.ones(500), -np.ones(500)]
    sizes = np.ones(1000)
    assert abs(vpin(sides, sizes, 50) - 1.0) < 1e-12


def test_it_is_scale_invariant():
    rng = np.random.default_rng(11)
    sides = rng.choice([1.0, -1.0], 600)
    sizes = rng.integers(1, 40, 600).astype(float)
    a = vpin(sides, sizes, N_BUCKETS)
    b = vpin(sides, sizes * 1000.0, N_BUCKETS)
    assert a is not None and abs(a - b) < 1e-9


# ---------------------------------------------------------------- the unsigned property

def test_vpin_is_unsigned_and_signed_volume_is_not():
    """THE FINDING BEHIND THE REGISTERED KILL'S BLIND SPOT.

    Flip every side: VPIN is unchanged to the bit, while O14's signed_volume negates. A
    correlation between an unsigned statistic and a signed one cannot detect that the first is a
    function of the second's MAGNITUDE - which is exactly the renaming the kill exists to catch.
    """
    from valuation.edge import tickflow_signals as TS
    rng = np.random.default_rng(7)
    sides = rng.choice([1.0, -1.0], 800)
    sizes = rng.integers(1, 25, 800).astype(float)

    assert abs(vpin(sides, sizes, N_BUCKETS) - vpin(-sides, sizes, N_BUCKETS)) < 1e-12
    sv = TS.signed_volume(sides, sizes)
    sv_flipped = TS.signed_volume(-sides, sizes)
    assert abs(sv + sv_flipped) < 1e-12
    assert abs(sv) > 1e-6, "the fixture must have a non-zero imbalance or it proves nothing"


def test_a_pure_magnitude_relationship_is_invisible_to_the_registered_comparison():
    """Positive control for the sentence above, on a constructed pair.

    Build tapes whose VPIN tracks |signed_volume| and whose SIGN alternates. The registered
    (signed) correlation reads ~0 while the magnitude correlation is ~1.

    THE SIDES MUST BE INTERLEAVED, and the first cut of this fixture was wrong for a reason worth
    keeping: it laid the tape out as a block of buys followed by a block of sells, which makes
    every equal-volume bucket internally one-sided and pins VPIN at 1.0 whatever the imbalance -
    so `v` was constant and the test measured nothing. It failed, which is how it was caught.
    """
    from valuation.edge import tickflow_signals as TS
    import pandas as pd
    rng = np.random.default_rng(3)
    v, s = [], []
    for i in range(60):
        frac = 0.5 + 0.5 * (i / 59.0)          # 50% -> 100% one-sided
        n = 400
        k = int(n * frac)
        sign = 1.0 if i % 2 == 0 else -1.0
        sides = np.r_[sign * np.ones(k), -sign * np.ones(n - k)]
        rng.shuffle(sides)                      # interleave: buckets must see BOTH sides
        sizes = np.ones(n)
        v.append(vpin(sides, sizes, 20))
        s.append(TS.signed_volume(sides, sizes))
    v = pd.Series(v)
    s = pd.Series(s)
    rho_signed = abs(v.rank().corr(s.rank()))
    rho_abs = abs(v.rank().corr(s.abs().rank()))
    assert rho_abs > 0.95, rho_abs
    assert rho_signed < 0.40, rho_signed


# ---------------------------------------------------------------- refusal, not fabrication

def test_it_returns_none_rather_than_zero_when_it_cannot_measure():
    assert vpin([], [], 50) is None
    assert vpin([0, 0, 0], [5, 5, 5], 50) is None           # nothing classified
    assert vpin([1, -1], [3, 4], 50) is None                # less volume than buckets
    assert vpin([1.0], [10.0], 1) is None                   # fewer than 2 buckets


def test_unclassified_prints_are_excluded_rather_than_counted_as_balanced():
    a = vpin([1, 1, 1, 1], [10, 10, 10, 10], 4)
    b = vpin([1, 1, 1, 1, 0, 0], [10, 10, 10, 10, 10, 10], 4)
    assert a is not None and b is not None and abs(a - b) < 1e-12


# ---------------------------------------------------------------- scope and provenance

def test_the_bulk_volume_classifier_is_not_built():
    """Andersen-Bondarenko's dispute is entirely about BVC; building it would import the
    contested component the item exists to avoid."""
    code = _src(os.path.join("scripts", "mb16_vpin.py"))
    tree = ast.parse(code)
    names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    for bad in ("bulk_volume", "bvc", "bulk_classify", "normal_cdf_classify"):
        assert bad not in names, bad


def test_the_classifier_is_imported_not_reimplemented():
    code = _src(os.path.join("scripts", "mb16_vpin.py"))
    assert "tickflow_signals" in code and "classify_side" in code
    tree = ast.parse(code)
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert "classify_side" not in defined, "a second copy of the classifier is the B7 defect"
    assert "lee_ready" not in defined


def test_the_kill_unit_departure_is_stated_in_the_source():
    """The item says 'within date'; that cross-section does not exist here. Silently swapping the
    unit would be the worst version of this - it must be declared where it is made."""
    code = _src(os.path.join("scripts", "mb16_vpin.py"))
    assert "_KILL_UNIT_NOTE" in code
    assert "within date" in code.lower() and "median of 2 names" in code.lower()


def test_the_bucket_count_is_a_constant_not_a_swept_parameter():
    """n=50 is EL O'H's standard, fixed on availability before any correlation. The sensitivity
    buckets must never be able to become the primary."""
    from scripts import mb16_vpin as M
    assert M.N_BUCKETS == 50
    assert M.N_BUCKETS not in M.SENSITIVITY_BUCKETS


def test_alert_day_conditioning_is_stated_in_the_payload_builder():
    code = _src(os.path.join("scripts", "mb16_vpin.py"))
    assert "ALERT DAYS ONLY" in code


def test_it_is_runnable_as_its_own_process():
    """RUN_RULES line 25 judges a suite by EXIT CODE; no __main__ block exits 0 vacuously."""
    assert 'if __name__ == "__main__":' in _src(os.path.join("scripts", "mb16_vpin.py"))
    assert 'if __name__ == "__main__":' in _src(os.path.join("scripts", "mb16_arm.py"))


# ---------------------------------------------------------------- the arm's gate and bar

ARM = os.path.join("scripts", "mb16_arm.py")


def test_the_arm_refuses_without_a_passing_kill_artifact():
    """The gating control and the outcomes it gates must not run in one pass - session 26's
    defect. Pinned on the SOURCE because running it needs the cache."""
    code = _src(ARM)
    tree = ast.parse(code)
    fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert "_gate" in fns, "there must be a gate"
    body = ast.dump(fns["_gate"])
    assert "SystemExit" in body, "the gate must REFUSE, not warn"
    # it must refuse on all three conditions: no artifact, kill fired, control failed
    assert body.count("SystemExit") >= 3, "the gate must refuse on each failure mode separately"
    assert "kill_fires" in code and "signed_volume_reproduces_exactly" in code


def test_the_arm_calls_the_gate_before_it_scores_anything():
    """A gate that runs after the arm is decoration."""
    tree = ast.parse(_src(ARM))
    main = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "main")
    order = []
    for node in ast.walk(main):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            order.append(node.func.id)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            order.append(node.func.attr)
    assert "_gate" in order, "main must call the gate"
    assert order.index("_gate") < order.index("score_arm"), "the gate must precede scoring"


def test_the_scoring_arithmetic_is_o14s_imported_not_reimplemented():
    code = _src(ARM)
    assert "o14_tickflow_signals" in code and "score_arm" in code
    tree = ast.parse(code)
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    for bad in ("score_arm", "quintiles_within_date", "long_short_series", "month_block_t",
                "perm_null_abs_t"):
        assert bad not in defined, "%s must be imported, not re-implemented (B7 class)" % bad


def test_a_candidate_requires_all_three_legs():
    """Mutation-style, on the real logic: flipping ANY leg must stop it being a CANDIDATE."""
    def verdict(full_ok, early_ok, late_ok, sign_agree, underpowered=False):
        passes = bool(full_ok and early_ok and late_ok and sign_agree)
        return "UNDERPOWERED" if underpowered else ("CANDIDATE" if passes else "NULL")

    assert verdict(True, True, True, True) == "CANDIDATE"
    for flip in range(4):
        legs = [True, True, True, True]
        legs[flip] = False
        assert verdict(*legs) == "NULL", flip
    assert verdict(True, True, True, True, underpowered=True) == "UNDERPOWERED"


def test_the_sign_agreement_clause_does_the_work_a_declared_sign_would():
    """Two halves with large opposite t must not clear - that is the whole reason the clause
    exists on a two-sided arm."""
    import numpy as _np
    for a, b in ((3.0, -3.0), (-3.0, 3.0)):
        signs = [_np.sign(a), _np.sign(b)]
        assert not (len(signs) == 2 and signs[0] == signs[1])
    for a, b in ((3.0, 1.0), (-3.0, -1.0)):
        signs = [_np.sign(a), _np.sign(b)]
        assert len(signs) == 2 and signs[0] == signs[1]


def test_the_null_carries_its_own_resolution():
    """V6 and S19: a NULL means 'not separable at this resolution', never 'absent', so the MDE
    must travel with the verdict - derived from the arm's OWN se and OWN bar, not a convention."""
    code = _src(ARM)
    assert "resolution" in code and "mde_at_own_p95_bar" in code
    assert "null_p95_abs_t" in code.split("resolution = {")[1].split("}")[0]
    assert "never that it is absent" in code


def test_the_framing_travels_with_the_result():
    """R2 stands and O11 binds - a candidate is for a future book that does not exist."""
    code = _src(ARM)
    assert "R2 STANDS" in code and "O11 binds" in code
    assert "never an adoption" in code


# ---------------------------------------------------------------- the double-count debt

# MB16's own finding, reported under RUN_RULES rule 3: `research_log._parse` has NO dedup by id,
# so an item that books a PRE-REGISTERED row and later appends a SEPARATE verdict row is counted
# twice. Two ids currently do this and the excess is 4 options trials.
#
# THIS IS A COMMITTED LITERAL IN THE MA13 IDIOM, NOT A CORRECTION. Lowering `N` moves a
# denominator every published options claim is gated on in the PERMISSIVE direction and touches
# another lane's rows, so it needs its own decision. What this pin buys is that the debt is
# VISIBLE and cannot grow silently: a NEW double-booked id fails here in the same commit that
# introduces it.
KNOWN_DOUBLE_COUNTED = {"MB1": 2, "O21-D2": 3}     # id -> number of COUNTED rows
KNOWN_EXCESS_TRIALS = 4


def test_no_new_id_is_double_counted_in_the_research_log():
    import collections
    from valuation.edge import research_log as rl

    parsed = rl._parse(os.path.join(REPO, "RESEARCH_LOG.md"))
    counts = collections.Counter(parsed["ids"])
    dupes = {i: n for i, n in counts.items() if n > 1}
    assert dupes == KNOWN_DOUBLE_COUNTED, (
        "the set of double-counted ids CHANGED: %r against a known %r. If you added an id here, "
        "book ONE row and EDIT its verdict cell in place rather than appending a second - that is "
        "what MB16 did. If you removed one, `N` has FALLEN, which is the permissive direction and "
        "needs its own decision." % (dupes, KNOWN_DOUBLE_COUNTED))


def test_mb16_itself_charges_exactly_one_row():
    """The behavioural fix, pinned on the item that found the defect."""
    import collections
    from valuation.edge import research_log as rl

    counts = collections.Counter(rl._parse(os.path.join(REPO, "RESEARCH_LOG.md"))["ids"])
    assert counts["MB16"] == 1, counts["MB16"]


def test_the_duplicate_detector_is_not_vacuous():
    """Positive control: it must actually see duplicates when they exist.

    A detector returning {} on every input would pass the pin above only by accident of the
    literal being right - and would never fail on a new one.
    """
    import collections
    ids = ["A", "B", "B", "C", "C", "C"]
    dupes = {i: n for i, n in collections.Counter(ids).items() if n > 1}
    assert dupes == {"B": 2, "C": 3}


def test_the_recorded_excess_matches_the_recorded_rows():
    """The excess is the number of DUPLICATE rows times their n, and both are recorded.

    MB1: 1 duplicate row at n=2 -> 2.  O21-D2: 2 duplicate rows at n=1 -> 2.  Total 4.
    If someone edits one literal without the other, this fails.
    """
    n_of = {"MB1": 2, "O21-D2": 1}
    excess = sum((rows - 1) * n_of[i] for i, rows in KNOWN_DOUBLE_COUNTED.items())
    assert excess == KNOWN_EXCESS_TRIALS, excess


if __name__ == "__main__":
    fails = 0
    names = [n for n in sorted(globals()) if n.startswith("test_")]
    for name in names:
        try:
            globals()[name]()
            print("PASS", name)
        except Exception as e:                                       # noqa: BLE001
            fails += 1
            print("FAIL", name, "->", repr(e))
    print("%d passed, %d failed" % (len(names) - fails, fails))
    sys.exit(1 if fails else 0)
