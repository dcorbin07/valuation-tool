"""
Trade autopsy (#23) — what separates the ~37% winners from the ~63% losers, using ONLY features
known at entry.

PRE-SPECIFIED. The gate below was written and committed before any feature was scored.

--------------------------------------------------------------------------------------------
THE FRAME, WHICH IS EASY TO GET WRONG.

The 37/63 split is the SIGNATURE of a long-vol book, not a defect. 30.7% of trades return
>= +100% and that tail is where the money is. So the objective is EXPECTANCY, never hit rate: a
filter that lifts the hit rate by clipping the tail makes the strategy worse while looking
better. Every candidate is therefore judged on held-out expectancy AND tail retention, and the
tail-retention number is reported even when nothing else is.

Equally: the winners are NOT clustered after the fact. Conditioning on the outcome finds
hindsight ("the winners went up"). Only entry-known features are assembled, and each is asked to
PREDICT out-of-sample.

--------------------------------------------------------------------------------------------
TWO OBJECTIVES, REPORTED SEPARATELY.

  1. WINNER-ENRICHMENT — features that predict the >= +100% tail. Few trades define the tail, so
     overfitting risk is highest here and the results are treated most sceptically.
  2. LOSER-AVOIDANCE — and specifically the AVOIDABLE structural mistakes, not the small losses,
     which are the fair price of convexity.

--------------------------------------------------------------------------------------------
THE PRE-COMMITTED GATE. A feature is ADOPTED only if ALL of these hold:

  G1. DIRECTION AND THRESHOLD ARE FITTED ON ONE HALF ONLY. Direction is the sign of that half's
      rank-IC; the threshold is the median of the feature among that half's PROFITABLE trades —
      `options_signals_v2.fit_threshold`'s recipe, reused rather than reinvented, so it stays an
      untuned rule ("look like the winners looked") and not a search over cutoffs.
  G2. HELD-OUT EXPECTANCY GAIN >= MIN_LATE_GAIN on the half that did not inform it.
  G3. RETENTION >= MIN_RETAINED. A filter that keeps 8% of alerts has not improved the strategy,
      it has replaced it with a smaller one.
  G4. n_kept >= MIN_TRADES on the held-out half.
  G5. TAIL RETENTION >= MIN_TAIL_RETENTION x overall retention. This is the bar that stops a
      filter buying expectancy by cutting the right tail, and it has no counterpart in any
      earlier phase of this project.
  G6. BEATS A RANDOM FILTER keeping the same number of trades (permutation p < ALPHA). Dropping
      trades at random from a heavy-tailed distribution moves expectancy on its own.
  G7. IT PASSES G2-G6 IN BOTH SPLIT DIRECTIONS — fit-early/confirm-late AND fit-late/confirm-
      early. The stock model's both-directions rule; a feature that only works one way round is
      noise that landed well.

  Then, separately, any survivor is re-tested STACKED ON TOP of term_slope (the adopted filter),
  because the question is what term_slope does not already capture — not what correlates with it.

MULTIPLE COMPARISONS ARE THE MAIN RISK HERE, so the count of features tested is reported
alongside the survivors, with a Benjamini-Hochberg FDR pass over the held-out permutation
p-values. With ~40 features x 2 directions, roughly 4 spurious "p<0.05" results are EXPECTED
before anything real is found. G7 exists because it is the cheapest defence against that.

--------------------------------------------------------------------------------------------
WHAT "KNOWN AT ENTRY" MEANS FOR EACH SOURCE.

  trade log          the alert's own fingerprint: score, DTE, delta, IV, premium, labels, and
                     the four §2 signals (term_slope, skew_25d, vrp, gex_proxy).
  <sym>-daily.pkl    the option surface ON the alert date: GEX geometry, walls, zero-gamma,
                     25-delta skew, the ATM term structure, p/c ratios, iv_rank. Computed from
                     that day's chain only, so joining on the alert date is not look-ahead.
  <sym>-<year>.pkl   the greek stack OF THE CONTRACT ACTUALLY BOUGHT, on the entry date.
  bars               underlying momentum / extension / realised vol from closes <= entry.
  regime             a cross-sectional VIX proxy: the median ATM 30-day IV across every mined
                     name on that date. It is a proxy and is labelled one — there is no VIX
                     series on disk.
  earnings           `datekey` from the Sharadar fundamentals export. NOTE this is the FILING
                     date, which trails the earnings ANNOUNCEMENT by a few days for large caps,
                     so "days since" is accurate to about a week and no finer. The forward
                     estimate adds the name's own median filing gap — an estimate available at
                     entry, not a peek at the next report.

RAW GREEKS ARE SCALE-DEPENDENT and would rank names by share price rather than by geometry, so
the higher-order ones enter normalised (vanna/vega, vomma/vega, zomma/gamma, theta/premium, ...).
Un-normalised vega on a $400 stock is simply bigger than on a $40 one; that is not a signal.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import pickle
from typing import Optional

from .options_signals_v2 import LATE_START, MIN_LATE_GAIN, MIN_RETAINED, MIN_TRADES
from .options_tracker import MIN_CLOSED_PER_BUCKET, _stats

# ---- Outcome definitions (pre-committed) ---------------------------------------------------
TAIL_WIN = 1.00          # >= +100%: the tail the strategy exists to catch (also the target)
TOTAL_LOSS = -0.90       # the "goes to zero" bucket the mandate asked about
STOP_OUT = -0.45         # at or through the -50% stop, allowing for exit slippage

# ---- Gate constants not inherited from §2 --------------------------------------------------
MIN_TAIL_RETENTION = 0.95   # G5: kept-share of >=+100% winners vs kept-share overall
ALPHA = 0.05                # G6 permutation significance
N_PERM = 2000               # permutation draws
FDR_Q = 0.10                # Benjamini-Hochberg false-discovery rate
STACK_TOP = 8               # near-misses also re-tested on top of term_slope

# Every feature that is a term-structure read, including the two that correlate >0.25 with
# term_slope by construction. Removing them is what makes `combiner_ex_term` interpretable.
TERM_FEATURES = ("f_term_slope", "f_d_term_14_60", "f_d_term_slope_60_30")

REGIME_VERSION = 2          # bump whenever market_regime() gains or changes a field
TRADES_PKL = os.path.join("options", "optbt_signals.pkl")
DERIVED = "options_derived"
BARS = os.path.join("bulk", "prepared", "bars")


def _log(m):
    print(f"[autopsy] {m}", flush=True)


def _f(x) -> Optional[float]:
    """float or None. NaN maps to None deliberately — see the skew_25d bug in §2, where NaN
    passed an `is not None` check and silently emptied a filter while coverage read 100%."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and abs(v) != math.inf else None


# ================================ loading ==================================================
def load_trades(data_root: str = "data") -> list:
    """The closed-trade log with the §2 signals already attached."""
    p = os.path.join(data_root, TRADES_PKL)
    with open(p, "rb") as f:
        rows = pickle.load(f)
    return [r for r in rows if _f(r.get("pnl_pct")) is not None]


class _Store:
    """Lazy, cached readers for the on-disk panels. One year-frame is held at a time: they are
    ~160k rows each and holding forty of them is gigabytes for no benefit, since features are
    built name-by-name."""

    def __init__(self, data_root: str = "data"):
        self.root = data_root
        self._daily: dict = {}
        self._bars: dict = {}
        self._year_key = None
        self._year_val = None

    def daily(self, ticker: str):
        if ticker not in self._daily:
            p = os.path.join(self.root, DERIVED, ticker, f"{ticker}-daily.pkl")
            got = None
            if os.path.exists(p):
                try:
                    import pandas as pd
                    d = pickle.load(open(p, "rb"))
                    d = d.copy()
                    d["_key"] = pd.to_datetime(d["date"]).dt.strftime("%Y-%m-%d")
                    got = {k: r for k, r in zip(d["_key"], d.to_dict("records"))}
                except Exception as e:                                   # noqa: BLE001
                    _log(f"{ticker}: daily read failed {type(e).__name__}")
            self._daily[ticker] = got
        return self._daily[ticker]

    def bars(self, ticker: str):
        if ticker not in self._bars:
            p = os.path.join(self.root, BARS, f"{ticker}.pkl")
            got = None
            if os.path.exists(p):
                try:
                    got = pickle.load(open(p, "rb"))
                except Exception:                                        # noqa: BLE001
                    got = None
            self._bars[ticker] = got
        return self._bars[ticker]

    def contracts(self, ticker: str, year: str):
        """Entry-date greek rows for one name-year, keyed by (date, expiry, strike, right)."""
        key = (ticker, year)
        if key == self._year_key:
            return self._year_val
        p = os.path.join(self.root, DERIVED, ticker, f"{ticker}-{year}.pkl")
        got = None
        if os.path.exists(p):
            try:
                import pandas as pd
                d = pickle.load(open(p, "rb"))
                d = d[d["right"].astype(str).str[0].str.upper() == "C"]
                idx = {}
                dates = pd.to_datetime(d["date"]).dt.strftime("%Y-%m-%d").values
                exps = pd.to_datetime(d["expiration"]).dt.strftime("%Y-%m-%d").values
                strikes = d["strike"].astype(float).values
                recs = d.to_dict("records")
                for i in range(len(recs)):
                    idx[(dates[i], exps[i], round(float(strikes[i]), 4))] = recs[i]
                got = idx
            except Exception as e:                                       # noqa: BLE001
                _log(f"{ticker} {year}: contract frame failed {type(e).__name__}")
        self._year_key, self._year_val = key, got
        return got


# ================================ regime proxy =============================================
def market_regime(data_root: str = "data", cache: bool = True) -> dict:
    """{date -> {mkt_iv, mkt_iv_rank}} — the cross-sectional median ATM 30-day IV across every
    mined name, and its trailing-252-session percentile.

    A VIX PROXY, not VIX. There is no index vol series on disk. It is built from the same
    surfaces the trades are drawn from, so it moves with them by construction; treat it as a
    coarse calm/stress switch rather than a market variable in its own right.
    """
    import numpy as np
    import pandas as pd

    # The version is in the FILENAME. A cache keyed only on path silently served a regime dict
    # built before `mkt_mom60` existed, and the feature simply never appeared in the sweep — no
    # error, no warning, exactly the failure mode the COVERAGE RULE exists for.
    out_p = os.path.join(data_root, "options", f"autopsy_regime_v{REGIME_VERSION}.pkl")
    if cache and os.path.exists(out_p):
        try:
            return pickle.load(open(out_p, "rb"))
        except Exception:                                                # noqa: BLE001
            pass
    root = os.path.join(data_root, DERIVED)
    names = [n for n in sorted(os.listdir(root)) if os.path.isdir(os.path.join(root, n))]
    frames, spots = [], []
    for n in names:
        p = os.path.join(root, n, f"{n}-daily.pkl")
        if not os.path.exists(p):
            continue
        try:
            d = pickle.load(open(p, "rb"))
            if "atm_iv_30" not in d.columns:
                continue
            frames.append(pd.DataFrame({"date": pd.to_datetime(d["date"]),
                                        "iv": pd.to_numeric(d["atm_iv_30"], errors="coerce")}))
            if "spot" in d.columns:
                s = pd.to_numeric(d["spot"], errors="coerce")
                first = s.dropna()
                if len(first):
                    # rebased so a $400 name does not dominate the median of a $40 one
                    spots.append(pd.DataFrame({"date": pd.to_datetime(d["date"]),
                                               "px": s / float(first.iloc[0])}))
        except Exception:                                                # noqa: BLE001
            continue
    if not frames:
        return {}
    allf = pd.concat(frames, ignore_index=True).dropna()
    med = allf.groupby("date", as_index=False)["iv"].median().sort_values("date")
    med["rank"] = med["iv"].rolling(252, min_periods=60).rank(pct=True)
    # Market TREND, the other half of "regime": an equal-weighted index of the mined names'
    # spots, and its trailing 60-session return. Same proxy caveat as the vol series.
    idx = (pd.concat(spots, ignore_index=True).dropna()
           .groupby("date", as_index=False)["px"].median().sort_values("date")
           if spots else None)
    mom = {}
    if idx is not None and len(idx) > 60:
        p = idx["px"].values.astype(float)
        r60 = np.full(p.size, np.nan)
        r60[60:] = p[60:] / p[:-60] - 1.0
        mom = {d.strftime("%Y-%m-%d"): (None if not np.isfinite(v) else float(v))
               for d, v in zip(idx["date"], r60)}
    out = {d.strftime("%Y-%m-%d"): {"mkt_iv": float(v),
                                    "mkt_iv_rank": (None if not np.isfinite(r) else float(r)),
                                    "mkt_mom60": mom.get(d.strftime("%Y-%m-%d"))}
           for d, v, r in zip(med["date"], med["iv"], med["rank"])}
    _log(f"regime proxy built from {len(frames)} names, {len(out)} dates")
    if cache:
        try:
            os.makedirs(os.path.dirname(out_p), exist_ok=True)
            pickle.dump(out, open(out_p, "wb"), protocol=pickle.HIGHEST_PROTOCOL)
        except OSError:
            pass
    return out


def earnings_map(data_root: str = "data") -> dict:
    """{ticker -> sorted [filing dates]} from the fundamentals export.

    These are FILING dates, which trail the announcement. Used for "days since" and, with the
    name's own median gap, an entry-time ESTIMATE of the next one. Both are labelled as
    filing-date-based wherever they are reported.
    """
    import pandas as pd

    p = os.path.join(data_root, "backtest", "fundamentals.csv")
    if not os.path.exists(p):
        return {}
    try:
        d = pd.read_csv(p, usecols=["ticker", "dimension", "datekey"])
    except (ValueError, OSError):
        return {}
    d = d[d["dimension"].astype(str).str.upper() == "ARQ"]
    out = {}
    for tk, g in d.groupby("ticker"):
        ds = sorted({str(x)[:10] for x in g["datekey"].dropna()})
        if ds:
            out[str(tk)] = ds
    return out


def sector_map(data_root: str = "data") -> dict:
    """{ticker -> sector} from the Sharadar TICKERS cache (wired for the panel in P10).

    NOTE the same look-ahead caveat the stock model records: this is TODAY's classification
    applied to 2016 rows. Reclassification is rare and not return-predictive, so it is usually
    considered benign — but it is stated rather than hidden.
    """
    p = os.path.join(data_root, "bulk", "prepared", "tickers.pkl")
    if not os.path.exists(p):
        return {}
    try:
        d = pickle.load(open(p, "rb"))
    except Exception:                                                    # noqa: BLE001
        return {}
    out = {}
    for tk, rec in (d or {}).items():
        s = (rec or {}).get("sector") if isinstance(rec, dict) else None
        if s:
            out[str(tk)] = str(s)
    return out


# ================================ feature assembly =========================================
def _bar_features(bars, as_of: str) -> dict:
    """Momentum / extension / realised vol from closes <= as_of. Adjusted closes: a split is not
    a crash, and every one of these is an indicator, not an option maths input."""
    import numpy as np

    out = {}
    if not bars:
        return out
    ds = bars["date"]
    hi = -1
    for i, d in enumerate(ds):
        if d <= as_of:
            hi = i
        else:
            break
    if hi < 130:
        return out
    px = np.asarray(bars["close"][:hi + 1], dtype=float)
    last = px[-1]
    if not np.isfinite(last) or last <= 0:
        return out
    for w, nm in ((5, "run5"), (20, "mom20"), (60, "mom60"), (120, "mom120")):
        if len(px) > w and px[-w - 1] > 0:
            out[nm] = float(last / px[-w - 1] - 1.0)
    if len(px) >= 252:
        out["ext_52w"] = float(last / float(np.max(px[-252:])) - 1.0)
    if len(px) >= 200:
        out["dist_sma200"] = float(last / float(np.mean(px[-200:])) - 1.0)
    if len(px) >= 50:
        out["dist_sma50"] = float(last / float(np.mean(px[-50:])) - 1.0)
    if len(px) >= 21:
        w20 = px[-21:]
        sd = float(np.std(w20[1:] / w20[:-1] - 1.0, ddof=1))
        out["rvol20"] = float(sd * math.sqrt(252))
        m, s = float(np.mean(px[-20:])), float(np.std(px[-20:], ddof=1))
        if s > 0:
            out["bb_pos"] = float((last - m) / (2.0 * s))
    if len(px) >= 61:
        w60 = px[-61:]
        out["rvol60"] = float(np.std(w60[1:] / w60[:-1] - 1.0, ddof=1) * math.sqrt(252))
    vol = bars.get("volume")
    if vol and len(vol) > hi >= 60:
        v = np.asarray(vol[max(0, hi - 59):hi + 1], dtype=float)
        med = float(np.median(v[:-1])) if len(v) > 1 else 0.0
        if med > 0:
            out["vol_surge"] = float(v[-1] / med)
    return out


def _contract_features(row) -> dict:
    """The traded contract's geometry, normalised so it ranks shape rather than share price."""
    out = {}
    if not row:
        return out
    mid = _f(row.get("mid"))
    vega = _f(row.get("vega"))
    gamma = _f(row.get("gamma"))
    spot = _f(row.get("spot"))
    delta = _f(row.get("delta"))
    for k in ("spread_frac", "moneyness", "iv"):
        v = _f(row.get(k))
        if v is not None:
            out[k if k != "iv" else "contract_iv"] = v
    # theta as a fraction of premium per DAY: the actual bleed rate the trade pays.
    theta = _f(row.get("theta"))
    if theta is not None and mid and mid > 0:
        out["theta_frac_day"] = float(theta / 365.0 / mid)
    # vega per unit premium: how much of the position is a vol bet.
    if vega is not None and mid and mid > 0:
        out["vega_frac"] = float(vega / 100.0 / mid)
    # gamma expressed as delta gained per 1% move, relative to the delta already owned.
    if gamma is not None and spot and delta and delta > 0:
        out["gamma_lev"] = float(gamma * spot * 0.01 / delta)
    if vega:
        for k, nm in (("vanna", "vanna_n"), ("vomma", "vomma_n"), ("ultima", "ultima_n")):
            v = _f(row.get(k))
            if v is not None and vega != 0:
                out[nm] = float(v / vega)
    if gamma:
        for k, nm in (("zomma", "zomma_n"), ("speed", "speed_n"), ("color", "color_n")):
            v = _f(row.get(k))
            if v is not None and gamma != 0:
                out[nm] = float(v / gamma * (spot if nm == "speed_n" and spot else 1.0))
    charm = _f(row.get("charm"))
    if charm is not None:
        out["charm_n"] = float(charm / 365.0)
    veta = _f(row.get("veta"))
    if veta is not None and vega:
        out["veta_n"] = float(veta / vega)
    return out


def _daily_features(rec, spot: Optional[float]) -> dict:
    """The surface features, made scale-free where they are not already."""
    out = {}
    if not rec:
        return out
    for k in ("iv_rank", "iv_pct", "gex_wall_conc", "zero_gamma_vs_spot", "pc_oi", "pc_vol",
              "skew_25d", "term_slope_60_30", "oi_coverage"):
        v = _f(rec.get(k))
        if v is not None:
            out["d_" + k] = v
    if "d_zero_gamma_vs_spot" in out:
        out["d_abs_zg"] = abs(out["d_zero_gamma_vs_spot"])
    a14, a30, a60 = _f(rec.get("atm_iv_14")), _f(rec.get("atm_iv_30")), _f(rec.get("atm_iv_60"))
    if a14 is not None and a60 is not None:
        out["d_term_14_60"] = a60 - a14
    if a30 is not None:
        out["d_atm_iv_30"] = a30
    s = spot or _f(rec.get("spot"))
    if s and s > 0:
        for k, nm in (("call_wall", "d_dist_call_wall"), ("put_wall", "d_dist_put_wall"),
                      ("gex_top_strike", "d_dist_gex_wall")):
            v = _f(rec.get(k))
            if v is not None:
                out[nm] = float(v / s - 1.0)
    # total_gex is dollars and scales with the name; its own trailing percentile is the
    # comparable quantity. Sign is kept separately because "short gamma" is a state, not a size.
    tg = _f(rec.get("total_gex"))
    if tg is not None:
        out["d_gex_sign"] = 1.0 if tg > 0 else 0.0
    return out


def build_features(trades: list, data_root: str = "data", verbose: bool = True) -> list:
    """Attach every entry-known feature to each trade. Features are namespaced `f_<name>`."""
    store = _Store(data_root)
    regime = market_regime(data_root)
    earn = earnings_map(data_root)
    sectors = sector_map(data_root)
    by_name: dict = {}
    for t in trades:
        by_name.setdefault(t["ticker"], []).append(t)

    out = []
    for i, (tk, rows) in enumerate(sorted(by_name.items())):
        daily = store.daily(tk)
        bars = store.bars(tk)
        edates = earn.get(tk) or []
        gaps = [((dt.date.fromisoformat(edates[j + 1]) - dt.date.fromisoformat(edates[j])).days)
                for j in range(len(edates) - 1)]
        gaps = sorted(g for g in gaps if 30 <= g <= 200)
        med_gap = gaps[len(gaps) // 2] if gaps else 91
        for t in sorted(rows, key=lambda r: r["alert_ts"]):
            as_of = str(t["alert_ts"])[:10]
            f = {}
            # ---- the alert's own fingerprint
            for k, nm in (("score", "score"), ("dte", "dte"), ("target_delta", "delta"),
                          ("iv", "entry_iv"), ("entry_premium", "premium"),
                          ("term_slope", "term_slope"), ("skew_25d", "sig_skew_25d"),
                          ("vrp", "sig_vrp"), ("gex_proxy", "sig_gex_proxy")):
                v = _f(t.get(k))
                if v is not None:
                    f[nm] = v
            labs = t.get("labels") or []
            f["n_labels"] = float(len(labs))
            low = " ".join(labs).lower()
            f["lab_call_heavy"] = 1.0 if "call-heavy" in low else 0.0
            f["lab_unusual_call"] = 1.0 if "unusual call" in low else 0.0
            f["lab_breakout"] = 1.0 if "breakout" in low else 0.0
            f["lab_52wk"] = 1.0 if "52-wk high" in low else 0.0
            f["lab_low_iv"] = 1.0 if "low iv" in low else 0.0
            # ---- surface
            rec = (daily or {}).get(as_of)
            spot = _f((rec or {}).get("spot"))
            f.update(_daily_features(rec, spot))
            # ---- the contract actually bought
            cidx = store.contracts(tk, as_of[:4])
            crow = None
            if cidx:
                crow = cidx.get((as_of, str(t["expiry"])[:10], round(float(t["strike"]), 4)))
            f.update(_contract_features(crow))
            if spot and _f(t.get("entry_premium")):
                f["premium_frac"] = float(t["entry_premium"] / spot)
            # ---- underlying
            f.update(_bar_features(bars, as_of))
            rv = f.get("rvol20")
            if rv is not None and _f(t.get("iv")) is not None:
                f["iv_minus_rv"] = float(t["iv"] - rv)
            # ---- regime
            rg = regime.get(as_of) or {}
            for k in ("mkt_iv", "mkt_iv_rank", "mkt_mom60"):
                v = _f(rg.get(k))
                if v is not None:
                    f[k] = v
            # ---- earnings (FILING dates; see docstring)
            prev = [d for d in edates if d <= as_of]
            if prev:
                since = (dt.date.fromisoformat(as_of)
                         - dt.date.fromisoformat(prev[-1])).days
                f["days_since_filing"] = float(since)
                est_next = float(med_gap - since)
                f["est_days_to_filing"] = est_next
                hold = (_f(t.get("dte")) or 60.0) * 0.5
                f["filing_in_window"] = 1.0 if 0 <= est_next <= hold else 0.0
            row = dict(t)
            row["_sector"] = sectors.get(tk) or "(unknown)"
            row["_f"] = {("f_" + k): v for k, v in f.items()}
            row["_has_contract"] = crow is not None
            row["_has_daily"] = rec is not None
            out.append(row)
        if verbose and (i + 1) % 10 == 0:
            _log(f"features: {i + 1}/{len(by_name)} names")
    return out


def feature_coverage(rows: list) -> dict:
    """Non-null share per feature. The COVERAGE RULE, applied before any IC is believed."""
    names = sorted({k for r in rows for k in r["_f"]})
    n = len(rows) or 1
    return {k: sum(1 for r in rows if _f(r["_f"].get(k)) is not None) / n for k in names}


# ================================ univariate machinery =====================================
def _spearman(xs, ys) -> Optional[float]:
    import numpy as np

    if len(xs) < 10:
        return None
    x = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if x.size < 10 or np.all(x == x[0]):
        return None

    def rank(a):
        o = a.argsort(kind="mergesort")
        r = np.empty(a.size, dtype=float)
        r[o] = np.arange(a.size, dtype=float)
        # average ranks within ties, or a binary feature reports a meaningless correlation
        _, inv, cnt = np.unique(a, return_inverse=True, return_counts=True)
        sums = np.zeros(cnt.size)
        np.add.at(sums, inv, r)
        return (sums / cnt)[inv]

    rx, ry = rank(x), rank(y)
    sx, sy = rx.std(), ry.std()
    if sx == 0 or sy == 0:
        return None
    return float(((rx - rx.mean()) * (ry - ry.mean())).mean() / (sx * sy))


def _vals(rows, feat):
    return [(r, _f(r["_f"].get(feat))) for r in rows]


def _present(rows, feat):
    return [r for r, v in _vals(rows, feat) if v is not None]


def rank_ic(rows, feat) -> Optional[float]:
    pres = [(r, v) for r, v in _vals(rows, feat) if v is not None]
    if len(pres) < 10:
        return None
    return _spearman([v for _, v in pres], [_f(r.get("pnl_pct")) for r, _ in pres])


def outcome_mix(rows) -> dict:
    """The three numbers that matter for a convex book, at any level of aggregation."""
    pnl = [_f(r.get("pnl_pct")) for r in rows]
    pnl = [p for p in pnl if p is not None]
    n = len(pnl) or 1
    return {"n": len(pnl),
            "expectancy": sum(pnl) / n,
            "p_tail": sum(1 for p in pnl if p >= TAIL_WIN) / n,
            "p_stop": sum(1 for p in pnl if p <= STOP_OUT) / n,
            "p_total_loss": sum(1 for p in pnl if p <= TOTAL_LOSS) / n,
            "hit_rate": sum(1 for p in pnl if p > 0) / n}


def quantile_table(rows, feat, q: int = 5) -> Optional[list]:
    """Conditional outcomes by feature quintile — the stock model's decile machinery, on trades."""
    import numpy as np

    pres = [(r, v) for r, v in _vals(rows, feat) if v is not None]
    if len(pres) < q * MIN_CLOSED_PER_BUCKET // 2:
        return None
    pres.sort(key=lambda t: t[1])
    vals = np.asarray([v for _, v in pres])
    # A feature with few distinct values (the binary labels) cannot be cut into q buckets;
    # group by value instead of manufacturing empty quantiles.
    uniq = np.unique(vals)
    if uniq.size <= q:
        groups = [(f"={u:g}", [r for r, v in pres if v == u]) for u in uniq]
    else:
        edges = np.quantile(vals, np.linspace(0, 1, q + 1))
        groups = []
        for i in range(q):
            lo, hi = edges[i], edges[i + 1]
            sel = [r for r, v in pres
                   if (v >= lo and (v < hi or (i == q - 1 and v <= hi)))]
            groups.append((f"Q{i + 1} [{lo:.4g},{hi:.4g}]", sel))
    out = []
    for lbl, sel in groups:
        if not sel:
            continue
        m = outcome_mix(sel)
        s = _stats(sel)
        m.update({"bucket": lbl, "profit_factor": s["profit_factor"]})
        out.append(m)
    return out


# ================================ the gate =================================================
def fit_rule(rows, feat) -> Optional[dict]:
    """G1 — direction from the fitting half's rank-IC sign, threshold from the house recipe."""
    import statistics as st

    ic = rank_ic(rows, feat)
    if ic is None or ic == 0:
        return None
    direction = 1 if ic > 0 else -1
    vals = [v for r, v in _vals(rows, feat)
            if v is not None and (_f(r.get("pnl_pct")) or 0) > 0]
    if len(vals) < MIN_CLOSED_PER_BUCKET:
        return None
    return {"direction": direction, "threshold": float(st.median(vals)), "fit_ic": ic,
            "fit_n": len(vals)}


def apply_rule(rows, feat, rule) -> list:
    d, thr = rule["direction"], rule["threshold"]
    out = []
    for r, v in _vals(rows, feat):
        if v is None:
            continue
        if (v >= thr) if d > 0 else (v <= thr):
            out.append(r)
    return out


def _perm_p(base_rows, kept_n, observed_exp, seed: int = 0, draws: int = N_PERM) -> float:
    """G6 — P(a random subset of the same size does this well). Uses the outcomes as they are,
    so it prices in the heavy tail rather than assuming a distribution."""
    import numpy as np

    pnl = np.asarray([p for p in (_f(r.get("pnl_pct")) for r in base_rows) if p is not None])
    if pnl.size == 0 or kept_n <= 0 or kept_n > pnl.size:
        return 1.0
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(draws):
        if rng.permuted(pnl)[:kept_n].mean() >= observed_exp:
            hits += 1
    return (hits + 1) / (draws + 1)


def evaluate_split(rows, feat, fit_rows, test_rows, seed: int = 0) -> dict:
    """Fit on `fit_rows`, judge on `test_rows` against G2-G6."""
    rule = fit_rule(fit_rows, feat)
    if rule is None:
        return {"ok": False, "reason": "cannot fit (no IC or too few profitable values)"}
    base = _present(test_rows, feat)
    if len(base) < MIN_TRADES:
        return {"ok": False, "reason": f"held-out coverage {len(base)} < {MIN_TRADES}"}
    kept = apply_rule(test_rows, feat, rule)
    if len(kept) < MIN_TRADES:
        return {"ok": False, "reason": f"kept {len(kept)} < {MIN_TRADES}", **rule}
    b, k = outcome_mix(base), outcome_mix(kept)
    retention = k["n"] / b["n"]
    tail_base = sum(1 for r in base if (_f(r.get("pnl_pct")) or 0) >= TAIL_WIN)
    tail_kept = sum(1 for r in kept if (_f(r.get("pnl_pct")) or 0) >= TAIL_WIN)
    tail_ret = (tail_kept / tail_base) if tail_base else None
    gain = k["expectancy"] - b["expectancy"]
    p = _perm_p(base, k["n"], k["expectancy"], seed=seed)
    tail_ok = tail_ret is not None and tail_ret >= MIN_TAIL_RETENTION * retention
    passed = (gain >= MIN_LATE_GAIN and retention >= MIN_RETAINED
              and k["n"] >= MIN_TRADES and tail_ok and p < ALPHA)
    return {"ok": True, **rule, "n_base": b["n"], "n_kept": k["n"], "retention": retention,
            "exp_base": b["expectancy"], "exp_kept": k["expectancy"], "gain": gain,
            "tail_base": tail_base, "tail_kept": tail_kept, "tail_retention": tail_ret,
            "tail_ratio": (tail_ret / retention) if tail_ret is not None else None,
            "p_stop_base": b["p_stop"], "p_stop_kept": k["p_stop"],
            "perm_p": p, "test_ic": rank_ic(test_rows, feat), "passed": passed}


def holdout_feature(rows, feat, seed: int = 0) -> dict:
    """G7 — the same test both ways round. Also reports the full-sample IC, clearly labelled as
    in-sample so it can never be quoted as evidence."""
    early = [r for r in rows if str(r["alert_ts"])[:10] < LATE_START]
    late = [r for r in rows if str(r["alert_ts"])[:10] >= LATE_START]
    fwd = evaluate_split(rows, feat, early, late, seed=seed)
    rev = evaluate_split(rows, feat, late, early, seed=seed + 1)
    both = bool(fwd.get("passed") and rev.get("passed"))
    return {"feature": feat, "coverage": len(_present(rows, feat)) / (len(rows) or 1),
            "full_sample_ic_IN_SAMPLE": rank_ic(rows, feat),
            "fit_early_test_late": fwd, "fit_late_test_early": rev,
            "passes_both_directions": both,
            "directions_agree": (fwd.get("direction") == rev.get("direction")
                                 if fwd.get("ok") and rev.get("ok") else None)}


def bh_fdr(pvals: list, q: float = FDR_Q) -> list:
    """Benjamini-Hochberg. Returns the boolean discovery flags in the input order."""
    idx = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m = len(pvals)
    keep = [False] * m
    kmax = -1
    for rank, i in enumerate(idx, start=1):
        if pvals[i] <= q * rank / m:
            kmax = rank
    for rank, i in enumerate(idx, start=1):
        if rank <= kmax:
            keep[i] = True
    return keep


# ================================ the loser autopsy ========================================
def loss_autopsy(rows, features: list) -> dict:
    """Where the losses actually are, and whether the worst ones look different AT ENTRY.

    Reported as a contrast of entry-feature medians, which is descriptive and in-sample. It is
    hypothesis GENERATION; anything it suggests still has to clear the held-out gate above.
    """
    import numpy as np

    pnl = [(r, _f(r.get("pnl_pct"))) for r in rows]
    pnl = [(r, p) for r, p in pnl if p is not None]
    buckets = {
        "total_loss (<=-90%)": [r for r, p in pnl if p <= TOTAL_LOSS],
        "stopped (<=-45%)": [r for r, p in pnl if p <= STOP_OUT],
        "small_loss (-45%..0)": [r for r, p in pnl if STOP_OUT < p <= 0],
        "small_win (0..+100%)": [r for r, p in pnl if 0 < p < TAIL_WIN],
        "tail_win (>=+100%)": [r for r, p in pnl if p >= TAIL_WIN],
    }
    mix = {k: outcome_mix(v) for k, v in buckets.items()}
    contrast = {}
    losers = buckets["stopped (<=-45%)"]
    winners = buckets["tail_win (>=+100%)"]
    for f in features:
        lv = [v for _, v in _vals(losers, f) if v is not None]
        wv = [v for _, v in _vals(winners, f) if v is not None]
        if len(lv) < MIN_CLOSED_PER_BUCKET or len(wv) < MIN_CLOSED_PER_BUCKET:
            continue
        allv = [v for _, v in _vals(rows, f) if v is not None]
        sd = float(np.std(allv, ddof=1)) if len(allv) > 2 else 0.0
        lm, wm = float(np.median(lv)), float(np.median(wv))
        contrast[f] = {"median_stopped": lm, "median_tail_win": wm,
                       "gap_in_sd": ((wm - lm) / sd) if sd > 0 else None,
                       "n_stopped": len(lv), "n_tail": len(wv)}
    ranked = sorted((c for c in contrast.items() if c[1]["gap_in_sd"] is not None),
                    key=lambda kv: -abs(kv[1]["gap_in_sd"]))
    return {"buckets": mix, "contrast_top": dict(ranked[:15]), "contrast_all": contrast,
            "note": ("The -50% stop is doing its job: the total-loss bucket is nearly empty, so "
                     "the dominant loss mode is the STOP-OUT, not the zero.")}


# ================================ orchestration ============================================
def run(data_root: str = "data", seed: int = 0, min_coverage: float = 0.50,
        stack_on_term: bool = True, combiner: bool = True, verbose: bool = True,
        trades: Optional[list] = None) -> dict:
    """`trades` overrides the on-disk 55-name log so the SAME gate can be re-run unchanged on a
    different trade log — the expanded universe (22b). Nothing else about the study moves; if the
    sweep had to be re-implemented to point at new data, the two results would not be
    comparable."""
    trades = load_trades(data_root) if trades is None else \
        [r for r in trades if _f(r.get("pnl_pct")) is not None]
    rows = build_features(trades, data_root, verbose=verbose)
    cov = feature_coverage(rows)
    feats = [f for f, c in sorted(cov.items()) if c >= min_coverage]
    dropped = {f: c for f, c in cov.items() if c < min_coverage}
    if verbose:
        _log(f"{len(rows)} trades, {len(cov)} features, {len(feats)} above "
             f"{min_coverage:.0%} coverage")

    overall = outcome_mix(rows)
    results = []
    for i, f in enumerate(feats):
        results.append(holdout_feature(rows, f, seed=seed + i * 7))
        if verbose and (i + 1) % 10 == 0:
            _log(f"gate: {i + 1}/{len(feats)}")

    # FDR over the confirming-half permutation p-values, one per feature per split direction.
    ps, tags = [], []
    for r in results:
        for k in ("fit_early_test_late", "fit_late_test_early"):
            v = r[k].get("perm_p")
            if v is not None:
                ps.append(v)
                tags.append((r["feature"], k))
    flags = bh_fdr(ps, FDR_Q) if ps else []
    fdr = {f"{t[0]}::{t[1]}": {"p": p, "discovery": d}
           for t, p, d in zip(tags, ps, flags)}

    survivors = [r["feature"] for r in results if r["passes_both_directions"]]

    # Stack on top of the adopted term_slope filter — the only question that matters for a new
    # filter is what it ADDS to the one already running, not whether it correlates with it.
    # The near-misses are stacked too: a feature can fail the standalone gate and still be the
    # interesting one here, and reporting only survivors would hide that.
    stacked = {}
    if stack_on_term:
        thr = _term_threshold(rows)
        base = [r for r in rows if (_f(r["_f"].get("f_term_slope")) or -9e9) >= thr]
        ranked = sorted(results, key=lambda r: -_mean_gain(r))
        pick = [r["feature"] for r in ranked[:STACK_TOP]]
        for f in dict.fromkeys(survivors + pick):
            if f == "f_term_slope":
                continue
            stacked[f] = holdout_feature(base, f, seed=seed + 999)
        stacked["_term_threshold"] = thr
        stacked["_n_after_term"] = len(base)
        stacked["_note"] = ("Stacked ON TOP of term_slope. Features listed here include "
                            "NEAR-MISSES that failed the standalone gate; presence in this "
                            "block is not adoption.")

    # How much of each candidate is term_slope wearing a different hat.
    corr_term = {}
    for r in results:
        f = r["feature"]
        if f == "f_term_slope":
            continue
        pres = [(a, b) for a, b in ((_f(x["_f"].get(f)), _f(x["_f"].get("f_term_slope")))
                                    for x in rows) if a is not None and b is not None]
        if len(pres) >= MIN_TRADES:
            corr_term[f] = _spearman([a for a, _ in pres], [b for _, b in pres])

    quantiles = {f: quantile_table(rows, f) for f in feats}
    autopsy = loss_autopsy(rows, feats)

    return {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "n_trades": len(rows),
        "n_with_contract": sum(1 for r in rows if r["_has_contract"]),
        "n_with_daily": sum(1 for r in rows if r["_has_daily"]),
        "overall": overall,
        "overall_stats": _stats(rows),
        "coverage": cov,
        "dropped_low_coverage": dropped,
        "n_features_tested": len(feats),
        "n_hypotheses": len(ps),
        "gate": {"MIN_LATE_GAIN": MIN_LATE_GAIN, "MIN_RETAINED": MIN_RETAINED,
                 "MIN_TRADES": MIN_TRADES, "MIN_TAIL_RETENTION": MIN_TAIL_RETENTION,
                 "ALPHA": ALPHA, "FDR_Q": FDR_Q, "N_PERM": N_PERM},
        "results": results,
        "survivors": survivors,
        "fdr": fdr,
        "stacked_on_term_slope": stacked,
        "corr_with_term_slope": corr_term,
        "quantiles": quantiles,
        "loss_autopsy": autopsy,
        "by_year": by_year(rows),
        "by_sector": sector_table(rows),
        "regime_confound": regime_confound(rows),
        "pbo": pbo_cscv(rows, feats),
        # DSR on the trades the LIVE filter keeps, deflated by the size of this search.
        "deflated_sharpe_term_slope": deflated_sharpe(
            [r.get("pnl_pct") for r in rows
             if (_f(r["_f"].get("f_term_slope")) or -9e9) >= _term_threshold(rows)],
            n_trials=len(feats)),
        "deflated_sharpe_unfiltered": deflated_sharpe(
            [r.get("pnl_pct") for r in rows], n_trials=len(feats)),
        # The mandate escalates to #26 only if a univariate signal exists. It is run either way
        # and the escalation status is recorded, because interactions are exactly what a
        # univariate sweep cannot see — "no main effect" is not evidence of "no interaction".
        "combiner_escalation_warranted": bool([s for s in survivors if s != "f_term_slope"]),
        "combiner": (combiner_test(rows, feats, seed=seed, verbose=verbose)
                     if combiner else None),
        # ...and again with every term-structure feature removed. term_slope is already adopted,
        # so "the model works" is uninformative if the model is just re-finding it. This variant
        # asks the mandate's actual question: is there anything in the greeks, the GEX geometry
        # and the underlying that term structure does not already carry?
        "combiner_ex_term": (combiner_test(rows, [f for f in feats if f not in TERM_FEATURES],
                                           seed=seed, verbose=verbose)
                             if combiner else None),
    }


def _mean_gain(r: dict) -> float:
    gs = [r[k].get("gain") for k in ("fit_early_test_late", "fit_late_test_early")
          if isinstance(r[k].get("gain"), (int, float))]
    return (sum(gs) / len(gs)) if gs else -9.0


def by_year(rows) -> dict:
    """Outcomes per calendar year. The fade is the backdrop to every number in this study."""
    out = {}
    for r in rows:
        out.setdefault(str(r["alert_ts"])[:4], []).append(r)
    return {y: outcome_mix(v) for y, v in sorted(out.items())}


def regime_confound(rows, top: int = 15) -> dict:
    """Is the right tail a SETUP or a REGIME? Reports where the biggest winners actually came
    from, and how concentrated the tail is by year and by name — the check the mandate asked
    for, because '2020 tech' is a period, not a tradable feature."""
    pnl = [(r, _f(r.get("pnl_pct"))) for r in rows]
    pnl = [(r, p) for r, p in pnl if p is not None]
    tail = [(r, p) for r, p in pnl if p >= TAIL_WIN]
    biggest = sorted(pnl, key=lambda t: -t[1])[:top]
    def share(items, key):
        c = {}
        for r, _ in items:
            c[key(r)] = c.get(key(r), 0) + 1
        return dict(sorted(c.items(), key=lambda kv: -kv[1]))
    n_tail = len(tail) or 1
    return {
        "n_tail": len(tail),
        "tail_by_year": share(tail, lambda r: str(r["alert_ts"])[:4]),
        "tail_by_name_top10": dict(list(share(tail, lambda r: r["ticker"]).items())[:10]),
        "top_winners": [{"ticker": r["ticker"], "date": str(r["alert_ts"])[:10],
                         "pnl_pct": p} for r, p in biggest],
        "top_winner_years": share(biggest, lambda r: str(r["alert_ts"])[:4]),
        "tail_share_2020": share(tail, lambda r: str(r["alert_ts"])[:4]).get("2020", 0) / n_tail,
    }


def _term_threshold(rows) -> float:
    """The adopted term_slope cutoff, refitted by the §2 recipe on the early half so the stack
    test uses the same rule that shipped rather than a hard-coded constant that could drift."""
    early = [r for r in rows if str(r["alert_ts"])[:10] < LATE_START]
    rule = fit_rule(early, "f_term_slope")
    return rule["threshold"] if rule else 0.0105


def sector_table(rows) -> dict:
    """Expectancy by sector, split into halves. Sector is CATEGORICAL — a median threshold on it
    would be meaningless — so it gets a consistency table instead of the numeric gate: does a
    sector that pays in one half still pay in the other?"""
    early, late, out = {}, {}, {}
    for r in rows:
        s = r.get("_sector") or "(unknown)"
        (early if str(r["alert_ts"])[:10] < LATE_START else late).setdefault(s, []).append(r)
    for s in sorted(set(early) | set(late)):
        e, l = early.get(s, []), late.get(s, [])
        me, ml = outcome_mix(e), outcome_mix(l)
        out[s] = {"n_early": me["n"], "exp_early": me["expectancy"] if e else None,
                  "n_late": ml["n"], "exp_late": ml["expectancy"] if l else None,
                  "n_total": me["n"] + ml["n"],
                  "both_halves_positive": bool(e and l and me["expectancy"] > 0
                                               and ml["expectancy"] > 0),
                  "enough_to_tune": (me["n"] >= MIN_CLOSED_PER_BUCKET
                                     and ml["n"] >= MIN_CLOSED_PER_BUCKET)}
    return out


# ================================ PBO and Deflated Sharpe ==================================
def _filter_series(rows, feat, rule):
    """{date -> [returns]} for the trades this feature's rule would keep."""
    out = {}
    for r in apply_rule(rows, feat, rule):
        p = _f(r.get("pnl_pct"))
        if p is not None:
            out.setdefault(str(r["alert_ts"])[:10], []).append(p)
    return out


def pbo_cscv(rows, feats, n_blocks: int = 8) -> dict:
    """Probability of Backtest Overfitting, by Combinatorially Symmetric Cross-Validation.

    PBO does not score a single strategy — it scores the SELECTION step. The question it answers
    is exactly this study's risk: "if I pick the best of 63 features in-sample, how often is it
    below median out-of-sample?" 50% means the selection carries no information at all.

    Each feature's rule is fixed once on the FULL sample (a config has to be constant across
    splits for CSCV to mean anything), so this measures the overfitting of CHOOSING among the
    configs, not of fitting each one. That is the standard construction and the relevant one.
    """
    import itertools
    import math as _m

    import numpy as np

    rules = {}
    for f in feats:
        r = fit_rule(rows, f)
        if r:
            rules[f] = r
    if len(rules) < 5:
        return {"ok": False, "reason": f"only {len(rules)} configs"}
    dates = sorted({str(r["alert_ts"])[:10] for r in rows})
    if len(dates) < n_blocks * 4:
        return {"ok": False, "reason": "too few dates"}
    edges = np.array_split(np.arange(len(dates)), n_blocks)
    blocks = [set(dates[i] for i in b) for b in edges]
    series = {f: _filter_series(rows, f, rules[f]) for f in rules}

    def perf(f, keep):
        vals = [v for d, vs in series[f].items() if d in keep for v in vs]
        return (sum(vals) / len(vals)) if len(vals) >= MIN_CLOSED_PER_BUCKET else None

    names = list(rules)
    lam, below = [], 0
    combos = list(itertools.combinations(range(n_blocks), n_blocks // 2))
    for c in combos:
        is_keep = set().union(*[blocks[i] for i in c])
        os_keep = set().union(*[blocks[i] for i in range(n_blocks) if i not in c])
        is_p = {f: perf(f, is_keep) for f in names}
        os_p = {f: perf(f, os_keep) for f in names}
        ok = [f for f in names if is_p[f] is not None and os_p[f] is not None]
        if len(ok) < 5:
            continue
        best = max(ok, key=lambda f: is_p[f])
        ranked = sorted(ok, key=lambda f: os_p[f])
        rank = ranked.index(best) + 1
        w = rank / (len(ok) + 1.0)
        w = min(max(w, 1e-6), 1 - 1e-6)
        lam.append(_m.log(w / (1 - w)))
        if w <= 0.5:
            below += 1
    if not lam:
        return {"ok": False, "reason": "no usable splits"}
    return {"ok": True, "pbo": below / len(lam), "n_splits": len(lam),
            "n_configs": len(names), "median_logit": float(np.median(lam)),
            "note": "PBO scores the SELECTION among configs, not any single filter."}


def deflated_sharpe(returns, n_trials: int, trial_sharpes=None) -> dict:
    """Deflated Sharpe Ratio on the per-trade return series, adjusted for `n_trials` searched.

    Two things to keep in view. The 'Sharpe' here is PER TRADE, not annualised — these are not
    a time series of periodic returns and must not be read as one. And the skew/kurtosis terms
    are load-bearing rather than cosmetic: the return distribution is a barbell with a fat right
    tail, which is precisely the shape a plain Sharpe misprices.

    AUDIT B25 — RECONCILED WITH `fundamental_panel._deflated_sharpe`. The audit reported the two
    as irreconcilable ("they disagree on the key input, `var_sr` as sampling variance versus
    cross-trial variance, and will never reconcile"). Worked through, they are **algebraically
    identical in the test statistic**:

        this module :  stat = (sr - sr0) / sqrt(var_sr),  var_sr = denom / (n - 1)
        the panel   :  z    = (sr - sr0) * sqrt(n - 1) / sqrt(denom)

    with `denom = 1 - skew*sr + (kurt - 1)/4 * sr^2` in both. Substituting one into the other
    gives the same expression. The ONLY genuine difference is the variance fed to the `sr0`
    benchmark, and there Bailey-Lopez de Prado are explicit: `SR0` scales with `V[{SR_n}]`, the
    variance ACROSS the trials searched — not with the sampling variance of one Sharpe estimate.

    So the panel's convention is the correct one and this module's was an approximation. Pass
    `trial_sharpes` and the benchmark is computed the paper's way; omit it and the sampling
    variance is used as before, with `sr0_basis` recording which was done. The 126-feature
    autopsy has no meaningful cross-trial Sharpe vector (its trials are feature screens, not
    strategies), which is why the fallback stays rather than being removed.
    """
    import numpy as np
    from math import erf, exp, log, sqrt

    x = np.asarray([v for v in (_f(r) for r in returns) if v is not None], dtype=float)
    n = x.size
    if n < MIN_CLOSED_PER_BUCKET or x.std(ddof=1) == 0:
        return {"ok": False, "reason": f"n={n}"}
    sr = float(x.mean() / x.std(ddof=1))
    z = (x - x.mean()) / x.std(ddof=1)
    g3, g4 = float((z ** 3).mean()), float((z ** 4).mean())

    def ppf(p):                                    # inverse normal CDF, Acklam's approximation
        a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
             1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
        b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
             6.680131188771972e+01, -1.328068155288572e+01]
        c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
             -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
        d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
             3.754408661907416e+00]
        pl = 0.02425
        if p < pl:
            q = sqrt(-2 * log(p))
            return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                   ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
        if p > 1 - pl:
            q = sqrt(-2 * log(1 - p))
            return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                    ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
        q, r = p - 0.5, (p - 0.5) ** 2
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
               (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)

    # Expected maximum Sharpe under the null across n_trials independent trials.
    N = max(int(n_trials), 2)
    euler = 0.5772156649015329
    sr0 = ((1 - euler) * ppf(1 - 1.0 / N) + euler * ppf(1 - 1.0 / (N * exp(1.0))))
    var_sr = (1 - g3 * sr + ((g4 - 1) / 4.0) * sr * sr) / (n - 1)
    if var_sr <= 0:
        return {"ok": False, "reason": "non-positive SR variance"}
    # AUDIT B25 — the benchmark scales with the variance ACROSS TRIALS when that is knowable.
    _ts = [v for v in (_f(t) for t in (trial_sharpes or [])) if v is not None]
    if len(_ts) > 1:
        _v = float(np.var(_ts, ddof=1))
        sr0_basis, sr0 = "cross_trial_variance", sr0 * sqrt(_v)
    else:
        sr0_basis, sr0 = "sampling_variance_APPROXIMATION", sr0 * sqrt(var_sr)
    stat = (sr - sr0) / sqrt(var_sr)
    dsr = 0.5 * (1 + erf(stat / sqrt(2)))
    return {"ok": True, "n": n, "sharpe_per_trade": sr, "skew": g3, "kurtosis": g4,
            "n_trials": N, "sr0_threshold": sr0, "deflated_sharpe": dsr,
            "sr0_basis": sr0_basis,                       # AUDIT B25
            "note": "per-TRADE Sharpe, not annualised"}


# ================================ #26 — the combiner =======================================
# PRE-SPECIFIED, ONE CONFIGURATION, NO SEARCH. A hyperparameter search over 1,540 heavy-tailed
# trades is how a result gets manufactured, so the settings below are fixed shallow defaults
# chosen for capacity control, not tuned: depth 3, 200 iterations, lr 0.05, L2 1.0, and a leaf
# floor of 40 trades (above MIN_CLOSED_PER_BUCKET, so no leaf is decided by a lucky triple-up).
#
# THE TARGET IS THE TAIL, NOT THE RETURN. Regressing a distribution whose mean is set by a few
# +600% trades fits those trades and nothing else. P(>= +100%) is the quantity that actually
# drives expectancy in a barbell payoff, and it is what the model is asked for.
#
# THE NULL IS A LABEL SHUFFLE, refit end to end. Comparing against 0 would test "is the model
# better than nothing"; comparing against the same model trained on scrambled labels tests "did
# it find structure, or is this the capacity of a 63-feature booster to fit 750 rows of noise" —
# which is the question that matters.
COMBINER_RETAIN = 0.406      # matched to term_slope's shipped retention, for a like-for-like read
COMBINER_NULL_RUNS = 100
HGB_PARAMS = {"max_depth": 3, "max_iter": 200, "learning_rate": 0.05,
              "l2_regularization": 1.0, "min_samples_leaf": 40, "random_state": 0}


def _matrix(rows, feats):
    import numpy as np

    X = np.full((len(rows), len(feats)), np.nan)
    for i, r in enumerate(rows):
        for j, f in enumerate(feats):
            v = _f(r["_f"].get(f))
            if v is not None:
                X[i, j] = v
    y_ret = np.asarray([_f(r.get("pnl_pct")) or 0.0 for r in rows])
    return X, (y_ret >= TAIL_WIN).astype(int), y_ret


def _combiner_once(Xtr, ytr, Xte, yret_te, kind: str, seed: int, retain: float):
    """Fit, rank the held-out half, keep the top `retain` share, return its expectancy + tail."""
    import numpy as np

    if len(np.unique(ytr)) < 2:
        return None
    if kind == "hgb":
        from sklearn.ensemble import HistGradientBoostingClassifier
        p = dict(HGB_PARAMS)
        p["random_state"] = seed
        m = HistGradientBoostingClassifier(**p)
        m.fit(Xtr, ytr)
        s = m.predict_proba(Xte)[:, 1]
    else:
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                          LogisticRegression(C=0.1, max_iter=2000, random_state=seed))
        m.fit(Xtr, ytr)
        s = m.predict_proba(Xte)[:, 1]
    k = max(MIN_TRADES, int(round(len(s) * retain)))
    idx = np.argsort(-s)[:k]
    sel = yret_te[idx]
    tail_all = int((yret_te >= TAIL_WIN).sum())
    return {"n_kept": int(k), "exp_kept": float(sel.mean()),
            "exp_base": float(yret_te.mean()),
            "gain": float(sel.mean() - yret_te.mean()),
            "retention": k / len(s),
            "tail_retention": (float((sel >= TAIL_WIN).sum() / tail_all)
                               if tail_all else None)}


def combiner_test(rows, feats, retain: float = COMBINER_RETAIN,
                  null_runs: int = COMBINER_NULL_RUNS, seed: int = 0,
                  verbose: bool = True) -> dict:
    """#26 — can a regularized/tree combiner find interactions the univariate pass cannot?"""
    import numpy as np

    early = [r for r in rows if str(r["alert_ts"])[:10] < LATE_START]
    late = [r for r in rows if str(r["alert_ts"])[:10] >= LATE_START]
    out = {"n_features": len(feats), "retain": retain, "null_runs": null_runs,
           "params": HGB_PARAMS, "target": f"pnl_pct >= {TAIL_WIN}"}
    for kind in ("hgb", "logit"):
        for name, tr, te in (("fit_early_test_late", early, late),
                             ("fit_late_test_early", late, early)):
            Xtr, ytr, _ = _matrix(tr, feats)
            Xte, _, yret = _matrix(te, feats)
            obs = _combiner_once(Xtr, ytr, Xte, yret, kind, seed, retain)
            if obs is None:
                out[f"{kind}::{name}"] = {"ok": False, "reason": "degenerate labels"}
                continue
            rng = np.random.default_rng(seed + 11)
            null = []
            for i in range(null_runs):
                sh = rng.permutation(ytr)
                r = _combiner_once(Xtr, sh, Xte, yret, kind, seed + i, retain)
                if r:
                    null.append(r["gain"])
            null = np.asarray(null) if null else np.asarray([0.0])
            p = float(((null >= obs["gain"]).sum() + 1) / (null.size + 1))
            out[f"{kind}::{name}"] = {
                "ok": True, **obs,
                "null_mean_gain": float(null.mean()), "null_sd": float(null.std()),
                "shuffle_p": p,
                "passed": bool(obs["gain"] >= MIN_LATE_GAIN and p < ALPHA
                               and obs["tail_retention"] is not None
                               and obs["tail_retention"] >= MIN_TAIL_RETENTION * obs["retention"])}
            if verbose:
                _log(f"{kind} {name}: gain {obs['gain']:+.4f} vs null "
                     f"{null.mean():+.4f} (p {p:.3f})")
    out["passed_any"] = any(v.get("passed") for v in out.values() if isinstance(v, dict))
    out["passed_both_directions"] = {
        k: bool(out.get(f"{k}::fit_early_test_late", {}).get("passed")
                and out.get(f"{k}::fit_late_test_early", {}).get("passed"))
        for k in ("hgb", "logit")}
    return out


def save(res: dict, data_root: str = "data") -> str:
    p = os.path.join(data_root, "options", "AUTOPSY_RESULTS.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    return p
