# -*- coding: utf-8 -*-
"""AMENDMENT 3 — a distribution is RECEIVED. Drafted for Don's signature; DORMANT until he signs.

Don approved the rule on 2026-10-17 on item 69's finding: the record contributes `cur / base - 1`
on the vendor's adjusted close, and the vendor left **Aptiv's** spin-off as a **−10.58%** cliff
and **Unilever's** demerger as **−7.03%** — losses no holder suffered, because they also held the
shares that were handed out. Amendment 2's rule cannot catch it: its trigger is *"acquired or
stops trading"*, and a spin-off is the one action where the held name keeps trading.

**THREE PROPERTIES CARRY THE WHOLE THING AND EACH IS PINNED HERE:**

1. **UNSIGNED, THE RECORD IS BIT-IDENTICAL.** The contract is the switch, read on every mark —
   not a description of a switch somewhere else.
2. **NO BACKFILL.** A segment whose base predates the effective date cannot be touched, and that
   is structural: the credit window is `base < distribution <= mark`, so a segment that opened
   after the event has already priced it into its own base.
3. **SIGNED AND IN WINDOW, THE FAKE LOSS GOES.** Without this the first two are satisfied by a
   rule that never does anything.

Nothing here touches a network or a credential, and nothing in this file signs the amendment.
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

import state_isolation   # noqa: E402,F401

from valuation.screener import index_mark as IM      # noqa: E402
from valuation.screener import index_track as IT      # noqa: E402

CONTRACT = os.path.join(REPO, "PAPER_TRACK_CONTRACT.md")

#: Aptiv's MEASURED cliff -- 69.44 to 62.09 on the distribution date (item 68), which the
#: record's vendor recorded as no action at all. The holder also received 1 VGNT per 3 APTV.
APTV_CLIFF = 62.09 / 69.440002

#: And the value that was actually distributed, per parent share: VGNT's first regular-way close
#: of 27.85 divided by the 3-for-1 ratio. **The construction is named because it is a CHOICE** --
#: a when-issued price and an official declared value are different numbers.
APTV_DISTRIBUTED = 27.85 / 3.0


def contract_with(signed, effective, path):
    """A contract carrying the two Amendment 3 rows, written to `path`.

    Built from the REAL document so the parser is exercised against the real surrounding
    markdown -- blockquotes, fenced examples and all -- rather than against two lines that
    happen to parse.
    """
    txt = io.open(CONTRACT, encoding="utf-8").read()
    txt = txt.replace("| **Amendment 3 signed** | **NO** |",
                      "| **Amendment 3 signed** | **%s** |" % signed)
    txt = txt.replace("| **Amendment 3 effective from segment base** | **2027-01-25** |",
                      "| **Amendment 3 effective from segment base** | **%s** |" % effective)
    io.open(path, "w", encoding="utf-8").write(txt)
    return path


class TheContractIsTheSwitch(unittest.TestCase):
    """**AS SHIPPED, AMENDMENT 3 IS NOT IN FORCE**, and the reason names the row."""

    def test_it_is_UNSIGNED_as_shipped(self):
        got = IM._amendment_3()
        self.assertFalse(got["signed"])
        self.assertIsNone(got["effective_from"])
        self.assertIn("amendment 3 signed", got["reason"])

    def test_the_contract_SAYS_it_is_a_draft(self):
        txt = io.open(CONTRACT, encoding="utf-8").read()
        self.assertIn("AMENDMENT 3", txt)
        self.assertIn("DRAFT — AWAITING DON'S SIGNATURE. NOT IN FORCE.", txt)
        self.assertIn("| **Amendment 3 signed** | **NO** |", txt)

    def test_a_signature_makes_it_in_force(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        p = contract_with("YES - 2026-10-20", "2027-01-25",
                          os.path.join(tmp, "contract.md"))
        got = IM._amendment_3(p)
        self.assertTrue(got["signed"], got["reason"])
        self.assertEqual(got["effective_from"], "2027-01-25")

    def test_HEDGED_PROSE_IS_NOT_A_SIGNATURE(self):
        """`index_track`'s own lesson: its first implementation read `yes-ish, mostly` as a pass.
        The vocabulary is reused rather than re-invented, so that cannot happen twice."""
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        for value in ("NO", "pending", "", "yes-ish, mostly", "probably", "not yet"):
            p = contract_with(value, "2027-01-25", os.path.join(tmp, "c.md"))
            self.assertFalse(IM._amendment_3(p)["signed"], "%r read as signed" % value)

    def test_TWO_ROWS_DISAGREEING_IS_A_BROKEN_REGISTER_not_an_approval(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        p = contract_with("YES - 2026-10-20", "2027-01-25", os.path.join(tmp, "c.md"))
        txt = io.open(p, encoding="utf-8").read()
        txt += "\n\n| **Amendment 3 signed** | **NO** |\n"
        io.open(p, "w", encoding="utf-8").write(txt)
        got = IM._amendment_3(p)
        self.assertFalse(got["signed"])
        self.assertIn("conflicting", got["reason"])

    def test_SIGNED_WITH_NO_EFFECTIVE_DATE_IS_NOT_IN_FORCE(self):
        """**THE REFUSING DIRECTION, and it matters.** A signature with no segment base would
        reach every segment including recorded ones — the backfill the amendment forbids — so the
        missing half refuses rather than defaulting to all of it."""
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        p = contract_with("YES - 2026-10-20", "(not set)", os.path.join(tmp, "c.md"))
        got = IM._amendment_3(p)
        self.assertFalse(got["signed"])
        self.assertIn("no segment base", got["reason"])

    def test_an_unreadable_contract_is_NOT_in_force(self):
        got = IM._amendment_3(os.path.join(tempfile.mkdtemp(), "absent.md"))
        self.assertFalse(got["signed"])

    def test_ONE_PARSER_reads_the_contract(self):
        """`B7`. A second reader of the document that governs the record would be a second
        definition of what it says, on the worst possible file."""
        src = io.open(IM.__file__, encoding="utf-8").read()
        self.assertIn("_it.contract_rows(", src)
        self.assertEqual(src.count("def contract_rows("), 0,
                         "index_mark defines its own contract parser")
        tr = io.open(IT.__file__, encoding="utf-8").read()
        self.assertEqual(tr.count("def contract_rows("), 1)

    def test_THE_OPERATIONAL_GATE_STILL_READS_THE_SAME(self):
        """The extraction must not have moved `gate_state`: it decides the public posture."""
        got = IT.gate_state()
        self.assertFalse(got["passed"])
        self.assertTrue(got["contract_present"])
        self.assertIn("not a pass", got["reason"])


class TheCreditWindowIsWhatMakesNoBackfillStructural(unittest.TestCase):
    """Only a distribution strictly AFTER the segment base and on or before the mark counts: the
    base price already reflects one that happened before it, so crediting it would invent a gain."""

    EV = ({"ticker": "APTV", "date": "2026-11-05",
           "value_per_parent_share": APTV_DISTRIBUTED,
           "source": "VGNT first regular-way close 27.85 / 3"},)

    def test_inside_the_window_it_counts(self):
        got = IM.distribution_credit("APTV", "2026-10-22", "2026-11-30",
                                     distributions=self.EV)
        self.assertAlmostEqual(got["credit"], APTV_DISTRIBUTED, places=6)
        self.assertEqual(len(got["events"]), 1)

    def test_BEFORE_the_segment_base_it_does_NOT(self):
        """**THE ONE THAT MATTERS: the base already priced it in.** This is also why no-backfill
        is structural rather than a policy somebody could forget."""
        got = IM.distribution_credit("APTV", "2026-11-30", "2026-12-30",
                                     distributions=self.EV)
        self.assertEqual(got["credit"], 0.0)
        self.assertIn("no declared distribution", got["reason"])

    def test_AFTER_the_mark_it_does_not_count_yet(self):
        got = IM.distribution_credit("APTV", "2026-10-22", "2026-11-01",
                                     distributions=self.EV)
        self.assertEqual(got["credit"], 0.0)

    def test_ON_the_segment_base_it_does_NOT_count(self):
        """A distribution dated exactly on the base is in the base's own price. Strictly after,
        deliberately: an off-by-one here is a free gain on every event."""
        got = IM.distribution_credit("APTV", "2026-11-05", "2026-11-30",
                                     distributions=self.EV)
        self.assertEqual(got["credit"], 0.0)

    def test_ON_the_mark_it_DOES(self):
        got = IM.distribution_credit("APTV", "2026-10-22", "2026-11-05",
                                     distributions=self.EV)
        self.assertGreater(got["credit"], 0.0)

    def test_another_name_is_untouched(self):
        self.assertEqual(IM.distribution_credit("AAPL", "2026-10-22", "2026-11-30",
                                                distributions=self.EV)["credit"], 0.0)

    def test_the_declared_list_is_EMPTY_today_and_that_is_reported_not_assumed(self):
        """No event has occurred inside a segment on or after the effective date. The two
        measured cases predate the record's 2026-07-30 inception."""
        self.assertEqual(IM.DISTRIBUTIONS, ())
        row = IT.contract_rows("amendment 3 declared distributions")
        self.assertEqual(row["values"], ["0"])

    def test_a_malformed_entry_is_SKIPPED_rather_than_credited(self):
        """A zero, a negative, an absent value or an unreadable date credits nothing. An entry
        this cannot read must not become a gain."""
        bad = ({"ticker": "APTV", "date": "2026-11-05"},
               {"ticker": "APTV", "date": "2026-11-05", "value_per_parent_share": 0.0},
               {"ticker": "APTV", "date": "2026-11-05", "value_per_parent_share": -5.0},
               {"ticker": "APTV", "date": "not-a-date", "value_per_parent_share": 9.0})
        got = IM.distribution_credit("APTV", "2026-10-22", "2026-11-30", distributions=bad)
        self.assertEqual(got["credit"], 0.0)
        self.assertEqual(got["events"], [])


class ItChangesTheRecordONLYWhenSignedAndInWindow(unittest.TestCase):
    """Driven through `contract_row` itself, with an injected price tape."""

    BASE_BEFORE, BASE_AFTER = "2026-10-22", "2027-01-25"
    MARK_BEFORE, MARK_AFTER = "2026-11-30", "2027-02-01"

    def _fetch(self, closes):
        import pandas as pd

        def fetch(ticker, days=400, as_of=None, **kw):
            rows = closes.get(str(ticker).upper())
            if not rows:
                return pd.DataFrame()
            # Date/Close is the shape `prices.get_history_df` returns.
            df = pd.DataFrame({"Date": list(rows.keys()), "Close": list(rows.values())})
            df.attrs["valquo_src"] = "injected"
            return df
        return fetch

    def _book(self, tmp, base):
        meta = {"ok": True, "benchmark": "SPY", "inception_date": base, "scan_date": base,
                "positions": [{"ticker": "APTV", "weight": 0.5},
                              {"ticker": "AAPL", "weight": 0.5}]}
        p = os.path.join(tmp, "fixture_book.json")
        io.open(p, "w", encoding="utf-8").write(json.dumps(meta))
        return p

    def _run(self, *, signed, base, mark, dist_date):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        flat = {base: 100.0, mark: 100.0}
        # APTV falls by its measured spin-off cliff and nothing else moves.
        cliffed = {base: 100.0, mark: 100.0 * APTV_CLIFF}
        # The distributed value in the SAME units as the tape: 100 x (1 - cliff) is what left.
        per_share = 100.0 * (1.0 - APTV_CLIFF)
        real = IM.DISTRIBUTIONS
        try:
            IM.DISTRIBUTIONS = ({"ticker": "APTV", "date": dist_date,
                                 "value_per_parent_share": per_share,
                                 "source": "test fixture"},)
            cpath = contract_with(("YES - 2026-10-20" if signed else "NO"),
                                  self.BASE_AFTER, os.path.join(tmp, "contract.md"))
            orig = IM._amendment_3

            def patched(path=None):
                return orig(cpath)
            IM._amendment_3 = patched
            try:
                return IM.contract_row(
                    as_of=mark, meta_path=self._book(tmp, base),
                    fetch=self._fetch({"APTV": cliffed, "AAPL": flat, "SPY": flat}),
                    refuse_before_close=False)
            finally:
                IM._amendment_3 = orig
        finally:
            IM.DISTRIBUTIONS = real

    def test_UNSIGNED_the_fake_loss_STANDS(self):
        """**THE PROPERTY THAT MAKES THIS SAFE TO SHIP BEFORE DON SIGNS.** The record is what it
        was: item 69's finding is still true, and the amendment has not changed a number."""
        got = self._run(signed=False, base=self.BASE_AFTER, mark=self.MARK_AFTER,
                        dist_date="2027-01-28")
        self.assertTrue(got["ok"], got.get("reason"))
        self.assertLess(got["row"]["valquo_pct"], -4.0, got["row"])
        d = got
        self.assertFalse((d.get("amendment_3") or {}).get("signed"))
        self.assertEqual(d.get("distributions_credited"), [])

    def test_SIGNED_AND_IN_WINDOW_the_fake_loss_GOES(self):
        """**AND WITHOUT THIS THE TWO PROPERTIES ABOVE WOULD BE SATISFIED BY A RULE THAT NEVER
        DOES ANYTHING.** The holder lost nothing, so the book should read about zero."""
        got = self._run(signed=True, base=self.BASE_AFTER, mark=self.MARK_AFTER,
                        dist_date="2027-01-28")
        self.assertTrue(got["ok"], got.get("reason"))
        self.assertAlmostEqual(got["row"]["valquo_pct"], 0.0, places=4)
        d = got
        self.assertTrue((d.get("amendment_3") or {}).get("applies_to_this_segment"))
        self.assertEqual([x["ticker"] for x in d["distributions_credited"]], ["APTV"])

    def test_SIGNED_BUT_AN_EARLIER_SEGMENT_IS_UNTOUCHED(self):
        """**NO BACKFILL.** The amendment is in force and this segment opened before its
        effective date, so the row is what it always was."""
        got = self._run(signed=True, base=self.BASE_BEFORE, mark=self.MARK_BEFORE,
                        dist_date="2026-11-05")
        self.assertTrue(got["ok"], got.get("reason"))
        self.assertLess(got["row"]["valquo_pct"], -4.0, got["row"])
        d = got
        self.assertTrue((d.get("amendment_3") or {}).get("signed"))
        self.assertFalse((d.get("amendment_3") or {}).get("applies_to_this_segment"))
        self.assertEqual(d.get("distributions_credited"), [])

    def test_the_two_states_are_DISTINGUISHABLE_on_the_row(self):
        """*"No distribution was credited"* and *"the rule is not in force"* must not read the
        same — that collapse is what items 65, 67 and 69 each paid for on the live path."""
        off = self._run(signed=False, base=self.BASE_AFTER, mark=self.MARK_AFTER,
                        dist_date="2027-01-28")
        on = self._run(signed=True, base=self.BASE_BEFORE, mark=self.MARK_BEFORE,
                       dist_date="2026-11-05")
        self.assertEqual(off["distributions_credited"], on["distributions_credited"])
        self.assertNotEqual(off["amendment_3"]["signed"], on["amendment_3"]["signed"])


class WhatTheAmendmentDoesNotChange(unittest.TestCase):
    def test_amendment_2_is_untouched_and_still_in_force(self):
        src = io.open(IM.__file__, encoding="utf-8").read()
        self.assertIn('CORPORATE_ACTION_FROM = "2026-10-22"', src)
        txt = io.open(CONTRACT, encoding="utf-8").read()
        self.assertIn("acquired or stops trading", txt)

    def test_no_clock_no_sigma_no_threshold_moved(self):
        from valuation.edge import track_meter as TM
        # `SIGMA_MONTHLY_PP`, and it is DERIVED from the tracking error and the design effect
        # rather than typed -- so this reads the module's own value instead of a literal I would
        # otherwise be asserting against itself.
        self.assertAlmostEqual(TM.SIGMA_MONTHLY_PP, 3.9847, places=3)

    def test_the_amendment_says_it_is_NOT_a_vintage_event(self):
        txt = io.open(CONTRACT, encoding="utf-8").read()
        i = txt.index("## 5a-3. AMENDMENT 3")
        self.assertIn("not a vintage event", txt[i:].lower())

    def test_it_states_what_it_does_NOT_claim(self):
        """The limitation is the honest half: the value is taken at the distribution date and
        carried flat, making no claim about what the distributed shares did next -- in Amendment
        2's own terms."""
        txt = io.open(CONTRACT, encoding="utf-8").read()
        i = txt.index("## 5a-3. AMENDMENT 3")
        body = txt[i:]
        self.assertIn("NO CLAIM ABOUT WHAT THE DISTRIBUTED SHARES DID NEXT", body)
        self.assertIn("makes no claim about what the proceeds did next", body)

    def test_it_names_the_alternatives_and_the_known_gap(self):
        txt = io.open(CONTRACT, encoding="utf-8").read()
        i = txt.index("## 5a-3. AMENDMENT 3")
        body = txt[i:]
        for alt in ("Do nothing", "Treat it as an exit", "Switch the record's price vendor"):
            self.assertIn(alt, body)
        self.assertIn("nothing in this repository watches for a", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
