"""
E-4 -- the market-tail crash flag beside the accounting card. THE RUNNER.

Register: `PREREG_e4_market_tail_flag.md` (ALONE and BLIND at `cf7c7fc`). Trial booked at
`654326a`, equity 238 -> 239, BEFORE this file existed.

    python -m scripts.e4_market_tail_flag --build       # the tail-mass panel (slow, cached)
    python -m scripts.e4_market_tail_flag --controls    # pass 1: kills and controls, READ FIRST
    python -m scripts.e4_market_tail_flag --arm         # pass 2: REFUSES without a passing pass 1

THREE PASSES, AND THE SEPARATION IS NOT COSMETIC
-------------------------------------------------
`O10` computed a gating control and its outcome statistics in ONE pass and therefore could not
claim the control was read before the numbers. `--arm` exits non-zero if `E4_CONTROLS.json` is
absent or does not carry `all_gating_pass: true`, and a test proves the refusal by tampering the
artifact and restoring it byte-for-byte.

CRASH RATES ONLY. NEVER ALPHA.
-------------------------------
No return statistic is computed in this file or in `valuation/studies/market_tail.py`. Pinned by
an AST test over both trees, not a grep -- this docstring names the forbidden quantities, and a
substring guard would fire on the sentence that forbids them (`MA49`, and `MB15`'s fourth
instance of the same family).

RULE 9: THE DRAWS ARE STORED
-----------------------------
`--build` writes the per-row tail-mass panel to `E4_TAIL_PANEL.pkl` before anything is
summarised. `O21-D2` lost a 75-minute pass by summarising first, and `X7` kept 100 placebo draws
as five rates and made a one-column re-denomination cost a 3.4-hour re-run.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_PRIMARY = r"C:\Users\donni\Downloads\valuation-tool"
for _p in (_REPO, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from valuation.edge import chain_store as cs                        # noqa: E402
from valuation.edge import research_log                             # noqa: E402
from valuation.studies import crash_gate as cg                      # noqa: E402
from valuation.studies import market_tail as mt                     # noqa: E402
from s10_accounting_veto import build_flags                         # noqa: E402  ONE definition

# ---------------------------------------------------------------- registered constants (sec 4)
CRASH = -0.50                 # MA28's registered threshold
RATIO_FLOOR = 2.0             # MA28 RATIO_FLOOR
ABS_FLOOR_PP = 0.50           # MA28 ABS_FLOOR_PP
N_PERM = 500                  # MA28
PERM_SEED = 20260816          # MA28
MIN_FLAGGED_PER_DATE = 30     # MA28
MIN_KEPT_PER_DATE = 100       # MA28
MIN_EVENTS = 10               # declared in sec 4 of THIS register
RATE = 0.02                   # the flat discount rate I-1's census used
OVERLAP_KILL = 0.70           # the ledger's own bar, sec 6
VOL_RELABEL = 0.90            # sec 6 C-VOL: at or above this the flag IS an implied-vol sort

PANEL_NAME = "panel_r5r6.pkl"
TAIL_PANEL = "E4_TAIL_PANEL.pkl"
CONTROLS = "E4_CONTROLS.json"
ARM = "E4_ARM.json"


def _data(*parts) -> str:
    """Repo-anchored, falling back to the primary checkout. EXISTENCE IS NOT POPULATION."""
    p = os.path.join(_REPO, "data", *parts)
    if os.path.isdir(p):
        if os.listdir(p):
            return p
    elif os.path.exists(p):
        return p
    return os.path.join(_PRIMARY, "data", *parts)


def _out(name: str) -> str:
    d = _data("free_analysis")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, name)


def _json(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(float(o)) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o)[:10]
    if isinstance(o, float) and not math.isfinite(o):
        return None
    raise TypeError(repr(type(o)))


def raw_close_series(bars_dir: str, sym: str):
    """`raw_close`, never `close`. Strikes are as-traded (`U1-SPLIT`)."""
    f = os.path.join(bars_dir, "%s.pkl" % sym)
    if not os.path.exists(f):
        return None
    d = pd.read_pickle(f)
    if isinstance(d, pd.DataFrame):
        if "raw_close" not in d.columns or "date" not in d.columns:
            return None
        return pd.Series(pd.to_numeric(d["raw_close"], errors="coerce").values,
                         index=pd.to_datetime(d["date"])).dropna()
    if not isinstance(d, dict) or "raw_close" not in d or "date" not in d:
        return None
    return pd.Series(np.asarray(d["raw_close"], dtype=float),
                     index=pd.to_datetime(d["date"])).dropna()


# =============================================================================== pass 0: build

def build(rate: float = RATE) -> pd.DataFrame:
    panel = pd.read_pickle(_data("free_analysis", PANEL_NAME))
    panel["_d"] = pd.to_datetime(panel["date"])
    panel["_t"] = panel["ticker"].astype(str)

    chains, prov = cs.resolve_chains(_data())
    if not prov.get("pinned"):
        raise SystemExit("E-4 reads the PINNED freeze only; provenance says pinned=%r"
                         % prov.get("pinned"))
    print("chains: %s  manifest %s" % (chains, str(prov.get("manifest_sha256"))[:16]))

    bars = _data("bulk", "prepared", "bars")
    bar_syms = set(f[:-4] for f in os.listdir(bars) if f.endswith(".pkl"))
    freeze = set(d for d in os.listdir(chains) if os.path.isdir(os.path.join(chains, d)))
    names = sorted(freeze & set(panel["_t"]) & bar_syms)
    print("names with chain + raw_close + panel: %d" % len(names))

    # group the work by (ticker, year): one pickle load serves every panel date in that year
    dates = sorted(panel["_d"].unique())
    by_year = {}
    for d in dates:
        by_year.setdefault(str(d)[:4], []).append(d)

    # RESUME. A 45-minute build that writes once at the end loses everything to any
    # interruption -- measured, not hypothesised: the first attempt was killed at 15 minutes with
    # its wrapper and left nothing. The checkpoint is keyed on the SYMBOL set already done, so a
    # resume neither duplicates a row nor silently skips one.
    rows = []
    done = set()
    ckpt = _out(TAIL_PANEL + ".partial")
    if os.path.exists(ckpt):
        prev = pd.read_pickle(ckpt)
        rows = prev.to_dict("records")
        done = set(prev["symbol"].astype(str))
        print("resuming: %d rows, %d symbols already done" % (len(rows), len(done)), flush=True)

    for i, t in enumerate(names, 1):
        if t in done:
            continue
        rc = raw_close_series(bars, t)
        if rc is None:
            continue
        tdir = os.path.join(chains, t)
        for y, ds in sorted(by_year.items()):
            f = os.path.join(tdir, "%s-%s.pkl" % (t, y))
            if not os.path.exists(f):
                continue
            want = [d for d in ds
                    if ((panel["_d"] == pd.Timestamp(d)) & (panel["_t"] == t)).any()]
            if not want:
                continue
            try:
                df = pd.read_pickle(f)
            except Exception as e:                                    # noqa: BLE001
                rows.append({"symbol": t, "date": pd.Timestamp(want[0]), "usable": False,
                             "reason": "chain_unreadable:%s" % type(e).__name__})
                continue
            dcol = pd.to_datetime(df["date"])
            for d in want:
                d = pd.Timestamp(d)
                spot = float(rc.loc[d]) if d in rc.index else None
                sub = df.loc[dcol == d]
                rows.append(mt.tail_mass_row(sub, spot, d, t, rate))
        if i % 25 == 0:
            pd.DataFrame(rows).to_pickle(ckpt)
            print("  ... %d/%d names, %d rows (checkpointed)" % (i, len(names), len(rows)),
                  flush=True)

    out = pd.DataFrame(rows)
    # RULE 9: the draws land on disk BEFORE anything is summarised.
    out.to_pickle(_out(TAIL_PANEL))
    if os.path.exists(ckpt):
        os.remove(ckpt)
    print("wrote %s  rows %d  usable %d" % (TAIL_PANEL, len(out), int(out["usable"].sum())))
    return out


# ============================================================================ pass 1: controls

def _joined():
    """The tail panel joined to the panel's own crash outcome and to MA28's flags."""
    tail = pd.read_pickle(_out(TAIL_PANEL))
    tail["date"] = pd.to_datetime(tail["date"])
    ok = tail.loc[tail["usable"].astype(bool)].copy()

    panel = pd.read_pickle(_data("free_analysis", PANEL_NAME))
    panel["date"] = pd.to_datetime(panel["date"])
    panel["ticker"] = panel["ticker"].astype(str)
    keep = ["date", "ticker", "fwd_ret", "market_cap"]
    j = ok.merge(panel[keep], left_on=["date", "symbol"], right_on=["date", "ticker"],
                 how="inner", validate="one_to_one")

    # THE FLAGS ARE BUILT ON THE FULL PANEL CROSS-SECTION, NOT ON MY SUBSET, AND THAT IS NOT A
    # DETAIL. `MA28`'s external-financing leg flags the TOP DECILE WITHIN EACH DATE, so handing
    # `build_flags` only the ~440 optionable names would compute a decile boundary on a different
    # universe and produce a flag that is NOT the published one -- it would compute cleanly,
    # raise nothing, and quietly answer a different question. `MA31`'s column-name trap in a new
    # costume. Restricting to my rows happens AFTER the flag is formed.
    all_tickers = sorted(panel["ticker"].unique())
    flags = build_flags(_data("backtest"), all_tickers, sorted(j["date"].unique()))
    flags["date"] = pd.to_datetime(flags["date"])
    j = j.merge(flags[["date", "ticker", "vetoed", "n_flags"]], on=["date", "ticker"],
                how="left")
    # A name with no computable accounting flag is NOT accounting-flagged, and the count of such
    # rows is REPORTED -- MB8's finding is that the bucket a rule cannot evaluate is a real one.
    j["acct_flag"] = j["vetoed"].fillna(False).astype(bool)
    j["acct_uncomputable"] = j["vetoed"].isna()
    j["crash"] = cg.crash_flag(j["fwd_ret"], CRASH)
    j["market_flag"] = mt.within_date_worst_quintile(j, "tail_mass")
    qual = set(mt.qualifying_dates(j, "tail_mass"))
    j["date_qualifies"] = j["date"].isin(qual)
    return tail, j, flags


def controls() -> dict:
    tail, j, flags = _joined()
    q = j.loc[j["date_qualifies"]].copy()

    chains, prov = cs.resolve_chains(_data())
    rep = {"register": "PREREG_e4_market_tail_flag.md",
           "register_commit": "cf7c7fc",
           "trial_commit": "654326a",
           "by_domain_at_run": research_log.detail().get("by_domain")}

    # ---- C-PIN
    rep["C_PIN"] = {"pinned": bool(prov.get("pinned")),
                    "manifest_sha256": prov.get("manifest_sha256"),
                    "freeze_root": prov.get("freeze_root"),
                    "mutable_store_opened": False}
    # The covered date set is checked against an INDEPENDENTLY produced object rather than
    # against my own arithmetic -- `P1S0` built its optionable partition from the same store for
    # a different question, and if the two disagree one of them is wrong.
    p1s0 = _data("free_analysis", "P1S0_OPTIONABLE_PARTITION.pkl")
    if os.path.exists(p1s0):
        their = set(str(x)[:10] for x in
                    pd.to_datetime(pd.read_pickle(p1s0)["date"]).unique())
        mine = set(str(x)[:10] for x in j["date"].unique())
        rep["C_PIN"]["p1s0_dates"] = len(their)
        rep["C_PIN"]["my_dates"] = len(mine)
        rep["C_PIN"]["dates_only_in_p1s0"] = sorted(their - mine)
        rep["C_PIN"]["dates_only_in_mine"] = sorted(mine - their)
        rep["C_PIN"]["date_sets_identical"] = bool(their == mine)
    else:
        rep["C_PIN"]["p1s0_dates"] = None
        rep["C_PIN"]["note_p1s0"] = "VACUOUS, not passing: P1S0_OPTIONABLE_PARTITION.pkl absent"

    # ---- coverage / C-INSTRUMENT
    reasons = {}
    for r in tail.loc[~tail["usable"].astype(bool), "reason"].fillna("(none)"):
        h = str(r).split(":")[0]
        reasons[h] = reasons.get(h, 0) + 1
    rep["coverage"] = {
        "tail_rows_attempted": int(len(tail)),
        "tail_rows_usable": int(tail["usable"].astype(bool).sum()),
        "usable_share": float(tail["usable"].astype(bool).mean()) if len(tail) else None,
        "refusal_reasons": reasons,
        "joined_rows": int(len(j)),
        "rows_on_qualifying_dates": int(len(q)),
        "n_dates": int(q["date"].nunique()),
        "n_names": int(q["symbol"].nunique()),
        "min_names_per_date": int(q.groupby("date").size().min()) if len(q) else None,
        "median_names_per_date": float(q.groupby("date").size().median()) if len(q) else None,
        "acct_uncomputable_rows": int(q["acct_uncomputable"].sum()),
        "outcome_coverage": cg.coverage(q["fwd_ret"]),
        "extrapolated_share_primary": float(q["extrapolated_primary"].mean()) if len(q) else None,
        "integral_median": float(q["integral"].median()) if len(q) else None,
        "negative_mass_p95": float(q["negative_mass"].quantile(0.95)) if len(q) else None,
        "cdf_route_max_gap_median": (float(q["cdf_route_max_gap"].median())
                                     if "cdf_route_max_gap" in q else None),
    }

    # ---- K-OVERLAP (the ledger's kill, run AS WRITTEN, plus the reachable direction)
    m = q["market_flag"].astype(bool).values
    a = q["acct_flag"].astype(bool).values
    p_acct_given_mkt = float(a[m].mean()) if m.sum() else None
    p_mkt_given_acct = float(m[a].mean()) if a.sum() else None
    ceiling = (float(a.mean()) / mt.QUINTILE) if len(a) else None
    rep["K_OVERLAP"] = {
        "as_written_P_accounting_given_market": p_acct_given_mkt,
        "as_written_bar": OVERLAP_KILL,
        "as_written_arithmetic_ceiling": ceiling,
        "as_written_can_fire": bool(ceiling is not None and ceiling > OVERLAP_KILL),
        "reachable_P_market_given_accounting": p_mkt_given_acct,
        "reachable_bar": OVERLAP_KILL,
        "FIRES": bool(p_mkt_given_acct is not None and p_mkt_given_acct > OVERLAP_KILL),
        "cohens_kappa": mt.cohens_kappa(m, a),
        "co_firing_odds_ratio": mt.odds_ratio(m, a),
        "note": ("The as-written direction is bounded above by accounting_share / 0.20 and "
                 "cannot reach 0.70 -- MB8's failure, stated before running rather than after. "
                 "The kill is taken on the direction that can attain its bar."),
    }

    # ---- C-ACCT: the accounting arm IS MA28's flag, verified rather than assumed (MA28's C3)
    rep["C_ACCT_FIDELITY"] = {
        "flagged_share_on_full_cross_section": float(flags["vetoed"].mean()),
        "MA28_published_panel_share": 0.057414,
        "rows_on_full_cross_section": int(len(flags)),
        "n_dates": int(flags["date"].nunique()),
        "flagged_share_on_the_optionable_subset": float(q["acct_flag"].mean()) if len(q) else None,
        "note": ("Built on the FULL panel cross-section and restricted afterwards, because the "
                 "external-financing leg is a within-date TOP DECILE and a subset universe would "
                 "move the boundary. The subset share is expected to sit BELOW the panel share: "
                 "accounting flags fire on distressed small names and this universe is large and "
                 "liquid. Reported, not asserted."),
    }

    # ---- C-VOL, C-TENOR: mean per-date Spearman
    def mean_rho(col):
        vals = []
        for _, g in q.groupby("date"):
            x = pd.to_numeric(g["tail_mass"], errors="coerce")
            y = pd.to_numeric(g[col], errors="coerce")
            ok = x.notna() & y.notna()
            if int(ok.sum()) < 20:
                continue
            vals.append(float(x[ok].corr(y[ok], method="spearman")))
        return (float(np.mean(vals)) if vals else None), len(vals)

    rho_vol, n_vol = mean_rho("atm_vol")
    rho_dte, n_dte = mean_rho("dte_days")
    rep["C_VOL"] = {"mean_per_date_spearman_vs_atm_vol": rho_vol, "n_dates": n_vol,
                    "relabel_bar": VOL_RELABEL,
                    "MUST_BE_DESCRIBED_AS_AN_IV_SORT": bool(
                        rho_vol is not None and abs(rho_vol) >= VOL_RELABEL)}
    rep["C_TENOR"] = {"mean_per_date_spearman_vs_dte": rho_dte, "n_dates": n_dte,
                      "dte_median": float(q["dte_days"].median()) if len(q) else None,
                      "dte_p05": float(q["dte_days"].quantile(0.05)) if len(q) else None,
                      "dte_p95": float(q["dte_days"].quantile(0.95)) if len(q) else None}

    # ---- C-SIZE (MA28's C4)
    mc = pd.to_numeric(q["market_cap"], errors="coerce")
    rep["C_SIZE"] = {
        "median_market_cap_flagged": float(mc[m].median()) if m.sum() else None,
        "median_market_cap_kept": float(mc[~m].median()) if (~m).sum() else None,
        "ratio_flagged_over_kept": (float(mc[m].median() / mc[~m].median())
                                    if m.sum() and (~m).sum() and mc[~m].median() else None),
    }
    # MA28's C4, and the control that decided three sibling items (`U7`, `S10`, `V6-B`): a flag
    # that is really a size sort separates only BECAUSE small names crash more. Compared WITHIN
    # market-cap quintile, formed per date so it is a cross-sectional control and not an era one.
    qq = q.copy()
    qq["_capq"] = np.nan
    for _, g in qq.groupby("date"):
        v = pd.to_numeric(g["market_cap"], errors="coerce")
        if int(v.notna().sum()) < 25:
            continue
        qq.loc[g.index, "_capq"] = pd.qcut(v.rank(method="first"), 5, labels=False,
                                           duplicates="drop")
    by_q = {}
    for lab in sorted(x for x in qq["_capq"].dropna().unique()):
        g = qq.loc[qq["_capq"] == lab].rename(columns={"market_flag": "flagged"})
        po = cg.pooled(g, crash_col="crash", flag_col="flagged")
        by_q["cap_quintile_%d" % (int(lab) + 1)] = cg.quotable(po, min_events=MIN_EVENTS)
    rep["C_SIZE"]["within_cap_quintile"] = by_q
    rep["C_SIZE"]["within_cap_quintile_note"] = (
        "Quintile 1 is the SMALLEST. Every ratio is withheld where either bucket carries fewer "
        "than %d crashes -- on this universe most of them will be, and that is the finding "
        "rather than a gap." % MIN_EVENTS)

    rep["all_gating_pass"] = bool(
        rep["C_PIN"]["pinned"]
        and not rep["K_OVERLAP"]["FIRES"]
        and rep["coverage"]["rows_on_qualifying_dates"] > 0)
    rep["gating_note"] = ("K-OVERLAP is the only KILL. C-VOL is a mandatory RELABEL, not a kill. "
                          "C-SIZE and C-TENOR are reported whatever they show.")

    with open(_out(CONTROLS), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=2, default=_json)
    print(json.dumps(rep, indent=2, default=_json)[:4000])
    return rep


# ================================================================================= pass 2: arm

def arm() -> dict:
    p = _out(CONTROLS)
    if not os.path.exists(p):
        raise SystemExit("E-4 --arm REFUSES: %s absent. Pass 1 runs and is READ first." % CONTROLS)
    with open(p, encoding="utf-8") as fh:
        c = json.load(fh)
    if not c.get("all_gating_pass"):
        raise SystemExit("E-4 --arm REFUSES: controls did not pass (all_gating_pass=%r)."
                         % c.get("all_gating_pass"))

    _, j, _flags = _joined()
    q = j.loc[j["date_qualifies"]].copy()
    q = q.rename(columns={"market_flag": "flagged"})

    # `halves` EMBARGOES the middle date so neither half can borrow it, and it
    # returns that boundary -- recorded, because a half-split whose boundary is not
    # reported cannot be checked against any other item's.
    early, late, boundary = cg.halves(q)
    windows = {}
    for label, frame in (("full", q), ("early", early), ("late", late)):
        windows[label] = cg.window_result(
            frame, label, crash_col="crash", flag_col="flagged",
            ratio_floor=RATIO_FLOOR, abs_floor_pp=ABS_FLOOR_PP,
            n_perm=N_PERM, perm_seed=PERM_SEED,
            min_flagged_per_date=MIN_FLAGGED_PER_DATE,
            min_kept_per_date=MIN_KEPT_PER_DATE)
        po = windows[label].get("pooled")
        if po:
            windows[label]["quotable"] = cg.quotable(po, min_events=MIN_EVENTS)

    # ---- the realised per-date sd, and the MDE re-stated on it (sec 5)
    from valuation.edge.power_gate import state as power_state
    pdd = cg.per_date_diff(q, crash_col="crash", flag_col="flagged",
                           min_flagged_per_date=MIN_FLAGGED_PER_DATE,
                           min_kept_per_date=MIN_KEPT_PER_DATE)
    n_eq = int(research_log.detail()["by_domain"]["equity"])
    realised = {}
    if len(pdd) > 1:
        sd = float(pdd["d"].std(ddof=1))
        se = sd / math.sqrt(len(pdd))
        obs = float(pdd["d"].mean())
        realised = {
            "n_dates": int(len(pdd)), "sd_per_date": sd, "se_of_mean": se,
            "se_of_mean_pp": se * 100.0,
            "prerun_binomial_se_pp": 0.1638,
            "observed_mean_diff_pp": obs * 100.0,
            "mde_80pct_pp": (cg.required_dates(obs, sd, n_trials=n_eq)
                             if obs > 0 else None),
            "statement_project_hurdle": power_state(obs, se, n_trials=n_eq),
            "statement_t2_convention": power_state(obs, se, crit=2.0),
        }

    # ---- required-n at the realised base rate and flagged share
    base = float(q.loc[~q["flagged"], "crash"].mean())
    share = float(q["flagged"].mean())
    req = {}
    for ratio in (RATIO_FLOOR, 3.0422):
        for lab, kw in (("project_hurdle", dict(n_trials=n_eq)), ("t2", dict(crit=2.0))):
            try:
                req["ratio_%s_%s" % (ratio, lab)] = cg.required_rows(base, ratio, share, **kw)
            except ValueError as e:                                   # noqa: BLE001
                req["ratio_%s_%s" % (ratio, lab)] = {"error": str(e)}

    # ---- the three-state verdict (sec 5.1), decided by arithmetic
    passed = all(bool(windows[w].get("clears_all_three")) for w in ("full", "early", "late"))
    obs_eff = float(pdd["d"].mean()) if len(pdd) else 0.0
    mde80 = None
    if realised:
        from valuation.edge.power_gate import critical_value, z_for_power
        crit = float(critical_value(n_trials=n_eq))
        mde80 = (crit + float(z_for_power(0.80))) * realised["se_of_mean"]
    if passed:
        verdict = "PASS"
    elif mde80 is not None and abs(obs_eff) < mde80:
        verdict = "UNDERPOWERED"
    else:
        verdict = "FAIL"

    # ---- the 2x2 (sec 7), reported whatever the verdict
    tt = mt.two_by_two(q, market_col="flagged", acct_col="acct_flag", crash_col="crash")
    clean = q.loc[~q["acct_flag"]].copy()
    mkt_clean = q.loc[~q["flagged"]].copy()
    incremental = {
        "market_flag_on_accounting_CLEAN_rows": cg.quotable(
            cg.pooled(clean, crash_col="crash", flag_col="flagged"), min_events=MIN_EVENTS),
        "accounting_flag_on_market_CLEAN_rows": cg.quotable(
            cg.pooled(mkt_clean.rename(columns={"acct_flag": "flagged2"}),
                      crash_col="crash", flag_col="flagged2"), min_events=MIN_EVENTS),
    }

    # ---- sensitivity thresholds: NO VERDICT (sec 3.2)
    sens = {}
    for frac in mt.SENSITIVITY_THRESHOLDS:
        col = "tail_mass_%s" % frac
        if col not in q.columns or q[col].isna().all():
            continue
        f = mt.within_date_worst_quintile(q, col)
        po = cg.pooled(q.assign(flagged=f), crash_col="crash", flag_col="flagged")
        sens[col] = {"pooled": po,
                     "rank_agreement_with_primary": float(
                         q[["tail_mass", col]].corr(method="spearman").iloc[0, 1]),
                     "VERDICT": "NONE - sensitivity only, quoting this as the result voids sec 8.1"}

    rep = {"register": "PREREG_e4_market_tail_flag.md", "register_commit": "cf7c7fc",
           "verdict": verdict, "verdict_grammar": "PASS / FAIL / UNDERPOWERED (sec 5.1)",
           "bars": {"B2_ratio_floor": RATIO_FLOOR, "B3_abs_floor_pp": ABS_FLOOR_PP,
                    "crash_threshold": CRASH, "min_events": MIN_EVENTS,
                    "n_perm": N_PERM, "perm_seed": PERM_SEED,
                    "source": "MA28-CARD verbatim; min_events declared in this register"},
           "halves_boundary_embargoed": boundary,
           "windows": windows, "realised_power": realised, "required_rows": req,
           "mde_80pct_per_date_diff": mde80,
           "two_by_two": tt, "incremental": incremental, "sensitivity_NO_VERDICT": sens,
           "scope": ("The OPTIONABLE subset only -- 40 late dates, and this universe crashes at "
                     "0.4218% against 1.3250% for all panel names on the SAME dates. Nothing "
                     "here generalises to the panel or to the book."),
           "adopts": "NOTHING"}
    with open(_out(ARM), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=2, default=_json)
    print(json.dumps(rep, indent=2, default=_json)[:6000])
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--arm", action="store_true")
    ap.add_argument("--rate", type=float, default=RATE)
    a = ap.parse_args()
    if a.build:
        build(a.rate)
    if a.controls:
        controls()
    if a.arm:
        arm()
    if not (a.build or a.controls or a.arm):
        ap.error("pick one of --build / --controls / --arm")


if __name__ == "__main__":
    main()
