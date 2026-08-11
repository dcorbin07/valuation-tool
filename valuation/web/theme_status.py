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
    "insider": {
        "inputs": "cluster insider buying",
        # Weighted at 0.125 and contributing NOTHING: the live column is a constant, which
        # standardizes to all-NaN and renormalises away. Saying so is the whole point -- this
        # is the theme that hid in plain sight behind 100% "coverage".
        "dormant": ("Form 4 window does not reproduce the panel's ranking "
                    "(Spearman +0.36 against a 0.60 gate) — deliberately not wired"),
    },
    "institutional": {
        "inputs": "13F institutional accumulation · holder breadth",
        "dormant": ("13F source does not reproduce the panel's ranking "
                    "(Spearman +0.17 against a 0.60 gate) — deliberately not wired"),
    },
}


def payload() -> Dict[str, Dict[str, str]]:
    """The dict injected as `window.THEME_STATUS`. Plain data, safe to serialise."""
    return {k: dict(v) for k, v in THEMES.items()}
