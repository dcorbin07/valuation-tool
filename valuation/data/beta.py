"""Beta, computed from prices — so a valuation stops depending on a vendor field that comes
and goes.

WHY THIS EXISTS (2026-08-07)
---------------------------
`wacc.py` read `cd.beta` (Yahoo's `info["beta"]`) and, when it was missing or implausible,
silently substituted `1.10`. That is a reproducibility hole with a measured cost: Yahoo stopped
returning a beta for **MRK** between 2026-08-04 and 2026-08-05, the fallback fired, WACC went
**5.53% → 9.31%**, and the name went from "cannot value this name" to a published 91 "Strong
Buy" — **because a vendor field vanished, not because anything about Merck changed.** The field
is INTERMITTENT rather than gone: it was back at 0.211 on 2026-08-07.

The other half is the opposite failure. `wacc.py` rejected beta `<= 0` or `> 3.0` and had no
low-side floor and no minimum-history check, so **KSPI's 0.080 — a five-year monthly beta with
only 30 monthly observations behind it, on an ADR that listed in 2024 — passed as plausible**
and produced a 5.10% WACC and a +1,255% upside.

THE ESTIMATOR, AND WHY THIS WINDOW
----------------------------------
Five-year MONTHLY returns regressed on SPY. That window is not a preference; it is the one
validated in `HANDOFF_live_data_bugs.md` §2 against the vendor on control names, and re-checked
on 2026-08-07 before this module was written:

    AAPL 1.070 / JPM 1.013 / NVDA 2.217 / MRK 0.180 / GILD 0.305 / CI 0.288 / CHTR 0.669

reproducing that section's recorded column to a worst absolute difference of **0.036** (JPM).

**A one-year DAILY window was tried first and is WRONG.** Measured the same day it returned
**KO −0.286 and XOM −0.484** — negative betas for Coca-Cola and Exxon. It is recorded here
because the daily series is the one `yahoo.py` already has in hand, so it is the window a future
reader will reach for to save a network call. It costs 0.14s to do this properly.
"""
from __future__ import annotations

import datetime as _dt
import time
from dataclasses import dataclass
from typing import Optional

# The market. Beta is defined against a market portfolio, and SPY is the proxy every
# comparison in the record was made against.
MARKET_PROXY = "SPY"

# Five years of monthly closes -> 59 monthly returns. Vendors quote a 5y monthly beta, so this
# is the same object the vendor field claims to be, which is what makes the two comparable.
BETA_PERIOD = "5y"
BETA_INTERVAL = "1mo"

# Minimum monthly observations before a beta is treated as supportable. KSPI has 30; every
# other name measured has 59. A threshold of 60 would flag EVERY name, because five years of
# monthly closes yields 59 returns — the off-by-one that makes the obvious number wrong.
MIN_BETA_OBSERVATIONS = 36

# Minimum observations before OUR OWN estimate is worth using in place of a rejected vendor
# value. Lower than the bar above on purpose: at this point the alternative is not a better
# beta, it is a constant that knows nothing about the company at all.
MIN_COMPUTED_OBSERVATIONS = 24

_TTL_SECONDS = 6 * 3600
_MKT = {"returns": None, "ts": 0.0}


@dataclass(frozen=True)
class BetaEstimate:
    """A beta and everything needed to decide whether to believe it."""
    value: Optional[float]
    n_observations: int
    as_of: str = ""
    error: str = ""

    @property
    def supportable(self) -> bool:
        return self.value is not None and self.n_observations >= MIN_COMPUTED_OBSERVATIONS

    @property
    def unavailable(self) -> bool:
        """True when the estimate could not be MADE — as opposed to made and found thin.

        THE DISTINCTION IS THE WHOLE POINT, and it was missing from the first version of this
        module. Measured 2026-08-07: running this corroboration across 402 names in 3.7 minutes
        exhausted Yahoo's quota, and **176 names came back `YFRateLimitError`**. A caller that
        cannot tell that apart from "this company has thin history" will reject a perfectly good
        vendor beta because the network was busy — turning a transient outage into a changed
        headline, which is the exact bug this whole module exists to remove.

        A vendor beta may only be REJECTED on positive evidence that its history is short. It
        may never be rejected because the check failed to run.
        """
        return self.value is None or self.n_observations == 0


def _market_returns():
    """Monthly market returns, cached in-process — the `macro.py` risk-free-rate pattern.

    One fetch serves every name in a scan; without this a 400-name run would pull the same
    index series 400 times.
    """
    now = time.time()
    if _MKT["returns"] is not None and (now - _MKT["ts"]) < _TTL_SECONDS:
        return _MKT["returns"]
    import yfinance as yf
    h = yf.Ticker(MARKET_PROXY).history(period=BETA_PERIOD, interval=BETA_INTERVAL)
    r = h["Close"].dropna().pct_change().dropna()
    _MKT.update(returns=r, ts=now)
    return r


def compute_beta(ticker: str, closes=None) -> BetaEstimate:
    """Estimate beta for `ticker` against the market proxy. Never raises.

    `closes` lets a caller pass a monthly close series it already holds; everything else
    fetches. The observation count returned is the number of PAIRED months actually regressed,
    not the length of either input — an intersection is what the regression sees, and reporting
    anything else would make the history check a fiction.
    """
    try:
        import numpy as np
        mkt = _market_returns()
        if closes is None:
            import yfinance as yf
            closes = (yf.Ticker(ticker)
                      .history(period=BETA_PERIOD, interval=BETA_INTERVAL)["Close"].dropna())
        r = closes.pct_change().dropna()
        joint = r.index.intersection(mkt.index)
        n = int(len(joint))
        if n < 2:
            return BetaEstimate(None, n, error="no overlapping observations")
        a = np.asarray(r.reindex(joint), dtype=float)
        b = np.asarray(mkt.reindex(joint), dtype=float)
        var = float(np.var(b, ddof=1))
        if not var > 0:
            return BetaEstimate(None, n, error="market variance is zero")
        beta = float(np.cov(a, b, ddof=1)[0, 1] / var)
        if beta != beta:                                   # NaN
            return BetaEstimate(None, n, error="regression produced NaN")
        as_of = ""
        try:
            as_of = str(joint[-1].date())
        except Exception:
            pass
        return BetaEstimate(beta, n, as_of=as_of)
    except Exception as e:                                 # network, shape, anything
        return BetaEstimate(None, 0, error=f"{type(e).__name__}: {e}")
