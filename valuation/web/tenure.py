"""
MA30 — TENURE ON THE HOT LIST. How many recent scans in a row a name has held the top decile.

WHY IT IS WORTH SHOWING. A ranked list refreshed daily invites exactly one wrong inference:
that the names on it are a stable set the model keeps choosing. `S22` measured the opposite
on the backtest panel — the Kaplan-Meier median spell in the top decile is **ONE rebalance**,
70.6% of spells last exactly one, and re-entry is the norm rather than the exception. So the
single most misleading thing about the hot list is invisible on it, and churn is the honest
disclosure this module exists to make.

THE CLAIM IT MUST NEVER MAKE, AND THE REASON IS SPECIFIC. Nothing here says a long-tenured
name is a better name. `S22` measured a term structure of the SIGNAL — the alpha earned by a
cohort selected on ONE date, still accruing at two years — and **not** a term structure of
TENURE. No arm in this project has ever tested tenure as a predictor. The two are easy to
conflate and they are different objects: "the edge persists after selection" and "names that
keep being selected are better" are separate claims, and only the first is measured. `BANNED`
below enumerates the wordings that would assert the second, and `violations()` is asserted
against the RENDERED payload rather than against this file, because rendering is where copy
leaks (the `dip_posture.py` precedent, carried forward on the record's own recommendation).

A REGISTER IS REQUIRED THE MOMENT ANYONE SORTS OR FILTERS BY IT. Displaying tenure discloses
churn; ranking on it, filtering on it, or feeding it into a score converts a disclosure into
a SCREEN — a new selection rule, needing the both-halves gate like any other. That is not a
style preference: a screen chosen after seeing which tenure looks good is the in-sample
selection this project has already paid for twice. `tests/test_tenure.py` fails if the field
is ever used as a sort key or a filter predicate, so the constraint outlives this docstring.

WHAT IT COSTS: zero trials, because it measures no hypothesis and clears no threshold. It
reports a count.

WHAT HAS NEVER BEEN SEEN, STATED PLAINLY. The arithmetic is pinned against fixtures, and the
NUMBERS it will show have not been observed anywhere: the store in this checkout holds ONE
scan, dated 2099-01-01 with provider "ci" — a test artefact — and the local scan archive holds
one real day of eight. The scan history lives on the live service. So this module is verified
as a computation and unverified as a description of the live book, and the first real reading
will be the first real reading.

THE DECILE IS TAKEN OVER THE SCAN, NOT OVER WHAT THE VIEWER ASKED FOR. `?top=` is a display
cap and differs per tier, so measuring membership against it would give the SAME name a
different tenure for a free reader and a paying one. `scored` on the scan row is the
denominator, and a scan that did not record its own size is skipped as UNKNOWN rather than
being treated as empty — a missing denominator must not read as "everybody qualified".
"""
from __future__ import annotations

import math
from typing import Optional

#: How far back to look. Bounded because this runs inside a public request; a name at the cap
#: reports `capped: True` rather than a number that silently means "at least this many".
LOOKBACK_SCANS = 20

#: What counts as "on the hot list" for this purpose: the top tenth of the ranked scan. The
#: same fraction the Index construction uses for its own tier, so the disclosure and the book
#: describe the same slice rather than two nearby ones.
DECILE_FRACTION = 0.10

#: The calibrated wording. One module owns it and a test pins it verbatim — the `V3` /
#: `score_confidence.py` rule, because copy that lives in a template drifts silently.
LABEL = "Scans in a row in the top 10%"

EXPLAINER = (
    "How many of the most recent scans in a row this name has been in the top 10% of the "
    "ranking. It is here to show how much the list CHURNS: on the backtest panel the typical "
    "name held the top decile for a single rebalance. It is not a measure of quality or "
    "conviction, and this project has never tested whether names that stay longer do better."
)

#: Wordings that would turn the disclosure into the claim it must not make. Checked against
#: the rendered payload, lower-cased, substring — deliberately blunt, since a near-miss here
#: costs a user a false inference and a false positive costs an author one edit.
BANNED = (
    "high conviction",
    "conviction pick",
    "the longer the better",
    "longer is better",
    "proven performer",
    "consistent performer",
    "staying power",
    "has held up",
    "track record of",
    "reliable pick",
    "best names",
    "buy the",
)


def violations(text: str) -> list:
    """Which banned phrases a rendered string contains. Empty is the only passing answer."""
    low = (text or "").lower()
    return [p for p in BANNED if p in low]


def decile_cutoff(scored) -> Optional[int]:
    """Rank at or below which a name is in the top decile of a scan of `scored` names.

    `None` when the scan did not record its size — the caller must then skip that scan, not
    count it as a miss. A miss and an unknown break a streak differently: a miss ENDS it,
    an unknown means we cannot say, and conflating them would under-report tenure on exactly
    the older scans whose metadata is thinnest.
    """
    try:
        n = int(scored)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    return max(1, int(math.ceil(n * DECILE_FRACTION)))


def streaks(history, tickers=None) -> dict:
    """`{ticker: {"scans": n, "capped": bool}}` from `Store.recent_ranks()` output.

    `history` is newest-first `(scan_date, scored, {ticker: rank})`. The streak is counted
    from the newest scan backwards and stops at the first scan where the name was ranked and
    OUTSIDE the decile, or was absent from the scan entirely — absence is a genuine miss,
    since a name the scan scored and did not rank highly and a name the scan did not reach
    are both "not on the list that day".

    A scan with no usable denominator is SKIPPED, not counted either way, so it neither
    extends nor breaks a streak.
    """
    usable = [(d, decile_cutoff(s), r) for d, s, r in (history or [])]
    usable = [(d, c, r) for d, c, r in usable if c is not None]
    if tickers is None:
        tickers = set()
        for _, _, r in usable:
            tickers.update(r)
    out = {}
    for t in tickers:
        n = 0
        for _, cut, ranks in usable:
            rk = ranks.get(t)
            if rk is None or rk > cut:
                break
            n += 1
        out[t] = {"scans": n, "capped": bool(n and n >= len(usable) >= LOOKBACK_SCANS)}
    return out


def annotate(rows, store, lookback: int = LOOKBACK_SCANS) -> dict:
    """Attach `tenure_scans` to each row and return the block describing what it means.

    ADDITIVE AND FAIL-SOFT. A store that cannot answer leaves the rows untouched and returns
    `available: False` — a display disclosure must never be able to fail a scan render, and a
    missing count is honestly missing rather than defaulted to 1, which would read as "new
    today" for every name on the list.

    It does NOT reorder `rows`, and nothing here filters them. See the module docstring: that
    is the line between disclosing churn and screening on it, and `tests/test_tenure.py`
    holds it.
    """
    block = {"available": False, "label": LABEL, "explainer": EXPLAINER,
             "lookback_scans": int(lookback), "scans_available": 0,
             "decile_fraction": DECILE_FRACTION}
    try:
        history = store.recent_ranks(lookback)
    except Exception:                                        # noqa: BLE001
        return block
    usable = [h for h in history if decile_cutoff(h[1]) is not None]
    block["scans_available"] = len(usable)
    if not usable:
        return block
    st = streaks(history, {r.get("ticker") for r in (rows or []) if r.get("ticker")})
    for r in rows or []:
        s = st.get(r.get("ticker"))
        if s is not None:
            r["tenure_scans"] = s["scans"]
            if s["capped"]:
                r["tenure_capped"] = True
    block["available"] = True
    return block
