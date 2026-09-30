"""THE BACKTESTED CARD — one book per config, every benchmark named, tax stated on both sides.

Four families, each pointed at a way this has actually gone wrong or could:

  * **NO ALPHA WITHOUT A NAMED BENCHMARK.** The original defect: one tile said "Alpha / yr",
    and on this project that word has meant both "excess over the equal-weighted universe"
    (uninvestable, zero cost) and "excess over SPY". Asserted against the RENDERED payload and
    against the renderer.

  * **ONE BOOK PER CARD.** The defect the FIRST fix introduced. Version 1 published the roth
    top-25 book while the page's Sharpe and turnover followed the dropdown, so "taxable" showed
    a 32.1% gross beside a 0.90 after-tax Sharpe and the decile's turnover. Every figure must
    now come from the selected config, and switching the dropdown must move ALL of them.

  * **TAXABLE NET IS NOT ROTH NET, AND THE BENCHMARK IS TAXED TOO.** The tax drag on this book
    is about three times the cost drag: the net excess over SPY falls from ~+13.6pp to ~+4.5pp.
    Comparing an after-tax book against an untaxed index would hand the strategy the whole of
    the index's tax bill, so `untaxed_benchmark_against_taxed_book` must always be empty — and
    it is checked as a property of the payload, not trusted to the builder, because that
    failure would look entirely normal on the page.

  * **FAIL CLOSED.** Missing, wrong-schema, incomplete or impossible cards render nothing.

Run: python tests/test_backtest_card.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.screener import backtest_card as BC                       # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPJS = os.path.join(ROOT, "valuation", "web", "static", "app.js")
RESULTS = os.path.join(ROOT, "BACKTEST_RESULTS.json")

PASSED = FAILED = 0


def check(name, fn):
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print("  ok   %s" % name)
    except Exception as e:                                               # noqa: BLE001
        FAILED += 1
        print("  FAIL %s\n         %s: %s" % (name, type(e).__name__, e))


def _good():
    raw = BC.load()
    assert raw, "the published card is missing or unreadable"
    return raw


def _write(d, raw):
    p = os.path.join(d, "card.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(raw, f)
    return p


# =======================================================================================
# NO ALPHA WITHOUT A NAMED BENCHMARK
# =======================================================================================
def test_no_excess_line_appears_without_a_named_benchmark():
    for cfg in ("roth", "taxable"):
        c = BC.card(cfg)
        assert c["available"], (cfg, c)
        bad = BC.unlabelled_excesses(c)
        assert not bad, "%s: an excess line names no benchmark: %s" % (cfg, bad)
        ex = [l for l in c["lines"] if l["kind"] == "excess"]
        assert ex, "%s renders no excess at all, so the pin would be vacuous" % cfg
        for l in ex:
            assert l["benchmark"] in l["label"], (cfg, l)


def test_the_pin_can_actually_fire():
    forged = {"lines": [{"kind": "excess", "key": "vs_mystery",
                         "label": "Alpha / yr", "benchmark": ""}]}
    assert BC.unlabelled_excesses(forged) == ["vs_mystery"]


def test_the_renderer_never_prints_a_bare_alpha_tile():
    js = open(APPJS, encoding="utf-8").read()
    for needle in ('metric("Alpha', "metric('Alpha", 'metric(`Alpha'):
        assert needle not in js, "a bare Alpha tile is back in the renderer: %s" % needle


def test_every_level_line_says_gross_or_net():
    for cfg in ("roth", "taxable"):
        for l in [x for x in BC.card(cfg)["lines"] if x["kind"] == "level"]:
            low = l["label"].lower()
            assert ("gross" in low) or ("net" in low), (cfg, l["label"])


# =======================================================================================
# ONE BOOK PER CARD — the defect the first fix introduced
# =======================================================================================
def test_every_figure_on_the_card_moves_when_the_config_moves():
    """THE book-consistency pin. If any field were still read from a fixed book it would be
    identical across configs while its neighbours changed — which is exactly what shipped."""
    a, b = BC.card("roth"), BC.card("taxable")
    lv = lambda c: {l["key"]: l.get("value") for l in c["lines"] if l["kind"] == "level"}
    ex = lambda c: {l["key"]: (l.get("gross"), l.get("net"))
                    for l in c["lines"] if l["kind"] == "excess"}
    assert lv(a) != lv(b), "gross/net are identical across two different books"
    assert ex(a) != ex(b), "the excesses are identical across two different books"
    assert a["sharpe"] != b["sharpe"], "Sharpe did not follow the config"
    assert a["annual_turnover"] != b["annual_turnover"], "turnover did not follow the config"


def test_the_renderer_reads_sharpe_and_turnover_from_the_card_not_the_settings_block():
    """`bt.*` is the settings block for the selected config; mixing it with card figures from a
    different book is the shipped defect. The tiles must read `bc.*`."""
    js = open(APPJS, encoding="utf-8").read()
    assert 'metric("Sharpe", bc.sharpe == null' in js, "Sharpe is not read from the card"
    assert 'metric("Turnover / yr", bc.annual_turnover == null' in js, (
        "turnover is not read from the card")


def test_the_server_serves_the_card_for_the_config_it_was_asked_for():
    """THE WIRING, not just the reader. Found by mutation: every test above calls
    `BC.card(cfg)` directly, so reverting `index_track` to `_bc.card()` — dropping the
    selection and serving roth to everyone — passed the whole suite. The defect this version
    exists to fix would have come straight back through the one line nobody tested.
    """
    from valuation.screener import index_track as IT
    seen = {}
    for cfg in ("roth", "taxable"):
        card = (IT.summarize(config=cfg).get("backtested") or {}).get("card") or {}
        assert card.get("available"), (cfg, card)
        assert card.get("config") == cfg, (
            "asked for %r and the server returned the %r card" % (cfg, card.get("config")))
        seen[cfg] = card.get("net_means")
    assert seen["roth"] != seen["taxable"], (
        "both configs came back on the same tax basis: %r" % seen)


def test_each_book_reproduces_its_own_published_block():
    """The artifact is gated on this at build time; re-asserted here so drift is caught later.

    `net_alpha` is an excess over the EQUAL-WEIGHTED universe, which is how the results file
    states it — the card never renders that number, it is used only as an identity check that
    the recomputed book IS the published one.
    """
    if not os.path.exists(RESULTS):
        return
    pub = json.load(open(RESULTS, encoding="utf-8")).get("book_configs") or {}
    raw = _good()
    for name, book in (raw.get("books") or {}).items():
        want = pub.get(name) or {}
        got_turn = book["full"]["annual_turnover"]
        assert abs(float(want["annual_turnover"]) - float(got_turn)) < 1e-12, (
            "%s turnover %r vs published %r" % (name, got_turn, want["annual_turnover"]))
        # AGAINST THE BOOK'S OWN EQUAL-WEIGHT LEVEL, not the `benchmarks` block's. The results
        # file carries TWO -- 0.17239 from the cost/after-tax scorers and 0.18137 from
        # `benchmark_panel` -- both correct for their own construction, and reaching for the
        # wrong one fails this identity while every number in it is right. Found that way.
        ew_ann = book["full"].get("equal_weight_ann")
        assert ew_ann is not None, "%s stores no equal_weight_ann to check against" % name
        key = ("after_tax_alpha" if book["net_means"].endswith("taxes") else "net_alpha")
        implied = book["full"]["net_ann"] - float(ew_ann)
        assert abs(implied - float(want[key])) < 1e-9, (
            "%s: net implies %s %r against published %r" % (name, key, implied, want[key]))


# =======================================================================================
# TAX — the net means what it says, on both sides
# =======================================================================================
def test_the_taxable_net_is_after_tax_and_the_roth_net_is_not():
    r, t = BC.card("roth"), BC.card("taxable")
    assert r["net_means"] == "after costs", r["net_means"]
    assert t["net_means"] == "after costs and taxes", t["net_means"]
    rn = [l for l in r["lines"] if l["key"] == "net"][0]
    tn = [l for l in t["lines"] if l["key"] == "net"][0]
    assert "after costs" in rn["label"] and "tax" not in rn["label"].lower(), rn["label"]
    assert "taxes" in tn["label"], tn["label"]


def test_the_tax_drag_is_real_and_dominates_the_cost_drag():
    """Not a formatting difference. If tax were being applied as a token haircut this fails."""
    t = BC.card("taxable")
    cost, tax = t["cost_drag_ann"], t["tax_drag_ann"]
    assert cost and tax, t
    assert tax > cost, "the tax drag (%r) does not exceed the cost drag (%r)" % (tax, cost)
    assert tax > 0.02, "the tax drag is implausibly small for a 40.8%% short-term rate: %r" % tax


def test_an_after_tax_book_is_never_compared_against_an_untaxed_benchmark():
    """THE rigging check. It would flatter the strategy by the benchmark's whole tax bill."""
    for cfg in ("roth", "taxable"):
        bad = BC.untaxed_benchmark_against_taxed_book(BC.card(cfg))
        assert not bad, "%s compares an after-tax book against an untaxed benchmark: %s" % (
            cfg, bad)


def test_that_rigging_check_can_fire():
    forged = {"net_means": "after costs and taxes",
              "lines": [{"kind": "excess", "key": "vs_spy", "benchmark": "SPY",
                         "label": "vs SPY / yr", "benchmark_taxed": False}]}
    assert BC.untaxed_benchmark_against_taxed_book(forged) == ["vs_spy"]


def test_taxing_the_benchmark_makes_the_excess_smaller_not_larger():
    """A haircut applied with the wrong sign would RAISE the excess and still look plausible."""
    t = BC.card("taxable")
    raw = _good()["books"]["taxable"]["full"]
    assert raw["spy_ann"] < raw["spy_untaxed_ann"], (
        "the taxed SPY level is not below the untaxed one: %r vs %r"
        % (raw["spy_ann"], raw["spy_untaxed_ann"]))
    cap = t["caption"].lower()
    assert cap.count("defer") >= 1, "the caption does not state the deferral"
    # ...and it must say WHY that asymmetry is legitimate rather than merely asserting it,
    # because "we taxed one side less" is the sentence a reader is entitled to question.
    assert "smaller" in cap or "realises almost nothing" in cap, (
        "the caption states the deferral without explaining the benchmark's smaller tax bill")


def test_the_caption_states_the_tax_treatment_of_both_sides():
    t = BC.card("taxable")["caption"].lower()
    for w in ("40.8", "23.8", "qualified", "defer"):
        assert w in t, "the taxable caption omits %r" % w
    r = BC.card("roth")["caption"].lower()
    assert "no tax" in r, "the roth caption does not say it pays no tax"
    for w in ("gross", "net", "in-sample", "hypothetical", "tuned"):
        assert w in r and w in t, "a caption dropped %r" % w


# =======================================================================================
# THE BAND — say which width the figures were measured at
# =======================================================================================
def test_the_taxable_band_reports_the_width_its_figures_were_measured_at():
    raw = _good()["books"]["taxable"]
    band = raw.get("band") or {}
    assert band.get("live_width"), band
    assert band.get("figures_measured_at") == band["live_width"], (
        "the figures are not measured at the live width: %r" % band)
    if band.get("settings_measured_width") != band["live_width"]:
        assert band.get("stale_settings_note"), (
            "settings carries a different measured_width and the card says nothing")
        assert BC.card("taxable").get("band_note"), "the note never reaches the payload"


# =======================================================================================
# THE PARTIAL WINDOW
# =======================================================================================
def test_the_spmo_line_carries_its_own_window_label_and_inception():
    for cfg in ("roth", "taxable"):
        l = [x for x in BC.card(cfg)["lines"] if x["key"] == "vs_spmo"]
        assert l, "%s has no SPMO line" % cfg
        assert l[0]["window"] == "partial", l[0]
        assert "partial window" in (l[0].get("window_label") or "").lower(), l[0]
        assert (l[0].get("since") or "").startswith("2015-10"), l[0]


def test_the_spmo_line_ships_its_window_matched_spy_excess():
    for cfg in ("roth", "taxable"):
        l = [x for x in BC.card(cfg)["lines"] if x["key"] == "vs_spmo"][0]
        assert l.get("matched_spy_gross") is not None, (cfg, l)
        assert l["matched_spy_gross"] > l["gross"], (
            "%s: the window-matched SPY excess is not larger than the SPMO excess; the note "
            "claims it is" % cfg)


# =======================================================================================
# FAIL CLOSED
# =======================================================================================
def test_a_missing_card_renders_nothing():
    with tempfile.TemporaryDirectory() as d:
        assert BC.card("roth", os.path.join(d, "absent.json"))["available"] is False


def test_a_wrong_schema_renders_nothing():
    with tempfile.TemporaryDirectory() as d:
        raw = dict(_good())
        raw["schema"] = "something_else/9"
        assert BC.card("roth", _write(d, raw))["available"] is False


def test_an_unknown_config_renders_nothing_rather_than_defaulting():
    """Falling back to another book is exactly the mixing this version exists to end."""
    assert BC.card("no_such_book")["available"] is False


def test_an_incomplete_full_window_renders_nothing():
    with tempfile.TemporaryDirectory() as d:
        raw = json.loads(json.dumps(_good()))
        raw["books"]["roth"]["full"]["net_ann"] = None
        assert BC.card("roth", _write(d, raw))["available"] is False


def test_a_net_above_gross_renders_nothing_rather_than_a_caveat():
    with tempfile.TemporaryDirectory() as d:
        raw = json.loads(json.dumps(_good()))
        raw["books"]["roth"]["full"]["net_ann"] = raw["books"]["roth"]["full"]["gross_ann"] + 0.01
        assert BC.card("roth", _write(d, raw))["available"] is False


def test_a_missing_spmo_drops_only_its_line():
    with tempfile.TemporaryDirectory() as d:
        raw = json.loads(json.dumps(_good()))
        raw["books"]["roth"]["partial"]["vs_spmo_gross"] = None
        raw["books"]["roth"]["partial"]["vs_spmo_net"] = None
        c = BC.card("roth", _write(d, raw))
        assert c["available"] is True and c["spmo_available"] is False
        assert not [l for l in c["lines"] if l["key"] == "vs_spmo"]
        assert [l for l in c["lines"] if l["key"] == "vs_spy"], "the SPY line was lost too"


def test_the_basis_note_names_this_book_and_the_one_it_is_not():
    for cfg in ("roth", "taxable"):
        note = BC.card(cfg)["basis_note"]
        assert "portfolio" in note.lower(), note
        assert BC.B17_WARNING in note, "the B17 warning is not carried"


def test_the_renderer_is_syntactically_valid_javascript():
    """Nothing else here parses JS, and that gap once let a broken app.js through a green gate."""
    node = shutil.which("node")
    if not node:
        print("       (skipped: no node on PATH — JS syntax is UNCHECKED on this machine)")
        return
    r = subprocess.run([node, "--check", APPJS], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, "app.js does not parse: " + (r.stderr or "")[:600]


def run():
    global PASSED, FAILED
    print("BACKTESTED CARD")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            check(name, fn)
    print("\n%d passed, %d failed" % (PASSED, FAILED))
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
