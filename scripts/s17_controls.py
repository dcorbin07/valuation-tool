"""S17 addendum - control C3 and the characteristic diagnostic.

ADDITIVE ONLY. This never recomputes an arm; it merges extra keys into the artifact written
by scripts.s17_event_codes so no published number can move.

C3 (registered, section 5) - AUDIT B6's signature. A per-ticker price tail makes the earliest
cross-sections consist ONLY of names that had already stopped trading. Measured directly: of
the names present in the earliest cross-sections, what fraction are STILL trading ten years
later? Under the B6 defect that fraction collapses toward zero.

D1 (diagnostic, NO VERDICT) - is an event code a firm-characteristic tilt rather than a signal?
That is U7's and S10's failure mode: a "signal" that is really a market-cap sort. Reported
because it is the most likely explanation of a sign-stable full-sample result.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from scripts.s17_event_codes import (ARM_CODES, DATA, LOOKBACK_CAL_DAYS,  # noqa: E402
                                     MIN_MARKET_CAP_MM, PRICE_FLOOR, load_caps,
                                     load_events, load_prices, month_end_grid)

ART = os.path.join(DATA, "free_analysis", "S17_EVENT_CODES.json")


def _log(m):
    print(f"[s17c] {m}", flush=True)


def control_c3(prices: dict, grid: list) -> dict:
    """Are the earliest cross-sections composed of names that had already stopped trading?"""
    g = np.array(grid, dtype="datetime64[D]")
    early = g[:12]
    out = []
    for d in early:
        present, survive = 0, 0
        later = d + np.timedelta64(3650, "D")
        for tk, (ds, _cs) in prices.items():
            i = int(np.searchsorted(ds, d, side="right")) - 1
            if i < 0 or (d - ds[i]).astype(int) > 10:
                continue
            present += 1
            if ds[-1] >= later:
                survive += 1
        if present:
            out.append({"date": str(d), "names_present": present,
                        "still_trading_10y_later": survive,
                        "survival_fraction": survive / present})
    frac = [r["survival_fraction"] for r in out]
    return {"earliest_dates": out,
            "min_survival_fraction": float(min(frac)) if frac else None,
            "mean_survival_fraction": float(np.mean(frac)) if frac else None,
            "b6_signature_would_be_near_zero": True,
            "ok": bool(frac and min(frac) > 0.20)}


def diagnostic_d1(prices: dict, events: dict, caps: dict, grid: list) -> dict:
    """Median market cap of event vs non-event names, per code. NO VERDICT."""
    g = np.array(grid, dtype="datetime64[D]")
    sample = g[::6]                      # every sixth month-end, enough for a characteristic
    ev_dates = {}
    for tk, rows in events.items():
        by = {}
        for d, codes in rows:
            for c in codes:
                if c in ARM_CODES:
                    by.setdefault(c, []).append(d)
        if by:
            ev_dates[tk] = {c: np.array(sorted(v), dtype="datetime64[D]")
                            for c, v in by.items()}
    acc = {c: {"ev": [], "no": []} for c in ARM_CODES}
    for d in sample:
        lo = d - np.timedelta64(LOOKBACK_CAL_DAYS, "D")
        for tk, (ds, cs) in prices.items():
            i = int(np.searchsorted(ds, d, side="right")) - 1
            if i < 0 or (d - ds[i]).astype(int) > 10 or float(cs[i]) < PRICE_FLOOR:
                continue
            cd, cv = caps.get(tk, (None, None))
            if cd is None:
                continue
            j = int(np.searchsorted(cd, d, side="right")) - 1
            if j < 0 or (d - cd[j]).astype(int) > 70 or cv[j] < MIN_MARKET_CAP_MM:
                continue
            mc = float(cv[j])
            evt = ev_dates.get(tk, {})
            for c in ARM_CODES:
                a = evt.get(c)
                hit = False
                if a is not None:
                    hit = int(np.searchsorted(a, d, "left")) > int(np.searchsorted(a, lo, "left"))
                acc[c]["ev" if hit else "no"].append(mc)
    out = {}
    for c in ARM_CODES:
        e, n = np.array(acc[c]["ev"]), np.array(acc[c]["no"])
        if e.size and n.size:
            out[c] = {"median_cap_mm_event": float(np.median(e)),
                      "median_cap_mm_no_event": float(np.median(n)),
                      "ratio": float(np.median(e) / np.median(n)),
                      "n_event": int(e.size), "n_no_event": int(n.size)}
    return {"note": "DIAGNOSTIC ONLY - no threshold, no verdict. A ratio far from 1.0 means "
                    "the code is substantially a market-cap sort (U7 / S10's failure mode).",
            "by_code": out, "sampled_dates": len(sample)}


def diagnostic_d2(prices: dict, events: dict, caps: dict, grid: list) -> dict:
    """How much INDEPENDENT evidence is '8 of 10 arms clear'? NO VERDICT.

    The SELRULE lesson in a new costume: 16 co-moving countries were worth 2-4 independent
    draws, not 16. If the five codes fire on largely the same name-dates then the arms are one
    finding counted five times, and BH - which assumes independence or positive dependence -
    is being fed correlated tests.
    """
    g = np.array(grid, dtype="datetime64[D]")
    sample = g[::6]
    ev_dates = {}
    for tk, rows in events.items():
        by = {}
        for d, codes in rows:
            for c in codes:
                if c in ARM_CODES:
                    by.setdefault(c, []).append(d)
        if by:
            ev_dates[tk] = {c: np.array(sorted(v), dtype="datetime64[D]")
                            for c, v in by.items()}
    cols = {c: [] for c in ARM_CODES}
    for d in sample:
        lo = d - np.timedelta64(LOOKBACK_CAL_DAYS, "D")
        for tk, (ds, cs) in prices.items():
            i = int(np.searchsorted(ds, d, side="right")) - 1
            if i < 0 or (d - ds[i]).astype(int) > 10 or float(cs[i]) < PRICE_FLOOR:
                continue
            cd, cv = caps.get(tk, (None, None))
            if cd is None:
                continue
            j = int(np.searchsorted(cd, d, side="right")) - 1
            if j < 0 or (d - cd[j]).astype(int) > 70 or cv[j] < MIN_MARKET_CAP_MM:
                continue
            evt = ev_dates.get(tk, {})
            for c in ARM_CODES:
                a = evt.get(c)
                hit = (a is not None
                       and int(np.searchsorted(a, d, "left"))
                       > int(np.searchsorted(a, lo, "left")))
                cols[c].append(1 if hit else 0)
    M = np.array([cols[c] for c in ARM_CODES], dtype=float)
    corr = np.corrcoef(M)
    pair = {}
    for i, a in enumerate(ARM_CODES):
        for j, b in enumerate(ARM_CODES):
            if i < j:
                pair[f"{a}~{b}"] = float(corr[i, j])
    return {"note": "DIAGNOSTIC ONLY - no threshold, no verdict. Pairwise correlation of the "
                    "event INDICATORS at name-date level. High values mean the arms are not "
                    "independent tests and '8 of 10 clear' overstates the evidence.",
            "n_name_dates": int(M.shape[1]),
            "pairwise_indicator_correlation": pair,
            "max_abs_pairwise": float(max(abs(v) for v in pair.values())),
            "mean_abs_pairwise": float(np.mean([abs(v) for v in pair.values()]))}


def diagnostic_d3(prices: dict, events: dict, caps: dict, grid: list) -> dict:
    """DIFFERENTIAL SURVIVAL. NO VERDICT.

    A name-date is only scored if a forward return exists `horizon` trading days later, so a
    name that stops trading inside the window is DROPPED rather than assigned its outcome. If
    event names disappear at a different rate from non-event names, the event-vs-non-event
    comparison is conditioned on survival differently in the two groups. Measured rather than
    assumed, because it runs in an unknown direction and would matter to anyone re-opening S17.
    """
    g = np.array(grid, dtype="datetime64[D]")
    sample = g[::6]
    H = 63
    ev_dates = {}
    for tk, rows in events.items():
        by = {}
        for d, codes in rows:
            for c in codes:
                if c in ARM_CODES:
                    by.setdefault(c, []).append(d)
        if by:
            ev_dates[tk] = {c: np.array(sorted(v), dtype="datetime64[D]")
                            for c, v in by.items()}
    tally = {c: {"ev_total": 0, "ev_dropped": 0, "no_total": 0, "no_dropped": 0}
             for c in ARM_CODES}
    for d in sample:
        lo = d - np.timedelta64(LOOKBACK_CAL_DAYS, "D")
        for tk, (ds, cs) in prices.items():
            i = int(np.searchsorted(ds, d, side="right")) - 1
            if i < 0 or (d - ds[i]).astype(int) > 10 or float(cs[i]) < PRICE_FLOOR:
                continue
            cd, cv = caps.get(tk, (None, None))
            if cd is None:
                continue
            j = int(np.searchsorted(cd, d, side="right")) - 1
            if j < 0 or (d - cd[j]).astype(int) > 70 or cv[j] < MIN_MARKET_CAP_MM:
                continue
            dropped = (i + H) >= len(cs)
            evt = ev_dates.get(tk, {})
            for c in ARM_CODES:
                a = evt.get(c)
                hit = (a is not None
                       and int(np.searchsorted(a, d, "left"))
                       > int(np.searchsorted(a, lo, "left")))
                k = "ev" if hit else "no"
                tally[c][f"{k}_total"] += 1
                if dropped:
                    tally[c][f"{k}_dropped"] += 1
    out = {}
    for c, t in tally.items():
        er = t["ev_dropped"] / t["ev_total"] if t["ev_total"] else None
        nr = t["no_dropped"] / t["no_total"] if t["no_total"] else None
        out[c] = {"event_drop_rate": er, "no_event_drop_rate": nr,
                  "difference_pp": (er - nr) * 100 if er is not None and nr is not None else None,
                  **t}
    return {"note": "DIAGNOSTIC ONLY - no threshold, no verdict. A name with no forward return "
                    "63 trading days out is dropped, not scored. A large difference in drop "
                    "rate means the arms condition on survival differently by group.",
            "horizon_days": H, "by_code": out,
            "max_abs_difference_pp": max(abs(v["difference_pp"]) for v in out.values())}


def main() -> int:
    _log("loading (prices are cached)")
    prices = load_prices()
    events = load_events()
    caps = load_caps()
    grid = month_end_grid(prices)
    _log("C3: the B6 truncation signature")
    c3 = control_c3(prices, grid)
    _log(f"  survival fraction min {c3['min_survival_fraction']:.3f} "
         f"mean {c3['mean_survival_fraction']:.3f} -> ok={c3['ok']}")
    _log("D1: characteristic diagnostic")
    d1 = diagnostic_d1(prices, events, caps, grid)
    for c, v in d1["by_code"].items():
        _log(f"  code {c}: median cap event ${v['median_cap_mm_event']:,.0f}M vs "
             f"non-event ${v['median_cap_mm_no_event']:,.0f}M  ratio {v['ratio']:.3f}")
    with open(ART, encoding="utf-8") as f:
        art = json.load(f)
    _log("D2: how independent are the arms?")
    d2 = diagnostic_d2(prices, events, caps, grid)
    _log(f"  max |pairwise indicator corr| {d2['max_abs_pairwise']:.4f}, "
         f"mean {d2['mean_abs_pairwise']:.4f} over {d2['n_name_dates']:,} name-dates")
    for k, v in sorted(d2["pairwise_indicator_correlation"].items(),
                       key=lambda kv: -abs(kv[1]))[:4]:
        _log(f"    {k}: {v:+.4f}")
    _log("D3: differential survival")
    d3 = diagnostic_d3(prices, events, caps, grid)
    for c, v in d3["by_code"].items():
        _log(f"  code {c}: dropped {v['event_drop_rate']:.4f} (event) vs "
             f"{v['no_event_drop_rate']:.4f} (non-event), diff {v['difference_pp']:+.2f}pp")
    art["controls"]["C3_no_per_ticker_truncation_b6"] = c3
    art["diagnostics"] = {"D1_characteristic_tilt": d1, "D2_arm_independence": d2,
                          "D3_differential_survival": d3}
    with open(ART, "w", encoding="utf-8") as f:
        json.dump(art, f, indent=2, default=str)
    _log(f"merged into {ART}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
