"""MA13 — tamper-evidence for `N`, the denominator of every significance claim this project makes.

Run: python tests/test_research_log_integrity.py

WHY THIS FILE EXISTS. `N` (equity trials) is the denominator of the Deflated Sharpe, of the
Harvey-Liu-Zhu hurdle sqrt(2 ln N), and of `_trials_haircut`, which the CPCV adopt gate multiplies
its standard error by. **Lowering `N` raises every DSR- and HLZ-gated claim in the project**, and
lowering it takes one edited cell: changing a `verdict` to `FIXED` removes that row from the count
(`research_log.py`). It is parsed out of a markdown table that agents append to every session.

The suite did not pin it. `tests/test_edge.py`'s M1 test asserts only RELATIONAL properties --
`trial_count("equity") < trial_count(None)`, `FP._trial_N() == RL.trial_count("equity")`, a missing
file falls back to 8, `by_domain["equity"] > 8`. **Every one of those still passes after an edit
that drops `N` from 224 to 9.** Meanwhile the project pins far less consequential things by
literal: the vintage clock is pinned by derivation, the Sharadar freeze carries a sha256 manifest,
`SCHEMA_VERSION` is asserted field by field.

WHAT THIS IS AND IS NOT. It is tamper-EVIDENCE, not a lock. `N` is *supposed* to rise -- every
landed register raises it, and that is the counter working correctly. The point is that it may
only change **deliberately and visibly**: this file makes a change to `N` require editing a
committed literal in the same commit, so it appears in the diff and has to be argued. That is
exactly the `test_track_meter` idiom, applied to the other number nobody can see move.

IT IS ALSO CHECKED FOR VACUITY, which is the failure mode a guard like this actually dies of (M6's
lesson: a check that cannot fail anything is not a check). `test_the_stamp_is_not_vacuous` proves
the comparison rejects a tampered count in BOTH directions, and
`test_a_tampered_log_really_does_lower_N` performs the exact edit the docstring warns about on a
real copy of the log and shows the count fall.
"""
import os
import re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import fundamental_panel as FP          # noqa: E402
from valuation.edge import research_log as RL               # noqa: E402

# ---------------------------------------------------------------------------------------------
# THE STAMP. Committed literal. If a register lands and `N` legitimately rises, edit this dict in
# the SAME COMMIT as the log row -- that is the whole mechanism. Do not delete the assertion, and
# do not "temporarily" relax it to an inequality: an inequality is what this file exists to
# replace.
#
#   2026-08-14  equity 224, options 292, infra 14, unified 0   (stamp introduced, MA13)
#   2026-08-14  infra 14 -> 15                                 (MA19's own calibration row)
#
# That second line is the stamp's FIRST REAL EXERCISE, and it worked as designed: landing MA19's
# log row moved infra, the stamp went RED, and the expectation was updated deliberately in the
# same commit rather than relaxed to an inequality. MA13's own row charges nothing -- its verdict
# cell reads FIXED, so the parser does not count it -- which is why infra reads 15 and not 16.
#
# WHY A LITERAL HERE AND NOT `BACKTEST_RESULTS.json`'s `by_domain`. The audit notes that the
# canonical artifact already ships this dict and so is "a natural home" for the expectation.
# Measured 2026-08-14, the two agree exactly. It is still declined as the SOURCE, deliberately:
# the artifact is refreshed by a 20-40 minute backtest, while `N` rises the moment a register
# lands, so sourcing the expectation from it would put the suite RED for the ordinary, correct
# interval between a landing and the next full run. CLAUDE.md's own warning applies -- "a gate
# that cries wolf is one you learn to ignore" -- and a tamper-evidence check is worth nothing
# once people are used to seeing it fail. Cross-checking the artifact against the log is a real
# and separate convention (the master audit lists it under MA21); it belongs to that row, with
# its own decision about staleness tolerance, not smuggled in here.
# ---------------------------------------------------------------------------------------------
EXPECTED_BY_DOMAIN = {"equity": 224, "options": 292, "unified": 0, "infra": 15}


def _diff(expected, actual):
    """Human-readable difference, or '' when they agree. Direction and magnitude are both named:
    a FALL in `N` is the dangerous direction (it raises every gated claim) and must say so."""
    keys = sorted(set(expected) | set(actual))
    bad = []
    for k in keys:
        e, a = expected.get(k), actual.get(k)
        if e == a:
            continue
        if e is None:
            bad.append(f"  {k}: NEW domain appeared, now {a}")
        elif a is None:
            bad.append(f"  {k}: domain DISAPPEARED (was {e})")
        else:
            d = a - e
            arrow = "FELL" if d < 0 else "rose"
            warn = "  <-- a FALL RAISES every DSR/HLZ-gated claim" if d < 0 else ""
            bad.append(f"  {k}: {e} -> {a}  ({arrow} by {abs(d)}){warn}")
    if not bad:
        return ""
    return (
        "RESEARCH_LOG.md's trial counts no longer match the committed stamp:\n"
        + "\n".join(bad)
        + "\n\nIf this change is INTENTIONAL (a register landed, so `N` rose), update\n"
          "EXPECTED_BY_DOMAIN in tests/test_research_log_integrity.py IN THE SAME COMMIT as the\n"
          "log row, so the change appears in the diff. If it is NOT intentional, `N` has moved\n"
          "without a register and every significance claim gated on it is now misquoted."
    )


def test_the_trial_counts_match_the_committed_stamp():
    """MA13. The stamp itself."""
    actual = RL.detail()["by_domain"]
    msg = _diff(EXPECTED_BY_DOMAIN, actual)
    assert not msg, msg


def test_the_stamp_is_not_vacuous():
    """A guard that passes because it compares nothing is the defect it exists to prevent.

    Both directions must be caught. A fall is the dangerous one, but an unrecorded RISE is still
    an undisclosed change to a published denominator, and a stamp that only caught falls would
    let `N` drift upward silently between sessions.
    """
    base = dict(EXPECTED_BY_DOMAIN)
    assert _diff(base, base) == "", "identical dicts must compare equal"

    lowered = dict(base, equity=base["equity"] - 1)
    msg = _diff(base, lowered)
    assert msg, "a LOWER equity count was not caught"
    assert "FELL" in msg and "RAISES every DSR/HLZ-gated claim" in msg, msg

    raised = dict(base, equity=base["equity"] + 7)
    msg = _diff(base, raised)
    assert msg and "rose by 7" in msg, f"a HIGHER equity count was not caught: {msg}"

    # A whole domain vanishing (e.g. the parser silently failing on one table) must not read as
    # agreement.
    dropped = {k: v for k, v in base.items() if k != "options"}
    assert "DISAPPEARED" in _diff(base, dropped), "a vanished domain was not caught"


def test_a_tampered_log_really_does_lower_N():
    """The end-to-end vacuity proof: perform the exact edit the docstring warns about.

    Flipping a single `verdict` cell to FIXED removes that row from the count. This is done on a
    COPY in a temp dir -- the real log is append-only and is never written by a test.
    """
    real = RL.detail()
    src = real["path"]
    assert src and os.path.exists(src), f"cannot locate RESEARCH_LOG.md: {src}"

    with tempfile.TemporaryDirectory() as td:
        dst = os.path.join(td, "RESEARCH_LOG.md")
        shutil.copyfile(src, dst)

        before = RL.trial_count(path=dst, use_cache=False, domain="equity")
        assert before == real["by_domain"]["equity"], (
            f"the copy must parse identically to the original: {before} vs "
            f"{real['by_domain']['equity']}")

        # Flip the FIRST counted equity row's verdict cell to FIXED.
        #
        # THE COLUMN IS RESOLVED BY HEADER NAME, NOT BY A FIXED INDEX, and that is not fussiness:
        # RESEARCH_LOG.md contains TWO tables with DIFFERENT 9-column schemas --
        #   table 1: id | date | domain | hypothesis | universe | metric | threshold | verdict | source
        #   table 2: id | date | domain | pre | hypothesis | metric | verdict | n | source
        # -- so `verdict` sits at a different offset in each. The first cut of this test used
        # table 2's offset throughout, edited table 1's `threshold` cell instead, and reported
        # "tampering did NOT lower N". That read like evidence the hazard was not real; it was
        # actually a demonstration that session 12's fix works (the parser reads the verdict cell
        # ALONE, so a stray FIXED elsewhere on the row is correctly ignored). Resolving by name is
        # what `research_log._parse` itself does.
        text = open(dst, encoding="utf-8", errors="replace").read()
        out, tampered, hdr = [], False, None
        for line in text.splitlines():
            if line.startswith("|"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                low = [c.lower() for c in cells]
                if "verdict" in low and "domain" in low:
                    hdr = {"verdict": low.index("verdict"), "domain": low.index("domain"),
                           "width": len(cells)}
                elif (not tampered and hdr is not None and len(cells) == hdr["width"]
                      and cells[hdr["domain"]].lower() == "equity"
                      and not cells[hdr["verdict"]].upper().startswith("FIXED")
                      and cells[0] and not set(cells[0]) <= set("-: ")):
                    cells[hdr["verdict"]] = "FIXED"
                    line = "| " + " | ".join(cells) + " |"
                    tampered = True
            out.append(line)
        assert tampered, "could not find an equity row to tamper with — schema may have changed"
        open(dst, "w", encoding="utf-8").write("\n".join(out))

        after = RL.trial_count(path=dst, use_cache=False, domain="equity")
        assert after < before, (
            f"tampering did NOT lower N ({before} -> {after}); either the parser changed or this "
            f"test is no longer exercising the hazard MA13 describes")

        # And the stamp must catch precisely that.
        msg = _diff(EXPECTED_BY_DOMAIN, dict(real["by_domain"], equity=after))
        assert msg and "FELL" in msg, "the stamp did not catch a real tampered count"


def test_the_statistics_N_gates_move_with_it():
    """`N` is not an ornament: pin the two derived quantities it actually drives.

    These are asserted as RELATIONSHIPS to the stamp rather than as second literals, so there is
    exactly one place to edit when `N` legitimately changes. Pinning the numbers twice would give
    two things to forget.
    """
    import math

    n = EXPECTED_BY_DOMAIN["equity"]
    assert RL.trial_count(domain="equity") == n

    # The Harvey-Liu-Zhu hurdle the record quotes.
    assert abs(math.sqrt(2.0 * math.log(n)) - 3.2898772171176964) < 1e-12, (
        "the HLZ hurdle no longer matches the stamped N")

    # The CPCV adopt gate's multiplier. `_trials_haircut` is FLOORED at the log's N, so handing
    # it the 8 weight schemes must still return the N-driven value -- that flooring is the whole
    # mechanism by which N reaches the adopt decision (and, through it, the placebo floors).
    assert abs(FP._trials_haircut(8) - math.sqrt(2.0 * math.log(n))) < 1e-12, (
        "_trials_haircut is no longer floored at the research log's N")


def test_the_relational_assertions_are_kept_too():
    """MA13 ADDS to M1's test, it does not replace it. The relational properties still matter --
    they catch a different failure (domain scoping collapsing) that an equality check would pass
    straight through if the stamp were edited to match."""
    assert RL.trial_count(domain="equity") < RL.trial_count(domain=None)
    assert RL.trial_count(path="does_not_exist.md", use_cache=False) == RL.WEIGHT_SCHEME_TRIALS
    assert FP._trial_N() == RL.trial_count(domain="equity")


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
    print(f"\n{passed}/{len(tests)} research-log integrity tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
