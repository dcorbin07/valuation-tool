"""The theme legend describes the model the product actually runs — offline.

    python tests/test_theme_status.py

WHAT WENT WRONG, measured rather than supposed.

On 2026-08-11 the theme restoration wired `capital_discipline` into the live scoring path — the
adoption that closed vintage 2 and opened vintage 3. On that same day the legend in `app.js`
read:

    capital_discipline: "low share issuance · low asset growth (dormant — needs data)"

Both halves were false. The theme was not dormant; it had just become the fifth live theme. And
`factors.py:265` computes it as `df[["z_neg_issuance"]].mean(axis=1)` — **issuance only** —
because asset growth was deliberately removed for cancelling out the one input that works.

BE PRECISE ABOUT WHICH HALF WAS BROKEN, because it is not the obvious one. The BARS were always
data-driven: `_themeBars` enumerates whatever weights the payload carries, so the fifth theme
appeared on its own. What was hardcoded was the CAPTION UNDER the bar. That is the worse of the
two failures — a missing bar invites a question, a confident wrong caption closes one.

Four ways this rots, one group each:

1. **THE LEGEND AND THE MODEL DIVERGE AGAIN.** The theme set here must match
   `settings.FACTORS_ALL`, and a theme's inputs must not name a column `factors.py` has stopped
   averaging.

2. **A DEAD THEME LOOKS HEALTHY.** A theme carrying weight while contributing nothing is the
   standing failure mode (`insider`: 100% "covered", constant, renormalised away). Anything
   weighted-but-unwired must carry a dormancy reason, and the reason must say WHY.

3. **A LIVE THEME IS LIBELLED AS DORMANT.** The exact defect found. Anything wired must carry
   no dormancy note at all.

4. **app.js GROWS ITS OWN COPY BACK.** One source, or the two drift again.
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

from valuation.web import theme_status as TS  # noqa: E402
from valuation.screener import settings as S  # noqa: E402


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


#: Themes that reach a live score today. `capital_discipline` joined on 2026-08-11.
# UPDATED 2026-08-11 by FIDELITY-2: `institutional` and `insider` were rebuilt to the panel's
# own definitions and cleared the SAME 0.60 gate they had failed (+0.9190 and +0.8726), so
# they now reach a live score and must not be libelled as dormant.
_LIVE = {"value", "quality", "growth", "momentum", "size", "capital_discipline",
         "institutional", "insider"}
#: Weighted in at least one book, but NOT wired live.
_WEIGHTED_BUT_DEAD = {"insider", "institutional"}


# ------------------------------------------------ 1. legend vs model
def test_the_legend_covers_exactly_the_models_themes():
    assert set(TS.THEMES) == set(S.FACTORS_ALL), (
        f"legend/model mismatch: only-legend={set(TS.THEMES) - set(S.FACTORS_ALL)}, "
        f"only-model={set(S.FACTORS_ALL) - set(TS.THEMES)}")


def test_capital_discipline_names_issuance_only():
    """The specific regression. Asset growth was removed from the theme (factors.py:262) for
    cancelling out neg_issuance; a legend that still lists it describes a different model."""
    inp = TS.THEMES["capital_discipline"]["inputs"].lower()
    assert "issuance" in inp, inp
    assert "asset growth" not in inp, f"legend still lists a dropped input: {inp!r}"


def test_the_theme_really_is_one_column_in_the_code():
    """Pinned against `factors.py` itself, so the legend cannot quietly re-diverge if the theme
    gains an input back without the caption following."""
    src = _read("valuation", "screener", "factors.py")
    m = re.search(r'df\["capital_discipline"\]\s*=\s*df\[\[([^\]]*)\]\]', src)
    assert m, "could not locate the capital_discipline definition"
    cols = [c.strip().strip('"\'') for c in m.group(1).split(",") if c.strip()]
    assert cols == ["z_neg_issuance"], (
        f"capital_discipline now averages {cols} — the legend says issuance only")


def test_no_theme_claims_an_input_the_frame_never_builds():
    """A loose but real check: every theme's caption must be non-empty, since an empty caption
    under a bar is the state the hardcoded map degraded to for unknown keys."""
    for k, v in TS.THEMES.items():
        assert (v.get("inputs") or "").strip(), f"{k} has no inputs described"


# ------------------------------------------------ 2. dead themes are flagged
def test_every_weighted_but_unwired_theme_carries_a_reason():
    weights = dict(S.WEIGHTS_ESTABLISHED)
    weights.update({k: v for k, v in S.WEIGHTS_SPECULATIVE.items() if v})
    for k in _WEIGHTED_BUT_DEAD:
        if k in _LIVE:
            continue          # restored since this list was written; covered by _LIVE above
        assert weights.get(k, 0) > 0, f"{k} is no longer weighted — update this test's premise"
        reason = TS.THEMES[k]["dormant"]
        assert reason, f"{k} carries weight but contributes nothing, and the legend is silent"
        assert len(reason) > 20, f"{k}'s dormancy reason does not say why: {reason!r}"


def test_a_dormant_theme_says_WHY_and_not_merely_that_it_is_dormant():
    """REWRITTEN 2026-08-11. This used to name `institutional` and `insider` and require their
    reasons to cite a Spearman and a gate. Both have since been rebuilt and RESTORED, so the
    frozen list turned a legitimate restoration into a red test.

    The property worth keeping is not which themes are dormant -- that changes, and should --
    but that ANY dormant theme explains itself rather than just going quiet. 'needs data' would
    imply the fix is a download; for a theme that failed a fidelity gate it is not."""
    for k, v in TS.THEMES.items():
        r = (v.get("dormant") or "").strip()
        if not r:
            continue
        assert len(r) > 20, f"{k} is dormant and the legend does not say why: {r!r}"
        assert any(w in r.lower() for w in
                   ("gate", "spearman", "zeroed", "not for lack of data", "source")), \
            f"{k}'s dormancy reason does not name a cause: {r!r}"


def test_low_risk_is_described_as_switched_off_not_as_missing():
    r = TS.THEMES["low_risk"]["dormant"].lower()
    assert r, "low_risk carries zero weight and the legend says nothing"
    assert "not for lack of data" in r or "zeroed" in r, r


# ------------------------------------------------ 3. live themes are not libelled
def test_no_live_theme_is_marked_dormant():
    for k in sorted(_LIVE):
        assert not TS.THEMES[k]["dormant"], (
            f"{k} reaches a live score and the legend calls it dormant: "
            f"{TS.THEMES[k]['dormant']!r}")


def test_capital_discipline_is_live():
    """The one-line regression guard for the whole session."""
    assert TS.THEMES["capital_discipline"]["dormant"] == ""


def test_the_restoration_is_actually_wired_behind_that_claim():
    """The legend may only call the theme live because the code path exists. Checked against
    the screener, so deleting the enrichment breaks this rather than silently re-lying."""
    screen = _read("valuation", "screener", "screen.py")
    assert "_enrich_with_issuance(metrics, cfg)" in screen, "the live issuance fill is gone"
    assert os.path.exists(os.path.join(ROOT, "valuation", "screener", "issuance.py"))


# ------------------------------------------------ 4. one source
def test_app_js_holds_no_theme_copy_of_its_own():
    js = _read("valuation", "web", "static", "app.js")
    assert "const THEME_INPUTS" not in js, "the hardcoded legend map is back"
    assert "window.THEME_STATUS" in js, "app.js no longer reads the served legend"
    code = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
    code = re.sub(r"^\s*//.*$", " ", code, flags=re.M)
    assert "dormant — needs data" not in code, "the stale caption is back in app.js"


def test_the_page_injects_the_legend():
    html = _read("valuation", "web", "templates", "index.html")
    assert "window.THEME_STATUS = {{ theme_status|tojson }};" in html
    app = _read("valuation", "web", "app.py")
    assert '"theme_status": _theme_status.payload()' in app


def test_the_payload_is_json_serialisable_and_a_copy():
    p = TS.payload()
    json.dumps(p)
    p["value"]["inputs"] = "mutated"
    assert TS.THEMES["value"]["inputs"] != "mutated", "payload() leaks the module's own dicts"


def test_the_bars_were_and_remain_data_driven():
    """The half that was never broken, pinned so a later 'tidy-up' cannot hardcode the list.
    `_themeBars` must enumerate the payload, not a literal set of theme names."""
    js = _read("valuation", "web", "static", "app.js")
    m = re.search(r"function _themeBars\(w\) \{.*?\n\}", js, re.S)
    assert m, "could not locate _themeBars"
    assert "Object.entries(w)" in m.group(0), "the theme bars stopped being data-driven"


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
