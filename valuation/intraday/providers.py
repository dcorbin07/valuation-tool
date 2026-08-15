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


# Plausibility band for a single-name equity ATM implied vol. Outside it the quote is not a
# market: Tradier's `mid_iv` is solved from the raw bid/ask, so on an illiquid wing (a $0.00 bid
# against a $0.51 ask on a 50-strike when spot is 308) it returns values like 2.30 - i.e. 230%
# vol - while the smoothed `smv_vol` for the same contract says 0.42.
_IV_MIN, _IV_MAX = 0.02, 1.50


def atm_iv_from_chain(opts, underlying=None):
    """ATM implied vol for one expiry. None when the chain cannot support an honest answer.

    FIXED 2026-08-02, and the bug this replaces was live and severe. The old rule ranked
    contracts by `abs(strike - o["underlying_price"])`, but **Tradier option rows do not carry
    `underlying_price`** - the field simply does not exist in the payload. `.get()` returned
    None, `(None or 0)` collapsed it to 0, and the "nearest strike to zero" is the LOWEST strike
    on the board. So the ATM IV of AAPL at $308.91 was read off the $50 strike, giving
    atm_iv 1.4917 and atm_iv_60d 2.2997 against a true ATM of ~0.256.

    That fed `term_slope` directly, producing live slopes of +0.81 (AAPL), -0.93 (MSFT), -1.02
    (KO) against a fitted threshold of 0.0105 - noise two orders of magnitude larger than the
    signal, so the term gate was suppressing alerts essentially at random. It also corrupted the
    options component of every live intraday score.

    Two changes fix it:

      * ATM IS FOUND BY DELTA, NOT BY SPOT. The contract whose |delta| is nearest 0.50 *is* the
        at-the-money one, by definition. This needs no underlying price, so it cannot silently
        degrade when a field is missing - which is exactly how the original failed. When a spot
        price IS supplied it is used instead, as the more direct measure.
      * IMPLAUSIBLE IVs ARE REJECTED, not preferred. The old code took `mid_iv or smv_vol`,
        preferring the raw solve over the smoothed surface. That is the wrong way round on a
        wide quote. Here `mid_iv` is used only when it lands inside `_IV_MIN.._IV_MAX`, and
        `smv_vol` is the fallback - and if neither is plausible the contract is skipped rather
        than contributing a fabricated number.
    """
    if not opts:
        return None
    best, best_key = None, None
    for o in opts or []:
        if not isinstance(o, dict):
            continue
        g = o.get("greeks") or {}
        iv = None
        for cand in (g.get("mid_iv"), g.get("smv_vol")):
            try:
                v = float(cand)
            except (TypeError, ValueError):
                continue
            if v == v and _IV_MIN <= v <= _IV_MAX:
                iv = v
                break
        if iv is None:
            continue
        try:
            strike = float(o.get("strike"))
        except (TypeError, ValueError):
            continue
        if underlying:
            key = abs(strike - float(underlying))
        else:
            try:
                key = abs(abs(float(g.get("delta"))) - 0.50)
            except (TypeError, ValueError):
                continue
        if best_key is None or key < best_key:
            best, best_key = iv, key
    return best


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


TRADIER_LIVE_BASE = "https://api.tradier.com/v1"
TRADIER_SANDBOX_BASE = "https://sandbox.tradier.com/v1"


class TradierProvider(IntradayProvider):
    name = "Tradier"

    def __init__(self, cfg=CONFIG, base=None, token=None):
        """`base`/`token` are ADDITIVE overrides, both default to the existing behaviour.

        They exist so the forward paper track can point one instance at the sandbox on the
        dedicated paper credentials WITHOUT touching `TRADIER_ENV` / `TRADIER_TOKEN`, which are
        the live app's production feed. Two instances therefore run side by side: the scan keeps
        reading production quotes while the paper book reads (and trades) the sandbox. Passing
        neither reproduces the previous constructor exactly.
        """
        self.cfg = cfg
        self.base = base or (TRADIER_LIVE_BASE if cfg.tradier_env == "live"
                             else TRADIER_SANDBOX_BASE)
        self._token = token or cfg.tradier_token

    def _get(self, path, **params):
        import requests
        r = requests.get(f"{self.base}/{path}",
                         params=params,
                         headers={"Authorization": f"Bearer {self._token}",
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
            cv = sum((o.get("volume") or 0) for o in opts if o.get("option_type") == "call")
            pv = sum((o.get("volume") or 0) for o in opts if o.get("option_type") == "put")
            coi = sum((o.get("open_interest") or 0) for o in opts if o.get("option_type") == "call")
            poi = sum((o.get("open_interest") or 0) for o in opts if o.get("option_type") == "put")
            atm_iv = atm_iv_from_chain(opts)
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
                    atm_iv_60d = atm_iv_from_chain(o2)
                except Exception:                                    # noqa: BLE001
                    atm_iv_60d = None
            return {"call_volume": cv, "put_volume": pv, "call_oi": coi, "put_oi": poi,
                    "atm_iv": atm_iv, "atm_iv_60d": atm_iv_60d,
                    # AUDIT MA44 — WHICH expiry these figures describe. `dl[0]` applies no date
                    # filter, so on an expiry day this can be TODAY, while the reconstruction in
                    # `edge.options_backtest.chain_summary` and the term read in
                    # `edge.options_live.term_read` both take the first STRICTLY LATER expiry.
                    # Reported rather than changed: altering which expiry the live scan reads
                    # would change which alerts fire. Nothing consumes this yet; it exists so the
                    # divergence is observable in a live payload instead of inferred from code.
                    "front_expiry": str(expiry)[:10]}
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
            # AUDIT MA44: `exps[0]` applies no date filter either — the same rule as the Tradier
            # path and the opposite of both strictly-after sites. Reported, not changed.
            return {"call_volume": cv, "put_volume": pv, "call_oi": coi, "put_oi": poi,
                    "atm_iv": iv, "front_expiry": str(exps[0])[:10]}
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
