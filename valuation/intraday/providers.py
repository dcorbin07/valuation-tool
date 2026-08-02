"""
Intraday data providers.

  * TradierProvider — real-time quotes, daily history, and option chains via your
    Tradier token (best for an always-running scanner). Set TRADIER_TOKEN and
    TRADIER_ENV (sandbox|live).
  * FreeProvider — yfinance fallback (delayed): daily history + nearest-expiry
    option chain. Works with no key.

Both emit the same shapes the signal engine needs:
  bars           -> {"close":[...], "high":[...], "low":[...], "volume":[...]}
  option_summary -> {"put_volume","call_volume","put_oi","call_oi","atm_iv"} | None

Universe defaults to the bundled liquid large-cap set (an S&P-500-style, highly
liquid list); extend it to the full 500 by enlarging the bundled universe.
"""
from __future__ import annotations

from typing import Optional

from ..config import CONFIG
from ..screener.universe import sp500_tickers


class IntradayProvider:
    name = "base"

    def get_universe(self) -> list:
        # Full S&P 500 (live, with offline fallback to the bundled liquid set).
        return sp500_tickers(getattr(self, "cfg", None) or CONFIG)

    def get_bars(self, ticker: str) -> Optional[dict]:
        raise NotImplementedError

    def get_option_summary(self, ticker: str) -> Optional[dict]:
        return None

    def get_option_chain(self, ticker: str, dte_range=(45, 75)) -> Optional[list]:
        """Raw chain rows for the tradable band, for live contract selection.

        Separate from `get_option_summary` on purpose. The summary is cheap and runs for every
        name in the universe on every scan; this is expensive (several expiries of full quotes)
        and runs ONLY for names that already cleared the alert bar - a handful per scan.
        """
        return None


class TradierProvider(IntradayProvider):
    name = "Tradier"

    def __init__(self, cfg=CONFIG):
        self.cfg = cfg
        self.base = ("https://api.tradier.com/v1" if cfg.tradier_env == "live"
                     else "https://sandbox.tradier.com/v1")

    def _get(self, path, **params):
        import requests
        r = requests.get(f"{self.base}/{path}",
                         params=params,
                         headers={"Authorization": f"Bearer {self.cfg.tradier_token}",
                                  "Accept": "application/json"}, timeout=20)
        r.raise_for_status()
        return r.json()

    def get_bars(self, ticker: str) -> Optional[dict]:
        try:
            import datetime as dt
            start = (dt.date.today() - dt.timedelta(days=400)).isoformat()
            d = self._get("markets/history", symbol=ticker, interval="daily", start=start)
            days = ((d or {}).get("history") or {}).get("day")
            if not days:
                return None
            if isinstance(days, dict):
                days = [days]
            return {"close": [x["close"] for x in days], "high": [x["high"] for x in days],
                    "low": [x["low"] for x in days], "volume": [x["volume"] for x in days]}
        except Exception:
            return None

    def get_option_summary(self, ticker: str) -> Optional[dict]:
        try:
            exps = self._get("markets/options/expirations", symbol=ticker)
            dates = ((exps or {}).get("expirations") or {}).get("date")
            if not dates:
                return None
            dl = dates if isinstance(dates, list) else [dates]
            expiry = dl[0]
            # A ~60-DTE expiry too: term_slope needs BOTH legs and the front alone cannot give it.
            expiry_60 = None
            try:
                import datetime as _dt
                today = _dt.date.today()
                cand = []
                for d in dl:
                    try:
                        cand.append((abs((_dt.date.fromisoformat(str(d)[:10]) - today).days - 60), d))
                    except ValueError:
                        continue
                if cand:
                    expiry_60 = min(cand)[1]
            except Exception:                                        # noqa: BLE001
                expiry_60 = None
            ch = self._get("markets/options/chains", symbol=ticker, expiration=expiry, greeks="true")
            opts = ((ch or {}).get("options") or {}).get("option")
            if not opts:
                return None
            if isinstance(opts, dict):
                opts = [opts]
            und = None
            for o in opts:
                g = o.get("greeks") or {}
                if g.get("smv_vol") or g.get("mid_iv"):
                    und = o.get("underlying")
                    break
            cv = sum((o.get("volume") or 0) for o in opts if o.get("option_type") == "call")
            pv = sum((o.get("volume") or 0) for o in opts if o.get("option_type") == "put")
            coi = sum((o.get("open_interest") or 0) for o in opts if o.get("option_type") == "call")
            poi = sum((o.get("open_interest") or 0) for o in opts if o.get("option_type") == "put")
            # ATM IV: nearest-strike option's greeks
            ivs = [( (o.get("greeks") or {}).get("mid_iv") or (o.get("greeks") or {}).get("smv_vol"),
                     abs((o.get("strike") or 0) - (o.get("underlying_price") or 0)) )
                   for o in opts if (o.get("greeks") or {}).get("mid_iv") or (o.get("greeks") or {}).get("smv_vol")]
            atm_iv = None
            if ivs:
                atm_iv = sorted(ivs, key=lambda x: x[1])[0][0]
            # ATM IV of a ~60-DTE expiry, the second leg term_slope needs. Best-effort: a
            # failure here leaves atm_iv_60d absent, which the filter reads as UNKNOWN and does
            # not act on - a quote hiccup must never look like backwardation.
            atm_iv_60d = None
            if expiry_60 and expiry_60 != expiry:
                try:
                    ch2 = self._get("markets/options/chains", symbol=ticker,
                                    expiration=expiry_60, greeks="true")
                    o2 = ((ch2 or {}).get("options") or {}).get("option")
                    if isinstance(o2, dict):
                        o2 = [o2]
                    ivs2 = [((o.get("greeks") or {}).get("mid_iv")
                             or (o.get("greeks") or {}).get("smv_vol"),
                             abs((o.get("strike") or 0) - (o.get("underlying_price") or 0)))
                            for o in (o2 or [])
                            if (o.get("greeks") or {}).get("mid_iv")
                            or (o.get("greeks") or {}).get("smv_vol")]
                    if ivs2:
                        atm_iv_60d = sorted(ivs2, key=lambda x: x[1])[0][0]
                except Exception:                                    # noqa: BLE001
                    atm_iv_60d = None
            return {"call_volume": cv, "put_volume": pv, "call_oi": coi, "put_oi": poi,
                    "atm_iv": atm_iv, "atm_iv_60d": atm_iv_60d}
        except Exception:
            return None

    def get_option_chain(self, ticker: str, dte_range=(45, 75)) -> Optional[list]:
        """Full quotes for every expiry in the band, PLUS the front expiry.

        The front expiry is fetched even though nothing in 45-75 DTE trades it, because
        `term_slope` is (~60-DTE ATM IV - FRONT ATM IV) and the near leg cannot be inferred from
        the band. Fetching the band alone would leave the term read permanently unknown, which
        the filter reads as "do not act" - a silent loss of the one signal that arrests the fade.
        """
        try:
            import datetime as _dt
            exps = self._get("markets/options/expirations", symbol=ticker)
            dates = ((exps or {}).get("expirations") or {}).get("date")
            if not dates:
                return None
            dl = dates if isinstance(dates, list) else [dates]
            today = _dt.date.today()
            dated = []
            for d in dl:
                try:
                    dated.append((_dt.date.fromisoformat(str(d)[:10]), str(d)[:10]))
                except ValueError:
                    continue
            if not dated:
                return None
            dated.sort()
            lo, hi = int(dte_range[0]), int(dte_range[1])
            want = [s for dd, s in dated if lo <= (dd - today).days <= hi]
            front = next((s for dd, s in dated if (dd - today).days > 0), None)
            if front and front not in want:
                want.append(front)
            if not want:
                return None
            rows = []
            for e in want:
                ch = self._get("markets/options/chains", symbol=ticker, expiration=e,
                               greeks="true")
                opts = ((ch or {}).get("options") or {}).get("option")
                if not opts:
                    continue
                if isinstance(opts, dict):
                    opts = [opts]
                rows.extend(opts)
            return rows or None
        except Exception:
            return None


class FreeProvider(IntradayProvider):
    name = "free (yfinance, delayed)"

    def get_bars(self, ticker: str) -> Optional[dict]:
        try:
            import yfinance as yf
            h = yf.Ticker(ticker).history(period="1y")
            if h is None or h.empty:
                return None
            return {"close": [float(x) for x in h["Close"]], "high": [float(x) for x in h["High"]],
                    "low": [float(x) for x in h["Low"]], "volume": [float(x) for x in h["Volume"]]}
        except Exception:
            return None

    def get_option_summary(self, ticker: str) -> Optional[dict]:
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            exps = t.options
            if not exps:
                return None
            chain = t.option_chain(exps[0])
            calls, puts = chain.calls, chain.puts
            cv = float(calls["volume"].fillna(0).sum())
            pv = float(puts["volume"].fillna(0).sum())
            coi = float(calls["openInterest"].fillna(0).sum())
            poi = float(puts["openInterest"].fillna(0).sum())
            iv = None
            try:
                iv = float(calls["impliedVolatility"].median())
            except Exception:
                pass
            return {"call_volume": cv, "put_volume": pv, "call_oi": coi, "put_oi": poi, "atm_iv": iv}
        except Exception:
            return None

    def get_option_chain(self, ticker: str, dte_range=(45, 75)) -> Optional[list]:
        """Same shape from yfinance. DELAYED quotes - fine for a paper book, not for a fill."""
        try:
            import datetime as _dt

            import yfinance as yf
            t = yf.Ticker(ticker)
            exps = t.options or []
            today = _dt.date.today()
            dated = []
            for d in exps:
                try:
                    dated.append((_dt.date.fromisoformat(str(d)[:10]), str(d)[:10]))
                except ValueError:
                    continue
            if not dated:
                return None
            dated.sort()
            lo, hi = int(dte_range[0]), int(dte_range[1])
            want = [s for dd, s in dated if lo <= (dd - today).days <= hi]
            front = next((s for dd, s in dated if (dd - today).days > 0), None)
            if front and front not in want:
                want.append(front)
            rows = []
            for e in want:
                ch = t.option_chain(e)
                for df, kind in ((ch.calls, "call"), (ch.puts, "put")):
                    if df is None or df.empty:
                        continue
                    for _, r in df.iterrows():
                        rows.append({
                            "option_type": kind, "expiration_date": e,
                            "strike": float(r.get("strike")),
                            "bid": r.get("bid"), "ask": r.get("ask"),
                            "volume": r.get("volume"), "open_interest": r.get("openInterest"),
                            "greeks": {"mid_iv": r.get("impliedVolatility")},
                        })
            return rows or None
        except Exception:
            return None


def get_provider(cfg=CONFIG) -> IntradayProvider:
    if cfg.tradier_token:
        return TradierProvider(cfg)
    return FreeProvider()
