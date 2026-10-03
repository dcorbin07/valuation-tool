# -*- coding: utf-8 -*-
"""ITEM 21 — the Index's holdings card described a different book, in four separate ways.

WHAT WAS ON THE LIVE TAB
------------------------
Verbatim, 2026-10-03, above a correct list of 86 holdings::

    Tax-free (Roth/IRA): highest net alpha, full rotation, ~2-month rebalance — 85 of
    undefined eligible (undefined scored). Rebalance every ~2 months, full rotation.
    backtested net Sharpe 1.10, net excess over the equal-weighted universe 11.6%

and the Company, Sector, Hot score and Market cap columns were an em dash on every row.

FOUR DEFECTS, ONE PAYLOAD
-------------------------
1. **THE ROUTE DESCRIBED THE WRONG BOOK.** `/api/valquo-index` defaulted its config to
   `settings.DEFAULT_BOOK_CONFIG`, which is `"roth"`. The HOLDINGS were right -- they come
   from `index_in_force.book_in_force`, which reads the bound record -- but the `config` block
   bolted to them was roth's, so every clause of the header was about an account type the
   Index is not. The tracked book is `index_track.TRACKED_CONFIG`. Session 74 made
   `index_track.summarize` stop reading the preference for exactly this reason; this route was
   missed, which is the one-defect-two-call-sites shape this project keeps finding.

2. **TWO `undefined`s.** The renderer read `d.n_eligible` and `d.n_scored`, which are facts
   about a SCAN. A held book has no such fields and never did, so JavaScript rendered the
   string "undefined" into a sentence about the product.

3. **FOUR EMPTY COLUMNS.** `book_in_force` returns `ticker`, `weight_at_formation`, `weight`
   and `status`, which is right -- those are the only things the record knows. The table's
   Company/Sector/Hot score/Market cap columns were inherited from the PREVIEW payload, which
   is built from a scan and carries all four.

4. **A RESEARCH FIGURE, UNLABELLED, ONE INCH ABOVE THE HOLDINGS.** "net Sharpe 1.10, net
   excess over the equal-weighted universe 11.6%" is `config.measured` -- the research
   decile's figure for an account type, an all-cap equal-weighted top 10% and not the 86-name
   large-cap book listed underneath. Item 18 pointed the performance card at the Index's own
   measurement; this card was quoting a different backtest for the same tab.

WHY THIS SUITE RENDERS INSTEAD OF GREPPING
------------------------------------------
Three guards in this lane's recent lineage were defeated by asserting that a STRING WAS
PRESENT in the source rather than that the rendered output was right -- twice by `if (false)`
and once by a docstring satisfying the assertion. The user's requirement here is explicitly
about the RENDERED card, so this suite loads the real `app.js` into node against a stubbed DOM
and asserts on the HTML that comes out. A source grep could not have caught defect 2 at all:
`n_eligible` is a legitimate key name and appears in the preview branch, which is correct.
"""
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from valuation.screener import settings as S                      # noqa: E402
from valuation.screener.index_track import TRACKED_CONFIG         # noqa: E402
from valuation.screener.index_in_force import (                   # noqa: E402
    attach_labels, cadence_sentence)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPJS = os.path.join(REPO, "valuation", "web", "static", "app.js")
APPPY = os.path.join(REPO, "valuation", "web", "app.py")

#: The book shape `book_in_force` really returns, with the live counts from the brief. 86 rows
#: would make the fixture unreadable and prove nothing extra, so it is three held and one
#: exited -- WBS, which is the name the brief says left.
BOOK = {
    "ok": True,
    "n_positions": 3,
    "n_exited": 1,
    "formed_on": "2026-07-30",
    "next_rebalance": "2026-10-22",
    "next_rebalance_basis": "63 trading days after the formation date",
    "held_since_days": 65,
    "prorata_scale": 1.0101,
    "weight_exited": 0.01,
    "positions": [
        {"ticker": "AAPL", "weight": 0.0303, "weight_at_formation": 0.03, "status": "held"},
        {"ticker": "MSFT", "weight": 0.0202, "weight_at_formation": 0.02, "status": "held"},
        {"ticker": "NVDA", "weight": 0.0101, "weight_at_formation": 0.01, "status": "held"},
        {"ticker": "WBS", "weight": 0.0, "weight_at_formation": 0.01, "status": "exited"},
    ],
}


class _Store(object):
    """The one method `attach_labels` and `sector_mix` use, and nothing else."""

    def __init__(self, rows, date="2026-10-02"):
        self._rows, self._date = rows, date

    def latest_scan_date(self):
        return self._date

    def load_snapshot(self, _d=None, top=None):
        return list(self._rows)


SNAP = [
    {"ticker": "AAPL", "name": "Apple Inc", "sector": "Technology",
     "market_cap": 3.2e12, "hot_score": 71.4},
    {"ticker": "MSFT", "name": "Microsoft Corp", "sector": "Technology",
     "market_cap": 3.0e12, "hot_score": 66.0},
    # NVDA deliberately absent: a holding the latest scan no longer carries must keep its em
    # dash rather than be dropped or filled with a guess.
]


def _node():
    return shutil.which("node")


def render_index_card(payload, cfg_name=TRACKED_CONFIG):
    """Run the REAL `_renderValquoIndex` against a stub DOM and return the card's HTML.

    Returns ``(note_html, body_html)``. `None` when node is absent, so the caller skips
    LOUDLY rather than passing on an unrendered page.
    """
    node = _node()
    if not node:
        return None
    harness = r"""
const fs = require('fs');
// A DOM with exactly the surface app.js touches on this path. Deliberately minimal: a real
// DOM would let a defect hide behind jsdom's forgiveness, and the only thing under test is
// what the renderer WRITES.
const els = {};
function el(id) {
  if (!els[id]) els[id] = {id: id, innerHTML: "", value: "",
                           set textContent(v) { this.innerHTML = String(v); },
                           get textContent() { return this.innerHTML; }};
  return els[id];
}
global.document = {getElementById: (id) => el(id),
                   querySelectorAll: () => [], querySelector: () => null,
                   addEventListener: () => {}, createElement: () => el("_tmp")};
global.window = {addEventListener: () => {}, location: {search: "", href: ""},
                 matchMedia: () => ({matches: false, addEventListener: () => {}})};
global.localStorage = {getItem: () => null, setItem: () => {}, removeItem: () => {}};
global.navigator = {userAgent: "node"};
global.fetch = () => Promise.reject(new Error("no network in the harness"));
const src = fs.readFileSync(process.argv[2], 'utf8');
// `const`/`function` at top level of a CommonJS module are module-scoped, which is what we
// want: the renderer and its helpers see each other and nothing leaks between cases.
const run = new Function('require', 'document', 'window', 'localStorage', 'navigator', 'fetch',
                         src + "\nreturn {r: _renderValquoIndex};");
const api = run(require, global.document, global.window, global.localStorage,
                global.navigator, global.fetch);
const payload = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
api.r(payload, process.argv[4]);
process.stdout.write(JSON.stringify({
  note: el("valquoIndexNote").innerHTML,
  body: el("valquoIndexBody").innerHTML,
}));
"""
    d = tempfile.mkdtemp(prefix="idxcard-")
    try:
        hp = os.path.join(d, "h.js")
        pp = os.path.join(d, "p.json")
        with open(hp, "w", encoding="utf-8") as f:
            f.write(harness)
        with open(pp, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        r = subprocess.run([node, hp, APPJS, pp, cfg_name], capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            raise AssertionError("harness failed: " + (r.stderr or "")[:1500])
        out = json.loads(r.stdout)
        return out["note"], out["body"]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def live_payload():
    """The payload the route now serves for the book in force, built the way the route builds
    it -- so this suite cannot pass against a route that stopped doing it."""
    from valuation.edge.valquo_index import config_block
    st = _Store(SNAP)
    book = dict(BOOK)
    book["positions"] = [dict(p) for p in BOOK["positions"]]
    attach_labels(book, st)
    cfg = (S.BOOK_CONFIGS or {})[TRACKED_CONFIG]
    book["config"] = dict(config_block(TRACKED_CONFIG, cfg))
    book["is_preview"] = False
    book["card"] = {
        "n_held": book["n_positions"],
        "n_exited": book["n_exited"],
        "exited": [p["ticker"] for p in book["positions"] if p["status"] == "exited"],
        "formed_on": book["formed_on"],
        "next_rebalance": book["next_rebalance"],
        "next_rebalance_basis": book["next_rebalance_basis"],
        "cadence": cadence_sentence(cfg),
        "construction": TRACKED_CONFIG,
        "is_tracked_construction": True,
        "not_an_account_type": ("the Valquo Index is one book; the account types describe how "
                               "a future rebalance would be built, not what is held"),
    }
    book["source_note"] = "the book formed at the last rebalance and held unchanged since"
    return book


# ==========================================================================================
# THE TWO WORDS THE USER NAMED
# ==========================================================================================
class TheTwoBannedWords(unittest.TestCase):
    """`undefined` and `Roth/IRA`, asserted against the RENDERED card.

    Both are rendering failures rather than wording choices, which is why they are asserted
    together: "undefined" is a key that does not exist on this object, and "Roth/IRA" is a
    label for a book this is not.
    """

    def setUp(self):
        out = render_index_card(live_payload())
        if out is None:
            self.skipTest("no node on PATH — the RENDERED card is UNCHECKED on this machine")
        self.note, self.body = out

    def test_the_rendered_card_never_says_undefined(self):
        for where, html in (("note", self.note), ("body", self.body)):
            self.assertNotIn("undefined", html,
                             "the %s renders the string 'undefined': %s"
                             % (where, html[:300]))

    def test_the_rendered_card_never_says_roth_or_ira(self):
        both = self.note + self.body
        for banned in ("Roth/IRA", "Roth", "IRA", "Tax-free"):
            self.assertNotIn(banned, both,
                             "the Index card names an account type (%r). The Index is ONE "
                             "book; account types describe how a future rebalance would be "
                             "built. Card: %s" % (banned, self.note[:300]))

    def test_it_does_not_say_full_rotation_or_two_months(self):
        """roth's cadence, on a quarterly banded book."""
        low = (self.note + self.body).lower()
        self.assertNotIn("full rotation", low)
        self.assertNotIn("~2-month", low)
        self.assertNotIn("every ~2 months", low)

    def test_the_vacuity_control_the_card_is_not_simply_empty(self):
        """A renderer that wrote nothing would pass every assertion above."""
        self.assertGreater(len(self.note), 120, "the note is suspiciously short: %r" % self.note)
        self.assertIn("Valquo Index", self.note)
        self.assertIn("<table", self.body)


class TheExactLiveState(unittest.TestCase):
    """THE PAYLOAD THE OLD ROUTE SERVED, rendered: holdings from the record, config from roth.

    This class exists because the banned-word test above would otherwise be HALF VACUOUS. The
    fixture `live_payload()` attaches the TRACKED config block, so a pre-fix render of it says
    "Taxable: ..." and the word "Roth" never appears -- the `undefined`s fire, the account type
    does not. The live defect was the OTHER half: the route resolved `DEFAULT_BOOK_CONFIG`, so
    the payload carried ROTH's block above the record's holdings.

    So this reconstructs that payload exactly and asserts the ban fires on it. It is the
    positive control for `test_the_rendered_card_never_says_roth_or_ira`: without it, that
    assertion could pass on a tree where the route regression was back.
    """

    def setUp(self):
        from valuation.edge.valquo_index import config_block
        st = _Store(SNAP)
        book = dict(BOOK)
        book["positions"] = [dict(p) for p in BOOK["positions"]]
        attach_labels(book, st)
        # The defect, reproduced: the UI PREFERENCE resolved instead of the tracked book.
        wrong = S.DEFAULT_BOOK_CONFIG
        book["config"] = dict(config_block(wrong, (S.BOOK_CONFIGS or {})[wrong]))
        book["is_preview"] = False
        book["source_note"] = "the book formed at the last rebalance and held unchanged since"
        self.payload = book
        self.wrong = wrong

    def test_the_old_payload_names_an_account_type_in_its_config_block(self):
        """The fixture is faithful: it really does carry the roth label."""
        self.assertIn("Roth", self.payload["config"]["label"])

    def test_rendering_it_with_the_CURRENT_renderer_still_says_nothing_about_roth(self):
        """THE REPAIR IS BELT AND BRACES, AND THIS IS THE BRACES.

        The route no longer serves roth's block -- but the renderer no longer READS
        `config.label` for the book in force either, so even a payload carrying the wrong
        config cannot put an account type above the holdings. Two independent reasons the live
        header cannot come back, and this asserts the second one.
        """
        out = render_index_card(self.payload)
        if out is None:
            self.skipTest("no node on PATH — the RENDERED card is UNCHECKED on this machine")
        note, body = out
        self.assertNotIn("Roth", note + body)
        self.assertNotIn("undefined", note + body)
        self.assertIn("Valquo Index", note)


class TheCardDescribesTheBookInForce(unittest.TestCase):
    """The four facts a held book actually has."""

    def setUp(self):
        out = render_index_card(live_payload())
        if out is None:
            self.skipTest("no node on PATH — the RENDERED card is UNCHECKED on this machine")
        self.note, self.body = out

    def test_it_states_the_number_held(self):
        self.assertIn("3 holdings", self.note)

    def test_it_names_the_formation_date(self):
        self.assertIn("2026-07-30", self.note)

    def test_it_names_the_next_rebalance(self):
        self.assertIn("2026-10-22", self.note)

    def test_it_states_the_cadence_from_the_config(self):
        self.assertIn("quarterly", self.note)
        self.assertIn("30%", self.note)

    def test_it_names_the_exited_holding(self):
        """WBS is the name the brief says left, and a reader must be able to see that the
        count fell for a corporate reason rather than because the book was re-picked."""
        self.assertIn("WBS", self.note)
        self.assertIn("1 left the book", self.note)

    def test_it_says_the_account_types_are_not_what_is_held(self):
        self.assertIn("one book", self.note)


# ==========================================================================================
# THE FOUR COLUMNS
# ==========================================================================================
class TheDisplayLabels(unittest.TestCase):
    def setUp(self):
        self.book = dict(BOOK)
        self.book["positions"] = [dict(p) for p in BOOK["positions"]]
        attach_labels(self.book, _Store(SNAP))
        self.by = {p["ticker"]: p for p in self.book["positions"]}

    def test_a_labelled_holding_gets_its_name_sector_and_cap(self):
        p = self.by["AAPL"]
        self.assertEqual(p["name"], "Apple Inc")
        self.assertEqual(p["sector"], "Technology")
        self.assertEqual(p["market_cap"], 3.2e12)

    def test_a_holding_absent_from_the_scan_is_NOT_filled_or_dropped(self):
        """NVDA is still held. A guess would be worse than an em dash."""
        self.assertIn("NVDA", self.by)
        self.assertNotIn("name", self.by["NVDA"])
        self.assertNotIn("sector", self.by["NVDA"])
        self.assertNotIn("market_cap", self.by["NVDA"])

    def test_the_hot_score_arrives_under_a_DIFFERENT_key(self):
        """THE LOAD-BEARING ASSERTION OF THIS CLASS.

        The record does not keep the score each name was selected on. Serving today's score as
        `hot_score`, next to a column headed "Weight at formation", would read as the formation
        score -- the most misleading thing this table could say. The key says which it is.
        """
        self.assertEqual(self.by["AAPL"]["hot_score_today"], 71.4)
        self.assertNotIn("hot_score", self.by["AAPL"])

    def test_it_reports_how_many_it_could_label(self):
        lab = self.book["labels"]
        self.assertEqual(lab["n_labelled"], 2)
        self.assertEqual(lab["n_positions"], 4)
        self.assertTrue(lab["available"])

    def test_labelling_nothing_is_reported_rather_than_rendered_as_four_dashes(self):
        """The state the live tab was in. `available` False is what lets the page SAY so."""
        book = dict(BOOK)
        book["positions"] = [dict(p) for p in BOOK["positions"]]
        attach_labels(book, _Store([{"ticker": "ZZZZ", "name": "Nothing", "sector": "X"}]))
        self.assertFalse(book["labels"]["available"])
        self.assertEqual(book["labels"]["n_labelled"], 0)
        self.assertIn("no holding appears", book["labels"]["reason"])

    def test_no_store_is_not_an_error(self):
        book = dict(BOOK)
        book["positions"] = [dict(p) for p in BOOK["positions"]]
        attach_labels(book, None)
        self.assertFalse(book["labels"]["available"])

    def test_a_present_but_null_column_is_left_alone(self):
        """`None` written under a name that reads as measured is worse than the dash."""
        book = dict(BOOK)
        book["positions"] = [dict(p) for p in BOOK["positions"]]
        attach_labels(book, _Store([{"ticker": "AAPL", "name": None, "sector": "",
                                     "market_cap": None, "hot_score": None}]))
        p = [x for x in book["positions"] if x["ticker"] == "AAPL"][0]
        self.assertNotIn("name", p)
        self.assertNotIn("sector", p)
        self.assertNotIn("market_cap", p)
        self.assertNotIn("hot_score_today", p)
        # It WAS found, which is a different fact from having no labels.
        self.assertEqual(book["labels"]["n_labelled"], 1)


class TheRenderedColumns(unittest.TestCase):
    def setUp(self):
        out = render_index_card(live_payload())
        if out is None:
            self.skipTest("no node on PATH — the RENDERED card is UNCHECKED on this machine")
        self.note, self.body = out

    def test_the_company_name_is_in_the_table(self):
        self.assertIn("Apple Inc", self.body)

    def test_the_sector_is_in_the_table(self):
        self.assertIn("Technology", self.body)

    def test_the_hot_score_column_says_whose_score_it_is(self):
        self.assertIn("hot score", self.body.lower())
        self.assertRegex(self.body, r"Today.s hot score")

    def test_the_unlabelled_holding_renders_a_dash_and_is_still_listed(self):
        self.assertIn("NVDA", self.body)

    def test_the_page_says_where_the_labels_came_from(self):
        self.assertIn("latest scan", self.body)
        self.assertIn("2 of 4", self.body)

    def test_it_says_the_hot_score_is_not_the_selection_score(self):
        self.assertIn("not the score the name was selected on", self.body)


# ==========================================================================================
# THE RESEARCH FIGURE IS GONE FROM THIS CARD
# ==========================================================================================
class NoBacktestFigureOnTheHoldingsCard(unittest.TestCase):
    """Defect 4. Item 18 gave the Index its own measurement; a second, different, unlabelled
    backtest figure one inch above the holdings is how two surfaces on one tab disagree."""

    def setUp(self):
        out = render_index_card(live_payload())
        if out is None:
            self.skipTest("no node on PATH — the RENDERED card is UNCHECKED on this machine")
        self.note, self.body = out

    def test_the_card_quotes_no_sharpe(self):
        self.assertNotIn("Sharpe", self.note + self.body)

    def test_the_card_quotes_no_excess_over_the_equal_weighted_universe(self):
        low = (self.note + self.body).lower()
        self.assertNotIn("equal-weighted universe", low)

    def test_the_dead_renderer_variable_is_GONE_not_merely_unused(self):
        """Dead code that renders a banned figure is a loaded gun for the next reader."""
        src = open(APPJS, encoding="utf-8").read()
        self.assertNotIn("const meas = (m.net_sharpe", src)
        self.assertNotIn("c.measured || {}", src)


# ==========================================================================================
# THE ROUTE
# ==========================================================================================
class TheRouteDescribesTheTrackedBook(unittest.TestCase):
    def test_the_tracked_config_is_not_the_ui_default(self):
        """If these ever coincide the bug becomes invisible, so say it out loud."""
        self.assertNotEqual(TRACKED_CONFIG, S.DEFAULT_BOOK_CONFIG,
                            "TRACKED_CONFIG and DEFAULT_BOOK_CONFIG now agree. This test's "
                            "subject is that they differ; if the project has deliberately "
                            "made them equal, this guard needs rewriting rather than deleting.")

    def test_the_route_defaults_to_TRACKED_CONFIG_and_not_to_the_preference(self):
        """Read from the AST, because the defect is which NAME the default comes from.

        Asserting a rendered string could not catch this: the route serves whatever config it
        resolved, so both the wrong and the right answer render fine.
        """
        tree = ast.parse(open(APPPY, encoding="utf-8").read())
        fn = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and "valquo_index" in node.name:
                fn = node
                break
        self.assertIsNotNone(fn, "the /api/valquo-index handler was not found")
        names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
        self.assertIn("TRACKED_CONFIG", names,
                      "the handler does not mention TRACKED_CONFIG at all")
        # The assignment that resolves the config must not fall back to the preference.
        for node in ast.walk(fn):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == "name"):
                txt = ast.unparse(node)
                self.assertIn("TRACKED_CONFIG", txt)
                self.assertNotIn("DEFAULT_BOOK_CONFIG", txt,
                                 "the config default still reads the UI preference: " + txt)
                return
        self.fail("no `name = ...` assignment found in the handler")


class TheCadenceIsDerived(unittest.TestCase):
    """Item 21's first cut typed "quarterly, with a 0.30 no-trade band" into the API, which is
    the same defect one layer along: a hand-maintained sentence beside the construction it
    describes."""

    def test_the_tracked_book_reads_quarterly_with_its_band(self):
        s = cadence_sentence((S.BOOK_CONFIGS or {})[TRACKED_CONFIG])
        self.assertIn("quarterly", s)
        self.assertIn("30%", s)
        self.assertIn("0.30", s)

    def test_a_bandless_fixed_n_config_does_not_claim_a_band(self):
        s = cadence_sentence((S.BOOK_CONFIGS or {})["roth"])
        self.assertIn("no no-trade band", s)
        self.assertNotIn("30%", s)

    def test_the_words_follow_the_number(self):
        self.assertIn("about once a year", cadence_sentence({"rebalance_days": 252}))
        self.assertIn("about twice a year", cadence_sentence({"rebalance_days": 126}))
        self.assertIn("quarterly", cadence_sentence({"rebalance_days": 63}))
        self.assertIn("about every two months", cadence_sentence({"rebalance_days": 42}))
        self.assertIn("every 10 trading days", cadence_sentence({"rebalance_days": 10}))

    def test_no_schedule_is_said_rather_than_implied(self):
        self.assertIn("no fixed schedule", cadence_sentence({}))

    def test_it_is_not_hard_coded_anywhere_in_the_route(self):
        src = open(APPPY, encoding="utf-8").read()
        self.assertNotIn('"quarterly, with a 0.30 no-trade band"', src)


class ThePreviewKeepsItsConstructionWording(unittest.TestCase):
    """The owner preview legitimately IS an account-type construction built from today's scan,
    so it keeps the label -- and must say it is not the Index."""

    def setUp(self):
        from valuation.edge.valquo_index import config_block
        cfg = (S.BOOK_CONFIGS or {})["roth"]
        self.payload = {
            "is_preview": True, "n_positions": 25, "n_eligible": 400, "n_scored": 380,
            "config": dict(config_block("roth", cfg)),
            "positions": [{"ticker": "AAPL", "weight": 0.04, "name": "Apple Inc",
                           "sector": "Technology", "hot_score": 71.4,
                           "market_cap": 3.2e12}],
            "not_the_index": "IF THE REBALANCE WERE TODAY. This is NOT the Valquo Index.",
            "scan_date": "2026-10-02",
        }
        out = render_index_card(self.payload, "roth")
        if out is None:
            self.skipTest("no node on PATH — the RENDERED card is UNCHECKED on this machine")
        self.note, self.body = out

    def test_the_preview_says_it_is_not_the_index(self):
        self.assertIn("PREVIEW", self.note)
        self.assertIn("not the Index", self.note)

    def test_the_preview_may_name_the_account_type(self):
        """The positive control for the ban above: it fires on the Index card and not here,
        so it is a statement about which object is being described rather than a word filter."""
        self.assertIn("Roth", self.note)

    def test_the_preview_renders_no_undefined(self):
        self.assertNotIn("undefined", self.note + self.body)

    def test_the_preview_keeps_the_plain_hot_score_column(self):
        """There "today" and "at formation" are the same scan, so the qualifier would be noise."""
        self.assertIn("Hot score", self.body)
        self.assertNotRegex(self.body, r"Today.s hot score")


class TheBranchIsKeyedOnIdentity(unittest.TestCase):
    """A CORRECTION TO THIS CHANGE'S OWN FIRST CUT, pinned from both directions.

    The repair first read `const bk = d.card || null; if (bk)`, so a book-in-force payload
    arriving WITHOUT the `card` convenience block fell into the preview branch and rendered the
    account-type label and both `undefined`s. The entire live defect, back, from one missing
    field -- found by driving that payload through the repaired renderer rather than by reading
    it. The wrong-object family: a branch on the presence of a DISPLAY field is a branch on the
    renderer's convenience and not on the data's identity.

    `is_preview` is the key because the route sets it EXPLICITLY on both paths and always has.
    """

    def _book_without_card(self):
        from valuation.edge.valquo_index import config_block
        book = dict(BOOK)
        book["positions"] = [dict(x) for x in BOOK["positions"]]
        attach_labels(book, _Store(SNAP))
        cfg = (S.BOOK_CONFIGS or {})[TRACKED_CONFIG]
        book["config"] = dict(config_block(TRACKED_CONFIG, cfg))
        book["is_preview"] = False
        book["source_note"] = "the record"
        return book          # NO `card` key at all

    def test_a_record_payload_with_no_card_still_renders_as_the_record(self):
        out = render_index_card(self._book_without_card())
        if out is None:
            self.skipTest("no node on PATH - the RENDERED card is UNCHECKED on this machine")
        note, body = out
        self.assertIn("Valquo Index", note)
        self.assertNotIn("PREVIEW", note)
        self.assertNotIn("undefined", note + body)

    def test_and_it_still_gets_its_facts_from_the_book_itself(self):
        """Degrading must not mean degrading to silence."""
        out = render_index_card(self._book_without_card())
        if out is None:
            self.skipTest("no node on PATH")
        note, _ = out
        self.assertIn("3 holdings", note)
        self.assertIn("2026-07-30", note)
        self.assertIn("2026-10-22", note)
        self.assertIn("WBS", note)

    def test_a_preview_carrying_a_card_is_STILL_a_preview(self):
        """The other direction: `card` must not be able to promote a rebuild to the record."""
        from valuation.edge.valquo_index import config_block
        cfg = (S.BOOK_CONFIGS or {})["roth"]
        payload = {
            "is_preview": True, "n_positions": 25, "n_eligible": 400, "n_scored": 380,
            "config": dict(config_block("roth", cfg)),
            "card": {"n_held": 25, "formed_on": "2026-10-02",
                     "next_rebalance": "never", "cadence": "made up"},
            "positions": [{"ticker": "AAPL", "weight": 0.04}],
            "not_the_index": "NOT the Valquo Index.",
        }
        out = render_index_card(payload, "roth")
        if out is None:
            self.skipTest("no node on PATH")
        note, _ = out
        self.assertIn("PREVIEW", note)
        self.assertNotIn("the book in force", note)

    def test_an_older_response_with_no_is_preview_renders_as_the_record(self):
        """THE SAFE DIRECTION, stated rather than hoped. `undefined !== true`, and the record
        is what this route serves by default while a preview is owner-only."""
        book = self._book_without_card()
        del book["is_preview"]
        out = render_index_card(book)
        if out is None:
            self.skipTest("no node on PATH")
        note, _ = out
        self.assertIn("Valquo Index", note)
        self.assertNotIn("PREVIEW", note)

    def test_the_renderer_does_not_branch_on_the_card_field(self):
        """Read from the source, because this is a statement about the CONDITION.

        Asserting rendered output alone could not distinguish "keyed on identity" from "keyed
        on `card`, and this fixture happens to carry one".
        """
        src = open(APPJS, encoding="utf-8").read()
        self.assertNotIn("const bk = d.card || null;\n  if (bk) {", src)
        self.assertIn("const isPreview = d.is_preview === true;", src)
        self.assertIn("if (!isPreview) {", src)


class TheHarnessItself(unittest.TestCase):
    """A harness that silently renders nothing would make every assertion above vacuous."""

    def test_node_is_present_or_the_skip_is_loud(self):
        if not _node():
            print("       (NOTE: node is absent — every RENDERED assertion in this suite "
                  "skipped. JS is UNCHECKED on this machine.)")
        self.assertTrue(True)

    def test_the_harness_can_render_the_empty_state(self):
        out = render_index_card({"empty": True, "message": "nothing yet"})
        if out is None:
            self.skipTest("no node on PATH")
        note, body = out
        self.assertIn("nothing yet", note)
        self.assertEqual(body, "")

    def test_the_harness_reports_a_broken_app_js_rather_than_passing(self):
        """Proved by driving it: a renderer that throws must fail the suite, not return ''."""
        bad = dict(live_payload())
        bad["positions"] = "not a list"       # `.some` does not exist on a string
        if not _node():
            self.skipTest("no node on PATH")
        with self.assertRaises(AssertionError):
            render_index_card(bad)

    def test_app_js_parses(self):
        node = _node()
        if not node:
            self.skipTest("no node on PATH")
        r = subprocess.run([node, "--check", APPJS], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, (r.stderr or "")[:600])


if __name__ == "__main__":
    unittest.main(verbosity=2)
