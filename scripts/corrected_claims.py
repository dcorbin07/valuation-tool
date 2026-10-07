# -*- coding: utf-8 -*-
"""`CORRECTED-FLOORS` part 2 -- re-measure the eight claims `UNIVERSE-BIAS` part 2 listed as
UNMEASURED, on the corrected universe, against part 1's corrected floors.

**ZERO TRIALS.** Every construction here is already registered and landed -- `INDEX-BOOK`'s arms,
`R1`'s FF5+MOM regression, `S22`'s horizon grid, `score_confidence`, `hold_horizon`, `V6-B`'s dip
arms. Re-measuring a registered construction on a corrected universe is the `S25` / `X7RECON` /
`PANEL-EXT-RECHECK` class: no hypothesis, no bar chosen here, no second arm, no new degree of
freedom.

**THE THREE-STATE VOCABULARY IS THE DELIVERABLE AND IT IS FIXED HERE, NOT AFTER THE NUMBERS.**

* `SURVIVES` -- re-measured on the corrected universe and still clearing the bar that governs it.
* `NO LONGER HOLDS` -- re-measured and no longer clearing.
* `UNMEASURED` -- not re-measurable in this item, with the reason NAMED.

A claim that cannot be re-measured is **`UNMEASURED`, never `SURVIVES`**. `V6`'s rule: a null and
an absent measurement must not read the same, and the flattering direction here is to let an
unmeasured claim sit in the surviving column.

**TWO CLAIMS NEED NO MEASUREMENT AND THAT IS A FACT, NOT A DODGE.** The options payoff is an
OPTIONS book (`R2`'s 3,870 trades over 187 names) and no equity panel change can reach it; the
live Track Record is a FORWARD record under `PAPER_TRACK_CONTRACT.md` and no backtest change
touches it. Both were already reasoned that way in part 2's own artifact and are carried forward
rather than re-derived.

**NOTHING IS ADOPTED AND NO PUBLIC PAGE CHANGES**, pinned by test. The disclosure is **PENDING
DON** (`DECISIONS.md` 2026-10-07).
"""
from __future__ import annotations

import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

#: the three states, fixed before any number
SURVIVES = "SURVIVES"
NO_LONGER_HOLDS = "NO LONGER HOLDS"
UNMEASURED = "UNMEASURED"
STATES = (SURVIVES, NO_LONGER_HOLDS, UNMEASURED)


def data_root():
    """Resolved LAZILY. `served_index_book` computes its data root at IMPORT time and RAISES
    without the banked panel, which is how `UNIVERSE-BIAS`'s first suite errored three ways on a
    CI runner while passing locally. Nothing in this module may be imported into that failure.
    """
    from scripts.index_best import _data_root
    return _data_root()


def fa():
    return os.path.join(data_root(), "free_analysis")


def landed_corrected_alpha():
    """`UNIVERSE-BIAS` part 2's own `corrected` top-decile alpha, READ from its artifact.

    **NOT the gate target for the corrected Index book** -- that is
    `landed_corrected_deployed_alpha()` below, because `served_index_book` scores the DEPLOYED
    composite while this column is the CPCV-ADOPTED one. This function exists to REPORT the
    adopted figure beside the deployed one, so a reader can see which is which.

    (This docstring said it WAS the gate target until part 1b; the gate refused that target
    twice and the second refusal is what produced part 1b. Corrected rather than left to rot.)
    """
    p = os.path.join(fa(), "UNIVERSE_BIAS_PUBLIC.json")
    with io.open(p, encoding="utf-8") as fh:
        figs = json.load(fh)["figures"]
    for r in figs:
        if r["payload_path"] == "construction.top_decile_alpha":
            return float(r["corrected"])
    raise SystemExit("UNIVERSE_BIAS_PUBLIC.json carries no construction.top_decile_alpha; "
                     "refusing to invent a gate target")


def landed_corrected_deployed_alpha():
    """Part 1b's own DEPLOYED corrected top-decile alpha, READ from its artifact.

    This is the gate target for the corrected Index book, and NOT
    `landed_corrected_alpha()` above. `served_index_book` scores the DEPLOYED composite --
    `DEPLOYED` themes at `BASE_WEIGHT`, CPCV never consulted -- while part 2's `corrected`
    column is the CPCV-ADOPTED book. Handing it the adopted figure is a numerator from one
    construction against a gate for another, which is the very defect part 1b exists to record,
    and the gate caught it.
    """
    p = os.path.join(fa(), "CORRECTED_DEPLOYED.json")
    if not os.path.exists(p):
        raise SystemExit("REFUSING: no CORRECTED_DEPLOYED.json -- run "
                         "`python -m scripts.corrected_deployed` first. Its deployed alpha is "
                         "this gate's target and may not be typed here.")
    with io.open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    v = (d.get("deployed") or {}).get("top_decile_alpha")
    if v is None:
        raise SystemExit("CORRECTED_DEPLOYED.json carries no deployed.top_decile_alpha; "
                         "refusing to invent a gate target")
    return float(v)


def corrected_floor(key):
    """A floor from part 1's calibration, READ from its artifact. `None` if absent -- never a
    default, because a defaulted floor is how `MA5` measured the HLZ bar freezing at 3.0."""
    p = os.path.join(fa(), "CORRECTED_FLOORS.json")
    if not os.path.exists(p):
        return None
    with io.open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    if d.get("PARTIAL"):
        raise SystemExit("CORRECTED_FLOORS.json is PARTIAL -- part 1's sweep did not complete, "
                         "so no claim may be scored against its floors")
    for r in d["floors"]:
        if r["key"] == key:
            return r["corrected"]
    return None


def claim(name, surface, transcribed_in, published, corrected, state, floor=None,
          floor_key=None, why=None, note=None):
    """One row of the deliverable. `state` is checked against the fixed vocabulary, so a typo
    cannot invent a fourth state that a reader would have to interpret."""
    assert state in STATES, "unknown state %r -- the vocabulary is fixed" % state
    if state in (SURVIVES, NO_LONGER_HOLDS):
        assert corrected is not None, \
            "%s claims to be re-measured with no corrected value" % name
    if state == UNMEASURED:
        assert why, "%s is UNMEASURED with no reason named" % name
    return {"claim": name, "surface": surface, "transcribed_in": transcribed_in,
            "published": published, "corrected": corrected, "state": state,
            "floor": floor, "floor_key": floor_key, "why": why, "note": note}
