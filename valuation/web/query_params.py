"""One clamp for every caller-supplied row limit. [MA50]

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
"""
from __future__ import annotations

__all__ = ["clamp_int"]


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
