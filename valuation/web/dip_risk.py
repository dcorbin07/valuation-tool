"""V6-B's M1 risk statistic, attached to the name a reader is actually looking at.

WHAT THIS IS, AND THE ONE WORD IT IS NOT
----------------------------------------
`dip_posture` carries V6-B's result as a paragraph about a population: *healthy names already
down 20% went on to fall another 20% about a quarter less often than unhealthy ones.* True, and
measured. It is also the kind of sentence a reader nods at and does not apply, because the
population it describes is not visibly connected to the twelve rows on the screen.

This module makes the connection: for each screened name it reports **which of M1's two measured
classes that name falls in**, and **the historical rate for that class**. Nothing else. It is a
DISPLAY of a measurement:

  * no vintage event — nothing here reaches the live scoring path;
  * nothing enters the composite, and no weight moves;
  * it does not order, filter or gate the screen. Adding it changes which NUMBERS a row shows
    and never which rows appear or in what order. `tests/test_dip_risk.py` fails if that stops
    being true, because the moment a measured rate decides membership it has stopped being a
    disclosure and become a selection rule needing its own register and the both-halves gate.

THE FIDELITY QUESTION, WHICH IS THE WHOLE RISK IN THIS FILE
-----------------------------------------------------------
V6's own register wrote down, before any result existed, that *"a POSITIVE would NOT license the
tab's copy without a separate live-vs-panel fidelity check — coverage is not fidelity."* M1 came
back POSITIVE, so that check is owed, and this is it. It is owed at the level of the
CLASSIFICATION: a rate is only this name's class's rate if this name is classified the way the
measured rows were.

M1's rule is two clauses (`scripts/v6b_dip_survival.py:346-347`):

    healthy = (quality theme z-score  >  0.0)  AND  (financial health score  >=  50.0)

Note the asymmetry — the quality clause is STRICT and the health clause is INCLUSIVE. It is
reproduced here exactly, including that asymmetry, rather than tidied into two `>=`.

Both clauses are computable live, which is why this is buildable at all:

  * the quality theme z-score is on the scan snapshot as `z_quality`, written by
    `screener/screen.py` from the same `build_frame` theme column the panel uses;
  * the 0-100 financial health score comes from `engine/scoring._health_score` — and M1 called
    **that same shipped function**, deliberately, rather than retyping its breakpoints.

FOUR WAYS THE MAPPING IS STILL IMPERFECT, ALL FOUR DISCLOSED RATHER THAN ASSUMED AWAY
-------------------------------------------------------------------------------------
1. **DIFFERENT CROSS-SECTION.** `z_quality > 0` means "above average quality for the names in
   THIS scan"; M1's meant "above average for that date's slice of a 2,531-name point-in-time
   panel". The RULE transfers — it is defined relative to whatever cross-section it is applied
   to — but the two cross-sections are not the same set, so the boundary sits in a slightly
   different place. Unfixable without scoring the live universe through the panel, and named
   rather than hidden.

2. **THE CASH-BURNING BRANCH WAS NEVER MEASURED.** `_health_score` has two branches. M1's panel
   build could not supply `cash_runway_years` — a live-engine quantity — so it forced the
   non-burner branch and its own C4 control reports that **zero rows took the burner branch**.
   A live cash-burning name therefore gets a health score from a branch that contributed no rows
   to the measured population, so it is **excluded** here rather than classified against a rate
   that never saw its kind. Detected by reading the shipped `classification.is_cash_burning`
   flag, not by re-deriving it (audit B7's defect class).

3. **DEPTH.** M1 measured names **at least 20% below** their trailing 252-session high. The
   screen's control runs from 10% to 40%, so a reader can put rows on the page that are outside
   the measured population entirely. Those rows are classified and given **no rate**, with the
   reason stated. This is the gate that does the most work in practice and the one most easily
   forgotten, because at the default threshold it never fires.

4. **SIZE.** The effect is not uniform: it runs **-14.29pp** in the smallest company tier and
   **-3.79pp** in the largest, and the largest tier is the one quintile that does NOT hold in
   both halves on its own. The live book is megacap-tilted, so this bites. The artifact publishes
   each quintile's MEDIAN market cap and **not its edges**, so a live name cannot be assigned to a
   measured tier — inventing edges would put a confident fabricated number on a public surface,
   which is the failure `withhold.py` exists to prevent. What CAN be said soundly is
   one-directional: a name above the TOP quintile's own median is necessarily inside the top
   quintile, because that median sits at roughly the 90th percentile of the whole distribution.
   So `weakest_size_tier` is True or unknown; it is never False. Below the line says nothing.

WHAT THIS FIELD DISCRIMINATES ON THIS SURFACE — ALMOST NOTHING, AND THAT IS THE FINDING
----------------------------------------------------------------------------------------
MEASURED, not assumed, by sweeping the live screen's own gates against M1's rule: **a name that
lists on the Dip Detector can essentially never classify UNHEALTHY.** Two independent reasons,
both structural:

  * the screen's cheap prefilter already drops `z_quality < 0`, which is M1's quality clause
    less its strictness — so the only listed row that can fail that clause is one sitting at
    **exactly 0.0**, and
  * the screen lists on `health >= 66`, while M1's health floor is **50**, so the health clause
    is satisfied by every listed name with room to spare.

The sweep found the unhealthy class reachable in exactly the predicted cell (`z_quality == 0.0`)
and nowhere else.

So this field is **not a discriminator between two groups here; it is a verification that each
listed name really is in the measured group**, which is precisely the question a rate attached
to a row raises and precisely what "coverage is not fidelity" was warning about. Its remaining
work is the four honest refusals — depth, cash-burning, unclassifiable, and the size flag — each
of which fires on real rows.

Two things follow, and both are stated on the surface rather than left to a reader:

  * the 43.4% figure is a **comparison baseline describing names this screen does not show**,
    never a label it is about to apply to one.

    **CORRECTED 2026-08-16, and this is the copy change the r1 pass forced.** That bullet used
    to end *"It is quoted beside every rate for exactly that reason: a rate with nothing on the
    other side of it is not interpretable."* The premise is right and the placement was wrong.
    `HANDOFF_v6b_health_gap.md` §6.1 measured what a per-row side-by-side actually communicates:
    it *"invites reading the screen as having done the separating when the prefilter did it
    upstream"*. Quoting 32.5% against 43.4% on a ROW says, to any ordinary reader, *this name is
    in the better of the two groups on this page* — and there is no second group on this page.
    So the contrast is now stated ONCE, at screen level, in `SCREEN_CONTRAST_NOTE`, explicitly
    as a fact about the PANEL and immediately beside the statement that it cannot be made here.
    `label_for` renders one class's panel rate and no comparison at all.

    **The old argument survives the move**: a rate with nothing on the other side of it is not
    interpretable, which is why the other side is still rendered — one screen-level note is
    still on the surface, still adjacent, and now says which population it belongs to.
  * "healthy" here is the MEASUREMENT's looser definition, not the screen's stricter one, and
    `METHOD_NOTE` says so — otherwise a reader who knows the screen lists at 66/66/66 would
    reasonably assume the rate was measured on names that cleared 66/66/66. It was not.

`test_dip_risk.py` pins the finding, so if either gate is ever loosened the claim is re-checked
rather than quietly becoming false.

THE NUMBERS ARE SERVED AND, UNTIL 2026-08-16, WERE RENDERED TO NOBODY
---------------------------------------------------------------------
`HANDOFF_v6b_health_gap.md` §5 found `grep -c dip_risk static/app.js` → **0**: the class, both
rates, the method note and the "not a probability" caveat were computed on every request and
displayed nowhere. `rendered_text` exists so the banned-phrasing rule can be asserted against
what is SERVED — and with no renderer it was sweeping copy no reader could see. `renderDip` now
reads this block, so the guard covers text that reaches somebody. That gap is the reason the
careful wording above was worth writing and the reason it was worth nothing until now.

V3's RULE, WHICH IS THE REASON THE COPY IS SHAPED THE WAY IT IS
---------------------------------------------------------------
A measured group average is not a statement about the next name a reader clicks. V3 made the
hot score's confidence language learn that, and a per-name field is where it matters most,
because putting a percentage on a row is the single most natural way to be read as "this
company's chance". Every rendered sentence here says *"of names in this class"* and the payload
carries `NOT_A_PROBABILITY` beside the number. The field is deliberately named
`further_fall_rate` — a rate over a class — and never `risk`, `probability` or `odds`.

BOTH CLASSES ARE EQUALLY SAYABLE, which is the same rule `dip_posture` applies to a NULL
verdict. The unhealthy label is written out in full and quotes the healthy rate beside it, so
the unflattering classification is exactly as legible as the flattering one and neither reads as
an absence.

The rendered text is checked against `dip_posture.BANNED` — the same list, imported rather than
copied — because that list already carries the DISTRESS family V6-B's own write-up put there,
and a further-fall statistic sitting next to a void bankruptcy arm is precisely where "fell
further less often" slides into "went bust less often".
"""
from __future__ import annotations

from typing import List, Optional

from . import dip_posture

# --------------------------------------------------------------------------------------- #
# PROVENANCE — every number below is quoted, and the test suite re-reads its source
# --------------------------------------------------------------------------------------- #

REGISTER = "PREREG_v6b_dip_survival.md"
ARTIFACT = "data/free_analysis/V6B_DIP_SURVIVAL.json"
SCRIPT = "scripts/v6b_dip_survival.py"

# --------------------------------------------------------------------------------------- #
# M1's CLASSIFICATION — reproduced verbatim, asymmetry and all
# --------------------------------------------------------------------------------------- #

#: `scripts/v6_dip_detector.py:41-42`, cited in the register as 3.3. The quality clause is
#: STRICT and the health clause is INCLUSIVE; see `classify` for why that is preserved.
QUALITY_FLOOR = 0.0
HEALTH_FLOOR = 50.0

HEALTHY, UNHEALTHY = "healthy", "unhealthy"

#: The population M1 measured: at least this far below the trailing high, over that many
#: sessions, looking forward that many. `scripts/v6_dip_detector.py:37-40` and the artifact's
#: own `depth` / `fwd_td`.
MEASURED_DEPTH = 0.20
TRAIL_SESSIONS = 252
FORWARD_SESSIONS = 126

# --------------------------------------------------------------------------------------- #
# THE MEASURED RATES — artifact `diagnostics.D1_base_rates`
# --------------------------------------------------------------------------------------- #

#: P(a further -20% within `FORWARD_SESSIONS`), by class.
RATE = {HEALTHY: 0.3251, UNHEALTHY: 0.4335}

#: How many drawdown episodes each rate is measured on.
N_ROWS = {HEALTHY: 9924, UNHEALTHY: 27090}

#: The same probability with no health filter at all, so a reader can see that the healthy rate
#: is below the unconditioned one rather than merely below the unhealthy one.
RATE_ALL_DIPS = 0.4044
N_ROWS_ALL = 37014

#: The registered per-date statistic and its replication. Quoted so the surface can say the
#: result held in both halves without a second measurement of it living anywhere.
PER_DATE_DIFF_PP = -10.228
PER_DATE_T = -10.585
HALVES_PP = {"early": -9.064, "late": -11.515}
N_DATES = 68

#: `diagnostics.D2_m1_within_market_cap_quintiles`. The extremes and the one that did not
#: replicate in both halves on its own.
SIZE_STRONGEST_PP = -14.287
SIZE_WEAKEST_PP = -3.787
#: The TOP quintile's own median market cap. Used only as a one-directional test — see the
#: module docstring, point 4.
TOP_QUINTILE_MEDIAN_MCAP = 21_852_950_000.0

# --------------------------------------------------------------------------------------- #
# THE COPY
# --------------------------------------------------------------------------------------- #

#: V3's rule, on the payload rather than left to the template.
NOT_A_PROBABILITY = (
    "This is how often it happened to a measured group of past companies, not a probability "
    "for this one.")

#: Why a row can carry a class and no rate. One string per reason, so the surface renders a
#: cause instead of a blank.
WHY_NOT = {
    "shallow": ("This name has not fallen far enough to be in the group that was measured — "
                "the measurement covers names at least 20% below their 52-week high."),
    "unclassified": ("This name's quality or financial-health score is missing, so it cannot "
                     "be placed in either measured group."),
    "cash_burning": ("This name's financial health is scored on the cash-burning branch, and "
                     "no company in the measured group was scored that way."),
    "register_withdrawn": ("The measurement behind this figure is no longer published, so no "
                           "rate is shown."),
}


METHOD_NOTE = (
    "Measured on 37,014 drawdown episodes across an 18-year point-in-time panel of 2,531 "
    "companies. \"Healthy\" here is the definition the measurement used: quality above average "
    "for its cross-section, and financial health at least 50 out of 100 — a lower bar than the "
    "one this screen lists on, so a name that appears here has in practice already cleared it. "
    "The unhealthy figure describes companies this screen does not show, and is here so the "
    "healthy one has something to be read against.")


def _pct(x) -> str:
    return "%.1f%%" % (100.0 * float(x))


def label_for(klass: str) -> str:
    """The one-line sentence for a class: that class's rate ON THE PANEL, and no comparison.

    IT DELIBERATELY NO LONGER QUOTES THE OTHER CLASS'S RATE — see the module docstring's
    CORRECTED bullet. A per-row "32.5% against 43.4%" reads as *this name is in the better of
    the two groups here*, and there is no second group here: the screen's own filters removed
    it upstream. The panel contrast moved to `SCREEN_CONTRAST_NOTE`, rendered once, where it
    can say which population it describes.

    "on the measured panel" is in the sentence rather than left to a nearby note, because a
    number and its scope get separated the moment anything is copied, tooltipped or truncated.

    Both directions are still written out in full and neither is a stub. A healthy row that
    said "32.5%" and an unhealthy row that said nothing would make the unflattering class read
    as missing data, and that rule is untouched by the change above.
    """
    return ("%s group on the measured panel: %s of these names went on to fall another 20%% "
            "within about six months." % (klass.capitalize(), _pct(RATE[klass])))


def unhealthy_share() -> float:
    """The panel's own unhealthy share — DERIVED from the row counts, never typed.

    It is the number that makes the contrast concrete: on the panel that produced these rates
    nearly three quarters of drawdown episodes were unhealthy, and on this screen essentially
    none are. Deriving it means the share and the counts it is computed from cannot come to
    disagree, which is this project's standing habit after four separate stale-figure
    corrections.
    """
    return float(N_ROWS[UNHEALTHY]) / float(N_ROWS_ALL)


#: THE NOTE THE r1 PASS FORCED, and the reason the per-name label carries no comparison.
#:
#: `HANDOFF_v6b_health_gap.md` measured that the live screen does NOT reproduce M1's comparison:
#: its prefilter "removes M1's entire unhealthy side before the classifier sees it" (§0.2), the
#: unhealthy class is reachable "at exactly one value of `z_quality` — 0.0 — and nowhere else"
#: (§0.1), and the field is therefore "a verification that a listed row is inside the measured
#: group, not a discriminator between two groups on this surface" (§5). Every clause below is
#: that finding said to a reader; the wording is pinned to the handoff by test.
#: IT CARRIES THE PEER RATE, and that is deliberate rather than an oversight of the change
#: above. Moving the comparison off the rows must not delete it: `METHOD_NOTE` promises the
#: unhealthy figure is "here so the healthy one has something to be read against", and a rate
#: with nothing on the other side of it is not interpretable. So both panel rates are stated
#: HERE, once, explicitly about the panel — which is the distinction the whole change turns on.
#: A per-row "32.5% against 43.4%" claims a separation this page did not make; a screen-level
#: "on the panel it was 32.5% against 43.4%, and this page cannot make that comparison" is a
#: fact about the panel with its scope attached.
SCREEN_CONTRAST_NOTE = (
    "The comparison behind this figure was made on the measured panel, where %s of drawdown "
    "episodes were in the unhealthy group and %s of those went on to fall another 20%%, "
    "against %s of the healthy group. That comparison cannot be made on this page. This "
    "screen's own filters remove the unhealthy side before the classification runs, so "
    "essentially every name listed here is already in the healthy group — the separating was "
    "done by those filters upstream, not by the figure shown. Read the rate as a check that a "
    "listed name is inside the group that was measured, not as this screen sorting names into "
    "a better half and a worse one."
    % (_pct(unhealthy_share()), _pct(RATE[UNHEALTHY]), _pct(RATE[HEALTHY])))


#: Rendered only on the rows it is true of. The effect is not uniform across company size and
#: the live book is megacap-tilted, so on this surface the caveat applies to most of what a
#: reader sees — CLAUDE.md's "the claim is strongest exactly where the product is not". Both
#: figures are interpolated from the pinned constants rather than retyped.
SIZE_CAVEAT = (
    "This name is in the largest size tier, where the measured effect is weakest — %.2f "
    "percentage points against %.2f in the smallest tier — and that tier is the one that did "
    "not hold in both halves of the sample on its own."
    % (SIZE_WEAKEST_PP, SIZE_STRONGEST_PP))


# --------------------------------------------------------------------------------------- #
# THE REGISTER GATE
# --------------------------------------------------------------------------------------- #

def register_is_live() -> bool:
    """Is V6-B still POSITIVE? Read at call time, never cached.

    DERIVED, NOT SET BY HAND, for the reason `dip_posture.digest_eligible` gives about itself:
    a close-out that revises the paragraph and forgets a second surface leaves the two
    disagreeing, and the surface nobody remembered is the one still making the claim. A test
    pinning `RISK_STATUS == POSITIVE` catches that too — but only for as long as the test
    survives the edit, and a runtime gate does not depend on that.

    Fails to the safe side by construction: anything other than POSITIVE withdraws the rates.
    """
    return dip_posture.RISK_STATUS == dip_posture.POSITIVE


# --------------------------------------------------------------------------------------- #
# THE CLASSIFICATION
# --------------------------------------------------------------------------------------- #

def classify(z_quality, health_score) -> Optional[str]:
    """M1's class for one name, or None when it cannot be determined.

    `(quality > 0.0) and (health >= 50.0)` — the asymmetry is M1's and is deliberate here. A
    name sitting exactly at the cross-sectional quality average is UNHEALTHY under the strict
    clause, and one sitting exactly at 50/100 health is HEALTHY under the inclusive one. Tidying
    either into the other would silently move a boundary and re-point a published rate at a
    population that was never measured.

    A MISSING input returns None, never a class. Defaulting a missing quality score to
    "unhealthy" would attach the 43.4% rate to a name nobody scored, and defaulting it to
    "healthy" would attach 32.5% — both are a confident number invented out of an absence, and
    the second is the flattering direction.
    """
    q = _num(z_quality)
    h = _num(health_score)
    if q is None or h is None:
        return None
    return HEALTHY if (q > QUALITY_FLOOR and h >= HEALTH_FLOOR) else UNHEALTHY


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f                                        # NaN is not a score


def in_weakest_size_tier(market_cap) -> Optional[bool]:
    """True when this name is certainly in the size tier where the effect is weakest.

    ONE-DIRECTIONAL BY CONSTRUCTION. The artifact publishes each quintile's median and not its
    edges, so "is this name in Q5" is not answerable in general. It IS answerable above the
    line: the top quintile's median sits at about the 90th percentile of the whole
    distribution, so a name above it is necessarily inside the top quintile. Below the line the
    honest answer is None — unknown — and never False, because False would read as "this name
    is in a tier where the effect is stronger", which the data cannot support.
    """
    mc = _num(market_cap)
    if mc is None or mc <= 0:
        return None
    return True if mc > TOP_QUINTILE_MEDIAN_MCAP else None


# --------------------------------------------------------------------------------------- #
# THE PER-NAME FIELD
# --------------------------------------------------------------------------------------- #

def for_name(drawdown, z_quality, health_score, market_cap=None,
             cash_burning=None) -> dict:
    """The risk block for one screened name. Pure — this is the whole computation.

    Every branch that withholds the rate still returns the class where one could be determined,
    because "we could not place this name" and "this name is in the healthy group but is
    shallower than the measurement" are different facts and a reader is owed which.
    """
    klass = classify(z_quality, health_score)
    dd = _num(drawdown)

    # Checked FIRST and it withdraws the class too, not just the rate. A class whose floors
    # come from a withdrawn register is not a neutral fact left standing — rendered beside the
    # word "healthy" it invites exactly the lookup the withdrawal is meant to stop.
    if not register_is_live():
        return {"class": None, "applies": False, "why_not": WHY_NOT["register_withdrawn"],
                "why_not_code": "register_withdrawn", "further_fall_rate": None,
                "peer_rate": None, "n_episodes": None, "label": None,
                "not_a_probability": NOT_A_PROBABILITY, "weakest_size_tier": None,
                "basis": {}}

    reason = None
    if klass is None:
        reason = "unclassified"
    elif bool(cash_burning):
        reason = "cash_burning"
    elif dd is None or dd < MEASURED_DEPTH:
        reason = "shallow"

    applies = reason is None
    other = None if klass is None else (UNHEALTHY if klass == HEALTHY else HEALTHY)
    weakest = in_weakest_size_tier(market_cap)

    return {
        "class": klass,
        "applies": applies,
        "why_not": None if applies else WHY_NOT[reason],
        "why_not_code": reason,
        # The rate is present ONLY when it applies. A rate beside a "does not apply" flag is a
        # number that will be read and a flag that will not.
        "further_fall_rate": RATE[klass] if applies else None,
        "peer_rate": RATE[other] if applies else None,
        "n_episodes": N_ROWS[klass] if applies else None,
        "label": label_for(klass) if applies else None,
        "not_a_probability": NOT_A_PROBABILITY,
        "weakest_size_tier": weakest,
        # Present only where the flag is True, for the same reason the rate is present only
        # where it applies: a caveat beside a field that does not carry it is a string the
        # renderer has to decide about, and renderers decide wrong.
        "size_caveat": SIZE_CAVEAT if weakest else None,
        "basis": {
            "z_quality": _num(z_quality),
            "health_score": _num(health_score),
            "quality_floor": QUALITY_FLOOR,
            "health_floor": HEALTH_FLOOR,
            "measured_depth": MEASURED_DEPTH,
        },
    }


def summary(rows: List[dict]) -> dict:
    """The coverage block, per the standing coverage rule.

    A per-name field that quietly fails to attach on most rows reads as though the statistic
    were narrow rather than as though the join were broken — the failure mode the coverage rule
    exists for. So the counts ship beside the rows, including a breakdown of WHY each
    withholding happened, and a caller can see at a glance whether a screen is mostly
    unclassified.
    """
    blocks = [r.get("dip_risk") for r in rows if isinstance(r, dict) and r.get("dip_risk")]
    n = len(blocks)
    applied = [b for b in blocks if b.get("applies")]
    by_reason = {}
    for b in blocks:
        code = b.get("why_not_code")
        if code:
            by_reason[code] = by_reason.get(code, 0) + 1
    return {
        "register": REGISTER,
        "artifact": ARTIFACT,
        "rows": n,
        "classified": sum(1 for b in blocks if b.get("class")),
        "rate_shown": len(applied),
        "withheld_by_reason": by_reason,
        "coverage": (float(len(applied)) / n) if n else None,
        "healthy": sum(1 for b in blocks if b.get("class") == HEALTHY),
        "unhealthy": sum(1 for b in blocks if b.get("class") == UNHEALTHY),
        "in_weakest_size_tier": sum(1 for b in blocks if b.get("weakest_size_tier")),
        # The measured population, restated where the numbers are, so a reader of the payload
        # alone can tell what the rates are rates OF.
        "measured": {
            "depth": MEASURED_DEPTH,
            "trail_sessions": TRAIL_SESSIONS,
            "forward_sessions": FORWARD_SESSIONS,
            "rate": dict(RATE),
            "n_rows": dict(N_ROWS),
            "rate_all_dips": RATE_ALL_DIPS,
            "n_rows_all": N_ROWS_ALL,
            "per_date_diff_pp": PER_DATE_DIFF_PP,
            "per_date_t": PER_DATE_T,
            "halves_pp": dict(HALVES_PP),
            "n_dates": N_DATES,
            "size_strongest_pp": SIZE_STRONGEST_PP,
            "size_weakest_pp": SIZE_WEAKEST_PP,
        },
        "method_note": METHOD_NOTE,
        # The panel contrast, stated once at screen level instead of on every row. The share is
        # served beside the sentence so a caller that renders its own layout still has the
        # number rather than having to parse it back out of the prose.
        "screen_contrast_note": SCREEN_CONTRAST_NOTE,
        "panel_unhealthy_share": unhealthy_share(),
        "not_a_probability": NOT_A_PROBABILITY,
    }


def rendered_text(rows: List[dict], block: dict) -> str:
    """Every sentence this feature puts on a surface, concatenated.

    Exists so the banned-phrasing rule can be asserted against what is SERVED rather than
    against this file — `dip_posture`'s own rule, and V4's lesson that rendering is where copy
    leaks.
    """
    parts = [block.get("method_note") or "", block.get("screen_contrast_note") or "",
             block.get("not_a_probability") or ""]
    for r in rows:
        b = (r or {}).get("dip_risk") or {}
        parts.extend([b.get("label") or "", b.get("why_not") or "",
                      b.get("size_caveat") or "", b.get("not_a_probability") or ""])
    return " ".join(p for p in parts if p)


def violations(text: str) -> list:
    """Delegates to `dip_posture`. One banned list on this surface, not two."""
    return dip_posture.violations(text)
