"""One clamp for every caller-supplied NUMBER. [MA50, extended by MA53]

WHY THIS MODULE EXISTS
----------------------
`/api/hotstocks?top=-1` defeated the per-tier paywall. The route read

    top = min(int(request.args.get("top", 100)), cap)

and `min(-1, 500)` is `-1`. That value reached `store.load_snapshot`, which builds
`q += f" LIMIT {int(top)}"`, and **SQLite treats `LIMIT -1` as no limit at all** — so a
negative `top` returned the entire snapshot instead of the tier's cap. The cap
(`g.hotstocks_cap`, free 10 / premium 500) *is* the paywall. It was masked in production only
because `OPEN_ACCESS=true` makes everyone premium; the moment that flag flips, an anonymous
visitor asking for `top=-1` gets the full list.

`min(x, cap)` bounds a value from ABOVE and says nothing about the floor. That is the whole
bug, and it is not specific to one route — the same one-sided clamp appeared at five call
sites in two blueprints, written independently each time. Hence one function: a second
hand-rolled clamp is how the first one gets fixed and the others do not (audit B7's defect
class — three composite functions, one repair).

WHAT IT GUARANTEES
------------------
The return value is always an `int` in `[floor, cap]`. There is no input — negative, zero,
absurd, fractional, empty, missing, or non-numeric — for which it returns something outside
that range or raises. `int("abc")` raising a `ValueError` into a Flask view is a 500 on a
public endpoint, which is its own small gift to a prober, so garbage degrades to the default
rather than to a traceback.

The arithmetic is the audit's own prescribed remedy — `min(max(1, int(...)), cap)` — and not a
variation on it. The one thing added is the parse guard, because the registered fix still
raises on `top=abc`. A negative therefore comes back as the FLOOR (1), not as the cap: asking
for minus one row is a probe or a typo, and answering it with the largest page the tier allows
would be a strange way to fix a bug about pages being too large.

MA53 EXTENDED IT TO FLOATS, AND FLOATS ARE WORSE
------------------------------------------------
Sweeping for the same class found one survivor that `clamp_int` could never have covered:
`/api/options-alerts?risk_budget=` is parsed with a bare `float(...)`. `float` accepts three
strings `int` rejects — `"nan"`, `"inf"`, `"-inf"` — so that parameter had no defence at all,
not even the accidental one of raising. A NaN risk budget does not raise, does not log, and
does not stop: it propagates silently through position sizing, and every comparison against it
is False, so the guards downstream read as satisfied. That is strictly worse than a 500.

The endpoint is owner-only, so this is not a paywall or a public hole — it is reported and
fixed as the same class rather than left because its blast radius is small.
"""
from __future__ import annotations

import math

__all__ = ["clamp_int", "clamp_float"]


def clamp_int(raw, default: int, cap: int, floor: int = 1) -> int:
    """Coerce a caller-supplied row count into `[floor, cap]`.

    `raw` is whatever `request.args.get(...)` handed back: a string, None, or already an int.
    `default` is used when `raw` is absent or unparseable. `cap` is the ceiling the caller is
    entitled to (a per-tier cap, or a fixed ceiling on an owner-only route).

    `floor` is 1 rather than 0 deliberately: every caller here feeds a SQL `LIMIT` or an
    equivalent slice, and `LIMIT 0` is a silently empty page rather than an error. Asking for
    nothing is far more likely to be a typo or a probe than a request, so it reads as one.

    Note the order — bound by the cap FIRST, then raise to the floor — so the floor can never
    lift a caller above the ceiling their tier allows. With a cap of 0 that ordering is what
    makes the result 0 rather than 1.
    """
    try:
        val = int(raw)
    except (TypeError, ValueError):
        val = int(default)
    cap = int(cap)
    if cap < floor:
        # A cap below the floor is a configuration error, not a caller's doing. The cap wins:
        # it is the entitlement, and no floor may raise anyone above it.
        return cap
    return max(floor, min(val, cap))


def clamp_float(raw, default: float, lo: float, hi: float) -> float:
    """Coerce a caller-supplied real number into `[lo, hi]`, with NaN and infinity refused.

    The NaN check is the point of this function and is why `clamp_int`'s shape is not simply
    reused with `float` swapped in. Every comparison involving NaN is False, so `min`/`max`
    keep whichever operand they reached first — which makes a min/max clamp ORDER-DEPENDENT on
    NaN. Measured, all three natural spellings:

        max(lo, min(v, hi))  ->  lo    (this one: NaN becomes the floor, silently)
        min(max(v, lo), hi)  ->  nan   (NaN passes straight through)
        max(min(v, hi), lo)  ->  nan   (NaN passes straight through)

    So two of the three let NaN out untouched, and the third turns garbage into a
    plausible-looking minimum. None of them is a clamp. Which one a given author writes is
    arbitrary, and the two behaviours are indistinguishable in review — the same
    value-dependent-guard family as the `zscore` zero-variance check this project has already
    been bitten by twice.

    Infinity clamps correctly by comparison, so it is caught by the range rather than by the
    special case — but it is checked explicitly anyway, because a caller sending `inf` is
    saying something different from a caller sending a large number, and degrading to the
    documented default is a better answer than silently substituting the ceiling.
    """
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(val):        # NaN and +/-inf, before any comparison is trusted
        return float(default)
    return max(float(lo), min(val, float(hi)))
