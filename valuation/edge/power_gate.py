"""
MB22 — the required-n / minimum-detectable-effect gate.

Ported from TIDEMARK (`scripts/p1_9_power_gate.py`, `POWER_GATE.md`), which used it to rule
its own Phase 2 **NOT PERMITTED** before running it. Register:
`PREREG_mb22_mb23_power_and_hodrick.md`. **No TIDEMARK DATA crosses — only the method**, which
is itself re-derived from the arithmetic printed in that project's charter (`MB24` marks data
flow out of scope).

WHAT THIS ADDS THAT VALQUO DID NOT HAVE
---------------------------------------
`statistics.effective_n(n, rho)` converts observations to *effective* observations, and
`options_stats.effective_n(rows, block)` does it with a design effect scored against a shuffled
null. Both answer "how much independent evidence is in this sample?". **Neither answers "how
much would I need?"** — and that second question is the one a register has to answer *before*
it runs, because afterwards the answer is contaminated by the result.

    required_n(effect)  = ((crit + z_power) / effect) ** 2
    mde_at_power(n)     = (crit + z_power) / sqrt(n)          # the same identity, inverted

THE DISTINCTION THIS MODULE EXISTS TO KEEP STRAIGHT, and Valquo has been eliding it
-----------------------------------------------------------------------------------
Two different quantities have both been called "the MDE" in this project's registers:

  * `detection_threshold(se) = crit * se` — the effect at which the POINT ESTIMATE would just
    reach the bar. A true effect of exactly this size is detected **half the time**: it is a
    50%-power figure.
  * `mde_at_power(...) = (crit + z_power) * se` — the effect that would be detected with
    probability `Phi(z_power)`, conventionally 80%.

**Every MDE this project has published is the first one.** `S19`'s +0.020549, `V2G`'s 1.8708 pp
and `V6`'s +4.177 pp are all `2.0 * se`. They are correct as stated and they are *not* 80%-power
MDEs; at `crit = 2.0` the 80%-power figure is **1.42x larger**.

That is not a criticism of those registers — `V2G` says so itself, in the only place it could:
having quoted 1.8708 pp as what the design "resolves", it goes on to compute that its power
against a true 1.95 pp gap is **55.0%**, i.e. barely more than a coin flip. `power_at()` below
reproduces that 55.0% from the same two numbers, which is what proves the two vocabularies are
about one thing. **Both are reported by `gate()`, always together, so the next register cannot
pick one by accident.**

THE CRITICAL VALUE HAS NO DEFAULT, DELIBERATELY
-----------------------------------------------
`critical_value()` requires exactly one of `n_trials` (multiplicity-corrected, via the ONE
shipped `statistics.hlz_hurdle`) or `crit` (explicit, e.g. the conventional 2.0). It refuses to
guess. **MA5's finding is that a default is precisely how the Harvey-Liu-Zhu bar froze at the
constant 3.0** — sqrt(2 ln N) at N = 90 — and stayed there while this project's N went past 90
on 2026-08-06 and on to 234. `hlz_hurdle` is IMPORTED here and never re-derived; a second copy
of that expression anywhere under `valuation/` fails a shipped test, and it would deserve to.

THE TWO "AVAILABLE N" ROUTES ARE SEPARATE FUNCTIONS AND MUST NOT VALIDATE EACH OTHER
------------------------------------------------------------------------------------
`POWER_GATE.md` 5.1 records a validation that could not be run: it asked that the
`n_overlapping / deff` bridge reproduce a charter column of "independent n", and that column is
exactly `n / h`, the count of NON-OVERLAPPING windows — a different quantity reached by an
unrelated route, sitting in the adjacent column of the same table. They look as though they
should agree and there is no theorem saying they must.

So they are `available_independent_n_from_deff` and `available_independent_n_nonoverlapping`,
with different names, and a caller has to choose one deliberately. `compare_routes()` reports
the gap and labels it **corroboration, never validation**.

WHAT THIS MODULE IS NOT
-----------------------
It is not a check that fires on anything. There is no sweep over `PREREG_*.md`, no warning, no
build failure. ~68 historical registers state no MDE in this form, so such a check would fire on
essentially all of them on its first run and be switched off inside a week — `MA21`'s precedent,
which declined a blank-verdict warning that would have fired on 41 legitimate ledger rows, and
`MB30`'s refusal. What binds instead is `RUN_RULES.md` PART A rule 11, for registers written
from now on, plus this library for them to call.
"""

from __future__ import annotations

import math
from statistics import NormalDist

from .statistics import hlz_hurdle

__all__ = [
    "Z_POWER_CONVENTION", "AMBIGUITY",
    "critical_value", "z_for_power",
    "required_n", "mde_at_power", "detection_threshold",
    "detection_threshold_from_observed", "power_at",
    "available_independent_n_from_deff", "available_independent_n_nonoverlapping",
    "compare_routes", "gate", "state",
]

_N = NormalDist()

#: The charter convention TIDEMARK's printed power table is built on. Phi^-1(0.80) is
#: 0.8416212335729143; the published table rounds it to 0.84 and reproducing that table
#: exactly (IR 0.20 -> 196, 0.30 -> 87, 0.15 -> 348) requires the rounded value. Use
#: `z_for_power(0.80)` when the exact figure is wanted; the difference is under 0.3% of a
#: required-n and is never decision-relevant at the precision these bars are quoted to.
Z_POWER_CONVENTION = 0.84

#: `POWER_GATE.md` 1: a ratio inside +/- this band resolves to NOT PERMITTED rather than to a
#: judgement call. `RUN_RULES` A6 in a new place — ambiguous against a pre-committed threshold
#: is a null, and the null here is the conservative direction.
AMBIGUITY = 0.10

_PERMITTED = "PERMITTED"
_NULL = "NULL - NOT PERMITTED"
_NOT = "NOT PERMITTED"


def z_for_power(power: float) -> float:
    """One-sided normal quantile for a target power. `z_for_power(0.80)` = 0.84162..."""
    if not 0.0 < power < 1.0:
        raise ValueError(f"power must be in (0, 1), got {power}")
    return float(_N.inv_cdf(power))


def critical_value(n_trials=None, crit=None) -> float:
    """The bar a t-statistic must clear. EXACTLY ONE of `n_trials` or `crit`, no default.

    `n_trials` routes through `statistics.hlz_hurdle` — the ONE definition of sqrt(2 ln N) in
    this project (MA5) — so a multiplicity-corrected bar moves with the trial count instead of
    freezing. `crit` is the explicit escape for the conventional 2.0 that this project's older
    registers used, and for reproducing an external table (TIDEMARK's charter prints its power
    table at 1.96).

    Refusing to default is the point. A default is how the 3.0 constant survived past N = 90.
    """
    if (n_trials is None) == (crit is None):
        raise ValueError(
            "pass exactly one of n_trials (multiplicity-corrected) or crit (explicit). "
            "There is deliberately no default: MA5 records that a default is how the "
            "Harvey-Liu-Zhu bar froze at 3.0."
        )
    if crit is not None:
        c = float(crit)
        if c <= 0:
            raise ValueError(f"crit must be positive, got {c}")
        return c
    return float(hlz_hurdle(n_trials))


def required_n(effect, n_trials=None, crit=None, z_power=Z_POWER_CONVENTION) -> float:
    """Independent observations needed to detect `effect` at `z_power` power.

    `((crit + z_power) / effect) ** 2`, with `effect` in units of one observation's standard
    deviation — an information ratio per period, a standardised mean difference, whatever the
    register's own units are. **The units of `effect` and the units of `n` must match**, which
    is the one way this is easy to get wrong: an annual IR needs `n` in YEARS.
    """
    e = abs(float(effect))
    if e <= 0:
        raise ValueError("effect must be non-zero; a zero effect needs infinite n, which is "
                         "a true statement and not a useful one")
    return float(((critical_value(n_trials, crit) + float(z_power)) / e) ** 2)


def mde_at_power(available_n, n_trials=None, crit=None, z_power=Z_POWER_CONVENTION) -> float:
    """The smallest effect detectable at `z_power` power given `available_n`.

    `(crit + z_power) / sqrt(available_n)` — algebraically `required_n` inverted, and the more
    useful direction. `POWER_GATE.md` 3.1 calls it "the honest form of the refusal": instead of
    asking whether the data reaches the bar, it asks what a strategy would have to be worth for
    the bar to be reachable, and then you can say whether that is plausible.
    """
    n = float(available_n)
    if n <= 0:
        raise ValueError(f"available_n must be positive, got {n}")
    return float((critical_value(n_trials, crit) + float(z_power)) / math.sqrt(n))


def detection_threshold(se, n_trials=None, crit=None) -> float:
    """`crit * se` — the effect at which the point estimate would just reach the bar.

    **This is a 50%-POWER figure and it is what every MDE in this project's registers so far
    actually is** (`S19` +0.020549, `V2G` 1.8708 pp, `V6` +4.177 pp, all `2.0 * se`). A true
    effect of exactly this size is detected half the time. Report it beside `mde_at_power` or
    the reader will assume the wrong one; `gate()` and `state()` do that for you.
    """
    s = float(se)
    if s <= 0:
        raise ValueError(f"se must be positive, got {s}")
    return float(critical_value(n_trials, crit) * s)


def detection_threshold_from_observed(effect, t, n_trials=None, crit=None) -> float:
    """The same quantity from an observed `(effect, t)` pair — `crit * |effect| / |t|`.

    `MA33`'s route, used to derive `S19`'s MDE from an artifact that stored no standard error.
    It is `detection_threshold(|effect| / |t|)` and MUST agree with it exactly; if the two can
    disagree there are two definitions of MDE in this repository, which is MA5's finding again.
    """
    tt = abs(float(t))
    if tt <= 0:
        raise ValueError("t must be non-zero to back out a standard error from it")
    return detection_threshold(abs(float(effect)) / tt, n_trials, crit)


def power_at(effect, se, n_trials=None, crit=None) -> float:
    """Two-sided power of the test `|t| > crit` against a true `effect`.

    The far-tail term is kept rather than dropped: it is negligible at the sizes these designs
    run at, but dropping it makes the function silently wrong for a bar below the effect, and a
    power calculation that is wrong only in the easy cases is worse than one that is right.
    """
    s = float(se)
    if s <= 0:
        raise ValueError(f"se must be positive, got {s}")
    c = critical_value(n_trials, crit)
    d = abs(float(effect)) / s
    return float(_N.cdf(d - c) + _N.cdf(-d - c))


def available_independent_n_from_deff(n_overlapping, deff) -> float:
    """`n_overlapping / deff` — the DESIGN-EFFECT route.

    `deff` must be a design effect measured against its own null. R3's rule is that a raw design
    effect proves nothing — 600 independent draws in 12 blocks report one near 1.8 from pure
    sampling error, because that ratio is F(k-1, n-k) — so this function takes the number and
    does NOT compute it; get it from `options_stats.effective_n` (shuffled null included) or an
    equivalent simulation, and quote the null beside it.

    NOT interchangeable with `available_independent_n_nonoverlapping`. See `compare_routes`.
    """
    n = float(n_overlapping)
    d = float(deff)
    if n <= 0 or d <= 0:
        raise ValueError(f"need positive n_overlapping and deff, got {n} and {d}")
    return float(n / d)


def available_independent_n_nonoverlapping(n, h) -> float:
    """`n / h` — the NON-OVERLAPPING-WINDOW route. A count, not a variance-based quantity.

    NOT interchangeable with `available_independent_n_from_deff`, and `POWER_GATE.md` 5.1 is the
    record of someone assuming otherwise: a pre-registered validation asked one to reproduce the
    other, and it could not, because they are different quantities that happened to sit in
    adjacent columns of one table.
    """
    nn = float(n)
    hh = float(h)
    if nn <= 0 or hh <= 0:
        raise ValueError(f"need positive n and h, got {nn} and {hh}")
    return float(nn / hh)


def compare_routes(deff_route, nonoverlap_route) -> dict:
    """Report the two routes side by side. **CORROBORATION, NEVER VALIDATION.**

    Agreement is reassuring and disagreement is informative, and neither is evidence that one
    route is correct — there is no theorem making them equal. `relative_gap` is reported against
    the SMALLER of the two, so the figure is the conservative one.
    """
    a = float(deff_route)
    b = float(nonoverlap_route)
    lo = min(abs(a), abs(b))
    return {
        "deff_route": a,
        "nonoverlap_route": b,
        "relative_gap": (abs(a - b) / lo) if lo > 0 else None,
        "status": "corroboration_not_validation",
        "note": ("These are DIFFERENT quantities (POWER_GATE.md 5.1). Neither validates the "
                 "other; report both."),
    }


def gate(available_n, effect, n_trials=None, crit=None,
         z_power=Z_POWER_CONVENTION, ambiguity=AMBIGUITY, se=None) -> dict:
    """THE GATE. Is a question answerable on the evidence available, before it is asked?

    Returns a verdict against a pre-committed effect size, plus both MDE vocabularies so the
    caller cannot quote the 50%-power number as though it were the 80%-power one.

    The ambiguity band resolves toward NOT PERMITTED, which is the conservative direction: a
    design that only just reaches its bar has not shown it can answer the question, and
    `RUN_RULES` A6 already says an ambiguous result against a pre-committed threshold is a null.
    """
    c = critical_value(n_trials, crit)
    req = required_n(effect, crit=c, z_power=z_power)
    ratio = float(available_n) / req
    amb = float(ambiguity)
    if ratio >= 1.0 + amb:
        verdict = _PERMITTED
    elif ratio >= 1.0 - amb:
        verdict = _NULL
    else:
        verdict = _NOT
    out = {
        "available_n": float(available_n),
        "effect_ruled_on": float(effect),
        "crit": c,
        "z_power": float(z_power),
        "required_n": req,
        "ratio": ratio,
        "ambiguity": amb,
        "verdict": verdict,
        "effect_needed_for_power": mde_at_power(available_n, crit=c, z_power=z_power),
    }
    if se is not None:
        out["detection_threshold_50pct_power"] = detection_threshold(se, crit=c)
        out["mde_80pct_power"] = (c + float(z_power)) * float(se)
        out["power_at_ruled_effect"] = power_at(effect, se, crit=c)
        out["se"] = float(se)
    return out


def state(effect, se, n_trials=None, crit=None, z_power=Z_POWER_CONVENTION) -> str:
    """The one-line statement `RUN_RULES.md` PART A rule 11 asks every register to print.

    Both numbers, in one sentence, with the bar that produced them — so a reader cannot pick up
    the 50%-power figure believing it is the 80%-power one.
    """
    c = critical_value(n_trials, crit)
    det = detection_threshold(se, crit=c)
    mde = (c + float(z_power)) * float(se)
    pw = power_at(effect, se, crit=c)
    src = f"N = {int(n_trials)}" if n_trials is not None else "explicit"
    return (f"MDE at |t| > {c:.4f} ({src}): detection threshold {det:.6g} (50% power); "
            f"{mde:.6g} at {_N.cdf(float(z_power)) * 100:.0f}% power. "
            f"Power against the registered effect {float(effect):.6g} is {pw * 100:.1f}%.")
