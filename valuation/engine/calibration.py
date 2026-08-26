"""
Calibration — is the fair-value gap a SIGNAL, or just a framing device?

The valuation engine now produces a defensible number for every archetype (DCF for
mature names, a justified P/B-ROE for banks, a growth-scaled revenue multiple for
pre-profit names). Defensible is not the same as PREDICTIVE. Nothing in it has ever
been measured against forward returns: it is valuation arithmetic, and the rest of
this project holds signals to a much higher bar than arithmetic.

This module closes that gap. It rebuilds the fair value POINT-IN-TIME on the same
Sharadar panel the factor research uses, and measures the value/price gap exactly
the way every other factor here is measured — coverage first, per-date rank IC,
decile spread, monotonicity, both halves of a time split reported separately.

Why it re-derives the company instead of reusing build_fundamental_panel
-----------------------------------------------------------------------
The factor panel emits standardized THEME columns; a DCF needs the raw line items
(revenue, EBIT, D&A, capex, invested capital, net debt, share count). So this walks
the same provider and the same rebalance calendar and builds a point-in-time
`CompanyData` per (date, ticker), then runs the LIVE engine on it — classify ->
WACC -> assumptions -> DCF -> comps -> growth lens -> blend. Not a re-implementation:
the same functions the website calls, which is the only way the measurement says
anything about what the site actually publishes.

Monte Carlo, sensitivity and scoring are skipped because none of them feed
`blend.value`. `test_lean_path_matches_the_full_pipeline` pins that equivalence, so
if anyone ever wires one of them into the headline this stops matching and fails.

Three traps this had to avoid, all of which have bitten this project before
--------------------------------------------------------------------------
1. **Quarterly flows.** The Sharadar export is ARQ — one QUARTER per row. Feeding
   `revenue` straight into a DCF values the company off a quarter of its sales and
   makes every fair value come out ~4x too low, uniformly, with no error. Every FLOW
   here is a trailing-twelve-month sum (with the panel's own gap guard); only the
   BALANCE-SHEET stocks come from the latest row.
2. **Currency (P7).** `marketcap` is USD, the line items are in the reporting
   currency. Mixing them is what produced SK Telecom's book/price of 892. All
   monetary line items are converted to USD by the panel's `_usd_divisor` before
   they ever reach `CompanyData`.
3. **Empty inputs (the COVERAGE RULE).** `coverage_report()` runs FIRST and is
   printed above the ICs. A fair value computed from a column that is blank in 100%
   of rows is not a weak signal, it is no signal, and this project has shipped that
   mistake four times.

What it found (2026-08-02, full universe — details in HANDOFF_growth_calibration.md)
------------------------------------------------------------------------------------
Essentially nothing, and the two numbers that looked like something both dissolved
under the first control applied to them:

  * 63-day horizon: median IC +0.0092 (t +0.99). The one apparently-significant
    figure, a +7.92%/yr top-decile alpha (t +2.04), is a SIZE effect — the widest-
    discount decile is $1.73B median cap against the universe's $4.60B, and inside
    each market-cap tercile the alpha t-stats are +0.95 / +0.21 / +0.16.
  * 252-day horizon: looks stronger (+11.17% alpha, t +3.71) but 252-day returns
    sampled every 63 days OVERLAP threefold. On non-overlapping windows the alpha
    t-stat falls to +1.78..+1.93 across all four offsets — consistently positive,
    consistently short of the t>2 bar this project holds signals to.
  * The pre-profit tier — the one the growth lens exists for — has a NEGATIVE IC at
    both horizons. The lens made the number defensible, not predictive.
  * Robust to the discount rate: rebuilt at rf=2.0% vs 4.3%, IC t +0.98 vs +0.99.

And the finding that matters most: `control_factors()` measures plain `ebit_ev` and
`neg_ev_sales` on the SAME rows and both beat the blended gap (t +1.73 / +1.92 vs
+0.99 at 63d; +3.15 / +3.27 vs +1.91 at 252d). **The full valuation engine ranks
stocks less well than a plain EV/Sales sort.** Every modelling choice in the blend is
a place to add noise, and for RANKING purposes that is the net effect. For scale, the
gap's +0.0092 median IC sits below all seven positively-weighted themes in
BACKTEST_RESULTS.json — below even `size` (+0.0126).

Honesty
-------
A null result here is a perfectly good result, and is what should be reported if it
is what comes out: it means the valuation is a reasonable way to FRAME a stock and
not something to weight as alpha. That is what came out. Do not go looking through
this panel for a cut that passes a threshold — see the note at the end of the handoff.

Run it:
    python -m valuation.engine.calibration --data-dir data/backtest \
        --json data/backtest/calibration.json
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd

from ..config import CONFIG
from ..data.models import CompanyData
from .assumptions import build_base_assumptions
from .blend import blended_fair_value
from .classify import classify
from .comps import compute_comps
from .dcf import run_dcf
from .financials import financial_scenarios
from .growth import growth_fair_value, mature_discount_rate, maturity_from_company
from .reverse_dcf import reverse_dcf
from .wacc import compute_wacc

# Point-in-time helpers, reused (not copied) from the backtest engine so the
# as-of semantics can't drift apart from the factor panel's.
from ..edge.fundamental_panel import (TTM_MAX_SPAN_DAYS, _daily_at, _f, _to_usd,
                                      _usd_divisor)

# --- Flows must be summed over four quarters; stocks are read at the period end. ---
FLOW_KEYS = ("revenue", "ebit", "ebitda", "netinc", "gp", "fcf", "ncfo", "intexp")
STOCK_KEYS = ("equity", "debt", "cashneq", "invcap")

# Maturity tiers for the "does it work better on mature names?" cut. Chosen to match
# how blend.py already behaves rather than to split the sample evenly: below ~0.5 the
# revenue lens takes over half the blend (blend.GROWTH_LED), so that is the boundary
# that means something. The middle band is where the two lenses genuinely share it.
MATURITY_TIERS = (("deep_growth", 0.0, 0.35), ("mixed", 0.35, 0.65),
                  ("established", 0.65, 1.01))

MIN_NAMES_PER_DATE = 20        # below this a cross-sectional IC is noise
MIN_DATES = 8                  # below this the t-stat on the IC series is meaningless
REALIZED_GROWTH_YEARS = 3      # horizon for "did the implied growth show up?"


# --------------------------------------------------------------------------- #
# Point-in-time company construction
# --------------------------------------------------------------------------- #

def _ttm_per_key(rows, i, keys) -> Optional[dict]:
    """TTM sums ending at row `i`, computed INDEPENDENTLY per key.

    Deliberately not `fundamental_panel._ttm`, which returns None unless every requested
    key is present in all four quarters. That is right for a factor built from a fixed
    input set; here it would mean one blank `intexp` (common, and needed only for a
    cost-of-debt refinement) silently discards the whole company. Each key gets its own
    all-four-or-nothing test, so a missing extra costs that extra and nothing else.

    The four rows must still be four DISTINCT quarters spanning a plausible year, or a
    missing filing turns "the last four rows" into two or three years of summed flow.
    """
    if i < 3:
        return None
    picked = rows[i - 3:i + 1]
    dks = [str(r.get("datekey") or r.get("date") or "") for r in picked]
    if len(set(dks)) < 4 or not all(dks):
        return None
    try:
        span = (pd.Timestamp(dks[-1]) - pd.Timestamp(dks[0])).days
    except (ValueError, TypeError):
        return None
    if span > TTM_MAX_SPAN_DAYS:
        return None
    out = {}
    for k in keys:
        vals = [_f(r, k) for r in picked]
        out[k] = float(sum(vals)) if all(v is not None for v in vals) else None
    return out


def _prep_fundamentals(rows) -> list:
    """[(datekey, sf1_row, ttm_flows|None), ...] ascending, TTM computed ONCE per quarter.

    Computing the TTM inside the date loop instead costs a full re-scan of the ticker's
    history per rebalance date (~110x the work for an identical answer).
    """
    rows = sorted(rows or [], key=lambda r: (r.get("datekey") or r.get("date") or ""))
    out = []
    for i, r in enumerate(rows):
        dk = r.get("datekey") or r.get("date")
        if not dk:
            continue
        out.append((str(dk), r, _ttm_per_key(rows, i, FLOW_KEYS)))
    return out


def _at(prep, as_of):
    """Latest (sf1, ttm) on/before as_of. Reverse walk — cannot see the future."""
    for dk, row, ttm in reversed(prep or []):
        if dk <= as_of:
            return row, ttm
    return None, None


def _rev_history(prep, as_of, years=5) -> list:
    """TTM revenue now and at each of the previous `years` anniversaries, recent-first.

    CompanyData.revenue_growth() reads this as a fiscal-year series, so TTM sums at
    annual spacing are the right shape: rev_growth_ttm becomes a real year-over-year
    number rather than one quarter against another.
    """
    out = []
    ts = pd.Timestamp(as_of)
    for k in range(years + 1):
        cut = str((ts - pd.Timedelta(days=365 * k)).date())
        _row, ttm = _at(prep, cut)
        out.append(ttm.get("revenue") if ttm else None)
    return out


def pit_company(ticker, prep, as_of, price, market_cap, sector="", industry="", beta=None,
                risk_free=None) -> Optional[CompanyData]:
    """A point-in-time CompanyData, in USD millions, or None if the row can't support one.

    `market_cap` and `price` arrive in USD (Sharadar DAILY / SEP); the statement lines
    arrive in the reporting currency and are divided by `_usd_divisor` here.

    Share count is derived as market_cap / price rather than read from `sharesbas`. That
    is not a shortcut — it makes `market_cap == price x shares` hold exactly, and since
    the fair value is `equity_value / shares` and the price is `market_cap / shares`, the
    share count CANCELS out of the value/price gap entirely. The measurement below is
    therefore immune to ADR ratios, share classes and split adjustments, all of which are
    live sources of error in `sharesbas` (pinned by test_gap_is_invariant_to_share_count).
    """
    sf1, ttm = _at(prep, as_of)
    if not sf1 or not ttm:
        return None                       # no four clean quarters -> no TTM -> no valuation
    if not price or price <= 0 or not market_cap or market_cap <= 0:
        return None

    div = _usd_divisor(sf1)

    def flow(key):
        """A TTM flow in USD millions."""
        v = ttm.get(key)
        if v is None:
            return None
        # Sharadar's *usd columns are point-in-time single-quarter figures, so they can't
        # be used for a TTM sum; convert the local TTM with the same divisor instead.
        return (v / div) / 1e6 if div else v / 1e6

    def stock(key, usd_key=None):
        v = _to_usd(sf1, usd_key, _f(sf1, key), div)
        return None if v is None else v / 1e6

    rev = flow("revenue")
    if rev is None or rev <= 0:
        return None                       # nothing to value on revenue OR on a margin

    ebit, ebitda = flow("ebit"), flow("ebitda")
    ncfo, fcf = flow("ncfo"), flow("fcf")
    # Neither `depamor` nor `capex` is in the loader's column allowlist, and this module
    # must not touch the loader. Both fall out of columns that ARE there:
    #   D&A   = EBITDA - EBIT        capex = operating cash flow - free cash flow
    da = (ebitda - ebit) if (ebitda is not None and ebit is not None) else None
    capex = (ncfo - fcf) if (ncfo is not None and fcf is not None) else None
    if capex is not None and capex < 0:
        capex = 0.0                       # negative "capex" is a disposal, not investment

    mc_mm = market_cap / 1e6
    shares_mm = mc_mm / price

    cd = CompanyData(
        ticker=ticker, sector=sector or "", industry=industry or "", as_of=as_of,
        price=float(price), shares_diluted=shares_mm, market_cap=mc_mm, beta=beta,
        revenue=rev, ebit=ebit, gross_profit=flow("gp"), net_income=flow("netinc"),
        da=da, capex=capex, fcf=fcf,
        total_debt=stock("debt"), cash_sti=stock("cashneq"),
        interest_expense=(abs(flow("intexp")) if flow("intexp") is not None else None),
        invested_capital=stock("invcap"), total_equity=stock("equity", "equityusd"),
        risk_free_rate=risk_free,
    )
    hist = _rev_history(prep, as_of)
    cd.revenue_history = [None if v is None else (v / div) / 1e6 for v in hist]
    cd.fiscal_years = list(range(len(cd.revenue_history)))
    return cd


# --------------------------------------------------------------------------- #
# The valuation itself — the live engine, minus what doesn't feed the headline
# --------------------------------------------------------------------------- #

def offline_beta(pit_beta):
    """S23 — the beta a POINT-IN-TIME valuation may use, with no network and no hindsight.

    `wacc._resolve_beta` rung 3 corroborates an unusable vendor beta by calling
    `data.beta.compute_beta`, which fetches `yf.Ticker(...).history(...)` — i.e. TODAY'S prices.
    That is correct for the live product, where today IS the as-of date. In a backtest it values
    a 1999 date with a beta regressed on 2021-2026 returns, which is look-ahead; it is also a
    network dependency and a rate-limit hazard. Measured on a 25-name probe it fired 157 times
    over 1,122 rows.

    This reproduces the ladder with rung 3 removed: an in-range point-in-time beta is used
    (rung 2), and anything else falls to the engine's OWN stated constant (rung 4) — which is
    exactly where the ladder lands when corroboration cannot run.
    """
    from .wacc import BETA_FALLBACK, BETA_HIGH_CAP, BETA_LOW_TRIGGER
    b = pit_beta
    if b is not None and b == b and 0 < b <= BETA_HIGH_CAP and b > BETA_LOW_TRIGGER:
        return float(b)
    return float(BETA_FALLBACK)


def lean_fair_value(cd: CompanyData, cfg=CONFIG, with_reverse=True, beta_override=None,
                    with_scenarios=False) -> dict:
    """The blended fair value for one company, by the same path as the website.

    Mirrors pipeline.value_from_company exactly up to `blend.value`; Monte Carlo,
    sensitivity and scoring are omitted because none of them can change it (pinned by
    test_lean_path_matches_the_full_pipeline). The reverse DCF does not change it
    either, but it IS the growth-name headline, so it is computed when asked for.

    S10 — `with_scenarios=True` additionally returns the blended bear/bull band as
    `bear_value` / `bull_value`, the same pair the live pipeline stores as
    `blend.value_low` / `blend.value_high` and the site renders as the scenario card.
    It is OPT-IN, so with the default every caller (including S23's) is unchanged and
    bit-identical; pinned by test_s10_the_scenario_band_is_opt_in_and_changes_nothing.
    """
    cls = classify(cd)
    # S23 — `beta_override` defaults to None, so the live path is unchanged. A point-in-time
    # caller passes `offline_beta(pit_beta)` and the ladder never reaches its network rung.
    w = compute_wacc(cd, cfg, beta_override=beta_override)
    wacc_value = w.wacc
    base = build_base_assumptions(cd, cls, w.risk_free, cfg)

    dcf_ps = run_dcf(cd, base, wacc_value).per_share
    if cls.regime == "financial":
        fin = financial_scenarios(cd, w.cost_of_equity, base.terminal_growth)
        dcf_ps = fin[1] if fin else None

    comps = compute_comps(cd)
    maturity, parts = maturity_from_company(cd, growth=cls.blended_growth)
    mature_rate = mature_discount_rate(w.risk_free, w.erp, wacc_value)
    gl = (None if cls.regime == "financial"
          else growth_fair_value(cd, base, wacc_value, maturity, comps.benchmark,
                                 mature_rate=mature_rate))
    rev = reverse_dcf(cd, base, wacc_value) if with_reverse else None

    blend = blended_fair_value(cd, cls, dcf_ps, comps.comps_fair_value, reverse=rev,
                               growth_value=(gl.value if gl is not None else None),
                               maturity=maturity, maturity_parts=parts, quiet=True)

    price = cd.price
    fv = blend.value if blend.valuable else None
    out = {
        "fair_value": fv,
        "gap": (math.log(fv / price) if (fv and price and price > 0 and fv > 0) else None),
        "upside": (fv / price - 1.0) if (fv and price and price > 0) else None,
        "maturity": blend.maturity, "regime": cls.regime, "method": blend.method,
        "growth_led": bool(blend.growth_led), "confidence": blend.confidence,
        "valuable": bool(blend.valuable),
        "dcf_ps": dcf_ps, "comps_fv": comps.comps_fair_value,
        "growth_ps": (gl.value if gl is not None else None),
        "wacc": wacc_value, "beta": w.beta,
        "implied_growth": (getattr(rev, "implied_avg_growth", None) if rev else None),
        "base_growth": (getattr(rev, "base_avg_growth", None) if rev else None),
        "implied_bounded": (getattr(rev, "implied_growth_bounded", "") if rev else ""),
        "ev_ebitda_used": ("ev_ebitda" in (comps.implied or {})),
        "ev_sales_used": ("ev_sales" in (comps.implied or {})),
    }
    # S10 — the keys are added ONLY when asked for, so the default return dict is
    # identical key-for-key to what every existing caller already receives.
    if with_scenarios:
        band = _scenario_band(cd, cls, base, wacc_value, comps, rev, maturity, parts,
                              mature_rate, w.cost_of_equity)
        out["bear_value"], out["bull_value"] = band.get("bear"), band.get("bull")
    return out


def _scenario_band(cd, cls, base, wacc_value, comps, rev, maturity, parts,
                   mature_rate, cost_of_equity) -> dict:
    """The blended bear/base/bull band — the SAME object the site shows on its scenario card.

    `_blend_scenarios` is IMPORTED from the live pipeline, never re-implemented here. A second
    copy would be free to drift from the number the reader is shown, which is precisely audit
    B7's defect class ("no shipped code path reproduces the backtested composite exactly").
    Pinned by test_s10_the_band_uses_the_SHIPPED_blend_scenarios.
    """
    from .growth import build_growth_scenarios
    from .pipeline import _blend_scenarios
    from .scenarios import build_scenarios

    scen = build_scenarios(cd, cls, base, wacc_value)
    # Banks/insurers: the live pipeline REPLACES the per-share cone with the justified
    # P/B-ROE model before blending, and `lean_fair_value` already does the equivalent for
    # the base case. Without this the band would be DCF-derived while its own base is not.
    if cls.regime == "financial":
        fin = financial_scenarios(cd, cost_of_equity, base.terminal_growth)
        if fin:
            scen.bear.per_share, scen.base.per_share, scen.bull.per_share = fin
    gscn = ({} if cls.regime == "financial"
            else build_growth_scenarios(cd, cls, base, wacc_value, maturity,
                                        comps.benchmark, mature_rate=mature_rate))
    return _blend_scenarios(cd, cls, scen, comps, rev, gscn, maturity, parts)


# --------------------------------------------------------------------------- #
# Panel construction
# --------------------------------------------------------------------------- #

def _beta_at(closes, benchv, i, window=120) -> Optional[float]:
    """Point-in-time beta — the same 120-day regression the factor panel uses.

    Kept in numpy rather than the panel's Python loops purely for scale: this runs once
    per (date, ticker), and converting an ~6,800-day price array to a list each time is
    two orders of magnitude more work than the regression itself.
    """
    if benchv is None or i < window:
        return None
    s = np.asarray(closes[max(0, i - window):i + 1], dtype=float)
    b = np.asarray(benchv[max(0, i - window):i + 1], dtype=float)
    n = min(len(s), len(b))
    if n < 41:
        return None
    s, b = s[:n], b[:n]
    ok = (s[:-1] > 0) & (b[:-1] > 0) & (s[1:] > 0) & (b[1:] > 0)
    if ok.sum() < 40:
        return None
    sr = s[1:][ok] / s[:-1][ok] - 1.0
    br = b[1:][ok] / b[:-1][ok] - 1.0
    varb = float(((br - br.mean()) ** 2).sum())
    if varb <= 0:
        return None
    return float(((br - br.mean()) * (sr - sr.mean())).sum() / varb)


def s25_repair_sectors(sector_map, ticker, as_of, base_sector):
    """S25's repair decision, in ONE place. Returns `(sector_a, sector_b, state, pit)`.

    `sector_a` is REPAIR-A (CHANGE-ONLY, the register's PRIMARY): the dated sector ONLY where
    GICS records a reclassification between `as_of` and today. The crosswalk's own vendor
    disagreement cancels by construction, so what moves is look-ahead and nothing else.

    `sector_b` is REPAIR-B (FULL): the dated sector wherever it is known. It fixes look-ahead
    AND switches taxonomy in one step, so it is CONFOUNDED by construction and carries no
    verdict.

    **A NON-OK LOOKUP RETURNS `base_sector` AND NEVER A BLANK, in both arms.** Both engine
    dicts fail open — `SECTOR_TARGET_MARGIN.get(s, 0.12)` and `SECTOR_MULTIPLES.get(s,
    _DEFAULT)` — so blanking an unknown sector silently hands the row the middle of a 2.70x
    range. **A refusal that blanks is not an abstention; it is a vote.** The state travels
    back separately so a caller can COUNT the refusals instead of inferring them from a gap.

    Kept as one function rather than inlined so it can be tested without building a panel,
    and so there is exactly one definition of the rule (`B7`).
    """
    at = sector_map.at(ticker, as_of)
    now = sector_map.current(ticker)
    state, pit = at.get("state"), at.get("sector")
    ok_at = (state == "OK" and pit)
    ok_now = (now.get("state") == "OK" and now.get("sector"))

    sec_a = base_sector
    if ok_at and ok_now and pit != now["sector"]:
        sec_a = pit
    sec_b = pit if ok_at else base_sector
    return sec_a, sec_b, state, pit


def build_valuation_panel(provider, tickers, benchmark="SPY", rebalance_days=63,
                          lookback_years=18, horizon=63, progress=True,
                          risk_free=None, offline=False,
                          with_scenarios=False, sector_map=None) -> pd.DataFrame:
    """Point-in-time fair value + forward return per (date, ticker).

    Same calendar, same delisting mask and same forward-return convention as
    build_fundamental_panel, so the numbers this produces are directly comparable to
    the factor ICs rather than merely similar-looking.

    **`sector_map` IS S25's LOOK-AHEAD REPAIR AND IT IS OPT-IN AND ADDITIVE.** The sector
    reaching `pit_company` is TODAY's, from the TICKERS snapshot, and it selects
    `SECTOR_TARGET_MARGIN` across a 2.70x range and `SECTOR_MULTIPLES` — so a 2009 valuation
    is scored against a 2026 classification. Passing a dated map (anything exposing
    `at(ticker, as_of)` and `current(ticker)`) adds `*_a` and `*_b` columns carrying the
    repaired valuation BESIDE the incumbent one. **With `sector_map=None` this function is
    bit-identical to what it was**, pinned by test, because adopting a repair is a VINTAGE
    EVENT and is not this parameter's decision to make.

    **IT IS DUCK-TYPED ON PURPOSE.** The map lives in `valuation/edge/`, and an engine module
    importing it would put a study-side dependency on the live valuation path. Nothing is
    imported here; the caller passes the object.

    **A NON-OK LOOKUP KEEPS THE PANEL'S OWN SECTOR AND NEVER BLANKS IT.** Both engine dicts
    FAIL OPEN — `.get(sector, 0.12)` and `.get(sector, _DEFAULT)` — so an empty sector is
    silently handed the middle of the range. **A refusal that blanks the sector is not
    neutral; it is a vote.** The state is recorded in `sector_state` so it can be counted.
    """
    import sys
    import time
    TD = 252
    t0 = time.time()

    def prog(msg):
        if progress:
            print(f"[calib] {time.time() - t0:6.0f}s  {msg}", file=sys.stderr, flush=True)

    # AUDIT B6, APPLIED HERE TOO (S23). This function used to request
    # `days=TD*lookback_years + horizon + 60`, which takes the PER-TICKER tail — the exact
    # route `data_providers.price_history` says in its own comment "is never the panel's route
    # now". The consequence is B6's: the union calendar's early cross-sections consist only of
    # names that stopped trading before the window closed, and measured on a 25-name probe this
    # produced 110 rebalance dates starting 1998-12-31 against the corrected factor panel's 69
    # from 2008-01-16. `days=None` asks for the WHOLE series and the SHARED calendar is cut once
    # below, so every ticker is cut at the same DATE and this panel lands on the factor panel's
    # own dates (pinned by S23's control C1).
    _CAL_DAYS = TD * lookback_years + horizon + 60

    def series(t):
        d, c = provider.price_history(t, days=None)
        return pd.Series(c, index=pd.to_datetime(d)) if (d and c and len(c) > TD) else None

    bench = series(benchmark)
    if bench is None or len(bench) < TD + horizon:
        try:
            from ..screener.prices import close_series
            d, c = close_series(benchmark, days=TD * lookback_years + horizon + 200)
            if d and c and len(c) > TD:
                bench = pd.Series(c, index=pd.to_datetime(d))
        except Exception:
            pass
    if bench is None or len(bench) < TD + horizon:
        print(f"[calib] benchmark '{benchmark}' unavailable — cannot build the panel.",
              file=sys.stderr)
        return pd.DataFrame()

    prog(f"loading price + fundamentals for {len(tickers)} tickers")
    px, prep, dly, meta = {}, {}, {}, {}
    for i, t in enumerate(tickers):
        if i and i % 500 == 0:
            prog(f"  loaded {i}/{len(tickers)}, {len(px)} usable")
        s = series(t)
        if s is None or len(s) <= TD + horizon:
            continue
        px[t] = s
        prep[t] = _prep_fundamentals(provider.fundamentals_history(t))
        dly[t] = provider.daily_history(t) if hasattr(provider, "daily_history") else []
        meta[t] = provider.ticker_meta(t) if hasattr(provider, "ticker_meta") else {}
    if not px:
        return pd.DataFrame()

    frame = pd.DataFrame(px).sort_index().ffill()
    # Survivorship: blank each name after its delisting so ffill can't keep it "trading"
    # flat forever and contribute a fake 0% forward return for the next decade.
    try:
        delisted = (provider.delisted_map() or {}) if hasattr(provider, "delisted_map") else {}
    except Exception:
        delisted = {}
    for t in frame.columns:
        dd = delisted.get(str(t).upper())
        if dd:
            m = frame.index > pd.to_datetime(dd)
            if m.any():
                frame.loc[m, t] = np.nan

    # AUDIT B6 — cut the shared CALENDAR once, after the frame is built, so every ticker is
    # cut at the same date. This is the same cut `build_fundamental_panel` makes, which is what
    # puts the two panels on identical rebalance dates.
    if _CAL_DAYS and len(frame.index) > _CAL_DAYS:
        frame = frame.iloc[-_CAL_DAYS:]

    cal = frame.index
    benchf = bench.reindex(cal).ffill()
    benchv = benchf.values.tolist()
    idx = list(range(TD, len(cal) - horizon, rebalance_days))
    prog(f"{len(px)} usable tickers, scoring {len(idx)} rebalance dates")

    # A swallowed exception is how a factor ends up "measured" on half the universe with
    # nothing to show it. These are counted and printed rather than passed over, so a
    # systematic failure (one sector, one era, one missing column) is visible as a number.
    rows, n_failed, n_no_company, first_errors = [], 0, 0, []
    for di, i in enumerate(idx):
        as_of = str(cal[i].date())
        if di and di % 10 == 0:
            prog(f"  rebalance {di}/{len(idx)} ({as_of}), {len(rows):,} rows")
        b0, b1 = benchf.iloc[i], benchf.iloc[i + horizon]
        bret = (b1 / b0 - 1.0) if (b0 and b0 > 0) else np.nan
        for t in px:
            closes = frame[t].values
            p = closes[i]
            if p != p or p <= 0:
                continue
            d = _daily_at(dly.get(t), as_of)
            if not (d and d[0]):
                continue                       # no point-in-time market cap -> skip
            mc = float(d[0]) * 1e6
            md = meta.get(t) or {}
            _pit_beta = _beta_at(closes, benchv, i)
            cd = pit_company(t, prep.get(t), as_of, float(p), mc,
                             sector=md.get("sector") or "",
                             industry=md.get("industry") or "",
                             beta=_pit_beta,
                             risk_free=risk_free)
            if cd is None:
                n_no_company += 1
                continue
            try:
                # S23 — `offline=True` pins the beta point-in-time so the ladder cannot reach
                # its network rung and fetch TODAY'S prices for a historical valuation.
                v = lean_fair_value(cd, beta_override=(offline_beta(_pit_beta) if offline
                                                       else None),
                                    with_scenarios=with_scenarios)
            except Exception as e:               # counted, never silent — see below
                n_failed += 1
                if len(first_errors) < 5:
                    first_errors.append(f"{t} {as_of}: {type(e).__name__}: {e}")
                continue

            end = closes[i + horizon]
            if end != end:                     # delisted mid-window -> realize the last print
                seg = closes[i + 1:i + horizon + 1]
                valid = seg[~np.isnan(seg)] if len(seg) else seg
                end = float(valid[-1]) if len(valid) else np.nan
            if end != end:
                continue

            row = {"date": as_of, "ticker": t, "sector": cd.sector, "price": float(p),
                   "market_cap": mc, "fwd_ret": float(end / p - 1.0),
                   "bench_ret": (float(bret) if bret == bret else np.nan),
                   "revenue": cd.revenue, "rev_growth": cd.rev_growth_ttm,
                   "op_margin": cd.ebit_margin, "fcf_margin": cd.fcf_margin,
                   "net_debt": cd.net_debt,
                   # For the P7/P8 sanity layer: foreign reporters were the subgroup the
                   # currency bug pushed to the top of every value ranking, so their share
                   # of the widest-discount decile is the direct test for a repeat.
                   "is_adr": ("ADR" in str(md.get("category") or "").upper())}
            row.update(v)
            row["realized_growth"] = _realized_growth(prep.get(t), as_of)

            # ---- S25: the look-ahead repair, measured beside the incumbent, never instead
            if sector_map is not None:
                base_sector = cd.sector
                sec_a, sec_b, _state, _pit = s25_repair_sectors(
                    sector_map, t, as_of, base_sector)
                row["sector_state"] = _state
                row["sector_pit"] = _pit

                for tag, sec in (("a", sec_a), ("b", sec_b)):
                    if sec == base_sector:
                        # Nothing moved; copy rather than re-value. Same numbers, less work.
                        row["fair_value_" + tag] = v.get("fair_value")
                        row["regime_" + tag] = v.get("regime")
                        row["method_" + tag] = v.get("method")
                        row["sector_" + tag] = base_sector
                        row["revalued_" + tag] = False
                        continue
                    row["sector_" + tag] = sec
                    row["revalued_" + tag] = True
                    cd2 = pit_company(t, prep.get(t), as_of, float(p), mc,
                                      sector=sec,
                                      industry=md.get("industry") or "",
                                      beta=_pit_beta, risk_free=risk_free)
                    if cd2 is None:
                        row["fair_value_" + tag] = None
                        row["regime_" + tag] = None
                        row["method_" + tag] = None
                        continue
                    try:
                        v2 = lean_fair_value(
                            cd2,
                            beta_override=(offline_beta(_pit_beta) if offline else None),
                            with_scenarios=with_scenarios)
                    except Exception:
                        # Counted the same way the base valuation is: a repaired row that
                        # raises is a hole in the repair, not a silent pass-through.
                        row["fair_value_" + tag] = None
                        row["regime_" + tag] = None
                        row["method_" + tag] = None
                        continue
                    row["fair_value_" + tag] = v2.get("fair_value")
                    row["regime_" + tag] = v2.get("regime")
                    row["method_" + tag] = v2.get("method")

            rows.append(row)
    prog(f"done: {len(rows):,} rows · {n_no_company:,} (date, ticker) pairs had no usable "
         f"point-in-time company (no TTM / no market cap) · {n_failed:,} valuations raised")
    for e in first_errors:
        prog(f"  first errors: {e}")
    return pd.DataFrame(rows)


def _realized_growth(prep, as_of, years=REALIZED_GROWTH_YEARS):
    """Revenue CAGR actually delivered over the next `years`. LOOK-AHEAD BY DESIGN.

    Used only to ask whether the market-implied growth was ever borne out — a diagnostic,
    never an input to anything ranked or traded.

    Both endpoints are TTM revenue in the RAW reporting currency: the FX divisor cancels
    in a growth ratio, so converting first would add a rounding step and no accuracy. The
    CAGR is annualized over the ACTUAL elapsed time between the two filings, and the row
    is dropped unless a filing genuinely exists near the far end — otherwise a company
    whose history stops early gets its 1-year growth reported as if it were 3-year.
    """
    if not prep:
        return None
    ts = pd.Timestamp(as_of)
    fut = str((ts + pd.Timedelta(days=365 * years)).date())
    if fut > prep[-1][0]:
        return None                            # that future hasn't happened in this export
    dk1, _row1, ttm1 = None, None, None
    for dk, row, ttm in reversed(prep):
        if dk <= fut:
            dk1, _row1, ttm1 = dk, row, ttm
            break
    dk0, ttm0 = None, None
    for dk, _row, ttm in reversed(prep):
        if dk <= as_of:
            dk0, ttm0 = dk, ttm
            break
    if not (ttm0 and ttm1 and dk0 and dk1):
        return None
    r0, r1 = ttm0.get("revenue"), ttm1.get("revenue")
    if not r0 or r0 <= 0 or not r1 or r1 <= 0:
        return None
    elapsed = (pd.Timestamp(dk1) - pd.Timestamp(dk0)).days / 365.25
    if elapsed < years * 0.75:                 # the far filing isn't actually far enough out
        return None
    return (r1 / r0) ** (1.0 / elapsed) - 1.0


# --------------------------------------------------------------------------- #
# Measurement — same conventions as the factor research
# --------------------------------------------------------------------------- #

def _spearman(a, b) -> float:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 3:
        return float("nan")
    return float(pd.Series(a[ok]).corr(pd.Series(b[ok]), method="spearman"))


def coverage_report(panel) -> dict:
    """What fraction of rows actually HAS each input. Read this before any IC.

    Five wired factors in this project were blank in 100% of rows for its entire history
    and nothing surfaced it, because an empty column raises no error — it just quietly
    contributes nothing. Coverage is the first thing printed, not a footnote.
    """
    if panel is None or panel.empty:
        return {"rows": 0}
    n = float(len(panel))
    cols = ["fair_value", "gap", "dcf_ps", "comps_fv", "growth_ps", "maturity",
            "implied_growth", "realized_growth", "rev_growth", "op_margin", "net_debt",
            "beta", "revenue"]
    out = {"rows": int(n), "dates": int(panel["date"].nunique()),
           "names": int(panel["ticker"].nunique()),
           "coverage": {c: round(float(panel[c].notna().mean()), 4)
                        for c in cols if c in panel.columns}}
    out["valuable_frac"] = round(float(panel["valuable"].mean()), 4) if "valuable" in panel else None
    out["growth_led_frac"] = round(float(panel["growth_led"].mean()), 4) if "growth_led" in panel else None
    if "ev_ebitda_used" in panel:
        out["ev_ebitda_used_frac"] = round(float(panel["ev_ebitda_used"].mean()), 4)
    if "ev_sales_used" in panel:
        out["ev_sales_used_frac"] = round(float(panel["ev_sales_used"].mean()), 4)
    if "regime" in panel:
        out["regime_mix"] = {k: round(v, 4) for k, v in
                             panel["regime"].value_counts(normalize=True).items()}
    below = [c for c, v in out["coverage"].items() if v < 0.05]
    if below:
        out["below_floor"] = below
    return out


def sanity_check(panel, col="gap", n_q=10, warn=True) -> dict:
    """Is the gap SANE, not merely present? (The P8 lesson, applied to this signal.)

    Coverage told us the currency-corrupted value ratios were 100% populated; what
    actually caught them was noticing WHICH names sat at the top. So this asks the same
    questions of the widest-discount decile:

      * are foreign reporters (ADRs) over-represented there? — the P7 signature, and the
        one subgroup this whole module could plausibly break the same way;
      * is it all one sector, or one maturity tier?
      * is its median market cap wildly different from the universe's? — a gap that only
        fires on micro-caps is a liquidity story, not a valuation one.

    Flags are for INVESTIGATING, not for silencing. Nothing here fails a run.
    """
    out = {"flags": []}
    if panel is None or panel.empty or col not in panel.columns:
        return {"status": "no data", "flags": []}
    sub = panel.dropna(subset=[col])
    if len(sub) < n_q * 10:
        return {"status": "too few rows", "flags": []}

    top = sub[sub.groupby("date")[col].rank(ascending=False, pct=True) <= 1.0 / n_q]
    bot = sub[sub.groupby("date")[col].rank(ascending=True, pct=True) <= 1.0 / n_q]
    out["top_decile_rows"] = int(len(top))

    if "is_adr" in sub.columns and sub["is_adr"].any():
        base = float(sub["is_adr"].mean())
        got = float(top["is_adr"].mean())
        out["adr_share_universe"] = round(base, 4)
        out["adr_share_top_decile"] = round(got, 4)
        out["adr_over_representation"] = round(got / base, 3) if base > 0 else None
        if base > 0 and got / base > 2.0:
            out["flags"].append(
                f"ADRs are {got / base:.2f}x over-represented in the widest-discount decile "
                f"({got:.1%} vs {base:.1%}) — the P7 currency signature. Investigate before "
                f"believing this gap.")

    if "market_cap" in sub.columns:
        mu, mt = float(sub["market_cap"].median()), float(top["market_cap"].median())
        out["median_mktcap_universe"] = mu
        out["median_mktcap_top_decile"] = mt
        if mu > 0 and (mt / mu < 0.34 or mt / mu > 3.0):
            out["flags"].append(
                f"The widest-discount decile's median market cap is {mt / mu:.2f}x the "
                f"universe's — the gap is picking a size bucket as much as a valuation.")

    for key in ("sector", "regime"):
        if key in top.columns and len(top):
            share = top[key].value_counts(normalize=True)
            if len(share):
                out[f"top_decile_{key}_top"] = {str(share.index[0]): round(float(share.iloc[0]), 3)}
                if float(share.iloc[0]) > 0.5:
                    out["flags"].append(
                        f"Over half the widest-discount decile is a single {key} "
                        f"({share.index[0]}, {share.iloc[0]:.0%}).")
    if "maturity" in top.columns:
        out["median_maturity_top_decile"] = round(float(top["maturity"].median()), 3)
        out["median_maturity_bottom_decile"] = round(float(bot["maturity"].median()), 3)

    if warn and out["flags"]:
        import sys
        for f in out["flags"]:
            print(f"[calib][sanity] {f}", file=sys.stderr)
    return out


def gap_ic(panel, col="gap", horizon_col="fwd_ret", min_names=MIN_NAMES_PER_DATE,
           min_dates=MIN_DATES) -> dict:
    """Per-date Spearman IC of the value/price gap against the forward return.

    Rank IC, so it is invariant to whether the gap is expressed as a ratio, a log ratio
    or a percentage upside — all three give an identical number by construction.
    """
    if panel is None or panel.empty or col not in panel.columns:
        return {"status": "no data"}
    ics, dates = [], []
    for d, sub in panel.groupby("date"):
        ss = sub.dropna(subset=[col, horizon_col])
        if len(ss) < min_names:
            continue
        ic = _spearman(ss[col].values, ss[horizon_col].values)
        if ic == ic:
            ics.append(ic)
            dates.append(d)
    if len(ics) < min_dates:
        return {"status": f"insufficient dates ({len(ics)})", "n_dates": len(ics)}
    a = np.asarray(ics, dtype=float)
    sd = float(a.std(ddof=1))
    return {"n_dates": len(a), "mean_ic": float(a.mean()), "median_ic": float(np.median(a)),
            "ic_tstat": (float(a.mean() / (sd / math.sqrt(len(a)))) if sd > 0 else 0.0),
            "ic_positive_frac": float((a > 0).mean()),
            "coverage": float(panel[col].notna().mean()),
            "first_date": min(dates), "last_date": max(dates)}


def gap_quantiles(panel, col="gap", n_q=10, horizon=63, min_names=None) -> dict:
    """Decile spread on the gap, highest-upside bucket first.

    `monotonicity` follows this project's existing convention (quantile_backtest):
    buckets are ordered BEST-FIRST, so -1.0 is perfectly ordered and +1.0 is backwards.
    """
    if panel is None or panel.empty or col not in panel.columns:
        return {"status": "no data"}
    min_names = min_names if min_names is not None else n_q * 3
    q_rets = [[] for _ in range(n_q)]
    ls, ew = [], []
    for _d, sub in panel.groupby("date"):
        ss = sub.dropna(subset=[col, "fwd_ret"])
        if len(ss) < min_names:
            continue
        g, fwd = ss[col].values, ss["fwd_ret"].values
        order = np.argsort(-g)                       # widest discount (highest gap) first
        buckets = np.array_split(order, n_q)
        for qi, b in enumerate(buckets):
            if len(b):
                q_rets[qi].append(float(np.mean(fwd[b])))
        ls.append(float(np.mean(fwd[buckets[0]]) - np.mean(fwd[buckets[-1]])))
        ew.append(float(np.mean(fwd)))
    if len(ls) < 4:
        return {"status": f"insufficient periods ({len(ls)})"}
    ppy = 252.0 / horizon

    def ann(s):
        return float(np.mean(s) * ppy) if s else None

    def tstat(s):
        s = np.asarray(s, dtype=float)
        sd = float(np.std(s, ddof=1)) if len(s) > 1 else 0.0
        return float(np.mean(s) / (sd / math.sqrt(len(s)))) if sd > 0 else None

    dec = [ann(q) for q in q_rets]
    ew_ann = ann(ew)
    mono = _spearman(np.arange(n_q, dtype=float),
                     np.array([np.mean(q) if q else np.nan for q in q_rets]))
    # t-stat on the top bucket's EXCESS over the equal-weight universe, period by period.
    # An annualized alpha with no t-stat beside it is the easiest number in this project to
    # over-read: the long-short t and the top-decile alpha can point opposite ways, and when
    # they do it is the t-stats that settle it.
    top_ex = [a - b for a, b in zip(q_rets[0], ew)] if q_rets[0] else []
    return {"n_periods": len(ls), "n_quantiles": n_q,
            "top_decile_alpha_tstat": tstat(top_ex) if len(top_ex) > 1 else None,
            "decile_ann_return": dec, "equal_weight_ann": ew_ann,
            "long_short_ann": ann(ls), "long_short_tstat": tstat(ls),
            "long_short_hit": float(np.mean([1.0 if x > 0 else 0.0 for x in ls])),
            "top_decile_alpha": (None if dec[0] is None or ew_ann is None else dec[0] - ew_ann),
            "bottom_decile_alpha": (None if dec[-1] is None or ew_ann is None else dec[-1] - ew_ann),
            "monotonicity": (None if mono != mono else float(mono))}


def by_maturity(panel, col="gap", n_q=5, horizon=63, tiers=MATURITY_TIERS) -> dict:
    """The real question: does the gap work on mature names, growth names, or neither?

    Deciles inside a tier would be built from a few dozen names, so this uses quintiles
    and reports the IC alongside — the IC uses the whole tier and is the more reliable
    of the two here.
    """
    out = {}
    if panel is None or panel.empty or "maturity" not in panel.columns:
        return out
    for name, lo, hi in tiers:
        sub = panel[(panel["maturity"] >= lo) & (panel["maturity"] < hi)]
        out[name] = {"bounds": [lo, hi], "rows": int(len(sub)),
                     "share_of_panel": (round(len(sub) / len(panel), 4) if len(panel) else None),
                     "ic": gap_ic(sub, col=col),
                     "quantiles": gap_quantiles(sub, col=col, n_q=n_q, horizon=horizon,
                                                min_names=n_q * 4)}
    # The growth-led cut is what the UI actually branches on, so report it directly too.
    if "growth_led" in panel.columns:
        gl = panel[panel["growth_led"].astype(bool)]
        out["growth_led"] = {"rows": int(len(gl)), "ic": gap_ic(gl, col=col),
                             "quantiles": gap_quantiles(gl, col=col, n_q=n_q, horizon=horizon,
                                                        min_names=n_q * 4)}
    return out


def nonoverlapping_check(panel, col="gap", horizon=63, rebalance_days=63, n_q=10) -> dict:
    """Re-measure using only NON-OVERLAPPING forward windows.

    A 252-day forward return sampled every 63 days overlaps the next three observations.
    The IC series is then autocorrelated by construction, and the t-stat — which assumes
    independent draws — is inflated by roughly sqrt(overlap), i.e. about 2x at a 4x
    overlap. That is large enough to turn "nothing" into "significant", so it cannot be
    left as a footnote.

    Taking every `horizon/rebalance_days`-th date restores independence exactly (it is the
    same thing as having run the panel at that rebalance frequency). Doing it at each
    possible OFFSET and reporting all of them costs nothing extra and shows whether the
    answer depends on which dates happen to be picked — a single subsample would just be
    trading one arbitrary choice for another.
    """
    if panel is None or panel.empty:
        return {}
    stride = max(1, int(round(horizon / max(1, rebalance_days))))
    if stride <= 1:
        return {"stride": 1, "note": "windows already non-overlapping"}
    dates = sorted(panel["date"].unique())
    out = {"stride": stride, "n_dates_full": len(dates), "offsets": {}}
    for off in range(stride):
        keep = set(dates[off::stride])
        sub = panel[panel["date"].isin(keep)]
        out["offsets"][str(off)] = {
            "n_dates": len(keep),
            "ic": gap_ic(sub, col=col, min_dates=4),
            "quantiles": gap_quantiles(sub, col=col, n_q=n_q, horizon=horizon)}
    ts = [o["ic"].get("ic_tstat") for o in out["offsets"].values()
          if not o["ic"].get("status")]
    ls = [o["quantiles"].get("long_short_tstat") for o in out["offsets"].values()
          if not o["quantiles"].get("status")]
    al = [o["quantiles"].get("top_decile_alpha_tstat") for o in out["offsets"].values()
          if not o["quantiles"].get("status")]
    out["ic_tstat_range"] = [min(ts), max(ts)] if ts else None
    out["long_short_tstat_range"] = ([min(x for x in ls if x is not None),
                                      max(x for x in ls if x is not None)]
                                     if any(x is not None for x in ls) else None)
    out["top_decile_alpha_tstat_range"] = ([min(x for x in al if x is not None),
                                           max(x for x in al if x is not None)]
                                          if any(x is not None for x in al) else None)
    return out


def control_factors(panel, horizon=63) -> dict:
    """POSITIVE CONTROL: measure two plain value factors on the SAME rows.

    A null result on the fair-value gap is only worth reporting if the measurement can
    find a signal that is known to be there. `ebit_ev` and `neg_ev_sales` are both live
    inputs to this project's `value` theme and have been measured independently by the
    factor panel, so they are the natural check: if they show their usual weak-positive
    IC here and the gap shows nothing, the null is about the gap. If THEY come out null
    too, the harness is broken and nothing in this module should be believed.

    Both are derived from columns the panel already carries, so this costs no rebuild:
        EBIT      = op_margin x revenue            EV = market cap + net debt
    """
    if panel is None or panel.empty:
        return {}
    p = panel.copy()
    if not {"op_margin", "revenue", "market_cap", "net_debt"} <= set(p.columns):
        return {"status": "columns missing"}
    ev = p["market_cap"] / 1e6 + p["net_debt"]        # market_cap is $, the rest are $mm
    ev = ev.where(ev > 0)
    p["ebit_ev"] = (p["op_margin"] * p["revenue"]) / ev
    p["neg_ev_sales"] = -(ev / p["revenue"].where(p["revenue"] > 0))
    return {k: {"ic": gap_ic(p, col=k),
                "quantiles": gap_quantiles(p, col=k, horizon=horizon)}
            for k in ("ebit_ev", "neg_ev_sales")}


def by_size(panel, col="gap", n_q=5, horizon=63, n_tiers=3) -> dict:
    """Is the gap a VALUATION signal or a size proxy?

    The widest-discount decile comes out materially smaller-cap than the universe, and
    small caps have their own well-documented return premium (and their own costs). If
    the gap only works across the size spectrum and vanishes inside each tier, then what
    it is really ranking is market cap wearing a valuation's clothes.

    Tiers are formed WITHIN each date, so a tier means the same thing in 2001 as in 2025
    rather than drifting with the whole market's capitalization.
    """
    out = {}
    if panel is None or panel.empty or "market_cap" not in panel.columns:
        return out
    p = panel.dropna(subset=["market_cap"]).copy()
    p["_tier"] = p.groupby("date")["market_cap"].transform(
        lambda s: pd.qcut(s.rank(method="first"), n_tiers, labels=False, duplicates="drop"))
    names = {0: "small", 1: "mid", 2: "large"} if n_tiers == 3 else {}
    for tier, sub in p.groupby("_tier"):
        if sub.empty:
            continue
        out[names.get(int(tier), f"tier{int(tier)}")] = {
            "rows": int(len(sub)),
            "median_mktcap": float(sub["market_cap"].median()),
            "ic": gap_ic(sub, col=col),
            "quantiles": gap_quantiles(sub, col=col, n_q=n_q, horizon=horizon,
                                       min_names=n_q * 4)}
    return out


def half_split(panel, col="gap", n_q=10, horizon=63) -> dict:
    """The same measurement on each half of the history, reported separately.

    Not a held-out TEST (nothing here was fitted, so there is nothing to hold out) —
    it is a stability check. A gap that only works in one half is a period effect, and
    this project has already been burned by treating one period's IC as a property
    (`size` flips t +3.17 -> -0.67 across exactly this split).
    """
    if panel is None or panel.empty:
        return {}
    dates = sorted(panel["date"].unique())
    if len(dates) < 2 * MIN_DATES:
        return {"status": f"only {len(dates)} dates"}
    cut = dates[len(dates) // 2]
    out = {}
    for label, mask in (("first_half", panel["date"] < cut), ("second_half", panel["date"] >= cut)):
        sub = panel[mask]
        out[label] = {"dates": [str(sub['date'].min()), str(sub['date'].max())],
                      "ic": gap_ic(sub, col=col),
                      "quantiles": gap_quantiles(sub, col=col, n_q=n_q, horizon=horizon)}
    return out


def implied_growth_realization(panel, years=REALIZED_GROWTH_YEARS) -> dict:
    """Did the growth the price implied actually show up?

    Only meaningful on growth-led names (elsewhere the implied-growth read isn't the
    headline). Reports the median implied vs median realized, how often reality cleared
    the bar, and the rank correlation between the two — the last being the question that
    matters: even if the LEVEL is always too high, does a higher implied growth at least
    identify a faster-growing company?

    ONE-SIDED COMPARISON, stated so nobody has to rediscover it: `implied_avg_growth` is
    the average over the DCF's whole forecast (5 years for a mature name, 10 for a
    hypergrowth one) while `realized_growth` covers the FIRST 3. Because the growth path
    fades, those first three years are the fastest ones — so this comparison is tilted in
    the COMPANY's favour. A low "met or beat" rate measured this way is therefore a floor
    on how demanding the implied number is, not an exaggeration of it.
    """
    if panel is None or panel.empty:
        return {"status": "no data"}
    need = ["implied_growth", "realized_growth"]
    if any(c not in panel.columns for c in need):
        return {"status": "columns missing"}

    def stats(sub, label):
        ss = sub.dropna(subset=need)
        if len(ss) < 30:
            return {"label": label, "n": int(len(ss)), "status": "too few rows"}
        imp, real = ss["implied_growth"].values, ss["realized_growth"].values
        bounded = (ss["implied_bounded"] == "above").mean() if "implied_bounded" in ss else None
        return {"label": label, "n": int(len(ss)),
                "median_implied": float(np.median(imp)),
                "median_realized": float(np.median(real)),
                "median_shortfall": float(np.median(real - imp)),
                "frac_realized_at_or_above_implied": float((real >= imp).mean()),
                "rank_corr_implied_vs_realized": _spearman(imp, real),
                "frac_solver_bounded_above": (None if bounded is None else float(bounded)),
                "horizon_years": years}

    out = {"all": stats(panel, "all names")}
    if "growth_led" in panel.columns:
        out["growth_led"] = stats(panel[panel["growth_led"].astype(bool)], "growth-led names")
        out["not_growth_led"] = stats(panel[~panel["growth_led"].astype(bool)], "everything else")
    return out


def spot_checks(panel, per_tier=3) -> dict:
    """A few real (date, ticker) rows per archetype, so the blend can be eyeballed
    across the whole spectrum rather than trusted from summary statistics."""
    out = {}
    if panel is None or panel.empty:
        return out
    groups = {"financial": panel[panel["regime"] == "financial"] if "regime" in panel else None}
    if "maturity" in panel.columns:
        groups["established"] = panel[(panel["maturity"] >= 0.65) & (panel["regime"] != "financial")]
        groups["deep_growth"] = panel[(panel["maturity"] < 0.35) & (panel["regime"] != "financial")]
    for name, sub in groups.items():
        if sub is None or sub.empty:
            continue
        take = sub.sort_values(["date", "ticker"]).iloc[:: max(1, len(sub) // per_tier)][:per_tier]
        out[name] = [{"date": r["date"], "ticker": r["ticker"], "price": round(r["price"], 2),
                      "fair_value": (None if r["fair_value"] != r["fair_value"]
                                     else round(r["fair_value"], 2)),
                      "method": r["method"], "maturity": r["maturity"],
                      "confidence": r["confidence"]}
                     for _i, r in take.iterrows()]
    return out


def run_calibration(provider, tickers, rebalance_days=63, horizon=63, lookback_years=18,
                    panel=None, risk_free=None) -> dict:
    """Everything above, in the order the conclusions should be read in."""
    if panel is None:
        panel = build_valuation_panel(provider, tickers, rebalance_days=rebalance_days,
                                      lookback_years=lookback_years, horizon=horizon,
                                      risk_free=risk_free)
    if panel is None or panel.empty:
        return {"status": "empty panel"}
    return {
        "universe": {"names": int(panel["ticker"].nunique()),
                     "dates": int(panel["date"].nunique()), "rows": int(len(panel)),
                     "horizon_days": horizon, "rebalance_days": rebalance_days,
                     "risk_free_override": risk_free},
        "coverage": coverage_report(panel),          # FIRST — see the COVERAGE RULE
        "sanity": sanity_check(panel),               # SECOND — present is not the same as sane
        "gap_ic": gap_ic(panel),
        "gap_quantiles": gap_quantiles(panel, horizon=horizon),
        "nonoverlapping": nonoverlapping_check(panel, horizon=horizon,
                                               rebalance_days=rebalance_days),
        "controls": control_factors(panel, horizon=horizon),
        "by_maturity": by_maturity(panel, horizon=horizon),
        "by_size": by_size(panel, horizon=horizon),
        "half_split": half_split(panel, horizon=horizon),
        "implied_growth": implied_growth_realization(panel),
        "spot_checks": spot_checks(panel),
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _fmt(x, p="+.2%"):
    return "n/a" if x is None or (isinstance(x, float) and x != x) else format(x, p)


def main(argv=None):
    import argparse
    import json
    import sys
    from .. import config as _cfgmod
    from ..edge.data_providers import WRDSProvider, get_historical_provider

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(
        description="Does the fair-value gap predict forward returns?")
    ap.add_argument("--data-dir", default=None, help="local Sharadar export directory")
    ap.add_argument("--limit", type=int, default=CONFIG.backtest_universe_limit)
    ap.add_argument("--horizon", type=int, default=63)
    ap.add_argument("--rebalance-days", type=int, default=63)
    ap.add_argument("--lookback-years", type=int, default=18)
    ap.add_argument("--risk-free", type=float, default=None,
                    help="override the risk-free rate for every date. There is no historical "
                         "yield series on disk, so the engine otherwise uses one constant "
                         "across 18 years; re-run with 0.02 and 0.06 to check the conclusion "
                         "doesn't rest on that.")
    ap.add_argument("--json", default=None, help="write the full result JSON here")
    ap.add_argument("--panel-csv", default=None, help="also dump the raw panel here")
    ap.add_argument("--from-panel-csv", default=None,
                    help="re-measure a panel dumped earlier instead of rebuilding it "
                         "(the build is ~8 minutes; the statistics are seconds)")
    args = ap.parse_args(argv)

    if args.from_panel_csv:
        panel = pd.read_csv(args.from_panel_csv)
        res = run_calibration(None, None, horizon=args.horizon,
                              rebalance_days=args.rebalance_days, panel=panel)
        _report(res, args, smoke=False)
        return 0

    if args.data_dir:
        class _C:
            wrds_data_dir = args.data_dir
        prov = WRDSProvider(_C())
    else:
        prov = get_historical_provider(CONFIG)
    ok, msg = prov.ready()
    if not ok:
        print(f"Provider not ready: {msg}")
        return 1

    tickers = prov.universe(limit=args.limit) or []
    if not tickers:
        print("No tickers in the export.")
        return 1
    smoke = len(tickers) < 2000
    if smoke:
        print(f"*** SMOKE TEST ONLY ({len(tickers)} names) — the methodology rule requires the "
              f"FULL universe for any keep/reject verdict. ***")

    panel = build_valuation_panel(prov, tickers, rebalance_days=args.rebalance_days,
                                  lookback_years=args.lookback_years, horizon=args.horizon,
                                  risk_free=args.risk_free)
    if panel.empty:
        print("Empty panel.")
        return 1
    if args.panel_csv:
        panel.to_csv(args.panel_csv, index=False)
    res = run_calibration(prov, tickers, horizon=args.horizon,
                          rebalance_days=args.rebalance_days, panel=panel,
                          risk_free=args.risk_free)
    _report(res, args, smoke=smoke)
    return 0


def _report(res, args, smoke=False):
    """Print the run, in the order the conclusions should be read in."""
    import json
    if res.get("status"):
        print(res["status"])
        return
    cov = res["coverage"]
    print(f"\n=== Coverage (read this first) ===")
    print(f"  {cov['rows']:,} rows · {cov['names']} names · {cov['dates']} dates")
    for k, v in sorted(cov.get("coverage", {}).items()):
        flag = "   <-- BELOW 5% FLOOR" if v < 0.05 else ""
        print(f"    {k:<20} {v:6.1%}{flag}")
    print(f"    {'valuable':<20} {cov.get('valuable_frac') or 0:6.1%}")
    print(f"    {'growth-led':<20} {cov.get('growth_led_frac') or 0:6.1%}")
    print(f"    {'ev_ebitda used':<20} {cov.get('ev_ebitda_used_frac') or 0:6.1%}")
    print(f"    {'ev_sales used':<20} {cov.get('ev_sales_used_frac') or 0:6.1%}")

    sn = res.get("sanity") or {}
    print(f"\n=== Sanity (present is not the same as sane) ===")
    if sn.get("adr_over_representation") is not None:
        print(f"    ADRs in widest-discount decile: {sn['adr_share_top_decile']:.1%} vs "
              f"{sn['adr_share_universe']:.1%} of the universe "
              f"({sn['adr_over_representation']:.2f}x)")
    if sn.get("median_mktcap_top_decile"):
        print(f"    median market cap: top decile ${sn['median_mktcap_top_decile']/1e9:,.2f}B vs "
              f"universe ${sn['median_mktcap_universe']/1e9:,.2f}B")
    if sn.get("median_maturity_top_decile") is not None:
        print(f"    median maturity: top decile {sn['median_maturity_top_decile']} vs "
              f"bottom decile {sn['median_maturity_bottom_decile']}")
    for f in sn.get("flags", []):
        print(f"    FLAG: {f}")
    if not sn.get("flags"):
        print("    no flags")

    ic = res["gap_ic"]
    print(f"\n=== Value/price gap -> forward {args.horizon}d return ===")
    if ic.get("status"):
        print(f"  {ic['status']}")
    else:
        print(f"  median IC {ic['median_ic']:+.4f}   mean IC {ic['mean_ic']:+.4f}   "
              f"t {ic['ic_tstat']:+.2f}   IC>0 on {ic['ic_positive_frac']:.0%} of "
              f"{ic['n_dates']} dates")
    q = res["gap_quantiles"]
    if not q.get("status"):
        print(f"  deciles/yr: " + "  ".join(_fmt(d, '+.1%') for d in q["decile_ann_return"]))
        print(f"  equal-weight {_fmt(q['equal_weight_ann'], '+.1%')}   "
              f"top-decile alpha {_fmt(q['top_decile_alpha'], '+.2%')} "
              f"(t {_fmt(q.get('top_decile_alpha_tstat'), '+.2f')})   "
              f"long-short {_fmt(q['long_short_ann'], '+.2%')} (t {_fmt(q['long_short_tstat'], '+.2f')})   "
              f"monotonicity {_fmt(q['monotonicity'], '+.3f')}")

    ov = res.get("nonoverlapping") or {}
    if ov.get("offsets"):
        print(f"\n=== Same test on NON-OVERLAPPING windows (every {ov['stride']}th date) ===")
        print(f"  overlapping windows inflate a t-stat by ~sqrt({ov['stride']}); each offset "
              f"below is an independent-draw re-run")
        for off, r in sorted(ov["offsets"].items()):
            i, qq = r["ic"], r["quantiles"]
            if i.get("status"):
                print(f"  offset {off}  {r['n_dates']:>3} dates   {i['status']}")
                continue
            print(f"  offset {off}  {r['n_dates']:>3} dates   medIC {i['median_ic']:+.4f}  "
                  f"t {i['ic_tstat']:+.2f}   LS t {_fmt(qq.get('long_short_tstat'), '+.2f')}   "
                  f"topQ alpha {_fmt(qq.get('top_decile_alpha'), '+.1%')} "
                  f"(t {_fmt(qq.get('top_decile_alpha_tstat'), '+.2f')})")
        if ov.get("ic_tstat_range"):
            print(f"  IC t range across offsets: {ov['ic_tstat_range'][0]:+.2f} .. "
                  f"{ov['ic_tstat_range'][1]:+.2f}")

    print(f"\n=== Positive control: plain value factors on the SAME rows ===")
    for name, r in (res.get("controls") or {}).items():
        if not isinstance(r, dict):
            continue
        i, qq = r.get("ic", {}), r.get("quantiles", {})
        if i.get("status"):
            print(f"  {name:<14} {i['status']}")
            continue
        print(f"  {name:<14} medIC {i['median_ic']:+.4f}  t {i['ic_tstat']:+.2f}   "
              f"LS {_fmt(qq.get('long_short_ann'), '+.1%')} (t {_fmt(qq.get('long_short_tstat'), '+.2f')})"
              f"   topQ alpha {_fmt(qq.get('top_decile_alpha'), '+.1%')} "
              f"(t {_fmt(qq.get('top_decile_alpha_tstat'), '+.2f')})")

    print(f"\n=== By market-cap tier (is the gap a valuation signal or a size proxy?) ===")
    for name, r in (res.get("by_size") or {}).items():
        i, qq = r.get("ic", {}), r.get("quantiles", {})
        if i.get("status"):
            print(f"  {name:<8} {r['rows']:>7,} rows   {i['status']}")
            continue
        print(f"  {name:<8} {r['rows']:>7,} rows  median ${r['median_mktcap']/1e9:>6.2f}B   "
              f"medIC {i['median_ic']:+.4f}  t {i['ic_tstat']:+.2f}   "
              f"LS {_fmt(qq.get('long_short_ann'), '+.1%')} (t {_fmt(qq.get('long_short_tstat'), '+.2f')})   "
              f"topQ alpha {_fmt(qq.get('top_decile_alpha'), '+.1%')} "
              f"(t {_fmt(qq.get('top_decile_alpha_tstat'), '+.2f')})")

    print(f"\n=== By maturity tier (does the growth lens help or just look reasonable?) ===")
    for name, r in res["by_maturity"].items():
        i, qq = r.get("ic", {}), r.get("quantiles", {})
        if i.get("status"):
            print(f"  {name:<14} {r['rows']:>7,} rows   {i['status']}")
            continue
        print(f"  {name:<14} {r['rows']:>7,} rows   medIC {i['median_ic']:+.4f}  t {i['ic_tstat']:+.2f}"
              f"   LS {_fmt(qq.get('long_short_ann'), '+.1%')} (t {_fmt(qq.get('long_short_tstat'), '+.2f')})"
              f"   topQ alpha {_fmt(qq.get('top_decile_alpha'), '+.1%')} "
              f"(t {_fmt(qq.get('top_decile_alpha_tstat'), '+.2f')})")

    print(f"\n=== Stability across the two halves ===")
    for half, r in res["half_split"].items():
        if not isinstance(r, dict) or "ic" not in r:
            continue
        i, qq = r["ic"], r["quantiles"]
        if i.get("status"):
            print(f"  {half:<12} {i['status']}")
            continue
        print(f"  {half:<12} {r['dates'][0]}..{r['dates'][1]}   medIC {i['median_ic']:+.4f}  "
              f"t {i['ic_tstat']:+.2f}   LS t {_fmt(qq.get('long_short_tstat'), '+.2f')}")

    print(f"\n=== Does implied growth show up? ({REALIZED_GROWTH_YEARS}y realized) ===")
    for k, r in res["implied_growth"].items():
        if r.get("status"):
            print(f"  {k:<16} {r['status']} (n={r.get('n')})")
            continue
        print(f"  {k:<16} n={r['n']:,}  implied {r['median_implied']:+.1%}  "
              f"realized {r['median_realized']:+.1%}  "
              f"met-or-beat {r['frac_realized_at_or_above_implied']:.1%}  "
              f"rank corr {r['rank_corr_implied_vs_realized']:+.3f}")

    print(f"\n=== Spot checks: does the blend behave across the whole spectrum? ===")
    for tier, rows in (res.get("spot_checks") or {}).items():
        for r in rows:
            fv = "n/a" if r["fair_value"] is None else f"${r['fair_value']:,.2f}"
            print(f"  {tier:<12} {r['date']}  {r['ticker']:<6} price ${r['price']:>9,.2f}  "
                  f"fair {fv:>12}  maturity {r['maturity']:.2f}  "
                  f"{r['confidence']:<6}  {r['method']}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2, default=str)
        print(f"\nWrote {args.json}")
    if smoke:
        print("\n*** Reminder: the above is a SMOKE TEST, not a verdict. ***")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
