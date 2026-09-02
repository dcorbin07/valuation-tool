"""THE BACKTESTED CARD — no alpha may appear without a named benchmark.

That is the pin the whole change exists for. The card used to print one figure labelled
"Alpha / yr" with no benchmark named, and on this project "alpha" has meant BOTH "excess over
the equal-weighted universe" — uninvestable, and charged zero trading cost while the strategy
pays — and "excess over SPY". Those differ by several points a year on the same book, so a
reader could not tell which claim was being made, and the obvious guess was the wrong one.

Three families here, and each is pointed at a different way this could go wrong:

  * **THE BENCHMARK PIN.** Asserted against the RENDERED payload, not the source (the V3 /
    `dip_posture` precedent — rendering is where copy leaks), AND against the renderer, so a
    future edit cannot reintroduce a bare "Alpha" tile that the payload never sees.

  * **FAIL CLOSED.** Missing, wrong-schema, incomplete or internally impossible cards must make
    the whole section disappear. A performance card that renders half its lines is worse than
    one that renders none, because the half that renders is the half that flatters.

  * **THE PARTIAL WINDOW CANNOT BE LAUNDERED INTO A FULL ONE.** SPMO listed 2015-10-09. Its
    line must carry its own window label, and the window-matched SPY excess must travel with
    it — without which the card invites one specific misreading, that SPMO is the easier
    benchmark. It is the harder one.

Run: python tests/test_backtest_card.py
"""
from __future__ import annotations

import json
import os
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
# THE BENCHMARK PIN — the reason this change exists
# =======================================================================================
def test_no_excess_line_appears_without_a_named_benchmark():
    """THE pin. Every excess names its benchmark, in the LABEL and in a field."""
    c = BC.card()
    assert c["available"], c
    bad = BC.unlabelled_excesses(c)
    assert not bad, "an excess line names no benchmark: %s" % bad
    excesses = [l for l in c["lines"] if l["kind"] == "excess"]
    assert excesses, "the card renders no excess at all, so the pin would be vacuous"
    for l in excesses:
        assert l["benchmark"] in l["label"], l


def test_the_pin_can_actually_fire():
    """A guard that cannot fail is not a guard. Positive control."""
    forged = {"lines": [{"kind": "excess", "key": "vs_mystery",
                         "label": "Alpha / yr", "benchmark": ""}]}
    assert BC.unlabelled_excesses(forged) == ["vs_mystery"], BC.unlabelled_excesses(forged)


def test_the_renderer_never_prints_a_bare_alpha_tile():
    """Pinned on the RENDERER too, so a future edit cannot reintroduce what the payload lost."""
    js = open(APPJS, encoding="utf-8").read()
    for needle in ('metric("Alpha', "metric('Alpha", 'metric(`Alpha'):
        assert needle not in js, "a bare Alpha tile is back in the renderer: %s" % needle


def test_every_level_line_says_gross_or_net():
    c = BC.card()
    for l in [x for x in c["lines"] if x["kind"] == "level"]:
        low = l["label"].lower()
        assert ("gross" in low) or ("net" in low), (
            "a level line states neither gross nor net: %r" % l["label"])


# =======================================================================================
# FAIL CLOSED
# =======================================================================================
def test_a_missing_card_renders_nothing():
    with tempfile.TemporaryDirectory() as d:
        c = BC.card(os.path.join(d, "absent.json"))
        assert c["available"] is False, c


def test_a_wrong_schema_renders_nothing():
    with tempfile.TemporaryDirectory() as d:
        raw = dict(_good())
        raw["schema"] = "something_else/9"
        assert BC.card(_write(d, raw))["available"] is False


def test_an_incomplete_full_window_renders_nothing():
    with tempfile.TemporaryDirectory() as d:
        raw = json.loads(json.dumps(_good()))
        raw["full"]["net_ann"] = None
        assert BC.card(_write(d, raw))["available"] is False


def test_a_net_above_gross_renders_nothing_rather_than_a_caveat():
    """Net above gross means the cost model was not applied, or applied backwards."""
    with tempfile.TemporaryDirectory() as d:
        raw = json.loads(json.dumps(_good()))
        raw["full"]["net_ann"] = raw["full"]["gross_ann"] + 0.01
        assert BC.card(_write(d, raw))["available"] is False


def test_a_missing_spmo_drops_only_its_line_and_keeps_the_rest():
    """SPMO is the one figure that needs a network fetch, so its absence must not take the
    card down — but it must not silently become a full-window number either."""
    with tempfile.TemporaryDirectory() as d:
        raw = json.loads(json.dumps(_good()))
        raw["partial"]["vs_spmo_gross"] = None
        raw["partial"]["vs_spmo_net"] = None
        c = BC.card(_write(d, raw))
        assert c["available"] is True, c
        assert c["spmo_available"] is False
        assert not [l for l in c["lines"] if l["key"] == "vs_spmo"], c["lines"]
        assert [l for l in c["lines"] if l["key"] == "vs_spy"], "the SPY line was lost too"


# =======================================================================================
# THE PARTIAL WINDOW
# =======================================================================================
def test_the_spmo_line_carries_its_own_window_label_and_inception():
    c = BC.card()
    spmo = [l for l in c["lines"] if l["key"] == "vs_spmo"]
    assert spmo, "no SPMO line to check"
    l = spmo[0]
    assert l["window"] == "partial", l
    assert "partial window" in (l.get("window_label") or "").lower(), l
    assert (l.get("since") or "").startswith("2015-10"), l


def test_the_spmo_line_ships_its_window_matched_spy_excess():
    """Without this the card invites the one misreading it must not invite."""
    c = BC.card()
    l = [x for x in c["lines"] if x["key"] == "vs_spmo"][0]
    assert l.get("matched_spy_gross") is not None, l
    # ...and on the SAME window SPY is the EASIER benchmark, which is the fact that makes the
    # matched figure worth printing rather than decorative.
    assert l["matched_spy_gross"] > l["gross"], (
        "the window-matched SPY excess is not larger than the SPMO excess; re-read the card "
        "before publishing, because the note claims it is")


def test_the_full_window_lines_are_not_the_partial_window():
    raw = _good()
    assert raw["full"]["first_date"] < raw["partial"]["first_date"], raw
    assert raw["partial"]["n_periods"] < raw["full"]["n_periods"], raw


# =======================================================================================
# PROVENANCE — the card describes the book it claims to
# =======================================================================================
def test_the_card_reproduces_the_published_roth_book():
    """C1, re-asserted at test time: the artifact must still match what is on record."""
    if not os.path.exists(RESULTS):
        return
    pub = json.load(open(RESULTS, encoding="utf-8"))["costs"]["top_25"]
    raw = _good()
    for k in ("gross_ann", "net_ann"):
        assert abs(float(raw["full"][k]) - float(pub[k])) < 1e-12, (
            "%s drifted from BACKTEST_RESULTS.json: %r vs %r" % (k, raw["full"][k], pub[k]))


def test_the_net_uses_the_measured_drag_and_not_the_stale_settings_figure():
    """`settings.BOOK_CONFIGS[roth].measured.cost_drag_ann` is 0.0440 and its OWN comment
    records it as a pre-B6 figure never re-measured. The measured drag is 0.0325."""
    from valuation.screener import settings as S
    stale = (S.BOOK_CONFIGS["roth"]["measured"] or {}).get("cost_drag_ann")
    raw = _good()
    drag = float(raw["full"]["gross_ann"]) - float(raw["full"]["net_ann"])
    assert abs(drag - float(stale)) > 1e-6, (
        "the card's net is charged the stale settings drag %r" % stale)
    assert abs(drag - float(raw["full"]["cost_drag_ann"])) < 1e-12


def test_the_basis_note_says_which_book_and_names_the_other_one():
    c = BC.card()
    note = c["basis_note"]
    assert "roth" in note.lower() and "portfolio" in note.lower(), note
    assert BC.B17_WARNING in note, "the B17 warning is not carried"


def test_the_caption_keeps_every_required_disclosure():
    cap = BC.CAPTION.lower()
    for word in ("gross", "net", "in-sample", "hypothetical", "tuned"):
        assert word in cap, "the caption dropped %r" % word


def test_the_longer_price_window_is_inert_for_every_shipped_caller():
    """`prices._yf_history` gained a "max" tier so a benchmark can be measured since its own
    inception. It is ADDITIVE: the largest `days` any shipped caller passes is 2700, which
    still maps to "10y". Pinned so a future edit cannot lower the threshold into live callers.

    The 10y cap is why this was needed at all, and the failure it caused is worth recording:
    it returned a full-looking frame that silently STARTED A YEAR LATE, so the first attempt
    compared a book from 2015-10 against an ETF from 2016-09 and looked entirely healthy.
    """
    import re
    src = open(os.path.join(ROOT, "valuation", "screener", "prices.py"), encoding="utf-8").read()
    m = re.search(r'period = \(("max" if days > (\d+))', src)
    assert m, "the period mapping changed shape; re-read it before editing this test"
    threshold = int(m.group(2))
    assert threshold >= 3650, (
        "the max tier fires at %d days, which is inside the range shipped callers use "
        "(largest is 2700)" % threshold)


def test_the_renderer_is_syntactically_valid_javascript():
    """NOTHING ELSE IN THIS SUITE PARSES JAVASCRIPT, AND THAT GAP COST A REAL DEFECT.

    While wiring these lines I wrote `${/* comment */}` inside a template literal. An
    interpolation needs an EXPRESSION and a bare comment is not one, so `app.js` failed to
    parse — which would have taken down the whole page, not just this card. Every Python test
    here still passed, because they read the file as TEXT: the renderer pin greps for a bare
    Alpha tile and a grep is happy with a file that will never execute.

    So the file is handed to a real parser. Skips LOUDLY if node is absent rather than passing
    on a machine that cannot check — a silent skip here is the vacuous pass this repo keeps
    paying for.
    """
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        print("       (skipped: no node on PATH — JS syntax is UNCHECKED on this machine)")
        return
    r = subprocess.run([node, "--check", APPJS], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, "app.js does not parse: " + (r.stderr or "")[:800]


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
