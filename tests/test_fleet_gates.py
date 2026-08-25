"""(B) THE DEPLOYED-IMAGE GAP — what leaves the licensed store, and the proof it is only a bit.

Six declared books gate on flags computed from licensed Sharadar exports, and
`.dockerignore` excludes `data/` WHOLESALE while the fleet cycle runs on the Render service.
The route taken is the paper track's: a DERIVED artifact under `data_export/`, which is
tracked and shipped.

**THE SAFETY ARGUMENT IS STRUCTURAL AND THESE PIN IT: A TICKER SYMBOL AND A BOOLEAN LEAVE,
AND NOTHING ELSE.** A boolean cannot carry a vendor row. The reduction is thousands of rows to
one bit and is not reversible. This is asserted on the SHIPPED artifact, on the builder's
output, and at write time inside the exporter itself -- a test can be skipped, and the
guarantee cannot rest on a test being run.

**AND THREE STATES, NEVER TWO.** An unknown gate, an unknown ticker and a stale gate are three
different facts and none of them is a pass. `MB8`: the bucket a rule cannot evaluate is a real
bucket and is not the safe one.

    python tests/test_fleet_gates.py
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge import fleet_gates as G          # noqa: E402
import fleet_export_gates as EX                      # noqa: E402

TODAY = dt.date(2026, 8, 24)


def _write(root, payload):
    os.makedirs(os.path.join(root, "data_export"), exist_ok=True)
    with io.open(os.path.join(root, G.ARTIFACT_REL), "w", encoding="utf-8") as fh:
        json.dump(payload, fh)


def _payload(**gates):
    return {"schema": G.SCHEMA, "generated_utc": "2026-08-24T00:00:00+00:00",
            "license_note": "x", "gates": gates}


class OnlyABitLeavesTheLicensedStore(unittest.TestCase):
    """The whole safety argument, asserted on the artifact that actually ships."""

    def setUp(self):
        p = os.path.join(REPO, G.ARTIFACT_REL)
        if not os.path.exists(p):
            self.skipTest("gates artifact not exported in this tree")
        with io.open(p, encoding="utf-8") as fh:
            self.payload = json.load(fh)

    def test_every_value_in_every_gate_is_a_BOOLEAN(self):
        """A boolean cannot carry a vendor row. That is the guarantee, and it is structural."""
        seen = 0
        for name, g in self.payload["gates"].items():
            for t, v in (g.get("tickers") or {}).items():
                self.assertIsInstance(v, bool, "%s/%s is %s" % (name, t, type(v).__name__))
                seen += 1
        self.assertGreater(seen, 0, "the scan saw nothing -- it would pass on an empty file")

    def test_no_FLOAT_appears_anywhere_in_any_ticker_map(self):
        """The specific leak this forbids: a Beneish M, an Altman Z, a tail mass or a price
        smuggled in beside the flag it was computed from."""
        for name, g in self.payload["gates"].items():
            for t, v in (g.get("tickers") or {}).items():
                self.assertNotIsInstance(v, float, "%s/%s" % (name, t))
                self.assertNotIsInstance(v, (list, dict), "%s/%s" % (name, t))

    def test_the_keys_are_plausible_TICKERS_and_not_smuggled_payloads(self):
        for name, g in self.payload["gates"].items():
            for t in (g.get("tickers") or {}):
                self.assertIsInstance(t, str)
                self.assertTrue(0 < len(t) <= 12, "%s/%r" % (name, t))

    def test_each_gate_stamps_its_OWN_as_of_because_the_vintages_differ(self):
        """A single top-level timestamp would average a quarterly compute and a panel that
        ends months earlier into one reassuring number."""
        stamps = set()
        for name, g in self.payload["gates"].items():
            if g.get("absent"):
                continue
            self.assertIn("as_of", g, name)
            stamps.add(g["as_of"])
        self.assertGreaterEqual(len(stamps), 1)

    def test_the_artifact_is_small_enough_to_be_a_bitmap_and_not_a_dataset(self):
        """A crude but real check on the reduction: thousands of rows per name went in, and
        what came out is one bit each. If this file ever grows into the megabytes, something
        other than bits is leaving."""
        n = sum(len(g.get("tickers") or {}) for g in self.payload["gates"].values())
        size = os.path.getsize(os.path.join(REPO, G.ARTIFACT_REL))
        self.assertLess(size, 60 * max(n, 1) + 8192, "bytes per flag is too high")


class TheExporterRefusesToWiden(unittest.TestCase):
    """The guarantee is enforced at WRITE time, not only by a test that might not be run."""

    def test_a_non_boolean_is_refused_by_the_writer_itself(self):
        bad = _payload(g1={"as_of": "2026-01-28", "tickers": {"AAPL": 1.234}})
        with self.assertRaises(SystemExit) as cm:
            EX._assert_booleans_only(bad)
        self.assertIn("bool", str(cm.exception))

    def test_an_int_is_refused_too_because_a_count_is_not_a_flag(self):
        bad = _payload(g1={"as_of": "2026-01-28", "tickers": {"AAPL": 2}})
        with self.assertRaises(SystemExit):
            EX._assert_booleans_only(bad)

    def test_a_clean_payload_passes_and_the_check_is_not_vacuous(self):
        ok = _payload(g1={"as_of": "2026-01-28", "tickers": {"AAPL": True, "MSFT": False}})
        self.assertEqual(EX._assert_booleans_only(ok), 2)

    def test_the_exporter_names_a_CLOSED_gate_set(self):
        """A gate absent from `GATES` cannot appear in the artifact by accident.

        A COMMITTED LITERAL (`MA13`), so widening the artifact is a deliberate edit that shows
        in a diff rather than something that happens while nobody is looking. It has already
        fired once, on `optionable` being added in the same session -- which is the idiom
        working, not a nuisance.
        """
        self.assertEqual(set(EX.GATES), {"ma28_clean", "evt_clean", "optionable"})


class ThreeStatesNeverTwo(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="gates_")

    def test_an_absent_artifact_is_reported_and_never_raises(self):
        r = G.load(self.root)
        self.assertFalse(r["ok"])
        self.assertTrue(r["absent"])
        self.assertIn("fleet_export_gates", r["reason"])

    def test_an_absent_artifact_yields_UNKNOWN_and_not_False(self):
        g = G.gate("ma28_clean", "AAPL", root=self.root)
        self.assertIsNone(g["value"], "an unknown must never read as a fail")
        self.assertEqual(g["state"], G.UNKNOWN_GATE)

    def test_a_name_outside_the_cross_section_is_UNKNOWN_TICKER(self):
        _write(self.root, _payload(ma28_clean={"as_of": "2026-01-28",
                                               "tickers": {"AAPL": True}}))
        g = G.gate("ma28_clean", "NOSUCH", root=self.root, today=TODAY)
        self.assertIsNone(g["value"])
        self.assertEqual(g["state"], G.UNKNOWN_TICKER)
        self.assertIn("cross-section", g["reason"])

    def test_a_known_name_returns_its_bit_and_its_vintage(self):
        _write(self.root, _payload(ma28_clean={"as_of": "2026-01-28",
                                               "tickers": {"AAPL": True, "AA": False}}))
        a = G.gate("ma28_clean", "aapl", root=self.root, today=TODAY)
        self.assertIs(a["value"], True)
        self.assertEqual(a["state"], G.OK)
        self.assertEqual(a["as_of"], "2026-01-28")
        self.assertEqual(a["age_days"], 208)
        self.assertIs(G.gate("ma28_clean", "AA", root=self.root, today=TODAY)["value"], False)

    def test_a_stale_gate_is_its_OWN_state_and_returns_no_value(self):
        """Staleness is a caller's bar, so it has no default -- inventing one here is exactly
        how `MA5` measured a bar freezing."""
        _write(self.root, _payload(ma28_clean={"as_of": "2026-01-28",
                                               "tickers": {"AAPL": True}}))
        fresh = G.gate("ma28_clean", "AAPL", root=self.root, today=TODAY, max_age_days=400)
        self.assertIs(fresh["value"], True)
        stale = G.gate("ma28_clean", "AAPL", root=self.root, today=TODAY, max_age_days=90)
        self.assertIsNone(stale["value"])
        self.assertEqual(stale["state"], G.STALE)
        self.assertIn("208 days old", stale["reason"])

    def test_there_is_NO_default_parameter_anywhere_on_the_reader(self):
        """A `default=` would let a caller turn an unknown into a pass in one keyword, which
        is the fail-open this module exists to prevent."""
        import inspect
        for fn in (G.gate, G.as_of, G.age_days, G.coverage, G.load):
            self.assertNotIn("default", inspect.signature(fn).parameters, fn.__name__)

    def test_a_wrong_schema_is_refused_rather_than_read_optimistically(self):
        _write(self.root, {"schema": "something/9", "gates": {}})
        r = G.load(self.root)
        self.assertFalse(r["ok"])
        self.assertIn("schema", r["reason"])

    def test_an_EMPTY_gate_is_VACUOUS_and_not_coverage_of_zero(self):
        """`O21-D2`'s C5: a filter that never ran and one that ran and found nothing must not
        read the same."""
        _write(self.root, _payload(ma28_clean={"as_of": "2026-01-28", "tickers": {}}))
        cov = G.coverage(self.root)
        self.assertTrue(cov["gates"]["ma28_clean"]["present"])
        self.assertTrue(cov["gates"]["ma28_clean"]["vacuous"])

    def test_an_absent_gate_carries_its_reason_into_coverage(self):
        _write(self.root, _payload(evt_clean={"absent": True, "reason": "panel stranded"}))
        cov = G.coverage(self.root)
        self.assertFalse(cov["gates"]["evt_clean"]["present"])
        self.assertIn("stranded", cov["gates"]["evt_clean"]["reason"])


class TheShippedArtifactIsReadableInTheImage(unittest.TestCase):

    def test_the_real_artifact_loads_and_both_gates_are_present(self):
        if not os.path.exists(os.path.join(REPO, G.ARTIFACT_REL)):
            self.skipTest("gates artifact not exported in this tree")
        cov = G.coverage()
        self.assertTrue(cov["ok"])
        for name in EX.GATES:
            self.assertIn(name, cov["gates"], name)
            self.assertTrue(cov["gates"][name]["present"], name)
            self.assertFalse(cov["gates"][name]["vacuous"], name)

    def test_data_export_is_shipped_so_this_artifact_actually_reaches_the_runner(self):
        """The entire point. If `data_export/` were ever excluded, this route silently stops
        working ON THE SERVICE while every test here still passes."""
        with io.open(os.path.join(REPO, ".dockerignore"), encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh if ln.strip() and not ln.strip().startswith("#")]
        self.assertIn("data/", lines)
        self.assertNotIn("data_export/", lines)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
