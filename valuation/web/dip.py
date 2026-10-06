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


#: How far BELOW the threshold a free drawdown may sit and still buy a valuation.
#:
#: THE PRESELECTOR IS DELIBERATELY LOOSE, AND THIS IS THE WHOLE REASON IT IS SAFE. The free
#: drawdown comes from the SNAPSHOT -- yesterday's close against a 52-week high computed then --
#: while the rendered drawdown comes from the valuation's own as-traded price. They disagree by
#: however much the name has moved since the scan. A tight preselector would therefore DROP a
#: name that qualifies today because it did not qualify yesterday, and it would do so silently.
#:
#: Five points of slack is wider than a day's move on any name this screen would report (the
#: shallowest row it has ever rendered is 51%), so the preselector is a NECESSARY condition
#: that costs nothing and the measured drawdown stays the AUTHORITY for what is shown. A name
#: admitted on slack and then measured below the threshold is dropped by the existing rule.
PRESELECT_SLACK = 0.05


def spread_across(seq, k: int):
    """`k` items taken EVENLY ACROSS `seq` by rank, both ends included.

    WHY THE SCREEN NEEDS THIS. `seq` is the qualifying names ordered DEEPEST FIRST, and the
    budget used to be `seq[:k]` -- so at `min_drawdown=0.10` the live service qualified 204
    names, valued the 12 deepest, and showed two: APP and PODD, both about 60% down. A user
    asking for "down 10%" saw only the most extreme crashes in the market, and the page gave no
    sign that the other 192 qualifiers had never been looked at.

    RAISING THE CAP IS NOT THE FIX AND WAS MEASURED, NOT ASSUMED: `_get_or_compute` falls
    through to a full `value_ticker` on a cache miss, so 204 valuations is 204 computations
    inside one request on a 512 MB instance. The budget stays; what changes is that it buys a
    SAMPLE OF THE WHOLE RANGE instead of the tail of it.

    DETERMINISTIC AND ENDPOINT-INCLUSIVE. The deepest name is always kept -- it is the one the
    page is most likely to be asked about -- and so is the shallowest qualifier, which is what
    makes the result span the request. Rounding collisions are topped up in rank order so the
    budget is always fully spent rather than quietly under-used.
    """
    n = len(seq)
    if k is None or k <= 0 or n == 0:
        return []
    if n <= k:
        return list(seq)
    if k == 1:
        return [seq[0]]
    step = (n - 1) / float(k - 1)
    idx = []
    for i in range(k):
        j = int(round(i * step))
        if j not in idx:
            idx.append(j)
    for j in range(n):                       # top up after rounding collisions
        if len(idx) >= k:
            break
        if j not in idx:
            idx.append(j)
    return [seq[j] for j in sorted(idx)[:k]]


def cheap_drawdown(row: dict):
    """This row's drawdown from the snapshot alone, or None. NO VALUATION, NO NETWORK.

    `1 - high_prox`, where `high_prox = price / 52-week high` is computed by `prices.py` and
    `broker_universe.py` for every name in every scan. Until item 23 only its within-date
    Z-SCORE reached the snapshot, so the screen could ORDER 242 eligible names for free and
    could not say how far down any of them was -- which is why it valued twelve and then
    thresholded those twelve.

    RETURNS None RATHER THAN A GUESS on an older snapshot that has no raw ratio, and the caller
    degrades to measuring the shortlist exactly as before and SAYS SO in the payload. A
    preselector that silently treated "unknown" as "shallow" would hide the deepest names on
    the page it exists to fill -- `_z_high_prox`'s own note, one layer along.
    """
    v = row.get("high_prox")
    if v is None:
        v = (row.get("extra") or {}).get("high_prox")
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    if v != v or v <= 0:                                    # NaN, or a ratio that cannot be one
        return None
    dd = 1.0 - v
    # A name ABOVE its own 52-week high reads as a small negative; that is zero drawdown, not a
    # negative one, and clamping is what `clamp_drawdown` already does for the threshold.
    return max(0.0, dd)


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

    # ITEM 23 -- THRESHOLD FOR FREE, THEN PAY FOR THE QUALIFIERS.
    #
    # This used to take the first `shortlist` names and measure them, which on the live service
    # meant 12 valuations against 242 eligible names: the screen checked 5% of what it was
    # eligible to check and then reported the result as though it had looked at the market. The
    # 12 were the DEEPEST 12 (the sort above is exact), so the cap was not hiding anything
    # deeper -- it was hiding everything BETWEEN the threshold and the 12th name's depth, which
    # at a 20% threshold is most of the interesting range. Measured on the service: of the 12,
    # six were 51-66% down and five of those six were rejected on health, so one row survived.
    #
    # With the raw ratio on the row the threshold is decidable for every eligible name at zero
    # cost, so the budget buys DEPTH OF COVERAGE instead of being spent on names that were never
    # going to qualify. The cap stays -- a valuation is a real cost and an unbounded request is
    # not an option on a 512 MB instance -- but it now applies to the QUALIFIERS.
    cheap = [(r, c, cheap_drawdown(r)) for r, c in survivors]
    n_with_cheap = sum(1 for _, _, dd in cheap if dd is not None)
    preselect_available = n_with_cheap > 0
    if preselect_available:
        floor = max(0.0, min_drawdown - PRESELECT_SLACK)
        # A name with NO free drawdown is kept, not dropped: on a part-populated snapshot the
        # unknown names are exactly the ones a strict rule would silently delete.
        # SPLIT, BECAUSE THE TWO HALVES DESERVE THE BUDGET DIFFERENTLY. `known` passed the depth
        # floor on a reading from the scan; `unknown` is kept only because the snapshot carries
        # no depth for it and a strict rule would silently delete exactly the names it cannot
        # see. Both are QUALIFIED for counting; only `known` is known to be worth a valuation.
        known = [(r, c) for r, c, dd in cheap if dd is not None and dd >= floor]
        unknown = [(r, c) for r, c, dd in cheap if dd is None]
        qualified = known + unknown
        # THE TWO POPULATIONS ARE NOT NESTED, WHICH IS WHY THE NOTE READ "204-of-163".
        # `n_qualified` counts names kept on depth PLUS names kept because their depth is
        # unknown; `n_with_cheap` counts only the ones a depth could be read for. So the first
        # can exceed the second, and the live page said "the 204-of-163 eligible names" -- a
        # ratio of two different denominators, which is impossible on its face and is the kind
        # of number a reader stops trusting the rest of the payload over. They are now counted
        # and reported separately.
        n_depth_pass = sum(1 for _, _, dd in cheap if dd is not None and dd >= floor)
        n_depth_unknown = sum(1 for _, _, dd in cheap if dd is None)
    else:
        qualified = [(r, c) for r, c, _ in cheap]
        n_depth_pass, n_depth_unknown = 0, len(qualified)
    n_qualified = len(qualified)
    capped = max(0, n_qualified - shortlist) if shortlist and shortlist > 0 else 0
    # SPREAD ACROSS THE QUALIFIERS RATHER THAN THE DEEPEST N -- see `spread_across`. Identical
    # cost, and the rows returned now span the range the caller asked for instead of being the
    # extreme tail of it.
    #
    # ONLY WHEN THE PRESELECTOR IS AVAILABLE, and that distinction is load-bearing rather than
    # defensive. Spreading requires knowing WHICH names qualify; without a free depth reading
    # `qualified` is just every eligible name ordered by `z_high_prox`, so a spread would value
    # names that are barely down at all -- precisely what item 23 stopped doing. With no free
    # depth the exact z-ordering is the best available information and the deepest-N prefix is
    # the right spend. Two of this module's own tests pin that fallback and caught the first cut
    # of this change doing it wrong.
    if not (shortlist and shortlist > 0):
        measured_set = qualified
    elif preselect_available:
        # SPREAD ACROSS THE *KNOWN* QUALIFIERS, AND THE FIRST CUT OF THIS GOT IT WRONG ON THE
        # LIVE SERVICE. Spreading across `qualified` sampled the 64 depth-UNKNOWN names too --
        # about a third of the budget -- and those are precisely the names least likely to clear
        # the threshold once measured. Measured at `min_drawdown=0.10`: 12 valued,
        # `rejected_health` 0, `n_unmeasured` 0, and **0 rows returned**, where the old
        # deepest-first behaviour returned 2. That is item 23's defect reintroduced by the fix
        # for a different one: a valuation spent on a name that was never going to qualify.
        #
        # The unknowns stay REACHABLE -- they take whatever budget the known set does not use --
        # so a snapshot with little depth coverage still measures them rather than dropping
        # them silently.
        measured_set = spread_across(known, shortlist)
        if len(measured_set) < shortlist:
            measured_set = measured_set + unknown[:shortlist - len(measured_set)]
    else:
        measured_set = qualified[:shortlist]

    # F-11 (audit #5 H2's consequence). `rejected_health` was a COUNT, and the identities were
    # discarded -- which is why `dip_rejects` had no source and recorded a fabricated zero. The
    # classification is already computed here; only the aggregation threw it away. Collected,
    # not recomputed: a second implementation of "which names fail the health floors" is
    # exactly how a screen and a book come to disagree about what they screened.
    out, unmeasured, rejected_health, health_rejects = [], 0, 0, []
    rejected_shallow = 0
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
            # The drawdown is already known here (`dd is None` was rejected above), so the
            # F-11 conjunction -- deep enough AND failing health -- is decidable by the
            # consumer without re-measuring anything. The threshold is NOT applied here: this
            # is the raw reject population and `dip_rejects()` below is the one place the
            # declared >= min_drawdown rule lives.
            health_rejects.append({
                "ticker": (r.get("ticker") or "").strip().upper(),
                "drawdown": dd,
                # AS-TRADED, from the same measurement as the drawdown -- never a panel
                # price. A strike compared against a split-adjusted price picks a contract
                # nowhere near the money and fails SILENTLY (this record measured raw_close
                # 411.80 against an adjusted 8.236 on one real row).
                "price": m.get("price", r.get("price")),
                "high_52w": m.get("high_52w"),
                "below": list(h.get("below") or []),
                "missing": list(h.get("missing") or []),
                "scores": dict(h.get("scores") or {}),
                "days_since_high": m.get("days_since_high"),
            })
            continue
        if dd < min_drawdown:
            # COUNTED, because "valued and then found too shallow" was invisible. With
            # `rejected_health` 0 and `n_unmeasured` 0 and no rows, the only way to tell where
            # twelve valuations went was to reason about it -- which is how the first cut of the
            # spread shipped. The free depth is a RATIO from the snapshot and the measured
            # drawdown is a real price path, so some disagreement near the floor is expected and
            # `PRESELECT_SLACK` exists for it; a large count here means the budget is being
            # spent on names that do not qualify.
            rejected_shallow += 1
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
        # ITEM 23 -- HOW MANY QUALIFIED AGAINST HOW MANY WERE CHECKED, which the page is now
        # required to state. Before this the only honest reading of the payload was "12 names
        # were valued out of 242 eligible", and the page reported the result as though it had
        # looked at the market.
        "n_checked_for_depth": n_with_cheap if preselect_available else 0,
        "n_qualified_on_depth": n_qualified if preselect_available else None,
        # THE THREE COUNTS THAT ACTUALLY NEST, so a reader can add them up. `n_qualified_on_depth`
        # is the sum of the two below, and `n_checked_for_depth` is how many of the eligible
        # names a depth could be read for at all.
        "n_depth_pass": n_depth_pass if preselect_available else None,
        "n_depth_unknown_kept": n_depth_unknown if preselect_available else None,
        "selection": ("spread across the qualifying range" if (
            preselect_available and shortlist and shortlist > 0 and n_qualified > shortlist)
            else ("deepest first (no free depth reading)" if (
                shortlist and shortlist > 0 and n_qualified > shortlist)
                else "all qualifiers")),
        "preselect_available": preselect_available,
        "preselect_slack": PRESELECT_SLACK,
        "preselect_note": (
            ("%d of the %d eligible names qualified on depth (%d read from the scan, %d kept "
             "because the scan carries no depth for them); %d were valued, SPREAD ACROSS the "
             "qualifying range rather than taken from the deepest end, so the rows span the "
             "depth you asked for. Depth is read from the scan at no cost; a valuation is not, "
             "which is why it is capped."
             % (n_qualified, n_eligible, n_depth_pass, n_depth_unknown,
                len(measured_set))) if preselect_available else
            ("this scan snapshot carries no 52-week-high ratio, so depth could not be read "
             "without a valuation and only the deepest-ranked names were checked. A scan run "
             "after this change will carry it.")),
        "rejected_prefilter": rejected_prefilter,
        "rejected_health": rejected_health,
        # Measured, and then shallower than the threshold the caller asked for.
        "rejected_shallow": rejected_shallow,
        # ADDITIVE. Every existing consumer reads `rows`, and this changes none of them.
        "health_rejects": health_rejects,
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


class DipWiringError(TypeError):
    """`get_result` handed back something that is neither a result nor a cache entry.

    A DISTINCT TYPE ON PURPOSE. `engine_measure` swallows per-name failures by design -- one
    name that will not value is not the screen failing -- and that is exactly how this defect
    stayed invisible for seven weeks: every one of 229 names raised the same wiring error and
    each was counted as "unmeasured", which reads as a data gap. A wiring error is not a data
    gap, so it gets its own type and is NOT swallowed.
    """


def unwrap_result(obj):
    """The `ValuationResult`, whether handed one or the cache entry that holds one.

    **THE DEFECT THIS CLOSES (found 2026-10-03; live since the Dip Detector shipped
    2026-08-13).** Every caller passes `web/app._get_or_compute`, which returns a
    `resultcache.Entry` -- its own docstring says *"Returns the cache entry rather than the
    result, because the caller has to stamp the document with when the numbers were made"* --
    and it has done since `42597e2` on 2026-08-06, **a week before this screen was built**. So
    `measurement_from` did `getattr(result, "company")` on an `Entry`, got `None`, computed no
    drawdown, and counted every name unmeasured. Measured on the service: `n_eligible` 241,
    `n_measured` 12, `n_unmeasured` 12 -- **every examined name unmeasured** -- while the page
    said "No name cleared a 20% fall". `POST /api/value` shows NKE at 33.87 against a 52-week
    high of 69.63, so the data was there the whole time.

    **WHY A STUB HID IT, which is the transferable part.** `measurement_from`'s docstring says
    it is *"Pure -- no network, no cache -- so the mapping from a valuation to a screened row is
    testable against a stub result, where the interesting mistakes live."* The stub was a
    result-shaped object, so the mapping was tested and the WIRING never was. A pure function
    tested only against a hand-built input cannot catch a caller passing the wrong type.

    Order matters: `.company` is checked FIRST, so a result that happens to carry a `.result`
    attribute is still treated as a result.
    """
    if obj is None:
        return None
    if hasattr(obj, "company"):
        return obj
    inner = getattr(obj, "result", None)
    if inner is not None:
        # One level only. A cache entry holding a cache entry is itself a wiring defect and
        # must not be papered over by recursing until something sticks.
        if not hasattr(inner, "company"):
            raise DipWiringError(
                "get_result returned a %s whose .result is a %s, and that carries no "
                ".company" % (type(obj).__name__, type(inner).__name__))
        return inner
    raise DipWiringError(
        "get_result returned a %s, which carries neither .company (a result) nor .result "
        "(a cache entry)" % (type(obj).__name__,))


def measurement_from(result) -> Optional[dict]:
    """Turn one `ValuationResult` into the `measure(row)` payload `screen` consumes.

    Pure — no network, no cache — so the mapping from a valuation to a screened row is
    testable against a stub result, which is where the interesting mistakes live.
    """
    if result is None:
        return None
    # UNWRAPPED IN ONE PLACE. Every caller passes a cache ENTRY, not a result; see
    # `unwrap_result` for the seven weeks that cost. A wrong type raises rather than
    # returning None, because None here is indistinguishable from "this name has no data".
    result = unwrap_result(result)
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


def dip_rejects(payload: dict, min_drawdown=None) -> List[dict]:
    """F-11's REJECT population from a `screen()`/`screen_snapshot()` payload.

    The declared entry rule, and the ONLY place its conjunction lives: *"names down >=20% from
    the 252-session high AND failing the shipped health floors, classified by the screen's own
    published functions `health_check` and `clamp_drawdown` on the same rows the live screen
    uses."* Both halves are read from what `screen` already computed -- nothing is
    re-classified here, because a second implementation of the same rule is how a screen and a
    book come to disagree about what they screened.

    **THE THRESHOLD GOES THROUGH `clamp_drawdown`**, so the book is held to the same clamped
    value the live screen used and not to a raw literal.

    **A COVERAGE LIMIT THAT MUST TRAVEL WITH THE LIST: `screen` measures only its SHORTLIST**
    (the deepest `shortlist` names by drawdown proximity), so a name that never got measured
    cannot appear here. The reject list is bounded by the measurement budget, and a name absent
    from it is *"not measured"* rather than *"healthy"* -- `screen`'s own `n_unmeasured` is the
    figure that says how many.
    """
    floor = clamp_drawdown(DEFAULT_MIN_DRAWDOWN if min_drawdown is None else min_drawdown)
    out = []
    for r in (payload or {}).get("health_rejects") or []:
        dd = r.get("drawdown")
        try:
            dd = float(dd)
        except (TypeError, ValueError):
            continue                                   # unmeasured is not "shallow"
        if dd != dd or dd < floor:
            continue
        row = dict(r)
        row["min_drawdown_used"] = floor
        out.append(row)
    return sorted(out, key=lambda r: (-float(r.get("drawdown") or 0.0),
                                      str(r.get("ticker") or "")))


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
        except DipWiringError:
            # NOT SWALLOWED. This `except` is why the defect was invisible: every one of 229
            # names raised the same wiring error and each was counted as "unmeasured", which
            # reads as a data gap rather than as a screen that is wired to the wrong object.
            # A per-name failure is tolerable; a wiring failure is a bug and must be loud.
            raise
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
