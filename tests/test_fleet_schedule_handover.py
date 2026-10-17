"""The fleet-cycle schedule handover - one install must leave exactly ONE fleet schedule.

**THE DEFECT THIS SUITE EXISTS FOR, AND THE FILE THAT HAD IT WAS THE FILE WARNING ABOUT IT.**
The handover first shipped as `pending_workflows/fleet-cycle-in-hours.yml`. `install_workflows.bat`
copies each pending `.yml` into `.github/workflows/` **by name**, so a new name is an ADDITION:
the 22:19Z schedule and the 12:00Z one would both have run, each able to enter, and the books
would have filled at twice their declared rate -- the double-fill the handover's own header
warned about. **Renaming it to `fleet-cycle.yml` is the whole fix**, because the installer
overwrites by name.

WHAT THESE PIN
--------------
1. **It replaces rather than adds**: the pending file's name matches an installed workflow.
2. **The body is VERBATIM apart from the cron** - every other key byte-equal to the installed
   file, so the two cannot drift into two different doors on two different schedules.
3. **The cron is the 12:00Z one**, and it is the only schedule in the file.
4. **No second fleet schedule is left anywhere** after an install, modelled directly.

    python tests/test_fleet_schedule_handover.py
"""
from __future__ import annotations

import io
import os
import sys
import unittest

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import state_isolation  # noqa: F401,E402

PENDING = os.path.join(REPO, "pending_workflows", "fleet-cycle.yml")
INSTALLED = os.path.join(REPO, ".github", "workflows", "fleet-cycle.yml")


def _load(p):
    with io.open(p, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _on(d):
    # PyYAML parses a bare `on:` key as the boolean True.
    return d.get(True) if True in d else d.get("on")


class TestItReplacesRatherThanAdds(unittest.TestCase):
    """(1) and (4)."""

    def test_the_pending_file_has_the_SAME_NAME_as_an_installed_workflow(self):
        self.assertTrue(os.path.exists(PENDING), "the handover is missing")
        self.assertTrue(os.path.exists(INSTALLED), "nothing to replace")
        self.assertEqual(os.path.basename(PENDING), os.path.basename(INSTALLED))

    def test_the_old_additive_filename_is_gone(self):
        stale = os.path.join(REPO, "pending_workflows", "fleet-cycle-in-hours.yml")
        self.assertFalse(os.path.exists(stale),
                         "a second fleet schedule would be ADDED beside the first")

    def test_one_install_leaves_exactly_one_fleet_schedule(self):
        """Modelled on the installer's own rule: it copies each pending .yml by name."""
        installed = {f for f in os.listdir(os.path.join(REPO, ".github", "workflows"))
                     if f.endswith((".yml", ".yaml"))}
        pending = {f for f in os.listdir(os.path.join(REPO, "pending_workflows"))
                   if f.endswith((".yml", ".yaml"))}
        after = installed | pending                      # copy-by-name is a set union
        fleet = sorted(f for f in after if "fleet-cycle" in f)
        self.assertEqual(fleet, ["fleet-cycle.yml"],
                         "exactly one fleet-cycle schedule may exist after an install")

    def test_no_OTHER_workflow_also_posts_the_fleet_cycle_door_on_a_schedule(self):
        """A second scheduled caller of the same door is the same double-fill by another route."""
        wf = os.path.join(REPO, ".github", "workflows")
        callers = []
        for f in sorted(os.listdir(wf)):
            if not f.endswith((".yml", ".yaml")):
                continue
            with io.open(os.path.join(wf, f), encoding="utf-8") as fh:
                src = fh.read()
            if "admin/fleet-cycle?run=1" in src and "schedule:" in src:
                callers.append(f)
        self.assertEqual(callers, ["fleet-cycle.yml"], "callers: %r" % (callers,))


class TestTheBodyIsVerbatim(unittest.TestCase):
    """(2) - or the two files become two different doors."""

    def setUp(self):
        self.p = _load(PENDING)
        self.i = _load(INSTALLED)

    def test_every_key_except_the_schedule_is_identical(self):
        self.assertEqual(self.p["name"], self.i["name"])
        self.assertEqual(self.p["jobs"], self.i["jobs"])
        self.assertEqual(self.p.get("concurrency"), self.i.get("concurrency"))
        self.assertEqual(self.p.get("permissions"), self.i.get("permissions"))
        self.assertEqual(_on(self.p).get("workflow_dispatch"),
                         _on(self.i).get("workflow_dispatch"))

    def test_the_run_step_is_byte_identical(self):
        """The step is what POSTs the door; a drift here is a drift in what runs."""
        a = self.p["jobs"]["cycle"]["steps"][0]["run"]
        b = self.i["jobs"]["cycle"]["steps"][0]["run"]
        self.assertEqual(a, b)

    def test_it_still_only_writes_through_POST_run_1(self):
        """The positive control: a verbatim body must still carry the thing that matters."""
        self.assertIn("admin/fleet-cycle?run=1", self.p["jobs"]["cycle"]["steps"][0]["run"])
        self.assertIn("-X POST", self.p["jobs"]["cycle"]["steps"][0]["run"])


class TestTheCron(unittest.TestCase):
    """(3)."""

    def test_the_pending_cron_is_1200Z_on_weekdays_and_is_the_only_one(self):
        sched = _on(_load(PENDING))["schedule"]
        self.assertEqual(sched, [{"cron": "0 12 * * 1-5"}])

    def test_it_differs_from_the_installed_cron_or_the_handover_is_pointless(self):
        self.assertNotEqual(_on(_load(PENDING))["schedule"],
                            _on(_load(INSTALLED))["schedule"])

    def test_the_header_carries_the_measurement_the_cron_is_derived_from(self):
        with io.open(PENDING, encoding="utf-8") as fh:
            head = fh.read().split("\non:")[0]
        for needle in ("17m48s", "18m28s", "16m16s", "3.5-7.5h", "12:00Z + 7.5h"):
            self.assertIn(needle, head, "the derivation must travel with the file")
        self.assertIn("ONE INSTALL", head.upper())


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
