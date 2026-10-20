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
2. **The body is VERBATIM apart from the cron** - compared as TEXT, not as parsed YAML, so
   the two cannot drift into two different doors and the comments that carry the reasoning
   cannot drift either. (The first cut imported PyYAML; CI has none, and the land went red.)
3. **The cron is the 12:00Z one**, and it is the only schedule in the file.
4. **No second fleet schedule is left anywhere** after an install, modelled directly.

    python tests/test_fleet_schedule_handover.py
"""
from __future__ import annotations

import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import state_isolation  # noqa: F401,E402

PENDING = os.path.join(REPO, "pending_workflows", "fleet-cycle.yml")
INSTALLED = os.path.join(REPO, ".github", "workflows", "fleet-cycle.yml")


#: THE TWO DECLARED CRONS. `MA13`'s committed-literal idiom: the handover moves the installed
#: file from the first to the second, and a THIRD value has not been declared by anybody -- so
#: naming both is what lets this suite stay sharp after the install instead of going red on it.
CRON_BEFORE = "19 22 * * 1-5"       # 22:19Z, which GitHub's measured 3.5-7.5h delay pushed
                                    # past the dip row the entry rules read
CRON_AFTER = "0 12 * * 1-5"         # 12:00Z, inside regular hours across the whole delay range


def _handover_state():
    """`"pending"` or `"done"`, read from the installed cron. [repointed]

    **THE SUITE USED TO ASSERT THE PENDING STATE, WHICH MADE INSTALLING THE FILE -- the thing it
    exists to make safe -- THE EVENT THAT BROKE IT.** A guard keyed on "these two differ today"
    fires on the clock; the property it stood in for is that they differ in NOTHING BUT THE
    CRON, which holds in both states and is asserted in both.
    """
    inst = _crons(INSTALLED)
    if inst == [CRON_AFTER]:
        return "done"
    if inst == [CRON_BEFORE]:
        return "pending"
    # **AND A THIRD VALUE IS NEITHER, which the old form could not say.** An installed cron
    # nobody declared is a finding whatever the handover's state.
    raise AssertionError("the installed fleet cron is %r, which is neither the declared "
                         "before (%r) nor the declared after (%r)"
                         % (inst, CRON_BEFORE, CRON_AFTER))


def _text(p):
    with io.open(p, encoding="utf-8") as fh:
        return fh.read().replace("\r\n", "\n")


def _body(p):
    """Everything from the `on:` key down -- the part that must be verbatim.

    **COMPARED AS TEXT, NOT AS PARSED YAML, AND THAT IS BOTH STRONGER AND CHEAPER.** The first
    cut imported PyYAML and compared key by key; CI has no PyYAML, so the suite died with
    `ModuleNotFoundError` on the land -- the `guards that fail open in CI` family, except this
    one failed closed and blocked the branch. A byte comparison needs no dependency AND proves
    more: key-by-key equality would pass on two files whose comments had drifted, and the
    comments here carry the reasoning a future reader needs.
    """
    t = _text(p)
    i = t.index("\non:")
    return t[i:]


def _crons(p):
    return re.findall(r'^\s*-\s*cron:\s*"([^"]+)"', _text(p), re.M)


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


#: The steps item 74 adds to every workflow. A CLOSED LIST, named here rather than "anything
#: added is fine": a guard that permits arbitrary additions is not a guard. Each is monitoring
#: only -- a healthchecks ping and a Discord post on failure -- and none of them can change what
#: the door does.
ITEM_74_STEPS = ("item 74: healthchecks start", "item 74: tell Don this failed",
                 "item 74: healthchecks end")


def _strip_item74(src: str) -> str:
    """`src` with item 74's monitoring steps removed, so the verbatim guards keep their subject.

    **WHY THIS EXISTS [repointed item 74, and `MA59`'s rule -- in the same commit].** This
    class enforced *"the cron is the ONLY line that differs"* by comparing the whole jobs block
    byte for byte. That is exactly right for a handover whose only content is a cron change, and
    false the moment a second legitimate change arrives -- which item 74 is. The property it was
    really guarding is in its own docstring: *"or the two files become two different doors"*, and
    the door is one step. So the declared monitoring steps are removed and the comparison keeps
    asking its own question about everything else.

    Third repoint of this shape on this path, after item 71's `MB31` tripwire and item 72's bag
    list, and the pattern is identical each time: a guard asserting "these two things are equal
    today" fires on the clock, so assert the property the equality stood in for.

    A comment run above a step belongs to it, so the cut starts there.
    `TestTheBodyIsVerbatim.test_THE_STRIPPER_IS_NOT_VACUOUS` proves it both removes and keeps.
    """
    lines = src.split("\n")
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if ln.lstrip().startswith("- name:") and "item 74:" in ln:
            while out and (out[-1].lstrip().startswith("#") or not out[-1].strip()):
                out.pop()
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.lstrip().startswith("- name:") or (
                        nxt.strip() and not nxt.startswith("      ")):
                    break
                i += 1
            continue
        out.append(ln)
        i += 1
    return "\n".join(out)


class TestTheBodyIsVerbatim(unittest.TestCase):
    """(2) - or the two files become two different doors."""

    @staticmethod
    def _door_step(src):
        """The `POST the fleet-cycle door` step's own text -- the thing that must not drift.

        **STRIPPED FIRST, THEN SLICED.** Taking the slice from the raw text ends it at whatever
        step comes next, which in the pending file is item 74's comment block -- so the two
        sides differed by the trailing blank lines rather than by anything the door does.
        Trailing whitespace is normalised for the same reason: the subject is what the step
        does, not whether the file ends on a blank line.
        """
        src = _strip_item74(src)
        start = src.index("      - name: POST the fleet-cycle door")
        rest = src[start + 1:]
        nxt = rest.find("\n      - name:")
        return (rest[:nxt] if nxt >= 0 else rest).rstrip()

    def test_the_door_step_is_byte_identical_in_both_files(self):
        """The obligation, narrowed to the door: nothing it DOES may differ."""
        self.assertEqual(self._door_step(_body(PENDING)),
                         self._door_step(_body(INSTALLED)),
                         "the fleet-cycle door call differs between the pending and the "
                         "installed file -- two files, two doors")

    def test_ANYTHING_ADDED_IS_A_DECLARED_MONITORING_STEP_and_nothing_else(self):
        """The other half, and without it the narrowing above would permit anything.

        Every step name in one file and not the other must be one of item 74's three. A
        smuggled extra step, or a renamed door, still fails.
        """
        def names(src):
            return re.findall(r"^      - name:\s*(.+?)\s*$", src, re.M)

        pend, inst = names(_body(PENDING)), names(_body(INSTALLED))
        diff = set(pend) ^ set(inst)
        for extra in sorted(diff):
            self.assertTrue(any(k in extra for k in ITEM_74_STEPS),
                            "%r is in one file and not the other, and it is not one of item "
                            "74's monitoring steps" % extra)

    def test_THE_STRIPPER_IS_NOT_VACUOUS(self):
        """A stripper that removed everything would make the two guards below pass by seeing
        nothing -- the vacuous-pass family this project has paid for repeatedly. So it must
        remove the item-74 steps AND keep the door."""
        raw = _body(PENDING)
        out = _strip_item74(raw)
        self.assertIn("POST the fleet-cycle door", out, "the stripper ate the door")
        self.assertIn("admin/fleet-cycle?run=1", out)
        self.assertNotIn("item 74:", out, "the stripper left an item-74 step behind")
        self.assertLess(len(out), len(raw), "the stripper removed nothing at all")

    def test_the_body_is_byte_identical_once_the_cron_block_is_substituted(self):
        """The whole obligation, in one comparison: nothing but the schedule may differ."""
        # Trailing whitespace normalised: removing a step at the end of a file leaves a
        # different number of trailing newlines, and the subject is content.
        pend = _strip_item74(_body(PENDING)).rstrip()
        inst = _strip_item74(_body(INSTALLED)).rstrip()
        # **THE HANDOVER HAS RUN, OR IT HAS NOT, AND BOTH ARE LEGITIMATE.** This used to assert
        # the files DIFFER, which is only true while the pending file is pending -- so the
        # install that this suite exists to make safe is what broke it (`2dc5496`, pushed
        # straight to main by the installer, which does not go through the gate).
        state = _handover_state()
        if state == "pending":
            self.assertNotEqual(pend, inst,
                                "the handover is pending, so they must differ -- by the cron")
        else:
            self.assertEqual(pend, inst,
                             "the handover is DONE, so the installed file must be the pending "
                             "one verbatim -- if it is not, the installer copied something else")
        # swap the pending cron block back for the installed one and they must coincide
        pc, ic = _crons(PENDING), _crons(INSTALLED)
        self.assertEqual(len(pc), 1)
        self.assertEqual(len(ic), 1)
        a = re.sub(r'(?m)^(\s*#.*\n)*\s*-\s*cron:\s*"[^"]+"\n', "CRON\n", pend)
        b = re.sub(r'(?m)^(\s*#.*\n)*\s*-\s*cron:\s*"[^"]+"\n', "CRON\n", inst)
        self.assertEqual(a, b,
                         "the pending body differs from the installed one by more than its "
                         "cron -- two files, two doors, two schedules")

    def test_the_jobs_and_steps_text_is_present_verbatim(self):
        """A narrower restatement, so a failure says WHICH part drifted."""
        pend = _strip_item74(_body(PENDING)).rstrip()
        inst = _strip_item74(_body(INSTALLED)).rstrip()
        tail = inst[inst.index("jobs:"):]
        self.assertIn(tail, pend, "the jobs block must be verbatim")

    def test_it_still_only_writes_through_POST_run_1(self):
        """The positive control: a verbatim body must still carry the thing that matters."""
        pend = _body(PENDING)
        self.assertIn("admin/fleet-cycle?run=1", pend)
        self.assertIn("-X POST", pend)


class TestTheCron(unittest.TestCase):
    """(3)."""

    def test_the_pending_cron_is_1200Z_on_weekdays_and_is_the_only_one(self):
        self.assertEqual(_crons(PENDING), ["0 12 * * 1-5"])

    def test_the_installed_cron_is_one_of_THE_TWO_DECLARED_VALUES(self):
        """**REPOINTED.** This read `assertNotEqual(pending, installed)` -- *"or the handover is
        pointless"* -- which is a statement that the handover has not happened, and it went red
        the moment it did. The durable property is that the installed cron is the declared
        before-value or the declared after-value and never a third thing, and
        `_handover_state()` raises on anything else."""
        self.assertIn(_handover_state(), ("pending", "done"))
        self.assertIn(_crons(INSTALLED)[0], (CRON_BEFORE, CRON_AFTER))

    def test_and_the_handover_actually_MOVES_the_cron(self):
        """The thing the old assertion was reaching for, stated as a property of the two
        DECLARED values rather than of today's files: the handover is not pointless because the
        two crons it moves between are different."""
        self.assertNotEqual(CRON_BEFORE, CRON_AFTER)
        self.assertEqual(_crons(PENDING), [CRON_AFTER])

    def test_the_header_carries_the_measurement_the_cron_is_derived_from(self):
        with io.open(PENDING, encoding="utf-8") as fh:
            head = fh.read().split("\non:")[0]
        for needle in ("17m48s", "18m28s", "16m16s", "3.5-7.5h", "12:00Z + 7.5h"):
            self.assertIn(needle, head, "the derivation must travel with the file")
        self.assertIn("ONE INSTALL", head.upper())


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
