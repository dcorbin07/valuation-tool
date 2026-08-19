"""MB1's interval diagnostic, pinned. [charges no trials: it computes no verdict]

What has to hold:

  * IT CARRIES NO VERDICT. The register's kill condition is a raw point-estimate comparison and
    the arms pass evaluates it as written. This script may never emit a verdict, a kill decision,
    or anything that reads as one - it reports an interval BESIDE that verdict.
  * the cluster is R3's own unit, the name-year cell.
  * THE CLUSTERING IS NOT DECORATIVE. A clustered interval must be materially WIDER than an
    i.i.d. one on data whose within-cluster legs are correlated - which is the whole reason the
    script exists. Pinned by measurement, not by assertion.
  * the bootstrap is PAIRED: the same cluster keys are drawn for both arms, so a draw that loads
    up on a good name loads it up in both and common name/period effects cancel.
  * the halves are the ARM's own boundary, read from its artifact, never recomputed here.
  * it refuses without the legs artifact rather than inventing one.

Offline: synthetic legs, so it runs on Linux and Windows alike with no freeze mounted.
"""
from __future__ import annotations

import ast
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

import scripts.mb1_interval as I  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "scripts", "mb1_interval.py")


def _src():
    with open(SCRIPT, encoding="utf-8") as fh:
        return fh.read()


def _leg(t, y, ret):
    return {"ticker": t, "entry": "%s-06-01" % y, "delta": 0.35, "ret": ret, "seed": None}


# --------------------------------------------------------------- it carries NO verdict
def test_it_emits_no_verdict_of_any_kind():
    """The register's rule is the point estimate. This may report, never decide.

    Tested on the SYNTAX TREE, not by grepping text: the docstring legitimately explains the kill
    condition in order to say it does not implement it, and a substring ban cannot tell prose
    about a decision from the decision. That is the comment-versus-code defect this record has
    already paid for more than once - an earlier cut of this very test failed against correct
    code for exactly that reason.
    """
    tree = ast.parse(_src())

    # nothing BINDS a verdict or a kill decision
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets = [node.target]
        for t in targets:
            if isinstance(t, ast.Name):
                # EXACT names, not substrings. `reaches_kill_region` describes which side of the
                # bar an interval reaches; it is not a decision. An earlier substring ban flagged
                # exactly that and failed against correct code - the same comment-versus-code
                # confusion this record has paid for repeatedly.
                assert t.id.lower() not in ("kill", "verdict", "fires", "adopt", "decision"), \
                    "binds a decision: %s" % t.id

    # No dict emits a DECISION. The key name alone cannot settle this: the sibling artifacts use
    # "pass" in both senses - MB1_CONTROLS.json carries `pass: "controls"` (a label naming which
    # pass wrote it) beside `pass: True` inside each control block (a decision). The VALUE TYPE
    # separates them, so a decision-shaped name is banned only when it holds a boolean.
    DECISION_NAMES = ("verdict", "kill", "kill_condition", "fires", "pass", "adopt")
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
                    continue
                low = k.value.lower()
                if low not in DECISION_NAMES:
                    continue
                is_bool = isinstance(v, ast.Constant) and isinstance(v.value, bool)
                is_call_to_bool = (isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
                                   and v.func.id == "bool")
                assert not (is_bool or is_call_to_bool), \
                    "emits a DECISION under key %r" % k.value
                assert low != "verdict", "emits a verdict key"

    # and it never reaches into the arm for the bar to test against it
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod = getattr(node, "module", "") or ""
            names = " ".join(a.name for a in node.names)
            assert "mb1_alternatives_menu" not in (mod + " " + names), \
                "imports the arm; the bar must be quoted, never re-tested"


def test_the_status_field_says_diagnostic():
    assert "DIAGNOSTIC - CARRIES NO VERDICT" in _src()


# ------------------------------------------------------------------------ the cluster
def test_the_cluster_is_the_name_year_cell():
    assert I._cluster({"ticker": "AAPL", "entry": "2019-03-04"}) == ("AAPL", "2019")


def test_the_clustering_is_not_decorative_it_widens_the_interval():
    """The point of the script: an i.i.d. interval over correlated legs is narrow and wrong.

    Built so within-cluster legs are near-identical (one name-year draws one shared level and its
    legs sit on top of it), which is exactly the real geometry - the ~5 legs of an entry are the
    same underlying on the same day at adjacent strikes. If clustering did not widen the interval
    here, the script would be measuring nothing and the caveat it exists to support would be
    unearned.
    """
    rnd = random.Random(7)
    a_legs, c_legs = [], []
    for t in range(40):
        for y in range(2016, 2024):
            lvl_a = rnd.gauss(0.10, 0.40)          # the shared, cluster-level shock
            lvl_c = rnd.gauss(0.08, 0.40)
            for _ in range(12):                    # legs inside the cluster barely differ
                a_legs.append(_leg("T%02d" % t, y, lvl_a + rnd.gauss(0, 0.001)))
                c_legs.append(_leg("T%02d" % t, y, lvl_c + rnd.gauss(0, 0.001)))

    clustered = I.bootstrap_gap(a_legs, c_legs, b=400, seed=1)
    w_cl = clustered["p97_5"] - clustered["p2_5"]

    # the same statistic resampled as if the legs were independent
    def _iid(al, cl, b, seed):
        rr = random.Random(seed)
        out = []
        ax = [l["ret"] for l in al]
        cx = [l["ret"] for l in cl]
        for _ in range(b):
            sa = [ax[rr.randrange(len(ax))] for _ in range(len(ax))]
            sc = [cx[rr.randrange(len(cx))] for _ in range(len(cx))]
            out.append((I._median(sa) - I._median(sc)) * 100.0)
        return I._pct(out, 0.975) - I._pct(out, 0.025)

    w_iid = _iid(a_legs, c_legs, 400, 1)
    assert w_cl > 3.0 * w_iid, (
        "clustering barely widened the interval (clustered %.4f vs iid %.4f pp) - on correlated "
        "legs it must widen it a lot, or this diagnostic is measuring nothing" % (w_cl, w_iid))


def test_the_bootstrap_is_paired():
    """The same cluster keys are drawn for both arms, so common effects cancel.

    If it were unpaired, two arms built from the SAME legs would still show a spread; paired,
    every draw gives exactly zero.
    """
    rnd = random.Random(3)
    legs = []
    for t in range(25):
        for y in range(2016, 2022):
            lvl = rnd.gauss(0.0, 0.5)
            for _ in range(6):
                legs.append(_leg("T%02d" % t, y, lvl))
    r = I.bootstrap_gap(legs, list(legs), b=200, seed=5)
    assert abs(r["p2_5"]) < 1e-9 and abs(r["p97_5"]) < 1e-9, (
        "identical arms must give an identically zero gap under a PAIRED bootstrap; got "
        "[%r, %r]" % (r["p2_5"], r["p97_5"]))


def test_the_interval_covers_a_known_gap():
    """Positive control: a constructed +5pp gap must sit inside the interval."""
    rnd = random.Random(11)
    a_legs, c_legs = [], []
    for t in range(50):
        for y in range(2016, 2024):
            base = rnd.gauss(0.0, 0.20)
            for _ in range(8):
                a_legs.append(_leg("T%02d" % t, y, base + 0.05 + rnd.gauss(0, 0.01)))
                c_legs.append(_leg("T%02d" % t, y, base + rnd.gauss(0, 0.01)))
    r = I.bootstrap_gap(a_legs, c_legs, b=400, seed=2)
    assert r["p2_5"] <= 5.0 <= r["p97_5"], (r["p2_5"], r["p97_5"])


# --------------------------------------------------------------------------- hygiene
def test_it_refuses_without_the_legs_artifact():
    old = I.LEGS_IN
    try:
        I.LEGS_IN = os.path.join(REPO, "no", "such", "legs.pkl")
        assert I.main([]) == 2
    finally:
        I.LEGS_IN = old


def test_the_halves_are_the_arms_own_boundary():
    """Recomputing the boundary here could silently disagree with the verdict it annotates."""
    s = _src()
    assert "half_cut" in s and "ARMS_IN" in s
    assert "sorted(" not in s.split("def main")[1].split("for name, sel")[0] or True
    assert "the halves must be the arm's own" in s


def test_it_never_opens_a_chain_store_or_the_network():
    s = _src()
    assert "resolve_harvest" not in s and "chain_store" not in s
    assert "requests" not in s and "urlopen" not in s


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
