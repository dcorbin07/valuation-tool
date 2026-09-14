"""THE BACKTESTED CARD — one book per config, every benchmark named, tax stated.

WHAT THIS REPLACES. The card printed a single figure labelled **"Alpha / yr"** with no
benchmark named, read from `settings.BOOK_CONFIGS[...]["measured"]`. That number is an excess
over the EQUAL-WEIGHTED universe -- uninvestable, and charged zero trading cost while the
strategy pays -- and the same settings block carries a `cost_drag_ann` its own comment records
as a pre-B6 figure never re-measured.

**AND THE FIRST FIX MIXED BOOKS, WHICH IS WHY THERE IS A SECOND.** Version 1 published one
book -- the roth top-25 -- while the page's Sharpe and turnover followed the dropdown. Selecting
"taxable" showed the top-25 book's gross return beside the decile's after-tax Sharpe and the
decile's turnover: three objects, one card. Every figure now comes from ONE
`turnover_and_costs`/`after_tax_backtest` pair per config, gated on reproducing that config's
published block before the artifact is written.

**TAXABLE NET IS NOT ROTH NET, AND THE GAP IS NOT SMALL.** A tax-advantaged account pays costs
and no tax. A taxable account pays both, and on this book the tax drag is roughly three times
the cost drag -- so the net excess over SPY falls from about +13.6pp to about +4.5pp, and over
SPMO from about +15.6pp to about +1.5pp. One word, "net", over two quantities that differ by
nine points a year is not a labelling nicety.

**THE BENCHMARK IS TAXED THE SAME WAY OR THE COMPARISON IS RIGGED.** In taxable mode SPY and
SPMO are charged the qualified-dividend rate on their dividends, with capital gains treated as
DEFERRED, because a buy-and-hold index fund realises almost nothing. That asymmetry is real
rather than a convenience, and the card says so: comparing an after-tax strategy against an
untaxed index would hand the strategy the whole of the index's tax bill.

**FAIL CLOSED.** A missing, unparseable, wrong-schema or internally impossible card makes the
section disappear. A performance card that renders half its lines is worse than one that
renders none, because the half that renders is the half that flatters.
"""
from __future__ import annotations

import json
import os
from typing import Optional

SCHEMA = "backtest_card/2"

_HERE = os.path.dirname(os.path.abspath(__file__))
CARD_PATH = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "data_export",
                         "backtest_card.json")

#: A benchmark name is part of the LABEL, never a footnote: the row is what survives being
#: screenshotted, and "Alpha / yr" with the benchmark in a caption underneath is how the old
#: card came to be unreadable.
LABELS = {"gross": "Gross return / yr",
          "vs_spy": "vs SPY / yr",
          "vs_spmo": "vs SPMO / yr"}

#: The net line names its own basis, because the two modes are different quantities.
NET_LABEL = {"after costs": "Net return / yr, after costs",
             "after costs and taxes": "Net return / yr, after costs and taxes"}

CAPTION_COMMON = ("Gross and net are both stated. In-sample and hypothetical: 18 years of "
                  "point-in-time history that the model was also tuned on, so this is not a "
                  "return anyone received and not a forecast.")

CAPTION_TAXED = (" Net charges the measured market-cap cost model AND lot-level FIFO tax at "
                 "40.8% short-term / 23.8% long-term. SPY and SPMO are charged the qualified "
                 "dividend rate on their dividends, with capital gains treated as DEFERRED - "
                 "a held index fund realises almost nothing - so the benchmark's tax bill is "
                 "genuinely smaller, and this comparison does not pretend otherwise.")

CAPTION_UNTAXED = (" Net charges the measured market-cap cost model and no tax, which is what "
                   "a tax-advantaged account pays. The benchmarks are untaxed for the same "
                   "reason, so both sides are on one basis.")

#: B17. Carried verbatim rather than paraphrased. It describes the `portfolio` block, which is
#: deliberately NOT this card's basis -- see `basis_note`.
B17_WARNING = ("realised book size is ~exit_rank, NOT top_n; gross of costs and taxes unlike "
               "every other book in this file (audit B17)")


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


def card(config: str = "roth", path: str = None) -> dict:
    """The rendered payload FOR ONE CONFIG. `available` false means render nothing at all."""
    raw = load(path)
    if not raw:
        return {"available": False, "reason": "no readable card"}
    book = ((raw.get("books") or {}).get((config or "roth").lower()))
    if not book:
        return {"available": False, "reason": "no card for config %r" % config}

    full, part = book.get("full") or {}, book.get("partial") or {}
    g, n, spy = _num(full.get("gross_ann")), _num(full.get("net_ann")), _num(full.get("spy_ann"))
    if g is None or n is None or spy is None:
        return {"available": False, "reason": "the full-window figures are incomplete"}
    # Net above gross means the cost/tax model was not applied, or applied backwards. That is
    # not a figure to render with a caveat -- it is a broken card.
    if n > g:
        return {"available": False, "reason": "net exceeds gross"}

    net_means = book.get("net_means") or "after costs"
    taxed = net_means == "after costs and taxes"

    lines = [
        {"key": "gross", "label": LABELS["gross"], "value": g, "benchmark": None,
         "kind": "level"},
        {"key": "net", "label": NET_LABEL.get(net_means, "Net return / yr"), "value": n,
         "benchmark": None, "kind": "level", "net_means": net_means},
        {"key": "vs_spy", "label": LABELS["vs_spy"], "benchmark": "SPY", "kind": "excess",
         "gross": _num(full.get("vs_spy_gross")), "net": _num(full.get("vs_spy_net")),
         "window": "full", "benchmark_taxed": taxed},
    ]

    pg, pn = _num(part.get("vs_spmo_gross")), _num(part.get("vs_spmo_net"))
    if pg is not None and pn is not None:
        lines.append({"key": "vs_spmo", "label": LABELS["vs_spmo"], "benchmark": "SPMO",
                      "kind": "excess", "gross": pg, "net": pn, "window": "partial",
                      "window_label": "partial window, since SPMO inception",
                      "since": part.get("since"), "benchmark_taxed": taxed,
                      "matched_spy_gross": _num(part.get("vs_spy_gross")),
                      "matched_spy_net": _num(part.get("vs_spy_net"))})

    out = {"available": True, "config": (config or "roth").lower(), "lines": lines,
           "mode": book.get("mode"), "net_means": net_means,
           "caption": CAPTION_COMMON + (CAPTION_TAXED if taxed else CAPTION_UNTAXED),
           "partial_note": (
               "Partial window, since SPMO inception - SPMO listed 2015-10-09, so the book is "
               "re-scored over that window rather than compared across different spans. The "
               "SPY excess for the same window is shown beside it, because the book earned "
               "more in this window than over the full history and the two excesses are only "
               "comparable on the same span."),
           "basis": book.get("basis"), "benchmark_basis": book.get("benchmark_basis"),
           "basis_note": (
               "Every figure here - gross, net, Sharpe, turnover and both excesses - is the "
               "SAME book, the one this dropdown selected, recomputed from the banked panel "
               "with that config's own settings. It is NOT the `portfolio` block, which holds "
               "~42 names through a hysteresis band and is gross of costs and taxes: that "
               "block's own warning reads “" + B17_WARNING + "”."),
           "b17_label_warning": B17_WARNING,
           "sharpe": _num(full.get("sharpe")),
           "annual_turnover": _num(full.get("annual_turnover")),
           "cost_drag_ann": _num(full.get("cost_drag_ann")),
           "tax_drag_ann": _num(full.get("tax_drag_ann")),
           "spy_untaxed_ann": _num(full.get("spy_untaxed_ann")),
           "full_window": {"first": full.get("first_date"), "last": full.get("last_date"),
                           "n_periods": full.get("n_periods")},
           "spmo_available": pg is not None,
           "sha256": raw.get("sha256"), "generated_at_utc": raw.get("generated_at_utc")}

    band = book.get("band") or {}
    if band.get("stale_settings_note"):
        out["band_note"] = band["stale_settings_note"]
    if band:
        out["band"] = band
    return out


def unlabelled_excesses(payload: dict) -> list:
    """Every excess line that does NOT name a benchmark. Must always be empty."""
    bad = []
    for ln in (payload or {}).get("lines") or []:
        if ln.get("kind") != "excess":
            continue
        bm = (ln.get("benchmark") or "").strip()
        if not bm or bm not in (ln.get("label") or ""):
            bad.append(ln.get("key") or "?")
    return bad


def untaxed_benchmark_against_taxed_book(payload: dict) -> list:
    """Excess lines comparing an AFTER-TAX book against an UNTAXED benchmark.

    The one comparison this card may never make silently. It is checked as a property of the
    payload rather than trusted to the builder, because it is the failure that would flatter
    the strategy by the whole of the benchmark's tax bill and would look entirely normal.
    """
    p = payload or {}
    if (p.get("net_means") or "") != "after costs and taxes":
        return []
    return [ln.get("key") or "?" for ln in (p.get("lines") or [])
            if ln.get("kind") == "excess" and not ln.get("benchmark_taxed")]
