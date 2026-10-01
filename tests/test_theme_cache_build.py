"""THE PRODUCTION THEME CACHE — derived periods, a live universe, and one code object.

**WHAT WAS MEASURED.** On 2026-09-29 valquo.co served `theme_contributing` **institutional 0.0
/ insider 0.0**. `live_themes.py` reads `data/live_cache/theme_columns.json` and no production
scan has ever had it: `data/` is gitignored *and* dockerignored, `auto-scan.yml` sets no
`LIVE_THEMES_CACHE`, and the only writer was pinned to a snapshot of 500 names served on
2026-08-08 plus two period constants.

**THE CONTROL THAT CARRIES THE DERIVATION, and it is the one test here that could have gone
either way.** The periods must come from the calendar on the panel's own lag rule
(`_inst_accum`, `lag_days=45`) rather than from `PERIOD_CURR` / `PERIOD_PRIOR`. That is only
trustworthy if the derivation reproduces the pinned convention *on the date the constants were
written* — otherwise "derived" would just mean "different". It does, exactly, and it rolls on
precisely the date `live_theme_sources`' own comment predicts.

**AND THE ROW ARITHMETIC IS NOT REIMPLEMENTED.** `fidelity2_rebuild.build_live` computes it;
the builder calls that function with live arguments. A second copy is how the measured +0.9190
/ +0.8726 fidelity silently stops describing what production runs (`B7`).

Run: python tests/test_theme_cache_build.py
"""
from __future__ import annotations

import ast
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from scripts import fidelity2_rebuild as F2                              # noqa: E402
from scripts import live_theme_sources as M                              # noqa: E402
from scripts import theme_cache_build as B                               # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "auto-scan.yml")

PASSED = FAILED = SKIPPED = 0


def check(name, fn):
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print("  ok   %s" % name)
    except Exception as e:                                               # noqa: BLE001
        FAILED += 1
        print("  FAIL %s\n         %s: %s" % (name, type(e).__name__, e))


# =======================================================================================
# THE PERIOD DERIVATION — the control, and the staleness it exposes
# =======================================================================================
def test_the_derivation_reproduces_both_pinned_pairs_on_the_date_they_were_written():
    """THE decisive control. `PERIOD_CURR`/`PERIOD_PRIOR` were correct when V2G ran, and
    Q2-2026 13Fs were due 2026-08-14 — so on 2026-08-13 the calendar must give exactly the
    pinned answer. If it did not, "derived" would mean "different", not "current"."""
    p = B.latest_complete_periods(dt.date(2026, 8, 13))
    assert p["curr"] == M.PERIOD_CURR, (p["curr"], M.PERIOD_CURR)
    assert p["prior"] == M.PERIOD_PRIOR, (p["prior"], M.PERIOD_PRIOR)
    assert p["window_curr"] == M.WINDOW_CURR, (p["window_curr"], M.WINDOW_CURR)
    assert p["window_prior"] == M.WINDOW_PRIOR, (p["window_prior"], M.WINDOW_PRIOR)


def test_it_rolls_on_exactly_the_date_the_source_predicts():
    """`live_theme_sources` says "the 01jun2026-31aug2026 window is not published (Q2-2026 13Fs
    are due 2026-08-14)". The derivation must produce that window on that day — which is the
    independent confirmation that the lag rule is the right rule."""
    p = B.latest_complete_periods(dt.date(2026, 8, 14))
    assert p["curr"] == "30-JUN-2026", p["curr"]
    assert p["prior"] == "31-MAR-2026", p["prior"]
    assert p["window_curr"] == "01jun2026-31aug2026", p["window_curr"]


def test_the_pinned_constants_are_now_one_quarter_stale():
    """Stated as a test so it cannot be forgotten: this is WHY the constants had to go."""
    p = B.latest_complete_periods(dt.date(2026, 9, 29))
    assert p["curr"] != M.PERIOD_CURR, (
        "the constants are current today, so this test's premise has expired — re-read it")
    assert p["curr"] == "30-JUN-2026" and p["prior"] == "31-MAR-2026", p


def test_the_lag_rule_is_the_panel_s_own_and_a_period_is_never_used_early():
    """A quarter counts only when `period_end + 45d <= as_of` — `_inst_accum`'s own test."""
    assert B.INST_LAG_DAYS == 45, B.INST_LAG_DAYS
    # The day BEFORE Q2-2026 becomes complete, Q2 must not be used.
    p = B.latest_complete_periods(dt.date(2026, 8, 13))
    assert p["curr"] == "31-MAR-2026", "a period was used 45 days early"
    # ...and the boundary is inclusive, as the docstring's `<=` says.
    assert B.latest_complete_periods(dt.date(2026, 8, 14))["curr"] == "30-JUN-2026"


def test_the_two_periods_are_always_consecutive_quarters_and_ordered():
    for y in (2025, 2026):
        for mo in (1, 4, 7, 10):
            p = B.latest_complete_periods(dt.date(y, mo, 15))
            c = dt.date.fromisoformat(p["curr_date"])
            pr = dt.date.fromisoformat(p["prior_date"])
            assert pr < c, p
            gap = (c - pr).days
            assert 89 <= gap <= 92, (p, gap)


def test_quarter_ends_are_the_real_month_lengths():
    assert B.period_label(dt.date(2026, 3, 31)) == "31-MAR-2026"
    assert B.period_label(dt.date(2026, 6, 30)) == "30-JUN-2026"
    assert B.period_label(dt.date(2025, 12, 31)) == "31-DEC-2025"


# =======================================================================================
# B7 — ONE CODE OBJECT, AND THE DEFAULTS ARE UNCHANGED
# =======================================================================================
def test_the_builder_does_not_reimplement_the_row_arithmetic():
    """The insider formula and the inst_accum ratio must appear ONCE, in `build_live`.

    Read from the AST rather than grepped, because this module's docstring legitimately
    discusses `INSIDER_TANH_SCALE` and a substring ban would fire on the prose that documents
    the rule — the family that has cost this project six sessions.
    """
    src = open(B.__file__, encoding="utf-8").read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "tanh":
            raise AssertionError("the builder computes tanh itself; build_live owns that")
        if isinstance(node, ast.Name) and node.id in (
                "INSIDER_TANH_SCALE", "INSIDER_BUY_CAP", "INSIDER_BUY_BONUS"):
            raise AssertionError("the builder references %s directly rather than delegating"
                                 % node.id)
    assert "build_live(" in src, "the builder must CALL build_live, not restate it"


def test_build_live_with_no_arguments_is_unchanged():
    """Parameterising it must leave the pinned call bit-identical in SHAPE: every new
    parameter defaults to what the function already did."""
    import inspect
    sig = inspect.signature(F2.build_live)
    for name in ("served", "period_curr", "period_prior", "cache_path", "f4_dir", "root"):
        assert name in sig.parameters, "missing parameter %s" % name
        assert sig.parameters[name].default is None, (
            "%s does not default to None, so build_live() changed behaviour" % name)


def test_a_period_the_aggregate_lacks_is_REFUSED_not_defaulted():
    """The dangerous failure: a missing period would yield an empty dict, every `inst_accum`
    would be omitted, and the cache would look like a clean build of a universe with no
    institutional data — which is the 0.0 this whole item exists to fix.

    TESTED BEHAVIOURALLY, and the first version was not. It asserted the refusal's MESSAGE was
    present in the source, so blanking the branch to `if False:` left the string in place and
    the test passed — found by mutation. A guard tested by grepping for its own error text is
    not tested.
    """
    real_read, real_join = F2.M._read_json, F2.M.join_13f
    F2.M._read_json = lambda p: ({"by_period": {"31-DEC-2025": {}}}
                                 if str(p).endswith("13f_aggregate.json") else None)
    F2.M.join_13f = lambda root, served, agg: {}
    try:
        raised = None
        try:
            F2.build_live(served=[{"ticker": "AAPL", "name": "", "market_cap": 1.0,
                                   "sector": ""}],
                          period_curr="30-JUN-2026", period_prior="31-DEC-2025",
                          cache_path=os.path.join(ROOT, "_should_not_be_written.json"))
        except SystemExit as e:
            raised = str(e)
        assert raised is not None, "a missing 13F period did NOT refuse"
        assert "carries no data for" in raised and "30-JUN-2026" in raised, raised
        assert not os.path.exists(os.path.join(ROOT, "_should_not_be_written.json")), (
            "it wrote a cache despite refusing")
    finally:
        F2.M._read_json, F2.M.join_13f = real_read, real_join


# =======================================================================================
# THE CACHE PATH — why it must be overridable
# =======================================================================================
def test_the_cache_path_comes_from_the_environment():
    had = os.environ.get("LIVE_THEMES_CACHE")
    try:
        os.environ["LIVE_THEMES_CACHE"] = ".scan-cache/theme_columns.json"
        assert B.cache_path() == ".scan-cache/theme_columns.json"
        os.environ.pop("LIVE_THEMES_CACHE")
        assert B.cache_path() == B.DEFAULT_CACHE
    finally:
        if had is None:
            os.environ.pop("LIVE_THEMES_CACHE", None)
        else:
            os.environ["LIVE_THEMES_CACHE"] = had


def test_an_empty_store_is_a_refusal_rather_than_an_empty_cache():
    """A zero-row cache reads to `live_themes.py` exactly like the absent file."""
    class Empty:
        def latest_scan_date(self):
            return None

        def load_snapshot(self, d=None, top=None):
            return []

    got = B.served_from_store(Empty())
    assert got["served"] == [] and got["scan_date"] is None
    assert "no scans" in got["reason"], got["reason"]


def test_the_served_universe_comes_from_the_latest_scan_not_the_pinned_file():
    class Fake:
        def latest_scan_date(self):
            return "2026-09-29"

        def load_snapshot(self, d=None, top=None):
            return [{"ticker": "aapl", "name": "Apple", "market_cap": 1.0, "sector": "Tech"},
                    {"ticker": "", "name": "junk"}]

    got = B.served_from_store(Fake())
    assert got["scan_date"] == "2026-09-29"
    assert [r["ticker"] for r in got["served"]] == ["AAPL"], got["served"]
    # READ THE TREE, NOT THE TEXT. This banned the substring `load_served()` and then fired
    # against a CORRECT builder, because a comment was added explaining why the no-argument form
    # must not be used -- prose documenting a rule quotes what the rule forbids. Fourth instance
    # of that family in this repo's record. The property is that no CALL to `load_served` takes
    # zero arguments anywhere in the builder.
    import ast as _ast
    src = open(B.__file__, encoding="utf-8").read()
    bare = [n for n in _ast.walk(_ast.parse(src))
            if isinstance(n, _ast.Call)
            and (getattr(n.func, "id", None) == "load_served"
                 or getattr(n.func, "attr", None) == "load_served")
            and not n.args and not n.keywords]
    assert not bare, (
        "the builder falls back to the pinned snapshot, which is the defect")
    # POSITIVE CONTROL: the narrowed rule must still bite on the thing it exists to catch.
    _probe = _ast.parse("served = load_served()")
    _hit = [n for n in _ast.walk(_probe)
            if isinstance(n, _ast.Call) and getattr(n.func, "id", None) == "load_served"
            and not n.args and not n.keywords]
    assert _hit, "the narrowed guard can no longer see a bare load_served() call"


# =======================================================================================
# THE FIDELITY CONTROL — and it must not pass vacuously
# =======================================================================================
def test_the_fidelity_control_cannot_pass_when_its_inputs_are_absent():
    """An absent control and a satisfied control must never read the same. On this machine the
    banked artifacts are GONE, so the honest answer is `runnable: False` — neither a pass nor
    a failure."""
    r = B.fidelity_control(banked=os.path.join(ROOT, "no", "such", "cache.json"),
                           root=os.path.join(ROOT, "no", "such", "root"))
    assert r["runnable"] is False and r["ok"] is False, r
    assert r["missing_inputs"], r
    assert "CANNOT RUN" in r["reason"], r["reason"]
    assert "NOT a pass" in r["reason"], r["reason"]


def test_the_fidelity_control_exits_non_zero_when_it_cannot_run():
    """A control that could not run must not report success to a shell."""
    had = os.environ.get("LIVE_THEMES_CACHE")
    try:
        os.environ["LIVE_THEMES_CACHE"] = os.path.join(ROOT, "no", "such", "x.json")
        assert B.main(["--fidelity"]) != 0
    finally:
        if had is None:
            os.environ.pop("LIVE_THEMES_CACHE", None)
        else:
            os.environ["LIVE_THEMES_CACHE"] = had


# =======================================================================================
# THE WORKFLOW HALF — MA12 idiom, skipping loudly until Don's PR lands
# =======================================================================================
def test_the_hot_job_sets_LIVE_THEMES_CACHE():
    """MA12 idiom: read the workflow and fail while the hot job cannot see the cache.

    SKIPS LOUDLY until the PR lands, because `.github/` is Don-PR-only and this lane may not
    edit it — but it skips rather than passing, so the gap stays visible instead of being
    mistaken for done.
    """
    global SKIPPED
    if not os.path.exists(WORKFLOW):
        SKIPPED += 1
        print("       (SKIPPED LOUDLY: %s absent)" % WORKFLOW)
        return
    txt = open(WORKFLOW, encoding="utf-8").read()
    if "LIVE_THEMES_CACHE" not in txt:
        SKIPPED += 1
        print("       (SKIPPED LOUDLY: auto-scan.yml sets no LIVE_THEMES_CACHE, so every live "
              "score still omits institutional and insider. Don's PR — brief 5.3 — is "
              "OUTSTANDING; this becomes a hard failure once it lands.)")
        return
    assert "theme_columns.json" in txt, (
        "LIVE_THEMES_CACHE is set but does not name theme_columns.json")


# =======================================================================================
# MC1 FOLLOW-UPS — the path hazard and the half-applied override
# =======================================================================================
def test_the_fidelity_reference_is_NOT_the_live_readers_path():
    """THE HAZARD, and it is a silent vintage change rather than a wrong number.

    `fidelity2_rebuild.LIVE_CACHE` and `live_themes.CACHE` are the same file. Restoring the
    banked reference there to run `--fidelity` turns on the seven-theme book for every local
    scan and keeps it on for up to `MAX_AGE_DAYS` = 120 days — an unannounced vintage 5,
    arrived at by putting a file somewhere. The Oct 22 rebalance book is built locally, so it
    is not hypothetical.
    """
    from valuation.screener import live_themes as LT
    ref = os.path.abspath(B.FIDELITY_REFERENCE)
    assert ref != os.path.abspath(LT.CACHE), (
        "the fidelity reference IS the live cache path: restoring it would silently enable the "
        "seven-theme book for %d days" % LT.MAX_AGE_DAYS)
    assert ref != os.path.abspath(F2.LIVE_CACHE), (ref, F2.LIVE_CACHE)
    # ...and it is the control's DEFAULT, not merely available.
    r = B.fidelity_control(root=os.path.join(ROOT, "no", "such", "root"))
    assert any("FIDELITY_REFERENCE" in m or "theme_columns.FIDELITY_REFERENCE" in m
               for m in r["missing_inputs"]), r["missing_inputs"]


def test_the_root_override_is_forwarded_to_the_build_and_not_half_applied():
    """A half-applied override reports that it checked one tree and then measures another.

    The first cut used `root` for the existence checks and the probe path and called
    `build_live` with no `root`, so it verified the override's inputs and then built from
    `F2.ROOT`. The wrong-object family.
    """
    import inspect
    src = inspect.getsource(B.fidelity_control)
    assert "F2.build_live(root=root" in src, (
        "root is not forwarded to build_live, so the override is half-applied")
    assert "f4_dir=" in src, "the Form 4 directory is not derived from root either"


def test_a_tiny_residue_is_LABELLED_rather_than_tolerated():
    """The bar stays 0.0; a Linux run must not read as a fidelity failure.

    Measured 2026-09-29: 440 rows, max abs delta 1.42e-14 on 44 insider_score rows, and the
    PRE-parameterisation code gives the identical figure while new-vs-old on one machine is
    exactly 0.0 — so it is platform `math.tanh`, not the refactor.
    """
    src = open(B.__file__, encoding="utf-8").read()
    assert "platform_note" in src, "a sub-1e-12 residue is not labelled at all"
    assert "THE BAR REMAINS 0.0" in src, "the note does not say the bar is unchanged"
    # AND THE BAR IS STILL 0.0 IN CODE, not widened to a tolerance.
    assert "ok=(worst == 0.0" in src, "the fidelity bar was loosened to a tolerance"


def run():
    global PASSED, FAILED
    print("THEME CACHE BUILD")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            check(name, fn)
    print("\n%d passed, %d failed, %d skipped" % (PASSED, FAILED, SKIPPED))
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
