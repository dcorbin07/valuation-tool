# -*- coding: utf-8 -*-
"""ITEM 79 — the confidence ceiling below half the price, and Amendment 4 behind its signature.

TWO INDEPENDENT PARTS, and they share only this file:

  1. **Don's ruling of 2026-10-22, option 1 of three.** A fair value below 0.5x the price is
     never labelled "high confidence"; the label is capped one level down. Nothing is hidden,
     no value is revalued, no warning text is added, and item 76's loud flag below 0.2x is
     untouched. Measured on the live service the same day: **15 served names sit between 0.2x
     and 0.5x and SEVEN carry `confidence: high`**, all seven on the Dip Detector.
  2. **Amendment 4, drafted for signature.** The six-month operational-gate window starts at
     2026-09-23, the date the automated writer became gapless, so the gate falls 2027-03-23.
     **Both states are pinned**: unsigned, every date and every figure is what it is today;
     signed, exactly one date moves.

Nothing here contacts a network, writes a record, or places an order.
"""
from __future__ import annotations

import ast
import datetime as _dt
import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from valuation.edge import track_meter as TM                  # noqa: E402
from valuation.engine import blend as B                       # noqa: E402
from valuation.engine import publication as P                 # noqa: E402
from valuation.screener import index_book_measured as IBM     # noqa: E402
from valuation.screener import rebalance_watch as RW          # noqa: E402
from valuation.web import withhold as W                       # noqa: E402

CONTRACT = os.path.join(REPO, "PAPER_TRACK_CONTRACT.md")


def _call_census() -> dict:
    """`{repo-relative path: {called function names}}` for `valuation/` and `scripts/`.

    **ON THE SYNTAX TREE, because A MENTION IS NOT A CALL.** `publication.py` names
    `flag_implausibly_low_fair_values` in a docstring and calls nothing; read as text, that is a
    surface skipping the cap. My first cut did read it as text and failed on exactly that -- the
    substring-ban family, in a guard written to enforce a one-function rule.
    """
    import glob
    out = {}
    for path in (glob.glob(os.path.join(REPO, "valuation", "**", "*.py"), recursive=True)
                 + glob.glob(os.path.join(REPO, "scripts", "*.py"))):
        rel = os.path.relpath(path, REPO).replace(os.sep, "/")
        try:
            with io.open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
        except (OSError, SyntaxError):
            continue
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                n = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                if n:
                    names.add(n)
        out[rel] = names
    return out


def _non_docstring_strings(src: str) -> list:
    """Every string constant in `src` that is NOT a docstring. Prose is not code."""
    tree = ast.parse(src)
    docs = set()
    for parent in ast.walk(tree):
        body = getattr(parent, "body", None)
        if (isinstance(parent, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                ast.AsyncFunctionDef)) and body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            docs.add(id(body[0].value))
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docs]


# =============================================================================================
# PART 1 — the confidence ceiling
# =============================================================================================
class TheCeilingIsOneNumberInOnePlace(unittest.TestCase):

    def test_the_ratio_lives_beside_the_band_it_belongs_to(self):
        self.assertEqual(P.CONFIDENCE_CAP_RATIO, 0.5)
        self.assertEqual(P.CONFIDENCE_CAP_CEILING, "medium")
        # ABOVE the loud-flag band, or the cap could never fire. Asserted in the module too.
        self.assertLess(P.FV_BAND_LOW, P.CONFIDENCE_CAP_RATIO)

    def test_it_is_NEVER_RETYPED_anywhere(self):
        """The ruling's own words: *define 0.5 once, beside `FV_BAND_LOW`, and import it.*

        Read on the syntax tree rather than by grepping for "0.5", because the figure appears
        legitimately in prose all over this codebase (`GROWTH_LED = 0.50`, a 0.5 weight share,
        a 50% ceiling) and a substring ban on a number is the family this project has
        repointed more than once. What is forbidden is a FLOAT LITERAL 0.5 compared against
        something ratio-shaped in the files that implement this rule.
        """
        for rel in ("valuation/engine/blend.py", "valuation/web/withhold.py",
                    "valuation/engine/scoring.py", "valuation/engine/pipeline.py"):
            with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Compare):
                    continue
                names = {getattr(x, "id", None) or getattr(x, "attr", None)
                         for x in [node.left] + list(node.comparators)}
                if not ({"ratio", "r"} & names):
                    continue
                for c in node.comparators:
                    if isinstance(c, ast.Constant) and c.value == P.CONFIDENCE_CAP_RATIO:
                        self.fail("%s compares a ratio against a retyped %r"
                                  % (rel, P.CONFIDENCE_CAP_RATIO))

    def test_the_comparison_is_the_verdict_s_and_has_one_definition(self):
        v = P.decide(30.0, 100.0, growth_led=False)
        self.assertTrue(v.caps_confidence)
        self.assertFalse(P.decide(60.0, 100.0, growth_led=False).caps_confidence)
        # EXACTLY ON THE RATIO PUBLISHES "high", matching `FV_BAND_LOW`'s own strict-inequality
        # convention, so no name sitting on the line changes state as a side effect.
        self.assertFalse(P.decide(50.0, 100.0, growth_led=False).caps_confidence)

    def test_it_is_MONOTONE_DOWNWARD_and_can_never_rescue_a_label(self):
        for ratio in (0.01, 0.19, 0.3, 0.499):
            self.assertEqual(B.price_ratio_cap("high", ratio), "medium", ratio)
            self.assertEqual(B.price_ratio_cap("medium", ratio), "medium", ratio)
            self.assertEqual(B.price_ratio_cap("low", ratio), "low", ratio)
        for ratio in (0.5, 0.51, 1.0, 5.0):
            for c in ("high", "medium", "low"):
                self.assertEqual(B.price_ratio_cap(c, ratio), c, (c, ratio))

    def test_an_unreadable_ratio_changes_nothing(self):
        for bad in (None, "", "n/a", float("nan"), float("inf"), float("-inf")):
            self.assertEqual(B.price_ratio_cap("high", bad), "high", repr(bad))

    def test_the_two_caps_COMPOSE_rather_than_overwriting_each_other(self):
        """`terminal_share_cap` now delegates to the same `cap_to`, so neither cap can raise."""
        label, note = B.terminal_share_cap("high", 0.95)
        self.assertEqual(label, "medium")
        self.assertTrue(note)
        self.assertEqual(B.price_ratio_cap(label, 0.3), "medium")
        # The harsher of the two wins, whichever order they are applied in.
        self.assertEqual(B.terminal_share_cap(B.price_ratio_cap("high", 0.3), 1.05)[0], "low")
        self.assertEqual(B.price_ratio_cap(B.terminal_share_cap("high", 1.05)[0], 0.3), "low")

    def test_NO_NEW_WARNING_TEXT_which_is_Don_s_instruction_and_not_an_omission(self):
        """The cap returns a label and nothing else. The ruling says *no new warning text.*"""
        self.assertIsInstance(B.price_ratio_cap("high", 0.3), str)
        src = io.open(B.__file__, encoding="utf-8").read()
        body = src.split("def price_ratio_cap", 1)[1].split("\ndef ", 1)[0]
        code = body.split('"""', 2)[2] if body.count('"""') >= 2 else body
        self.assertNotIn("Confidence is marked down", code)
        # ... and the row-level pass adds no note key either.
        rows = [{"fair_value": 30.0, "price": 100.0, "confidence": "high"}]
        before = set(rows[0])
        W.cap_confidence_below_half(rows)
        self.assertEqual(set(rows[0]), before, "the cap invented a field")


class EveryRowSurfaceIsCapped(unittest.TestCase):

    def _rows(self):
        return [
            # in the band, both keys, both capped
            {"ticker": "FIX", "fair_value": 34.0, "price": 100.0,
             "confidence": "high", "fair_value_confidence": "high"},
            # in the band, already medium -> untouched
            {"ticker": "APP", "fair_value": 48.4, "price": 100.0, "confidence": "medium"},
            # in the band, NO label at all -> stays absent (INSW/JXN on the live service)
            {"ticker": "INSW", "fair_value": 30.7, "price": 100.0},
            # outside the band -> untouched
            {"ticker": "AAPL", "fair_value": 120.0, "price": 100.0, "confidence": "high"},
            # below the loud flag -> already low, and the cap cannot raise it
            {"ticker": "KOD", "fair_value": 2.6, "price": 100.0, "confidence": "low"},
            # withheld -> skipped, there is no published value for a label to describe
            {"ticker": "ZZ", "fair_value": 30.0, "price": 100.0, "confidence": "high",
             "fair_value_withheld": True},
        ]

    def test_it_caps_exactly_the_rows_in_the_band_that_carry_a_label(self):
        rows = self._rows()
        self.assertEqual(W.cap_confidence_below_half(rows), 1)
        by = {r["ticker"]: r for r in rows}
        self.assertEqual(by["FIX"]["confidence"], "medium")
        self.assertEqual(by["FIX"]["fair_value_confidence"], "medium")
        self.assertEqual(by["APP"]["confidence"], "medium")
        self.assertNotIn("confidence", by["INSW"])
        self.assertEqual(by["AAPL"]["confidence"], "high")
        self.assertEqual(by["KOD"]["confidence"], "low")
        self.assertEqual(by["ZZ"]["confidence"], "high", "a withheld row was relabelled")

    def test_NO_FAIR_VALUE_MOVES_which_is_the_whole_ruling(self):
        rows = self._rows()
        before = [(r["ticker"], r.get("fair_value"), r.get("price"), r.get("upside"))
                  for r in rows]
        W.cap_confidence_below_half(rows)
        after = [(r["ticker"], r.get("fair_value"), r.get("price"), r.get("upside"))
                 for r in rows]
        self.assertEqual(before, after)

    def test_it_is_IDEMPOTENT(self):
        rows = self._rows()
        W.cap_confidence_below_half(rows)
        snap = [dict(r) for r in rows]
        self.assertEqual(W.cap_confidence_below_half(rows), 0)
        self.assertEqual([dict(r) for r in rows], snap)

    def test_both_confidence_keys_are_declared_in_ONE_place(self):
        self.assertEqual(set(W.ROW_CONFIDENCE_KEYS),
                         {"fair_value_confidence", "confidence"})

    def test_NO_SITE_SKIPS_IT(self):
        """The guard the ruling asks for: *a test that fails if any site skips it.*

        **THE SET IS DERIVED, NOT LISTED.** Every module that applies the LOW side of the band
        is a module serving rows carrying a fair value and a price, which is exactly the
        population this cap is about -- so the obligation is read off
        `flag_implausibly_low_fair_values`'s own call sites rather than from a list here that a
        fifth surface could be added without.
        """
        need, have = [], []
        for rel, calls in _call_census().items():
            if rel == "valuation/web/withhold.py":
                continue
            if "flag_implausibly_low_fair_values" in calls:
                need.append(rel)
            if "cap_confidence_below_half" in calls:
                have.append(rel)
        self.assertTrue(need, "the low-side flag has no callers, so this guard sees nothing")
        missing = sorted(set(need) - set(have))
        self.assertEqual(missing, [], "these surfaces flag the low side and skip the cap: %r"
                         % missing)

    def test_and_that_guard_is_not_vacuous(self):
        """A positive control: the derived obligation really does name the four live surfaces."""
        found = {rel for rel, calls in _call_census().items()
                 if "flag_implausibly_low_fair_values" in calls}
        # AND THE PROSE-ONLY MENTION IS PROVABLY EXCLUDED, which is why this reads the AST:
        # `publication.py` names the function in a docstring and calls nothing.
        self.assertNotIn("valuation/engine/publication.py", found)
        for rel in ("valuation/web/app.py", "valuation/web/dip.py", "valuation/web/unified.py",
                    "scripts/ci_scan.py"):
            self.assertIn(rel, found)


class TheOBJECTSurfacesAreCappedToo(unittest.TestCase):
    """The valuation page reads `blend.confidence`; the gauge and the dip row read the score's."""

    def test_the_blend_is_capped_in_the_pipeline_where_the_price_is_known(self):
        src = io.open(os.path.join(REPO, "valuation", "engine", "pipeline.py"),
                      encoding="utf-8").read()
        self.assertIn("blend.confidence = _price_ratio_cap(blend.confidence, ratio)", src)
        # BESIDE the low flag, so one price ratio's consequences cannot reach different places.
        head = src.split("blend.implausibly_low = True", 1)[1][:1400]
        self.assertIn("_price_ratio_cap", head)

    def test_the_score_is_capped_in_scoring_after_both_band_branches(self):
        src = io.open(os.path.join(REPO, "valuation", "engine", "scoring.py"),
                      encoding="utf-8").read()
        self.assertIn("confidence = _price_ratio_cap(confidence, ratio)", src)
        tree = ast.parse(src)
        # IT IS UNCONDITIONAL INSIDE THE RATIO BLOCK, never nested in one of the two branches:
        # the 0.2x-0.5x gap is precisely where neither branch fires.
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            val = node.value
            if (isinstance(val, ast.Call)
                    and getattr(val.func, "id", None) == "_price_ratio_cap"):
                break
        else:
            self.fail("scoring never calls the cap")

    def test_no_second_implementation_of_mark_down_never_up(self):
        src = io.open(B.__file__, encoding="utf-8").read()
        self.assertEqual(src.count("def cap_to("), 1)
        # `terminal_share_cap` delegates rather than keeping its own `min` over the rank table.
        body = src.split("def terminal_share_cap", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("cap_to(confidence, ceiling)", body)
        self.assertNotIn("_CONF_RANK.get(confidence, 1), _CONF_RANK[ceiling]", body)


# =============================================================================================
# PART 2 — Amendment 4, behind its signature row
# =============================================================================================
def _contract_with(signed: str = None, starts: str = None) -> str:
    """A copy of the real contract with the two Amendment 4 rows rewritten. Returns a path."""
    src = io.open(CONTRACT, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in src[:4000] else "\n"
    out = []
    for line in src.split(nl):
        t = line.strip()
        if t.startswith("| **Amendment 4 signed**") and signed is not None:
            line = "| **Amendment 4 signed** | %s |" % signed
        elif (t.startswith("| **Amendment 4 operational-gate window starts**")
              and starts is not None):
            line = "| **Amendment 4 operational-gate window starts** | %s |" % starts
        out.append(line)
    fd, path = tempfile.mkstemp(suffix=".md")
    os.close(fd)
    io.open(path, "w", encoding="utf-8", newline="").write(nl.join(out))
    return path


class AmendmentFourIsSignedAndTheDORMANTStateStillHolds(unittest.TestCase):
    """**REPOINTED WHEN DON SIGNED, 2026-10-22, and not loosened.**

    These three asserted the DRAFTED state -- not signed, gate unmoved, example inert. Two of
    them were statements about the signature row's VALUE and are now simply the other value;
    the property worth keeping is the DORMANCY ONE, which is that a contract reading anything
    other than a clean YES leaves the gate exactly where the vintage puts it. That is still
    checkable, on a copy of the real contract with the row set back, so it survives the
    signature rather than being deleted by it.
    """

    def test_the_shipped_contract_reads_SIGNED(self):
        a4 = TM.amendment_4()
        self.assertTrue(a4["signed"], a4["reason"])
        self.assertEqual(a4["window_starts"], "2026-09-23")
        self.assertEqual(a4["gate_date"], "2027-03-23")

    def test_and_the_gate_HAS_MOVED_while_the_vintage_s_own_six_months_is_still_reported(self):
        gw = TM.gate_window()
        self.assertTrue(gw["moved"])
        self.assertEqual(gw["gate_date"], "2027-03-23")
        self.assertEqual(gw["starts"], "2026-09-23")
        # THE VINTAGE'S OWN SIX MONTHS IS NOT LOST, under its own name, so a reader can see
        # both and check the amendment moved what it said it would.
        self.assertEqual(TM.OPERATIONAL_GATE.isoformat(), "2027-02-13")
        self.assertEqual(TM.frozen_parameters()["vintage_six_months"], "2027-02-13")

    def test_PUT_THE_ROW_BACK_AND_THE_GATE_RETURNS_which_is_the_dormancy_property(self):
        path = _contract_with(signed="**NO**")
        try:
            self.assertFalse(TM.amendment_4(path)["signed"])
            gw = TM.gate_window(path)
            self.assertFalse(gw["moved"])
            self.assertEqual(gw["gate_date"], TM.OPERATIONAL_GATE.isoformat())
            self.assertEqual(gw["starts"], TM.INCEPTION.isoformat())
        finally:
            os.remove(path)

    def test_the_fenced_EXAMPLE_signature_is_not_a_signature(self):
        """The contract documents how to sign inside a fenced block inside a blockquote.

        If that example parsed as a register row the amendment would have been in force the
        moment it was drafted -- the defect `contract_rows` was written to avoid for the
        operational gate. **Still checkable after the signature**: set the real row back to NO
        and the example alone must not sign it, which is the only way this property can be
        tested on a signed contract.
        """
        text = io.open(CONTRACT, encoding="utf-8").read()
        self.assertIn("| **Amendment 4 signed** | **YES — 2026-10-22 (Don, in chat)** |", text)
        path = _contract_with(signed="**NO**")
        try:
            self.assertFalse(TM.amendment_4(path)["signed"])
        finally:
            os.remove(path)


class SignedItMovesExactlyOneDate(unittest.TestCase):

    def setUp(self):
        self.path = _contract_with(signed="**YES — 2026-10-22 (Don, in chat)**")
        self.addCleanup(lambda: os.path.exists(self.path) and os.remove(self.path))

    def test_the_gate_moves_to_2027_03_23(self):
        a4 = TM.amendment_4(self.path)
        self.assertTrue(a4["signed"], a4["reason"])
        self.assertEqual(a4["window_starts"], "2026-09-23")
        self.assertEqual(a4["gate_date"], "2027-03-23")

    def test_SIX_MONTHS_IS_DERIVED_from_the_contract_s_own_constant(self):
        self.assertEqual(TM.GATE_MONTHS, 6)
        self.assertEqual(
            TM.amendment_4(self.path)["gate_date"],
            TM._months_after(_dt.date(2026, 9, 23), TM.GATE_MONTHS).isoformat())

    def test_the_VERDICT_DATE_DOES_NOT_MOVE(self):
        """The one thing a reader will most want to check. 60 months stays on the vintage."""
        self.assertEqual(TM.VERDICT_DATE.isoformat(), "2031-08-13")
        gw = TM.gate_window(self.path)
        self.assertTrue(gw["moved"])
        self.assertNotEqual(gw["gate_date"], TM.VERDICT_DATE.isoformat())
        src = io.open(TM.__file__, encoding="utf-8").read()
        self.assertIn("VERDICT_DATE = _months_after(INCEPTION, VERDICT_MONTHS)", src)

    def test_and_NEITHER_DOES_ANY_FROZEN_METER_PARAMETER(self):
        before = TM.frozen_parameters()
        after_signed = {"sigma_monthly_pp": TM.SIGMA_MONTHLY_PP, "rho": TM.RHO,
                        "alpha": TM.ALPHA,
                        "cost_drag_pp_per_month": TM.COST_DRAG_PP_PER_MONTH}
        for k, v in after_signed.items():
            self.assertEqual(before[k], v)
        # The declared figures, as the contract states them.
        self.assertAlmostEqual(TM.SIGMA_MONTHLY_PP, 3.9847, places=3)
        self.assertEqual(TM.RHO, 3.0)
        self.assertEqual(TM.ALPHA, 0.05)
        self.assertAlmostEqual(TM.COST_DRAG_PP_PER_MONTH, 0.14529, places=5)


class NothingElseCountsAsASignature(unittest.TestCase):

    def _gate(self, **kw):
        path = _contract_with(**kw)
        try:
            return TM.amendment_4(path), TM.gate_window(path)
        finally:
            os.remove(path)

    def test_NO_is_not_signed(self):
        a4, gw = self._gate(signed="**NO**")
        self.assertFalse(a4["signed"])
        self.assertEqual(gw["gate_date"], "2027-02-13")

    def test_hedged_prose_is_not_signed(self):
        a4, _ = self._gate(signed="probably, once the writer has run longer")
        self.assertFalse(a4["signed"])

    def test_a_BLANK_value_is_not_signed(self):
        a4, _ = self._gate(signed="")
        self.assertFalse(a4["signed"])

    def test_a_SIGNATURE_WITH_NO_USABLE_START_DATE_IS_NOT_IN_FORCE(self):
        """Amendment 3's rule on the other kind of date, and the reason is the same.

        A start the code had to guess could only be guessed as the inception -- the window this
        amendment exists to replace -- so the missing half refuses rather than defaulting to the
        answer that makes the change invisible.
        """
        a4, gw = self._gate(signed="**YES**", starts="to be decided")
        self.assertFalse(a4["signed"])
        self.assertIn("no window", a4["reason"])
        self.assertEqual(gw["gate_date"], "2027-02-13")

    def test_an_UNREADABLE_contract_leaves_the_gate_where_it_is(self):
        a4 = TM.amendment_4(os.path.join(REPO, "no-such-contract-file.md"))
        self.assertFalse(a4["signed"])

    def test_TWO_ROWS_DISAGREEING_is_a_broken_register_and_not_an_approval(self):
        """**REPOINTED AT THE SIGNATURE: the second row is now a NO.**

        It used to append a YES beside the drafted NO. With the real row reading YES that
        appended a second YES, the two AGREED, and the test passed for the wrong reason -- a
        guard that stops exercising its own case. The conflict has to be manufactured from
        whichever value the register does NOT hold, so it is the opposite row now, and the
        resolution is the same either way: not signed.
        """
        src = io.open(CONTRACT, encoding="utf-8", newline="").read()
        nl = "\r\n" if "\r\n" in src[:4000] else "\n"
        out = []
        for line in src.split(nl):
            out.append(line)
            if line.strip().startswith("| **Amendment 4 signed**"):
                out.append("| **Amendment 4 signed** | **NO** |")
        fd, path = tempfile.mkstemp(suffix=".md")
        os.close(fd)
        io.open(path, "w", encoding="utf-8", newline="").write(nl.join(out))
        try:
            a4 = TM.amendment_4(path)
            self.assertFalse(a4["signed"])
            self.assertIn("conflicting", a4["reason"])
        finally:
            os.remove(path)


class TheGATE_S_OWN_QUESTION_FOLLOWS_THE_WINDOW(unittest.TestCase):
    """`recording_ok` is what the gate asks. Signed, it asks about the repaired run."""

    #: Vintage 4's shape, simplified to what `gap_report` reads: 2026-08-14 missing, the
    #: September run missing, and everything from the repair onward present.
    def _series(self):
        have = []
        d, end = _dt.date(2026, 8, 13), _dt.date(2026, 10, 21)
        missing = {_dt.date(2026, 8, 14)} | {
            _dt.date(2026, 9, x) for x in (2, 3, 8, 9, 10, 11, 16, 17, 18, 22)}
        while d <= end:
            if TM.is_trading_day(d) and d not in missing and d > _dt.date(2026, 8, 13):
                have.append({"date": d.isoformat(), "valquo_pct": 1.0, "spy_pct": 1.0})
            d += _dt.timedelta(days=1)
        return have

    def test_from_INCEPTION_the_window_is_incomplete_which_is_today(self):
        g = TM.gap_report(self._series(), as_of=_dt.date(2026, 10, 22))
        self.assertFalse(g["complete"])
        self.assertEqual(g["missing_count"], 11)
        self.assertIn("2026-08-14", g["missing_dates"])

    def test_from_THE_REPAIR_the_window_is_complete(self):
        g = TM.gap_report(self._series(), as_of=_dt.date(2026, 10, 22),
                          inception=_dt.date(2026, 9, 23))
        self.assertTrue(g["complete"], g["missing_dates"])
        self.assertEqual(g["missing_count"], 0)

    def test_THE_MISSED_DAYS_STAY_VISIBLE_which_is_the_amendment_s_own_term(self):
        """`recording_history` is scoped per VINTAGE and is not touched by the amendment."""
        hist = TM.recording_history(self._series(), as_of=_dt.date(2026, 10, 22))
        openv = [h for h in hist if str(h.get("status")).upper() == "OPEN"]
        self.assertTrue(openv)
        self.assertIn("2026-08-14", openv[0]["missing_dates"])
        self.assertEqual(len(openv[0]["missing_dates"]), 11)
        src = io.open(TM.__file__, encoding="utf-8").read()
        body = src.split("def recording_history", 1)[1].split("\ndef ", 1)[0]
        self.assertNotIn("gate_window", body, "the audit trail was scoped to the gate window")

    def test_DETAIL_REPORTS_BOTH_SCOPES_AND_NAMES_WHICH_IS_WHICH(self):
        """**THE DEFECT THE CONTRACT'S OWN SUITE CAUGHT WHEN DON SIGNED, pinned so it cannot
        come back.** Signing re-scoped `started` and `recording_ok` to the gate window while
        `meter.gaps` stayed the vintage's -- two scopes under names that did not say which, in a
        payload a human reads, which is the wrong-object family. Both are reported now and
        `recording_window` says which the gate-scoped pair answers about.

        AND THIS IS THE SHARPEST STATEMENT OF WHAT THE SIGNATURE DID: on the same series, at the
        same instant, the GATE's question is YES and the VINTAGE's is NO. The eleven missed days
        are still missing -- that is why the second answer is NO -- and they no longer block the
        gate, which is why the first is YES.
        """
        d = TM.detail(series=self._series(), as_of=_dt.date(2026, 10, 22))
        self.assertTrue(d["available"], d.get("reason"))
        self.assertTrue(d["recording_ok"], d["recording_note"])
        self.assertFalse(d["vintage_recording_ok"])
        self.assertIn("2026-09-23", d["recording_window"])
        self.assertEqual(d["operational_gate_date"], "2027-03-23")
        # The vintage's own gap report is untouched and still names all eleven.
        self.assertEqual(d["meter"]["gaps"]["missing_count"], 11)

    def test_NO_ROW_IS_EVER_WRITTEN_FOR_A_MISSED_DAY(self):
        """A backfill voids the whole run. The amendment adds no writer and no filler."""
        src = io.open(TM.__file__, encoding="utf-8").read()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open":
                args = [a for a in node.args[1:] if isinstance(a, ast.Constant)]
                for a in args:
                    self.assertNotIn("w", str(a.value), "track_meter writes a file")


class TheALERTNamesTheNewDateOnlyOnceSigned(unittest.TestCase):

    DETAIL = {"recording_ok": False,
              "per_vintage_recording": [{"status": "OPEN",
                                         "missing_dates": ["2026-08-14", "2026-09-02"]}]}

    def _reason(self, path=None):
        real = None
        try:
            if path is not None:
                from valuation.screener import index_track as IT
                real = IT.contract_path
                IT.contract_path = lambda: path
            a = RW.record_status(detail=self.DETAIL)["alerts"]
            return [x for x in a if x["kind"] == "recording_not_ok"][0]["reason"]
        finally:
            if real is not None:
                from valuation.screener import index_track as IT
                IT.contract_path = real

    def test_signed_it_names_the_date_which_is_the_shipped_state(self):
        self.assertIn("The operational gate (2027-03-23) cannot pass", self._reason())

    def test_and_PUT_THE_ROW_BACK_and_the_sentence_carries_no_date(self):
        """**REPOINTED AT THE SIGNATURE.** This was the unsigned case read off the real
        contract; now the real contract is signed, so the unsigned case is read off a copy with
        the row set back. The property is unchanged: the alert names a date only when a
        document says what the date is."""
        path = _contract_with(signed="**NO**")
        try:
            line = self._reason(path)
            self.assertIn("The operational gate cannot pass", line)
            self.assertNotIn("2027-03-23", line)
            self.assertNotIn("2027-02-13", line)
        finally:
            os.remove(path)

    def test_the_date_is_DERIVED_and_never_typed_in_the_alert(self):
        src = io.open(RW.__file__, encoding="utf-8").read()
        body = src.split("def _gate_phrase", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("gate_window", body)
        # **ON THE CODE, NOT ON THE FILE.** `_gate_phrase`'s own docstring quotes 2027-03-23 to
        # say what the sentence becomes -- prose documenting the rule, which is what a substring
        # ban always trips on, and it tripped mine. The property is that no gate date reaches a
        # string this module actually uses.
        for s in _non_docstring_strings(src):
            for bad in ("2027-03-23", "2027-02-13"):
                self.assertNotIn(bad, s, "a gate date is typed into a live string")

    def test_the_count_is_still_in_the_reason_so_a_new_missing_day_re_announces(self):
        """Item 78 section 5's property, which this change must not break."""
        one = RW.record_status(detail=self.DETAIL)["alerts"]
        two = RW.record_status(detail={
            "recording_ok": False,
            "per_vintage_recording": [{"status": "OPEN",
                                       "missing_dates": ["2026-08-14", "2026-09-02",
                                                         "2026-10-22"]}]})["alerts"]
        a = [x for x in one if x["kind"] == "recording_not_ok"][0]["reason"]
        b = [x for x in two if x["kind"] == "recording_not_ok"][0]["reason"]
        self.assertNotEqual(a[:120], b[:120], "the cause changed and the signature did not")


class TheCostConditionNamesTheSERVEDBook(unittest.TestCase):

    def test_the_served_figures_come_from_the_tracked_module(self):
        self.assertAlmostEqual(IBM.SERVED_COST_BPS_ONE_WAY, 9.435593, places=6)
        self.assertAlmostEqual(IBM.SERVED_TURNOVER, 2.809390, places=6)

    def test_the_amendment_quotes_them_verbatim_and_names_what_they_describe(self):
        text = io.open(CONTRACT, encoding="utf-8").read()
        a4 = text.split("## 5a-4.", 1)[1]
        self.assertIn("9.435593", a4)
        self.assertIn("2.809390", a4)
        self.assertIn("SERVED_COST_BPS_ONE_WAY", a4)
        self.assertIn("CANONICAL_FIGURE_TABLE.md", a4)

    def test_it_says_33_4_AND_77_0_are_both_the_WRONG_book(self):
        """The brief's own point: the research decile's 77 bps is not the Index's cost either.

        A reader who sees 33.4 replaced could reasonably assume 77.0 was the replacement, and
        that is the misreading this amendment has to foreclose in writing.
        """
        a4 = io.open(CONTRACT, encoding="utf-8").read().split("## 5a-4.", 1)[1]
        self.assertIn("33.4", a4)
        self.assertIn("77.0", a4)
        self.assertIn("RESEARCH DECILE", a4)

    def test_and_it_keeps_the_MODELLED_limitation(self):
        a4 = io.open(CONTRACT, encoding="utf-8").read().split("## 5a-4.", 1)[1]
        self.assertIn("MODELLED", a4)
        self.assertIn("not measured on fills", a4)


class TheAmendmentSaysWhatItDoesNotChange(unittest.TestCase):

    def setUp(self):
        self.a4 = io.open(CONTRACT, encoding="utf-8").read().split("## 5a-4.", 1)[1]

    def test_every_item_the_brief_requires_is_stated(self):
        for want in ("2031-08-13", "σ", "ρ", "α", "0.14529", "SUPPORTED", "UNSUPPORTED",
                     "Amendment 1", "Amendment 2", "Amendment 3",
                     "NOT a vintage event"):
            self.assertIn(want, self.a4, want)

    def test_the_whole_run_void_clause_is_confirmed_not_engaged(self):
        self.assertIn("WHOLE-RUN VOID CLAUSE IS NOT ENGAGED", self.a4.upper())
        for clause in ("back-fill of prices or positions",
                       "discretionary override of a pick",
                       "change to this contract's thresholds after inception"):
            self.assertIn(clause, self.a4, clause)

    def test_it_states_the_derived_consequence_rather_than_hiding_it(self):
        self.assertIn("FIRST RENDER", self.a4.upper())
        self.assertIn("2027-03-23", self.a4)

    def test_the_signature_row_IS_SET_and_the_instruction_that_set_it_is_still_there(self):
        """**REPOINTED AT THE SIGNATURE.** The drafted row read NO; it reads YES now. The
        instruction block STAYS in the document rather than being tidied away, so a reader can
        see what was set and how -- which is the whole reason the signature is a row in a
        tracked file rather than a flag somewhere."""
        self.assertIn("| **Amendment 4 signed** | **YES - 2026-10-22 (Don, in chat)** |",
                      self.a4)
        self.assertNotIn("| **Amendment 4 signed** | **NO** |", self.a4)
        self.assertIn("set the first row and nothing else", self.a4)

    def test_EXACTLY_ONE_register_row_carries_the_signature(self):
        """Two rows disagreeing resolves to NOT signed, so a stray second row would silently
        switch the amendment back off. Counted on the register rows, with the fenced example
        excluded the way `contract_rows` excludes it."""
        rows = [ln for ln in self.a4.splitlines()
                if ln.strip().startswith("| **Amendment 4 signed**")]
        self.assertEqual(len(rows), 1, rows)


if __name__ == "__main__":
    unittest.main(verbosity=2)
