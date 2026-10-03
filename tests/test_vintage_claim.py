# -*- coding: utf-8 -*-
"""E7 — the hero band reported ONE number, and it was the wrong one to report alone.

WHAT WAS WRONG, IN TWO HALVES
-----------------------------
(a) TWO START DATES FOR ONE WINDOW, IN ONE BOX. `index_track.summarize` sets
    `live["since"] = series[0]["date"]` -- the first RECORDED ROW -- while `vs_spy_claim`'s
    window text starts at the INCEPTION date. On the bound record those differ (inception
    2026-07-30, first row 2026-07-31), and `hero.py` took `live["since"] or t["inception"]`, so
    the band's label read "since 2026-07-31" three tiles above its own provenance line reading
    "since inception 2026-07-30". It is LA8's family, which this very module's docstring already
    names: a COVERAGE fact rendered under a WINDOW's name.

(b) THE CONTEXT FIGURE WAS SHOWN AND THE CLAIM FIGURE WAS NOT. Contract §5a rule 5 ends *"Both
    are reported; neither is substituted for the other."* The band's Excess tile is the
    as-operated chain: on the bound record it spans FOUR vintages, one VOID, whose window the
    contract itself discloses at -2.85pp. Rule 5 says that object "is explicitly not the
    contract's test". The test is the OPEN vintage (rule 4) -- and that figure was on no surface
    at all.

THE NUMBER WAS NEVER WRONG, WHICH IS WHY EVERY CHECK PASSED
-----------------------------------------------------------
Chaining contiguous legs of a cumulative series reproduces the cumulative, so the as-operated
total EQUALS the recorded since-inception excess by construction. `test_the_two_objects_reconcile`
asserts that identity rather than assuming it, because a False there would mean two derivations
of one object disagree. The defect was a missing label and a missing companion.

WHAT THESE TESTS PIN, AND WHY EACH ONE EXISTS
---------------------------------------------
The load-bearing one is `test_an_empty_vintage_reports_no_figure_and_NOT_zero`. `as_operated`
gives an empty leg `rv = rs = 1.0`, so its excess is exactly 0.0 -- right as a chaining factor
and ruinous as a displayed number. This is not hypothetical: THE DAY ANY FUTURE VINTAGE OPENS
its leg is empty by definition, so without the guard the band would show a measured-looking
"+0.00pp" for the one window a verdict is read on. The local dev store is already in that state,
which is how it was found.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from valuation.edge import track_meter as TM              # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META = os.path.join(REPO, "data_export", "valquo_index_meta.json")
HIST = os.path.join(REPO, "data_export", "valquo_index_track.csv")


def _bound():
    return TM.vintage_claim(meta_path=META, history_path=HIST)


class TheBoundRecordIsReadable(unittest.TestCase):
    """Both inputs are TRACKED, so this suite runs on a CI runner rather than failing open.

    A guard whose input is untracked is absent on a runner and passes while checking nothing.
    These two files are committed by the backup Action, so the assertions below have reach --
    and this test says so out loud rather than leaving it to be assumed.
    """

    def test_both_inputs_exist(self):
        self.assertTrue(os.path.exists(META), META)
        self.assertTrue(os.path.exists(HIST), HIST)

    def test_the_claim_is_available_on_the_bound_record(self):
        v = _bound()
        self.assertTrue(v.get("available"), v.get("reason"))


class RuleFiveReportsBothObjects(unittest.TestCase):
    """§5a rule 5: "Both are reported; neither is substituted for the other"."""

    def test_both_objects_are_present(self):
        v = _bound()
        self.assertIsNotNone(v.get("current"), "the verdict window is missing")
        self.assertIsNotNone(v.get("as_operated"), "the as-operated context is missing")

    def test_each_object_says_WHICH_it_is(self):
        """A reader of the payload must not have to know which key is the verdict."""
        v = _bound()
        self.assertIs(v["current"]["is_the_verdict_window"], True)
        self.assertIs(v["as_operated"]["is_the_verdict_window"], False)

    def test_the_as_operated_figure_carries_its_own_disclaimer(self):
        """The sentence travels WITH the number, so a surface cannot render one and drop it."""
        v = _bound()
        nav = (v["as_operated"].get("not_a_verdict") or "").lower()
        self.assertIn("models", nav)
        self.assertIn("current vintage", nav)

    def test_the_rule_is_quoted_rather_than_paraphrased(self):
        v = _bound()
        self.assertIn("neither is substituted for the other", v.get("rule") or "")

    def test_the_two_figures_DIFFER_on_the_bound_record(self):
        """Which is the whole point: showing one is not showing the other.

        Pinned as a DIFFERENCE rather than as two literals, because the writer appends a row
        every trading day and a pinned figure would rot within a day. The direction is
        structural: vintage 1 is VOID at a disclosed -2.85pp, so the chain lags the open
        vintage.
        """
        v = _bound()
        cur, ao = v["current"]["excess_pp"], v["as_operated"]["excess_pp"]
        self.assertIsNotNone(cur)
        self.assertIsNotNone(ao)
        self.assertNotAlmostEqual(cur, ao, places=3,
                                  msg="if these ever coincide the test is vacuous, not passing")


class TheTwoDerivationsAgree(unittest.TestCase):
    def test_the_two_objects_reconcile(self):
        """The chain must agree with the recorded since-inception figure.

        A False here is not cosmetic -- it means two derivations of one object disagree, which
        is the state that let a wrong number ship on 2026-08-05.
        """
        v = _bound()
        self.assertIs(v["as_operated"]["agrees_with_recorded"], True)

    def test_reconciliation_is_not_vacuously_none(self):
        """`_reconcile` returns None when the authority has nothing to say. That is a legitimate
        state on a fresh deploy and NOT a pass, so it is distinguished here."""
        v = _bound()
        self.assertIsNotNone(v["as_operated"]["agrees_with_recorded"])


class TheEmptyVintageGuard(unittest.TestCase):
    """The load-bearing test. See the module docstring."""

    # Rows that STOP BEFORE the open vintage began, read at a date after it began. That is
    # exactly the local dev store's state -- which is how the defect was found -- and exactly
    # the state the live record is in for the first hours after every vintage event. Reading
    # at a date BEFORE the vintage opened does not reproduce it: `as_operated` skips a leg
    # whose end precedes its start, so no open leg is emitted at all.
    _EMPTY_ROWS = [{"date": "2026-07-31", "valquo": 0.41, "spy": 0.69},
                   {"date": "2026-08-04", "valquo": 1.50, "spy": 0.75}]

    def test_an_empty_vintage_reports_no_figure_and_NOT_zero(self):
        import datetime as dt
        v = self._claim_from(self._EMPTY_ROWS, as_of=dt.date(2026, 9, 29))
        self.assertTrue(v.get("available"), v.get("reason"))
        cur = v["current"]
        self.assertEqual(cur["n_rows"], 0)
        self.assertIsNone(cur["excess_pp"],
                          "an unrecorded vintage must not render as a flat one")
        self.assertIsNone(cur["valquo_pct"])
        self.assertIsNone(cur["spy_pct"])
        self.assertIn("no recorded rows", (cur.get("reason") or ""))

    def test_the_underlying_leg_really_does_say_zero(self):
        """The positive control: without the guard the figure IS 0.0, not None.

        If `as_operated` ever stopped returning 0.0 for an empty leg, the guard above would be
        passing for no reason and this test fails first and says so.
        """
        import datetime as dt
        ao = TM.as_operated(self._EMPTY_ROWS, as_of=dt.date(2026, 9, 29))
        open_leg = [L for L in ao["legs"] if L["status"] == "OPEN"]
        self.assertEqual(len(open_leg), 1)
        self.assertEqual(open_leg[0]["n_rows"], 0)
        self.assertAlmostEqual(open_leg[0]["excess_pp"], 0.0, places=9)

    def test_a_vintage_WITH_rows_still_reports_its_figure(self):
        """The guard must not swallow the real case -- a refusal that refuses everything is
        not a guard."""
        v = _bound()
        self.assertGreater(v["current"]["n_rows"], 0)
        self.assertIsNotNone(v["current"]["excess_pp"])
        self.assertIsNone(v["current"].get("reason"))

    @staticmethod
    def _claim_from(rows, as_of):
        """Drive `vintage_claim` against a synthetic series via a patched `detail`."""
        import datetime as dt
        real_detail = TM.detail

        def fake(meta_path=None, history_path=None, **kw):
            ao = TM.as_operated(rows, as_of=as_of)
            return {"vintage_label": TM.vintage_label(), "as_operated": ao,
                    "as_operated_agrees_with_authority": True}
        TM.detail = fake
        try:
            return TM.vintage_claim()
        finally:
            TM.detail = real_detail


class TheOpenLegIsFoundByStatus(unittest.TestCase):
    def test_the_leg_is_selected_by_STATUS_not_by_position(self):
        """"The last entry" would silently become the answer the day a vintage is appended
        ahead of time. The register is the authority on which vintage is live."""
        import datetime as dt
        real = TM.as_operated

        def fake(series, as_of=None):
            out = real(series, as_of=as_of)
            # A future, not-yet-open vintage appended after the live one.
            out["legs"] = list(out["legs"]) + [
                {"vintage": 99, "run": 99, "status": "PLANNED", "opened": "2027-01-01",
                 "closed": None, "n_rows": 7, "valquo_ret_pp": 50.0, "spy_ret_pp": 0.0,
                 "excess_pp": 50.0}]
            return out
        TM.as_operated = fake
        try:
            v = _bound()
        finally:
            TM.as_operated = real
        self.assertEqual(v["current"]["vintage"], TM.current_vintage()["vintage"])
        self.assertNotEqual(v["current"]["vintage"], 99)
        self.assertNotAlmostEqual(v["current"]["excess_pp"], 50.0, places=3)


class TheShadowIsFenced(unittest.TestCase):
    """PT-OUTBOUND: the shadow's NUMBERS stay off every outbound surface.

    `as_operated` carries a per-vintage leg list and one of those legs IS the shadow.
    `/api/track`'s own comment records that it adds the vintage LABEL and "carries no
    measurement" for that reason. The OPEN vintage's own excess is not the shadow's, so
    publishing it breaches nothing -- publishing the breakdown would.
    """

    def test_no_per_vintage_leg_list_is_returned(self):
        v = _bound()
        self.assertNotIn("legs", v)
        self.assertNotIn("legs", v["as_operated"])

    def test_the_shadow_vintages_figure_is_absent_from_the_payload(self):
        import json
        v = _bound()
        blob = json.dumps(v, default=str)
        shadow = TM.vintage_label().get("shadow_vintage")
        self.assertIsNotNone(shadow, "the register holds no shadow; this test is vacuous")
        legs = TM.as_operated(
            [{"date": r[0], "valquo": r[1], "spy": r[2]} for r in _rows()])["legs"]
        shadow_leg = [L for L in legs if L["vintage"] == shadow]
        self.assertEqual(len(shadow_leg), 1)
        # Its excess must not appear anywhere in what a surface receives.
        self.assertNotIn("%.4f" % shadow_leg[0]["excess_pp"], blob)


class ItNeverRaises(unittest.TestCase):
    def test_an_unreadable_register_degrades_rather_than_raising(self):
        """`current_vintage()` RAISES when the register is not well formed -- correct for the
        register, wrong for a band that has a figure to show."""
        real = TM.detail

        def boom(**kw):
            raise RuntimeError("register unreadable")
        TM.detail = boom
        try:
            v = TM.vintage_claim()
        finally:
            TM.detail = real
        self.assertFalse(v["available"])
        self.assertIn("register", v["reason"])

    def test_a_register_with_no_open_vintage_degrades_with_a_reason(self):
        real = TM.detail

        def fake(**kw):
            return {"vintage_label": {"vintage": 4, "since": "2026-08-13"},
                    "as_operated": {"legs": [{"vintage": 1, "status": "VOID",
                                              "opened": "2026-07-30", "n_rows": 1,
                                              "excess_pp": -2.8468}],
                                    "label": "x", "n_vintages": 1,
                                    "cumulative_excess_pp": 0.0},
                    "as_operated_agrees_with_authority": None}
        TM.detail = fake
        try:
            v = TM.vintage_claim()
        finally:
            TM.detail = real
        self.assertFalse(v["available"])
        self.assertIn("no open vintage", v["reason"])


class TheHeroPrefersInceptionOverTheFirstRow(unittest.TestCase):
    """Half (a). The precedence was `live["since"] or t["inception"]`, i.e. backwards.

    Two neighbouring surfaces had it RIGHT already and only the hero had it wrong:
    `app.js` renders `d.inception || live.since` and `landing.html` renders
    `track.inception`. So this is not a judgement call about which date to prefer -- it is the
    hero disagreeing with the rest of the product about one window.
    """

    @staticmethod
    def _block():
        from valuation.web import hero
        import valuation.screener.index_track as _it
        old = _it.summarize

        def fake(*a, **kw):
            return {"available": True, "inception": "2026-07-30",
                    "live": {"since": "2026-07-31", "as_of": "2026-09-29", "days": 24},
                    "series": [], "benchmark": "SPY"}
        _it.summarize = fake
        try:
            return hero._index_block(None)
        finally:
            _it.summarize = old

    def test_inception_wins_when_the_two_differ(self):
        self.assertEqual(self._block()["since"], "2026-07-30",
                         "the window these percentages are cumulative over starts at inception")

    def test_the_first_row_is_kept_rather_than_dropped(self):
        """The gap between inception and the first recorded row IS the recording story --
        dropping it would lose the only signal that recording started a day late."""
        self.assertEqual(self._block()["first_row"], "2026-07-31")


class TheBandNamesTheVintageNotASecondDate(unittest.TestCase):
    """Half (a), the label. It read "paper, since <first recorded row>" in larger type than
    the provenance line that said "since inception <inception>". The window line already
    states both dates, so repeating a date in the label could only ever contradict it. What
    was genuinely missing is the vintage, which §5a rule 4 requires a verdict surface to name.
    """

    def _hero(self, vintage_num=4):
        from valuation.web import hero
        import valuation.screener.index_track as _it
        import valuation.edge.track_meter as _tmm
        old_s, old_v = _it.summarize, _tmm.vintage_claim

        def fake_summarize(*a, **kw):
            return {"available": True, "inception": "2026-07-30", "thin": True,
                    "live": {"since": "2026-07-31", "as_of": "2026-09-29", "days": 24,
                             "cum_valquo_pct": 4.36, "cum_spy_pct": 3.29, "excess_pp": 1.07},
                    "series": [], "benchmark": "SPY"}

        def fake_vintage(*a, **kw):
            if vintage_num is None:
                return {"available": False, "reason": "no register"}
            return {"available": True, "vintage": {"vintage": vintage_num,
                                                   "since": "2026-08-13", "label": "x"},
                    "current": {"vintage": vintage_num, "excess_pp": 1.62, "n_rows": 21},
                    "as_operated": {"excess_pp": 1.07, "not_a_verdict": "n"},
                    "rule": "r"}
        _it.summarize, _tmm.vintage_claim = fake_summarize, fake_vintage
        try:
            return hero.live_hero(None)
        finally:
            _it.summarize, _tmm.vintage_claim = old_s, old_v

    def test_the_label_names_the_vintage(self):
        self.assertIn("book vintage 4", self._hero(4)["label"])

    def test_the_label_states_no_date_at_all_when_a_vintage_is_known(self):
        """Because the provenance line owns the dates. Two dates in one box was the defect."""
        label = self._hero(4)["label"]
        self.assertNotIn("2026-07-31", label)
        self.assertNotIn("2026-07-30", label)
        self.assertNotIn("since 2", label)

    def test_it_falls_back_to_a_date_when_the_register_is_unreadable(self):
        """A band must still say what it is when the vintage cannot be read -- and the date it
        falls back to is the INCEPTION one, not the first row."""
        h = self._hero(None)
        self.assertIn("since 2026-07-30", h["label"])
        self.assertNotIn("2026-07-31", h["label"])


class TheRenderedBandShowsBoth(unittest.TestCase):
    """Asserted on the RENDERED output, not on the template source.

    `hero.py`'s own docstring records why: the removed sandbox fallback DID set
    `source: "paper-sandbox"`, honestly, and the template never rendered it -- *"a label that
    a surface can decline to show is not a safeguard"*. A test that greps the template proves
    the string is present in a file, not that a reader sees it.
    """

    @classmethod
    def _tiles(cls, vintage):
        """The band's FIGURE TILES as (label, value) pairs, caption text excluded.

        MUTATION FOUND THIS AND IT WAS MY OWN TEST THAT WAS WEAK. The first cut asserted
        `"vintage 4" in rendered_text` and `"as operated" in rendered_text` -- and BOTH
        strings also occur in the provenance CAPTION underneath, so deleting the tile outright
        left the assertions passing. A test that cannot tell a figure from a sentence about
        the figure is not testing the figure. So the tiles are parsed out and asserted on
        directly: `.lb-stat` minus `.lb-prov`, which is exactly the visual distinction the
        band makes between a number and its prose.
        """
        import re
        html = cls._html(vintage)
        out = []
        for m in re.finditer(r'<div class="lb-stat([^"]*)">(.*?)</div>\s*(?=<div|</div>|$)',
                             html, re.S):
            if "lb-prov" in m.group(1):
                continue
            inner = m.group(2)
            k = re.search(r'<span class="k">(.*?)</span>', inner, re.S)
            v = re.search(r'<span class="v[^"]*">(.*?)</span>', inner, re.S)
            clean = lambda t: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t or "")).strip()
            out.append((clean(k.group(1) if k else ""), clean(v.group(1) if v else "")))
        return out

    @staticmethod
    def _html(vintage):
        from jinja2 import Environment, FileSystemLoader
        tdir = os.path.join(REPO, "valuation", "web", "templates")
        src = open(os.path.join(tdir, "index.html"), encoding="utf-8").read()
        i = src.index("{% if hero.show %}")
        j = src.index("{% endif %}", src.index("lb-spark"))
        frag = (src[i:j] + "{% endif %}{% endif %}").replace("{% if hero.spark %}",
                                                             "{% if False %}")
        env = Environment(loader=FileSystemLoader(tdir))
        return env.from_string(frag).render(hero={
            "show": True, "thin": True, "label": "paper, book vintage 4, thin",
            "caveat": "c", "spark": None,
            "index": {"available": True, "benchmark": "SPY", "cum_pct": 4.36,
                      "bench_pct": 3.29, "excess_pp": 1.07, "book": "Valquo Index",
                      "window": "since inception 2026-07-30 through 2026-09-29",
                      "age": {"age": 44, "recorded": 24, "complete": False}, "days": 24,
                      "vintage": vintage},
            "options": {"available": False}, "reported": {"available": False}})

    @classmethod
    def _render(cls, vintage):
        """The band's full text, for the CAPTION assertions."""
        import re
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", cls._html(vintage))).strip()

    _WITH = {"available": True,
             "vintage": {"vintage": 4, "since": "2026-08-13", "label": "no-trade band"},
             "current": {"vintage": 4, "excess_pp": 1.6199, "n_rows": 21, "reason": None},
             "as_operated": {"excess_pp": 1.0683, "n_vintages": 4,
                             "not_a_verdict": "chains across vintages and therefore across "
                                              "MODELS"},
             "rule": "Both are reported; neither is substituted for the other"}

    def test_both_excess_figures_are_rendered_as_LABELLED_TILES(self):
        tiles = self._tiles(self._WITH)
        excess = [(k, v) for k, v in tiles if k.startswith("Excess")]
        self.assertEqual(len(excess), 2,
                         "the band must carry TWO excess tiles, got %r" % (excess,))
        by_label = dict(excess)
        self.assertIn("Excess as operated", by_label, "the chain tile is unlabelled: %r" % tiles)
        self.assertEqual(by_label["Excess as operated"], "+1.07pp")
        self.assertIn("Excess vintage 4", by_label, "the verdict tile is missing: %r" % tiles)
        self.assertEqual(by_label["Excess vintage 4"], "+1.62pp")

    def test_the_window_tags_are_NOT_pt_spmos_reported_tags(self):
        """THE DEFECT THIS PINS WAS MINE, AND ANOTHER ITEM'S LANDED GUARD CAUGHT IT.

        The first cut marked both Excess tiles with `rep-tag`, and two of
        `test_reported_benchmark.py`'s tests went red: one counts exactly two of them, the
        other requires none when no comparison is recorded. They were right for a reason
        beyond the count. `rep-tag` is PT-SPMO's vocabulary for a benchmark that is REPORTED
        and NOT the bound claim; these two tiles are both bound-SPY figures over different
        WINDOWS, and the vintage one IS the contract's claim -- so tagging it "reported" says
        the opposite of the truth.

        The tags look identical on purpose (same geometry in `style.css`); the names differ so
        the two meanings cannot be conflated again. This test is here rather than there because
        the lesson is this item's.
        """
        html = self._html(self._WITH)
        self.assertEqual(html.count('class="win-tag"'), 2,
                         "both window tags must use the window class")
        self.assertNotIn('class="rep-tag"', html,
                         "a window label must not borrow PT-SPMO's reported vocabulary")

    def test_the_rendered_band_carries_the_not_a_verdict_sentence(self):
        self.assertIn("chains across vintages", self._render(self._WITH))

    def test_the_rendered_band_carries_rule_fives_own_words(self):
        self.assertIn("neither is substituted for the other", self._render(self._WITH))

    def test_an_empty_vintage_renders_NO_second_figure_and_says_why(self):
        empty = dict(self._WITH)
        empty["current"] = {"vintage": 4, "excess_pp": None, "n_rows": 0,
                            "reason": "this vintage has no recorded rows yet"}
        tiles = self._tiles(empty)
        excess = [(k, v) for k, v in tiles if k.startswith("Excess")]
        self.assertEqual(len(excess), 1, "no second tile when the vintage has no rows: %r"
                         % (excess,))
        self.assertEqual(excess[0], ("Excess as operated", "+1.07pp"),
                         "the as-operated figure must still show; withholding both is worse")
        self.assertNotIn("+0.00pp", [v for _, v in tiles],
                         "an unrecorded vintage must not render as a flat one")
        # And the band says WHY, in the module's own words.
        self.assertIn("no recorded rows", self._render(empty))

    def test_an_unreadable_register_renders_the_band_without_the_vintage_text(self):
        txt = self._render({"available": False, "reason": "no register"})
        self.assertIn("+1.07pp", txt, "the band must still show what it has")
        self.assertNotIn("Book vintage", txt)


def _rows():
    import csv
    import io as _io
    out = []
    with _io.open(HIST, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append((r["date"], float(r["valquo_pct"]), float(r["spy_pct"])))
    return out


if __name__ == "__main__":
    unittest.main(verbosity=2)
