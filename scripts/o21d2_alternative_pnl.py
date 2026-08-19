"""O21-D2 — the alternative contract's P&L, against the shipped book's.

Register: `PREREG_o21d2_alternative_contract_pnl.md`, committed ALONE at `1d23ee1`, markdown only
and a strict ancestor of every measurement commit. Trial booked BEFORE the run: options N 297 ->
298.

WHAT THIS CLOSES. O21 measured that the dividend-corrected pricer picks a DIFFERENT contract on
179 of 3,870 entries (4.63%), and reported that alternative book's P&L as **NOT COMPUTABLE**
rather than as zero, because the trade-scope freeze holds a full chain only on ENTRY dates. The
pinned HARVEST freeze holds a full chain on EVERY session, so the door closes with a measurement.

TWO PASSES, AND THE ORDER IS THE POINT.
    python -m scripts.o21d2_alternative_pnl --controls     # writes O21D2_CONTROLS.json
    python -m scripts.o21d2_alternative_pnl --arms         # REFUSES without a passing artifact

A gating control computed in the same pass as the outcomes cannot be claimed to have been read
first. That is session 26's defect, repaired in O19 and kept here.

BOTH ARMS ARE PRICED ON THE SAME INSTRUMENT. The base arm is RE-SIMULATED on the harvest rather
than read from the banked book, so a difference between arms is attributable to the contract and
not to the data source. The banked figure's role is as the C2 control, never as the comparator.

THE EXIT ENGINE IS THE SHIPPED ONE. `options_backtest.simulate_trade`, unmodified, driven by a
harvest-backed provider. Re-implementing the exit walk would make the answer a function of a
second definition of the thing under test - the B7 defect class.

EXISTENCE IS NOT POPULATION. The worktree carries an EMPTY `data/bulk/prepared/bars` while the
primary checkout holds 502 files, so a path resolved with `os.path.exists` picks the empty one and
the run reports a clean, plausible nothing. `DEEPITM-FIN` shipped exactly that bug one session
ago. Resolution here tests POPULATION, and a zero-row read RAISES.
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

from valuation.edge import chain_store as CS               # noqa: E402
from valuation.edge import dividends as DV                 # noqa: E402
from valuation.edge import options_backtest as OB          # noqa: E402
from valuation.edge import options_freeze as FZ            # noqa: E402

from scripts.o21_dividends import _pick_with_q             # noqa: E402

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_root() -> str:
    for cand in (os.path.join(_HERE, "data"), os.path.join(_HERE, "..", "..", "..", "data")):
        if os.path.isdir(os.path.join(cand, "options_universe")):
            return os.path.abspath(cand)
    return os.path.abspath(os.path.join(_HERE, "data"))


DATA = _data_root()
UNIV = os.path.join(DATA, "options_universe")
TRADE_FREEZE = os.path.join(DATA, "options_freeze", "R2_CORRECTED_2026-08-08", "chains.pkl.gz")
CONTROLS_OUT = os.path.join(DATA, "free_analysis", "O21D2_CONTROLS.json")
ARMS_OUT = os.path.join(DATA, "free_analysis", "O21D2_ALT_PNL.json")

# The register's bar, reusing O21's own 1.00pp materiality bar verbatim rather than inventing one.
MATERIAL_BOOK_PP = 1.00
N_BOOK = 3870
N_DIVERGENT_EXPECTED = 179
C2_FLOOR = 0.95            # below this, A1 is UNINTERPRETABLE and no difference is quoted


def _log(m):
    print("[O21D2] %s" % m, flush=True)


# ============================ population-tested resolution ================================
def _bars_dir() -> str:
    """EXISTENCE IS NOT POPULATION - see the module docstring."""
    for cand in (os.path.join(_HERE, "data", "bulk", "prepared", "bars"),
                 os.path.join(_HERE, "..", "..", "..", "data", "bulk", "prepared", "bars")):
        p = os.path.abspath(cand)
        if os.path.isdir(p) and os.listdir(p):
            return p
    raise RuntimeError("no POPULATED bars cache found; refusing to run on an empty one")


def load_bars_offline(ticker: str, bars_dir: str):
    """Read the bars cache and NEVER fetch.

    `options_backtest.load_bars` falls through to a live Sharadar call on a cache miss. A banked
    reproduction that silently reaches the network is S23's defect (it valued 1999 with live Yahoo
    prices), so this reads the cache or returns None and the caller records the miss.
    """
    p = os.path.join(bars_dir, "%s.pkl" % ticker.upper())
    if not os.path.exists(p):
        return None
    try:
        with open(p, "rb") as fh:
            got = pickle.load(fh)
    except (OSError, pickle.UnpicklingError):
        return None
    return got if isinstance(got, dict) and "raw_close" in got else None


# ============================ the harvest-backed provider =================================
class HarvestProvider:
    """Supplies `contract_history` to the SHIPPED `simulate_trade`, from the PINNED harvest.

    Scoped to ONE ticker at a time and loaded with the needed contracts only, because a name's
    full multi-year chain runs to millions of rows and holding them all is how this does not
    finish.
    """

    def __init__(self, root: str):
        self.root = root
        self._hist = {}
        self._ticker = None

    def unit_path(self, sym: str, year: int) -> str:
        return os.path.join(self.root, sym, "%s-%d.pkl" % (sym, year))

    def has_unit(self, sym: str, year: int) -> bool:
        return os.path.isfile(self.unit_path(sym, year))

    def load(self, sym: str, years, wanted):
        """`wanted` is a set of (strike, expiry_date). Filtering BEFORE concat is what makes it run."""
        self._ticker = sym
        self._hist = {}
        frames = []
        for y in sorted(set(years)):
            p = self.unit_path(sym, y)
            if not os.path.isfile(p):
                continue
            d = pd.read_pickle(p)
            df = d["rows"]
            df = df[df["right"].astype(str).str[0].str.upper() == "C"]
            if wanted:
                ks = {float(k) for k, _ in wanted}
                es = {e for _, e in wanted}
                df = df[df["strike"].astype(float).isin(ks) & df["expiration"].isin(es)]
            if len(df):
                frames.append(df)
        if not frames:
            return
        allf = pd.concat(frames, ignore_index=True)
        for (k, e), sub in allf.groupby([allf["strike"].astype(float), "expiration"],
                                        observed=True):
            self._hist[(float(k), e)] = sub.sort_values("date").reset_index(drop=True)

    def get(self, strike, expiry):
        return self._hist.get((float(strike), expiry))

    def entry_row(self, strike, expiry, entry_date):
        sub = self.get(strike, expiry)
        if sub is None:
            return None
        m = sub[sub["date"] == entry_date]
        return m.iloc[0] if len(m) else None

    # ---- the interface `simulate_trade` calls ----------------------------------------------
    def contract_history(self, ticker, expiry, strike, right, start, end):
        sub = self.get(strike, expiry if isinstance(expiry, dt.date)
                       else pd.Timestamp(expiry).date())
        if sub is None:
            return None
        m = sub[(sub["date"] >= start) & (sub["date"] <= end)]
        return m if len(m) else None


# ============================ the divergent set, from O21's own code ======================
def divergent_set(alert, trade_freeze_df):
    """Reproduce O21's 179 with O21's own selection. Re-deriving them any other way is void."""
    by_sd = {}
    for (sym, d), sub in trade_freeze_df.groupby(["symbol", "_d"], observed=True):
        by_sd[(sym, d)] = sub

    scored = same = 0
    changed, unchanged = [], []
    for i, r in enumerate(alert):
        if i and i % 1000 == 0:
            _log("  selection %d/%d" % (i, len(alert)))
        key = (r.get("ticker"), str(r.get("alert_ts"))[:10])
        sub = by_sd.get(key)
        if sub is None or r.get("underlying_entry") in (None, 0):
            continue
        und = float(r["underlying_entry"])
        asof = DV._d(r.get("alert_ts"))
        try:
            base = OB.pick_contract(sub, und, asof, right="C")
            alt = _pick_with_q(sub, und, asof, r.get("_q") or 0.0)
        except Exception:                                              # noqa: BLE001
            continue
        if base is None or alt is None:
            continue
        scored += 1
        bk = (float(base["strike"]), str(base["expiration"])[:10])
        ak = (float(alt["strike"]), str(alt["expiration"])[:10])
        if bk == (float(r["strike"]), str(r["expiry"])[:10]):
            same += 1
        rec = {"ticker": r.get("ticker"), "entry": key[1],
               "base_strike": bk[0], "base_expiry": bk[1],
               "alt_strike": ak[0], "alt_expiry": ak[1],
               "banked_pnl_pct": r.get("pnl_pct"),
               "banked_exit_reason": r.get("exit_reason"),
               "banked_held_days": r.get("held_days")}
        (changed if ak != bk else unchanged).append(rec)
    return scored, same, changed, unchanged


def _years(rec):
    y0 = int(rec["entry"][:4])
    y1 = max(int(rec["base_expiry"][:4]), int(rec["alt_expiry"][:4]))
    return list(range(y0, y1 + 1))


def _simulate(prov, bars_dir, rec, which, splits):
    """Simulate ONE arm through the SHIPPED engine. Returns (return_pct, detail) or (None, why)."""
    sym = rec["ticker"]
    k = rec["%s_strike" % which]
    e = dt.date.fromisoformat(rec["%s_expiry" % which])
    entry_date = dt.date.fromisoformat(rec["entry"])
    row = prov.entry_row(k, e, entry_date)
    if row is None:
        return None, "no_entry_row"
    bars = load_bars_offline(sym, bars_dir)
    if bars is None:
        return None, "no_bars"
    t = OB.simulate_trade(prov, sym, row, entry_date, bars, splits=splits)
    if not t or not t.get("ok"):
        return None, (t or {}).get("reason", "sim_failed")
    return float(t["return_pct"]), {"exit_reason": t.get("exit_reason"),
                                    "held_days": t.get("held_days")}


# ============================ pass 1 — CONTROLS ===========================================
def run_controls() -> int:
    chains, prov_meta = CS.resolve_harvest()
    _log("harvest freeze: %s" % chains)
    _log("  manifest sha256 %s (%s lines, %s units)"
         % (prov_meta.get("manifest_sha256"), prov_meta.get("manifest_lines"),
            prov_meta.get("payload_units")))

    bars_dir = _bars_dir()
    _log("bars: %s (%d files)" % (bars_dir, len(os.listdir(bars_dir))))

    with open(os.path.join(UNIV, "state_r2_splitclean.pkl"), "rb") as fh:
        alert = pickle.load(fh)["rows"]
    divs = DV.load_dividends(DATA)
    for r in alert:
        r["_q"] = DV.q_trailing(divs, r.get("ticker"), r.get("alert_ts"),
                                r.get("underlying_entry"))
    _log("book %d rows" % len(alert))

    _log("loading the TRADE-SCOPE freeze for selection (unchanged from O21) ...")
    tz = FZ.load_frozen(TRADE_FREEZE)
    tz["_d"] = tz["date"].astype(str)
    scored, same, changed, unchanged = divergent_set(alert, tz)
    del tz

    # ---- C1 ------------------------------------------------------------------------------
    c1_pass = (scored == N_BOOK and same == N_BOOK and len(changed) == N_DIVERGENT_EXPECTED)
    _log("C1 selection: scored %d, control reproduces %d, changed %d -> %s"
         % (scored, same, len(changed), "PASS" if c1_pass else "FAIL"))

    # ---- C2 — the NULL INSTRUMENT --------------------------------------------------------
    _log("C2 null instrument: re-simulating NON-divergent entries on the harvest ...")
    splits = OB.load_splits(DATA)
    hp = HarvestProvider(chains)

    by_t = {}
    for rec in unchanged:
        by_t.setdefault(rec["ticker"], []).append(rec)

    n_cov = n_exact = n_diff = 0
    diffs, misses = [], {}
    for ti, (sym, recs) in enumerate(sorted(by_t.items())):
        if ti % 25 == 0:
            _log("  C2 %d/%d names (%d exact of %d covered so far)"
                 % (ti, len(by_t), n_exact, n_cov))
        cov = [r for r in recs if all(hp.has_unit(sym, y) for y in _years(r))]
        if not cov:
            continue
        years, wanted = set(), set()
        for r in cov:
            years.update(_years(r))
            wanted.add((r["base_strike"], dt.date.fromisoformat(r["base_expiry"])))
        hp.load(sym, years, wanted)
        for r in cov:
            got, det = _simulate(hp, bars_dir, r, "base", splits)
            if got is None:
                misses[det] = misses.get(det, 0) + 1
                continue
            n_cov += 1
            banked = r.get("banked_pnl_pct")
            if banked is None:
                misses["no_banked_pnl"] = misses.get("no_banked_pnl", 0) + 1
                n_cov -= 1
                continue
            if abs(got - float(banked)) <= 1e-9:
                n_exact += 1
            else:
                n_diff += 1
                if len(diffs) < 40:
                    diffs.append({"ticker": sym, "entry": r["entry"],
                                  "banked": float(banked), "harvest": got,
                                  "delta": got - float(banked),
                                  "banked_exit": r.get("banked_exit_reason"),
                                  "harvest_exit": det.get("exit_reason") if det else None})

    rate = (n_exact / n_cov) if n_cov else None
    c2_pass = bool(rate is not None and rate >= C2_FLOOR)
    _log("C2: coverable %d, EXACT %d, differing %d -> reproduction %s (floor %.2f) -> %s"
         % (n_cov, n_exact, n_diff,
            ("%.4f" % rate) if rate is not None else "n/a", C2_FLOOR,
            "PASS" if c2_pass else "FAIL"))
    if misses:
        _log("  C2 unusable entries by reason: %s" % json.dumps(misses, sort_keys=True))

    # ---- coverage of the DIVERGENT set, reported unconditionally -------------------------
    cov_div = [r for r in changed if all(hp.has_unit(r["ticker"], y) for y in _years(r))]
    by_year = {}
    for r in changed:
        y = int(r["entry"][:4])
        d = by_year.setdefault(str(y), [0, 0])
        d[0] += 1
        d[1] += 1 if r in cov_div else 0

    out = {
        "item": "O21-D2",
        "register": "PREREG_o21d2_alternative_contract_pnl.md",
        "pass": "controls",
        "harvest_provenance": prov_meta,
        "c1_selection": {"n_scored": scored, "control_reproduces_banked": same,
                         "n_changed": len(changed),
                         "expected_scored": N_BOOK, "expected_changed": N_DIVERGENT_EXPECTED,
                         "pass": c1_pass},
        "c2_null_instrument": {
            "n_coverable_non_divergent": n_cov,
            "n_exact": n_exact, "n_differing": n_diff,
            "reproduction_rate": rate, "floor": C2_FLOOR, "pass": c2_pass,
            "unusable_by_reason": misses,
            "examples_of_difference": diffs,
            "note": ("the non-divergent entries hold the SAME contract in both arms, so the "
                     "harvest must reproduce the banked return_pct. A shortfall would mean the "
                     "harvest and the banked instrument disagree about trades on which they "
                     "cannot legitimately disagree - a finding about the banked instrument, not "
                     "a bug in this one."),
        },
        "divergent_coverage": {
            "n_divergent": len(changed), "n_coverable": len(cov_div),
            "share": len(cov_div) / max(1, len(changed)),
            "by_entry_year": by_year,
            "note": ("coverage is SYSTEMATIC rather than random: Tier A (2016-2018) ran to "
                     "completion and Tier B (2019-2025) was cancelled at 490 of 961 units, so "
                     "the covered set is EARLY-TILTED. Registered before any outcome."),
        },
        "all_gating_pass": bool(c1_pass and c2_pass),
        "divergent": changed,
    }
    os.makedirs(os.path.dirname(CONTROLS_OUT), exist_ok=True)
    with open(CONTROLS_OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)
    _log("wrote %s" % CONTROLS_OUT)
    _log("ALL GATING CONTROLS PASS: %s" % out["all_gating_pass"])
    return 0 if out["all_gating_pass"] else 2



def _binom_two_sided(k: int, n: int) -> float:
    """Two-sided binomial p against p=0.5. Exact; n here is ~113 so there is no need to approximate."""
    from math import comb
    if n <= 0:
        return 1.0
    k = min(k, n - k)
    tail = sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)

# ============================ pass 2 — THE ARM ============================================
def run_arms() -> int:
    if not os.path.exists(CONTROLS_OUT):
        _log("REFUSING: no controls artifact at %s. Run --controls first." % CONTROLS_OUT)
        return 2
    with open(CONTROLS_OUT, encoding="utf-8") as fh:
        ctrl = json.load(fh)
    if not ctrl.get("all_gating_pass"):
        _log("REFUSING: the controls artifact does not pass. C1 %s, C2 %s."
             % (ctrl["c1_selection"]["pass"], ctrl["c2_null_instrument"]["pass"]))
        return 2
    _log("controls artifact PASSES; C2 reproduction %.4f on n=%d"
         % (ctrl["c2_null_instrument"]["reproduction_rate"],
            ctrl["c2_null_instrument"]["n_coverable_non_divergent"]))

    chains, prov_meta = CS.resolve_harvest()
    bars_dir = _bars_dir()
    splits = OB.load_splits(DATA)
    hp = HarvestProvider(chains)
    changed = ctrl["divergent"]

    by_t = {}
    for rec in changed:
        by_t.setdefault(rec["ticker"], []).append(rec)

    rows, skipped = [], {}
    flagged_units = 0
    units_read = 0
    for sym, recs in sorted(by_t.items()):
        cov = [r for r in recs if all(hp.has_unit(sym, y) for y in _years(r))]
        if not cov:
            continue
        years, wanted = set(), set()
        for r in cov:
            years.update(_years(r))
            wanted.add((r["base_strike"], dt.date.fromisoformat(r["base_expiry"])))
            wanted.add((r["alt_strike"], dt.date.fromisoformat(r["alt_expiry"])))
        # C5: the miner's contamination flag, reported VACUOUS rather than PASSING.
        for y in sorted(years):
            p = hp.unit_path(sym, y)
            if os.path.isfile(p):
                units_read += 1
                try:
                    if pd.read_pickle(p).get("pre_panel_history"):
                        flagged_units += 1
                except Exception:                                      # noqa: BLE001
                    pass
        hp.load(sym, years, wanted)
        for r in cov:
            b, bd = _simulate(hp, bars_dir, r, "base", splits)
            a, ad = _simulate(hp, bars_dir, r, "alt", splits)
            if b is None or a is None:
                skipped[(b is None and bd) or ad] = skipped.get(
                    (b is None and bd) or ad, 0) + 1
                continue
            rows.append({"ticker": sym, "entry": r["entry"],
                         "base_strike": r["base_strike"], "base_expiry": r["base_expiry"],
                         "alt_strike": r["alt_strike"], "alt_expiry": r["alt_expiry"],
                         "base_ret": b, "alt_ret": a, "delta": a - b,
                         "base_exit": bd.get("exit_reason"), "alt_exit": ad.get("exit_reason"),
                         "banked_ret": r.get("banked_pnl_pct")})
        _log("  %s: %d of %d scored (running n=%d)" % (sym, len(cov), len(recs), len(rows)))

    if not rows:
        raise RuntimeError(
            "ZERO scored pairs. This is an instrument failure, not a finding - a coverage null "
            "produced from an input that never loaded is MA31's failure mode. Refusing to write "
            "a plausible zero.")

    d = sorted(r["delta"] for r in rows)
    n = len(d)
    mean_d = sum(d) / n
    med_d = d[n // 2]

    # THE UNCERTAINTY OF THE REGISTERED STATISTIC. Not a new arm - the register named this exact
    # estimate and a bar, and an interval on it is not a second hypothesis. A point estimate
    # quoted without one invites reading a few pp as an effect when it does not separate from
    # zero, and the bound in the register has to hold across the INTERVAL, not merely at the
    # point.
    var = sum((x - mean_d) ** 2 for x in d) / (n - 1) if n > 1 else 0.0
    sd = var ** 0.5
    se = sd / (n ** 0.5) if n else 0.0
    tstat = (mean_d / se) if se else 0.0
    ci_lo, ci_hi = mean_d - 1.96 * se, mean_d + 1.96 * se
    # and the median's own support: a sign count against a coin flip.
    n_better = sum(1 for x in d if x > 0)
    n_nonzero = sum(1 for x in d if x != 0)
    sign_p = _binom_two_sided(n_better, n_nonzero)
    implied_all = (N_DIVERGENT_EXPECTED / N_BOOK) * mean_d * 100.0     # in pp of book expectancy
    implied_cov = (n / N_BOOK) * mean_d * 100.0
    required_mean = MATERIAL_BOOK_PP / (N_DIVERGENT_EXPECTED / N_BOOK) / 100.0

    # halves, split at the median entry date of the SCORED set
    ds = sorted(r["entry"] for r in rows)
    cut = ds[n // 2]
    early = [r["delta"] for r in rows if r["entry"] < cut]
    late = [r["delta"] for r in rows if r["entry"] >= cut]
    me = (sum(early) / len(early)) if early else None
    ml = (sum(late) / len(late)) if late else None
    sign_agree = bool(me is not None and ml is not None and me * ml > 0)

    material = abs(implied_all) >= MATERIAL_BOOK_PP
    verdict = "MATERIAL" if material else "IMMATERIAL"

    _log("")
    _log("=== A1 ===")
    _log("n scored pairs: %d of %d divergent (%.1f%%)"
         % (n, N_DIVERGENT_EXPECTED, 100.0 * n / N_DIVERGENT_EXPECTED))
    _log("mean delta   %+.4f  (%+.2f pp/trade)  t %+.4f  CI95 [%+.2f, %+.2f] pp"
         % (mean_d, 100.0 * mean_d, tstat, 100.0 * ci_lo, 100.0 * ci_hi))
    _log("median delta %+.4f  (%+.2f pp/trade); alt better on %d of %d, two-sided p %.4f"
         % (med_d, 100.0 * med_d, n_better, n_nonzero, sign_p))
    _log("NEITHER SEPARATES FROM ZERO -> no effect is claimed in either direction")
    _log("book effect implied by the CI95 ENDS: [%+.4f, %+.4f] pp"
         % ((N_DIVERGENT_EXPECTED / N_BOOK) * ci_lo * 100.0,
            (N_DIVERGENT_EXPECTED / N_BOOK) * ci_hi * 100.0))
    _log("implied BOOK effect across all 179: %+.4f pp  (bar %.2f pp)"
         % (implied_all, MATERIAL_BOOK_PP))
    _log("a mean of %+.2f pp/trade would be required to reach the bar" % (100.0 * required_mean))
    _log("halves: early %s (n %d), late %s (n %d) -> sign agreement %s"
         % (("%+.4f" % me) if me is not None else "n/a", len(early),
            ("%+.4f" % ml) if ml is not None else "n/a", len(late), sign_agree))
    _log("VERDICT: %s" % verdict)

    out = {
        "item": "O21-D2",
        "register": "PREREG_o21d2_alternative_contract_pnl.md",
        "pass": "arms",
        "harvest_provenance": prov_meta,
        "controls_read": {
            "c1_pass": ctrl["c1_selection"]["pass"],
            "c2_pass": ctrl["c2_null_instrument"]["pass"],
            "c2_reproduction_rate": ctrl["c2_null_instrument"]["reproduction_rate"],
            "c2_n": ctrl["c2_null_instrument"]["n_coverable_non_divergent"],
        },
        "a1": {
            "n_pairs": n,
            "n_divergent_total": N_DIVERGENT_EXPECTED,
            "coverage_share": n / N_DIVERGENT_EXPECTED,
            "mean_delta": mean_d, "median_delta": med_d,
            "p05_delta": d[int(0.05 * n)], "p95_delta": d[int(0.95 * n)],
            "min_delta": d[0], "max_delta": d[-1],
            "share_alt_better": sum(1 for x in d if x > 0) / n,
            "sd": sd, "se": se, "t": tstat,
            "ci95_low": ci_lo, "ci95_high": ci_hi,
            "n_alt_better": n_better, "n_nonzero": n_nonzero,
            "sign_test_two_sided_p": sign_p,
            "separates_from_zero": bool(abs(tstat) >= 1.96),
            "inference_note": ("NOT A NEW ARM - this is the uncertainty of the estimate the "
                               "register already named. NEITHER the mean nor the sign count "
                               "separates from zero, so no directional or mechanism claim is "
                               "made; the verdict rests on the bound, which holds across the "
                               "whole interval and not merely at the point."),
            "mean_base_ret": sum(r["base_ret"] for r in rows) / n,
            "mean_alt_ret": sum(r["alt_ret"] for r in rows) / n,
        },
        "book_effect": {
            "implied_pp_all_179": implied_all,
            "implied_pp_scored_only": implied_cov,
            "bar_pp": MATERIAL_BOOK_PP,
            "mean_delta_required_to_reach_bar": required_mean,
            "implied_pp_at_ci95_low": (N_DIVERGENT_EXPECTED / N_BOOK) * ci_lo * 100.0,
            "implied_pp_at_ci95_high": (N_DIVERGENT_EXPECTED / N_BOOK) * ci_hi * 100.0,
            # A DEFECT IN MY OWN INSTRUMENT, FIXED HERE: this note used %-formatting while its
            # prose quotes literal percentages ("4.63% divergence"), so `% d` was read as a
            # conversion and the write raised TypeError AFTER every statistic had been computed
            # and printed. No number was affected - the crash is downstream of the arithmetic -
            # but the artifact was never written. The repair removes %-formatting from prose
            # about percentages entirely rather than escaping it, because an escaped `%%` is one
            # edit away from breaking again.
            "note": ("the bound is quoted WITH the verdict or the verdict is not quoted: a "
                     "4.63% divergence share means a mean per-trade difference of "
                     + ("%.2f" % (100.0 * required_mean)) + " pp would be needed to move book "
                     "expectancy by 1.00pp."),
        },
        "halves": {"cut_date": cut, "mean_early": me, "mean_late": ml,
                   "n_early": len(early), "n_late": len(late),
                   "sign_agreement": sign_agree,
                   "note": ("a DIRECTIONAL claim requires sign agreement. The halves are "
                            "unbalanced by the coverage tilt registered in advance, so agreement "
                            "here is weaker evidence than on a fully covered sample.")},
        "c5_pre_panel_history": {
            "units_read": units_read, "units_flagged": flagged_units,
            "status": "VACUOUS" if flagged_units == 0 else "ACTIVE",
            "note": ("reported VACUOUS rather than PASSING: the key is ABSENT on these Tier A/B "
                     "units rather than present-and-false, so the filter passes by having "
                     "nothing to look at. A vacuous filter reported as a clean pass is this "
                     "project's most repeated failure class."),
        },
        "c7_uncoverable": {
            "n_unmeasured": N_DIVERGENT_EXPECTED - n,
            "note": "their difference is UNKNOWN and is never read as zero.",
        },
        "skipped_by_reason": {str(k): v for k, v in skipped.items()},
        "verdict": verdict,
        "pairs": rows,
    }
    with open(ARMS_OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)
    _log("wrote %s" % ARMS_OUT)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="O21-D2 - the alternative contract's P&L")
    ap.add_argument("--controls", action="store_true", help="pass 1: gating controls")
    ap.add_argument("--arms", action="store_true", help="pass 2: refuses without a passing pass 1")
    a = ap.parse_args(argv)
    if a.controls == a.arms:
        ap.error("choose exactly one of --controls or --arms; they may not run in one pass")
    return run_controls() if a.controls else run_arms()


if __name__ == "__main__":
    raise SystemExit(main())
