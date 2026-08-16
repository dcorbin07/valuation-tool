"""AUDIT MA56 - the residual term-slope, RECORDED and deliberately NOT run.

Run: python tests/test_ma56_carry_forward.py

MA56 is the one row in this lane's batch that is `trial_cost: 0 (record only)`, and its own kill
condition is the instruction "do not run today; carry in the next entry register". So the
deliverable is a record that (a) a future entry-register author will actually encounter and
(b) cannot silently drift away from the measurement it claims to be quoting.

The test that earns its keep is `test_the_recorded_figures_match_the_research_log_row`: it parses
the O16-REFROZEN row out of `RESEARCH_LOG.md` and checks every number in the carry-forward block
against it. A record copied by hand from an audit's one-line summary is exactly the artifact this
project has caught going stale a dozen times - the stale theme-IC table, the 1.95pp alpha margin,
the "62 suites". Here the source is on disk, so the copy can be checked against it.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import options_entry as OE                    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _log_row() -> str:
    body = open(os.path.join(ROOT, "RESEARCH_LOG.md"), encoding="utf-8").read()
    rows = [l for l in body.split("\n") if l.startswith("| O16-REFROZEN ")]
    assert len(rows) == 1, f"expected exactly one O16-REFROZEN row, found {len(rows)}"
    return rows[0]


def test_the_carry_forward_record_exists_and_says_it_was_not_run():
    rec = OE.MA56_CARRY_FORWARD
    assert "ts_resid" in rec["feature"]
    assert "RECORD ONLY" in rec["status"]
    assert "zero trials" in rec["status"]
    assert "R2" in rec["blocked_on"]


def test_the_recorded_figures_match_the_research_log_row():
    """The record must be checkable against its source, not taken on trust."""
    row = _log_row()
    rec = OE.MA56_CARRY_FORWARD
    # residual IC +0.07034 [+0.0287, +0.1131]; raw +0.05673 [+0.0206, +0.0922];
    # -atm_front +0.01316 [-0.0333, +0.0626]
    for val in (rec["residual_ic"], rec["parent_ic"], rec["atm_front_ic"]):
        assert f"{val:+.5f}".lstrip("+") in row or f"{val:.5f}" in row, val
    for lo, hi in (rec["residual_ci95"], rec["parent_ci95"]):
        assert f"{lo:+.4f}" in row and f"{hi:+.4f}" in row, (lo, hi)
    assert rec["residual_ic"] > rec["parent_ic"] > rec["atm_front_ic"], rec
    # the parent's own CI excludes zero, the atm_front leg's does not - the dissociation
    assert rec["parent_ci95"][0] > 0
    assert rec["atm_front_ci95"][0] < 0 < rec["atm_front_ci95"][1]


def test_the_three_caveats_the_audit_summary_omits_are_recorded_in_the_source():
    """A one-line summary that drops the caveats is how a sorted-losing-book becomes 'it works'."""
    src = open(os.path.join(ROOT, "valuation/edge/options_entry.py"), encoding="utf-8").read()
    # anchored on the HEADER, not on the bare token: the first cut split on "MA56" and landed in
    # the two-line gap before the caveats, so it failed against a source that already had them.
    block = src.split("# ---- MA56")[1].split("ENTRY_START")[0]
    assert "R2" in block and "-5.0640" in block, "the book it was measured on must be named"
    assert "Pearson" in block and "OPPOSITE" in block, "the estimator dependence must be named"
    assert "NOT blind" in block or "not blind" in block.lower(), "the non-blindness must be named"


def test_nothing_computes_ts_resid_for_a_verdict():
    """MA56's kill condition is 'do not run today'. Running it would breach the audit's own row."""
    hits = []
    for base, _dirs, files in os.walk(os.path.join(ROOT, "valuation")):
        if "__pycache__" in base:
            continue
        for fn in files:
            if not fn.endswith(".py"):
                continue
            p = os.path.join(base, fn)
            body = open(p, encoding="utf-8", errors="replace").read()
            # a DEFINITION of the feature, not a mention of the name in prose
            for m in re.finditer(r"^\s*(?:ts_resid|MA56_RESID)\s*=", body, re.M):
                hits.append(f"{os.path.relpath(p, ROOT)}:{body[:m.start()].count(chr(10)) + 1}")
    assert not hits, f"MA56 says do not run it; found a computation at {hits}"


def test_the_register_names_quoting_MA56_as_tested_a_void_condition():
    p = os.path.join(ROOT, "PREREG_ma31_ma32_parity_openclose.md")
    body = open(p, encoding="utf-8").read()
    void = body.split("## 5. Void conditions")[1].split("## 6.")[0]
    assert "MA56" in void and "record only" in void


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
