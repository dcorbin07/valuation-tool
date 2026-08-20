"""MB11 — the optionable partition as a REPORTED DIAGNOSTIC. Offline, deterministic.

    python tests/test_optionable_partition.py

WHAT IS ACTUALLY AT RISK HERE, and it is not the table.

1. **A DESCRIPTION BECOMING A RULE.** The measurement says the options-listed subset did worse
   early and better late. The late column is large and a reader — or a copy edit — will build
   "so options-listed names do better" out of it unaided. `P1S0-CONTROL` was the register built
   to test exactly that causal claim and it returned NULL, so the claim is not merely unproven,
   it is one this project specifically tried and failed to establish. The BANNED tuple's
   ATTRIBUTION family exists for it.

2. **A GUARD THAT DEFEATS ITS OWN ITEM.** Ban "outperform" outright and the surface can no
   longer state the finding it exists to state. The line is the TENSE, not the verb, and there
   is a test below that fails if past-tense description ever stops being sayable.

3. **A NUMBER TYPED TWICE.** The gaps between the two columns are derived from the two sides.
   A hand-typed gap that happened to agree with a mistyped side would look right forever.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

import ast                                            # noqa: E402
import html as _htmlmod                               # noqa: E402

from valuation.config import CONFIG                   # noqa: E402

CONFIG.private_mode = False
CONFIG.portfolio_path = "/work"

from valuation.saas.app_saas import create_saas_app   # noqa: E402
from valuation.web import optionable_partition as OP  # noqa: E402

APP = create_saas_app(CONFIG)
APP.config["TESTING"] = True

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE = os.path.join(ROOT, "valuation", "web", "optionable_partition.py")
TEMPLATE = os.path.join(ROOT, "valuation", "web", "templates", "portfolio.html")


def _page():
    with APP.test_client() as c:
        r = c.get("/work")
    assert r.status_code == 200, f"/work returned {r.status_code}"
    return _htmlmod.unescape(r.get_data(as_text=True))


def _section(page=None):
    """Just MB11's own section of the rendered page.

    SCOPED DELIBERATELY. `/work` carries nine sections written by different items, and the
    BANNED tuple run against the whole page fires on `tradable`, `buy` and `sell` in other
    items' prose. Policing another item's copy is not this guard's job — see `violations`.
    """
    p = page if page is not None else _page()
    i = p.index(OP.HEADING)
    return p[i:p.index("</section>", i)]


def _src(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# --------------------------------------------------------------------- it is on the page
def test_the_section_renders_and_every_sentence_comes_from_the_module():
    sec = _section()
    pay = OP.payload()
    for key in ("heading", "callout_heading", "lede", "what_it_is", "what_was_measured",
                "not_a_forecast", "cannot_separate", "source_note"):
        assert pay[key] in sec, f"{key} is not rendered verbatim"


def test_the_template_holds_no_copy_of_its_own():
    """A sentence living in both places is two versions of the truth — the defect
    `dip_posture` was made a module to prevent."""
    tmpl = _src(TEMPLATE)
    for key in ("lede", "what_it_is", "what_was_measured", "not_a_forecast", "cannot_separate",
                "callout_heading"):
        text = OP.payload()[key]
        for chunk in (text[:40], text[-40:]):
            assert chunk not in tmpl, f"{key} is retyped in the template"


# --------------------------------------------------------------------- the posture line
def test_the_rendered_section_carries_no_banned_phrasing():
    """Asserted against what is SERVED, `dip_posture`'s design — rendering is where copy
    leaks — and scoped to the section this item owns."""
    bad = OP.violations(_section())
    assert not bad, f"banned phrasing reached the rendered section: {bad}"


def test_the_banned_check_is_not_vacuous():
    """It must fire on a real forecast, a real recommendation and the causal claim."""
    for planted in ("options-listed names will outperform going forward",
                    "you should buy the options-listed half",
                    "they did better because they are optionable",
                    "this is a signal worth trading"):
        assert OP.violations(planted), f"the guard missed: {planted!r}"


def test_past_tense_description_stays_sayable():
    """THE GUARD MUST NOT DEFEAT THE ITEM IT GUARDS.

    MB11's whole deliverable is a reported description. If the tuple banned the verbs the
    description needs, the honest sentence would be unsayable and the surface would be reduced
    to a caveat with nothing to caveat.
    """
    for allowed in ("the options-listed subset did better over 2021 to 2025",
                    "it did worse early and better late",
                    "the subset outperformed the full panel in the later window",
                    "the full panel beat it at all three horizons"):
        assert not OP.violations(allowed), (
            f"the guard forbids stating the finding: {allowed!r} -> {OP.violations(allowed)}")


def test_it_says_it_describes_the_past_and_carries_no_forecast():
    """The item's own requirement, asserted on the RENDERED section rather than the source."""
    sec = _section().lower()
    assert "describes the past" in sec, "the surface does not say it describes the past"
    assert "no forecast" in sec, "the surface does not say it carries no forecast"


def test_the_three_reasons_are_all_present_and_none_is_an_assertion():
    """Each of the three is a MEASURED fact, and the copy must carry all three: the
    attribution returned null, the full panel did not sort either in that window, and it
    reverses. Dropping any one leaves a reader able to rebuild the causal claim."""
    sec = _section().lower()
    assert "no answer" in sec or "null" in sec, "the failed attribution is not stated"
    assert "did not sort either" in sec, "the full panel's own early failure is not stated"
    assert "reverses" in sec, "the reversal is not stated"
    assert "could not separate them" in sec, "the inseparability is not stated"


def test_the_closed_family_is_not_reopened():
    sec = _section().lower()
    assert "closed" in sec and "reopens it" in sec, (
        "the surface does not say the family it came from stays closed")


# --------------------------------------------------------------------- the numbers
def test_the_gaps_are_derived_and_never_typed():
    """Only the two sides are transcribed; every gap is computed from them.

    `accounting_risk`'s rule. A hand-typed gap that agreed with a mistyped side would look
    right forever, and nothing else on the page could catch it.
    """
    for r in OP.rows():
        assert abs(r["gap_early"] - (r["full_early"] - r["opt_early"])) < 1e-12
        assert abs(r["gap_late"] - (r["full_late"] - r["opt_late"])) < 1e-12

    code = _src(MODULE)
    for r in OP.rows():
        for g in (r["gap_early"], r["gap_late"]):
            assert ("%.3f" % g) not in code, f"gap {g:.3f} is typed into the module"
    sec_src = _src(TEMPLATE)
    for r in OP.rows():
        for g in (r["gap_early"], r["gap_late"]):
            assert ("%.3f" % g) not in sec_src, f"gap {g:.3f} is typed into the template"


def test_the_two_sides_reproduce_the_artifacts():
    """A SECOND, INDEPENDENT TRANSCRIPTION.

    `data/` is gitignored and never ships, so the module cannot read the artifacts at render
    time and neither can CI. The figures are therefore transcribed here a second time,
    straight from `P1S0_GATE.json` (`modes.pit_liquid.arms`) and `P1S0_CONTROL.json`
    (`horizons.*.full_panel`), and compared. Two independent transcriptions agreeing is the
    strongest check available offline; one transcription checked against itself is none.
    """
    expected = {
        63:  dict(full_early=4.284968705583039,  opt_early=2.817664383006252,
                  full_late=14.60410952103895,   opt_late=24.307846868585395),
        252: dict(full_early=6.042706550726021,  opt_early=-0.08168588889261308,
                  full_late=11.854230233961291,  opt_late=22.781390621069983),
        504: dict(full_early=2.0437022401810473, opt_early=0.5163009659756745,
                  full_late=9.733290973192038,   opt_late=11.288231624406292),
    }
    got = {r["days"]: r for r in OP.rows()}
    assert set(got) == set(expected), sorted(got)
    for days, exp in expected.items():
        for k, v in exp.items():
            assert abs(got[days][k] - v) < 1e-12, (days, k, got[days][k], v)

    # ...and the audit's own six gaps, which is what the item was raised on.
    audit = {63: (1.467, -9.704), 252: (6.124, -10.927), 504: (1.527, -1.555)}
    for days, (e, l) in audit.items():
        assert abs(got[days]["gap_early"] - e) < 0.001, (days, got[days]["gap_early"], e)
        assert abs(got[days]["gap_late"] - l) < 0.001, (days, got[days]["gap_late"], l)


def test_the_direction_of_every_row_matches_what_the_copy_claims():
    """The copy says the subset did WORSE early at all three horizons and BETTER late at all
    three. Prose that states a direction the numbers do not have is the failure this catches,
    and it is the one a later transcription slip would produce."""
    for r in OP.rows():
        assert r["gap_early"] > 0, f"H={r['days']}: copy says worse early, numbers disagree"
        assert r["gap_late"] < 0, f"H={r['days']}: copy says better late, numbers disagree"


# --------------------------------------------------------------------- posture of the page
def test_the_page_stays_static_and_byte_identical():
    """`/work`'s own promise: it takes no arguments, reads no store and makes no fetch. This
    section must not be the thing that breaks it."""
    with APP.test_client() as c:
        a = c.get("/work").get_data(as_text=True)
        b = c.get("/work").get_data(as_text=True)
    assert a == b, "the page stopped being byte-identical across requests"
    assert "/api/" not in a, "the page acquired an API call"


def test_the_module_reads_no_store_and_has_no_clock():
    """Literals only. A clock or a file read here would make the page non-static, and the
    private-mode suite's byte-identical assertion is what would break — one item over."""
    tree = ast.parse(_src(MODULE))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in ("open", "input"), f"{node.func.id}() in the module"
        if isinstance(node, ast.Attribute):
            assert node.attr not in ("now", "today", "utcnow", "get", "post"), (
                f"the module calls .{node.attr}()")
    for banned_import in ("requests", "datetime", "json", "sqlite3"):
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(a.name != banned_import for a in node.names), banned_import
            if isinstance(node, ast.ImportFrom):
                assert node.module != banned_import, banned_import


def test_no_test_in_this_file_is_shadowed_by_a_duplicate_name():
    """A second `def test_x` silently rebinds the first and the runner iterates globals, so
    the shadowed one vanishes without a word."""
    tree = ast.parse(_src(os.path.abspath(__file__)))
    names = [n.name for n in tree.body
             if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
    assert len(names) == len(set(names)), (
        f"shadowed: {sorted(n for n in names if names.count(n) > 1)}")
    reachable = [k for k in globals() if k.startswith("test_") and callable(globals()[k])]
    assert len(reachable) == len(names), (len(reachable), len(names))


def _run_all():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:                                   # noqa: BLE001
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} optionable-partition tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
