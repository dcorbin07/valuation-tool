"""O21-D2, pinned.  [the arm charges 1 options trial; these tests charge none]

What has to hold, and each is a defect this project has already paid for at least once:

  * the two passes may NOT run together, and `--arms` REFUSES without a passing controls
    artifact. A gating control computed in the same pass as the outcomes cannot be claimed to
    have been read first (session 26's defect, repaired in O19);
  * the arm reads the PINNED harvest and never the mutable `data/options`;
  * resolution is LAZY — CI has no `D:` drive, so resolving at module import would take the
    whole suite down on every machine without the freeze;
  * the harvest resolver RAISES on every unusable state rather than falling back, and has NO
    mutable opt-out at all, because the harvest's unfrozen twin has no legitimate reader;
  * a zero-row arm RAISES rather than writing a plausible coverage null (MA31's failure mode,
    and DEEPITM-FIN's own repeat of it);
  * the bar is O21's, reused verbatim rather than invented, and the bound that makes the verdict
    readable is arithmetic rather than prose;
  * bars resolution tests POPULATION, and the settlement path never reaches the network.

Offline: every filesystem case is a temp dir. The one group touching the real freeze SKIPS
loudly when it is not mounted.
"""
from __future__ import annotations

import ast
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

from valuation.edge import chain_store as CS  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "scripts", "o21d2_alternative_pnl.py")
REGISTER = os.path.join(REPO, "PREREG_o21d2_alternative_contract_pnl.md")


def _src():
    with open(SCRIPT, encoding="utf-8") as fh:
        return fh.read()


def _tree():
    return ast.parse(_src())


class _Env:
    def __init__(self, **kw):
        self.kw, self.old = kw, {}

    def __enter__(self):
        for k, v in self.kw.items():
            self.old[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return self

    def __exit__(self, *a):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _fake_harvest(tmp, n_dirs=500, populate=True, **over):
    root = os.path.join(tmp, "harvest")
    opt = os.path.join(root, "options")
    os.makedirs(opt, exist_ok=True)
    for i in range(n_dirs):
        d = os.path.join(opt, "T%04d" % i)
        os.makedirs(d, exist_ok=True)
        if populate:
            with open(os.path.join(d, "T%04d-2018.pkl" % i), "wb") as fh:
                fh.write(b"x")
    s = {"schema": 1, "kind": "chain_store_freeze", "source": "D:/thetadata/chains",
         "generated_utc": "2026-08-18T10:28:29+00:00", "files_recorded": 1865,
         "payload_units": 1865, "bytes": 1, "hash_mismatches_at_copy": 0,
         "n_source_files_not_yet_frozen": 0}
    s.update(over)
    with open(os.path.join(root, "FREEZE_SUMMARY.json"), "w", encoding="utf-8") as fh:
        json.dump(s, fh)
    with open(os.path.join(root, "manifest.jsonl"), "w", encoding="utf-8") as fh:
        fh.write('{"rel": "T0000/T0000-2018.pkl"}\n')
    return root



def _same_path(a: str, b: str) -> bool:
    """Separator- and case-insensitive path comparison, MB42.

    `os.path.normcase`/`normpath` are NOT enough: on POSIX a backslash is an ordinary filename
    character, so a Windows path compared on Linux normalises to itself and the two spellings
    still differ. Folding the separator explicitly makes the assertion mean the same thing on
    both platforms, which is the whole point of the fix.
    """
    def norm(x):
        return str(x).replace("\\", "/").rstrip("/").lower()
    return norm(a) == norm(b)

def _raises(fn, exc=CS.ChainStoreError):
    try:
        fn()
    except exc:
        return True
    except Exception as e:                                           # noqa: BLE001
        raise AssertionError("wrong exception: %r" % (e,))
    raise AssertionError("did not raise")


# ------------------------------------------------------- the harvest resolver raises, always
def test_a_missing_harvest_freeze_raises_and_has_no_mutable_fallback():
    tmp = tempfile.mkdtemp()
    with _Env(**{CS.ENV_HARVEST_ROOT: os.path.join(tmp, "nope")}):
        assert _raises(CS.resolve_harvest)


def test_an_unpopulated_harvest_raises_because_existence_is_not_population():
    tmp = tempfile.mkdtemp()
    root = _fake_harvest(tmp, populate=False)
    with _Env(**{CS.ENV_HARVEST_ROOT: root}):
        assert _raises(CS.resolve_harvest)


def test_a_too_small_harvest_raises():
    tmp = tempfile.mkdtemp()
    root = _fake_harvest(tmp, n_dirs=10)
    with _Env(**{CS.ENV_HARVEST_ROOT: root}):
        assert _raises(CS.resolve_harvest)


def test_a_harvest_admitting_hash_mismatches_raises():
    tmp = tempfile.mkdtemp()
    root = _fake_harvest(tmp, hash_mismatches_at_copy=3)
    with _Env(**{CS.ENV_HARVEST_ROOT: root}):
        assert _raises(CS.resolve_harvest)


def test_an_incomplete_harvest_raises():
    tmp = tempfile.mkdtemp()
    root = _fake_harvest(tmp, n_source_files_not_yet_frozen=7)
    with _Env(**{CS.ENV_HARVEST_ROOT: root}):
        assert _raises(CS.resolve_harvest)


def test_a_wrong_kind_harvest_raises():
    tmp = tempfile.mkdtemp()
    root = _fake_harvest(tmp, kind="something_else")
    with _Env(**{CS.ENV_HARVEST_ROOT: root}):
        assert _raises(CS.resolve_harvest)


def test_a_good_harvest_resolves_and_carries_a_fingerprint():
    tmp = tempfile.mkdtemp()
    root = _fake_harvest(tmp)
    with _Env(**{CS.ENV_HARVEST_ROOT: root}):
        d, prov = CS.resolve_harvest()
    assert d == os.path.join(root, "options")
    assert prov["source"] == "FROZEN_HARVEST" and prov["pinned"] is True
    # A NAMED artifact, not a floating label.
    assert len(prov["manifest_sha256"]) == 64
    assert prov["manifest_lines"] == 1


def test_the_harvest_resolver_offers_no_mutable_opt_out():
    """`resolve_chains` takes allow_mutable; `resolve_harvest` deliberately does not.

    The harvest's unfrozen twin is a miner scratch tree with no legitimate reader in an analysis
    path, and offering a door is how a door gets used.
    """
    import inspect
    sig = inspect.signature(CS.resolve_harvest)
    assert "allow_mutable" not in sig.parameters
    assert "allow_mutable" in inspect.signature(CS.resolve_chains).parameters


# ------------------------------------------------------------------- the two passes are two
def test_the_two_passes_may_not_run_in_one_invocation():
    import scripts.o21d2_alternative_pnl as M
    for argv in ([], ["--controls", "--arms"]):
        try:
            M.main(argv)
        except SystemExit as e:
            assert e.code != 0, "argparse must reject %r" % (argv,)
        else:
            raise AssertionError("should have exited on %r" % (argv,))


def test_arms_refuses_without_a_controls_artifact():
    """MUTATION-TESTED below: the refusal must be reachable, not merely written."""
    import scripts.o21d2_alternative_pnl as M
    old = M.CONTROLS_OUT
    try:
        M.CONTROLS_OUT = os.path.join(tempfile.mkdtemp(), "absent.json")
        assert M.run_arms() == 2
    finally:
        M.CONTROLS_OUT = old


def test_arms_refuses_when_the_controls_artifact_does_not_pass():
    """The mutation: flip `all_gating_pass` false and the arm must exit 2, not run anyway."""
    import scripts.o21d2_alternative_pnl as M
    tmp = tempfile.mkdtemp()
    p = os.path.join(tmp, "controls.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"all_gating_pass": False,
                   "c1_selection": {"pass": True},
                   "c2_null_instrument": {"pass": False, "reproduction_rate": 0.4,
                                          "n_coverable_non_divergent": 10},
                   "divergent": []}, fh)
    old = M.CONTROLS_OUT
    try:
        M.CONTROLS_OUT = p
        assert M.run_arms() == 2
    finally:
        M.CONTROLS_OUT = old


# --------------------------------------------------------------- the source it may not read
def test_the_arm_never_builds_the_mutable_options_path():
    src = _src()
    assert 'join(DATA, "options")' not in src
    assert "resolve_chains" not in src, "this arm reads the HARVEST, not the options store"
    assert "resolve_harvest" in src


def test_resolution_is_lazy_because_ci_has_no_d_drive():
    """No module-level call to resolve_harvest — importing must not need the freeze mounted."""
    for node in _tree().body:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                if sub.func.attr == "resolve_harvest" and isinstance(node,
                                                                     (ast.Assign, ast.Expr)):
                    raise AssertionError("resolve_harvest is called at module level")


def test_the_settlement_path_never_reaches_the_network():
    """S23 valued 1999 with LIVE Yahoo prices. `load_bars_offline` reads a cache or returns None.

    Pinned on the AST rather than by grep, because the words appear in the docstring explaining
    exactly this — the MA49(c) defect, where a fixture failed against the FIXED tree because the
    comment quoted the bug.
    """
    tree = _tree()
    fn = [n for n in tree.body
          if isinstance(n, ast.FunctionDef) and n.name == "load_bars_offline"]
    assert fn, "load_bars_offline is missing"
    for sub in ast.walk(fn[0]):
        if isinstance(sub, ast.Attribute):
            assert sub.attr not in ("get", "post") or not isinstance(sub.value, ast.Name) \
                or sub.value.id != "requests"
        if isinstance(sub, (ast.Import, ast.ImportFrom)):
            raise AssertionError("load_bars_offline imports something; it must only read a file")
    # and the shipped fetching loader is not used
    assert "OB.load_bars(" not in _src()


def test_a_zero_row_arm_raises_rather_than_writing_a_plausible_null():
    """MA31's failure mode: an empty input flowing downstream as a clean coverage null."""
    src = _src()
    assert "ZERO scored pairs" in src
    tree = _tree()
    fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_arms"][0]
    assert any(isinstance(s, ast.Raise) for s in ast.walk(fn)), "run_arms must be able to raise"


# ------------------------------------------------------------------------ the bar is O21's
def test_the_bar_is_o21s_own_and_is_not_reinvented():
    import scripts.o21d2_alternative_pnl as M
    assert M.MATERIAL_BOOK_PP == 1.00
    with open(os.path.join(REPO, "PREREG_o21_dividends.md"), encoding="utf-8") as fh:
        assert "MATERIALITY BAR" in fh.read()


def test_the_bound_that_makes_the_verdict_readable_is_arithmetic():
    """4.63% of the book means a 1.00pp book effect needs a 21.6pp per-trade mean.

    Quoting a mean difference without this bar invites reading 5pp as large when it is 0.23pp of
    book expectancy.
    """
    import scripts.o21d2_alternative_pnl as M
    share = M.N_DIVERGENT_EXPECTED / M.N_BOOK
    required = M.MATERIAL_BOOK_PP / share
    assert abs(required - 21.62) < 0.01, required


def test_the_register_exists_and_is_cited():
    """MA-class: a register citation is checkable only if the file is asserted to be on disk."""
    assert os.path.isfile(REGISTER)
    assert "PREREG_o21d2_alternative_contract_pnl.md" in _src()


def test_the_divergent_count_is_pinned_to_o21s():
    """Re-deriving the set by any other route, or quoting another count, is a void condition."""
    import scripts.o21d2_alternative_pnl as M
    assert M.N_DIVERGENT_EXPECTED == 179
    assert M.N_BOOK == 3870


def test_c2_has_a_floor_and_it_gates():
    import scripts.o21d2_alternative_pnl as M
    assert M.C2_FLOOR == 0.95
    assert "UNINTERPRETABLE" in _src()


# ------------------------------------------------------------------ the real freeze, if mounted
def test_the_real_harvest_freeze_resolves_when_mounted():
    if not os.path.isdir(CS.harvest_root()):
        print("SKIP: harvest freeze not mounted at %s" % CS.harvest_root())
        return
    d, prov = CS.resolve_harvest()
    assert prov["pinned"] is True
    # MB42. This used to be `== "D:/thetadata/chains"`. The freeze summary spells the source with
    # BACKSLASHES, so the literal was red on the only machine that owns the data while the CI
    # runner - which has no D: drive - skipped the whole test and the auto-land Action stayed
    # green. Compared separator-insensitively now; `_same_path` is exercised on every platform by
    # the fixture test below, so this is not the only place the comparison runs.
    assert _same_path(prov["frozen_from"], "D:/thetadata/chains"), prov["frozen_from"]
    assert prov["hash_mismatches_at_copy"] == 0
    assert len(prov["manifest_sha256"]) == 64


def test_the_frozen_from_comparison_runs_on_every_platform():
    """MB42's kill condition: normalising is not enough if the comparison still only runs on one
    platform. This builds a freeze whose summary spells the source the way the real one does -
    with BACKSLASHES - and asserts the resolver's provenance matches the forward-slash spelling.

    It uses a temp dir, so it executes on Linux and Windows alike. The mounted test above skips
    without a D: drive; this one never skips.
    """
    tmp = tempfile.mkdtemp()
    root = _fake_harvest(tmp, source="D:\\thetadata\\chains")
    with _Env(**{CS.ENV_HARVEST_ROOT: root}):
        _d, prov = CS.resolve_harvest()
    assert prov["frozen_from"] == "D:\\thetadata\\chains"
    assert _same_path(prov["frozen_from"], "D:/thetadata/chains")
    # and it must still be able to tell genuinely different paths apart
    assert not _same_path(prov["frozen_from"], "D:/thetadata/other")


def test_the_path_comparison_is_not_vacuous():
    """A comparison that returns True for everything would make the test above meaningless."""
    assert _same_path("D:\\a\\b", "D:/a/b")
    assert _same_path("D:/a/b/", "d:\\A\\B")
    assert not _same_path("D:/a/b", "D:/a/c")
    assert not _same_path("", "D:/a")


if __name__ == "__main__":
    # RUN_RULES line 25 runs each suite as its own process: `python tests/test_*.py`.
    # WITHOUT THIS BLOCK THE FILE WOULD EXIT 0 HAVING RUN NOTHING - a vacuous pass, which is the
    # failure class this project keeps finding in its own guards.
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
