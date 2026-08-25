"""EVOWN pass 2 - build the event-ownership book on the PINNED chains freeze.

`PREREG_evown_event_ownership.md`. Entry: K = 5 trading days before each covered announcement,
contract chosen by the SHIPPED `pick_contract` and held by the SHIPPED `simulate_trade`, both
IMPORTED - a second copy of either would be the B7 defect class and would stop this measuring the
engine the rest of the record is measured on.

NO ARM IS SCORED HERE. This writes the raw per-trade rows (RUN_RULES rule 9: store the draws, so
the arms and any later interval do not each cost a fresh multi-hour pass - MB1's lesson, learned
by nearly paying it twice).

SCOPE, in every output: 157 scoreable names, 2016-2025, the covered ~75% of in-window
announcements. `pre_panel_history` filtered. Strike selection and settlement on as-traded
`raw_close` (`U1-SPLIT`). The uncovered remainder is UNMEASURED and never read as zero.

    python -m scripts.evown_build
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

from valuation.edge import options_backtest as OB
from valuation.edge.chain_store import resolve_chains
from scripts.mb_evown_census import DATA, K_GRID, _alert_names, _bars_dir, _earnings_map

K = 5                      # register: fixed on AVAILABILITY before any return was computed
YEARS = range(2016, 2026)
OUT = os.path.join(DATA, "free_analysis", "EVOWN_BOOK.pkl")
META = os.path.join(DATA, "free_analysis", "EVOWN_BOOK.json")

T0 = time.time()


def _log(m):
    print("[EVOWN-B %6.1fs] %s" % (time.time() - T0, m), flush=True)


class FreezeChains:
    """One ticker's whole 2016-2025 chain history, indexed for both the pick and the hold."""

    def __init__(self, opt_root, tk):
        frames = []
        for y in YEARS:
            p = os.path.join(opt_root, tk, "%s-%d.pkl" % (tk, y))
            if not os.path.isfile(p):
                continue
            try:
                f = pd.read_pickle(p)
            except Exception:                                          # noqa: BLE001
                continue
            if isinstance(f, pd.DataFrame) and len(f):
                frames.append(f)
        if not frames:
            self.by_date, self._all = None, None
            return
        a = pd.concat(frames, ignore_index=True)
        a["date"] = a["date"].astype(str).str[:10]
        a["expiration"] = a["expiration"].astype(str).str[:10]
        self._all = a
        self.by_date = {d: g for d, g in a.groupby("date", observed=True)}
        self.by_contract = {}

    def chain_on(self, day):
        return self.by_date.get(day) if self.by_date else None

    def index_contracts(self, wanted):
        """Key on (strike, expiration, RIGHT).

        THE RIGHT IS PART OF THE KEY AND LEAVING IT OUT IS NOT COSMETIC. A strike/expiry pair
        names TWO instruments, and this freeze carries both: at AAPL 99.87 on 2016-07-19 the
        105 call is bid 1.18 while the 105 PUT is bid 6.70. A history keyed without the right
        hands `simulate_trade` a frame with both, it reads whichever row comes first per date,
        and a deep-ITM put's quote read as a call's shows an instant several-hundred-percent
        gain that exits at "target" on day one. Caught by disbelieving six consecutive
        target hits at +105% to +457% on the smoke test, not by anything raising.
        """
        self.by_contract = {}
        if not wanted or self._all is None:
            return
        a = self._all
        ks = {float(k) for k, _, _ in wanted}
        es = {str(e) for _, e, _ in wanted}
        rs = {str(r).upper()[:1] for _, _, r in wanted}
        sub = a[a["strike"].astype(float).isin(ks) & a["expiration"].isin(es)
                & a["right"].astype(str).str.upper().str[:1].isin(rs)]
        rr = sub["right"].astype(str).str.upper().str[:1]
        for (k, e, r), g in sub.groupby([sub["strike"].astype(float), "expiration", rr],
                                        observed=True):
            g = g.sort_values("date").reset_index(drop=True)
            # `simulate_trade` walks this frame and compares `day <= entry_date` against a
            # datetime.date, so the provider must hand back DATE objects. The by_date index
            # deliberately stays on strings - it is only ever keyed, never compared.
            g["date"] = pd.to_datetime(g["date"]).dt.date
            self.by_contract[(float(k), str(e), str(r))] = g

    # ---- the interface `simulate_trade` calls ------------------------------------------------
    def contract_history(self, ticker, expiry, strike, right, start, end):
        e = expiry if isinstance(expiry, str) else pd.Timestamp(expiry).date().isoformat()
        sub = (self.by_contract or {}).get(
            (float(strike), str(e)[:10], str(right).upper()[:1]))
        if sub is None:
            return None
        s0 = start if isinstance(start, dt.date) else dt.date.fromisoformat(str(start)[:10])
        e0 = end if isinstance(end, dt.date) else dt.date.fromisoformat(str(end)[:10])
        m = sub[(sub["date"] >= s0) & (sub["date"] <= e0)]
        return m if len(m) else None


def main():
    chains, prov = resolve_chains(DATA)
    assert prov.get("pinned"), "REFUSING: the chain store is not the pinned freeze"
    _log("chain store %s pinned=%s" % (prov.get("source"), prov.get("pinned")))

    bars_dir = _bars_dir()
    splits = OB.load_splits(DATA)
    names = sorted(set(_alert_names()))
    em = _earnings_map(names)
    names = [t for t in names if em.get(t) and os.path.isdir(os.path.join(chains, t))
             and os.path.isfile(os.path.join(bars_dir, "%s.pkl" % t.upper()))]
    _log("scoreable names %d" % len(names))

    rows, skipped = [], {"no_session": 0, "no_chain": 0, "no_pick": 0, "sim_none": 0,
                         "sim_not_ok": 0}
    for i, tk in enumerate(names, 1):
        try:
            bars = pickle.load(open(os.path.join(bars_dir, "%s.pkl" % tk.upper()), "rb"))
        except Exception:                                              # noqa: BLE001
            continue
        if not isinstance(bars, dict) or "raw_close" not in bars:
            continue
        px = {}
        for d0, rc in zip(bars["date"], bars["raw_close"]):
            if rc is None:
                continue
            v = float(rc)
            if np.isfinite(v) and v > 0:
                px[str(d0)[:10]] = v
        sess = sorted(px)
        if not sess:
            continue
        pos = {d: j for j, d in enumerate(sess)}

        fc = FreezeChains(chains, tk)
        if fc.by_date is None:
            continue

        picks = []
        for ann in em[tk]:
            if not ("2016-01-01" <= ann <= "2025-12-31"):
                continue
            j = pos.get(ann)
            if j is None:
                nxt = [d for d in sess if d >= ann]
                if not nxt:
                    skipped["no_session"] += 1
                    continue
                j = pos[nxt[0]]
            if j - K < 0:
                skipped["no_session"] += 1
                continue
            entry = sess[j - K]
            day = fc.chain_on(entry)
            if day is None or not len(day):
                skipped["no_chain"] += 1
                continue
            best = OB.pick_contract(day, float(px[entry]), entry)
            if best is None:
                skipped["no_pick"] += 1
                continue
            picks.append((entry, ann, best))

        if not picks:
            continue
        fc.index_contracts([(float(b["strike"]), str(b["expiration"])[:10],
                             str(b["right"])) for _, _, b in picks])

        for entry, ann, best in picks:
            ed = dt.date.fromisoformat(entry)
            t = OB.simulate_trade(fc, tk, best, ed, bars, splits=splits)
            if t is None:
                skipped["sim_none"] += 1
                continue
            if not t.get("ok"):
                skipped["sim_not_ok"] += 1
                continue
            exp = str(best["expiration"])[:10]
            # The MARK PATH, recorded here so the survivability arm does not cost a second
            # multi-hour pass (RUN_RULES rule 9). Same shape as `O11_MARKS.pkl`: (date, mid)
            # over the holding period, which is what `long_leg_as_book_trade` consumes.
            exit_date = t.get("exit_date") or exp
            marks = []
            hist = fc.contract_history(tk, exp, float(best["strike"]), str(best["right"]),
                                       ed, dt.date.fromisoformat(str(exit_date)[:10]))
            if hist is not None:
                for _, hr in hist.iterrows():
                    b_, a_ = hr.get("bid"), hr.get("ask")
                    if b_ is None or a_ is None:
                        continue
                    b_, a_ = float(b_), float(a_)
                    if np.isfinite(b_) and np.isfinite(a_) and a_ >= b_ >= 0:
                        marks.append((str(hr["date"])[:10], 0.5 * (b_ + a_)))
            rows.append({
                "ticker": tk, "entry": entry, "announcement": ann, "expiry": exp,
                "strike": float(best["strike"]), "right": str(best["right"]),
                "dte": (dt.date.fromisoformat(exp) - ed).days,
                "ret": float(t["return_pct"]) if t.get("return_pct") is not None else None,
                # `simulate_trade` returns `entry_fill` and `net_pnl`; the BOOK vocabulary
                # that `long_leg_as_book_trade` consumes calls them `entry_premium` and
                # `pnl_dollars`. Mapped here rather than renamed downstream, and verified:
                # on the shipped book pnl_dollars == pnl_pct * entry_premium * 100 to
                # 1.8e-12 over 500 rows, which is the identity these two must satisfy.
                "entry_premium": t.get("entry_fill"),
                "pnl_dollars": t.get("net_pnl"),
                "alert_ts": entry,          # book vocabulary for the entry date
                "exit_date": str(exit_date)[:10],
                "held_days": t.get("held_days"),
                "exit_reason": t.get("exit_reason"),
                "marks": marks,
                "year": entry[:4],
            })
        if i % 10 == 0:
            _log("  %d/%d names, trades %d, skipped %s" % (i, len(names), len(rows), skipped))

    df = pd.DataFrame(rows)
    df = df[df["ret"].notna()] if len(df) else df
    pickle.dump({"rows": rows, "skipped": skipped}, open(OUT, "wb"))

    meta = {
        "item": "EVOWN", "pass": "build",
        "register": "PREREG_evown_event_ownership.md",
        "status": "RAW BOOK ONLY - no arm scored here",
        "chain_store_source": prov.get("source"), "chain_store_pinned": prov.get("pinned"),
        "freeze_generated_utc": prov.get("generated_utc"),
        "K_trading_days": K, "k_grid_censused": list(K_GRID),
        "scope": "157 scoreable alert-book names, 2016-2025, covered ~75% of in-window "
                 "announcements; pre_panel_history filtered; as-traded raw_close for strike and "
                 "settlement (U1-SPLIT); the uncovered remainder is UNMEASURED and never read "
                 "as zero",
        "selection": "valuation.edge.options_backtest.pick_contract, IMPORTED",
        "exit": "valuation.edge.options_backtest.simulate_trade, IMPORTED and unmodified",
        "n_trades": int(len(df)), "n_names": int(df["ticker"].nunique()) if len(df) else 0,
        "skipped": skipped,
        "dte_p05": float(np.percentile(df["dte"], 5)) if len(df) else None,
        "dte_median": float(np.median(df["dte"])) if len(df) else None,
        "dte_p95": float(np.percentile(df["dte"], 95)) if len(df) else None,
        "first_entry": df["entry"].min() if len(df) else None,
        "last_entry": df["entry"].max() if len(df) else None,
    }
    with io.open(META, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1, default=str)
    _log("trades %d over %d names; skipped %s" % (meta["n_trades"], meta["n_names"], skipped))
    _log("wrote %s and %s" % (OUT, META))
    return 0


if __name__ == "__main__":
    sys.exit(main())
