"""
E-4 -- the market-tail crash flag: option-implied left-tail mass as a crash flag.

Register: `PREREG_e4_market_tail_flag.md` (committed ALONE and BLIND at `cf7c7fc`, markdown only,
378 lines, a strict git ancestor of every measurement commit). Ledger entry `E-4` / `S-SEED-5`,
option-implied half -- the half `IDEAS_LEDGER.md` names `I-1` as unblocking.

**THE VERDICT OBJECT IS A CRASH RATE. NEVER ALPHA.** `MA28-CARD`'s gate style. `S10` is the
reason the distinction is structural rather than remembered: it ran a valuation-band exclusion as
a *screen*, failed the portfolio-drawdown leg, and its own mechanism arm then found the excluded
names crashed at HALF the rate of the names kept. This is a card candidate, not a screen. No
return statistic -- no alpha, no IC, no long-short, no expectancy -- is computed anywhere in this
module or in `scripts/e4_market_tail_flag.py`, and `tests/test_e4_market_tail.py` pins that by
reading the **AST** of both files rather than grepping them (`MA49`'s comment-versus-code defect,
whose sixth instance was a guard failing against the CORRECT tree because the repair comment
quoted the defect verbatim).

WHAT THIS MODULE OWNS, AND WHAT IT DELIBERATELY DOES NOT
--------------------------------------------------------
It owns the *flag construction* (a within-date quintile with a declared minimum cross-section)
and the *2x2 census*. It does **not** own a single bar. Every threshold in the verdict path comes
from `valuation.studies.crash_gate`, whose bars are keyword-only with no defaults -- `I-3`'s
design decision, taken because `MA5` measured that a default is exactly how the Harvey-Liu-Zhu
bar froze at the constant 3.0 while this project's `N` went past 90 and on to 239.

THE THRESHOLD IS 0.70 AND NOT THE 0.50 THAT MATCHES THE CRASH EVENT
-------------------------------------------------------------------
`MA28`'s crash event is `fwd_ret <= -0.50`, so the *natural* risk-neutral analogue is
`Q(S_T <= 0.50 * S_0)` -- which is what `O-1`'s K2 reads. It is not the primary here, and the
reason is this lane's own instrument census rather than a preference: **at 0.50, 80.48% of usable
I-1 slices are reading a wing EXTRAPOLATION**, against 46.06% at 0.70 and 27.74% at 0.80. At 0.70
a majority of readings rest on quoted strikes. The choice was fixed in the register on that
pre-outcome statistic and on nothing else; 0.50/0.60/0.80/0.90 travel as SENSITIVITY carrying no
verdict, and quoting one as the result voids the register.

AND THE TAIL ITSELF IS NOT SR-677 AS PUBLISHED
-----------------------------------------------
`I-1` measured that NY Fed SR-677 implemented literally returns **0 usable slices of 387** on
equity chains, for two structural reasons -- a `K(delta)` map that is not invertible on a steep
skew, and a flat vol extrapolation that puts a step in `sigma'`, i.e. a delta function in
`sigma''`, which the density carries as `C_sigma * sigma''`. The departures (log-moneyness
abscissa, C1 smooth-pasted wings) are documented in `valuation/studies/rnd.py` and they bind
every number this module produces.

THE SPOT IS `raw_close` AND THIS FAILS SILENTLY IF IT IS NOT
-------------------------------------------------------------
Strikes are as-traded; `data/bulk/prepared/bars`'s `close` is split- and dividend-adjusted (NVDA
2012 reads 0.27 against a raw 11.97, a 43x ratio). `U1-SPLIT`'s defect does not raise -- the
option still prices, it is simply nowhere near the money. `rnd.build_slice` runs the parity
diagnostic on every slice for exactly this reason, and rows failing it are excluded and counted.
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Sequence

import numpy as np
import pandas as pd

__all__ = [
    "BAND",
    "PRIMARY_THRESHOLD",
    "QUINTILE",
    "SENSITIVITY_THRESHOLDS",
    "TARGET_DTE",
    "MIN_NAMES_PER_DATE",
    "cohens_kappa",
    "odds_ratio",
    "pick_expiry",
    "tail_mass_row",
    "two_by_two",
    "within_date_worst_quintile",
]

# --------------------------------------------------------------------------- registered constants
# EVERY CONSTANT BELOW IS FROM THE REGISTER. Changing one after a measurement voids the item --
# `MA28`'s own rule, quoted because it is the rule that makes a pre-registration mean anything.

PRIMARY_THRESHOLD = 0.70          # sec 3.2 -- NOT 0.50; see the module docstring
SENSITIVITY_THRESHOLDS = (0.50, 0.60, 0.80, 0.90)   # sec 3.2 -- NO VERDICT
TARGET_DTE = 92                   # sec 3.3 -- 63 trading days, MA28's crash window, in calendar days
BAND = (50, 140)                  # sec 3.3 -- chosen on a coverage PLATEAU, pre-outcome
QUINTILE = 0.20                   # sec 3.1 -- the ledger's own flag width, adopted verbatim
MIN_NAMES_PER_DATE = 50           # sec 3.1 -- MA28's own extfin floor, reused


def pick_expiry(expiries: Sequence, asof, target: int = TARGET_DTE,
                band=BAND) -> Optional[pd.Timestamp]:
    """The expiry nearest `target` days inside `band`, or None.

    ONE rule, fixed in the register before any outcome was read. The band was chosen on coverage
    alone and sits on a PLATEAU -- [50,140] and [45,150] give an identical 93.5% expiry-found and
    55.3% usable rate on the 220-name-day sample, so the choice is not perched on an edge. The
    wider [30,200] reaches 60.8% usable and was REJECTED: a 6.7x tenor range inside one
    cross-section is a tenor confound, and `C-TENOR` exists because even 2.8x is not nothing.
    """
    asof = pd.Timestamp(asof)
    lo, hi = int(band[0]), int(band[1])
    best, best_gap = None, None
    for e in expiries:
        e = pd.Timestamp(e)
        dte = int((e - asof).days)
        if dte < lo or dte > hi:
            continue
        gap = abs(dte - int(target))
        if best_gap is None or gap < best_gap:
            best, best_gap = e, gap
    return best


def tail_mass_row(chain: pd.DataFrame, spot: float, asof, symbol: str, r: float,
                  thresholds: Sequence[float] = (PRIMARY_THRESHOLD,) + SENSITIVITY_THRESHOLDS,
                  target: int = TARGET_DTE, band=BAND) -> Dict[str, object]:
    """One (name, date) -> one tail-mass record, or a refusal that says why.

    NEVER raises on bad data and NEVER returns a number it could not compute. A refusal carries
    `usable=False` and a `reason`; a caller writing a coverage census needs the refusals, and a
    function that silently returned only the survivors would make that census impossible.

    `spot` MUST be the as-traded `raw_close` -- see the module docstring.
    """
    from valuation.studies import rnd

    asof = pd.Timestamp(asof)
    out: Dict[str, object] = {"symbol": str(symbol), "date": asof, "usable": False,
                              "reason": None, "spot": float(spot) if spot is not None else None}
    if spot is None or not (math.isfinite(float(spot)) and float(spot) > 0):
        out["reason"] = "bad_spot"
        return out
    if chain is None or not len(chain):
        out["reason"] = "no_chain_on_date"
        return out

    exps = pd.to_datetime(chain["expiration"]).unique()
    e = pick_expiry(exps, asof, target=target, band=band)
    if e is None:
        out["reason"] = "no_expiry_in_dte_band"
        return out

    xs = chain.loc[pd.to_datetime(chain["expiration"]) == e]
    s = rnd.build_slice(xs, spot=float(spot), asof=asof, expiry=e, symbol=str(symbol), r=r,
                        thresholds=tuple(thresholds))
    out["expiry"] = pd.Timestamp(e)
    out["dte_days"] = int((pd.Timestamp(e) - asof).days)
    if not s.usable:
        out["reason"] = (s.reasons or ("(none)",))[0]
        return out

    out["usable"] = True
    out["tail_mass"] = float(s.tail_mass[PRIMARY_THRESHOLD])
    for frac in SENSITIVITY_THRESHOLDS:
        out["tail_mass_%s" % frac] = (float(s.tail_mass[frac]) if frac in s.tail_mass else None)
    out["extrapolated_primary"] = bool(s.threshold_extrapolated.get(PRIMARY_THRESHOLD, False))
    out["atm_vol"] = s.diagnostics.get("atm_vol")
    out["integral"] = s.diagnostics.get("integral")
    out["negative_mass"] = s.diagnostics.get("negative_mass")
    out["parity_spot_dev_frac"] = s.diagnostics.get("parity_spot_dev_frac")
    out["n_smile"] = (s.diagnostics.get("smile") or {}).get("n_smile")
    out["cdf_route_max_gap"] = s.diagnostics.get("cdf_route_max_gap")
    return out


def within_date_worst_quintile(frame: pd.DataFrame, value_col: str, *, date_col: str = "date",
                               q: float = QUINTILE,
                               min_names: int = MIN_NAMES_PER_DATE) -> pd.Series:
    """The flag: the WORST (highest tail mass) `q` of each date's cross-section.

    A date with fewer than `min_names` usable names forms no quintile and every row on it is
    UNFLAGGED **and excluded by the caller** -- never quietly flagged False and kept, which would
    put a date the rule could not evaluate into the comparison bucket. `MB8`'s finding is the
    general form: the bucket a rule cannot evaluate is a real bucket and is not the safe one.

    `q` and `min_names` are explicit so a caller cannot inherit them by accident, but they DO
    carry the register's values as defaults -- unlike `crash_gate`'s bars, these are not
    pre-committed *bars*, they are the construction, and the construction is pinned by test.
    """
    if not (0.0 < float(q) < 1.0):
        raise ValueError("within_date_worst_quintile: q must be strictly in (0, 1)")
    flag = pd.Series(False, index=frame.index)
    for _, g in frame.groupby(date_col, sort=False):
        v = pd.to_numeric(g[value_col], errors="coerce")
        ok = v.notna()
        if int(ok.sum()) < int(min_names):
            continue
        # strictly greater than the (1-q) quantile: ties do not inflate the flagged share, and
        # on a continuous statistic this is the quintile exactly.
        thr = float(v[ok].quantile(1.0 - float(q)))
        flag.loc[g.index] = (v > thr).fillna(False)
    return flag


def qualifying_dates(frame: pd.DataFrame, value_col: str, *, date_col: str = "date",
                     min_names: int = MIN_NAMES_PER_DATE) -> list:
    """Dates whose cross-section is large enough to form a quintile at all. Reported, not assumed."""
    out = []
    for d, g in frame.groupby(date_col, sort=False):
        if int(pd.to_numeric(g[value_col], errors="coerce").notna().sum()) >= int(min_names):
            out.append(d)
    return sorted(out)


# --------------------------------------------------------------------------- the 2x2

def cohens_kappa(a: Sequence[bool], b: Sequence[bool]) -> Optional[float]:
    """Chance-corrected agreement between two boolean flags. Reported with NO bar."""
    a = np.asarray(list(a), dtype=bool)
    b = np.asarray(list(b), dtype=bool)
    n = a.size
    if n == 0 or b.size != n:
        return None
    po = float((a == b).mean())
    pa, pb = float(a.mean()), float(b.mean())
    pe = pa * pb + (1 - pa) * (1 - pb)
    if abs(1.0 - pe) < 1e-15:
        return None
    return (po - pe) / (1.0 - pe)


def odds_ratio(a: Sequence[bool], b: Sequence[bool]) -> Optional[float]:
    """Co-firing odds ratio. `None` when any cell is empty -- an infinite OR is not a number."""
    a = np.asarray(list(a), dtype=bool)
    b = np.asarray(list(b), dtype=bool)
    n11 = int((a & b).sum())
    n10 = int((a & ~b).sum())
    n01 = int((~a & b).sum())
    n00 = int((~a & ~b).sum())
    if min(n11, n10, n01, n00) == 0:
        return None
    return (n11 * n00) / float(n10 * n01)


def two_by_two(frame: pd.DataFrame, *, market_col: str, acct_col: str,
               crash_col: str) -> Dict[str, object]:
    """Counts and CRASH RATES for the four cells. Descriptive: no bar, no verdict, no gate.

    This is the deliverable that survives an UNDERPOWERED verdict, which is why it is computed
    separately from the gate rather than inside it. **Every cell carries its event COUNT beside
    its rate**, so a reader can see which rates rest on a handful of crashes -- `crash_gate`'s own
    rule, and `MB8` is the reason it is a rule (one crash of eighty-four, quoted as a ratio).
    """
    m = frame[market_col].astype(bool).values
    a = frame[acct_col].astype(bool).values
    c = frame[crash_col].astype(bool).values

    def cell(mask):
        n = int(mask.sum())
        k = int(c[mask].sum()) if n else 0
        return {"n": n, "crashes": k, "rate": (k / n) if n else None}

    return {
        "market_flagged_and_accounting_flagged": cell(m & a),
        "market_flagged_and_accounting_clean": cell(m & ~a),
        "market_clean_and_accounting_flagged": cell(~m & a),
        "market_clean_and_accounting_clean": cell(~m & ~a),
        "n_rows": int(len(frame)),
        "market_flagged_share": float(m.mean()) if len(m) else None,
        "accounting_flagged_share": float(a.mean()) if len(a) else None,
        "cohens_kappa": cohens_kappa(m, a),
        "co_firing_odds_ratio": odds_ratio(m, a),
        "note": ("Descriptive census. Rates carry their event counts; a rate resting on a "
                 "handful of crashes is a count and must not be read as a rate."),
    }
