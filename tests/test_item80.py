# -*- coding: utf-8 -*-
"""ITEM 80 — the rebalance door refused EVERY book, and its tests could not see it.

**MEASURED 2026-10-23 ~8:45pm ET, mid-rebalance.** Don ran
`scripts/seed_track --rebalance ... --send` with an 81-name book whose largest weight is 1.96%
and whose own `contract_conformance` block reads `conforms: true`, and got:

    HTTP 422  the rebalance is not the contract-bound Index: conformance refused

`index_mark.append_rebalance` read `(c or {}).get("ok")` off `valquo_index.conformance`, which
returns **`conforms` and `why_not`** and has neither `ok` nor `reason`. So the test was `None`
for every book that has ever been handed to that door, conforming or not, and the message was
the generic fallback -- a refusal that could not be satisfied, wearing the words of one that
could.

**WHY THE SUITE WAS GREEN: the door takes an INJECTABLE `conformance` and the fixtures injected
a stub returning `ok`.** The seam's return SHAPE differed from the thing it stood in for, which
is the defect family `index_mark`'s own `announce` docstring names -- *"a seam whose signature
differs from the thing it stands in for is how a fixture comes to pass against behaviour that
could not happen"*. So **every test here drives the door through the REAL function**, and the
one that does not is an AST guard pinning that `ok`/`reason` is never read off a conformance
result again.

Nothing here contacts a network or a broker; every path writes inside a temporary directory.
"""
from __future__ import annotations

import ast
import datetime as _dt
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from valuation.edge import valquo_index as VI      # noqa: E402
from valuation.screener import index_mark as IM     # noqa: E402

#: A conforming book: at least `CONTRACT_MIN_POSITIONS` names with the 8% cap actually binding.
#: Built from the contract's own constants rather than from the number 50, so a change to the
#: floor moves this fixture with it instead of turning it red.
N_OK = VI.CONTRACT_MIN_POSITIONS + 31           # 81 on today's constants, Don's own book size


def _book(n, inception="2026-07-30", events=None):
    """The bound book file, with `n` equally weighted names."""
    return {"inception_date": inception,
            "positions": [{"ticker": "T%03d" % i, "weight": 1.0 / n} for i in range(n)],
            "rebalances": list(events or [])}


def _event(n, date="2026-10-22", scan="2026-10-22"):
    return {"date": date, "scan_date": scan,
            "positions": [{"ticker": "T%03d" % i, "weight": 1.0 / n} for i in range(n)]}


class TheDoorReadsTheKeysTheFunctionReturns(unittest.TestCase):
    """**EVERY CASE GOES THROUGH THE REAL `valquo_index.conformance`.** No stub, anywhere."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="i80_")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.meta = os.path.join(self.root, "valquo_track.json")
        self.hist = os.path.join(self.root, "valquo_track_history.csv")

    def _write(self, book, rows=("2026-10-22",)):
        with io.open(self.meta, "w", encoding="utf-8") as fh:
            json.dump(book, fh)
        with io.open(self.hist, "w", encoding="utf-8", newline="") as fh:
            fh.write("date,valquo_pct,spy_pct,n_priced\n")
            for d in rows:
                fh.write("%s,1.0,1.0,%d\n" % (d, N_OK))

    def _append(self, event, book=None):
        self._write(book if book is not None else _book(N_OK))
        # NO `conformance=` ARGUMENT. The door resolves the real one itself, which is the whole
        # point of this suite.
        return IM.append_rebalance(event, meta_path=self.meta, history_path=self.hist)

    # ---------------------------------------------------------------- the defect
    def test_A_CONFORMING_BOOK_IS_ACCEPTED(self):
        """**THE CASE THAT FAILS ON TODAY'S CODE AND IS WHY DON WAS BLOCKED.**

        81 names at 1.23% each: above the contract floor, cap binding, `conforms: true`. Before
        the fix this came back *"the rebalance is not the contract-bound Index: conformance
        refused"*, because the door tested a key the function does not return.
        """
        got = self._append(_event(N_OK))
        self.assertTrue(got.get("ok"), got.get("reason"))
        self.assertNotIn("not the contract-bound Index", got.get("reason") or "")

    def test_the_REAL_conformance_really_does_accept_that_book(self):
        """The control on the fixture rather than on the door: if this ever reads False the
        test above would be asserting the wrong thing and would need a different book, not a
        different door."""
        c = VI.conformance(N_OK, 1.0 / N_OK)
        self.assertTrue(c["conforms"], c["why_not"])
        self.assertNotIn("ok", c, "conformance grew an `ok` key; this whole item assumes not")
        self.assertNotIn("reason", c)

    # ---------------------------------------------------------------- the refusal is KEPT
    def test_A_BOOK_BELOW_THE_FLOOR_IS_STILL_REFUSED(self):
        n = VI.CONTRACT_MIN_POSITIONS - 1
        got = self._append(_event(n), book=_book(n))
        self.assertFalse(got.get("ok"))
        self.assertIn("not the contract-bound Index", got["reason"])

    def test_AND_THE_REASON_NAMES_why_not_RATHER_THAN_THE_GENERIC_FALLBACK(self):
        """The half that proves the door is reading the result and not merely rejecting it.

        A door that refused everything with the fallback text would satisfy the test above --
        that is exactly the state Don hit -- so the reason has to carry the FUNCTION's own
        words.
        """
        n = VI.CONTRACT_MIN_POSITIONS - 1
        got = self._append(_event(n), book=_book(n))
        why = VI.conformance(n, 1.0 / n)["why_not"]
        self.assertTrue(why)
        for sentence in why:
            self.assertIn(sentence, got["reason"])
        self.assertNotIn("conformance refused", got["reason"],
                         "the generic fallback fired on a book that had reasons")

    def test_AN_UNBOUND_CAP_IS_REFUSED_even_at_enough_names(self):
        """The contract's second condition, which is a different `why_not` sentence."""
        n = VI.CONTRACT_MIN_POSITIONS + 1
        pos = [{"ticker": "T%03d" % i, "weight": 1.0} for i in range(n)]
        pos[0]["weight"] = 100.0                      # one name dominates once normalised
        book = {"inception_date": "2026-07-30", "positions": pos, "rebalances": []}
        ev = {"date": "2026-10-22", "scan_date": "2026-10-22", "positions": pos}
        got = self._append(ev, book=book)
        self.assertFalse(got.get("ok"))
        self.assertIn("cap does not bind", got["reason"])

    # ---------------------------------------------------------------- nothing else moved
    def test_THE_OTHER_REFUSALS_ARE_UNTOUCHED(self):
        """Item 80's own instruction: *do not touch the other refusals.* One case each."""
        book = _book(N_OK)
        # built AFTER its own event date
        got = self._append(_event(N_OK, date="2026-10-22", scan="2026-10-23"), book=book)
        self.assertFalse(got.get("ok"))
        self.assertNotIn("not the contract-bound Index", got["reason"])
        # dated on or before inception
        got = self._append(_event(N_OK, date="2026-07-29", scan="2026-07-29"), book=book)
        self.assertFalse(got.get("ok"))
        # no recorded row on that date
        self._write(book, rows=("2026-10-21",))
        got = IM.append_rebalance(_event(N_OK, date="2026-10-22"),
                                  meta_path=self.meta, history_path=self.hist)
        self.assertFalse(got.get("ok"))

    def test_INCEPTION_IS_NEVER_TOUCHED(self):
        self._append(_event(N_OK))
        with io.open(self.meta, encoding="utf-8") as fh:
            self.assertEqual((json.load(fh) or {}).get("inception_date"), "2026-07-30")

    def test_RE_SENDING_THE_SAME_EVENT_IS_STILL_A_NO_OP(self):
        """The retry property, which matters tonight: Don is re-running a `--send`."""
        ev = _event(N_OK)
        first = self._append(ev)
        self.assertTrue(first.get("ok"), first.get("reason"))
        again = IM.append_rebalance(ev, meta_path=self.meta, history_path=self.hist)
        self.assertTrue(again.get("ok"), again.get("reason"))
        with io.open(self.meta, encoding="utf-8") as fh:
            self.assertEqual(len((json.load(fh) or {}).get("rebalances") or []), 1)


class NoCallerReadsAKeyConformanceDoesNotReturn(unittest.TestCase):
    """The guard that stops this recurring, read on the syntax tree over the whole package."""

    #: What `conformance()` actually returns. A committed literal (`MA13`) so a future key
    #: rename shows up here as a change rather than as a silently weakened guard.
    RETURNED = ("conforms", "n_positions", "effective_max_weight", "max_weight",
                "min_positions", "n_eligible", "why_not")

    def test_the_returned_keys_are_what_this_guard_thinks_they_are(self):
        got = VI.conformance(N_OK, 1.0 / N_OK)
        self.assertEqual(set(got), set(self.RETURNED))

    def test_no_module_reads_ok_or_reason_off_a_conformance_RESULT(self):
        """**AST, NOT A GREP, and the distinction is the whole reason this guard can exist.**
        `.get("ok")` and `.get("reason")` are everywhere in this codebase and almost always
        correct -- the door's own `out` dict has both. What is forbidden is reading one off a
        name that holds a CONFORMANCE result, so the guard matches on the receiver.

        **AND THE FIRST CUT OF THIS GUARD DID NOT CATCH THE DEFECT IT WAS WRITTEN FOR.** The
        line was `(c or {}).get("ok")`, whose receiver is a `BoolOp` and not a `Name`, so
        resolving `receiver.id` gave `None` and the guard passed against the exact expression
        that blocked Don's rebalance. Measured by restoring the pre-fix source and re-running:
        6 of 15 cases went red and this one did not. **A guard that cannot see the shape the
        codebase actually wrote is not measuring the tree** -- so `_receiver` unwraps the
        `x or {}` idiom, and `test_and_that_guard_bites` drives the original line through it.
        """
        import glob

        def _receiver(node):
            """The name a `.get` is called on, through the `x or {}` idiom. `None` otherwise."""
            v = getattr(node, "value", None)
            if isinstance(v, ast.BoolOp) and isinstance(v.op, ast.Or) and v.values:
                v = v.values[0]
            return getattr(v, "id", None)

        names = {"c", "conf", "conformance", "_conf", "blk"}
        bad = []
        for path in glob.glob(os.path.join(REPO, "valuation", "**", "*.py"), recursive=True):
            rel = os.path.relpath(path, REPO).replace(os.sep, "/")
            with io.open(path, encoding="utf-8") as fh:
                src = fh.read()
            if "conformance(" not in src:
                continue
            for node in ast.walk(ast.parse(src)):
                if not isinstance(node, ast.Call):
                    continue
                f = node.func
                if getattr(f, "attr", None) != "get" or not node.args:
                    continue
                recv = _receiver(f)
                arg = node.args[0]
                if (recv in names and isinstance(arg, ast.Constant)
                        and arg.value in ("ok", "reason")):
                    bad.append("%s:%d  %s.get(%r)" % (rel, node.lineno, recv, arg.value))
        self.assertEqual(bad, [], "a conformance result is read by the wrong key: %r" % bad)

    def test_and_that_guard_bites_ON_THE_EXACT_PRE_FIX_LINE(self):
        """The positive control, and it is the line from Don's refusal rather than a lookalike.

        It drives the receiver resolution over `(c or {}).get("ok")` -- the `BoolOp` receiver
        the first cut of the guard could not see, measured by restoring the pre-fix source and
        watching 6 of 15 cases go red while this one stayed green. If the unwrapping is ever
        removed this fails, which is the only way to keep the guard honest about its own blind
        spot.
        """
        def _receiver(node):
            v = getattr(node, "value", None)
            if isinstance(v, ast.BoolOp) and isinstance(v.op, ast.Or) and v.values:
                v = v.values[0]
            return getattr(v, "id", None)

        tree = ast.parse('c = conformance(1, 1.0)\nif not (c or {}).get("ok"):\n    pass\n')
        hits = [n for n in ast.walk(tree)
                if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "get"
                and _receiver(n.func) == "c"
                and n.args and isinstance(n.args[0], ast.Constant)
                and n.args[0].value in ("ok", "reason")]
        self.assertTrue(hits, "the guard cannot see the expression that caused item 80")
        # AND THE PLAIN-NAME FORM TOO, so unwrapping did not replace the simple case.
        plain = ast.parse('conf = conformance(1, 1.0)\nconf.get("reason")\n')
        self.assertTrue([n for n in ast.walk(plain)
                         if isinstance(n, ast.Call)
                         and getattr(n.func, "attr", None) == "get"
                         and _receiver(n.func) == "conf"])

    def test_EVERY_caller_of_conformance_is_censused(self):
        """Item 80 step 3: check every caller. This records the answer so a new one is visible.

        Measured 2026-10-23: `append_rebalance` was the ONLY site with the mismatch. The seed
        door one function along, `paper_track.book_conformance`, `seed_book`,
        `held_book_conformance` and `scripts/index_best_diag` all read `conforms`/`why_not`
        correctly.
        """
        import glob
        callers = set()
        for pat in ("valuation/**/*.py", "scripts/*.py"):
            for path in glob.glob(os.path.join(REPO, pat), recursive=True):
                with io.open(path, encoding="utf-8") as fh:
                    tree = ast.parse(fh.read())
                for node in ast.walk(tree):
                    if (isinstance(node, ast.Call)
                            and (getattr(node.func, "attr", None) == "conformance"
                                 or getattr(node.func, "id", None) == "conformance")):
                        callers.add(os.path.relpath(path, REPO).replace(os.sep, "/"))
        self.assertIn("valuation/screener/index_mark.py", callers)
        self.assertIn("valuation/edge/paper_track.py", callers)


class TheSEAMThatHidItIsNamed(unittest.TestCase):

    def test_the_injectable_conformance_still_exists_and_is_still_optional(self):
        """NOT removed. It is why a test need not build a 50-name book, and tonight's suite
        shows the real function is reachable without it. What changed is that the door reads the
        REAL return shape, so a stub returning `ok` can no longer make anything pass."""
        import inspect
        sig = inspect.signature(IM.append_rebalance)
        self.assertIn("conformance", sig.parameters)
        self.assertIsNone(sig.parameters["conformance"].default)

    def test_a_STUB_RETURNING_ok_NO_LONGER_LETS_A_NON_CONFORMING_BOOK_THROUGH(self):
        """The precise inversion of the defect: the old door believed `ok`, the new one does
        not, so the shape that used to be the only thing that worked is now inert."""
        root = tempfile.mkdtemp(prefix="i80stub_")
        self.addCleanup(shutil.rmtree, root, True)
        meta = os.path.join(root, "b.json")
        hist = os.path.join(root, "h.csv")
        with io.open(meta, "w", encoding="utf-8") as fh:
            json.dump(_book(N_OK), fh)
        with io.open(hist, "w", encoding="utf-8", newline="") as fh:
            fh.write("date,valquo_pct,spy_pct,n_priced\n2026-10-22,1.0,1.0,%d\n" % N_OK)
        got = IM.append_rebalance(_event(N_OK), meta_path=meta, history_path=hist,
                                  conformance=lambda *_a, **_k: {"ok": True})
        self.assertFalse(got.get("ok"))
        self.assertIn("not the contract-bound Index", got["reason"])


class TheDEPLOYCanBeCONFIRMEDRatherThanInferred(unittest.TestCase):
    """`/api/health` now says which commit is serving. [item 80's own Done step]

    **IT EXISTS BECAUSE CONFIRMING A DEPLOY WAS NOT POSSIBLE.** `render.yaml` sets
    `autoDeploy: true` and no surface said what had deployed, so "the fix is live" could only be
    INFERRED from main's HEAD plus elapsed time. On the night Don was waiting mid-rebalance on a
    one-line fix, that is the difference between telling him it is live and telling him it
    probably is.
    """

    def _client(self, commit=None):
        import importlib
        if commit is None:
            os.environ.pop("RENDER_GIT_COMMIT", None)
        else:
            os.environ["RENDER_GIT_COMMIT"] = commit
        app = importlib.import_module("valuation.web.app")
        return app.create_app().test_client()

    def tearDown(self):
        os.environ.pop("RENDER_GIT_COMMIT", None)

    def test_it_reports_the_commit_render_set(self):
        d = self._client("abc1234def5678").get("/api/health").get_json()
        self.assertTrue(d["ok"])
        self.assertEqual(d["commit"], "abc1234def5678")
        self.assertEqual(d["commit_short"], "abc1234")

    def test_ABSENT_READS_AS_NULL_rather_than_as_a_guess(self):
        """Local runs and any host that does not set it. `None` is an answer; a fabricated or
        inferred SHA would be worse than none, because the whole point is confirmation."""
        d = self._client(None).get("/api/health").get_json()
        self.assertIsNone(d["commit"])
        self.assertIsNone(d["commit_short"])
        self.assertTrue(d["ok"], "the health check must not fail for want of a commit")

    def test_NOTHING_ELSE_WAS_ADDED_to_that_payload(self):
        """No path, no branch, no environment, no token -- a deploy marker is not a place to
        start publishing the service's configuration."""
        d = self._client("deadbeef").get("/api/health").get_json()
        self.assertEqual(set(d), {"ok", "ai_enabled", "sector_sources", "commit",
                                  "commit_short", "ai_provider", "mc_trials"})

    def test_the_health_check_path_render_probes_is_the_one_that_carries_it(self):
        """`render.yaml`'s `healthCheckPath` is `/api/health`, so the marker is on the surface
        Render already calls -- derived from the file rather than assumed."""
        with io.open(os.path.join(REPO, "render.yaml"), encoding="utf-8") as fh:
            self.assertIn("healthCheckPath: /api/health", fh.read())


class TheSEEDDoorWasAlreadyRight(unittest.TestCase):
    """Item 80 step 3, pinned rather than asserted in prose."""

    def test_it_reads_conforms_and_why_not(self):
        src = io.open(IM.__file__, encoding="utf-8").read()
        body = src.split("def seed(", 1)[1] if "def seed(" in src else src
        self.assertIn('conf.get("conforms")', body)
        self.assertIn('conf.get("why_not")', body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
