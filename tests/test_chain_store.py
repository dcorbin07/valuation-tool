"""The chain-store resolver, pinned.  [zero trials — infrastructure, no hypothesis]

What has to hold, and each of these is a defect this project has already paid for once:

  * the MUTABLE store is an explicit opt-out and NEVER a silent fallback. A resolver that fell
    back when the pin was missing would reintroduce the drift it exists to remove, invisibly,
    while the run still claimed to be pinned;
  * EXISTENCE IS NOT POPULATION. DEEPITM-FIN resolved a path with os.path.exists, picked an
    EMPTY directory over a populated one and reported zero rows;
  * resolution is LAZY. Tests import these scripts and CI has no D: drive, so resolving at
    module import would take the whole suite down on every machine without the freeze;
  * and the provenance names a FINGERPRINT, not a floating label, so a future reader can tell
    whether they are looking at the same bytes.

These run offline: every filesystem case is built in a temp dir. Only the last group touches the
real freeze and it SKIPS (loudly) when the freeze is not mounted.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

from valuation.edge import chain_store as CS  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _Env:
    """Restore the environment whatever happens — a leaked var would poison later tests."""

    def __init__(self, **kw):
        self.kw = kw
        self.old = {}

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


def _fake_freeze(tmp, n_dirs=600, populate=True, **summary_over):
    root = os.path.join(tmp, "freeze")
    opt = os.path.join(root, "options")
    os.makedirs(opt, exist_ok=True)
    for i in range(n_dirs):
        d = os.path.join(opt, "T%04d" % i)
        os.makedirs(d, exist_ok=True)
        if populate:
            with open(os.path.join(d, "T%04d-2024.pkl" % i), "wb") as fh:
                fh.write(b"x")
    summary = {"schema": 1, "kind": "chain_store_freeze", "generated_utc": "2026-08-17T22:52:00+00:00",
               "files_recorded": 12302, "payload_units": 5063, "bytes": 1,
               "hash_mismatches_at_copy": 0, "n_source_files_not_yet_frozen": 0,
               "source": "whatever"}
    summary.update(summary_over)
    with open(os.path.join(root, "FREEZE_SUMMARY.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh)
    with open(os.path.join(root, "manifest.jsonl"), "w", encoding="utf-8") as fh:
        fh.write('{"rel": "T0000/T0000-2024.pkl"}\n')
    return root


def _raises(fn, exc=CS.ChainStoreError):
    try:
        fn()
    except exc:
        return True
    except Exception as e:                                           # noqa: BLE001
        raise AssertionError("wrong exception: %r" % (e,))
    raise AssertionError("did not raise")


# ------------------------------------------------------------------ the fallback is the defect
def test_a_missing_freeze_raises_rather_than_falling_back_to_the_mutable_store():
    tmp = tempfile.mkdtemp()
    data = os.path.join(tmp, "data")
    os.makedirs(os.path.join(data, "options"), exist_ok=True)
    with _Env(**{CS.ENV_MODE: None, CS.ENV_FREEZE_ROOT: os.path.join(tmp, "nope")}):
        assert _raises(lambda: CS.resolve_chains(data))


def test_an_unpopulated_freeze_raises_because_existence_is_not_population():
    tmp = tempfile.mkdtemp()
    root = _fake_freeze(tmp, n_dirs=600, populate=False)
    with _Env(**{CS.ENV_MODE: None, CS.ENV_FREEZE_ROOT: root}):
        assert _raises(lambda: CS.resolve_chains(os.path.join(tmp, "data")))


def test_a_freeze_with_too_few_ticker_dirs_raises():
    tmp = tempfile.mkdtemp()
    root = _fake_freeze(tmp, n_dirs=10)
    with _Env(**{CS.ENV_MODE: None, CS.ENV_FREEZE_ROOT: root}):
        assert _raises(lambda: CS.resolve_chains(os.path.join(tmp, "data")))


def test_a_freeze_that_admits_a_hash_mismatch_is_refused():
    tmp = tempfile.mkdtemp()
    root = _fake_freeze(tmp, hash_mismatches_at_copy=3)
    with _Env(**{CS.ENV_MODE: None, CS.ENV_FREEZE_ROOT: root}):
        assert _raises(lambda: CS.resolve_chains(os.path.join(tmp, "data")))


def test_an_incomplete_freeze_is_refused():
    tmp = tempfile.mkdtemp()
    root = _fake_freeze(tmp, n_source_files_not_yet_frozen=7)
    with _Env(**{CS.ENV_MODE: None, CS.ENV_FREEZE_ROOT: root}):
        assert _raises(lambda: CS.resolve_chains(os.path.join(tmp, "data")))


def test_a_directory_that_is_not_a_chain_store_freeze_is_refused():
    tmp = tempfile.mkdtemp()
    root = _fake_freeze(tmp, kind="something_else")
    with _Env(**{CS.ENV_MODE: None, CS.ENV_FREEZE_ROOT: root}):
        assert _raises(lambda: CS.resolve_chains(os.path.join(tmp, "data")))


# ------------------------------------------------------------------- the opt-out is explicit
def test_the_mutable_store_is_reachable_only_by_saying_so():
    tmp = tempfile.mkdtemp()
    data = os.path.join(tmp, "data")
    mut = os.path.join(data, "options")
    for i in range(600):
        d = os.path.join(mut, "T%04d" % i)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "T%04d-2024.pkl" % i), "wb") as fh:
            fh.write(b"x")
    with _Env(**{CS.ENV_MODE: None, CS.ENV_FREEZE_ROOT: os.path.join(tmp, "nope")}):
        path, prov = CS.resolve_chains(data, allow_mutable=True)
        assert prov["source"] == "MUTABLE"
        assert prov["pinned"] is False
        assert "explicit" in prov["opt_out"]
        assert "44.2%" in prov["warning"], "the opt-out must carry the drift warning"
        assert path == mut


def test_the_env_var_is_an_equally_explicit_opt_out():
    tmp = tempfile.mkdtemp()
    data = os.path.join(tmp, "data")
    mut = os.path.join(data, "options")
    for i in range(600):
        d = os.path.join(mut, "T%04d" % i)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "T%04d-2024.pkl" % i), "wb") as fh:
            fh.write(b"x")
    with _Env(**{CS.ENV_MODE: "mutable", CS.ENV_FREEZE_ROOT: os.path.join(tmp, "nope")}):
        _path, prov = CS.resolve_chains(data)
        assert prov["source"] == "MUTABLE"


def test_a_good_freeze_resolves_and_reports_a_fingerprint():
    tmp = tempfile.mkdtemp()
    root = _fake_freeze(tmp)
    with _Env(**{CS.ENV_MODE: None, CS.ENV_FREEZE_ROOT: root}):
        path, prov = CS.resolve_chains(os.path.join(tmp, "data"))
        assert prov["source"] == "FROZEN" and prov["pinned"] is True
        assert path == os.path.join(root, "options")
        assert len(prov["manifest_sha256"]) == 64
        assert prov["manifest_lines"] == 1


# ------------------------------------------------------------------------- laziness at import
def test_the_repointed_scripts_do_not_resolve_at_import_time():
    """CI has no D: drive. A module-level resolve would raise at import and kill the suite."""
    import ast
    for rel in ("scripts/o3_o4_o5_surface.py", "scripts/o6_o7_o17_earnings.py",
                "scripts/o11_o19_o22_o25_portfolio.py", "scripts/o14_tickflow_signals.py",
                "scripts/ma31_ma32_measure.py"):
        src = open(os.path.join(REPO, rel), encoding="utf-8").read()
        assert "_resolve_chains" in src, "%s does not use the shared resolver" % rel
        tree = ast.parse(src)
        for node in tree.body:                       # MODULE level only
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call) and getattr(sub.func, "id", "") == "_resolve_chains":
                    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        raise AssertionError("%s resolves the chain store at import time" % rel)


def test_no_repointed_script_still_builds_the_mutable_path_itself():
    for rel in ("scripts/o3_o4_o5_surface.py", "scripts/o6_o7_o17_earnings.py",
                "scripts/o11_o19_o22_o25_portfolio.py", "scripts/o14_tickflow_signals.py",
                "scripts/ma31_ma32_measure.py"):
        src = open(os.path.join(REPO, rel), encoding="utf-8").read()
        assert 'CHAINS = os.path.join(DATA, "options")' not in src, (
            "%s still hard-codes the mutable chain store" % rel)


def test_the_miner_is_not_repointed():
    """theta_bulk writes the store. Repointing it would send mining at a read-only freeze."""
    src = open(os.path.join(REPO, "valuation", "edge", "theta_bulk.py"), encoding="utf-8").read()
    assert "chain_store" not in src, "the miner must keep writing to the mutable store"


# ------------------------------------------------------------------------ the real freeze
def test_the_real_freeze_resolves_when_it_is_mounted():
    if not os.path.isdir(CS.freeze_root()):
        print("   (skipped — freeze not mounted on this machine)")
        return
    with _Env(**{CS.ENV_MODE: None}):
        _path, prov = CS.resolve_chains(os.path.join(REPO, "data"))
    assert prov["source"] == "FROZEN"
    assert prov["hash_mismatches_at_copy"] == 0
    assert prov["files_recorded"] == prov["manifest_lines"], (
        "the summary's file count and the manifest's line count disagree")


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
