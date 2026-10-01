"""What each theme is made of, and whether it reaches a live score today.

WHY THIS MODULE EXISTS
----------------------
The theme legend in `static/app.js` was a hand-maintained map (`THEME_INPUTS`), and on
2026-08-11 it was measurably wrong about the theme the whole day's work was about:

    capital_discipline: "low share issuance · low asset growth (dormant — needs data)"

Both halves were false. `capital_discipline` had *just* been restored to the live scoring path
from free SEC XBRL company facts -- the adoption that closed vintage 2 and opened vintage 3 --
so it was not dormant. And `factors.py:265` computes it as `df[["z_neg_issuance"]].mean(axis=1)`:
**issuance only**. Asset growth was deliberately removed from the theme, because it was
cancelling out the one input that works, and the legend never caught up.

That is the same class of defect as the stale figures in `settings.BOOK_CONFIGS`: copy that
describes the model, living somewhere the model cannot reach, going quietly out of date. The
BARS were never the problem -- `_themeBars` enumerates whatever weights the payload carries, so
the fifth theme appeared on its own the moment it had a weight. It was the SENTENCE UNDER THE
BAR that lied, which is worse than a missing bar: a missing bar invites a question, and a
confident caption closes one.

ONE SOURCE, AND IT IS THE PYTHON SIDE
-------------------------------------
Same convention as `score_confidence.py` and `hold_horizon.py`: the strings live here, get
injected into the page as `window.THEME_STATUS`, and `app.js` escapes them without rewording.
`tests/test_theme_status.py` fails if a theme carries weight while claiming to be dormant, if
a theme claimed live is one the fidelity gate rejected, or if this module and
`settings.FACTORS_ALL` stop describing the same set of themes.

WHY `dormant` IS NOT DERIVED FROM A LIVE SCAN
---------------------------------------------
It could be -- `screen.py` already ships `health.theme_contributing`, which measures what
survives standardization -- and that number IS what the scan-health warning uses. It is the
right instrument for "did this theme move TODAY'S scan" and the wrong one for a legend, because
a theme can be absent from one cross-section for an ordinary reason (a bad day at SEC's
endpoint, which `issuance.py` deliberately fails to `None` for) without being dormant as a
matter of design. The legend states the DESIGN; the health block states the DAY. Conflating
them would make a transient outage read as a retired theme.

NOTHING HERE IS A PERFORMANCE CLAIM. These are descriptions of inputs and wiring. The Spearman
figures quoted in the dormancy reasons are fidelity measurements from
`PREREG_theme_restoration.md` -- how closely a live column reproduces the panel's own ranking --
and are NOT evidence about returns.
"""
from __future__ import annotations

from typing import Dict

#: theme -> (inputs, dormant_reason or "")
#:
#: `inputs` must name what `valuation/screener/factors.py` actually averages -- not what the
#: theme was originally designed to average. A dormant reason is shown to the reader verbatim,
#: so it says WHY, never just "no data".
THEMES: Dict[str, Dict[str, str]] = {
    "value": {
        "inputs": "earnings yield · FCF yield · EBIT/EV · sales multiples · book-to-price",
        "dormant": "",
    },
    "quality": {
        "inputs": ("ROIC · ROE · margins · low leverage · gross profitability · FCF margin · "
                   "accruals · interest coverage"),
        "dormant": "",
    },
    "growth": {
        "inputs": "revenue growth · growth acceleration",
        "dormant": "",
    },
    "momentum": {
        "inputs": "12-1 return · 6-1 return · 52-week-high proximity",
        "dormant": "",
    },
    "low_risk": {
        "inputs": "low beta · low realized volatility",
        # Not dormant for want of data -- it is switched off on evidence, which is a different
        # statement and the reader deserves the difference.
        "dormant": "carries no weight — zeroed on a held-out test, not for lack of data",
    },
    "capital_discipline": {
        # RESTORED 2026-08-11. Issuance ONLY: asset growth was dropped from this theme because
        # it was cancelling out neg_issuance, the one input in it that works (factors.py:262).
        "inputs": "low share issuance",
        "dormant": "",
    },
    "sentiment": {
        "inputs": "estimate revisions · analyst rating actions",
        "dormant": "no point-in-time source — estimate revisions need IBES/WRDS",
    },
    "size": {
        "inputs": "small-cap tilt",
        "dormant": "",
    },
    # CORRECTED 2026-08-11 BY FIDELITY-2, AND THIS FILE IS USER-FACING SO THE CORRECTION IS NOT
    # COSMETIC. Both entries below said "deliberately not wired" and quoted the FAILING
    # Spearmans (+0.36, +0.17). That was true when written and is now false: both themes were
    # rebuilt to the panel's own definitions and cleared the SAME 0.60 gate at +0.8726 and
    # +0.9190, and both are wired. `insider` in particular is no longer "a constant" -- it was
    # the constant 0.0 that `factors.py:284` writes when `insider_score` is absent, and it now
    # carries real cross-sectional variation.
    #
    # Recorded as a comment rather than silently deleted: the dormancy claim was CORRECT when
    # written, and why it stopped being correct is the useful part.
    "insider": {
        "inputs": "cluster insider buying",
        "dormant": "",
    },
    "institutional": {
        "inputs": "13F institutional accumulation · holder breadth",
        "dormant": "",
    },
}


def counts(contributing: Dict[str, float] = None, floor: float = 0.05) -> dict:
    """The one place that answers "how many themes does the live ranking run on".

    THE CONTRADICTION THIS RESOLVES, and both sides of it were TRUE. `THEMES` reported `insider`
    and `institutional` as NOT dormant -- correct, they are **wired**, which is what FIDELITY-2
    delivered -- while the live scan reported `theme_contributing` **0.0** for both, because the
    theme cache never reached a production scan. And the `/methodology` copy said *"five of the
    backtest's seven themes"*, which is a third statement: a claim about what the ranking
    **runs on today**, which is neither "wired" nor "carries weight".

    So this does NOT collapse the two into one flag. It names them:

      * `weighted`  -- carries non-zero weight in the deployed composite. A property of the
        DESIGN, and the denominator the copy's "of seven" refers to.
      * `dormant`   -- declared dormant here. Also the DESIGN, and deliberately NOT derived from
        a scan: this module's own docstring gives the reason, that a theme absent from one
        cross-section for an ordinary reason (a bad day at SEC's endpoint) is not retired.
      * `contributing_now` -- actually moved the latest scan, from `health.theme_contributing`.
        A property of the DAY.

    **The copy reads `contributing_now`, because that is what it claims.** A legend saying
    "runs on five" while the scan contributes seven would be wrong in the other direction the
    moment the cache lands, which is exactly why it must not be a literal.

    `contributing` is PASSED IN rather than fetched, so this module stays pure and the caller --
    which already holds the scan health -- cannot end up reading a different scan from the one
    it is rendering beside.
    """
    # THE DEPLOYED SEVEN, IMPORTED (B7) -- never the union of the two bucket weight sets.
    #
    # A first cut unioned `WEIGHTS_ESTABLISHED` and `WEIGHTS_SPECULATIVE` and got **EIGHT**,
    # because `growth` carries weight in the speculative bucket only. That is the same
    # MEMBERSHIP difference session 67 measured -- established blends `quality`, speculative
    # blends `growth` -- and it means the union is not the set the record was built on. The
    # copy's "of seven" refers to the DEPLOYED composite, which is `FLAT_SEVEN`, and importing
    # it keeps one definition rather than two that drift the day a weight changes.
    from ..edge.valquo_index import FLAT_SEVEN
    weighted = sorted(k for k in FLAT_SEVEN if k in THEMES)
    dormant = sorted(k for k, v in THEMES.items() if v.get("dormant"))
    out = {
        "weighted": weighted,
        "n_weighted": len(weighted),
        "dormant": dormant,
        "n_dormant": len(dormant),
        "contributing_now": None,
        "n_contributing_now": None,
        "not_contributing_now": None,
        # THE SHORTFALL COUNT IS AN EXPLICIT KEY, NOT A TEMPLATE SUBTRACTION. A template reading
        # an absent attribute gets Jinja's Undefined, which is FALSY -- so
        # `{% if theme_counts.n_not_contributing_now %}` would have quietly taken the else branch
        # and told a reader ALL SEVEN themes reach a live score on a day when two do not. Fail
        # open, on the one sentence the page exists to be honest about.
        "n_not_contributing_now": None,
        "basis": ("`weighted` and `dormant` are the DESIGN; `contributing_now` is the DAY, from "
                  "the latest scan's own health block. They are reported separately because a "
                  "theme can be wired and carry weight and still not have moved today."),
    }
    if contributing is None:
        return out
    live = sorted(k for k in weighted
                  if float(contributing.get(k) or 0.0) >= floor)
    out["contributing_now"] = live
    out["n_contributing_now"] = len(live)
    out["not_contributing_now"] = sorted(set(weighted) - set(live))
    out["n_not_contributing_now"] = len(out["not_contributing_now"])
    return out


def sentence(contributing: Dict[str, float] = None) -> str:
    """The `/methodology` sentence, DERIVED. Never a literal.

    It has already been wrong twice in opposite directions -- "nine themes" while five were
    live, then "five of seven" which will be wrong the day the theme cache lands. A number in
    prose about a system that changes is a number that will be wrong.
    """
    c = counts(contributing)
    n7 = c["n_weighted"]
    if c["n_contributing_now"] is None:
        return ("The live ranking runs on the backtest's %d weighted themes; today's "
                "contribution is not available on this page." % n7)
    n = c["n_contributing_now"]
    if n >= n7:
        return ("The live ranking runs on all %d of the backtest's weighted themes." % n7)
    missing = c["not_contributing_now"]
    pretty = [m.replace("_", " ") for m in missing]
    listed = (pretty[0] if len(pretty) == 1
              else " and ".join(pretty) if len(pretty) == 2
              else ", ".join(pretty[:-1]) + " and " + pretty[-1])
    verb = "contributed" if len(pretty) > 1 else "contributed"
    return ("The live ranking runs on %d of the backtest's %d weighted themes: %s %s nothing "
            "to the latest scan, so that weight is shared among the rest."
            % (n, n7, listed, verb))


def payload() -> Dict[str, Dict[str, str]]:
    """The dict injected as `window.THEME_STATUS`. Plain data, safe to serialise."""
    return {k: dict(v) for k, v in THEMES.items()}
