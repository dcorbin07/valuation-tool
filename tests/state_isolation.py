"""Every test runs against TEMPORARY state, never the repository's real state (audit LA15).

WHAT THIS FIXES
---------------
`tests/test_saas.py` POSTed a `scan_date: "2099-01-01"` snapshot to `/admin/ingest-snapshot`
against a `Store()` that resolves to the repository's own `data/screener.db`. Because
`Store.latest_scan_date()` orders by `scan_date DESC`, a year-2099 fixture outranks every real
scan forever, so after one local test run every scan-derived surface — `/api/hotstocks`,
`/api/valquo-index`, `/api/whatdo`, the hero band — served the fixture as the latest scan.

Measured on this checkout before the fix, ONE run of `tests/test_saas.py` left SIX rows across
five tables plus a meta key, not the one snapshot row the audit named:

    meta            hot_processed_2099-01-01
    scans           2099-01-01
    snapshot_rows   TESTX @ 2099-01-01
    track_picks     hot10 / 2099-01-01 / TESTX
    positions       an OPEN hot10 paper position in TESTX at $10.00
    alerts_sent     __HOTDIGEST__ marked sent for the REAL calendar day the test ran

The last one is the row that is not merely cosmetic. `notify.post_hot_digest` skips when
`store.alerted_today("__HOTDIGEST__")`, and `mark_alerted` stamps *today*, not the scan date —
so running the suite on a box with a Discord webhook configured suppresses that day's real hot
digest. A test cannot be allowed to decide whether the product notifies its users.

Separately, and larger: `create_saas_app` binds `UserStore(cfg.database_url)`, which defaults to
`sqlite:///data/app.db`. Six suites build the app, and this checkout's real accounts database had
accumulated **69 user accounts** from test runs.

And a third leak the audit did not name, found by measuring rather than reading. `tests/
test_screener.py` calls `run_scan(..., save=True)` against a *temp* store — the author isolated
the database — but `screen.py` then calls `archive_scan(rows, scan_date, provider.name)` with no
root, and `archive.DEFAULT_ROOT` is the RELATIVE path `data/archive`, resolved against the cwd.
So the suite wrote `data/archive/scans/<today>.json.gz`, one synthetic day per calendar day the
suite was run. Measured on this checkout: **all five archived scan days were
`provider: "synthetic (offline test)"`, 100 `SYN*` rows each.** That directory is what
`scripts/theme_health.py` reads, so it is at least part of why the V2 theme-health meter reports
every archived scan day as synthetic. A relative default root is invisible from the call site,
which is why isolating the store was not enough — the same class as the miner's `data/options`
root already pinned in `tests/test_edge.py`.

HOW IT WORKS
------------
Importing this module, before anything that can construct a store:

  1. redirects the screener store, the accounts store and the index-track files into a
     per-process temp directory that is removed at exit;
  2. installs a TRIPWIRE — any store that still resolves inside the repository's real `data/`
     raises `RealStateTouched` instead of quietly opening it.

The tripwire is the part that matters. Redirection alone is silent when it fails; the failure
mode this file exists to prevent is precisely a silent one.

WHY A PLAIN MODULE AND NOT A PYTEST FIXTURE
-------------------------------------------
The auto-land Action runs `for f in tests/test_*.py; do python "$f"; done` — every suite is a
standalone script, so `conftest.py` and fixtures never execute. An import is the only hook that
is guaranteed to run in the harness this project actually uses.

ORDER MATTERS. Import this ABOVE the `valuation.*` imports in a test module. `create_saas_app`
is idempotent — it wraps one module-level Flask app and every later call returns that same app,
config and all — so a `database_url` changed after the first call changes nothing.

The rule is pinned by `tests/test_state_isolation.py`, which fails if a suite that can reach
default state forgets to import this.
"""
import atexit
import inspect
import os
import shutil
import sys
import tempfile

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(_TESTS_DIR)
REAL_DATA_DIR = os.path.join(REPO_ROOT, "data")

if REPO_ROOT not in sys.path:                      # suites run as standalone scripts
    sys.path.insert(0, REPO_ROOT)


class RealStateTouched(RuntimeError):
    """A test resolved a database inside the repository's real `data/` directory."""


_TMP_DIR = tempfile.mkdtemp(prefix="valquo-test-state-")
atexit.register(shutil.rmtree, _TMP_DIR, ignore_errors=True)

_applied = False


def temp_dir() -> str:
    return _TMP_DIR


def temp_path(name: str) -> str:
    return os.path.join(_TMP_DIR, name)


def under_real_data(path: str) -> bool:
    """True if `path` lives inside the repository's real data/ directory.

    `commonpath` raises on Windows when the two paths sit on different drives (a temp dir on
    another volume is the normal case), which is emphatically NOT a match — hence the catch.
    """
    if not path:
        return False
    try:
        return os.path.commonpath(
            [os.path.abspath(path), REAL_DATA_DIR]) == REAL_DATA_DIR
    except ValueError:
        return False


def _url_to_path(url: str) -> str:
    """`sqlite:///data/app.db` -> `data/app.db`. Anything else is returned unchanged."""
    if isinstance(url, str) and url.startswith("sqlite:///"):
        return url[len("sqlite:///"):]
    return url or ""


def _isolate_screener_store():
    """Redirect `Store()` and refuse any Store that still lands in the real data dir."""
    from valuation.screener import store as _store

    _store._DEFAULT_DB = temp_path("screener.db")

    real_init = _store.Store.__init__
    if getattr(real_init, "_la15_guarded", False):
        return

    def guarded_init(self, path=None):
        resolved = path or _store._DEFAULT_DB
        if under_real_data(resolved):
            raise RealStateTouched(
                f"test tried to open the REAL screener store at {resolved!r}. "
                "Use tests.state_isolation.temp_path(...) or pass an explicit temp path "
                "(audit LA15).")
        return real_init(self, resolved)

    guarded_init._la15_guarded = True
    _store.Store.__init__ = guarded_init


def _isolate_user_store():
    """Point the accounts DB at temp state BEFORE the first `create_saas_app` call."""
    from valuation.config import CONFIG
    from valuation.saas import models as _models

    CONFIG.database_url = "sqlite:///" + temp_path("app.db").replace("\\", "/")

    real_init = _models.UserStore.__init__
    if getattr(real_init, "_la15_guarded", False):
        return

    # `UserStore.__init__(self, database_url="sqlite:///data/app.db")` — the default IS the real
    # accounts DB, so a bare `UserStore()` must still be judged rather than passed through as
    # None. Keep the parameter's real name too: a caller using the keyword must not slip past.
    _default = inspect.signature(real_init).parameters["database_url"].default

    def guarded_init(self, database_url=_default, *a, **kw):
        if under_real_data(_url_to_path(database_url)):
            raise RealStateTouched(
                f"test tried to open the REAL accounts store at {database_url!r} "
                "(audit LA15).")
        return real_init(self, database_url, *a, **kw)

    guarded_init._la15_guarded = True
    _models.UserStore.__init__ = guarded_init


def _isolate_index_track_files():
    """Redirect the Cowork-maintained track files.

    `index_track.default_paths()` returns `data/valquo_track.json` and
    `valquo_track_history.csv` in the repository. Those are real forward-track records on a
    developer box and absent in CI, which is why the hero tests in `tests/test_paper_track.py`
    have been reported as "37/40 locally, 40/40 in CI" — the suite was reading a machine's own
    state. Pointing them at a temp directory makes a local run agree with CI.
    """
    from valuation.screener import index_track as _it

    if getattr(_it.default_paths, "_la15_guarded", False):
        return

    def guarded_default_paths():
        return (temp_path("valquo_track.json"), temp_path("valquo_track_history.csv"))

    guarded_default_paths._la15_guarded = True
    _it.default_paths = guarded_default_paths


def _isolate_archive_root():
    """Redirect the dated scan/intraday archive.

    `archive.DEFAULT_ROOT` is the RELATIVE path `data/archive`, and it is bound as a default
    argument at def time — so reassigning the module constant changes nothing. The functions
    themselves are wrapped instead, which also catches `screen.py`'s `archive_scan(rows,
    scan_date, provider.name)`, a call that names no root at all.
    """
    from valuation.edge import archive as _archive

    for fname in ("archive_scan", "archive_intraday"):
        real = getattr(_archive, fname)
        if getattr(real, "_la15_guarded", False):
            continue

        def guarded(*args, _real=real, **kwargs):
            # The root sits at a different position in each function, so bind by signature
            # rather than by counting arguments. A caller that names a root explicitly is
            # CHECKED, not silently replaced — a test asking for a specific path is usually
            # asserting something about that path.
            bound = inspect.signature(_real).bind(*args, **kwargs)
            root = bound.arguments.get("root")
            if root is None:
                kwargs["root"] = temp_path("archive")
            elif under_real_data(root):
                raise RealStateTouched(
                    f"test tried to write the REAL archive under {root!r} (audit LA15).")
            return _real(*args, **kwargs)

        guarded._la15_guarded = True
        setattr(_archive, fname, guarded)


def apply(index_track_files: bool = True):
    """Idempotent. Safe to call from every suite; the first call does the work."""
    global _applied
    _isolate_screener_store()
    _isolate_user_store()
    _isolate_archive_root()
    if index_track_files:
        _isolate_index_track_files()
    _applied = True
    return _TMP_DIR


def applied() -> bool:
    return _applied


apply()
