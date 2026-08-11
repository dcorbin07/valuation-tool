"""The rule: a test may not read or write the repository's REAL state (audit LA15).

    python tests/test_state_isolation.py

`tests/state_isolation.py` enforces the rule at runtime; this suite pins it. The half that keeps
it true a month from now is the sweep in `EverySuiteThatCanReachRealStateImportsTheGuard` — it
parses every other suite and fails if one can reach default state without importing the guard.
A rule that lives only in a docstring lasts until the next person writes a test.

THE FOUR ESCAPES ARE ENUMERATED, NOT INFERRED. Each was measured by fingerprinting `data/`
around a run of every suite, not guessed from reading code:

    create_saas_app(...)   binds UserStore(cfg.database_url) -> data/app.db
    Store() / UserStore()  no path -> data/screener.db, data/app.db
    run_scan(..., save)    screen.py archives to the RELATIVE default root data/archive
    live_hero(...)         index_track.default_paths() -> data/valquo_track.json + .csv

That list is deliberately a list of *known* escapes rather than a claim of completeness. The
runtime tripwire in `state_isolation` is the backstop for the ones nobody has thought of yet:
it raises rather than opening anything that resolves inside the real `data/`.
"""
import ast
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation as ISO   # noqa: E402  — MUST precede every `valuation` import

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
REAL_DATA = os.path.join(REPO_ROOT, "data")

_SELF = {"test_state_isolation.py"}


def _fp(p):
    try:
        st = os.stat(p)
        return (st.st_size, round(st.st_mtime, 3))
    except OSError:
        return None


# Captured at import, i.e. before any test body runs.
_REAL_DBS = (os.path.join(REAL_DATA, "screener.db"), os.path.join(REAL_DATA, "app.db"))
_BASELINE = {p: _fp(p) for p in _REAL_DBS}
_TODAY_ARCHIVE = os.path.join(REAL_DATA, "archive", "scans",
                              datetime.date.today().isoformat() + ".json.gz")
_ARCHIVE_BASELINE = {_TODAY_ARCHIVE: _fp(_TODAY_ARCHIVE)}


# --------------------------------------------------------------------------------------- #
class TheDefaultStoresAreRedirectedIntoTempSpace(unittest.TestCase):

    def test_a_bare_store_does_not_land_in_the_repository(self):
        from valuation.screener.store import Store
        st = Store()
        self.assertFalse(ISO.under_real_data(st.path), st.path)
        self.assertTrue(os.path.abspath(st.path).startswith(
            os.path.abspath(ISO.temp_dir())))

    def test_the_accounts_url_points_at_temp_space_before_any_app_is_built(self):
        from valuation.config import CONFIG
        self.assertIn(ISO.temp_dir().replace("\\", "/"), CONFIG.database_url)
        self.assertFalse(ISO.under_real_data(ISO._url_to_path(CONFIG.database_url)))

    def test_the_index_track_files_are_redirected(self):
        """`data/valquo_track.json` is real forward-track state on a developer box and absent
        in CI, which is why the hero tests have read as 37/40 locally and 40/40 in CI."""
        from valuation.screener import index_track
        for p in index_track.default_paths():
            self.assertFalse(ISO.under_real_data(p), p)

    def test_an_unrooted_archive_write_lands_in_temp_space(self):
        """`screen.py` calls `archive_scan(rows, scan_date, provider.name)` with no root, and
        the default root is RELATIVE — invisible from the call site, so isolating the store
        was not enough."""
        from valuation.edge.archive import archive_scan
        p = archive_scan([{"ticker": "X", "rank": 1}], "2026-01-02", "unit")
        self.assertIsNotNone(p)
        self.assertFalse(ISO.under_real_data(p), p)

    def test_an_explicitly_rooted_archive_write_is_honoured_not_hijacked(self):
        """A test that names a root is usually asserting something about that root."""
        import tempfile
        from valuation.edge.archive import archive_scan
        root = tempfile.mkdtemp()
        p = archive_scan([{"ticker": "X"}], "2026-01-02", "unit", root=root)
        self.assertTrue(p.startswith(root), p)

    def test_the_temp_directory_belongs_to_this_process_alone(self):
        self.assertIn("valquo-test-state-", os.path.basename(ISO.temp_dir()))
        self.assertTrue(os.path.isdir(ISO.temp_dir()))

    def test_applying_twice_is_a_no_op_and_does_not_double_wrap(self):
        from valuation.screener.store import Store
        before = Store().path
        ISO.apply()
        ISO.apply()
        self.assertEqual(Store().path, before)


# --------------------------------------------------------------------------------------- #
class TheTripwireRefusesTheRealState(unittest.TestCase):
    """Redirection alone fails SILENTLY. The tripwire is what makes a miss loud."""

    def test_an_explicit_real_screener_path_raises(self):
        from valuation.screener.store import Store
        with self.assertRaises(ISO.RealStateTouched):
            Store(os.path.join(REAL_DATA, "screener.db"))

    def test_an_explicit_real_accounts_url_raises(self):
        from valuation.saas.models import UserStore
        url = "sqlite:///" + os.path.join(REAL_DATA, "app.db").replace("\\", "/")
        with self.assertRaises(ISO.RealStateTouched):
            UserStore(url)

    def test_a_bare_user_store_raises_rather_than_opening_its_real_default(self):
        """`UserStore.__init__`'s own default IS `sqlite:///data/app.db`, so a bare call must be
        judged, not passed through — the guard keeps the real default instead of None."""
        from valuation.saas.models import UserStore
        with self.assertRaises(ISO.RealStateTouched):
            UserStore()

    def test_the_keyword_spelling_cannot_slip_past(self):
        """The wrapper must keep the parameter's real name (`database_url`), or a caller using
        the keyword lands in **kwargs and is never checked."""
        from valuation.saas.models import UserStore
        url = "sqlite:///" + os.path.join(REAL_DATA, "app.db").replace("\\", "/")
        with self.assertRaises(ISO.RealStateTouched):
            UserStore(database_url=url)

    def test_an_explicit_real_archive_root_raises(self):
        from valuation.edge.archive import archive_scan
        with self.assertRaises(ISO.RealStateTouched):
            archive_scan([{"ticker": "X"}], "2026-01-02", "unit",
                         root=os.path.join(REAL_DATA, "archive"))

    def test_the_refusal_names_the_audit_item(self):
        from valuation.screener.store import Store
        with self.assertRaises(ISO.RealStateTouched) as cm:
            Store(os.path.join(REAL_DATA, "screener.db"))
        self.assertIn("LA15", str(cm.exception))

    def test_the_refusal_happens_before_the_file_is_created(self):
        """`Store.__init__` makedirs and executescript, so a guard that fired late would
        still have created the thing it refused."""
        victim = os.path.join(REAL_DATA, "tripwire_probe.db")
        from valuation.screener.store import Store
        with self.assertRaises(ISO.RealStateTouched):
            Store(victim)
        self.assertFalse(os.path.exists(victim), "the guard created the file it refused")

    def test_a_temp_path_is_still_allowed(self):
        from valuation.screener.store import Store
        self.assertIsNone(Store(ISO.temp_path("explicit.db")).latest_scan_date())

    def test_under_real_data_survives_a_different_drive(self):
        """`commonpath` raises across Windows drives; that is a NON-match, not a crash."""
        self.assertFalse(ISO.under_real_data("Z:\\elsewhere\\screener.db"))
        self.assertFalse(ISO.under_real_data(""))
        self.assertTrue(ISO.under_real_data(os.path.join(REAL_DATA, "screener.db")))

    def test_a_relative_path_is_resolved_before_it_is_judged(self):
        """`data/archive` is how the leak was actually spelled — relative, not absolute."""
        keep = os.getcwd()
        try:
            os.chdir(REPO_ROOT)
            self.assertTrue(ISO.under_real_data(os.path.join("data", "screener.db")))
        finally:
            os.chdir(keep)


# --------------------------------------------------------------------------------------- #
def _suite_files():
    return sorted(f for f in os.listdir(TESTS_DIR)
                  if f.startswith("test_") and f.endswith(".py") and f not in _SELF)


def _reaching_calls(tree):
    """Calls that resolve to the repository's real state when given no explicit path.

    AST, not grep: `tests/test_intraday.py` asserts on the SOURCE TEXT
    `"open_alerts(Store(), limit=limit)"` inside a string literal, and a textual sweep would
    flag that line forever without a single real store behind it.
    """
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
        kw = {k.arg: k.value for k in node.keywords if k.arg}
        if name == "create_saas_app":
            hits.append("create_saas_app")
        elif name in ("Store", "UserStore") and not node.args and not node.keywords:
            hits.append(name + "()")
        elif name == "live_hero":
            hits.append("live_hero")
        elif name == "run_scan":
            save = kw.get("save")
            if not (isinstance(save, ast.Constant) and save.value is False):
                hits.append("run_scan")
    return hits


def _guard_import_line(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name.split(".")[-1] == "state_isolation" for a in node.names):
                return node.lineno
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[-1] == "state_isolation":
                return node.lineno
            if any(a.name == "state_isolation" for a in node.names):
                return node.lineno
    return None


def _first_valuation_import_line(tree):
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            lines += [node.lineno for a in node.names
                      if a.name.split(".")[0] == "valuation"]
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] == "valuation":
                lines.append(node.lineno)
    return min(lines) if lines else None


def _parse(fname):
    with open(os.path.join(TESTS_DIR, fname), encoding="utf-8") as fh:
        return ast.parse(fh.read())


class EverySuiteThatCanReachRealStateImportsTheGuard(unittest.TestCase):

    def test_the_sweep_is_not_vacuous(self):
        """A sweep that inspects zero files, or finds zero candidates, passes for the wrong
        reason — which is the failure mode this whole audit item is about."""
        files = _suite_files()
        self.assertGreaterEqual(len(files), 30, files)
        reaching = [f for f in files if _reaching_calls(_parse(f))]
        self.assertGreaterEqual(len(reaching), 5, reaching)

    def test_no_suite_reaches_default_state_without_importing_the_guard(self):
        offenders = []
        for f in _suite_files():
            tree = _parse(f)
            calls = _reaching_calls(tree)
            if calls and _guard_import_line(tree) is None:
                offenders.append((f, sorted(set(calls))))
        self.assertEqual(offenders, [], (
            "these suites can reach the repository's real state and do not import "
            "tests/state_isolation.py (audit LA15): " + repr(offenders)))

    def test_the_guard_is_imported_above_the_valuation_imports(self):
        """`create_saas_app` is idempotent — it wraps one module-level Flask app and every
        later call returns that same app, config and all — so a `database_url` changed after
        the first call changes nothing at all."""
        late = []
        for f in _suite_files():
            tree = _parse(f)
            g, v = _guard_import_line(tree), _first_valuation_import_line(tree)
            if g is not None and v is not None and g > v:
                late.append((f, "guard@%d" % g, "valuation@%d" % v))
        self.assertEqual(late, [], "guard imported below a valuation import: " + repr(late))

    def test_a_forgetful_suite_is_actually_caught(self):
        bad = ast.parse("from valuation.screener.store import Store\n"
                        "def test_x():\n    Store().latest_scan_date()\n")
        self.assertEqual(_reaching_calls(bad), ["Store()"])
        self.assertIsNone(_guard_import_line(bad))

    def test_each_of_the_four_measured_escapes_is_detected(self):
        for src, want in (
                ("create_saas_app(CONFIG)", "create_saas_app"),
                ("Store()", "Store()"),
                ("run_scan(scope='synthetic', store=st, save=True)", "run_scan"),
                ("live_hero(st)", "live_hero")):
            self.assertEqual(_reaching_calls(ast.parse(src)), [want], src)

    def test_a_scan_that_does_not_save_is_not_flagged(self):
        """`save=False` never reaches `archive_scan`, so it cannot leak."""
        self.assertEqual(_reaching_calls(ast.parse("run_scan(store=st, save=False)")), [])
        self.assertEqual(_reaching_calls(ast.parse("run_scan(store=st, save=flag)")),
                         ["run_scan"], "a non-literal save must be treated as saving")

    def test_a_guarded_suite_is_recognised_in_every_import_spelling(self):
        for src in ("import state_isolation\ncreate_saas_app()\n",
                    "from tests import state_isolation\ncreate_saas_app()\n",
                    "from state_isolation import apply\ncreate_saas_app()\n"):
            t = ast.parse(src)
            self.assertEqual(_guard_import_line(t), 1, src)
            self.assertEqual(_reaching_calls(t), ["create_saas_app"])

    def test_a_store_with_an_explicit_path_is_not_flagged(self):
        self.assertEqual(_reaching_calls(ast.parse(
            "Store(tmp)\nUserStore('sqlite:///' + p)\nStore(path=q)\n")), [])

    def test_a_store_call_inside_a_string_is_not_flagged(self):
        self.assertEqual(_reaching_calls(ast.parse(
            'assert "open_alerts(Store(), limit=limit)" in src\n')), [])


# --------------------------------------------------------------------------------------- #
class ThisRunLeavesTheRealStateExactlyAsItFoundIt(unittest.TestCase):
    """The end-to-end assertion. Everything above is mechanism; this is the outcome."""

    def test_no_real_database_was_created_or_modified(self):
        for p in _REAL_DBS:
            was, now = _BASELINE[p], _fp(p)
            if was is None:
                self.assertIsNone(now, os.path.basename(p) + " was CREATED by the suite")
            else:
                self.assertEqual(now, was, os.path.basename(p) + " changed during the run")

    def test_no_archive_day_was_written_for_today(self):
        self.assertEqual(_fp(_TODAY_ARCHIVE), _ARCHIVE_BASELINE[_TODAY_ARCHIVE],
                         "the suite wrote a synthetic scan day into the real archive")

    def test_the_baseline_was_captured_before_any_test_ran(self):
        self.assertEqual(set(_BASELINE), set(_REAL_DBS))


if __name__ == "__main__":
    unittest.main(verbosity=2)
