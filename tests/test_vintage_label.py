"""The operated record names its own vintage, and the name is the register's — offline.

    python tests/test_vintage_label.py

WHAT IS AT RISK, and the session that produced this file is the evidence.

`PAPER_TRACK_CONTRACT.md` §5a Rule 4: *"a verdict is a statement about a vintage, and must name
it."* The forward-track card is the closest thing the product publishes to such a statement, and
until now it named an inception date and never the vintage that date belongs to. A reader could
not tell that the series had restarted, nor that a predecessor was being shadowed.

THE FAILURE MODE IS NOT HYPOTHETICAL. This work was commissioned as *"Book vintage 2 since
2026-08-11 (capital_discipline restored); vintage 1 runs in shadow"*. The register says the live
vintage is **3** and the shadowed one is **2** — the theme restoration had opened a vintage that
the request had not caught up with, on the same day. A hand-written label would have shipped that
off-by-one to the one surface whose entire job is to say which book the numbers describe.

So the rule this file enforces is: **the label is DERIVED, and pinned to the derivation rather
than to today's numbers.** `tests/test_track_meter.py` already learned the second half the hard
way — it used to assert "it is vintage 2", and a legitimate vintage event then failed a test that
exists to catch two vintages being open at once. Pinning `3` here would rot exactly as fast.

Four ways this can rot, one group each:

1. **THE LABEL DRIFTS FROM THE REGISTER.** Any literal vintage number in a rendered string is
   the defect; the phrase must be reconstructible from `VINTAGES` alone.

2. **THE TWO HALVES DISAGREE.** "Which vintage is live" comes from `track_meter`, "which one is
   shadowed" is also answered by `shadow_vintage.open_pairs()`. Two sources for one fact drift,
   so they are cross-checked here — this file may import both; `valuation/web` may not.

3. **THE SHADOW'S NUMBERS LEAK.** `V1`'s outbound fence exists because PT-OUTBOUND published a
   research figure. Naming a vintage is bookkeeping; publishing its paired difference is not.
   The fence must still hold with the label shipped.

4. **PUBLIC POSTURE MOVES.** The label is an owner-surface addition. The backtested/live
   headline rule, and the public landing copy, must be untouched by it.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import state_isolation  # noqa: F401,E402  -- MUST precede any `valuation` import

from valuation.edge import track_meter as TM  # noqa: E402
from valuation.edge import shadow_vintage as SV  # noqa: E402


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


# ------------------------------------------------ 1. the label IS the register
def test_the_label_is_rebuilt_from_the_register_and_not_typed():
    """Reconstruct the expected phrase from VINTAGES independently, then compare."""
    lab = TM.vintage_label()
    cur = TM.current_vintage()

    assert lab["vintage"] == cur["vintage"], "label names a different vintage than the register"
    assert lab["since"] == cur["opened"].isoformat(), "label's date is not the vintage's opening"
    assert f"vintage {cur['vintage']}" in lab["phrase"]
    assert cur["opened"].isoformat() in lab["phrase"]


def test_the_shadow_is_the_immediate_predecessor():
    lab = TM.vintage_label()
    n = TM.current_vintage()["vintage"]
    earlier = [int(v["vintage"]) for v in TM.VINTAGES if int(v["vintage"]) < n]
    assert lab["shadow_vintage"] == (max(earlier) if earlier else None)
    if earlier:
        assert f"vintage {max(earlier)} runs in shadow" in lab["phrase"]


def test_a_first_vintage_has_no_shadow_clause():
    """The stub that reads as a bug: '; None runs in shadow' on the one surface nobody revisits.

    Exercised by mutation rather than by trusting the branch — with only vintage 1 in the
    register there is no predecessor, and the clause must be absent entirely.
    """
    only_first = tuple(v for v in TM.VINTAGES if v["vintage"] == 1)
    real = TM.VINTAGES
    try:
        TM.VINTAGES = tuple({**v, "status": "OPEN", "closed": None} for v in only_first)
        lab = TM.vintage_label()
        assert lab["shadow_vintage"] is None
        assert "shadow" not in lab["phrase"].lower(), lab["phrase"]
        assert "None" not in lab["phrase"], lab["phrase"]
    finally:
        TM.VINTAGES = real


def test_every_register_row_carries_a_short_label():
    """The parenthetical comes from the register too, so it cannot be invented at the surface."""
    for v in TM.VINTAGES:
        assert (v.get("label") or "").strip(), f"vintage {v['vintage']} has no short label"
        assert len(v["label"]) <= 60, f"vintage {v['vintage']} label is a paragraph, not a label"


def test_the_open_vintages_label_is_the_one_rendered():
    lab = TM.vintage_label()
    assert f"({TM.current_vintage()['label']})" in lab["phrase"]


# ------------------------------------------------ 2. the two sources agree
def test_the_label_and_the_shadow_machinery_name_the_same_pair():
    """`open_pairs()` answers 'can the predecessor be scored'; the label answers 'which is it'.

    They are computed independently and must not disagree. If they ever do, one of them is
    describing a vintage that the other does not think exists.
    """
    lab = TM.vintage_label()
    pairs = SV.open_pairs()
    if not pairs:
        return  # no pinned pair yet; the label still stands on the register alone
    assert len(pairs) == 1, f"expected one open pair, got {pairs}"
    p = pairs[0]
    assert p["live_vintage"] == lab["vintage"], (p, lab)
    assert p["shadow_vintage"] == lab["shadow_vintage"], (p, lab)


def test_the_meter_and_the_label_share_one_inception():
    assert TM.INCEPTION.isoformat() == TM.vintage_label()["since"]


# ------------------------------------------------ 3. it reaches the owner surfaces
def test_the_contract_block_carries_the_label():
    d = TM.detail(series=[])
    assert d.get("available") is True, d
    assert "vintage_label" in d, "contract_track dropped the label"
    assert d["vintage_label"]["phrase"] == TM.vintage_label()["phrase"]
    assert d["vintage_label"]["vintage"] == d["vintage"], "two vintage numbers in one payload"


def test_the_index_track_route_attaches_the_label():
    src = _read("valuation", "web", "app.py")
    m = re.search(r"def api_index_track\(\).*?\n@app\.route", src, re.S)
    assert m, "could not locate api_index_track"
    body = m.group(0)
    assert "track_meter.vintage_label()" in body, "the index-track card has no vintage label"


def test_the_card_renders_the_served_phrase_and_builds_no_sentence_of_its_own():
    """The card may escape the phrase. It may not assemble one, or the number and the date stop
    moving together — the same rule LA8 applied to the track's age."""
    js = _read("valuation", "web", "static", "app.js")
    # NB: bounded by the next statement, not by a `;` — the rendered CSS is full of semicolons
    # and an earlier version of this regex stopped inside the style attribute and "passed" by
    # never reaching the code it was meant to check.
    m = re.search(r"const vin = d\.vintage.*?\n\s*let liveRows;", js, re.S)
    assert m, "the vintage line is not rendered from the payload"
    seg = m.group(0)
    assert "vin.phrase" in seg, "the card does not render the served phrase"
    # Comments are stripped first. The prose explaining WHY the copy is served rather than
    # written necessarily names the vintage that motivated it, and banning the words from the
    # explanation would push the explanation out of the file — the opposite of the intent.
    code = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
    code = re.sub(r"^\s*//.*$", " ", code, flags=re.M)
    for banned in ("Book vintage", "runs in shadow", "vintage 1", "vintage 2", "vintage 3"):
        assert banned not in code, f"app.js hardcodes vintage copy: {banned!r}"


def test_the_label_is_json_serialisable():
    json.dumps(TM.vintage_label())


# ------------------------------------------------ 4. fences and posture
def test_the_shadows_numbers_still_do_not_reach_an_outbound_surface():
    """The fence `test_shadow_vintage.py` owns, re-asserted from the side that just added a
    surface. Naming a vintage is bookkeeping; shipping its paired difference is not."""
    offenders = []
    for sub in ("valuation/saas", "valuation/web"):
        base = os.path.join(ROOT, *sub.split("/"))
        for dirpath, _dirs, files in os.walk(base):
            for f in files:
                if not f.endswith(".py"):
                    continue
                path = os.path.join(dirpath, f)
                try:
                    src = open(path, encoding="utf-8").read()
                except OSError:
                    continue
                if "shadow_vintage" in src:
                    offenders.append(os.path.relpath(path, ROOT))
    assert not offenders, f"the shadow module reached an outbound surface: {offenders}"


def test_the_label_carries_no_measurement():
    """Bookkeeping only. A return, an excess or a paired difference in this dict would be the
    leak the fence exists to prevent, arriving through the door marked 'label'."""
    lab = TM.vintage_label()
    # No float anywhere: a paired difference, an excess or a Sharpe would arrive as one.
    assert not any(isinstance(v, float) for v in lab.values()), lab
    # And no measurement vocabulary in the keys or the rendered strings. Whole words only —
    # substring matching would flag "approach" for "pp" and the test would be dodged by
    # rewording rather than by not leaking.
    words = set(re.findall(r"[a-z_]+", json.dumps(lab).lower()))
    leaked = words & {"excess", "alpha", "sharpe", "spy", "ret", "pp",
                      "cagr", "drawdown", "ir", "tracking"}
    assert not leaked, f"the label carries measurement vocabulary: {sorted(leaked)}"


def test_public_posture_language_is_untouched():
    """The label is an owner-surface addition. The headline rule and the public landing copy
    are a different finding's copy and were explicitly out of scope."""
    it = _read("valuation", "screener", "index_track.py")
    # The gate counts RECORDED ROWS (LA8's rule). A vintage label is not a reason to move it.
    assert "long_enough = days >= MIN_LIVE_DAYS" in it, "the gate moved off recorded rows"
    # ...and the headline still needs the contract's row, not just a day count.
    assert 'headline' in it and 'gate["passed"]' in it, "the headline rule changed"
    landing = _read("valuation", "web", "templates", "landing.html")
    assert "vintage" not in landing.lower(), "the vintage reached the public landing page"


def test_the_index_track_card_is_owner_only():
    """The whole argument that a vintage label is safe to render rests on this path being
    owner-gated. If it is ever published, the decision needs revisiting, not the label."""
    src = _read("valuation", "saas", "surfaces.py")
    m = re.search(r"OWNER_ONLY_PATHS\s*=\s*frozenset\(\{(.*?)\}\)", src, re.S)
    assert m, "could not locate OWNER_ONLY_PATHS"
    assert '"/api/index-track"' in m.group(1), "/api/index-track is no longer owner-only"


def test_the_rule_sentence_travels_with_the_label():
    lab = TM.vintage_label()
    assert "own clock" in lab["rule"] and "statement about a vintage" in lab["rule"]


if __name__ == "__main__":
    fns = [(k, v) for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    failed = 0
    for name, fn in fns:
        try:
            fn()
            print(f"  ok  {name}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {name}\n      {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"ERR   {name}\n      {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
