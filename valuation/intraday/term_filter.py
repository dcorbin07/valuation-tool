"""
Live term-structure filter — the one signal that survived phase 3b's fade gate.

--------------------------------------------------------------------------------------------
WHAT IT DOES AND WHY IT IS ON.

`term_slope` = (ATM IV of the ~60-DTE expiry) - (ATM IV of the front expiry). Positive is
contango, the calm default. Negative is backwardation: the market is pricing near-term stress or
a pending event, which is a poor moment to pay up for a 45-75 day call.

Measured on 1,540 backtested scream-buy trades, judged ONLY on the fading 2021-2025 half with the
threshold fitted on 2016-2020:

    late-half expectancy   +4.76%  ->  +12.88%   (+8.12pp)
    losing years           2022 -11.41% -> +19.78% ; 2023 -4.61% -> +7.30%
    but                    2025  -0.05% ->  -5.90%

It is robust rather than a tuned cutoff: over a 3x range of the threshold the gain stays between
+7.7pp and +9.0pp.

--------------------------------------------------------------------------------------------
THREE THINGS THIS DELIBERATELY DOES NOT DO.

1. CORRECTED 2026-08-02 - IT NOW DOES DELETE ALERTS BY DEFAULT. This paragraph used to say the
   opposite, and the reason it said so still stands on its own terms: discarding ~60% of signals
   is a large product change that should be chosen deliberately rather than inherited from a
   backtest. It has now been chosen deliberately (roadmap #21), on the grounds that a filter
   which is the single thing arresting the fade is worth nothing if the live path shows the
   alerts it would have removed. DEFAULT_MODE is therefore MODE_SUPPRESS, and MODE_FLAG remains
   one config value away for anyone who wants the annotated-but-complete list.

   Because this is now a gate rather than a label, the live retention rate is logged and
   compared against the backtested 40.6% - see `options_live.term_filter_stats`. The threshold
   was fitted on IV solved from the mid by bisection; a broker publishes its own smoothed
   surface, and ~1 vol point is a small enough threshold that the two need not agree.

2. IT DOES NOT FAIL CLOSED ON MISSING DATA. If the chain does not yield both IVs, `term_ok` is
   None - unknown, not bad. Suppressing alerts because a quote feed hiccuped would convert a
   data outage into a silent trading halt, which is far worse than showing an unfiltered alert.

3. IT DOES NOT CLAIM TO FIX THE FADE. It repaired two of the three losing years and made the
   third worse, and it helps six of ten years overall. It is a real filter, not a cure, and the
   `reason` strings say "contango"/"backwardation" rather than anything implying a forecast.

SIZING INTERACTION, which matters more than the filter itself: because ~60% of alerts fall on
the wrong side, a book that keeps position size constant while trading 40% as often deploys far
less capital. `size_multiplier` therefore returns a LARGER multiple for contango alerts, so the
sleeve's total exposure is roughly preserved rather than silently shrinking by 60%. It is capped,
because "trade less often but much bigger" is how a modest edge becomes a concentrated bet.
"""
from __future__ import annotations

from typing import Optional

# Fitted on 2016-2020 profitable trades; applied unchanged to 2021-2025. See options_signals_v2.
TERM_SLOPE_THRESHOLD = 0.0105

MODE_OFF = "off"            # compute nothing, behave exactly as before
MODE_FLAG = "flag"          # annotate every alert, suppress none
MODE_SUPPRESS = "suppress"  # drop backwardation alerts entirely  (DEFAULT since roadmap #21)
DEFAULT_MODE = MODE_SUPPRESS

# Contango alerts carry more of the book because ~60% of signals are filtered out. Capped so a
# fading edge cannot turn into a concentrated bet.
SIZE_MULT_CONTANGO = 1.5
SIZE_MULT_BACKWARDATION = 0.5
SIZE_MULT_UNKNOWN = 1.0


def term_slope(summary: Optional[dict]) -> Optional[float]:
    """(~60-DTE ATM IV) - (front ATM IV). None when either leg is unavailable."""
    if not summary:
        return None
    front = summary.get("atm_iv")
    mid = summary.get("atm_iv_60d")
    try:
        f, m = float(front), float(mid)
    except (TypeError, ValueError):
        return None
    if f != f or m != m or f <= 0 or m <= 0:
        return None
    return m - f


def classify(summary: Optional[dict], threshold: float = TERM_SLOPE_THRESHOLD) -> dict:
    """{term_slope, term_ok, reason}. term_ok is None when unknown - never False on missing data."""
    ts = term_slope(summary)
    if ts is None:
        return {"term_slope": None, "term_ok": None,
                "reason": "term structure unavailable"}
    ok = ts >= threshold
    return {"term_slope": ts, "term_ok": bool(ok),
            "reason": (f"contango (+{ts:.3f})" if ok else f"backwardation ({ts:+.3f})")}


def size_multiplier(term_ok: Optional[bool]) -> float:
    """Preserve sleeve exposure when the filter removes ~60% of alerts. Capped deliberately."""
    if term_ok is None:
        return SIZE_MULT_UNKNOWN
    return SIZE_MULT_CONTANGO if term_ok else SIZE_MULT_BACKWARDATION


def apply(rows, mode: str = DEFAULT_MODE, threshold: float = TERM_SLOPE_THRESHOLD) -> list:
    """Annotate (and optionally filter) live scan rows. Unknown term structure is never dropped."""
    return apply_with_stats(rows, mode, threshold)[0]


def apply_with_stats(rows, mode: str = DEFAULT_MODE,
                     threshold: float = TERM_SLOPE_THRESHOLD):
    """`apply`, plus what it did. Returns (rows, stats).

    The counts are not decoration. Now that the default is to SUPPRESS, the discard rate is the
    only way to notice that a threshold fitted on one IV estimator did not transfer to another:
    the backtest kept 40.6% of alerts, so a live retention of 5% or 95% means the live filter is
    not the filter that was tested.
    """
    stats = {"mode": mode, "threshold": threshold, "n_in": len(rows or []),
             "kept": 0, "discarded": 0, "unknown": 0}
    if mode == MODE_OFF:
        stats["n_out"] = stats["n_in"]
        return list(rows or []), stats
    out = []
    for r in rows or []:
        detail = r.get("detail") or {}
        summary = {"atm_iv": detail.get("opt_atm_iv"),
                   "atm_iv_60d": detail.get("opt_atm_iv_60d")}
        c = classify(summary, threshold)
        if c["term_ok"] is True:
            stats["kept"] += 1
        elif c["term_ok"] is False:
            stats["discarded"] += 1
        else:
            stats["unknown"] += 1
        r = {**r, **c, "size_multiplier": size_multiplier(c["term_ok"])}
        if mode == MODE_SUPPRESS and c["term_ok"] is False:
            continue
        out.append(r)
    known = stats["kept"] + stats["discarded"]
    stats["retention"] = (stats["kept"] / known) if known else None
    stats["n_out"] = len(out)
    return out, stats
