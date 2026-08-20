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
import io
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
#   2026-08-15  equity 224 -> 227                              (MA31 + MA32, 3 arms, one register)
#   2026-08-16  equity 227 -> 230, options 292 -> 294          (P1S0 3 horizons; O17C4 2 arms)
#   2026-08-16  equity 230 -> 231                              (MA28-CARD, 1 arm, budget booked BEFORE the run)
#   2026-08-16  equity 231 -> 232                              (P1S0-CONTROL, 1 arm, budget booked BEFORE the run)
#   2026-08-19  infra 15 -> 17                                 (MB22 + MB23, 1 each, one register
#                                                               committed ALONE at 9dee135)
#   2026-08-19  options 304 -> 305                             (a CONCURRENT lane, merged in while
#                                                               MB22/MB23 were landing -- so this
#                                                               dict was reconciled to the MEASURED
#                                                               post-merge count, not to either
#                                                               side of the conflict. Taking one
#                                                               side would have mis-stamped a
#                                                               domain neither lane had wrong.)
#   2026-08-19  equity 235 -> 236                              (MB8, 1 arm, BOOKED BEFORE
#                                                               THE RUN. The register's own
#                                                               arithmetic expects its kill to
#                                                               fire, and the trial is charged
#                                                               anyway -- session 8's rule is
#                                                               that declining to run keeps the
#                                                               denominator while running and
#                                                               killing does not refund it.)
#   2026-08-19  equity 234 -> 235                              (MB18, 1 arm, BOOKED BEFORE
#                                                               THE RUN. No outcome existed at
#                                                               the booking commit -- which is
#                                                               the point: an N that rises only
#                                                               when a result is worth reporting
#                                                               understates every multiplicity
#                                                               correction in the project.)
#   2026-08-19  infra 15 -> 16                                 (MB21, 1 arm: the persistence-preserving
#                                                               null for S22. Charged INFRA on the
#                                                               HACFLOOR / X7RECON precedent -- building
#                                                               and validating a null is infrastructure,
#                                                               and infra N gates no published claim.
#                                                               Re-scoring a LANDED claim on a NEW
#                                                               instrument is not a new search and
#                                                               charges nothing further, so equity is
#                                                               deliberately unmoved at 234.)
#   2026-08-20  equity 236 -> 237                             (E-1, 1 arm, BOOKED BEFORE
#                                                               THE RUN. The register was
#                                                               accepted VERBATIM from the
#                                                               Frontier Scout's draft and
#                                                               committed ALONE at e05c33c,
#                                                               a strict ancestor of every
#                                                               measurement commit. ONE log
#                                                               row, verdict edited IN
#                                                               PLACE - MB16 measured that
#                                                               a second verdict row
#                                                               charges the trial twice.)
#   ---- the two infra entries above are INDEPENDENT registers landing the same day, and
#        the dict below is MEASURED post-merge rather than taken from either side.
#   2026-08-20  infra 18 -> 19                                 (SC-1, 1 trial BOOKED BEFORE the run
#                                                               per its own register, committed ALONE
#                                                               at e95cffb; equity 234 and options 305
#                                                               untouched - SC-1 opens no market data)
#   2026-08-20  equity 234 -> 235                             (a CONCURRENT lane, merged in
#                                                               while SC-1 was landing - the
#                                                               stamp is reconciled to the
#                                                               MEASURED post-merge count,
#                                                               never to one side of a
#                                                               conflict)
#
# The 2026-08-16 line moved BOTH scored domains in one session and is the first time it has. The
# HLZ literal moved with it again, for the second time running and for the reason the note below
# already gives -- so that note is now a measurement rather than a prediction. U6-COV landed in
# the same commit and charges NOTHING (its verdict cell reads FIXED): the proof it was seen and
# correctly excluded is `rows_fixed_not_counted` 47 -> 48, which is checked rather than assumed.
#
# A CORRECTION TO THE PROJECT'S OWN FOLKLORE ABOUT THIS FILE'S SIBLING HAZARD, measured while
# appending: an unescaped `|` inside a cell shifts every column after it, and the received wisdom
# (recorded in more than one handoff) is that such pipes "want escaping as `\|`". THEY DO NOT
# HELP. `research_log._parse` splits on a bare `"|"` and does not honour a backslash escape at
# all, so `\|` still creates two extra columns -- an append written that way is flagged
# `rows_malformed` exactly as an unescaped one is. The only fix is to not put a pipe in the prose.
# Caught here because the P1S0 row used `|delta|` for an absolute value, was flagged, and was
# rewritten to say "abs delta".
#
# The 2026-08-15 line is the stamp's SECOND real exercise and its first on `equity`, the domain
# that actually gates published claims. It went red on the MA31/MA32 log rows and was updated in
# the same commit, which is the mechanism working. Note the HLZ literal below had to move WITH it:
# despite `test_the_statistics_N_gates_move_with_it`'s docstring claiming its quantities are
# "asserted as RELATIONSHIPS to the stamp rather than as second literals, so there is exactly one
# place to edit", the hurdle IS a second literal and there were two of them. Reported here rather
# than restructured, because deriving it would make the assertion tautological and lose the
# formula check it really provides.
#
# That second line is the stamp's FIRST REAL EXERCISE, and it worked as designed: landing MA19's
# log row moved infra, the stamp went RED, and the expectation was updated deliberately in the
# same commit rather than relaxed to an inequality. MA13's own row charges nothing -- its verdict
# cell reads FIXED, so the parser does not count it. That held infra at 15 until 2026-08-19,
# when MB21's single infra trial took it to 16 -- the stamp's SECOND real exercise, updated
# in the same commit rather than relaxed, exactly as the first one was.
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
EXPECTED_BY_DOMAIN = {"equity": 238, "options": 305, "unified": 0, "infra": 19}


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


def test_the_stamp_is_assigned_EXACTLY_ONCE():
    """A duplicated stamp defeats the tamper-evidence it exists to provide.

    FOUND 2026-08-20, AND IT WAS THIS SUITE'S OWN, INTRODUCED BY A MERGE RESOLUTION. Commit
    `3def224` resolved two lanes booking a trial concurrently by KEEPING BOTH sides -- which is
    right for ledger ROWS, where two lanes' rows both belong, and wrong for a single-valued
    CONSTANT, where the first assignment becomes dead code. The suite went on passing because
    Python takes the last one, and for four days the file carried `equity: 235` above
    `equity: 236` with nothing to say which was live.

    That is the whole point of the guard defeated: a reader checking the count could read the
    dead line, and an editor updating it would see no effect. The merge was CLEAN -- adjacent
    insertions, no conflict markers, nothing to review -- which is the shape `MA23`'s
    cross-lane collision already recorded: *no file was edited by both sides, so there was no
    conflict to resolve and nothing to review.*

    Two lanes booking trials concurrently is now routine, so this will recur. Read from the
    SYNTAX TREE, so a comment quoting an old stamp cannot trip it.
    """
    import ast
    here = os.path.dirname(os.path.abspath(__file__))
    with io.open(os.path.join(here, "test_research_log_integrity.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    n = sum(1 for node in tree.body if isinstance(node, ast.Assign)
            for t in node.targets
            if isinstance(t, ast.Name) and t.id == "EXPECTED_BY_DOMAIN")
    assert n == 1, (
        f"EXPECTED_BY_DOMAIN is assigned {n} times. Keeping both sides of a merge is correct "
        f"for ledger ROWS and wrong for a single-valued CONSTANT: only the last assignment is "
        f"live, so the stamp stops being tamper-evidence. Re-read `by_domain` after the merge "
        f"and keep ONE line carrying the MEASURED counts (MA37's rule).")


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
    assert abs(math.sqrt(2.0 * math.log(n)) - 3.3082535192066147) < 1e-12, (
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


# =============================================================================================
# AUDIT MA5 — ONE Harvey-Liu-Zhu bar, DERIVED. Known-bad fixtures: each of the first three FAILS
# against the pre-fix tree (M3's standard), which was measured by restoring the sources to HEAD.
# =============================================================================================

_HLZ_ARITH = re.compile(r"sqrt\(\s*2(\.0)?\s*\*\s*(np|math)\.log")


def _code_only(src):
    """`src` with every COMMENT and STRING token blanked out, line structure preserved.

    A plain text sweep for this arithmetic fires on its own documentation -- it did, twice, on
    the block comment explaining the fix and on a docstring recording what the old expression
    was. A guard that cannot tell code from prose about code is not measuring the tree.
    """
    import io
    import tokenize

    lines = src.splitlines()
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return src
    out = [list(ln) for ln in lines]
    for tok in toks:
        if tok.type not in (tokenize.COMMENT, tokenize.STRING):
            continue
        (r0, c0), (r1, c1) = tok.start, tok.end
        for r in range(r0 - 1, min(r1, len(out))):
            lo = c0 if r == r0 - 1 else 0
            hi = c1 if r == r1 - 1 else len(out[r])
            for i in range(lo, min(hi, len(out[r]))):
                out[r][i] = " "
    return "\n".join("".join(ln) for ln in out)


def _shipped_py():
    """Every .py under `valuation/` — the SHIPPED package, not `scripts/`."""
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "valuation")
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.endswith(".py"):
                p = os.path.join(dirpath, f)
                with open(p, encoding="utf-8") as fh:
                    yield p, fh.read()


def test_ma5_there_is_exactly_one_sqrt_2_ln_N_in_the_shipped_package():
    """The audit found TWO bars. Measured, the shipped package carried the same idea FOUR times:
    `statistics.hlz_significant` (a CONSTANT 3.0), `fundamental_panel._trials_haircut`, the
    inline `hurdle` in its `multiple_testing` block, and `ablation.py`'s own copy -- and only one
    of them saw M1's floor. B7's defect class (three composite functions, one repair).

    ONE EXPRESSION IS DELIBERATELY NOT CONSOLIDATED, and this sweep found it: `param_search.py`
    computes Hansen's SPA recentring threshold `A = (omega/sqrt(T)) * sqrt(2 ln ln T)`. That is
    the law of the ITERATED logarithm over the SAMPLE LENGTH `T` -- a different statistic of a
    different quantity that merely shares a shape. Folding it into `hlz_hurdle` would silently
    change the SPA test. It is excluded by structure (its log argument is itself a log) rather
    than by filename, so a real HLZ copy appearing in that same file still fails this test.

    KNOWN-BAD: pre-fix this finds four HLZ copies and fails.
    """
    hits = []
    for p, src in _shipped_py():
        for line in _code_only(src).splitlines():
            m = _HLZ_ARITH.search(line)
            if not m:
                continue
            if "log(" in line[m.end():]:                  # sqrt(2 ln ln T) -- Hansen SPA, not HLZ
                continue
            hits.append(os.path.basename(p))
    assert sorted(set(hits)) == ["statistics.py"], (
        "sqrt(2 ln N) must be written ONCE, in statistics.hlz_hurdle; found it in %s"
        % (sorted(set(hits)),))


def test_ma5_the_hlz_bar_is_not_a_frozen_constant_anywhere():
    """3.0 is not a different bar from sqrt(2 ln N) -- it is that expression at N = 90, frozen.
    A constant cannot track a denominator that only rises, and the staleness runs in the
    FLATTERING direction because the hurdle only ever gets harder.

    KNOWN-BAD: pre-fix `statistics.py` contains `abs(t_stat) > 3.0` and this fails.
    """
    import inspect
    from valuation.edge import statistics as ST

    # Scoped to the FUNCTION, not the module: `statistics.py` legitimately carries 3.0 as the
    # normal kurtosis default, and the block comment above `hlz_hurdle` quotes the old constant
    # in order to explain it. A module-wide string ban fired on this test's own documentation --
    # caught by running it, and worth recording as the reason the check is narrow.
    body = inspect.getsource(ST.hlz_significant)
    assert "hlz_hurdle(" in body, "hlz_significant must delegate to the one definition"
    assert "3.0" not in body and "> 3" not in body, (
        "a hard-coded Harvey-Liu-Zhu constant is back in hlz_significant")

    # `n_trials` must be REQUIRED. A default is exactly what let this freeze in the first place.
    params = inspect.signature(ST.hlz_significant).parameters
    assert "n_trials" in params, "hlz_significant must take the trial count"
    assert params["n_trials"].default is inspect.Parameter.empty, (
        "n_trials must have NO default -- a default is how the bar went stale silently")


def test_ma5_the_two_bars_disagree_today_and_the_gap_only_widens():
    """The measurement that makes MA5 worth fixing rather than noting: the frozen constant and
    the derived bar crossed on 2026-08-06, when equity `N` went 84 -> 104.

    KNOWN-BAD: pre-fix `hlz_hurdle` does not exist and this errors.
    """
    import math
    from valuation.edge.statistics import hlz_hurdle, hlz_significant

    assert hlz_hurdle(90) < 3.0 < hlz_hurdle(91), "3.0 is sqrt(2 ln N) at N = 90"
    n = EXPECTED_BY_DOMAIN["equity"]
    assert abs(hlz_hurdle(n) - 3.3082535192066147) < 1e-12
    assert hlz_hurdle(n) > 3.0, "the derived bar is HARDER than the constant at today's N"

    # A statistic in the gap is 'significant' under the constant and is NOT at today's N. This
    # is the whole exposure, and it is why the fix is worth making before a second caller exists.
    t_in_the_gap = 3.1
    assert abs(t_in_the_gap) > 3.0                       # the constant would have passed it
    assert not hlz_significant(t_in_the_gap, n)          # the honest bar does not

    # Monotone in N, so a frozen bar can only ever be too EASY.
    assert hlz_hurdle(1000) > hlz_hurdle(n) > hlz_hurdle(8)


def test_ma5_every_shipped_bar_delegates_to_the_one_definition():
    """The pin that matters most: the CPCV adopt gate's multiplier and the helper must be the
    SAME arithmetic, and the floor must not become a cap.

    A CORRECTION AGAINST THIS TEST'S OWN FIRST DOCSTRING, kept because the error is the
    instructive part. It claimed this one "PASSES pre-fix, because the pre-fix copies were
    numerically equal". Measured by restoring the sources to HEAD, it ERRORS pre-fix -- there is
    no `hlz_hurdle` to import. The SUBSTANCE of the claim was right (the copies did agree to the
    bit; verified over 2,010 values at max |delta| 0.000e+00, which is why MA5 moves no number)
    and the claim about the TEST was wrong. Do not describe a fixture's pre-fix behaviour without
    running it.
    """
    from valuation.edge.statistics import hlz_hurdle

    n = EXPECTED_BY_DOMAIN["equity"]
    # `_trials_haircut` is FLOORED at the log's N, so the 8 weight schemes still return the
    # N-driven value. That flooring is local to the gate and is NOT part of the hurdle.
    assert FP._trials_haircut(8) == hlz_hurdle(n)
    assert FP._trials_haircut(10 ** 6) == hlz_hurdle(10 ** 6), "the floor must not become a cap"


# =============================================================================================
# AUDIT MA6 — the trial counter's one silent path toward a SMALLER `N`.
# =============================================================================================

_T2_HDR = "| id | date | domain | pre | hypothesis | metric | verdict | n | source |"
_T1_HDR = ("| id | date | domain | hypothesis | universe | metric | "
           "threshold (pre-committed) | verdict | source |")
_SEP = "|" + "---|" * 9


def _write_log(tmpdir, header, *rows):
    p = os.path.join(tmpdir, "RESEARCH_LOG.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write("# log\n\n" + header + "\n" + _SEP + "\n" + "\n".join(rows) + "\n")
    return p


def test_ma6_a_row_whose_domain_does_not_resolve_is_still_charged_to_N():
    """THE DEFECT. `by_domain[dom] += k` ran only when a domain resolved, so a row with a typo'd
    or blank domain cell was added to `trials` and to NO bucket -- and `trial_count(domain=...)`
    reads the bucket. The row was a real search over the data that no family paid for.
    Understating `N` OVERSTATES every DSR- and HLZ-gated claim: M1's own error, in M1's parser.

    KNOWN-BAD: pre-fix this returns 20 and fails. Both counts are kept above the
    WEIGHT_SCHEME_TRIALS floor of 8 deliberately -- at small n the floor would mask the defect.
    """
    with tempfile.TemporaryDirectory() as d:
        p = _write_log(
            d, _T2_HDR,
            "| A1 | 2026-01-01 | equity | yes | h | m | REJECTED | n=20 | s |",
            "| A2 | 2026-01-01 | equties | yes | h | m | REJECTED | n=5 | s |",
        )
        det = RL.detail(path=p, use_cache=False)
        assert det["trials_logged"] == 25, det["trials_logged"]
        assert det["by_domain"]["equity"] == 20, "by_domain still means 'rows that RESOLVED'"
        # THE BEHAVIOURAL ASSERTION FIRST, deliberately: against the pre-fix tree this FAILS
        # with the real number (20) rather than erroring on a key that does not exist yet, so
        # the fixture demonstrates the defect itself and not merely the absence of the repair.
        assert RL.trial_count(path=p, use_cache=False, domain="equity") == 25, (
            "the unresolved row must be CHARGED -- dropping it understates N")
        assert det["trials_domain_unresolved"] == 5
        # It cannot be attributed, so it is charged to EVERY family. Overstating N understates
        # significance, which is the safe direction; the reverse is the error M1 exists to fix.
        # `options` has 0 resolved + 5 unresolved = 5, which the weight-scheme floor lifts to 8.
        assert RL.trial_count(path=p, use_cache=False, domain="options") == 8
        assert RL.trial_count(path=p, use_cache=False, domain=None) == 25


def test_ma6_the_unresolved_rows_are_named_not_merely_counted():
    """THE COUNTER THAT DID NOT EXIST. Every other degradation in this parser is reported
    (`rows_malformed`, `rows_changed_by_parser_fix`); this one was reported nowhere, so a log
    quietly losing a domain cell was invisible.

    KNOWN-BAD: pre-fix `detail()` has no such key and this raises KeyError.
    """
    with tempfile.TemporaryDirectory() as d:
        p = _write_log(
            d, _T2_HDR,
            "| A1 | 2026-01-01 | equity | yes | h | m | REJECTED | n=9 | s |",
            "| A2 | 2026-01-01 |  | yes | h | m | REJECTED | n=4 | s |",
        )
        det = RL.detail(path=p, use_cache=False)
        rows = det["rows_domain_unresolved"]
        assert len(rows) == 1 and rows[0]["id"] == "A2", rows
        assert rows[0]["n_trials"] == 4
        assert rows[0]["domain_cell"] is None            # the blank cell is reported as blank
        assert det["by_domain_plus_unresolved_equals_trials"] is True


def test_ma6_the_invariant_is_reported_and_is_not_vacuous():
    """`sum(by_domain) + unresolved == trials` is the property a reader can check by hand. It is
    asserted BOTH ways so the flag cannot pass by always being True."""
    with tempfile.TemporaryDirectory() as d:
        p = _write_log(d, _T2_HDR,
                       "| A1 | 2026-01-01 | equity | yes | h | m | REJECTED | n=3 | s |",
                       "| A2 | 2026-01-01 | nonsense | yes | h | m | REJECTED | n=7 | s |")
        det = RL.detail(path=p, use_cache=False)
        assert det["by_domain_plus_unresolved_equals_trials"] is True
        assert sum(det["by_domain"].values()) == 3
        assert det["trials_domain_unresolved"] == 7 and det["trials_logged"] == 10


def test_ma6_a_row_appended_under_the_wrong_table_is_reported():
    """THE SECOND HAZARD. Both tables in `RESEARCH_LOG.md` are NINE columns wide with different
    orders, so `rows_malformed`'s width guard cannot see a row filed under the wrong header --
    its verdict is then read from the `threshold` column.

    KNOWN-BAD: pre-fix `detail()` has no `rows_misfiled_table` and this raises KeyError.
    """
    with tempfile.TemporaryDirectory() as d:
        p = _write_log(d, _T1_HDR,      # table-1 header ...
                       # ... with a table-2-shaped row under it: index 7 is `verdict` for this
                       # header but holds the grid multiplier for this row.
                       "| B1 | 2026-01-01 | equity | yes | h | m | REJECTED | n=3 | s |")
        det = RL.detail(path=p, use_cache=False)
        assert det["rows_malformed"] == [], "the width guard cannot see it -- 9 columns either way"
        mis = det["rows_misfiled_table"]
        assert len(mis) == 1 and mis[0]["id"] == "B1", mis
        assert mis[0]["verdict_cell"] == "n=3"


def test_ma6_the_misfiled_detector_does_not_cry_wolf():
    """REFUSAL DIRECTION. The rule is narrow on purpose -- a verdict cell of the exact form
    `n=<k>`. It must fire on NOTHING in the real log, and on no ordinary row."""
    with tempfile.TemporaryDirectory() as d:
        p = _write_log(d, _T2_HDR,
                       "| A1 | 2026-01-01 | equity | yes | h | m | REJECTED | n=3 | s |",
                       "| A2 | 2026-01-01 | infra | yes | h | m | FIXED - repaired | n/a | s |",
                       "| A3 | 2026-01-01 | options | retro | h | m | NULL | | s |")
        assert RL.detail(path=p, use_cache=False)["rows_misfiled_table"] == []
    assert RL.detail()["rows_misfiled_table"] == [], (
        "the real RESEARCH_LOG.md must be free of misfiled rows")


def test_ma6_use_cache_is_honoured_by_rows():
    """`rows(path, use_cache=True)` accepted the flag and called `_parse` unconditionally, so the
    parameter was a lie. Harmless in outcome -- it always re-read, the safe direction -- and
    closed because a parameter that does nothing is indistinguishable from one that broke.

    KNOWN-BAD: pre-fix `research_log._PARSED` does not exist and this raises AttributeError.
    """
    with tempfile.TemporaryDirectory() as d:
        p = _write_log(d, _T2_HDR,
                       "| A1 | 2026-01-01 | equity | yes | h | m | REJECTED | n=1 | s |")
        RL._PARSED.clear()
        first = RL.rows(path=p, use_cache=True)
        assert len(first) == 1
        assert any(k[0] == p for k in RL._PARSED), "a cached read must populate the cache"
        assert RL.rows(path=p, use_cache=False) == first

    # AND THE CACHE MUST NOT GO STALE: the key carries (mtime, size), so a file that CHANGES on
    # disk re-parses. A path-only key -- what `detail` used -- would have served the old count.
    with tempfile.TemporaryDirectory() as d:
        p = _write_log(d, _T2_HDR,
                       "| A1 | 2026-01-01 | equity | yes | h | m | REJECTED | n=1 | s |")
        assert RL.trial_count(path=p, domain=None) == 8       # floored at WEIGHT_SCHEME_TRIALS
        _write_log(d, _T2_HDR,
                   "| A1 | 2026-01-01 | equity | yes | h | m | REJECTED | n=40 | s |")
        assert RL.trial_count(path=p, domain=None) == 40, (
            "a changed file must re-parse; a path-only cache key served the stale count")


def test_ma6_N_did_not_move_on_the_real_log():
    """THE REPORTED RESULT. MA6 is a LATENT defect: today no row loses its domain, so the fix
    changes no published number. This asserts that, so a future log row that DOES lose its
    domain shows up as a deliberate stamp change rather than a silent one."""
    det = RL.detail()
    assert det["rows_domain_unresolved"] == [], det["rows_domain_unresolved"]
    assert det["trials_domain_unresolved"] == 0
    assert det["by_domain_plus_unresolved_equals_trials"] is True
    assert RL.trial_count(domain="equity") == EXPECTED_BY_DOMAIN["equity"]


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
