"""V1 — SHADOW VINTAGES: a forward, paired A/B of every adoption.

Amendment 1 (`PAPER_TRACK_CONTRACT.md` §5a) made an adopted scoring change close the current
vintage and open the next. That gives the project an honest clock, and it costs it something
real: **Rule 6 — a vintage change resets the whole accrued clock and buys nothing
statistically.** A vintage that closes at month 30 has spent 30 months for no evidence.

This module is the answer to "then how does an adoption ever get evidence?". When vintage N+1
opens, vintage N's frozen composite keeps being scored in SHADOW on the same dates, from the
same code path, with its parameters pinned rather than re-derived. The two books are then
compared as a **paired** difference, and the same anytime-valid machinery the contract already
uses (`track_meter.boundary`) is pointed at that difference.

WHY PAIRING IS THE WHOLE POINT, and the one number that justifies this file existing:

    both books see the same market on the same days, so the market risk that dominates a
    vs-SPY comparison CANCELS.

The contract's vs-SPY meter runs at sigma 3.9847 pp/month and needs ~19 pp/yr to cross at 60
months. A shadow pair whose books overlap heavily runs at a far smaller sigma -- at 1.0 pp/month
the same boundary needs ~4.8 pp/yr. That is a four-fold improvement for free, and it is the only
reason a live A/B of an adoption is worth attempting at all.

AND THE HONEST OTHER HALF, which is in `PREREG_v1_shadow_vintages.md` and must travel with any
result this ever produces: **the tension is structural.** sigma_d is small exactly when the two
books overlap, i.e. when the adoption changed little; an adoption big enough to matter also
raises sigma_d. There is no configuration in which this instrument is powerful AND the change
being tested is small. It is a real improvement over the vs-SPY meter and it is still weak in
absolute terms. A shadow pair that has not crossed is the EXPECTED outcome and is NOT evidence
that the adoption was worthless.

RESEARCH INSTRUMENTATION ONLY. Nothing here may reach a public surface, ever -- V1's own brief
says so, and `tests/test_shadow_vintage.py` pins it by AST over the outbound modules. The
project already shipped one false claim by letting a research object reach Discord
(`PT-OUTBOUND`); this one is fenced before it has any numbers to leak.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
from typing import Dict, List, Optional, Sequence

from . import track_meter

# ---------------------------------------------------------------------------
# Frozen at this commit. Same discipline as the contract's meter: these are
# pre-registered parameters, not tunables, and PREREG_v1_shadow_vintages.md is
# the register. No parameter here may be revisited after this commit.
# ---------------------------------------------------------------------------

CONTRACT_VERSION = "V1-shadow-vintages-2026-08-10"

# Deliberately IMPORTED, not re-declared. A second copy of rho/alpha would be a second record of
# the same fact, free to drift from the contract Don signed.
RHO = track_meter.RHO                       # 3.0
ALPHA = track_meter.ALPHA                   # 0.05, two-sided
DESIGN_EFFECT = track_meter._DESIGN_EFFECT  # 1.466091 -- R9's AR(1) lag-1 +0.189

# The verdict horizon is the contract's, for one reason: a shadow pair that outlived its own
# vintage would be comparing a book to a parameter set nothing has run for years.
VERDICT_MONTHS = track_meter.VERDICT_MONTHS          # 60
MIN_MONTHS_FOR_ANY_VERDICT = 6                       # below this, INSUFFICIENT and nothing else

# A pair is only interpretable while the two books remain comparable. If the live book drifts so
# far from the shadow that they share less than this much weight, the difference is no longer
# "the effect of the adoption" -- it is two unrelated books.
MIN_WEIGHT_OVERLAP = 0.20


# ---------------------------------------------------------------------------
# Parameter snapshots -- a PINNED copy, never a re-derivation
# ---------------------------------------------------------------------------

# The scoring inputs that define a vintage. V1's brief is explicit that the shadow must run "the
# SAME code path with the OLD frozen parameters (a pinned snapshot of the config, not a
# re-derivation)", and this tuple is what "the parameters" means. Adding a key here is itself a
# construction change and belongs in a register.
PARAM_KEYS = ("theme_weights", "sector_neutral", "residual_momentum", "ev_point_in_time",
              "large_cap_min", "top_decile", "max_weight", "weighting", "top_n")


def snapshot(params: Dict) -> Dict:
    """Freeze a parameter set into a comparable, hashable snapshot.

    Only `PARAM_KEYS` survive, sorted, so two snapshots taken through different call paths that
    describe the same model compare equal. The hash is over the canonical JSON, which is what
    makes "did anything actually change?" a mechanical question rather than a judgement.
    """
    clean = {}
    for k in PARAM_KEYS:
        if k not in (params or {}):
            continue
        v = (params or {})[k]
        if isinstance(v, dict):
            v = {str(kk): (round(float(vv), 10) if isinstance(vv, (int, float)) else vv)
                 for kk, vv in sorted(v.items())}
        elif isinstance(v, float):
            v = round(v, 10)
        clean[k] = v
    blob = json.dumps(clean, sort_keys=True, separators=(",", ":"))
    return {"params": clean, "params_id": hashlib.sha256(blob.encode()).hexdigest()[:12],
            "n_keys": len(clean)}


def same_model(a: Dict, b: Dict) -> bool:
    """Do two snapshots describe the same model? The vintage rule's trigger, mechanically."""
    return bool(a) and bool(b) and a.get("params_id") == b.get("params_id")


# The pinned snapshot for the CURRENTLY OPEN vintage. Written now, while vintage 2 is the only
# open one and no successor exists, so it cannot have been chosen to make any comparison look a
# particular way. When an adoption opens vintage 3, its predecessor's parameters are already
# here, in a tracked file, rather than being reconstructed afterwards from memory or from git.
PINNED: Dict[int, Dict] = {
    2: {"opened": _dt.date(2026, 8, 10),
        "note": "vintage 2 as opened by Amendment 1; deployed flat 1/7 themes, low_risk zeroed",
        "snapshot": snapshot({
            "theme_weights": {"quality": 0.125, "momentum": 0.125, "value": 0.125,
                              "growth": 0.125, "capital_discipline": 0.125,
                              "institutional": 0.125, "insider": 0.125, "low_risk": 0.0},
            "sector_neutral": False, "residual_momentum": False, "ev_point_in_time": True,
            "large_cap_min": 10e9, "top_decile": 0.10, "max_weight": 0.08,
            "weighting": "score", "top_n": None})},
}


def pinned_snapshot(vintage: int) -> Optional[Dict]:
    """The frozen parameters a shadow book must be scored with. None if never pinned."""
    row = PINNED.get(int(vintage))
    return dict(row["snapshot"]) if row else None


# ---------------------------------------------------------------------------
# Divergence -- reported per rebalance, as V1 requires
# ---------------------------------------------------------------------------

def divergence(live_positions: Sequence[Dict], shadow_positions: Sequence[Dict]) -> Dict:
    """How far apart are the two books at ONE rebalance?

    `weight_overlap` is 1 - 0.5 * sum|w_live - w_shadow| over the union of names: 1.0 when the
    books are identical, 0.0 when they share nothing. It is the standard portfolio-overlap
    measure and it is the quantity that governs whether a paired comparison means anything --
    which is why `MIN_WEIGHT_OVERLAP` gates the verdict rather than merely decorating it.

    Name counts alone are NOT enough: two books can hold the same 86 names at weights that make
    them different portfolios, and the overlap number is the one that notices.
    """
    lw = {str(p.get("ticker")): float(p.get("weight") or 0.0) for p in (live_positions or [])}
    sw = {str(p.get("ticker")): float(p.get("weight") or 0.0) for p in (shadow_positions or [])}
    names = set(lw) | set(sw)
    l1 = sum(abs(lw.get(t, 0.0) - sw.get(t, 0.0)) for t in names)
    shared = sorted(set(lw) & set(sw))
    return {"n_live": len(lw), "n_shadow": len(sw), "n_shared": len(shared),
            "n_only_live": len(set(lw) - set(sw)), "n_only_shadow": len(set(sw) - set(lw)),
            "weight_overlap": round(1.0 - 0.5 * l1, 6),
            "l1_weight_distance": round(l1, 6),
            "comparable": bool(names) and (1.0 - 0.5 * l1) >= MIN_WEIGHT_OVERLAP}


# ---------------------------------------------------------------------------
# The frozen sigma ESTIMATOR
# ---------------------------------------------------------------------------

def sigma_monthly_pp(te_annual_pp: float) -> float:
    """sigma for the PAIRED difference, from the two books' annualised tracking error.

    The estimator is frozen here; the input is measured ONCE, at pair open, by scoring both
    parameter sets over the historical backtest panel and taking the annualised standard
    deviation of the difference in their top-decile returns. That is a deterministic procedure
    fixed before any vintage pair exists, which is what makes it a pre-registration rather than
    a knob.

    The same AR(1) design-effect inflation the contract uses is applied, for the same reason:
    the difference series is autocorrelated too, and without the inflation the boundary breaks
    its own guarantee (measured on the vs-SPY meter: 6.7% false crossings against a nominal 5%).

    SIGMA MAY NEVER BE REVISED DOWNWARD -- contract §6.5, and it binds here identically. A later
    measurement showing the books track more closely than first estimated is exactly the
    circumstance in which lowering sigma would manufacture a crossing.
    """
    te = float(te_annual_pp)
    if not (te > 0):
        raise ValueError("tracking error must be positive; a zero-sigma meter always crosses")
    return (te / math.sqrt(12.0)) * math.sqrt(DESIGN_EFFECT)


def boundary(n: int, sigma: float) -> float:
    """The Robbins boundary at `n` months for this pair's sigma.

    Delegates to `track_meter.boundary` rather than re-implementing it: one boundary function in
    the project, so a change to the guarantee cannot apply to one meter and not the other.
    """
    return track_meter.boundary(n, sigma=float(sigma), rho=RHO, alpha=ALPHA)


def detectable_difference_pp_per_year(n: int, sigma: float) -> float:
    """The sustained annual difference this pair would need to cross at `n` months.

    Quote this beside every shadow verdict. A meter that has not crossed says nothing until the
    reader knows what it COULD have detected.
    """
    return boundary(n, sigma) / n * 12.0


# ---------------------------------------------------------------------------
# The verdict
# ---------------------------------------------------------------------------

def verdict(monthly_diff_pp: Sequence[float], sigma: float,
            weight_overlap: Optional[float] = None) -> Dict:
    """CONFIRMED-LIVE / HARMED / NULL / INSUFFICIENT on a paired monthly difference series.

    `monthly_diff_pp[i]` is (live vintage's excess) - (shadow vintage's excess) for month i, in
    percentage points. Positive means the ADOPTION helped.

    There is NO sign branch anywhere in this function: the same boundary decides both
    directions, and a HARMED verdict is reached by exactly the arithmetic that reaches a
    CONFIRMED-LIVE one. That symmetry is the property `PREREG_v1_shadow_vintages.md` commits to
    and `tests/test_shadow_vintage.py` pins by flipping the sign of an entire series.
    """
    diffs = [float(x) for x in (monthly_diff_pp or [])]
    n = len(diffs)
    total = sum(diffs)
    out = {"n_months": n, "cumulative_diff_pp": round(total, 6),
           "sigma_monthly_pp": round(float(sigma), 6),
           "verdict": "INSUFFICIENT", "crossed": False,
           "min_months": MIN_MONTHS_FOR_ANY_VERDICT, "verdict_months": VERDICT_MONTHS}
    if n:
        b = boundary(n, sigma)
        out["boundary_pp"] = round(b, 6)
        out["detectable_pp_per_year"] = round(detectable_difference_pp_per_year(n, sigma), 4)
        out["crossed"] = abs(total) > b
    if weight_overlap is not None:
        out["weight_overlap"] = round(float(weight_overlap), 6)
        if weight_overlap < MIN_WEIGHT_OVERLAP:
            out["verdict"] = "NOT-COMPARABLE"
            out["why"] = (f"the books share only {weight_overlap:.1%} of weight, below the "
                          f"{MIN_WEIGHT_OVERLAP:.0%} floor; a paired difference between two "
                          f"unrelated books does not measure the adoption")
            return out
    if n < MIN_MONTHS_FOR_ANY_VERDICT:
        out["why"] = (f"{n} complete months against a floor of {MIN_MONTHS_FOR_ANY_VERDICT}; "
                      f"no verdict is available and none is implied")
        return out
    if out["crossed"]:
        out["verdict"] = "CONFIRMED-LIVE" if total > 0 else "HARMED"
        out["why"] = (f"cumulative difference {total:+.4f}pp exceeds the anytime-valid boundary "
                      f"{out['boundary_pp']:.4f}pp at n={n}")
        return out
    out["verdict"] = "NULL"
    out["why"] = (f"cumulative difference {total:+.4f}pp is inside the boundary "
                  f"{out.get('boundary_pp', float('nan')):.4f}pp at n={n}. A pair that has not "
                  f"crossed is the EXPECTED outcome and is NOT evidence that the adoption was "
                  f"worthless -- this instrument could only have detected a sustained "
                  f"{out.get('detectable_pp_per_year', float('nan')):.2f}pp/yr difference.")
    return out


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def open_pairs() -> List[Dict]:
    """Vintage pairs currently being shadowed. Empty until an adoption opens vintage 3."""
    vintages = [v for v in track_meter.VINTAGES if v.get("status") == "OPEN"]
    pairs = []
    for v in vintages:
        prev = int(v.get("vintage") or 0) - 1
        if prev in PINNED and int(v.get("vintage") or 0) in PINNED:
            pairs.append({"live_vintage": v.get("vintage"), "shadow_vintage": prev,
                          "opened": v.get("opened")})
    return pairs


def detail() -> Dict:
    """Status of the shadow machinery. Deliberately NOT vacuously green.

    Before any vintage pair exists there is nothing to report, and this says exactly that rather
    than returning a healthy-looking object with zeros in it -- the same failure `track_meter`
    had to fix when `recording_ok` read `true` before the vintage had started.
    """
    cur = track_meter.current_vintage()
    pairs = open_pairs()
    out = {"contract_version": CONTRACT_VERSION,
           "current_vintage": cur.get("vintage"),
           "pinned_vintages": sorted(PINNED),
           "n_pairs": len(pairs), "pairs": pairs,
           "rho": RHO, "alpha": ALPHA, "design_effect": round(DESIGN_EFFECT, 6),
           "min_weight_overlap": MIN_WEIGHT_OVERLAP,
           "min_months_for_any_verdict": MIN_MONTHS_FOR_ANY_VERDICT,
           "verdict_months": VERDICT_MONTHS,
           "public_surface": "never - research instrumentation only (V1)"}
    if not pairs:
        out["active"] = False
        out["status"] = (
            f"no vintage pair exists yet. Vintage {cur.get('vintage')} is open and has no "
            f"predecessor being shadowed, so there is nothing to compare and no verdict of any "
            f"kind is available. The machinery and the decision rule are registered in advance; "
            f"the first pair begins when an ADOPTED change opens the next vintage.")
        return out
    out["active"] = True
    out["status"] = f"{len(pairs)} vintage pair(s) under shadow"
    return out


def frozen_parameters() -> Dict:
    """Everything a reader needs to check that nothing was retuned after the fact."""
    return {"contract_version": CONTRACT_VERSION, "rho": RHO, "alpha": ALPHA,
            "design_effect": DESIGN_EFFECT, "verdict_months": VERDICT_MONTHS,
            "min_months_for_any_verdict": MIN_MONTHS_FOR_ANY_VERDICT,
            "min_weight_overlap": MIN_WEIGHT_OVERLAP,
            "param_keys": list(PARAM_KEYS),
            "sigma_estimator": ("(annualised TE between the two books' top-decile returns) / "
                                "sqrt(12) * sqrt(AR(1) design effect); measured ONCE at pair "
                                "open and never revised downward"),
            "pinned": {k: {"opened": v["opened"].isoformat(),
                           "params_id": v["snapshot"]["params_id"]} for k, v in PINNED.items()}}
