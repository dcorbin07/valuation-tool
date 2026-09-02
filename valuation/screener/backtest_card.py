"""THE BACKTESTED CARD'S FOUR LINES — every one of them names its benchmark.

WHAT THIS REPLACES, AND WHY THAT MATTERED. The card printed a single figure labelled
**"Alpha / yr"** with no benchmark named, read from `settings.BOOK_CONFIGS[...]["measured"]`.
Two things were wrong with it at once. That number is `net_alpha`, which on this project means
**versus the equal-weighted universe** — an uninvestable book that is charged zero trading cost
while the strategy pays, a limitation the results file states about itself. And the same
settings block carries a `cost_drag_ann` of 0.0440 whose own comment records it as a **pre-B6
figure that was never re-measured**; the measured drag for that book is **0.0325**.

So a visitor read one number, could not tell what it was measured against, and the obvious
guess — the S&P — was the wrong one.

**FOUR LINES, ONE SERIES, EVERY BENCHMARK NAMED.** Gross return, net return, the excess over
SPY on both bases, and the excess over SPMO. They come from `data_export/backtest_card.json`,
which `scripts/backtest_card.py` derives and which is gated on reproducing the published
`costs.top_25` block bit-for-bit before it will write anything.

**THE SPMO LINE IS A PARTIAL WINDOW AND SAYS SO IN ITS OWN LABEL.** SPMO listed 2015-10-09.
The book is RE-SCORED on the panel restricted to that window rather than having its 17-year
figure set against a 10-year ETF, and the window-matched SPY excess ships beside it —
**without which the card would invite exactly one misreading**: the book earned more in the
recent window than over the full history, so a full-window SPY excess next to a partial-window
SPMO excess makes SPMO look like the easier benchmark. It is the harder one.

**FAIL CLOSED.** A missing, unparseable, wrong-schema or internally inconsistent card makes
`available` false and the whole section disappears. A performance card that renders half its
lines is worse than one that renders none, because the half that renders is the half that
flatters.
"""
from __future__ import annotations

import json
import os
from typing import Optional

SCHEMA = "backtest_card/1"

_HERE = os.path.dirname(os.path.abspath(__file__))
CARD_PATH = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "data_export",
                         "backtest_card.json")

#: Every line's label. A benchmark name is part of the LABEL, never a footnote: the row is what
#: survives being screenshotted, and "Alpha / yr" with the benchmark in a caption underneath is
#: how the old card came to be unreadable.
LABELS = {
    "gross": "Gross return / yr",
    "net": "Net return / yr, after measured costs",
    "vs_spy": "vs SPY / yr",
    "vs_spmo": "vs SPMO / yr",
}

CAPTION = ("Gross and net are both stated. In-sample and hypothetical: 18 years of "
           "point-in-time history that the model was also tuned on, so this is not a return "
           "anyone received and not a forecast. Net charges the measured market-cap cost "
           "model, not a flat assumption.")

PARTIAL_NOTE = ("Partial window, since SPMO inception — SPMO listed 2015-10-09, so the book "
                "is re-scored over that window rather than compared across different spans. "
                "The SPY excess for the same window is shown beside it, because the book "
                "earned more in this window than over the full history and the two excesses "
                "are only comparable on the same span.")

#: B17. Carried verbatim from the results file rather than paraphrased, and it applies to the
#: `portfolio` block. It is reported here because the card's basis is DELIBERATELY not that
#: block -- see `basis_note` -- and a reader comparing the two needs to know why they differ.
B17_WARNING = ("realised book size is ~exit_rank, NOT top_n; gross of costs and taxes unlike "
               "every other book in this file (audit B17)")

BASIS_NOTE = ("These four lines are the roth book — 25 names, no no-trade band — which is the "
              "only book in the results file carrying a gross AND a net figure from the same "
              "cost model on the same series. It is NOT the `portfolio` block, which holds "
              "~42 names through a hysteresis band and is gross of costs and taxes: that "
              "block's own warning reads “" + B17_WARNING + "”.")


def _num(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and abs(v) != float("inf") else None


def load(path: str = None) -> Optional[dict]:
    try:
        with open(path or CARD_PATH, encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:                                                    # noqa: BLE001
        return None
    return raw if isinstance(raw, dict) and raw.get("schema") == SCHEMA else None


def card(path: str = None) -> dict:
    """The rendered payload. `available` false means render nothing at all."""
    raw = load(path)
    if not raw:
        return {"available": False, "reason": "no readable card"}
    full, part = raw.get("full") or {}, raw.get("partial") or {}

    g, n = _num(full.get("gross_ann")), _num(full.get("net_ann"))
    spy = _num(full.get("spy_ann"))
    if g is None or n is None or spy is None:
        return {"available": False, "reason": "the full-window figures are incomplete"}
    # A net above gross means the cost model was not applied, or was applied backwards. That is
    # not a figure to render with a caveat -- it is a broken card.
    if n > g:
        return {"available": False, "reason": "net exceeds gross"}

    lines = [
        {"key": "gross", "label": LABELS["gross"], "value": g, "benchmark": None,
         "kind": "level"},
        {"key": "net", "label": LABELS["net"], "value": n, "benchmark": None, "kind": "level"},
        {"key": "vs_spy", "label": LABELS["vs_spy"], "benchmark": "SPY", "kind": "excess",
         "gross": _num(full.get("vs_spy_gross")), "net": _num(full.get("vs_spy_net")),
         "window": "full"},
    ]

    pg, pn = _num(part.get("vs_spmo_gross")), _num(part.get("vs_spmo_net"))
    if pg is not None and pn is not None:
        lines.append({"key": "vs_spmo", "label": LABELS["vs_spmo"], "benchmark": "SPMO",
                      "kind": "excess", "gross": pg, "net": pn, "window": "partial",
                      "window_label": "partial window, since SPMO inception",
                      "since": part.get("since"),
                      "matched_spy_gross": _num(part.get("vs_spy_gross")),
                      "matched_spy_net": _num(part.get("vs_spy_net"))})

    return {"available": True, "lines": lines, "caption": CAPTION,
            "partial_note": PARTIAL_NOTE, "basis": raw.get("basis"), "basis_note": BASIS_NOTE,
            "b17_label_warning": B17_WARNING,
            "full_window": {"first": full.get("first_date"), "last": full.get("last_date"),
                            "n_periods": full.get("n_periods")},
            "spmo_available": pg is not None,
            "sha256": raw.get("sha256"), "generated_at_utc": raw.get("generated_at_utc")}


def unlabelled_excesses(payload: dict) -> list:
    """Every excess line that does NOT name a benchmark. Must always be empty.

    This is the check the card exists for, so it lives beside the copy rather than only in the
    suite: an excess is a claim about a comparison, and a comparison with no named counterparty
    is not checkable by the person reading it.
    """
    bad = []
    for ln in (payload or {}).get("lines") or []:
        if ln.get("kind") != "excess":
            continue
        bm = (ln.get("benchmark") or "").strip()
        if not bm or bm not in (ln.get("label") or ""):
            bad.append(ln.get("key") or "?")
    return bad
