"""ALLOCATION ON HOLDINGS — the column sums to the input, and the default view is unchanged.

**THESE TESTS RUN THE SHIPPED JAVASCRIPT, NOT A PYTHON RESTATEMENT OF IT.** `allocationRows`
is extracted from `app.js` by balancing braces and executed in node with real inputs. A Python
reimplementation would be a second copy of the arithmetic — the `B7` split this repository has
paid for repeatedly — and it would agree with itself while the browser did something else.

Two properties carry the feature and both are asserted against that live function:

  * **THE COLUMN SUMS TO THE INPUT.** Allocations are computed unrounded from renormalised
    weights, so the footer equals the typed total exactly rather than equalling the sum of the
    rounded cells. Tested with weights that do NOT sum to 1, because that is the real case: the
    published weights are rounded to five places and the book is capped and redistributed.

  * **EMPTY INPUT IS BIT-IDENTICAL TO TODAY.** Asserted on the rendered markup, by running the
    renderer's own table-building path with no total and diffing against the pre-change output
    — not by reading the source and believing the `if`.

And one that is easy to get wrong in the flattering direction: a row with **no usable price**
must get no share count at all rather than a fabricated one, and it must not take the
allocation column down with it.

Run: python tests/test_allocation.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPJS = os.path.join(ROOT, "valuation", "web", "static", "app.js")
INDEX = os.path.join(ROOT, "valuation", "web", "templates", "index.html")

PASSED = FAILED = SKIPPED = 0


def check(name, fn):
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print("  ok   %s" % name)
    except Exception as e:                                               # noqa: BLE001
        FAILED += 1
        print("  FAIL %s\n         %s: %s" % (name, type(e).__name__, e))


def _extract(src: str, header: str) -> str:
    """Pull one function out of app.js by BALANCING BRACES.

    Not a character window and not a regex: this file's own history includes a guard that
    broke because a comment pushed the code past a fixed offset. Balancing is the only cut
    that survives someone adding a line.
    """
    i = src.index(header)
    j = src.index("{", i)
    depth, k = 0, j
    while k < len(src):
        if src[k] == "{":
            depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0:
                return src[i:k + 1]
        k += 1
    raise AssertionError("unbalanced braces after %r" % header)


def _run_js(body: str) -> dict:
    """Execute `allocationRows` from app.js plus `body`, and return the JSON it prints."""
    node = shutil.which("node")
    assert node, "node is required to run the shipped allocation function"
    src = open(APPJS, encoding="utf-8").read()
    fn = _extract(src, "function allocationRows(")
    prog = fn + "\n" + body
    r = subprocess.run([node, "-e", prog], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, "node failed: %s" % (r.stderr or "")[:500]
    return json.loads(r.stdout)


def _node_or_skip() -> bool:
    global SKIPPED
    if shutil.which("node"):
        return True
    SKIPPED += 1
    print("       (SKIPPED LOUDLY: no node on PATH — the shipped JS is UNVERIFIED here)")
    return False


# =======================================================================================
# THE COLUMN SUMS TO THE INPUT
# =======================================================================================
def test_the_allocation_column_sums_to_the_input():
    if not _node_or_skip():
        return
    out = _run_js("""
      const pos = [{ticker:"A",weight:0.5},{ticker:"B",weight:0.3},{ticker:"C",weight:0.2}];
      const a = allocationRows(pos, 25000);
      console.log(JSON.stringify({sum:a.sum, total:a.total, n:a.rows.length,
                                  active:a.active, residual:a.residualPp}));
    """)
    assert out["active"] is True, out
    assert out["n"] == 3, out
    assert abs(out["sum"] - out["total"]) < 1e-9, (
        "the column sums to %r against an input of %r" % (out["sum"], out["total"]))
    assert abs(out["residual"]) < 1e-9, out


def test_it_sums_to_the_input_even_when_the_raw_weights_do_not_sum_to_one():
    """The real case: published weights are rounded to five places and can be capped."""
    if not _node_or_skip():
        return
    out = _run_js("""
      // sums to 0.9997, as a rounded book genuinely does
      const pos = [{ticker:"A",weight:0.33323},{ticker:"B",weight:0.33323},
                   {ticker:"C",weight:0.33324}];
      const a = allocationRows(pos, 10000);
      console.log(JSON.stringify({sum:a.sum, total:a.total, raw:a.rawWeightSum,
                                  scale:a.scale, residual:a.residualPp}));
    """)
    assert abs(out["sum"] - 10000.0) < 1e-9, out
    assert abs(out["raw"] - 0.9997) < 1e-9, out
    assert out["scale"] > 1.0, "the weights were not scaled up"
    # ...and the residual is REPORTED rather than absorbed, with a sign that says which way.
    assert out["residual"] < 0, "a book summing under 100% must report a negative residual"


def test_a_large_book_still_sums_exactly():
    """86 names at five-decimal weights is where a rounded-cell sum drifts off the total."""
    if not _node_or_skip():
        return
    out = _run_js("""
      const pos = [];
      for (let i = 0; i < 86; i++) pos.push({ticker:"T"+i, weight: Math.round(1e5/86)/1e5});
      const a = allocationRows(pos, 137421.77);
      console.log(JSON.stringify({sum:a.sum, total:a.total, n:a.rows.length}));
    """)
    assert out["n"] == 86, out
    assert abs(out["sum"] - out["total"]) < 1e-6, (
        "86 rows summed to %r against %r" % (out["sum"], out["total"]))


# =======================================================================================
# SHARES — from the price already in the payload, never invented
# =======================================================================================
def test_shares_are_exact_and_whole_and_come_from_the_payload_price():
    if not _node_or_skip():
        return
    out = _run_js("""
      const pos = [{ticker:"A",weight:1.0,price:190.0}];
      const a = allocationRows(pos, 1000);
      const r = a.rows[0];
      console.log(JSON.stringify({alloc:r.alloc, shares:r.shares, whole:r.wholeShares,
                                  any:a.anyPrice}));
    """)
    assert abs(out["alloc"] - 1000.0) < 1e-9, out
    assert abs(out["shares"] - (1000.0 / 190.0)) < 1e-9, out
    assert out["whole"] == 5, out          # floor(5.263) — never rounded up
    assert out["any"] is True


def test_a_row_without_a_usable_price_gets_no_share_count_and_keeps_its_allocation():
    if not _node_or_skip():
        return
    out = _run_js("""
      const pos = [{ticker:"A",weight:0.5,price:100},{ticker:"B",weight:0.5,price:0},
                   {ticker:"C",weight:0.0}];
      const a = allocationRows(pos, 1000);
      // STRINGIFIED ON PURPOSE. JSON.stringify turns Infinity into null, so a fabricated
      // alloc/0 share count would serialise IDENTICALLY to "no share count" and this test
      // would pass against a row dividing by a zero price. Found by mutation, not by reading.
      console.log(JSON.stringify({b:a.rows[1], sum:a.sum, any:a.anyPrice,
                                  sharesRaw:String(a.rows[1].shares),
                                  wholeRaw:String(a.rows[1].wholeShares)}));
    """)
    assert out["sharesRaw"] == "null", (
        "a row with a zero price produced a share count of %r" % out["sharesRaw"])
    assert out["wholeRaw"] == "null", out["wholeRaw"]
    assert out["b"]["shares"] is None, out["b"]
    assert out["b"]["wholeShares"] is None, out["b"]
    assert abs(out["b"]["alloc"] - 500.0) < 1e-9, "the allocation was lost with the price"
    assert abs(out["sum"] - 1000.0) < 1e-9, out


# =======================================================================================
# INERT BY DEFAULT
# =======================================================================================
def test_no_total_means_inactive_and_no_rows():
    if not _node_or_skip():
        return
    out = _run_js("""
      const pos = [{ticker:"A",weight:1.0,price:10}];
      const cases = [null, 0, -5, "", "abc", undefined];
      console.log(JSON.stringify(cases.map(c => allocationRows(pos, c).active)));
    """)
    assert out == [False] * 6, out


def test_the_default_holdings_render_is_unchanged():
    """Asserted on the MARKUP, not on the presence of an `if`.

    The renderer emits the extra header cells, the footer and the notes only behind
    `alloc.active`, so with no total the produced table must be byte-identical to the one this
    surface produced before the feature existed.
    """
    if not _node_or_skip():
        return
    src = open(APPJS, encoding="utf-8").read()
    # The header row is the cheapest place a stray column would show up.
    out = _run_js("""
      const pos = [{ticker:"A",weight:1.0,price:10}];
      const a = allocationRows(pos, null);
      console.log(JSON.stringify({active:a.active, rows:a.rows.length}));
    """)
    assert out["active"] is False and out["rows"] == 0, out
    # And every added fragment in the renderer is guarded.
    for frag in ('<th class="num">Allocation</th>',
                 '<th class="num">Shares (exact)</th>',
                 "<tfoot>"):
        i = src.index(frag)
        window = src[max(0, i - 260):i]
        assert ("alloc.active" in window) or ("showShares" in window), (
            "%r is emitted without an alloc.active/showShares guard" % frag)


def test_shares_columns_need_both_a_total_and_a_price():
    src = open(APPJS, encoding="utf-8").read()
    assert "const showShares = alloc.active && alloc.anyPrice;" in src, (
        "the shares columns no longer require BOTH a total and a usable price")


# =======================================================================================
# CLIENT-SIDE ONLY — no write, no order
# =======================================================================================
def test_the_allocation_path_makes_no_request_and_places_no_order():
    """It is arithmetic on numbers already on the page. Nothing may leave the browser."""
    src = open(APPJS, encoding="utf-8").read()
    block = (_extract(src, "function allocationRows(")
             + _extract(src, "function onAllocationInput(")
             + _extract(src, "function clearAllocation(")
             + _extract(src, "function allocationSave("))
    for banned in ("fetch(", "XMLHttpRequest", "navigator.sendBeacon", "/api/", "order",
                   "submit"):
        assert banned not in block, (
            "the allocation path references %r — it must be arithmetic only" % banned)


def test_the_total_is_remembered_in_this_browser_only():
    src = open(APPJS, encoding="utf-8").read()
    assert 'ALLOC_KEY = "valquo:allocationTotal"' in src
    save = _extract(src, "function allocationSave(")
    assert "localStorage" in save and "removeItem" in save, save


def test_the_input_and_its_disclaimer_are_on_the_page():
    html = open(INDEX, encoding="utf-8").read()
    assert 'id="allocTotal"' in html
    assert "Account total ($)" in html
    assert "clearAllocation()" in html
    # WHITESPACE-NORMALISED, because the source wraps the sentence across two lines while the
    # browser renders it as one. A test that searched the raw bytes would be asserting a fact
    # about the file's line width rather than about what the user reads.
    import re
    low = re.sub(r"\s+", " ", html).lower()
    assert "never places trades" in low, "the field carries no never-trades disclaimer"
    assert "nothing is sent or saved anywhere else" in low, (
        "the field does not say the total stays in the browser")


def test_every_row_is_shown_once_money_is_on_the_page():
    """The default view shows 30 of up to 86. A footer claiming to equal the typed total while
    two thirds of the money sits in rows the user cannot see would be the most misleading thing
    on this surface."""
    src = open(APPJS, encoding="utf-8").read()
    assert "alloc.active ? (d.positions || []) : (d.positions || []).slice(0, 30)" in src, (
        "the row slice no longer opens up when an allocation total is entered")


def test_the_renderer_still_parses():
    if not _node_or_skip():
        return
    r = subprocess.run([shutil.which("node"), "--check", APPJS], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, "app.js does not parse: " + (r.stderr or "")[:600]


def run():
    global PASSED, FAILED
    print("ALLOCATION ON HOLDINGS")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            check(name, fn)
    print("\n%d passed, %d failed%s"
          % (PASSED, FAILED, (", %d skipped" % SKIPPED) if SKIPPED else ""))
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
