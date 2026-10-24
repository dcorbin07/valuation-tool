# -*- coding: utf-8 -*-
"""ITEM 80b — the door could not find the row the site was serving.

**MEASURED 2026-10-23 ~10:55pm ET, same rebalance as item 80.** With the conformance refusal
gone, Don's re-send hit the next one:

    HTTP 422  2026-10-22 has no recorded row, so a rebalance anchored there has no level to
              compound onto

while `https://valquo.co/api/index-track` was serving that exact row as the last point of its
series: `{"date":"2026-10-22","valquo":1.4735,"spy":3.2584,...}`.

**TWO CAUSES, BOTH VERIFIED IN THE SOURCE RATHER THAN TAKEN FROM THE BRIEF.**

1. `append_rebalance` defaulted ONLY `meta_path` -- `meta_path, _h = default_paths()` threw the
   history path away -- so `history_path` stayed `None`, `_read_history(None)` did
   `open(None, "rb")`, the `TypeError` landed in the generic `except`, and the returned dict had
   **no `rows` key at all**. Every recorded-row question read an empty series. **The refusal was
   reading a file it had never been given the name of.**
2. On a deploy the recorded series can live in the STORE rather than the CSV -- `data/` is
   gitignored, and `index_track._unpriced_block`'s own note already said *"the live service
   holds the record in its STORE rather than in the CSV `index_mark` would otherwise read"*.
   Nothing in `index_mark` acted on it.

**AND A THIRD, LATENT, FOUND BY GREPPING THE OTHER CALLER RATHER THAN BY HITTING IT: the DAILY
WRITER had the same hole.** `/admin/track-row` calls `contract_row(date)` with no path, and
`contract_row`'s anchor branch runs ONLY once a rebalance exists -- the record had zero events,
so it had never fired. **The moment the 2026-10-22 event was recorded, the writer would have
refused every row from then on**, silently stopping the forward record the operational gate
depends on.

Nothing here contacts a network. Every path writes inside a temporary directory.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401  — temp state only. Import BEFORE `valuation`.

from valuation.config import CONFIG                    # noqa: E402
from valuation.edge import valquo_index as VI           # noqa: E402
from valuation.saas.app_saas import create_saas_app     # noqa: E402
from valuation.screener import index_mark as IM         # noqa: E402
from valuation.screener import index_track as IT        # noqa: E402

N_OK = VI.CONTRACT_MIN_POSITIONS + 31      # 81, Don's own book size
DATE = "2026-10-22"


def _positions(n=N_OK):
    return [{"ticker": "T%03d" % i, "weight": 1.0 / n} for i in range(n)]


def _event(date=DATE, scan=DATE):
    return {"date": date, "scan_date": scan, "positions": _positions()}


def _book(events=()):
    return {"inception_date": "2026-07-30", "positions": _positions(),
            "rebalances": list(events)}


#: The recorded series in the STORE's own vocabulary -- `valquo`/`spy`, which is what
#: `index_track.from_store` emits and is NOT what this module's readers expect.
def _store_series(dates=("2026-10-21", DATE)):
    return [{"date": d, "valquo": 1.0814, "spy": 3.0026, "excess": -1.9212, "n_priced": 85}
            for d in dates]


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="i80b_")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.meta = os.path.join(self.root, "valquo_track.json")
        self.hist = os.path.join(self.root, "valquo_track_history.csv")
        self._real_paths = IT.default_paths
        self.addCleanup(lambda: setattr(IT, "default_paths", self._real_paths))
        IT.default_paths = lambda: (self.meta, self.hist)

    def _write_book(self, events=()):
        with io.open(self.meta, "w", encoding="utf-8") as fh:
            json.dump(_book(events), fh)

    def _write_csv(self, dates=("2026-10-21", DATE)):
        with io.open(self.hist, "w", encoding="utf-8", newline="") as fh:
            fh.write("date,day_n,valquo_pct,spy_pct,excess_pp,n_priced\n")
            for i, d in enumerate(dates, 1):
                fh.write("%s,%d,1.0814,3.0026,-1.9212,85\n" % (d, i))


class TheDoorFindsTheRowWithoutBeingGivenAPath(_Tmp):
    """Cause 1. **THESE FAIL ON TODAY'S CODE** because `history_path` stays `None`."""

    def test_NO_PATHS_SUPPLIED_AND_THE_ANCHOR_IS_FOUND(self):
        """The reproduction of Don's refusal, as the CLI and the HTTP door actually call it."""
        self._write_book()
        self._write_csv()
        got = IM.append_rebalance(_event())            # no meta_path, no history_path
        self.assertTrue(got.get("ok"), got.get("reason"))
        self.assertTrue(got.get("wrote"))
        self.assertNotIn("no recorded row", got.get("reason") or "")

    def test_and_it_REPORTS_how_many_rows_it_read(self):
        """So a future refusal can be told from a read that found nothing, which is the state
        that produced this bug and was indistinguishable from a genuinely unmarked day."""
        self._write_book()
        self._write_csv()
        got = IM.append_rebalance(_event())
        self.assertEqual(got.get("recorded_rows"), 2)

    def test_A_GENUINELY_UNMARKED_DAY_IS_STILL_REFUSED(self):
        """The refusal is KEPT -- the brief's own instruction. Rows exist, just not that one."""
        self._write_book()
        self._write_csv(dates=("2026-10-20", "2026-10-21"))
        got = IM.append_rebalance(_event())
        self.assertFalse(got.get("ok"))
        self.assertIn("no recorded row", got["reason"])
        self.assertEqual(got.get("recorded_rows"), 2, "it refused on an EMPTY read again")


class TheRecordedSeriesIsReadFromTheStoreToo(_Tmp):
    """Cause 2: on a deploy the series lives in the store, which `/api/index-track` serves."""

    class _Store:
        def __init__(self, series):
            self._d = {"series": list(series)}

        def get_meta(self, key):
            return self._d if key == IT.STORE_KEY else None

    def test_the_anchor_resolves_from_a_STORE_BACKED_record_with_no_CSV(self):
        self._write_book()                             # book on disk, history NOT
        got = IM.append_rebalance(_event(), store=self._Store(_store_series()))
        self.assertTrue(got.get("ok"), got.get("reason"))
        self.assertEqual(got.get("recorded_rows"), 2)

    def test_THE_STORE_S_KEYS_ARE_NORMALISED_which_is_item_80_one_layer_along(self):
        """**`from_store` emits `valquo`/`spy`; every reader here wants `valquo_pct`/`spy_pct`.**

        Handing the store's rows through unnormalised would make `_recorded_level` read a key
        the row does not have, return `None`, and refuse the anchor -- the IDENTICAL
        key-mismatch item 80's first half was about, and it would have looked exactly like the
        bug being fixed. So the conversion is asserted directly rather than trusted.
        """
        rows = IM.recorded_rows(os.path.join(self.root, "absent.csv"),
                                self._Store(_store_series()))
        self.assertTrue(rows)
        for r in rows:
            self.assertIn("valquo_pct", r)
            self.assertNotIn("valquo", r)
            self.assertIsNotNone(r["valquo_pct"])

    def test_the_CSV_WINS_when_both_exist_which_is_index_track_s_own_order(self):
        """`vs_spy_claim` reads the CSV and falls back to the store only when it is empty. The
        same order here, so the two cannot disagree about which record is authoritative."""
        self._write_csv(dates=("2026-10-20", "2026-10-21", DATE))
        rows = IM.recorded_rows(self.hist, self._Store(_store_series()))
        self.assertEqual(len(rows), 3, "the store overrode a present CSV")

    def test_NEITHER_SOURCE_IS_STILL_A_REFUSAL(self):
        self._write_book()
        got = IM.append_rebalance(_event())
        self.assertFalse(got.get("ok"))
        self.assertIn("no recorded row", got["reason"])
        self.assertEqual(got.get("recorded_rows"), 0)


class ThroughTheRealAppRoute(_Tmp):
    """The brief's own requirement: *a test that runs through the real app route against a
    store-backed record.* The route resolves its own store, so this is the only form that
    exercises what Don's `--send` actually hits."""

    def _client(self):
        app = create_saas_app(CONFIG)
        return app.test_client(), {"X-Admin-Token": CONFIG.admin_token}

    def _seed_store(self, client, series):
        """Put the recorded series where `/api/index-track` reads it from on a deploy."""
        from valuation.screener.store import Store                # noqa: PLC0415
        Store().set_meta(IT.STORE_KEY, {"series": list(series),
                                        "inception_date": "2026-07-30",
                                        "benchmark": "SPY"})

    def test_POST_track_rebalance_ACCEPTS_a_store_backed_anchor(self):
        self._write_book()
        c, h = self._client()
        self._seed_store(c, _store_series())
        r = c.post("/admin/track-rebalance", json={"rebalance": _event()}, headers=h)
        self.assertEqual(r.status_code, 201, r.get_json())
        self.assertTrue(r.get_json().get("wrote"))

    def test_AND_A_MISSING_ANCHOR_STILL_422s_THROUGH_THE_ROUTE(self):
        self._write_book()
        c, h = self._client()
        self._seed_store(c, _store_series(dates=("2026-10-20", "2026-10-21")))
        r = c.post("/admin/track-rebalance", json={"rebalance": _event()}, headers=h)
        self.assertEqual(r.status_code, 422, r.get_json())
        self.assertIn("no recorded row", (r.get_json() or {}).get("reason") or "")

    def test_THE_LATER_ROW_REFUSAL_SURVIVES_which_the_brief_names_explicitly(self):
        """*"a recorded row already exists after the event date" must still refuse.* It now
        reads the SAME rows as the anchor check, so the two cannot disagree."""
        self._write_book()
        c, h = self._client()
        self._seed_store(c, _store_series(dates=(DATE, "2026-10-23")))
        r = c.post("/admin/track-rebalance", json={"rebalance": _event()}, headers=h)
        # **409, NOT 422, and my own first expectation here was wrong rather than the code.**
        # The door maps a reason containing "append-only" to 409 ("you disagree with the
        # record") and everything else to 422, and this refusal's own text ends *"Events are
        # append-only and that row can never be corrected."* So the status is right and the
        # test was asserting the wrong one.
        #
        # **AND THIS IS THE RACE THE BRIEF NAMES.** Once the 2026-10-23 row lands, a 2026-10-22
        # event is refused BY DESIGN -- this is what that looks like through the route, which
        # makes it the documentation of the deadline as well as a regression guard.
        self.assertEqual(r.status_code, 409, r.get_json())
        body = r.get_json() or {}
        self.assertIn("2026-10-23", body.get("reason") or "")
        self.assertEqual(body.get("latest_recorded_row"), "2026-10-23")
        # IT READ THE STORE TO GET THERE, which is what makes this a 80b test and not an
        # inherited one: two rows resolved from the store with no CSV present at all.
        self.assertEqual(body.get("recorded_rows"), 2)

    def test_the_door_is_still_owner_only(self):
        c, _h = self._client()
        r = c.post("/admin/track-rebalance", json={"rebalance": _event()})
        self.assertEqual(r.status_code, 401)


class TheDAILYWRITERSAnchorResolvesToo(_Tmp):
    """The latent third cause. **This is the one that would have stopped the record.**"""

    def test_contract_row_defaults_its_history_path(self):
        """Asserted on the signature and the body rather than by driving a vendor fetch: the
        branch needs a priced mark, and what broke was the PATH, not the pricing."""
        import inspect
        src = inspect.getsource(IM.contract_row)
        self.assertIn("default_paths()[1]", src)
        self.assertIn("recorded_rows(", src)
        self.assertIn("store", inspect.signature(IM.contract_row).parameters)

    def test_and_the_writer_door_hands_the_store_through(self):
        src = io.open(os.path.join(REPO, "valuation", "saas", "app_saas.py"),
                      encoding="utf-8").read()
        # **`Store()` AND NOT `_store()`, which this file has now warned about three times.**
        # The first cut of these two call sites used `_store()` -- a helper that lives in
        # `web/app.py` and does not exist in `app_saas` -- so the authorised path would have
        # raised `NameError` into the handler's `except` and returned a 500, strictly WORSE for
        # Don than the 422 he already had. This suite caught it on its first run because it
        # drives the real route; asserting the string is how it stays caught.
        self.assertIn("index_mark.contract_row(date, store=_Store80b())", src)
        self.assertIn("index_mark.append_rebalance(event, store=_Store80b())", src)
        self.assertNotIn("store=_store()", src, "the non-existent helper is back")

    def test_the_anchor_is_found_once_a_rebalance_exists(self):
        """The property the daily writer needs: with an event recorded and NO path supplied,
        the level that event compounds onto resolves."""
        self._write_csv(dates=("2026-10-21", DATE))
        self.assertIsNotNone(
            IM._recorded_level(DATE, rows=IM.recorded_rows(self.hist, None)))
        # ... and through the default, which is what `contract_row` now does.
        self.assertIsNotNone(
            IM._recorded_level(DATE, rows=IM.recorded_rows(IT.default_paths()[1], None)))


class NoOtherCallerPassesNoneByAccident(unittest.TestCase):
    """The brief's step: grep for other `_read_history`/`_recorded_level` callers."""

    def test_every_in_module_recorded_level_call_resolves_a_source(self):
        import ast
        src = io.open(IM.__file__, encoding="utf-8").read()
        bad = []
        for node in ast.walk(ast.parse(src)):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name not in ("_recorded_level", "_last_recorded_date"):
                continue
            kw = {k.arg for k in node.keywords}
            # Either pre-resolved rows, or a path argument that is not the bare default.
            if "rows" in kw or len(node.args) >= 2:
                continue
            bad.append("line %d: %s with neither rows= nor a path" % (node.lineno, name))
        self.assertEqual(bad, [], bad)

    def test_the_app_s_own_history_read_still_names_the_path(self):
        """`app_saas` fixed this same defect thirty lines above `contract_row`'s caller; that
        fix must not regress, because it is the precedent this item followed."""
        src = io.open(os.path.join(REPO, "valuation", "saas", "app_saas.py"),
                      encoding="utf-8").read()
        self.assertIn("index_mark._read_history(_it.default_paths()[1])", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
