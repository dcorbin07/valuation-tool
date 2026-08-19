"""MB1 — the alternatives MENU, and the selection-vs-timing decomposition.

Register: `PREREG_mb1_alternatives_menu.md`, committed ALONE at `33ad7ee`, markdown only and a
strict ancestor of every measurement commit. Trials booked BEFORE the run at `476650e`: options
N 300 -> 302.

THE QUESTION. Every options study this project has run scored the ONE contract the book held, so
`R2`'s -5.0640pp gap is a compound: the alert chose a DAY and a rule chose a CONTRACT. Scoring the
WHOLE in-band menu on alert days against the same construction on random days separates them.

TWO PASSES, AND THE ORDER IS THE POINT.
    python -m scripts.mb1_alternatives_menu --controls    # writes MB1_CONTROLS.json
    python -m scripts.mb1_alternatives_menu --arms        # REFUSES without a passing artifact

THE MENU IS THE ENGINE'S OWN. `build_menu` is `pick_contract`'s prefilter verbatim, minus the
final argmin, INCLUDING its moneyness fallback. C1 gates on the shipped pick being a member of
the menu and on the menu's own argmin BEING that pick.

A CONTROL THE REGISTER DID NOT ANTICIPATE, added because of a data fact found while implementing
and declared rather than absorbed: THE CONTROL BOOKS STORE NO `underlying_entry` (it is None on
every row). The menu's moneyness band needs it. Using the alert book's stored value for one arm
and a derived value for the other would make the two menus incomparable at exactly the filter that
defines them, so BOTH arms derive the underlying from `bars["raw_close"]` on the entry date -
as-traded, per U1-SPLIT/O6 - and C7 measures that derivation against the alert book's stored
value. Symmetry beats fidelity to one arm's convenience.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd                                        # noqa: E402

from valuation.edge import blackscholes as BS              # noqa: E402
from valuation.edge import chain_store as CS               # noqa: E402
from valuation.edge import options_backtest as OB          # noqa: E402
from valuation.edge import options_fill as F               # noqa: E402

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_root() -> str:
    for cand in (os.path.join(_HERE, "data"), os.path.join(_HERE, "..", "..", "..", "data")):
        if os.path.isdir(os.path.join(cand, "options_universe")):
            return os.path.abspath(cand)
    return os.path.abspath(os.path.join(_HERE, "data"))


DATA = _data_root()
UNIV = os.path.join(DATA, "options_universe")
CONTROLS_OUT = os.path.join(DATA, "free_analysis", "MB1_CONTROLS.json")
ARMS_OUT = os.path.join(DATA, "free_analysis", "MB1_MENU.json")
LEGS_OUT = os.path.join(DATA, "MB1_LEGS.pkl")   # RUN_RULES rule 9: store the draws

KILL_PP = 1.0                 # under this, in EITHER half, contract selection is closed for good
C1_FLOOR = 0.99               # menu must contain the shipped pick
C2_COVERAGE_TOL_PP = 2.0      # arms' coverage shares must agree within this
DELTA_BUCKETS = ((0.00, 0.15), (0.15, 0.35), (0.35, 0.60), (0.60, 1.01))


def _log(m):
    print("[MB1] %s" % m, flush=True)


def _bars_dir() -> str:
    """EXISTENCE IS NOT POPULATION - the worktree's bars dir is empty, the primary's holds 502."""
    for cand in (os.path.join(_HERE, "data", "bulk", "prepared", "bars"),
                 os.path.join(_HERE, "..", "..", "..", "data", "bulk", "prepared", "bars")):
        p = os.path.abspath(cand)
        if os.path.isdir(p) and os.listdir(p):
            return p
    raise RuntimeError("no POPULATED bars cache found; refusing to run on an empty one")


_BARS = {}


def bars_for(tk, bars_dir):
    """Cache-only. NEVER fetches: a banked reproduction that reaches the network is S23's defect."""
    if tk not in _BARS:
        p = os.path.join(bars_dir, "%s.pkl" % tk.upper())
        got = None
        if os.path.exists(p):
            try:
                with open(p, "rb") as fh:
                    g = pickle.load(fh)
                got = g if isinstance(g, dict) and "raw_close" in g else None
            except (OSError, pickle.UnpicklingError):
                got = None
        _BARS[tk] = got
    return _BARS[tk]


def underlying_on(tk, day, bars_dir):
    """AS-TRADED close on `day`, per U1-SPLIT: raw_close for anything touching a STRIKE."""
    b = bars_for(tk, bars_dir)
    if not b:
        return None
    ds = b["date"]
    px = b.get("raw_close") or b["close"]
    iso = day.isoformat()
    lo, hi = 0, len(ds) - 1
    if not ds or iso < ds[0]:
        return None
    # last date <= iso
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if ds[mid] <= iso:
            lo = mid
        else:
            hi = mid - 1
    return float(px[lo]) if ds[lo] == iso else None


# ============================ THE MENU — the shipped prefilter, verbatim ===================
def build_menu(chain, underlying: float, asof, right: str = "C", dte_range=OB.DTE_RANGE):
    """`pick_contract`'s prefilter, VERBATIM, minus the final argmin.

    Every line here mirrors `options_backtest.pick_contract`, INCLUDING the moneyness fallback
    (`if len(near) == 0: near = d`). Removing the fallback would make this a different menu from
    the engine's, which is a void condition of the register.
    """
    if chain is None or len(chain) == 0:
        return None
    d = chain[chain["right"].astype(str).str.upper().str.startswith(right.upper())]
    if len(d) == 0:
        return None
    exp = pd.to_datetime(d["expiration"]).dt.date
    dte = pd.Series([(e - asof).days for e in exp], index=d.index)
    d = d[(dte >= dte_range[0]) & (dte <= dte_range[1])]
    if len(d) == 0:
        return None
    mny = d["strike"].astype(float) / float(underlying)
    lo, hi = (0.90, 1.20) if right.upper().startswith("C") else (0.80, 1.10)
    near = d[(mny >= lo) & (mny <= hi)]
    if len(near) == 0:
        near = d                                  # the shipped fallback, kept verbatim
    enr = BS.enrich_chain(near, underlying, asof)
    enr = enr.dropna(subset=["delta"])
    if len(enr) == 0:
        return None
    ok = []
    for _, r in enr.iterrows():
        q = F.Quote(bid=r.get("bid"), ask=r.get("ask"), oi=r.get("open_interest"),
                    volume=r.get("volume"))
        if F.quote_reject_reason(q) is None:
            ok.append(r)
    return ok or None


def menu_argmin(menu, target=OB.TARGET_DELTA):
    """What `pick_contract` returns, given the menu. C1 asserts this IS the shipped pick."""
    return min(menu, key=lambda r: abs(abs(float(r["delta"])) - target))


# ============================ per-ticker harvest access ===================================
class TickerChains:
    """All the calls a ticker needs, loaded once. Two passes so memory stays bounded."""

    def __init__(self, root):
        self.root = root
        self.by_date = None
        self.by_contract = None

    def unit(self, sym, y):
        return os.path.join(self.root, sym, "%s-%d.pkl" % (sym, y))

    def has(self, sym, y):
        return os.path.isfile(self.unit(sym, y))

    def load(self, sym, years):
        frames = []
        for y in sorted(set(years)):
            p = self.unit(sym, y)
            if not os.path.isfile(p):
                continue
            df = pd.read_pickle(p)["rows"]
            df = df[df["right"].astype(str).str[0].str.upper() == "C"]
            if len(df):
                frames.append(df)
        if not frames:
            self.by_date = {}
            return
        allc = pd.concat(frames, ignore_index=True)
        self.by_date = {d: g for d, g in allc.groupby("date", observed=True)}
        self._all = allc

    def index_contracts(self, wanted):
        """Second pass: forward paths for the menu contracts only."""
        self.by_contract = {}
        if not wanted or self.by_date is None or not len(getattr(self, "_all", [])):
            return
        a = self._all
        ks = {float(k) for k, _ in wanted}
        es = {e for _, e in wanted}
        sub = a[a["strike"].astype(float).isin(ks) & a["expiration"].isin(es)]
        for (k, e), g in sub.groupby([sub["strike"].astype(float), "expiration"], observed=True):
            self.by_contract[(float(k), e)] = g.sort_values("date").reset_index(drop=True)

    def chain_on(self, day):
        return self.by_date.get(day) if self.by_date else None

    # ---- the interface `simulate_trade` calls -------------------------------------------
    def contract_history(self, ticker, expiry, strike, right, start, end):
        e = expiry if isinstance(expiry, dt.date) else pd.Timestamp(expiry).date()
        sub = (self.by_contract or {}).get((float(strike), e))
        if sub is None:
            return None
        m = sub[(sub["date"] >= start) & (sub["date"] <= end)]
        return m if len(m) else None


def _books():
    def load(p):
        with open(p, "rb") as fh:
            d = pickle.load(fh)
        return d["rows"] if isinstance(d, dict) else d
    alert = load(os.path.join(UNIV, "state_r2_splitclean.pkl"))
    ctrl = []
    for s in range(5):
        for r in load(os.path.join(UNIV, "control_r2_splitclean_seed%d.pkl" % s)):
            r = dict(r)
            r["_seed"] = s
            ctrl.append(r)
    return alert, ctrl


def _years(r):
    a = str(r.get("alert_ts"))[:10]
    e = str(r.get("expiry"))[:10]
    return list(range(int(a[:4]), int(e[:4]) + 1))


def _covered(rows, tc):
    return [r for r in rows if all(tc.has(r["ticker"], y) for y in _years(r))]


# ============================ pass 1 — CONTROLS ===========================================
def run_controls() -> int:
    chains, prov = CS.resolve_harvest()
    _log("harvest %s  (%s units, generated %s)"
         % (prov["manifest_sha256"], prov["payload_units"], prov["generated_utc"]))
    bars_dir = _bars_dir()
    tc = TickerChains(chains)
    alert, ctrl = _books()
    _log("alert %d, control %d" % (len(alert), len(ctrl)))

    ca, cc = _covered(alert, tc), _covered(ctrl, tc)
    sa, sc = len(ca) / max(1, len(alert)), len(cc) / max(1, len(ctrl))
    c2_pass = abs(sa - sc) * 100.0 <= C2_COVERAGE_TOL_PP
    _log("C2 coverage: alert %d/%d = %.4f, control %d/%d = %.4f, gap %.2fpp -> %s"
         % (len(ca), len(alert), sa, len(cc), len(ctrl), sc, abs(sa - sc) * 100.0,
            "PASS" if c2_pass else "FAIL"))

    # ---- C1 + C7 on covered ALERT entries, grouped by ticker ---------------------------
    by_t = {}
    for r in ca:
        by_t.setdefault(r["ticker"], []).append(r)

    n = hit = argmin_hit = 0
    und_n = und_exact = 0
    und_err = []
    menu_sizes = []
    for i, (sym, rows) in enumerate(sorted(by_t.items())):
        if i % 25 == 0:
            _log("  C1 %d/%d names (%d of %d so far)" % (i, len(by_t), hit, n))
        years = set()
        for r in rows:
            years.update(_years(r))
        tc.load(sym, years)
        for r in rows:
            a = dt.date.fromisoformat(str(r["alert_ts"])[:10])
            u_der = underlying_on(sym, a, bars_dir)
            u_book = r.get("underlying_entry")
            if u_der is not None and u_book:
                und_n += 1
                rel = abs(u_der - float(u_book)) / float(u_book)
                und_err.append(rel)
                if rel < 1e-9:
                    und_exact += 1
            if u_der is None:
                continue
            ch = tc.chain_on(a)
            if ch is None:
                continue
            m = build_menu(ch, u_der, a)
            if not m:
                continue
            menu_sizes.append(len(m))
            n += 1
            pick = OB.pick_contract(ch, u_der, a, right="C")
            if pick is None:
                continue
            pk = (float(pick["strike"]), str(pick["expiration"])[:10])
            keys = {(float(x["strike"]), str(x["expiration"])[:10]) for x in m}
            if pk in keys:
                hit += 1
            am = menu_argmin(m)
            if (float(am["strike"]), str(am["expiration"])[:10]) == pk:
                argmin_hit += 1

    rate = hit / max(1, n)
    arate = argmin_hit / max(1, n)
    c1_pass = bool(rate >= C1_FLOOR and arate >= C1_FLOOR)
    _log("C1 menu-contains-pick %d/%d = %.4f; menu-argmin-IS-pick %.4f -> %s"
         % (hit, n, rate, arate, "PASS" if c1_pass else "FAIL"))
    und_err.sort()
    if und_err:
        _log("C7 derived underlying vs the alert book's stored value: n %d, EXACT %d (%.4f), "
             "median rel err %.3e, p95 %.3e"
             % (und_n, und_exact, und_exact / max(1, und_n), und_err[len(und_err) // 2],
                und_err[int(0.95 * len(und_err))]))
    menu_sizes.sort()
    out = {
        "item": "MB1", "register": "PREREG_mb1_alternatives_menu.md", "pass": "controls",
        "harvest_provenance": prov,
        "c1_menu_contains_pick": {"n": n, "contains": hit, "rate": rate,
                                  "argmin_is_pick": argmin_hit, "argmin_rate": arate,
                                  "floor": C1_FLOOR, "pass": c1_pass},
        "c2_coverage_parity": {"alert_covered": len(ca), "alert_n": len(alert),
                               "alert_share": sa, "control_covered": len(cc),
                               "control_n": len(ctrl), "control_share": sc,
                               "gap_pp": abs(sa - sc) * 100.0,
                               "tol_pp": C2_COVERAGE_TOL_PP, "pass": c2_pass},
        "c7_derived_underlying": {
            "n": und_n, "exact": und_exact,
            "exact_share": (und_exact / und_n) if und_n else None,
            "median_rel_err": und_err[len(und_err) // 2] if und_err else None,
            "note": ("a control the register did not anticipate. The CONTROL books store no "
                     "underlying_entry, so both arms derive it from raw_close and this measures "
                     "that derivation against the ALERT book's stored value. Symmetry between the "
                     "arms beats fidelity to one arm's stored field."),
        },
        "menu_size_alert": {"n": len(menu_sizes),
                            "median": menu_sizes[len(menu_sizes) // 2] if menu_sizes else None,
                            "p90": menu_sizes[int(0.9 * len(menu_sizes))] if menu_sizes else None},
        "all_gating_pass": bool(c1_pass and c2_pass),
    }
    os.makedirs(os.path.dirname(CONTROLS_OUT), exist_ok=True)
    with open(CONTROLS_OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)
    _log("wrote %s" % CONTROLS_OUT)
    _log("ALL GATING CONTROLS PASS: %s" % out["all_gating_pass"])
    return 0 if out["all_gating_pass"] else 2


# ============================ pass 2 — THE ARMS ===========================================
def _pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    i = min(len(xs) - 1, max(0, int(q * len(xs))))
    return xs[i]


def _score_both(alert_rows, ctrl_rows, tc, bars_dir):
    """Score BOTH arms in ONE ticker loop.

    Unit loading dominates, and scoring the arms in separate passes loaded every ticker's harvest
    units TWICE. Nothing definitional changes here - same menu, same simulator, same entries, and
    the arms are still kept separate and labelled. Only the iteration order moves.
    """
    by_t = {}
    for r in alert_rows:
        by_t.setdefault(r["ticker"], ([], []))[0].append(r)
    for r in ctrl_rows:
        by_t.setdefault(r["ticker"], ([], []))[1].append(r)

    a_legs, c_legs = [], []
    names = sorted(by_t)
    for i, sym in enumerate(names):
        arows, crows = by_t[sym]
        if i % 10 == 0:
            _log("  %d/%d names (alert %s legs, control %s legs)"
                 % (i, len(names), "{:,}".format(len(a_legs)), "{:,}".format(len(c_legs))))
        years = set()
        for r in arows + crows:
            years.update(_years(r))
        tc.load(sym, years)

        built = []          # (row, entry_date, menu, which)
        wanted = set()
        for rows, which in ((arows, "a"), (crows, "c")):
            for r in rows:
                a = dt.date.fromisoformat(str(r["alert_ts"])[:10])
                u = underlying_on(sym, a, bars_dir)
                if u is None:
                    continue
                ch = tc.chain_on(a)
                if ch is None:
                    continue
                m = build_menu(ch, u, a)
                if not m:
                    continue
                built.append((r, a, m, which))
                for x in m:
                    wanted.add((float(x["strike"]), pd.Timestamp(x["expiration"]).date()))
        tc.index_contracts(wanted)
        bars = bars_for(sym, bars_dir) or {}
        for r, a, m, which in built:
            for x in m:
                t = OB.simulate_trade(tc, sym, x, a, bars)
                if not t or not t.get("ok"):
                    continue
                leg = {"ticker": sym, "entry": a.isoformat(),
                       "delta": abs(float(x["delta"])),
                       "ret": float(t["return_pct"]),
                       "seed": r.get("_seed")}
                (a_legs if which == "a" else c_legs).append(leg)
    _log("  DONE: alert %s legs, control %s legs"
         % ("{:,}".format(len(a_legs)), "{:,}".format(len(c_legs))))
    return a_legs, c_legs


def _summarise(legs):
    rets = [l["ret"] for l in legs]
    per_entry = {}
    for l in legs:
        per_entry.setdefault((l["ticker"], l["entry"], l["seed"]), []).append(l["ret"])
    ew = [sorted(v)[len(v) // 2] for v in per_entry.values()]
    return {
        "n_legs": len(rets), "n_entries": len(per_entry),
        "median": _pct(rets, 0.5), "p75": _pct(rets, 0.75), "p25": _pct(rets, 0.25),
        "mean": (sum(rets) / len(rets)) if rets else None,
        "entry_weighted_median": _pct(ew, 0.5),
    }


def _buckets(legs):
    out = {}
    for lo, hi in DELTA_BUCKETS:
        sel = [l["ret"] for l in legs if lo <= l["delta"] < hi]
        out["%.2f-%.2f" % (lo, hi)] = {"n": len(sel), "median": _pct(sel, 0.5),
                                       "p75": _pct(sel, 0.75)}
    return out


def run_arms() -> int:
    if not os.path.exists(CONTROLS_OUT):
        _log("REFUSING: no controls artifact at %s. Run --controls first." % CONTROLS_OUT)
        return 2
    with open(CONTROLS_OUT, encoding="utf-8") as fh:
        ctrl_art = json.load(fh)
    if not ctrl_art.get("all_gating_pass"):
        _log("REFUSING: the controls artifact does not pass.")
        return 2
    _log("controls PASS: C1 %.4f, C2 gap %.2fpp"
         % (ctrl_art["c1_menu_contains_pick"]["rate"],
            ctrl_art["c2_coverage_parity"]["gap_pp"]))

    chains, prov = CS.resolve_harvest()
    bars_dir = _bars_dir()
    tc = TickerChains(chains)
    alert, ctrl = _books()
    ca, cc = _covered(alert, tc), _covered(ctrl, tc)

    a_legs, c_legs = _score_both(ca, cc, tc, bars_dir)
    if not a_legs or not c_legs:
        raise RuntimeError(
            "ZERO legs in an arm. An instrument failure, not a finding - a coverage null produced "
            "from an input that never loaded is MA31's failure mode. Refusing to write it.")

    # RULE 9: the draws go to disk BEFORE anything is summarised, so a defect in the summarising
    # or the write still leaves a ~55-minute scoring pass recoverable. O21-D2 lost a whole run to a
    # crash that fired after every statistic had been computed.
    pd.to_pickle({"alert": a_legs, "control": c_legs}, LEGS_OUT)
    _log("wrote %s (alert %s legs, control %s legs)"
         % (LEGS_OUT, "{:,}".format(len(a_legs)), "{:,}".format(len(c_legs))))

    # The register: "Split at the median entry date of the covered ALERT set, applied to both
    # arms." THE COVERED SET IS ENTRIES, NOT LEGS. An earlier cut took the median over a_legs,
    # which is LEG-weighted - each entry contributes a variable number of legs (median 5), so an
    # entry sitting on a deep chain would drag the boundary toward its own date. It is also
    # computable BEFORE any leg is scored, so the boundary cannot be influenced by an outcome.
    _entry_dates = sorted(dt.date.fromisoformat(str(r["alert_ts"])[:10]).isoformat() for r in ca)
    cut = _entry_dates[len(_entry_dates) // 2]
    halves = {}
    for name, pred in (("early", lambda e: e < cut), ("late", lambda e: e >= cut)):
        al = [l for l in a_legs if pred(l["entry"])]
        cl = [l for l in c_legs if pred(l["entry"])]
        A, C = _summarise(al), _summarise(cl)
        gap = ((A["median"] - C["median"]) * 100.0) if (A["median"] is not None
                                                        and C["median"] is not None) else None
        halves[name] = {"alert": A, "control": C, "gap_pp_median": gap,
                        "gap_pp_p75": ((A["p75"] - C["p75"]) * 100.0)
                        if (A["p75"] is not None and C["p75"] is not None) else None,
                        "alert_buckets": _buckets(al), "control_buckets": _buckets(cl)}

    A, C = _summarise(a_legs), _summarise(c_legs)
    full_gap = (A["median"] - C["median"]) * 100.0
    gaps = [halves["early"]["gap_pp_median"], halves["late"]["gap_pp_median"]]
    kill = any(g is not None and abs(g) < KILL_PP for g in gaps)
    signs_agree = (gaps[0] is not None and gaps[1] is not None and gaps[0] * gaps[1] > 0)

    verdict = ("CLOSED - contract selection is IRRELEVANT" if kill
               else ("SELECTION CARRIES SOME OF THE LOSS" if signs_agree
                     else "UNRESOLVED on direction; halves disagree in sign"))

    _log("")
    _log("=== MB1 ===")
    _log("ALERT   legs %s over %s entries: median %+.4f  p75 %+.4f"
         % ("{:,}".format(A["n_legs"]), "{:,}".format(A["n_entries"]), A["median"], A["p75"]))
    _log("CONTROL legs %s over %s entries: median %+.4f  p75 %+.4f"
         % ("{:,}".format(C["n_legs"]), "{:,}".format(C["n_entries"]), C["median"], C["p75"]))
    _log("full-sample median gap %+.4f pp" % full_gap)
    for h in ("early", "late"):
        _log("  %-5s gap median %s pp   p75 %s pp"
             % (h,
                ("%+.4f" % halves[h]["gap_pp_median"]) if halves[h]["gap_pp_median"] is not None else "n/a",
                ("%+.4f" % halves[h]["gap_pp_p75"]) if halves[h]["gap_pp_p75"] is not None else "n/a"))
    _log("KILL CONDITION (<%.1fpp in EITHER half): %s" % (KILL_PP, "FIRES" if kill else "does not fire"))
    _log("VERDICT: %s" % verdict)

    out = {
        "item": "MB1", "register": "PREREG_mb1_alternatives_menu.md", "pass": "arms",
        "harvest_provenance": prov,
        "controls_read": {"c1_rate": ctrl_art["c1_menu_contains_pick"]["rate"],
                          "c2_gap_pp": ctrl_art["c2_coverage_parity"]["gap_pp"]},
        "alert": A, "control": C,
        "full_sample_gap_pp_median": full_gap,
        "full_sample_gap_pp_p75": (A["p75"] - C["p75"]) * 100.0,
        "halves": halves, "half_cut": cut,
        "kill_condition": {"bar_pp": KILL_PP, "gaps_pp": gaps, "fires": kill,
                           "rule": ("under the bar in EITHER half closes contract selection "
                                    "PERMANENTLY; it fires on the WEAKER half, never both")},
        "signs_agree": signs_agree,
        "verdict": verdict,
        "coverage_note": ("alert %.1f%% and control %.1f%% of their books; the uncovered "
                          "remainder is UNMEASURED and never read as zero"
                          % (100.0 * ctrl_art["c2_coverage_parity"]["alert_share"],
                             100.0 * ctrl_art["c2_coverage_parity"]["control_share"])),
        "legs_artifact": LEGS_OUT,
        "menu_premise": ("the audit's 636 alternatives per entry is the WHOLE CHAIN; the engine's "
                         "own in-band fillable menu has a median of 5. Any reading leaning on a "
                         "distribution over ~636 is void."),
    }
    with open(ARMS_OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)
    _log("wrote %s" % ARMS_OUT)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="MB1 - the alternatives menu")
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--arms", action="store_true")
    a = ap.parse_args(argv)
    if a.controls == a.arms:
        ap.error("choose exactly one of --controls or --arms; they may not run in one pass")
    return run_controls() if a.controls else run_arms()


if __name__ == "__main__":
    raise SystemExit(main())
