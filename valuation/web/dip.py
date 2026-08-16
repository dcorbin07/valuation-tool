"""The Dip Detector — healthy names trading well below their own 52-week high.

WHAT DON ASKED FOR, AND THE ONE WORD THIS MODULE WILL NOT SAY
------------------------------------------------------------
Don, 2026-08-13: *"when a rock solid company sees a dip of X%+ and the financials are all
healthy, no good reason besides sentiment or something that will very likely pass over, we
have it alerted."*

Two halves. The first half is a SCREEN and every piece of it is already measured somewhere in
this repository: a drawdown, a set of sub-scores, and the publication flags that say whether
this name's valuation is fit to show. That half is built here.

The second half — *"no good reason besides sentiment"*, *"will very likely pass over"* — is a
claim about FORWARD RETURNS: that healthy names in drawdown recover better than the market.
Nothing in this repository has measured that. It is exactly what the pipeline lane is
pre-registering as **V6**, and until that register closes this module may not imply the
answer in either direction. Not in a verb, not in a badge colour, not in an ordering that
reads as a ranking of conviction. `POSTURE` below is the sentence the tab says instead, and
`BANNED` is the list of phrasings a test refuses to let onto the surface.

The distinction is not pedantry, and this project has already paid for getting it wrong the
other way round: `PT-OUTBOUND` shipped a research figure to Discord, and the landing page
rendered a pre-B6 `+17.4%/yr` for weeks because the number lived in a config dict nobody
grepped. A screen that quietly reads as a prediction is the same defect with better manners.

THE DRAWDOWN IS NOT IN THE SNAPSHOT, AND THE TEMPTING SHORTCUT IS WRONG
----------------------------------------------------------------------
The quantity this screen is built on already exists: `prices.get_quote` computes

    high_prox = price / max(close over the trailing 252 sessions)

for every name in every scan, because the momentum theme z-scores it
(`settings.NUMBER_THEME["high_prox"] = "momentum"`). Drawdown from the 52-week high is
exactly `1 - high_prox`.

It is then THROWN AWAY. `screen.py::_rows_from` builds `extra` from a fixed list of raw
fields and `high_prox` is not on it; what survives is `extra["numbers"]["high_prox"]`, which
is the **cross-sectional z-score**, not the ratio.

THE SHORTCUT THAT MUST NOT BE TAKEN: a z-score cannot be turned back into a percentage. It is
`(x - mean) / sd` over that date's cross-section, so the same z is a different drawdown on
every scan date — deep on a calm day, shallow on a day the whole market is down. Rendering
`z` as a percentage would put a fabricated, confident, per-name number on a public surface,
which is the failure class `withhold.py` exists to prevent. (The other tempting inversion —
"some name is always at its high, so max(high_prox) = 1.0, use that as an anchor" — needs a
SECOND anchor to solve two unknowns, and "some name is always at its high" is an assumption
about the cross-section, not a measurement of it.)

WHAT IS TRUE ABOUT THE Z-SCORE, AND IS THE REASON THIS IS AFFORDABLE: standardisation within a
date is a strictly monotone (affine) transform, so ordering by `z_high_prox` ascending is
EXACTLY ordering by drawdown descending. Not approximately — identically. So the z-score is a
perfect *ranking* key and a useless *threshold* key, and this module uses it for precisely the
first: rank the healthy names by it, take a bounded shortlist, and then MEASURE the real
percentage for that shortlist only. Every drawdown this module reports is a measured ratio of
two prices, never a transformed z.

The cap that follows from that is real and is DISCLOSED rather than silently applied — see
`capped` and `n_unmeasured` in the payload. `RUN_RULES` A6's habit applies: a bound nobody
reports reads as coverage.

WHAT WOULD *NOT* REMOVE THE CAP, recorded because it is the obvious guess and it is wrong.
Persisting the raw `high_prox` in the scan would make the drawdown exact and free over the
whole universe — a one-line change in the screener lane, filed in the handoff, worth doing —
and the cap would not move, because the drawdown is not what the cap is paying for. The health
gate is defined on three 0-100 sub-scores that only a full valuation produces, and so are two
of the four disqualifiers. The binding cost is the VALUATION, not the price history.

WHAT "HEALTHY" MEANS, AND WHY THE FLOOR IS 66
--------------------------------------------
`engine/scoring.py` computes five 0-100 sub-scores — valuation, quality, growth, health,
momentum. Don named three of them: quality, financial health, growth.

The floor is not invented. `scoring._recommendation` is the product's own calibration of what
a 0-100 score means, and 66 is where it stops saying "Hold" and starts saying "Buy";
`static/app.js::scoreColor` independently uses the same 66 for green. Two places in the
product already treat 66 as the healthy boundary, so this takes it rather than adding a third
opinion. `HEALTH_FLOORS` is a dict so a future calibration moves one number, once.

MOMENTUM IS DELIBERATELY NOT IN THE HEALTH GATE. A name in a 20% drawdown has poor momentum by
construction — `_momentum_score` reads price vs the 200-day average and the 6-month return —
so requiring healthy momentum would reject the entire population this screen exists to find.
Valuation is excluded for a different reason: it is the sub-score the withholding machinery
suppresses, and gating on a figure that is sometimes withheld would make the screen's
membership depend on data availability.

A CHECK THAT DID NOT RUN IS NOT A CHECK THAT PASSED
---------------------------------------------------
Don's four disqualifiers do not all live on the same surface, and pretending otherwise is how
a green tick comes to mean nothing:

  * `withheld`      — on every snapshot row (`fair_value_withheld`). CHECKABLE HERE.
  * `no_data`       — the fail-closed kind (`KIND_UNAVAILABLE`), also on the row. CHECKABLE.
  * `terminal_share`— a cap applied to a DCF's confidence (`blend.terminal_share_cap`).
  * `beta_provenance` — a property of `wacc._resolve_beta`.

The last two exist only where a full valuation ran, and the hot list runs no DCF for most
names (`api_hotstocks` fills the rest with peer multiples). So they are reported `not_run`,
NOT `pass`. `Screen.checks_not_run` counts them and the tab says so. This is the same
distinction `holdout_theme_validate` had to learn the hard way: `oos_directions_tested = 0`
means no test was run, which is a different statement from a negative result.

A row lists only if no check FAILED. It may list with checks that did not run, provided the
surface says which — which is what `Row.checks` carries.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from ..engine.publication import (KIND_UNAVAILABLE, ROW_WITHHELD, ROW_WITHHELD_KIND,
                                  ROW_WITHHELD_REASON)
from . import dip_risk as _dip_risk

# --------------------------------------------------------------------------------------- #
# THE THRESHOLD CONTROL
# --------------------------------------------------------------------------------------- #

#: Don's "X%": the default drawdown from the 52-week high that puts a name on the screen.
DEFAULT_MIN_DRAWDOWN = 0.20

#: The visible control's range. Don asked for 10-40% and these are the ends of it. Clamped
#: rather than rejected, because a query string is user input and a 400 on a slider is worse
#: than a clamp the payload reports back (`Screen.min_drawdown` is the value actually used).
MIN_DRAWDOWN_FLOOR = 0.10
MIN_DRAWDOWN_CEIL = 0.40

#: How many prefiltered names get a real measurement per request. See "THE ONLY PART OF THIS
#: MODULE THAT TOUCHES A COMPANY" below for why it is this low, and `MAX_SHORTLIST` for the
#: ceiling a caller may raise it to. The exact `z_high_prox` ordering is what makes a small
#: number defensible: these are the N most drawn-down eligible names, not a sample of them.
DEFAULT_SHORTLIST = 12
MAX_SHORTLIST = 25


def clamp_drawdown(x) -> float:
    """The threshold actually used, clamped into the control's range. Bad input -> default."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return DEFAULT_MIN_DRAWDOWN
    if v != v:                                          # NaN
        return DEFAULT_MIN_DRAWDOWN
    if v > 1.0:                                         # a slider sending 20 rather than 0.20
        v = v / 100.0
    return max(MIN_DRAWDOWN_FLOOR, min(MIN_DRAWDOWN_CEIL, v))


# --------------------------------------------------------------------------------------- #
# THE HEALTH GATE
# --------------------------------------------------------------------------------------- #

#: 0-100 sub-score floors, taken from `scoring._recommendation`'s "Buy" boundary. See the
#: module docstring for why 66 and why momentum and valuation are not here.
HEALTH_FLOORS: Dict[str, float] = {"quality": 66.0, "health": 66.0, "growth": 66.0}

#: The floor's provenance, rendered next to the chips so the number is not a bare assertion.
HEALTH_FLOOR_NOTE = ("Healthy means each of quality, financial health and growth scores at "
                     "least 66 out of 100 — the same boundary at which this product's own "
                     "scoring stops saying \"Hold\" and starts saying \"Buy\".")


def health_check(subs: Optional[dict]) -> dict:
    """Score a name's sub-scores against the floors.

    Returns {"ok", "missing", "below", "scores"}. A MISSING sub-score is not a pass: a name
    whose growth could not be computed has not demonstrated healthy growth, it has declined to
    answer, and this screen's whole premise is that the fundamentals were checked.
    """
    subs = subs or {}
    scores, missing, below = {}, [], []
    for k, floor in HEALTH_FLOORS.items():
        v = subs.get(k)
        try:
            v = None if v is None else float(v)
        except (TypeError, ValueError):
            v = None
        if v is None or v != v:
            missing.append(k)
            scores[k] = None
            continue
        scores[k] = v
        if v < floor:
            below.append(k)
    return {"ok": not missing and not below, "missing": sorted(missing),
            "below": sorted(below), "scores": scores}


# --------------------------------------------------------------------------------------- #
# THE DISQUALIFIER GATE
# --------------------------------------------------------------------------------------- #

#: Every check this screen claims to apply, with what it means when it does not run. The
#: strings are the surface's vocabulary too — one definition, so a badge and a tooltip cannot
#: come to disagree.
CHECKS = {
    "withheld": "The model publishes a fair value for this name (it has not refused it).",
    "no_data": "This name's fundamentals arrived — it is not withheld for missing data.",
    "terminal_share": ("The valuation's confidence is not capped by its terminal value's "
                       "share of the total."),
    "beta_provenance": "The discount rate's beta comes from a source the model trusts.",
}

PASS, FAIL, NOT_RUN = "pass", "fail", "not_run"

#: The two checks that need a full DCF, which the hot-list screen does not run. Listed as a
#: constant so the tab's "2 of 4 checks did not run" is computed, never typed.
DCF_ONLY_CHECKS = ("terminal_share", "beta_provenance")


def disqualifier_checks(row: dict) -> dict:
    """Per-check verdicts for one snapshot row: pass / fail / not_run.

    Reads the publication flags by their MODULE constants rather than by literal strings, so a
    rename in `engine/publication.py` breaks this at import rather than silently turning every
    check green.
    """
    out = {}
    withheld = bool(row.get(ROW_WITHHELD))
    kind = (row.get(ROW_WITHHELD_KIND) or "").strip().lower()

    # A withheld valuation of EITHER kind fails `withheld`; the no-data kind additionally
    # fails `no_data`, which is what lets the surface tell "we could not look" apart from
    # "the model rejects this", exactly as `record_unavailable` intends.
    out["withheld"] = FAIL if withheld else PASS
    out["no_data"] = FAIL if (withheld and kind == KIND_UNAVAILABLE) else PASS

    for k in DCF_ONLY_CHECKS:
        out[k] = NOT_RUN
    return out


def _reason(row: dict) -> Optional[str]:
    r = row.get(ROW_WITHHELD_REASON)
    return str(r) if r else None


# --------------------------------------------------------------------------------------- #
# THE SCREEN
# --------------------------------------------------------------------------------------- #

def _z_high_prox(row: dict):
    """This row's within-date z-score of `high_prox`, or None.

    ORDERING KEY ONLY. See the module docstring — this is never rendered and never converted
    into a percentage.
    """
    try:
        v = ((row.get("extra") or {}).get("numbers") or {}).get("high_prox")
        return None if v is None else float(v)
    except (TypeError, ValueError, AttributeError):
        return None


class Row(dict):
    """One screened name. A dict so it serialises straight to JSON with no adapter."""


#: The cheap prefilter's floor on the snapshot's own cross-sectional theme z-scores.
#:
#: THIS IS NOT THE HEALTH GATE AND MUST NEVER BE DESCRIBED AS ONE. It is a budget-saver: the
#: real gate is `health_check` against 0-100 sub-scores, and reaching it costs a valuation, so
#: names whose fundamentals are already below the cross-sectional average are dropped before
#: spending one on them. Zero, because the z-scores are standardised within the date and zero
#: is therefore "average for this cross-section" — a measured statement that needs no
#: calibration and cannot drift.
#:
#: A row MISSING a theme z-score survives the prefilter and is decided by the real gate. Being
#: strict here would silently narrow the screen on a data gap, which is the failure the
#: coverage rule exists for; being strict THERE is correct, because that is where the claim is.
PREFILTER_Z_FLOOR = 0.0
PREFILTER_THEMES = ("z_quality", "z_growth")


def prefilter_ok(row: dict) -> bool:
    """Cheap, snapshot-only sieve. See `PREFILTER_Z_FLOOR` — a saver, not the gate."""
    for k in PREFILTER_THEMES:
        v = row.get(k)
        try:
            v = None if v is None else float(v)
        except (TypeError, ValueError):
            v = None
        if v is None or v != v:
            continue
        if v < PREFILTER_Z_FLOOR:
            return False
    return True


def screen(rows: List[dict],
           min_drawdown: float = DEFAULT_MIN_DRAWDOWN,
           measure: Optional[Callable[[dict], Optional[dict]]] = None,
           shortlist: int = DEFAULT_SHORTLIST) -> dict:
    """Run the screen over snapshot rows. Pure: the one source of truth is injected.

    `measure(row)` returns `{"drawdown", "subs", "checks", "fair_value", "upside", ...}` for
    one name, or None if it could not be measured. It is a SINGLE callable rather than the
    three separate ones an earlier draft had, and that is a correctness decision, not a
    tidiness one: the drawdown, the sub-scores and the two DCF-only checks all come from one
    valuation of one company at one moment. Fetching them independently would let a row show a
    drawdown from today's price beside a health score from a cached result computed against a
    different one — a per-name inconsistency no test would catch because each half is correct.

    THE ORDER OF THE STAGES IS A COST DECISION, NOT A SEMANTIC ONE. The row-level
    disqualifiers and the prefilter are free; measuring is not. Filtering first and measuring
    second gives the same set as the reverse — a conjunction does not care about order — while
    measuring far fewer names.
    """
    min_drawdown = clamp_drawdown(min_drawdown)
    measure = measure or (lambda r: None)

    universe = [r for r in rows if isinstance(r, dict)]
    survivors, rejected_prefilter, rejected_checks = [], 0, 0

    for r in universe:
        checks = disqualifier_checks(r)
        if any(v == FAIL for v in checks.values()):
            rejected_checks += 1
            continue
        if not prefilter_ok(r):
            rejected_prefilter += 1
            continue
        survivors.append((r, checks))

    # Exact ordering by drawdown, at zero cost — standardisation within a date is strictly
    # monotone, so this IS the drawdown order. Names with no z sort last: unknown is not
    # "shallow", it is unknown, and putting them first would spend the whole measurement
    # budget on names whose drawdown nobody can even rank.
    def _key(item):
        z = _z_high_prox(item[0])
        return (1, 0.0) if z is None else (0, z)

    survivors.sort(key=_key)

    n_eligible = len(survivors)
    capped = max(0, n_eligible - shortlist) if shortlist and shortlist > 0 else 0
    measured_set = survivors[:shortlist] if (shortlist and shortlist > 0) else survivors

    out, unmeasured, rejected_health = [], 0, 0
    for r, checks in measured_set:
        m = measure(r) or {}
        dd = m.get("drawdown")
        h = health_check(m.get("subs"))
        # The measured checks REPLACE the row-level not_run entries only where the measurement
        # actually produced a verdict; `disqualifier_checks` stays the floor, so a valuation
        # that fails to answer cannot upgrade a row-level FAIL into a pass.
        merged = dict(checks)
        for k, v in (m.get("checks") or {}).items():
            if k in merged and merged[k] != FAIL and v in (PASS, FAIL, NOT_RUN):
                merged[k] = v
        if any(v == FAIL for v in merged.values()):
            rejected_checks += 1
            continue
        if dd is None:
            unmeasured += 1
            continue
        if not h["ok"]:
            rejected_health += 1
            continue
        if dd < min_drawdown:
            continue
        out.append(Row({
            "ticker": r.get("ticker"),
            "name": r.get("name") or r.get("ticker"),
            "sector": r.get("sector") or "",
            "price": m.get("price", r.get("price")),
            "market_cap": r.get("market_cap"),
            "hot_score": r.get("hot_score"),
            "rank": r.get("rank"),
            "drawdown": dd,
            "high_52w": m.get("high_52w"),
            "health": h["scores"],
            "score": m.get("score"),
            "confidence": m.get("confidence"),
            "checks": merged,
            "checks_not_run": sorted(k for k, v in merged.items() if v == NOT_RUN),
            "fair_value": m.get("fair_value"),
            "upside": m.get("upside"),
            "fair_value_low": m.get("fair_value_low"),
            "fair_value_high": m.get("fair_value_high"),
            "fair_value_withheld_reason": m.get("fair_value_withheld_reason") or _reason(r),
            # V6-B's M1 statistic for THIS name's measured class. Built here and nowhere else
            # because this is the only point where all three inputs coexist for one company at
            # one moment: the snapshot's `z_quality`, the valuation's 0-100 health sub-score,
            # and the drawdown just measured from the same quote. Assembling them from separate
            # passes is exactly the per-name inconsistency this function's docstring refuses.
            #
            # DISPLAY ONLY. It is computed AFTER every membership decision above, so it cannot
            # reach one — a row's class does not admit it, exclude it or move it. The sort below
            # is on `drawdown`, unchanged, and `test_dip_risk.py` pins both facts.
            "dip_risk": _dip_risk.for_name(
                drawdown=dd,
                z_quality=r.get("z_quality"),
                health_score=(h["scores"] or {}).get("health"),
                market_cap=r.get("market_cap"),
                cash_burning=m.get("cash_burning")),
        }))

    out.sort(key=lambda x: -(x.get("drawdown") or 0.0))
    return {
        "rows": out,
        "min_drawdown": min_drawdown,
        "min_drawdown_floor": MIN_DRAWDOWN_FLOOR,
        "min_drawdown_ceil": MIN_DRAWDOWN_CEIL,
        "n_universe": len(universe),
        "n_eligible": n_eligible,
        "n_measured": len(measured_set),
        "n_unmeasured": unmeasured,
        "capped": capped,
        "rejected_prefilter": rejected_prefilter,
        "rejected_health": rejected_health,
        "rejected_checks": rejected_checks,
        "health_floors": dict(HEALTH_FLOORS),
        "health_floor_note": HEALTH_FLOOR_NOTE,
        "checks": dict(CHECKS),
        # Coverage for the per-name risk field, per the standing coverage rule: a join that
        # quietly fails on most rows would otherwise read as a narrow statistic rather than a
        # broken lookup.
        "dip_risk": _dip_risk.summary(out),
    }


# --------------------------------------------------------------------------------------- #
# THE ONLY PART OF THIS MODULE THAT TOUCHES A COMPANY
#
# Everything above is pure and is tested with fixtures. This section measures one name, and it
# is fenced off deliberately: the moment a screen's filtering logic and its data fetching are
# interleaved, the filtering stops being testable without a network and the tests quietly
# become integration tests nobody runs offline.
#
# WHY THE FULL VALUATION AND NOT A CHEAP QUOTE. A price lookup would give the drawdown for
# pennies. It would not give the three 0-100 sub-scores this screen's health gate is defined
# on, and it would leave the two DCF-only checks permanently `not_run`. One valuation supplies
# all four, and — the part that matters — it is the SAME valuation the name's own page renders,
# from the same TTL cache. So a name cannot show one health score on the Dip Detector and a
# different one when the reader clicks it. That is this project's standing rule (one authority,
# no second computation) and it is what the whole cap below is being spent on.
#
# THE COST IS REAL AND IS DISCLOSED. Each miss is a vendor fetch of several seconds, and a few
# hundred live per-name lookups throttle and then return EMPTY objects rather than erroring —
# so an unbounded sweep would not merely be slow, it would silently start measuring nothing.
# `DEFAULT_SHORTLIST` bounds it, `Screen.capped` reports what the bound dropped, and
# `n_unmeasured` reports what the budget did not reach.
# --------------------------------------------------------------------------------------- #

def _beta_check(result) -> str:
    """`beta_provenance` clean? PASS unless the beta is NOT this company's own number.

    `InputProvenance.substituted` is the field's own word for that (`wacc.py:52`), so this
    reads the flag rather than pattern-matching `source`, which has five values and gains
    more.
    """
    try:
        prov = getattr(getattr(result, "wacc", None), "beta_provenance", None)
        if prov is None:
            return NOT_RUN
        return FAIL if bool(getattr(prov, "substituted", False)) else PASS
    except Exception:                                                # noqa: BLE001
        return NOT_RUN


def _terminal_share_check(result) -> str:
    """Was confidence capped by the DCF's terminal share?

    Recomputed through `blend.terminal_share_cap` — the same pure function the pipeline
    applies — rather than by re-deriving a threshold here. It takes a label and a number and
    returns a label, so calling it twice is free and cannot disagree with the pipeline.

    NOT_RUN when there is no blend or no terminal share, which is the common case on this
    surface: terminal share says nothing about a name valued on P/B-ROE or a revenue multiple,
    and `blend.terminal_share_cap`'s own docstring says callers must only apply it when the
    DCF lens is in the blend.
    """
    try:
        blend = getattr(result, "fair_value_blend", None)
        share = getattr(blend, "tv_share", None) if blend is not None else None
        if share is None:
            return NOT_RUN
        from ..engine.blend import terminal_share_cap
        _, note = terminal_share_cap(getattr(blend, "confidence", "medium"), share)
        return FAIL if note else PASS
    except Exception:                                                # noqa: BLE001
        return NOT_RUN


def measurement_from(result) -> Optional[dict]:
    """Turn one `ValuationResult` into the `measure(row)` payload `screen` consumes.

    Pure — no network, no cache — so the mapping from a valuation to a screened row is
    testable against a stub result, which is where the interesting mistakes live.
    """
    if result is None:
        return None
    cd = getattr(result, "company", None)
    score = getattr(result, "score", None)
    subs = dict(getattr(score, "subscores", None) or {}) if score is not None else {}

    price = getattr(cd, "price", None) if cd is not None else None
    high = getattr(cd, "price_52w_high", None) if cd is not None else None
    dd = None
    try:
        price_f, high_f = float(price), float(high)
        # A price ABOVE the trailing high is not a negative drawdown, it is a new high: the
        # 52-week window and the quote can be minutes apart. Clamped at zero, never negative,
        # so it can only fail the threshold rather than pass it from the wrong side.
        if high_f > 0 and price_f > 0:
            dd = max(0.0, 1.0 - price_f / high_f)
    except (TypeError, ValueError):
        dd = None

    from . import withhold as _wh
    withheld = _wh.is_withheld_result(result)

    fv = None if withheld else getattr(result, "base_fair_value", None)
    upside = None
    try:
        if fv is not None and price:
            upside = float(fv) / float(price) - 1.0
    except (TypeError, ValueError, ZeroDivisionError):
        upside = None

    # The band is the bear/bull pair the page already shows, and it is withheld WITH the
    # valuation: `withhold.py`'s whole finding is that scenarios are the same valuation re-run
    # on shifted assumptions, so publishing them past a refusal republishes the refused number.
    lo = hi = None
    if not withheld:
        scen = getattr(result, "fair_value_scenarios", None) or {}
        try:
            lo = scen.get("bear")
            hi = scen.get("bull")
            lo = None if lo is None else float(lo)
            hi = None if hi is None else float(hi)
        except (TypeError, ValueError, AttributeError):
            lo = hi = None

    # Read, never re-derived. `classify.py:82` sets this flag and `scoring._health_score`
    # branches on it; V6-B's panel build could not supply the branch's input and so measured
    # ZERO cash-burning rows, which is why `dip_risk` has to be able to tell. Deriving it here
    # from `fcf` instead would be a second definition of a shipped one — audit B7's class.
    cls = getattr(result, "classification", None)
    burning = None if cls is None else bool(getattr(cls, "is_cash_burning", False))

    return {
        "drawdown": dd,
        "price": price,
        "high_52w": high,
        "subs": subs,
        "cash_burning": burning,
        "score": None if withheld else getattr(score, "score", None),
        "confidence": getattr(score, "confidence", None) if score is not None else None,
        "fair_value": fv,
        "upside": upside,
        "fair_value_low": lo,
        "fair_value_high": hi,
        "fair_value_withheld_reason": _wh.refusal_reason(result) if withheld else None,
        "checks": {
            # A refusal here is authoritative even when the snapshot row said nothing: the
            # snapshot's flag is written by the scan, this is the model asked directly.
            "withheld": FAIL if withheld else PASS,
            "beta_provenance": _beta_check(result),
            "terminal_share": _terminal_share_check(result),
        },
    }


def engine_measure(get_result: Callable[[str], object], budget: int = DEFAULT_SHORTLIST):
    """A `measure` backed by real valuations, with a hard call budget.

    `get_result(ticker)` is injected (the route passes the TTL-cached `_get_or_compute`), so
    this module never reaches for the pipeline itself and a test can drive the whole path with
    a dict. When the budget is spent the remaining names return None, which `screen` counts as
    `n_unmeasured` and the surface reports — an unmeasured name is never rendered as "not in
    drawdown".
    """
    state = {"spent": 0}

    def _measure(row: dict) -> Optional[dict]:
        ticker = (row.get("ticker") or "").strip().upper()
        if not ticker or state["spent"] >= budget:
            return None
        state["spent"] += 1
        try:
            return measurement_from(get_result(ticker))
        except Exception:                                            # noqa: BLE001
            # One name failing to value is not the screen failing. It becomes unmeasured and
            # is counted, which is the honest reading: nobody checked it.
            return None

    return _measure


def screen_snapshot(store, get_result: Callable[[str], object], min_drawdown=None,
                    shortlist: int = DEFAULT_SHORTLIST, scan_date=None) -> dict:
    """The whole screen, from a scan snapshot — ONE definition, two callers.

    `/api/dip` renders this and `saas/notify.post_dip_digest` pushes it. Written the moment
    there was a second caller, because the alternative is two copies of the same four steps and
    that is precisely the arrangement the route's own comment warns about: the Index and the hot
    list once disagreed because the RULE was duplicated rather than the CODE. A digest that
    applied the publication passes in a different order, or skipped `withhold` entirely, would
    push a name the site itself refuses to display — and it would do it outbound, where nobody
    sees the discrepancy until it has already been sent.

    Returns `screen`'s payload with `scan_date` attached, or an `empty` marker when no scan has
    landed yet.
    """
    scan_date = scan_date or store.latest_scan_date()
    if not scan_date:
        return {"empty": True, "rows": [], "scan_date": None}
    rows = store.load_snapshot(scan_date)
    # The same two passes `/api/hotstocks` runs, in the same order and from the same modules,
    # so a name withheld there is withheld here and in the digest.
    from ..screener.fairvalue import estimate_fair_values
    from . import withhold as _withhold
    estimate_fair_values(rows, peer_rows=rows)
    _withhold.withhold_implausible_fair_values(rows)
    shortlist = max(1, min(int(shortlist), MAX_SHORTLIST))
    out = screen(rows, min_drawdown=min_drawdown,
                 measure=engine_measure(get_result, budget=shortlist), shortlist=shortlist)
    out["scan_date"] = scan_date
    return out
