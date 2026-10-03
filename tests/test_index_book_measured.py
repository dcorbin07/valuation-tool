# -*- coding: utf-8 -*-
"""ITEM 18 — the Index's backtest is the SERVED book's, and its figures cannot go stale silently.

WHAT THIS GUARDS
----------------
`index_book_measured` holds committed literals, which is the family that produced E9 and E12 one
session ago. The difference, and the reason these tests exist: a stale-literal defect is a figure
that tracks a CLOCK — a trial count, a universe size, a date — and no test can pin it. These
track a dated STUDY with a committed artifact, so they CAN be pinned, against the record itself.

`TheConstantsMatchTheCommittedRecord` asserts every figure appears verbatim in BOTH
`HANDOFF_edge_audit.md` and `VALQUO_LEDGER.md`. Re-run `INDEX-BOOK` and the record moves; the
record moving turns this suite red and the module has to be updated with it. That is `MA13`'s
committed-literal idiom: the human record and the machine record are the same bytes.

THE BUILD PATH IS NOT TOUCHED, AND IT IS PROVED RATHER THAN PROMISED
--------------------------------------------------------------------
Item 18 forbids changing how a rebalance book is BUILT. `headline_scope` is a disclosure field,
so `TheDisclosureIsInertOnTheBook` runs `build_index` against the pre-change source restored from
git and requires every field a book consists of to be identical across both arms — and PRINTS the
counts, because the first cut of that proof built from the local store's ONE-NAME fixture and
"nothing moved" meant almost nothing. A proof with no reach is the vacuous-pass family.
"""
import importlib
import io
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from valuation.screener import index_book_measured as M      # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDOFF = os.path.join(REPO, "HANDOFF_edge_audit.md")
LEDGER = os.path.join(REPO, "VALQUO_LEDGER.md")
VI = os.path.join(REPO, "valuation", "edge", "valquo_index.py")


def _read(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()


def _norm(s):
    """Typographic minus and en-dash normalised to ASCII. A test comparing a NUMBER in prose
    must compare the number and not the glyph — the first cut of the spec test failed on
    `-0.0576` because the record writes it with U+2212."""
    return s.replace("−", "-").replace("–", "-")


class TheConstantsMatchTheCommittedRecord(unittest.TestCase):
    """The anti-stale guard. Both inputs are tracked, so this runs on a CI runner."""

    #: Every figure the module publishes, with the spelling the record uses.
    FIGURES = (
        ("SERVED_ROTH_PCT", "17.1619"),
        ("SERVED_TAXABLE_PCT", "12.2033"),
        ("TAX_COST_PP", "4.9586"),
        ("SERVED_NET_PCT", "17.1817"),
        ("SERVED_ROTH_SHARPE", "1.0318"),
        ("SERVED_TAXABLE_SHARPE", "0.7595"),
        ("SERVED_TURNOVER", "2.4372"),
        ("SERVED_COST_BPS_ONE_WAY", "9.58"),
        ("ALPHA_VS_OWN_TIER_PP", "4.1209"),
        ("ALPHA_VS_OWN_TIER_EARLY_PP", "4.0615"),
        ("ALPHA_VS_OWN_TIER_LATE_PP", "4.1746"),
        ("ALPHA_VS_SPY_PP", "1.9488"),
        ("ALPHA_VS_SPY_EARLY_PP", "3.7202"),
        ("ALPHA_VS_SPY_LATE_PP", "0.2702"),
        ("ALPHA_VS_ALL_CAP_EW_PP", "-0.0576"),
        ("SERVED_TE_VS_SPY", "8.4381"),
        ("RESEARCH_NET_PCT", "23.2893"),
        ("RESEARCH_ALPHA_VS_EW_PP", "6.0500"),
        ("RESEARCH_ALPHA_VS_SPY_PP", "8.0564"),
        ("RESEARCH_SHARPE", "1.0997"),
        ("RESEARCH_TE_VS_SPY", "11.3878"),
        ("CONTRACT_EDGE_IN_USE_PP", "9.9864"),
    )

    def test_both_records_are_present(self):
        """A guard whose input is absent passes while checking nothing."""
        self.assertTrue(os.path.exists(HANDOFF))
        self.assertTrue(os.path.exists(LEDGER))

    def test_every_constant_is_the_value_the_module_declares(self):
        """The literal in the table above must equal the module's own constant, or this suite
        is checking the table against the record and never the code."""
        for name, text in self.FIGURES:
            self.assertAlmostEqual(getattr(M, name), float(text), places=4,
                                   msg="%s does not equal %s" % (name, text))

    def test_every_figure_appears_in_the_handoff(self):
        h = _norm(_read(HANDOFF))
        for name, text in self.FIGURES:
            self.assertIn(text, h, "%s (%s) is not in INDEX-BOOK's handoff record" % (name, text))

    #: The ledger carries the headline figures; three are handoff-only detail. MEASURED rather
    #: than assumed — the first cut asserted all but one were present and four were not.
    LEDGER_ONLY_IN_HANDOFF = ("SERVED_TAXABLE_SHARPE", "SERVED_TE_VS_SPY", "RESEARCH_NET_PCT")

    def test_every_figure_the_ledger_carries_is_the_same_figure(self):
        """THE LEDGER SPELLS A NEGATIVE AS A WORD. Its row reads "MINUS 0.0576pp" rather than
        using a sign, so normalising the glyph is not enough — the prose form has to be
        normalised too. Found by this test failing on four figures when it expected one."""
        lg = _norm(_read(LEDGER)).replace("MINUS ", "-").replace("PLUS ", "+")
        missing = [n for n, t in self.FIGURES if t not in lg]
        self.assertEqual(sorted(missing), sorted(self.LEDGER_ONLY_IN_HANDOFF),
                         "the ledger's figure set moved: %r" % (missing,))

    def test_the_handoff_is_the_binding_record_and_carries_every_figure(self):
        """So the three the ledger omits are still pinned somewhere tracked."""
        h = _norm(_read(HANDOFF))
        for name in self.LEDGER_ONLY_IN_HANDOFF:
            text = dict((n, t) for n, t in self.FIGURES)[name]
            self.assertIn(text, h, "%s (%s) is pinned nowhere" % (name, text))

    def test_the_months_to_detect_appears_with_its_thousands_separator(self):
        self.assertIn("{:,}".format(M.SERVED_MONTHS_TO_DETECT), _read(HANDOFF))

    def test_the_provenance_resolves_to_a_REAL_commit_that_names_the_study(self):
        """Checked against GIT rather than against the markdown, which is where it belongs:
        neither the ledger nor the handoff records the sha, so asserting it appears in them
        fails against a correct tree. Git is the authority on whether a commit exists."""
        self.assertEqual(M.STUDY, "INDEX-BOOK")
        self.assertTrue(M.STUDY_COMMIT)
        r = subprocess.run(["git", "log", "-1", "--format=%s", M.STUDY_COMMIT],
                           cwd=REPO, capture_output=True)
        if r.returncode != 0:
            self.skipTest("commit %s not reachable in this checkout" % M.STUDY_COMMIT)
        subject = r.stdout.decode("utf-8", "replace")
        self.assertIn("INDEX-BOOK", subject,
                      "%s is not the study's commit: %r" % (M.STUDY_COMMIT, subject))

    def test_the_study_has_a_record_row_at_all(self):
        self.assertIn("INDEX-BOOK", _read(LEDGER))
        self.assertIn("INDEX-BOOK", _read(HANDOFF))


class BothAlphaLegsAreStructurallyInseparable(unittest.TestCase):
    """`INDEX-BOOK`'s void condition: "BOTH ALPHA SENTENCES ARE TRUE AND NEITHER MAY TRAVEL
    ALONE." Enforced on the payload, not left to a surface to remember."""

    def test_the_sentence_cannot_quote_one_leg_without_the_other(self):
        s = M.block()["alpha"]["both_sentence"]
        self.assertIn("%.4f" % M.ALPHA_VS_OWN_TIER_PP, s)
        self.assertIn("%.4f" % M.ALPHA_VS_ALL_CAP_EW_PP, s)

    def test_the_favourable_leg_is_not_the_only_one_in_the_card(self):
        keys = {l.get("key") for l in M.card()["lines"]}
        self.assertIn("vs_own_tier", keys)
        self.assertIn("vs_all_cap_ew", keys)
        self.assertIn("vs_spy", keys)

    def test_the_all_cap_leg_is_negative_so_the_pairing_is_not_decorative(self):
        """If it were positive the rule would cost nothing; it is essentially zero and slightly
        negative, which is exactly why quoting the +4.12 alone would mislead."""
        self.assertLess(M.ALPHA_VS_ALL_CAP_EW_PP, 0.0)
        self.assertGreater(M.ALPHA_VS_OWN_TIER_PP, 4.0)


class ThePowerStatementIsHonest(unittest.TestCase):
    def test_it_states_what_the_test_CANNOT_show(self):
        s = M.power_sentence()
        self.assertIn("cannot", s)
        self.assertIn("beats SPY", s)
        self.assertIn("4,383", s)

    def test_it_states_what_the_test_CAN_show(self):
        s = M.power_sentence()
        self.assertIn("recorded honestly", s)
        self.assertIn("costs and turnover", s)

    def test_it_uses_the_SERVED_books_own_tracking_error(self):
        """`MB8`: an `se` may not be borrowed across constructions. Pairing the served edge
        with the all-cap decile's TE would be a numerator from one book over a denominator
        from another."""
        s = M.power_sentence()
        self.assertIn("%.2f" % M.SERVED_TE_VS_SPY, s)
        self.assertNotIn("%.2f" % M.RESEARCH_TE_VS_SPY, s)
        self.assertNotIn("11.40", s)

    def test_the_served_book_needs_far_more_months_than_the_research_decile(self):
        """The whole reason the figure in use is wrong: it is the other book's."""
        self.assertGreater(M.SERVED_MONTHS_TO_DETECT, 10 * M.RESEARCH_MONTHS_TO_DETECT)


class ThePowerStatementReachesThePageAndTheContractIsUntouched(unittest.TestCase):
    """Item 18: base the public power claim on the served book, and do NOT edit the signed
    contract -- draft the correction for the next amendment instead."""

    def test_the_tab_has_an_element_for_it(self):
        t = _read(os.path.join(REPO, "valuation", "web", "templates", "index.html"))
        self.assertIn('id="indexPowerNote"', t)

    def test_the_renderer_fills_it_from_the_SERVER_sentence(self):
        """Read on the code with comments stripped: a positive assertion satisfied by a
        comment goes green while the page stays blank."""
        import re
        src = _read(os.path.join(REPO, "valuation", "web", "static", "app.js"))
        src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
        src = "\n".join(re.sub(r"//.*$", "", ln) for ln in src.splitlines())
        self.assertIn("indexPowerNote", src)
        self.assertIn("power", src)
        self.assertIn("pw.sentence", src,
                      "the note is not filled from the server's sentence")

    def test_a_null_gross_prints_only_the_net_figure(self):
        """FOUND BY MUTATION, which is why it is here: disabling the null-gross branch was
        NOT caught by anything. `INDEX-BOOK` measured the alpha legs NET and there is no gross
        figure for them, so printing "— gross · +4.12% net" puts an em dash where a reader
        reads a missing measurement rather than an absent concept."""
        import re
        src = _read(os.path.join(REPO, "valuation", "web", "static", "app.js"))
        src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
        src = "\n".join(re.sub(r"//.*$", "", ln) for ln in src.splitlines())
        self.assertIn("l.gross == null", src,
                      "the renderer no longer special-cases a net-only card")
        # And the served card really does supply null grosses, or the branch is unreachable.
        grosses = [l.get("gross") for l in M.card()["lines"] if l.get("kind") == "excess"]
        self.assertTrue(grosses, "the served card has no excess lines")
        self.assertTrue(all(g is None for g in grosses),
                        "the served card invented a gross figure: %r" % (grosses,))

    def test_the_renderer_words_none_of_it(self):
        """One copy authority. If the page composed its own sentence, the page and the
        measurement could disagree about what five years can show."""
        import re
        src = _read(os.path.join(REPO, "valuation", "web", "static", "app.js"))
        src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
        src = "\n".join(re.sub(r"//.*$", "", ln) for ln in src.splitlines())
        self.assertNotIn("4,383", src, "the renderer types a measured figure")
        self.assertNotIn("365 years", src)

    def test_the_SIGNED_contract_does_NOT_carry_the_correction(self):
        """σ may never be revised downward and the thresholds are Don's, so the correction is a
        DRAFT and the signed text must not contain it.

        ASSERTED ON THE FILE'S CONTENT, NOT ON A DIFF. My first cut ran
        `git diff origin/main -- PAPER_TRACK_CONTRACT.md`, and
        `test_ma60_conventions::NoSuiteAssertsOnAWorkingTreeDiff` refused it -- for the THIRD
        time in this lane's lineage, and rightly: that compares main against whatever is
        checked out, measures nothing about the lane that wrote it, and becomes a tripwire on a
        whole file that fires on the next unrelated lane. The content property is the real one
        and is strictly better: the served figures must appear in the DRAFT and nowhere in the
        contract."""
        contract = _norm(_read(os.path.join(REPO, "PAPER_TRACK_CONTRACT.md")))
        draft = _norm(_read(os.path.join(REPO, "PREREG_DRAFT_contract_amendment_2.md")))
        for text in ("%.4f" % M.ALPHA_VS_SPY_PP, "%.4f" % M.SERVED_TE_VS_SPY,
                     "{:,}".format(M.SERVED_MONTHS_TO_DETECT)):
            self.assertIn(text, draft, "the draft is missing %s" % text)
            self.assertNotIn(text, contract,
                             "the signed contract carries %s, so the correction was applied "
                             "to it rather than drafted" % text)

    def test_the_contract_still_states_the_rule_that_forbids_lowering_sigma(self):
        """The thing an edit would most plausibly have removed."""
        t = _read(os.path.join(REPO, "PAPER_TRACK_CONTRACT.md"))
        self.assertIn("may never be revised downward", t)

    def test_the_amendment_is_drafted_and_says_it_is_not_in_force(self):
        p = os.path.join(REPO, "PREREG_DRAFT_contract_amendment_2.md")
        self.assertTrue(os.path.exists(p), "the amendment draft is missing")
        t = _norm(_read(p))
        self.assertIn("NOTHING HERE IS IN FORCE", t)
        self.assertIn("9.9864", t)
        self.assertIn("1.9488", t)
        self.assertIn("8.4381", t)
        self.assertIn("4,383", t)

    def test_the_draft_does_not_propose_lowering_sigma(self):
        """The one thing the contract forbids outright."""
        t = _read(os.path.join(REPO, "PREREG_DRAFT_contract_amendment_2.md"))
        self.assertIn("may never be revised downward", t)
        self.assertIn("is NOT revised", t)

    def test_the_draft_states_the_amendment_makes_the_stated_power_WORSE(self):
        """A correction that only ever flattered would be the suspicious kind."""
        t = _read(os.path.join(REPO, "PREREG_DRAFT_contract_amendment_2.md"))
        self.assertIn("WORSE, not better", t)


class TheResearchDecileIsASeparateObject(unittest.TestCase):
    def test_the_two_blocks_share_no_return_key(self):
        """So a surface cannot render one under the other's label."""
        self.assertNotIn("net_pct", M.block())
        self.assertNotIn("roth", M.research_block())

    def test_the_research_block_says_it_is_not_the_index(self):
        self.assertIn("NOT the Valquo Index", M.research_block()["not_the_index"])
        self.assertIn("RESEARCH DECILE", M.research_block()["label"])

    def test_the_served_block_says_it_IS(self):
        self.assertIs(M.block()["is_the_served_book"], True)
        self.assertIs(M.research_block()["is_the_served_book"], False)


class TheDisclosureNamesAllThreeDifferences(unittest.TestCase):
    """`headline_scope` used to name the no-trade BAND and be silent on the UNIVERSE and the
    WEIGHTING, so the payload a user receives quoted all-cap equal-weighted figures for a
    large-cap score-weighted book. `INDEX-BOOK` reported it against this lane by name, and the
    band is the SMALLEST of the three: tier -5.9871pp, weighting +0.6804pp, band -0.8009pp.

    THE NEW FACTS ARE ADDITIVE. My first cut made `differs` mean "differs at all", and
    `test_no_trade_band` caught it: that field is the BAND question and two of its tests read
    it that way, so redefining it in place was the `provider` trap. `differs` is unchanged.
    """

    def _scope(self, *, banded=True, weighting="score", tier=1e10):
        import valuation.edge.valquo_index as V
        return V._headline_scope(0.30 if banded else None, weighting, tier)

    def test_differs_still_means_the_BAND_question(self):
        self.assertIs(self._scope(banded=True)["differs"], True)
        self.assertIs(self._scope(banded=False)["differs"], False)

    def test_the_universe_difference_is_reported_on_its_own_field(self):
        s = self._scope()
        self.assertIs(s["universe_differs"], True)
        self.assertIn("universe", " ".join(s["differs_on"]).lower())

    def test_the_weighting_difference_is_reported_on_its_own_field(self):
        s = self._scope()
        self.assertIs(s["weighting_differs"], True)
        self.assertIn("weighting", " ".join(s["differs_on"]).lower())

    def test_the_weighting_is_READ_and_not_assumed(self):
        """The first cut hard-coded "score-weighted", which is wrong for any caller passing
        `weighting="equal"` -- including `test_no_trade_band`'s own fixtures. A disclosure that
        misdescribes the book it discloses about is worse than none."""
        self.assertIs(self._scope(weighting="equal")["weighting_differs"], False)
        self.assertIs(self._scope(weighting="score")["weighting_differs"], True)

    def test_an_untiered_book_reports_no_universe_difference(self):
        self.assertIs(self._scope(tier=0.0)["universe_differs"], False)

    def test_it_still_names_the_band(self):
        """The old disclosure was incomplete, not wrong. Dropping it would be a regression,
        and `test_no_trade_band` pins the exact wording."""
        s = self._scope()
        self.assertIn("no-trade band", " ".join(s["differs_on"]))
        self.assertIn("WITHOUT a", s["note"])

    def test_the_note_says_the_band_is_NOT_the_largest_difference(self):
        self.assertIn("NOT THE LARGEST DIFFERENCE", self._scope()["note"])

    def test_the_decomposition_shows_the_band_is_the_smallest(self):
        d = self._scope()["one_knob_decomposition_pp_per_yr"]
        self.assertLess(abs(d["no_trade_band_0_to_030"]), abs(d["tier_all_cap_to_10bn"]))
        self.assertAlmostEqual(d["tier_all_cap_to_10bn"], -5.9871, places=4)

    def test_it_carries_the_served_measurement_rather_than_retyping_it(self):
        sv = self._scope()["served_book_measured"]
        self.assertIsNotNone(sv, "the disclosure lost the measured figures")
        self.assertEqual(sv["roth_pct"], M.SERVED_ROTH_PCT)
        self.assertEqual(sv["alpha_vs_all_cap_ew_pp"], M.ALPHA_VS_ALL_CAP_EW_PP)

    def test_the_served_figures_reach_the_note(self):
        self.assertIn("%.4f" % M.SERVED_ROTH_PCT, self._scope()["note"])


class E11ThePaperAccountsFairValueCopyIsConfirmed(unittest.TestCase):
    """E11 asked for the copy to be CONFIRMED, so it is checked against the code it describes.

    Three claims, all of them true, each pinned against `edge/positions.py` rather than read:

      * an ABSENT fair value cannot fire the exit  -> `fair_map.get(t) and ...` is falsy
      * the score floor is a SEPARATE route out    -> its own `elif` branch
      * there is no time limit on a hold           -> `paper_max_hold_days` is 0 and the branch
                                                      reads `if max_hold_days and ...`

    AND ONE IMPLICATION THAT WAS NOT TRUE, now corrected in the copy:
    `withhold_implausible_fair_values` fires only on `ratio > FV_BAND_HIGH` (5.0). A fair value
    that is implausibly LOW is warned about at `FV_BAND_LOW` (0.2) and NOT withheld, so it stays
    truthy and `price >= fair_value` holds at any real price. The old wording implied the guard
    was symmetric.
    """

    def test_an_absent_fair_value_cannot_fire_the_exit(self):
        import ast
        src = _read(os.path.join(REPO, "valuation", "edge", "positions.py"))
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "update_positions")
        # ASSERTED IN PARTS, because `ast.unparse` NORMALISES: it renders the comparison as
        # `(price >= fair_map[...])` with parentheses the source does not have, so a one-literal
        # match fails against a correct tree. Same normalisation trap as the quote one this
        # project has already been caught by twice.
        body = ast.unparse(fn)
        self.assertIn("fair_map.get(p['ticker'])", body,
                      "the fair-value exit no longer guards on the value being present")
        self.assertIn("price >= fair_map[p['ticker']]", body)
        self.assertIn("'hit fair value'", body)
        # And the guard and the comparison are in ONE conjunction, not two statements where the
        # order could change.
        self.assertRegex(body, r"fair_map\.get\(p\['ticker'\]\)\s+and\s+\(?price >= ")

    def test_there_really_is_no_time_limit(self):
        from valuation.config import CONFIG
        self.assertEqual(getattr(CONFIG, "paper_max_hold_days", None), 0,
                         "the copy says there is no time limit on a hold")
        import ast
        src = _read(os.path.join(REPO, "valuation", "edge", "positions.py"))
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "update_positions")
        self.assertIn("if max_hold_days and hold >= max_hold_days", ast.unparse(fn),
                      "a zero max_hold_days would no longer disable the time stop")

    def test_withholding_is_HIGH_side_only_and_the_copy_no_longer_implies_otherwise(self):
        from valuation.engine.publication import FV_BAND_HIGH, FV_BAND_LOW
        self.assertEqual(FV_BAND_HIGH, 5.0)
        self.assertEqual(FV_BAND_LOW, 0.2)
        import re
        src = _read(os.path.join(REPO, "valuation", "web", "static", "app.js"))
        src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
        src = "\n".join(re.sub(r"//.*$", "", ln) for ln in src.splitlines())
        self.assertIn("implausibly <b>high</b>", src,
                      "the copy does not say the withholding is high-side only")
        self.assertNotIn("WITHHELD when neither can be computed", src,
                         "the old symmetric claim is still on the page")

    def test_the_exit_RULE_itself_is_untouched(self):
        """Changing it would change the paper account's recorded history, and the band is the
        engine lane's -- reported in the handoff, not altered here.

        Asserted as PROPERTIES of the three files rather than as a diff, for the reason in
        `test_the_SIGNED_contract_does_NOT_carry_the_correction`."""
        from valuation.engine.publication import FV_BAND_HIGH, FV_BAND_LOW
        self.assertEqual((FV_BAND_HIGH, FV_BAND_LOW), (5.0, 0.2),
                         "the bands moved; the copy describes them")
        wh = _read(os.path.join(REPO, "valuation", "web", "withhold.py"))
        self.assertIn("ratio <= band", wh,
                      "the withholding is no longer a one-sided high-side test")
        pos = _read(os.path.join(REPO, "valuation", "edge", "positions.py"))
        self.assertIn('reason = "hit fair value"', pos)
        self.assertIn("exit_score - exit_band", pos)


class TheDisclosureIsInertOnTheBook(unittest.TestCase):
    """Item 18 forbids changing how a rebalance book is BUILT. Proved against git rather than
    against my expectation, and with enough names that the comparison means something."""

    BOOK_FIELDS = ("positions", "n_positions", "n_eligible", "n_scored", "weighting",
                   "no_trade_band", "contract_conformance", "sector_weights",
                   "sector_data_available", "method", "weights")

    @staticmethod
    def _rows():
        out = []
        for i in range(400):
            out.append({"ticker": "T%03d" % i, "name": "Name %03d" % i,
                        "sector": ["Tech", "Health", "Fin", "Energy"][i % 4],
                        "market_cap": 2e9 + i * 1.2e9, "price": 10.0 + (i % 37),
                        "hot_score": 20.0 + (i * 0.19) % 75.0,
                        "score": 20.0 + (i * 0.19) % 75.0})
        out[0]["hot_score"] = out[0]["score"] = 99.9
        return out

    @classmethod
    def _build(cls):
        import valuation.edge.valquo_index as V
        importlib.reload(V)
        r = cls._rows()
        first = V.build_index(r, exit_frac=None)
        held = [p["ticker"] for p in first["positions"]][:20]
        return first, V.build_index(r, held=held, exit_frac=0.30)

    def test_the_book_is_identical_against_the_pre_change_source(self):
        base = subprocess.run(["git", "show", "origin/main:valuation/edge/valquo_index.py"],
                              cwd=REPO, capture_output=True)
        if base.returncode != 0 or not base.stdout:
            self.skipTest("origin/main copy of valquo_index.py unavailable")
        with io.open(VI, "rb") as _f:
            cur = _f.read()
        # NORMALISE BEFORE COMPARING, AND THAT IS A DEFECT IN THIS TEST'S FIRST CUT.
        #
        # `git show` emits LF; the working tree on this machine is CRLF. So `base.stdout ==
        # cur` was NEVER equal, the "nothing to prove" skip could not fire, and the moment the
        # change landed on origin/main the two sources became content-identical and the final
        # "the disclosure DID move" assertion failed -- a red suite reporting that a landed,
        # correct change had done nothing.
        #
        # The recorded version of this trap is about DECODING a git baseline as cp1252; this is
        # the same family one step along: comparing a git baseline's BYTES against a working
        # tree whose line endings the checkout chose. Compare content, not bytes.
        def _norm(b):
            return b.decode("utf-8", "replace").replace("\r\n", "\n")
        if _norm(base.stdout) == _norm(cur):
            # LOUD, not silent. Once this change is on main this test can only ever skip, and
            # a quiet skip reads as a pass.
            print("       (ALREADY LANDED: valquo_index.py matches origin/main, so the "
                  "one-time inertness demonstration has nothing to compare. The BOOK-identity "
                  "assertions below are what keep standing.)")
            self.skipTest("the file is content-identical to origin/main; nothing to prove")

        a_first, a_band = self._build()
        with io.open(VI, "wb") as _f:
            _f.write(base.stdout)
        try:
            b_first, b_band = self._build()
        finally:
            with io.open(VI, "wb") as _f:
                _f.write(cur)
            importlib.reload(importlib.import_module("valuation.edge.valquo_index"))
        with io.open(VI, "rb") as _f:
            self.assertEqual(_f.read(), cur, "restore failed")

        # REACH, asserted and not assumed.
        self.assertGreaterEqual(a_first.get("n_eligible") or 0, 100)
        self.assertGreaterEqual(a_first.get("n_positions") or 0, 10)
        self.assertIs((a_band.get("no_trade_band") or {}).get("applied"), True)

        moved = []
        for k in self.BOOK_FIELDS:
            for lbl, x, y in (("no-band", b_first, a_first), ("band", b_band, a_band)):
                if (json.dumps(x.get(k), sort_keys=True, default=str)
                        != json.dumps(y.get(k), sort_keys=True, default=str)):
                    moved.append("%s/%s" % (lbl, k))
        self.assertEqual(moved, [], "the build changed: %r" % (moved,))

        # And the disclosure DID move, or the change did nothing.
        self.assertNotEqual(
            json.dumps(b_first.get("headline_scope"), sort_keys=True, default=str),
            json.dumps(a_first.get("headline_scope"), sort_keys=True, default=str))


if __name__ == "__main__":
    unittest.main(verbosity=2)
