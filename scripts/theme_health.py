#!/usr/bin/env python3
"""theme_health.py -- V2, the live theme-health meter.

WHY THIS EXISTS. The backtest's theme ICs (`per_theme.themes` in `BACKTEST_RESULTS.json`:
quality +0.0356, capital_discipline +0.0297, low_risk +0.0247, ...) are measured on ONE
Sharadar panel of 69 rebalance dates, and **they have never been checked against live forward
returns**. Every daily scan already records each name's ten theme scores and its price. This
reads that record back, as 63-day windows close, and asks whether each theme is still doing
live what the panel says it did historically.

EVERY PARAMETER HERE WAS FIXED IN `PREREG_v2_theme_health.md` BEFORE THIS FILE EXISTED, at a
moment when the live record held **zero closed 63-day windows**. There was no live number to
tune a threshold against, even in principle. Changing any constant below is a breach of that
pre-registration, not a code change -- with one exception, stated at `SIGMA` and inherited
verbatim from `track_meter`: sigma may be raised, never lowered.

WHAT IT WILL SAY TODAY, AND WHY THAT IS THE CORRECT ANSWER RATHER THAN A FAILURE. NOT-QUOTABLE,
on every theme. The deepest snapshot history on this machine is 7 calendar days and all of it
is synthetic test output; the first 63-day window cannot close for ~3 months and the
pre-registered minimum is 6 closed monthly windows after that. **A meter that prints a number
before it has one is the defect this file is built to avoid**, so the refusal is the product.

THE COVERAGE RULE IS ENFORCED AS A REFUSAL, NOT A FOOTNOTE. Five wired factors in this project
were silently empty for its entire history, because an empty column contributes nothing to a
mean, raises no error, and lets the run complete normally. So every gate below suppresses the
IC rather than annotating it, and the report leads with depth before it ever reaches a
statistic.

READ-ONLY ON `valuation/edge/**`, WHICH IS THE POINT OF TWO IMPORTS. `_spearman` is the panel's
own correlation and `boundary` is the contract meter's own confidence sequence. Re-implementing
either would give the project a second definition free to drift from the first, which is the
defect class it has already paid for more than once.

Usage:
    python -m scripts.theme_health                       # auto source, human-readable report
    python -m scripts.theme_health --json OUT.json       # + machine artifact with per-date rows
    python -m scripts.theme_health --source archive      # force one source
    python -m scripts.theme_health --db /path/screener.db --archive /path/archive
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import gzip
import json
import math
import os
import sqlite3
import sys
from typing import Dict, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge.fundamental_panel import _spearman          # noqa: E402  READ-ONLY
from valuation.edge.track_meter import boundary                 # noqa: E402  READ-ONLY
from valuation.screener import settings as S                    # noqa: E402
from valuation.screener.market_session import is_trading_day    # noqa: E402

# ---------------------------------------------------------------------------
# FROZEN by PREREG_v2_theme_health.md. Every value here was chosen with zero
# closed windows in hand. Derivations are shown so they are auditable, then
# pinned to literals by tests.
# ---------------------------------------------------------------------------

PREREG = "PREREG_v2_theme_health.md"

HORIZON_TD = 63                  # matches the panel's own horizon, so live and backtest
                                 # figures are the same object on different data

# Monthly cadence against a 63-trading-day window means consecutive observations overlap
# 3:1. That is not corrected away by discarding observations; it is priced in here. For
# statistics on m-fold overlapping windows the lag-j autocorrelation is ~(1 - j/m), so the
# variance of the running sum inflates by 1 + 2*sum_{j=1..m-1}(1 - j/m), which at m = 3 is
# exactly 3. Treating overlapping windows as independent is the easiest way to manufacture
# significance here, and it is refused up front.
OVERLAP_M = 3
OVERLAP_DESIGN_EFFECT = 1.0 + 2.0 * sum(1.0 - j / float(OVERLAP_M) for j in range(1, OVERLAP_M))
SIGMA = math.sqrt(OVERLAP_DESIGN_EFFECT)          # 1.7320508...

# MAY NEVER BE REVISED DOWNWARD -- track_meter rule 1, inherited verbatim. A narrower band
# makes crossing easier, so a downward revision is indistinguishable from buying a result.
# If the realised sd of the observations exceeds SIGMA the bound is anti-conservative and
# sigma must be RAISED; `sigma_breach` is reported on every call so that cannot pass quietly.

RHO = 3.0                        # the value track_meter froze, for the same 12-60 month range

# Family-wise across the ten themes. NOT caution -- a measured correction: X7 measured that
# when eight themes are tested and the bar is applied to whichever looks best, 39% of pure-noise
# draws produce at least one theme clearing it. V2 tests ten.
ALPHA_FAMILY = 0.05
N_THEMES = len(S.FACTORS_ALL)                     # 10
ALPHA_THEME = ALPHA_FAMILY / N_THEMES             # 0.005, two-sided

# --- the coverage rule, as refusals ---------------------------------------
MIN_NAMES_PER_DATE = 20          # the panel's own theme_ic floor
MIN_MONTHS = 6                   # closed windows before ANY IC is quoted for a theme
MIN_THEME_COVERAGE = 0.30        # the project's existing 30% floor (the bar pead_drift failed)
MAX_ATTRITION = 0.20             # a date >20% unmeasurable forward is VOIDED, not measured
                                 # on its survivors
MAX_VOIDED_FRACTION = 0.10       # track_meter's constant
PRICE_STALENESS_TD = 3           # forward mark within +/-3 td of d+63 (track_meter's limit)
REF_MIN_IC = 0.01                # below this the backtest claims no direction, so no
                                 # directional verdict is defined

# Provider strings that mark a source as not-real. Pre-committed in the register BEFORE the
# exclusion could be described as convenient: every scan archive on this machine is
# "synthetic (offline test)" with SYN* tickers, and an IC measured on those rows would be a
# real-looking number about nothing.
SYNTHETIC_MARKERS = ("synthetic", "offline test", "fixture", "mock", "dummy", "sample")

# TIGHTER THAN THE PRE-COMMITMENT, deliberately, and recorded because tightening must be.
# A scan dated after today is not a record of anything that happened and no forward window
# from it can have closed. This is not hypothetical: `tests/test_saas.py:200` POSTs a row
# dated 2099-01-01 to /admin/ingest-snapshot, and on this machine that row is sitting in the
# real `data/screener.db`. Before this guard it became the meter's `as_of` and dragged the
# whole report into the year 2099. Excluding MORE data cannot reach the harmful error here,
# which is quoting an IC that is not supported; it can only delay a verdict.
EXCLUDE_FUTURE_DATED = True

VERDICTS = ("DEGRADED", "CONFIRMED-LIVE", "INSUFFICIENT", "NO-REFERENCE", "NOT-QUOTABLE")


def frozen_parameters() -> Dict:
    """Everything the pre-registration fixed, in one place, for the artifact and the tests."""
    return {
        "prereg": PREREG,
        "horizon_td": HORIZON_TD,
        "cadence": "monthly",
        "overlap_m": OVERLAP_M,
        "overlap_design_effect": OVERLAP_DESIGN_EFFECT,
        "sigma": SIGMA,
        "rho": RHO,
        "alpha_family": ALPHA_FAMILY,
        "n_themes": N_THEMES,
        "alpha_theme": ALPHA_THEME,
        "min_names_per_date": MIN_NAMES_PER_DATE,
        "min_months": MIN_MONTHS,
        "min_theme_coverage": MIN_THEME_COVERAGE,
        "max_attrition": MAX_ATTRITION,
        "max_voided_fraction": MAX_VOIDED_FRACTION,
        "price_staleness_td": PRICE_STALENESS_TD,
        "ref_min_ic": REF_MIN_IC,
        "synthetic_markers": list(SYNTHETIC_MARKERS),
        "ic_definition": "valuation.edge.fundamental_panel._spearman (imported read-only)",
        "band": "valuation.edge.track_meter.boundary (imported read-only)",
    }


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

def _d(x) -> Optional[_dt.date]:
    if isinstance(x, _dt.date):
        return x
    try:
        return _dt.date.fromisoformat(str(x)[:10])
    except Exception:
        return None


def _plus_trading_days(start: _dt.date, n: int) -> _dt.date:
    """The date exactly `n` trading days after `start`."""
    d, seen = start, 0
    while seen < n:
        d += _dt.timedelta(days=1)
        if is_trading_day(d):
            seen += 1
    return d


def _trading_days_between(a: _dt.date, b: _dt.date) -> int:
    """Signed count of trading days from a to b (0 if same day)."""
    if a == b:
        return 0
    sign, lo, hi = (1, a, b) if b > a else (-1, b, a)
    n, d = 0, lo
    while d < hi:
        d += _dt.timedelta(days=1)
        if is_trading_day(d):
            n += 1
    return sign * n


def _month_key(d: _dt.date) -> str:
    return "%04d-%02d" % (d.year, d.month)


def is_synthetic(provider: str) -> bool:
    p = (provider or "").lower()
    return any(m in p for m in SYNTHETIC_MARKERS)


def is_future(day: _dt.date, today: _dt.date = None) -> bool:
    return bool(EXCLUDE_FUTURE_DATED) and day > (today or _dt.date.today())


# ---------------------------------------------------------------------------
# Loading. Two sources, the same shape out of both.
#
# A row is {date, ticker, price, factors{theme: float|None}, provider, source}. The price
# series the forward return is measured against is THE SAME RECORD -- no vendor is called, so
# the script is offline, reproducible, and cannot be invalidated by a rate limiter (a sibling
# lane has already lost two full runs to silent Yahoo throttling).
# ---------------------------------------------------------------------------

def load_store(db_path: str, today: _dt.date = None) -> Tuple[List[dict], dict]:
    """Snapshot rows from the screener store -- the full scanned universe per date."""
    prov = {"source": "store", "path": db_path, "present": os.path.exists(db_path),
            "dates_seen": 0, "dates_synthetic": 0, "dates_future": 0, "rows": 0,
            "providers": {}}
    if not prov["present"]:
        prov["error"] = "no such file"
        return [], prov
    out: List[dict] = []
    try:
        c = sqlite3.connect(db_path)
        c.row_factory = sqlite3.Row
        providers = {r["scan_date"]: (r["provider"] or "")
                     for r in c.execute("SELECT scan_date, provider FROM scans")}
        seen_dates, future_dates = set(), set()
        for r in c.execute("SELECT scan_date, ticker, price, extra FROM snapshot_rows"):
            day = _d(r["scan_date"])
            if day is None:
                continue
            seen_dates.add(day)
            provider = providers.get(r["scan_date"], "")
            prov["providers"][provider] = prov["providers"].get(provider, 0) + 1
            if is_future(day, today):
                future_dates.add(day)
                continue
            if is_synthetic(provider):
                continue
            try:
                extra = json.loads(r["extra"]) if r["extra"] else {}
            except Exception:
                extra = {}
            out.append({"date": day, "ticker": r["ticker"], "price": r["price"],
                        "factors": (extra.get("factors") or {}), "provider": provider,
                        "source": "store"})
        c.close()
        prov["dates_seen"] = len(seen_dates)
        prov["dates_synthetic"] = len({r for r in providers if is_synthetic(providers[r])})
        prov["dates_future"] = len(future_dates)
        prov["rows"] = len(out)
    except Exception as e:                                   # pragma: no cover - defensive
        prov["error"] = "%s: %s" % (type(e).__name__, e)
    return out, prov


def load_archive(root: str, today: _dt.date = None) -> Tuple[List[dict], dict]:
    """Dated gzipped scan archives -- top 100 per day, survivorship-free, DB-independent."""
    prov = {"source": "archive", "path": root, "present": os.path.isdir(root),
            "dates_seen": 0, "dates_synthetic": 0, "dates_future": 0, "rows": 0,
            "providers": {}}
    if not prov["present"]:
        prov["error"] = "no such directory"
        return [], prov
    out: List[dict] = []
    files = sorted(glob.glob(os.path.join(root, "*.json.gz")))
    for fn in files:
        try:
            with gzip.open(fn, "rt", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            continue
        day = _d(payload.get("scan_date")) or _d(os.path.basename(fn)[:10])
        if day is None:
            continue
        prov["dates_seen"] += 1
        provider = payload.get("provider") or ""
        prov["providers"][provider] = prov["providers"].get(provider, 0) + 1
        if is_future(day, today):
            prov["dates_future"] += 1
            continue
        if is_synthetic(provider):
            prov["dates_synthetic"] += 1
            continue
        for r in payload.get("rows") or []:
            out.append({"date": day, "ticker": r.get("ticker"), "price": r.get("price"),
                        "factors": (r.get("factors") or {}), "provider": provider,
                        "source": "archive"})
    prov["rows"] = len(out)
    return out, prov


def load_observations(source: str = "auto", db_path: str = None,
                      archive_root: str = None,
                      today: _dt.date = None) -> Tuple[List[dict], dict]:
    """Load from the requested source; `auto` takes whichever yields more usable dates.

    The two sources are never merged. They record different books -- the store keeps the whole
    scanned universe, the archive keeps the top 100 -- so pooling them would silently change
    what the cross-section IS from date to date, which changes what the IC means.
    """
    db_path = db_path or os.path.join(_HERE, "data", "screener.db")
    archive_root = archive_root or os.path.join(_HERE, "data", "archive", "scans")
    store_rows, store_prov = ([], None)
    arch_rows, arch_prov = ([], None)
    if source in ("auto", "store"):
        store_rows, store_prov = load_store(db_path, today=today)
    if source in ("auto", "archive"):
        arch_rows, arch_prov = load_archive(archive_root, today=today)

    def usable_dates(rows):
        return len({r["date"] for r in rows})

    if source == "store":
        rows, chosen = store_rows, store_prov
    elif source == "archive":
        rows, chosen = arch_rows, arch_prov
    else:
        if usable_dates(store_rows) >= usable_dates(arch_rows):
            rows, chosen = store_rows, store_prov
        else:
            rows, chosen = arch_rows, arch_prov
    prov = {"requested": source, "chosen": (chosen or {}).get("source"),
            "store": store_prov, "archive": arch_prov}
    return rows, prov


# ---------------------------------------------------------------------------
# Depth. REPORTED BEFORE ANY IC EXISTS -- V2 requires it and the coverage rule
# demands it: coverage says a factor is PRESENT, and nothing else here means
# anything until that is known.
# ---------------------------------------------------------------------------

def depth_report(rows: Sequence[dict]) -> dict:
    dates = sorted({r["date"] for r in rows})
    names = {r["ticker"] for r in rows}
    per_theme = {}
    n = float(len(rows)) or 1.0
    for theme in S.FACTORS_ALL:
        present = sum(1 for r in rows if (r["factors"] or {}).get(theme) is not None)
        theme_dates = sorted({r["date"] for r in rows
                              if (r["factors"] or {}).get(theme) is not None})
        per_theme[theme] = {
            "non_null_rows": present,
            "coverage": present / n,
            "dates_with_data": len(theme_dates),
            "meets_coverage_floor": (present / n) >= MIN_THEME_COVERAGE,
        }
    return {
        "rows": len(rows),
        "dates": len(dates),
        "first_date": dates[0].isoformat() if dates else None,
        "last_date": dates[-1].isoformat() if dates else None,
        "distinct_names": len(names),
        "calendar_span_days": (dates[-1] - dates[0]).days if len(dates) > 1 else 0,
        "per_theme": per_theme,
    }


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------

def measurement_dates(rows: Sequence[dict]) -> List[_dt.date]:
    """One date per calendar month: the last scan in that month. Monthly cadence, per V2."""
    by_month: Dict[str, _dt.date] = {}
    for d in {r["date"] for r in rows}:
        k = _month_key(d)
        if k not in by_month or d > by_month[k]:
            by_month[k] = d
    return [by_month[k] for k in sorted(by_month)]


def build_index(rows: Sequence[dict]) -> dict:
    """Rows grouped by date, and (ticker, date) -> price. Built once per run.

    Without it every measurement date rescans the whole record, which is quadratic in the
    history length -- fine at 7 days and not fine at the five years this meter is designed to
    run for.
    """
    by_date: Dict[_dt.date, List[dict]] = {}
    price: Dict[Tuple[str, _dt.date], float] = {}
    for r in rows:
        by_date.setdefault(r["date"], []).append(r)
        if r.get("price") is not None:
            try:
                price[(r["ticker"], r["date"])] = float(r["price"])
            except (TypeError, ValueError):
                pass
    return {"by_date": by_date, "price": price,
            "dates": sorted(by_date), "n_rows": len(rows)}


def _idx(rows, index):
    return index if index is not None else build_index(rows)


def forward_returns(rows: Sequence[dict], d: _dt.date,
                    as_of: _dt.date = None, index: dict = None) -> Tuple[Dict[str, float], dict]:
    """Realised 63-trading-day returns for the names present on `d`, from recorded prices.

    A name contributes only if the record holds a price within PRICE_STALENESS_TD trading days
    of `d + 63`. Names that do not are ATTRITION and are counted, never quietly dropped -- an
    IC computed on whoever happened to still be in the book is a statistic about survivors.
    """
    ix = _idx(rows, index)
    target = _plus_trading_days(d, HORIZON_TD)
    as_of = as_of or (ix["dates"][-1] if ix["dates"] else d)
    info = {"date": d.isoformat(), "target": target.isoformat(),
            "window_closed": target <= as_of, "n_at_entry": 0, "n_measured": 0,
            "attrition": None, "mark_dates": []}
    if not info["window_closed"]:
        return {}, info

    entry = {}
    for r in ix["by_date"].get(d, []):
        p = ix["price"].get((r["ticker"], d))
        if p:
            entry[r["ticker"]] = p
    info["n_at_entry"] = len(entry)
    if not entry:
        info["attrition"] = 1.0
        return {}, info

    # Candidate mark dates: every recorded scan date within the staleness window of the
    # target, nearest first, so a name is marked from the closest price the record holds
    # rather than from whatever turns up first.
    candidates = sorted(
        [(abs(_trading_days_between(target, dd)), dd) for dd in ix["by_date"]
         if abs((dd - target).days) <= 3 * PRICE_STALENESS_TD + 7])
    candidates = [(g, dd) for g, dd in candidates if g <= PRICE_STALENESS_TD]

    out = {}
    for tkr, p0 in entry.items():
        for _gap, dd in candidates:
            px = ix["price"].get((tkr, dd))
            if px and px > 0 and p0 > 0:
                out[tkr] = px / p0 - 1.0
                info["mark_dates"].append(dd.isoformat())
                break
    info["n_measured"] = len(out)
    info["attrition"] = 1.0 - (len(out) / float(len(entry)))
    info["mark_dates"] = sorted(set(info["mark_dates"]))
    return out, info


def per_date_ic(rows: Sequence[dict], d: _dt.date, fwd: Dict[str, float],
                index: dict = None) -> Dict[str, dict]:
    """{theme: {ic, n}} on date `d`. The correlation is the panel's own `_spearman`."""
    ix = _idx(rows, index)
    same_day = ix["by_date"].get(d, [])
    out = {}
    for theme in S.FACTORS_ALL:
        xs, ys = [], []
        for r in same_day:
            v = (r["factors"] or {}).get(theme)
            f = fwd.get(r["ticker"])
            if v is None or f is None:
                continue
            try:
                xs.append(float(v))
                ys.append(float(f))
            except (TypeError, ValueError):
                continue
        if len(xs) >= MIN_NAMES_PER_DATE:
            ic = _spearman(xs, ys)
            out[theme] = {"ic": (float(ic) if ic == ic else None), "n": len(xs)}
        else:
            out[theme] = {"ic": None, "n": len(xs)}
    return out


# ---------------------------------------------------------------------------
# The band
# ---------------------------------------------------------------------------

def observations_to_z(obs: Sequence[Tuple[float, int]]) -> List[float]:
    """z_i = IC_i * sqrt(n_i - 1): unit variance under the null whatever the cross-section is.

    This is how a cross-section that changes size month to month is handled EXACTLY rather
    than by plugging in an average n and hoping.
    """
    return [ic * math.sqrt(max(n - 1, 1)) for ic, n in obs]


def meter(obs: Sequence[Tuple[float, int]], reference_sign: Optional[int]) -> dict:
    """The anytime-valid state of one theme. `obs` is [(ic, n_names), ...] in time order."""
    zs = observations_to_z(obs)
    k = len(zs)
    out = {"n_months": k, "z": zs, "running_sum": None, "boundary": None,
           "crossed": None, "verdict": None, "sigma_used": SIGMA,
           "sigma_realised": None, "sigma_breach": False,
           "mean_ic": None, "median_ic": None}
    if k == 0:
        return out
    ics = sorted(ic for ic, _n in obs)
    out["mean_ic"] = sum(ic for ic, _n in obs) / float(k)
    out["median_ic"] = (ics[k // 2] if k % 2 else 0.5 * (ics[k // 2 - 1] + ics[k // 2]))
    s = sum(zs)
    b = boundary(k, sigma=SIGMA, rho=RHO, alpha=ALPHA_THEME)
    out["running_sum"] = s
    out["boundary"] = b
    if k >= 2:
        mean_z = sum(zs) / float(k)
        var = sum((z - mean_z) ** 2 for z in zs) / float(k - 1)
        out["sigma_realised"] = math.sqrt(var)
        # Anti-conservative if realised dispersion exceeds the plug-in. Reported, never
        # silently absorbed -- sigma may then only be RAISED.
        out["sigma_breach"] = out["sigma_realised"] > SIGMA

    if s > b:
        out["crossed"] = "up"
    elif s < -b:
        out["crossed"] = "down"
    else:
        out["crossed"] = None

    if reference_sign is None:
        out["verdict"] = "NO-REFERENCE"
    elif out["crossed"] is None:
        out["verdict"] = "INSUFFICIENT"
    else:
        same = (out["crossed"] == "up" and reference_sign > 0) or \
               (out["crossed"] == "down" and reference_sign < 0)
        out["verdict"] = "CONFIRMED-LIVE" if same else "DEGRADED"
    return out


def reference_signs(backtest_path: str = None) -> Tuple[Dict[str, Optional[int]], dict]:
    """Sign of each theme's backtest median IC, with the artifact's own provenance.

    Read at run time rather than hard-coded, so a stale BACKTEST_RESULTS.json is VISIBLE in
    the output instead of being baked invisibly into a constant. A theme whose backtest IC is
    smaller than REF_MIN_IC gets no reference: the backtest is not claiming a direction there,
    so "degraded relative to what?" has no answer.
    """
    backtest_path = backtest_path or os.path.join(_HERE, "BACKTEST_RESULTS.json")
    prov = {"path": backtest_path, "present": os.path.exists(backtest_path)}
    signs: Dict[str, Optional[int]] = {t: None for t in S.FACTORS_ALL}
    values: Dict[str, Optional[float]] = {t: None for t in S.FACTORS_ALL}
    if not prov["present"]:
        prov["error"] = "no such file; every theme falls back to NO-REFERENCE"
        return signs, {"provenance": prov, "median_ic": values}
    try:
        with open(backtest_path, encoding="utf-8") as f:
            data = json.load(f)
        prov["generated_at"] = data.get("generated_at")
        prov["git"] = data.get("git")
        prov["universe"] = data.get("universe")
        themes = ((data.get("per_theme") or {}).get("themes") or {})
        for t in S.FACTORS_ALL:
            v = (themes.get(t) or {}).get("median_ic")
            values[t] = v
            if v is None:
                continue
            if abs(v) >= REF_MIN_IC:
                signs[t] = 1 if v > 0 else -1
    except Exception as e:                                   # pragma: no cover - defensive
        prov["error"] = "%s: %s" % (type(e).__name__, e)
    return signs, {"provenance": prov, "median_ic": values}


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------

def analyse(rows: Sequence[dict], as_of: _dt.date = None,
            backtest_path: str = None) -> dict:
    """Depth first, then windows, then -- only if every gate passes -- an IC."""
    ix = build_index(rows)
    as_of = as_of or (ix["dates"][-1] if ix["dates"] else _dt.date.today())
    depth = depth_report(rows)
    signs, ref = reference_signs(backtest_path)

    mdates = measurement_dates(rows)
    windows, per_theme_obs = [], {t: [] for t in S.FACTORS_ALL}
    for d in mdates:
        fwd, info = forward_returns(rows, d, as_of=as_of, index=ix)
        info["voided"] = False
        info["void_reason"] = None
        if not info["window_closed"]:
            info["voided"] = True
            info["void_reason"] = "window has not closed"
        elif info["n_measured"] < MIN_NAMES_PER_DATE:
            info["voided"] = True
            info["void_reason"] = ("only %d names measurable forward, floor is %d"
                                   % (info["n_measured"], MIN_NAMES_PER_DATE))
        elif info["attrition"] is not None and info["attrition"] > MAX_ATTRITION:
            info["voided"] = True
            info["void_reason"] = ("attrition %.1f%% exceeds the %.0f%% ceiling -- the survivors "
                                   "are not the cross-section"
                                   % (100.0 * info["attrition"], 100.0 * MAX_ATTRITION))
        if not info["voided"]:
            ics = per_date_ic(rows, d, fwd, index=ix)
            info["ic"] = {t: v["ic"] for t, v in ics.items()}
            info["n"] = {t: v["n"] for t, v in ics.items()}
            for t, v in ics.items():
                if v["ic"] is not None:
                    per_theme_obs[t].append((v["ic"], v["n"]))
        else:
            info["ic"] = None
            info["n"] = None
        windows.append(info)

    closed = [w for w in windows if w["window_closed"]]
    voided = [w for w in closed if w["voided"]]
    voided_fraction = (len(voided) / float(len(closed))) if closed else 0.0

    results = {}
    for t in S.FACTORS_ALL:
        obs = per_theme_obs[t]
        blocks = []
        if depth["per_theme"][t]["non_null_rows"] == 0:
            blocks.append("theme is empty in the record (0 non-null rows)")
        elif not depth["per_theme"][t]["meets_coverage_floor"]:
            blocks.append("coverage %.1f%% is below the %.0f%% floor"
                          % (100.0 * depth["per_theme"][t]["coverage"],
                             100.0 * MIN_THEME_COVERAGE))
        if len(obs) < MIN_MONTHS:
            blocks.append("%d closed monthly windows, floor is %d" % (len(obs), MIN_MONTHS))
        if closed and voided_fraction > MAX_VOIDED_FRACTION:
            blocks.append("%.0f%% of closed windows voided, ceiling is %.0f%%"
                          % (100.0 * voided_fraction, 100.0 * MAX_VOIDED_FRACTION))
        m = meter(obs, signs[t])
        if blocks:
            # NOT-QUOTABLE suppresses the statistic itself, not merely the verdict. A number
            # printed beside its own reason for being untrustworthy gets quoted without it.
            results[t] = {
                "verdict": "NOT-QUOTABLE", "quotable": False, "blocked_by": blocks,
                "n_months": m["n_months"], "coverage": depth["per_theme"][t]["coverage"],
                "reference_median_ic": ref["median_ic"][t], "reference_sign": signs[t],
                "mean_ic": None, "median_ic": None, "running_sum": None, "boundary": None,
                "crossed": None, "sigma_breach": None,
            }
        else:
            results[t] = {
                "verdict": m["verdict"], "quotable": True, "blocked_by": [],
                "n_months": m["n_months"], "coverage": depth["per_theme"][t]["coverage"],
                "reference_median_ic": ref["median_ic"][t], "reference_sign": signs[t],
                "mean_ic": m["mean_ic"], "median_ic": m["median_ic"],
                "running_sum": m["running_sum"], "boundary": m["boundary"],
                "crossed": m["crossed"], "sigma_breach": m["sigma_breach"],
                "sigma_realised": m["sigma_realised"],
                "observations": [{"ic": ic, "n": n} for ic, n in obs],
            }

    # The typical cross-section a window is measured on. Taken from the closed windows if
    # any exist, otherwise from the record's own per-date name counts, so the power statement
    # is available before the first window closes -- which is when it is most needed.
    sizes = [w["n_measured"] for w in closed if not w["voided"] and w["n_measured"]]
    if not sizes:
        sizes = [len(v) for v in ix["by_date"].values()]
    typical = int(sorted(sizes)[len(sizes) // 2]) if sizes else 0
    det = {}
    for k in (24, 60):
        det[k] = (boundary(k, sigma=SIGMA, rho=RHO, alpha=ALPHA_THEME) /
                  (k * math.sqrt(max(typical - 1, 1)))) if typical > 1 else None

    quotable = [t for t, v in results.items() if v["quotable"]]
    return {
        "as_of": as_of.isoformat(),
        "typical_cross_section": typical,
        "detectable_ic_24m": det[24],
        "detectable_ic_60m": det[60],
        "parameters": frozen_parameters(),
        "depth": depth,
        "reference": ref,
        "windows": windows,
        "windows_closed": len(closed),
        "windows_voided": len(voided),
        "voided_fraction": voided_fraction,
        "themes": results,
        "any_quotable": bool(quotable),
        "quotable_themes": sorted(quotable),
    }


# ---------------------------------------------------------------------------
# Report. Leads with depth, because until depth is known nothing else means
# anything -- and says for itself when it is too thin, which V2 requires.
# ---------------------------------------------------------------------------

def render(result: dict, provenance: dict) -> str:
    L = []
    A = L.append
    A("=" * 78)
    A("LIVE THEME-HEALTH METER  (V2)   as of %s" % result["as_of"])
    A("pre-registered in %s -- every parameter below was fixed before the first IC" % PREREG)
    A("=" * 78)

    A("")
    A("-- WHERE THE DATA CAME FROM " + "-" * 50)
    A("  requested source: %s        chosen: %s" % (provenance.get("requested"),
                                                    provenance.get("chosen")))
    for key in ("store", "archive"):
        p = provenance.get(key)
        if not p:
            continue
        A("  %-8s %s" % (key, p.get("path")))
        A("           present=%s  dates=%s  synthetic_dates=%s  future_dated=%s  usable_rows=%s%s"
          % (p.get("present"), p.get("dates_seen"), p.get("dates_synthetic"),
             p.get("dates_future"), p.get("rows"),
             ("  ERROR: " + p["error"]) if p.get("error") else ""))
        for prov_name, cnt in sorted((p.get("providers") or {}).items()):
            flag = "  <-- EXCLUDED AS SYNTHETIC" if is_synthetic(prov_name) else ""
            A("           provider %-28r %5d%s" % (prov_name, cnt, flag))

    d = result["depth"]
    A("")
    A("-- DEPTH, BEFORE ANY STATISTIC " + "-" * 46)
    A("  usable rows %d over %d scan dates (%s -> %s), %d distinct names"
      % (d["rows"], d["dates"], d["first_date"], d["last_date"], d["distinct_names"]))
    A("  closed 63-trading-day windows: %d      voided: %d (%.0f%%)"
      % (result["windows_closed"], result["windows_voided"],
         100.0 * result["voided_fraction"]))
    # THE CROSS-SECTION SIZE IS THE WHOLE BALLGAME and it is invisible unless printed here.
    # Measured: at 100 names this meter has 2.5% power at 60 months against quality's own
    # backtested IC; at 800 names it has 80.3%. Same band, same horizon, different source.
    ns = result.get("typical_cross_section")
    if ns and result.get("detectable_ic_24m") is not None:
        A("  typical cross-section: %d names -> a live IC of %+.4f is detectable by month 24,"
          % (ns, result["detectable_ic_24m"]))
        A("                          %+.4f by month 60 (quality's backtested IC is +0.0356)"
          % result["detectable_ic_60m"])
    A("")
    A("  %-20s %10s %9s %8s" % ("theme", "non-null", "coverage", "months"))
    for t in S.FACTORS_ALL:
        pt = d["per_theme"][t]
        A("  %-20s %10d %8.1f%% %8d%s"
          % (t, pt["non_null_rows"], 100.0 * pt["coverage"],
             result["themes"][t]["n_months"],
             "" if pt["meets_coverage_floor"] else "   < floor"))

    A("")
    A("-- VERDICTS " + "-" * 65)
    if not result["any_quotable"]:
        A("  NO THEME IS QUOTABLE. This meter is reporting that it has nothing to report,")
        A("  which is the correct output at this depth and not a failure of the run.")
    A("")
    A("  %-20s %-15s %s" % ("theme", "verdict", "why / where it stands"))
    for t in S.FACTORS_ALL:
        v = result["themes"][t]
        if v["quotable"]:
            why = ("median IC %+.4f over %d months; sum %+.2f vs boundary %.2f%s"
                   % (v["median_ic"], v["n_months"], v["running_sum"], v["boundary"],
                      "  SIGMA BREACH" if v.get("sigma_breach") else ""))
        else:
            why = "; ".join(v["blocked_by"])
        A("  %-20s %-15s %s" % (t, v["verdict"], why))

    A("")
    A("-- HOW TO READ IT " + "-" * 59)
    A("  INSUFFICIENT is NOT evidence that a theme is fine, and NOT evidence that it is")
    A("  broken. An anytime-valid band is wide on purpose: it can be read every month")
    A("  without a multiplicity correction, and the price is paid in width.")
    A("  alpha is %.4f per theme (%.2f family-wise across %d themes), because X7 measured"
      % (ALPHA_THEME, ALPHA_FAMILY, N_THEMES))
    A("  that testing 8 themes at a per-theme bar lets 39% of pure-noise draws clear it.")
    A("  Windows overlap 3:1 at monthly cadence; sigma = sqrt(3) prices that in.")
    return "\n".join(L)


def calibrate(n_names: int = 100, horizons=(6, 12, 24, 36, 60, 120),
              draws: int = 20000, seed: int = 1000) -> dict:
    """What this meter can actually deliver -- measured, not asserted.

    An anytime-valid band is honest and WIDE, and the project has already been burned by
    quoting a test's existence as if it were the test's power (the forward track's 13% at 60
    months). So the same question is answered here before anyone reads a verdict off it: how
    big must a live IC be before this thing can see it, and how often does it fire on nothing?

    The null is simulated with the overlap structure the band assumes -- z_i is an equally
    weighted moving average of 3 iid innovations, giving unit variance and lag-1/lag-2
    autocorrelations of exactly 2/3 and 1/3.
    """
    import random as _rnd
    root3 = math.sqrt(3.0)
    detectable = {}
    for k in horizons:
        # mean IC needed for the running sum to reach the boundary at month k
        detectable[k] = boundary(k, sigma=SIGMA, rho=RHO, alpha=ALPHA_THEME) / (
            k * math.sqrt(max(n_names - 1, 1)))

    def run(mean_shift: float, k_max: int, n_draws: int, seed0: int) -> float:
        rng = _rnd.Random(seed0)
        crossed = 0
        for _ in range(n_draws):
            u = [rng.gauss(0, 1), rng.gauss(0, 1)]
            s = 0.0
            hit = False
            for k in range(1, k_max + 1):
                u.append(rng.gauss(0, 1))
                z = (u[-1] + u[-2] + u[-3]) / root3 + mean_shift
                s += z
                if abs(s) > boundary(k, sigma=SIGMA, rho=RHO, alpha=ALPHA_THEME):
                    hit = True
                    break
            crossed += 1 if hit else 0
        return crossed / float(n_draws)

    out = {"n_names": n_names, "draws": draws, "seed": seed,
           "detectable_ic": detectable, "false_crossing": {}, "power": {}}
    for k in (60, 120):
        out["false_crossing"][k] = run(0.0, k, draws, seed)
    # Power at the backtest's own theme ICs, which is the effect size that matters.
    for label, ic in (("quality_0.0356", 0.0356), ("capital_discipline_0.0297", 0.0297),
                      ("three_times_quality_0.107", 0.1068)):
        shift = ic * math.sqrt(max(n_names - 1, 1))
        out["power"][label] = {k: run(shift, k, draws // 2, seed + 1) for k in (24, 60, 120)}
    return out


def render_calibration(c: dict) -> str:
    L = ["=" * 78,
         "WHAT THIS METER CAN DELIVER  (calibration, %d names per cross-section)" % c["n_names"],
         "=" * 78, "",
         "  mean live IC needed to cross, by month:"]
    for k, v in sorted(c["detectable_ic"].items()):
        L.append("      %4d months   IC %+.4f" % (k, v))
    L.append("")
    L.append("  false crossing under the null (nominal %.3f two-sided):" % ALPHA_THEME)
    for k, v in sorted(c["false_crossing"].items()):
        L.append("      by %3d months  %.4f" % (k, v))
    L.append("")
    L.append("  power at the backtest's own theme ICs:")
    for label, by_k in sorted(c["power"].items()):
        L.append("      %-28s %s" % (label,
                 "  ".join("%dm %.3f" % (k, v) for k, v in sorted(by_k.items()))))
    L.append("")
    L.append("  READ THIS BEFORE READING A VERDICT: the same arithmetic that gives the forward")
    L.append("  track 13% power at 60 months applies here. A theme that is exactly as good live")
    L.append("  as the panel says will mostly NOT cross, and that is the designed behaviour of")
    L.append("  an honest anytime-valid bound -- not evidence about the theme.")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="V2 live theme-health meter (owner-side).")
    ap.add_argument("--source", choices=["auto", "store", "archive"], default="auto")
    ap.add_argument("--db", default=None, help="path to screener.db")
    ap.add_argument("--archive", default=None, help="path to data/archive/scans")
    ap.add_argument("--backtest", default=None, help="path to BACKTEST_RESULTS.json")
    ap.add_argument("--as-of", default=None, help="YYYY-MM-DD (default: last scan date)")
    ap.add_argument("--json", default=None, help="write the full artifact, per-date rows included")
    ap.add_argument("--calibrate", action="store_true",
                    help="measure what the band can detect, and how often it fires on nothing")
    ap.add_argument("--calibrate-names", type=int, default=100)
    ap.add_argument("--calibrate-draws", type=int, default=20000)
    args = ap.parse_args(argv)

    if args.calibrate:
        c = calibrate(n_names=args.calibrate_names, draws=args.calibrate_draws)
        print(render_calibration(c))
        if args.json:
            os.makedirs(os.path.dirname(os.path.abspath(args.json)) or ".", exist_ok=True)
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump(c, f, indent=1, default=str)
            print("\nartifact -> %s" % args.json)
        return 0

    rows, provenance = load_observations(args.source, args.db, args.archive)
    as_of = _d(args.as_of) if args.as_of else None
    result = analyse(rows, as_of=as_of, backtest_path=args.backtest)
    result["provenance"] = provenance
    print(render(result, provenance))
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)) or ".", exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=1, default=str)
        print("\nartifact -> %s" % args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
